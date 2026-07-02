# QLanalyser Waveform Scoring Workbench Detailed Design

Date: 20260629
Status: baseline detailed design
Scope: UI/interaction/backend flow for unified scoring workbench

## 1. Sources


Sources used:
- `docs/product/qlanalyser_waveform_scoring_workbench_research_input_20260629.md`
- `docs/product/qlanalyser_pc_sleep_module_source_review_20260629.md`
- `docs/product/waveform_scoring_workbench_unified_design_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_requirements_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_architecture_20260629.md`

Sources partially read / controlled:
- Feishu PSG/sleep reference `https://quanland.feishu.cn/wiki/UevhwictEiaiOFk9tBCcatqqnge?from=from_copylink` was partially readable from the internal wiki on 2026-06-29. Status: `partial_read_from_feishu_aasm_v3_reference`; chapter-level scope, event-layer architecture, and contract categories are incorporated. Exact rule thresholds and full translated rule text remain controlled internal reference pending full QA review.


## 2. Page Placement

The workbench is embedded under the main QLanalyser Analysis page.

Entry flow:

```text
Data Preparation confirmed
-> Analysis page
-> select Epilepsy Event Review / Sleep Staging / PSG Event Scoring / Animal Preclinical profile
-> open EmbeddedScoringWorkbench
```

No standalone return button is needed because the global navigation shell owns navigation.

## 3. Page Information Architecture

Desktop layout:

```text
Global navigation shell
  Analysis context header
  Workbench status/context strip
  Evidence toolbar
  Waveform viewport
  Spectrogram / auxiliary evidence panel
  Stage strip / event strip stack
  Main table: candidate events or stage epochs
  Right panel: current selection + correction actions + history + publish
```

Customer clean mode should hide developer-only task IDs unless expanded.

## 4. Workbench Context Header

Shows:

- dataset name;
- data preparation plan and revision;
- domain/profile;
- channel count and visible channels;
- source algorithm status;
- review revision status;
- non-medical research-support notice.

Avoid duplicate time/progress text. One canonical timeline control owns time navigation.

## 5. Timeline Controller

Inputs:

- wheel pan;
- ctrl/cmd wheel zoom;
- page previous/next;
- left/right small movement;
- slider drag/click;
- event/epoch click;
- go-to time/epoch.

State update sequence:

```text
user action -> update TimelineState -> request needed chunks/tiles -> render all panels -> update selection/context
```

Old/stale async responses must not override newer state.

## 6. Channel Manager UI

Required controls:

- visible channel selector;
- channel group selector;
- channel role badges;
- per-channel gain or global gain;
- bad-channel display;
- event-related channel highlight.

For 1-64 channels:

- default to a useful subset, not all channels if too dense;
- provide search/filter;
- use grouped display and virtualized rendering in later performance phases.

## 7. Evidence Panels

### 7.1 Waveform Panel

- Primary evidence.
- Must appear before algorithm completion when file data is available.
- Uses waveform chunk API.
- Displays loading/stale/ready explicitly.
- Never remaps old payload to a new time axis.

### 7.2 Spectrogram Panel

- Review evidence synchronized to waveform.
- Uses spectrogram-window/tile API when available.
- P0 can display deterministic review evidence only if clearly labeled and not represented as formal TFR output.

### 7.3 Stage Strip

Used for epoch labels:

- sleep stage labels;
- epilepsy Stage_Code-style review intervals when applicable;
- artifact/unscored markers.

### 7.4 Event Strip

Used for interval events:

- epilepsy candidate events;
- PSG respiratory/arousal/movement/oxygen events;
- animal seizure intervals;
- artifact intervals.

Multiple event strips may stack vertically.

## 8. Domain-Specific Panels

### Epilepsy Event Review

Actions:

- open candidate;
- confirm candidate;
- reject false positive;
- mark artifact;
- adjust onset/offset;
- add missed event;
- add note;
- Undo/Redo;
- publish reviewed events.

### Sleep Staging

Actions:

- select epoch/range;
- assign stage label;
- mark artifact/unscored;
- Undo/Redo;
- show stage statistics;
- publish hypnogram and stage table.

### Human PSG Event Scoring Foundation

Actions planned after spec incorporation:

- add/edit respiratory interval event;
- add/edit arousal interval event;
- add/edit oxygen desaturation event;
- attach event to channel roles;
- compute PSG summaries where validated.

### Animal / CRO Study Panel

Shows:

- study_id;
- protocol_id;
- animal_id;
- species/strain/sex/group/treatment;
- light/dark cycle;
- scoring profile;
- review lock status.

## 9. Manual Correction UX

Correction panel structure:

```text
Current selection
  selected event/epoch/range
Suggested actions
  domain-specific buttons
Reason/comment
  required in GLP-ready modes
Action history
  latest actions, undo, redo
Publish
  save draft, lock/sign later phase, publish Results
```

Rules:

- Buttons disabled when no valid target exists.
- Disabled state must have deterministic reason.
- New edit clears redo stack.
- All edits show source output vs review value.

## 10. Review States

```text
no_source_output
source_ready
review_draft
review_saved
under_review
locked
published
archived
```

P0 may implement subset:

```text
source_ready -> review_draft -> review_saved -> published
```

CRO/GLP-ready phases add `under_review`, `locked`, `signed`, `archived`.

## 11. Backend Flow

### P0 Epilepsy

```text
open workbench
-> load waveform chunk
-> create/run epilepsy task if requested
-> load source candidate events
-> create review draft in UI or lightweight session
-> save review revision
-> publish Results artifact
```

### P1 Sleep

```text
select sleep profile
-> load waveform/channel roles
-> run sleep staging task
-> load hypnogram/source stage table
-> review/edit epochs
-> publish Results artifact
```

### P2 PSG

```text
load PSG channel role schema
-> load stage/event layers
-> edit interval events
-> compute validated summaries
-> publish PSG review artifact
```


P2 PSG UI behavior:

- Left/evidence area keeps waveform as the primary evidence.
- Stage strip remains an epoch strip only.
- Event strip stack separates arousal, respiratory, movement, cardiac, oxygen, position/snore, and HSAT layers.
- Right panel switches by selected item type: epoch selection edits stage labels; respiratory interval edits type/duration/effort/flow/desaturation/arousal evidence; arousal interval links evidence and associated events; movement/cardiac/oxygen intervals expose their own category fields.
- Rule text is summarized as profile metadata; exact internal rule wording is not copied into customer-facing UI.
- HSAT profile hides PSG-only controls that require unavailable channels and uses HSAT-specific report parameters.

## 12. Error And Empty States

Must handle:

- no data preparation plan;
- no waveform chunk available;
- algorithm task failed;
- source output missing;
- no candidates found;
- no visible channels;
- unsupported profile;
- unauthorized GLP action;
- locked revision cannot be edited;
- PSG rule detail not authorized for the selected profile;
- missing channels required by the selected PSG/HSAT profile.

## 13. Non-Medical Wording

Use:

- candidate event;
- automated screening;
- research support;
- manual review;
- reviewed event list.

Avoid:

- diagnosis;
- confirmed clinical seizure;
- clinical recommendation;
- treatment suggestion.

## 14. Change Log

- 2026-06-29: Created detailed design baseline.

- 2026-06-29: Incorporated partial Feishu AASM V3 PSG/HSAT source at UI behavior level; separated epoch stage actions from PSG interval event categories.

<!-- 20260629_PREVIEW_MIGRATION_BEGIN -->
## 2026-06-29 Detailed Design Amendment: Epilepsy Reader Control Surface

Status: accepted detailed-design amendment.

### Target layout

The epilepsy workbench should present the waveform reader as the first working area:

```text
Context header
Reader toolbar
  Browse: prev / next / go-to / overview drag
  Display: uV/row / channel group / raw-filter-prepared / event density
  Overlays: candidate events / Stage_Code / review edits / spectrogram
Waveform canvas
Overview strip
Stage_Code strip
Spectrogram panel
Candidate event list
Right correction panel
```

### Required migrated interactions

| Interaction | Expected behavior |
| --- | --- |
| Wheel | horizontal pan, not zoom |
| Ctrl/Cmd + wheel | time zoom around pointer |
| PageUp/PageDown | previous/next page |
| Left/Right | 1/10 page movement |
| Middle-button drag | horizontal pan |
| +/- | amplitude sensitivity |
| Ctrl/Cmd +/- | time zoom |
| Overview click/drag | jump current window |
| Candidate previous/next | select and center event |
| Stage_Code click | select corresponding event/epoch |
| Correction click | write review draft only |

### Required status model

Only one canonical reader status should be visible:

```text
window start-end | s/page | visible channels | uV/row | Raw/Filter/Prepared | source output status | review draft status
```

Avoid repeating the same time range in a title, badge, toolbar, and progress bar. The overview strip can show position visually; the status text can show exact values.

### Required overlay model

Overlays are separate layers:

- waveform source signal;
- candidate events;
- Stage_Code / epoch labels;
- review edits;
- artifact / excluded interval;
- spectrogram selection marker.

Each overlay must be toggleable or visually quiet enough not to obscure the waveform.

### Required empty/loading/stale behavior

- No algorithm task yet: waveform still loads; overlays say "not run yet".
- Running: waveform remains usable; candidate layers show loading.
- Stale viewport request: old waveform may remain only as stale/greyed state, never remapped to the new time axis.
- No candidates: show "no candidates found" as an algorithm result, not as missing waveform.

### Teaching mode behavior

Teaching mode must keep using the epilepsy-specific fixture for this workbench and must show a short local boundary message. Teaching overlays and guide chrome must not block core reader controls during E2E acceptance.


## 2026-06-29 Adversarial Review: Preview Migration Gap

Round 1 - Product truth:
Finding: The phrase "original waveform review window" implies professional browsing controls. Current implementation proves visibility, not full reviewing capability.
Decision: Accepted. P0 scope must require reader-control migration.

Round 2 - Information architecture:
Finding: Time window, scale, and progress can become repeated badges instead of one navigable timeline.
Decision: Accepted. One overview/timeline controller must own navigation.

Round 3 - Interaction state:
Finding: Algorithm overlays can accidentally become the main driver of viewport state.
Decision: Accepted. Source waveform reader owns viewport; algorithm output is overlay.

Round 4 - User workflow:
Finding: Epilepsy review needs previous/next candidate and center-on-event. Otherwise reviewers must manually hunt through the trace.
Decision: Accepted. Candidate navigation is P0b.

Round 5 - Release risk:
Finding: Teaching chain passes, but release wording could overclaim if reader migration is not complete.
Decision: Accepted. Release plan now separates P0a internal candidate from P0b release-candidate reader migration.
<!-- 20260629_PREVIEW_MIGRATION_END -->

<!-- 20260629_P0B_READER_IMPLEMENTATION_ACCEPTANCE_BEGIN -->
## 2026-06-29 P0b Reader Implementation Acceptance

Implemented interaction details:
- Reader toolbar groups controls into browse, candidate navigation, display, and overlays.
- Overview strip is draggable and shows current window, candidate events, and review marks.
- Canvas receives focus for keyboard operation.
- Mouse wheel pans; Ctrl/Cmd wheel zooms around the pointer anchor; PageUp/PageDown page; ArrowLeft/ArrowRight move by 1/10 page; +/- changes uV/row unless Ctrl/Cmd is held.
- Candidate list, Stage_Code cells, and prev/next candidate controls explicitly select and center the event.
- Overlay toggles affect candidate, Stage_Code, and review-edit visibility state without touching review draft data.

Design review result:
- Accepted P0/P1: waveform is the primary first-screen task; duplicate time-scale controls were centralized into the waveform reader; spectrogram is now a follower panel.
- Remaining P2: toolbar density can be further refined after more real-user screenshots, but it is not a blocker for internal trial.
<!-- 20260629_P0B_READER_IMPLEMENTATION_ACCEPTANCE_END -->

## 2026-06-30 P0 Addendum: Epilepsy STFT Rendering Detail

Backend design:
- Select the same EEG channel used by epilepsy ML.
- Compute STFT using PC-compatible parameters: 4 s window, 90% overlap, `boundary="zeros"`.
- Convert to display power with `10*log10(abs(Zxx)+1e-10)`.
- Keep frequencies 0.5-50 Hz and write 10/99 percentile display bounds.
- For long records, the artifact may retain a bounded number of time bins for display, but the computation parameters and source compatibility metadata must remain explicit.

Frontend design:
- Load `epilepsy_ml_spectrogram` alongside epoch predictions and candidate events.
- Draw only the current waveform reader window from `times_sec` / `power_db`.
- If the artifact is missing, show a waiting state that asks the user to run screening; do not draw a misleading temporary spectrogram as if it were the analysis result.
- Canvas source marker: `epilepsy_ml_spectrogram_artifact_pc_stft`.

## 2026-06-30 Detailed Design Addendum: Results Image Preview

Status: accepted detailed design amendment.

Backend design:
- Generate `figures/epilepsy_ml_event_timeline.svg` from epoch predictions and candidate events.
- Generate `figures/epilepsy_ml_spectrogram_preview.svg` from the PC-compatible STFT payload.
- Add both SVG paths to the analysis output contract and task workflow template.
- Include non-medical research boundary text inside each SVG.

Frontend design:
- Detect image artifacts by MIME type or image file extension.
- Render image artifacts in a compact Results image preview grid before the technical artifact list.
- Each image card must link to the artifact download URL and keep the source artifact label visible.
- The Results image preview must not replace the CSV/JSON provenance list; it is a readable front layer over the same artifact contract.
