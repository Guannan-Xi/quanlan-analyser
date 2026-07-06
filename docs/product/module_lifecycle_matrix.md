# QLanalyser Module Lifecycle Matrix

Date: 2026-07-03 (updated: PAC V2 promoted to stable candidate)

## 1. Lifecycle states

| State | Meaning | Visible to customers |
| --- | --- | --- |
| draft | Design only | No |
| internal_validation | Executable internally | No unless explicitly labeled |
| beta | Visible with explicit limits | Yes, but with limitations |
| stable | Allowed in the main workflow | Yes |
| deprecated | Kept for history only | Hidden from new work |

## 2. Current method family guidance

| Module family | Current target | Promotion note |
| --- | --- | --- |
| QC / preprocessing readiness | stable target | Must remain the gate before later analysis |
| PSD / bandpower | stable target | Must keep reproducibility and report evidence |
| ERP / P300 | conditional target | Must require events and clear boundary language |
| TFR / ERSP / ITC | beta / preview | Need epoch, baseline, and statistics validation |
| PAC / CFC | beta / preview (V2 stable candidate) | PAC V1 remains beta; PAC V2 promoted to stable candidate on 2026-07-03 (see §5) |
| Connectivity | preview | Need reference and volume-conduction controls |
| Source localization | preview | Need inverse-model and source-space boundary discipline |

## 3. Promotion requirements

Before a module moves up, confirm:

- input requirements exist;
- parameter schema exists;
- output schema exists;
- artifact manifest exists;
- report mapping exists;
- acceptance scripts exist;
- user-facing text has been reviewed;
- the main workflow can actually reach it.

## 4. Update rule

When a module changes state:

- update this matrix;
- update the acceptance matrix;
- update the release notes or product status doc;
- update the change log if the page is visible to users.

## 5. Per-module lifecycle matrix

| Module ID | Display name | Code | Current state | Notes |
| --- | --- | --- | --- | --- |
| `qc` | QC | `eeg_core/preprocess/` | stable | Main gate |
| `preprocessing_readiness` | Preprocessing readiness | `eeg_core/preprocess/` | stable | — |
| `psd_bandpower` | PSD / bandpower | `eeg_core/analysis/psd.py` | stable | — |
| `erp_p300` | ERP P300 | `eeg_core/analysis/erp.py` | stable | — |
| `tfr_ersp_itc` | TFR / ERSP / ITC | `eeg_core/analysis/tfr.py` | beta | Needs epoch baseline + statistics validation |
| `multitaper_psd_tfr` | Multitaper PSD/TFR | `eeg_core/analysis/multitaper_psd_tfr.py` | beta | — |
| `pac_cfc` | PAC V1 | `eeg_core/analysis/pac.py` | beta | Lab-only; surrogate/boundary controls still required before stable |
| `pac_cfc_v2` | PAC V2 | `eeg_core/analysis/pac_v2.py` | **promoted_to_stable_from_beta** (stable candidate) | Promoted 2026-07-03 — see §6 |
| `connectivity` | Connectivity | `eeg_core/analysis/connectivity.py` | beta | — |
| `reference_csd` | Reference / CSD | `eeg_core/analysis/reference_csd.py` | beta | — |
| `epilepsy_ml` | Epilepsy ML | `eeg_core/analysis/epilepsy_ml.py` | internal_validation | — |
| `epilepsy` | Epilepsy workbench | `eeg_core/analysis/epilepsy.py` | internal_validation | — |

## 6. PAC V2 promotion note (2026-07-03)

PAC V2 (`eeg_core/analysis/pac_v2.py`, module ID `pac_cfc_v2`) was promoted from
beta / lab to **stable candidate** on 2026-07-03.

Validation evidence:

- 6 real EEG scenarios, MI correlation r = 1.000000 with PAC V1;
- 2.22x-4.74x speed improvement over V1 across scenarios;
- E2E lab integration verified via the module-lab path;
- P1 issue resolved: parameters now visible by default;
- P2 issue resolved: `duration_sec` now computed from actual `sfreq` instead of a
  hardcoded `/250.0` constant.

Non-medical boundary retained: PAC V2 stays single-record descriptive
sensor-space output only. Not for diagnosis, treatment, clinical decision
support, causality, source localization, brain-region communication, or
group-level inference. No p-value or formal significance conclusion is produced.

PAC V1 (`pac_cfc`) is unchanged and remains `beta`. V1 must not be modified as
part of this promotion. See `work/pac_dev/PAC_V1_V2_COMPARISON.md` for the
detailed V1/V2 differences.
