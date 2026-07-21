# QLanalyser Real Dataset Owner Review Requirements

Date: 2026-06-26
Owner: 07-PM / QLanalyser acceptance
Source: `work/release_evidence/07-full-product-e2e-pdca/10_acceptance_packet/full_product_e2e_acceptance_packet_20260626.json`
Evidence root: `work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review`

This document starts the next PDCA cycle after synthetic full-product acceptance. It is a requirements source, not a chat summary.

## 0. Product Boundary

QLanalyser remains a non-medical EEG research and CRO workflow tool. Real or representative datasets may support workflow regression and owner release review, but they do not create clinical, diagnostic, causal, source-localization, or cohort-validity claims.

## 1. PDCA Rule

| Phase | Required artifact | Pass condition |
|---|---|---|
| Plan | Owner data-input requirements and acceptance scope | Data authorization, anonymization, allowed methods, and stop conditions are explicit |
| Do | Owner manifest, dataset inventory, preflight, and later regression run evidence | No dataset is used unless the owner manifest explicitly authorizes it |
| Check | JSON evidence, source/path checks, method/run eligibility, report/UI review references | Synthetic/test/demo files are not mislabelled as real data |
| Act | completed input gate, blocked receipt, or regression acceptance packet | If data are missing, the blocker names the exact owner input needed |

## 2. Requirements

### RD-1. Owner Authorization Gate

- A dataset is eligible only if an owner manifest says it is authorized for QLanalyser regression.
- The manifest must state whether the file is anonymized, whether it contains PHI/customer-sensitive data, and which methods may be run.
- Local files found by scanning the repo are candidates only; scanning does not grant permission.

### RD-2. Data Privacy and Anonymization Gate

- The owner manifest must include a privacy assertion for each file.
- File names and directory paths should avoid personal names, hospital identifiers, phone numbers, emails, exact birth dates, or customer names.
- If any privacy field is unknown, the dataset is blocked until reviewed.

### RD-3. Method Regression Scope

For each eligible dataset, run the full method stack when scientifically appropriate:

- QC / data preparation
- PSD
- ERP when event markers exist
- TFR when event markers and epoch length are sufficient
- Multitaper PSD
- Multitaper TFR when event markers and epoch length are sufficient
- Reference / CSD when channel metadata are sufficient
- PAC
- Connectivity

If a method is scientifically inappropriate for a dataset, the packet must mark it as `skipped_with_reason`, not `passed`.

### RD-4. Report and Figure Review

- Real-dataset report outputs must pass the same report inventory, forbidden-claim scan, and scientific-figure gate used in synthetic E2E.
- Figures must keep axes, units, legends/colorbars, method boundaries, and non-clinical interpretation notes.
- Real-dataset evidence must not expose raw local paths or sensitive identifiers in owner-facing summaries.

### RD-5. Owner Release Review

The owner-facing packet must say:

- what data were used;
- what methods ran;
- what methods were skipped and why;
- what report/UI/figure checks passed;
- what risks remain before pilot/release.

The packet may report release readiness only after a human owner confirms the dataset and residual risk.

## 3. Stop Conditions

Emit `blocked_final_receipt` when:

- no owner manifest exists;
- no dataset is explicitly authorized;
- any authorized file is missing;
- anonymization is unknown or false without an approved exception;
- method eligibility cannot be decided from the available metadata;
- real-dataset output contains unsafe clinical/causal/source-localization claims.

## 4. Authorized Regression Runner Requirements

The product must provide a repeatable local runner for the stage after owner authorization:

```powershell
python -X utf8 scripts/run_real_dataset_regression_from_manifest.py --input-manifest work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json
```

Required behavior:

- The runner must execute the input gate first and must not register data, create tasks, or create reports if the input gate is blocked.
- When the input gate is blocked, it must still write deterministic blocked evidence under `02_regression/`, `03_reports/`, and `05_owner_packet/`.
- When the input gate passes, it must register only manifest-authorized datasets into the local backend service layer.
- It must run only methods listed in each dataset's `allowed_methods`.
- Event-dependent methods (`erp`, `tfr`, `multitaper_tfr`) must be skipped, not failed, when `event_markers_available` is not true.
- Method failures must be recorded at method level so one real dataset issue does not hide the rest of the matrix.
- At least one completed method and one valid report package are required before the real-dataset stage can produce `completed_final_receipt`.
- The report package scan must confirm required entries and must scan for unsupported clinical, diagnostic, causal, source-localization, p-value, and statistical-significance claims.

Required evidence:

```text
02_regression/real_dataset_regression_run.json
03_reports/real_dataset_report_inventory.json
05_owner_packet/real_dataset_owner_review_final_packet.json
```

The runner is a local acceptance tool. It does not certify scientific validity, cohort validity, clinical use, diagnosis, treatment, source localization, or statistical significance.
