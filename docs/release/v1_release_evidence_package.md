# QLanalyser V1 Release Evidence Package

Updated: 2026-06-19

Owner: C5 quality/release gate, coordinated by C0

Status: required evidence structure before calling the owner to review a product-visible V1 build

## 1. Purpose

This package is the evidence bundle required before QLanalyser V1 is shown as a product-verifiable release.

It is not enough for a page to open. The release must prove that a customer can complete:

```text
Project -> EEG File -> Data Preparation -> PSD/ERP-if-valid -> Result Review -> Report Package
```

under the first controlled production target:

- 10 concurrent users;
- 200 MB to 1 GB EEG files;
- 4 to 5 tasks per user;
- 40 to 50 queued/running tasks;
- Alibaba Cloud deployment or deployment-equivalent staging evidence.

## 2. Evidence bundle layout

Create a timestamped folder under:

```text
work/release_evidence/YYYYMMDD-HHMM-aliyun-v1/
```

Required files:

```text
00_git_baseline.txt
01_changed_files_by_owner.md
02_final_command_log.txt
03_api_acceptance.json
04_ui_acceptance.md
05_capacity_acceptance.md
06_scientific_acceptance.md
07_report_zip_contract.md
08_aliyun_deployment_gate.md
09_rollback_plan.md
10_p0_blockers.md
screenshots/
logs/
artifacts/
```

## 3. Final command set

Run from repository root:

```powershell
git fetch origin --prune
git status --short --branch
git diff --stat
git diff --cached --stat
git diff --check

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

## 4. New acceptance scripts required before external trial

| Script | Required evidence | Owner | Severity |
| --- | --- | --- | --- |
| `scripts/acceptance_large_uploads.py --users 10 --min-mb 200 --max-mb 1024` | upload/selection is memory-safe; size/hash/status recorded; metadata cached | C1/DevOps | P0 |
| `scripts/acceptance_task_queue_capacity.py --users 10 --tasks 50` | queued/running/completed/failed lifecycle without API starvation | C1 | P0 |
| `scripts/acceptance_report_zip_contract.py` | report ZIP contains result, manifest, log, tables, figures, parameters, workflow, versions, method text, plan reference when used | C3/C1 | P0 |
| `scripts/acceptance_audit_quota_contract.py` | upload/task/report usage events include org/project/user/quota/audit trace fields | C1 | P0/P1 |
| `scripts/acceptance_synthetic_erp_p300.py` | ERP accepts event-rich synthetic data and rejects no-event data clearly | C3 | P0 |
| `scripts/acceptance_aliyun_storage_contract.py` | OSS-style storage boundary supports put stream, get, stat, signed download, delete/mark-deleted | C1/DevOps | P0 |
| `scripts/acceptance_backup_restore_drill.py` | state + artifact/report restore works in a clean environment | C1/DevOps | P0 |

## 5. Product-visible UI evidence

Required screenshots or browser evidence:

- project/file entry;
- metadata and QC summary;
- data preparation plan confirmed state;
- PSD enabled only after confirmed plan;
- ERP disabled or conditional when events are missing;
- PSD result page showing current task and plan revision;
- report package/download page;
- lab/preview area showing TFR/PAC/Connectivity as preview-only;
- no customer-visible internal/local/demo/backend wording.

## 6. Alibaba Cloud deployment gate

Minimum evidence:

- frontend/backend reachable through intended deployment URL;
- backend health check passes;
- worker process/service is running or accepted trial limitation is documented;
- raw uploads, derivatives, and report packages write to OSS or accepted trial storage;
- logs include `project_id`, `task_id`, and audit trace fields where available;
- monitoring covers CPU, memory, disk, queue depth, failed task rate, upload failures, report failures;
- backup/restore drill recorded;
- rollback command and prior version recorded;
- no secrets or private EEG data are staged.

## 7. P0 blockers by owner

| Owner | P0 blocker |
| --- | --- |
| C0 | V1 scope not frozen; feature pages remain the primary workflow |
| C1 | full-body 1 GB upload remains; no queue-ready task lifecycle; no org/user/quota/audit hooks |
| C2 | QC/Data Preparation cannot produce confirmed plan with bad channels/segments, annotation actions, preview evidence, and revision safety |
| C3 | PSD/ERP do not reference confirmed plan; ERP synthetic/no-event validation missing; report ZIP not built from current task outputs |
| C4 | no browser evidence/screenshots/trace for the full workflow; internal/dev wording remains visible |
| C5 | final evidence package incomplete; mixed worktree or staged cross-owner files remain at release |
| DevOps | Alibaba Cloud OSS/logging/monitoring/backup/rollback not validated |

## 8. Owner notification threshold

Do not notify the owner for ordinary document updates, task dispatch, or non-product-visible progress.

Notify the owner only when:

- a product-visible build is ready for review;
- a deployment/staging URL is ready to open;
- a P0 blocker prevents reaching a product-visible build;
- owner confirmation is genuinely required for release scope or risk acceptance.
