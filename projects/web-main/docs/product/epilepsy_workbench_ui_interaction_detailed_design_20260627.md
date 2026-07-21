# 癫痫工作台 UI/交互重构详细设计

版本：2026-06-27
实现范围：实验室癫痫工作台第一阶段 P0。

## 1. 设计总览

第一阶段新增一个前端轻量控制层：

```text
EpilepsyWaveformViewportController
```

它不是独立文件，而是先在 `frontend/epilepsy-workbench.js` 内以一组状态字段和函数落地，避免改动范围过大。后续若进入 07 主干，可提取为独立 adapter。

## 2. 状态设计

新增状态：

```js
state.waveformViewport = {
  startSec: null,
  durationSec: null,
  lastEventId: ""
}

state.waveformInteraction = {
  mode: "browse",      // browse | correct
  gain: "auto",        // auto | 0.5 | 1 | 2 | 4
  isDragging: false
}
```

现有状态继续保留：

- `activeWaveformLabel`
- `waveformRenderer`
- `waveformWindow`
- `waveformEventId`
- `timechartMetrics`

## 3. Viewport 计算

### 3.1 默认事件窗口

沿用当前事件窗口策略：

```text
start = event.start_sec - 2s
duration = clamp(event.duration_sec + 4s, 6s, 30s)
```

并 clamp 到 EDF 总时长。

### 3.2 当前窗口

`runWaveformPreview()` 不再直接总是计算默认事件窗口，而是读取：

```text
state.waveformViewport.startSec
state.waveformViewport.durationSec
```

如果为空，才回到默认事件窗口。

### 3.3 匹配逻辑

`waveformWindowMatchesActiveView()` 除滤波 profile 外，还要检查：

- payload.start_sec 与 viewport.startSec 接近。
- payload.stop_sec - payload.start_sec 与 viewport.durationSec 接近。

避免用户平移/缩放后仍显示旧窗口。

## 4. 事件设计

### 4.1 鼠标滚轮

绑定在波形 frame：

```text
data-waveform-interactive="true"
```

处理：

- 普通 wheel：zoomAt(anchorTime, factor)。
- Shift+wheel：panBy(deltaSec)。
- Ctrl/Cmd+wheel：setGain(next/previous)。

每次 viewport 变化后：

```text
clear stale waveformWindow
render()
scheduleWaveformPreview()
```

### 4.2 拖拽平移

pointerdown 记录起点。
pointermove 根据 dx 换算 deltaSec。
pointerup 触发 debounced waveform-window 请求。

本阶段不做框选修正，避免拖拽平移和 epoch 修改冲突。

### 4.3 键盘

全局 keydown 中忽略输入框/textarea/select。

- `ArrowLeft/ArrowRight` 平移。
- `+/-` 缩放。
- `R` 回到事件窗口。
- `F` 切 Raw/Filter。
- `E` 切浏览/矫正模式。
- Shift+1/2 只有矫正模式生效。

## 5. UI 设计

### 5.1 波形状态条

显示：

```text
File | Event | Window | Filter | Gain | Renderer | Mode
```

### 5.2 mini map

基于 `recordingDurationSec()`、当前 viewport 和 selected event 生成纯 HTML/CSS 比例条：

```text
full duration bar
current viewport block
event block
```

### 5.3 模式按钮

在波形工具栏加入：

```text
Browse mode
Correction mode
```

矫正按钮禁用规则：

- 浏览模式：Seizure / Normal 修改按钮 disabled。
- 矫正模式：按钮启用。
- 待复核按钮可在浏览模式下使用，因为它不改 Stage_Code。

## 6. Renderer 适配

### 6.1 SVG

继续使用 `renderWaveformWindow(payload)`，但外层 viewport 由 controller 管理。

### 6.2 TimeChart

继续使用 `renderTimeChartHost(payload)` 和 `hydrateWaveformRenderer()`。

TimeChart 输入仍是 `/waveform-window` 返回的 raw/minmax 数据；不修改 ML 和事件语义。

## 7. 性能与失败处理

- `scheduleWaveformPreview()` debounce 约 180-250 ms。
- 只要 viewport/filter/event 变化，先清空旧 payload，避免视觉假匹配。
- TimeChart 失败时保留 SVG fallback。
- `/waveform-window` 失败显示 error empty state，不吞掉异常。

## 8. 安全边界

- 浏览模式是默认模式。
- `applyStageToSelection()` 在非矫正模式下直接拒绝。
- `markSelectedEvent("seizure_candidate"|"normal")` 也必须经过模式检查。
- 待复核不改变 Stage_Code，可保留。

## 9. 文件范围

本阶段允许修改：

- `frontend/epilepsy-workbench.js`
- `frontend/epilepsy-workbench.css`
- `frontend/epilepsy-workbench.html` 仅版本号
- `scripts/e2e_epilepsy_timechart_lab.mjs`
- `docs/product/epilepsy_workbench_ui_interaction_requirements_20260627.md`
- `docs/product/epilepsy_workbench_ui_interaction_detailed_design_20260627.md`
- `docs/product/epilepsy_workbench_ui_interaction_e2e_test_plan_20260627.md`

禁止修改：

- router / Headroom / gateway / IPC
- backend ML 参数
- 07 主工作台入口
- Band Power / PSD 语义

## 10. Stage_Code FSM 详细设计

前端入口统一经过 `applyStageToSelection(stageCode, context)`。该函数必须执行：

1. 非 Correction mode 直接拒绝，提示用户当前是浏览模式。
2. 将输入归一为数字 enum，只允许 `0` 和 `1`。
3. 与源 Stage_Code 相同则删除 override，保持源产物只读。
4. 与源 Stage_Code 不同则写入 `epochOverrides[index] = stageCode`。
5. 写入 `reviewActions`，action 固定为 `set_stage`，保留 event、epoch range、source、created_at。

后续 P1 需要把该入口扩展为 FSM validator：

```text
validateStageTransition({ before, after, mode, baseRevision, sourceHash })
```

返回：

```text
allow | reject_with_reason | rollback_required
```

非法迁移不进入 `reviewActions`，也不进入导出。

## 11. 边界与隔离设计

本实验台只读依赖：

- EDF 文件列表和 `/waveform-window`。
- `epilepsy_ml_xgboost` 或 `epilepsy_std_threshold` 已生成的源 artifact。
- 本地 review layer、review session patch/export。

明确不依赖、不写入：

- 07 主工作台路由。
- router / Headroom / gateway / IPC。
- backend ML 模型参数、scaler、feature order、threshold。
- Band Power / PSD 模块状态和语义。

如果未来接入 07，必须通过独立 adapter 注入，而不是把实验台页面直接并入主工作台。

## 12. P1/P2 技术设计占位

P1：

- 抽出 `EpilepsyWorkbenchShell`、`EpilepsyWaveformViewportController`、`EpilepsyReviewSessionStore`。
- 引入 source artifact hash、base revision、optimistic lock。
- 任务执行 UI 使用 async task state machine：idle / pending / running / completed / failed / canceled。
- 性能证据从单次响应升级为 p95/p99 窗口读取与渲染。

P2：

- 事件批量导航、复核历史 diff、热键帮助层、可访问性测试。
- TimeChart/SVG/Canvas renderer adapter 矩阵。
- 大通道/长窗口/弱机器降级策略。
