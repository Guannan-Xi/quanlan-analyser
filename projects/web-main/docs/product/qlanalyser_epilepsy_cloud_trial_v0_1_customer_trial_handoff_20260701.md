# QLanalyser Epilepsy-Like Event Screening Cloud Trial v0.1 - Customer Trial Handoff

Status: `customer_trial_handoff_ready`; `cloud_synthetic_edf_rc_ready_for_acceptance`; `formal_external_release_blocked_owner_manifest_missing_or_invalid`.

Date: 2026-07-01

## Purpose

This handoff is the controlled customer-trial package for QLanalyser epilepsy-like event screening v0.1. It is intended for guided trial use, not unrestricted external release.

The product wording is:

- epilepsy-like event screening;
- candidate event detection;
- manual review / manual correction;
- review version save;
- results export.

Do not call this module epilepsy staging. Sleep uses staging; epilepsy uses event screening and review.

## Trial Link

Cloud trial URL:

```text
http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=e2e-refresh-20260701a#storage
```

API base:

```text
http://39.97.248.225/api
```

Recommended guided path:

```text
Storage / Upload
-> Data Preparation
-> Analysis Task
-> Epilepsy-like Event Workbench
-> Start Screening
-> Candidate Event Review
-> Save Review Version
-> Export Results
-> Results / Report Package
```

## Trial Dataset

Synthetic labeled EDF fixture:

```text
D:\Quanlan\Codes\Python\quanlan-analyser-official\work\fixtures\epilepsy_regular_labeled\regular_epilepsy_labeled_60s.edf
```

Fixture details:

```text
file_size = 152152 bytes
duration = 60 s
sampling_rate = 250 Hz
channels = 5
expected Stage_Code = 000001100000
expected candidate event = 25.0-35.0 s
```

Related fixture evidence:

```text
D:\Quanlan\Codes\Python\quanlan-analyser-official\work\fixtures\epilepsy_regular_labeled\regular_epilepsy_labeled_manifest.json
D:\Quanlan\Codes\Python\quanlan-analyser-official\work\fixtures\epilepsy_regular_labeled\regular_epilepsy_labeled_stage_code.csv
D:\Quanlan\Codes\Python\quanlan-analyser-official\work\fixtures\epilepsy_regular_labeled\regular_epilepsy_labeled_events.csv
D:\Quanlan\Codes\Python\quanlan-analyser-official\work\fixtures\epilepsy_regular_labeled\regular_epilepsy_labeled_generation_evidence.json
```

This fixture is synthetic. It is useful for customer workflow demonstration and automated acceptance, not for efficacy claims on real-world datasets.

## What The Customer Should See

Expected visible behavior:

1. Upload requires an authorization confirmation.
2. The uploaded EDF appears with metadata.
3. Data Preparation can be confirmed before screening.
4. The analysis workbench opens inside the main QLanalyser navigation.
5. The first meaningful workbench view is the waveform reader.
6. The primary action is Start screening. In Chinese UI, this is the start-initial-screening action.
7. A progress state is visible while screening runs.
8. Screening completes with one synthetic candidate event around 25.0-35.0 s.
9. Stage_Code overlay and synchronized spectrogram evidence are visible.
10. Manual correction buttons write review-layer changes only.
11. Export creates a review package.
12. Results/report package includes event timeline and spectrogram figures.

Expected backend/task behavior:

```text
module_name = epilepsy_ml
workflow_id = epilepsy_ml_xgboost
data_preparation_plan_id = present
data_preparation_revision = present
data_preparation_contract_version = qlanalyser-data-preparation-v0.2
non_medical_scope = research_screening_support_only
```

## Trial Evidence Already Passed

Latest cloud browser E2E:

```text
work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh/browser_upload_to_export.json
```

Result:

```text
status = passed
checks = 34 / 34 passed
failed = []
report package = HTTP 200
event timeline figure = present
spectrogram figure = present
```

Screenshots:

```text
work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh/01_opened.png
work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh/02_after_upload.png
work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh/03_inline_initial.png
work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh/04_results_review_package.png
```

Current release-gate verdict:

```text
cloud_trial_rc_verdict = cloud_trial_rc_ready_for_acceptance
release_verdict = cloud_release_candidate_ready_for_acceptance
external_release_verdict = blocked_owner_manifest_missing_or_invalid
```

## Support Packet

Use this support packet to control the live customer-trial session, classify issues, record feedback, and decide whether to continue or stop:

```text
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_customer_trial_support_packet_20260701.md
```

Trial-day operator materials:

```text
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_trial_day_operator_card_20260701.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_trial_issue_log_template_20260701.md
```

## Customer Trial Boundary

Allowed claims:

- The system can demonstrate a cloud EEG upload-to-review workflow on the synthetic EDF fixture.
- The workflow supports epilepsy-like event candidate screening for research review.
- Manual review creates a review layer and does not modify source ML outputs.
- Results and report packages can include event timeline and spectrogram figures.

Do not claim:

- clinical diagnosis;
- treatment recommendation;
- medical triage;
- epilepsy staging;
- GLP validation readiness;
- real-data efficacy;
- 1GB EDF performance;
- arbitrary 1-64 channel production readiness;
- sleep staging / respiratory scoring / video analysis runtime in this v0.1 epilepsy trial.

## Known Limits

1. Formal external release is blocked until owner/data steward provides an authorized anonymous EEG `input_manifest.json` and real-data regression passes.
2. The accepted E2E is based on a 60 s, 5-channel synthetic EDF.
3. Large EDF and 1GB-class performance are not yet accepted.
4. Trial account/permission matrix still needs broader coverage.
5. Legacy pages outside the active v0.1 epilepsy path may still need copy/visual sweep.
6. The synchronized spectrogram is evidence for the current epilepsy workbench window. It is not a formal PSD/TFR/Band Power module output unless separately contracted.

## Support Checklist During Trial

If the customer says upload failed:

1. Confirm upload authorization checkbox was selected.
2. Confirm the file is EDF for this v0.1 path.
3. Check API reachability at `/api/health`.
4. Capture browser URL and timestamp.

If the customer says screening cannot start:

1. Confirm Data Preparation has been confirmed.
2. Confirm the workbench uses `epilepsy_ml_xgboost`.
3. Confirm task payload includes data-preparation plan id, revision, and contract version.

If the customer says results are missing:

1. Confirm the task reached `completed`.
2. Confirm artifact binding is scoped to the current `task_<id>`.
3. Confirm Results page shows the review package.
4. Confirm report package includes event timeline and spectrogram figures.

If the customer says the system is making medical claims:

1. Stop the trial script.
2. Record the exact page/copy/screenshot.
3. Fix wording before continuing.
4. The correct wording is research support, candidate event, manual review, and event correction.

## Refresh Commands

Cloud E2E refresh:

```powershell
$env:QLANALYSER_FRONTEND_URL='http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=e2e-refresh-20260701a#storage'
$env:QLANALYSER_API_BASE_URL='http://39.97.248.225/api'
$env:QLANALYSER_EPILEPSY_UPLOAD_E2E_DIR='work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh'
node scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs
```

Strict gate refresh:

```powershell
$env:QLANALYSER_CLOUD_FRONTEND_URL='http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=e2e-refresh-20260701a#storage'
$env:QLANALYSER_CLOUD_API_BASE_URL='http://39.97.248.225/api'
$env:QLANALYSER_REQUIRE_CLOUD='1'
node scripts/validate_epilepsy_cloud_trial_v0_1_release_gate.mjs
node scripts/build_epilepsy_cloud_trial_readiness_packet.mjs
```

Formal external release commands after owner/data steward input:

```powershell
node scripts/validate_epilepsy_owner_data_manifest_v0_1.mjs
python -X utf8 scripts/run_real_dataset_regression_from_manifest.py
node scripts/validate_epilepsy_cloud_trial_v0_1_release_gate.mjs
node scripts/build_epilepsy_cloud_trial_readiness_packet.mjs
```

## Rollback / Stop Conditions

Stop the customer trial and roll back to internal-only if any of the following happens:

- cloud E2E fails;
- uploaded EDF cannot complete Data Preparation;
- screening task fails or does not publish artifacts;
- Results package is missing event timeline or spectrogram figures;
- UI copy says diagnosis, treatment, triage, or epilepsy staging;
- source ML artifacts are modified by manual review;
- review export fails;
- customer uploads real data without explicit authorization and trial scope agreement.

## Trial Script For Demonstration

1. Open the trial link.
2. Upload `regular_epilepsy_labeled_60s.edf`.
3. Confirm upload authorization.
4. Confirm Data Preparation.
5. Enter the epilepsy-like event workbench.
6. Check that waveform appears first.
7. Click start screening.
8. Wait for progress to reach completed.
9. Open the candidate event around 25.0-35.0 s.
10. Demonstrate one manual correction.
11. Save/export the review version.
12. Open Results and show the event timeline and spectrogram figures.
13. Say: "This is a research-support candidate event workflow, not a diagnostic result."

## Final Customer-Trial Verdict

```text
customer_trial_handoff = ready
cloud synthetic EDF RC = ready_for_acceptance
formal external release = blocked_owner_manifest_missing_or_invalid
```

## Next Real Artifacts

For customer trial:

```text
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_customer_trial_handoff_20260701.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_customer_trial_support_packet_20260701.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_trial_day_operator_card_20260701.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_trial_issue_log_template_20260701.md
work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh/browser_upload_to_export.json
```

For formal external release:

```text
work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json
work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/real_dataset_regression_result.json
```
