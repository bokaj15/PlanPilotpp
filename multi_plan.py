#! /usr/bin/env python3
"""Generate the per-plan blocks for the multiple-plans repair encoding.

Scope: one problem, N input plans (any mix of whitelist and blacklist). Each
plan becomes its own PATH ``P`` with a private timeline; all paths share the
global repair layer (``applied_*``/``enabled``) provided by
``encodings/multiple-plans-repair.lp``, so a single repair set must satisfy every
path at once.

For each plan this module emits, on a fresh path id, the per-path facts the
template consumes (it derives ``plan/1`` and ``time(0..H,P)`` from them):
  * a kind tag -- ``positive_example(P).`` or ``negative_example(P).``,
  * a horizon -- ``horizon(P, H).``, and
  * one ``occurs(action(...), step, P).`` fact per pinned action.

The kind tag decides how the path is constrained (all in the template):
  * positive example -> its pinned actions are preserved and the tail up to the
    horizon may be completed by search so the goal holds at the horizon;
  * negative example -> only its prefix runs (horizon = prefix length) and its
    last action is forced inapplicable in the state the prefix reaches. That
    block-last-action constraint names a specific action, so it is emitted here.

Positive (whitelist) files use the partial-plan format (whitespace-separated
actions delimited by ``(1)``); negative (blacklist) files use one
``(action arg1 arg2)`` per line. This module is independent of
``repair_candidates`` -- it only consumes the shared ``applied_precondition``
the encoding provides.
"""

WHITELIST_DELIMITER = "(1)"


def _parse_whitelist(path):
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


def _parse_blacklist(path):
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


def _whitelist_block(pid, plan, horizon):
    """A positive path: pin the plan, and let the tail run to ``horizon``.

    The template derives ``plan(pid)`` and ``time(0..horizon,pid)`` from the
    tag/horizon facts, gates the completion choice rule and the goal on
    ``positive_example``, so the pinned actions are preserved and the tail (if
    ``horizon`` exceeds the prefix length) is completed to reach the goal.
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


def _blacklist_block(pid, plan):
    """A negative path: pin the prefix and forbid the last action.

    The last action must be inapplicable in the state reached at step |prefix|
    (read off ``holds`` under the repaired domain); the pinned prefix must stay
    applicable, so the forbidden action is the first inapplicable one. The
    horizon is the prefix length (no completion, no goal).
    """
    if not plan:
        raise ValueError(f"blacklist plan '{pid}' is empty")
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


def render_multi_plan_program(whitelist_files, blacklist_files, whitelist_horizons):
    """Return the ASP text for all per-plan paths (whitelists then blacklists).

    Path ids are ``w1, w2, ...`` for whitelists and ``b1, b2, ...`` for
    blacklists; ids are opaque and only need to be unique. ``whitelist_horizons``
    gives one horizon per whitelist file, in the same order.
    """
    if len(whitelist_horizons) < len(whitelist_files):
        raise ValueError(
            "need one horizon per whitelist plan: got "
            f"{len(whitelist_horizons)} horizon(s) for {len(whitelist_files)} "
            "whitelist plan(s) (pass --horizon h1 h2 ... matching "
            "--partial-plan w1 w2 ...)"
        )
    lines = []
    for i, (path, horizon) in enumerate(
        zip(whitelist_files, whitelist_horizons), start=1
    ):
        lines.extend(_whitelist_block(f"w{i}", _parse_whitelist(path), horizon))
        lines.append("")
    for i, path in enumerate(blacklist_files, start=1):
        lines.extend(_blacklist_block(f"b{i}", _parse_blacklist(path)))
        lines.append("")
    return "\n".join(lines) + "\n"
