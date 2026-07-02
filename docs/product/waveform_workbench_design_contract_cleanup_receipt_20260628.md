# WaveformWorkbench Design Contract Cleanup Receipt

Date: 2026-06-28  
Design contract:

- `DESIGN.md`
- `docs/product/qlanalyser_project_design_system_20260628.md`
- `docs/product/qlanalyser_design_contract_waveform_workbench_audit_20260628.md`

## Scope

Implemented `Packet A + Packet B` from the WaveformWorkbench design-contract audit.

Changed files:

- `frontend/waveform-workbench.html`
- `frontend/waveform-workbench.css`
- `frontend/waveform-workbench.js`
- `scripts/e2e_waveform_workbench_module.mjs`

No router, Headroom, gateway, IPC, model route, TimeChart, or epilepsy source-workbench files were touched.

## Changes

### 1. Status bar deduplication

Before:

- Default status bar repeated mode, display parameters, selection, draft-empty state, and browse safety.

After:

- Default status bar is hidden when there is no selected segment, no draft, and no write-mode safety message.
- Status bar appears only when it adds decision value:
  - selected segment;
  - non-empty draft count;
  - write-mode safety boundary.

### 2. Event legend deduplication

Before:

- Overview caption and legend both explained that event markers are not discontinuities.

After:

- Overview caption keeps the explanatory sentence.
- Legend item is shortened to `事件标记`.

### 3. Right-panel inactive action cleanup

Before:

- Undo / redo / restore and danger-zone clear buttons were visible but disabled in the default no-selection state.

After:

- History actions are hidden until undo/redo/restore context exists.
- Danger-zone clear actions are hidden until a draft/candidate exists.
- Review actions remain hidden until a valid segment is selected.

## Verification

### Syntax

Passed:

```text
node --check frontend\waveform-workbench.js
node --check scripts\e2e_waveform_workbench_module.mjs
```

### Browser E2E

Evidence:

- `work/release_evidence/20260628-waveform-design-contract-cleanup/waveform_workbench_e2e_result.json`

Result:

- Status: `passed`
- Checks: 41
- Failed: 0

Key checks:

- `T-WF-12-status-bar-deduped-by-default`: passed
- `T-UI-01-empty-state-does-not-promote-disabled-write-actions`: passed
- `T-WF-13-page-scroll-keeps-waveform-state`: passed

### Viewport Matrix

Evidence:

- `work/release_evidence/20260628-waveform-design-contract-cleanup/viewport_matrix_result.json`

Result:

- Status: `passed`
- 1440 / 1280 / 390 screenshots generated.
- No horizontal overflow.

Screenshots:

- `work/release_evidence/20260628-waveform-design-contract-cleanup/01_initial_loaded.png`
- `work/release_evidence/20260628-waveform-design-contract-cleanup/04_after_write_mode_draft.png`
- `work/release_evidence/20260628-waveform-design-contract-cleanup/desktop_1440_top.png`
- `work/release_evidence/20260628-waveform-design-contract-cleanup/mobile_390_top.png`

## Acceptance

Accepted for this cleanup slice.

The page now better follows the project-level design contract:

- one timeline source;
- default status not duplicated;
- no visible disabled danger/history controls before selection;
- right panel owns next-action guidance;
- waveform remains the dominant scientific object.

## Remaining Design Follow-Up

1. Decide whether `候选坏段 / 坏道 / 快捷键` should move into a secondary annotation cluster.
2. Review top boundary card vs header paragraph duplication.
3. Add empty/loading/error/focus visual evidence for release-level page QA.
4. Apply the same audit template to main workbench and teaching mode.

Final receipt: `completed_waveform_design_contract_cleanup_packet_a_b`

