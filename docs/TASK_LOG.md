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

