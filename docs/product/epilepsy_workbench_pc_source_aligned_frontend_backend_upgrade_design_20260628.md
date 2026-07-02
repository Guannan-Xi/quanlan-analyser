# QLanalyser Epilepsy Staging Workbench PC-Source-Aligned Upgrade Design

Date: 2026-06-28
Status: design baseline for next implementation slice
Scope: epilepsy-like event staging child page, data-preparation inheritance, waveform operation, manual correction, Results handoff
Boundary: research screening support only; not for diagnosis, confirmation, treatment, triage, or medical advice

## 1. Route And Evidence

### 1.1 Route decision

This document is the integration artifact after three evidence lanes:

- PC source study lane: read-only inspection of `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC`.
- Web adversarial review lane: read-only inspection of current QLanalyser web epilepsy workbench and prior staging child-page gates.
- Codex acceptance lane: local source verification, design-system gate application, and final front-end/back-end design synthesis.

Claude 4.8 / Opus live review was re-run on 2026-06-29 through the local Claude CLI route with stdin prompt delivery and PC source read permission. The returned review is counted as completed evidence:

```text
work/claude_arch_review/claude48_epilepsy_upgrade_review_20260629.md
```

Claude verdict:

```text
conditional_go
```

Claude's key acceptance note: the design baseline is strong enough to build against, but the shipped Web implementation is still the pre-design standalone page. The root P0 blocker is `frontend/app.js:3714 epilepsyWorkbenchUrl()`, which currently omits `embed=1`, `plan`, `rev`, `contract`, and `results`.

### 1.2 Sources verified

PC source files:

- `AR_analyser_PC/src/Data_Info.py`
- `AR_analyser_PC/src/Epilepsy_Analysis_main.py`
- `AR_analyser_PC/src/EpilepsyAnalysis.py`
- `AR_analyser_PC/src/EpilepsyAnalysis_STD.py`
- `AR_analyser_PC/src/EpilepsyAnalysis_ML.py`
- `AR_analyser_PC/src/PreviewandRejection.py`
- `AR_analyser_PC/src/MatplotEventHandler.py`

Current Web files:

- `frontend/app.js`
- `frontend/epilepsy-workbench.js`
- `frontend/epilepsy-workbench.css`
- `backend/api/epilepsy_workbench.py`
- `scripts/e2e_epilepsy_workbench.mjs`

Design and product gates:

- `docs/product/epilepsy_sleep_staging_predev_adversarial_gate_20260628.md`
- `docs/product/epilepsy_sleep_waveform_staging_detailed_design_20260628.md`
- `D:\QuanLanKnowledgeBase\manifests\design\GOOGLE_LABS_DESIGN_MD_CONTRACT_TOOL_20260627.md`
- `D:\QuanLanKnowledgeBase\learning-notes\design\UX_STATE_FEEDBACK_EMPTY_ERROR_LOADING_MOTION_GATE_CN.md`
- `D:\QuanLanKnowledgeBase\learning-notes\qlanalyser\HUMAN_FACTORS_FORMATIVE_SUMMATIVE_EVIDENCE_PACK_STANDARD_CN.md`

## 2. Product Intent

The epilepsy analysis page should become a child view in the main QLanalyser workflow. It is not a separate upload tool, not a detached review app, and not a static waveform preview. The user enters it after data preparation and epilepsy task creation. It inherits:

- project context;
- selected EEG file;
- confirmed data-preparation plan;
- data-preparation revision;
- data-preparation contract version;
- epilepsy task id;
- task artifacts;
- Results destination.

The page's job is:

1. Display algorithm candidate epochs and events with EEG/EMG/ACC/time-frequency evidence.
2. Let the user browse waveform and stage results with low latency.
3. Let the user manually correct stage labels in an auditable draft layer.
4. Save the draft session.
5. Publish corrected outputs back to the main Results module when the server-side artifact contract is available.

Sleep staging should reuse the same shell later, but sleep staging is P2/internal until real sleep artifacts, labels, and tests exist.

## 3. PC Source Behavior Facts

### 3.1 Entry model

In the PC client, epilepsy is not opened as a generic waveform viewer. `Data_Info.py` exposes epilepsy through the analysis menu and splits it into Threshold Epilepsy Analysis and ML Epilepsy Analysis. Both paths import the processed raw data first, then open a maximized analysis window.

Web implication:

- The web entry should start from a completed QLanalyser analysis task, not from a standalone upload path.
- STD and ML are algorithm strategies inside one domain module. They should not create two unrelated customer pages.

### 3.2 Stage_Code is discrete state

`Epilepsy_Analysis_main.py` creates `StageArray` and draws it as discrete spans. `EpilepsyAnalysis.py` maps:

- `0 -> Normal`
- `1 -> Seizure`

The important source behavior is not the exact color, but the categorical strip. It is not a probability curve and not a continuous RMS line.

Web implication:

- The Web stage strip must draw categorical epoch blocks.
- It may show confidence or RMS as secondary evidence, but the primary stage layer is discrete.
- Manual correction must create a new review layer; source algorithm artifacts stay read-only.

### 3.3 Dual-level waveform navigation

The PC source has a global view plus a local window:

- global view shows long-range context and Stage_Code;
- a rectangle marks the current local window;
- local view shows the selected epoch range;
- the rectangle snaps to epoch boundaries.

Web implication:

- The web page needs one overview timeline and one local waveform viewport.
- The overview should be the single time navigation owner.
- Window changes must snap to epoch boundaries in correction/epoch modes.
- Browse mode can pan continuously, but stage correction operates on epoch-aligned selections.

### 3.4 Multi-track evidence

The richer PC workbench uses stacked tracks:

- Stage_Code / hypnogram-like strip;
- EEG;
- EMG;
- ACC;
- spectrogram/time-frequency evidence.

The PC implementation links the X axis across plots and allows horizontal pan/zoom. It keeps Y behavior mostly controlled, with amplitude settings separated by signal type.

Web implication:

- The Web page should show EEG/EMG/ACC/time-frequency as synchronized evidence tracks where available.
- Y-axis amplitude sensitivity should be per group: EEG uV/row, EMG scale, ACC scale.
- A single time window controls all tracks.
- If EMG/ACC/spectrogram is missing, show a quiet missing-evidence state, not a blank chart.

### 3.5 Manual correction and history

PC correction semantics:

- select one epoch by click;
- drag to select continuous epoch range;
- right click can clear selection in the newer handler;
- `Normal` and `Seizure` write to selected epochs;
- `Undo`, `Redo`, and `Reset` operate on the edit history;
- shortcuts include `Shift+1` for Normal and `Shift+2` for Seizure;
- operation logs are written.

Web implication:

- Buttons and keyboard shortcuts must share one command handler.
- Browse mode must not write.
- Correction mode writes only after a valid selection.
- Undo/Redo/Reset must be state-driven and disabled with reasons when unavailable.
- Every correction command needs before/after/provenance fields.

### 3.6 Loading and performance behavior

PC source uses background threads, progress bars, loading overlay, delayed enablement of result buttons, and display optimizations such as visible-range updates. It does not treat analysis and display as instant.

Web implication:

- The web page must separate task running, source-ready, waveform loading, stale waveform, draft saving, and publishing.
- Old waveform data may be shown only as stale/ghosted data. It must never masquerade as the current time window.
- Pan/zoom should update UI state immediately and then resolve data asynchronously.
- Large `All` windows need a performance warning and coarser rendering path.

## 4. Current Web Gap Summary

### 4.1 Main app entry gap

Current `epilepsyWorkbenchUrl(task)` only sends:

- `task`
- `mode`
- `renderer`
- `api`
- `v`

It does not send:

- `embed=1`
- `domain=epilepsy`
- `plan`
- `rev`
- `contract`
- `results`

This breaks data-preparation inheritance and makes the page feel like a separate tool.

### 4.2 Independent page chrome gap

Current `frontend/epilepsy-workbench.js` renders:

- independent header/nav;
- hero;
- run screening button;
- lab data button;
- file select;
- upload control;
- refresh controls;
- parameter panel as primary entry.

In the target product, these controls are forbidden in inherited customer mode. They may exist only in explicit lab/dev mode.

### 4.3 Waveform duplication gap

The current waveform area can show statusbar, minimap, toolbar text, notice, and stale banner at the same time. Several controls repeat the same facts:

- current time window;
- active mode;
- selected event;
- filter profile;
- waveform status.

Target rule: each user-visible fact has one primary owner. Secondary places may use icons or microcopy only when they do not compete with the primary owner.

### 4.4 Results handoff gap

`backend/api/epilepsy_workbench.py` has review session and export routes, but `exports` returns inline CSV/JSON strings. It does not register corrected outputs as standard task artifacts. Therefore the main Results/Report system cannot reliably consume the corrected session outputs.

### 4.5 E2E gap

Existing E2E mainly proves the old standalone page can open and interact. It does not sufficiently prove:

- inherited child-page context;
- direct URL blocking;
- data-preparation plan/revision/contract display;
- pan/zoom/select pixel-level behavior;
- stale/loading behavior;
- Results artifact registration;
- no duplicate controls;
- no customer path into lab/dev upload workflow.

### 4.6 Claude 4.8 review additions

Claude 4.8 agreed with the main design direction and added the following concrete P0 constraints:

1. `frontend/app.js:3714 epilepsyWorkbenchUrl()` is the first implementation blocker. No child-frame behavior, context validation, anti-stale waveform identity, or Results handoff is reachable until this URL passes inherited context.
2. `frontend/epilepsy-workbench.js` must remove standalone chrome, hero, primary upload, file picker, and silent fixture bootstrap in customer inherited mode.
3. Seizure/Normal controls currently appear in more than one place with different disabled logic. P0 must consolidate correction into one command authority.
4. Waveform status currently appears in multiple competing places. P0 must enforce one authoritative mode/window/status owner.
5. Browse mode must be read-only for all writes, not only for Seizure/Normal. Marking `needs_review` is also a write and must require Correction mode or an explicit write state.
6. Stale waveform should be ghosted for the whole stale duration, not only announced with a transient banner. Correction writes should be disabled while stale data is visible.
7. Results publication must remain disabled or clearly labeled as future contract until corrected outputs are registered as standard task artifacts.

## 5. Target Front-End Design

### 5.1 Route contract

From the main analysis task card:

```text
wanted URL query
embed=1
domain=epilepsy
task=<task_id>
plan=<data_preparation_plan_id>
rev=<data_preparation_revision>
contract=qlanalyser-data-preparation-v0.2
results=#results
renderer=canvas
api=<api_base>
```

Allowed direct lab route:

```text
lab=1
fixture=demo
```

Customer/default direct URL without `embed=1` must not show upload/lab workflow. It should show a controlled state in the main navigation frame:

```text
Open this staging page from Analysis after selecting data and confirming data preparation.
```

### 5.2 Page shell

The child page must sit inside the main QLanalyser navigation framework:

- global sidebar/header remains visible or is mirrored by the parent shell;
- active navigation remains under Analysis;
- Results is a same-frame tab/view destination;
- no return-to-main button;
- no separate app brand header.

Layout:

```text
Row 1: ContextHeader
Row 2: Task status callout
Row 3: Overview timeline
Row 4: Waveform viewport with synchronized evidence tracks
Row 5: Correction/action panel and history
Row 6: Save/Publish/Results handoff
```

### 5.3 ContextHeader

ContextHeader is the only primary place for:

- project;
- EEG file;
- task id/status;
- algorithm mode: ML or STD;
- data-preparation plan id;
- revision;
- contract version;
- non-medical research boundary.

Do not repeat these facts in large cards below. The waveform area can show abbreviated chips only if they are operationally needed.

### 5.4 Task status callout

Task status has one owner:

- Queued
- Running
- Failed
- SourceReady
- SourceMissing
- ContextStale

If the algorithm task is running, the page shows stage/progress and disables correction. It must not offer upload as the next action.

If source artifacts are missing, the page explains which artifact is missing:

- epoch score table;
- event table;
- summary;
- waveform source.

### 5.5 Overview timeline

The overview timeline is the only time-navigation control. It contains:

- full file duration;
- current local window;
- event density;
- Stage_Code blocks;
- selected event/range;
- draft correction marks;
- stale/loading state for requested window.

The lower progress bar or duplicate slider should be removed or demoted. One visible timeline is enough.

### 5.6 Waveform viewport

The central viewport is the main work surface. Required tracks:

- Stage_Code categorical strip;
- EEG waveform;
- EMG waveform when available;
- ACC waveform when available;
- spectrogram/time-frequency evidence when available.

Rules:

- all tracks share the same time window;
- waveform must remain visible after pan/zoom;
- direct image fallback is allowed only as a degraded state and must be labeled as static fallback;
- Canvas is the default renderer;
- old payload cannot be re-timed to a new window;
- stale data must be ghosted and labeled.

### 5.7 Mode model

Default mode: Browse.

Modes:

```text
Browse
InspectCandidate
SelectEpochRange
Correction
```

Browse:

- wheel pans horizontally;
- Ctrl/Cmd + wheel zooms around pointer;
- click inspects;
- drag pans or selects only if the active tool is selection;
- `Shift+1` and `Shift+2` show a disabled-reason hint and do not write.

Correction:

- user explicitly enters correction mode;
- valid epoch/range selection is required;
- `Shift+1` writes Normal;
- `Shift+2` writes Seizure candidate;
- Undo/Redo/Reset operate on command history.

### 5.8 Correction panel

The correction panel should not be a pile of always-visible buttons. It should follow task logic:

1. Current selection summary.
2. Suggested actions.
3. Correction commands.
4. Action history.
5. Save draft.
6. Publish to Results when available.

Buttons:

- Mark as Normal
- Mark as Seizure candidate
- Needs review
- Undo
- Redo
- Reset draft
- Save draft
- Publish corrected outputs
- Open Results

Every button must have a control-state matrix row.

### 5.9 Results handoff

P0:

- show current publish status;
- do not show a working publish button unless backend artifact registration exists;
- if publish is unavailable, show disabled button with reason.

P1:

- Publish corrected outputs as standard task artifacts;
- same-frame switch to Results view;
- Results card shows corrected epoch table, corrected event table, action log, session manifest, and source artifacts.

### 5.10 Copy rules

Use customer-visible Chinese terms:

- `癫痫样事件分析台`
- `候选事件`
- `人工矫正`
- `修正草稿`
- `保存草稿`
- `发布到结果`

Avoid:

- `复核工作台` as the main product name;
- raw developer labels as primary text;
- positive medical claims;
- upload/lab wording in inherited mode;
- duplicate explanatory text near every control.

## 6. Target Back-End Design

### 6.1 Staging session model

Existing `EpilepsyReviewSession` can be kept internally for P0, but the target model should be a domain-neutral staging session:

```json
{
  "id": "stg_xxx",
  "domain": "epilepsy",
  "project_id": "proj_xxx",
  "input_file_id": "eeg_xxx",
  "analysis_task_id": "task_xxx",
  "workflow_id": "epilepsy_ml_xgboost",
  "data_preparation_plan_id": "prep_xxx",
  "data_preparation_revision": 3,
  "data_preparation_contract_version": "qlanalyser-data-preparation-v0.2",
  "source_artifacts": [],
  "overrides": {},
  "actions": [],
  "redo_actions": [],
  "status": "draft",
  "publish_state": "not_published",
  "non_medical_scope": "research_screening_support_only"
}
```

### 6.2 Context validation

Session creation must validate:

- task exists;
- task input file matches inherited file;
- task parameters contain data-preparation plan id/revision/contract;
- inherited URL context matches task parameters;
- source artifacts exist or missing artifacts are explicitly reported.

If a mismatch exists, return `ContextStale` and do not silently continue.

### 6.3 Waveform API

Current endpoint:

```text
GET /api/eeg/files/{file_id}/waveform-window
```

Required additions:

- `server_elapsed_ms`
- `read_elapsed_ms`
- `filter_elapsed_ms`
- `encode_elapsed_ms`
- `payload_bytes`
- `cache.hit`
- `request_id`
- `window_key`
- `source_data_revision`

Longer-term:

- pyramid manifest per EEG;
- min-max envelope decimation;
- server-side LRU cache;
- prefetch current/previous/next window;
- optional binary format after JSON budget is exceeded.

### 6.4 Command API

Manual correction should become command-based:

```json
{
  "action_id": "act_xxx",
  "domain": "epilepsy",
  "type": "set_stage",
  "target_epochs": [10, 11],
  "before": ["Normal", "Normal"],
  "after": ["Seizure", "Seizure"],
  "source": "button",
  "actor": "local-user",
  "created_at": "ISO-8601"
}
```

Commands support:

- append;
- undo;
- redo;
- reset;
- note;
- save draft;
- export audit log.

### 6.5 Publish API

P1 endpoint:

```text
POST /api/staging-sessions/{session_id}/publish
```

Generated artifacts:

- `corrected_epoch_table.csv`
- `corrected_events.csv`
- `staging_session_manifest.json`
- `action_log.jsonl`
- optional `waveform_evidence_snapshot.png`

These must be registered through the standard artifact service so:

- `GET /tasks/{task_id}/artifacts` returns them;
- Results can display them;
- Report generation can include them;
- exports include source artifact references and correction provenance.

### 6.6 Algorithm boundary

The staging workbench must not alter ML/STD source outputs. It creates a review/correction layer. Required source fields:

- source algorithm mode;
- model/scaler/feature schema hash for ML;
- threshold parameter set for STD;
- epoch length;
- source artifact ids;
- data-preparation plan id/revision/contract.

## 7. Latency And Feedback Budget

### 7.1 User-perceived budgets

| Action | Target feedback | Target data completion |
| --- | --- | --- |
| Open child page with completed task | context visible < 500 ms | source artifacts loaded < 1500 ms |
| Click candidate event | selection feedback < 100 ms | waveform window p50 < 500 ms, p95 < 1200 ms |
| Wheel pan cached window | visual update < 50 ms | no network required |
| Wheel pan uncached window | stale/loading label < 100 ms | waveform p50 < 500 ms |
| Ctrl/Cmd wheel zoom | anchor feedback < 100 ms | waveform p50 < 500 ms |
| Mark Normal/Seizure | UI draft < 100 ms | session PATCH < 1000 ms |
| Undo/Redo | UI draft < 100 ms | session PATCH < 1000 ms |
| Save draft | disabled/progress immediate | complete < 1500 ms |
| Publish to Results | progress immediate | complete < 3000 ms or async status |

### 7.2 Loading/stale states

Required states:

- `ready`
- `loading_new_window`
- `stale_window_visible`
- `partial_tracks`
- `waveform_error`
- `source_missing`
- `context_stale`

Rules:

- stale waveform must be greyed or ghosted;
- stale label must include requested window and displayed window;
- new request id must ignore older responses;
- buttons that write correction remain tied to selected epoch/range, not to stale waveform.

### 7.3 Performance metrics

Every waveform-window response should expose:

```json
{
  "metrics": {
    "server_elapsed_ms": 0,
    "read_elapsed_ms": 0,
    "filter_elapsed_ms": 0,
    "encode_elapsed_ms": 0,
    "payload_bytes": 0
  },
  "cache": {
    "hit": false,
    "key": "..."
  }
}
```

Front-end evidence should record:

- request start/end;
- JSON parse time;
- canvas draw time;
- long tasks;
- stale duration;
- dropped/ignored stale responses.

## 8. Control-State Matrix Baseline

The implementation must store a machine-readable matrix. P0 rows:

| Control id | Visible when | Enabled when | Click result | Duplicate rule |
| --- | --- | --- | --- | --- |
| `epilepsy-open-staging` | completed epilepsy task exists | data-preparation plan confirmed | same-frame child view | replaces standalone review wording |
| `epilepsy-mode-browse` | SourceReady | always | Browse mode | single mode owner |
| `epilepsy-mode-correction` | SourceReady | source artifacts loaded | Correction mode | single correction entry |
| `epilepsy-overview-window` | SourceReady | waveform source exists | set window | replaces duplicate lower progress slider |
| `epilepsy-stage-normal` | Correction mode | selected epochs > 0 | append set_stage Normal | no write in Browse |
| `epilepsy-stage-seizure` | Correction mode | selected epochs > 0 | append set_stage Seizure candidate | no write in Browse |
| `epilepsy-undo` | CorrectionDraft | undo stack not empty | undo command | disabled reason required |
| `epilepsy-redo` | CorrectionDraft | redo stack not empty | redo command | disabled reason required |
| `epilepsy-reset-draft` | CorrectionDraft | draft dirty | reset after confirmation | high-risk confirmation |
| `epilepsy-save-draft` | CorrectionDraft | draft dirty and session ready | save session | progress state required |
| `epilepsy-publish-results` | Saved | artifact publish backend available | publish artifacts | hidden/disabled until P1 |
| `epilepsy-open-results` | Published | result artifacts registered | same-frame Results | no new independent page |

## 9. E2E Acceptance Plan

### 9.1 P0 E2E

1. Main analysis task card opens child page with `embed=1`, `task`, `plan`, `rev`, and `contract`.
2. Child page shows ContextHeader and does not show hero, upload, lab data, file select, or refresh-as-primary controls.
3. Direct customer URL without `embed=1` shows inherited-context blocked state.
4. Browse mode left click/keyboard does not write correction.
5. Correction mode requires valid selection before Normal/Seizure buttons enable.
6. Shift+1/Shift+2 share the same command handler as buttons.
7. Overview pan changes actual waveform pixels and final API request window.
8. Ctrl/Cmd wheel zoom changes duration around anchor and keeps waveform visible.
9. Stale response is ignored if a newer request finishes later.
10. Stale waveform is visibly labeled and not treated as ready.
11. Undo/Redo/Reset button states match stack state.
12. Save draft persists actions to session.
13. Publish button is absent or disabled with reason until artifact registration exists.
14. Forbidden copy scan passes.
15. No duplicate time/progress controls for the same window.

### 9.2 P1 E2E

1. Publish corrected outputs registers standard artifacts.
2. Results card lists corrected epoch table, corrected events, action log, manifest, and source artifacts.
3. Report generation can include corrected outputs with provenance.
4. Large EDF p95 waveform-window latency is within budget.
5. All/long-window mode uses envelope/pyramid and shows performance guidance.

### 9.3 Visual evidence

Required screenshots:

- desktop 1440 inherited child view;
- laptop 1280 inherited child view;
- mobile 390 controlled/narrow view;
- loading waveform state;
- stale waveform state;
- correction mode with selection;
- saved draft;
- Results handoff.

## 10. Implementation Roadmap

### P0: Make the current epilepsy workbench product-correct

Files likely touched:

- `frontend/app.js`
- `frontend/epilepsy-workbench.js`
- `frontend/epilepsy-workbench.css`
- `scripts/e2e_epilepsy_workbench.mjs`
- new `scripts/validate_epilepsy_staging_child_page_contract.mjs`
- evidence under `work/release_evidence/20260628-epilepsy-staging-upgrade/`

Work:

1. Update main app URL builder and button wording.
2. Add embed context parsing.
3. Add inherited ContextHeader.
4. Hide standalone hero/upload/lab/file entry in embed customer mode.
5. Add direct URL blocked state.
6. Reduce duplicated status/time controls.
7. Enforce Browse vs Correction command boundary.
8. Add control-state matrix JSON.
9. Expand E2E for inherited context, no duplicate controls, and waveform interaction.
10. Add waveform `window_key`/request identity checks so late responses cannot paint as current.
11. Ghost stale waveform frames and disable correction writes while stale.
12. Ensure `needs_review` and any other review mark are treated as writes, not Browse actions.

### P1: Server-backed staging session and Results publish

Files likely touched:

- `backend/api/epilepsy_workbench.py`
- task/artifact service integration files
- Results UI renderer
- report artifact reader

Work:

1. Add staging session fields for plan/rev/contract/project/domain.
2. Add context stale validation.
3. Add publish endpoint that registers artifacts.
4. Add Results card.
5. Add report handoff.
6. Add waveform metrics/cache fields.

### P2: Shared epilepsy/sleep staging shell

Work:

1. Extract shared staging shell components.
2. Add sleep domain only after real sleep source artifacts exist.
3. Add sleep-specific stage labels and hypnogram semantics.
4. Add sleep E2E and evidence.

## 11. Risks And Non-Goals

### Risks

- Directly copying PC full-data loading would make Web slow and unstable.
- Keeping standalone upload/lab paths in customer mode will confuse the workflow.
- Publishing without artifact registration will create false success.
- Duplicate progress/time/status controls will recreate the current UI confusion.
- Positive medical wording could violate the product boundary.

### Non-goals

- Do not touch router, Headroom, gateway, IPC, or model route.
- Do not connect TimeChart in this slice.
- Do not mix PSD/BandPower into the staging workbench.
- Do not claim sleep staging is customer-ready.
- Do not rewrite the entire analysis architecture in P0.

## 12. Acceptance Decision

The current Web epilepsy workbench is not yet release-ready as the final customer-facing staging page. It has useful pieces: review session, waveform-window endpoint, Canvas/SVG rendering paths, Browse/Correction boundary, and local undo/redo draft. The upgrade should proceed, but the next implementation must start with P0 inherited child-page integration and interaction/state cleanup before adding more features.

Recommended next real artifact:

```text
work/release_evidence/20260628-epilepsy-staging-upgrade/control_state_matrix.json
```

Recommended next code slice:

```text
P0 inherited epilepsy child page:
main app entry -> embed context -> ContextHeader -> hide standalone controls -> direct URL block -> no duplicate time/progress controls -> E2E evidence
```
