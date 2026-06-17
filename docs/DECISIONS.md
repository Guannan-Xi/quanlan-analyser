# QLanalyser Online 决策记录

## 1. 产品命名

产品名统一为：

`QLanalyser Online`

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



