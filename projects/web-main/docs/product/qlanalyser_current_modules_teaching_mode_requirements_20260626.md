# QLanalyser 当前可用分析方法、教学模式与科研工作流修复需求

Date: 2026-06-26
Owner: 07-PM / QLanalyser product acceptance
Repo: `D:\Quanlan\Codes\Python\quanlan-analyser-official`
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
