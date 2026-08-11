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

Task 1 is verified. Task 2 is being revised to generate exactly 140 calls per day with conditional NHPP arrival times while retaining the per-vehicle 12-dispatch limit and continuous cross-midnight vehicle state. Previous near-30-minute Task 2 outputs are obsolete and are not part of this project history.
