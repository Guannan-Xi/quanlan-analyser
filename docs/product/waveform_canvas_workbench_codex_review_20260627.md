# 07 Canvas 数据准备波形工作台 Codex 独立评审（2026-06-27）

## 结论

Codex note:

07 这轮 Canvas 数据准备波形工作台，作为“工程里程碑 / dev-ready”可以通过：真实波形能自动加载，Canvas 不再白屏，`times_sec` 坐标、坏段/选段/事件叠加、旧响应保护、数据准备门禁、教学数据保护锚点和静态契约验证都已补上。

但它还不应按“专业 EEG 波形工作台 / reviewer”进入最终验收。最大问题不在能不能画，而在 EEG 操作范式：视口不是一等公民，键盘导航缺失，灵敏度不是固定 uV/格，浏览/标注模式没有隔离，mini map、通道 gutter、montage 和事件导航也还没有形成专家工作流。

建议：先把 07 打回一个 1-2 小时的 P0 UX 包，重点关掉“每次视口动作都打后端任务”的手感问题，并把灵敏度改成 EEG 可读的 uV/格。

## 已核验证据

- 07 线程：`019efdfd-0e4a-7ef0-a77b-66bf524ac0f0`，最新状态为空闲，最近任务为 Canvas 工作台开发包。
- 验收包：`work/release_evidence/20260627-waveform-canvas-workbench-dev/acceptance_packet.json`，状态为 `completed_canvas_workbench_dev_ready_for_acceptance`。
- 浏览器 E2E：`waveform_canvas_workbench_browser_e2e.json`，状态 passed。
- 真实加载探针：`waveform_canvas_workbench_real_loaded_probe.json`，状态 passed，Canvas 有非白像素且 loading overlay 隐藏。
- 静态契约：`waveform_canvas_contract_static_validation.json`，状态 passed。
- 截图：`waveform_canvas_workbench_data_preparation.png`，页面能显示真实多通道波形。
- 本轮复跑：`node --check frontend/app.js`、两个 E2E 脚本语法检查、`scripts/validate_waveform_canvas_contract.mjs` 均通过。
- 编码检查：源码和 evidence JSON 以 UTF-8 读取无 replacement 字符和常见 mojibake 标记；终端乱码是 PowerShell 显示问题。

## 前端评审

做对的部分：

- `frontend/app.js:1510` 起的 `normalizeWaveformPreview` 统一了预览 payload，包含 `display_sample_rate_hz`、`downsampled`、`downsample_method`、`scale_uv`、`bad_segments`、`events` 等字段。
- `frontend/app.js:1618` 与 `frontend/app.js:1624` 的 `timeToCanvasX` / `canvasXToTime` 让 Canvas 时间映射统一，坏段、选段、事件 marker 和鼠标命中共用同一坐标系。
- `frontend/app.js:1780` 附近的视口按钮、`frontend/app.js:5503` 的 Ctrl/Cmd 滚轮缩放、`frontend/app.js:5848` 的 resize 重绘，让当前 Canvas 从静态预览变成可交互预览。
- `frontend/app.js:2104` 的 `runQcPreviewFromUi` 有 `previewRequestSeq` 保护，旧响应不应覆盖新请求。
- `frontend/app.js:2781` 附近给下游分析任务带上 `data_preparation_contract_version`，方向正确。

主要风险：

- `frontend/app.js:5523`、`frontend/app.js:5785`、`frontend/app.js:5805` 会在滚轮/输入/滤波变化后触发 `reloadWaveformPreview()`。这意味着用户做视口动作时仍走后端 QC preview 任务链，不像 EEG reviewer 的本地 viewport 浏览。
- `frontend/app.js:1871-1872` 使用每通道 `maxAbs` 做自适应缩放。画面好看，但不是固定 uV/格，无法让用户跨通道比较真实幅值。
- `frontend/app.js:5841` 的键盘处理只覆盖教学引导 Escape，没有 EEG 常用的左右翻页、PageUp/PageDown、Home、增益和时间窗快捷键。
- Canvas 拖拽默认就是选段，缺少“浏览模式拖拽平移 / 标注模式拖拽选段”的模式隔离。

## 后端/API 契约评审

当前复用 `POST /api/tasks` + `module_name=qc` + `workflow_id=qc_waveform_preview` 是这个里程碑可以接受的工程折中，因为文档也允许先从任务产物读取 `waveform_preview.json`。数据准备 plan 的 `qlanalyser-data-preparation-v0.2`、revision 和下游分析门禁也已经被前端接入。

但这不是长期架构。专业波形浏览需要真正的 windowed waveform API、缓存和多分辨率预览层。否则每次平移、缩放、切滤波都像“重新跑任务”，用户会觉得慢，E2E 也很难覆盖快速切换和旧响应抢占。

## 用户逻辑与工作流

一致的地方：

- 教学模式和普通模式的边界更清楚，内置教学数据有保护提示。
- 数据准备确认后，下游分析必须带准备方案 id、revision、contract version 的方向正确。
- QC、坏道、坏段、滤波预览、重参考被放在数据准备语义下，没有继续伪装成分析方法。

仍未充分证明的地方：

- E2E 主要证明了“已确认后可继续”，还没有完整证明“未确认时拦截 PSD/ERP 提交”。
- 教学数据不可删除/不可覆盖，目前前端保护可见，但后端拒绝路径没有在本轮 evidence 中看到端到端证明。
- 快速切换文件时旧预览不覆盖新画布，代码上有 requestSeq，但缺真实慢响应抢占 E2E。

## UI/视觉评审

基于截图，当前成熟度是 `usable`，还没到 `good usability`，更没到 `polished professional`。

原因：

- 波形已经是真实主内容，但页面仍像“Web 表单包着一张波形预览”。顶部步骤卡、显示控制、右侧预处理面板、下方片段表单、事件保存与最终确认都同时占视觉权重。
- 波形区周围有太多重复控制，用户会在“看波形”和“填表单”之间来回跳。
- 右侧预处理设置有价值，但它现在像浮动表单，和 Canvas 内的状态条/灵敏度/时间窗没有形成统一操作面。
- 状态可见性不足：缺常驻状态条展示当前时间、页长、uV/格、显示采样率、滤波、参考、是否降采样、当前 cursor 读数。

设计基准来自本轮读取的本地知识库：B2B 科研工作台需要任务定位、信息层级、密度扫描、图表/波形可读性、状态覆盖和科学边界一起成立；不能因为 E2E 通过就称为专业。

## EEG 操作范式评审

与 02 线程规范对照：

- viewport：部分具备，但仍被后端任务驱动，未达到一等公民。
- wheel zoom：已有 Ctrl/Cmd 滚轮锚点缩放，但普通拖拽平移缺失。
- keyboard：缺失。
- mini map：缺失。
- channel gutter：只有左侧通道名，没有可交互 gutter、坏道切换、分组和固定列。
- montage：缺失，重参考仍是表单设置，不是 viewer 级切换。
- events：已有竖线绘制能力，但缺上/下一个事件导航和事件列表联动。
- sensitivity/timebase：时间窗有，但灵敏度不是 uV/格；`2x` 不是 EEG 语言。
- browse/correction mode：缺失，浏览状态也会拖出选段。

## P0 / P1 / P2

P0：

1. 视口本地化：在已加载 buffer 内平移/缩放/键盘翻页只重绘，不重新 `POST /api/tasks`；越界再预取。
2. 固定灵敏度：用 `scale_uv` / uV/格绘制，替换 `2x` 相对增益，并画校准条。
3. 键盘导航：左右键、PageUp/PageDown、Home、`+/-`、`[`/`]`，仅在波形区聚焦时生效。

P1：

1. 浏览/标注/确认三模式隔离，浏览模式拖拽平移，标注模式拖拽选段。
2. 常驻状态条：时间位置、页长、uV/格、采样率、降采样、滤波/参考、cursor 读数。
3. 事件导航：上/下一个事件、事件列表与 Canvas 竖线联动。
4. mini map：显示全时长、当前窗口、坏段/事件概览，支持点击/拖动 seek。

P2：

1. montage 与通道 gutter。
2. 标准页长和灵敏度档位。
3. 降采样大窗口 E2E，证明尖峰保留。

## 建议给 07 的下一包

包名：`waveform-viewport-p0`

目标文件：

- `frontend/app.js`
- `frontend/index.html`
- `frontend/styles.css`
- `scripts/e2e_waveform_interaction.mjs`
- `scripts/validate_waveform_canvas_contract.mjs`

验收证据：

- 连续本地平移/缩放不新增 task POST 的 E2E JSON。
- 键盘导航 E2E JSON。
- 固定 uV/格和校准条静态验证 JSON。
- `downsampled=true` 大窗口保峰值 E2E。
- 新截图：波形区作为主工作面，状态条可见。

final_receipt: completed_codex_full_local_review_ready
