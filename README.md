# QuanLan Analyser

Formal development workspace for the QuanLan research EEG analysis platform.

## Product Boundary

V1 is a research analysis platform, not a clinical diagnosis system.

The first release focuses on:

- EEG file upload
- Metadata extraction and display
- Resting-state PSD analysis
- ERP analysis from existing event markers
- Single-subject report generation
- Downloadable result packages

Out of scope for V1:

- Clinical diagnosis
- HIS/PACS integration
- AI interpretation
- Complex permissions
- Payments
- Full BIDS workflow
- Visual workflow builder

## Repository Layout

```text
frontend/   Browser UI for project, data, QC, analysis, results, and reports.
backend/    API, domain models, storage, metadata, task, and report services.
worker/     Background task entry points for metadata, preprocessing, PSD, ERP, and reports.
eeg_core/   EEG IO, preprocessing, analysis, statistics, reporting, and workflow code.
data/       Local development data roots for uploads, derivatives, and reports.
docs/       Product architecture and Research MVP documentation.
outputs/    Historical static MVP and generated demo assets.
work/       Development scripts and local tooling.
```

## Development Notes

The current refactor creates the formal architecture and a minimal runnable API surface.
Heavy analysis logic should live in `eeg_core/`; API handlers should call services, and services should call workers or core modules.

