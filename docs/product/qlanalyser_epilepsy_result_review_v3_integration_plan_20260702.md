# QLanalyser Epilepsy Result Review v3 Integration Plan

Status: draft for 07 PM architecture review and feature-gated implementation
Date: 2026-07-02
Scope: epilepsy-like EEG event result review, evidence package export, Results publication, and release-gate planning

## Sources Used

- Migrated v3 package:
  `C:\Users\XGN\Documents\Codex\2026-06-25\07-2\work\epilepsy_result_review_v3_migrated_20260702`
- Migrated handoff:
  `work/epilepsy_result_review_v3_migrated_20260702/MIGRATION_HANDOFF_20260702.md`
- Migrated six-pack:
  `work/epilepsy_result_review_v3_migrated_20260702/docs/product/qlanalyser_research_results_review_evidence_package_*.md`
- Current mainline epilepsy trial six-pack:
  `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_*.md`
- Current mainline waveform scoring six-pack:
  `docs/product/qlanalyser_waveform_scoring_workbench_*.md`
- Current mainline UI/code targets:
  `frontend/index.html`, `frontend/app.js`, `backend/api/epilepsy_workbench.py`, Results and report delivery surfaces.

## Sources Blocked Or Unread

- No new external clinical/medical guideline was used in this integration note.
- The Feishu PSG/sleep external wiki remains outside this specific epilepsy result-review slice.
- This note does not claim Claude/DeepSeek re-review; it is a 07 PM/Codex integration plan based on migrated local artifacts and local validator evidence.

## Verified Intake

The migrated v3 package was verified in the 07 workspace:

- `python validate_epilepsy_evidence_package.py`: PASS
- Event package: `qlanalyser_epilepsy_event_E-007_evidence_package.zip`
- All-event package: `qlanalyser_epilepsy_all_events_evidence_package.zip`
- Inventory: 96 PNG, 96 SVG, 18 ZIP, 6 product Markdown documents, 2 Python scripts, 1 HTML prototype.
- HTML readback contract: current-event review exists; delivery center exists; top hero all-event ZIP button is absent; blocked clinical terms were not found.

## Product Decision

v3 is accepted as the reference baseline for epilepsy-like EEG result return and evidence package interaction, but it must enter the main product through a feature gate.

The target user flow is:

```text
Data Preparation
-> Analysis Task
-> Epilepsy-like Event Workbench
-> Candidate Event Detection
-> Manual Research Review
-> Results: Event Review Workspace
-> Evidence Package Export
-> Report Delivery
```

The v3 page must not become a standalone second product. It should become the Results-side review workspace for already generated candidate events and evidence figures.

## Non-Medical Boundary

All user-facing copy must use research/CRO wording:

- allowed: epilepsy-like event, candidate event, screening support, research review, manual correction, evidence package, reviewer status.
- disallowed: diagnosis, positive, negative, lesion, seizure probability, confidence as clinical certainty, treatment, triage, confirmed epilepsy.

Source algorithm outputs are immutable. Manual correction creates a review draft or revision and can be published to Results. It must not overwrite the original algorithm artifact.

## Integration Architecture

### Frontend Placement

1. Keep `#epilepsyWorkbenchInline` as the analysis-side workbench for waveform reading, synchronized candidate overlays, and running initial screening.
2. Add a Results-side feature-gated panel inside `#statistics`:
   - left: candidate event index;
   - center: 1-35 Hz evidence figure viewer;
   - right: current event research review panel;
   - lower/right delivery center: all-event package and generated evidence package status.
3. Keep current-event ZIP action in the right review panel.
4. Keep all-event ZIP action in delivery center, not in hero/top primary actions.

### Backend/API Placement

P0 can reuse existing task artifacts and static evidence package assets behind a feature gate. P1 should expose stable endpoints:

- `GET /api/epilepsy-workbench/{task_id}/events`
- `GET /api/epilepsy-workbench/{task_id}/events/{event_id}/evidence`
- `POST /api/epilepsy-workbench/{task_id}/events/{event_id}/review`
- `POST /api/epilepsy-workbench/{task_id}/evidence-package`
- `GET /api/epilepsy-workbench/{task_id}/evidence-package/{package_id}`

Required production fields for P0/P1:

- reviewer;
- review time;
- task ID;
- package size;
- package generation time;
- checksum/validation status;
- Results publication status.

### Data Contract

Each event review record should include:

- `event_id`;
- `task_id`;
- `source_algorithm_artifact_id`;
- `start_sec`;
- `end_sec`;
- `channels_shown`;
- `evidence_figure_1_35hz_png`;
- `evidence_figure_1_35hz_svg`;
- `current_event_zip`;
- `review_status`;
- `review_note`;
- `reviewer_id`;
- `reviewed_at`;
- `revision_id`;
- `published_to_results`;

Custom channel selection only changes evidence figure rendering and export view. It must not change candidate detection, event timing, or algorithm labels.

## UI Contract

P0 layout must preserve the v3 hierarchy:

1. Event index on the left.
2. 1-35 Hz evidence viewer in the center.
3. Current event review on the right.
4. Delivery center below or adjacent to review output.

Do not reintroduce:

- 5+1 capability cards as first-screen content;
- all-event ZIP as a hero button;
- manifest/CSV/checksum field lists in first screen;
- project-template save as a required current task;
- clinical diagnosis wording.

## Five-Round Adversarial Review Checklist

Before implementation acceptance, run at least five rounds:

1. Page-level intent: can a researcher tell this is an event review workspace within three seconds?
2. Region hierarchy: event index, evidence viewer, current review, and delivery center have one role each and no duplicate primary action.
3. Control state: event select, current ZIP, all-event ZIP, reviewer status, publish status, and disabled reasons are correct.
4. Business flow: analysis result enters Results, manual review writes revision, Results publication is explicit, source algorithm artifact is immutable.
5. Scientific trust: 1-35 Hz evidence is labeled as evidence view, not diagnostic proof; units, time window, channel set, reviewer, and timestamp are visible.

## Release Gate Plan

### P0 Feature-Gated Integration

Entry criteria:

- migrated validator remains PASS;
- mainline `#statistics` can show v3 event review behind a URL or feature flag;
- no router, Headroom, IPC, or model route changes.

Exit criteria:

- event index visible;
- evidence figure visible;
- current-event review panel visible;
- current-event ZIP works;
- all-event ZIP appears only in delivery center;
- non-medical copy validator passes;
- browser E2E passes on local frontend/backend.

### P1 Production Data Wiring

Entry criteria:

- task artifacts provide stable event IDs and evidence figure metadata;
- package generation has size, checksum, generation time, and validation status.

Exit criteria:

- real task ID can load events;
- review status persists;
- Results publication state is visible;
- exported package readback validates.

### P2 Cloud Trial Hardening

Entry criteria:

- P1 passes on local HE-105 or synthetic labeled EDF fixture.

Exit criteria:

- cloud URL upload-to-analysis-to-results-to-export E2E passes;
- package download time and size are logged;
- reviewer/time/task metadata survive refresh;
- failed package generation has recoverable user feedback.

## Implementation Plan

1. Create feature flag:
   - `epilepsy_result_review_v3=1` or internal state flag.
2. Add Results-side v3 panel:
   - no standalone page;
   - keep main navigation shell.
3. Add adapter:
   - convert current epilepsy result artifacts to v3 event review DTO.
4. Add package status model:
   - current event package;
   - all event package;
   - validation status.
5. Add tests:
   - static contract validator;
   - UI copy boundary validator;
   - browser E2E for event selection and package actions;
   - artifact ZIP validator readback.

## Traceability / Acceptance Mapping

| Requirement | Architecture boundary | Test |
|---|---|---|
| Event review is Results-side, not standalone | `#statistics` feature-gated panel | Browser E2E hash stays in main shell |
| Current ZIP right side, all ZIP delivery center | UI layout contract | DOM/text/action inventory |
| Custom channels do not alter algorithm result | adapter contract | DTO comparison before/after channel view change |
| Non-medical wording | copy governance | forbidden-term validator |
| Reviewer/time/task/package metadata | data API contract | API readback and export manifest validation |

## Open Risks

- The migrated v3 prototype is static; production wiring must avoid copying static assumptions into live task state.
- Current mainline `frontend/app.js` is already large and heavily modified; implementation should be sliced to avoid increasing UI state coupling.
- Evidence package generation should be a service/facade, not ad hoc DOM download logic.

## Change Log

- 2026-07-02: Created 07 PM integration plan from migrated v3 evidence package baseline.
