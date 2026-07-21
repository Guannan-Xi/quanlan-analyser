# QLanalyser Waveform Scoring Workbench Architecture

Date: 20260629
Status: baseline architecture design
Scope: unified scoring workbench for epilepsy, sleep staging, PSG event scoring foundation, animal/preclinical CRO workflows, and 1-64 channel review

## 1. Architectural Goal

Provide a reusable main-system child workbench that separates raw data, data preparation, source algorithm outputs, manual review revisions, and published Results.

```text
Raw Data -> Data Preparation -> Analysis Task -> Scoring Workbench -> Review Revision -> Results -> Report/Export
```

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


## 3. System Boundaries

### Owned by Data Preparation

- File selection and upload.
- Basic waveform preview.
- Bad channel/bad segment preparation.
- Confirmed preparation plan and revision.

### Owned by Analysis Task

- Formal algorithm task creation.
- Source algorithm output artifacts.
- Workflow/module/model provenance.

### Owned by Scoring Workbench

- Synchronized evidence review.
- Stage/event review session.
- Manual correction draft.
- Undo/Redo.
- Review revision.
- Publish to Results.

### Owned by Results

- Published review artifact display.
- Source-output and review-output traceability.
- Report/export package.

## 4. Layered State Ownership

```text
L0 Raw signal                         immutable
L1 Data preparation plan              read-only in workbench
L2 Source algorithm output            read-only
L3 Local review draft                 editable
L4 Saved review revision              server-authoritative
L5 Published Results artifact         locked/exportable
L6 GLP archive/sign-off package       controlled later phase
```

## 5. Core Modules

```text
MainApp
  DataPreparationPage
  AnalysisTaskPage
    WorkbenchEntryCard
    EmbeddedScoringWorkbench
      WorkbenchContextHeader
      TimelineController
      ChannelManager
      EvidencePanelStack
        WaveformPanel
        SpectrogramPanel
        StageStripPanel
        EventStripPanel
        OptionalAuxiliaryPanels
      DomainPanel
        EpilepsyEventReviewPanel
        SleepStageReviewPanel
        HumanPsgEventPanel
        AnimalStudyPanel
      CorrectionPanel
      ReviewActionHistory
      PublishToResultsPanel
  ResultsPage
```

## 6. Domain Extensibility

Domains are plugins/configurations, not separate mini-apps.

```text
epilepsy_event
sleep_staging
human_psg_event_scoring
animal_preclinical
```

Each domain provides:

- label schemas;
- event/stage schemas;
- default channels/roles;
- supported algorithms;
- result summaries;
- review actions;
- report sections.

## 7. Canonical Timeline Architecture

One `TimelineState` drives all evidence panels:

```json
{
  "window_start_sec": 0,
  "window_duration_sec": 30,
  "selected_epoch_indices": [],
  "selected_event_id": null,
  "scale_mode": "detail | page | overview"
}
```

Rules:

- Waveform, spectrogram, stage strips, respiratory strips, and tables subscribe to this state.
- Pan/zoom/event click/epoch click updates the state once, then all panels render from it.
- Stale responses carry request sequence keys and cannot overwrite newer state.

## 8. Channel Architecture

`ChannelManager` owns 1-64 channel handling:

- raw channel list;
- channel roles;
- visible subset;
- channel groups;
- per-channel gain;
- bad-channel state;
- event-related channel highlighting;
- montage/reference info when applicable.

It must support EEG-only, EEG+EMG+ACC, and PSG-style multimodal signals.

## 9. Evidence Architecture

### Waveform

- Primary evidence layer.
- Uses lightweight waveform chunk API.
- Supports min-max display for long windows.
- Does not trigger formal analysis tasks for browsing.

### Spectrogram

- Review evidence layer.
- Synchronized to the same timeline.
- Does not replace formal TFR/PSD/Band Power modules.

### Stage/Event strips

- Stage strip: epoch-based labels.
- Event strip: interval events.
- Multiple event layers may stack for PSG.


### PSG event layer stack

Human PSG and HSAT workflows use a layered event model:

```text
TimelineState
  StageLayer              epoch labels
  ArousalLayer            interval events
  RespiratoryLayer        apnea/hypopnea/RERA/desaturation-linked intervals
  MovementLayer           movement-related intervals/events
  CardiacLayer            rate/rhythm/cardiac annotations
  OxygenLayer             SpO2 baseline/desaturation/nadir/recovery
  PositionSnoreLayer      optional auxiliary evidence
  HsatLayer               reduced-channel HSAT event/report constraints
```

Rules:

- Stage labels never store respiratory, arousal, movement, cardiac, or oxygen events.
- All layers subscribe to one `TimelineState`; selecting any event recenters waveform, spectrogram, stage strip, and details table together.
- Rule-grade metadata belongs to the scoring profile/contract, not hard-coded UI text.
- HSAT is a separate profile family with fewer channels and different reporting constraints from full PSG.

## 10. Review Architecture

Manual corrections are commands:

```text
ReviewAction -> ReviewDraft -> ReviewRevision -> Published ResultsArtifact
```

Command properties:

- target type: epoch, epoch range, event, interval, channel, artifact;
- old value;
- new value;
- reason;
- user;
- timestamp;
- software/model/profile versions.

Undo/Redo acts on ReviewAction stacks.

## 11. CRO/GLP Study Layer

A future GLP-ready layer wraps the scoring workbench:

```text
Study
  Protocol
  Animal/Cohort
  ScoringProfile
  Controlled Analysis Plan
  Review Session
  Audit Trail
  Sign-off / Lock
  Archive Package
```

GLP-ready does not mean the software certifies a facility. It means the software supports controlled, traceable, auditable study execution.

## 12. API Boundary

Recommended API groups:

```text
/eeg/files/{file_id}/waveform/chunk
/eeg/files/{file_id}/spectrogram-window
/scoring-profiles
/scoring-sessions
/scoring-sessions/{id}/actions
/scoring-sessions/{id}/undo
/scoring-sessions/{id}/redo
/scoring-sessions/{id}/save
/scoring-sessions/{id}/publish-results
/studies
/protocols
/audit-trails
```

## 13. Non-Touch Boundaries

This architecture must not require changes to:

- router;
- Headroom;
- gateway;
- IPC;
- model route;
- unrelated billing/admin modules;
- TimeChart dependency.

## 14. Architecture Risks

| Risk | Mitigation |
| --- | --- |
| PSG scope explodes | P2a/P2b/P2c phases, controlled AASM source handling, and event-layer contracts |
| Any-animal promise overclaims | Profile architecture plus per-species validation requirement |
| 64-channel rendering overload | Channel virtualization and chunk/min-max strategy |
| Manual edits overwrite source | Immutable source output and review revision separation |
| GLP claims overreach | Use GLP-ready/supporting language and validation roadmap |

## 15. Change Log

- 2026-06-29: Created architecture baseline and GLP Study Layer concept.

- 2026-06-29: Incorporated partial Feishu AASM V3 PSG/HSAT source at architecture level; added PSG event layer stack and rule-governance boundary.

<!-- 20260629_PREVIEW_MIGRATION_BEGIN -->
## 2026-06-29 Architecture Amendment: Shared Waveform Reader Core

Status: accepted architecture amendment after owner correction and adversarial review.

### Problem

The current embedded epilepsy workbench has a waveform panel, but the panel is not yet architecturally equivalent to the Data Preparation / WaveformWorkbench reader. This creates a product split:

- Data Preparation has real waveform navigation and preparation interactions.
- Epilepsy workbench has synchronized evidence display, but limited browsing controls.

### Required architecture

Introduce or enforce a shared reader-core boundary:

```text
WaveformReaderCore
  TimelineState
  ViewportController
  ChannelController
  WaveformChunkClient
  OverviewStrip
  InteractionMapper
  OverlayRegistry
  LoadingStaleReadyState
```

Domain workbenches must compose the shared reader core:

```text
EmbeddedScoringWorkbench(epilepsy)
  WaveformReaderCore
  EpilepsyOverlayAdapter
    Stage_Code layer
    candidate event layer
    review correction layer
  EpilepsyReviewCommandPanel
```

### Ownership rules

- `WaveformReaderCore` owns pan/zoom/window/channel/display state.
- Epilepsy overlay adapter owns candidate events, Stage_Code, and review overlays.
- Correction panel owns review commands.
- Results owns published review artifacts.
- No panel may maintain an independent hidden time range.

### Anti-patterns now forbidden

- Rendering a passive waveform panel with no reader controls and calling it a workbench.
- Duplicating time controls in multiple panels.
- Letting algorithm output drive the source waveform viewport as the primary owner.
- Treating STFT preview as formal TFR/PSD/Band Power.
- Using standalone workbench navigation inside the main-system child page.

### Join condition for P0 architecture

The embedded epilepsy workbench is architecturally accepted only when:

1. one TimelineState drives waveform, overview, Stage_Code, spectrogram, candidate list, and correction panel;
2. reader controls work before and after the epilepsy screening task;
3. stale responses cannot overwrite the latest viewport;
4. Data Preparation and Epilepsy do not fork incompatible waveform interaction semantics.


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

Architecture decision accepted:
- `epilepsyInline.reader` is the viewport owner for the inline epilepsy waveform reader.
- Candidate events can request recentering, but selected events no longer drive every render's waveform window.
- Waveform, synchronized spectrogram, Stage_Code strip, candidate table, and review draft share the same selected event and reader window state.
- The waveform chunk request key is derived from file id, reader start, reader duration, channel count, and decimation mode, so stale responses cannot overwrite a newer reader window.

Acceptance evidence:
- `node scripts/e2e_main_epilepsy_entry_contract.mjs`: passed with reader toolbar, overview drag, wheel, keyboard, candidate navigation, overlay toggle, and no-draft-on-browse checks.

Traceability:
- P0b is accepted for the inline epilepsy teaching path. Shared sleep/animal workbench extraction remains a later architecture slice.
<!-- 20260629_P0B_READER_IMPLEMENTATION_ACCEPTANCE_END -->

## 2026-06-30 P0 Addendum: Epilepsy STFT Artifact Boundary

Architecture decision:
- Epilepsy time-frequency evidence is produced in the backend analysis layer, not synthesized as the primary source by the browser.
- `run_epilepsy_ml()` writes `data/epilepsy_ml_spectrogram.json`; `task_service` registers it with other epilepsy ML artifacts.
- The main workbench frontend loads the artifact through the existing artifact download facade and renders only the current `ReaderState` time window.

Boundary:
- Algorithm/source-compatible computation: `eeg_core.analysis.epilepsy_ml`.
- Artifact registration: `backend.services.task_service`.
- Visualization and synchronization: `frontend/app.js`.
- No TimeChart integration and no replacement of formal TFR/PSD/Band Power workflows in this checkpoint.

Source reference:
- `AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis2.py::calculate_spectrogram`.

## 2026-06-30 Architecture Addendum: Result Image Publication Boundary

Status: accepted architecture amendment.

Boundary:
- `eeg_core.analysis.epilepsy_ml` owns generation of source-compatible tabular outputs, spectrogram JSON, and visual evidence SVGs.
- `backend.services.task_service` owns artifact registration and MIME typing.
- The Results module owns final display of task image artifacts.
- The embedded epilepsy workbench may use these artifacts for synchronized review, but it must not be the only place where final results are visible.

Ownership rules:
- Source algorithm artifacts are immutable.
- Manual review and correction are separate review-session/revision outputs.
- Result images are evidence previews for research screening, not regulated diagnostic report figures.

Anti-pattern now forbidden:
- Completing an epilepsy screening run with only hidden CSV/JSON outputs and no customer-visible result images.
