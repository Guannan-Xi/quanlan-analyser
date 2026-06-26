# QLanalyser Mainline Productization Requirements

Date: 2026-06-26
Owner: 07-PM / QLanalyser mainline acceptance
Repo: D:\Quanlan\Codes\Python\quanlan-analyser-official
Status: implementation contract before code changes

This document is the requirements source for the next productization slice. Do not pass missing requirements through chat. Implementation, review, and testing must read this file, the matching design file, and the matching E2E test plan before changing product behavior.

## 1. Background

The 02 -> 07 Module Lab grouped-methods integration has been accepted at function level. The accepted method set is:

| User-facing entry | Stable backend contract | Product status |
|---|---|---|
| Data preparation and quality check | `metadata_qc` / `metadata_qc` | Available as a preparation dependency |
| PSD / Bandpower | `resting_psd` / `resting_psd` | Available |
| ERP / P300 | `erp_p300` / `erp_p300` | Available, requires events |
| TFR / ERSP / ITC | `tfr_ersp_itc` / `tfr_ersp_itc` | Preview, requires review |
| Multitaper PSD | `multitaper_psd_tfr` / `multitaper_psd_tfr` with `analysis_family=psd` | Preview, requires review |
| Multitaper TFR | `multitaper_psd_tfr` / `multitaper_psd_tfr` with `analysis_family=tfr` | Preview, requires review |
| Reference / CSD | `reference_csd` / `reference_csd` | Preview, requires review |
| PAC / CFC | `pac_cfc` / `pac_cfc` | Preview, no causal claim |
| Connectivity | `connectivity` / `connectivity` | Preview, no causal or information-flow claim |

Current gap: Module Lab exposes and tests all 9 entries, but the main workbench "Current available modules" surface only carries part of them. The product must now merge the accepted methods into the mainline user journey without making beta/review methods look like stable public claims.

## 2. Product Positioning

QLanalyser is a non-medical EEG research analysis and CRO-support platform. It may provide reproducible signal-analysis results, quality records, charts, tables, parameters, and report packages. It must not imply diagnosis, treatment, clinical decision support, seizure prediction, causality, exact source localization, universal validity, or production release approval from a single demo or synthetic file.

## 3. Global Requirements

### R0. Documentation-first execution

- Implementation must not start before this requirements document, the detailed design document, and the E2E test plan exist and pass UTF-8/mojibake checks.
- Every implementation slice must cite the requirement IDs it changes.
- If code behavior conflicts with this document, update the document first through a reviewed requirement change, then implement.

### R1. User-language-first copy

All customer-visible pages must describe user tasks, not developer internals.

Allowed main-surface wording examples:

- "Select EEG data"
- "Preview waveform"
- "Mark bad channel"
- "Restore segment"
- "Current available modules"
- "Preview method, needs review"
- "Download report package"

Do not use these on customer main surfaces:

- `runner`, `workflow id`, `module id`, `/api/tasks`, `manifest`, `acceptance`, `gate`, `debug`, `fake`, `mock`, `demo-only`, "开发验收", "内部测试", "实验台" as the primary label.

Exceptions:

- Technical identifiers may appear in a collapsed "Reproducibility details" area, downloadable processing record, admin-only diagnostics, or developer documentation.
- The internal Module Lab route may keep internal evidence, but its customer-facing title must become "Analysis Method Center" or "Available Analysis Methods" rather than "method module lab" when linked from the main workbench.

### R2. Current available modules must include all 9 accepted entries

The main workbench "Current available modules" section must list all accepted 02 -> 07 entries in user language:

- Data preparation and quality check
- PSD / Bandpower
- ERP / P300
- TFR / ERSP / ITC
- Multitaper PSD
- Multitaper TFR
- Reference / CSD
- PAC / CFC
- Connectivity

The section must group them by user meaning:

| Group | Entries | Required visible status |
|---|---|---|
| Data preparation | QC | "Preparation step" |
| Available analysis | PSD, ERP | "Available" |
| Preview methods, needs review | TFR, Multitaper PSD, Multitaper TFR, Reference / CSD, PAC, Connectivity | "Preview, needs review" |

The user must not need to open Module Lab to discover that these methods exist. Module Lab remains the bounded review/test surface for advanced parameter evidence and grouped-method E2E.

### R3. Main customer path closure

The product must support this path as a coherent first-class workflow:

```text
Upload EDF
-> prepare/preview data
-> QC and reversible edits
-> choose analysis method
-> run analysis
-> preview results
-> download report package
```

Acceptance:

- The path can be completed from the main workbench without visiting developer/test pages.
- Each step has one primary next action.
- Result preview and report delivery are different surfaces.
- Failed or incomplete steps explain recovery in user language.

### R4. Data click must trigger preview

Selecting or clicking a data row must request and display preview. A separate "Run QC preview" primary button is not allowed.

Allowed:

- A secondary "Reload preview" action after automatic preview exists.
- A clear loading, success, and error state.

Acceptance:

- E2E must select a data row and verify preview without clicking `run-qc-preview-inline`.
- Existing tests that still click `run-qc-preview-inline` must be updated or replaced.

### R5. Data preparation tools must stay on the waveform page

Bad channel, segment exclusion, event label editing, and current edit record must be visible in the same page as waveform preview at standard desktop viewport.

Acceptance:

- At 1440x900, no scroll is required to find the primary waveform, bad-channel entry, segment entry, event-label entry, and edit summary.
- On narrow viewport, these tools may stack, but remain reachable in a logical order and without horizontal overflow.

### R6. Bad channel, segment, and event edits must be reversible

The following user edits must be actionable, visible, reversible, and recorded:

| Edit | Required operation | Required restoration |
|---|---|---|
| Bad channel | Mark channel as bad | Restore channel |
| Bad segment | Exclude time range | Restore time range |
| Event label | Add or rename label | Restore previous label |

Each record must carry:

- object type
- object id or time range
- before value
- after value
- source: user
- timestamp
- reversible flag
- whether the edit entered the preparation plan

Original data must not be destructively changed by UI edits.

### R7. Beta/review surface governance

TFR, Multitaper PSD, Multitaper TFR, Reference / CSD, PAC, and Connectivity must be usable from the current module list only with review boundary text.

Required user-facing boundary:

- Results are for research reference.
- Results require review before delivery.
- PAC and Connectivity do not prove causality or information flow.
- Reference / CSD does not imply exact source localization.
- TFR and Multitaper TFR must show baseline/time-frequency parameter context.

Forbidden:

- Presenting preview methods as clinically validated.
- Hiding review status behind an internal `beta` label only.
- Using "stable" or "released" for these methods until a later release document upgrades them.

### R8. Product-wide UI and color governance

The product must remove the remaining left-side green/teal drift and replace it with a stable token system.

Required token groups:

- text, surface, border
- action primary/secondary
- active navigation
- selection
- focus ring
- success, warning, error, info, neutral
- preview/review/beta
- chart palettes

Acceptance:

- Navigation and sidebar active states are not green by default.
- Success green is reserved for success state only.
- Review/preview/beta colors are not confused with success.
- Raw hex values inside component-level CSS are reduced or documented as temporary migration exceptions.

### R9. State feedback coverage

Core surfaces must cover:

- empty
- loading
- error
- success
- disabled / permission denied
- partial result
- stale data
- long task
- reduced motion

Error messages must not expose local absolute paths, secrets, tokens, private storage paths, or raw internal logs.

### R10. Scientific figure and report boundary

Scientific charts must follow data-visualization and color semantics:

- no default rainbow/jet for continuous quantitative data
- visible title, axis labels, units, range, legend or colorbar
- baseline/normalization visible for TFR/heatmap/topomap-like charts
- non-color encoding where status/risk/significance appears
- export table or data package available
- report/package forbidden-claim scan before release

### R11. User-perspective copy on every page

All customer-visible pages must describe what the user can do and what the result means. The UI must not expose development, routing, runner, acceptance, or internal module vocabulary as primary copy.

Scope:

- main customer workbench
- data preparation page
- analysis task page
- current available modules
- result review and report delivery
- analysis method library
- static method preview pages
- admin pages, where wording must still be operator-readable rather than engineering-console copy

Acceptance:

- The 02 merged methods appear inside `当前可用模块`; users must not need to enter a beta/lab page to discover them.
- Status copy for preview methods is `预览方法，需复核`, not `beta`.
- The main analysis badge says `当前可用：9 项分析能力，预览方法需复核`.
- Visible page copy must not use `workflow`, `runner`, raw API route, `module id`, `方法分支`, `分析任务工作台`, `真实后端任务`, `参数回显`, `产物证据`, `API 服务`, `Research Module`, `Workflow contract`, `测试输入数据`, or `合成科研测试数据`.
- Internal backend fields may keep technical names when they are not rendered to users and are required for task execution.

### R12. Main workbench direct method entry coverage

The main workbench `当前可用模块` list and the `选择分析方法` action area must not drift apart.

Acceptance:

- `当前可用模块` shows 9 entries: QC plus 8 analysis methods.
- QC remains a preparation step and is not duplicated as an analysis-run button.
- The main workbench exposes direct user actions for the 8 analysis methods: PSD, ERP, TFR, Multitaper PSD, Multitaper TFR, Reference / CSD, PAC, and Connectivity.
- Preview methods use user wording such as `试用 ...（需复核）`; they must not be presented as stable final delivery.
- Backend IDs such as `multitaper_psd_tfr` may be used internally, but the user-facing action stays split into Multitaper PSD and Multitaper TFR.

## 4. Five-Task PDCA Requirements

### Task 1. Main Customer Path Closure

Plan:

- Make the main workbench the customer path from upload to report.
- Non-goal: do not promote Module Lab as the primary customer workbench.
- Acceptance: one browser E2E completes upload/selection, auto preview, preparation confirmation, analysis, result preview, and report download.

Do:

- Update data row selection and auto-preview semantics.
- Update analysis method section to point from prepared data to current available modules.
- Update result preview and report delivery copy to separate preview vs package.

Check:

- `acceptance_edf_upload_to_results_ui_only.mjs` or replacement must not click the old QC preview primary action.
- Evidence under `work/release_evidence/07-mainline-productization/customer_path/`.

Act:

- Any repeated confusion becomes either a copy fix, state fix, or layout fix in the next PDCA cycle.

### Task 2. Beta Area Becomes Controlled Preview Methods

Plan:

- Merge accepted methods into "Current available modules".
- Keep advanced methods visibly review-gated.
- Non-goal: no clinical or stable-public upgrade for preview methods.

Do:

- Replace the 4-card current module list with the 9-entry grouped list.
- Use status badges: "Preparation step", "Available", "Preview, needs review".
- Put module/workflow/runner identifiers in details only.

Check:

- DOM test verifies all 9 user labels.
- Copy scan verifies no customer main-card internal labels.
- Module Lab grouped-method E2E still passes.

Act:

- Promote a preview method to "Available" only through a later release-grade method validation packet.

### Task 3. Reversible Bad Channel / Segment / Event Edits

Plan:

- Give users direct edit and restore operations on the waveform page.
- Non-goal: destructive raw-file editing.

Do:

- Surface mark/restore bad channel.
- Surface exclude/restore segment.
- Surface add/rename/restore event label.
- Write before/after edit records into the preparation plan or draft plan.

Check:

- E2E marks and restores each edit type.
- Saved preparation plan no longer contains restored objects as active exclusions.
- Edit history retains before/after.

Act:

- If recoverability is confusing, revise visual states before adding more editing controls.

### Task 4. Product-wide UI and Color Governance Round 2

Plan:

- Treat navigation/sidebar/green residue/button overload/copy voice as a product-system problem.
- Target quality level: polished and professional for a scientific research workbench.

Do:

- Tokenize sidebar, navigation, buttons, cards, statuses, review badges, and chart palettes.
- Remove redundant primary buttons.
- Replace developer-language labels across pages with user-task labels.

Check:

- Color governance scripts pass.
- Sidebar screenshot no longer reads as green.
- Button-governance scan passes.
- Customer-copy forbidden internal terms scan passes.

Act:

- Raw-value exceptions are logged and retired in later slices.

### Task 5. Formal E2E Release Matrix

Plan:

- Replace stale or mixed evidence with a fresh current-code matrix.
- Non-goal: do not claim release readiness from historical screenshots or old checkpoints.

Do:

- Generate a synthetic EDF.
- Run main customer path.
- Run data-preparation edit/restore.
- Run Module Lab grouped 9-method E2E.
- Run report ZIP and scientific chart inventory.
- Run forbidden-claim scan.

Check:

- Evidence is written under one dated `formal_e2e_YYYYMMDD` directory.
- Every matrix row has command, status, output path, screenshot path if visual.

Act:

- Failed rows become blocking tickets with owner, first failing step, and next fix.

## 5. Priority

P0:

- Current available modules list all 9 accepted entries with user-language labels.
- Customer copy does not expose internal developer terms on main surfaces.
- Data row click triggers preview without a required preview button.
- Bad channel, segment, and event edits can be restored.
- Formal E2E must use fresh evidence.

P1:

- Sidebar and nav color governance.
- Button count and primary action hierarchy.
- State coverage screenshots.
- Scientific chart color and forbidden-claim validators.

P2:

- More refined method education, tooltips, and example interpretation cards.
- Expert-mode shortcuts after the customer path is stable.

## 6. Implementation Hooks

Likely affected files:

- `frontend/index.html`
- `frontend/app.js`
- `frontend/styles.css`
- `frontend/module-lab.html`
- `frontend/module-lab.js`
- `frontend/module-lab.css`
- `scripts/acceptance_workflow_pages_ui_gate.mjs`
- `scripts/acceptance_edf_upload_to_results_ui_only.mjs`
- new acceptance scripts under `scripts/`
- release evidence under `work/release_evidence/07-mainline-productization/`

Implementation must protect unrelated dirty worktree changes. Do not reset or remove unrelated edits.

## 7. Blocking Conditions

The work is blocked if:

- The main app cannot be started locally after two bounded attempts.
- Existing APIs do not expose enough task entry points to run a listed method and no safe UI-only fallback is acceptable.
- A test requires production credentials or external writes.
- Scientific/forbidden-claim scan finds P0 language that cannot be corrected without product owner decision.

Blocked state must produce a `blocked_final_receipt` with exact failing requirement IDs.
