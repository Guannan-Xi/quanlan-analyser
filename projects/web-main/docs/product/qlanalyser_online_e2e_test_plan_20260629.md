# QLanalyser Online E2E Test Plan

Date: 20260629
Status: finalized product-level E2E baseline
Scope: full Online product gates and epilepsy trial release gates

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


## 2. Test Strategy

Testing proves the chain:

```text
Teaching/real data -> Data Preparation -> Analysis -> Epilepsy Workbench -> Manual Correction -> Results
```

For external full release, real anonymized owner-data regression is mandatory.

## 3. P0 Product Gates

### ONLINE-001 Preflight

- Backend reachable.
- Frontend reachable.
- Teaching/demo flags work.

### ONLINE-002 Login / teaching protection

- Teaching data loads.
- Teaching data cannot be deleted/overwritten/upload-mutated.

### ONLINE-003 Data Preparation

- Select data.
- Waveform visible.
- Bad-channel/bad-segment draft works.
- Confirmed preparation plan id/revision exists.

### ONLINE-004 Formal analysis methods

- 8 formal method entries visible.
- QC is not an analysis card.
- Backend smoke/source comparison passes.

### ONLINE-005 Results

- Completed task artifacts display.
- Provenance and non-medical scope visible.

## 4. Epilepsy Trial P0a Gates

### EPI-001 Inherited entry

- From Analysis page, open epilepsy child page with task id, plan id, revision, contract version, and Results target.

### EPI-002 First visible waveform

- Workbench opens with waveform evidence and context header.
- No static fake waveform is used.

### EPI-003 Direct URL blocked

- Opening epilepsy workbench without inherited context shows controlled blocked state.

### EPI-004 Browse mode read-only

- Click/drag/keyboard actions in Browse do not write review actions.

### EPI-005 Correction mode writes only when ready

- Correction buttons disabled during loading/stale/no-target.
- Valid correction appends command and enables Undo.

### EPI-006 Stale response protection

- Fast window changes cannot let old waveform overwrite new state.

### EPI-007 Save / publish honesty

- Save draft stores review state or clearly labels local draft.
- Publish Results remains disabled until corrected artifacts are registered.

### EPI-008 API contract

- Session/context API includes data preparation plan/revision/version.
- Waveform API includes identity or client-side stale guard evidence.

### EPI-009 Visual regression

- 1440, 1280, and 390 widths have no blocking overflow or unusable primary controls.

## 5. Trial Data Gates

### TRIAL-001 Teaching/synthetic fixture

- Epilepsy workflow passes with deterministic fixture.

### TRIAL-002 Owner anonymized data

- `input_manifest.json` exists.
- Checksums and allowed methods are valid.
- Real dataset regression passes.

P0a internal trial may begin with TRIAL-001 plus a clear data-risk label. External or customer trial needs TRIAL-002 unless owner explicitly scopes it as teaching/demo-only.

## 6. Non-Medical Copy Gate

Scan UI/docs for forbidden claims:

- diagnosis;
- confirmed clinical seizure;
- treatment advice;
- clinical triage;
- GLP certified software.

## 7. Performance Gates

For epilepsy trial:

- context header visible quickly;
- waveform first visible within acceptable local budget;
- pan/zoom does not trigger full QC task path when lightweight API exists;
- stale/loading state is visible and disables writes.

## 8. Release Verdict Rules

- Any failure in inherited entry, first waveform, Browse read-only, stale write protection, or publish honesty blocks epilepsy trial.
- Missing owner-data regression blocks external full release.
- Missing backend waveform identity may be partial only if client stale guard evidence passes and P1 backend gap is recorded.


## Product-Level Release Guardrail Terms

- Owner data gate: external release needs authorized anonymized owner data and `input_manifest.json` regression evidence.

## 9. Change Log

- 2026-06-29: Created product-level E2E baseline and epilepsy trial gate matrix.

## 10. Traceability / Acceptance Mapping

| Flow | Tests |
| --- | --- |
| Data Preparation to Analysis | ONLINE-003/004 |
| Epilepsy child page | EPI-001/003 |
| Waveform evidence | EPI-002/006 |
| Manual correction | EPI-004/005/007 |
| Results | ONLINE-005/EPI-007 |
| External release | TRIAL-002 |
