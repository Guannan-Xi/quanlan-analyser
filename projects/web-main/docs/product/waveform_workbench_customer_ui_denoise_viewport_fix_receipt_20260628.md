# WaveformWorkbench Customer UI Denoise And Viewport Fix Receipt

Date: 2026-06-28

## Scope

This fix targets the standalone WaveformWorkbench customer-facing interface:

- `frontend/waveform-workbench.html`
- `frontend/waveform-workbench.css`
- `frontend/waveform-workbench.js`
- `scripts/e2e_waveform_workbench_module.mjs`
- `scripts/review_waveform_workbench_viewport_matrix.mjs`

No router, Headroom, gateway, IPC, model route, TimeChart, or epilepsy source-workbench files were touched in this slice.

## User Problem

The page still looked too much like an engineering control surface:

- Repeated status explanations appeared in the header, toolbar, status bar, and right panel.
- The toolbar consumed too much vertical space at laptop and mobile widths.
- The status bar exposed too many internal details for a customer default view.
- Disabled write buttons and draft metadata made the page feel noisy before the user selected a waveform segment.

## Product Decision

Default customer view should show only the information needed for the next decision:

1. Current dataset and safety boundary.
2. Main waveform canvas.
3. Browse/display/marking controls grouped by task.
4. One concise status row.
5. Right-side next-action panel.

Detailed interaction hints remain available through the shortcut help and test-facing `data-*` state, but are not shown as repeated default text in every toolbar group.

## Changes Made

### Toolbar Denoise

- Removed default visible helper text under every toolbar group.
- Reduced toolbar group padding and minimum control widths.
- Kept four task groups visible on desktop:
  - Browse
  - Display
  - Marking mode
  - Epoch
- Kept mobile controls operable while hiding advanced display sliders.

### Status Bar Denoise

- Removed the former extra metadata row.
- Kept status bar to a concise set:
  - Mode
  - Time window with `s/page`
  - Display summary
  - Selection
  - Draft count
  - Safety note

### Responsive Layout

- Desktop and 1280px laptop keep the toolbar compact enough for the waveform to remain visible in the first screen.
- 390px mobile no longer overflows horizontally and stays within the mobile toolbar-height guardrail.

### Test Contract Update

- Updated the E2E status-bar assertion so `Epoch` is no longer required in the status bar.
- Epoch remains visible in its own control group and in state data; it is not duplicated in the default status row.

## Verification

### Static Checks

Passed:

```text
node --check frontend\waveform-workbench.js
node --check scripts\e2e_waveform_workbench_module.mjs
node --check scripts\review_waveform_workbench_viewport_matrix.mjs
```

### Browser E2E

Passed:

```text
scripts\e2e_waveform_workbench_module.mjs
```

Evidence:

- `work/release_evidence/20260628-waveform-customer-ui-review-fix/waveform_workbench_e2e_result.json`
- Status: `passed`
- Checks: 41
- Failed: 0

Key screenshots:

- `work/release_evidence/20260628-waveform-customer-ui-review-fix/01_initial_loaded.png`
- `work/release_evidence/20260628-waveform-customer-ui-review-fix/04_after_write_mode_draft.png`

### Viewport Matrix

Passed:

```text
scripts\review_waveform_workbench_viewport_matrix.mjs
```

Evidence:

- `work/release_evidence/20260628-waveform-customer-viewport-matrix/viewport_matrix_result.json`
- Status: `passed`
- Failed: 0

Measured results:

| Viewport | Toolbar height | Horizontal overflow | Canvas ink ratio |
| --- | ---: | ---: | ---: |
| 1440 desktop | 206 px | 0 px | 0.2413 |
| 1280 laptop | 196 px | 0 px | 0.2618 |
| 390 mobile | 647 px | 0 px | 0.1188 |

Screenshots:

- `work/release_evidence/20260628-waveform-customer-viewport-matrix/desktop_1440_top.png`
- `work/release_evidence/20260628-waveform-customer-viewport-matrix/laptop_1280_top.png`
- `work/release_evidence/20260628-waveform-customer-viewport-matrix/mobile_390_top.png`

## Acceptance

Accepted for the current standalone WaveformWorkbench customer UI cleanup slice.

The page is now clearer and less redundant:

- The waveform appears in the first desktop viewport.
- Toolbar height is controlled at 1440 and 1280 widths.
- Mobile has no horizontal overflow and stays inside the agreed guardrail.
- The status bar no longer duplicates Epoch and internal cache/debug information.
- Functional E2E still passes after the UI denoise.

## Remaining Follow-Up

Mobile is acceptable for preview and light interaction, but still not ideal for dense EEG rejection work. A later product pass should decide whether mobile should become:

1. View-only plus simple navigation, or
2. A dedicated compact review workflow with collapsible panels.

This follow-up is not a blocker for the current desktop customer demo path.

Final receipt: `completed_waveform_workbench_customer_ui_denoise_viewport_fix`
