# Main Data Preparation Waveform Canvas Migration Receipt - 2026-06-28

## Scope

The main QLanalyser Data Preparation page now embeds the real WaveformWorkbench Canvas path instead of behaving like a static preview image.

Main test URL:

`http://127.0.0.1:4174/?customer_demo=auto&teaching_demo=auto&api=http://127.0.0.1:8001/api&v=main-epilepsy-entry#analysis`

## Implemented

- The main page Canvas `#eegCanvas` loads waveform data through the lightweight chunk API:
  - `GET /api/eeg/files/{file_id}/waveform/chunk`
  - mode: `minmax`
  - no initial `qc_waveform_preview` task is created for normal unfiltered Canvas preview.
- The initial teaching/demo data selection automatically renders a non-blank Canvas waveform.
- Wheel/keyboard/slider interactions update the Canvas viewport state.
- The bottom time navigator is an actual draggable control:
  - dragging updates the visible time-window skeleton immediately;
  - release commits the new window and reloads a real chunk.
- The strengthened E2E now proves:
  - wheel pan requests/updates the Canvas viewport;
  - time-slider drag changes the active position;
  - candidate actions are disabled before a Canvas selection;
  - Canvas selection enables candidate action;
  - adding a candidate enables confirm-exclusion;
  - the right-side processing panel reflects the Canvas selection;
  - the professional WaveformWorkbench entry remains present.
- The old duplicate "segment/tag/bad-channel" card grid is hidden from the customer-facing flow.
- The primary decision surface is now the "Next Processing" panel:
  - add candidate bad segment;
  - confirm exclusion;
  - restore exclusion;
  - mark bad channel;
  - confirm data preparation.
- Invalid edit actions are disabled until their prerequisites exist.
- Repeated metadata chips and preview-strip details are visually collapsed from the main flow.
- Event chips are summarized instead of listing many per-event tags under the waveform.
- Toolbar layout is organized as a responsive workbench grid.

## Evidence

Canvas/chunk E2E:

- Script: `scripts/e2e_main_data_prep_canvas_chunk_interaction.mjs`
- JSON: `work/release_evidence/20260628-main-data-prep-canvas-chunk/main_data_prep_canvas_chunk_interaction.json`
- Screenshot: `work/release_evidence/20260628-main-data-prep-canvas-chunk/main_data_prep_canvas_chunk_interaction.png`

Latest result:

```json
{
  "status": "passed",
  "checks": {
    "chunk_api_used": true,
    "no_qc_task_for_initial_canvas": true,
    "canvas_non_blank": true,
    "no_static_image_preview": true,
    "interaction_updates_canvas_state": true,
    "slider_drag_changes_position": true,
    "wheel_pan_requests_chunk": true,
    "add_candidate_disabled_until_selection": true,
    "confirm_candidate_enabled_after_candidate": true,
    "right_panel_reflects_canvas_selection": true,
    "professional_workbench_entry_present": true
  },
  "network": {
    "chunk": 2,
    "qcTask": 0
  }
}
```

Viewport/design cleanup:

- Script: `scripts/review_main_workbench_design_cleanup_viewports.mjs`
- JSON: `work/release_evidence/20260628-main-workbench-design-cleanup/main_workbench_design_cleanup_viewports.json`
- Result: `passed`, `failed=[]`

Epilepsy entry preservation:

- Script: `scripts/e2e_main_epilepsy_entry_contract.mjs`
- JSON: `work/release_evidence/20260628-main-epilepsy-entry-contract/main_epilepsy_entry_contract.json`
- Result: `passed`
- Confirmed:
  - epilepsy method card is visible;
  - QC is not treated as a method card;
  - epilepsy payload uses `module_name=epilepsy_ml`;
  - epilepsy payload uses `workflow_id=epilepsy_ml_xgboost`;
  - non-medical boundary is preserved;
  - result area exposes `epilepsy-workbench.html?...renderer=canvas...`.

Syntax checks:

- `node --check frontend/app.js`
- `node --check scripts/e2e_main_data_prep_canvas_chunk_interaction.mjs`
- `node --check scripts/e2e_main_epilepsy_entry_contract.mjs`

## Files Changed

- `frontend/app.js`
- `frontend/styles.css`
- `docs/product/main_data_preparation_waveform_canvas_migration_receipt_20260628.md`

Existing current-slice files also include:

- `frontend/index.html`
- `scripts/e2e_main_data_prep_canvas_chunk_interaction.mjs`

## Remaining Follow-Up

- The main data preparation workbench is now functional and Canvas-backed, but the toolbar can still be refined for a more compact expert-reader density after user trial.
- Filter preview still falls back to the heavier QC preview task path by design; this should later get a lightweight filtered chunk API.
- External release remains blocked by the known owner real-data regression manifest gap, not by this Canvas migration slice.

## Boundary

This slice did not touch router, Headroom, gateway, IPC, front-route, model route, TimeChart, or the epilepsy source workbench.
