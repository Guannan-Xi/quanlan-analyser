# 新手友好分析功能蓝图

更新时间：2026-06-18

## 1. 文档定位

本文件给开发对话和体验中心对话使用。目标是把每个 EEG 分析功能设计成“脑电分析小白也能完成，并且越用越理解”的产品能力。

开发任何分析功能前，先读：

- `docs/modules/mne_analysis_function_design_basis.md`
- `docs/modules/analysis_modules_design_matrix.md`
- `docs/modules/beginner_learning_analysis_design.md`
- 当前功能的详细设计文档，例如 `docs/modules/erp_design.md`

本文件不替代专家审稿，也不承诺自动生成顶刊结论。它规定产品必须提供足够证据链，让结果接近严肃科研交付所需：数据可查、参数可追、图表可读、解释克制、失败诚实。

## 2. 统一体验结构

每个功能都按四层展示。

| 层级 | 给用户看到什么 | 后端必须返回什么 |
| --- | --- | --- |
| 示例学习 | 用内置示例数据跑一遍完整流程 | 示例数据 ID、固定参数、预期结果、解释边界 |
| 引导运行 | 一次只问一个必要问题 | 参数 schema、默认值来源、用户确认记录 |
| 结果解释 | 把数字和图翻译成可理解结论 | summary、tables、figures、method、warnings |
| 专家复核 | 展开高级参数和下载复现包 | manifest、log、software_versions、workflow |

页面不应把参数墙放在第一屏。默认先给“推荐设置”，再允许用户展开高级参数。

## 3. 统一结果解释卡

每个分析结果旁边必须有 5 张短卡片。

| 卡片 | 内容 |
| --- | --- |
| 结果 | 系统实际发现了什么，用一两句话说清楚。 |
| 依据 | 这个结论来自哪些通道、频段、事件、时间窗或 trial。 |
| 质量 | 数据是否足够继续解释，异常在哪里。 |
| 风险 | 哪些因素可能改变结论，例如参考、伪迹、事件语义、trial 数。 |
| 下一步 | 建议继续、调整参数、回到 QC、请专家复核或停止解释。 |

这些卡片不能重复介绍软件是什么，也不能使用“顶刊”“诊断”“异常脑电”等夸大表述。

## 4. 功能设计矩阵

| 功能 | 新手要回答的问题 | 系统默认动作 | 必须展示的结果 | 高可信门槛 | 当前下一步 |
| --- | --- | --- | --- | --- | --- |
| QC | 这份数据能不能继续用？ | 读取 metadata、检查 EEG 通道、采样率、时长、平线和极端幅值 | 文件概览、通道质量、事件概览、是否可继续 PSD/ERP | 文件可读、EEG 通道存在、关键异常可解释 | 把“可继续/需复核/停止”的白话建议接到前端 |
| PSD | 主要频段能量是什么样？ | 使用 EEG 通道计算 Welch PSD 和默认频段功率 | 频谱、频段功率表、通道 x 频段表 | QC 通过、频率参数合法、伪迹风险可见 | 增加图表和参数失败路径验收 |
| ERP | 不同事件后的反应是否不同？ | 从 annotations 提取事件，按条件 epoch，按 ROI 提取 N100/P200/P300 | 事件映射、有效 epoch、ROI 指标、drop log | 事件语义已确认、ROI/参考/baseline 可见、trial 数足够 | 前端补事件确认步骤和 ROI 选择控件 |
| TFR | 事件前后频率随时间怎么变？ | 仅 preview，基于 epoch 计算时频功率 | 时频图、baseline 设置、频率/n_cycles | 事件、baseline、统计单位确认 | 先完成详细设计，不进入 stable |
| PAC | 低频相位和高频振幅是否耦合？ | 仅 preview/custom-needed，不用 MNE core 直接承诺生产 PAC | PAC 矩阵、surrogate/null model | 有清洗数据、足够时长、替代分布 | 先做方法评审和算法选择 |
| Connectivity | 通道/区域之间是否同步？ | 仅 preview，需评估 `mne-connectivity` 和体积传导风险 | metric 表、频段、连接图 | 参考策略、体积传导、统计策略清楚 | 暂不作为 v0.1 stable |

## 5. ERP 当前可靠性基线

ERP 已从“所有 EEG 通道平均”改为 ROI-aware 指标：

- N100 默认 ROI：`Fz,Cz`
- P200 默认 ROI：`Fz,Cz,Pz`
- P300 默认 ROI：`Pz,P3,P4`

如果文件缺少这些通道，runner 会退回到可用 EEG 通道，并在 `missing_roi_channels` 和 `roi_by_component` 中记录。前端必须把实际使用的 ROI 展示给用户。

ERP 输出必须包含：

- `tables/erp_metrics.csv`：包含 `reference`、`roi_name`、`roi_channels`。
- `reproducibility/event_confirmation.json`：记录事件来源、发现的 event_id、选择的 event_id、是否确认。
- `reproducibility/drop_log_summary.json`：记录输入事件数、保留 epoch 数、丢弃 epoch 数和原因。

事件未确认时，界面可以显示结果，但不能用高可信语气解释条件差异。

## 6. 示例数据验收

内置教学数据来自：

- `scripts/generate_teaching_oddball_case.py`
- `work/learning_case/data/teaching_oddball.edf`

固定设计：60 秒、250 Hz、8 个 EEG 通道、24 个 standard、12 个 target、后部 10 Hz alpha、target 增强 P300-like 响应。

当前示例验收标准：

1. QC 返回 `passed`。
2. PSD 中 alpha 频段为主导频段。
3. ERP 默认平均参考 + P300 ROI 下，target P300 高于 standard P300。
4. ERP 输出 event confirmation 和 drop log。
5. 所有输出进入 `result.json`、`manifest.json`、`log.txt` 和 reproducibility 目录。

## 7. 前端落地清单

- [ ] 体验中心首屏提供“用示例数据学习”和“上传我的数据”。
- [ ] QC 完成后给出“可继续 PSD / 可继续 ERP / 需要先确认事件”的建议。
- [ ] PSD 展示频谱和频段功率时，同时展示频段定义和风险提示。
- [ ] ERP 运行前必须显示事件映射确认步骤。
- [ ] ERP 结果必须显示 ROI、参考、baseline、有效 epoch 和 drop log。
- [ ] 所有功能都提供下载复现包入口。
- [ ] 专家参数默认折叠，展开后每个参数有默认来源和风险说明。

## 8. 给开发对话的交接语

开发任一分析功能时，先同步 GitHub 最新状态，再阅读本文件和对应模块文档。不要只做静态卡片；每个功能都要形成可运行任务、可下载产物、可复核参数和失败状态。遇到本地或远端差异，先提醒用户确认，不自动覆盖。
