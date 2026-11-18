#! /usr/bin/env python

"""Collect a "steps" value per planning problem from the lmcut/lama experiment.

Use the lmcut value when it exists (optimal plan length), otherwise fall back to
the lama value. Problems solved by neither are left out. The output JSON maps
domain -> problem -> steps.
"""

import argparse
import json
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DEFAULT_PROPERTIES = RESULTS_DIR / "properties_lmcut_lama_261016"
DEFAULT_OUTPUT = RESULTS_DIR / "steps_lmcut_lama_261016.json"

PRIMARY_ALGORITHM = "lmcut"
FALLBACK_ALGORITHM = "lama"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("properties", nargs="?", type=Path, default=DEFAULT_PROPERTIES)
    parser.add_argument("output", nargs="?", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def collect_steps_by_algorithm(properties):
    """Return {algorithm: {(domain, problem): steps}} for runs that have steps."""
    steps_by_algorithm = {}
    for run in properties.values():
        steps = run.get("steps")
        if steps is None:
            continue
        key = (run["domain"], run["problem"])
        steps_by_algorithm.setdefault(run["algorithm"], {})[key] = int(steps)
    return steps_by_algorithm


def main():
    args = parse_args()
    with open(args.properties) as f:
        properties = json.load(f)

    tasks = sorted({(run["domain"], run["problem"]) for run in properties.values()})
    steps_by_algorithm = collect_steps_by_algorithm(properties)
    primary = steps_by_algorithm.get(PRIMARY_ALGORITHM, {})
    fallback = steps_by_algorithm.get(FALLBACK_ALGORITHM, {})

    result = {}
    num_primary = num_fallback = num_missing = 0
    for domain, problem in tasks:
        if (domain, problem) in primary:
            steps = primary[(domain, problem)]
            num_primary += 1
        elif (domain, problem) in fallback:
            steps = fallback[(domain, problem)]
            num_fallback += 1
        else:
            num_missing += 1
            continue
        result.setdefault(domain, {})[problem] = steps

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Tasks: {len(tasks)}")
    print(f"  from {PRIMARY_ALGORITHM}: {num_primary}")
    print(f"  from {FALLBACK_ALGORITHM}: {num_fallback}")
    print(f"  no steps value: {num_missing}")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
