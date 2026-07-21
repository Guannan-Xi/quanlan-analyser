# WaveformWorkbench Same-Page Mode Toggle Receipt

Date: 2026-06-28  
Surface: `frontend/waveform-workbench.html`  
Evidence folder: `work/release_evidence/20260628-waveform-workbench-same-page-toggle/`

## Product Decision

The basic waveform preview and the Epoch review preview are now available on the same page through a top segmented switch:

- `基础预览`
- `Epoch 复核`

This keeps one shared waveform engine and lets the owner debug both product forms without switching URLs or reloading the selected teaching data.

## Behavior

Default mode:

- The page opens in `基础预览`.
- Epoch UI is hidden.
- Keyboard `E` does not enter Epoch review.

Same-page switch to Epoch:

- The selected data and waveform cache remain loaded.
- The URL is updated with `workbench=epoch`.
- Epoch button and Epoch review behavior become available.

Same-page switch back to basic:

- The URL removes `workbench`.
- Epoch button and controls are hidden again.
- Epoch selection state is cleared.

## Changed Files

- `frontend/waveform-workbench.html`
- `frontend/waveform-workbench.css`
- `frontend/waveform-workbench.js`
- `scripts/e2e_waveform_workbench_dual_mode_contract.mjs`
- `docs/product/waveform_workbench_same_page_toggle_receipt_20260628.md`

## Verification

Syntax checks:

- `node --check frontend/waveform-workbench.js`: passed
- `node --check scripts/e2e_waveform_workbench_dual_mode_contract.mjs`: passed
- `node --check scripts/e2e_waveform_workbench_module.mjs`: passed

Same-page dual-mode E2E:

- Command: `node scripts/e2e_waveform_workbench_dual_mode_contract.mjs`
- Result JSON: `work/release_evidence/20260628-waveform-workbench-same-page-toggle/waveform_workbench_dual_mode_contract_result.json`
- Status: passed
- Failed: 0

Epoch full E2E regression:

- Command: `node scripts/e2e_waveform_workbench_module.mjs`
- Result JSON: `work/release_evidence/20260628-waveform-workbench-same-page-toggle/epoch-full-e2e/waveform_workbench_e2e_result.json`
- Status: passed
- Failed: 0

Screenshots:

- Basic initial: `work/release_evidence/20260628-waveform-workbench-same-page-toggle/01_basic_initial.png`
- Same page after Epoch switch: `work/release_evidence/20260628-waveform-workbench-same-page-toggle/02b_same_page_after_epoch_switch.png`
- Same page after switching back to basic: `work/release_evidence/20260628-waveform-workbench-same-page-toggle/02c_same_page_after_basic_switch.png`
- Epoch full regression: `work/release_evidence/20260628-waveform-workbench-same-page-toggle/epoch-full-e2e/`

## Acceptance

The owner can now debug the two waveform forms in one page:

- Basic waveform preview remains free of Epoch concepts by default.
- Epoch review can be turned on immediately from the same page.
- Switching mode does not require selecting or loading data again.

## Follow-Up Option

Current behavior preserves a time-range selection when switching from basic to Epoch mode. This is useful for debugging continuity, but a stricter production behavior could clear regular selected segments when entering Epoch mode. This can be decided in a later interaction-state policy slice.

## Receipt

```yaml
final_receipt: completed_waveform_same_page_mode_toggle_ready_for_acceptance
route_decision: gpt55_planner_or_acceptance + script_validator
executor_evidence:
  - syntax_checks_passed
  - same_page_dual_mode_e2e_passed
  - epoch_full_e2e_regression_passed
gpt55_acceptance: accepted_for_same_page_debugging
next_real_artifact: decide_selection_preservation_policy_when_switching_modes
```
