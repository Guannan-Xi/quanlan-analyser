# QLanalyser Design Contract

Status: active project-level contract  
Date: 2026-06-28  
Owner: 07 PM / GPT-5.5-Codex acceptance lane

This file is the first design reference for QLanalyser UI, API, analysis modules, waveform workbenches, reports, and release gates.

Detailed project standards:

- `docs/product/qlanalyser_project_design_standard_20260628.md`
- `docs/product/qlanalyser_design_pattern_debt_scan_20260628.md`
- `docs/product/qlanalyser_refactor_roadmap_20260628.md`
- `docs/product/data_preparation_interaction_controls_state_matrix_20260628.md`

## Non-Negotiable Rules

1. QLanalyser is a research/support EEG analysis product, not a clinical diagnosis product.
2. Customer-facing controls must never look enabled when the current state cannot execute them.
3. Teaching mode, normal mode, customer demo mode, data preparation, waveform browsing, correction/review, task execution, and report export must be explicit states.
4. A UI action that changes data must be modeled as a command with an auditable outcome.
5. Analysis algorithms must be registered through stable workflow contracts: `module_name`, `workflow_id`, parameters schema, output schema, artifact labels, summary, reproducibility, and scope boundary.
6. Legacy/source algorithms must enter through adapters. Old field names should not leak across UI, API, artifacts, and reports.
7. Waveform display must use lightweight chunk/window APIs for browsing. Heavy analysis tasks are not the browsing path.
8. Every production feature needs requirements, detailed design, E2E or API verification, performance boundaries when relevant, and evidence paths.
9. Router, Headroom, gateway, IPC, front-route, and model route are protected infrastructure. Do not touch them during product refactors unless explicitly assigned.

## Design Pattern Mapping

- State: mode/page/control availability.
- Command: user actions, marking, review edits, undo/redo, export.
- Facade: task creation, waveform chunk loading, artifact listing, report packaging.
- Strategy: analysis runners and algorithms.
- Adapter: source/legacy algorithm migration and external contract normalization.
- Observer/Mediator: UI state refresh and cross-panel coordination.
- Memento: review history, undo/redo, preparation revisions.
- Chain of Responsibility: validation, auth, quota, task execution, artifact registration.

