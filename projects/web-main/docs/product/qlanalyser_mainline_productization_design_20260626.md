# QLanalyser Mainline Productization Detailed Design

Date: 2026-06-26
Source requirements: `docs/product/qlanalyser_mainline_productization_requirements_20260626.md`
Status: implementation design contract

## 1. Design Goal

Build a polished and professional EEG research workbench where the user always understands:

- what data is selected
- what can be previewed now
- what edits have been made
- what analysis modules are currently available
- which methods require review
- what result/report artifacts can be trusted for research reference

The product must feel like a scientific workbench, not a developer console or method demo page.

## 2. Design References And Fit

Reference systems used as radar, not as copy targets:

| Source | Adopted rules | Skipped rules |
|---|---|---|
| IBM Carbon | Dense scientific dashboard hierarchy, subdued surfaces, semantic status colors | Carbon branding and component implementation |
| Fluent 2 | Enterprise navigation, focus states, restrained color, icon clarity | Windows-specific platform metaphors |
| Primer | Developer-adjacent clarity for tables, status badges, compact cards | GitHub visual identity |
| Arco / Semi | Chinese enterprise admin density and form conventions | Library dependency or direct component adoption |
| Local design gates | Design tokens, state coverage, scientific color semantics, forbidden claim scan | Any rule conflicting with the current product scope |

Target maturity: `polished and professional`.

## 3. Information Architecture

Canonical customer IA:

```text
Project Management
Data Management
Data Preparation
Analysis Tasks
Result Review
Report Delivery
Personal Center
```

Admin-only IA:

```text
Operations Home
Task Operations
Finance
System Status
Quality Check
```

Method review/testing IA:

```text
Analysis Method Center
Current Available Modules
Reproducibility Details
Preview Methods, Needs Review
Internal Module Lab Details
```

Customer-facing labels must use Chinese task language:

| Surface | Preferred label | Avoid as main label |
|---|---|---|
| Method list | 当前可用模块 | Module Lab |
| Method review page | 分析方法中心 | 方法模块实验室 |
| Technical details | 复现信息 | workflow / runner / API |
| Advanced status | 预览方法，需复核 | beta only |
| Report package | 报告材料包 | artifact bundle |

## 4. Main Workbench Wireframe

```text
+--------------------------------------------------------------------------------+
| Top bar: QLanalyser Online · Project to Report Workbench                        |
+--------------+-----------------------------------------------------------------+
| Left nav     | Page title and current context                                  |
|              | Project: <name>  Data: <file>  Preparation: <status>             |
| Project      +-----------------------------------------------------------------+
| Data         | Step strip                                                       |
| Preparation  | Upload -> Preview -> Edit -> Analyze -> Result -> Report         |
| Analysis     +-----------------------------------------------------------------+
| Results      | Main task area                                                   |
| Report       | - selected object                                                |
|              | - primary action                                                  |
|              | - secondary details folded                                        |
+--------------+-----------------------------------------------------------------+
```

Design rules:

- Left navigation uses neutral navy/blue active state, not green.
- The active item must be clear in grayscale.
- Each page has one main object and one primary action.
- Internal logs, IDs, and reproducibility details are folded.

## 5. Data Preparation Page Wireframe

```text
+--------------------------------------------------------------------------------+
| Current Data: sample.edf | 8 channels | 250 Hz | 60 s | Preview loaded          |
+--------------------+-------------------------------+---------------------------+
| Data queue         | Waveform preview               | Current edit record       |
| - sample.edf       | channel/time viewport          | Bad channels              |
| - another.edf      | visible selected segment       | Excluded segments         |
|                    | event markers                  | Event label edits         |
+--------------------+-------------------------------+---------------------------+
| Quality hints      | Bad channel / segment / event tools on same page           |
+--------------------+-------------------------------+---------------------------+
| Primary: Confirm data preparation      Secondary: Reload preview / Details      |
+--------------------------------------------------------------------------------+
```

Required interactions:

- Clicking a data row selects and previews it.
- Bad-channel action appears near channel list or waveform.
- Segment action appears near waveform time selection.
- Event label action appears near marker list.
- Restore action is visible in the edit record.
- Confirm action is disabled until preview state is known.

## 6. Current Available Modules Design

This is the required main workbench structure after merging the 02 methods.

```text
Current Available Modules
These modules can be used with the selected project data. Preview methods require review before delivery.

[Data preparation and quality check]     status: Preparation step
  Use before analysis. Produces quality summary, metadata, preview, and preparation record.

Available analysis
[PSD / Bandpower]                         status: Available
[ERP / P300]                              status: Available, requires events

Preview methods, needs review
[TFR / ERSP / ITC]                        status: Preview, needs review
[Multitaper PSD]                          status: Preview, needs review
[Multitaper TFR]                          status: Preview, needs review
[Reference / CSD]                         status: Preview, needs review
[PAC / CFC]                               status: Preview, needs review
[Connectivity]                            status: Preview, needs review
```

Each card must show:

- user-facing method name
- when to use it
- prerequisite
- output materials
- status badge
- safe interpretation boundary

Each card must not show by default:

- module id
- workflow id
- runner name
- raw API route
- acceptance/gate/debug wording

Technical detail pattern:

```text
<details class="reproducibility-details">
  <summary>Reproducibility details</summary>
  backend module, workflow, parameters, task id, artifact ids
</details>
```

## 7. Module Status Copy

| Entry | User title | Prerequisite | Output | Status copy |
|---|---|---|---|---|
| QC | 数据准备与质量检查 | EEG file selected | preview, metadata, quality hints | Preparation step |
| PSD | PSD / Bandpower | continuous EEG | spectrum and bandpower tables | Available |
| ERP | ERP / P300 | event markers | waveforms and event metrics | Available, requires events |
| TFR | TFR / ERSP / ITC | event markers and baseline | time-frequency charts | Preview, needs review |
| Multitaper PSD | Multitaper PSD | continuous EEG | multitaper spectrum | Preview, needs review |
| Multitaper TFR | Multitaper TFR | event markers and baseline | multitaper time-frequency charts | Preview, needs review |
| Reference / CSD | Reference / CSD | montage/reference review | transformed signal outputs | Preview, needs review |
| PAC | PAC / CFC | defined frequency bands | comodulogram and tables | Preview, no causal claim |
| Connectivity | Connectivity | reviewed preprocessing/reference | connectivity matrix/edges | Preview, no causal claim |

Chinese main-card copy must be user oriented. Example:

```text
PAC / CFC
查看相位-振幅耦合的描述性图表和表格。结果用于研究参考，不能单独解释为因果关系。
状态：预览方法，需复核
```

## 7.1 Whole-Product Copy Governance

All visible copy follows the user task layer first:

```text
User object -> user action -> user result -> review boundary
```

Preferred replacements:

| Avoid in visible UI | Use instead |
|---|---|
| 方法模块实验室 / 方法开发测试试验台 | 分析方法库 |
| beta / Beta 方法 | 预览方法，需复核 |
| workflow / runner / picker | 分析流程 / 选择方法 |
| 真实后端任务 | 分析任务 |
| 参数回显 | 参数记录 |
| 产物证据 | 结果文件 |
| API 服务 | 服务连接 |
| 分析任务工作台 | 分析任务 |
| 方法分支 | 选择分析方法 |
| 项目 ID | 项目编号 |
| Research Module / Workflow contract | 分析方法预览 / 输入与输出 |
| 测试输入数据 / 合成科研测试数据 | 示例输入数据 / 合成科研示例数据 |

Internal attributes, dataset IDs, workflow IDs, and backend module names are allowed only when hidden from the user and required by the API contract.

## 7.2 Main Workbench Method Entries

The main workbench has two adjacent method surfaces:

- `当前可用模块`: discovery and boundary explanation for 9 entries.
- `选择分析方法`: direct actions for methods that create an analysis task.

Design rules:

- QC stays in the data-preparation path. It is visible in `当前可用模块`, but not rendered as a duplicate analysis button.
- Stable methods use `开始 ... 分析`.
- Preview methods use `试用 ...（需复核）`.
- Multitaper PSD and Multitaper TFR are separate user actions even though the backend module contract remains `multitaper_psd_tfr`.
- Result review stores and displays the split user-facing method key, so users can tell which method they ran.

## 8. Visual System

### 8.1 Token layers

Primitive tokens:

- `--ql-blue-700`
- `--ql-blue-500`
- `--ql-gray-900`
- `--ql-gray-700`
- `--ql-gray-100`
- `--ql-amber-600`
- `--ql-red-600`
- `--ql-green-700`

Semantic tokens:

- `--ql-bg-canvas`
- `--ql-bg-panel`
- `--ql-text-primary`
- `--ql-text-secondary`
- `--ql-border-subtle`
- `--ql-action-primary`
- `--ql-nav-active-bg`
- `--ql-nav-active-text`
- `--ql-status-success`
- `--ql-status-warning`
- `--ql-status-error`
- `--ql-status-info`
- `--ql-status-preview`
- `--ql-focus-ring`

Component tokens:

- `--ql-sidebar-bg`
- `--ql-sidebar-item-bg-active`
- `--ql-sidebar-item-text-active`
- `--ql-button-primary-bg`
- `--ql-button-secondary-border`
- `--ql-card-border`
- `--ql-method-status-available-bg`
- `--ql-method-status-preview-bg`
- `--ql-table-row-selected-bg`

### 8.2 Color governance

- Navigation active state: navy/blue, not green.
- Success: green only when an operation is completed or validated.
- Warning/review/preview: amber or coral family, not success green.
- Error: red family with text and icon, not color-only.
- Neutral status: gray/blue-gray.

### 8.3 Button governance

- One primary button per task surface.
- Secondary actions use ghost/icon/text buttons with clear hierarchy.
- Automatic system actions must not be primary buttons.
- Download/audit/details actions are grouped under report delivery or details, not mixed into data preparation main action.

### 8.4 Typography and spacing

- Compact dashboards use moderate headings, not hero-scale headings.
- Button text must fit at mobile and desktop widths.
- Cards use radius 8px or less unless existing design requires otherwise.
- No cards inside cards for page sections.
- Fixed-format controls use stable dimensions to prevent layout shift.

## 9. State Design

Each core surface must provide these states:

| State | Required behavior |
|---|---|
| Empty | says what is missing and next action |
| Loading | names the current operation |
| Error | says what failed, what is affected, and recovery action |
| Success | confirms result and next action |
| Disabled | gives reason |
| Permission denied | explains access boundary |
| Partial result | shows what is available and what is missing |
| Stale data | offers refresh/re-run |
| Long task | shows stage and retry/background policy |
| Reduced motion | avoids essential motion-only feedback |

## 10. Scientific Chart Design

Chart gate:

- waveform: channel labels, units, time axis, filter/reference context
- TFR/heatmap: time axis, frequency axis, colorbar label, baseline/normalization
- PAC/connectivity: metric definition, null/surrogate or review boundary, edge/color semantics
- source-like maps: no source claim without source model evidence

Color selection:

- sequential for power/amplitude/MI
- diverging for baseline-relative changes
- cyclic for phase
- categorical for conditions/groups
- binary status for pass/fail
- uncertainty overlay for confidence/masks

Do not use rainbow/jet by default.

## 11. Page Copy Design

All pages must pass this copy lens:

| Page | User question to answer | Copy rule |
|---|---|---|
| Project management | Which project am I working on? | project-first, no system internals |
| Data management | Which data file can I use? | row click selects and previews |
| Data preparation | What needs fixing before analysis? | edit/restore language |
| Analysis tasks | What can I run now? | current modules and prerequisites |
| Result review | What did the analysis produce? | method, source data, quality hints |
| Report delivery | What can I deliver/download? | package, report, reproducibility record |
| Personal center | What account/finance settings matter? | separate from analysis flow |
| Admin pages | What operation needs attention? | admin language allowed, customer data protected |

## 12. Accessibility

- Keyboard focus must be visible.
- Buttons and controls need accessible names.
- Status text cannot rely on color only.
- Errors must be announced or reachable by screen readers.
- Tables/cards must retain logical reading order on narrow screens.

## 13. Implementation Plan

Slice order:

1. Current available modules and copy contract.
2. Auto-preview E2E rewrite and UI behavior cleanup.
3. Reversible edit UI and processing-record contract.
4. Sidebar/nav/color token cleanup.
5. Formal E2E matrix and scientific/report release packet.

Each slice must update tests before or with implementation. No slice may claim completion without evidence paths.

## 14. Rollback

- If current modules merge causes failures, hide only the new preview cards behind a visible "Preview methods temporarily unavailable" state, not behind a silent removal.
- Stable PSD/ERP path must remain accessible.
- Module Lab grouped-method stack must remain runnable for diagnosis.
- Router, Headroom, IPC, and gateway configuration are out of scope.
