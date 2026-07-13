# PlanPilot — Domain Repair

This project builds on PlanPilot (https://github.com/abcorrea/planpilot), adding a **domain-repair** mode to fix a domain that is _broken_ (missing precondition, missing effect, ...).

---
## Build

```bash
apptainer build planpilot.sif Apptainer.planpilot
```

## Flags

#### (no flag)

Runs the normal PlanPilot behaviour.

#### `--domain-repair`

Enters domain-repair mode. Skips the Fast Downward translator and runs
`plasp` directly on the PDDL.

With `--domain-repair` and nothing else, the default repair set is applied:

- **add positive effects** (`add_pos_eff`)
- **delete positive preconditions** (`del_pos_pre`)

and, if the domain contains negative preconditions, additionally:

- **delete negative preconditions** (`del_neg_pre`)
- **add negative effects** (`add_neg_eff`)


#### `--max-repairs <N|min>`

Upper bound on how many repairs may be enabled at once. Default: `1`.

Pass `min` instead of a number to minimize the total repair cost (default cost 
is `1` for each repair type). This solves directly with `clingo` instead of `fasb`, and
enumerates up to 10 optimal models.

#### `--partial-plan <file>`

Taken from PlanPilot (minimal change). Includes a plan as constraints that must
stay applicable. The domain is repaired (with the default candidates: add
effects, delete preconditions) so that plan becomes applicable. Its role changes
when combined with `--black-list-plan`. See *Combinations* below.

#### `--black-list-plan <file>`

A plan whose last action must become inapplicable. The preceding actions let us infer
the state in which that last action should be forbidden. A blacklist can only be satisfied by
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

#### `--black-list-plan <file>` + `--partial-plan <file>`

Repair the domain so the blacklist plan becomes inapplicable, while the partial
plan must stay applicable. The repair focuses on forbidding
the blacklist plan, not on making the partial plan applicable.

#### `--black-list-plan <file>` + `--partial-plan <file>` + `--repair-candidates add_pos_eff del_pos_pre`

Repair the domain so the blacklist plan becomes inapplicable and the whitelist
plan applicable at the same time.

#### Summary
- **`--domain-repair` alone** → add effects and delete preconditions to look for a solution.
- **`--partial-plan` alone** → repair the domain so that plan becomes applicable.
- **`--black-list-plan` + `--partial-plan`** → the partial plan is preserved, the domain is repaired only to make the blacklist plan inapplicable.
- To make the blacklist plan inapplicable and the whitelist applicable together,
  you must ask for it explicitly with `--repair-candidates`.

---

## Example 

The domain and problem are in `benchmarks/logistics/`:

- `logistics.pddl` — the domain (deliberately breakable, see below).
- `prob01.pddl` — the problem.
- `white-list-plan` — a positive example plan, supplied via `--partial-plan`.
- `black-list-plan` — a plan up to the first action that should be inapplicable,
  supplied via `--black-list-plan`.

### Breaking the domain

You can "break" logistics by removing the `(at ?pkg ?loc)` precondition of
`LOAD-TRUCK`. Without it, a package can be loaded into a truck it is not
co-located with ("remotely charging" the package). The domain-repair approach
recovers the missing precondition. Providing the blacklist plan should be enough
to repair it by adding the precondition back.

Also, you can remove the `(in ?obj ?truck)` effect from `LOAD-TRUCK`.
Running `--domain-repair`, or passing the `white-list-plan` file via
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

### 2. Repair a whitelist plan

```bash
./planpilot.sif \
  -i benchmarks/logistics/prob01.pddl \
  -d benchmarks/logistics/logistics.pddl \
  --encoding bounded --horizon 8 \
  --domain-repair --max-repairs 1 \
  --partial-plan benchmarks/logistics/white-list-plan
```

### 3. Repair a blacklist plan (forbid the innaplicable action)

```bash
./planpilot.sif \
  -i benchmarks/logistics/prob01.pddl \
  -d benchmarks/logistics/logistics.pddl \
  --encoding bounded --horizon 8 \
  --domain-repair --max-repairs 1 \
  --black-list-plan benchmarks/logistics/black-list-plan
```

### 4. Blacklist + whitelist (repair the blacklist, preserve whitelist)

```bash
./planpilot.sif \
  -i benchmarks/logistics/prob01.pddl \
  -d benchmarks/logistics/logistics.pddl \
  --encoding bounded --horizon 8 \
  --domain-repair --max-repairs 1 \
  --partial-plan benchmarks/logistics/white-list-plan \
  --black-list-plan benchmarks/logistics/black-list-plan
```

### 5. Repair blacklist and whitelist at the same time

```bash
./planpilot.sif \
  -i benchmarks/logistics/prob01.pddl \
  -d benchmarks/logistics/logistics.pddl \
  --encoding bounded --horizon 8 \
  --domain-repair --max-repairs 1 \
  --partial-plan benchmarks/logistics/white-list-plan \
  --black-list-plan benchmarks/logistics/black-list-plan \
  --repair-candidates add_pos_eff del_pos_pre
```