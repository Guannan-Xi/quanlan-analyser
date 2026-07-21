# QLanalyser Epilepsy-Like Event Screening Cloud Trial v0.1 - Six-Pack Convergence Review

Status: `cloud_synthetic_edf_trial_rc_ready_for_acceptance`; `formal_external_release_blocked_owner_manifest_missing_or_invalid`.
Date: 2026-07-01
Scope: requirements, architecture, detailed design, data/API contract, E2E test plan, release plan for the epilepsy-like event screening customer-trial version.

## 1. Purpose

This document freezes the current six-pack convergence state after the 2026-07-01 cloud E2E rerun. It prevents the project from drifting back into screenshot-by-screenshot fixes by tying every accepted behavior to a requirement, boundary, test, and release decision.

The accepted v0.1 product path is:

```text
Cloud app
-> trial user / customer-demo access
-> project
-> EDF upload with authorization
-> data preparation confirmation
-> analysis task
-> embedded epilepsy-like event workbench
-> waveform-first review
-> epilepsy_ml_xgboost screening
-> Stage_Code / candidate events / synchronized STFT spectrogram
-> manual correction
-> review export
-> Results image/table/report package
```

The module remains non-medical research support. It must not claim diagnosis, treatment, clinical triage, or epilepsy staging. Sleep uses staging; epilepsy uses event screening, candidate events, manual review, event correction, and export.

## 2. Sources Used

Six-pack and active receipts:

```text
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_requirements_20260629.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_architecture_20260629.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_detailed_design_20260629.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_data_api_contract_20260629.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_e2e_test_plan_20260629.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_release_plan_20260629.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_release_gate_receipt_20260701.md
```

Evidence:

```text
work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/browser_upload_to_export.json
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-release-gate/release_gate_result.json
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-readiness/readiness_packet.json
```

Relevant implementation files:

```text
frontend/app.js
scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs
scripts/validate_epilepsy_cloud_trial_v0_1_release_gate.mjs
scripts/build_epilepsy_cloud_trial_readiness_packet.mjs
```

## 3. Current Acceptance State

| Gate | Current State | Evidence | Interpretation |
| --- | --- | --- | --- |
| Local browser upload-to-export | Passed, 34/34 | `20260629...browser-upload-to-export/browser_upload_to_export.json` | Internal implementation evidence. |
| Cloud browser upload-to-export | Passed, 34/34 | `20260630...cloud-upload-to-export/browser_upload_to_export.json` | Synthetic EDF customer-trial RC accepted for trial acceptance. |
| Release gate | `cloud_release_candidate_ready_for_acceptance` | `release_gate_result.json` | Cloud synthetic trial path ready for acceptance. |
| Readiness packet | `not_ready`; cloud trial ready, external release blocked | `readiness_packet.json` | Not ready only under full external release standard. |
| Owner real-data regression | Missing | owner manifest path not present | Blocks formal external release, not synthetic cloud trial RC. |

## 4. Requirement Traceability

| Requirement | Requirements Doc | Architecture | Detailed Design | Data/API Contract | E2E Evidence | Release Decision |
| --- | --- | --- | --- | --- | --- | --- |
| Cloud EDF upload with authorization | R2 / R10 | Upload service -> Data Preparation | Upload first, then preparation | `upload_authorization_confirmed=true` | cloud E2E passed | Accepted for synthetic RC |
| Confirmed data preparation before screening | R3 | Data Preparation owns plan | Preparation gate before workbench action | `data_preparation_plan_id/revision/contract_version` | cloud E2E payload/readback | Accepted |
| Main-navigation child workbench | R4/R7 | main shell child workbench | no standalone return button | UI context only, no direct artifact mutation | title/nav in E2E | Accepted |
| Waveform-first entry | R7 | Scoring workbench evidence layer | waveform before screening panel | waveform preview/chunk evidence | `inline_entry_waveform_first` | Accepted |
| Start screening with progress | R6 | Analysis task layer | progress bar and message | `epilepsy_ml_xgboost` task | `inline_progress_completed` | Accepted |
| Stage_Code and candidate truth | R7/R10 | source algorithm read-only layer | Stage_Code strip + event list | epoch/events artifacts | `000001100000`, `25.0-35.0s` | Accepted for fixture |
| Same-window STFT evidence | R7 | evidence adapter | STFT follows waveform window | `epilepsy_ml_spectrogram.json` | `inline_spectrogram_same_window_source` | Accepted |
| Manual correction/review revision | R8 | L3/L4 review draft/revision | correction panel + draft ledger | review session + patch/export | review save/export passed | Accepted |
| Results image/table/report package | R9 | Results consumes published review artifacts | image preview and technical links | review export + figures | report package includes images | Accepted |
| Non-medical wording | R11 | boundary rules | copy guard | `research_screening_support_only` | copy checks passed | Accepted for scoped v0.1 |
| Formal external release | R10.4 | owner-data gate | not UI-only | owner manifest/regression | missing | Blocked |
| Large EDF / 1GB-class performance | R2.3/R6.4 | performance future envelope | long-task feedback required | future chunk/caching contract | not measured | Not claimed |

## 5. Five-Round Adversarial Review

### Round 1 - Product Goal and Scope

Self-question: Are we secretly building a local demo instead of a cloud customer-trial flow?

Finding: Earlier documents mixed local evidence and cloud readiness. Current evidence now includes a non-local browser run at `http://39.97.248.225` with ordinary EDF upload, data preparation, screening, review export, Results, and report package.

Decision: Accept cloud synthetic EDF customer-trial RC. Keep external formal release blocked until owner data regression.

Change applied: Requirements, architecture, data/API contract, E2E plan, release plan, and release-gate receipt now distinguish synthetic cloud RC from formal external release.

Remaining risk: Customer accounts/auth hardening and large-file performance are not proven by the synthetic fixture.

### Round 2 - Information Architecture and Workflow

Self-question: Does the page follow the intended business flow, or does it still behave like a detached waveform demo?

Finding: Current accepted path is main-navigation child workbench. The chain is Data Preparation -> Analysis Task -> Epilepsy Workbench -> Manual Correction -> Results. This matches the user correction that the workbench must be part of the system, not standalone.

Decision: Accept for v0.1 synthetic RC.

Change applied: Six-pack status now references child workbench and Results package readback as accepted cloud evidence.

Remaining risk: Sleep staging and PSG event scoring are future phases and must not be implied by the epilepsy RC.

### Round 3 - Data/API Truthfulness

Self-question: Can the UI accidentally bind the wrong artifact and show false results?

Finding: A real cloud failure exposed this risk: `/tasks/{task}/artifacts` may include data-preparation artifacts before epilepsy task artifacts. A loose label/path matcher can select the wrong artifact.

Decision: Fix at the UI data-binding layer and document it as a contract rule.

Change applied: `frontend/app.js` now scopes inline epilepsy result artifacts to the current `task_<id>` directory, excludes `data_preparation`, and binds epoch/events/spectrogram artifacts explicitly.

Evidence: Cloud E2E passed after the fix; release gate reads cloud status as passed.

Remaining risk: Future artifact labels must preserve this current-task scoping rule.

### Round 4 - Controls, States, and User Trust

Self-question: Are there inert buttons, duplicate controls, misleading loading messages, or unsafe copy that a customer would distrust?

Finding: Current cloud E2E covers no old wheel-loading toast, progress completion, Stage_Code overlay toggle, no duplicate scale controls, scoped copy governance, and key failure states. Manual correction buttons save and export real backend review sessions.

Decision: Accept scoped v0.1 control/state coverage.

Remaining risk: Full product obsolete-page copy governance and a larger keyboard/control matrix remain future hardening tasks.

### Round 5 - Release Readiness and Boundary Claims

Self-question: Are we over-claiming beyond the evidence?

Finding: The synthetic 60 s EDF path is now ready for customer-trial acceptance, but formal external release is not ready because owner-approved anonymous real EEG regression is missing. Large EDF / 1GB performance is also not proven.

Decision: Do not mark full external release complete. Do not claim GLP readiness, sleep staging, respiratory scoring, any-animal validity, or clinical value in v0.1.

Remaining P0 for formal release: owner manifest and real-data regression.

Remaining P1 for customer-trial hardening: large-file latency benchmark, account/permission trial matrix, broader visual/control regression, full obsolete-page copy sweep.

## 6. Release Decision

```text
cloud synthetic EDF customer-trial RC: ready_for_acceptance
formal external release: blocked_owner_manifest_missing_or_invalid
```

The accepted cloud RC uses synthetic labeled EDF evidence only. It is appropriate for controlled customer trial demonstration and internal acceptance, not for unrestricted external release or efficacy claims.

## 7. Next Development Slices

P0 next if owner data arrives:

1. Validate `input_manifest.json`.
2. Run real dataset regression.
3. Read back artifacts, Stage_Code/candidate outputs, review/export package, and non-medical scope.
4. Update release gate from `blocked_owner_manifest_missing_or_invalid` only if real-data regression passes.

P1 next for customer trial hardening:

1. Measure upload/metadata/screening/artifact/review/export latency on cloud with larger EDF files.
2. Add a customer account/permission matrix for view/upload/review/export roles.
3. Extend visual/control E2E for keyboard, disabled states, empty states, failed artifact load, and report-package viewing.
4. Add scheduled artifact cleanup/quota policy for repeated trial uploads.

P2 next for platform roadmap:

1. Sleep staging child workbench using the shared waveform scoring architecture.
2. Animal/CRO study metadata and audit workflow.
3. 1-64 channel performance and layout regression.
4. GLP-supporting audit/export package, only after owner selects a GLP validation level.

## 8. Change Log

- 2026-07-01: Created convergence review after cloud E2E passed 34/34 and release gate returned `cloud_release_candidate_ready_for_acceptance`.
- 2026-07-01: Recorded artifact binding fix as design/API contract, not just implementation detail.
- 2026-07-01: Preserved formal external release blocker for owner-approved anonymous real EEG regression.
