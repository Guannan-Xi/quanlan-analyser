# QLanalyser Epilepsy-like Event Screening Cloud Trial v0.1 - Export Contract Receipt

Status: passed local API slice.

## Scope

This receipt closes the backend/API part of the v0.1 review export contract:

- keep source algorithm outputs immutable;
- export a review-layer package after manual correction;
- provide customer-facing v0.1 CSV/JSON names in addition to legacy internal workbench files;
- preserve non-medical research boundary in the export package.

## Files Changed In This Slice

- `backend/api/epilepsy_workbench.py`
- `scripts/acceptance_epilepsy_workbench_api_contract.py`

The repository already contains unrelated in-progress edits. This receipt only accepts the files above for this slice.

## Export Contract Added

CSV artifacts:

- `epoch_predictions.csv`
- `candidate_events.csv`
- `manual_corrections.csv`
- `final_review_events.csv`

JSON artifacts:

- `summary.json`
- `parameters.json`
- `model_manifest.json`
- `review_revision.json`
- `scope_contract.json`

Legacy compatibility artifacts remain:

- `epilepsy_reviewed_epoch_scores`
- `epilepsy_reviewed_events`
- `epilepsy_review_actions`
- `epilepsy_review_session_manifest`

## Validation

- `python -m py_compile backend\api\epilepsy_workbench.py scripts\acceptance_epilepsy_workbench_api_contract.py` - PASS
- `python -X utf8 scripts\acceptance_epilepsy_workbench_api_contract.py` - PASS

Evidence:

- `work/release_evidence/epilepsy_source_workbench_replica_acceptance/latest_final_verdict.json`
- `work/release_evidence/epilepsy_source_workbench_replica_acceptance/20260630_000532/export.json`

## Acceptance Mapping

- Source ML task completed with `epilepsy_ml_xgboost`.
- Source artifacts include epoch predictions, candidate events, and summary.
- Review session can be created and patched.
- Manual correction is exported as `manual_corrections.csv`.
- Full epoch table is exported as `epoch_predictions.csv` with `Stage_Code`.
- Candidate events are exported as `candidate_events.csv` with `review_status`.
- Final reviewed events are exported as `final_review_events.csv`.
- Export registers all v0.1 artifact labels.
- `scope_contract.json` states research-screening-only boundary.
- Manifest keeps source artifacts readonly and review-layer-only.

## Remaining Work

The current API contract pass uses the protected teaching epilepsy fixture. The next release-gate slice must run the normal upload path with the labeled EDF fixture and assert:

- upload authorization is confirmed;
- data preparation plan/revision/contract is present in the epilepsy ML task;
- review revision carries the same data-preparation lineage;
- Results UI exposes the v0.1 export package.

final_receipt: completed_v01_review_export_contract_slice_ready_for_cloud_e2e
