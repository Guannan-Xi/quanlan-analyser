# Data Preparation Interaction Controls State Matrix - 2026-06-28

## Scope

This document records the release-candidate control-state fixes for the QLanalyser data preparation page. It focuses on customer-visible interaction consistency:

- Teaching mode to normal mode transition.
- Waveform browsing and editing controls.
- Data-preparation action buttons.
- Analysis entry gating.
- Legacy hidden controls that must not interfere with the customer flow.

Protected areas were not touched: router, Headroom, gateway, IPC, front-route, model route, TimeChart, and epilepsy source workbench.

## Fixed Contracts

1. Teaching mode exit must immediately refresh the page chrome.
   - `body.teaching-sandbox-active` is removed.
   - `#teachingModeBtn` returns to `data-teaching-action="start"` and `aria-pressed="false"`.
   - `teaching_demo=auto` is removed from the URL so refresh does not re-enter teaching mode.
   - Teaching demo project/file/task/draft state is cleared from the active workspace.

2. Teaching mode start failure must roll back to normal mode.
   - If `/api/lab/demo/dataset` fails, the page must not remain in teaching chrome.
   - The user gets a failure toast and stays in normal mode.

3. No-data waveform controls must be visibly unavailable.
   - Browse mode remains available.
   - Write modes (`selectSegment`, `markBadSegment`, `markBadChannel`) are disabled until an EEG file and waveform payload are available.
   - Waveform navigation, time slider, window preset, gain, and channel controls are disabled without an EEG file.
   - Disabled controls carry `aria-disabled="true"` and an explanatory title.

4. Analysis task entry must share the preparation gate.
   - `[data-view-jump="workflow"]` routes through `handleSubmitAnalysisClick()`.
   - Unconfirmed preparation keeps the user on the data preparation page and shows the preparation gate.

5. Label and draft actions must not create empty-file drafts.
   - `add-label` is disabled without a file and without a selected segment.
   - Hard-triggered `add-label` calls are blocked if `file_id` or selected segment is missing.

6. Segment mode controls must not be fake controls.
   - If visible, `data-segment="time/event"` switches the matching form and updates `aria-pressed`.
   - If hidden in the customer UI, they are treated as legacy controls and must not block or confuse the main flow.
   - Current segment settings are included in the data-preparation plan payload when confirmed.

## Verification

New state-matrix E2E:

- `scripts/e2e_data_prep_interaction_controls_state_matrix.mjs`
- Evidence JSON: `work/release_evidence/20260628-data-preparation-controls-state-matrix/data_preparation_controls_state_matrix.json`
- Screenshot: `work/release_evidence/20260628-data-preparation-controls-state-matrix/data_preparation_controls_state_matrix.png`

Required checks:

- `teaching_auto_enters_once_with_exit_button`
- `teaching_exit_refreshes_chrome`
- `teaching_exit_removes_auto_url_param`
- `no_data_write_modes_disabled_with_reason`
- `no_data_waveform_navigation_disabled`
- `no_data_label_action_disabled`
- `workflow_jump_uses_preparation_gate`
- `legacy_segment_controls_hidden_in_customer_ui` or visible segment switch checks
- `teaching_start_failure_rolls_back_chrome`

Regression checks rerun:

- `scripts/e2e_main_data_prep_canvas_chunk_interaction.mjs`
- `scripts/audit_data_preparation_page_release_candidate.mjs`
- `node --check frontend/app.js`
- `node --check scripts/e2e_data_prep_interaction_controls_state_matrix.mjs`

## Remaining Follow-Up

The broader project-level design-pattern governance task is queued after this completed receipt. It should create a project design standard and full design-debt scan before any wider refactor.
