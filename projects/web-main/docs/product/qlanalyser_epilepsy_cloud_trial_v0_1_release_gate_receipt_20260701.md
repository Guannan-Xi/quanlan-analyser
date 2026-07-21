# QLanalyser Epilepsy-Like Event Screening Cloud Trial v0.1 - Release Gate Receipt

Status: `cloud_trial_rc_ready_for_acceptance`; `external_release_blocked_owner_manifest_missing_or_invalid`.

Date: 2026-07-01

Last updated: 2026-07-01 11:50 Asia/Shanghai

## Scope

This receipt records the latest release-gate readback for the QLanalyser epilepsy-like event screening cloud trial v0.1.

The accepted trial scope remains:

- EDF upload by a trial user.
- Data preparation confirmation before screening.
- Epilepsy-like event screening, not epilepsy staging.
- Candidate event detection, manual review/correction, review export.
- Results-module readback with non-medical research-support wording.

The trial scope still excludes clinical diagnosis, treatment recommendation, medical triage, sleep staging, respiratory scoring, and video analysis.

## Evidence Read Back

### Local browser E2E

Path:

```text
work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/browser_upload_to_export.json
```

Result:

```text
status = passed
checks = 34 / 34 passed
```

### Cloud browser E2E

Path:

```text
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json
```

Result:

```text
status = passed
target = http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=e2e-rc-final-clean-20260701f#storage
checks = 34 / 34 passed
```

### Release gate

Path:

```text
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-release-gate/release_gate_result.json
```

Latest readback:

```json
{
  "release_verdict": "cloud_release_candidate_ready_for_acceptance",
  "cloud_trial_rc_verdict": "cloud_trial_rc_ready_for_acceptance",
  "external_release_verdict": "blocked_owner_manifest_missing_or_invalid"
}
```

### Readiness packet

Path:

```text
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-readiness/readiness_packet.json
```

Latest readback:

```json
{
  "status": "not_ready",
  "internal_local_status": "passed",
  "cloud_trial_rc_status": "ready_for_acceptance",
  "external_release_status": "blocked_owner_manifest_missing_or_invalid",
  "blockers": [
    "owner_data_manifest_contract",
    "owner_data_regression"
  ]
}
```

## Gate Adjustment

The release-gate script now separates two concepts:

1. Whether non-local cloud E2E evidence already exists and passed.
2. Whether the current shell has cloud target environment variables for an immediate rerun.

The cloud release-candidate verdict is based on verified non-local evidence, not on whether the current shell still has the rerun environment variables set.

Changed file:

```text
scripts/validate_epilepsy_cloud_trial_v0_1_release_gate.mjs
```

## 2026-07-01 Cloud Result-Load Fix

During cloud rerun, the backend completed the epilepsy-like event screening task and registered all expected artifacts, but the inline workbench initially failed to load results because the frontend artifact selector could match upstream data-preparation artifacts before the current epilepsy task artifacts.

Root cause:

```text
frontend/app.js artifact selection matched labels/paths too loosely across the whole task artifact list.
The /tasks/{task_id}/artifacts response can include data-preparation artifacts before epilepsy outputs.
```

Fix:

- Added current-task scoped artifact matching for inline epilepsy results.
- Excluded `data_preparation` artifacts from epilepsy result loading.
- Preferred current `task_<id>` outputs:
  - `tables/epilepsy_ml_epoch_predictions.csv`
  - `tables/epilepsy_ml_events.csv`
  - `data/epilepsy_ml_spectrogram.json`
- Published E2E state after review export and refreshed the Results delivery surface.

Changed file:

```text
frontend/app.js
```

Verification:

```text
node --check frontend/app.js
node scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs
cloud browser E2E with target http://39.97.248.225 ... v=e2e-rc-final-clean-20260701f#storage
node scripts/validate_epilepsy_cloud_trial_v0_1_release_gate.mjs
node scripts/build_epilepsy_cloud_trial_readiness_packet.mjs
```

Verified cloud behavior:

- EDF upload requires authorization and persists authorization readback.
- Data preparation plan is confirmed before screening.
- Epilepsy-like event screening task uses `epilepsy_ml_xgboost`.
- Result loading binds Stage_Code, candidate events, and PC-compatible STFT spectrogram from the same task.
- Manual review/correction saves to backend review session.
- Review export registers review-layer artifacts without modifying source ML artifacts.
- Results module shows review package and result images.
- Report package includes event timeline and spectrogram images.
- No "epilepsy staging", diagnosis, treatment, medical triage, or video placeholder copy appears.

## Current Verdict

```text
cloud synthetic EDF trial path: ready_for_acceptance
formal external release: blocked
```

The formal external release remains blocked until an owner/data steward provides an authorized anonymous EEG `input_manifest.json`, and the real-data regression passes.

## Verification Commands

```powershell
node --check scripts/validate_epilepsy_cloud_trial_v0_1_release_gate.mjs
node scripts/validate_epilepsy_cloud_trial_v0_1_release_gate.mjs
node scripts/build_epilepsy_cloud_trial_readiness_packet.mjs
```

## Next Real Artifact

For cloud trial acceptance:

```text
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json
```

For formal external release:

```text
work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json
work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/real_dataset_regression_result.json
```
