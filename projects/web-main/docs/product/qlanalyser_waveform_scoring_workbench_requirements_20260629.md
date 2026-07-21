# QLanalyser Waveform Scoring Workbench Requirements

Date: 20260629
Status: baseline PRD for architecture/design/test planning
Scope: epilepsy event review, sleep staging, human PSG event scoring foundation, animal/preclinical workflows, 1-64 channel waveform review, CRO/GLP-ready roadmap

## 1. Product Goal

Build a unified, main-system child workbench for EEG/PSG/physiology scoring workflows:

```text
Data Preparation -> Analysis Task -> Embedded Scoring Workbench -> Manual Correction / Review Revision -> Results
```

The module must not become a standalone mini-app. It must inherit confirmed Data Preparation context, display waveform evidence first, support automated candidate/stage outputs, allow manual correction without overwriting source outputs, and publish auditable review results into the QLanalyser Results module.

## 2. Sources


Sources used:
- `docs/product/qlanalyser_waveform_scoring_workbench_research_input_20260629.md`
- `docs/product/qlanalyser_pc_sleep_module_source_review_20260629.md`
- `docs/product/waveform_scoring_workbench_unified_design_20260629.md`
- Existing epilepsy/sleep staging design and E2E notes under `docs/product/`.
- QLanalyser-PC sleep module source files under `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC`.
- Public AASM/YASA/PhysioNet/ILAE/ACNS/OECD/FDA/NMPA references summarized in the research input.
- `docs/product/qlanalyser_waveform_scoring_workbench_aasm_v3_feishu_source_extract_20260629.md`

Sources partially read / controlled:
- Feishu PSG/sleep reference `https://quanland.feishu.cn/wiki/UevhwictEiaiOFk9tBCcatqqnge?from=from_copylink` was partially readable from the internal wiki on 2026-06-29. Status: `partial_read_from_feishu_aasm_v3_reference`; chapter-level scope, event-layer architecture, and contract categories are incorporated. Exact rule thresholds and full translated rule text remain controlled internal reference pending full QA review.


## 3. User Roles

### Research / CRO roles

- Operator: imports data, checks channels, starts data preparation.
- Scorer / Reviewer: reviews waveform, events, stages, and applies manual corrections.
- Senior Reviewer: confirms review revisions and resolves disagreements.
- Study Director: locks study outputs for CRO/GLP-ready workflows.
- QA Auditor: reviews audit trail, protocol adherence, and export package.
- Admin: manages users, profiles, and system configuration.

### Product modes

- Exploratory research mode: flexible analysis, clearly marked non-GLP exploratory output.
- CRO research-ready mode: study metadata, animal/cohort metadata, review revisions, audit logs.
- GLP-ready / GLP-supporting mode: protocol lock, role permissions, audit trail, review sign-off, archive/export package. The software supports GLP workflows but does not by itself certify the CRO facility as GLP-compliant.

## 4. Supported Domains

### D1. Epilepsy event review

Purpose: automated candidate event screening plus human/manual review.

Must support:

- candidate event detection output;
- waveform-first review;
- synchronized spectrogram evidence;
- event strip and event list;
- confirm / reject / artifact / needs-review labels;
- onset/offset adjustment;
- missed-event insertion;
- review action history;
- Results publication.

Non-medical boundary:

- Use `candidate event`, `research screening support`, `manual review`.
- Do not use diagnosis, confirmed clinical seizure, treatment advice, or clinical triage wording.

### D2. Sleep staging

Purpose: epoch-level sleep stage scoring and manual correction.

Must support configurable stage schemas:

- rodent-style P0/P1: Wake / NREM / REM / Artifact;
- human PSG style when enabled: Wake / N1 / N2 / N3 / REM / Artifact;
- custom profile labels for validated projects.

Must support:

- hypnogram/stage strip;
- epoch paging/selection;
- manual stage edits;
- Undo/Redo;
- stage duration/statistics;
- Results publication.

### D3. Human PSG event scoring foundation

Purpose: prepare architecture for PSG event scoring beyond staging.

Must distinguish epoch labels from interval events.

Event layers may include, after further standard/spec incorporation:

- respiratory events such as apnea/hypopnea/RERA-like categories;
- arousal events;
- oxygen desaturation;
- movement events;
- snoring/audio-derived events;
- body position;
- cardiac-related annotations.

Full release-grade PSG respiratory scoring remains gated until the partial Feishu AASM V3 source is expanded into full rule-level extraction, QA review, authorized citation handling, and fixture-based tests.
AASM V3 / PSG source implications now incorporated at chapter/category level:

- PSG is broader than sleep staging and must include report parameters, technical acquisition metadata, sleep stages, arousals, cardiac events, movement events, respiratory events, HSAT workflows, and terminology governance.
- Stage labels are epoch-level decisions. Arousal, respiratory, movement, cardiac, oxygen, snore, position, and HSAT events are interval or measurement-derived events and must not be collapsed into `Stage_Code`.
- Exact AASM-derived rule thresholds remain controlled internal reference pending full QA review.


### D4. Animal/preclinical workflows

Purpose: support CRO/preclinical animal sleep and epilepsy studies.

Must support:

- species profile: human, mouse, rat, dog, monkey, custom;
- animal metadata: animal_id, strain, sex, age, weight, group, treatment, cage, implant/electrode metadata;
- study/protocol metadata;
- light/dark cycle and intervention timing;
- optional Racine / modified Racine severity schema for rodent epilepsy;
- per-animal and per-group summaries.

Compatibility with any animal means configurable platform support. It does not mean every species algorithm is validated by default.

## 5. Channel Requirements

The workbench must support 1-64 channels.

Must support:

- channel roles, not only raw channel names;
- visible channel subset;
- channel grouping;
- per-channel gain;
- bad-channel status;
- event-related channel highlighting;
- role schemas for EEG, EOG, EMG, ECG, airflow, respiratory effort, SpO2, snore/audio, position, ACC/motion, temperature, and custom auxiliary signals.

## 6. Functional Requirements

### F1. Data preparation inheritance

- Workbench entry requires or clearly marks confirmed Data Preparation context.
- Payloads must carry data_preparation_plan_id, revision, and contract version when applicable.
- The workbench does not alter raw EEG/PSG data.

### F2. Waveform-first entry

- On entering the workbench, waveform evidence appears before or independently of formal algorithm completion.
- No static fake waveform or placeholder image may represent data.

### F3. Synchronized evidence panels

- Waveform, spectrogram, stage/event strips, and tables share one canonical timeline state.
- User selection of event/epoch updates all panels together.
- No panel may keep an independent hidden time range.

### F4. Automated source outputs

- Automated algorithms output read-only source results.
- Source output includes model/workflow/version/provenance where available.
- Algorithms generate candidates/stages, not final human-approved truth.

### F5. Manual correction and review revisions

- Manual edits create ReviewAction records.
- ReviewAction records build ReviewRevision.
- Undo/Redo operates on actions, not raw data.
- Source algorithm output remains immutable.

### F6. Results publication

- Published review revisions must appear in Results.
- Results must include source data, preparation plan, algorithm output, manual changes, and non-medical boundary statement.

### F7. CRO/GLP-ready requirements

CRO/GLP-ready phases must support:

- Study and Protocol identifiers;
- controlled scoring profile;
- role-based access;
- audit trail;
- review lock / sign-off;
- reason-for-change;
- software/model version manifest;
- export/archive package.

Electronic records/signatures and formal validation package are later phases, not P0.

## 7. Non-Functional Requirements

### Performance

Targets for interactive review:

- Initial visible waveform: under 2 seconds for teaching/demo and reasonable local test data.
- Cached pan: under 50 ms.
- New waveform chunk: under 500 ms target.
- Spectrogram window/tile: under 1 second after cache warm-up target.
- Rapid pan/zoom must ignore stale responses.

### Reliability

- Loading/stale/ready states must be explicit.
- Old window data must not be remapped as new data.
- Controls must not appear clickable when ineffective.

### Traceability

- Every major output must trace to raw file, preparation plan, algorithm task, review revision, software version, and model version when available.

## 8. Out Of Scope For P0

- Full human PSG respiratory-event release-grade scoring.
- Full Part 11 electronic signature implementation.
- Formal GLP validation package IQ/OQ/PQ.
- Validated algorithms for every animal species.
- Replacing formal PSD/TFR/Band Power modules with the review spectrogram layer.
- TimeChart or new commercial charting dependency.

## 9. Open Questions

1. Feishu PSG/sleep reference is partially read and incorporated at chapter/category level; full rule-level extraction, QA review, and authorized citation handling remain required before claiming full AASM V3 scoring support.
2. Which first animal species/profile is the commercial priority: mouse, rat, nonhuman primate, or custom CRO profile?
3. Which GLP-ready level is needed for first CRO delivery: research-ready, GLP-ready audit trail, Part 11-style signatures, or full validation package?
4. Which sleep stage schema should ship first: rodent Wake/NREM/REM or human W/N1/N2/N3/REM?

## 10. Change Log

- 2026-06-29: Created baseline PRD from research input, PC sleep source review, epilepsy workflow discussion, PSG/public standards scan, and CRO/GLP requirement expansion.

- 2026-06-29: Incorporated partial Feishu AASM V3 PSG/HSAT source at chapter/category level; added PSG report, technical, arousal, respiratory, movement, cardiac, HSAT, terminology, and rule-governance requirements.

## 11. Traceability Summary

| Requirement | Architecture | Detailed Design | Contract | Test | Release |
| --- | --- | --- | --- | --- | --- |
| Waveform-first child workbench | Main child-page architecture | Workbench shell | TimelineState/WaveformChunk | E2E entry waveform | P0 |
| Epilepsy candidate review | Domain module | Event review UI | EventSchema/ReviewAction | Candidate review flow | P0 |
| Sleep staging | Domain module | Stage/hypnogram UI | StageSchema | Epoch edit flow | P1 |
| Human PSG events | PSG/HSAT event-layer stack | Stage and interval event panels | PSG/HSAT/Arousal/Respiratory/Movement/Cardiac schemas | PSG-001 to PSG-009 | P2a-P2c |
| Animal CRO/GLP | Study layer | Study/protocol UI | Study/Animal/AuditTrail | Audit/signoff tests | P1-P3 |
| 1-64 channels | Channel manager | Channel panel | ChannelRoleSchema | Channel matrix/performance | P0-P4 |

<!-- 20260629_PREVIEW_MIGRATION_BEGIN -->
## 2026-06-29 Owner Correction: Preview Workbench Capabilities Must Migrate Into Epilepsy Workbench

Status: accepted product correction after adversarial review.

Owner observation:

> The epilepsy workbench waveform window still says "enter workbench and first look at waveform", but it has not fully migrated the data-preparation preview/workbench capabilities.

### New P0 requirement set: epilepsy workbench waveform reader is a real reader, not a passive display

The embedded epilepsy workbench must not stop at "waveform visible plus algorithm overlays". It must inherit the core waveform-review behavior from Data Preparation / WaveformWorkbench:

1. Waveform-first entry remains mandatory.
2. Algorithm output is an overlay layer only; source waveform browsing must work before and after screening.
3. EDFBrowser-style navigation must be available:
   - normal mouse wheel = horizontal pan;
   - Ctrl/Cmd + wheel = time zoom around cursor;
   - PageUp/PageDown = previous/next page;
   - Left/Right = small movement;
   - middle-button drag = horizontal pan where browser automation permits;
   - +/- = amplitude sensitivity;
   - Ctrl/Cmd +/- = time-window zoom.
4. A single canonical timeline controller must own:
   - current start/end time;
   - duration scale;
   - visible channel subset;
   - selected event/epoch;
   - current review draft target.
5. A draggable overview/progress strip is required:
   - shows full file duration;
   - shows current window;
   - shows loaded chunks;
   - shows candidate events;
   - shows reviewed/edited intervals;
   - supports click/drag jump.
6. Channel controls must support 1-64 channels:
   - visible channel count/subset;
   - channel group;
   - per-domain channel roles;
   - bad-channel visibility inherited from Data Preparation.
7. Display controls must expose:
   - uV/row amplitude sensitivity;
   - raw/filter/prepared view label;
   - min-max/envelope display mode for long windows;
   - stale/loading/ready state without remapping old data to a new axis.
8. Candidate event controls must include:
   - previous/next candidate;
   - center selected candidate;
   - optional auto-advance after correction;
   - quick labels for Seizure-like candidate / Normal / Artifact / Needs review, with non-medical wording.
9. Review actions must be command-based and auditable:
   - source algorithm output remains immutable;
   - manual correction writes review draft/revision;
   - undo/redo works on commands;
   - publish sends review artifacts to Results.

### P1 requirement set: information architecture cleanup

The epilepsy workbench must reduce repeated status/control text:

- "time window", "progress", and "scale" must not appear as competing controls in multiple places.
- One timeline strip owns navigation; panels may display read-only status.
- Toolbar groups must be explicit: Browse, Display, Overlays, Review Actions, Publish.
- Disabled buttons must expose deterministic reasons and be covered by E2E.
- Customer clean mode must hide developer-only IDs unless expanded.

### Adversarial review conclusion

Current implementation is an internal teaching-chain candidate, not a complete release-ready epilepsy reader. It passes the teaching-mode closed loop, but the waveform reader is still missing several Data Preparation / WaveformWorkbench interactions. Therefore P0 release scope is updated: P0 is not complete until waveform-reader migration E2E passes.


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

Status: implemented and locally accepted for the teaching epilepsy inline workbench.

Scope accepted:
- Main-navigation inline epilepsy workbench now owns a dedicated waveform reader state instead of using the selected candidate event as the implicit viewport owner.
- Reader controls cover page pan, candidate navigation, 5/30/300 s window request with file-duration clamp, uV/row sensitivity, overlay toggles, wheel pan, Ctrl/Cmd wheel zoom, keyboard pan/zoom/gain, middle-drag pan, and draggable overview strip.
- Browse operations must not write review draft commands. Manual correction remains explicit through Seizure / Normal / Needs review actions.
- Time-scale control is centralized in the waveform reader toolbar. The synchronized spectrogram follows the current waveform window and no longer exposes a second duplicate scale control.

Acceptance evidence:
- `node --check frontend/app.js`: passed.
- `node --check scripts/e2e_main_epilepsy_entry_contract.mjs`: passed.
- `node scripts/e2e_main_epilepsy_entry_contract.mjs`: passed.
- `node scripts/validate_epilepsy_child_page_p0_contract.mjs`: passed.
- `node scripts/e2e_epilepsy_child_page_p0.mjs`: passed.

Traceability:
- Covers EPI-RDR-001 through EPI-RDR-008 for the teaching epilepsy path.
- Remaining release risk: real owner-data regression and broader sleep/animal scoring integration are outside this P0b implementation slice.
<!-- 20260629_P0B_READER_IMPLEMENTATION_ACCEPTANCE_END -->

## 2026-06-30 P0 Addendum: Epilepsy PC-Compatible STFT Evidence

Status: accepted for development baseline.

Requirement:
- In the epilepsy-like event screening workbench, the synchronized time-frequency panel must not use a frontend-only temporary STFT as the primary evidence after screening.
- After "start screening", the panel must use the backend artifact `data/epilepsy_ml_spectrogram.json` generated by `epilepsy_ml_xgboost`.
- The artifact must follow QLanalyser-PC `AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis2.py::calculate_spectrogram`: `scipy.signal.stft`, 4 s window, 90% overlap, `boundary="zeros"`, 0.5-50 Hz, `10*log10(abs(Zxx)+1e-10)`, 10/99 percentile display range.
- The layer remains review evidence synchronized with waveform, Stage_Code, candidate events, and manual correction. It is not a substitute for formal TFR, PSD, or Band Power modules.

Acceptance mapping:
- Backend artifact exists and is registered as `epilepsy_ml_spectrogram`.
- Frontend canvas exposes `data-source="epilepsy_ml_spectrogram_artifact_pc_stft"` after screening.
- E2E checks the artifact schema and exact parameter contract.

## 2026-06-30 P0 Addendum: Epilepsy Screening Result Images

Status: accepted requirement amendment.

Requirement:
- Epilepsy-like event screening must produce customer-visible result images, not only CSV/JSON artifacts.
- At minimum, `epilepsy_ml_xgboost` must generate:
  - candidate event timeline image;
  - source-compatible spectrogram preview image.
- These images must be published as task artifacts and shown in the main Results page.
- The images are visual review evidence for candidate event screening and manual review. They must not be described as diagnosis, treatment guidance, seizure confirmation, or clinical triage.

Acceptance mapping:
- Backend writes `figures/epilepsy_ml_event_timeline.svg` and `figures/epilepsy_ml_spectrogram_preview.svg`.
- Task artifact list registers the two SVG files with image MIME type.
- Results page renders an image preview grid for image artifacts.
- Fixture/E2E tests assert that both SVGs exist, are non-empty, contain expected titles, and include the non-medical research boundary.
