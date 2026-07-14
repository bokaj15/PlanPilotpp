#! /usr/bin/env python3
"""Extract total_time per run from a lab 'properties' file and emit a
LaTeX/pgfplots figure with one subplot per domain, one line per algorithm.

Usage:
    ./plot_total_time.py [properties_path] [-o output.tex]
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

DOMAIN_ORDER = ["satellite", "transport", "blocks", "rovers"]

# (legend label, color name) per algorithm, in draw order.
ALGORITHM_STYLES = {
    "to-solve-max-repairs-1": ("1 repair", "color0"),
    "to-solve-max-repairs-2": ("2 repairs", "color1"),
    "to-solve-max-repairs-3": ("3 repairs", "color2"),
}

DOMAIN_DISPLAY_NAMES = {
    "blocks": "Blocksworld",
}

# Okabe-Ito colorblind-safe palette.
COLOR_DEFS = {
    "color0": "0072B2",
    "color1": "D55E00",
    "color2": "009E73",
}


def load_runs(properties_path):
    return list(json.loads(Path(properties_path).read_text()).values())


def problem_number(problem):
    match = re.search(r"\d+", problem or "")
    return int(match.group()) if match else None


def group_by_domain(runs):
    """domain -> algorithm -> {problem_number: total_time}"""
    by_domain = defaultdict(lambda: defaultdict(dict))
    for run in runs:
        domain = run.get("domain")
        algorithm = run.get("algorithm")
        total_time = run.get("total_time")
        num = problem_number(run.get("problem"))
        if None in (domain, algorithm, total_time, num):
            continue
        by_domain[domain][algorithm][num] = total_time
    return by_domain


def format_coords(points):
    return " ".join(f"({num},{time:.2f})" for num, time in sorted(points.items()))


def render_axis(domain, series_by_algorithm, with_legend):
    display_name = DOMAIN_DISPLAY_NAMES.get(domain, domain.capitalize())
    options = f"title={{\\textbf{{{display_name}}}}}"
    if with_legend:
        options += ", legend pos=north west"
    lines = [f"\\nextgroupplot[{options}]"]
    for algorithm, (label, color) in ALGORITHM_STYLES.items():
        points = series_by_algorithm.get(algorithm)
        if not points:
            continue
        coords = format_coords(points)
        lines.append(f"\\addplot[{color}, mark=none] coordinates {{{coords}}};")
        if with_legend:
            lines.append(f"\\addlegendentry{{{label}}}")
    return "\n".join(lines)


def render_document(by_domain):
    domains = [d for d in DOMAIN_ORDER if d in by_domain]
    domains += [d for d in sorted(by_domain) if d not in DOMAIN_ORDER]

    color_defs = "\n".join(
        f"\\definecolor{{{name}}}{{HTML}}{{{hex_}}}" for name, hex_ in COLOR_DEFS.items()
    )
    axes = "\n".join(
        render_axis(domain, by_domain[domain], with_legend=(i == 0))
        for i, domain in enumerate(domains)
    )

    return f"""\\documentclass[tikz,border=5pt]{{standalone}}
\\usepackage{{pgfplots}}
\\pgfplotsset{{compat=1.18}}
\\usepgfplotslibrary{{groupplots}}
{color_defs}
\\begin{{document}}
\\begin{{tikzpicture}}
\\begin{{groupplot}}[
    group style={{group size=2 by 2, horizontal sep=1.6cm, vertical sep=1.8cm}},
    width=6.5cm, height=5cm,
    xlabel={{problem}},
    ylabel={{Time (s)}},
    xtick distance=1,
    legend style={{font=\\footnotesize}},
]
{axes}
\\end{{groupplot}}
\\end{{tikzpicture}}
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
        help="Output .tex path (default: <properties dir>/total_time.tex).",
    )
    args = parser.parse_args()

    by_domain = group_by_domain(load_runs(args.properties))
    output = args.output or args.properties.parent / "total_time.tex"
    output.write_text(render_document(by_domain))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
