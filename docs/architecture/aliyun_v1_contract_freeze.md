# QLanalyser Alibaba Cloud V1 Contract Freeze

Updated: 2026-06-19

Owner: C0 architecture center

Status: contract baseline for the two-week Alibaba Cloud V1 push

## 1. Scope

This document freezes the minimum platform contracts required for the first Alibaba Cloud deployable V1.

The product target is a multi-user laboratory EEG analysis platform:

- 10 concurrent users.
- 200 MB to 1 GB EEG files per user.
- 4 to 5 analysis tasks per user.
- 40 to 50 tasks queued or running.
- Lab incubation first; only accepted labs enter the main workflow.

## 2. Current verified repository baseline

Verified on 2026-06-19 from local files:

- `backend/models/analysis_task.py` currently has `project_id`, `module_name`, `workflow_id`, `input_file_id`, `parameters_json`, `status`, `progress`, `error_message`, timestamps.
- `backend/models/eeg_file.py` currently has `project_id`, `subject_id`, `session_id`, original filename, local path, format, sampling rate, channel count, duration, metadata, status, created time.
- `backend/models/artifact.py` currently has `task_id`, type, label, local path, MIME type, created time.
- `backend/models/report.py` currently has `project_id`, `task_id`, title, HTML path, package path, created time.
- `backend/models/data_preparation.py` currently supports `qc` and `psd` plan module scopes.
- `backend/services/storage_service.py` currently reads uploads with `await upload.read()`, which is not acceptable for 200 MB to 1 GB concurrent production uploads.
- `backend/api/tasks.py` currently creates tasks through `task_service.create_task`; the service still performs local execution semantics rather than a production queue.

## 3. Stable workflow contract

The customer main workflow is:

```text
project -> eeg_file -> qc/data_preparation -> confirmed data_preparation_plan -> analysis task -> result review -> report/artifact package
```

No stable V1 analysis path may bypass the data preparation gate except explicit metadata-only QC.

## 4. Object identity and ownership fields

All durable V1 objects must be compatible with these fields, even if some remain defaulted in the first release:

```text
organization_id
project_id
owner_user_id
created_by
updated_by
visibility_scope
permission_policy
quota_account_id
audit_trace_id
created_at
updated_at
```

Objects covered:

- project
- subject/participant
- EEG file
- data_preparation_plan
- analysis_task
- artifact
- report
- usage_record
- audit_event

## 5. EEG file contract

Current fields remain valid. V1 extensions:

```text
object_key
storage_backend: local | oss
storage_tier: hot | warm | cold
size_bytes
sha256
content_type
upload_status: uploading | uploaded | metadata_ready | failed | archived | deleted
retention_policy
deleted_at
metadata_extracted_at
```

Required behavior:

- Uploads must stream or chunk data; do not read full 1 GB request bodies into memory.
- Store original EEG immutably.
- Compute or record file size and hash.
- Metadata extraction must be cached.
- Deletion must be soft/logged for customer data unless an admin retention policy explicitly allows purge.

## 6. Data preparation plan contract

Stable schema version:

```text
qlanalyser-data-preparation-v0.2
```

The plan is the common preprocessing/QC contract. It may contain:

- metadata review;
- channel types;
- channel renames;
- montage/reference decisions;
- preview-only filter/notch settings;
- bad channels;
- bad segments;
- annotation actions;
- saved preview segments;
- source file summary;
- module-specific parameter hints only when explicitly scoped.

Revision behavior:

- Every save must include `base_revision` or equivalent expected revision.
- Stale updates must fail with a revision conflict.
- Analysis tasks must record the exact plan id and revision they consumed.

ERP gap:

- Current verified code supports only `qc` and `psd` module scopes.
- ERP must not be promoted into the main workflow until plan references support ERP with revision checks and task-scoped reproducibility artifacts.

## 7. Task contract

Current fields remain valid. V1 extensions:

```text
organization_id
owner_user_id
queue_status: created | queued | running | completed | failed | cancelled | retryable_failed
priority
resource_estimate_json
quota_charge_preview_json
actual_resource_usage_json
retry_count
max_retries
worker_id
queue_name
idempotency_key
data_preparation_plan_id
data_preparation_revision
data_preparation_contract_version
```

Required behavior:

- API request validates and enqueues; worker executes.
- V1 may use a local queue first, but API shape must not expose synchronous-only assumptions.
- Per-user and per-project concurrency caps must exist before multi-user trial.
- Failed tasks must be retrievable and explain the user-actionable cause.
- Tasks that use a plan must write `reproducibility/data_preparation_task_reference.json`.

## 8. Artifact contract

Current fields remain valid. V1 extensions:

```text
organization_id
project_id
input_file_id
object_key
storage_backend
storage_tier
size_bytes
sha256
retention_policy
download_policy
expires_at
quota_usage_json
```

Minimum task output package:

```text
result.json
manifest.json
log.txt
tables/
figures/
reproducibility/parameters.json
reproducibility/software_versions.json
reproducibility/workflow.json
reproducibility/method_description.txt
```

If a task used a data preparation plan, include:

```text
reproducibility/data_preparation_plan.json
reproducibility/data_preparation_task_reference.json
reproducibility/data_preparation_artifact_contract.json
```

## 9. Report contract

The V1 report must package current task outputs, not static example assets.

Required report evidence:

- project and file identity;
- task id, module, workflow, status;
- plan id and revision if used;
- parameters;
- software versions;
- figures and tables;
- limitations and non-clinical boundary;
- artifact manifest;
- downloadable ZIP/package.

## 10. Storage backend contract

Introduce or preserve a boundary equivalent to:

```text
put_stream(source, object_key, metadata)
get_readable(object_key)
exists(object_key)
stat(object_key)
signed_download_url(object_key, expires_in)
copy_to_tier(object_key, tier)
delete_or_mark_deleted(object_key)
```

V1 deployment target:

- local filesystem for development;
- Alibaba Cloud OSS for production object storage;
- lifecycle policy for warm/cold retention.

## 11. Quota, billing, and audit hooks

Real payment can remain disabled in V1, but usage accounting must be contract-ready.

Record at minimum:

- upload bytes;
- stored bytes by tier;
- submitted tasks;
- worker runtime;
- output bytes;
- report package downloads;
- failures and retries;
- user/project/org attribution.

Billing UI must not imply real charging until a payment provider is connected.

## 12. UI gate contract

Customer-visible UI must follow workflow state, not internal modules.

Required gates:

- PSD/ERP main action disabled until a data preparation plan is confirmed.
- Task result page displays current task, not examples.
- Result page displays plan id, revision, and whether plan directives were applied.
- TFR/PAC/Connectivity remain lab/preview unless C5 accepts their scientific and compute gates.
- Internal terms such as local API, demo backend, registry, task runner debug, or raw JSON must be hidden by default.

## 13. Release blockers

P0 blockers for the two-week V1:

- full-body 1 GB upload in memory;
- long analysis running directly in the HTTP request path for multi-user trial;
- PSD/ERP main path not referencing a confirmed plan;
- report package missing reproducibility files;
- results mixed with static sample assets;
- no artifact download test;
- no 10-user / 40-50-task acceptance evidence;
- worktree ownership not separated before commit/push.
