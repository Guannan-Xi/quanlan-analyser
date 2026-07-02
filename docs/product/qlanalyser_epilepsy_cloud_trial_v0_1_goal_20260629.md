# QLanalyser Epilepsy-like Event Screening Cloud Trial v0.1 - Goal

Status: document synced 2026-06-30; local API and local inline-browser evidence accepted, cloud trial RC still blocked.

## Product Goal

Launch a controlled cloud trial of QLanalyser Epilepsy-like Event Screening v0.1.

The trial user must be able to start from the cloud web app, upload EEG/EDF data, complete data preparation, run epilepsy-like event screening, inspect waveform / spectrogram / Stage_Code / candidate event evidence, perform manual review and event correction, save a review revision, then view and export CSV/JSON results from the Results module.

Local demo or localhost browser evidence can support acceptance of implementation slices, but it cannot be used to claim cloud release-candidate readiness.

The cloud RC path must prove Results readback and export from the same non-local browser session that created the review revision.

## Non-Medical Boundary

This version is for research support, CRO trial evaluation, and epilepsy-like candidate event screening. It must not claim diagnosis, seizure confirmation, treatment recommendation, clinical triage, or clinical decision support.

## Trial Audience

Priority order:

1. Internal users.
2. Research trial users.
3. CRO / animal experiment service users.

External trial is controlled invite only: internal users may use an internal account; friendly customers should receive independent trial accounts with scoped permissions.

The trial goal does not include sleep staging, video analysis, or public production release.

## Scope Summary

P0 includes:

- Cloud trial/staging environment, not local-only workflow.
- User upload from the web app.
- EDF is the P0 acceptance format; broader format compatibility can exist but is not release-gated.
- Data preparation confirmation before ordinary uploaded data can run screening.
- Epilepsy-like event screening, not epilepsy staging.
- ML/XGBoost source-compatible workflow as the default; STD remains baseline/internal comparison.
- Waveform-first workbench.
- Progress feedback for screening.
- Candidate events, Stage_Code, waveform overlays, synchronized spectrogram, manual review, review revision, Results entry, CSV/JSON export.
- Synthetic labeled EDF end-to-end cloud validation.

Out of v0.1 P0:

- Full GLP compliance.
- Medical diagnostic claims.
- Batch analysis and batch reports.
- Formal accuracy claims before owner-data regression.

## Success Definition

v0.1 is successful when a trial user can complete this cloud path without developer intervention:

```text
Open cloud app
-> log in / use trial account
-> create or open project
-> upload EEG/EDF
-> inspect file metadata and base waveform
-> confirm data preparation
-> enter Analysis
-> open Epilepsy-like Event Screening workbench
-> click Start Screening
-> see progress and completion/failure state
-> inspect waveform, spectrogram, Stage_Code, and candidate events
-> enter Manual Review
-> correct event/epoch labels
-> save review revision
-> open Results
-> export CSV/JSON package
```

The synthetic labeled EDF acceptance fixture must prove:

- `Stage_Code = 000001100000`
- candidate event = 25.0-35.0 s
- UI event marker is visible
- manual review can be saved
- Results and export package contain the expected outputs

## Sources Used

- Owner choice rounds in the current Codex thread, 2026-06-29.
- `docs/product/epilepsy_sleep_terminology_contract_20260629.md`
- `docs/product/epilepsy_regular_labeled_fixture_20260629.md`
- QLanalyser-PC epilepsy source review already captured in existing product docs.

## Sources Blocked / Unread

- No new Feishu external source was read for this goal document.
- Authorized anonymous real owner data manifest is still not required for internal trial, but remains required before external formal release.

## Change Log

- 2026-06-29: Created v0.1 cloud trial goal baseline.
- 2026-06-30: Synced completed local evidence and kept cloud/trial-account and ordinary browser-upload gaps blocking.

## 2026-06-30 Document Sync

Completed evidence now linked to the goal:

- Upload authorization and data-preparation gate passed locally: `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_upload_contract_receipt_20260629.md`; evidence `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-contract/upload_authorization_contract.json`.
- Strict preparation lineage and normal upload-to-export API E2E passed locally: `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_upload_to_export_e2e_receipt_20260629.md`; evidence `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-to-export/cloud_upload_to_export_contract.json`.
- v0.1 review export CSV/JSON contract passed locally: `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_export_contract_receipt_20260629.md`.
- Main inline epilepsy-like event workbench browser demo passed locally: `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_browser_e2e_receipt_20260629.md`; evidence under `work/release_evidence/20260629-epilepsy-release-e2e/`.

Still blocking this goal:

- Cloud/staging URL plus trial account E2E.
- Ordinary UI upload path starting from the browser.
- Results module opening the v0.1 export package.
- Failure states and customer-facing error copy.
- Full copy governance scan, including no mojibake and no epilepsy "staging" wording.
- Cloud performance boundary.
- Owner/steward approved anonymous real data regression.

Terminology boundary: this v0.1 remains research-support / non-medical epilepsy-like event screening. It is not diagnosis, treatment, triage, clinical decision support, or epilepsy staging.
