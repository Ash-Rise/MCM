# Problem A: Ambulance Dispatch

Summer-assignment modeling solution for ambulance station location, vehicle allocation, routine dispatch, reserve configuration, and emergency response. The 2026 national-contest template is used only as a layout reference; this project does not claim to be a 2026 national-contest entry.

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

Tasks 1 and 2 have frozen result tables and publication figures. Task 2 uses exactly 140 calls per day, a fixed 30-day warmup, conditional-NHPP arrival times, a per-vehicle 12-dispatch limit, and continuous cross-midnight vehicle state. Task 3 is currently frozen at the model-contract level: incident duration is continuous on `[0.5, 12]` hours, while finite simulation nodes are only an adaptive numerical design. The old six-duration aggregate results and figures are not current paper evidence.

## Reproduction

Run commands from this directory:

```powershell
# Read-only validation of the staged Task 1 and Task 2 evidence.
python src/reproduce_all.py --project-root . --mode verify --scope q1-q2

# Rebuild only the Task 2 aggregate tables, then validate Task 1 and Task 2.
python src/reproduce_all.py --project-root . --mode rebuild --scope q1-q2
```

The versioned replication-level CSV files are intentional scientific evidence, not disposable caches. `results/复现清单.json` currently binds only the staged Task 1 and Task 2 evidence. No Task 3 reproduction command is published until the continuous-duration adaptive response surface has been implemented and revalidated.
