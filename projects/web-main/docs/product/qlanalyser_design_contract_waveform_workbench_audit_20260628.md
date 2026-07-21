# QLanalyser Design Contract Audit: WaveformWorkbench

Date: 2026-06-28  
Page: `frontend/waveform-workbench.html`  
Contract sources:

- `DESIGN.md`
- `docs/product/qlanalyser_project_design_system_20260628.md`
- `docs/product/waveform_workbench_DESIGN.md`

Evidence used:

- `work/release_evidence/20260628-waveform-customer-viewport-matrix/desktop_1440_top.png`
- `work/release_evidence/20260628-waveform-customer-viewport-matrix/desktop_1440_middle.png`
- `work/release_evidence/20260628-waveform-customer-viewport-matrix/laptop_1280_top.png`
- `work/release_evidence/20260628-waveform-customer-viewport-matrix/mobile_390_top.png`
- `work/release_evidence/20260628-waveform-customer-viewport-matrix/viewport_matrix_result.json`
- `work/release_evidence/20260628-waveform-customer-ui-review-fix/waveform_workbench_e2e_result.json`

Current verification:

- Browser E2E: passed, 41 checks, 0 failed.
- Viewport matrix: passed, 1440 / 1280 / 390, no horizontal overflow.
- Current page is functional, but not yet fully aligned with the project-level customer UI contract.

## 1. Page Audit Summary

```yaml
page: WaveformWorkbench
target_user: EEG researcher / CRO analyst / teaching-mode evaluator
primary_task: inspect continuous EEG and create a data-preparation draft
primary_visual_object: multi-channel EEG waveform
primary_action: browse safely, then select/mark/review segments
decision: revise
```

The page has reached functional usability. The remaining issue is information discipline: several controls and state messages still repeat the same meaning in nearby areas. This makes the page feel more like a rich engineering workbench than a calm customer-facing scientific tool.

## 2. Contract Compliance

| Contract rule | Current status | Notes |
| --- | --- | --- |
| Waveform visible in first desktop viewport | Pass | 1440 screenshot shows waveform in first viewport. |
| One timeline control | Pass after latest fix | Generic lower time slider removed; overview strip remains. |
| No horizontal overflow | Pass | 1440 / 1280 / 390 all passed. |
| Browse mode does not write draft | Pass | E2E confirms safe browse behavior. |
| Default UI avoids developer debug state | Mostly pass | Cache/schema/debug text is hidden; some evidence JSON may display mojibake in terminal but UI screenshots are readable. |
| One function, one primary place | Partial | Several repeated facts remain: event marker explanation, mode/safety, display parameters, draft/action hints. |
| Status is concise and non-duplicative | Partial | Time duplication fixed; display/mode/safety still appear in multiple places. |
| Dangerous actions separated | Pass but visually noisy | Danger zone is separated, but disabled history/danger buttons still occupy attention before selection. |
| Mobile preview/light-operation | Partial | No overflow; toolbar remains long but acceptable for preview. Needs product decision before dense mobile review. |

## 3. Duplicate Information Findings

### D1. Event marker explanation repeated

Locations:

- Overview caption says event vertical lines are non-discontinuities.
- Legend also says event marker is non-discontinuity.

Impact:

- Both are useful, but showing the same explanation twice in the same visual area adds noise.

Recommended fix:

- Keep the explanation in overview caption when event markers are visible.
- Shorten legend item to `事件标记`, or move the legend to a collapsible `图例` row.

Priority: P1

### D2. Browse mode repeated

Locations:

- Active `浏览` mode button.
- Status chip: `模式 浏览模式`.
- Status warning: `浏览模式不会写入草稿`.
- Right panel: `当前是安全浏览状态，不会写入草稿`.

Impact:

- User sees the same safety message multiple times.
- The important distinction is browse vs write mode; once visible, it should not be repeated in every region.

Recommended fix:

- Keep active mode button as the mode source.
- Keep one safety message, preferably in the right panel before selection or in status chip after toolbar scroll.
- Remove status `模式` chip when toolbar is visible, or make status bar show only `选区 / 草稿 / 安全提示`.

Priority: P0/P1 because it affects overall clarity.

### D3. Display parameters repeated

Locations:

- Display controls show time window, event marker, uV/row, channel count.
- Status chip repeats `显示 8 ch · 42 uV/row · Raw`.

Impact:

- On desktop, controls and status are visible at the same time, so this is redundant.
- On scrolled view, status can be useful. The design needs one source depending on layout/scroll.

Recommended fix:

- Option A: remove `显示` status chip from default desktop view.
- Option B: keep it only when the toolbar is out of view or make it part of a sticky compact status bar.
- Current quickest fix: status bar becomes `选区 / 草稿 / 安全边界` only.

Priority: P1

### D4. Draft state repeated

Locations:

- Status chip says `草稿 无`.
- Right panel draft box says no draft and tells the user to select a waveform segment.
- Right panel primary hint also tells the user to select a segment.

Impact:

- Repetition is visible before the user has done anything.
- The right panel should own draft/action guidance; status should not repeat empty draft unless there is a non-zero draft count.

Recommended fix:

- Hide `草稿 无` in status.
- Show draft chip only when draft count > 0.
- Keep detailed draft state in the right panel.

Priority: P1

### D5. Header and context boundary repeated

Locations:

- Header paragraph says all actions only write preparation draft and do not modify raw data.
- Context card says research data preparation, not for diagnosis.
- Right panel says current actions only write draft and do not modify raw EEG.
- Status warning repeats browse/write safety.

Impact:

- Boundary is important, but repeated boundary text weakens readability.

Recommended fix:

- Header: short product task statement only.
- Context card: keep non-medical boundary.
- Right panel/status: only show write-safety when in write mode or when a selection exists.

Priority: P1

## 4. Button And Control Findings

### B1. Disabled history/danger buttons are too visible before selection

Locations:

- Undo / Redo / Restore are visible but disabled before meaningful draft exists.
- Clear actions are visible in danger zone even when no draft exists.

Impact:

- Disabled controls make the page feel complex and inactive.
- They distract from the first task: select or browse waveform.

Recommended fix:

- Hide history actions until there is an undo stack, redo stack, restored segment, or draft.
- Hide danger zone until there is a draft/candidate to clear.
- Keep keyboard undo/redo support unchanged.

Priority: P1

### B2. Mode group has too many equal-weight actions

Locations:

- Browse, Select, Epoch Review, Candidate Bad Segment, Bad Channel, Shortcut.

Impact:

- Professional users can handle modes, but customer demos may read them as parallel primary actions.

Recommended fix:

- Keep `浏览 / 选段 / Epoch 复核` as visible core.
- Move `候选坏段 / 坏道 / 快捷键` into secondary row or `更多标注`.
- Do not remove features; reduce default visual weight.

Priority: P2 for desktop, P1 for mobile.

## 5. Scientific / EEG Expert Findings

### S1. Waveform priority is acceptable

The current desktop screenshot gives the waveform enough space. After removing the duplicate time slider, the waveform area is cleaner.

Decision: pass.

### S2. Event markers still risk being interpreted as discontinuities

The overview and waveform event lines are visually dense in teaching oddball data. The caption says they are not discontinuities, but the density still competes with waveform reading.

Recommended fix:

- Keep default event display as light.
- In legend, use `事件标记` without repeating explanation.
- Consider auto-fading event lines further when density is high.

Priority: P1.

### S3. Non-medical boundary is correct but noisy

The wording is safe, but appears in too many places. Keep one persistent boundary and one contextual write-safety message.

Priority: P1.

## 6. Accessibility And Visual Regression Findings

Current evidence:

- 1440 / 1280 / 390 screenshots exist.
- No horizontal overflow.
- E2E validates waveform ink, pan/zoom, selection, write draft, epoch selection, and scroll persistence.

Remaining evidence gaps:

- Focus-keyboard screenshot not captured in the latest matrix.
- Empty/loading/error screenshots are not part of the current page-level audit pack.
- Mobile dense review is not designed as a full workflow; treat mobile as preview/light-operation until a dedicated compact flow exists.

Priority: P2 for current internal iteration; P1 before external release claim.

## 7. Recommended整改 Order

### Packet A: Status and duplicate-text cleanup

Goal: make the default page obey "one fact, one source".

Changes:

1. Status bar should show:
   - selected segment only when selected;
   - draft count only when count > 0;
   - one safety hint, not mode + safety + draft all at once.
2. Remove display summary from status when display controls are visible.
3. Remove `草稿 无` from status.
4. Shorten legend event label to `事件标记`.
5. Keep non-medical boundary in context card only; contextual write safety remains in right panel.

Expected result:

- Status bar becomes quieter.
- Right panel owns next action.
- Overview owns time and event context.

Priority: P0/P1.

### Packet B: Right-panel action visibility cleanup

Goal: remove inactive button noise.

Changes:

1. Hide history actions until history exists.
2. Hide danger zone until there is something to clear.
3. Keep disabled state for controls that remain visible.
4. Preserve E2E selectors by allowing hidden state assertions.

Priority: P1.

### Packet C: Mode-control hierarchy cleanup

Goal: reduce equal-weight button field.

Changes:

1. Keep browse/select/epoch review visible.
2. Move candidate bad segment, bad channel, shortcut help into a secondary annotation cluster or compact secondary row.
3. On mobile, collapse secondary annotation controls more aggressively.

Priority: P2 desktop, P1 mobile.

### Packet D: Evidence-state matrix

Goal: complete visual QA according to project design system.

Add screenshots/tests for:

- empty state;
- loading state;
- error state;
- keyboard focus state;
- selected/write mode state;
- draft-present state;
- mobile preview state.

Priority: P1 before release-level visual claim.

## 8. Acceptance Checklist For Next Fix

After Packet A/B, the page should satisfy:

- No duplicate timeline controls.
- No duplicate time window in status.
- No duplicate event "non-discontinuity" explanation.
- No `草稿 无` chip when there is no draft.
- No disabled danger zone visible when there is nothing to clear.
- One clear next action in the right panel.
- Waveform still visible in first desktop viewport.
- E2E still passes.
- 1440 / 1280 / 390 viewport matrix still passes.

## 9. Decision

Current page decision: `revise`.

Functional quality is acceptable, but customer-facing information discipline still needs one more cleanup pass before it should be treated as the final interaction version.

Next implementation target:

`Packet A + Packet B` in one small UI cleanup slice.

