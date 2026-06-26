# QLanalyser Two-Week Alibaba Cloud V1 War Plan

Updated: 2026-06-19
Owner: C0 architecture / product / neuroscience center
Status: C0 execution baseline for parallel team work

## 1. Product objective

Ship a first cloud-deployable QLanalyser version on Alibaba Cloud within two weeks.

This version is not a single-user EEG demo. It is the first production-shaped release of a multi-user laboratory EEG analysis platform:

- 10 concurrent users.
- 200 MB to 1 GB EEG data per user.
- 4 to 5 analysis tasks per user.
- 40 to 50 tasks concurrently running or queued.
- Lab incubation remains the product development model: each analysis lab is built, tried with real data, accepted, and only then merged into the main customer workflow.

## 2. Non-negotiable architecture constraints

### 2.1 Large EEG data handling

The browser must never load full raw EEG data for preview.

Required pattern:

- windowed time-range preview;
- channel subset loading;
- server-side downsampling for preview;
- immutable raw upload;
- explicit derivative/artifact files;
- reproducible parameters for every task.

### 2.2 Task execution

The first release may keep a local-worker implementation if production queue replacement is not completed in time, but every API and artifact contract must be queue-ready.

Required task contract fields or future hooks:

- organization_id;
- project_id;
- owner_user_id / created_by;
- file_id;
- data_preparation_plan_id and revision where applicable;
- module_name and workflow;
- parameters;
- status: queued/running/completed/failed/cancelled;
- resource_estimate;
- quota_charge_preview;
- actual_resource_usage;
- artifact_manifest;
- audit timestamps.

### 2.3 Multi-user laboratory platform

Every durable object should be compatible with organization-scoped ownership:

- Organization / tenant;
- Project;
- Subject or participant;
- EEG file;
- Data preparation plan;
- Analysis task;
- Artifact;
- Report;
- Wallet/quota ledger;
- Audit event.

V1 may expose auth/billing as disabled or admin-only placeholders, but the data model and service boundaries must not block adding them.

### 2.4 Cost and storage

Alibaba Cloud target design:

- Hot storage: recent uploads, active derivatives, current reports.
- Cold storage: old raw data, old task outputs, archived project packages.
- Object storage abstraction must hide local filesystem vs OSS.
- No destructive overwrite of raw EEG.
- Every artifact must be downloadable or explicitly expired with a clear status.

### 2.5 Customer-visible UI

The UI must be workflow-first, not module-card-first.

Default customer path:

1. Create/select project.
2. Upload/select EEG file.
3. Prepare data in QC/Data Preparation lab.
4. Save data_preparation_plan.
5. Choose analysis goal.
6. Run PSD/ERP using the saved plan.
7. Review results with evidence that the plan was applied.
8. Generate report/package.

Experimental methods such as TFR/PAC/Connectivity can be visible only as preview or locked roadmap items unless C5 accepts their science and compute gates.

## 3. Lab incubation rule

Each analysis capability moves through gates:

1. Lab design: purpose, user decisions, inputs, outputs, risks.
2. Real-data service: no static fake UI for accepted features.
3. Scientific validation: synthetic/reference checks and method limitations.
4. Performance validation: large-file and concurrent-task behavior.
5. Permission/cost/storage validation: owner scope, quota hook, artifact lifecycle.
6. Customer acceptance: clean workflow language, no internal/dev wording.
7. Main-flow merge: only after C0/C4/C5 acceptance.

## 4. Two-week scope recommendation

### Must ship

- Alibaba Cloud deployable backend/frontend package or deployment guide.
- QC/Data Preparation lab as the first serious lab workstation.
- PSD lab/main-flow integration using data_preparation_plan.
- ERP minimal workflow with clear event requirements, failure messages, and data_preparation_plan support parity before it is promoted into the main customer path.
- Report/artifact package with reproducibility manifests.
- Basic admin/status surfaces.
- Disabled-but-contract-stable billing/quota endpoints or equivalent hooks.
- Storage abstraction documented for local filesystem now and OSS next.
- 10-user virtual smoke and task/artifact/report acceptance.
- Streaming or chunked upload path for 200 MB to 1 GB EEG files, or a clearly documented V1 blocker if this cannot be completed safely.
- Queue-ready task lifecycle with user/project concurrency caps, even if the first implementation still uses a local worker.

### Should ship if safe

- UI cleanup from module gallery to workflow cockpit.
- Preview segment save and replay in reports.
- Resource estimate before task submit.
- Task queue status vocabulary even if local worker remains synchronous underneath.

### Defer intentionally

- Full self-service RBAC UI.
- Real payment/recharge integration.
- Full OSS cold archive automation.
- Production Celery/Redis/K8s autoscaling if it endangers QC/PSD/ERP acceptance.
- Production TFR/PAC/Connectivity claims.
- Clinical/normative interpretation.

## 5. Owner work packages

### C1 Main framework

Freeze API contracts for:

- project/file registry;
- data_preparation_plan;
- task lifecycle;
- artifact/download;
- report package;
- billing/quota placeholder;
- storage abstraction.

C1 must not silently change C2/C3 contracts.

### C2 QC/Data Preparation

Own the first lab workstation:

- 64-channel preview max target;
- windowed waveform loading;
- x/y zoom;
- filter/notch preview;
- bad channel multi-select;
- bad segment selection;
- annotation handling;
- current preview segment save;
- data_preparation_plan save/revision.

C2 must report shared-contract gaps instead of redefining APIs.

### C3 PSD/ERP/Results

Own result-side evidence:

- PSD/ERP tasks consume data_preparation_plan;
- results show bad channels/segments/filter choices applied;
- artifacts include method, parameters, versions, limitations;
- report can package QC evidence + analysis output.
- ERP cannot be promoted to the main path until data_preparation_plan references support ERP with revision checks and task-scoped reproducibility artifacts.

Required result-page evidence:

- plan ID, revision, status, and applied/not-applied state;
- applied bad channels and bad segments;
- channel rename/type decisions and annotation actions when present;
- clear separation between preview-only filter settings and formal analysis settings;
- downloadable `data_preparation_plan.json`, `data_preparation_task_reference.json`, task `parameters.json`, and artifact contract.

### C4 User-flow acceptance

Judge the customer path only:

- clutter;
- duplicate wording;
- hidden sequence;
- internal/dev copy;
- dead links;
- report/download failures;
- unclear lab-to-main merge state.

### C5 Quality/release

Own release gate:

- clean-code gate;
- API contract tests;
- scientific reference tests;
- 10-user virtual smoke;
- large-file strategy checks;
- artifact/report download;
- Alibaba Cloud deployment/rollback checklist;
- release blockers.

## 6. Minimum validation commands currently known

Run from project root unless otherwise specified:

```powershell
python -m py_compile backend\main.py backend\services\state_store.py backend\services\storage_service.py backend\services\task_service.py backend\services\report_service.py
python scripts\check_no_mojibake.py
python scripts\acceptance_state_store_concurrency.py
python scripts\smoke_v01_api.py
python scripts\acceptance_v01_worker_core.py
python scripts\acceptance_v01_persistence.py
python scripts\acceptance_v01_full.py
python scripts\acceptance_data_preparation_plan.py
python scripts\acceptance_data_preparation_api.py
python scripts\acceptance_psd_p0.py
python scripts\acceptance_qc_preview_service.py
node scripts\acceptance_research_modules_static.mjs
node scripts\acceptance_v01_ui.mjs
python scripts\launch_v01_virtual_users.py
python scripts\launch_v01_merge9_virtual_users_10rounds.py 10
python scripts\launch_v01_public_virtual_users.py
```

C5 must update this list into a release-command set for Alibaba Cloud.

## 7. Current evidence and uncertainty

Verified from local repository on 2026-06-19:

- Backend currently uses FastAPI and local JSON state files.
- Uploads/artifacts/reports currently use local filesystem paths.
- Uploads currently read the full request body in `backend/services/storage_service.py`; this is not acceptable as-is for 200 MB to 1 GB production uploads.
- Billing endpoints exist as disabled placeholders in acceptance checks.
- Data preparation plan references currently support QC/PSD but not ERP in `backend/models/data_preparation.py`.
- Existing acceptance scripts cover smoke, persistence, full V01, UI, data_preparation_plan, QC preview, PSD P0, and virtual users.
- Worktree is mixed and main is ahead of origin; do not use global staging or push until ownership is separated.

Unverified / pending:

- Feishu EEG basics wiki could not be read because the token is not in the current Feishu authorization whitelist.
- Alibaba Cloud deployment topology is not yet frozen.
- Production queue and database choices are not yet frozen.

## 8. C0 next actions

1. Collect C1/C2/C3/C4/C5 outputs from this parallel round.
2. Freeze the V1 API/storage/task/report contracts.
3. Decide the two-week deployment architecture: minimal VM/local-worker vs queue-backed architecture.
4. Convert accepted requirements into implementation tickets.
5. Notify owner at completion/blocker/confirmation checkpoint.
