# QEEG Dynamic Freeze — RESOLVED (unfrozen 2026-07-22)

Date opened: 2026-07-22 · Date resolved: 2026-07-22

## Status

**RESOLVED.** The external writer has stopped and the post-baseline QEEG updates
were audited, verified, and committed in isolation as `8c5a673`
(`feat(qeeg): reintegrate post-baseline QEEG updates`). The freeze below is kept
as history; the unfreeze gate is recorded as completed at the end of this file.

## Decision (original)

`projects/qeeg-64ch-research` was temporarily frozen from phase-1 live inventory updates because another process/session was still writing it. The user selected: **先冻结 QEEG 目录**.

## Stable reference

- Stable local baseline commit: `6b18faf` (`chore: establish local workspace baseline`).
- The QEEG records in `files.csv`, `python-symbols.csv`, and related baseline artifacts correspond to the state captured in that commit.
- Phase 1 may classify the QEEG capabilities already present in commit `6b18faf`, but must not claim that the live directory is fully inventoried after that point.

## Post-baseline drift observed

Immediately after the baseline commit, the live working tree showed changes not made by this modularization work:

- modified `src/qlanalyser_eeg64/expanded_report.py`;
- modified `src/qlanalyser_eeg64/qc.py`;
- untracked `tests/test_qc_source_time_mapping.py`.

At observation time, the two modified source files contained 54 net inserted lines and 6 removed lines in total. The new test covers source-time mapping across rejected QC intervals. These changes remain unstaged and unmodified by this work.

## Gate to unfreeze

Before QEEG can satisfy the final `unclassified_count == 0` condition:

1. confirm the external writer has stopped;
2. inspect and attribute all diffs since `6b18faf`;
3. run the safety scan and dependency-aware QEEG tests;
4. create a separate local commit for accepted QEEG changes;
5. regenerate the QEEG file/symbol/method/result inventory;
6. compare old and new feature counts and add every new capability to the traceability matrix.

Until this gate passes, overall workspace status is **partial inventory: web-main + Spike active, QEEG frozen**, not “zero omission complete”.

## Unfreeze / reintegration record (2026-07-22)

The gate was executed as follows:

1. **Writer stopped** — newest QEEG edit at 12:17; confirmed idle (~31 min) plus explicit user confirmation "好我更新了".
2. **Diffs attributed** — full diff vs `6b18faf` (later `8f6d0d5`): +6145/−157 across 18 files.
   - modified: `README.md`, `expanded_report.py`, `gfp.py`, `microstates.py`, `pipeline.py`, `qc.py`, `registry.py`, `report.py`, `test_expanded_report_microstate_information.py`, `test_report_contract.py`;
   - new: `historical_exports.py`, `test_gfp_retained_intervals.py`, `test_historical_exports_contract.py`, `test_microstate_sequence_dynamics.py`, `test_microstate_sequence_exports.py`, `test_qc_source_time_mapping.py`, `test_saved_microstate_upgrade.py`, `test_saved_report_refresh.py`.
   - New capabilities: microstate **sequence dynamics** (Markov / jump-chain / block-entropy / LZ76 complexity / dwell-survival / per-second distribution); transactional **report bundle publish** + microstate extended-information & sequence-dynamics HTML/CSV/figure outputs; **historical_exports** (pure `analysis_summary.json` → CSV compatibility layer for the retired 64ch contract, does NOT read raw EEG or run algorithms); `report.refresh_report_from_saved_artifacts` / `upgrade_saved_microstate_report`; GFP source-time-axis + retained-interval filtering; QC now carries original-recording sample coordinates through `source_time_mapping`; `registry.clinical_report_renderer` promoted to `implemented`.
3. **Safety scan** — `scan_baseline_safety.py --fail-on-block` over the changed set: **0 findings**. README example de-identified (real patient path/name → `D:\path\to\recording.bdf`).
4. **Committed in isolation** — `8c5a673`, source + tests only, nothing under `results/`, no binaries.
5. **Inventory regenerated** — files 902→910, `research.qeeg-64ch` 32→40, parse-errors 0→cleared, `unclassified_count == 0` preserved.
6. **Counts reconciled** — QEEG project file_count 31→40 (+1 module, +8 tests); ledger 1085→1093.

### Verification honesty boundary

- QEEG pytest suite **could not run** in this Python 3.14 env: package `__init__.py` eagerly imports `pipeline → complexity → antropy`, and `antropy`/`sklearn` are absent (`antropy` needs `numba`, which lacks Py3.14 support). This is an environment gap, **not** a code failure. All 18 changed files were verified by `py_compile`. Test *logic* remains unexecuted here and must be run in a deps-complete env before any stable/clinical promotion.
- Lab/internal-validation status unchanged: these recovered methods are **not** promoted to stable or clinical, no 19→64 normative extrapolation, results stay ignored/out of Git.
