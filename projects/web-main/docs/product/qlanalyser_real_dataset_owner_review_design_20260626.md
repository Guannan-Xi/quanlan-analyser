# QLanalyser Real Dataset Owner Review Design

Date: 2026-06-26
Source requirements: `docs/product/qlanalyser_real_dataset_owner_review_requirements_20260626.md`
Evidence root: `work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review`

## 1. Design Goal

Create a safe bridge from synthetic full-product acceptance to owner-reviewed real or representative anonymized dataset regression.

The design intentionally separates three states:

```text
local file found -> owner-authorized dataset -> regression evidence
```

No local file becomes a real-dataset regression input without the middle owner-authorization state.

## 2. Data Intake Design

Required manifest:

```json
{
  "owner_confirmed_authorized": true,
  "owner": "Xi Guannan or delegated data owner",
  "authorization_note": "Dataset is anonymized and approved for local QLanalyser regression.",
  "datasets": [
    {
      "dataset_id": "owner_review_001",
      "path": "D:/path/to/anonymized.edf",
      "data_type": "edf",
      "anonymized": true,
      "contains_phi": false,
      "allowed_methods": ["qc", "psd", "erp", "tfr", "multitaper_psd", "multitaper_tfr", "reference_csd", "pac", "connectivity"],
      "event_markers_available": true,
      "channel_location_available": "unknown",
      "known_limitations": []
    }
  ]
}
```

Template path:

```text
work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.template.json
```

Active manifest path:

```text
work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json
```

## 3. Owner Review UI Sketch

This is an evidence packet layout, not a new app page yet:

```text
+--------------------------------------------------------------------------------+
| QLanalyser Owner Release Review                                                |
+--------------------------------------------------------------------------------+
| Dataset authorization | Privacy status | Method eligibility | Remaining risks   |
+--------------------------------------------------------------------------------+
| Dataset card: file alias, format, duration, channels, events, allowed methods   |
| Regression matrix: method -> run/skipped -> evidence -> reviewer note           |
| Report and figure gate: inventory, claim scan, scientific figure QA             |
| Owner decision: ready / revise / blocked                                        |
+--------------------------------------------------------------------------------+
```

Design rules:

- Use dataset aliases in summaries, not raw local paths.
- Show skipped methods as honest scientific decisions.
- Keep UI/report wording researcher-facing and non-clinical.
- Link back to synthetic full-product evidence instead of repeating large logs.

## 4. Execution Design

Stage 1: Input gate

- Scan local candidate EEG files.
- Classify obvious demo/synthetic/test files.
- Generate owner checklist and manifest template.
- Block if no authorized manifest exists.

Stage 2: Regression run, only after Stage 1 passes

- Register or upload authorized data through the existing backend/UI path.
- Run method matrix according to allowed methods and metadata.
- Build report package and run report/figure/UI gates.

Stage 3: Owner decision packet

- Summarize data, methods, evidence, and residual risks.
- Require owner decision before pilot/release wording.

## 5. Non-Goals

- No automatic use of local customer or uploaded data.
- No production deployment.
- No claim that synthetic or one real record proves method validity.
- No router, Headroom, IPC, or gateway changes.

## 6. Runner Architecture

Entrypoint:

```powershell
python -X utf8 scripts/run_real_dataset_regression_from_manifest.py --input-manifest work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json
```

The runner has a gate-first design:

```text
run input gate
  -> if blocked: write blocked regression/report/final packet evidence and stop
  -> if passed: register authorized dataset aliases
       -> run allowed method matrix
       -> build one report package per dataset from a completed seed task
       -> scan package entries and forbidden claims
       -> write final owner packet
```

### 6.1 Backend Integration Points

The runner uses existing service-layer functions only:

- `storage_service.upsert_project` creates or refreshes the local owner-review project.
- `storage_service.register_eeg_file` registers an authorized dataset with file alias, hash, metadata, and owner-review provenance.
- `metadata_service.extract_metadata` fills sampling rate, channel count, duration, and detected format when the file is readable.
- `task_service.create_task` runs analysis synchronously and returns a completed or failed task record.
- `task_service.list_task_artifacts` inventories output artifacts for the method matrix.
- `report_service.create_report` creates the local report package from a completed task.

### 6.2 Method Matrix Design

Allowed manifest methods map to the current backend modules:

| Manifest method | Backend module | Workflow | Gate |
|---|---|---|---|
| `qc` | `qc` | `metadata_qc` | always allowed |
| `psd` | `psd` | `resting_psd` | always allowed |
| `erp` | `erp` | `erp_p300` | requires `event_markers_available=true` |
| `tfr` | `tfr` | `tfr_ersp_itc` | requires `event_markers_available=true` |
| `multitaper_psd` | `multitaper_psd_tfr` | `multitaper_psd_tfr` | `analysis_family=psd` |
| `multitaper_tfr` | `multitaper_psd_tfr` | `multitaper_psd_tfr` | requires events, `analysis_family=tfr` |
| `reference_csd` | `reference_csd` | `reference_csd` | average reference by default |
| `pac` | `pac` | `pac_cfc` | light local acceptance parameters |
| `connectivity` | `connectivity` | `connectivity` | correlation, alpha band default |

Each matrix row stores `passed`, `skipped`, or `failed` with method-level evidence. Event-dependent methods are skipped honestly when event markers are not confirmed.

### 6.3 Report and Claim Gate

The report gate requires all of these package entries:

```text
reports/report.html
reports/report_manifest.json
reports/report.json
reports/report.pdf
```

Text-bearing package entries are scanned for unsupported positive claims about clinical decisions, diagnosis, treatment, causality, exact source localization, brain-region activation, p-values, or statistical significance. Boundary statements such as "not for clinical diagnosis" remain allowed.

### 6.4 Final Packet Contract

The runner writes:

```text
02_regression/real_dataset_regression_run.json
03_reports/real_dataset_report_inventory.json
05_owner_packet/real_dataset_owner_review_final_packet.json
```

`completed_final_receipt` requires:

- input gate passed;
- at least one authorized method completed;
- at least one report package passed required-entry checks;
- forbidden-claim scan passed.

Otherwise the final packet remains `blocked_final_receipt` with exact blockers and the next owner action.
