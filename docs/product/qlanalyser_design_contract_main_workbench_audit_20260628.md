# QLanalyser Design Contract Audit: Main Data-Preparation Workbench

Date: 2026-06-28  
Page: main workbench `#analysis` / data preparation  
Target URL:

`http://127.0.0.1:4174/?customer_demo=auto&teaching_demo=auto&api=http://127.0.0.1:8001/api#analysis`

Contract sources:

- `DESIGN.md`
- `docs/product/qlanalyser_project_design_system_20260628.md`
- `docs/product/waveform_workbench_DESIGN.md`

Evidence used:

- `work/release_evidence/20260628-main-workbench-design-audit/main_workbench_design_audit_probe.json`
- `work/release_evidence/20260628-main-workbench-design-audit/desktop_1440_analysis_top.png`
- `work/release_evidence/20260628-main-workbench-design-audit/desktop_1440_analysis_middle.png`
- `work/release_evidence/20260628-main-workbench-design-audit/laptop_1280_analysis_top.png`
- `work/release_evidence/20260628-main-workbench-design-audit/mobile_390_analysis_top.png`

Probe result:

- Active page: `analysis`
- 1440 / 1280 / 390: no horizontal overflow
- Customer-visible debug terms: none from the checked list
- Visible controls on desktop probe: 46
- Preview wording count radar: high (`预览` appears many times)

## 1. Page Audit Summary

```yaml
page: Main Data-Preparation Workbench
target_user: EEG researcher / CRO analyst / teaching-mode customer
primary_task: select a dataset, inspect waveform, adjust preparation settings, confirm data preparation
primary_visual_object: EEG waveform preview
primary_action: confirm data preparation after waveform/preprocessing review
decision: revise
```

The page is functionally usable and has no overflow. The remaining issue is information architecture density: the first screen contains a data queue, step cards, waveform controls, preprocessing panel, mode controls, inline status chips, and teaching boundary text. The middle screen then repeats preparation explanation, event/segment saving, and next-step controls that already exist above.

## 2. Contract Compliance

| Contract rule | Status | Notes |
| --- | --- | --- |
| Waveform/scientific evidence first | Partial | Waveform is visible but competes with many controls and side cards. |
| One function, one primary place | Partial | Data preparation confirmation appears in side panel and is explained again in lower next-step card. |
| Default UI not debugging | Pass | No visible manifest/runner/gate/schema/cache terms in probe. |
| Status concise and non-duplicative | Partial | Inline status chips repeat mode/window/display/reference/selection/draft facts near controls. |
| Teaching mode boundary visible | Pass but noisy | Teaching banner and data queue both communicate protected teaching data. |
| No horizontal overflow | Pass | 1440 / 1280 / 390 passed. |
| Dangerous actions separated | Partial | Restore/remove/edit actions are visible in dense grids before user intent is clear. |

## 3. P0 / P1 / P2 Findings

### P0-1: Mid-page duplicate panels weaken task clarity

Locations:

- `data-testid="preprocessing-readiness-panel"`
- `data-testid="event-epoch-panel"`
- `data-testid="data-preparation-submit-last"`

Problem:

- These repeat information/actions already handled by the single-file preview panel and right-side preprocessing panel.
- The page says "confirm button is fixed above", then still shows a lower "next step" panel.

Impact:

- User may think there are two workflows: upper waveform workflow and lower preparation workflow.

Recommended fix:

- Keep selectors for tests, but visually collapse these panels into a compact "更多记录与导出" details region, or hide them until the user has a prepared revision / event mapping need.
- The primary confirm action should remain only in the right-side preprocessing panel.

### P0-2: Status chips repeat nearby controls

Observed in screenshot:

- Mode chip repeats active mode buttons.
- Time window chip repeats time-window selector and navigator.
- Channel/sensitivity display repeats controls.
- Reference chip repeats preprocessing side panel.
- Draft and selection chips repeat side/draft context.

Recommended fix:

- Main status area should only show exceptional/non-obvious state:
  - active selected segment if any;
  - non-empty draft count;
  - plan confirmation/revision;
  - warning if write mode is active.
- Hide empty/default chips.

### P1-1: Data queue and teaching banner repeat protected-data explanation

Locations:

- Top teaching banner.
- Data queue protected note.
- Selected teaching file card.

Recommended fix:

- Keep top teaching banner as mode-level context.
- In data queue, replace long protected note with a compact badge: `教学数据 · 受保护`.

### P1-2: Too many equal-weight controls in first viewport

Observed:

- Browse buttons, zoom buttons, reset, mode buttons, start input, time window, gain, channels, filter, reference/filter, shortcuts.

Recommended fix:

- Keep browse/time/gain/channel as primary visible controls.
- Move filter/reference/shortcuts into side preprocessing panel or a compact secondary row.
- Keep mode controls visible but visually grouped as "浏览 / 标注".

### P1-3: Preview edit cards are too dense

Locations:

- Candidate bad segment
- Confirm candidate
- Restore delete
- Add label
- Mark bad channel
- Discard candidate

Recommended fix:

- Show only actions relevant to current state:
  - no selection: show guidance, not action grid;
  - selected segment: show candidate/confirm/reject-like actions;
  - existing draft: show restore/discard/history.

### P1-4: Event/epoch saving is not clearly scoped

Problem:

- It appears inside data preparation, but analysis task also has event-dependent methods.

Recommended fix:

- Keep event/epoch saving but subordinate it under data-preparation records or method prerequisites.
- Do not make it look like a second primary workflow.

### P2-1: Step cards consume vertical space after user is already in step 2/3

Recommended fix:

- Use compact horizontal progress with current step only.
- Collapse details after data is selected.

### P2-2: Mobile is usable but not designed for dense review

Recommended fix:

- Treat mobile as preview/light operation.
- Later add a compact mobile-specific preparation flow if needed.

## 4. Recommended Implementation Packets

### Packet M-A: Main page duplicate-panel cleanup

Goal:

- Remove the apparent second workflow below the waveform.

Changes:

1. Convert `preprocessing-readiness-panel`, `event-epoch-panel`, and `data-preparation-submit-last` into a lower-priority collapsible/compact records area.
2. Keep existing `data-testid` selectors to avoid breaking tests.
3. Keep the primary `确认数据准备` action only in the right-side preprocessing panel.

Priority: P0.

### Packet M-B: Main status chip cleanup

Goal:

- Make inline status reflect only non-default decision information.

Changes:

1. Hide default chips for mode/window/channel/reference when controls are visible.
2. Show selection/draft/revision/warning chips only when meaningful.
3. Keep technical state in `data-*` attributes for tests.

Priority: P0/P1.

### Packet M-C: Control hierarchy cleanup

Goal:

- Reduce first-screen equal-weight controls.

Changes:

1. Keep browse/time/gain/channel primary.
2. Move filter/reference/shortcut into preprocessing side panel or secondary row.
3. Mode controls become browse vs marking group.

Priority: P1.

### Packet M-D: Preview edit action state gating

Goal:

- Avoid showing a dense action grid before selection/draft exists.

Changes:

1. Hide edit cards until a relevant selection or draft exists.
2. Show one empty-state prompt when no segment is selected.
3. Preserve keyboard and existing action handlers.

Priority: P1.

## 5. Acceptance Criteria

After Packet M-A/M-B:

- The waveform remains visible in the first desktop viewport.
- The primary confirm action appears in one place.
- Lower duplicate panels do not look like a second workflow.
- Default status chips do not repeat mode/window/channel/reference controls.
- Existing analysis-preparation gate and data-preparation confirmation E2E still pass.
- 1440 / 1280 / 390 no horizontal overflow.
- No customer-visible debug terms.

## 6. Decision

Current page decision: `revise`.

Recommended next implementation:

`Packet M-A + Packet M-B` as a small, scoped UI cleanup slice.

