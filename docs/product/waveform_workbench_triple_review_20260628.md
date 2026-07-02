# WaveformWorkbench 三方评审报告（2026-06-28）

仓库：`D:\Quanlan\Codes\Python\quanlan-analyser-official`

目标：只读评审 WaveformWorkbench “数据看起来不连续”的根因、UI/交互、科研 EEG 阅片习惯、按钮分组和 E2E 补充项。

## 执行状态

- Claude：真实调用成功，采用有效输出 `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260628-waveform-workbench-triple-review\claude_review_oneline.utf8.md`。前两次 Claude 调用存在 stdin 卡住或 prompt/编码失效，已保留失败证据但不作为评审依据。
- DeepSeek：真实调用成功，路由 `DEEPSEEK_CLAUDECC`，模型 `deepseek-v4-flash`。DeepSeek 只基于 Codex 抽取的证据包评审，没有直接访问本地文件。
- Codex：已复核真实源码、截图、E2E JSON 和两方输出；本轮未修改业务代码。

## 最终口径

- `final_receipt`: `completed_review_packet`
- `release_verdict`: `blocked_until_P0_visual_continuity_and_interaction_fixes`

解释：三方评审已完成，但当前用户反馈对应 P0 体验风险，不能作为“用户体验已通过”交给发布。

## Claude says

data_continuity_root_cause_ranking

The discontinuity is **display/pipeline-induced, not real sampling discontinuity.** Ranked by likelihood with code evidence:

**R1 — Overlapping cache chunks with mismatched decimation grids (highest).**
`currentWindowData()` (`waveform-workbench.js:397-424`) merges points from *every* cached chunk overlapping the current window, then dedupes only when `Math.abs(point.time - last) < 1e-6` (line 412). Each backend chunk is decimated with `np.linspace(0, n_times-1, 1200)` over *that window's own* sample count (`qc_preview.py:382-385`), so each pan/zoom produces a **different absolute time grid**. After panning (8% steps, `wheelPanRatio:0.08`), chunk A `[0–24s]` and chunk B `[1.92–25.92s]` overlap on `[1.92–24s]` with non-coincident grids. The 1e-6 dedup never collapses them, so the polyline is drawn through **two interleaved sampling grids** of the same signal → vertical sawtooth that reads as "discontinuous / noisy". Up to 24 chunks accumulate (line 317), compounding the effect.

**R2 — Point-extraction decimation, not min-max (high).**
`_window_data()` reduces to `MAX_DISPLAY_POINTS=1200` by single-point `linspace` sampling. For a 24s/200Hz window (4800 samples) effective display rate ≈ 50 Hz; for 30s ≈ 40 Hz. EEG alpha (8–12 Hz) then renders with ~4 points/cycle → polygonal, choppy traces even with one clean chunk. This is exactly doc G6.

**R3 — Per-pan paged reload + 30s backend cap → boundary gaps during loading (medium).**
Every pan/zoom/slider move spawns a fresh `qc_waveform_preview` task (`reloadViewportPreview`, `scheduleViewportReload` 180ms debounce). `MAX_DURATION_SEC=30.0` caps each request. While the new task runs (MNE read→crop→resample→decimate, seconds), `currentWindowData` shows only whatever cached points fall in `[start,end]` → partial coverage / edge gaps until reload lands. `windowCoverage` returns `partial`/`missing` in this interval.

**R4 — Narrow peaks dropped by extraction (medium, subset of R2).** Spikes/transients between extracted indices vanish; doc G6 calls this out as scientifically worse than slow rendering.

**R5 — NOT a root cause: synthetic teaching data.** `buildLocalTeachin

final_verdict

**completed_review_packet.** Root cause is display-pipeline, not real sampling discontinuity: primary = front-end overlapping-chunk grid interleave (`currentWindowData`), secondary = backend `linspace` point-extraction at 1200 pts (no min-max), tertiary = per-pan paged reload boundary gaps. Highest-leverage, lowest-risk fix is the single-grid render selection in `currentWindowData`; pair with min-max bucket decimation and the listed E2E continuity assertions before release.

## DeepSeek says

用户为什么会觉得“不连续”：按可能性排序**

最核心原因是：**当前端向后端请求新时间窗数据时，现有界面处理方式造成了视觉上的“数据真空”，破坏了用户对数据连续性的感知。** E2E测试虽然通过，但不代表用户体验通过。

**可能性排序（从最高到最低）：**

1.  **“读取中”提示与旧波形同时存在，而非清晰覆盖（高概率）**:
    *   证据：`frontend/waveform-workbench.js` 第526-530行代码显示，当 `times` 数组为空时（即新数据尚未加载），代码会在画布上绘制文字“正在读取当前时间窗；不会把旧窗口波形映射到新时间轴。”。
    *   **问题**：这说明在数据切换的瞬间，旧波形被保留在画布上，但新的时间轴提示却叠加在旧波形之上。用户会看到旧波形和新提示并存，但旧波形的时间轴或数据点已与当前操作（如缩放、平移）失配。更优的做法是在数据请求发出后立即**清空画布**并显示一个**全幅的、半透明的加载遮罩**，明确告知用户“旧数据已失效，正在加载新视图”，而不是让旧波形“残影”和新提示混杂。

2.  **Epoch选区与加载状态重叠，造成视觉混乱（中高概率）**:
    *   证据：`04b_after_epoch_selection.png` 截图显示Epoch选择（粉色覆盖层）和加载状态可以共存。
    *   **问题**：点击一个Epoch后，界面立即进入加载状态，但Epoch的粉色选区依然保留。用户无法分辨这个选区是“已确认的当前操作”还是“正在试图操作的遗留物”。这种状态重叠加剧了“数据不连续”的感知，因为用户会认为操作对象（Epoch）在一个“不稳定的、正在过渡的”界面上。

3.  **“草稿”与“原始数据”的视觉层级未区分（中概率）**:
    *   证据：`05_after_scroll_persistence.png` 截图显示 `Remain`、`选中/剔除覆盖层`、`坏道标记` 共存；`frontend/waveform-workbench.js` 第506-510行中，`draft` 对象的 `remainSegments`, `candidateBadSegments`, `badSegments`, `selectedSegment` 都是直接在主画布上绘制。
    *   **问题**：科研用户在阅片时需要清晰区分“原始EEG波形”与“用户标记的草稿”。当前设计将两者绘制在同一个画布（Canvas）上，视觉上融为一体。当用户滚动或缩放时，草稿标记（如 `Remain`、`Reject`）应该保持其相对于时间轴的固定位置，而原始波形则平滑变化。如果刷新机制不当，草稿标记可能会随数据加载而闪烁或消失，导致用户感觉操作没有“粘性”，进而产生“数据不连续”的错觉。

4.  **后端预览时长限制（低概率，但需注意）**:
    *   证据：`eeg_core/preprocess/qc_preview.py` 第13行和19行显示 `DEFAULT_PREVIEW` 的 `duration_sec` 为12秒，`MAX_DURATION_SEC` 为30秒。同时，`frontend/waveform-workbench.js` 第27行显示初始 `durationSec` 为24秒。
    *   **问题**：前端请求24秒的波形，但后端默认或最大只提供12-30秒窗口。虽然代码 (`previewParameters` 函数) 使用了 `Math.min(30, ...)` 来限制，但这仍然意味着用户每次请求的时间窗都可能被后端截断或重新适配。如果频繁操作（如快速滚动），前端和后端之间关于“时间窗”长度的不一致可能导致数据加载失败或显示不完整，造成“卡顿”或“跳帧”的不连续体验。

**3. P0/P1/P2 问题清单**

*   **P0 (严重影响核心操作流程，必须修复)**
    1.  **数据加载期间的视觉断层**：在 `reloadViewportPreview` 执行时，画布应完全清空并显示明确加载状态，而非保留旧数据。这是“不连续”观感的直接根源。
    2.  **模式按钮文案不统一**：`frontend/waveform-workbench.html` 中模式按钮为“Epoch 复核”（第80行），而产品文档和代码注释中均使用“Epoch Review Mode”。应统一为中文“Epoch 复核”或“Epoch 模式”，避免中英混杂。
    3.  **核心操作“显而易见性”不足**：“标为剔除 / 标为保留”按钮 (`wwRejectBtn`, `wwRemainBtn`) 在整体页面中不够突出。科研用户的肌肉记忆是“看到问题 → 标记为坏/保留”。当前按钮样式 (`ww-danger`, `ww-keep`) 虽然正确，但缺乏在主操作区的突出地位。

*   **P1 (影响效率和舒适度，建议高优先级修复)**
    1.  **“Remain”和“Reject”的文案视觉语义混淆**：证据中 `Remain`（绿色）

final_verdict**

**blocked_review_packet**

**理由**：虽然现有功能点（如E2E测试）已通过，但核心用户体验问题——“数据看起来不连续”——被定义为P0级别。第2点和第3点中列出的“数据加载期间的视觉断层”和“模式按钮文案不统一”是直接影响用户对产品专业性和稳定性的根本问题。在未解决这些P0问题前，无法批准用户体验。建议优先解决数据加载时的视觉过渡问题和文案统一问题，并补充第6点中的E2E测试后，重新提交评审。

## Codex Acceptance

我接受 Claude 的技术根因排序，并把它提升为本轮最高优先级：`currentWindowData()` 会合并多个缓存 chunk，而后端每个窗口用自己的 `np.linspace` 抽点网格。重叠窗口的时间点不完全一致时，前端会把同一段信号的不同抽点网格交错连线，用户看到的就是锯齿、跳变或不连续感。

我也接受 DeepSeek 的体验判断：即使技术绘制修好，加载态、选区、事件 marker、草稿 overlay 仍会让科研用户误以为数据本身不稳定。因此 P0 修复必须同时覆盖“真实绘制连续性”和“用户感知连续性”。

## P0 问题

1. 缓存 chunk 叠加导致不同抽点网格交错连线。
   证据：`frontend/waveform-workbench.js:301-317` 缓存最多 24 个 chunk；`frontend/waveform-workbench.js:397-424` 合并所有 chunk 点；`eeg_core/preprocess/qc_preview.py:382-385` 用 `np.linspace` 抽点。

2. 长窗预览只做单点抽取，不保峰谷。
   影响：24/30s 窗口会显得折线化；后续 60/300s 概览更明显。

3. 加载、选区、草稿、事件层同屏时状态层级不清。
   影响：用户无法判断当前看到的是旧窗口、加载中窗口、已确认标记还是临时草稿。

## P1 问题

1. 事件 marker 在教学 oddball 数据里过密，视觉权重超过波形。
2. 工具栏按钮集中，浏览/显示/标注/Epoch复核/确认没有形成清晰操作区。
3. 独立 workbench 仍是 24s 默认、30s 上限，更像分页复核，不像连续 EEG 阅片。
4. 中英术语混用可保留必要科研词，但应弱化内部实现词，强化“当前选择、下一步、可恢复”。

## 给 07 的修复包建议

1. 先修绘制数据源：当前可视窗口只选择一个权威 chunk，或把多 chunk 重采样到统一 display grid；不要把 overlapping chunks 直接拼成一条 polyline。
2. 后端或前端补 envelope/min-max decimation，长窗保留峰谷。
3. 加载状态重构：旧视图要么隐藏，要么明确标记 stale；loading overlay 与 selection overlay 分层。
4. 事件层做 light/full/hidden/aggregate，默认降低密度与透明度。
5. 工具栏按“浏览、显示、标注、Epoch复核、确认提交”分组；写操作在无有效选区时禁用。
6. 增加 overview/epoch strip，显示全局时间、已加载范围、reject/remain/bad channel，并支持恢复。

## 必补 E2E

- Pixel/numeric continuity assertion: after pan/zoom, rendered polyline must not contain duplicate/interleaved time grids within the same visible interval.
- Cache chunk invariant: overlapping chunks must be selected/resampled deterministically; verify chunk count does not produce visual duplication.
- Min-max decimation visual test: synthetic sine/alpha + spike should preserve envelope and peaks at 24/30/60/300s.
- Loading-state test: old view is either explicitly stale or hidden; selection overlay and loading overlay must not imply confirmed data.
- Event-density test: light/full/hidden modes, dense oddball events, and overview ticks remain readable.
- Button-state test: browse mode write actions disabled; epoch selected enables reject/remain; undo/redo/cancel-all state and recovery are visible.
- Narrow/wide screenshot set: top/middle/bottom for 1440/1280/390 with no horizontal overflow and no overlay collisions.

## Evidence Paths

- 合并 JSON：`D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260628-waveform-workbench-triple-review\triple_review_result.json`
- Claude 有效评审：`D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260628-waveform-workbench-triple-review\claude_review_oneline.utf8.md`
- DeepSeek 评审：`D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260628-waveform-workbench-triple-review\deepseek_review.md`
- DeepSeek 路由证据：`D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260628-waveform-workbench-triple-review\deepseek_route_check.json`
- Codex 抽取证据包：`D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260628-waveform-workbench-triple-review\codex_extracted_evidence.md`
- 原 E2E 截图与 JSON：`D:\Quanlan\Codes\Python\quanlan-analyser-official\work\release_evidence\20260628-waveform-workbench-epoch-review`
