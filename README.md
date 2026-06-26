# QuanLan Analyser

Formal development workspace for the QuanLan research EEG analysis platform.

## Product Boundary

V1 is a research EEG analysis platform, not a medical diagnosis, treatment, or
clinical decision system.

The first release is the paid-pilot operating version for the customer EEG
analysis loop. It must stay aligned with the long-term goal in
`docs/product/LONG_TERM_GOAL_AND_ONE_YEAR_ROADMAP.md`: turn non-standard EEG
analysis into standardized, reproducible, auditable, and commercially operable
research/CRO workflows.

The V1 operating scope includes:

- EEG file upload
- Metadata extraction and display
- QC and preprocessing readiness checks
- Resting-state PSD analysis
- Bandpower analysis from PSD outputs
- ERP analysis from existing event markers
- Single-subject report generation
- Downloadable result packages
- Analysis lab and preset analysis workflows
- Customer registration and login
- Email, phone verification, and WeChat registration sandbox/operable flows
- Sandbox Alipay and WeChat Pay confirmation loops
- Wallet balance, deduction, ledger, and order records
- Customer invoice submission
- Admin invoice review and PDF upload
- Customer inbox delivery for issued invoices
- Admin operations console

Out of scope for V1:

- Clinical diagnosis
- HIS/PACS integration
- AI interpretation
- Full enterprise RBAC beyond the V1 customer/admin boundary
- Real production payment, SMS, WeChat, email, OSS, and backup provider
  certification unless the corresponding third-party callback and cloud
  evidence has been supplied
- Full BIDS workflow
- Visual workflow builder

Sandbox provider flows are allowed in V1 only when the product has real orders,
statuses, records, files, scripts, and evidence. Do not replace executable EEG
analysis, billing, invoice, or admin workflows with static screenshots or copy.

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
C:\Users\XGN\miniconda3\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

Current-source customer review API. Use this for V01 acceptance and customer demo review; `8000` is only a legacy/core-flow fallback if an older local backend is already running:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
python scripts\check_running_backend_contract.py --base-url http://127.0.0.1:8001/api
```

Frontend static dev server:

```powershell
cd frontend
npm run serve
```

If the frontend is opened directly at `http://127.0.0.1:4174/`, pass the API base explicitly:

```text
http://127.0.0.1:4174/?api=http://127.0.0.1:8001/api
```

Customer demo review link with the demo account prefilled/logged in:

```text
http://127.0.0.1:4174/?customer_demo=login&api=http://127.0.0.1:8001/api
```

Demo credentials:

```text
demo.customer@quanlan.cn / demo123456
```

Current public review links:

```text
Customer: http://39.97.248.225/?customer_demo=login&api=http://39.97.248.225/api
Lab:      http://39.97.248.225/module-lab.html?api=http://39.97.248.225/api
API:      http://39.97.248.225/api/health
Admin:    use the top-right management entry, ops@quanlan.cn
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

For Alibaba Cloud staging, first run the no-secret preflight and follow the canonical staging smoke runbook:

```powershell
python scripts\run_release_review_gate.py
```

For manual step-by-step review, run:

```powershell
python scripts\aliyun_staging_preflight.py
python scripts\build_aliyun_owner_input_checklist.py
python scripts\build_release_gate_summary.py
python scripts\acceptance_release_gate_summary.py
python scripts\build_sanitized_review_package.py
python scripts\acceptance_sanitized_review_package.py
```

See `docs/release/aliyun_v1_staging_smoke.md`. Do not claim Aliyun staging or production readiness until strict OSS/storage, backup/restore, and staged full-acceptance evidence have passed.

For the current release-review entry and public deployment evidence, start with:

```text
work\release_evidence\20260620-v01-acceptance\START_HERE_RELEASE_REVIEW.md
work\release_evidence\20260620-v01-public\PUBLIC_DEPLOYMENT_EVIDENCE.md
```

See `docs/v01_production_readiness.md` for the launch-readiness matrix and Feishu EEG knowledge-base mapping.

See `docs/eeg_v01_product_principles.md` for the EEG product principles that connect domain knowledge, customer UX, backend contracts, report evidence, and acceptance checks.

Before accepting any non-trivial product, UI, backend, runner, report, checkpoint, or release work, apply the stage-gated review contract:

```powershell
python scripts\acceptance_stage_gated_review_policy.py
```

The canonical policy is `docs/product/stage_gated_development_review_system.md`; the machine-readable contract is `docs/product/stage_gated_review_contract.json`.

See `docs/PROJECT_STATUS_CURRENT.md` for the clean current project-status entry.

See `docs/modules/analysis_module_contract.md` before adding or promoting any
analysis method.

See `docs/compliance/cro_traceability_contract.md` before adding audit,
review, approval, SOP, role, or controlled-delivery behavior.

## Development Notes

The current refactor creates the formal architecture and a minimal runnable API surface.
Heavy analysis logic should live in `eeg_core/`; API handlers should call services, and services should call workers or core modules.
