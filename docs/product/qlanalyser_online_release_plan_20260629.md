# QLanalyser Online Release Plan

Date: 20260629
Status: finalized product-level release baseline
Scope: QLanalyser Online staged releases, prioritizing epilepsy analysis trial

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


## 2. Current Overall Verdict

```text
internal_development_status: pass_with_risks
external_full_release_status: blocked_owner_data_missing
nearest_release_priority: epilepsy_analysis_trial
```

The current product can continue internal/pre-release development. Full external release remains blocked by missing authorized anonymized owner-data regression.

## 3. P0: Product Foundation Stabilization

Includes:

- teaching/demo mode;
- data preparation release-candidate controls;
- 8 formal analysis methods + QC dependency contract;
- Results provenance baseline;
- copy governance and non-medical boundary;
- browser E2E infrastructure cleanup.

Exit criteria:

- preflight passed;
- backend smoke passed;
- method source comparison passed;
- data preparation plan acceptance passed;
- current module validator passed;
- copy governance passed.

Status: mostly accepted for internal development; external release still blocked by owner data.

## 4. P0a: Epilepsy Analysis Trial Release

Goal:

```text
Data Preparation -> Epilepsy Workbench -> Candidate/Event Review -> Manual Correction -> Results
```

Trial includes:

- main Analysis child-page entry;
- waveform-first workbench;
- candidate event / event-stage table;
- synchronized waveform/event/spectrogram evidence where available;
- Browse vs Correction mode separation;
- stale waveform write protection;
- save draft/review revision path;
- honest publish-to-Results behavior;
- non-medical research-support wording.

Trial excludes:

- clinical diagnosis;
- treatment/triage recommendations;
- GLP validation claim;
- full PSG/HSAT rule scoring;
- universal animal algorithm validity claim;
- external full product release without owner-data regression.

Exit criteria:

- EPI-001 to EPI-009 pass;
- deterministic teaching/synthetic epilepsy fixture passes;
- if customer trial uses real data, owner anonymized `input_manifest.json` and real-data regression pass;
- Results artifact registration verified or publish remains disabled with reason;
- no direct standalone customer route bypasses Data Preparation context.

Recommended trial label:

```text
Epilepsy research screening trial / not for diagnosis
```

## 5. P1: Sleep Staging Workbench

Includes:

- shared waveform/timeline infrastructure;
- animal and human sleep profiles;
- Stage_Code / hypnogram;
- manual epoch correction;
- Results handoff.

Exit criteria:

- sleep fixture E2E passes;
- stage schema and review revision contracts pass.

## 6. P2: Human PSG / HSAT Foundation

Includes:

- PSG/HSAT channel roles;
- arousal, respiratory, movement, cardiac, oxygen, position/snore event layers;
- RuleGrade metadata;
- controlled AASM V3 rule extraction and QA before rule-level claims.

Exit criteria:

- PSG-001 to PSG-009 pass for foundation;
- full AASM rule tests pass before rule-level release.

## 7. P3: CRO / GLP-ready Workflow Features

Includes:

- Study/Protocol/Animal metadata;
- role permissions;
- audit trail;
- reason-for-change;
- review lock/sign/archive;
- validated export package.

Wording: GLP-ready / GLP-supporting only.

## 8. P4: Scale And Performance

Includes:

- lightweight waveform chunk API;
- min-max/envelope decimation;
- 1-64 channel virtualization;
- spectrogram tiles/cache;
- large EDF regression.

## 9. Owner Decisions Needed

1. Provide authorized anonymized EEG `input_manifest.json` for real-data regression.
2. Decide whether epilepsy trial starts teaching/synthetic-only or includes owner data from the first trial.
3. Define first trial users and acceptable wording.
4. Decide which epilepsy Results artifact package is minimum viable for trial.
5. Confirm whether public/customer trial requires deployment or only local/internal trial.

## 10. Rollback Strategy

- Keep epilepsy workbench behind child-page entry and trial flag until EPI gates pass.
- Disable publish-to-Results if corrected artifact registration is incomplete.
- Keep sleep/PSG/CRO features hidden until their phase gates pass.
- Preserve backup branch / full product baseline; do not push to default branch without acceptance.

## 11. Change Log

- 2026-06-29: Created product-level release baseline and made epilepsy analysis trial the nearest release priority.

## 12. Traceability / Acceptance Mapping

| Phase | Evidence |
| --- | --- |
| P0 foundation | full product E2E review and blocker acceptance |
| P0a epilepsy trial | epilepsy child page E2E + API + visual evidence |
| P1 sleep | waveform scoring workbench six-pack |
| P2 PSG/HSAT | AASM V3 source extract and PSG tests |
| P3 CRO/GLP-ready | future audit/sign/archive evidence |
| P4 performance | waveform chunk/min-max benchmarks |
