# Benchmarks Structure and Usage

This directory contains the benchmark suites used by PlanPilot:

- blocks
- rovers
- satellite
- transport

Each domain directory follows the same layout:

- common-problems/
- to-solve/
- to-forbid/ (when available)
- horizons.txt

## 1) common-problems

Contains the problem instances, usually named:

- p1.pddl
- p2.pddl
- ...
- p10.pddl

Index mapping rule:

- The i-th broken domain file must be run with the i-th problem file.
- Example: broken domain ".../domain7.pddl" must be run with "common-problems/p7.pddl".

## 2) to-solve

Used for tasks where repairs should make intended plans executable/solvable.

Contains:

- broken-domains/
  - max-repairs-1/
  - max-repairs-2/
  - max-repairs-3/
- white-list-plans/
  - sas_plan-1
  - ...
  - sas_plan-10
- domain log file (for example: blockslog-to-solve.txt, roverslog-to-solve.txt, etc.)

Meaning:

- max-repairs-k stores broken variants designed for a run with --max-repairs k.
- white-list plan i corresponds to problem pi and broken domain i.

## 3) to-forbid

Used for tasks where repairs should forbid unintended plans.

Contains:

- broken-domains/
  - max-repairs-1/
- black-list-plans/
  - sas_plan-1
  - ...
  - sas_plan-10
- domain log file (for example: transportlog-to-forbid.txt, satellitelog-forbidden.txt, etc.)

Meaning:

- black-list plan i corresponds to problem pi and broken domain i.
- In these benchmarks, max-repairs-1 is typically used.

## 4) horizons

Per-problem horizons are defined in:

- horizons.txt

Use the horizon for the matching problem index.

Example:

- Problem 4 -> read "horizon: ..." under "Problem 4" in horizons.txt.

## 5) How to Run


### A) To-solve run (with white-list plan)

```bash
./planpilot.sif \
  -i benchmarks/<domain>/common-problems/pX.pddl \
  -d benchmarks/<domain>/to-solve/broken-domains/max-repairs-K/<domain>X.pddl \
  --encoding exact \
  --horizon Y \
  --domain-repair \
  --max-repairs K \
  --partial-plan benchmarks/<domain>/to-solve/white-list-plans/sas_plan-X
```

Where:

- X = problem/domain index (1..10)
- K = repair budget (1, 2, or 3 depending on the benchmark set)
- Y = horizon for problem X from horizons.txt


## 6) Naming Conventions

- Domain file names inside broken-domains usually follow: <domain><index>.pddl
  - examples: blocks5.pddl, rovers1.pddl, satellite10.pddl, transport3.pddl
- Plans follow:
  - white list: sas_plan-X
  - black list: sas_plan-X


