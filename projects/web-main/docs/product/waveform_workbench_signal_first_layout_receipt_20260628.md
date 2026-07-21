# WaveformWorkbench Signal-First Layout Receipt

Date: 2026-06-28  
Surface: `frontend/waveform-workbench.html`  
Evidence folder: `work/release_evidence/20260628-waveform-signal-first-layout/`

## Goal

Fix the customer-review P0 issue where narrow or embedded browser viewports showed title, metadata cards, and the full toolbar before the EEG waveform.

The corrected rule is:

- waveform first,
- full toolbar second,
- no horizontal overflow,
- Basic/Epoch same-page switch still works.

## Changes

Changed files:

- `frontend/waveform-workbench.css`
- `scripts/e2e_waveform_workbench_dual_mode_contract.mjs`
- `docs/product/waveform_workbench_signal_first_layout_receipt_20260628.md`

Implementation:

- Under 980 px viewport width, `.ww-workbench` becomes a vertical flex layout.
- `.ww-main-grid` is ordered before `.ww-toolbar`, so the waveform appears before the full controls.
- Metadata cards compress into a tighter status area under 980 px.
- Under 760 px, the header, action buttons, and context rows use compact sizing.
- The dual-mode E2E now asserts signal-first behavior in a 599 px viewport.

## Verification

Syntax:

- `node --check frontend/waveform-workbench.js`: passed
- `node --check scripts/e2e_waveform_workbench_dual_mode_contract.mjs`: passed

Dual-mode and signal-first E2E:

- Command: `node scripts/e2e_waveform_workbench_dual_mode_contract.mjs`
- Result JSON: `work/release_evidence/20260628-waveform-signal-first-layout/waveform_workbench_dual_mode_contract_result.json`
- Status: passed
- Checks: 13
- Failed: 0

Epoch full workflow regression:

- Command: `node scripts/e2e_waveform_workbench_module.mjs`
- Result JSON: `work/release_evidence/20260628-waveform-signal-first-layout/epoch-full-e2e/waveform_workbench_e2e_result.json`
- Status: passed
- Failed: 0

Live in-app browser check:

- URL: `http://127.0.0.1:4174/waveform-workbench.html?teaching_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=signal-first`
- Basic mode loaded: true
- Horizontal overflow: 0
- Canvas y: about 403 px
- Full toolbar y: about 1257 px

Screenshots:

- `work/release_evidence/20260628-waveform-signal-first-layout/05_basic_narrow_signal_first.png`
- `work/release_evidence/20260628-waveform-signal-first-layout/01_basic_initial.png`
- `work/release_evidence/20260628-waveform-signal-first-layout/02b_same_page_after_epoch_switch.png`
- `work/release_evidence/20260628-waveform-signal-first-layout/epoch-full-e2e/`

## Acceptance

The P0 signal-first problem is fixed for narrow viewports:

- The EEG waveform appears before the full Browse/Display/Write toolbar.
- Context metadata is compact enough not to bury the signal.
- The same-page Basic/Epoch switch remains available.
- Epoch workflow regression remains green.

## Follow-Up

The next useful slice is the action panel policy:

- On narrow viewports, consider turning the right-side action panel into a compact sticky action strip.
- Decide whether Basic to Epoch switching should preserve a normal selected segment in production mode.

## Receipt

```yaml
final_receipt: completed_waveform_signal_first_layout_ready_for_acceptance
route_decision: gpt55_planner_or_acceptance + browser_visual_review + script_validator
executor_evidence:
  - dual_mode_signal_first_e2e_passed_13_checks_failed_0
  - epoch_full_workflow_e2e_passed
  - live_browser_canvas_before_toolbar_confirmed
gpt55_acceptance: accepted_for_signal_first_layout_slice
next_real_artifact: narrow_view_action_panel_policy
```
