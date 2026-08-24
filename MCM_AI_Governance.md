# MCM AI Governance

> Status: implementation-ready specification; cold-resume and adversarial decision-conflict validation complete.
> Purpose: protect consequential semantics, decisions, evidence, and recovery while keeping routine AI work autonomous and lightweight.
> Scope: governance boundaries only. Modeling methods, writing craft, DOCX techniques, repository conventions, and exact formatting belong in playbooks, profiles, tools, code, tests, or project-local artifacts.

---

# 1. Governing principle

Use a small number of strong boundaries instead of many procedures.

Create a permanent governance mechanism only for a reusable, consequential failure class that existing mechanisms do not already cover. A local incident, rare mistake, or project-specific defect does not by itself justify a new rule, gate, file, test, or workflow artifact.

Governance should reduce the probability, blast radius, and recovery cost of consequential mistakes without making routine work depend on human approval or ceremony.

Historical incident lists and redesign backlogs are governance test sets, not permanent rule-production queues.

---

# 2. Decision governance

## 2.1 Significant decisions

A choice is normally significant if it can change problem interpretation, model semantics, important assumptions, objectives, hard constraints, evaluation metrics, resource boundaries, final conclusions, an important cross-stage contract, or what artifact is authoritative. It is also significant when a plausible different choice by a future capable agent could silently drift the project or cause substantial downstream rework.

Ordinary implementation choices—function structure, variable names, APIs, local refactors, plotting organization, worker count without semantic effect, temporary files, and similar details—remain autonomous and need no governance record beyond normal code/Git history.

## 2.2 Ownership

**Human-owned:** significant choices that define or materially change problem interpretation, model meaning, important assumptions, objectives, hard constraints, evaluation metrics, allowed/prohibited resources, substantive scope, or interpretation of the final modeling conclusion. The AI investigates and recommends but does not silently accept them.

**AI-owned:** consequential technical choices affecting numerical quality, reproducibility, efficiency, or implementation without changing model meaning. The AI may proceed autonomously and reports only those important enough to matter in later review.

## 2.3 Question Gate

Do not ask merely because asking is safer. Escalate only when all five conditions hold:

1. **Materiality** — the answer can materially change the model, scope, evidence, conclusion, or another consequential downstream decision.
2. **Irreducibility** — the uncertainty cannot reasonably be resolved from authoritative project material, relevant research, safe reversible assumptions, or later execution.
3. **Timing** — the answer is needed for the next meaningful step.
4. **Ownership** — the choice is human-owned.
5. **Analysis readiness** — enough investigation exists to explain the real decision space.

Otherwise decide, investigate further, defer, or continue safely.

Operationally: routine technical choices are autonomous; consequential AI-owned choices are autonomous but surfaced later when material; human-owned significant choices require a Decision Proposal before accepted project meaning changes.

**Accepted-Decision conflict rule:** if a new instruction conflicts with an Accepted Decision, stop before editing files or executing downstream work. Identify the conflicting Decision, explain the semantic and material downstream effects, and perform a Decision Review. The conflicting instruction by itself is not sufficient authorization to supersede the Accepted Decision. Execute only after the user explicitly confirms the supersession with that conflict and impact made clear.

The Question Gate is not the sole protection against drift. Stable, consequential, mechanically checkable Accepted Decisions should also receive appropriate tests or structural checks when practical.

## 2.4 Decision Proposal

Present all materially reasonable alternatives; there is no fixed option count. Alternatives must be genuinely distinct, feasible, at the same abstraction level, compatible with higher authority, and supported by a real reason someone might choose them. Never manufacture options for ceremony. A choice that contradicts the original problem or another controlling authority is a rejected/conflicting path, not a selectable proposal option, unless the user has explicitly asked to consider superseding that authority.

Compare genuine trade-offs symmetrically. If evidence clearly favors one option, present the recommendation directly together with its strongest real drawback and the evidence or condition that would change the recommendation. Before recommending, consider the strongest plausible reason it could be wrong. State uncertainty/confidence only when useful to the decision.

When the user has already proposed one concrete change that conflicts with an Accepted Decision, do not manufacture alternatives merely to satisfy this format. The required interaction is a concise Decision Review and explicit supersession confirmation.

## 2.5 Decision Ledger

After user approval and before changing the accepted model, verify the exact choice, affected project elements, conflicts with existing Accepted Decisions, important implicit assumptions, downstream effects, and whether an older Decision is superseded.

The **Decision Ledger** is authoritative for Accepted significant decisions. Default to one short project-local `decisions.md`; split only if real scale makes a single file hard to use.

Each record contains only:

```text
ID / Title
Status
Decision
Reason
Supersedes
Implications   # optional
```

Accepted Decisions are never silently rewritten. Semantic change creates a new record that explicitly supersedes the old one. Keep current effective decisions easy to scan; Git preserves detailed history.

The Ledger is not an experiment log, report, code explanation, literature review, or diary. A practical inclusion test is: if another capable agent could later make a plausible different choice and thereby change project meaning or conclusions, the accepted choice probably belongs here.

## 2.6 Human supervisory interface

The routine **semantic decision** interface contains only:

1. **Decision Proposal** — prospective approval for human-owned significant decisions.
2. **Uncertainty & Decision Report** — retrospective audit at a meaningful modeling/design phase boundary.

The report contains substantive uncertainties and how they were resolved/escalated/deferred, user-approved decisions, consequential AI-owned technical decisions, superseded decisions, and unresolved items that may matter later. Exclude trivial implementation details.

Pull-request review under §3.1 is an implementation integration boundary, not a third semantic decision mechanism. It checks whether implementation and evidence faithfully realize accepted upstream meaning; it does not authorize a human-owned semantic change that should have gone through a Decision Proposal first.

---

# 3. Authority and protected transitions

Authority is category-specific; no artifact is globally authoritative because it is newer, more detailed, generated later, or internally consistent.

| Information category | Authority |
|---|---|
| Problem facts and requirements | Original problem statement |
| Accepted significant decisions | Decision Ledger |
| Current implementation | Source code |
| Formal numerical evidence | Accepted/frozen results |
| Paper content | `paper.md` |
| User-approved manual Word layout | approved `paper.docx` |
| Modeling/writing methods | modeling playbook |
| Exact formatting parameters | formatting/profile YAML |
| Historical state and rollback | Git |
| Published version identity | Git Tag / Release |

An artifact may establish facts only within its authority category. Code, tests, results, README, generated artifacts, and modification time cannot silently redefine an Accepted Decision. A passing test proves consistency with the tested contract, not correctness of the contract itself. Layout authority is not model/content authority. Git records history but does not define current semantic truth.

Downstream work should consume accepted upstream state rather than recreate, bypass, or redefine it. A downstream stage may rely on an upstream artifact only after the acceptance condition appropriate to that artifact has been satisfied. Governance does not require fixed G0/G1/G2/G3 stage names.

## 3.1 Implementation integration boundary

A pull request is required when an implementation change has **substantial integration risk**: a plausible defect could silently propagate across multiple authoritative or downstream artifacts, or reviewing the exact proposed state would materially reduce the risk of integrating it. A PR is an engineering integration boundary, not a label for every consequential choice.

Semantic significance and implementation integration risk are separate:

- a human-owned semantic change always requires a Decision Proposal before accepted project meaning changes;
- after approval, implementing that decision requires a PR only when the implementation has substantial integration risk;
- a semantics-preserving change may still require a PR when it is broad, difficult to verify, or risky to integrate;
- touching results, paper, governance, or another important file does not by itself trigger a PR.

Typical PR triggers include:

- a broad rewrite of core modeling, optimization, simulation, or experiment infrastructure where a defect could silently change results;
- a migration of a cross-stage schema, contract, or data pipeline with multiple downstream consumers;
- replacing a major computational engine while intending to preserve accepted semantics;
- regenerating formal evidence and conclusions through a broad implementation change;
- final integration or freeze of a substantial project result before release or submission.

A small implementation of an already approved decision, routine wording or formatting edits, ordinary local refactors, localized tooling or test changes, and localized semantics-preserving performance work do not require a PR merely because the surrounding project is important.

When this boundary applies:

1. create or use a dedicated branch for one coherent integration change;
2. implement the change and perform only the impact-scoped validation justified by §5;
3. when the exact change set is reviewable, push the branch and open one pull request against the normal integration branch;
4. make the PR description and the accompanying report identify the purpose, material impact, relevant Accepted Decisions, authoritative artifacts affected, validation/evidence performed, and unresolved review questions;
5. stop before merge, report the change in detail to the user, and wait for human review and explicit merge direction;
6. use AI review only as optional assistance for diff inspection, consistency checks, or evidence lookup; it is not a required gate and does not replace human approval.

The human review asks whether the implementation faithfully realizes accepted decisions, whether affected evidence and conclusions remain valid, and whether the integration introduces unintended scope or semantic drift. Its outcome should be merge, targeted correction, or defer/escalate.

PR review never substitutes for the Question Gate. If a change requires a human-owned significant decision, obtain that decision before implementation. Conversely, an approved Decision Proposal does not by itself require a PR when the resulting implementation has low integration risk.

---

# 4. State and recovery

Persistent state exists only when an execution frontier must survive context loss, session changes, long runtime, or multi-phase work. Ordinary bounded tasks need no state artifact.

When needed, prefer one project-local current `state.md`, versioned with the project when repository-backed. It is current working memory, not a chronological log: keep it short and replace/compact stale entries rather than accumulating sessions.

Useful live fields are:

```text
Objective
Phase
Completed      # meaningful current milestones only
In Progress
Next Actions
Blockers
Pending Decisions
Rejected / Do Not Repeat   # only while operationally relevant
```

Do not duplicate the Decision Ledger, full design documents, permanent rules, large historical TODO lists, or raw reasoning history.

`state.md` is not a project summary. If information can be recovered directly from `decisions.md`, accepted/frozen results, `paper.md`, or Git and is not needed to determine the next action, omit it from `state.md`.

Update state only at meaningful checkpoints such as phase transitions, major conclusions/rejections, before or after costly runs, true blockers, before a human decision handoff, and session stop/switch.

When active work ends, `state.md` stops being an authority for future project meaning. Promote durable decisions to the Ledger, genuinely reusable methods to the playbook, and leave ordinary execution history to Git.

Cold resume from durable project state rather than compressed chat memory alone:

```text
AGENTS.md
→ original problem / current task goal
→ Accepted Decisions
→ state.md if present
→ current repository/results as needed
→ relevant playbook sections on demand
```

For retrospective workflow analysis, use compressed project notes as the historical index and return to the original long conversation only for exact wording, chronology, evidence, or omitted detail.

Do not move a long-running reasoning task to a fresh context merely because the conversation is large. First durably consolidate active state and pass a cold-resume test.

---

# 5. Evidence and validation

**Validation** asks whether an implementation/artifact/transformation is reliable for its intended role. **Evidence** supports a modeling claim, comparison, or conclusion. Internal consistency alone does not prove that approved semantics were preserved.

## 5.1 Failure-driven validation

Validation is driven by what changed and what could fail, not fixed ceremonies or automatic invalidation of all prior checks.

For a nontrivial check, identify:

```text
Failure: what concrete error could occur?
Detection: how will this check reveal it?
Action: what changes or stops if it fails?
Stop: what evidence is sufficient to stop checking?
```

A check without a concrete failure model or meaningful action is probably unnecessary. Existing evidence remains valid unless the thing it proves changed. Restore confidence only on the affected risk/dependency surface; full-system validation is mainly a release concern.

When downstream artifacts encode Accepted Decisions, validate against the relevant upstream authority rather than only checking downstream artifacts against each other.

Permanent regression tests protect stable, consequential, mechanically checkable invariants. Do not keep a test merely because one incident once happened. Hashes are correctness evidence only when byte identity/provenance is itself the property under test.

## 5.2 Decision-bounded evidence

Before materially increasing research, tuning, validation, simulation, or agent complexity, identify what consequential uncertainty/decision the extra evidence could change and the smallest credible test that could resolve it. Stop when more evidence is unlikely to change the action; sunk effort is not a reason to continue.

## 5.3 Expensive work

Scale expensive work only after a realistic small run shows both decision value and a viable execution path. Costly long runs should preserve useful progress across interruption at an appropriate granularity. Specific schemas, metadata, worker counts, profiling procedures, and file layouts remain implementation/playbook/tooling details unless a project-specific need makes them consequential.

## 5.4 Subagents

Subagents are evidence tools, not default reviewers. Use them only for high-impact algorithmic choices with multiple genuinely viable alternatives, no clear theoretical winner, and a smallest common pilot capable of resolving the uncertainty. Compare alternatives under the same scenarios/evidence/criteria and stop once the uncertainty is sufficiently resolved. Do not assign one advocate agent per option by default.

---

# 6. Method routing and artifact boundaries

`AGENTS.md` is the thin always-active router, not the full manual. It contains only repository-wide boundaries that must remain active plus pointers to deeper sources.

Detailed methodology belongs on demand:

- modeling/writing → modeling playbook;
- exact formatting → formatting/profile YAML;
- DOCX conversion/postprocessing → document tooling/playbook;
- project implementation conventions → project code/docs/tests.

For substantive modeling, experiment design, analysis, paper drafting, or document production, route to the relevant playbook section; do not load or duplicate the entire playbook merely because it exists.

Keep context roles separate:

```text
Decision Ledger → accepted project semantics
state.md        → current execution frontier
playbook        → reusable methods
Git             → history
```

Reusable experience enters the playbook only after it is genuinely distilled into a reusable method; raw project history is not long-term method memory.

Do not create a governance skill until repeated real projects show that it is stable, recurring, inconsistently applied without a skill, and extracting it would reduce overhead. Do not create separate artifacts merely because concepts such as Question Gate, Authority Matrix, Decision Review, blockers, handoff, or execution contract have names.

---

# 7. Governance evolution

Project experience does not create governance by default.

```text
Already covered?
├─ yes → improve execution/routing/mechanical support if needed; add no principle
└─ no
   ↓
Project-local or rare local defect?
├─ yes → fix locally; add no global governance
└─ no
   ↓
Repeated or consequential evidence of a reusable cross-project failure class?
├─ no → keep local
└─ yes
   ↓
Can an existing principle be generalized or rewritten?
├─ yes → merge/rewrite
└─ no → only then consider a new permanent rule
```

A new permanent rule must capture a general failure class, fill a real gap in existing mechanisms, and be justified by repeated evidence or a single sufficiently consequential systemic failure.

When governance changes, prefer replacement, generalization, or deletion over accumulation. There is no permanent incident backlog and no mandatory recurring governance-review ceremony. Review governance when evidence gives a reason. Remove mechanisms that repeatedly show low value relative to maintenance cost; stale rules are themselves a context-quality defect.

---

# 8. Minimal operating loop

```text
Read AGENTS + problem + Accepted Decisions + relevant current evidence
→ recover state if needed
→ investigate uncertainty autonomously
→ requested/considered change conflicts with an Accepted Decision?
   ├─ yes → STOP before edits
   │        → identify conflict + downstream impact
   │        → Decision Review
   │        → explicit supersession confirmation
   │        → new Decision supersedes old Decision
   └─ no → significant decision?
      ├─ no → AI handles
      └─ yes → human-owned?
         ├─ no → AI decides; report later if consequential
         └─ yes → complete safe analysis
                  → checkpoint state if needed
                  → Decision Proposal
                  → user approval
                  → Decision Review / Ledger update
→ substantial implementation integration risk or final freeze?
   ├─ yes → create/use dedicated branch
   └─ no → continue normally
→ implement
→ impact-scoped validation against relevant authorities
→ PR boundary applies?
   ├─ yes → push branch → open one PR → detailed report → STOP before merge
   │        → human review → merge only on explicit user direction
   └─ no → normal Git integration
→ meaningful phase end: Uncertainty & Decision Report
```

Everything else is implementation detail or optional support and should exist only when justified by the task.
