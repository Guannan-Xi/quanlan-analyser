# QuanLan Analyser

中文名：在线脑电分析平台

GitLab repository slug: `quanlan-analyser`

定位：面向小白用户的在线脑电数据管理、计费、分析和结果交付平台。

重要安全约束：

- 不提交真实客户脑电数据、充值记录、邮箱收件人数据或隐私数据。
- 不提交运行日志、打包结果、临时分析输出。
- 可提交前端 MVP、部署文件、示例资产生成脚本、交接文档和状态说明。

## Spike 分析业务线

Spike sorting 与分析当前不属于 `web-main` 内部模块，而是工作区顶层的独立预研项目 `projects/spike-analysis`。该业务线面向神经电生理实验人员，当前状态为暂缓：不实现、不定价、不进入 QLanalyser 现有版本排期，也不向普通用户展示。

后续只有在获得合规、去标识化的真实 PLX 样本，确认客户问题并具备专项资源后，才重新启动需求和技术评估。若其中某项方法通过验证并晋级 QLanalyser 主平台，应接入现有项目、文件、任务、报告和账户边界，经 `backend/api/`、`backend/services/` 与 `worker/tasks/` 集成，不新增平行应用或重复服务入口。

任何后续方案仍不得包含临床诊断或治疗建议。SpikeInterface、Kilosort 和具体设备格式的适配范围、依赖与交付边界，必须基于真实样本验证后再决定。
