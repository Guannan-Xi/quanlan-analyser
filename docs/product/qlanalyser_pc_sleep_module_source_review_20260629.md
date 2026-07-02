# QLanalyser-PC Sleep Module Source Review

Date: 2026-06-29
Status: source-grounded research note for Web epilepsy/sleep staging workbench
Scope: `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC` sleep staging module
Review mode: read-only source review; no business code changes

## 1. Source Files Reviewed

Primary PC sleep module files:

- `src/QlassAnalysiscopy.py`
- `src/QlassAnalysis.py`
- `view/xxxAnalysis_main.ui`
- `view/Anesthesia_Analysis_main.ui`
- `src/Qlass/Qlass.py`
- `src/Qlass/models/2_LightGBM-1EEG.pkl`
- `src/Qlass/models/1_LightGBM-2EEG.pkl`

Related comparison files:

- `src/Anesthesia_Analysis_main.py`
- `src/EMGAnalysis.py`

The clearest business flow is in `QlassAnalysiscopy.py`. The more productized and performance-oriented implementation is in `QlassAnalysis.py`.

## 2. What The PC Sleep Module Actually Does

The module is not merely a results table. It is a synchronized scoring workbench:

1. Run sleep staging on prepared raw EEG.
2. Show aligned evidence layers:
   - hypnogram / Stage_Code strip;
   - EEG waveform;
   - EMG envelope;
   - ACC signal;
   - EEG spectrogram.
3. Let the user page through epochs.
4. Let the user select one or more epochs.
5. Let the user manually change stage labels.
6. Support undo / redo / reset style correction history.
7. Save user-edited score files and export data/images/statistics.

This matches the owner's product requirement for the Web version: enter the analysis workbench first, inspect synchronized waveform/stage/evidence panels, then run or review staging, then manually correct, then publish to Results.

## 3. Sleep Staging Algorithm Flow

The analysis thread is `Thread_run_analysis(QThread)`.

Default settings found in source:

- model: `2_LightGBM-1EEG`
- epoch length: `4` seconds
- stage codes:
  - `1 = Wake`
  - `2 = NREM`
  - `3 = REM`
- EEG/EMG/ACC are selected from user-chosen channels.
- raw data is resampled to `100 Hz`.

Main flow:

```text
load model
-> resample raw to 100 Hz
-> pick EEG / EMG / ACC channels
-> compute EMG envelope
-> extract_features_from_raw(...)
-> model.predict(features_df)
-> build df_score: Epoch No., Stage_Code, Stage
-> correct_sleep_transitions(df_score)
-> compute stage counts
-> compute spectrogram
-> enable plotting/review controls
```

Important implementation detail:

- `QlassAnalysiscopy.py` loads `Qlass/models/{model_name}.pkl` directly with `joblib.load`.
- `QlassAnalysis.py` uses a `model_loader.get_model(...)` path, suggesting later optimization around model reuse.
- The code logs several slow steps: resampling, feature extraction, prediction, and save/in-memory transfer.

## 4. Sleep Transition Post-Processing

The function `correct_sleep_transitions(df)` applies a simple physiological plausibility rule.

Observed rule:

```text
if previous stage is REM and current stage is Wake:
    change current stage to NREM
```

The source comment says the purpose is to avoid an unreasonable direct jump in sleep-stage transitions.

Migration implication:

- Web sleep staging should not present raw model output as the only truth.
- It should distinguish:
  - source model output;
  - rule-adjusted output;
  - manual correction revision.
- This should be auditable in Results.

## 5. Spectrogram Design

The PC module computes EEG spectrogram as a review evidence layer:

```text
fs = raw_processed.info["sfreq"]
nperseg = fs * 4
noverlap = nperseg * 0.9
STFT boundary = "zeros"
power = 10 * log10(abs(Zxx) + 1e-10)
frequency range = 0.5-50 Hz
color scale = 10th to 99th percentile
```

Rendering differences:

- `QlassAnalysiscopy.py` uses Matplotlib `imshow` with `RdBu_r`.
- `QlassAnalysis.py` uses PyQtGraph `ImageItem`, transforms image coordinates into real seconds/Hz, and uses a CET-R4-like colormap.

Migration implication:

- Web spectrogram should not be a decorative block.
- Minimum credible P0/P1 contract:
  - STFT;
  - 0.5-50 Hz;
  - log power dB;
  - robust percentile color scale;
  - synchronized x-axis with waveform and Stage_Code.
- It must be labeled as review evidence, not formal TFR / PSD / Band Power analysis.

## 6. Synchronized Evidence Layout In PC Version

The clearest PC layout in `QlassAnalysiscopy.py` is:

```text
Hypnogram / Stage strip
EEG waveform
EMG envelope
ACC signal
EEG spectrogram
Time slider
```

The newer `QlassAnalysis.py` moves waveform/spectrogram rendering toward PyQtGraph for better interaction performance:

- `plot_eeg`
- `plot_emg`
- `plot_acc`
- `plot_widget` for spectrogram

All views share the same time window through functions such as:

- `update_display_range`
- `on_slider_changed`
- `update_display_previous`
- `update_display_next`
- `update_display_previous_more`
- `update_display_next_more`
- `goto_epoch`

Core product idea:

```text
one current time window
-> update waveform
-> update EMG
-> update ACC
-> update spectrogram
-> update hypnogram/Stage_Code
```

This is exactly the discipline Web needs. Each panel must not own an independent hidden time range.

## 7. Navigation And Time-Window Model

The PC module has two navigation models:

### 7.1 Epoch-based paging

In the simpler implementation:

- `epoch_start` is the source of truth.
- `n_epochs_display` controls page width.
- previous/next changes by one epoch.
- previous_more/next_more changes by one page.
- goto_epoch jumps to a specific epoch.
- slider maps directly to `epoch_start`.

### 7.2 Second-based slider

In the newer implementation:

- slider value is seconds (`pos_sec`).
- `n_epochs_display * epoch_length` gives current page duration.
- `x_min = pos_sec`.
- `x_max = min(pos_sec + page_duration, total_time)`.
- all PyQtGraph view boxes receive the same xRange.

Migration recommendation:

- For Web, use second-based `windowStartSec` and `windowDurationSec` as the canonical state.
- Derive epoch index from seconds:
  - `epochIndex = floor(timeSec / epochLengthSec)`.
- This works for both epilepsy and sleep and avoids duplicated state.

## 8. Selection And Manual Correction

PC selection supports:

- single epoch click;
- Ctrl multi-select;
- Shift range select;
- mouse drag across a range;
- hover status showing epoch number.

Selected epochs are stored as:

- `current_selected_epoch`
- `current_selected_epochs`
- `shift_begin`
- highlight overlays

Manual correction flow:

```text
select epoch(s)
-> click Wake / NREM / REM
-> record previous Stage_Code in history
-> write new Stage_Code and Stage
-> recompute counts
-> redraw stage strip / views
-> enable Undo
-> clear Redo
```

The newer UI also binds shortcuts:

- `Shift+1 = Wake`
- `Shift+2 = NREM`
- `Shift+3 = REM`

Migration recommendation:

- Web should model each correction as a command:

```json
{
  "action_id": "act_xxx",
  "domain": "sleep_staging",
  "epoch_indices": [10, 11, 12],
  "old_values": [2, 2, 1],
  "new_value": 3,
  "label": "REM",
  "source": "manual",
  "created_at": "ISO-8601"
}
```

- Undo/redo should operate on command objects, not scattered DOM state.
- Source model output should remain read-only. Manual correction should create a review revision.

## 9. Controls Worth Migrating

The following PC controls are product-relevant:

- run analysis / abort analysis;
- page previous / next;
- jump to epoch;
- epochs per page;
- time slider that can be clicked and dragged;
- stage editing buttons;
- undo / redo / reset;
- EEG amplitude range;
- EMG amplitude range;
- ACC amplitude range;
- save data / save picture / statistics;
- load history/cache.

For Web, these should be grouped by workflow rather than copied as a dense desktop toolbar:

1. Evidence navigation:
   - previous page, next page, jump, slider, scale.
2. Display controls:
   - channels, amplitude, spectrogram visibility, stage strip visibility.
3. Scoring/correction:
   - domain-specific labels, undo, redo, clear draft.
4. Publish:
   - save review draft, publish to Results.

## 10. Controls Not To Copy Directly

Do not copy these PC patterns directly into Web:

- large fixed left-side parameter panel that competes with waveform space;
- log textbox as a primary user-facing area;
- repeated status text in multiple places;
- path-specific cache handling under user Documents;
- direct CSV overwrite as the main persistence model;
- heavy full-plot redraw after each edit;
- silent print/log side effects as user feedback;
- ambiguous "Plot Results" step after analysis is already complete.

Web should make the waveform/scoring workbench feel like one continuous task, not a sequence of desktop utility buttons.

## 11. Performance Lessons

PC performance decisions worth carrying forward:

- use a background analysis thread;
- support abort/cancel;
- resample display/analysis data intentionally;
- calculate EMG envelope once and reuse it;
- cache/reuse model when possible;
- avoid redrawing full plots on every pan;
- update only visible curve data where possible;
- keep the same x-range for every evidence panel;
- disable repeated update signals during synchronized range changes;
- clean large arrays and model objects when no longer needed.

For Web, this maps to:

- light waveform chunk API for browsing;
- separate analysis task API for formal analysis;
- server-generated or cached spectrogram tiles;
- request cancellation / stale response suppression;
- min-max waveform decimation for long windows;
- visible target latency:
  - cached pan < 50 ms;
  - new waveform chunk < 500 ms;
  - initial visible waveform < 2 s;
  - formal staging task can be longer but must show progress and remain cancellable.

## 12. Web Epilepsy Workbench Migration Implications

The current Web epilepsy child page should evolve from "event card plus chart area" into a synchronized scoring workbench.

Required canonical state:

```json
{
  "domain": "epilepsy",
  "windowStartSec": 0,
  "windowDurationSec": 30,
  "epochLengthSec": 5,
  "selectedEpochIndices": [],
  "selectedEventId": null,
  "analysisTaskId": "task_xxx",
  "dataPreparationPlanId": "prep_xxx",
  "dataPreparationRevision": 1,
  "reviewRevision": 0
}
```

Panels that must subscribe to this state:

- waveform;
- Stage_Code strip;
- spectrogram;
- candidate events;
- correction panel;
- Results draft summary.

No panel should have a separate hidden time window.

Epilepsy label set can remain domain-specific:

- Normal / background;
- Candidate event;
- Needs review;
- Artifact / exclude if needed.

The UI text must keep non-medical boundaries:

- "candidate event";
- "research screening support";
- "manual review";
- not "diagnosis", "confirmed seizure", or "treatment".

## 13. Web Sleep Staging Workbench Migration Implications

The sleep workbench should share the same shell as epilepsy but use sleep-specific stages and statistics.

Domain-specific stage set:

- P0: Wake / NREM / REM, matching PC source.
- P1: Wake / N1 / N2 / N3 / REM / Artifact if model and data contract support it.

Required panels:

- EEG waveform;
- optional EMG envelope if channel exists;
- optional ACC signal if channel exists;
- spectrogram;
- hypnogram / Stage strip;
- stage statistics;
- manual correction history.

Recommended defaults:

- epoch length: 4 s if using the existing PC model lineage;
- visible page: 30-100 epochs depending on screen width;
- time slider: draggable and clickable;
- shortcuts:
  - `Shift+1` Wake;
  - `Shift+2` NREM;
  - `Shift+3` REM.

## 14. Video Panel Correction

Earlier design material contained a P0 video panel concept. The owner later clarified that the current "原始信号视频分析 / Video unavailable" panel is not needed.

Therefore current P0 rule:

- do not show a video panel when the current dataset has no real synchronized video;
- do not show "Video unavailable" as a permanent empty panel;
- do not use a placeholder image to imply video evidence;
- only reintroduce video after there is authorized synchronized video data and explicit time-alignment metadata.

## 15. Proposed Unified Web Workbench Contract

Create one shared workbench concept:

```text
ScoringWorkbench
  domain = epilepsy | sleep_staging
  source = confirmed data preparation plan + source analysis task
  evidence = waveform + spectrogram + stage/hypnogram + optional EMG/ACC
  review = selected epoch/event + command history
  output = saved review revision + Results card
```

Shared behavior:

- enter from main Analysis page, inside the main navigation shell;
- inherit confirmed data preparation plan;
- show waveform first;
- allow run/re-run of formal algorithm inside the workbench;
- display model output as read-only source layer;
- apply manual correction as editable review layer;
- publish review revision to Results.

Differences by domain:

| Area | Epilepsy | Sleep |
| --- | --- | --- |
| source algorithm | epilepsy ML / candidate event screening | LightGBM sleep staging or future sleep model |
| stage labels | normal, candidate, needs review | Wake, NREM, REM |
| output | candidate event table + Stage_Code | hypnogram + sleep architecture stats |
| correction target | event/epoch candidate labels | every epoch stage |
| statistics | candidate count, duration, review changes | stage duration/percentage/latency |

## 16. Immediate Recommendations For Current QLanalyser Web Work

P0 recommendations:

1. Keep the epilepsy workbench as a child page under the main Analysis navigation.
2. Make waveform the first visible evidence panel.
3. Add a real, synchronized Stage_Code strip and spectrogram evidence layer tied to the same `windowStartSec`.
4. Remove current-scope video unavailable panel entirely.
5. Make the bottom timeline draggable/clickable.
6. Group buttons by task: navigation, display, correction, publish.
7. Do not show duplicate time/progress readouts in multiple places.
8. Disable controls with clear state reasons instead of leaving non-working buttons visible.
9. Save corrections as review actions/revisions, not direct mutation of source analysis artifacts.
10. Publish corrected results to the main Results module.

P1 recommendations:

1. Add server-authoritative staging session routes.
2. Add spectrogram tile/window API.
3. Add sleep staging child page using the same workbench shell.
4. Add long-record performance tests for chunk API and spectrogram API.
5. Add export package for review revision, source model output, and action log.

## 17. E2E Test Requirements Derived From PC Source

Minimum Web E2E coverage:

1. Data preparation confirmed -> Analysis page -> enter epilepsy/sleep child page.
2. Child page initially shows waveform before algorithm result is available.
3. Run algorithm -> task completes -> stage strip/hypnogram appears.
4. Waveform, spectrogram, and Stage_Code share the same visible time range.
5. Slider drag changes all panels together.
6. Previous/next page changes by one page.
7. Left/right or small-step control changes by one epoch or defined small step.
8. Go to epoch centers the selected epoch.
9. Click epoch selects one epoch.
10. Drag selects a range.
11. Ctrl/Shift multi-select behavior is either implemented or intentionally not exposed.
12. Stage edit writes a UI draft/review action.
13. Undo restores old Stage_Code.
14. Redo reapplies new Stage_Code.
15. Publish creates a Results-visible review artifact.
16. Source analysis output remains read-only.
17. Non-medical wording remains within research-support scope.
18. No video panel appears when no synchronized video exists.
19. No duplicate time/progress information appears in the same visual region.
20. Disabled controls have deterministic reason and testable state.

## 18. Final Judgment

The PC sleep module provides a strong interaction model for Web migration:

- synchronized evidence panels;
- epoch/page navigation;
- direct manual correction;
- undo/redo command history;
- time-frequency evidence tied to the same x-axis;
- exportable review outputs.

The Web version should not copy the PC interface literally. It should preserve the workflow logic while modernizing state ownership, control grouping, visual hierarchy, persistence, and E2E evidence.

Most important migration principle:

```text
one timeline state, many synchronized evidence panels, immutable source output, editable review revision, publish to Results
```

