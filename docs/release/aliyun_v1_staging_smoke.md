# QLanalyser V01 Aliyun Staging Smoke

Date: 2026-06-20
Owner: C0 architecture / release
Status: canonical staging entry point; does not contain secrets

## Release Claim Boundary

Current verified claim:

- Local current-source V01 production-grade review package passed.
- Historical DeepSeek official-direct Chinese copy gate passed; latest bandpower/lab-boundary copy still requires official-direct review before public release.
- Payment, verification, WeChat auth, invoice delivery, and Aliyun storage are sandbox/local or prerequisite-gated unless real provider credentials and staging evidence are supplied.

Do not claim Aliyun staging or production readiness until the strict staging checks below pass and the evidence is read back.

## Target Topology

Preferred ECS topology for first staging:

- Single public origin on Nginx.
- Frontend static files served from `/`.
- Backend FastAPI served behind `/api`.
- Large upload proxy limits and timeouts explicitly configured.
- Object storage set to Aliyun OSS only for isolated staging bucket smoke.
- Local JSON state is acceptable for first staging smoke only; database-backed state remains V1.x hardening.

Template:

```text
deploy/aliyun/nginx.single-origin.conf
```

Replace the upstream address and `server_name` for the target ECS instance before enabling it.
To avoid deploying placeholders, render the config with:

```powershell
python scripts\render_aliyun_nginx_config.py --server-name https://<staging-host> --upstream 127.0.0.1:8001
```

The rendered file is written to:

```text
work/release_evidence/20260620-aliyun-staging/nginx.single-origin.rendered.conf
```

Environment template:

```text
deploy/aliyun/qlanalyser-v01-staging.env.example
```

Copy it into the staging runtime or CI secret store and replace placeholders there. Do not commit filled secrets.

Fallback topology:

- Frontend static host and API split by port.
- The exact frontend origin must be included in `QLANALYSER_CORS_ORIGINS`.
- The review link must pass the API base explicitly with `?api=...`.

## Required Environment

Never commit these values. Export them only in the staging runtime or CI secret store.

```text
QLANALYSER_PUBLIC_BASE_URL=https://<staging-host>
QLANALYSER_API_BASE_URL=https://<staging-host>/api
QLANALYSER_CORS_ORIGINS=https://<staging-host>

QLANALYSER_STORAGE_BACKEND=oss
QLANALYSER_ALIYUN_OSS_ENDPOINT=<oss endpoint>
QLANALYSER_ALIYUN_OSS_BUCKET=<isolated staging bucket>
QLANALYSER_ALIYUN_OSS_ACCESS_KEY_ID=<secret>
QLANALYSER_ALIYUN_OSS_ACCESS_KEY_SECRET=<secret>
QLANALYSER_ALIYUN_OSS_ALLOW_WRITE=1
QLANALYSER_ALIYUN_OSS_LIFECYCLE_POLICY_EVIDENCE=<path to exported lifecycle policy json>
QLANALYSER_ALIYUN_OSS_PREFIX=qlanalyser-v01-staging

QLANALYSER_ALIYUN_BACKUP_BUCKET=<isolated staging backup bucket>
QLANALYSER_ALIYUN_BACKUP_PREFIX=qlanalyser-v01-staging-backup
```

## Preflight

Run from the repository root before any strict cloud smoke:

Install the Python runtime dependencies in the staging environment first:

```powershell
python -m pip install -r requirements.txt
```

This is required for the Aliyun OSS SDK (`oss2`) used by strict storage smoke.

Recommended local review gate:

```powershell
python scripts\run_release_review_gate.py
```

This produces:

```text
work\release_evidence\20260620-v01-acceptance\release_review_gate_run.json
```

Manual step-by-step commands:

```powershell
python scripts\aliyun_staging_preflight.py
python scripts\build_aliyun_owner_input_checklist.py
python scripts\build_release_gate_summary.py
python scripts\acceptance_release_gate_summary.py
python scripts\build_sanitized_review_package.py
python scripts\acceptance_sanitized_review_package.py
```

This writes:

```text
work\release_evidence\20260620-aliyun-staging\aliyun_staging_preflight.json
work\release_evidence\20260620-aliyun-staging\owner_input_checklist.md
work\release_evidence\20260620-v01-acceptance\release_gate_summary.json
work\release_evidence\20260620-v01-acceptance\release_gate_summary.md
work\release_evidence\20260620-v01-sanitized-review.zip
```

Strict mode is for CI or release gates:

```powershell
python scripts\aliyun_staging_preflight.py --strict
```

Strict mode fails until all required env, OSS lifecycle evidence, `oss2`, and deployment origin values are present.

After any strict preflight run, regenerate the owner checklist and release gate summary:

```powershell
python scripts\build_aliyun_owner_input_checklist.py
python scripts\build_release_gate_summary.py
python scripts\acceptance_owner_input_checklist.py
python scripts\acceptance_release_gate_summary.py
python scripts\refresh_release_readiness_manifest.py
python scripts\build_sanitized_evidence_bundle.py
```

## Strict Cloud Smoke

Only after preflight returns `ready_for_strict_staging`:

```powershell
python scripts\acceptance_aliyun_storage_contract.py --target aliyun --strict
python scripts\acceptance_backup_restore_drill.py --target aliyun --strict
```

Then run the full product acceptance against the staged frontend/API:

```powershell
$env:QLANALYSER_API_URL="https://<staging-host>/api"
$env:QLANALYSER_FRONTEND_URL="https://<staging-host>/?api=https://<staging-host>/api"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_v01_acceptance.ps1
```

Record the produced evidence paths in:

```text
work\release_evidence\20260620-v01-acceptance\evidence_manifest.json
work\release_evidence\20260620-production-boundary\production_boundary_and_aliyun_gap.md
```

## Rollback

Rollback is acceptable only when evidence remains readable after rollback.

Minimum rollback actions:

- Remove public staging traffic from the new backend.
- Restore frontend static files or Nginx config to the previous release.
- Set `QLANALYSER_STORAGE_BACKEND=local` for local fallback review, or point the staging service back to the previous verified OSS prefix.
- Export backup manifest before destructive cleanup.
- Re-run `python scripts\acceptance_backup_restore_drill.py --target local` after local fallback.

## Owner Decision Packet

If preflight remains blocked, report these exact missing categories:

- Latest changed Chinese copy has not passed DeepSeek official-direct review.
- Missing OSS env variables.
- Missing `QLANALYSER_ALIYUN_OSS_ALLOW_WRITE=1` for isolated staging.
- Missing lifecycle policy evidence path.
- Missing `oss2` package in staging runtime.
- Missing backup bucket/prefix.
- Missing public/API URL and CORS origin.
- Missing payment, registration, and messaging provider mode/callback evidence.

Do not broaden the release claim beyond local review while any of these are missing.
