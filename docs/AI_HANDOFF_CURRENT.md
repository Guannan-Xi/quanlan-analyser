# QLanalyser Online 当前 AI 接力依据

更新时间：2026-06-18

## 1. 当前唯一依据

本仓库 Markdown 文档是 QLanalyser Online 多对话协作的唯一开发依据。飞书只作为同步、评审和讨论窗口。

启动新对话时，优先读取：

1. `AGENTS.md`
2. `docs/AI_CONVERSATION_SYNC.md`
3. `docs/DECISIONS.md`
4. `docs/PROJECT_STATUS.md`
5. `docs/TASK_LOG.md` 最近记录
6. `docs/architecture/system_architecture.md`
7. `docs/architecture/version_detailed_design.md`
8. `docs/modules/analysis_modules_design_matrix.md`
9. 与当前任务相关的其他 `docs/architecture/*.md` 或 `docs/modules/*.md`

## 2. 当前产品边界

QLanalyser Online 是面向科研团队的 EEG 数据管理、分析交付与复现记录平台。当前 v0.1 Pilot 用于客户免费试用，不作为临床诊断系统。

## 3. 当前模块路线

分析实验室作为正式功能孵化区：

1. 单功能实验室开发
2. 输入输出交互完善
3. 测试数据验证
4. 科研输出验收
5. 小范围公测
6. 服务化 / 模块化
7. 合并进入正式主流程

实验室保持免登录；正式工作台保持登录 / 注册。

## 4. 当前同步规则

- 架构和模块设计写入仓库 docs。
- 飞书从仓库摘要生成。
- 多个对话开发前必须先读仓库当前依据。
- 重要结论写入 `docs/DECISIONS.md`。
- 任务完成写入 `docs/TASK_LOG.md` 和必要的状态文档。

## 5. 当前架构设计依据

本项目当前总纲级开发依据：

- `docs/architecture/system_architecture.md`
- `docs/architecture/version_detailed_design.md`
- `docs/modules/analysis_modules_design_matrix.md`

后续架构、版本和模块开发应先对齐这些文件，再进入代码实现。

## 6. 新对话启动提示词

```text
请继续 QLanalyser Online 项目。

请先读取仓库中的以下文件，不要依赖旧聊天记忆：
1. AGENTS.md
2. docs/AI_CONVERSATION_SYNC.md
3. docs/DECISIONS.md
4. docs/PROJECT_STATUS.md
5. docs/TASK_LOG.md 最近记录
6. docs/architecture/system_architecture.md
7. docs/architecture/version_detailed_design.md
8. docs/modules/analysis_modules_design_matrix.md
9. 与当前任务相关的其他 docs/architecture 或 docs/modules 文档

协作规则：
- 仓库 Markdown 文档是唯一开发依据。
- 飞书只作为同步和评审窗口。
- 先运行 git status --short --branch 和 git diff --stat。
- 不覆盖无关改动。
- 重要设计结论必须固化到仓库文档。
- 完成后给出修改文件、验证结果、风险点和下一步建议。
```
