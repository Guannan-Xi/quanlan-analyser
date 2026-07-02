# QLanalyser Epilepsy Trial P0a Fix Receipt

Status: completed_internal_trial_ready_with_results_publish_pending

Date: 2026-06-29

## Scope

This receipt covers the P0a epilepsy analysis trial entry from the main QLanalyser analysis page into the inline epilepsy workbench.

The accepted flow is:

Data Preparation -> Analysis method card -> Inline Epilepsy Workbench -> Run research screening -> Waveform / Stage_Code / spectrogram evidence -> Manual correction draft.

The Results publish path remains disabled until corrected review artifacts are registered by the backend and readable through the task artifacts contract.

## Files Changed In This Slice

- `scripts/e2e_main_epilepsy_entry_contract.mjs`
- `scripts/e2e_epilepsy_child_page_p0.mjs`
- `docs/product/qlanalyser_epilepsy_trial_p0a_fix_receipt_20260629.md`

Existing implementation files from the prior slice remain the active product implementation:

- `frontend/index.html`
- `frontend/app.js`
- `scripts/validate_epilepsy_child_page_p0_contract.mjs`

## Verification

Passed:

- `node --check scripts/e2e_main_epilepsy_entry_contract.mjs`
- `node scripts/e2e_main_epilepsy_entry_contract.mjs`
- `node --check scripts/e2e_epilepsy_child_page_p0.mjs`
- `node scripts/e2e_epilepsy_child_page_p0.mjs`
- `node scripts/validate_epilepsy_child_page_p0_contract.mjs`

Evidence:

- `work/release_evidence/20260628-main-epilepsy-entry-contract/main_epilepsy_entry_contract.json`
- `work/release_evidence/20260628-main-epilepsy-entry-contract/01_main_methods_epilepsy_card.png`
- `work/release_evidence/20260628-main-epilepsy-entry-contract/02_epilepsy_console_initial_state.png`
- `work/release_evidence/20260628-main-epilepsy-entry-contract/03_main_to_epilepsy_child_page.png`
- `work/release_evidence/20260628-main-epilepsy-entry-contract/04_synchronized_spectrogram_300s.png`
- `work/release_evidence/20260629-epilepsy-child-page-p0/e2e_epilepsy_child_page_p0.json`
- `work/release_evidence/20260629-epilepsy-child-page-p0/direct_url_blocked.png`

## Acceptance Notes

- The epilepsy method card is visible in the main analysis page and opens the inline workbench inside the main navigation shell.
- Clicking the method card does not create an analysis task prematurely.
- Running screening creates an `epilepsy_ml` task with `workflow_id=epilepsy_ml_xgboost`.
- The task payload includes `data_preparation_plan_id`, `data_preparation_revision`, and `data_preparation_contract_version=qlanalyser-data-preparation-v0.2`.
- The inline workbench shows synchronized waveform, Stage_Code strip, spectrogram evidence, candidate events, and manual correction controls.
- The video panel is not shown in the current P0a scope.
- The old standalone child-page embed flow is superseded by the main inline workbench. Direct standalone access remains blocked.
- Results publish remains honest: the UI shows `结果发布待接入` and keeps publishing disabled until corrected artifacts registration/readback exists.

## Remaining Risks

- External release remains blocked until authorized real owner-data regression is available.
- Results integration needs a backend corrected-artifact registration/readback path before enabling publish.
- The current trial E2E uses mocked artifacts and API routes; it validates the user journey and payload contract, not owner-data algorithm performance.
- Some existing product files may still contain older unrelated dirty-worktree changes; this receipt only accepts the P0a epilepsy trial slice above.

## Final Receipt

final_receipt: completed_epilepsy_trial_p0a_ready_for_internal_trial_with_results_publish_pending

