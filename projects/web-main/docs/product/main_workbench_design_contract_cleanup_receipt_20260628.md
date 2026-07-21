# QLanalyser Main Workbench Design Contract Cleanup Receipt

Date: 2026-06-28

Scope:
- Main workbench `#analysis` data preparation surface.
- Keep the current Canvas waveform workbench, teaching sandbox data, and preparation plan workflow intact.
- Do not touch router, Headroom, gateway, IPC, model route, TimeChart, or epilepsy source workbench.

## Design Contract Applied

Reference documents:
- `DESIGN.md`
- `docs/product/qlanalyser_project_design_system_20260628.md`
- `docs/product/qlanalyser_design_contract_main_workbench_audit_20260628.md`

Applied rules:
- One function has one primary place.
- Default customer UI should show decision information, not engineering/debug state.
- Waveform and scientific evidence stay primary.
- Status text must not duplicate nearby controls.
- Secondary record/export actions should be visually lower priority than waveform review and preparation confirmation.

## Changes Made

1. Waveform status bar deduplication
   - `frontend/app.js`
   - `renderWaveformWorkbenchStatus()` now keeps only selected segment, non-empty draft state, confirmed preparation plan state, write-mode safety, or explicit messages.
   - Repeated mode/time/window/channel/sensitivity/raw/reference information is no longer shown in the status bar.
   - Confirmed plan text was shortened from the repeated form `准备准备方案：已确认 r1` to `方案已确认 r1`.

2. Secondary record panels lowered
   - `frontend/index.html`
   - `frontend/styles.css`
   - The lower `preprocessing-readiness-panel`, `event-epoch-panel`, and `data-preparation-submit-last` panels keep their test IDs and workflow hooks, but are visually demoted as record/export guidance instead of competing primary action panels.

3. E2E contract updated
   - `scripts/e2e_main_data_prep_waveform_visible.mjs`
   - The test now checks that status text does not duplicate `s/page`, channel count, `uV/row`, `Raw`, or browse-mode text.
   - It allows meaningful status such as confirmed preparation plan.

4. Viewport evidence added
   - `scripts/review_main_workbench_design_cleanup_viewports.mjs`
   - Captures desktop, laptop, and mobile screenshots.
   - Checks horizontal overflow and visible customer-facing debug terms.

## Verification

Evidence directory:
- `work/release_evidence/20260628-main-workbench-design-cleanup/`

Passed checks:
- `node --check frontend/app.js`
- `node --check scripts/e2e_main_data_prep_waveform_visible.mjs`
- `node --check scripts/review_main_workbench_design_cleanup_viewports.mjs`
- Browser E2E: `main_data_prep_waveform_visible_e2e.json`, status `passed`
- Viewport matrix: `main_workbench_design_cleanup_viewports.json`, status `passed`

Screenshot evidence:
- `main_data_prep_waveform_visible.png`
- `desktop_1440_analysis_top.png`
- `laptop_1280_analysis_top.png`
- `mobile_390_analysis_top.png`

Key observed values:
- Status text: `方案已确认 r1`
- Desktop horizontal overflow: false
- Laptop horizontal overflow: false
- Mobile horizontal overflow: false
- Forbidden debug terms found in visible body text: none

## Acceptance

Decision: `completed_main_workbench_design_contract_cleanup_packet_m_a_b`

Accepted:
- Teaching data still auto-loads into the main data preparation waveform.
- Waveform canvas remains visible.
- Status bar no longer repeats the time/window/channel/display controls.
- Confirmed preparation state remains visible because it affects the analysis gate.
- Lower duplicate panels are visually demoted without breaking their existing selectors or workflow hooks.
- Three viewport screenshots show no horizontal overflow.

Remaining follow-up:
- P1: visible control count is still high. The next design packet should group controls into clearer sections: Browse, Display, Mark/Edit, Preparation Settings, Confirm.
- P1: event/epoch save and record download can move into an expandable `Records and export` area once tests are updated.
- P1: mobile layout is functional but still dense; it should become a task-step layout rather than exposing all controls at once.
- P2: review remaining Chinese labels for consistent customer-facing wording and glossary alignment.

