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
node --check scriptscceptance_research_modules_static.mjs
python scripts\check_no_mojibake.py
node scriptscceptance_research_modules_static.mjs
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
