# QLanalyser Staging Synchronized Waveform/Video/Stage/Spectrogram E2E Test Plan

Date: 2026-06-29
Status: P0 E2E contract

## 1. Test Target

URL:

```text
http://127.0.0.1:4174/?customer_demo=auto&teaching_demo=auto&api=http://127.0.0.1:8001/api&v=main-epilepsy-entry#analysis
```

Evidence directory:

```text
work/release_evidence/20260628-main-epilepsy-entry-contract/
```

## 2. Required P0 Checks

T-SYNC-01: Video and spectrogram evidence panels exist only inside the epilepsy staging child page.

- Selectors:
  - `[data-testid="inline-epilepsy-video-panel"]`
  - `[data-testid="inline-epilepsy-video-canvas"]`
  - `[data-testid="inline-epilepsy-spectrogram-panel"]`
- Expected: visible after entering the child page.

T-SYNC-02: Waveform, video, spectrogram, and Stage_Code share scale state.

- Click `[data-epilepsy-action="set-time-scale"][data-scale-sec="300"]`.
- Expected:
  - `[data-testid="inline-epilepsy-waveform-canvas"] data-sync-scale == "300"`
  - `[data-testid="inline-epilepsy-spectrogram-canvas"] data-sync-scale == "300"`
  - `[data-testid="inline-epilepsy-stage-strip"] data-sync-scale == "300"`

T-SYNC-03: Event selection synchronizes all three panels.

- Click event `evt-2`.
- Expected waveform and spectrogram `data-selected-event == "evt-2"`; Stage_Code selected cell corresponds to event 2.

T-SYNC-04: Scale change preserves selected event.

- Select `evt-1`, switch 5s -> 30s -> 300s.
- Expected selected event stays `evt-1` in waveform and spectrogram.

T-SYNC-05: Scale change preserves correction draft.

- Select `evt-1`, set Normal, switch scale.
- Expected draft ledger still contains `evt-1: Normal`.

T-SYNC-06: Spectrogram copy stays inside review-evidence boundary.

- Expected text includes review/evidence wording.
- Expected text does not claim formal TFR/Band Power output.

T-SYNC-07: No duplicate scale controls.

- Expected scale controls exist in shared toolbar only; Stage_Code and spectrogram do not create separate independent zoom controls.

T-SYNC-08: Existing epilepsy child-page P0 contract still passes.

- Run `node scripts/e2e_epilepsy_child_page_p0.mjs`.

## 3. Visual Evidence

Required screenshots:

- `03_main_to_epilepsy_child_page.png`: after interaction closure and publish.
- `04_synchronized_spectrogram_300s.png`: 300s scale after event selection.

## 4. Acceptance

Pass requires all existing main epilepsy checks plus all `T-SYNC-*` checks. Any independent hidden timeline, misleading formal TFR wording, video evidence presented as diagnosis, or correction draft loss during scale changes is P0 failure.
