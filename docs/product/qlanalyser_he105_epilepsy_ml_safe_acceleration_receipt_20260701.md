# HE-105 Epilepsy ML Safe Acceleration Receipt - 2026-07-01

Status: `completed_safe_low_risk_acceleration`

## Scope

This package continues the local HE-105 long-EDF epilepsy-like event screening fix. Customer data stayed local.

Customer EDF:

`D:\Quanlan\Data\HE脑电\HE脑电\HE-105.edf`

## Product/science decision

The user correctly flagged that blindly filtering the whole continuous record can spread artifacts across abnormal segments, discontinuities, or saturated periods. Therefore this package did not implement unguarded whole-record filtering.

Instead, it implemented a safer acceleration path:

- Keep epoch-local filtering semantics.
- Do not filter across epoch boundaries.
- Batch multiple epochs through SciPy filtering along the epoch time axis.
- Preserve the same feature names, model/scaler path, 0.5 threshold, output tables, and candidate-event aggregation.

This reduces repeated Python filter calls without introducing cross-epoch artifact spread.

## Source-level changes

Changed:

`D:\Quanlan\Codes\Python\quanlan-analyser-official\eeg_core\analysis\epilepsy_ml.py`

Key changes:

- Added vectorized epoch band-power helper `_bandpower_for_epochs`.
- `P_delta`, `P_theta`, `P_alpha`, `P_beta`, `P_gamma`, `P_total`, and relative powers are now computed per chunk as epoch matrices.
- Complex/nonlinear features remain per epoch: Hjorth mobility, TKEO, PFD, skew, kurtosis, variance, Hilbert envelope.
- Added optional `feature_worker_count`, but thread parallelism is not recommended as default based on HE-105 evidence.

Updated regression helper:

`D:\Quanlan\Codes\Python\quanlan-analyser-official\scripts\run_he105_epilepsy_ml_chunked_regression.py`

## Verification

### Static checks

- `python -m py_compile eeg_core\analysis\epilepsy_ml.py` passed.
- `python -m py_compile scripts\run_he105_epilepsy_ml_chunked_regression.py` passed.

### Teaching fixture

- `python scripts\acceptance_epilepsy_ml_fixture_run.py` passed.

### HE-105 10-minute slice

Command:

`python scripts\run_he105_epilepsy_ml_chunked_regression.py slice 1 128`

Result:

- status: `computed`
- elapsed: `3.023 sec`
- epochs: `120`
- candidate events: `0`

### HE-105 full EDF

Baseline after memory fix:

- `he105_full_result.json`
- elapsed: `288.768 sec`
- candidate events: `46`

Safe acceleration run:

Command:

`python scripts\run_he105_epilepsy_ml_chunked_regression.py full 1 128`

Result:

- elapsed: `250.031 sec`
- candidate events: `46`
- speedup vs memory-fix baseline: about `13.4%`
- event timing consistency: `passed`

Evidence:

- `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260701-he105-epilepsy-ml-chunked-fix\he105_full_w1_c128_result.json`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260701-he105-epilepsy-ml-chunked-fix\he105_acceleration_event_consistency.json`

Event consistency result:

- old candidate event count: `46`
- new candidate event count: `46`
- candidate event start/end timing identical: `true`

### Thread parallelism experiment

Command:

`python scripts\run_he105_epilepsy_ml_chunked_regression.py full 4 32`

Result:

- elapsed: `520.771 sec`
- candidate events: `46`

Conclusion: thread-parallel chunk extraction is slower on this local machine and should not be used as the default acceleration strategy.

## Remaining performance limit

The safe acceleration is real but not enough for a smooth customer click path. Full HE-105 still takes about 4 min 10 sec locally. The remaining time is likely dominated by nonlinear per-epoch features and source-compatible Hilbert/envelope/statistical calculations, not just band-power filtering.

## Next acceleration strategy

For a production-grade customer trial, the next package should prioritize:

1. Browser/backend async task progress so users do not wait on a blocking request.
2. Feature-level profiling to identify the remaining slow features precisely.
3. Optional fast screening mode only after validation:
   - candidate-event agreement vs source-compatible mode;
   - probability distribution drift;
   - high-amplitude/saturation/unit policy checks;
   - no diagnostic or clinical wording.
4. Unit/scale policy review for HE-105, because source-compatible power calculations still raise overflow warnings.

final_receipt: completed_he105_safe_epoch_batch_filter_acceleration_with_event_consistency
