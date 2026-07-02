# WaveformWorkbench Toolbar Governance Contract

Date: 2026-06-28  
Surface: `frontend/waveform-workbench.html`  
Source gate: `docs/product/qlanalyser_ui_interaction_visual_governance_master_20260628.md`

## DESIGN_CONTRACT_USED

```yaml
surface: independent_waveform_workbench_toolbar
target_user:
  - EEG researcher
  - CRO data preparation operator
  - teaching-mode customer
primary_task: continuously inspect EEG, adjust display, mark/review segments, and prepare a reversible data-preparation draft
risk_level: medium_high_scientific_workflow
source_documents:
  - DESIGN.md
  - docs/product/qlanalyser_ui_interaction_visual_governance_master_20260628.md
  - docs/product/qlanalyser_project_design_system_20260628.md
adopted_rules:
  - one user intention, one primary control
  - browse and write modes must not be ambiguous
  - time window and epoch length must be separate concepts
  - status bars do not duplicate controls
  - main scientific object remains dominant
  - secondary/advanced controls are contextual
skipped_rules_with_reason:
  - full human-factors summative evidence: not a release-validation slice
  - backend chunk API redesign: already handled by prior performance packet, not part of toolbar IA
expected_screenshots:
  - default desktop toolbar
  - epoch-review mode toolbar
  - write-mode draft state
  - mobile/narrow viewport
expected_e2e:
  - waveform still auto-loads
  - browse drag does not write draft
  - select/epoch/bad segment/bad channel modes still work
  - epoch controls hidden in browse mode and visible in epoch review mode
  - no horizontal overflow
decision_before_build: pass_to_build
```

## INTERACTION_INTERFERENCE_MATRIX

```yaml
surface: independent_waveform_workbench_toolbar
controls:
  - control: first/previous/next/last buttons
    intention: move through continuous EEG
    layer: browse
    can_write_data: false
    visible_by_default: true
    duplicates_control: overview shows position only, not duplicate primary browsing action
    conflicts_with: none if write modes keep separate visual state
    recovery: no data mutation
  - control: time window selector
    intention: choose visible continuous EEG duration
    layer: display
    can_write_data: false
    visible_by_default: true
    duplicates_control: overview caption may display current window but cannot be primary control
    conflicts_with: epoch length if placed as peer control
    recovery: user can choose another window
  - control: event marker visibility
    intention: reduce event overlay noise
    layer: display
    can_write_data: false
    visible_by_default: true
    duplicates_control: event legend only explains visual meaning
    conflicts_with: visual continuity if dense labels are too prominent
    recovery: hidden/light/full modes
  - control: sensitivity and channel count
    intention: adjust display readability
    layer: display
    can_write_data: false
    visible_by_default: true
    duplicates_control: status bar must not repeat values
    conflicts_with: none
    recovery: preset and keyboard +/- path
  - control: browse/select/epoch/bad segment/bad channel mode buttons
    intention: choose whether interaction is read-only or writes draft
    layer: write_draft
    can_write_data: true except browse
    visible_by_default: true
    duplicates_control: shortcut help only explains, not primary entry
    conflicts_with: browse if mode state not visually obvious
    recovery: Esc/B returns to browse; draft undo/redo
  - control: epoch length and visible epoch count
    intention: configure epoch review unit
    layer: write_draft
    can_write_data: false by itself; affects epoch review selection
    visible_by_default: false
    duplicates_control: none
    conflicts_with: time window if shown as peer display control
    recovery: appears only in epoch review context
findings:
  - severity: P0
    issue: epoch length was visually peer to display time window
    fix: hide/demote epoch settings until epoch review mode and place under review layer
  - severity: P1
    issue: browse, display, and write controls were visually flattened
    fix: split toolbar into task bands with clear headings and safety copy
decision: pass_to_build
```

