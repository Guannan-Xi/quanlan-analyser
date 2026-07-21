# Exclusions, Risks, and Stop Conditions

## Explicit exclusions

### `projects/pc-qlanalyser`

- Excluded from modularization, movement, and source cleanup by user instruction.
- May be read only for numerical/source provenance comparisons when required.
- Large `.pkl`, `.sav`, `.parquet`, `.NRM`, `.dll`, notebook, and `qeeg_output` assets remain on disk and are ignored by the workspace Git baseline.
- PC has documented duplicate QEEG trees and 19-channel normative assets. Neither is silently promoted into 64-channel contracts.

### Runtime and private payloads

Ignored and not copied into research modules:

- raw EEG/electrophysiology files;
- databases and runtime state;
- `.env`, keys, tokens, authentication caches;
- customer reports and generated ZIP/PDF payloads;
- `.venv`, caches, build outputs;
- QEEG `results/` payloads (indexed, not committed).

## Dynamic freeze

`qeeg-64ch-research` is frozen at baseline commit `6b18faf` because another process is still writing the live directory. See `qeeg-dynamic-freeze.md`. Final zero-omission acceptance is blocked until the live drift is audited and reintegrated.

## Current high-risk boundaries

1. **No Git history before baseline**: removal decisions cannot use blame/rename history for older files.
2. **Synchronous long analysis**: Web `task_service` directly invokes core runners; worker is a local stand-in. QEEG full pipelines and Spike sorting must not enter the HTTP path before real asynchronous execution exists.
3. **Same name, different scientific meaning**: PSD, band power, connectivity, PAC, preprocess, report, pipeline, summary and status differ by project/profile.
4. **QEEG test environment unavailable**: direct tests fail package discovery; with `PYTHONPATH=src`, collection still fails because `antropy` is absent. Algorithm health is not verified.
5. **64-channel claim boundary**: hard-coded channel subsets and limited synthetic channel coverage do not establish full 64-channel robustness.
6. **Normative boundary**: PC 19-channel norms must not be represented as 64-channel norms.
7. **Lifecycle truth**: Lab/recovered/Beta results are not stable, clinical diagnosis, or treatment advice.
8. **Frontend parallel implementations**: main app, labs, workbenches, previews and static evidence may overlap but have different users and acceptance roles.
9. **Historical acceptance**: prior 33/33 evidence does not prove the current worktree or future modularized path.
10. **Generated evidence drift**: QEEG package version, README examples and results directory versions disagree.

## Stop conditions

Migration or deletion must stop when any of these occurs:

- source file/route/frontend entry has no ledger classification;
- source and target feature counts do not reconcile;
- an external writer changes the module during migration;
- secret/patient/raw-data scan returns an unresolved blocking finding;
- numerical or contract comparison fails;
- only visual similarity supports a scientific result comparison;
- a Lab method would enter the stable customer whitelist without its acceptance gate;
- a heavy method would execute synchronously in an HTTP request;
- a deletion candidate lacks byte/reference/semantic/new-path-acceptance evidence;
- the target contradicts its documented role or contains unrelated user changes.

## Current completion statement

- Frozen inventory file coverage: complete for commit `6b18faf`.
- `web-main + Spike` phase-1 classification: generated with `unclassified_count == 0` at file/route/frontend-entry level.
- Live QEEG completeness: **not complete** due dynamic freeze.
- Behavioral correctness/release readiness: **not established** by inventory.
