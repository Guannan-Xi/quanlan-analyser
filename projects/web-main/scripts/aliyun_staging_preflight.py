from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "aliyun_staging_preflight.json"
STAGING_ENV_TEMPLATE = ROOT / "deploy" / "aliyun" / "qlanalyser-v01-staging.env.example"

REQUIRED_FILES = [
    "backend/main.py",
    "frontend/Dockerfile",
    "frontend/nginx.conf",
    "deploy/aliyun/nginx.single-origin.conf",
    "deploy/aliyun/qlanalyser-v01-staging.env.example",
    "scripts/render_aliyun_nginx_config.py",
    "scripts/run_v01_acceptance.ps1",
    "scripts/acceptance_aliyun_storage_contract.py",
    "scripts/acceptance_backup_restore_drill.py",
    "work/release_evidence/20260620-v01-acceptance/evidence_manifest.json",
    "work/release_evidence/20260620-deepseek-copy-gate/deepseek_copy_gate_after_report_download_artifact_fix.json",
    "work/release_evidence/20260620-deepseek-copy-gate/deepseek_copy_gate_after_v1_public_status_alignment_skipped.json",
]

OSS_ENV = [
    "QLANALYSER_ALIYUN_OSS_ENDPOINT",
    "QLANALYSER_ALIYUN_OSS_BUCKET",
    "QLANALYSER_ALIYUN_OSS_ACCESS_KEY_ID",
    "QLANALYSER_ALIYUN_OSS_ACCESS_KEY_SECRET",
]

BACKUP_ENV = [
    "QLANALYSER_ALIYUN_BACKUP_BUCKET",
    "QLANALYSER_ALIYUN_BACKUP_PREFIX",
]

DEPLOY_ENV = [
    "QLANALYSER_PUBLIC_BASE_URL",
    "QLANALYSER_API_BASE_URL",
    "QLANALYSER_CORS_ORIGINS",
]

PROVIDER_ENV = [
    "QLANALYSER_PAYMENT_PROVIDER_MODE",
    "QLANALYSER_ALIPAY_CALLBACK_EVIDENCE",
    "QLANALYSER_WECHAT_PAY_CALLBACK_EVIDENCE",
    "QLANALYSER_EMAIL_PROVIDER_MODE",
    "QLANALYSER_SMS_PROVIDER_MODE",
    "QLANALYSER_WECHAT_AUTH_PROVIDER_MODE",
    "QLANALYSER_MESSAGE_PROVIDER_EVIDENCE",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def env_status(name: str) -> dict[str, Any]:
    value = os.getenv(name, "")
    return {"name": name, "set": bool(value), "length": len(value) if value else 0}


def add_check(checks: list[dict[str, Any]], name: str, status: str, detail: str, **extra: Any) -> None:
    checks.append({"name": name, "status": status, "detail": detail, **extra})


def summarize(checks: list[dict[str, Any]]) -> str:
    if any(check["status"] == "fail" for check in checks):
        return "blocked_missing_prerequisites"
    if any(check["status"] == "todo" for check in checks):
        return "blocked_missing_prerequisites"
    return "ready_for_strict_staging"


def is_valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether QLanalyser Aliyun staging smoke prerequisites are ready.")
    parser.add_argument("--evidence-path", default=str(DEFAULT_EVIDENCE), help="UTF-8 JSON output path.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when staging prerequisites are missing.")
    args = parser.parse_args()

    checks: list[dict[str, Any]] = []
    details: dict[str, Any] = {}

    missing_files = []
    for relative in REQUIRED_FILES:
        path = ROOT / relative
        if not path.exists():
            missing_files.append(relative)
    add_check(
        checks,
        "required_files",
        "pass" if not missing_files else "fail",
        "Required deploy/smoke files are present." if not missing_files else "Missing required deploy/smoke files.",
        missing=missing_files,
    )

    manifest_path = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "evidence_manifest.json"
    manifest = load_json(manifest_path)
    manifest_ok = bool(
        manifest
        and manifest.get("full_runner_result") == "V01 acceptance suite passed."
        and (manifest.get("latest_full_acceptance") or {}).get("result") == "V01 acceptance suite passed."
    )
    add_check(
        checks,
        "local_v01_acceptance_manifest",
        "pass" if manifest_ok else "fail",
        "Latest local V01 acceptance pass is recorded." if manifest_ok else "Latest local V01 acceptance pass is not recorded.",
        path=str(manifest_path),
    )

    deepseek_path = ROOT / "work" / "release_evidence" / "20260620-deepseek-copy-gate" / "deepseek_copy_gate_after_report_download_artifact_fix.json"
    latest_deepseek_path = ROOT / "work" / "release_evidence" / "20260620-deepseek-copy-gate" / "deepseek_copy_gate_after_v1_public_status_alignment_skipped.json"
    deepseek = load_json(deepseek_path)
    latest_deepseek = load_json(latest_deepseek_path)
    historical_deepseek_ok = bool(deepseek and deepseek.get("status") == "pass" and not deepseek.get("required_changes"))
    latest_deepseek_ok = bool(latest_deepseek and latest_deepseek.get("status") == "pass" and not latest_deepseek.get("required_changes"))
    latest_deepseek_skipped = bool(latest_deepseek and latest_deepseek.get("status") == "skipped")
    deepseek_status = "pass" if latest_deepseek_ok else ("todo" if latest_deepseek_skipped and historical_deepseek_ok else "fail")
    add_check(
        checks,
        "deepseek_copy_gate",
        deepseek_status,
        "Latest DeepSeek Chinese copy gate passed." if latest_deepseek_ok else (
            "Latest changed copy has not passed DeepSeek official direct review; historical copy gate passed."
            if latest_deepseek_skipped and historical_deepseek_ok
            else "DeepSeek Chinese copy gate is not pass."
        ),
        historical_path=str(deepseek_path),
        latest_path=str(latest_deepseek_path),
        latest_status=(latest_deepseek or {}).get("status", "<missing>"),
    )

    oss_env = [env_status(name) for name in OSS_ENV]
    missing_oss = [item["name"] for item in oss_env if not item["set"]]
    add_check(
        checks,
        "oss_required_env",
        "pass" if not missing_oss else "todo",
        "Required OSS environment variables are set." if not missing_oss else "OSS environment variables are missing.",
        missing=missing_oss,
        expected=OSS_ENV,
        template=str(STAGING_ENV_TEMPLATE),
    )

    storage_backend = os.getenv("QLANALYSER_STORAGE_BACKEND", "")
    add_check(
        checks,
        "oss_storage_backend",
        "pass" if storage_backend.lower() in {"oss", "aliyun", "aliyun-oss"} else "todo",
        "OSS storage backend is selected." if storage_backend.lower() in {"oss", "aliyun", "aliyun-oss"} else "Set QLANALYSER_STORAGE_BACKEND=oss for cloud smoke.",
        storage_backend=storage_backend or "<unset>",
        expected="oss",
    )

    allow_write = os.getenv("QLANALYSER_ALIYUN_OSS_ALLOW_WRITE") == "1"
    add_check(
        checks,
        "oss_allow_write",
        "pass" if allow_write else "todo",
        "OSS staging writes are explicitly allowed." if allow_write else "Set QLANALYSER_ALIYUN_OSS_ALLOW_WRITE=1 only for isolated staging smoke.",
        expected="1",
    )

    lifecycle_path_text = os.getenv("QLANALYSER_ALIYUN_OSS_LIFECYCLE_POLICY_EVIDENCE", "").strip()
    lifecycle_path = Path(lifecycle_path_text) if lifecycle_path_text else None
    lifecycle_ok = bool(lifecycle_path and lifecycle_path.exists() and lifecycle_path.is_file())
    add_check(
        checks,
        "oss_lifecycle_evidence",
        "pass" if lifecycle_ok else "todo",
        "OSS lifecycle policy evidence file exists." if lifecycle_ok else "Provide QLANALYSER_ALIYUN_OSS_LIFECYCLE_POLICY_EVIDENCE pointing to exported lifecycle policy evidence.",
        path=lifecycle_path_text or "<unset>",
        expected="path to exported OSS lifecycle policy JSON",
    )

    oss2_ok = importlib.util.find_spec("oss2") is not None
    add_check(
        checks,
        "oss2_dependency",
        "pass" if oss2_ok else "todo",
        "Python oss2 package is importable." if oss2_ok else "Install requirements.txt in the staging runtime before strict OSS smoke; requirements.txt includes oss2.",
        expected="python -m pip install -r requirements.txt",
    )

    backup_env = [env_status(name) for name in BACKUP_ENV]
    missing_backup = [item["name"] for item in backup_env if not item["set"]]
    add_check(
        checks,
        "backup_required_env",
        "pass" if not missing_backup else "todo",
        "Backup bucket environment variables are set." if not missing_backup else "Backup bucket environment variables are missing.",
        missing=missing_backup,
        expected=BACKUP_ENV,
        template=str(STAGING_ENV_TEMPLATE),
    )

    deploy_env = [env_status(name) for name in DEPLOY_ENV]
    missing_deploy = [item["name"] for item in deploy_env if not item["set"]]
    public_url = os.getenv("QLANALYSER_PUBLIC_BASE_URL", "")
    api_url = os.getenv("QLANALYSER_API_BASE_URL", "")
    url_ok = (not public_url or is_valid_http_url(public_url)) and (not api_url or is_valid_http_url(api_url))
    add_check(
        checks,
        "deploy_origin_env",
        "pass" if not missing_deploy and url_ok else "todo",
        "Deployment URL/CORS environment variables are set." if not missing_deploy and url_ok else "Set public/API URL and CORS origins for the exact staging origin.",
        missing=missing_deploy,
        public_url_set=bool(public_url),
        api_url_set=bool(api_url),
        url_shape_ok=url_ok,
        expected=DEPLOY_ENV,
        template=str(STAGING_ENV_TEMPLATE),
    )

    provider_env = [env_status(name) for name in PROVIDER_ENV]
    missing_provider = [item["name"] for item in provider_env if not item["set"]]
    add_check(
        checks,
        "provider_boundary_env",
        "pass" if not missing_provider else "todo",
        "Payment, registration, and messaging provider boundary evidence is set." if not missing_provider else "Provider mode/callback evidence variables are missing; keep third-party integrations in sandbox/local-review claim only.",
        missing=missing_provider,
        expected=PROVIDER_ENV,
        template=str(STAGING_ENV_TEMPLATE),
    )

    status = summarize(checks)
    next_commands = [
        "python scripts/aliyun_staging_preflight.py --strict",
        "python scripts/acceptance_aliyun_storage_contract.py --target aliyun --strict",
        "python scripts/acceptance_backup_restore_drill.py --target aliyun --strict",
        "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\run_v01_acceptance.ps1",
    ]
    details["env"] = {
        "staging_env_template": str(STAGING_ENV_TEMPLATE),
        "oss": oss_env,
        "backup": backup_env,
        "deploy": deploy_env,
        "provider": provider_env,
        "storage_backend": storage_backend or "<unset>",
        "allow_write": allow_write,
        "lifecycle_evidence_path_set": bool(lifecycle_path_text),
    }
    details["commands_after_preflight_passes"] = next_commands[1:]
    payload = {
        "status": status,
        "generated_at": utc_now(),
        "script": str(Path(__file__).resolve()),
        "strict": bool(args.strict),
        "checks": checks,
        "details": details,
        "next_commands": next_commands,
        "safe_claim": "Aliyun staging prerequisites are ready." if status == "ready_for_strict_staging" else "Aliyun staging prerequisites are not complete; keep release claim local-review only.",
    }
    evidence_path = Path(args.evidence_path)
    write_json(evidence_path, payload)
    print(json.dumps({
        "status": status,
        "evidence_path": str(evidence_path),
        "passed": len([check for check in checks if check["status"] == "pass"]),
        "todos": len([check for check in checks if check["status"] == "todo"]),
        "failed": len([check for check in checks if check["status"] == "fail"]),
        "safe_claim": payload["safe_claim"],
    }, ensure_ascii=False, indent=2))
    return 1 if args.strict and status != "ready_for_strict_staging" else 0


if __name__ == "__main__":
    raise SystemExit(main())
