# QLanalyser E2E Failure Classification Receipt - 2026-06-28

## Scope

This receipt covers the low-risk refactor that separates browser E2E failures into machine-readable release-gate classes.

## Status Classes

- `passed`: the product path passed.
- `environment_blocked`: the runner cannot resolve or launch Playwright/browser dependencies.
- `service_unreachable`: frontend/backend service or API health is unreachable.
- `product_failed`: services and runner are available, but product assertions failed.

`acceptance_verdict` remains `passed` or `failed` so report aggregators can read a simple verdict while still preserving the failure class.

## Changed Files

- `scripts/lib/playwright_runtime.mjs`
  - Added `classifyAcceptanceFailure(error, evidence)`.
  - Added `isAcceptancePassedStatus(status)`.
  - Changed Playwright resolution to lazy launch-time loading so scripts can still import the classifier and write classified evidence when Playwright is missing.
- `scripts/acceptance_edf_upload_to_results_ui_only.mjs`
  - Uses the shared classifier for exception exits and top-level launch/import exits.
  - Emits `acceptance_verdict` and `failure_class`.
  - Uses `product_failed` instead of the generic `failed` status when product checks fail.

## Verification

- `node --check scripts/lib/playwright_runtime.mjs`: passed.
- `node --check scripts/acceptance_edf_upload_to_results_ui_only.mjs`: passed.
- `node --check frontend/app.js`: passed.
- `node scripts/audit_frontend_design_debt_static.mjs`: `passed_with_known_debt`, unexpected duplicate count `0`.
- `node scripts/e2e_data_prep_interaction_controls_state_matrix.mjs`: passed.
- Classifier smoke without configured Playwright module path:
  - Importing `classifyAcceptanceFailure` does not crash.
  - Playwright package error -> `environment_blocked`.
- Classifier smoke with configured Playwright module path:
  - Playwright package error -> `environment_blocked`.
  - Connection refused error -> `service_unreachable`.
  - Product assertion error -> `product_failed`.

## Remaining Follow-Up

The classifier can now be imported without Playwright installed because Playwright is loaded lazily at browser launch time.

Next migration targets:

- `scripts/acceptance_data_prep_analysis_entry_consistency_e2e.mjs`
- `scripts/acceptance_full_product_ui_scroll_review.mjs`
- `scripts/acceptance_main_workbench_direct_method_clickthrough_e2e.mjs`

## Boundary

No router, Headroom, gateway, IPC, front-route, model route, or epilepsy workbench implementation was changed in this slice.
