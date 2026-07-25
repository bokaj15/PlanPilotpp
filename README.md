# PlanPilot — Domain Repair

This project builds on PlanPilot (Gnad et al. KR 2025; [link to repo](https://github.com/abcorrea/planpilot)), adding a **domain-repair** mode to fix a domain that is _broken_ (missing precondition, missing effect, ...).

---
## Build

```bash
apptainer build planpilot.sif Apptainer.planpilot
```

## Flags

#### (no flag)

Runs the normal PlanPilot behaviour.

#### `--domain-repair`

Enters domain-repair mode. Skips the [Fast Downward](https://www.fast-downward.org/latest/) translator and runs
`plasp` (Gebser et al. LPNMR 2011; Dimopoulos et al. TPLP 2019; [link to
repo](https://github.com/potassco/plasp)) directly on the PDDL.

With `--domain-repair` and nothing else, the default repair set is applied:

- **add positive effects** (`add_pos_eff`)
- **delete positive preconditions** (`del_pos_pre`)

and, if the domain contains negative preconditions, additionally:

- **delete negative preconditions** (`del_neg_pre`)
- **add negative effects** (`add_neg_eff`)


#### `--max-repairs <N|min>`

Upper bound on how many repairs may be enabled at once. Default: `1`.

Pass `min` instead of a number to minimize the total repair cost (default cost 
is `1` for each repair type). This solves directly with `clingo` ([link to repo](https://github.com/potassco/clingo)) instead of `fasb` (Fichte et al. AAAI 2022; [link to repo](https://github.com/drwadu/fasb)), and
enumerates up to `--enum-opt-sols` optimal models (default 10).

#### `--enum-opt-sols <N>`

Only valid together with `--max-repairs min`. Maximum number of (possibly
tied) optimal models `clingo` enumerates. Default: `10`. Pass `0` to enumerate
all optimal solutions with respect to repair cost.

#### `--repair-weights <TYPE=WEIGHT> [<TYPE=WEIGHT> ...]`

Only valid together with `--max-repairs min`. Sets a per-repair-type cost used
by the cost-minimizing encoding; any type not listed keeps the default cost of
`1`. A repair type covers both polarities, e.g. `add_precondition` applies
whether the added precondition is positive or negative. Valid types:

- **`add_precondition`** — covers `add_pos_pre` and `add_neg_pre`.
- **`delete_precondition`** — covers `del_pos_pre` and `del_neg_pre`.
- **`add_effect`** — covers `add_pos_eff` and `add_neg_eff`.
- **`delete_effect`** — covers `del_pos_eff` and `del_neg_eff`.

Example:

```bash
--max-repairs min --repair-weights add_precondition=1 delete_effect=3
```

#### `--partial-plan <file>`

Taken from PlanPilot (minimal change). Includes a plan as constraints that must
stay applicable. The domain is repaired (with the default candidates: add
effects, delete preconditions) so that plan becomes applicable. Its role changes
when combined with `--negative-example`. See *Combinations* below.

#### `--negative-example <file>`

A plan whose last action must become inapplicable. The preceding actions let us infer
the state in which that last action should be forbidden. A negative plan can only be satisfied by
adding preconditions, so those are the candidates generated for it.

#### `--repair-candidates <kind> [<kind> ...]`

Explicitly selects which repair candidates to generate, overriding the
defaults. Each candidate is `{add,del}_{pos,neg}_{pre,eff}`:

- **`add_pos_pre`** — add positive preconditions.
- **`add_neg_pre`** — add negative preconditions.
- **`del_pos_pre`** — delete positive preconditions.
- **`del_neg_pre`** — delete negative preconditions.
- **`add_pos_eff`** — add positive effects.
- **`add_neg_eff`** — add negative effects.
- **`del_pos_eff`** — delete positive effects.
- **`del_neg_eff`** — delete negative effects.

---

## Combinations

#### `--negative-example <file>` + `--partial-plan <file>`

Repair the domain so the negative plan becomes inapplicable, while the partial
plan must stay applicable. The repair focuses on forbidding
the negative plan, not on making the partial plan applicable.

#### `--negative-example <file>` + `--partial-plan <file>` + `--repair-candidates add_pos_eff del_pos_pre`

Repair the domain so the negative plan becomes inapplicable and the positive
plan applicable at the same time.

#### Summary
- **`--domain-repair` alone** → add effects and delete preconditions to look for a solution.
- **`--partial-plan` alone** → repair the domain so that plan becomes applicable.
- **`--negative-example` + `--partial-plan`** → the partial plan is preserved, the domain is repaired only to make the negative plan inapplicable.
- To make the negative plan inapplicable and the positive plan applicable together,
  you must ask for it explicitly with `--repair-candidates`.

---

## Example 

The domain and problem are in `benchmarks/logistics/`:

- `logistics.pddl` — the domain (deliberately breakable, see below).
- `prob01.pddl` — the problem.
- `positive-plan` — a positive example plan, supplied via `--partial-plan`.
- `negative-plan` — a plan up to the first action that should be inapplicable,
  supplied via `--negative-example`.

### Breaking the domain

You can "break" logistics by removing the `(at ?pkg ?loc)` precondition of
`LOAD-TRUCK`. Without it, a package can be loaded into a truck it is not
co-located with ("remotely charging" the package). The domain-repair approach
recovers the missing precondition. Providing the negative plan should be enough
to repair it by adding the precondition back.

Also, you can remove the `(in ?obj ?truck)` effect from `LOAD-TRUCK`.
Running `--domain-repair`, or passing the `positive-plan` file via
`--partial-plan`, lets you see the repairs.

---

## How to run

### 1. Plain repair

```bash
./planpilot.sif \
  -i benchmarks/logistics/prob01.pddl \
  -d benchmarks/logistics/logistics.pddl \
  --encoding bounded --horizon 8 \
  --domain-repair --max-repairs 1
```

### 2. Repair a positive plan

```bash
./planpilot.sif \
  -i benchmarks/logistics/prob01.pddl \
  -d benchmarks/logistics/logistics.pddl \
  --encoding bounded --horizon 8 \
  --domain-repair --max-repairs 1 \
  --partial-plan benchmarks/logistics/positive-plan
```

### 3. Repair a negative plan (forbid the innaplicable action)

```bash
./planpilot.sif \
  -i benchmarks/logistics/prob01.pddl \
  -d benchmarks/logistics/logistics.pddl \
  --encoding bounded --horizon 8 \
  --domain-repair --max-repairs 1 \
  --negative-example benchmarks/logistics/negative-plan
```

### 4. Negative + positive plan (repair the negative plan, preserve positive plan)

```bash
./planpilot.sif \
  -i benchmarks/logistics/prob01.pddl \
  -d benchmarks/logistics/logistics.pddl \
  --encoding bounded --horizon 8 \
  --domain-repair --max-repairs 1 \
  --partial-plan benchmarks/logistics/positive-plan \
  --negative-example benchmarks/logistics/negative-plan
```

### 5. Repair negative and positive plan at the same time

```bash
./planpilot.sif \
  -i benchmarks/logistics/prob01.pddl \
  -d benchmarks/logistics/logistics.pddl \
  --encoding bounded --horizon 8 \
  --domain-repair --max-repairs 1 \
  --partial-plan benchmarks/logistics/positive-plan \
  --negative-example benchmarks/logistics/negative-plan \
  --repair-candidates add_pos_eff del_pos_pre
```