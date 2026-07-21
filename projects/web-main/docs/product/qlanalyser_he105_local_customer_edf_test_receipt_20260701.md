# HE-105 Local Customer EDF Test Receipt - 2026-07-01

Status: `blocked_full_length_epilepsy_ml_memory`

## Data

- Source: `D:\Quanlan\Data\HE脑电\HE脑电\HE-105.edf`
- Size: `2009769280` bytes
- Channels: `['EEG1', 'EEG2', 'EMG', 'ACC']`
- Sampling rate: `1000.0` Hz
- Duration: `251221.0` s
- Annotations: `0`

## Full HE-105 Local Test

Passed:

- EDF header readable.
- Local upload passed.
- Metadata persisted: file id `eeg_6cbfaae7c6ff`.
- Data preparation confirmed: plan `prep_f089ac813dd9` revision `1`.
- Inline epilepsy workbench opened and waveform-first page was visible.

Blocked:

- Full-length `epilepsy_ml_xgboost` is not production-ready for this 69.8h file.
- Observed failure: `Unable to allocate 18.7 GiB for an array with shape (628054, 4000) and data type float64`.

## HE-105 10-Minute Slice Test

- Slice path: `work\release_evidence\20260701-he105-customer-data-local-test\slice_10min\HE-105_first_10min.edf`
- Slice duration: `600.0` s
- Slice size: `4806336` bytes
- Epilepsy ML task: `task_72a63c79bdd9`
- Task status: `completed`
- Artifact count: `30`

Interpretation: the customer EDF format is compatible with the pipeline, but full-length processing needs chunked/streaming architecture.

## Required Fix Packet

1. Add long-file preflight and explain estimated runtime/memory before `epilepsy_ml`.
2. Implement chunked epoch feature extraction; do not allocate the full epoch-sample matrix.
3. Write features/results incrementally.
4. Build spectrogram preview from bounded time windows.
5. Make long tasks asynchronous with progress polling.
6. Fix browser E2E task tracking so QC preview cannot overwrite the epilepsy task id.

## Evidence

- `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260701-he105-customer-data-local-test\he105_edf_header.json`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260701-he105-customer-data-local-test\browser_upload_to_export\browser_upload_to_export.json`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260701-he105-customer-data-local-test\slice_10min\slice_creation_result.json`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260701-he105-customer-data-local-test\slice_10min\browser_upload_to_export\browser_upload_to_export.json`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260701-he105-customer-data-local-test\slice_10min\api_artifact_readback.json`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260701-he105-customer-data-local-test\he105_local_test_receipt.json`
