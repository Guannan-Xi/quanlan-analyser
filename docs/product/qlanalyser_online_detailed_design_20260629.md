# QLanalyser Online Detailed Design

Date: 20260629
Status: finalized product-level detailed design baseline
Scope: current Online UI/interaction design, with epilepsy trial as primary near-term flow

## 1. Sources

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


## 2. Product Navigation

Use one global shell:

```text
Home / Project / Data / Analysis / Results / Reports / Account
```

Specialized pages such as epilepsy and sleep workbenches open inside this shell. They must not show standalone upload/lab controls in customer inherited mode.

## 3. Data Preparation Design

Primary task:

```text
Select data -> inspect waveform -> prepare bad channels/segments -> confirm preparation plan
```

Rules:

- one primary timeline/progress control;
- no duplicate time/progress widgets with equal weight;
- no Epoch controls in basic preparation mode;
- write actions live in the current selection/draft panel;
- waveform area is interactive Canvas evidence, not a static image;
- teaching data is protected from upload/delete/overwrite actions.

## 4. Analysis Page Design

Formal analysis methods display as task cards for the 8 methods. QC remains a preparation dependency.

Epilepsy trial entry appears as a child workbench entry when:

- data preparation is confirmed or teaching demo provides a confirmed context;
- source epilepsy task or fixture-backed source exists;
- non-medical trial label is visible.

## 5. Epilepsy Workbench P0a Design

Opening state:

- user first sees waveform and context header;
- mode is Browse;
- correction buttons are disabled with reason until Correction mode and valid target;
- stale/loading waveform state is visually explicit.

Main regions:

```text
Context strip: dataset, prep plan/revision, task/source status
Evidence toolbar: browse/correction mode, window controls, gain, event visibility
Waveform panel: primary EEG evidence
Event/stage strip: candidate and correction overlays
Spectrogram panel: review evidence, synchronized with waveform when available
Event table: candidate list / selected interval
Right panel: current selection, suggested actions, reason/comment, history, save/publish
```

Button rules:

- Browse mode never writes review actions.
- Correction mode writes only when current waveform window is ready.
- Save draft persists review state; publish to Results requires registered corrected artifacts.
- Undo/Redo operate on correction commands.
- Direct URL without inherited context shows blocked guidance.

## 6. Sleep / PSG Future Design

Sleep workbench reuses the same shell:

- Stage_Code / hypnogram are epoch-level;
- human W/N1/N2/N3/REM and animal Wake/NREM/REM profiles are separate;
- PSG interval layers are separate from stage labels;
- HSAT profile hides unavailable PSG-only controls.

## 7. Results Design

Results must show:

- source task output;
- data preparation plan id/revision;
- review revision if applicable;
- corrected event/stage table;
- provenance and non-medical scope.

No UI may say “published” until the backend/artifact registry confirms the artifact exists.

## 8. Customer Copy Rules

Allowed:

- candidate event;
- research support;
- manual review;
- reviewed result;
- GLP-ready workflow features.

Forbidden:

- diagnosis;
- confirmed clinical seizure;
- treatment advice;
- clinical triage;
- GLP certified software.


## Product-Level Release Guardrail Terms

- Owner data gate: external release needs authorized anonymized owner data and `input_manifest.json` regression evidence.

## 9. Change Log

- 2026-06-29: Created product-level detailed design baseline and epilepsy trial UI rules.

## 10. Traceability / Acceptance Mapping

| UI rule | Test |
| --- | --- |
| First view shows waveform | epilepsy child page visual E2E |
| Browse read-only | UI-06 |
| Stale waveform disables correction | UI-09/API-03 |
| Publish honesty | UI-10/API-04 |
| No duplicate primary controls | UI-05 and adversarial review |
