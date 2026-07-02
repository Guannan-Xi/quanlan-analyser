# WaveformWorkbench Customer-Level Page Review

Date: 2026-06-28  
Surface: `frontend/waveform-workbench.html`  
Reviewed URL: `http://127.0.0.1:4174/waveform-workbench.html?teaching_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=page-review-live`  
Evidence folder: `work/release_evidence/20260628-waveform-page-review-live/`

## Review Position

This review treats the current page as a customer-facing waveform workbench for non-medical EEG research and CRO-style data preparation.

The page is evaluated as:

- an EEG researcher-facing continuous waveform preview,
- a data preparation workbench,
- a shared page that can switch into an Epoch review mode for epilepsy/sleep-staging style workflows.

The page is not evaluated as a clinical diagnostic tool.

## Evidence Used

Screenshots:

- `work/release_evidence/20260628-waveform-page-review-live/01_basic_live.png`
- `work/release_evidence/20260628-waveform-page-review-live/02_epoch_live.png`
- `work/release_evidence/20260628-waveform-page-review-live/03_basic_return_live.png`

DOM/state snapshot:

- `work/release_evidence/20260628-waveform-page-review-live/live_page_states.json`

Reference wide-layout evidence:

- `work/release_evidence/20260628-waveform-workbench-same-page-toggle/01_basic_initial.png`
- `work/release_evidence/20260628-waveform-workbench-same-page-toggle/02b_same_page_after_epoch_switch.png`
- `work/release_evidence/20260628-waveform-workbench-same-page-toggle/waveform_workbench_dual_mode_contract_result.json`

Verified facts:

- Basic mode and Epoch mode switch in the same page.
- Basic mode hides Epoch controls.
- Epoch mode exposes Epoch review.
- Current narrow in-app browser viewport has no horizontal overflow.
- DOM has one topbar and one workbench; the repeated title seen in a tall full-page screenshot is a screenshot/rendering artifact, not duplicate DOM.
- In the current narrow viewport, the waveform workbench page height is about 2211 px.

## Executive Verdict

Current maturity: **good functional prototype / usable internal demo**, not yet a polished final customer page.

The core product model is now correct:

- basic waveform preview and Epoch review are distinct,
- both are available in one page,
- waveform is visible,
- the page has safe non-medical language,
- the interaction model is testable.

However, the current page still feels too much like an engineering-control workbench. The scientific object, the EEG waveform, does not dominate early enough in the page. On narrow viewports, users see title, metadata cards, and controls before the waveform. This is especially harmful for EEG users because their first trust check is not "which buttons exist" but "is the signal continuous, scaled correctly, and operable?"

## UX_DESIGN_CRITIQUE_SCORECARD

| Dimension | Rating | Evidence | Judgment |
|---|---:|---|---|
| Scientific task fit | 7/10 | Waveform, channel labels, uV/row, event markers, bad segment/reject/remain concepts exist | Good foundation; waveform should be visually promoted above metadata/control bulk |
| Mode separation | 8/10 | Basic/Epoch switch works; Basic hides Epoch | Correct product split; still needs stronger mode explanation and entry ownership |
| First-screen clarity | 5/10 | Narrow viewport shows waveform only after large title/context/tool sections | Main object is delayed; customer may think this is a settings page |
| Control hierarchy | 6/10 | Browse/Display/Write groups exist | Better than before, but too many peer controls remain visible at once |
| Button economy | 5/10 | 16 visible controls in Basic, 17 in Epoch | Functional but dense; several controls should become secondary/advanced or icon+tooltip |
| State feedback | 6/10 | Loaded state, selected state, draft summary, right panel exist | Right panel appears too late on narrow viewports; disabled actions are hidden but mode guidance can be crisper |
| Visual polish | 6/10 | Cards, spacing, color tokens mostly coherent | Card stack is heavy; page looks spacious but not yet expert-tool compact |
| Accessibility/keyboard | 7/10 | Keyboard shortcuts exist, buttons have text | Needs visible focus review and shortcut discoverability refinement |
| Non-medical boundary | 8/10 | "科研数据准备，不用于诊断" visible | Good, but should not over-dominate waveform task area |
| Performance perception | 6/10 | Waveform loads; no horizontal overflow | Page is tall; perceived latency can feel worse because waveform appears below control blocks |

## P0 Findings

### P0-1: In narrow/in-app viewport, waveform is not the first operational object

Evidence:

- `live_page_states.json` shows:
  - topbar starts at y=12 and height≈206,
  - context cards y=236, height≈346,
  - toolbar bands y=619..1312,
  - side panel y≈1938,
  - page height≈2211.

Impact:

- A customer looking for "why is there no waveform?" may see only title/cards/controls first.
- EEG experts expect signal-first inspection. The current narrow layout delays that moment.

Required fix direction:

- On narrow and medium viewports, move waveform immediately after a compact header/context row.
- Collapse the Browse/Display/Write toolbar into a sticky/accordion command strip.
- Keep only the most important controls visible before the waveform:
  - mode switch,
  - load data,
  - time window,
  - uV/row,
  - channel count,
  - current browse/write mode.

### P0-2: The top metadata cards are too tall for the job they perform

Evidence:

- Context section takes about 346 px in current narrow viewport.
- It repeats slow-changing information: file, data state, prep state, boundary.

Impact:

- Useful, but not worth pushing waveform down by one third of the screen.

Required fix direction:

- Convert context cards into a compact single-line status strip on narrow viewports:
  - `文件: teaching...fif · 8 ch · 200 Hz · 准备: 教学/当前记录 · 科研用途`
- Keep full cards only on wide desktop if there is room.

### P0-3: Basic mode still shows the "Epoch 复核" switch at top, which is acceptable for debugging but not ideal for final customer flow

Evidence:

- Current owner request is to keep both modes in one page for debugging.
- Customer-facing basic mode will show an Epoch option even for users who only need data preparation.

Impact:

- For internal testing this is useful.
- For public/customer release, this can create conceptual leakage: data preparation users may wonder why they need Epoch review.

Required fix direction:

- Keep same-page switch for owner/debug route.
- For production entry from data preparation, either:
  - hide the switch behind "高级 / 分段复核模式", or
  - show it only when entering from epilepsy/sleep workflows, or
  - label it as "切换到分段复核工作台" with explanatory tooltip.

## P1 Findings

### P1-1: Toolbar has correct layers but too much visible control mass

Current visible control groups:

- Browse: first/prev/next/last
- Display: time window, event marker, uV preset, gain slider, channel count
- Write/review: browse/select/Epoch/candidate/bad channel/shortcut

Issue:

- All controls compete visually, especially on narrow viewports.

Recommended structure:

```text
Sticky compact command strip:
  Mode switch | Time window | uV/row | Channels | Browse/Select/Bad segment/Bad channel

Secondary drawer:
  First/Prev/Next/Last
  Event marker detail
  Gain fine adjustment
  Shortcut help
  Epoch length/count (only in Epoch review)
```

### P1-2: Right-side action panel appears too late on narrow viewport

Evidence:

- `ww-side-panel` y≈1938 in narrow view.

Issue:

- The panel is conceptually important: it tells the user whether they are only browsing or writing draft.
- It should not be below the waveform and far below controls in narrow view.

Recommended fix:

- On narrow viewport, convert the right panel into a sticky bottom action bar:
  - current mode/status,
  - selected range,
  - Reject/Remain actions when available,
  - Undo/Redo in overflow menu.

### P1-3: Browse buttons are not self-explanatory enough for customer use

Issue:

- `|<`, `<`, `>`, `>|` are compact but look like media controls, not necessarily EEG paging controls.

Recommended fix:

- Use text+icon labels where space allows:
  - `首页`
  - `上一窗`
  - `下一窗`
  - `末尾`
- In compact mode, keep icons but provide visible tooltip or `title` that uses EEG language.

### P1-4: Event marker layer can still be mistaken as data segmentation

Issue:

- Vertical event lines are visually dense in teaching oddball data.
- The caption says they are event markers, but they can still look like discontinuities.

Recommended fix:

- Default event display in Basic mode should be `minimal`/`hidden` for non-event workflows.
- Add quick toggle in legend:
  - `事件: 显示/淡化/隐藏`
- In Basic mode, label "事件标记（非断点）" closer to waveform, not only in overview caption.

### P1-5: The "加载教学数据" button remains too prominent after data is loaded

Issue:

- Once data is loaded, the primary task is waveform review, not loading again.

Recommended fix:

- After teaching data is loaded, demote this button to secondary:
  - `重新载入教学数据`
- Primary emphasis should move to current mode / waveform controls.

### P1-6: Switching Basic→Epoch preserves a normal selected segment

Observed:

- This is useful for debugging continuity.
- It may be confusing in production because a selected continuous segment is not necessarily an Epoch selection.

Recommendation:

- Define a policy:
  - debug mode: preserve selection,
  - customer mode: clear ordinary selection and show "已切换到 Epoch 复核，请重新选择 Epoch".

## P2 Findings

### P2-1: Page title is visually large for a tool surface

Recommendation:

- Reduce title size and vertical spacing after the first successful data load.
- Scientific workbenches should give vertical space to the signal.

### P2-2: Too many cards use the same rounded-card visual weight

Recommendation:

- Reserve strong cards for waveform and action panel.
- Use lighter status strips for metadata and legends.

### P2-3: Terminology can be improved for mixed expert/customer users

Current terms:

- `Reject`
- `Remain`
- `候选坏段`
- `坏道`

Recommendation:

- Keep expert terms, but add small Chinese explanation near first use:
  - `Reject 排除`
  - `Remain 保留`
  - `候选坏段（待确认）`

### P2-4: Keyboard shortcut discoverability is too hidden

Recommendation:

- Add a small "?" or "快捷键" popover near the waveform, not only in the toolbar.
- In focus state, show a small overlay:
  - `滚轮平移 · Ctrl+滚轮缩放 · S 选段 · B 返回浏览`

## Proposed Redesign Direction

### Layout vNext

```text
Header row:
  QLanalyser / WaveformWorkbench | Basic/Epoch switch | Load/reload | Back

Compact status strip:
  file · channels · sfreq · prep state · non-medical boundary

Primary work area:
  left/main: EEG waveform canvas
  right or bottom: current action state

Sticky command strip:
  time window | uV/row | channels | browse/select/candidate/bad channel | event display

Secondary drawer:
  first/prev/next/last
  fine gain
  shortcut help
  Epoch settings only when Epoch review is active
```

### Narrow viewport rule

For viewport width under 760 px:

1. Header becomes compact.
2. Metadata cards collapse into one status line.
3. Waveform appears before full toolbar.
4. Action panel becomes bottom/sticky.
5. Advanced controls collapse into expandable sections.

### Wide desktop rule

For width above 1200 px:

1. Keep waveform and action panel side by side.
2. Toolbar can remain three bands, but visually thinner.
3. Context cards can remain as a single row.

## Recommended Implementation Packets

### Packet A: Signal-first layout

Goal:

- Move waveform higher on narrow/medium viewports.
- Collapse metadata and toolbar density.

Acceptance:

- In 584 px wide viewport, waveform begins before y=700.
- In 1440 px wide viewport, waveform remains visible in first screen.

### Packet B: Action panel refactor

Goal:

- Convert right panel to sticky bottom action bar in narrow mode.
- Keep full side panel on desktop.

Acceptance:

- Selected segment actions are visible without scrolling past the waveform.
- Empty state does not show disabled write actions.

### Packet C: Production/debug mode policy

Goal:

- Keep same-page Basic/Epoch switch for owner debugging.
- Define whether customer data-preparation entry shows the switch.

Acceptance:

- Debug URL shows switch.
- Data-preparation production entry can hide or demote switch.
- Epilepsy/sleep entry opens Epoch mode directly.

### Packet D: Event-marker visual de-noising

Goal:

- Prevent event markers from looking like signal discontinuities.

Acceptance:

- Event marker mode can be hidden/light/full.
- Basic mode defaults to minimal or hidden where appropriate.
- Legend explicitly says event markers are not discontinuities.

## Current Decision

Do not start broad visual rewriting immediately. The current code is functional and testable. The next best slice is:

1. Signal-first layout for narrow/medium viewports.
2. Right action panel becomes a compact action strip on narrow viewports.
3. Keep same-page switch as a debugging tool, but add a production-entry policy.

## Receipt

```yaml
final_receipt: completed_waveform_page_customer_review_ready_for_fix_planning
route_decision: gpt55_planner_or_acceptance + browser_visual_review + script_validator
executor_evidence:
  - live_browser_screenshots_basic_epoch_basic_return
  - live_dom_state_snapshot
  - duplicate_dom_check
gpt55_acceptance: page_is_functional_but_not_final_customer_polish
next_real_artifact: signal_first_layout_fix_packet
```
