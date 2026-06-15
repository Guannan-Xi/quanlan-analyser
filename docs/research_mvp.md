# Research MVP

## Must Ship

1. Upload EEG files.
2. Read and display metadata.
3. Run resting-state PSD analysis.
4. Run ERP analysis from existing event markers.
5. Generate single-subject reports.
6. Download result packages.

## V1 Result Package

```text
result_package.zip
  figures/
    psd.png
    alpha_topomap.png
    erp_waveform.png

  tables/
    band_power.csv
    erp_metrics.csv

  reports/
    report.html

  reproducibility/
    parameters.json
    workflow.yaml
    software_versions.json
    method_description.txt
```

## Not In V1

- Complex permissions
- Payment
- Medical diagnosis
- HIS/PACS
- AI interpretation
- Advanced connectivity
- Full BIDS
- Drag-and-drop workflow builder

## Development Rule

API routes stay thin. Business behavior belongs in `backend/services`. EEG domain logic belongs in `eeg_core`. Long-running execution belongs in `worker`.

