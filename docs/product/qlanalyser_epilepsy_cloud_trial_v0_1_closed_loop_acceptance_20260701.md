# QLanalyser Epilepsy Cloud Trial Closed-Loop Acceptance - 2026-07-01

Status: passed

## Scope

Cloud customer-trial path from uploading a synthetic labeled EDF to data preparation, epilepsy-like event screening, manual correction, Results readback, and report package export.

## Target

- Frontend: http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=cloud-trial-e2e-20260701c#storage
- API: http://39.97.248.225/api
- Sample EDF: `D:\Quanlan\Codes\Python\quanlan-analyser-official\work\fixtures\epilepsy_regular_labeled\regular_epilepsy_labeled_60s.edf`

## Result

- E2E status: `passed`
- Checks: 34 / 34 passed
- Failed checks: []
- Uploaded file: `eeg_354150e6a928` / `regular_epilepsy_labeled_60s.edf`
- Preparation plan: `prep_411864daf64a` revision `1`
- Epilepsy task: `task_4cd719f44d25` status `completed`
- Report package bytes: `150588`

## Five-Round Adversarial Review

| Round | Question | Verdict | Evidence |
| --- | --- | --- | --- |
| R1-main-path | Can a customer start from cloud upload and reach the epilepsy-like event workbench without local-only shortcuts? | passed | upload_authorization_in_request, uploaded_edf_metadata, plan_confirmed_for_uploaded_file, task_payload_contract |
| R2-scientific-output | Does the workflow produce the expected candidate event and Stage_Code evidence rather than only UI decoration? | passed | stage_code_truth, candidate_event_truth, epilepsy_pc_stft_artifact_contract, inline_spectrogram_same_window_source |
| R3-manual-correction | Can a researcher correct candidate events and preserve review-layer immutability? | passed | review_correction_saved, correction_matrix_actions_saved, review_export_published |
| R4-results-and-export | Do Results and report packages include review outputs and images needed for customer trial review? | passed | results_module_has_review_package, epilepsy_result_image_artifacts, results_module_shows_result_images, report_package_includes_result_images |
| R5-boundary-and-copy | Does the trial avoid epilepsy staging, diagnosis/treatment claims, old labels, video placeholders, and scroll popups? | passed | no_epilepsy_staging_copy, no_diagnosis_or_treatment_copy, customer_review_labels_visible, no_old_labels_in_candidate_panel, inline_wheel_no_toast, no_video_placeholder_copy |

## Screenshots

- Opened: `work\release_evidence\20260701-epilepsy-cloud-trial-final-e2e\01_opened.png`
- After upload: `work\release_evidence\20260701-epilepsy-cloud-trial-final-e2e\02_after_upload.png`
- Inline workbench: `work\release_evidence\20260701-epilepsy-cloud-trial-final-e2e\03_inline_initial.png`
- Results package: `work\release_evidence\20260701-epilepsy-cloud-trial-final-e2e\04_results_review_package.png`

## Boundary

This proves the cloud synthetic-data customer trial closed loop. It does not close the formal external-release blocker. Formal external release still requires owner/data-steward authorized anonymous EEG manifest and real-data regression.

## Next Real Artifact

customer trial operator run + issue log, or owner anonymous EEG manifest for formal release regression
