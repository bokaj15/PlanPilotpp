#! /usr/bin/env python

import sys
import project
from pathlib import Path
from lab.parser import Parser
from lab.reports import Attribute

from downward import suites
from downward.experiment import Experiment, FastDownwardExperiment

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCHMARKS_DIR = str(REPO_ROOT / "benchmarks" / "katz-et-al-benchmarks")
REPO = REPO_ROOT / "third-party" / "downward-projects" / "symbolic-osp"
FAST_DOWNWARD = str(REPO / "fast-downward.py")

SUITE = project.SUITE_LEARNING

TIME_LIMIT = 30 * 60
MEMORY_LIMIT = 4096

# "--translate --search" is the invocation documented by symbolic-osp. It skips
# the preprocessor, which prunes goal-irrelevant variables and therefore empties
# OSP tasks, as those have no goal.
DRIVER_OPTIONS = [
    "--translate",
    "--search",
    "--overall-time-limit",
    f"{TIME_LIMIT}s",
    "--overall-memory-limit",
    f"{MEMORY_LIMIT}M",
]

if project.REMOTE:
    ENV = project.ArrheniusEnvironment(
        email="jennifer.santos@liu.se",
        extra_options="#SBATCH -A naiss2026-3-786",
        memory_per_cpu="4150M",
        cpus_per_task=4,
    )
else:
    SUITE = [
        "blocks-25:probBLOCKS-4-0.pddl",
    ]
    ENV = project.LocalEnvironment(processes=2)

CONFIGS = [
    (f"symosp-uBDD", ["--search", "symosp-fw()"]),
    (f"symosp-uADD", ["--search", "symosp-fw(use_add=true)"]),
]

ATTRIBUTES = [
    "error",
    "run_dir",
    "search_start_time",
    "search_start_memory",
    "total_time",
    "h_values",
    "coverage",
    "expansions",
    "memory",
    "planner_time",
    "plan_utility",
    Attribute("solved", absolute=True, min_wins=False),
]

def get_osp_parser():
    p = Parser()
    p.add_pattern("plan_utility", r"Plan utility: (-?\d+)", type=int)
    return p

def add_solved(content, props):
    """Solved: a plan was found and it has positive utility."""
    props["solved"] = int(
        props.get("coverage") == 1 and props.get("plan_utility", 0) > 0
    )

def get_solved_parser():
    p = Parser()
    p.add_function(add_solved)
    return p

def add_resources(run, instance):
    run.add_resource("domain", instance.domain_file, symlink=True)
    run.add_resource("problem", instance.problem_file, symlink=True)


def set_properties(run, instance, config_nick, config):
    run.set_property("domain", instance.domain)
    run.set_property("problem", instance.problem)
    run.set_property("algorithm", config_nick)
    run.set_property("component_options", config)
    run.set_property("driver_options", DRIVER_OPTIONS)
    run.set_property("id", [config_nick, instance.domain, instance.problem])


exp = Experiment(environment=ENV)

exp.add_parser(get_osp_parser())

for config_nick, config in CONFIGS:
    for instance in suites.build_suite(BENCHMARKS_DIR, SUITE):
        run = exp.add_run()
        add_resources(run, instance)
        set_properties(run, instance, config_nick, config)

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
exp.add_parser(FastDownwardExperiment.SINGLE_SEARCH_PARSER)
exp.add_parser(FastDownwardExperiment.PLANNER_PARSER)
# Must come after PLANNER_PARSER, which sets coverage.
exp.add_parser(get_solved_parser())

exp.add_step("build", exp.build)
exp.add_step("start", exp.start_runs)
exp.add_step("parse", exp.parse)
exp.add_fetcher(name="fetch")

project.add_absolute_report(
    exp, attributes=ATTRIBUTES
)

project.add_compress_exp_dir_step(exp)

exp.run_steps()
