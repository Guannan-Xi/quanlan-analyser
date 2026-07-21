# QLanalyser Full Product E2E Dual Review - 2026-06-27

## claude_review_result

Claude was actually called twice with `--model claude-opus-4-8`; both calls returned with empty stderr.

Usable Claude findings:
- The waveform zoom contract has a real mismatch: `zoomEegWindow()` allows up to 300 s, but `syncEegControlsFromState()` and `buildQcPreviewParametersFromUi()` clamp `windowSec` back to 30 s, and the HTML slider max is 30. This blocks professional long-window EEG browsing beyond 30 s.
- The EDFBrowser contract validator is still too string/grep oriented and can pass while numeric behavior regresses.
- A real-dataset/owner regression gate is still not proven by the synthetic evidence.

Claude limitations:
- First Claude response reviewed mostly the waveform implementation, not the whole product.
- Retry response corrected scope partly, but mixed in stale pre-implementation P0s that are contradicted by the 2026-06-27 Canvas acceptance package. Codex does not adopt those stale P0s.
- Claude did not rerun tests itself; its review is treated as model-review evidence, not deterministic acceptance.

Claude evidence:
- `work/release_evidence/20260627-full-product-e2e-dual-review/claude_full_product_review.md`
- `work/release_evidence/20260627-full-product-e2e-dual-review/claude_full_product_review_retry.md`

## gpt55_review_result

Codex/GPT-5.5 acceptance verdict: `blocked` for external release, `pass_with_risks` for continuing internal 07 development.

Current rerun evidence passed:
- `node --check frontend/app.js`
- `node --check scripts/e2e_edfbrowser_canvas_interaction.mjs`
- `node --check scripts/validate_edfbrowser_waveform_interaction_contract.mjs`
- `python -X utf8 scripts/run_full_product_e2e_preflight.py`
- `python -X utf8 scripts/run_full_product_backend_api_smoke.py`
- `python -X utf8 scripts/run_full_product_method_source_comparison.py`

Current browser sanity review via system Edge produced 24 checks, with 23 pass and 1 fail:
- Failed: data preparation page has horizontal overflow at 1440 px viewport (`scrollWidth=1539`, `clientWidth=1440`).
- Passed: core left navigation, personal center entry, Canvas presence, four EDFBrowser modes, analysis gate node, preprocessing controls same screen, QC not an independent analysis method, no visible positive medical claims in the checked workflow page.

Important release blockers:
- Data preparation 30 s vs 300 s waveform window mismatch is verified in source.
- Data preparation page has horizontal overflow at 1440 px.
- Browser E2E scripts cannot be rerun from the repository because they import `../frontend/node_modules/playwright`, which is missing in this checkout.
- `scripts/acceptance_current_available_modules_9_methods.mjs` is stale: it parses `<article class="ia-method-card">`, while current UI uses `<button class="ia-method-card">`.
- Full-product evidence is still mostly synthetic/demo. Real anonymized dataset owner regression remains a separate blocked gate.

## disagreements

Claude and Codex agree on:
- The 30 s/300 s waveform window mismatch is real.
- Validator depth needs hardening beyond string presence.
- Synthetic evidence is not real-dataset scientific validation.

Codex disagrees with Claude on:
- Claude retry claimed the 2026-06-27 EDFBrowser layer was still only design-review. Current evidence shows a development acceptance package exists and passed T-EDF-01..T-EDF-12, though Codex still blocks release due to the newly found 30 s/300 s mismatch, horizontal overflow, and stale tests.
- Claude retry listed old doc P0s as if still current. Codex does not adopt those old P0 labels without current-source confirmation.

## full_page_e2e_matrix

| Page / area | Current result | Evidence | Release note |
|---|---:|---|---|
| Cover / login / app shell | Pass with synthetic account | `03_preflight/preflight.json`, Edge screenshots | Not a production auth/security audit. |
| Left navigation | Pass | `codex_browser_sanity_review.json` | Core pages and personal center entry present. |
| Project management | Pass with risks | `backend_api_smoke.json`, `page_dashboard.png` | Project list works in synthetic state; large registry size should be watched. |
| Data management | Pass with risks | `page_storage.png`, backend smoke | Upload/select states visible; full destructive-protection test not rerun today. |
| Data preparation | Blocked | `page_analysis.png`, `edfbrowser_*`, source lines | Canvas exists, modes exist, but 1440 px overflow and 30 s/300 s mismatch block release. |
| Analysis tasks | Pass with risks | `method_source_comparison_matrix.json`, `main_workbench_direct_method_clickthrough_e2e.json`, `page_workflow_methods.png` | Current no-data state correctly disables cards; direct-method clickthrough evidence is prior 2026-06-25/26 and should be rerun after fixing Playwright path. |
| Results | Pass with risks | `report_zip_inventory.json`, `scientific_figure_audit.json` | Report package covers required artifacts; not every method has equal full report depth. |
| Report delivery | Pass with risks | `page_publication.png`, report evidence | Empty state and generation entry visible; full download chain relies on prior evidence. |
| Personal center | Pass | `page_userCenter.png` | Entry was not lost. |
| Admin / account backend | Pass with risks | `backend_api_smoke.json` | Admin auth/routes smoke passed; not a hard security review. |

## analysis_method_e2e_matrix

| Method | UI entry | Backend/source evidence | Output evidence | Verdict |
|---|---|---|---|---|
| QC / data preparation | Inline only, not independent analysis method | `qc_preview.py`, `quality.py`, data prep service | QC manifest/result/repro files | Pass as dependency, not analysis method. |
| PSD + Band Power | `run-psd` | `run_psd`, MNE `compute_psd(method="welch")` | PSD spectrum, band power CSV/SVG | Pass with synthetic evidence. |
| ERP | `run-erp` | `run_erp`, events/epochs/baseline | ERP metrics, waveform SVG | Pass with synthetic event fixture. |
| TFR | `run-tfr` | `run_tfr`, Morlet TFR | power/ITC CSV/SVG | Pass with synthetic evidence; keep research-boundary copy. |
| Multitaper PSD | `run-multitaper-psd` | shared `run_multitaper_psd_tfr` | multitaper PSD curve/tables | Pass with synthetic evidence. |
| Multitaper TFR | `run-multitaper-tfr` | shared `run_multitaper_psd_tfr` | multitaper TFR heatmap/tables | Pass with synthetic evidence. |
| CSD / reference | `run-reference-csd` | `run_reference_csd` | reference/CSD before-after outputs | Pass with synthetic montage; requires channel-position boundary. |
| PAC | `run-pac` | `run_pac`, Hilbert/filter pipeline | comodulogram/dynamic/tables | Pass with synthetic evidence; not causal interpretation. |
| Connectivity | `run-connectivity` | `run_connectivity` | matrix/network/tables | Pass with synthetic evidence; not information-flow/causality. |
| Epilepsy current availability | Backend templates/imports exist | `task_service.py` imports epilepsy/epilepsy_ml | Not part of current Canvas release depth | Risk-only review; do not expand in this fix packet. |

## ui_visual_review

Passes:
- Main left navigation is clear and keeps personal center visible.
- Data preparation now shows Canvas, status strip, mode buttons, and preprocessing controls in one working surface.
- Report delivery and empty states are understandable for a researcher.
- Visible checked pages avoid positive medical promises.

Fix before release:
- Remove data preparation horizontal overflow at 1440 px.
- Recheck narrow and wide viewports after the layout fix.
- Keep analysis cards visually distinct between "available after prep" and disabled/currently blocked states.
- Replace test-output mojibake by UTF-8 read/write paths where possible, even though rendered UI screenshot text is readable.

## scientific_plot_review

Current scientific figure audit passed for scanned synthetic outputs:
- Required figure files exist and are nonempty.
- Title/axis/context scans passed.
- `jet`, `rainbow`, and similar unsafe colormap names were not found in scanned artifacts.
- Unsupported diagnostic-claim scan passed.

Remaining risks:
- Static scans do not prove perceptual quality, colorbar readability, or publication-grade sizing.
- Report package full-depth evidence is strongest for PSD/ERP/TFR/PAC; method matrix covers all 9 UI rows/8 backend families, but the report-chain depth is not equal for every method.

## blocked_items

1. Waveform time-window contract mismatch: code path allows 300 s then clamps back to 30 s.
2. Data preparation page horizontal overflow at 1440 px.
3. Repo browser E2E scripts fail without `frontend/node_modules/playwright`; current review used Codex-bundled Playwright plus system Edge as workaround.
4. `acceptance_current_available_modules_9_methods.mjs` is stale against current button-based method-card markup.
5. Real anonymized dataset owner regression remains unproven in this review cycle.
6. Claude full-product review is only partially reliable; Codex acceptance owns final verdict.

## required_fixes_before_release

07-PM fix packet:

1. Fix waveform window duration contract.
   - Choose either 30 s or 300 s as product truth. For EDFBrowser-style long EEG reading, Codex recommends implementing the 300 s ceiling.
   - Update `frontend/index.html` slider max, `syncEegControlsFromState()`, `buildQcPreviewParametersFromUi()`, and `EDF_BROWSER_INTERACTION_CONSTANTS`.
   - Add an E2E assertion that zoom-out can exceed 30 s when file duration allows and remains clamped at the selected max.

2. Fix data preparation horizontal overflow.
   - Target evidence failure: `codex_browser_sanity_review.json`, `page_no_horizontal_overflow_analysis`, 1440 px.
   - Recheck desktop 1440, laptop 1280, mobile 390, plus scroll top/middle/bottom.

3. Repair browser E2E dependencies.
   - Replace hard import of `../frontend/node_modules/playwright` with package import plus optional system Edge executable fallback, matching `scripts/e2e_edfbrowser_canvas_interaction.mjs`.
   - Do not install dependencies as part of the release fix unless 07-PM explicitly approves.

4. Update stale 9-method static validator.
   - Parse both `<button class="ia-method-card">` and legacy `<article class="ia-method-card">`.
   - Assert current 8 run actions plus QC-as-dependency separately.

5. Harden Canvas interaction E2E assertions.
   - Check pan ratio magnitude, zoom anchor drift tolerance, PageUp/PageDown page jump, arrow 0.1 page jump, mode-specific write/no-write side effects, and payload version fields.

6. Run real anonymized dataset owner regression.
   - Provide input manifest, source checksum, data boundaries, artifact inventory, report package, and owner-facing release packet.

## evidence_paths

- `work/release_evidence/20260627-edfbrowser-waveform-interaction-dev/acceptance_packet.json`
- `work/release_evidence/20260627-edfbrowser-waveform-interaction-dev/edfbrowser_waveform_interaction_contract_validation.json`
- `work/release_evidence/20260627-edfbrowser-waveform-interaction-dev/edfbrowser_waveform_interaction_browser_e2e.json`
- `work/release_evidence/20260627-edfbrowser-waveform-interaction-dev/edfbrowser_waveform_interaction_e2e.png`
- `work/release_evidence/20260627-full-product-e2e-dual-review/codex_browser_sanity_review.json`
- `work/release_evidence/20260627-full-product-e2e-dual-review/claude_full_product_review.md`
- `work/release_evidence/20260627-full-product-e2e-dual-review/claude_full_product_review_retry.md`
- `work/release_evidence/07-full-product-e2e-pdca/03_preflight/preflight.json`
- `work/release_evidence/07-full-product-e2e-pdca/04_backend_api/backend_api_smoke.json`
- `work/release_evidence/07-full-product-e2e-pdca/05_methods/method_source_comparison_matrix.json`
- `work/release_evidence/07-full-product-e2e-pdca/06_main_workbench/main_workbench_clickthrough_e2e/main_workbench_direct_method_clickthrough_e2e.json`
- `work/release_evidence/07-full-product-e2e-pdca/07_reports/scientific_figure_audit.json`
- `work/release_evidence/07-full-product-e2e-pdca/10_acceptance_packet/full_product_e2e_acceptance_packet_20260626.json`

## final_verdict

`blocked`

Reason: the current product can continue internal 07 development, and many synthetic full-product checks pass. It should not be released externally until the waveform 30 s/300 s mismatch, data-preparation overflow, stale E2E/test scripts, and real-dataset owner regression gate are resolved.
