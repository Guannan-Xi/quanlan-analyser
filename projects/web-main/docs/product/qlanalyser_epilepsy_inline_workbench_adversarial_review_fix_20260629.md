# QLanalyser Inline Epilepsy Workbench Adversarial Review And Fix

Status: internal_trial_candidate_improved

Date: 2026-06-29

## Scope

Target page:

`/?customer_demo=auto&teaching_demo=auto&api=http://127.0.0.1:8001/api&v=main-epilepsy-entry#epilepsyWorkbenchInline`

This review covers the main-system inline epilepsy workbench, including page copy, task flow, waveform, Stage_Code strip, spectrogram evidence layer, manual correction draft, Results boundary, and frontend/backend truthfulness.

## Sources Used

- Screenshot provided by owner: epilepsy inline workbench page, 2026-06-29.
- `frontend/app.js`
- `frontend/styles.css`
- `frontend/index.html`
- `backend/api/epilepsy_workbench.py`
- `scripts/e2e_main_epilepsy_entry_contract.mjs`
- `scripts/validate_epilepsy_child_page_p0_contract.mjs`
- QLanalyser-PC reference source:
  - `D:\Quanlan\Codes\Python\AR_analyser1\AR_analyser_PC\src\BasicalAnalysisViewerTimeFrequency.py`
  - worker-read evidence for `EpilepsyAnalysis.py` / `QlassAnalysis.py` STFT patterns.

## Five-Round Adversarial Review

### Round 1 - Page-Level Task Clarity

Finding:

The page correctly places waveform first, but the surrounding text still mixes analysis-page context, workbench context, and Results context.

Decision:

Keep the page inside the main navigation shell. Do not restore a standalone workbench or a fake Results jump.

Change:

No broad layout change in this slice. Results publishing remains disabled and honest.

### Round 2 - Scientific Evidence Truthfulness

Finding:

The spectrogram area was a static tile heatmap, not computed from EEG data. This is unsafe for a neuroscience-facing workbench because it looks like evidence.

Accepted change:

Replaced static tiles with a Canvas spectrogram preview computed from the current waveform chunk. The preview uses a lightweight STFT-like calculation, 0.5-50 Hz frequency bins, log power, and 10/99 percentile color scaling inspired by QLanalyser-PC.

Boundary:

The UI now states this is a lightweight STFT preview from waveform chunk data. Formal TFR / PSD / Band Power still require analysis-module output and artifact registration.

### Round 3 - Interaction State Machine

Finding:

`Stage_Code` cells had `data-epilepsy-action="select-epoch"` but no handler, so they looked interactive while doing nothing.

Accepted change:

Added epoch-to-event mapping. Clicking a Stage_Code cell now selects the mapped candidate event and keeps waveform, Stage strip, and spectrogram `data-selected-event` synchronized.

### Round 4 - Manual Correction And Backend Truthfulness

Finding:

Manual correction save currently writes local frontend state only. The backend has review-session endpoints, but the inline page does not yet patch or export through them.

Accepted change:

The inline page now creates a backend epilepsy review session, PATCHes the full current draft snapshot, and exports corrected review artifacts before enabling Results publish.

Boundary:

Exported outputs are a manual correction layer: reviewed epochs, reviewed events, review actions, and review manifest. The source ML artifacts remain read-only and are not overwritten.

### Round 5 - Regression And Release Boundary

Finding:

The trial path must keep user flow working while preventing overclaiming.

Verification:

The main E2E now asserts:

- epilepsy card opens inline child page;
- task is created only after start screening;
- payload carries data preparation plan id, revision, and contract version;
- video panel is absent for current scope;
- waveform is ready;
- spectrogram is a Canvas `waveform_chunk_stft_preview`, not static tiles;
- Stage_Code click selects the mapped event;
- correction writes local draft;
- publish remains disabled pending corrected artifact registration.

## Verification Evidence

Passed:

- `node --check frontend/app.js`
- `node --check scripts/e2e_main_epilepsy_entry_contract.mjs`
- `node scripts/validate_epilepsy_child_page_p0_contract.mjs`
- `node scripts/e2e_main_epilepsy_entry_contract.mjs`

Evidence paths:

- `work/release_evidence/20260628-main-epilepsy-entry-contract/main_epilepsy_entry_contract.json`
- `work/release_evidence/20260628-main-epilepsy-entry-contract/03_main_to_epilepsy_child_page.png`
- `work/release_evidence/20260628-main-epilepsy-entry-contract/04_synchronized_spectrogram_300s.png`

## Remaining P0/P1

P0 remaining:

- Run owner-authorized real-data regression before any external release claim.

P1 remaining:

- Replace frontend STFT preview with a backend `/spectrogram-window` or task-artifact contract for real uploaded data performance.
- Reduce repeated boundary text further after backend persistence is connected.
- Add visual regression screenshots for 1440, 1280, and 390 px.

## Final Receipt

final_receipt: completed_epilepsy_inline_workbench_review_session_export_internal_trial_candidate
