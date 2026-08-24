# MCM Workflow Handoff

> **Non-authoritative historical rationale.** Current requirements live in `AGENTS.md` and `MCM_AI_Governance.md`; modeling and writing methods live in the playbook. This file preserves only background that those authorities intentionally do not carry.

## Why the repository, not chat history, is the recovery surface

Long modeling conversations repeatedly diluted current assumptions and encouraged reuse of obsolete context. The repository therefore separates problem statements, Accepted Decisions, current evidence, paper content and Git history by authority category. Conversation history remains useful for recovering exact chronology, not for defining current project meaning.

Projects use directories on the stable integration branch rather than permanent per-problem branches. Temporary branches and pull requests are reserved for changes whose implementation integration risk makes review of the exact diff valuable.

## Why semantic approval and integration review are separate

Earlier workflow revisions blurred two different failures: choosing the wrong model meaning and implementing an accepted meaning incorrectly. A Decision Proposal controls the former; a pull request can reduce the latter. Keeping them separate prevents routine edits from acquiring approval ceremony while still stopping silent semantic drift.

## Failures that shaped the current boundaries

- Validation machinery once accumulated hashes, manifests and repeated checks without a downstream action. This led to the present failure-driven rule: provenance checks are retained only where identity is itself consequential; Git carries ordinary history.
- Problem B exposed that an absent event time can be filled by a convenient assumption that silently changes a static routing problem into, or away from, a dynamic one. The lesson was not to require another artifact, but to judge ownership by semantic effect rather than by whether the source datum is missing.
- Passing code and internally consistent results have previously been mistaken for proof that the model contract was correct. This is why implementation evidence is checked against the problem statement and Accepted Decisions, not only against other downstream artifacts.

## Cold-resume intent

Recover current work from the repository authorities named in `AGENTS.md`, using this handoff only when the historical reason for a boundary matters. Do not copy its examples into project decisions or papers.
