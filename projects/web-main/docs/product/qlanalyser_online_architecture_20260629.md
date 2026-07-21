# QLanalyser Online Architecture

Date: 20260629
Status: finalized product-level architecture baseline
Scope: Online product architecture, with epilepsy trial route as P0a

## 1. Architectural Principle

QLanalyser Online uses a single main product shell. Specialized workbenches are child pages that inherit context from Data Preparation and Analysis, not standalone tools.

```text
MainShell
  LoginTeachingDemo
  ProjectDatasetContext
  DataPreparation
  Analysis
    FormalMethodTasks
    EpilepsyWorkbenchChild
    SleepWorkbenchChild
    PsgHsatWorkbenchFuture
  Results
  ReportsExports
```

## 2. Sources

Sources used:
- `docs/product/qlanalyser_full_product_complete_e2e_review_20260627.md`
- `docs/product/qlanalyser_complete_e2e_release_blocker_fixes_acceptance_20260627.md`
- `docs/product/data_preparation_adversarial_audit_and_cleanup_20260628.md`
- `docs/product/epilepsy_child_page_p0_ui_api_e2e_test_plan_20260629.md`
- `docs/product/epilepsy_inline_workbench_release_e2e_receipt_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_requirements_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_architecture_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_data_api_contract_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_e2e_test_plan_20260629.md`
- `docs/product/qlanalyser_waveform_scoring_workbench_release_plan_20260629.md`

Sources blocked / controlled:
- External full release remains blocked by missing authorized anonymized EEG `input_manifest.json` for owner-data regression.
- AASM V3 / PSG rules are partially incorporated at architecture/category level only; full rule-level extraction remains controlled internal reference pending QA.
- GLP-ready is a workflow-support target, not a claim that the software or customer facility is GLP-certified.


## 3. State Ownership

```text
L0 Raw data                         immutable
L1 Data Preparation plan/revision   immutable after confirmation
L2 Source analysis output           immutable
L3 Review draft                     editable, local/server session
L4 Review revision                  saved server-authoritative artifact
L5 Results artifact                 published and traceable
L6 Archive/sign-off                 future controlled workflow
```

Epilepsy trial uses L0-L5. GLP archive/sign-off is future scope.

## 4. Main Boundaries

### Data Preparation owns

- selected file / teaching dataset;
- QC dependency;
- waveform preview for preparation;
- bad channel / bad segment draft;
- confirmed preparation plan id and revision.

### Analysis owns

- formal method task creation;
- method parameter validation;
- task status;
- source artifacts.

### Epilepsy Workbench owns

- inherited task and preparation context;
- waveform/event/timeline review state;
- manual correction draft/revision;
- publish-to-Results action after artifact registration.

### Results owns

- display of source and reviewed artifacts;
- report/export references;
- provenance chain.

## 5. Epilepsy Trial Architecture

```text
Analysis method card / task
-> Open Epilepsy Workbench child route
-> Load inherited context
-> Load waveform window / candidate events
-> Browse mode by default
-> Correction mode only when waveform is ready and target selected
-> Save review draft/revision
-> Register corrected artifacts
-> Results opens reviewed output
```

P0a must preserve:

- request sequence / stale waveform protection;
- Browse mode is read-only;
- Correction mode cannot write while waveform is stale/loading;
- direct standalone URL without inherited context shows controlled blocked state;
- Results publish button is disabled until corrected artifacts exist.

## 6. Shared Timeline Architecture

Waveform, spectrogram, stage/event strip, table, and details panel subscribe to one timeline state:

```json
{
  "window_start_sec": 0,
  "window_duration_sec": 30,
  "selected_event_id": null,
  "selected_epoch_indices": [],
  "request_seq": 0,
  "window_key": "file:start:duration:revision"
}
```

## 7. Performance Architecture

Near-term:

- use lightweight waveform chunk/window API for browsing;
- avoid full QC task path for pan/zoom;
- include timing metrics where possible;
- cache adjacent windows;
- reject stale async responses.

Future:

- min-max/envelope chunking;
- spectrogram tiles/cache;
- 1-64 channel virtualization;
- binary transfer if JSON becomes bottleneck.

## 8. Non-Touch Boundaries

This product-level architecture does not require changes to:

- router;
- Headroom;
- gateway;
- IPC;
- model route;
- TimeChart dependency;
- unrelated billing/admin internals.

## 9. Architecture Risks

| Risk | Control |
| --- | --- |
| Epilepsy trial mistaken for medical diagnosis | Non-medical copy gate and Results scope statement |
| Static/placeholder evidence reaches customer | E2E verifies real waveform/event artifacts or honest unavailable state |
| Source output overwritten | L2/L3/L4 separation |
| Results overclaim | Publish disabled until artifacts registered |
| External release blocked | Owner-data manifest and real-data regression gate |


## Product-Level Release Guardrail Terms

- non-medical boundary: the product is research support only and must not claim diagnosis, treatment, or clinical triage.
- Owner data gate: external release needs authorized anonymized owner data and `input_manifest.json` regression evidence.
- non-medical boundary: the product is research support only and must not claim diagnosis, treatment, or clinical triage.

## 10. Change Log

- 2026-06-29: Created product-level architecture baseline with epilepsy trial route.

## 11. Traceability / Acceptance Mapping

| Boundary | Contract | Test | Release |
| --- | --- | --- | --- |
| Data Preparation inheritance | plan id/revision/contract version | entry gate E2E | P0/P0a |
| Epilepsy child route | task + prep + result link params | child page E2E | P0a |
| Review revision | ReviewAction/ReviewRevision | save/publish tests | P0a/P1 |
| Results | ResultsArtifact | artifact registration tests | P0a |
