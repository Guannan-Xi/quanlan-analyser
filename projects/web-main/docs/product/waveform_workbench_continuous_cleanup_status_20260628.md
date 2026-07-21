# WaveformWorkbench Continuous Cleanup Status

Date: 2026-06-28  
Surface: `frontend/waveform-workbench.html`

## Current Cleanup Goal

Continue fixing the waveform and data-preparation workbench until it follows the project UI/interaction governance:

- signal first,
- one user intention per primary control,
- no unnecessary visual noise,
- no hidden medical/clinical implication,
- Basic preview and Epoch review separated but debuggable in one page,
- customer-facing controls should not fight for attention.

## Completed Slices in This Continuous Run

### 1. Signal-first layout

Status: completed.

Evidence:

- `work/release_evidence/20260628-waveform-signal-first-layout/waveform_workbench_dual_mode_contract_result.json`
- `work/release_evidence/20260628-waveform-signal-first-layout/05_basic_narrow_signal_first.png`

Result:

- In narrow viewport, waveform appears before the full Browse/Display/Write toolbar.
- Live check: canvas y≈403, toolbar y≈1257 in the signal-first slice.

### 2. Compact narrow action panel

Status: completed.

Evidence:

- `work/release_evidence/20260628-waveform-action-panel-compact/waveform_workbench_dual_mode_contract_result.json`

Result:

- Narrow action panel is before the full toolbar.
- Action panel height is about 163 px in the checked viewport.

### 3. Basic-mode event layer policy

Status: completed.

Evidence:

- `work/release_evidence/20260628-waveform-event-layer-policy/waveform_workbench_dual_mode_contract_result.json`
- `work/release_evidence/20260628-waveform-event-layer-policy/05_basic_narrow_signal_first.png`

Result:

- Basic mode defaults to hidden event markers.
- Epoch mode defaults to light event markers.
- Overview caption and legend now match the event display state.

### 4. Loaded-state button hierarchy

Status: completed.

Evidence:

- `work/release_evidence/20260628-waveform-button-hierarchy/waveform_workbench_dual_mode_contract_result.json`
- `work/release_evidence/20260628-waveform-button-hierarchy/epoch-full-e2e/waveform_workbench_e2e_result.json`

Result:

- Before data load: `加载教学数据` remains primary.
- After data load: button becomes `重新载入教学数据` and is no longer primary.

## Current Live Browser State

URL:

```text
http://127.0.0.1:4174/waveform-workbench.html?teaching_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=button-hierarchy
```

Observed:

- loaded: true
- eventDisplay: hidden
- load teaching text: `重新载入教学数据`
- load teaching primary: false
- canvas y: about 403
- action panel y: about 993
- action panel height: about 161
- full toolbar y: about 1168
- horizontal overflow: 0

## Verification Summary

Latest dual-mode E2E:

- Folder: `work/release_evidence/20260628-waveform-button-hierarchy/`
- Status: passed
- Failed: 0

Latest Epoch full workflow E2E:

- Folder: `work/release_evidence/20260628-waveform-button-hierarchy/epoch-full-e2e/`
- Status: passed
- Failed: 0

## Remaining Cleanup Backlog

### P1: Toolbar progressive disclosure

The toolbar is now below the waveform and action panel in narrow mode, but it is still visually long. Next cleanup should make advanced controls less prominent.

Candidate direction:

- Keep compact essentials visible:
  - time window,
  - uV/row,
  - channel count,
  - browse/select/candidate/bad channel mode.
- Put advanced navigation, event display, shortcuts, and Epoch settings into a collapsible advanced controls block.

### P1: Production/debug mode switch policy

The same-page Basic/Epoch switch is useful for owner debugging. For final customer data-preparation entry, the Epoch switch may need to be hidden or demoted unless the user enters from epilepsy/sleep workflows.

Candidate direction:

- Debug route: show Basic/Epoch switch.
- Data-preparation customer route: hide or demote switch.
- Epilepsy/sleep route: open Epoch mode directly.

### P2: Wide desktop polish

Wide layout remains functional. It can still be polished after narrow customer flow is stable.

## Receipt

```yaml
final_receipt: partial_waveform_continuous_cleanup_progressing
route_decision: gpt55_planner_or_acceptance + browser_visual_review + script_validator
executor_evidence:
  - signal_first_layout_e2e_passed
  - action_panel_compact_e2e_passed
  - event_layer_policy_e2e_passed
  - button_hierarchy_e2e_passed
  - epoch_full_regressions_passed
gpt55_acceptance: accepted_incremental_slices_so_far
next_real_artifact: toolbar_progressive_disclosure_or_production_debug_mode_policy
```
