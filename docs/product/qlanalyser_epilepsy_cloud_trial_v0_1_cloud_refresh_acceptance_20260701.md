# QLanalyser Epilepsy-Like Event Screening Cloud Trial v0.1 - Cloud Refresh Acceptance

Status: `cloud_synthetic_edf_customer_trial_rc_ready_for_acceptance`; `formal_external_release_blocked_owner_manifest_missing_or_invalid`.

Date: 2026-07-01

## Scope

This receipt records the latest cloud browser refresh run for the QLanalyser epilepsy-like event screening customer-trial v0.1 path.

Accepted scope:

- Cloud browser starts from EDF upload.
- Upload authorization is required and persisted.
- Data Preparation is confirmed before epilepsy-like event screening.
- The workbench is a main-navigation child page, not a standalone mini-app.
- The user starts epilepsy-like event screening, not epilepsy staging.
- The screening task produces Stage_Code, candidate event, synchronized spectrogram evidence, and result image artifacts.
- Manual correction writes a review layer and does not modify source ML artifacts.
- Results/report package includes event timeline and spectrogram figures.

Excluded from this acceptance:

- Clinical diagnosis, treatment recommendation, medical triage, or clinical release.
- Sleep staging, respiratory scoring, and video analysis runtime.
- GLP validation package, e-signature, and regulated audit controls.
- Large EDF / 1GB-class performance claims.
- Formal external release without owner-approved anonymous real EEG regression.

## Evidence Used

Latest cloud browser E2E:

```text
work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh/browser_upload_to_export.json
```

Screenshots:

```text
work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh/01_opened.png
work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh/02_after_upload.png
work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh/03_inline_initial.png
work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh/04_results_review_package.png
```

Gate/readiness readback:

```text
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-release-gate/release_gate_result.json
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-readiness/readiness_packet.json
```

Related six-pack convergence:

```text
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_six_pack_convergence_review_20260701.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_release_gate_receipt_20260701.md
```

## Latest Browser E2E Readback

```text
target = http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=e2e-refresh-20260701a#storage
api = http://39.97.248.225/api
status = passed
checks = 34 / 34 passed
failed = []
uploaded file = regular_epilepsy_labeled_60s.edf
format = EDF
sampling_rate = 250 Hz
channels = 5
duration = 60 s
task = epilepsy_ml / epilepsy_ml_xgboost
task status = completed
task progress = 100
report package = HTTP 200
event timeline figure = present
spectrogram figure = present
```

The E2E check set includes:

- no task before explicit start;
- upload authorization request and readback;
- confirmed data-preparation plan for the uploaded file;
- task payload contract with data-preparation lineage;
- completed epilepsy ML task;
- Stage_Code truth check;
- candidate event truth check;
- review correction save;
- correction matrix action save;
- review export publication;
- Results module review package;
- non-medical export scope;
- rejection of missing upload authorization;
- rejection of unconfirmed data preparation;
- rejection of wrong workflow id;
- rejection of missing review session export;
- customer-facing review labels;
- no old candidate-panel labels;
- no epilepsy staging copy;
- no diagnosis/treatment copy;
- no video placeholder copy;
- waveform-first inline entry;
- no duplicated inline scale controls;
- wheel interaction does not show global toast;
- progress reaches completed;
- spectrogram follows the same window source;
- PC-STFT artifact contract;
- result image artifacts;
- Results module image visibility;
- report package image inclusion;
- Stage_Code overlay toggle.

## Release Gate Readback

Strict cloud gate was rerun with:

```text
QLANALYSER_CLOUD_FRONTEND_URL = http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=e2e-refresh-20260701a#storage
QLANALYSER_CLOUD_API_BASE_URL = http://39.97.248.225/api
QLANALYSER_REQUIRE_CLOUD = 1
```

Result:

```text
cloud_trial_rc_verdict = cloud_trial_rc_ready_for_acceptance
release_verdict = cloud_release_candidate_ready_for_acceptance
external_release_verdict = blocked_owner_manifest_missing_or_invalid
non_medical_boundary = research_screening_support_only
```

Readiness packet result:

```text
status = not_ready
internal_local_status = passed
cloud_trial_rc_status = ready_for_acceptance
external_release_status = blocked_owner_manifest_missing_or_invalid
```

`not_ready` means formal external release is not ready; it does not negate the cloud synthetic EDF customer-trial RC.

## Acceptance Mapping

| Requirement | Latest evidence | Verdict |
| --- | --- | --- |
| Upload starts from the cloud UI | 20260701 cloud browser E2E | Accepted for synthetic RC |
| EDF authorization is required | Positive upload and negative missing-authorization check | Accepted |
| Data Preparation precedes screening | Confirmed plan and negative unconfirmed-plan check | Accepted |
| Workbench is embedded in main navigation | Inline workbench E2E state and screenshots | Accepted |
| Epilepsy terminology avoids staging | Copy checks for no epilepsy staging wording | Accepted |
| Screening task completes | `epilepsy_ml / epilepsy_ml_xgboost`, progress 100 | Accepted |
| Stage_Code and candidate event truth | E2E truth checks passed | Accepted for synthetic fixture |
| Spectrogram is same-source evidence | `epilepsy_pc_stft_artifact_contract` and same-window source checks passed | Accepted |
| Manual correction is review-layer only | Review correction save/export and source immutability checks passed | Accepted |
| Results/report output images | Results image and report package image checks passed | Accepted |
| Formal external release | Owner manifest and real-data regression absent | Blocked |

## Five-Round Adversarial Acceptance Review

### Round 1 - Product Boundary

Question: Does the latest cloud run prove a customer trial path, or does it overclaim a formal external release?

Finding: It proves the synthetic EDF customer-trial RC only. The readiness packet still reports `not_ready` because formal owner-data regression is missing.

Decision: Accept the cloud RC; keep formal external release blocked.

### Round 2 - Workflow Integrity

Question: Can the user reach screening only after upload and preparation, or can the UI bypass the intended flow?

Finding: E2E starts from upload, confirms Data Preparation, then starts screening. Negative checks reject unconfirmed preparation and wrong workflow id.

Decision: Accept workflow integrity for v0.1 synthetic RC.

### Round 3 - Data/API Truthfulness

Question: Are displayed results bound to the current epilepsy task rather than stale or upstream artifacts?

Finding: Previous artifact-binding fix scopes result loading to the current task and excludes data-preparation artifacts. Cloud rerun confirms result images and report package.

Decision: Accept current-task result binding for v0.1 RC.

### Round 4 - UI/Interaction Trust

Question: Do controls create confusion around epilepsy staging, video placeholders, duplicate time-scale controls, or wheel toasts?

Finding: E2E checks pass for no epilepsy staging copy, no video placeholder copy, no duplicate inline scale controls, and no global toast during wheel interaction.

Decision: Accept scoped UI interaction gate.

### Round 5 - Release Readiness

Question: Is it safe to hand this to a controlled customer as a cloud trial?

Finding: Yes for a controlled synthetic EDF customer-trial RC with non-medical wording. No for formal external release, real-data performance claims, GLP claims, or clinical claims.

Decision: `cloud_synthetic_edf_customer_trial_rc_ready_for_acceptance`; `formal_external_release_blocked_owner_manifest_missing_or_invalid`.

## Remaining Work

P0 for formal external release:

1. Receive owner/data steward authorized anonymous EEG `input_manifest.json`.
2. Run owner manifest validator.
3. Run real dataset regression.
4. Read back real-data artifacts, Stage_Code/candidate outputs, review/export package, and non-medical scope.
5. Re-run release gate and readiness packet.

P1 for customer-trial hardening:

1. Cloud latency benchmark for larger EDF files.
2. Explicit cloud data-size boundary.
3. Broader account/permission matrix.
4. Wider visual/control regression on 1440/1280/390 viewports.
5. Legacy page/copy sweep outside the active v0.1 epilepsy path.

## Current Verdict

```text
cloud synthetic EDF customer-trial RC = ready_for_acceptance
formal external release = blocked_owner_manifest_missing_or_invalid
```

## Next Real Artifact

For customer-trial acceptance:

```text
work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh/browser_upload_to_export.json
```

For formal external release:

```text
work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json
work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/real_dataset_regression_result.json
```
