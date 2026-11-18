#! /usr/bin/env python

import json
import re
import sys
import project
from pathlib import Path
from lab.parser import Parser
from lab.reports import Attribute

from downward import suites
from downward.experiment import Experiment, FastDownwardExperiment

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCHMARKS_DIR = str(REPO_ROOT / "benchmarks" / "katz-et-al-benchmarks-OG-mugs")
REPO = REPO_ROOT / "third-party" / "xpp-fast-downward"
FAST_DOWNWARD = str(REPO / "fast-downward.py")
COST_BOUNDS = json.loads(
    (Path(__file__).resolve().parent / "osp_cost_bounds_25_50_75.json").read_text()
)
LEVELS = ("25", "50", "75")

SUITE = project.FD_MUGS_SUITE

TIME_LIMIT = 30 * 60
MEMORY_LIMIT = 4096

# "--translate --search" is the invocation documented by symbolic-osp. It skips
# the preprocessor, which prunes goal-irrelevant variables and therefore empties
# OSP tasks, as those have no goal.
DRIVER_OPTIONS = [
    "--build",
    "release64",
    "--overall-time-limit",
    f"{TIME_LIMIT}s",
    "--overall-memory-limit",
    f"{MEMORY_LIMIT}M",
]

if project.REMOTE:
    ENV = project.ArrheniusEnvironment(
        email="jennifer.santos@liu.se",
        extra_options="#SBATCH -A naiss2025-5-561-cpu",
        memory_per_cpu="4150M",
    )
else:
    SUITE = [
        "blocks:probBLOCKS-4-0.pddl",
    ]
    ENV = project.LocalEnvironment(processes=2)

# {bound} is filled in per task from COST_BOUNDS.
CONFIGS = [
    (f"mugs-fd-syss", [ "--heuristic", "h=ff()", "--search", "goal_relation([eager(single(h), reopen_closed=true, bound={bound})], heu=[h], metasearch=BOTTOMUPMUGSSEARCH, all_soft_goals=true)" ]),
]


ATTRIBUTES = [
    "error",
    "run_dir",
    "id",
    "domain",
    "problem",
    "algorithm",
    "bound",
    "search_time",
    "actual_search_time",
    "total_time",
    "memory",
    "planner_wall_clock_time",
    "mugs",
    "mugs_count",
    "mugs_consistent",
]


def get_mugs_parser():
    def add_time(attribute, label):
        def add(content, props):
            match = re.search(rf"^{label}:\s*([0-9.e+-]+)s", content, re.M)
            if match:
                props[attribute] = float(match.group(1))
        return add

    def add_mugs(content, props):
        # One MUGS per line between "MUGS" and the next "****" line, atoms separated by "|".
        match = re.search(r"^MUGS\n(.*?)^\*+$", content, re.M | re.S)
        if match:
            props["mugs"] = [
                line.split("|") for line in match.group(1).splitlines() if line
            ]

    def add_mugs_count(content, props):
        match = re.search(r"Number of minimal unsolvable goal subsets:\s*(\d+)", content)
        if match:
            props["mugs_count"] = int(match.group(1))

    def check_mugs_count(content, props):
        if "mugs_count" in props:
            num_mugs = len(props.get("mugs", []))
            props["mugs_consistent"] = int(num_mugs == props["mugs_count"])
            if not props["mugs_consistent"]:
                props.add_unexplained_error(
                    f"parsed {num_mugs} MUGS, but planner reported {props['mugs_count']}"
                )

    def add_memory(content, props):
        # Like lab, only keep peak memory of runs that finished, i.e. printed the MUGS.
        match = re.search(r"^Peak memory:\s*(\d+) KB", content, re.M)
        if match and "mugs_count" in props:
            props["memory"] = int(match.group(1))

    p = Parser()
    p.add_function(add_time("search_time", "Search time"))
    p.add_function(add_time("actual_search_time", "Actual search time"))
    p.add_function(add_time("total_time", "Total time"))
    p.add_function(add_mugs)
    p.add_function(add_mugs_count)
    p.add_function(check_mugs_count)
    p.add_function(add_memory)
    return p


def add_resources(run, instance):
    run.add_resource("domain", instance.domain_file, symlink=True)
    run.add_resource("problem", instance.problem_file, symlink=True)

def set_properties(run, instance, domain, bound, config_nick, config):
    run.set_property("domain", domain)
    run.set_property("problem", instance.problem)
    run.set_property("bound", bound)
    run.set_property("algorithm", config_nick)
    run.set_property("component_options", config)
    run.set_property("driver_options", DRIVER_OPTIONS)
    run.set_property("id", [config_nick, domain, instance.problem])

exp = Experiment(environment=ENV)

for config_nick, config_template in CONFIGS:
    for instance in suites.build_suite(BENCHMARKS_DIR, SUITE):
        for level in LEVELS:
            # The FD bound is exclusive, so +1 allows plans of cost equal to the OSP bound.
            # The "bound" property stores the OSP bound itself, to compare with planpilot.
            bound = COST_BOUNDS[instance.domain][level][instance.problem]
            config = [arg.format(bound=bound + 1) for arg in config_template]
            domain = f"{instance.domain}-{level}"
            run = exp.add_run()
            add_resources(run, instance)
            set_properties(run, instance, domain, bound, config_nick, config)

            cmd = (
                [sys.executable, FAST_DOWNWARD]
                + DRIVER_OPTIONS
                + ["{domain}", "{problem}"]
                + config
            )
            run.add_command(
                "planner",
                cmd,
                time_limit=TIME_LIMIT,
                memory_limit=MEMORY_LIMIT,
            )

exp.add_parser(FastDownwardExperiment.EXITCODE_PARSER)
exp.add_parser(FastDownwardExperiment.TRANSLATOR_PARSER)
exp.add_parser(FastDownwardExperiment.ANYTIME_SEARCH_PARSER)
exp.add_parser(FastDownwardExperiment.PLANNER_PARSER)
exp.add_parser(get_mugs_parser())

exp.add_step("build", exp.build)
exp.add_step("start", exp.start_runs)
exp.add_step("parse", exp.parse)
exp.add_fetcher(name="fetch")

project.add_absolute_report(
    exp, attributes=ATTRIBUTES
)

project.add_compress_exp_dir_step(exp)

exp.run_steps()
