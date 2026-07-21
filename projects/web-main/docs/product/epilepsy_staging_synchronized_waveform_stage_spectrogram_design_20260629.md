# QLanalyser Epilepsy/Sleep Staging Synchronized Evidence Panels Design

Date: 2026-06-29
Status: P0 implementation contract for main-system child page
Surface: Analysis Tasks -> Epilepsy-like Event Screening child page; future Sleep Staging child page

## 1. Owner Intent

The staging workbench must show four synchronized evidence views:

1. Waveform view: EEG/EMG/ACC time-domain evidence.
2. Video view: synchronized source-signal video analysis / behavior evidence when available.
3. Stage_Code / epoch strip: discrete staging result and candidate-event intervals.
4. Spectrogram / time-frequency evidence panel: frequency-time evidence used during manual review.

The spectrogram panel is not the formal TFR/Band Power analysis module. It is a review evidence layer inside epilepsy/sleep staging. Formal TFR, Multitaper TFR, PSD, and Band Power remain independent analysis methods.

The video panel is not an exported result video or a decorative thumbnail. It is a synchronized source evidence layer for behavior, motion artifact, environment context, or future sleep/epilepsy visual review. It must share the same selected event and time-scale state as waveform, spectrogram, and Stage_Code.

## 2. P0 Design Principle

All evidence panels must be driven by one shared timeline state:

```json
{
  "selected_event_id": "evt-1",
  "window_start_sec": 0,
  "time_scale_sec": 5 | 30 | 300,
  "domain": "epilepsy | sleep",
  "source_task_id": "task_xxx",
  "data_preparation_plan_id": "prep_xxx",
  "data_preparation_revision": 1
}
```

A scale change, event click, epoch click, or future pan/zoom action must update all panels together. The UI must not allow each chart to keep an independent hidden time range.

## 3. Layout Contract

Desktop order inside the main navigation frame:

1. Compact task context.
2. Screening status row.
3. Waveform panel: primary electrophysiology evidence view.
4. Video panel: synchronized original source-signal video analysis / behavior evidence.
5. Spectrogram panel: time-frequency evidence synchronized to waveform and video.
6. Stage_Code / Epoch strip.
7. Candidate events.
8. Summary and source contract.
9. Sticky correction panel.

Reason: waveform and video are source evidence layers; spectrogram is derived review evidence; Stage_Code is the discrete annotation layer. Users should visually move from raw signal/video -> frequency evidence -> discrete stage -> correction.

## 4. Shared Scale Semantics

P0 scale buttons:

| Scale | Label | Purpose |
| --- | --- | --- |
| 5s | Detail | Inspect waveform morphology and local time-frequency burst. |
| 30s | Review | Standard event/epoch review scale. |
| 300s | Overview | Coarse trend and candidate density overview. |

The active scale must be visible in waveform, video, spectrogram, and Stage_Code panel via `data-sync-scale` and visible text. Changing scale must not clear selected event or correction draft.

## 5. Video and Spectrogram Evidence Panel Contract

Required selectors:

- `[data-testid="inline-epilepsy-video-panel"]`
- `[data-testid="inline-epilepsy-video-canvas"]`
- `[data-testid="inline-epilepsy-spectrogram-panel"]`
- `[data-testid="inline-epilepsy-spectrogram-canvas"]`
- `[data-epilepsy-action="set-time-scale"]`

Required attributes:

- `data-sync-scale`: current shared scale in seconds.
- `data-selected-event`: selected candidate event id or empty string.
- `data-evidence-layer="source-video"` for the video evidence layer.
- `data-evidence-layer="spectrogram"` for the time-frequency evidence layer.

Visual requirements:

- Video panel shows a synchronized source-video frame/strip placeholder, selected-event window, and behavior/motion evidence copy.
- Video panel must explicitly say it is source evidence, not diagnosis and not formal TFR/PSD/Band Power output.
- Show frequency bands on y-axis: delta/theta/alpha/beta/gamma or simplified labels in P0.
- Show event window aligned with selected event.
- Show "review evidence only" copy; do not claim formal TFR output.
- At 300s scale, reduce detail and emphasize density/trend.
- At 5s scale, emphasize local event burst.

## 6. Adversarial Review Findings and Preventive Rules

Round 1 - Global IA:
- Risk: adding a new panel may make the page feel longer and more redundant.
- Decision: spectrogram panel must sit between waveform and Stage_Code as an evidence layer, not as another summary/status block.

Round 2 - State synchronization:
- Risk: waveform, video, spectrogram, and Stage_Code can drift if each owns its own range.
- Decision: one shared `state.epilepsyInline.timeScaleSec` drives all evidence layers.

Round 3 - Button governance:
- Risk: evidence panels each expose zoom buttons.
- Decision: only one evidence toolbar owns scale controls. Other panels display current scale but do not duplicate controls.

Round 4 - Scientific boundary:
- Risk: spectrogram panel may be confused with formal TFR analysis.
- Decision: label it as "时频证据层 / review evidence", not "TFR result".

Round 5 - Workflow:
- Risk: scale changes could erase correction state.
- Decision: selected event and draft commands must persist across scale changes.

## 7. Implementation Scope

P0 changes:

- `frontend/index.html`: add video and spectrogram panel containers.
- `frontend/app.js`: add shared scale state and rendering synchronization.
- `frontend/styles.css`: add video, spectrogram, and scale-control styles.
- `scripts/e2e_main_epilepsy_entry_contract.mjs`: add synchronization assertions.

P0 non-goals:

- No backend spectrogram computation yet.
- No formal TFR artifact registration.
- No router/Headroom/gateway/IPC/model-route changes.
- No TimeChart dependency.

## 8. Future Backend Contract

P1 endpoint can return spectrogram tiles:

```http
GET /api/eeg/files/{file_id}/spectrogram-window?start_sec=...&duration_sec=...&channels=...&freq_min=1&freq_max=80&mode=review
```

For now, P0 uses deterministic review mock rendering in the main page, explicitly marked as a review evidence placeholder. P1 can add synchronized source-signal video metadata/tile loading if the owner provides authorized video files and time-alignment metadata.
