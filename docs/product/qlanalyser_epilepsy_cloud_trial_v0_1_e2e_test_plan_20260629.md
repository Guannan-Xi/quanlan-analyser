# QLanalyser Epilepsy-like Event Screening Cloud Trial v0.1 - E2E Test Plan

Status: document synced 2026-07-01; cloud synthetic EDF upload-to-export E2E passed; external formal release still requires owner-approved anonymous real EEG regression.

## Test Strategy

P0 tests must prove the cloud trial path from upload to export. Local tests are useful during development but cannot replace cloud/trial E2E acceptance.

## Required Evidence Directory

Recommended path:

```text
work/release_evidence/20260629-epilepsy-cloud-trial-v0-1/
```

## Test Data

Mandatory synthetic fixture:

- `regular_epilepsy_labeled_60s.edf`
- expected `Stage_Code = 000001100000`
- expected event `25.0-35.0 s`

Optional before external formal release:

- authorized anonymous real EEG owner-data regression

## P0 E2E Cases

### T-ECT-01 Cloud Entry and Login

Steps:

1. Open cloud trial URL.
2. Log in as internal user or trial account.
3. Confirm non-medical trial boundary is visible.

Expected:

- authenticated cloud app opens
- no local URL parameter or developer step required

### T-ECT-02 Project and Upload

Steps:

1. Create/open project.
2. Upload `regular_epilepsy_labeled_60s.edf`.
3. Wait for upload and metadata extraction.

Expected:

- upload completes
- file metadata visible: name, size, duration, sampling rate, channel count, channel names, format, warnings
- upload authorization confirmation recorded

### T-ECT-03 Data Preparation Gate

Steps:

1. Try to run epilepsy-like screening before confirming preparation.
2. Confirm data preparation.

Expected:

- ordinary uploaded data is gated before confirmation
- confirmation creates plan id, revision, contract version
- analysis entry becomes available

### T-ECT-04 Workbench First View

Steps:

1. Open Epilepsy-like Event Screening workbench.

Expected:

- raw/base waveform visible before screening, or clear waveform loading state
- file/preparation state visible
- button text `开始初筛`
- no video placeholder if no synchronized video exists

### T-ECT-05 Start Screening Feedback

Steps:

1. Click `开始初筛`.

Expected:

- immediate feedback
- progress bar
- current step
- no no-op button behavior
- task can be restored after navigation

### T-ECT-06 Backend Result Correctness

Steps:

1. Wait for task completion.
2. Read epoch and event artifacts.

Expected:

- `Stage_Code = 000001100000`
- one candidate event from 25.0 to 35.0 s
- output includes model/parameter traceability
- no medical diagnostic wording

### T-ECT-07 Evidence Rendering

Steps:

1. Open result workbench.
2. Select the candidate event.

Expected:

- waveform shows event marker
- Stage_Code strip highlights epochs 5-6
- candidate table selects same event
- spectrogram uses the same window/data
- target UI sync response <= 100 ms when cached/available

### T-ECT-08 Manual Review

Steps:

1. Verify browse mode cannot write.
2. Enter Manual Review.
3. Change one epoch/range label.
4. Undo and Redo.
5. Add note/reason.

Expected:

- review draft changes only the review layer
- source algorithm output remains available
- candidate events recalculate from reviewed labels
- action log records previous/new labels, editor, time, reason, preparation version, algorithm version

### T-ECT-09 Save Review Revision

Steps:

1. Save review revision.
2. Refresh/reopen task.

Expected:

- review revision persists
- revision id visible
- Results route available

### T-ECT-10 Results Page

Steps:

1. Open Results for the task.

Expected:

- task state, file, project, algorithm version, data preparation version, candidate event count, review state, review revision, and export entry visible

### T-ECT-11 Export Package

Steps:

1. Export CSV/JSON.
2. Inspect package.

Expected CSV:

- `epoch_predictions.csv`
- `candidate_events.csv`
- `manual_corrections.csv`
- `final_review_events.csv`

Expected JSON:

- `summary.json`
- `parameters.json`
- `model_manifest.json`
- `review_revision.json`
- `scope_contract.json`

Expected:

- package includes non-medical boundary
- synthetic fixture truth is preserved

### T-ECT-12 Failure Handling

Steps:

1. Trigger unsupported format or forced backend failure in a controlled test.

Expected:

- failure reason
- error id
- suggested action
- support entry

### T-ECT-13 UI Governance

Checks:

- no clickable no-op controls
- disabled controls have reason
- no duplicated status/time/progress without distinct purpose
- no epilepsy "staging" wording in customer UI
- waveform wheel/keyboard does not trigger global toast
- mobile can view status but is not professional review P0

## Release Gates

Internal trial can pass only when:

- T-ECT-01 through T-ECT-13 pass on cloud trial or documented equivalent staging environment
- no P0 blockers remain
- synthetic fixture backend and UI results match truth

Friendly customer trial additionally requires:

- upload authorization confirmation
- error/support path
- operation guide

External formal release additionally requires:

- authorized anonymous real data regression
- performance boundary report
- security/permission review
- fuller audit and reporting

## Sources Used

- Owner choice rounds, 2026-06-29.
- Synthetic fixture document.
- Terminology contract.

## Change Log

- 2026-06-29: Created v0.1 E2E test plan baseline.
- 2026-06-30: Synced passed local E2E receipts and clarified remaining release-blocking browser/cloud cases.

## 2026-06-30 E2E Sync

Passed local E2E/acceptance evidence:

- Upload authorization and preparation gate: `python -X utf8 scripts\acceptance_epilepsy_cloud_trial_upload_contract.py`; evidence `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-contract/upload_authorization_contract.json`.
- Upload-to-export API E2E: `python -X utf8 scripts\acceptance_epilepsy_cloud_trial_upload_to_export.py`; evidence `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-to-export/cloud_upload_to_export_contract.json`.
- v0.1 export contract: `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_export_contract_receipt_20260629.md`.
- Main inline epilepsy-like event workbench local browser demo: `node scripts/e2e_main_epilepsy_entry_real_path.mjs`; evidence `work/release_evidence/20260629-epilepsy-release-e2e/main_epilepsy_entry_real_path.json` and screenshots in the same directory.

Release-blocking E2E still required:

- Cloud/staging URL plus trial account E2E.
- Browser E2E that starts with ordinary UI upload, then confirms data preparation, runs screening, saves/reviews, exports, and opens Results.
- Results module verification for the v0.1 export package.
- Cloud/staging failure-state and error-copy browser coverage; local scoped failure-state E2E has passed.
- Full obsolete-page copy governance scan; scoped v0.1 copy governance has passed.
- Cloud performance boundary.
- Owner/steward approved anonymous real data regression.

The next concrete E2E artifact remains:

```text
scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs
work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/
```

## 2026-06-29 Test Status Update

### Passed Local Tests

| Test Area | Script | Evidence | Status |
| --- | --- | --- | --- |
| Upload authorization API contract | `python -X utf8 scripts/acceptance_epilepsy_cloud_trial_upload_contract.py` | `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-contract/upload_authorization_contract.json` | passed |
| Upload-to-export API chain | `python -X utf8 scripts/acceptance_epilepsy_cloud_trial_upload_to_export.py` | `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-to-export/cloud_upload_to_export_contract.json` | passed |
| Review export contract | `python -X utf8 scripts/acceptance_epilepsy_workbench_api_contract.py` | `work/release_evidence/epilepsy_source_workbench_replica_acceptance/latest_final_verdict.json` | passed |
| Main inline workbench local browser demo | `node scripts/e2e_main_epilepsy_entry_real_path.mjs` | `work/release_evidence/20260629-epilepsy-release-e2e/main_epilepsy_entry_real_path.json` | passed |
| Child page static contract | `node scripts/validate_epilepsy_child_page_p0_contract.mjs` | `work/release_evidence/20260629-epilepsy-child-page-p0/static_epilepsy_child_page_contract.json` | passed |

### Tests Still Required Before v0.1 Release Candidate

| Required Test | Purpose |
| --- | --- |
| `scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs` | Prove the browser path from upload authorization through Results/export. |
| Cloud/staging run of the same browser E2E | Prove trial account, deployed frontend, deployed backend, storage, and artifact paths. |
| Results module export package E2E | Prove users can open the saved review package outside the workbench. |
| Scoped v0.1 copy/UTF-8 governance | Prove customer-facing text is readable and uses event-screening terminology, not epilepsy staging/diagnosis wording. Local scoped script passed; cloud/obsolete-page sweep pending. |
| Failure-state browser E2E | Prove actionable feedback for missing authorization, unconfirmed preparation, failed task, artifact load failure, review-save failure, and export failure. Local script passed; cloud/staging repeat or documented safe simulation pending. |
| Cloud performance benchmark | Prove practical trial latency for upload, metadata, screening, artifact load, review save, and export. |

### New Browser Upload-to-Export E2E Acceptance

The next browser test must cover:

1. Project creation or selection.
2. EDF file selection using `work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_60s.edf`.
3. Upload authorization checkbox required and recorded.
4. File metadata visible after upload.
5. Confirmed data preparation plan id/revision/contract.
6. Main analysis entry opens the inline workbench.
7. Start screening button shows progress and creates exactly one `epilepsy_ml_xgboost` task.
8. Completion shows Stage_Code `000001100000`.
9. Candidate event `25.0-35.0s` is visible.
10. Waveform, Stage_Code strip, and spectrogram stay synchronized on event selection.
11. Manual correction creates a review action.
12. Save review version creates a revision.
13. Export creates the v0.1 CSV/JSON package.
14. Results module shows the exported package and artifact labels.

## 2026-06-30 Local Interaction E2E Sync

Status: `local_browser_upload_to_export_interaction_pass_cloud_pending`.

Accepted local browser evidence:

```text
node scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs
work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/browser_upload_to_export.json
```

Latest local result:

- `status = passed`
- `checks = 29/29`
- start path: ordinary browser EDF upload with upload authorization
- data preparation: confirmed plan/revision/contract passed into task payload
- task: `module_name=epilepsy_ml`, `workflow_id=epilepsy_ml_xgboost`
- truth: `Stage_Code=000001100000`, candidate event `25.0-35.0s`
- review: manual correction saved with Chinese `display_label`
- export: v0.1 review package registered and visible in Results
- interaction: waveform-first child page, parent nav `workflow`, page title `癫痫样事件分析台`, no duplicate time-scale controls, inline wheel without global toast, STFT source `waveform_chunk_stft_preview`, and real `Stage_Code` canvas overlay toggle

Release gate evidence:

```text
node scripts/validate_epilepsy_cloud_trial_v0_1_release_gate.mjs
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-release-gate/release_gate_result.json
```

Historical note: before the 2026-07-01 cloud rerun, the gate intentionally reported `blocked_cloud_trial_e2e_missing` while the latest browser evidence URL was localhost. To refresh or reproduce cloud E2E evidence, run the same browser script with:

```text
QLANALYSER_FRONTEND_URL=<cloud_or_staging_frontend_url>
QLANALYSER_API_BASE_URL=<cloud_or_staging_api_url>
QLANALYSER_EPILEPSY_UPLOAD_E2E_DIR=work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export
node scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs
```

If a release job requires cloud evidence, set `QLANALYSER_REQUIRE_CLOUD=1` when running the release-gate script so localhost-only evidence fails the gate.

Current 2026-07-01 cloud RC evidence:

```text
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json
status = passed
checks = 34 / 34 passed
frontend = http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=e2e-rc-final-clean-20260701f#storage
```

Release gate readback:

```text
release_verdict = cloud_release_candidate_ready_for_acceptance
cloud_trial_rc_verdict = cloud_trial_rc_ready_for_acceptance
external_release_verdict = blocked_owner_manifest_missing_or_invalid
```

Note: the browser E2E now automatically writes to the cloud evidence directory when `QLANALYSER_FRONTEND_URL` is non-local. The explicit `QLANALYSER_EPILEPSY_UPLOAD_E2E_DIR` above is kept in the release command for audit clarity.

## 2026-06-30 Cloud Upload-to-Export Acceptance Sync

Status: `cloud_synthetic_edf_upload_to_export_passed`.

Latest cloud browser evidence:

```text
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json
```

Latest cloud result:

```json
{
  "status": "passed",
  "check_count": 34,
  "failed_checks": [],
  "uploaded_file_id": "eeg_f7788b10e2f0",
  "data_preparation_plan_id": "prep_1a2f0a161df1",
  "epilepsy_task_id": "task_d10bc7a94fa0",
  "report_id": "report_89d7518fc9c8"
}
```

This cloud E2E starts from the ordinary upload path, confirms upload authorization, creates and confirms a data preparation plan, runs `epilepsy_ml_xgboost`, verifies Stage_Code and candidate-event truth, saves manual correction actions, publishes the review package to Results, and verifies SVG result images in the report package.

The copy-boundary check now distinguishes compliant negative boundary text, such as "not for diagnosis", from unsafe positive claims. It still rejects diagnosis conclusion, confirmed diagnosis, treatment advice, or clinical triage recommendation wording.

Remaining release distinction:

- Cloud synthetic EDF trial path: ready for acceptance.
- External formal release: still requires owner-approved anonymous real EDF regression when that data package is available.

For the cloud trial acceptance run, prefer the wrapper:

```text
QLANALYSER_CLOUD_FRONTEND_URL=<cloud_or_staging_frontend_url>
QLANALYSER_CLOUD_API_BASE_URL=<cloud_or_staging_api_url>
node scripts/run_epilepsy_cloud_trial_acceptance.mjs
```

This wrapper runs cloud target preflight, cloud browser upload-to-export E2E, strict cloud release gate, and readiness packet in sequence. It writes:

```text
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-target-preflight/preflight_result.json
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-acceptance-run/acceptance_run.json
```

### 2026-06-30 Checkpoint and Cutover Test Sync

Handoff references:

```text
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_checkpoint_20260630.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_cloud_cutover_runbook_20260630.md
```

The checkpoint records the current evidence status after rerunning local contract, copy, failure-state, upload-to-export, release-gate, readiness, cloud-preflight, cloud-acceptance wrapper, owner-manifest, and owner-input packet scripts.

Required interpretation:

- `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/browser_upload_to_export.json` proves the local synthetic browser path only.
- `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json` must exist and pass before cloud trial RC can be accepted.
- `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-owner-data-manifest/owner_data_manifest_contract.json` must pass before owner real-data regression can count.
- `work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/real_dataset_regression_result.json` must exist and pass before external release can be accepted.

The E2E owner must not weaken any of the 29 required browser checks, the 6 failure-state checks, or the scoped copy governance checks to clear a release gate. If a gate fails, inspect the evidence JSON and screenshots, fix the product or environment, then rerun the same gate.

### 2026-06-30 Scoped Copy and Failure-State E2E Sync

Accepted local evidence:

```text
node scripts/validate_epilepsy_cloud_trial_v0_1_copy_governance.mjs
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-copy-governance/copy_governance_result.json

node scripts/e2e_epilepsy_failure_states_browser.mjs
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-failure-states/failure_states_browser.json

node scripts/build_epilepsy_cloud_trial_readiness_packet.mjs
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-readiness/readiness_packet.json

node scripts/run_epilepsy_cloud_trial_acceptance.mjs
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-acceptance-run/acceptance_run.json

node scripts/preflight_epilepsy_cloud_trial_target.mjs
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-target-preflight/preflight_result.json

node scripts/validate_epilepsy_owner_data_manifest_v0_1.mjs
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-owner-data-manifest/owner_data_manifest_contract.json

node scripts/build_epilepsy_cloud_trial_owner_input_packet.mjs
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-owner-input-packet/owner_input_packet.json
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-owner-input-packet/owner_input_packet.md
```

Latest local results:

- copy governance: `status=passed`; no forbidden customer-facing v0.1 terms in `frontend/index.html` / `frontend/app.js`; internal `Seizure/Normal/Needs review` labels are allowed only behind Chinese display labels.
- failure-state E2E: `status=passed`; covers missing upload authorization UI, unconfirmed preparation gate UI, forced screening failure UI, artifact load failure UI, review-save failure UI, and export failure UI.
- release gate now reads scoped copy governance evidence and separates `cloud_trial_rc_verdict` from `external_release_verdict`; external release still requires owner-data regression.
- release gate requires all 29 named upload-to-export checks to exist and pass; a generic `status=passed` JSON without the required checks is not accepted as cloud evidence.
- release gate also requires local failure-state browser E2E coverage for missing authorization, unconfirmed preparation, forced screening failure, artifact load failure, review-save failure, and export failure.
- readiness packet summarizes all current gates in one JSON: local status, cloud trial RC status, external release status, blockers, and next commands.
- readiness packet includes the owner manifest template/checklist and commands for owner manifest validation and real-data regression.
- cloud acceptance wrapper is the preferred QA command once non-local cloud frontend/API URLs are available.
- cloud target preflight verifies non-local frontend/API URLs, API `/health`, and the synthetic EDF fixture before running the longer browser E2E.
- owner-data manifest validator enforces the v0.1 method contract: 8 formal methods only, QC as data-preparation dependency, event-marker requirements for ERP/TFR/multitaper TFR/PAC, and anonymized owner authorization before real-data regression.
- owner input packet consolidates the remaining cloud/deployment and owner-data inputs into one human-readable handoff.
