# QLanalyser UI Interaction and Visual Governance Master Standard

Date: 2026-06-28  
Status: active hard gate; supersedes ad-hoc UI decisions  
Scope: all QLanalyser customer-facing UI, teaching mode, data preparation, waveform workbench, analysis methods, result review, reports, exports, module lab, and internal validation screens that may be shown to customers.  
Product boundary: QLanalyser is a non-medical EEG research and CRO analysis workspace. It must not imply diagnosis, treatment, clinical decision-making, seizure confirmation, disease screening for clinical use, or medical triage.

This document combines external usability/accessibility/human-factors standards and QuanLan local knowledge-base gates into one enforceable design standard. It is not a mood board. It is the checklist that must be read before UI design, implementation, review, or release.

---

## 0. Mandatory Use

### 0.1 When this document must be used

Use this document before any change involving:

- page layout;
- buttons, tabs, toolbars, cards, status chips, modals, popovers, toasts;
- waveform, EEG chart, event marker, epoch review, bad segment / bad channel interaction;
- teaching mode, onboarding, help text, method explanation;
- analysis method selection, parameter setting, report interpretation;
- empty / loading / error / success / disabled / stale states;
- mobile, narrow, wide, dense-data visual behavior;
- customer-facing Chinese or English UI copy;
- screenshots, visual acceptance, E2E acceptance, external release gates.

### 0.2 Required output before implementation

Every non-trivial UI change must produce or update a local design artifact:

```yaml
DESIGN_CONTRACT_USED:
  surface:
  target_user:
  primary_task:
  risk_level:
  source_documents:
  adopted_rules:
  skipped_rules_with_reason:
  expected_screenshots:
  expected_e2e:
  decision_before_build: pass_to_build | revise_design | blocked
```

### 0.3 Required output after implementation

```yaml
UI_GOVERNANCE_ACCEPTANCE:
  surface:
  changed_files:
  screenshots:
  e2e_results:
  viewport_matrix:
  state_coverage:
  interference_matrix:
  forbidden_terms_scan:
  accessibility_check:
  scientific_boundary_check:
  remaining_risks:
  decision: pass | revise | block
```

A UI change is not accepted just because it looks better in one screenshot.

---

## 1. Source Authority Stack

When sources conflict, use this order:

1. Current owner instruction and product boundary.
2. QLanalyser `DESIGN.md` and this master standard.
3. QLanalyser page-level design contracts.
4. QuanLan local knowledge-base gates listed below.
5. External official standards and design systems.
6. Expert judgment from Codex / GPT-5.5 final acceptance.
7. Community examples or taste references.

Community signals and screenshots can reveal a problem, but they cannot become a hard rule unless supported by product intent, evidence, or an accepted design contract.

### 1.1 External references used

- NN/g 10 Usability Heuristics: system status, match with real world, user control, consistency, error prevention, recognition over recall, minimalist design, recovery from errors.
- W3C WCAG 2.2: perceivable, operable, understandable, robust; keyboard access, focus visibility, non-color encoding, reduced motion, accessible names, error identification.
- Material Design 3: component states, progress indicators, design tokens, layout, interaction feedback.
- Apple Human Interface Guidelines: clarity, deference to content, direct manipulation, feedback, consistency, forgiving interaction.
- Microsoft Fluent 2: wait UX, progress feedback, status, accessibility, enterprise component behavior.
- IBM Carbon Design System: empty states, data-dense enterprise UI, tokens, accessibility, enterprise dashboard discipline.
- IEC 62366-1 / FDA Human Factors guidance: critical tasks, foreseeable use errors, risk controls, formative findings, validation evidence. Used as human-factors methodology only; QLanalyser remains non-medical unless formally repositioned.

### 1.2 Local QuanLan / QLanalyser references used

- `DESIGN.md`
- `docs/product/qlanalyser_project_design_system_20260628.md`
- `D:/QuanLanKnowledgeBase/manifests/design/GOOGLE_LABS_DESIGN_MD_CONTRACT_TOOL_20260627.md`
- `D:/QuanLanKnowledgeBase/learning-notes/design/UX_DESIGN_CRITIQUE_WORKFLOW_RUBRIC_CN.md`
- `D:/QuanLanKnowledgeBase/learning-notes/design/B2B_SCIENTIFIC_DASHBOARD_SCREENSHOT_AUDIT_CHECKLIST_CN.md`
- `D:/QuanLanKnowledgeBase/learning-notes/design/B2B_SCIENTIFIC_DASHBOARD_VISUAL_ANTIPATTERN_FIXTURES_CN.md`
- `D:/QuanLanKnowledgeBase/learning-notes/design/UX_STATE_FEEDBACK_EMPTY_ERROR_LOADING_MOTION_GATE_CN.md`
- `D:/QuanLanKnowledgeBase/learning-notes/design/DESIGN_TOKENS_VISUAL_REGRESSION_GATE_CN.md`
- `D:/QuanLanKnowledgeBase/learning-notes/design/VISUAL_REGRESSION_BASELINE_NAMING_SCREENSHOT_SET_STANDARD_CN.md`
- `D:/QuanLanKnowledgeBase/learning-notes/qlanalyser/QLANALYSER_ONBOARDING_CRITICAL_TASK_RESULT_INTERPRETATION_GATE_CN.md`
- `D:/QuanLanKnowledgeBase/learning-notes/qlanalyser/HUMAN_FACTORS_FORMATIVE_SUMMATIVE_EVIDENCE_PACK_STANDARD_CN.md`
- `D:/QuanLanKnowledgeBase/learning-notes/qlanalyser/QLANALYSER_EEG_GLOSSARY_CN.md`
- `D:/QuanLanKnowledgeBase/learning-notes/qlanalyser/QLANALYSER_REPORT_FORBIDDEN_CLAIM_SCAN_STANDARD_CN.md`
- `D:/QuanLanKnowledgeBase/learning-notes/qlanalyser/QLANALYSER_USER_EDUCATION_METHOD_EXPLAINER_CURRICULUM_GATE_CN.md`

---

## 2. Product-Level Design Constitution

### 2.1 QLanalyser is

QLanalyser is a professional non-medical EEG research and CRO workspace for:

1. managing EEG projects and datasets;
2. inspecting waveforms and preparing data;
3. selecting appropriate analysis methods;
4. running reproducible analysis workflows;
5. reviewing results with scientific boundaries;
6. exporting traceable reports and artifacts;
7. teaching customers through protected built-in demo data.

### 2.2 QLanalyser is not

QLanalyser is not:

- a generic chart demo;
- an engineering console;
- a medical diagnostic tool;
- a clinical seizure detector;
- a collection of unrelated method buttons;
- a dashboard that prioritizes KPI cards over scientific evidence;
- a teaching overlay that exits into a normal empty page requiring manual upload;
- a UI where every backend artifact becomes a visible customer concept.

### 2.3 Product feeling target

The product should feel calm, scientific, traceable, trustworthy, data-first, recoverable, professional enough for labs and CRO teams, and simple enough for customers to complete critical tasks without a developer standing next to them.

It should not feel like a debugger, a prototype control panel, a pile of buttons, a marketing page without operational depth, or a medical claim engine.

---

## 3. Universal UI Hard Rules

These rules are merge-blocking unless explicitly waived in a design receipt.

### 3.1 One user intention, one primary control

For each user intention, there must be one primary place to act.

| Intention | Primary control location | Other locations may do |
| --- | --- | --- |
| Move through time | waveform navigation / time overview | display current time only |
| Change visible window length | display controls | status text may not repeat it |
| Mark bad segment | write-mode annotation panel | waveform overlay shows result |
| Confirm preparation plan | preparation decision panel | workflow gate shows read-only status |
| Start PSD analysis | analysis method card | report/results page may link previous run |

Blocked patterns:

- same action appears as two primary buttons in different panels;
- time position is controlled by multiple equally prominent controls without clear difference;
- status bar repeats values already next to controls;
- teaching banner, file card, and queue card repeat the same protection paragraph;
- a secondary export action competes visually with the primary next task.

### 3.2 Separate read-only display, display settings, and writing actions

Every control belongs to exactly one layer:

1. Read-only status layer: current file, sample rate, prepared/unprepared, non-medical boundary.
2. Display control layer: time window, gain/sensitivity, channel count, event marker visibility, raw/filter preview.
3. Browse layer: pan, page, jump, zoom.
4. Write/review layer: selected segment, candidate bad segment, confirmed reject/remain, bad channel, label, undo/redo/restore, confirm plan.
5. Analysis layer: method selection, parameters, run task, result review.
6. Export layer: report, artifact, audit record, package download.

Controls from different layers must not be visually flattened into one button row.

### 3.3 Browse mode and write mode must never be ambiguous

Browse mode:

- mouse wheel pans horizontally;
- Ctrl/Cmd + wheel zooms time;
- PageUp/PageDown changes page;
- Left/Right moves by a small step;
- middle drag pans;
- plus/minus changes display sensitivity unless Ctrl/Cmd is held;
- no bad segment, bad channel, label, reject, remain, or preparation draft is written.

Write modes:

- selected mode is visually emphasized;
- canvas cursor changes;
- status states that changes write only to preparation draft;
- write buttons are disabled until a valid selection or target exists;
- all changes are undoable or restorable;
- original EEG file is never silently modified.

Blocked patterns:

- dragging in browse mode creates a hidden draft;
- a write-mode button remains active after switching back to browse;
- color alone distinguishes browse/write mode;
- warning appears only in a toast and disappears;
- user cannot tell whether a change is transient, draft, or persisted.

### 3.4 Three-layer write model

All data preparation changes must follow:

```text
L1 transient interaction:
  hover, drag, temporary cursor, temporary selection preview
L2 UI draft:
  released selection, candidate bad segment, local undo stack, visible draft summary
L3 persisted preparation revision:
  saved/confirmed preparation plan with id, revision, contract version, source file id
```

Rules:

- L1 must not be counted as saved work.
- L2 must be visible, reviewable, undoable, and clearable.
- L3 requires explicit save/confirm action.
- Analysis tasks must not start from unconfirmed L2 state unless the task explicitly supports draft mode.
- Confirmed analysis payload must carry `data_preparation_plan_id`, `data_preparation_revision`, and `data_preparation_contract_version`.

### 3.5 Status bars must not become duplicate dashboards

Status bars may show only:

- selected segment when it affects the next action;
- non-empty draft count;
- confirmed plan status;
- write-mode safety text;
- loading/stale/error state;
- explicit user-relevant message.

Status bars must not repeat:

- file name if shown in object card;
- time window if shown in navigator;
- channel count if shown next to channel control;
- sensitivity if shown next to gain control;
- raw/filter if shown in display control;
- mode if already shown as active segmented control;
- debug values such as cache range, artifact count, runner, schema, dispatch.

### 3.6 The main scientific object must dominate

For EEG workbench pages, the waveform or main plot must be visually dominant.

Minimum expectations:

- desktop first viewport shows data object, primary workflow step, and waveform/plot;
- controls support waveform reading, not compete with it;
- side panels must not make waveform too narrow;
- on narrow screens, task steps should stack; do not squeeze dense toolbars into unreadable rows;
- dense scientific labels must remain legible.

### 3.7 Hide advanced and secondary actions by default

Default view should show:

- what data is selected;
- what task the page supports;
- primary display controls;
- one primary next action;
- current risk/status needed for the next decision.

Move these into expandable areas unless actively needed:

- download JSON;
- export audit history;
- raw artifact inventory;
- schema/manifest details;
- rarely used restore-all actions;
- debug or validation details;
- advanced method parameters;
- secondary report package controls.

### 3.8 Customer-visible forbidden debug terms

These terms must not appear in default customer UI unless inside a developer-only panel or evidence artifact:

```text
manifest
runner
dispatch
schema
artifact count
cache range
internal validation route
worker
backend task object
raw JSON
IPC
Headroom
gateway
router
model route
```

Allowed: exported audit documents and developer/admin diagnostic pages, clearly labeled as technical.

---

## 4. QLanalyser Page Archetypes

### 4.1 Cover / login / entry

Primary job:

- identify the product;
- choose teaching mode or normal mode;
- enter workspace;
- avoid medical overclaim.

Rules:

- do not show an error before the user attempts an action;
- teaching mode and normal mode must be visibly separate;
- teaching mode should enter a protected sandbox with built-in data, not a normal empty page;
- no fake promise such as automatic clinical interpretation.

### 4.2 Project and data management

Primary job:

- select project;
- upload/manage EEG data;
- understand what is protected and what can be changed.

Rules:

- preloaded teaching datasets are protected and clearly labeled;
- teaching data cannot be deleted, renamed, overwritten, or mixed silently with owner data;
- upload errors must preserve user context and explain recovery;
- file cards show filename, format, sample rate, channel count, duration, selected/prepared status;
- project cleanup must not remove real work without confirmation.

### 4.3 Data preparation / waveform workbench

Primary job:

- inspect continuous EEG;
- adjust display;
- mark bad channels/segments/events;
- confirm preparation plan.

Rules:

- waveform loads automatically after selecting data;
- browsing is safe and non-writing;
- display controls and write controls are separated;
- event markers are visual evidence, not data discontinuities;
- dense markers are light/aggregated by default;
- old/stale waveform must not be remapped into a new time window as if it were current data;
- long files require chunk API, caching, loading/stale distinction, and min-max/envelope decimation;
- canvas must not be wider than actual available data duration without explicit empty/after-end state.

### 4.4 Analysis method library

Primary job:

- choose the scientifically appropriate method;
- understand prerequisites;
- run analysis with confirmed preparation plan.

Rules:

- QC is data preparation dependency, not a formal analysis method card;
- use current formal method set consistently;
- method cards must state required inputs and limitations;
- disabled method cards explain what is missing;
- Band Power as PSD view/alias must not create a fake backend method if product contract says PSD handles it;
- analysis run payload must include preparation revision when required.

### 4.5 Results and report review

Primary job:

- inspect outputs;
- understand method, parameters, QC, limitations;
- export deliverables.

Rules:

- separate raw data, processed data, descriptive metric, statistical inference, scientific interpretation, and clinical implication;
- all scientific figures need units, method context, time/frequency/channel context, and limitations;
- no result should imply diagnosis/treatment/clinical decision;
- report package must include source, QC, parameters, versions, and artifact inventory where appropriate;
- exported report should match visible UI meaning.

### 4.6 Teaching mode

Primary job:

- guide customer through learning cards;
- then let them run each method end-to-end with protected built-in data.

Rules:

- teaching mode is not merely an overlay;
- after teaching cards, user stays in teaching sandbox unless they intentionally switch;
- built-in data is protected;
- each formal analysis method should be testable with suitable teaching fixtures, or clearly marked unavailable with reason;
- teaching copy explains safe interpretation and common misunderstanding;
- no raw EEG or customer-sensitive content is collected in teaching analytics.

---

## 5. Waveform and EEG Interaction Standard

### 5.1 Layout

Recommended desktop order:

```text
Object summary strip
  current file | data status | preparation plan | boundary

Main workbench
  left/main: waveform canvas + overview/time navigator + minimal status
  right/side: preparation settings and primary confirm action

Contextual drawer/accordion
  records, exports, advanced settings, audit history
```

Toolbar groups must follow task order:

1. Browse: first, previous, next, last, time slider/overview.
2. Display: window length, sensitivity, channel count, event marker density, raw/filter preview.
3. Mode: browse, select segment, mark bad segment, mark bad channel, epoch review.
4. Draft actions: candidate, confirm reject/remain, undo, redo, restore.
5. Preparation action: confirm plan.
6. Secondary: record/export/download.

### 5.2 Time window vs epoch length

Time window and epoch length are different concepts.

- Time window controls how much continuous EEG is visible per page.
- Epoch length controls review unit or segmentation length.

They must not appear as peer controls without explanatory grouping. If both are visible, label them under separate groups:

```text
Display window: 10 s/page, 30 s/page, 60 s/page, 5 min/page
Epoch review unit: 1 s, 2 s, 4 s, custom
```

### 5.3 Event marker display

Event markers are overlays, not cuts.

Required modes:

- hidden;
- light default;
- full labels;
- aggregate/density for dense events.

Labels should appear on hover, current focus, or selected event; not all labels should be shown by default in dense windows.

### 5.4 Data continuity and loading

Rules:

- display data must match current time axis;
- do not remap an old payload to a new time window;
- stale data must be greyed or labeled as stale;
- loading overlay must not look like confirmed selection;
- request sequence must ignore old responses after rapid switching;
- cache hit should be instant but must still identify correct window;
- preview downsampling must preserve peaks/valleys for EEG reading.

### 5.5 Decimation and performance disclosure

For display sampling:

- simple point sampling is not acceptable for long windows where spikes may be lost;
- min-max bucket or envelope decimation is preferred;
- preview-only resampling must be disclosed as display policy;
- original EEG must remain unchanged;
- large file interactions require chunk API and caching; full QC task is not appropriate for every scroll.

### 5.6 Canvas accessibility

Canvas must have:

- accessible label;
- keyboard focus;
- keyboard equivalents for core browsing;
- visible focus style;
- non-color overlays for selection/reject/bad channel/event;
- status text outside canvas for screen reader / non-visual context;
- reduced-motion safe behavior.

---

## 6. Information Architecture and De-Duplication Rules

### 6.1 Information owner map

Each information type has one owner:

| Information | Owner component | May be repeated? |
| --- | --- | --- |
| current file | object summary / data card | only compact name in breadcrumb |
| sample rate / channel count | object summary | no in status unless abnormal |
| time position | time navigator / overview | no in status bar |
| window length | display control | no in status bar |
| sensitivity | display control | no in status bar |
| event density | event display control / overview | no in object card |
| preparation state | status strip / analysis gate | yes if it gates analysis |
| draft count | status bar / draft panel | yes if non-empty |
| write-mode safety | status bar while write mode active | yes while active |
| non-medical boundary | object strip / result/report interpretation | concise, not noisy |

### 6.2 Control density limits

A default customer-facing toolbar should not exceed:

- 4-6 visible primary controls per group;
- 3-5 groups per row on desktop;
- 1 active primary action per decision area;
- no more than 2 visually emphasized buttons in one panel.

If visible controls exceed this, group into accordions, menus, drawers, or contextual panels.

### 6.3 Progressive disclosure

Use progressive disclosure when:

- control is advanced;
- action is rare;
- action is dangerous;
- action is export/audit rather than current task;
- explanation is long;
- customer does not need it for the next decision.

Do not hide:

- current data identity;
- primary waveform/result;
- primary next step;
- error/recovery path;
- write mode state;
- non-medical boundary where interpretation risk is present.

---

## 7. State Feedback Standard

Every meaningful page/component must cover:

- ideal/default;
- first-use empty;
- no-data empty;
- loading under 1 second;
- loading over 1 second;
- long task over 3 seconds;
- partial data;
- stale data;
- validation error;
- system error;
- permission/disabled;
- success;
- cancelled/retried;
- reduced motion.

### 7.1 Empty state must answer

1. What should appear here?
2. Why is it empty now?
3. What can the user do next?
4. Is no action required?

### 7.2 Loading state must answer

1. What is the system doing?
2. Is progress measurable?
3. Can the user cancel, continue elsewhere, or retry?
4. What remains safe and unchanged?

For EEG waveform loading, do not hide the previous window silently. Label stale display or show loading overlay.

### 7.3 Error state must answer

1. What happened?
2. What data/task is affected?
3. What can the user do?
4. What support/debug id is safe to copy?
5. What private path/secret must not be exposed?

### 7.4 Disabled state must answer

A disabled action must explain the missing prerequisite:

- no data selected;
- preparation plan not confirmed;
- no event markers;
- method not suitable for this dataset;
- teaching data does not include this feature;
- permission missing.

---

## 8. Visual System and Tokens

### 8.1 Token hierarchy

Use three layers:

1. Primitive tokens: raw values such as blue.600, space.4, radius.8.
2. Semantic tokens: text.primary, surface.card, status.warning, chart.event.
3. Component tokens: button.primary.bg, input.border.error, table.row.selected.

Components should use semantic/component tokens, not random raw values.

### 8.2 Required token groups

```text
color.surface.page
color.surface.card
color.surface.subtle
color.text.primary
color.text.secondary
color.text.muted
color.border.subtle
color.border.strong
color.action.primary
color.action.primary.hover
color.status.success
color.status.warning
color.status.error
color.status.info
color.chart.categorical.*
color.chart.event
color.chart.selection
space.1 / 2 / 3 / 4 / 6 / 8
radius.sm / md / lg / xl / pill
shadow.card / popover
focus.ring
motion.duration.fast / normal / slow
```

### 8.3 Typography

Rules:

- page title: clear but not oversized;
- section titles: concise and task-oriented;
- labels near controls;
- units visible next to scientific values;
- no tiny critical warnings;
- no mojibake, replacement characters, or broken Chinese text;
- mixed Chinese/English terms only when the English term is the scientific anchor, e.g. PSD, ERP, PAC, Epoch.

### 8.4 Color semantics

- blue: primary action / selected navigation;
- teal/green: safe confirmed success;
- amber: caution, write draft, pending review;
- red: destructive or blocking error;
- grey: inactive/disabled/stale;
- chart colors: separated from UI status colors.

Do not use red/green as the only encoding.

### 8.5 Scientific colormap

For scientific charts:

- choose color map by data type: sequential, diverging, cyclic, categorical, binary status, uncertainty;
- show units/range/baseline/normalization;
- avoid rainbow/jet as default quantitative colormap;
- color must not imply diagnosis, causality, source localization certainty, or release approval.

---

## 9. Accessibility and Keyboard Standard

### 9.1 Minimum accessibility rules

- all interactive controls keyboard reachable;
- visible focus ring;
- accessible names for icon buttons;
- color contrast sufficient for body text and labels;
- no color-only status;
- form errors linked to fields;
- canvas has keyboard fallback and external status text;
- no auto motion that cannot be reduced or stopped;
- no important information in transient toast only.

### 9.2 Required keyboard paths for EEG workbench

- Left/Right: small pan;
- PageUp/PageDown: page pan;
- Ctrl/Cmd + plus/minus: time zoom;
- plus/minus: sensitivity change;
- Escape: cancel transient interaction or close overlay;
- Tab: predictable control order;
- Enter/Space: activate focused buttons.

Keyboard shortcuts must have a visible help entry. Shortcut help must not be the only way to discover actions.

---

## 10. Scientific and Non-Medical Boundary

### 10.1 Allowed wording

Use:

- research analysis;
- data preparation;
- candidate event;
- review support;
- descriptive metric;
- statistical result;
- scientific interpretation;
- non-medical research use;
- not for diagnosis, treatment, clinical decision-making, or emergency use.

### 10.2 Forbidden or high-risk wording without explicit regulatory decision

Avoid or block:

- diagnosis;
- confirm seizure;
- detect disease for clinical use;
- treatment recommendation;
- clinical decision;
- triage;
- patient risk prediction;
- therapy response;
- precise brain lesion localization;
- causal connectivity unless proven by method and context.

### 10.3 Interpretation layers

Reports and result pages must separate:

1. raw data;
2. processed data;
3. descriptive metrics;
4. statistical inference;
5. scientific interpretation;
6. clinical implication.

The sixth layer must generally be absent or explicitly negated for QLanalyser unless a future regulated product route is approved.

---

## 11. Teaching Mode Governance

Teaching mode has two phases:

1. Guided learning cards.
2. Protected sandbox operation with built-in data.

Rules:

- teaching data cannot be deleted, overwritten, renamed, or mixed silently with user data;
- teaching mode and normal mode must be switchable by a clear button;
- after learning cards, user should enter runnable teaching workflows, not a normal page requiring upload;
- built-in data should support end-to-end tests for each available method when scientifically appropriate;
- if a method needs event markers and teaching data lacks them, the UI must explain why;
- teaching copy must include common misunderstanding and safe interpretation;
- teaching analytics must not collect raw EEG, PHI, full report text, or free-text sensitive answers.

---

## 12. Critical Task and Human-Factors Gate

Use this for major releases, public beta, external demonstrations, or high-risk UI changes.

### 12.1 Critical task list

QLanalyser minimum critical tasks:

- select or create project;
- choose teaching vs normal mode;
- upload/select EEG file;
- inspect waveform;
- mark/restore bad channels or segments;
- confirm preparation plan;
- choose analysis method;
- understand disabled method reason;
- run analysis;
- review result and limitations;
- export report;
- recover from upload/analysis/report error.

### 12.2 Foreseeable use errors

Examples:

- user thinks event marker is data discontinuity;
- user thinks browse drag wrote bad segment;
- user starts analysis without confirmed preparation plan;
- user interprets QC warning as final conclusion;
- user treats epilepsy candidate event as diagnosis;
- user exports report without parameters/QC context;
- user deletes or overwrites teaching data;
- user cannot recover after slow waveform loading.

Each P0/P1 foreseeable use error must have a risk control and retest evidence.

### 12.3 Formative finding disposition

Every P0/P1 usability finding must record:

```yaml
FORMATIVE_FINDING_DISPOSITION:
  finding_id:
  severity:
  linked_critical_task:
  observed_issue:
  suspected_root_cause:
  design_change:
  retest_needed:
  retest_evidence:
  residual_risk:
  disposition: fixed | accepted_with_rationale | moved_to_summative | duplicate | out_of_scope
```

---

## 13. Screenshot and E2E Evidence Gate

### 13.1 Required screenshot matrix

For meaningful UI changes, capture:

```text
default_desktop_1440.png
laptop_1280.png
mobile_390.png
wide_1920_if_relevant.png
empty_state.png
loading_state.png
error_state.png
success_state.png
disabled_state.png
focus_keyboard_state.png
dense_data_state.png
```

Not every tiny CSS change needs every screenshot, but every release-level or customer-visible workflow change does.

### 13.2 Required E2E types

- happy path;
- no-data / missing prerequisite;
- slow/loading path;
- error recovery;
- disabled action reason;
- keyboard/focus path for critical controls;
- no horizontal overflow;
- no forbidden debug terms;
- data-preparation payload contract if analysis is involved;
- screenshot readback.

### 13.3 Visual acceptance is not just screenshot diff

Screenshot diff proves pixels changed. It does not prove:

- hierarchy improved;
- scientific meaning is preserved;
- accessibility is intact;
- mode interference is solved;
- user understands next step.

Human review remains required for these.

---

## 14. Interaction Interference Matrix

Before accepting any toolbar/workbench change, fill this matrix.

```yaml
INTERACTION_INTERFERENCE_MATRIX:
  surface:
  controls:
    - control:
      intention:
      layer: read_status | display | browse | write_draft | persist | analysis | export
      can_write_data: true | false
      visible_by_default: true | false
      disabled_reason_when_unavailable:
      duplicates_control:
      conflicts_with:
      recovery:
  findings:
    - severity:
      issue:
      fix:
  decision: pass | revise | block
```

### 14.1 Common interference patterns to block

| Interference | Example | Fix |
| --- | --- | --- |
| Browse/write collision | drag both pans and marks bad segment | mode separation, cursor, color, status |
| Time/epoch collision | 24 s/page next to 4 s epoch without grouping | display vs epoch review groups |
| Status/control duplication | status repeats 8 ch, Raw, 10 s/page | status only shows decision states |
| Event/data discontinuity confusion | dense marker lines look like cuts | light/aggregate marker mode and caption |
| Primary/secondary action collision | export button competes with confirm plan | demote export to records drawer |
| Teaching/normal state collision | teaching data appears as deletable upload | protected teaching object state |
| Loading/selection collision | loading overlay looks like selected region | separate stale/loading/selection layers |

---

## 15. Component Rules

### 15.1 Buttons

- One primary button per decision area.
- Destructive actions use danger style, confirmation, and recovery path.
- Disabled buttons explain reason.
- Icon-only buttons need title/aria label and tooltip.
- Repeated buttons for same action are blocked unless one is a sticky duplicate explicitly justified for long pages.

### 15.2 Cards

A card must contain one coherent idea:

- data object;
- task step;
- method prerequisite;
- result summary;
- teaching lesson;
- status/decision.

Cards must not become random containers for unrelated controls.

### 15.3 Segmented controls / modes

Use for mutually exclusive modes only:

- browse;
- select segment;
- mark bad segment;
- mark bad channel;
- epoch review.

Do not use segmented controls for actions that can all happen independently.

### 15.4 Accordions / details

Use for:

- advanced parameters;
- record/export;
- audit logs;
- technical details;
- rarely used recovery operations.

Do not hide primary next actions inside collapsed areas.

### 15.5 Tables

Tables must have:

- understandable column labels;
- units near values;
- sticky header for long tables when useful;
- empty state;
- sorting/filtering clarity;
- row selection state;
- export consistency.

---

## 16. Page Review Scorecard

Use the 8-pass review for screenshots or live pages.

```yaml
UX_DESIGN_CRITIQUE_SCORECARD:
  surface:
  screenshot_or_url:
  target_user:
  primary_task:
  L1_first_glance:
    score_0_5:
    issue:
  L2_information_architecture:
    score_0_5:
    issue:
  L3_task_flow:
    score_0_5:
    issue:
  L4_layout_spacing_alignment:
    score_0_5:
    issue:
  L5_typography_copy:
    score_0_5:
    issue:
  L6_color_state_accessibility:
    score_0_5:
    issue:
  L7_scientific_integrity:
    score_0_5:
    issue:
  L8_implementation_testability:
    score_0_5:
    issue:
  P0:
  P1:
  P2:
  decision: pass | revise | block
```

Minimum pass for public/customer beta:

- no P0;
- P1 either fixed or explicitly accepted with rationale;
- first glance, task flow, scientific integrity, accessibility all score at least 4/5;
- evidence folder exists.

---

## 17. Release Blocking Criteria

Block release if any of these are true:

### 17.1 Product / scientific blockers

- UI implies diagnosis, treatment, clinical decision, seizure confirmation, or unsupported localization/causality.
- Report/result lacks QC, parameter, method, or limitation context.
- Teaching mode allows deletion/overwrite of protected data.
- Formal analysis can run without required preparation plan when contract requires it.

### 17.2 Interaction blockers

- browse and write modes are ambiguous;
- dangerous action has no recovery/confirmation;
- status/control duplication causes user confusion;
- old/stale waveform is shown as current data;
- disabled action has no reason;
- critical task has no error recovery path.

### 17.3 Visual / accessibility blockers

- horizontal overflow at supported viewport;
- main scientific object hidden below excessive controls;
- focus path broken for critical controls;
- color-only status;
- unreadable text or mojibake;
- loading/error/empty states missing on critical path;
- customer-visible debug terms in default UI.

### 17.4 Evidence blockers

- no screenshot evidence for visual claim;
- no E2E for critical path;
- no viewport matrix for responsive claim;
- no readback of generated files;
- no evidence for human-factors risk control if P0/P1 use error was found.

---

## 18. Current Waveform Toolbar Specific Rule

The current class of problems reported by the owner is governed by this rule:

If a toolbar contains browsing controls, display controls, event visibility, epoch review length, annotation modes, candidate bad segment, bad channel, and preparation actions in the same visual band, it must be redesigned into grouped task layers before it can be considered customer-final.

Required target grouping:

```text
Object status strip:
  current file | sample rate/channel | preparation status | non-medical boundary

Browse group:
  first | previous | next | last | overview/time slider

Display group:
  window length | sensitivity | channel count | event marker density | raw/filter preview

Write/review mode group:
  browse | select segment | bad segment | bad channel | epoch review

Contextual draft actions:
  candidate | reject/remain | undo/redo | restore | clear draft

Preparation decision:
  confirm data preparation | preparation revision status

Secondary records:
  event/epoch save | download preparation record | audit history
```

Controls from a group should appear only when relevant. For example, epoch length should not compete with continuous browsing controls unless epoch review mode is active or clearly grouped as an epoch-review setting.

---

## 19. Implementation Workflow

### 19.1 Before coding

1. Read `DESIGN.md`.
2. Read this master standard.
3. Identify page archetype.
4. Fill design contract.
5. Fill interference matrix for toolbar/workbench changes.
6. Define screenshot/E2E evidence paths.
7. Decide what is out of scope.

### 19.2 During coding

1. Keep changes scoped to the page/component.
2. Preserve existing selectors unless intentionally updating tests.
3. Do not add duplicate controls to satisfy a test; update test contract if design contract changed.
4. Use semantic classes/tokens where available.
5. Keep technical/debug content behind developer-only affordances.
6. Maintain non-medical wording.

### 19.3 After coding

1. Run syntax checks.
2. Run relevant E2E.
3. Capture screenshots.
4. Check overflow and forbidden terms.
5. Review screenshot against 8-pass scorecard.
6. Write fix receipt.
7. List remaining P1/P2 follow-up honestly.

---

## 20. Templates

### 20.1 Page design contract template

```yaml
QLANALYSER_PAGE_DESIGN_CONTRACT:
  page:
  surface_url:
  owner:
  target_user:
  primary_task:
  secondary_tasks:
  primary_visual_object:
  primary_action:
  page_archetype:
  risk_level:
  normal_mode_behavior:
  teaching_mode_behavior:
  non_medical_boundary:
  information_owner_map:
    current_file:
    time_context:
    preparation_state:
    draft_state:
    method_prerequisites:
  mode_model:
    read_only:
    display:
    browse:
    write_draft:
    persist:
  controls_visible_by_default:
  controls_hidden_or_collapsed:
  forbidden_duplicates:
  expected_states:
  expected_evidence:
  decision: pass_to_build | revise | block
```

### 20.2 UI acceptance receipt template

```yaml
QLANALYSER_UI_ACCEPTANCE_RECEIPT:
  surface:
  version_or_url:
  changed_files:
  source_design_contract:
  evidence_dir:
  screenshots:
  tests:
  state_coverage:
  interference_matrix_result:
  accessibility_result:
  scientific_boundary_result:
  product_copy_result:
  accepted:
  remaining_followup:
  blocked_items:
  final_receipt:
```

### 20.3 Fast pre-merge checklist

```text
[ ] Read DESIGN.md and this master standard.
[ ] Primary task and primary action are clear.
[ ] One function has one primary control.
[ ] Browse and write modes cannot be confused.
[ ] Status does not duplicate nearby controls.
[ ] Main scientific object is dominant.
[ ] Empty/loading/error/disabled/success are covered if relevant.
[ ] No customer-visible debug terms.
[ ] No medical overclaim.
[ ] Keyboard/focus path works for critical controls.
[ ] 1440/1280/390 screenshots or justified skip.
[ ] E2E covers the critical task.
[ ] Fix receipt written.
```

---

## 21. Versioning and Governance

- This document is active from 2026-06-28.
- Page-specific design contracts can extend this document but cannot weaken it.
- Any exception must be written in the page design receipt with reason, owner, risk, and retest plan.
- Future changes should update this file and `DESIGN.md` together.
- For public release, this document must be paired with real user/owner data regression and human-factors evidence if critical tasks are claimed as validated.

---

## 22. Summary Decision

QLanalyser must stop treating UI as local decoration. UI is part of scientific workflow safety: it determines whether users select the right data, understand preparation state, avoid accidental writes, choose valid methods, interpret outputs safely, and export traceable reports.

Therefore, every QLanalyser UI change must satisfy three gates:

1. Interaction gate: no mode/control/status interference.
2. Scientific gate: no unsupported interpretation or medical overclaim.
3. Evidence gate: screenshots and E2E prove the intended task path.

If any gate fails, the UI is not ready, even if the feature technically runs.
