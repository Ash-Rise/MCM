# MCM

Long-lived workspace for mathematical-modeling coursework, practice, and competitions.

## Projects

- [`2026 Summer Assignment`](projects/2026-summer-assignment/README.md)
- Current deliverable: [`A题论文(v2.2).docx`](projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/paper/A题论文(v2.2).docx)

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
|               |-- paper/            # Versioned paper and conversion manifest
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
- Reusable templates and reference material live under `shared/`.
- Generated caches and local scratch files remain outside version history.

No license is granted by default. Problem statements and third-party reference material remain subject to their original rights.
