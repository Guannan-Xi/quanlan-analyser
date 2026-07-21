# QLanalyser Online 分析模块设计矩阵

更新时间：2026-06-18

## 1. 文档定位

本文件是分析模块详细设计的索引和矩阵，供实验室评审、后端实现、前端交互和科研验收共同使用。

模块状态定义：

- stable：v0.1 正式可执行或必须稳定。
- beta：条件满足时可执行，但解释边界更严格。
- preview：实验室展示和设计评审，不承诺后端生产执行。

MNE / 学习体验设计总依据：

- `docs/modules/mne_analysis_function_design_basis.md`：所有 EEG 分析功能的 MNE 对象、API、输入输出、失败模式和科研风险基线。
- `docs/modules/beginner_learning_analysis_design.md`：面向脑电分析新手的学习式流程、示例 EDF 验证结果和可靠性交付要求。
- `docs/modules/beginner_friendly_analysis_function_blueprint.md`：面向开发对话的 QC、PSD、ERP、TFR、PAC、Connectivity 新手友好功能蓝图。

## 2. 模块总览

| 模块 | 当前状态 | v0.1 后端 | 实验室 | 主流程 | 下一步 |
| --- | --- | --- | --- | --- | --- |
| QC | stable | 已启用 | 已展示 | 应进入主流程 | 补独立设计文档和 contract 测试 |
| PSD | stable | 已启用 | 已展示 | 应进入主流程 | 按 `docs/modules/psd_design.md` 补参数失败路径和图表验收 |
| ERP | beta/stable when events exist | 已启用但依赖事件 | 已展示 | 条件进入主流程 | 前端补事件确认、ROI 选择和 drop log 展示 |
| Epilepsy STD / 癫痫样事件筛查 | internal_validation | 已启用 STD runner | 已展示 | 条件进入主流程 | 后续补 ML asset validation、事件复核编辑器和独立设计文档 |
| TFR | beta | 已启用 | 已展示 | 条件进入主流程 | 补 epoch/baseline/statistics 与 TFR 结果复核 |
| Multitaper PSD/TFR | beta | 已启用 | 已展示 | 条件进入主流程 | 完成 multitaper PSD 与 event-locked TFR 的参数、输出与验收 |
| PAC | beta | 已启用 | 已展示 | 条件进入主流程 | 完成 surrogate/null model 设计 |
| Connectivity | beta | 已启用 | 已展示 | 条件进入主流程 | 完成参考/体积传导/metric 审查 |

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

详细设计文档：

- `docs/modules/psd_design.md`

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

### Band Power alias

Band Power 在 07 主线中只作为 PSD 的 UI 视图/别名，不是独立后端模块。前端可显示 `Band Power`，但任务提交仍必须使用 `module_name=psd`、`workflow_id=resting_psd`，输出复用 `tables/band_power.csv`、`tables/channel_band_power.csv` 和 `figures/psd_band_power.svg`。不得新增 Band Power API、runner、router、IPC 或 Headroom 通道。

## 5. ERP 模块设计

详细设计文档：

- `docs/modules/erp_design.md`

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

## 6. Epilepsy STD / 癫痫样事件筛查模块设计

### 当前状态

internal_validation。当前只启用 STD 阈值版 runner，作为单记录、单 EEG 通道的癫痫样事件科研筛查辅助，不启用 ML 模型，不输出诊断、治疗建议、临床分诊或发作确认。

### 用户目标

研究者在非医疗科研/CRO 场景中，对长时程 EEG 进行可复现的高 RMS 阈值事件标记，得到候选事件、epoch 级分数和固定窗口统计，用于后续人工复核、算法验证或报告附录。

### 输入

- EEG 原始文件：EDF / BDF / FIF / BrainVision / SET / CNT。
- 可选 EEG 通道：未指定时选择第一个可用 EEG 通道。
- STD 阈值参数：`std_factor`、`rms_window_samples`、`epoch_length_sec`。
- 事件合并参数：`merge_gap_epoch_num`、`min_event_epochs`、`event_window_sec`。
- 可选坏道列表：不存在的坏道名必须报错，避免静默忽略。

### MNE / 算法映射

- `mne.io.Raw` 读取并 preload。
- 选取一个 EEG 通道后计算 sliding RMS：`sqrt(convolve(data**2, ones(window)/window, mode="same"))`。
- 阈值定义：`mean(RMS) + std_factor * std(RMS)`。
- 将超过阈值的 sample 映射到固定长度 epoch，再按 `merge_gap_epoch_num` 合并邻近候选 epoch，并用 `min_event_epochs` 过滤过短事件。

### 输出

- `tables/epilepsy_epoch_scores.csv`
- `tables/epilepsy_events.csv`
- `tables/epilepsy_window_stats_30min.csv`
- `reproducibility/epilepsy_summary.json`
- `reproducibility/parameters.json`
- `reproducibility/method_description.txt`
- `reproducibility/scope_contract.json`
- `result.json`
- `manifest.json`
- `log.txt`

### 验收

- 无 EEG 通道、坏道名不存在、请求非 EEG 通道、`method != std_threshold` 必须给出可读失败原因。
- 输出契约必须包含 3 个表格、summary、参数、方法说明、scope contract、manifest/result/log。
- `epilepsy_epoch_scores.csv` 必须包含 `is_event_epoch`，便于区分超过阈值的 epoch 与合并过滤后的事件 epoch。
- 前端入口必须提交 `module_name=epilepsy`、`workflow_id=epilepsy_std_threshold`，不得提交 `band_power` 或新建 router/IPC 通道。
- 所有用户可见文案必须标注科研筛查辅助，不能出现诊断、治疗建议、临床决策或发作确认承诺。

### 风险

- STD 阈值对肌电、运动伪迹、参考方式和滤波设置敏感，不能单独解释为癫痫事件。
- 单通道筛查会丢失空间分布信息，需要人工复核和多通道上下文。
- ML 版需要模型资产、依赖、sha256、训练/验证来源和漂移监控，必须作为后续独立切片进入。

## 7. TFR 模块设计

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

## 8. PAC 模块设计

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

## 9. Connectivity 模块设计

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

## 10. 模块合并主流程准入

一个模块从实验室进入正式工作台前必须满足：

- [ ] `docs/modules/<module>_design.md` 完整。
- [ ] 前端实验室输入、参数、MNE、输出、风险展示完整。
- [ ] 后端 runner 或明确 disabled 状态完整。
- [ ] 输出契约包含 `result.json`、`manifest.json`、`log.txt`。
- [ ] 报告包可复核。
- [ ] 验收脚本覆盖成功和失败路径。
- [ ] 科研边界和非临床说明可见。

## 11. 下一步

优先拆出独立文档：

1. `docs/modules/qc_design.md`
2. `docs/modules/psd_design.md`
3. `docs/modules/erp_design.md`（已建立，下一步补事件确认和 drop log）
4. `docs/modules/epilepsy_std_design.md`（后续独立补齐 STD 阈值、ML 禁用状态、事件复核和非医疗边界）。
5. 基于 `docs/modules/mne_analysis_function_design_basis.md` 逐个补齐 PSD、ERP、Epilepsy STD、TFR、PAC、Connectivity 的输入、参数、MNE API、输出、失败模式和验收脚本。
6. 基于 `docs/modules/beginner_friendly_analysis_function_blueprint.md` 增加示例学习模式、结果解释卡片和可靠性检查。
