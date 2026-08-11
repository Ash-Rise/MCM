# Task 3 Emergency Dispatch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible Task 3 experiment that compares the selected routine B policy with incident-aware B dispatch over all ten incident zones and a duration curve.

**Architecture:** Extend the existing future-loss calculation with an optional time-varying zone-rate multiplier, then keep incident generation and Task 3 aggregation in a focused experiment module. Each replication generates one call stream and runs both policies against it.

**Tech Stack:** Python 3.13, NumPy, pandas, SciPy, `unittest`, existing discrete-event simulator.

---

### Task 1: Time-varying forecast intensity

**Files:**
- Modify: `src/ambulance_model.py`
- Modify: `tests/test_ambulance_model.py`

- [ ] Write a failing test that passes a zone-rate callback into `cumulative_response_losses` and verifies that multiplying one zone's rate changes only the weighted loss calculation.
- [ ] Run `python -m unittest tests.test_ambulance_model -v` and confirm the test fails because the callback is not accepted.
- [ ] Add an optional `rate_multiplier(future_min)` callback to `cumulative_response_loss`, `cumulative_response_losses`, `_choose_b`, and `simulate`; default to an all-ones vector so Task 2 results remain unchanged.
- [ ] Run the test module and the full suite; expect all tests to pass.

### Task 2: Incident call generation and paired metrics

**Files:**
- Create: `src/run_emergency_experiments.py`
- Create: `tests/test_emergency_experiments.py`

- [ ] Write failing tests for worst-window bounds, reproducible extra-NHPP generation, exact zone/interval membership, and incident-window metric filtering.
- [ ] Run `python -m unittest tests.test_emergency_experiments -v` and confirm failure because the module is absent.
- [ ] Implement `worst_start_hour`, `incident_rate_multiplier`, `generate_incident_calls`, `incident_queue_statistics`, and `summarize_incident` with fixed `WARMUP_DAYS=30`.
- [ ] Add a paired replication worker that runs `B_N` and `B_E` on the same calls with `beta=4`, `delta=2`.
- [ ] Run the new tests and full suite; expect all tests to pass.

### Task 3: Full Task 3 experiment

**Files:**
- Modify: `src/run_emergency_experiments.py`
- Create: `results/task-3/replicates.csv`
- Create: `results/task-3/summary.csv`
- Create: `results/task-3/paired_effects.csv`
- Create: `results/task-3/scenarios.csv`

- [ ] Freeze the duration grid and replication seeds as module constants and validate that every zone-duration-seed combination has exactly two policy rows.
- [ ] Run `python src/run_emergency_experiments.py --project-root . --workers 11` from the solution root.
- [ ] Check zero stderr, finite metrics, paired call counts, and hard constraints (`max_daily_dispatches_per_ambulance <= 12`).
- [ ] Compute 95% t intervals and paired `B_E-B_N` effects without selecting the incident zone after seeing a single replication.

### Task 4: Analysis and figures

**Files:**
- Modify: `analysis/modeling-report.md`
- Modify: `analysis/terminology.md`
- Modify: `src/generate_figures.py`

- [ ] Replace the provisional Task 3 boundary section with the frozen demand, dispatch, observation-window, and evaluation equations.
- [ ] Add raw incident-load, process duration-zone, and result paired-effect figures using the generated CSV files.
- [ ] Generate SVG, 300-DPI PNG, and grayscale previews, then run the strict figure checks for `q1 q2 q3`.
- [ ] Re-run all tests and request independent P2 only after code, results, figures, and the reproduction manifest are frozen.
