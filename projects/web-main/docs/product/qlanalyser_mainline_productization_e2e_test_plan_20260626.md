# QLanalyser Mainline Productization E2E Test Plan

Date: 2026-06-26
Source requirements: `docs/product/qlanalyser_mainline_productization_requirements_20260626.md`
Source design: `docs/product/qlanalyser_mainline_productization_design_20260626.md`
Status: validation contract before productization implementation

## 1. Test Goal

Validate that QLanalyser mainline now behaves like a user-facing EEG research workbench:

- the main customer path closes from EDF upload to report package
- data selection triggers preview automatically
- reversible data preparation edits work
- all 9 accepted methods appear under "Current available modules"
- preview/review methods are clearly bounded
- UI copy is user language, not developer language
- color and navigation follow the product design tokens
- scientific charts and reports avoid unsafe color and claims

## 2. Evidence Root

All fresh evidence for this release cycle must be written under:

```text
work/release_evidence/07-mainline-productization/formal_e2e_YYYYMMDD/
```

Recommended subdirectories:

```text
customer_edf_path/
data_preparation_auto_preview/
current_available_modules/
module_lab_9_methods/
ui_visual_color/
report_science_zip/
claim_boundary/
release_gate/
```

Do not treat older checkpoint evidence as current release evidence unless the test plan explicitly marks it as historical context.

## 3. Preflight

Commands:

```powershell
python -X utf8 scripts\check_no_mojibake.py docs\product\qlanalyser_mainline_productization_requirements_20260626.md docs\product\qlanalyser_mainline_productization_design_20260626.md docs\product\qlanalyser_mainline_productization_e2e_test_plan_20260626.md
node --check frontend\app.js
node --check frontend\module-lab.js
node --check scripts\acceptance_module_lab_grouped_methods_e2e.mjs
```

Pass:

- all command statuses are 0
- no mojibake markers in the new docs
- syntax checks pass

## 4. Test Matrix

| ID | Requirement | Test type | Script |
|---|---|---|---|
| T1 | Main customer path closure | Browser E2E | `scripts/acceptance_edf_upload_to_results_ui_only.mjs` or replacement |
| T2 | Click data -> auto preview | Browser E2E | `scripts/acceptance_data_preparation_auto_preview.mjs` |
| T3 | Current available modules include 9 entries | DOM/browser scan | `scripts/acceptance_current_available_modules_9_methods.mjs` |
| T4 | Preview/review status visible | DOM/browser scan | `scripts/acceptance_current_available_modules_9_methods.mjs` |
| T5 | Bad channel restore | Browser E2E | `scripts/acceptance_data_preparation_bad_channel_restore.mjs` |
| T6 | Segment restore | Browser E2E | `scripts/acceptance_data_preparation_segment_restore.mjs` |
| T7 | Event label restore | Browser E2E | `scripts/acceptance_data_preparation_event_label_restore.mjs` |
| T8 | User-language copy governance | Static + browser scan | `scripts/acceptance_product_wide_ux_copy_governance.mjs` |
| T9 | Button governance | Static + browser scan | `scripts/acceptance_product_ux_button_governance.mjs` |
| T10 | Color/nav token governance | Static + browser scan | existing color governance scripts |
| T11 | Module Lab 9 grouped methods | Full browser/API E2E | `scripts/run_module_lab_acceptance_stack.py` |
| T12 | Report ZIP inventory | File/API check | `scripts/report_zip_evidence_matrix.py` |
| T13 | Scientific chart color audit | JSON/image metadata check | new or existing scientific colormap audit runner |
| T14 | Forbidden-claim scan | Static/report package scan | release no-misclaim scan or replacement |
| T15 | Final release packet | Aggregator | `scripts/run_release_review_gate.py` or productization aggregator |
| T16 | Main workbench direct method entries | Static DOM/handler scan | `scripts/acceptance_main_workbench_direct_method_entries_9_methods.mjs` |

## 5. Detailed Cases

### T1. Main customer EDF path

Steps:

1. Start backend and frontend with the standardized local stack.
2. Generate or select a synthetic EDF.
3. Upload EDF or select existing generated EDF.
4. Select the data row.
5. Wait for automatic preview.
6. Confirm data preparation.
7. Run one stable method: PSD.
8. Run one event method when event data exists: ERP.
9. Open result review.
10. Generate and download report package.

Assertions:

- no required click on "Run QC preview"
- result review has method name, source data, parameters, quality hint
- report package exists
- no clinical/diagnostic claim appears

Evidence:

```text
customer_edf_path/customer_edf_path.json
customer_edf_path/customer_edf_path.png
customer_edf_path/downloaded_report_inventory.json
```

### T2. Data auto preview

Steps:

1. Open data preparation.
2. Click a data row.
3. Do not click preview/QC buttons.
4. Wait for preview state.

Assertions:

- waveform or preview placeholder is visible
- channel count, sampling rate, duration, and event count are visible when available
- loading state names the operation
- error state gives recovery action
- `run-qc-preview-inline` is absent as primary or only appears as secondary reload

### T3/T4. Current available modules with 9 entries

Required labels:

- 数据准备与质量检查
- PSD / Bandpower
- ERP / P300
- TFR / ERSP / ITC
- Multitaper PSD
- Multitaper TFR
- Reference / CSD
- PAC / CFC
- Connectivity

Required statuses:

- Preparation step for QC
- Available for PSD and ERP
- Preview, needs review for TFR, Multitaper PSD, Multitaper TFR, Reference / CSD, PAC, Connectivity

Forbidden main-card terms:

- runner
- workflow id
- module id
- `/api/tasks`
- manifest
- acceptance
- gate
- debug
- fake
- mock
- demo-only
- 内部测试
- 开发验收

Allowed only in collapsed details:

- backend module
- workflow
- task id
- artifact id

Evidence:

```text
current_available_modules/current_available_modules_9_methods.json
current_available_modules/current_available_modules_desktop.png
current_available_modules/current_available_modules_mobile.png
```

### T5. Bad channel restore

Steps:

1. Select a data file.
2. Wait for preview.
3. Mark one channel as bad.
4. Verify waveform/list visual state.
5. Verify edit record includes before/after and restore.
6. Restore channel.
7. Verify active bad-channel list no longer includes it.
8. Verify history retains restore record.

### T6. Segment restore

Steps:

1. Select a time range.
2. Exclude the segment.
3. Verify overlay and preparation plan.
4. Restore the segment.
5. Verify overlay removed and active exclusion removed.
6. Verify history retains before/after.

### T7. Event label restore

Steps:

1. Select an event marker or event row.
2. Add or rename label.
3. Verify waveform/marker list updates.
4. Restore previous label.
5. Verify before/after history remains.

### T8. User-language copy governance

Surfaces:

- login
- project management
- data management
- data preparation
- analysis tasks
- current available modules
- result review
- report delivery
- personal center
- admin pages
- method center

Checks:

- main text uses user action language
- all merged methods are discoverable in `当前可用模块`
- main analysis badge says `当前可用：9 项分析能力，预览方法需复核`
- preview status is `预览方法，需复核`, not `beta`
- internal words are not visible on customer main surfaces or method-preview pages
- visible copy avoids `workflow`, `runner`, raw API route, `module id`, `方法分支`, `分析任务工作台`, `真实后端任务`, `参数回显`, `产物证据`, `API 服务`, `Research Module`, `Workflow contract`, `测试输入数据`, and `合成科研测试数据`
- no clinical, causality, exact localization, or universal validity claims

### T9. Button governance

Checks:

- each work area has no more than one primary button
- automatic actions are not primary buttons
- destructive actions are secondary/danger with confirmation where applicable
- disabled buttons explain why
- download/audit/log controls are grouped under details or report delivery

### T10. Color/nav governance

Reuse:

```powershell
node scripts\acceptance_customer_workspace_color_governance.mjs
node scripts\acceptance_customer_workspace_color_browser_offline.mjs
node scripts\acceptance_customer_sidebar_navigation_governance.mjs
```

Additional assertions:

- sidebar active state is navy/blue or neutral, not green
- green appears only for success
- preview/review badge is not green
- focus ring visible

### T11. Module Lab 9 grouped methods

Command:

```powershell
python -X utf8 scripts\run_module_lab_acceptance_stack.py
```

Expected:

- visible-fields passed
- layout review passed
- generated EDF passed
- grouped methods E2E passed
- group count = 9
- picker count = 0
- errors = 0

### T12. Report ZIP inventory

Command:

```powershell
python -X utf8 scripts\inventory_latest_edf_e2e_report_zip.py
python -X utf8 scripts\report_zip_evidence_matrix.py
```

Expected report package includes:

- HTML report
- figures
- tables/CSV
- method text
- parameters
- software versions
- workflow/provenance
- processing record

### T13. Scientific chart color audit

Each generated chart must record:

- artifact path
- data relationship
- unit/range/baseline
- colormap/palette
- colorbar/legend/direct label
- non-color encoding
- boundary statement

Blockers:

- rainbow/jet without explicit justified exception
- missing unit/range/colorbar
- color implies diagnosis/causality/localization

### T14. Forbidden claim scan

Scan targets:

- UI visible copy
- method cards
- result review
- report HTML/Markdown/PDF text if generated
- figure captions
- package README/manifest

Blockers:

- diagnosis/treatment/clinical decision
- causality/proof/mechanism confirmed
- exact source localization without source evidence
- universal performance claim
- synthetic/demo result represented as validation

### T15. Final release packet

The final packet must include:

- requirements path
- design path
- test plan path
- commands run
- evidence paths
- screenshots
- failures and blockers
- accepted/rejected status per task
- final decision: accepted, accepted with residual risk, or blocked

### T16. Main workbench direct method entries

Steps:

1. Open the main workbench analysis task page.
2. Inspect `当前可用模块` and confirm it contains QC plus 8 analysis methods.
3. Inspect `选择分析方法` and confirm it contains direct actions for the 8 analysis methods.
4. Confirm QC is treated as a preparation step, not a duplicate analysis button.
5. Confirm preview methods are labelled as review-needed actions.

Assertions:

- Direct actions exist for PSD, ERP, TFR, Multitaper PSD, Multitaper TFR, Reference / CSD, PAC, and Connectivity.
- Action handlers map to the correct backend workflow.
- `multitaper_psd` and `multitaper_tfr` remain separate user actions while sharing backend module `multitaper_psd_tfr`.
- Empty-state and result-review copy does not imply only PSD/ERP/TFR/PAC exist.

Evidence:

```text
current_available_modules/main_workbench_direct_method_entries_9_methods.json
```

## 6. PDCA Checkpoints

| Task | Check artifact | Pass condition |
|---|---|---|
| Main customer path | customer path JSON + screenshot | full path complete without preview button dependency |
| Controlled preview methods | current module JSON + screenshot | 9 entries and review boundaries visible |
| Reversible edits | edit/restore JSON + screenshot | all three edit types restore and history preserved |
| UI/color governance | token/color/nav JSON + screenshots | no green sidebar residue, no button overload |
| Formal E2E | release matrix packet | all rows fresh or explicitly blocked |

## 7. Stop Rules

Stop and produce a `blocked_final_receipt` if:

- local service cannot start after two bounded attempts
- browser E2E cannot reach the app after two bounded attempts
- generated EDF cannot be read by the current backend
- a P0 forbidden claim remains unresolved
- a preview method cannot be safely represented without misleading status copy

## 8. Manual Acceptance Script

1. Open the local product URL.
2. Log in as customer.
3. Open or create a project.
4. Upload/select EDF.
5. Confirm data row click shows preview automatically.
6. Mark and restore a bad channel.
7. Exclude and restore a segment.
8. Rename and restore an event label.
9. Open Analysis Tasks.
10. Confirm Current Available Modules shows 9 entries.
11. Confirm preview methods say "needs review".
12. Run PSD.
13. Open Result Review.
14. Generate and download report package.
15. Confirm no diagnostic, treatment, causality, or exact localization claim appears.

Pass means a researcher can complete the path without asking a developer what to click.
