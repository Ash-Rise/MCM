# Task 3 Emergency Dispatch Design

## Scope

Task 3 evaluates a recognized major incident in one of the ten demand zones. During the incident, that zone's call intensity is five times its normal intensity. The model uses the existing 12 ambulances, permits cross-station dispatch, and returns each ambulance to its home station after the fixed 45-minute busy cycle. It adds no external aid, triage classes, temporary bases, or longer service times.

The incident zone is enumerated over all ten zones. Incident duration is an input rather than an assumed four-hour constant. Results are reported as performance curves over a compact duration grid. For each duration, the incident starts at the 24-hour interval with the largest integral of the shared intraday density, which supplies a transparent worst-time scenario without asserting an unsupported clock time.

## Demand construction

Each replication retains the Task 2 background stream: exactly 140 calls per complete day, with conditional-NHPP arrival times and zone marks proportional to normal demand. During incident interval `[t0, t0 + H)`, an independent extra NHPP stream is added in zone `k` with intensity

`4 q_k f(t mod 24)`.

Therefore the combined zone-k intensity is `5 q_k f(t mod 24)` in the incident interval and normal outside it. The same realized call stream is used for both compared dispatch modes.

## Compared modes

- `B_N`: continue the Task 2 selected policy `B(beta=4, delta=2)` while its 45-minute future-loss calculation still uses normal demand intensity.
- `B_E`: retain exactly the same score, queue discipline, busy time, and daily cap, but calculate future loss with the recognized incident intensity during the incident interval.

Because Task 2 selected B, no fixed reserve identity exists in the main baseline. The independently reported C configuration remains the explicit reserve-configuration answer to Task 2 and is not mixed into Task 3.

## Observation window

The simulator uses the same fixed 30-day warmup. Task 3 metrics include every call arriving during `[t0, t0 + H)`, separately for all zones, the incident zone, and non-incident zones. Calls arriving before incident end but still waiting at incident end remain in the simulation until dispatched so their full response times are observed. New calls after incident end are not generated for Task 3 evaluation, and no post-incident recovery metric is reported.

## Outputs

For every zone, duration, mode, and replication, report mean and P95 response time, strict four-minute rate, mean waiting time, delay penalty, and maximum queue during the incident interval. Paired differences use common random numbers. Summary tables provide 95% t intervals and identify adverse, typical, and favorable zones from the full ten-zone result rather than selecting a location in advance.

## Verification

Tests must show that extra calls occur only in the incident zone and interval, generation is reproducible, the emergency rate profile is exactly five only where intended, B_N and B_E receive identical calls, the 30-day warmup is fixed, and incident metrics exclude post-incident arrivals while retaining delayed incident calls.
