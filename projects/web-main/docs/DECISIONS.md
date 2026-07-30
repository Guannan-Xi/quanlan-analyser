# QLanalyser Online 决策记录

## 1. 产品命名

产品名统一为：

`QLanalyser Online`

版本标记统一为：

`Pilot`

完整版本统一为：

`QLanalyser Online v0.1 Pilot`

中文说明统一为：

`QLanalyser Online Pilot 试用版`

不得继续使用：

`QLanalyser EEG`

## 2. 品牌命名

品牌统一为：

- 全澜脑科学<sup>®</sup>
- QuanLan BrainScience<sup>®</sup>

## 3. 产品定位

统一使用：

`清晰管理 EEG 数据，规范执行分析流程，稳定交付可复核研究结果。`

## 4. 平台边界

统一使用：

`本平台用于科研数据管理与分析辅助，结果不作为临床诊断依据。`

## 5. 当前版本目标

当前目标是：

`QLanalyser Online v0.1 Pilot`

定位为：

`稳定 MVP，用于客户免费试用。`

不是完整商业化平台。

## 6. MVP 优先功能

优先实现：

- 登录页
- 工作台首页
- 项目管理
- EEG 文件上传
- 文件元数据查看
- Metadata/QC 分析
- Resting PSD 分析
- 分析任务状态
- 任务失败原因展示
- HTML 报告
- ZIP 报告包下载
- 管理员入口
- 基础日志
- 基础部署和备份说明

## 7. 暂不实现功能

暂不实现：

- 自助注册
- 复杂多租户
- 复杂权限系统
- 在线支付
- PAC
- Connectivity
- TFR
- 机器学习
- 临床诊断功能
- Kubernetes
- 微服务拆分
- 复杂 PDF 排版

## 8. 技术原则

- 不重写整个项目。
- 不做大规模重构。
- 每次只做一个明确小任务。
- 原始 EEG 文件不存数据库。
- 数据库只保存文件元数据和路径。
- 长时间 EEG 分析任务不阻塞 HTTP 请求。
- 分析结果必须尽量可复核，保存输入信息、参数、日志、软件版本和输出路径。
## 9. Git 工作流规则

每完成一个明确小任务后，必须使用项目专属 `qlanalyser-git-guard` 工作流：

- 先检查 `git status`、`git diff --stat`、`git diff --name-only`、`git remote -v`。
- 确认没有无关文件、敏感信息或临时输出进入提交。
- 运行相关测试，或对文档类任务确认仅文档/规则文件变化。
- 更新 `docs/PROJECT_STATUS.md` 和 `docs/TASK_LOG.md`。
- 只 stage 本次任务相关文件，不使用 `git add .` 处理混杂工作树。
- 创建小而清晰的本地 commit。
- 不自动 push；push 到 GitHub 必须等待用户明确确认。
- 不使用 `git push --force` 或 `git push -f`。
- 如果本地与远程历史分叉、落后或发生冲突，停止并报告，不强行 merge、rebase 或覆盖远程历史。

## 12. Spike 分析并入统一 QLanalyser（已撤回，见第 13 条）

2026-07-22：Spike sorting 与分析不再作为 `projects/spike-analysis` 平级软件维护，统一并入 `projects/web-main`。本地执行只描述数据处理位置，不改变应用归属。

- 复用现有 FastAPI、浏览器前端、账户、项目、文件、任务、artifact 和报告边界。
- Spike 领域逻辑放在 `eeg_core/spike/`，未来的 API、服务和长任务分别接入现有 `backend/api/`、`backend/services/` 和 `worker/tasks/`。
- 不复制第二套服务、登录、数据库、前端或启动命令；真实设备格式和 sorter 依赖在样本验证后再进入正式契约。

## 13. Spike 分析撤回并入，重新拆回独立预研模块

2026-07-22（同一天）：撤回第 12 条决策。Spike sorting 与分析重新拆回独立顶层项目
`projects/spike-analysis`，不再是 `web-main` 内部模块。

- 理由与 `qeeg-64ch-research` 一致：预研阶段的方法应先在独立包里做数值验证，
  不直接绑定 FastAPI/数据库/任务队列，避免过早耦合进核心平台。
- `eeg_core/spike/` 已从 `web-main` 移除；`projects/spike-analysis` 目前只有
  目录占位（README + `__init__.py`），未搭建 `pyproject.toml`/`tests`/CLI。
- `docs/product/spike_analysis_product_and_architecture.md` 保留作为第 12 条
  决策的历史背景，不代表当前归属。
- 未来若要把某个 Spike 方法提升进核心平台，走 Lab/internal validation →
  数值/契约验证 → 逐项迁入 `web-main/eeg_core` 的路径，不整包合并。





## 10. 多对话开发依据与飞书同步

QLanalyser Online 的软件架构设计、模块详细设计、验收标准和跨对话开发依据，统一以 GitHub / 仓库 Markdown 文档为唯一依据。

执行规则：

- 仓库文档是 canonical source of truth。
- 飞书只作为同步、评审和会议纪要窗口。
- 如果飞书内容与仓库文档不一致，以仓库文档为准。
- 对话中的重要结论必须先固化到仓库文档，再生成飞书可复制摘要。
- 没有实际飞书 API / 工具调用成功时，只能输出“可复制到飞书的摘要”，不得声称已同步飞书。
- 多个 AI 对话并行开发前，必须先读取 `docs/AI_CONVERSATION_SYNC.md` 与 `docs/AI_HANDOFF_CURRENT.md`。

对应项目 skill：`qlanalyser-conversation-sync`。

## 11. GitHub 最新基线与并行开发同步

所有 QLanalyser Online 并行开发对话必须以 GitHub `origin/main` 的最新状态和仓库内 canonical 设计文档为基础。

强制规则：

- 开发开始前必须执行 `git fetch origin` 并检查 `git status --short --branch`。
- 架构、版本、模块相关工作必须读取：
  - `docs/architecture/system_architecture.md`
  - `docs/architecture/version_detailed_design.md`
  - `docs/modules/analysis_modules_design_matrix.md`
  - `docs/DECISIONS.md`
  - `docs/PROJECT_STATUS.md`
- 开发完成前、commit 前、push 前必须再次 fetch GitHub 最新状态。
- 如果本地落后、分叉、远程 canonical 文档发生变化，必须停止并提醒用户确认下一步。
- 不允许自动覆盖本地或 GitHub 文件；涉及 merge、rebase、reset、覆盖或 force push 时必须明确说明风险并等待用户确认。
- push 前必须确认本地只领先远程且没有未解决冲突。

对应项目 skill：`qlanalyser-github-baseline-sync`。

## 14. SimNIBS 报告统计与渲染解耦

2026-07-28：SimNIBS 报告中的体积 ROI 或材料区域统计，统一以四面体体积作为均值和分位数权重；最大值单独定义为有限体单元峰值。报告必须同时保存权重类型、纳入体积、单位和来源场文件。

- SimNIBS 网格解析和场后处理由 SimNIBS 环境完成。
- 图件、Excel、HTML、PDF 和 manifest 可由独立交付层生成，但必须读取同一冻结统计数据。
- 当 SimNIBS 或 Matplotlib 运行环境的渲染后端不稳定时，不允许跳过统计口径或伪造图件；改用可复核的中间数据和独立渲染器。
- 正向球体工程验证不得升级表述为个体 MRI、TI、ROI、逆向优化或临床结论。

## 15. TI 载波回路电气独立性是数值引用硬前提

2026-07-29：当两个 TI 载波回路的电极网格存在共享节点、点接触或其他无法证明正间隙的拓扑时，报告不得只把问题描述为设备可执行性或几何迁移限制。

- 机器数据必须显式记录电气独立性是否建立、可能受影响的 E1/E2/TImax 与派生统计，以及正式引用是否允许。
- 在验证正的最小电极间隙、重新网格并重算两个载波场前，受影响场值、区域统计、阈值覆盖率和图件只能用于流程演示。
- HTML/PDF、图注、图件就绪表、schema 和验收脚本必须使用同一数值有效性口径；自动化文件验收不得被解释为科学有效性通过。
