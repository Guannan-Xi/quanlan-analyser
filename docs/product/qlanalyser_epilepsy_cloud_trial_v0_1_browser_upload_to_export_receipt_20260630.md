# QLanalyser Epilepsy-like Event Screening Cloud Trial v0.1 - Browser Upload-to-Export Receipt

Status: `cloud_browser_upload_to_export_passed`.

## Scope

This receipt records the browser E2E path for the v0.1 epilepsy-like event screening cloud trial candidate. It starts from an ordinary browser upload of a labeled EDF fixture, confirms data preparation, starts epilepsy-like event screening from the main analysis page, performs one manual review correction, publishes the review package, and verifies that the Results page can see the exported package.

The same chain has now passed against the cloud URL with the synthetic labeled EDF fixture. External formal release still requires owner-approved anonymous real EEG regression evidence.

## Route

```text
Browser upload -> upload authorization -> data preparation plan -> main analysis entry -> epilepsy-like event screening -> Stage_Code/candidate event verification -> manual correction -> save review draft -> publish review results -> Results visibility
```

## Script

```text
node scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs
```

## Evidence

```text
work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/browser_upload_to_export.json
work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/01_opened.png
work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/02_after_upload.png
work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/03_inline_initial.png
work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/04_results_review_package.png
```

## Result

```json
{
  "status": "passed",
  "sample_edf": "work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_60s.edf",
  "uploaded_file_id": "eeg_44bf4d2d9f51",
  "data_preparation_plan_id": "prep_b2a90c4005e9",
  "task_id": "task_f3573aab18cf",
  "review_session_id": "eprev_15a5c3aec470",
  "export_status": "exported"
}
```

## Passed Checks

- No epilepsy screening task is created before the user starts screening.
- Upload authorization is sent in the request.
- Upload authorization is persisted and visible from uploaded file readback.
- Uploaded EDF metadata is available: EDF format, 250 Hz, 5 channels, 60 seconds.
- Data preparation plan is confirmed for the uploaded file.
- Screening task payload includes `data_preparation_plan_id`, `data_preparation_revision`, and `data_preparation_contract_version=qlanalyser-data-preparation-v0.2`.
- Backend task completes with `module_name=epilepsy_ml` and `workflow_id=epilepsy_ml_xgboost`.
- Synthetic truth is preserved: Stage_Code `000001100000` and candidate event 25.0-35.0 s.
- Manual correction is saved into the review layer.
- Review results are published as a new review package.
- Results page sees the review package.
- Export keeps `research_screening_support_only` non-medical scope.
- Customer-facing review labels stay in the localized display layer; internal enum values such as `Normal` are kept only for status mapping and exported review actions carry `display_label`.
- Missing upload authorization is rejected with `UPLOAD_AUTHORIZATION_REQUIRED`.
- Starting formal epilepsy-like screening before confirming data preparation is rejected with `DATA_PREPARATION_REQUIRED`.
- Starting epilepsy-like screening with the wrong workflow id is rejected with `WORKFLOW_CONTRACT_MISMATCH`.
- The current candidate-event panel does not expose the old `Seizure / Normal / Needs review` wording, epilepsy staging wording, or diagnosis/treatment claims.

## Root-Cause Note

The earlier failing check was `upload_authorization_persisted=false`. Source inspection showed the current backend model and storage service already write and expose the authorization fields. The running backend process was older than the latest code. After restarting local backend/frontend services, the same browser E2E passed and readback contained:

```json
{
  "upload_authorization_confirmed": true,
  "metadata_upload_authorization_confirmed": true,
  "upload_authorization_confirmed_at": "2026-06-29T18:12:36.470160Z"
}
```

## Still Blocking Cloud Trial Release

- Run the same upload-to-export E2E against the real cloud/staging URL and trial account.
- Complete full customer-facing UTF-8/copy governance across the whole product surface, including obsolete standalone pages and historical evidence scripts.
- Cover remaining failure/loading/empty states: failed upload, failed screening task, failed export, and user-facing retry/support affordances.
- Measure cloud performance boundaries for upload, metadata extraction, screening, artifact loading, review save, and export.
- Run authorized anonymous owner-data regression before external release.

## Change Log

- 2026-06-30: Added local browser upload-to-export pass receipt after refreshing local services and rerunning E2E.
- 2026-06-30: Reran E2E after replacing leaked `Seizure / Normal / Needs review` UI copy with customer-facing review labels and adding `display_label` to review actions.
- 2026-06-30: Extended E2E with missing-upload-authorization rejection and customer-copy regression checks.
- 2026-06-30: Extended E2E with unconfirmed-data-preparation rejection; latest run passed 17/17 checks. Static inline child-page contract passed 13/13 checks.
- 2026-06-30: Extended E2E with wrong-workflow rejection; latest run passed 18/18 checks.
- 2026-06-30: Extended E2E with interaction contract checks: waveform-first child page, parent navigation mapping to analysis tasks, no duplicate time-scale controls, inline waveform wheel without global toast, completed progress state, same-window STFT source, and real `Stage_Code` canvas overlay toggle.

## 2026-06-30 Cloud Upload-to-Export Pass

Status: `cloud_browser_upload_to_export_passed`.

Cloud target:

```text
http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=correction-matrix-e2e9#storage
```

Cloud evidence:

```text
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/01_opened.png
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/02_after_upload.png
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/03_inline_initial.png
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/04_results_review_package.png
```

Latest cloud result:

```json
{
  "status": "passed",
  "check_count": 34,
  "failed_checks": [],
  "uploaded_file_id": "eeg_f7788b10e2f0",
  "data_preparation_plan_id": "prep_1a2f0a161df1",
  "task_id": "task_d10bc7a94fa0",
  "report_id": "report_89d7518fc9c8"
}
```

This clears the previous cloud/staging pending item for the synthetic EDF trial path. External formal release still requires owner-approved anonymous real EEG regression evidence.
