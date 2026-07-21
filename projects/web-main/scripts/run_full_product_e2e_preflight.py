from __future__ import annotations

import json
import py_compile
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "work" / "release_evidence" / "07-full-product-e2e-pdca" / "03_preflight"
EVIDENCE_PATH = EVIDENCE_DIR / "preflight.json"

DOCS = [
    "docs/product/qlanalyser_full_product_e2e_requirements_20260626.md",
    "docs/product/qlanalyser_full_product_e2e_design_20260626.md",
    "docs/product/qlanalyser_full_product_e2e_test_plan_20260626.md",
    "docs/product/qlanalyser_full_product_e2e_execution_packet_20260626.md",
    "work/release_evidence/07-full-product-e2e-pdca/09_deepseek/researcher_logic_review_ascii.md",
    "work/release_evidence/07-full-product-e2e-pdca/09_deepseek/researcher_logic_review_adoption.json",
]

NODE_CHECKS = [
    "frontend/app.js",
    "frontend/module-lab.js",
    "frontend/qc-lab.js",
    "frontend/research-modules.js",
    "scripts/acceptance_edf_upload_to_results_ui_only.mjs",
    "scripts/acceptance_full_product_ui_scroll_review.mjs",
    "scripts/acceptance_main_workbench_direct_method_clickthrough_e2e.mjs",
    "scripts/acceptance_module_lab_visible_fields.mjs",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_command(name: str, command: list[str], timeout: int = 120) -> dict[str, Any]:
    started = time.time()
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        status = "passed" if result.returncode == 0 else "failed"
        return {
            "name": name,
            "command": command,
            "status": status,
            "returncode": result.returncode,
            "duration_sec": round(time.time() - started, 3),
            "stdout_tail": result.stdout[-4000:],
            "stderr_tail": result.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "name": name,
            "command": command,
            "status": "timeout",
            "returncode": None,
            "duration_sec": round(time.time() - started, 3),
            "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
        }


def py_compile_check() -> dict[str, Any]:
    patterns = [
        "backend/main.py",
        "backend/api/*.py",
        "backend/services/task_service.py",
        "backend/services/data_preparation_service.py",
        "backend/models/data_preparation.py",
        "eeg_core/analysis/*.py",
        "eeg_core/preprocess/*.py",
        "scripts/build_full_product_e2e_pdca_packet.py",
        "scripts/run_full_product_method_source_comparison.py",
        "scripts/build_full_product_e2e_acceptance_packet.py",
        "scripts/run_full_product_e2e_preflight.py",
    ]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(ROOT.glob(pattern))
    files = sorted(set(files))
    failures = []
    for path in files:
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:  # noqa: BLE001
            failures.append({"path": str(path.relative_to(ROOT)), "error": str(exc)})
    return {
        "name": "python_py_compile",
        "status": "passed" if not failures else "failed",
        "file_count": len(files),
        "failures": failures,
    }


def http_check(url: str, timeout: int = 5) -> dict[str, Any]:
    started = time.time()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(200)
            return {
                "url": url,
                "status": "passed",
                "status_code": response.status,
                "duration_sec": round(time.time() - started, 3),
                "body_sample": body.decode("utf-8", errors="replace"),
            }
    except urllib.error.HTTPError as exc:
        return {
            "url": url,
            "status": "failed",
            "status_code": exc.code,
            "duration_sec": round(time.time() - started, 3),
            "error": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "url": url,
            "status": "failed",
            "status_code": None,
            "duration_sec": round(time.time() - started, 3),
            "error": str(exc),
        }


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, Any]] = []
    checks.append(
        run_command(
            "mojibake_docs_and_deepseek",
            [sys.executable, "-X", "utf8", "scripts/check_no_mojibake.py", *DOCS],
            timeout=60,
        )
    )
    checks.append(py_compile_check())
    for target in NODE_CHECKS:
        if (ROOT / target).exists():
            checks.append(run_command(f"node_check_{target}", ["node", "--check", target], timeout=60))
        else:
            checks.append({"name": f"node_check_{target}", "status": "skipped_missing", "path": target})
    checks.append(
        run_command(
            "deepseek_route_check",
            ["python", "C:/Users/XGN/.codex/scripts/model-consultant.py", "--role", "polish", "--route-check"],
            timeout=60,
        )
    )
    service_checks = [
        http_check("http://127.0.0.1:8001/api/health"),
        http_check("http://127.0.0.1:4174/"),
    ]
    status = "passed" if all(item.get("status") in {"passed", "skipped_missing"} for item in checks) and all(item.get("status") == "passed" for item in service_checks) else "failed"
    evidence = {
        "status": status,
        "generated_at": now_iso(),
        "checks": checks,
        "service_checks": service_checks,
    }
    EVIDENCE_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "evidence": str(EVIDENCE_PATH), "checks": len(checks), "service_checks": service_checks}, ensure_ascii=False, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
