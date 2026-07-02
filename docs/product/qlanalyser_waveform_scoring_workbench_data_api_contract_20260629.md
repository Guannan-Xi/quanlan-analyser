# QLanalyser Waveform Scoring Workbench Data / API / Artifact Contract

Date: 20260629
Status: baseline data/API/artifact contract
Scope: contracts for unified waveform scoring workbench

## 1. Sources


Sources used:
- `docs/product/qlanalyser_waveform_scoring_workbench_research_input_20260629.md`
- `docs/product/qlanalyser_pc_sleep_module_source_review_20260629.md`
- `docs/product/waveform_scoring_workbench_unified_design_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_requirements_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_architecture_20260629.md`

Sources partially read / controlled:
- Feishu PSG/sleep reference `https://quanland.feishu.cn/wiki/UevhwictEiaiOFk9tBCcatqqnge?from=from_copylink` was partially readable from the internal wiki on 2026-06-29. Status: `partial_read_from_feishu_aasm_v3_reference`; chapter-level scope, event-layer architecture, and contract categories are incorporated. Exact rule thresholds and full translated rule text remain controlled internal reference pending full QA review.


## 2. Contract Versioning

Recommended contract id:

```text
qlanalyser-waveform-scoring-workbench-v0.1
```

Data Preparation dependency remains:

```text
qlanalyser-data-preparation-v0.2
```

## 3. Core Entities

### 3.1 ScoringProfile

```json
{
  "scoring_profile_id": "profile_mouse_sleep_v1",
  "domain": "sleep_staging",
  "species": "mouse",
  "epoch_length_sec": 4,
  "stage_schema_id": "sleep_rodent_v1",
  "event_schema_ids": ["artifact_interval_v1"],
  "channel_role_schema_id": "rodent_eeg_emg_acc_v1",
  "supported_channel_count": {"min": 1, "max": 64},
  "algorithm_ids": ["optional_model_id"],
  "status": "draft | validated | locked | retired"
}
```

### 3.2 ChannelRoleSchema

```json
{
  "channel_role_schema_id": "psg_basic_v1",
  "roles": [
    {"role": "EEG", "required": true, "min": 1},
    {"role": "EOG", "required": false, "min": 0},
    {"role": "EMG", "required": false, "min": 0},
    {"role": "airflow", "required": false, "min": 0},
    {"role": "SpO2", "required": false, "min": 0}
  ]
}
```

### 3.3 StageSchema

```json
{
  "stage_schema_id": "sleep_human_basic_v1",
  "epoch_length_sec": 30,
  "labels": [
    {"code": "W", "name": "Wake", "color": "#f59e0b"},
    {"code": "N1", "name": "N1", "color": "#93c5fd"},
    {"code": "N2", "name": "N2", "color": "#2563eb"},
    {"code": "N3", "name": "N3", "color": "#1e3a8a"},
    {"code": "REM", "name": "REM", "color": "#16a34a"},
    {"code": "ART", "name": "Artifact", "color": "#6b7280"}
  ]
}
```

### 3.4 EventSchema

```json
{
  "event_schema_id": "epilepsy_event_review_v1",
  "event_types": [
    {"code": "candidate", "name": "Candidate event"},
    {"code": "artifact", "name": "Artifact"},
    {"code": "rejected", "name": "Rejected"},
    {"code": "needs_review", "name": "Needs review"}
  ],
  "severity_scales": []
}
```

Respiratory event schemas are now designed at category/schema level from the partial Feishu AASM V3 source read. Exact rule thresholds remain controlled internal reference pending full QA review.


### 3.5 RuleGrade

```json
{
  "rule_grade": "RECOMMENDED | ACCEPTABLE | OPTIONAL | INTERNAL_PROFILE",
  "rule_family": "AASM_V3 | CRO_PROFILE | RODENT_PROFILE | CUSTOM_PROTOCOL",
  "population_scope": "adult | pediatric | human_unspecified | mouse | rat | nonhuman_primate | custom",
  "citation": {
    "source_id": "aasm_v3_internal_feishu",
    "section_ref": "controlled_internal_pointer",
    "public_summary_allowed": false
  }
}
```

### 3.6 PSG / HSAT Event Contracts

```json
{
  "psg_report_parameter": {
    "parameter_id": "ahi",
    "name": "Apnea-hypopnea index",
    "value": null,
    "unit": "events/hour",
    "source_layers": ["respiratory_event", "sleep_time"],
    "rule_grade": "RECOMMENDED"
  },
  "arousal_event": {
    "event_id": "ar_001",
    "start_sec": 120.0,
    "end_sec": 126.0,
    "duration_sec": 6.0,
    "associated_event_ids": ["resp_001"],
    "evidence_channels": ["EEG", "EMG"],
    "rule_grade": "RECOMMENDED"
  },
  "respiratory_event": {
    "event_id": "resp_001",
    "type": "apnea | hypopnea | rera | desaturation_related | custom",
    "start_sec": 100.0,
    "end_sec": 114.0,
    "duration_sec": 14.0,
    "airflow_evidence": "present | absent | unavailable",
    "effort_evidence": "increase | reduced | absent | unavailable",
    "flow_limitation": "present | absent | unavailable",
    "spo2_desaturation_percent": null,
    "arousal_event_id": "ar_001",
    "population_scope": "adult | pediatric | custom",
    "rule_grade": "RECOMMENDED"
  },
  "movement_event": {
    "event_id": "mov_001",
    "type": "limb | body | artifact | custom",
    "start_sec": 300.0,
    "end_sec": 303.0,
    "evidence_channels": ["EMG", "ACC"],
    "associated_arousal_event_id": null
  },
  "cardiac_event": {
    "event_id": "card_001",
    "type": "tachycardia | bradycardia | rhythm_event | custom",
    "start_sec": 500.0,
    "end_sec": 520.0,
    "evidence_channels": ["ECG"]
  },
  "hsat_recording": {
    "recording_id": "hsat_001",
    "available_roles": ["airflow", "effort", "SpO2", "position"],
    "unsupported_layers": ["sleep_stage_if_no_eeg"],
    "report_constraints": ["reduced_channel_test"]
  }
}
```

### 3.7 TimelineState

```json
{
  "window_start_sec": 0,
  "window_duration_sec": 30,
  "selected_event_id": null,
  "selected_epoch_indices": [],
  "visible_channel_ids": [],
  "request_seq": 42
}
```

### 3.8 ReviewAction

```json
{
  "action_id": "act_001",
  "session_id": "sess_001",
  "action_type": "change_stage | change_event_label | adjust_event_interval | add_event | mark_artifact",
  "target_type": "epoch | epoch_range | event | interval | channel",
  "target": {"event_id": "evt_001"},
  "before": {"label": "candidate"},
  "after": {"label": "artifact"},
  "reason": "movement artifact",
  "user_id": "reviewer_01",
  "created_at": "ISO-8601",
  "software_version": "unknown",
  "model_version": "unknown"
}
```

### 3.9 ReviewRevision

```json
{
  "review_revision_id": "rev_001",
  "session_id": "sess_001",
  "source_task_id": "task_001",
  "data_preparation_plan_id": "prep_001",
  "data_preparation_revision": 1,
  "actions": ["act_001"],
  "status": "draft | saved | under_review | locked | published | archived"
}
```

### 3.10 Study / Protocol / Animal

```json
{
  "study_id": "STUDY-001",
  "protocol_id": "PROTO-001",
  "animal_id": "M001",
  "species": "mouse",
  "strain": "C57BL/6J",
  "sex": "male",
  "group": "vehicle",
  "treatment": "drug_a_low",
  "light_dark_cycle": "12:12",
  "glp_mode": "exploratory | cro_research_ready | glp_ready"
}
```

## 4. API Contracts

### 4.1 Waveform Chunk

```http
GET /api/eeg/files/{file_id}/waveform/chunk?start_sec=0&duration_sec=30&channels=...&mode=minmax
```

Response includes:

- start_sec;
- duration_sec;
- display_sample_rate_hz;
- channels;
- times_sec or bucket grid;
- data_uv or min/max buckets;
- request_seq.

### 4.2 Spectrogram Window

```http
GET /api/eeg/files/{file_id}/spectrogram-window?start_sec=0&duration_sec=30&channel=...&freq_min=0.5&freq_max=50&mode=review
```

Response includes:

- freqs_hz;
- times_sec;
- power_db;
- vmin/vmax;
- method;
- review_only=true.

### 4.3 Scoring Sessions

```http
POST /api/scoring-sessions/from-task/{task_id}
GET  /api/scoring-sessions/{session_id}
POST /api/scoring-sessions/{session_id}/actions
POST /api/scoring-sessions/{session_id}/undo
POST /api/scoring-sessions/{session_id}/redo
POST /api/scoring-sessions/{session_id}/save
POST /api/scoring-sessions/{session_id}/publish-results
```

### 4.4 Study / GLP-ready APIs

Planned:

```http
POST /api/studies
POST /api/protocols
GET  /api/studies/{study_id}/audit-trail
POST /api/scoring-sessions/{session_id}/lock
POST /api/scoring-sessions/{session_id}/sign
POST /api/scoring-sessions/{session_id}/archive-package
```

## 5. Artifact Labels

Recommended labels:

```text
waveform_scoring_source_output
epilepsy_candidate_events_source
sleep_stage_source_table
scoring_review_revision
scoring_review_action_log
scoring_results_artifact
glp_audit_trail_export
glp_archive_package
```

## 6. ResultsArtifact Contract

```json
{
  "results_artifact_id": "res_001",
  "domain": "epilepsy_event",
  "source_task_id": "task_001",
  "review_revision_id": "rev_001",
  "data_preparation_plan_id": "prep_001",
  "summary": {},
  "tables": [],
  "figures": [],
  "audit_log_ref": "artifact_id",
  "non_medical_scope": "research_support_only"
}
```

## 7. Immutability Rules

- Raw data is immutable.
- Data preparation plan revisions are immutable after confirmation; new changes create new revisions.
- Source algorithm outputs are immutable.
- ReviewAction append-only after save in GLP-ready modes.
- Locked ReviewRevision can only be changed through amendment/new revision.

## 8. Change Log

- 2026-06-29: Created baseline data/API/artifact contract.

- 2026-06-29: Incorporated partial Feishu AASM V3 PSG/HSAT source at schema level; added RuleGrade, PSG report parameter, arousal, respiratory, movement, cardiac, and HSAT contracts.

<!-- 20260629_PREVIEW_MIGRATION_BEGIN -->
## 2026-06-29 Data/API Contract Amendment: Reader State And Overlay Contracts

Status: accepted contract amendment for preview-migration gap.

### ReaderState

```json
{
  "reader_state_version": "qlanalyser-waveform-reader-v0.1",
  "file_id": "eeg_demo_epilepsy_high_amplitude",
  "window_start_sec": 0.0,
  "window_duration_sec": 30.0,
  "file_duration_sec": 60.0,
  "visible_channel_ids": ["Cz", "Pz", "Oz"],
  "channel_group_id": "default",
  "sensitivity_uv_per_row": 50.0,
  "display_mode": "raw | filter_preview | prepared",
  "decimation_mode": "raw | minmax | envelope",
  "request_seq": 1
}
```

### OverviewState

```json
{
  "loaded_windows": [{"start_sec": 0, "end_sec": 30}],
  "current_window": {"start_sec": 0, "end_sec": 30},
  "candidate_event_marks": [{"event_id": "evt_1", "start_sec": 5, "end_sec": 15}],
  "review_marks": [{"action_id": "act_1", "start_sec": 5, "end_sec": 15, "label": "rejected"}]
}
```

### EpilepsyOverlayState

```json
{
  "source_task_id": "task_epilepsy_entry_contract",
  "selected_event_id": "evt_1",
  "candidate_events": [],
  "stage_code_epochs": [],
  "review_actions": [],
  "overlay_visibility": {
    "candidate_events": true,
    "stage_code": true,
    "review_edits": true,
    "spectrogram_marker": true
  }
}
```

### API implications

Waveform browsing must use lightweight read APIs, not formal analysis task creation:

```http
GET /api/eeg/files/{file_id}/waveform/chunk
GET /api/eeg/files/{file_id}/spectrogram-window
```

Formal epilepsy screening remains a task:

```http
POST /api/tasks
```

Manual correction remains review layer:

```http
POST /api/tasks/{task_id}/epilepsy-review-sessions
PATCH /api/epilepsy-review-sessions/{session_id}
POST /api/epilepsy-review-sessions/{session_id}/exports
```

### Contract invariants

- `ReaderState.request_seq` or equivalent request key must prevent stale viewport overwrite.
- Waveform chunk payload must include enough metadata to prove it matches the current `ReaderState`.
- Review actions must reference source task, preparation plan, and reader/event target.
- Published artifacts must distinguish source algorithm outputs from reviewed outputs.


## 2026-06-29 Adversarial Review: Preview Migration Gap

Round 1 - Product truth:
Finding: The phrase "original waveform review window" implies professional browsing controls. Current implementation proves visibility, not full reviewing capability.
Decision: Accepted. P0 scope must require reader-control migration.

Round 2 - Information architecture:
Finding: Time window, scale, and progress can become repeated badges instead of one navigable timeline.
Decision: Accepted. One overview/timeline controller must own navigation.

Round 3 - Interaction state:
Finding: Algorithm overlays can accidentally become the main driver of viewport state.
Decision: Accepted. Source waveform reader owns viewport; algorithm output is overlay.

Round 4 - User workflow:
Finding: Epilepsy review needs previous/next candidate and center-on-event. Otherwise reviewers must manually hunt through the trace.
Decision: Accepted. Candidate navigation is P0b.

Round 5 - Release risk:
Finding: Teaching chain passes, but release wording could overclaim if reader migration is not complete.
Decision: Accepted. Release plan now separates P0a internal candidate from P0b release-candidate reader migration.
<!-- 20260629_PREVIEW_MIGRATION_END -->

<!-- 20260629_P0B_READER_IMPLEMENTATION_ACCEPTANCE_BEGIN -->
## 2026-06-29 P0b Reader Implementation Acceptance

Data/API contract accepted:
- Inline epilepsy reader uses `GET /api/eeg/files/{file_id}/waveform/chunk` with `start_sec`, `duration_sec`, `channel_limit`, `display_sfreq`, `mode=minmax`, and `width_px`.
- The returned waveform chunk remains preview-only and does not register analysis artifacts.
- Manual correction remains separate review-session state and export artifacts; browsing, panning, zooming, and overlay toggles do not write review commands.
- Task and review payloads continue to carry `data_preparation_plan_id`, `data_preparation_revision`, and `data_preparation_contract_version`.

Evidence:
- Main E2E captured epilepsy task payload and review session create/patch/export payloads with the data-preparation contract fields intact.
<!-- 20260629_P0B_READER_IMPLEMENTATION_ACCEPTANCE_END -->

## 2026-06-30 P0 Addendum: `epilepsy_ml_spectrogram` Artifact

Producer:
- `module_name=epilepsy_ml`
- `workflow_id=epilepsy_ml_xgboost`
- label: `epilepsy_ml_spectrogram`
- path: `data/epilepsy_ml_spectrogram.json`

Schema:
```json
{
  "schema_version": "qlanalyser-epilepsy-ml-spectrogram-v0.1",
  "source_compatibility": "AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis2.py::calculate_spectrogram",
  "method": "scipy.signal.stft",
  "channel": "EEG3",
  "sfreq": 250.0,
  "duration_sec": 60.0,
  "parameters": {
    "window_sec": 4.0,
    "overlap_ratio": 0.9,
    "boundary": "zeros",
    "freq_min_hz": 0.5,
    "freq_max_hz": 50.0,
    "power_transform": "10*log10(abs(Zxx)+1e-10)",
    "vmin_percentile": 10,
    "vmax_percentile": 99
  },
  "frequencies_hz": [],
  "times_sec": [],
  "power_db": [],
  "vmin": -20.0,
  "vmax": 10.0
}
```

Contract rules:
- `power_db.length == frequencies_hz.length`.
- Each `power_db[row].length == times_sec.length`.
- The artifact is review evidence. Formal TFR/PSD/Band Power outputs keep their own contracts.

## 2026-06-30 P0 Addendum: Epilepsy ML Result Image Artifacts

The epilepsy ML workflow must publish customer-visible image artifacts:

```text
module_name=epilepsy_ml
workflow_id=epilepsy_ml_xgboost
```

Required artifact labels:

| Label | Path | MIME | Scope |
| --- | --- | --- | --- |
| `epilepsy_ml_event_timeline_figure` | `figures/epilepsy_ml_event_timeline.svg` | `image/svg+xml` | candidate-event visual evidence |
| `epilepsy_ml_spectrogram_figure` | `figures/epilepsy_ml_spectrogram_preview.svg` | `image/svg+xml` | source-compatible STFT visual evidence |

Summary contract:

```json
{
  "figures": {
    "event_timeline": "figures/epilepsy_ml_event_timeline.svg",
    "spectrogram_preview": "figures/epilepsy_ml_spectrogram_preview.svg",
    "scope": "result_review_visual_evidence_only"
  }
}
```

Rules:
- The SVGs must contain a visible non-medical research boundary.
- The Results page may display these images directly.
- These images do not supersede source tables, spectrogram JSON, model manifest, reproducibility files, or review revision exports.
