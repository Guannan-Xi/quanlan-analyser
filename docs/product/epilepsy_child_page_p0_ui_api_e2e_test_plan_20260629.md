# QLanalyser Epilepsy Child Page P0 UI/API/E2E Test Plan

Date: 2026-06-29
Status: mandatory P0 implementation test contract
Scope: epilepsy-like event staging child page inside QLanalyser main analysis flow
Design baseline:

- `docs/product/epilepsy_workbench_pc_source_aligned_frontend_backend_upgrade_design_20260628.md`
- `work/claude_arch_review/claude48_epilepsy_upgrade_review_20260629.md`
- `docs/product/epilepsy_sleep_staging_predev_adversarial_gate_20260628.md`

## 1. Release Verdict Rule

P0 can only be called release-candidate when all P0 tests below pass or have an explicit blocked reason with owner decision.

Hard blockers:

1. The epilepsy page opens as a standalone upload/lab workflow for customer routes.
2. The main app entry omits `embed=1`, `plan`, `rev`, `contract`, or `results`.
3. Browse mode writes any review/correction state.
4. `needs_review` writes in Browse mode.
5. Stale waveform is displayed as current ready waveform.
6. Seizure/Normal correction is possible while stale data is visible.
7. UI claims Results publication before corrected artifacts are registered.
8. The same primary fact is shown through competing controls.

## 2. Test Environment

Default local target:

```text
frontend: http://127.0.0.1:4174
backend: http://127.0.0.1:8001/api
main page: /?customer_demo=auto&teaching_demo=auto&api=http://127.0.0.1:8001/api&v=epilepsy-child-p0#analysis
epilepsy child page: /epilepsy-workbench.html?embed=1&domain=epilepsy&task=<task_id>&plan=<plan_id>&rev=<revision>&contract=qlanalyser-data-preparation-v0.2&results=%23results&renderer=canvas&api=http://127.0.0.1:8001/api
```

Required evidence output:

```text
work/release_evidence/20260629-epilepsy-child-page-p0/
```

Required evidence files:

```text
control_state_matrix.json
e2e_epilepsy_child_page_p0.json
static_epilepsy_child_page_contract.json
backend_epilepsy_waveform_contract.json
desktop_1440_child_page.png
desktop_1440_stale_waveform.png
desktop_1440_correction_mode.png
direct_url_blocked.png
```

## 3. Control-State Matrix Requirements

Every visible button, link, toggle, select, slider, timeline, canvas gesture, and keyboard shortcut must have:

```json
{
  "control_id": "epilepsy-stage-seizure",
  "surface": "epilepsy_child_page",
  "label": "Seizure candidate",
  "visible_when": "Embed && SourceReady && Correction",
  "enabled_when": "selected_epoch_count > 0 && !waveform_stale && !waveform_loading",
  "disabled_reason": "Select epochs in Correction mode after the current waveform window is ready.",
  "click_result": "append correction command",
  "success_state": "CorrectionDraft",
  "failure_state": "unchanged with message",
  "undo_or_recovery": "Undo removes the command",
  "authoritative_state_owner": "CorrectionCommandController",
  "duplicates": "none",
  "e2e_assertion": "[data-testid='epilepsy-stage-seizure'] disabled in Browse and stale states"
}
```

P0 control ids:

- `epilepsy-open-staging`
- `epilepsy-context-header`
- `epilepsy-mode-browse`
- `epilepsy-mode-correction`
- `epilepsy-overview-window`
- `epilepsy-waveform-frame`
- `epilepsy-stage-normal`
- `epilepsy-stage-seizure`
- `epilepsy-event-needs-review`
- `epilepsy-undo`
- `epilepsy-redo`
- `epilepsy-reset-draft`
- `epilepsy-save-draft`
- `epilepsy-publish-results`
- `epilepsy-open-results`
- `shortcut-shift-1`
- `shortcut-shift-2`
- `shortcut-e`

## 4. UI Surface Test Matrix

### UI-01 Main app entry passes inherited context

User path:

1. Open main QLanalyser analysis page.
2. Select or load teaching/demo EEG.
3. Confirm data-preparation plan.
4. Run epilepsy-like event screening.
5. Click the epilepsy child-page entry.

Assertions:

- link selector: `[data-testid="open-epilepsy-workbench"]`
- link URL contains:
  - `embed=1`
  - `domain=epilepsy`
  - `task=<task_id>`
  - `plan=<data_preparation_plan_id>`
  - `rev=<data_preparation_revision>`
  - `contract=qlanalyser-data-preparation-v0.2`
  - `results=%23results` or equivalent encoded Results route
  - `renderer=canvas`
- visible label is not `打开癫痫复核工作台`.
- visible label is `进入癫痫样事件分析台` or equivalent event-screening wording.

Failure examples:

- URL only contains `task/mode/renderer/api/v`.
- button implies an isolated review workbench.

### UI-02 Embed child page shows ContextHeader once

Open inherited URL.

Assertions:

- `[data-testid="epilepsy-context-header"]` exists.
- It contains project/file/task/plan/revision/contract boundary.
- Plan/revision/contract appear in ContextHeader and not again as competing large cards.
- Header copy says research support / non-medical boundary without positive medical claims.

### UI-03 Standalone controls hidden in inherited customer mode

Assertions in `embed=1`:

- no primary upload control.
- no primary file select.
- no `选中实验室数据`.
- no `运行筛查` hero CTA.
- no independent app hero.
- no `返回主程序` as the main navigation method.

Selectors/text that must be absent in inherited customer mode:

- `#eegUpload`
- `#fileSelect` as primary entry
- `#loadLatestEpilepsyFileBtn`
- `#runTaskTopBtn`
- `.hero`
- `.ep-top` standalone nav unless it is converted into main-frame shell.

### UI-04 Direct URL is blocked unless explicit lab/dev route

Open:

```text
/epilepsy-workbench.html?api=http://127.0.0.1:8001/api
```

Assertions:

- page shows controlled inherited-context blocked state.
- no upload/lab workflow is visible.
- message tells user to open from Analysis after data preparation.
- lab/dev controls are only visible when `lab=1` or explicit dev fixture route is present.

### UI-05 Single source of truth for mode/window/status

Assertions:

- active mode appears in one primary place only.
- current time window appears in overview/timeline as the primary owner.
- waveform status appears in one primary status element.
- no competing statusbar repeats File/Event/Window/Filter/Gain/Mode as equal-weight primary facts.

Automated check:

- count visible elements matching `Browse|Correction|Window|Filter|Gain|Mode`.
- allow concise chips only if `aria-hidden` or visually secondary.

### UI-06 Browse mode is fully read-only

Initial state:

- active mode is Browse.

Actions:

- click event row.
- click waveform.
- drag waveform selection.
- press `Shift+1`.
- press `Shift+2`.
- click `待复核`.
- click Seizure/Normal if visible.

Assertions:

- no `epochOverrides` changes.
- no `reviewActions` appended.
- no event review status changes.
- message explains Correction mode is required.
- Seizure/Normal/Needs Review controls are disabled or route to disabled reason, not a write.

### UI-07 Correction mode write boundary

Actions:

1. Click `[data-testid="epilepsy-waveform-mode-correct"]`.
2. Select one epoch or range.
3. Click Seizure candidate.
4. Undo.
5. Redo.
6. Reset draft.

Assertions:

- Seizure/Normal/Needs Review enable only after valid selection and ready waveform.
- correction command includes before/after target epochs.
- Undo restores previous Stage_Code.
- Redo reapplies Stage_Code.
- Reset asks for confirmation or has a clear high-risk disabled/confirm path.
- source algorithm artifacts are not modified.

### UI-08 `needs_review` is a write

Actions:

- In Browse: click `待复核`.
- In Correction: click `待复核` with selected event.

Assertions:

- Browse: no write, disabled reason.
- Correction: appends review action or event review status with provenance.

### UI-09 Keyboard shortcuts share command handler

Actions:

- Browse + `Shift+1`: no write.
- Browse + `Shift+2`: no write.
- Correction + selected epoch + `Shift+1`: writes Normal.
- Correction + selected epoch + `Shift+2`: writes Seizure candidate.
- `E`: enters Correction only when epoch mode is allowed; otherwise it is ignored with hint.

Assertions:

- keyboard and button produce identical action schema.
- shortcuts do not bypass disabled state.

### UI-10 Stale waveform ghosting

Setup:

- Load event waveform.
- Trigger pan/zoom to a different window while previous waveform is visible.

Assertions:

- previous frame is visually ghosted/dimmed for the entire stale period.
- stale label includes displayed window and requested window.
- correction buttons disabled while stale.
- late response with old window key does not repaint as current.
- once new response arrives, ghost class is removed and correction can be enabled only if Correction mode and selection are valid.

### UI-11 Waveform interaction is real

Actions:

- wheel pan.
- Ctrl/Cmd + wheel zoom.
- drag range selection.
- reset/fit event.

Assertions:

- canvas pixels or internal viewport state change after pan.
- zoom changes duration.
- selected epoch/range state changes after drag.
- waveform remains visible.
- static image fallback is not used in normal Canvas route.

### UI-12 Results honesty

P0 assertions:

- Publish button is absent or disabled with reason:
  - `发布到结果将在标准结果产物注册后启用`
  - or equivalent.
- UI may show `保存草稿`.
- UI must not show `已发布` unless corrected artifacts exist in `/tasks/{task_id}/artifacts`.

P1 assertions:

- after publish, artifacts include corrected epoch table, corrected events, session manifest, and action log.

## 5. API Test Matrix

### API-01 Review/staging session inherits context

Request:

```text
POST /api/tasks/{task_id}/epilepsy-review-sessions
```

Payload includes:

```json
{
  "input_file_id": "...",
  "workflow_id": "epilepsy_ml_xgboost",
  "data_preparation_plan_id": "...",
  "data_preparation_revision": 1,
  "data_preparation_contract_version": "qlanalyser-data-preparation-v0.2"
}
```

P0 acceptable:

- if API still uses old model, UI must at least preserve inherited context and show P1 server contract gap.

P1 required:

- server validates task parameters match payload.
- mismatch returns ContextStale.

### API-02 Waveform-window returns identity and metrics

Request:

```text
GET /api/eeg/files/{file_id}/waveform-window?start_sec=0&duration_sec=30&filter_profile_id=raw&max_points=2000
```

Assertions:

- response includes `start_sec`, `duration_sec`, `stop_sec`.
- response includes `window_key`.
- response includes `request_id`.
- response includes `source_data_revision`.
- response includes:
  - `metrics.server_elapsed_ms`
  - `metrics.read_elapsed_ms`
  - `metrics.filter_elapsed_ms`
  - `metrics.encode_elapsed_ms`
  - `metrics.payload_bytes`
- `cache.hit` exists.
- channel encoding is `raw` or `minmax`.

### API-03 Late response cannot override active window

Simulation:

1. Fire request A for window A.
2. Fire request B for window B.
3. Make A resolve after B.

Assertions:

- UI active `window_key` remains B.
- A is recorded as ignored/dropped.

### API-04 Export does not claim Results publication

Request:

```text
POST /api/epilepsy-review-sessions/{session_id}/exports
```

P0 assertions:

- export may return inline CSV/manifest.
- UI must label it as draft/export, not Results publication.

P1 assertions:

- publish endpoint registers standard artifacts and `/tasks/{task_id}/artifacts` lists them.

## 6. Performance Test Matrix

### PERF-01 First visible context

Budget:

- ContextHeader visible under 500 ms after document interactive for existing completed task.

### PERF-02 Waveform-window latency

Budget:

- p50 < 500 ms for <= 8 channels / 30 s / 2000-2400 max points.
- p95 < 1200 ms.
- If exceeded, stale/loading state must appear within 100 ms.

### PERF-03 Cached pan

Budget:

- cached pan feedback < 50 ms.

### PERF-04 Canvas draw

Budget:

- p95 canvas draw < 100 ms.
- no long task > 200 ms during ordinary pan/zoom.

## 7. Visual Regression Matrix

Required screenshots:

1. 1440 desktop inherited child page ready.
2. 1440 direct URL blocked state.
3. 1440 Browse mode no-write.
4. 1440 Correction mode with selected epoch.
5. 1440 stale waveform ghosted.
6. 1280 inherited child page ready.
7. 390 narrow controlled layout.

Visual checks:

- waveform is the dominant surface.
- no large hero in inherited mode.
- no duplicated progress/time controls.
- correction controls are grouped and disabled with understandable reason.
- copy is non-medical research-support wording.
- no mojibake in browser.

## 8. Static Contract Checks

Scan must pass:

- no `TimeChart` integration in P0 runtime path.
- no positive diagnostic/confirmed seizure/treatment/triage/medical advice wording.
- no upload/lab controls visible in inherited customer mode.
- no `打开癫痫复核工作台` main label.
- `epilepsyWorkbenchUrl()` includes inherited parameters.
- `needs_review` write path requires Correction mode.
- stale window branch applies ghost class and disables correction writes.

## 9. P0 Acceptance Checklist

```text
P0_ACCEPTANCE:
  inherited_entry_url: pass | fail
  context_header_once: pass | fail
  standalone_controls_hidden: pass | fail
  direct_url_blocked: pass | fail
  browse_readonly: pass | fail
  needs_review_gated: pass | fail
  correction_command_state: pass | fail
  stale_ghost_and_write_disabled: pass | fail
  waveform_interaction_real: pass | fail
  results_honesty: pass | fail
  api_waveform_identity_metrics: pass | fail
  visual_regression: pass | fail
  forbidden_copy_scan: pass | fail
```

Final P0 verdict rules:

- Any `fail` in inherited entry, Browse read-only, stale handling, or Results honesty is `blocked`.
- API waveform identity/metrics may be `partial` only if UI anti-stale uses client request id and the backend P1 gap is recorded.
- Results publish may be `partial` only if publish remains disabled with reason.
