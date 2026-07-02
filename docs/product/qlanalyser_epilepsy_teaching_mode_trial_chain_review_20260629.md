# QLanalyser Epilepsy Teaching Mode Trial Chain Fix And Adversarial Review

Status: completed_internal_teaching_chain_candidate
Date: 2026-06-29

## Scope

This packet covers the teaching-mode path for the main-navigation inline epilepsy workbench only:

Teaching mode -> built-in epilepsy EEG fixture -> protected data preparation plan -> inline epilepsy workbench -> screening/staging task -> waveform + STFT preview + Stage_Code + candidate event -> manual correction -> backend review session -> export reviewed artifacts.

Out of scope: sleep staging, real owner-data regression, standalone legacy epilepsy page, router/Headroom/gateway/IPC/model route, TimeChart, broad UI redesign.

## Files Changed In This Slice

- `frontend/app.js`
  - Added module-aware teaching dataset loading.
  - `openEpilepsyWorkbenchFromPlan()` now asks teaching mode to load `/lab/demo/epilepsy` before opening the inline epilepsy console.
  - Added inline teaching boundary notice for the epilepsy workbench.
  - Teaching protected data now disables upload action and blocks rename action in the UI.
- `backend/services/storage_service.py`
  - Uploading into a protected teaching project now raises `TEACHING_DATASET_PROTECTED`.
- `scripts/e2e_main_epilepsy_entry_contract.mjs`
  - E2E now starts from the real teaching button instead of manually seeding the workspace.
  - Added epilepsy-specific teaching fixture assertions.
  - Added payload assertions for task and review session.
- `scripts/validate_teaching_epilepsy_protection.py`
  - Added backend protection regression for epilepsy teaching project/file.

Note: `frontend/app.js` already contains earlier Waveform/Data Preparation/Epilepsy workbench changes in the dirty working tree. This document describes only the incremental teaching-mode hardening slice.

## Root Cause

The main teaching entry originally loaded the general teaching oddball dataset (`proj_demo_learning / eeg_demo_teaching_oddball`). The epilepsy E2E could still pass because it manually seeded a valid epilepsy fixture path in a later step. That created a false positive: the real customer teaching path and the test path were not the same.

## Fix Summary

1. Introduced `loadTeachingDatasetForModule(moduleName)`.
2. Kept normal teaching mode on `/lab/demo/dataset`.
3. Switched epilepsy inline workbench in teaching mode to `/lab/demo/epilepsy`.
4. Verified task payload uses:
   - `project_id = proj_demo_epilepsy_lab`
   - `input_file_id = eeg_demo_epilepsy_high_amplitude`
   - `workflow_id = epilepsy_ml_xgboost`
5. Added teaching boundary copy inside the inline epilepsy workbench.
6. Added frontend and backend protection against upload/rename/delete/overwrite of teaching data.

## Five-Round Adversarial Review

### Round 1 - Entry Truthfulness

Question: Does the visible teaching entry use the same data as the epilepsy workbench test?

Finding: No. The entry loaded the general oddball teaching dataset, while the successful epilepsy path depended on manual E2E seed.

Decision: Accepted as P0. Fixed by module-aware teaching dataset loading.

Evidence: E2E `seed_workspace = not_used_teaching_entry_only`; final task payload uses epilepsy teaching project and file.

### Round 2 - Data Protection

Question: Can teaching data be accidentally uploaded over, renamed, deleted, or modified?

Finding: Rename/delete had backend protection; upload into protected teaching project was not guarded at the same layer. Frontend upload could also appear actionable.

Decision: Accepted as P0/P1. Added backend upload guard and frontend upload/rename block.

Evidence: `scripts/validate_teaching_epilepsy_protection.py` passed all checks.

### Round 3 - User Boundary And Copy

Question: Does the epilepsy workbench make clear that teaching data is synthetic and not real customer data or diagnostic evidence?

Finding: Global teaching banner existed, but the epilepsy console itself did not carry a local boundary statement.

Decision: Accepted as P1. Added `data-testid="inline-epilepsy-teaching-boundary"` note.

Evidence: E2E check `teaching_epilepsy_boundary_visible = true`.

### Round 4 - End-to-End Functional Chain

Question: Does the teaching path complete the actual analysis-console workflow, not just open a page?

Finding: After fixing the data path, the E2E validates page entry, task creation, waveform, STFT preview, Stage_Code selection, manual correction, review session save, and export artifact registration.

Decision: Accepted as internally complete for teaching trial.

Evidence: `scripts/e2e_main_epilepsy_entry_contract.mjs` passed 64/64 checks.

### Round 5 - Release Readiness Risks

Question: Is this externally release-ready?

Finding: Teaching internal trial path is ready. External release still needs owner-authorized real-data regression and a production spectrogram contract. The teaching guide overlay required an E2E-only fallback to close reliably during automated navigation; product behavior remains unchanged.

Decision: Internal teaching chain candidate accepted; external release remains gated by broader product release criteria.

## Verification

Passed:

- `node --check frontend/app.js`
- `node --check scripts/e2e_main_epilepsy_entry_contract.mjs`
- `python -m py_compile backend/services/storage_service.py scripts/validate_teaching_epilepsy_protection.py`
- `python scripts/validate_teaching_epilepsy_protection.py`
- `node scripts/e2e_main_epilepsy_entry_contract.mjs`
- `node scripts/validate_epilepsy_child_page_p0_contract.mjs`
- `node scripts/e2e_epilepsy_child_page_p0.mjs`

Primary E2E evidence:

- `work/release_evidence/20260628-main-epilepsy-entry-contract/main_epilepsy_entry_contract.json`
- `work/release_evidence/20260628-main-epilepsy-entry-contract/03_main_to_epilepsy_child_page.png`
- `work/release_evidence/20260628-main-epilepsy-entry-contract/04_synchronized_spectrogram_300s.png`

Main E2E result:

- status: passed
- checks: 64/64
- review session create: 1
- review session patch: 1
- review session export: 1

## Remaining Risks

P1:

- Teaching guide overlay automation needed a test fallback to close before navigating. Product behavior appears functional, but a dedicated teaching-guide E2E should separately verify close/next/finish controls.
- Right-side toast can temporarily cover part of the correction panel; this is not a chain blocker but should be cleaned before customer polish.
- STFT is still clearly labeled as lightweight waveform-chunk preview, not formal TFR/PSD/Band Power artifact.

P0 external-release gate still outside this slice:

- Owner-authorized real EEG regression remains required before external release.

## Final Receipt

final_receipt: completed_epilepsy_teaching_mode_trial_chain_ready_for_internal_acceptance
