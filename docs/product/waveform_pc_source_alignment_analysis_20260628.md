# QLanalyser PC 端波形显示源码对齐分析

日期：2026-06-28

目标：基于 `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC` 的真实源码，分析 PC 端 QLanalyser 的波形显示、浏览、缩放、平移、坏段剔除和人工修正逻辑，并给出 Web 版 `WaveformWorkbench` 的对齐要求。

本文件只做源码分析和产品/工程对齐，不直接改代码。

## 1. 源码范围

### 1.1 PC 端参考源码

重点读取文件：

- `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC\src\BasicalAnalysis.py`
- `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC\src\PreviewandRejection.py`
- `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC\src\MatplotEventHandler.py`
- `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC\view\BasicalAnalysis.ui`
- `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC\view\PreviewandRejection.ui`

### 1.2 当前 Web 端相关源码

重点读取文件：

- `D:\Quanlan\Codes\Python\quanlan-analyser-official\frontend\app.js`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\frontend\waveform-workbench.html`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\frontend\waveform-workbench.js`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\frontend\waveform-workbench-adapter.js`
- `D:\Quanlan\Codes\Python\quanlan-analyser-official\eeg_core\preprocess\qc_preview.py`

## 2. PC 端波形显示分为两类

PC 端源码里实际有两套波形页面，它们承担的产品职责不同。

### 2.1 `BasicalAnalysis.py`：基础分析前的波形浏览页

这个页面更像“基础预览 + 分析入口”。

核心特征：

- 使用 `Matplotlib Figure + FigureCanvas` 嵌入 PyQt。
- Canvas 放在 `QScrollArea` 中，允许大量通道纵向滚动。
- 时间窗通过下拉框选择：`1s / 5s / 30s / 60s / 90s / 3min / 15min / 60min / 90min / 12hour / 24hour`。
- 默认时间窗是 `30s`。
- 振幅通过下拉框选择：`1uV / 10uV / 50uV / 100uV / 200uV / 500uV / 1000uV / 2000uV / 5000uV / 7000uV / 10000uV`。
- 默认振幅是 `200uV`。
- 翻页是整页跳转：上一页、下一页、输入页码。
- 每个通道单独一个 subplot，Y 轴范围固定为 `[-scale_amplitude, scale_amplitude]`。
- 大时间窗时用非常简单的降采样：当 `scale_seconds > 30` 时，`downsample_factor = int(scale_seconds / 30)`。
- 分析入口如 Band Power、Time-frequency、PSD 直接接收 `raw_cropped`。

产品含义：

基础分析页的核心不是精细坏段剔除，而是让用户先看到当前数据，选择时间跨度和振幅，再进入具体分析。

### 2.2 `PreviewandRejection.py`：预处理/坏段剔除页

这个页面才是当前 Web `数据准备 + 波形工作台` 最应该对齐的核心。

核心特征：

- 也是 PyQt + Matplotlib，但有更完整的人工阅片/剔除工作流。
- 页面顶部提供 `Reject / Remain / Redo / Undo / Cancel All`。
- 时间轴不是任意秒级选择，而是基于 epoch：
  - `epoch_length` 来自顶部下拉框，典型值包括 `0.5 / 1 / 2 / 4` 秒。
  - 一屏显示多少个 epoch 由 `combobox_select_n_epochs` 控制。
  - 当前窗口长度 = `epoch_length * n_epochs_display`。
- 使用 time slider 直接定位到某个时间偏移。
- 通道分层：
  - 不含 `ACC` 的通道绘制到第一块 EEG canvas。
  - 包含 `ACC` 的通道绘制到第二块 ACC canvas。
- EEG 和 ACC 的振幅控制分开：
  - EEG 振幅来自 `combobox_eeg`。
  - ACC 振幅来自 `combobox_acc`。
  - 支持 `Auto`。
- 绘图时固定降采样 `downsample_factor = 5`。
- 波形线条是黑色细线，通道之间用浅灰分隔线。
- 已 Reject 区间用红色半透明覆盖。
- 当前选中的 epoch 用粉色半透明覆盖。
- 选中、拖拽、取消选择由 `MatplotEventHandler.py` 处理。
- 人工修改写入 `df_score`：
  - `Stage_Code = 0` 表示 Remain。
  - `Stage_Code = 1` 表示 Reject。
  - `Stage` 文本同步为 `Remain / Reject`。
- Undo/Redo 通过 `EventScoreWH` 保存变更栈。
- `confirm_rejected_data()` 会把 Reject epoch 合并成连续区间，并真正生成新的 `mne.io.RawArray`。
- 保存时可导出新的 EDF。

产品含义：

PC 端预处理的核心不是“画一张图”，而是“按 epoch 做人工判读，并保留 Reject/Remain 的状态机”。用户要能看到波形、选择片段、标坏、恢复、撤销、确认，再把准备后的数据交给后续分析。

## 3. PC 端交互模型

### 3.1 浏览/定位

PC 端主要通过三种方式定位：

- 上一页 / 下一页。
- 页码输入。
- time slider。

PC 端源码没有把滚轮作为主要水平浏览入口。滚轮更多由 `QScrollArea` 自然承担纵向通道滚动。对 Web 来说，可以保留 EDFBrowser 风格的滚轮水平浏览，但不能因此丢掉 PC 端的页/滑块/epoch 工作流。

### 3.2 时间窗

PC 端有两种时间窗语义：

- 基础分析页：时间窗是 `1s` 到 `24hour` 的整页浏览窗口。
- 预处理页：时间窗由 `epoch_length * n_epochs_display` 决定。

Web 对齐建议：

- 普通波形浏览保留 `5s / 10s / 30s / 60s / 300s`。
- 预处理/剔除模式增加 epoch 视角：
  - epoch length：`0.5 / 1 / 2 / 4 s`。
  - visible epochs：`25 / 50 / 100 / All` 或类似方案。
  - 状态栏显示 `epoch length`、`visible epochs`、当前 epoch 范围。

### 3.3 振幅

PC 端基础分析页用固定 uV 下拉框，预处理页还支持 Auto。

Web 现在主页面和独立工作台使用 `uV/row` 或 gain slider。方向是对的，但需要补两点：

- 给科研用户一个固定档位入口：`50 / 100 / 200 / 500 / 1000 uV/row`。
- 保留细调 slider，但不要只给 slider。科研用户常按固定档位复核波形。

### 3.4 选择

PC 端选择是 epoch-based：

- 单击一个 epoch。
- 拖拽选择连续 epoch。
- 再次点击可取消。
- 选区同步覆盖 EEG 和 ACC 两个画布。

Web 现在是任意秒级拖拽选段，适合灵活标注，但与 PC 端预处理剔除习惯还不完全一致。

Web 对齐建议：

- 保留秒级自由选段，用于普通标注。
- 新增“按 epoch 标记”模式：
  - 鼠标落点先转换为 epoch index。
  - 拖拽时选中 `[start_epoch, end_epoch]`。
  - 最终草稿保存为 epoch 列表和秒级区间两种表示。
  - UI 显示“已选择 12-18 epoch，48.0-76.0 s”。

### 3.5 Reject / Remain

PC 端有明确的 `Reject` 和 `Remain` 动作。这个比 Web 当前“候选坏段 / 确认剔除 / 恢复”更符合人工复核语义。

Web 对齐建议：

- 写入模式下提供两个主动作：
  - `标为剔除 Reject`
  - `标为保留 Remain`
- `Remain` 不是普通取消按钮，它表示用户看过并确认该 epoch/片段保留。
- 已 Reject 的片段可以被 Remain 覆盖。
- Remain 操作也应进入 audit trail。

### 3.6 Undo / Redo / Cancel All

PC 端有完整 Undo/Redo/Cancel All。

Web 当前已有部分恢复/清空，但要对齐 PC 端，应该形成明确的操作栈：

- `undoStack`：每次 Reject/Remain/坏道/恢复都入栈。
- `redoStack`：Undo 后可 Redo。
- `Cancel All`：清空当前草稿或回到上次确认状态，必须弹出确认。
- 所有动作写入 audit action，包括时间、操作者、对象、旧状态、新状态。

### 3.7 Confirm / Apply

PC 端 `confirm_rejected_data()` 会真正拼接 Raw，生成新的 `RawArray`，这在 Web 端不应原样继承。

Web 更合理的安全模型：

- 原始 EEG 永不改写。
- 用户所有动作先写入 UI draft。
- 点击“确认数据准备”后生成 `data_preparation_plan_id` 和 revision。
- 后续 PSD、Band Power、TFR、PAC、Connectivity、ERP、CSD 等分析任务必须携带准备方案。
- 如果需要物理导出准备后数据，应作为单独导出 artifact，而不是覆盖原文件。

这是 Web 版应优于 PC 端的地方。

## 4. 当前 Web 实现现状

### 4.1 已经具备的能力

当前 Web 主页面和独立 `waveform-workbench.html` 已具备这些基础：

- Canvas 多通道波形绘制。
- 教学数据自动加载。
- `/api/tasks` 调用 `module_name=qc`、`workflow_id=qc_waveform_preview` 生成 `waveform_preview.json`。
- `waveform_preview.json` 包含：
  - `start_sec`
  - `duration_sec`
  - `file_duration_sec`
  - `sfreq_display`
  - `channels`
  - `times_sec`
  - `data_uv`
  - `annotations`
- 前端可对 artifact 做 normalize。
- 支持 `Raw / Filter` 预览，且后端文案明确 filter 仅用于预览，不修改原始文件。
- 普通滚轮水平浏览。
- Ctrl/Cmd + 滚轮按鼠标锚点缩放。
- PageUp / PageDown 翻页。
- Left / Right 小步移动。
- `+ / -` 调整振幅。
- `Ctrl/Cmd + +/-` 调整时间窗。
- S / X / C / B 切换选段、候选坏段、坏道、浏览模式。
- 浏览模式和写入模式分离。
- 坏段先进入候选，再确认剔除，可恢复。
- 后端 QC preview 不改写上传文件。

### 4.2 Web 当前实现与 PC 端不一致处

#### G1. 缺少 PC 端的 epoch 主工作流

当前 Web 以秒级窗口为主，没有把 `epoch_length` 和 `visible_epochs` 作为预处理剔除的主语义。

影响：

- 用户不能像 PC 端一样按 epoch 快速判读。
- Reject/Remain 的对象不够稳定。
- 后续审计很难回答“第几个 epoch 被谁标成 Reject”。

#### G2. 缺少 `Remain` 主动作

当前 Web 有恢复，但没有“标为保留 Remain”的正向动作。

影响：

- 对人工复核来说，Remain 是“我确认这个片段没问题”，不是“撤销剔除”。
- 对科研质控来说，Remain 应该进入审计记录。

#### G3. Undo/Redo 还不够像 PC 端

当前 Web 有恢复/清空，但不是完整操作栈。

影响：

- 用户误标以后缺少专业工具的安全感。
- 多步批量操作后无法逐步回退。

#### G4. EEG/ACC/EMG 分层显示不足

PC 端明确把 ACC 放到第二画布。Web 当前主要是通道列表前 N 个显示。

影响：

- EEG 与运动/肌电辅助通道混在一起时，可读性变差。
- 对科研人员判断运动伪迹、肌电伪迹不够友好。

#### G5. 当前后端 preview window 仍有 30s 上限

`eeg_core/preprocess/qc_preview.py` 中 `MAX_DURATION_SEC = 30.0`。前端已经支持 300s 时间窗，但后端 `qc_waveform_preview` 对单次 preview 请求仍限制 30s。

影响：

- Web 前端显示 300s 工作台时，真实窗口数据可能受后端限制。
- 可能出现“界面窗口是 300s，但 artifact 只有 30s”的错觉。

建议：

- 短期：Web UI 中明确“30s 以内为真实高精度窗口，长窗口用分段/概览读取”。
- 中期：后端新增 windowed waveform endpoint 或支持分块读取。
- 长期：建立 pyramid / min-max bucket 数据结构，保证 300s、15min、1h 的大窗也能科学显示。

#### G6. 降采样策略需要更科学

PC 端基础分析用 `scale_seconds / 30` 简单降采样，预处理页固定 `downsample_factor=5`。Web 后端现在 `_window_data()` 超过 `MAX_DISPLAY_POINTS=1200` 时用等距抽点。

风险：

- 等距抽点可能漏掉窄峰、尖波、瞬态伪迹。
- 对 EEG 质控来说，漏掉尖峰比画得慢更严重。

建议：

- 当前窗口绘制应优先使用 min-max bucket，而不是单点抽样。
- 对大窗口概览，每个 bucket 至少保留 min/max，必要时保留 first/last。
- 后端 payload 需要显式标记 `downsample_method = min_max_bucket`。

#### G7. 坏段确认语义需要更接近科研流程

PC 端状态是 `Stage_Code`，一眼可见 Remain/Reject。

Web 应补一个“准备草稿状态条/epoch strip”：

- 未查看：灰色。
- 当前选中：粉色。
- 候选坏段：黄色。
- 已 Reject：红色。
- 已 Remain：蓝色或绿色细边。
- 已恢复：灰色虚线。

这能让用户在不滚动整页的情况下知道整段数据的人工复核进度。

## 5. PC -> Web 功能映射表

| PC 功能 | 源码位置 | Web 当前状态 | 对齐建议 |
| --- | --- | --- | --- |
| Matplotlib 多通道波形 | `BasicalAnalysis.update_plot` / `PreviewandRejection.update_plot` | Canvas 已实现 | 保留 Canvas，不回退到静态图 |
| 时间窗下拉 | `comboBox_1_list` | 已有时间窗输入/预设 | 增加科研固定档位 |
| 振幅下拉 | `comboBox_2` / `combobox_eeg` / `combobox_acc` | 已有 gain/uV 控制 | 增加固定 uV/row 档位和 Auto |
| 页码/上一页/下一页 | `previous_page` / `next_page` | 已有按钮和快捷键 | 保留，并让 PageUp/PageDown 对齐整页 |
| time slider | `widget_time_slider` | 已有 slider | 保留，快速切换时忽略旧响应 |
| epoch length | `combobox_epoch_length` | 未充分产品化 | P0 补齐 |
| visible epochs | `combobox_select_n_epochs` | 未充分产品化 | P0 补齐 |
| 单击 epoch | `MatplotlibEventHandler.on_released` | 秒级点击/拖拽 | 增加 epoch snap |
| 拖拽 epoch 范围 | `MatplotlibEventHandler.on_dragged` | 秒级拖拽 | 增加 epoch range select |
| Reject | `user_edit_stage("Reject")` | 候选坏段/确认剔除 | 增加 Reject 主动作 |
| Remain | `user_edit_stage("Remain")` | 只有恢复语义 | 增加 Remain 主动作 |
| Undo/Redo | `EventScoreWH` | 不完整 | P0 补操作栈 |
| Cancel All | `reset_edit` | 有清空但语义需收敛 | 对齐为清空当前草稿/回到上次确认 |
| 红色 Reject 覆盖 | `_add_rejection_regions` | 已有红/黄覆盖 | 加图例和 epoch strip |
| 粉色选区 | `axvspan` / Rectangle | 已有选段覆盖 | 对齐颜色和状态 |
| ACC 独立画布 | `first_canvas_channels` / `second_canvas_channels` | 未完整分层 | 增加 EEG/ACC/EMG 分组显示 |
| Apply Rejection 生成新 Raw | `confirm_rejected_data` | Web 走 preparation plan | 保持 Web 更安全，不覆盖原始 EEG |

## 6. 对齐后的目标交互

### 6.1 普通浏览模式

默认进入浏览模式：

- 鼠标滚轮：水平浏览。
- Ctrl/Cmd + 滚轮：按鼠标位置缩放时间窗。
- PageUp/PageDown：上一页/下一页。
- Left/Right：当前窗口 1/10 小步移动。
- `+ / -`：调振幅。
- `Ctrl/Cmd + +/-`：调时间窗。
- 中键拖动：水平平移。
- 左键在浏览模式下不写入任何草稿。

### 6.2 Epoch 复核模式

进入“按 epoch 复核”后：

- 用户选择 epoch length。
- 用户选择 visible epochs。
- Canvas 背后显示淡网格，epoch 边界对齐时间轴。
- 单击选择一个 epoch。
- 拖拽选择连续 epoch。
- 选区在 EEG/ACC/EMG 分层上同步显示。
- 操作按钮变为：
  - 标为剔除 Reject
  - 标为保留 Remain
  - 撤销
  - 重做
  - 清空本轮草稿
  - 确认数据准备

### 6.3 坏段和坏道

坏段：

- 候选坏段只是待确认，不影响分析。
- Reject 后写入准备草稿。
- Remain 可覆盖 Reject。
- Restore 表示从已确认剔除中恢复。

坏道：

- 单击通道名或通道行标记坏道。
- 再次点击或恢复按钮取消坏道。
- 坏道操作必须进入 audit。

### 6.4 数据安全

所有操作必须遵循三层模型：

- L1 transient：鼠标 hover/拖拽中的临时态。
- L2 UI draft：释放鼠标后的本地草稿，可撤销/重做。
- L3 persisted preparation plan revision：点击确认后才保存到后端。

不得直接改写原始 EEG。

## 7. 建议开发优先级

### P0：直接影响“像 PC 端一样能用”的功能

1. Epoch mode：
   - epoch length。
   - visible epochs。
   - epoch grid。
   - click/drag snap to epoch。

2. Reject / Remain：
   - 两个主动作。
   - 写入草稿。
   - 可互相覆盖。

3. Undo / Redo / Cancel All：
   - 操作栈。
   - Redo 栈。
   - 清空当前草稿前确认。

4. 后端窗口合同：
   - 解决前端 300s 与后端 30s preview 上限不一致。
   - 短期至少在 UI/状态栏明确真实读取窗口。

5. 降采样改为 min-max bucket：
   - 避免漏掉尖峰。

### P1：提升专业阅片体验

1. EEG / ACC / EMG 分层。
2. Epoch strip 全局状态条。
3. 固定 uV/row 档位 + Auto。
4. 图例：选区、候选坏段、已剔除、已保留、已恢复。
5. 操作审计面板。

### P2：高级能力

1. 多窗口同步浏览。
2. 概览条 + 局部窗口联动。
3. 大文件 pyramid 缓存。
4. 准备后数据导出 EDF/FIF。

## 8. 验收标准

### 8.1 源码行为验收

- 选择数据后自动生成并显示真实波形，不需要用户点击内部 QC 预览。
- Canvas 不能只显示 skeleton 或静态图片。
- 浏览模式左键不写入草稿。
- 写入模式释放鼠标后才写入 UI draft。
- 快速切换窗口时旧响应不能覆盖新窗口。
- 滤波预览必须显示为 preview only。
- 原始 EEG 不被改写。

### 8.2 PC 对齐验收

- 支持 epoch length：`0.5 / 1 / 2 / 4 s`。
- 支持 visible epochs。
- 支持单击 epoch 和拖拽 epoch 范围。
- Reject / Remain 都可操作。
- Undo / Redo / Cancel All 可用。
- Reject 区域红色半透明覆盖。
- 当前选区粉色半透明覆盖。
- EEG 与 ACC/EMG 可分层显示。

### 8.3 端到端测试

必须用合成 EDF/FIF 数据跑：

- 教学模式自动加载并显示波形。
- 普通模式上传/选择数据后显示波形。
- 滚轮水平浏览后仍有波形。
- Ctrl/Cmd + 滚轮缩放后仍有波形。
- PageUp/PageDown 翻页后仍有波形。
- Left/Right 小步移动后仍有波形。
- Epoch 模式单击一个 epoch 后选区正确。
- Epoch 模式拖拽多个 epoch 后选区正确。
- Reject 后红色覆盖出现。
- Remain 后状态恢复为保留。
- Undo/Redo 后状态与图层同步。
- Confirm preparation 后分析 payload 包含：
  - `data_preparation_plan_id`
  - `data_preparation_revision`
  - `data_preparation_contract_version = qlanalyser-data-preparation-v0.2`

## 9. 结论

PC 端源码给 Web 版的最大启发不是具体绘图库，而是操作语义：

- 波形预览必须是可操作工作台。
- 预处理必须围绕波形完成，不能把控件放到页面深处。
- 坏段剔除应以 epoch 为主要对象。
- Reject 和 Remain 是两个明确的人工复核动作。
- Undo/Redo/Cancel All 是专业工具的基本安全感。
- EEG 与 ACC/EMG 应分层，帮助科研用户判断伪迹。
- Web 版必须保留更安全的数据准备方案模型，不能照搬 PC 端直接拼接删除原始 Raw 的方式。

下一步建议按本文件拆 `WaveformWorkbench Epoch Review Mode` 开发包，并补充对应 E2E。
