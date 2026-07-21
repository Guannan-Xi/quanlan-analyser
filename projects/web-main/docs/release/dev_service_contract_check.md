# Dev Service Contract Check

Updated: 2026-06-19

Purpose: prevent browser acceptance from using a stale FastAPI process.

## Why This Check Exists

During C0/C4 validation, `http://127.0.0.1:8000/api/health` could still return `ok` while its OpenAPI schema did not expose the current data preparation routes. A fresh backend on `8001` exposed the expected routes.

Health alone is therefore not enough before UI acceptance. The running service must also expose the current contract in OpenAPI.

## Required Routes

The backend used by the frontend must expose:

```text
GET  /api/eeg/files/{file_id}/data-preparation-plan
POST /api/eeg/files/{file_id}/data-preparation-plan
GET  /api/eeg/files/{file_id}/data-preparation-plans
GET  /api/data-preparation/plans
POST /api/data-preparation/plans
```

## Command

Check the API base URL that the frontend will use:

```powershell
python scripts\check_running_backend_contract.py --base-url http://127.0.0.1:8001/api --evidence-dir work\release_evidence\latest
```

To compare a suspected stale service and the current service:

```powershell
python scripts\check_running_backend_contract.py --base-url http://127.0.0.1:8000/api --base-url http://127.0.0.1:8001/api --evidence-dir work\release_evidence\latest
```

If any checked service lacks the required routes, the script exits non-zero. For browser acceptance, use only a service whose check result is `ok: true`.

## C4 Browser Acceptance Rule

Before running Playwright or manual owner review:

1. Start or identify the backend port.
2. Run the contract check against that exact API base URL.
3. Set the frontend API URL to the checked backend, for example:

```powershell
$env:QLANALYSER_API_URL = "http://127.0.0.1:8001/api"
```

4. Capture browser evidence only after the contract check passes.
