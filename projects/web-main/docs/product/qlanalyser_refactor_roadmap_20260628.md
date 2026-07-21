# QLanalyser Refactor Roadmap

Date: 2026-06-28  
Status: actionable roadmap  
Rule: low-risk local refactors may be implemented; cross-module refactors require a packet, tests, and rollback plan.

## P0 - Release Evidence and Safety Gates

### P0-A. Browser E2E environment preflight

Problem:

- EDF upload to result/report UI evidence is failed because Playwright browser runtime is missing.

Scope:

- `scripts/lib/playwright_runtime.mjs`
- E2E scripts that directly import Playwright or rely on browser availability

Plan:

1. Add shared runtime preflight that distinguishes:
   - `environment_blocked`
   - `service_unreachable`
   - `product_failed`
2. Make UI E2E JSON write explicit status and reason.
3. Keep existing product assertions unchanged.

Verification:

- Run script syntax checks.
- Run one E2E with known available runtime.
- Simulate missing runtime where feasible.

Rollback:

- Revert helper and script import changes.

### P0-B. Real owner-data regression

Problem:

- Owner release remains blocked until authorized anonymous EEG manifest exists.

Scope:

- `work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/input_manifest.json`
- `scripts/build_real_dataset_owner_review_packet.py`
- `scripts/run_real_dataset_regression_from_manifest.py`

Plan:

1. Wait for owner/data steward manifest.
2. Validate allowed methods and QC dependency.
3. Run data preparation, allowed analyses, report package, and boundary leakage checks.

Verification:

- Owner regression evidence packet.

Rollback:

- None; missing manifest stays blocked by design.

## P1 - Product Architecture Refactors

### P1-A. Analysis workflow registry

Problem:

- `/api/tasks` accepts free module/workflow strings and dispatches mostly by module.

Scope:

- `backend/services/task_service.py`
- new or extended registry service
- task API tests

Plan:

1. Define canonical `(module_name, workflow_id)` registry.
2. Add illegal-combination validation before task creation.
3. Move runner selection and artifact policy into registry records.
4. Normalize PAC/TFR workflow ids or explicit aliases.

Tests:

- Illegal combo: `module_name=pac`, `workflow_id=resting_psd` fails.
- Legal combos pass.
- PAC task/result/manifest workflow consistency.
- TFR estimate returns runnable metadata.

Risk:

- Medium. Touches task creation and many methods.

Rollback:

- Keep old dispatch branch behind registry fallback until tests pass.

### P1-B. Frontend command registry

Problem:

- Large document click chain and repeated buttons make state gating fragile.

Scope:

- `frontend/app.js`
- data-preparation actions first

Plan:

1. Add a `commandRegistry` object for data-preparation commands.
2. Commands expose `canRun`, `disabledReason`, `run`, `sideEffect`, `auditAction`.
3. Existing buttons call registry rather than bespoke branches.
4. Keep selectors and UI unchanged in first pass.

Tests:

- Existing data-preparation control state matrix.
- Disabled command blocked audit.
- Hidden command cannot mutate state.

Risk:

- Medium. Start with data preparation only.

Rollback:

- Keep old handlers until registry tests pass, then remove one action at a time.

### P1-C. Workspace state facade

Problem:

- Duplicate derived-state/render functions in `frontend/app.js`.

Scope:

- `frontend/app.js`

Plan:

1. Create a facade for selected project/file/plan/epoch/task.
2. Replace duplicate state-label functions with facade output.
3. Add static duplicate-function guard.

Tests:

- Project/file/plan matrix.
- Existing RC audit.

Risk:

- Medium because `app.js` is dirty and broad.

Rollback:

- Apply in small slices, one derived label group at a time.

### P1-D. Waveform workbench state machine

Problem:

- Basic/epoch/workbench mode is split across URL, state, config, CSS.

Scope:

- `frontend/waveform-workbench.js`
- `frontend/waveform-workbench.css`
- dual-mode E2E

Plan:

1. Define legal state transitions.
2. Make URL a state adapter.
3. Keep basic preview and epoch review as modes of one state machine.

Tests:

- Existing dual-mode contract.
- Add illegal transition tests.

Risk:

- Medium.

Rollback:

- Preserve existing URL parameters and mode aliases.

## P2 - Cleanups and Hardening

### P2-A. ViewModel copy cleanup

Replace post-render visible-copy cleanup with ViewModel-rendered text.

### P2-B. Module-lab active state

Persist active method tab in app state and optional URL parameter.

### P2-C. Epilepsy review repository

Move review localStorage logic behind a repository adapter and add migration/version tests.

### P2-D. Artifact download policy

Add project/user access checks and path containment checks before file download.

### P2-E. Contract path configuration

Make module contract directory configurable and fail readiness when required contracts are missing.

## Low-Risk Refactors Allowed Immediately

These can be implemented without changing product behavior:

1. Add `DESIGN.md` and design governance docs.
2. Add static duplicate-function detector for `frontend/app.js`.
3. Add browser-runtime preflight helper or evidence status normalization.
4. Add workflow-combo validation tests before changing backend dispatch.

## Do Not Do Yet

- Do not rewrite `frontend/app.js` wholesale.
- Do not merge epilepsy ML source workbench refactor into this packet.
- Do not change router, Headroom, gateway, IPC, front-route, or model route.
- Do not change algorithm math while doing architecture cleanup.

