# QLanalyser 全页面对抗性视觉逻辑评审

Date: 2026-07-05  
Status: review, not implementation  
Scope: 登录后客户主工作台页面、普通模式、示例模式、用户截图指出的数据管理页。  
Reviewer: Codex  

## 0. 结论

本轮补评审确认：上一份 `qlanalyser_beginner_analysis_flow_ui_redesign_20260705.md` 是设计合同，不是完整逐页对抗性评审。当前 UI 的核心缺陷不是单个页面不好看，而是全局存在同一类问题：

```text
页面路由、步骤条、当前状态、主按钮和下一步之间没有形成唯一真相。
```

因此用户会反复遇到：

- 我到底在第几步？
- 当前页面是用来做什么的？
- 现在应该按哪个按钮？
- 为什么一个信息在多个地方重复？
- 示例模式到底是在教学、试用，还是正常工作区？

本轮判定：

```yaml
overall_decision: revise
P0: 0 confirmed from current screenshots
P1: 12
P2: 18
highest_risk: P1 workflow_state_conflict
first_fix_target: 数据管理页 + 全局步骤条状态规则
```

> 说明：当前截图未发现不可读乱码、主页面横向溢出、临床诊断过度承诺等 P0。但多处 P1 会持续造成新手路径混乱，不能算“面向小白可用”。

## 1. 证据来源

### 1.1 用户指出的截图

```text
C:\Users\XGN\xwechat_files\wxid_vcs1q0qhwqdb21_2c98\temp\InputTemp\e7373e74-b784-4765-98ca-bc6cf3b8adc4.png
```

截图状态：

- 页面：数据管理。
- 模式：示例模式。
- 已有示例项目和示例数据。
- 顶部步骤条高亮：`4 运行分析`。
- 页面主内容仍在：数据管理 / 项目数据文件 / 文件详情。

### 1.2 本轮浏览器抓图

普通模式，2048 x 1152，`http://127.0.0.1:4174/index.html?customer_demo=auto&density=2`：

```text
outputs/adversarial_all_pages_20260705/01-dashboard.png
outputs/adversarial_all_pages_20260705/02-storage.png
outputs/adversarial_all_pages_20260705/03-analysis.png
outputs/adversarial_all_pages_20260705/04-workflow.png
outputs/adversarial_all_pages_20260705/05-statistics.png
outputs/adversarial_all_pages_20260705/06-publication.png
outputs/adversarial_all_pages_20260705/07-journey.png
outputs/adversarial_all_pages_20260705/08-userCenter.png
outputs/adversarial_all_pages_20260705/all_pages_snapshot_report.json
```

示例模式引导层抓图：

```text
outputs/adversarial_all_pages_teaching_20260705/teaching_pages_snapshot_report.json
outputs/adversarial_all_pages_teaching_after_guide_20260705/teaching_after_guide_snapshot_report.json
```

### 1.3 采用的评审规范

- `docs/product/qlanalyser_beginner_analysis_flow_ui_redesign_20260705.md`
- `docs/product/qlanalyser_ui_interaction_visual_governance_master_20260628.md`
- `docs/product/qlanalyser_project_design_system_20260628.md`
- `docs/product/qlanalyser_research_user_copy_governance_spec_20260701.md`
- `docs/quality/visual_layout_design_spec.md`
- `D:\QuanLanKnowledgeBase\learning-notes\design\B2B_SCIENTIFIC_DASHBOARD_SCREENSHOT_AUDIT_CHECKLIST_CN.md`
- `D:\QuanLanKnowledgeBase\learning-notes\design\UX_STATE_FEEDBACK_EMPTY_ERROR_LOADING_MOTION_GATE_CN.md`

## 2. 评审标准

每页按以下问题评审：

```yaml
page:
target_user:
primary_task:
first_glance:
current_state_truth:
primary_action:
duplicate_information:
state_feedback:
visual_density:
scientific_boundary:
accessibility_readability:
P0:
P1:
P2:
fix:
decision:
```

评分维度：

| 维度 | 通过要求 |
| --- | --- |
| 视觉层级 | 5 秒内知道本页主任务 |
| 一致性 | 路由、标题、步骤条、按钮表达一致 |
| 可用性 | 一个主动作，禁用原因清楚 |
| 品牌匹配 | 专业科研工作台，不像模块演示 |
| 现代专业感 | 开阔、克制、控件轻量 |
| 可读性 | 文字不重叠、不依赖 80% 缩放 |
| 科学边界 | 不暗示诊断，不夸大方法能力 |

## 3. 全局 P1 问题

### P1-01: 步骤条表达的是“推荐下一步”，但视觉上像“当前页面”

证据：

- 用户截图：页面标题是 `数据管理`，步骤条高亮 `4 运行分析`。
- 普通模式 `02-storage.png`：页面是数据管理，步骤条高亮 `2 上传数据`。
- `04-workflow.png`：页面是分析任务，步骤条高亮 `4 运行分析`。

问题：

步骤条同时承担了三件事：

1. 当前路由。
2. 已完成阶段。
3. 下一步推荐。

这三者没有视觉区分。用户截图中最明显：用户在数据管理页，但系统告诉他正在运行分析。

修复：

- 步骤条只表示主流程进度，不表示当前路由。
- 当前页面标题和步骤条高亮必须一致，或步骤条改成 `已完成 / 当前建议下一步` 两层表达。
- 在数据管理页，如果数据已准备且下一步是运行分析，应显示：

```text
当前页面：数据管理
下一步建议：运行分析
```

不要把 `运行分析` 做成步骤条当前高亮。

### P1-02: 多页面重复标题，降低第一眼定位

证据：

- `01-dashboard.png`: headings 为 `项目管理 / 项目管理`。
- `02-storage.png`: headings 为 `数据管理 / 数据管理`。
- `05-statistics.png`: headings 为 `结果查看 / 结果查看`。
- `06-publication.png`: headings 为 `报告交付 / 报告交付`。

问题：

顶部标题和面板标题重复，但没有增加信息。新手看到的不是任务，而是模块名重复。

修复：

- 顶部保留任务标题。
- 面板标题改成对象或动作：

| 页面 | 顶部标题 | 面板标题 |
| --- | --- | --- |
| 项目 | 开始一次 EEG 分析 | 当前项目 |
| 数据 | 上传或选择 EEG 数据 | 项目数据文件 |
| 准备 | 检查 EEG 数据 | 波形预览 |
| 分析 | 选择分析方法 | 推荐分析 |
| 结果 | 查看分析结果 | 最近结果 |
| 报告 | 生成和下载报告 | 报告包 |

### P1-03: 主按钮数量不稳定

DOM 证据：

| 页面 | primaryButtonCount | 问题 |
| --- | ---: | --- |
| dashboard | 1 | 可接受 |
| storage | 2 | 无项目状态仍有两个主按钮 |
| analysis | 1 | 可接受，但空态重复 |
| workflow | 0 | 没有明确可运行主按钮 |
| statistics | 0 | 空态没有主动作 |
| publication | 2 | 生成报告与去数据准备竞争 |
| userCenter | 2 | 充值/提交开票抢权重 |

修复：

- 每个页面每个状态只保留一个主按钮。
- 禁用主按钮不算主动作，必须有对应可执行恢复动作。
- 报告页无结果时主按钮只能是 `去运行分析` 或 `去数据准备`，不能同时显示 `生成交付报告`。

### P1-04: 示例模式引导层会接管导航，遮蔽真实页面

证据：

- 自动抓图中，进入示例模式后，尝试切换 `storage / analysis / workflow` 仍停留在 `dashboard`。
- 可见按钮仍包含 `上一步 / 下一步 / 结束引导`。

问题：

引导层本身可能是合理的，但对全页面使用来说，它会阻止用户自由验证页面。如果用户想直接去数据页，引导层不应把导航锁死或反复拉回。

修复：

- 引导层只在首次进入时显示。
- `结束引导` 必须可靠关闭，并持久记录。
- 引导中点击左侧导航时，应询问是否退出引导，不能静默拉回。

## 4. 用户截图专项评审：示例模式数据管理页

截图路径：

```text
C:\Users\XGN\xwechat_files\wxid_vcs1q0qhwqdb21_2c98\temp\InputTemp\e7373e74-b784-4765-98ca-bc6cf3b8adc4.png
```

### 4.1 当前页面判断

```yaml
page: 数据管理
mode: 示例模式
target_user: 第一次使用示例数据的小白用户
primary_task_should_be: 选择示例 EEG 数据，并进入数据准备
actual_primary_task_seen: 数据管理 / 运行分析 / 进入数据准备混杂
decision: revise
```

### 4.2 P1 问题

#### P1-DATA-01: 页面标题和步骤条冲突

看到的内容：

- 页面标题：`数据管理`。
- 左侧导航选中：`数据管理`。
- 步骤条高亮：`4 运行分析`。
- 右上摘要：`下一步 选择数据并进入准备`。

为什么严重：

同一屏出现三个不同阶段：

```text
数据管理
运行分析
选择数据并进入准备
```

新手无法判断当前该管理数据、准备数据，还是直接运行分析。

修复：

```text
步骤条：
创建项目 已完成
选择数据 当前
检查数据 下一步
运行分析 未开始
查看结果 未开始
生成报告 未开始
```

如果系统认为数据已准备，则数据页只显示右侧建议：

```text
此数据已准备，可直接进入分析任务。
[进入分析任务]
```

#### P1-DATA-02: 同一动作出现两次

看到的内容：

- 文件详情内有一个 `进入数据准备`。
- 底部又出现一个 `进入数据准备`。

风险：

用户会怀疑两个按钮是否含义不同。根据“一意图一主控”规则，这是 P1。

修复：

- 文件详情只保留一个主按钮。
- 只读说明 `示例数据只读，上传和编辑已收起` 放在按钮下方小字，不另起按钮行。

#### P1-DATA-03: 文件信息重复，占用大量垂直空间

重复项：

- 文件名在摘要卡、表格行、详情标题中重复。
- `fif · 8 通道 · 250 Hz` 在表格和详情中重复。
- 项目名在摘要卡和详情中重复。
- 准备记录在表格状态和详情中重复。

修复：

将详情区改成一行对象摘要：

```text
teaching_oddball_with_montage_raw.fif
FIF · 8 通道 · 250 Hz · 示例项目 · 准备记录第 1 版
[进入数据准备]
```

表格只保留列表选择，详情只保留下一步和少量关键元数据。

#### P1-DATA-04: 示例模式提示过长且离主任务太远

当前：

```text
示例模式 你正在使用内置脑电数据试跑流程，无需上传数据；示例数据不可删除，结果仅用于学习操作。
```

问题：

这段话有价值，但它压在全页顶部，像系统公告。用户当前真正需要的是“这个数据可以直接用，下一步去准备/分析”。

修复：

顶部提示缩短：

```text
示例模式：内置数据只读，可直接试跑流程。
```

更详细解释放入文件详情小字：

```text
示例数据不可编辑，不影响你的真实项目。
```

#### P1-DATA-05: 输入法悬浮条遮挡内容区域

截图中右侧有输入法悬浮条。它不是应用自身问题，但暴露出一个风险：页面当前没有为右侧悬浮控件留出稳定安全区，容易遮挡表格行右侧按钮。

修复：

- 右侧表格动作不要紧贴最右边。
- 文件行动作列保留至少 24 px 右侧安全距离。

### 4.3 P2 问题

| 问题 | 修复 |
| --- | --- |
| 摘要卡四格都很重，像 KPI dashboard | 改为一行 context strip |
| 文件详情卡过大，内容太稀 | 改为 compact detail panel |
| 表格选中态蓝边过重 | 只保留浅底 + 左边 2 px accent |
| 按钮图标视觉偏重 | 图标 14-15 px，按钮高度 34-36 px |
| 页面大量浅蓝边框让空间变碎 | 外层减边框，内部用分隔线 |

## 5. 逐页评审

### 5.1 项目管理页

证据：

```text
outputs/adversarial_all_pages_20260705/01-dashboard.png
```

```yaml
primary_task_should_be: 创建或打开项目
observed_title: 项目管理
primary_action: 创建项目
decision: revise
```

P1：

- 标题 `项目管理` 重复两次，不像“开始一次 EEG 分析”。
- 页面正文太空，只有一个小面板，1920/2048 下显得不像产品工作台。
- `进入数据管理` 在无项目状态下是次级路径，但当前与创建项目并列出现在首屏，容易提前跳转。

P2：

- 左侧底部“账号与服务”卡片视觉重量偏高，抢主流程。
- 侧边栏 QLanalyser 标志区域偏像内部系统，不够品牌化。

修复：

- 页面标题改为 `开始一次 EEG 分析`。
- 主按钮：无项目时只突出 `创建项目`。
- 次级：`打开已有项目` 或 `进入数据管理` 降权。
- 项目页补一个清晰的项目列表/空态，而不是大面积空白。

### 5.2 数据管理页（普通模式无项目）

证据：

```text
outputs/adversarial_all_pages_20260705/02-storage.png
```

P1：

- 无项目状态下仍可见 `选择 EEG 文件` 和 `上传到当前项目` 两个禁用按钮，视觉上增加错误期待。
- `打开项目` 被顶部摘要、右上按钮、空态按钮、详情说明多次重复。
- 右侧详情面板在无项目时价值低，占据过多空间。

修复：

- 无项目状态只显示一个空态：

```text
上传数据前，需要先创建或打开项目。
[去项目页]
```

- 隐藏上传按钮，不显示禁用上传控件。
- 右侧详情面板在无项目时收起。

### 5.3 数据准备页

证据：

```text
outputs/adversarial_all_pages_20260705/03-analysis.png
```

P1：

- 标题仍是 `数据准备`，但正文中出现 `当前上下文 / 波形预览与数据准备 / 等待选择 EEG 数据 / 当前预览窗未发现事件标记`，空态信息碎片化。
- 无数据状态下，事件标记提示过早出现。小白还没选数据，不应看到“未发现事件标记”。
- `创建或打开项目` 与 `去选择数据` 同屏出现，前置条件不够线性。

修复：

- 若无项目：只显示 `请先创建或打开项目`。
- 若有项目无数据：只显示 `请先选择 EEG 数据`。
- 未选择数据时隐藏波形控件、事件提示、预览空图。

### 5.4 分析任务页

证据：

```text
outputs/adversarial_all_pages_20260705/04-workflow.png
```

P1：

- DOM 显示 `primaryButtonCount=0`，没有明确主动作。
- 页面写 `当前可用：8 项分析方法`，但多数卡片灰掉或不可运行；这对新手是噪声。
- PSD 虽在“推荐运行”，但视觉权重并不够像唯一推荐主动作。
- 高级方法仍占据第一屏大量横向空间。

修复：

- 主区域只突出一张 PSD 推荐卡：

```text
推荐先运行
PSD 频谱分析
查看不同频段能量分布。
[运行 PSD]
```

- ERP 放到 `需要事件标记`，不可用时明确原因。
- TFR/PAC/Connectivity/ML 折叠到 `进阶方法`。
- 若准备方案未确认，主按钮改为 `去确认数据准备`。

### 5.5 结果查看页

证据：

```text
outputs/adversarial_all_pages_20260705/05-statistics.png
```

P1：

- 空态写了“请先完成数据准备，再开始 PSD 或 ERP 分析”，但没有主按钮。
- 结果页和报告页之间的关系只是文字说明，没有动作路径。
- `结果说明` 面板在无结果状态下显得像结论，容易误导。

修复：

无结果时：

```text
还没有分析结果
运行 PSD 后，这里会显示频谱图、频段功率表和参数记录。
[去运行 PSD]
```

如果缺准备方案：

```text
[去检查 EEG 数据]
```

### 5.6 报告交付页

证据：

```text
outputs/adversarial_all_pages_20260705/06-publication.png
```

P1：

- `生成交付报告` 在右上显示为禁用，同时空态里主按钮是 `去数据准备`，形成两个主动作。
- 页面叫 `报告交付`，对小白偏业务交付，不如 `生成和下载报告` 直接。
- `交付包内容` 在无结果时过早展示，占用空间但没有当前可操作价值。

修复：

- 无结果时隐藏右上 `生成交付报告`。
- 标题改为 `生成和下载报告`。
- `交付包内容` 折叠或移到报告就绪后展示。

### 5.7 质量检查页

证据：

```text
outputs/adversarial_all_pages_20260705/07-journey.png
```

观察：

- 自动点击 `journey` 后 activeView 仍为 `dashboard`，说明该入口当前在客户导航里被隐藏或重定向。

P1：

- 左侧导航没有质量检查，但设计文档中仍有该路由。信息架构不一致。
- 如果质量检查是客户功能，应在导航和路由一致；如果不是，应从客户设计合同中降级。

修复：

- V0.1 建议暂不放客户主导航。
- 报告页内用轻量 checklist 表达交付完整性。
- 质量检查作为管理员/内部验收页另设入口。

### 5.8 个人中心

证据：

```text
outputs/adversarial_all_pages_20260705/08-userCenter.png
```

P1：

- `充值`、`提交开票申请` 视觉权重过高，和当前“开发/试用工作台”主线冲突。
- 余额出现两个数值：`当前余额 ￥1000.00` 与充值输入 `￥16043.50`，容易被误解为真实财务状态。
- 个人中心内容太多，像账户后台，不像客户工作台的低频页。

修复：

- V0.1 试点阶段将充值/发票改为低调二级区域。
- 沙盒金额明显标注 `沙盒余额`。
- 主区优先显示账号、单位、权限、退出；财务折叠。

### 5.9 登录封面

本轮未重新截图登录封面，但前序设计合同已覆盖。仍需在实现前做实际截图复审。

必须评审：

- 全底图是否真实覆盖首屏。
- 品牌和产品名是否符合：

```text
全澜脑科学® | QuanLan BrainScience®
QLanalyser Online
```

- 登录模块是否极简。
- 默认测试账号是否不阻塞开发。
- 注册/账号开通是否没有长文案。
- 运营后台入口是否低调。

## 6. 设计维度评分

| 页面 | 视觉层级 | 一致性 | 可用性 | 品牌匹配 | 现代专业感 | 可读性 | 判定 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 项目管理 | 3 | 3 | 3 | 3 | 3 | 4 | revise |
| 数据管理-普通 | 3 | 2 | 3 | 3 | 3 | 4 | revise |
| 数据管理-示例 | 3 | 2 | 3 | 3 | 3 | 4 | revise |
| 数据准备 | 3 | 3 | 3 | 3 | 3 | 4 | revise |
| 分析任务 | 2 | 3 | 2 | 3 | 3 | 4 | revise |
| 结果查看 | 3 | 3 | 2 | 3 | 3 | 4 | revise |
| 报告交付 | 3 | 3 | 2 | 3 | 3 | 4 | revise |
| 个人中心 | 3 | 3 | 3 | 3 | 3 | 4 | revise |

目标通过线是 4。当前没有一个客户主页面达到“新手友好科研工作台”的 4 分线。

## 7. 修复优先级

### 第一批：必须先修

1. 全局步骤条语义：当前页、已完成、下一步建议分开。
2. 数据管理页：消除步骤冲突、按钮重复、文件信息重复。
3. 分析任务页：PSD 成为唯一推荐主动作，高级方法折叠。
4. 结果/报告空态：空态必须有一个主按钮。
5. 示例模式引导：结束引导后允许自由导航，且不要反复盖住页面。

### 第二批：体验升级

1. 页面标题从模块名改为任务名。
2. 重复标题删除。
3. 普通无项目状态隐藏无效上传控件。
4. 个人中心财务模块降权。
5. 侧边栏底部账户卡片降权或收起。

### 第三批：视觉 polish

1. 图标视觉尺寸统一 14-15 px。
2. 表格行高 34-38 px。
3. 卡片半径 6-8 px。
4. 减少蓝色边框密度。
5. 选中态从重边框改为浅底 + 左侧 accent。

## 8. 推荐整改后的数据管理页结构

### 示例模式且已有示例数据

```text
顶部：
上传或选择 EEG 数据
示例模式：内置数据只读，可直接试跑流程。

状态条：
体验中心示例项目 / teaching_oddball_with_montage_raw.fif / 已准备
下一步建议：进入分析任务

主区：
项目数据文件
  teaching_oddball_with_montage_raw.fif | FIF | 8 通道 | 250 Hz | 已准备

详情区：
teaching_oddball_with_montage_raw.fif
FIF · 8 通道 · 250 Hz · 准备记录第 1 版
示例数据只读，不影响真实项目。
[进入分析任务]
```

如果用户在数据页想复查准备：

```text
次级链接：查看数据准备
```

不要再出现两个 `进入数据准备`。

### 普通模式无项目

```text
上传或选择 EEG 数据

上传数据前，需要先创建或打开项目。
[去项目页]
```

隐藏：

- 文件表格。
- 文件详情。
- 上传按钮。
- 禁用上传按钮。

## 9. 验收要求

整改后必须重新截图：

```text
outputs/adversarial_fix_review_20260705/dashboard_2048.png
outputs/adversarial_fix_review_20260705/storage_normal_no_project_2048.png
outputs/adversarial_fix_review_20260705/storage_teaching_with_data_2048.png
outputs/adversarial_fix_review_20260705/analysis_no_data_2048.png
outputs/adversarial_fix_review_20260705/workflow_ready_2048.png
outputs/adversarial_fix_review_20260705/statistics_empty_2048.png
outputs/adversarial_fix_review_20260705/publication_empty_2048.png
outputs/adversarial_fix_review_20260705/user_center_2048.png
```

并检查：

- 每页 `primaryButtonCount <= 1`，特殊情况必须解释。
- 当前页标题和步骤条不冲突。
- 空态必须有一个明确主动作。
- 示例模式引导关闭后可以自由导航。
- 1366、1536、1920、2048 无水平溢出。
- 客户默认 UI 不出现 `manifest / runner / schema / artifact count / gate / acceptance`。

## 10. 最终判定

当前 UI 可以操作，但还不是“让小白开始 EEG 分析”的产品级工作台。

最应该先修的不是颜色和图标，而是：

```text
一个页面，一个当前状态，一个主动作，一个下一步。
```

你指出的数据管理页正好击中了这个核心问题：它同时显示“数据管理”“运行分析”“选择数据并进入准备”。如果不先修这个状态真相，继续压缩图标或调整留白，只会让一个混乱的页面变得更紧凑。

