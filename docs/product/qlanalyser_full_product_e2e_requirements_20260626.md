# QLanalyser Full Product E2E Requirements

Date: 2026-06-26
Owner: 07-PM / QLanalyser acceptance
Repo: D:\Quanlan\Codes\Python\quanlan-analyser-official
Status: requirements source before implementation and full-product E2E

This document is the requirements source for the next full-product acceptance cycle. Requirements must be transferred through this file and its matching design and test-plan documents, not through chat-only memory.

## 0. PDCA Rule

Every task in this cycle must run as a closed PDCA loop:

| Phase | Required artifact | Pass condition |
|---|---|---|
| Plan | Requirement row, scope, risk, expected evidence | Scope is explicit and mapped to a real file, route, page, method, or artifact |
| Do | Script, browser path, generated fixture, review packet, or code change | Work is bounded and does not silently change unrelated modules |
| Check | JSON evidence, screenshot, source comparison, report inventory, or DeepSeek review output | Evidence is saved and readable; failures name the exact requirement ID |
| Act | Fix, backlog item, blocked receipt, or acceptance record | No issue is left as an undocumented observation |

The acceptance cycle is incomplete if a task has Plan and Do but no Check and Act record.

## 1. Product Boundary

QLanalyser is a non-medical EEG research and CRO workflow product. It must not claim diagnosis, treatment, clinical decision support, causal proof, exact source localization, or cohort-level scientific validity from synthetic or single-record evidence.

Synthetic EDF and virtual data are required for deterministic E2E and regression checks. They prove workflow execution, input/output contracts, report packaging, and figure QA. They do not prove real-world method validity.

## 2. Required Knowledge Gates

This cycle adopts the following knowledge-base gates:

| Gate | Source | Adopted rule |
|---|---|---|
| `NEURAL_SIGNAL_METHOD_BENCHMARK_GATE` | `D:\QuanLanKnowledgeBase\learning-notes\qlanalyser\NEURAL_SIGNAL_METHOD_BENCHMARK_VALIDATION_GATE_CN.md` | Each method needs input contract, output contract, benchmark/fixture plan, limitations, and pass/revise/block decision |
| `NEURAL_SIGNAL_REGRESSION_FIXTURE_GATE` | `D:\QuanLanKnowledgeBase\learning-notes\qlanalyser\NEURAL_SIGNAL_ALGORITHM_REGRESSION_FIXTURE_STANDARD_CN.md` | Synthetic fixture must record seed, signal definition, expected recovery, tolerance, artifacts, and baseline update policy |
| `UX_DESIGN_CRITIQUE_GATE` | `D:\QuanLanKnowledgeBase\learning-notes\design\UX_DESIGN_CRITIQUE_WORKFLOW_RUBRIC_CN.md` | UI review must check task orientation, hierarchy, layout, color, state feedback, chart integrity, accessibility, and brand trust |
| `B2B_SCIENTIFIC_DASHBOARD_SCREENSHOT_AUDIT_GATE` | `D:\QuanLanKnowledgeBase\learning-notes\design\B2B_SCIENTIFIC_DASHBOARD_SCREENSHOT_AUDIT_CHECKLIST_CN.md` | Research dashboards need default, dense, empty, loading, error, success, disabled/focus, narrow, and wide evidence when relevant |
| `UX_STATE_COVERAGE_GATE` | `D:\QuanLanKnowledgeBase\learning-notes\design\UX_STATE_FEEDBACK_EMPTY_ERROR_LOADING_MOTION_GATE_CN.md` | Upload, analysis, rendering, report, and export paths need loading/error/success/recovery evidence |
| `DESIGN_TOKEN_GOVERNANCE_GATE` | `D:\QuanLanKnowledgeBase\learning-notes\design\DESIGN_TOKENS_VISUAL_REGRESSION_GATE_CN.md` | UI colors, spacing, status colors, focus, chart palettes, and raw hex risks must be checked |
| `VISUAL_REGRESSION_REVIEW_GATE` | `D:\QuanLanKnowledgeBase\learning-notes\design\VISUAL_REGRESSION_BASELINE_NAMING_SCREENSHOT_SET_STANDARD_CN.md` | Screenshots must encode product, surface, state, density, viewport, theme, locale, browser, OS, and version |
| `QLANALYSER_CRITICAL_TASK_ONBOARDING_GATE` | `D:\QuanLanKnowledgeBase\learning-notes\qlanalyser\QLANALYSER_ONBOARDING_CRITICAL_TASK_RESULT_INTERPRETATION_GATE_CN.md` | Critical user tasks must show guidance, recovery, result interpretation boundaries, and browser evidence |

Skipped rules: public dataset benchmark and summative human-factors validation are not claimed in this local E2E cycle. They remain required before external release or real-customer validation.

## 3. Full Product Scope

The cycle covers:

- Cover/home/login surfaces: `frontend/index.html`, `frontend/expert-entry-demo.html`, `frontend/open-design-entry-demo.html`.
- Main workbench: project, data, data preparation, current modules, analysis tasks, result review, report delivery, personal/account surfaces.
- Method review surfaces: `frontend/module-lab.html`, `frontend/research-modules.html`, `frontend/research-module/*.html`, `frontend/qc-lab.html`.
- Backend APIs: health, accounts, projects, subjects, EEG files, templates, tasks, artifacts, reports, billing, data CRUD, data preparation, workflow, admin.
- Analysis methods: QC/data preparation, PSD, ERP, TFR, Multitaper PSD, Multitaper TFR, Reference/CSD, PAC, Connectivity.
- Report package: HTML, PDF, figures, tables, method text, parameters, software versions, workflow, processing record.
- Visual system: sidebar, color tokens, method cards, tables, waveform preview, result charts, report/export states, admin/ops surfaces.
- Scroll and layout behavior: vertical scroll, sticky/visible controls, horizontal overflow, long lists, dense data, mobile/narrow viewport, wide desktop viewport.

## 4. Functional Requirements

### FR-1. Cover and Login Path

Plan:

- Cover/home/login must make the product identity, user role, and next action clear within the first viewport.
- Login/register/admin tabs must not expose developer wording or internal IDs.

Do:

- Use a synthetic or demo account path only.
- No production credentials or external writes.

Check:

- Browser E2E opens cover/login surfaces at 1440, 1280, 390 widths.
- Screenshots verify no overlap, no horizontal overflow, and visible next action.

Act:

- P0 if login/register/admin cannot be reached.
- P1 if first viewport hides the main action or scroll traps controls.

### FR-2. Backend API and Admin Path

Plan:

- All registered API routes must be inventoried and smoke-tested according to role and risk.
- Admin pages must be reviewed as operational tools, not marketing pages.

Do:

- Use local API at `http://127.0.0.1:8001/api`.
- Read-only admin list routes may be probed. Mutating or billing routes require fixture-safe payloads or are marked as skipped with reason.

Check:

- API inventory JSON records route, method, expected status, auth assumption, and response schema notes.
- Admin UI screenshot set covers overview, account/task/billing/invoice/status surfaces where available.

Act:

- P0 if health/task/report routes required by the main workflow fail.
- P1 if admin status surfaces leak absolute paths, secrets, or internal-only stack traces.

### FR-3. Synthetic Data and Virtual Fixture

Plan:

- Build a deterministic synthetic EDF fixture that includes continuous rhythms, event markers, controlled ERP response, frequency burst for TFR, PAC-like coupling, and channel-level relationships for connectivity.
- Record seed, sampling rate, channels, events, signal definitions, expected output ranges, and known limitations.

Do:

- Generate fixture under `work/release_evidence/07-full-product-e2e-pdca/fixtures/`.
- Do not use real customer data.

Check:

- Fixture manifest includes checksum, seed, channels, event counts, expected recovery targets, and license/sensitivity status.

Act:

- P0 if fixture lacks manifest, checksum, seed, or generation script evidence.
- P1 if fixture cannot exercise ERP/TFR/PAC/connectivity prerequisites.

### FR-4. Analysis Method Correctness and Source Comparison

Plan:

- Each method must be compared against its implementation source and expected reference-library behavior.
- The comparison must verify input fields, output files, figure semantics, boundaries, and warnings.

Do:

- Read `eeg_core/analysis/*.py`, `backend/services/task_service.py`, and method-specific acceptance scripts.
- Run each method through local API or direct runner with the synthetic fixture.

Check:

- Method evidence matrix records:
  - source file and runner function
  - frontend action
  - backend `module_name`
  - `workflow_id`
  - required parameters
  - output artifacts
  - figure titles/axes/units/legends
  - limits and forbidden claims
  - reference library/API comparison notes
  - repeated-run stability result

Act:

- P0 if method output schema does not match task-service contract.
- P0 if figures imply diagnosis, causality, exact localization, or statistical significance not supported by the method.
- P1 if a method has no clear source comparison row.

### FR-5. Main Workbench Full User Path

Plan:

The user path must be:

```text
Open product
-> create/select project
-> upload/select EDF
-> automatic data preview
-> reversible QC/data preparation edits
-> select each analysis method
-> run analysis
-> inspect result preview
-> generate/download report package
```

Do:

- Use browser E2E and synthetic EDF.
- Run all direct analysis actions: PSD, ERP, TFR, Multitaper PSD, Multitaper TFR, Reference/CSD, PAC, Connectivity.
- QC remains data-preparation path, not duplicate analysis button.

Check:

- Evidence records every task id, module name, workflow id, status, report package path, and screenshot.
- No step depends on hidden developer tools.

Act:

- P0 if a method button creates the wrong backend module or workflow.
- P0 if report generation omits current task evidence.

### FR-6. Data Preparation and Reversibility

Plan:

- Clicking data must auto-preview.
- Bad channel, segment exclusion, and event label edits must be visible near waveform preview and reversible.

Do:

- Execute add/restore cycles for one bad channel, one segment, and one event label.

Check:

- Evidence records before/after values, timestamp, user source, reversible flag, preparation plan inclusion, and restored state.

Act:

- P0 if restore is not available or original data is destructively changed.
- P1 if tools are below the fold on desktop 1440x900 without a visible anchor.

### FR-7. Report and Export Integrity

Plan:

- Report package must match current analysis tasks and include reproducibility materials.

Do:

- Generate/download report ZIP after E2E method runs.

Check:

- Inventory verifies HTML, PDF, manifest, figures, tables, method text, parameters, software versions, workflow/provenance, and processing record.
- OCR or text scan checks no forbidden diagnostic/clinical/causal claims.

Act:

- P0 if report package is static demo content or tied to the wrong task.
- P0 if report exposes local absolute paths, keys, or private internal IDs in user-facing files.

### FR-8. UI Visual and Scroll Governance

Plan:

- UI review must cover cover/home, main workbench, data preparation, analysis tasks, results, reports, admin/ops, Module Lab, method library, and research module detail pages.
- Review must inspect scroll behavior, not just first viewport.

Do:

- Use Playwright screenshots at desktop 1440x1000, laptop 1280x800, narrow 390x844, and wide 1920x1080.
- Capture top, middle, bottom, and important scrolled states for long pages.

Check:

- Visual review JSON includes screenshot paths, viewport, state, scroll position, findings, and decision.
- Color/token audit checks sidebar, status colors, chart palette, focus ring, and raw-value risk.

Act:

- P0 if controls overlap, horizontal overflow blocks use, focus path is lost, or errors are hidden below unreachable scroll.
- P1 if visual hierarchy is confusing for researchers, even when the function runs.

### FR-9. Researcher Workflow Logic

Plan:

- Operation order must match researcher habits: inspect data quality before analysis, show prerequisites before unavailable methods, keep parameters and outputs traceable, and separate descriptive results from interpretation.

Do:

- Use DeepSeek official direct route for Chinese logic and workflow review after Codex writes this requirements/design/test package.

Check:

- DeepSeek review output is saved under `work/release_evidence/07-full-product-e2e-pdca/deepseek/`.
- Codex reviews and accepts/rejects DeepSeek findings; DeepSeek does not make final release decisions.

Act:

- P0 if DeepSeek route is unavailable and no replacement logic review is documented.
- P1 if workflow language is technically correct but unnatural for researchers.

## 5. Non-Goals

- No production deployment.
- No router, Headroom, IPC, gateway, or process communication changes.
- No real customer data.
- No clinical validation or medical-device claim.
- No destructive cleanup of the dirty worktree.
- No `git add .` or broad commit.

## 6. Acceptance Outputs

The final acceptance cycle must produce:

- Requirements document: this file.
- Detailed design document: `docs/product/qlanalyser_full_product_e2e_design_20260626.md`.
- E2E validation document: `docs/product/qlanalyser_full_product_e2e_test_plan_20260626.md`.
- Synthetic fixture manifest.
- Method source comparison matrix.
- API and page inventory.
- UI visual/scroll review packet.
- Report ZIP inventory and forbidden-claim scan.
- DeepSeek logic review packet or explicit blocked record.
- Final acceptance packet with `completed_final_receipt` or `blocked_final_receipt`.

## 7. Stop and Block Rules

Stop and emit `blocked_final_receipt` if:

- Local frontend/backend cannot be started or reached after two bounded attempts.
- Synthetic EDF cannot be generated with enough events/channels to exercise the required methods.
- A method cannot run because its backend contract is missing or inconsistent.
- DeepSeek official route is unavailable and the user specifically requires DeepSeek review before acceptance.
- UI E2E finds a P0 navigation, scroll, or state-recovery failure that cannot be fixed in this cycle.
- Any report/export artifact contains unsafe clinical/diagnostic/causal overclaim that cannot be corrected without product-owner decision.

## 8. DeepSeek Researcher Logic Review Amendments

Source:

```text
work/release_evidence/07-full-product-e2e-pdca/09_deepseek/researcher_logic_review_ascii.md
```

Codex adoption status: accepted as requirements refinements unless marked otherwise. These amendments do not turn DeepSeek into the release owner; they become additional requirements for this E2E cycle and later repair packets.

| ID | Mapped requirement | Requirement amendment | Blocking level |
|---|---|---|---|
| DS-F1 | FR-3, FR-5 | Synthetic and imported data checks must record channel type assumptions. Mixed EEG/EOG/EMG/other channels must be detected or explicitly marked as unsupported/needs review before method execution. | P1 for full-product release; not a blocker for synthetic all-EEG local smoke if documented |
| DS-F2 | FR-6 | Do not claim automatic bad-channel removal unless the UI gives the researcher a review/override step. Current requirement remains manual, reversible marking/restore. | P1 copy/logic boundary |
| DS-F3 | FR-4, FR-5 | PSD must show a data-quality prerequisite warning when data have not been previewed/prepared or when artifact/filter status is unknown. | P1 |
| DS-F4 | FR-4 | ERP must validate event marker presence and consistency, including missing markers and duplicate timestamps where detectable. | P1 |
| DS-F5 | FR-4 | TFR must warn when epoch/trial length is too short for the lowest requested frequency. | P2 |
| DS-F6 | FR-4 | Connectivity must show a data-length and stationarity caution; coherence/correlation outputs remain descriptive sensor-space associations. | P2 |
| DS-F7 | FR-5, FR-8 | Preview surfaces must say whether they use full data or a subset. If subset, show the subset rule. | P1 |
| DS-F8 | FR-8 | Long analyses over 5 seconds need stage/progress feedback or an honest long-task status. | P1 |
| DS-F9 | FR-8 | Scroll/layout tests must include dense scientific pages with long channel lists or large frequency-bin tables. | P2 |
| DS-F10 | FR-4, FR-7 | Do not claim manual artifact rejection, all EEG file formats, real-time analysis, cloud processing, or multi-user collaboration unless a requirement and evidence row exists. | P0 claim boundary |

Additional method-specific prerequisites:

- ERP default baseline window must be visible when ERP is run.
- PAC phase and amplitude frequency bands must be visible in the parameter summary.
- Multitaper taper/time-bandwidth parameters must be visible when exposed by the backend.
- Reference/CSD must explain whether channel-location metadata are required or whether the current run is limited to supported sensor-space transforms.

## 9. Backend/Admin Smoke and Visible Copy Addendum

This addendum closes the post-acceptance gap found after the synthetic full-product E2E packet: backend/admin behavior must have standalone evidence, not only a health check.

### FR-10. Backend and Admin API Smoke

Plan:

- Verify the running API contract and in-process backend route behavior with fixture-safe requests.
- Cover health/readiness, OpenAPI route presence, customer login, admin login, admin authorization, admin overview, admin state, projects, wallet, inbox, demo dataset, and demo run-all.
- Mutating requests are allowed only for local synthetic/demo data and must be labelled as fixture-safe.

Do:

- Generate `04_backend_api/backend_api_smoke.json`.
- Reuse `scripts/check_running_backend_contract.py` for route-contract evidence when a local 8001 service is available.

Check:

- Customer and admin tokens are issued from seeded demo accounts.
- Customer endpoints reject or accept requests according to role.
- Admin endpoints require admin authorization and return structured JSON.
- Demo run-all returns the expected synthetic task modules without real customer data.

Act:

- P0 if admin data is visible without authorization.
- P0 if seeded customer/admin login fails.
- P1 if only health/openapi is covered and no authenticated backend smoke exists.

### FR-11. Product-Wide Visible Copy Guard

Plan:

- User-facing pages must not depend on developer wording, route names, ZIP/internal IDs, or mojibake text.
- The copy guard must include cover/login, main workbench, current available modules, data preparation, reports, admin entry, Module Lab, and method-library pages.

Do:

- Run product-wide copy governance with evidence under `08_ui_visual_scroll/product_wide_ux_copy_governance.json`.
- Extend mojibake detection so common UTF-8/GBK failure phrases are caught before acceptance.

Check:

- Required user-facing phrases exist, including `当前可用模块`, `预览方法，需复核`, `生成交付报告`, and `下载完整报告`.
- Banned developer-facing terms do not appear in visible default copy.
- Mojibake/readiness scan covers frontend, backend, eeg_core, docs, and scripts changed in this cycle.

Act:

- P0 if visible copy is unreadable, unsafe, or clinically overclaims.
- P1 if developer/internal wording is visible on a normal customer path.
