from __future__ import annotations

import json
import os
import re
import shutil
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QLANALYSER_ENV", "test")

from backend.main import app
from scripts.generate_teaching_oddball_case import build_raw


WORK = ROOT / "work" / "release_evidence" / "customer_api_no_internal_paths"
DATA = WORK / "data"
EVIDENCE_PATH = WORK / "acceptance_customer_api_no_internal_paths.json"

FORBIDDEN_KEYS = {
    "absolute_path",
    "artifact_root",
    "audit_json_path",
    "channels_tsv_path",
    "edf_path",
    "events_tsv_path",
    "html_path",
    "local_path",
    "package_path",
    "path",
    "repo_path",
    "root_dir",
    "source_integrity_path",
    "stored_path",
    "ui_evidence_path",
}

FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?i)\b[a-z]:[\\/]"),
    re.compile(r"(?i)(?:^|[\\/])users[\\/]"),
    re.compile(r"(?i)(?:^|[\\/])home[\\/]"),
    re.compile(r"(?i)(?:^|[\\/])tmp[\\/]"),
    re.compile(r"(?i)quanlan-analyser"),
    re.compile(r"(?i)\blocalhost\b"),
    re.compile(r"(?i)\b127\.0\.0\.1\b"),
    re.compile(r"(?i)traceback \(most recent call last\)"),
]


def require(condition: bool, message: str, detail: Any = None) -> None:
    if not condition:
        raise AssertionError(f"{message}: {detail}")


def _login(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": "demo.customer@quanlan.cn", "password": "demo123456"},
    )
    response.raise_for_status()
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _make_fixture(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = build_raw()
    raw.save(path, overwrite=True, verbose="ERROR")


def _json(response):
    response.raise_for_status()
    return response.json()


def _scan_public_payload(label: str, value: Any) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    def walk(item: Any, trail: str) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                key_text = str(key)
                child_trail = f"{trail}.{key_text}" if trail else key_text
                if key_text.lower() in FORBIDDEN_KEYS:
                    findings.append({"label": label, "path": child_trail, "reason": "forbidden_key"})
                walk(child, child_trail)
            return
        if isinstance(item, list):
            for index, child in enumerate(item):
                walk(child, f"{trail}[{index}]")
            return
        if isinstance(item, str):
            for pattern in FORBIDDEN_VALUE_PATTERNS:
                if pattern.search(item):
                    findings.append({"label": label, "path": trail, "reason": f"forbidden_value:{pattern.pattern}", "value": item[:240]})

    walk(value, "")
    return findings


def _assert_clean(label: str, payload: Any, findings: list[dict[str, str]]) -> None:
    findings.extend(_scan_public_payload(label, payload))


def _assert_download_clean(label: str, content: bytes, findings: list[dict[str, str]]) -> None:
    text = content.decode("utf-8", errors="ignore")
    if not text.strip():
        return
    for pattern in FORBIDDEN_VALUE_PATTERNS:
        if pattern.search(text):
            findings.append({"label": label, "path": "$download", "reason": f"forbidden_download_value:{pattern.pattern}", "value": text[:400]})


def _create_customer_source(client: TestClient, headers: dict[str, str]) -> tuple[dict, dict]:
    project = _json(
        client.post(
            "/api/projects",
            headers=headers,
            json={"name": "Customer API no internal paths", "research_type": "resting_state"},
        )
    )
    fixture = DATA / "customer_api_no_internal_paths_raw.fif"
    _make_fixture(fixture)
    with fixture.open("rb") as handle:
        eeg_file = _json(
            client.post(
                f"/api/eeg/upload?project_id={project['id']}"
                "&upload_authorization_confirmed=true"
                "&upload_authorization_text=customer%20api%20path%20privacy%20acceptance%20authorization",
                headers=headers,
                files={"file": (fixture.name, handle, "application/octet-stream")},
            )
        )
    return project, eeg_file


def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True, exist_ok=True)
    client = TestClient(app)
    headers = _login(client)
    findings: list[dict[str, str]] = []
    checks: dict[str, Any] = {}

    project, eeg_file = _create_customer_source(client, headers)
    _assert_clean("upload_eeg", eeg_file, findings)

    eeg_files = _json(client.get("/api/eeg/files", headers=headers))
    eeg_detail = _json(client.get(f"/api/eeg/files/{eeg_file['id']}", headers=headers))
    data_files = _json(client.get("/api/data/files", headers=headers))
    _assert_clean("list_eeg_files", eeg_files, findings)
    _assert_clean("get_eeg_file", eeg_detail, findings)
    _assert_clean("list_data_files", data_files, findings)

    plan_payload = {
        "project_id": project["id"],
        "input_file_id": eeg_file["id"],
        "status": "confirmed",
        "module_scope": ["qc", "psd", "band_power", "erp"],
        "title": "Customer API privacy data preparation plan",
        "source_file": {
            "original_filename": eeg_file["original_filename"],
            "edf_path": r"D:\Quanlan\Codes\Python\quanlan-analyser-official\data\private.edf",
            "events_tsv_path": r"D:\Quanlan\Codes\Python\quanlan-analyser-official\data\events.tsv",
        },
        "metadata_review": {
            "status": "accepted",
            "root_dir": r"D:\Quanlan\Codes\Python\quanlan-analyser-official",
        },
        "qc_json": {
            "pending_edits": {
                "local_path": r"D:\Quanlan\Codes\Python\quanlan-analyser-official\work\qc.json",
            }
        },
    }
    plan = _json(client.post("/api/data-preparation/plans", headers=headers, json=plan_payload))
    plans = _json(client.get(f"/api/data-preparation/plans?input_file_id={eeg_file['id']}", headers=headers))
    plan_detail = _json(client.get(f"/api/data-preparation/plans/{plan['id']}", headers=headers))
    current_plan = _json(client.get(f"/api/eeg/files/{eeg_file['id']}/data-preparation-plan", headers=headers))
    _assert_clean("create_data_preparation_plan", plan, findings)
    _assert_clean("list_data_preparation_plans", plans, findings)
    _assert_clean("get_data_preparation_plan", plan_detail, findings)
    _assert_clean("get_current_data_preparation_plan_for_file", current_plan, findings)

    task = _json(
        client.post(
            "/api/tasks",
            headers=headers,
            json={
                "project_id": project["id"],
                "module_name": "psd",
                "workflow_id": "resting_psd",
                "input_file_id": eeg_file["id"],
                "parameters_json": {
                    "fmin": 1,
                    "fmax": 35,
                    "data_preparation_plan_id": plan["id"],
                    "data_preparation_revision": plan["revision"],
                },
            },
        )
    )
    _assert_clean("create_task", task, findings)

    task_detail = _json(client.get(f"/api/tasks/{task['id']}", headers=headers))
    artifacts = _json(client.get(f"/api/tasks/{task['id']}/artifacts", headers=headers))
    _assert_clean("get_task", task_detail, findings)
    _assert_clean("list_task_artifacts", artifacts, findings)
    checks["artifact_download_urls"] = [artifact.get("download_url") for artifact in artifacts[:5]]
    require(artifacts and all("download_url" in artifact for artifact in artifacts), "artifacts expose download_url", artifacts[:3])

    download_targets = []
    for preferred in ("result", "parameters", "manifest", "log"):
        match = next(
            (
                artifact for artifact in artifacts
                if artifact.get("id") and preferred in f"{artifact.get('label', '')} {artifact.get('file_name', '')}".lower()
            ),
            None,
        )
        if match:
            download_targets.append(match)
    download_targets.extend([artifact for artifact in artifacts if artifact.get("id") and artifact not in download_targets][:2])
    artifact_download_statuses = {}
    for artifact in download_targets:
        artifact_download = client.get(f"/api/artifacts/{artifact['id']}/download", headers=headers)
        artifact_download_statuses[artifact["id"]] = artifact_download.status_code
        require(artifact_download.status_code == 200, "artifact download endpoint remains available", artifact_download.text[:200])
        _assert_download_clean(f"download_artifact:{artifact.get('label') or artifact.get('file_name')}", artifact_download.content, findings)

    batch_download = client.post(f"/api/tasks/{task['id']}/artifacts/batch", headers=headers)
    require(batch_download.status_code == 200, "task batch artifact download remains available", batch_download.text[:200])
    with zipfile.ZipFile(BytesIO(batch_download.content)) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            suffix = Path(entry.filename).suffix.lower()
            if suffix in {".json", ".txt", ".log", ".csv", ".tsv", ".md", ".html", ".xml", ".yaml", ".yml"}:
                _assert_download_clean(f"batch_artifact:{entry.filename}", archive.read(entry), findings)

    review = _json(client.post(f"/api/tasks/{task['id']}/result-review", headers=headers))
    _assert_clean("result_review", review, findings)

    report = _json(
        client.post(
            "/api/reports",
            headers=headers,
            json={"project_id": project["id"], "task_id": task["id"], "title": "Customer API privacy report"},
        )
    )
    report_detail = _json(client.get(f"/api/reports/{report['id']}", headers=headers))
    _assert_clean("create_report", report, findings)
    _assert_clean("get_report", report_detail, findings)
    require("package_download_url" in report_detail, "report exposes package_download_url", report_detail)

    package_download = client.get(f"/api/reports/{report['id']}/package", headers=headers)
    require(package_download.status_code == 200, "report package download endpoint remains available", package_download.text[:200])
    with zipfile.ZipFile(BytesIO(package_download.content)) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            suffix = Path(entry.filename).suffix.lower()
            if suffix in {".json", ".txt", ".log", ".csv", ".tsv", ".md", ".html", ".xml", ".yaml", ".yml"}:
                _assert_download_clean(f"report_package:{entry.filename}", archive.read(entry), findings)

    payload = {
        "status": "passed" if not findings else "failed",
        "findings": findings,
        "checks": {
            **checks,
            "project_id": project["id"],
            "input_file_id": eeg_file["id"],
            "plan_id": plan["id"],
            "task_id": task["id"],
            "report_id": report["id"],
            "artifact_count": len(artifacts),
            "artifact_download_statuses": artifact_download_statuses,
            "batch_download_status": batch_download.status_code,
            "report_package_download_status": package_download.status_code,
        },
    }
    EVIDENCE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
