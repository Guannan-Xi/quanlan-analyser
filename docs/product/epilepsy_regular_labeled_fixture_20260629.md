# Epilepsy Regular Labeled Fixture - 2026-06-29

Status: generated and algorithm-replayed.

## Scope

This document records the ordinary-mode synthetic EEG fixture for QLanalyser epilepsy-like event screening regression.

The fixture is not a protected teaching dataset. It is intended to be uploaded or selected through the normal user data path, then used to verify that the epilepsy workbench can run the `epilepsy_ml` workflow and display Stage_Code plus candidate event overlays.

## Files

- Generator: `scripts/generate_regular_epilepsy_labeled_fixture.py`
- EDF: `work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_60s.edf`
- Source-scale FIF: `work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_60s_raw.fif`
- Stage truth: `work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_stage_code.csv`
- Event truth: `work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_events.csv`
- Manifest: `work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_manifest.json`
- Acceptance evidence: `work/release_evidence/20260629-regular-epilepsy-labeled-fixture/regular_epilepsy_labeled_fixture_acceptance.json`

## Fixture Contract

- `fixture_id`: `regular_epilepsy_labeled_60s_v1`
- Duration: 60 s
- Sampling rate: 250 Hz
- Channels: `EEG0`, `EEG1`, `EEG2`, `EEG3`, `ACC0`
- Selected analysis channel: `EEG3`
- Epoch length: 5 s
- Expected `Stage_Code`: `000001100000`
- Expected candidate event: 25.0-35.0 s, epochs 5-6, two consecutive seizure-like epochs
- Recommended workflow: `module_name=epilepsy_ml`, `workflow_id=epilepsy_ml_xgboost`
- Recommended parameters: `method=ml_epoch_classifier`, `eeg_channel=EEG3`, `epoch_length_sec=5`, `probability_threshold=0.5`, `unit_mode=source_compatible`

## Non-Medical Boundary

This fixture is synthetic research-screening support data only. It is not clinical EEG, not diagnosis, and must not be used for treatment, triage, or clinical decision-making claims.

## Verification

Run:

```powershell
python -X utf8 scripts\generate_regular_epilepsy_labeled_fixture.py
```

The script:

1. Finds a stable 5 s epoch that triggers the migrated source-compatible XGBoost model.
2. Builds a 60 s synthetic EDF with only epochs 5 and 6 labeled as seizure-like.
3. Writes truth CSVs and manifest.
4. Calls the real `run_epilepsy_ml()` function on the EDF.
5. Fails unless the algorithm output matches the truth labels and event interval.

Latest local acceptance:

- `algorithm_status_computed`: true
- `selected_channel_EEG3`: true
- `stage_code_matches_truth`: true
- `single_expected_event_detected`: true
- `non_medical_boundary_present`: true

## Traceability / Acceptance Mapping

| Requirement | Evidence |
| --- | --- |
| Ordinary-mode fixture, not teaching protected data | Manifest `mode=regular_upload_test` and `regular_mode_note` |
| Stage_Code truth is known | Stage CSV and manifest expected code |
| Candidate event truth is known | Events CSV and manifest expected event |
| Backend algorithm can reproduce truth | Acceptance JSON `status=PASS` |
| Future UI E2E can inspect overlays | EDF + manifest + algorithm replay artifacts |

## Change Log

- 2026-06-29: Created ordinary-mode labeled epilepsy-like fixture and replay acceptance evidence.
