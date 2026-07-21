# QLanalyser P0 Fix Acceptance Dual Review - 2026-06-27

## Scope

This review accepts the 07-PM P0 fix package as the latest baseline:

- `work/release_evidence/20260627-full-product-e2e-dual-review-fixes/fix_receipt.json`
- `work/release_evidence/20260627-full-product-e2e-dual-review-fixes/current_modules/current_available_modules_9_methods.json`
- `work/release_evidence/20260627-full-product-e2e-dual-review-fixes/edfbrowser_contract/edfbrowser_waveform_interaction_contract_validation.json`
- `work/release_evidence/20260627-full-product-e2e-dual-review-fixes/edfbrowser_numeric/edfbrowser_numeric_regression.json`
- `work/release_evidence/20260627-full-product-e2e-dual-review-fixes/visual_overflow/analysis_overflow_visual_regression.json`

Forbidden scope was preserved: no router, Headroom, gateway, IPC, model route, TimeChart integration, or epilepsy source-workbench change was made by this acceptance pass.

## Claude Review

Claude was actually called through the local Claude CLI with model request `claude-opus-4-8`.

Evidence:

- Prompt: `work/release_evidence/20260627-full-product-e2e-dual-review-fix-acceptance/claude_fix_acceptance_prompt.md`
- Result: `work/release_evidence/20260627-full-product-e2e-dual-review-fix-acceptance/claude_fix_acceptance_review.md`
- Error log: `work/release_evidence/20260627-full-product-e2e-dual-review-fix-acceptance/claude_fix_acceptance_error.txt`

Claude says:

- Verdict: conditional go for the EDFBrowser waveform interaction slice.
- Confirmed the implementation is real and not merely document-level: constants, anchored zoom, browse/write-mode separation, three-layer write model, and the 300 s ceiling are present.
- Raised residual risk around document/script/code drift, especially `minDurationSec`, anchor drift tolerance, brittle string-grep contract checks, and weak analysis-gate payload E2E assertions.

Codex note:

Claude did not produce a clean full-product page-by-page review. Its output is useful as a sidecar review for the waveform interaction slice, but it is not treated as full-product acceptance evidence by itself.

## GPT-5.5 / Codex Review

Codex rechecked the latest P0 fix evidence and reran the narrow validators available in this environment. Result: the 07 P0 fix package is accepted for internal development with remaining release risks.

Verified:

- P0-1 waveform time window: source and contract now align on `maxWindowSec = 300`, dynamically bounded by file duration.
- P0-2 horizontal overflow: 1440, 1280, and 390 px visual regression passed without hiding body overflow.
- P0-3 browser E2E hard path: syntax checks passed after replacing the old `../frontend/node_modules/playwright` assumption with package import plus Edge fallback.
- P0-4 current module validator: current UI exposes 8 formal analysis cards; QC is a data-preparation dependency, not an analysis-method card.
- Canvas numeric regression: wheel pan, Ctrl/Cmd zoom, Page/Arrow pan, middle-drag pan, browse no-draft, write-mode draft, and 30 s ceiling removal all passed.

Verification commands rerun in this acceptance pass included:

- `node --check frontend/app.js`
- `node --check scripts/e2e_edfbrowser_canvas_interaction.mjs`
- `node --check scripts/validate_edfbrowser_waveform_interaction_contract.mjs`
- `node --check scripts/acceptance_current_available_modules_9_methods.mjs`
- `node --check scripts/acceptance_data_prep_analysis_entry_consistency_e2e.mjs`
- `node --check scripts/acceptance_main_workbench_direct_method_clickthrough_e2e.mjs`
- `node --check scripts/acceptance_full_product_ui_scroll_review.mjs`
- `python -X utf8 scripts/run_full_product_e2e_preflight.py`
- `python -X utf8 scripts/run_full_product_method_source_comparison.py`
- `python -X utf8 scripts/run_full_product_backend_api_smoke.py`
- `node scripts/validate_edfbrowser_waveform_interaction_contract.mjs`
- `node scripts/acceptance_current_available_modules_9_methods.mjs`

## Full Page E2E Result

| Page / Area | Evidence | Result | Notes |
|---|---|---|---|
| Cover / login / navigation | Full-product preflight and backend smoke | Pass with risks | Login/API smoke passed; full visual inspection remains evidence-based, not a new manual UX walkthrough. |
| Project management | Backend API smoke, project list readback | Pass with risks | Demo/teaching protected project metadata is present. |
| Data upload / data management | Backend smoke, teaching dataset readback | Pass with risks | Teaching dataset protection is present in metadata. |
| Data preparation | Current P0 visual, EDFBrowser contract, numeric E2E | Pass | Canvas is interactive; no TimeChart; 2-300 s contract fixed; no horizontal overflow. |
| Analysis tasks | Current modules validator, method source comparison | Pass | 8 formal analysis method cards; QC excluded as an analysis method. |
| Result statistics / artifacts | Backend API smoke, method matrix | Pass with risks | Synthetic outputs and artifacts passed; real-data owner regression remains pending. |
| Report delivery | Backend smoke and prior full-product matrix | Pass with risks | Report/artifact paths are reachable in evidence; non-medical boundary must remain visible before external release. |
| Personal center / admin | Backend API smoke | Pass with risks | Admin/customer auth routes passed. |
| Module-lab / research pages | Prior full-product baseline | Pass with risks | Not the focus of this P0 package; no new blocker found. |

## Analysis Method E2E Result

| Method | Backend / Workflow | Evidence | Result |
|---|---|---|---|
| QC data preparation | `qc` / `metadata_qc` | `method_source_comparison_matrix.json` | Pass as data-preparation dependency, not analysis card |
| PSD / Band Power | `psd` / `resting_psd` | `method_source_comparison_matrix.json` | Pass |
| ERP | `erp` / `erp_p300` | `method_source_comparison_matrix.json` | Pass |
| TFR | `tfr` / `tfr_ersp_itc` | `method_source_comparison_matrix.json` | Pass |
| Multitaper PSD | `multitaper_psd_tfr` | `method_source_comparison_matrix.json` | Pass |
| Multitaper TFR | `multitaper_psd_tfr` | `method_source_comparison_matrix.json` | Pass |
| PAC | `pac` / `pac_cfc` | `method_source_comparison_matrix.json` | Pass |
| Connectivity | `connectivity` | `method_source_comparison_matrix.json` | Pass |
| CSD / reference | `reference_csd` | `method_source_comparison_matrix.json` | Pass |

Synthetic evidence proves workflow and artifact contracts, not cohort-level scientific validity.

## UI Visual Review

Current P0 visual evidence passed:

- `analysis-desktop-1440x900-top.png`
- `analysis-desktop-1440x900-middle.png`
- `analysis-desktop-1440x900-bottom.png`
- `analysis-laptop-1280x800-top.png`
- `analysis-laptop-1280x800-middle.png`
- `analysis-laptop-1280x800-bottom.png`
- `analysis-mobile-390x844-top.png`
- `analysis-mobile-390x844-middle.png`
- `analysis-mobile-390x844-bottom.png`

The JSON metrics show `scrollWidth == clientWidth` at 1440, 1280, and 390 px. The current analysis page has 8 method cards and 0 QC method cards. The waveform area and right-side preprocessing controls remain available in the data-preparation screen.

## Scientific Plot Review

The method matrix reports figure artifacts for PSD, ERP, TFR, multitaper PSD/TFR, PAC, Connectivity, and CSD/reference. Required output checks passed in `method_source_comparison_matrix.json`.

Remaining caution: synthetic figure checks validate artifact existence and basic scientific metadata contract; they do not replace a real-data scientific review by a domain owner.

## Blocking Items

No internal P0 fix blocker was found in this acceptance pass.

External release blockers / gates still open:

- Real anonymized owner regression is still required before external release.
- The browser E2E scripts are syntax-fixed, but direct plain `node` execution in this environment still lacks a resolvable Playwright package. This is a QA runner portability risk, not a product runtime blocker.

## Non-Blocking Issues

- Claude flagged residual documentation/test drift around `minDurationSec`, anchor drift tolerance, and brittle string-grep contract tests. Codex did not treat this as a current product blocker because the latest source and current fix evidence pass, but 07 should reconcile the docs/scripts before calling the EDFBrowser package a long-term acceptance baseline.
- T-EDF-11 analysis-gate payload assertions should be strengthened into a true submit/payload inspection test instead of relying mostly on gate presence and static contract evidence.
- Current git status includes unrelated epilepsy/timechart dirty files. They must not be attributed to the P0 Canvas fix package.

## Final Verdict

`final_verdict: pass_with_risks`

Meaning:

- Internal development acceptance: pass.
- P0 fix package: accepted.
- External release: not yet final pass until real anonymized owner regression and QA runner portability are closed.

## QGCS Receipt

route_decision: `gpt55_planner_or_acceptance + script_validator + claude_sidecar + browser_visual_evidence`

execution_packet_or_skip_reason: reused current 07 fix context; no new pool created; evidence package and Claude sidecar consumed.

executor_evidence: JSON evidence files, syntax checks, backend smoke, method matrix, visual overflow screenshots, EDFBrowser contract/numeric regression, Claude CLI output.

gpt55_acceptance: accepted the internal P0 fix package with external-release risks.

final_receipt: `completed_full_product_dual_review_fix_acceptance_pass_with_risks`

next_real_artifact: send this report and `final_acceptance_result.json` back to 07-PM for doc/test drift cleanup and owner real-data regression.
