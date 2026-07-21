---
name: qlanalyser-release-maintenance-gate
description: Use this skill before QLanalyser demo, pilot release, deployment, push, or maintenance handoff to verify tests, scientific outputs, UI flow, Git state, rollback notes, and unresolved risks.
---

# QLanalyser Release & Maintenance Gate Skill

## Purpose

Prevent QLanalyser from reaching a state where a feature runs locally but cannot be trusted for customer demo, Pilot release, deployment, or maintenance.

This skill covers release readiness, test strategy, scientific reproducibility, rollback, and maintenance handoff.

## Triggers

Use this skill when:

- a module is finished
- preparing a demo URL or Pilot release
- the user asks whether to push, deploy, or deliver
- reviewing another thread's final work
- preparing deployment, rollback, or maintenance notes
- the user asks what else should be tested

## Required Test Layers

### 1. Static and syntax checks

- Python compile or unit tests.
- Node syntax checks.
- Static acceptance scripts.
- Encoding checks when customer-facing text is touched.

### 2. Contract and API tests

Shared services must test:

- data_preparation_plan save, read, and update.
- revision conflict behavior.
- task reference behavior.
- artifact registration and download behavior.
- clear 4xx / 5xx error semantics.

### 3. Scientific validation

EEG analysis modules must test:

- synthetic data with known expected properties.
- comparison against MNE or another reference implementation when possible.
- explicit tolerance.
- provenance: input file, parameters, library version, plan revision.
- no clinical-diagnosis implication unless explicitly approved.

### 4. UI business-flow tests

Customer pages must test:

- the main path can be completed.
- every button has a clear target.
- unavailable features show understandable messages.
- analysis pages contain no internal, developer, or admin-setting copy.
- screenshots or browser notes are captured for review.

### 5. Pilot end-to-end smoke

Minimum path:

1. Open the entry URL.
2. Create or open a project.
3. Upload or select an EEG file.
4. Run QC / data preparation.
5. Create or select a data preparation plan.
6. Run one analysis module, such as PSD.
7. Review results.
8. Download report or artifacts.
9. Confirm failure states are understandable.

### 6. Release and maintenance checks

- GitHub baseline checked.
- Changed file scope is clear.
- No secrets, private data, or real customer data in commits.
- Rollback path is known.
- Technical debt is recorded.
- Post-deploy logs, monitoring, and backup expectations are stated.

## Release Decision Output

When this skill is used, output:

- Decision: Ready / Not ready / Ready with stated exceptions.
- Verified items.
- Unverified items.
- Blockers.
- Acceptable exceptions.
- Rollback/recovery plan.
- Maintenance handoff: owner, logs/artifacts, known debt, next check.

## Do Not Recommend Release When

- GitHub baseline is behind or diverged and unresolved.
- Public UI contains internal or developer copy.
- Shared API changed without tests and docs.
- Scientific output cannot be reproduced or explained.
- Download or report links fail silently.
- A deployed change has no rollback path.
