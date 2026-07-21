# QLanalyser Epilepsy/Sleep Waveform Staging Child Pages - Requirements

Date: 2026-06-28  
Status: P0 design package for implementation  
Scope: Epilepsy-like event waveform staging and sleep staging as QLanalyser main-system child pages  
Sources: owner correction, Claude 4.8 opus review, Codex design review, local QLanalyser design system  
Forbidden scope: router, Headroom, gateway, IPC, model route, TimeChart, PSD/BandPower mixing, medical diagnosis wording

Mandatory pre-development gate:

- `docs/product/epilepsy_sleep_staging_predev_adversarial_gate_20260628.md`

P0 implementation cannot start unless that gate is satisfied. In particular, the requirements must prevent duplicate visible facts, useless controls, unclear Browse/Correction boundaries, standalone-tool behavior, static waveform claims, and false Results publish claims.


## 1. Product Requirement

The epilepsy and sleep workbenches are active waveform staging and manual correction workbenches inside QLanalyser. They are not standalone review-only pages and not independent data-upload tools.

## 2. User Roles

- EEG researcher;
- lab engineer;
- CRO analysis operator;
- internal reviewer / QA;
- trainee in teaching mode.

## 3. Critical User Paths

1. Select project and EEG file.
2. Confirm data preparation.
3. Run epilepsy-like event or sleep staging analysis task.
4. Enter staging subview inside the QLanalyser navigation frame.
5. Verify inherited context.
6. Browse waveform.
7. Select epoch/range.
8. Apply manual correction.
9. Undo/redo/reset.
10. Save/publish corrected staged result.
11. Find output in Results.
12. Export/report.

## 4. Functional Requirements

### FR-GEN

- FR-GEN1: Child subviews must inherit project/file/task/data-preparation context while staying inside the main QLanalyser navigation frame.
- FR-GEN2: Child pages must not show primary independent upload in the inherited path.
- FR-GEN3: Waveform must be interactive, not a static image.
- FR-GEN4: Browse mode must not write corrections.
- FR-GEN5: Correction mode must create auditable actions.
- FR-GEN6: Results must appear in the main Results module after publish.

### FR-EPI

- FR-EPI1: Display Stage_Code / Normal / Seizure-like state strip.
- FR-EPI2: Display candidate events and waveform evidence.
- FR-EPI3: Allow single epoch and range correction to Seizure-like / Normal.
- FR-EPI4: Support Undo/Redo/Reset/Save.
- FR-EPI5: Preserve source predictions as immutable.

### FR-SLEEP

- FR-SL1: Display 30s sleep epochs.
- FR-SL2: Display EEG/EOG/EMG waveform panes.
- FR-SL3: Display hypnogram linked to selected epoch.
- FR-SL4: Allow Wake/N1/N2/N3/REM/Artifact/Unknown correction.
- FR-SL5: Support batch correction and Undo/Redo/Save.

## 5. Non-Functional Requirements

- Event select feedback P95 < 100 ms on cached data.
- Waveform redraw P95 < 100 ms on cached data.
- Cache miss must show pane-level loading, not blank page.
- 10k epoch overview must not create one DOM element per epoch.
- No raw EEG, local absolute path, key, or PHI in telemetry/export logs.
- Keyboard route for critical actions.
- Visible focus ring.
- Non-color stage encoding.

## 6. Copy and Boundary Requirements

Allowed wording:

- `癫痫样事件筛查`
- `候选事件`
- `分期 / 标注 / 人工矫正`
- `科研筛查支持`
- `睡眠分期`

Forbidden positive claims:

- diagnosis / 确诊;
- treatment / 治疗建议;
- triage / 分诊;
- clinical decision / 临床决策;
- confirmed epilepsy / 癫痫确诊.

## 7. P0 Acceptance Requirements

P0 does not need full publish-results implementation, but must prove:

- inherited child page entry works;
- context header shows project/file/plan revision/task;
- primary upload path hidden in embed mode;
- waveform page loads from task;
- task payload contains data preparation plan fields;
- Results page has a clear placeholder/contract for future publish, without overclaiming.

## 8. Anti-Regression Requirements From Owner Corrections

The following requirements are mandatory because the owner repeatedly identified these failures in the WaveformWorkbench and Data Preparation surfaces.

### FR-UX1 Information Is Not Repeated

The UI must not repeat the same time range, file name, task state, plan state, or next step in multiple visible regions. If repetition is necessary for accessibility or responsive layout, one copy must be marked as secondary and must not compete with the primary action.

Acceptance:

- no duplicate progress bar/time slider pair for the same navigation task;
- no duplicated upload/select data controls in inherited child pages;
- no repeated "running/completed" state cards that disagree with each other;
- no developer/cache/debug status in customer default mode.

### FR-UX2 Buttons Must Have a State Machine

Every control must define:

```text
visible_when
enabled_when
disabled_reason
click_result
success_state
failure_state
undo_or_recovery_if_applicable
```

Controls that are visible but cannot succeed are blocked unless they show a clear disabled reason.

### FR-UX3 Workflow Logic Must Be One Directional

The intended customer path is:

```text
Data Preparation -> Analysis Task -> Staging Subview in Main Navigation Frame -> Results -> Report
```

The child subview must not pull the user backward into upload/project setup. Recovery should happen through the existing main navigation frame, Analysis/Data Preparation view switch, or an inline fix action inside the same app shell; it must not rely on a standalone return-page pattern.

### FR-UX4 No Static Waveform Claim

If a page is called a waveform staging workbench, it must provide interactive pan/zoom/epoch selection or clearly label the view as an unavailable/loading/error state. A static preview image cannot satisfy this requirement.

### FR-UX5 Sleep Must Not Be Over-Promised

Until sleep task, stage schema, hypnogram, correction commands, and Results card exist, customer-facing copy may describe sleep staging as planned/P2 or internal preview only. It must not be included in release-ready claims.

### FR-UX6 Explicit Mode Boundary

The staging workbench must always expose the current interaction mode with both visual state and text label.

Default mode: `Browse`.

Mode rules:

| Mode | User intent | Left click/drag | Wheel | Writes correction? | Primary visible controls |
| --- | --- | --- | --- | --- | --- |
| Browse | read waveform | select cursor or pan only | pan/zoom | no | navigation, zoom, channel/gain |
| Select Epoch/Range | choose target | select epoch/range | pan/zoom | no | clear selection, enter correction |
| Correction | apply label/stage | apply selected stage only after explicit command | pan/zoom | yes, auditable | stage palette, undo/redo/save |
| Inspect | read details | show tooltip/detail | pan/zoom | no | event/epoch details |

The UI must not rely on color alone to show mode. Mode change must update toolbar, cursor, status, and disabled reasons.

### FR-UX7 Direct URL / Non-Embed Behavior

If `epilepsy-workbench.html` or a future sleep workbench is opened without inherited context (`embed=1`, task id, and data preparation contract), the page must not act as a primary standalone upload tool in customer mode.

It must also not present itself as a separate product page. If a direct URL is supported, it should render a controlled state inside the QLanalyser navigation frame and guide the user to open the workbench from Analysis.

Allowed behavior:

- show blocked inherited-context state;
- explain that data must come from Data Preparation;
- provide one action back to the main app Data Preparation/Analysis Tasks path;
- optionally expose lab/developer fixture mode only behind explicit lab parameter.

### FR-UX8 No-Source and Save-Failure States

The workbench must define customer-readable states for:

- no source predictions/artifacts after task completion;
- task still running;
- waveform chunk loading;
- waveform stale/partial;
- save failed but draft retained;
- publish failed but saved session retained;
- stale data preparation revision.

Each state must include impact and recovery action.

## 9. Pre-Development Blockers

The following are release-blocking requirement failures:

- a visible control lacks a control-state matrix row;
- the same time navigation appears as both a timeline and an equivalent progress bar;
- project/file/plan/task status appears in two competing primary surfaces;
- a child page reached from the main app asks the user to upload or choose lab data as the primary path;
- direct customer URL opens a full standalone workbench instead of a controlled inherited-context state;
- waveform interaction is not demonstrable by pan, zoom, selection, or keyboard evidence;
- corrected/staged outputs are implied to be in Results before registered artifacts exist;
- sleep staging is presented as release-ready before real task/schema/UI/session/Results/E2E evidence exists.
