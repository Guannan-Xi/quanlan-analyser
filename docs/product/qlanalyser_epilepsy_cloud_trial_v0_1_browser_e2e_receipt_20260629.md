# QLanalyser Epilepsy-like Event Screening Cloud Trial v0.1 - Browser E2E Receipt

Status: `local_browser_demo_pass_cloud_upload_browser_pending`.

## Scope

This receipt records the current browser E2E evidence for the inline epilepsy-like event workbench in the main QLanalyser navigation shell.

It is intentionally not a cloud trial release approval, because the completed browser E2E uses the local teaching/demo fixture path rather than a real trial account uploading an EDF from the browser.

## Local Browser Target

```text
http://127.0.0.1:4174/?customer_demo=auto&api=http%3A%2F%2F127.0.0.1%3A8001%2Fapi&v=epilepsy-release-real-path#analysis
```

## Script

```text
node scripts/e2e_main_epilepsy_entry_real_path.mjs
```

## Evidence

```text
work/release_evidence/20260629-epilepsy-release-e2e/main_epilepsy_entry_real_path.json
work/release_evidence/20260629-epilepsy-release-e2e/01_workflow_epilepsy_card.png
work/release_evidence/20260629-epilepsy-release-e2e/02_inline_console_initial.png
work/release_evidence/20260629-epilepsy-release-e2e/03_inline_console_completed.png
```

## Passed Assertions

- The epilepsy-like event screening card is visible in the main analysis page.
- The workbench opens inline inside the main shell, not as a detached standalone page.
- No task is created before the user clicks start.
- The submitted task uses `module_name=epilepsy_ml`.
- The submitted task uses `workflow_id=epilepsy_ml_xgboost`.
- The submitted task includes a confirmed preparation plan id, revision, and `qlanalyser-data-preparation-v0.2`.
- The task completes.
- The UI state is synchronized with the completed task.
- Epoch prediction artifacts include Stage_Code.
- Event artifacts include the synthetic candidate event.
- Stage_Code `000001100000` is visible.
- Candidate event `25.0-35.0s` is visible.
- Waveform, Stage_Code strip, and spectrogram panels are visible.
- Backend artifacts are registered.

## Known Limitation

The evidence JSON currently contains mojibake in some captured Chinese text fields. This does not invalidate the functional assertions, but it blocks customer-facing release readiness until a UTF-8/copy governance pass proves the rendered DOM and stored evidence are clean.

## Remaining Browser E2E Required For v0.1 RC

A separate browser test is still required:

```text
scripts/e2e_epilepsy_cloud_trial_upload_to_export_browser.mjs
```

Minimum required path:

1. Open the cloud/staging or local trial URL.
2. Create or select a project.
3. Upload `work/fixtures/epilepsy_regular_labeled/regular_epilepsy_labeled_60s.edf`.
4. Confirm upload authorization.
5. Read back uploaded file metadata.
6. Confirm the data preparation plan.
7. Enter the inline epilepsy-like event workbench from the main analysis page.
8. Click `Start screening`.
9. See progress and completion feedback.
10. Verify Stage_Code `000001100000`.
11. Verify candidate event `25.0-35.0s`.
12. Apply one manual correction and save a review revision.
13. Export CSV/JSON.
14. Open the Results module and verify the v0.1 export package is visible.

## Change Log

- 2026-06-29: Added local browser E2E receipt and separated it from cloud upload browser acceptance.
