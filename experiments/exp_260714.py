#! /usr/bin/env python3

import re
from pathlib import Path
from downward.experiment import Experiment
from downward.reports.absolute import AbsoluteReport
from lab.parser import Parser
from lab.reports import Attribute
from lab.environments import (
    BaselSlurmEnvironment,
    LocalEnvironment,
    TetralithEnvironment,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PLANPILOT_SIF = REPO_ROOT / "planpilot.sif"
BENCHMARKS_DIR = REPO_ROOT / "benchmarks"
DOMAINS = [
    "satellite",
    "transport",
    "blocks",
    "rovers",
]

NUM_PROBLEMS = 10
TIME_LIMIT = 30 * 60
MEMORY_LIMIT = 4096

# Cover both the Basel and Linköping clusters for simplicity.
REMOTE = BaselSlurmEnvironment.is_present() or TetralithEnvironment.is_present()

if REMOTE:
    ENV = LocalEnvironment(processes=4) # TODO change when running on the cluster
else:
    ENV = LocalEnvironment(processes=4)

CONFIG_TEMPLATES = [
    # (
    #     "to-forbid-max-repairs-1",
    #     "to-forbid/broken-domains/max-repairs-1",
    #     "to-forbid/black-list-plans",
    #     "--black-list-plan",
    #     "min",
    # ),

    (
        "to-solve-max-repairs-1",
        "to-solve/broken-domains/max-repairs-1",
        "to-solve/white-list-plans",
        "--partial-plan",
        "min",
    ),

    (
        "to-solve-max-repairs-2",
        "to-solve/broken-domains/max-repairs-2",
        "to-solve/white-list-plans",
        "--partial-plan",
        "min",
    ),

    (
        "to-solve-max-repairs-3",
        "to-solve/broken-domains/max-repairs-3",
        "to-solve/white-list-plans",
        "--partial-plan",
        "min",
    ),
]

def load_horizons(path):
    """Parse "Problem N\\nhorizon: H" blocks from horizons.txt."""
    text = path.read_text()
    horizons = {}
    for problem, horizon in re.findall(r"Problem\s+(\d+)\s*\n\s*horizon:\s*(\d+)", text):
        horizons[int(problem)] = int(horizon)
    return horizons


def get_parser():
    def add_horizon(content, props):
        match = re.search(r"--horizon\s+(\d+)", content)
        if match:
            props["horizon"] = int(match.group(1))

    def add_repair_cost(content, props):
        match = re.search(r"\brepair_cost=(\d+)\b", content)
        if match:
            props["repair_cost"] = int(match.group(1))

    def add_clingo_result(content, props):
        match = re.search(r"\bclingo result:\s*(SAT|UNSAT|UNKNOWN)\b", content)
        if match:
            props["satisfiable"] = match.group(1)
            props["coverage"] = 1 if match.group(1) == "SAT" else 0

    def add_clingo_time(content, props):
        match = re.search(r"\bclingo time:\s*([0-9]+(?:\.[0-9]+)?)s", content)
        if match:
            props["clingo_time"] = float(match.group(1))

    def add_plasp_time(content, props):
        match = re.search(r"\bplasp time:\s*([0-9]+(?:\.[0-9]+)?)s", content)
        if match:
            props["plasp_time"] = float(match.group(1))

    def add_total_time(content, props):
        match = re.search(r"\bTotal time:\s*([0-9]+(?:\.[0-9]+)?)s", content)
        if match:
            props["total_time"] = float(match.group(1))

    def extract_enabled_atoms(answer):
        """Extract the enabled(...) atoms."""
        atoms = []
        for m in re.finditer(r"enabled\(", answer):
            depth = 0
            for i in range(m.end() - 1, len(answer)):
                if answer[i] == "(":
                    depth += 1
                elif answer[i] == ")":
                    depth -= 1
                    if depth == 0:
                        atoms.append(answer[m.start():i + 1])
                        break
        return atoms

    def add_answers(content, props):
        for number, answer in re.findall(r"^Answer (\d+): (.*)$", content, re.MULTILINE):
            props[f"Answer_{number}"] = "; ".join(extract_enabled_atoms(answer)) or "(no repairs)"

    p = Parser()
    p.add_function(add_horizon)
    p.add_function(add_repair_cost)
    p.add_function(add_clingo_result)
    p.add_function(add_clingo_time)
    p.add_function(add_plasp_time)
    p.add_function(add_total_time)
    p.add_function(add_answers)
    return p


REPAIR_TYPE_SHORTHAND = {
    "add_prec": "add_precondition",
    "del_prec": "delete_precondition",
    "add_effect": "add_effect",
    "del_effect": "delete_effect",
}

GROUND_TRUTH_VARIANTS = {
    "MAX-REPAIRS 1": "max-repairs-1",
    "MAX-REPAIRS 2": "max-repairs-2",
    "MAX-REPAIRS 3": "max-repairs-3",
}


def parse_ground_truth(path):
    """Parse a satellitelog-*.txt file into {(variant, problem): [signature, ...]}.

    Each signature is the substring an enabled(...) atom must contain to count
    as a match, e.g. 'add_precondition("take_image",("calibrated"' -- good
    enough since the parameters are trusted to be correct once the repair
    type, action and predicate agree.
    """
    ground_truth = {}
    variant = problem_num = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("-----"):
            variant = GROUND_TRUTH_VARIANTS.get(line.lstrip("-").strip())
        elif line.startswith("Problem "):
            problem_num = int(line.split()[1])
            ground_truth[(variant, problem_num)] = []
        elif ":" in line and variant is not None and problem_num is not None:
            shorthand, rest = line.split(":", 1)
            action, args = rest.strip().split("(", 1)
            predicate = args.split()[0]
            repair_type = REPAIR_TYPE_SHORTHAND.get(shorthand.strip(), shorthand.strip())
            signature = f'{repair_type}("{action}",("{predicate}"'
            ground_truth[(variant, problem_num)].append(signature)
    return ground_truth


def precision_recall_f1(predicted_atoms, ground_truth_signatures):
    """predicted_atoms: the enabled(...) strings of one answer.
    ground_truth_signatures: the expected repair signatures for this problem."""
    if not ground_truth_signatures:
        return None, None, None
    true_positives = sum(
        any(sig in atom for atom in predicted_atoms) for sig in ground_truth_signatures
    )
    if not predicted_atoms:
        return 0.0, 0.0, 0.0
    precision = true_positives / len(predicted_atoms)
    recall = true_positives / len(ground_truth_signatures)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def add_f1_scores(run):
    """Compare the enabled(...) repairs found in Answer_1..Answer_10 against
    the known ground-truth repair(s) for this problem/variant (from
    satellitelog-to-solve.txt / satellitelog-to-forbid.txt). Adds
    precision/recall/F1 for Answer_1 alone and for the best-matching answer
    among all (tied-optimal) answers returned.
    """
    domain = run.get("domain")
    variant = run.get("broken_domains_variant")
    plan_flag = run.get("plan_flag")
    problem = run.get("problem", "")
    if not (domain and variant and plan_flag and problem.startswith("p") and problem.endswith(".pddl")):
        return True

    log_name = "to-solve" if plan_flag == "partial-plan" else "to-forbid"
    log_path = BENCHMARKS_DIR / domain / log_name / f"{domain}log-{log_name}.txt"
    if not log_path.is_file():
        return True

    ground_truth = parse_ground_truth(log_path).get((variant, int(problem[1:-5])))
    if not ground_truth:
        return True
    run["ground_truth"] = "; ".join(ground_truth)

    answers = [
        run[f"Answer_{i}"].split("; ") for i in range(1, 11) if run.get(f"Answer_{i}")
    ]

    precision, recall, f1 = precision_recall_f1(answers[0] if answers else [], ground_truth)
    run["precision_answer1"], run["recall_answer1"], run["f1_answer1"] = precision, recall, f1

    scored = [precision_recall_f1(a, ground_truth) for a in answers] or [(0.0, 0.0, 0.0)]
    best_precision, best_recall, best_f1 = max(scored, key=lambda prf: prf[2])
    run["precision_best"], run["recall_best"], run["f1_best"] = (
        best_precision, best_recall, best_f1
    )

    return True


def strip_unexplained_errors(run):
    """Remove lines containing 'info:' from unexplained_errors entries.
    """
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


ATTRIBUTES = [
    "algorithm",
    "domain",
    "domain_file",
    "problem",
    "error",
    Attribute("coverage", function=sum),
    "run_dir",
    "unexplained_errors",
    "repair_cost",
    "satisfiable",
    "plan_flag",
    "max_repairs",
    "broken_domains_variant",
    "ground_truth",
    Attribute("f1_answer1", function=sum),
    Attribute("f1_best", function=sum),
] + [f"Answer_{i}" for i in range(1, 11)] + [
    "horizon",
    Attribute("total_time", function=sum),
    Attribute("clingo_time", function=sum),
    Attribute("plasp_time", function=sum),
]

# --- Experiment setup ---
exp = Experiment(environment=ENV)
exp.add_parser(get_parser())


def add_resources(run, problem, domain, plan_file):
    run.add_resource("domain", str(domain), symlink=True)
    run.add_resource("problem", str(problem), symlink=True)
    run.add_resource("plan_file", str(plan_file), symlink=True)


def set_properties(
    run, benchmark_domain, config_name, problem, domain, horizon, plan_flag, max_repairs
):
    # "domain" is the grouping key AbsoluteReport uses to build one table per
    # domain (with "problem" as rows, "algorithm" as columns); it must be the
    # shared benchmark family name, not the per-problem broken-domain file.
    run.set_property("domain", benchmark_domain)
    run.set_property("domain_file", domain.name)
    run.set_property("problem", problem.name)
    run.set_property("algorithm", config_name)
    run.set_property("id", [config_name, domain.name, problem.name])
    run.set_property("horizon", horizon)
    run.set_property("plan_flag", plan_flag.lstrip("-"))
    run.set_property("max_repairs", max_repairs)
    run.set_property("broken_domains_variant", domain.parent.name)


for benchmark_domain in DOMAINS:
    benchmark_dir = BENCHMARKS_DIR / benchmark_domain
    problems_dir = benchmark_dir / "common-problems"
    horizons = load_horizons(benchmark_dir / "horizons.txt")

    for config_suffix, broken_domains_rel, plans_rel, plan_flag, max_repairs in CONFIG_TEMPLATES:
        config_name = config_suffix
        broken_domains_dir = benchmark_dir / broken_domains_rel
        plans_dir = benchmark_dir / plans_rel

        for i in range(1, NUM_PROBLEMS + 1):
            problem = problems_dir / f"p{i}.pddl"
            domain = broken_domains_dir / f"{benchmark_domain}{i}.pddl"
            plan_file = plans_dir / f"sas_plan-{i}"
            horizon = horizons[i]

            run = exp.add_run()
            add_resources(run, problem, domain, plan_file)
            set_properties(
                run,
                benchmark_domain,
                config_name,
                problem,
                domain,
                horizon,
                plan_flag,
                max_repairs,
            )

            cmd = [
                str(PLANPILOT_SIF),
                "-i", "{problem}",
                "-d", "{domain}",
                "--encoding", "bounded",
                "--horizon", str(horizon),
                "--domain-repair",
                "--max-repairs", str(max_repairs),
                plan_flag, "{plan_file}",
            ]
            run.add_command(
                "planpilot",
                cmd,
                time_limit=TIME_LIMIT,
                memory_limit=MEMORY_LIMIT,
            )

exp.add_step("build", exp.build)
exp.add_step("start", exp.start_runs)
exp.add_step("parse", exp.parse)
exp.add_fetcher(name="fetch")

exp.add_report(
    AbsoluteReport(
        attributes=ATTRIBUTES,
        filter=[strip_unexplained_errors, add_f1_scores],
    ),
    name="report",
)

exp.run_steps()
