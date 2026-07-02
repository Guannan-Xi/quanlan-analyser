# QLanalyser Online Requirements

Date: 20260629
Status: finalized product-level baseline for current Online development checkpoint
Scope: QLanalyser Online full product, with epilepsy analysis trial as the nearest release priority

## 1. Product Goal

QLanalyser Online is a non-medical EEG/PSG/neurophysiology research-support platform. The product must provide a coherent web workflow:

```text
Login / teaching mode
-> project and dataset selection
-> Data Preparation
-> Analysis Task
-> Embedded Analysis / Scoring Workbench
-> Manual Review / Correction where applicable
-> Results
-> Report / Export
```

The system must not become a collection of disconnected mini-apps. Data preparation, analysis, epilepsy workbench, sleep workbench, Results, and reports must share one navigation shell, one inherited context model, and one evidence/audit trail.

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


## 3. Release Priority

The near-term priority is to bring the epilepsy analysis workflow online for controlled trial use.

Trial scope:

- inherited entry from the main Analysis page after Data Preparation;
- waveform-first epilepsy workbench inside the main navigation frame;
- candidate-event / event-staging review;
- synchronized waveform, event strip, and review table;
- correction actions stored as review draft/revision, not overwriting source output;
- Results handoff when corrected artifacts are registered;
- non-medical research-support wording.

Trial must not claim clinical seizure diagnosis, treatment suggestion, clinical triage, or full external release readiness.

## 4. Product Modules

### M1 Login / teaching / customer demo

- Teaching mode must protect built-in demo data.
- Customer demo mode must hide developer-only details.
- Error prompts must appear only after real failure.

### M2 Data Preparation

- Data Preparation is upstream of all analysis.
- It owns file selection, waveform preview, bad-channel/bad-segment drafts, QC dependency, and confirmed preparation plan revisions.
- It must avoid duplicate controls and misleading status text.

### M3 Formal analysis methods

Current formal methods are:

1. PSD / Band Power
2. ERP
3. TFR
4. Multitaper PSD
5. Multitaper TFR
6. Reference / CSD
7. PAC
8. Connectivity

QC is a Data Preparation dependency, not a formal analysis card.

### M4 Epilepsy analysis workbench

- Must be a child page in the main Analysis flow.
- Must inherit Data Preparation context.
- Must open with waveform evidence, not a static placeholder.
- Must support candidate/event review and manual correction.
- Must separate source algorithm output from review layer.
- Must publish only registered corrected artifacts to Results.

### M5 Sleep staging workbench

- Planned as a sibling workbench sharing waveform/timeline/review infrastructure.
- Supports Stage_Code / hypnogram / epoch correction.
- Animal and human profiles must be explicit.

### M6 PSG / HSAT extension

- Planned after sleep foundation.
- Must separate stage labels from arousal, respiratory, movement, cardiac, oxygen, position/snore, and HSAT layers.
- AASM V3 rule-level support requires controlled rule extraction and QA.

### M7 Results / report / export

- Results displays source outputs and review outputs with provenance.
- Reports must include data preparation plan, task id, method, parameters, source artifact, review revision when applicable, and non-medical boundary.

### M8 CRO / GLP-ready roadmap

- Support Study, Protocol, Animal/Cohort, ScoringProfile, AuditTrail, reason-for-change, lock/sign/archive in later phases.
- Use GLP-ready / GLP-supporting wording only.

## 5. Product Boundaries

Required:

- Raw data immutable.
- Confirmed Data Preparation revisions immutable.
- Source algorithm outputs immutable.
- Manual corrections append review actions and produce review revisions.
- Results consumes registered artifacts only.

Forbidden:

- clinical diagnosis wording;
- treatment advice;
- static fake waveform/video evidence;
- buttons that appear usable but do nothing;
- duplicate primary controls for the same task;
- direct standalone customer flow for epilepsy/sleep workbenches without inherited context.

## 6. Current Status Summary

| Area | Status | Notes |
| --- | --- | --- |
| Full product internal development | pass_with_risks | P0 fixes accepted; internal work can continue. |
| External full release | blocked | Missing real anonymized owner-data regression manifest. |
| Data Preparation page | local release-candidate | Passed adversarial cleanup; external release still needs real-data regression. |
| 8 formal analysis methods | accepted by smoke/source comparison | QC remains dependency, not method card. |
| Epilepsy child page | ready for focused trial-hardening | Release E2E receipt exists; remaining gaps must be closed before trial. |
| Waveform Scoring Workbench | six-pack baseline exists | Covers epilepsy/sleep/PSG/animal/CRO roadmap. |

## 7. Open Decisions

1. Which authorized anonymized epilepsy dataset will be used for trial validation?
2. What is the first epilepsy trial user group and acceptable risk label?
3. Should trial use teaching/synthetic only first, or include owner anonymized EDF from day one?
4. Which artifacts must Results display before trial: event table only, waveform snapshot, spectrogram, or full review package?

## 8. Change Log

- 2026-06-29: Created product-level finalized baseline and marked epilepsy analysis trial as near-term release priority.

## 9. Traceability / Acceptance Mapping

| Requirement | Architecture | Design | Contract | E2E | Release |
| --- | --- | --- | --- | --- | --- |
| Epilepsy trial | Child workbench | Epilepsy workbench UI | ReviewSession/Event/Results artifacts | EPI/API/visual tests | P0a |
| Data Preparation inheritance | Context boundary | Analysis entry gate | data_preparation_plan_id/revision | preparation gate tests | P0 |
| Formal methods | Analysis service boundary | 8 method cards | task/artifact contracts | smoke/source comparison | P0 |
| Results honesty | Results boundary | publish disabled until artifact exists | ResultsArtifact | publish tests | P0a |
| Sleep/PSG roadmap | shared scoring workbench | stage/event layers | Stage/Event/RuleGrade | SLP/PSG tests | P1/P2 |

## Product-Level Release Guardrail Terms

- Owner data gate: external release needs authorized anonymized owner data and `input_manifest.json` regression evidence.

