# WaveformWorkbench chunk API performance fix receipt - 2026-06-28

## Scope

This P0 fix moves WaveformWorkbench browsing away from the old QC preview task path for interactive waveform reads.

The new default path is:

```text
WaveformWorkbench pan/zoom/load
-> GET /api/eeg/files/{file_id}/waveform/chunk
-> lightweight in-process waveform window read
-> min-max bucket display payload
-> Canvas render/cache
```

The old `/api/tasks` `qc_waveform_preview` path remains as a fallback and should be used for saved QC evidence, not for normal rolling waveform browsing.

## Changed files

- `backend/services/waveform_chunk_service.py`
  - Added lightweight waveform chunk service.
  - Reads a bounded time window and selected EEG channels.
  - Returns min-max bucket display data without task/artifact/report/quota side effects.
- `backend/api/eeg_files.py`
  - Added `GET /api/eeg/files/{file_id}/waveform/chunk`.
- `frontend/waveform-workbench-adapter.js`
  - Added `fetchWaveformChunk`.
- `frontend/waveform-workbench.js`
  - Loads teaching/viewport waveform through chunk API first.
  - Exposes `data-waveform-source` and schema version for E2E.
  - Keeps old QC preview task fallback.
  - Fixed empty-state overlay synchronization after chunk loading and interaction.
- `frontend/waveform-workbench.css`
  - Empty-state overlay no longer intercepts canvas mouse events.
- `scripts/e2e_waveform_workbench_module.mjs`
  - Added assertion that initial waveform uses `waveform_chunk_api`.
- `scripts/benchmark_waveform_workbench_latency.mjs`
  - Benchmarks chunk API by default.
  - Legacy QC task benchmark is skipped unless `QLANALYSER_INCLUDE_LEGACY_TASK_BENCH=1`.

## Evidence

Evidence directory:

```text
work/release_evidence/20260628-waveform-chunk-api/
work/release_evidence/20260628-waveform-chunk-api-benchmark/
```

Key files:

- `work/release_evidence/20260628-waveform-chunk-api/waveform_workbench_e2e_result.json`
- `work/release_evidence/20260628-waveform-chunk-api/01_initial_loaded.png`
- `work/release_evidence/20260628-waveform-chunk-api/02_after_wheel_pan.png`
- `work/release_evidence/20260628-waveform-chunk-api/03_after_ctrl_zoom.png`
- `work/release_evidence/20260628-waveform-chunk-api/04_after_write_mode_draft.png`
- `work/release_evidence/20260628-waveform-chunk-api/04b_after_epoch_selection.png`
- `work/release_evidence/20260628-waveform-chunk-api/05_after_scroll_persistence.png`
- `work/release_evidence/20260628-waveform-chunk-api/06_short_data_full_file.png`
- `work/release_evidence/20260628-waveform-chunk-api-benchmark/waveform_latency_benchmark.json`

## Verification

Static checks:

```text
python -m py_compile backend/services/waveform_chunk_service.py backend/api/eeg_files.py
node --check frontend/waveform-workbench-adapter.js
node --check frontend/waveform-workbench.js
node --check scripts/e2e_waveform_workbench_module.mjs
node --check scripts/benchmark_waveform_workbench_latency.mjs
```

All passed.

API smoke:

```text
GET /api/eeg/files/eeg_demo_teaching_oddball/waveform/chunk?start_sec=0&duration_sec=24&channel_limit=8&display_sfreq=200&mode=minmax&width_px=1440
```

Result:

```json
{
  "status": 200,
  "source": "waveform_chunk_api",
  "schema_version": "qlanalyser-waveform-chunk-v0.1",
  "channels": 8,
  "times": 4800,
  "rows": 8,
  "duration_sec": 24.0,
  "downsample": "min_max_bucket"
}
```

Browser E2E:

```text
status=passed
checks=40
failed=[]
```

The E2E now includes a pixel-level first-screen canvas ink check:

```text
T-VIS-01-initial-canvas-has-visible-waveform-ink
ratio=0.236
```

Benchmark:

```text
api.health: 13.0 ms
api.lab_demo_dataset: 682.7 ms
api.waveform_chunk_0_24_first: 63.5 ms
api.waveform_chunk_0_24_warm: 59.7 ms
browser.workbench: 1765.6 ms
```

The browser benchmark state confirmed:

```json
{
  "waveformSource": "waveform_chunk_api",
  "windowCoverage": "ready",
  "usesRemappedFallback": "false"
}
```

## Acceptance

Accepted for the current independent WaveformWorkbench slice:

- First visible workbench load is under 2 seconds in this local run.
- Interactive chunk read is under 500 ms in this local run.
- The workbench no longer waits for the old 95-second QC task path by default.
- Empty-state overlay no longer blocks canvas interaction after data is loaded.
- The first visible screen now draws the waveform immediately after chunk load; it no longer needs a pan/scroll before waveform appears.
- Wheel pan, Ctrl-wheel zoom, selection, epoch review, scroll persistence, and short-file coverage remain passing in E2E.

## Boundaries

No TimeChart integration.

No epilepsy source workbench work.

No gateway, Headroom, IPC, front-route, or model-route changes.

The only new API route is the product backend waveform chunk endpoint needed for this feature.

## Remaining risks and next work

- First open of a large EDF may still be slower than the cached teaching FIF path; measure with real authorized owner data.
- JSON is acceptable for this release slice, but Arrow/MessagePack/Float32Array should be evaluated for multi-hour, high-channel browsing.
- Server-side request cancellation and prefetch windows are not implemented yet.
- The chunk cache is per backend process only.
- Permission/auth hardening follows the existing file registry model and should be reviewed before external release.

final_receipt: completed_waveform_workbench_chunk_api_fix_ready_for_acceptance
