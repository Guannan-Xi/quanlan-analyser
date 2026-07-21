---
name: qlanalyser-clean-code-quality-gate
description: Use this skill for QLanalyser code review, implementation rules, refactoring decisions, and pre-merge quality checks based on Clean Code principles adapted into verifiable engineering gates.
---

# QLanalyser Clean Code Quality Gate Skill

## Purpose

Convert Clean Code ideas into concrete, verifiable engineering gates for QLanalyser.

This skill does not reproduce the book. It applies the engineering spirit: code should express intent, functions should be small and focused, side effects should be isolated, boundaries should be clear, errors should be useful, and touched code should become safer.

## Triggers

Use this skill when:

- writing or reviewing non-trivial code
- accepting work from another thread
- refactoring duplicated logic
- designing shared services or APIs
- preparing commit, merge, push, or release
- the user asks for Clean Code, maintainability, or coding rules

## Quality Gates

### 1. Names express intent

Pass when:

- Functions, components, and services describe business or technical intent.
- Domain terms match docs: project, file, task, artifact, data_preparation_plan, QC, PSD.
- Boolean names read like true/false facts.

Fail when:

- Names such as data, temp, handle, process, newFunc hide meaning.
- UI labels, API fields, and docs use different names for the same concept.

### 2. Functions do one thing

Pass when:

- A function has one reason to change.
- Orchestration, validation, file IO, plotting, API calls, and DOM rendering are separated.
- Complex validation can be tested alone.

Fail when:

- One function mixes UI rendering, network calls, state mutation, error display, and conversion.
- Core logic cannot be checked without booting the whole app.

### 3. Boundaries are explicit

Pass when:

- The frontend talks to the backend through documented endpoints.
- Modules collaborate through plan, task, and artifact contracts.
- MNE/EEG processing is wrapped behind project-owned functions or services.

Fail when:

- A module reaches across layers into unrelated state, DOM, or global config.
- Shared JSON shapes change without docs and acceptance updates.

### 4. Duplication is controlled

Pass when:

- Repeated logic is extracted at the third occurrence, or a reason is documented.
- Small duplication is allowed only when early abstraction would be worse.

Watch closely: parameter validation, artifact naming, task status mapping, error copy, and customer-facing text.

### 5. Side effects are isolated

Pass when:

- Network calls, file writes, state registries, and artifact registration live in service/helper layers.
- Pure transformations can be tested without filesystem or browser side effects.

Fail when:

- Display code writes persistent state.
- Algorithm code directly decides customer UI copy.

### 6. Errors are useful and safe

Pass when:

- User-visible errors explain what to do next.
- Logs contain useful technical details without leaking secrets, private data, or unnecessary local paths.
- API errors use stable status codes and understandable messages.

Fail when there are blank pages, silent failures, raw stack traces, or unexplained 404s.

### 7. Tests match risk

Pass when:

- Shared services have contract tests.
- EEG/scientific outputs have synthetic-data or reference-output checks.
- Customer-facing UI has screenshot or business-flow checks.

Fail when delivery relies only on looking fine.

## Required Handoff Checklist

Every non-trivial handoff must report:

- Naming checked: pass / fail / exception
- Function responsibility checked: pass / fail / exception
- Boundary violations checked: pass / fail / exception
- Duplication checked: pass / fail / exception
- Side effects isolated: pass / fail / exception
- Error handling checked: pass / fail / exception
- Tests run: commands and results
- Remaining technical debt

## Refactoring Rule

Refactor only inside the task boundary unless the user or C0 approves a broader cleanup. Do not mix broad cleanup with feature delivery.

## Stop Conditions

Stop and ask before proceeding when:

- A shared API shape must change.
- Persisted state format or migration must change.
- Dirty files belong to another thread.
- A test would overwrite real data.
- A fix requires broad unrelated rewrites.
