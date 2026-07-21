# QLanalyser Online Data / API / Artifact Contract

Date: 20260629
Status: finalized product-level contract baseline
Scope: Online data/API/artifact contracts for current product and epilepsy trial

## 1. Sources

Sources used:
- `docs/product/qlanalyser_full_product_complete_e2e_review_20260627.md`
- `docs/product/qlanalyser_complete_e2e_release_blocker_fixes_acceptance_20260627.md`
- `docs/product/data_preparation_adversarial_audit_and_cleanup_20260628.md`
- `docs/product/epilepsy_child_page_p0_ui_api_e2e_test_plan_20260629.md`
- `docs/product/epilepsy_inline_workbench_release_e2e_receipt_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_requirements_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_architecture_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_data_api_contract_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_e2e_test_plan_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_release_plan_20260629.md`

Sources blocked / controlled:
- External full release remains blocked by missing authorized anonymized EEG `input_manifest.json` for owner-data regression.
- AASM V3 / PSG rules are partially incorporated at architecture/category level only; full rule-level extraction remains controlled internal reference pending QA.
- GLP-ready is a workflow-support target, not a claim that the software or customer facility is GLP-certified.


## 2. Contract Families

Required contract identifiers:

```text
qlanalyser-data-preparation-v0.2
qlanalyser-waveform-scoring-workbench-v0.1
qlanalyser-online-results-v0.1
```

Epilepsy trial may use provisional epilepsy review endpoints only if the UI labels them as trial/internal and preserves source/review separation.

## 3. Data Preparation Context

Every downstream analysis/workbench route must carry:

```json
{
  "data_preparation_plan_id": "prep_001",
  "data_preparation_revision": 1,
  "data_preparation_contract_version": "qlanalyser-data-preparation-v0.2"
}
```

## 4. Formal Analysis Task

```json
{
  "task_id": "task_001",
  "workflow_id": "psd | erp | tfr | multitaper_psd | multitaper_tfr | reference_csd | pac | connectivity | epilepsy_trial",
  "input_file_id": "file_001",
  "data_preparation_plan_id": "prep_001",
  "data_preparation_revision": 1,
  "status": "queued | running | completed | failed"
}
```

QC is represented through data preparation, not as a formal method card.

## 5. Waveform Window / Chunk

```http
GET /api/eeg/files/{file_id}/waveform-window?start_sec=0&duration_sec=30&filter_profile_id=raw&max_points=2000
```

Minimum response:

```json
{
  "start_sec": 0,
  "duration_sec": 30,
  "stop_sec": 30,
  "window_key": "file:start:duration:revision",
  "request_id": "req_001",
  "source_data_revision": "rev_001",
  "channels": [],
  "times_sec": [],
  "data_uv": [],
  "metrics": {
    "server_elapsed_ms": 0,
    "read_elapsed_ms": 0,
    "filter_elapsed_ms": 0,
    "encode_elapsed_ms": 0
  }
}
```

P0a acceptable fallback: client request id protects stale responses if backend metrics/window_key are incomplete. P1 requires backend identity and metrics.

## 6. Epilepsy Review Session

```http
POST /api/tasks/{task_id}/epilepsy-review-sessions
POST /api/epilepsy-review-sessions/{session_id}/actions
POST /api/epilepsy-review-sessions/{session_id}/undo
POST /api/epilepsy-review-sessions/{session_id}/redo
POST /api/epilepsy-review-sessions/{session_id}/save
POST /api/epilepsy-review-sessions/{session_id}/publish-results
```

Review action:

```json
{
  "action_type": "change_event_label | adjust_event_interval | mark_needs_review | mark_artifact",
  "target_type": "event | interval | epoch_range",
  "before": {},
  "after": {},
  "reason": "manual review",
  "mode": "correction",
  "waveform_window_key": "file:start:duration:revision"
}
```

## 7. Results Artifact

```json
{
  "results_artifact_id": "res_001",
  "source_task_id": "task_001",
  "input_file_id": "file_001",
  "data_preparation_plan_id": "prep_001",
  "data_preparation_revision": 1,
  "review_revision_id": "rev_001",
  "artifact_labels": ["epilepsy_candidate_events_source", "scoring_review_revision"],
  "non_medical_scope": "research_support_only"
}
```

## 8. Immutability Rules

- Raw file is immutable.
- Source task artifacts are immutable.
- Manual correction creates ReviewAction entries.
- Saved review revisions are append-only in controlled modes.
- Results references artifacts; it does not mutate source outputs.


## Product-Level Release Guardrail Terms

- non-medical boundary: the product is research support only and must not claim diagnosis, treatment, or clinical triage.
- Owner data gate: external release needs authorized anonymized owner data and `input_manifest.json` regression evidence.
- non-medical boundary: the product is research support only and must not claim diagnosis, treatment, or clinical triage.

## 9. Change Log

- 2026-06-29: Created product-level data/API/artifact baseline for Online product and epilepsy trial.

## 10. Traceability / Acceptance Mapping

| Contract | Test |
| --- | --- |
| Data Preparation context | API-01 / gate tests |
| Waveform identity | API-02 / API-03 |
| Review actions | UI-07 / API session tests |
| Results artifact | UI-10 / API-04 |
