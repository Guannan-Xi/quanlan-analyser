# 64-channel QEEG method recovery

This is a local, reusable analysis package rebuilt from the retained 64-channel report artifacts and verified existing QLanalyser algorithm sources. It contains no patient recordings or generated reports.

`run_recovered_full_pipeline` applies QC then runs all recovered methods over the QC-retained complete recording. A non-pass safety gate remains explicit in the structured result.

Nonlinear complexity estimators use up to 5,000 evenly spaced samples from the complete retained recording. This bounds estimator cost while preserving coverage from the beginning to the end of the recording; spectral, spatial, microstate, connectivity, and coupling measures use all retained samples.

Install optional automatic ICLabel support with `pip install -e ".[qc-iclabel]"`.
# Recovered 64-channel QEEG report pipeline

This project restores the modular, full-recording 64-channel QEEG workflow
from retained structured report outputs. It reads the source recording without
modifying it, writes all results to a new output directory, and keeps the
analysis modules separate from report rendering.

## Run the complete report

```powershell
cd D:\Quanlan\Codes\Python\qlanalyser-workspace\projects\qeeg-64ch-research
python -m qlanalyser_eeg64 `
  "D:\path\to\recording.bdf" `
  ".\results\v0.2.1-scientific-layout" `
  --include-aperiodic
```

The command produces:

- `analysis_summary.json`: complete machine-readable analysis contract
- `report.html` and `technical-details.html`: standalone report pages
- `assets\`: full-recording scientific figures
- `tables\`: structured CSV results
- `visual_manifest.json`: figure size, palette, typography, and layout evidence

All quantitative modules receive the one-second epoch-screened, retained data.
`AUTO_PASS_BLOCKED` is intentionally preserved when automated ICA cannot be
completed; the report remains descriptive review material and is not labelled
as automatically approved.

## Test

```powershell
python -m pytest -q
```

## Refresh saved report pages

When `analysis_summary.json`, `visual_manifest.json`, and the existing assets
are already present, refresh the HTML and historical compatibility CSVs without
reopening the raw EEG recording:

```powershell
python -c "from qlanalyser_eeg64.report import refresh_report_from_saved_artifacts; refresh_report_from_saved_artifacts(r'.\results\v0.2.5-historical-html-complete\analysis_summary.json')"
```
