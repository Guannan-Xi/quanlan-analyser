# QLanalyser Epilepsy-like Event Screening Cloud Trial v0.1 - Data/API Contract

Status: document synced 2026-07-01; cloud synthetic EDF upload/preparation/screening/review/export contract accepted for customer-trial RC; formal external release still blocked by owner-approved anonymous real EEG regression.

## Contract Principles

- Uploaded EEG files are user-owned trial inputs.
- Source algorithm outputs are immutable.
- Manual review writes revision data.
- Results/export consumes both algorithm outputs and review revision.
- All outputs include non-medical boundary.

## Upload Contract

Required upload metadata:

```json
{
  "file_id": "string",
  "project_id": "string",
  "original_filename": "string",
  "detected_format": "edf",
  "upload_status": "uploaded|failed|processing",
  "size_bytes": 0,
  "duration_sec": 0,
  "sample_rate_hz": 0,
  "channel_count": 0,
  "channel_names": [],
  "read_warnings": [],
  "upload_authorization_confirmed": true
}
```

P0 accepted format: EDF.

## Data Preparation Contract

Analysis payload requires:

```json
{
  "data_preparation_plan_id": "string",
  "data_preparation_revision": 1,
  "data_preparation_contract_version": "qlanalyser-data-preparation-v0.2"
}
```

Ordinary uploaded data without confirmed preparation is gated.

## Screening Task Contract

ML task payload:

```json
{
  "project_id": "string",
  "module_name": "epilepsy_ml",
  "workflow_id": "epilepsy_ml_xgboost",
  "input_file_id": "string",
  "parameters": {
    "method": "ml_epoch_classifier",
    "eeg_channel": "EEG3",
    "epoch_length_sec": 5,
    "probability_threshold": 0.5,
    "unit_mode": "source_compatible",
    "data_preparation_plan_id": "string",
    "data_preparation_revision": 1,
    "data_preparation_contract_version": "qlanalyser-data-preparation-v0.2"
  }
}
```

STD task payload may use:

```json
{
  "module_name": "epilepsy",
  "workflow_id": "epilepsy_std_threshold"
}
```

STD is baseline/internal comparison in v0.1.

## Task Status Contract

```json
{
  "task_id": "string",
  "status": "queued|running|completed|failed",
  "progress_percent": 0,
  "current_step": "reading_eeg|extracting_features|running_model|merging_events|registering_artifacts",
  "error_id": "string",
  "error_message": "string",
  "suggested_action": "string"
}
```

## Epoch Prediction Contract

CSV/JSON row fields:

```json
{
  "epoch_index": 0,
  "start_sec": 0,
  "end_sec": 5,
  "duration_sec": 5,
  "Stage_Code": 0,
  "Stage": "Normal",
  "probability": 0.0,
  "above_threshold": false,
  "is_event_epoch": false,
  "threshold": 0.5
}
```

Stage_Code meaning for epilepsy:

- `0 = Normal`
- `1 = epilepsy-like candidate`

## Candidate Event Contract

```json
{
  "event_id": 1,
  "start_sec": 25.0,
  "end_sec": 35.0,
  "duration_sec": 10.0,
  "start_epoch": 5,
  "end_epoch": 6,
  "epoch_count": 2,
  "mean_probability": 0.0,
  "rms": 0.0,
  "max_abs_amplitude": 0.0,
  "review_status": "unreviewed|kept|excluded|modified|needs_review"
}
```

Source-compatible v0.1 rule: merge consecutive seizure-like epochs when epoch count >= 2.

## Spectrogram Contract

```json
{
  "source": "same_eeg_file_and_channel_as_active_event",
  "channel": "EEG3",
  "start_sec": 0,
  "end_sec": 30,
  "winsize_sec": 1.0,
  "noverlap_ratio": 0.75,
  "power_unit": "10log10",
  "frequencies_hz": [],
  "times_sec": [],
  "power": [],
  "vmin": 0,
  "vmax": 0
}
```

The spectrogram cannot be a placeholder image. It must match the selected event/window.

## Manual Review Action Contract

```json
{
  "action_id": "string",
  "task_id": "string",
  "file_id": "string",
  "epoch_start": 0,
  "epoch_end": 0,
  "previous_label": "Normal",
  "new_label": "epilepsy_like_candidate|normal|needs_review|artifact",
  "reason": "string",
  "editor": "string",
  "created_at": "iso8601",
  "data_preparation_plan_id": "string",
  "data_preparation_revision": 1,
  "algorithm_workflow_id": "epilepsy_ml_xgboost"
}
```

## Review Revision Contract

```json
{
  "review_revision_id": "string",
  "task_id": "string",
  "source_algorithm_artifact_ids": [],
  "reviewed_epoch_predictions": [],
  "reviewed_candidate_events": [],
  "manual_corrections": [],
  "created_by": "string",
  "created_at": "iso8601",
  "scope_contract": "research_screening_support_only"
}
```

## Export Contract

CSV:

- `epoch_predictions.csv`
- `candidate_events.csv`
- `manual_corrections.csv`
- `final_review_events.csv`

JSON:

- `summary.json`
- `parameters.json`
- `model_manifest.json`
- `review_revision.json`
- `scope_contract.json`

All exports include:

```json
{
  "non_medical_boundary": "Research screening/support only; not for diagnosis, treatment, triage, or clinical decision-making."
}
```

## Synthetic Fixture Contract

Mandatory P0 E2E fixture:

- `fixture_id = regular_epilepsy_labeled_60s_v1`
- EDF path: `work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_60s.edf`
- expected Stage_Code: `000001100000`
- expected event: `25.0-35.0 s`

## Sources Used

- Owner choice rounds, 2026-06-29.
- `docs/product/epilepsy_regular_labeled_fixture_20260629.md`
- Current `epilepsy_ml` artifact behavior.

## Change Log

- 2026-06-29: Created v0.1 data/API contract baseline.
- 2026-06-30: Synced local API receipts for upload authorization, strict preparation lineage, upload-to-export, and v0.1 export naming.
- 2026-06-30: Synced local browser upload-to-export evidence and explicit cloud release-gate separation.

## 2026-06-30 Contract Sync

Locally accepted contract evidence:

- Upload authorization: `scripts/acceptance_epilepsy_cloud_trial_upload_contract.py` passed; evidence `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-contract/upload_authorization_contract.json`.
- Strict preparation lineage: `scripts/acceptance_epilepsy_cloud_trial_upload_to_export.py` passed; evidence `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-to-export/cloud_upload_to_export_contract.json`.
- Export package: `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_export_contract_receipt_20260629.md` records local API pass for the v0.1 CSV/JSON names and non-medical boundary.
- Inline browser demo: `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_browser_e2e_receipt_20260629.md` records local browser evidence, but not an ordinary browser upload contract.

Contract status after 2026-07-01 cloud RC rerun:

- Browser-originated cloud upload-to-export request/response chain is proven for the synthetic 60 s EDF fixture.
- Results module readback of the v0.1 review/export package is proven in the same non-local browser session.
- Failure-state response contracts and customer-readable copy are covered by scoped v0.1 E2E/gate evidence.
- Cloud timing boundary for large EDF / 1GB-class files is not measured and is not claimed by v0.1.
- Anonymous real owner data regression requires owner/steward authorization before it can become formal external-release evidence.

## 2026-06-29 Contract Status Update

Locally verified contracts:

- `/api/eeg/upload` requires upload authorization for ordinary uploads and persists authorization metadata.
- `create_task` allows QC before preparation confirmation, but formal analysis requires a confirmed preparation plan for ordinary uploaded data.
- Formal task creation rejects draft preparation plans.
- Formal task creation rejects preparation plans from a different input file or project.
- `epilepsy_ml` task creation rejects workflow ids other than `epilepsy_ml_xgboost`.
- Review export registers the v0.1 CSV/JSON package:
  - `epoch_predictions.csv`
  - `candidate_events.csv`
  - `manual_corrections.csv`
  - `final_review_events.csv`
  - `summary.json`
  - `parameters.json`
  - `model_manifest.json`
  - `review_revision.json`
  - `scope_contract.json`

Contracts still requiring expanded proof:

- Formal external release: owner/steward authorized anonymous real EEG manifest and regression.
- Wider rollout: large EDF / 1GB-class storage, artifact, and timeout behavior.
- Broader product sweep: obsolete surfaces outside scoped v0.1 must not contradict the current terminology/copy contract.

## 2026-06-30 Browser Contract Sync

Local browser contract evidence is now accepted for the synthetic labeled EDF path:

- Evidence: `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/browser_upload_to_export.json`
- Status: `passed`, 29/29 checks.
- Upload request includes `upload_authorization_confirmed=true`.
- Uploaded file readback persists:
  - `upload_authorization_confirmed=true`
  - `metadata_upload_authorization_confirmed=true`
  - `upload_authorization_confirmed_at`
- Confirmed preparation plan is passed into task payload:
  - `data_preparation_plan_id`
  - `data_preparation_revision`
  - `data_preparation_contract_version=qlanalyser-data-preparation-v0.2`
- Screening task contract:
  - `module_name=epilepsy_ml`
  - `workflow_id=epilepsy_ml_xgboost`
  - `non_medical_scope=research_screening_support_only`
- Review/export contract:
  - manual correction uses internal status mapping but carries customer-facing `display_label`
  - export manifest preserves `source_artifacts_readonly=true`
  - export manifest preserves `review_layer_only=true`
  - Results page can see the local review package.

## 2026-07-01 Cloud Contract Acceptance Sync

Cloud contract status:

```text
cloud synthetic EDF trial RC = ready_for_acceptance
formal external release = blocked_owner_manifest_missing_or_invalid
```

Evidence:

```text
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-release-gate/release_gate_result.json
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_release_gate_receipt_20260701.md
```

Accepted cloud contract details:

- Upload request includes `upload_authorization_confirmed=true`.
- Uploaded EDF metadata persists authorization readback.
- Data preparation plan is confirmed before `epilepsy_ml` task creation.
- Task payload carries `data_preparation_plan_id`, `data_preparation_revision`, and `data_preparation_contract_version`.
- Task uses `module_name=epilepsy_ml` and `workflow_id=epilepsy_ml_xgboost`.
- Inline result loading binds only current-task artifacts:
  - `tables/epilepsy_ml_epoch_predictions.csv`
  - `tables/epilepsy_ml_events.csv`
  - `data/epilepsy_ml_spectrogram.json`
- Review export registers review-layer artifacts and preserves source ML output immutability.
- Results module displays review package and result image artifacts.
- Report package includes event timeline and spectrogram images.

`Stage` field note: the source-compatible `Stage` label in epilepsy artifacts is a legacy/algorithm output label paired with `Stage_Code`; in this module it means event-screening candidate status, not sleep staging and not clinical epilepsy staging.

## Traceability / Acceptance Mapping

| Contract item | Accepted evidence | Current status |
| --- | --- | --- |
| Upload authorization | Cloud browser request/readback includes `upload_authorization_confirmed=true`. | Accepted for synthetic RC. |
| Data preparation lineage | Epilepsy task readback carries `data_preparation_plan_id`, `data_preparation_revision`, and `data_preparation_contract_version`. | Accepted for synthetic RC. |
| Workflow identity | Task uses `module_name=epilepsy_ml` and `workflow_id=epilepsy_ml_xgboost`. | Accepted for synthetic RC. |
| Current-task artifact binding | Frontend loads epoch predictions, events, and spectrogram JSON from current `task_<id>` outputs and excludes data-preparation artifacts. | Accepted. |
| Review-layer export | Export artifacts preserve `source_artifacts_readonly=true` and `review_layer_only=true`. | Accepted for synthetic RC. |
| Results/report images | Report package contains event timeline and spectrogram images. | Accepted for synthetic RC. |
| Owner real-data manifest | `input_manifest.json` is not present/validated for owner-approved anonymous EEG. | Blocks formal external release. |
