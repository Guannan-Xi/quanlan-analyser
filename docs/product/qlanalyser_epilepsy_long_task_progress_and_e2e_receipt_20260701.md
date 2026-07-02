# QLanalyser Epilepsy Long Task Progress and E2E Receipt - 2026-07-01

Status: `completed_local_fix_and_e2e_pass`

## Scope

This receipt closes the local P0 package for epilepsy-like candidate event screening on long EDF files.

Customer local EDF used for performance regression:

`D:\Quanlan\Data\HE脑电\HE脑电\HE-105.edf`

Synthetic EDF used for browser E2E:

`work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_60s.edf`

Product boundary remains:

- epilepsy-like candidate event screening;
- manual review/correction;
- export results;
- research support only;
- not diagnosis, treatment, or clinical triage.

## Changes

### Backend algorithm

Changed `eeg_core/analysis/epilepsy_ml.py`.

The previous implementation could materialize full-record epoch matrices and full-record STFT artifacts. For HE-105 this led to memory risk on a 2.01 GB, 69.8 h EDF.

The current implementation:

- reads the EDF header without preloading all channels;
- loads only the selected scoring channel;
- extracts the source-compatible 19 features in bounded epoch chunks;
- avoids full epoch matrix materialization;
- writes bounded STFT review preview artifacts instead of full-record STFT;
- writes event timeline and spectrogram SVG result figures;
- records processing plan and feature-scale diagnostics in the summary.

Acceleration was implemented conservatively:

- band-power filtering is batched along the epoch time axis;
- filtering does not cross epoch boundaries;
- event timing stayed identical to the memory-fix baseline.

### Frontend progress

Changed `frontend/app.js`.

When the user clicks `开始初筛`, the inline epilepsy workbench now immediately shows a running task state and progress feedback before the synchronous backend response returns.

For long files, the message is:

`长记录正在本地分块提取特征，页面没有卡死；请保持本页打开。`

This is a UI responsiveness fix. It does not yet turn the backend into a true async/background queue.

### E2E evidence quality

Changed `scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs`.

The E2E test now waits for the `/api/tasks` response whose request body has `module_name=epilepsy_ml`, so QC preview tasks can no longer pollute `task_response` evidence.

## HE-105 local performance evidence

Evidence directory:

`work/release_evidence/20260701-he105-epilepsy-ml-chunked-fix/`

Full HE-105 memory-fix run:

- elapsed: `288.768 sec`
- duration: `251221 sec`
- epoch count: `50244`
- candidate event count: `46`
- evidence: `he105_full_result.json`

Safe acceleration run:

- elapsed: `250.031 sec`
- candidate event count: `46`
- event timing identical to baseline: `true`
- evidence:
  - `he105_full_w1_c128_result.json`
  - `he105_acceleration_event_consistency.json`

Scale/unit diagnostic evidence:

- evidence: `he105_slice_10min_w1_c128/reproducibility/epilepsy_ml_summary.json`
- warning emitted: `feature_scale_review_recommended`
- reason: clipped or near-clipped feature values were detected before scoring.

This means HE-105 is now computable locally without the original memory blow-up, but its EDF unit/source scaling should still be reviewed before customer-facing scientific interpretation.

## Browser E2E evidence

Command target:

`http://127.0.0.1:4174/?customer_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=progress-fix-task-evidence#storage`

Evidence:

`work/release_evidence/20260629-epilepsy-cloud-trial-v0-1-browser-upload-to-export/browser_upload_to_export.json`

Final E2E result:

- status: `passed`
- task response module: `epilepsy_ml`
- workflow: `epilepsy_ml_xgboost`
- task status: `completed`
- progress: `100`

Key checks passed:

- upload authorization request and persistence;
- EDF metadata readback;
- data preparation plan confirmation;
- epilepsy task payload contract;
- candidate event truth;
- Stage_Code truth;
- manual correction saved;
- review export published;
- Results module has review package;
- report package includes event timeline SVG;
- report package includes spectrogram SVG;
- no epilepsy staging copy;
- no diagnosis/treatment copy;
- no video placeholder copy;
- waveform-first inline entry;
- wheel interaction does not show toast;
- progress reaches completed state;
- spectrogram uses the same window source contract.

Screenshots:

- `01_opened.png`
- `02_after_upload.png`
- `03_inline_initial.png`
- `04_results_review_package.png`

## Verification

Passed:

```text
python -m py_compile eeg_core\analysis\epilepsy_ml.py scripts\run_he105_epilepsy_ml_chunked_regression.py
node --check frontend\app.js
node --check scripts\e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs
node scripts\e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs
```

Parallel read-only review:

- reviewed `frontend/app.js` progress state path;
- reviewed E2E epilepsy task waiting path;
- reviewed user-facing copy boundary;
- no high-risk blocker found.

## Remaining Risks

1. Backend is still synchronous for the actual `/api/tasks` call. The UI now gives immediate progress feedback, but a production cloud trial should move long EDF scoring into a real async job queue with pollable progress.
2. HE-105 still emits feature-scale warnings. The file is computable, but unit/scaling and high-amplitude artifacts require review before using the output as customer-facing scientific evidence.
3. Safe batch filtering improved HE-105 runtime by about 13.4 percent. Larger gains should come from measured feature-level profiling, not from unguarded whole-record filtering.
4. Cloud deployment has not been re-run in this receipt. This is a local verification package.

final_receipt: `completed_epilepsy_long_task_progress_he105_local_e2e_pass`
