# QLanalyser -> ZCode 开发交接

## 最新状态：阿里云演示已验收

2026-07-21 公网演示链路已完成 33/33 项浏览器端到端验收，可演示数据管理、EEG 波形预览、癫痫样事件分析、人工复核和报告 ZIP 导出。

- 演示入口：`http://39.97.248.225/?customer_demo=auto&workbench=epilepsy_ml&api=http%3A%2F%2F39.97.248.225%2Fapi`
- API health：`status=ok`
- 发布记录：`docs/release/aliyun_epilepsy_demo_20260721.md`
- E2E 证据：`work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json`
- 截图：`work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/04_results_review_package.png`
- 当前状态：线上演示已验收；本地相关改动未 commit、未 push。

ZCode 接手后的第一动作：先读 `docs/PROJECT_HUB.md` 和本次发布记录，再运行 `git status --short --branch`。不要 reset、checkout、clean，不要提交整个脏工作树，也不要用本地整个 `frontend/app.js` 覆盖线上文件。

演示只能使用 `work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_60s.edf` 合成数据。禁止上传真实客户、受试者或 HE 数据。产品仅用于科研筛查支持，不作临床诊断。

必须保留的技术事实：当前分析在 HTTP 请求内同步执行，`worker/` 尚未接入正式异步链路；JSON registry 多实例一致性和 `.accounts.lock` 超时仍是风险。

> 交接日期：2026-07-21（Asia/Shanghai）  
> 接手对象：ZCode  
> 任务性质：继续本地开发；先保护与收敛现有工作树，再进入下一项功能开发。  
> 事实口径：本文中的仓库、分支、提交和工作树状态已于交接当日从本机核验；历史测试结果不能替代当前代码复测。

## 0. 给 ZCode 的直接指令

请在以下唯一主仓库继续工作：

```text
D:\Quanlan\Codes\Python\quanlan-analyser-official
```

进入仓库后先执行第 7 节的只读检查。当前存在大量未提交开发成果，**禁止 reset、checkout 覆盖、clean、批量删除、强制切分支或重写历史**。不要把未跟踪文件当临时垃圾，它们包含新增模型、服务、算法和验收脚本。

当前唯一主线：保护现有成果，建立可复现的当前基线，将改动按功能域拆成可独立验证的工作单元。不要先开发新的无关功能。

## 1. 产品定义与边界

QLanalyser Online 是面向科研和 CRO 场景的在线 EEG 数据管理、分析与结果交付平台。目标是把非标准脑电分析转化为标准化、可复现、可审计、可商业运营的科研工作流。

硬边界：

- 不是医疗诊断、治疗建议、医疗器械或临床决策支持系统。
- 不得把 Lab/Beta 方法写成稳定生产能力。
- 不得用静态页面、假数据或文案冒充可执行后端链路。
- 不得提交真实客户 EEG、隐私数据、日志、缓存、密钥、`.env` 或本地模型连接文件。
- 原始 EEG 不存入数据库；长分析任务不得阻塞 HTTP 请求。

团队项目入口：

```text
docs\PROJECT_HUB.md
```

飞书项目总览：

```text
https://quanland.feishu.cn/wiki/OeNWwlv7MiPL7ck37fUclmN8nIg
```

## 2. 已核验 Git 基线

```text
Remote:  https://github.com/Guannan-Xi/quanlan-analyser.git
Branch:  feature/epilepsy-full-flow-backend-20260706
HEAD:    f1a18f153298da2ba1e4b4fd046be3ae174a0091
Commit:  fix(ui): simplify epilepsy review flow controls
Date:    2026-07-08T13:32:59+08:00
Remote relation: ahead 1 of origin/feature/epilepsy-full-flow-backend-20260706
```

注意：

- `D:\Quanlan\Codes\Python\quanlan-analyser` 不是源码仓库，仅有本地模型连接配置。不要读取或迁移其中的密钥。
- `D:\Quanlan\Codes\Python\quanlan-analyser-official-non-epilepsy` 是同一仓库的并行 worktree，包含另一条大型未提交工作线。未经差异盘点和用户确认，不要合并或覆盖。
- `D:\Quanlan\Codes\Python\AR_analyser1` 是旧 PyQt 桌面产品，属于算法/产品历史来源，不是当前 Web 主仓库。

## 3. 当前工作树事实

当前工作树不是干净基线。交接前的 `git status` 显示：

- 业务与既有文档：约 45 个已修改文件；
- 新增内容：约 12 个未跟踪文件（包含本交接文档前的项目总览）；
- 原业务改动统计：约 3050 行新增、988 行删除；
- 当前分支领先同名远程分支 1 个提交。

数量会因本交接文档新增而增加 1；请以接手时的 `git status --short` 为准。

这些改动不是一个已验收整体，不能一次性 `git add -A` 后提交。

## 4. 未提交改动分组

### A. 癫痫样事件本地 Lab 全流程（开发中）

主要文件：

```text
backend/api/lab_epilepsy_full_flow.py
frontend/epilepsy-full-flow-preview.{html,css,js}
frontend/epilepsy-review-preview.{html,css,js}
frontend/epilepsy-report-preview.{html,css,js}
scripts/acceptance_lab_epilepsy_full_flow_api.py
scripts/e2e_lab_epilepsy_full_flow_browser.mjs
scripts/acceptance_epilepsy_full_page_visual_review_screenshots.mjs
scripts/acceptance_epilepsy_review_waveform_performance.mjs
```

目标：候选事件生成、波形复核、报告预览与导出形成可执行的本地实验室链路。

边界：只用于科研/Lab 复核，不得表达为癫痫临床诊断。

### B. 分析模块与科学契约（开发中）

主要文件：

```text
eeg_core/analysis/pac.py
eeg_core/analysis/pac_v2.py
eeg_core/analysis/tfr.py
eeg_core/analysis/band_power.py
backend/services/module_contract_service.py
backend/services/product_catalog.py
frontend/module-lab.js
scripts/acceptance_pac_module.py
scripts/acceptance_pac_v2_contract.py
scripts/acceptance_tfr_module.py
scripts/acceptance_band_power_backend.py
scripts/acceptance_module_contract_registry.py
```

目标：统一输入、参数、输出、工件、报告映射和生命周期状态。Band Power 为 V1 稳定目标；PAC/TFR 仍按 Lab/Beta 证据管理。

### C. 数据准备、正式输入与任务边界（开发中）

主要文件：

```text
backend/api/data_crud.py
backend/api/data_preparation.py
backend/api/eeg_files.py
backend/api/projects.py
backend/api/tasks.py
backend/models/data_preparation.py
backend/services/data_preparation_service.py
backend/services/data_source_policy.py
backend/services/task_service.py
scripts/acceptance_data_prep_task_billing_guards.py
scripts/acceptance_formal_task_rejects_teaching_input.py
scripts/acceptance_module_lab_input_source_gate.mjs
scripts/acceptance_teaching_mode_protection.py
```

目标：教学/演示数据与正式客户数据隔离；数据准备结果正确绑定正式分析任务；不允许通过前端或 API 绕过输入来源门禁。

### D. 报告、客户交付、计费与公开 API 边界（开发中）

主要文件：

```text
backend/api/artifacts.py
backend/api/reports.py
backend/models/public_api.py
backend/services/customer_delivery_service.py
backend/services/billing_service.py
backend/services/quota_service.py
backend/services/report_service.py
scripts/acceptance_customer_api_no_internal_paths.py
```

目标：客户下载与报告输出不泄露服务器内部路径；交付物、任务计费和报告工件保持一致且可追溯。

### E. 文档入口（本次 Codex 新增，未提交）

```text
README.md
docs/PROJECT_HUB.md
docs/PROJECT_STATUS_CURRENT.md
HANDOFF_FOR_ZCODE_20260721.md
```

目标：`docs/PROJECT_HUB.md` 是当前项目唯一协作入口；旧 `PROJECT_STATUS_CURRENT.md` 仅保留为 2026-06-20 历史快照。

## 5. 接手后的第一目标

**目标：在不丢失任何现有改动的前提下，形成当前工作树的可信基线与可提交切片。**

完成定义：

1. 保存完整 `git status`、`git diff --stat` 和未跟踪文件清单，不读取秘密文件内容。
2. 对 A-D 四组逐组检查依赖关系，确认是否可独立提交；不要按文件类型机械拆分。
3. 为每组运行最小语法/契约测试，记录通过、失败和未运行项。
4. 失败时修根因，不用跳过、硬编码通过或删除断言掩盖失败。
5. 在 `docs/PROJECT_HUB.md` 更新真实状态、证据路径和下一动作。
6. 提交前只暂存当前已验收的一组，执行 `git diff --cached --name-only` 和秘密/隐私检查。
7. 未经用户明确要求，不 push、不部署、不操作生产环境。

## 6. 建议执行顺序

### 第一步：建立只读现场快照

执行第 7 节命令并保存结果。若接手时状态与本文差异明显，以当前磁盘为准，但不得擅自回滚新增变化。

### 第二步：先验证数据来源和公开交付边界

优先验证 C、D 两组。它们影响正式数据、客户可见信息、计费与结果交付，风险高于 UI 润色。

### 第三步：验证分析模块契约

验证 B 组的 PAC v2、TFR、Band Power、模块注册、计费和产物映射保持一致。

### 第四步：验证癫痫 Lab 全流程

先跑 API 验收，再启动本地页面做浏览器 E2E、波形性能和 9:16/桌面视觉检查。不要把 Lab 结果推广为临床或生产结论。

### 第五步：形成小提交

每次提交只处理一个行为闭环，建议顺序：

1. 数据来源门禁与正式任务绑定；
2. 客户公开 API/交付路径保护；
3. Band Power 与模块契约；
4. PAC v2 / TFR Lab 契约；
5. 癫痫 full-flow API；
6. 癫痫复核/报告前端与浏览器证据；
7. 项目文档与交接。

只有在实际依赖关系允许时才采用此顺序。若一项依赖另一项尚未提交的接口，应记录依赖并一起形成最小闭环，不要复制实现。

## 7. 接手必跑命令

### 只读 Git 检查

```powershell
$repo = 'D:\Quanlan\Codes\Python\quanlan-analyser-official'
git -C $repo status --short --branch
git -C $repo remote -v
git -C $repo log -1 --date=iso-strict --pretty=fuller
git -C $repo diff --stat
git -C $repo ls-files --others --exclude-standard
```

### Python 与 JavaScript 最小静态检查

只对当前切片相关文件运行，不要用自动格式化器批量重写整个仓库。

```powershell
Set-Location 'D:\Quanlan\Codes\Python\quanlan-analyser-official'
C:\Users\XGN\miniconda3\python.exe -X utf8 -m py_compile <本切片 Python 文件>
node --check <本切片 JavaScript/MJS 文件>
C:\Users\XGN\miniconda3\python.exe -X utf8 scripts\check_no_mojibake.py <本切片文本文件>
```

### 当前切片候选验收

按依赖逐个运行；若某脚本需要服务、样本或环境变量，先读脚本入口和 README，不要猜参数，不要打印配置值。

```powershell
C:\Users\XGN\miniconda3\python.exe -X utf8 scripts\acceptance_data_prep_task_billing_guards.py
C:\Users\XGN\miniconda3\python.exe -X utf8 scripts\acceptance_formal_task_rejects_teaching_input.py
C:\Users\XGN\miniconda3\python.exe -X utf8 scripts\acceptance_customer_api_no_internal_paths.py
C:\Users\XGN\miniconda3\python.exe -X utf8 scripts\acceptance_band_power_backend.py
C:\Users\XGN\miniconda3\python.exe -X utf8 scripts\acceptance_pac_v2_contract.py
C:\Users\XGN\miniconda3\python.exe -X utf8 scripts\acceptance_module_contract_registry.py
node scripts\acceptance_module_lab_input_source_gate.mjs
```

癫痫 Lab 全流程以仓库 README 的启动方式为准。确认本地样本目录存在后，再运行：

```powershell
C:\Users\XGN\miniconda3\python.exe scripts\acceptance_lab_epilepsy_full_flow_api.py --api-base-url http://127.0.0.1:8001/api --record-id he-105 --top-k 6 --scan-windows 12 --candidate-timeout 120
node scripts\e2e_lab_epilepsy_full_flow_browser.mjs
```

本文没有声称上述测试在当前工作树已经通过；ZCode 必须记录实际结果。

## 8. 本地启动

后端：

```powershell
Set-Location 'D:\Quanlan\Codes\Python\quanlan-analyser-official'
C:\Users\XGN\miniconda3\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

前端：

```powershell
Set-Location 'D:\Quanlan\Codes\Python\quanlan-analyser-official\frontend'
npm run serve
```

客户入口：

```text
http://127.0.0.1:4174/?api=http://127.0.0.1:8001/api
```

不要默认占用已有服务端口。启动前先检查端口；若已有服务，确认它是否来自当前仓库和当前代码。

## 9. 禁止事项

- 禁止 `git reset --hard`、`git clean -fd`、`git checkout -- <file>` 或等效覆盖操作。
- 禁止一次性 `git add -A` 提交所有历史改动。
- 禁止读取、输出、复制或提交 `.env`、API key、token、本地模型连接配置。
- 禁止把 `data/`、`work/`、`outputs/` 中的客户数据、日志、缓存或大型证据包纳入提交。
- 禁止未经用户确认合并 `quanlan-analyser-official-non-epilepsy` worktree。
- 禁止自动 push、部署阿里云或修改线上环境。
- 禁止用历史 `passed` 代替当前分支验证。
- 禁止把科研候选事件、算法评分或 Lab 结果表述成临床诊断。
- 禁止无关重构、批量格式化或依赖升级。

## 10. ZCode 每次完成一个切片后的回写格式

更新 `docs/PROJECT_HUB.md`，并在回复中使用：

```text
目标：
完成内容：
根因/设计依据：
修改文件：
验证命令：
验证结果：
未完成：
风险与边界：
commit：
是否 push：否（除非用户明确要求）
下一步唯一动作：
```

状态只使用：`待办`、`进行中`、`阻塞`、`待验收`、`已完成`。标记“已完成”必须绑定实际 commit 或验收证据。

## 11. 当前明确未完成

- 当前 50 多项工作树变化尚未形成可信的分组提交。
- 本交接未运行业务代码的全量验收。
- 非癫痫 worktree 与当前分支的合并策略尚未确认。
- 历史公开部署证据不能证明当前工作树可发布。
- 当前正式发布结论：**未验证，不可宣称可发布**。

## 12. ZCode 的第一条回复应包含

1. 已确认的仓库、分支、HEAD 和工作树数量；
2. 明确承诺不覆盖现有修改；
3. A-D 四组中首先处理哪一组及原因；
4. 该组的验收标准和计划运行的命令；
5. 发现本文与现场不一致时，列出差异，不自行重置现场。
