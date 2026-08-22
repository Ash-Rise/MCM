# MCM Workflow Handoff

## Purpose

This document preserves important workflow context that is not part of formal governance.

`MCM_AI_Governance.md` defines what the workflow requires.
This document explains why some design choices were made and records lessons learned from previous projects.

It should remain concise and should not become a second governance specification.

---

# Repository Philosophy

The repository is the durable source of truth.

Important project meaning should exist in:

- problem statements;
- Accepted Decisions;
- evidence/results;
- paper artifacts;
- governance documents.

Conversation history is temporary context, not project authority.

---

# Agent Roles

## Codex

Primary execution agent.

Responsible for:

- repository operations;
- code implementation;
- experiments;
- tests;
- results generation;
- Git operations.

Codex should autonomously handle ordinary implementation choices.

---

## ChatGPT / Human Review

Used for:

- consequential semantic decisions;
- evaluating modeling assumptions;
- reviewing high-impact changes;
- resolving uncertainty where human judgment is valuable.

Human involvement should focus on decisions that materially affect conclusions.

---

## ChatGPT Work

Used mainly for external information gathering.

Typical use cases:

- missing real-world parameters;
- literature search;
- external datasets;
- domain background;
- comparison of existing methods.

Work should not become a parallel project authority.

---

# Reasoning Effort

Default reasoning configuration:

- GPT-5.6 Sol
- Medium reasoning effort

Higher reasoning effort should be used selectively for difficult independent reviews or unusually complex decisions.

Maximum reasoning is not the default because excessive exploration can increase:

- unnecessary validation;
- process expansion;
- scope drift.

The goal is not maximum thinking time, but reliable progress.

---

# Lessons From Long Conversations

A single extremely long conversation can cause:

- context dilution;
- old assumptions being accidentally reused;
- excessive focus on workflow instead of the actual modeling task.

Preferred approach:

- one main conversation per major modeling problem;
- repository artifacts preserve long-term state;
- new conversations should recover context from authority files rather than old chat history.

---

# Governance Design Lessons

## Decision Proposal vs PR

These solve different problems.

Decision Proposal:

- controls semantic changes;
- decides whether project meaning should change.

Pull Request:

- controls risky implementation integration;
- checks whether a complex implementation should enter the stable branch.

A semantic change does not automatically require a PR.
A complex implementation change does not automatically require a Decision Proposal.

---

# Known Failure Modes

Avoid:

## Over-engineered validation

Validation should detect a concrete failure mode and change an action.

Avoid adding:

- unnecessary hashes;
- repeated checks;
- permanent audit artifacts;

unless they provide real value.

---

## Confusing implementation correctness with model correctness

Tests can show:

"the code matches the implemented contract."

They cannot prove:

"the contract is the correct model."

Semantic decisions require separate evaluation.

---

## Governance expansion

Do not create new mechanisms only because a failure is theoretically possible.

Every new rule should justify:

- what failure it prevents;
- why existing mechanisms cannot handle it;
- what action changes when it triggers.

---

# Starting a New Modeling Problem

Recommended startup:

1. Read:
   - AGENTS.md
   - MCM_AI_Governance.md
   - relevant methods/templates

2. Read the problem statement.

3. Understand:
   - what the problem asks;
   - key modeling difficulties;
   - important uncertainties.

4. Create decisions.md only when meaningful semantic choices appear.

5. Begin modeling and implementation.

Do not copy previous problem assumptions unless they are independently justified.

---

# Current Workflow Summary

The intended workflow is:

Problem statement
↓
Model understanding
↓
Decision Proposal when semantic uncertainty exists
↓
Implementation
↓
Experiments and evidence
↓
Paper and final artifacts

AI performs most execution.
Human focuses on consequential judgment.
