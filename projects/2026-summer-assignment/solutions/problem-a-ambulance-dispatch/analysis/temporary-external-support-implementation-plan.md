# Temporary External Ambulance Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add accident-time external ambulances at the nearest station, quantify response and delay-penalty gains for 0-6 vehicles, generate reproducible results and figures, and update Task 3 Markdown after real outputs are frozen.

**Architecture:** Extend the existing ambulance simulator with activation-aware temporary vehicles while preserving the 12-vehicle default. Add a separate external-support experiment path that reuses the frozen Task 3 scenario calls and common random numbers. Aggregate paired results by external count without pooling across accident duration.

**Tech Stack:** Python 3, NumPy, pandas, SciPy, Matplotlib, unittest, existing Pandoc Markdown paper source.

---

### Task 1: Activation-aware temporary fleet

**Files:**
- Modify: `src/ambulance_model.py`
- Modify: `tests/test_ambulance_model.py`

- [ ] **Step 1: Write failing tests for activation and temporary sites**

Add tests that call the planned API:

```python
fleet = build_fleet(
    self.data,
    external_sites=[2, 2],
    external_activation_min=100.0,
)
self.assertEqual(len(fleet), 14)
self.assertEqual([a.site for a in fleet[-2:]], [2, 2])
self.assertTrue(all(a.external for a in fleet[-2:]))
self.assertEqual(_current_candidates(fleet, 99.0), build_fleet(self.data))
self.assertEqual(len(_current_candidates(fleet, 100.0)), 14)
```

Add a simulation test with calls immediately before and at activation time. The temporary vehicle must be absent before activation and eligible at activation.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
python -m unittest tests.test_ambulance_model.AProblemTest.test_external_ambulances_activate_at_incident_start -v
```

Expected: failure because `build_fleet` does not accept external vehicle arguments and `Ambulance` has no activation metadata.

- [ ] **Step 3: Implement the minimal fleet API**

Extend `Ambulance` with:

```python
activation_min: float = 0.0
external: bool = False
```

Extend `build_fleet` and `simulate` with optional arguments:

```python
external_sites: Iterable[int] | None = None
external_activation_min: float = 0.0
```

Append one non-reserve ambulance per external site. Update `_current_candidates`, `_known_wait`, `_predicted_zone_response`, and `cumulative_response_losses` so an external ambulance is invisible to both dispatch and forecast calculations while `state_time_min < activation_min`. Include activation times among future-loss integration breakpoints after activation.

- [ ] **Step 4: Run focused and baseline tests**

Run:

```powershell
python -m unittest tests.test_ambulance_model -v
```

Expected: all existing tests and new activation tests pass; default fleet remains 12 vehicles.

- [ ] **Step 5: Commit simulator support**

```powershell
git add -- src/ambulance_model.py tests/test_ambulance_model.py
git commit -m "feat: support incident-time external ambulances"
```

### Task 2: External-support scenarios and nearest-station mapping

**Files:**
- Modify: `src/run_emergency_experiments.py`
- Modify: `tests/test_emergency_experiments.py`

- [ ] **Step 1: Write failing tests for the placement map**

Test the planned helpers:

```python
self.assertEqual(nearest_external_sites(self.data, incident_zone=0, count=2), [0, 0])
self.assertEqual(nearest_external_sites(self.data, incident_zone=6, count=2), [2, 2])
self.assertEqual(nearest_external_sites(self.data, incident_zone=7, count=5), [3, 5, 3, 5, 3])
```

Also test invalid counts and zone indices.

- [ ] **Step 2: Verify placement tests fail**

Run:

```powershell
python -m unittest tests.test_emergency_experiments.EmergencyExperimentTest.test_nearest_external_site_mapping -v
```

Expected: import failure because `nearest_external_sites` is not implemented.

- [ ] **Step 3: Implement placement and an external worker**

Add:

```python
EXTERNAL_COUNTS = tuple(range(7))

def nearest_external_sites(data: ProblemData, incident_zone: int, count: int) -> list[int]:
    # Stable distance ordering; R8 alternates S4/S6 because they tie.
```

Add `_external_scenario_worker` that builds the same calls once, loops over `external_count=0..6`, runs strategy B with the incident multiplier, passes the temporary sites and incident-start activation time to `simulate`, and records `external_count`, `call_digest`, all incident metrics, and maximum daily dispatches.

- [ ] **Step 4: Test common calls and zero-external equivalence**

Create a small scenario test asserting all seven counts share one call digest. Compare the `external_count=0` row against the existing `B_E` worker for every metric with exact or tight floating tolerance.

- [ ] **Step 5: Run emergency tests**

```powershell
python -m unittest tests.test_emergency_experiments -v
```

Expected: all existing and new tests pass.

- [ ] **Step 6: Commit scenario support**

```powershell
git add -- src/run_emergency_experiments.py tests/test_emergency_experiments.py
git commit -m "feat: add nearest-station external support scenarios"
```

### Task 3: Cost-effectiveness aggregation and output validation

**Files:**
- Modify: `src/run_emergency_experiments.py`
- Modify: `tests/test_emergency_experiments.py`
- Modify: `src/reproduce_all.py`
- Modify: `tests/test_reproduce_all.py`

- [ ] **Step 1: Write failing aggregation tests**

Use a deterministic miniature frame and assert:

```python
summary = build_external_support_table(frame)
self.assertAlmostEqual(row_m2["cumulative_response_gain_min"], t0 - t2)
self.assertAlmostEqual(row_m2["marginal_response_gain_min"], t1 - t2)
self.assertAlmostEqual(row_m2["avoided_penalty_yuan"], p0 - p2)
self.assertAlmostEqual(row_m2["avoided_penalty_per_vehicle_yuan"], (p0 - p2) / 2)
self.assertAlmostEqual(row_m2["marginal_break_even_cost_yuan"], p1 - p2)
```

Assert count 0 has zero cumulative gain and missing per-vehicle/marginal values. Reject incomplete count sets, mixed call digests, and missing incident zones.

- [ ] **Step 2: Verify aggregation tests fail**

Run the new focused tests and confirm missing function failures.

- [ ] **Step 3: Implement summaries**

Add deterministic builders for:

- replication-level paired gains versus count 0;
- `external_support_by_zone_duration.csv` with mean and 95% confidence intervals;
- `external_support_citywide.csv` with ten-scenario equal-weight summaries within each seed and duration;
- `external_support_worst_zone.csv` identifying the largest mean response for each duration and count.

Compute total incident delay penalty as call count times mean penalty per call. Keep every duration separate.

- [ ] **Step 4: Add a dedicated full-run entry point**

Add CLI options:

```powershell
python src/run_emergency_experiments.py --project-root . --external-support --workers 12
```

Write external results under `results/task-3/external-support/` so frozen B_N/B_E evidence is not overwritten.

- [ ] **Step 5: Add reproducibility checks**

Verify 7000 rows, ten zones, ten durations, ten seeds, counts 0-6, identical calls across counts, daily cap at most 12, and count-0 equality with frozen B_E rows.

- [ ] **Step 6: Run focused and project tests**

```powershell
python -m unittest tests.test_emergency_experiments tests.test_reproduce_all -v
```

- [ ] **Step 7: Commit aggregation and validation**

```powershell
git add -- src/run_emergency_experiments.py src/reproduce_all.py tests/test_emergency_experiments.py tests/test_reproduce_all.py
git commit -m "feat: summarize external ambulance cost effectiveness"
```

### Task 4: Minimal slice and full 7000-run experiment

**Files:**
- Create: `results/task-3/external-support/*.csv`

- [ ] **Step 1: Run a minimal slice**

Run one zone, one duration, one seed and counts 0-2. Confirm count 0 matches frozen B_E, calls are identical, response values are finite, and external vehicles respect activation and daily caps.

- [ ] **Step 2: Run the P1 deterministic gate**

Run the focused tests and a read-only inspection of the minimal CSV. Do not start the full experiment until this slice passes.

- [ ] **Step 3: Run the full experiment**

```powershell
python src/run_emergency_experiments.py --project-root . --external-support --workers 12
```

Expected: 7000 replication rows and all derived external-support tables.

- [ ] **Step 4: Validate frozen and new evidence**

```powershell
python src/reproduce_all.py --project-root . --mode verify --scope all
```

- [ ] **Step 5: Commit frozen result tables**

```powershell
git add -- results/task-3/external-support
git commit -m "data: add temporary external ambulance results"
```

### Task 5: Publication figure and visual verification

**Files:**
- Modify: `src/generate_figures.py`
- Modify: `tests/test_reproduce_all.py`
- Create: `figures/result_q3_external_support.png`
- Create: `figures/result_q3_external_support.svg`

- [ ] **Step 1: Profile the external-support result table**

Check group sizes, missing values, response ranges, penalty ranges and marginal-gain signs before choosing plotted durations.

- [ ] **Step 2: Write the figure contract**

Core claim: additional ambulances reduce long-incident response sharply at first, while marginal response and avoided-penalty gains decline as vehicle count grows.

Use two independent panels: response-time curves by duration on the left; marginal break-even avoided penalty by external count on the right. Do not use a dual axis.

- [ ] **Step 3: Add a failing figure-evidence test**

Require `result_q3_external_support` to map to `external_support_citywide.csv` and require both PNG and SVG outputs.

- [ ] **Step 4: Implement and export the figure**

Generate at final Word width with colorblind-safe colors, distinct markers/linestyles, 95% intervals where readable, 300 DPI PNG and SVG.

- [ ] **Step 5: Run figure checks and inspect the PNG**

```powershell
python src/generate_figures.py
python "C:\Users\AA\.codex\skills\math-modeling\tools\figure\scripts\check_figure.py" figures --strict
```

Open the PNG and check labels, clipping, legend, line distinction and grayscale readability.

- [ ] **Step 6: Commit figure code and outputs**

```powershell
git add -- src/generate_figures.py tests/test_reproduce_all.py figures/result_q3_external_support.png figures/result_q3_external_support.svg
git commit -m "docs: visualize external ambulance efficiency"
```

### Task 6: Rewrite Task 3 Markdown from real results

**Files:**
- Modify: `paper/v2.5/A题论文(v2.5).md`

- [ ] **Step 1: Simplify Section 7.1**

State directly that R1-R10 are ten separate single-zone accident scenarios. Keep one increment formula and explain that the worst start is common across zones for a fixed duration because all zones share the same intraday density.

- [ ] **Step 2: Add temporary support and final summary sections**

Use `7.8 临时外援车辆配置与性价比` and `7.9 任务三小结`. Report only values from the frozen CSV files, explain that the break-even cost is avoided delay penalty rather than assumed vehicle expense, and preserve the no-cross-duration aggregation boundary.

- [ ] **Step 3: Update the abstract and algorithm table**

Keep `针对任务一/二/三` bold. Add the selected external-support result and recommended vehicle count only after the response and marginal-benefit results are known.

- [ ] **Step 4: Parse and audit Markdown**

```powershell
pandoc "paper/v2.5/A题论文(v2.5).md" --from=markdown+tex_math_dollars --to=native | Out-Null
python "C:\Users\AA\.codex\skills\remove-ai-flavor\scripts\audit_ai_flavor.py" "paper/v2.5/A题论文(v2.5).md"
git diff --check
```

- [ ] **Step 5: Stop at the Markdown review gate**

Provide the content-change report. Do not generate or overwrite DOCX until the user approves the Markdown.

---

## Plan self-review

- The plan covers activation, nearest-station placement, identical vehicle parameters, common calls, 0-6 vehicles, cost-effectiveness, full results, figures and paper text.
- Default 12-vehicle simulations remain unchanged because all new fleet arguments are optional.
- External results use a separate directory and cannot overwrite frozen B_N/B_E evidence.
- The economic interpretation does not invent external-vehicle cost.
- Full stochastic execution is gated by a count-0 reproduction slice.
