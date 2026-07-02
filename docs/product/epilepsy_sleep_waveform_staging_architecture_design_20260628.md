# QLanalyser Epilepsy/Sleep Waveform Staging Child Pages - Architecture Design

Date: 2026-06-28  
Status: P0 design package for implementation  
Scope: Epilepsy-like event waveform staging and sleep staging as QLanalyser main-system child pages  
Sources: owner correction, Claude 4.8 opus review, Codex design review, local QLanalyser design system  
Forbidden scope: router, Headroom, gateway, IPC, model route, TimeChart, PSD/BandPower mixing, medical diagnosis wording

Architecture guardrail:

- `docs/product/epilepsy_sleep_staging_predev_adversarial_gate_20260628.md`

This architecture is not ready for implementation unless the guardrail is satisfied. The guardrail converts the owner's repeated UI corrections into enforceable state, control, information-ownership, waveform-interaction, and Results-flow contracts.


## 1. Architecture Decision

Use a hybrid migration path.

P0 may reuse the existing epilepsy HTML implementation shell internally, but the product experience must be an inherited Analysis subview inside the QLanalyser main navigation frame. It must not behave as a separate app, a standalone landing page, or an independent primary upload page in this path.

P1 introduces server-authoritative staging sessions and result publication.

P2 introduces the sleep staging workbench using the same child-page/session/waveform infrastructure.

Target product chain:

```text
Project/Data -> Data Preparation -> Analysis Tasks -> Staging Subview -> Save/Publish -> Results -> Report Delivery
```

## 2. State Ownership

| Layer | Content | Owner | Child page mutability |
| --- | --- | --- | --- |
| L0 | Original EEG | Data module | never |
| L1 | confirmed data preparation plan | Data Preparation | read only |
| L2 | source analysis output | Analysis task | read only |
| L3 | staging draft/actions | Staging session | editable |
| L4 | saved staged result | Staging session service | save/publish only |
| L5 | report/export package | Results/Report service | generated |

## 3. Navigation-Frame Child Subview Contract

Required inherited context:

```json
{
  "project_id": "proj_xxx",
  "input_file_id": "eeg_xxx",
  "analysis_task_id": "task_xxx",
  "domain": "epilepsy | sleep",
  "module_name": "epilepsy_ml | sleep_staging",
  "workflow_id": "epilepsy_ml_xgboost | sleep_staging_*",
  "data_preparation_plan_id": "prep_xxx",
  "data_preparation_revision": 3,
  "data_preparation_contract_version": "qlanalyser-data-preparation-v0.2",
  "mode": "waveform_staging",
  "non_medical_scope": "research_support_only"
}
```

## 4. Frontend Architecture

```text
MainApp
  AnalysisTaskView
    MethodTaskStatusCallout
  StagingChildShell(embed=1)
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
  ResultsView
    DomainResultCard
```

P0 uses an inherited shell or route that carries `embed=1&task=...&plan=...&rev=...&contract=...` as context, but it must be presented within the main QLanalyser navigation frame. Upload/project/fixture bootstrap controls are suppressed in embed mode.

Required navigation behavior:

- the global navigation/header/sidebar remains visible or is owned by the parent main app shell;
- the active location is still part of Analysis, not a separate product;
- moving to Results is a same-frame view switch or navigation state, not a return out of the workbench;
- breadcrumbs may show `Analysis / Epilepsy-like staging`, but they are not a substitute for the main navigation framework.

## 5. Backend Architecture

Existing epilepsy review-session routes can be kept as aliases, but the target model is a generalized staging session:

```text
POST /api/staging-sessions/from-task/{task_id}
GET  /api/staging-sessions/{session_id}
POST /api/staging-sessions/{session_id}/actions
POST /api/staging-sessions/{session_id}/undo
POST /api/staging-sessions/{session_id}/redo
POST /api/staging-sessions/{session_id}/reset
POST /api/staging-sessions/{session_id}/save
POST /api/staging-sessions/{session_id}/publish-results
```

Waveform serving should reuse existing window/chunk/minmax APIs. Do not introduce TimeChart in this round.

## 6. Results Contract

Epilepsy result card minimum fields:

- EEG file and preparation plan id/revision;
- task/workflow/model hash when available;
- source candidate count and corrected candidate count;
- manually changed epoch count;
- Stage_Code strip or summary image;
- event table;
- waveform evidence links;
- action log download;
- non-medical research-support boundary;
- continue staging action.

Sleep result card minimum fields:

- EEG file and preparation plan id/revision;
- task/workflow/source;
- hypnogram;
- Wake/N1/N2/N3/REM percentages and durations;
- sleep architecture summary;
- epoch stage table;
- manually changed epoch count;
- action log download;
- continue staging action.

## 7. Domain Firewall

Epilepsy fields: `Stage_Code`, `seizure_candidate`, `normal`, `candidate_event`, `spectrogram`.

Sleep fields: `sleep_stage`, `Wake`, `N1`, `N2`, `N3`, `REM`, `Artifact`, `hypnogram`.

Forbidden inside epilepsy/sleep staging namespace: `band_power`, `psd_band_power`, `channel_band_power`.

## 8. P0 Architecture Gate

P0 may start only if:

- epilepsy task payload always carries confirmed non-default data preparation plan fields;
- child page displays inherited context before waveform/detail data finishes loading;
- embed mode suppresses primary upload/select-file path;
- E2E proves data preparation -> task -> child page context;
- no claims of published corrected Results are made before server-authoritative staging session exists.

## 9. Owner-Correction Guardrails Before Development

These guardrails convert the owner's repeated WaveformWorkbench/Data Preparation corrections into architecture blockers. They must be checked before any implementation slice is accepted.

### 9.1 No Duplicate Information

The child page may show each concept in one primary location only:

- time/window position: one timeline overview plus one concise status label, not multiple competing progress bars;
- selected data: one context header, not repeated file panels;
- preparation plan: one inherited context block, not repeated hidden debug badges;
- task state: one task status callout, not a card, toast, and panel saying the same thing;
- next action: one primary action per decision area.

If two controls perform the same function, one must be removed, demoted to an advanced menu, or explicitly scoped.

### 9.2 No Useless or Decorative Buttons

Every visible button must pass this test:

```text
Can the target user explain what happens if they click it?
Is it enabled only when the action is possible?
Does it change state, navigate, save, export, or explain a concrete blocker?
Is there exactly one primary button in this decision area?
```

Buttons that only duplicate another control, silently do nothing, or exist for developer convenience are release blockers.

### 9.3 Waveform Is the Primary Scientific Object

The staging child page must not open as a hero/dashboard/upload page. After context is loaded, the main first-viewport object is the waveform/epoch staging surface:

```text
ContextHeader
-> WaveformViewport + Timeline/EpochStrip
-> Domain correction panel
-> Action history / Save-Publish
```

Static images may be exported evidence, but not the main interactive waveform.

### 9.4 No Independent-Tool Feeling

In inherited `embed=1` mode, the child subview must not feel like a separate application. It must show:

- parent project/file/preparation/task context;
- the main QLanalyser navigation frame;
- Analysis as the active workflow location;
- Results as a same-frame destination or panel;
- non-medical research-support boundary;
- no primary upload/select-file path;
- no lab fixture bootstrap as the default customer path.

### 9.5 Results Backflow Is Part of the Architecture

The workbench is not complete when a correction is made. It is complete only when the corrected/staged output is discoverable from the main Results module. P0 may label this as a contract/placeholder, but P1 must implement artifact publication and Results cards.

## 10. Single Source of Truth Ownership

To prevent the repeated Data Preparation/WaveformWorkbench issue of duplicated status and competing controls, every state fact has one owner and one primary display location.

| Fact | State owner | Primary display | Secondary display allowed? |
| --- | --- | --- | --- |
| current project/file/plan/task | WorkbenchContextController | ContextHeader | no, only compact tooltip |
| running/completed/failed task state | parent task state | Analysis task status callout | Results card after task completion |
| waveform time window | WaveformWindowController | TimelineOverview | status label may summarize, not duplicate control |
| selected epoch/range | EpochSelectionController | EpochStrip + CorrectionPanel | no |
| current mode | InteractionModeController | StagingToolbar | cursor/style mirrors only |
| dirty/saved/published state | CorrectionCommandController / server session | SavePublishPanel | Results card after publish |
| candidate or stage counts | domain result summary | DomainPanel | Results card after publish |
| error/recovery | owning controller | nearest affected panel | global toast only as secondary |

If a proposed UI needs to show the same fact in multiple places, the design must specify which copy is authoritative and why the duplicate is unavoidable.

## 11. Minimum State Machine

P0/P1 implementation must respect this state machine. Controls are illegal unless their target state is reachable.

```text
NoContext
  -> ContextLoaded
ContextLoaded
  -> TaskRunning | SourceReady | SourceMissing | ContextInvalid
TaskRunning
  -> SourceReady | SourceMissing | TaskFailed
SourceReady
  -> Browse
Browse
  -> SelectEpochRange | Inspect | ContextStale
SelectEpochRange
  -> Browse | CorrectionDraft
CorrectionDraft
  -> Saved | SaveFailed | ResetToSource
Saved
  -> Published | PublishFailed | CorrectionDraft
Published
  -> ResultsVisible | CorrectionDraft
ContextStale
  -> ReloadContext | BlockCorrection
```

Control policy:

- Upload/select EEG controls are hidden in `ContextLoaded` and later inherited states.
- Stage palette is disabled in Browse and Inspect.
- Save is enabled only when dirty draft exists.
- Publish is enabled only after a server-saved session.
- Results action is enabled after a task result or published staging output exists.
- Reset requires explicit confirmation when dirty actions exist.
