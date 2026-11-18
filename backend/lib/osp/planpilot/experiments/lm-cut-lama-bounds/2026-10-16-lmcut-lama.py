#! /usr/bin/env python

import sys
import project
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCHMARKS_DIR = str(REPO_ROOT / "benchmarks" / "katz-et-al-benchmarks-unit")

REPO = "TODO" # TODO clone repo and enter path

SUITE = project.SUITE_UNIT_COST_LENGTH

if project.REMOTE:
    ENV = project.ArrheniusEnvironment(
        email="jennifer.santos@liu.se",
        extra_options="#SBATCH -A naiss2025-5-561-cpu",
        memory_per_cpu="4150M",
    )
else:
    SUITE = [
        "blocks:probBLOCKS-4-0.pddl",
        "blocks:probBLOCKS-4-1.pddl",
        "blocks:probBLOCKS-4-2.pddl",
        "sokoban-opt08-strips:p01.pddl",
    ]
    ENV = project.LocalEnvironment(processes=2)

CONFIGS = [
    ("lmcut", ["--search", "astar(lmcut())"], []),
    ("lama", [], ["--alias", "seq-sat-lama-2011"]),
]

BUILD_OPTIONS = []
DRIVER_OPTIONS = ["--overall-time-limit", "30m", "--overall-memory-limit", "4G"]

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
    "plan_length",
    "cost",
    "steps",
]

exp = project.FastDownwardExperiment(environment=ENV)
for config_nick, config, extra_driver_options in CONFIGS:
    exp.add_algorithm(
        config_nick,
        REPO,
        "LATEST_COMMIT", # TODO insert latest FD revision here
        config,
        build_options=BUILD_OPTIONS,
        driver_options=extra_driver_options + DRIVER_OPTIONS,
    )

exp.add_suite(BENCHMARKS_DIR, SUITE)

exp.add_parser(exp.EXITCODE_PARSER)
exp.add_parser(exp.TRANSLATOR_PARSER)
exp.add_parser(exp.SINGLE_SEARCH_PARSER)
exp.add_parser(exp.ANYTIME_SEARCH_PARSER)
exp.add_parser(exp.PLANNER_PARSER)

exp.add_step("build", exp.build)
exp.add_step("start", exp.start_runs)
exp.add_step("parse", exp.parse)
exp.add_fetcher(name="fetch")

project.add_absolute_report(
    exp, attributes=ATTRIBUTES
)

project.add_compress_exp_dir_step(exp)

exp.run_steps()
