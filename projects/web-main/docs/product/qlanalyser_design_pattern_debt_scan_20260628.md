# QLanalyser Design Pattern and Design Debt Scan

Date: 2026-06-28  
Scan type: read-only source and evidence scan  
Result: no new confirmed product-code P0; release acceptance still blocked by test/data evidence gaps

## 1. What Already Fits the Design Direction

| Area | Evidence | Pattern already present |
| --- | --- | --- |
| Module contracts | `backend/services/module_contract_service.py` enriches workflow templates from module contracts | Registry / contract facade |
| Waveform browsing | `backend/services/waveform_chunk_service.py` provides chunk API without task/artifact side effects | Facade / proxy / performance boundary |
| Reproducibility | `eeg_core/report/reproducibility.py` writes parameters, sidecars, manifests, scope contracts | Template Method foundation |
| Data preparation revisions | `backend/services/data_preparation_service.py` and data-preparation plan acceptance scripts | Memento / revision model |
| Frontend control matrix | `scripts/e2e_data_prep_interaction_controls_state_matrix.mjs` | State-machine testing |
| Design contract habit | `DESIGN.md` and product design docs | Persistent design contract |

## 2. P0 Release Evidence Gaps

These are not necessarily product-code defects, but they block owner-level release confidence.

### P0-1. UI-only EDF to report/export evidence is currently failed

Evidence:

- `work/release_evidence/edf_upload_to_results_ui_only/edf_upload_to_results_ui_only.json`
- Reported failure cause: Playwright Chromium executable missing.

Impact:

- The current evidence cannot prove EDF upload, manual review, analysis entry, report ZIP/PDF/OCR/export flow.

Recommended fix:

- Add environment preflight to browser E2E scripts.
- If browser runtime is missing, report `environment_blocked` separately from product failure.
- Standardize Playwright loader and browser availability checks.

Pattern:

- Facade for browser runtime setup.
- Chain of Responsibility for E2E preflight before product assertions.

### P0-2. Real owner-data regression remains blocked

Evidence:

- `work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json` missing.
- Existing owner regression scripts block as expected.

Impact:

- Synthetic/demo evidence is useful for internal development but not enough for owner release.

Recommended fix:

- Obtain authorized anonymous EEG manifest.
- Run real dataset regression covering data preparation, selected allowed methods, report package, boundary text, and PHI/path leakage checks.

Pattern:

- Acceptance gate / release facade.

## 3. P1 Design Debts

### P1-1. Frontend state derivation has duplicate definitions

Evidence:

- Duplicate state-label and render functions in `frontend/app.js`, including `selectedStateLabel` and `renderProjectDataManagement`.

Impact:

- Later definitions override earlier definitions.
- Fixes can be applied to dead code.
- State labels may drift between project, file, plan, and dashboard.

Recommended refactor:

- Introduce `workspaceStateFacade` for derived project/file/plan/epoch/task state.
- Render functions consume the facade output.

Patterns:

- State
- Facade
- Observer

Tests:

- Static duplicate function-name check.
- Project/file/plan state matrix E2E.

### P1-2. View/auth/role/demo/teaching are multi-source

Evidence:

- HTML initial `.view active`, DOM hidden attributes, `setView()`, URL hash, localStorage/sessionStorage, and teaching/customer URL params all influence visible state.

Impact:

- Hidden old DOM may be active to selectors.
- Refresh/hash/customer demo/teaching demo combinations can drift.

Recommended refactor:

- Define an app state reducer:
  - `auth`
  - `role`
  - `view`
  - `teaching`
  - `workspace`
- URL and storage become adapters.

Patterns:

- State
- Observer
- Router Adapter

Tests:

- Hash restore matrix.
- Teaching/customer demo URL matrix.
- Hidden controls not focusable/clickable.

### P1-3. Waveform workbench mode state is dispersed

Evidence:

- `frontend/waveform-workbench.js` reads URL parameters, mutates `state.mode`, mutates config, writes history, and CSS hides controls by `data-mode`.

Impact:

- Basic preview and epoch review may diverge.
- Hidden epoch controls can linger in basic mode.

Recommended refactor:

- Create explicit `WaveformWorkbenchStateMachine`.
- URL is only initialization/persistence adapter.
- Mode transition table is tested.

Patterns:

- State Machine
- Command
- URL Adapter

Tests:

- `workbench=basic|epoch|epilepsy|sleep` matrix.
- Browse/write/epoch review transition matrix.
- No payload write-mode blocked.

### P1-4. Global event delegation lacks command boundary

Evidence:

- `frontend/app.js` has a large document-level click chain.
- Multiple buttons share `data-real-action`.
- Some file triggers use inline DOM behavior.

Impact:

- Hidden or repeated buttons may trigger commands.
- New controls can miss disabled/audit behavior.

Recommended refactor:

- Introduce `commandRegistry`.
- Each command has `canRun`, `reason`, `run`, `sideEffect`, `audit`.
- Button handlers only call the registry.

Patterns:

- Command
- Mediator

Tests:

- Each command fires once.
- Hidden view command cannot mutate state.
- Disabled command produces blocked audit and no network write.

### P1-5. `/api/tasks` does not validate `(module_name, workflow_id)`

Evidence:

- `AnalysisTaskCreate` accepts free strings.
- `task_service.create_task()` dispatches mainly by `module_name`.
- `workflow_id` only affects selected branches.

Impact:

- Mixed module/workflow tasks can be submitted.
- Billing, report, artifacts, and reproducibility can disagree.

Recommended refactor:

- Add `AnalysisWorkflowRegistry`.
- Validate runner, schema, artifact policy, lifecycle, and scope before task creation.

Patterns:

- Strategy
- Facade
- Chain of Responsibility

Tests:

- Illegal combinations return 422.
- Legal combinations keep task/result/manifest workflow consistent.

### P1-6. Workflow id drift in PAC and TFR

Evidence:

- PAC frontend/template uses `pac_cfc`, while algorithm writes `pac_cfc_beta`.
- TFR template says enabled but has empty outputs; estimate infers enablement from outputs.

Impact:

- Reports and acceptance scripts can disagree with runtime outputs.

Recommended refactor:

- Canonical workflow id plus explicit alias/display id.
- Estimate should use registry lifecycle/runner metadata, not `outputs` truthiness.

Tests:

- PAC workflow consistency test.
- TFR estimate returns runnable and lists outputs.

### P1-7. Epilepsy ML artifact labels duplicate paths

Evidence:

- `eeg_core/analysis/epilepsy_ml.py` maps the same files to generic epilepsy and epilepsy_ml labels.
- `task_service` registers every label.

Impact:

- Report/download lists can duplicate outputs.
- ML output can be confused with STD threshold output.

Recommended refactor:

- Canonical `epilepsy_ml_*` labels in runner output.
- Display compatibility only in report/UI adapter.

Tests:

- One physical path maps to one canonical artifact label.

## 4. P2 Design Debts

| Debt | Impact | Recommendation |
| --- | --- | --- |
| Post-render copy cleanup in `app.js` | UI copy lives in several layers | Move to ViewModel render source |
| `module-lab` tabs are DOM-only state | Refresh/deep link cannot restore method group state | Add active method state |
| Epilepsy workbench full rerender + bind events | Focus/selection/review state can be lost | Add local command/repository boundary |
| Module contract path is machine-specific | Deployments may silently lose contracts | Configurable path + readiness failure |
| Artifact download policy is mostly declarative | Future multi-tenant auth gap | Add project/user access policy checks |
| Playwright paths and URLs not fully portable | E2E failures can look like product failures | Shared Playwright env facade |

## 5. Pattern-to-Code Map

| Pattern | QLanalyser target |
| --- | --- |
| State | app/view/teaching/waveform/review/export modes |
| Command | UI actions and review edits |
| Facade | task creation, waveform chunk, report export, owner release gate |
| Strategy | analysis runner selection |
| Adapter | source algorithms, legacy fields, external contract files |
| Observer | UI panel refresh after state changes |
| Memento | data-preparation revisions and review undo/redo |
| Chain of Responsibility | task validation, quota, execution, artifact registration |

