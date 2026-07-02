# QLanalyser Epilepsy/Sleep Staging Pre-Development Adversarial Gate

Date: 2026-06-28
Status: mandatory gate before P0 implementation
Scope: epilepsy-like event staging, future sleep staging, inherited waveform child pages, data-preparation handoff
Evidence sources: owner corrections on 2026-06-28, Codex review, Claude 4.8 adversarial review, QLanalyser project design system

This document is the gate that prevents the recurring failure pattern seen during the WaveformWorkbench and Data Preparation iterations: duplicate information, controls that appear usable but do nothing, unclear task flow, standalone-tool behavior, and waveform areas that look static.

Implementation may start only when every P0 gate below is either satisfied by the design documents or explicitly marked out of scope for the current release slice.

## 1. Development Entry Verdict

| Area | Verdict before this gate | Required before code |
| --- | --- | --- |
| Architecture direction | Go | Keep inherited child-page model |
| Epilepsy P0 child page | Conditional go | Pass G1-G8 |
| Sleep page | No external release claim | Keep as P2/internal unless real task, stage schema, UI, Results card, and E2E exist |
| Results publish | P1 unless implemented | P0 may show honest contract only; no false "published" claim |

## 2. P0 Gate List

### G1 - Explicit State Machine

The design must define legal states, legal transitions, and control behavior.

Required states:

```text
NoContext
ContextLoaded
ContextInvalid
TaskRunning
TaskFailed
SourceMissing
SourceReady
Browse
Inspect
SelectRange
CorrectionDraft
SaveInFlight
Saved
SaveFailed
PublishInFlight
Published
PublishFailed
ResultsVisible
ContextStale
```

No visible control may exist without:

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

### G2 - Browse vs Correction Boundary

Default mode is `Browse`. Browse is read-only.

Rules:

- left click in Browse selects or inspects only; it never writes a correction;
- wheel and drag pan the waveform or timeline only;
- correction commands require explicit `Correction` mode or explicit stage action;
- the active mode must be visible in one concise place;
- keyboard shortcuts must obey the same state machine as buttons.

### G3 - Single Source of Truth for Visible Facts

Each visible fact must have one owner and one primary display location.

| Fact | Authoritative owner | Primary display | Must not be repeated as |
| --- | --- | --- | --- |
| project/file | parent main app context | child ContextHeader | upload/file card |
| preparation plan/revision | parent confirmed preparation state | child ContextHeader | side-panel status card |
| task status | analysis task state | task callout or ContextHeader | multiple chips/cards |
| waveform time window | waveform controller | draggable overview strip | duplicate progress bar plus status text |
| active mode | interaction state machine | toolbar mode chip | repeated canvas overlay |
| dirty/saved state | staging session | save panel | floating debug line |
| selected epoch/range | selection controller | correction panel | repeated summary card |
| candidate/stage counts | domain result summary | domain panel/results card | extra top-level KPI card |

If a secondary copy is unavoidable for responsive layout or accessibility, it must be lower visual weight and must not create another control for the same action.

### G4 - No Primary Upload Path and No Standalone Page Chrome in Inherited Child Pages

When `embed=1` is present, epilepsy and sleep child pages inherit context from the main system and remain inside the main QLanalyser navigation frame. They are Analysis subviews, not separate applications.

Forbidden in inherited mode:

- primary upload button;
- primary select-lab-data button;
- independent file picker as the first workflow step;
- hero section that asks the user to start a new analysis;
- fixture bootstrap that silently replaces the inherited task.
- a page-level return workflow that implies the user left the main system;
- separate app chrome, separate navigation identity, or standalone landing layout.

Required in inherited mode:

- global navigation/header/sidebar remains visible or is provided by the parent shell;
- the active navigation item remains under Analysis / Results workflow;
- movement to Results is a same-frame navigation state, tab, route, or view switch;
- breadcrumbs may show location, but they must not replace the main navigation frame.

Direct URL without `embed=1` must show a controlled state:

```text
customer/default: blocked inherited-context state inside the main navigation frame, with guidance to open from Analysis
lab/dev explicit parameter: fixture/upload path allowed as developer route
```

### G5 - Demonstrable Waveform Interaction

A waveform workbench cannot pass with a static canvas or static image.

Required proof:

- pan changes visible time window and keeps waveform visible;
- zoom changes duration around a known anchor or visible focus;
- click/drag selects epoch/range in the correct mode;
- stale/loading state cannot masquerade as confirmed current waveform;
- no old payload is remapped onto a new time axis as if it were current data.

### G6 - Results Backflow Honesty

P0 may show the intended Results contract without implementing publish.

Rules:

- if publish is not implemented, the UI must say "save draft / contract ready" rather than "published";
- the child page must expose Results as a same-frame navigation destination or panel in the main navigation framework;
- Results must not claim corrected artifacts exist until they are registered artifacts;
- P1 publish must register normal artifacts consumable by Results and Report modules.

### G7 - Sleep Release Claim Gate

Sleep staging must remain P2/internal until all are true:

- sleep task exists;
- stage schema exists;
- waveform plus hypnogram/epoch UI exists;
- correction commands exist;
- saved session exists;
- Results card exists;
- E2E proves inherited context and output flow.

### G8 - No Domain Bleed

Epilepsy/sleep staging must not import PSD/BandPower semantics.

Forbidden in staging namespaces and customer copy:

```text
band_power
psd_band_power
channel_band_power
diagnosis
confirmed seizure
treatment
triage
medical advice
```

Negated non-medical boundary text is allowed, for example research-support wording that explicitly says the tool is not diagnostic.

## 3. Required Control-State Matrix

Every implementation slice must include or update a machine-readable control-state matrix with this shape:

```json
{
  "control_id": "epilepsy-stage-seizure",
  "surface": "epilepsy_staging",
  "label": "Set as Seizure Candidate",
  "primary_or_secondary": "secondary",
  "visible_when": "SourceReady && domain == epilepsy",
  "enabled_when": "CorrectionDraftAllowed && selected_epoch_count > 0",
  "disabled_reason": "Select one or more epochs before correcting the stage.",
  "click_result": "append correction command",
  "success_state": "CorrectionDraft",
  "failure_state": "SaveFailed or unchanged Browse",
  "undo_or_recovery": "Undo removes the last command",
  "authoritative_state_owner": "CorrectionCommandController",
  "duplicates": "none",
  "e2e_assertion": "[data-testid='epilepsy-stage-seizure'] disabled without selection, enabled with selection"
}
```

Implementation cannot introduce a visible button, toggle, input, slider, timeline, or shortcut without a row in this matrix.

## 4. Required Page-Surface Review

Before code, each surface must answer these questions:

| Surface | Required review |
| --- | --- |
| main analysis task card | Does it send inherited context? Does it avoid "review-only" wording? |
| child ContextHeader | Does it show project/file/task/plan/revision/contract once? |
| waveform toolbar | Is there exactly one primary browse mode and one correction entry? |
| overview/timeline | Is it the only time navigation control? Is it draggable? |
| epoch strip | Hidden in basic preview; visible only in epilepsy/sleep staging |
| correction panel | Disabled until valid selection; every write is undoable |
| action history | Shows audit trail only; does not duplicate status |
| save/publish panel | Honest about draft/saved/published state |
| Results card | Points to corrected outputs only after publish |
| Report handoff | Consumes registered artifacts only |

## 5. Required E2E Failure Cases

The suite must fail if any of these happen:

- inherited child page shows primary upload/select-lab-data controls;
- direct customer URL opens an independent upload tool;
- Browse mode writes any correction action;
- a visible enabled control has no state change, navigation, save, export, or clear disabled reason;
- timeline and progress bar duplicate the same navigation function;
- task status or plan revision appears in two competing primary locations;
- waveform remains blank/static after data load;
- pan/zoom changes labels but not rendered waveform content;
- stale waveform is shown as current ready state;
- publish button claims success without registered Results artifacts;
- sleep appears release-ready without real sleep evidence;
- epilepsy/sleep copy contains positive diagnostic or treatment wording.

## 6. Required Evidence Package

Implementation evidence must be written under:

```text
work/release_evidence/20260628-epilepsy-sleep-staging-child-pages/
```

Minimum files:

```text
control_state_matrix.json
predev_gate_validation.json
e2e_main_epilepsy_child_context.json
e2e_epilepsy_direct_url_blocked.json
e2e_epilepsy_waveform_interaction.json
e2e_epilepsy_no_duplicate_controls.json
e2e_epilepsy_results_contract.json
static_forbidden_namespace_and_copy.json
desktop_1440_child_page.png
laptop_1280_child_page.png
mobile_390_child_page.png
```

## 7. Development Start Decision

P0 development may start only after:

1. this gate is referenced by requirements, detailed design, and E2E plan;
2. control-state matrix rows exist for P0 visible controls;
3. non-embed direct route behavior is designed;
4. waveform interaction proof is listed as an E2E, not only a visual screenshot;
5. Results publish is either implemented or honestly marked as future contract;
6. sleep release claim is blocked unless real sleep implementation exists.

If any of the above is missing, the correct receipt is:

```text
blocked_predev_gate_missing
```

not:

```text
ready_for_development
```

## 8. Current vs Target Reconciliation Gate

Claude 4.8 live review added one extra blocker: the target design is strong, but it must reconcile with the code that already exists. Otherwise a developer can add the new child-page shell while leaving old independent-tool controls in place.

Before implementation, each P0 surface must have a disposition:

```text
keep
delete
hide_in_embed
rename
migrate
build_new
block_until_P1
```

Required reconciliation table:

| Current surface or route | Current behavior | Target behavior | P0 disposition |
| --- | --- | --- | --- |
| `epilepsyWorkbenchUrl(task)` | opens separate page with task/mode/renderer/api/v only | inherited Analysis subview in the main navigation frame with embed/domain/task/plan/rev/contract/results context | migrate |
| workbench hero | shows run screening, lab data, refresh | no hero after inherited task context exists | hide_in_embed |
| file select and upload form | primary independent data entry | forbidden as primary path in inherited child page | hide_in_embed |
| direct customer URL | can reach standalone workbench | blocked inherited-context state inside the main navigation frame, or guidance to open from Analysis | build_new |
| waveform source | may use existing preview/task payloads | must prove windowed pan/zoom/select with current data | verify_before_claim |
| `epilepsy-review-sessions` routes | PATCH/export review model | P0 may keep internal; P1 publish needs explicit migration | keep_P0_migrate_P1 |
| local undo/redo/history | browser-local draft | allowed for P0 draft only, not Results publish | keep_P0 |
| Publish to Results button | not backed by registered corrected artifacts | absent or disabled with reason until P1 backend exists | block_until_P1 |
| `waveform-statusbar` plus minimap/time labels | duplicate mode/time risk | one primary time navigation and one concise mode label | delete_or_demote_duplicates |
| page/workbench names | review/workbench/staging labels drift | one customer-visible surface name | rename_consistently |
| sleep sections | present-tense target design | P2/internal until real sleep implementation exists | mark_P2_only |

P0 is not ready if a current surface is known to conflict with the target and has no disposition.
