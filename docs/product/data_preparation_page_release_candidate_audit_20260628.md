# Data Preparation Page Release-Candidate Audit - 2026-06-28

## Scope

This audit focuses only on the main QLanalyser Data Preparation page:

`http://127.0.0.1:4174/?customer_demo=auto&teaching_demo=auto&api=http://127.0.0.1:8001/api&v=data-prep-rc-audit#analysis`

It reviews the page from four levels:

1. Global page structure.
2. Functional regions.
3. Individual interaction points.
4. End-to-end data-preparation workflow.

## Self-Adversarial Review Questions

### Global page

- Does the page make the selected data and waveform immediately understandable?
- Does it avoid horizontal overflow on desktop, laptop, and mobile?
- Does it avoid presenting a static image as if it were a waveform workbench?
- Does it avoid mixing preparation-plan status with waveform-browsing status?

### Functional regions

- Are the data queue, progress steps, waveform, action panel, record/export section, and next-step section separated by priority?
- Is the waveform visually dominant enough for a data-preparation task?
- Are secondary record/export actions visually lower priority than the waveform and preparation confirmation?
- On mobile, is the waveform reachable without scrolling through every control first?

### Functional points

- Are write actions disabled until the user has a valid selection?
- Does wheel browsing update the Canvas without implying that the current waveform is "confirmed"?
- Does the time slider actually move the active window?
- Does a Canvas selection enable the candidate-bad-segment action?
- Does adding a candidate enable confirm-exclusion?
- Does confirming exclusion enable restore?

### Business workflow

- Teaching/demo data loads directly into the data-preparation page.
- Initial Canvas loads from lightweight chunk API.
- Initial Canvas does not create a heavy QC preview task.
- User can browse, drag time, select a segment, add a candidate, confirm exclusion, and see the right panel update.
- The professional WaveformWorkbench entry remains available.
- The downstream analysis entry remains available after preparation.

## Implemented Fixes During This Audit

1. Mobile waveform priority:
   - On narrow screens, the preview panel order is now:
     - title;
     - waveform Canvas;
     - time navigator/status/action panel;
     - controls.
   - The toolbar no longer appears before the waveform on mobile.

2. Mobile step compression:
   - Data-preparation steps become a compact 5-step progress strip on mobile.
   - Long step descriptions are hidden on mobile to reduce scroll cost.

3. Mobile preview caption compression:
   - The long preview caption is hidden on mobile.
   - The page keeps the title and professional-workbench entry.

4. Waveform status semantics:
   - The waveform status bar no longer shows preparation-plan confirmation such as `已确认 r1`.
   - Preparation-plan status remains in the right-side data-preparation panel.
   - Wheel browsing can no longer produce a confusing "confirmed waveform" impression.

## Evidence

Primary RC audit:

- Script: `scripts/audit_data_preparation_page_release_candidate.mjs`
- JSON: `work/release_evidence/20260628-data-preparation-page-rc-audit/data_preparation_page_rc_audit.json`
- Result: `passed`
- Failed checks: `[]`

Screenshots:

- Desktop 1440: `work/release_evidence/20260628-data-preparation-page-rc-audit/data_prep_rc_desktop_1440.png`
- Laptop 1280: `work/release_evidence/20260628-data-preparation-page-rc-audit/data_prep_rc_laptop_1280.png`
- Mobile 390: `work/release_evidence/20260628-data-preparation-page-rc-audit/data_prep_rc_mobile_390.png`
- Interaction flow: `work/release_evidence/20260628-data-preparation-page-rc-audit/data_prep_rc_interaction_flow.png`

Supporting Canvas E2E:

- Script: `scripts/e2e_main_data_prep_canvas_chunk_interaction.mjs`
- JSON: `work/release_evidence/20260628-main-data-prep-canvas-chunk/main_data_prep_canvas_chunk_interaction.json`
- Result: `passed`

Key RC checks:

```json
{
  "global_title_data_preparation": true,
  "global_no_horizontal_overflow": true,
  "global_no_static_image_preview": true,
  "global_canvas_visible_and_nonblank": true,
  "global_no_qc_task_for_initial_canvas": true,
  "global_chunk_api_used": true,
  "section_step_cards_present": true,
  "section_waveform_toolbar_slider_present": true,
  "section_right_action_panel_present": true,
  "section_old_duplicate_edit_workbench_hidden": true,
  "section_advanced_reference_collapsed": true,
  "section_secondary_record_panels_present": true,
  "function_preconditions_disable_write_actions": true,
  "function_wheel_pan_safe_status": true,
  "function_slider_drag_changes_position": true,
  "function_canvas_selection_enables_candidate": true,
  "function_candidate_enables_confirm": true,
  "function_confirm_candidate_enables_restore": true,
  "business_flow_primary_path_complete": true,
  "business_flow_analysis_entry_preserved": true,
  "mobile_canvas_reachable": true
}
```

## Release-Candidate Verdict

`data_preparation_page_rc_status = passed`

The Data Preparation page is acceptable as a page-level release candidate for internal/customer trial.

## Remaining Non-Blocking Follow-Up

- Filter preview still uses the heavier QC preview path; future work should add lightweight filtered chunks.
- The mobile toolbar is now after the waveform, but can later be folded into a compact disclosure if customer trials show the page still feels long.
- The page-level RC does not replace the full-product external release gate, which still depends on owner real-data regression.

## Boundary

This audit and fix did not touch router, Headroom, gateway, IPC, front-route, model route, TimeChart, or the epilepsy source workbench.
