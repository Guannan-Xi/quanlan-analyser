# QLanalyser Epilepsy/Sleep Waveform Staging Child Pages - Test and Acceptance Plan

Date: 2026-06-28  
Status: P0 design package for implementation  
Scope: Epilepsy-like event waveform staging and sleep staging as QLanalyser main-system child pages  
Sources: owner correction, Claude 4.8 opus review, Codex design review, local QLanalyser design system  
Forbidden scope: router, Headroom, gateway, IPC, model route, TimeChart, PSD/BandPower mixing, medical diagnosis wording

Mandatory E2E gate:

- `docs/product/epilepsy_sleep_staging_predev_adversarial_gate_20260628.md`

The E2E plan must prove the gate, not only prove that pages open.


## 1. Gate Strategy

Acceptance requires browser click-path evidence, not only API tests. Each critical state must have screenshot or JSON evidence.

## 2. P0 E2E Matrix

| ID | Scenario | Expected |
| --- | --- | --- |
| ES-P0-01 | Data Preparation confirm then run epilepsy task | task payload contains `data_preparation_plan_id`, `data_preparation_revision`, `data_preparation_contract_version` |
| ES-P0-02 | Open epilepsy staging subview | route contains `embed=1`, task id, plan, rev, contract, and the main navigation frame is visible |
| ES-P0-03 | Context header | shows project/file/task/workflow/plan/revision/contract |
| ES-P0-04 | No primary upload path | upload/select independent EEG controls hidden or demoted in embed mode |
| ES-P0-05 | Waveform workbench visible | canvas/waveform area visible; not static-only image |
| ES-P0-06 | Running task state | long-task state shown without asking user to upload |
| ES-P0-07 | Missing plan guard | staging subview blocks correction and guides the user to Data Preparation inside the same app frame |
| ES-P0-08 | Results contract | Results page has epilepsy result/status card or placeholder with correct non-medical wording |
| ES-P0-09 | No forbidden route touch | git diff excludes router/Headroom/gateway/IPC/model route |
| ES-P0-10 | Copy scan | no diagnosis/treatment/triage/clinical decision wording in positive claims |

## 3. P1 E2E Matrix

| ID | Scenario | Expected |
| --- | --- | --- |
| ES-P1-01 | Select epoch and set Seizure-like | epoch strip updates, action log appends |
| ES-P1-02 | Set Normal | selected epoch returns to Normal |
| ES-P1-03 | Undo/Redo | previous/next stage restored |
| ES-P1-04 | Reset | overrides cleared with confirmation/action log |
| ES-P1-05 | Save | server session revision increments |
| ES-P1-06 | Publish results | corrected artifacts appear in Results |
| ES-P1-07 | Reopen session | saved correction state restored |
| ES-P1-08 | Stale plan revision | stale warning and recovery action shown |

## 4. P2 Sleep E2E Matrix

| ID | Scenario | Expected |
| --- | --- | --- |
| SL-P2-01 | Open sleep child page | inherited context shown |
| SL-P2-02 | Stage epoch Wake/N1/N2/N3/REM | hypnogram and epoch table update |
| SL-P2-03 | Batch correction | range changes and action log records |
| SL-P2-04 | Save/publish | sleep Results card shows hypnogram and stage summary |

## 5. Visual/UX State Screenshots

Required screenshots:

- default inherited staging subview inside main navigation frame;
- task running;
- no source predictions;
- waveform loading;
- correction dirty state;
- save failed;
- save success;
- published Results card;
- disabled controls with reason;
- keyboard focus state;
- 1440, 1280, 390 viewports.

## 6. Static Validators

- active scripts must not import hard-coded `../frontend/node_modules/playwright`;
- `target="_blank"` or separate full-page navigation is not used as the main product path for epilepsy/sleep staging subviews;
- no primary upload controls visible in `embed=1`;
- epilepsy/sleep namespace scan blocks `band_power`, `psd_band_power`, `channel_band_power`;
- forbidden medical wording scan with context-aware negation allowance;
- data-preparation payload field assertions.

## 7. Commands

P0 expected commands:

```powershell
node --check frontend/app.js
node --check frontend/epilepsy-workbench.js
node --check scripts/e2e_main_epilepsy_entry_real_path.mjs
python -m py_compile backend/api/data_crud.py backend/models/data_preparation.py backend/services/data_preparation_service.py
node scripts/e2e_main_epilepsy_entry_real_path.mjs
```

Add new validators as implementation proceeds.

## 8. Release Blockers

- child page asks user to upload EEG as primary path;
- child page lacks data preparation plan/revision/contract;
- correction overwrites source artifacts;
- Results module cannot find final outputs;
- waveform is static or blank;
- critical controls are clickable but do nothing;
- positive medical overclaim;
- no E2E screenshot evidence for inherited context and no-primary-upload mode.

## 9. Pre-Development Adversarial UI Test Pass

Before development starts, run a document-level adversarial review against every planned surface:

```text
analysis task card
staging subview context header
waveform toolbar
timeline / progress control
epoch strip
correction panel
action history
save/publish panel
Results card
Report handoff
```

For each surface, answer:

1. What is the user's one primary task here?
2. Which element is the main scientific object?
3. Which button is primary, and why only this one?
4. Is any state repeated elsewhere?
5. Is any button decorative, disabled without reason, or duplicate?
6. Can the user recover from empty/loading/error/stale state?
7. Can keyboard users reach and use the control?
8. Does this surface preserve the data-preparation inheritance chain?
9. Does the output flow to Results?
10. Could a customer misread this as diagnostic or clinical?

Any unanswered item is a P0 documentation gap before coding.

## 10. Duplicate-Control Regression Tests

Add or extend E2E/static validators to assert:

- `embed=1` page has no primary upload button visible;
- only one primary CTA is visible inside each decision area;
- timeline overview is draggable and no second equivalent progress slider competes with it;
- status text does not momentarily appear/disappear below waveform during scroll/pan;
- Browse mode left click does not write corrections;
- Correction mode writes exactly one draft action per intentional command;
- disabled controls expose a `title`, inline reason, or accessible description;
- Results page and child page do not show conflicting task status.

## 11. Evidence Package Naming

For this feature, evidence must be written under:

```text
work/release_evidence/20260628-epilepsy-sleep-staging-child-pages/
```

Minimum evidence files:

```text
e2e_main_epilepsy_child_context.json
e2e_epilepsy_no_primary_upload.png
e2e_epilepsy_waveform_interaction.png
e2e_epilepsy_control_state_matrix.json
e2e_epilepsy_results_contract.png
static_no_forbidden_medical_claims.json
static_no_psd_bandpower_namespace_bleed.json
static_no_duplicate_primary_controls.json
```

Sleep evidence is required only when sleep enters the release claim.

## 12. Additional Claude 4.8 Adversarial Gate

Claude 4.8 adversarial review marked P0 implementation as NO-GO until the following are testable. These are mandatory before any development slice is accepted.

| Gate | Required proof |
| --- | --- |
| explicit state machine | generated/checked control-state matrix for all critical controls |
| Browse vs Correction boundary | E2E proves Browse does not write and Correction writes exactly one action |
| no duplicate status/buttons | static audit finds no duplicate primary CTA/status for same fact |
| direct URL blocked | opening workbench without `embed=1` does not show customer primary upload workflow and remains inside the main navigation frame |
| demonstrable waveform interaction | pan/zoom/select change measurable state and screenshot |
| Results forward pointer | P0 placeholder states exactly where final corrected result will appear and how to continue |
| no-source state | completed task without source artifacts has recovery UI, not upload fallback |
| save-failure state | failed save keeps dirty draft and exposes retry |

## 13. New/Updated Test Scripts Required

```text
scripts/e2e_epilepsy_staging_embed_context.mjs
scripts/e2e_epilepsy_staging_control_state_matrix.mjs
scripts/e2e_epilepsy_staging_waveform_interaction.mjs
scripts/e2e_epilepsy_staging_direct_url_blocked.mjs
scripts/audit_staging_duplicate_controls.mjs
scripts/audit_staging_forbidden_namespace_and_copy.mjs
```

Existing `scripts/e2e_main_epilepsy_entry_real_path.mjs` must be upgraded from "link exists / page opens" to "inherited same-frame staging subview context, main navigation frame, and no-primary-upload path verified".

## 13. Gate Regression Suite

The following tests are mandatory before a P0 development slice can be called ready:

| ID | Scenario | Failure condition |
| --- | --- | --- |
| GATE-01 | Open epilepsy staging subview from main task | route lacks `embed=1`, ContextHeader lacks task/plan/revision/contract, or main navigation frame is absent |
| GATE-02 | Open child page directly as customer | independent upload/file-selection workflow is available |
| GATE-03 | Inspect controls with no selection | write controls are enabled or lack a visible disabled reason |
| GATE-04 | Browse-mode click/wheel/drag | any correction/action log is created |
| GATE-05 | Correction-mode selection and stage command | no auditable draft command is created, or Undo cannot reverse it |
| GATE-06 | Time navigation | timeline and progress bar both control the same window |
| GATE-07 | Status ownership | task status/plan revision/current time window appear in duplicate primary surfaces |
| GATE-08 | Waveform interaction | pan/zoom/selection changes labels only, not rendered waveform/selection state |
| GATE-09 | Results contract | UI claims corrected outputs are published without registered artifacts |
| GATE-10 | Sleep release gate | customer sees sleep as release-ready without real sleep implementation evidence |
| GATE-11 | Domain bleed | epilepsy/sleep staging contains PSD/BandPower namespace or positive medical wording |
| GATE-12 | Current-vs-target reconciliation | legacy hero/upload/statusbar/publish controls survive in inherited P0 mode without an explicit disposition |
| GATE-13 | Main navigation frame | staging opens as a standalone-looking page or depends on a return button instead of same-frame navigation |

Each failed gate blocks development acceptance. The correct receipt is `blocked_predev_gate_missing` or `partial_predev_gate_needs_followup`, not a release-ready receipt.
