# QLanalyser Self-Adversarial UI Audit Protocol

Date: 2026-06-28
Status: active protocol
Scope: all QLanalyser customer-facing pages, especially WaveformWorkbench, data preparation, module selection, results, reports, teaching mode, and review workbenches.

## Why This Exists

Recent WaveformWorkbench reviews showed a failure mode:

- user screenshots exposed problems faster than normal functional E2E;
- local tests proved that controls worked, but did not always prove that the page felt clear, scientific, or customer-ready;
- incremental fixes could create hidden interference, such as duplicated time/status information, control hierarchy drift, or layout-dependent automation misses.

This protocol makes Codex run a self-adversarial review before accepting UI work. The reviewer must attack the design from multiple roles, not merely verify that buttons exist.

## Non-Negotiable Source Contracts

Every audit must read or apply:

1. `DESIGN.md`
2. `docs/product/waveform_workbench_DESIGN.md` when the page contains EEG waveform/data-preparation behavior
3. `docs/product/qlanalyser_project_design_system_20260628.md` when visual-system consistency matters
4. `docs/product/qlanalyser_ui_interaction_visual_governance_master_20260628.md` when release/customer readiness is claimed

Page-specific contracts can add stricter rules but cannot weaken the above.

## Self-Adversarial Roles

The same Codex thread must explicitly separate these roles:

### 1. Product Owner

Question:

- What is the single job this page helps the customer complete?
- Is the next action obvious without reading documentation?
- Does the page avoid teaching/debug/internal-system language in the default view?

Failure examples:

- controls appear before the scientific object;
- the page looks like an internal engineering console;
- the customer sees mode switches meant only for debugging.

### 2. EEG Researcher / Neuroscience Expert

Question:

- Is the waveform or result evidence the primary object?
- Are EEG reading habits respected: continuous time browsing, amplitude scaling, channel labels, time-window control, event/bad-segment layers?
- Are basic preview and epoch review separated correctly?

Failure examples:

- the waveform looks static;
- event markers look like data discontinuities;
- epoch controls appear in a basic data-preparation preview.

### 3. UI Red Team

Question:

- What is duplicated?
- What looks clickable but is not?
- What is clickable but has no affordance?
- Which controls compete with each other?
- Which status blocks say the same thing twice?

Failure examples:

- overview bar shows time position, and another status block repeats the same position;
- two buttons do the same thing with different labels;
- a progress bar is visually strong but cannot be dragged.

### 4. Workflow Tester

Question:

- Can a customer finish the full task from first screen to output?
- Does every step have a reversible/safe state?
- Are disabled buttons hidden or explained?
- Does an action create the right draft/persistent artifact layer?

Failure examples:

- a button is visible but disabled with no reason;
- a draft appears to modify raw EEG;
- switching modes carries stale selections without explanation.

### 5. Accessibility / Keyboard Reviewer

Question:

- Can the main task be performed with keyboard shortcuts or focusable controls?
- Are interactive regions labeled?
- Does a slider/overview strip expose that it can be manipulated?

Failure examples:

- draggable timeline has no cursor, focus, or label;
- keyboard shortcuts conflict across Basic and Epoch modes;
- focus order starts with low-priority controls before the waveform.

### 6. Visual System Auditor

Question:

- Are spacing, typography, colors, and elevation consistent?
- Does visual weight match task importance?
- Are warnings/danger actions visually separated from ordinary actions?

Failure examples:

- empty draft boxes consume space;
- legends and badges compete with the waveform;
- too many equal-weight cards make the page feel noisy.

### 7. Automation Skeptic

Question:

- Do tests verify behavior or merely presence?
- Could a layout change make the test click the wrong place?
- Does the E2E use fresh coordinates after scrolling/layout changes?

Failure examples:

- a test keeps an old Canvas bounding box after mode buttons scroll the page;
- screenshots are captured but never inspected against layout rules;
- a static validator passes while the customer flow is broken.

## Four-Layer Audit Order

Audits must run in this order.

### Layer A: Global Page Audit

Check:

- page goal;
- first-screen object hierarchy;
- customer/debug boundary;
- mode and entry strategy;
- no horizontal overflow;
- no obvious repeated status.

Required question:

> If this were the final customer-facing page, what would embarrass us in a live demo?

### Layer B: Functional Region Audit

For each region:

- header/context;
- waveform/canvas;
- overview/timeline;
- action panel;
- toolbar;
- legend/status;
- teaching/customer mode controls.

Check:

- purpose;
- priority;
- whether it should be visible by default;
- whether it duplicates another region;
- whether it has a clear empty/loading/error/ready state.

### Layer C: Control-Level Audit

For every button/select/slider/drag target:

- user-facing name;
- task owner;
- enabled/disabled condition;
- visible/hidden condition;
- side effect;
- undo/recovery path;
- test coverage.

Required red-team prompt:

> Could a customer reasonably assume this control does something else?

### Layer D: Business Workflow Audit

Run or script:

- open page;
- load teaching data;
- browse/pan/zoom;
- drag overview timeline;
- select segment;
- reject/remain/undo/redo;
- mark bad segment;
- mark bad channel;
- switch Basic/Epoch;
- hide customer debug switch;
- verify non-medical wording;
- verify no protected route/module touched.

## Minimum Evidence Pack

For any customer-facing UI change, the acceptance pack must include:

- screenshot: desktop customer mode;
- screenshot: narrow/embedded customer mode;
- screenshot: main interaction state;
- JSON: E2E result with failed `[]`;
- proof that no router/Headroom/gateway/IPC/model route was touched;
- list of unresolved P1/P2 risks.

For WaveformWorkbench specifically:

- Basic mode screenshot;
- Epoch mode screenshot;
- waveform ink/non-empty check;
- overview drag or pan check;
- selection/review draft check;
- stale-coordinate protection in E2E when layout changes.

## Acceptance Rule

Do not accept a UI slice only because:

- syntax passes;
- buttons exist;
- one screenshot looks acceptable;
- E2E says "passed" without checking the relevant user behavior.

Accept only when:

- product owner role says the page goal is clear;
- EEG expert role says the signal/evidence behavior is scientifically sensible;
- UI red team has no P0/P1 unresolved finding;
- workflow tester can complete the core flow;
- automation skeptic confirms tests cover the actual changed behavior.

## Standard Self-Adversarial Receipt

Every significant UI fix should close with:

```text
self_adversarial_roles:
global_page_findings:
region_findings:
control_findings:
workflow_findings:
fixes_applied:
evidence:
remaining_risks:
final_receipt:
next_real_artifact:
```

