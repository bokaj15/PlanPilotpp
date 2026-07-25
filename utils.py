import argparse
import errno
import logging
import os
import shutil

from pathlib import Path

logger = logging.getLogger(__name__)


def get_elapsed_time():
    """
    Return the CPU time taken by the python process and its child
    processes.
    """
    if os.name == "nt":
        # The child time components of os.times() are 0 on Windows.
        raise NotImplementedError("cannot use get_elapsed_time() on Windows")
    return sum(os.times()[:4])


def find_domain_filename(task_filename):
    """
    Find domain filename for the given task using automatic naming rules.
    """
    dirname, basename = os.path.split(task_filename)

    domain_basenames = [
        "domain.pddl",
        basename[:3] + "-domain.pddl",
        "domain_" + basename,
        "domain-" + basename,
    ]

    for domain_basename in domain_basenames:
        domain_filename = os.path.join(dirname, domain_basename)
        if os.path.exists(domain_filename):
            return domain_filename


def max_repairs_type(value):
    """Parse ``--max-repairs``: either a non-negative int bound, or 'min'."""
    if value == "min":
        return "min"
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--max-repairs must be an integer or 'min', got '{value}'"
        )


def repair_weight_type(value):
    """Parse one ``--repair-weights`` item: 'repair_type=weight'."""
    repair_type, sep, weight = value.partition("=")
    if not sep:
        raise argparse.ArgumentTypeError(
            f"--repair-weights items must be 'repair_type=weight', got '{value}'"
        )
    try:
        weight = int(weight)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--repair-weights: weight for '{repair_type}' must be an integer, "
            f"got '{weight}'"
        )
    return repair_type, weight


def parse_arguments():
    parser = argparse.ArgumentParser(description="Wrapper to pipeline plasp and fasb.")
    parser.add_argument(
        "-i",
        "--instance",
        required=True,
        help="The path to the PDDL/SAS instance file.",
    )
    parser.add_argument(
        "-d",
        "--domain",
        default=None,
        help="(Optional) The path to the PDDL domain file. If none is "
        "provided, the system will try to automatically deduce "
        "it from the instance filename.",
    )
    parser.add_argument(
        "--partial-plan",
        nargs="+",
        help="Path(s) to one or more partial-plan (positive-example) files. "
        "Passing more than one plan in total across --partial-plan and "
        "--negative-example enables multiple-plans repair mode: every plan "
        "becomes its own path and a single shared repair set must satisfy them "
        "all.",
    )
    parser.add_argument(
        "--add-constraints", help="String containing additional contraints.", type=str
    )
    parser.add_argument(
        "--add-constraints-file",
        help="The path to the file containing additional contraints.",
    )
    parser.add_argument(
        "--dry",
        help="If true, facets will not be computed at startup.",
        action="store_true",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        nargs="+",
        default=None,
        help="Horizon(s) used by clingo. Pass a single value for normal mode. "
        "In multiple-plans mode pass one horizon per --partial-plan file, in "
        "the same order (--horizon h1 h2 ... --partial-plan w1 w2 ...); "
        "negative-example plans need no horizon (it is their prefix length). "
        "The first value is also the global horizon constant handed to "
        "clingo/fasb. May be omitted when repairing only --negative-example "
        "plans (their horizon is derived from the prefix length).",
    )
    parser.add_argument(
        "--lp-name",
        default="instance.lp",
        type=str,
        help="Name of intermediate logic program (lp) file.",
    )
    parser.add_argument(
        "--encoding",
        default="exact",
        type=str,
        choices=["exact", "bounded"],
        help="Type of ASP encoding.",
    )
    parser.add_argument(
        "--abstract-time-steps",
        action="store_true",
        help="If true, it only reports that actions occur some time during the plans, but "
        "without specifying when.",
    )
    parser.add_argument(
        "--script",
        type=str,
        help="The path to the fasb script; for non-interactive mode (requires fasb built in"
        "interpreter configuration.",
    )
    parser.add_argument(
        "--dump-output",
        action="store_true",
        help="dump the output of tools.",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean all LP files in the folder after execution.",
    )
    parser.add_argument(
        "--domain-repair",
        action="store_true",
        help="Enable domain repair mode. Skips the Fast Downward translator.",
    )
    parser.add_argument(
        "--repair-candidates",
        nargs="+",
        default=None,
        help="Repair candidates to generate in domain repair mode. If omitted, "
        "the positive relaxing candidates (add positive effects, delete positive "
        "preconditions) are always used, plus the negative candidates (delete "
        "negative preconditions, add negative effects) when the domain has "
        "negative preconditions.",
    )
    parser.add_argument(
        "--max-repairs",
        type=max_repairs_type,
        default=1,
        help="Maximum number of repairs that may be enabled at once in domain "
        "repair mode (upper bound of the repair choice rule), or 'min' to "
        "instead minimize the total repair cost.",
    )
    parser.add_argument(
        "--repair-weights",
        nargs="+",
        type=repair_weight_type,
        default=None,
        metavar="REPAIR_TYPE=WEIGHT",
        help="Only used with --max-repairs min. Per-repair-type cost (default: "
        "1 for every type not listed). A repair type covers both polarities, "
        "e.g. add_precondition applies whether the added precondition is "
        "positive or negative. Valid types: add_precondition, "
        "delete_precondition, add_effect, delete_effect. Example: "
        "--repair-weights add_precondition=1 delete_effect=3",
    )
    parser.add_argument(
        "--enum-opt-sols",
        type=int,
        default=10,
        help="Only used with --max-repairs min. Maximum number of (possibly "
        "tied) optimal models clingo enumerates via --opt-mode=optN.",
    )
    parser.add_argument(
        "--negative-example",
        nargs="+",
        help="(Domain-repair mode) Path(s) to one or more plan files in standard "
        "PDDL plan format (one '(action arg1 arg2)' per line; ';' comments and "
        "blank lines ignored). In each plan the last action is the one that is "
        "applicable in the broken domain but should not be; the preceding actions "
        "establish the state it must not be applicable in, and a repair is forced "
        "that makes it inapplicable there. Passing more than one plan in total "
        "across --partial-plan and --negative-example enables multiple-plans "
        "repair mode (a single shared repair set must satisfy every plan).",
    )

    args = parser.parse_args()
    args.is_pddl_instance = True
    if args.instance.endswith(".sas"):
        args.is_pddl_instance = False
    if args.domain is None and args.is_pddl_instance:
        args.domain = find_domain_filename(args.instance)
        if args.domain is None:
            raise RuntimeError(
                f'Could not find domain filename that matches instance file "{args.domain}"'
            )

    return args


def write_lines_to_file(file_path, lines):
    try:
        with open(file_path, "w") as file:
            for line in lines:
                file.write(line + "\n")
        # print(f"Successfully wrote {len(lines)} lines to {file_path}.")
    except Exception as e:
        print(f"An error occurred: {e}")


def is_binary_available(binary_name):
    # Check if the binary exists in the current directory
    # TODO: change dir_binary to current_dir_binary?
    dir_binary = Path("bin/" + binary_name)
    if current_dir_binary.is_file():
        return True
    # Check if the binary is in the PATH
    if shutil.which(binary_name):
        return True
    return False


def check_necessary_files():
    if not is_binary_available("plasp"):
        logger.error("ERROR: plasp is not available!")
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), "plasp")

    if not is_binary_available("fasb"):
        logger.error("ERROR: fasb is not available!")
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), "fasb")
