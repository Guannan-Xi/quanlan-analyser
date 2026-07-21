# 癫痫工作台 UI/交互重构需求规格

版本：2026-06-27
范围：实验室癫痫候选事件复核工作台，不进入 07 主工作台主干。
边界：不修改 ML 模型、特征顺序、scaler、threshold、Stage_Code 规则；不修改 router、Headroom、IPC；不混入 Band Power/PSD 语义。

## 1. 背景与目标

当前癫痫实验工作台已经完成 EDF 预置、ML 高保真任务加载、候选事件、人工复核、Raw/Filter preview、TimeChart 实验渲染和 SVG fallback。但页面仍偏“实验室聚合页”：数据选择、参数、源交互、候选事件、波形和结果文件垂直堆叠。生产级复核场景中，用户的主任务是：

1. 载入 EDF 和筛查结果。
2. 在 EEG 波形中定位候选事件。
3. 使用常规 EEG 浏览器手势缩放、平移、调增益和切换滤波视图。
4. 对候选事件和 epoch 状态进行人工复核。
5. 导出复核后的 JSON/CSV，同时保留源算法只读证据。

因此本轮目标是把“候选波形预览”升级为“EEG 波形复核工作区”，并为后续整页重构留下规格。

## 2. 用户角色与主流程

### 2.1 角色

- 研究员/工程师：查看候选事件，确认算法输出是否合理。
- 复核人员：在波形、probability 和 Stage_Code 离散块之间来回确认，记录人工结论。
- 内部开发/验证人员：检查源 ML 迁移是否高保真、UI 是否保留安全边界。

### 2.2 主流程

```text
选择/加载 EDF
-> 载入或运行 epilepsy_ml_xgboost
-> 自动选中第一个候选事件
-> 自动居中并加载事件附近波形
-> 浏览模式下缩放/平移/切 Raw-Filter/调增益
-> 显式进入矫正模式
-> 标记 Seizure / Normal / 待复核
-> 导出复核结果
```

## 3. 信息架构需求

### 3.1 当前阶段 P0

本阶段不整体重排页面，只增强波形 panel，使其具备 EEG 工作台手感：

- 波形区具备状态条：文件、窗口、事件、滤波、增益、渲染器、模式。
- 波形区具备 mini map：显示整段 EDF、当前窗口、当前候选事件。
- 波形区支持鼠标滚轮缩放、拖拽平移、键盘左右移动、快捷复位。
- 选择候选事件后，窗口自动回到事件附近，不再要求用户理解内部“刷新”语义。
- 浏览模式默认安全；修改 Stage_Code 必须显式进入矫正模式。

### 3.2 后续 P1 整页重构

建议将页面重构为：

```text
顶部固定任务栏：文件 / 任务 / 候选事件 / 人工修改 / 非医疗边界
主区：波形浏览器
右侧：候选事件列表 + 当前事件复核卡
底部：Epoch probability + Stage_Code 离散块
抽屉：参数、结果文件、原始 JSON、导出历史
```

参数和结果文件默认折叠；复核阶段主视野应优先给波形和事件。

## 4. EEG 波形交互需求

### 4.1 鼠标

| 操作 | 行为 |
|---|---|
| 滚轮 | 以鼠标所在时间点为锚点横向缩放 |
| Shift + 滚轮 | 左右平移当前窗口 |
| Ctrl/Cmd + 滚轮 | 调整体增益 |
| 鼠标拖拽 | 左右平移当前窗口 |
| 双击波形区 | 回到当前候选事件默认窗口 |

### 4.2 键盘

| 快捷键 | 行为 |
|---|---|
| Left / Right | 左右移动 20% 当前窗口 |
| Shift + Left / Right | 左右移动 80% 当前窗口 |
| + / - | 缩放时间窗 |
| R | 回到当前事件窗口 |
| F | Raw / Filter preview 切换 |
| E | 浏览模式 / 矫正模式切换 |
| Shift+1 / Shift+2 | 仅在矫正模式下标 Normal / Seizure |

### 4.3 增益

本阶段支持全局增益档位：

```text
0.5x, 1x, 2x, 4x, Auto
```

后续可扩展单通道增益和通道隐藏。

## 5. 复核安全需求

### 5.1 模式隔离

默认模式是浏览模式：

- 滚轮、拖拽、键盘导航只影响波形窗口。
- 点击候选事件只选择和加载波形。
- 不修改 Stage_Code。

矫正模式需要显式点击按钮或按 `E` 进入：

- Seizure / Normal 按钮才允许修改 epoch 范围。
- Shift+1 / Shift+2 才生效。
- UI 必须显示当前处于“矫正模式”。

### 5.2 Stage_Code 离散表达

Stage_Code 是离散 enum：

```text
0 = Normal
1 = Seizure
```

UI 禁止把 Stage_Code 画成连续缓慢上升曲线。Probability 可以连续；Stage_Code 只能用离散块、标签或事件区间表达。

## 6. 性能需求

- 复用 `/waveform-window` 直接窗口接口。
- 单次窗口请求目标 < 500 ms；实验验收阈值 < 2000 ms。
- 缩放/平移触发请求需 debounce，避免滚轮连续打爆后端。
- TimeChart 加载失败、WebGL 构造失败或 CDN 不可用时必须回退 SVG。
- 长期生产方案应引入窗口缓存或 pyramid，但本阶段不新增后端缓存。

## 7. 非医疗与合规边界

页面必须可见说明：

```text
仅用于科研筛查和候选事件复核，不用于诊断、确诊、治疗或临床决策。
```

导出结果必须保留源算法只读证据和人工复核层，不覆盖源产物。

## 8. 验收摘要

P0 验收：

1. 当前实验页可加载 EDF 任务。
2. 候选事件自动居中加载波形。
3. 滚轮缩放、拖拽平移、键盘移动可用。
4. Raw/Filter preview 切换后仍使用同一 viewport 语义。
5. SVG current 可回退。
6. 浏览模式下 Shift+1/2 不修改 Stage_Code。
7. 矫正模式下 Shift+1/2 才修改 Stage_Code。
8. Stage_Code DOM 仍保持 normal/seizure 离散类。

## 9. P1/P2 生产级补强范围

P1 硬化需求：

- 整页重构为“癫痫候选事件复核工作台”：顶部任务栏、主波形区、右侧事件/复核卡、底部 probability + Stage_Code 离散块、参数/文件抽屉。
- ML 任务必须异步呈现 pending/cancel/error/success，不允许 30s 级任务阻塞页面交互。
- 复核保存引入 `base_revision`、source artifact hash 和 optimistic lock；hash 不一致时拒绝覆盖，并提示重新载入。
- 导出只追加 review layer，不覆盖 ML 源 CSV/JSON；重复导出需要稳定命名和 manifest。
- 性能在负载下补 p95：raw window 目标 < 60 ms，filter window 目标 < 70 ms；P0 阶段仍以 < 500 ms 目标、< 2000 ms 硬阈值验收。

P2 可用性需求：

- 复核历史 diff、批量事件导航、热键提示、可访问性焦点顺序、截图视觉 QA。
- TimeChart / SVG / Canvas 对比矩阵；大通道数、大窗口、长 EDF 压力测试。
- 增加只读教学沙盒模式，但必须和真实复核写入隔离。

## 10. Stage_Code FSM 与非法迁移

Stage_Code 是离散 FSM，不是连续曲线。

允许状态：

```text
0 = Normal
1 = Seizure
```

允许迁移：

```text
Normal -> Seizure
Seizure -> Normal
source value -> same value, treated as no-op override removal
```

禁止行为：

- 写入 `0.2`、`0.5`、`maybe`、`probability`、`unknown` 等非 enum 值。
- 把 probability 的连续值映射为 Stage_Code 视觉曲线。
- 浏览模式、加载中、源 artifact hash mismatch、session revision mismatch 时写入 Stage_Code。
- 把 PSD / Band Power 的频段含义混入癫痫候选事件复核语义。

非法迁移必须回滚或拒绝，并在 E2E 证据中保留错误/拦截记录。

## 11. 边界证据包

每轮验收证据至少包含：

- `final_verdict.json`
- `browser_smoke.json`
- `stage_code_fsm.json`
- `performance_p95.json`
- `non_medical_snapshot.json`
- 自然 TimeChart、forced fallback、导出后截图。

边界扫描必须确认页面和导出中没有 07 主干入口、医疗承诺、PSD/Band Power 混用、router/Headroom/IPC 变更。
