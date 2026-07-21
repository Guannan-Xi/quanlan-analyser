# HE-105 Epilepsy ML Chunked Long-EDF Fix Receipt - 2026-07-01

Status: `completed_local_long_edf_algorithm_fix`

## Scope

This fix targets the local QLanalyser epilepsy-like event screening path for the customer EDF:

`D:\Quanlan\Data\HE脑电\HE脑电\HE-105.edf`

The file was tested locally only. It was not uploaded to the cloud in this fix package.

## Root cause

The previous `epilepsy_ml` implementation materialized all complete epochs as one dense matrix before feature extraction. For HE-105, the browser E2E previously failed with an allocation error of about 18.7 GiB. The STFT evidence layer also attempted to operate on the full record.

## Source-level fix

Changed `D:\Quanlan\Codes\Python\quanlan-analyser-official\eeg_core\analysis\epilepsy_ml.py`:

- Read EEG header without preloading all channels.
- Load only the selected EEG channel for the epilepsy-like event screening task.
- Replace full epoch-matrix materialization with chunked source-compatible feature extraction.
- Preserve the existing 19 feature columns, XGBoost/scaler path, fixed 0.5 threshold, and output table names.
- Bound the PC-compatible STFT artifact to a review preview window while keeping full-record epoch classification.
- Add `processing_plan` metadata to summary output.

Added local regression script:

`D:\Quanlan\Codes\Python\quanlan-analyser-official\scripts\run_he105_epilepsy_ml_chunked_regression.py`

## Local verification

### Static checks

- `python -m py_compile eeg_core\analysis\epilepsy_ml.py` passed.
- `python -m py_compile scripts\run_he105_epilepsy_ml_chunked_regression.py` passed.

### Existing teaching fixture

- `python scripts\acceptance_epilepsy_ml_fixture_run.py` passed.
- Evidence: `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\e2e_epilepsy_ml_migration\fixture_run_evidence.json`

### HE-105 10-minute slice

Command:

`python scripts\run_he105_epilepsy_ml_chunked_regression.py slice`

Result:

- status: `computed`
- elapsed: `2.041 sec`
- duration: `600.0 sec`
- epochs: `120`
- candidate events: `0`
- processing strategy: `selected_channel_chunked_features_bounded_spectrogram`

Evidence:

`D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260701-he105-epilepsy-ml-chunked-fix\he105_slice_10min_result.json`

### HE-105 full EDF

Command:

`python scripts\run_he105_epilepsy_ml_chunked_regression.py full`

Result:

- status: `computed`
- elapsed: `288.768 sec`
- duration: `251221.0 sec` (~69.8 h)
- epochs: `50244`
- candidate events: `46`
- processing strategy: `selected_channel_chunked_features_bounded_spectrogram`
- previous full-matrix memory allocation error did not recur.

Evidence:

`D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260701-he105-epilepsy-ml-chunked-fix\he105_full_result.json`

Important artifacts:

- `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260701-he105-epilepsy-ml-chunked-fix\he105_full\tables\epilepsy_ml_epoch_predictions.csv`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260701-he105-epilepsy-ml-chunked-fix\he105_full\tables\epilepsy_ml_events.csv`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260701-he105-epilepsy-ml-chunked-fix\he105_full\data\epilepsy_ml_spectrogram.json`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260701-he105-epilepsy-ml-chunked-fix\he105_full\figures\epilepsy_ml_event_timeline.svg`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260701-he105-epilepsy-ml-chunked-fix\he105_full\figures\epilepsy_ml_spectrogram_preview.svg`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260701-he105-epilepsy-ml-chunked-fix\he105_full\reproducibility\epilepsy_ml_summary.json`

First three candidate events in HE-105 full run:

1. 7880.0-7890.0 s, 2 epochs
2. 10165.0-10175.0 s, 2 epochs
3. 33160.0-33170.0 s, 2 epochs

## Remaining risks

1. Long EDF UX is still not production-grade: full HE-105 local algorithm time was about 4 min 49 sec, so browser/cloud users need async task progress rather than a blocking click.
2. HE-105 produced numerical overflow warnings in source-compatible feature power calculations. This suggests a data-unit/scale policy review is needed for this customer file class. The task completed, but scientific interpretation should be reviewed before customer-facing claims.
3. The bounded STFT artifact is intentionally a review preview. Full-record event classification is complete; full-record time-frequency analysis is not computed by this artifact.
4. This is local algorithm-layer verification. A browser E2E upload-to-results rerun should follow after task progress/state tracking is fixed.

## Next recommended artifact

`qlanalyser_epilepsy_long_task_progress_and_unit_policy_fix_packet_20260701`

Recommended next P0 items:

1. Add async/background task progress for long EDF epilepsy-like event screening.
2. Fix browser E2E task tracking so it waits for the epilepsy task, not a QC preview task.
3. Add unit/scale policy checks for EDF sources like HE-105, with a visible scientific warning when source-compatible scaling is suspicious.
4. Rerun local browser upload-to-results E2E with HE-105 and verify result figures are visible in the Results module.

final_receipt: completed_he105_local_epilepsy_ml_chunked_long_edf_fix_ready_for_browser_e2e
