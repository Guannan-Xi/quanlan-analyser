# QLanalyser Epilepsy-like Event Screening Cloud Trial v0.1 - Current Gap Review

Status: document synced 2026-06-30; local API/browser-demo gaps updated, cloud RC blockers remain.

## Scope

This review maps the v0.1 cloud trial goal against the current local codebase. It does not claim cloud acceptance. It identifies the next development slices.

## 2026-07-01 Adversarial Review Round 1
## 2026-07-01 Adversarial Review Round 2
## 2026-07-01 Adversarial Review Round 3

### Reviewer Question 1: Is Results treated as a traceable export target or a decorative summary page?
- Finding: mostly traceable, but the wording still needs to stay strict that Results consumes published review revisions and does not recompute or relabel source outputs.
- Suggested fix: keep Results as a readback of the published review/export package, and require explicit artifact ids in the acceptance packet.

### Reviewer Question 2: Do page states prevent false success?
- Finding: partly. The design notes show waveform-first and explicit empty/loading states, but the trial page still risks using old algorithm overlays or placeholder controls to imply progress before screening really runs.
- Suggested fix: enforce explicit state transitions for empty -> uploaded -> preparation required -> screening running -> review ready -> results ready, with stale-state overwrite protection.

### Reviewer Question 3: Does the copy still hint at broader product modes?
- Finding: the cloud trial docs are better, but the release plan still carries later-phase concepts that can be mistaken for v0.1 scope.
- Suggested fix: keep later phases documented, but label them as future and keep the v0.1 gate text centered on cloud trial, EDF upload, waveform-first review, screening, manual correction, and export.


### Reviewer Question 1: Does the architecture still mix v0.1 and future-release concerns?
- Finding: yes, if the architecture keeps the friendly-customer and broader trial path in the same branch as the v0.1 cloud trial, the boundary is still too loose.
- Suggested fix: explicitly separate v0.1 cloud trial RC from later friendly-customer trial, sleep staging, and any broader production rollout.

### Reviewer Question 2: Are cloud and local evidence clearly distinguished?
- Finding: only partially. The architecture and data contract both mention local demo evidence and cloud RC, but the proof hierarchy is still easy to misread unless each document says local evidence is acceptance-only and cloud RC needs a non-local browser session.
- Suggested fix: keep adding one explicit sentence per doc that says local demo/browser evidence cannot be used to claim cloud RC readiness.

### Reviewer Question 3: Are failure states part of the release gate or only implementation notes?
- Finding: failure states are mentioned, but the trial boundary would be stronger if missing authorization, unconfirmed preparation, task failure, artifact load failure, review-save failure, and export failure were treated as required v0.1 acceptance evidence.
- Suggested fix: make failure-state browser evidence a P0 trial gate instead of a soft follow-up.


## 2026-07-01 Adversarial Review Round 4

### Reviewer Question 1: Is Results a true readback of the published review package?
- Finding: not yet hard enough. The docs say Results opens the export package, but they still do not force a single trace from `review_revision_id` to `report_id` to the exported CSV/JSON files in the acceptance packet.
- Suggested fix: require explicit artifact ids and same-session browser readback in the Results acceptance criteria.

### Reviewer Question 2: Are empty/loading/stale states clearly separated?
- Finding: partially. The release plan and detailed design mention loading and empty states, but they do not yet require stale-state overwrite protection when a newer screening or review revision arrives.
- Suggested fix: make stale-state overwrite protection a named requirement and add E2E assertions for empty, loading, stale, and ready states.

### Reviewer Question 3: Does the trial still allow scope drift through wording?
- Finding: yes, if later-phase wording remains nearby without a hard boundary. Even if the feature is not implemented, nearby mentions of sleep, video, or public rollout can mislead readers about v0.1 scope.
- Suggested fix: keep future-phase items in separate future sections and repeat that v0.1 ends at cloud screening, review, Results, and export.


## 2026-07-01 Adversarial Review Round 5

### Reviewer Question 1: Can cloud RC be claimed from localhost evidence?
- Finding: no. Local browser acceptance is useful, but it is not enough to prove cloud RC. The gate must explicitly require non-local frontend/API URLs and a browser session that both creates and reads back the review package.
- Suggested fix: write the cloud RC gate in a way that rejects localhost-only proof.

### Reviewer Question 2: Is failure evidence treated as first-class acceptance?
- Finding: not fully. The test plan names failure states, but the release gate still reads more like a happy-path summary than a first-class evidence matrix.
- Suggested fix: make upload-authorization failure, unconfirmed-preparation failure, task failure, artifact-load failure, review-save failure, and export failure mandatory P0 evidence rows.

### Reviewer Question 3: Is the boundary to external release explicit enough?
- Finding: mostly, but the owner-data regression path must stay clearly separate from the cloud trial RC path so that a cloud pass cannot be mistaken for external release readiness.
- Suggested fix: keep owner-data regression as the last external-release-only blocker, and state that cloud RC success does not unblock public release.


### Implementation Gate Summary
- Docs are sufficient to proceed to implementation gating for the v0.1 cloud trial slice.
- Not sufficient for external release gating.
- Remaining hard blockers outside the cloud RC slice: non-local cloud/staging browser acceptance, same-session Results readback on the deployed target, and authorized owner-data regression for external release.


### Reviewer Question 1: Is the version goal too broad?
- Finding: yes, if the release plan still retains friendly-customer trial / sleep / video / public production wording, the v0.1 boundary is too wide for a customer-trial gate.
- Suggested fix: keep the v0.1 goal limited to cloud trial, EDF upload, waveform-first screening, manual review, Results/export, and explicit non-medical wording.

### Reviewer Question 2: Is the release gate measurable?
- Finding: partially. Local API/browser/demo evidence is measurable, but cloud RC must require a non-local URL, same-session Results readback, and a pass/fail artifact that names the exact browser E2E checks.
- Suggested fix: require a single cloud acceptance packet with explicit upload, screening, Results, export, failure-state, and copy-governance checks.

### Reviewer Question 3: What blocks trial readiness?
- Finding: cloud/staging upload-to-export, Results-module readback, cloud performance boundary, and owner-data regression remain open.
- Suggested fix: mark those as P0 blockers for cloud trial RC; keep real-data regression as external-release-only.

## Current Strengths Already Present

1. Upload backend exists.
   - `backend/api/eeg_files.py` exposes `/api/eeg/upload`.
   - `backend/services/storage_service.py` persists EEG files and records soft delete audit events.

2. Data preparation contract exists in the main analysis task flow.
   - `frontend/app.js` builds task parameters with `data_preparation_plan_id`, `data_preparation_revision`, and `data_preparation_contract_version`.
   - `epilepsy_ml` is included in the preparation gate.

3. Epilepsy ML backend exists.
   - `eeg_core/analysis/epilepsy_ml.py` outputs epoch predictions, events, summary, model manifest, sidecars, and source-compatible event grouping.

4. Review session backend exists.
   - `backend/api/epilepsy_workbench.py` supports create/get/patch review sessions.
   - Review session records preparation context and source artifact ids.

5. Waveform window backend exists.
   - `backend/api/epilepsy_workbench.py` exposes `/api/eeg/files/{file_id}/waveform-window`.
   - `backend/api/eeg_files.py` exposes `/api/eeg/files/{file_id}/waveform/chunk`.

6. Review export backend exists.
   - `backend/api/epilepsy_workbench.py` exports reviewed epoch scores, reviewed events, review actions, review session manifest, and registered artifacts.

7. Synthetic ordinary-mode fixture exists and passes local algorithm replay.
   - `scripts/generate_regular_epilepsy_labeled_fixture.py`
   - `work/release_evidence/20260629-regular-epilepsy-labeled-fixture/regular_epilepsy_labeled_fixture_acceptance.json`

## Gaps Against v0.1 P0

### G1 Cloud upload authorization confirmation - closed locally, cloud/browser readback pending

Requirement:

- Upload must record user confirmation that the uploader has rights to use the EEG for research trial analysis.

Current:

- Local API acceptance now proves upload authorization is required and read back on the file/metadata path.
- Evidence: `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-contract/upload_authorization_contract.json`.

Still needed:

- Browser UI checkbox/readback evidence from ordinary upload.
- Cloud/staging trial account readback.

Related P0 rows:

- P0-05

### G2 Cloud E2E from upload is missing

Requirement:

- P0 E2E must start from EDF upload, not preloaded demo files.

Current:

- Existing tests cover demo/lab and local API paths.
- Synthetic fixture exists, but cloud upload-to-export E2E is not yet implemented.

Needed:

- Create `scripts/e2e_epilepsy_cloud_trial_v0_1.mjs` or equivalent.
- Drive UI upload using `regular_epilepsy_labeled_60s.edf`.
- Verify P0 matrix output.

Related P0 rows:

- P0-01 through P0-30

### G3 Results/export contract - API package aligned locally, Results UI pending

Requirement:

- CSV: `epoch_predictions.csv`, `candidate_events.csv`, `manual_corrections.csv`, `final_review_events.csv`
- JSON: `summary.json`, `parameters.json`, `model_manifest.json`, `review_revision.json`, `scope_contract.json`

Current:

- Local API export contract now includes the v0.1 CSV/JSON package shape and non-medical scope.
- Evidence: `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_export_contract_receipt_20260629.md`.

Still needed:

- Results module browser evidence that opens and displays the v0.1 export package.
- Export inventory/readback from the ordinary browser upload path.

Related P0 rows:

- P0-23 through P0-26

### G4 Spectrogram evidence contract needs runtime verification

Requirement:

- Spectrogram must be synchronized with waveform/candidate event and based on the same data.

Current:

- UI and prior docs discuss spectrogram.
- Current backend endpoint inspected in this pass focuses on waveform-window; no dedicated v0.1 spectrogram artifact was verified in this review.

Needed:

- Verify existing spectrogram rendering/data source.
- If missing, add a synchronized spectrogram artifact or endpoint using the PC-aligned method.
- Add E2E that checks same selected event/window.

Related P0 rows:

- P0-17, P0-18

### G5 Upload metadata UI/readback needs contract check

Requirement:

- Upload result must show name, size, duration, sampling rate, channel count/names, format, warnings.

Current:

- `EEGFileRead` includes some metadata fields.
- `/api/eeg/files/{file_id}/metadata` exists.
- Current UI evidence not yet checked against the new v0.1 metadata list.

Needed:

- Add/verify UI metadata panel.
- E2E DOM assertion.

Related P0 rows:

- P0-04

### G6 Failure support path is not yet verified

Requirement:

- Failure shows reason, error id, suggested action, support entry.

Current:

- Task errors and UI toasts exist, but v0.1 structured failure UX is not verified.

Needed:

- Define error id convention for upload/screening.
- Add controlled failure E2E.

Related P0 rows:

- P0-27

### G7 No-op control audit must be rerun against v0.1 target

Requirement:

- No clickable no-op controls; disabled controls have reasons.

Current:

- Prior work added control-state reviews, but v0.1 cloud trial target has a new acceptance matrix.

Needed:

- Extend control-state E2E to the cloud trial workflow.

Related P0 rows:

- P0-28

### G8 Cloud environment is not verified in this pass

Requirement:

- v0.1 acceptance must run on cloud staging/trial.

Current:

- This pass is local repository/document work only.

Needed:

- Identify trial URL/environment.
- Run upload-to-export E2E there.
- Record evidence.

Related P0 rows:

- P0-01 through P0-30

## Recommended Development Slices

### Slice A - Upload Authorization and Metadata

Files likely involved:

- `backend/models/eeg_file.py`
- `backend/api/eeg_files.py`
- `backend/services/storage_service.py`
- `frontend/app.js`
- upload E2E script

Exit:

- Upload checkbox visible.
- Authorization stored.
- Metadata panel passes E2E.

### Slice B - v0.1 Export Package Alignment

Files likely involved:

- `backend/api/epilepsy_workbench.py`
- Results UI in `frontend/app.js`
- export acceptance script

Exit:

- CSV/JSON package names match v0.1 contract.
- Non-medical boundary included.
- Results page exposes formal export.

### Slice C - Spectrogram Synchronization

Files likely involved:

- backend spectrogram endpoint or artifact generation
- `frontend/app.js` inline epilepsy workbench
- `frontend/epilepsy-workbench.js`
- E2E screenshot/data-source checks

Exit:

- Selecting event synchronizes waveform, Stage_Code, candidate table, and spectrogram.
- Spectrogram source metadata matches file/channel/window.

### Slice D - Cloud Upload-to-Export E2E

Files likely involved:

- new `scripts/e2e_epilepsy_cloud_trial_v0_1.mjs`
- Playwright runtime helper
- release evidence directory

Exit:

- Synthetic labeled EDF passes upload, preparation, screening, review, Results, export.

## Acceptance Notes

Local fixture replay is already valuable but does not prove v0.1 cloud trial acceptance. The next real acceptance artifact must be a cloud/staging E2E packet that starts from upload.

## Change Log

- 2026-06-29: Created implementation gap review after v0.1 six-pack baseline.
- 2026-06-30: Marked upload authorization and v0.1 API export package gaps locally closed, while keeping browser/cloud/Results/copy/performance/owner-data blockers.

## 2026-06-29 Current Gap Update

The implementation gap review is now updated after the local API and local browser demo acceptance passes.

### Gaps Closed Locally

- Upload authorization is implemented and verified for `/api/eeg/upload`.
- Ordinary uploaded data is blocked from formal analysis until a confirmed data preparation plan exists.
- Data preparation lineage checks now reject draft plans, wrong-file plans, and wrong-project plans.
- `epilepsy_ml` rejects unexpected workflow ids and requires `epilepsy_ml_xgboost`.
- The synthetic ordinary EDF fixture passes upload-to-export API acceptance with Stage_Code `000001100000` and candidate event `25.0-35.0s`.
- Review export now includes the v0.1 CSV/JSON package shape.
- The main analysis page can open an inline epilepsy-like event workbench in the local teaching/demo browser path.

### Remaining P0 Gaps

1. `G-cloud-staging`: no cloud/staging trial URL and trial account browser E2E evidence yet.
2. `G-browser-upload`: no browser E2E that starts from ordinary EDF upload and ends at export/Results.
3. `G-results`: Results module has not yet been verified against the v0.1 review export package.
4. `G-copy-utf8`: customer-facing text and evidence still need a no-mojibake copy governance pass.
5. `G-failure-states`: upload authorization missing, unconfirmed preparation, task failure, artifact load failure, and export failure states need screenshots/assertions.
6. `G-cloud-performance`: cloud timing boundaries are not measured.
7. `G-owner-data`: authorized anonymous real EEG owner-data regression remains pending.

### Next Slice

Build and run a browser E2E for ordinary upload-to-export:

```text
scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs
```

The script must not rely on teaching/demo URL shortcuts for the upload path. It may run locally first, then be reused for cloud/staging by changing the base URL and credentials.

## 2026-06-30 Gap Sync

Closed locally:

- Upload authorization and data preparation gate.
- Strict plan lineage.
- `epilepsy_ml` upload-to-export API E2E.
- v0.1 export contract.
- Main inline epilepsy-like event workbench local browser demo.

Still blocking:

- `G-cloud-staging`: cloud/staging URL plus trial account E2E.
- `G-browser-upload`: ordinary UI upload from the browser through export/Results.
- `G-results`: Results module opening the v0.1 export package.
- `G-failure-states`: failure states and customer-facing error copy.
- `G-copy-governance`: full no-mojibake/no-diagnostic/no-epilepsy-staging scan.
- `G-cloud-performance`: cloud performance boundary.
- `G-owner-data`: owner/steward approved anonymous real data regression.

Next real artifact:

```text
scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs
work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/
```
