# QLanalyser Epilepsy-Like Event Screening Cloud Trial v0.1 - Trial Issue Log Template

Status: `trial_issue_log_template_ready`.

Date: 2026-07-01

## Session Metadata

| Field | Value |
| --- | --- |
| Trial date/time |  |
| Customer / organization |  |
| Trial owner |  |
| Technical operator |  |
| Product reviewer |  |
| Support owner |  |
| Cloud URL |  |
| API base |  |
| Dataset | Synthetic EDF / other |
| File name |  |
| File authorization confirmed | Yes / No |

## Flow Checklist

| Step | Pass/Fail | Notes |
| --- | --- | --- |
| Page opens |  |  |
| Upload completes |  |  |
| Upload authorization persisted |  |  |
| Data Preparation confirmed |  |  |
| Workbench opens inside main navigation |  |  |
| Waveform-first view visible |  |  |
| Start screening clicked |  |  |
| Progress reaches completed |  |  |
| Candidate event visible |  |  |
| Stage_Code overlay visible |  |  |
| Spectrogram visible and synchronized |  |  |
| Manual correction demonstrated |  |  |
| Review/export completed |  |  |
| Results package visible |  |  |
| Event timeline figure visible |  |  |
| Spectrogram figure visible |  |  |
| Non-medical wording preserved |  |  |

## Task / Artifact Readback

| Field | Value |
| --- | --- |
| Uploaded file id |  |
| Data preparation plan id |  |
| Data preparation revision |  |
| Task id |  |
| Module name | `epilepsy_ml` |
| Workflow id | `epilepsy_ml_xgboost` |
| Task status |  |
| Task progress |  |
| Review session id |  |
| Export/report id |  |
| Event timeline figure present | Yes / No |
| Spectrogram figure present | Yes / No |

## Issue Log

| Issue id | Severity | Area | Description | Evidence path/screenshot | Owner | Decision |
| --- | --- | --- | --- | --- | --- | --- |
|  | S0 / S1 / S2 / S3 | Upload / Preparation / Workbench / Screening / Review / Results / Copy / Performance |  |  |  | Continue / pause / stop |

## Severity Rules

| Severity | Meaning | Action |
| --- | --- | --- |
| S0 | Trust, data safety, medical boundary, or source-output integrity risk. | Stop trial immediately. |
| S1 | Core flow cannot complete. | Stop or switch to accepted evidence; fix before next trial. |
| S2 | Flow completes but customer confusion is likely. | Continue only with explanation; fix before wider trial. |
| S3 | Cosmetic/non-blocking issue. | Record for polish. |

## Customer Feedback

| Question | Customer answer |
| --- | --- |
| Was upload-to-review flow understandable? |  |
| Did waveform-first review match EEG inspection expectations? |  |
| Was algorithm candidate vs manual review clear? |  |
| Were event timeline and spectrogram figures useful? |  |
| Which step felt slow or confusing? |  |
| What output is needed before using authorized anonymous real data? |  |

## Final Session Decision

| Decision | Value |
| --- | --- |
| Continue customer trial program | Yes / No |
| Needs fix before next trial | Yes / No |
| Requires owner/data steward input | Yes / No |
| Formal external release discussed | No by default |
| Notes |  |

## Boundary Reminder

Do not use this issue log to claim diagnosis, treatment, clinical triage, epilepsy staging, GLP readiness, or real-data efficacy.
