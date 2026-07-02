# QLanalyser 数据准备波形工作台：EDFBrowser 交互习惯需求补充

版本：2026-06-27
状态：已吸收 Codex + Claude 双评审 P0 建议的可开发基线 v2

适用范围：QLanalyser 主工作台数据准备页的 Canvas EEG 波形区、viewport 导航、选段/坏段/坏道标注、滤波预览与分析门禁。

本补充文档优先级：在“波形区如何操作”这一点上，本文件覆盖早期文档中“普通滚轮缩放、左键拖动平移”的网页图表式口径。Canvas 主线仍保持，不接入 TimeChart。

## 1. 参考依据

- EDFbrowser 官方手册：https://www.teuniz.net/edfbrowser/EDFbrowser%20manual.html
- 02｜QLanalyser 模块开发支援线程对 EDFbrowser 手感的已验证结论：普通滚轮水平浏览，Ctrl/Cmd + 滚轮缩放，PageUp/PageDown 翻页，左右箭头按当前页宽 1/10 小步移动，中键拖动水平浏览。
- Codex + Claude 双评审结论：方向正确，但必须补齐模式入口、三层写入模型、数值常量表、分析门禁 E2E 和状态栏断言后再交 07 实现。

## 2. 为什么要改

当前主工作台的波形交互如果继续沿用通用网页图表习惯，用户会很容易出现三类误操作：

1. 想翻阅 EEG，却因为滚轮默认缩放导致窗口忽大忽小。
2. 想框选一段用于坏段/分析，却因为默认拖动平移导致无法稳定选择。
3. 想连续键盘浏览，却因为焦点丢失或快捷键不统一导致只响应一次。

EEG 浏览器的核心心智不是“看一张图表”，而是“像桌面 EEG 软件一样连续阅片”。因此主工作台必须以浏览/翻页为默认，缩放和写入操作都要显式。

## 3. 用户目标

用户在数据准备页需要完成：

1. 选中 EDF/FIF 后立即看到可翻阅的 EEG 波形。
2. 用滚轮、键盘和页按钮快速沿时间轴浏览。
3. 在不误改数据准备方案的情况下缩放时间窗和调整振幅灵敏度。
4. 显式进入“选段/坏段/坏道”模式后再写入数据准备草稿。
5. 确认准备方案后，后续 PSD/ERP 等分析任务携带准备方案 id、revision 和 contract version。

## 4. P0 交互需求

### 4.1 默认浏览模式

默认进入波形页时处于“浏览模式”，所有鼠标和键盘动作只改变 viewport，不写入坏段、选段或坏道。

| 操作 | P0 行为 | 说明 |
|---|---|---|
| 普通鼠标滚轮 | 水平平移当前时间窗 | 采用 EDFbrowser Navigation 习惯；禁止普通滚轮默认缩放。 |
| Ctrl/Cmd + 鼠标滚轮 | 以鼠标所在时间点为锚点改变时间窗长度 | 对应 EDFbrowser Timescale 习惯。 |
| PageUp / PageDown | 上一页 / 下一页，移动一个当前窗口长度 | 浏览长 EEG 的主路径。 |
| Left / Right | 左右移动当前窗口宽度的 1/10 | 对应 EDFbrowser 小步浏览习惯。 |
| Ctrl/Cmd + Home / End | 跳到文件开始 / 文件末尾 | 大文件定位。 |
| 中键按住拖动 | 水平平移 | 对应 EDFbrowser 中键拖动水平浏览。 |

双击波形空白区可作为 P1 增强：回到当前事件或当前选段中心；无事件时复位到 0s。双击不是 P0 验收门槛。

### 4.2 时间缩放和振幅灵敏度分离

时间缩放与振幅灵敏度必须分开：

- 时间缩放：Ctrl/Cmd + 滚轮、Ctrl/Cmd + `+/-`、工具栏“时间窗”。
- 振幅灵敏度：普通 `+/-`、工具栏“灵敏度”、通道行内灵敏度控件。
- 状态栏必须同时显示：当前窗口起止时间、窗口长度、显示采样率、灵敏度、通道数、是否滤波预览。

术语要求：

- “缩短时间窗 / 看得更细”表示 zoom-in。
- “拉长时间窗 / 看得更长”表示 zoom-out。
- 禁止只写“放大时间窗”这种容易混淆的词。

### 4.3 模式切换入口

必须有可自动化定位的模式切换入口。

| 模式 | 入口按钮 | 快捷键 | 状态标识 | 用户含义 |
|---|---|---|---|---|
| 浏览模式 | `[data-testid="waveform-mode-browse"]` | Esc 或 B | `data-mode="browse"` | 只阅片，不写入。 |
| 选段模式 | `[data-testid="waveform-mode-select-segment"]` | S | `data-mode="selectSegment"` | 框选分析片段。 |
| 坏段模式 | `[data-testid="waveform-mode-mark-bad-segment"]` | X | `data-mode="markBadSegment"` | 标记要排除的坏段。 |
| 坏道模式 | `[data-testid="waveform-mode-mark-bad-channel"]` | C | `data-mode="markBadChannel"` | 标记或恢复坏道。 |

模式切换后，状态栏、cursor 和按钮选中态必须同步变化。进入写入模式时必须显示：“只写入准备草稿，不修改原始 EEG”。

### 4.4 三层写入模型

QLanalyser 比 EDFbrowser 多了数据准备草稿写入，因此必须把“浏览”和“写入”拆开，并明确三层写入：

| 层级 | 名称 | 触发 | 是否持久化 | 说明 |
|---|---|---|---|---|
| L1 | transient interaction | pointer move / keydown 过程中 | 否 | 只用于临时 overlay、时间读数。 |
| L2 | UI draft | pointer up 后，或点击“加入草稿” | 否，本地状态 | 更新 `#segmentStart` / `#segmentEnd`、草稿列表和状态栏。 |
| L3 | persisted preparation plan revision | 点击“保存草稿”或“确认准备” | 是 | 写入 data preparation plan，产生 revision。 |

默认浏览模式不得写入 L2/L3。选段模式 pointer up 只允许写入 L2；只有明确保存/确认才写入 L3。

### 4.5 写入型操作

| 模式 | 左键拖拽 | 结果 |
|---|---|---|
| 浏览模式 | 框选放大或不写入的临时选区 | 不写入准备方案；不得新增坏段/选段草稿。 |
| 选段模式 | 创建/调整分析选段 | 释放后写入 L2 UI draft；保存/确认后进入 L3。 |
| 坏段模式 | 创建坏段候选 | 释放后写入 L2 UI draft，显示撤销入口；保存/确认后进入 L3。 |
| 坏道模式 | 点击通道标签或通道行 | 标记/恢复坏道候选，保留 audit 记录。 |

### 4.6 统一数值常量

实现和 E2E 必须使用同一组常量；如后续要调整，必须同时改需求、设计和测试。

| 常量 | 默认值 | 说明 |
|---|---:|---|
| wheelPanRatio | 0.08 | 普通滚轮每次移动当前窗口 8%。 |
| arrowPanRatio | 0.10 | Left/Right 每次移动当前窗口 10%。 |
| pagePanRatio | 1.00 | PageUp/PageDown 每次移动一个当前窗口。 |
| zoomFactor | 1.20 | Ctrl/Cmd + 滚轮或 Ctrl/Cmd + `+/-` 的缩放因子。 |
| minDurationSec | max(0.5, 20 / display_sample_rate_hz) | 最短显示窗口。 |
| maxDurationSec | min(fileDurationSec, 300) | P0 上限；大文件全局浏览以后交给 mini map/P1。 |
| gainStepRatio | 1.20 | 普通 `+/-` 的振幅灵敏度步进。 |
| minSensitivityUvPerRow | 5 | 防止过度放大。 |
| maxSensitivityUvPerRow | 500 | 防止过度压扁。 |
| anchorDriftToleranceSec | max(0.05, 2 / display_sample_rate_hz) | 锚点缩放容差；t=0 或文件末尾 clamp 时允许按边界例外判定。 |

### 4.7 专业 EEG 视觉反馈

波形区状态栏必须始终可见以下状态：

- 当前模式：浏览 / 选段 / 坏段 / 坏道。
- 当前时间窗：`hh:mm:ss-hh:mm:ss`、duration。
- 当前时标：例如 `10 s/page`。
- 当前振幅灵敏度：统一使用 `uV/row`，不要同时混用 `gain_px_per_uv`、`gain`、`uV/row` 三套外显单位。
- 当前滤波/参考是否只是 preview。
- 当前准备方案状态：未确认 / 草稿已保存 / 已确认。

状态栏必须有稳定选择器：`[data-testid="waveform-status-bar"]`。

### 4.8 非医疗边界

所有文案使用“科研数据准备 / 质量检查 / 预览 / 标记 / 分析前准备”，不得使用“诊断、治疗、医疗决策、癫痫自动诊断”等承诺性表述。

### 4.9 分析门禁

未确认数据准备方案时，PSD/ERP 等分析入口必须被 `[data-testid="analysis-preparation-gate"]` 阻止。

确认准备方案后，后续分析任务 payload 必须携带：

- `data_preparation_plan_id`
- `data_preparation_revision`
- `data_preparation_contract_version == "qlanalyser-data-preparation-v0.2"`

这条是 P0，不得只写在 E2E 中。

## 5. P1 体验增强

1. Mini map：显示完整文件长度、当前 viewport、坏段、事件。
2. 事件跳转：点击事件 marker 或事件列表时居中到事件窗口。
3. 键盘帮助层：`?` 打开快捷键说明。
4. Shift + 滚轮可加速到当前窗口 50%。
5. 焦点保持：任一快捷键触发重绘后，焦点回到波形容器，支持连续按键。
6. 双击波形空白区复位或居中当前事件。

## 6. 明确废弃的旧口径

以下早期口径不再作为主工作台验收标准：

- 普通滚轮默认缩放。
- 左键拖动默认平移。
- Ctrl/Cmd + 滚轮默认改振幅增益。
- 只靠按钮上一段/下一段，不支持键盘阅片。
- 波形区只作为静态预览图，不承担主交互。
