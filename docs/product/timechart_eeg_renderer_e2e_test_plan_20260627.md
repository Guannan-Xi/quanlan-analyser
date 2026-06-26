# TimeChart EEG Renderer — E2E Test Plan

**Project:** QLanalyser EEG Waveform Workbench
**Candidate:** TimeChart (WebGL) with Canvas fallback
**Date:** 2026-06-27
**Status:** Pre-promotion evaluation

---

## 1. Scope & Assumptions

| Item | Value |
|------|-------|
| Renderer under test | `TimeChart` via `RendererAdapter` shim |
| Fallback renderer | Canvas 2D |
| Test runner | Playwright (Edge executable path per existing workaround) |
| No code edits | Adapter must wrap TimeChart without modifying QLanalyser core |
| Signal matrix | 8 / 32 / 64 / 128 channels × 10s / 60s / 300s × 200 / 500 / 1000 Hz |

---

## 2. Test Environment Setup

```
# Install TimeChart candidate
npm install timechart
npm audit --audit-level=moderate

# Verify adapter loads without touching core
node -e "require('./eeg_core/renderer/timechart_adapter')"
```

- Browser: Chromium (WebGL enabled), Edge (WebGL disabled via `--disable-webgl` flag for fallback path)
- Record: Playwright traces + `--video=retain-on-failure`
- Baseline screenshots stored in `tests/e2e/snapshots/`

---

## 3. Dependency, License & Security Gate

| Test ID | Check | Pass Criteria |
|---------|-------|---------------|
| DEP-01 | `npm audit` | Zero high/critical CVEs |
| DEP-02 | License scan (`license-checker`) | No GPL-3, AGPL, or unknown licenses |
| DEP-03 | Bundle size delta | TimeChart adds ≤ 150 kB gzipped to vendor chunk |
| DEP-04 | Peer dependency conflicts | `npm install` exits 0, no `ERESOLVE` |
| DEP-05 | Sub-dependency tree depth | No new transitive deps with known CVE in OSV database |

**Evidence:** `npm-audit.json`, `license-report.json`, webpack bundle stats saved to `tests/evidence/deps/`.

---

## 4. Functional Tests

### 4.1 Renderer Adapter Contract

| Test ID | Scenario | Assertion |
|---------|----------|-----------|
| FUNC-01 | Adapter instantiates with 8-channel EEG fixture | `adapter.isReady === true` within 2 s |
| FUNC-02 | `setWindow(start, end)` updates visible range | Canvas/WebGL frame repaints; x-axis ticks match `[start, end]` |
| FUNC-03 | `setChannels(channels)` adds/removes traces | Channel label count in DOM equals `channels.length` |
| FUNC-04 | `destroy()` removes all DOM nodes and listeners | `document.querySelectorAll('canvas').length === 0`; no console errors |
| FUNC-05 | Adapter exposes required windowed-waveform API surface | Duck-type check: `setWindow`, `setChannels`, `setMarkers`, `setBadSegments`, `setSelectedSegment`, `setBadChannels` all callable |

### 4.2 Stacked EEG Channels

| Test ID | Scenario | Assertion |
|---------|----------|-----------|
| FUNC-06 | 32 channels rendered stacked | 32 distinct y-offset traces visible; no overlap beyond configured spacing |
| FUNC-07 | Channel order matches metadata array order | Top channel label == `channels[0].label` |
| FUNC-08 | Amplitude scale toggle (µV / normalized) | Y-axis unit label updates; waveform peaks rescale proportionally |

### 4.3 Bad Segments

| Test ID | Scenario | Assertion |
|---------|----------|-----------|
| FUNC-09 | Single bad segment passed via `setBadSegments` | Overlay rectangle rendered at correct x-range with red/semi-transparent fill |
| FUNC-10 | Multiple overlapping bad segments | All segments drawn; no z-fighting artifacts (screenshot diff < 1%) |
| FUNC-11 | Bad segment outside current window | No overlay visible; no console error |

### 4.4 Selected Segment

| Test ID | Scenario | Assertion |
|---------|----------|-----------|
| FUNC-12 | `setSelectedSegment({start, end})` called | Highlighted region rendered with distinct border style |
| FUNC-13 | Selected segment updates on re-call | Previous highlight removed; new region shown |
| FUNC-14 | `setSelectedSegment(null)` clears selection | No selection overlay in DOM |

### 4.5 Event Markers

| Test ID | Scenario | Assertion |
|---------|----------|-----------|
| FUNC-15 | 10 event markers at known timestamps | 10 vertical lines at correct x-positions (±1 px tolerance) |
| FUNC-16 | Marker label text rendered | Label text matches marker `id` field |
| FUNC-17 | Markers outside window clipped | No lines outside canvas bounds |

### 4.6 Bad-Channel Styles

| Test ID | Scenario | Assertion |
|---------|----------|-----------|
| FUNC-18 | `setBadChannels(['Fp1','O2'])` | Those channel traces rendered in grey/dashed style |
| FUNC-19 | Good channel adjacent to bad channel | No style bleed onto good-channel trace |
| FUNC-20 | Clearing bad channels restores default style | All traces revert to default colour |

### 4.7 Overlay Sync

| Test ID | Scenario | Assertion |
|---------|----------|-----------|
| FUNC-21 | Scroll/pan updates all overlay layers simultaneously | Bad segment, selected segment, and event markers move with waveform — no offset drift |
| FUNC-22 | Window resize redraws overlays | Overlay x-positions recalculate correctly after viewport width change |

---

## 5. Canvas Fallback Tests

| Test ID | Scenario | Assertion |
|---------|----------|-----------|
| FALL-01 | WebGL disabled (`--disable-webgl`) | Adapter detects fallback; `renderer.type === 'canvas'` logged |
| FALL-02 | 8-channel render in Canvas mode | Waveform visible; channel labels present |
| FALL-03 | All FUNC-09 – FUNC-20 overlay tests repeated in Canvas mode | Same pass criteria |
| FALL-04 | No WebGL error messages in console | Zero `WebGL` or `CONTEXT_LOST` errors |
| FALL-05 | Performance within 2× WebGL baseline (32ch/60s/500Hz) | FPS ≥ 15 in Canvas mode |

---

## 6. Performance Benchmark Matrix

Metric collection: `window.performance.now()` around first-paint; `requestAnimationFrame` counter over 5 s scroll; Chrome DevTools trace via Playwright CDP.

**Targets:**

| Channels | Duration | Sample Rate | First-Paint (ms) | Scroll FPS | Memory (MB heap) |
|----------|----------|-------------|-----------------|------------|-----------------|
| 8 | 10 s | 200 Hz | ≤ 200 | ≥ 55 | ≤ 50 |
| 32 | 60 s | 500 Hz | ≤ 500 | ≥ 45 | ≤ 150 |
| 64 | 300 s | 500 Hz | ≤ 1000 | ≥ 30 | ≤ 300 |
| 128 | 300 s | 1000 Hz | ≤ 2000 | ≥ 20 | ≤ 500 |

| Test ID | Matrix Cell | Extra Assertion |
|---------|-------------|-----------------|
| PERF-01 – PERF-12 | Full 3×4 matrix (8/32/64/128 × 10s/60s/300s at 500 Hz) | All cells meet first-paint target |
| PERF-13 – PERF-15 | 32ch / 60s at 200 / 500 / 1000 Hz | FPS does not drop > 30% from 200→1000 Hz |
| PERF-16 | 128ch / 300s / 1000 Hz sustained 30 s scroll | No memory leak > 10% heap growth |
| PERF-17 | Rapid `setWindow` calls (50 calls/s for 5 s) | No frame drops below 10 FPS |

**Evidence:** JSON benchmark file per matrix cell saved to `tests/evidence/perf/`.

---

## 7. Visual / UX Tests

| Test ID | Scenario | Assertion |
|---------|----------|-----------|
| VIS-01 | Default 32ch render matches baseline screenshot | Pixel diff < 0.5% (Playwright `toHaveScreenshot`) |
| VIS-02 | Dark theme applied | Background colour matches design token `--color-bg-dark` |
| VIS-03 | Channel labels legible at 64 channels | Font size ≥ 8 px; no label overlap |
| VIS-04 | Horizontal scrollbar absent when window fills data | No scrollbar DOM element present |
| VIS-05 | Zoom in/out via `setWindow` shows smooth re-render | No flash/blank frame during transition (video review) |

---

## 8. Security Tests

| Test ID | Check | Assertion |
|---------|-------|-----------|
| SEC-01 | Marker label XSS: `id: '<img src=x onerror=alert(1)>'` | Label rendered as text; no script execution; CSP header present |
| SEC-02 | Channel label injection via metadata | Same as SEC-01 for channel names |
| SEC-03 | WebGL shader source not exposed | `gl.getShaderSource()` returns `null` in production build |
| SEC-04 | No `eval()` or `new Function()` in TimeChart bundle | `grep -rE 'eval\(|new Function\(' node_modules/timechart/dist/` returns empty |
| SEC-05 | Content-Security-Policy allows `unsafe-eval` requirement audit | If TimeChart requires `unsafe-eval`, flag as blocker |

---

## 9. Evidence Output

All artefacts written to `tests/evidence/` and committed to the PR:

```
tests/evidence/
  deps/npm-audit.json
  deps/license-report.json
  deps/bundle-stats.json
  perf/<matrix-cell>.json          # one per PERF-xx test
  screenshots/<test-id>-actual.png
  traces/<test-id>.zip             # Playwright trace
  security/csp-audit.txt
  SUMMARY.md                       # pass/fail table, blocker list
```

---

## 10. Promotion Gate

All items must be **PASS** before merging TimeChart into the EEG waveform workbench:

| Gate | Requirement |
|------|-------------|
| G-1 | DEP-01 (zero high/critical CVEs) |
| G-2 | DEP-02 (no copyleft licenses) |
| G-3 | All FUNC-xx tests pass in WebGL and Canvas modes |
| G-4 | All FALL-xx fallback tests pass |
| G-5 | PERF targets met for 8/32/64 channel tiers (128-ch advisory) |
| G-6 | SEC-01 – SEC-04 pass; SEC-05 no `unsafe-eval` requirement |
| G-7 | VIS-01 pixel diff < 0.5% |
| G-8 | `npm audit` clean in CI (blocking step in GitHub Actions) |

**Any G-1 – G-7 failure = promotion blocked.** 128-ch/300s/1000Hz performance misses are advisory and require documented justification.
