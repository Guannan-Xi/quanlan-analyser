# QLanalyser Epilepsy/Sleep Waveform Staging Child Pages Architecture

Date: 2026-06-28  
Status: architecture draft for owner review  
Scope: epilepsy-like event analysis workbench and sleep staging workbench as main-system child pages  
Non-goals: standalone review-only pages, independent primary upload flow, TimeChart integration, router/Headroom/gateway/IPC/model-route changes

## 1. Owner Intent Correction

The owner corrected the product meaning:

- Epilepsy and sleep workbenches are not merely result review pages.
- They are interactive waveform staging and manual correction workbenches.
- They must live as child pages inside the QLanalyser main system.
- They inherit the data selected and confirmed in Data Preparation.
- They publish final staged/corrected outputs back into the main Results module and report/export pipeline.

Correct product chain:

```text
Project/Data
-> Data Preparation
-> Analysis Tasks
-> Epilepsy/Sleep waveform staging child page
-> manual staging/correction save
-> Results
-> Report Delivery
```

## 2. Knowledge Sources Read

Local/project knowledge used:

- `D:/QuanLanKnowledgeBase/manifests/design/GOOGLE_LABS_DESIGN_MD_CONTRACT_TOOL_20260627.md`
- `D:/QuanLanKnowledgeBase/learning-notes/design/UX_DESIGN_CRITIQUE_WORKFLOW_RUBRIC_CN.md`
- `D:/QuanLanKnowledgeBase/learning-notes/design/B2B_SCIENTIFIC_DASHBOARD_SCREENSHOT_AUDIT_CHECKLIST_CN.md`
- `D:/QuanLanKnowledgeBase/learning-notes/design/UX_STATE_FEEDBACK_EMPTY_ERROR_LOADING_MOTION_GATE_CN.md`
- `D:/QuanLanKnowledgeBase/learning-notes/design/DESIGN_TOKENS_VISUAL_REGRESSION_GATE_CN.md`
- `D:/QuanLanKnowledgeBase/learning-notes/qlanalyser/QLANALYSER_ONBOARDING_CRITICAL_TASK_RESULT_INTERPRETATION_GATE_CN.md`
- `D:/QuanLanKnowledgeBase/learning-notes/qlanalyser/HUMAN_FACTORS_FORMATIVE_SUMMATIVE_EVIDENCE_PACK_STANDARD_CN.md`
- `D:/QuanLanKnowledgeBase/learning-notes/qlanalyser/QLANALYSER_EEG_GLOSSARY_CN.md`
- `docs/product/qlanalyser_project_design_system_20260628.md`
- `docs/modules/epilepsy_source_workbench_replica_detailed_design.md`

Adopted rules:

- Major UI work must have a persistent design contract.
- Main scientific object must dominate the workbench.
- One primary action per decision area.
- No duplicate controls or noisy status blocks.
- Empty/loading/error/success/disabled/long-task/stale states are product surfaces.
- Critical tasks require browser-path evidence, not only API checks.
- Results must separate raw data, processed data, descriptive metrics, scientific interpretation, and non-medical boundary.
- Design tokens, focus state, semantic status colors, chart colors, and visual regression states must be governed.

## 3. Product Architecture Decision

### 3.1 Recommended route

Use a hybrid migration path:

1. Short term: keep existing `epilepsy-workbench.html` as an implementation shell only, but enter it from the main app as a governed child surface with inherited state and explicit return/result links.
2. Main product target: move epilepsy and sleep workbenches into the main app navigation/view model as first-class child pages:
   - `view=epilepsy-staging`
   - `view=sleep-staging`
3. Long term: extract shared waveform staging components so epilepsy and sleep reuse the same waveform/window/session/correction infrastructure while keeping their domain labels and result schemas separate.

### 3.2 Why not standalone pages

Standalone pages create user and data-chain breakage:

- Users cannot tell whether Data Preparation still applies.
- Results do not naturally appear in the main Results module.
- Upload/select-data controls duplicate the main system.
- Report delivery cannot trust a unified artifact manifest.
- E2E tests become page-local instead of workflow-level.

### 3.3 What counts as child page

A child page must:

- keep QLanalyser shell context or clear parent breadcrumbs;
- display current project, EEG file, data preparation plan id/revision, task id, and contract version;
- prevent primary independent upload unless explicitly in a fallback/import mode;
- save staged/corrected results into main result/artifact contracts;
- provide return actions to Analysis Tasks and Results.

## 4. Data and State Contract

Every epilepsy/sleep staging session must be created from an existing prepared data context.

Required input contract:

```json
{
  "project_id": "proj_xxx",
  "input_file_id": "eeg_xxx",
  "analysis_task_id": "task_xxx",
  "module_name": "epilepsy_ml | sleep_staging",
  "workflow_id": "epilepsy_ml_xgboost | sleep_staging_*",
  "data_preparation_plan_id": "prep_xxx",
  "data_preparation_revision": 3,
  "data_preparation_contract_version": "qlanalyser-data-preparation-v0.2",
  "mode": "waveform_staging",
  "non_medical_scope": "research_support_only"
}
```

State layers:

```text
L0 source data: original EEG file, immutable
L1 prepared data contract: confirmed data preparation plan, immutable by staging page
L2 source analysis output: model/algorithm epoch predictions, immutable
L3 staging session draft: user manual corrections, undo/redo stack, dirty state
L4 saved staged result: corrected epochs/events/sleep stages, published to Results
L5 report/export package: downloadable evidence, summaries, manifests
```

Forbidden:

- child workbench directly mutating original EEG;
- child workbench overwriting source task artifacts;
- UI-only corrections that do not enter an auditable session/action log;
- result exports that bypass the Results module.

## 5. Workbench Types

### 5.1 Epilepsy-like event staging workbench

Primary job:

```text
Interactive EEG waveform and epoch/time-window staging for seizure-like candidate event research screening.
```

Core views:

- waveform viewport;
- epoch/state strip;
- candidate event table;
- Stage_Code / Seizure / Normal control;
- manual correction action log;
- source vs corrected event summary;
- save/publish to Results.

Main labels:

- Use: `癫痫样事件筛查`, `候选事件`, `Seizure-like candidate`, `Normal`, `人工矫正`, `科研筛查支持`.
- Avoid: diagnosis, confirmed epilepsy, treatment, triage, clinical recommendation.

### 5.2 Sleep staging workbench

Primary job:

```text
Interactive EEG/EOG/EMG waveform staging and manual correction of sleep epochs.
```

Core views:

- waveform viewport;
- 30s epoch strip;
- hypnogram;
- stage palette: Wake, N1, N2, N3, REM, Unknown/Artifact if needed;
- single-epoch and range correction;
- undo/redo/save;
- sleep architecture summary;
- publish to Results.

Important distinction:

- Sleep staging is not epilepsy review.
- It shares waveform/session/action infrastructure but has separate labels, stage schema, summaries, and result cards.

## 6. Shared Frontend Architecture

Suggested shared component tree:

```text
MainApp
  AnalysisTaskPage
    MethodTaskStatusCallout
    OpenChildWorkbenchAction
  StagingChildPageShell
    ContextHeader
    StagingToolbar
    WaveformViewport
    TimelineOverview
    EpochStrip
    DomainPanel
      EpilepsyCandidatePanel | SleepHypnogramPanel
    CorrectionPanel
    ActionHistoryPanel
    SavePublishPanel
  ResultsPage
    DomainResultCard
```

Shared controllers:

- `WorkbenchContextController`: project/file/plan/task/session loading.
- `WaveformWindowController`: start/duration/channel/gain/filter/decimation/cache.
- `EpochSelectionController`: click, drag, range select, keyboard navigation.
- `CorrectionCommandController`: command objects for set-stage, bulk-apply, undo, redo, reset.
- `ResultPublicationController`: save session, generate artifacts, update Results state.

Mode separation:

```text
browse: pan/zoom only, no writes
selectEpoch: selects epoch/range, no direct write
correctStage: applies selected stage to selected epoch/range
inspect: hover/table/detail inspection
```

Controls must not look active when unavailable. Disabled controls need reasons.

Keyboard/mouse baseline:

- Wheel: horizontal pan.
- Ctrl/Cmd + wheel: anchored zoom.
- Left/Right: small pan or epoch move depending focus.
- PageUp/PageDown: page pan.
- Number/letter shortcuts only when focus is in workbench and help is visible.
- Escape: cancel transient selection.
- Undo/Redo: visible buttons plus keyboard shortcuts.

## 7. Backend/API Architecture

### 7.1 Session APIs

Recommended generalized session endpoints:

```text
POST /api/staging-sessions/from-task/{task_id}
GET  /api/staging-sessions/{session_id}
PATCH /api/staging-sessions/{session_id}
POST /api/staging-sessions/{session_id}/actions
POST /api/staging-sessions/{session_id}/undo
POST /api/staging-sessions/{session_id}/redo
POST /api/staging-sessions/{session_id}/reset
POST /api/staging-sessions/{session_id}/save
POST /api/staging-sessions/{session_id}/publish-results
```

Specialized aliases may exist:

```text
/api/epilepsy/staging-sessions/...
/api/sleep/staging-sessions/...
```

but they should share the same underlying command/session pattern.

### 7.2 Waveform chunk API

Required for performance:

```text
GET /api/eeg/files/{file_id}/waveform/chunk
  ?start_sec=0
  &duration_sec=30
  &channels=Fz,Cz,Pz,EOG,EMG
  &display_sfreq=200
  &mode=minmax
  &data_preparation_plan_id=prep_xxx
  &data_preparation_revision=3
```

Response requirements:

- exact covered start/duration;
- channel names/kinds/units;
- min-max envelope for long windows;
- source sampling rate and display sampling rate;
- cache status;
- no full-file waveform payload;
- no patient/private path leakage.

### 7.3 Correction command schema

```json
{
  "action_id": "act_xxx",
  "session_id": "stage_xxx",
  "domain": "epilepsy | sleep",
  "type": "set_stage | bulk_set_stage | reset | note",
  "target_epochs": [10, 11, 12],
  "before": ["Normal", "Normal", "Normal"],
  "after": ["Seizure", "Seizure", "Seizure"],
  "source": "button | shortcut | drag_range | table_edit",
  "created_at": "ISO-8601",
  "actor": "local-user"
}
```

## 8. Results Module Contract

The main Results module must become the single place where final outputs are visible.

### 8.1 Epilepsy result card

Minimum visible fields:

- input EEG file;
- data preparation plan id/revision;
- task id/workflow/model/scaler hash when available;
- source candidate count;
- corrected candidate count;
- manually changed epoch count;
- event table;
- Stage_Code strip or summary image;
- waveform evidence links;
- action log download;
- non-medical research-support boundary;
- open staging child page / continue correction action.

### 8.2 Sleep result card

Minimum visible fields:

- input EEG file;
- data preparation plan id/revision;
- task id/workflow/model/source;
- hypnogram;
- stage percentages and durations;
- sleep architecture summary;
- epoch stage table;
- manually changed epoch count;
- artifact/unknown epoch count;
- action log download;
- open sleep staging child page / continue correction action.

## 9. UX/Human-Factors Gates

Critical tasks:

1. Select current prepared EEG and confirm data preparation.
2. Start epilepsy/sleep analysis task.
3. Enter child staging workbench from Analysis Tasks.
4. Understand inherited context: project/file/plan/task.
5. Browse waveform and select epoch/range.
6. Apply manual correction.
7. Undo/redo/reset safely.
8. Save/publish staged result.
9. Find output in Results.
10. Download/export report package.

Required states:

- no prepared data;
- analysis running;
- staging session loading;
- waveform chunk loading;
- waveform stale/partial;
- save dirty state;
- save failed with retry;
- no candidates/no events;
- no sleep stage predictions;
- export success;
- disabled controls with reasons.

Accessibility:

- visible focus ring;
- keyboard route for critical actions;
- non-color encoding for stage classes;
- readable labels and units;
- no disappearing-only toast for critical state;
- reduced-motion safe interactions.

## 10. Migration Plan

### P0: Product contract and safe entry chain

- Rename UX from `复核工作台` to `分析台 / 分期与人工矫正` where appropriate.
- Analysis Tasks page shows task status and child-page entry in place.
- Child page receives task/file/plan context and hides primary independent upload route.
- Results page shows at least a structured placeholder/result card for epilepsy output.
- E2E: data preparation -> run epilepsy -> enter child page -> visible inherited context -> return results.

### P1: Shared waveform staging foundation

- Extract shared waveform viewport/controller from WaveformWorkbench.
- Add lightweight waveform chunk API with min-max decimation.
- Add staging session model/action stack.
- Add epilepsy manual stage correction save and results publication.
- E2E: select epoch, mark Seizure/Normal, undo/redo, save, result card changes.

### P2: Sleep staging and advanced result contracts

- Add sleep analysis task entry.
- Add sleep child workbench with hypnogram and Wake/N1/N2/N3/REM palette.
- Add sleep result card and report package integration.
- Add dense-data/long-recording performance evidence.

### P3: Hardening

- visual regression matrix;
- accessibility/focus audit;
- large EDF performance;
- true owner-data regression;
- human-factors formative evidence pack.

## 11. E2E Acceptance Matrix

| ID | Path | Expected evidence |
| --- | --- | --- |
| ES-01 | Data Preparation -> confirm -> epilepsy task | payload includes data_preparation_plan_id/revision/contract_version |
| ES-02 | epilepsy task complete -> open child page | child page visible inside main-system context or governed child shell |
| ES-03 | child page context | project/file/plan/task shown, no primary independent upload required |
| ES-04 | waveform interaction | pan/zoom/select epoch works on real canvas/data, not static image |
| ES-05 | epilepsy correction | set Seizure/Normal changes selected epoch strip and action log |
| ES-06 | undo/redo/reset | action stack restores previous labels |
| ES-07 | save/publish | staging session saved and artifacts generated |
| ES-08 | Results output | Results page shows epilepsy result card and downloads |
| SL-01 | sleep task -> child page | sleep staging page opens with inherited prepared data |
| SL-02 | sleep correction | Wake/N1/N2/N3/REM correction changes hypnogram and table |
| SL-03 | sleep publish | Results page shows hypnogram, stage summary, epoch table |
| UX-01 | empty/loading/error | all major states have screenshots and recovery actions |
| A11Y-01 | keyboard | focus and keyboard path reaches waveform, correction, save, results |

## 12. Top Risks

1. Keeping standalone page behavior and breaking workflow continuity.
2. Duplicate upload/data selection inside child pages.
3. UI corrections not persisted into auditable artifacts.
4. Results module not receiving staged outputs.
5. Full-file waveform loading causing slow or frozen UI.
6. Mixing epilepsy/sleep/PSD result schemas.
7. Medical overclaim wording.
8. Undo/redo action stack diverging from saved session.
9. Lack of empty/error/long-task states.
10. E2E only checking DOM existence, not real workflow completion.

## 13. Claude 4.8 Review Status

Requested by owner: open a Claude 4.8 sidecar for architecture review.

Attempted route:

```text
python C:/Users/XGN/.codex/skills/claude-relay-window/scripts/claude_relay.py --prompt ping
```

Current result:

```text
The command line is too long.
```

Conclusion: Claude relay is currently unavailable in this session. Do not treat this document as Claude-reviewed. The full Claude prompt is saved at:

```text
work/claude_arch_review/claude_epilepsy_sleep_child_workbench_arch_prompt.md
```

A Codex read-only review subagent was started as a temporary substitute, but Codex remains final acceptance owner.

## 14. Current Codex Verdict

Conditional GO for design/spec implementation.

Do P0 documentation and contract-first integration next. Do not start large code surgery until the child-page contract, result contract, and E2E paths are accepted.

Implementation should begin with the smallest safe user-visible slice:

```text
Analysis Tasks status callout
-> child page inherited context
-> no-primary-upload mode
-> Results card placeholder/contract
-> E2E route evidence
```

Then add real waveform staging/correction APIs.
