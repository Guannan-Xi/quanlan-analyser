# QLanalyser Waveform Scoring Workbench E2E Test Plan

Date: 20260629
Status: baseline E2E and acceptance plan
Scope: tests for unified waveform scoring workbench and staged releases

## 1. Sources


Sources used:
- `docs/product/qlanalyser_waveform_scoring_workbench_research_input_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_requirements_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_architecture_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_detailed_design_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_data_api_contract_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_aasm_v3_feishu_source_extract_20260629.md`

Sources partially read / controlled:
- Feishu PSG/sleep reference `https://quanland.feishu.cn/wiki/UevhwictEiaiOFk9tBCcatqqnge?from=from_copylink` was partially readable from the internal wiki on 2026-06-29. Status: `partial_read_from_feishu_aasm_v3_reference`; chapter-level scope, event-layer architecture, and contract categories are incorporated. Exact rule thresholds and full translated rule text remain controlled internal reference pending full QA review.


## 2. Test Strategy

Testing must prove the business chain, not merely button existence:

```text
Data Preparation -> Analysis Task -> Workbench Evidence -> Manual Correction -> Review Revision -> Results
```

Each requirement must have at least one of:

- static contract validator;
- API smoke/integration test;
- browser E2E test;
- visual regression evidence;
- performance benchmark;
- manual acceptance checklist with evidence path.

## 3. Static Contract Tests

### C-001 Six-pack presence

Verify required six documents exist and are UTF-8 readable.

### C-002 Contract references

Verify requirements, architecture, detailed design, data/API contract, E2E test plan, and release plan reference the same module name and the partial Feishu AASM V3 PSG/HSAT incorporation status.

### C-003 Non-medical wording

Scan UI/docs intended for users for forbidden phrases:

- diagnosis;
- confirmed clinical seizure;
- treatment advice;
- clinical triage.

Allowed wording:

- candidate event;
- research support;
- manual review;
- reviewed results.

### C-004 Source/review immutability

Verify contract declares raw/source outputs immutable and manual correction as review revision.

## 4. API Tests

### API-001 Waveform chunk

- Request a valid file window.
- Assert response has start/duration/channel/data fields.
- Assert repeated pan uses request sequence or equivalent stale-response guard.

### API-002 Spectrogram window

- Request a valid spectrogram review window.
- Assert method, freqs, times, power, vmin/vmax, review_only.
- If endpoint not implemented, mark P1/P2 pending with explicit skip reason.

### API-003 Scoring session

- Create session from source task.
- Add review action.
- Undo action.
- Redo action.
- Save review revision.
- Publish Results.

### API-004 Study/GLP-ready metadata

For CRO/GLP phases:

- create study;
- bind protocol;
- bind animal metadata;
- add audit action;
- lock/sign/archive where implemented.

## 5. Browser E2E: P0 Epilepsy

### EPI-001 Entry inherits Data Preparation

- Confirm data preparation.
- Enter Analysis page.
- Open epilepsy workbench inside main navigation frame.
- Assert no standalone mini-app / return-main-app flow.

### EPI-002 Waveform first

- Enter workbench before algorithm completion.
- Assert waveform canvas is visible and not static placeholder.

### EPI-003 Start automatic screening

- Click start screening.
- Backend task completes or deterministic fixture returns candidates.
- Candidate event list appears.

### EPI-004 Synchronized candidate selection

- Click candidate event.
- Assert waveform window, spectrogram window, event strip, and details panel share selected time range.

### EPI-005 Manual correction

- Confirm event.
- Reject another event.
- Mark artifact.
- Adjust onset/offset.
- Add note/reason.
- Assert ReviewAction list updates.

### EPI-006 Undo/Redo

- Undo last event edit.
- Assert prior label/time restored.
- Redo.
- Assert edit reapplied.

### EPI-007 Publish Results

- Save review revision.
- Publish to Results.
- Open Results page.
- Assert reviewed event table and source provenance are visible.

## 6. Browser E2E: P1 Sleep Staging

### SLP-001 Profile selection

- Select sleep staging profile.
- Assert stage schema and epoch length are visible.

### SLP-002 Hypnogram and waveform sync

- Load source stages.
- Click epoch.
- Assert waveform, spectrogram, and hypnogram highlight same epoch.

### SLP-003 Stage edit

- Select epoch/range.
- Assign Wake/NREM/REM or configured label.
- Assert review draft changes only review layer.

### SLP-004 Statistics update

- Save stage edits.
- Assert stage duration/count summary updates.

### SLP-005 Publish sleep results

- Publish review revision.
- Results page shows hypnogram/stage table/provenance.

## 7. Browser E2E: P2 Human PSG Foundation

### PSG-001 Channel roles

- Load profile with EEG/EOG/EMG/SpO2/airflow roles.
- Assert channel roles display correctly.

### PSG-002 Interval event layer

- Add respiratory-like interval event in test profile.
- Assert it renders as interval, not stage label.

### PSG-003 Multiple event layers

- Add arousal/movement/oxygen test events.
- Assert layers do not collapse into Stage_Code.

### PSG-004 Event category visibility

- Load PSG profile.
- Assert stage, arousal, respiratory, movement, cardiac, oxygen, and HSAT/auxiliary layers have separate controls or clearly disabled unavailable states.

### PSG-005 Respiratory interval is not a stage

- Add or load respiratory event.
- Assert it has start/end/duration and renders on respiratory layer, not as an epoch stage label.

### PSG-006 Arousal event

- Add or load arousal event.
- Assert waveform selection, details panel, and associated respiratory/movement links update together.

### PSG-007 Movement and cardiac events

- Add or load movement and cardiac events.
- Assert each appears in its own event layer and details panel category.

### PSG-008 Rule grade display

- Load rule metadata.
- Assert `RECOMMENDED`, `ACCEPTABLE`, `OPTIONAL`, or `INTERNAL_PROFILE` displays in the profile/rule metadata area without copying controlled rule text.

### PSG-009 Report parameter output

- Generate a PSG foundation report fixture.
- Assert report parameters reference source layers and rule metadata.

Full PSG clinical scoring acceptance requires full internal AASM V3 rule-level extraction, QA review, and authorized citation handling.

## 8. Browser E2E: Animal / CRO

### CRO-001 Animal metadata

- Create/open animal study context.
- Assert animal_id, species, group, treatment visible.

### CRO-002 Epilepsy severity profile

- Use rodent epilepsy profile.
- Assign severity/Racine-like score if profile supports it.
- Assert event-level summary includes severity.

### CRO-003 Audit trail

- Make edit with reason.
- Assert audit log includes user, timestamp, before, after, reason, software/model/profile refs.

### CRO-004 Lock behavior

- Lock review revision in GLP-ready phase.
- Assert edits are blocked unless new amendment/revision is created.

## 9. Performance Tests

### PERF-001 Initial waveform

Target: visible waveform under 2 seconds on teaching/demo fixture.

### PERF-002 Cached pan

Target: cached pan under 50 ms.

### PERF-003 New chunk pan

Target: new waveform chunk under 500 ms when local backend/cache is healthy.

### PERF-004 Spectrogram window

Target: spectrogram review window under 1 second after warm-up.

### PERF-005 64-channel stress

P4 test:

- load 64-channel fixture;
- render default visible subset;
- switch channel groups;
- assert UI remains responsive and no horizontal overflow.

## 10. Visual Regression

Required viewports:

- 1440 desktop;
- 1280 laptop;
- 390 mobile/narrow read-only view.

Screenshots:

- initial entry;
- loading waveform;
- source output ready;
- event selected;
- correction draft;
- Results published;
- locked/GLP-ready view when implemented.

## 11. Release Gates

P0 can pass without P2/P3/P4 tests if they are marked pending by release plan.

External release cannot claim:

- full human PSG rule-level scoring until Feishu/internal AASM V3 rules are fully extracted, QA-reviewed, and tests pass;
- any-animal validated algorithms until species-specific validation evidence exists;
- GLP compliance until validation package, SOPs, roles, audit trail, and controlled deployment are verified.

## 12. Traceability Matrix

| Requirement | Test IDs |
| --- | --- |
| Waveform-first child page | EPI-001, EPI-002 |
| Candidate event review | EPI-003 to EPI-007 |
| Sleep staging | SLP-001 to SLP-005 |
| PSG interval events | PSG-001 to PSG-009 |
| CRO/GLP audit | CRO-001 to CRO-004 |
| 1-64 channels | PSG-001, PERF-005 |
| Non-medical wording | C-003 |
| Results publication | EPI-007, SLP-005 |

## 13. Change Log

- 2026-06-29: Created baseline E2E test plan.

- 2026-06-29: Incorporated partial Feishu AASM V3 PSG/HSAT source into E2E categories; expanded PSG-004 to PSG-009.

<!-- 20260629_PREVIEW_MIGRATION_BEGIN -->
## 2026-06-29 E2E Amendment: Preview Workbench Migration Tests

Status: accepted E2E amendment.

Add the following tests before P0 epilepsy workbench is considered release-ready.

### EPI-RDR-001 Waveform reader controls exist and are visible

- Enter teaching epilepsy workbench.
- Assert waveform is visible before screening.
- Assert toolbar has Browse / Display / Overlays / Review or equivalent grouped controls.
- Assert no duplicate primary time/progress controls compete with the overview strip.

### EPI-RDR-002 Wheel and keyboard navigation

- Wheel pans horizontally.
- Ctrl/Cmd + wheel zooms around pointer.
- PageUp/PageDown moves one page.
- Left/Right moves 1/10 page.
- +/- changes uV/row.
- Ctrl/Cmd +/- changes time window.

### EPI-RDR-003 Overview drag

- Drag overview window to a later time.
- Assert waveform, Stage_Code, spectrogram, candidate list highlight, and status all use the same new time window.

### EPI-RDR-004 Candidate navigation

- Run screening.
- Click next candidate.
- Assert selected candidate is centered or visible in waveform.
- Assert Stage_Code and spectrogram markers update.
- Click previous candidate and assert same synchronization.

### EPI-RDR-005 Overlay toggles

- Toggle candidate event overlay off/on.
- Toggle Stage_Code layer off/on.
- Toggle review edits layer off/on.
- Assert source waveform remains visible and unchanged.

### EPI-RDR-006 Stale request guard

- Rapidly pan/zoom several times.
- Mock delayed older waveform response.
- Assert final rendered waveform matches the latest request key/window, not the delayed old response.

### EPI-RDR-007 Review command integrity

- Select candidate.
- Mark Normal / Artifact / Needs review.
- Undo and redo.
- Assert source algorithm output remains unchanged.
- Assert review draft and action log change.
- Publish and assert Results receives reviewed artifacts only after save/export.

### EPI-RDR-008 Teaching protection

- Start from real Teaching Mode button.
- Assert epilepsy workbench uses `proj_demo_epilepsy_lab` and `eeg_demo_epilepsy_high_amplitude`.
- Assert upload/rename/delete are blocked for protected teaching data.
- Assert teaching guide overlay does not block reader controls during acceptance flow.

### Updated P0 exit criterion

P0 Epilepsy is not complete until EPI-001 to EPI-007 and EPI-RDR-001 to EPI-RDR-008 pass or have explicit owner-approved deferral.


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
## 2026-06-29 P0b Reader E2E Acceptance

Executed tests:
- `node --check frontend/app.js`: passed.
- `node --check scripts/e2e_main_epilepsy_entry_contract.mjs`: passed.
- `node scripts/e2e_main_epilepsy_entry_contract.mjs`: passed.
- `node scripts/validate_epilepsy_child_page_p0_contract.mjs`: passed.
- `node scripts/e2e_epilepsy_child_page_p0.mjs`: passed.

New/strengthened checks:
- `reader_toolbar_visible`
- `reader_overview_strip_visible`
- `reader_wheel_pan_changes_window`
- `reader_ctrl_wheel_zoom_changes_duration`
- `reader_keyboard_arrow_changes_window`
- `reader_gain_button_changes_uv_per_row`
- `reader_overview_drag_changes_window`
- `reader_candidate_next_selects_and_centers`
- `reader_overlay_toggle_hides_candidate_layer`
- `reader_browse_controls_do_not_write_review_draft`

Evidence paths:
- `work/release_evidence/20260628-main-epilepsy-entry-contract/main_epilepsy_entry_contract.json`
- `work/release_evidence/20260628-main-epilepsy-entry-contract/03_main_to_epilepsy_child_page.png`
- `work/release_evidence/20260628-main-epilepsy-entry-contract/04_synchronized_spectrogram_300s.png`
<!-- 20260629_P0B_READER_IMPLEMENTATION_ACCEPTANCE_END -->

## 2026-06-30 P0 Addendum: Epilepsy STFT E2E Assertions

Add to epilepsy cloud trial and local fixture tests:
- Run `epilepsy_ml_xgboost` on the synthetic labeled EDF.
- Assert artifacts include `epilepsy_ml_spectrogram`.
- Download `data/epilepsy_ml_spectrogram.json`.
- Assert schema version `qlanalyser-epilepsy-ml-spectrogram-v0.1`.
- Assert source reference includes `EpilepsyAnalysis2.py::calculate_spectrogram`.
- Assert method `scipy.signal.stft`.
- Assert parameters: `window_sec=4.0`, `overlap_ratio=0.9`, `freq_min_hz=0.5`, `freq_max_hz=50.0`, `power_transform="10*log10(abs(Zxx)+1e-10)"`.
- Assert the frontend spectrogram canvas uses `data-source="epilepsy_ml_spectrogram_artifact_pc_stft"` after screening.
- Assert no customer-facing copy claims this review evidence is a formal TFR/PSD/Band Power result.

## 2026-06-30 P0 E2E Addendum: Result Image Artifacts

Add to local fixture, cloud upload, and Results browser E2E:

- Run `epilepsy_ml_xgboost` on the synthetic labeled EDF.
- Assert outputs include `epilepsy_ml_event_timeline_figure` and `epilepsy_ml_spectrogram_figure`.
- Assert files exist, are non-empty SVGs, and contain:
  - `癫痫样候选事件初筛时间轴`;
  - `癫痫样事件初筛时频证据图`;
  - visible research/non-diagnostic boundary wording.
- Assert task artifacts register both SVGs with `image/svg+xml` or image-compatible metadata.
- Open Results page and assert `[data-testid="result-image-preview-grid"]` contains image previews for the epilepsy screening task.
