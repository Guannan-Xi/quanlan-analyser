---
name: qlanalyser-team-orchestrator
description: Use this skill when the user speaks in product or customer language and QLanalyser work must be converted into team roles, task packets, boundaries, acceptance criteria, and handoff prompts.
---

# QLanalyser Team Orchestrator Skill

## Purpose

Convert user product language, customer-experience language, and business goals into executable task packets for the QLanalyser Online multi-thread team.

The user should not need to manage every development thread. The research/design thread acts as the command center: understand intent, split tasks, protect boundaries, define acceptance criteria, and decide which thread owns which work.

## Triggers

Use this skill when the user says or implies:

- assign the work
- send this to another thread
- I only want to spot-check results
- build the team
- what module should we do next
- translate product language into tasks
- sync this to framework, module, QA, or release threads

## Default Team Topology

Start with 6 standing roles. Do not expand to 10 roles at the beginning. Six roles are enough to cover design, development, acceptance, release, and maintenance.

| Role | Thread | Responsibility | Must not do |
| --- | --- | --- | --- |
| C0 Command Center | Research and Design | User intent, scientific research, architecture, module design, task splitting, final consistency | Do not get trapped in large implementation for one module |
| C1 Main Framework | Framework Development | Routes, APIs, shared services, state, tasks, artifacts, deployment base | Do not silently change module algorithms |
| C2 Module A | Module Dev 1 | Current QC and common data preparation workstation | Do not bypass shared contracts |
| C3 Module B | Module Dev 2 | Current PSD or next independent analysis module | Do not touch QC internals or the global UI shell |
| C4 Pilot Acceptance | Pilot and Acceptance | User journey, button flow, screenshots, customer-visible behavior | Do not justify implementation defects |
| C5 Quality Release | Quality, Release, Maintenance | Clean Code gate, test strategy, release checks, rollback, technical debt | Do not silently expand feature scope |

## Expansion Rules

Expand to 8-10 roles only when a real bottleneck appears:

1. UI quality repeatedly blocks customer review.
2. Regression testing slows every module delivery.
3. Deployment, release, or rollback becomes a repeated bottleneck.
4. Data governance, permission, billing, or privacy becomes complex.

Possible later roles:

- C6 UI / Customer Workflow Review
- C7 Test Automation / Scientific Validation
- C8 Data Governance / Auth / Billing
- C9 DevOps / Monitoring / Maintenance

## Required Checks Before Dispatch

1. Run the GitHub baseline flow through qlanalyser-github-baseline-sync.
2. Read current architecture, version, and module design documents.
3. Check dirty files and identify whether they belong to another thread.
4. Decide whether the task touches shared contracts.
5. Decide whether UI review or scientific validation is required.

## Required Task Packet Fields

Each packet sent to another thread must include:

- Role: what the receiving thread is responsible for.
- Goal: one concrete result for this round.
- Source of truth: required docs and skills.
- Scope you own: editable files, modules, services, and pages.
- Scope you must not touch: explicit forbidden areas.
- Required workflow: fetch, status, read docs, narrow implementation, validation, handoff.
- Acceptance criteria: visible behavior, API contracts, tests, and customer-facing copy.
- Handoff required: changed files, tests, screenshots/artifacts, assumptions, push status.

## Boundary Rules

- Module threads must not invent shared APIs without C0/C1 agreement.
- The main framework thread must not change scientific algorithm behavior without a design document.
- Acceptance threads judge observable behavior; they do not explain away defects.
- Quality/release threads may block delivery if gates fail.
- Temporary workarounds must be recorded with cleanup triggers.

## Required Output

When this skill is used, end with:

- Recommended roles.
- Task packets for C1, C2, C3, C4, and C5 when relevant.
- Work retained by C0.
- Risks and protection rules.
