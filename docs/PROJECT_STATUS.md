# QLanalyser Online 项目状态

## 1. 当前目标

QLanalyser Online v0.1 Pilot：稳定 MVP，用于客户免费试用。

命名基线：

- 产品名：QLanalyser Online
- 版本标记：Pilot
- 完整版本：QLanalyser Online v0.1 Pilot
- 中文说明：QLanalyser Online Pilot 试用版
- 边界说明：本平台用于科研数据管理与分析辅助，结果不作为临床诊断依据。

## 2. 当前技术栈

- 前端：静态 HTML、CSS、JavaScript，使用 `http-server` 本地服务；`frontend/package.json` 中仍有旧命名，需后续统一。
- 后端：FastAPI、Uvicorn、Pydantic、python-multipart。
- 数据库：未发现正式数据库；当前通过 `backend/services/state_store.py` 将项目、受试者、EEG 文件、任务、产物、报告等 registry 持久化到 `data/state/*.json`。
- EEG 分析模块：MNE-Python 与项目内 `eeg_core/`，当前包含 IO、metadata、quality、PSD、ERP、report、workflow 等模块。
- 任务队列：未发现真实 Celery/Redis 队列；`worker/celery_app.py` 是 `LocalWorkerApp` 占位，worker 任务为薄封装。当前 `backend/services/task_service.py` 在创建任务时直接调用 QC/PSD/ERP 分析逻辑。
- 文件存储：本地文件系统。上传文件保存到 `data/uploads/`，分析结果保存到 `data/derivatives/`，报告保存到 `data/reports/`，状态保存到 `data/state/`。
- 部署方式：本地开发使用 Uvicorn 后端与静态前端服务；`frontend/` 中存在 Dockerfile、nginx.conf、DEPLOY.md，但生产部署方案待确认。

## 3. 当前目录结构

- `frontend/`：浏览器端静态工作台页面、样式、脚本、前端部署文件。
- `backend/`：FastAPI 应用、API 路由、Pydantic 模型、项目/文件/任务/报告/状态服务。
- `worker/`：metadata、preprocess、PSD、ERP、report 等后台任务入口；当前主要复用 `eeg_core`。
- `eeg_core/`：EEG 文件读取、元数据提取、预处理质控、PSD、ERP、统计、HTML 报告、workflow 等核心分析代码。
- `data/`：本地开发数据根目录，包括 uploads、derivatives、reports、state。
- `docs/`：产品架构、Research MVP、V01 readiness 与本次新增协作状态文档。
- `outputs/`：历史静态 MVP 和生成演示资产。
- `scripts/`：V01 smoke、acceptance、mojibake 检查等验证脚本。
- `work/`：本地开发脚本、验收工作区和临时产物。
- `.ai/`：AI 协作相关本地目录，具体用途待确认。

## 4. 已完成功能

- FastAPI 应用已注册 health、projects、subjects、eeg_files、templates、tasks、artifacts、reports、billing、data_crud、workflow、admin 等 API 路由。
- 支持创建项目、创建受试者、上传真实 EEG 文件，并限制 EDF、BDF、EEGLAB SET、BrainVision VHDR、CNT、FIF 等格式。
- 支持本地保存 EEG 原始文件路径和元数据 registry，原始文件保存于文件系统。
- 已有 Metadata/QC、Resting PSD、ERP/P300 相关核心分析与任务入口。
- 支持生成分析 artifacts，并通过 artifact 下载接口获取文件。
- 支持生成 HTML 报告与 ZIP 报告包，报告包包含报告、表格和 reproducibility 信息。
- 已有管理员 dashboard 与失败任务列表接口。
- V01 smoke 验证通过：项目创建、真实 EEG 上传、metadata、QC、PSD、ERP、报告和 ZIP 包均通过。
- V01 Full API acceptance 通过：126 项检查，失败数 0，覆盖高级方法禁用、失败 ERP 任务错误保存、artifact 下载、HTML 报告、ZIP 报告包、admin failed tasks 等。
- V01 persistence acceptance 通过：项目、受试者、EEG 文件、任务、报告状态可写入 `data/state`。
- UI acceptance 在默认脚本中因 4174 前端服务未启动失败；手动启动后端 8001 与前端 4174 后，`scripts/acceptance_v01_ui.mjs` 通过。`8000` 仅保留为旧线兼容回退。
- 前端静态工作台已存在，包含项目、数据、QC、分析、结果、报告等页面资源。

## 5. 部分完成的功能

- 登录页与登录逻辑：前端页面存在，但真实认证、会话、权限边界待确认。
- 工作台首页：UI acceptance 在手动启动服务后通过，真实试用部署下的端口、代理和启动方式仍需固化。
- 管理员入口：后端 admin dashboard 与 failed tasks 接口验收通过，前端权限控制待确认。
- 分析任务状态：QC/PSD/ERP 任务完成态、失败 ERP 任务错误信息保存均已通过自动化验收；长任务后台运行机制仍待确认。
- 任务失败原因展示：后端失败任务列表验收通过，前端展示完整性待确认。
- 基础日志：报告与任务输出中有 reproducibility 信息，系统级运行日志与审计日志待确认。
- 基础部署和备份说明：前端 DEPLOY 与 README 有局部说明，后端、数据目录、备份恢复说明不完整。
- Billing 路由：代码中存在 billing API，但 v0.1 Pilot 暂不做在线支付，是否保留为占位待确认。

## 6. 未完成功能

- 明确并验证真实登录/鉴权方案，避免 Pilot 试用时出现未授权访问风险。
- 将长时间 EEG 分析任务移出 HTTP 请求阻塞路径，确认本地后台任务、状态刷新和失败重试策略。
- 完成文件上传限制、文件安全检查、存储清理、备份恢复和容量策略。
- 完成产品名与品牌文案在活动页面、报告、包清单、配置文件中的统一清理。
- 完成工作台前后端端到端验收，特别是项目、上传、任务、报告下载流程。
- 完成部署运行手册：前端、后端、数据目录、端口、环境变量、备份、恢复、日志位置。
- 完成 v0.1 Pilot 客户试用前的最小安全检查与错误提示打磨。

## 7. 当前风险点

- 当前 git 工作树已有大量未提交业务代码修改和未跟踪文件，验收结果代表当前本地工作树，不代表远程干净 checkout。
- 当前本地 `main` 与 `origin/main` 存在 ahead/behind 分叉，禁止自动 push，需要先确认同步策略。
- `scripts/run_v01_acceptance.ps1` 默认要求 4174 前端服务已启动；未启动时 UI acceptance 会因 `ERR_CONNECTION_REFUSED` 失败。手动启动 8001/4174 后 UI 脚本可通过。
- 当前正式数据库缺失，JSON state 适合单机 Pilot，但多用户并发、数据一致性、备份恢复存在风险。
- 当前未接入真实持久化任务队列，分析任务可能阻塞 HTTP 请求；较大 EEG 文件会带来超时和体验风险。
- 上传文件仅按后缀限制，文件大小、恶意文件、重复文件、存储清理和权限隔离策略待完善。
- 前端、报告包、部署说明中仍可能存在旧产品命名和旧定位文案，存在品牌不一致风险。
- 高级分析方法如 PAC、Connectivity、TFR、机器学习应继续保持禁用或明确返回不可用，避免 Pilot 承诺过高。
- 报告可复核性已经有雏形，但仍需持续验证输入文件信息、参数、运行日志、软件版本、输出路径是否完整保存。
- 本次验收生成/更新 `data/state`、`data/uploads`、`data/derivatives`、`data/reports`、`work/acceptance` 等本地产物，不应混入提交。

## 8. 最近一次修改

本次执行 QLanalyser Online v0.1 Pilot 基线验收：smoke 通过；完整 acceptance 的 compile、frontend syntax、core/worker、full API 通过；默认 UI 步骤因 4174 前端服务未启动失败，手动启动 8001/4174 后 UI acceptance 通过；persistence acceptance 通过。同步写入 Pilot 命名基线。

## 9. 下一步建议任务

1. 固化本地验收启动方式：让 acceptance 脚本自动启动或明确要求启动 backend/frontend，避免 UI 步骤因服务未启动失败。
2. 先确认 `main` 与 `origin/main` 的同步策略，再决定是否 merge/rebase 或 push。
3. 做一次产品命名与品牌文案审计，只清理活动页面、报告与部署文档中的旧命名。

## 10. 本地运行方式

后端 API：

```powershell
C:\Users\XGN\miniconda3\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

前端静态服务：

```powershell
cd frontend
npm run serve
```

前端访问 API 示例：

```text
http://127.0.0.1:4174/?api=http://127.0.0.1:8001/api
```

V01 smoke 验证：

```powershell
C:\Users\XGN\miniconda3\python.exe scripts\smoke_v01_api.py
```

V01 完整验收：

```powershell
scripts\run_v01_acceptance.ps1
```

数据库启动方式：未发现正式数据库，当前使用 `data/state/*.json`。

Docker 启动方式：`frontend/` 内有静态前端 Dockerfile；后端 Docker 或统一 compose 方案待确认。

## 11. AI Handoff Skills

当前项目使用两类 AI 接力 skills：

- `qlanalyser-close-chat-handoff`：用于结束当前对话前生成可接力的状态记录。
- `qlanalyser-continue-project-context`：用于新对话接续项目上下文、验收结果和下一步计划。

继续 QLanalyser Online 时，请优先复核工作树、验收结果和 EEG 平台入口，不要自动 push。

## 12. v0.1 Pilot architecture/module plan

New planning document: `docs/v01_pilot_architecture_plan.md`.

Architecture judgment: the current project is suitable for a single-node, low-concurrency, controlled-trial QLanalyser Online v0.1 Pilot. metadata/QC, PSD, and report packaging can be treated as the stable baseline; ERP should remain beta; TFR/PAC/connectivity should remain experimental or planned. The current JSON state store, synchronous task runner, and local filesystem should not be described as a production-grade 20-user / 500MB-file architecture.

Next priority: standardize job_type, task states, and output contracts (`parameters.json`, `result.json`, `manifest.json`, `log.txt`) before moving to module registry, background runner, database, queue, and object storage.

## 13. Git sync risk audit

Conclusion first: do not push now. The local branch is `main...origin/main [ahead 7, behind 1]`, the working tree still has broad unstaged code/assets/scripts/state changes, and the remote-only commit must be reconciled before any push.

Current remote state is not stale: `git ls-remote origin refs/heads/main` points to `bb14003`, the same object as local `origin/main`. The remote-only commit `bb14003 Set QLanalyser as the only EEG platform version` has no content diff against local commit `fd73a10` (`git diff fd73a10 bb14003` is empty), but it is a different commit object, so direct push would still be a non-fast-forward risk.

Staging area is clean. Unstaged/untracked changes remain across README/docs, backend API/services, EEG analysis/report code, frontend pages, outputs mirror files, worker/scripts, generated state JSON, and image/assets. These must be reviewed and split before the next adapter task.

Sensitive scan result: no high-risk secret patterns were reported. Two medium-risk `password` assignment pattern hits were found in `frontend/app.js:373` and `outputs/eeglab-mne-mvp/app.js:373`; values were not printed and should be manually confirmed as demo-only before staging those files.

Recommended next safety step: before implementing the unified output-contract adapter, either park or deliberately split the existing uncommitted changes, then decide how to reconcile `bb14003` with the local 7 commits. Do not use `git add .`, do not merge/rebase without explicit confirmation, and do not push until the remote divergence is resolved.



## 12. Research Modules Static Testbench

Update date: 2026-06-18

A standalone static research-module testbench was added for tomorrow's EEG analysis workflow review.

- Entry: `frontend/research-modules.html`
- Module pages: `frontend/research-module/qc.html`, `psd.html`, `erp.html`, `tfr.html`, `pac.html`, `connectivity.html`
- Static assets and synthetic test data: `frontend/assets/research-modules/`
- Manifest: `frontend/assets/research-modules/reproducibility/research_module_manifest.json`
- All-in-one test package: `frontend/assets/research-modules/packages/qlanalyser_research_modules_static_test_package.zip`

Scope boundary:

- Enabled in V01: QC, PSD, ERP.
- Preview/research-design only: TFR / ERSP / ITC, PAC / CFC, Connectivity. These pages define interaction and output expectations; they do not mean the V01 backend execution path is enabled.
- All displayed data are synthetic and for research workflow testing only; not for clinical diagnosis.

MNE references checked:

- `mne.io.Raw`
- `mne.events_from_annotations`
- `mne.Epochs`
- `mne.Evoked`
- `mne.time_frequency.tfr_morlet`
- `mne.viz.plot_topomap`
- `mne.viz.plot_compare_evokeds`

Local validation:

```powershell
python -m py_compile scripts\generate_research_module_assets.py
node --check frontend\research-modules.js
node --check scripts\acceptance_research_modules_static.mjs
node scripts\acceptance_research_modules_static.mjs
```

Result: `passed`, 130 checks, 6 module pages. Report: `work/acceptance/research_modules_static_latest.json`.

## 13. Production-grade state/concurrency hardening and full validation

Date: 2026-06-18

Scope:

- Hardened JSON registry persistence for concurrent/local multi-process use.
- Added isolated state-root override, cross-process lock files, merge-on-save, single-item upsert/delete paths, and read-before-access refresh in services that keep in-memory registries.
- Updated virtual-user acceptance checks so they validate the actual V01 frontend, research-module manifest, readiness limits, output contract, downloads, reproducibility assets, and mojibake guardrails.
- Public Aliyun smoke/virtual-user check passed for `http://39.97.248.225` after the local acceptance scripts were aligned with current product signals.

Validation completed:

```powershell
python -m py_compile backend\main.py backend\services\state_store.py backend\services\storage_service.py backend\services\task_service.py backend\services\report_service.py scripts\acceptance_state_store_concurrency.py scripts\launch_v01_virtual_users.py scripts\launch_v01_merge9_virtual_users_10rounds.py scripts\launch_v01_public_virtual_users.py
python scripts\acceptance_state_store_concurrency.py
python scripts\smoke_v01_api.py
python scripts\acceptance_v01_worker_core.py
python scripts\acceptance_v01_persistence.py
python scripts\acceptance_v01_full.py
node scripts\acceptance_research_modules_static.mjs
python scripts\check_no_mojibake.py
python scripts\launch_v01_virtual_users.py
python scripts\launch_v01_merge9_virtual_users_10rounds.py 10
python scripts\launch_v01_public_virtual_users.py
```

Result:

- State concurrency acceptance: passed, 6 workers ? 12 rounds, 72 persisted records.
- Smoke V01 API: passed.
- Worker/core acceptance: passed.
- Persistence acceptance: passed.
- Full V01 acceptance: passed, 180 checks.
- Research modules static acceptance: passed, 130 checks, 6 pages.
- Virtual users: passed, 10/10 rounds, min score 1.0.
- Public virtual users: passed against `http://39.97.248.225`, min score 1.0.
- `python scripts\check_no_mojibake.py`: passed.

Operational notes:

- MNE still emits `pick_types()` legacy warnings during tests; these are non-blocking but should be considered for a later MNE API modernization pass.
- Test runs generated runtime files under `data/state`, `data/uploads`, `data/derivatives`, `data/reports`, and `work/acceptance`; these should not be committed except for intentional source/test/reporting scripts.
- Unified output-contract adapter remains the next product-development target; this round focused on production stability, state consistency, and validation.

## 14. No-login Analysis Lab for standalone module trials

Date: 2026-06-18

A formal no-login Analysis Lab entry was added for standalone EEG module trials and parallel development.

- Entry pages: `frontend/index.html`, `frontend/expert-entry-demo.html`, and `frontend/research-modules.html` now link to `frontend/module-lab.html`.
- Lab overview: `frontend/module-lab.html` renders six module cards from `research_module_manifest.json`.
- Module URLs: `frontend/module-lab.html?module=qc`, `psd`, `erp`, `tfr`, `pac`, `connectivity`.
- Each module page shows inputs, parameters, MNE methods, outputs, visual artifacts, file deliverables, acceptance matrix, research guardrails, and parallel-development handoff notes.
- Cover background asset was replaced with a higher-resolution neuron-firing network illustration and reused by the lab hero.
- V01 enabled modules remain QC / PSD / ERP; TFR / PAC / Connectivity remain preview-only research designs.

Validation:

```powershell
node --check frontend\module-lab.js
node --check scriptscceptance_research_modules_static.mjs
python scripts\check_no_mojibake.py
node scriptscceptance_research_modules_static.mjs
```

Result:
- Static/lab acceptance: passed, 189 checks, 6 lab module pages.
- Report: `work/acceptance/research_modules_static_latest.json`.
- External review: DeepSeek consultant call succeeded; output recorded at `.ai/module-lab-review/deepseek_review.md`. Console rendering had encoding noise, so actionable conclusions were cross-checked against local evidence.

Risks:
- The worktree still contains unrelated legacy changes under `outputs/eeglab-mne-mvp/` and untracked files. Commit this task with precise staging only.
- The Analysis Lab is no-login by design and must continue to expose only static synthetic/research-demo assets unless a separate access-control decision is made.

## 15. Aliyun deployment for no-login Analysis Lab

Date: 2026-06-18

The no-login Analysis Lab was deployed to Aliyun for user testing.

- Public base: `http://39.97.248.225`
- Lab entry: `http://39.97.248.225/module-lab.html`
- Module URLs: `module-lab.html?module=qc`, `psd`, `erp`, `tfr`, `pac`, `connectivity`.
- Formal workbench/login remains separate: the public root still renders the normal login form and only links to the lab as a no-login static trial.
- Remote static root: `/opt/qlanalyser/outputs/aliyun-static-lite`
- Remote service: `qlanalyser.service`
- Remote backup: `/opt/qlanalyser/backups/module-lab-static.20260618_131208.tar.gz`

Validation:
- Remote service restart: passed.
- Public root `/`: 200, login form present, lab links present.
- Public lab `/module-lab.html`: 200, six module cards rendered.
- Public lab module URLs for QC / PSD / ERP / TFR / PAC / Connectivity: 200 and include inputs, parameters, MNE methods, outputs, acceptance matrix, and research guardrails.
- Public virtual users: passed, min_score 1.0.


## 16. Multi-conversation design sync workflow

Date: 2026-06-18

Scope:

- Added `qlanalyser-conversation-sync` as the project skill for fixing architecture/module-design conclusions into repository documents.
- Established GitHub / repository Markdown docs as the single source of truth for multi-conversation development.
- Established Feishu as a review and communication mirror, generated from repository summaries.
- Added canonical sync docs and templates for architecture design, module detailed design, conversation records, and Feishu summaries.

Canonical files:

- `docs/AI_CONVERSATION_SYNC.md`
- `docs/AI_HANDOFF_CURRENT.md`
- `docs/templates/conversation_sync_record.md`
- `docs/templates/feishu_sync_summary.md`
- `docs/templates/architecture_design_doc.md`
- `docs/templates/module_design_doc.md`

Current rule:

- Architecture and module design should be written under `docs/architecture/` and `docs/modules/` before implementation work proceeds in parallel conversations.
- Feishu summaries should be copied from repository-generated summaries unless a real Feishu integration is added later.


## 17. Canonical architecture and version design documents

Date: 2026-06-18

Scope:

- Added canonical system architecture design for QLanalyser Online.
- Added version-by-version detailed design covering Legacy Static MVP, v0.1 Pilot, v0.2 hardening, v0.3 public beta, v1.0 research platform, and v1.x commercial/scale evolution.
- Added analysis module design matrix covering QC, PSD, ERP, TFR, PAC, and Connectivity.

Canonical docs:

- `docs/architecture/system_architecture.md`
- `docs/architecture/version_detailed_design.md`
- `docs/modules/analysis_modules_design_matrix.md`

Current architecture basis:

- v0.1 Pilot remains a single-node research MVP with static frontend, FastAPI API, JSON state store, local filesystem storage, and MNE-Python `eeg_core` analysis modules.
- QC / PSD / ERP are the v0.1 executable modules; TFR / PAC / Connectivity remain preview-only until scientific and statistical prerequisites are satisfied.
- Architecture changes and module implementation tasks should use these docs as their starting basis.

## 18. GitHub baseline sync guard for parallel conversations

Date: 2026-06-18

Scope:

- Added `qlanalyser-github-baseline-sync` as the required guard for parallel QLanalyser Online development conversations.
- All development/design tasks must fetch GitHub `origin/main` before starting, before committing, and before pushing.
- Architecture/module/version work must re-check canonical docs before editing:
  - `docs/architecture/system_architecture.md`
  - `docs/architecture/version_detailed_design.md`
  - `docs/modules/analysis_modules_design_matrix.md`
  - `docs/DECISIONS.md`
  - `docs/PROJECT_STATUS.md`
- If local and GitHub differ, or if canonical docs changed remotely, the assistant must pause and ask the user before merge/rebase/reset/overwrite/push.

Current boundary:

- This workflow does not automatically pull, merge, rebase, overwrite, or force push.
- Existing untracked frontend Open Design demo files remain local and outside this documentation/sync workflow unless explicitly requested.

## 19. QC Lab early-access service preview

Date: 2026-06-18

Scope:

- Added the first live QC Lab service preview for the Analysis Lab early-access area.
- `qc_waveform_preview` now runs through `/api/tasks` for QC/preprocess jobs when the workflow id is `qc_waveform_preview`, `qc_filter_preview`, or `qc_snapshot`.
- Added `frontend/qc-lab.html`, `frontend/qc-lab.js`, and `frontend/qc-lab.css` so users can upload or select EEG files, inspect metadata, choose preview channels/time window, run preview-only filtering, view SVG snapshots, and download artifacts.
- Updated `frontend/module-lab.html` and `frontend/module-lab.js` so the lab reads as a customer-facing free early-access area instead of an internal Open Design/demo review page.
- Added `scripts/acceptance_qc_preview_service.py` and extended `scripts/acceptance_research_modules_static.mjs` to cover the QC Lab page.

Validation:

```powershell
python -m py_compile eeg_core/preprocess/qc_preview.py backend/main.py backend/api/eeg_files.py backend/services/task_service.py scripts/acceptance_qc_preview_service.py
node --check frontend/module-lab.js
node --check frontend/qc-lab.js
node --check scripts/acceptance_research_modules_static.mjs
python scripts/check_no_mojibake.py
python scripts/acceptance_qc_preview_service.py
node scripts/acceptance_research_modules_static.mjs
python scripts/smoke_v01_api.py
python scripts/acceptance_v01_worker_core.py
python scripts/acceptance_v01_persistence.py
python scripts/acceptance_v01_full.py
```

Result:

- QC preview service acceptance: passed, generated 13 artifacts.
- Static/lab acceptance: passed, 209 checks, 6 module pages.
- Smoke V01 API: passed.
- Worker/core acceptance: passed.
- Persistence acceptance: passed.
- Full V01 acceptance: passed, 180 checks.
- Mojibake/readiness text check: passed.

Risks and boundaries:

- QC preview filtering is explicitly preview-only and does not modify uploaded files.
- The no-login lab now includes a live upload/service page, so public deployment must avoid real customer data exposure and must keep formal project management behind login.
- Failure-path coverage for invalid preview parameters still needs to be expanded.
- Local runtime outputs under `data/` and `work/` must not be committed.

## 20. MNE analysis function design basis

Date: 2026-06-18

Scope:

- Distilled MNE documentation review and multi-model consultation into a canonical project design basis for EEG analysis functions.
- Added `docs/modules/mne_analysis_function_design_basis.md` as the required starting document for QC, preprocessing, PSD, ERP, TFR, PAC, Connectivity, statistics, reports, and BIDS planning.
- Linked the new basis from `docs/modules/analysis_modules_design_matrix.md` so future module design conversations can find it from the module index.

Current design baseline:

- Current dependency contract is `mne>=1.8`; local verification was run against `mne 1.10.1`.
- Core MNE APIs verified locally: `Raw.compute_psd`, `Epochs.compute_psd`, `Epochs.compute_tfr`, `mne.Epochs`, `mne.Evoked`, `mne.events_from_annotations`, `mne.find_events`, `mne.preprocessing.ICA`, and `mne.Report`.
- `mne_connectivity` and `mne_bids` are not installed in the current environment; Connectivity and BIDS remain preview / roadmap items until dependencies and methods are explicitly approved.

Current step:

- QC, preprocessing preview, PSD, and event-conditioned ERP are the first concrete function-design targets.
- TFR remains preview until epoch, baseline, frequency, decimation, memory, and statistics rules are specified.
- PAC requires custom or external-method design; it must include surrogate/null-model controls before beta.
- Connectivity requires dependency review and volume-conduction/reference-risk controls before beta.

Next step:

1. Write `docs/modules/psd_design.md` using the MNE basis.
2. Write `docs/modules/erp_design.md` with event mapping, baseline, reject, and drop-log rules.
3. Expand `docs/modules/qc_design.md` failure-path coverage and preprocessing preview boundary.

## 21. Customer entry value proposition copy

Date: 2026-06-18

Scope:

- Updated the customer-facing Open Design entry value list to emphasize visual UI operation, no-code use, traceable results, and research-grade chart delivery.
- Kept the simplified research-customer tone and preserved the registered brand mark in the entry page.
- This is copy-only UI positioning work and does not change authentication, backend APIs, EEG algorithms, or lab-module behavior.

Validation:

- `git diff --check -- frontend/open-design-entry-demo.html`: passed.
- `python scripts/check_no_mojibake.py`: passed.

## 22. PSD detailed design

Date: 2026-06-18

Scope:

- Added `docs/modules/psd_design.md` as the detailed design for the stable v0.1 PSD workflow.
- Linked the PSD design from `docs/modules/analysis_modules_design_matrix.md`.
- Clarified the current runner contract around `resting_psd`, MNE Welch PSD, band power tables, reproducibility outputs, validation gaps, and next implementation tasks.

Current PSD baseline:

- Current runner: `eeg_core/analysis/psd.py`.
- Current workflow id: `resting_psd`.
- Current MNE method: `Raw.compute_psd(method="welch")` after EEG channel picking and optional filter/notch preview parameters.
- Current required outputs: `tables/band_power.csv`, `tables/channel_band_power.csv`, `reproducibility/psd_summary.json`, reproducibility files, `result.json`, `manifest.json`, and `log.txt`.

Next step:

1. Add explicit PSD parameter validation for `fmin`, `fmax`, `l_freq`, `h_freq`, and `notch_freq`.
2. Add PSD failure-path acceptance for no EEG channel, all bad channels, illegal frequency range, and invalid notch.
3. Add PSD chart/table UI or report-level visual acceptance after parameter failures are covered.

## 23. Analysis Lab feature selection guide

Date: 2026-06-18

Scope:

- Simplified the Analysis Lab review table from an internal experience checklist into a customer-facing feature selection guide.
- The guide now maps research questions to recommended modules, required inputs, expected outputs, and review advice.
- Removed repeated entry/local-access wording so the page focuses on what QC, PSD, ERP, TFR, PAC, and Connectivity can help researchers decide.

Validation:

- `node --check frontend/module-lab.js`: passed.
- `python scripts/check_no_mojibake.py`: passed.

## 23. ERP detailed design

Date: 2026-06-18

Scope:

- Added `docs/modules/erp_design.md` as the detailed design for event-conditioned ERP / P300 workflow.
- Linked the ERP design from `docs/modules/analysis_modules_design_matrix.md`.
- Clarified the conditional status: ERP is enabled only when events/annotations exist and marker semantics are verified.

Current ERP baseline:

- Current runner: `eeg_core/analysis/erp.py`.
- Current workflow id: `erp_p300`.
- Current MNE flow: `events_from_annotations`, filtering/reference, `mne.Epochs`, condition `Evoked`, and N100/P200/P300 metric extraction.
- Current required outputs: `tables/erp_metrics.csv`, `reproducibility/erp_summary.json`, reproducibility files, `result.json`, `manifest.json`, and `log.txt`.

Next step:

1. Add explicit ERP parameter validation for `tmin`, `tmax`, `baseline`, `components`, `reject_eeg_uv`, filter, and reference.
2. Add drop log / rejected epoch summaries to ERP outputs.
3. Add an event-id confirmation surface before treating ERP results as scientifically interpretable.

## 24. EEG workflow information architecture

Date: 2026-06-18

Scope:

- Reorganized the customer-facing workbench navigation around the EEG research workflow: project setup, data import, preview/preprocessing, analysis branches, statistics, figures, downloads, data assets, guide, and reference material.
- Reworked the no-login preview area so its main frame follows the same workflow from project setup through downloadable reproducibility artifacts.
- Updated Analysis Lab detail navigation from generic input/output labels to workflow labels: data input, parameters/preprocessing, analysis method, metric outputs, figures, downloads, review, and boundaries.
- Kept internal routes stable, including `frontend/module-lab.html`, `module-lab.html?module=...`, and `research-module/*`.

Review basis:

- MNE/project evidence supports the flow Raw import -> QC/preprocessing -> events/epochs or spectrum/evoked branches -> statistics -> figures/reports/artifacts.
- External model calls were attempted for IA review: GPT route returned 503; GLM route returned token usage but an empty content file, so final decisions used repository MNE docs, prior review artifacts, and internal reverse review.

Boundary:

- No backend API, authentication, route, or EEG algorithm change is included in this UI information-architecture pass.
- `eeg_core/analysis/erp.py` has a separate local algorithm change and must not be mixed into this commit.

Validation:

- `node --check frontend/app.js frontend/module-lab.js frontend/research-modules.js scripts/acceptance_research_modules_static.mjs`: passed.
- `python scripts/check_no_mojibake.py`: passed.
- `git diff --check`: passed.
- `node scripts/acceptance_research_modules_static.mjs`: passed, 212 checks, 6 module pages.

## 25. Experience Center customer-facing copy

Date: 2026-06-18

Scope:

- Customer-visible lab wording is now consolidated around `体验中心`.
- The no-login page uses project-oriented labels such as `体验项目`, `详情`, `检查清单`, `体验清单`, and `结果包`.
- QC / PSD / ERP remain labeled `已可体验`; TFR / PAC / Connectivity remain `预览` / `即将开放`.
- The static acceptance script now checks the Experience Center wording and rejects the old customer-facing lab-name/status language.

Boundary:

- Internal filenames and routes remain unchanged: `frontend/module-lab.html`, `module-lab.html?module=...`, `frontend/research-modules.html`, and `research-module/*`.
- No backend API, authentication, route, task runner, or EEG algorithm behavior changed.
- Formal workbench login/register remains separate from the no-login Experience Center.

Validation:

- `node --check frontend/module-lab.js`: passed.
- `node scripts/acceptance_research_modules_static.mjs`: passed, 212 checks, 6 module pages.
- `python scripts/check_no_mojibake.py`: passed.

## 26. Experience Center copy polish

Date: 2026-06-18

Scope:

- Further polished the Experience Center customer-visible wording after the first rename pass.
- Replaced remaining visible labels such as `模块结果包`, `MNE 设计`, `打开体验中心`, and `高级方法启用前` with `结果包`, `MNE 方法`, `进入体验中心`, and `高级方法开放前`.
- Kept `体验中心`, `体验项目`, `已可体验`, `预览`, `即将开放`, `检查清单`, `体验清单`, and `结果包` as the visible copy baseline.

Boundary:

- No URL, filename, backend API, authentication, task runner, or EEG algorithm changes.
- Formal workbench login/register and the no-login Experience Center boundary remain unchanged.

Validation:

- `node --check frontend/module-lab.js`: passed.
- `node scripts/acceptance_research_modules_static.mjs`: passed, 212 checks, 6 module pages.
- `python scripts/check_no_mojibake.py`: passed.

## 2026-06-18 Login background Image2 update

Scope:

- Generated a new login background illustration with the user-level `GPT_IMAGE_2_*` Image2 route.
- Saved the generated neuron-firing medical teaching illustration to `frontend/assets/qlanalyser-neuron-firing-bg.png`.

Image route evidence:

- Base route: `https://llm-all.pro/v1/images/generations`.
- Model: `gpt-image-2`.
- `/v1/models` was reachable from the injected user-level environment and listed `gpt-image-2`.
- Image generation returned `b64_json` after transient remote disconnects and retry.

Risks / notes:

- Keep API keys in user environment only; do not commit keys, tokens, request logs, or generated debug output.
- `docs/modules/qc_common_data_preparation_requirements.md` was present as an unrelated untracked file and was not touched.

## 2026-06-18 UI information noise cleanup

Scope:

- Removed internal explanatory cards from the logged-in workbench entry area.
- Removed the "new user safety guard" panel that repeated method and output rules already covered elsewhere.
- Kept the customer path focused on the actual EEG workflow and the Analysis Lab entry.

Validation:

- `node --check frontend/app.js frontend/module-lab.js frontend/research-modules.js scripts/acceptance_research_modules_static.mjs`: passed.
- `node scripts/acceptance_research_modules_static.mjs`: passed, 212 checks, 6 module pages.
- Removed stale acceptance wording that treated the new Analysis Lab name as invalid.

## 2026-06-18 QC/PSD common data preparation plan service

Scope:

- Added a shared `data_preparation_plan` service for QC and PSD before changing PSD algorithm details.
- Supports plan save/read/update, optimistic revision conflict detection, task parameter validation, task reference generation, and artifact contract files.
- Registered `/api/data-preparation/plans` routes and connected task creation to optional `data_preparation_plan_id` / `data_preparation_revision` parameters.

Output contract:

- `reproducibility/data_preparation_plan.json`
- `reproducibility/data_preparation_task_reference.json`
- `reproducibility/data_preparation_artifact_contract.json`
- Contract version: `qlanalyser-data-preparation-v0.1`

Validation:

- `python -m py_compile backend/models/data_preparation.py backend/services/data_preparation_service.py backend/api/data_preparation.py backend/services/task_service.py backend/main.py scripts/acceptance_data_preparation_plan.py scripts/acceptance_data_preparation_api.py`: passed.
- `python scripts/acceptance_data_preparation_plan.py`: passed.
- `python scripts/acceptance_data_preparation_api.py`: passed.
- `eeg_core/analysis/psd.py` was not modified.

## 2026-06-19 C0 customer Pilot flow checkpoint

Scope:

- Cleaned the default customer entry and workbench flow so the visible path reads as project -> data import -> data preparation -> analysis branch -> result review -> delivery download.
- Hid secondary module-center and operations entries from the default login page while keeping internal routes/selectors available for controlled access and tests.
- Renamed customer-visible dashboard labels away from internal/demo/local/backend wording.
- Replaced stale `customer_oddball_case` asset links with existing static assets under `frontend/assets`.
- Mirrored the cleaned default entry into `frontend/expert-entry-demo.html` so old entry URLs do not diverge.
- Strengthened UI acceptance to enter through `?pilot=1`, reject visible internal customer-copy regressions, hide visible operations navigation for customer role, and fail on non-API page asset/navigation 4xx responses.

Validation:

```powershell
git fetch origin --prune
node --check frontend\app.js
node --check scripts\acceptance_v01_ui.mjs
node --check scripts\acceptance_research_modules_static.mjs
python scripts\check_no_mojibake.py
node scripts\acceptance_research_modules_static.mjs
python scripts\acceptance_data_preparation_plan.py
python scripts\acceptance_data_preparation_api.py
python scripts\acceptance_psd_p0.py
python scripts\acceptance_qc_preview_service.py
python scripts\acceptance_v01_full.py
python scripts\smoke_v01_api.py
node scripts\acceptance_v01_ui.mjs
```

Result:

- Static/browser module acceptance: passed, 217 checks, 6 pages.
- Mojibake/readiness check: passed.
- Data preparation plan acceptance: passed.
- Data preparation API acceptance: passed.
- PSD P0 acceptance: passed.
- QC preview acceptance: passed, 13 artifacts, 64 preview channels checked.
- Full V01 API acceptance: passed, 191 checks.
- Smoke V01 API: passed.
- Real browser E2E: passed using `http://127.0.0.1:4174/?pilot=1` and `http://127.0.0.1:8001/api`; project/create, invalid upload guard, valid FIF upload, QC, PSD, ERP, and report creation all returned expected results.

Risks and boundaries:

- Worktree remains mixed with C1/C2/C3/governance changes; do not use `git add .`.
- Branch remains locally ahead of `origin/main`; do not push until C0 separates owner scopes and confirms release baseline.
- This checkpoint did not change shared backend data-preparation/PSD contracts beyond already-validated local changes.

## Non-negotiable product goal - customer self-serve production loop

The first production-grade QLanalyser release is not complete until a customer can complete the product loop without developer help:

1. Register or log in with email, phone verification, or WeChat sandbox registration.
2. Upload EEG data through the customer product UI.
3. Recharge through the sandbox payment flow and see wallet/balance/ledger records.
4. Select a real analysis pipeline or preset method, including preprocessing/data preparation, PSD, ERP/P300, and bandpower outputs where applicable.
5. Adjust analysis parameters in a real form, not only read static method descriptions.
6. Run the backend analysis on the uploaded or selected EEG file.
7. See task status, artifacts, report/package links, and download the real outputs.
8. Request an invoice, let an admin review/upload the invoice, and receive the invoice in the customer inbox.

Static pages, screenshots, method text, synthetic-only illustrations, or buttons that only show descriptions do not satisfy this goal. Demo datasets may be kept for onboarding, but production readiness requires the same frontend/backend contract to work for customer-uploaded data and generated results.

## Progress - Customer preset analysis is now real, not static

Date: 2026-06-20

The formal customer workbench now has interactive preset analysis controls for:

- Preprocessing / QC plan confirmation.
- PSD / bandpower parameters and real PSD task submission.
- ERP / P300 event, epoch and baseline parameters with real ERP task submission.

Focused browser evidence:

- Script: `scripts/acceptance_customer_preset_analysis.mjs`
- Evidence: `work/release_evidence/20260620-customer-preset-analysis/customer_preset_analysis.json`
- Screenshot: `work/release_evidence/20260620-customer-preset-analysis/customer_preset_analysis.png`
- Verified flow: customer project -> EEG upload -> data-preparation plan -> PSD parameters -> `/api/tasks` -> artifact links -> ERP parameters -> `/api/tasks` -> artifact links.

This does not complete the full production goal yet. Remaining gates include Chinese copy cleanup and DeepSeek review, ERP/QC inclusion in full V01 acceptance, page visual QA refresh after the new controls, sanitized evidence refresh, and final release boundary review.

## Progress - Reference / CSD beta module is runnable

Date: 2026-06-22

The Analysis Lab now includes a runnable `reference_csd` beta module instead of a disabled CSD preview card.

Implemented scope:

- Backend runner: `eeg_core/analysis/reference_csd.py`
- Task path: `POST /api/tasks` with `module_name=reference_csd`, `workflow_id=reference_csd`
- Frontend entry: `frontend/module-lab.js` runnable beta card with reference mode, preview window, preview channels, and CSD advanced parameters
- Output evidence: `reference_summary.json`, `csd_summary.json`, `reference_lineage.json`, `parameters.json`, `workflow.json`, `software_versions.json`, `result.json`, `manifest.json`, CSV tables, and SVG before/after previews
- Boundary: sensor-space reference/CSD preprocessing only; not source localization, diagnosis, or brain-region activation

Validation:

- `python -m py_compile ...`: passed for changed Python files.
- `node --check frontend/module-lab.js`: passed.
- `node --check scripts/acceptance_module_lab_live_runner.mjs`: passed.
- `python scripts/acceptance_reference_csd_module.py`: passed; runner and task-service path produced 20 artifacts.
- `python scripts/acceptance_module_contract_registry.py`: passed; `reference_csd` remains beta and is now enabled with a runner.
- `python scripts/acceptance_module_lab_preview_selectors.py`: passed; CSD is runnable, TFR/PAC/Connectivity remain preview.
- `node scripts/acceptance_module_lab_live_runner.mjs`: passed after local backend restart; upload -> QC -> PSD -> ERP -> Reference/CSD all completed through UI clicks.

Evidence:

- `work/release_evidence/20260622-reference-csd-module/acceptance_reference_csd_module.json`
- `work/release_evidence/20260620-module-lab-live-runner/module_lab_live_runner.json`
- `work/release_evidence/module_lab_preview_selectors/acceptance_module_lab_preview_selectors.json`

Known boundary:

- Full-repo `python scripts/check_no_mojibake.py` currently fails on pre-existing `frontend/app.js` and `frontend/index.html` text. The CSD-changed files passed a targeted replacement-marker scan.

## Progress - Connectivity beta module is runnable

Date: 2026-06-22

The Analysis Lab now includes a runnable `connectivity` beta module with backend execution and real UI task submission.

Implemented scope:

- Backend runner: `eeg_core/analysis/connectivity.py`
- Task path: `POST /api/tasks` with `module_name=connectivity`, `workflow_id=connectivity`
- Frontend entry: `frontend/module-lab.js` runnable beta card with method, frequency band, window, channel selection, threshold, and max-edge controls
- Output evidence: connectivity matrix CSV, long edge table CSV, matrix SVG, sensor network SVG, `connectivity_summary.json`, `parameters.json`, `method_description.json`, `workflow.json`, `software_versions.json`, `result.json`, `manifest.json`, and `log.txt`
- Boundary: sensor-space single-record beta analysis only; not causality, source localization, diagnosis, brain-region communication, group statistics, or significance testing

Validation:

- `python -m py_compile ...`: passed for changed Python files.
- `node --check frontend/module-lab.js`: passed.
- `node --check scripts/acceptance_module_lab_live_runner.mjs`: passed.
- `python scripts/acceptance_connectivity_module.py`: passed; runner and task-service path produced 18 artifacts.
- `python scripts/acceptance_module_contract_registry.py`: passed.
- `python scripts/acceptance_module_lab_preview_selectors.py`: passed.
- `node scripts/acceptance_module_lab_live_runner.mjs`: passed after local backend 8001 restart; UI-only flow uploaded EEG and completed QC, PSD, ERP, Reference/CSD, and Connectivity tasks from the selected file.

Evidence:

- `work/release_evidence/20260622-connectivity-module/acceptance_connectivity_module.json`
- `work/release_evidence/20260620-module-lab-live-runner/module_lab_live_runner.json`
- `work/release_evidence/module_lab_preview_selectors/acceptance_module_lab_preview_selectors.json`

Known boundary:

- Full product/release is still not complete. This is a beta module-level gate only.
- Full-repo `python scripts/check_no_mojibake.py` remains blocked by pre-existing replacement-marker text outside the connectivity slice; targeted scan on connectivity-touched files passed.

## Progress - PAC / CFC beta module is runnable

Date: 2026-06-22

The Analysis Lab now includes a runnable `pac` beta module with backend execution and real UI task submission.

Implemented scope:

- Backend runner: `eeg_core/analysis/pac.py`
- Task path: `POST /api/tasks` with `module_name=pac`, `workflow_id=pac_cfc`
- Frontend entry: `frontend/module-lab.js` runnable beta card with channels, phase-frequency grid, amplitude-frequency grid, phase-bin count, analysis window, dynamic window, and bad-channel controls
- Output evidence: `pac_comodulogram_long.csv`, `pac_binned_amplitude.csv`, `pac_dynamic_curve.csv`, `pac_channel_summary.csv`, three SVG figures, `pac_summary.json`, `frequency_grid.json`, `filter_edge_policy.json`, `parameters.json`, `method_description.txt`, `result.json`, `manifest.json`, and `log.txt`
- Boundary: single-record sensor-space descriptive PAC beta only; not p-values, significance, group comparison, diagnosis, causality, source localization, or brain-region communication

Validation:

- `python -m py_compile ...`: passed for changed Python files.
- `node --check frontend/module-lab.js`: passed.
- `node --check scripts/acceptance_module_lab_live_runner.mjs`: passed.
- `python scripts/acceptance_pac_module.py`: passed; runner and task-service path produced 23 artifacts.
- `python scripts/validate_pac_beta_artifacts.py work/release_evidence/20260622-pac-module/runner_output --out work/release_evidence/20260622-pac-module/pac_runner_validator.json`: passed.
- `python scripts/acceptance_module_contract_registry.py`: passed; `pac_cfc` remains beta and is now enabled with a runner.
- `python scripts/acceptance_module_lab_preview_selectors.py`: passed; PAC is runnable, TFR remains preview.
- `node scripts/acceptance_module_lab_live_runner.mjs`: passed after local backend 8001 restart; UI-only flow uploaded EEG and completed QC, PSD, ERP, PAC, Reference/CSD, and Connectivity tasks from the selected file.

Evidence:

- `work/release_evidence/20260622-pac-module/acceptance_pac_module.json`
- `work/release_evidence/20260622-pac-module/pac_runner_validator.json`
- `work/release_evidence/20260620-module-lab-live-runner/module_lab_live_runner.json`
- `work/release_evidence/module_lab_preview_selectors/acceptance_module_lab_preview_selectors.json`

Known boundary:

- Full product/release is still not complete. This is a beta module-level gate only.
- PAC defaults were intentionally set to amplitude centers `30,50,70 Hz` and an `0-8 s` window so the bundled short 200 Hz UI fixture passes Nyquist and duration checks; users can still configure higher bands when sampling rate and recording length support them.

## Progress - Project CRUD persistence and EDF-to-results review checkpoint

Date: 2026-06-22

The customer workspace project/data management path now treats project edit and archive as real backend-persisted actions instead of UI-only feedback. The end-to-end UI-only path from login and synthetic EDF upload through QC, data preparation, epoch set, PSD, ERP, TFR, PAC, and report ZIP download was revalidated on refreshed local services.

Implemented scope:

- Project edit calls `PATCH /api/projects/{project_id}` and records `persistence: backend_patch`.
- Project archive calls `POST /api/projects/{project_id}/archive` and records `persistence: backend_archive`.
- Project delete remains guarded and records `persistence: not_mutated`.
- The five-round multi-role UI-only review now fails if these persistence contract fields are missing or mismatched.
- Review checkpoint includes fixed review access, demo credentials, permission scope, and credential safety notes.

Validation:

- `python -m py_compile backend\models\project.py backend\services\storage_service.py backend\api\projects.py`: passed.
- `node --check frontend\app.js scripts\acceptance_multirole_click_review_5rounds.mjs`: passed.
- `python scripts\check_no_mojibake.py frontend\app.js frontend\index.html backend\models\project.py backend\services\storage_service.py backend\api\projects.py scripts\acceptance_multirole_click_review_5rounds.mjs`: passed.
- Backend route smoke after service restart: project create, patch, and archive passed.
- `node scripts\acceptance_customer_login_demo.mjs`: passed.
- `python scripts\acceptance_project_data_preparation_ia.py`: passed.
- `node scripts\acceptance_multirole_click_review_5rounds.mjs`: passed.
- `node scripts\acceptance_edf_upload_to_results_ui_only.mjs`: passed; produced report ZIP `work/release_evidence/edf_upload_to_results_ui_only/report_a69280766dc6.zip`.
- `python scripts\acceptance_professional_chinese_gate.py`: passed.
- `python scripts\acceptance_mainline_eeg_contract_mapping_consumption.py`: passed.
- `python scripts\acceptance_round006_tfr_real_report_consumption.py`: passed.
- `python scripts\acceptance_round006_pac_real_report_consumption.py`: passed.
- `python scripts\validate_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0750-project-crud-persistence-edf-results-checkpoint.json`: passed.
- `python scripts\acceptance_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0750-project-crud-persistence-edf-results-checkpoint.json`: passed.

Evidence:

- `work/release_evidence/checkpoints/2026-06-22-0750-project-crud-persistence-edf-results-checkpoint.md`
- `work/release_evidence/checkpoints/2026-06-22-0750-project-crud-persistence-edf-results-checkpoint.json`
- `work/release_evidence/multirole_click_review_5rounds/multirole_click_review_5rounds.json`
- `work/release_evidence/edf_upload_to_results_ui_only/edf_upload_to_results_ui_only.json`
- `work/release_evidence/edf_upload_to_results_ui_only/report_a69280766dc6.zip`

Known boundary:

- This is a review checkpoint, not a full release pass.
- PAC and TFR remain beta/descriptive single-record outputs and must not be promoted to stable or interpreted as diagnosis, treatment, causality, group statistics, significance, source localization, or brain-region communication.

## Progress - Report delivery page is visible and verified

Date: 2026-06-22

The customer report-delivery view now has an explicit empty state before report creation and a generated-report state after report creation. The EDF UI-only acceptance now verifies that the delivery page shows the generated report id and a ZIP download action before saving the downloaded report package.

Implemented scope:

- `frontend/app.js` now renders a clear `realDeliveryLinks` empty state when no report exists.
- Generated report delivery cards now use clean UTF-8-safe Chinese labels for report id, ZIP download, and HTML view.
- The delivery view is re-rendered on view changes so the report download page is not blank.
- The five-round UI-only review uses the visible navigation item for the report download view.
- The EDF-to-results runner now records `deliveryState` and fails if the generated report is not visible on the delivery page.

Validation:

- `node --check frontend\app.js scripts\acceptance_multirole_click_review_5rounds.mjs scripts\acceptance_edf_upload_to_results_ui_only.mjs`: passed.
- `python scripts\check_no_mojibake.py frontend\app.js frontend\index.html scripts\acceptance_multirole_click_review_5rounds.mjs scripts\acceptance_edf_upload_to_results_ui_only.mjs work\release_evidence\edf_upload_to_results_ui_only\edf_upload_to_results_ui_only.json work\release_evidence\multirole_click_review_5rounds\multirole_click_review_5rounds.json`: passed.
- `node scripts\acceptance_multirole_click_review_5rounds.mjs`: passed; report download view is visible and has a clear empty state.
- `python scripts\acceptance_pac_module.py`: passed after a transient local service interruption during the first EDF rerun.
- `node scripts\acceptance_customer_login_demo.mjs`: passed.
- `node scripts\acceptance_edf_upload_to_results_ui_only.mjs`: passed on rerun; generated report `report_d5e669acfd33` and downloaded `report_d5e669acfd33.zip`.
- `python scripts\acceptance_professional_chinese_gate.py`: passed.
- `python scripts\acceptance_mainline_eeg_contract_mapping_consumption.py`: passed.
- `python scripts\acceptance_round006_tfr_real_report_consumption.py`: passed.
- `python scripts\acceptance_round006_pac_real_report_consumption.py`: passed.
- `python scripts\validate_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0806-report-delivery-visible-edf-results-checkpoint.json`: passed.
- `python scripts\acceptance_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0806-report-delivery-visible-edf-results-checkpoint.json`: passed.

Evidence:

- `work/release_evidence/checkpoints/2026-06-22-0806-report-delivery-visible-edf-results-checkpoint.md`
- `work/release_evidence/checkpoints/2026-06-22-0806-report-delivery-visible-edf-results-checkpoint.json`
- `work/release_evidence/edf_upload_to_results_ui_only/edf_upload_to_results_ui_only.json`
- `work/release_evidence/edf_upload_to_results_ui_only/report_d5e669acfd33.zip`
- `work/release_evidence/multirole_click_review_5rounds/multirole_click_review_5rounds.json`

Known boundary:

- This is a review checkpoint, not a full release pass.
- One EDF rerun saw a transient local backend connection interruption during PAC; PAC module acceptance and the full EDF chain passed immediately afterward.
- PAC and TFR remain beta/descriptive single-record outputs.

## Progress - EDF-to-results chain now records backend health stability

Date: 2026-06-22

The synthetic EDF customer path now verifies not only that the user can upload data, run preparation, run PSD/ERP/TFR/PAC, view results, and download a report ZIP, but also that the backend process remains healthy and stable throughout the long UI-only chain.

Implemented scope:

- `/api/health` exposes process identity and uptime fields: `process_id`, `started_at`, and `uptime_sec`.
- `scripts/acceptance_edf_upload_to_results_ui_only.mjs` samples backend health before and after major UI steps.
- The EDF UI-only runner records `backendHealthSamplesOk`, `backendProcessStable`, and `backendProcessIdsObserved`.
- The runner now fails the product path if the backend PID changes during a successful long-chain run.
- A review-ready checkpoint was written with REVIEW_ACCESS, demo credentials, permission scope, and credential safety.

Validation:

- `python -m py_compile backend\api\health.py`: passed.
- `node --check scripts\acceptance_edf_upload_to_results_ui_only.mjs`: passed.
- `python scripts\check_no_mojibake.py backend\api\health.py scripts\acceptance_edf_upload_to_results_ui_only.mjs`: passed.
- Backend health check returned `status=ok`, `process_id=37620`, and uptime evidence.
- Frontend review URL returned HTTP 200 with UTF-8 content type.
- `node scripts\acceptance_customer_login_demo.mjs`: passed.
- `node scripts\acceptance_multirole_click_review_5rounds.mjs`: passed.
- `node scripts\acceptance_edf_upload_to_results_ui_only.mjs`: passed; generated report `report_2fdf3d048d26`.
- EDF runner evidence recorded `backendHealthSamplesOk=true`, `backendProcessStable=true`, and `backendProcessIdsObserved=[37620]`.
- `python scripts\acceptance_professional_chinese_gate.py`: passed.
- `python scripts\acceptance_mainline_eeg_contract_mapping_consumption.py`: passed.
- `python scripts\acceptance_round006_tfr_real_report_consumption.py`: passed.
- `python scripts\acceptance_round006_pac_real_report_consumption.py`: passed.
- `python scripts\validate_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0818-edf-chain-backend-health-stability-checkpoint.json`: passed.
- `python scripts\acceptance_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0818-edf-chain-backend-health-stability-checkpoint.json`: passed.
- `python scripts\check_no_mojibake.py work\release_evidence\checkpoints\2026-06-22-0818-edf-chain-backend-health-stability-checkpoint.md work\release_evidence\checkpoints\2026-06-22-0818-edf-chain-backend-health-stability-checkpoint.json work\release_evidence\edf_upload_to_results_ui_only\edf_upload_to_results_ui_only.json work\release_evidence\multirole_click_review_5rounds\multirole_click_review_5rounds.json`: passed.

Evidence:

- `work/release_evidence/checkpoints/2026-06-22-0818-edf-chain-backend-health-stability-checkpoint.md`
- `work/release_evidence/checkpoints/2026-06-22-0818-edf-chain-backend-health-stability-checkpoint.json`
- `work/release_evidence/edf_upload_to_results_ui_only/edf_upload_to_results_ui_only.json`
- `work/release_evidence/edf_upload_to_results_ui_only/report_2fdf3d048d26.zip`
- `work/release_evidence/multirole_click_review_5rounds/multirole_click_review_5rounds.json`

Known boundary:

- This is a review checkpoint, not a full release pass.
- PAC and TFR remain beta/descriptive single-record outputs and must not be promoted to stable from this evidence alone.
- This closes the transient backend-interruption concern for the latest EDF-to-results run; it does not prove production high availability.

## Progress - OCR-first PDF artifact QA gate is executable and consumed

Date: 2026-06-22

The latest report ZIP now has an executable OCR-first PDF artifact QA gate. The gate renders every PDF page to images, uses PaddleOCR as the primary full-page parse, keeps PyMuPDF native text-layer audit as auxiliary evidence, and verifies report-page sections, parameters, warnings, provenance, and boundary wording.

Implemented scope:

- `scripts/acceptance_pdf_ocr_artifact_qa.py` was executed against the latest EDF UI-only report package.
- The gate wrote `work/release_evidence/pdf_ocr_artifact_qa/pdf_ocr_artifact_qa.json`.
- The latest report ZIP under QA was `work/release_evidence/edf_upload_to_results_ui_only/report_2fdf3d048d26.zip`.
- OCR-first evidence is consumed by the production goal matrix, release gate summary, and release evidence manifest.
- A review-ready checkpoint was written with REVIEW_ACCESS, demo credentials, permission scope, and credential safety.

Validation:

- `python -m py_compile scripts\acceptance_pdf_ocr_artifact_qa.py scripts\acceptance_production_goal_matrix.py scripts\build_release_gate_summary.py scripts\refresh_release_readiness_manifest.py scripts\run_release_review_gate.py`: passed.
- `python scripts\check_no_mojibake.py scripts\acceptance_pdf_ocr_artifact_qa.py scripts\acceptance_production_goal_matrix.py scripts\build_release_gate_summary.py scripts\refresh_release_readiness_manifest.py scripts\run_release_review_gate.py`: passed.
- `python scripts\acceptance_pdf_ocr_artifact_qa.py`: passed.
- OCR evidence: `primary_parse=PaddleOCR_all_pages`, `auxiliary_text_layer_audit=yes`, `artifact_validator_verdict=pass`, `blockers=[]`.
- Page checks passed for cover, overview, data quality, methods, results, and appendix.
- `python scripts\acceptance_production_goal_matrix.py`: passed with external boundaries.
- `python scripts\build_release_gate_summary.py`: passed; release status remains `blocked_external_inputs`.
- `python scripts\refresh_release_readiness_manifest.py`: passed; evidence manifest contains `pdf_ocr_artifact_qa`.
- `python scripts\acceptance_release_gate_summary.py`: passed.
- `python scripts\acceptance_release_manifest_consistency.py`: passed.
- `python scripts\acceptance_release_no_misclaim.py`: passed.
- `python scripts\validate_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0824-pdf-ocr-artifact-qa-checkpoint.json`: passed.
- `python scripts\acceptance_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0824-pdf-ocr-artifact-qa-checkpoint.json`: passed.
- `python scripts\check_no_mojibake.py work\release_evidence\checkpoints\2026-06-22-0824-pdf-ocr-artifact-qa-checkpoint.md work\release_evidence\checkpoints\2026-06-22-0824-pdf-ocr-artifact-qa-checkpoint.json work\release_evidence\pdf_ocr_artifact_qa\pdf_ocr_artifact_qa.json`: passed.

Evidence:

- `work/release_evidence/checkpoints/2026-06-22-0824-pdf-ocr-artifact-qa-checkpoint.md`
- `work/release_evidence/checkpoints/2026-06-22-0824-pdf-ocr-artifact-qa-checkpoint.json`
- `work/release_evidence/pdf_ocr_artifact_qa/pdf_ocr_artifact_qa.json`
- `work/release_evidence/pdf_ocr_artifact_qa/pages/page_001.png`
- `work/release_evidence/pdf_ocr_artifact_qa/pages/page_002.png`
- `work/release_evidence/20260620-v01-acceptance/release_gate_summary.json`
- `work/release_evidence/20260620-v01-acceptance/evidence_manifest.json`

Known boundary:

- This is PDF artifact QA evidence, not a full release pass.
- Native text-layer audit remains auxiliary and must not be removed.
- OCR may confuse punctuation or rare words; key fields remain cross-checked against report JSON/native text.

## Progress - Login feedback, visible UTF-8, and EDF-to-report chain verified

Date: 2026-06-22

The customer entry now gives a clear validation message when users click login without credentials, and the visible login/workbench Chinese copy is no longer blocked by the old duplicated global script scope. The EDF upload-to-results UI-only runner was rerun after the fix and passed from synthetic EDF upload through data preparation, PSD, ERP, TFR beta, PAC beta, report ZIP download, and inline PDF OCR artifact QA.

Validation:

- Browser check: empty login click shows `请先输入邮箱/手机号和密码，再点击登录。`.
- Browser check: `demo.customer@quanlan.cn` / `demo123456` enters `项目工作台`; visible bad-marker scan returned empty.
- `node --check frontend\app.js`: passed.
- `python scripts\check_no_mojibake.py frontend\app.js frontend\index.html`: passed.
- `node scripts\acceptance_edf_upload_to_results_ui_only.mjs`: passed; generated `report_8d4a83bd4ae3`.
- Inline PDF OCR QA in the UI-only runner: `artifact_validator_verdict=pass`, `primary_parse=PaddleOCR_all_pages`, `blockers=[]`.
- `python scripts\acceptance_psd_real_report_consumption.py`: passed.
- `python scripts\acceptance_qc_real_report_consumption.py`: passed.
- `python scripts\acceptance_round006_tfr_real_report_consumption.py`: passed.
- `python scripts\acceptance_round006_pac_real_report_consumption.py`: passed.
- `python scripts\acceptance_round008_erp_real_report_consumption.py`: passed.
- `python scripts\run_release_review_gate.py`: passed, 29 steps, failed steps empty.
- `python scripts\acceptance_release_gate_summary.py`: passed; release status remains `blocked_external_inputs`.
- `python scripts\validate_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0856-edf-ui-login-mojibake-inline-pdf-ocr-checkpoint.json`: passed.
- `python scripts\acceptance_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0856-edf-ui-login-mojibake-inline-pdf-ocr-checkpoint.json`: passed.

Evidence:

- `work/release_evidence/checkpoints/2026-06-22-0856-edf-ui-login-mojibake-inline-pdf-ocr-checkpoint.md`
- `work/release_evidence/checkpoints/2026-06-22-0856-edf-ui-login-mojibake-inline-pdf-ocr-checkpoint.json`
- `work/release_evidence/edf_upload_to_results_ui_only/edf_upload_to_results_ui_only.json`
- `work/release_evidence/edf_upload_to_results_ui_only/report_8d4a83bd4ae3.zip`
- `work/release_evidence/pdf_ocr_artifact_qa/pdf_ocr_artifact_qa.json`
- `work/release_evidence/20260620-v01-acceptance/release_gate_summary.json`

Known boundary:

- This is a review checkpoint, not a full release pass.
- Public cloud/provider readiness remains blocked by external inputs.
- PAC and TFR remain beta, single-record, descriptive, and non-diagnostic.

## Progress - 08 replacement entry verified 07-consumable module evidence

Date: 2026-06-22

The replacement `08` research-room entry validated a real 07-consumable evidence chain instead of producing a knowledge-only handoff. The mainline EEG contract-consumption checker, PSD real-report consumption checker, module-lab live P0 evidence, release summary, and one-command release review gate now agree.

Validation:

- `python scripts\acceptance_mainline_eeg_contract_mapping_consumption.py`: passed; status `ready_for_07_review`, bridge recommendation `CONDITIONAL PASS for entering mainline integration review`.
- `python scripts\acceptance_psd_real_report_consumption.py`: passed for VR-EO-0003 with no blockers against the latest UI-only report ZIP.
- `node scripts\acceptance_module_lab_live_runner.mjs`: produced P0-consumable QC/PSD/ERP evidence using one uploaded customer file; advanced module timeout remains tracked outside this P0 row.
- `python scripts\acceptance_production_goal_matrix.py`: passed with external boundaries and no failed requirements.
- `python scripts\acceptance_release_gate_summary.py`: passed after the P0 gap-repair evidence path was made visible in the Markdown summary.
- `python scripts\run_release_review_gate.py`: passed, 33 steps, failed steps empty.

Evidence:

- `work/release_evidence/20260620-module-lab-live-runner/module_lab_live_runner.json`
- `work/release_evidence/20260620-v01-acceptance/production_goal_requirement_matrix.json`
- `work/release_evidence/20260620-v01-acceptance/release_gate_summary.json`
- `work/release_evidence/20260620-v01-acceptance/release_gate_summary.md`
- `work/release_evidence/20260620-v01-acceptance/release_review_gate_run.json`

Known boundary:

- Release status remains `blocked_external_inputs`; this is local/sandbox review evidence, not public production readiness.
- TFR/PAC/advanced module status remains beta/descriptive and must not be promoted from this P0 evidence.

## Progress - Service 07 all beta module-lab runner evidence

Date: 2026-06-22

The replacement Service 07 entry closed a real module-support checkpoint for the Analysis Lab instead of producing a knowledge-only summary. The latest local evidence proves one uploaded customer EEG file can drive all current module-lab runners through `/api/tasks` and artifact download lists.

Validated modules:

- QC / metadata: passed, 8 artifact links.
- PSD / bandpower: passed, 19 artifact links.
- ERP / P300: passed, 11 artifact links.
- TFR / ERSP / ITC beta: passed, 20 artifact links.
- PAC / CFC beta: passed, 24 artifact links.
- Reference / CSD beta: passed, 20 artifact links.
- Multitaper PSD / TFR beta: passed, 22 artifact links.
- Sensor connectivity beta: passed, 18 artifact links.

Validation:

- `python -m py_compile eeg_core\analysis\connectivity.py backend\services\task_service.py scripts\acceptance_connectivity_module.py`: passed.
- `node --check frontend\module-lab.js scripts\acceptance_module_lab_live_runner.mjs`: passed.
- `python scripts\acceptance_connectivity_module.py`: passed.
- `python scripts\acceptance_multitaper_psd_tfr_module.py`: passed after restarting the local 8001 backend to current source.
- `QLANALYSER_MODULE_LAB_SCOPE=all node scripts\acceptance_module_lab_live_runner.mjs`: passed with 8 real task submissions and no browser errors.
- `python scripts\check_no_mojibake.py frontend\module-lab.js frontend\module-lab.html frontend\module-lab.css work\release_evidence\20260620-module-lab-live-runner\module_lab_live_runner.json work\release_evidence\20260622-connectivity-module\acceptance_connectivity_module.json work\release_evidence\20260622-multitaper-psd-tfr-module\acceptance_multitaper_psd_tfr_module.json`: passed.

Evidence:

- `work/release_evidence/20260620-module-lab-live-runner/module_lab_live_runner.json`
- `work/release_evidence/20260620-module-lab-live-runner/module_lab_live_runner_all.png`
- `work/release_evidence/20260622-connectivity-module/acceptance_connectivity_module.json`
- `work/release_evidence/20260622-multitaper-psd-tfr-module/acceptance_multitaper_psd_tfr_module.json`

Known boundary:

- This is beta module integration evidence, not full release readiness.
- The UI evidence is conditionally acceptable for module integration only. Under `UI_INTERACTION_REVIEW_GATE_20260622.md`, final UI pass still needs narrower viewport evidence, explicit error/recovery state evidence, keyboard/focus path evidence, and better long-task progress treatment.
- The first all-module UI run failed because the local backend process was stale and did not include the current multitaper task-service branch; restarting local uvicorn fixed the runtime mismatch.
- Worktree remains mixed. Do not push, deploy, or use broad staging from this state.

## 2026-06-22 Service 07 module-lab P0/Beta UI split

### Goal
Close the 07A revise item where module-lab mixed P0 customer workflow, beta runnable methods, and preview-only methods in one primary module grid.

### Changed files
- `frontend/module-lab.js`: added P0 and beta module id groups, rendered separate P0/Beta/Preview sections, and kept upload/refresh/select listener ownership in `bindRunners()` instead of `renderFileOptions()`.
- `frontend/module-lab.css`: added section-intro/workflow-section styling and made the module index responsive as three workflow columns.
- `frontend/module-lab.html`: repaired the corrupted title/meta copy and bumped module-lab asset query versions.

### Validation
- `node --check frontend\module-lab.js`: passed.
- `node --check scripts\acceptance_module_lab_live_runner.mjs`: passed.
- `python scripts\check_no_mojibake.py frontend\module-lab.js frontend\module-lab.html frontend\module-lab.css`: passed.
- `node scripts\acceptance_module_lab_live_runner.mjs`: passed for P0 scope; one uploaded customer EEG file created exactly 3 `/api/tasks` submissions for QC, PSD, and ERP; all completed with downloadable artifacts.
- `QLANALYSER_MODULE_LAB_SCOPE=all node scripts\acceptance_module_lab_live_runner.mjs`: not accepted in this turn; it exceeded the local wait window and was stopped, so beta all-scope evidence remains the prior checkpoint until rerun as a separate packet.

### Evidence
- P0 runner output observed in terminal: status `passed`, moduleScope `p0`, taskPostCount `3`, modules `qc`, `psd`, `erp` all passed.
- Screenshot path emitted by runner: `work\release_evidence\20260620-module-lab-live-runner\module_lab_live_runner_all.png`.
- Patch/recovery working copies: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\tmp\module-lab-patch\mod\frontend`.

### Boundary
- This is a module-lab product-structure and event-binding repair, not a new scientific module.
- Beta modules remain research/beta evidence surfaces and are not promoted to stable release-ready modules by this UI split.
- No push or deploy was performed.
- why_not_mini: UI verdict, accidental patch-apply recovery, and final acceptance required GPT-5.5/Codex judgment; scripts supplied deterministic syntax, mojibake, and runner evidence only.


## 2026-06-23 Service 07 module-lab beta all-scope runner and visual gate evidence

### Goal
Continue the QLanalyser module-support mainline with real beta module verification evidence after the P0/Beta/Preview module-lab split.

### Parallel packages
- Package A - script/validator runner: start local backend/frontend acceptance services, verify backend health and demo dataset, then run module-lab all-scope runner against real `/api/tasks`.
- Package B - visual/evidence matrix: inspect desktop all-scope screenshot, generate a 390px mobile screenshot, and summarize P0/Beta/Preview UI boundary evidence.

### Environment/root cause fixed
- Initial all-scope run failed because `http://127.0.0.1:4174` was not running.
- After frontend start, the browser reported CORS, but direct backend logs showed the true root cause was `PermissionError` writing `data/state/.projects.lock`.
- Restarting the local backend with permission to write project state fixed `/api/lab/demo/dataset`; CORS preflight itself returned 200.

### Validation
- `Invoke-RestMethod http://127.0.0.1:8001/api/health`: passed; backend process `28976`.
- `Invoke-RestMethod http://127.0.0.1:8001/api/lab/demo/dataset`: passed after authorized backend restart.
- `QLANALYSER_MODULE_LAB_SCOPE=all node scripts\acceptance_module_lab_live_runner.mjs`: passed.
- `python scripts\check_no_mojibake.py work\release_evidence\20260623-module-lab-beta-all-scope\module_lab_live_runner_all_scope.json`: passed.
- Mobile visual check at 390px: P0/Beta/Preview sections present; module index collapsed to one column (`gridTemplateColumns` observed as `328px`).

### Evidence matrix
| module | workflow | completed | workflow match | uses uploaded file | download links | verdict |
| --- | --- | --- | --- | --- | ---: | --- |
| qc | metadata_qc | true | true | true | 8 | pass |
| psd | resting_psd | true | true | true | 19 | pass |
| erp | erp_p300 | true | true | true | 11 | pass |
| tfr | tfr_ersp_itc | true | true | true | 20 | pass |
| pac | pac_cfc | true | true | true | 24 | pass |
| reference_csd | reference_csd | true | true | true | 20 | pass |
| multitaper_psd_tfr | multitaper_psd_tfr | true | true | true | 22 | pass |
| connectivity | connectivity | true | true | true | 18 | pass |

### Evidence paths
- All-scope runner JSON: `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260623-module-lab-beta-all-scope\module_lab_live_runner_all_scope.json`
- All-scope desktop screenshot: `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260623-module-lab-beta-all-scope\module_lab_live_runner_all_scope.png`
- Mobile 390px screenshot: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_mobile_390_20260623.png`

### Acceptance boundary
- GPT-5.5/Codex acceptance: module-lab all-scope beta runner now has current 2026-06-23 evidence. All 8 module-lab runnable modules pass real `/api/tasks` execution using one uploaded customer EEG file.
- UI acceptance is evidence-pass for beta/module integration and P0/Beta/Preview separation. It is not a final polished customer UI pass because the page remains long and parameter-dense.
- No push or deploy was performed.
- why_not_mini: root-cause interpretation, visual verdict, and final acceptance required GPT-5.5/Codex; script/validator supplied deterministic runner, health, JSON, and screenshot evidence.


## 2026-06-23 Service 07 module-lab UI gate evidence packet

### Goal
Continue QLanalyser module development support under QGCS by closing the remaining module-lab UI evidence gaps after the P0/Beta/Preview split and all-scope runner pass.

### Route decision
- GPT-5.5/Codex planner/acceptance: define UI gate scope, inspect screenshots, judge product boundary.
- script/validator execution packet: capture deterministic browser evidence for narrow viewport, keyboard focus path, and load-error state.
- skip reason for deepseek-v4-pro: the bounded work was browser automation and filesystem evidence capture, where deterministic Playwright output is stronger than model-generated observation.

### Executor evidence
- Validator script: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_ui_gate_capture_20260623.mjs`
- Validator JSON: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_ui_gate_20260623\module_lab_ui_gate_20260623.json`
- Narrow viewport screenshot: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_ui_gate_20260623\module_lab_narrow_390.png`
- Keyboard focus screenshot: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_ui_gate_20260623\module_lab_keyboard_focus.png`
- Load-error screenshot: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_ui_gate_20260623\module_lab_load_error_390.png`

### Checks
- `node outputs\module_lab_ui_gate_capture_20260623.mjs`: passed.
- `python scripts\check_no_mojibake.py outputs\module_lab_ui_gate_20260623\module_lab_ui_gate_20260623.json outputs\module_lab_ui_gate_capture_20260623.mjs`: passed.
- Verdict inputs from JSON:
  - `hasP0BetaPreviewOnNarrow`: true
  - `narrowSingleColumn`: true
  - `keyboardHasVisiblePath`: true
  - `loadErrorVisible`: true

### GPT-5.5/Codex acceptance
- UI gate evidence pass for structure and interaction coverage: narrow viewport preserves P0/Beta/Preview sections, module index collapses to one column, keyboard focus reaches visible controls, and backend-load failure is visible.
- Not a final polished UI pass: screenshots still show mojibake in some runtime Chinese text and the load-error state says `Analysis lab failed to load: Failed to fetch` without friendly recovery guidance.
- Next repair should be a small UI copy/error-state code packet, not another evidence-only packet.

### Boundary
- No push or deploy was performed.
- This packet adds validation/evidence only. Product code was not changed in this UI gate packet.



## Progress - Module Lab review-system UI gate retest

Date: 2026-06-23

Scope:

- Finished the review-system test -> guidance -> optimization -> retest loop for the Module Lab visible release-review surface.
- Repaired remaining mojibake-prone hero and research-boundary copy in `frontend/module-lab.js` by switching the visible strings to ASCII-safe English.
- Repaired the load-error empty state layout in `frontend/module-lab.css` so the title, technical error, and recovery guidance render as separate readable lines.
- No backend runner behavior was changed in this slice.

Validation evidence:

- JS syntax: `node --check frontend\module-lab.js` passed.
- Targeted mojibake validator: `python scripts\check_no_mojibake.py frontend\module-lab.js frontend\module-lab.html frontend\module-lab.css` passed.
- Targeted broken-text/readback scan: `rg -n "Failed to fetch|\\u4e|\\u7|mojibake-marker" frontend/module-lab.js frontend/module-lab.html frontend/module-lab.css` returned no matches.
- UI gate runner: `node C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_ui_gate_capture_20260623.mjs` passed all boolean inputs.
- UI gate JSON: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_ui_gate_20260623\module_lab_ui_gate_20260623.json`.
- Fresh screenshots: `module_lab_narrow_390.png`, `module_lab_keyboard_focus.png`, `module_lab_load_error_390.png` in the same evidence folder.
- Runner evidence retained: `work\release_evidence\20260623-module-lab-beta-all-scope\module_lab_live_runner_all_scope.json`; rerun skipped because this slice only changed visible copy and CSS empty-state layout, not `/api/tasks`, runner parameters, backend module dispatch, or artifact contracts.
- Release review gate check: `python scripts\run_release_review_gate.py` still reports one pre-existing failed step, `accept_v01_no_group_statistics_boundary`, writing `work\release_evidence\20260620-v01-acceptance\release_review_gate_run.json`.

Verdict:

- Module Lab UI/copy/error-state gate is publish-standard for this slice: no visible mojibake found in fresh screenshots, narrow responsive layout passes, keyboard focus path is present, and load-error recovery state is readable.
- Full product publish readiness is not claimed because the broader release gate still has the existing `accept_v01_no_group_statistics_boundary` failure outside this UI/copy slice.


## Progress - Release review gate passed after review-system repair loop

Date: 2026-06-23

Scope:

- Continued the review-system test -> guidance -> optimization -> retest loop until the authoritative release review gate returned no failed steps.
- Fixed the V01 no-group-statistics boundary blocker by replacing the customer storage page wording with boundary-safe descriptive result-table copy.
- Refreshed customer/admin page visual QA with real browser screenshots for 15 page states across desktop, mobile, and narrow viewports.
- Preserved the public-cloud boundary: this pass is local/sandbox publish-standard evidence; strict public cloud/provider production remains blocked by external Aliyun/OSS/provider inputs.

Current authoritative evidence:

- Full release gate: `work\release_evidence\20260620-v01-acceptance\release_review_gate_run.json` -> `status=passed`, `steps=35`, `failed_steps=[]`.
- Production goal matrix: `work\release_evidence\20260620-v01-acceptance\production_goal_requirement_matrix.json` -> `status=passed_with_external_boundaries`, `failed_requirements=[]`, `external_boundaries=[aliyun_provider_boundary]`.
- V01 no group-statistics boundary: `work\release_evidence\virtual_reviewer_round_008\v01_no_group_statistics_boundary.json` -> `status=passed`, `blockers=[]`.
- Page visual QA: `work\release_evidence\20260620-page-visual-qa\page_visual_qa.json` -> `status=passed`, `pageVisualQa.pass=true`, `pageCount=15`, `viewportCount=3`.
- Page visual QA rerun mirror: `work\release_evidence\20260620-page-visual-qa\page_visual_qa_rerun_4174.json`.
- Page visual screenshots: `work\release_evidence\20260620-page-visual-qa\screenshots\`.
- Module Lab UI gate remains current: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_ui_gate_20260623\module_lab_ui_gate_20260623.json`.
- Module Lab all-scope runner evidence remains current for backend behavior: `work\release_evidence\20260623-module-lab-beta-all-scope\module_lab_live_runner_all_scope.json`.

Verdict:

- Accepted as local/sandbox publish-standard by the review system: the full release review gate is passed and failed_steps is empty.
- Not claimed as strict public-cloud/provider production-ready until `aliyun_provider_boundary` external inputs are supplied and strict preflight is rerun.


## Progress - Aliyun/provider boundary continuation receipt

Date: 2026-06-23

Scope:

- Continued after the local/sandbox release review gate passed.
- Performed a non-destructive Aliyun/provider boundary readback and strict preflight rerun.
- No deploy, public-cloud mutation, production config write, OSS write, backup write, or provider callback mutation was performed.

Evidence:

- Boundary receipt JSON: `work\release_evidence\20260623-aliyun-boundary-continuation\aliyun_boundary_continuation_receipt.json`.
- Boundary receipt MD: `work\release_evidence\20260623-aliyun-boundary-continuation\aliyun_boundary_continuation_receipt.md`.
- Strict preflight evidence: `work\release_evidence\20260620-aliyun-staging\aliyun_staging_preflight.json`.
- Full local/sandbox release gate remains passed: `work\release_evidence\20260620-v01-acceptance\release_review_gate_run.json` -> `status=passed`, `failed_steps=[]`.
- Production matrix remains `passed_with_external_boundaries`: `work\release_evidence\20260620-v01-acceptance\production_goal_requirement_matrix.json` -> `failed_requirements=[]`, `external_boundaries=[aliyun_provider_boundary]`.

Current strict preflight status:

- `status=blocked_missing_prerequisites`
- `passed=2`
- `todos=9`
- `failed=0`

Missing external inputs / todo groups:

- `deepseek_copy_gate`: latest changed copy still needs current official-direct review evidence.
- `oss_required_env`: OSS endpoint, bucket, access key id, and access key secret are not set.
- `oss_storage_backend`: `QLANALYSER_STORAGE_BACKEND=oss` is not set.
- `oss_allow_write`: isolated staging write gate `QLANALYSER_ALIYUN_OSS_ALLOW_WRITE=1` is not set.
- `oss_lifecycle_evidence`: exported OSS lifecycle policy evidence path is not set.
- `oss2_dependency`: staging runtime still needs `python -m pip install -r requirements.txt` evidence.
- `backup_required_env`: backup bucket and prefix are not set.
- `deploy_origin_env`: public base URL, API base URL, and CORS origins are not set.
- `provider_boundary_env`: payment/email/SMS/WeChat/provider callback evidence variables are not set.

Verdict:

- Local/sandbox publish-standard remains accepted.
- Strict public-cloud/provider readiness remains open and blocked on external owner/provider inputs.

## 2026-06-23 8501 service discovery and customer Oddball frontend wiring

Status:

- `http://127.0.0.1:8501/` is not an active local listener in the current environment.
- The active local QLanalyser development services are the backend at `http://127.0.0.1:8001/api` and the frontend at `http://127.0.0.1:4174/`.
- The active repository is `D:\Quanlan\Codes\Python\quanlan-analyser-official`.

Changes:

- Added the existing customer Oddball ERP figures, CSV summaries, manifest, ZIP package, methods text, and figure-caption downloads to the active `frontend/index.html` result and delivery pages.
- Kept email wording conservative: the UI states that SMTP has not been verified and does not claim that email was sent.

Evidence:

- Port/process evidence: `4174` is served by `http-server`; `8001` is served by `uvicorn backend.main:app`; `8501` refused connection.
- HTTP smoke: `http://127.0.0.1:8001/api/health` returned 200; `http://127.0.0.1:4174/` returned 200.


## 2026-06-25 Module Lab Chinese UI review page

Task goal:

- Translate the direct test-data Module Lab review page into Chinese while preserving real backend task execution.

Changed files:

- `frontend/module-lab.js`: translated visible Module Lab copy, form labels, status text, error/recovery text, section descriptions, and select-option display labels into Chinese. Internal API values, workflow ids, and method acronyms are preserved for backend compatibility.

Validation:

```powershell
node --check frontend\module-lab.js
python scripts\check_no_mojibake.py frontend\module-lab.js frontend\module-lab.html frontend\module-lab.css
node C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\inspect_module_lab_visible_text_20260625.mjs
node C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\smoke_module_lab_cn_run_qc_20260625.mjs
```

Evidence:

- Narrow Chinese screenshot: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_cn_20260625\module_lab_cn_390.png`.
- Visible text capture: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_cn_20260625\visible_text.txt`.
- QC result screenshot: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_cn_20260625\module_lab_cn_qc_result.png`.
- QC smoke result: real backend task completed and result panel showed Chinese `任务完成`.

Acceptance note:

- Accepted for user review: the direct test-data page is now Chinese-first, with professional EEG method acronyms and file names intentionally retained.
- 2026-06-25 12:18 CST - Module Lab grouped-method review page accepted locally.

  Current status:

  - Module Lab now groups same-family methods into review cards with an in-card method selector:
    - Data readiness: QC.
    - Spectral/time-frequency: PSD, TFR, multitaper PSD/TFR.
    - Event-related: ERP/P300.
    - Reference/spatial transform: reference/CSD.
    - Coupling/connectivity: PAC/CFC and sensor connectivity.
  - Existing backend module and workflow contracts are preserved; the UI still submits the selected method's original `module_name`, `workflow_id`, and method-specific parameters to `/api/tasks`.

  Verification:

  - Syntax and UTF-8 checks passed for touched frontend and acceptance files.
  - Local EDF generated at `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_local.edf`.
  - Browser E2E passed on `http://127.0.0.1:4174/module-lab.html?api=http://127.0.0.1:8001/api&acceptance=grouped-methods-e2e`.
  - E2E result: generated EDF uploaded as `eeg_7d53b8fd1e4b`; all 8 runnable methods completed with artifact links.

  Evidence:

  - `work\release_evidence\20260625-module-lab-grouped-methods-e2e\generated_edf_summary.json`.
  - `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.json`.
  - `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.png`.

  Remaining boundary:

  - This is local Module Lab acceptance, not public cloud/provider release evidence.

- 2026-06-25 13:02 CST - Module Lab method taxonomy corrected after product review.

  Current status:

  - The previous broad "spectral/time-frequency" grouping was split because PSD and TFR answer different analysis questions.
  - The previous "coupling/connectivity" grouping was split because PAC/CFC and sensor connectivity have different scientific interpretations.
  - Current review taxonomy:
    - QC / data readiness.
    - Continuous spectral power: PSD / bandpower.
    - Event-locked time-domain response: ERP / P300.
    - Event-locked time-frequency dynamics: TFR / ERSP / ITC.
    - Multitaper estimator: multitaper PSD/TFR with internal analysis-family parameter.
    - Reference/spatial transform: reference / CSD.
    - Cross-frequency coupling: PAC / CFC.
    - Sensor connectivity.

  Verification:

  - Taxonomy browser check passed on the normal review URL.
  - Generated-EDF full E2E passed again: 8 method groups rendered, no unnecessary single-method dropdowns, and 8/8 runnable methods completed with backend artifacts.

  Evidence:

  - `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_taxonomy_review_20260625\taxonomy_review.json`.
  - `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_taxonomy_review_20260625\taxonomy_review.png`.
  - `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.json`.

- 2026-06-25 13:52 CST - Module Lab beta parameter surface and layout upgraded.

  Current status:

  - PSD and ERP parameter surfaces were already expanded from code review.
  - Remaining runnable beta methods now expose additional backend-effective parameters:
    - TFR: channel picks and average output flag.
    - PAC: surrogate count, random seed, filter edge padding, edge trim.
    - Reference/CSD: bad channels and simple bipolar-pair shorthand.
    - Multitaper PSD/TFR: remove DC, bad channels, picks, baseline mode, FFT and zero-mean toggles.
    - Connectivity: explicit current-recording reference selector.
  - Structured bad-segment editors and advanced component/pair editors remain future UI work; not exposed as raw JSON.

  Verification:

  - Module-level acceptance passed for TFR, PAC, Reference/CSD, Multitaper PSD/TFR, and Connectivity.
  - Full Module Lab generated-EDF E2E passed after the parameter expansion: generated EDF upload plus 8/8 runnable methods completed with artifacts.
  - Layout review passed on desktop and narrow viewport; no horizontal overflow, 8 groups rendered, primary actions visible.

  Evidence:

  - `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.json`.
  - `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_layout_review_20260625\layout_review.json`.

- 2026-06-25 15:10 CST - Module Lab requirements and test plan baseline added.

  Current status:

  - Added `docs\product\module_lab_method_test_bench_requirements_and_test_plan.md`.
  - The document records Module Lab as a no-account / no-formal-project method development test bench, with preprocessing retained and each analysis branch independently testable.
  - It defines current 9-entry method taxonomy, backend mapping expectations, parameter exposure rules, UI/layout requirements, generated-EDF E2E requirements, layout review requirements, release acceptance criteria, and current evidence paths.

  Next:

  - Use this document as the baseline for the next Module Lab UI review and method-specific parameter/editor iterations.

- 2026-06-25 15:35 CST - Module Lab visual polish pass completed for review.

  Current status:

  - `frontend\module-lab.html`, `frontend\module-lab.js`, and `frontend\module-lab.css` now present Module Lab as a Chinese-first method development test bench with stronger visual hierarchy and clearer evidence language.
  - The UI now highlights no-account testing, real backend execution, 9 independent method entries, data-readiness-first workflow, and artifact/parameter evidence.
  - Backend task contracts and scientific taxonomy were preserved.

  Validation:

  - `node --check frontend\module-lab.js`: passed.
  - `node --check scripts\acceptance_module_lab_grouped_methods_e2e.mjs`: passed.
  - `python -X utf8 scripts\check_no_mojibake.py frontend\module-lab.js frontend\module-lab.css frontend\module-lab.html`: passed.
  - Layout review script: passed, 9 groups, no horizontal overflow.
  - Browser QC smoke: completed real task `task_2ec674631d4c`, parameter echo visible, 8 artifacts visible.

  Evidence:

  - `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_polish_20260625\module_lab_polished_qc_smoke.json`
  - `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_polish_20260625\module_lab_polished_qc_smoke.png`
  - `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_layout_review_20260625\layout_review.json`

  Boundary:

  - This slice accepted visual polish and focused QC smoke. Full all-method generated-EDF E2E should be rerun as the next verification artifact before treating the polish as release-candidate complete.
  - `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_layout_review_20260625\desktop.png`.
  - `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_layout_review_20260625\narrow.png`.

- 2026-06-25 14:26 CST - Multitaper PSD/TFR presentation corrected.

  Current status:

  - Module Lab no longer presents "Multitaper PSD / TFR" as a single combined method.
  - Review surface now has 9 independent method entries:
    - QC / data readiness.
    - PSD / bandpower.
    - ERP / P300.
    - Event-locked TFR.
    - Multitaper PSD.
    - Event-locked multitaper TFR.
    - Reference / CSD.
    - PAC / CFC.
    - Sensor connectivity.
  - The backend runner remains shared for the two multitaper entries, but the UI fixes `analysis_family=psd` or `analysis_family=tfr` per entry and maps both to backend `multitaper_psd_tfr`.

  Verification:

  - Syntax and UTF-8 checks passed.
  - Layout review passed with 9 groups and no horizontal overflow.
  - Full generated-EDF E2E passed with both `multitaper_psd` and `multitaper_tfr` independently executed.

  Evidence:

  - `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.json`.
  - `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_layout_review_20260625\layout_review.json`.

- 2026-06-26 00:05 CST - Module Lab grouped-methods closed-parameter E2E repair accepted.

  Current status:

  - Continued the 02 QLanalyser module-support line after the inherited grouped-methods E2E failure.
  - Root cause: advanced parameter fields were rendered inside a closed `details.advanced-params` block, so real browser acceptance could not edit fields such as `multitaper_psd.picks` even though the inputs existed in the DOM.
  - Fix: `frontend\module-lab.js` now renders advanced parameter blocks open by default, preserving backend module ids, workflow ids, parameter names, and artifact contracts.
  - Local service impact: only a temporary backend `8001` process was started for verification and then stopped; existing frontend `4174` was left untouched. No router, Headroom, IPC, gateway, or process-communication config was changed.

  Validation:

  - `node --check frontend\module-lab.js`: passed.
  - `python -X utf8 scripts\check_no_mojibake.py frontend\module-lab.js scripts\acceptance_module_lab_grouped_methods_e2e.mjs`: passed.
  - `python scripts\acceptance_multitaper_psd_tfr_module.py`: passed, 22 artifacts, no failures.
  - `node scripts\acceptance_module_lab_grouped_methods_e2e.mjs`: passed with 9 grouped UI entries, 0 method pickers, 0 errors, and all runnable methods completed: `qc, psd, tfr, multitaper_psd, multitaper_tfr, erp, reference_csd, pac, connectivity`.

  Evidence:

  - `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.json` (status `passed`, errors `0`, uploaded EDF `eeg_6df62d80be11`).
  - `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.png`.

- 2026-06-26 01:10 CST - 02 -> 07 Module Lab mainline integration accepted.

  Current status:

  - Beta zone is merged into the 07 mainline as an internal beta / review surface, not as a public stable customer entry.
  - The accepted method surface contains 9 grouped entries: `qc`, `psd`, `tfr`, `multitaper_psd`, `multitaper_tfr`, `erp`, `reference_csd`, `pac`, and `connectivity`.
  - `multitaper_psd` and `multitaper_tfr` keep separate UI form ids while sharing backend runner/task module `multitaper_psd_tfr`; old UI form id `data-runner-form="multitaper_psd_tfr"` is not used.
  - Router, Headroom, IPC, gateway, and process-communication configuration were not changed.

  Validation:

  - Syntax and UTF-8/mojibake checks passed for `frontend\module-lab.js`, grouped E2E, visible-fields, layout review, acceptance stack, and packet builder scripts.
  - Module-level gates passed for `multitaper_psd_tfr`, `connectivity`, `reference_csd`, and `pac`.
  - Standardized 8001/4174 stack passed: visible-fields, layout review, generated EDF, and full grouped-methods E2E all returned success.
  - Layout review passed for desktop `1440x1000`, mobile `390x844`, and narrow `360x800`, with 9 groups, 0 method pickers, 6 beta cards, and no horizontal overflow.

  Evidence:

  - `work\release_evidence\07-mainline-integration\module_lab_integration_manifest.json`.
  - `work\release_evidence\07-mainline-integration\module_lab_visible_fields.json`.
  - `work\release_evidence\07-mainline-integration\module_lab_layout_review.json`.
  - `work\release_evidence\07-mainline-integration\module_lab_acceptance_stack.json`.
  - `work\release_evidence\07-mainline-integration\module_lab_mainline_acceptance_packet.json`.
