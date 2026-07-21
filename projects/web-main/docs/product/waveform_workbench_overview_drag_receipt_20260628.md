# WaveformWorkbench Overview Drag Receipt

Date: 2026-06-28
Status: completed incremental fix

## User Request

The overview/progress bar below the waveform must be draggable. It should not be a static status strip.

## Implemented Behavior

- The overview track is now an interactive slider-like control.
- Mouse down on the track seeks the current waveform window to the clicked position.
- Dragging horizontally updates the current time window continuously.
- Releasing the mouse schedules the waveform chunk reload for the final position.
- The current window handle remains visual-only and does not intercept pointer events.
- The control is focusable and has a screen-reader label: `全局时间轴，可拖动定位当前窗口`.

## Files Changed

- `frontend/waveform-workbench.html`
- `frontend/waveform-workbench.css`
- `frontend/waveform-workbench.js`
- `scripts/e2e_waveform_workbench_dual_mode_contract.mjs`

## Evidence

Evidence folder:

`work/release_evidence/20260628-waveform-overview-drag/`

Main E2E result:

`work/release_evidence/20260628-waveform-overview-drag/waveform_workbench_dual_mode_contract_result.json`

Epoch full E2E result:

`work/release_evidence/20260628-waveform-overview-drag/epoch-full-e2e/waveform_workbench_e2e_result.json`

Validation summary:

- `node --check frontend/waveform-workbench.js`: passed
- `node --check scripts/e2e_waveform_workbench_dual_mode_contract.mjs`: passed
- Dual-mode E2E: passed, 25 checks, failed `[]`
- Epoch full E2E: passed, failed `[]`

New regression check:

- `T-DUAL-20-overview-track-drag-seeks-time-window`
  - before `startSec = 0`
  - after drag `startSec = 36`
  - final `windowCoverage = ready`

Protected areas were not touched:

- router
- Headroom
- gateway
- IPC
- model route
- TimeChart
- epilepsy source workbench

final_receipt: completed_waveform_overview_drag_ready_for_acceptance
