# QLanalyser Epilepsy-like Event Screening Cloud Trial v0.1 - Upload-to-Export E2E Receipt

Status: passed local API E2E slice.

## Scope

This receipt verifies the normal uploaded-data path for the v0.1 cloud trial:

1. create a normal project;
2. upload the labeled EDF fixture with upload authorization;
3. read metadata;
4. create a confirmed data-preparation plan;
5. run `epilepsy_ml / epilepsy_ml_xgboost` with the preparation plan lineage;
6. assert the known Stage_Code truth;
7. assert the known candidate event interval;
8. create a review session;
9. apply a manual review action;
10. export the v0.1 CSV/JSON review package.

## Fixture

- Path: `work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_60s.edf`
- Expected `Stage_Code`: `000001100000`
- Expected candidate event: `25.0-35.0s`
- Expected screening channel: `EEG3`

## Files Changed In This Slice

- `scripts/acceptance_epilepsy_cloud_trial_upload_to_export.py`

The backend export and upload-gate support are covered by the earlier receipts:

- `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_upload_contract_receipt_20260629.md`
- `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_export_contract_receipt_20260629.md`

## Validation

- `python -m py_compile scripts\acceptance_epilepsy_cloud_trial_upload_to_export.py` - PASS
- `python -X utf8 scripts\acceptance_epilepsy_cloud_trial_upload_to_export.py` - PASS
- `python -X utf8 scripts\acceptance_epilepsy_cloud_trial_upload_contract.py` - PASS rerun
- `node --check frontend\app.js` - PASS rerun

Evidence:

- `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-to-export/cloud_upload_to_export_contract.json`
- `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-contract/upload_authorization_contract.json`

## Acceptance Mapping

- Upload authorization is required and recorded.
- Metadata is readable after upload.
- Data preparation plan is confirmed before formal analysis.
- Epilepsy ML task completes with the data-preparation plan/revision/contract.
- Stage_Code matches `000001100000`.
- Candidate event `25.0-35.0s` is detected.
- Review export registers the v0.1 CSV/JSON artifact names.
- `review_revision.json` carries:
  - `data_preparation_plan_id`
  - `data_preparation_revision`
  - `data_preparation_contract_version=qlanalyser-data-preparation-v0.2`
- `scope_contract.json` keeps the non-medical research-screening boundary.

## Remaining Release Candidate Work

This is API-level E2E. The next gate should be browser-level E2E from the main analysis page:

- upload/select the labeled EDF fixture in UI;
- confirm data preparation in UI;
- enter the embedded epilepsy-like event workbench;
- start screening with visible progress;
- verify waveform-first display;
- verify Stage_Code, candidate table, and spectrogram synchronize;
- perform manual correction through UI;
- export and open the Results module package.

final_receipt: completed_upload_to_export_api_e2e_ready_for_browser_e2e
