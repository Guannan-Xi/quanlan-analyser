# QLanalyser Epilepsy-like Event Screening Cloud Trial v0.1 - Upload Contract Receipt

Status: passed local API slice.

## Scope

This receipt closes P0 Slice A for the cloud trial upload path:

- uploaded EEG data must require uploader authorization confirmation;
- upload authorization must be stored on the file record and metadata payload;
- formal analysis on uploaded data must be blocked until a confirmed data-preparation plan is supplied;
- QC/metadata preparation remains allowed before the confirmed plan;
- smoke tests must follow the cloud v0.1 flow: upload -> metadata -> confirmed data preparation -> formal analysis.

## Files Changed In This Slice

- `backend/models/eeg_file.py`
- `backend/api/eeg_files.py`
- `backend/services/storage_service.py`
- `backend/services/task_service.py`
- `frontend/index.html`
- `frontend/app.js`
- `frontend/styles.css`
- `scripts/acceptance_epilepsy_cloud_trial_upload_contract.py`
- `scripts/smoke_v01_api.py`

The repository already contains unrelated in-progress edits. This receipt only accepts the files above for this slice.

## Validation

- `python -m py_compile backend\models\eeg_file.py backend\services\storage_service.py backend\api\eeg_files.py backend\services\task_service.py scripts\acceptance_epilepsy_cloud_trial_upload_contract.py scripts\smoke_v01_api.py` - PASS
- `node --check frontend\app.js` - PASS
- `python -X utf8 scripts\acceptance_epilepsy_cloud_trial_upload_contract.py` - PASS
- `python -X utf8 scripts\smoke_v01_api.py` - PASS

Evidence:

- `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-contract/upload_authorization_contract.json`

## Acceptance Mapping

- Upload without authorization returns `422 UPLOAD_AUTHORIZATION_REQUIRED`.
- Upload with authorization succeeds.
- File readback includes `upload_authorization_confirmed=true`.
- Metadata readback includes `upload_authorization_confirmed=true`.
- Formal analysis without a data-preparation plan returns `422 DATA_PREPARATION_REQUIRED`.
- Formal analysis with `data_preparation_plan_id`, `data_preparation_revision`, and `data_preparation_contract_version=qlanalyser-data-preparation-v0.2` completes in smoke.
- Report package generation still works after the data-preparation gate.

## Remaining Work

Next P0 slice should align the epilepsy review/export package with the v0.1 contract:

- CSV: `epoch_predictions.csv`, `candidate_events.csv`, `manual_corrections.csv`, `final_review_events.csv`.
- JSON: `summary.json`, `parameters.json`, `model_manifest.json`, `review_revision.json`, `scope_contract.json`.
- Results UI should expose the formal export path.

final_receipt: completed_upload_authorization_and_preparation_gate_slice_ready_for_next_p0
