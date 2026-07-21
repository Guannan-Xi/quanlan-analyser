# QLanalyser Research-User Copy Governance Spec - 2026-07-01

Status: active project-level copy baseline for research-user facing pages.

Scope: QLanalyser Online customer-visible UI copy, workflow labels, help text, loading/error/empty/success states, export/result boundary copy, and release copy governance checks.

## 1. Purpose

QLanalyser is a research EEG analysis product. The user-facing language must make the research workflow clear without overclaiming clinical, diagnostic, or fully automated conclusions.

This document prevents the repeated pattern of fixing one screenshot at a time. Every visible copy change should be checked against the same product rules:

- the user knows where they are in the research workflow;
- the user knows which dataset and preparation plan are active;
- the user knows what the method does and what it does not prove;
- the user knows whether a change writes to a draft, review layer, result artifact, or source data;
- the UI does not use clinical or diagnostic wording unless it is explicitly negated as a boundary.

## 2. Target Users

- EEG researcher or PI checking whether the workflow is scientifically credible.
- Lab technician preparing EEG data and running repeatable analysis tasks.
- CRO technical reviewer using the product for preclinical or contract research workflows.
- Internal trial operator demonstrating the product with example data.

These users do not need marketing slogans. They need concise, evidence-oriented copy with units, provenance, task status, and next action.

## 3. Global Copy Model

Every page should answer five questions within the first working screen:

1. What workflow am I in?
2. Which data am I handling?
3. Which method, parameters, or preparation plan is active?
4. Where will results or edits be written?
5. What is the next valid action?

If a page cannot answer these questions, adding more status chips, banners, or buttons is not allowed until the information architecture is clarified.

## 4. Product Boundary

Use these boundary statements consistently:

- Research support only.
- Candidate event screening, manual review, and export support.
- Source EEG and source algorithm outputs are immutable.
- Data preparation and manual correction write drafts/revisions, not raw EEG.
- Results are descriptive research outputs unless an approved regulated product track exists.

Do not use copy that implies:

- diagnosis, confirmed disease, treatment, clinical triage, or medical decision-making;
- automatic truth, one-click scientific conclusion, or clinician replacement;
- mutation of source EEG when the action actually creates a draft or review layer.

## 5. Terminology Contract

### 5.1 Epilepsy-like Event Workflow

Preferred:

- 癫痫样事件初筛
- 候选事件检测
- 查看候选事件
- 人工复核
- 人工矫正
- 事件修正
- 保存复核版本
- 导出结果
- 科研支持，不作为临床诊断依据

Avoid in epilepsy customer UI:

- 癫痫分期
- 癫痫样事件分期
- 开始分期
- 分期波形
- 自动诊断
- 确诊
- 治疗建议
- 临床分诊

Reason: sleep can have staging; epilepsy-like event workflows are event screening and manual review workflows.

### 5.2 Sleep Workflow

Preferred:

- 睡眠分期
- 分期图
- Hypnogram
- 呼吸事件
- 觉醒事件
- 人工校正
- 保存分期复核版本

Guardrail: sleep staging terms must not leak into epilepsy event copy unless describing shared internal infrastructure or test IDs.

### 5.3 Example / Teaching Data

Customer-visible labels should prefer:

- 示例模式
- 示例项目
- 示例数据
- 示例 EDF
- 示例流程

Internal or developer documentation may still use teaching mode when describing implementation state, selectors, or test fixtures.

Use "teaching" only if the visible user task is truly a guided lesson. For a customer trial, "example" is calmer and more professional.

### 5.4 Waveform Copy

Preferred:

- 已加载波形
- 当前时间窗
- 波形数据
- 波形窗口
- 当前时间窗暂无可写入的波形点

Avoid:

- 正在读取真实波形 as a repeated canvas overlay or scroll-time popup;
- 真实波形 when it sounds like a quality guarantee rather than the currently loaded data;
- developer-facing explanations such as "不会用旧窗口伪装当前数据" in customer UI.

## 6. Page-Level Rules

### Login / Entry

- Default page errors must stay hidden until a real failed action occurs.
- Demo entry should say "示例模式" or "示例项目", not "test/debug/dev".

### Project / Data Management

- Normal mode with no user upload should show an empty list, not demo data.
- Protected example data must be clearly marked as protected and non-deletable.
- Delete copy must specify what is removed and what is preserved.

### Data Preparation

- The first screen should prioritize waveform, selected dataset, preparation state, and the single next action.
- Do not duplicate the same time/progress/status information in multiple controls.
- Marking bad channels, bad segments, and preparation choices must say they write to a preparation draft/revision.
- Confirming data preparation must say it does not overwrite raw EEG.

### Waveform Workbench

- Basic preview mode must not mention Epoch unless the user opens an epoch/scoring workflow.
- Epoch review is allowed for epilepsy/sleep/scoring workbenches, not basic waveform preview.
- Scroll and drag feedback should not flash transient text over the data layer.

### Analysis Tasks

- Analysis entry copy must separate data preparation from method execution.
- Method cards should say what the method computes and one major limitation.
- Avoid "one-click" and "intelligent judgment". Prefer "运行分析任务" and "查看任务产物".

### Epilepsy-like Event Workbench

- Entry state: first show waveform and method boundary; do not show algorithm-candidate styling before initial screening has run.
- Primary actions:
  - 开始初筛
  - 查看候选事件
  - 进入人工矫正
  - 保存复核版本
  - 导出结果
- The UI should show candidate events as review targets, not final truth.
- Manual correction writes review revisions and exports; it must not mutate source algorithm output.

### Results / Reports

Each result should show:

- input file;
- data preparation plan and revision;
- method/workflow id;
- task id;
- artifact id or export file;
- parameter summary;
- non-medical/research boundary where relevant.

## 7. Error, Loading, Empty, Success States

Every state message should include the reason and the next action.

Poor:

- 操作失败，请重试。
- 正在读取真实波形。
- 未选择。

Better:

- 示例 EDF 自动载入未完成。请重新载入示例数据，或回到数据管理选择文件。
- 当前时间窗暂无可写入的波形点，请等待窗口读取完成后再选择片段。
- 普通模式暂无项目数据。请上传 EDF/FIF/BDF 文件，或切换到示例项目。

## 8. Adversarial Review Questions

For any substantial customer-facing copy change, run at least these five checks:

1. Global workflow: does the page say where the user is and what the next valid action is?
2. Information duplication: does the same state appear in two places with different wording?
3. Scientific boundary: can a skeptical researcher read this as diagnosis, causality, or final truth?
4. State behavior: does disabled/loading/error copy explain why and how to recover?
5. Traceability: can the user identify dataset, method, preparation plan, and output destination?

For release candidates, repeat after changes until no P0 copy issue remains.

## 9. Validation Plan

Required checks:

- static copy governance script for forbidden or guarded customer-visible terms;
- browser or DOM check for visible copy on major pages;
- E2E checks for epilepsy cloud trial and data preparation states;
- no mojibake check for newly written docs/scripts;
- no broad replacement of internal class names or test ids without test updates.

## 10. Traceability

| Requirement | UI / file area | Test or gate |
| --- | --- | --- |
| Epilepsy is event screening, not staging | Main analysis entry, epilepsy workbench | copy governance, E2E DOM text |
| Example mode copy is customer-friendly | Topbar, data queue, waveform workbench | research-user copy governance |
| Source data immutability is explicit | Data preparation, manual review | E2E state/copy checks |
| No diagnostic/clinical claim | All customer UI and exports | static governance + browser scan |
| Waveform loading copy does not flash or mislead | Data preparation, waveform workbench, epilepsy workbench | waveform E2E + copy scan |

## 11. Sources Used

- `docs/product/epilepsy_sleep_terminology_contract_20260629.md`
- `docs/product/qlanalyser_design_contract_main_workbench_audit_20260628.md`
- `docs/product/product_doc_governance.md`
- `docs/product/qlanalyser_epilepsy_cloud_trial_v0_1_customer_trial_support_packet_20260701.md`
- Current frontend source scan on 2026-07-01.

## 12. Sources Blocked / Unread

- Feishu PSG/AASM wiki remains blocked unless the user exports or authorizes access. This document does not claim to incorporate unread Feishu details.

## 13. Change Log

- 2026-07-01: Created project-level research-user copy governance baseline and linked it to epilepsy/sleep terminology, waveform/data-preparation copy, and release validation.
