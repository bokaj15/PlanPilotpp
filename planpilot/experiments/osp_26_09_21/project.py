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

SUITE_LEARNING = [
"airport-25",
"airport-50",
"airport-75",
"airport-100",
"barman-opt11-strips-25",
"barman-opt11-strips-50",
"barman-opt11-strips-75",
"barman-opt11-strips-100",
"barman-opt14-strips-25",
"barman-opt14-strips-50",
"barman-opt14-strips-75",
"barman-opt14-strips-100",
"blocks-25",
"blocks-50",
"blocks-75",
"blocks-100",
"childsnack-opt14-strips-25",
"childsnack-opt14-strips-50",
"childsnack-opt14-strips-75",
"childsnack-opt14-strips-100",
"depot-25",
"depot-50",
"depot-75",
"depot-100",
"driverlog-25",
"driverlog-50",
"driverlog-75",
"driverlog-100",
"elevators-opt08-strips-25",
"elevators-opt08-strips-50",
"elevators-opt08-strips-75",
"elevators-opt08-strips-100",
"elevators-opt11-strips-25",
"elevators-opt11-strips-50",
"elevators-opt11-strips-75",
"elevators-opt11-strips-100",
"floortile-opt11-strips-25",
"floortile-opt11-strips-50",
"floortile-opt11-strips-75",
"floortile-opt11-strips-100",
"floortile-opt14-strips-25",
"floortile-opt14-strips-50",
"floortile-opt14-strips-75",
"floortile-opt14-strips-100",
"freecell-25",
"freecell-50",
"freecell-75",
"freecell-100",
"ged-opt14-strips-25",
"ged-opt14-strips-50",
"ged-opt14-strips-75",
"ged-opt14-strips-100",
"grid-25",
"grid-50",
"grid-75",
"grid-100",
"gripper-25",
"gripper-50",
"gripper-75",
"gripper-100",
"hiking-opt14-strips-25",
"hiking-opt14-strips-50",
"hiking-opt14-strips-75",
"hiking-opt14-strips-100",
"logistics00-25",
"logistics00-50",
"logistics00-75",
"logistics00-100",
"logistics98-25",
"logistics98-50",
"logistics98-75",
"logistics98-100",
"miconic-25",
"miconic-50",
"miconic-75",
"miconic-100",
"movie-25",
"movie-50",
"movie-75",
"movie-100",
"mprime-25",
"mprime-50",
"mprime-75",
"mprime-100",
"mystery-25",
"mystery-50",
"mystery-75",
"mystery-100",
"nomystery-opt11-strips-25",
"nomystery-opt11-strips-50",
"nomystery-opt11-strips-75",
"nomystery-opt11-strips-100",
"openstacks-opt08-strips-25",
"openstacks-opt08-strips-50",
"openstacks-opt08-strips-75",
"openstacks-opt08-strips-100",
"openstacks-opt11-strips-25",
"openstacks-opt11-strips-50",
"openstacks-opt11-strips-75",
"openstacks-opt11-strips-100",
"openstacks-opt14-strips-25",
"openstacks-opt14-strips-50",
"openstacks-opt14-strips-75",
"openstacks-opt14-strips-100",
"openstacks-strips-25",
"openstacks-strips-50",
"openstacks-strips-75",
"openstacks-strips-100",
"parcprinter-08-strips-25",
"parcprinter-08-strips-50",
"parcprinter-08-strips-75",
"parcprinter-08-strips-100",
"parcprinter-opt11-strips-25",
"parcprinter-opt11-strips-50",
"parcprinter-opt11-strips-75",
"parcprinter-opt11-strips-100",
"parking-opt11-strips-25",
"parking-opt11-strips-50",
"parking-opt11-strips-75",
"parking-opt11-strips-100",
"parking-opt14-strips-25",
"parking-opt14-strips-50",
"parking-opt14-strips-75",
"parking-opt14-strips-100",
"pathways-noneg-25",
"pathways-noneg-50",
"pathways-noneg-75",
"pathways-noneg-100",
"pegsol-08-strips-25",
"pegsol-08-strips-50",
"pegsol-08-strips-75",
"pegsol-08-strips-100",
"pegsol-opt11-strips-25",
"pegsol-opt11-strips-50",
"pegsol-opt11-strips-75",
"pegsol-opt11-strips-100",
"pipesworld-notankage-25",
"pipesworld-notankage-50",
"pipesworld-notankage-75",
"pipesworld-notankage-100",
"pipesworld-tankage-25",
"pipesworld-tankage-50",
"pipesworld-tankage-75",
"pipesworld-tankage-100",
"psr-small-25",
"psr-small-50",
"psr-small-75",
"psr-small-100",
"rovers-25",
"rovers-50",
"rovers-75",
"rovers-100",
"satellite-25",
"satellite-50",
"satellite-75",
"satellite-100",
"scanalyzer-08-strips-25",
"scanalyzer-08-strips-50",
"scanalyzer-08-strips-75",
"scanalyzer-08-strips-100",
"scanalyzer-opt11-strips-25",
"scanalyzer-opt11-strips-50",
"scanalyzer-opt11-strips-75",
"scanalyzer-opt11-strips-100",
"sokoban-opt08-strips-25",
"sokoban-opt08-strips-50",
"sokoban-opt08-strips-75",
"sokoban-opt08-strips-100",
"sokoban-opt11-strips-25",
"sokoban-opt11-strips-50",
"sokoban-opt11-strips-75",
"sokoban-opt11-strips-100",
"storage-25",
"storage-50",
"storage-75",
"storage-100",
"tetris-opt14-strips-25",
"tetris-opt14-strips-50",
"tetris-opt14-strips-75",
"tetris-opt14-strips-100",
"tidybot-opt11-strips-25",
"tidybot-opt11-strips-50",
"tidybot-opt11-strips-75",
"tidybot-opt11-strips-100",
"tidybot-opt14-strips-25",
"tidybot-opt14-strips-50",
"tidybot-opt14-strips-75",
"tidybot-opt14-strips-100",
"tpp-25",
"tpp-50",
"tpp-75",
"tpp-100",
"transport-opt08-strips-25",
"transport-opt08-strips-50",
"transport-opt08-strips-75",
"transport-opt08-strips-100",
"transport-opt11-strips-25",
"transport-opt11-strips-50",
"transport-opt11-strips-75",
"transport-opt11-strips-100",
"transport-opt14-strips-25",
"transport-opt14-strips-50",
"transport-opt14-strips-75",
"transport-opt14-strips-100",
"trucks-strips-25",
"trucks-strips-50",
"trucks-strips-75",
"trucks-strips-100",
"visitall-opt11-strips-25",
"visitall-opt11-strips-50",
"visitall-opt11-strips-75",
"visitall-opt11-strips-100",
"visitall-opt14-strips-25",
"visitall-opt14-strips-50",
"visitall-opt14-strips-75",
"visitall-opt14-strips-100",
"woodworking-opt08-strips-25",
"woodworking-opt08-strips-50",
"woodworking-opt08-strips-75",
"woodworking-opt08-strips-100",
"woodworking-opt11-strips-25",
"woodworking-opt11-strips-50",
"woodworking-opt11-strips-75",
"woodworking-opt11-strips-100",
"zenotravel-25",
"zenotravel-50",
"zenotravel-75",
"zenotravel-100",
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

