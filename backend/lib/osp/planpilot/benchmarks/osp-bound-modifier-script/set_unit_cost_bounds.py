"""Set the OSP cost bounds of katz-et-al-benchmarks-OSP-unit from unit-cost plan lengths.

For a problem in <domain>-<p> (p in 25/50/75/100) the new bound is
max(1, floor(p/100 * B)), where B is the unit-cost bound of that problem in
unit-cost-bounds.json. This is the same rule as in the original Katz et al.
benchmarks. The bound is computed from the JSON and not from the current
bound, so the script can be re-run safely.
"""

import argparse
import json
import re
from pathlib import Path

BENCHMARKS = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = BENCHMARKS / "katz-et-al-benchmarks-OSP-unit"
DEFAULT_BOUNDS = (
    BENCHMARKS.parent / "experiments" / "lm-cut-lama-bounds" / "results" / "steps_lmcut_lama_261016.json"
)
LEVELS = (25, 50, 75, 100)
BOUND_RE = re.compile(rb"\(:bound\s+\d+\s*\)", re.IGNORECASE)


def scaled_bound(unit_bound, level):
    return max(1, unit_bound * level // 100)


def split_dir_name(name):
    domain, level = name.rsplit("-", 1)
    return domain, int(level)


def set_bound(path, bound, dry_run):
    # Bytes keep the CRLF line endings of the openstacks files intact.
    text = path.read_bytes()
    old = BOUND_RE.search(text)
    new_text, count = BOUND_RE.subn(b"(:bound %d)" % bound, text)
    if count != 1:
        raise ValueError(f"{path}: expected one (:bound N), found {count}")
    if not dry_run and new_text != text:
        path.write_bytes(new_text)
    return old.group().decode(), new_text != text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--bounds", type=Path, default=DEFAULT_BOUNDS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    bounds = json.loads(args.bounds.read_text())
    changed = unchanged = 0
    missing = []
    for task_dir in sorted(p for p in args.target.iterdir() if p.is_dir()):
        domain, level = split_dir_name(task_dir.name)
        if level not in LEVELS:
            raise ValueError(f"{task_dir}: unknown level {level}")
        for problem in sorted(task_dir.glob("*.pddl")):
            if "domain" in problem.name:
                continue
            unit_bound = bounds.get(domain, {}).get(problem.name)
            if unit_bound is None:
                missing.append(f"{task_dir.name}/{problem.name}")
                continue
            bound = scaled_bound(unit_bound, level)
            old, did_change = set_bound(problem, bound, args.dry_run)
            if did_change:
                changed += 1
                if args.dry_run:
                    print(f"{task_dir.name}/{problem.name}: {old} -> (:bound {bound})")
            else:
                unchanged += 1

    verb = "would change" if args.dry_run else "changed"
    print(f"{verb}: {changed}, already correct: {unchanged}, no bound in JSON: {len(missing)}")
    for name in missing:
        print(f"  missing: {name}")


if __name__ == "__main__":
    main()
