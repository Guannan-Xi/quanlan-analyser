# WaveformWorkbench Self-Audit Clean Mode Receipt

Date: 2026-06-28
Status: completed incremental fix

## Scope

This receipt closes the current WaveformWorkbench self-adversarial P1 slice:

- overview/timeline discoverability;
- overview keyboard semantics;
- customer clean mode;
- main-program entry to the clean waveform workbench;
- regression coverage for Basic and Epoch modes.

## Fixes

1. Overview/timeline discoverability
   - The overview caption now states that the timeline can be dragged for fast positioning.
   - The overview track exposes slider-like aria value text.

2. Overview keyboard semantics
   - `Home` moves to the beginning.
   - `End` moves to the end.
   - `ArrowLeft` / `ArrowRight` use the existing small pan behavior.
   - `PageUp` / `PageDown` use the existing page pan behavior.

3. Customer clean mode
   - `customer_mode=clean` collapses advanced controls on desktop too.
   - The clean mode keeps time window, uV/row, and core annotation controls visible.
   - Advanced controls remain available through `More settings`.

4. Main-program entry
   - Data preparation now includes `打开专业波形工作台`.
   - The link opens `waveform-workbench.html` with `mode_switch=hidden`, `customer_mode=clean`, and the current `api` parameter.

## Evidence

Evidence folders:

- `work/release_evidence/20260628-waveform-self-audit-clean-mode/`
- `work/release_evidence/20260628-waveform-main-entry/`

Validation:

- `node --check frontend/app.js`: passed
- `node --check frontend/waveform-workbench.js`: passed
- `node --check scripts/e2e_waveform_workbench_dual_mode_contract.mjs`: passed
- Dual-mode WaveformWorkbench E2E: passed, failed `[]`
- Epoch full WaveformWorkbench E2E: passed, failed `[]`
- Main program entry check: passed

Main-program entry resolved to:

`waveform-workbench.html?teaching_demo=auto&mode_switch=hidden&customer_mode=clean&v=main-entry&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi`

New/covered checks include:

- overview drag affordance and aria value text;
- overview Home/End keyboard seek;
- customer clean desktop advanced-control collapse;
- main-program clean workbench link.

## Protected Areas

Not touched:

- router
- Headroom
- gateway
- IPC
- model route
- TimeChart

final_receipt: completed_waveform_self_audit_clean_mode_ready_for_epilepsy_integration
