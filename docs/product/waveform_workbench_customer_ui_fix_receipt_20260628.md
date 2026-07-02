# WaveformWorkbench 客户级交互整改回执（2026-06-28）

## 1. 本轮目标

基于客户最终版视角，对独立 `WaveformWorkbench` 的界面交互、信息层级、按钮逻辑和科研语义进行评审，并按本地文档执行第一轮整改。

详细评审与整改方案已保存：

```text
docs/product/waveform_workbench_customer_final_interaction_review_20260628.md
```

## 2. 主要整改

### 2.1 工具条从“控件堆”改为任务分区

改动前：

- 浏览、时间窗、事件显示、灵敏度、通道数、标注模式、Epoch 控件平铺在一行。
- 客户需要先理解所有控件才知道下一步。

改动后：

- 浏览：第一页/上一页/下一页/末页，并说明滚轮和 Ctrl/⌘+滚轮。
- 显示：时间窗、事件标记、每行振幅、振幅细调、显示通道数，并注明只影响屏幕预览。
- 标注模式：浏览、选段、Epoch 复核、候选坏段、坏道、快捷键，并注明默认浏览不写草稿。
- Epoch：长度和显示数量，并注明用于固定时间片批量复核。

### 2.2 去掉客户界面中的实现噪音

改动前：

- overview caption 会显示长串加载区间，例如 `0.0-60.0s, 0.0-24.0s...`。
- 底部状态 chips 暴露缓存/加载实现细节。

改动后：

- overview caption 改为：

```text
全程 ... · 当前 ... · 当前窗口已缓存，可连续浏览 · 竖线为事件标记（非断点）
```

- meta/status 默认只显示客户能理解的信息：当前窗口、通道数、显示采样、当前窗已缓存、单位、Raw、草稿计数。
- chunk/cache/prefetch 仍保留在 `data-*` 测试状态中，不暴露给客户默认界面。

### 2.3 右侧操作区从“按钮堆”改为下一步处理

改动前：

- 无选区时仍显示 Reject/Remain 灰色按钮，容易给客户“不可用”的第一印象。
- 草稿摘要是文字日志，扫读困难。

改动后：

- 右侧标题改为“下一步处理”。
- 无选区时隐藏 Reject/Remain 主处理按钮，只保留“请先选择波形或切换 Epoch 复核”的下一步提示。
- 有选区后才显示 `剔除 Reject` / `保留 Remain`。
- 草稿摘要改成网格卡片：当前选区、Epoch、候选坏段、剔除、保留、坏道、可恢复、撤销/重做。
- 危险操作增加“危险操作”分区，降低误点风险。

### 2.4 事件线语义降噪

改动前：

- 图例只写“事件/注释”，教学 oddball 数据中竖线较密，容易被误解为数据断点。

改动后：

- 图例改为 `事件标记（非断点）`。
- overview caption 明确“竖线为事件标记（非断点）”。
- 默认事件线透明度进一步降低，波形优先。

## 3. 改动文件

```text
frontend/waveform-workbench.html
frontend/waveform-workbench.css
frontend/waveform-workbench.js
scripts/e2e_waveform_workbench_module.mjs
docs/product/waveform_workbench_customer_final_interaction_review_20260628.md
docs/product/waveform_workbench_customer_ui_fix_receipt_20260628.md
```

## 4. 验证证据

Evidence directory:

```text
work/release_evidence/20260628-waveform-customer-ui-review-fix/
```

Key evidence:

```text
work/release_evidence/20260628-waveform-customer-ui-review-fix/waveform_workbench_e2e_result.json
work/release_evidence/20260628-waveform-customer-ui-review-fix/01_initial_loaded.png
work/release_evidence/20260628-waveform-customer-ui-review-fix/04_after_write_mode_draft.png
```

Static checks:

```text
node --check frontend/waveform-workbench.js
node --check scripts/e2e_waveform_workbench_module.mjs
```

Result:

```text
passed
```

Browser E2E:

```text
status=passed
checks=41
failed=[]
```

Key accepted checks:

```text
T-VIS-01-initial-canvas-has-visible-waveform-ink
T-UI-01-empty-state-does-not-promote-disabled-write-actions
T-UI-02-selection-promotes-review-actions
T-CONT-05-overview-visible-without-cache-log-noise
T-PERF-02-wheel-pan-uses-cache-hit-not-legacy-task
```

## 5. 视觉复核

人工查看截图：

- 首屏波形可见。
- 工具条分区比旧版更容易理解。
- 无选区时右侧不再突出灰色 Reject/Remain 按钮。
- 选区后右侧显示明确的 Reject/Remain 下一步。
- 页面不再在客户可见区域显示长串缓存区间。
- 事件标记已说明为非断点。

当前成熟度：

```text
good usability -> 接近 polished and professional
```

仍建议后续继续精修：

- 降低首屏工具条高度，让波形区域再上移。
- 增加真实数据文件信息弹窗：原始采样率、参考、通道位置、注释数量、显示降采样策略。
- 补窄屏客户级截图矩阵。
- 用真实授权 EDF 做人工可用性走查。

## 6. 边界

本轮未改：

- 后端算法和 chunk API。
- 主工作台。
- PSD/ERP/PAC/癫痫模块。
- router / Headroom / gateway / IPC / model route。
- TimeChart。

final_receipt: completed_waveform_workbench_customer_ui_fix_ready_for_acceptance
