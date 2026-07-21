# WaveformWorkbench Toolbar Progressive Disclosure Receipt

Date: 2026-06-28
Status: completed incremental cleanup

## Scope

This receipt covers the customer-facing cleanup of the WaveformWorkbench toolbar and repeated status information.

Protected areas were not touched:

- router
- Headroom
- gateway
- IPC
- model route
- TimeChart
- epilepsy source workbench

## Design Rule Applied

The implementation follows the project `DESIGN.md` rule:

- waveform first;
- one function, one primary place;
- customer UI should not look like an internal debugging console;
- advanced controls should be available on demand, not compete with the signal.

## Fixes

1. Added progressive disclosure for narrow and embedded layouts.
   - Default view keeps only common controls: time window, amplitude preset, channel count, browse/select/bad-segment/bad-channel modes.
   - Less frequent controls move behind `More settings`: page jump buttons, event marker display, amplitude fine tuning, channel fine tuning, shortcut help, and Epoch settings.

2. Removed duplicated current-window text from the overview caption.
   - The overview strip remains the single primary place for time position and progress.
   - The caption now only states total duration, cache/read state, and event-layer policy.

3. Fixed CSS interference in narrow mode.
   - The old narrow rule forced range controls to stay hidden even after advanced settings were opened.
   - It now hides range controls only while advanced settings are collapsed.

4. Removed numeric toolbar headings.
   - Collapsed mode no longer shows `2. Adjust display` without `1. Browse continuous EEG`.
   - Headings now name tasks directly: browse, display, annotation/review.

5. Made the waveform primary on desktop and narrow layouts.
   - The waveform/review area now appears before the support toolbar at all widths.
   - The toolbar is a support surface, not the first-screen object.

6. Reduced empty-state clutter.
   - Empty draft boxes are hidden until a selection or draft exists.
   - Narrow layout hides the legend row by default so it does not compete with the waveform.

7. Kept the dual-mode product boundary.
   - Basic waveform preview remains the default and does not expose Epoch controls.
   - Epoch review remains available for epilepsy and sleep-staging style workflows.

8. Updated E2E interaction coordinates after the signal-first layout change.
   - The Epoch full test now recomputes the current Canvas position after toolbar mode changes.
   - This prevents stale coordinates from missing the waveform after the page scrolls.

## Evidence

Evidence folder:

`work/release_evidence/20260628-waveform-toolbar-progressive-disclosure/`

Main result:

`work/release_evidence/20260628-waveform-toolbar-progressive-disclosure/waveform_workbench_dual_mode_contract_result.json`

Screenshots:

- `01_basic_initial.png`
- `05_basic_narrow_signal_first.png`
- `05b_basic_narrow_advanced_open.png`
- `06_customer_basic_hidden_switch.png`

Validation summary:

- `node --check frontend/waveform-workbench.js`: passed
- `node --check scripts/lib/playwright_runtime.mjs`: passed
- `node --check scripts/e2e_waveform_workbench_dual_mode_contract.mjs`: passed
- `scripts/e2e_waveform_workbench_dual_mode_contract.mjs`: passed, 24 checks, failed `[]`
- `scripts/e2e_waveform_workbench_module.mjs`: passed, output under `work/release_evidence/20260628-waveform-toolbar-progressive-disclosure/epoch-full-e2e/`

New checks added:

- `T-DUAL-16-narrow-default-uses-progressive-disclosure`
- `T-DUAL-17-overview-does-not-repeat-current-time-range`
- `T-DUAL-18-narrow-advanced-controls-expand-on-demand`
- `T-DUAL-14B-narrow-hides-empty-draft-and-legend-clutter`
- `T-DUAL-19-customer-desktop-keeps-waveform-before-toolbar`

## Remaining Follow-up

P1 follow-up is still useful, but no longer blocking this cleanup slice:

- connect the main data-preparation entry to `mode_switch=hidden`;
- add customer-mode screenshots for 1440, 1280, and 390 widths after the next route integration;
- decide whether Basic-to-Epoch debug switching should preserve or clear a normal time selection in production mode.

final_receipt: completed_waveform_toolbar_progressive_disclosure_ready_for_acceptance
