# QLanalyser Project Design Standard

Date: 2026-06-28  
Status: draft standard, active for new work  
Scope: frontend workbenches, backend APIs, EEG algorithms, artifacts, reports, labs, review systems, and release evidence

## 1. Product Boundary

QLanalyser is a non-medical EEG research/support platform. It may provide candidate events, descriptive metrics, reproducibility records, and review support. It must not claim diagnosis, treatment, triage, clinical decision-making, or medical advice.

Allowed wording:

- research screening/support
- candidate event
- descriptive EEG metric
- manual review support
- reproducible analysis record

Forbidden positive claims:

- diagnosis or confirmed disease
- treatment recommendation
- clinical decision
- emergency triage
- medical advice

## 2. State Machine Standard

Every page or workbench must define its state before controls are implemented.

Minimum state dimensions:

- `auth`: logged_out, customer_demo, customer_user, admin
- `teaching`: off, loading, active, guide_active, failed
- `workspace`: no_project, project_selected, file_selected, plan_confirmed, task_running, task_done, report_ready
- `waveform`: empty, loading, ready, stale, browse, select_segment, mark_bad_segment, mark_bad_channel
- `review`: none, candidate, edited, undo_available, redo_available, saved
- `export`: unavailable, ready, running, done, failed

Required matrix for every visible control:

| Field | Meaning |
| --- | --- |
| selector | Stable selector or command id |
| enabled states | Exact state combinations where it works |
| disabled reason | User-readable reason |
| command | Command invoked when enabled |
| side effect | none, UI draft, backend revision, task, artifact, report |
| audit | record path or action log |
| test | E2E/API assertion |

Forbidden:

- Button appears enabled but click does nothing.
- A hidden legacy control can receive focus or trigger a command.
- URL parameter, local storage, backend session, and memory state disagree without a resolver.
- A write mode silently changes original EEG data.

## 3. UI and Interaction Standard

Use a project-level `DESIGN.md` or module-level design contract before UI work.

Customer UI rules:

- Show the primary scientific evidence first.
- Keep workflow decisions near the data they affect.
- Do not duplicate the same status beside a control and in a status bar.
- Keep debug/internal terms out of default customer mode.
- Put advanced settings in expandable sections when not needed for the next decision.
- Use icons for familiar operations and text only when the command needs clarity.
- Every disabled control needs a reason through title, inline hint, or status feedback.

Workbench rules:

- Basic waveform preview is for data preparation and initial bad segment/channel screening. It does not show epoch controls.
- Epoch review waveform is for epilepsy, sleep staging, and other epoch-based review. It may show epoch controls and stage/status strips.
- Browse mode never writes.
- Write/review modes write only UI draft or review layer until saved/confirmed.
- Heavy analysis tasks must not be the default waveform browsing path.

## 4. Frontend Architecture Standard

Preferred structure:

- State reducer/facade owns derived state.
- Commands own user actions.
- Views render from state and do not invent business rules.
- URL/localStorage/sessionStorage are adapters, not primary truth.
- Event delegation is allowed only when commands are centralized and hidden controls are guarded.

Required patterns:

- State for page/mode/control availability.
- Command for create project, choose data, add candidate, confirm preparation, create task, export report.
- Observer/Mediator for updating panels after state changes.
- Memento for undo/redo and review history.
- Adapter for legacy UI or source algorithm fields.

Forbidden:

- Multiple definitions of the same state-derivation function.
- Post-render copy cleanup as the primary UI copy mechanism.
- Inline `onclick` for workflow commands.
- Full-page rerender that loses focus/selection without a deliberate reset.

## 5. Backend API and Workflow Contract Standard

Every analysis workflow must be registered by a canonical tuple:

```json
{
  "module_name": "psd",
  "workflow_id": "resting_psd",
  "runner": "callable or service id",
  "parameter_schema": {},
  "output_schema": {},
  "artifact_labels": [],
  "summary_schema": {},
  "scope_contract": {},
  "non_medical_boundary": "",
  "enabled": true,
  "lifecycle_state": "production|beta|lab|draft"
}
```

`/api/tasks` must validate the tuple before execution. Illegal module/workflow combinations must fail before billing, artifact registration, or report generation.

Preferred patterns:

- Strategy for analysis runners.
- Facade for task lifecycle.
- Chain of Responsibility for validation, quota, execution, artifact registration, and audit.
- Adapter for legacy/source algorithms.
- Template Method for repeated runner lifecycle: load input, validate params, execute, write reproducibility, register artifacts.

Forbidden:

- Free-form workflow ids with no registry validation.
- Same physical artifact registered under multiple canonical labels.
- UI workflow id, task workflow id, result sidecar workflow id, and report workflow id drifting without explicit alias fields.
- Contract files silently missing in release readiness.

## 6. Artifact and Report Standard

Every production analysis must output:

- parameters
- parameter schema snapshot
- summary
- method description
- source metadata
- software versions
- workflow record
- table dictionary when tables exist
- scope contract
- result contract or manifest

Artifact labels must be canonical. Display aliases belong in UI/report adapters, not artifact registry duplication.

## 7. Teaching and Demo Data Standard

Teaching data is protected and non-deletable.

Rules:

- Teaching mode and normal mode are independent states.
- Exiting teaching mode removes `teaching_demo` URL auto-entry and clears active teaching data selection.
- Teaching start failure rolls back to normal mode.
- Teaching data may auto-confirm a preparation plan only in teaching state.
- Demo state must not leak into normal customer mode.

## 8. Testing and Acceptance Standard

Each production feature must have:

- requirements document
- detailed design document
- test plan or acceptance matrix
- executable E2E/API/script validator
- evidence JSON
- screenshots for visual/UI claims
- release receipt with remaining risks

Required matrices:

- state/control availability
- URL/hash/localStorage restore
- empty data, demo data, uploaded data, owner real data
- success, failure, stale response, retry
- customer/admin/teaching mode
- artifact/report export

Release cannot be called owner-ready while:

- authorized real-data manifest is missing
- browser E2E infrastructure is environment-blocked
- report/export chain lacks current passing evidence

## 9. Protected Infrastructure

The following are out of scope for product refactors unless explicitly assigned:

- router
- Headroom
- gateway
- IPC
- front-route
- model route
- Codex control plane

