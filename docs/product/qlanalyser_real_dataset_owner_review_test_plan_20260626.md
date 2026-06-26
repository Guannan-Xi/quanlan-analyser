# QLanalyser Real Dataset Owner Review Test Plan

Date: 2026-06-26
Source requirements: `docs/product/qlanalyser_real_dataset_owner_review_requirements_20260626.md`
Source design: `docs/product/qlanalyser_real_dataset_owner_review_design_20260626.md`

## 1. Evidence Root

```text
work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/
```

Recommended structure:

```text
00_docs/
01_input_gate/
02_regression/
03_reports/
04_ui_visual/
05_owner_packet/
```

## 2. Input-Gate Tests

### RD-T1. Documentation and Template

Pass:

- requirements/design/test documents exist;
- `input_manifest.template.json` exists;
- `owner_input_checklist.md` exists.

Evidence:

```text
01_input_gate/real_dataset_owner_review_preflight.json
```

### RD-T2. Candidate Data Inventory

Pass:

- local candidate EDF/FIF/SET files are inventoried;
- obvious demo/synthetic/test files are labelled as not owner-authorized;
- no candidate file is used as real data without manifest approval.

Evidence:

```text
01_input_gate/candidate_data_inventory.json
```

### RD-T3. Owner Manifest Validation

Pass:

- `input_manifest.json` exists;
- `owner_confirmed_authorized=true`;
- each dataset path exists;
- each dataset has `anonymized=true` and `contains_phi=false`;
- allowed methods are explicit.

If no manifest exists, status must be `blocked_final_receipt` with exact owner action.

Evidence:

```text
01_input_gate/real_dataset_owner_review_preflight.json
05_owner_packet/real_dataset_owner_review_final_receipt.json
```

## 3. Regression Tests After Data Approval

Run only after input gate passes.

| ID | Scope | Pass condition |
|---|---|---|
| RD-R1 | QC/data preparation | Preview, preparation record, reversible bad-channel/segment/event edits if applicable |
| RD-R2 | PSD | Task completes, source/output contract matches, figures/tables valid |
| RD-R3 | ERP | Runs only if events exist; no-event state is explicit |
| RD-R4 | TFR | Runs only if events and epoch length support requested frequencies |
| RD-R5 | Multitaper PSD/TFR | Split UI actions map to backend family correctly |
| RD-R6 | Reference/CSD | Sensor/reference boundary visible |
| RD-R7 | PAC | Descriptive coupling boundary visible |
| RD-R8 | Connectivity | Sensor-space association boundary visible |
| RD-R9 | Report package | Inventory, claim scan, figure audit pass |
| RD-R10 | UI visual | Scroll/color/copy checks pass on result pages |

## 4. Runner Validation

### RD-R0. Missing-Manifest Safety Run

Command:

```powershell
python -X utf8 scripts/run_real_dataset_regression_from_manifest.py
```

Pass:

- command exits successfully by default because the blocked state is expected evidence, not a script crash;
- no backend analysis task is created from candidate-only local files;
- `02_regression/real_dataset_regression_run.json` exists and has `status=blocked_final_receipt`;
- `03_reports/real_dataset_report_inventory.json` exists and has `status=blocked`;
- `05_owner_packet/real_dataset_owner_review_final_packet.json` exists and has `final_receipt=blocked_final_receipt`;
- blockers include the missing or invalid manifest reason.

### RD-R4. Authorized Dataset Method Matrix

Precondition:

- `input_manifest.json` exists;
- `owner_confirmed_authorized=true`;
- each dataset path exists;
- each dataset is anonymized and has `contains_phi=false`;
- `allowed_methods` is explicit.

Command:

```powershell
python -X utf8 scripts/run_real_dataset_regression_from_manifest.py --input-manifest work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json --fail-on-blocked
```

Pass:

- the runner registers only datasets listed in the owner manifest;
- every allowed method has one matrix row;
- event-dependent rows are skipped when event markers are not confirmed;
- failures are method-level records, not silent omissions;
- completed rows have task ids and artifact inventories.

Evidence:

```text
02_regression/real_dataset_regression_run.json
```

### RD-R5. Report Package and Claim Scan

Pass:

- at least one completed task per dataset is used as the report seed when available;
- each generated report package includes `reports/report.html`, `reports/report_manifest.json`, `reports/report.json`, and `reports/report.pdf`;
- text-bearing report entries have no unsupported positive clinical, diagnostic, causal, exact source-localization, brain-region activation, p-value, or statistical-significance claims.

Evidence:

```text
03_reports/real_dataset_report_inventory.json
05_owner_packet/real_dataset_owner_review_final_packet.json
```

## 5. Final Rule

The owner packet may be `completed_final_receipt` for the input-gate setup even when real data are missing. It must be `blocked_final_receipt` for real-data regression until an authorized manifest is supplied.

## 6. Acceptance Commands

Run before accepting this PDCA slice:

```powershell
python -X utf8 -m py_compile scripts/run_real_dataset_regression_from_manifest.py scripts/build_real_dataset_owner_review_packet.py
python -X utf8 scripts/check_no_mojibake.py docs/product/qlanalyser_real_dataset_owner_review_requirements_20260626.md docs/product/qlanalyser_real_dataset_owner_review_design_20260626.md docs/product/qlanalyser_real_dataset_owner_review_test_plan_20260626.md scripts/run_real_dataset_regression_from_manifest.py
python -X utf8 scripts/run_real_dataset_regression_from_manifest.py
```

The final command must produce a blocked receipt until an owner-authorized manifest is present.
