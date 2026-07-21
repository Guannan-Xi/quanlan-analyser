# QLanalyser Epilepsy-Like Event Screening Cloud Trial v0.1 Cutover Runbook

Status: ready for cloud target input; not yet approved for cloud trial RC or external release.

Scope: this runbook covers only the v0.1 epilepsy-like event screening trial path: browser upload, data preparation confirmation, epilepsy-like event screening, waveform/STFT/Stage_Code/candidate event review, manual correction, review save, Results export, and non-medical research-support boundary.

Out of scope for v0.1 P0: sleep staging, synchronized video analysis, diagnosis, treatment recommendation, clinical triage, and any fake video placeholder.

## 1. Required Inputs

Cloud/deployment owner must provide:

```text
QLANALYSER_CLOUD_FRONTEND_URL=<non-local cloud or staging frontend URL>
QLANALYSER_CLOUD_API_BASE_URL=<non-local cloud or staging API base URL>
```

The API base URL must expose `/health`.

Owner/data steward must provide:

```text
work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json
```

The manifest must describe authorized anonymized EEG data. It must not include PHI, and it must keep QLanalyser in research-support scope.

## 2. Local Baseline Before Cloud Run

Run the local baseline only to confirm the code path is healthy. Passing local baseline does not approve cloud trial RC.

```powershell
node scripts/validate_epilepsy_child_page_p0_contract.mjs
node scripts/validate_epilepsy_cloud_trial_v0_1_copy_governance.mjs
node scripts/e2e_epilepsy_failure_states_browser.mjs
node scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs
node scripts/build_epilepsy_cloud_trial_readiness_packet.mjs
```

Expected local state:

- child page contract: passed
- copy governance: passed
- failure states: passed
- browser upload-to-export: passed 29/29
- readiness: `not_ready` until cloud and owner data evidence exist

## 3. Cloud Trial RC Run

Set the cloud target in the same shell:

```powershell
$env:QLANALYSER_CLOUD_FRONTEND_URL="<cloud_or_staging_frontend_url>"
$env:QLANALYSER_CLOUD_API_BASE_URL="<cloud_or_staging_api_url>"
node scripts/run_epilepsy_cloud_trial_acceptance.mjs
```

Expected evidence:

```text
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-target-preflight/preflight_result.json
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-acceptance-run/acceptance_run.json
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-release-gate/release_gate_result.json
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-readiness/readiness_packet.json
```

Cloud RC can be accepted only if:

- cloud preflight passes with non-local frontend and API URLs;
- cloud browser upload-to-export E2E passes all 29 required checks;
- strict release gate no longer reports `blocked_cloud_trial_e2e_missing`;
- the UI still uses "癫痫样事件初筛 / 候选事件 / 人工复核 / 事件修正";
- the UI does not expose "癫痫分期", diagnosis, treatment, triage, fake video placeholder copy, or old English review labels.

## 4. Owner Real-Data Regression

After the data steward provides `input_manifest.json`, run:

```powershell
node scripts/validate_epilepsy_owner_data_manifest_v0_1.mjs
python -X utf8 scripts/run_real_dataset_regression_from_manifest.py
node scripts/validate_epilepsy_cloud_trial_v0_1_release_gate.mjs
node scripts/build_epilepsy_cloud_trial_readiness_packet.mjs
```

External release can be accepted only if:

- owner manifest contract passes;
- real anonymized EEG regression passes;
- release gate no longer reports `blocked_owner_manifest_missing_or_invalid`;
- readiness packet reports no blocker for owner data manifest or owner data regression.

## 5. Failure Handling

If cloud preflight fails:

- verify the frontend URL is not localhost or 127.0.0.1;
- verify the API URL is not localhost or 127.0.0.1;
- verify `/health` is reachable from the test machine;
- rerun `node scripts/preflight_epilepsy_cloud_trial_target.mjs`.

If browser E2E fails:

- inspect `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json`;
- check the `failed` list and screenshots before changing code;
- do not weaken required checks to make the gate pass.

If owner manifest validation fails:

- fix the manifest, not the validator, unless the validator contradicts the approved data contract;
- keep `qc` out of `allowed_methods`;
- keep PHI out of the manifest;
- record any excluded dataset reason in the owner packet.

## 6. Stop Conditions

Stop and do not approve cloud trial RC if:

- cloud target is missing;
- cloud upload-to-export evidence is missing;
- cloud E2E is local-only;
- any required 29 cloud browser checks are missing or false;
- non-medical boundary copy is missing or contradicted.

Stop and do not approve external release if:

- owner manifest is missing;
- manifest contract fails;
- real-data regression is missing or fails;
- any release gate reports a blocker.

## 7. Final Receipts

Use one of these receipts:

```text
completed_epilepsy_cloud_trial_v0_1_cloud_rc_ready_for_owner_review
partial_epilepsy_cloud_trial_v0_1_local_pass_cloud_target_missing
blocked_epilepsy_cloud_trial_v0_1_owner_manifest_missing
blocked_epilepsy_cloud_trial_v0_1_cloud_e2e_failed
blocked_epilepsy_cloud_trial_v0_1_owner_regression_failed
```

Do not use `completed` unless the required evidence for that release level exists and has been read back.

## Change Log

- 2026-06-30: Created cloud cutover runbook from current v0.1 gate scripts and evidence paths.
