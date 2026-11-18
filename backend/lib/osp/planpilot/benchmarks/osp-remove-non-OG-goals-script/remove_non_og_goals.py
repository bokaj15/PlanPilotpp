"""Remove the non-original soft goals from OSP problems.

In every problem file, entries of the (:utility ...) block whose weight is not
10 are removed; the weight-10 entries (the original goals) are kept unchanged.
The removed entries are expected to have weights in 1-5; any other removed
weight is reported as a warning. Files without (:utility, such as domain files,
are left untouched.

Usage: python3 remove_non_og_goals.py <folder> [--write]
Without --write it only reports what it would do and prints one example.
"""
import os
import sys

UTILITY = "(:utility"
KEEP_WEIGHT = 10
EXPECTED_REMOVED = range(1, 6)


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


def utility_entries(body):
    # each entry is (= <atom> <number>); <atom> may itself be (not (...))
    entries = []
    i = 0
    while True:
        i = body.find("(=", i)
        if i == -1:
            return entries
        end = closing_paren(body, i)
        atom_start = body.index("(", i + 2)
        atom_end = closing_paren(body, atom_start)
        weight = float(body[atom_end + 1:end])
        entries.append((body[i:end + 1], weight))
        i = end + 1


def convert(text):
    start = text.index(UTILITY)
    end = closing_paren(text, start)
    entries = utility_entries(text[start + len(UTILITY):end])

    kept = [e for e, w in entries if w == KEEP_WEIGHT]
    removed = [w for _, w in entries if w != KEEP_WEIGHT]
    if not kept:
        raise ValueError(f"no utility entry with weight {KEEP_WEIGHT}")

    utility = UTILITY + " \n" + "".join(f"    {e} \n" for e in kept) + " )"
    return text[:start] + utility + text[end + 1:], removed


def main():
    folder = sys.argv[1]
    write = "--write" in sys.argv
    example = None
    n_files = 0
    n_removed = 0
    for dirpath, _, files in os.walk(folder):
        for f in sorted(files):
            path = os.path.join(dirpath, f)
            with open(path) as fh:
                text = fh.read()
            if UTILITY not in text:
                continue
            new_text, removed = convert(text)
            unexpected = [w for w in removed if w not in EXPECTED_REMOVED]
            if unexpected:
                print(f"warning: removed weights outside 1-5 {unexpected}: {path}")
            n_files += 1
            n_removed += len(removed)
            if example is None and removed:
                example = (path, new_text)
            if write and removed:
                with open(path, "w") as fh:
                    fh.write(new_text)

    print(f"{'removed' if write else 'would remove'} {n_removed} utility entries in {n_files} files")
    if example and not write:
        print(f"\nexample: {example[0]}\n" + example[1][-600:])
main()
