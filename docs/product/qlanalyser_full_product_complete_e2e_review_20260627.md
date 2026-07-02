# QLanalyser Complete Full-Product E2E Review - 2026-06-27

## Executive Verdict

`final_verdict: blocked`

This is a stricter complete-release verdict, not a rejection of the P0 fix package.

- Internal development status: `pass_with_risks`
- P0 fix package status: accepted
- Complete external-release status: `blocked`

Blocking reason: the product-facing P0 fixes are real, but complete full-product release evidence is not yet closed because real anonymized owner-data regression is missing and multiple older browser E2E scripts still depend on `../frontend/node_modules/playwright`.

## Review Scope

Repository:

`D:\Quanlan\Codes\Python\quanlan-analyser-official`

Reviewed areas:

1. Cover / login / navigation / personal center / admin.
2. Project management and teaching-mode protection.
3. Data upload, selection, no-data state, teaching-data protection.
4. Data preparation Canvas and EDFBrowser-style interaction.
5. Analysis tasks: PSD/Band Power, ERP, TFR, Multitaper PSD, Multitaper TFR, PAC, Connectivity, CSD.
6. Results and report delivery.
7. UI visual review at 1440 / 1280 / 390 widths.
8. Scientific plotting and non-medical boundary.
9. Test infrastructure and release gates.

Forbidden scope preserved:

- No router / Headroom / gateway / IPC / model route change.
- No TimeChart integration.
- No epilepsy source-workbench work.
- No product code changes by this review.

## Claude Complete Review

Claude was called again through local Claude CLI with model request `claude-opus-4-8`.

Evidence:

- Prompt: `work/release_evidence/20260627-full-product-complete-review/claude_complete_review_prompt.md`
- Output: `work/release_evidence/20260627-full-product-complete-review/claude_complete_review.md`
- Error log: `work/release_evidence/20260627-full-product-complete-review/claude_complete_review_error.txt`

Claude says:

- `claude_complete_review_status: completed`
- `final_verdict: pass_with_risks`
- Confirmed 8 available analysis method cards and no QC method card.
- Confirmed TimeChart is absent from the main product HTML.
- Confirmed the analysis payload path contains `data_preparation_plan_id`, `data_preparation_revision`, and `data_preparation_contract_version`.
- Treated T-EDF-11 payload weakness as test-depth risk, not product defect.
- Still recommended closing real owner-data regression, stronger payload E2E, doc/test drift, and minor resource cleanup before external release.

Codex note:

Claude did a fuller review than the previous EDFBrowser-only response. However, Claude did not rerun the local scripts. Codex therefore uses Claude as sidecar judgment and keeps the final acceptance stricter: `blocked` for complete external release.

## Codex Evidence Rerun

Passed:

- `python -X utf8 scripts/run_full_product_e2e_preflight.py`
  - 11 checks passed.
  - `http://127.0.0.1:8001/api/health` passed.
  - `http://127.0.0.1:4174/` passed.
- `python -X utf8 scripts/run_full_product_backend_api_smoke.py`
  - 16 checks passed.
  - Blockers empty.
  - Demo run-all modules: `connectivity`, `erp`, `psd`, `qc`, `reference_csd`.
- `python -X utf8 scripts/run_full_product_method_source_comparison.py`
  - 9 method rows passed, including QC as data preparation dependency.
- `python -X utf8 scripts/acceptance_data_preparation_plan.py`
  - Created plan revision 2 and linked a PSD task.
- `node scripts/validate_edfbrowser_waveform_interaction_contract.mjs`
  - Passed.
- `node scripts/acceptance_current_available_modules_9_methods.mjs`
  - Passed.
  - 8 current analysis method cards.
  - QC excluded as analysis method card.

Failed / blocked evidence:

- `node scripts/acceptance_data_prep_analysis_entry_consistency_e2e.mjs`
  - Failed because package `playwright` is not resolvable in plain repo `node`.
- `node scripts/acceptance_customer_sidebar_navigation_governance.mjs`
  - Failed because it still hardcodes `../frontend/node_modules/playwright`.
- `node scripts/acceptance_product_wide_ux_copy_governance.mjs`
  - Failed. Some failures are stale-script expectations from the old 9-method / preview-method wording; some are real copy-governance questions.
- `node scripts/acceptance_customer_pages_user_copy_governance.mjs`
  - Failed with the same product-wide copy governance evidence.
- `python -X utf8 scripts/run_real_dataset_regression_from_manifest.py`
  - `blocked_final_receipt`: `input_manifest.json is missing`.

## Full Page E2E Matrix

| Page / area | Evidence | Status | Review notes |
|---|---|---:|---|
| Cover / login | Browser screenshot, DOM inventory, preflight | Pass with risks | Visual is professional. Default message `操作未完成，请检查信息后重试` can confuse users before login. |
| Navigation | Browser DOM inventory, screenshots | Pass with risks | Main entries exist. Mobile top area shows a personal-center card while data-preparation page is active, which weakens information hierarchy. |
| Personal center | DOM inventory and nav text | Pass with risks | Entry exists and remains reachable. Needs dedicated mobile visual cleanup. |
| Admin / backend | Backend smoke | Pass with risks | Admin endpoints and auth route smoke passed. Browser governance script for sidebar still blocked by Playwright hard path. |
| Project management | Backend project readback, DOM navigation | Pass with risks | Project state/API available. Full destructive-protection regression should stay release-gated. |
| Teaching mode / preset protection | Fix evidence and backend readback | Pass with risks | Teaching dataset metadata includes protected flags. |
| Data management | Backend/API evidence and UI navigation | Pass with risks | Upload/select surfaces exist. Full upload journey browser script chain is not completely portable yet. |
| Data preparation | Visual overflow regression, EDFBrowser contract, numeric regression | Pass | 1440/1280/390 no horizontal overflow; Canvas interaction contract and constants pass. |
| Analysis tasks | Current module validator, source/method matrix | Pass | 8 formal methods; QC is dependency. |
| Results | Method matrix and artifact checks | Pass with risks | Synthetic artifacts exist. Real-data owner regression missing. |
| Report delivery | Backend report path and UI text | Pass with risks | Report generation route exists. External release still needs real-data report package review. |
| Module-lab / research pages | Source/copy governance scan | Pass with risks | Static pages exist but copy governance script still has stale requirements and failures. |

## Analysis Method E2E Matrix

| Method | Evidence | Status | Notes |
|---|---|---:|---|
| QC data preparation | Method matrix, backend smoke, data-prep plan acceptance | Pass as dependency | Correctly not counted as formal analysis card. |
| PSD / Band Power | Method matrix, backend demo run-all | Pass | Source runner, workflow, runtime, outputs, figures passed. |
| ERP | Method matrix, backend demo run-all | Pass with risks | Runtime evidence passed; UI copy `可运行 ERP` needs wording review. |
| TFR | Method matrix | Pass with risks | Synthetic method matrix passed; not included in backend demo run-all. |
| Multitaper PSD | Method matrix | Pass with risks | Synthetic method matrix passed. |
| Multitaper TFR | Method matrix | Pass with risks | Synthetic method matrix passed. |
| PAC | Method matrix | Pass with risks | Synthetic method matrix passed; single-record descriptive boundary is present. |
| Connectivity | Method matrix, backend demo run-all | Pass | Boundary says it does not prove information flow or causality. |
| CSD / reference | Method matrix, backend demo run-all | Pass | Boundary says sensor-space filtering, not source localization or diagnosis. |

Important limitation: backend demo `run-all` covers only `qc`, `psd`, `erp`, `reference_csd`, and `connectivity`. TFR, Multitaper, and PAC are covered by synthetic method-source comparison, not the same demo run-all API path.

## Data Preparation / Payload Gate Review

Verified in `frontend/app.js`:

- `runRealTask` requires a confirmed, non-default data-preparation plan for all 8 formal analysis methods.
- It rejects wrong or missing `DATA_PREPARATION_CONTRACT_VERSION`.
- `buildTaskParameters` writes:
  - `data_preparation_plan_id`
  - `data_preparation_revision`
  - `data_preparation_contract_version`
- `/tasks` receives those values under `parameters_json`.

Verified in `backend/services/task_service.py`:

- Backend stores `data_preparation_plan_id` and `data_preparation_revision` on the task.
- Backend reads `data_preparation_contract_version` from `payload.parameters_json`.

Remaining risk:

- The live browser E2E for T-EDF-11 still needs a true submit/payload inspection assertion. Current source is correct, but the automated browser test depth is not yet release-grade.

## UI Visual Review

Evidence:

- `work/release_evidence/20260627-full-product-e2e-dual-review-fixes/visual_overflow/analysis_overflow_visual_regression.json`
- `work/release_evidence/20260627-full-product-complete-review/browser_dom/browser_dom_inventory.json`
- Screenshots under `work/release_evidence/20260627-full-product-complete-review/browser_dom/`
- Screenshots under `work/release_evidence/20260627-full-product-e2e-dual-review-fixes/visual_overflow/`

Positive:

- 1440 / 1280 / 390 data-preparation screenshots show no horizontal overflow.
- Data-preparation toolbar is more professional and includes browse / select / bad segment / bad channel controls.
- Right-side preprocessing panel remains visible on desktop.
- Mobile form controls are readable and do not overflow horizontally.

Issues:

- Default login screen can show `操作未完成，请检查信息后重试` before the user has meaningfully failed an operation.
- Mobile navigation top area can show a personal-center card while the active page is data preparation.
- Empty waveform state takes a large vertical area on mobile; users must scroll far to reach segment/bad-channel controls before data is selected.
- `favicon.ico` returns 404 on the local frontend and creates a console error. This is low severity, but should be cleaned for console hygiene.

## Scientific Plot Review

Evidence:

- `work/release_evidence/07-full-product-e2e-pdca/05_methods/method_source_comparison_matrix.json`
- Source scan under `eeg_core/analysis`

Positive:

- PSD, ERP, TFR, Multitaper PSD/TFR, PAC, Connectivity, and CSD/reference generated figure artifacts in the method matrix.
- Output checks include source runner, workflow contract, runtime, required outputs, scientific figures, and reference-token checks.
- Several modules include explicit scientific boundaries: no diagnosis, no treatment recommendation, no causality/source-localization overclaim.

Risks:

- Synthetic evidence proves workflow and artifact contract, not real-cohort scientific validity.
- Complete external release should include owner-reviewed real-data figures and report package review.

## Test Infrastructure Review

Blocking for complete external release:

- Multiple older browser scripts still hardcode `../frontend/node_modules/playwright`, including:
  - `scripts/acceptance_click_only_user_journey.mjs`
  - `scripts/acceptance_customer_login_demo.mjs`
  - `scripts/acceptance_customer_preset_analysis.mjs`
  - `scripts/acceptance_customer_workspace_color_browser_offline.mjs`
  - `scripts/acceptance_customer_sidebar_navigation_governance.mjs`
  - `scripts/acceptance_data_preparation_ux_repair_browser.mjs`
  - `scripts/acceptance_edf_upload_to_results_ui_only.mjs`
  - `scripts/e2e_teaching_user_logic_journey.mjs`
  - `scripts/ui_three_round_coverage.mjs`
  - `scripts/virtual_reviewer_p0_ui_only_runner.mjs`
  - `scripts/virtual_reviewer_vr_itc_0001.mjs`
  - `scripts/virtual_reviewer_pac_beta_ui_only_runner.mjs`
- The P0 fix corrected only the target scripts. A complete release gate needs either all active browser scripts migrated to package import + system Edge fallback, or a documented allowlisted runner.

## Blocking Items

1. Real anonymized owner-data regression is blocked because `input_manifest.json` is missing.
2. Complete browser E2E infrastructure is not release-ready because several active scripts still use old Playwright hard paths.
3. Full-product copy governance currently fails and the governance script is out of sync with the new 8-method/QC-dependency product contract.

## Non-Blocking Items

1. Strengthen T-EDF-11 into a live submit/payload inspection test.
2. Clean EDFBrowser documentation/test drift, including `minDurationSec` and brittle grep-style contract checks.
3. Fix local `favicon.ico` 404.
4. Improve mobile navigation state and default login error copy.
5. Consider reducing the mobile empty waveform placeholder height before EEG data is selected.

## Required Fix Packet Before External Release

1. Provide `input_manifest.json` for authorized anonymized real EEG datasets and rerun `scripts/run_real_dataset_regression_from_manifest.py`.
2. Migrate remaining active browser E2E scripts away from `../frontend/node_modules/playwright`.
3. Update product-wide copy governance to the current contract:
   - 8 formal analysis methods.
   - QC as data-preparation dependency.
   - No stale `9 项分析能力` requirement.
4. Add live payload assertion for T-EDF-11.
5. Re-run:
   - preflight
   - backend smoke
   - method source comparison
   - data-prep plan acceptance
   - all active browser E2E scripts
   - real dataset regression

## Final Receipt

route_decision: `gpt55_planner_or_acceptance + script_validator + claude_sidecar + browser_visual_evidence`

execution_packet_or_skip_reason: parallel evidence rerun, Claude complete review, browser DOM/screenshot inspection, source/payload review.

executor_evidence:

- Claude complete review output.
- Full-product preflight.
- Backend smoke.
- Method source comparison.
- Data-preparation plan acceptance.
- EDFBrowser contract validation.
- Current module validator.
- Browser DOM inventory and screenshots through system Edge.
- Real dataset regression gate.
- Product copy governance and browser-script path scans.

gpt55_acceptance: P0 fix accepted; internal development may continue; complete external release remains blocked.

final_receipt: `blocked_complete_full_product_e2e_external_release`

next_real_artifact: 07-PM should fix the release-gate blockers above, then return a new evidence packet for final external-release acceptance.
