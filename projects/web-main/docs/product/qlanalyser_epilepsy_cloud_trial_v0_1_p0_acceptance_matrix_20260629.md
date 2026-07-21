# QLanalyser Epilepsy-like Event Screening Cloud Trial v0.1 - P0 Acceptance Matrix

Status: document synced 2026-06-30; local browser upload-to-export pass recorded with interaction fixes, cloud RC blocked.

| ID | Requirement | Evidence Required | Status |
| --- | --- | --- | --- |
| P0-01 | Cloud trial app accessible with login/trial account | Browser E2E screenshot + auth state | blocking: no cloud/staging URL + trial account E2E |
| P0-02 | User can create/open project | Browser E2E + API readback | passed local browser upload-to-export E2E; cloud/staging pending |
| P0-03 | User uploads synthetic EDF from UI | Browser E2E + uploaded file metadata | passed local browser upload-to-export E2E; cloud/staging pending |
| P0-04 | Upload metadata shows name, size, duration, sfreq, channel count/names, format, warnings | DOM snapshot + backend readback | partially passed local browser/API readback for format, duration, sfreq, channel count; full customer DOM metadata review pending |
| P0-05 | Upload authorization confirmation is recorded | API readback / audit row | passed local browser upload-to-export E2E; cloud/staging pending |
| P0-06 | Ordinary uploaded data is gated before preparation confirmation | Browser E2E | passed local browser upload-to-export E2E: direct `epilepsy_ml` task before confirmed plan returns `DATA_PREPARATION_REQUIRED`; cloud/staging pending |
| P0-07 | Data preparation plan confirmation creates plan/revision/contract | API readback + payload inspect | passed local browser upload-to-export E2E; cloud/staging pending |
| P0-08 | Analysis entry uses epilepsy-like event screening wording, not staging wording | DOM/copy governance scan | passed local static contract + scoped v0.1 copy governance; full obsolete-page governance pending |
| P0-09 | Workbench first view shows waveform before screening | Screenshot + canvas/pixel check | passed local browser upload-to-export E2E; cloud/staging pending |
| P0-10 | Start button label is `开始初筛` and gives immediate feedback | Browser E2E | passed local browser upload-to-export E2E; cloud/staging pending |
| P0-11 | Backend task is real `epilepsy_ml` by default | intercepted payload + task readback | passed local API and inline demo |
| P0-12 | Progress bar and current step are visible while running | Browser E2E | passed local browser upload-to-export E2E with completed progress assertion; cloud/staging pending |
| P0-13 | Synthetic fixture algorithm output Stage_Code is `000001100000` | artifact CSV/JSON readback | passed locally, cloud planned |
| P0-14 | Synthetic fixture candidate event is 25.0-35.0 s | artifact CSV/JSON readback | passed locally, cloud planned |
| P0-15 | Result UI shows waveform event marker | screenshot + DOM/canvas evidence | passed local browser upload-to-export E2E; cloud/staging pending |
| P0-16 | Result UI shows Stage_Code strip and canvas overlay | screenshot + DOM/canvas evidence | passed local static contract and browser E2E overlay-toggle check; cloud/staging pending |
| P0-17 | Result UI shows synchronized spectrogram | screenshot + artifact/source check | passed local browser upload-to-export E2E; STFT source is same waveform chunk; cloud/staging pending |
| P0-18 | Candidate event click syncs table, waveform, Stage_Code, spectrogram within target | Browser timing evidence | planned |
| P0-19 | Browse mode cannot write review changes | Browser E2E | planned |
| P0-20 | Manual Review can mark epoch/range labels | Browser E2E + review draft readback | planned |
| P0-21 | Undo/Redo works | Browser E2E | planned |
| P0-22 | Save review revision persists across refresh | Browser E2E + API readback | planned |
| P0-23 | Results page shows task, file, algorithm, preparation, candidate count, review revision | Browser E2E | passed local browser upload-to-export E2E for review package visibility; detailed field-by-field cloud DOM review pending |
| P0-24 | CSV export includes required four tables | export inventory | passed local browser upload-to-export E2E and API export contract; cloud/staging pending |
| P0-25 | JSON export includes required five JSON docs | export inventory | passed local browser upload-to-export E2E and API export contract; cloud/staging pending |
| P0-26 | Export includes non-medical boundary | content scan | passed local API export contract; customer copy governance pending |
| P0-27 | Failure state shows reason, error id, suggested action, support entry | passed local failure-state browser E2E for missing authorization, unconfirmed preparation gate, forced screening failure, artifact load failure, review-save failure, and export failure; cloud/staging pending |
| P0-28 | No no-op clickable controls | control state matrix E2E | partially passed local failure-state browser E2E via disabled reasons for unconfirmed preparation and review actions; broader keyboard/control matrix pending |
| P0-29 | No epilepsy staging / diagnostic wording in customer UI | copy governance scan | passed scoped v0.1 copy governance and browser E2E guards; full product/obsolete-page copy governance still pending |
| P0-30 | Waveform wheel/keyboard does not trigger global toast | browser interaction E2E | passed local browser upload-to-export E2E for inline waveform wheel; broader keyboard matrix pending |

## Current Known Evidence

Local synthetic fixture evidence:

- `work/release_evidence/20260629-regular-epilepsy-labeled-fixture/regular_epilepsy_labeled_fixture_acceptance.json`

This proves the fixture and local backend algorithm replay, not cloud upload E2E.

## Acceptance Rule

Internal cloud trial cannot be accepted until every P0 row is `passed` or has an explicit owner-approved deferral that does not break the stated v0.1 cloud trial goal.

## Change Log

- 2026-06-29: Created P0 acceptance matrix baseline.
- 2026-06-30: Updated top-level P0 row statuses from local API/browser-demo evidence and kept cloud RC blockers explicit.

## 2026-06-29 Incremental Acceptance Update

Status: `partial_local_pass_cloud_blocked`.

This update records the latest local development evidence without upgrading the cloud trial release status.

### Passed In Local API / Backend Contract

| Area | Status | Evidence |
| --- | --- | --- |
| Upload authorization gate | passed | `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-contract/upload_authorization_contract.json` |
| Ordinary uploaded data requires confirmed data preparation before formal analysis | passed | `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-to-export/cloud_upload_to_export_contract.json` |
| Data preparation lineage is strict: confirmed plan, same file, same project | passed | `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-to-export/cloud_upload_to_export_contract.json` |
| `epilepsy_ml` workflow is constrained to `epilepsy_ml_xgboost` | passed | `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-to-export/cloud_upload_to_export_contract.json` |
| Synthetic labeled EDF upload-to-export API chain | passed | `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-upload-to-export/cloud_upload_to_export_contract.json` |
| Review export v0.1 CSV/JSON contract | passed | `work/release_evidence/epilepsy_source_workbench_replica_acceptance/latest_final_verdict.json` and latest `export.json` |

### Passed In Local Browser Teaching/Demo Path

| Area | Status | Evidence |
| --- | --- | --- |
| Main analysis page opens inline epilepsy-like event workbench | passed | `work/release_evidence/20260629-epilepsy-release-e2e/main_epilepsy_entry_real_path.json` |
| Start screening sends `module_name=epilepsy_ml` and `workflow_id=epilepsy_ml_xgboost` | passed | same evidence path |
| Task payload carries `data_preparation_plan_id`, `data_preparation_revision`, and `data_preparation_contract_version=qlanalyser-data-preparation-v0.2` | passed | same evidence path |
| Stage_Code truth fixture is visible as `000001100000` | passed | same evidence path |
| Candidate event `25.0-35.0s` is detected and visible | passed | same evidence path |
| Waveform, Stage_Code strip, and synchronized spectrogram panels are visible | passed | same evidence path |

### Still Blocking Cloud Trial Release Candidate

| Blocker | Required Evidence Before RC |
| --- | --- |
| Cloud/staging URL and trial account E2E are not yet completed | Browser evidence against the real cloud/staging URL, not `127.0.0.1` |
| Cloud/staging browser UI path from ordinary EDF upload to export is not yet completed | Repeat the passed local browser E2E against the real cloud/staging URL and trial account |
| Cloud Results module has not yet proven it can open the v0.1 export package | Results page screenshot and artifact readback for CSV/JSON package against real cloud/staging URL |
| Cloud/staging customer copy governance has not been rerun | No mojibake in cloud DOM/evidence, no "epilepsy staging" wording, no diagnosis/triage claims |
| Cloud/staging failure/loading/empty states are not yet covered | Repeat failure-state browser assertions against cloud/staging where safe, or document simulated failure route |
| Cloud performance boundary is not measured | Upload, metadata extraction, screening task, artifact load, review save, export timing |
| Authorized anonymous owner-data regression remains pending | Owner/steward manifest and regression evidence |

Acceptance remains blocked for external/cloud trial until the blocking rows above are resolved or explicitly deferred by the owner without contradicting the v0.1 trial goal.

## 2026-06-30 Interaction Fix Sync

Status: `local_browser_upload_to_export_pass_interaction_contract_extended_cloud_blocked`.

New local evidence:

- `work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/browser_upload_to_export.json`
- `work/release_evidence/20260629-epilepsy-child-page-p0/static_epilepsy_child_page_contract.json`
- `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-copy-governance/copy_governance_result.json`
- `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-failure-states/failure_states_browser.json`

New accepted checks:

- Inline workbench stays inside the main shell and maps its parent navigation to `analysis task / workflow`.
- Page title shows `癫痫样事件分析台` while the sidebar parent remains `分析任务`.
- First visible workbench content is the waveform panel, not the screening button.
- Time-scale controls are not duplicated between waveform and spectrogram; the spectrogram readout follows the waveform window.
- Inline waveform wheel browsing does not raise a global toast.
- Screening progress reaches the completed state in local browser upload-to-export E2E.
- STFT preview declares `waveform_chunk_stft_preview` as its source.
- `Stage_Code` has a real canvas overlay toggle, not a no-op button.
- Scoped v0.1 copy governance passes: customer UI uses event-screening wording, not epilepsy staging wording; internal `Seizure/Normal/Needs review` labels are allowed only behind Chinese display labels.
- Failure-state E2E passes locally for missing upload authorization, unconfirmed preparation gate, forced screening failure, artifact load failure, review-save failure, and export failure.

This update does not change the cloud release verdict. Cloud/staging trial account E2E, cloud performance boundary, full obsolete-page copy governance, and authorized owner-data regression remain pending.
