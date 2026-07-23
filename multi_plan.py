#! /usr/bin/env python3
"""Generate the per-plan blocks for the multiple-plans repair encoding.

Scope: one problem, N input plans (any mix of positive and negative). Each
plan becomes its own PLAN ``P`` with a private timeline; all paths share the
global repair layer (``applied_*``/``enabled``) provided by
``encodings/multiple-plans-repair.lp``, so a single repair set must satisfy every
plan at once.

For each plan this module emits: a plan id, the per-plan facts the
template uses (it derives ``plan/1`` and ``time(0..H,P)`` from them):
  * a tag -- ``positive_example(P).`` or ``negative_example(P).``,
  * a horizon -- ``horizon(P, H).``, and
  * one ``occurs(action(...), step, P).`` fact per fixed action.

The tag decides how the plan is constrained (all in the template):
  * positive-example -> its fixed actions are preserved and the tail up to the
    horizon may be completed so the goal holds at the horizon;
  * negative-example -> only its prefix runs (horizon = prefix length) and its
    last action is forced inapplicable in the state the prefix reaches. That
    block-last-action constraint names a specific action, so it is emitted here.

Positive example files use the partial-plan format (whitespace-separated
actions delimited by ``(1)``); negative example files use one
``(action arg1 arg2)`` per line. This module is independent of
``repair_candidates`` -- it only uses the shared ``applied_precondition``
the encoding provides.
"""

WHITELIST_DELIMITER = "(1)"


def _parse_positive_example(path):
    """Parse a ``(1)``-delimited partial plan into ``[(op, [args]), ...]``."""
    plan = []
    with open(path) as f:
        text = f.read()
    for chunk in text.split(WHITELIST_DELIMITER):
        chunk = chunk.strip()
        if not chunk:
            continue
        tokens = chunk.split()
        plan.append((tokens[0].lower(), [t.lower() for t in tokens[1:]]))
    return plan


def _parse_negative_example(path):
    """Parse a PDDL ``(action args)``-per-line plan into ``[(op, [args]), ...]``.

    Blank lines and ``;`` comments (e.g. a trailing cost line) are ignored.
    """
    plan = []
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith(";"):
                continue
            tokens = line.strip("()").split()
            if not tokens:
                continue
            plan.append((tokens[0].lower(), [t.lower() for t in tokens[1:]]))
    return plan


def _ground_action(op, args):
    """Render ``action(("op", constant("a"), ...))`` (plasp's grounding)."""
    inner = ", ".join([f'"{op}"'] + [f'constant("{a}")' for a in args])
    return f"action(({inner}))"


def _positive_plan_block(pid, plan, horizon):
    """A positive plan: fix the plan, and let rest run to ``horizon``.
    """
    if not plan:
        raise ValueError(f"whitelist plan '{pid}' is empty")
    length = len(plan)
    if horizon < length:
        raise ValueError(
            f"horizon {horizon} for whitelist plan '{pid}' is smaller than its "
            f"length {length}"
        )
    lines = [
        f"% path {pid}: positive example -- preserve, complete to goal by step {horizon}",
        f"positive_example({pid}).",
        f"horizon({pid},{horizon}).",
    ]
    for step, (op, args) in enumerate(plan, start=1):
        lines.append(f"occurs({_ground_action(op, args)},{step},{pid}).")
    return lines


def _negative_plan_block(pid, plan):
    """A negative plan: fix the prefix and forbid the last action.

    The last action must be inapplicable in the state reached at step |prefix|
    (read off ``holds`` under the repaired domain); the prefix must stay
    applicable, so the forbidden action is the first inapplicable one. The
    horizon is the prefix length (no completion, no goal).
    """
    if not plan:
        raise ValueError(f"negative plan '{pid}' is empty")
    prefix, (fop, fargs) = plan[:-1], plan[-1]
    length = len(prefix)
    forbidden = _ground_action(fop, fargs)
    lines = [
        f"% path {pid}: negative example -- forbid the last action at step {length}",
        f"negative_example({pid}).",
        f"horizon({pid},{length}).",
    ]
    for step, (op, args) in enumerate(prefix, start=1):
        lines.append(f"occurs({_ground_action(op, args)},{step},{pid}).")
    lines.append(
        f":- holds(Variable, Value, {length}, {pid}) : "
        f"applied_precondition({forbidden}, Variable, Value)."
    )
    return lines


def render_multi_plan_program(positive_plan_files, negative_plan_files, positive_horizons):
    """Return the ASP text for all per-plan paths.

    Plan ids are ``w1, w2, ...`` for positive examples and ``b1, b2, ...`` for
    negative examples; ids are opaque and only need to be unique.
    """
    if len(positive_horizons) < len(positive_plan_files):
        raise ValueError(
            "need one horizon per positive plan: got "
            f"{len(positive_horizons)} horizon(s) for {len(positive_plan_files)} "
            "positive plan(s) (pass --horizon h1 h2 ... matching "
            "--partial-plan w1 w2 ...)"
        )
    lines = []
    for i, (path, horizon) in enumerate(
        zip(positive_plan_files, positive_horizons), start=1
    ):
        lines.extend(_positive_plan_block(f"w{i}", _parse_positive_example(path), horizon))
        lines.append("")
    for i, path in enumerate(negative_plan_files, start=1):
        lines.extend(_negative_plan_block(f"b{i}", _parse_negative_example(path)))
        lines.append("")
    return "\n".join(lines) + "\n"
