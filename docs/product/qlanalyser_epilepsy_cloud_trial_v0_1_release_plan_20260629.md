# QLanalyser Epilepsy-like Event Screening Cloud Trial v0.1 - Release Plan

Status: document synced 2026-07-01; cloud synthetic EDF trial RC ready for acceptance; external formal release still requires owner-approved anonymous real EEG regression.

## Release Name

QLanalyser Epilepsy-like Event Screening Cloud Trial v0.1

Chinese product wording:

QLanalyser 癫痫样事件初筛云端试用版 v0.1

## Phase Plan

### P0-A Spec Freeze

Exit criteria:

- goal document created
- requirements created
- architecture created
- detailed design created
- data/API contract created
- E2E test plan created
- release plan created
- terminology contract linked

### P0-B Local Implementation Closure

Exit criteria:

- ordinary uploaded/synthetic EDF path works locally
- data preparation gate passes
- Start Screening runs real backend workflow
- waveform, Stage_Code, event table, spectrogram show synchronized evidence
- manual review saves revision
- Results/export path works locally
- local E2E evidence generated

### P0-C Cloud Trial/Staging Closure

Exit criteria:

- cloud trial environment reachable
- login/trial account works
- upload starts from UI
- synthetic labeled EDF E2E passes from upload to export
- failure handling and support path visible
- no medical wording

### P0-D Internal Trial

Exit criteria:

- internal users can complete the full flow without developer help
- no P0 blockers
- operation guide available
- issue capture path available

### P0-E Friendly Customer Trial

Exit criteria:

- internal trial passed
- friendly customer account configured
- upload authorization confirmation works
- error/support path works
- trial guide available

Note: v0.1 customer-trial release planning must not claim P0-E as already available unless a separate customer-trial acceptance packet exists.

For v0.1, keep P0-E as a future phase label unless the trial package is explicitly re-baselined.
## P1 Candidates

- PDF/HTML report package
- batch upload/export
- larger EDF performance hardening
- 1-64 channel broad regression
- authorized anonymous real data regression
- GLP-oriented audit expansion
- richer spectrogram/band power evidence
- sleep staging separate release track
- real synchronized video support only when data includes video

## Release Blockers

Blocks internal cloud trial:

- upload path fails
- data preparation gate fails
- Start Screening no feedback or no real task
- synthetic fixture truth mismatch
- waveform/result evidence missing
- manual review cannot save
- export missing
- diagnostic/medical wording appears

Blocks friendly customer trial:

- internal trial not passed
- upload authorization confirmation missing
- basic support/error path missing
- no operation guide

Blocks external formal release:

- no authorized anonymous real data regression
- no performance boundary report
- no security/permission review
- incomplete audit/export report

## Rollback

If the cloud trial fails:

- disable external trial account access
- keep internal staging accessible for debugging
- preserve uploaded test data and evidence paths unless deletion is requested
- keep previous stable QLanalyser functions available
- do not expose diagnostic claims or incomplete exports

## Evidence Paths

Recommended:

```text
work/release_evidence/20260629-epilepsy-cloud-trial-v0-1/
work/release_evidence/20260629-regular-epilepsy-labeled-fixture/
```

Additional accepted evidence paths:

```text
work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-contract/upload_authorization_contract.json
work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-to-export/cloud_upload_to_export_contract.json
work/release_evidence/20260629-epilepsy-release-e2e/main_epilepsy_entry_real_path.json
work/release_evidence/20260629-epilepsy-release-e2e/03_inline_console_completed.png
```

## 2026-06-29 Release Status Update

Historical release status before cloud rerun: `internal_development_partial_pass_cloud_rc_blocked`.

Accepted for local development:

- backend upload authorization contract
- confirmed data preparation gate and strict plan lineage
- `epilepsy_ml_xgboost` workflow enforcement
- synthetic labeled EDF upload-to-export API acceptance
- v0.1 review export CSV/JSON contract
- main analysis page inline workbench local teaching/demo browser E2E

Historical blockers before 2026-07-01 cloud rerun:

- cloud/staging URL and trial account E2E
- browser upload-to-export path for ordinary uploaded EDF
- Results module package viewing
- cloud/staging UTF-8/customer copy governance; local scoped v0.1 copy governance has passed
- cloud/staging failure/loading/empty state browser coverage; local scoped failure-state E2E has passed
- cloud performance boundary
- authorized anonymous owner-data regression

The next release-gate artifact should be:

```text
work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/
```

It should be produced by the new browser E2E for ordinary upload-to-export and then reused against cloud/staging.

## Owner Decisions Captured

- v0.1 is cloud trial, not local-only.
- EDF upload path is mandatory.
- Epilepsy is event screening, not staging.
- Sleep staging is next phase.
- Video support is hidden unless real synchronized video exists.
- Single-file analysis/export is enough for v0.1.
- Data size limit is not promised before cloud measurement.
- Internal trial can proceed with synthetic fixture; external formal release requires authorized anonymous real data regression.

## Change Log

- 2026-06-29: Created v0.1 release plan baseline.
- 2026-06-30: Synced accepted local API/browser-demo evidence and kept cloud/trial-account RC blockers explicit.
- 2026-06-30: Added local browser upload-to-export interaction pass and cloud release-gate script evidence.
- 2026-06-30: Added scoped v0.1 copy governance, failure-state browser E2E, and stricter release-gate verdict split for cloud trial RC vs external formal release.

## 2026-06-30 Release Sync

Historical release status before cloud rerun: `internal_local_partial_pass_cloud_rc_blocked`.

Accepted local evidence:

- Upload authorization and data preparation gate.
- Strict plan lineage from confirmed preparation into `epilepsy_ml_xgboost` and review/export.
- Synthetic EDF upload-to-export API E2E.
- v0.1 export CSV/JSON contract.
- Main inline epilepsy-like event workbench local browser demo.

Historical release-candidate blockers before 2026-07-01 cloud rerun:

- Cloud/staging URL plus trial account E2E.
- Ordinary browser UI upload-to-export path.
- Results module opening the v0.1 export package.
- Failure states and customer-facing error copy.
- Full copy governance scan.
- Cloud performance boundary.
- Owner/steward approved anonymous real data regression.

Terminology and product boundary: release wording remains non-medical research-support "epilepsy-like event screening"; epilepsy must not be described as staging or 分期.

## 2026-06-30 Local Interaction Release Gate

Current release status: `local_browser_interaction_pass_cloud_e2e_blocked`.

Accepted local release evidence:

- Browser upload-to-export E2E passed 29/29:
  - `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/browser_upload_to_export.json`
- Static inline child-page contract passed 15/15:
  - `work/release_evidence/20260629-epilepsy-child-page-p0/static_epilepsy_child_page_contract.json`
- Scoped v0.1 copy governance passed:
  - `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-copy-governance/copy_governance_result.json`
- Failure-state browser E2E passed:
  - `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-failure-states/failure_states_browser.json`
- Readiness packet generated:
  - `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-readiness/readiness_packet.json`
- Cloud trial acceptance wrapper available:
  - `scripts/run_epilepsy_cloud_trial_acceptance.mjs`
  - output `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-acceptance-run/acceptance_run.json`
- Cloud target preflight available:
  - `scripts/preflight_epilepsy_cloud_trial_target.mjs`
  - output `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-target-preflight/preflight_result.json`
- Owner-data manifest contract validator available:
  - `scripts/validate_epilepsy_owner_data_manifest_v0_1.mjs`
  - output `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-owner-data-manifest/owner_data_manifest_contract.json`
- Owner/cloud input packet available:
  - `scripts/build_epilepsy_cloud_trial_owner_input_packet.mjs`
  - outputs `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-owner-input-packet/owner_input_packet.json` and `.md`
- Cloud release gate generated:
  - `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-release-gate/release_gate_result.json`

Accepted local scope:

- trial user path from browser EDF upload to data preparation, screening, review correction, export, and Results visibility;
- parent navigation and page title behavior inside the main QLanalyser shell;
- same-window waveform/STFT/Stage_Code/candidate-event interaction contract;
- non-medical research-support boundary in payload and export;
- customer-facing v0.1 terminology gate for event screening wording;
- visible failure feedback for missing authorization, unconfirmed preparation, forced screening failure, artifact load failure, review-save failure, and export failure.

Historical blockers before 2026-07-01 cloud rerun:

- no non-local cloud/staging frontend URL and API URL have been supplied in the evidence;
- the upload-to-export E2E has not yet been rerun against a real trial account and deployed storage/artifact environment;
- cloud latency for upload, metadata extraction, screening, artifact loading, review save, and export remains unmeasured;
- authorized anonymous owner-data regression remains outside the synthetic-fixture local pass.

Release gate semantics:

- `cloud_trial_rc_verdict` requires local E2E, static child-page contract, scoped copy governance, and non-local cloud browser upload-to-export evidence.
- It also requires local failure-state browser E2E coverage for the six scoped failure states before a cloud trial RC can be accepted.
- Non-local cloud browser evidence must include all 29 required upload-to-export checks; an empty or partial `checks` object is rejected.
- `external_release_verdict` additionally requires authorized owner-data regression.
- The readiness packet is the current handoff artifact for deployment/QA: it records `internal_local_status`, `cloud_trial_rc_status`, `external_release_status`, blockers, and next commands.
- The readiness packet also links the owner manifest template, owner input checklist, owner manifest validator, owner input-gate packet, and owner-data regression command.
- The owner input packet is the human-readable handoff for cloud/deployment owner and owner/data steward inputs.
- For QA or deployment dry-run, use `scripts/run_epilepsy_cloud_trial_acceptance.mjs` with non-local `QLANALYSER_CLOUD_FRONTEND_URL` and `QLANALYSER_CLOUD_API_BASE_URL`; it runs cloud target preflight, cloud E2E, strict cloud gate, and readiness packet in order.
- Local demo or localhost browser evidence remains implementation acceptance only and cannot satisfy the cloud trial RC gate.
- Results and export readback for cloud RC must come from the same non-local browser session that created the review revision.
- External release also requires `scripts/validate_epilepsy_owner_data_manifest_v0_1.mjs` to pass before owner-data regression can count as release evidence.

Cloud gate command:

```text
node scripts/validate_epilepsy_cloud_trial_v0_1_release_gate.mjs
```

Strict cloud gate command:

```text
QLANALYSER_REQUIRE_CLOUD=1 node scripts/validate_epilepsy_cloud_trial_v0_1_release_gate.mjs
```

The strict command must fail until cloud/staging target URLs and a passing non-local browser E2E evidence packet exist. After the 2026-07-01 cloud rerun, this condition is satisfied for the synthetic EDF customer-trial RC evidence packet, but not for formal external release.

## 2026-06-30 Cloud Synthetic Trial Acceptance Sync

Current release status: `cloud_synthetic_edf_trial_path_ready_for_acceptance`.

Accepted cloud evidence:

```text
work/release_evidence/20260630-epilepsy-deeplink-bootstrap-cloud/deeplink_bootstrap.json
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json
docs/product/qlanalyser_epilepsy_workbench_deeplink_p0_status_20260630.md
```

Latest accepted cloud upload-to-export result:

```json
{
  "status": "passed",
  "check_count": 34,
  "failed_checks": [],
  "uploaded_file_id": "eeg_f7788b10e2f0",
  "data_preparation_plan_id": "prep_1a2f0a161df1",
  "epilepsy_task_id": "task_d10bc7a94fa0",
  "report_id": "report_89d7518fc9c8"
}
```

Accepted for cloud synthetic trial:

- deep-link entry reaches `#epilepsyWorkbenchInline` and selects the epilepsy EDF demo instead of the oddball FIF demo;
- ordinary uploaded EDF path reaches data preparation, screening, manual correction, review export, Results, and report package;
- report package includes `figures/epilepsy_ml_event_timeline.svg` and `figures/epilepsy_ml_spectrogram_preview.svg`;
- non-medical research boundary is preserved without unsafe diagnosis/treatment claims;
- wheel interaction does not raise the old waveform loading toast;
- copy checks reject epilepsy staging wording in the epilepsy module.

Remaining non-blocking cloud trial follow-up:

- clean legacy cloud HTML encoding / malformed markup outside the active epilepsy trial path.

External formal release remains blocked until owner/data steward provides an authorized anonymous real EDF regression package and the real-data regression passes.

## 2026-06-30 Cutover Checkpoint Sync

Current checkpoint documents:

```text
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_checkpoint_20260630.md
docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_cloud_cutover_runbook_20260630.md
```

These documents are now the handoff reference for deployment/QA. They do not change the v0.1 scope; they make the gate state explicit. Historical note: before the 2026-07-01 cloud rerun, local synthetic upload-to-export E2E was accepted as internal evidence only and cloud trial RC remained blocked until a non-local cloud/staging target passed the full browser upload-to-export E2E. Current note: after the 2026-07-01 cloud rerun, the synthetic EDF cloud trial RC is ready for acceptance, while external release remains blocked until owner/data steward manifest validation and real anonymized EEG regression pass.

- local synthetic upload-to-export E2E remains internal implementation evidence;
- cloud synthetic EDF trial RC is ready for acceptance based on non-local browser upload-to-export E2E;
- external release remains blocked until owner/data steward manifest validation and real anonymized EEG regression pass;
- sleep staging and video analysis remain future interfaces and are not P0 acceptance items for this v0.1 epilepsy-like event screening trial.

Deployment/QA should use the cutover runbook before claiming a new cloud target is ready. Stop conditions remain: missing cloud target, localhost-only E2E, missing owner manifest for formal external release, failed owner regression, or missing non-medical boundary.

Next real release artifact:

```text
work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-acceptance-run/acceptance_run.json
```

or, after owner/data steward input:

```text
work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/real_dataset_regression_result.json
```

## Sources Used

- Owner choice rounds and product-boundary decisions in the current Codex thread, 2026-06-29 to 2026-07-01.
- `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_release_gate_receipt_20260701.md`.
- `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json`.
- `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-release-gate/release_gate_result.json`.
- `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-readiness/readiness_packet.json`.

## Traceability / Acceptance Mapping

| Release phase | Exit evidence | Current status |
| --- | --- | --- |
| P0-A Spec Freeze | Six-pack validator and convergence review. | Passed for synthetic cloud RC. |
| P0-B Local Implementation Closure | Local browser upload-to-export E2E 34/34. | Passed. |
| P0-C Cloud Trial/Staging Closure | Non-local cloud browser upload-to-export E2E 34/34 and strict release gate. | Ready for acceptance for synthetic EDF RC. |
| P0-D Internal Trial | Owner/team acceptance on the cloud RC packet. | Next acceptance step. |
| P0-E Friendly Customer Trial | Trial account, agreed data-size boundary, and support/rollback owner. | Planned, not yet formally accepted. |
| Formal external release | Owner manifest validation and real anonymized EEG regression. | Blocked. |
