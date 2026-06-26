# QLanalyser Module Lifecycle Matrix

Date: 2026-06-22

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
| PAC / CFC | beta / preview | Need surrogate/null and boundary controls |
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
