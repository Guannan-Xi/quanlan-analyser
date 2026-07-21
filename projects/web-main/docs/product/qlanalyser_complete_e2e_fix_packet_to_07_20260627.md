# QLanalyser Complete E2E Fix Packet to 07 - 2026-06-27

## Verdict from Complete Review

Current status:

- P0 fix package: accepted.
- Internal development: `pass_with_risks`.
- Complete external release: `blocked`.

This packet converts the complete review into concrete 07-PM development and test work.

Primary review artifacts:

- `docs/product/qlanalyser_full_product_complete_e2e_review_20260627.md`
- `work/release_evidence/20260627-full-product-complete-review/complete_review_result.json`
- `work/release_evidence/20260627-full-product-complete-review/claude_complete_review.md`
- `work/release_evidence/20260627-full-product-complete-review/browser_dom/browser_dom_inventory.json`

## Release Blockers for 07

### B1. Real anonymized owner-data regression is missing

Evidence:

- `python -X utf8 scripts/run_real_dataset_regression_from_manifest.py`
- Result: `blocked_final_receipt`
- Blocker: `input_manifest.json is missing`

Required 07 action:

1. Define the expected owner regression input manifest path and schema.
2. Ask owner/data steward for authorized anonymized EEG input.
3. Add manifest only after authorization; do not commit raw private data.
4. Rerun the real dataset regression.
5. Produce a final owner regression evidence packet.

Acceptance:

- `scripts/run_real_dataset_regression_from_manifest.py` returns passed.
- Evidence includes manifest path, anonymization statement, checksums or stable IDs, analysis outputs, report package, and non-medical claim scan.

### B2. Browser E2E infrastructure is not release-ready

Evidence:

Several active scripts still hardcode:

`../frontend/node_modules/playwright`

Known examples:

- `scripts/acceptance_click_only_user_journey.mjs`
- `scripts/acceptance_customer_login_demo.mjs`
- `scripts/acceptance_customer_preset_analysis.mjs`
- `scripts/acceptance_customer_workspace_color_browser_offline.mjs`
- `scripts/acceptance_customer_sidebar_navigation_governance.mjs`
- `scripts/acceptance_data_preparation_ux_repair_browser.mjs`
- `scripts/acceptance_edf_upload_to_results_ui_only.mjs`
- `scripts/e2e_teaching_user_logic_journey.mjs`
- `scripts/ui_three_round_coverage.mjs`
- `scripts/virtual_reviewer_p0_ui_only_runner.mjs`
- `scripts/virtual_reviewer_vr_itc_0001.mjs`
- `scripts/virtual_reviewer_pac_beta_ui_only_runner.mjs`

Required 07 action:

1. Create or reuse a shared Playwright loader helper.
2. Support package import first.
3. Support system Edge fallback.
4. Do not install dependencies as part of this fix unless explicitly approved.
5. Migrate all active browser E2E scripts or mark obsolete scripts clearly.

Acceptance:

- `rg -n "frontend/node_modules/playwright" scripts -S` has no active script hits.
- Active browser scripts either run or produce a clear `skipped_unavailable` receipt with documented runner reason.
- At least the following are rerun:
  - data-prep analysis entry E2E
  - sidebar/navigation governance
  - login demo
  - upload-to-results UI journey
  - teaching user logic journey

### B3. Product-wide copy governance is out of sync

Evidence:

- `node scripts/acceptance_product_wide_ux_copy_governance.mjs`
- `node scripts/acceptance_customer_pages_user_copy_governance.mjs`
- Current failure includes stale expectations:
  - old `9 项分析能力`
  - old `预览方法，需复核`
  - old `试用 ...` method wording

Current product contract:

- 8 formal analysis methods.
- QC is a data-preparation dependency, not an analysis method card.
- Method wording should be research-facing and non-medical.

Required 07 action:

1. Update copy governance scripts and docs to the current 8-method/QC-dependency contract.
2. Decide whether button copy such as `可运行 ERP` / `可运行 TFR` is acceptable or should become more research-workflow wording.
3. Remove stale 9-method release text.
4. Keep non-medical and non-causal boundaries visible.

Acceptance:

- Product-wide copy governance passes.
- Customer-pages copy governance passes.
- `current_available_modules_9_methods` validator still passes, or is renamed if 07 chooses to remove the legacy filename.

## Non-Blocking UX Fixes

### N1. Login page default error copy

Issue:

Default login screenshot can show:

`操作未完成，请检查信息后重试`

This appears before a meaningful failed operation and may confuse first-time users.

Suggested fix:

- Hide the error slot by default.
- Show only after a real failed submit.

### N2. Mobile navigation state

Issue:

On mobile data-preparation screenshots, the top dark navigation area can show personal-center/account context while the active page is data preparation.

Suggested fix:

- Keep only global navigation in the collapsed top area.
- Move personal-center detail card into the personal-center page body.

### N3. Mobile empty waveform height

Issue:

Before EEG data is selected, the empty waveform placeholder is tall and pushes segment/bad-channel controls far down.

Suggested fix:

- Use a compact empty state before data selection.
- Expand to full waveform height only after a file is selected or preview is loading.

### N4. favicon 404

Evidence:

- `http://127.0.0.1:4174/favicon.ico` returns 404.

Suggested fix:

- Add a small favicon asset or remove the implicit missing reference.

## Payload Gate Follow-Up

Source evidence confirms:

- `frontend/app.js` requires a confirmed data-preparation plan before the 8 formal analysis methods.
- `buildTaskParameters` writes:
  - `data_preparation_plan_id`
  - `data_preparation_revision`
  - `data_preparation_contract_version`
- `backend/services/task_service.py` stores plan id/revision and reads contract version from task parameters.

Remaining test-depth fix:

- Strengthen T-EDF-11 into a browser E2E that intercepts or inspects the actual `/tasks` submit payload.

Acceptance:

- Test proves unconfirmed data preparation blocks analysis.
- After confirmation, `/tasks` payload includes:
  - `data_preparation_plan_id`
  - `data_preparation_revision`
  - `data_preparation_contract_version == qlanalyser-data-preparation-v0.2`

## Rerun Checklist After Fix

Run and attach evidence:

```text
python -X utf8 scripts/run_full_product_e2e_preflight.py
python -X utf8 scripts/run_full_product_backend_api_smoke.py
python -X utf8 scripts/run_full_product_method_source_comparison.py
python -X utf8 scripts/acceptance_data_preparation_plan.py
node scripts/validate_edfbrowser_waveform_interaction_contract.mjs
node scripts/acceptance_current_available_modules_9_methods.mjs
node scripts/acceptance_product_wide_ux_copy_governance.mjs
node scripts/acceptance_customer_pages_user_copy_governance.mjs
python -X utf8 scripts/run_real_dataset_regression_from_manifest.py
```

Also rerun all active browser E2E scripts after Playwright loader cleanup.

## Return Packet Required from 07

07 should return:

```json
{
  "final_receipt": "completed_complete_e2e_release_blocker_fixes_ready_for_acceptance",
  "changed_files": [],
  "blockers_fixed": {
    "real_owner_regression": "passed or still blocked with owner reason",
    "browser_e2e_playwright_loader": "passed",
    "copy_governance_contract": "passed"
  },
  "evidence_paths": [],
  "remaining_risks": [],
  "ready_for_external_release_acceptance": true
}
```

If real owner data is still not available, use:

`blocked_complete_e2e_release_blocker_fixes_owner_data_missing`

and include the exact owner action needed.

## Boundary

Do not touch:

- router
- Headroom
- gateway
- IPC
- model route
- TimeChart integration
- epilepsy source workbench

Do not claim external release pass until the real owner regression and active browser E2E chain are both closed.
