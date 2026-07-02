# QLanalyser WaveformWorkbench + Epilepsy Release Candidate Integration Receipt

Date: 2026-06-28

## Scope

This receipt covers the current integration slice:

- Keep WaveformWorkbench dual-mode contract as the signal-review baseline.
- Add epilepsy ML screening into the main analysis entry.
- Preserve QC as a data-preparation dependency, not an analysis method.
- Keep epilepsy workbench on Canvas/SVG customer path; no TimeChart customer entry.
- Verify the main entry, epilepsy workbench, backend API, and WaveformWorkbench regression paths.

## Product Contract

Current main analysis entry now exposes 9 analysis methods:

1. PSD / Band Power
2. ERP
3. TFR
4. Multitaper PSD
5. Multitaper TFR
6. PAC
7. Connectivity
8. Reference / CSD
9. Epilepsy-like event screening

QC remains a data-preparation dependency and must not appear as an analysis method card.

Epilepsy main entry submits:

- `module_name`: `epilepsy_ml`
- `workflow_id`: `epilepsy_ml_xgboost`
- `method`: `ml_epoch_classifier`
- `probability_threshold`: `0.5`
- `epoch_length_sec`: `5`
- `non_medical_boundary`: `Research screening/support only; no diagnosis, treatment, or clinical decision-making.`

After the task completes, the result card exposes the epilepsy review workbench link with Canvas renderer:

- `epilepsy-workbench.html?task=<task_id>&mode=ml_epoch_classifier&renderer=canvas`

## Self-Adversarial Review

### Global Page

Pass:

- Main analysis page shows one coherent method set: 9 analysis cards.
- QC is absent from method cards.
- The epilepsy card is described as research screening and routes to a review workbench.

Remaining risk:

- Existing product-wide owner real-data regression is still blocked until the authorized anonymous EEG manifest is provided.

### Functional Regions

Pass:

- Data preparation remains the gate before analysis.
- WaveformWorkbench basic/epoch split remains intact.
- Epilepsy workbench keeps source output and manual review layers separate.

Remaining risk:

- Epilepsy ML task is relatively slow in the local fixture E2E; this is algorithm/runtime cost, not UI rendering cost.

### Control Level

Pass:

- Epilepsy Stage_Code edits require Correction mode before Seizure/Normal can modify the local review layer.
- The E2E now validates the current safety behavior instead of bypassing it.
- The old TimeChart customer entry is not visible.

Remaining risk:

- Some legacy TimeChart implementation code remains unreachable in the workbench source. It is not exposed by URL parameter or toolbar entry in the customer path.

### Business Workflow

Pass:

- Main app: teaching data -> confirm preparation -> click epilepsy method -> task payload contract -> result workbench link.
- Epilepsy workbench: select fixture -> run ML workflow -> render candidates -> enable Correction mode -> modify Stage_Code -> undo/restore -> read waveform window -> visible preview.
- WaveformWorkbench: basic mode and epoch mode both pass regression E2E.

Remaining risk:

- External release should still require owner-data regression and QA-machine browser runner portability checks.

## Evidence

Main epilepsy entry:

- `work/release_evidence/20260628-main-epilepsy-entry-contract/main_epilepsy_entry_contract.json`
- `work/release_evidence/20260628-main-epilepsy-entry-contract/01_main_methods_epilepsy_card.png`
- `work/release_evidence/20260628-main-epilepsy-entry-contract/02_epilepsy_result_workbench_link.png`

Epilepsy workbench:

- `work/e2e_epilepsy_workbench/ui_e2e/epilepsy_workbench_e2e.json`
- `work/e2e_epilepsy_workbench/ui_e2e/01_workbench_loaded.png`
- `work/e2e_epilepsy_workbench/ui_e2e/02_after_workbench_run.png`

WaveformWorkbench:

- `work/release_evidence/20260628-waveform-workbench-dual-mode-contract/waveform_workbench_dual_mode_contract_result.json`
- `work/release_evidence/20260628-waveform-workbench-epoch-review/waveform_workbench_e2e_result.json`

Backend and ML:

- `work/release_evidence/07-full-product-e2e-pdca/04_backend_api/backend_api_smoke.json`
- `work/e2e_epilepsy_ml_migration/asset_validation.json`
- `work/e2e_epilepsy_ml_migration/feature_contract.json`
- `work/e2e_epilepsy_ml_migration/model_smoke.json`
- `work/e2e_epilepsy_ml_migration/fixture_run_evidence.json`

## Verification Commands

Passed:

- `node --check frontend/app.js`
- `node --check frontend/epilepsy-workbench.js`
- `node --check scripts/e2e_epilepsy_workbench.mjs`
- `node scripts/acceptance_current_available_modules_9_methods.mjs`
- `node scripts/acceptance_main_workbench_direct_method_entries_9_methods.mjs`
- `node scripts/acceptance_current_modules_teaching_mode_static.mjs`
- `node scripts/e2e_main_epilepsy_entry_contract.mjs`
- `node scripts/e2e_epilepsy_workbench.mjs`
- `node scripts/e2e_waveform_workbench_dual_mode_contract.mjs`
- `node scripts/e2e_waveform_workbench_module.mjs`
- `python -X utf8 scripts/acceptance_epilepsy_workbench_api_contract.py`
- `python -X utf8 scripts/validate_epilepsy_ml_assets.py`
- `python -X utf8 scripts/acceptance_epilepsy_ml_feature_contract.py`
- `python -X utf8 scripts/acceptance_epilepsy_ml_model_smoke.py`
- `python -X utf8 scripts/acceptance_epilepsy_ml_fixture_run.py`
- `python -X utf8 scripts/run_full_product_backend_api_smoke.py`
- `python -X utf8 scripts/run_full_product_method_source_comparison.py`

Route protection:

- Protected route diff scan returned no router / Headroom / gateway / IPC / model route hits.

## Verdict

Internal release-candidate slice status: pass with risks.

Not yet full external release:

- Real anonymous owner-data regression is still blocked by missing authorized `input_manifest.json`.
- QA machine Playwright portability should still be checked outside this local runtime.

