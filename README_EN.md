# MCM

[简体中文](README.md)

Long-lived workspace for mathematical-modeling coursework, practice, and competitions.

## Projects

- [`2026 Summer Assignment`](projects/2026-summer-assignment/README.md)
- Online preview: [`A题论文(v2.4)`](projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/paper/v2.4/A题论文(v2.4)-GitHub预览.md)
- Word deliverable: [`A题论文(v2.4).docx`](projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/paper/v2.4/A题论文(v2.4).docx)

## Release Notes

### v2.4 (2026-08-13 04:39 UTC+8)

- Shortened the paper title to fit on one line and standardized top-level body headings to Chinese numerals from “一、” through “八、”.
- Revised the problem analysis, model boundaries, and evaluation into formal academic prose without changing models, data, metrics, or numerical conclusions.
- Converted all four in-text reference markers to superscript while retaining normal numbering in the reference list.
- Added implementation-aligned three-line algorithm-design tables for Tasks 1, 2, and 3.
- Reformatted all 12 three-line tables against the reference papers, standardized centered equations, compound subscripts, and table alignment, and kept every Table 7 field on one line at 10 pt.
- Standardized the service indicator as “arrival within 4 minutes” and synchronized the latest Word and Markdown content.
- Expanded the Task 2 paired-comparison figure to six metrics: mean response, P95, mean waiting time, arrival within 4 minutes, regional mean gap, and delay cost per call.
- Retained Tables 11 and 12 and consolidated the emergency-policy effects into one large figure covering citywide, incident-zone, and non-incident-zone outcomes.
- Tightened the Task 3 causal boundary: under the fixed-fleet and incident-intensity settings used here, capacity constraints have a larger effect than the marginal demand-forecast correction.

### v2.3 (2026-08-12 19:27 UTC+8)

- Matched the reference paper's paragraph density: 1.5-line body text, 1.25-line references and appendix notes, and 1.15-line table cells.
- Corrected paragraph alignment so body text remains justified while only titles, major headings, figures, and captions are centered.
- Organized every paper release under `paper/vX.Y/`, with the Markdown source, Word paper, and conversion manifest kept together.

### v2.2 (2026-08-12 18:45 UTC+8)

- Condensed repetitive passages without changing the three tasks' models, frozen numerical results, or conclusions.
- Repaired Markdown math notation that triggered conversion warnings and tightened the reproducibility note in the appendix.
- Standardized Chinese typography, heading alignment, captions, table geometry, page numbers, and figure alternative text against the reference layout.

### v2.1 (2026-08-12 16:41 UTC+8)

- Published the first complete three-task paper, including the transport LP for vehicle allocation, conditional-NHPP dispatch simulation, and continuous-duration emergency-response analysis.
- Included all 13 data-driven figures, eight result tables, native Word equations, references, and the reproducibility appendix.
- Established the version naming rule: minor revisions advance `v2.x`, while a substantial model or paper rewrite advances to `v3`.

## Workflow and Template Changelog

This section records generation-pipeline, online-preview, test, and reusable-template changes that do not alter the formal paper. These changes do not modify the paper release timestamp.

### 2026-08-13 13:26 UTC+8 — Repository Agent Guidance

- Added a concise repository-level `AGENTS.md` covering only instruction entry points, dirty-worktree protection, preservation of manual DOCX edits, and release-validation boundaries without duplicating the personalized modeling workflow.

### 2026-08-13 13:20 UTC+8 — Template Naming Adjustment

- Simplified the workflow title from “Our Personalized Mathematical Modeling Workflow and Paper Template” to “Personalized Mathematical Modeling Workflow and Paper Template” by removing the unnecessary possessive qualifier.

### 2026-08-13 13:03 UTC+8 — Personalized Template v1.1

- Codified the dual-target Markdown workflow for the Pandoc/DOCX source and the generated GitHub preview in both the human workflow and machine-readable profile.
- Added verified rule promotion: only rules backed by a real artifact or official renderer, reusable across projects, and compatible with official requirements and user decisions may be promoted, with source and date recorded.
- Added template contract tests covering the dual-target syntax, four required release artifacts, and promotion gates.

### 2026-08-13 12:55 UTC+8 — GitHub Online Preview

- Added a generated GitHub preview that renders all 178 mathematical expressions, four citation superscripts, and all 11 image widths correctly.
- Kept the Pandoc source and formal DOCX unchanged; the preview is generator-owned and must not be edited manually.

### 2026-08-13 12:32 UTC+8 — Word Table Generation Pipeline

- Synchronized the user-corrected Table 2, Table 8, and Table 10 widths and table-cell alignments back into the DOCX postprocessor and regression tests.
- Did not rebuild or overwrite the published v2.4 DOCX.

### 2026-08-13 05:06 UTC+8 — Personalized Template v1.0

- Added the full project retrospective, personalized modeling workflow, and machine-readable paper profile for future project kickoff and context recovery.

## Repository Layout

```text
MCM/
|-- AGENTS.md                      # Repository-level agent operating rules
|-- projects/
|   `-- 2026-summer-assignment/
|       |-- problem-statements/       # Original assignment statements
|       `-- solutions/
|           `-- problem-a-ambulance-dispatch/
|               |-- analysis/         # Modeling report and terminology
|               |-- figures/          # Publication figures (PNG and SVG)
|               |-- paper/vX.Y/       # Pandoc source, GitHub preview, DOCX, and manifest
|               |-- results/          # Reproducible result tables and manifest
|               |-- src/              # Optimization, simulation, and plotting code
|               |-- templates/        # Personalized workflow, paper profile, and reusable prompts
|               |-- tests/            # Model and document regression tests
|               `-- utils/            # Project-specific helpers
`-- shared/
    |-- references/                    # Reusable modeling references
    `-- templates/                     # Retained Word template and inspection tools
```

## Repository Conventions

- Original prompts use the suffix `-statement` and live under each assignment's `problem-statements/` directory.
- Solutions are self-contained under `solutions/` with separate source, tests, analysis, results, figures, and paper directories.
- Retrospectives and personalized workflows live under each solution's `analysis/` and `templates/` directories for future project kickoff and context recovery.
- Every new paper release must add its version directory and update the release notes in both the Chinese `README.md` and English `README_EN.md` in the same commit; release timestamps use `YYYY-MM-DD HH:MM UTC+8`.
- Update the paper release timestamp only when the formal paper deliverable changes; record preview, generator, test, and template changes in the separate workflow and template changelog.
- Reusable templates and reference material live under `shared/`.
- Generated caches and local scratch files remain outside version history.

No license is granted by default. Problem statements and third-party reference material remain subject to their original rights.
