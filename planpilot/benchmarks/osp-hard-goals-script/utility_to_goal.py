"""Turn OSP problems into classical problems with hard goals.

In every problem file, the (:utility ...) block and the (:bound N) after it are
replaced by (:goal (and ...)) over the utility atoms (weights are dropped).
A (:use-cost-metric) after the bound becomes (:metric minimize (total-cost)).
Files without (:utility, such as domain files, are left untouched.

Usage: python3 utility_to_goal.py <folder> [--write]
Without --write it only reports what it would do and prints one example.
"""
import os
import re
import sys

UTILITY = "(:utility"
BOUND_RE = re.compile(r"\s*\(:bound\s+\d+\s*\)")
USE_COST_METRIC_RE = re.compile(r"^\s*\(:use-cost-metric\)")


def closing_paren(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("unbalanced parentheses")


def utility_atoms(body):
    # each entry is (= <atom> <number>); <atom> may itself be (not (...))
    atoms = []
    i = 0
    while True:
        i = body.find("(=", i)
        if i == -1:
            return atoms
        end = closing_paren(body, i)
        atom_start = body.index("(", i + 2)
        atom_end = closing_paren(body, atom_start)
        atoms.append(" ".join(body[atom_start:atom_end + 1].split()))
        i = end + 1


def convert(text):
    start = text.index(UTILITY)
    end = closing_paren(text, start)
    atoms = utility_atoms(text[start + len(UTILITY):end])

    rest = text[end + 1:]
    bound = BOUND_RE.match(rest)
    if not bound:
        raise ValueError("no (:bound N) right after (:utility ...)")
    rest = rest[bound.end():]
    rest = USE_COST_METRIC_RE.sub("\n (:metric minimize (total-cost))", rest, count=1)

    goal = "(:goal (and\n" + "".join(f"    {a}\n" for a in atoms) + " ))"
    return text[:start] + goal + rest, atoms


def main():
    folder = sys.argv[1]
    write = "--write" in sys.argv
    example = None
    n_files = 0
    for dirpath, _, files in os.walk(folder):
        for f in sorted(files):
            path = os.path.join(dirpath, f)
            with open(path) as fh:
                text = fh.read()
            if UTILITY not in text:
                continue
            if "(:goal" in text:
                print(f"skip (already has :goal): {path}")
                continue
            new_text, atoms = convert(text)
            n_files += 1
            if example is None:
                example = (path, new_text)
            if write:
                with open(path, "w") as fh:
                    fh.write(new_text)

    print(f"{'converted' if write else 'would convert'} {n_files} files")
    if example and not write:
        print(f"\nexample: {example[0]}\n" + example[1][-600:])
main()
