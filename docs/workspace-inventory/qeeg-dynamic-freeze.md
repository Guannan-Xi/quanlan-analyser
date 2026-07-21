# QEEG Dynamic Freeze

Date: 2026-07-22

## Decision

`projects/qeeg-64ch-research` is temporarily frozen from phase-1 live inventory updates because another process/session is still writing it. The user selected: **先冻结 QEEG 目录**.

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
