# TimeChart EEG Renderer — Detailed Design

**Project:** QLanalyser EEG Waveform Workbench
**Date:** 2026-06-27
**Status:** Proposal

---

## 1. Architecture

The renderer stack is a thin adapter layer inserted between the existing waveform workbench and the underlying draw surface. No existing backend or analysis code is modified.

```
┌─────────────────────────────────────────┐
│          Waveform Workbench (host)       │
│   xRange · yRange · segments · events   │
└──────────────┬──────────────────────────┘
               │ RendererAdapter API
    ┌──────────┴──────────┐
    │  TimeChartRenderer  │   (WebGL, primary)
    └──────────┬──────────┘
               │ capability probe fails
    ┌──────────┴──────────┐
    │   CanvasRenderer    │   (Canvas 2D, fallback)
    └─────────────────────┘
               │ shared
    ┌──────────┴──────────┐
    │    OverlayLayer     │   (SVG / Canvas 2D)
    └─────────────────────┘
```

Both renderers implement an identical `IEEGRenderer` interface. The host always calls that interface; it never imports a concrete renderer directly.

---

## 2. Module Boundaries

| Module | Path | Responsibility |
|---|---|---|
| `RendererFactory` | `frontend/waveform/renderer/factory.ts` | Probe WebGL support, instantiate correct renderer |
| `IEEGRenderer` | `frontend/waveform/renderer/types.ts` | Shared interface + data types |
| `TimeChartRenderer` | `frontend/waveform/renderer/timechart.ts` | WebGL draw via TimeChart |
| `CanvasRenderer` | `frontend/waveform/renderer/canvas.ts` | Canvas 2D fallback |
| `OverlayLayer` | `frontend/waveform/renderer/overlay.ts` | SVG overlays: events, bad segments, selections |
| `DataTransform` | `frontend/waveform/renderer/transform.ts` | Windowed slice, normalisation, channel offsetting |

No module may import from `backend/`, `eeg_core/`, or any analysis service. The host passes pre-computed arrays; the renderer is display-only.

---

## 3. Adapter API (`IEEGRenderer`)

```typescript
interface WindowedData {
  channels: Float32Array[];   // one array per channel, same length
  channelLabels: string[];
  sampleRate: number;
  startSample: number;        // absolute sample index of window start
}

interface XRange { startSample: number; endSample: number; }
interface YRange { minUV: number; maxUV: number; }

interface BadSegment  { startSample: number; endSample: number; }
interface EventMarker { sample: number; label: string; color?: string; }
interface SelectedSegment { startSample: number; endSample: number; }

interface IEEGRenderer {
  /** Attach to a container element; called once. */
  mount(container: HTMLElement): void;

  /** Replace the visible window of EEG data. */
  setData(data: WindowedData): void;

  /** Pan / zoom: re-render within the current data window. */
  setXRange(range: XRange): void;
  setYRange(range: YRange): void;

  /** Overlay state updates — cheap, no GPU re-upload. */
  setBadSegments(segments: BadSegment[]): void;
  setSelectedSegment(seg: SelectedSegment | null): void;
  setEventMarkers(markers: EventMarker[]): void;
  setBadChannels(indices: number[]): void;

  /** Lifecycle. */
  resize(width: number, height: number): void;
  destroy(): void;
}
```

The host constructs the renderer via `RendererFactory.create(container)` and never touches `TimeChartRenderer` or `CanvasRenderer` directly.

---

## 4. Data Transform

`DataTransform` runs on the CPU before any draw call. Steps in order:

1. **Window slice** — extract `[startSample, endSample)` from the full buffer using typed-array subarray views (zero-copy where possible).
2. **Normalise** — map raw µV values to `[−1, 1]` within the supplied `yRange`. Bad channels receive a fixed centre-line value of `0` so they render as a flat line rather than noise.
3. **Channel offset** — add a per-channel vertical offset so channels stack without overlap. Offset stride = `2.0 / channelCount` in normalised space.
4. **Downsample guard** — if `pixelsPerSample < 1`, apply min/max decimation (Largest Triangle Three Buckets is out of scope; plain min/max suffices here) to keep the point count ≤ `containerWidth × 2`.

Output is a `Float32Array` of interleaved `(x, y)` pairs per channel, ready for direct upload to a TimeChart line series or Canvas `lineTo` loop.

---

## 5. Overlay Layer

The `OverlayLayer` is a transparent `<svg>` element positioned absolutely over the renderer canvas. It is renderer-agnostic.

**Bad segments** — semi-transparent red `<rect>` elements, `opacity: 0.18`, mapped from sample indices to pixel x-coordinates via a shared `sampleToX(s, xRange, width)` utility.

**Selected segment** — single blue `<rect>`, `opacity: 0.25`, updated on every `setSelectedSegment` call.

**Event markers** — vertical `<line>` elements at the marker sample, with a `<text>` label above. Labels longer than 12 characters are truncated with `…`.

**Bad channel rows** — a horizontal `<rect>` spanning the full width behind each bad channel row, `fill: #ff000010`. Row height = `containerHeight / channelCount`.

All SVG elements are drawn declaratively from a single `renderOverlay(state)` call that diffs the current DOM to minimise reflow. No animation framework is used.

---

## 6. Fallback Strategy

`RendererFactory` probes WebGL on module load:

```typescript
function supportsWebGL(): boolean {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') ?? c.getContext('webgl'));
  } catch { return false; }
}
```

If the probe fails (headless test environment, locked-down browser, integrated GPU driver denial), `CanvasRenderer` is returned. `CanvasRenderer` implements `IEEGRenderer` identically using `CanvasRenderingContext2D.lineTo`. Performance is acceptable for ≤ 32 channels at 250 Hz display rate; above that, the workbench should display a notice but remain functional.

The factory decision is logged to `console.info` to aid debugging. No silent fallback.

---

## 7. Interaction

The renderer itself is passive — it draws and does nothing else. Interaction is handled by the host workbench and communicated back through the adapter API:

| User action | Host responsibility | Adapter call |
|---|---|---|
| Horizontal pan | Compute new `xRange` | `setXRange(newRange)` |
| Vertical zoom | Compute new `yRange` | `setYRange(newRange)` |
| Click-drag selection | Resolve sample indices | `setSelectedSegment(seg)` |
| Window resize | Observe `ResizeObserver` | `resize(w, h)` |

The renderer must not attach its own mouse or keyboard listeners to the container. Pointer events pass through to the host.

---

## 8. Security

**Dependency gate** — TimeChart is pinned to an exact semver (`"timechart": "0.x.y"`) in `frontend/package.json`. Any update requires a manual review checklist item before merge.

**Supply chain** — `package-lock.json` is committed and checked in CI via `npm ci --ignore-scripts`. No postinstall scripts run from TimeChart or its transitive dependencies.

**XSS** — Event marker labels and channel labels are inserted into SVG as text content via `element.textContent`, never `innerHTML`. Any label containing `<`, `>`, or `&` is sanitised before insertion.

**Content Security Policy** — The renderer requires `webgl` in the `worker-src` / `script-src` directives. No inline `eval`, no `blob:` URLs. Document `unsafe-eval` is not required.

**Canvas fingerprinting** — The WebGL context is created with `{ preserveDrawingBuffer: false, antialias: false }` to minimise GPU fingerprint surface.

---

## 9. Benchmark Gates

A Playwright benchmark script (`frontend/tests/bench/renderer.bench.ts`) must pass before the rollout gate closes. Pass criteria:

| Metric | Target | Condition |
|---|---|---|
| First render latency | < 120 ms | 64-channel, 10 s window, cold start |
| Pan frame time | < 16 ms (p95) | Slide 1 s window, 100 iterations |
| Memory growth | < 5 MB / 60 s | Continuous pan, no leak |
| Canvas fallback parity | < 2× slower | Same benchmark on forced-fallback path |

Benchmarks run in CI on a fixed `--browser=chromium` runner. Results are written to `frontend/tests/bench/results.json` and diffed against the baseline committed at rollout start. A regression beyond threshold blocks merge.

---

## 10. Rollout

**Phase 1 (current sprint)** — Implement `IEEGRenderer`, `DataTransform`, `OverlayLayer`, and `CanvasRenderer`. No TimeChart dependency yet. All existing tests pass unchanged.

**Phase 2** — Add TimeChart as a dependency. Implement `TimeChartRenderer`. Feature-flagged behind `VITE_TIMECHART=1` env var; default off.

**Phase 3** — Run benchmarks on a representative dataset. Fix any regressions.

**Phase 4** — Enable by default. Remove the feature flag. Keep `CanvasRenderer` as the probe-fail path permanently.

No changes to `backend/`, `eeg_core/`, or any analysis pipeline at any phase.

---

## 11. Conclusion

The adapter boundary cleanly decouples the draw engine from the rest of the workbench. The host calls one interface; the implementation can be swapped or extended without touching analysis logic. The `CanvasRenderer` fallback ensures no user is left with a broken view. Overlay, interaction, security, and benchmark requirements are addressed at the design level, reducing integration risk before a single line of WebGL code is written.
