# QLanalyser 阿里云癫痫演示发布记录

> 发布日期：2026-07-21（Asia/Shanghai）  
> 用途：对外演示数据管理、EEG 波形预览、癫痫样事件科研筛查、人工复核和结果导出  
> 状态：公网端到端验收通过；本地相关改动尚未 commit、尚未 push

## 1. 演示入口

- 前端：`http://39.97.248.225/?customer_demo=auto&workbench=epilepsy_ml&api=http%3A%2F%2F39.97.248.225%2Fapi`
- API：`http://39.97.248.225/api`
- Health：`http://39.97.248.225/api/health`
- 2026-07-21 复核：health 返回 `status=ok`

账号密码不得写入仓库或本文。由演示负责人通过受控渠道提供，并在演示结束后轮换。

## 2. 演示范围和边界

本环境已验收以下流程：

1. 创建项目并上传演示 EDF。
2. 数据管理、元数据读取、波形预览和数据准备确认。
3. 启动癫痫样事件分析并查看候选事件、时间轴和频谱结果。
4. 保存人工复核、发布复核结果并生成报告 ZIP。

只允许使用仓库内的合成 EDF。禁止上传真实客户数据、真实受试者数据、HE 数据或任何可识别个人的信息。本功能仅用于科研筛查支持，不作临床诊断、治疗建议或医疗决策。

## 3. 固定演示数据

- 文件：`work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_60s.edf`
- 类型：完全合成 EDF
- 参数：5 通道、250 Hz、60 秒
- SHA256：`63bfda3dcaec7c77ceb11752e027f0ce3d03a29b0fc5e680933cc163c61405d2`
- 预期候选事件：25–35 秒
- 预期 Stage Code：`000001100000`

## 4. 公网验收结果

浏览器 E2E 于 `2026-07-21T06:30:01.912Z` 完成，脚本退出码为 0，33 项检查全部为 `true`。

关键对象：

- 项目：`proj_d33037d0fe81`
- 文件：`eeg_150778c8957d`
- 数据准备计划：`prep_7bbeb4f21c72`
- 分析任务：`task_d43e482ae959`，状态 `completed`
- 报告：`report_d577b93dc678`
- ZIP：154190 bytes，包含事件时间轴和频谱图

覆盖范围包括上传授权、数据准备、Stage Code、25–35 秒候选事件、STFT 产物、人工复核、两张鉴权结果图、报告打包，以及 4 个预期的 422/404 负向业务校验。

证据：

- `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json`
- `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/04_results_review_package.png`

归档 JSON 内有历史中文乱码字符串，PowerShell `ConvertFrom-Json` 严格解析会失败；验收脚本本身已退出 0，顶层 33 项检查均为真。后续应单独清理证据生成时的编码，不应改写本次不可变发布结论。

## 5. 本次线上补丁和回滚

- 线上前端 `app.js` SHA256：`63d83a87c85c8c0f88e61703fd3334c8c6177e722f929d1c84ff71ce2d51c320`
- 服务器回滚备份：`/opt/qlanalyser/backups/frontend-app-pre-auth-images-20260721T142800Z.js`
- 本地部署补丁基线：`work/deploy_patch/aliyun_app.js`、`work/deploy_patch/aliyun_web_app.current.js`

回滚时，在服务器上先校验当前 `/usr/share/nginx/html/app.js` 的 SHA256，再用上述备份恢复，校验 Nginx 配置并 reload，随后重新运行公网 health 和浏览器 E2E。不要用本地整个 `frontend/app.js` 覆盖线上文件。

## 6. 已知风险

- 后端分析目前仍在 HTTP 请求内同步执行；`worker/` 尚未接入正式异步任务链路。
- JSON registry 在多实例下存在一致性风险。
- `.accounts.lock` 存在超时风险。
- 当前工作树包含大量未提交的并行改动；本次线上补丁不等于某个干净 Git commit 的完整部署。
- 当前仍为 HTTP 公网入口，正式长期演示前应配置域名、HTTPS、访问控制、日志脱敏和备份恢复演练。

## 7. Git 状态

发布验收发生在本地脏工作树对应的受控补丁基础上。本记录创建时：

- 分支：`feature/epilepsy-full-flow-backend-20260706`
- 相对远端：ahead 1
- 本次相关改动：未 commit、未 push

接手人不得把当前整个脏工作树一次性提交或整体部署。应先按功能边界拆分、复测、审阅，再形成可回滚的小提交。
