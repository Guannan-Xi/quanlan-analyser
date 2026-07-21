# WaveformWorkbench Event Layer Policy Receipt

Date: 2026-06-28  
Surface: `frontend/waveform-workbench.html`  
Evidence folder: `work/release_evidence/20260628-waveform-event-layer-policy/`

## Goal

Reduce the risk that dense event marker lines in teaching/demo EEG are mistaken for signal discontinuities in the basic waveform preview.

## Policy

Basic waveform preview:

- Default event marker display is `hidden`.
- Event marker legend is hidden.
- Overview caption says `事件标记已隐藏`.

Epoch review mode:

- Default event marker display is `light`.
- Event marker legend is visible.
- This is appropriate for epilepsy/sleep-style workflows where events or epoch evidence may matter.

User override:

- If the user manually changes event display, the workbench respects that choice and does not auto-reset it on mode switch.

## Changed Files

- `frontend/waveform-workbench.js`
- `scripts/e2e_waveform_workbench_dual_mode_contract.mjs`
- `docs/product/waveform_workbench_event_layer_policy_receipt_20260628.md`

## Verification

Syntax:

- `node --check frontend/waveform-workbench.js`: passed
- `node --check scripts/e2e_waveform_workbench_dual_mode_contract.mjs`: passed

Dual-mode E2E:

- Command: `node scripts/e2e_waveform_workbench_dual_mode_contract.mjs`
- Result JSON: `work/release_evidence/20260628-waveform-event-layer-policy/waveform_workbench_dual_mode_contract_result.json`
- Status: passed
- Failed: 0

Epoch full regression:

- Command: `node scripts/e2e_waveform_workbench_module.mjs`
- Result JSON: `work/release_evidence/20260628-waveform-event-layer-policy/epoch-full-e2e/waveform_workbench_e2e_result.json`
- Status: passed
- Failed: 0

Live browser check:

- URL: `http://127.0.0.1:4174/waveform-workbench.html?teaching_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=event-layer-policy`
- Basic mode loaded: true
- `eventDisplay`: `hidden`
- Event legend visible: false
- Overview caption: `事件标记已隐藏`
- Horizontal overflow: 0

Screenshots:

- `work/release_evidence/20260628-waveform-event-layer-policy/05_basic_narrow_signal_first.png`
- `work/release_evidence/20260628-waveform-event-layer-policy/02b_same_page_after_epoch_switch.png`
- `work/release_evidence/20260628-waveform-event-layer-policy/epoch-full-e2e/`

## Acceptance

The basic waveform preview is now more signal-first:

- Dense event marker lines are not shown by default.
- The waveform looks continuous and less visually fragmented.
- Epoch mode still keeps event evidence available.

## Receipt

```yaml
final_receipt: completed_waveform_event_layer_policy_ready_for_acceptance
route_decision: gpt55_planner_or_acceptance + browser_visual_review + script_validator
executor_evidence:
  - dual_mode_event_policy_e2e_passed
  - epoch_full_regression_passed
  - live_browser_basic_event_hidden_confirmed
gpt55_acceptance: accepted_for_event_layer_policy_slice
next_real_artifact: toolbar_progressive_disclosure_for_customer_mode
```
