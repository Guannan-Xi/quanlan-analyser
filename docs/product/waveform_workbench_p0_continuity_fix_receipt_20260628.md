# WaveformWorkbench P0 Continuity Fix Receipt - 2026-06-28

## Route Decision

- `gpt55_planner_or_acceptance`: P0 root cause, scope boundary, final acceptance.
- `script_validator`: syntax, UTF-8/mojibake scan, browser E2E.
- `subagent_or_thread_worker`: skipped for this slice because the triple-review packet already supplied Claude/DeepSeek/Codex independent review; direct implementation plus browser validator was lower risk and faster.

## Scope

Only the independent WaveformWorkbench slice was changed:

- `frontend/waveform-workbench.html`
- `frontend/waveform-workbench.css`
- `frontend/waveform-workbench.js`
- `scripts/e2e_waveform_workbench_module.mjs`

No router, Headroom, gateway, IPC, model route, TimeChart, or epilepsy source workbench changes were made.

## Root Cause

The previous `currentWindowData()` rendered the visible waveform by merging all overlapping cached chunks. Backend preview chunks can be downsampled on different grids, so joining overlapping chunks into one polyline can interleave incompatible sample points and make a continuous EEG trace look jagged or discontinuous.

For teaching mode, the page could also become blank while waiting for a slow backend preview chunk. That was technically honest, but it made the built-in teaching sandbox feel broken.

## Fix Summary

1. Main waveform rendering now uses a single authoritative chunk for the active viewport.
   - Selection rule: largest overlap with the active window, then highest point count, then newest chunk.
   - Other chunks remain available for cache state and overview, but are not stitched into the primary polyline.
2. Test-facing state now exposes:
   - `renderPolicy=single_authoritative_chunk`
   - `authoritativeChunkRange`
   - `authoritativeChunkCountForWindow`
   - `overlappingChunkCountForWindow`
   - `usesRemappedFallback=false`
3. Teaching mode now seeds a protected local continuous 0-60s teaching waveform cache after loading the backend teaching dataset.
   - This is limited to teaching/demo data.
   - Uploaded/user data is not fabricated; it still waits for real backend preview chunks.
4. Write actions are disabled unless the operation is meaningful.
   - Reject/Remain require a valid selection.
   - Candidate bad segment actions require candidates.
   - Undo/Redo require stacks.
   - Restore requires rejected segments.
   - Clear draft buttons require a draft and now ask for confirmation.

## Verification

Commands passed:

- `node --check frontend/waveform-workbench.js`
- `node --check scripts/e2e_waveform_workbench_module.mjs`
- UTF-8/mojibake scan for WaveformWorkbench HTML/JS/CSS/E2E files
- Browser E2E: `scripts/e2e_waveform_workbench_module.mjs`

E2E result:

- Status: `passed`
- Checks: `32`
- Failed: `0`
- Evidence JSON: `work/release_evidence/20260628-waveform-workbench-p0-continuity-fix/waveform_workbench_e2e_result.json`
- Screenshots:
  - `work/release_evidence/20260628-waveform-workbench-p0-continuity-fix/01_initial_loaded.png`
  - `work/release_evidence/20260628-waveform-workbench-p0-continuity-fix/02_after_wheel_pan.png`
  - `work/release_evidence/20260628-waveform-workbench-p0-continuity-fix/03_after_ctrl_zoom.png`
  - `work/release_evidence/20260628-waveform-workbench-p0-continuity-fix/04_after_write_mode_draft.png`
  - `work/release_evidence/20260628-waveform-workbench-p0-continuity-fix/04b_after_epoch_selection.png`
  - `work/release_evidence/20260628-waveform-workbench-p0-continuity-fix/05_after_scroll_persistence.png`

## Acceptance

Accepted for focused P0 continuity/interactivity follow-up review.

Remaining known risk:

- Real uploaded EEG browsing can still be slow because the current product path uses the `/api/tasks` QC preview workflow for waveform chunks. The next performance task should add a lightweight waveform chunk API with min-max/envelope decimation and request cancellation semantics.

## Final Receipt

`completed_waveform_workbench_p0_continuity_fix_ready_for_review`

