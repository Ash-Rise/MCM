# MCM Repository Structure Design

## Purpose

`MCM` is a long-lived repository for mathematical-modeling coursework, practice, and competitions. The current ambulance-dispatch work is one solution inside the 2026 summer assignment, not the repository root project.

## Repository Layout

```text
MCM/
|-- README.md
|-- projects/
|   `-- 2026-summer-assignment/
|       |-- README.md
|       |-- problem-statements/
|       |   |-- problem-a-ambulance-dispatch-statement.docx
|       |   |-- problem-b-statement.docx
|       |   |-- problem-c-statement.docx
|       |   `-- problem-c-supporting-data.docx
|       `-- solutions/
|           `-- problem-a-ambulance-dispatch/
|               |-- README.md
|               |-- src/
|               |-- tests/
|               |-- analysis/
|               |-- results/
|               |-- figures/
|               |-- paper/
|               `-- utils/
|-- shared/
|   |-- templates/
|   `-- references/
|-- docs/
`-- local-archives/
```

## Naming Rules

- Directories and ordinary files use lowercase English kebab-case.
- Python modules use lowercase snake_case.
- Original problem documents end in `-statement.docx`.
- Supporting attachments end in `-supporting-data.<ext>`.
- Final papers end in `-paper.docx` or `-paper.pdf`.
- Generated tables live under `results/task-N/`; figures use `raw_`, `process_`, or `result_` prefixes plus the task number.

## Version-Control Boundary

- Track problem statements, source code, tests, analysis contracts, compact key results, approved figures, and final papers.
- Keep teammate papers, review extracts, backups, Office lock files, large archives, simulation caches, and rendered QA pages under ignored local storage.
- Preserve the pre-migration repository as local branch `local-baseline`.
- Publish a new root commit on `main` so local-only review material is absent from the GitHub history.
- Do not add an open-source license until publication and reuse rights are confirmed.

## Current Project Boundary

The current solution is `projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch`. The task-one result remains valid. Task two is under revision to use 140 calls per simulated day with conditional NHPP arrival times and a four-minute excess-delay cost; obsolete full-run outputs remain local only.
