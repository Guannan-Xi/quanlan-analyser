# QLanalyser UI Product Delivery Design

Version: v0.2
Date: 2026-06-22
Owner: 07 QLanalyser Product Owner
Status: living design source of truth

## 1. Product Goal

QLanalyser must feel like a production scientific SaaS workspace for EEG and research data analysis. It is not a demo, script launcher, method gallery, or internal validation dashboard.

The visible customer path is:

1. Project management.
2. Project-scoped data management.
3. Data preparation and preprocessing.
4. Analysis task execution.
5. Result review.
6. Report delivery.
7. Review and validation.
8. User center for account, balance, recharge, invoices, permissions, security, notifications, preferences, and help.

Every UI change must preserve this path and remove anything that distracts from the user's current job.

## 2. User Aesthetic And Interaction Standard

- Calm B2B scientific product, not marketing, not decorative, not a toy dashboard.
- Dense but readable information. Prefer tables, master-detail panels, compact status chips, and purposeful empty states over scattered cards.
- One information item appears once. Do not repeat the same workflow in navigation, header, cards, and bottom blocks.
- One page has one primary job. Do not mix project CRUD, analysis templates, billing, and validation evidence on one page.
- Controls must be real. If a button is visible, it must work or explain the missing prerequisite in plain Chinese.
- Internal words must not reach customers. Do not show raw IDs, `active`, `acceptance-label`, `Persistence Gate`, `runner`, `manifest`, `gate`, or debug labels as primary user copy.
- Layout must not jump vertically when selecting project/data or switching pages.
- Blank space must be intentional. A large blank right area is a defect unless it is a meaningful empty state with one clear action.

## 3. Design Tokens

Use these values for customer workspace pages. New raw values need a documented exception in this file.

### 3.1 Layout Tokens

| Token | Value | Usage |
| --- | --- | --- |
| `--app-shell-sidebar-width` | `248px` | Desktop left navigation width |
| `--app-shell-topbar-height` | `72px` | Top bar minimum height |
| `--workspace-max-width` | `1440px` | Maximum content width |
| `--workspace-padding-x` | `24px` desktop, `16px` <= 900px | Main page side padding |
| `--section-gap` | `20px` | Gap between primary page sections |
| `--panel-gap` | `16px` | Gap inside two-column layouts |
| `--control-height` | `38px` | Default input/button height |
| `--compact-row-height` | `48px` | Dense table/list row minimum |
| `--detail-panel-min-width` | `360px` | Right detail panel minimum |

### 3.2 Visual Tokens

| Token | Value | Usage |
| --- | --- | --- |
| `--surface-page` | `#f6f8fb` | Workspace background |
| `--surface-panel` | `#ffffff` | Panels, tables, forms |
| `--surface-subtle` | `#f8fafc` | Empty states and nested neutral areas |
| `--border-subtle` | `#dbe3ef` | Panel and table borders |
| `--border-strong` | `#b7c4d8` | Selected object borders |
| `--text-primary` | `#172033` | Main text |
| `--text-secondary` | `#526174` | Secondary text |
| `--text-muted` | `#7b8797` | Hints |
| `--brand-primary` | `#2457d6` | Primary actions and selected nav |
| `--status-success` | `#157347` | Success text/chip |
| `--status-warning` | `#a15c00` | Warning text/chip |
| `--status-error` | `#b42318` | Error text/chip |
| `--radius-panel` | `8px` | Panels and repeated items |
| `--radius-control` | `6px` | Buttons, inputs, chips |
| `--shadow-panel` | `0 8px 24px rgba(17, 32, 56, 0.08)` | Only for floating/modals; normal panels use border only |
| `--focus-ring` | `0 0 0 3px rgba(36, 87, 214, 0.24)` | Keyboard focus |

### 3.3 Typography Tokens

| Token | Value | Usage |
| --- | --- | --- |
| `--font-family-ui` | system UI stack | All app UI |
| `--font-size-page-title` | `22px` | Page h1 |
| `--font-size-section-title` | `18px` | Panel h2 |
| `--font-size-body` | `14px` | Default text |
| `--font-size-caption` | `12px` | Hints, metadata |
| `--line-height-body` | `1.55` | Readable Chinese UI text |
| `--font-weight-title` | `700` | Page and section titles |
| `--font-weight-label` | `600` | Field labels and table heads |

No page may use viewport-scaled font sizes. Letter spacing must stay `0`.

## 4. App Shell And Navigation

### 4.1 Canonical Navigation

The customer left navigation must contain exactly these primary entries in this order:

1. 项目管理: `data-view="dashboard"`
2. 数据管理: `data-view="storage"`
3. 数据准备: `data-view="analysis"`
4. 分析任务: `data-view="workflow"`
5. 结果查看: `data-view="statistics"`
6. 报告交付: `data-view="publication"`
7. 评审验证: `data-view="journey"`
8. 个人中心: `data-view="userCenter"`

Do not add standalone 充值、发票、余额、方法工作台、科研级流程, or demo links to this navigation.

### 4.2 Navigation State

- 项目管理 and 个人中心 are always enabled.
- 数据管理 requires selected project.
- 数据准备 requires selected project and selected data.
- 分析任务 requires selected project and prepared or previewable data.
- 结果查看 requires at least one result or fixture result in demo mode.
- 报告交付 requires at least one result/report package.
- 评审验证 requires evidence or a runnable validator.

If an item is locked, clicking it must show feedback such as `请先选择项目` or `请先上传或选择数据`. Do not silently ignore clicks.

## 5. Project Management Page

Project management only contains project CRUD/selection and selected-project data preview. It must not contain method workbench, analysis templates, scientific workflow cards, bottom real-analysis-flow blocks, billing, recharge, invoices, or expanded data lists before project selection.

Use a master-detail layout:

```text
.project-data-master-detail
  grid-template-columns: minmax(520px, 1fr) minmax(360px, 420px)
  gap: 16px
  align-items: start
  collapse to 1 column at max-width: 1100px
```

Project list required columns:

- 项目名称: flexible min `220px`
- 数据: `88px`
- 状态: `96px`
- 最近更新: `140px`
- 操作: `148px`

Project row rules:

- Row click selects project.
- Selected row uses `data-selected="true"` and selected background/border.
- Primary action is `进入项目`.
- Rename/archive/delete are secondary compact actions, not large primary buttons.
- Raw project ID may appear only as copyable metadata in detail, never as primary name.

User-facing status vocabulary:

| Internal | User text |
| --- | --- |
| `active` | 进行中 |
| `created` | 未开始 |
| `ready` | 可分析 |
| `processing` | 处理中 |
| `completed` | 已完成 |
| `warning` | 有提醒 |
| `error` | 需处理 |
| `archived` | 已归档 |

Forbidden on screen: `Persistence Gate`, `Acceptance project`, `active`, raw `proj_...` as a title.

## 6. Data Management Page

Data management is project-scoped. It only appears as a working page after a project is selected.

Allowed functions:

- Upload EEG data into the current project.
- List all files under the selected project.
- Select one data file.
- Preview metadata and waveform summary.
- Edit display name.
- Edit plain-language notes.
- Manage labels.
- Archive/delete data with confirmation.
- Enter data preparation for selected data.

Forbidden functions:

- Analysis method cards.
- Scientific workflow cards.
- Billing or invoice controls.
- `替换文件` unless it is a real versioned replacement flow with explicit source-data consequences.

Layout:

```text
.data-management-layout
  grid-template-columns: minmax(560px, 1fr) minmax(360px, 440px)
  gap: 16px
```

If no project is selected:

- Show centered empty state: `请先选择项目`.
- One action: `返回项目管理`.
- Hide upload input and data table.

Upload selectors:

- File input: `#real-eeg-file`
- File name text: `#realEegFileName`
- Upload action: `[data-real-action="upload-eeg"]`

## 7. Data Preparation Page

Data preparation is a systematic preprocessing workspace. It is not a template selector and not a generic analysis page.

Required order:

1. Selected project/data context.
2. Data preview and metadata.
3. Segment selection and deletion/exclusion.
4. Label viewing/editing.
5. Bad-channel and QC review.
6. Preprocessing parameters.
7. Task summary.
8. Submit preparation task as the final block.

Rules:

- The page must not move upward or change scroll position unexpectedly after selecting data or toggling panels.
- Use two columns only when both columns contain meaningful content.
- Submit block uses `data-testid="data-preparation-submit-last"` and must remain visually last.
- Every disabled action must show a prerequisite reason.

## 8. Analysis, Results, Reports, Review

### 8.1 Analysis Task Page

Allowed current modules:

- QC as data quality review, not as a scientific analysis method.
- PSD / Bandpower.
- ERP.
- TFR.
- PAC.

Future methods such as Connectivity, CSD, and Source localization must not appear as actionable modules unless runner, route, validator, and report artifacts are product-ready.

### 8.2 Results Page

Results must show figures, tables, parameters, warnings, provenance, and non-diagnostic/research-use boundary. It must not contain report download controls or overstate scientific conclusions.

### 8.3 Reports Page

Reports must show report package list, preview/open action, download action, included artifact summary, creation time, and validator status. Download buttons must work through visible browser clicks.

### 8.4 Review Page

Review page contains product validation and reviewer gates. It must not be a dumping ground for manifest paths, internal script evidence, or repeated workflow teaching.

## 9. User Center

User center contains all account and finance functions. The scientific workspace must not show billing widgets except when a paid task is blocked, in which case the action links to user center.

Required sections:

- Account overview: name, email, organization, role, account state.
- Permissions: accessible projects, data scope, review role.
- Security: login method, password/device placeholder, logout.
- Balance and recharge: balance, quota, recharge amount, consumption records.
- Orders and invoices: invoice profile, invoice request, invoice history, order/payment records.
- Notifications: task reminders, review reminders, invoice reminders.
- Preferences: language, theme, default landing page, notification frequency.
- Help and feedback.

Layout:

```text
.user-center-product-grid
  grid-template-columns: minmax(360px, 0.9fr) minmax(440px, 1.1fr)
  gap: 16px
  align-items: start
  collapse to 1 column at max-width: 1050px
```

Left column: account, permissions, security.

Right column: balance, recharge, orders/invoices, notifications, preferences, help.

## 10. Copywriting Rules

Use plain Chinese:

- `备注已保存`
- `数据已上传`
- `请先选择项目`
- `请先上传或选择数据`
- `报告已生成，可以下载`
- `当前文件可进入数据准备`

Do not show:

- `acceptance-label`
- `Persistence Gate`
- `durable epoch set`
- `runner evidence`
- `manifest`
- `gate`
- `active`
- `status`
- `替换文件` without a product-defined replacement flow

## 11. Code-Level Review Hooks

Every UI slice must identify:

- `code_files_reviewed`
- `component_tree_summary`
- `state_model_review`
- `layout_risk_review`
- `token_usage_review`
- `interaction_logic_review`
- `element_interference_risks`
- `code_level_fix_plan`
- `visual_validation_required`
- `post_fix_evidence`

Primary files:

- `frontend/index.html`: semantic page and control structure.
- `frontend/app.js`: state model, render functions, click handlers, status mapping, feedback.
- `frontend/styles.css`: layout, tokens, responsive behavior, selected/disabled/focus states.

## 12. Acceptance Criteria

### 12.1 Static Acceptance

- No `workspaceProjectSelect`, `workspaceFileSelect`, or `workspacePlanSelect` in the customer UI.
- No bottom `quick-real-flow-panel` on project management.
- No standalone customer nav item for billing or invoice.
- No user-facing text containing forbidden internal words listed in section 10.
- No duplicate `科研级流程` or method workbench card on project management.
- `data-testid="data-preparation-submit-last"` exists and appears after preparation settings.

### 12.2 Browser Acceptance

Browser click tests must cover:

1. Open review URL with default account.
2. Project management renders project panel, not dropdown-first selection.
3. Clicking a project selects it and fills the detail panel.
4. Data list is hidden or empty-state-only before project selection.
5. Upload control appears only in project-scoped data management.
6. Data preparation does not jump upward when opened.
7. User center contains balance, recharge, invoices, orders, permissions, and preferences.
8. Locked or unavailable controls provide feedback.

### 12.3 Visual Acceptance

Required screenshot/state coverage:

- Desktop default.
- Desktop dense project list.
- Desktop selected project and data detail.
- Empty project/data state.
- Upload success or selected-file state.
- Error/disabled state.
- Narrow viewport <= 390px.
- Keyboard focus state.

Visual fail conditions:

- Right side large blank area without useful empty state.
- Repeated cards that say the same thing as navigation.
- Misaligned columns or overlapping controls.
- Text overflow in buttons, chips, table cells, or nav.
- More than one primary action competing in the same panel.
- Finance content visible inside project/data/analysis pages.

## 13. Implementation Rule

Future UI work must read this document before editing. Conversation notes are not the implementation source. If user feedback changes the design, update this document first, read it back, then modify code.
