# QC 数据质量控制模块服务化设计

更新时间：2026-06-18  
状态：实验室 stable 设计稿；后端已有 `metadata_qc` 基础能力，待补齐数据预览、滤波预览和波形快照服务。

## 1. 定位

QC 不是卡片示意页，也不是只输出一个质量结论的摘要模块。QC 是研究者进入 QLanalyser Online 后的第一个真实分析服务，承担三件事：

1. 判断 EEG 文件是否可读、是否满足后续分析的最低条件。
2. 让研究者第一眼看见数据本身，包括原始波形、通道、事件/注释、时间窗和采样信息。
3. 提供可复核的数据预览能力，包括带通/陷波预览、原始波形截取和预览区域快照。

QC 的输出不能替代人工复核。它负责暴露风险、生成证据和给出后续分析建议；临床诊断、疾病判断和不可逆预处理结论不属于 QC。

## 2. 服务化边界

实验室页面只做入口和交互编排。QC 能力必须封装成可被正式工作台调用的服务。

### 2.1 服务包

| 服务 | job_type | v0.1 状态 | 目标 |
| --- | --- | --- | --- |
| Metadata QC | `metadata_qc` | 已有基础实现，必须稳定 | 文件读取、metadata、通道、采样率、时长、基础质量指标 |
| Waveform Preview | `qc_waveform_preview` | 待实现，必须进入实验室完整功能 | 读取指定时间窗和通道，返回原始波形预览数据与图像 |
| Filter Preview | `qc_filter_preview` | 待实现，必须进入实验室完整功能 | 对预览窗口应用临时带通/陷波，用于视觉比较，不写回原文件 |
| Snapshot Export | `qc_snapshot` | 待实现，必须进入实验室完整功能 | 保存当前预览区域快照、参数、时间窗和通道选择 |
| QC Report Package | `qc_report_package` | 待实现/可由 contract adapter 生成 | 汇总 QC、预览图、快照、JSON、方法说明和 manifest |

### 2.2 非目标

- 不在 QC 中执行 ICA、自动坏段删除或不可逆清洗。
- 不把滤波预览直接当作下游分析的正式预处理结果。
- 不把 preview 截图当作完整统计图。
- 不在前端直接计算核心 EEG 指标；前端只做可视化和服务调用。

## 3. 用户场景

### 3.1 研究助理上传新数据

用户想知道：

- 文件能不能读。
- 通道数、采样率、时长是否正确。
- 是否有明显平线、极端振幅、坏道或事件缺失。
- 原始波形看起来是否像正确采集的数据。
- 是否需要先调整参考、滤波或重新导出数据。

### 3.2 PI / 审稿前复核

用户想看到：

- QC 结论不是黑箱，能追溯到图、表、JSON 和方法说明。
- 预览快照能说明“为什么这个文件可以/不可以继续分析”。
- 截图包含文件、时间窗、通道、滤波预览参数和生成时间。

### 3.3 后续模块调用

PSD / ERP 等模块需要消费 QC 结果：

- 文件可读性。
- EEG 通道列表。
- bad channel 候选。
- 建议继续/暂停的状态。
- 用户是否完成必要人工复核。

## 4. 前端工作流

QC 页面必须从展示页升级为完整工作台。

```text
选择 EEG 文件
  -> 读取 metadata
  -> 显示文件概览与通道表
  -> 选择预览通道和时间窗
  -> 查看原始波形
  -> 可选：开启带通/陷波预览
  -> 截取当前预览区域快照
  -> 运行/刷新 QC 检查
  -> 查看 QC 结果、风险、建议
  -> 下载报告包和复现记录
```

### 4.1 页面区域

| 区域 | 内容 | 是否必须 |
| --- | --- | --- |
| 文件输入 | 已上传文件选择、文件名、格式、大小、上传时间 | 必须 |
| Metadata 概览 | 采样率、时长、通道数、通道类型、事件/注释数量、参考/滤波信息 | 必须 |
| 通道选择 | EEG 通道、坏道候选、通道类型筛选、ROI/常用通道组 | 必须 |
| 时间窗选择 | 起止秒、窗口长度、跳转上一段/下一段、事件附近定位 | 必须 |
| 波形预览 | 原始波形 traces、比例尺、时间轴、通道标签、事件/注释标记 | 必须 |
| 滤波预览 | 带通、陷波、开关、参数、原始/滤波后对比 | 必须 |
| 快照 | 保存当前预览区域为 PNG/SVG 和 JSON 描述 | 必须 |
| QC 检查 | 自动 checks、warnings、人工复核提示 | 必须 |
| 输出下载 | summary、parameters、snapshot、manifest、log、report package | 必须 |

## 5. 输入契约

### 5.1 通用任务输入

```json
{
  "project_id": "project_xxx",
  "module_name": "qc",
  "workflow_id": "metadata_qc",
  "input_file_id": "file_xxx",
  "parameters_json": {
    "qc_thresholds": {},
    "preview": {},
    "filter_preview": {},
    "snapshot": {}
  }
}
```

### 5.2 QC 阈值参数

```json
{
  "qc_thresholds": {
    "min_sfreq": 100.0,
    "min_duration_sec": 5.0,
    "flat_threshold_uv": 1.0,
    "extreme_threshold_uv": 1000.0,
    "max_bad_channel_ratio": 0.2,
    "require_eeg_channels": true,
    "require_annotations": false
  }
}
```

### 5.3 波形预览参数

```json
{
  "preview": {
    "start_sec": 10.0,
    "duration_sec": 12.0,
    "channels": ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4"],
    "channel_limit": 32,
    "amplitude_unit": "uV",
    "downsample_for_display": true,
    "display_sfreq": 250.0,
    "show_annotations": true,
    "show_events": true,
    "vertical_scale_uv": 100.0
  }
}
```

要求：

- `start_sec` 不得小于 0。
- `duration_sec` 不能超过服务配置上限，建议 v0.1 默认 5-30 秒。
- 通道不存在时必须明确返回 `CHANNEL_NOT_FOUND`。
- 时间窗超出文件范围时必须返回可读错误，并给出允许范围。

### 5.4 滤波预览参数

```json
{
  "filter_preview": {
    "enabled": true,
    "bandpass": {
      "enabled": true,
      "l_freq": 1.0,
      "h_freq": 40.0,
      "method": "fir"
    },
    "notch": {
      "enabled": true,
      "freqs": [50.0],
      "method": "fir"
    },
    "compare_mode": "overlay",
    "apply_to": "preview_window_only"
  }
}
```

要求：

- 带通和陷波只作用于预览窗口，不修改原始文件。
- UI 必须明确标注“滤波预览，不是正式预处理产物”。
- 参数不合法时必须返回 `INVALID_FILTER_PARAMETER`。
- 当 `h_freq >= sfreq / 2` 时必须失败并提示 Nyquist 限制。
- 50Hz/60Hz 陷波应允许用户选择，不应默认假设所有数据都需要。

### 5.5 快照参数

```json
{
  "snapshot": {
    "enabled": true,
    "label": "baseline window before PSD",
    "format": "png",
    "include_raw": true,
    "include_filtered_preview": true,
    "include_annotations": true,
    "include_parameter_badge": true
  }
}
```

## 6. 输出契约

QC 服务必须输出统一 contract 文件：

```text
qc_job_xxx/
  result.json
  manifest.json
  log.txt
  report.html
  report_package.zip
  reproducibility/
    qc_summary.json
    parameters.json
    workflow.json
    software_versions.json
    method_description.txt
  figures/
    waveform_raw_preview.png
    waveform_filter_preview.png
    qc_dashboard.png
    snapshots/
      snapshot_001.png
  tables/
    channel_qc.csv
    annotation_summary.csv
  data/
    waveform_preview.json
    filter_preview.json
    snapshot_001.json
```

### 6.1 `qc_summary.json`

必须包含：

```json
{
  "status": "pass | warning | fail",
  "readable": true,
  "format": "edf",
  "reader": "mne.io.read_raw_edf",
  "sfreq": 500.0,
  "duration_sec": 120.0,
  "n_channels": 64,
  "n_eeg_channels": 64,
  "annotations_count": 12,
  "bad_channel_candidates": [],
  "flat_channel_candidates": [],
  "extreme_amplitude_channels": [],
  "checks": [],
  "warnings": [],
  "next_step_recommendation": {
    "psd_allowed": true,
    "erp_allowed": "depends_on_events",
    "requires_human_review": true
  }
}
```

### 6.2 `waveform_preview.json`

必须包含：

```json
{
  "input_file_id": "file_xxx",
  "start_sec": 10.0,
  "duration_sec": 12.0,
  "sfreq_original": 500.0,
  "sfreq_display": 250.0,
  "channels": ["Fp1", "Fp2"],
  "unit": "uV",
  "times_sec": [10.0, 10.004],
  "data_uv": [[0.1, 0.2], [-0.1, -0.2]],
  "annotations": [],
  "events": [],
  "decimation": {
    "enabled": true,
    "reason": "display_only"
  }
}
```

### 6.3 `filter_preview.json`

必须包含：

```json
{
  "filter_preview_only": true,
  "parameters": {
    "bandpass": {"enabled": true, "l_freq": 1.0, "h_freq": 40.0},
    "notch": {"enabled": true, "freqs": [50.0]}
  },
  "input_window": {
    "start_sec": 10.0,
    "duration_sec": 12.0,
    "channels": ["Fp1", "Fp2"]
  },
  "outputs": {
    "raw_trace": "data/waveform_preview.json",
    "filtered_trace": "data/filter_preview.json",
    "figure": "figures/waveform_filter_preview.png"
  },
  "warnings": [
    "Filtering is for preview only and does not modify the uploaded file."
  ]
}
```

### 6.4 `snapshot_001.json`

必须包含：

```json
{
  "snapshot_id": "snapshot_001",
  "created_at": "2026-06-18T00:00:00Z",
  "label": "baseline window before PSD",
  "input_file_id": "file_xxx",
  "time_window": {"start_sec": 10.0, "duration_sec": 12.0},
  "channels": ["Fp1", "Fp2"],
  "filter_preview": {
    "enabled": true,
    "bandpass": {"l_freq": 1.0, "h_freq": 40.0},
    "notch": {"freqs": [50.0]}
  },
  "figure": "figures/snapshots/snapshot_001.png",
  "review_note": "User-visible preview snapshot; not a clinical interpretation."
}
```

## 7. 图表质量标准

### 7.1 原始波形预览

- 必须有横轴时间秒、纵轴单位 μV 或明确偏移显示规则。
- 必须显示通道名。
- 必须显示采样率和预览时间窗。
- 多通道波形应支持垂直偏移，避免重叠不可读。
- 事件/annotation 应作为竖线或标记显示，不应遮挡波形。
- 预览降采样必须标注 `display_sfreq`，不能伪装成原始采样率。

### 7.2 滤波预览

- 必须能切换“原始 / 滤波后 / 对比”。
- 对比模式必须明确颜色和图例。
- 必须展示带通和陷波参数。
- 必须显示“预览滤波，不写回原始文件”。
- 滤波边界效应应在时间窗两端提示，必要时扩大内部计算窗口后裁剪显示。

### 7.3 快照

- 快照必须包含标题、文件名/匿名 ID、时间窗、通道列表、滤波预览参数、生成时间。
- 快照不应包含真实个人身份信息。
- 快照应可被 report package 收录。

## 8. 错误契约

| error_code | 场景 | 用户提示 |
| --- | --- | --- |
| `FILE_NOT_FOUND` | 输入文件不存在 | 未找到 EEG 文件，请重新上传或选择文件 |
| `UNSUPPORTED_FORMAT` | 格式不支持 | 当前格式暂不支持，请上传 EDF/BDF/FIF/BrainVision/SET/CNT |
| `MNE_READ_FAILED` | MNE 读取失败 | 文件读取失败，请检查文件是否损坏或导出是否完整 |
| `NO_EEG_CHANNELS` | 没有 EEG 通道 | 未识别到 EEG 通道，请检查通道类型或文件格式 |
| `TIME_WINDOW_OUT_OF_RANGE` | 预览窗口越界 | 预览时间窗超出记录范围，请选择 0 到 duration_sec 内的窗口 |
| `CHANNEL_NOT_FOUND` | 选择通道不存在 | 部分通道不存在，请重新选择通道 |
| `INVALID_FILTER_PARAMETER` | 滤波参数非法 | 滤波参数不合法，请检查低切、高切和陷波频率 |
| `SNAPSHOT_RENDER_FAILED` | 快照渲染失败 | 当前预览快照生成失败，请缩短窗口或减少通道数 |

错误返回必须同时写入 `result.json.errors` 和 `log.txt`。

## 9. 服务接口建议

v0.1 可以继续使用现有 `/api/tasks`，但 `workflow_id` 必须区分能力：

```text
metadata_qc
qc_waveform_preview
qc_filter_preview
qc_snapshot
qc_report_package
```

后续如果拆独立 endpoint，建议：

```text
POST /api/analysis/qc/metadata
POST /api/analysis/qc/waveform-preview
POST /api/analysis/qc/filter-preview
POST /api/analysis/qc/snapshot
GET  /api/tasks/{task_id}/artifacts
```

前端不应直接读取本地文件路径，只消费 artifact URL 或 task artifact 列表。

## 10. 后端实现建议

### 10.1 模块拆分

建议后续逐步形成：

```text
eeg_core/modules/qc/
  schema.py
  metadata.py
  waveform_preview.py
  filter_preview.py
  snapshot.py
  report.py
  runner.py
```

v0.1 不强制物理迁移；可以先在现有 `eeg_core/preprocess/quality.py` 外新增 adapter，避免破坏已通过验收的逻辑。

### 10.2 关键实现要求

- 使用 MNE 读取 raw，`preload=False` 做 metadata，预览窗口按需读取数据。
- 波形预览只加载所选通道和时间窗，避免大文件一次性进内存。
- 滤波预览应 copy 当前窗口数据，不应修改 raw 原对象或上传文件。
- 大文件显示可降采样，但必须保留原始采样率记录。
- 所有输出进入统一 `result.json`、`manifest.json`、`log.txt` 契约。

## 11. 前端交互验收

QC 实验室页面完成前，不允许只保留卡片示意。必须通过以下验收：

- [ ] 可以选择一个已上传 EEG 文件。
- [ ] 可以看到文件 metadata 概览。
- [ ] 可以选择通道和时间窗。
- [ ] 可以显示原始波形预览。
- [ ] 可以开启/关闭带通预览。
- [ ] 可以开启/关闭 50Hz/60Hz 陷波预览。
- [ ] 可以对比原始波形和滤波后预览。
- [ ] 可以截取当前预览区域快照。
- [ ] 快照可下载，并进入 report package。
- [ ] QC summary、parameters、workflow、software_versions、result、manifest、log 均可下载。
- [ ] 所有失败状态都有可读错误。
- [ ] 页面明确说明滤波是预览，不是正式预处理。

## 12. 自动化验收

### 12.1 成功路径

- 使用 synthetic EEG 文件运行 `metadata_qc`。
- 请求 8 通道、12 秒原始波形预览。
- 请求 1-40 Hz 带通 + 50 Hz 陷波预览。
- 生成一个快照。
- 检查所有 contract 文件和 artifact 存在。

### 12.2 失败路径

- 不支持格式。
- 空文件或损坏文件。
- 无 EEG 通道。
- 时间窗越界。
- 通道不存在。
- `h_freq >= sfreq / 2`。
- 快照通道过多或窗口过长时返回可读错误。

### 12.3 性能边界

- 500MB 文件 metadata 读取不得阻塞整个 API 超过设计阈值；v0.1 可记录耗时，v0.2 迁移后台队列。
- 预览窗口默认不超过 30 秒、32 通道。
- 前端显示数据点数超过阈值时必须降采样或分页。

## 13. 与 PSD / ERP 的关系

QC 是下游分析的入口守门服务。

PSD 进入条件：

- 文件可读。
- 有 EEG 通道。
- 采样率满足最低要求。
- 预览无明显全局异常。
- 用户已确认是否接受坏道候选和滤波建议。

ERP 进入条件：

- 文件可读。
- 有 EEG 通道。
- 事件/annotations 存在且能映射到 event_id。
- 用户已确认 epoch 时间窗和 baseline 前置条件。

QC 不替 PSD/ERP 做正式参数决定，但必须把风险和建议传递给后续模块。

## 14. 主流程合并准入

QC 从实验室进入正式工作台前必须满足：

- [ ] `metadata_qc` 稳定。
- [ ] `qc_waveform_preview` 可用。
- [ ] `qc_filter_preview` 可用。
- [ ] `qc_snapshot` 可用。
- [ ] 前端 QC 页面完整输入输出，不再只是静态卡片。
- [ ] 输出包包含图、表、JSON、方法说明、manifest 和 log。
- [ ] 成功/失败自动化验收通过。
- [ ] 文案保留科研用途边界和非临床说明。

## 15. 飞书摘要

```text
模块：QC 数据质量控制
本次确认：QC 必须承担数据预览能力，包括原始波形窗口、带通/陷波滤波预览、预览区域快照和完整报告包。
输入输出：输入 EEG 文件、QC 阈值、预览通道、时间窗、滤波预览参数；输出 qc_summary、waveform_preview、filter_preview、snapshot、figures、tables、result、manifest、log、report_package。
验收标准：不能只做卡片示意；必须能选择文件、配置参数、查看原始/滤波预览、截取快照、下载完整复现材料，并处理失败状态。
待确认：滤波预览默认频段、预览窗口上限、快照格式 PNG/SVG、是否在 v0.1 通过 /api/tasks 承载所有 QC 子服务。
```

## 16. 2026-06-18 implementation note

The first customer-facing QC Lab service preview is implemented.

Implemented scope:

- `qc_waveform_preview` runs through the existing `/api/tasks` task API.
- The preview accepts `preview`, `filter_preview`, and `snapshot` parameters.
- The service writes `result.json`, `manifest.json`, `log.txt`, `data/waveform_preview.json`, `data/filter_preview.json`, `data/snapshot_001.json`, `figures/waveform_raw_preview.svg`, `figures/waveform_filter_preview.svg`, and `figures/snapshots/snapshot_001.svg`.
- `frontend/qc-lab.html` provides the first full QC Lab page for upload or selection, metadata review, preview parameters, filter preview, snapshots, and artifact downloads.
- Filtering remains preview-only and does not modify the uploaded EEG file.

Validation evidence:

```powershell
python scripts/acceptance_qc_preview_service.py
node scripts/acceptance_research_modules_static.mjs
python scripts/smoke_v01_api.py
python scripts/acceptance_v01_worker_core.py
python scripts/acceptance_v01_persistence.py
python scripts/acceptance_v01_full.py
python scripts/check_no_mojibake.py
```

Result: all commands passed in the 2026-06-18 local run.

Remaining work:

- Add explicit failure-path tests for invalid channels, out-of-range windows, unsupported files, and invalid filter parameters.
- Decide whether `qc_filter_preview` and `qc_snapshot` should remain aliases of the same runner or become separate runner entries.
- Add PNG export if journal/report workflows require bitmap snapshots in addition to SVG.
