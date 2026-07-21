# Module Lab 方法开发测试试验台需求与测试文档

Date: 2026-06-25
Owner: QLanalyser 07 product line, 02 module support
Status: beta review baseline
Scope: `frontend/module-lab.html`, `frontend/module-lab.js`, `frontend/module-lab.css`, `/api/tasks`, `/lab/demo/run/{module}/configured`, generated EDF end-to-end acceptance, layout review.

## 1. 文档目的

本文档定义 Module Lab 的产品定位、方法分组、参数暴露原则、页面测试要求和验收证据。它用于指导后续方法开发、代码评审、科学评审、UI 评审和端到端测试。

Module Lab 不是正式客户工作台，也不是销售演示页。它是一个面向内部开发、科学复核、QA 和产品评审的“方法开发测试试验台”。它必须让评审人员在没有账号、没有正式项目、没有客户数据管理流程的情况下，独立验证预处理和每个分析方法分支是否真正可运行、可测试、可复现、可解释。

## 2. 产品定位

### 2.1 必须是什么

Module Lab 必须满足以下定位：

1. 无账号入口：评审人员可以直接打开页面测试，不依赖登录、套餐、订单、正式项目权限。
2. 无正式项目依赖：页面可以在后台自动创建或复用临时测试上下文，但不能要求用户先理解正式项目管理流程。
3. 方法开发优先：页面服务于单个方法的开发、参数调试、任务提交、结果回读和证据收集。
4. 真实后端优先：每个方法必须调用真实后端任务，不允许只做前端假状态或静态样例。
5. 预处理保留：试验台必须保留数据准备、QC、预处理相关入口，因为很多分析方法的正确性依赖数据可分析性。
6. 分析分支独立：每个科学问题对应的分析分支必须可以独立运行、独立失败、独立产出证据。
7. 本地样例可测：页面必须支持生成 EDF 或上传本地 EDF，让评审人员不用等待真实客户数据即可做端到端测试。
8. 中文可评审：页面面向当前内部评审时，主要可见文案必须是中文，并避免乱码、英文残留和内部字段上屏。

### 2.2 明确不是什么

Module Lab 当前不承担以下目标：

1. 不替代正式客户项目工作台。
2. 不承担计费、团队协作、权限、订单、发票等商业流程。
3. 不展示临床诊断结论，不暗示医疗用途。
4. 不把所有算法包装成一个“万能分析”入口。
5. 不为了减少卡片数量而合并科学含义不同的方法。
6. 不暴露尚未被后端实际使用、验证或记录的参数。
7. 不提供复杂 JSON 原始编辑器，除非已经有结构化、可校验、可回显的编辑控件。

## 3. 目标用户和典型场景

### 3.1 方法开发者

目标：快速选择数据、修改参数、运行单个方法，查看任务状态、参数回显和产物路径。

关键需求：

- 上传或生成一份测试 EDF。
- 对某个方法反复调整参数。
- 看到后端是否真实接收参数。
- 看到失败原因，而不是只看到“运行失败”。
- 可以保存或引用本次任务证据。

### 3.2 科学评审人员

目标：判断方法分组、默认参数、可暴露参数和结果解释是否符合脑电科研语境。

关键需求：

- PSD、TFR、ERP、PAC、连接性等方法边界必须清楚。
- 同一后端 runner 支撑多个科学入口时，UI 必须按科学问题拆开。
- ERSP、ITC 等指标要作为 TFR 输出或度量呈现，不能误导为完全独立方法。
- 参数名称、单位、默认值和使用范围必须能被复核。

### 3.3 QA / 验收人员

目标：在无账号环境里跑完页面级端到端测试，并获得机器可读证据。

关键需求：

- 有稳定生成的本地 EDF。
- 有可重复执行的 E2E 脚本。
- 每个方法都能独立提交任务。
- 任务完成后有 artifact、参数回显、状态记录。
- 页面在桌面和窄屏下没有横向溢出、遮挡、重复标签和乱码。

### 3.4 产品评审人员

目标：确认页面是否符合“方法试验台”而不是“客户成品工作台”的定位。

关键需求：

- 页面第一眼能看出是测试方法，不是正式项目流程。
- 分组能帮助评审人员找到想测的方法。
- 单方法卡片不出现重复“方法类型”选择。
- 对未来高级能力保留位置，但不把未成熟控件提前上屏。

## 4. 核心用户流程

### 4.1 基础流程

1. 打开 Module Lab 页面。
2. 页面连接后端 API。
3. 用户选择生成本地 EDF 或上传本地 EDF。
4. 页面完成临时测试上下文准备。
5. 用户先查看数据可分析性或预处理状态。
6. 用户选择一个分析方法分支。
7. 用户调整该方法参数。
8. 页面提交真实后端任务。
9. 后端创建 `/api/tasks` 任务并执行 runner。
10. 页面轮询任务状态。
11. 页面展示任务完成、失败原因、参数回显和产物链接。
12. 验收脚本读取结果 JSON、artifact 和布局证据。

### 4.2 数据路径要求

Module Lab 可以在后台自动创建测试项目或测试记录，但 UI 不应把“项目管理”作为主流程。对评审人员来说，数据路径应表达为：

- 当前测试数据。
- 数据可分析性。
- 预处理 / QC。
- 单个分析方法。
- 结果和证据。

后台技术对象可以包括 project、file、task、artifact，但这些对象不应压过方法测试主线。

## 5. 方法分组需求

### 5.1 分组原则

方法分组必须按科学问题和分析目的组织，而不是按后端文件名、runner 复用关系或历史实现路径组织。

分组必须遵守以下原则：

1. PSD 和 TFR 不是同一类方法。
2. 连续频谱功率、事件锁定时域反应、事件锁定时频动态必须分开。
3. Multitaper 是估计器或算法家族，不等于一个单独科学问题；因此 multitaper PSD 和 multitaper TFR 应分成独立入口。
4. PAC / CFC 和传感器连接性解释对象不同，必须分开。
5. 参考变换、平均参考、指定参考、CSD 属于传感器空间变换，不应和分析统计结果混在一起。
6. 单方法区域不显示重复“方法类型”选择；方法类型只有在同一区域确实有多个可选方法时才出现。

### 5.2 当前 beta 分组

| UI 分组 | UI 方法 ID | 后端模块 | 科学目的 | 分组理由 |
| --- | --- | --- | --- | --- |
| QC / 数据可分析性 | `qc` | `qc` | 检查数据质量、通道、采样、可分析性 | 属于分析前准备，不是结果分析 |
| 连续频谱功率 | `psd` | `psd` | 估计连续数据的功率谱和频带功率 | 回答“哪些频率能量更强” |
| 事件锁定时域 | `erp` | `erp` | 估计事件相关时域波形，如 P300 | 回答“事件后电位如何变化” |
| 事件锁定时频 | `tfr` | `tfr` | 估计事件锁定时频功率、ERSP、ITC 等 | 回答“事件后频率随时间如何变化” |
| 多窗 PSD | `multitaper_psd` | `multitaper_psd_tfr` | 用 multitaper 估计连续频谱功率 | 后端复用 runner，但科学入口属于 PSD |
| 多窗 TFR | `multitaper_tfr` | `multitaper_psd_tfr` | 用 multitaper 估计事件锁定时频动态 | 后端复用 runner，但科学入口属于 TFR |
| 参考与空间变换 | `reference_csd` | `reference_csd` | 平均参考、指定参考、双极参考、CSD | 改变传感器空间表达，不是统计分析 |
| 跨频耦合 | `pac` | `pac` | 相位-振幅耦合、跨频耦合 | 解释不同频段之间的耦合关系 |
| 传感器连接性 | `connectivity` | `connectivity` | 通道之间的连接性指标 | 解释传感器之间的相互关系 |

### 5.3 TFR、ERSP、ITC 的关系

当前要求：

- TFR 是方法入口。
- ERSP 和 ITC 是 TFR 任务内的输出指标或度量。
- 如果未来要把 ERSP、ITC 做成独立入口，必须满足两个条件：
  1. 后端 runner、参数集合、输出产物和解释文案已经形成稳定差异。
  2. UI 上的独立入口能减少评审混淆，而不是制造重复按钮。

在当前 beta 阶段，ERSP / ITC 不作为和 TFR 并列的独立方法入口。

### 5.4 PSD 和 TFR 的边界

PSD：

- 通常面向连续或相对静态时间段。
- 主要输出频率轴上的功率分布。
- 典型参数包括频段范围、Welch 窗长、重叠、通道选择、平均方式、频带定义。

TFR：

- 面向事件锁定或时间变化过程。
- 输出时间 x 频率矩阵，可能包含 power、ERSP、ITC。
- 典型参数包括频率列表、周期数、基线窗口、基线校正模式、时间降采样、是否平均 epoch。

因此，PSD 和 TFR 不能放在同一个区域里只靠一个“方法类型”参数切换。

## 6. 参数暴露原则

### 6.1 可暴露参数

参数必须同时满足以下条件才适合上屏：

1. 后端 runner 实际读取该参数。
2. 参数有明确单位、类型、默认值和边界。
3. 参数能在任务记录或结果证据中回显。
4. 错误输入能被前端或后端明确拒绝。
5. 普通评审人员不需要理解内部实现细节就能判断含义。

### 6.2 暂不暴露参数

以下参数或配置暂不直接上屏：

1. `bad_segments` 原始数组：需要结构化坏段编辑器。
2. ERP 自定义 `components` 时间窗数组：需要组件时间窗编辑器。
3. 复杂 bipolar 多对配置：当前可保留简写 beta 输入，但正式化前需要成对编辑器、通道校验和预览。
4. 任意 JSON 高级参数：必须先有 schema、示例、校验、回显和错误提示。
5. 后端未实际使用的参数：禁止为了“看起来专业”提前展示。

### 6.3 默认值要求

默认值必须满足：

- 能让生成 EDF 端到端测试通过。
- 不制造临床含义。
- 不要求用户知道内部任务对象。
- 与后端 runner 默认值一致，或在 UI 中明确说明差异。
- 如果 UI 方法拆分但后端 runner 复用，必须通过固定参数保证后端行为明确。例如：
  - `multitaper_psd` 固定 `analysis_family=psd`。
  - `multitaper_tfr` 固定 `analysis_family=tfr`。

## 7. UI 需求

### 7.1 页面结构

页面应至少包含：

1. API 连接状态。
2. 当前测试数据状态。
3. 数据生成 / 上传入口。
4. 数据可分析性 / 预处理区域。
5. 稳定分析方法区域。
6. beta 分析方法区域。
7. 每个方法的参数表单。
8. 运行按钮。
9. 任务状态、失败原因、参数回显和产物链接。

### 7.2 中文与文案

要求：

- 面向评审人员的主要文案使用中文。
- 内部字段名不直接作为主要标签上屏。
- 英文缩写可以保留，但必须放在中文语境里，如“连续频谱功率（PSD）”。
- 不出现乱码。
- 不使用空泛宣传语。
- 不把“方法类型”重复显示在只有一个方法的区域。

### 7.3 布局

要求：

- 桌面宽屏下方法卡片宽度稳定，不出现过窄三列导致参数挤压。
- 窄屏下参数字段切换为单列。
- 不能有横向滚动条。
- 按钮、标签、输入框不能重叠。
- 方法分组导航和区域标题必须一致。
- 单方法区域标题、说明、参数区和运行按钮层级清楚。

### 7.4 未来 UI 增强

建议后续增加：

1. 基础 / 高级参数折叠。
2. 坏段结构化编辑器。
3. ERP 组件时间窗编辑器。
4. 双极参考通道对编辑器。
5. 参数模板保存和恢复。
6. 结果对比视图。
7. 每个方法的最小可接受数据条件提示。

这些增强不阻塞当前 beta 试验台验收，但应纳入后续迭代。

## 8. 后端与任务要求

### 8.1 真实任务

每个方法必须创建真实任务，并通过 `/api/tasks` 或等价任务接口可回读。任务证据至少包含：

- task id。
- module name。
- status。
- submitted parameters。
- started / completed timestamp。
- failure reason, if failed。
- artifacts or output references。

### 8.2 后端映射

UI 方法 ID 可以和后端模块名不同，但必须显式映射并可测试。例如：

- `multitaper_psd` -> backend `multitaper_psd_tfr`, fixed `analysis_family=psd`。
- `multitaper_tfr` -> backend `multitaper_psd_tfr`, fixed `analysis_family=tfr`。

这种映射允许 UI 按科学问题组织，同时保持后端 runner 复用。

### 8.3 失败处理

失败必须可解释：

- 参数校验失败：指出字段和原因。
- 数据条件不足：指出缺少事件、通道、采样率、montage 或 epoch 条件。
- CSD 失败：提示需要电极位置或 montage，而不是泛化为“运行失败”。
- 任务执行异常：保留后端错误摘要和 task id，便于开发者追踪。

## 9. 测试计划

### 9.1 静态检查

每次修改 Module Lab 相关文件后必须运行：

```powershell
node --check frontend\module-lab.js
node --check scripts\acceptance_module_lab_grouped_methods_e2e.mjs
python -X utf8 scripts\check_no_mojibake.py frontend\module-lab.js frontend\module-lab.css scripts\acceptance_module_lab_grouped_methods_e2e.mjs
```

若修改本文档或其他中文文档，也应执行 mojibake 检查或 UTF-8 readback。

### 9.2 生成 EDF

必须有本地生成 EDF 脚本，用于无客户数据测试：

```powershell
python -X utf8 scripts\generate_module_lab_grouped_methods_edf.py
```

生成 EDF 必须满足：

- 能被后端读取。
- 包含当前 E2E 所需的通道、采样率、事件或注释条件。
- 能支持 PSD、ERP、TFR、multitaper、reference、PAC、connectivity 的基本路径。
- 输出路径写入验收证据。

### 9.3 方法级验收

方法级验收用于确认单个 runner 的后端能力：

```powershell
python -X utf8 scripts\acceptance_tfr_module.py
python -X utf8 scripts\acceptance_reference_csd_module.py
```

当前 beta 证据还包括：

- `work\release_evidence\20260622-tfr-module\acceptance_tfr_module.json`
- `work\release_evidence\20260622-pac-module\acceptance_pac_module.json`
- `work\release_evidence\20260622-reference-csd-module\acceptance_reference_csd_module.json`
- `work\release_evidence\20260622-multitaper-psd-tfr-module\acceptance_multitaper_psd_tfr_module.json`
- `work\release_evidence\20260622-connectivity-module\acceptance_connectivity_module.json`

### 9.4 页面端到端验收

页面级 E2E 必须验证：

1. 页面可打开。
2. API 地址可识别。
3. 方法分组数量正确。
4. 本地 EDF 可生成或上传。
5. 每个 UI 方法入口可独立运行。
6. 后端 task 被创建。
7. 参数被提交并回显。
8. 任务完成后有 artifact。
9. `multitaper_psd` 和 `multitaper_tfr` 分别执行，并分别带固定 `analysis_family`。
10. E2E 输出 JSON `status=passed`。

当前命令：

```powershell
node scripts\acceptance_module_lab_grouped_methods_e2e.mjs
```

当前证据：

- `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.json`
- `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_local.edf`

### 9.5 布局与视觉验收

布局验收必须覆盖桌面和窄屏：

```powershell
node C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\layout_review_20260625.mjs
```

必须检查：

- 页面中文存在。
- group count 正确。
- 无横向溢出。
- 方法卡片不互相遮挡。
- 参数字段不挤出容器。
- 单方法区域不出现重复“方法类型”。
- 截图可作为人工复核证据。

当前证据：

- `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_layout_review_20260625\layout_review.json`
- `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_layout_review_20260625\desktop.png`
- `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_layout_review_20260625\narrow.png`

## 10. 发布前验收标准

Module Lab beta 至少满足以下条件，才能进入下一轮发布候选：

1. 页面中文文案无乱码。
2. 方法分组符合本文第 5 节。
3. PSD 和 TFR 不被合并为一个区域。
4. Multitaper PSD 和 Multitaper TFR 是独立 UI 入口。
5. 参考 / CSD 不显示重复“方法类型”。
6. 所有上屏参数都被后端实际使用、校验或记录。
7. 生成 EDF E2E 覆盖所有当前 UI 方法入口。
8. 每个方法产生真实 task id。
9. 每个成功任务有 artifact 或明确输出引用。
10. 失败任务有可解释原因。
11. 桌面和窄屏布局无横向溢出。
12. `docs/TASK_LOG.md` 和 `docs/PROJECT_STATUS.md` 记录证据路径。

## 11. 当前已验证状态

截至 2026-06-25，当前 beta 基线已验证：

- `node --check frontend\module-lab.js` passed。
- `node --check scripts\acceptance_module_lab_grouped_methods_e2e.mjs` passed。
- Module Lab 相关前端和 E2E 脚本 mojibake 检查 passed。
- 生成 EDF 页面级 E2E passed。
- 当前 E2E 覆盖 9 个独立 UI 方法入口。
- 布局评审 passed，桌面和窄屏无横向溢出。

当前关键证据：

- E2E JSON: `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_e2e.json`
- Generated EDF: `work\release_evidence\20260625-module-lab-grouped-methods-e2e\module_lab_grouped_methods_local.edf`
- Layout JSON: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_layout_review_20260625\layout_review.json`
- Layout screenshots: `C:\Users\XGN\Documents\Codex\2026-06-22\quanlan-02-qlanalyser-module-support-replacement\outputs\module_lab_layout_review_20260625\desktop.png`, `...\narrow.png`

## 12. 后续迭代清单

优先级建议：

1. 增加坏段结构化编辑器，替代原始 `bad_segments` JSON。
2. 增加 ERP 组件时间窗编辑器，支持 P1/N1/P2/N2/P3 等组件配置。
3. 增加双极参考通道对编辑器，替代自由文本简写。
4. 为每个方法增加“最小数据条件”提示。
5. 增加参数模板保存和一键恢复默认值。
6. 增加任务结果对比视图，便于同一数据多参数对比。
7. 增加方法级证据矩阵页面，把 task、参数、artifact、截图、JSON 证据汇总到一个评审入口。

## 13. 变更控制

后续如修改方法分组、方法 ID、后端映射、参数暴露或测试脚本，必须同步更新本文档，并至少补充：

- 变更原因。
- 影响的方法入口。
- 后端映射变化。
- 新增或删除参数。
- 重新运行的测试命令。
- 新的证据路径。

任何“为了 UI 简洁而合并方法”的变更，都必须先通过科学边界复核。不能再把 PSD 和 TFR、PAC 和连接性、参考变换和统计分析混成一个区域。
