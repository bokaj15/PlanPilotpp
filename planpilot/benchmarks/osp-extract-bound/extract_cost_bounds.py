"""Extract the OSP cost bounds of katz-et-al-benchmarks-OSP-OG-goals.

Reads the (:bound N) of every problem in <domain>-<p> for p in 25/50/75 and
writes them as JSON grouped by domain and level:

    {"blocks": {"25": {"probBLOCKS-10-0.pddl": 8, ...}, "50": {...}, ...}, ...}
"""

import argparse
import json
import re
from pathlib import Path

BENCHMARKS = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = BENCHMARKS / "katz-et-al-benchmarks-OSP-OG-goals"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "cost_bounds.json"
LEVELS = (25, 50, 75)
BOUND_RE = re.compile(r"\(:bound\s+(\d+)\s*\)", re.IGNORECASE)


def split_dir_name(name):
    domain, level = name.rsplit("-", 1)
    return domain, int(level)


def read_bound(path):
    matches = BOUND_RE.findall(path.read_text())
    if len(matches) != 1:
        raise ValueError(f"{path}: expected one (:bound N), found {len(matches)}")
    return int(matches[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    bounds = {}
    count = 0
    for task_dir in sorted(p for p in args.source.iterdir() if p.is_dir()):
        domain, level = split_dir_name(task_dir.name)
        if level not in LEVELS:
            continue
        level_bounds = bounds.setdefault(domain, {}).setdefault(str(level), {})
        for problem in sorted(task_dir.glob("*.pddl")):
            if "domain" in problem.name:
                continue
            level_bounds[problem.name] = read_bound(problem)
            count += 1

    args.output.write_text(json.dumps(bounds, indent=2, sort_keys=True) + "\n")
    print(f"wrote {count} bounds for {len(bounds)} domains to {args.output}")


if __name__ == "__main__":
    main()
