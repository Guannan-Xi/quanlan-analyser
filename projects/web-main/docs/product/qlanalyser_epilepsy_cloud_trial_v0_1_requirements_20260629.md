# QLanalyser Epilepsy-like Event Screening Cloud Trial v0.1 - Requirements

Status: document synced 2026-07-01; cloud synthetic EDF customer-trial RC evidence accepted; formal external release still blocked by owner-approved anonymous real EEG regression.

## Scope

This document defines the functional and product requirements for the v0.1 cloud trial. It is governed by the terminology contract: epilepsy uses "screening / candidate event / manual review / event correction / export"; sleep alone uses "staging / 分期".

## R1 User and Access

R1.1 Internal users and controlled friendly customers can access the cloud trial environment.

R1.2 Friendly customers receive independent trial accounts. Internal users may use internal test accounts.

R1.3 Permissions must distinguish at least view, upload, review, and export.

R1.4 Trial users must confirm upload authorization: the uploaded EEG may be used for research analysis in this trial.

R1.5 Trial data is not used for model training by default. Training use requires explicit future authorization. v0.1 does not perform training.

## R2 Upload and File Intake

R2.1 The user can upload EEG data from the cloud UI.

R2.2 EDF is the P0 acceptance format. Other compatible formats may remain available, but P0 release gates only require EDF.

R2.3 The first release does not promise a fixed maximum file size. The actual cloud-tested limit, timing, and failure boundary must be recorded.

R2.4 After upload, the UI must show file name, size, upload state, duration, sampling rate, channel count, channel names, detected format, and reading warnings.

R2.5 Upload failure must show a reason, an error id, suggested next action, and support contact entry.

R2.6 Multiple files can be uploaded to a project, but v0.1 analyzes one file at a time.

R2.7 User deletion is allowed only with confirmation, permission checks, and operation log. Deletion must not be a silent one-click destructive action.

## R3 Data Preparation

R3.1 Ordinary uploaded data cannot start epilepsy-like event screening until a data preparation plan is confirmed.

R3.2 Data Preparation must show basic waveform, file metadata, channel list, preparation controls, and a confirm action.

R3.3 The target design includes complete preprocessing parameter management. P0 acceptance may focus on the confirmed plan contract and visible base waveform, but the UI must not block future full parameter expansion.

R3.4 Confirmed analysis payloads must carry:

- `data_preparation_plan_id`
- `data_preparation_revision`
- `data_preparation_contract_version`

## R4 Analysis Entry

R4.1 The Analysis page includes an Epilepsy-like Event Screening workbench entry after data preparation.

R4.2 The entry must not use "癫痫分期", "初筛/分期", or "开始分期".

R4.3 The child workbench must remain inside the main navigation frame. It must not behave as a standalone disconnected mini-app for customer use.

## R5 Workbench First View

R5.1 When entering the workbench, the first view shows raw/base waveform, current file, data preparation state, and the Start Screening button.

R5.2 The waveform must be visible before screening starts. For large data, a clear loading state is acceptable.

R5.3 The page must not show irrelevant empty-state content such as "current data has no video". Video panels are only visible when a real synchronized video exists.

R5.4 Unavailable buttons must be disabled with a visible reason, hidden, or marked future. No clickable no-op controls are allowed.

R5.5 Duplicate status, progress, or time-axis information must be merged unless each layer has a clearly different user purpose.

## R6 Screening Execution

R6.1 The run button label is `开始初筛`.

R6.2 Default workflow is ML/XGBoost source-compatible epilepsy-like event screening. STD is a baseline/comparison method, mainly for internal or advanced comparison use.

R6.3 Screening must call the real backend workflow and create traceable task/artifact outputs.

R6.4 Running state must show progress and current step. The synthetic 60 s fixture should finish within 30 s; the v0.1 cloud target for ordinary trial files is within 2 minutes when feasible. If longer, the state must remain understandable.

R6.5 If the user leaves and returns, the task state can be restored and final success/failure results can be opened.

## R7 Result Evidence

R7.1 Screening completion must show a summary: event count, total candidate duration, epoch count, channel, algorithm version, data preparation version, and result state.

R7.2 Stage_Code is an epoch-level discrete label, not sleep staging:

- `0 = Normal`
- `1 = epilepsy-like candidate`

R7.3 Candidate event detection follows source-compatible logic in v0.1: consecutive seizure-like epochs with length >= 2 are merged into candidate events. This may become configurable later.

R7.4 The workbench must show:

- waveform evidence
- candidate event overlay
- Stage_Code strip
- candidate event table
- synchronized spectrogram

R7.5 Clicking a candidate event synchronizes waveform, Stage_Code, spectrogram, and candidate table selection. Target response is 100 ms for UI sync when data is available.

R7.6 Spectrogram must be based on the same selected data/time window as the waveform/candidate event. It is not a decorative static image.

## R8 Manual Review and Event Correction

R8.1 Default mode is browse/read-only. Edits require `进入人工复核`.

R8.2 Manual review can change a single epoch or a continuous epoch range.

R8.3 Allowed manual labels:

- epilepsy-like candidate
- Normal
- needs review
- artifact

R8.4 Candidate events are recalculated from the reviewed epoch labels.

R8.5 Undo and Redo are required.

R8.6 Manual review never overwrites the source algorithm result. It saves a review revision.

R8.7 Review records include previous label, new label, editor, timestamp, reason/note, data preparation version, and algorithm version.

## R9 Results and Export

R9.1 The workbench is for review; formal deliverables appear in Results.

R9.2 Results must show task state, file, project, algorithm version, data preparation version, event count, review state, review revision, and export entry.

R9.2a Local demo or localhost browser evidence may support implementation acceptance, but it must not be used to claim cloud trial RC readiness.

R9.2b Cloud RC must prove Results readback and export from the same non-local browser session that created the review revision.

R9.3 v0.1 exports CSV and JSON. PDF/HTML report is P1.

R9.4 CSV package includes:

- `epoch_predictions.csv`
- `candidate_events.csv`
- `manual_corrections.csv`
- `final_review_events.csv`

R9.5 JSON package includes:

- `summary.json`
- `parameters.json`
- `model_manifest.json`
- `review_revision.json`
- `scope_contract.json`

R9.6 Export package includes the non-medical boundary.

## R10 Cloud Acceptance

R10.1 v0.1 acceptance runs in cloud staging/trial, not only local dev.

R10.2 E2E must start from EDF upload. Server-existing-file path may be tested additionally but cannot replace upload acceptance.

R10.3 The synthetic labeled EDF fixture is mandatory:

- `regular_epilepsy_labeled_60s.edf`
- expected `Stage_Code = 000001100000`
- expected candidate event `25.0-35.0 s`

R10.4 Authorized anonymous real data regression is not required for internal trial, but is required before external formal release.

## P0 Blockers

Any of these blocks v0.1 cloud trial:

- upload fails
- data preparation cannot be confirmed
- Start Screening has no feedback
- backend screening cannot complete on the labeled EDF
- result evidence is not visible
- manual review cannot save
- export is missing or incorrect
- medical/diagnostic wording appears in customer-facing output

## Sources Used

- Owner choice rounds in the current Codex thread, 2026-06-29.
- `docs/product/epilepsy_sleep_terminology_contract_20260629.md`
- `docs/product/epilepsy_regular_labeled_fixture_20260629.md`

## Change Log

- 2026-06-29: Created v0.1 requirements baseline.
- 2026-06-30: Synced completed local evidence, promoted closed local gates, and kept cloud/trial/browser gaps blocking.
- 2026-06-30: Synced local browser upload-to-export interaction pass and cloud release-gate blocker.

## 2026-06-30 Requirement Sync

Requirements now treated as locally evidenced:

- R1.4 upload authorization: local API acceptance passed; see `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_upload_contract_receipt_20260629.md`.
- R3.1/R3.4 data-preparation gate and lineage: local API acceptance passed; upload-to-export E2E preserved `data_preparation_plan_id`, `data_preparation_revision`, and `data_preparation_contract_version=qlanalyser-data-preparation-v0.2`.
- R5/R6 epilepsy ML task path: local API E2E passed through `module_name=epilepsy_ml` and `workflow_id=epilepsy_ml_xgboost`.
- R7 synthetic fixture truth: local API E2E passed with `Stage_Code=000001100000` and candidate event `25.0-35.0s`.
- R9 v0.1 CSV/JSON package naming: local API export contract passed.
- Ordinary local browser upload-to-export path: passed 29/29 from EDF upload authorization through data preparation, screening, Stage_Code/candidate-event truth, manual correction, export, Results visibility, interaction checks, and customer-facing copy guards.
- Inline workbench local interaction contract: passed for main-shell child page, waveform-first layout, parent navigation, no duplicate time-scale controls, wheel browsing without global toast, same-window STFT source, and real `Stage_Code` canvas overlay.

Historical requirements that blocked cloud trial RC before 2026-07-01:

- Cloud/staging URL plus trial account E2E. Current status: closed for synthetic EDF RC by 2026-07-01 cloud browser E2E.
- Non-local browser UI upload from the deployed trial app through export/Results. Current status: closed for synthetic EDF RC by 2026-07-01 cloud browser E2E.
- Failure states and customer-facing error copy for failed task, artifact load failure, and export failure. Current status: covered by scoped v0.1 gates/E2E for RC; broader product sweep remains future hardening.
- Full copy governance scan: no mojibake, no diagnostic/clinical claims, and no epilepsy "staging" wording. Current status: scoped v0.1 passed; obsolete/full-product sweep remains future hardening.
- Cloud performance boundary for upload, metadata extraction, screening, artifact load, review save, and export. Current status: still pending for large EDF / 1GB-class files; not claimed by v0.1 synthetic RC.
- Owner/steward approved anonymous real data regression before external formal release. Current status: still blocking formal external release.

Terminology guard: epilepsy remains "screening / candidate event / manual review / event correction / export". Sleep may use staging; epilepsy must not be called staging or 分期.

## 2026-06-29 Requirement Status Update

The following requirements are now implemented and locally verified:

- Upload authorization is mandatory for ordinary `/api/eeg/upload`.
- Ordinary uploaded data cannot run formal epilepsy-like event screening without a confirmed data preparation plan.
- Formal analysis validates preparation plan status, file lineage, and project lineage.
- `epilepsy_ml` is constrained to the v0.1 workflow id `epilepsy_ml_xgboost`.
- The synthetic labeled EDF fixture produces Stage_Code `000001100000` and candidate event `25.0-35.0s` in the API upload-to-export path.
- Review export includes the v0.1 CSV/JSON package.
- The main analysis page can open the inline epilepsy-like event workbench in the local teaching/demo browser path.

## 2026-07-01 Cloud Trial RC Sync

Current requirement status:

- Cloud synthetic EDF customer-trial RC: accepted for trial acceptance.
- Formal external release: blocked until owner/data steward supplies authorized anonymous real EEG `input_manifest.json` and real-data regression passes.
- Large-file performance and broader 1-64 channel regression: not claimed by v0.1; must be planned before wider customer rollout.

Accepted cloud RC evidence:

```text
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-release-gate/release_gate_result.json
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_release_gate_receipt_20260701.md
```

Evidence readback:

```text
cloud browser E2E status = passed
checks = 34 / 34 passed
frontend = http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=e2e-rc-final-clean-20260701f#storage
task = epilepsy_ml / epilepsy_ml_xgboost
Stage_Code = 000001100000
candidate event = 25.0-35.0s
report package includes event timeline and spectrogram figures
```

The following items remain outside the accepted cloud synthetic RC and must not be implied as complete:

- Real owner/steward anonymous EEG regression for formal external release.
- Explicit large EDF / 1GB-class performance envelope.
- Full GLP validation package, e-signature, and regulated audit controls.
- Sleep staging, respiratory event scoring, and video analysis runtime.

## Traceability / Acceptance Mapping

| Requirement area | Accepted cloud RC evidence | Formal release status |
| --- | --- | --- |
| EDF upload with authorization | Cloud browser upload-to-export E2E passed 34/34. | Accepted for synthetic RC; real owner-data regression still pending. |
| Data preparation lineage | Cloud task readback includes `data_preparation_plan_id`, revision, and contract version. | Accepted for synthetic RC. |
| Embedded epilepsy-like event workbench | Deep link and upload flow reach the main-navigation child workbench. | Accepted for synthetic RC. |
| Screening terminology | Copy contract uses event screening, candidate events, manual review, correction, and export; not epilepsy staging. | Accepted for synthetic RC; must remain enforced in future copy sweeps. |
| Stage_Code and candidate event evidence | Cloud fixture readback confirms Stage_Code `000001100000` and candidate event `25.0-35.0s`. | Accepted for synthetic RC only. |
| Results and report package | Cloud report package includes event timeline and spectrogram figures. | Accepted for synthetic RC. |
| Formal external release evidence | Not applicable to synthetic RC. | Blocked until owner manifest validation and real anonymized EEG regression pass. |
