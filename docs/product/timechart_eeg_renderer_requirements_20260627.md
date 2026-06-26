# TimeChart EEG Renderer Requirements 2026-06-27

**Status:** Architecture review package only. This document does not approve main-workbench implementation.

**Independent Reviewer:** ClaudeCode Architecture Agent
**Review Date:** 2026-06-27
**Handoff Source:** 07-PM / QLanalyser Main Line

---

## Executive Summary

TimeChart is **conditionally suitable** as a WebGL renderer candidate for future large-file and multi-channel EEG waveform browsing in QLanalyser. However, it must enter only as an **isolated prototype** with mandatory Canvas fallback. Direct replacement of the current Canvas workbench is **not recommended**.

### Critical Decision

**Recommended Path:**
1. Maintain current Canvas renderer as stable default and mandatory fallback
2. Develop TimeChart integration only behind a renderer adapter in isolated prototype
3. Gate promotion on benchmark, overlay synchronization, dependency security, and UX validation

**Not Authorized:**
- Editing production workbench code (`frontend/app.js`, `frontend/index.html`)
- Installing TimeChart dependencies in main frontend package
- Replacing Canvas renderer
- Modifying router/Headroom/gateway/IPC/model routes

---

## 1. Product Problem Statement

### 1.1 Current State

QLanalyser's data-preparation workbench successfully delivers:
- Teaching/demo data with automatic waveform preview
- Interactive Canvas-based waveform display
- Drag-to-select segment interaction
- Segment deletion/restoration
- Bad-channel marking (non-destructive in teaching mode)
- Preview-only filtering
- Re-reference controls
- Synchronous overlay of preparation state

**Evidence:**
- `work/release_evidence/20260627-data-preparation-workbench/`
- `work/release_evidence/20260627-waveform-interaction/`

### 1.2 Performance Gap

User feedback indicates "slow loading" for:
- 32-128 channel EEG files
- 60-300 second viewing windows
- 500-1000 Hz display sampling rates
- Repeated pan/zoom/gain adjustments

### 1.3 Target Improvement

Enable smooth, responsive waveform browsing for:
- **Channels:** 8, 32, 64, 128
- **Windows:** 10s, 60s, 300s
- **Sampling:** 200, 500, 1000 Hz
- **Interactions:** Pan p95 ≤ 50ms, zoom p95 ≤ 50ms for 32ch/60s case

---

## 2. Scope and Boundaries

### 2.1 In Scope

**Functional:**
- WebGL-accelerated waveform line rendering
- EEG channel stacking (row-based display)
- Pan/zoom performance optimization
- Windowed data loading (not full-file browser load)
- Renderer adapter abstraction
- Product-owned overlay layer for EEG semantics
- Automatic Canvas fallback

**Non-Functional:**
- Benchmark matrix validation (8/32/64/128 channels)
- Dependency security audit
- License compatibility review
- Memory stability testing
- WebGL availability detection

### 2.2 Out of Scope

**Product Features (Not Renderer Concerns):**
- Analysis method implementation (PSD, ERP, connectivity)
- Data preparation workflow logic
- Project/file/task management
- Authentication/authorization
- Clinical diagnosis features
- Epilepsy source workbench

**Infrastructure (Protected):**
- Router modification
- Headroom modification
- Gateway/IPC changes
- Model route changes
- Main workbench code (`frontend/app.js`)

### 2.3 Non-Goals

This architecture review **does not**:
- Authorize production deployment
- Replace Canvas renderer
- Modify teaching mode data constraints
- Change QC/re-reference data-preparation semantics
- Install dependencies without isolated prototype approval

---

## 3. User Goals

### 3.1 Primary User Need

**As a neuroscience researcher**, I need to:
- Load large EEG files (32-128 channels, multi-minute recordings)
- Browse waveforms smoothly without UI freezes
- Identify bad channels and segments visually
- Select time segments for analysis
- Preview filter effects interactively
- Complete data preparation faster

### 3.2 Success Criteria

**Performance:**
- First render ≤ 1000ms for 32ch/60s/500Hz
- Pan/zoom p95 ≤ 50ms for 32ch/60s/500Hz
- No crashes or persistent freezes for 64ch/300s

**Correctness:**
- Overlay synchronization drift ≤ 20ms or ≤ 1 display sample
- Bad segment bands align with waveform time axis
- Selected segment boundaries accurate to display sampling
- Event markers appear at correct time positions

**Reliability:**
- Automatic Canvas fallback when WebGL unavailable
- Clear user feedback for loading/empty/error states
- No memory leaks across pan/zoom cycles
- Graceful degradation on low-end hardware

---

## 4. Functional Requirements

### 4.1 Renderer Coexistence (REQ-COEX)

**REQ-COEX-001:** System must support multiple renderer backends
- `canvas` (current stable, mandatory fallback)
- `timechart-webgl` (experimental, prototype/feature-flag only)
- `auto` (selection based on capability + benchmark gate)

**REQ-COEX-002:** Renderer selection must not alter data preparation semantics
- Selected segment state remains in QLanalyser workspace
- Bad channel lists remain in preparation draft
- Excluded segments remain in preparation revision
- Filter preview settings remain in preview state

**REQ-COEX-003:** Renderer switch must be non-destructive
- User can switch renderer without losing current work
- Fallback must preserve visible time window
- Fallback must preserve current gain/channel view
- Fallback message must be clear and actionable

### 4.2 Windowed Waveform API (REQ-WIND)

**REQ-WIND-001:** Renderer must consume bounded window payload, never full file

**Required Request Parameters:**
| Parameter | Type | Constraint |
|-----------|------|------------|
| `file_id` | string | Current EEG file identifier |
| `start_sec` | number | Window start time (≥ 0) |
| `duration_sec` | number | Window duration (1-600s) |
| `display_sfreq` | number | Display sampling rate (50-2000 Hz) |
| `channel_limit` | number | Visible channel count (1-256) |

**Optional Request Parameters:**
- `channel_offset`: Starting channel index for pagination
- `channel_names`: Explicit channel subset
- `filter_preview`: Preview-only filter parameters
- `revision`: Preparation revision identifier

**Required Response Fields:**
| Field | Type | Meaning |
|-------|------|---------|
| `file_id` | string | Source file echo |
| `start_sec` | number | Actual window start |
| `duration_sec` | number | Actual window duration |
| `source_sfreq` | number | Original sampling rate |
| `sfreq_display` | number | Downsampled rate |
| `times_sec` | number[] | Time vector (display samples) |
| `channels` | string[] | Channel names |
| `data_uv` | number[][] | Channel-major microvolts [ch][sample] |
| `unit` | string | Amplitude unit |
| `events` | object[] | Event markers in window |
| `bad_channels` | string[] | Known bad channels |
| `preview_only` | boolean | Filter preview flag |
| `cache_key` | string | Backend cache identifier |
| `warnings` | string[] | Non-fatal issues |

**REQ-WIND-002:** Backend must enforce windowing
- Browser must never load full large EEG files
- Backend must downsample to `display_sfreq` before transmission
- Payload size target: ≤ 2 MB per window for 64ch/300s case

### 4.3 EEG Channel Stacking (REQ-STACK)

**REQ-STACK-001:** Display must present EEG as stacked channel rows, not single y-axis chart
- Each channel has stable row center coordinate
- Row order remains stable across gain changes
- Vertical spacing provides visual separation
- Channel labels remain readable during interactions

**REQ-STACK-002:** Gain must scale amplitude without reordering channels
- `gain = 1`: microvolts map to row-relative amplitude
- `gain = 2`: double amplitude, same channel order
- `gain = 0.5`: half amplitude, same channel order

**REQ-STACK-003:** Bad channel indication must be accessible
- Color difference alone is insufficient (WCAG compliance)
- Use color + pattern + label annotation
- Maintain contrast ratio ≥ 4.5:1 for text
- Provide non-visual encoding (aria labels)

**REQ-STACK-004:** Y-axis semantics differ from generic time series
- Y-range represents row coordinates, not physical amplitude scale
- Channel labels appear at row centers
- Y-zoom may be disabled or limited to prevent row collision

### 4.4 xRange and yRange Mapping (REQ-RANGE)

**REQ-RANGE-001:** Adapter must own canonical time/channel ranges

```javascript
xRange = [start_sec, start_sec + duration_sec]
yRange = [0, visibleChannelCount]
```

**REQ-RANGE-002:** TimeChart must receive pre-transformed coordinates
- x: relative seconds from window start
- y: row center ± normalized amplitude
- Transformation: `QLanalyser → Adapter → TimeChart`

**REQ-RANGE-003:** Pan/zoom interactions must emit canonical ranges back to QLanalyser
- TimeChart internal range changes trigger adapter events
- Adapter emits standard `xRangeChanged(start, end)` events
- QLanalyser decides whether to request new backend window
- Overlay layer consumes same canonical ranges

### 4.5 Overlay Layer (REQ-OVERLAY)

**REQ-OVERLAY-001:** Product must own overlay rendering, not TimeChart

**Overlay Items:**
- Selected segment: semi-transparent band with distinct color
- Excluded/bad segments: cross-hatched or stippled bands
- Event markers: vertical lines with labels
- Bad-channel row styles: row background or border
- Hover/cursor time readout: crosshair + time display
- Loading/error/fallback state: centered message overlay

**REQ-OVERLAY-002:** Overlay must use same coordinate mapping as renderer
```javascript
xPx = plotLeft + (timeSec - xRangeStart) / (xRangeEnd - xRangeStart) * plotWidth
yPx = plotTop + channelIndex * rowHeight + rowHeight / 2
```

**REQ-OVERLAY-003:** Overlay synchronization tolerance
- Drift ≤ 20ms or ≤ 1 display sample (whichever is larger)
- Measured after pan/zoom/resize interactions
- Failure triggers Canvas fallback

**REQ-OVERLAY-004:** Overlay must render above TimeChart canvas
```
Container (position: relative)
  ├─ TimeChart canvas (z-index: 1)
  ├─ SVG overlay for bands/markers (z-index: 2)
  ├─ HTML overlay for labels/chips (z-index: 3)
  └─ Interaction layer for drag selection (z-index: 4)
```

### 4.6 Interaction Design (REQ-INTERACT)

**REQ-INTERACT-001:** Pan and zoom must preserve QLanalyser state ownership
- User pans → TimeChart updates internal view → Adapter emits xRange → QLanalyser updates state → May request new window
- User zooms → Same pattern as pan

**REQ-INTERACT-002:** Drag-to-select must create selected segments
```
1. pointerdown on waveform → start selection
2. pointermove → draw temporary selection band
3. pointerup → convert pixel coordinates to [startSec, endSec]
4. Update QLanalyser selectedSegment state
5. Redraw overlay with finalized segment band
```

**REQ-INTERACT-003:** TimeChart native interactions must be controllable
- Ability to disable y-axis zoom (preserve row structure)
- Ability to constrain x-axis pan limits
- Ability to intercept zoom/pan for windowing logic
- Ability to disable tooltip if conflicts with EEG overlay

### 4.7 Fallback Controller (REQ-FALLBACK)

**REQ-FALLBACK-001:** Canvas fallback is mandatory, not optional

**Fallback Triggers:**
| Condition | Action |
|-----------|--------|
| WebGL unavailable | Immediate Canvas fallback on init |
| TimeChart import failure | Canvas fallback + dependency error log |
| TimeChart init exception | Canvas fallback + error telemetry |
| WebGL context lost | Canvas fallback + user notification |
| Benchmark gate failure | Keep prototype disabled, use Canvas |
| Overlay drift > tolerance | Canvas fallback after 3 consecutive failures |
| Memory pressure | Canvas fallback + reduce window size suggestion |

**REQ-FALLBACK-002:** Fallback must preserve user work
- Current time window position
- Current gain and channel visibility
- Selected segment
- Bad channel markings
- Excluded segments

**REQ-FALLBACK-003:** Fallback message must be safe and clear
- No local file paths
- No stack traces
- No authentication tokens
- No raw EEG data snippets
- Example: "已切换到稳定 Canvas 波形预览；当前数据和准备记录不受影响。"

**REQ-FALLBACK-004:** Fallback must be testable
- Manual WebGL disable mechanism for testing
- Simulated context loss trigger
- Dependency import failure injection
- Fallback reason must be logged for debugging

---

## 5. Non-Functional Requirements

### 5.1 Performance (NFR-PERF)

**Benchmark Matrix:**
| Case ID | Channels | Duration | Display Hz | Total Points | Purpose |
|---------|----------|----------|------------|--------------|---------|
| TCR-001 | 8 | 10s | 200 | 16,000 | Basic correctness |
| TCR-002 | 32 | 60s | 500 | 960,000 | Target workload |
| TCR-003 | 64 | 300s | 500 | 9,600,000 | Stress test |
| TCR-004 | 128 | 300s | 1000 | 38,400,000 | Extreme stress |

**Performance Gates:**
| Metric | TCR-001 | TCR-002 | TCR-003 | TCR-004 |
|--------|---------|---------|---------|---------|
| Data conversion | ≤ 50ms | ≤ 200ms | ≤ 800ms | ≤ 2000ms |
| First render | ≤ 200ms | ≤ 1000ms | ≤ 3000ms | ≤ 8000ms or fallback |
| Pan p95 | ≤ 20ms | ≤ 50ms | ≤ 100ms | ≤ 200ms or fallback |
| Zoom p95 | ≤ 20ms | ≤ 50ms | ≤ 100ms | ≤ 200ms or fallback |
| Overlay sync | ≤ 20ms | ≤ 20ms | ≤ 20ms | ≤ 20ms |

**NFR-PERF-001:** Minimum promotion gate
- TCR-002 (32ch/60s/500Hz) must pass all metrics
- TCR-003 (64ch/300s) must not crash or freeze
- TCR-004 (128ch/300s) may fallback but must fallback gracefully

**NFR-PERF-002:** Memory stability
- No monotonic memory growth across 20 pan/zoom cycles
- Memory delta after 20 cycles ≤ 2× baseline memory increase
- Destroy must release major references (testable in Chrome DevTools)

### 5.2 Dependency Security (NFR-SEC-DEP)

**Observed Metadata (npm view timechart@0.5.2):**
- Package: `timechart`
- Version: `0.5.2`
- License: `MIT`
- Unpacked size: ~467 KB
- Dependencies: `d3-axis`, `d3-color`, `d3-scale`, `d3-selection`, `gl-matrix`, `tslib`
- Repository: `https://github.com/huww98/TimeChart`

**NFR-SEC-DEP-001:** Installation restrictions
- Install only in isolated prototype branch/package
- Pin exact versions in package-lock.json
- Do not install in production frontend without security clearance

**NFR-SEC-DEP-002:** Security audit required
- Run `npm audit --json` in isolated prototype
- Document all vulnerabilities (including transitive dependencies)
- Prior handoff reported "high vulnerabilities" during trial
- Blocking: Any unreviewed HIGH or CRITICAL findings prevent promotion

**NFR-SEC-DEP-003:** License compliance
- TimeChart: MIT ✓
- All transitive dependencies must be compatible with QLanalyser license
- Generate and review license inventory
- Store license summary in evidence package

**NFR-SEC-DEP-004:** Supply chain
- Use official npm registry or approved internal mirror
- Verify package integrity (checksum validation)
- Document dependency provenance

### 5.3 Privacy and Data Protection (NFR-SEC-PRIV)

**NFR-SEC-PRIV-001:** Test data restrictions
- Prototype benchmarks must use synthetic data or approved teaching data
- Never write raw customer EEG to benchmark artifacts
- Never include patient identifiers in logs or screenshots

**NFR-SEC-PRIV-002:** Error message sanitization
- No local file paths in user-facing errors
- No stack traces in user-facing errors
- No authentication tokens or session IDs
- No raw EEG data values in error messages

**NFR-SEC-PRIV-003:** Browser security
- Check CSP (Content Security Policy) implications of WebGL
- Verify no third-party CDN loading in production
- Document WebGL security considerations

### 5.4 Accessibility (NFR-A11Y)

**NFR-A11Y-001:** Visual contrast
- Channel waveforms: contrast ratio ≥ 3:1 against background
- Text labels: contrast ratio ≥ 4.5:1
- Selected/bad segments: contrast ratio ≥ 3:1

**NFR-A11Y-002:** Non-color encoding
- Bad channels: color + pattern/icon + label suffix
- Selected segment: color + border + aria-label
- Excluded segment: color + cross-hatch + aria-label

**NFR-A11Y-003:** Keyboard navigation
- Tab through interactive elements
- Keyboard shortcuts for common actions (if applicable)
- Focus indicators visible

**NFR-A11Y-004:** Screen reader support
- Canvas/WebGL fallback description
- Segment selection announced
- Loading/error states announced

### 5.5 Browser Compatibility (NFR-COMPAT)

**NFR-COMPAT-001:** WebGL support detection
- Test on Chrome/Edge (Chromium)
- Test on Firefox
- Test on Safari (if macOS available)
- Test on remote desktop (WebGL often disabled)
- Test on low-end GPUs

**NFR-COMPAT-002:** Graceful degradation
- WebGL unavailable → Canvas
- WebGL context loss → Canvas
- Old browser → Canvas
- Remote desktop → Canvas (with explanation)

---

## 6. Acceptance Criteria

### 6.1 Architecture Document Approval Gates

07-PM must approve:
1. ✓ Isolated prototype approach (no main workbench replacement)
2. ✓ Canvas fallback retained
3. ✓ Renderer adapter contract documented
4. ✓ Windowed payload contract documented
5. ✓ Overlay synchronization testable
6. ✓ Dependency/security gates explicit
7. ✓ Benchmark evidence path defined

### 6.2 Prototype Development Gates

Before starting prototype:
- [ ] This requirements document accepted by 07-PM
- [ ] Detailed design document accepted by 07-PM
- [ ] E2E test plan accepted by 07-PM
- [ ] Architecture review JSON accepted by 07-PM
- [ ] Prototype branch created (isolated from main)
- [ ] Prototype package.json created (separate from frontend/package.json)

### 6.3 Prototype Promotion Gates

Before integrating into main workbench:
- [ ] All TCR-001 through TCR-004 benchmarks executed
- [ ] TCR-002 performance gates passed
- [ ] TCR-003 stability gates passed
- [ ] `npm audit` cleared or exceptions documented
- [ ] License inventory approved
- [ ] Overlay synchronization drift ≤ tolerance
- [ ] Fallback tested and functional
- [ ] Screenshots reviewed for UX clarity
- [ ] 07-PM explicit approval

---

## 7. Comparison with Alternative Approaches

### 7.1 TimeChart vs. Other Candidates

| Library | WebGL | Time-Series Focus | EEG Suitability | Risk |
|---------|-------|-------------------|-----------------|------|
| **TimeChart** | ✓ | ✓ High | Medium (needs adapter + overlay) | Dependency audit needed |
| uPlot | ✗ Canvas | ✓ Medium | Medium-High (proven, lighter) | Lower risk, lower perf ceiling |
| webgl-plot | ✓ | ✓ Low-level | High (custom control) | High dev cost |
| ChartGPU | ✓ WebGPU | ✓ High | Low (browser compat risk) | WebGPU adoption too early |
| Squiggly | N/A | N/A | N/A (reference only) | Not a library |

**Recommendation:** TimeChart is the first candidate for WebGL path, but uPlot remains viable as lower-risk alternative if TimeChart fails gates.

### 7.2 Why Not Direct Replacement?

**Risks of replacing Canvas directly:**
1. No fallback if WebGL fails in production
2. Dependency vulnerabilities affect all users
3. Overlay synchronization issues block all workflows
4. Regression testing burden on entire workbench
5. Difficult rollback if problems discovered post-deployment

**Benefits of adapter approach:**
1. Canvas remains proven fallback
2. TimeChart isolated to opt-in users
3. A/B testing possible
4. Independent iteration
5. Easy rollback

---

## 8. Recommendation

### 8.1 Proceed to Isolated Prototype

**Recommendation: CONDITIONAL YES**

Proceed to isolated prototype development with these constraints:
- **Do not** integrate into main workbench yet
- **Do not** install dependencies in production frontend
- **Do** build standalone prototype page + benchmark runner
- **Do** implement renderer adapter contract
- **Do** prove Canvas fallback works
- **Do** collect benchmark evidence
- **Do** complete dependency security audit

### 8.2 Evidence Required for Promotion

Before production integration:
1. `benchmark_summary.json` with all TCR cases
2. `dependency_audit.json` from `npm audit`
3. `license_inventory.json` for all dependencies
4. `overlay_sync_report.json` with drift measurements
5. Screenshots of all states (ready/loading/error/fallback)
6. Browser compatibility matrix
7. 07-PM written approval

### 8.3 Blocking Risks

**STOP conditions (do not proceed to production):**
- [ ] Unresolved HIGH/CRITICAL npm audit findings
- [ ] TCR-002 performance gates fail repeatedly
- [ ] Overlay drift > tolerance in 64ch case
- [ ] No functional Canvas fallback
- [ ] Memory leaks detected
- [ ] License incompatibility found

---

## 9. Next Steps for 07-PM

If this requirements document is accepted:

1. **Review Phase (this document)**
   - Review requirements document ✓
   - Review detailed design document
   - Review E2E test plan document
   - Review architecture JSON

2. **Prototype Phase (after approval)**
   - Create isolated prototype branch
   - Set up prototype package.json
   - Implement renderer adapter skeleton
   - Implement TimeChart adapter
   - Implement Canvas adapter (use existing code)
   - Implement overlay layer
   - Build benchmark runner
   - Execute benchmark matrix

3. **Evidence Phase**
   - Collect all benchmark data
   - Run npm audit
   - Generate license inventory
   - Capture screenshots
   - Write evidence summary

4. **Decision Phase**
   - Review evidence against gates
   - Decide: promote / iterate / abandon
   - If promote: plan feature flag rollout
   - If iterate: identify failure causes
   - If abandon: document lessons learned

---

## Appendix A: Glossary

- **Canvas:** HTML5 Canvas 2D rendering context (current stable renderer)
- **TimeChart:** WebGL-based time-series charting library (candidate renderer)
- **Renderer Adapter:** Abstraction layer isolating QLanalyser from specific renderer implementation
- **Overlay Layer:** Product-owned visual elements rendered above waveform (segments, markers, labels)
- **Windowed API:** Backend API returning bounded time window of EEG data, not full file
- **Display Sampling:** Downsampled data sent to browser for rendering (e.g., 500 Hz display from 2000 Hz source)
- **Channel Stacking:** EEG visualization technique where each channel occupies a horizontal row
- **Gain:** Amplitude scaling factor (gain=2 doubles visible amplitude)
- **Bad Channel:** Channel marked as unreliable/noisy during data preparation
- **Excluded Segment:** Time range marked for removal during data preparation
- **Selected Segment:** Time range highlighted for analysis or annotation

---

## Document Control

- **Version:** 1.0
- **Status:** Architecture Review - Awaiting 07-PM Approval
- **Author:** ClaudeCode Architecture Agent (Independent Review)
- **Date:** 2026-06-27
- **Handoff Source:** `docs/product/timechart_webgl_renderer_handoff_to_claudecode_20260627.md`
- **Related Documents:**
  - `timechart_eeg_renderer_detailed_design_20260627.md`
  - `timechart_eeg_renderer_e2e_test_plan_20260627.md`
  - `work/release_evidence/20260627-timechart-renderer-review/claudecode_architecture_review.json`
