#! /usr/bin/env python3
import logging
import os
import select
import sys
import utils

import repair_candidates

from subprocess import Popen, PIPE


logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s ::: %(message)s",
)
logger = logging.getLogger(__name__)

dirname = os.path.dirname(__file__)


def fix_path(path):
    return os.path.join(dirname, path)


def run_fd_translator(domain, instance):
    binary_path = fix_path("translate/translate.py")
    python_exec = sys.executable  # Uses the currently running Python interpreter
    command = [
        python_exec,
        binary_path,
        "--keep-unimportant-variables",
        domain,
        instance,
    ]
    time = utils.get_elapsed_time()
    process = Popen(command, stdout=PIPE, stderr=PIPE, text=True)
    stdout, stderr = process.communicate()
    # if stdout:
    #     print(stdout, file=sys.stdout, end='')

    if stderr:
        print(stderr, file=sys.stderr, end="")
    _, error = process.communicate()
    logging.info(f"translator time: {utils.get_elapsed_time() - time:.2f}s")

    logger.info(f"translator return code: {process.returncode}")
    if process.returncode != 0:
        print(error)
        exit(process.returncode)


def run_plasp(domain, instance, lp, encoding, dump_output, pddl_instance=True):
    binary_path = fix_path("bin/plasp")
    command = [binary_path, "translate", instance]  # SAS+ instance
    if pddl_instance:
        command = [binary_path, "translate", domain, instance]

    with open(lp, "w") as lp_file:
        # First, we add the corresponding sequential encoding to it.
        # In domain-repair mode we use the repair variants, which route the
        # precondition check and effect application through applied_*
        # (with no repairs enabled they collapse to the plasp facts exactly).
        if args.domain_repair:
            encoding = fix_path("encodings/exact-sequential-horizon-repair.lp")
            if args.encoding == "bounded":
                encoding = fix_path("encodings/bounded-sequential-horizon-repair.lp")
        else:
            encoding = fix_path("encodings/exact-sequential-horizon.lp")
            if args.encoding == "bounded":
                encoding = fix_path("encodings/bounded-sequential-horizon.lp")
        with open(encoding) as seq_encoding:
            lp_file.write(seq_encoding.read())

        time_steps_encoding = fix_path("encodings/action-per-time-step.lp")
        if args.abstract_time_steps:
            time_steps_encoding = fix_path("encodings/abstract-time-steps.lp")

        with open(time_steps_encoding) as time_encoding:
            lp_file.write(time_encoding.read())

        if args.partial_plan:
            logger.info(f"Using partial plan '{args.partial_plan}'...")
            constraints: str | None = translate_partial_plan_into_constraints(
                args.partial_plan
            )
            lp_file.write("\n%%%%%%% partial plan encoding\n" + constraints + "\n")

        if args.black_list_plan:
            logger.info(f"Using blacklist plan '{args.black_list_plan}'...")
            blacklist = repair_candidates.render_blacklist_program(
                domain, instance, args.black_list_plan
            )
            lp_file.write("\n%%%%%%% blacklist plan encoding\n" + blacklist)

        if args.add_constraints_file:
            logger.info(
                f"Using additional constraints of file '{args.add_constraints_file}'..."
            )
            try:
                with open(args.add_constraints_file, "r") as f:
                    constraints = f.readlines()
                    constraints = "".join(constraints)
                    lp_file.write(
                        "\n%%%%%%% partial plan encoding\n" + constraints + "\n"
                    )
            except IOError:
                print(
                    f"Error: File {args.add_constraints_file} does not appear to exist."
                )
                exit(1)

        if args.add_constraints:
            constraints = args.add_constraints.encode().decode("unicode_escape")
            lp_file.write("\n%%%%%%% partial plan encoding\n" + constraints + "\n")

        if args.domain_repair:
            logger.info("Adding generated repair candidates...")
            # The static repair layer (applied_* indirection and the
            # {enabled(R) : repair(R)} switch) lives in the repair-variant
            # horizon encoding written above; here we only append the
            # domain-specific candidate facts and their bridge rules.
            candidates = args.repair_candidates
            if args.black_list_plan:
                # A blacklist is satisfied only by add-precondition repairs, so
                # by default generate just those. A partial plan (whitelist) is
                # only a guard here, exactly like in normal PlanPilot: it
                # constrains the solution to keep that plan runnable, but never
                # triggers repairs of its own. Relaxing candidates are unioned
                # in only when the user explicitly asks for them via
                # --repair-candidates.
                candidates = repair_candidates.blacklist_candidates(
                    domain,
                    instance,
                    candidates,
                    union_with_relaxing=bool(args.repair_candidates),
                )
            repair_program = repair_candidates.render_repair_program(
                domain, instance, candidates
            )
            lp_file.write("\n" + repair_program)


        # Now, we run plasp to produce the instance-specific info
        process = Popen(command, stdout=lp_file, stdin=PIPE, stderr=PIPE, text=True)

    time = utils.get_elapsed_time()
    _, error = process.communicate()
    logging.info(f"plasp time: {utils.get_elapsed_time() - time:.2f}s")

    logger.info(f"plasp return code: {process.returncode}")
    if process.returncode != 0:
        print(error)
        exit(process.returncode)


def run_fasb(lp, horizon, script=None, max_repairs=None):
    binary_path = fix_path(
        "bin/fasb-x86_64-unknown-linux-gnu/fasb"
    )  # TODO don't keep multiple versions

    if script:
        binary_path = fix_path("bin/fasb_interpreter")
        logger.info(f"Executing fasb script {script}...")

    command = [binary_path, lp, "-c", f"horizon={horizon}"]
    if max_repairs is not None:
        command += ["-c", f"max_repairs={max_repairs}"]
    command.append("0")

    if script:
        full_script_path = fix_path(script)
        command.append(full_script_path)

    if args.dry:
        logging.info("Dry startup...")
        logging.info(
            "To compute facets matching some regular expression 're', use the command '!? re'..."
        )
        command.append("--f")

    time = utils.get_elapsed_time()
    if script:
        logging.info("Starting fasb...")
        process = Popen(command, stdout=PIPE, stderr=PIPE, text=True)
        stdout, stderr = process.communicate()
        if stdout:
            print(stdout, file=sys.stdout, end="")

        if stderr:
            print(stderr, file=sys.stderr, end="")
    else:
        process = Popen(
            command,
            stdout=PIPE,
            stdin=PIPE,
            stderr=PIPE,
            text=True,
            universal_newlines=True,
            bufsize=1,
        )

        logging.info(
            "Starting fasb... To quit the interactive mode, use the command ':q'."
        )

        # Set up the file descriptors for select
        input_stream = sys.stdin
        output_stream = process.stdout
        error_stream = process.stderr

        prompts = 0
        try:
            terminated = False
            while not terminated:
                # Use select to wait for input/output readiness
                reads, _, _ = select.select(
                    [input_stream, output_stream, error_stream], [], []
                )
                for stream in reads:
                    if stream == output_stream:
                        # Drain everything currently available on the raw fd.
                        # We must NOT use process.stdout.readline() here: it is a
                        # buffered TextIOWrapper, so a single readline pulls a
                        # whole chunk (e.g. a multi-line answer set) into Python's
                        # internal buffer but returns only the first line. select()
                        # then sees the OS fd as empty and blocks forever, leaving
                        # the rest of the output (the answer set itself) stuck in
                        # the buffer. Reading the fd directly delivers all lines.
                        chunk = os.read(output_stream.fileno(), 65536)
                        if chunk:  # If there's output, print it
                            sys.stdout.write(chunk.decode(errors="replace"))
                            sys.stdout.flush()
                        else:
                            # If no output, the process might have closed
                            logging.info("Terminating fasb.")
                            logging.info(f"Number of prompts: {prompts}")
                            terminated = True
                            break

                    elif stream == input_stream:
                        # Get user input
                        user_input = input()
                        # Send input to the subprocess
                        process.stdin.write(user_input + "\n")
                        process.stdin.flush()  # Ensure it's sent immediately
                        prompts = prompts + 1

                    elif stream == error_stream:
                        # Read from the subprocess's error stream if needed
                        # (raw fd read for the same buffering reason as above).
                        error_chunk = os.read(error_stream.fileno(), 65536)
                        if error_chunk:
                            sys.stderr.write(error_chunk.decode(errors="replace"))
                            sys.stderr.flush()

        except KeyboardInterrupt:
            # Handle Ctrl+C to exit cleanly
            print("Exiting...")
            process.stdin.write("exit()\n")  # Send exit command to the subprocess
            process.stdin.flush()

    logging.info(f"fasb time: {utils.get_elapsed_time() - time:.2f}s")

    logger.info(f"fasb return code: {process.returncode}")


def remove_lp_files():
    current_directory = os.getcwd()

    for file_name in os.listdir(current_directory):
        file_path = os.path.join(current_directory, file_name)
        if os.path.isfile(file_path) and file_name.endswith(".lp"):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Error removing {file_path}: {e}")


def translate_partial_plan_into_constraints(file_path: str) -> str | None:
    # TODO: give the name of specific format
    """
    Expects actions in specific format.

    Example:
    `a b c (1) d e (1)`
    will be translated into
    `
    :- not occurs(action(("a","b","c")),1).
    :- not occurs(action(("d","e")),2).
    `
    """
    global PARTIAL_PLAN_DELIMITER
    PARTIAL_PLAN_DELIMITER = "(1)"

    try:
        with open(file_path, "r") as f:
            actions = filter(
                lambda x: x,
                map(lambda x: x.strip(), f.read().split(PARTIAL_PLAN_DELIMITER)),
            )
            return "\n".join(
                map(
                    lambda t: translate_action_to_constraint(*t[::-1]),
                    enumerate(actions),
                )
            )
    except Exception as e:
        logger.error(f"could not read partial plan '{file_path}': {e}")


def translate_action_to_constraint(action: str, at: int) -> str:
    """
    Translates whitespace-separated action into integrity constraint.

    Example:
    `a b c` as first action will be translated into
    `:- not occurs(action(("a","b","c")),1).`

    In domain-repair mode plasp grounds arguments as `constant("x")`, so each
    argument (but not the operator name) is wrapped accordingly.
    """
    name, *arguments = action.split(" ")
    if args.domain_repair:
        terms = [f'"{name}"'] + [f'constant("{x}")' for x in arguments]
    else:
        terms = [f'"{x}"' for x in [name, *arguments]]
    return ":- not occurs(action((" + ",".join(terms) + f")),{at+1})."


if __name__ == "__main__":
    args = utils.parse_arguments()

    domain_file = args.domain
    instance_file = args.instance
    if args.is_pddl_instance and not os.path.isfile(domain_file):
        sys.stderr.write("Error: Domain file does not exist.\n")
        sys.exit()
    if not os.path.isfile(instance_file):
        sys.stderr.write("Error: Instance file does not exist.\n")
        sys.exit()

    if args.black_list_plan and not args.domain_repair:
        sys.stderr.write(
            "Error: --black-list-plan requires --domain-repair "
            "(it relies on the repair-variant encoding).\n"
        )
        sys.exit()

    if args.domain_repair:
        logger.info("Domain repair mode: skipping translator, running plasp on PDDL...")
        run_plasp(
            args.domain, args.instance, args.lp_name, args.encoding, args.dump_output, True
        )
    else:
        if args.is_pddl_instance:
            logger.info("Running translator...")
            run_fd_translator(args.domain, args.instance)
            args.instance = "output.sas"
            # run_plasp(
            #     args.domain,
            #     args.instance,
            #     args.lp_name,
            #     args.encoding,
            #     args.dump_output)

        logger.info("Running plasp...")
        run_plasp("", args.instance, args.lp_name, args.encoding, args.dump_output, False)

    logger.info("Running fasb...")
    max_repairs = args.max_repairs if args.domain_repair else None
    run_fasb(args.lp_name, args.horizon, args.script, max_repairs)

    if args.cleanup:
        remove_lp_files()

    logging.info(f"Total time: {utils.get_elapsed_time():.2f}s")
    logger.info("Done!")
