# QLanalyser Unified Review System Governance

Date: 2026-06-22

## 1. Purpose

This document defines the shared review system that must be used before product
work is considered accepted.

The review system is not a one-off checklist. It is a reusable operating layer
for:

- product review;
- page review;
- backend review;
- UI review;
- EDF flow review;
- knowledge-base refresh;
- evidence write-back;
- multi-role verification.

## 2. Core principle

Use one review core, many domain packs.

### Shared core

The shared core must always handle:

- pre-read of the latest relevant knowledge-base updates;
- task scoping;
- evidence collection;
- multi-role review rounds;
- pass / conditional pass / fail judgment;
- write-back to the page change log and review log;
- follow-up reminder items.

### Domain packs

Each department or product line must keep its own review pack:

- QLanalyser product pack;
- self-media pack;
- other department packs when needed.

The shared core should not flatten domain rules into one generic checklist.

## 3. Why this should be shared

Sharing the review core avoids:

- duplicated review logic;
- inconsistent pass criteria;
- missing evidence discipline;
- repeated forgetting of recently updated knowledge;
- separate teams inventing incompatible review formats.

## 4. Why domain packs must stay separate

Do not merge domain content blindly.

QLanalyser review rules and self-media review rules differ in:

- subject matter;
- risk model;
- evidence type;
- acceptance language;
- ownership;
- release behavior;
- output audience.

The safe architecture is:

```text
shared review core
  -> QLanalyser pack
  -> self-media pack
  -> other domain packs
```

## 5. Required review flow

Every review round should follow this sequence:

1. Read the latest related knowledge-base updates.
2. Identify the current task and owner.
3. Load the domain pack for the current department.
4. Collect evidence from UI, API, files, logs, or screenshots.
5. Review the evidence from multiple angles.
6. Classify issues as blocker / risk / note.
7. Record the result.
8. Write back what was used and what was missing.

## 6. Knowledge refresh gate

Before any review, the system must explicitly check:

- what changed since the last review;
- which knowledge cards or docs are relevant;
- whether a rule is new, updated, or deprecated;
- whether the current review needs a mini-exam or spot check.

The review system should not rely on stale memory alone.

## 7. Evidence model

The shared review core should accept the following evidence types:

- browser screenshot;
- browser trace;
- UI click path;
- API response;
- JSON artifact;
- file path;
- log excerpt;
- report package;
- diff summary;
- reviewer note.

## 8. Review output model

Every review round should be able to produce:

- objective;
- scope;
- used knowledge sources;
- adopted rules;
- skipped rules with reason;
- evidence list;
- issues found;
- pass / conditional pass / fail verdict;
- next action;
- write-back note.

## 9. Self-media integration rule

Self-media may share the same review core, but its pack must keep its own:

- content standards;
- source-grounding rules;
- visual or script QA rules;
- publication gate;
- compliance language.

The self-media pack must not replace QLanalyser product criteria.

## 10. QLanalyser integration rule

QLanalyser review must keep its own:

- product workflow gates;
- research EEG boundary;
- non-medical boundary;
- acceptance matrix;
- document and API contracts;
- EDF end-to-end evidence requirements.

The QLanalyser pack must not inherit unrelated self-media standards.

## 11. Update and maintenance rule

Whenever a department adds a new page, new gate, or new acceptance rule:

1. Update the relevant domain pack.
2. Update the page change log.
3. Update the acceptance matrix if the rule affects pass/fail.
4. Update the knowledge refresh notes if new KB content is needed.
5. Add a short review note describing what changed.

## 12. Practical merge recommendation

Recommended structure:

- one shared review system core;
- one review pack per department;
- one common log format;
- one common evidence schema;
- one common refresh gate.

Not recommended:

- one giant checklist for all departments;
- duplicated review engines per department;
- free-form review notes without write-back.
