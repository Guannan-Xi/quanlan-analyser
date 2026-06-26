# 癫痫源码工作台复刻需求文档

状态：生产级需求草案，供 07 主干集成使用
日期：2026-06-27
源系统：`D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC`
目标系统：`D:/Quanlan/Codes/Python/quanlan-analyser-official`
关联文档：`epilepsy_ml_high_fidelity_requirements.md`、`epilepsy_ml_high_fidelity_test_plan.md`、`epilepsy_ml_lab_sync_mirror_plan.md`

## 1. 目标

本需求定义 07 主干服务中“癫痫样事件分析工作台”的源码交互复刻标准。

这里要迁移的不是一个只输出 CSV 的后端任务，也不是一个网页报告页，而是 AR_analyser1 桌面端里的研究复核工作台：

1. 左侧设置输入、通道、epoch length、起止时间等参数；
2. 点击 Analyse 后进入进度页；
3. 分析完成后进入一屏联动复核画布；
4. 顶部显示 epoch 级 Normal/Seizure 离散状态条；
5. 下方同步显示 EEG、EMG envelope、ACC、EEG 频谱/时频图；
6. 支持事件跳转、epoch 跳转、窗口浏览、范围选择；
7. 支持 Seizure/Normal 人工矫正、Undo、Redo、Reset；
8. 支持保存图片、保存数据、加载历史；
9. 保持非医疗科研筛查边界。

## 2. 最高优先级原则

### 2.1 Stage_Code 是离散状态

`Stage_Code` 是 epoch 级分类状态：`0 = Normal`，`1 = Seizure`。主时间轴必须表达为离散状态切换，Normal 到 Seizure 必须是突变，而不是连续概率缓慢上升。

P0 禁止：

- 把 probability 或 RMS 折线作为 ML 模式主图；
- 用平滑曲线暗示癫痫状态逐渐上升；
- 用 threshold 线解释 ML 模式的主状态；
- 把状态条和数值趋势混成一个语义。

允许：

- probability/RMS 作为 tooltip、表格列、折叠层或 STD 模式辅助图；
- ML 模式主图仍以 `Stage_Code` 状态条和事件区间为主。

### 2.2 工作台不是报告卡片页

目标 UI 必须是“专家复核工作台”，不是“任务产物卡片页”。运行完成后，首屏核心应是：状态条 + 波形证据 + 导航/矫正工具，而不是 hero、说明卡、summary JSON 或下载列表。

### 2.3 性能是 P0

生产级要求是不卡顿。不能一次性把全量原始波形塞给浏览器；不能在 All 模式渲染数万个 DOM 节点；不能每次 hover 或选择都整页重绘；不能用慢速图片生成作为主复核链路。

### 2.4 Band Power / PSD 边界是 P0

癫痫工作台中的“频谱”是人工复核的时频证据层，用来帮助用户查看候选事件附近的波形背景；它不是 Band Power/PSD 分析模块。

P0 禁止：

- 在 epilepsy UI/API/export 中把频谱证据命名为 `band_power`、`psd_band_power`、`channel_band_power` 或频段功率结论；
- 用癫痫工作台的 `Stage_Code`、Seizure/Normal、review session 语义承载 Band Power；
- 把 Band Power 迁移验收并入癫痫工作台复刻验收。

允许：

- 共用 EDF 文件管理、任务队列、artifact 下载、实验室 fixture、性能埋点；
- 在文档中说明 Band Power 是并列模块；
- 在癫痫工作台显示 window/tile spectrogram 作为事件复核证据。

## 3. 用户角色和关键场景

### 3.1 用户角色

- 科研分析人员：上传/选择 EEG 数据，运行癫痫样候选事件筛查，查看候选事件。
- 专家复核人员：根据 EEG/EMG/ACC/频谱证据，对候选事件和 epoch 标签进行人工复核。
- 交付人员：导出 reviewed epoch scores、reviewed events、review actions 和复核报告。
- 实验室验证人员：用固定 EDF fixture 比较源码和 07 主干行为。

### 3.2 核心场景

P0 场景：

1. 选择 EDF 数据；
2. 选择 EEG/EMG/ACC 通道；
3. 选择 epoch length 3s 或 5s；
4. 运行 ML 高保真筛查；
5. 进入源码式复核工作台；
6. 点击第一个候选事件，所有视图跳转到事件窗口；
7. 查看状态条、EEG、EMG、ACC、频谱；
8. 选择一段 epoch，点击 Normal 或 Seizure；
9. 候选事件自动重算；
10. Undo、Redo、Reset 可用；
11. 保存 reviewed 结果；
12. 重新打开 session，复核状态完整恢复；
13. 导出复核包。

## 4. 源码交互复刻需求

### 4.1 页面布局

P0：

- 保留左参数区 + 右复核画布的主结构。
- 顶部保留分析名称、Number of Epochs to display、分页导航。
- 右侧画布分为：状态条、EEG、EMG、ACC、频谱/时频图。
- 底部或固定工具区保留 Analyse、Load history、Save picture、Save data。
- 运行完成后默认显示复核画布，不把结果埋到页面下方。

P1：

- 支持全屏复核模式。
- 支持紧凑布局和宽屏布局。
- 支持键盘可访问和焦点样式。

### 4.2 参数区

P0：

- 文件选择/上传支持 EDF；保留兼容 BDF/FIF 等现有格式能力。
- EEG/EMG/ACC 通道可选。
- 通道默认优先匹配源码习惯：EEG3、EEG1、ACC0；缺失时明确提示并要求用户选择或使用可解释 fallback。
- Epoch length 支持 3 和 5 秒。
- ML 模式加载对应 3s/5s 模型，遵循高保真算法迁移文档。
- 参数变更后必须清楚提示需要重新运行，避免旧结果误用。

参数合同矩阵：

| 参数 | 源码语义 | Web 要求 | 验收重点 |
| --- | --- | --- | --- |
| 文件 | EDF 优先，兼容实验数据 | 支持 EDF；保留 BDF/FIF 兼容能力 | 选择、上传、fixture 三条链路可用 |
| EEG/EMG/ACC 通道 | 默认倾向 EEG3/EEG1/ACC0 | 可选；缺失时显式 fallback | 不静默选错通道 |
| Epoch length | 3s/5s | ML 绑定 3s/5s 对应模型 | 3s/5s 路由和 artifact 可读回 |
| Start/End time | 限定分析区间 | 支持起止时间并影响任务 payload | 旧结果不得伪装成新参数结果 |
| ML/STD 模式 | 两套分析逻辑 | 切换后参数区和 workflow_id 同步 | 不混用 STD 阈值和 ML 模型 |
| Amplitude | 仅影响显示 | 写入 UI state，不进算法 payload | 不改变 source artifact |
| Raw/Filter preview | 仅影响复核视图 | filter profile 属于波形窗口请求 | 不改变 ML/STD 算法输入 |

### 4.3 分析运行状态

P0：

- Analyse 后显示进度、阶段和可恢复失败信息。
- 页面不可假死；长任务必须异步或 worker 化。
- 运行期间主要按钮防重复提交。
- 失败信息不泄露密钥、私有路径、完整内部堆栈。
- 完成后自动进入复核画布。

### 4.4 Epoch 状态条

P0：

- 用离散条、块、step 或 canvas lane 表达 `Stage_Code`。
- 蓝色/冷色代表 Normal，红色/暖色代表 Seizure，候选事件区间用边框、底线或半透明背景表达。
- 当前 epoch、选中范围、人工修改状态必须可区分。
- 状态切换为突变。
- All 模式不得用大量 DOM 按钮直接渲染所有 epoch。

P1：

- hover 显示 epoch 编号、起止时间、Stage、probability、是否人工修改、所属事件。
- 当前事件区间高亮。
- 支持拖动或框选范围。

### 4.5 波形和频谱复核

P0：

- EEG、EMG envelope、ACC、频谱/时频图在同一工作台中同步显示。
- 事件跳转、epoch 跳转、分页、时间滑块必须联动所有图。
- 当前选区必须在波形和状态条上同步高亮。
- Raw 和 Filter preview 可以作为切换层，但不能取代主工作台实时窗口数据。
- 振幅设置必须真实改变 EEG/EMG/ACC 显示范围。
- 每个图必须有通道名、单位、时间轴或等价上下文。

P1：

- 支持局部放大窗口或侧边放大面板。
- 支持 Ctrl/修饰键做 Y 轴缩放或等效交互。
- 支持减少动画模式。

### 4.6 导航

P0：

- Number of Epochs to display：All、100、50、30、20、10、5、3。
- first、previous、goto、next、last。
- 当前 page / total page 可见。
- 当前 epoch 输入框可跳转。
- 当前鼠标 epoch 可显示或有等价反馈。
- 事件表点击必须跳转到对应时间窗口。
- epoch 选择必须驱动右侧证据视图，而不是只改变小格子样式。

### 4.7 人工矫正

P0：

- Seizure 按钮把选中 epoch 范围设置为 `Stage_Code=1`。
- Normal 按钮把选中 epoch 范围设置为 `Stage_Code=0`。
- Shift+2 触发 Seizure；Shift+1 触发 Normal。
- 修改对象是 reviewed layer，不覆盖 source/model layer。
- 每次修改写入 action stack。
- 修改后重算 reviewed events 和统计。
- Undo/Redo/Reset 与源码语义一致。
- Reset 恢复到原始模型/算法结果。

### 4.8 候选事件表

P0：

- 显示 event id、起止时间、起止 epoch、持续时间、epoch 数、RMS/最大幅度等可用证据、复核状态。
- 点击事件跳转到事件窗口。
- 人工修改后事件表重算。
- 没有事件时必须明确解释：当前 reviewed Stage_Code 没有形成满足规则的连续 Seizure 区间。

### 4.9 保存、导出、历史

P0：

- 导出 reviewed epoch scores CSV。
- 导出 reviewed events CSV。
- 导出 review session manifest JSON。
- 导出 review actions JSONL 或等价审计记录。
- 导出当前视图截图/图片。
- 保存后重开必须恢复 reviewed labels、reviewed events、actions、当前任务元数据。
- 导出包包含非医疗边界说明。

## 5. 性能需求

### 5.1 用户可感知指标

P0 指标：

- 工作台页面初次可交互：普通 demo 文件 p50 < 1.5s，p95 < 3s。
- 已有任务打开复核工作台：p95 < 3s。
- 点击 event/epoch 后视觉反馈：p95 < 50ms。
- cached waveform 窗口重绘：p95 < 100ms。
- uncached 30-60s waveform 窗口数据可见：p95 < 800ms（本地生产级服务）。
- previous/next/goto 响应：p95 < 100ms。
- hover epoch 更新：p95 < 50ms。
- 100 epoch 范围内人工修改并重算事件：p95 < 200ms。
- 主线程 long task > 200ms 的次数为 0 或有明确豁免。
- 浏览器不因 All 模式、24h 文件或大事件表崩溃。

### 5.2 大数据能力

P0：

- 12 小时 EEG 可正常浏览、跳转、复核。
- 24 小时压力 fixture 不崩溃、不无限增长内存。
- 原始波形按窗口请求，不全量传到前端。
- 前端渲染使用窗口化、降采样、虚拟化或 canvas 聚合。
- 频谱支持 tile、窗口化或缓存，不一次性绘制超大矩阵。

### 5.3 防卡顿要求

P0：

- 不在前端用数万个 button 表示 All epochs。
- 不在每次 hover 时重算全部事件。
- 不在每次状态修改后整页 innerHTML 全量重建主图。
- 不把波形预览作为慢速后端图片生成主路径。
- 不在 UI 请求线程执行长时间 ML 推理。
- 不阻塞 router、Headroom、IPC 或其他服务通道。

## 6. 当前 Web 版差距

当前 Web 版已有基础：文件选择、上传、运行任务、epoch cells、事件表、本地 review override、Undo/Redo、导出 JSON/CSV、候选波形预览。

主要差距：

1. 页面结构偏卡片式，源码工作台感不足；
2. 运行后不是一屏联动复核画布；
3. `renderRmsChart` 折线会误导为连续趋势；
4. EEG/EMG/ACC/频谱不是主工作台的实时同步窗；
5. 波形预览依赖手动刷新和图片产物，交互慢；
6. amplitude 控件没有完整绑定波形视图；
7. event table 的权重过大，epoch/波形选择链不足；
8. All 模式和大文件性能策略未明确；
9. 保存/重开 reviewed session 仍需主干级 API 支撑。

## 7. 分级验收

### 7.1 P0 必须完成

- 源码式主布局和一屏复核画布；
- 离散 Stage_Code 状态条；
- EEG/EMG/ACC/频谱同步窗口；
- event/epoch 导航联动；
- Seizure/Normal + Shift+1/Shift+2；
- Undo/Redo/Reset；
- reviewed event 重算；
- reviewed export/reload；
- 性能指标通过；
- 非医疗边界通过；
- 不改 router/Headroom/IPC。

### 7.2 P1 建议完成

- hover 当前 epoch；
- 拖选/框选范围；
- 局部放大窗口；
- current mouse epoch 显示；
- 快捷键说明和可访问性增强；
- 当前视图截图导出与源码风格接近。

### 7.3 P2 可后置

- 多布局主题；
- 更丰富的标注协作；
- 服务端多人审阅锁；
- 高级频谱参数交互；
- 更复杂的报告模板。

## 8. 不做项

- 不改变 ML 模型权重和 scaler；
- 不改变高保真算法 parity 合同；
- 不创建第二套实验室专用癫痫算法；
- 不把 Band Power 迁移混入本工作台复刻范围；Band Power 作为并列分析模块迁移，只共享文件选择、任务、artifact 和实验室 fixture 基础设施；
- 不修改 router、Headroom、gateway、IPC；
- 不做临床诊断、治疗、确诊、分诊功能；
- 不重构无关模块。

### 8.1 与 ML 高保真和 Band Power 的边界

本需求只定义“癫痫样事件筛查结果的源码式复核工作台”。ML 算法迁移仍以 `epilepsy_ml_high_fidelity_requirements.md` 和对应测试文档为准：模型文件、scaler、阈值、epoch 构造、特征顺序、`Stage_Code` 生成规则不得因 UI 复刻而改变。

Band Power 需要迁移，但不应塞进癫痫工作台内部。07 主干集成时应把 Band Power 作为并列模块处理：可复用 EDF 文件管理、任务队列、artifact 下载、实验室数据生成和性能基线，但不得复用癫痫工作台的 `Stage_Code`、Seizure/Normal 人工矫正、事件重算语义。

## 9. 最终完成定义

完成必须同时满足：

1. 用户能按源码工作流完成一次完整人工复核；
2. 状态条表达为突变式离散状态；
3. 波形证据、状态条、事件表和人工矫正联动；
4. 大文件浏览不卡顿；
5. reviewed 保存、重开、导出可验；
6. 独立 E2E 和性能测试通过；
7. 非医疗边界无违规；
8. router/Headroom/IPC 健康检查无回归。


## 10. 源码证据索引

以下证据用于约束实现和评审，避免把 Web 工作台做成泛化报告页：

- 显示 epoch 数下拉 `All/100/50/30/20/10/5/3`：`D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis.py:548`。
- epoch length 选择 `3/5` 秒：`D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis.py:845`。
- EEG/EMG/ACC/频谱四轨创建：`D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis.py:1042`。
- 画布布局顺序包含状态条、EEG、EMG、ACC、频谱：`D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis.py:1087`。
- EMG/ACC X 轴链接 EEG：`D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis.py:1066`。
- 时间滑块触发显示更新：`D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis.py:2113`。
- `map_stages={0:"Normal",1:"Seizure"}`：`D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis.py:712`。
- 状态条用 `hlines(scores, start, end)` 画离散分段：`D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis.py:3591`。
- Seizure/Normal/Undo/Redo/Reset 按钮连接：`D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis.py:2115`。
- 人工矫正直接写 `Stage_Code`：`D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis.py:2873`。
- EEG/EMG/ACC amplitude 菜单：`D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis.py:660`。
- 三轨 Auto/Manual Y 轴范围：`D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis.py:3198`。
- ML 版继承基础工作台 UI：`D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis_ML.py:22`。
- ML probability 经过 0.5 阈值后生成离散 `Stage_Code`：`D:/Quanlan/Codes/Python/AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis_ML.py:416`。

当前 Web 差距证据：

- 当前主区按 summary、source toolbar、timeline、events、waveform、artifacts 分面板渲染：`D:/Quanlan/Codes/Python/quanlan-analyser-official/frontend/epilepsy-workbench.js:457`。
- 当前 timeline 后接 `renderRmsChart()` 单曲线：`D:/Quanlan/Codes/Python/quanlan-analyser-official/frontend/epilepsy-workbench.js:701`。
- 当前事件区以候选事件表为中心：`D:/Quanlan/Codes/Python/quanlan-analyser-official/frontend/epilepsy-workbench.js:740`。
- 当前波形预览是候选事件窗口图片：`D:/Quanlan/Codes/Python/quanlan-analyser-official/frontend/epilepsy-workbench.js:793`。
- 当前 review payload 已含非医疗边界和 `stage_code_map`，应保留并前置：`D:/Quanlan/Codes/Python/quanlan-analyser-official/frontend/epilepsy-workbench.js:1406`、`D:/Quanlan/Codes/Python/quanlan-analyser-official/frontend/epilepsy-workbench.js:1414`。

## 11. 补充性能阈值

除第 5 节指标外，生产验收还必须记录：

- 首屏框架显示不超过 1s；已有分析产物时工作台可交互不超过 2s。
- epoch 选择、Normal/Seizure、Undo/Redo 的 P95 不超过 100ms。
- 时间滑块和分页切换 P95 不超过 150ms；连续拖动保持至少 30fps，目标 60fps。
- 10k epoch 内状态条更新不超过 100ms。
- 50k epoch 及以上必须窗口化或 canvas 聚合，禁止创建 50k 个长期 DOM 节点。
- 后台解析、重采样、频谱计算不得阻塞主线程超过 200ms。
- 切换窗口后释放不可见波形缓存，禁止全量 EEG/EMG/ACC 点长期留在 DOM/SVG。
