# QLanalyser Epilepsy-like Event Screening Cloud Trial v0.1 - Architecture

Status: document synced 2026-07-01; cloud synthetic EDF customer-trial RC architecture evidence accepted; formal external release still blocked by owner-approved anonymous real EEG regression.

## Architecture Goal

Provide a cloud trial workflow that connects project/data upload, data preparation, backend screening task execution, embedded workbench review, Results registration, and export without local developer steps.

## Main Flow

```text
Cloud UI
-> Auth / trial account
-> Project
-> EEG upload
-> EEG file metadata extraction
-> Data Preparation plan
-> Analysis task
-> Epilepsy-like Event Screening workbench
-> Backend epilepsy_ml / STD workflow
-> Artifacts
-> Manual review session / revision
-> Results
-> CSV/JSON export
```

## Boundary Rules

1. UI cannot bypass the backend task/artifact contract to mutate algorithm outputs.
2. Data Preparation is upstream of analysis. Analysis payloads inherit the confirmed plan/revision/contract.
3. Algorithm source outputs are immutable.
4. Manual review writes review revision data.
5. Results consumes algorithm artifacts plus published review revisions.
6. Sleep staging and video analysis are future interfaces, not v0.1 P0 runtime requirements.

## Frontend Surfaces

### Project / Upload

Responsibilities:

- create/open project
- upload EEG/EDF
- show file metadata and read warnings
- show upload failure with error id, suggestion, and support route

### Data Preparation

Responsibilities:

- waveform-first preview
- channel metadata
- preparation controls
- confirm preparation plan
- prevent ordinary analysis until confirmed

### Analysis Page

Responsibilities:

- show Epilepsy-like Event Screening entry
- enforce preparation gate
- route to embedded child workbench with file/task/preparation context

### Epilepsy-like Event Screening Workbench

Responsibilities:

- show waveform before screening
- run screening
- poll/restore task state
- render artifacts
- synchronize candidate event table, waveform, Stage_Code, and spectrogram
- support manual review and review revision save

### Results

Responsibilities:

- show task result and review revision
- expose export package
- keep non-medical boundary visible

## Backend Services

### Upload / Storage

- Persist uploaded file.
- Extract metadata: duration, sampling rate, channel count, channel names, detected format, warnings.
- Store user authorization confirmation and operation log.

### Data Preparation Service

- Create confirmed plan and revision.
- Return preparation contract fields required by analysis.

### Task Service

- Create `epilepsy_ml` or `epilepsy` task.
- Persist task state for restore after navigation.
- Register artifacts.

### Epilepsy ML Runner

Default workflow:

- `module_name = epilepsy_ml`
- `workflow_id = epilepsy_ml_xgboost`
- source-compatible XGBoost feature/model path
- fixed probability threshold 0.5
- epoch length 5 s or 3 s by supported model
- candidate event grouping with >= 2 consecutive seizure-like epochs

### Review Session Service

- Store manual review state and actions.
- Preserve source algorithm outputs.
- Publish review revision artifacts.

### Export Service

- Bundle CSV/JSON outputs.
- Include scope contract and non-medical boundary.

## Data Contracts

The core artifact families are:

- EEG file metadata
- data preparation plan
- task summary
- epoch predictions / Stage_Code
- candidate events
- spectrogram data
- manual corrections
- review revision
- export manifest
- scope contract

## Performance Architecture

P0 cloud trial target:

- first waveform visible within 5 s for tested files, with loading state for slower files
- synthetic 60 s EDF screening within 30 s
- ordinary trial task target within 2 minutes where feasible
- candidate event selection sync target 100 ms when required data is cached/available

Future performance work:

- chunk API for long EDF
- min-max/envelope waveform decimation
- spectrogram tile/cache
- cancellation and prefetch

Cloud trial boundary:

- local localhost/demo E2E is evidence only, not cloud RC proof
- cloud/staging evidence must come from a non-local trial URL with real browser upload, screening, review, Results, and export
- no Results claim is accepted unless the cloud environment can open the v0.1 export package
- do not treat ordinary local browser evidence or screenshots as proof of cloud RC readiness

## Security and Trial Governance

- Trial account required.
- Upload authorization checkbox required.
- Basic logs for upload, analysis, review, export.
- User deletion allowed only with confirmation, permission check, and log.
- Trial data is not used for training unless explicitly authorized in a future workflow.

## Sources Used

- Owner choice rounds, 2026-06-29.
- Existing epilepsy ML runner and workbench direction.
- QLanalyser-PC source-compatible behavior captured in existing docs.

## Change Log

- 2026-06-29: Created v0.1 cloud trial architecture baseline.
- 2026-06-30: Synced local acceptance receipts and separated proven local architecture from cloud/browser RC blockers.
- 2026-06-30: Synced ordinary local browser upload-to-export pass and explicit cloud release gate.

## 2026-06-30 Architecture Sync

Locally accepted architecture links:

- Upload service now has local evidence for authorization readback and metadata propagation: `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-contract/upload_authorization_contract.json`.
- Data Preparation remains the upstream gate; local API E2E proved strict lineage into the analysis payload and review/export package.
- `epilepsy_ml / epilepsy_ml_xgboost` is the accepted P0 ML path for the synthetic ordinary EDF fixture.
- Export service locally supports the v0.1 CSV/JSON package shape and non-medical boundary.
- Main navigation can open the inline epilepsy-like event workbench in the ordinary local browser upload-to-export path.
- The inline workbench is proven locally as a main-shell child page with waveform-first layout, parent navigation mapping, Stage_Code canvas overlay, same-window STFT evidence, and Results export visibility.

Architecture status after 2026-07-01 cloud RC rerun:

- Cloud synthetic EDF runtime target and ordinary browser upload-to-export path are verified for the v0.1 RC evidence packet.
- Cloud Results module opened the v0.1 review/export package in browser acceptance.
- Failure-state, copy-governance, and mojibake checks are covered by scoped v0.1 evidence and the upload-to-export browser E2E.
- Cloud performance boundaries for large EDF / 1GB-class files remain unmeasured and are not claimed by v0.1.
- Owner/steward approved anonymous real data regression is pending for formal external release.

Boundary retained: QLanalyser v0.1 is non-medical research-support screening. Algorithm outputs remain immutable; manual review writes a review revision; Results consumes algorithm artifacts plus the review revision.

## 2026-06-29 Architecture Status Update

Current implemented local architecture:

```text
Upload with authorization
-> EEG file metadata
-> Confirmed data preparation plan
-> Main analysis page inline epilepsy-like event workbench
-> epilepsy_ml_xgboost task
-> Stage_Code / candidate event artifacts
-> Review session and manual correction revision
-> v0.1 CSV/JSON export package
```

Architecture boundaries reaffirmed:

- Data Preparation remains upstream of formal analysis for ordinary uploaded data.
- The epilepsy-like event workbench is a child surface inside the main navigation shell, not a detached mini-app.
- Source algorithm outputs are read-only; manual corrections write review actions/revisions.
- Results must consume published review/export artifacts rather than recomputing or bypassing the workbench contract.
- Sleep staging and video synchronization remain future extension points and are not v0.1 P0.

## 2026-07-01 Cloud Architecture Acceptance Sync

Accepted deployed architecture path:

```text
Cloud UI at http://39.97.248.225
-> ordinary EDF upload with authorization
-> confirmed data preparation plan
-> main navigation child workbench
-> epilepsy_ml_xgboost task
-> current-task-scoped artifact loading
-> waveform / Stage_Code / candidate event / STFT spectrogram evidence
-> manual review session
-> review-layer export artifacts
-> Results image/table/report package readback
```

Evidence:

```text
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-release-gate/release_gate_result.json
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_release_gate_receipt_20260701.md
```

Architecture fix accepted on 2026-07-01:

- Inline epilepsy result loading now scopes artifacts to the current `task_<id>` directory.
- Data-preparation artifacts are excluded from epilepsy result binding.
- Review export refreshes Results and E2E state after artifact registration.

Residual architecture risks:

- Formal external release still needs owner-approved anonymous real EEG regression.
- Large EDF and 1-64 channel performance envelopes are not proven by the 60 s synthetic EDF RC.
- GLP-ready controls remain later-phase architecture and must not be claimed in v0.1.

## Traceability / Acceptance Mapping

| Architecture boundary | Current implementation/evidence | Release interpretation |
| --- | --- | --- |
| Cloud UI and upload service | Non-local cloud browser E2E starts from EDF upload. | Accepted for synthetic RC. |
| Data Preparation upstream gate | Confirmed plan lineage is preserved into the epilepsy task payload/readback. | Accepted for synthetic RC. |
| Task service and epilepsy ML runner | `epilepsy_ml / epilepsy_ml_xgboost` completes on the labeled synthetic EDF. | Accepted for synthetic RC only. |
| Current-task artifact adapter | Frontend binds epoch, event, and spectrogram artifacts from the current `task_<id>` output and excludes data-preparation artifacts. | Accepted architecture fix. |
| Review/export facade | Manual correction writes review-layer artifacts and refreshes Results readback. | Accepted for synthetic RC. |
| Formal release data boundary | Owner-approved anonymous real EEG manifest is missing. | Blocks formal external release. |
