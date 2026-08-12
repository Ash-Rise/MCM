# MCM

Long-lived workspace for mathematical-modeling coursework, practice, and competitions.

## Projects

- [`2026 Summer Assignment`](projects/2026-summer-assignment/README.md)
- Current deliverable: [`A题论文(v2.3).docx`](projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/paper/v2.3/A题论文(v2.3).docx)

## Release Notes

### v2.3 (2026-08-12 19:27 CST)

- Matched the reference paper's paragraph density: 1.5-line body text, 1.25-line references and appendix notes, and 1.15-line table cells.
- Corrected paragraph alignment so body text remains justified while only titles, major headings, figures, and captions are centered.
- Organized every paper release under `paper/vX.Y/`, with the Markdown source, Word paper, and conversion manifest kept together.

### v2.2 (2026-08-12 18:45 CST)

- Condensed repetitive passages without changing the three tasks' models, frozen numerical results, or conclusions.
- Repaired Markdown math notation that triggered conversion warnings and tightened the reproducibility note in the appendix.
- Standardized Chinese typography, heading alignment, captions, table geometry, page numbers, and figure alternative text against the reference layout.

### v2.1 (2026-08-12 16:41 CST)

- Published the first complete three-task paper, including the transport LP for vehicle allocation, conditional-NHPP dispatch simulation, and continuous-duration emergency-response analysis.
- Included all 13 data-driven figures, eight result tables, native Word equations, references, and the reproducibility appendix.
- Established the version naming rule: minor revisions advance `v2.x`, while a substantial model or paper rewrite advances to `v3`.

## Repository Layout

```text
MCM/
|-- projects/
|   `-- 2026-summer-assignment/
|       |-- problem-statements/       # Original assignment statements
|       `-- solutions/
|           `-- problem-a-ambulance-dispatch/
|               |-- analysis/         # Modeling report and terminology
|               |-- figures/          # Publication figures (PNG and SVG)
|               |-- paper/vX.Y/       # One Markdown, DOCX, and manifest set per release
|               |-- results/          # Reproducible result tables and manifest
|               |-- src/              # Optimization, simulation, and plotting code
|               |-- tests/            # Model and document regression tests
|               `-- utils/            # Project-specific helpers
`-- shared/
    |-- references/                    # Reusable modeling references
    `-- templates/                     # Retained Word template and inspection tools
```

## Repository Conventions

- Original prompts use the suffix `-statement` and live under each assignment's `problem-statements/` directory.
- Solutions are self-contained under `solutions/` with separate source, tests, analysis, results, figures, and paper directories.
- Every new paper release must add its version directory and update the release notes in the same commit; release timestamps use `YYYY-MM-DD HH:MM CST`.
- Reusable templates and reference material live under `shared/`.
- Generated caches and local scratch files remain outside version history.

No license is granted by default. Problem statements and third-party reference material remain subject to their original rights.
