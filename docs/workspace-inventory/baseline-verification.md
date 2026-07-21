# Baseline Verification

Date: 2026-07-22

## Repository

- One Git repository: workspace root.
- Branch: `master`.
- Initial state: no commits, no remote, all source files untracked.
- Baseline action: create a local-only initial commit after safety review; do not push.

## Safety and inclusion checks

- Trackable high-risk data/archive extensions after ignore rules: 0.
- Trackable files larger than 5 MiB after ignore rules: 0.
- QEEG generated `results/`: ignored; 355 files / 176,112,662 bytes indexed by root only.
- PC `.pkl` models and `.NRM` normative assets: ignored, retained locally, path/size/SHA-256 indexed.
- Content signature scan: 0 blocking signatures; 4 review findings.
- The 4 review findings were inspected with matched values redacted. They are local demo/acceptance account password literals (`demo`, `example.com`, or `.local` contexts), not external provider credentials. They remain recorded as review findings rather than being silently cleared.
- `customer_oddball_case` manifest states the files are customer-facing aliases of a teaching sample. No EDF payload is trackable. The directory remains flagged for provenance review because filename-level scanning alone is not a complete privacy audit.

## Baseline checks

### Inventory tooling

Command:

```bash
python -m py_compile scripts/build_workspace_inventory.py scripts/scan_baseline_safety.py
python scripts/build_workspace_inventory.py --check
python scripts/scan_baseline_safety.py --fail-on-block
```

Result: passed. Current inventory found 901 in-scope files, 2,060 Python symbols, 48 frontend entries, and 12 path-level review findings. The safety gate found no blocking secret signature.

### Web Python compilation

Command:

```bash
python -m compileall -q backend eeg_core worker
```

Result: passed. This is a syntax/import-bytecode compilation check only; it is not business-flow acceptance.

### Staged diff hygiene

`git diff --cached --check` reports pre-existing trailing whitespace in legacy files, primarily under the explicitly excluded `pc-qlanalyser` project. The baseline intentionally preserves existing bytes instead of bulk-formatting legacy code. New inventory/tooling files are reviewed separately during later incremental commits.

### QEEG tests

First command:

```bash
python -m pytest -q
```

Result: collection failed for 7 test modules because the `src`-layout package was not installed or on `PYTHONPATH` (`ModuleNotFoundError: qlanalyser_eeg64`).

Second command:

```bash
PYTHONPATH=src python -m pytest -q
```

Result: collection still failed for 7 test modules because the current Python 3.14 environment lacks declared dependency `antropy` (`ModuleNotFoundError: antropy`).

Interpretation: the baseline environment cannot run the QEEG test suite. This does **not** prove algorithm failure or success. No dependencies were installed and no assertions were changed during baseline capture. A reproducible QEEG environment must be established before numerical migration.

## Baseline limitations

- Historical `33/33` acceptance is not current-worktree verification.
- The Web worker remains a local stand-in; long analysis is not proven asynchronous.
- QEEG generated result versions and package version are inconsistent and remain unresolved.
- Spike remains a placeholder, not an implemented module.
- Presence in inventory does not establish lifecycle status, scientific validity, or release readiness.
