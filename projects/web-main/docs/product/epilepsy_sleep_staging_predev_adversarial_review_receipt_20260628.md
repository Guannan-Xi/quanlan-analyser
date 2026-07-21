# QLanalyser Epilepsy/Sleep Staging Pre-Development Adversarial Review Receipt

Date: 2026-06-28
Status: completed design-gate hardening, waiting for optional live Claude readback if still running

## Scope

This review covers the design documents that are about to feed P0 development for:

- epilepsy-like event staging subview inside the main navigation frame;
- future sleep staging subview inside the main navigation frame;
- inherited data-preparation context;
- waveform interaction;
- correction/session state;
- Results and Report handoff contracts.

The review specifically guards against the owner's repeated UI corrections from the WaveformWorkbench and Data Preparation iterations:

- duplicate information;
- duplicate timeline/progress controls;
- buttons that look usable but cannot succeed;
- unclear Browse vs Correction mode;
- standalone upload-tool feeling;
- static or blank waveform area;
- corrected results that do not return to Results/Reports.

## Review Lanes

| Lane | Status | Evidence |
| --- | --- | --- |
| Codex/GPT-5.5 coordinator | completed | local document and code readback |
| Subagent A, positive design integrity | completed | inherited-context, information architecture, Results honesty, E2E gate review |
| Subagent B, adversarial product/QA review | completed | 10 likely owner/customer complaints and prevention rules |
| Claude 4.8 previous valid review | completed | `work/claude_arch_review/claude48_adversarial_review_docs.md` |
| Claude 4.8 live re-review after patch | completed | `work/claude_arch_review/claude48_adversarial_review_after_gate_patch.md` |
| Script validator | completed | `scripts/audit_staging_predev_gate.mjs` passed |

## Documents Updated

- `docs/product/epilepsy_sleep_staging_predev_adversarial_gate_20260628.md`
- `docs/product/epilepsy_sleep_waveform_staging_architecture_design_20260628.md`
- `docs/product/epilepsy_sleep_waveform_staging_requirements_20260628.md`
- `docs/product/epilepsy_sleep_waveform_staging_detailed_design_20260628.md`
- `docs/product/epilepsy_sleep_waveform_staging_e2e_acceptance_plan_20260628.md`
- `scripts/audit_staging_predev_gate.mjs`

## Main Findings

### P0-1: State machine must precede buttons

No visible control can enter implementation without a control-state matrix row defining:

```text
visible_when
enabled_when
disabled_reason
click_result
success_state
failure_state
undo_or_recovery
authoritative_state_owner
```

This prevents "looks clickable but does nothing" failures.

### P0-2: One fact has one owner and one primary display

Task status, plan revision, waveform time window, active mode, selected range, dirty/saved state, and result availability each need a single primary display location.

This prevents duplicate status bars, duplicate progress controls, and conflicting state chips.

### P0-3: Child subview must inherit context inside the main navigation frame

The epilepsy/sleep staging page is a main-system Analysis subview, not an independent upload tool and not a separate page that needs a return button.

Required P0 behavior:

- `embed=1`;
- `domain`;
- `task`;
- `plan`;
- `rev`;
- `contract`;
- same-frame Results target;
- ContextHeader first;
- no primary upload/select-lab-data path in inherited mode.

Direct customer URL without `embed=1` must be blocked inside the main navigation frame or guided to open the workbench from Analysis.

### P0-4: Waveform interaction must be demonstrable

A canvas or screenshot is not enough. P0 evidence must prove pan, zoom, and selection change the rendered waveform or selected state.

### P0-5: Results backflow must be honest

P0 may show a future Results contract, but it must not claim corrected artifacts are published until registered artifacts exist. P1 must register corrected tables, events, session manifest, action log, and optional evidence images through the normal Results/Report pipeline.

### P0-6: Sleep must not be over-promised

Sleep staging is not release-ready until real task, schema, waveform/hypnogram UI, correction commands, saved session, Results card, and E2E evidence exist.

### P0-7: Current code must be reconciled with the target design

Claude 4.8 live review found that the documents described the target system well, but did not sufficiently require a current-vs-target demolition/migration table. The gate and detailed design now require explicit disposition for existing hero, upload/file panels, direct URL behavior, waveform data path, review-session routes, local undo/redo, publish button, duplicate statusbar/minimap, naming drift, and sleep P2 sections.

## Development Start Decision

P0 implementation may start only for the epilepsy inherited-context slice if the first development packet includes:

1. `embed=1` same-frame route/context contract from main app;
2. child ContextHeader;
3. primary upload/lab-data controls hidden in inherited mode;
4. direct URL blocked state;
5. first control-state matrix;
6. E2E proving inherited child context and no primary upload path.

Implementation must not start on sleep release claims or Results publish claims until their contracts are implemented and tested.

## Required Next Artifacts

```text
work/release_evidence/20260628-epilepsy-sleep-staging-child-pages/control_state_matrix.json
scripts/e2e_epilepsy_staging_embed_context.mjs
scripts/e2e_epilepsy_staging_direct_url_blocked.mjs
scripts/audit_staging_duplicate_controls.mjs
scripts/audit_staging_forbidden_namespace_and_copy.mjs
```

## Receipt

```text
route_decision: gpt55_planner_or_acceptance + subagent positive review + subagent adversarial review + script_validator + Claude 4.8 prior review
execution_packet: design docs pre-development adversarial hardening
executor_evidence: subagent outputs, Claude prior review, local document readback, validator pass
gpt55_acceptance: gate now blocks the known failure classes before development
final_receipt: completed_predev_adversarial_gate_ready_for_first_epilepsy_embed_slice_after_current_target_reconciliation
next_real_artifact: epilepsy embed child-page implementation packet with control-state matrix, current-vs-target disposition, and E2E
```
