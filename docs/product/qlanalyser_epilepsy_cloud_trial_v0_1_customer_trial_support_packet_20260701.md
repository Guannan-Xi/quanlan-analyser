# QLanalyser Epilepsy-Like Event Screening Cloud Trial v0.1 - Customer Trial Support Packet

Status: `customer_trial_support_packet_ready`; `cloud_synthetic_edf_rc_ready_for_acceptance`; `formal_external_release_blocked_owner_manifest_missing_or_invalid`.

Date: 2026-07-01

## Purpose

This packet controls the guided customer trial after the technical cloud RC has passed. It defines who may run the trial, what must be checked before the session, how issues are recorded, when to stop, and what evidence must be collected after the session.

This packet does not approve formal external release. It supports a controlled customer trial using the accepted synthetic EDF path.

## Trial Ownership

| Role | Responsibility |
| --- | --- |
| Trial owner | Confirms the customer, trial window, scope, and stop conditions. |
| Technical operator | Runs preflight, uploads the synthetic EDF if needed, monitors task/result behavior, and captures evidence. |
| Product reviewer | Checks wording, workflow clarity, and customer confusion points. |
| Data steward | Provides owner-approved anonymous real EEG manifest only for formal release regression, not for the synthetic trial. |
| Support owner | Receives customer issues and classifies severity. |

## Pre-Trial Checklist

Run this checklist before showing the trial to a customer.

| Check | Required result | Evidence |
| --- | --- | --- |
| Cloud URL opens | QLanalyser loads without dashboard fallback or blank page. | Browser screenshot or E2E opened screenshot. |
| API reachable | `/api/health` responds. | Browser/network/API readback. |
| Synthetic EDF exists | `regular_epilepsy_labeled_60s.edf` exists locally. | File path/readback. |
| Latest cloud E2E | 34/34 checks pass or a recent passing evidence packet is accepted. | `browser_upload_to_export.json`. |
| Release gate | `cloud_trial_rc_ready_for_acceptance`. | `release_gate_result.json`. |
| Readiness packet | `cloud_trial_rc_status=ready_for_acceptance`. | `readiness_packet.json`. |
| Product boundary | No diagnosis, treatment, triage, or epilepsy staging wording. | Copy/governance or browser evidence. |
| Result images | Event timeline and spectrogram figures are present. | Report package/readback. |

## Customer Trial Entry

Use this URL for the guided trial:

```text
http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=e2e-refresh-20260701a#storage
```

Synthetic EDF:

```text
D:\Quanlan\Codes\Python\quanlan-analyser-official\work\fixtures\epilepsy_regular_labeled\regular_epilepsy_labeled_60s.edf
```

Approved demo sentence:

```text
This is a research-support workflow for epilepsy-like candidate event screening and manual review. It is not a diagnostic result.
```

## Supported Trial Flow

1. Open the trial link.
2. Upload the synthetic EDF.
3. Confirm upload authorization.
4. Confirm Data Preparation.
5. Enter the epilepsy-like event workbench.
6. Confirm waveform-first view.
7. Start screening.
8. Wait until progress reaches completed.
9. Review the candidate event around 25.0-35.0 s.
10. Demonstrate one manual correction.
11. Save/export the review version.
12. Open Results.
13. Confirm event timeline and spectrogram figures.

Do not use customer real EEG during this synthetic trial unless the trial owner and data steward have explicitly approved the data-handling scope.

## Trial-Day Materials

Use these compact materials during the live session:

```text
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_trial_day_operator_card_20260701.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_trial_issue_log_template_20260701.md
```

## Issue Severity

| Severity | Definition | Examples | Action |
| --- | --- | --- | --- |
| S0 stop trial | Customer trust, data safety, medical-scope, or source-output integrity risk. | Diagnosis wording, treatment advice, source ML artifact modified by review, unauthorized real data upload. | Stop immediately, capture evidence, fix before next trial. |
| S1 blocker | Core flow cannot complete. | Upload fails, Data Preparation cannot confirm, screening cannot start, task fails, export missing. | Stop the session or switch to recorded evidence; create fix ticket. |
| S2 major | Flow completes but customer may misunderstand. | Duplicate controls, unclear progress, candidate event not visually obvious, Results package hard to find. | Continue only if explained; fix before wider trial. |
| S3 minor | Cosmetic or wording issue that does not affect trust or result meaning. | Spacing, low-priority copy polish, non-blocking icon alignment. | Record for next polish pass. |

## Stop Conditions

Stop the trial if any of these happen:

- The cloud app fails to load.
- The uploaded EDF cannot be prepared.
- Screening task fails or stays incomplete.
- Results/report package cannot show event timeline and spectrogram figures.
- UI or operator wording implies diagnosis, treatment, triage, or epilepsy staging.
- Manual correction modifies source ML outputs instead of review-layer outputs.
- Customer wants to upload real data before authorization scope is confirmed.
- Any PHI or personal data appears in a screen, filename, artifact, or exported report.

## Trial Session Log Template

Use one row per customer session.

| Field | Value |
| --- | --- |
| Trial date/time |  |
| Customer / organization |  |
| Operator |  |
| Cloud URL |  |
| API base |  |
| Dataset | Synthetic EDF / other |
| File name |  |
| Upload authorization confirmed | Yes / No |
| Data Preparation confirmed | Yes / No |
| Screening task id |  |
| Workflow id | `epilepsy_ml_xgboost` |
| Candidate event visible | Yes / No |
| Manual correction demonstrated | Yes / No |
| Export package visible in Results | Yes / No |
| Event timeline figure visible | Yes / No |
| Spectrogram figure visible | Yes / No |
| Customer questions |  |
| Issues found |  |
| Severity | S0 / S1 / S2 / S3 / none |
| Follow-up owner |  |
| Decision | Continue / pause / stop |

## Customer Feedback Questions

Ask after the demo:

1. Could you understand the path from upload to review/export?
2. Did the waveform-first workbench match how you expect to inspect EEG?
3. Was the difference between algorithm candidate and manual review clear?
4. Were the event timeline and spectrogram figures useful?
5. Which step felt slow, confusing, or unnecessary?
6. What output would you need before trying this with your own authorized anonymous data?

Do not ask the customer to judge clinical correctness in this v0.1 synthetic trial.

## Evidence To Save After Each Trial

Required:

```text
browser URL
trial timestamp
uploaded file name
task id
review/export id if available
Results screenshot
event timeline / spectrogram report package evidence
issue log if any
```

Optional but useful:

```text
browser console errors
network waterfall for slow sessions
customer feedback notes
operator observations
```

## Recovery Playbook

If upload fails:

1. Confirm authorization checkbox.
2. Confirm file is the synthetic EDF.
3. Confirm API base is `http://39.97.248.225/api`.
4. Re-run cloud E2E only after the session.

If screening fails:

1. Confirm Data Preparation was confirmed.
2. Confirm task payload uses `epilepsy_ml_xgboost`.
3. Capture task id and error message.
4. Do not retry repeatedly in front of the customer.

If Results are missing:

1. Confirm review export completed.
2. Confirm task id and review id.
3. Use the latest accepted evidence as fallback for demo discussion.
4. File an S1 issue if the live path cannot recover.

If wording crosses medical boundary:

1. Stop the trial.
2. Capture screenshot and text.
3. Replace wording with research-support / candidate event / manual review terms.
4. Re-run copy governance before the next customer trial.

## Go / No-Go Criteria For The Next Trial

Go if:

- latest cloud E2E remains passing;
- release gate remains `cloud_trial_rc_ready_for_acceptance`;
- no open S0 or S1 issue exists;
- all customer-facing wording stays in research-support scope;
- support owner is available during the trial window.

No-go if:

- cloud E2E fails;
- S0 or unresolved S1 issue exists;
- operator cannot show Results/report images;
- customer insists on real data before data authorization scope is ready;
- owner/data steward has not approved real-data handling and the trial needs real data.

## Relationship To Formal External Release

The customer trial can proceed with the synthetic EDF RC evidence.

Formal external release still requires:

```text
work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json
work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/real_dataset_regression_result.json
```

Do not merge these two release levels in customer communication.

## Final Support Verdict

```text
customer_trial_support_packet = ready
trial_day_operator_card = ready
trial_issue_log_template = ready
cloud synthetic EDF customer trial = ready_for_acceptance
formal external release = blocked_owner_manifest_missing_or_invalid
```
