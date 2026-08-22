# MCM Agent Entry

This repository is operated primarily by AI agents under human supervision. Keep this file short: it is a router and boundary list, not a workflow manual.

## 1. Read the right authority

Before substantive work, locate the active project and use the source that owns the question:

- problem facts / requirements → original problem statement; use a verified adjacent Markdown extraction as the default reading interface when the original is not plain text, but return to the original on any discrepancy;
- accepted model meaning / assumptions / objectives / constraints → project `decisions.md` if present;
- current long-task frontier → project `state.md` if present;
- implementation → source code;
- formal numerical claims → accepted/frozen results;
- paper content → current `paper.md`;
- approved manual Word layout → approved `paper.docx`;
- modeling / analysis / writing methods → relevant section of `shared/templates/personal-modeling-playbook.md`;
- exact formatting parameters → `shared/templates/personal-paper-profile.yaml`;
- governance boundaries → `MCM_AI_Governance.md`;
- history / rollback → Git.

At the start of a major repository task or before creating a branch, inspect the working tree and refresh available upstream refs. Do not assume a local integration branch contains the latest authority; if local and upstream state differ, reconcile or explicitly isolate user work before continuing.

Do not infer project semantics from code, tests, results, README, generated files, or modification time when an authoritative problem statement or Accepted Decision exists.

When a problem statement arrives as DOCX, PDF, image, or another format that is awkward for reliable machine reading, create a same-stem Markdown extraction beside it before substantive modeling. Preserve the original unchanged, record its path and SHA-256 in the extraction, reproduce all substantive text and tables, note any content that cannot be represented faithfully, and verify the extraction against the original. The Markdown file is a reading derivative, not a replacement authority.

## 2. Human decisions vs AI autonomy

Handle ordinary implementation and reversible technical choices autonomously.

Before changing problem interpretation, model semantics, important assumptions, objectives, hard constraints, evaluation metrics, allowed resources, substantive scope, or final conclusion interpretation, follow the Question Gate in `MCM_AI_Governance.md`. If the choice is human-owned and significant, investigate first and present a Decision Proposal rather than silently changing project meaning.

If a request conflicts with an Accepted Decision, stop before editing files or executing downstream work. Identify the conflicting Decision and material impact, then ask for explicit confirmation to supersede it. A direct instruction to make the conflicting change is not, by itself, sufficient supersession confirmation.

Consequential AI-owned technical decisions may proceed without approval, but surface them in the next meaningful Uncertainty & Decision Report.

## 3. State and decisions

Use a short project-local `decisions.md` only for Accepted significant decisions. Never turn it into a diary or experiment log; supersede old decisions explicitly rather than silently rewriting their meaning.

Create or maintain one project-local current `state.md` only when long-running or multi-phase work needs durable recovery. Keep it current and compact; do not accumulate session history. Update it at meaningful checkpoints, especially before a session ends, a costly run starts/stops, or a human decision handoff occurs.

## 4. Method routing

For substantive modeling, experiment design, analysis, paper drafting, or document production, read only the relevant playbook section before doing that work. The playbook is a method reference, not a governance authority; `MCM_AI_Governance.md`, the problem statement, and Accepted Decisions take precedence on process boundaries and project semantics.

External skills and helper tools are also execution aids, not project authority. Skip any fixed gate, mandatory artifact set, validation ceremony, or stage vocabulary they prescribe when the current repository authority does not require it.

Do not load the whole playbook merely because it exists.

### Project Python environments

Codex bundled Python, `CODEX_PRIMARY_RUNTIME_PYTHON`, Skill runtimes, and Skill-private environments are tool runtimes, not project interpreters. Use them only for their own helper scripts.

Never use a tool runtime to run repository source, tests, experiments, or plotting code; to determine whether project dependencies such as NumPy, SciPy, Pandas, or Matplotlib are installed; or to change an algorithm because a tool runtime lacks a package.

Resolve the project interpreter once, in this order: repository authority or an explicit project command; a project-local `.venv`; `pyproject.toml`, `uv.lock`, or Conda configuration; only then the first Python on the user PATH. Before reporting a missing dependency, print `sys.executable` once and import the required package with that same explicit interpreter. Reuse it for project execution, tests, plotting, and installation; invoke installation as `<python> -m pip`, never bare `pip`.

Re-resolve only when the project environment changes or an import/execution error gives a concrete reason. Package availability in a tool runtime says nothing about package availability in the project environment.

## 5. Evidence and completion

Validate the affected failure/risk surface rather than running every historical gate by default. Where downstream artifacts encode accepted semantics, verify against the relevant upstream authority, not only against each other.

Before materially increasing research, simulation, validation, or agent complexity, identify what consequential uncertainty the extra evidence could change and use the smallest credible test first.

At a meaningful modeling/design phase boundary, provide a concise Uncertainty & Decision Report covering substantive uncertainties, Accepted Decisions, consequential AI-owned decisions, superseded decisions, and unresolved items. Do not report trivial implementation details.

## 6. Repository hygiene

Do not modify unrelated user work. Keep generated/process artifacts only when they have a current consumer or authority role. Git preserves history; do not duplicate history through version-copy clutter or permanent incident archives.

Use the stable integration branch for ordinary project work. Use a dedicated temporary branch and pull request only for implementation changes with substantial integration risk, or for final integration or freeze when human review would materially reduce risk. A semantic change requires a Decision Proposal regardless of whether a PR is later used; approving project meaning and reviewing implementation integration are separate responsibilities. Once such a change is reviewable, push the branch, open one PR, report its purpose, material impact, validation, and unresolved issues, and leave it unmerged for human review or explicit user merge direction. AI may assist mechanical checks, but an AI reviewer is not a required gate and does not replace human approval.
