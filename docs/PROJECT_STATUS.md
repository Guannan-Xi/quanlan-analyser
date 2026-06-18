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
- UI acceptance 在默认脚本中因 4174 前端服务未启动失败；手动启动后端 8000 与前端 4174 后，`scripts/acceptance_v01_ui.mjs` 通过。
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
- `scripts/run_v01_acceptance.ps1` 默认要求 4174 前端服务已启动；未启动时 UI acceptance 会因 `ERR_CONNECTION_REFUSED` 失败。手动启动 8000/4174 后 UI 脚本可通过。
- 当前正式数据库缺失，JSON state 适合单机 Pilot，但多用户并发、数据一致性、备份恢复存在风险。
- 当前未接入真实持久化任务队列，分析任务可能阻塞 HTTP 请求；较大 EEG 文件会带来超时和体验风险。
- 上传文件仅按后缀限制，文件大小、恶意文件、重复文件、存储清理和权限隔离策略待完善。
- 前端、报告包、部署说明中仍可能存在旧产品命名和旧定位文案，存在品牌不一致风险。
- 高级分析方法如 PAC、Connectivity、TFR、机器学习应继续保持禁用或明确返回不可用，避免 Pilot 承诺过高。
- 报告可复核性已经有雏形，但仍需持续验证输入文件信息、参数、运行日志、软件版本、输出路径是否完整保存。
- 本次验收生成/更新 `data/state`、`data/uploads`、`data/derivatives`、`data/reports`、`work/acceptance` 等本地产物，不应混入提交。

## 8. 最近一次修改

本次执行 QLanalyser Online v0.1 Pilot 基线验收：smoke 通过；完整 acceptance 的 compile、frontend syntax、core/worker、full API 通过；默认 UI 步骤因 4174 前端服务未启动失败，手动启动 8000/4174 后 UI acceptance 通过；persistence acceptance 通过。同步写入 Pilot 命名基线。

## 9. 下一步建议任务

1. 固化本地验收启动方式：让 acceptance 脚本自动启动或明确要求启动 backend/frontend，避免 UI 步骤因服务未启动失败。
2. 先确认 `main` 与 `origin/main` 的同步策略，再决定是否 merge/rebase 或 push。
3. 做一次产品命名与品牌文案审计，只清理活动页面、报告与部署文档中的旧命名。

## 10. 本地运行方式

后端 API：

```powershell
C:\Users\XGN\miniconda3\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

前端静态服务：

```powershell
cd frontend
npm run serve
```

前端访问 API 示例：

```text
http://127.0.0.1:4174/?api=http://127.0.0.1:8000/api
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
