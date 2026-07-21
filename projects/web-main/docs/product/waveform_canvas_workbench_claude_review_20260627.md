我已实地核对全部硬目标文件、契约、三份证据 JSON、两份 E2E 脚本、静态校验器、`frontend/app.js` 的 Canvas 绘制与交互代码路径、`backend/api/data_preparation.py` 路由，以及实际渲染截图。下面是独立复审。

---

Claude says：

复审目标确认无误：QLanalyser 07 最新本地工作 = 数据准备 Canvas 波形工作台（`20260627-waveform-canvas-workbench-dev`）。非 PSD、非 billing、非暂存区、非 TimeChart。继续。

## 1. 总体结论

**工程 Canvas 里程碑判定：基本达成（dev 级）。** 统一时间映射、`times_sec` 绘制、DPR 分离、min/max 兜底、stale guard、Ctrl 滚轮锚点缩放、resize 重绘、契约字段归一化、教学/门禁选择器——这些 P0 缺口（我上一轮 Canvas 契约复审提出的）在代码层确实补上了，静态校验 14/14、浏览器 E2E、real-loaded probe 三绿。作为"Canvas 能画、能交互、有契约"的开发里程碑，成立。

**专业 EEG 阅图者 UX 判定：未达标。** 三个结构性问题（详见 §7）：
- 视口**不是一等公民**——每一次平移/缩放/翻页/改通道都重新 `POST /api/tasks` 走 QC 任务流水线（`runQcPreviewFromUi`），8s 软 / 20s 硬超时挂在交互路径上。滚轮滑一下 = 打一次后端。这与"viewport is first-class"直接冲突。
- **零键盘导航**——全局 `keydown` 只处理教学引导的 Escape，没有任何 ←/→/PageUp/Down 翻页。
- **无固定 uV/格灵敏度**——绘制用每通道 `maxAbs` 自动归一化（`scale = rowHeight*0.34*gain/maxAbs`），契约 §2.4 规定的 `scale_uv` 字段被解析却从未用于绘制。增益是相对倍数，不是校准电压。EEG 阅图者据此无法跨通道比较振幅。

**进入终审 or 回炉 07：建议回炉 07 做一个 P0 UX 包，不要现在进终审。** 理由：当前可作为"数据准备草稿编辑器"验收，但若以"专业 EEG 波形工作台"对外，上述三点是会被第一线用户立刻发现的硬伤。验收范围必须明确降级措辞，否则名实不符。

## 2. 已核查证据

已实地读取并核对：
- `acceptance_packet.json`、`waveform_canvas_contract_static_validation.json`（14 检查全 pass）、`waveform_canvas_workbench_browser_e2e.json`（10 检查全 pass，4 次 task POST）、`waveform_canvas_workbench_real_loaded_probe.json`
- `waveform_canvas_workbench_data_preparation.png`（已视觉打开，见 §6）
- `docs/product/...canvas_contract_20260627.md`（全文）
- `frontend/app.js`：`minMaxBucketWaveform`(1473)、`normalizeWaveformPreview`(1510)、`timeToCanvasX/canvasXToTime`(1618/1624)、`drawEegWaveformPreview`(1794)、骨架(1936)、指针/滚轮交互(5461-5524)、`runQcPreviewFromUi`(2104)、`keydown`(5841)、resize/ResizeObserver(5848)
- `scripts/validate_waveform_canvas_contract.mjs`、`e2e_waveform_interaction.mjs`、`e2e_teaching_waveform_preview.mjs`
- `backend/api/data_preparation.py` 路由清单

**未核查（标记 unverified）：**
- 未亲自重跑任何 E2E / 静态校验器（read-only 复审，仅核对脚本与产物一致性）。
- 未视觉打开 `waveform_canvas_workbench_browser_e2e.png` 与 `..._real_loaded.png`（仅读其 JSON probe）。
- 未核查 `frontend/index.html` / `frontend/styles.css` 全文（仅依据静态校验器断言与截图）。
- 未核查后端 `qc_waveform_preview` 服务实现是否真返回 `events` / `scale_uv`（仅从契约与前端归一化推断）。

## 3. 前端复审

- **坐标映射**：`timeToCanvasX/canvasXToTime` 共用 `canvasPlotWindow`，互为逆函数，clamp 到 `[start,end]`，拖拽/坏段/选段/刻度共用 `eegState.lastPlot`——契约 §2.2 满足。✅
- **times_sec 绘制**：`drawEegWaveformPreview` 用 `Number(times[index] ?? 线性兜底)` + `timeToCanvasX`，不再用样本索引。✅ 兜底分支在 `times` 短于样本时退化为均匀间隔，可接受。
- **stale guard**：`previewRequestSeq` 自增 + `loadWaveformPreviewFromTask` 内 `requestSeq !== eegState.previewRequestSeq` 双卡点（2128/2131）。逻辑正确。⚠️ 但仅静态/单步验证，**未做真实慢响应抢占**（acceptance 自认）。
- **降采样**：`minMaxBucketWaveform` 保留首尾 + 每桶 min/max 索引，按原序输出，`downsampled/downsample_method` 如实回填。✅ 但 `targetBuckets = floor(maxPoints/2)`，每桶产 2 点，实际输出可达 `maxPoints` 量级——边界正确。性能隐患：内层 `matrix.map(row=>row[index])` 对每个 index 重算，O(samples×channels)，大窗口下偏重，但当前 8 通道无碍。
- **叠加层**：坏段(红)→选段(粉)→波形→事件(青竖线)顺序与契约 §2.5 一致，标签"坏段/选段"可读，透明度在建议区间。✅
- **选区**：`pointerDown/Move/Up` 经 `canvasXToTime` 反算 + `normalizeSegmentRange`（最小段 `max(0.05, 2/sfreq)`）。✅
- **事件**：仅当 payload 含 `events/annotations` 才画；连续数据 QC 预览大概率无事件 → 事件标记实战中多半不出现，且**无事件跳转控件**。⚠️
- **响应式**：1100px 折叠（静态校验确认 CSS 命中）。✅
- **选择器**：契约 §7 登记表选择器静态校验存在。✅
- **致命点**：**振幅未用 `scale_uv`**，每通道独立自适应。这是前端最大偏差，详见 §1/§7。❌

## 4. 后端 / API 契约复审

- **当前复用**：波形窗口**唯一**来源是 `POST /api/tasks` + `module_name=qc` + `workflow_id=qc_waveform_preview`，前端从任务产物读 `waveform_preview.json` 再 `normalizeWaveformPreview` 归一化。契约 §3.1 允许此复用，前端归一化层到位。✅
- **data_preparation 契约**：`backend/api/data_preparation.py` 提供 plans / `eeg/files/{id}/data-preparation-plan` GET·POST / `bad-channel-audit` / epoch-sets，schema `qlanalyser-data-preparation-v0.2` + `base_revision` 冲突检测，前端分析任务携带 `data_preparation_contract_version`。契约 §5 锚点齐全。✅
- **缺口（P0 架构风险）**：**没有真正的窗口化波形 API，没有缓存，没有金字塔/多分辨率。** `data_preparation.py` 全是 plan/epoch/audit，无任何 `waveform`/`window` 端点。后果直接落到 §3 的交互：每次 `shiftEegWindow`/`zoomEegWindow`/`handleEegCanvasWheel` 都 `reloadWaveformPreview()→runQcPreviewFromUi()→建任务→跑 worker→读产物`。证据自证：browser_e2e 一次会话产生 **4 次 task POST**。这就是"missing true windowed waveform API/cache/pyramid risk"的实锤——平移/缩放体验受后端任务延迟与 8/20s 超时支配，不是本地视口操作。

## 5. 用户逻辑 / 工作流复审

- **教学模式**：进入自动选教学文件、自动预览（fast_ui_preview=true），`teaching-data-protected` 选择器可见。✅ 但后端拒删/拒覆盖**未在本证据集验证**（契约 §8 后端要求）。⚠️
- **普通模式**：选数据自动进入预览、骨架不白屏、`#loadEegBtn` 作"重新加载"语义。✅
- **分析门禁**：`analysis-preparation-gate` 选择器存在，E2E 显示 gateText="数据准备已确认，可以开始分析"。✅ **但**：这是**已确认**态，E2E **没有走未确认→拦截→提示→跳转**的失败路径，也没有真正提交 PSD/ERP 并断言 payload 带 `plan_id/revision`（仅静态校验代码含该字段）。门禁的"拦截"侧 unverified。⚠️
- **QC 不作为分析方法**：契约 §1.4 定位正确，QC=数据准备而非分析方法，前端走 qc preview 而非分析列表。✅
- **数据准备确认**：草稿/确认/逐项恢复语义在 E2E 可见（剔除/恢复/坏道/恢复坏道写草稿态）。✅
- **教学数据保护**：选择器可见、沙盒分析可用方向正确。✅（后端强制 unverified）

## 6. UI / 视觉复审

依据 `..._data_preparation.png`：8 通道彩色堆叠波形、顶部时间轴、左侧步骤指引 + 教学保护卡、右侧预处理参数、画布下方"起点/时间窗/增益/通道"控件、再下方剔除/标签/坏道四格、底部数据准备说明与确认条。

- **层级/视觉权重**：合格。主区波形够大，预处理在右栏，确认在底。
- **可扫读性 / 控件密度**：偏高。单列长滚动，波形下方堆叠了 6+ 组控件块，阅图与编辑在视觉上未分区。
- **可读性 / 可达性**：通道名、刻度、状态文案清晰；自动归一化使每行波形等高填满，**好看但误导**——丢了真实振幅对比。
- **状态可见性**：有顶部 meta 行与 `segmentSummary` 文本摘要，但**画布内无常驻状态栏**（无 uV/格、无当前时间游标读数、无页码/总时长）。

**分级：usable（可用）。** 未到 good usability（缺视口状态栏、缩略导航、灵敏度刻度），更未到 polished professional。

## 7. EEG 操作习惯复审（以 02 线规范为准绳）

| 习惯（P0/P1） | 状态 | 证据 |
|---|---|---|
| 视口一等公民 | ❌ P0 | 每次平移/缩放/翻页都 `POST /api/tasks` 重渲染（§4）|
| 滚轮缩放 / 拖拽平移 | ⚠️ | Ctrl 滚轮缩放✅；普通滚轮是"平移窗口起点"但走后端重载，非本地拖拽 pan |
| 键盘翻页 / 导航 | ❌ P0 | `keydown` 仅 Escape（5841），无 ←/→/PageUp/Down |
| 状态栏 | ⚠️ P1 | 仅文本 meta，无画布内常驻 uV·时间·页码状态栏 |
| 缩略图 / mini-map | ❌ P1 | 代码与截图均无 minimap/概览条 |
| 通道槽 gutter | ⚠️ | 有通道名列(x=18)，但无独立 gutter（坏道勾选、拖动排序、折叠）|
| 蒙太奇 montage | ❌ P1 | 无 montage 选择器；重参考仅在预处理面板，非画布级双极/参考切换 |
| 事件竖标 / 事件跳转 | ⚠️ | 画事件竖线✅，但**无上/下一个事件跳转**；连续 QC 数据通常无事件 |
| uV/格 灵敏度 | ❌ P0 | 每通道 `maxAbs` 自归一化，`scale_uv` 未用于绘制；增益是相对倍数，无校准条 |
| 时基 / 页长 | ✅/⚠️ | 有时间窗输入与缩放，但页长档位非标准（2–30s 任意），无 10/15/30s 习惯档 |
| 浏览 / 标注模式隔离 | ❌ P1 | 无 browse vs correction 模式切换；拖拽永远=选段，浏览态也会误触发选区 |
| 撤销栈 | N/A | 契约 §5.4 本期只要求逐项恢复，符合范围 |
| 可发现快捷键 | ❌ | 提示文案"滚轮平移，Ctrl+滚轮缩放"，但无快捷键面板，且键盘根本未绑定 |

## 8. 测试 / 证据缺口

**E2E 证明了：** 客户外壳加载、Canvas 自动加载真实波形且骨架隐藏（nonWhite 8617 / colored 6816）、教学保护选择器可见、拖拽更新 `segmentStart/End`、剔除/恢复段写草稿态、标记/恢复坏道写草稿态、导航控件改视口输入、门禁选择器存在且为确认态。

**E2E 没证明（unverified）：**
1. **stale 抢占**：真实慢响应覆盖未测（acceptance 自认）。
2. **拖拽像素-时间精度**：仅断言 end>start，未对齐 `max(0.05, 2/sfreq)` 容差（契约 §10.3）。
3. **叠加层在缩放/平移/resize 后对齐**（§10.4）：无对齐断言。
4. **downsampled=true 仍显尖峰**（§10.5）：E2E 窗口 10s×200Hz≈2000 点 < 2500 阈值，**根本未触发降采样**，该断言空缺。
5. **确认→PSD/ERP payload 带 plan_id/revision**（§10.7）：仅静态含字段，未端到端提交校验。
6. **门禁拦截侧**（§10.8）：只验证"已确认"放行，未验证"未确认"拦截。
7. **教学删除/覆盖后端拒绝**（§10.9）：未测。
8. **无医疗承诺文案**（§10.10）：本证据集未含该扫描（仅 mojibake）。
9. **快速切两个文件不串画布**：浏览器层未测。

外加：CLI Playwright 仍需 NODE_PATH/内置运行时；全量发布套件未重跑（acceptance 自认）。

## 9. P0 / P1 / P2 发现（可执行）

**P0（回炉 07 必修）**
- **P0-1 视口本地化**：拖拽 pan、滚轮 pan、缩放、翻页必须在已加载缓冲上本地重绘，不得每次 `POST /api/tasks`。最小方案：一次拉取比可视窗大的缓冲（如 60s），视口内移动只重绘不打后端；越界才预取。`frontend/app.js` `shiftEegWindow/zoomEegWindow/handleEegCanvasWheel`。
- **P0-2 键盘导航**：绑定 ←/→ 翻半屏、PageUp/Down 翻整屏、Home 复位、+/- 增益、[ / ] 时基，且仅在画布聚焦/可见时生效。`app.js` `keydown`(5841)。
- **P0-3 固定 uV/格灵敏度**：绘制改用 `gainPxPerUv = rowHeight*0.32/max(scale_uv,1)`（契约 §2.4），增益输入改为档位 uV/格（如 50/100/150 µV），画布左下角画校准条。`drawEegWaveformPreview`(1872)。

**P1**
- **P1-1 画布常驻状态栏**：当前页 start–end、总时长/页码、µV/格、显示采样率、降采样标记、游标处时间。
- **P1-2 浏览/标注模式隔离**：默认浏览态（拖拽=pan），切到标注态才允许拖拽选段；契约 §1 应补该状态。
- **P1-3 事件导航**：上/下一个事件按钮 + 快捷键（ERP 门禁依赖事件，必须能找到事件）。
- **P1-4 缩略 mini-map**：全长概览条 + 视口框，点击/拖动定位。

**P2**
- **P2-1 montage/重参考画布级切换**（双极/平均参考）。
- **P2-2 标准页长档位**（10/15/30s）与标准灵敏度档。
- **P2-3 通道 gutter**：坏道勾选、折叠、排序。
- **P2-4 降采样 E2E**：构造 >2500 点窗口，断言尖峰极值保留。

## 10. 下一个 07 开发包（1–2 小时，实操）

**包名：waveform-viewport-p0（视口一等公民最小包）**

聚焦 P0-1/P0-2/P0-3 中投入产出最高、且不触碰 router/Headroom/IPC/model route、不引入 TimeChart、不碰癫痫源工作台的三项：

1. **本地视口重绘**（`frontend/app.js`）：新增 `eegState.buffer`（最近一次拉取的较大窗口 + 其 start/end）；`shiftEegWindow/zoomEegWindow/handleEegCanvasWheel` 改为：若目标窗口落在 buffer 内 → 仅 `redrawCurrentWaveform()` 用 buffer 切片，不 `POST`；越界才走现有 `reloadWaveformPreview()` 预取。`normalizeWaveformPreview` 增加按 `[start,end]` 切片的纯函数。
2. **键盘导航**（`app.js` keydown）：←/→/PageUp/Down/Home/+/-/[/]，复用上面的本地重绘路径；画布加 `tabindex=0` 与聚焦判定。
3. **固定 µV/格 + 校准条**（`drawEegWaveformPreview`）：用 `scale_uv` 计算 `gainPxPerUv`，增益输入语义改 µV/格，左下角画校准条与"µV/格"读数。

**验收证据（写入 `work/release_evidence/<date>-waveform-viewport-p0/`）：**
- `viewport_local_redraw_e2e.json`：连续 5 次 ←/→ + 3 次滚轮 pan + 2 次缩放，断言 **task POST 次数 = 0**（越界除外单独计数），画布像素变化但无网络任务。
- `keyboard_navigation_e2e.json`：键盘各键改 `#eegStartInput/#eegWindowInput/#eegGainInput` 且画布重绘。
- `fixed_sensitivity_static_validation.json`：静态断言绘制使用 `scale_uv` 与 `gainPxPerUv`，校准条文本存在。
- `downsampled_peak_e2e.json`：≥2500 点窗口，`downsampled=true` 且尖峰极值可见（补 §10.5 缺口）。
- 截图 `viewport_p0.png` + 更新 `acceptance_packet.json`（route 标注无 router/headroom/timechart 改动）。

此包 1–2 小时可落，直接把"viewport is first-class"从 ❌ 拉到 ✅，是进入终审前性价比最高的一步。

## 11. 最终回执

**completed_claude_full_local_review_ready**

补充结论：复审本身完成且证据自洽；但**不建议现在进入终审**——建议先回炉 07 执行 §10 的 `waveform-viewport-p0` 包。当前里程碑可按"数据准备 Canvas 草稿编辑器（dev-ready）"验收，但不可按"专业 EEG 波形工作台"对外定性，直到 P0-1/2/3 闭合。产品仍保持非医疗 / 科研数据准备定位，未触碰 router/Headroom/IPC/model route、未引入 TimeChart、未触碰癫痫源工作台。
