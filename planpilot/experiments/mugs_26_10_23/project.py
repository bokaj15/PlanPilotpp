import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from downward.experiment import FastDownwardExperiment
from downward.reports.absolute import AbsoluteReport
from downward.reports.scatter import ScatterPlotReport
from downward.reports.taskwise import TaskwiseReport
from lab import tools
from lab.environments import (
    BaselSlurmEnvironment,
    LocalEnvironment,
    TetralithEnvironment,
    ArrheniusEnvironment
)
from lab.experiment import ARGPARSER
from lab.reports import Attribute, geometric_mean

# Silence import-unused messages. Experiment scripts may use these imports.
assert (
    BaselSlurmEnvironment
    and FastDownwardExperiment
    and LocalEnvironment
    and ScatterPlotReport
    and TaskwiseReport
    and TetralithEnvironment
    and ArrheniusEnvironment
)

DIR = Path(__file__).resolve().parent
SCRIPT = Path(sys.argv[0]).resolve()

# Cover both the Basel and Linköping clusters for simplicity.
REMOTE = BaselSlurmEnvironment.is_present() or TetralithEnvironment.is_present() or ArrheniusEnvironment.is_present()

TEST_LEARNING = ["blocks-25"]

PLANPILOT_MUGS_SUITE = [
"airport-25",
"airport-50", 
"airport-75",
"barman-opt11-strips-25",
"barman-opt11-strips-50",
"barman-opt11-strips-75",
"barman-opt14-strips-25",
"barman-opt14-strips-50",
"barman-opt14-strips-75",
"blocks-25",
"blocks-50",
"blocks-75",
"childsnack-opt14-strips-25",
"childsnack-opt14-strips-50",
"childsnack-opt14-strips-75",
"depot-25",
"depot-50",
"depot-75",
"driverlog-25",
"driverlog-50",
"driverlog-75",
"elevators-opt08-strips-25",
"elevators-opt08-strips-50",
"elevators-opt08-strips-75",
"elevators-opt11-strips-25",
"elevators-opt11-strips-50",
"elevators-opt11-strips-75",
"floortile-opt11-strips-25",
"floortile-opt11-strips-50",
"floortile-opt11-strips-75",
"floortile-opt14-strips-25",
"floortile-opt14-strips-50",
"floortile-opt14-strips-75",
"freecell-25",
"freecell-50",
"freecell-75",
"ged-opt14-strips-25",
"ged-opt14-strips-50",
"ged-opt14-strips-75",
"grid-25",
"grid-50",
"grid-75",
"gripper-25",
"gripper-50",
"gripper-75",
"hiking-opt14-strips-25",
"hiking-opt14-strips-50",
"hiking-opt14-strips-75",
"logistics00-25",
"logistics00-50",
"logistics00-75",
"logistics98-25",
"logistics98-50",
"logistics98-75",
"miconic-25",
"miconic-50",
"miconic-75",
"movie-25",
"movie-50",
"movie-75",
"mprime-25",
"mprime-50",
"mprime-75",
"mystery-25",
"mystery-50",
"mystery-75",
"nomystery-opt11-strips-25",
"nomystery-opt11-strips-50",
"nomystery-opt11-strips-75",
"openstacks-opt08-strips-25",
"openstacks-opt08-strips-50",
"openstacks-opt08-strips-75",
"openstacks-opt11-strips-25",
"openstacks-opt11-strips-50",
"openstacks-opt11-strips-75",
"openstacks-opt14-strips-25",
"openstacks-opt14-strips-50",
"openstacks-opt14-strips-75",
"openstacks-strips-25",
"openstacks-strips-50",
"openstacks-strips-75",
"parcprinter-08-strips-25",
"parcprinter-08-strips-50",
"parcprinter-08-strips-75",
"parcprinter-opt11-strips-25",
"parcprinter-opt11-strips-50",
"parcprinter-opt11-strips-75",
"parking-opt11-strips-25",
"parking-opt11-strips-50",
"parking-opt11-strips-75",
"parking-opt14-strips-25",
"parking-opt14-strips-50",
"parking-opt14-strips-75",
"pathways-noneg-25",
"pathways-noneg-50",
"pathways-noneg-75",
"pegsol-08-strips-25",
"pegsol-08-strips-50",
"pegsol-08-strips-75",
"pegsol-opt11-strips-25",
"pegsol-opt11-strips-50",
"pegsol-opt11-strips-75",
"pipesworld-notankage-25",
"pipesworld-notankage-50",
"pipesworld-notankage-75",
"pipesworld-tankage-25",
"pipesworld-tankage-50",
"pipesworld-tankage-75",
"psr-small-25",
"psr-small-50",
"psr-small-75",
"rovers-25",
"rovers-50",
"rovers-75",
"satellite-25",
"satellite-50",
"satellite-75",
"scanalyzer-08-strips-25",
"scanalyzer-08-strips-50",
"scanalyzer-08-strips-75",
"scanalyzer-opt11-strips-25",
"scanalyzer-opt11-strips-50",
"scanalyzer-opt11-strips-75",
"sokoban-opt08-strips-25",
"sokoban-opt08-strips-50",
"sokoban-opt08-strips-75",
"sokoban-opt11-strips-25",
"sokoban-opt11-strips-50",
"sokoban-opt11-strips-75",
"storage-25",
"storage-50",
"storage-75",
"tetris-opt14-strips-25",
"tetris-opt14-strips-50",
"tetris-opt14-strips-75",
"tidybot-opt11-strips-25",
"tidybot-opt11-strips-50",
"tidybot-opt11-strips-75",
"tidybot-opt14-strips-25",
"tidybot-opt14-strips-50",
"tidybot-opt14-strips-75",
"tpp-25",
"tpp-50",
"tpp-75",
"transport-opt08-strips-25",
"transport-opt08-strips-50",
"transport-opt08-strips-75",
"transport-opt11-strips-25",
"transport-opt11-strips-50",
"transport-opt11-strips-75",
"transport-opt14-strips-25",
"transport-opt14-strips-50",
"transport-opt14-strips-75",
"trucks-strips-25",
"trucks-strips-50",
"trucks-strips-75",
"visitall-opt11-strips-25",
"visitall-opt11-strips-50",
"visitall-opt11-strips-75",
"visitall-opt14-strips-25",
"visitall-opt14-strips-50",
"visitall-opt14-strips-75",
"woodworking-opt08-strips-25",
"woodworking-opt08-strips-50",
"woodworking-opt08-strips-75",
"woodworking-opt11-strips-25",
"woodworking-opt11-strips-50",
"woodworking-opt11-strips-75",
"zenotravel-25",
"zenotravel-50",
"zenotravel-75",
]

FD_MUGS_SUITE = [
"airport",
"barman-opt11-strips",
"barman-opt14-strips",
"blocks",
"childsnack-opt14-strips",
"depot",
"driverlog",
"elevators-opt08-strips",
"elevators-opt11-strips",
"floortile-opt11-strips",
"floortile-opt14-strips",
"freecell",
"ged-opt14-strips",
"grid",
"gripper",
"hiking-opt14-strips",
"logistics00",
"logistics98",
"miconic",
"movie",
"mprime",
"mystery",
"nomystery-opt11-strips",
"openstacks-opt08-strips",
"openstacks-opt11-strips",
"openstacks-opt14-strips",
"openstacks-strips",
"parcprinter-08-strips",
"parcprinter-opt11-strips",
"parking-opt11-strips",
"parking-opt14-strips",
"pathways-noneg",
"pegsol-08-strips",
"pegsol-opt11-strips",
"pipesworld-notankage",
"pipesworld-tankage",
"psr-small",
"rovers",
"satellite",
"scanalyzer-08-strips",
"scanalyzer-opt11-strips",
"sokoban-opt08-strips",
"sokoban-opt11-strips",
"storage",
"tetris-opt14-strips",
"tidybot-opt11-strips",
"tidybot-opt14-strips",
"tpp",
"transport-opt08-strips",
"transport-opt11-strips",
"transport-opt14-strips",
"trucks-strips",
"visitall-opt11-strips",
"visitall-opt14-strips",
"woodworking-opt08-strips",
"woodworking-opt11-strips",
"zenotravel",
]

def add_compress_exp_dir_step(exp):
    def compress_exp_dir():
        tar_file_path = Path(exp.path).parent / f"{exp.name}.tar.xz"
        exp_dir_path = Path(exp.path)

        subprocess.run(
            [
                "tar",
                "-cJvf",
                str(tar_file_path),
                "-C",
                str(exp_dir_path.parent),
                exp.name,
            ],
            check=True,
        )

        shutil.rmtree(exp_dir_path)

    exp.add_step("compress-exp-dir", compress_exp_dir)

def add_absolute_report(exp, *, name=None, outfile=None, **kwargs):
    report = AbsoluteReport(**kwargs)
    if name and not outfile:
        outfile = f"{name}.{report.output_format}"
    elif outfile and not name:
        name = Path(outfile).name
    elif not name and not outfile:
        name = f"{exp.name}-abs"
        outfile = f"{name}.{report.output_format}"

    if not Path(outfile).is_absolute():
        outfile = Path(exp.eval_dir) / outfile

    exp.add_report(report, name=name, outfile=outfile)
    if not REMOTE:
        exp.add_step(f"open-{name}", subprocess.call, ["xdg-open", outfile])

