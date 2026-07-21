# WaveformWorkbench 全功能点评审与连续读片优化方案

日期：2026-06-28  
目标页面：`http://127.0.0.1:4174/waveform-workbench.html?teaching_demo=auto&api=http://127.0.0.1:8001/api&v=e2e`  
适用范围：独立 `WaveformWorkbench` 页面，不扩大到主工作台、不处理癫痫源码工作台、不触碰 router / Headroom / gateway / IPC / model route。

## 1. 本轮结论

用户反馈“数据怎么不连续”，判断成立：当前页面已经能显示波形，也已合并基础浏览和 epoch 复核动作，但它仍是“按窗口预览”的实现，不是科研人员预期的“连续阅片工作台”。

根因不是 EEG 文件本身断裂，而是当前交互和数据加载策略造成了连续性错觉：

1. 后端 QC preview 当前上限是 30 秒，页面默认按 24 秒窗口读取。
2. 每次滚轮、翻页或缩放后，前端会重新请求一个窗口级 preview task。
3. 为避免重新请求期间画布空白，前端保留旧窗口并 fallback 显示；这会让用户感觉波形被“拼贴”或“跳段”。
4. 教学 oddball 数据事件 marker 很密，竖线比波形更抢眼，视觉上像很多分段切口。
5. 当前没有全局时间轴 / mini-map / 连续缓存带，用户无法确认自己在整段 60 秒记录中的连续位置。

因此下一轮优化目标不是继续堆按钮，而是把工作台从“预览卡片”升级为“连续 EEG 阅片 + epoch 复核工作台”。

## 2. 三方评审状态

| 评审方 | 状态 | 证据 | 结论 |
|---|---:|---|---|
| Codex / GPT-5.5 主审 | 已完成本轮主审 | 本地源码、API、截图、E2E JSON、用户反馈 | 功能通过，但连续读片体验不通过，需要优化 |
| 双评审线程 `019f04c3-c297-7883-87d9-a23cf6729be6` | 已发送，只读评审进行中 | `codex_app.send_message_to_thread` 已投递评审包 | 当前已回传初步一致意见：E2E 通过不等于连续体验通过 |
| DeepSeek 语言/逻辑评审 | 当前不可证明已调用 | 本会话无直接 DeepSeek 工具/API 回执 | 暂不伪造；优化后可把中文文案和科研操作逻辑交给 DeepSeek 或人工语言层复核 |
| Open Design | 当前本地 daemon 健康检查超时 | `http://127.0.0.1:7456/api/health` timeout | 不声称已完成 Open Design；本轮使用本地截图 + Google Labs design.md 合同进行替代评审 |

## 3. 现有功能点盘点

### 3.1 已实现且可保留

- 教学数据自动加载。
- 基础浏览：
  - 第一页、上一页、下一页、最后一页。
  - 滚轮水平浏览。
  - Ctrl/Cmd + 滚轮缩放。
  - PageUp/PageDown 翻页。
  - Left/Right 小步移动。
  - `+/-` 调节振幅灵敏度。
- 预处理复核：
  - 浏览模式不写入。
  - 选段模式写入草稿。
  - Epoch 复核模式按 epoch snap 选择。
  - Reject / Remain。
  - Undo / Redo。
  - Cancel All / 清空草稿。
  - 候选坏段、确认候选、取消候选、恢复最近剔除。
  - 坏道点击写入草稿。
- 状态栏：
  - 模式、时间窗、窗口长度、通道数、灵敏度、Raw/Filter、Epoch、Reject、Remain 等。
- 证据：
  - `work/release_evidence/20260628-waveform-workbench-epoch-review/waveform_workbench_e2e_result.json`
  - 20 项 E2E 检查通过。

### 3.2 当前不符合专业 EEG 阅片习惯的点

#### P0：连续性与信任问题

1. 页面显示的是窗口级 preview，不是真正连续数据流。
2. 切换窗口期间 fallback 旧窗口，可能把旧数据视觉映射到新时间窗，造成“假连续 / 假不连续”。
3. 缺少全局 timeline / overview，用户不知道当前窗口与全记录关系。
4. 事件 marker 过密，且强视觉权重高于波形，导致用户看起来像数据被切断。
5. 没有明确显示“当前窗口来自缓存 / 正在读取 / 已同步到真实数据”。

#### P1：操作模型仍偏网页工具，不够像 EEG 工作站

1. Reject / Remain / 候选坏段 / 坏道按钮都在同一个侧栏，信息层级偏平。
2. “选段”和“Epoch 复核”都能产生选择，用户容易混淆。
3. Cancel All 与“清空全部草稿”语义接近，按钮重复。
4. 候选坏段与 Reject 的关系不够清楚：候选是待确认，Reject 是草稿剔除。
5. 通道定位、当前鼠标时间、当前 epoch 编号没有形成稳定读片状态栏。

#### P1：视觉和文案问题

1. 页面标题 `WaveformWorkbench` 偏开发命名，应提供中文主标题，例如“脑电波形与数据准备工作台”。
2. 右侧草稿区域说明较长，核心动作不够突出。
3. 事件线、epoch 网格、Reject/Remain 区域的视觉优先级需要重新排序。
4. 当前教学数据说明没有告诉用户“这是合成 oddball 事件数据，事件线较密，波形本身是连续的”。

#### P2：后续可增强

1. 通道选择器、通道搜索、通道分组。
2. 垂直滚动通道列表。
3. Raw / Filter 双层切换或叠加。
4. 显示比例尺：时间标尺、振幅标尺、uV/row。
5. 导出当前复核草稿为准备方案。

## 4. 数据不连续的根因排序

### 第一优先级：窗口级 preview 与连续阅片需求不匹配

当前后端 `eeg_core/preprocess/qc_preview.py` 中有：

- `MAX_DURATION_SEC = 30.0`
- `MAX_DISPLAY_POINTS = 1200`

前端 `frontend/waveform-workbench.js` 中有：

- `constants.maxDurationSec = 30`
- 默认 `durationSec = 24`
- `reloadViewportPreview()` 每次重新创建 QC preview task。

这说明当前设计是“短窗口预览”，不是“完整连续浏览”。

### 第二优先级：fallback 旧数据保画布不空，但会制造错觉

当前绘制逻辑：

- `currentWindowData()` 按全局 start/end 过滤 payload times。
- 如果没有 indices，会调用 `fallbackWindowData()`。
- `fallbackWindowData()` 使用当前 start/duration 重新生成 times，但 matrix 仍来自当前 payload。

这个设计解决了“滚动就没了”，但在真实用户眼里可能变成“数据跳了 / 不连续 / 被拉伸”。

### 第三优先级：事件 marker 密度和视觉权重过高

教学数据是 60 秒 oddball，包含 24 个 standard 和 12 个 target。24 秒窗口内事件线较多，且 marker 颜色鲜明，视觉上比小振幅 EEG 曲线更强，容易被误认为切割线。

### 第四优先级：缺少全局位置反馈

没有 mini-map、滚动条、页码、当前位置百分比、缓存窗口边界、已加载窗口范围。用户无法建立“我在连续记录中的哪里”的心理模型。

## 5. 优化设计目标

### 5.1 产品目标

把当前页面升级为：

> 一个科研 EEG 数据准备工作台：默认给用户连续读片感；所有剔除、保留、坏道操作都清楚写入草稿；原始 EEG 永不被修改。

### 5.2 交互原则

1. 浏览优先：打开页面先看到连续波形，不先看到一堆按钮。
2. 连续感优先：任何滚轮/翻页/缩放都不能让用户感觉数据断裂。
3. 写入模式隔离：浏览模式绝不写草稿；写入模式有明确颜色和提示。
4. 按 epoch 复核：Reject / Remain 以 epoch 为核心对象。
5. 可恢复：剔除、坏道、坏段都必须可撤销、可重做、可恢复。
6. 解释少而准：按钮和说明必须面向科研用户，而不是开发者。

## 6. 下一轮实现方案

### 6.1 P0：连续数据缓存层

新增前端缓存模型：

```text
windowCache = {
  key: file_id + channel_set + display_sfreq + raw_filter,
  chunks: [
    { start_sec, end_sec, times_sec, data_uv, events }
  ],
  pendingRanges: [],
  loadedRanges: []
}
```

行为：

1. 当前窗口移动时，先从缓存拼接当前可见范围。
2. 如果缺少部分范围，只在缺口处显示轻微 loading overlay，不把旧数据拉伸到新时间窗。
3. 请求完成后按真实 `start_sec/end_sec` 合并 chunk。
4. 旧响应不得覆盖新视图，只能进入缓存。
5. 画布状态显示：
   - “已同步”
   - “正在读取 00:00:24-00:00:48”
   - “部分窗口待加载”

### 6.2 P0：全局时间轴 / overview bar

在 Canvas 下方增加一条 overview：

```text
|-------------------- 60s recording --------------------|
      [ current 24s window ]
    loaded chunks: 0-24, 24-48
    reject/red/remain/green overlays
```

功能：

- 显示全记录长度。
- 显示当前窗口位置。
- 显示已加载缓存范围。
- 显示 Reject / Remain / Candidate bad segment 覆盖。
- 支持点击跳转、拖动窗口。

### 6.3 P0：事件 marker 降噪

默认改为：

- 事件线降低透明度。
- 同类型密集事件聚合为顶部 tick / rug。
- 鼠标 hover 时显示事件名称。
- 提供“事件显示：隐藏 / 简洁 / 详细”切换。

### 6.4 P1：按钮重组

推荐结构：

```text
左上：浏览控制
  页首 / 上一页 / 下一页 / 页尾 / 时间窗 / 灵敏度 / 通道数

画布上方：模式
  浏览 / 选段 / Epoch 复核 / 标坏道

右侧：当前选择
  当前时间段
  当前 epoch
  操作：剔除 / 保留
  历史：撤销 / 重做

底部：草稿清单
  候选坏段
  已剔除
  已保留
  坏道
  清空本轮草稿
```

需要合并/弱化：

- “清空本轮草稿”和“清空全部草稿”保留一个主入口，另一个放二级确认。
- “候选坏段”不要和 Reject 同层；候选应是“待确认清单”。
- 快捷键帮助折叠到帮助按钮，不抢主工作区。

### 6.5 P1：状态栏升级

状态栏固定显示：

- 当前时间：`00:00:24.000 - 00:00:48.000`
- 当前页：`第 2 / 3 页`
- 当前鼠标：`t=31.240s, ch=Cz, epoch=7`
- 显示：`Raw, 200 Hz display, 200 uV/row`
- 缓存：`已加载 0-48s / 共 60s`
- 草稿：`Reject 1, Remain 1, bad channel 1`

### 6.6 P1：科研文案优化

建议文案：

- 页面主标题：`脑电波形与数据准备工作台`
- 副标题：`连续浏览 EEG，按 epoch 标记剔除/保留，所有操作先进入准备草稿。`
- 教学数据说明：`当前为内置合成 oddball 教学数据，事件标记较密；波形本身连续，用于学习浏览、坏段和坏道复核。`
- Reject：`剔除此 epoch`
- Remain：`保留此 epoch`
- Candidate bad segment：`加入待确认坏段`
- Cancel All：`清空本轮复核草稿`

## 7. E2E 验收补充项

下一轮必须新增：

1. `T-CONT-01` 初始加载后，当前窗口真实 times 覆盖 `start_sec` 到 `start_sec + duration_sec`，不使用 fallback。
2. `T-CONT-02` 滚轮平移后，如果新窗口缺缓存，只显示加载状态，不把旧波形拉伸到新时间窗。
3. `T-CONT-03` 请求完成后，chunk 按真实 start/end 写入 cache，画布显示真实数据。
4. `T-CONT-04` 快速连续滚动，旧响应不得覆盖当前 viewport。
5. `T-CONT-05` overview bar 显示全记录、当前窗口、已加载范围。
6. `T-CONT-06` 事件 marker 简洁模式下不遮挡波形。
7. `T-CONT-07` Reject / Remain overlay 在 main canvas 和 overview bar 对齐。
8. `T-CONT-08` Undo / Redo 后 main canvas 和 overview bar 同步恢复。
9. `T-CONT-09` 清空草稿需要二次确认，确认后所有 overlay 清除。
10. `T-CONT-10` 页面上下滚动后 canvas、overview、状态栏一致。
11. `T-CONT-11` 键盘路径：PageDown、Arrow、Ctrl+Wheel、+/-、E、Z、Y 均可用。
12. `T-CONT-12` 移动端或窄屏不横向溢出，主波形仍优先。

## 8. 开发边界

允许改：

- `frontend/waveform-workbench.html`
- `frontend/waveform-workbench.css`
- `frontend/waveform-workbench.js`
- `scripts/e2e_waveform_workbench_module.mjs`
- 必要时新增独立 `scripts/review_*` 或 evidence JSON。

谨慎改：

- `frontend/waveform-workbench-adapter.js`
- `eeg_core/preprocess/qc_preview.py`

禁止改：

- router / Headroom / gateway / IPC / model route
- 癫痫源码工作台
- 主工作台大范围样式
- unrelated billing/admin/report

## 9. 下一步执行建议

建议下一轮直接开发 P0：

1. 前端新增 chunk cache，不再把旧窗口 fallback 拉伸到新窗口。
2. 新增 overview bar。
3. 降低事件 marker 视觉权重，增加事件显示模式。
4. 重组右侧操作区，删除重复清空按钮。
5. 补 `T-CONT-01` 到 `T-CONT-12` E2E。

完成后再做第二轮 UI polish：

1. 文案客户化。
2. 状态栏和帮助层级优化。
3. 窄屏和高密度状态评审。
4. 若 Open Design / Claude / DeepSeek 可用，再纳入真实三方最终验收；不可用则明确标注 unavailable，不伪造。

