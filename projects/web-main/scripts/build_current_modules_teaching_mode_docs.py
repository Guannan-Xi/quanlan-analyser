from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "docs" / "product"
EVIDENCE_ROOT = ROOT / "work" / "release_evidence" / "07-full-product-e2e-pdca" / "12_current_modules_teaching_mode"
DEEPSEEK_DIR = EVIDENCE_ROOT / "deepseek"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


DATE = "2026-06-26"
REPO = r"D:\Quanlan\Codes\Python\quanlan-analyser-official"
GENERATED_AT = datetime.now(timezone.utc).isoformat()


requirements = f"""
# QLanalyser 当前可用分析方法、教学模式与科研工作流修复需求

Date: {DATE}
Owner: 07-PM / QLanalyser product acceptance
Repo: `{REPO}`
Status: requirements source before implementation
Supersedes where conflicting:

- `docs/product/qlanalyser_mainline_productization_requirements_20260626.md`
- `docs/product/qlanalyser_product_wide_ux_repair_spec_20260625.md`
- any chat-only summary about current modules, reference/CSD, teaching mode, or preview wording

This document is the requirement source for this slice. Implementation, review, DeepSeek logic review, and end-to-end testing must read this file and its matching design/UI/test documents before changing product behavior. Requirements must not be transferred only through conversation.

## 1. Product Positioning

QLanalyser is a non-medical EEG research analysis and CRO-support product. The product may help researchers organize projects, prepare EEG data, run reproducible signal-analysis methods, review figures/tables, and export records. The product must not imply diagnosis, treatment, clinical decision support, source localization, brain-region activation, causality, information flow, population inference, or statistical significance unless the specific method and evidence support that claim.

The visible product must feel like a formal research EEG platform, not a development lab or function dump. Customer-facing copy must describe the researcher task, input, output, limitation, and recovery path.

## 2. Requirement Trace

| ID | Requirement | Rationale | Acceptance evidence |
|---|---|---|---|
| R-IA-01 | `当前可用模块` must be renamed and treated as `当前可用分析方法`. | The section must contain analysis/computation methods, not preparation dependencies. | UI screenshot, DOM/copy scan, method-card inventory JSON. |
| R-IA-02 | Data preparation, QC, bad channels, bad segments, event edits, and re-referencing must live in `数据准备/预处理`. | These are preparation steps before analysis, not analysis methods. | Data-preparation UI screenshot and action-path test. |
| R-IA-03 | The visible analysis method list must contain only true analysis/computation methods: PSD, ERP, TFR, Multitaper PSD, Multitaper TFR, PAC, Connectivity, CSD 电流源密度计算. | Prevents duplicated `数据准备` and user confusion. | 8-card visible-fields acceptance. |
| R-COPY-01 | Remove all visible `预览方法`, `可试用`, `需复核`, `beta`, and `Reference / CSD` wording from customer-facing product surfaces. | User requires all public methods to be tested before release and not presented as half-finished. | Forbidden-copy scan across `frontend/*.html`, `frontend/app.js`, customer-visible module surfaces. |
| R-COPY-02 | Keep scientific boundary wording while removing preview/beta labels. | Removing preview language must not create overclaim risk. | Forbidden-claim scan and DeepSeek/Codex review adoption record. |
| R-CSD-01 | The user-facing method name is `CSD 电流源密度计算`. | CSD is not a reference-setting method and must not be shown as `Reference / CSD`. | Method-card text, backend display name if exposed, report method text where applicable. |
| R-CSD-02 | CSD copy must explain it as a sensor-space/scalp surface spatial filtering result requiring channel-location information, not source localization. | Avoids overclaim and researcher misunderstanding. | CSD method card, help text, output boundary scan. |
| R-REF-01 | Re-reference settings belong in preprocessing with modes: 保留原始参考、平均参考、指定通道参考、双极参考. | Reference changes alter the signal before downstream methods; they are a preprocessing decision. | Data-preparation UI and parameter manifest evidence. |
| R-REF-02 | Re-reference actions must preserve reversibility and processing record. | Researchers need provenance and must be able to recover decisions. | Processing-record JSON and UI restore test. |
| R-NAV-01 | `个人中心` must remain visible and reachable globally, including project-management pages. | The user noticed it disappeared in project management. | Browser click path from project management to personal center. |
| R-NAV-02 | A top-right `教学模式` entry must be globally visible for customer role pages. | Teaching mode is a core onboarding path, not hidden documentation. | Browser screenshot and click path from cover/project page. |
| R-TEACH-01 | Teaching mode must preload a synthetic EEG dataset with events and channel-location information. | A first-time user must be able to complete the full flow without uploading data. | Demo dataset API, file manifest, checksum, synthetic-data declaration. |
| R-TEACH-02 | Teaching mode must provide mask + step提示 guidance. | The user explicitly requested guided overlay onboarding. | Overlay screenshot sequence, step count, focus target evidence. |
| R-TEACH-03 | Teaching mode must not pollute real project data or report outputs. | Demo learning state must remain separable from real project work. | Demo project/file IDs, storage manifest, UI badge, export boundary check. |
| R-TEACH-04 | Teaching mode must guide the full flow: enter project, select sample data, inspect waveform/QC, prepare data, run methods, review results, export report. | Onboarding must teach real critical tasks, not a welcome screen. | End-to-end teaching-mode trace and screenshots. |
| R-QC-01 | Selecting a data record must automatically show waveform/quality preview; no separate `运行质控预览` primary button is allowed. | Required system work should not be pushed to the user as an extra action. | Data-click auto-preview E2E. |
| R-QC-02 | Bad-channel exclusion, segment exclusion, event edits, and reference decisions must be operable and recoverable. | Destructive scientific edits require reversibility. | Reversible-edit test and processing-record JSON. |
| R-UI-01 | Waveform preview and its correction tools must be visible in the same working area without forcing the user to scroll down for core actions. | Context-dependent tools must stay near the waveform. | Desktop and mobile scroll review screenshots. |
| R-UI-02 | Remove duplicate cards that repeat project/data/next-step information without adding actions. | Reduces noise and restores task hierarchy. | Surface inventory before/after and screenshot review. |
| R-UI-03 | Buttons are only for user decisions; system records, audit files, and processing plans are automatic or placed under secondary menus. | Avoids internal workflow leakage. | Button inventory and copy review. |
| R-VIS-01 | UI colors, spacing, hierarchy, focus states, and status colors must follow knowledge-base design-token guidance. | The user requested UI color治理 and professional scientific product feel. | Design-token/color audit JSON and screenshots. |
| R-VIS-02 | Scientific figures must use appropriate colormaps, labels, legends/colorbars, units, and non-overclaiming titles. | Analysis outputs must follow scientific plotting norms. | Scientific figure audit and source-comparison outputs. |
| R-E2E-01 | All core functions, including cover/login, backend/admin, project management, data preparation, analysis methods, result review, report delivery, and teaching mode, must be tested end to end with synthetic EEG data. | The release must be system-level, not single-page. | Full E2E acceptance packet. |
| R-DEEPSEEK-01 | DeepSeek must review researcher workflow logic and Chinese customer-facing operation logic where available. | User asked for DeepSeek logic review. | DeepSeek result file or explicit unavailable evidence with prompt packet. |

## 3. Information Architecture

### 3.1 Primary customer navigation

The customer product navigation is:

1. 项目管理
2. 数据管理
3. 数据准备
4. 分析任务
5. 结果查看
6. 报告交付
7. 个人中心

Top-right global actions:

- 教学模式
- 知识库
- 操作记录
- 退出

`个人中心` can remain in left navigation and must also stay reachable from the account panel. `教学模式` must be a top-right visible action so first-time users can find it from any customer page.

### 3.2 Data preparation / preprocessing scope

This scope includes:

- Data overview and waveform preview.
- Basic QC status and channel/event/duration metadata.
- Bad-channel mark and restore.
- Bad-segment mark and restore.
- Event label add/edit/restore.
- Re-reference settings:
  - 保留原始参考
  - 平均参考
  - 指定通道参考
  - 双极参考
- Processing record, parameter manifest, and reversible edit log.

It does not belong in `当前可用分析方法` as a method card.

### 3.3 Current available analysis methods

The visible section contains exactly these analysis methods:

| Group | User-facing name | Backend/module contract | Required visible boundary |
|---|---|---|---|
| 频谱 | PSD 频谱与频段功率 | `psd` | Descriptive frequency-domain metrics only. |
| 事件相关 | ERP 事件相关电位 | `erp` | Requires events; no clinical interpretation. |
| 时频 | TFR 时频分析 | `tfr` | Requires event/time-frequency settings and baseline clarity. |
| 时频 | Multitaper PSD | `multitaper_psd_tfr` with PSD family | Multi-taper spectrum estimate; document bandwidth/window parameters. |
| 时频 | Multitaper TFR | `multitaper_psd_tfr` with TFR family | Multi-taper time-frequency estimate; document event/baseline parameters. |
| 耦合 | PAC 相位-振幅耦合 | `pac` | Descriptive coupling metric; no causality claim. |
| 连接 | Connectivity 连接性分析 | `connectivity` | Descriptive association matrix; no information-flow or causality claim. |
| 空间滤波 | CSD 电流源密度计算 | backend id may remain `reference_csd` with `reference_mode=csd` | Requires channel locations; not source localization. |

Backend compatibility rule: existing stored task IDs and module IDs may remain stable. User-facing names, cards, help text, and route labels must use the new product language.

## 4. Teaching Mode Requirements

Teaching mode must be a real guided workflow:

- Entry: top-right `教学模式`.
- Dataset: deterministic synthetic oddball EEG EDF with events and montage/channel locations.
- Visual mark: clear `教学数据` badge and non-real-data boundary.
- Overlay style: mask plus focused target, step title, concise instruction, `上一步`, `下一步`, `结束教学`, progress count.
- User path:
  1. Open teaching mode.
  2. Load sample project and sample EEG.
  3. Select sample data and see waveform/QC automatically.
  4. Mark and restore at least one bad channel or segment.
  5. Confirm data preparation.
  6. Run at least PSD, ERP, CSD, PAC, Connectivity, TFR/Multitaper where supported by fixture.
  7. Review results and report package.
  8. Exit teaching mode and return to normal project.

Teaching mode must not:

- claim the synthetic result is scientific evidence;
- mix demo files into real customer projects without explicit teaching badge;
- hide personal center or normal navigation;
- require users to upload their own data.

## 5. Copy Rules

Customer-visible copy must use user task language:

- Use: `当前可用分析方法`, `数据准备`, `重参考设置`, `CSD 电流源密度计算`, `教学模式`, `查看结果`, `下载报告`.
- Avoid visible development words: `module id`, `workflow id`, `/api/tasks`, `manifest`, `gate`, `debug`, `acceptance`, `实验台` as a primary user label.
- Avoid half-release wording: `预览方法`, `可试用`, `需复核`, `beta`.
- Avoid overclaim wording: `诊断`, `治疗`, `病灶定位`, `脑区激活`, `源定位`, `证明因果`, `信息流方向`, `显著差异` unless a specific reviewed method supports the exact claim.

## 6. PDCA Execution Requirements

Every implementation and test item must record:

| PDCA field | Required content |
|---|---|
| Plan | Requirement IDs and intended product behavior. |
| Do | Files changed, scripts run, browser/API action. |
| Check | Assertions and evidence paths. |
| Act | accepted, fixed, blocked, or backlog with reason. |

Final release cannot pass on chat confirmation alone. It requires saved documents, DeepSeek review evidence or explicit unavailable record, synthetic data E2E, browser screenshots, backend/API evidence, and final acceptance packet.
"""


design = f"""
# QLanalyser 当前可用分析方法、教学模式与科研工作流详细设计

Date: {DATE}
Source requirements: `docs/product/qlanalyser_current_modules_teaching_mode_requirements_20260626.md`
Repo: `{REPO}`
Status: detailed design before implementation

## 1. Design Goals

This design turns the requirements into implementable product behavior. The primary design goal is to make QLanalyser feel like a researcher-facing EEG workflow:

- The user starts from a project and data record.
- Data preparation is the place for QC, waveform, bad channels, bad segments, events, and re-reference decisions.
- Analysis methods are only methods that compute analysis outputs.
- Teaching mode lets a new user run the real workflow with synthetic data.
- The product copy avoids internal engineering language and avoids scientific overclaims.

## 2. Architecture Boundary

### 2.1 Frontend

Primary files:

- `frontend/index.html`: static shell, navigation, method cards, top-right actions.
- `frontend/app.js`: dynamic copy, state transitions, action handlers, teaching-mode behavior.
- `frontend/styles.css`: navigation/topbar, method cards, data-preparation workbench, teaching overlay, color/token治理.

Frontend must provide:

- Top-right `教学模式` control.
- Global `个人中心` reachability.
- `当前可用分析方法` card list with 8 true method cards.
- Data-preparation re-reference UI.
- Teaching overlay state machine.
- Forbidden-copy prevention in customer surfaces.

### 2.2 Backend

Primary files:

- `backend/services/lab_demo_service.py`
- `backend/api/lab_demo.py`
- `backend/services/task_service.py`
- `eeg_core/analysis/reference_csd.py`

Backend must preserve existing task compatibility. The stable backend id `reference_csd` can remain, but user-facing labels must use `CSD 电流源密度计算` when the user is selecting the CSD analysis method. Re-reference modes stay available as preprocessing settings or internal transformation modes.

### 2.3 Existing source facts

Observed source behavior before implementation:

- `frontend/index.html` and `frontend/app.js` currently expose `当前可用模块`, `预览方法`, `需复核`, and `Reference / CSD`.
- `backend/services/task_service.py` currently declares workflow id `reference_csd` with display name `Reference / CSD`.
- `eeg_core/analysis/reference_csd.py` supports modes `keep_original`, `existing`, `average`, `specific_channels`, `bipolar`, and `csd`; CSD calls `mne.preprocessing.compute_current_source_density`.
- `eeg_core/analysis/reference_csd.py` already enforces `MONTAGE_REQUIRED_FOR_CSD` when CSD lacks montage/channel locations.
- `backend/services/lab_demo_service.py` already creates `teaching_oddball.edf` and a demo project/file.

## 3. User Flow Design

### 3.1 Normal researcher flow

```mermaid
flowchart LR
  A["项目管理"] --> B["数据管理: 上传或选择 EEG"]
  B --> C["数据准备: 自动预览波形与基础质量"]
  C --> D["预处理: 坏道/片段/事件/重参考"]
  D --> E["分析任务: 选择当前可用分析方法"]
  E --> F["结果查看: 图表/表格/参数/边界解释"]
  F --> G["报告交付: 下载报告包与处理记录"]
```

### 3.2 Teaching mode flow

```mermaid
flowchart LR
  A["点击教学模式"] --> B["创建或载入教学项目"]
  B --> C["载入合成 Oddball EEG"]
  C --> D["蒙版步骤 1: 认识项目和数据"]
  D --> E["步骤 2: 点击样本数据自动预览"]
  E --> F["步骤 3: 修改并恢复坏道/片段"]
  F --> G["步骤 4: 确认数据准备"]
  G --> H["步骤 5: 运行分析方法"]
  H --> I["步骤 6: 查看结果和报告"]
  I --> J["退出教学模式"]
```

## 4. Component Design

### 4.1 Global topbar

Required controls:

- `教学模式`: visible for customer role pages; opens teaching overlay and demo dataset.
- `知识库`: opens help/knowledge panel.
- `操作记录`: opens audit/activity record.
- `退出`: logout.

Personal center:

- `个人中心` remains visible in left navigation and account panel.
- If screen width hides side navigation, a topbar/account shortcut must still reach personal center.

### 4.2 Data preparation workbench

Layout:

- Left: data queue/list.
- Center: waveform preview and direct tools.
- Right: quality summary and current modifications.
- Bottom or top-right: `确认并进入分析`.

Rules:

- Single-clicking a data row selects it and starts waveform/QC preview.
- The previous primary button `运行质控预览` is removed. Only failure/retry states may show `重新加载预览`.
- Bad channel, bad segment, event edit, and re-reference settings are stored as reversible preparation actions.
- Re-reference settings must show mode, affected channels, output preview/record, and restore path.

### 4.3 Current available analysis methods

Card contract:

| Field | Design |
|---|---|
| title | User-facing method name. |
| body | What the researcher gets from the method. |
| input requirement | Events, channel locations, prepared data, or minimum channels. |
| output | Figure/table/report artifacts. |
| boundary | No unsupported clinical, source, causal, or significance claim. |
| action | Start method or open parameter panel. |

Cards:

1. `PSD 频谱与频段功率`
2. `ERP 事件相关电位`
3. `TFR 时频分析`
4. `Multitaper PSD`
5. `Multitaper TFR`
6. `PAC 相位-振幅耦合`
7. `Connectivity 连接性分析`
8. `CSD 电流源密度计算`

Not cards:

- 数据准备与质量检查
- 重参考设置
- 平均参考
- 指定通道参考
- 双极参考

### 4.4 CSD detailed behavior

User-facing title: `CSD 电流源密度计算`.

Visible explanation:

> 基于通道位置信息计算头皮电位的空间分布变化，用于观察传感器空间的局部变化；这不是脑源定位或诊断判断。

Run conditions:

- At least two usable EEG channels.
- Montage/channel locations present.
- Parameters recorded: sphere, lambda2, stiffness, n_legendre_terms.

Failure state:

- If channel locations are missing, do not show a generic failure. Show: `CSD 需要通道位置信息。请为数据补充 montage/电极位置后再运行。`

Backend compatibility:

- Keep `reference_csd` as a backend id if required by existing tasks.
- When user selects CSD, send `reference_mode=csd`.
- Re-reference modes do not appear as analysis method cards.

## 5. Teaching Overlay State Machine

State fields:

```json
{{
  "teachingMode": true,
  "stepIndex": 0,
  "datasetLoaded": true,
  "demoProjectId": "proj_demo_learning",
  "demoFileId": "eeg_demo_teaching_oddball",
  "isDemoData": true
}}
```

Overlay component:

- `role="dialog"` or equivalent accessible modal semantics.
- Mask dims the page but leaves target visibly framed.
- Step pointer must not cover the target action.
- Controls: `上一步`, `下一步`, `结束教学`.
- Escape or `结束教学` exits without deleting real project state.
- Reduced-motion users get no animated scrolling.

Step list:

| Step | Target | User instruction |
|---|---|---|
| T1 | topbar `教学模式` | 进入教学模式，系统载入一份合成 EEG 数据。 |
| T2 | project card/data list | 查看教学项目和样本数据。 |
| T3 | data row | 单击数据，波形和基础质量信息自动加载。 |
| T4 | waveform toolbar | 标记一个坏道或片段，再恢复它。 |
| T5 | re-reference panel | 查看重参考设置，理解它属于预处理。 |
| T6 | confirm preparation | 确认数据准备并进入分析。 |
| T7 | method cards | 选择一个分析方法，了解输入、输出和边界。 |
| T8 | result/report | 查看图表、参数记录和报告下载入口。 |

## 6. Visual Design Rules

Knowledge-base rules adopted:

- `DESIGN_TOKEN_GOVERNANCE_GATE`: use semantic colors, status colors, focus rings, spacing scale, radius/elevation tokens where the project supports them.
- `UX_STATE_COVERAGE_GATE`: cover ideal, empty, loading, error, success, disabled/focus, narrow/wide viewport.
- `QLANALYSER_CRITICAL_TASK_ONBOARDING_GATE`: onboarding is contextual help for critical tasks, not only a welcome page.
- `B2B_SCIENTIFIC_DASHBOARD_VISUAL_ANTIPATTERN_FIXTURES`: no unclear first landing point, no developer-looking function dump, no dense unreadable cards, no unscannable hierarchy.
- Scientific chart rules: no rainbow/jet default for quantitative EEG results; charts need axes, units, colorbar/legend, baseline/normalization notes where relevant.

Visual tone:

- Quiet research workbench, not marketing page.
- Dense but readable information hierarchy.
- Neutral surfaces with semantic accent colors.
- Avoid one-note green sidebar or one-hue dominated theme.
- Cards only for repeated items or framed tools; avoid nested cards.
- Icon buttons use familiar icons and tooltips where needed.

## 7. State and Error Design

Required states:

| Surface | Empty | Loading | Success | Error/recovery |
|---|---|---|---|---|
| Data list | Explain how to upload/use teaching data | Skeleton or stable row placeholders | Rows selectable | Retry load, no local absolute path leak |
| Waveform/QC | Select data or enter teaching mode | Reading waveform and quality info | Waveform + tools visible | `重新加载预览` |
| Re-reference | Show default mode | Applying settings | Processing record updated | Restore previous mode |
| Method cards | Explain data requirements | Checking readiness | Runnable actions | Show unmet condition and next action |
| Teaching overlay | Not active | Loading demo dataset | Step guidance | Continue with last valid state or exit teaching |
| Report delivery | No completed task | Packaging | Download report/record | Retry package, preserve task id |

## 8. Implementation Sequence

1. Update documents and DeepSeek review packet.
2. Add/adjust tests for forbidden copy, 8 visible analysis methods, global topbar, teaching overlay, CSD readiness, and synthetic full E2E.
3. Implement UI copy and IA changes.
4. Implement or wire teaching-mode state and overlay.
5. Verify syntax/mojibake/copy.
6. Run backend/API synthetic demo checks.
7. Run browser E2E screenshots and method tests.
8. Build final acceptance packet.

## 9. Non-goals

- Do not redesign backend task IDs if compatibility would break existing evidence.
- Do not make QLanalyser a clinical/medical diagnostic product.
- Do not remove reproducibility records; move them out of the main user action area.
- Do not claim real-world scientific validity from synthetic EEG fixtures.
"""


ui_design = f"""
# QLanalyser 当前可用分析方法与教学模式 UI 设计稿

Date: {DATE}
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
"""


test_plan = f"""
# QLanalyser 当前可用分析方法、教学模式与全流程 E2E 测试验证文档

Date: {DATE}
Source requirements: `docs/product/qlanalyser_current_modules_teaching_mode_requirements_20260626.md`
Source design: `docs/product/qlanalyser_current_modules_teaching_mode_design_20260626.md`
Source UI draft: `docs/product/qlanalyser_current_modules_teaching_mode_ui_design_20260626.md`
Status: test and validation contract before implementation

## 1. Evidence Root

All evidence for this slice is saved under:

```text
work/release_evidence/07-full-product-e2e-pdca/12_current_modules_teaching_mode/
```

Required subfolders:

```text
00_docs/
01_inventory/
02_deepseek/
03_static_checks/
04_backend_api/
05_synthetic_data/
06_methods/
07_ui_browser/
08_reports_figures/
09_acceptance_packet/
```

## 2. PDCA Test Record Schema

Each validation item writes a JSON record:

```json
{{
  "id": "TC-...",
  "requirements": ["R-..."],
  "pdca": {{
    "plan": "what is tested and why",
    "do": "command/browser/API/action",
    "check": "assertions and evidence paths",
    "act": "accepted|fixed|blocked|backlog"
  }},
  "status": "passed|failed|blocked|skipped_with_reason",
  "evidence": [],
  "findings": []
}}
```

No test may be marked `passed` without an evidence path.

## 3. Documentation and DeepSeek Gate

| ID | Requirements | Test | Pass condition |
|---|---|---|---|
| DOC-1 | R-DEEPSEEK-01 | Check requirements/design/UI/test docs exist. | All four docs exist and are UTF-8 readable. |
| DOC-2 | R-DEEPSEEK-01 | Run `scripts/check_no_mojibake.py` on new docs and review packets. | No mojibake markers. |
| DOC-3 | R-DEEPSEEK-01 | Create DeepSeek review prompt from these docs. | Prompt saved under evidence root. |
| DOC-4 | R-DEEPSEEK-01 | Run DeepSeek polish/logic route if available. | Review saved, or explicit unavailable JSON with command/error. |
| DOC-5 | R-DEEPSEEK-01 | Codex adoption review. | Every DeepSeek issue accepted/rejected with reason. |

## 4. Static Copy and UI Inventory Gate

Forbidden visible terms:

- `预览方法`
- `可试用`
- `需复核`
- `beta`
- `Reference / CSD`
- `参考方案与 CSD`
- `module id`
- `workflow id`
- `/api/tasks`
- `acceptance`
- `gate`
- `debug`

Allowed contexts:

- Developer docs.
- Test files that define forbidden terms.
- Reproducibility downloads or collapsed admin diagnostics.

Tests:

| ID | Requirements | Scope | Pass condition |
|---|---|---|---|
| COPY-1 | R-COPY-01 | `frontend/index.html`, `frontend/app.js`, customer-visible frontend HTML/JS | No forbidden release-maturity wording. |
| COPY-2 | R-COPY-02 | method card bodies and result boundary text | CSD/PAC/Connectivity limitations remain visible. |
| COPY-3 | R-IA-01/R-IA-03 | method card inventory | Exactly 8 current available analysis method cards. |
| COPY-4 | R-NAV-01/R-NAV-02 | nav/topbar inventory | `个人中心` and `教学模式` are globally reachable. |

## 5. Synthetic Data Fixture Gate

Fixture requirements:

- Deterministic seed.
- EDF output.
- Channel list includes valid EEG labels with montage positions.
- Events include at least `standard` and `target`.
- Signal design supports:
  - PSD: alpha rhythm dominance.
  - ERP: target P300-like response.
  - TFR/Multitaper TFR: event-related time-frequency window.
  - PAC: synthetic or at least non-empty phase/amplitude bands.
  - Connectivity: multiple channels and stable segment windows.
  - CSD: montage/channel locations.

Tests:

| ID | Requirements | Command/source | Pass condition |
|---|---|---|---|
| FX-1 | R-TEACH-01/R-E2E-01 | `scripts/generate_teaching_oddball_case.py` or equivalent | EDF/events generated, manifest records seed and synthetic status. |
| FX-2 | R-CSD-02 | fixture metadata | Montage/channel locations present. |
| FX-3 | R-TEACH-03 | demo service state | Demo project/file IDs are isolated from real projects. |

## 6. Backend/API Gate

| ID | Requirements | Endpoint/script | Pass condition |
|---|---|---|---|
| API-1 | R-TEACH-01 | `/api/lab/demo/dataset` | Returns project and file. |
| API-2 | R-E2E-01 | `/api/lab/demo/run-all` | Runs supported synthetic demo methods and returns task list. |
| API-3 | R-CSD-01/R-CSD-02 | `/api/tasks` with `module_name=reference_csd`, `reference_mode=csd` | CSD runs when montage is present. |
| API-4 | R-CSD-02 | CSD with missing montage fixture | Fails with recoverable montage-required message, not generic crash. |
| API-5 | R-REF-01 | Re-reference modes through preparation/parameters | Average/specific/bipolar modes are recorded as preprocessing, not method cards. |

## 7. Analysis Method Source-Comparison Gate

Every method must be compared against source implementation and output artifacts.

| ID | Method | Source check | Runtime check | Figure/report check |
|---|---|---|---|---|
| M-PSD | PSD 频谱与频段功率 | `eeg_core/analysis/psd.py` | task/API or direct runner | spectrum axes, units, band table |
| M-ERP | ERP 事件相关电位 | `eeg_core/analysis/erp.py` | event fixture | waveform, metrics, drop log, baseline |
| M-TFR | TFR 时频分析 | `eeg_core/analysis/tfr.py` | event fixture | time-frequency image, colorbar, baseline mode |
| M-MTP | Multitaper PSD | multitaper source family | `analysis_family=psd` | bandwidth/parameter record |
| M-MTT | Multitaper TFR | multitaper source family | `analysis_family=tfr` | time-frequency output and ITC if supported |
| M-PAC | PAC 相位-振幅耦合 | `eeg_core/analysis/pac.py` | synthetic channels/bands | comodulogram/phase-bin outputs, no causality claim |
| M-CON | Connectivity 连接性分析 | `eeg_core/analysis/connectivity.py` | multi-channel fixture | matrix/edge table, no information-flow claim |
| M-CSD | CSD 电流源密度计算 | `eeg_core/analysis/reference_csd.py`, `compute_current_source_density` | `reference_mode=csd` with montage | before/after preview, CSD summary, not source localization |

Pass condition:

- Required output artifacts exist.
- Parameter manifest exists.
- Method boundary text does not overclaim.
- Figures meet scientific plotting gate: title, axes/units where applicable, colorbar/legend for heatmaps/topomaps, source/parameter provenance.

## 8. Browser/UI E2E Gate

Required screenshot/click paths:

| ID | Requirements | Path | Pass condition |
|---|---|---|---|
| UI-1 | R-E2E-01 | Cover/login customer path | User reaches project management. |
| UI-2 | R-NAV-01 | Project management -> personal center | Personal center visible and reachable. |
| UI-3 | R-NAV-02/R-TEACH-02 | Project management -> teaching mode | Top-right teaching button opens overlay. |
| UI-4 | R-QC-01 | Data row click | Waveform/QC enters loading/success without `运行质控预览`. |
| UI-5 | R-QC-02 | Mark/restore bad channel/segment/event | Each edit is visible and individually recoverable. |
| UI-6 | R-REF-01 | Re-reference panel | Modes are in data preparation, not method cards. |
| UI-7 | R-IA-03 | Analysis task page | 8 method cards, no data-prep duplicate. |
| UI-8 | R-CSD-01 | Method card | CSD appears as `CSD 电流源密度计算`. |
| UI-9 | R-TEACH-04 | Teaching full path | Steps progress through data, preparation, method, result, report. |
| UI-10 | R-VIS-01 | Desktop/mobile scroll | No core tool hidden below fold; no overlap; colors/status/focus pass review. |

Screenshot matrix:

- desktop 1440x1000
- laptop 1280x800
- mobile 390x844
- wide 1920x1080
- states: default, teaching, data loading, data success, method cards, result/report, error/recovery where practical

## 9. Scientific Figure Gate

| ID | Requirement | Check |
|---|---|---|
| FIG-1 | R-VIS-02 | No rainbow/jet default for quantitative heatmaps unless explicitly justified. |
| FIG-2 | R-VIS-02 | TFR/PAC/connectivity figures include legend/colorbar or direct labels. |
| FIG-3 | R-VIS-02 | Axes and units are present where the plot has physical dimensions. |
| FIG-4 | R-COPY-02 | Figure titles/captions do not imply diagnosis, source localization, or causality. |
| FIG-5 | R-E2E-01 | Exported report includes method, parameters, data provenance, and boundary text. |

## 10. Final Acceptance Packet

Final packet fields:

```json
{{
  "route_decision": "",
  "reused_pool_or_new_pool": "",
  "execution_packets": [],
  "executor_evidence": [],
  "targeted_or_full_e2e": "",
  "page_visual_review": "",
  "deepseek_logic_review": "",
  "gpt55_acceptance": "",
  "final_receipt": "completed_final_receipt|blocked_final_receipt",
  "next_real_artifact": "",
  "route_chain": "",
  "model_lane": "",
  "headroom_savings": ""
}}
```

Acceptance can pass only if:

- Docs exist and pass mojibake checks.
- DeepSeek review is completed or explicitly unavailable with saved prompt/error.
- Static copy gate passes.
- Backend/API smoke passes.
- Synthetic data method E2E passes for all supported methods.
- Browser/UI E2E screenshots exist.
- Scientific figure audit passes or lists blockers.
- Codex/GPT-5.5 final acceptance reviews all evidence.
"""


execution_packet = f"""
# 07 Execution Packet: Current Modules, Teaching Mode, and Synthetic Full E2E

Date: {DATE}
Repo: `{REPO}`
Generated: {GENERATED_AT}
Pool decision: reuse current 07 continuation pool unless release/checkpoint governance requires a new pool.

## Objective

Implement and validate the documented requirements for current available analysis methods, preprocessing/re-reference placement, CSD naming, global personal center/teaching mode navigation, guided teaching overlay, and full synthetic EEG E2E.

## Inputs

- Requirements: `docs/product/qlanalyser_current_modules_teaching_mode_requirements_20260626.md`
- Design: `docs/product/qlanalyser_current_modules_teaching_mode_design_20260626.md`
- UI design draft: `docs/product/qlanalyser_current_modules_teaching_mode_ui_design_20260626.md`
- Test plan: `docs/product/qlanalyser_current_modules_teaching_mode_test_plan_20260626.md`
- Prior acceptance: `work/release_evidence/07-full-product-e2e-pdca/10_acceptance_packet/full_product_e2e_acceptance_packet_20260626.json`

## Allowed Write Scope

- `frontend/index.html`
- `frontend/app.js`
- `frontend/styles.css`
- targeted frontend acceptance scripts under `scripts/`
- targeted backend/demo acceptance scripts under `scripts/`
- evidence under `work/release_evidence/07-full-product-e2e-pdca/12_current_modules_teaching_mode/`
- final packet builder if needed

## Forbidden Scope

- Router, Headroom, gateway, IPC, model-route, or process communication configuration.
- Destructive git operations.
- Broad cleanup of unrelated dirty files.
- Clinical/medical claims.
- Backend ID migration that breaks stored task compatibility without explicit migration plan.

## Worker Packets

1. Code/copy inventory packet: locate existing visible copy, nav, method card, backend display, CSD/reference code.
2. Test inventory packet: locate synthetic data generation, module E2E, full product smoke, figure audit, UI screenshot checks.
3. UI/knowledge review packet: extract design-token, state, onboarding, glossary, scientific dashboard gates.
4. DeepSeek logic packet: review researcher workflow and Chinese operation logic.
5. Script-validator packet: syntax, mojibake, copy scan, backend smoke, browser E2E, final evidence inventory.

## Verification Commands

The exact commands may be refined after implementation, but the final run must include equivalents of:

```text
python -X utf8 scripts/check_no_mojibake.py <new docs and evidence markdown>
node --check frontend/app.js
python -X utf8 scripts/run_full_product_backend_api_smoke.py
python -X utf8 scripts/run_full_product_method_source_comparison.py
node scripts/acceptance_full_product_ui_scroll_review.mjs
python -X utf8 scripts/build_full_product_e2e_acceptance_packet.py
```

Additional required checks for this slice:

```text
forbidden customer-visible copy scan
8 current available analysis methods visible-fields scan
teaching-mode overlay browser E2E
CSD with montage positive path
CSD missing-montage recovery path
scientific figure audit
```

## Acceptance

Codex/GPT-5.5 accepts only after reading real files, real evidence JSON, screenshots/trace paths where available, and test outputs. Worker or DeepSeek results are advisory until accepted in the final packet.
"""


deepseek_prompt = f"""
# DeepSeek Researcher-Logic Review Prompt

Date: {DATE}
Purpose: Review QLanalyser current modules, preprocessing/reference placement, CSD naming, teaching mode, and Chinese customer-facing operation logic from the perspective of EEG researchers.

You are reviewing saved requirements/design/test documents, not a chat-only request.

## Documents to Review

- `docs/product/qlanalyser_current_modules_teaching_mode_requirements_20260626.md`
- `docs/product/qlanalyser_current_modules_teaching_mode_design_20260626.md`
- `docs/product/qlanalyser_current_modules_teaching_mode_ui_design_20260626.md`
- `docs/product/qlanalyser_current_modules_teaching_mode_test_plan_20260626.md`

## Review Questions

1. Does the information architecture match how EEG researchers think: project/data -> data preparation/preprocessing -> analysis methods -> result/report?
2. Is it correct to remove `数据准备与质量检查` from `当前可用分析方法` and keep it in data preparation?
3. Is re-reference correctly treated as preprocessing rather than an analysis method?
4. Is `CSD 电流源密度计算` a clearer user-facing name than `Reference / CSD`?
5. Does the CSD wording avoid confusing CSD with source localization or diagnosis?
6. Is teaching mode designed as a real critical-task onboarding path rather than a superficial tutorial?
7. Are the mask/step提示 interactions natural for a first-time researcher using a complex EEG tool?
8. Are the visible method card names and boundaries understandable to a researcher without exposing backend internals?
9. Are any user-facing Chinese phrases still too developer-oriented, vague, or likely to mislead?
10. Are any missing test cases likely to create release risk?

## Output Format

Return concise Chinese Markdown:

```text
结论: pass | revise | block
主要问题:
- [P0/P1/P2] ...
建议改法:
- ...
必须进入测试的验收点:
- ...
可接受的残余风险:
- ...
```

Do not claim clinical/medical validity. Do not rewrite the entire documents; focus on logic, workflow, terminology, and researcher usability.
"""


def main() -> None:
    write(DOC_DIR / "qlanalyser_current_modules_teaching_mode_requirements_20260626.md", requirements)
    write(DOC_DIR / "qlanalyser_current_modules_teaching_mode_design_20260626.md", design)
    write(DOC_DIR / "qlanalyser_current_modules_teaching_mode_ui_design_20260626.md", ui_design)
    write(DOC_DIR / "qlanalyser_current_modules_teaching_mode_test_plan_20260626.md", test_plan)
    write(EVIDENCE_ROOT / "current_modules_teaching_mode_execution_packet_20260626.md", execution_packet)
    write(DEEPSEEK_DIR / "researcher_logic_review_prompt.md", deepseek_prompt)
    manifest = f"""{{
  "generated_at": "{GENERATED_AT}",
  "docs": [
    "docs/product/qlanalyser_current_modules_teaching_mode_requirements_20260626.md",
    "docs/product/qlanalyser_current_modules_teaching_mode_design_20260626.md",
    "docs/product/qlanalyser_current_modules_teaching_mode_ui_design_20260626.md",
    "docs/product/qlanalyser_current_modules_teaching_mode_test_plan_20260626.md"
  ],
  "execution_packet": "work/release_evidence/07-full-product-e2e-pdca/12_current_modules_teaching_mode/current_modules_teaching_mode_execution_packet_20260626.md",
  "deepseek_prompt": "work/release_evidence/07-full-product-e2e-pdca/12_current_modules_teaching_mode/deepseek/researcher_logic_review_prompt.md",
  "status": "docs_generated_before_implementation"
}}"""
    write(EVIDENCE_ROOT / "current_modules_teaching_mode_docs_manifest.json", manifest)


if __name__ == "__main__":
    main()
