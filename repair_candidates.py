#! /usr/bin/env python3
"""Generate lifted domain-repair candidates from a PDDL domain.

A *repair candidate* is a single lifted edit to an operator schema. Each
candidate is emitted as an ASP fact of the form

    repair(add_precondition("load-truck", ("at", par1, par3), true)).

where
  * the operator name is the lowercased action name (matching plasp),
  * the fluent is a tuple of the predicate name plus *slot* symbols ``par1..parN``
    with ``pari`` denoting the operator's i-th parameter (declaration order,
    which is exactly the ``Xi`` plasp binds), and
  * the last argument is the polarity (``true``/``false``).

There are eight candidate kinds, ``{add,delete} x {precondition,effect} x
{positive,negative}``. Which candidates are emitted is controlled by the
``candidates`` argument; by default the positive-side "relaxing" candidates are
always produced (add positive effects, delete positive preconditions), and the
negative-side candidates (delete negative preconditions, add negative effects)
are added automatically when the domain has negative preconditions -- which is
what is needed to make a task solvable or an input plan applicable.

The candidate *sources* are:
  * add  positive precondition -> any predicate, type-restricted to the
                                  operator's parameters
  * add  negative precondition -> same pool, negative polarity
  * del  positive precondition -> the operator's current positive preconditions
  * del  negative precondition -> the operator's current negative preconditions
  * add  positive effect       -> predicates appearing as a positive
                                  precondition of some operator or in the goal
  * add  negative effect       -> predicates appearing as a negative
                                  precondition of some operator or in the goal
  * del  positive effect       -> the operator's current positive effects
  * del  negative effect       -> the operator's current negative effects

Add candidates are filtered by a no-op guard: a candidate whose fluent the
operator already has at *either* polarity as an effect is skipped (same sign =
redundant, opposite sign = contradiction). Add-effect candidates draw their
fluents from *other* actions' preconditions (or the goal); a fluent that is
already a same-polarity precondition of the operator is *not* skipped, since the
correct repair may be to delete it from the preconditions and add it as an
effect (e.g. blocksworld put-down: drop the spurious ``handempty`` precondition
and add the missing ``handempty`` effect).
"""

import os
import sys
from itertools import product

# The repo vendors Fast Downward's PDDL parser under translate/. Put it on the
# path so we can reuse the same lifted schema plasp is built on, instead of
# adding a second parser dependency.
_TRANSLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "translate")
if _TRANSLATE_DIR not in sys.path:
    sys.path.insert(0, _TRANSLATE_DIR)

import pddl  # noqa: E402
from pddl_parser import pddl_file  # noqa: E402


# All repair candidates, and the subset emitted when nothing else is requested.
CANDIDATES = (
    "add_pos_pre",
    "add_neg_pre",
    "del_pos_pre",
    "del_neg_pre",
    "add_pos_eff",
    "add_neg_eff",
    "del_pos_eff",
    "del_neg_eff",
)

# No input / positive plan only: relax the operator so the task becomes
# solvable or the input plan applicable. The positive-side candidates are always
# emitted by default: add positive effects (to achieve things) and delete
# positive preconditions (to unblock).
DEFAULT_POSITIVE_CANDIDATES = (
    "add_pos_eff",
    "del_pos_pre",
)

# Negative-side counterparts. These are only *meaningful* when the domain has
# negative preconditions -- delete such a precondition to unblock, or add a
# negative effect to establish one -- so by default they are emitted only when
# the domain actually contains a negative precondition (auto-detected).
DEFAULT_NEGATIVE_CANDIDATES = (
    "del_neg_pre",
    "add_neg_eff",
)

# Maps each candidate key to the repair type used by its repair(...) facts.
REPAIR_TYPES = {
    "add_pos_pre": "add_precondition",
    "add_neg_pre": "add_precondition",
    "del_pos_pre": "delete_precondition",
    "del_neg_pre": "delete_precondition",
    "add_pos_eff": "add_effect",
    "add_neg_eff": "add_effect",
    "del_pos_eff": "delete_effect",
    "del_neg_eff": "delete_effect",
}

def _build_supertype_map(task):
    """Map each type name to its immediate base type name."""
    supers = {}
    for t in task.types:
        supers[t.name.lower()] = (t.basetype_name or "").lower()
    return supers


def _is_subtype(sub, sup, supers):
    """True iff ``sub`` is ``sup`` or a (transitive) subtype of it."""
    sub, sup = sub.lower(), sup.lower()
    seen = set()
    while sub and sub not in seen:
        if sub == sup:
            return True
        seen.add(sub)
        sub = supers.get(sub, "")
    return sub == sup


def _collect_literals(condition):
    """Flatten a STRIPS condition into (predicate, args, negated) triples.

    Handles conjunctions, plain/negated atoms and truth. Anything richer
    (disjunction, quantifiers) is skipped with a warning on stderr.
    """
    result = []

    def visit(cond):
        if isinstance(cond, pddl.conditions.Truth):
            return
        if isinstance(cond, pddl.conditions.Conjunction):
            for part in cond.parts:
                visit(part)
            return
        if isinstance(cond, pddl.conditions.Literal):
            result.append((cond.predicate.lower(), tuple(cond.args), cond.negated))
            return
        print(
            f"warning: skipping non-STRIPS condition part {type(cond).__name__}",
            file=sys.stderr,
        )

    visit(condition)
    return result


def _param_slots(action):
    """Return (name->slot) map and list of (slot, type) for the parameters.

    Slots are 1-based positions matching plasp's ``Xi`` binding.
    """
    name_to_slot = {}
    slot_types = []
    for i, par in enumerate(action.parameters, start=1):
        name_to_slot[par.name] = i
        slot_types.append((i, par.type_name.lower()))
    return name_to_slot, slot_types


def _render_fluent(predicate, slots):
    """Render ``("at", par1, par3)`` from a predicate name and slot indices."""
    args = "".join(f", par{s}" for s in slots)
    return f'("{predicate}"{args})'


def _repair_fact(candidate, operator, predicate, slots, polarity):
    fluent = _render_fluent(predicate, slots)
    return f'repair({candidate}("{operator}", {fluent}, {polarity})).'


def _repair_cost_rule(repair_type, cost=1):
    """Cost of each rule covering every repair fact of ``repair_type``."""
    return (
        f"repair_cost({repair_type}(Action, Variable, Value), {cost}) :- "
        f"repair({repair_type}(Action, Variable, Value))."
    )


def _action_term(operator, arity):
    """Render the lifted action term ``action(("op", X1, .., Xn))``."""
    args = "".join(f", X{i}" for i in range(1, arity + 1))
    return f'action(("{operator}"{args}))'


def _fluent_var(predicate, slots):
    """Render ``variable(("at", X1, X3))`` from a predicate name and slot indices."""
    args = "".join(f", X{s}" for s in slots)
    return f'variable(("{predicate}"{args}))'


def _ground_action(operator, args):
    """Render a ground ``action(("load-truck", constant("package1"), ...))`` term."""
    rendered = "".join(f', constant("{a}")' for a in args)
    return f'action(("{operator}"{rendered}))'


def _bridge_rule(candidate, operator, predicate, slots, polarity, arity):
    """Render the bridge rule that turns an enabled repair into an applied edit.

    Each candidate feeds the predicate the repair-variant horizon encoding reads:
      * add_precondition    -> added_precondition/3
      * delete_precondition -> deleted_precondition/3
      * add_effect          -> added_effect/3
      * delete_effect       -> deleted_postcondition/4 (effect(unconditional))

    The positive ``action(...)`` body literal binds the operator variables
    (keeping the rule safe) and scopes the edit to that operator's ground
    instances; the ``enabled(...)`` guard switches it on.
    """
    act = _action_term(operator, arity)
    var = _fluent_var(predicate, slots)
    val = f"value({var}, {polarity})"
    fluent = _render_fluent(predicate, slots)
    body = f'action({act}), enabled({candidate}("{operator}", {fluent}, {polarity}))'
    if candidate == "add_precondition":
        head = f"added_precondition({act}, {var}, {val})"
    elif candidate == "delete_precondition":
        head = f"deleted_precondition({act}, {var}, {val})"
    elif candidate == "add_effect":
        head = f"added_effect({act}, {var}, {val})"
    elif candidate == "delete_effect":
        head = f"deleted_postcondition({act}, effect(unconditional), {var}, {val})"
    else:
        raise ValueError(f"unknown repair candidate term: {candidate}")
    return f"{head} :- {body}."


def _type_valid_assignments(predicate, slot_types, supers, allow_repeated_slots=False):
    """Yield slot-index tuples assigning parameters to a predicate's arguments.

    A parameter may fill an argument iff their types are compatible, i.e. one is
    a subtype of the other (equivalently, their object sets can overlap). This
    covers both a parameter that is more specific than the argument (e.g. a
    ``truck`` parameter filling a ``vehicle`` argument) and one that is more
    general (e.g. a ``vehicle`` parameter filling a ``truck`` argument, which is
    meaningful for the ground instances where the vehicle happens to be a
    truck). Parameters whose type is disjoint from the argument's are excluded.
    By default, assignments that map two distinct predicate arguments to the
    same parameter (repeated slots, e.g. ``("in", par1, par1)``) are skipped,
    since they are almost always vacuous.
    """
    choices = []
    for arg in predicate.arguments:
        arg_type = arg.type_name.lower()
        opts = [
            slot
            for (slot, ptype) in slot_types
            if _is_subtype(ptype, arg_type, supers) or _is_subtype(arg_type, ptype, supers)
        ]
        if not opts:
            return  # this predicate cannot be instantiated over the parameters
        choices.append(opts)
    for combo in product(*choices):
        if not allow_repeated_slots and len(set(combo)) != len(combo):
            continue  # skip repeated-slot assignments
        yield combo


def _has_negative_preconditions(task):
    """True iff some operator in the task has a negative precondition."""
    for action in task.actions:
        for (_pred, _args, negated) in _collect_literals(action.precondition):
            if negated:
                return True
    return False


def generate_repair_candidates(domain, instance, candidates=None, add_repair_cost=False):
    """Return a list of ASP ``repair(...)`` fact lines for the given domain.

    ``candidates`` is an iterable of candidate keys (see ``CANDIDATES``). When
    omitted, a default set is chosen from the domain: the positive-side relaxing
    candidates (``DEFAULT_POSITIVE_CANDIDATES``) always, plus the negative-side
    candidates (``DEFAULT_NEGATIVE_CANDIDATES``) when the domain has negative
    preconditions.

    ``add_repair_cost`` emits one cost rule per enabled repair
    type (for ``--max-repairs min``, where repairs are chosen by minimizing
    total cost instead of a fixed cardinality bound).
    """
    explicit = candidates is not None
    if explicit:
        enabled = set(candidates)
        unknown = enabled - set(CANDIDATES)
        if unknown:
            raise ValueError(f"unknown repair candidates: {sorted(unknown)}")

    task = pddl_file.open(domain_filename=domain, task_filename=instance)

    if not explicit:
        # Auto-detect: add the negative-side candidates only when the domain
        # actually has negative preconditions (otherwise they emit nothing).
        enabled = set(DEFAULT_POSITIVE_CANDIDATES)
        if _has_negative_preconditions(task):
            enabled |= set(DEFAULT_NEGATIVE_CANDIDATES)

    supers = _build_supertype_map(task)
    # Skip the built-in equality predicate injected by the parser.
    predicates_by_name = {
        p.name.lower(): p for p in task.predicates if p.name.lower() != "="
    }

    # Predicate symbols mentioned as positive atoms in the goal; these seed the
    # add-positive-effect pool together with the domain's positive preconditions.
    goal_preds = {
        pred for (pred, _args, negated) in _collect_literals(task.goal) if not negated
    }
    # Predicate symbols mentioned as negative atoms in the goal; symmetric seed
    # for the add-negative-effect pool.
    neg_goal_preds = {
        pred for (pred, _args, negated) in _collect_literals(task.goal) if negated
    }

    # Predicate symbols appearing as a positive precondition of *some* operator.
    # Together with the goal predicates these form the add-positive-effect pool:
    # a fluent worth establishing is one that some action requires or the goal
    # needs, even if the operator being repaired does not itself mention it.
    pos_pre_preds = set()
    neg_pre_preds = set()
    for action in task.actions:
        for (pred, _args, negated) in _collect_literals(action.precondition):
            if negated:
                neg_pre_preds.add(pred)
            else:
                pos_pre_preds.add(pred)
    add_pos_eff_pool = pos_pre_preds | goal_preds
    # Symmetric negative pool: a fluent worth *deleting* is one that some action
    # requires to be false (negative precondition) or the goal needs false.
    add_neg_eff_pool = neg_pre_preds | neg_goal_preds

    lines = []

    if add_repair_cost:
        # One cost rule per enabled repair type.
        enabled_repair_types = sorted({REPAIR_TYPES[c] for c in enabled})
        if enabled_repair_types:
            lines.append("% unit cost for each enabled repair type")
            lines.extend(_repair_cost_rule(rt) for rt in enabled_repair_types)
            lines.append("")

    for action in task.actions:
        operator = action.name.lower()
        name_to_slot, slot_types = _param_slots(action)
        arity = len(action.parameters)

        pre = _collect_literals(action.precondition)
        pos_pre = [(p, a) for (p, a, neg) in pre if not neg]
        neg_pre = [(p, a) for (p, a, neg) in pre if neg]

        eff = []
        for e in action.effects:
            if isinstance(e.condition, pddl.conditions.Truth) and isinstance(
                e.literal, pddl.conditions.Literal
            ):
                eff.append((e.literal.predicate.lower(), tuple(e.literal.args), e.literal.negated))
        pos_eff = [(p, a) for (p, a, neg) in eff if not neg]
        neg_eff = [(p, a) for (p, a, neg) in eff if neg]

        def slots_of(args):
            return tuple(name_to_slot[a] for a in args)

        # Existing (predicate, slots) sets, ignoring polarity. An add candidate
        # is skipped when the fluent already appears in the operator at *any*
        # polarity: same sign would be a no-op, opposite sign would be a clash
        # (an inversion that both kills the action via the uniqueness constraint
        # and duplicates what the delete candidate already offers).
        have_pos_pre = {(p, slots_of(a)) for (p, a) in pos_pre}
        have_neg_pre = {(p, slots_of(a)) for (p, a) in neg_pre}
        have_pre = have_pos_pre | have_neg_pre
        have_eff = {(p, slots_of(a)) for (p, a) in pos_eff}
        have_eff |= {(p, slots_of(a)) for (p, a) in neg_eff}

        op_lines = []

        # Emit a candidate as its repair fact plus the bridge rule that applies
        # it when enabled. They are adjacent for readability; order is irrelevant.
        def emit(candidate, predicate, slots, polarity):
            op_lines.append(_repair_fact(candidate, operator, predicate, slots, polarity))
            op_lines.append(
                _bridge_rule(candidate, operator, predicate, slots, polarity, arity)
            )

        # --- ADD precondition: any predicate, type-restricted to the params ---
        def add_pre(polarity, key):
            for pred_name, predicate in sorted(predicates_by_name.items()):
                for slots in _type_valid_assignments(predicate, slot_types, supers):
                    if (pred_name, slots) in have_pre:
                        continue  # no-op or clash with an existing precondition
                    emit(key, pred_name, slots, polarity)

        if "add_pos_pre" in enabled:
            add_pre("true", "add_precondition")
        if "add_neg_pre" in enabled:
            add_pre("false", "add_precondition")

        # --- DELETE precondition: the operator's current preconditions ---
        if "del_pos_pre" in enabled:
            for (p, a) in pos_pre:
                emit("delete_precondition", p, slots_of(a), "true")
        if "del_neg_pre" in enabled:
            for (p, a) in neg_pre:
                emit("delete_precondition", p, slots_of(a), "false")

        # --- ADD effect: predicates from positive preconditions + goal ---
        if "add_pos_eff" in enabled:
            for pred_name in sorted(add_pos_eff_pool):
                predicate = predicates_by_name.get(pred_name)
                if predicate is None:
                    continue
                for slots in _type_valid_assignments(predicate, slot_types, supers):
                    if (pred_name, slots) in have_eff:
                        continue  # no-op or clash with an existing effect
                    # Note: a fluent that is already a positive precondition is
                    # NOT skipped -- the correct repair may be to delete it from
                    # the preconditions and add it as an effect (e.g. blocks
                    # put-down: drop the spurious handempty precondition and add
                    # the missing handempty effect).
                    emit("add_effect", pred_name, slots, "true")

        # --- ADD negative effect: predicates from negative preconditions ---
        if "add_neg_eff" in enabled:
            for pred_name in sorted(add_neg_eff_pool):
                predicate = predicates_by_name.get(pred_name)
                if predicate is None:
                    continue
                for slots in _type_valid_assignments(predicate, slot_types, supers):
                    if (pred_name, slots) in have_eff:
                        continue  # no-op or clash with an existing effect
                    emit("add_effect", pred_name, slots, "false")

        # --- DELETE effect: the operator's current effects ---
        if "del_pos_eff" in enabled:
            for (p, a) in pos_eff:
                emit("delete_effect", p, slots_of(a), "true")
        if "del_neg_eff" in enabled:
            for (p, a) in neg_eff:
                emit("delete_effect", p, slots_of(a), "false")

        if op_lines:
            lines.append(f"% repair candidates for {operator}")
            lines.extend(op_lines)
            lines.append("")

    return lines


def render_repair_program(domain, instance, candidates=None, add_repair_cost=False):
    """Return the text of the generated repair candidate facts.

    Contains the domain-specific ``repair(...)`` candidate facts together with
    their bridge rules (one per candidate), plus one generic unit-cost rule per
    enabled repair type when ``add_repair_cost`` is set. The static part of the
    repair layer -- the ``applied_*`` indirection and the ``{enabled(R) :
    repair(R)}`` choice plus the ``#show`` directive -- lives in the
    repair-variant horizon encoding (``encodings/*-sequential-horizon-repair.lp``)
    written before these facts.
    """
    lines = generate_repair_candidates(domain, instance, candidates, add_repair_cost)
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Blacklist plan: a plan whose last action is applicable in the (broken) domain
# but should not be. We replay the prefix to reach the state just before that
# action, then forbid any repair under which the action stays applicable there.
# --------------------------------------------------------------------------- #


def _parse_plan_file(path):
    """Parse a plan file into an ordered list of ``(operator, [args])``.

    Accepts one PDDL action per line, e.g. ``(load-truck package1 truck1 c1)``.
    Blank lines and ``;`` comment lines (such as the trailing cost line) are
    ignored. Names are lower-cased to match plasp's grounding.
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


def generate_blacklist_program(domain, instance, blacklist_file):
    """Return ASP lines that turn the blacklist plan into a non-solution.

    The last line of ``blacklist_file`` is the *forbidden* action; the preceding
    lines are its *prefix*. The prefix is pinned into the trace (the same
    integrity-constraint form used for a partial plan), so the solver replays it
    under the *repaired* domain and materialises the reached state as
    ``holds(., |prefix|)``. The emitted constraint then forbids any repair under
    which the forbidden action's applied preconditions all hold in that state --
    i.e. it forces the forbidden action to be inapplicable there.

    Because the whole prefix is pinned, every prefix action must remain
    applicable under the repair, so the forbidden action is guaranteed to be the
    *first* inapplicable action (cf. Lin, Grastien, and Bercher 2023). Reading
    the applicability off ``holds`` (instead of a precomputed snapshot) is what
    lets effect repairs -- e.g. ``delete_effect`` -- affect the outcome.

    ``blacklist_active`` is emitted to switch off the goal constraint in the
    repair encoding: a negative example only requires the prefix to run and the
    last action to be blocked, not the goal to be reached. Runs should therefore
    use ``horizon = |prefix|``.

    Requires the repair-variant encoding (it references ``applied_precondition``
    and ``holds``).
    """
    task = pddl_file.open(domain_filename=domain, task_filename=instance)
    schemas = {a.name.lower(): a for a in task.actions}

    plan = _parse_plan_file(blacklist_file)
    if not plan:
        raise ValueError(f"blacklist plan '{blacklist_file}' is empty")
    prefix, (fop, fargs) = plan[:-1], plan[-1]

    def check(op, args, what):
        schema = schemas.get(op)
        if schema is None:
            raise ValueError(f"blacklist plan uses unknown action '{op}'")
        if len(args) != len(schema.parameters):
            raise ValueError(
                f"{what} '{op}' expects {len(schema.parameters)} "
                f"arguments, got {len(args)}"
            )

    check(fop, fargs, "forbidden action")
    forbidden = _ground_action(fop, fargs)

    lines = [
        "% blacklist: enforce the prefix and forbid the last action from being",
        "% applicable in the state the prefix reaches. The goal is dropped for a",
        "% blacklist run (block only) via blacklist_active. Run with horizon = |prefix|.\n",
        "blacklist_active.",
    ]

    # Pin every prefix action to its step, exactly like a partial plan. Under the
    # repaired domain these must stay applicable, which makes the forbidden
    # action the first inapplicable one.
    for step, (op, args) in enumerate(prefix, start=1):
        check(op, args, "blacklist action")
        lines.append(f":- not occurs({_ground_action(op, args)}, {step}).")

    # Inconsistent if all the forbidden action's applied preconditions hold in
    # the reached state at step |prefix|; the only way out is a repair that makes
    # one of them fail there.
    lines.append(
        f":- holds(Variable, Value, {len(prefix)}) : "
        f"applied_precondition({forbidden}, Variable, Value)."
    )
    return lines


def render_blacklist_program(domain, instance, blacklist_file):
    """Return the text of the generated blacklist program (see above)."""
    return "\n".join(generate_blacklist_program(domain, instance, blacklist_file)) + "\n"


def blacklist_candidates(domain, instance, candidates=None, union_with_relaxing=False):
    """Return the candidate set to generate for a blacklist run.

    With the prefix pinned into the trace, the forbidden action's applicability
    is read off the reached state ``holds(., |prefix|)``, so a blacklist can be
    satisfied two ways: adding a precondition that is false in that state
    (Case 2), or deleting an upstream positive effect so an existing
    precondition loses its support (Case 3). The constraining candidates are
    therefore ``add_pos_pre`` and ``del_pos_eff`` always, plus ``add_neg_pre``
    when the domain has negative preconditions (so the forced precondition may
    be negative).

    Two modes:
      * ``union_with_relaxing=False`` (default, e.g. a blacklist alone or a
        blacklist guarded by a partial plan): emit *only* the constraining
        add-precondition / delete-effect candidates. Relaxing candidates cannot
        satisfy the blacklist, and a partial plan is only a guard that must stay
        runnable under the blocking repairs -- it does not trigger relaxing
        repairs of its own -- so they would just be noise.
      * ``union_with_relaxing=True`` (only when the user explicitly asks for
        relaxing candidates via ``--repair-candidates``): union the constraining
        candidates with the requested relaxing ones, so the domain can be
        repaired to block the blacklist *and* make an otherwise-inapplicable
        whitelist applicable. The relaxing base is ``candidates`` if given, else
        the same default :func:`generate_repair_candidates` picks (positive
        relaxing candidates, plus the negative ones when the domain has negative
        preconditions).

    Returns a sorted list.
    """
    task = pddl_file.open(domain_filename=domain, task_filename=instance)
    has_neg = _has_negative_preconditions(task)

    constraining = {"add_pos_pre", "del_pos_eff"}
    if has_neg:
        constraining.add("add_neg_pre")

    if not union_with_relaxing:
        return sorted(constraining)

    if candidates is None:
        relaxing = set(DEFAULT_POSITIVE_CANDIDATES)
        if has_neg:
            relaxing |= set(DEFAULT_NEGATIVE_CANDIDATES)
    else:
        relaxing = set(candidates)
    return sorted(constraining | relaxing)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate lifted domain-repair candidates from a PDDL domain."
    )
    parser.add_argument("domain", nargs="?", help="Path to the PDDL domain file.")
    parser.add_argument("instance", nargs="?", help="Path to the PDDL instance file.")
    parser.add_argument(
        "-c",
        "--candidates",
        nargs="+",
        choices=CANDIDATES,
        help="Repair candidates to emit (default: the relaxing candidates).",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Write the full repair program to this file instead of stdout.",
    )
    parser.add_argument(
        "-b",
        "--blacklist",
        help="Instead of repair candidates, render the blacklist program for "
        "this plan file (last action is the forbidden one).",
    )
    cli = parser.parse_args()

    if cli.domain and cli.instance:
        domain_path, instance_path = cli.domain, cli.instance
    else:
        base = os.path.join(_TRANSLATE_DIR, "..", "benchmarks", "logistics")
        domain_path = os.path.join(base, "logistics.pddl")
        instance_path = os.path.join(base, "prob01.pddl")

    if cli.blacklist:
        program = render_blacklist_program(domain_path, instance_path, cli.blacklist)
    else:
        program = render_repair_program(domain_path, instance_path, cli.candidates)
    if cli.output:
        with open(cli.output, "w") as f:
            f.write(program)
    else:
        sys.stdout.write(program)
