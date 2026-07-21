# QLanalyser EEG 方法与工具包纳入矩阵

更新时间：2026-06-21

## 1. 这页的用途

这是一张产品矩阵，不是论文综述。

它回答四件事：

1. 现在 QLanalyser 主流程里已经有哪些方法。
2. 哪些方法还在 preview / beta，不能当 stable 主流程承诺。
3. 新方法要满足什么条件，才能纳入主流程。
4. 主流程、增强流程、未来研究流程各自怎么分层。

## 2. 当前工具包与职责

| 工具包 / 生态 | 在 QLanalyser 里的职责 | 适合承载什么 |
| --- | --- | --- |
| MNE-Python | 当前主后端分析引擎 | 读文件、事件、epoch、PSD、ERP、QC、部分 TFR / 研究预览 |
| EEGLAB | 用户心智参考与兼容语义 | 让界面、术语、流程更像脑电用户熟悉的工作方式 |
| FieldTrip | 方法参考与高级分析语义参考 | 连接性、时间频率、源分析等方法学对齐 |

结论：

- **真正执行分析的是 MNE-Python。**
- **EEGLAB / FieldTrip 更像设计和方法学参考，不是当前主后端承诺。**

## 3. 主流程、增强流程、未来研究流程

| 类别 | 当前状态 | 是否进入主流程 | 典型方法 | 说明 |
| --- | --- | --- | --- | --- |
| 主流程 | 已启用 | 是 | QC / preprocessing readiness、PSD / bandpower、ERP / P300 | 上传 EEG 后最先考虑的结果链路 |
| 增强流程 | 已有设计或局部实现 | 条件进入 | ICA 审计、坏段 / epoch 拒绝、TFR / ERSP / ITC | 可用于主流程增强，但必须有更严格边界 |
| 预研流程 | preview / beta | 暂不进入 stable | PAC / CFC、Connectivity、Source localization、CSD | 可以研究、展示、做边界验证，但不能抢主流程位置 |

## 4. 方法纳入规则

每个新方法想进入 QLanalyser 主流程，至少要过下面这 6 个坎：

1. **输入清楚**
   - 文件格式
   - 采样率
   - 通道类型
   - 事件或 epoch 依赖
   - 参考和坏道前置条件

2. **参数清楚**
   - 每个参数的意义
   - 必填和默认
   - 合理范围
   - 参数 provenance

3. **子流程清楚**
   - 预处理
   - 计算
   - 统计
   - 可视化
   - 结果导出

4. **输出清楚**
   - 图
   - 表
   - JSON
   - manifest
   - 方法说明
   - 复现文件

5. **边界清楚**
   - 不写诊断
   - 不写治疗建议
   - 不把 sensor-space 说成 source-space
   - 不把 preview 说成 stable
   - 不把单份数据说成组统计

6. **验收清楚**
   - 单元测试
   - API / runner
   - UI 点击链路
   - 报告 ZIP
   - 负例阻断

## 5. 当前各类方法怎么定位

| 方法 | 当前定位 | 主流程继承条件 | 备注 |
| --- | --- | --- | --- |
| QC / preprocessing readiness | stable | 已满足 | 主流程入口 |
| PSD / bandpower | stable | 已满足 | 主流程入口 |
| ERP / P300 | beta/stable when events exist | 事件可读、epoch 可信 | 条件进入主流程 |
| ICA 审计 | internal validation / beta | 需要人工确认和前后证据 | 建议作为预处理增强 |
| Bad segment / epoch rejection | internal validation / beta | 需要 drop log、阈值、剩余 trial 数 | 建议绑定预处理或 ERP 前置 |
| TFR / ERSP / ITC | preview / beta | baseline、时间频率网格、图表和统计边界明确 | 适合作为增强分析 |
| PAC / CFC | preview | surrogate、null model、边界控制明确 | 先研究再产品化 |
| Connectivity | preview | reference、volume conduction 控制、metric 明确 | 先研究再产品化 |
| CSD | preview / boundary | 参考定义和适用场景明确 | 更适合边界说明 |
| Source localization | boundary / preview | MRI、头模型、正逆问题、ROI、方法学边界 | 高门槛，最后纳入 |

## 6. Source localization 为什么门槛最高

源定位不是简单的“换个图”。
它通常要求：

- MRI 或标准头模
- 头模型
- 正问题 / 逆问题
- 参考和先验
- ROI 或脑区定义
- 更严格的解释边界

所以它更适合：

- 先做 boundary / preview
- 再做 beta
- 最后才考虑是否进入主流程

## 7. 对第一版产品的建议

第一版主流程应该优先是：

1. 上传 EEG
2. 预处理 / QC
3. ERP / P300
4. PSD / bandpower
5. 报告导出

先别让 PAC、Connectivity、Source localization 抢占首页位置。

它们可以存在，但要以 preview / beta 的姿态存在。

## 8. 最适合你记忆的一句话

**主流程先做“能稳定交付的结果”，预研方法先做“能清楚说边界的证据”。**
