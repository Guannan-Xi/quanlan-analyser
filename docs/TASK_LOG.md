# QLanalyser Online 任务日志

## 任务记录模板

### 日期
YYYY-MM-DD

### 任务目标
...

### 修改文件
- `path/to/file`：修改原因

### 已完成
...

### 测试方式
...

### 测试结果
...

### 风险点
...

### 未完成事项
...

### 下一步建议
...

---

## 历史任务

### 日期
2026-06-17

### 任务目标
建立项目协作与进度交接机制。

### 修改文件
- `AGENTS.md`
- `docs/PROJECT_STATUS.md`
- `docs/TASK_LOG.md`
- `docs/DECISIONS.md`

### 已完成
- 建立项目级开发规则。
- 建立项目状态文档。
- 建立任务日志模板。
- 建立产品与架构决策记录。

### 测试方式
文档类修改，无需运行应用。

### 测试结果
待确认。

### 风险点
无业务代码修改风险。

### 未完成事项
后续每次代码任务完成后需要持续更新本文档。

### 下一步建议
根据 `docs/PROJECT_STATUS.md` 的项目诊断结果，选择第一个最小开发任务。
---

## 历史任务

### 日期
2026-06-17

### 任务目标
建立 Git 任务提交规则、创建项目专属 Git skill `qlanalyser-git-guard`，并确认 GitHub 远程仓库绑定。

### 修改文件
- `.gitignore`：补充本地环境、密钥证书和 AI 临时目录忽略规则。
- `.agents/skills/qlanalyser-git-guard/SKILL.md`：新增项目专属 Git Guard 工作流 skill。
- `AGENTS.md`：新增每个小任务完成后必须使用 Git Guard 工作流的规则。
- `docs/PROJECT_STATUS.md`：更新最近修改、远程分支差异风险和下一步建议。
- `docs/TASK_LOG.md`：记录本次 Git Guard 规则建立任务。

### 已完成
- 确认当前项目 remote 为 `https://github.com/Guannan-Xi/quanlan-analyser.git`。
- 执行 `git fetch origin`，发现远程 `origin/main` 有新历史。
- 创建 `qlanalyser-git-guard` skill。
- 补充 `.gitignore` 安全规则。
- 将“不自动 push、不 force push、只提交相关文件”的规则写入项目文档。

### 测试方式
文档与规则类修改，无需运行应用；通过 `git diff --cached --name-only` 和 staged diff 检查确认只暂存本次相关文档/skill 文件。

### 测试结果
待提交前最终确认。

### 风险点
当前本地 `main` 与 `origin/main` 存在差异，本地 ahead 2、behind 1；不得自动 push，需要用户确认同步策略。取消全局 `*.png` 忽略后，部分 PNG 资源会出现在未跟踪文件中，后续需要单独判断是否为正式资源。

### 未完成事项
未执行 push；未处理本地与远程分支差异。

### 下一步建议
先确认远程同步策略，再决定是否将本地 commit 推送到 GitHub。
---

## 历史任务

### 日期
2026-06-17

### 任务目标
将品牌注册商标符号 `®` 调整为上角标展示。

### 修改文件
- `AGENTS.md`：品牌规范中的注册商标符号改为 `<sup>®</sup>`。
- `docs/DECISIONS.md`：品牌决策记录中的注册商标符号改为 `<sup>®</sup>`。
- `frontend/index.html`：登录页和侧边栏品牌文案改为上角标注册商标。
- `frontend/styles.css`：新增 `.registered-mark` 样式。
- `frontend/DEPLOY.md`：部署说明品牌文案改为上角标注册商标。
- `outputs/eeglab-mne-mvp/index.html`：同步历史静态输出副本的品牌上角标展示。
- `outputs/eeglab-mne-mvp/styles.css`：同步 `.registered-mark` 样式。
- `outputs/eeglab-mne-mvp/DEPLOY.md`：同步部署说明品牌文案。
- `docs/PROJECT_STATUS.md`：更新最近一次修改与远程分叉风险。
- `docs/TASK_LOG.md`：记录本次任务。

### 已完成
- 已将英文品牌名后的注册商标符号调整为 `<sup>®</sup>` 或网页中的 `<sup class="registered-mark">®</sup>`。
- 已将中文品牌名后的注册商标符号调整为 `<sup>®</sup>` 或网页中的 `<sup class="registered-mark">®</sup>`。
- 已新增上角标样式，减少注册符号对品牌文字视觉高度的影响。

### 测试方式
文案/UI 轻量修改；通过 `rg` 检查裸品牌注册符号是否仍残留，通过 `git diff --cached --name-only` 检查仅暂存本次相关文件。未运行应用测试。

### 测试结果
待提交前最终确认。

### 风险点
当前本地 `main` 与 `origin/main` 仍存在差异；不得自动 push，需要用户确认同步策略。历史静态输出副本同步修改，后续如不再维护该副本需另行确认。

### 未完成事项
未执行 push；未处理本地与远程分支差异。

### 下一步建议
确认是否继续处理品牌命名统一（例如旧的 `QLanalyser 脑电分析平台` 文案）以及远程同步策略。
---

## Latest Task

### Date
2026-06-22

### Goal
Deliver the first runnable beta module in the inherited QLanalyser 02/08 slice: `multitaper_psd_tfr`.

### Modified Files
- `eeg_core/analysis/multitaper_psd_tfr.py`: new multitaper PSD/TFR runner with validation, reproducibility files, and result/manifest/log output.
- `backend/services/task_service.py`: route `multitaper_psd_tfr` through `/api/tasks` and enable the workflow template.
- `backend/services/lab_demo_service.py`: add demo defaults for `multitaper_psd_tfr`.
- `backend/services/billing_service.py`: add task pricing for `multitaper_psd_tfr`.
- `backend/services/quota_service.py`: add quota estimate factor for `multitaper_psd_tfr`.
- `frontend/module-lab.js`: add the multitaper module card and parameter collection, and fix preview rendering.
- `scripts/acceptance_multitaper_psd_tfr_module.py`: standalone runner/task acceptance.
- `scripts/acceptance_module_lab_live_runner.mjs`: add beta module coverage and longer waits for heavy tasks.
- `scripts/acceptance_module_lab_preview_selectors.py`: add the multitaper card to the browser checks.
- `scripts/acceptance_module_contract_registry.py`: expect multitaper beta to be enabled.
- `docs/modules/analysis_module_contract.md`: list multitaper as a beta/lab module.
- `docs/modules/analysis_modules_design_matrix.md`: update module status matrix to reflect current beta runners.
- `docs/PROJECT_STATUS_CURRENT.md`: record the new beta runner in the current status snapshot.

### Completed
- Added a runnable multitaper PSD/TFR beta runner with output files, manifest, log, and reproducibility sidecars.
- Wired the module into task routing, demo defaults, billing, quota, and the analysis lab UI.
- Added dedicated acceptance for the new module and updated browser/contract checks.
- Fixed the module-lab preview rendering bug that blocked the page from loading.

### Tests
- `python -m py_compile` on the touched Python files.
- `python scripts/acceptance_multitaper_psd_tfr_module.py` -> passed.
- `python scripts/acceptance_module_contract_registry.py` -> passed.
- `python scripts/acceptance_module_lab_preview_selectors.py` -> passed.
- `node scripts/acceptance_module_lab_live_runner.mjs` -> passed.

### Results
- The multitaper beta module now runs through `/api/tasks`, appears in the module lab, and emits downloadable artifacts.

## 最新任务

### 日期
2026-06-17

### 任务目标
运行现有 V01 smoke/acceptance 脚本，确认 QLanalyser Online v0.1 Pilot 当前本地原型真实可运行状态；同步记录 Pilot 命名基线。

### 修改文件
- `docs/PROJECT_STATUS.md`：更新基线验收结果、已完成功能、风险点和下一步建议。
- `docs/TASK_LOG.md`：记录本次 smoke/acceptance 命令、结果、失败项与风险。
- `docs/DECISIONS.md`：记录统一命名：产品名 `QLanalyser Online`、版本标记 `Pilot`、完整版本 `QLanalyser Online v0.1 Pilot`、中文说明 `QLanalyser Online Pilot 试用版`。

### 已完成
- 执行 `git status -sb` 与 `git diff --stat`，确认当前工作树存在大量既有未提交业务代码改动和未跟踪资源。
- 执行 smoke 验证，通过。
- 执行完整 acceptance 脚本：Python compileall、frontend syntax、core/worker、full API 均通过；默认 UI 步骤因 4174 前端服务未启动失败。
- 手动启动临时 backend `127.0.0.1:8000` 与 frontend `127.0.0.1:4174` 后，单独执行 UI acceptance，通过。
- 单独执行 persistence acceptance，通过。
- 未修改前端页面、后端逻辑、分析模块或依赖。

### 测试方式
执行以下命令：

```powershell
git status -sb
git diff --stat
C:\Users\XGN\miniconda3\python.exe scripts\smoke_v01_api.py
powershell -ExecutionPolicy Bypass -File scripts\run_v01_acceptance.ps1
# 临时启动 backend/frontend 后：
node scripts\acceptance_v01_ui.mjs
C:\Users\XGN\miniconda3\python.exe scripts\acceptance_v01_persistence.py
```

### 测试结果
- Smoke：通过。
- Full acceptance：部分通过。compileall、frontend syntax、core/worker、full API 通过；UI 步骤在默认环境失败，原因是 `http://127.0.0.1:4174/?api=http://127.0.0.1:8000/api` 连接被拒绝。
- UI acceptance：手动启动 8000/4174 后通过。
- Persistence acceptance：通过。
- Full API acceptance 报告：`work/acceptance/v01_acceptance_latest.json`，状态 `passed`，126 checks，失败数 0。

### 已验证功能
- 服务健康检查：通过。
- 项目创建：通过。
- EEG 上传：通过，包含 `.fif` 上传及缺失/不支持/空文件失败检查。
- Metadata/QC：通过。
- Resting PSD：通过。
- ERP/P300：通过；无事件 ERP 失败路径也通过。
- HTML 报告：通过。
- ZIP 报告包：通过。
- 失败任务列表：通过，admin failed tasks 接口返回失败 ERP 任务。
- 高级方法禁用：TFR、PAC、Connectivity 在 V01 中按预期返回 422。

### 未验证功能
- 不启动服务时的一键 UI acceptance 通过性：未通过，需先启动 4174 前端服务。
- 真实客户部署环境、认证/会话、安全权限、长时间大文件任务、备份恢复：未在本次脚本中验证。

### 风险点
- 当前验收基于本地未提交工作树，存在大量既有业务代码改动和未跟踪资源。
- 当前 `main` 与 `origin/main` 仍处于 ahead/behind 分叉状态，不得自动 push。
- 本次验收生成/更新 `data/state`、`data/uploads`、`data/derivatives`、`data/reports`、`work/acceptance` 等本地产物，不应提交。

### 未完成事项
未修复 acceptance 脚本对 4174 前端服务的启动依赖；未处理远程分叉；未 push。

### 下一步建议
固化验收脚本启动流程，或在 README 中明确启动 backend/frontend 后再运行完整 UI acceptance。

---

## AI handoff skills 接力记录

### 日期
2026-06-17

### 背景
继续 QLanalyser Online 项目时，已确认存在 AI handoff skills，可用于结束对话前写入接力状态，或在新对话中恢复项目上下文。

### 本轮复核
- 执行 `git status -sb`，确认工作树仍有未提交改动，分支 `main...origin/main` 处于 ahead 6、behind 1。
- 复核 GLM sidecar 成功结果：`.ai/glm-results/glm-1781704292-d8d5699c.result.json`，其 checklist 建议继续跑 Playwright、smoke、acceptance、更新 docs、精确暂存并 commit。
- 运行 `python -m compileall backend eeg_core worker scripts`，通过。
- 运行 `npm run check` 于 `frontend/` 与 `outputs/eeglab-mne-mvp/`，均通过。
- 运行 `scripts/run_v01_acceptance.ps1`：compile、frontend syntax、core/worker、full API 均通过；UI 步骤因 4174 前端服务未启动失败。
- 手动启动临时 backend `127.0.0.1:8000` 与 frontend `127.0.0.1:4174` 后，单独运行 `node scripts/acceptance_v01_ui.mjs`，通过；随后已停止临时服务。
- 运行 `scripts/smoke_v01_api.py`，通过。
- 运行 `scripts/acceptance_v01_persistence.py`，通过。
- 运行 `scripts/check_no_mojibake.py` 时发现本文件与 `docs/PROJECT_STATUS.md` 存在问号乱码段落，并已修复。

### 未完成事项
未处理远程分叉；未执行精确暂存、commit 或 push。

### 下一步建议
再次运行 `scripts/check_no_mojibake.py` 与必要的 acceptance 验收后，按变更范围精确 stage；如需结束当前对话，可运行 `qlanalyser-close-chat-handoff` 生成当前接力记录。

---

## v0.1 Pilot architecture/module planning

### Date
2026-06-17

### Goal
Plan the QLanalyser Online v0.1 Pilot architecture and modular EEG analysis roadmap, including current state, MVP target architecture, module boundaries, task system, concurrency target, output contract, test strategy, and phased refactor route.

### Audit summary
- Frontend is static HTML/CSS/JavaScript; backend is FastAPI; state is stored in `data/state/*.json`; files are stored under `data/uploads`, `data/derivatives`, and `data/reports`.
- Analysis code lives mainly in `eeg_core/`, with metadata/QC, PSD, ERP, report, and reproducibility capabilities already present.
- Task creation currently runs analysis synchronously in `backend/services/task_service.py`; `worker/tasks/*` are thin wrappers and are not backed by a real queue yet.
- Report service can produce HTML and ZIP packages, but unified `result.json`, `manifest.json`, and `log.txt` contracts still need follow-up work.
- The 20-user concurrency and 500MB-file goal should be treated as a controlled Pilot capacity probe, not a production SLA.

### Modified files
- `docs/v01_pilot_architecture_plan.md`: added architecture, module boundary, concurrency, output contract, test plan, and phased roadmap planning.
- `docs/PROJECT_STATUS.md`: added the planning document index and architecture judgment.
- `docs/TASK_LOG.md`: recorded this architecture planning audit.

### Verification
- This was a documentation/planning task. It did not change EEG analysis core logic, upload architecture, database, queue, or frontend UI.
- Lightweight checks are being run: Python compileall, frontend JS syntax check, and mojibake check.

### Not completed
- No large directory refactor.
- No PostgreSQL, Redis, Celery, or RQ introduction.
- UI acceptance still depends on a running 4174 frontend service.
- No commit or push performed.

### Next steps
1. Add a unified output-contract adapter for PSD/QC/ERP, starting with `result.json` and `manifest.json`.
2. Stabilize the UI acceptance startup flow so missing 4174 does not fail by surprise.
3. Run a naming audit for active pages, reports, and deployment docs.

---

## Git sync risk audit before adapter work

### Conclusion first
Do not push now. `main` is ahead 7 and behind 1, the remote-only commit is a different object from the local equivalent commit, and the working tree has broad unstaged/untracked changes. The next adapter task should not start until the existing changes are split or parked.

### Commands reviewed
- `git status --short --branch`: `main...origin/main [ahead 7, behind 1]`; staged area empty; broad unstaged/untracked changes present.
- `git remote -v`: origin fetch/push is `https://github.com/Guannan-Xi/quanlan-analyser.git`.
- `git log --oneline --left-right --graph origin/main...HEAD`: local has 7 commits; remote has `bb14003`.
- `git ls-remote origin refs/heads/main`: remote currently points to `bb14003`, so local `origin/main` is current.
- `git diff --stat`: 29 tracked files changed, 1278 insertions and 446 deletions.
- `git diff --cached --stat` and `git diff --cached --name-only`: no staged changes.
- `git log --oneline -10`: latest local commit is `0597e06 docs(architecture): plan v0.1 pilot architecture and analysis modules`.

### Local commits not pushed
- `0597e06 docs(architecture): plan v0.1 pilot architecture and analysis modules` - architecture/module planning docs; keep.
- `e72f1a8 docs(ai): add project handoff skills` - handoff skill docs; keep pending review.
- `4d6a3a6 docs(test): record v01 baseline acceptance` - acceptance record; keep pending review.
- `7c0a062 style(brand): superscript registered marks` - brand styling docs/frontend-related change; keep pending review.
- `10bdd27 docs(git): add guard workflow` - git guard workflow docs; keep.
- `0644c8d docs: add collaboration handoff process` - collaboration handoff docs; keep.
- `fd73a10 Set QLanalyser as the only EEG platform version` - local commit whose content matches remote `bb14003`; keep but reconcile history before push.

### Remote-only commit
- `bb14003 Set QLanalyser as the only EEG platform version` - content diff against local `fd73a10` is empty, but commit object differs. Conflict risk is low at file-content level but high at Git-history/push level because direct push is non-fast-forward.

### Uncommitted change categories
- Frontend pages: `frontend/app.js`, `frontend/index.html`, `frontend/styles.css`, `frontend/expert-entry-demo.html`.
- Frontend/assets: PNG analysis/publication assets and `frontend/assets/paradigm_benchmark/paradigm_coverage_summary.png`.
- Outputs mirror: `outputs/eeglab-mne-mvp/app.js`, `index.html`, `styles.css`, `expert-entry-demo.html`, and neuron background asset.
- Backend API/services: modified `backend/api/*.py`, `backend/main.py`, `backend/services/product_catalog.py`, `report_service.py`, `storage_service.py`, `task_service.py`; untracked `readiness_service.py`, `state_store.py`.
- EEG analysis/report code: modified `eeg_core/analysis/erp.py`, `psd.py`, `eeg_core/io/metadata.py`, `readers.py`, `eeg_core/preprocess/quality.py`, `eeg_core/report/html_report.py`; untracked `eeg_core/report/reproducibility.py`.
- Worker/scripts: modified worker report/preprocess wrappers; untracked acceptance/smoke/virtual-user scripts.
- Docs: modified `README.md`; untracked `docs/v01_production_readiness.md`.
- Runtime state: untracked `data/state/*.json` should not be included in the next adapter commit without a deliberate decision.

### Sensitive scan
No high-risk secret patterns were reported. Medium-risk password assignment pattern hits were found in `frontend/app.js:373` and `outputs/eeglab-mne-mvp/app.js:373`. Values were not printed; confirm they are demo-only before staging these files.

### Recommendation
Do not push. Do not merge or rebase without explicit confirmation. Before adapter work, split or park existing changes, decide how to reconcile `bb14003` with `fd73a10`, and keep `data/state/*.json` plus generated assets out of unrelated commits.


---

### Date
2026-06-18

### Task goal
Research the relevant MNE documentation, split EEG analysis capabilities into standalone static test pages, generate synthetic research test data, publication-style figures, CSV/JSON/TXT/ZIP output packages, and complete one local validation round.

### Modified files
- `frontend/research-modules.html`: new research-module testbench entry page.
- `frontend/research-modules.css`: styles for the testbench and module pages.
- `frontend/research-modules.js`: manifest-driven rendering, CSV/JSON/TXT previews, and download links.
- `frontend/research-module/*.html`: standalone QC, PSD, ERP, TFR, PAC, and Connectivity pages.
- `frontend/assets/research-modules/`: synthetic data, figures, CSV tables, parameters/methods/captions/summaries, and ZIP packages.
- `scripts/generate_research_module_assets.py`: generator for research-module static assets.
- `scripts/acceptance_research_modules_static.mjs`: static acceptance script for the research-module pages.
- `docs/PROJECT_STATUS.md`: records the new testbench scope and validation result.
- `docs/TASK_LOG.md`: records this task and validation result.

### Completed
- Checked official MNE references for Raw, events_from_annotations, Epochs, Evoked, tfr_morlet, plot_topomap, and plot_compare_evokeds.
- Split V01-enabled modules into QC, PSD, and ERP pages.
- Added preview-only pages for TFR / ERSP / ITC, PAC / CFC, and Connectivity, clearly marking them as not enabled in V01 backend execution.
- Generated synthetic research test data, subject-level tables, statistics summaries, method text, captions, reviewer checklist, manifest, and module ZIP packages.
- Each page shows inputs, parameter controls, outputs, figures, CSV tables, parameter JSON, method text, captions, summaries, and package downloads.
- Preserved the research-only guardrail: these outputs are not clinical diagnosis.

### Validation
Commands run:

```powershell
python -m py_compile scripts\generate_research_module_assets.py
node --check frontend\research-modules.js
node --check scripts\acceptance_research_modules_static.mjs
node scripts\acceptance_research_modules_static.mjs
```

Local static service used for browser validation: `http://127.0.0.1:4177/research-modules.html`.

### Result
- Static research-module acceptance: passed.
- Checks: 130.
- Module pages: 6.
- Report: `work/acceptance/research_modules_static_latest.json`.
- Screenshots: `work/research-modules-index.png`, `work/research-modules-erp.png`.

### Risks
- The worktree still contains unrelated legacy uncommitted changes. This task should be committed with precise staging only.
- TFR, PAC, and Connectivity are static research-design previews; they must not be described as enabled V01 backend workflows.
- The generator requires local scientific Python packages, but the committed static pages do not require Python to render.

### Unfinished
- Unified output-contract adapter is not implemented yet.
- TFR/PAC/Connectivity backend execution is not enabled.
- Aliyun public deployment is pending after commit/push.

### Next recommendations
1. Commit and push this static testbench as a GitHub backup.
2. Deploy the static pages to Aliyun and validate `http://39.97.248.225/research-modules.html`.
3. Start the minimal unified output-contract adapter for QC/PSD/ERP result JSON, manifest, artifact list, and package index.

---

## Production-grade state/concurrency hardening and full validation

### Date
2026-06-18

### Goal
Stabilize QLanalyser Online before continuing the unified output-contract adapter: improve concurrency/state/data consistency behavior, align virtual-user acceptance with the current V01 product, and run a complete local plus public validation round.

### Modified files
- `backend/services/state_store.py`: added configurable state root, lock files, safer atomic replace, merge-on-save, single-item upsert/delete, and readiness status alias.
- `backend/services/storage_service.py`: refreshed persistent registries before reads and used single-item state operations for create/update/delete.
- `backend/services/task_service.py`: refreshed tasks/artifacts before reads and used upsert persistence for task/artifact writes.
- `backend/services/report_service.py`: refreshed reports before reads and used upsert persistence for report writes.
- `scripts/acceptance_state_store_concurrency.py`: added isolated multi-process state registry acceptance.
- `scripts/launch_v01_virtual_users.py`: aligned checks with current frontend, research-module manifest, readiness limits, output contract, and robust mojibake detection.
- `scripts/launch_v01_merge9_virtual_users_10rounds.py`: retained 10-round stability launcher for repeated virtual-user checks.
- `scripts/launch_v01_public_virtual_users.py`: aligned public smoke checks with deployed product signals and robust mojibake detection.
- `docs/PROJECT_STATUS.md`: recorded the production hardening and full validation result.
- `docs/TASK_LOG.md`: recorded this task and validation matrix.

### Completed
- Fixed the Windows multi-process state-write issue and prevented stale in-memory registry snapshots from overwriting newer records.
- Added/validated isolated state-root support for concurrency tests.
- Verified V01 services refresh state before user-facing reads.
- Repaired virtual-user acceptance so `checks` can be a list or count, and so production readiness limits use `known_v01_limits`.
- Validated local and public user-facing flows, research-module pages, report packages, guardrails, and reproducibility assets.

### Test commands

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

### Test results
- All local tests passed.
- State concurrency: passed, 72 persisted records.
- Full V01 acceptance: passed, 180 checks.
- Research static acceptance: passed, 130 checks.
- Virtual users: passed, 10/10 rounds, min score 1.0.
- Public virtual users: passed against `http://39.97.248.225`, min score 1.0.
- Mojibake/readiness text check: passed.

### Risks
- Worktree still contains many legacy uncommitted changes. Use exact path staging only; do not stage runtime `data/state/*`, `data/uploads/*`, `data/derivatives/*`, `data/reports/*`, or `work/*` outputs.
- MNE `pick_types()` legacy warnings are visible but non-blocking; modernize MNE API usage later.
- TFR/PAC/Connectivity remain preview-only and must not be marketed as backend-enabled V01 features.

### Next recommendations
1. Commit this production-stability slice with precise staging, then push GitHub backup if the staged diff is clean.
2. Start the minimal unified output-contract adapter for QC/PSD/ERP.
3. Add a future MNE modernization pass to replace legacy `pick_types()` calls after adapter work is stable.

## No-login Analysis Lab formal entry and standalone module pages

Date: 2026-06-18

### Task goal
Add a formal no-login Analysis Lab to the project entry so standalone EEG analysis modules can be opened directly for parallel development and future customer single-module trials.

### Modified files
- `frontend/index.html`: added no-login Analysis Lab button on the login screen and an in-workspace shortcut.
- `frontend/expert-entry-demo.html`: added the same Analysis Lab entry points.
- `frontend/styles.css`: added anchor-button styles for the lab entry buttons.
- `frontend/research-modules.html`: linked the research-module overview to the Analysis Lab.
- `frontend/module-lab.html`, `frontend/module-lab.css`, `frontend/module-lab.js`: new standalone lab overview and per-module detail pages.
- `frontend/assets/qlanalyser-neuron-firing-bg.png` and `frontend/assets/research-modules/figures/qlanalyser-neuron-firing-bg.png`: updated neuron-firing network background.
- `scripts/acceptance_research_modules_static.mjs`: expanded acceptance to cover entry pages, lab overview, six lab module URLs, static module pages, assets, and guardrail sections.

### Implementation notes
- Stable lab URLs: `module-lab.html?module=qc`, `psd`, `erp`, `tfr`, `pac`, `connectivity`.
- Each module page shows inputs, parameters, MNE methods, outputs, figures, file deliverables, acceptance matrix, risks, and handoff notes.
- TFR / PAC / Connectivity remain preview-only; QC / PSD / ERP remain V01-enabled.
- Lab implementation is static and manifest-driven; it does not require login or backend execution.

### Validation
Commands run:

```powershell
node --check frontend\module-lab.js
node --check scriptscceptance_research_modules_static.mjs
python scripts\check_no_mojibake.py
node scriptscceptance_research_modules_static.mjs
```

Result:
- Syntax checks passed.
- Mojibake/readiness check passed.
- Static/lab browser acceptance passed: 189 checks, 6 module pages.
- Report: `work/acceptance/research_modules_static_latest.json`.

### Multi-model / review record
- External consultant call: DeepSeek (`polish`) succeeded in 15.234 s; output file `.ai/module-lab-review/deepseek_review.md`; estimated tokens included in consultant metrics summary.
- Review emphasis: no-login guardrail, preview module labeling, acceptance coverage, and contract clarity. Local evidence confirmed these are covered or documented as risks.
- Gemini/Grok were not called in this specific finishing pass to keep scope bounded after the interruption; fallback internal reverse review was performed against diffs and acceptance evidence.

### Risks
- Worktree still contains unrelated legacy/untracked changes. Stage only this task's files.
- No-login lab must remain restricted to synthetic/static research-demo data until a separate access-control decision is made.

## Aliyun deployment for no-login Analysis Lab

Date: 2026-06-18

### Task goal
Deploy the newly committed no-login Analysis Lab to Aliyun while keeping the formal workbench login boundary intact.

### Deployment
- Public base: `http://39.97.248.225`
- Lab: `http://39.97.248.225/module-lab.html`
- Remote static root: `/opt/qlanalyser/outputs/aliyun-static-lite`
- Remote backup: `/opt/qlanalyser/backups/module-lab-static.20260618_131208.tar.gz`
- Remote wrapper patched with explicit routes for `/module-lab.html`, `/module-lab.css`, and `/module-lab.js`.
- Service restarted: `qlanalyser.service`.

### Validation
- `/`: 200, formal login form still present, lab link present.
- `/research-modules.html`: 200, lab link present.
- `/module-lab.html`: 200, six module cards rendered.
- `/module-lab.html?module=qc|psd|erp|tfr|pac|connectivity`: all 200, no broken lab images, required sections present.
- `python scripts/launch_v01_public_virtual_users.py http://39.97.248.225`: passed, min_score 1.0.

### Boundary
The no-login behavior is only for the static Analysis Lab. The formal workbench/login flow remains separate.


## Conversation sync workflow for multi-dialog development

Date: 2026-06-18

### Goal
Create a reusable workflow so architecture design, module detailed design, and cross-conversation conclusions become stable development inputs for all QLanalyser Online conversations.

### Changes
- Added project skill `qlanalyser-conversation-sync`.
- Added `docs/AI_CONVERSATION_SYNC.md` as the canonical synchronization rule.
- Added `docs/AI_HANDOFF_CURRENT.md` as the short startup basis for new conversations.
- Added templates for conversation records, Feishu summaries, architecture docs, and module design docs.
- Recorded the decision that repository Markdown docs are the single source of truth and Feishu is a review/sync mirror.

### Validation
- Documentation-only change; validation should include `git diff --check` and optional mojibake check.

### Boundary
- Did not touch existing untracked frontend Open Design demo files.
- Did not claim any live Feishu synchronization.


## Architecture and version detailed design consolidation

Date: 2026-06-18

### Goal
Consolidate QLanalyser Online architecture design and version-by-version detailed design into canonical repository docs for multi-conversation development.

### Changes
- Added `docs/architecture/system_architecture.md` as the system architecture source of truth.
- Added `docs/architecture/version_detailed_design.md` for Legacy Static MVP, v0.1 Pilot, v0.2 hardening, v0.3 public beta, v1.0, and v1.x boundaries.
- Added `docs/modules/analysis_modules_design_matrix.md` for QC / PSD / ERP / TFR / PAC / Connectivity status, I/O, output contracts, risk, and promotion criteria.
- Updated architecture/module README files and `docs/AI_HANDOFF_CURRENT.md` so new conversations read the canonical design docs.
- Updated `docs/PROJECT_STATUS.md` with the new architecture documentation basis.

### Validation
- Documentation-only change; run `git diff --check` and `python scripts/check_no_mojibake.py`.

### Boundary
- Did not modify runtime code.
- Did not touch existing untracked frontend Open Design demo files.
- Did not claim live Feishu synchronization.

## GitHub baseline sync skill for parallel development

Date: 2026-06-18

### Goal
Add a required GitHub baseline synchronization workflow so all parallel QLanalyser Online development conversations use the latest remote state and canonical architecture/version/module docs.

### Changes
- Added project skill `qlanalyser-github-baseline-sync`.
- Registered the skill in `AGENTS.md`.
- Recorded the decision in `docs/DECISIONS.md`.
- Updated `docs/AI_HANDOFF_CURRENT.md` with start/finish GitHub baseline checks.
- Updated `docs/PROJECT_STATUS.md` with the new guardrail.

### Validation
- Documentation-only change; run `git diff --check` and `python scripts/check_no_mojibake.py`.

### Boundary
- Does not automatically pull, merge, rebase, reset, overwrite, or force push.
- Does not touch existing untracked frontend Open Design demo files.

---

### Date
2026-06-18

### Task goal
Ship the first customer-facing Analysis Lab early-access iteration and make QC a live service preview instead of a static card.

### Modified files
- `backend/api/eeg_files.py`: add a file-list API for the QC Lab selector.
- `backend/main.py`: allow local frontend ports used by lab development.
- `backend/services/task_service.py`: route QC preview workflow ids to the new QC preview runner and serve SVG artifacts with the right MIME type.
- `eeg_core/preprocess/qc_preview.py`: implement preview-window extraction, preview-only filtering, SVG rendering, snapshot metadata, and output contract writing.
- `frontend/module-lab.html`: update lab metadata to customer-facing early-access positioning.
- `frontend/module-lab.js`: replace internal Open Design/demo/review copy with customer-facing free early-access copy and add the QC preview entry.
- `frontend/qc-lab.html`, `frontend/qc-lab.css`, `frontend/qc-lab.js`: add the QC Lab upload/preview/download workbench.
- `frontend/open-design-entry-demo.html`, `frontend/open-design-entry-demo.css`: keep the simplified entry demo with registered brand mark, masked neuron background, and early-access lab copy.
- `scripts/acceptance_qc_preview_service.py`: add service-level acceptance for upload, preview task, artifacts, contract, and SVG download.
- `scripts/acceptance_research_modules_static.mjs`: extend static/browser acceptance to cover the QC Lab page.
- `docs/modules/qc_design.md`: update QC design status to reflect the implemented minimal preview service.
- `docs/PROJECT_STATUS.md`: record current project status and validation.
- `docs/TASK_LOG.md`: record this task.
- `docs/AI_HANDOFF_CURRENT.md`: record the new QC Lab live preview handoff note.

### Completed
- Added a live QC preview service reachable through the existing task API.
- Added a QC Lab page for upload/selection, metadata review, preview parameters, preview-only filtering, SVG snapshots, and artifact downloads.
- Updated the Analysis Lab overview and entry copy to read as free early access to new features for research customers.
- Preserved the formal-login boundary for project management and the non-clinical research guardrail.

### Test commands

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

### Test results
- All checks passed.
- QC preview service acceptance: passed, 13 artifacts generated.
- Static/lab browser acceptance: passed, 209 checks, 6 module pages.
- Smoke V01 API: passed.
- Worker/core acceptance: passed.
- Persistence acceptance: passed.
- Full V01 acceptance: passed, 180 checks.
- Mojibake/readiness text check: passed.

### Risks
- The QC Lab is no-login but can call the backend upload/task APIs. Public deployment must use only synthetic/demo data or add an explicit access-control decision before accepting real customer files.
- Failure-path acceptance for invalid QC preview parameters is not complete yet.
- Runtime outputs under `data/` and `work/` were generated locally and must not be staged.

### Unfinished
- Add failure-path tests for invalid channels, out-of-range windows, unsupported files, and invalid filter parameters.
- Decide whether to split `qc_filter_preview` and `qc_snapshot` into dedicated runner functions or keep them as workflow aliases for `qc_waveform_preview`.
- Decide whether the customer-facing entry demo should replace the formal root after review.

### Next suggestions
1. Add QC preview failure-path tests and improve UI error messages.
2. Start the next lab module service implementation for PSD or ERP using the same input/output pattern.
3. Review deployment policy for no-login service pages before pushing this live to Aliyun.

## 2026-06-18 MNE analysis design basis

### Completed
- Reviewed the project architecture docs, module matrix, conversation sync rules, and the current MNE dependency contract.
- Consolidated multi-model MNE consultation output into `docs/modules/mne_analysis_function_design_basis.md`.
- Linked the new basis from `docs/modules/analysis_modules_design_matrix.md`.
- Recorded the new design baseline in `docs/PROJECT_STATUS.md`.

### Current baseline
- v0.1 stable targets remain QC, PSD, and event-conditioned ERP.
- TFR stays preview until baseline/frequency/decimation/statistics rules are locked.
- PAC is custom-needed and must include surrogate/null-model controls.
- Connectivity stays preview until `mne-connectivity` and risk controls are approved.

### Next
1. Draft `docs/modules/psd_design.md` from the new MNE basis.
2. Draft `docs/modules/erp_design.md` from the new MNE basis.
3. Continue expanding QC failure-path and preprocessing-preview rules.

## 2026-06-18 Customer entry value proposition copy

### Completed
- Updated `frontend/open-design-entry-demo.html` so the main value points read as no-code visual operation, traceable results, and research-grade chart delivery.
- Preserved the concise research-customer tone, the `®` brand mark, and the existing login/register/lab entry structure.
- Did not modify backend logic, EEG analysis code, authentication behavior, lab modules, or deployment configuration.

### Validation
- `git diff --check -- frontend/open-design-entry-demo.html`: passed.
- `python scripts/check_no_mojibake.py`: passed.
- Sensitive-text scan found only the password input field in the entry form and historical documentation references to secret/token risk wording; no key contents were printed or staged.

### Next
1. Review the entry page visually in the browser after the local static server refreshes.
2. Decide whether the same three customer value points should be promoted from the Open Design demo into the formal production entry page.

## 2026-06-18 PSD detailed design

### Completed
- Added `docs/modules/psd_design.md`.
- Linked PSD from `docs/modules/analysis_modules_design_matrix.md`.
- Documented current input, parameters, MNE mapping, outputs, failure modes, interpretation boundaries, acceptance standards, and next implementation tasks.

### Current baseline
- PSD is v0.1 stable under workflow id `resting_psd`.
- Current runner uses MNE Welch PSD through `Raw.compute_psd(method="welch")`.
- Current outputs include band power CSV, channel-band CSV, PSD summary JSON, reproducibility files, result, manifest, and log.

### Next
1. Implement explicit PSD parameter validation and user-readable errors.
2. Add PSD failure-path acceptance cases.
3. Add PSD visual/table rendering acceptance after validation is hardened.

## 2026-06-18 Analysis Lab feature selection guide

### Completed
- Reworked the Analysis Lab feature experience section into a concise research workflow guide.
- Replaced repeated internal checklist rows with customer-facing rows for QC, PSD, ERP, TFR, PAC, Connectivity, and overall deliverables.
- Kept the existing filter behavior for all, enabled, and preview functions.

### Validation
- `node --check frontend/module-lab.js`: passed.
- `python scripts/check_no_mojibake.py`: passed.

### Next
1. Visually review `module-lab.html` in the browser and check whether the five-column table feels too dense on laptop width.
2. If needed, convert the guide from a table into stacked decision cards for lower cognitive load.

## 2026-06-18 ERP detailed design

### Completed
- Added `docs/modules/erp_design.md`.
- Linked ERP from `docs/modules/analysis_modules_design_matrix.md`.
- Documented current event input, parameters, MNE mapping, outputs, failure modes, interpretation boundaries, acceptance standards, and next implementation tasks.

### Current baseline
- ERP is event-conditioned beta/stable under workflow id `erp_p300`.
- Current runner uses `mne.events_from_annotations`, `mne.Epochs`, condition averages, and windowed N100/P200/P300 metrics.
- ERP must fail or require review when event markers are missing or marker semantics are unclear.

### Next
1. Implement explicit ERP parameter validation and user-readable errors.
2. Add drop log / rejected epoch summaries.
3. Add event-id confirmation and ERP waveform/table rendering acceptance.

## 2026-06-18 EEG workflow information architecture

### Goal
Align the main product frame, left navigation, and no-login preview area with the actual EEG analysis workflow instead of repeating generic lab/feature/entry wording.

### Completed
- Reordered the logged-in workbench left navigation around the EEG workflow: project setup, data import, preview/preprocessing, analysis branches, statistics, figures/downloads, data assets, guide, reference, billing, and invoice.
- Rebuilt `module-lab.html` / `module-lab.js` homepage around project setup -> data import -> preview/preprocessing -> analysis branches -> statistics -> figures -> downloads.
- Updated module detail side navigation to workflow labels: data input, parameters/preprocessing, analysis method, metric outputs, figures, downloads, review, and boundaries.
- Updated research-module overview copy/status labels and the static acceptance script to match the workflow IA and no-login preview wording.

### Multi-model / review record
- GPT route via configured OpenAI-compatible endpoint: failed with HTTP 503.
- GLM route `glm-5.2`: call returned usage metadata in about 25 s, but output content file was empty; not used as evidence.
- Final decision basis: repository architecture docs, `docs/modules/mne_analysis_function_design_basis.md`, previous MNE review artifacts, and internal reverse review.

### Boundaries
- Did not change backend APIs, authentication behavior, public routes, or EEG algorithms.
- `eeg_core/analysis/erp.py` has unrelated local algorithm changes and was intentionally excluded from this UI IA task.

### Validation
- `node --check frontend/app.js frontend/module-lab.js frontend/research-modules.js scripts/acceptance_research_modules_static.mjs`: passed.
- `python scripts/check_no_mojibake.py`: passed.
- `git diff --check`: passed.
- `node scripts/acceptance_research_modules_static.mjs`: passed, 212 checks, 6 module pages.

### Next
1. Visually review the left navigation and `module-lab.html` in the browser for cognitive load.
2. If the workflow table remains dense, convert it to stacked decision cards on small screens.
3. Keep ERP algorithm changes in a separate task/commit after validation.

## 2026-06-18 Experience Center customer-facing copy

### Goal
Consolidate the customer-visible former Analysis Lab wording as `体验中心` while keeping internal files and URLs stable.

### Changes
- Updated `frontend/module-lab.js` visible labels, workflow step copy, status labels, detail buttons, and side navigation to use Experience Center project wording.
- Updated `frontend/research-modules.html` visible heading/navigation copy to remove internal research-module/testbench wording.
- Updated `scripts/acceptance_research_modules_static.mjs` so static acceptance asserts the Experience Center wording and old-status guardrails.

### Boundaries
- Did not rename `frontend/module-lab.html`, `frontend/research-modules.html`, `module-lab.html?module=...`, or `research-module/*` URLs.
- Did not change backend APIs, authentication, task runners, EEG algorithms, or the formal workbench login/register flow.
- No customer data, API keys, logs, raw EEG, or local runtime output were committed.

### Validation
- `node --check frontend/module-lab.js`: passed.
- `node scripts/acceptance_research_modules_static.mjs`: passed, 212 checks, 6 module pages.
- `python scripts/check_no_mojibake.py`: passed.

### Next
1. Visually review `module-lab.html` and `research-modules.html` after deployment for final customer tone.
2. Keep URL/file renaming out of scope until explicitly approved.
3. Continue QC/PSD/ERP service work separately from this copy-only pass.

## 2026-06-18 Experience Center copy polish

### Goal
Finish the customer-visible Experience Center wording polish by removing remaining internal terms from the reviewed frontend surfaces.

### Changes
- Updated `frontend/module-lab.js` labels from `模块结果包`, `MNE 设计`, and `分析流程加载失败` to customer-facing Experience Center wording.
- Updated `frontend/research-modules.html` action and checklist wording from `打开体验中心` / `高级方法启用前` to `进入体验中心` / `高级方法开放前`.

### Boundaries
- Did not rename `frontend/module-lab.html`, `frontend/research-modules.html`, `module-lab.html?module=...`, or `research-module/*` URLs.
- Did not change backend APIs, authentication, task runners, EEG algorithms, or formal login/register behavior.

### Validation
- `node --check frontend/module-lab.js`: passed.
- `node scripts/acceptance_research_modules_static.mjs`: passed, 212 checks, 6 module pages.
- `python scripts/check_no_mojibake.py`: passed.

### Next
1. Deploy the static frontend after commit/push if public testing should use the latest copy.
2. Continue QC/PSD/ERP service work separately from this copy-only pass.

## 2026-06-18 Login background Image2 generation

### Goal
Use Image2 to generate a neuron-firing medical teaching illustration for the login page background.

### Completed
- Read the project rules and current UI files.
- Confirmed existing login CSS already references `frontend/assets/qlanalyser-neuron-firing-bg.png`.
- Injected user-level `GPT_IMAGE_2_BASE_URL`, `GPT_IMAGE_2_API_KEY`, and `GPT_IMAGE_2_MODEL` into the active command environment.
- Verified `/v1/models` could see `gpt-image-2`.
- Generated the new PNG via `/v1/images/generations`; the response used `b64_json`.
- Replaced `frontend/assets/qlanalyser-neuron-firing-bg.png` with the generated image.
- Visually inspected the output: blue medical-style neuron network with visible firing points and dark negative space suitable for white login copy.

### Validation
- `python scripts/check_no_mojibake.py`: passed.
- `git diff --check -- frontend/assets/qlanalyser-neuron-firing-bg.png docs/PROJECT_STATUS.md docs/TASK_LOG.md`: passed.

### Notes
- Early attempts through the old process-level `OPENAI_*` route could not see image models.
- The user-level Image2 route worked after retry; transient `RemoteDisconnected` occurred before success.
- Unrelated untracked file `docs/modules/qc_common_data_preparation_requirements.md` was not modified.

## 2026-06-18 UI information noise cleanup

### Goal
Remove customer-facing information noise from the workbench and keep the page focused on the actual EEG workflow.

### Completed
- Deleted the top explanatory flow note and three-column value cards from `frontend/index.html`.
- Deleted the repeated "科研级流程" panel.
- Removed the now-unused `.boss-brief` and `.central-config-note` CSS.
- Updated the static acceptance check so the customer-facing "模块中心" naming is accepted.

### Validation
- `node --check frontend/app.js frontend/module-lab.js frontend/research-modules.js scripts/acceptance_research_modules_static.mjs`: passed.
- `node scripts/acceptance_research_modules_static.mjs`: passed, 212 checks, 6 module pages.
- `git diff --check` on changed frontend and acceptance files: passed.

### Notes
- Unrelated dirty files were left unstaged: `eeg_core/preprocess/qc_preview.py`, `backend/models/data_preparation.py`, `docs/FOUR_CONVERSATION_WORKFLOW.md`, and `docs/modules/qc_common_data_preparation_requirements.md`.

## 2026-06-18 QC/PSD common data preparation plan service

### Goal
Implement the common `data_preparation_plan` foundation used by QC and PSD before changing PSD algorithm details.

### Completed
- Added `backend/models/data_preparation.py` for plan, update, and task-reference schemas.
- Added `backend/services/data_preparation_service.py` with JSON registry persistence, artifact contract output, task reference output, and revision conflict checks.
- Added `backend/api/data_preparation.py` and registered the router in `backend/main.py`.
- Connected `backend/services/task_service.py` so QC/PSD tasks can validate `data_preparation_plan_id` and `data_preparation_revision` and register plan-reference artifacts.
- Added service/API acceptance scripts.

### Validation
- `python -m py_compile backend/models/data_preparation.py backend/services/data_preparation_service.py backend/api/data_preparation.py backend/services/task_service.py backend/main.py scripts/acceptance_data_preparation_plan.py scripts/acceptance_data_preparation_api.py`: passed.
- `python scripts/acceptance_data_preparation_plan.py`: passed.
- `python scripts/acceptance_data_preparation_api.py`: passed.
- Confirmed `eeg_core/analysis/psd.py` has no diff.

### Notes
- This pass intentionally does not change PSD algorithm internals.
- Existing unrelated dirty frontend/QC files were not part of this service implementation.

## 2026-06-19 C0 customer Pilot flow cleanup checkpoint

### Goal
Make the customer-visible Pilot path coherent and verifiable before handing the UI to C4/C5 for independent review.

### Changes
- Cleaned `frontend/index.html` customer entry/workbench copy around project, data import, data preparation, analysis, result review, and delivery download.
- Hid secondary module-center and operations entries from the default login page while preserving internal routes/selectors for controlled use.
- Synchronized `frontend/expert-entry-demo.html` with the cleaned default entry so old entry URLs do not show stale Pilot/demo/admin copy.
- Replaced missing `customer_oddball_case` images/downloads with existing assets under `frontend/assets`.
- Updated `frontend/app.js` dynamic labels and messages away from local/demo/sandbox/backend wording.
- Updated `scripts/acceptance_v01_ui.mjs` to use `?pilot=1`, enforce customer-visible copy denylist, hide visible operations nav for customer role, and fail on non-API asset/navigation 4xx responses.
- Updated `scripts/acceptance_research_modules_static.mjs` so customer entry checks assert hidden secondary/operations entries and customer copy cleanliness.
- Fixed two historical mojibake placeholders in this task log so `scripts/check_no_mojibake.py` passes.

### Validation
- `git fetch origin --prune`: passed before UI edits.
- `node --check frontend/app.js`: passed.
- `node --check scripts/acceptance_v01_ui.mjs`: passed.
- `node --check scripts/acceptance_research_modules_static.mjs`: passed.
- `python scripts/check_no_mojibake.py`: passed.
- `node scripts/acceptance_research_modules_static.mjs`: passed, 217 checks, 6 pages.
- `python scripts/acceptance_data_preparation_plan.py`: passed.
- `python scripts/acceptance_data_preparation_api.py`: passed.
- `python scripts/acceptance_psd_p0.py`: passed.
- `python scripts/acceptance_qc_preview_service.py`: passed, 13 artifacts, 64 channels checked.
- `python scripts/acceptance_v01_full.py`: passed, 191 checks.
- `python scripts/smoke_v01_api.py`: passed.
- `node scripts/acceptance_v01_ui.mjs`: passed against local backend/frontend; project creation, upload guard, valid upload, QC, PSD, ERP, and report creation all returned expected results.

### Changed-file ownership map
- C0 current checkpoint: `frontend/index.html`, `frontend/expert-entry-demo.html`, `frontend/app.js`, `scripts/acceptance_v01_ui.mjs`, `scripts/acceptance_research_modules_static.mjs`, `docs/PROJECT_STATUS.md`, `docs/TASK_LOG.md`.
- Prior/shared backend chain residue: `backend/services/task_service.py`, `scripts/acceptance_data_preparation_plan.py`, `scripts/acceptance_psd_p0.py`, `eeg_core/analysis/psd.py`.
- C2/QC residue: `eeg_core/preprocess/qc_preview.py`, `frontend/qc-lab.html`, `frontend/qc-lab.js`, `frontend/qc-lab.css`, `scripts/acceptance_qc_preview_service.py`.
- Other UI residue: `frontend/styles.css`.
- Governance/team residue: `.agents/skills/qlanalyser-*`, `docs/TEAM_OPERATING_MODEL.md`, `docs/FOUR_CONVERSATION_WORKFLOW.md`, `docs/modules/qc_common_data_preparation_requirements.md`.

### Risks
- Worktree remains mixed; do not use `git add .`.
- `main` is still locally ahead of `origin/main`; do not push until C0 separates scopes and confirms release baseline.
- C4 still needs browser/screenshot acceptance from the user-flow perspective.
- C5 still needs final release-gate review before any commit/push.

### Next
1. Send C4 a checkpoint for independent customer-flow review.
2. Send C5 a checkpoint for release-gate and owner-boundary review.
3. Freeze the current shared data-preparation plan contract with C1 after C4/C5 feedback.

## 2026-06-22 Reference / CSD beta runnable module

### Goal
Turn Reference / CSD from a disabled preview card into one standalone, QLanalyser-integrable analysis module with backend runner, task routing, frontend controls, validation, and evidence.

### Changes
- Added `eeg_core/analysis/reference_csd.py` with parameter validation, average/specific/bipolar/CSD modes, bad-channel and bad-segment handling, before/after SVG previews, CSV tables, reproducibility sidecars, `result.json`, `manifest.json`, and boundary text.
- Enabled `reference_csd` in `backend/services/task_service.py` through the same `/api/tasks` path used by runnable modules.
- Extended data-preparation module scope and quota estimate support for `reference_csd`.
- Added demo support for `reference_csd` in `backend/services/lab_demo_service.py` and `/lab/demo/run-all`.
- Promoted CSD in `frontend/module-lab.js` from preview-only to a runnable beta card with reference mode, reference channels, preview window, preview channels, and CSD advanced fields.
- Added `scripts/acceptance_reference_csd_module.py` for runner + task-service acceptance.
- Updated live UI runner and preview selector acceptance so CSD is runnable while TFR/PAC/Connectivity remain preview.

### Validation
- `python -m py_compile eeg_core\analysis\reference_csd.py backend\services\task_service.py backend\models\data_preparation.py backend\services\lab_demo_service.py scripts\acceptance_reference_csd_module.py scripts\acceptance_module_lab_preview_selectors.py scripts\acceptance_module_contract_registry.py`: passed.
- `node --check frontend\module-lab.js`: passed.
- `node --check scripts\acceptance_module_lab_live_runner.mjs`: passed.
- `python scripts\acceptance_reference_csd_module.py`: passed; produced a completed `reference_csd` task and 20 artifacts.
- `python scripts\acceptance_module_contract_registry.py`: passed.
- `python scripts\acceptance_module_lab_preview_selectors.py`: passed.
- `node scripts\acceptance_module_lab_live_runner.mjs`: passed after restarting local backend 8001; UI-only flow uploaded EEG and completed QC, PSD, ERP, and Reference/CSD tasks.

### Evidence
- `work/release_evidence/20260622-reference-csd-module/acceptance_reference_csd_module.json`
- `work/release_evidence/20260620-module-lab-live-runner/module_lab_live_runner.json`
- `work/release_evidence/module_lab_preview_selectors/acceptance_module_lab_preview_selectors.json`

### Notes
- Local backend 8001 had to be restarted because the old process still rejected `reference_csd` as disabled.
- Full-repo `python scripts/check_no_mojibake.py` still fails on pre-existing `frontend/app.js` and `frontend/index.html` replacement-marker text; targeted scan on CSD-touched files did not find replacement markers or common mojibake strings.
- Worktree remains mixed with unrelated existing changes. Do not use `git add .`.

## 2026-06-22 Connectivity beta runnable module

### Goal
Turn Connectivity from a preview-only method into one standalone, QLanalyser-integrable beta analysis module with backend runner, task routing, frontend controls, validation, and evidence.

### Changes
- Replaced the preview stub in `eeg_core/analysis/connectivity.py` with a real sensor-space beta runner.
- Enabled `connectivity` in `backend/services/task_service.py` through the shared `/api/tasks` path.
- Added demo/quota/contract support through `backend/services/lab_demo_service.py`, `backend/api/lab_demo.py`, and `backend/services/quota_service.py`.
- Promoted Connectivity in `frontend/module-lab.js` from preview-only to a runnable beta card with method, frequency band, time window, channel selection, edge threshold, and max-edge fields.
- Added `scripts/acceptance_connectivity_module.py` for runner + task-service acceptance.
- Updated live UI runner, preview selector, and contract registry acceptance so Connectivity is runnable after QC, PSD, ERP, and Reference/CSD.

### Validation
- `python -m py_compile eeg_core\analysis\connectivity.py backend\services\task_service.py backend\services\lab_demo_service.py scripts\acceptance_connectivity_module.py scripts\acceptance_module_lab_preview_selectors.py scripts\acceptance_module_contract_registry.py`: passed.
- `node --check frontend\module-lab.js`: passed.
- `node --check scripts\acceptance_module_lab_live_runner.mjs`: passed.
- `python scripts\acceptance_connectivity_module.py`: passed; produced a completed `connectivity` task and 18 artifacts.
- `python scripts\acceptance_module_contract_registry.py`: passed.
- `python scripts\acceptance_module_lab_preview_selectors.py`: passed.
- `node scripts\acceptance_module_lab_live_runner.mjs`: passed after restarting local backend 8001; UI-only flow uploaded EEG and completed QC, PSD, ERP, Reference/CSD, and Connectivity tasks.

### Evidence
- `work/release_evidence/20260622-connectivity-module/acceptance_connectivity_module.json`
- `work/release_evidence/20260620-module-lab-live-runner/module_lab_live_runner.json`
- `work/release_evidence/module_lab_preview_selectors/acceptance_module_lab_preview_selectors.json`

### Notes
- Connectivity scope is sensor-space, single-record, beta only. It must not be described as causality, source localization, diagnosis, brain-region communication, group statistics, or significance testing.
- Full-repo `python scripts/check_no_mojibake.py` remains blocked by pre-existing replacement-marker text outside this slice; targeted scan on connectivity-touched files passed.
- Worktree remains mixed with unrelated existing changes. Do not use `git add .`.

## 2026-06-22 PAC / CFC beta runnable module

### Goal
Turn PAC / CFC from a preview-only method into one standalone, QLanalyser-integrable beta analysis module with backend runner, task routing, frontend controls, validation, and evidence.

### Changes
- Added `eeg_core/analysis/pac.py` with parameter validation, MNE filtering, Hilbert phase/envelope extraction, Tort-style MI calculation, phase-bin table, comodulogram table, dynamic curve table, summary table, SVG figures, reproducibility sidecars, `result.json`, `manifest.json`, and boundary text.
- Enabled `pac` in `backend/services/task_service.py` through the shared `/api/tasks` path while keeping the module lifecycle as beta.
- Added demo/quota support through `backend/services/lab_demo_service.py` and `backend/services/quota_service.py`.
- Promoted PAC in `frontend/module-lab.js` from preview-only to a runnable beta card with channels, phase grid, amplitude grid, bin count, time window, dynamic window, and bad-channel fields.
- Added `scripts/acceptance_pac_module.py` for runner + task-service acceptance.
- Updated live UI runner, preview selector, and contract registry acceptance so PAC is runnable after QC, PSD, and ERP and before Reference/CSD and Connectivity.

### Validation
- `python -m py_compile eeg_core\analysis\pac.py backend\services\task_service.py backend\services\lab_demo_service.py backend\services\quota_service.py scripts\acceptance_pac_module.py scripts\acceptance_module_lab_preview_selectors.py scripts\acceptance_module_contract_registry.py`: passed.
- `node --check frontend\module-lab.js`: passed.
- `node --check scripts\acceptance_module_lab_live_runner.mjs`: passed.
- `python scripts\acceptance_pac_module.py`: passed; produced a completed `pac` task and 23 artifacts.
- `python scripts\validate_pac_beta_artifacts.py work\release_evidence\20260622-pac-module\runner_output --out work\release_evidence\20260622-pac-module\pac_runner_validator.json`: passed.
- `python scripts\acceptance_module_contract_registry.py`: passed.
- `python scripts\acceptance_module_lab_preview_selectors.py`: passed.
- `node scripts\acceptance_module_lab_live_runner.mjs`: passed after restarting local backend 8001; UI-only flow uploaded EEG and completed QC, PSD, ERP, PAC, Reference/CSD, and Connectivity tasks.

### Evidence
- `work/release_evidence/20260622-pac-module/acceptance_pac_module.json`
- `work/release_evidence/20260622-pac-module/pac_runner_validator.json`
- `work/release_evidence/20260620-module-lab-live-runner/module_lab_live_runner.json`
- `work/release_evidence/module_lab_preview_selectors/acceptance_module_lab_preview_selectors.json`

### Debug notes
- First browser run hit the old backend process and failed with `pac is not enabled in V01`; root cause was stale uvicorn, fixed by stopping the exact listener PID and restarting 8001.
- Second browser run failed because amplitude centers `70,90,110 Hz` exceeded Nyquist for the 200 Hz UI fixture; UI defaults were lowered to `30,50,70 Hz`.
- Third browser run failed because the `0-20 s` window exceeded the short UI fixture duration; UI defaults were shortened to `0-8 s` with a 4 s dynamic window and 2 s step.

### Notes
- PAC scope is single-record, sensor-space, beta only. It must not be described as p-value/significance, diagnosis, group comparison, causality, brain-region communication, or source localization.
- Worktree remains mixed with unrelated existing changes. Do not use `git add .`.

## 2026-06-22 PAC beta bundle checkpoint

### Goal
Turn the PAC beta UI path into a reusable platform asset with a real downloadable ZIP bundle and a formal checkpoint record.

### Changes
- Added a PAC beta UI bundle checkpoint record at `work/release_evidence/checkpoints/2026-06-22-0805-pac-beta-ui-bundle-checkpoint.md`.
- Added the matching JSON packet at `work/release_evidence/checkpoints/2026-06-22-0805-pac-beta-ui-bundle-checkpoint.json`.
- Updated the checkpoint asset manifest and state snapshot so the new PAC checkpoint is indexed with the existing formal packet set.

### Validation
- `python scripts/acceptance_pac_module.py`: passed.
- `python scripts/acceptance_pac_beta_contract.py`: passed.
- `node scripts/virtual_reviewer_pac_beta_ui_only_runner.mjs`: passed.
- `python work\release_evidence\checkpoints\validate_checkpoints_directory_consistency.py`: to be rerun after the checkpoint index refresh.

### Evidence
- `work/release_evidence/checkpoints/2026-06-22-0805-pac-beta-ui-bundle-checkpoint.md`
- `work/release_evidence/checkpoints/2026-06-22-0805-pac-beta-ui-bundle-checkpoint.json`
- `work/release_evidence/pac_beta/pac_beta_artifact_bundle.zip`
- `work/release_evidence/pac_beta/pac-beta-ui-only-runner-evidence.json`

### Notes
- This is a product-platform checkpoint for PAC bundle delivery, not a PAC stable-promotion claim.
- Keep the bundle contract aligned if future PAC outputs change.
- Do not use `git add .`.

## 2026-06-22 Project CRUD persistence and EDF-to-results review checkpoint

### Goal
Close one user-visible product slice: project edit/archive must persist through backend routes, guarded destructive actions must remain explicit, and the review path must be able to enter with a demo account and complete a synthetic EDF-to-results flow.

### Changes
- Added project update and archive persistence service paths in `backend/services/storage_service.py`.
- Added `PATCH /api/projects/{project_id}` and `POST /api/projects/{project_id}/archive` in `backend/api/projects.py`.
- Added `ProjectUpdate` in `backend/models/project.py`.
- Updated `frontend/app.js` so project edit/archive call the backend and record persistence evidence; delete remains guarded.
- Updated `scripts/acceptance_multirole_click_review_5rounds.mjs` to assert `backend_patch`, `backend_archive`, and `not_mutated` UI audit contracts.
- Wrote a review checkpoint with fixed access, demo account, permission scope, and credential safety.

### Validation
- `python -m py_compile backend\models\project.py backend\services\storage_service.py backend\api\projects.py`: passed.
- `node --check frontend\app.js scripts\acceptance_multirole_click_review_5rounds.mjs`: passed.
- `python scripts\check_no_mojibake.py frontend\app.js frontend\index.html backend\models\project.py backend\services\storage_service.py backend\api\projects.py scripts\acceptance_multirole_click_review_5rounds.mjs`: passed.
- Refreshed backend 8001 and frontend 4174; health and frontend HTTP checks passed.
- Backend route smoke after restart passed for create, patch, and archive.
- `node scripts\acceptance_customer_login_demo.mjs`: passed.
- `python scripts\acceptance_project_data_preparation_ia.py`: passed.
- `node scripts\acceptance_multirole_click_review_5rounds.mjs`: passed with no blocking findings.
- `node scripts\acceptance_edf_upload_to_results_ui_only.mjs`: passed from synthetic EDF upload through QC, preparation, epoch set, PSD, ERP, TFR, PAC, and report ZIP.
- `python scripts\acceptance_professional_chinese_gate.py`: passed.
- `python scripts\acceptance_mainline_eeg_contract_mapping_consumption.py`: passed.
- `python scripts\acceptance_round006_tfr_real_report_consumption.py`: passed.
- `python scripts\acceptance_round006_pac_real_report_consumption.py`: passed.
- `python scripts\validate_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0750-project-crud-persistence-edf-results-checkpoint.json`: passed.
- `python scripts\acceptance_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0750-project-crud-persistence-edf-results-checkpoint.json`: passed.

### Evidence
- `work/release_evidence/checkpoints/2026-06-22-0750-project-crud-persistence-edf-results-checkpoint.md`
- `work/release_evidence/checkpoints/2026-06-22-0750-project-crud-persistence-edf-results-checkpoint.json`
- `work/release_evidence/multirole_click_review_5rounds/multirole_click_review_5rounds.json`
- `work/release_evidence/edf_upload_to_results_ui_only/edf_upload_to_results_ui_only.json`
- `work/release_evidence/edf_upload_to_results_ui_only/report_a69280766dc6.zip`

### Notes
- Feishu owner notice was sent for this checkpoint.
- This is a review checkpoint, not a full release pass.
- PAC and TFR remain beta/descriptive single-record outputs.
- Worktree remains mixed with unrelated existing changes. Do not use `git add .`.

## 2026-06-22 Report delivery page visible UI checkpoint

### Goal
Close the report-delivery usability gap: after users generate a report, the report download page must visibly show the generated report and ZIP action; before report generation, it must show a clear next step instead of an empty panel.

### Changes
- Replaced a mojibake dynamic report-delivery block in `frontend/app.js` with UTF-8-safe labels.
- Added a report-delivery empty state that guides the user back to data preparation or report generation.
- Re-rendered delivery state during view changes so the report page reflects current task/report state.
- Updated `scripts/acceptance_multirole_click_review_5rounds.mjs` so the report download view is exercised through the visible nav item.
- Updated `scripts/acceptance_edf_upload_to_results_ui_only.mjs` to record `deliveryState` and require the generated report id plus ZIP action on the delivery page.

### Validation
- `node --check frontend\app.js scripts\acceptance_multirole_click_review_5rounds.mjs scripts\acceptance_edf_upload_to_results_ui_only.mjs`: passed.
- `python scripts\check_no_mojibake.py frontend\app.js frontend\index.html scripts\acceptance_multirole_click_review_5rounds.mjs scripts\acceptance_edf_upload_to_results_ui_only.mjs work\release_evidence\edf_upload_to_results_ui_only\edf_upload_to_results_ui_only.json work\release_evidence\multirole_click_review_5rounds\multirole_click_review_5rounds.json`: passed.
- `node scripts\acceptance_multirole_click_review_5rounds.mjs`: passed.
- `python scripts\acceptance_pac_module.py`: passed.
- `node scripts\acceptance_customer_login_demo.mjs`: passed.
- `node scripts\acceptance_edf_upload_to_results_ui_only.mjs`: passed on rerun; generated `report_d5e669acfd33` and downloaded `report_d5e669acfd33.zip`.
- `python scripts\acceptance_professional_chinese_gate.py`: passed.
- `python scripts\acceptance_mainline_eeg_contract_mapping_consumption.py`: passed.
- `python scripts\acceptance_round006_tfr_real_report_consumption.py`: passed.
- `python scripts\acceptance_round006_pac_real_report_consumption.py`: passed.
- `python scripts\validate_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0806-report-delivery-visible-edf-results-checkpoint.json`: passed.
- `python scripts\acceptance_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0806-report-delivery-visible-edf-results-checkpoint.json`: passed.

### Evidence
- `work/release_evidence/checkpoints/2026-06-22-0806-report-delivery-visible-edf-results-checkpoint.md`
- `work/release_evidence/checkpoints/2026-06-22-0806-report-delivery-visible-edf-results-checkpoint.json`
- `work/release_evidence/edf_upload_to_results_ui_only/edf_upload_to_results_ui_only.json`
- `work/release_evidence/edf_upload_to_results_ui_only/report_d5e669acfd33.zip`
- `work/release_evidence/multirole_click_review_5rounds/multirole_click_review_5rounds.json`

### Debug notes
- First EDF rerun after the UI change failed during PAC with a temporary `ERR_CONNECTION_REFUSED` / `Failed to fetch`; backend PID changed during that window.
- PAC module acceptance passed immediately afterward, and the second full EDF UI-only rerun passed. Treat this as a transient local service interruption unless it recurs.

### Notes
- Feishu owner notice should include the review link and demo account for this checkpoint.
- This is a review checkpoint, not a full release pass.
- Worktree remains mixed with unrelated existing changes. Do not use `git add .`.

## 2026-06-22 EDF chain backend health stability checkpoint

### Goal
Turn the latest EDF upload-to-results product path into a stability-observable chain: upload synthetic EDF, run preparation, save epoch set, run PSD/ERP/TFR/PAC, view results, generate/download report ZIP, and prove the backend process stays healthy across the long UI-only run.

### Changes
- Added process identity and uptime fields to `/api/health` in `backend/api/health.py`.
- Updated `scripts/acceptance_edf_upload_to_results_ui_only.mjs` to sample backend health throughout the UI-only chain.
- Added runner checks for `backendHealthSamplesOk`, `backendProcessStable`, and `backendProcessIdsObserved`.
- Wrote a review-ready checkpoint with demo account, password/login method, permission scope, and credential safety.

### Validation
- `python -m py_compile backend\api\health.py`: passed.
- `node --check scripts\acceptance_edf_upload_to_results_ui_only.mjs`: passed.
- `python scripts\check_no_mojibake.py backend\api\health.py scripts\acceptance_edf_upload_to_results_ui_only.mjs`: passed.
- `node scripts\acceptance_customer_login_demo.mjs`: passed.
- `node scripts\acceptance_multirole_click_review_5rounds.mjs`: passed.
- `node scripts\acceptance_edf_upload_to_results_ui_only.mjs`: passed; report `report_2fdf3d048d26`, report ZIP `work\release_evidence\edf_upload_to_results_ui_only\report_2fdf3d048d26.zip`.
- Health evidence: all samples ok, `backendProcessIdsObserved=[37620]`, `backendProcessStable=true`.
- `python scripts\acceptance_professional_chinese_gate.py`: passed.
- `python scripts\acceptance_mainline_eeg_contract_mapping_consumption.py`: passed.
- `python scripts\acceptance_round006_tfr_real_report_consumption.py`: passed.
- `python scripts\acceptance_round006_pac_real_report_consumption.py`: passed.
- `python scripts\validate_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0818-edf-chain-backend-health-stability-checkpoint.json`: passed.
- `python scripts\acceptance_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0818-edf-chain-backend-health-stability-checkpoint.json`: passed.
- `python scripts\check_no_mojibake.py work\release_evidence\checkpoints\2026-06-22-0818-edf-chain-backend-health-stability-checkpoint.md work\release_evidence\checkpoints\2026-06-22-0818-edf-chain-backend-health-stability-checkpoint.json work\release_evidence\edf_upload_to_results_ui_only\edf_upload_to_results_ui_only.json work\release_evidence\multirole_click_review_5rounds\multirole_click_review_5rounds.json`: passed.

### Evidence
- `work/release_evidence/checkpoints/2026-06-22-0818-edf-chain-backend-health-stability-checkpoint.md`
- `work/release_evidence/checkpoints/2026-06-22-0818-edf-chain-backend-health-stability-checkpoint.json`
- `work/release_evidence/edf_upload_to_results_ui_only/edf_upload_to_results_ui_only.json`
- `work/release_evidence/edf_upload_to_results_ui_only/report_2fdf3d048d26.zip`
- `work/release_evidence/multirole_click_review_5rounds/multirole_click_review_5rounds.json`

### Notes
- This is review-ready checkpoint evidence, not a full release pass.
- PAC and TFR remain beta/descriptive single-record outputs.
- Review access is validated and includes the fixed demo account: `demo.customer@quanlan.cn` / `demo123456`.
- Worktree remains mixed with unrelated existing changes. Do not use `git add .`.

## 2026-06-22 OCR-first PDF artifact QA checkpoint

### Goal
Close one report-delivery quality gate: generated report PDFs must be rendered page-by-page, parsed through OCR as the primary artifact QA path, cross-checked with native text-layer audit, and consumed by the release evidence chain without claiming full release readiness.

### Changes
- Executed the OCR-first PDF artifact QA gate against the latest EDF UI-only report ZIP.
- Generated page images under `work\release_evidence\pdf_ocr_artifact_qa\pages`.
- Wrote the machine-readable PDF QA result to `work\release_evidence\pdf_ocr_artifact_qa\pdf_ocr_artifact_qa.json`.
- Refreshed production goal matrix, release gate summary, and release evidence manifest so they consume `pdf_ocr_artifact_qa`.
- Wrote a review-ready checkpoint with fixed demo access and credential-safety fields.

### Validation
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

### Evidence
- `work/release_evidence/checkpoints/2026-06-22-0824-pdf-ocr-artifact-qa-checkpoint.md`
- `work/release_evidence/checkpoints/2026-06-22-0824-pdf-ocr-artifact-qa-checkpoint.json`
- `work/release_evidence/pdf_ocr_artifact_qa/pdf_ocr_artifact_qa.json`
- `work/release_evidence/pdf_ocr_artifact_qa/pages/page_001.png`
- `work/release_evidence/pdf_ocr_artifact_qa/pages/page_002.png`
- `work/release_evidence/20260620-v01-acceptance/production_goal_requirement_matrix.json`
- `work/release_evidence/20260620-v01-acceptance/release_gate_summary.json`
- `work/release_evidence/20260620-v01-acceptance/evidence_manifest.json`

### Notes
- This is PDF artifact QA evidence, not a full release pass.
- Native text-layer parsing remains an auxiliary audit path for exact parameters, units, versions, and timestamps.
- Review access is validated and includes the fixed demo account: `demo.customer@quanlan.cn` / `demo123456`.
- Worktree remains mixed with unrelated existing changes. Do not use `git add .`.

## 2026-06-22 Login feedback, UTF-8 UI, and EDF-to-report checkpoint

### Goal
Ship one reviewable product slice: users can open the local review entry, get feedback if login fields are empty, log in with the default demo account, upload the synthetic EDF, run the main EEG chain, download a report ZIP, and have that exact ZIP pass inline OCR-first PDF QA.

### Changes
- Scoped `frontend/app.js` so it no longer collides with the legacy inline script globals in `frontend/index.html`.
- Added a clean visible-copy pass for the login/workbench surfaces affected by old mojibake.
- Kept the default review account flow at `demo.customer@quanlan.cn` / `demo123456`.
- Switched login/register/admin feedback messages to clear Chinese UI text.
- Wrote a review-ready checkpoint with REVIEW_ACCESS, credential safety, and validator pass.

### Validation
- Browser empty-login check: passed; message `请先输入邮箱/手机号和密码，再点击登录。`.
- Browser demo-login check: passed; reached `项目工作台` as `客户账户`; visible bad-marker scan empty.
- `node --check frontend\app.js`: passed.
- `python scripts\check_no_mojibake.py frontend\app.js frontend\index.html`: passed.
- `node scripts\acceptance_edf_upload_to_results_ui_only.mjs`: passed; report ZIP `work\release_evidence\edf_upload_to_results_ui_only\report_8d4a83bd4ae3.zip`.
- `python scripts\acceptance_psd_real_report_consumption.py`: passed.
- `python scripts\acceptance_qc_real_report_consumption.py`: passed.
- `python scripts\acceptance_round006_tfr_real_report_consumption.py`: passed.
- `python scripts\acceptance_round006_pac_real_report_consumption.py`: passed.
- `python scripts\acceptance_round008_erp_real_report_consumption.py`: passed.
- `python scripts\acceptance_mainline_eeg_contract_mapping_consumption.py`: passed.
- `python scripts\run_release_review_gate.py`: passed; failed steps empty.
- `python scripts\acceptance_production_goal_matrix.py`: passed with external boundaries.
- `python scripts\acceptance_release_gate_summary.py`: passed; release status remains `blocked_external_inputs`.
- `python scripts\acceptance_release_manifest_consistency.py`: passed.
- `python scripts\acceptance_release_no_misclaim.py`: passed.
- `python scripts\validate_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0856-edf-ui-login-mojibake-inline-pdf-ocr-checkpoint.json`: passed.
- `python scripts\acceptance_checkpoint_packet_access.py work\release_evidence\checkpoints\2026-06-22-0856-edf-ui-login-mojibake-inline-pdf-ocr-checkpoint.json`: passed.
- `python scripts\check_no_mojibake.py frontend\app.js frontend\index.html work\release_evidence\edf_upload_to_results_ui_only\edf_upload_to_results_ui_only.json work\release_evidence\pdf_ocr_artifact_qa\pdf_ocr_artifact_qa.json`: passed.

### Evidence
- `work/release_evidence/checkpoints/2026-06-22-0856-edf-ui-login-mojibake-inline-pdf-ocr-checkpoint.md`
- `work/release_evidence/checkpoints/2026-06-22-0856-edf-ui-login-mojibake-inline-pdf-ocr-checkpoint.json`
- `work/release_evidence/edf_upload_to_results_ui_only/edf_upload_to_results_ui_only.json`
- `work/release_evidence/edf_upload_to_results_ui_only/report_8d4a83bd4ae3.zip`
- `work/release_evidence/pdf_ocr_artifact_qa/pdf_ocr_artifact_qa.json`
- `work/release_evidence/20260620-v01-acceptance/release_gate_summary.json`

### Notes
- This checkpoint is review-ready, not a full release pass.
- PAC/TFR remain beta and descriptive only.
- DeepSeek language draft was skipped for this urgent functional UI fix because no DeepSeek callable route is available in this thread; wording is minimal factual UI feedback and remains subject to the professional Chinese gate.

## 2026-06-22 08 replacement entry: 07-consumable module evidence gate repair

### Goal
Take over the broken 08 research-room lane and deliver a real 07-consumable runner/checker/evidence result instead of a knowledge-only summary.

### Changes
- Updated `scripts/build_release_gate_summary.py` so the Markdown release summary exposes the P0 gap-repair contract evidence path already present in the summary JSON.
- Refreshed module-lab live P0 evidence, production goal matrix, release summary, and release review gate outputs.

### Validation
- `python -m py_compile scripts\build_release_gate_summary.py scripts\acceptance_release_gate_summary.py`: passed.
- `python scripts\check_no_mojibake.py scripts\build_release_gate_summary.py scripts\acceptance_release_gate_summary.py`: passed.
- `python scripts\acceptance_mainline_eeg_contract_mapping_consumption.py`: passed.
- `python scripts\acceptance_psd_real_report_consumption.py`: passed.
- `node scripts\acceptance_module_lab_live_runner.mjs`: P0 QC/PSD/ERP customer-file evidence present; advanced module timeout remains outside this P0 row.
- `python scripts\acceptance_production_goal_matrix.py`: passed with external boundaries.
- `python scripts\build_release_gate_summary.py`: passed, release status `blocked_external_inputs`.
- `python scripts\acceptance_release_gate_summary.py`: passed.
- `python scripts\run_release_review_gate.py`: passed, 33 steps, failed steps empty.

### Evidence
- `work\release_evidence\20260620-module-lab-live-runner\module_lab_live_runner.json`
- `work\release_evidence\20260620-v01-acceptance\production_goal_requirement_matrix.json`
- `work\release_evidence\20260620-v01-acceptance\release_gate_summary.json`
- `work\release_evidence\20260620-v01-acceptance\release_gate_summary.md`
- `work\release_evidence\20260620-v01-acceptance\release_review_gate_run.json`

### Notes
- Release readiness remains blocked by external provider/cloud inputs.
- why_not_mini: takeover, intent parsing, evidence-chain repair, and final acceptance belong to GPT-5.5/Codex; deterministic checks were handled by scripts.

## 2026-06-22 Service 07 replacement entry - module-lab all beta runner evidence

### Goal
Continue the QLanalyser module-support mainline with real runnable module evidence, not learning cards or summaries. Close a 07-consumable beta module checkpoint covering backend runner evidence, `/api/tasks`, module-lab UI submission, parameter validation, and visual evidence.

### Findings / root cause
- `connectivity` specialty acceptance passed immediately: backend runner, parameter rejection, task-service `/api/tasks` path, and artifact registration produced 18 artifacts.
- The first `module-lab` all-module UI run failed at `multitaper_psd_tfr` because the running local backend on port 8001 was still an older uvicorn process that did not include the current `multitaper_psd_tfr` task-service branch.
- Restarting only the local development backend aligned runtime behavior with the current source. No production service, push, deploy, or destructive repo operation was performed.

### Validation
- `python -m py_compile eeg_core\analysis\connectivity.py backend\services\task_service.py scripts\acceptance_connectivity_module.py`: passed.
- `node --check frontend\module-lab.js scripts\acceptance_module_lab_live_runner.mjs`: passed.
- `python scripts\acceptance_connectivity_module.py`: passed; `task_27d274bedfc0`, 18 artifacts.
- Local backend 8001 health after restart: passed; process changed to current-source uvicorn.
- `python scripts\acceptance_multitaper_psd_tfr_module.py`: passed; `task_1e63744a9dca`, 22 artifacts.
- `QLANALYSER_MODULE_LAB_SCOPE=all node scripts\acceptance_module_lab_live_runner.mjs`: passed; one uploaded customer file created 8 real `/api/tasks` and all 8 module cards returned downloadable artifacts.
- `python scripts\check_no_mojibake.py frontend\module-lab.js frontend\module-lab.html frontend\module-lab.css work\release_evidence\20260620-module-lab-live-runner\module_lab_live_runner.json work\release_evidence\20260622-connectivity-module\acceptance_connectivity_module.json work\release_evidence\20260622-multitaper-psd-tfr-module\acceptance_multitaper_psd_tfr_module.json`: passed.

### Evidence
- `work\release_evidence\20260622-connectivity-module\acceptance_connectivity_module.json`
- `work\release_evidence\20260622-connectivity-module\runner_output`
- `work\release_evidence\20260622-multitaper-psd-tfr-module\acceptance_multitaper_psd_tfr_module.json`
- `work\release_evidence\20260622-multitaper-psd-tfr-module\runner_output`
- `work\release_evidence\20260620-module-lab-live-runner\module_lab_live_runner.json`
- `work\release_evidence\20260620-module-lab-live-runner\module_lab_live_runner_all.png`

### UI review note
- Code-level UI sources checked: `frontend/module-lab.js`, `frontend/module-lab.html`, `frontend/module-lab.css`, plus `UI_INTERACTION_REVIEW_GATE_20260622.md`, `CODE_REVIEWABLE_UI_UX_KNOWLEDGE_STANDARD_20260622.md`, `UX_STATE_FEEDBACK_EMPTY_ERROR_LOADING_MOTION_GATE_CN.md`, and `QLANALYSER_DASHBOARD_DESIGN_SYSTEM_FIT_MATRIX_CN.md`.
- Visual evidence checked: `module_lab_live_runner_all.png`.
- UI verdict: conditional evidence pass for module integration and artifact visibility only. This is not a final polished UI pass; module-lab remains dense, parameter-heavy, and beta-lab oriented. Missing state coverage for narrow viewport, explicit error recovery screenshots, keyboard/focus path, and long-task progress detail prevents a final UI review pass under the 2026-06-22 gate.

### Notes
- Connectivity, PAC, TFR, Reference/CSD, and Multitaper remain beta/descriptive single-record research modules unless separately promoted.
- This checkpoint is local module integration evidence, not release readiness.
- Worktree remains mixed with unrelated existing changes. Do not use `git add .`, do not push, and do not deploy from this state without an explicit owner split/review.
- why_not_mini: takeover, UI verdict, root-cause interpretation, and final acceptance are GPT-5.5/Codex-owned. Scripts supplied mechanical evidence only.

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



## 2026-06-23 Module Lab review-system UI repair and retest

Task goal:

- Continue the review-system test -> guidance -> optimization -> retest loop until the Module Lab release-review UI surface meets publish-standard evidence for visible copy, recoverable error state, responsive layout, keyboard path, and deterministic validators.

Changed files:

- `frontend/module-lab.js`: replaced remaining mojibake-prone hero, boundary, status-label, upload-success, missing-file, and preview-card strings with readable ASCII-safe English.
- `frontend/module-lab.css`: changed `.empty` into a small grid and added `.empty strong` / `.empty span` rules so load-error title, error detail, and recovery guidance are visually separated.
- `docs/PROJECT_STATUS.md` and `docs/TASK_LOG.md`: recorded current evidence and residual release-gate boundary.

Validation:

```powershell
node --check frontend\module-lab.js
python scripts\check_no_mojibake.py frontend\module-lab.js frontend\module-lab.html frontend\module-lab.css
rg -n "Failed to fetch|\\u4e|\\u7|mojibake-marker" frontend/module-lab.js frontend/module-lab.html frontend/module-lab.css
node C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_ui_gate_capture_20260623.mjs
node --check scripts\acceptance_module_lab_live_runner.mjs
python scripts\run_release_review_gate.py
```

Results:

- JS syntax: passed.
- Mojibake/readiness text check for `frontend/module-lab.js`, `frontend/module-lab.html`, and `frontend/module-lab.css`: passed.
- Targeted broken-text/readback scan: `rg -n "Failed to fetch|\\u4e|\\u7|mojibake-marker" frontend/module-lab.js frontend/module-lab.html frontend/module-lab.css` returned no matches.
- UI gate JSON: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_ui_gate_20260623\module_lab_ui_gate_20260623.json` with `hasP0BetaPreviewOnNarrow=true`, `narrowSingleColumn=true`, `keyboardHasVisiblePath=true`, and `loadErrorVisible=true`.
- Fresh screenshots: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_ui_gate_20260623\module_lab_narrow_390.png`, `module_lab_keyboard_focus.png`, and `module_lab_load_error_390.png`.
- Live runner script syntax: passed. Existing all-scope runner evidence remains valid for backend behavior because this repair touched only copy/CSS: `work\release_evidence\20260623-module-lab-beta-all-scope\module_lab_live_runner_all_scope.json`.
- Broader release review gate: still failed only `accept_v01_no_group_statistics_boundary`; output path `work\release_evidence\20260620-v01-acceptance\release_review_gate_run.json`.

Acceptance note:

- Accepted for Module Lab UI/copy/error-state publish-standard slice.
- Not accepted as whole-product release-ready until the broader release-review boundary failure is resolved or formally scoped out.


## 2026-06-23 Release review gate pass after boundary and visual QA retest

Task goal:

- Continue the review-system test -> guidance -> optimization -> retest loop until the release review system considers the current local/sandbox release publish-standard.

Changed files and artifacts:

- `frontend/index.html`: changed the storage-page wording from a group-statistics-risk phrase to boundary-safe descriptive result-table copy.
- `work/release_evidence/20260620-page-visual-qa/page_visual_qa.json`: refreshed browser visual QA evidence.
- `work/release_evidence/20260620-page-visual-qa/page_visual_qa_rerun_4174.json`: mirrored rerun evidence for review-system packet consumers.
- `work/release_evidence/20260620-page-visual-qa/screenshots/`: refreshed customer/admin/lab screenshots.
- `docs/PROJECT_STATUS.md` and `docs/TASK_LOG.md`: recorded release-gate pass evidence and residual public-cloud boundary.

Validation:

```powershell
python scripts\acceptance_v01_no_group_statistics_boundary.py
python scripts\check_no_mojibake.py frontend\index.html frontend\module-lab.js frontend\module-lab.html frontend\module-lab.css
node C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\page_visual_qa_customer_admin_current_20260623.mjs
python scripts\acceptance_production_goal_matrix.py
python scripts\check_no_mojibake.py work\release_evidence\20260620-page-visual-qa\page_visual_qa.json work\release_evidence\20260620-page-visual-qa\page_visual_qa_rerun_4174.json
python scripts\run_release_review_gate.py
```

Results:

- V01 no group-statistics boundary: passed, blockers empty.
- Targeted source mojibake check: passed.
- Browser page visual QA: passed for 15 page states x 3 viewports, with screenshots under `work\release_evidence\20260620-page-visual-qa\screenshots\`.
- Production goal matrix: `passed_with_external_boundaries`, failed_requirements empty, external boundary only `aliyun_provider_boundary`.
- Full release review gate: `status=passed`, `steps=35`, `failed_steps=[]`.

Acceptance note:

- GPT-5.5/Codex final acceptance: local/sandbox review-system publish-standard is now proved by current authoritative evidence.
- Residual scope: strict public cloud/provider production release remains outside this pass until Aliyun/OSS/provider inputs are supplied and strict preflight is rerun.


## 2026-06-23 Aliyun/provider boundary continuation receipt

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

Task:

- Locate the user-referenced `http://127.0.0.1:8501/` service and continue the current local development line.

Actions:

- Verified that `8501` is not listening and that the active local app is QLanalyser Online on `4174` frontend + `8001` backend.
- Confirmed the active repository and startup commands from `README.md`, `frontend/package.json`, running process command lines, and HTTP smoke checks.
- Wired the existing `frontend/assets/customer_oddball_case` result package into the active `frontend/index.html` result-review and report-delivery views.

Verification:

- `http://127.0.0.1:8001/api/health`: 200.
- `http://127.0.0.1:4174/`: 200.
- `http://127.0.0.1:8501/`: connection refused, confirming it is not the active service.

Remaining:

- Run final link extraction and asset HTTP checks after the HTML change.
- Email remains draft/package-only until SMTP credentials are configured and verified.


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
- 2026-06-25 12:18 CST - Module Lab grouped-method UI and generated-EDF E2E acceptance.

  Objective:

  - Merge methods of the same analysis family into one review card with a method selector and method-specific parameters.
  - Generate a local EDF and run every runnable Module Lab method end-to-end against that generated EDF.

  Changed files:

  - `frontend/module-lab.js`: added grouped method cards, method picker behavior, and grouped Chinese method index while preserving existing `module_name` and `workflow_id` API contracts.
  - `frontend/module-lab.css`: added scoped styling for grouped method cards and method panels.
  - `scripts/generate_module_lab_grouped_methods_edf.py`: generates the local EDF fixture and event TSV for this acceptance run.
  - `scripts/acceptance_module_lab_grouped_methods_e2e.mjs`: uploads the generated EDF through the Module Lab page and runs QC, PSD, TFR, multitaper PSD/TFR, ERP, reference/CSD, PAC, and connectivity end-to-end.

  Validation:

  ```powershell
  node --check frontend\module-lab.js
  node --check scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  python -X utf8 scripts\check_no_mojibake.py frontend\module-lab.js frontend\module-lab.html frontend\module-lab.css scripts\generate_module_lab_grouped_methods_edf.py scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  python -X utf8 scripts\generate_module_lab_grouped_methods_edf.py
  node scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  ```

  Evidence:

  - Generated EDF: `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_local.edf`.
  - Generated EDF summary: `work\release_evidence\20260625-module-lab-grouped-methods-e2e\generated_edf_summary.json` (`status=passed`, 8 channels, 250 Hz, 60 sec, 36 annotations).
  - E2E evidence: `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.json` (`status=passed`, 5 grouped UI cards, 5 method pickers, 8/8 methods passed).
  - Visual evidence: `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.png`.
  - Normal review URL smoke: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_grouped_normal_url_20260625\normal_url_grouped_page.json` (`status=passed`, 5 groups, 5 pickers, TFR panel visible after selection).
  - Normal review URL screenshot: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_grouped_normal_url_20260625\normal_url_grouped_page.png`.

  Acceptance:

  - Accepted for local review. The page now presents same-family methods as grouped entries with parameter selection inside the group, and the generated EDF E2E run confirms every current runnable method creates real backend tasks and downloadable artifacts.

- 2026-06-25 13:02 CST - Module Lab method taxonomy correction after review.

  Review finding:

  - PSD and TFR were previously grouped too broadly as "spectral/time-frequency" because both use frequency parameters. This was rejected: PSD describes continuous/resting spectral power, while TFR describes event-locked time-frequency dynamics.
  - PAC and connectivity were also split: PAC/CFC is cross-frequency coupling, while connectivity is channel-to-channel association.

  Corrected taxonomy:

  - `data-readiness`: QC / data readiness.
  - `stationary-spectral-power`: PSD / bandpower.
  - `event-locked-time-domain`: ERP / P300.
  - `event-locked-time-frequency`: TFR / ERSP / ITC.
  - `multitaper-estimation`: multitaper PSD/TFR estimator with its own internal analysis-family parameter.
  - `reference-transform`: reference / CSD.
  - `cross-frequency-coupling`: PAC / CFC.
  - `sensor-connectivity`: sensor connectivity.

  Changed files:

  - `frontend/module-lab.js`: reclassified method groups and removed unnecessary single-method group dropdowns.
  - `frontend/module-lab.css`: added single-method method-type styling.
  - `scripts/acceptance_module_lab_grouped_methods_e2e.mjs`: updated expected group ids and E2E routing evidence.

  Validation:

  ```powershell
  node --check frontend\module-lab.js
  node --check scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  python -X utf8 scripts\check_no_mojibake.py frontend\module-lab.js frontend\module-lab.css scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  node C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\taxonomy_review_check_20260625.mjs
  node scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  ```

  Evidence:

  - Taxonomy review JSON: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_taxonomy_review_20260625\taxonomy_review.json` (`status=passed`, PSD separated from TFR, PAC separated from connectivity).
  - Taxonomy screenshot: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_taxonomy_review_20260625\taxonomy_review.png`.
  - Full EDF E2E: `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.json` (`status=passed`, 8 groups, 0 unnecessary method pickers, 8/8 methods passed).

- 2026-06-25 13:18 CST - PSD parameter exposure review and UI update.

  Code review finding:

  - `eeg_core/analysis/psd.py` already validates and applies `n_fft`, `n_overlap`, `bad_channels`, and `reject_by_annotation`.
  - `n_fft` and `n_overlap` are passed into `Raw.compute_psd(method="welch", ...)` and recorded in `effective_call.json`.
  - `bad_channels` is applied before EEG channel picking and recorded in source metadata / applied preparation.
  - `reject_by_annotation` is passed to MNE PSD computation.
  - `window` and `average` appear in `PSD_PARAMETER_SCHEMA`, but the current runner does not pass them into `compute_psd`; they are not exposed yet to avoid no-op UI controls.
  - `bad_segments` is supported by JSON parameters but needs a structured interval editor before exposing safely in Module Lab.

  Changed files:

  - `frontend/module-lab.js`: exposed PSD `n_fft`, `n_overlap`, `bad_channels`, and `reject_by_annotation`.
  - `scripts/acceptance_module_lab_grouped_methods_e2e.mjs`: updated PSD E2E to submit and verify the newly exposed parameters.

  Validation:

  ```powershell
  node --check frontend\module-lab.js
  node --check scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  python -X utf8 scripts\check_no_mojibake.py frontend\module-lab.js scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  python -X utf8 scripts\acceptance_psd_p0.py
  node C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\psd_param_review_20260625.mjs
  ```

  Evidence:

  - PSD backend acceptance: `scripts\acceptance_psd_p0.py` passed and confirmed `n_fft=256`, bad-channel exclusion, effective call, threshold validation, and artifact contract.
  - PSD page smoke JSON: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_psd_params_20260625\psd_params_review.json` (`status=passed`, fields present, parameters echoed, artifacts present).
  - PSD page smoke screenshot: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_psd_params_20260625\psd_params_review.png`.

- 2026-06-25 13:24 CST - ERP parameter exposure review and UI update.

  Code review finding:

  - `eeg_core/analysis/erp.py` already applies and records `reference`, `reject_by_annotation`, `reject_eeg_uv`, `bad_channels`, and `roi_channels`.
  - `reference` is applied through `raw.set_eeg_reference(...)` before epoching.
  - `reject_by_annotation` and `reject_eeg_uv` are passed into `mne.Epochs(...)` and summarized in `drop_log_summary.json`.
  - `bad_channels` is applied before epoching through data-preparation directives.
  - `roi_channels` controls the channel set used for component amplitude/latency extraction and is recorded in ERP metrics and summaries.
  - `components` / custom N100-P200-P300 windows are supported by the runner but not exposed yet; they need a structured component-window editor rather than loose text fields.
  - `bad_segments` is supported but not exposed yet for the same reason: it needs a safe interval editor.

  Changed files:

  - `frontend/module-lab.js`: exposed ERP `reference_mode`, `reject_by_annotation`, `reject_eeg_uv`, `bad_channels`, and `roi_channels`.
  - `scripts/acceptance_module_lab_grouped_methods_e2e.mjs`: updated ERP E2E to submit and verify the newly exposed parameters.

  Validation:

  ```powershell
  node --check frontend\module-lab.js
  node --check scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  python -X utf8 scripts\check_no_mojibake.py frontend\module-lab.js scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  node C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\erp_param_review_20260625.mjs
  node scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  ```

  Evidence:

  - ERP page smoke JSON: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_erp_params_20260625\erp_params_review.json` (`status=passed`, fields present, parameters echoed, artifacts present).
  - ERP page smoke screenshot: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_erp_params_20260625\erp_params_review.png`.
  - Full generated-EDF Module Lab E2E: `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.json` (`status=passed`, 8/8 runnable methods passed after ERP parameter exposure).

- 2026-06-25 13:52 CST - Remaining beta modules parameter exposure and layout review.

  Scope:

  - Upgraded remaining Module Lab method forms after reviewing live runner parameters.
  - Exposed only parameters that are validated/applied by backend runners and recorded in task evidence.

  Added UI parameters:

  - TFR: `picks`, `average`.
  - PAC: `n_surrogates`, `random_state`, `filter_edge_padding_sec`, `edge_trim_sec`.
  - Reference/CSD: `bad_channels`, `bipolar_pairs` text shorthand (`anode-cathode`).
  - Multitaper PSD/TFR: `remove_dc`, `bad_channels`, `picks`, `baseline_mode`, `use_fft`, `zero_mean`.
  - Connectivity: visible `reference=current_recording` selector.

  Not exposed yet:

  - `bad_segments` interval arrays and complex multi-pair editors remain blocked until a structured interval/pair editor is added.
  - CSD mode remains available but still requires montage/electrode positions; E2E uses average reference to avoid false CSD success on non-montage EDF.

  Validation:

  ```powershell
  node --check frontend\module-lab.js
  node --check scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  python -X utf8 scripts\check_no_mojibake.py frontend\module-lab.js frontend\module-lab.css scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  python -X utf8 scripts\acceptance_tfr_module.py
  python -X utf8 scripts\acceptance_reference_csd_module.py
  python -X utf8 C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\run_remaining_acceptance_serial_20260625.py
  node scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  node C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\layout_review_20260625.mjs
  ```

  Evidence:

  - TFR acceptance: `work\release_evidence\20260622-tfr-module\acceptance_tfr_module.json` passed.
  - PAC acceptance: `work\release_evidence\20260622-pac-module\acceptance_pac_module.json` passed.
  - Reference/CSD acceptance: `work\release_evidence\20260622-reference-csd-module\acceptance_reference_csd_module.json` passed.
  - Multitaper acceptance: `work\release_evidence\20260622-multitaper-psd-tfr-module\acceptance_multitaper_psd_tfr_module.json` passed.
  - Connectivity acceptance: `work\release_evidence\20260622-connectivity-module\acceptance_connectivity_module.json` passed.
  - Full generated-EDF Module Lab E2E: `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.json` (`status=passed`, 8/8 methods passed with upgraded parameters).
  - Layout review JSON: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_layout_review_20260625\layout_review.json` (`status=passed`, desktop+narrow, no horizontal overflow).
  - Layout screenshots: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_layout_review_20260625\desktop.png`, `...\narrow.png`.

  Layout decision:

  - Analysis cards now use auto-fit minimum widths to avoid narrow three-column beta cards on desktop.
  - Mobile parameters switch to single-column fields under 560 px.

- 2026-06-25 14:26 CST - Multitaper PSD and multitaper TFR split into independent review entries.

  Review finding:

  - `multitaper_psd_tfr` was still presented as one UI method even after PSD and TFR were separated elsewhere.
  - This was misleading for review: multitaper PSD is continuous spectral-power estimation, while multitaper TFR is event-locked time-frequency analysis.

  Implementation:

  - Added independent UI entries:
    - `multitaper_psd`: title `多窗 PSD`, fixed `analysis_family=psd`.
    - `multitaper_tfr`: title `事件锁定多窗 TFR`, fixed `analysis_family=tfr`.
  - Both entries still route to the existing backend module `multitaper_psd_tfr` and workflow `multitaper_psd_tfr`.
  - `runModule()` now supports `backendModule` mapping so UI method ids can be scientifically precise without breaking backend contracts.
  - Multitaper PSD automatically sends backend-required internal validation defaults for TFR-shaped fields (`freqs`, `baseline`, `n_cycles`, `time_bandwidth`, `decim`) without exposing them as PSD UI controls.

  Validation:

  ```powershell
  node --check frontend\module-lab.js
  node --check scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  python -X utf8 scripts\check_no_mojibake.py frontend\module-lab.js scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  node C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\layout_review_20260625.mjs
  node scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  ```

  Evidence:

  - Full generated-EDF Module Lab E2E: `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.json` (`status=passed`, 9 independent UI entries, including `multitaper_psd` and `multitaper_tfr`).
  - Layout review: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_layout_review_20260625\layout_review.json` (`status=passed`, 9 groups, no horizontal overflow).

- 2026-06-25 15:10 CST - Module Lab method test bench requirements and test plan documented.

  Scope:

  - Added a detailed product and testing baseline for the Module Lab method development test bench.
  - Clarified that Module Lab is a no-account, no-formal-project method development, review, and QA bench, not the final customer workbench.
  - Recorded the scientific taxonomy rule that PSD and TFR stay separate, multitaper PSD and multitaper TFR stay separate UI entries, and ERSP/ITC are current TFR outputs/metrics rather than separate methods.
  - Documented parameter exposure rules, UI requirements, backend task requirements, E2E testing requirements, layout checks, release criteria, current evidence, and future editor work.

  Artifact:

  - `docs\product\module_lab_method_test_bench_requirements_and_test_plan.md`.

- 2026-06-25 15:35 CST - Module Lab method test bench visual polish pass.

  Scope:

  - Upgraded Module Lab first-screen presentation from a stacked form feel to a polished method test bench surface.
  - Updated cache-busting resource versions in `frontend\module-lab.html`.
  - Added Chinese-first hero positioning for "method development test bench", no-account usage, 9 independent method entries, and real backend execution.
  - Added method-card evidence chips for real task execution, parameter echo, and artifact evidence.
  - Improved card, method index, data-source panel, button, input, empty-state, artifact, and parameter-echo styling in `frontend\module-lab.css`.
  - Kept backend contracts unchanged: module ids, workflow ids, `/api/tasks`, parameter names, and method taxonomy remain stable.

  Changed files:

  - `frontend\module-lab.html`
  - `frontend\module-lab.js`
  - `frontend\module-lab.css`

  Validation:

  ```powershell
  node --check frontend\module-lab.js
  node --check scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  python -X utf8 scripts\check_no_mojibake.py frontend\module-lab.js frontend\module-lab.css frontend\module-lab.html
  node C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\layout_review_20260625.mjs
  ```

  Browser evidence:

  - Current page URL: `http://127.0.0.1:4174/module-lab.html?api=http://127.0.0.1:8001/api`.
  - Polished QC smoke evidence: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_polish_20260625\module_lab_polished_qc_smoke.json`.
  - Polished QC smoke screenshot: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_polish_20260625\module_lab_polished_qc_smoke.png`.
  - QC UI smoke created real completed task `task_2ec674631d4c`, showed parameter echo, and exposed 8 artifact links.
  - Layout review JSON remains passed with 9 groups, Chinese body text, and no horizontal overflow.

  E2E note:

  - A full generated-EDF all-method E2E rerun was started after the polish fix. The first failed attempt revealed that closed parameter details hid parameter text from the acceptance script; this was fixed by leaving parameter echo open by default.
  - The subsequent full all-method E2E run exceeded the interactive window and was stopped to avoid a stale long-running test process. A focused real-browser QC smoke plus full layout review replaced it for this visual-only slice.

- 2026-06-26 00:05 CST - Module Lab grouped-methods closed-parameter E2E repair accepted.

  Scope:

  - Resume the inherited 02 grouped-methods Module Lab task and close the real browser E2E failure.
  - Do not alter router, Headroom, IPC, gateway, or process-communication files.

  Root cause:

  - The page and backend runner were healthy after starting the local 8001 backend.
  - The failing E2E point was `multitaper_psd`: `input[name="picks"]` existed but was hidden inside a closed advanced-parameter `details` block.
  - This made the field unavailable to the real browser runner and to normal visible editing, while leaving the DOM present enough to make the failure easy to misread.

  Implementation:

  - Updated `frontend\module-lab.js` so `renderParameterFields()` emits `<details class="advanced-params" open>`.
  - No backend dispatch, parameter contract, module taxonomy, task-service path, or artifact output contract was changed.

  Validation:

  ```powershell
  node --check frontend\module-lab.js
  python -X utf8 scripts\check_no_mojibake.py frontend\module-lab.js scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  python scripts\acceptance_multitaper_psd_tfr_module.py
  node scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  ```

  Evidence:

  - Module acceptance: `work\release_evidence\20260622-multitaper-psd-tfr-module\acceptance_multitaper_psd_tfr_module.json` passed with 22 artifacts and no failures.
  - Full generated-EDF Module Lab E2E: `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.json` passed with modules `qc, psd, tfr, multitaper_psd, multitaper_tfr, erp, reference_csd, pac, connectivity`, 9 groups, 0 errors.
  - Screenshot: `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.png`.

  Process note:

  - Temporary local backend `8001` was started for verification and stopped after the pass. The pre-existing `4174` frontend process was not modified.

- 2026-06-26 01:10 CST - 07 accepted 02 Module Lab grouped-methods into mainline.

  Scope:

  - Read the 02 -> 07 production integration design and execution packet from real repo files.
  - Merge the beta zone into the 07 mainline as an internal beta / review surface.
  - Preserve the distinction between stable methods and beta methods; do not promote beta methods to public stable customer entry.
  - Preserve backend contracts and do not touch router, Headroom, IPC, gateway, or process-communication configuration.

  Changes:

  - Added `scripts\acceptance_module_lab_visible_fields.mjs` for closed-details / hidden-input regression.
  - Added `scripts\acceptance_module_lab_layout_review.mjs` for desktop, mobile, and narrow Module Lab layout evidence.
  - Added `scripts\run_module_lab_acceptance_stack.py` to standardize the local 8001/4174 acceptance stack.
  - Added `scripts\build_module_lab_mainline_acceptance_packet.py` to generate 07 manifest and final acceptance packet.
  - Strengthened `scripts\acceptance_module_lab_grouped_methods_e2e.mjs` with `/api/tasks.module_name` assertions.
  - Updated `frontend\module-lab.js` with clearer beta boundary wording and unique PAC dataset/upload test ids.

  Validation:

  ```powershell
  node --check frontend\module-lab.js
  node --check scripts\acceptance_module_lab_grouped_methods_e2e.mjs
  node --check scripts\acceptance_module_lab_visible_fields.mjs
  node --check scripts\acceptance_module_lab_layout_review.mjs
  python -X utf8 -m py_compile scripts\run_module_lab_acceptance_stack.py scripts\build_module_lab_mainline_acceptance_packet.py
  python -X utf8 scripts\check_no_mojibake.py frontend\module-lab.js frontend\module-lab.css frontend\module-lab.html scripts\acceptance_module_lab_visible_fields.mjs scripts\acceptance_module_lab_layout_review.mjs scripts\run_module_lab_acceptance_stack.py scripts\build_module_lab_mainline_acceptance_packet.py
  python -X utf8 scripts\acceptance_multitaper_psd_tfr_module.py
  python -X utf8 scripts\acceptance_connectivity_module.py
  python -X utf8 scripts\acceptance_reference_csd_module.py
  python -X utf8 scripts\acceptance_pac_module.py
  python -X utf8 scripts\run_module_lab_acceptance_stack.py --mode both
  python -X utf8 scripts\build_module_lab_mainline_acceptance_packet.py
  ```

  Evidence:

  - `work\release_evidence\07-mainline-integration\module_lab_integration_manifest.json`.
  - `work\release_evidence\07-mainline-integration\module_lab_visible_fields.json`.
  - `work\release_evidence\07-mainline-integration\module_lab_layout_review.json`.
  - `work\release_evidence\07-mainline-integration\module_lab_acceptance_stack.json`.
  - `work\release_evidence\07-mainline-integration\module_lab_mainline_acceptance_packet.json`.
