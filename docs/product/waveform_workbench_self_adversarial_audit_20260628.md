# WaveformWorkbench Self-Adversarial Audit

Date: 2026-06-28
Page: `frontend/waveform-workbench.html`
Status: active audit backlog

## Current Baseline

Recent fixes already completed:

- Basic/Epoch modes separated.
- Basic mode hides Epoch controls and event markers by default.
- Waveform appears before toolbar.
- Toolbar supports progressive disclosure.
- Empty draft box and narrow legend clutter reduced.
- Overview/progress bar is draggable.
- Dual-mode E2E passed.
- Epoch full E2E passed.

## Self-Adversarial Findings

### Global Page

P1-G01: The standalone page still exposes a debug-style Basic/Epoch switch by default.

- Why it matters: customers should arrive through a task-specific entry. Debug switching is useful for development, not always for final product.
- Current mitigation: `mode_switch=hidden` exists.
- Next fix candidate: customer links should always include `mode_switch=hidden`; only development/test links should show the switch.

P1-G02: Header/context area still consumes meaningful vertical space.

- Why it matters: EEG reading pages should prioritize the signal area.
- Next fix candidate: create a compact header mode for customer workbench entry after the user has loaded data.

### Waveform / Canvas

P1-W01: Overview drag now works, but keyboard slider semantics are incomplete.

- Why it matters: a focusable slider-like control should support at least Home/End and Arrow movement.
- Next fix candidate: add Home/End to jump to beginning/end on the overview track; ArrowLeft/ArrowRight can reuse small pan.

P1-W02: The overview track has a cursor and focus ring, but no visible text hint that it can be dragged.

- Why it matters: users may not discover the interaction.
- Next fix candidate: caption can say `拖动时间轴可快速定位` without repeating current time.

### Action Panel

P1-A01: The action panel says "下一步处理", but in pure browsing state it mostly explains that no action is active.

- Why it matters: this can still feel like an inactive task card.
- Next fix candidate: in browse mode, collapse the right panel to a compact hint; expand when selection/candidate/draft exists.

P2-A02: Reject/Remain are bilingual and professional, but could be clearer for first-time users.

- Next fix candidate: keep professional labels but add tooltip/helper text on hover or compact help.

### Toolbar

P1-T01: Desktop customer mode now puts toolbar below waveform, but all advanced controls are visible on wide screens.

- Why it matters: wide does not always mean expert; customer default should still be low-noise.
- Next fix candidate: support `customer_mode=clean` where advanced controls are collapsed even on desktop.

P2-T02: "More settings" is only visible in narrow mode.

- Next fix candidate: if `customer_mode=clean`, show it on desktop too.

### Workflow

P1-F01: Main data-preparation entry still needs confirmed routing to the customer hidden-switch URL.

- Why it matters: otherwise the polished standalone page may not be what customers reach.
- Next fix candidate: update entry points only after checking current main-workbench routing to avoid breaking existing flows.

P1-F02: Basic-to-Epoch selection carryover policy is still a product decision.

- Why it matters: in dev testing, preserving selection is convenient; in customer production, it may confuse the user.
- Next fix candidate: add production behavior that clears ordinary selection when switching into Epoch, or show an explicit conversion prompt.

## Next Recommended Fix Order

1. Add a discoverability hint for draggable overview.
2. Add keyboard semantics for the overview track.
3. Add `customer_mode=clean` that collapses advanced toolbar controls on desktop too.
4. Compact the action panel in browse mode.
5. Update main entry links once verified.

## Evidence to Maintain

- `work/release_evidence/20260628-waveform-overview-drag/`
- `work/release_evidence/20260628-waveform-toolbar-progressive-disclosure/`

final_receipt: self_adversarial_audit_protocol_and_waveform_backlog_created
