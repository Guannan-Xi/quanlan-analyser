# QLanalyser Epilepsy-Like Event Screening Cloud Trial v0.1 - Trial Day Operator Card

Status: `trial_day_operator_card_ready`; `cloud_synthetic_edf_rc_ready_for_acceptance`; `formal_external_release_blocked_owner_manifest_missing_or_invalid`.

Date: 2026-07-01

## One-Sentence Boundary

This is a research-support workflow for epilepsy-like candidate event screening and manual review. It is not a diagnostic result.

## Open

Trial URL:

```text
http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=e2e-refresh-20260701a#storage
```

Synthetic EDF:

```text
D:\Quanlan\Codes\Python\quanlan-analyser-official\work\fixtures\epilepsy_regular_labeled\regular_epilepsy_labeled_60s.edf
```

Expected result:

```text
Stage_Code = 000001100000
Candidate event = 25.0-35.0 s
Report package has event timeline and spectrogram figures
```

## Before Customer Joins

1. Open the trial URL.
2. Confirm the page loads.
3. Confirm API base is `http://39.97.248.225/api`.
4. Confirm the synthetic EDF path is available.
5. Keep this sentence ready: "This is research support, not diagnosis."

## Demo Steps

1. Upload `regular_epilepsy_labeled_60s.edf`.
2. Confirm upload authorization.
3. Confirm Data Preparation.
4. Enter the epilepsy-like event workbench.
5. Show waveform-first view.
6. Click Start screening.
7. Wait for progress to reach completed.
8. Show candidate event around 25.0-35.0 s.
9. Show Stage_Code overlay and synchronized spectrogram.
10. Demonstrate one manual correction.
11. Save/export review version.
12. Open Results.
13. Show event timeline and spectrogram figures.

## Say

Use:

- "candidate event"
- "manual review"
- "review-layer correction"
- "research-support evidence"
- "source ML outputs remain read-only"

Avoid:

- diagnosis
- treatment
- triage
- epilepsy staging
- clinical decision
- real-data performance claim

## If Something Fails

Upload fails:

1. Check upload authorization.
2. Check EDF file.
3. Check API base.
4. Do not improvise with customer real data.

Screening fails:

1. Confirm Data Preparation was completed.
2. Capture task id and error.
3. Switch to accepted evidence screenshots if needed.

Results missing:

1. Confirm review export completed.
2. Refresh Results once.
3. Capture screenshot and stop live retry loops.

Medical wording appears:

1. Stop.
2. Capture screenshot.
3. Do not continue until wording is fixed.

## Stop Immediately If

- Customer wants to upload real data without approved data scope.
- Any PHI appears.
- The system implies diagnosis, treatment, triage, or epilepsy staging.
- Manual correction modifies source ML artifacts.
- Results/report figures cannot be produced.

## After Demo

Save:

```text
customer name
trial time
uploaded file name
task id
review/export id
Results screenshot
issues
customer feedback
go/no-go decision
```

## Final Operator Verdict

```text
operator_card = ready
cloud synthetic EDF customer trial = ready_for_acceptance
formal external release = blocked_owner_manifest_missing_or_invalid
```
