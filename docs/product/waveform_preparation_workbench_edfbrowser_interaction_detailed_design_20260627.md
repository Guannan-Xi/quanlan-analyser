# QLanalyser 数据准备波形工作台：EDFBrowser 风格详细设计补充

版本：2026-06-27
状态：已吸收 Codex + Claude 双评审 P0 建议的可开发基线 v2

适用范围：Canvas 主线波形工作台。禁止范围：不接入 TimeChart，不安装依赖，不触碰 router / Headroom / gateway / IPC / model route，不处理癫痫源码工作台。

## 1. 设计结论

主工作台波形区采用“EDFbrowser 风格的阅片优先交互”：

```text
默认浏览模式
-> 滚轮/键盘/中键拖动改变 viewport
-> Ctrl/Cmd 明确进入时间缩放
-> 模式切换后才允许左键拖拽写入选段/坏段
-> 所有写入先进入 UI draft，再由保存/确认进入 preparation plan revision
```

这不是外观复刻 EDFbrowser，而是复用成熟 EEG 工具的操作肌肉记忆。

## 2. 状态模型

```text
waveformInteractionMode:
  browse
  selectSegment
  markBadSegment
  markBadChannel

viewport:
  start_sec
  duration_sec
  end_sec
  display_sample_rate_hz
  visible_channels
  sensitivity_uv_per_row

interactionTransient:
  drag_start_time_sec
  drag_current_time_sec
  anchor_time_sec
  hover_time_sec
  hover_channel_name

uiDraft:
  selected_segment
  bad_segments
  bad_channels
  restored_segments
  restored_bad_channels
  audit_actions

persistedPreparation:
  data_preparation_plan_id
  data_preparation_revision
  data_preparation_contract_version
```

所有 Canvas 绘制、overlay 和鼠标命中都必须读同一个 `viewport`。外显振幅单位统一为 `sensitivity_uv_per_row`；内部如果需要 `gain_px_per_uv`，只能作为渲染派生值，不在 UI 状态栏作为主单位出现。

三层写入模型：

- L1 `interactionTransient`：拖拽过程和 hover 读数，只存在于当前交互。
- L2 `uiDraft`：释放鼠标后的本地草稿，可撤销，不产生后端 revision。
- L3 `persistedPreparation`：点击保存草稿或确认准备后，写入后端并产生 revision。

## 3. 模式切换 UI

波形工具栏必须提供模式按钮：

```html
<button data-testid="waveform-mode-browse" data-mode-target="browse">浏览</button>
<button data-testid="waveform-mode-select-segment" data-mode-target="selectSegment">选段</button>
<button data-testid="waveform-mode-mark-bad-segment" data-mode-target="markBadSegment">坏段</button>
<button data-testid="waveform-mode-mark-bad-channel" data-mode-target="markBadChannel">坏道</button>
```

Canvas 容器同步挂载：

```html
<section data-testid="preview-edit-workbench" data-mode="browse">
```

进入写入模式时：

- 对应按钮 `aria-pressed="true"`。
- 状态栏显示模式说明。
- Canvas cursor 变化。
- Esc/B 可回到 browse。

## 4. 统一常量

```js
const EDF_BROWSER_INTERACTION_CONSTANTS = {
  wheelPanRatio: 0.08,
  arrowPanRatio: 0.10,
  pagePanRatio: 1.00,
  zoomFactor: 1.20,
  minDurationSec: ({ displaySampleRate }) => Math.max(0.5, 20 / Math.max(displaySampleRate, 1)),
  maxDurationSec: ({ fileDurationSec }) => Math.min(Math.max(fileDurationSec || 300, 0.5), 300),
  gainStepRatio: 1.20,
  minSensitivityUvPerRow: 5,
  maxSensitivityUvPerRow: 500,
  anchorDriftToleranceSec: ({ displaySampleRate }) => Math.max(0.05, 2 / Math.max(displaySampleRate, 1)),
};
```

E2E 不应复制一套不同常量；如果脚本无法 import 前端常量，也必须在测试计划里使用同样数值。

## 5. 输入映射

### 5.1 鼠标滚轮

```text
wheel without Ctrl/Cmd:
  delta = sign(event.deltaY) * viewport.duration_sec * wheelPanRatio
  viewport.start_sec = clamp(start_sec + delta, 0, fileDurationSec - duration_sec)
  scheduleWaveformWindowReload()

wheel with Ctrl/Cmd:
  anchor_time = xToTime(event.clientX)
  scale = event.deltaY > 0 ? zoomFactor : 1 / zoomFactor
  new_duration = clamp(duration_sec * scale, minDurationSec, maxDurationSec)
  anchor_ratio = (anchor_time - old_start) / old_duration
  new_start = anchor_time - anchor_ratio * new_duration
  new_start = clamp(new_start, 0, fileDurationSec - new_duration)
  scheduleWaveformWindowReload()
```

要求：

- 普通滚轮绝不缩放。
- Ctrl/Cmd 缩放保持鼠标锚点时间尽量不漂移。
- 若锚点靠近 t=0 或文件末尾，因 clamp 导致的漂移按边界例外处理。
- 快速连续滚轮必须 debounce/abort stale request/requestSeq，旧响应不得覆盖新窗口。

### 5.2 键盘

| 快捷键 | 行为 |
|---|---|
| PageUp | `start_sec -= duration_sec` |
| PageDown | `start_sec += duration_sec` |
| Left | `start_sec -= duration_sec * 0.1` |
| Right | `start_sec += duration_sec * 0.1` |
| Ctrl/Cmd + `+` | 缩短时间窗，看得更细 |
| Ctrl/Cmd + `-` | 拉长时间窗，看得更长 |
| `+` | 提高振幅灵敏度，波形显示更大 |
| `-` | 降低振幅灵敏度，波形显示更小 |
| B / Esc | 浏览模式 |
| S | 选段模式 |
| X | 坏段模式 |
| C | 坏道模式 |
| R | 复位当前 viewport |
| F | 切换 filter preview |
| ? | 显示快捷键帮助 |

重绘后必须恢复波形容器焦点，保证连续按键有效。

### 5.3 鼠标拖动

| 模式 | pointer down/move/up |
|---|---|
| browse | 左键只做临时 hover/框选 zoom preview；中键拖动平移。 |
| selectSegment | 左键拖拽写入 transient；释放后更新 L2 UI draft；保存/确认后写入 L3。 |
| markBadSegment | 左键拖拽写入 transient；释放后生成 L2 坏段候选；保存/确认后写入 L3。 |
| markBadChannel | 点击通道标签或通道行切换 L2 坏道候选。 |

如果实现暂时无法支持浏览模式左键框选 zoom，允许先让浏览模式左键只显示十字光标/时间读数；但不得把左键拖动平移作为默认。

## 6. 状态栏

状态栏选择器：

```html
<div data-testid="waveform-status-bar"></div>
```

建议格式：

```text
浏览模式｜00:00:10-00:00:20｜10 s/page｜8 ch｜50 uV/row｜Raw｜准备方案：草稿未确认
```

字段要求：

1. 时间格式使用 `hh:mm:ss`，小时级 EEG 不得截断。
2. 振幅外显单位统一为 `uV/row`。
3. 写入模式必须变色并显示：“只写入准备草稿，不修改原始 EEG”。
4. 状态栏内容必须由 E2E 自动断言。

## 7. UI 布局

```text
顶部：文件 / 当前准备状态 / 非医疗边界
中部：波形区，占主要空间
波形上方：Page、时间窗、灵敏度、通道数、滤波/参考预览、模式按钮
波形内：通道标签、事件线、坏段、选段、当前模式 cursor
波形下方：状态栏 + 快捷键提示
右侧：预处理与准备方案草稿
底部：确认准备 / 下一步分析门禁
```

## 8. 审计与可撤销

坏段、坏道、恢复动作必须保留 audit 信息：

```json
{
  "action": "mark_bad_segment | restore_bad_segment | mark_bad_channel | restore_bad_channel",
  "source": "main_data_preparation_canvas",
  "mode": "markBadSegment",
  "viewport": {"start_sec": 0, "duration_sec": 10},
  "target": {},
  "reason": "user_marked",
  "created_at": "ISO-8601"
}
```

P0 只要求逐项恢复，不要求完整 undo/redo 栈。

## 9. 与现有 Canvas 契约的关系

保留现有正确地基：

- `times_sec` 统一 x 映射。
- `display_sample_rate_hz / downsampled / scale_uv / bad_segments / events` payload 归一化。
- min/max bucket 降采样。
- requestSeq / stale response ignore。
- `data_preparation_contract_version` 下游门禁。
- 教学数据保护。

新增约束：

- 输入事件不能再按网页图表默认习惯解释。
- 浏览模式和写入模式必须分离。
- 快捷键、模式按钮和状态栏必须成为验收对象。

## 10. 分析门禁设计

分析提交前统一检查：

```text
current_file_id exists
data_preparation_plan_id exists
data_preparation_revision exists
data_preparation_contract_version == "qlanalyser-data-preparation-v0.2"
```

未满足时：

- `[data-testid="analysis-preparation-gate"]` 显示阻断原因。
- PSD/ERP 提交按钮禁用，或提交时被前端拦截。
- 提供返回数据准备页/确认准备方案的操作。

满足时，分析任务 payload 必须携带：

```json
{
  "data_preparation_plan_id": "prep_xxx",
  "data_preparation_revision": 2,
  "data_preparation_contract_version": "qlanalyser-data-preparation-v0.2"
}
```
