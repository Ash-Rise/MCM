# Problem A: Ambulance Dispatch

Summer-assignment modeling solution for ambulance station location, vehicle allocation, routine dispatch, reserve configuration, and emergency response. The 2026 national-contest template is used only as a layout reference; this project does not claim to be a 2026 national-contest entry.

## Latest Paper: v2.5

- Current Pandoc source: [`paper.md`](paper/paper.md)
- Current Word deliverable: [`paper.docx`](paper/paper.docx)
- Source code: [`src/`](src/)
- Frozen results and replication data: [`results/`](results/)
- Reproduction manifest: [`results/复现清单.json`](results/复现清单.json)
- Publication figures: [`figures/`](figures/)

The current paper release is **v2.5**. Its Task 3 analysis includes the existing 12-vehicle incident-aware dispatch process and the 0--6 vehicle temporary-support experiment used to derive the 1/3/5-vehicle aid tiers.

## Layout

- `src/`: optimization, simulation, experiments, and figure generation.
- `tests/`: regression and model-contract tests.
- `analysis/`: model contracts, terminology, and technical design notes.
- Repository-wide workflow and formatting defaults: [`shared/templates/`](../../../../shared/templates/); this project keeps only project-specific analysis and evidence locally.
- `results/task-1/`: verified compact results for Task 1.
- `results/task-2/`: generated Task 2 results after the revised model passes validation.
- `figures/`: approved publication figures.
- `paper/`: fixed-name current Markdown, Word deliverable, and conversion manifest; historical repository snapshots are available through Git tags and versioned downloads through Releases.

## Current Status

Tasks 1--3 have frozen result tables and publication figures. Task 2 uses exactly 140 calls per day, a fixed 30-day warmup, conditional-NHPP arrival times, a per-vehicle 12-dispatch limit, and continuous cross-midnight vehicle state. Task 3 treats incident duration as continuous on `[0.5, 12]` hours: the six initial durations are expanded adaptively to ten simulation nodes, and replication-level PCHIP surfaces with 95% confidence bands are used only as numerical response approximations. No result is pooled across incident durations.

The current paper release is v2.5. [`paper/paper.md`](paper/paper.md) is the authoritative Pandoc/DOCX source on `main`; Git tags preserve historical repository snapshots, while Releases provide versioned Word downloads. Derived GitHub-preview Markdown is no longer published. Future tags use a project-qualified name such as `2026-summer-a/v2.6`. Small revisions increment the minor version; a substantial model or paper rewrite advances to `v3`. The root `README.md` records release notes.

Future projects should start from the repository-wide [`personal-modeling-playbook.md`](../../../../shared/templates/personal-modeling-playbook.md); its exact Word, single-source Pandoc Markdown, table, figure, and verified-rule-promotion defaults are mirrored in [`personal-paper-profile.yaml`](../../../../shared/templates/personal-paper-profile.yaml).

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
