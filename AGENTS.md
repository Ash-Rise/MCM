# MCM Agent Entry

This repository is operated primarily by AI agents under human supervision. Keep this file short: it is a router and boundary list, not a workflow manual.

## 1. Read the right authority

Before substantive work, locate the active project and use the source that owns the question:

- problem facts / requirements → original problem statement; for DOCX, PDF, image, or another format unsuitable for repeated machine reading, create a Markdown reading derivative as the default machine-reading interface before substantive modeling, while the original remains authoritative and controls every discrepancy;
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

When continuing an existing project, first look within that project for `state.md`, a handoff, or a similarly scoped recovery/status document, and read any relevant file that exists before resuming substantive work. Use it only to recover current context and execution boundaries; it does not replace the original problem statement, Governance, Accepted Decisions, or the relevant playbook method. A new project does not require a handoff or state file when none exists.

At the start of a major repository task or before creating a branch, inspect the working tree and refresh available upstream refs. Do not assume a local integration branch contains the latest authority; if local and upstream state differ, reconcile or explicitly isolate user work before continuing.

Do not infer project semantics from code, tests, results, README, generated files, or modification time when an authoritative problem statement or Accepted Decision exists.

For such a derivative, preserve all text, tables, formulas, units, numbering, and annotations that can affect problem meaning, and explicitly mark anything that cannot be transcribed reliably. Check high-impact content—especially numerical tables, formulas, key constraints, units, and ambiguous wording—against the original. If the derivative and original differ, the original problem statement always controls. Do not require SHA-256, machine-local absolute paths, full paragraph-by-paragraph mechanical verification, or a conversion manifest with no consumer by default; add hashes or stricter verification only when provenance, version confusion, or extraction correctness is a real project risk. The derivative is never a new problem-fact authority.

## 2. Human decisions vs AI autonomy

Handle ordinary implementation and reversible technical choices autonomously.

Before changing problem interpretation, model semantics, important assumptions, objectives, hard constraints, evaluation metrics, allowed resources, substantive scope, or final conclusion interpretation, follow the Question Gate in `MCM_AI_Governance.md`. If the choice is human-owned and significant, investigate first and present a Decision Proposal rather than silently changing project meaning.

If a request conflicts with an Accepted Decision, stop before editing files or executing downstream work. Identify the conflicting Decision and material impact, then ask for explicit confirmation to supersede it. A direct instruction to make the conflicting change is not, by itself, sufficient supersession confirmation.

Consequential AI-owned technical decisions may proceed without approval, but surface them in the next meaningful Uncertainty & Decision Report.

## 3. State and decisions

Use a short project-local `decisions.md` only for Accepted significant decisions. Never turn it into a diary or experiment log; supersede old decisions explicitly rather than silently rewriting their meaning.

Create or maintain one project-local current `state.md` only when long-running or multi-phase work needs durable recovery. Keep it current and compact; do not accumulate session history. Update it at meaningful checkpoints, especially before a session ends, a costly run starts/stops, or a human decision handoff occurs.

`state.md` is not a project summary; omit information recoverable from decisions, accepted results, paper, or Git unless it is necessary for the current execution frontier.

## 4. Method routing

For substantive modeling, experiment design, analysis, paper drafting, or document production, read only the relevant playbook section before doing that work. The playbook is a method reference, not a governance authority; `MCM_AI_Governance.md`, the problem statement, and Accepted Decisions take precedence on process boundaries and project semantics.

External skills and helper tools are also execution aids, not project authority. Skip any fixed gate, mandatory artifact set, validation ceremony, or stage vocabulary they prescribe when the current repository authority does not require it.

Codex bundled/Skill Python is a tool runtime, never the repository interpreter. Resolve repository Python from explicit project commands, `.venv`, project configuration, then user PATH; verify imports and run or install with that same `sys.executable` (`<python> -m pip`), and never infer project dependencies or change algorithms from a tool runtime.

Do not load the whole playbook merely because it exists.

## 5. Evidence and completion

Validate the affected failure/risk surface rather than running every historical gate by default. Where downstream artifacts encode accepted semantics, verify against the relevant upstream authority, not only against each other.

Before materially increasing research, simulation, validation, or agent complexity, identify what consequential uncertainty the extra evidence could change and use the smallest credible test first.

At a meaningful modeling/design phase boundary, provide a concise Uncertainty & Decision Report covering substantive uncertainties, Accepted Decisions, consequential AI-owned decisions, superseded decisions, and unresolved items. Do not report trivial implementation details.

## 6. Repository hygiene

Do not modify unrelated user work. Keep generated/process artifacts only when they have a current consumer or authority role. Git preserves history; do not duplicate history through version-copy clutter or permanent incident archives.

Use the stable integration branch for ordinary project work. Use a dedicated temporary branch and pull request only for implementation changes with substantial integration risk, or for final integration or freeze when human review would materially reduce risk. A semantic change requires a Decision Proposal regardless of whether a PR is later used; approving project meaning and reviewing implementation integration are separate responsibilities. Once such a change is reviewable, push the branch, open one PR, report its purpose, material impact, validation, and unresolved issues, and leave it unmerged for human review or explicit user merge direction. AI may assist mechanical checks, but an AI reviewer is not a required gate and does not replace human approval.
