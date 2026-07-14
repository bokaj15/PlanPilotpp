#! /usr/bin/env python3
"""Compute per-problem F1 scores (top answer vs. best-of-10) from a lab
'properties' file and the benchmarks' ground-truth repair logs, then emit a
LaTeX table: one row per algorithm/configuration, two columns (F1, F1@10)
per domain.

Usage:
    ./table_f1.py [properties_path] [-o output.tex]
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS_DIR = REPO_ROOT / "benchmarks"

DOMAIN_ORDER = ["satellite", "transport", "blocks", "rovers"]
DOMAIN_DISPLAY_NAMES = {
    "blocks": "Blocksworld",
}

ALGORITHM_ORDER = [
    "to-solve-max-repairs-1",
    "to-solve-max-repairs-2",
    "to-solve-max-repairs-3",
]
ALGORITHM_LABELS = {
    "to-solve-max-repairs-1": "to-solve max 1 repair",
    "to-solve-max-repairs-2": "to-solve max 2 repairs",
    "to-solve-max-repairs-3": "to-solve max 3 repairs",
}

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


def load_runs(properties_path):
    return list(json.loads(Path(properties_path).read_text()).values())


def parse_ground_truth(path):
    """Parse a <domain>log-<to-solve|to-forbid>.txt file into
    {(variant, problem_num): [signature, ...]}."""
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


def extract_enabled_atoms(answer):
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


def precision_recall_f1(predicted_atoms, ground_truth_signatures):
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


def problem_number(problem):
    match = re.search(r"\d+", problem or "")
    return int(match.group()) if match else None


def run_f1_scores(run, ground_truth_cache):
    """Return (f1_answer1, f1_best, num_answers) for a single run, or
    (None, None, None) if no ground truth is available for it."""
    domain = run.get("domain")
    variant = run.get("broken_domains_variant")
    plan_flag = run.get("plan_flag")
    problem = run.get("problem", "")
    num = problem_number(problem)
    if None in (domain, variant, plan_flag, num):
        return None, None, None

    log_name = "to-solve" if plan_flag == "partial-plan" else "to-forbid"
    log_path = BENCHMARKS_DIR / domain / log_name / f"{domain}log-{log_name}.txt"
    if not log_path.is_file():
        return None, None, None

    if log_path not in ground_truth_cache:
        ground_truth_cache[log_path] = parse_ground_truth(log_path)
    ground_truth = ground_truth_cache[log_path].get((variant, num))
    if not ground_truth:
        return None, None, None

    answers = [
        extract_enabled_atoms(run[f"Answer_{i}"])
        for i in range(1, 11) if run.get(f"Answer_{i}")
    ]
    _, _, f1_answer1 = precision_recall_f1(answers[0] if answers else [], ground_truth)
    scored_f1 = [precision_recall_f1(a, ground_truth)[2] for a in answers] or [0.0]
    return f1_answer1, max(scored_f1), len(answers)


def aggregate(runs):
    """(domain, algorithm) -> {"f1_answer1": [...], "f1_best": [...], "num_answers": [...]}"""
    scores = defaultdict(lambda: {"f1_answer1": [], "f1_best": [], "num_answers": []})
    ground_truth_cache = {}
    for run in runs:
        f1_answer1, f1_best, num_answers = run_f1_scores(run, ground_truth_cache)
        if f1_answer1 is None:
            continue
        key = (run["domain"], run["algorithm"])
        scores[key]["f1_answer1"].append(f1_answer1)
        scores[key]["f1_best"].append(f1_best)
        scores[key]["num_answers"].append(num_answers)
    return scores


def mean(values):
    return sum(values) / len(values) if values else None


def format_score(value):
    return f"{value:.2f}" if value is not None else "--"


def format_count(value):
    return f"{value:.1f}" if value is not None else "--"


EMPTY_ENTRY = {"f1_answer1": [], "f1_best": [], "num_answers": []}


def render_table(scores):
    domains = [d for d in DOMAIN_ORDER if any(k[0] == d for k in scores)]
    domains += sorted({k[0] for k in scores} - set(domains))
    algorithms = [a for a in ALGORITHM_ORDER if any(k[1] == a for k in scores)]
    algorithms += sorted({k[1] for k in scores} - set(algorithms))

    col_spec = "l" + "ccc" * len(domains)
    domain_header = " & ".join(
        f"\\multicolumn{{3}}{{c}}{{{DOMAIN_DISPLAY_NAMES.get(d, d.capitalize())}}}"
        for d in domains
    )
    cmidrules = " ".join(
        f"\\cmidrule(lr){{{3 * i + 2}-{3 * i + 4}}}" for i in range(len(domains))
    )
    metric_header = " & ".join("F1 & F1@10 & avg" for _ in domains)

    rows = []
    for algorithm in algorithms:
        cells = [ALGORITHM_LABELS.get(algorithm, algorithm)]
        for domain in domains:
            entry = scores.get((domain, algorithm), EMPTY_ENTRY)
            cells.append(format_score(mean(entry["f1_answer1"])))
            cells.append(format_score(mean(entry["f1_best"])))
            cells.append(format_count(mean(entry["num_answers"])))
        rows.append(" & ".join(cells) + " \\\\")

    return f"""\\documentclass{{standalone}}
\\usepackage{{booktabs}}
\\begin{{document}}
\\begin{{tabular}}{{{col_spec}}}
\\toprule
 & {domain_header} \\\\
{cmidrules}
Configuration & {metric_header} \\\\
\\midrule
{chr(10).join(rows)}
\\bottomrule
\\end{{tabular}}
\\end{{document}}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "properties",
        nargs="?",
        default="data/exp_260714-eval/properties",
        type=Path,
        help="Path to a lab 'properties' JSON file.",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output .tex path (default: <properties dir>/f1_table.tex).",
    )
    args = parser.parse_args()

    scores = aggregate(load_runs(args.properties))
    output = args.output or args.properties.parent / "f1_table.tex"
    output.write_text(render_table(scores))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
