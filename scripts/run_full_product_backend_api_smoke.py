from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main import app  # noqa: E402

EVIDENCE_DIR = ROOT / "work" / "release_evidence" / "07-full-product-e2e-pdca" / "04_backend_api"
EVIDENCE_PATH = EVIDENCE_DIR / "backend_api_smoke.json"
RUNNING_CONTRACT_PATH = EVIDENCE_DIR / "running_backend_contract_check.json"

EXPECTED_RUN_ALL_MODULES = {"qc", "psd", "erp", "reference_csd", "connectivity"}
REQUIRED_CONTRACT_PATHS = {
    "/api/health": {"get"},
    "/api/health/readiness": {"get"},
    "/api/auth/login": {"post"},
    "/api/admin/overview": {"get"},
    "/api/admin/state": {"get"},
    "/api/admin/accounts": {"get"},
    "/api/admin/tasks": {"get"},
    "/api/projects": {"get", "post"},
    "/api/billing/wallet": {"get"},
    "/api/inbox": {"get"},
    "/api/lab/demo/dataset": {"get"},
    "/api/lab/demo/run-all": {"post"},
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except (ValueError, OSError):
        return str(path).replace("\\", "/")


def compact_body(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in {"token", "authorization"}:
                out[key] = "<redacted>"
            elif isinstance(item, (dict, list)):
                out[key] = compact_body(item)
            else:
                out[key] = item
        return out
    if isinstance(value, list):
        return [compact_body(item) for item in value[:5]]
    return value


def call(
    client: TestClient,
    method: str,
    path: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    expected_status: int | set[int] = 200,
    required_keys: set[str] | None = None,
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    started = time.time()
    response = client.request(method, path, headers=headers, json=payload)
    duration_sec = round(time.time() - started, 3)
    try:
        body: Any = response.json()
    except Exception:
        body = response.text[:1000]

    expected = {expected_status} if isinstance(expected_status, int) else expected_status
    missing_keys: list[str] = []
    if required_keys:
        if not isinstance(body, dict):
            missing_keys.append("response is not a JSON object")
        else:
            missing_keys.extend(sorted(key for key in required_keys if key not in body))

    return {
        "name": f"{method.upper()} {path}",
        "method": method.upper(),
        "path": path,
        "expected_status": sorted(expected),
        "status_code": response.status_code,
        "duration_sec": duration_sec,
        "required_keys": sorted(required_keys or []),
        "missing_keys": missing_keys,
        "status": "passed" if response.status_code in expected and not missing_keys else "failed",
        "body_sample": compact_body(body),
    }


def openapi_contract(client: TestClient) -> dict[str, Any]:
    response = client.get("/openapi.json")
    body = response.json() if response.status_code == 200 else {}
    paths = body.get("paths", {}) if isinstance(body, dict) else {}
    endpoint_results = {}
    for route, required_methods in REQUIRED_CONTRACT_PATHS.items():
        actual_methods = set(paths.get(route, {}).keys())
        endpoint_results[route] = {
            "required_methods": sorted(required_methods),
            "actual_methods": sorted(actual_methods),
            "ok": required_methods.issubset(actual_methods),
        }
    return {
        "status": "passed" if response.status_code == 200 and all(item["ok"] for item in endpoint_results.values()) else "failed",
        "openapi_status": response.status_code,
        "path_count": len(paths),
        "endpoints": endpoint_results,
    }


def maybe_running_contract() -> dict[str, Any]:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-X",
        "utf8",
        "scripts/check_running_backend_contract.py",
        "--base-url",
        "http://127.0.0.1:8001/api",
        "--evidence-dir",
        str(EVIDENCE_DIR),
    ]
    started = time.time()
    try:
        proc = subprocess.run(command, cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=20)
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "skipped_or_failed",
            "command": " ".join(command),
            "duration_sec": round(time.time() - started, 3),
            "returncode": None,
            "evidence": None,
            "stdout_tail": (exc.stdout or "")[-1200:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-1200:] if isinstance(exc.stderr, str) else "",
            "note": "Running 8001 contract check timed out; in-process backend smoke remains authoritative for this addendum.",
        }
    status = "passed" if proc.returncode == 0 and RUNNING_CONTRACT_PATH.exists() else "skipped_or_failed"
    return {
        "status": status,
        "command": " ".join(command),
        "duration_sec": round(time.time() - started, 3),
        "returncode": proc.returncode,
        "evidence": rel(RUNNING_CONTRACT_PATH) if RUNNING_CONTRACT_PATH.exists() else None,
        "stdout_tail": proc.stdout[-1200:],
        "stderr_tail": proc.stderr[-1200:],
        "note": "This supplements in-process backend smoke when the local 8001 service is reachable.",
    }


def token_from_login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    if response.status_code != 200:
        return ""
    body = response.json()
    return str(body.get("token", ""))


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    running_contract = maybe_running_contract()

    smoke_checks: list[dict[str, Any]] = []
    with TestClient(app) as client:
        contract = openapi_contract(client)
        smoke_checks.append(call(client, "get", "/api/health", required_keys={"status", "scope", "version"}))
        smoke_checks.append(call(client, "get", "/api/health/readiness", required_keys={"status"}))
        smoke_checks.append(call(client, "get", "/api/admin/overview", expected_status=401))

        customer_login = call(
            client,
            "post",
            "/api/auth/login",
            payload={"email": "demo.customer@quanlan.cn", "password": "demo123456"},
            required_keys={"token", "account", "expires_at"},
        )
        admin_login = call(
            client,
            "post",
            "/api/auth/login",
            payload={"email": "ops@quanlan.cn", "password": "ops-demo-2026"},
            required_keys={"token", "account", "expires_at"},
        )
        smoke_checks.extend([customer_login, admin_login])

        customer_token = token_from_login(client, "demo.customer@quanlan.cn", "demo123456")
        admin_token = token_from_login(client, "ops@quanlan.cn", "ops-demo-2026")

        smoke_checks.extend(
            [
                call(client, "get", "/api/projects"),
                call(client, "get", "/api/billing/wallet", token=customer_token, required_keys={"account", "balance_credits", "payment_provider_mode"}),
                call(client, "get", "/api/inbox", token=customer_token),
                call(client, "get", "/api/admin/overview", token=admin_token, required_keys={"accounts", "tasks", "failed_tasks"}),
                call(client, "get", "/api/admin/state", token=admin_token),
                call(client, "get", "/api/admin/accounts", token=admin_token),
                call(client, "get", "/api/admin/tasks", token=admin_token),
                call(client, "get", "/api/admin/billing/recharge-orders", token=admin_token),
                call(client, "get", "/api/admin/billing/transactions", token=admin_token),
                call(client, "get", "/api/lab/demo/dataset", required_keys={"project", "file"}),
                call(client, "post", "/api/lab/demo/run-all", required_keys={"dataset", "tasks"}),
            ]
        )

    run_all = next((item for item in smoke_checks if item["path"] == "/api/lab/demo/run-all"), {})
    body_sample = run_all.get("body_sample")
    tasks = body_sample.get("tasks", {}) if isinstance(body_sample, dict) else {}
    run_all_modules = set(tasks.keys()) if isinstance(tasks, dict) else set()
    run_all_missing = sorted(EXPECTED_RUN_ALL_MODULES - run_all_modules)

    blockers: list[str] = []
    if contract["status"] != "passed":
        blockers.append("openapi contract missing required backend/admin paths")
    failed_checks = [item["name"] for item in smoke_checks if item["status"] != "passed"]
    if failed_checks:
        blockers.extend(f"backend smoke failed: {name}" for name in failed_checks)
    if run_all_missing:
        blockers.append(f"demo run-all missing modules: {', '.join(run_all_missing)}")

    payload = {
        "status": "passed" if not blockers else "failed",
        "generated_at": now_iso(),
        "pdca": {
            "plan": "Standalone backend/admin smoke for full-product E2E acceptance addendum FR-10.",
            "do": "FastAPI TestClient authenticated smoke plus optional running 8001 contract check.",
            "check": "Health/readiness, OpenAPI paths, customer/admin login, role-gated admin endpoints, customer resources, synthetic demo dataset/run-all.",
            "act": "Accepted if no blockers; otherwise fix route/auth/backend contract before final acceptance.",
        },
        "running_contract": running_contract,
        "in_process_contract": contract,
        "smoke_checks": smoke_checks,
        "run_all_modules": sorted(run_all_modules),
        "expected_run_all_modules": sorted(EXPECTED_RUN_ALL_MODULES),
        "blockers": blockers,
        "boundary": "Uses seeded demo accounts and synthetic/demo data only; no real customer data or clinical validity claim.",
    }
    EVIDENCE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "evidence": rel(EVIDENCE_PATH), "checks": len(smoke_checks), "blockers": blockers}, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
