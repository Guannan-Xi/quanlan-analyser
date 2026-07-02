# QLanalyser Online 项目协作规则

## 项目名称
QLanalyser Online

## 品牌
全澜脑科学® | QuanLan BrainScience®

## 产品定位
清晰管理 EEG 数据，规范执行分析流程，稳定交付可复核研究结果。

## 平台边界
本平台用于科研数据管理与分析辅助，结果不作为临床诊断依据。

## 当前目标
QLanalyser Online v0.1 Pilot：稳定 MVP，用于客户免费试用，不是完整商业化平台。

## 核心工作流
1. 登录 → 2. 创建项目 → 3. 上传 EEG 文件 → 4. 创建分析任务 → 5. 后台运行分析 → 6. 查看任务状态 → 7. 查看结果 → 8. 下载报告包

## 优先功能
登录页、工作台首页、项目管理、EEG文件上传、文件元数据、Metadata/QC分析、Resting PSD分析、任务状态、失败原因、HTML报告、ZIP报告包、管理员入口、基础日志、基础部署备份

## 暂不做
自助注册、复杂多租户、复杂权限系统、在线支付、PAC、Connectivity、TFR、机器学习、临床诊断功能、Kubernetes、微服务拆分、复杂PDF排版

## 开发规则
- 不要重写整个项目
- 不要一次性大规模重构
- 每次只完成一个明确小任务
- 不要引入不必要的新依赖
- 产品名统一为 QLanalyser Online
- 原始EEG文件不存入数据库
- 长时间分析任务不阻塞HTTP请求
- 分析结果保存完整参数和日志
- 每次任务完成后更新 docs/PROJECT_STATUS.md 和 docs/TASK_LOG.md
- 产品或架构决策更新 docs/DECISIONS.md

## QGCS 路由规则（项目级——V01 试点阶段）

本项目的 QGCS 全局路由规则执行时，以下项目级约束优先：

1. **安全审计范围：** 仅对 P0 硬边界（非医用措辞、数据完整性、功能崩溃）强制执行。暂不做清单中的项（复杂权限、多租户、机器学习等）不触发全局安全审计的 P0 要求。
2. **路由豁免：** 单文件 ≤5 行代码修改不需要跨模型路由，Codex 直接执行。≥6 行或多文件修改按全局规则路由到 GLM-5.2。
3. **并行 worker：** 项目是单体应用（FastAPI + 静态前端），Sprint Board 多 worker 并行规则不强制执行。
4. **对抗审核：** 全量审核保留，但 N-Fold 双模型审查降级为单模型合规扫描。V1 商业化阶段后再启用 GPT-5.5 + DeepSeek 双模型 N-Fold。
5. **用户级验收：** 对抗性审查必须按 `docs/product/qlanalyser_user_level_e2e_adversarial_review_standard_20260702.md` 执行；静态代码扫描不能替代用户级 E2E 验收。

## Git 工作流
- 每完成小任务提交一次
- 不自动 push，push 等用户确认
- 不用 git push --force
- 有冲突停止并报告

## 每次任务完成后的交接格式

```md
## 本次任务交接

### 1. 任务目标
...

### 2. 已完成内容
...

### 3. 修改文件
- `path/to/file`：修改原因

### 4. 如何运行
...

### 5. 如何测试
...

### 6. 测试结果
...

### 7. 风险点
...

### 8. 未完成事项
...

### 9. 下一步建议
...
```

## Project AI Handoff Skills

### qlanalyser-close-chat-handoff
触发：结束会话 / 任务完成 / 交接上下文
用途：更新项目 handoff 文档、总结项目状态、记录最近完成工作和测试结果、准备下次会话启动上下文。

### qlanalyser-continue-project-context
触发：继续 QLanalyser 开发 / 恢复上下文 / 读取 AI_HANDOFF_CURRENT
用途：读取当前项目 handoff 文档、总结项目状态、识别当前风险、推荐下一步任务。

### qlanalyser-conversation-sync
触发：同步本轮对话 / 固化到开发依据
用途：将架构、模块设计、验收标准和跨会话结论固化为仓库文档。更新 docs/DECISIONS.md、docs/PROJECT_STATUS.md、docs/TASK_LOG.md、docs/architecture/*.md、docs/modules/*.md。

### qlanalyser-github-baseline-sync
用途：开发任务前 fetch GitHub origin/main 确认 workspace 不落后。提交前再次 fetch 检查冲突。不 force-push。
