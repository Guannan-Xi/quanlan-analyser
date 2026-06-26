# QLanalyser V01 Parallel Agent Execution Architecture

Updated: 2026-06-20
Owner: Architecture contract lane
Status: Draft for execution

## 1. Purpose

This document defines how GPT-5.4-mini, GLM-5.2, DeepSeek, and C0/Codex must execute QLanalyser v0.1 tasks in parallel with minimal mistakes.

It is an execution contract, not a product redesign. It does not authorize product-code edits by itself. It exists to keep multi-agent work aligned with the current repository architecture, protected-file rules, output contracts, and acceptance commands.

Priority of truth for worker execution:

1. Repository markdown documents.
2. Current repository code.
3. Acceptance scripts and command outputs.
4. Conversation instructions.
5. Model memory or inference.

If sources conflict, the worker must stop and escalate to the coordinator packet owner.

## 2. Project Goal Lock

Every worker packet must begin from the same locked project goal:

```text
QLanalyser v0.1 is a stable pilot for research-team EEG data management,
analysis delivery, and reproducibility records. It is not a clinical
diagnosis system, not a multi-tenant production platform, and not a promise
of durable distributed workers in the current codebase.
```

Goal lock implications:

- Keep v0.1 stable for controlled pilot use.
- Preserve the current output contract for QC, PSD, ERP, reports, and reproducibility artifacts.
- Do not market preview modules as stable backend capability.
- Do not write clinical conclusions, disease claims, or automatic medical interpretation.
- Do not widen scope into billing, infra, auth, or queue redesign unless the packet explicitly owns that boundary and cites a canonical doc.

## 3. Protected Files Policy

Workers are assumed to operate in a shared worktree. They must not overwrite, reformat, or revert unrelated changes.

Protected by default:

- Any file already modified by another person or agent in `git status`.
- All product code outside the packet's allowed write set.
- Generated datasets, real customer data, logs, uploaded EEG files, or report outputs.
- Canonical architecture docs unless the packet explicitly owns architecture documentation.

For v0.1 worker execution, the coordinator should prefer write scopes shaped like:

- one backend service file
- one frontend file group for a single UI slice
- one test or acceptance file group
- one docs file

Mandatory worker rules:

- Read `git status --short` before editing.
- Edit only files listed in `allowed_write_paths`.
- Do not revert lines outside the packet intent.
- If a needed file is already dirty and the packet cannot safely merge, stop and escalate.
- Never delete files unless the packet explicitly allows deletion and provides rollback steps.

## 4. Deterministic Worker Packet Template

Every worker packet must use this template.

```text
PACKET_ID:
LANE:
GOAL_LOCK:
TASK_TYPE:
ALLOWED_WRITE_PATHS:
FORBIDDEN_PATHS:
DEPENDENCY_READS:
START_COMMANDS:
CHANGE_BUDGET:
EVIDENCE_REQUIREMENTS:
QUALITY_GATES:
SERIALIZATION_POINT:
ACCEPTANCE_COMMANDS:
DELIVERABLES:
ESCALATE_IF:
ROLLBACK_HINT:
```

Field rules:

- `PACKET_ID`: stable unique id such as `BE-QC-001`.
- `LANE`: `frontend`, `backend`, `qa`, `devops`, `science`, or `architecture`.
- `GOAL_LOCK`: exact text or a hash alias that resolves to Section 2.
- `TASK_TYPE`: one value from the taxonomy in Section 5.
- `ALLOWED_WRITE_PATHS`: explicit file or directory list.
- `FORBIDDEN_PATHS`: explicit deny list for sensitive or unrelated files.
- `DEPENDENCY_READS`: canonical docs, code files, and tests that must be read first.
- `START_COMMANDS`: read-only commands the worker must run before changing files.
- `CHANGE_BUDGET`: max file count and whether new files are allowed.
- `EVIDENCE_REQUIREMENTS`: what must be verified from files, commands, or tests.
- `QUALITY_GATES`: exact gates that must pass before handoff.
- `SERIALIZATION_POINT`: what must be handed back to the coordinator before parallel work can continue.
- `ACCEPTANCE_COMMANDS`: commands to run if the packet changes behavior.
- `DELIVERABLES`: expected diff summary, evidence summary, and risks.
- `ESCALATE_IF`: specific stop conditions.
- `ROLLBACK_HINT`: minimal revert instructions for the packet's own changes only.

## 5. Deterministic Worker Packet Taxonomy

Each packet must have exactly one primary task type.

| Task type | Lane | Allowed work shape | Default model |
| --- | --- | --- | --- |
| `DOC_CONTRACT` | architecture | docs only, no code edits | GPT-5.4-mini |
| `UI_STATIC` | frontend | static HTML/CSS/JS view or copy-constrained UI slice | GPT-5.4-mini |
| `UI_FLOW` | frontend | user-flow logic, API wiring, state handling, artifact rendering | GLM-5.2 draft or C0/Codex |
| `API_ROUTE` | backend | route or schema boundary, thin API changes | GLM-5.2 draft or C0/Codex |
| `SERVICE_LOGIC` | backend | service orchestration, task state, artifact registration | C0/Codex |
| `WORKER_CONTRACT` | backend | worker wrapper, runner adapter, task semantics | C0/Codex |
| `SCIENCE_RULE` | science | EEG method boundary, parameter semantics, output interpretation guardrails | C0/Codex |
| `TEST_ACCEPTANCE` | qa | acceptance script updates, smoke checks, evidence collectors | GPT-5.4-mini |
| `OPS_SCRIPT` | devops | local scripts, launchers, environment contract docs | GPT-5.4-mini |
| `REVIEW_ONLY` | qa | read, compare, report risks, no writes | GPT-5.4-mini |
| `COPY_GATE` | copy | Chinese customer-facing wording and logic review | DeepSeek |

GPT-5.4 is not an allowed worker lane for this project phase. If a packet appears to require GPT-5.4, split it smaller, send a bounded draft/checklist to GLM-5.2, or return it to C0/Codex for final implementation and quality-gate judgment.

Determinism rules:

- No mixed packets such as frontend plus backend plus science in one worker.
- If the scope crosses layers, split into multiple packets and serialize through the coordinator.
- A worker may read across layers but may write only within its lane and packet scope.

## 6. Safe WIP Limits / dynamic_safe_concurrency_frontier

Parallelism should be constrained by review capacity, not by model availability.

Hard limits:

- Maximum active code-writing packets at once: 3
- Maximum active docs-only packets at once: 2
- Maximum active review-only packets at once: 2
- Maximum files per code-writing packet: 4
- Maximum new files per packet: 1
- Maximum unresolved escalations before freeze: 1 per lane

Recommended v0.1 pattern:

1. One coordinator packet.
2. One backend packet.
3. One frontend or QA packet.
4. Optional one science review packet.

Do not run parallel packets that edit:

- the same file
- the same acceptance script
- the same task-state contract
- the same architecture doc

## 7. Model Routing

Use model size based on failure cost and ambiguity.

Return to C0/Codex when:

- changing backend logic
- touching task state transitions
- affecting artifact manifests or result contracts
- handling science semantics
- reconciling conflicting evidence
- making decisions that require reading multiple canonical docs

Route to GPT-5.4-mini when:

- drafting constrained docs
- updating static frontend copy or layout with clear patterns
- editing acceptance glue with low algorithmic risk
- performing review-only packet checks

Route to GLM-5.2 when:

- drafting a bounded code, test, diff, or checklist candidate
- the allowed file set is frozen
- rollback is explicit
- C0/Codex will review and run the final evidence

Route to DeepSeek when:

- reviewing customer-visible Chinese wording
- checking Chinese logic and tone
- preserving the official direct DeepSeek route evidence

Escalation rule:

- Start with GPT-5.4-mini for read-only, evidence, copy-screening, matrix, and checklist packets.
- Use GLM-5.2 only for bounded code/test/diff/checklist drafts with a frozen allowed file set and explicit rollback.
- Use DeepSeek only for Chinese copy and logic review through the official direct route.
- Return to C0/Codex when a worker finds conflicting docs, unclear ownership, task-state ambiguity, production/security/billing risk, or output-contract risk.
- Do not escalate to GPT-5.4.

## 8. Evidence Matrix

Every packet must close with an evidence matrix.

| Claim type | Minimum evidence | Example evidence |
| --- | --- | --- |
| File ownership respected | `git status --short` plus packet write set | dirty-file check before edit |
| Architecture alignment | canonical doc readback | `docs/architecture/system_architecture.md` |
| Version alignment | version doc readback | `docs/architecture/version_detailed_design.md` |
| v0.1 boundary preserved | pilot plan or product doc | `docs/v01_pilot_architecture_plan.md`, `PRODUCT.md` |
| Behavioral change works | targeted acceptance command output | `python scripts\smoke_v01_api.py` |
| Output contract preserved | artifact or script verification | `python scripts\acceptance_v01_worker_core.py` |
| Encoding safe | mojibake check | `python scripts\check_no_mojibake.py` |
| No whitespace or merge damage | diff check | `git diff --check` |

Evidence grading:

- `E0`: inference only, not acceptable for merge.
- `E1`: file-read evidence only, acceptable for docs or review-only packets.
- `E2`: file-read plus command or test evidence, acceptable for narrow code packets.
- `E3`: file-read plus targeted acceptance plus artifact inspection, required for output-contract changes.

Minimum required grade:

- docs-only packet: `E1`
- static frontend packet: `E2`
- backend or worker-contract packet: `E2`
- output-contract or science-sensitive packet: `E3`

## 9. Quality Gates

All packets must pass shared gates:

1. Scope gate: edits stay within `allowed_write_paths`.
2. Goal gate: no conflict with Section 2 goal lock.
3. Dirty-file gate: no overwrite of unrelated modifications.
4. Evidence gate: required evidence grade met.
5. Diff gate: `git diff --check` passes for changed files.
6. Encoding gate: `python scripts\check_no_mojibake.py` passes when text files change.

Additional gates by lane:

- Frontend:
  - verify target page or flow still matches current API or static contract
  - run relevant UI acceptance if behavior changed
- Backend:
  - verify task state names, output paths, and service boundaries against canonical docs
  - run relevant API, worker, or persistence acceptance
- QA:
  - prove the acceptance script checks the intended contract and fails for the right class of breakage
- Science:
  - prove no clinical interpretation or unsupported EEG claim was introduced
- DevOps:
  - verify commands are local-safe and do not imply production deployment by accident

## 10. Serialization Points

Parallel work must stop at these coordinator-owned serialization points:

1. Goal lock change.
2. Allowed write set change.
3. Task-state vocabulary change.
4. Output contract path or filename change.
5. Acceptance command roster change.
6. Shared architecture document update.
7. Any dirty-file conflict in packet scope.

At a serialization point, the worker must return:

- what changed
- what evidence was gathered
- what remains blocked
- whether downstream packets are still valid

The coordinator then decides whether to:

- approve continuation
- reissue packets
- narrow scope
- freeze the lane

## 11. Rollback Contract

Every packet must be independently reversible.

Rollback rules:

- Roll back only the packet's own changes.
- Do not use destructive repo-wide reset commands.
- Prefer file-specific revert or patch reversal.
- If a new file was added by the packet, delete only that file if rollback is approved.
- If rollback would touch lines modified by someone else after packet start, stop and escalate.

Minimal rollback payload from each worker:

```text
ROLLBACK_SCOPE:
FILES_CREATED:
FILES_MODIFIED:
SAFE_REVERT_METHOD:
POST_ROLLBACK_CHECKS:
```

Post-rollback checks:

- `git diff --check`
- any packet-specific acceptance command that previously passed

## 12. Acceptance Command Map

Coordinator packets should attach only the commands needed for the claimed surface area.

Shared low-cost checks:

```powershell
python scripts\check_no_mojibake.py
git diff --check
```

API and backend contract:

```powershell
python scripts\smoke_v01_api.py
python scripts\acceptance_v01_worker_core.py
python scripts\acceptance_v01_persistence.py
python scripts\acceptance_v01_full.py
python scripts\check_running_backend_contract.py
```

Frontend and static module contract:

```powershell
node scripts\acceptance_v01_ui.mjs
node scripts\acceptance_research_modules_static.mjs
node scripts\acceptance_ops_ui.mjs
node scripts\acceptance_qc_browser_gate.mjs
```

State, queue, and capacity contract:

```powershell
python scripts\acceptance_state_store_concurrency.py
python scripts\acceptance_task_queue_capacity.py
python scripts\acceptance_large_uploads.py
```

Analysis and science contract:

```powershell
python scripts\acceptance_psd_p0.py
python scripts\acceptance_qc_preview_service.py
python scripts\acceptance_synthetic_erp_p300.py
python scripts\acceptance_report_zip_contract.py
```

Ops and recovery contract:

```powershell
python scripts\acceptance_backup_restore_drill.py
python scripts\acceptance_aliyun_v1_contracts.py
python scripts\acceptance_aliyun_storage_contract.py
python scripts\acceptance_audit_quota_contract.py
python scripts\acceptance_ops_billing_invoice.py
```

Full bundle entry point:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_v01_acceptance.ps1
```

Command selection rules:

- docs-only packet: shared low-cost checks only
- frontend static packet: shared checks plus relevant UI acceptance
- backend service packet: shared checks plus smoke and worker-core acceptance
- task-state or persistence packet: include persistence and concurrency acceptance
- output-contract packet: include report-zip or worker-core acceptance
- science packet: include PSD, QC preview, or ERP synthetic acceptance as relevant

## 13. Good Packet Examples

### 13.1 Frontend example

```text
PACKET_ID: FE-OPS-001
LANE: frontend
GOAL_LOCK: Section 2
TASK_TYPE: UI_STATIC
ALLOWED_WRITE_PATHS: frontend/admin-ops.html, frontend/assets/js/admin-ops.js
FORBIDDEN_PATHS: backend/**, eeg_core/**, docs/architecture/**
DEPENDENCY_READS: docs/architecture/system_architecture.md, docs/architecture/version_detailed_design.md, scripts/acceptance_ops_ui.mjs
START_COMMANDS: git status --short
CHANGE_BUDGET: max 2 files, no new files
EVIDENCE_REQUIREMENTS: page matches current static/admin contract; no API contract drift
QUALITY_GATES: shared gates plus frontend gates
SERIALIZATION_POINT: before changing any API field names rendered by the page
ACCEPTANCE_COMMANDS: python scripts\check_no_mojibake.py; git diff --check; node scripts\acceptance_ops_ui.mjs
DELIVERABLES: diff summary, test summary, open risks
ESCALATE_IF: page requires backend field not in current contract
ROLLBACK_HINT: revert only frontend/admin-ops.html and frontend/assets/js/admin-ops.js changes
```

### 13.2 Backend example

```text
PACKET_ID: BE-TASK-002
LANE: backend
GOAL_LOCK: Section 2
TASK_TYPE: SERVICE_LOGIC
ALLOWED_WRITE_PATHS: backend/services/task_service.py, backend/models/analysis_task.py
FORBIDDEN_PATHS: frontend/**, docs/architecture/**, data/**
DEPENDENCY_READS: docs/architecture/system_architecture.md, docs/architecture/version_detailed_design.md, docs/v01_pilot_architecture_plan.md, scripts/acceptance_v01_worker_core.py
START_COMMANDS: git status --short
CHANGE_BUDGET: max 2 files, no new files
EVIDENCE_REQUIREMENTS: task state names and artifact paths stay aligned with v0.1 contract
QUALITY_GATES: shared gates plus backend gates
SERIALIZATION_POINT: before renaming task states or output paths
ACCEPTANCE_COMMANDS: python scripts\check_no_mojibake.py; git diff --check; python scripts\smoke_v01_api.py; python scripts\acceptance_v01_worker_core.py
DELIVERABLES: changed states, affected APIs, evidence grade, residual risks
ESCALATE_IF: packet requires route changes outside write set or conflicts with dirty files
ROLLBACK_HINT: reverse only packet edits in backend/services/task_service.py and backend/models/analysis_task.py
```

### 13.3 QA example

```text
PACKET_ID: QA-CONTRACT-003
LANE: qa
GOAL_LOCK: Section 2
TASK_TYPE: TEST_ACCEPTANCE
ALLOWED_WRITE_PATHS: scripts/acceptance_report_zip_contract.py
FORBIDDEN_PATHS: backend/**, frontend/**, eeg_core/**
DEPENDENCY_READS: docs/architecture/system_architecture.md, docs/architecture/version_detailed_design.md, scripts/acceptance_v01_worker_core.py
START_COMMANDS: git status --short
CHANGE_BUDGET: max 1 file, no new files
EVIDENCE_REQUIREMENTS: acceptance covers required files and fails on missing manifest/result/log artifacts
QUALITY_GATES: shared gates plus QA gates
SERIALIZATION_POINT: before changing asserted artifact filenames
ACCEPTANCE_COMMANDS: python scripts\check_no_mojibake.py; git diff --check; python scripts\acceptance_report_zip_contract.py
DELIVERABLES: assertion summary, evidence summary, known gaps
ESCALATE_IF: canonical output contract is inconsistent across docs and code
ROLLBACK_HINT: revert only scripts/acceptance_report_zip_contract.py
```

### 13.4 DevOps example

```text
PACKET_ID: OPS-ACC-004
LANE: devops
GOAL_LOCK: Section 2
TASK_TYPE: OPS_SCRIPT
ALLOWED_WRITE_PATHS: scripts/run_v01_acceptance.ps1
FORBIDDEN_PATHS: backend/**, frontend/**, data/**
DEPENDENCY_READS: docs/architecture/system_architecture.md, docs/architecture/version_detailed_design.md, scripts/run_v01_acceptance.ps1
START_COMMANDS: git status --short
CHANGE_BUDGET: max 1 file, no new files
EVIDENCE_REQUIREMENTS: command roster stays local-safe and aligned with v0.1 acceptance scope
QUALITY_GATES: shared gates plus devops gates
SERIALIZATION_POINT: before adding or removing acceptance stages
ACCEPTANCE_COMMANDS: python scripts\check_no_mojibake.py; git diff --check
DELIVERABLES: command-map diff, risk summary, skipped checks
ESCALATE_IF: script would imply production deployment or secrets access
ROLLBACK_HINT: revert only scripts/run_v01_acceptance.ps1
```

### 13.5 Science example

```text
PACKET_ID: SCI-ERP-005
LANE: science
GOAL_LOCK: Section 2
TASK_TYPE: SCIENCE_RULE
ALLOWED_WRITE_PATHS: docs/modules/erp_design.md
FORBIDDEN_PATHS: backend/**, frontend/**, clinical/**, data/**
DEPENDENCY_READS: docs/architecture/system_architecture.md, docs/architecture/version_detailed_design.md, docs/v01_pilot_architecture_plan.md, scripts/acceptance_synthetic_erp_p300.py
START_COMMANDS: git status --short
CHANGE_BUDGET: max 1 file, no new files
EVIDENCE_REQUIREMENTS: ERP wording remains research-use only and matches current synthetic acceptance boundary
QUALITY_GATES: shared gates plus science gates
SERIALIZATION_POINT: before changing module stability label or interpretation wording
ACCEPTANCE_COMMANDS: python scripts\check_no_mojibake.py; git diff --check; python scripts\acceptance_synthetic_erp_p300.py
DELIVERABLES: method-boundary summary, evidence summary, interpretation risks
ESCALATE_IF: requested change implies clinical conclusion or unsupported ERP promise
ROLLBACK_HINT: revert only docs/modules/erp_design.md
```

## 14. Coordinator Checklist

Before dispatch:

1. Read canonical architecture and version docs.
2. Run `git status --short`.
3. Freeze goal lock text.
4. Split work into single-type packets.
5. Assign explicit write paths.
6. Attach minimum acceptance commands.
7. Record serialization points.

Before merge or handoff:

1. Collect packet deliverables.
2. Compare evidence against claimed scope.
3. Resolve escalations one by one.
4. Re-run any shared acceptance affected by multiple packets.
5. Update canonical docs first if the contract changed.

## 15. Non-Goals

This document does not:

- introduce a real distributed queue into the current codebase
- grant permission to edit product code
- replace canonical system architecture or version design docs
- certify clinical validity
- guarantee that parallel execution is always faster than serialized execution

It exists to reduce mistakes, not to erase the need for coordinator judgment.
