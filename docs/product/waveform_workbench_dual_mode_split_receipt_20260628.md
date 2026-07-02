# WaveformWorkbench Dual-Mode Split Receipt

Date: 2026-06-28  
Surface: `frontend/waveform-workbench.html`  
Evidence folder: `work/release_evidence/20260628-waveform-workbench-dual-mode-contract/`

## Product Decision

The waveform workbench now has two product modes that share the same Canvas, cache, lightweight chunk loading, pan, zoom, sensitivity, event marker, bad segment, and bad channel foundations.

### 1. Basic waveform preview

Default URL:

```text
/waveform-workbench.html?teaching_demo=auto&api=<api>
```

Purpose:

- data preparation preview,
- continuous EEG browsing,
- display adjustment,
- time-range selection,
- candidate bad segment marking,
- bad channel marking.

Boundary:

- no Epoch review button,
- no Epoch settings,
- no Epoch keyboard shortcut,
- no Epoch grid/selection summary,
- no visible copy that introduces Epoch.

### 2. Epoch review preview

Enabled by URL:

```text
/waveform-workbench.html?workbench=epoch&teaching_demo=auto&api=<api>
```

Equivalent aliases accepted by the code:

- `workbench=epoch`
- `workbench=epoch_review`
- `workbench=epilepsy`
- `workbench=sleep`
- `workbench=sleep_stage`
- `workbench=sleep_staging`

Purpose:

- epilepsy analysis preview,
- sleep staging preview,
- other segment/epoch-level review tasks.

Boundary:

- Epoch review button is visible,
- keyboard `E` enters Epoch review,
- Epoch length and visible-epoch controls appear only in Epoch review mode,
- Epoch selected range can be reviewed as Reject/Remain.

## Implementation Summary

Changed files:

- `frontend/waveform-workbench.js`
- `frontend/waveform-workbench.css`
- `scripts/e2e_waveform_workbench_module.mjs`
- `scripts/e2e_waveform_workbench_dual_mode_contract.mjs`
- `docs/product/waveform_workbench_dual_mode_split_receipt_20260628.md`
- `work/release_evidence/20260628-waveform-workbench-dual-mode-contract/fix_receipt.json`

Main changes:

- Added a scenario gate from URL parameters.
- Default mode is `basic`.
- Epoch-capable mode is explicit.
- Basic mode hides and disables the Epoch button and controls.
- Basic mode ignores keyboard `E` for Epoch review.
- Basic mode does not render Epoch grid or Epoch selected overlay.
- Basic mode removes Epoch from visible copy, shortcut help, and draft summary.
- Existing full Epoch workflow remains available through `workbench=epoch`.

## Verification

Syntax checks:

- `node --check frontend/waveform-workbench.js`: passed
- `node --check scripts/e2e_waveform_workbench_module.mjs`: passed
- `node --check scripts/e2e_waveform_workbench_dual_mode_contract.mjs`: passed

Dual-mode contract:

- Command: `node scripts/e2e_waveform_workbench_dual_mode_contract.mjs`
- Result JSON: `work/release_evidence/20260628-waveform-workbench-dual-mode-contract/waveform_workbench_dual_mode_contract_result.json`
- Status: passed
- Checks: 9
- Failed: 0

Full Epoch workbench E2E:

- Command: `node scripts/e2e_waveform_workbench_module.mjs`
- Result JSON: `work/release_evidence/20260628-waveform-workbench-dual-mode-contract/epoch-full-e2e/waveform_workbench_e2e_result.json`
- Status: passed
- Checks: 46
- Failed: 0

Screenshots:

- Basic initial: `work/release_evidence/20260628-waveform-workbench-dual-mode-contract/01_basic_initial.png`
- Basic selected segment: `work/release_evidence/20260628-waveform-workbench-dual-mode-contract/02_basic_after_select.png`
- Epoch initial: `work/release_evidence/20260628-waveform-workbench-dual-mode-contract/03_epoch_initial.png`
- Epoch selected range: `work/release_evidence/20260628-waveform-workbench-dual-mode-contract/04_epoch_after_epoch_select.png`
- Full Epoch E2E screenshot set: `work/release_evidence/20260628-waveform-workbench-dual-mode-contract/epoch-full-e2e/`

## Acceptance

The user's split is implemented:

- Basic waveform preview does not expose Epoch.
- Epilepsy/sleep preview can explicitly enable Epoch.
- The two versions share one waveform engine instead of forking separate implementations.

## Receipt

```yaml
final_receipt: completed_waveform_dual_mode_split_ready_for_acceptance
route_decision: gpt55_planner_or_acceptance + script_validator
executor_evidence:
  - syntax_checks_passed
  - dual_mode_contract_e2e_passed_9_checks_failed_0
  - epoch_full_workbench_e2e_passed_46_checks_failed_0
gpt55_acceptance: accepted_for_dual_mode_waveform_boundary
next_real_artifact: wire_basic_mode_into_data_preparation_entry_and_epoch_mode_into_epilepsy_sleep_entries
```
