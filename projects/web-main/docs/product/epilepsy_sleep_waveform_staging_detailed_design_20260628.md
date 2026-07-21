# QLanalyser Epilepsy/Sleep Waveform Staging Child Pages - Detailed Design

Date: 2026-06-28  
Status: P0 design package for implementation  
Scope: Epilepsy-like event waveform staging and sleep staging as QLanalyser main-system child pages  
Sources: owner correction, Claude 4.8 opus review, Codex design review, local QLanalyser design system  
Forbidden scope: router, Headroom, gateway, IPC, model route, TimeChart, PSD/BandPower mixing, medical diagnosis wording

Mandatory implementation gate:

- `docs/product/epilepsy_sleep_staging_predev_adversarial_gate_20260628.md`

The gate is part of this detailed design. Any implementation that adds a visible control, timeline, status, shortcut, or output path must update the gate-aligned control-state matrix first.


## 1. P0 First Code Slice

Implement epilepsy inherited child-page mode before generalized backend staging sessions.

Files expected to change in P0:

- `frontend/app.js`
- `frontend/epilepsy-workbench.js`
- `frontend/epilepsy-workbench.html` if needed for shell markers only
- `frontend/epilepsy-workbench.css`
- `scripts/e2e_main_epilepsy_entry_real_path.mjs`
- optionally one new static validator script

P0 should not change router/Headroom/gateway/IPC/model route.

## 2. Main App Entry

Extend `epilepsyWorkbenchUrl(task)` to include:

```text
embed=1
domain=epilepsy
task=<task_id>
plan=<data_preparation_plan_id>
rev=<data_preparation_revision>
contract=<data_preparation_contract_version>
results=#statistics
renderer=canvas
api=<api_base>
```

Button label changes:

- From: `打开癫痫复核工作台`
- To: `进入癫痫样事件分析台`

## 3. Epilepsy Workbench Embed Mode

Add:

```js
const EMBED = params.get("embed") === "1";
const CONTEXT_HINT = { plan, rev, contract, domain, return, results };
```

Embed behavior:

- call `loadTask(START_TASK_ID)`;
- render `ContextHeader` immediately;
- render inside the main QLanalyser navigation frame or parent application shell;
- skip primary upload panel;
- skip primary project/file select as an entry path;
- allow same-frame navigation to Analysis Tasks and Results;
- keep waveform/candidate/correction tools available when task artifacts are ready;
- if task is running, show long-task state and do not show upload fallback as next action.

## 4. ContextHeader Fields

Required visible fields:

- project name/id if available;
- EEG file name/id;
- task id;
- workflow id;
- data preparation plan id;
- data preparation revision;
- contract version;
- non-medical research-support boundary.

If any required field is missing, show an error state with recovery action back to Data Preparation or Analysis Tasks.

## 5. Staging Session Target Model

Target session object:

```json
{
  "id": "stg_xxx",
  "domain": "epilepsy",
  "project_id": "proj_xxx",
  "input_file_id": "eeg_xxx",
  "analysis_task_id": "task_xxx",
  "data_preparation_plan_id": "prep_xxx",
  "data_preparation_revision": 3,
  "data_preparation_contract_version": "qlanalyser-data-preparation-v0.2",
  "source_artifacts": [],
  "overrides": {},
  "actions": [],
  "redo_actions": [],
  "status": "draft"
}
```

P0 may keep existing epilepsy-review session internally, but UI should use staging/correction language.

## 6. Correction Command

```json
{
  "action_id": "act_xxx",
  "domain": "epilepsy | sleep",
  "type": "set_stage | bulk_set_stage | reset | note",
  "target_epochs": [10, 11],
  "before": ["Normal", "Normal"],
  "after": ["Seizure", "Seizure"],
  "source": "button | shortcut | drag_range",
  "created_at": "ISO-8601",
  "actor": "local-user"
}
```

## 7. Results Integration Design

P0: render clear task status and future result contract; no false publish claim.

P1: publish `corrected_epoch_table.csv`, `corrected_events.csv`, `staging_session_manifest.json`, `action_log.json`, and optional evidence image artifacts. Register them as normal artifacts so existing Results and Report modules can consume them.

## 8. Sleep Workbench Detailed Direction

P2 creates `sleep-workbench.html/js/css` or main-app view using shared staging shell.

Fields:

- stage palette: Wake, N1, N2, N3, REM, Artifact, Unknown;
- default epoch length: 30s;
- panes: EEG/EOG/EMG;
- result artifacts: hypnogram image/json, epoch stage table csv, sleep architecture summary json, action log.

Do not promise real automated sleep model until workflow and backend are implemented.

## 9. UI Control Governance Before Coding

Before implementing any toolbar, side panel, card, or status block, create a local control matrix using this schema:

```json
{
  "control_id": "string",
  "surface": "analysis_task | epilepsy_staging | sleep_staging | results",
  "label": "customer-visible label",
  "primary_or_secondary": "primary | secondary | advanced | hidden",
  "visible_when": "state expression",
  "enabled_when": "state expression",
  "disabled_reason": "customer-visible reason",
  "click_result": "same-frame navigation | state change | save | export | help",
  "duplicates": "none or control_id it replaces",
  "e2e_assertion": "selector and expected result"
}
```

Implementation cannot add a visible button without this matrix entry.

## 10. Layout Contract For Staging Child Pages

The default desktop layout must follow this order:

```text
Row 1: ContextHeader, concise and single-line where possible
Row 2: WaveformViewport + EpochStrip as the dominant area
Row 3: Domain-specific correction panel and action history
Row 4: Save/Publish and Results handoff
```

Avoid:

- hero blocks after a task is already selected;
- large upload/file panels in inherited mode;
- multiple progress/time controls for the same window;
- side panels that push waveform below the first viewport;
- showing raw JSON or debug manifests in the customer default view.

## 11. State Synchronization Contract

The implementation must maintain a single source for each state:

- selected file and plan: parent task/context;
- waveform window: WaveformWindowController;
- selected epoch/range: EpochSelectionController;
- correction draft/actions: CorrectionCommandController or server session;
- task/result state: parent task plus Results publication state.

Do not update DOM text directly from multiple handlers without passing through the owning state/controller.

## 12. P0 Development Stop Conditions

Stop P0 implementation and go back to design if any of these appear:

- embed mode still shows primary upload/select-file workflow;
- inherited plan fields are missing from task payload;
- a visible button has no effect in E2E;
- waveform canvas is blank or static after data load;
- result path ends inside the child page and cannot be found from Results;
- sleep scope requires real algorithm work before the child-page shell is stable.

## 13. Required Control-State Table For P0

This section is the implementation-level state machine contract. It also enforces the No Duplicate Controls rule: one action has one primary control and one state owner.

The first implementation PR must include or generate this table for epilepsy embed mode:

| Control | NoContext | TaskRunning | SourceReady/Browse | SelectEpochRange | CorrectionDraft | Saved | Published | Error/Stale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Analysis/Results navigation within main frame | enabled | enabled | enabled | enabled | enabled | enabled | enabled | enabled |
| View Results | disabled | disabled | enabled if task result exists | enabled | enabled | enabled | enabled | enabled if previous result exists |
| Upload EEG | hidden | hidden | hidden | hidden | hidden | hidden | hidden | hidden |
| Select lab fixture | hidden | hidden | hidden | hidden | hidden | hidden | hidden | hidden |
| Pan/Zoom waveform | disabled | disabled/loading | enabled | enabled | enabled | enabled | enabled | disabled if stale blocks data |
| Select epoch/range | disabled | disabled | enabled | enabled | enabled | enabled | enabled | disabled |
| Set Seizure-like | disabled | disabled | disabled | enabled | enabled | enabled if new selection | enabled if new selection | disabled |
| Set Normal | disabled | disabled | disabled | enabled | enabled | enabled if new selection | enabled if new selection | disabled |
| Undo | disabled | disabled | enabled if actions exist | enabled if actions exist | enabled if actions exist | enabled if actions exist | enabled if actions exist | enabled if local actions exist |
| Redo | disabled | disabled | enabled if redo exists | enabled if redo exists | enabled if redo exists | enabled if redo exists | enabled if redo exists | enabled if redo exists |
| Reset | disabled | disabled | enabled if actions exist | enabled if actions exist | enabled if actions exist | enabled if actions exist | enabled if actions exist | disabled unless draft recoverable |
| Save | disabled | disabled | disabled | disabled | enabled | disabled | disabled | retry if save failed |
| Publish to Results | disabled | disabled | disabled | disabled | disabled | enabled | disabled | retry if publish failed |

This table must be kept aligned with E2E selectors.

## 14. Demonstrable Waveform Interaction Contract

P0 cannot accept "canvas exists" as proof of waveform functionality. The child page must demonstrate at least three interactions:

1. wheel or button pan changes the visible time window;
2. zoom changes duration or scale while keeping waveform visible;
3. clicking or dragging an epoch/range changes selected epoch/range state.

Evidence must include before/after screenshots or JSON measurements. A static canvas, screenshot image, or unchanged SVG does not pass.

## 15. Non-Embed Route Handling

Direct opening without `embed=1` must render one of these controlled states inside the main QLanalyser navigation frame:

```text
Customer/default: blocked inherited-context state with guidance to open from Analysis.
Lab/dev explicit mode: lab fixture/upload controls allowed only when lab parameter is present.
```

Do not let a customer reach a full independent upload workflow by typing the workbench URL directly.

## 16. Gate-Aligned Implementation Checklist

Before a code slice is accepted, verify:

1. `embed=1` child page renders `ContextHeader` and no primary upload/select-lab-data panel.
2. Direct customer URL without `embed=1` renders blocked inherited-context state inside the main navigation frame unless explicit lab/dev parameter is present.
3. One visible fact has one owner: task status, plan revision, current time window, active mode, dirty/saved state, selected range, and result availability cannot be duplicated as competing primary UI.
4. Browse mode is read-only; Correction mode creates auditable commands only after a valid selection.
5. The overview/timeline is the only time-navigation control for the same window.
6. Waveform interaction changes rendered content or selected state; static canvas or unchanged image does not pass.
7. Results publish is honest: P0 can show a future contract, but cannot claim registered corrected outputs until artifacts exist.
8. Sleep entry remains hidden/internal unless its real task, schema, correction session, Results card, and E2E are implemented.

## 17. Current vs Target Reconciliation

P0 implementation must begin by reconciling the current code with the target design. Adding new UI without removing or hiding conflicting current UI is not acceptable.

| Current code area | Existing behavior to verify | P0 target | Action |
| --- | --- | --- | --- |
| `frontend/app.js::epilepsyWorkbenchUrl` | URL lacks `embed`, `domain`, `plan`, `rev`, `contract`, `results` and may open a separate-feeling page | inherited same-frame Analysis subview carries all context | migrate |
| `frontend/app.js::renderEpilepsyWorkbenchAction` | label still says review workbench | label says epilepsy-like event staging/analysis workbench | rename |
| `frontend/epilepsy-workbench.js::params` | reads `api/task/mode/renderer`, no embed state | reads embed and context fields | build_new |
| `renderHero()` | first viewport contains run/lab/refresh actions | hidden in embed mode | hide_in_embed |
| `renderFilePanel()` | select file, refresh, lab data, upload form | hidden as primary path in embed mode | hide_in_embed |
| direct URL without embed | can behave as full standalone tool | customer blocked state inside main navigation frame unless lab/dev flag exists | build_new |
| waveform loading path | must be checked before claiming pan/zoom current-window behavior | prove current payload changes rendered waveform | verify_before_claim |
| `epilepsy-review-sessions` backend | PATCH/export review session | allowed as internal P0 save spine only if labeled honestly | keep_P0_migrate_P1 |
| local history/overrides | browser-local undo/redo | allowed for draft, not a Results publish mechanism | keep_P0 |
| publish/result controls | no registered corrected Results artifacts yet | no false publish button in P0 | block_until_P1 |
| `waveform-statusbar` / minimap / hints | duplicate time/mode/status risk | one primary timeline and one mode label | delete_or_demote_duplicates |
| page titles/H1/buttons | review/workbench/staging naming drift | one customer-visible name | rename_consistently |
| sleep target sections | target design without implementation | P2/internal copy only | mark_P2_only |

This table must be updated if implementation discovers another legacy surface that conflicts with the child-page contract.
