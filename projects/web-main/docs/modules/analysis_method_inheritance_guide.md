# QLanalyser EEG 方法继承指南

更新时间：2026-06-21

## 1. 这份文档解决什么问题

不是所有脑电分析方法都应该一开始就进入主流程。
QLanalyser 的正确做法是：

1. 先把方法拆成可独立测试的子流程。
2. 先在实验室或 preview 层把输入、参数、输出、风险说清楚。
3. 只有满足契约、验收和边界要求的方法，才进入主流程。

这份指南帮助你判断一类方法应该放在哪一层，以及它要满足哪些门槛才能继承到主流程。

## 2. 三层继承关系

### 2.1 Preview

用于方法预研、学习、界面讨论和风险澄清。

特点：

- 可以展示思路、图示和参数结构。
- 不承诺稳定后端执行。
- 不进入默认客户主流程。

典型方法：

- PAC / CFC
- Connectivity
- Source localization boundary
- 更复杂的 TFR / 高级统计展示

### 2.2 Internal validation / Beta

用于把方法变成真正可跑、可复核、可导出的产品能力。

特点：

- 有固定输入、固定参数 schema、固定输出 schema。
- 有 artifact manifest、report mapping、acceptance gates。
- 有明显的风险边界和负例阻断。

典型方法：

- TFR / ERSP / ITC
- ICA 审计
- 坏段、坏 epoch 拒绝摘要
- 需要前处理依赖的增强分析

### 2.3 Stable

真正进入主流程的能力。

特点：

- 从上传到结果有完整 UI-only 流程。
- 能生成报告包、结果表、图和复现材料。
- 默认动作中可见，但边界仍需写清楚。

典型方法：

- QC / preprocessing readiness
- ERP / P300
- PSD / bandpower

## 3. 每个方法都要先拆成的子流程

无论方法多新、多复杂，先回答下面 6 步：

1. 输入是什么。
2. 必要前处理是什么。
3. 参数怎么输入。
4. 核心算法/统计步骤是什么。
5. 输出是什么。
6. 风险和边界是什么。

这 6 步拆清楚，才谈得上继承到主流程。

## 4. 主流程继承规则

方法要进入 QLanalyser 主流程，至少要满足这些条件：

### 4.1 输入契约清楚

- 文件格式明确。
- 必需 metadata 明确。
- 依赖事件、epoch、参考、坏道、坏段的前置条件明确。
- 不支持的输入要被明确拒绝。

### 4.2 参数契约清楚

- 参数必须是结构化的，不是散乱文本。
- 默认值要科学且可复现。
- 高级参数必须有解释和边界。

### 4.3 输出契约清楚

- `result.json`
- `manifest.json`
- 方法说明
- 图表
- 表格
- 复现文件
- 报告映射

### 4.4 风险边界清楚

- 不写诊断。
- 不写治疗建议。
- 不把传感器空间结果说成脑源。
- 不把 preview 说成 stable。
- 不把单份数据说成分组统计。

### 4.5 验收链路清楚

至少要能回答：

- 单元测试过了吗。
- API 能不能创建任务。
- UI 能不能点出来。
- 报告 ZIP 有没有正确证据。
- 负例有没有被拒绝。
- 文案有没有越界。

## 5. 推荐的主流程顺序

第一版建议按这个顺序做：

1. 上传 EEG
2. 预处理 / QC
3. ERP / P300
4. PSD / bandpower
5. 报告导出

增强但仍可主流程内复用的能力：

- ICA 审计
- 坏段 / 坏 epoch 拒绝摘要
- TFR / ERSP / ITC

暂时留在 preview / beta 的能力：

- PAC / CFC
- Connectivity
- Source localization

## 6. 每类方法的继承判断

| 方法类 | 子流程重点 | 继承到主流程的门槛 |
| --- | --- | --- |
| QC / preprocessing | 读文件、坏道、滤波、参考、坏段、QC 预览 | 先做，且必须稳定 |
| ERP / P300 | 事件、epoch、baseline、ROI、成分窗口、drop log | 有事件时进入主流程 |
| PSD / bandpower | Welch、频段、参考、窗长、band table | 已适合主流程 |
| TFR / ERSP / ITC | epoch、baseline、频率网格、时间窗、图和表 | 先 beta，再稳态 |
| ICA | 成分、剔除原因、前后对比、截图 | 适合与预处理绑定 |
| PAC / CFC | phase/amplitude band、surrogate、null model、边界 | 先 preview，再谈 beta |
| Connectivity | metric、参考、volume conduction、阈值、null model | 先 preview，再谈 beta |
| Source localization | MRI、头模型、正逆问题、ROI、边界 | 高门槛，最后再做 |

## 7. 你以后学习时的最实用问法

每遇到一个新方法，先问：

1. 它依赖什么前处理。
2. 它的参数哪些是必须的，哪些是默认的。
3. 它的结果是图、表、还是 summary。
4. 它能不能被单独测试。
5. 它进主流程后会不会误导用户。
6. 它现在应该是 preview、beta，还是 stable。

## 8. 当前产品建议

QLanalyser 现在最该优先推进的是：

- 预处理 / QC
- ERP / P300
- PSD / bandpower

这些是从“上传 EEG”到“拿到可交付结果”的主链路。

PAC、Connectivity、Source localization 这类方法要保留研究能力，但不要挤占第一版主流程。
