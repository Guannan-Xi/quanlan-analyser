# 数据准备交互式波形工作台 Canvas 实现契约

版本：2026-06-27
适用范围：QLanalyser 主工作台数据准备页的 Canvas 波形预览、选段、坏段、坏道、滤波预览、重参考记录和分析门禁。
上游文档：

- `docs/product/waveform_preparation_workbench_requirements_20260627.md`
- `docs/product/waveform_preparation_workbench_detailed_design_20260627.md`
- `docs/product/waveform_preparation_workbench_e2e_test_plan_20260627.md`
- `docs/product/qlanalyser_project_cleanup_waveform_preprocessing_ui_design_20260626.md`

本文件补齐 Claude Opus 4.8 复审指出的 P0 缺口：Canvas 坐标规格、预览数据契约、数据准备保存契约、自动加载生命周期、降采样策略、选择器登记和教学数据保护。

## 1. 总原则

1. 当前实现路线是 **Canvas**，不是 TimeChart。
2. Canvas 只负责当前窗口波形和叠加层绘制，不拥有业务状态。
3. 所有预处理操作只写入数据准备记录，不改写原始 EEG。
4. QC、滤波预览、重参考、坏道、坏段、事件检查都属于数据准备，不进入“分析方法”列表。
5. 教学模式内置数据可被预览、可被用于教学沙盒分析，但不可删除、不可覆盖原始文件、不可污染真实项目。
6. 任何后续 PSD/ERP/其他分析任务必须携带已确认的数据准备方案，或被 UI 明确拦截。

## 2. Canvas 坐标与绘制规格

### 2.1 绘图区

Canvas 使用 CSS 尺寸和设备像素比分离：

```text
cssWidth  = canvas.getBoundingClientRect().width
cssHeight = canvas.getBoundingClientRect().height
dpr       = max(1, window.devicePixelRatio || 1)
canvas.width  = round(cssWidth  * dpr)
canvas.height = round(cssHeight * dpr)
ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
```

绘图区固定由四个边距定义：

```text
plotLeft   = 86
plotRight  = 24
plotTop    = 42
plotBottom = 46
plotWidth  = cssWidth  - plotLeft - plotRight
plotHeight = cssHeight - plotTop  - plotBottom
```

实现允许按 UI 实际尺寸微调边距，但所有时间、通道、叠加层和鼠标命中计算必须使用同一组边距。

### 2.2 时间到 x 坐标

输入窗口：

```text
windowStartSec
windowDurationSec
windowEndSec = windowStartSec + windowDurationSec
```

公式：

```text
x = plotLeft + ((timeSec - windowStartSec) / windowDurationSec) * plotWidth
timeSec = windowStartSec + ((x - plotLeft) / plotWidth) * windowDurationSec
```

约束：

- `timeSec` 必须 clamp 到 `[windowStartSec, windowEndSec]`。
- 鼠标拖拽选段使用同一个 `timeSec = f(x)` 反算公式。
- 坏段、选段、事件 marker、时间轴刻度必须共用同一个时间映射。

### 2.3 通道到 y 坐标

可见通道数：

```text
visibleChannelCount = min(requestedVisibleChannels, payload.channels.length)
rowHeight = plotHeight / visibleChannelCount
channelCenterY(index) = plotTop + rowHeight * (index + 0.5)
```

通道顺序以预览响应中的 `channels` 为准。前端不得自行重排，除非用户显式使用通道排序功能。

### 2.4 振幅到 y 坐标

预览数据单位统一为微伏 `uV`。每个通道的像素振幅：

```text
amplitudePx = sampleUv * gainPxPerUv
y = channelCenterY(channelIndex) - amplitudePx
```

默认增益建议：

```text
gainPxPerUv = rowHeight * 0.32 / max(channelScaleUv, 1)
```

其中 `channelScaleUv` 优先使用预览响应里的 `scale_uv`；如果没有，则以前端默认 `100 uV` 兜底。实现必须避免单个尖峰把整行撑爆：绘制时将 `y` clamp 到当前通道行上下边界外 4px 的范围内。

### 2.5 叠加层顺序

Canvas 单层绘制顺序：

1. 背景。
2. 网格和时间轴。
3. 坏段红色半透明区域。
4. 当前选段粉色/紫色半透明区域。
5. 波形折线。
6. 事件 marker。
7. 通道名、坏道样式和状态提示。

坏段不遮挡波形；坏段透明度建议 `0.10-0.18`。当前选段透明度建议 `0.12-0.20`，颜色必须与坏段可区分。

### 2.6 鼠标交互

拖拽选段：

```text
pointerDown -> startTimeSec = xToTime(eventX)
pointerMove -> currentTimeSec = xToTime(eventX)
selectedSegment = normalize(min(startTimeSec, currentTimeSec), max(...))
pointerUp   -> freeze selectedSegment
```

最小有效选段：

```text
minSegmentDurationSec = max(0.05, 2 / displaySampleRate)
```

滚轮：

- 普通滚轮：按当前窗口长度的 8% 平移。
- Ctrl/Cmd + 滚轮：围绕鼠标所在时间点缩放。
- 缩放后必须保持鼠标锚点时间尽量不漂移。

缩放锚点公式：

```text
anchorRatio = (anchorTimeSec - oldStartSec) / oldDurationSec
newStartSec = anchorTimeSec - anchorRatio * newDurationSec
```

## 3. 波形预览数据契约

### 3.1 当前可用入口

主工作台可以继续复用当前任务入口：

```text
POST /api/tasks
module_name = "qc"
workflow_id = "qc_waveform_preview"
```

实现上可以从任务产物读取 `waveform_preview.json`，也可以后续补一个直接窗口 API。无论入口如何变化，前端最终消费的预览 payload 必须归一化为本节结构。

### 3.2 预览请求参数

```json
{
  "schema_version": "qlanalyser-waveform-preview-v0.1",
  "input_file_id": "eeg_file_id",
  "window": {
    "start_sec": 0,
    "duration_sec": 10
  },
  "display": {
    "visible_channels": 8,
    "gain": 2,
    "max_points_per_channel": 2500
  },
  "filter_preview": {
    "enabled": false,
    "l_freq": null,
    "h_freq": null,
    "notch_freqs": []
  },
  "reference_preview": {
    "mode": "original",
    "channels": [],
    "bipolar_pairs": []
  },
  "boundary": "research preprocessing preview only; non-diagnostic"
}
```

### 3.3 预览响应归一化结构

```json
{
  "schema_version": "qlanalyser-waveform-preview-v0.1",
  "input_file_id": "eeg_file_id",
  "source_task_id": "task_id_or_null",
  "window": {
    "start_sec": 0,
    "duration_sec": 10,
    "end_sec": 10
  },
  "sample_rate_hz": 500,
  "display_sample_rate_hz": 250,
  "unit": "uV",
  "downsampled": true,
  "downsample_method": "min_max_bucket",
  "scale_uv": 100,
  "channels": [
    {
      "name": "Fp1",
      "index": 0,
      "status": "good",
      "type": "eeg"
    }
  ],
  "times_sec": [0, 0.004, 0.008],
  "data_uv": [
    [1.2, 0.9, -0.2]
  ],
  "bad_channels": [],
  "bad_segments": [],
  "events": [
    {
      "time_sec": 1.2,
      "label": "stim",
      "code": "target"
    }
  ],
  "metadata": {
    "preview_only_filtering": true,
    "reference_preview_only": true,
    "non_diagnostic": true
  }
}
```

字段要求：

- `channels.length` 必须等于 `data_uv.length`。
- 每个 `data_uv[i].length` 必须等于 `times_sec.length`。
- `times_sec` 必须单调递增。
- `display_sample_rate_hz` 是当前绘制数据的采样率，不等于原始采样率时必须设置 `downsampled=true`。
- 如果后端暂时只返回旧字段，前端适配层负责归一化，不得让 Canvas 绘制函数直接依赖多种形状。

## 4. 降采样策略

目标：保证自动加载和拖动缩放不因大文件或高采样率卡死。

默认阈值：

```text
maxPointsPerChannel = min(2500, max(900, plotWidth * 2))
```

当 `rawSamplesPerChannel <= maxPointsPerChannel` 时不降采样。
当超过阈值时使用 min/max bucket：

```text
bucketSize = ceil(rawSamplesPerChannel / maxPointsPerChannel)
for each bucket:
  keep sample with min value
  keep sample with max value
  preserve their original time order
```

要求：

1. 降采样必须保留尖峰和坏段边界附近的可见极值。
2. 前端如果拿到未降采样大数组，可以做临时 min/max bucket；但正式实现优先由后端返回已降采样窗口。
3. 预览响应必须说明 `downsampled` 和 `downsample_method`。
4. E2E 至少覆盖一个 `downsampled=true` 的窗口。

## 5. 数据准备保存契约

### 5.1 现有后端锚点

当前后端已有数据准备模型和路由：

```text
backend/models/data_preparation.py
backend/api/data_preparation.py
GET  /api/eeg/files/{file_id}/data-preparation-plan
POST /api/eeg/files/{file_id}/data-preparation-plan
POST /api/eeg/files/{file_id}/bad-channel-audit
```

实现必须沿用 `schema_version = "qlanalyser-data-preparation-v0.2"`，并使用 `base_revision` / `expected_revision` 做冲突检测。

### 5.2 保存草稿

前端保存草稿时，payload 至少包含：

```json
{
  "schema_version": "qlanalyser-data-preparation-v0.2",
  "project_id": "project_id",
  "status": "draft",
  "module_scope": ["qc", "psd", "erp"],
  "scope": "common_qc_preparation",
  "preprocessing_json": {
    "filter_preview": {
      "enabled": false,
      "l_freq": null,
      "h_freq": null,
      "notch_freqs": []
    },
    "reference": {
      "mode": "original",
      "channels": [],
      "bipolar_pairs": []
    }
  },
  "qc_json": {
    "viewport": {
      "start_sec": 0,
      "duration_sec": 10,
      "visible_channels": 8,
      "gain": 2
    },
    "selected_segment": {
      "start_sec": 1.0,
      "end_sec": 2.0
    }
  },
  "bad_channels": [],
  "bad_segments": [],
  "annotation_actions": [],
  "saved_preview_segments": [],
  "artifact_contract_json": {
    "source": "main_data_preparation_canvas",
    "preview_only_filtering": true,
    "non_diagnostic": true
  },
  "base_revision": 1
}
```

### 5.3 确认方案

用户点击“确认准备”后：

- `status` 必须为 `confirmed`。
- 后端返回 `id` 和 `revision`。
- 前端保存到当前文件状态：

```json
{
  "data_preparation_plan_id": "prep_xxx",
  "data_preparation_revision": 2,
  "data_preparation_contract_version": "qlanalyser-data-preparation-v0.2"
}
```

后续 PSD/ERP 等分析任务必须携带上述三项。缺失时 UI 必须阻止提交，并提示“请先确认数据准备方案”。

### 5.4 恢复语义

本期只要求逐项恢复，不要求多步 undo/redo。

- 恢复坏道：写入 `restoredBadChannels` 或等价 audit 记录，并从当前坏道显示中移除。
- 恢复坏段：写入 `restoredSegments` 或等价 audit 记录，并从当前剔除段显示中移除。
- 所有恢复动作必须保留来源动作、操作者、时间、窗口和理由。

## 6. 自动加载生命周期

数据选择后自动进入波形预览，不要求用户点击内部 QC 预览按钮。

状态机：

```text
idle
  -> selected_file
  -> loading_skeleton
  -> task_submitted
  -> preview_loaded
  -> interactive_ready
```

失败状态：

```text
loading_skeleton
  -> timeout
  -> failed
  -> stale_response_ignored
```

要求：

1. 每次加载生成递增 `previewRequestSeq`。
2. 新文件或新窗口请求发出后，旧响应如果晚到必须被忽略。
3. 加载中必须显示骨架波形或明确 loading，不允许白屏。
4. 失败时显示可理解错误和“重新加载”按钮。
5. `#loadEegBtn` 是用户可见的重新加载按钮，不是“运行质控预览”的主入口文案。
6. 教学模式进入后自动选择教学文件并自动预览。

超时建议：

```text
fast preview soft timeout: 8s
hard timeout with user-visible retry: 20s
```

## 7. UI 选择器登记表

实现和 E2E 必须优先使用稳定选择器。

| 类型 | 选择器 | 目的 |
|---|---|---|
| 工作台 | `[data-testid="data-preparation-workbench"]` | 数据准备主区域 |
| 单文件面板 | `[data-testid="single-file-preview-panel"]` | 波形与预处理同屏区域 |
| Canvas | `#eegCanvas` | 波形绘制、拖拽选段、滚轮交互 |
| 重新加载 | `#loadEegBtn` | 用户可见的波形重新加载 |
| 上一段 | `#eegPrevBtn` | 平移到前一窗口 |
| 下一段 | `#eegNextBtn` | 平移到后一窗口 |
| 放大 | `#eegZoomInBtn` | 缩短时间窗 |
| 缩小 | `#eegZoomOutBtn` | 放大时间窗 |
| 复位 | `#eegResetBtn` | 回到默认窗口 |
| 起点 | `#eegStartInput` | 当前窗口开始时间 |
| 时间窗 | `#eegWindowInput` | 当前窗口长度 |
| 增益 | `#eegGainInput` | 波形增益 |
| 通道数 | `#eegChannelInput` | 可见通道数 |
| 滤波预览 | `#eegFilterPreviewToggle` | 预览滤波开关 |
| 选段开始 | `#segmentStart` | 当前选段开始 |
| 选段结束 | `#segmentEnd` | 当前选段结束 |
| 状态摘要 | `#segmentSummary` | 当前窗口和操作摘要 |
| 剔除片段 | `[data-ia-action="exclude-segment"]` | 写入坏段/剔除段草稿 |
| 恢复片段 | `[data-ia-action="restore-segment"]` | 恢复剔除段 |
| 标记坏道 | `[data-ia-action="mark-bad-channel"]` | 写入坏道草稿 |
| 恢复坏道 | `[data-ia-action="restore-bad-channel"]` | 恢复坏道 |
| 预处理面板 | `[data-testid="preprocessing-inline-panel"]` | 滤波、重参考、确认准备 |
| 波形工作台 | `[data-testid="preview-edit-workbench"]` | Canvas 与交互容器 |
| 教学边界 | `[data-testid="teaching-data-protected"]` | 教学数据不可删除/不可覆盖提示 |
| 分析门禁 | `[data-testid="analysis-preparation-gate"]` | 未确认准备时的分析拦截 |

如果实现中暂时缺少某个选择器，开发任务必须同步补齐，不允许 E2E 改用脆弱文本查找。

## 8. 教学数据保护

教学数据固定标识：

```text
project_id: proj_demo_learning
file_id: eeg_demo_teaching_oddball
```

UI 要求：

1. 教学数据行显示“教学内置数据 / 受保护”。
2. 删除、覆盖、真实上传替换入口必须隐藏或禁用。
3. 数据准备草稿可以保存到教学沙盒，不得写入真实项目。
4. PSD/ERP 教学沙盒分析可直接使用教学文件和已确认准备方案，不再要求上传。

后端要求：

1. 删除教学内置文件必须返回拒绝。
2. 覆盖教学内置文件必须返回拒绝。
3. 教学沙盒生成的准备方案必须带教学项目/文件标识。

## 9. 分析门禁

分析任务提交前检查：

```text
current_file_id exists
data_preparation_plan_id exists
data_preparation_revision exists
data_preparation_contract_version == "qlanalyser-data-preparation-v0.2"
```

未满足时：

- 禁用提交按钮或提交时拦截。
- 提示：“请先在数据准备页确认当前 EEG 的准备方案。”
- 提供跳转到数据准备页的按钮。

ERP 额外检查：

- 有事件 marker 或 epoch set。
- 没有事件时，不运行 ERP；提示用户先检查/确认事件。

PSD 额外检查：

- PSD 可使用连续数据，但仍必须携带准备方案 id 和 revision。

## 10. E2E 追加断言

现有 E2E 文档应追加或细化以下断言：

1. 选择数据后 `#eegCanvas` 自动变为非空，不需要点击内部 QC 预览按钮。
2. 快速切换两个文件时，旧预览响应不会覆盖新文件画布。
3. Canvas 拖拽选段后，`#segmentStart` / `#segmentEnd` 与画布选区一致，误差小于 `max(0.05s, 2/displaySampleRate)`。
4. 坏段叠加与选段叠加在缩放、平移、resize 后仍与时间轴对齐。
5. `downsampled=true` 的预览窗口仍能显示尖峰极值。
6. 标记坏道、恢复坏道、剔除片段、恢复片段都写入准备方案草稿。
7. 点击“确认准备”后，后续 PSD/ERP 任务 payload 带 `data_preparation_plan_id` 和 `data_preparation_revision`。
8. 未确认准备时，分析提交被 `[data-testid="analysis-preparation-gate"]` 拦截。
9. 教学数据删除/覆盖入口不可用，后端拒绝删除或覆盖请求。
10. 页面不出现“临床诊断、治疗、医疗决策”等正向医疗承诺文案。

## 11. 开发门禁

进入 Canvas 核心绘制开发前，必须满足：

- 本文件已被实现任务引用。
- 预览 payload 已统一到第 3 节结构，或已有适配函数负责归一化。
- Canvas 坐标映射函数有单元级或脚本级验证。
- 数据准备保存使用现有 `qlanalyser-data-preparation-v0.2` 模型和 revision 检查。
- E2E 覆盖自动加载、拖拽选段、坏道/坏段恢复、确认准备、分析门禁和教学数据保护。

不满足以上条件时，只能开发布局骨架和静态 UI，不能宣称 Canvas 波形工作台完成。
