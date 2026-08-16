# MCM

[简体中文](README.md)

Long-lived workspace for mathematical-modeling coursework, practice, and competitions.

> New collaborators or their local AI agents: start with [`GET_STARTED_AI.md`](GET_STARTED_AI.md). It checks and installs VS Code, Git, and GitHub CLI before onboarding the repository workflow.

## Projects

- [`2026 Summer Assignment`](projects/2026-summer-assignment/README.md)
- Current Pandoc source: [`paper.md`](projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/paper/paper.md)
- Current Word deliverable: [`paper.docx`](projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/paper/paper.docx)
- Paper code and reproducibility materials: [`Problem A ambulance-dispatch reproduction entrypoint`](projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/README.md#reproduction)

## Problem A Project Layout

| Directory | Purpose |
|---|---|
| [`paper/`](projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/paper/) | Fixed-name current Pandoc Markdown, Word deliverable, and conversion manifest; tags preserve historical repository snapshots and Releases provide versioned Word downloads. |
| [`src/`](projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/src/) | Station planning, dispatch simulation, incident experiments, temporary-support analysis, figure generation, Word postprocessing, and unified reproduction code. |
| [`results/`](projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/results/) | Frozen outputs, replication-level data, parameter-screening results, and the [`reproduction manifest`](projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/results/复现清单.json). |
| [`figures/`](projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/figures/) | Publication figures; `raw_`, `process_`, and `result_` identify data, algorithm-process, and final-result figures. |
| [`analysis/`](projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/analysis/) | Problem analysis, terminology, figure contracts, design notes, and historical retrospectives; these are not final paper deliverables. |
| [`tests/`](projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/tests/) | Automated checks for model constraints, stochastic experiments, paper formatting, templates, and reproduction. |
| [`shared/templates/`](shared/templates/) | Repository-wide personalized workflow, machine-readable formatting profile, Word templates, and inspection tools. |
| [`utils/`](projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/utils/) | Shared helpers for figure fonts, colors, dimensions, and export formats. |
| [`docs/`](projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/docs/) | Image assets used by repository-onboarding and Git-collaboration documentation. |

```text
Problem data -> src models and simulations -> frozen results -> publication figures -> final paper
                         tests and the reproduction manifest verify the pipeline
```

## Release Notes

> The entries below describe the repository layout and workflow **as they existed when each version was released**, so they may contain paths or practices that were later retired. For current file organization, version control, and publishing rules, follow the “Repository Conventions” section, the latest “Workflow and Template Changelog” entries, and the repository-level `AGENTS.md`.

### v2.5 (2026-08-13 19:22 UTC+8)

Paper content and layout updated: 2026-08-15 04:31 UTC+8. This update completes the Task 3 emergency-response and temporary-support analysis and adopts the user's final proofreading of both the Markdown and DOCX while retaining the v2.5 version number.

This release improves the readability of the Task 2 dispatch policies, the operational clarity of the Task 3 emergency plan, the completeness of statistical comparison, and the stability of Word regeneration.

- `[~]` Rewrote Strategy B in the order of intuition, variable meaning, mathematical expression, and interpretation; completed Strategy C with its reserve-vector candidates, threshold release rule, lexicographic screening, and out-of-sample one-sided bound.
- `[~]` Consolidated the six mean improvement rates and paired 95% confidence intervals for Strategies B and C versus A into one bar chart, removed the redundant standalone paired-difference figure, and clarified time, rate, and cost units.
- `[~]` Replaced defensive negative phrasing in Tasks 1 and 3 and the model evaluation with direct statements tied to conditions, evidence, and scope.
- `[+]` Clarified the paired comparison between normal and incident-aware forecasts, defined the existing 12-vehicle emergency workflow from incident confirmation through rolling dispatch, queue handling, and mode exit, and identified the capacity bottleneck in long incidents.
- `[+]` Added a 7,000-row experiment covering zero to six temporary support vehicles, derived the 1/3/5-vehicle tiers from per-vehicle benefit, the 90% response-improvement threshold, and the 5-minute service target, and summarized response gains and marginal avoided penalties in Figure 11.
- `[~]` Updated the 29-page Word deliverable from the reviewed Markdown and re-froze the table layout proofread by the user in WPS; the paper contains 11 figures, 12 three-line tables, and 207 native Word equation objects.
- `[~]` Reduced each release to the Pandoc Markdown source, DOCX, and conversion manifest; removed the derived GitHub previews and their generation chain for v2.4—v2.5. Versions v2.1—v2.3 never contained such files.
- `[~]` Passed full evidence reproduction, conversion-manifest verification, and the 29-page A4 render review; the user-finalized WPS file retains two OMML child-order warnings in table equations and is intentionally not rewritten.
- `[~]` Promoted the manually revised complete table OOXML to the authoritative v2.5 table baseline and left-aligned Table 8's narrative execution notes; the frozen hash, save-reload regression, and rendered-page review all passed.

### v2.4 (2026-08-13 04:39 UTC+8)

This release strengthens the paper's algorithm exposition, evidence organization, and conclusion boundaries without changing the model, data, or frozen results.

- `[+]` Added implementation-aligned algorithm-design layers for all three tasks, connecting capacity analysis to lexicographic transportation planning, continuous multi-day dispatch simulation, and worst-window/PCHIP response-surface analysis.
- `[~]` Reorganized the evidence for Tasks 2 and 3: one six-metric figure now compares response, waiting, fairness, and cost, while one paired-effect figure covers citywide, incident-zone, and non-incident-zone outcomes.
- `[~]` Tightened statistical and causal language by standardizing the arrival-within-4-min metric and limiting the Task 3 conclusion to the fixed fleet and the paper's incident-intensity setting, where capacity pressure exceeds the marginal effect of forecast correction.
- `[~]` Unified paper-level presentation, including academic wording, heading hierarchy, superscript citations, equations, and three-line tables; these edits do not alter model definitions or numerical conclusions.

### v2.3 (2026-08-12 19:27 UTC+8)

This release establishes a traceable paper-delivery structure and systematically tunes reading density; the model and results remain unchanged.

- `[+]` Introduced `paper/vX.Y/` release directories containing the Pandoc Markdown source, Word deliverable, and conversion manifest for each independently inspectable version.
- `[~]` Differentiated spacing for body text, references/appendix notes, and tables, while standardizing justified body text and centered titles and captions.

### v2.2 (2026-08-12 18:45 UTC+8)

This release performs the first content-tightening and Markdown-to-Word conversion-quality pass. The three task models, frozen values, and conclusions remain unchanged.

- `[~]` Removed repetitive discussion and shortened reproduction notes so the paper focuses more directly on models, results, and interpretation.
- `[~]` Fixed math-conversion warnings and standardized fonts, headings, figures, tables, page numbers, and image alt text for a consistent Word deliverable.

### v2.1 (2026-08-12 16:41 UTC+8)

The first complete paper covering all three tasks, serving as the baseline for later content, layout, and reproducibility improvements.

- `[+]` Integrated transportation linear programming for fleet allocation, conditional nonhomogeneous Poisson dispatch simulation, and continuous-duration incident-response analysis into one end-to-end solution.
- `[+]` Shipped the supporting data-driven figures and tables, native Word equations, references, and reproducibility appendix required for a complete, verifiable deliverable.
- `[+]` Established the versioning rule: minor revisions increment `v2.x`, while a substantial model or paper rewrite advances to `v3`.

## Workflow and Template Changelog

This section records generation-pipeline, test, and reusable-template changes that do not alter the formal paper. These changes do not modify the paper release timestamp.

### 2026-08-16 20:28 UTC+8 — Global Template Entrypoint

- Moved the personalized workflow and machine-readable formatting profile from Problem A to `shared/templates/`, establishing one repository-wide entrypoint for all future modeling projects.
- Moved the template contract test with them and updated repository guidance, the Problem A README, and current-entry references in the historical retrospective; the Problem A directory now retains only project-specific evidence, retrospectives, and implementation.
- Physical Word templates and their inspection tools remain centralized in `shared/templates/`; this change does not include local untracked Word material reserved for a separate publishing workflow.
- This migration changes no v2.5 paper content, DOCX, results, figures, or release timestamp.

### 2026-08-16 20:21 UTC+8 — Personalized Template v2.0

- Reviewed the complete evolution since v1.0, released at 2026-08-13 05:06 UTC+8, covering Problem A collaboration, paper audit, Word formatting, version migration, and Git cleanup; consolidated the evidence into four executable protocols for audit, documents, appendices, and version control.
- Added a numeric-conflict evidence chain that starts from replication-level raw results, an explicit statistical formula, and an independent recalculation before checking tables, figures, and prose; agreement between manuscripts or an automated finding alone is not proof.
- Added joint structural-and-visual DOCX review, boundaries for source code in paper appendices, and classified handling of tracked, untracked, ignored, stashed, and ahead/behind Git state with precise local exclusions; upgraded the machine-readable profile and contract tests accordingly.
- This update changes only the workflow template, tests, and bilingual changelog; it does not alter the v2.5 paper, DOCX, results, figures, or release timestamp.

### 2026-08-16 19:50 UTC+8 — Fixed Paper Entrypoint and Tag-Based History

- Standardized the paper artifacts on `main` as `paper/paper.md`, `paper/paper.docx`, and `paper/paper.conversion.json`, eliminating per-version copies of Markdown and DOCX.
- Assigned historical repository state to Git tags and formal Word downloads to GitHub Releases; existing `v2.3`—`v2.5` tags and Releases remain unchanged, while future multi-project tags use `<project-id>/vX.Y`.
- Updated the generator, regression tests, collaboration guides, and personalized template v1.4. This is a path-only migration and does not change the v2.5 paper content, DOCX, or release timestamp.

### 2026-08-15 14:51 UTC+8 — Source Purpose Headers Added to the Personalized Template

- Moved the rule requiring each source file to begin with its purpose and pipeline role from the Problem A project agent guidance into the reusable modeling workflow, advancing the template to v1.3.
- Added machine-readable Python and MATLAB comment markers, source extensions, and forbidden content; the contract test now recursively inspects real source files under `src/` to prevent regression.
- This update changes only the workflow template, tests, and changelog; it does not alter the v2.5 paper, DOCX, results, figures, or release timestamp.

### 2026-08-13 23:44 UTC+8 — Strict Manual Table Lock

- Promoted the user-revised v2.5 Word tables to the new authoritative baseline; formal rebuilds must reproduce complete table OOXML when content matches, while partial layout inheritance remains draft-only.
- A table is considered locked only after baseline review, frozen-hash identity, save-reload full-table XML regression, semantic column-alignment assertions, and rendered-page inspection; a file hash alone is not evidence of correct layout.
- Codified left alignment for narrative columns and wrapped lines, the width–margin–label–font order for longer headings, and surgical OOXML-only corrections that leave unrelated DOCX parts unchanged.

### 2026-08-13 15:03 UTC+8 — Manual Word Table Baseline

- Codified that user-finalized Word/WPS tables take precedence over generic table rules in both the personalized workflow and the machine-readable profile.
- When table content is unchanged, regeneration inherits the complete manual OOXML; content drift fails closed, and layout-XML plus render checks guard against one-character lines, mixed alignment, and unexpected wrapping.

### 2026-08-13 13:26 UTC+8 — Repository Agent Guidance

- Added a concise repository-level `AGENTS.md` covering only instruction entry points, dirty-worktree protection, preservation of manual DOCX edits, and release-validation boundaries without duplicating the personalized modeling workflow.

### 2026-08-13 13:20 UTC+8 — Template Naming Adjustment

- Simplified the workflow title from “Our Personalized Mathematical Modeling Workflow and Paper Template” to “Personalized Mathematical Modeling Workflow and Paper Template” by removing the unnecessary possessive qualifier.

### 2026-08-13 13:03 UTC+8 — Personalized Template v1.1

- Codified the dual-target Markdown workflow for the Pandoc/DOCX source and the generated GitHub preview in both the human workflow and machine-readable profile.
- Added verified rule promotion: only rules backed by a real artifact or official renderer, reusable across projects, and compatible with official requirements and user decisions may be promoted, with source and date recorded.
- Added template contract tests covering the dual-target syntax, four required release artifacts, and promotion gates.

### 2026-08-13 19:10 UTC+8 — Retired Derived GitHub Previews

- Each release directory now retains only the Pandoc Markdown source, DOCX, and conversion manifest; removed the v2.4—v2.5 derived preview files, generator, and dedicated tests.
- Pandoc Markdown remains the sole editable content source and is linked directly from the README; the 12:55 preview approach is retained below as a superseded record.

### 2026-08-13 12:55 UTC+8 — GitHub Online Preview (retired at 19:10)

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
|               |-- paper/             # Fixed-name current Pandoc source, DOCX, and manifest
|               |-- results/          # Reproducible result tables and manifest
|               |-- src/              # Optimization, simulation, and plotting code
|               |-- tests/            # Model and document regression tests
|               `-- utils/            # Project-specific helpers
`-- shared/
    |-- references/                    # Reusable modeling references
    `-- templates/                     # Global workflow, format profile, Word templates, and contract tests
```

## Repository Conventions

- Original prompts use the suffix `-statement` and live under each assignment's `problem-statements/` directory.
- Solutions are self-contained under `solutions/` with separate source, tests, analysis, results, figures, and paper directories.
- Project retrospectives and decision evidence live under each solution's `analysis/` directory; the global workflow and formatting profile live in `shared/templates/` as the common project entrypoint.
- `main` retains only the fixed-name current paper artifacts. Every formal release updates both language release notes in the same commit and creates a project-qualified tag and Release; timestamps use `YYYY-MM-DD HH:MM UTC+8`.
- Use tags to inspect historical source and repository state and Releases to download versioned Word artifacts; do not copy `vX.Y` paper directories on `main`.
- Update the paper release timestamp only when the formal paper deliverable changes; record preview, generator, test, and template changes in the separate workflow and template changelog.
- Reusable templates and reference material live under `shared/`.
- Generated caches and local scratch files remain outside version history.

No license is granted by default. Problem statements and third-party reference material remain subject to their original rights.
