# QLanalyser 系统全页面对抗性视觉逻辑评审

Date: 2026-07-05  
Status: review, not implementation  
Scope: QLanalyser Online 登录封面、客户工作台、隐藏/重定向路由、示例/教学模式、运营后台、独立方法实验室、EDF 波形审阅器。  
Reviewer: Codex UI/Product review lane  
Supersedes: `docs/product/qlanalyser_all_pages_adversarial_visual_review_20260705.md` 的局部逐页评审范围。

## 0. 总结论

本轮不把“左侧导航能看到的 7 个页面”当作全系统范围，而是按静态页面、运行时可达页面和截图状态组合一起审查。

结论：

```yaml
overall_decision: revise
confirmed_p0: 0
unresolved_p1: 18
unresolved_p2: 24
evidence_status: partial
highest_risk: route_state_primary_action_inconsistency
first_fix_target: page_route_contract + workflow_stepper_truth + state_specific_empty_pages
```

当前系统视觉上没有发现 2048 宽度横向溢出，也没有在已截图画面中看到明显临床诊断过度承诺。但是，作为“让小白开始 EEG 分析”的产品级工作台，它仍未通过：

1. 部分页面请求后没有真实打开目标页。
2. 示例/教学模式会接管或遮蔽导航。
3. 后台截图没有进入后台，而是停留在客户项目页和示例引导。
4. 多个页面的当前路由、步骤条、空态、主按钮和下一步建议不一致。
5. 分析方法和独立实验室把高级/实验能力放得太像稳定主路径。

这不是单纯的美术问题。根因是：

```text
系统缺少一份运行时页面契约：当前页面、当前业务状态、当前模式、主动作、下一步、可达性必须形成唯一真相。
```

## 1. Review Brief

```yaml
goal:
  对 QLanalyser 系统所有页面和状态进行对抗性视觉逻辑评审，补齐此前漏掉的页面。
target_user:
  EEG 研究人员、实验室成员、CRO 分析人员、第一次用示例数据试跑流程的小白用户、运营后台人员。
hard_rules:
  - QLanalyser 是非医疗科研支持工具，不暗示诊断、治疗或临床决策。
  - 客户可见页面必须 5 秒内知道当前任务、当前数据和下一步。
  - 一个决策区只能有一个主按钮。
  - 空态、加载、错误、禁用、成功状态必须有原因和恢复动作。
  - 示例模式和普通模式、客户界面和后台界面必须明确隔离。
  - 不能只审理想截图；不可达页面必须标为 blocked 或 needs_recapture。
taste_rules:
  - calm, scientific, traceable, trustworthy, data-first.
  - 开阔不等于稀薄；主科学对象和主任务应占主要视觉预算。
  - 控件轻量、图标克制、运营和财务信息不抢客户主流程。
evidence_inspected:
  - `outputs/system_all_pages_adversarial_20260705/system_all_pages_snapshot_report.json`
  - `outputs/system_all_pages_adversarial_20260705/*.png`
  - `frontend/index.html`
  - `frontend/app.js`
  - `frontend/standalone-lab.html`
  - `frontend/lab-edf-reviewer.html`
unknowns:
  - 后台四页真实视觉未被当前截图批次捕获。
  - 教学模式关闭引导后的自由导航需重新用干净会话验证。
  - 本轮未触发上传、分析任务、报告生成的真实 loading/error/success 状态。
```

## 2. 采用规范

本轮读取并采用：

| 来源 | 采用规则 |
| --- | --- |
| `AGENTS.md` | 品牌、产品定位、V0.1 试点边界、核心工作流、暂不做范围 |
| `DESIGN.md` | 研究支持产品边界、控件可用性、状态显式、算法工作流契约 |
| `docs/product/qlanalyser_beginner_analysis_flow_ui_redesign_20260705.md` | 新手主流程、页面任务语言、登录封面、1920 工作区目标 |
| `docs/product/qlanalyser_ui_interaction_visual_governance_master_20260628.md` | 一意图一主控、页面原型、状态反馈、禁用原因、客户禁用词 |
| `docs/product/qlanalyser_project_design_system_20260628.md` | 专业 EEG 工作台、页面职责、主科学对象优先 |
| `docs/product/qlanalyser_research_user_copy_governance_spec_20260701.md` | 科研用户文案、示例模式术语、结果/报告边界 |
| `docs/product/qlanalyser_user_level_e2e_adversarial_review_standard_20260702.md` | 用户级 E2E 页面覆盖和证据要求 |
| `docs/product/page_interaction_inventory.md` | 页面职责、默认展开、状态标签、视觉噪声 |
| `docs/quality/visual_layout_design_spec.md` | 1920 目标、1366 最小安全、缩放策略、截图证据 |
| `D:\QuanLanKnowledgeBase\learning-notes\design\B2B_SCIENTIFIC_DASHBOARD_SCREENSHOT_AUDIT_CHECKLIST_CN.md` | B 端科研 dashboard 截图审查 |
| `D:\QuanLanKnowledgeBase\learning-notes\design\UX_STATE_FEEDBACK_EMPTY_ERROR_LOADING_MOTION_GATE_CN.md` | Empty/Loading/Error/Disabled/Success 状态 |
| `D:\QuanLanKnowledgeBase\learning-notes\design\QUANLAN_DESIGN_PRINCIPLES_V1_CN.md` | 极致清晰、极致有用、专业可信、可解释、可执行 |
| `D:\QuanLanKnowledgeBase\learning-notes\design\QLANALYSER_DASHBOARD_DESIGN_SYSTEM_FIT_MATRIX_CN.md` | 页面参考系统选择、状态完整、科学边界 |

## 3. 页面范围核对

### 3.1 静态 view section

`frontend/index.html` 中存在 15 个主 view：

```text
dashboard
journey
analysis
workflow
epilepsyWorkbenchInline
paradigms
statistics
publication
upload
storage
userCenter
adminDashboard
adminOperations
adminFinance
adminSystem
```

另有 2 个独立页面：

```text
standalone-lab.html
lab-edf-reviewer.html
```

### 3.2 截图证据批次

证据目录：

```text
outputs/system_all_pages_adversarial_20260705
```

截图批次：

```yaml
viewport: 2048 x 1152
total_pages_or_states: 32
console_errors: 0
horizontal_overflow_detected: false
```

### 3.3 页面/状态覆盖表

| 截图状态 | 类型 | 请求页面 | 实际页面 | 结论 |
| --- | --- | --- | --- | --- |
| `00-login-customer.png` | 登录 | customerLogin | dashboard hidden in DOM | 登录视觉可审；DOM/capture 混入 app 内容，需复核可访问性 |
| `01-login-account-open.png` | 登录 | register | dashboard hidden in DOM | 账号开通状态未单独形成干净页面 |
| `02-login-admin.png` | 登录 | adminLogin | dashboard hidden in DOM | 后台登录视觉可审；后台进入链路需另测 |
| `customer-dashboard.png` | 客户 | dashboard | dashboard | 可审 |
| `customer-storage.png` | 客户 | storage | storage | 可审 |
| `customer-analysis.png` | 客户 | analysis | analysis | 可审 |
| `customer-workflow.png` | 客户 | workflow | workflow | 可审 |
| `customer-statistics.png` | 客户 | statistics | statistics | 可审 |
| `customer-publication.png` | 客户 | publication | publication | 可审 |
| `customer-userCenter.png` | 客户 | userCenter | userCenter | 可审 |
| `customer-epilepsyWorkbenchInline.png` | 客户 | epilepsyWorkbenchInline | epilepsyWorkbenchInline | 可审 |
| `customer-route-journey.png` | 客户隐藏路由 | journey | dashboard | 重定向/隐藏，需契约化 |
| `customer-route-upload.png` | 客户隐藏路由 | upload | storage | 别名/重定向，需契约化 |
| `customer-route-paradigms.png` | 客户隐藏路由 | paradigms | dashboard | 重定向/隐藏，需契约化 |
| `forced-journey.png` | 强制隐藏 section | journey | no activeView | 只审静态片段，不代表真实可达 |
| `forced-upload.png` | 强制隐藏 section | upload | no activeView | 只审静态片段，不代表真实可达 |
| `forced-paradigms.png` | 强制隐藏 section | paradigms | no activeView | 只审静态片段，不代表真实可达 |
| `teaching-guide-dashboard.png` | 教学 | dashboard | dashboard | 可审引导层 |
| `teaching-dashboard.png` | 教学 | dashboard | dashboard | 可审引导层 |
| `teaching-storage.png` | 教学 | storage | dashboard | 未进入目标页 |
| `teaching-analysis.png` | 教学 | analysis | dashboard | 未进入目标页 |
| `teaching-workflow.png` | 教学 | workflow | dashboard | 未进入目标页 |
| `teaching-statistics.png` | 教学 | statistics | dashboard | 未进入目标页 |
| `teaching-publication.png` | 教学 | publication | dashboard | 未进入目标页 |
| `teaching-userCenter.png` | 教学 | userCenter | dashboard | 未进入目标页 |
| `admin-adminDashboard.png` | 后台 | adminDashboard | dashboard | 未进入后台 |
| `admin-adminOperations.png` | 后台 | adminOperations | dashboard | 未进入后台 |
| `admin-adminFinance.png` | 后台 | adminFinance | dashboard | 未进入后台 |
| `admin-adminSystem.png` | 后台 | adminSystem | dashboard | 未进入后台 |
| `admin-journey.png` | 后台 | journey | dashboard | 未进入后台/质量页 |
| `standalone-standalone-lab.png` | 独立工具 | standalone-lab.html | standalone | 可审 |
| `standalone-lab-edf-reviewer.png` | 独立工具 | lab-edf-reviewer.html | standalone | 可审 |

### 3.4 证据限制

本轮截图可以支持客户主工作台、登录封面、独立工具、部分隐藏路由的审查；不能支持“后台页面已经通过视觉验收”或“教学模式所有页面都能自由访问”的结论。

因此本轮对后台和教学模式给出的是：

```yaml
decision: needs_clean_recapture
reason:
  requested_view_did_not_match_active_view
```

## 4. 全局 P1 问题

### P1-SYS-01: 页面请求与实际页面不一致

证据：

- `teaching-storage` 请求 `storage`，实际仍是 `dashboard`。
- `teaching-analysis` 请求 `analysis`，实际仍是 `dashboard`。
- `admin-adminDashboard` 请求 `adminDashboard`，实际仍是 `dashboard`。
- `customer-route-journey` 请求 `journey`，实际回到 `dashboard`。
- `customer-route-upload` 请求 `upload`，实际为 `storage`。

风险：

用户、QA 和后续模型都会以为“已经审过该页面”，但实际审到的是另一页。上一轮漏掉数据管理页就是这个类型的失败。

修复：

1. 建立 `PAGE_ROUTE_CONTRACT`：

```yaml
route:
  public_hash:
  view_id:
  visible_in_customer_nav:
  visible_in_admin_nav:
  alias_of:
  redirect_to:
  required_role:
  required_mode:
  capture_required:
```

2. 截图脚本必须断言：

```text
requestedView === activeView
```

除非该页面在契约中显式声明为 alias 或 redirect。

3. 文档、测试、视觉评审都按契约命名截图，不能只按文件名假定页面。

### P1-SYS-02: 步骤条、页面标题、状态和下一步没有唯一真相

证据：

- 数据页无项目时步骤条仍展示完整流程，页面状态是“未打开项目”，下一步是“打开项目”。
- 分析任务页步骤条高亮 `运行分析`，但页面提示需要返回数据准备。
- 报告页步骤条高亮 `生成报告`，但主卡片提示去数据准备。
- 用户此前截图中，数据管理页同时出现“数据管理 / 运行分析 / 选择数据并进入准备”。

风险：

新手不知道自己在第几步，也不知道当前动作是否有效。

修复：

步骤条只表达主流程进度，不要同时表达“当前页”和“推荐下一步”。建议分成：

```text
当前页面：上传或选择 EEG 数据
流程状态：项目已创建 / 数据待选择 / 准备未确认 / 分析未运行 / 报告未生成
下一步建议：去项目页 / 上传 EEG / 检查数据 / 运行 PSD / 生成报告
```

### P1-SYS-03: 主按钮数量不稳定

DOM 证据：

| 页面 | primaryButtonCount | 问题 |
| --- | ---: | --- |
| `customer-storage` | 2 | 无项目状态仍有上传/空态主动作竞争 |
| `customer-workflow` | 0 | 没有明确可运行主动作 |
| `customer-statistics` | 0 | 结果空态没有主动作 |
| `customer-publication` | 2 | 禁用生成报告与去数据准备同时抢权重 |
| `customer-userCenter` | 2 | 充值和开票两个强主按钮 |
| `teaching-*` | 2 | 引导层按钮与页面动作混合 |
| `admin-*` | 2 | 实际是教学 dashboard，不是后台页 |

修复：

- 每个页面状态最多一个主动作。
- 不可用动作不应保持主按钮视觉权重。
- 如果页面缺前置条件，主按钮是恢复动作，不是目标动作。

### P1-SYS-04: 空态不是“状态页面”，而是把禁用工作台留在屏幕上

证据：

- 数据准备页未选数据时仍显示大波形坐标、通道、事件提示。
- 数据管理页无项目时仍显示上传按钮和详情面板。
- 癫痫样事件分析台无数据时下方出现多条空白骨架和边框。
- EDF 审阅器空态只有选择文件按钮和空条，没有说明文件后会出现什么。

修复：

空态必须收起不可操作工作台，只保留：

```yaml
title:
reason:
what_will_appear_after_next_step:
primary_action:
secondary_action_optional:
```

### P1-SYS-05: 分析方法层级仍像模块清单

证据：

- `customer-workflow.png` 第一屏展示 8 项方法，并把高级方法分组但仍占大量空间。
- `standalone-lab.html` 把 PSD、ERP、TFR、PAC、Connectivity、CSD 等方法长列表平铺。
- 稳定、Beta、V2 标签存在，但不能形成清楚的新手路径。

风险：

用户会把 PAC、Connectivity、CSD 等进阶或条件方法理解为和 PSD 一样稳定、一样适合作为第一步。

修复：

- 主工作台只突出 PSD 推荐。
- ERP 条件显示，缺事件时禁用并说明原因。
- TFR/PAC/Connectivity/CSD/ML 进入“进阶分析”折叠区或独立方法实验室。
- 独立实验室明确标识为“方法实验室/演示工具”，不承担新手主流程。

### P1-SYS-06: 示例/教学模式遮蔽真实页面

证据：

- 教学模式请求多个页面时实际停留在 `dashboard`。
- admin 视觉捕获也被示例引导覆盖。
- 截图中引导层包含 `上一步 / 下一步 / 结束引导`，背景页面变暗且不可独立审查。

风险：

示例模式变成“强制演示”，用户无法自由探索页面，也无法完成全页面验收。

修复：

- 引导层只负责首次教学，不应改写路由真相。
- `结束引导` 后必须持久记录并允许自由导航。
- 点击左侧导航时应询问是否退出引导，不能静默拉回 dashboard。
- E2E 必须分别截图：
  - teaching guide active
  - teaching sandbox dashboard
  - teaching sandbox storage
  - teaching sandbox analysis
  - teaching sandbox workflow
  - teaching sandbox results
  - teaching sandbox report

### P1-SYS-07: 后台视觉验收被客户/示例状态污染

证据：

- `admin-adminDashboard.png` 画面实际为项目管理页，右侧有示例模式引导卡。
- `admin-adminOperations`、`admin-adminFinance`、`admin-adminSystem` 报告同样实际为 `dashboard`。

风险：

当前不能证明后台四页视觉和逻辑可用。用户级 E2E 标准要求后台截图，当前证据不足。

修复：

- 后台登录使用干净 browser context。
- 进入后台后关闭教学状态、清除 customer demo 参数。
- 后台导航只显示后台页，不显示客户侧示例引导。
- 后台四页必须重新截图并单独评审。

### P1-SYS-08: 客户主流程被账户/财务信息持续抢权重

证据：

- 左侧底部账户卡片长期显示 `账号与服务`、余额、充值、发票、权限等。
- 个人中心 `充值` 和 `提交开票申请` 都是强主按钮。
- 沙盒余额和开票金额看起来像真实资金状态。

风险：

V0.1 试点阶段财务不应压过 EEG 分析主流程；否则会降低科研工作台的可信度。

修复：

- 左侧底部只显示 `个人中心` 和当前账号。
- 财务区降为个人中心二级服务。
- 所有非真实财务状态明确标 `沙盒余额 / 本地审核 / 试点演示`。

## 5. 页面级评审

### 5.1 登录封面：客户登录

证据：

```text
outputs/system_all_pages_adversarial_20260705/00-login-customer.png
```

判定：

```yaml
decision: revise
severity: P1/P2
```

已改进点：

- 全屏底图成立。
- 品牌显示为 `全澜脑科学® | QuanLan BrainScience®`，英文未全大写。
- `QLanalyser Online` 是第一视觉。
- 右上运营入口低调。
- 默认测试账号已填入，开发不被登录阻塞。

P1：

- 登录状态的 DOM/capture 中仍混入 `项目管理` 等登录后内容。视觉上被隐藏，但需要确认 `hidden/inert/aria-hidden` 对可访问树和自动化抓取是否一致。
- `项目入口` 更像内部系统入口，不如 `登录` 或 `进入 QLanalyser` 直接。

P2：

- 右侧登录框灰卡较重，和全底图的轻盈感冲突。
- 左侧关键词较好，但下面价值卡在当前截图中被隐藏或弱化，信息取舍可以更极简。

修复：

- 登录时 app shell 使用 `inert` 和 `aria-hidden="true"`，并在截图脚本中只读取可见/可访问文本。
- 登录模块标题改为 `登录`，产品名已在卡片顶端显示即可。
- 登录框透明度和边框再收轻，保持可读但不显笨重。

### 5.2 登录封面：账号开通

证据：

```text
outputs/system_all_pages_adversarial_20260705/01-login-account-open.png
```

判定：

```yaml
decision: revise
severity: P1
```

P1：

- 截图批次没有明确证明账号开通面板已切换成功；报告中按钮仍为登录/找回账号。
- `账号开通` tab 是 disabled，但设计目标是“极简账号开通逻辑”。disabled tab 容易让用户以为坏了。

修复：

- 如果不开放自助注册，账号开通不要做 disabled tab；改为登录框下方弱链接或说明：

```text
账号开通：请联系运营人员。
```

- 单独截图 `account_open_state`，验证没有注册长表单、没有创建账号主按钮。

### 5.3 登录封面：管理员登录

证据：

```text
outputs/system_all_pages_adversarial_20260705/02-login-admin.png
```

判定：

```yaml
decision: needs_recapture
severity: P1
```

P1：

- 当前截图可以看到运营入口按钮，但不能证明管理员登录后进入后台。
- 后续 admin 捕获全部停在 dashboard，说明后台登录/路由/教学状态存在干扰。

修复：

- 管理员入口保持右上角低调。
- 点击后只显示管理员邮箱、密码、进入后台，后台说明一行即可。
- 用独立会话重测 admin login -> adminDashboard。

### 5.4 项目管理页

证据：

```text
outputs/system_all_pages_adversarial_20260705/customer-dashboard.png
```

判定：

```yaml
decision: revise
severity: P1
```

P1：

- 页面过薄，2048 宽下只有一条横向面板，像未完成页面。
- 标题 `项目管理` 与面板 `项目管理` 重复，任务语言弱。
- `创建项目` 和 `进入数据管理` 同时为高权重按钮；无项目状态下不应鼓励直接去数据管理。

P2：

- 左下账户卡片视觉重量过高。
- 品牌区 `脑电科研数据分析` 可接受，但当前页面第一任务不够品牌化。

修复：

- 页面标题改为 `开始一次 EEG 分析`。
- 无项目：主按钮只保留 `创建项目`。
- 有项目：主按钮切换为 `进入数据管理`。
- 首屏应有项目列表/空态/当前项目详情，不留大面积空白。

### 5.5 数据管理页

证据：

```text
outputs/system_all_pages_adversarial_20260705/customer-storage.png
```

判定：

```yaml
decision: revise
severity: P1
```

P1：

- 无项目时仍显示上传按钮和详情面板，用户先看到的是不可操作控件。
- `primaryButtonCount=2`，违反一决策区一主控。
- 顶部摘要四格与空态重复表达“未打开项目/待选择项目/未选择数据/打开项目”。

P2：

- 文件详情面板无项目时价值很低，占据右侧空间。
- 页面宽但内容被细碎边框切开。

修复：

无项目时只显示：

```text
上传或选择 EEG 数据
上传数据前，需要先创建或打开项目。
[去项目页]
```

隐藏：

- 上传按钮。
- 文件列表。
- 文件详情。
- 禁用按钮。

有项目无数据时才显示上传入口。

### 5.6 数据准备页

证据：

```text
outputs/system_all_pages_adversarial_20260705/customer-analysis.png
```

判定：

```yaml
decision: revise
severity: P1
```

P1：

- 未选择数据时仍显示波形坐标、通道、事件标记提示，像加载失败或假数据。
- 左侧上下文、顶部步骤卡、正文提示都在重复“先选数据”，但主路径仍不够线性。
- `当前预览窗未发现事件标记` 在未选数据时出现过早，容易误导。

P2：

- 波形大区域视觉很开阔，但空态阶段不是主科学对象，应该让位给明确下一步。

修复：

- 无项目：只显示去项目页。
- 有项目无数据：只显示去数据页选择/上传。
- 有数据加载中：显示 skeleton + 明确加载内容。
- 有数据后才显示波形、事件、预处理控件。

### 5.7 分析任务页

证据：

```text
outputs/system_all_pages_adversarial_20260705/customer-workflow.png
```

判定：

```yaml
decision: revise
severity: P1
```

P1：

- `primaryButtonCount=0`，没有明确“现在能做什么”。
- `当前可用：8 项分析方法` 与下方灰化卡片冲突：看起来可用，实际不可运行。
- PSD 虽在推荐组，但视觉权重不足，不像新手首步。
- 高级方法卡片占据第一屏，削弱任务焦点。

修复：

缺准备方案时：

```text
还不能运行分析
请先检查并确认 EEG 数据准备方案。
[去检查 EEG 数据]
```

准备完成时：

```text
推荐先运行
PSD 频谱分析
查看不同频段的能量分布。
[运行 PSD]
```

ERP 放条件区；TFR/PAC/Connectivity/CSD 折叠为进阶方法。

### 5.8 结果查看页

证据：

```text
outputs/system_all_pages_adversarial_20260705/customer-statistics.png
```

判定：

```yaml
decision: revise
severity: P1
```

P1：

- `primaryButtonCount=0`，空态没有主动作。
- 空态文案说先完成数据准备再开始 PSD/ERP，但没有按钮闭环。
- 结果说明在无结果时容易像结论区。

修复：

无结果且未准备：

```text
还没有分析结果
请先检查 EEG 数据，然后运行 PSD。
[去检查 EEG 数据]
```

无结果且已准备：

```text
还没有分析结果
运行 PSD 后，这里会显示频谱图、频段功率表和参数记录。
[去运行 PSD]
```

### 5.9 报告交付页

证据：

```text
outputs/system_all_pages_adversarial_20260705/customer-publication.png
```

判定：

```yaml
decision: revise
severity: P1
```

P1：

- 步骤条显示第 6 步，空态却要求回数据准备。
- 右上禁用 `生成交付报告` 与空态 `去数据准备` 两个信号竞争。
- 页面名 `报告交付` 对小白偏业务化，不如 `生成和下载报告`。

P2：

- `交付包内容` 在无结果时过早展示，占空间但无法行动。

修复：

- 无结果：隐藏生成报告按钮，主按钮按状态指向 `去运行分析` 或 `去检查 EEG 数据`。
- 有结果无报告：主按钮 `生成报告`。
- 报告就绪：主按钮 `下载报告包`。
- 标题改为 `生成和下载报告`。

### 5.10 个人中心

证据：

```text
outputs/system_all_pages_adversarial_20260705/customer-userCenter.png
```

判定：

```yaml
decision: revise
severity: P1/P2
```

P1：

- `充值` 和 `提交开票申请` 都是强主按钮，个人中心变成财务后台。
- `￥16043.50`、`￥1000.00`、`5.00` 等金额没有足够强的沙盒标识。
- V0.1 试点边界暂不做真实在线支付，视觉上不应表现为正式资金闭环。

P2：

- 左右两栏信息密度较均衡，但账户/财务服务在客户工作台中仍过重。

修复：

- 主区优先：账号、单位、权限、退出、帮助。
- 财务服务折叠为 `沙盒财务服务`。
- 充值/发票按钮降权，不使用强主按钮。

### 5.11 癫痫样事件分析台

证据：

```text
outputs/system_all_pages_adversarial_20260705/customer-epilepsyWorkbenchInline.png
```

判定：

```yaml
decision: revise
severity: P1/P2
```

P1：

- 页面标题是 `癫痫样事件分析台`，左侧导航仍选中 `分析任务`，页面身份不够独立。
- 无数据空态下方留有多条空白骨架和边框，像加载失败。
- 空态按钮 `去数据管理` 和 `返回分析任务` 都可见，主路径略分叉。

P2：

- 癫痫样事件分析台作为高风险解释界面，空态应更明确“候选事件初筛/人工复核/非诊断”边界。

修复：

- 当进入该工作台时，左侧导航可保持分析任务，但顶部需显示清楚的子页 breadcrumb：

```text
分析任务 / 癫痫样事件分析台
```

- 无数据时隐藏下方空骨架，只显示一张空态。
- 主按钮只保留 `去选择 EDF/EEG 数据`；返回分析任务做文本链接。

### 5.12 隐藏/重定向路由：journey

证据：

```text
outputs/system_all_pages_adversarial_20260705/customer-route-journey.png
outputs/system_all_pages_adversarial_20260705/forced-journey.png
frontend/index.html#journey
```

判定：

```yaml
decision: contract_required
severity: P1
```

P1：

- 静态存在 `journey`，客户请求时实际跳回 dashboard。
- 代码后段又将 `journey` 导航对 customer 隐藏，仅 admin 可见。
- 设计文档中它曾被称为质量检查/交付完整性，但运行时职责不稳定。

修复：

- V0.1 建议：客户主导航不显示 `journey`。
- 报告页内用轻量 checklist 表达交付完整性。
- 如果作为内部质量页，只允许后台角色访问，并在后台导航中命名为 `质量检查`。

### 5.13 隐藏/重定向路由：upload

证据：

```text
outputs/system_all_pages_adversarial_20260705/customer-route-upload.png
outputs/system_all_pages_adversarial_20260705/forced-upload.png
frontend/index.html#upload
```

判定：

```yaml
decision: contract_required
severity: P2
```

P2：

- 静态 `upload` 页面是上传吞吐估算工具，不是 EEG 文件上传主页面。
- 客户请求 `upload` 实际进入 `storage`，说明它已是旧功能或别名。

修复：

- 明确 `upload -> storage` 为 alias，并从文档中移除 standalone upload 页面职责。
- 如果保留吞吐估算，应归入后台/帮助，不作为主客户路由。

### 5.14 隐藏/重定向路由：paradigms

证据：

```text
outputs/system_all_pages_adversarial_20260705/customer-route-paradigms.png
outputs/system_all_pages_adversarial_20260705/forced-paradigms.png
frontend/index.html#paradigms
```

判定：

```yaml
decision: contract_required
severity: P2
```

P2：

- 静态页面展示 20 个常见范式，属于学习/方法推荐功能。
- 客户请求实际回 dashboard，说明它不是当前主流程。

修复：

- 短期从客户默认页面契约中移除。
- 长期放到知识库或方法帮助，不与“选择分析方法”主流程并列。

### 5.15 教学/示例模式

证据：

```text
outputs/system_all_pages_adversarial_20260705/teaching-guide-dashboard.png
outputs/system_all_pages_adversarial_20260705/teaching-storage.png
outputs/system_all_pages_adversarial_20260705/teaching-analysis.png
outputs/system_all_pages_adversarial_20260705/teaching-workflow.png
outputs/system_all_pages_adversarial_20260705/teaching-statistics.png
outputs/system_all_pages_adversarial_20260705/teaching-publication.png
outputs/system_all_pages_adversarial_20260705/teaching-userCenter.png
```

判定：

```yaml
decision: needs_clean_recapture
severity: P1
```

P1：

- 除 dashboard 外，请求页面全部实际停留在 dashboard。
- 引导层遮蔽页面，不能证明示例模式下各页面可用。
- 示例模式入口按钮和引导卡都在顶层强显示，会影响后台/客户页面验收。

修复：

- 示例模式分两层：
  - `guide_active`: 有遮罩和教学卡。
  - `sandbox_active`: 无遮罩，可自由导航，数据受保护。
- 关闭引导后必须进入 sandbox，而不是普通空页面。
- 所有页面重截：

```text
teaching-storage-after-guide.png
teaching-analysis-after-guide.png
teaching-workflow-after-guide.png
teaching-statistics-after-guide.png
teaching-publication-after-guide.png
```

### 5.16 运营后台：后台总览

证据：

```text
outputs/system_all_pages_adversarial_20260705/admin-adminDashboard.png
frontend/index.html#adminDashboard
```

判定：

```yaml
decision: needs_clean_recapture
severity: P1
```

P1：

- 截图实际是项目管理页 + 示例引导，不是后台总览。
- 静态代码中的后台总览包含今日项目、待处理任务、扣费、结果通知、成功率、客户数据量等，但未被实际视觉验证。

修复：

- 干净后台会话重截。
- 后台总览要聚焦异常任务、客户状态、存储与系统健康；演示财务数字标明沙盒。

### 5.17 运营后台：任务运营

证据：

```text
outputs/system_all_pages_adversarial_20260705/admin-adminOperations.png
frontend/index.html#adminOperations
```

判定：

```yaml
decision: needs_clean_recapture
severity: P1
```

P1：

- 当前截图未进入任务运营页。
- 静态任务表存在 `ERP-P300-2401`、`REST-PSD-2398` 等行，但无法确认筛选、错误态、操作可用性。

修复：

- 重截真实后台任务页。
- 任务表至少要显示：任务 ID、客户、方法、状态、失败原因/操作、时间。
- 危险或复现记录下载需有权限边界。

### 5.18 运营后台：财务管理

证据：

```text
outputs/system_all_pages_adversarial_20260705/admin-adminFinance.png
frontend/index.html#adminFinance
```

判定：

```yaml
decision: needs_clean_recapture
severity: P1
```

P1：

- 当前截图未进入财务管理页。
- V0.1 暂不做真实在线支付闭环，财务页面必须标明演示/沙盒边界。

修复：

- 重截真实后台财务页。
- 金额、订单、开票状态必须有真实/沙盒标识。
- 客户侧不要把同样财务控件做成主流程。

### 5.19 运营后台：系统状态

证据：

```text
outputs/system_all_pages_adversarial_20260705/admin-adminSystem.png
frontend/index.html#adminSystem
```

判定：

```yaml
decision: needs_clean_recapture
severity: P1
```

P1：

- 当前截图未进入系统状态页。
- 系统状态作为后台页应支持故障恢复，而不只是健康数字。

修复：

- 重截真实后台系统页。
- 必须覆盖：服务状态、队列、存储、上传、报告导出、错误/降级信息、最近异常。

### 5.20 独立方法实验室

证据：

```text
outputs/system_all_pages_adversarial_20260705/standalone-standalone-lab.png
frontend/standalone-lab.html
```

判定：

```yaml
decision: revise
severity: P1/P2
```

P1：

- 页面标题 `在线脑电分析实验室` 和主工作台定位容易混淆：用户可能以为这里也是 QLanalyser 主流程。
- 多个方法卡同权重，稳定/BETA/V2 标签不足以建立“建议先跑 PSD”的路径。
- PAC、Connectivity、CSD 等进阶方法有边界文案，但位置仍像可直接批量运行。

P2：

- 2048 宽下内容被约束在中间窄列，页面很长，空间利用不符合工作台目标。
- 标题和方法卡里使用图标/emoji，和主产品克制风格不完全一致。

修复：

- 页面定位改为：

```text
方法实验室
用于方法验证和演示，不替代主工作台分析流程。
```

- 首屏只显示数据来源 + 推荐 PSD + ERP 条件卡。
- 进阶方法折叠。
- 与主工作台风格统一，减少 emoji 依赖。

### 5.21 EDF 波形审阅器

证据：

```text
outputs/system_all_pages_adversarial_20260705/standalone-lab-edf-reviewer.png
frontend/lab-edf-reviewer.html
```

判定：

```yaml
decision: revise
severity: P2
```

P2：

- 首屏足够简洁，但空态没有说明选择文件后将出现波形、多通道浏览、滤波、时间窗、SVG 导出等工具。
- 大面积上传框下方有一条空白灰条，像未加载或残缺组件。
- 非医疗边界黄色提示过重，占据首屏注意力。

修复：

- 空态改为：

```text
选择 EDF 文件后，可以浏览多通道 EEG/ACC 波形、调整滤波与时间窗，并导出 SVG 快照。
[选择 EDF 文件]
```

- 黄色边界提示收短，放在标题下或上传框下方一行。
- 空白灰条删除或改成明确的文件状态条。

## 6. 视觉评分

评分按 1-5；客户 beta 通过线为 4。

| 页面/状态 | 视觉层级 | 一致性 | 可用性 | 品牌匹配 | 现代专业感 | 可读性 | 判定 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 登录封面 | 4 | 3 | 4 | 4 | 4 | 4 | revise |
| 项目管理 | 2 | 3 | 3 | 3 | 3 | 4 | revise |
| 数据管理 | 3 | 2 | 2 | 3 | 3 | 4 | revise |
| 数据准备 | 3 | 2 | 2 | 3 | 3 | 4 | revise |
| 分析任务 | 2 | 3 | 2 | 3 | 3 | 4 | revise |
| 结果查看 | 3 | 3 | 2 | 3 | 3 | 4 | revise |
| 报告交付 | 3 | 2 | 2 | 3 | 3 | 4 | revise |
| 个人中心 | 3 | 3 | 3 | 3 | 3 | 4 | revise |
| 癫痫样事件分析台 | 3 | 2 | 3 | 3 | 3 | 4 | revise |
| 教学模式 | 3 | 1 | 2 | 3 | 3 | 4 | needs_recapture |
| 运营后台 | unknown | 1 | unknown | unknown | unknown | unknown | needs_recapture |
| 独立方法实验室 | 2 | 2 | 3 | 2 | 2 | 4 | revise |
| EDF 审阅器 | 3 | 3 | 3 | 3 | 3 | 4 | revise |

## 7. 优先修复计划

### Phase 1: 页面契约和截图验收先修

目标：

- 每个路由知道自己是真实页、alias、redirect、hidden section、admin-only 还是 standalone。
- 截图脚本强制校验 requestedView 与 activeView。

输出：

```text
docs/product/qlanalyser_page_route_contract_20260705.md
```

或合入现有页面清单。

### Phase 2: 工作流状态唯一真相

修复：

- 顶部步骤条只表示流程状态。
- 页面标题表示当前任务。
- 状态条表示当前项目/数据/准备/任务/报告。
- 下一步建议独立表达，不能伪装成当前步骤。

### Phase 3: 每页状态化空态

优先页面：

1. 数据管理无项目。
2. 数据准备无数据。
3. 分析任务未准备。
4. 结果无结果。
5. 报告无结果/有结果/报告就绪。
6. 癫痫样事件无数据。

### Phase 4: 分析方法层级

修复：

- PSD 推荐首步。
- ERP 条件方法。
- 高级方法折叠。
- 方法实验室与主工作台分离。

### Phase 5: 教学模式和后台干净重测

修复：

- 示例引导与 sandbox 分离。
- 后台使用独立会话和 role 状态。
- 后台四页真实截图。

### Phase 6: 财务和账户降噪

修复：

- 左侧底部账户卡片减重。
- 个人中心财务折叠。
- 沙盒金额显式标注。

## 8. 复测截图要求

整改后至少重新生成：

```text
outputs/system_all_pages_adversarial_fix_20260705/login-customer.png
outputs/system_all_pages_adversarial_fix_20260705/login-account-open.png
outputs/system_all_pages_adversarial_fix_20260705/login-admin.png
outputs/system_all_pages_adversarial_fix_20260705/customer-dashboard.png
outputs/system_all_pages_adversarial_fix_20260705/customer-storage-no-project.png
outputs/system_all_pages_adversarial_fix_20260705/customer-storage-with-data.png
outputs/system_all_pages_adversarial_fix_20260705/customer-analysis-no-data.png
outputs/system_all_pages_adversarial_fix_20260705/customer-analysis-with-data.png
outputs/system_all_pages_adversarial_fix_20260705/customer-workflow-not-ready.png
outputs/system_all_pages_adversarial_fix_20260705/customer-workflow-ready.png
outputs/system_all_pages_adversarial_fix_20260705/customer-statistics-empty.png
outputs/system_all_pages_adversarial_fix_20260705/customer-publication-empty.png
outputs/system_all_pages_adversarial_fix_20260705/customer-userCenter.png
outputs/system_all_pages_adversarial_fix_20260705/customer-epilepsy-empty.png
outputs/system_all_pages_adversarial_fix_20260705/teaching-storage-after-guide.png
outputs/system_all_pages_adversarial_fix_20260705/teaching-analysis-after-guide.png
outputs/system_all_pages_adversarial_fix_20260705/teaching-workflow-after-guide.png
outputs/system_all_pages_adversarial_fix_20260705/teaching-statistics-after-guide.png
outputs/system_all_pages_adversarial_fix_20260705/teaching-publication-after-guide.png
outputs/system_all_pages_adversarial_fix_20260705/admin-dashboard.png
outputs/system_all_pages_adversarial_fix_20260705/admin-operations.png
outputs/system_all_pages_adversarial_fix_20260705/admin-finance.png
outputs/system_all_pages_adversarial_fix_20260705/admin-system.png
outputs/system_all_pages_adversarial_fix_20260705/standalone-lab.png
outputs/system_all_pages_adversarial_fix_20260705/lab-edf-reviewer.png
```

视口至少覆盖：

```text
1366 x 768
1536 x 864
1920 x 1080
2048 x 1152
2560 x 1440
```

每张截图配套 DOM 断言：

```yaml
requestedView_equals_activeView: true
primaryButtonCount_per_decision_area: <= 1
horizontalOverflow: false
forbidden_debug_terms_visible: []
visible_text_mojibake: false
main_task_visible_in_5s: true
empty_state_has_next_action: true
```

后台和教学模式如果仍不能捕获目标页，验收结果必须标：

```text
product_failed
```

不能标 `passed` 或 `conditional_pass`。

## 9. Issue Ledger

| ID | Surface | Type | Severity | Issue | Exact Fix |
| --- | --- | --- | --- | --- | --- |
| P1-SYS-01 | routing | logic/QA | P1 | 请求页和实际页不一致 | 建页面路由契约，截图断言 requested=active |
| P1-SYS-02 | global stepper | logic/UI | P1 | 步骤条、页面、下一步冲突 | 分离当前页、流程状态、下一步建议 |
| P1-SYS-03 | primary actions | usability | P1 | 主按钮数量不稳定 | 每状态一个主动作 |
| P1-SYS-04 | empty states | state UX | P1 | 空态保留禁用工作台 | 空态收起工作台，给原因和恢复动作 |
| P1-SYS-05 | analysis methods | scientific UX | P1 | 方法像清单，高级方法过重 | PSD 推荐，ERP 条件，高级折叠 |
| P1-SYS-06 | teaching mode | mode/state | P1 | 引导层遮蔽页面 | guide 与 sandbox 分离 |
| P1-SYS-07 | admin | QA/routing | P1 | 后台未被真实捕获 | 干净后台会话重测 |
| P1-SYS-08 | account/billing | product IA | P1 | 财务抢客户主流程 | 降权，标沙盒 |
| P1-LOGIN-01 | login | accessibility/QA | P1 | 登录捕获混入 app 文本 | app shell inert/aria-hidden，截图只取可见文本 |
| P1-STORAGE-01 | storage | state UX | P1 | 无项目仍显示上传控件 | 无项目只显示去项目页 |
| P1-ANALYSIS-01 | data prep | state UX | P1 | 无数据仍显示假波形 | 无数据收起波形工作台 |
| P1-WORKFLOW-01 | workflow | usability | P1 | 无主动作且 8 方法噪声 | 状态化 PSD 主卡 |
| P1-RESULT-01 | results | state UX | P1 | 无结果无主按钮 | 空态指向检查数据或运行 PSD |
| P1-REPORT-01 | report | state UX | P1 | 生成报告禁用与回退动作竞争 | 按状态切换唯一主按钮 |
| P1-EPILEPSY-01 | epilepsy workbench | mode/empty | P1 | 子页身份和空骨架不清 | breadcrumb + 单一空态 |
| P1-LAB-01 | standalone lab | IA/scientific | P1 | 实验室像主工作台 | 改名方法实验室，高级折叠 |
| P2-EDF-01 | EDF reviewer | empty UX | P2 | 空态说明不足 | 说明选择文件后出现的工具 |
| P2-VIS-01 | global visual | polish | P2 | 边框和卡片切割过多 | 减少嵌套卡片，用分隔线和 context strip |

## 10. 最终门禁

```yaml
ADVERSARIAL_REVIEW_GATE:
  pass: false
  reason:
    - all_pages_not_reliably_captured
    - route_state_conflicts
    - state_empty_primary_action_failures
    - teaching_admin_needs_clean_recapture
  p0_count: 0 confirmed
  unresolved_p1_count: 18
  stop_or_continue:
    continue_after_route_contract_and_state_fix
```

当前可以继续优化 UI，但不要再以“看过主流程几个页面”宣称全系统页面通过。下一步应先把页面契约、状态机和截图验收修好，再做颜色、图标、留白等视觉 polish。

