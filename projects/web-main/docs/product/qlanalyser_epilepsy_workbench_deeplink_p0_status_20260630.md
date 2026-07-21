# QLanalyser epilepsy workbench P0 status - 2026-06-30

## Status

- Deep-link epilepsy workbench bootstrap: **passed on cloud E2E**.
- Teaching epilepsy EDF path: **passed**.
- Ordinary cloud upload-to-export E2E: **passed**.
- Current release slice verdict: **cloud synthetic EDF trial path ready for acceptance**.

## Cloud targets

- Deep-link teaching workbench:
  `http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=deeplink-e2e-20260630b#epilepsyWorkbenchInline`
- Uploaded EDF trial path:
  `http://39.97.248.225/?customer_demo=auto&api=http%3A%2F%2F39.97.248.225%2Fapi&v=correction-matrix-e2e9#storage`

## Accepted fixes

1. Deep-link hash preservation.
   - `#epilepsyWorkbenchInline` is preserved instead of being silently replaced by dashboard.
   - Epilepsy deep-link intent triggers the epilepsy demo bootstrap.

2. Teaching target selection.
   - Epilepsy workbench deep-link loads the epilepsy EDF demo path.
   - It does not default to the oddball FIF teaching dataset.

3. Teaching overlay behavior.
   - Deep-link bootstrap suppresses the blocking teaching overlay.
   - Target workbench remains reachable and testable.

4. Uploaded EDF path hydration.
   - E2E automation state is exposed for `e2e*` version markers.
   - Uploaded EDF results hydrate in the inline epilepsy workbench after backend task completion.

5. Copy-boundary assertion.
   - The cloud upload-to-export E2E now allows negative boundary text such as "not for diagnosis".
   - It still blocks unsafe positive claims such as diagnosis conclusion, confirmed diagnosis, treatment advice, or clinical triage recommendation.

## Evidence

- Deep-link evidence:
  `work/release_evidence/20260630-epilepsy-deeplink-bootstrap-cloud/deeplink_bootstrap.json`
- Upload-to-export evidence:
  `work/release_evidence/20260630-epilepsy-cloud-trial-v0-1-cloud-upload-to-export/browser_upload_to_export.json`

Latest upload-to-export evidence:

```json
{
  "status": "passed",
  "check_count": 34,
  "failed_checks": [],
  "uploaded_file_id": "eeg_f7788b10e2f0",
  "data_preparation_plan_id": "prep_1a2f0a161df1",
  "epilepsy_task_id": "task_d10bc7a94fa0",
  "report_id": "report_89d7518fc9c8",
  "result_images": [
    "figures/epilepsy_ml_event_timeline.svg",
    "figures/epilepsy_ml_spectrogram_preview.svg"
  ]
}
```

## Verified path

The cloud E2E covers:

- synthetic labelled EDF upload;
- upload authorization gate;
- data preparation plan confirmation;
- epilepsy task payload contract;
- backend task completion;
- Stage_Code and candidate event truth checks;
- manual correction action matrix;
- review draft save;
- review export publish;
- Results module review package;
- report package with SVG result images;
- failure gates for missing upload authorization, unconfirmed preparation, wrong workflow, and missing review session;
- customer copy governance, including no epilepsy staging copy and no unsafe diagnosis/treatment copy;
- waveform-first inline entry;
- wheel interaction without toast;
- progress completion;
- spectrogram same-window source and PC STFT artifact contract;
- stage overlay toggle.

## Remaining non-blocking follow-up

- Cloud HTML still has legacy encoding / malformed markup debt in some static areas. The active epilepsy trial path works, but the markup should be cleaned in a separate UI debt slice before a broader customer demo.
- This evidence proves the cloud synthetic EDF trial path. External release still needs the owner-approved anonymous real EDF regression package when that data is available.

## Boundary

Keep wording as candidate event screening / research support / manual review. Do not use epilepsy staging, diagnosis conclusion, confirmed diagnosis, treatment advice, or clinical triage recommendation wording.
