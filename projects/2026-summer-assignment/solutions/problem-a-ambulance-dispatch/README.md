# Problem A: Ambulance Dispatch

Modeling solution for ambulance station location, vehicle allocation, routine dispatch, reserve configuration, and emergency response.

## Layout

- `src/`: optimization, simulation, experiments, and figure generation.
- `tests/`: regression and model-contract tests.
- `analysis/`: modeling report and terminology contract.
- `results/task-1/`: verified compact results for Task 1.
- `results/task-2/`: generated Task 2 results after the revised model passes validation.
- `figures/`: approved publication figures.
- `paper/`: final Word/PDF paper artifacts.
- `utils/`: project-specific helpers.

## Current Status

Tasks 1 and 2 are verified. Task 2 uses exactly 140 calls per day, a fixed 30-day warmup, conditional-NHPP arrival times, a per-vehicle 12-dispatch limit, and continuous cross-midnight vehicle state. Task 3 emergency experiments are in progress.
