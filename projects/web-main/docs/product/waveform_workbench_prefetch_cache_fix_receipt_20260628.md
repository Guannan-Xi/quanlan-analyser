# WaveformWorkbench cache hit / prefetch fix receipt - 2026-06-28

## Scope

This follow-up fix improves interactive browsing after the lightweight waveform chunk API was added.

Main behavior:

- If the current viewport is already covered by a cached authoritative chunk, WaveformWorkbench renders immediately and records `cache_hit`.
- Cached viewport reloads settle with `0 ms` debounce.
- Missing viewport reloads keep the `180 ms` debounce to avoid flooding the backend during continuous wheel/drag navigation.
- A newer foreground request aborts the previous foreground request.
- Adjacent left/right windows are prefetched when they are not already covered by cache.
- The old QC preview task remains only as a fallback, not the normal browsing path.

## Changed files

- `frontend/waveform-workbench-adapter.js`
  - `fetchWaveformChunk` now accepts an `AbortSignal`.
- `frontend/waveform-workbench.js`
  - Added authoritative cache coverage detection.
  - Added foreground request cancellation.
  - Added cache-hit immediate reload path.
  - Added adjacent window prefetch.
  - Added test-visible counters for cache hits, chunk requests, aborts, fallbacks, and prefetches.
- `scripts/e2e_waveform_workbench_module.mjs`
  - Added `T-PERF-02-wheel-pan-uses-cache-hit-not-legacy-task`.
- `scripts/benchmark_waveform_workbench_latency.mjs`
  - Records cache hit / request / fallback counters in browser state.

## Evidence

Evidence directories:

```text
work/release_evidence/20260628-waveform-prefetch-cache/
work/release_evidence/20260628-waveform-prefetch-cache-benchmark/
```

Key evidence:

```text
work/release_evidence/20260628-waveform-prefetch-cache/waveform_workbench_e2e_result.json
work/release_evidence/20260628-waveform-prefetch-cache-benchmark/waveform_latency_benchmark.json
```

Static checks:

```text
node --check frontend/waveform-workbench-adapter.js
node --check frontend/waveform-workbench.js
node --check scripts/e2e_waveform_workbench_module.mjs
node --check scripts/benchmark_waveform_workbench_latency.mjs
```

All passed.

Browser E2E:

```text
status=passed
checks=41
failed=[]
```

New performance assertion:

```json
{
  "id": "T-PERF-02-wheel-pan-uses-cache-hit-not-legacy-task",
  "passed": true,
  "waveformLastReloadSource": "cache_hit",
  "waveformCacheHits": 1,
  "waveformChunkRequests": 0,
  "waveformChunkFallbacks": 0
}
```

Benchmark:

```text
api.health: 13.4 ms
api.lab_demo_dataset: 711.2 ms
api.waveform_chunk_0_24_first: 64.8 ms
api.waveform_chunk_0_24_warm: 79.7 ms
browser.workbench: 1725.4 ms
```

Wheel state within benchmark:

```json
{
  "startSec": 1.92,
  "windowCoverage": "ready",
  "waveformSource": "waveform_chunk_api",
  "waveformLastReloadSource": "cache_hit",
  "waveformCacheHits": 1,
  "waveformChunkRequests": 0,
  "waveformChunkAborts": 0,
  "waveformChunkFallbacks": 0,
  "waveformPrefetchRequests": 0,
  "loadingState": "ready",
  "usesRemappedFallback": "false"
}
```

## Acceptance

Accepted for the current independent WaveformWorkbench slice:

- Cached wheel pan does not create a backend waveform request.
- Cached wheel pan does not fall back to the old QC task path.
- Cached wheel pan settles as `cache_hit`.
- First-screen waveform visibility remains covered by the previous pixel-level E2E check.
- Chunk API remains in the 60-80 ms range in this local teaching-data benchmark.

## Notes

`waveformPrefetchRequests` is `0` in the teaching benchmark because the teaching dataset already provides a 0-60s continuous cache. This is expected. On real long files, adjacent windows that are not covered by cache will be prefetched.

## Boundaries

No TimeChart integration.

No epilepsy source workbench work.

No gateway, Headroom, IPC, front-route, or model-route changes.

final_receipt: completed_waveform_workbench_prefetch_cache_fix_ready_for_acceptance
