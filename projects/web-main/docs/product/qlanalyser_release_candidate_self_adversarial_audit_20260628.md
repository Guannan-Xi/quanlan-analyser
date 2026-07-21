# QLanalyser Release Candidate Self-Adversarial Audit

Generated: 2026-06-28T02:21:05.220Z

Final verdict: release_candidate_pass_with_risks
External release verdict: blocked_owner_data_missing

## Checks

- PASS [P0] WW-DISC-01 (global_page): Main data-preparation page exposes a discoverable clean WaveformWorkbench entry.
- PASS [P0] WW-MODE-01 (functional_region): WaveformWorkbench supports basic/epoch mode separation plus customer clean mode.
- PASS [P0] WW-KEY-01 (control_level): WaveformWorkbench exposes keyboard and draggable time-navigation semantics.
- PASS [P0] WW-E2E-01 (business_workflow): WaveformWorkbench basic/epoch/clean dual-mode E2E passed.
- PASS [P0] WW-E2E-02 (business_workflow): WaveformWorkbench epoch review interaction E2E passed.
- PASS [P0] MAIN-METHOD-01 (global_page): Main analysis page exposes 9 analysis methods and keeps QC out of method cards.
- PASS [P0] EPI-MAIN-01 (functional_region): Main app can submit epilepsy ML screening and link to the review workbench.
- PASS [P0] EPI-MAIN-E2E-01 (business_workflow): Main app epilepsy entry E2E proves payload and workbench link contract.
- PASS [P0] EPI-WB-01 (functional_region): Epilepsy workbench separates source output, manual review layer, and lightweight waveform window.
- PASS [P0] EPI-WB-02 (control_level): Epilepsy workbench customer path does not expose TimeChart.
- PASS [P0] EPI-WB-E2E-01 (business_workflow): Epilepsy workbench E2E proves ML run, correction mode review action, undo path, and waveform preview.
- PASS [P0] EPI-ML-01 (business_workflow): Epilepsy ML asset, feature schema, model smoke, and fixture run checks passed.
- PASS [P0] BACKEND-01 (business_workflow): Backend API smoke passed with no blockers.
- PASS [P0] COPY-01 (control_level): No blocking stale customer copy or QC-as-method copy remains in the edited customer path.
- PASS [P1] RELEASE-RISK-01 (business_workflow): External release owner-data regression remains blocked by missing authorized input_manifest.json.

## Blocking Failures

- None for internal release-candidate scope.

## Known Release Risk

- External release still requires authorized anonymous owner-data regression manifest and rerun.
- Existing model deserialization warnings should be tracked before hard external release, although current ML smoke and fixture checks pass.
