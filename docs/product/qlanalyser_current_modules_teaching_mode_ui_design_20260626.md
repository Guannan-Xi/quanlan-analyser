# QLanalyser 当前可用分析方法与教学模式 UI 设计稿

Date: 2026-06-26
Source design: `docs/product/qlanalyser_current_modules_teaching_mode_design_20260626.md`
Status: UI design draft before implementation

## 1. Design Reference Selection

`QLANALYSER_DASHBOARD_REFERENCE_SELECTION`

| Field | Selection |
|---|---|
| Surface | QLanalyser customer workbench: project/data/preparation/method/result/report |
| User role | EEG researcher, lab engineer, CRO analyst, trainee |
| Reference systems | Carbon/Atlassian-style dense B2B workbench, scientific dashboard anti-pattern fixtures, QLanalyser onboarding gate |
| Adopted rules | Clear first landing point, compact action hierarchy, semantic status color, visible focus, no overclaiming charts, contextual onboarding |
| Skipped rules | Marketing hero, decorative gradients, large editorial cards, clinical-device claims |

## 2. Global Shell Wireframe

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ QLanalyser Online · EEG 数据到报告                     [教学模式] [知识库] [记录] [退出] │
├───────────────┬────────────────────────────────────────────────────────────┤
│ QL            │ 当前页面标题                                                │
│ 项目管理       │ 状态条：当前项目 / 当前数据 / 准备状态 / 下一步                  │
│ 数据管理       │                                                            │
│ 数据准备       │ 页面工作区                                                   │
│ 分析任务       │                                                            │
│ 结果查看       │                                                            │
│ 报告交付       │                                                            │
│ 个人中心       │                                                            │
│               │                                                            │
│ 个人中心面板    │                                                            │
└───────────────┴────────────────────────────────────────────────────────────┘
```

Top-right requirements:

- `教学模式` is visible as text + icon because the concept is unfamiliar and important.
- `个人中心` is not only a role label; it remains reachable from sidebar/account panel and must not disappear on project management.

## 3. Data Preparation Wireframe

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ 数据准备  当前数据: teaching_oddball.edf  8 通道 · 250 Hz · 60 s · 36 events │
├───────────────┬────────────────────────────────────────┬───────────────────┤
│ 数据队列       │ 波形预览                               │ 质量提示             │
│ ○ sub-001     │ ┌ 工具条 ────────────────────────────┐ │ 可用通道 8          │
│ ● teaching... │ │ 缩放 平移 复位 增益 通道数 标坏道 剔除片段 添加事件 撤销 │ │ 事件 target/standard│
│               │ └───────────────────────────────────┘ │ 疑似坏道 0          │
│               │ [waveform canvas / SVG / preview]       │                   │
│               │ 已剔除片段以半透明区间显示                 │ 当前修改             │
│               │ 坏道通道在通道名旁显示，可恢复              │ - 坏道: Pz [恢复]    │
│               │ 事件标签在时间轴上显示                    │ - 片段: 12.0-13.5 [恢复] │
├───────────────┴────────────────────────────────────────┴───────────────────┤
│ 重参考设置: (保留原始参考) (平均参考) (指定通道参考) (双极参考)       [确认并进入分析] │
└────────────────────────────────────────────────────────────────────────────┘
```

Interaction requirements:

- Clicking a data row immediately loads waveform/QC.
- `运行质控预览` is not present as a primary action.
- If loading fails, show `重新加载预览`.
- The core waveform tools stay visible with the waveform.
- The right panel lists reversible modifications.

## 4. Analysis Methods Wireframe

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ 当前可用分析方法                                                          │
│ 选择一个分析目标，系统会根据当前数据条件提示可运行的方法。                       │
├─────────────────────┬─────────────────────┬─────────────────────┬──────────┤
│ PSD 频谱与频段功率    │ ERP 事件相关电位     │ TFR 时频分析          │ Multitaper PSD │
│ 输出频谱和频段功率... │ 基于事件分段输出...  │ 查看事件前后功率...    │ 多窗谱估计...   │
│ 输入: 准备后的 EEG    │ 输入: 事件标签        │ 输入: 事件/基线        │ 输入: EEG       │
│ 输出: 图+表+参数      │ 输出: 波形+指标       │ 输出: 时频图+ITC       │ 输出: 频谱表     │
│ [开始分析]           │ [开始分析]           │ [开始分析]            │ [开始分析]      │
├─────────────────────┼─────────────────────┼─────────────────────┼──────────┤
│ Multitaper TFR       │ PAC 相位-振幅耦合    │ Connectivity 连接性    │ CSD 电流源密度计算 │
│ 多窗时频估计...       │ 描述性耦合指标...     │ 描述性连接矩阵...       │ 需要通道位置信息...│
│ 边界: 记录基线参数    │ 边界: 不证明因果       │ 边界: 不证明信息流       │ 边界: 不是源定位    │
│ [开始分析]           │ [开始分析]           │ [开始分析]            │ [开始分析]       │
└─────────────────────┴─────────────────────┴─────────────────────┴──────────┘
```

Card style:

- 8px or less radius unless existing token differs.
- No nested cards.
- Method boundary is visible but concise.
- Status words are data readiness states, not release maturity labels.
- Avoid `预览方法`, `需复核`, `beta`.

## 5. CSD Panel Microcopy

Title:

`CSD 电流源密度计算`

Short body:

`基于通道位置信息计算头皮电位的空间分布变化，用于观察传感器空间的局部活动模式。`

Boundary:

`需要 montage/电极位置；结果不是脑源定位、诊断或治疗建议。`

Missing montage state:

`当前数据缺少通道位置信息，暂不能运行 CSD。请先补充 montage/电极位置。`

## 6. Teaching Overlay Wireframe

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ 页面被半透明蒙版覆盖，目标区域有清晰描边                                      │
│                                                                            │
│                         ┌────────────────────────────┐                     │
│                         │ 教学模式 2/8               │                     │
│                         │ 单击这份教学 EEG 数据。系统会自动载入波形和基础质量信息。 │
│                         │ [上一步] [下一步] [结束教学] │                     │
│                         └────────────────────────────┘                     │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

Overlay rules:

- The callout must not cover the exact target.
- Buttons must fit on mobile and desktop.
- Pressing Escape exits teaching mode.
- Step text must be under 48 Chinese characters when possible.
- The overlay must include `教学数据` boundary on demo surfaces.

## 7. Color and Token Direction

Use semantic roles instead of page-specific raw color decisions:

| Role | Use |
|---|---|
| `surface.page` | page background |
| `surface.panel` | workbench panels |
| `text.primary` | primary text |
| `text.secondary` | explanatory text |
| `border.subtle` | panel/card separation |
| `accent.action` | primary action and selected data |
| `status.success` | completed/ready |
| `status.warning` | unmet condition/recoverable issue |
| `status.error` | failure requiring user action |
| `status.info` | teaching/demo context |

Color治理 requirements:

- The sidebar must not remain visually dominated by a single green hue if the rest of the product uses a different professional palette.
- Do not use green as the only meaning carrier.
- Selected, success, warning, error, and teaching/demo states must be distinguishable by text/icon and color.
- Focus rings are visible in keyboard path.

## 8. Responsive Rules

Desktop:

- Data preparation should show list, waveform, and modification summary in one viewport.
- Method cards can use a 4-column or responsive dense grid.

Tablet:

- Data list and modification summary can collapse into tabs, but waveform toolbar remains attached to waveform.

Mobile:

- Teaching overlay callout is bottom sheet style.
- Method cards become one column with compact input/output rows.
- Topbar actions wrap without overlapping title.

## 9. UI Acceptance Checklist

| Gate | Pass condition |
|---|---|
| First landing point | User can identify next action within 3 seconds. |
| Current methods | 8 method cards, no data-prep duplicate, no preview/beta wording. |
| Data prep | Waveform and core tools visible together. |
| Teaching mode | Overlay + sample data + step progress visible. |
| Navigation | Personal center and teaching mode reachable from project management. |
| State coverage | empty/loading/error/success/focus/narrow/wide screenshots. |
| Scientific boundary | CSD/PAC/Connectivity visible copy avoids overclaim. |
| Accessibility | keyboard focus visible; reduced-motion respected; buttons do not overflow. |
