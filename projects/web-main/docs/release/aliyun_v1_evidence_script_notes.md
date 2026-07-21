# Aliyun V1 Evidence Script Notes

Updated: 2026-06-20

## Added scripts

- `scripts/acceptance_aliyun_storage_contract.py`
  - Supports `--target local|aliyun`, `--evidence-dir`, and `--strict`.
  - Local target exercises the current `backend.services.object_storage_service` boundary: put stream, exists, stat/hash, readable bytes, signed download contract, tier copy, and delete/mark-deleted.
  - The service has a local default backend and an optional Alibaba Cloud OSS backend behind `QLANALYSER_STORAGE_BACKEND=oss`.
  - Aliyun target is intentionally safe: without explicit staging prerequisites it records placeholder evidence; with `--strict`, missing OSS SDK, endpoint, bucket, access key, explicit allow-write, or lifecycle policy evidence fails the run.

- `scripts/acceptance_backup_restore_drill.py`
  - Supports `--target local|aliyun`, `--evidence-dir`, and `--strict`.
  - Local target seeds isolated JSON state plus object files, exports a state/object manifest, restores into clean roots, compares SHA-256 manifests, and validates restored registries through existing models.
  - Local target now verifies `backend.services.backup_service` exposes the manifest export/restore API.
  - Aliyun target records placeholder requirements without writing to cloud resources. `--strict` fails when hard Aliyun prerequisites are missing, including target placeholders.

## Validation commands

Run from the repository root:

```powershell
python scripts\acceptance_aliyun_storage_contract.py --target local --evidence-dir work\acceptance\aliyun-evidence
python scripts\acceptance_aliyun_storage_contract.py --target aliyun --evidence-dir work\acceptance\aliyun-evidence
python scripts\acceptance_aliyun_storage_contract.py --target aliyun --strict --evidence-dir work\acceptance\aliyun-evidence
python scripts\acceptance_backup_restore_drill.py --target local --evidence-dir work\acceptance\aliyun-evidence
python scripts\acceptance_backup_restore_drill.py --target aliyun --evidence-dir work\acceptance\aliyun-evidence
```

Strict Aliyun object-storage validation should be run only against isolated staging OSS resources:

```powershell
$env:QLANALYSER_STORAGE_BACKEND = "oss"
$env:QLANALYSER_ALIYUN_OSS_ENDPOINT = "<oss-endpoint>"
$env:QLANALYSER_ALIYUN_OSS_BUCKET = "<staging-oss-bucket>"
$env:QLANALYSER_ALIYUN_OSS_ACCESS_KEY_ID = "<access-key-id>"
$env:QLANALYSER_ALIYUN_OSS_ACCESS_KEY_SECRET = "<access-key-secret>"
$env:QLANALYSER_ALIYUN_OSS_ALLOW_WRITE = "1"
$env:QLANALYSER_ALIYUN_OSS_LIFECYCLE_POLICY_EVIDENCE = "<exported-lifecycle-policy-json>"
python scripts\acceptance_aliyun_storage_contract.py --target aliyun --strict --evidence-dir work\acceptance\aliyun-evidence
```

Strict Aliyun backup target validation should be run only after non-secret target placeholders are configured:

```powershell
$env:QLANALYSER_ALIYUN_OSS_BUCKET = "<oss-bucket>"
$env:QLANALYSER_ALIYUN_BACKUP_BUCKET = "<backup-bucket>"
$env:QLANALYSER_ALIYUN_BACKUP_PREFIX = "<backup-prefix>"
python scripts\acceptance_backup_restore_drill.py --target aliyun --strict --evidence-dir work\acceptance\aliyun-evidence
```

## Known TODOs

- Capture staging OSS lifecycle policy evidence for warm/cold retention.
- Install and verify optional `oss2` dependency in the Aliyun runtime image before enabling `QLANALYSER_STORAGE_BACKEND=oss`.
- Run `scripts\acceptance_aliyun_storage_contract.py --target aliyun --strict` against an isolated staging bucket; do not run strict cloud writes against production data.
- Run `backend.services.backup_service` against a staging object/state layout during deployment rehearsal; local manifest export/restore now passes with 0 todos.
- Run the strict backup drill only against an isolated staging bucket, never a production bucket.
