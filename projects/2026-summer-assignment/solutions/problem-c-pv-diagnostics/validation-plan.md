# Problem C Validation Plan

> Scope: smallest checks capable of selecting among current candidates or invalidating a planned conclusion. This plan does not authorize code, large experiments, or paper generation.

## 1. Validation principles

- Validate against the original DOCX and Accepted Decisions, not against generated outputs alone.
- Treat a day as the independent unit for forecasting and uncertainty.
- Use the reference-example labels only after Task 1 predictions are complete.
- Stop when the simplest adequate Task 2 candidate has sufficient evidence; do not expand model complexity merely because another feature is available.

## 2. Input and transformation checks

| Failure | Detection | Action if detected | Stop condition |
|---|---|---|---|
| Missing, duplicated, or misordered modules | Require exactly `PV001`–`PV100`, one parameter row and one generation row each | Stop downstream work and correct extraction | 100 unique aligned records |
| Wrong day or unit mapping | Require 15 numeric kWh values per module and 15 historical plus one forecast weather row with stated units | Stop and reconcile with DOCX | All dimensions and units match the statement |
| Reference-label leakage | Data contract keeps the reference column out of classifier inputs | Reject implementation | Classification can run with the reference column removed |
| Incorrect station aggregation | Compare each daily total with an independent sum over all 100 module values | Correct aggregation | Exact agreement within numerical parsing tolerance |
| Accepted semantics drift | Check diagnostic source and repair ranking formula against `decisions.md` | Stop and perform Decision Review | DP-C-001=A and DP-C-002=A are mechanically traceable in outputs |

## 3. Task 1 validation

### 3.1 Deterministic rule checks

- Unit-test the exact boundary cases `-15%`, `-5%`, and `+5%`.
- Verify that `b > 5%` is flagged outside the stated rule rather than silently assigned.
- Reconcile normal, microcrack, and hotspot counts to 100.
- Only after classification, compare with the reference-example column and list every disagreement rather than forcing agreement.

### 3.2 Shading screen checks

- Confirm every irradiation value used in `E/H` is positive; otherwise define a missing normalized value rather than divide by zero.
- Estimate the robust dispersion distribution from provisionally normal modules.
- Inspect flagged modules for time-local deviations after daily weather normalization.
- Compare flags under same-configuration peers and the broader normal cohort. If flags depend entirely on a very small peer group, report them as unstable.
- Do not alter the official three-state label based only on this screen.

### 3.3 Distribution checks

- Report both count and rate for every string, angle, tilt, and age group.
- Report group denominators and avoid causal language.
- Check whether conclusions disappear when very small or structurally confounded groups are combined; use this only as a descriptive robustness check.

## 4. Task 2 validation and selection

### 4.1 Evaluation protocol

Use deterministic leave-one-day-out cross-validation:

1. for each historical day `d`, fit M0, M1, and each identifiable version of M2 on the other 14 days;
2. predict held-out `Y_d` without using that day's station generation;
3. retain the 15 paired errors for every candidate;
4. fit the selected family on all 15 days only after candidate comparison.

Random train/test splits and component-level splits are prohibited because they would either waste the small time sample or leak the same daily weather across train and validation sets.

### 4.2 Metrics

- **Primary:** leave-one-day-out MAE in kWh.
- **Secondary:** RMSE, maximum absolute error, and normalized MAE relative to mean daily generation.
- **Required descriptive metric:** full-sample and cross-validated `R²`, clearly distinguished.
- **Interval diagnostics:** empirical leave-one-out coverage and mean width for the proposed interval, labeled as low-resolution evidence with only 15 cases.

MAPE is not a primary criterion because low-irradiation days receive disproportionate weight. It may be reported only as a supplementary percentage view.

### 4.3 Candidate-selection checks

- Apply the one-standard-error preference to cross-validated MAE.
- For M1, inspect whether the intercept is materially nonzero and whether it implies implausible generation near zero irradiation.
- For M2, inspect coefficient signs, fold-to-fold coefficient variation, predictor collinearity, and whether any gain comes from a single influential day.
- Remove inactive or unstable weather terms rather than add polynomial terms, regularization searches, weather categories, machine learning, or additional model families.
- Select an extension only when it improves held-out accuracy beyond the uncertainty of the comparison and remains physically interpretable.

### 4.4 Residual and interval checks

- Plot or tabulate residuals against fitted generation, irradiation, temperature, wind, and day order.
- Check whether residual scale is more stable for `Y` or for normalized output `Y/H`; choose the interval scale accordingly.
- Compare the Student-t interval with a modest day-level residual bootstrap sensitivity calculation if residual assumptions are doubtful.
- Report both the expected-value confidence interval and the realized-day prediction interval.
- Do not claim exact 95% calibration from 15 observations. If interval results are highly method-sensitive, report the range and limitation rather than selecting the narrowest interval.

### 4.5 Failure-triggered escalation

Simple models are inadequate only if all current candidates show a material, repeatable held-out error pattern not explained by extraction error or one influential day. Before considering any more complex model, identify the residual structure and propose the smallest additional mechanism capable of addressing it. If that mechanism changes target meaning or allowed information, use a Decision Proposal first.

## 5. Task 3 validation

### 5.1 Counterfactual checks

- Recompute each faulty module's `b_i` from `mean(E_i)` and the inverted counterfactual and require agreement with the supplied value within its display precision.
- Require `1+b_i > 0` and `L_i >= 0` for all ranked faults.
- Propagate the supplied one-decimal-percentage rounding as an interval or endpoint sensitivity for `L_i`.

### 5.2 Ranking checks

- Sort by kWh/day loss, not by percentage deviation alone.
- Verify that every selected module has loss no smaller than every unselected faulty module.
- Detect ties or overlapping rounding-sensitivity intervals at the rank-10 cutoff.
- Compare top-10 membership under the permitted physical and peer-counterfactual sensitivity models, while keeping the DP-C-002 ranking as primary.

### 5.3 Additivity and station reconciliation

- Confirm that predicted primary improvement equals the sum of the 10 selected component losses.
- Confirm that post-repair historical mean station generation equals current mean station generation plus that sum under the additive assumption.
- For day 16, keep forecast uncertainty and repair-counterfactual uncertainty separate before combining them.
- If evidence or new data reveal string bottlenecks, clipping, unequal costs, or shared downtime, stop: the exchange proof no longer applies and a new semantic decision is required.

## 6. Planned validation scale

The planned work is small and deterministic: data-contract checks, three low-parameter candidate families across 15 leave-one-day-out folds, residual diagnostics, and local sensitivity checks. No large simulation, hyperparameter search, or external-data acquisition is justified at this stage.
