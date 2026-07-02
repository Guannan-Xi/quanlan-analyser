# QLanalyser Inline Epilepsy Workbench Release E2E Receipt

Date: 2026-06-29

## Scope

Implemented and verified the epilepsy-like event analysis workbench as a child page inside the main QLanalyser navigation frame.

The flow is:

1. Data preparation confirmed.
2. Analysis task page opens the inline epilepsy workbench.
3. User clicks start screening/staging inside the workbench.
4. Frontend calls the real `epilepsy_ml` backend workflow.
5. UI reads this task's artifacts and renders Stage_Code, candidate events, waveform evidence, video availability, spectrogram evidence, and manual correction draft controls.
6. Draft correction can be saved and then published to the results view.

## Key Evidence

- UI contract E2E: `work/release_evidence/20260628-main-epilepsy-entry-contract/main_epilepsy_entry_contract.json`
- Real API/artifact E2E: `work/release_evidence/20260629-epilepsy-release-e2e/main_epilepsy_entry_real_path.json`
- Completed UI screenshot: `work/release_evidence/20260629-epilepsy-release-e2e/03_inline_console_completed.png`
- Backend API contract acceptance: `work/release_evidence/epilepsy_source_workbench_replica_acceptance/20260629_055221`

## Verified

- Main program child page, not standalone page.
- No backend task is created by clicking the card alone.
- Task is created only after the inline workbench start button is clicked.
- Task payload uses `module_name=epilepsy_ml` and `workflow_id=epilepsy_ml_xgboost`.
- Task payload carries `data_preparation_plan_id`, `data_preparation_revision`, and `data_preparation_contract_version=qlanalyser-data-preparation-v0.2`.
- Task payload carries `non_medical_scope=research_screening_support_only`.
- Real backend task completed from the epilepsy EDF fixture.
- Artifacts include epoch predictions, events, summary, features, scaled features, and model manifest.
- UI result state is bound to real artifacts: `resultLoadStatus=ready`, `epochRows=12`, `eventRows=1`, Stage_Code text `000001100000`.
- Video panel does not fake unavailable video; it states unavailable and keeps synchronization contract.
- Spectrogram panel is labeled as candidate-event evidence, not formal PSD/Band Power/TFR.
- Manual correction supports Seizure, Normal, Needs review, Undo, Redo, Reset, save draft, and publish result.

## Verification Commands

- `node --check frontend/app.js`
- `node --check scripts/e2e_main_epilepsy_entry_contract.mjs`
- `node --check scripts/e2e_main_epilepsy_entry_real_path.mjs`
- `node --check scripts/e2e_teaching_sandbox_analysis.mjs`
- `node scripts/e2e_main_epilepsy_entry_contract.mjs`
- `node scripts/e2e_main_epilepsy_entry_real_path.mjs`
- `python -X utf8 scripts/acceptance_epilepsy_workbench_api_contract.py`
- `git diff --check -- frontend/app.js scripts/e2e_main_epilepsy_entry_contract.mjs scripts/e2e_main_epilepsy_entry_real_path.mjs`

## Remaining Follow-Up

- Replace placeholder waveform evidence with true EEG/EMG/ACC waveform windows for each selected event.
- If synchronized video metadata exists in future datasets, connect a real video player; otherwise keep unavailable state.
- Persist manual correction draft through the review-session API instead of keeping it only as local UI draft.
- Continue replacing mojibake in older static copy as a separate UI-copy cleanup slice.

final_receipt: completed_inline_epilepsy_workbench_release_e2e_ready_for_review
