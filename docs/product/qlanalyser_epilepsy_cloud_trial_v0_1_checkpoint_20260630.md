# QLanalyser Epilepsy-Like Event Screening Cloud Trial v0.1 Checkpoint

Status: local synthetic E2E passed; cloud synthetic EDF customer-trial RC ready for acceptance after 2026-07-01 cloud refresh; formal external release blocked pending owner-data manifest and real-data regression.

Scope: epilepsy-like event screening cloud trial v0.1. This checkpoint preserves the product wording "癫痫样事件初筛 / 候选事件 / 人工复核 / 事件修正" and explicitly excludes sleep staging, video analysis, clinical diagnosis, treatment recommendation, and medical triage from P0.

## Sources Used

- `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_requirements_20260629.md`
- `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_architecture_20260629.md`
- `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_detailed_design_20260629.md`
- `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_data_api_contract_20260629.md`
- `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_e2e_test_plan_20260629.md`
- `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_release_plan_20260629.md`
- `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/browser_upload_to_export.json`
- `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-failure-states/failure_states_browser.json`
- `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-copy-governance/copy_governance_result.json`
- `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-release-gate/release_gate_result.json`
- `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-readiness/readiness_packet.json`
- `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-owner-input-packet/owner_input_packet.md`
- `work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh/browser_upload_to_export.json`
- `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_cloud_refresh_acceptance_20260701.md`
- `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_customer_trial_handoff_20260701.md`
- `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_customer_trial_support_packet_20260701.md`
- `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_trial_day_operator_card_20260701.md`
- `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_trial_issue_log_template_20260701.md`

## Current Verified State

Local synthetic browser upload-to-export E2E passed 29/29 against `http://127.0.0.1:4174/` and `http://127.0.0.1:8001/api`.

Failure-state browser E2E passed 6/6, including upload authorization, unconfirmed preparation, forced screening failure, artifact load failure, review-save failure, and export failure.

Scoped copy governance passed. Customer-facing UI keeps epilepsy as event screening and review, not staging. The customer surface does not expose diagnosis, treatment, triage, fake video placeholder copy, or old English review labels.

The synthetic labeled EDF fixture exists at `work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_60s.edf`. The local E2E verifies `Stage_Code = 000001100000` and the candidate event at 25.0-35.0s.

The 2026-07-01 non-local cloud browser refresh passed 34/34 checks against:

```text
http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=e2e-refresh-20260701a#storage
```

The cloud refresh starts from EDF upload and reaches Data Preparation, `epilepsy_ml / epilepsy_ml_xgboost` screening, manual correction, review export, Results image readback, and report package image inclusion.

The customer-trial handoff is now available for guided trial delivery:

```text
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_customer_trial_handoff_20260701.md
```

The customer-trial support packet is now available for trial ownership, preflight, issue severity, stop conditions, session logging, and feedback collection:

```text
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_customer_trial_support_packet_20260701.md
```

Trial-day compact materials are now available:

```text
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_trial_day_operator_card_20260701.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_trial_issue_log_template_20260701.md
```

## Current Blockers

Cloud synthetic EDF customer-trial RC is no longer blocked by missing cloud target evidence. The accepted cloud RC evidence is:

```text
work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh/browser_upload_to_export.json
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_cloud_refresh_acceptance_20260701.md
```

External release remains blocked because `work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json` is missing. Without the owner/data steward manifest, the real anonymized EEG regression cannot run.

## Required Owner Inputs

Cloud/deployment owner has provided a current reachable target for the synthetic EDF customer-trial RC:

- `QLANALYSER_CLOUD_FRONTEND_URL = http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=e2e-refresh-20260701a#storage`
- `QLANALYSER_CLOUD_API_BASE_URL = http://39.97.248.225/api`

To refresh cloud evidence, run:

```powershell
$env:QLANALYSER_FRONTEND_URL='http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=e2e-refresh-20260701a#storage'
$env:QLANALYSER_API_BASE_URL='http://39.97.248.225/api'
$env:QLANALYSER_EPILEPSY_UPLOAD_E2E_DIR='work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh'
node scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs
```

Owner/data steward must provide:

- `work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json`

Then run:

```powershell
node scripts/validate_epilepsy_owner_data_manifest_v0_1.mjs
python -X utf8 scripts/run_real_dataset_regression_from_manifest.py
node scripts/validate_epilepsy_cloud_trial_v0_1_release_gate.mjs
node scripts/build_epilepsy_cloud_trial_readiness_packet.mjs
```

## Acceptance Mapping

| Requirement | Current evidence | Status |
| --- | --- | --- |
| Browser user can upload EDF with authorization | local browser E2E | Passed locally |
| Data Preparation must be confirmed before screening | local browser E2E and failure-state E2E | Passed locally |
| Screening payload carries preparation contract fields | local browser E2E request capture | Passed locally |
| Waveform-first epilepsy child page inside main navigation | local browser E2E and static contract | Passed locally |
| STFT panel follows the same waveform window source | local browser E2E | Passed locally |
| Stage_Code overlay and candidate event truth | local browser E2E | Passed locally |
| Manual review/correction and review export | local browser E2E | Passed locally |
| Results page shows review package | local browser E2E | Passed locally |
| Failure states show visible feedback | failure-state browser E2E | Passed locally |
| Cloud/staging upload-to-export E2E | 20260701 cloud browser E2E 34/34 | Ready for acceptance for synthetic RC |
| Owner anonymized real-data regression | missing input manifest | Blocked |

## Change Log

- 2026-06-30: Captured the current local acceptance state and external blockers after rerunning local contract, copy, failure-state, upload-to-export, release-gate, readiness, cloud-preflight, cloud-acceptance wrapper, owner-manifest, and owner-input packet scripts.
- 2026-07-01: Synced checkpoint after non-local cloud browser refresh passed 34/34. Cloud synthetic EDF customer-trial RC is ready for acceptance; formal external release remains blocked by owner manifest / real-data regression.
- 2026-07-01: Added customer-trial handoff package with trial link, synthetic EDF path, expected workflow, customer boundary, support checklist, refresh commands, and stop conditions.
- 2026-07-01: Added customer-trial support packet with trial ownership, pre-trial checklist, severity levels, session log template, feedback questions, recovery playbook, and go/no-go criteria.
- 2026-07-01: Added trial-day operator card and issue log template for live customer trial execution.

## Next Real Artifact

For customer-trial acceptance:

```text
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_customer_trial_handoff_20260701.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_customer_trial_support_packet_20260701.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_trial_day_operator_card_20260701.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_trial_issue_log_template_20260701.md
work/release_evidence/20260701-epilepsy-cloud-trial-v0-1-cloud-upload-to-export-refresh/browser_upload_to_export.json
```

For formal external release:

```text
work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/real_dataset_regression_result.json
```
