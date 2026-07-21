# Waveform Scoring Workbench Unified Design

Date: 2026-06-29
Status: design draft after QLanalyser-PC sleep module source review
Applies to: embedded epilepsy-like event workbench and future sleep staging workbench
Non-medical boundary: research analysis support only; no diagnosis or treatment recommendation

## 1. Product Goal

Create one reusable embedded workbench for EEG scoring workflows.

The workbench is a child page inside the main QLanalyser navigation frame. It is not a standalone upload page and not a separate mini-app.

Workflow:

```text
Data Preparation
-> Analysis Task
-> Embedded Scoring Workbench
-> Manual Correction / Review Revision
-> Results
```

The user should enter the workbench and immediately see waveform evidence. Algorithm results, Stage_Code, hypnogram, candidate events, and manual correction are layered onto the same time base.

## 2. Domains

The first two domains share the same shell:

| Domain | Purpose | Primary output |
| --- | --- | --- |
| epilepsy | epilepsy-like candidate event screening and manual correction | candidate event table + Stage_Code/review revision |
| sleep_staging | sleep stage scoring and manual correction | hypnogram + stage statistics + review revision |

Shared shell, different labels:

```text
ScoringWorkbench(domain)
  Evidence timeline
  Waveform
  Spectrogram
  Stage strip / hypnogram
  Candidate or stage table
  Correction command panel
  Results publish panel
```

## 3. Source Of Truth

The workbench has one canonical timeline state.

```json
{
  "domain": "epilepsy | sleep_staging",
  "file_id": "eeg_xxx",
  "analysis_task_id": "task_xxx",
  "data_preparation_plan_id": "prep_xxx",
  "data_preparation_revision": 1,
  "data_preparation_contract_version": "qlanalyser-data-preparation-v0.2",
  "window_start_sec": 0,
  "window_duration_sec": 30,
  "epoch_length_sec": 4,
  "selected_epoch_indices": [],
  "selected_event_id": null,
  "review_revision": 0
}
```

Rules:

- waveform, spectrogram, Stage_Code/hypnogram, event table, and correction panel all subscribe to this one state;
- no panel is allowed to keep an independent hidden time range;
- changing scale must not clear selected event or correction draft;
- source algorithm output is immutable;
- manual correction creates a review action/revision.

## 4. Layout

Desktop layout inside the main app:

```text
Main navigation shell
  Analysis page active
    Compact inherited context
    Evidence toolbar
    Waveform panel
    Spectrogram panel
    Stage strip / hypnogram
    Candidate or stage table
    Right-side correction/revision panel
```

P0 does not show a video panel unless real synchronized video exists. Empty "Video unavailable" panels are forbidden.

## 5. Evidence Toolbar

The toolbar owns global view controls. Individual panels show current state but do not duplicate controls.

Controls:

- previous page;
- next page;
- jump to epoch/time;
- window scale: 5 s / 30 s / 300 s;
- amplitude sensitivity;
- channel visibility;
- stage/spectrogram visibility toggles if needed.

Control discipline:

- no duplicate time/progress controls in the same region;
- buttons that cannot work must be disabled with deterministic reason;
- no "return to main program" button inside the child page because the global navigation already owns navigation;
- no developer-only status rows in customer mode.

## 6. Evidence Panels

### 6.1 Waveform

The waveform is the primary evidence panel.

Requirements:

- first visible panel after entering workbench;
- loaded through lightweight waveform chunk API;
- never replaced by a static image;
- stale/loading state must not pretend old data is the new window;
- x-axis must match the canonical timeline state.

### 6.2 Spectrogram

The spectrogram is review evidence, not formal TFR/PSD output.

Recommended backend contract:

```http
GET /api/eeg/files/{file_id}/spectrogram-window
  ?start_sec=0
  &duration_sec=30
  &channel=EEG3
  &freq_min=0.5
  &freq_max=50
  &mode=review
```

Recommended computation inherited from PC:

- STFT;
- `nperseg = fs * 4`;
- `noverlap = 0.9 * nperseg`;
- log power dB;
- frequency range `0.5-50 Hz`;
- color scale `10th-99th percentile`.

### 6.3 Stage Strip / Hypnogram

For epilepsy:

- show candidate/normal/needs-review intervals;
- selected event highlights the matching interval;
- editing changes only the review layer.

For sleep:

- show Wake/NREM/REM in P0;
- later expand to W/N1/N2/N3/REM/Artifact if the model contract supports it;
- sleep statistics update from the current review revision.

## 7. Manual Correction State Machine

Layers:

| Layer | Meaning | Mutability |
| --- | --- | --- |
| L0 | raw EEG | never mutable |
| L1 | data preparation plan | read-only inside workbench |
| L2 | source algorithm output | read-only |
| L3 | local review draft | editable |
| L4 | saved review revision | server-authoritative |
| L5 | published Results artifact | generated |

Correction command:

```json
{
  "action_id": "act_xxx",
  "domain": "sleep_staging",
  "target_type": "epoch_range",
  "target_indices": [10, 11, 12],
  "old_values": [2, 2, 1],
  "new_value": 3,
  "new_label": "REM",
  "source": "manual",
  "created_at": "ISO-8601"
}
```

Undo/redo:

- undo pops one command from review history and restores old values;
- redo reapplies the command;
- new edit clears redo stack;
- all commands are auditable.

## 8. Domain Labels

### 8.1 Epilepsy

Suggested P0 labels:

- Background / normal;
- Candidate event;
- Needs review;
- Artifact / exclude if needed.

Forbidden labels:

- confirmed seizure;
- diagnosis;
- treatment advice;
- clinical triage.

### 8.2 Sleep

P0 labels from PC:

- Wake;
- NREM;
- REM.

Potential P1:

- Wake;
- N1;
- N2;
- N3;
- REM;
- Artifact.

## 9. Keyboard And Mouse

Shared:

- mouse wheel: horizontal browsing;
- Ctrl/Cmd + wheel: zoom around pointer;
- slider drag/click: jump timeline;
- page previous/next: page movement;
- left/right: small movement;
- click epoch: select;
- drag across epoch strip: range select.

Sleep shortcuts:

- `Shift+1`: Wake;
- `Shift+2`: NREM;
- `Shift+3`: REM.

Epilepsy shortcuts can use the same pattern but must show domain labels clearly.

## 10. Results Output

Publish must send the corrected review revision to the main Results module.

Minimum epilepsy result:

- file id;
- preparation plan id/revision;
- source task id/workflow/model;
- source candidate count;
- corrected candidate count;
- manual edit count;
- candidate event table;
- Stage_Code strip or image;
- action log;
- non-medical research-support statement.

Minimum sleep result:

- file id;
- preparation plan id/revision;
- source task id/workflow/model;
- hypnogram;
- Wake/NREM/REM duration and percentage;
- manual edit count;
- epoch score table;
- action log;
- non-medical research-support statement.

## 11. API Direction

P0 can reuse current epilepsy API where already implemented, but target architecture should converge to:

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

Waveform and spectrogram browsing should stay separate from formal analysis task creation:

```text
GET /api/eeg/files/{file_id}/waveform/chunk
GET /api/eeg/files/{file_id}/spectrogram-window
```

## 12. Acceptance Tests

P0 E2E:

1. Confirmed data preparation is required before entering scoring workflow.
2. Enter child page inside main navigation frame.
3. Waveform appears first.
4. No static fake waveform is shown.
5. No video-unavailable panel appears when no real video exists.
6. Run analysis task from inside workbench.
7. Stage strip/hypnogram appears after task completion.
8. Spectrogram panel shares the same visible time range.
9. Slider drag/click changes waveform, spectrogram, and stage strip together.
10. Page controls move by the defined page size.
11. Epoch click selects one epoch.
12. Drag selects an epoch range.
13. Stage edit creates draft action.
14. Undo restores prior value.
15. Redo reapplies edited value.
16. Publish creates Results-visible artifact.
17. Non-medical wording is preserved.
18. Disabled buttons are deterministic and tested.
19. No duplicate time/progress controls are visible in the same section.
20. Browser console has no fatal errors.

P1 performance:

1. Initial visible waveform under 2 s for teaching/demo data.
2. Cached pan under 50 ms.
3. New waveform chunk under 500 ms.
4. Spectrogram window under 1 s after cache warm-up.
5. Rapid pan/zoom ignores stale responses.

## 13. Development Order

Recommended sequence:

1. Harden current embedded epilepsy child page against this contract.
2. Extract shared timeline state and evidence-panel rendering helpers.
3. Add/clean E2E for controls and Results publish.
4. Add server-side staging session facade.
5. Add sleep staging child page using the same shell.
6. Add spectrogram-window API.
7. Add full sleep output/statistics package.

## 14. Design Review Checklist

Before any UI polish or new control is accepted:

- Does this control belong to navigation, display, correction, or publish?
- Is the same information already shown nearby?
- Does this panel own a hidden time range?
- Does this button work in the current state?
- If disabled, is the reason clear and testable?
- Is source algorithm output kept read-only?
- Are manual changes auditable?
- Does publishing go to Results rather than a local-only file?
- Is the wording non-medical?
- Can E2E prove the behavior without manual interpretation?

