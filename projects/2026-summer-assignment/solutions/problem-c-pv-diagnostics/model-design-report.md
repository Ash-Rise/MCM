# Problem C Model Design Report

> Status: candidate design; no model family is frozen and no formal solution has been computed.
> Authority: problem facts come from the original DOCX files; accepted semantics come from `decisions.md`.

## 1. Contract and information boundaries

### 1.1 Problem facts

- The station contains 100 photovoltaic modules, each rated at 550 W, connected through a string–combiner–inverter topology.
- For every module, the data package supplies 15 daily generation values, a 15-day average generation deviation rate, string membership, azimuth, tilt, and years in service.
- The statement supplies the three-state thresholds: normal when `|deviation| <= 5%`, microcrack when `-15% <= deviation < -5%`, and hotspot when `deviation < -15%`.
- Shading is a reference interference factor rather than a required fourth output class.
- Fifteen daily weather observations and the day-16 forecast are supplied. Task 2 asks for day-16 total station generation and uncertainty.
- Task 3 permits priority repair of 10 faulty modules and asks for a loss-based ranking and post-repair station improvement.

### 1.2 Accepted semantic decisions

- **DP-C-001=A:** the supplied deviation rate is the official diagnostic indicator. The reference-example label is used only after classification for verification.
- **DP-C-002=A:** the primary repair ranking uses 15-day historical mean absolute recoverable loss in kWh/day. Day-16 recoverable generation is supplementary.
- The rejected alternatives remain sensitivity or discussion models only and cannot silently replace either primary definition.

### 1.3 Necessary modeling assumptions

- A repaired module returns to the normal counterfactual represented by the theoretical-generation term in the official deviation-rate definition.
- Component daily-energy measurements are comparable and their contributions can be added when forming station energy.
- With no I–V curves, inverter clipping data, electrical mismatch parameters, repair-cost differences, or shared downtime constraints, repair gains are modeled as independent and additive. String topology is retained for distribution analysis and as a stated failure boundary, not used to invent unidentifiable interaction effects.
- Rounding of the supplied deviation rate may introduce small counterfactual and ranking uncertainty and must be tested.

### 1.4 AI-owned technical choices

- Data parsing, numerical tolerances, stable sorting, and exact boundary handling.
- The robust statistic used for shading-interference screening.
- Candidate fitting implementation, day-level cross-validation, residual diagnostics, and interval computation.
- Presentation of descriptive distributions and sensitivity results, provided these do not redefine the accepted diagnostic or ranking semantics.

No new human-owned semantic decision is required at this design stage. If later evidence shows material string-level interaction, partial rather than full restoration, or a different repair objective, work must stop for a new Decision Proposal.

## 2. Task 1 — Fault diagnosis

### 2.1 Model meaning

The model maps the supplied official 15-day deviation indicator to one of the three required states. Daily generation and metadata do not redefine this indicator; they support interference screening, distribution summaries, and validation.

### 2.2 Inputs

For module `i` and day `d`:

- `b_i`: supplied 15-day average generation deviation rate, expressed as a decimal in formulas;
- `E_id`: actual daily generation, kWh;
- `H_d`: daily total irradiation, kWh/m²;
- `string_i`, `azimuth_i`, `tilt_i`, `age_i`, and rated power;
- reference-example label, quarantined from the classification calculation and read only during validation.

### 2.3 Primary classification rule

The deterministic classifier is

\[
C_i=
\begin{cases}
\text{normal}, & |b_i|\le 0.05,\\
\text{microcrack}, & -0.15\le b_i<-0.05,\\
\text{hotspot}, & b_i<-0.15.
\end{cases}
\]

The official table does not define `b_i > 5%`. No supplied record lies there. A future record in that region must be flagged as outside the stated rule rather than silently forced into one of the three classes.

### 2.4 Shading-interference screen

Screening is necessary as a diagnostic caution because the statement explicitly identifies shading as a confounder, but it is not a fourth primary class and cannot overwrite `C_i`.

For each day with positive irradiation, construct an irradiation-normalized output `q_id = E_id/H_d`. To remove stable geometry effects, compare its time pattern with the daily median of provisionally normal peer modules with the same available configuration; if a peer group is too small, fall back to the broader normal cohort. A module is marked `shading_suspect` only when both conditions hold:

1. its robust temporal dispersion is an outlier relative to normal peers; and
2. the anomaly is time-local or patterned rather than a nearly constant deficit.

The exact robust cutoff is an AI-owned technical choice to be calibrated from the normal-cohort distribution. A shading flag means “the threshold diagnosis may be confounded and needs field inspection”; it does not assert a new fault label.

### 2.5 Descriptive distribution and causal boundary

Report counts and within-group rates by string, azimuth, tilt, and service age. Unequal group sizes require rates as well as counts. Because string, azimuth, tilt, and service age are strongly confounded in the supplied layout, these summaries support statements about concentration only. They do not identify causal effects of geometry, age, or string membership.

### 2.6 Candidate, rationale, data, validation, and failure boundary

- **Candidate model:** official threshold classifier plus a non-overriding robust shading screen.
- **Why selected:** it exactly implements DP-C-001 and the statement's explicit thresholds without manufacturing a learned classifier from a reference column.
- **Required data:** supplied deviation, 15 daily module outputs, irradiation, and component metadata.
- **Validation:** threshold-boundary tests, label agreement checked only after prediction, normalized-profile diagnostics, and count reconciliation to 100 modules.
- **Failure boundary:** undefined positive deviation above 5%; transient shading indistinguishable from sensor error; physical confirmation of hotspot/microcrack requires infrared or electroluminescence inspection not supplied by the problem.

## 3. Task 2 — Day-16 station generation forecast

### 3.1 Target and independent sample unit

The target remains the total generation of the station in its current, unrepaired operating state on day 16. Define

\[
Y_d=\sum_{i=1}^{100}E_{id}.
\]

The independent forecasting unit is a day, so there are 15 weather scenarios, not 1,500 independent training observations. Component-level repetitions cannot be used to inflate forecast degrees of freedom.

### 3.2 Candidate model set

#### M0 — Irradiation-proportional baseline

\[
Y_d=\beta H_d+\varepsilon_d.
\]

This is the mandatory simple baseline. It respects zero solar generation at zero irradiation and tests whether a stable station performance factor is sufficient. It is not frozen as the final model.

#### M1 — Restricted affine diagnostic extension

\[
Y_d=\alpha+\beta H_d+\varepsilon_d.
\]

The intercept tests systematic misspecification in M0. Because a large nonzero intercept is physically suspect, M1 may be selected only if validation improvement is material and the intercept remains physically credible.

#### M2 — Restricted weather-adjusted physical extension

\[
Y_d=H_d\left[\beta_0+\beta_T(T_d-T_*)+\beta_W(W_d-W_*)\right]+\varepsilon_d,
\]

where `T_*` and `W_*` are historical centering constants. Temperature and wind enter only through irradiation-scaled efficiency adjustments. When supported by fitting, use the physical sign constraints `beta_T <= 0` and `beta_W >= 0`. If collinearity makes either effect unstable or inactive, remove it rather than adding regularization layers or further predictors.

Weather type is not a primary predictor because it largely restates irradiation and has very small category counts. Azimuth and tilt are static for each module; with a fixed station composition they are absorbed into station performance coefficients and cannot be identified as independent daily effects. Splitting the station into fixed geometry groups and summing groupwise proportional models is algebraically equivalent to a single total proportional coefficient unless additional identifiable interactions are introduced, so it is not treated as a separate forecasting model.

### 3.3 Candidate selection rule

Use leave-one-day-out cross-validation for all candidates. The primary selection statistic is held-out MAE. RMSE, maximum absolute error, and held-out residual stability are secondary; full-sample `R²` is descriptive only.

Apply the one-standard-error preference: among models whose cross-validated MAE is within one estimated standard error of the minimum, retain the simplest physically credible model. An extension must also have stable coefficient signs and must not gain accuracy only from one influential day. Thus M0 is a baseline, not a predetermined winner.

### 3.4 Uncertainty output

For the selected model report both:

- a 95% confidence interval for expected day-16 generation; and
- a 95% prediction interval for a realized day-16 total, which includes day-level residual variability.

The primary interval method will be the small-sample Student-t regression interval when residual diagnostics are adequate. If variance is more stable after normalizing by irradiation, estimate uncertainty on `Y/H` and transform it back using `H_16`. A day-level residual bootstrap is a sensitivity method, not an automatic replacement. With only 15 days, interval coverage from leave-one-out predictions is reported as a diagnostic rather than claimed as a precise 95% calibration proof.

### 3.5 Candidate, rationale, data, validation, and failure boundary

- **Candidates:** M0 proportional baseline, M1 affine misspecification check, and M2 restricted weather-efficiency extension.
- **Why these models:** they span the smallest credible progression from irradiation-only physics to limited weather correction while keeping parameter count compatible with 15 days.
- **Required data:** daily station total aggregated from component records; irradiation, temperature, wind, and day-16 forecast.
- **Validation:** leave-one-day-out predictions, MAE/RMSE/`R²`, influence and residual checks, coefficient stability, and interval diagnostics.
- **Failure boundary:** only 15 days and one season; strong predictor collinearity; no independent variation in station geometry; forecast is not valid for weather outside the observed range, changed fault state, curtailment, inverter clipping, or major maintenance between days 15 and 16.

## 4. Task 3 — Repair ranking and recoverable generation

### 4.1 Fault set and normal counterfactual

Only modules classified as hotspot or microcrack under Task 1 enter the repair ranking. Let

\[
\bar E_i=\frac{1}{15}\sum_{d=1}^{15}E_{id}.
\]

The official deviation definition gives

\[
b_i=\frac{\bar E_i-\bar E_i^{(0)}}{\bar E_i^{(0)}},
\]

so the accepted main counterfactual is obtained without redefining the deviation rate:

\[
\bar E_i^{(0)}=\frac{\bar E_i}{1+b_i}.
\]

The historical mean absolute recoverable loss is therefore

\[
L_i=\bar E_i^{(0)}-\bar E_i
=-\frac{b_i}{1+b_i}\bar E_i\quad\text{(kWh/day)}.
\]

Peer-normalized or physical-theory counterfactuals are sensitivity analyses only, consistent with DP-C-001.

### 4.2 Additivity judgment

Under the available data contract, repair gains are additive: station energy is formed by summing component energy, repair costs are equal in the stated budget, and no interaction, clipping, downtime, or string bottleneck constraint is quantified. Hence a selected set `S` has primary historical gain

\[
G(S)=\sum_{i\in S}L_i.
\]

This is an explicit model assumption rather than a claim that all physical string effects are absent. If electrical mismatch or inverter clipping data later show that one repair changes another module's gain, additivity fails and a new semantic decision is required before adopting an interaction model.

### 4.3 Why sorting gives the exact top-10 solution

All feasible repairs have the same unit budget cost and nonnegative independent gain. Suppose a chosen set of 10 contains module `j` while an unchosen module `k` has `L_k > L_j`. Replacing `j` with `k` keeps the set feasible and increases total gain by `L_k-L_j`. Therefore no optimal set can omit a larger loss while containing a smaller one. Sorting losses in descending order and taking the first 10 is exact. Ties at the cutoff yield multiple equally optimal lists and must be reported rather than resolved by an invented substantive preference.

No optimization algorithm is needed unless unequal costs, interaction gains, shared constraints, or a different objective is introduced.

### 4.4 Day-16 supplementary gain

After Task 2 selects a forecasting model, scale the selected modules' normal and faulty counterfactual outputs to the day-16 weather condition and report their summed expected increment. This supplementary value does not change the DP-C-002 historical ranking.

### 4.5 Candidate, rationale, data, validation, and failure boundary

- **Candidate model:** analytical inversion of the official deviation definition, additive loss accounting, and exact descending sort.
- **Why selected:** it follows DP-C-002, uses the stated kWh loss objective, and exploits the absence of combination constraints.
- **Required data:** Task 1 fault set, 15 daily outputs, supplied deviation rates, and the selected Task 2 model for supplementary day-16 scaling.
- **Validation:** deviation reconstruction, nonnegative-loss and unit checks, ranking stability under deviation rounding and sensitivity counterfactuals, and reconciliation of selected gains with station-level improvement.
- **Failure boundary:** partial repair effectiveness, unequal repair costs, series-current bottlenecks, inverter clipping, repair downtime, future degradation, or long-horizon weather can make gains nonadditive or change the ranking meaning.

## 5. Model-selection frontier

- Task 1 semantics are fixed by DP-C-001; only interference diagnostics and descriptive analysis remain technical.
- Task 2 remains an open candidate comparison. M0 is only the baseline; no final forecasting model or interval method is accepted before validation.
- Task 3 semantics are fixed by DP-C-002; the main counterfactual follows directly from the official deviation definition, while physical and peer baselines remain sensitivity analyses.
- No machine-learning, deep-learning, metaheuristic, or combinatorial solver is justified by the present data or model contract.
