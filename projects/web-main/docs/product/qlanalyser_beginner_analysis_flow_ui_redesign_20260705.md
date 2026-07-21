# QLanalyser 新手分析流 UI 重设计详细文档

Date: 2026-07-05  
Status: proposed design contract for implementation  
Scope: QLanalyser Online 登录封面、客户工作台、项目管理、数据管理、数据准备、分析任务、结果查看、报告交付、质量检查、个人中心、低调运营后台入口。  
Owner: Codex UI/Product review lane  

## 0. 文档目的

本文件用于把 QLanalyser 当前“页面很多、信息很满、像模块清单”的体验，重构为“脑电分析小白也能开始一次分析”的产品工作流。

它不是审美建议集合，也不是单页截图优化说明。它是后续前端实现、截图验收、文案治理和对抗性评审的设计依据。

目标体验：

```text
创建或打开项目
-> 上传或选择 EEG 数据
-> 检查 EEG 数据
-> 运行推荐分析
-> 查看结果
-> 生成并下载报告
```

用户第一眼必须知道：

1. 我现在在哪一步。
2. 当前页面处理什么数据。
3. 为什么这一步对 EEG 分析重要。
4. 现在只能或最应该做什么。
5. 下一步怎样安全继续。

## 1. 依据来源

本设计读取并采用以下本地项目与知识库规范：

| 来源 | 采用内容 |
| --- | --- |
| `AGENTS.md` | 品牌、产品定位、V0.1 试点边界、核心工作流、非诊断边界 |
| `DESIGN.md` | 研究支持产品边界、控件可用性、任务/结果/报告可追溯 |
| `docs/product/lab_to_main_workflow_gate.md` | 主客户流程、禁止内部术语、新手五问、分析方法晋级规则 |
| `docs/product/qlanalyser_project_design_system_20260628.md` | 专业 EEG 研究工作台定位、页面职责、组件与文案边界 |
| `docs/product/qlanalyser_ui_interaction_visual_governance_master_20260628.md` | 一意图一主控、状态完整、主科学对象优先、禁用原因 |
| `docs/product/qlanalyser_research_user_copy_governance_spec_20260701.md` | 科研用户文案、非医疗边界、结果/报告可追溯文案 |
| `docs/quality/visual_layout_design_spec.md` | 1920 x 1080 目标、1366 最小安全、浏览器缩放策略、截图证据 |
| `docs/modules/beginner_friendly_analysis_function_blueprint.md` | 新手友好分析功能四层结构、PSD/ERP/QC 显示边界 |
| `docs/modules/beginner_learning_analysis_design.md` | 先完成、再理解、再进阶；QC/PSD/ERP 学习路径 |
| `D:\QuanLanKnowledgeBase\learning-notes\design\QUANLAN_DESIGN_PRINCIPLES_V1_CN.md` | 极致清晰、有用、专业可信、可读性、状态完整 |
| `D:\QuanLanKnowledgeBase\learning-notes\design\B2B_SCIENTIFIC_DASHBOARD_SCREENSHOT_AUDIT_CHECKLIST_CN.md` | B 端科研 dashboard 截图审查、状态与科学边界 |
| `D:\QuanLanKnowledgeBase\learning-notes\design\UX_STATE_FEEDBACK_EMPTY_ERROR_LOADING_MOTION_GATE_CN.md` | Empty/Loading/Error/Disabled/Success 状态规则 |
| `D:\QuanLanKnowledgeBase\learning-notes\design\QLANALYSER_DASHBOARD_DESIGN_SYSTEM_FIT_MATRIX_CN.md` | QLanalyser 页面参考系统选择和 dashboard 反模式 |

## 2. 产品定位与品牌表达

### 2.1 品牌

标准品牌显示：

```text
全澜脑科学® | QuanLan BrainScience®
```

显示要求：

- 中文与英文大小写保持上面写法。
- `®` 使用右上角标视觉，不挤占正文基线。
- 品牌不可全大写英文。
- 登录封面第一屏必须能看到品牌，不只藏在侧边栏小字里。

### 2.2 产品名

标准产品名：

```text
QLanalyser Online
```

### 2.3 产品定位句

当前项目定位采用：

```text
清晰管理 EEG 数据，规范执行分析流程，稳定交付可复核研究结果。
```

登录封面可使用更短的关键词式表达：

```text
清晰数据管理 · 流程化分析 · 规范结果交付
```

这三个词分别对应产品能力：

| 关键词 | 产品含义 | 不应变成 |
| --- | --- | --- |
| 清晰数据管理 | 项目、文件、参数、结果都能找到来源 | 文件仓库口号 |
| 流程化分析 | 从准备到任务到结果按步骤推进 | 一键智能判断 |
| 规范结果交付 | 图表、表格、方法和记录可复核 | 夸张营销承诺 |

### 2.4 非医疗边界

默认客户 UI 应使用低噪声边界：

```text
科研分析辅助，不作为临床诊断依据。
```

显示位置：

- 登录封面底部或产品说明区简短出现一次。
- 数据准备、结果、报告页在涉及解释时出现。
- 不要在每个卡片重复，避免噪音。

禁止表达：

- 自动诊断。
- 确诊。
- 临床分诊。
- 治疗建议。
- 一键得出科学结论。
- 精确定位病灶或因果连接，除非未来有单独证据和监管路线。

## 3. 对抗性评审摘要

### 3.1 当前主要问题

基于现有页面结构和本地规范，当前体验的根问题不是“图标再小一点”这么局部，而是：

```text
页面按模块堆叠，而不是按新手任务推进。
```

具体表现：

| 问题 | 风险 | 级别 |
| --- | --- | --- |
| 首页像状态面板和功能入口混合，不像“开始一次 EEG 分析” | 新手不知道第一步做什么 | P1 |
| 数据管理、数据准备、分析任务之间的下一步关系不够强 | 用户会跳页试错 | P1 |
| 分析方法暴露过多，PSD/ERP/TFR/PAC/Connectivity/ML 权重不清 | 预览或高级能力看起来像可稳定交付 | P1 |
| 空状态有时只告诉用户没有内容，未完整回答原因和下一步 | 首次使用阻塞 | P1 |
| 图标、卡片、按钮在 1920 下仍显得占空间 | 工作区不够开阔，科学对象不突出 | P2 |
| 一些页面仍有“报告交付”“质量检查”“个人中心”等运营感内容抢主流程注意力 | 主路径不纯 | P2 |
| 登录封面已有品牌和关键词，但账号开通、后台入口、测试账号逻辑需要更克制 | 第一印象不够产品化 | P2 |

### 3.2 目标成熟度

按 `open-design-codex-visual-review` 成熟度，本次目标不是只达到 `usable`，而是达到：

```text
good usability -> aesthetic and professional 的过渡状态
```

可接受标准：

- 用户可以在无人指导下完成一次示例或真实数据的 PSD 主路径。
- 用户不会误以为 PAC/Connectivity/ML 是当前稳定主流程。
- 页面视觉更开阔，主科学对象和主动作优先于装饰、图标和运营信息。
- 关键状态有恢复路径。

## 4. 设计原则

### 4.1 先主流程，后功能清单

导航和页面不是为了展示“我们有什么模块”，而是帮助用户完成：

```text
项目 -> 数据 -> 准备 -> 分析 -> 结果 -> 报告
```

任何不能服务当前阶段决策的内容，应降级、折叠、移到个人中心或运营后台。

### 4.2 一页一个主任务

每个页面必须定义：

```yaml
primary_task:
primary_visual_object:
primary_action:
disabled_reason:
next_safe_action:
```

一屏内不允许多个同权重主按钮竞争。

### 4.3 新手默认，专家折叠

默认视图只出现：

- 当前数据。
- 当前状态。
- 推荐动作。
- 简短风险。
- 必要参数。

专家细节折叠：

- MNE 函数名。
- 参数 JSON。
- manifest。
- artifact 路径。
- workflow id。
- 软件版本。
- 高级参数。

### 4.4 方法必须有边界

当前 V0.1 主路径：

- QC/Data Preparation: 必须。
- PSD: 推荐首个稳定分析。
- ERP: 条件可用，必须先确认事件语义。
- Report: 结果完成后可用。

默认不作为主流程入口：

- TFR。
- PAC。
- Connectivity。
- ML。
- 其他实验性工作台。

这些可以出现在“进阶分析”或“方法实验室”，但不能和 PSD 同权重。

### 4.5 状态也是页面

每个页面必须设计：

- 默认态。
- 首次空态。
- 缺少前置条件。
- 加载态。
- 长任务态。
- 错误态。
- 禁用态。
- 成功态。

空状态必须回答：

1. 这里本来显示什么。
2. 为什么现在没有。
3. 用户下一步做什么。

### 4.6 开阔但不依赖缩放

目标体验优化于：

```text
1920 x 1080
browser zoom 100%
```

但不得依赖用户把浏览器缩放到 80%。布局必须通过：

- 更小更克制的图标。
- 更紧凑的导航。
- 更少卡片。
- 更清楚的内容分组。
- 更少重复说明。
- 更大的科学对象区域。

而不是通过禁止用户访问缩放能力来制造“看起来更空”。

## 5. 目标信息架构

### 5.1 导航顺序

客户主导航建议：

1. 项目
2. 数据
3. 准备
4. 分析
5. 结果
6. 报告
7. 质量
8. 个人

运营后台从客户主导航中降权：

- 不在默认客户导航中占一整组入口。
- 仅管理员登录后在右上角或个人菜单中显示“运营后台”。
- 后台内部再分：总览、任务、财务、系统。

### 5.2 页面职责

| 页面 | 当前路由 | 主任务 | 主视觉对象 | 主动作 |
| --- | --- | --- | --- | --- |
| 登录封面 | `loginScreen` | 进入工作区或示例模式 | 全屏品牌底图 + 极简登录框 | 登录 |
| 项目 | `dashboard` | 创建或打开项目 | 项目列表/当前项目 | 创建新项目或打开项目 |
| 数据 | `storage` | 上传或选择 EEG 数据 | 文件列表和文件详情 | 上传 EEG 文件 |
| 准备 | `analysis` | 检查 EEG 数据并确认准备方案 | 波形/文件质量/准备步骤 | 确认数据准备 |
| 分析 | `workflow` | 选择可运行分析方法并提交任务 | 推荐方法列表 | 运行 PSD |
| 结果 | `statistics` | 查看已完成任务的图表、参数和限制 | 结果图表/表格 | 生成报告 |
| 报告 | `publication` | 下载可复核交付包 | 报告预览/下载清单 | 下载报告包 |
| 质量 | `journey` | 发布或交付前检查完整性 | 检查清单 | 处理阻断项 |
| 个人 | `userCenter` | 账户、余额、通知、帮助 | 账户摘要 | 管理账户 |
| 运营后台 | `admin*` | 管理任务/客户/系统 | 运营表格 | 查看异常任务 |

## 6. 全局状态机

### 6.1 主状态

```yaml
workspace_state:
  logged_out:
    next: login_or_demo
  no_project:
    next: create_project_or_open_project
  project_selected_no_data:
    next: upload_or_select_eeg
  data_selected_not_prepared:
    next: inspect_and_confirm_preparation
  preparation_confirmed_no_task:
    next: run_recommended_analysis
  task_running:
    next: wait_or_continue_in_background
  task_completed_no_report:
    next: review_result_or_generate_report
  report_ready:
    next: download_report_package
```

### 6.2 状态和主按钮

| 状态 | 顶部状态文案 | 主按钮 | 禁用或次级动作 |
| --- | --- | --- | --- |
| 未登录 | 请登录 QLanalyser Online | 登录 | 示例模式、账号开通 |
| 无项目 | 先创建或打开一个项目 | 创建新项目 | 打开已有项目 |
| 有项目无数据 | 当前项目还没有 EEG 数据 | 上传 EEG 文件 | 切换项目 |
| 有数据未准备 | 请先检查 EEG 数据 | 检查数据 | 返回数据页 |
| 已准备未分析 | 可以运行推荐分析 | 运行 PSD 分析 | 展开 ERP 条件 |
| 任务运行中 | 分析任务正在运行 | 查看任务状态 | 后台运行 |
| 有结果无报告 | 结果已生成 | 生成报告 | 查看参数 |
| 报告就绪 | 报告包可下载 | 下载报告包 | 重新生成 |

### 6.3 URL 与状态恢复

规则：

- URL/hash 可以恢复页面，不应伪造业务状态。
- 如果 hash 进入 `workflow` 但没有项目或数据，页面显示缺少前置条件并给出主按钮。
- localStorage/sessionStorage 只能辅助恢复，不是主事实来源。
- 示例模式和普通模式必须有明确隔离。

## 7. 登录封面设计

### 7.1 目标

登录封面要建立信任，而不是讲满产品功能。

第一屏结构：

```text
full-bleed background image
  left/top: brand + product name + three capability keywords
  right: compact login module
  top-right: subtle admin entry if permitted
  bottom: concise non-medical boundary or copyright
```

### 7.2 背景图

要求：

- 整个封面是一张底图，不用左右分栏假封面。
- 底图应与 EEG、脑科学、研究工作台相关。
- 不使用纯渐变、装饰光斑、过度抽象科技感作为主视觉。
- 登录框区域必须有足够遮罩或局部暗化，保证可读。

### 7.3 文案

推荐首屏：

```text
全澜脑科学® | QuanLan BrainScience®
QLanalyser Online
清晰数据管理 · 流程化分析 · 规范结果交付
```

不再使用：

```text
面向科研团队的脑电数据分析工作区
研究工作区
进入项目
```

原因：

- “面向科研团队”像介绍页，不像工作台入口。
- “研究工作区 / 进入项目”重复，不指向真实登录动作。

### 7.4 登录模块

登录模块只保留：

- Tab: 登录 / 账号开通。
- 账号输入。
- 密码输入。
- 记住登录状态。
- 登录按钮。
- 找回账号。

开发期默认填入测试账号：

```text
demo.customer@quanlan.cn
```

密码字段可默认填入演示密码，但不在文档中记录真实密码。

错误规则：

- 页面初始不显示错误。
- 后端不可用时，开发模式可进入本地 demo workspace，但必须给出低噪声提示。
- 正式模式不能把失败静默当成功。

账号开通：

```text
请联系运营人员开通账号。
```

不要写成长段解释。

后台入口：

- 右上角小入口。
- 管理员登录后显示。
- 视觉权重低于客户登录。

## 8. 工作台全局布局规格

### 8.1 设计目标

QLanalyser 是桌面科研工作台，目标是开阔、可扫读、适合反复操作。

主要画布：

```text
target: 1920 x 1080, browser zoom 100%
minimum safe: 1366 x 768, browser zoom 100%
```

必须验证：

- 1366 x 768。
- 1536 x 864。
- 1920 x 1080。
- 2048 x 1086。
- 2560 x 1440。

### 8.2 页面壳

建议尺寸：

| 区域 | 规格 |
| --- | --- |
| 左侧导航 | 176-200 px |
| 顶部上下文栏 | 44-52 px |
| 主区内边距 | 18-24 px |
| 面板间距 | 12-16 px |
| 面板圆角 | 8 px 或更小 |
| 图标视觉尺寸 | 14-16 px |
| 图标按钮可点击区 | 36-40 px |
| 主按钮高度 | 34-38 px |
| 表格行高 | 34-40 px |

说明：

- 图标小，不等于点击区域小。
- 视觉要轻，交互仍要可点。
- 不做大圆角卡片堆叠。
- 不把页面 section 包成一个大卡片。

### 8.3 浏览器缩放策略

不要试图完全禁止浏览器缩放。缩放是系统和可访问性能力。

允许做：

- 阻止常见误触：`Ctrl/Cmd + mouse wheel`。
- 阻止 `Ctrl/Cmd + +`、`Ctrl/Cmd + -`、`Ctrl/Cmd + =`、`Ctrl/Cmd + 0` 的页面默认缩放。
- 不阻止应用内部的波形时间缩放快捷键。

禁止做：

- 依赖 80% 浏览器缩放才能正常使用。
- 把浏览器缩放保护当作布局正确性的前提。
- 破坏系统级可访问性。

### 8.4 视觉密度

当前“图标和控件太大”的问题，应通过视觉预算解决：

| 元素 | 目标 |
| --- | --- |
| 侧边栏 | 图标 15 px，文字 13 px，行高 34-36 px |
| 面板标题 | 16-18 px，不用 hero 级标题 |
| 面板正文 | 13-14 px |
| 卡片 | 减少数量，每张卡只承载一个对象 |
| 状态 chip | 只放关键状态，不堆很多彩色标签 |
| 主工作区 | 优先给波形、图表、表格、报告预览 |

## 9. 逐页详细设计

### 9.1 项目页

页面名建议：

```text
开始一次 EEG 分析
```

页面目的：

```text
项目用于保存本次分析的数据、准备方案、任务、结果和报告。
```

默认无项目布局：

```text
Page header
  title: 开始一次 EEG 分析
  subtitle: 创建项目后，数据、参数、结果和报告会保存在同一条记录中。
  primary: 创建新项目
  secondary: 打开已有项目

Main area
  left: project list or empty state
  right: current project detail, only after selection
```

主动作规则：

| 状态 | 主动作 |
| --- | --- |
| 无项目 | 创建新项目 |
| 有项目 | 进入数据管理 |
| 项目归档 | 恢复项目或只读查看 |

空状态：

```text
还没有项目
创建一个项目，用来保存这次 EEG 分析的数据、参数、结果和报告。
```

按钮：

```text
创建新项目
```

删除/归档：

- 放入二级菜单或详情区。
- 必须确认。
- 说明影响范围。

不显示：

- 生命周期说明。
- 后续分析方法卡片。
- 报告下载入口。
- 运营/充值信息。

### 9.2 数据页

页面名建议：

```text
上传或选择 EEG 数据
```

页面目的：

```text
每个 EEG 文件先进入当前项目，再进入数据检查和分析流程。
```

布局：

```text
Page header
  current project chip
  primary: 上传 EEG 文件

Main
  left: file ledger
  right: selected file detail
```

无项目空态：

```text
上传数据前，需要先创建或打开一个项目。
```

主按钮：

```text
去项目页
```

有项目无数据空态：

```text
当前项目还没有 EEG 数据
上传 EDF、BDF、FIF 等 EEG 文件后，可以先检查波形和基础信息。
```

主按钮：

```text
上传 EEG 文件
```

文件列表显示字段：

- 文件名。
- 格式。
- 时长。
- 采样率。
- 通道数。
- 当前状态。
- 下一步。

文件详情主按钮：

```text
检查数据
```

不显示：

- 生命周期面板。
- 归档可恢复说明。
- “近期可快速重跑 / 项目期保存 / 归档可恢复”这类解释。
- 开发字段、路径、manifest、runner。

### 9.3 数据准备页

页面名建议：

```text
检查 EEG 数据
```

页面目的：

```text
先确认文件可读、通道和波形合理，再进入分析。
```

布局：

```text
Top object strip
  project | file | sample rate | channels | preparation status

Main
  left large: waveform / preview / quality evidence
  right narrow: preparation checklist and confirm action

Bottom or drawer
  advanced preprocessing details
```

步骤：

1. 选择数据。
2. 查看波形与基础信息。
3. 标记明显坏道或坏段。
4. 确认数据准备。
5. 进入分析任务。

无数据空态：

```text
还没有选择 EEG 数据
请先在数据页选择一个文件，系统会在这里显示波形预览和基础检查。
```

主按钮：

```text
去选择数据
```

确认前必须显示：

- 原始 EEG 不会被覆盖。
- 准备动作写入准备方案。
- 分析任务会引用该准备方案。

主按钮：

```text
确认数据准备
```

禁用原因示例：

```text
请先选择 EEG 文件。
波形仍在读取中，请稍后确认。
当前文件读取失败，请重新选择或上传。
```

工具栏分组：

| 组 | 控件 |
| --- | --- |
| 浏览 | 上一页、下一页、时间窗 |
| 显示 | 增益、通道数、事件显示 |
| 标记 | 浏览、选段、坏段、坏道 |
| 草稿 | 撤销、恢复、清空草稿 |
| 确认 | 确认准备方案 |

不允许：

- 浏览和写入模式混在一起。
- Epoch 控件默认出现在基础连续波形预览中。
- 状态栏重复所有显示控件。
- 旧波形被当作当前窗口显示。

### 9.4 分析任务页

页面名建议：

```text
选择分析方法
```

页面目的：

```text
根据当前数据和准备状态，选择可以运行的分析任务。
```

默认布局：

```text
Top gate strip
  current project | current data | preparation state

Primary method
  PSD 频谱分析
  recommended badge
  short explanation
  primary: 运行 PSD 分析

Conditional methods
  ERP 事件相关电位
  disabled or secondary until event semantics confirmed

Advanced/lab methods
  collapsed
```

PSD 文案：

```text
PSD 频谱分析
查看不同频段的能量分布。第一次分析建议先运行 PSD。
```

PSD 限制：

```text
频段功率受参考、伪迹和预处理影响，不能单独解释为诊断结论。
```

ERP 文案：

```text
ERP 事件相关电位
适合有事件标记的数据。运行前需要确认 target、standard 或其他事件语义。
```

ERP 禁用原因：

```text
当前数据还没有确认事件标记，暂不能运行 ERP。
```

进阶方法折叠：

```text
进阶分析方法
TFR、PAC、Connectivity 和 ML 需要更多前置条件，当前不作为推荐首步。
```

不允许：

- 8 个方法同权重平铺。
- preview/lab 方法和 stable 方法看起来一样可交付。
- QC 作为和 PSD 并列的分析方法卡。
- “一键智能分析”。

### 9.5 结果页

页面名建议：

```text
查看分析结果
```

页面目的：

```text
查看已完成任务的图表、表格、参数、质量提醒和解释边界。
```

无结果空态：

```text
还没有分析结果
完成一次分析任务后，这里会显示图表、表格、参数和可复核记录。
```

主按钮：

```text
去运行 PSD 分析
```

结果卡结构：

| 区域 | 内容 |
| --- | --- |
| 结果 | 系统实际计算到什么 |
| 依据 | 来自哪些通道、频段、时间窗或事件 |
| 质量 | 数据是否足够继续解释 |
| 风险 | 哪些因素可能改变解释 |
| 下一步 | 生成报告、调整准备、专家复核 |

每个结果必须显示：

- 项目。
- EEG 文件。
- 任务 ID。
- 分析方法。
- 准备方案版本。
- 关键参数。
- 图表单位。
- 方法限制。
- 下载入口。

不允许：

- 只有漂亮图，没有参数和限制。
- 把 descriptive metric 写成诊断结论。
- 把 PAC/connectivity 说成因果或信息流。

### 9.6 报告页

页面名建议：

```text
生成和下载报告
```

页面目的：

```text
把结果、图表、参数、方法和复现记录打包交付。
```

无结果空态：

```text
还不能生成报告
请先完成至少一个分析任务。
```

主按钮：

```text
去运行分析
```

有结果无报告：

```text
已有分析结果，可以生成报告。
```

主按钮：

```text
生成报告
```

报告就绪：

```text
报告包已生成
```

主按钮：

```text
下载报告包
```

报告内容清单：

- HTML 报告。
- 图表。
- 表格。
- 参数记录。
- 方法说明。
- 软件版本。
- 复现记录。
- 限制说明。

技术详情：

- 默认折叠。
- 不在首屏显示 artifact count、manifest、schema。

### 9.7 质量页

页面名建议：

```text
检查交付完整性
```

页面目的：

```text
在交付前检查数据、准备、任务、结果和报告是否完整。
```

默认位置：

- 主流程第 7 位，低于报告。
- 不抢“结果”和“报告”的主任务。

显示方式：

| 状态 | 文案 |
| --- | --- |
| 可通过 | 当前交付材料完整 |
| 有缺项 | 还有项目需要处理 |
| 无报告 | 生成报告后再检查交付完整性 |

主按钮：

- 有阻断项：处理阻断项。
- 无阻断项：返回报告页。

不显示：

- 内部验收术语。
- release gate。
- acceptance。
- debug 路径。

### 9.8 个人中心

页面名建议：

```text
个人中心
```

页面目的：

```text
管理账号、余额、通知和帮助，不承载分析主流程。
```

结构：

- 账号信息。
- 所属单位。
- 登录状态。
- 余额和账单。
- 通知。
- 帮助与反馈。

不放：

- 项目列表。
- 数据列表。
- 方法入口。
- 结果主展示。
- 报告主下载。

### 9.9 运营后台

入口：

- 管理员角色才显示。
- 客户主界面右上角低调入口。
- 不在客户侧边栏长期占位。

后台首页：

```text
运营后台
任务、客户、账务和系统状态。
```

后台可以更信息密集，但仍需：

- 表格可扫读。
- 错误可恢复。
- 危险操作确认。
- 客户数据权限边界。

## 10. 文案规范

### 10.1 文案语气

使用：

- 短句。
- 当前任务语言。
- 真实 EEG 工作流语言。
- 可执行下一步。

避免：

- AI 味套话。
- 营销口号过多。
- “赋能”“智能洞察”“一站式”等泛词。
- “研究工作区”“进入项目”这种重复弱动作。
- 内部技术词。

### 10.2 页面标题建议

| 路由 | 标题 |
| --- | --- |
| 登录 | QLanalyser Online |
| 项目 | 开始一次 EEG 分析 |
| 数据 | 上传或选择 EEG 数据 |
| 准备 | 检查 EEG 数据 |
| 分析 | 选择分析方法 |
| 结果 | 查看分析结果 |
| 报告 | 生成和下载报告 |
| 质量 | 检查交付完整性 |
| 个人 | 个人中心 |

### 10.3 禁止客户默认可见词

```text
manifest
runner
dispatch
schema
artifact count
cache range
raw JSON
backend task object
acceptance
gate
registry
task runner debug
MNE internals
```

可以出现在：

- 专家详情。
- 管理员技术诊断。
- 下载的复现文件。
- 开发文档。

### 10.4 推荐替换

| 旧表达 | 新表达 |
| --- | --- |
| 研究工作区 | QLanalyser Online |
| 进入项目 | 打开项目 |
| 面向科研团队的脑电数据分析工作区 | 删除 |
| 当前可用 8 项分析方法 | 推荐先运行 PSD |
| 提交分析与生成报告 | 运行分析 |
| 报告交付 | 生成和下载报告 |
| 查看结果 | 查看分析结果 |
| 数据准备工作台 | 检查 EEG 数据 |
| 当前项目暂无数据 | 当前项目还没有 EEG 数据 |

## 11. 组件规范

### 11.1 PageHeader

字段：

```yaml
title:
subtitle:
context_chips:
primary_action:
secondary_actions:
```

规则：

- 标题说任务，不说模块。
- 副标题一行内说明为什么。
- 只放一个主动作。

### 11.2 WorkflowStepper

步骤：

```text
项目 / 数据 / 准备 / 分析 / 结果 / 报告
```

规则：

- 显示当前步骤。
- 已完成步骤可回看。
- 未满足前置条件的步骤显示原因。
- 不做满屏大卡片。

### 11.3 ObjectContextStrip

显示：

- 当前项目。
- 当前数据。
- 准备状态。
- 当前任务或结果。

规则：

- 一行扫读。
- 不重复表格中的长字段。
- 状态用语义颜色，但不只靠颜色。

### 11.4 EmptyState

结构：

```yaml
title:
reason:
next_action:
secondary_action_optional:
```

示例：

```text
还没有分析结果
完成一次分析任务后，这里会显示图表、表格、参数和可复核记录。
[去运行 PSD 分析]
```

### 11.5 MethodCard

字段：

```yaml
method_name:
status: recommended | available | conditional | advanced | unavailable
what_it_does:
required_inputs:
major_limitation:
primary_action:
disabled_reason:
```

视觉：

- 推荐 PSD 一张主卡。
- ERP 次级或条件卡。
- 进阶方法折叠。

### 11.6 ResultExplanationCards

固定 5 卡：

1. 结果。
2. 依据。
3. 质量。
4. 风险。
5. 下一步。

每张只写 1-2 句，不写教材段落。

## 12. 状态矩阵

### 12.1 页面级状态

| 页面 | 空态 | 加载 | 错误 | 禁用 | 成功 |
| --- | --- | --- | --- | --- | --- |
| 项目 | 还没有项目 | 正在读取项目 | 项目列表读取失败 | 无权限编辑 | 项目已创建 |
| 数据 | 当前项目还没有 EEG 数据 | 正在上传/读取文件 | 文件上传失败 | 未选项目不能上传 | 文件已上传 |
| 准备 | 还没有选择 EEG 数据 | 正在读取波形 | 波形读取失败 | 未加载完成不能确认 | 准备方案已确认 |
| 分析 | 还不能运行分析 | 正在创建任务 | 任务创建失败 | 缺少准备方案/事件 | 分析任务已提交 |
| 结果 | 还没有分析结果 | 正在读取结果 | 结果读取失败 | 无完成任务 | 结果已生成 |
| 报告 | 还不能生成报告 | 正在生成报告 | 报告生成失败 | 无结果不能生成 | 报告包已生成 |

### 12.2 长任务状态

分析和报告生成必须显示：

```yaml
task_id:
stage:
  - queued
  - loading_data
  - preprocessing
  - running_analysis
  - rendering
  - packaging
  - complete
  - failed
progress_percent:
current_action_label:
can_run_in_background:
retry_available:
safe_error_id:
```

文案示例：

```text
正在计算 PSD 频谱
任务会在后台运行，完成后可在结果页查看。
```

失败示例：

```text
PSD 分析未完成
当前文件读取成功，但频率参数不合法。请恢复默认参数后重试。
```

## 13. 分析方法暴露策略

### 13.1 默认推荐

首次分析推荐：

```text
PSD 频谱分析
```

理由：

- 不依赖事件标记。
- 适合新手理解频段能量。
- 可作为后续 ERP/TFR/PAC 前的数据理解基础。

### 13.2 条件方法

ERP：

- 只有检测到或上传了事件标记后才强调。
- 必须先确认事件语义。
- 结果必须显示 ROI、baseline、有效 epoch、drop log。

### 13.3 进阶方法

TFR、PAC、Connectivity、ML：

- 默认折叠。
- 标为进阶或实验。
- 必须说明前置条件。
- 不能作为 V0.1 稳定主流程承诺。

示例：

```text
进阶分析方法
这些方法需要事件、清洗策略、统计设计或额外复核。当前不建议作为第一次分析。
```

## 14. 当前页面到目标页面迁移表

| 当前问题 | 目标改法 | 优先级 |
| --- | --- | --- |
| 登录封面信息和登录模块仍偏解释型 | 全底图 + 品牌 + 三关键词 + 极简登录 | P1 |
| 项目页像状态 dashboard | 改成“开始一次 EEG 分析” | P1 |
| 数据页仍有多余说明 | 只保留文件列表、详情、上传和下一步 | P1 |
| 数据准备首屏控件多 | 波形优先，准备 checklist 右侧，专家折叠 | P1 |
| 分析页 8 个方法并列 | PSD 推荐，ERP 条件，进阶折叠 | P1 |
| 结果页空态和报告关系不够新手化 | 无结果时直接引导去运行 PSD | P1 |
| 报告页“交付”感强但路径不清 | 改成生成/下载报告，按结果状态显示 | P1 |
| 质量页像内部验收 | 改成客户可理解的交付完整性检查 | P2 |
| 个人中心内容过多 | 保留账户/余额/通知/帮助，移除主流程 | P2 |
| 运营后台入口权重过高 | 右上角低调入口，管理员可见 | P2 |
| 图标显得大、页面不空旷 | 统一 14-16 px 图标视觉尺寸和紧凑行高 | P2 |

## 15. 实施计划

### Phase 1: 信息架构和文案收口

目标：

- 页面标题改成任务语言。
- 每页只有一个主动作。
- 删除生命周期类说明。
- 登录封面收口。
- 默认测试账号不阻塞开发登录。

改动范围：

- `frontend/index.html`
- `frontend/app.js`
- `frontend/styles.css`

验收：

- 首屏不出现“面向科研团队的脑电数据分析工作区”。
- 登录不因 demo 后端不可用阻塞开发。
- 项目页第一主按钮明确。
- 数据页无生命周期面板。

### Phase 2: 新手主流程状态机

目标：

- 建立 `no_project -> project_selected_no_data -> data_selected_not_prepared -> preparation_confirmed_no_task -> task_completed_no_report -> report_ready` 的 UI 派生状态。
- 每页空态和禁用态由状态机生成。

验收：

- hash 直达任意页面时，都能显示缺少前置条件和下一步。
- 不出现可见但点了无反应的主按钮。

### Phase 3: 分析方法页重构

目标：

- PSD 作为推荐首步。
- ERP 条件可用。
- TFR/PAC/Connectivity/ML 默认折叠或标记为进阶。

验收：

- 新手不会看到 8 个同权重方法卡。
- 缺少事件时 ERP 有明确禁用原因。
- 预览/实验方法不冒充稳定交付。

### Phase 4: 工作区视觉密度升级

目标：

- 1920 x 1080 下主区更开阔。
- 图标视觉尺寸降低。
- 面板数量减少。
- 主科学对象面积增加。

验收：

- 1920 截图中主内容区域不是卡片墙。
- 1366 无横向溢出。
- 重要按钮不被挤压。
- 浏览器 100% 缩放下可用，不依赖 80%。

### Phase 5: 结果和报告可复核表达

目标：

- 结果页显示方法、参数、准备方案、限制。
- 报告页显示生成和下载状态。
- 专家详情折叠。

验收：

- 每个结果能追溯到项目、文件、任务和参数。
- 报告下载入口只在报告就绪后突出。
- 无诊断性表达。

## 16. 验收标准

### 16.1 页面截图

每轮主要 UI 实现后至少保存：

```text
outputs/beginner_flow_login_1920.png
outputs/beginner_flow_dashboard_1920.png
outputs/beginner_flow_storage_1920.png
outputs/beginner_flow_analysis_1920.png
outputs/beginner_flow_workflow_1920.png
outputs/beginner_flow_results_1920.png
outputs/beginner_flow_publication_1920.png
outputs/beginner_flow_user_center_1920.png
outputs/beginner_flow_1366_dashboard.png
outputs/beginner_flow_1536_analysis.png
```

必须检查：

- 无水平溢出。
- 无文字重叠。
- 无主按钮被遮挡。
- 图标视觉尺寸一致。
- 页面首屏能看出主任务。

### 16.2 用户级路径

最低验收路径：

1. 打开登录页。
2. 使用默认 demo 账号进入。
3. 创建或打开项目。
4. 上传或选择 EEG 数据。
5. 进入数据准备。
6. 确认准备方案。
7. 运行 PSD。
8. 查看结果。
9. 生成报告。
10. 下载报告包。

### 16.3 设计评分

每页按 5 分评：

| 维度 | 通过线 |
| --- | --- |
| 视觉层级 | >= 4 |
| 一致性 | >= 4 |
| 可用性 | >= 4 |
| 品牌匹配 | >= 4 |
| 现代专业感 | >= 4 |
| 可读性/可访问性 | >= 4 |

发布前不得有：

- P0。
- 未解释的 P1。
- 客户默认可见 debug 术语。
- 医疗或诊断过度承诺。
- 只有理想态截图，没有空/错/加载/禁用证据。

## 17. 对抗性审查清单

每页评审时回答：

```yaml
page:
target_user:
primary_task:
primary_visual_object:
primary_action:
first_glance_5s:
current_data_visible:
next_step_visible:
empty_state:
loading_state:
error_state:
disabled_reason:
duplicate_controls:
forbidden_terms:
scientific_boundary:
visual_density:
responsive_risk:
P0:
P1:
P2:
decision:
```

### 17.1 P0 阻断

- 用户无法登录或进入示例模式。
- 主路径无法继续且没有恢复动作。
- 结果或报告暗示临床诊断。
- 重要文字不可读、乱码、重叠。
- 关键按钮可见但无效。
- 1366 或 1920 下出现水平溢出并影响主任务。

### 17.2 P1 必修

- 首屏看不出页面任务。
- 多个主按钮竞争。
- 空态没有下一步。
- 禁用按钮没有原因。
- PSD/ERP/进阶方法边界不清。
- 登录封面品牌或产品名不规范。

### 17.3 P2 优化

- 图标偏大。
- 间距略松或略密。
- 状态 chip 过多。
- 副文案不够自然。
- hover/focus polish 不一致。

## 18. 风险和待决策

### 18.1 需要产品确认

1. 默认 demo 登录是否在正式构建中隐藏。
2. 运营后台入口是否只对管理员角色显示。
3. ERP 是否在当前客户主流程中作为条件方法展示，还是先完全折叠。
4. TFR/PAC/Connectivity/ML 是否移入方法实验室，而非主分析页。
5. “报告交付”导航是否改名为“报告”，页面标题用“生成和下载报告”。

### 18.2 技术风险

| 风险 | 处理 |
| --- | --- |
| 当前前端存在后置文案 patch，可能覆盖 index 文案 | 将文案集中到一处状态/页面配置 |
| hash 直达页面和业务状态不一致 | 建立前置条件 gate |
| 示例模式和普通模式状态混用 | 明确 `teaching/customer_demo/normal` 状态 |
| 多处按钮触发同一动作 | 建立 command registry 或统一事件代理 |
| 图标缩小后点击区域变小 | 视觉尺寸和 hit area 分离 |

## 19. 实施后的文档更新

实现本设计后，至少更新：

- `docs/product/qlanalyser_research_user_copy_governance_spec_20260701.md`，补充新页面标题和禁用词。
- `docs/quality/visual_layout_design_spec.md`，如实际采用新的 nav 宽度和密度 token。
- `docs/product/qlanalyser_user_level_e2e_adversarial_review_standard_20260702.md`，如主路径截图名称或页面标题变化。
- `docs/PROJECT_STATUS.md` 和 `docs/TASK_LOG.md`，记录实现与验收结果。

## 20. 最终设计决策

QLanalyser UI 升级的核心不是“让页面更漂亮”，而是让用户更容易完成正确的 EEG 分析路径。

本设计采用以下决策：

1. 封面建立品牌信任，工作台承担任务推进。
2. 客户主路径固定为项目、数据、准备、分析、结果、报告。
3. PSD 是新手推荐首个分析。
4. ERP 是条件方法，事件语义确认前不高亮。
5. TFR/PAC/Connectivity/ML 不作为 V0.1 默认稳定入口。
6. 页面标题改为任务语言。
7. 状态和禁用原因必须成为 UI 的一部分。
8. 1920 x 1080 是最佳体验目标，但 1366 x 768 必须安全。
9. 防误触缩放可以做，但不能依赖禁止缩放解决布局。
10. 图标和控件视觉收紧，科学对象和主流程获得更多空间。

