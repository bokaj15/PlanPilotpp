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
    "blocks-25",
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

