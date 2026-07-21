# QLanalyser 项目清洁、波形操作与预处理同屏 UI 设计稿

日期：2026-06-26
目标用户：脑电科研人员、实验助理、数据分析人员
成熟度目标：aesthetic and professional / polished and professional

## 1. 设计系统选择

QLANALYSER_DASHBOARD_REFERENCE_SELECTION:

```yaml
surface: project_management_and_data_preparation_workbench
task: open_project_select_data_preview_waveform_and_prepare_data
user_role: researcher
risk_level: medium
selected_reference_systems:
  - name: Carbon workbench / data table / empty states
    evidence_level: L1/L3
    why_fit_this_surface: high-density B2B data workflow with clear task states
    adopted_rules:
      - clear empty/loading/error/success states
      - compact but readable controls
      - explicit status and recovery action
    skipped_rules_with_reason:
      - marketing-style cards are not suitable for repeated scientific work
  - name: PatternFly admin/workspace patterns
    evidence_level: L1/L3
    why_fit_this_surface: project list and operational records need dense, scannable tables
    adopted_rules:
      - searchable project ledger
      - danger actions visually downgraded
      - selected row state visible
    skipped_rules_with_reason:
      - enterprise admin chrome is not copied directly
  - name: QLanalyser scientific dashboard local rules
    evidence_level: project-specific
    why_fit_this_surface: EEG preview and preprocessing need scientific boundary language
    adopted_rules:
      - units, sampling rate, time window and provenance visible
      - non-diagnostic boundary visible
      - color does not imply unsupported certainty
required_screenshot_states:
  - default
  - dense_data
  - empty
  - loading
  - error
  - success
  - focus_or_keyboard
scientific_boundary_checks:
  method_visible: true
  units_visible: true
  uncertainty_visible: true
  sample_or_epoch_count_visible: not_applicable_for_preview
  source_or_data_provenance_visible: true
  non_diagnostic_boundary_visible: true
```

## 2. 项目管理页面

### 2.1 目标

用户进入项目管理时只需要回答三个问题：

1. 我现在在哪个项目？
2. 这个项目有没有 EEG 数据？
3. 下一步是上传、选择数据，还是进入数据准备？

### 2.2 结构

```text
项目管理
说明：先打开一个研究项目，再处理项目内数据。

[搜索项目                         ] [ ] 显示内部/归档项目
默认显示：12 / 538 个项目；已隐藏内部验收和自动生成项目

┌ 项目名称                 数据       状态          最近更新        操作 ┐
│ 认知任务 ERP 研究        3          3 份数据可用  今天 10:20      打开 │
│ 睡眠纺锤波分析           1          1 份数据可用  昨天            打开 │
└──────────────────────────────────────────────────────────────────────┘

当前项目数据
┌ 数据文件                 格式       准备状态                  操作 ┐
│ sub-001_oddball.edf      EDF 32ch   待预览                    预览 │
└────────────────────────────────────────────────────────────────────┘
```

### 2.3 视觉要求

1. 项目列表使用紧凑表格按钮，不使用大面积营销卡片。
2. 内部项目开关使用 checkbox，文案为“显示内部/归档项目”。
3. 过滤摘要必须真实，例如“默认显示 12 / 538 个项目；已隐藏内部验收和自动生成项目”。
4. 项目 ID 可小字显示，但不作为第一视觉重点。
5. 删除按钮保持危险态，且不做默认主按钮。

## 3. 波形与预处理同屏

### 3.1 桌面布局

```text
单文件预览与预处理
说明：选择数据后自动加载波形；预览滤波不改写原始数据。

┌──────────────────────────────────────────────────────┬─────────────────────────┐
│ [←] [缩小] [放大] [→] [更新波形] [复位]              │ 预处理参数              │
│ 起点 0.0s | 窗口 10s | 增益 2x | 通道 8 | 预览滤波   │ 参考：平均参考          │
│                                                      │ 参考通道：[ Cz ]        │
│ canvas: EEG waveform                                │ 双极通道对：[ F3-F4 ]   │
│                                                      │ 低切 1 Hz 高切 40 Hz    │
│ 当前窗口 0-10s / 8 通道 / 200Hz / uV / 预览不改原始  │ 陷波 50 Hz              │
│ 事件：stim/target 1.20s ...                         │ [标记坏道] [恢复坏道]   │
│                                                      │ [确认数据准备]          │
└──────────────────────────────────────────────────────┴─────────────────────────┘

当前修改记录
坏道修改 1 条 / 片段剔除 0 条 / 标签 0 条 / 可恢复
```

### 3.2 窄屏布局

```text
工具栏换行
canvas
预处理参数
当前修改记录
确认数据准备
```

### 3.3 控件规范

1. 前后、放大、缩小、复位使用 lucide 图标按钮。
2. 更新波形、确认数据准备使用文字按钮，因为它们是明确命令。
3. 低切、高切、陷波使用数字输入，单位明确。
4. 参考设置使用 select；指定参考和双极通道使用输入框。
5. 预览滤波使用 checkbox/toggle，旁边显示“仅预览”。
6. 坏道标记/恢复是明确操作按钮，不藏在无解释功能区。
7. 任何按钮点击后必须给出当前页面可见反馈，不只靠 toast。

## 4. 文案规范

### 4.1 删除/替换

| 旧文案/模式 | 处理 |
|---|---|
| QC 任务 已生成 | 删除，任务状态不放在客户波形区 |
| 结果文件 13 个 | 删除，除非用户在报告下载页 |
| 状态 可继续准备 | 删除，换成具体下一步 |
| 预览方法可试用 | 删除，所有上线方法都必须测试通过 |
| Reference / CSD | 拆分为预处理参考设置与 CSD 电流源密度计算 |
| beta / preview method | 客户界面禁用 |

### 4.2 推荐文案

1. “预览滤波只作用于当前显示窗口，不改写原始 EEG 文件。”
2. “重参考设置会记录到数据准备方案中，确认后供后续分析复用。”
3. “CSD 电流源密度计算需要通道位置信息；结果是传感器空间变换，不是源定位。”
4. “当前项目暂无数据，请到数据管理上传 EEG 文件。”
5. “已隐藏内部验收和自动生成项目，可通过开关查看。”

## 5. 颜色与状态

1. 主色继续使用治理后的蓝/青体系，避免左侧绿色回潮。
2. 成功、警告、错误状态不得只靠颜色表达。
3. 波形线条使用有限多色轮换，但不得使用 rainbow/jet 作为定量色图。
4. 预览滤波状态使用轻量提示色，不使用警告红。
5. 内部/归档项目使用中性灰或低强调标签，不与真实错误混淆。

## 6. Aesthetic Review v3 检查项

L0 证据：用户截图、当前本地 URL、浏览器截图。
L1 首屏：5 秒内能看到项目/数据/波形/下一步。
L2 结构：项目管理与数据准备职责分离。
L3 文案：客户视角，不出现开发词。
L4 布局：波形与预处理同屏，底部无重复按钮区。
L5 色彩/状态：蓝青主色、状态真实、可访问。
L6 科学边界：单位、采样率、预览边界、CSD 边界可见。
L7 验证：静态检查、浏览器 E2E、截图、像素非空、scroll review。
