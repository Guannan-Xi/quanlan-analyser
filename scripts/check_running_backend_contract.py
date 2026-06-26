import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


REQUIRED_ENDPOINTS = {
    "/api/eeg/files/{file_id}/data-preparation-plan": {"get", "post"},
    "/api/eeg/files/{file_id}/data-preparation-plans": {"get"},
    "/api/data-preparation/plans": {"get", "post"},
    "/api/lab/demo/dataset": {"get"},
    "/api/lab/demo/run/{module}": {"post"},
    "/api/lab/demo/run-all": {"post"},
    "/api/auth/verification-code": {"post"},
    "/api/auth/register": {"post"},
    "/api/auth/login": {"post"},
    "/api/billing/wallet": {"get"},
    "/api/billing/recharge": {"post"},
    "/api/billing/recharge/{order_id}/confirm": {"post"},
    "/api/invoices": {"get", "post"},
    "/api/inbox": {"get"},
    "/api/admin/overview": {"get"},
    "/api/admin/invoices": {"get"},
}


def fetch_json(url: str, timeout: float) -> tuple[int | None, object | None, str | None]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(raw), None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return exc.code, None, raw
    except Exception as exc:
        return None, None, str(exc)


def normalize_base_url(value: str) -> str:
    return value.rstrip("/")


def root_url(api_base_url: str) -> str:
    if api_base_url.endswith("/api"):
        return api_base_url[:-4]
    return api_base_url


def check_base_url(api_base_url: str, timeout: float) -> dict:
    api_base_url = normalize_base_url(api_base_url)
    health_url = f"{api_base_url}/health"
    openapi_url = f"{root_url(api_base_url)}/openapi.json"
    health_status, health_body, health_error = fetch_json(health_url, timeout)
    openapi_status, openapi_body, openapi_error = fetch_json(openapi_url, timeout)
    paths = openapi_body.get("paths", {}) if isinstance(openapi_body, dict) else {}
    endpoint_results = {}
    for path, required_methods in REQUIRED_ENDPOINTS.items():
        actual_methods = set(paths.get(path, {}).keys())
        endpoint_results[path] = {
            "required_methods": sorted(required_methods),
            "actual_methods": sorted(actual_methods),
            "ok": required_methods.issubset(actual_methods),
        }
    ok = (
        health_status == 200
        and openapi_status == 200
        and all(item["ok"] for item in endpoint_results.values())
    )
    return {
        "base_url": api_base_url,
        "health": {"url": health_url, "status": health_status, "body": health_body, "error": health_error},
        "openapi": {
            "url": openapi_url,
            "status": openapi_status,
            "path_count": len(paths),
            "error": openapi_error,
        },
        "endpoints": endpoint_results,
        "ok": ok,
    }


def write_evidence(evidence_dir: Path, payload: dict) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    path = evidence_dir / "running_backend_contract_check.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the running QLanalyser backend contract before browser acceptance.")
    parser.add_argument("--base-url", action="append", default=[], help="API base URL, for example http://127.0.0.1:8001/api. Can be repeated.")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()

    base_urls = args.base_url or ["http://127.0.0.1:8001/api"]
    checks = [check_base_url(base_url, args.timeout) for base_url in base_urls]
    payload = {
        "status": "passed" if all(item["ok"] for item in checks) else "failed",
        "checked_at_unix": time.time(),
        "checks": checks,
    }
    if args.evidence_dir:
        try:
            payload["evidence_path"] = str(write_evidence(args.evidence_dir, payload))
        except Exception as exc:
            payload["evidence_error"] = str(exc)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
