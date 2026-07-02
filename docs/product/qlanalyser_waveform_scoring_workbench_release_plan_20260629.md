# QLanalyser Waveform Scoring Workbench Release Plan

Date: 20260629
Status: baseline version roadmap
Scope: staged delivery plan for unified waveform scoring workbench

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


## 2. Release Principle

Design together, implement in phases.

The architecture must support epilepsy, sleep, PSG, animal/CRO, and 1-64 channels, but releases must not claim more than has been implemented and validated.

## 3. P0: Epilepsy Event Review Closed Loop

### Goal

Deliver the first complete closed loop:

```text
Data Preparation -> Epilepsy Workbench -> Candidate Events -> Manual Review -> Results
```

### Includes

- main-navigation child workbench;
- waveform-first entry;
- automatic candidate events from existing epilepsy task path or fixture-backed source;
- synchronized waveform/spectrogram/event strip;
- event list and event details;
- confirm/reject/artifact/needs-review;
- onset/offset adjustment;
- Undo/Redo;
- publish to Results;
- non-medical research-support wording.

### Excludes

- human PSG respiratory scoring;
- GLP sign-off/electronic signatures;
- full 64-channel performance guarantee;
- any-animal algorithm validity claims.

### Exit criteria

- P0 E2E EPI-001 to EPI-007 pass.
- Non-medical wording check passes.
- Results publication visible.
- No static fake waveform/video placeholder.

## 4. P1: Basic Sleep Staging Workbench

### Goal

Deliver configurable sleep staging review.

### Includes

- sleep scoring profile selection;
- rodent Wake/NREM/REM or human basic W/N1/N2/N3/REM profile;
- waveform/hypnogram/spectrogram sync;
- epoch selection and range selection;
- manual stage correction;
- Undo/Redo;
- sleep stage summary;
- publish to Results.

### Excludes

- full AASM respiratory/arousal/movement/cardiac event scoring;
- GLP sign-off;
- species-wide algorithm validation.

### Exit criteria

- SLP-001 to SLP-005 pass.
- StageSchema contract implemented.
- Results page shows stage outputs and provenance.

## 5. P2: Human PSG / HSAT Event Scoring Foundation

### Goal

Add human PSG and HSAT event-layer foundation without overclaiming full rule-level clinical scoring.

### P2a PSG architecture and event schemas

Includes:

- PSG channel-role profile;
- separate stage, arousal, respiratory, movement, cardiac, oxygen, position/snore, and auxiliary event layers;
- PSG report parameter contract;
- rule-grade metadata contract;
- PSG-001 to PSG-009 contract/browser fixtures.

Exit criteria:

- PSG event schemas pass static contract tests.
- Event layers do not collapse into Stage_Code.
- Rule-grade metadata displays without copying controlled rule text.

### P2b AASM V3 rule-aware scoring support

Includes:

- authorized internal AASM V3 rule-level extraction;
- QA-reviewed rule profiles;
- rule citations / controlled internal pointers;
- adult/pediatric/profile scope handling where supported;
- respiratory/arousal/movement/cardiac summary checks.

Exit criteria:

- Full internal source review completed.
- Rule threshold tests pass for authorized fixtures.
- Customer-facing wording remains research-support / non-diagnostic.

### P2c HSAT support

Includes:

- HSAT-specific channel-role profile;
- reduced-channel constraints;
- HSAT-specific report parameters and unavailable-channel states;
- no PSG-only controls when required channels are absent.

Exit criteria:

- HSAT fixture loads with correct unavailable/available layers.
- HSAT report parameters generate from allowed source layers.

### Excludes

- full rule-level scoring until P2b criteria pass;
- regulatory medical-device claims.

### Exit criteria

- PSG-001 to PSG-009 pass for P2a.
- P2b/P2c remain hidden unless their own exit criteria pass.

## 6. P3: Animal / CRO Research-Ready And GLP-Ready Foundation

### Goal

Support CRO animal studies with traceable review workflows.

### Includes

- Study/Protocol/Animal metadata;
- controlled ScoringProfile;
- role-based permission foundation;
- audit trail;
- reason-for-change;
- review lock;
- source/model/software version manifest;
- per-animal/per-group result summaries.

### GLP-ready wording

Use:

```text
GLP-ready / GLP-supporting workflow features
```

Do not claim:

```text
software is GLP certified
```

### Exit criteria

- CRO-001 to CRO-004 pass.
- Audit trail export exists.
- Locked review cannot be silently edited.
- Report package includes provenance and version manifest.

## 7. P4: Scale And 1-64 Channel Performance

### Goal

Make the workbench robust for large files and 1-64 channel review.

### Includes

- channel virtualization/grouping;
- min-max waveform chunk rendering;
- spectrogram tiles/cache;
- rapid pan/zoom stale response protection;
- 64-channel fixture tests;
- visual regression for dense channel displays.

### Exit criteria

- PERF-001 to PERF-005 pass or have accepted environment-specific baselines.
- No horizontal overflow at target viewports.
- Channel grouping and visible subset UX accepted.

## 8. P5: Part 11 / Formal Validation Package, If Required

### Goal

Only if owner/CRO need electronic-record regulated workflows.

### Includes

- electronic signature workflow;
- authentication/session controls;
- audit trail review;
- archive package;
- IQ/OQ/PQ documentation;
- SOP templates;
- validation test suite;
- model validation report.

### Exit criteria

- Owner selects regulated/GLP validation scope.
- Validation package reviewed by QA/regulatory owner.

## 9. Release Gate Summary

| Phase | Can be internally accepted when | Cannot claim |
| --- | --- | --- |
| P0 | Epilepsy closed loop E2E passes | PSG, GLP, any-animal validity |
| P1 | Sleep staging E2E passes | Respiratory PSG scoring |
| P2 | PSG event contracts/tests pass | Full PSG scoring without spec |
| P3 | Audit/study/lock tests pass | Facility GLP certification |
| P4 | Performance/64-channel tests pass | Infinite channel/file scalability |
| P5 | Validation package accepted | Regulatory equivalence without owner approval |

## 10. Data And Regression Requirements

- P0: synthetic/demo EEG plus available epilepsy fixture.
- P1: sleep staging fixture, preferably Sleep-EDF-like or PC-derived sample where allowed.
- P2: authorized PSG fixture with channel-role metadata.
- P3: animal/CRO fixture with animal_id/group/treatment/protocol metadata.
- P4: 1/8/16/32/64 channel performance fixtures.

Real owner data regression remains required before external release claims.

## 11. Rollback Strategy

- Each phase must be feature-flag or route-gated where practical.
- Source outputs remain immutable, so review-layer rollback can discard review revisions without touching raw data.
- P2/P3/P4 features can remain hidden until contracts/tests pass.

## 12. Owner Decisions Needed

1. Decide whether the partial Feishu AASM V3 source read is enough for P2a, or whether full rule-level extraction should be completed before any PSG UI is exposed to customers.
2. Choose first commercial animal/CRO species/profile.
3. Choose first GLP-ready target level.
4. Decide whether P1 prioritizes rodent sleep or human basic sleep staging.
5. Provide real anonymized regression data manifest before external release.

## 13. Change Log

- 2026-06-29: Created baseline release roadmap P0-P5.

- 2026-06-29: Incorporated partial Feishu AASM V3 PSG/HSAT source into release phasing; split P2 into P2a/P2b/P2c.

<!-- 20260629_PREVIEW_MIGRATION_BEGIN -->
## 2026-06-29 Release Plan Amendment: P0 Epilepsy Reader Migration Gate

Status: accepted release-gate amendment.

### Updated P0 interpretation

The current teaching-mode closed loop is accepted as an internal candidate, but P0 epilepsy cannot be called release-ready while the waveform window remains a partial display. The release gate now requires migration of core Data Preparation / WaveformWorkbench reader capabilities into the embedded epilepsy workbench.

### P0a already accepted

- main-navigation inline epilepsy child page;
- teaching epilepsy fixture path;
- waveform visible;
- STFT preview clearly marked as review-only;
- Stage_Code/event synchronization;
- manual correction save/export;
- teaching protection.

### P0b required before release-candidate label

- EDFBrowser-style pan/zoom/key controls;
- draggable overview strip;
- canonical ReaderState shared by waveform, Stage_Code, spectrogram, candidate list, and correction panel;
- channel/display controls including uV/row;
- candidate previous/next/center controls;
- overlay toggles and non-obscuring overlay visuals;
- stale request guard;
- no duplicate time/progress control confusion;
- EPI-RDR-001 to EPI-RDR-008 pass.

### Deferral policy

If any reader feature is deferred, the release receipt must say `partial_epilepsy_reader_migration` and name the exact missing feature. Do not describe the workbench as complete if it only shows a passive waveform display.

### Risk update

The largest P0 product risk is no longer "can the page open"; it is "does the page behave like a professional EEG review workbench rather than a result page with a waveform picture".


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
## 2026-06-29 P0b Release Gate Update

P0b status: accepted for internal epilepsy teaching trial.

Accepted:
- Inline epilepsy reader is no longer a static waveform result view.
- Reader controls, overview drag, mouse/keyboard EDFBrowser-style navigation, synchronized spectrogram, candidate navigation, and manual correction draft separation are covered by E2E.
- Duplicate time-scale controls were reduced by centralizing control in the waveform reader and making the spectrogram a follower.

Not yet external-release complete:
- Real owner-data regression remains required.
- Sleep staging and animal 1-64 channel shared scoring workbench still require the next six-pack implementation slice.
- Broader customer visual polish should continue with five-round adversarial UI review on real data screenshots.

Current recommendation:
- Proceed to the next implementation slice: real-data epilepsy trial hardening, then shared epilepsy/sleep scoring workbench extraction.
<!-- 20260629_P0B_READER_IMPLEMENTATION_ACCEPTANCE_END -->

## 2026-06-30 P0 Addendum: Cloud Trial Release Gate For Epilepsy STFT

Release gate:
- Cloud trial cannot be accepted if the epilepsy workbench shows only frontend-derived temporary STFT after screening.
- The backend must generate and register `epilepsy_ml_spectrogram`.
- The browser E2E must prove that the rendered spectrogram comes from `epilepsy_ml_spectrogram_artifact_pc_stft`.

Rollout:
- Local fixture run first.
- Browser/cloud upload-to-export E2E second.
- Then deploy frontend/backend together because the UI depends on the new artifact.

Rollback:
- If artifact generation fails in production, hide the spectrogram evidence panel behind the waiting state rather than falling back to a misleading frontend-only spectrogram.

## 2026-06-30 Release Plan Addendum: Result Image Gate

Status: accepted P0 release-gate amendment.

P0 epilepsy cloud trial is not release-ready unless:
- screening creates event timeline and spectrogram SVG result images;
- task artifacts expose both images;
- Results page displays the images as first-class result previews;
- the images preserve the research-only, non-diagnostic boundary.

Rollback:
- If image generation fails, keep tabular/JSON artifacts available but mark the release gate failed.
- Do not fake result images with static placeholders or frontend-only drawings that are not tied to the task artifact contract.
