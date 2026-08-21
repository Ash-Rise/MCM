# Accepted Decisions

> Semantic authority for the completed ambulance-dispatch project. Keep only significant accepted choices that future work must not silently redefine. Problem facts, implementation details, numerical results, and execution history remain authoritative in their own artifacts.

## DEC-001 — Task 1 objective and construction-priority role

**Status:** Accepted

**Decision:**  
For the full-service Task 1 model, minimize demand-weighted dispatch distance first; among distance-optimal service allocations, maximize planning coverage. The construction-priority score is not part of the main objective or constraints because the capacity requirement forces all six stations to open; it may only inform a separate staged-construction analysis.

**Reason:**  
This preserves the accepted primary objective without introducing an arbitrary cross-metric weight or a constant construction-priority term.

**Supersedes:** none

## DEC-002 — Task 1 service-radius semantics

**Status:** Accepted

**Decision:**  
Use 3 km (`45 km/h × 4 min`) as Task 1's nominal four-minute pure-driving planning-service radius. It is not the strict total-response radius after the 3 min preparation time. The 0.75 km center-based radius (`45 km/h × (4-3) min`) is a strict-response diagnostic only and does not drive the Task 1 allocation.

**Reason:**  
The user explicitly selected the 3 km planning interpretation after separating planning coverage from operational total response time.

**Supersedes:** none

## DEC-003 — Daily call-generation semantics

**Status:** Accepted

**Decision:**  
Generate exactly 140 calls per calendar day. The conditional NHPP randomizes intraday arrival times rather than the daily total; region labels are sampled with probability `q_i / 140`. The periodic double-Gaussian intraday profile is a transparent scenario input, not a fit to unavailable hourly historical data.

**Reason:**  
A Poisson-distributed daily total around 140 created artificial overload against the system's 144-call nominal daily capacity and was rejected.

**Supersedes:** none

## DEC-004 — Response-time and delay-penalty semantics

**Status:** Accepted

**Decision:**  
Operational response time is
`T_resp = T_wait + 3 + 60d/45` minutes: queue wait + fixed preparation + travel to the incident at 45 km/h. Distance from the incident to the nearest hospital is not part of this arrival-response metric or the dispatch objective. Delay penalty is `200 × max(T_resp - 4, 0)` yuan per call and is an evaluation metric; it does not replace mean response time as the primary performance objective.

**Reason:**  
This is the accepted interpretation of the four-minute response target and the given delay-penalty data.

**Supersedes:** none

## DEC-005 — Vehicle occupation, daily limits, and queue continuity

**Status:** Accepted

**Decision:**  
A dispatched ambulance is occupied for the full 45 min task cycle and then returns to its assigned station. Each ambulance may accept at most 12 tasks per calendar day, counted by dispatch acceptance time. At 00:00 only the daily acceptance counter resets; vehicle busy/free state and the unserved FCFS queue continue across midnight. Calls are served from one citywide FCFS queue and are not discarded merely because the calendar day or incident window ends.

**Reason:**  
This is the accepted continuous multi-day simulation contract and prevents midnight truncation from understating waiting time.

**Supersedes:** none

## DEC-006 — Incident-duration domain

**Status:** Accepted

**Decision:**  
Incident duration `H` is continuous on `[0.5, 12]` hours. Any finite set of simulated duration nodes is numerical sampling only and does not redefine the mathematical domain. Interpolation between sampled durations is a numerical approximation, not an exact continuous analytic solution.

**Reason:**  
The user explicitly restored the continuous domain after numerical sample nodes had drifted into the model contract as if they were the only allowed durations.

**Supersedes:** none

## DEC-007 — Task 3 incident scenarios and BN/BE meaning

**Status:** Accepted

**Decision:**  
R1 through R10 are ten separate single-zone incident scenarios, not simultaneous incidents. During an incident, the affected region's total call intensity is five times normal while other regions remain at normal intensity. The base `B_N` versus `B_E` comparison uses the original fixed 12-ambulance fleet. `B_N` keeps Strategy B's normal future-demand forecast; `B_E` uses the same dispatch framework but, only during the incident, treats the affected region's future 45 min demand forecast as five times normal and returns to `B_N` when the incident ends. `B_E` is a priority/forecast adjustment, not added capacity.

**Reason:**  
The accepted Task 3 design studies an incident-state parameter switch within the existing dispatch framework before separately studying capacity expansion.

**Supersedes:** none

## DEC-008 — Task 3 evaluation window

**Status:** Accepted

**Decision:**  
Task 3 performance is evaluated on calls that arrive during the incident. If such a call is still waiting when the incident ends, simulation continues until it receives service; new calls arriving after the incident are not part of the incident-performance sample. Duration-specific results remain conditional on `H`; do not turn different `H` values into one probabilistic overall effect unless a duration distribution is supplied.

**Reason:**  
This preserves a stable denominator and avoids silently changing the question by truncating unresolved calls or inventing a probability distribution over incident durations.

**Supersedes:** none

## DEC-009 — Temporary external-support extension

**Status:** Accepted

**Decision:**  
Temporary external ambulances are allowed only as a separate extension after the fixed-12 baseline is evaluated. They stage at the nearest existing station, use temporary staging space that does not consume permanent station parking capacity, and are available at incident start with zero activation delay. Their preparation time, speed, 45 min task occupation, daily task limit, return-to-assigned-station rule, and `B_E` participation match ordinary ambulances. They remain available until calls generated during the incident have cleared.

**Reason:**  
These were frozen user choices defining what the later external-support experiment means; they must not be retroactively folded into the original fixed-fleet baseline.

**Supersedes:** none

## DEC-010 — External-support economic boundary

**Status:** Accepted

**Decision:**  
Do not invent a purchase, rental, or deployment price for external ambulances. Use the given 200 yuan/(min·call) delay penalty to report avoided delay penalty and marginal break-even deployment cost. Without an actual external-vehicle cost, the project may compare response/resource trade-offs but must not claim a unique economic optimum.

**Reason:**  
The problem provides a delay penalty but no external-vehicle price, so a unique monetary optimum would require unsupported data.

**Supersedes:** none
