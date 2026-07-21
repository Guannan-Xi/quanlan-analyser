# TimeChart WebGL EEG Renderer 调研交接文档（给 ClaudeCode）

日期：2026-06-27
来源：07-PM / QLanalyser 主线
接收方：ClaudeCode 对话 / 架构设计与评审
当前状态：仅调研交接，不允许直接改主工作台代码。

## 1. 背景

QLanalyser 当前的数据准备页已经形成交互式波形工作台，支持教学沙盒内置数据、波形预览、拖拽选段、剔除/恢复、坏道草稿、滤波预览和重参考设置。但用户反馈“读取太慢”，并询问是否存在更适合大文件、多通道、超高性能时序信号的开源绘图库或控件。

经过初步调研，TimeChart 是一个值得优先评估的开源 WebGL time-series 库，可能适合未来大文件 EEG 波形浏览器或高性能 renderer。当前要求是：请 ClaudeCode 进行架构设计和评审，生成详细需求文档、详细设计方案、测试文档，评审完成后再交回 07-PM 开发。不要直接改主线代码。

## 2. 当前产品约束

### 2.1 不可破坏的现有主线

- 数据准备页现有 Canvas 工作台必须保持可用。
- 教学模式与普通模式独立；教学模式内置 EEG 数据不可删除、不可覆盖、不可改名。
- QC 和重参考属于数据准备，不是分析方法。
- 癫痫源码工作台复刻当前 parked / waiting_for_lab_ready，不进入本任务。
- 不触碰 router / Headroom / gateway / IPC / model route。

### 2.2 当前数据准备工作台能力

当前已实现并通过 E2E 的能力：

- 教学数据自动波形预览。
- 数据准备页波形与预处理设置同屏。
- 波形状态条显示当前窗口、增益、选段、滤波、参考、坏道草稿、片段草稿。
- canvas 拖拽选段。
- 剔除/恢复片段。
- 坏道标记/恢复（教学模式中为非破坏性 UI 草稿）。
- PSD 教学沙盒分析不触发上传，使用内置教学项目和内置教学数据。

相关证据路径：

- `work/release_evidence/20260627-data-preparation-workbench/acceptance_packet.json`
- `work/release_evidence/20260627-data-preparation-workbench/data_preparation_workbench_e2e.json`
- `work/release_evidence/20260627-waveform-interaction/waveform_interaction_e2e.json`
- `work/release_evidence/20260626-teaching-waveform-preview/teaching_waveform_preview_e2e.json`

## 3. TimeChart 初步调研结论

### 3.1 基本信息

- GitHub：`https://github.com/huww98/TimeChart`
- npm：`timechart`
- 当前 npm 版本：`0.5.2`
- license：MIT
- npm unpacked size：约 467 KB
- 主入口：`dist/timechart.umd.js`
- module 入口：`dist/timechart.module.js`

### 3.2 官方定位

TimeChart README 描述为：

- specialized for large-scale time-series data
- built on WebGL
- high performance interaction
- supports pan / zoom
- claims 60 fps interaction for large-scale time series

### 3.3 依赖

`timechart@0.5.2` 依赖：

- `d3-axis`
- `d3-color`
- `d3-scale`
- `d3-selection`
- `gl-matrix`
- `tslib`

注意：曾临时安装试验后发现 npm audit 随依赖安装出现 high vulnerabilities；随后已卸载，当前不应把 TimeChart 依赖留在主线。ClaudeCode 需要重新评估依赖风险、license、包体积和安全策略。

### 3.4 API 关键点

基本用法：

```js
const chart = new TimeChart(el, {
  series: [{ data }],
});
```

数据格式：

```js
{ x: number, y: number }
```

其中：

- x 是相对 `baseTime` 的毫秒数。
- x 必须单调递增。
- 动态更新后，只能追加数据；调用 update 后不能编辑或删除既有数据。
- 如果 x 是 Date.now 这种大数，需用 baseTime 避免浮点精度问题。

全局参数包括：

- `lineWidth`
- `backgroundColor`
- `paddingTop / paddingRight / paddingLeft / paddingBottom`
- `xRange / yRange`
- `realTime`
- `baseTime`
- `xScaleType`
- `debugWebGL`

交互支持：

- mouse drag pan
- wheel translate X
- Ctrl + wheel zoom X
- Alt / Ctrl+Alt 支持 Y 轴操作
- trackpad pan / pinch

## 4. 与 EEG 工作台的适配推测

### 4.1 推荐初始方案：每通道一个 series

将每个 EEG 通道作为一个 TimeChart series：

```text
CH01 -> series 1
CH02 -> series 2
...
```

每个通道的 y 值增加固定 offset，实现堆叠显示。

优点：

- 原型开发最快。
- TimeChart 原生支持多 series。
- 可以控制每通道颜色、可见性、坏道状态。

风险：

- 64/128 通道时 series 数量较多，性能需实测。
- 通道名、坏道样式、事件 marker、坏段 overlay 需要额外层实现。
- EEG 的“通道行”不是普通 y 轴折线图，yRange/axis 需要特殊处理。

### 4.2 后续高性能方案：自定义 WebGL layer / 合并 buffer

如果每通道一个 series 在 64/128 通道下性能不理想，可评估自定义 WebGL 层或合并 buffer。

优点：

- 性能上限更高。
- 更像专业 EEG viewer renderer。

缺点：

- 开发量明显增加。
- 与 TimeChart 的 axes/zoom/tooltip 协同需要深入研究。

## 5. 需要 ClaudeCode 产出的文档

请先只做文档和评审，不做主线代码开发。

### 5.1 需求文档

请生成：

`docs/product/timechart_eeg_renderer_requirements_20260627.md`

必须包含：

- 用户目标：更快读取和浏览大文件、多通道 EEG。
- 适用范围：数据准备波形 renderer；不替代分析方法；不进入癫痫工作台。
- 场景：教学数据、普通上传数据、32/64/128 通道、大窗口、快速平移缩放。
- 非目标：不做诊断、不做源定位、不改 IPC/router/Headroom。
- 验收标准：首屏、pan/zoom、overlay 同步、fallback、安全和性能。

### 5.2 详细设计文档

请生成：

`docs/product/timechart_eeg_renderer_detailed_design_20260627.md`

必须包含：

- 架构图：数据读取层、windowed waveform API、renderer adapter、overlay layer、fallback Canvas。
- TimeChart adapter 设计。
- 数据模型：`WaveformWindowPayload` 到 TimeChart series 的转换。
- 通道堆叠策略。
- xRange/yRange 与 EEG 时间窗/通道行映射。
- 坏段、选段、事件 marker、坏道样式 overlay 设计。
- WebGL 不可用 fallback 方案。
- 与当前 Canvas 工作台共存方案。
- 不污染主工作台的实验页面或 feature flag 方案。

### 5.3 测试文档

请生成：

`docs/product/timechart_eeg_renderer_e2e_test_plan_20260627.md`

必须包含：

- 单元测试：数据转换、offset、range、marker 对齐。
- Playwright E2E：WebGL 初始化、渲染非空、pan/zoom、overlay 同步。
- 性能 benchmark：8/32/64/128 通道，10s/60s/300s，200/500/1000Hz。
- 兼容性：WebGL 可用/不可用、远程桌面、低端显卡、Edge/Chrome。
- 回归：现有 Canvas 工作台 E2E 必须继续通过。
- 失败门禁：性能退化、内存泄漏、overlay 偏移、无 fallback、依赖漏洞。

### 5.4 架构评审结论

请生成：

`work/release_evidence/20260627-timechart-renderer-review/claudecode_architecture_review.json`

字段建议：

```json
{
  "status": "recommended | not_recommended | conditional",
  "summary": "",
  "recommended_path": "",
  "risks": [],
  "dependency_review": {},
  "security_review": {},
  "performance_plan": {},
  "fallback_plan": {},
  "files_created": [],
  "do_not_implement_yet": true
}
```

## 6. 建议 benchmark 场景

| 场景 | 通道 | 时长 | 采样率 | 点数 |
|---|---:|---:|---:|---:|
| 轻量 | 8 ch | 10 s | 200 Hz | 16,000 |
| 常规 | 32 ch | 60 s | 500 Hz | 960,000 |
| 压力 | 64 ch | 300 s | 500 Hz | 9,600,000 |
| 极限 | 128 ch | 300 s | 1000 Hz | 38,400,000 |

建议指标：

- data generation / conversion ms
- first render ms
- pan response ms
- zoom response ms
- FPS 或 long task summary
- memory before/after
- WebGL available
- fallback triggered
- overlay sync error ms

## 7. 与其他候选库的对比要求

ClaudeCode 可在文档里简要比较：

- TimeChart：WebGL time-series，第一优先候选。
- webgl-plot：更底层，更适合自研 EEG renderer 内核。
- ChartGPU：WebGPU 潜力高，但浏览器兼容风险更大。
- uPlot：当前上线稳妥，非 WebGL，但轻量可靠。
- Squiggly：EEG 产品交互参考，不是通用绘图库。

## 8. ClaudeCode 工作边界

请严格遵守：

1. 不改 `frontend/app.js`、`frontend/index.html`、`frontend/styles.css` 的主工作台逻辑。
2. 不安装 npm 依赖到主线，除非仅在设计文档中说明；如果必须试验，先写方案，不实际执行。
3. 不触碰 router / Headroom / gateway / IPC / model route。
4. 不处理癫痫源码工作台。
5. 不提交、不 push。
6. 只生成文档和架构评审 JSON。
7. 完成后交回 07-PM，由 07-PM 决定是否进入开发。

## 9. 07-PM 当前建议

07-PM 初步倾向：

- TimeChart 值得试，但不能直接替换主工作台。
- 第一阶段只做独立 renderer benchmark 和架构评审。
- 主工作台继续保留 Canvas fallback。
- 若 TimeChart 在 32/64 通道大窗口下明显优于当前 Canvas，再做 adapter 接入。
- 若依赖风险、overlay 同步或 WebGL 兼容性不达标，则继续优化现有 Canvas + windowed API + 缓存。

## 10. 回执要求

ClaudeCode 完成后请回执：

- 是否读取本交接文档。
- 生成了哪些文档。
- 架构评审结论。
- 是否建议进入原型开发。
- 是否有依赖/security 阻断项。
- 下一步应由 07-PM 开发什么。

final_receipt 应为：

- `completed_architecture_review_documents`，或
- `blocked_architecture_review_documents` 并说明阻断原因。
