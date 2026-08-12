# Problem A: Ambulance Dispatch

Summer-assignment modeling solution for ambulance station location, vehicle allocation, routine dispatch, reserve configuration, and emergency response. The 2026 national-contest template is used only as a layout reference; this project does not claim to be a 2026 national-contest entry.

## Layout

- `src/`: optimization, simulation, experiments, and figure generation.
- `tests/`: regression and model-contract tests.
- `analysis/`: historical modeling materials and the authoritative v2.4 retrospective.
- `templates/`: personalized workflow, paper profile, and reusable task prompts.
- `results/task-1/`: verified compact results for Task 1.
- `results/task-2/`: generated Task 2 results after the revised model passes validation.
- `figures/`: approved publication figures.
- `paper/vX.Y/`: one Word paper, Markdown source, and conversion manifest per release.
- `utils/`: project-specific helpers.

## Current Status

Tasks 1--3 have frozen result tables and publication figures. Task 2 uses exactly 140 calls per day, a fixed 30-day warmup, conditional-NHPP arrival times, a per-vehicle 12-dispatch limit, and continuous cross-midnight vehicle state. Task 3 treats incident duration as continuous on `[0.5, 12]` hours: the six initial durations are expanded adaptively to ten simulation nodes, and replication-level PCHIP surfaces with 95% confidence bands are used only as numerical response approximations. No result is pooled across incident durations.

The current paper release is `paper/v2.4/A题论文(v2.4)`. Small revisions increment the minor version; a substantial model or paper rewrite advances to `v3`. The root `README.md` records the release notes.

The complete v2.4 project retrospective is `analysis/project-retrospective-v2.4.md`. Future projects should start from `templates/personal-modeling-playbook.md`; its exact Word/table/figure defaults are mirrored in `templates/personal-paper-profile.yaml`.

## Reproduction

Run commands from this directory:

```powershell
# Read-only validation of all frozen evidence. This is the manifest command.
python src/reproduce_all.py --project-root . --mode verify --scope all

# Rebuild aggregate tables and response surfaces from versioned replication data,
# regenerate figures, and then validate all three tasks.
python src/reproduce_all.py --project-root . --mode rebuild --scope all

# Optional full rerun, including the expensive stochastic experiments.
python src/reproduce_all.py --project-root . --mode full --scope all
```

The versioned replication-level CSV files are intentional scientific evidence, not disposable caches. `results/复现清单.json` binds the statement and the frozen results for all three tasks. The verification command does not rerun the long simulation; it recomputes deterministic checks and validates every frozen table, paired scenario, hard constraint, and required figure.
