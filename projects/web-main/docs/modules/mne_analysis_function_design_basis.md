# MNE 分析功能设计依据

更新时间：2026-06-18

## 1. 文档定位

本文件是 QLanalyser Online 设计每个 EEG 分析功能时的 MNE 依据。后续所有对话在设计 QC、预处理、PSD、ERP、TFR、PAC、Connectivity、统计和报告能力前，先读本文件，再读对应模块详细设计。

本文件不替代 MNE 官方文档，也不把实验性高级分析直接标记为可生产交付能力。它把 MNE 文档和多模型审阅结果整理成项目可执行的设计约束。

依据来源：

- 项目依赖：`requirements.txt` 当前约束为 `mne>=1.8`。
- 当前本地环境核对：`mne 1.10.1`；`mne_connectivity` 和 `mne_bids` 未安装。
- 已核对的核心接口：`Raw.compute_psd`、`Epochs.compute_psd`、`Epochs.compute_tfr`、`mne.Epochs`、`mne.Evoked`、`mne.events_from_annotations`、`mne.find_events`、`mne.preprocessing.ICA`、`mne.Report`。
- 多模型审阅：Gemini、Grok、DeepSeek 对 MNE 设计范围、模块边界、失败模式和科研风险给出交叉意见；原始输出保存在 `.ai/` scratch，不作为仓库正式依据。

官方文档优先核对入口：

- MNE stable documentation: `https://mne.tools/stable/`
- Raw object: `https://mne.tools/stable/generated/mne.io.Raw.html`
- Events from annotations: `https://mne.tools/stable/generated/mne.events_from_annotations.html`
- Epochs: `https://mne.tools/stable/generated/mne.Epochs.html`
- Evoked: `https://mne.tools/stable/generated/mne.Evoked.html`
- Time-frequency: `https://mne.tools/stable/api/time_frequency.html`
- Preprocessing: `https://mne.tools/stable/api/preprocessing.html`
- Statistics: `https://mne.tools/stable/api/stats.html`

## 2. 总设计原则

1. MNE 对象是分析边界的核心：连续数据用 `mne.io.Raw`，分段数据用 `mne.Epochs`，平均诱发结果用 `mne.Evoked`，频谱结果用 `Spectrum`，时频结果用 TFR 对象。
2. `mne.Info` 是元数据主来源：采样率、通道名、通道类型、坏道、参考、滤波状态、montage、投影器和测量信息必须从 `Info` 读取或写回。
3. 事件必须显式建模：ERP、TFR、事件相关统计都必须记录 events 数组、`event_id`、事件来源、事件映射和无事件时的失败说明。
4. 分析模块不互相传递不可复现的内存对象。任务输出必须记录输入文件身份、参数、软件版本、处理流程和产物清单，必要时再写出派生 FIF 或表格。
5. 所有模块必须区分 `stable`、`beta`、`preview` 和 `custom-needed`。当前可执行能力不能暗示高级分析已经生产可用。
6. UI 面向客户时只展示必要信息，避免反复出现“QLanalyser / 分析 / 功能 / 模块 / 入口 / 设计”等重复文案；技术依据留在文档和报告方法部分。
7. 所有报告保留科研用途边界，不输出临床诊断、疾病判断或自动医学建议。

## 3. 跨模块复现契约

每个分析任务至少写出：

```text
result.json
manifest.json
log.txt
reproducibility/parameters.json
reproducibility/software_versions.json
reproducibility/workflow.json
reproducibility/method_description.txt
```

`parameters.json` 必须记录：

- 输入文件 ID、路径、大小、hash、原始格式。
- MNE 读取函数和读取参数，例如 `preload`、通道类型处理、stim 通道处理。
- 采样率、通道名、通道类型、坏道、montage、参考、滤波状态。
- 事件来源、events 数组摘要、`event_id`、epoch 时间窗、baseline、reject 规则。
- 当前模块所有显式参数和默认参数。
- 软件版本：Python、MNE、NumPy、SciPy、Pandas、FastAPI、项目版本或 commit。
- 输出文件列表和解释限制。

失败也必须写清楚：失败阶段、MNE 异常摘要、用户可理解原因、是否可以改参数重试、是否需要回到文件或实验记录。

## 4. 模块总览

| 模块 | 当前定位 | MNE / 依赖 | 输入 | 主要输出 | 下一步设计任务 |
| --- | --- | --- | --- | --- | --- |
| QC / 元数据 | v0.1 stable | `mne.io.read_raw_*`, `Raw.info`, `Raw.annotations` | EEG 原始文件 | 元数据、通道质量、事件摘要、QC 标记 | 补齐失败路径和质量阈值说明 |
| 预处理 | v0.1 preview-to-stable 基础能力 | `filter`, `notch_filter`, `resample`, `set_eeg_reference`, `interpolate_bads`, `ICA` | Raw + QC 结果 + 参数 | 清洗预览、处理步骤、可选派生 FIF | 明确哪些步骤只预览、哪些步骤可写入正式流程 |
| PSD | v0.1 stable | `Raw.compute_psd`, `Epochs.compute_psd`, `Spectrum` | Raw 或 Epochs | 频谱、band power、topomap、CSV/JSON | 稳定 Welch 默认参数和 bandpower 合同 |
| ERP | event 条件下 beta/stable | `events_from_annotations`, `find_events`, `Epochs`, `Evoked`, `get_peak` | Raw + events + event_id | Epoch 统计、Evoked、峰值/时间窗指标 | 强化事件映射、baseline、reject 和失败提示 |
| TFR / ERSP / ITC | v0.1 preview | `Epochs.compute_tfr`, Morlet / multitaper | Epochs + 频率设计 | power、ITC、时频图 | 明确频率、`n_cycles`、baseline、decim 和统计策略 |
| PAC / CFC | custom-needed preview | MNE core 不提供完整生产 PAC 流程 | 清洗后的 Raw/Epochs | PAC 矩阵、surrogate 结果 | 设计自定义算法、null model、边界效应控制 |
| Connectivity | preview，需新增依赖 | `mne-connectivity` | Epochs 或 source/ROI 数据 | coherence、PLV、PLI、wPLI 等 | 评估依赖、参考策略、体积传导风险 |
| Statistics | preview | `mne.stats` | subject-level 汇总 | cluster/permutation 结果 | 明确 subject 是统计单位，不把 trial 当被试 |
| Reports / BIDS | 报告 v0.1，BIDS 后续 | `mne.Report`, later `mne-bids` | 任务产物 | HTML/ZIP/方法/复现材料 | 先稳定当前报告包，BIDS 放到 v1 路线 |

## 5. QC / 元数据

### MNE 映射

- 读取：按文件类型调用 `mne.io.read_raw_edf`、`read_raw_bdf`、`read_raw_fif`、`read_raw_brainvision`、`read_raw_eeglab`、`read_raw_cnt` 等。
- 元数据：`raw.info`、`raw.ch_names`、`raw.get_channel_types()`、`raw.annotations`、`raw.times`。
- 事件：优先从 annotations 或 stim 通道提取，并记录来源。

### 参数

- `preload`：服务端分析通常需要 `True`，但大文件应限制容量。
- 支持格式和读取器。
- 采样率下限、最小时长、最大通道数、幅值阈值、平线阈值。
- montage 或通道命名标准，只能作为检查和提示，不能自动假设真实电极位置正确。

### 输出

- 文件格式、大小、hash、读取器。
- 采样率、时长、通道数、通道类型分布、坏道初判。
- annotations 和 events 摘要。
- 疑似平线、极端振幅、缺失数据、过短记录、采样率过低等 QC flag。

### 失败和风险

- 文件损坏或格式不支持。
- 没有 EEG 通道或通道类型识别错误。
- annotations 存在但无法映射为目标事件。
- 自动坏道只是提示，必须允许用户复核。

## 6. 预处理

### MNE 映射

- 滤波：`raw.filter(l_freq, h_freq)`。
- 陷波：`raw.notch_filter(freqs)`。
- 重采样：`raw.resample(sfreq)`。
- 重参考：`raw.set_eeg_reference(ref_channels)`。
- 坏道插值：`raw.interpolate_bads()`。
- ICA：`mne.preprocessing.ICA`，fit 后记录排除成分并 apply。

### 参数

- 高通、低通、陷波频率、滤波方法和相位策略。
- 目标采样率。
- 参考方式：average、指定参考通道、保持原参考。
- 坏道列表和插值开关。
- ICA 成分数、算法、随机种子、最大迭代数、排除成分。

### 输出

- 处理步骤序列和每一步参数。
- 前后对比图、滤波预览、坏道列表、ICA 成分摘要。
- 可选派生 FIF，仅在正式流程中写入；体验中心预览不能改写原始上传文件。

### 失败和风险

- 滤波参数越界或导致数据过度失真。
- 重采样可能影响事件时间，事件应先提取并记录映射策略。
- 平均参考前未排除坏道会扩散伪迹。
- ICA 数据太短、通道太少或不收敛时必须失败并提示。

## 7. PSD

### MNE 映射

- 连续数据：`raw.compute_psd(method="welch", fmin, fmax, picks, reject_by_annotation=True, **method_kw)`。
- 分段数据：`epochs.compute_psd(method="multitaper" or "welch", fmin, fmax, picks, **method_kw)`。
- 输出对象：MNE `Spectrum`，再转为频率数组、通道数组、功率矩阵和 bandpower 表。

### 参数

- `method`：v0.1 默认 Welch；multitaper 作为高级选项或后续。
- `fmin`、`fmax`，不得超过 Nyquist 频率。
- Welch：`n_fft`、`n_overlap`、`window`。
- Multitaper：`bandwidth`、`adaptive`、`low_bias`。
- bands：delta、theta、alpha、beta、gamma 等频段必须可配置，默认值写入参数。
- 输出：absolute power 和 relative power 都可保留，UI 应优先解释 relative power 的适用边界。

### 输出

- `tables/psd_by_channel.csv`。
- `tables/bandpower_by_channel.csv`。
- `reproducibility/psd_summary.json`。
- 频谱曲线、频段 topomap、方法说明。

### 失败和风险

- `n_fft` 大于有效数据段长度。
- `fmax >= sfreq / 2`。
- 频段定义重叠或超出有效频率。
- 绝对功率受头皮阻抗、颅骨、参考方式影响很大；不能直接作跨个体临床解释。

## 8. ERP

### MNE 映射

- 事件提取：`mne.events_from_annotations(raw)` 或 `mne.find_events(raw)`。
- 分段：`mne.Epochs(raw, events, event_id, tmin, tmax, baseline, reject, preload=True)`。
- 平均：`epochs[condition].average()` 得到 `mne.Evoked`。
- 峰值：`evoked.get_peak()` 或在指定时间窗和 ROI 上自定义均值/峰值指标。

### 参数

- event source、`event_id` 映射、目标 condition。
- `tmin`、`tmax`、baseline。
- reject 阈值、flat 阈值、`reject_by_annotation`。
- ROI 通道、峰值搜索时间窗、极性。

### 输出

- 每个 condition 的 epoch 数、被拒绝数量、drop log 摘要。
- Evoked 波形、条件对比图、ROI 时间窗均值、峰值潜伏期和幅值。
- 事件映射和 baseline/reject 参数。

### 失败和风险

- 无事件、事件映射为空、目标 condition 没有有效 trial。
- baseline 区间超出 epoch 时间窗。
- reject 阈值过严导致有效 trial 太少。
- 单个 trial 不能当作被试；组统计必须按 subject 汇总。

## 9. TFR / ERSP / ITC

### MNE 映射

- 基础对象必须是 Epochs。
- MNE 1.10 可使用 `epochs.compute_tfr(method, freqs, output="power", return_itc=True/False, decim, **method_kw)`。
- Morlet 需要设计 `freqs` 和 `n_cycles`；multitaper 需要设计 time-bandwidth / bandwidth。

### 参数

- condition、epoch 时间窗、baseline 和 baseline correction 模式。
- `freqs`、`n_cycles`、method、decim、picks。
- 输出 power、ITC 或 averaged power。
- 统计和可视化色标必须固定规则。

### 输出

- 时频矩阵、通道/ROI 汇总、power 图、ITC 图。
- baseline 参数和 decimation 参数。
- 内存和耗时记录。

### 失败和风险

- TFR 对内存敏感，必须限制通道数、epoch 数、频率数和采样率。
- baseline 选择会强烈影响 ERSP 解释。
- 多频率、多时间点、多通道需要多重比较控制；v0.1 只能 preview。

## 10. PAC / CFC

### 定位

PAC 不应被写成 MNE core 已经直接提供的稳定功能。它需要项目自定义实现或引入专门库，并接受科研方法审查。

### 必须设计

- 低频相位频段、高频振幅频段、滤波策略和边缘裁剪。
- Hilbert 或其他相位/振幅提取方法。
- PAC 指标，例如 modulation index 或 mean vector length。
- surrogate/null model、置换次数、显著性阈值。
- 防止非正弦波形导致虚假 PAC 的提示。

### 风险

- 滤波边缘效应、相位估计误差、非正弦信号、共同驱动和肌电伪迹都可能制造假阳性。
- v0.1 不进入 stable，只能作为设计评审和科研预研。

## 11. Connectivity

### 定位

Connectivity 应依赖 `mne-connectivity`，当前项目未安装该依赖，所以不能标记为 v0.1 可执行。

### 必须设计

- 输入是 sensor-level Epochs 还是 source/ROI 数据。
- 频段、epoch、参考方式、坏道策略。
- 指标：coherence、imaginary coherence、PLV、PLI、wPLI 等。
- 连接矩阵、阈值、网络图和 ROI 汇总。

### 风险

- sensor-level connectivity 容易受体积传导和参考方式影响。
- coherence 和 PLV 对零相位同步敏感；UI 和报告应优先提示 PLI/wPLI 等相位滞后指标的边界。
- 阈值选择会改变网络结论，必须写入参数并避免过度解释。

## 12. Statistics / Reports / BIDS

### Statistics

- MNE `mne.stats` 可用于 permutation 和 cluster-based 统计。
- 统计单位必须是 subject；trial-level 只能作为 subject 内估计。
- 必须记录 contrasts、threshold、tail、n_permutations、adjacency 和 random seed。

### Reports

- `mne.Report` 可作为后续报告组织参考，但当前项目已有 HTML/ZIP 报告契约，先稳定项目报告包。
- 报告必须包含方法、参数、软件版本、数据质量、失败说明和非临床边界。

### BIDS

- BIDS 导出应放到 v1 路线，并评估 `mne-bids`。
- 当前 v0.1 不承诺完整 BIDS 工作流。

## 13. 当前开发顺序

1. 先稳定 QC：读取、元数据、事件摘要、通道质量、失败路径。
2. 再稳定预处理预览：滤波、notch、重参考、坏道、ICA 的参数和风险边界。
3. 然后稳定 PSD：Welch 默认参数、bandpower 输出、图表和报告方法。
4. ERP 以事件存在为前提：先把事件映射、baseline、reject、drop log 做清楚。
5. TFR 只做 preview 详细设计，不承诺 production stable。
6. PAC 和 Connectivity 先做方法评审和依赖评估，再决定是否进入 beta。
7. 统计、BIDS、正式队列和生产化报告在 v0.2/v1 继续推进。

## 14. 给其他开发对话的启动清单

新对话开始设计任一分析功能前，必须确认：

- 已执行 GitHub baseline 同步，并确认本地不是落后状态。
- 已阅读 `docs/architecture/system_architecture.md`、`docs/architecture/version_detailed_design.md`、`docs/modules/analysis_modules_design_matrix.md` 和本文件。
- 已明确该功能是 stable、beta、preview 还是 custom-needed。
- 已列出输入、参数、MNE API、输出、失败模式、解释风险和验收脚本。
- 完成后只提交本次相关文件；如远程或本地已有差异，先提醒用户确认，不自动覆盖。
