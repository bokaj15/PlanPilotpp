#! /usr/bin/env python3

import sys
import platform
import re
import os
import project
from pathlib import Path
from downward import suites
from downward.experiment import Experiment
from downward.reports.absolute import AbsoluteReport
from lab.parser import Parser
from lab.reports import Attribute
from lab.environments import (
    LocalEnvironment,
    ArrheniusEnvironment,
)

# Silence import-unused messages. Experiment scripts may use these imports.
assert (
    ArrheniusEnvironment
    and LocalEnvironment
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCHMARKS_DIR = str(REPO_ROOT / "benchmarks" / "katz-et-al-benchmarks")

SIF_PLANPILOT = os.path.join(REPO_ROOT, "planpilot.sif")

SUITE = project.SUITE_LEARNING

TIME_LIMIT = 30 * 60
MEMORY_LIMIT = 4096

DRIVER_OPTIONS = [
    "--overall-time-limit",
    f"{TIME_LIMIT}s",
    "--overall-memory-limit",
    f"{MEMORY_LIMIT}M",
]

ATTRIBUTES = [
    "coverage",
    "run_dir",
    "planner_wall_clock_time",
    "total_time",
    "plan_length",
]

REMOTE = ArrheniusEnvironment.is_present()

if REMOTE:
    SUITE = SUITE,
    ENV = ArrheniusEnvironment(
        email="jennifer.santos@liu.se",
        extra_options="#SBATCH -A naiss2025-5-561-cpu",
        memory_per_cpu="4150M",
        partition="fat",
        cpus_per_task=1,
    )
else:
    SUITE = [
        "blocks-25:probBLOCKS-4-0.pddl",
    ]
    ENV = LocalEnvironment(processes=2)


def get_parser():
    def has_bool_flag(content, key, value):
        pattern = rf"(?:^|[\s,]){key}={str(value)}(?:[\s,]|$)"
        return re.search(pattern, content) is not None

    def add_plan_length(content, props):
        matches = re.findall(r"\bplan_length\s*=\s*(\d+)\b", content)
        if matches:
            props["plan_length"] = int(matches[-1])

    def add_best_opt(content, props):
        match = re.search(r"\bbest_optimization_value\s*=\s*(\d+)\b", content)
        if match:
            props["plan_utility"] = int(match.group(1))

    def add_clingo_total_time(content, props):
        match = re.search(r"\bclingo_total_time\s*=\s*([0-9]+(?:\.[0-9]+)?)s?", content)
        if match:
            props["clingo_total_time"] = float(match.group(1))

    def add_clingo_cpu_time(content, props):
        match = re.search(r"\bclingo_cpu_time\s*=\s*([0-9]+(?:\.[0-9]+)?)s?", content)
        if match:
            props["clingo_cpu_time"] = float(match.group(1))

    def add_clingo_solve_time(content, props):
        match = re.search(r"\bclingo_solve_time\s*=\s*([0-9]+(?:\.[0-9]+)?)s?", content)
        if match:
            props["clingo_solve_time"] = float(match.group(1))

    def add_planner_time(content, props):
        match = re.search(r"Total time:\s*([0-9]+(?:\.[0-9]+)?)s?", content)
        if match:
            props["total_time"] = float(match.group(1))

    def add_wall_clock_time(content, props):
        match = re.search(r"osp wall-clock time:\s*([0-9]+(?:\.[0-9]+)?)s?", content)
        if match:
            props["planner_wall_clock_time"] = float(match.group(1))

    def add_coverage(content, props):
        if has_bool_flag(content, "satisfiable", True):
            props["solved"] = 1
        elif has_bool_flag(content, "satisfiable", False):
            props["solved"] = 0

    p = Parser()
    p.add_function(add_plan_length)
    p.add_function(add_best_opt)
    p.add_function(add_clingo_cpu_time)
    p.add_function(add_clingo_total_time)
    p.add_function(add_clingo_solve_time)
    p.add_function(add_planner_time)
    p.add_function(add_wall_clock_time, file="driver.log")
    p.add_function(add_coverage)
    return p


def strip_unexplained_errors(run):
    """Remove lines containing 'info:' from unexplained_errors entries."""
    errors = run.get("unexplained_errors")
    if not errors:
        return True

    keep = []
    for err in errors:
        filtered_lines = []
        skip_info_block = False
        for ln in err.splitlines():
            lower_ln = ln.lower()
            if "info:" in lower_ln:
                skip_info_block = True
                continue

            if skip_info_block:
                if ln.startswith(" ") or ln.startswith("\t") or ln.strip() == "":
                    continue
                skip_info_block = False

            filtered_lines.append(ln)

        filtered_err = "\n".join(filtered_lines).strip()
        if filtered_err:
            keep.append(filtered_err)

    if keep:
        run["unexplained_errors"] = keep
    else:
        run.pop("unexplained_errors", None)

    return True


# --- Experiment setup ---
exp = Experiment(environment=ENV)
exp.add_parser(get_parser())

configs = [
    ("osp_maximize", ["--osp", "max"]),
]

def add_resources(run, instance):
    run.add_resource("domain", instance.domain_file, symlink=True)
    run.add_resource("problem", instance.problem_file, symlink=True)


def set_properties(run, instance, config_name, config, config_driver_options):
    run.set_property("domain", instance.domain)
    run.set_property("problem", instance.problem)
    run.set_property("algorithm", config_name)
    run.set_property("component_options", config)
    run.set_property("driver_options", config_driver_options)
    run.set_property("id", [config_name, instance.domain, instance.problem])

driver_options = DRIVER_OPTIONS

for config_name, config in configs:
    for instance in suites.build_suite(BENCHMARKS_DIR, SUITE):

        run = exp.add_run()
        add_resources(run, instance)
        set_properties(run, instance, config_name, config, driver_options)

        cmd = (
            [SIF_PLANPILOT]
            + ["-i", "{problem}"]
            + ["-d", "{domain}"]
            + config
        )
        run.add_command(
            "osp",
            cmd,
            time_limit=TIME_LIMIT,
            memory_limit=MEMORY_LIMIT,
        )

        run.add_command(
            "cleanup",
            [
                sys.executable,
                "-c",
                "import glob, os; [os.remove(f) for f in glob.glob('output.sas')]",
            ],
        )

        run.add_command(
            "cleanup-gmon",
            [
                sys.executable,
                "-c",
                "import glob, os; [os.remove(f) for f in glob.glob('output.lp')]",
            ],
        )

exp.add_step("build", exp.build)
exp.add_step("start", exp.start_runs)
exp.add_step("parse", exp.parse)
exp.add_fetcher(name="fetch")

exp.add_report(
    AbsoluteReport(
        attributes=ATTRIBUTES,
        filter=[strip_unexplained_errors],
    ),
    name="report",
)

# exp.add_report(
#     AbsoluteReport(
#         attributes=ATTRIBUTES,
#         filter=[strip_unexplained_errors],
#         format="tex",
#     ),
#     name="report-tex",
#     outfile="report.tex",
# )

exp.run_steps()