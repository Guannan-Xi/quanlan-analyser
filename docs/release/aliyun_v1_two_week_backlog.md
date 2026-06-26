# QLanalyser Alibaba Cloud V1 Two-Week Backlog

Updated: 2026-06-19

Owner: C0 architecture center

Status: execution backlog for C1/C2/C3/C4/C5

## 1. V1 release definition

V1 is accepted only if a customer can complete this production-shaped workflow:

```text
create/select project
-> upload/select EEG file
-> inspect metadata/QC
-> save and confirm data_preparation_plan
-> run PSD and ERP when scientifically allowed
-> review current task results
-> download artifacts/report package
```

Production shape means:

- 10 concurrent users are supported in a controlled trial.
- Each user may upload or select 200 MB to 1 GB EEG data.
- Each user may submit 4 to 5 tasks.
- 40 to 50 tasks can be queued or running without blocking the API.
- The system is deployable on Alibaba Cloud with storage, logging, backup, rollback, and quota/audit hooks.

## 2. Workstream summary

| Owner | Workstream | V1 must deliver |
| --- | --- | --- |
| C0 | Product/architecture coordination | Contract freeze, workflow IA, scope guard, final go/no-go |
| C1 | Main framework | Upload/storage/task/artifact/report contracts, queue-ready task lifecycle, quota/audit hooks |
| C2 | QC/Data Preparation lab | Windowed waveform preview, bad channels/segments, preview segment persistence, confirmed plan |
| C3 | PSD/ERP/Results/Report | Plan-aware PSD/ERP, current-task result pages, reproducibility package |
| C4 | User-flow acceptance | Workflow-first UI acceptance, no scattered feature-page release |
| C5 | Quality/release | Test matrix, Alibaba Cloud release gate, rollback and maintenance evidence |

## 3. Day 1-3: Freeze contracts and remove P0 uncertainty

### C0

- Maintain `docs/architecture/aliyun_v1_contract_freeze.md`.
- Maintain `docs/TWO_WEEK_ALIYUN_V1_WAR_PLAN.md`.
- Decide and publish final V1 scope: stable QC/Data Preparation, PSD, ERP-if-events, Report; TFR/PAC/Connectivity preview only.
- Publish UI workflow IA: project, file, data preparation, analysis task, result review, report.

Acceptance:

- C1/C2/C3 can implement without inventing new shared fields.
- C4/C5 can test against a single user journey.

### C1

Must implement or prepare focused patches for:

- streaming/chunked upload path replacing full-body `await upload.read()` for production target;
- file metadata: size, sha256, storage backend/object key;
- task lifecycle vocabulary: queued/running/completed/failed/cancelled;
- queue-ready boundary: API creates task, worker/runner executes task;
- artifact extensions: size/hash/object key/retention placeholders;
- report package contract remains stable;
- quota/audit hooks as no-charge usage records.

Acceptance:

- uploading a large test/stub file does not read the entire file into memory;
- task creation can return queued/running status without blocking on long work;
- existing V01 acceptance still passes or failures are documented with owner.

### C2

Must implement or prepare focused patches for:

- QC Lab plan save/read through file-level current-plan route;
- backend preview segment persistence API or C1 escalation if route ownership is shared;
- current preview segment saved as reproducible evidence;
- UI distinguishes preview-only filter from formal analysis settings;
- plan confirmation state exposed to main workflow.

Acceptance:

- user can upload/select file, preview waveform window, mark bad channel/bad segment, save plan, reload plan;
- saved preview segment is retrievable from backend, not only browser localStorage;
- QC preview remains windowed/channel-subset/downsampled.

### C3

Must implement or prepare focused patches for:

- PSD result page and artifacts prove plan was applied;
- ERP plan support parity or ERP remains lab/conditional in main workflow;
- report package includes plan and task reproducibility evidence;
- current task result page never mixes static sample assets with customer task outputs.

Acceptance:

- PSD task with `data_preparation_plan_id/revision` applies bad channels/segments and writes plan reference artifact;
- ERP fails clearly without events and does not produce misleading success;
- report ZIP contains method, parameters, workflow, software versions, manifest, log, figures/tables.

### C4

Must produce:

- screenshot/browser acceptance checklist for the single workflow;
- must-remove customer-visible internal copy list;
- UI blocker list before main-flow release.

Acceptance:

- a new user can identify the next action in each stage within 5 seconds;
- no TFR/PAC/Connectivity stable promise in V1 main path.

### C5

Must produce:

- final release command set;
- performance/capacity scripts to add or adapt;
- go/no-go table with P0 blockers;
- rollback checklist.

Acceptance:

- every P0 blocker maps to an owner and a command/manual evidence item.

## 4. Day 4-7: Integrate the first production-shaped workflow

### Main path

Implement and verify:

```text
project -> upload -> metadata/QC -> confirmed plan -> PSD -> ERP-if-events -> report package
```

### Required engineering outcomes

- API does not block on long tasks.
- Upload path supports large files safely or has a declared blocker.
- File/task/artifact/report records carry enough future org/quota/storage metadata.
- Frontend makes plan confirmation a gate before PSD/ERP.
- Reports are generated from task outputs, not examples.

### Required validation

```powershell
python scripts\check_no_mojibake.py
python scripts\acceptance_data_preparation_plan.py
python scripts\acceptance_data_preparation_api.py
python scripts\acceptance_qc_preview_service.py
python scripts\acceptance_psd_p0.py
python scripts\acceptance_v01_full.py
python scripts\smoke_v01_api.py
node scripts\acceptance_research_modules_static.mjs
node scripts\acceptance_v01_ui.mjs
```

Add or adapt:

```powershell
python scripts\acceptance_large_uploads.py --users 10 --min-mb 200 --max-mb 1024
python scripts\acceptance_task_queue_capacity.py --users 10 --tasks 50
python scripts\acceptance_report_zip_contract.py
python scripts\acceptance_audit_quota_contract.py
python scripts\acceptance_synthetic_erp_p300.py
```

## 5. Day 8-14: Alibaba Cloud deployment and release hardening

### Alibaba Cloud minimum topology

Preferred V1 deployment shape:

- ECS or container host for frontend/backend.
- Separate worker process or service.
- OSS for raw uploads, derivatives, and report packages.
- RDS or equivalent persistent DB if feasible; otherwise state-store risk must be explicitly accepted for controlled trial only.
- Log service or file/log shipping with task_id correlation.
- HTTPS endpoint.
- Backup and rollback procedure.

### Deployment acceptance

- health check returns OK;
- upload works against deployment storage;
- QC preview works on deployed backend;
- PSD and ERP tasks run or queue correctly;
- artifact download works;
- report package download works;
- logs can locate one task by task_id;
- backup/restore drill is documented;
- rollback steps are documented.

## 6. P0 blockers

Do not release V1 if any remain unresolved without explicit C0 owner acceptance:

- full-file 1 GB upload is read into memory in production path;
- tasks run long analysis inside the HTTP request path for multi-user trial;
- no confirmed data_preparation_plan gate before PSD/ERP main action;
- PSD/ERP result page cannot prove which plan revision was applied;
- report package lacks reproducibility files;
- customer UI still presents scattered module cards as the primary workflow;
- TFR/PAC/Connectivity appear as stable V1 production analysis;
- no 10-user/40-50-task evidence;
- artifact downloads or report ZIP fail;
- mixed worktree ownership is not separated before commit/push;
- secrets or private raw EEG data are staged.

## 7. Daily C0 checkpoint format

```text
Date:
Current branch/worktree:
Completed:
Changed files by owner:
Validation run:
P0 blockers:
P1 risks:
Owner actions:
Next 24h:
Feishu notification:
GLM 5.2 opportunity:
Verification discipline:
```

## 8. Owner notification threshold

The owner does not need Feishu notifications for ordinary document updates, task dispatch, or internal coordination progress.

C0 should notify the owner only when:

- a product-visible build is ready for review;
- a deployment/staging URL is ready to open;
- a P0 blocker prevents reaching a product-visible build;
- owner confirmation is genuinely required for release scope or risk acceptance.

For normal progress, keep working and record evidence in `docs/release/v1_release_evidence_package.md` and the release evidence folder.
