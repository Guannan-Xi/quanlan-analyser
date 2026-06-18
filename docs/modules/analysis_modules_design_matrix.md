# QLanalyser Online 分析模块设计矩阵

更新时间：2026-06-18

## 1. 文档定位

本文件是分析模块详细设计的索引和矩阵，供实验室评审、后端实现、前端交互和科研验收共同使用。

模块状态定义：

- stable：v0.1 正式可执行或必须稳定。
- beta：条件满足时可执行，但解释边界更严格。
- preview：实验室展示和设计评审，不承诺后端生产执行。

MNE 设计总依据：

- `docs/modules/mne_analysis_function_design_basis.md`：所有 EEG 分析功能的 MNE 对象、API、输入输出、失败模式和科研风险基线。

## 2. 模块总览

| 模块 | 当前状态 | v0.1 后端 | 实验室 | 主流程 | 下一步 |
| --- | --- | --- | --- | --- | --- |
| QC | stable | 已启用 | 已展示 | 应进入主流程 | 补独立设计文档和 contract 测试 |
| PSD | stable | 已启用 | 已展示 | 应进入主流程 | 稳定 Welch 参数和 bandpower 交付 |
| ERP | beta/stable when events exist | 已启用但依赖事件 | 已展示 | 条件进入主流程 | 强化事件语义和失败提示 |
| TFR | preview | 未启用 | 已展示 | 不进入 stable | 完成 epoch/baseline/statistics 设计 |
| PAC | preview | 未启用 | 已展示 | 不进入 stable | 完成 surrogate/null model 设计 |
| Connectivity | preview | 未启用 | 已展示 | 不进入 stable | 完成参考/体积传导/metric 审查 |

## 3. QC 模块设计

### 用户目标

研究者上传 EEG 后，先判断文件是否可读、通道是否合理、时长和采样率是否满足后续分析、是否存在疑似坏道或极端振幅。

### 输入

- EEG 原始文件：EDF / BDF / FIF / BrainVision / SET / CNT。
- QC 阈值：最低采样率、最短时长、平线阈值、极端振幅阈值。
- 可选上下文：任务范式、实验记录、预处理备注。

### MNE / 算法映射

- `mne.io.Raw` / format-specific reader。
- metadata summary。
- per-channel peak-to-peak amplitude checks。
- annotations / channel types inspection。

### 输出

- `reproducibility/qc_summary.json`
- `reproducibility/parameters.json`
- `reproducibility/software_versions.json`
- `reproducibility/workflow.json`
- `reproducibility/method_description.txt`
- `result.json`
- `manifest.json`
- `log.txt`

### 验收

- 空文件、不支持格式、无 EEG 通道必须给出可读失败原因。
- QC 只能给风险提示，不替代人工复核。
- 输出文件可进入报告包。

## 4. PSD 模块设计

### 用户目标

研究者对静息态或连续 EEG 数据计算频谱和频段功率，用于受试者级或组水平统计前的数据交付。

### 输入

- 可读 EEG 文件。
- 频率范围：默认 1-40 Hz。
- 频段定义：delta/theta/alpha/beta/gamma_low。
- 可选滤波、notch、通道选择和时间窗。

### MNE / 算法映射

- `Raw.compute_psd(method="welch")`。
- EEG channel picks。
- band average aggregation。

### 输出

- `tables/band_power.csv`
- `tables/channel_band_power.csv`
- `reproducibility/psd_summary.json`
- `reproducibility/parameters.json`
- `reproducibility/method_description.txt`
- `result.json`
- `manifest.json`
- `log.txt`

### 验收

- 至少一个可用 EEG 通道。
- Welch 参数、频段定义和单位必须可追溯。
- 解释边界必须提示参考、滤波、肌电和个体 alpha peak 风险。

## 5. ERP 模块设计

### 用户目标

研究者基于已有 annotations/events 计算 ERP/P300 等成分指标，导出条件级和成分级表格。

### 输入

- 可读 EEG 文件。
- 事件标记 / annotations。
- `event_id`、`tmin`、`tmax`、baseline、reject threshold。
- 成分窗口和通道/ROI 约定。

### MNE / 算法映射

- `mne.events_from_annotations`。
- `mne.Epochs`。
- `mne.Evoked`。
- component peak amplitude / latency extraction。

### 输出

- `tables/erp_metrics.csv`
- `reproducibility/erp_summary.json`
- `reproducibility/parameters.json`
- `reproducibility/method_description.txt`
- `result.json`
- `manifest.json`
- `log.txt`

### 验收

- 无事件必须清晰失败。
- 事件语义不清时不得给确定性科学解释。
- 统计单位必须是 subject，不把 trial 当独立被试。

## 6. TFR 模块设计

### 当前状态

preview。v0.1 只在实验室展示，不作为正式后端 stable 功能。

### 进入 beta 前要求

- 明确 epoch 设计。
- 明确 frequencies、n_cycles、baseline 模式、decimation。
- 明确 power / ITC 输出。
- 明确多重比较或 cluster/permutation 策略。
- 明确图表色标、baseline 和 ROI。

### 风险

- baseline 选择影响解释。
- 时间频率平滑影响时频分辨率。
- 多重比较风险高。

## 7. PAC 模块设计

### 当前状态

preview。v0.1 只展示设计，不承诺后端生产执行。

### 进入 beta 前要求

- 明确相位频段和振幅频段。
- 明确滤波长度、Hilbert 边界处理。
- 明确 surrogate/null distribution。
- 明确 ROI、窗口和多重比较策略。

### 风险

- 非正弦波形可产生假 PAC。
- 肌电、眼动和滤波边界效应会造成假阳性。
- 没有 surrogate 不允许 stable。

## 8. Connectivity 模块设计

### 当前状态

preview。v0.1 只展示设计，不承诺后端生产执行。

### 进入 beta 前要求

- 明确 connectivity metric。
- 明确参考方式。
- 明确 volume conduction 控制。
- 明确频段、窗口、节点/ROI 和阈值。
- 明确 null model 和图指标。

### 风险

- 参考方式强烈影响连接性结果。
- 体积传导会造成伪连接。
- 阈值选择会改变网络结论。

## 9. 模块合并主流程准入

一个模块从实验室进入正式工作台前必须满足：

- [ ] `docs/modules/<module>_design.md` 完整。
- [ ] 前端实验室输入、参数、MNE、输出、风险展示完整。
- [ ] 后端 runner 或明确 disabled 状态完整。
- [ ] 输出契约包含 `result.json`、`manifest.json`、`log.txt`。
- [ ] 报告包可复核。
- [ ] 验收脚本覆盖成功和失败路径。
- [ ] 科研边界和非临床说明可见。

## 10. 下一步

优先拆出独立文档：

1. `docs/modules/qc_design.md`
2. `docs/modules/psd_design.md`
3. `docs/modules/erp_design.md`
4. 基于 `docs/modules/mne_analysis_function_design_basis.md` 逐个补齐 PSD、ERP、TFR、PAC、Connectivity 的输入、参数、MNE API、输出、失败模式和验收脚本。
