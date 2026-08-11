# MCM Repository Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the current flat workspace into the approved long-lived `MCM` repository, verify the relocated ambulance project, and publish a private GitHub repository without local review material in its history.

**Architecture:** Assignment-level problem statements are separated from solution projects. Each solution owns its source, tests, analysis, results, figures, and paper, while shared templates and references live at repository level. Local-only archives remain on disk but outside the published Git tree.

**Tech Stack:** Git, GitHub CLI, PowerShell, Python 3.13, unittest, NumPy, pandas, SciPy

---

### Task 1: Establish the repository skeleton

**Files:**
- Create: `README.md`
- Create: `projects/2026-summer-assignment/README.md`
- Create: `projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/README.md`
- Modify: `.gitignore`
- Create: `.gitattributes`

- [ ] Create the approved English directory hierarchy.
- [ ] Document repository, assignment, and solution boundaries in the three README files.
- [ ] Ignore local archives, transient simulation files, caches, and Office lock files.
- [ ] Configure text and binary attributes for Python, Markdown, CSV, DOCX, PDF, and images.

### Task 2: Relocate and rename existing assets

**Files:**
- Move: `A题.docx` to `projects/2026-summer-assignment/problem-statements/problem-a-ambulance-dispatch-statement.docx`
- Move: `B题.docx` to `projects/2026-summer-assignment/problem-statements/problem-b-statement.docx`
- Move: `C题.docx` to `projects/2026-summer-assignment/problem-statements/problem-c-statement.docx`
- Move: `C题赛题数据包.docx` to `projects/2026-summer-assignment/problem-statements/problem-c-supporting-data.docx`
- Move: current Python, tests, analysis, task-one results, templates, and references into their approved locations.
- Move: obsolete full-run outputs, review extracts, backups, and large ZIP files into ignored `local-archives/` paths.

- [ ] Resolve and print every source and destination before moving files.
- [ ] Verify every destination stays inside the repository root.
- [ ] Move files with native PowerShell path operations.
- [ ] Confirm no required source file is missing and no destination collision occurred.

### Task 3: Repair imports and input/output paths

**Files:**
- Modify: `projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/src/ambulance_model.py`
- Modify: `projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/src/run_experiments.py`
- Modify: `projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/src/generate_figures.py`
- Modify: `projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/tests/test_ambulance_model.py`
- Modify: `projects/2026-summer-assignment/solutions/problem-a-ambulance-dispatch/tests/test_experiments.py`

- [ ] Add a single helper that resolves the assignment statement path from the solution root.
- [ ] Update CLI defaults to the relocated solution root.
- [ ] Update imports so tests run from the solution directory without installation.
- [ ] Run `python -m unittest discover -s tests -v` from the solution root and require all tests to pass.
- [ ] Run the minimal P1 command from the solution root and verify the statement hash and output paths.

### Task 4: Build a clean public-safe main history

**Files:**
- Review: all files selected by `git status --short` and `git ls-files`.

- [ ] Preserve commit `5604273` as local branch `local-baseline`.
- [ ] Stage only the approved repository tree.
- [ ] Use `git write-tree` and `git commit-tree` to create a parentless `main` root commit from the staged tree.
- [ ] Confirm teammate extracts, backups, archives, caches, and obsolete full-run results are absent from `main`.
- [ ] Re-run the complete test suite on `main`.

### Task 5: Create and verify the private GitHub repository

**Files:**
- Remote: `Ash-Rise/MCM`

- [ ] Create `Ash-Rise/MCM` with private visibility and without an auto-generated README, license, or gitignore.
- [ ] Add it as `origin` and push `main` with upstream tracking.
- [ ] Verify repository visibility, default branch, remote URL, and clean local status using `gh repo view`, `git remote -v`, and `git status --short`.
- [ ] Report the repository URL and explicitly note that changing visibility to public later exposes the entire pushed history.
