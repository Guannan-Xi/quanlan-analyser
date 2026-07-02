# WaveformWorkbench Action UI Fix Receipt - 2026-06-28

## Scope

This package fixes the UI logic issue identified from the screenshot review: the right-side operation panel previously over-promoted "confirm candidate bad segment" even when there was no candidate segment, and the status area repeated too many low-level state chips.

Changed files:

- `frontend/waveform-workbench.html`
- `frontend/waveform-workbench.css`
- `frontend/waveform-workbench.js`
- `scripts/e2e_waveform_workbench_module.mjs`

No router, Headroom, gateway, IPC, model route, TimeChart, or epilepsy source workbench changes were made.

## Fixes

1. Reworked the right-side panel into:
   - Current selection and processing state.
   - Recommended action hint.
   - Draft summary.
   - Review actions.
   - Candidate actions.
   - History and recovery actions.
   - Destructive clear actions.
2. Candidate actions are hidden when there are no candidate bad segments.
3. The blue primary candidate confirmation no longer appears as the main next step when candidate count is zero.
4. When a normal waveform segment is selected, the panel promotes Reject / Remain decisions.
5. When candidate bad segments exist, the candidate confirmation/cancel controls become visible and contextually explained.
6. Status chips were reduced to necessary decision state; duplicate low-level metadata is de-emphasized.
7. Resource query versions were updated to avoid stale browser cache.

## Verification

Passed:

- `node --check frontend/waveform-workbench.js`
- `node --check scripts/e2e_waveform_workbench_module.mjs`
- UTF-8/mojibake scan for changed files
- Browser E2E: `scripts/e2e_waveform_workbench_module.mjs`

Browser E2E result:

- Status: `passed`
- Checks: `38`
- Failed: `0`
- New UI logic checks:
  - `T-UI-01-no-candidate-primary-action-when-empty`
  - `T-UI-02-selection-promotes-review-actions`
  - `T-UI-03-candidate-actions-appear-only-with-candidates`

Evidence:

- `work/release_evidence/20260628-waveform-workbench-action-ui-fix/waveform_workbench_e2e_result.json`
- `work/release_evidence/20260628-waveform-workbench-action-ui-fix/01_initial_loaded.png`
- `work/release_evidence/20260628-waveform-workbench-action-ui-fix/04_after_write_mode_draft.png`
- `work/release_evidence/20260628-waveform-workbench-action-ui-fix/04b_after_epoch_selection.png`

## Acceptance

Focused right-side action UI optimization is ready for review.

Remaining follow-up:

- Event marker density still needs visual reduction.
- Loading chip should be refined when local teaching cache is ready but backend request remains pending.
- Long-data performance still needs lightweight waveform chunk API.

## Final Receipt

`completed_waveform_workbench_action_ui_fix_ready_for_review`

