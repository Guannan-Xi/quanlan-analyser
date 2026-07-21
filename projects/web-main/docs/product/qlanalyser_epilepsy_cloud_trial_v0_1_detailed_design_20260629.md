# QLanalyser Epilepsy-like Event Screening Cloud Trial v0.1 - Detailed Design

Status: document synced 2026-07-01; cloud synthetic EDF browser upload-to-export UX accepted for customer-trial RC; formal external release still blocked by owner-approved anonymous real EEG regression.

## Design Principles

1. Waveform first: the user enters the workbench and sees the signal before algorithm results.
2. One next step: every state presents the next useful action, not a wall of controls.
3. No fake controls: disabled controls show the reason; future features are hidden or marked future.
4. No duplicate status: progress, time range, and task state appear once at the correct hierarchy.
5. Professional EEG interaction: waveform wheel/keyboard follows EDFBrowser-like reading habits and does not trigger global toast popups.
6. Epilepsy terminology: screening and candidate events, not staging.
7. Source output immutable: manual correction is a review revision.

## Page States

### S0 No Project / No File

- show an empty but not broken customer-trial entry state
- no fake results or placeholder analysis artifacts
- use explicit upload and trial-start affordances, not a hidden developer-only shortcut

Visible:

- create/open project entry
- upload prompt
- optional example data entry
- non-medical boundary

Not visible:

- video placeholder
- inactive analysis controls

### S1 Uploaded File

Visible:

- file name, size, status
- duration, sampling rate, channel count, channel list
- detected format and warnings
- base waveform loading/ready state
- data preparation entry

### S2 Preparation Required

Visible:

- waveform preview
- preparation controls
- confirm preparation plan
- explanation that analysis is gated until preparation is confirmed

### S3 Preparation Confirmed

Visible:

- Epilepsy-like Event Screening entry
- preparation plan id, revision, contract version
- selectable analysis channel with recommended EEG channel

### S4 Workbench Ready / Not Screened

Visible:

- project/file/preparation state
- raw/base waveform
- `开始初筛`
- algorithm selector: ML default, STD baseline/advanced
- compact parameter panel

Disabled:

- manual review controls
- export controls

### S5 Screening Running

- show progress and task state only
- do not convert algorithm evidence into diagnostic language
- do not allow stale overlays to overwrite the latest reader state
- keep the waveform visible; do not replace it with a loading-only page

Visible:

- progress bar
- current step
- task id
- cancel/retry policy if available

Expected steps:

- reading EEG
- selecting channel
- extracting features
- running model/baseline
- merging candidate events
- registering artifacts

### S6 Screening Completed

Visible:

- summary cards
- waveform with event overlay
- Stage_Code strip
- candidate event table
- synchronized spectrogram
- `进入人工复核`
- export not final until review revision is saved or user chooses algorithm-only export if allowed by release policy

### S7 Manual Review

- review revision writes are explicit and separate from source algorithm outputs
- action buttons remain disabled until a candidate/event target is selected

Visible:

- correction mode indicator
- selected epoch/range
- label actions: epilepsy-like candidate, Normal, needs review, artifact
- Undo / Redo
- reason/note field
- `保存复核版本`

Rules:

- browse mode cannot write
- correction updates review draft only
- source algorithm output remains visible or recoverable
- candidate events recalculate from reviewed labels

### S8 Saved Review Revision

Visible:

- saved revision id
- review state
- Results route
- export controls

### S9 Failure

Visible:

- failure reason
- error id
- suggested action
- support entry
- retry if safe

## Workbench Layout

Recommended desktop hierarchy:

```text
Header: project / file / preparation / task state
Toolbar: Start Screening or review mode actions
Main: waveform reader
Evidence: Stage_Code strip + spectrogram
Right rail: candidate events + selected event details + review controls
Footer/status: current time window, channel, scale, task state
```

No separate video panel appears unless the uploaded data has real synchronized video.

## Controls

### Primary Buttons

- `开始初筛`
- `查看候选事件`
- `进入人工复核`
- `保存复核版本`
- `导出结果`

### Disabled Reasons

Examples:

- "请先确认数据准备方案"
- "请先运行癫痫样事件初筛"
- "请选择候选事件或 epoch"
- "浏览模式下不可修改，请进入人工复核"

## Waveform Interaction

Inside waveform region:

- wheel pans horizontally
- Ctrl/Cmd + wheel zooms anchored to pointer
- arrow keys move the window
- PageUp/PageDown page the window
- middle drag pans if supported
- no global toast on normal navigation

Outside waveform region:

- normal page scrolling works

## Spectrogram Design

The spectrogram must represent the same data/time range as the active event/window.

Source-aligned method:

- `scipy.signal.spectrogram`
- `nperseg = winsize * sampling_rate`
- `noverlap = nperseg * 3/4`
- power display in `10 * log10(Sxx)`
- frequency range filter supported
- display range based on percentiles, e.g. 10th to 99th percentile

## Manual Review Data Model

Each review action:

- action id
- task id
- file id
- epoch range
- previous label
- new label
- reason/note
- editor
- timestamp
- data preparation plan/revision/contract
- algorithm module/workflow/model version

Undo/Redo uses the action history. Saving produces a review revision.

## Results Display

Results page card includes:

- project
- file
- task status
- algorithm version
- data preparation version
- candidate event count
- review revision
- export entry

## Mobile

Mobile is not a P0 professional reading target. It may show status and summary, but desktop is the P0 review environment.

## Sources Used

- Owner choice rounds, 2026-06-29.
- Terminology contract.
- PC source-aligned spectrogram and epilepsy event behavior captured in previous docs.

## Change Log

- 2026-06-29: Created v0.1 detailed design baseline.
- 2026-06-30: Synced local interaction fixes for main-shell child page, Stage_Code overlay, time-scale control deduplication, and same-window STFT evidence.

## 2026-06-29 Detailed Design Status Update

Local design decisions now confirmed by implementation/evidence:

- Use `Start screening`, `Candidate events`, `Manual correction`, `Save review version`, and `Export results` wording. Do not use epilepsy staging wording.
- Start screening must create exactly one `epilepsy_ml` task with workflow `epilepsy_ml_xgboost`.
- The workbench first meaningful view must be waveform-centered; algorithm output appears as synchronized overlays/evidence, not as the only content.
- Stage_Code is shown as an algorithm-derived event-screening sequence for the synthetic fixture, not as a sleep-stage label.
- Spectrogram is synchronized evidence for the selected file/channel/window and must not be presented as unrelated demonstration data.
- Manual correction changes review state/revision only; it does not modify source epoch predictions.
- No real synchronized video means no fake video panel or placeholder image in v0.1.

Design work still required:

- Browser upload-to-export interaction details and selectors.
- Results package card/detail layout for the v0.1 export contract.
- Failure-state copy and button disabled reasons.
- UTF-8/copy governance pass on DOM text and captured evidence.

## 2026-06-30 Detailed Design Sync

Accepted local UX/design evidence:

- Main inline epilepsy-like event workbench opened inside the QLanalyser navigation shell in local browser E2E.
- Local demo/browser evidence showed Stage_Code `000001100000`, candidate event `25.0-35.0s`, waveform, Stage_Code strip, and spectrogram panels.
- API receipts proved the upload authorization gate, data-preparation lineage, `epilepsy_ml_xgboost` run, and v0.1 export package shape.

Detailed-design acceptance after 2026-07-01 cloud RC rerun:

- Cloud/staging browser upload flow starts from EDF upload and ends at export/Results on a non-local target.
- Failure-state, copy-governance, mojibake, no-staging-copy, and wheel/no-toast checks are covered by scoped v0.1 E2E/gate evidence.
- Stage_Code, candidate events, waveform, same-window STFT spectrogram, manual correction, Results image previews, and report package are accepted for the synthetic 60 s EDF trial path.
- Cloud performance for large EDF / 1GB-class files and owner/steward anonymous-data regression remain pending and are outside the accepted v0.1 synthetic RC.

Terminology guard: copy may say "癫痫样事件初筛", "候选事件", "人工复核", and "事件校正"; it must not call epilepsy "分期".

## 2026-06-30 Interaction Design Sync

Accepted local design behavior:

- The workbench is a child page inside the main QLanalyser navigation shell.
- Its sidebar parent is `分析任务`; its page title is `癫痫样事件分析台`.
- The first workbench content is the raw waveform reader, before the screening action panel.
- The waveform reader owns the time-scale controls (`5s / 30s / 300s`).
- The STFT panel does not duplicate those controls; it displays a readout that follows the current waveform window.
- Mouse-wheel browsing in the inline waveform reader pans horizontally and does not raise a global toast.
- `Stage_Code` overlay is a real canvas overlay toggle, not a disabled/no-op control.
- STFT preview is derived from the current waveform chunk and remains explicitly labeled as synchronized evidence, not as formal TFR/PSD/Band Power output.
- Manual correction remains review-layer-only and preserves source ML artifacts as readonly.

Evidence:

- `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/browser_upload_to_export.json`
- `work/release_evidence/20260629-epilepsy-child-page-p0/static_epilepsy_child_page_contract.json`

## 2026-07-01 Detailed Design Sync: Cloud Result Loading

The inline workbench result-loading design is now:

```text
completed epilepsy_ml_xgboost task
-> fetch task artifacts
-> filter artifacts to current task_<id>
-> exclude data_preparation artifacts
-> bind epoch predictions, events, and spectrogram JSON
-> render Stage_Code, candidate list, waveform overlay, spectrogram, and review controls
```

Design rationale:

- A task artifact list may include upstream data-preparation artifacts as well as current analysis outputs.
- The UI must never infer epilepsy results from a data-preparation artifact merely because a path or label contains a similar word.
- Current-task artifact scoping is therefore part of the UI data contract, not a test-only workaround.

Accepted evidence:

```text
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-release-gate/release_gate_result.json
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_release_gate_receipt_20260701.md
```

Cloud E2E confirms:

- 34 / 34 checks passed.
- The workbench uses `epilepsy_ml_xgboost`.
- The loaded Stage_Code truth is `000001100000`.
- The candidate event is `25.0-35.0s`.
- The STFT spectrogram source is the current epilepsy ML spectrogram artifact.
- Results shows review package and result images.
- Report package includes event timeline and spectrogram figures.

## Traceability / Acceptance Mapping

| Design element | Current accepted evidence | Remaining design guard |
| --- | --- | --- |
| Waveform-first first view | Cloud upload-to-export E2E reaches the inline workbench and renders the waveform-first state. | Keep algorithm output as overlay/evidence, not the only first-screen content. |
| Start screening feedback | Progress reaches completed state in browser E2E. | Larger files need explicit latency and timeout copy in later trials. |
| Same-window STFT evidence | Spectrogram source is the current epilepsy ML spectrogram artifact. | Do not present it as formal PSD/TFR/Band Power unless contracted. |
| Stage_Code strip and candidate list | Fixture readback confirms Stage_Code `000001100000` and event `25.0-35.0s`. | Do not call epilepsy output staging. |
| Manual correction | Review save/export succeeds and source ML artifacts remain read-only. | Future audit trail must preserve reviewer identity and revision history. |
| Results visuals | Report package includes event timeline and spectrogram figures. | Formal release still needs real-data regression and broader visual QA. |
