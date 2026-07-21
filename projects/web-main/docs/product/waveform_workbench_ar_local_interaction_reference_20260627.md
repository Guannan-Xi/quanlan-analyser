# 数据准备波形工作台：AR 本地版交互参考

日期：2026-06-27

## 目标

本文件用于把 `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC` 中成熟的 EEG 阅片交互，迁移为当前 Web 主干的数据准备 Canvas 工作台设计依据。迁移目标不是照搬 PyQt 界面，而是继承科研人员熟悉的操作逻辑：稳定看波形、明确定位时间、显式调整时间窗和振幅、看着波形标记片段/坏道，并且所有准备修改都可恢复。

## 本地版交互模型

### 1. Preview and Rejection

参考文件：

- `src/PreviewandRejection.py`
- `src/MatplotEventHandler.py`
- `src/Domain/HistoricalWarehouse.py`

核心逻辑：

- 时间浏览由 First / Previous / Next / Last、页码和底部 time slider 负责。
- 时间窗大小由 epoch length 和每屏 epoch 数决定。
- 振幅由 EEG amplitude / ACC amplitude 下拉控制。
- 鼠标点击和拖拽主要用于选择 epoch，不承担平移和缩放。
- Reject / Remain 修改 `Stage_Code`，Undo / Redo / Cancel All 通过历史仓库恢复。
- Apply Rejection 才真正生成新的 Raw；确认前只是编辑状态，不破坏原始数据。

### 2. BasicalAnalysisViewer

参考文件：

- `src/BasicalAnalysisViewer.py`
- `src/CustomControls.py`

核心逻辑：

- 主波形允许 X 轴浏览/缩放，Y 轴不自由拖动。
- Shift + 左键框选局部区域，用放大窗口查看细节。
- 放大窗口中 Ctrl + 滚轮可切换为 Y 轴缩放。
- 时间移动仍有 slider 和上一页/下一页。
- 振幅缩放使用显式 amplitude selector。

### 3. task_Analysis

参考文件：

- `src/task_Analysis.py`

核心逻辑：

- 波形底图保持稳定，交互优先更新分析窗口矩形和 overlay。
- 分析时间窗矩形可拖动、左右边缘可调整大小。
- 事件列表点击只移动分析窗，不重绘整张波形。
- X 轴显示窗口用显式档位：5s/page、10s/page、30s/page、60s/page、15min/page、20min/page、1h/page。
- Y 轴振幅用显式档位。
- 底部水平滚动条控制当前起点。

## Web 主干继承要求

### 必须继承

- 波形是数据准备主界面，不是静态预览图。
- 默认浏览模式不写入任何草稿。
- 写入模式与浏览模式分离：选段、坏段、坏道必须显式切换。
- 选段/坏段/坏道先进入 UI draft，可恢复；确认准备方案后才持久化。
- 普通滚轮用于水平浏览；Ctrl/Cmd + 滚轮用于时间窗缩放。
- `+/-` 调振幅；Ctrl/Cmd + `+/-` 调时间窗。
- 必须有可见的时间导航控件：First / Previous / Next / Last、时间滑块、当前窗口状态。
- 时间窗长度必须显式可选，不能只靠滚轮猜。

### 不直接继承

- 不照搬 PyQtGraph/Matplotlib 控件。
- 不把 QC、滤波、重参考、坏道坏段做成分析方法。
- 不在滚轮/拖拽时先清空 Canvas。
- 不在预览滤波时改写原始 EEG。

## 本轮 Web 验收标准

- 选择教学数据或普通数据后，波形自动加载并可见。
- 普通滚轮水平平移后，波形仍可见。
- Ctrl/Cmd + 滚轮缩放时间窗后，波形仍可见。
- First / Previous / Next / Last 能移动当前时间窗。
- 时间滑块拖动后，当前起点、状态栏和波形同步。
- 时间窗档位切换后，状态栏显示新的 `s/page`。
- 浏览模式左键不写入坏段/选段。
- 选段模式拖拽更新起止时间输入框。
- 坏段模式拖拽后进入可恢复草稿。
- 坏道标记可恢复。
- 确认数据准备后，分析任务 payload 带 `data_preparation_plan_id`、`data_preparation_revision`、`data_preparation_contract_version`。
- 教学数据受保护，不需要上传，不允许删除或覆盖。
