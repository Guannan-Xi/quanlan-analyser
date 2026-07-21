# QLanalyser Stage-Gated Development Review System

Date: 2026-06-23
Owner: 07 QLanalyser product owner
Status: mandatory for product development and review-system loops

## 1. Purpose

QLanalyser development must follow the same quality principle as staged media
production: every independent generation or construction step must pass its own
review gate before the next step starts.

For software work this means: requirements, detailed design, implementation,
unit checks, integration, UI interaction, real user path, artifacts, checkpoint,
and release decision are separate gates. A later green check cannot erase an
earlier missing gate.

## 2. Non-bypass rule

No non-trivial QLanalyser work may be accepted with only a summary, screenshot,
or final demo. Each environment and stage must have evidence.

If a gate fails, the work returns to that gate's fix loop. Do not pass failures
downstream.

## 3. Required route

Every non-trivial task uses:

```text
QGCS route decision
-> execution packet
-> executor lane evidence
-> GPT-5.5/Codex acceptance
-> final receipt
-> next real artifact
```

Executor lanes may include `script_validator`, `deepseek_text_worker`,
browser/UI runner, local validator, or bounded worker. Do not claim a lane unless
a real execution id, command output, report path, screenshot, or artifact exists.

## 4. Stage gates

| Gate | Applies to | Required evidence | Pass owner | Cannot proceed to |
|---|---|---|---|---|
| `route_gate` | all non-trivial tasks | route decision, task id, owner, consumer, acceptance | GPT-5.5/Codex | requirements/design |
| `requirement_gate` | product need, page, API, runner, report, deployment | requirements, user path, P0/P1/P2 acceptance, non-goals | GPT-5.5/Codex | design |
| `design_gate` | frontend/backend/runner/artifact/release design | detailed design, API/state/component model, test plan | GPT-5.5/Codex | implementation |
| `implementation_gate` | code/docs/config changes | diff or changed files, scope statement, no unrelated churn | GPT-5.5/Codex | unit/static tests |
| `unit_static_gate` | syntax, schema, UTF-8, focused unit checks | command output and evidence path | script_validator | integration |
| `integration_gate` | API, runner, storage, report, task route | integration command/report, service health, output paths | GPT-5.5/Codex | UI/E2E |
| `ui_interaction_gate` | all user-visible pages and flows | real browser evidence, screenshots, default/empty/loading/error/success/dense/narrow states where applicable | GPT-5.5/Codex | real user path acceptance |
| `real_user_path_gate` | upload/load data -> analysis -> result -> report | UI-only runner evidence, no direct task mutation, downloaded artifact path | GPT-5.5/Codex | artifact gate |
| `artifact_report_gate` | report ZIP/PDF/HTML/manifest/result package | ZIP inventory, required entries, OCR/layout/text checks, scientific boundary checks | GPT-5.5/Codex | checkpoint |
| `checkpoint_access_gate` | every review checkpoint | front-end link, backend health, test account, credential_safety, checkpoint_path, validator pass | script_validator + GPT-5.5/Codex | review-ready claim |
| `release_decision_gate` | local release, staging, production | release review gate, failed_steps=[], external prerequisite status, no release misclaim | GPT-5.5/Codex | release-ready claim |

## 5. Environment coverage

The following environments must attach the stage gates relevant to their work:

- `product_docs`: requirement_gate, design_gate, checkpoint_access_gate when docs support review.
- `frontend_ui`: design_gate, implementation_gate, unit_static_gate, ui_interaction_gate, real_user_path_gate.
- `backend_api`: design_gate, implementation_gate, unit_static_gate, integration_gate.
- `runner_worker`: design_gate, implementation_gate, unit_static_gate, integration_gate, artifact_report_gate.
- `artifact_report`: artifact_report_gate, scientific boundary checks, readability checks.
- `review_checkpoint`: checkpoint_access_gate, credential safety, access validator.
- `release_deploy`: release_decision_gate and external prerequisite preflight.

## 6. Material-production analogy for dev work

For media work the gates are script -> voice/text -> image copy -> frames ->
audio -> sample -> final.

For QLanalyser development the equivalent gates are:

```text
requirement -> detailed design -> implementation -> static/unit -> integration
-> UI interaction -> real user path -> artifact/report -> checkpoint -> release decision
```

A stage is complete only when its evidence exists and GPT-5.5/Codex acceptance
is recorded.

## 7. Required receipt

Every non-trivial visible report must include:

```text
route_decision:
execution_packet_or_skip_reason:
execution_id_or_evidence_path:
executor_evidence:
gpt55_acceptance:
final_receipt:
next_real_artifact:
```

## 8. Failure rules

Use explicit labels instead of vague progress:

- `gate-missing`
- `executor-evidence-missing`
- `acceptance-only-pretended`
- `ui-evidence-missing`
- `artifact-evidence-missing`
- `checkpoint-access-risk`
- `release-misclaim-risk`

## 9. Current local commands

Common local review commands include:

```powershell
node --check frontend\app.js
python scripts\acceptance_results_report_readability_gate.py
python scripts\inventory_latest_edf_e2e_report_zip.py
node scripts\acceptance_edf_upload_to_results_ui_only.mjs
python scripts\run_release_review_gate.py
python scripts\validate_checkpoint_packet_access.py <checkpoint.json>
```

Executor Bus packets should prefer allowlisted commands first. If a desired
command is not allowlisted, record the bus rejection and use an allowed packet or
local validator evidence without claiming fake executor success.

## 10. All-environment review-system coverage

The review system is mandatory in every environment that can affect a real
QLanalyser delivery. A feature cannot move from one environment to the next by
prose, screenshots alone, or a manifest-only pass.

Canonical machine contract:

```text
docs/product/stage_gated_review_contract.json
```

Canonical validator:

```powershell
python scripts\acceptance_review_system_all_environments.py
```

Required environment gates:

| Environment | Gate | Required command or entry | Blocks on |
|---|---|---|---|
| `development_workspace` | `unit_static_gate` | compile/check review scripts and contract | syntax error, mojibake in gate script, missing contract |
| `frontend_ui_e2e` | `ui_interaction_gate` | UI workflow gate plus EDF upload-to-result UI-only run | login blocked, missing action, disabled action without reason, visible mojibake, duplicate/internal copy, horizontal overflow |
| `backend_api_runner` | `integration_gate` | backend health/task contract check | unhealthy API, missing task route, wrong status semantics |
| `runner_artifact_report` | `artifact_report_gate` | artifact label readability and latest report ZIP inventory | missing artifact, unreadable label, internal artifact name, local path leak |
| `release_gate` | `release_decision_gate` | release review runner | failed step, release-ready misclaim, missing external preflight boundary |
| `checkpoint_review_access` | `checkpoint_access_gate` | checkpoint access validator and acceptance | missing URL, account, credential safety, checkpoint path |
| `docs_living_system` | `requirement_gate` | stage-gated policy and all-environment contract validators | conceptual-only rule, missing maintenance rule, missing environment contract |
| `cross_department_handoff` | `route_gate` | QGCS task pool packet results and acceptance summary | no consumer, no executor evidence, single-thread closed loop |

Each environment record must include:

```text
environment_id
entry
gate
command_or_entry
blocking_rules
evidence_path
owner
consumer
```

Maintenance rule: when a new page, API route, runner, artifact type, deployment
target, or department handoff is added, update the contract first, then add a
validator or UI runner step, then wire the step into `scripts/run_release_review_gate.py`.
If the gate cannot run yet, mark the environment `review-blocked` with a concrete
owner and next command; do not mark it review-ready.

## 11. Pre-submission gate for every acceptance, checkpoint, and review artifact

Before every acceptance submission, checkpoint packet, review artifact, or final
release-gate receipt, the current build must pass both:

```powershell
node scripts\acceptance_edf_upload_to_results_ui_only.mjs
node scripts\acceptance_workflow_pages_ui_gate.mjs
```

The first command proves the real user path: login, create/select project,
upload/load EDF, run preparation and analysis modules, view results, and download
the report package. The second command performs page-level visual and interaction
review across the product pages, including login/dashboard, project/data
management, data preparation, analysis tasks, result review, report delivery,
review validation, and personal center.

Blocking rules:

- `e2e_status_not_passed`
- `page_visual_review_missing`
- `visible_mojibake_or_internal_jargon`
- `required_action_missing_or_no_feedback`
- `checkpoint_created_without_fresh_e2e_and_visual_evidence`

A checkpoint without fresh E2E JSON and page-level visual evidence is
`review-blocked`, even if the code compiled or a release manifest exists.
