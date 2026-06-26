from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "work" / "release_evidence" / "07-mainline-integration"
EVIDENCE_PATH = EVIDENCE_DIR / "module_lab_acceptance_stack.json"
BACKEND_URL = "http://127.0.0.1:8001/api/health"
FRONTEND_ROOT_URL = "http://127.0.0.1:4174/module-lab.html"
FRONTEND_URL = "http://127.0.0.1:4174/module-lab.html?api=http://127.0.0.1:8001/api&acceptance=stack"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_evidence(payload: dict) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def health_json(url: str, timeout: float = 2.0) -> dict | None:
    try:
        with urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return None
            return json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError):
        return None


def fetch_text(url: str, timeout: float = 2.0) -> str | None:
    try:
        with urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return None
            return response.read().decode("utf-8", errors="replace")
    except (OSError, URLError):
        return None


def wait_for_health(url: str, seconds: int) -> dict | None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        payload = health_json(url)
        if payload:
            return payload
        time.sleep(1)
    return None


def wait_for_frontend(url: str, seconds: int) -> str | None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        text = fetch_text(url)
        if text and "module-lab.js" in text and "moduleLab" in text:
            return text
        time.sleep(1)
    return None


def run_command(command: list[str], env: dict[str, str] | None = None, timeout: int = 300) -> dict:
    started = now_iso()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    output = completed.stdout or ""
    return {
        "command": command,
        "started_at": started,
        "finished_at": now_iso(),
        "returncode": completed.returncode,
        "output_tail": output[-4000:],
        "passed": completed.returncode == 0,
    }


def start_backend(evidence: dict) -> subprocess.Popen | None:
    existing = health_json(BACKEND_URL)
    if existing:
        evidence["backend"] = {
            "status": "already_running",
            "url": BACKEND_URL,
            "health": existing,
            "owned_by_stack": False,
        }
        return None

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8001"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    health = wait_for_health(BACKEND_URL, 45)
    evidence["backend"] = {
        "status": "started" if health else "failed_to_start",
        "url": BACKEND_URL,
        "health": health,
        "owned_by_stack": True,
        "pid": proc.pid,
    }
    if not health:
        proc.terminate()
        return None
    return proc


def start_frontend(evidence: dict) -> subprocess.Popen | None:
    existing = fetch_text(FRONTEND_ROOT_URL)
    if existing and "module-lab.js" in existing and "moduleLab" in existing:
        evidence["frontend"] = {
            "status": "already_running",
            "url": FRONTEND_ROOT_URL,
            "serves_module_lab": True,
            "owned_by_stack": False,
        }
        return None

    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", "4174", "--bind", "127.0.0.1"],
        cwd=ROOT / "frontend",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    page_text = wait_for_frontend(FRONTEND_ROOT_URL, 20)
    evidence["frontend"] = {
        "status": "started" if page_text else "failed_to_start",
        "url": FRONTEND_ROOT_URL,
        "serves_module_lab": bool(page_text),
        "owned_by_stack": True,
        "pid": proc.pid,
    }
    if not page_text:
        proc.terminate()
        return None
    return proc


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the standardized Module Lab 8001/4174 acceptance stack.")
    parser.add_argument("--mode", choices=["visible", "grouped", "both"], default="visible")
    args = parser.parse_args()

    evidence: dict = {
        "status": "running",
        "started_at": now_iso(),
        "repo": str(ROOT),
        "backend_url": BACKEND_URL,
        "frontend_url": FRONTEND_URL,
        "mode": args.mode,
        "commands": [],
        "notes": [
            "This script does not modify router, Headroom, IPC, gateway, or production deployment configuration.",
            "It only stops the backend process that it starts itself.",
        ],
    }
    write_evidence(evidence)

    backend_proc = start_backend(evidence)
    frontend_proc = start_frontend(evidence)
    try:
        if not evidence.get("backend", {}).get("health"):
            evidence["status"] = "failed"
            evidence["finished_at"] = now_iso()
            write_evidence(evidence)
            return 1
        if not evidence.get("frontend", {}).get("serves_module_lab"):
            evidence["status"] = "failed"
            evidence["finished_at"] = now_iso()
            write_evidence(evidence)
            return 1

        env = os.environ.copy()
        env["QLANALYSER_FRONTEND_URL"] = FRONTEND_URL

        if args.mode in {"visible", "both"}:
            evidence["commands"].append(run_command(["node", "scripts/acceptance_module_lab_visible_fields.mjs"], env=env, timeout=180))
            write_evidence(evidence)
            evidence["commands"].append(run_command(["node", "scripts/acceptance_module_lab_layout_review.mjs"], env=env, timeout=180))
            write_evidence(evidence)

        if args.mode in {"grouped", "both"}:
            evidence["commands"].append(run_command([sys.executable, "-X", "utf8", "scripts/generate_module_lab_grouped_methods_edf.py"], timeout=180))
            write_evidence(evidence)
            evidence["commands"].append(run_command(["node", "scripts/acceptance_module_lab_grouped_methods_e2e.mjs"], env=env, timeout=480))
            write_evidence(evidence)

        evidence["status"] = "passed" if all(command["passed"] for command in evidence["commands"]) else "failed"
        evidence["finished_at"] = now_iso()
        write_evidence(evidence)
        return 0 if evidence["status"] == "passed" else 1
    finally:
        if frontend_proc and frontend_proc.poll() is None:
            frontend_proc.terminate()
            try:
                frontend_proc.wait(timeout=10)
                evidence["frontend"]["stopped_owned_process"] = True
            except subprocess.TimeoutExpired:
                frontend_proc.kill()
                evidence["frontend"]["stopped_owned_process"] = "killed_after_timeout"
            evidence["finished_at"] = now_iso()
            write_evidence(evidence)
        if backend_proc and backend_proc.poll() is None:
            backend_proc.terminate()
            try:
                backend_proc.wait(timeout=10)
                evidence["backend"]["stopped_owned_process"] = True
            except subprocess.TimeoutExpired:
                backend_proc.kill()
                evidence["backend"]["stopped_owned_process"] = "killed_after_timeout"
            evidence["finished_at"] = now_iso()
            write_evidence(evidence)


if __name__ == "__main__":
    raise SystemExit(main())
