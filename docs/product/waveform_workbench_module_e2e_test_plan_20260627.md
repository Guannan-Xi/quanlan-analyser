# WaveformWorkbench 独立模块 E2E 测试文档

版本：2026-06-27  
分支：`feature/waveform-workbench-edfbrowser-v2`

## 1. 测试目标

验证独立 WaveformWorkbench 达到 EDFbrowser 风格阅片交互，并能在教学数据和普通合成数据上稳定显示波形、浏览、缩放、标记草稿、保存准备方案。

## 2. 证据目录

```text
work/release_evidence/20260627-waveform-workbench-module/
```

每次 E2E 输出：

- `waveform_workbench_e2e_result.json`
- `01_initial_loaded.png`
- `02_after_wheel_pan.png`
- `03_after_ctrl_zoom.png`
- `04_after_write_mode_draft.png`
- `05_after_scroll_persistence.png`
- `artifact_inventory.json`

## 3. T-WF 测试矩阵

### T-WF-01 教学数据自动加载

步骤：

1. 打开 `waveform-workbench.html?teaching_demo=auto&api=http://127.0.0.1:8001/api`。
2. 等待最多 10 秒。
3. 检查 Canvas 可见，空态隐藏。

断言：

- 文件名包含 `teaching_oddball`。
- 状态栏包含 `8 ch`、`uV/row`、`Raw`。
- 元数据包含 `8 / 8 个通道`。
- 截图中可见多通道彩色波形。

### T-WF-02 复用已有预览任务

步骤：

1. 调用 `/api/lab/demo/dataset`。
2. 确认返回 `qc_preview_task.status=completed`。
3. 打开工作台。

断言：

- 页面优先恢复已有 artifact。
- 不重复创建多个并发 `qc_waveform_preview` 任务。
- 10 秒内显示波形。

### T-WF-03 普通滚轮水平浏览

步骤：

1. 记录初始 `viewport.startSec`。
2. 在 Canvas 上普通滚轮。
3. 读取状态栏和 debug state。

断言：

- startSec 改变约 `durationSec * 0.08`。
- durationSec 不变。
- 无草稿新增。

### T-WF-04 Ctrl/Cmd + 滚轮锚点缩放

断言：

- durationSec 按 1.20 因子变化。
- 鼠标锚点时间漂移不超过 `max(0.05, 2/display_sample_rate_hz)`，边界 clamp 例外。
- startSec 合法。

### T-WF-05 PageUp/PageDown 翻页

断言：

- PageDown 后 startSec 增加约一个 durationSec。
- PageUp 后回到上一页。
- 焦点不丢失。

### T-WF-06 Left/Right 小步移动

断言：

- Left/Right 步长约 `durationSec * 0.10`。
- 状态栏时间同步。

### T-WF-07 振幅和时间缩放分离

断言：

- `+/-` 只改变 `uV/row`，不改变 durationSec。
- Ctrl/Cmd + `+/-` 只改变 durationSec。

### T-WF-08 浏览模式不写草稿

步骤：

1. 确认 mode=browse。
2. 左键拖动 Canvas。

断言：

- selectedSegment、badSegments、badChannels 均不增加。
- 状态栏提示浏览/测量。

### T-WF-09 选段模式写 UI draft

断言：

- 切换 selectSegment 后拖动生成 selectedSegment。
- 仍未写后端 revision。
- 草稿可清除。

### T-WF-10 坏段模式写 UI draft 并可恢复

断言：

- 切换 markBadSegment 后拖动新增 badSegment。
- 点击恢复后 moved to restoredSegments 或从 badSegments 移除。
- auditActions 增加。

### T-WF-11 坏道模式点击通道标签

断言：

- 点击通道标签新增 badChannel。
- 再次点击或恢复按钮可恢复。

### T-WF-12 状态栏完整性

状态栏必须包含：

- 模式。
- 起止时间。
- s/page。
- 通道数。
- uV/row。
- Raw/Filter。
- 准备方案状态。

### T-WF-13 页面滚动后波形保留

步骤：

1. 首屏确认波形显示。
2. 页面向下滚动。
3. 再回到波形区域。

断言：

- 空态不重新出现。
- Canvas 仍显示当前波形或快速恢复。
- 状态栏不丢失。

### T-WF-14 保存准备方案 payload

断言：

- 确认准备后，后端返回 plan id/revision。
- 后续分析 payload 包含：
  - `data_preparation_plan_id`
  - `data_preparation_revision`
  - `data_preparation_contract_version == qlanalyser-data-preparation-v0.2`

### T-WF-15 禁止范围扫描

断言 git diff 不包含：

- router
- Headroom
- gateway
- IPC
- model route
- TimeChart dependency
- epilepsy workbench

## 4. 失败即阻断

任一项失败不得集成回主数据准备页：

- 数据选中后 Canvas 仍显示等待选择。
- 普通滚轮缩放而不是平移。
- 浏览模式误写草稿。
- 快速切换窗口后旧响应覆盖新窗口。
- 教学数据可删除或覆盖。
- E2E 没有截图/JSON 证据。
