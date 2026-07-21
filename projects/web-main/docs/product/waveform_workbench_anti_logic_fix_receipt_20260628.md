# WaveformWorkbench Anti-Logic Fix Receipt - 2026-06-28

## Scope

This package follows `docs/product/waveform_workbench_anti_logic_defect_review_20260628.md` and fixes the first group of anti-logic defects in the independent WaveformWorkbench.

Changed files:

- `frontend/waveform-workbench.js`
- `scripts/e2e_waveform_workbench_module.mjs`

No router, Headroom, gateway, IPC, model route, TimeChart, or epilepsy source workbench changes were made.

## Fixes

1. Added a first-class current-window data coverage model.
   - Exposes `dataCoverageState`, `dataCoverageRange`, and `dataCoverageFraction`.
   - Keeps `windowCoverage` derived from the same model.
2. Added visual coverage masking on the canvas.
   - Missing/loading areas are shaded instead of looking like valid empty EEG.
   - Empty windows show an explicit message that old waveform data is not being reused.
3. Fixed short-file behavior.
   - If the file is shorter than the default 24s window, the viewport clamps to the file duration.
   - The E2E short demo verifies a 10s file renders as `10 s/page`, not a 24s blank-padded canvas.
4. Prevented writes outside real waveform coverage.
   - Drag start outside loaded data is rejected.
   - Drag preview and final selected segment are clipped to loaded coverage.
   - Reject/Remain use the clipped segment.
   - Bad-channel marking is blocked when the current window has no real waveform data.
5. Added initial sensitivity estimation.
   - The first loaded payload gets a robust initial `uV/row` estimate so low-amplitude teaching/short data is visibly readable.

## Verification

Passed:

- `node --check frontend/waveform-workbench.js`
- `node --check scripts/e2e_waveform_workbench_module.mjs`
- UTF-8/mojibake scan for changed files
- Browser E2E: `scripts/e2e_waveform_workbench_module.mjs`

Browser E2E result:

- Status: `passed`
- Checks: `35`
- Failed: `0`
- New anti-logic checks:
  - `T-LOGIC-01-initial-canvas-matches-real-data-coverage`
  - `T-LOGIC-02-pan-exposes-data-coverage-state`
  - `T-LOGIC-03-short-file-uses-full-file-window`

Evidence:

- `work/release_evidence/20260628-waveform-workbench-anti-logic-fix/waveform_workbench_e2e_result.json`
- `work/release_evidence/20260628-waveform-workbench-anti-logic-fix/01_initial_loaded.png`
- `work/release_evidence/20260628-waveform-workbench-anti-logic-fix/02_after_wheel_pan.png`
- `work/release_evidence/20260628-waveform-workbench-anti-logic-fix/03_after_ctrl_zoom.png`
- `work/release_evidence/20260628-waveform-workbench-anti-logic-fix/04_after_write_mode_draft.png`
- `work/release_evidence/20260628-waveform-workbench-anti-logic-fix/04b_after_epoch_selection.png`
- `work/release_evidence/20260628-waveform-workbench-anti-logic-fix/05_after_scroll_persistence.png`
- `work/release_evidence/20260628-waveform-workbench-anti-logic-fix/06_short_data_full_file.png`

## Acceptance

Focused anti-logic fix is ready for review.

Remaining follow-up:

- P1 loading label refinement: when teaching continuous cache is ready but a backend request is pending, avoid overemphasizing the loading chip.
- P1 event marker density reduction.
- P1 lightweight waveform chunk API with min-max/envelope decimation and request cancellation.
- P2 60/300s overview and narrow-screen visual matrix.

## Final Receipt

`completed_waveform_workbench_anti_logic_fix_ready_for_review`

