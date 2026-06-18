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



## Local Run

Backend API:

```powershell
C:\Users\XGN\miniconda3\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Frontend static dev server:

```powershell
cd frontend
npm run serve
```

If the frontend is opened directly at `http://127.0.0.1:4174/`, pass the API base explicitly:

```text
http://127.0.0.1:4174/?api=http://127.0.0.1:8000/api
```

When served through the local 8765 portal/proxy, the frontend can use the default `/api` base if the proxy forwards API requests.

## V01 Verification

Run backend/core smoke verification with a synthetic annotated FIF file:

```powershell
C:\Users\XGN\miniconda3\python.exe scripts\smoke_v01_api.py
```

Expected coverage: project creation, real EEG upload, metadata extraction, QC, PSD, ERP, planned advanced-method rejection, artifact download, HTML report generation, and ZIP package download.


For full pre-release acceptance, start backend/frontend first, then run:

```powershell
scripts\run_v01_acceptance.ps1
```

This runs compile checks, frontend syntax, core/worker acceptance, full API acceptance, and browser UI acceptance.

See `docs/v01_production_readiness.md` for the launch-readiness matrix and Feishu EEG knowledge-base mapping.

## Development Notes

The current refactor creates the formal architecture and a minimal runnable API surface.
Heavy analysis logic should live in `eeg_core/`; API handlers should call services, and services should call workers or core modules.

