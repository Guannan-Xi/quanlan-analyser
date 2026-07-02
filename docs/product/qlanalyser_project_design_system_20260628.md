# QLanalyser Project Design System

Date: 2026-06-28  
Status: active project-level design specification  
Source contract: `DESIGN.md`  
Knowledge sources used:

- `D:\QuanLanKnowledgeBase\manifests\design\GOOGLE_LABS_DESIGN_MD_CONTRACT_TOOL_20260627.md`
- `D:\QuanLanKnowledgeBase\learning-notes\design\QUANLAN_DESIGN_PRINCIPLES_V1_CN.md`
- `D:\QuanLanKnowledgeBase\learning-notes\design\DESIGN_TOKENS_VISUAL_REGRESSION_GATE_CN.md`
- `D:\QuanLanKnowledgeBase\learning-notes\design\B2B_SCIENTIFIC_DASHBOARD_SCREENSHOT_AUDIT_CHECKLIST_CN.md`
- `D:\QuanLanKnowledgeBase\learning-notes\design\B2B_SCIENTIFIC_DASHBOARD_VISUAL_ANTIPATTERN_FIXTURES_CN.md`
- `D:\QuanLanKnowledgeBase\learning-notes\design\DATA_VIZ_ACCESSIBILITY_CHARTABILITY_CN.md`
- `D:\QuanLanKnowledgeBase\learning-notes\design\SCIENTIFIC_COLORMAP_AND_CHART_COLOR_GATE_CN.md`
- `D:\QuanLanKnowledgeBase\learning-notes\qlanalyser\QLANALYSER_EEG_GLOSSARY_CN.md`
- `D:\QuanLanKnowledgeBase\learning-notes\qlanalyser\HUMAN_FACTORS_FORMATIVE_SUMMATIVE_EVIDENCE_PACK_STANDARD_CN.md`

## 1. Design Goal

QLanalyser should feel like a professional EEG research workspace:

- credible enough for labs and CRO teams;
- clear enough for customers to operate without developer guidance;
- scientifically careful enough to avoid diagnosis or unsupported certainty;
- stable enough for repeated analysis and report delivery.

The product must not look like:

- a script launcher;
- an internal acceptance dashboard;
- a generic SaaS template;
- a medical diagnostic viewer;
- a demo gallery with disconnected methods.

## 2. Target Users

### Primary

- EEG researchers and lab members.
- CRO analysts.
- Neuroscience students and trainees.
- Product evaluators testing teaching data and synthetic fixtures.

### Secondary

- Internal QA/reviewers.
- Method developers.
- Customer-success staff preparing demonstrations.

Developer/debug information may exist for secondary users, but must not pollute the default primary-user UI.

## 3. Information Architecture

Project-wide navigation should follow this mental model:

1. Project
2. Data
3. Preparation
4. Analysis
5. Results
6. Reports
7. Review / Validation
8. User / Billing / Help
9. Teaching / Sandbox

### Page responsibilities

| Page | Main job | Must not contain |
| --- | --- | --- |
| Project Management | Select/create/manage projects | analysis method cards, waveform controls, billing |
| Data Management | Upload/select files | analysis execution controls |
| Data Preparation | inspect waveform, QC, preprocessing plan | method-selection grid as primary content |
| Analysis | choose/run methods with prerequisites | raw data editing, QC as independent analysis method |
| Results | inspect outputs, figures, tables | unrelated project CRUD |
| Reports | package/export/deliver report | raw debug artifacts as primary UI |
| Teaching Mode | protected end-to-end learning sandbox | deletable teaching data, unclear normal/demo boundary |
| WaveformWorkbench | professional EEG reading and preparation | duplicate timeline controls, hidden waveform, static preview |

## 4. Visual Hierarchy

Every screen must have:

1. one primary visual focus;
2. one clear next action;
3. one status source for each fact;
4. clear separation between safe, normal, and dangerous actions.

### Hierarchy checklist

- Can a new user identify the main task in 5 seconds?
- Is the scientific object larger than surrounding controls?
- Is there only one primary action in the current decision area?
- Are secondary actions visually quieter?
- Are dangerous actions separated and confirmed?
- Are repeated facts removed?

## 5. Layout System

### Desktop

- Max content width: approximately 1440-1540px.
- Page padding: 24px desktop, 12-16px mobile.
- Workbench pages: main scientific panel first, side decision panel second.
- Avoid side panels wider than needed when they reduce waveform/plot readability.

### Suggested grids

#### Workbench layout

```text
main-grid:
  columns: minmax(0, 1fr) minmax(300px, 360px)
  gap: 16px
  collapse: 980px
```

#### Dashboard layout

```text
dashboard-grid:
  columns: repeat(12, minmax(0, 1fr))
  gap: 16px
  card-radius: 16-20px
```

#### Form/detail layout

```text
master-detail:
  columns: minmax(520px, 1fr) minmax(340px, 420px)
  gap: 16px
  collapse: 1100px
```

## 6. Tokens

The project should progressively converge on semantic tokens. Existing CSS variables may be migrated gradually.

### Required token groups

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
```

### Token rules

- Components should use semantic/component tokens, not random raw values.
- Status colors must be semantic, not only brand blue.
- Focus ring must be visible and tokenized.
- Chart palette must be separate from brand palette.
- Scientific colors must not imply unsupported certainty.

## 7. Typography

Recommended Chinese/English stack:

```css
font-family: "Inter", "Segoe UI", "Microsoft YaHei", sans-serif;
```

### Scale

| Use | Desktop | Mobile |
| --- | ---: | ---: |
| Page title | 28-36px | 26-30px |
| Section title | 18-22px | 17-20px |
| Body | 14-16px | 14-16px |
| Label | 12-13px | 12-13px |
| Scientific axis/legend | >= 12px UI, >= 18px exported figure | >= 12px UI |

Rules:

- Avoid long paragraphs in control panels.
- Use labels near controls.
- Do not use tiny text for critical scientific units or warnings.
- No mojibake, replacement characters, or literal question marks in Chinese UI.

## 8. Components

### Buttons

| Type | Use | Rule |
| --- | --- | --- |
| Primary | one next action | one per decision area |
| Secondary | alternative normal action | lower visual weight |
| Ghost | navigation/help/low-risk action | not for destructive actions |
| Danger | delete/clear/irreversible-like action | separated, confirmed |
| Disabled | impossible action | avoid dominating default UI |

### Cards

Cards should contain one coherent idea:

- status summary;
- next action;
- result summary;
- method prerequisite;
- teaching step.

Do not mix unrelated functions in one card.

### Status chips

Use chips for concise state only:

- mode;
- selected data;
- prepared/unprepared;
- draft count;
- warning/error.

Do not use chips to repeat timeline, chart legend, or selected row information.

### Timelines and progress controls

One timeline control per task:

- For waveform browsing, prefer a professional overview strip that can encode current window, event density, bad segments, and retained segments.
- Do not place a second generic slider directly below it unless it serves a different explicit job.

## 9. Scientific Visualization Rules

### EEG waveform

Required:

- visible waveform after file/teaching data selection;
- pan and zoom;
- amplitude control in uV/row;
- channel count/visibility;
- Raw/Filter state;
- mode separation: browse vs marking/review;
- event markers visually lighter than waveform;
- overview/minimap for continuous context.

Avoid:

- static preview images as main waveform;
- old data remapped into a new time window;
- duplicate timeline controls;
- event markers that visually look like discontinuities;
- hidden or delayed waveform behind a "run QC preview" task.

### Result figures

Required:

- method name;
- units;
- parameter summary;
- data/preparation provenance;
- interpretation boundary;
- export readiness.

For quantitative charts:

- avoid rainbow/jet as default;
- show scale/legend;
- use accessible color choices;
- do not imply diagnosis, treatment, or clinical decision.

## 10. Copywriting

### Preferred wording

- 当前为浏览模式，不会写入草稿
- 已写入准备草稿
- 科研数据准备，不用于诊断
- 候选事件
- 候选坏段
- 剔除 Reject
- 保留 Remain
- 请选择数据
- 请先确认数据准备方案

### Avoid in customer UI

- manifest
- runner
- gate
- acceptance
- artifact count
- schema version
- dispatch
- cache loaded range
- durable epoch set
- active status

These may appear in developer evidence files, not default customer UI.

## 11. Interaction Rules

### General

- Clicks should produce visible feedback.
- Locked actions should explain what prerequisite is missing.
- Loading states should say what is loading and whether old data is stale.
- Empty states should teach the next step.
- Errors should be recoverable and not blame the user.

### Keyboard and mouse for waveform

- Normal wheel: horizontal browsing.
- Ctrl/Cmd + wheel: zoom time window.
- +/-: amplitude sensitivity.
- Ctrl/Cmd +/-: time zoom.
- PageUp/PageDown: previous/next page.
- Left/Right: small pan.
- Browse mode must not write preparation drafts.

## 12. Accessibility

Minimum:

- visible keyboard focus;
- sufficient contrast;
- labels for inputs;
- no color-only state;
- disabled controls identifiable;
- touch targets large enough on mobile;
- no horizontal overflow at 1440, 1280, 390 widths.

For release-level UX:

- test empty/loading/error/success/disabled/focus states;
- inspect dense data screens;
- inspect mobile/narrow viewport;
- record screenshot evidence.

## 13. Teaching Mode

Teaching mode is a protected sandbox:

- teaching data cannot be deleted or overwritten;
- entry must clearly show teaching mode;
- customers can run end-to-end workflows without upload;
- normal mode and teaching mode should not silently mix state;
- teaching cards should lead to real runnable method workflows.

## 14. Human-Factors Review

For customer-facing release claims, screenshots and E2E are not enough. A higher gate should include:

- critical task list;
- target user type;
- test environment;
- observed confusion points;
- P0/P1 finding disposition;
- retest evidence.

Use this for major release, not every tiny CSS change.

## 15. Visual Regression Evidence

For meaningful UI changes, create an evidence folder with:

```text
default_desktop_1440.png
laptop_1280.png
mobile_390.png
empty_state.png
loading_state.png
error_state.png
disabled_state.png
focus_keyboard_state.png
e2e_result.json
visual_review_result.json
```

Release should block on:

- horizontal overflow;
- hidden main task;
- duplicate primary controls;
- unreadable text;
- mojibake;
- dangerous action ambiguity;
- scientific overclaim;
- broken keyboard/focus path for critical controls.

## 16. Page Audit Template

For each page, reviewers should fill:

```yaml
page:
target_user:
primary_task:
primary_visual_object:
primary_action:
duplicate_information:
duplicate_controls:
customer_visible_debug_terms:
mode_or_boundary_clarity:
empty_loading_error_states:
accessibility_risks:
scientific_or_non_medical_boundary:
P0:
P1:
P2:
recommended_changes:
evidence_paths:
decision: pass | revise | block
```

## 17. WaveformWorkbench Immediate Application

Current known rules already applied or being applied:

- Keep only one timeline control: overview strip.
- Remove duplicate status time window when overview/time controls already show it.
- Hide developer/cache/debug status from default UI.
- Keep waveform visible in first desktop viewport.
- Keep write actions hidden or disabled until selection exists.
- Keep browse mode safe and non-writing.

Next cleanup candidates:

1. Legend vs status chip duplication.
2. Header boundary vs side-panel safety text duplication.
3. Toolbar display controls vs status display chip duplication.
4. Right-panel disabled buttons occupying too much attention before selection.

## 18. Acceptance Summary

A QLanalyser page is acceptable when:

- the user knows the page's job in 5 seconds;
- the main scientific object is visually dominant;
- one function has one primary location;
- status is concise and non-duplicative;
- all critical states are visible and understandable;
- non-medical boundaries are clear but not noisy;
- tests and screenshots prove the claim.
