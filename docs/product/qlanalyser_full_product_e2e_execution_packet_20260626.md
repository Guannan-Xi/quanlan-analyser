# QLanalyser Full Product E2E PDCA Execution Packet

Date: 2026-06-26
Source requirements: `docs/product/qlanalyser_full_product_e2e_requirements_20260626.md`
Source design: `docs/product/qlanalyser_full_product_e2e_design_20260626.md`
Source test plan: `docs/product/qlanalyser_full_product_e2e_test_plan_20260626.md`
Evidence root: `work/release_evidence/07-full-product-e2e-pdca`
Status: execution packet before current automation implementation

This packet binds the current full-product acceptance cycle to concrete scripts and evidence files. It prevents requirements from being carried only in chat.

## 1. Scope

The current cycle covers five PDCA tasks:

| Task | Requirement IDs | Output |
|---|---|---|
| Synthetic fixture and method execution | FR-3, FR-4, DS-T1 to DS-T6 | Synthetic EDF, method run evidence, source-comparison matrix |
| Main workbench and report chain | FR-5, FR-7, DS-T8, DS-T10 | Browser E2E evidence and report ZIP inventory |
| UI visual, color, state, and scroll review | FR-8, FR-9, DS-T2, DS-T7, DS-T9 | Screenshot manifest, scroll review, color audit |
| DeepSeek adoption verification | DS-T1 to DS-T10 | Method/UI adoption check JSON |
| Final acceptance packet | all above | `completed_final_receipt` or `blocked_final_receipt` JSON |

## 2. Non-Goals

- No router, Headroom, IPC, gateway, or process communication changes.
- No production deployment.
- No real customer EEG data.
- No clinical, diagnostic, causal, cohort-level, or source-localization validity claim.
- No broad cleanup of the existing dirty worktree.

## 3. UI Design Evidence Matrix

The UI review must capture these surfaces:

| Surface | Entry | Required states |
|---|---|---|
| Cover/login | `frontend/index.html`, entry demo pages | first viewport, login/entry, scrolled bottom |
| Main workbench | `dashboard`, `storage`, `analysis`, `workflow`, `statistics`, `publication`, `userCenter` | top, middle, bottom when scrollable |
| Admin/backstage | `adminDashboard`, `adminOperations`, `adminFinance`, `adminSystem` | role entry, table density, bottom scroll |
| QC/data preparation | `frontend/qc-lab.html` and main `analysis` view | preview, reversible action affordance, disabled/focus checks |
| Current modules/method lab | `workflow`, `module-lab.html`, `research-modules.html` | grouped methods, preview/review wording, details reachable |
| Method detail pages | `qc`, `psd`, `erp`, `tfr`, `pac`, `connectivity`, `source_localization` | long page, boundary copy, no horizontal overflow |

Viewports:

- `desktop-1440x1000`
- `laptop-1280x800`
- `mobile-390x844`
- `wide-1920x1080`

Color and token checks:

- Sidebar or active navigation may use navy, blue, cyan, or neutral.
- Green is reserved for success and must not be the primary active navigation color.
- Preview/review method badges must not look like success approval.
- Focus and disabled states must remain visible after scrolling.

## 4. Automation Design

| Script | Responsibility | Primary evidence |
|---|---|---|
| `scripts/run_full_product_method_source_comparison.py` | Run synthetic EDF full analysis, copy fixture, compare source runners and outputs | `05_methods/method_source_comparison_matrix.json` |
| `scripts/acceptance_full_product_ui_scroll_review.mjs` | Browser screenshot, scroll, overflow, active color, and state audit | `08_ui_visual_scroll/screenshot_manifest.json` |
| `scripts/build_full_product_e2e_acceptance_packet.py` | Aggregate docs, preflight, method, UI, report, DeepSeek, and E2E evidence | `10_acceptance_packet/full_product_e2e_acceptance_packet_20260626.json` |

Existing scripts remain part of the stack:

- `scripts/acceptance_synthetic_edf_full_analysis_scientific_figures.py`
- `scripts/acceptance_main_workbench_direct_method_clickthrough_e2e.mjs`
- `scripts/acceptance_edf_upload_to_results_ui_only.mjs`
- `scripts/run_full_product_e2e_preflight.py`
- `scripts/build_full_product_e2e_pdca_packet.py`

## 5. PDCA Rows

### PDCA-FX-MTH

Plan: Generate deterministic synthetic EDF and run every method supported by the current backend.

Do: Execute the synthetic full-analysis runner under the current PDCA evidence root.

Check:

- EDF exists and has checksum.
- 8 runnable backend method families pass.
- 9 UI method entries are represented by source-comparison rows, with multitaper PSD and multitaper TFR split at UI level but sharing backend module id.
- Figure audit has no blockers.

Act:

- If any method fails, final packet is blocked and names the method.
- If only source-reference anchors are weak, final packet records revise-required but may still accept workflow plumbing.

### PDCA-UI

Plan: Capture every major UI surface across desktop, laptop, mobile, and wide viewports.

Do: Browser automation opens the current local frontend and captures top/middle/bottom scroll positions where applicable.

Check:

- No horizontal overflow.
- No protected region is hidden behind sticky/fixed UI.
- Active navigation is not green.
- Customer surfaces do not expose admin navigation.
- Internal developer terms are not visible in default user copy.

Act:

- P0 UI blocker if a primary action is unreachable or content overlaps.
- P1/P2 findings are recorded for later UI polish if they do not block the workflow.

### PDCA-RPT

Plan: Prove current report generation, download, package structure, and claim boundary.

Do: Run the EDF upload-to-report browser E2E using the synthetic EDF when available.

Check:

- Report package and HTML preview links exist by stable DOM contract.
- ZIP header and required entries are valid.
- Report package includes task-linked analysis outputs.
- Forbidden overclaim scan passes.

Act:

- Stale copy assertions are fixed in acceptance scripts, not by changing user-facing wording.
- Unsafe scientific/clinical claim blocks final acceptance.

### PDCA-FINAL

Plan: Aggregate all evidence into one final machine-readable packet.

Do: Build `10_acceptance_packet/full_product_e2e_acceptance_packet_20260626.json`.

Check:

- Each required evidence file exists and has a status.
- Completed final receipt is allowed only with no P0 blockers.
- Historical evidence is labelled historical unless rerun in this cycle.

Act:

- Emit `completed_final_receipt` or `blocked_final_receipt`.
- List the next real artifact.

## 6. Verification Commands

```powershell
python -X utf8 scripts/build_full_product_e2e_pdca_packet.py
python -X utf8 scripts/run_full_product_e2e_preflight.py
python -X utf8 scripts/run_full_product_method_source_comparison.py
node --check scripts/acceptance_full_product_ui_scroll_review.mjs
node scripts/acceptance_full_product_ui_scroll_review.mjs
node --check scripts/acceptance_edf_upload_to_results_ui_only.mjs
node --check scripts/acceptance_main_workbench_direct_method_clickthrough_e2e.mjs
node scripts/acceptance_main_workbench_direct_method_clickthrough_e2e.mjs
node scripts/acceptance_edf_upload_to_results_ui_only.mjs
python -X utf8 scripts/build_full_product_e2e_acceptance_packet.py
```

Environment variables may redirect evidence into the PDCA root:

```text
QLANALYSER_SYNTHETIC_FIGURE_EVIDENCE_ROOT
QLANALYSER_MAIN_WORKBENCH_CLICK_E2E_DIR
QLANALYSER_EDF_E2E_DIR
QLANALYSER_UI_SAMPLE_EDF
QLANALYSER_FULL_UI_SCROLL_EVIDENCE_ROOT
```

## 7. Acceptance Rule

The final packet may report `completed_final_receipt` only when:

- documents and preflight pass;
- synthetic fixture is generated in this cycle;
- every method row is passed or explicitly split/covered by the backend family;
- main workbench direct method clickthrough passes or is exactly blocked;
- report chain and ZIP inventory pass;
- UI scroll/color review has no P0 blockers;
- DeepSeek adoption checks are represented in method/UI evidence.

## 8. Backend/Admin and Copy-Gap Closure Addendum

This addendum extends the same PDCA packet after the first completed synthetic acceptance. It is not a new product scope; it closes the missing standalone backend/admin evidence and makes product-wide copy governance an explicit acceptance check.

Additional commands:

```powershell
python -X utf8 scripts/check_running_backend_contract.py --base-url http://127.0.0.1:8001/api --evidence-dir work/release_evidence/07-full-product-e2e-pdca/04_backend_api
python -X utf8 scripts/run_full_product_backend_api_smoke.py
$env:QLANALYSER_COPY_GOVERNANCE_EVIDENCE_DIR="work/release_evidence/07-full-product-e2e-pdca/08_ui_visual_scroll"
node scripts/acceptance_product_wide_ux_copy_governance.mjs
python -X utf8 scripts/build_full_product_e2e_acceptance_packet.py
```

Additional acceptance requirements:

- `04_backend_api/backend_api_smoke.json` passes.
- `04_backend_api/running_backend_contract_check.json` passes when 8001 is available, or is explicitly absent while in-process backend smoke passes.
- `08_ui_visual_scroll/product_wide_ux_copy_governance.json` passes.
- final acceptance packet lists backend/admin and copy-governance checks.
