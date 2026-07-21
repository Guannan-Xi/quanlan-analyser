from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QLANALYSER_ENV", "test")
os.environ.setdefault("QLANALYSER_PUBLIC_LAB_DEMO_ENABLED", "1")

from backend.main import app
from backend.services import lab_demo_service, state_store
from scripts.generate_teaching_oddball_case import build_raw


WORK = ROOT / "work" / "release_evidence" / "formal_task_rejects_teaching_input"
DATA = WORK / "data"
EVIDENCE_PATH = WORK / "acceptance_formal_task_rejects_teaching_input.json"
FORMAL_TEACHING_REJECTION_CODES = {
    "TEACHING_DATASET_NOT_FORMAL_INPUT",
    "FORMAL_TASK_REQUIRES_UPLOADED_AUTHORIZED_EEG",
}


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


def _post_task(client: TestClient, headers: dict[str, str], project_id: str, file_id: str, module: str, workflow: str, parameters: dict | None = None):
    return client.post(
        "/api/tasks",
        headers=headers,
        json={
            "project_id": project_id,
            "module_name": module,
            "workflow_id": workflow,
            "input_file_id": file_id,
            "parameters_json": parameters or {},
        },
    )


def _registry_ids(names: list[str]) -> dict[str, set[str]]:
    snapshot: dict[str, set[str]] = {}
    for name in names:
        snapshot[name] = {
            str(item.get("id"))
            for item in state_store._load_payload_unlocked(name)
            if isinstance(item, dict) and item.get("id")
        }
    return snapshot


def _registry_delta(before: dict[str, set[str]], after: dict[str, set[str]]) -> dict[str, list[str]]:
    return {name: sorted(after.get(name, set()) - ids) for name, ids in before.items()}


def _create_formal_uploaded_psd(client: TestClient, headers: dict[str, str]) -> tuple[dict, dict]:
    project_response = client.post(
        "/api/projects",
        headers=headers,
        json={"name": "Formal source gate acceptance", "research_type": "resting_state"},
    )
    project_response.raise_for_status()
    project = project_response.json()

    fixture = DATA / "formal_customer_oddball_raw.fif"
    _make_fixture(fixture)
    with fixture.open("rb") as handle:
        upload_response = client.post(
            f"/api/eeg/upload?project_id={project['id']}&upload_authorization_confirmed=true&upload_authorization_text=acceptance%20confirms%20authorized%20customer%20research%20EEG%20upload",
            headers=headers,
            files={"file": (fixture.name, handle, "application/octet-stream")},
        )
    upload_response.raise_for_status()
    eeg_file = upload_response.json()

    plan_response = client.post(
        "/api/data-preparation/plans",
        headers=headers,
        json={
            "project_id": project["id"],
            "input_file_id": eeg_file["id"],
            "status": "confirmed",
            "module_scope": ["qc", "psd", "band_power", "erp"],
            "title": "Formal acceptance preparation plan",
            "description": "Confirmed data-preparation plan for formal source gate acceptance.",
        },
    )
    plan_response.raise_for_status()
    plan = plan_response.json()

    task_response = _post_task(
        client,
        headers,
        project["id"],
        eeg_file["id"],
        "psd",
        "resting_psd",
        {
            "fmin": 1,
            "fmax": 35,
            "data_preparation_plan_id": plan["id"],
            "data_preparation_revision": plan["revision"],
        },
    )
    task_response.raise_for_status()
    return project, task_response.json()


def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True, exist_ok=True)
    lab_demo_service.ensure_demo_dataset()

    client = TestClient(app)
    headers = _login(client)
    failures: list[str] = []
    checks: dict[str, object] = {}

    projects_response = client.get("/api/projects", headers=headers)
    files_response = client.get("/api/eeg/files", headers=headers)
    checks["demo_project_hidden_by_default"] = "proj_demo_learning" not in {item["id"] for item in projects_response.json()}
    checks["demo_file_hidden_by_default"] = "eeg_demo_teaching_oddball" not in {item["id"] for item in files_response.json()}
    demo_file_detail = client.get(f"/api/eeg/files/{lab_demo_service.DEMO_FILE_ID}", headers=headers)
    checks["demo_file_direct_get_rejected"] = demo_file_detail.status_code in {403, 404}
    if not checks["demo_project_hidden_by_default"]:
        failures.append("demo_project_visible_in_customer_projects")
    if not checks["demo_file_hidden_by_default"]:
        failures.append("demo_file_visible_in_customer_eeg_files")
    if not checks["demo_file_direct_get_rejected"]:
        failures.append(f"demo_file_direct_get_not_rejected:{demo_file_detail.status_code}:{demo_file_detail.text[:500]}")

    formal_attempts = {
        "psd": ("psd", "resting_psd", {"fmin": 1, "fmax": 35}),
        "band_power": ("band_power", "band_power", {"fmin": 1, "fmax": 35}),
        "erp": ("erp", "erp_p300", {"event_id": {"standard": 1, "target": 2}, "event_id_confirmed": True}),
        "qc": ("qc", "metadata_qc", {}),
    }
    formal_registry_names = ["tasks", "artifacts", "billing_transactions", "usage_records", "reports"]
    before_formal_attempts = _registry_ids(formal_registry_names)
    task_rejections: dict[str, dict] = {}
    for label, (module, workflow, params) in formal_attempts.items():
        response = _post_task(client, headers, lab_demo_service.DEMO_PROJECT_ID, lab_demo_service.DEMO_FILE_ID, module, workflow, params)
        body = response.json()
        task_rejections[label] = {"status_code": response.status_code, "body": body}
        serialized_body = json.dumps(body, ensure_ascii=False)
        if response.status_code not in {403, 422} or not any(code in serialized_body for code in FORMAL_TEACHING_REJECTION_CODES):
            failures.append(f"formal_demo_task_not_rejected:{label}:{response.status_code}")
    after_formal_attempts = _registry_ids(formal_registry_names)
    formal_attempt_deltas = _registry_delta(before_formal_attempts, after_formal_attempts)
    if any(formal_attempt_deltas.values()):
        failures.append(f"formal_teaching_rejection_created_state:{formal_attempt_deltas}")

    demo_run = client.post("/api/lab/demo/run/psd/configured", json={"parameters_json": {"fmin": 1, "fmax": 35}})
    if demo_run.status_code != 200:
        failures.append(f"lab_demo_run_failed:{demo_run.status_code}:{demo_run.text[:500]}")
        demo_task = {}
    else:
        demo_task = demo_run.json()
        params = demo_task.get("parameters_json") or {}
        if params.get("lab_preview_run") is not True or params.get("delivery_scope") != "lab_preview_only":
            failures.append(f"lab_demo_task_not_marked_preview:{params}")
        client.post(f"/api/tasks/{demo_task['id']}/result-review", headers=headers)
        report_response = client.post(
            "/api/reports",
            headers=headers,
            json={"project_id": demo_task["project_id"], "task_id": demo_task["id"], "title": "Demo report should fail"},
        )
        if report_response.status_code != 422 or "LAB_PREVIEW_TASK_NOT_REPORTABLE" not in report_response.text:
            failures.append(f"lab_preview_report_not_rejected:{report_response.status_code}:{report_response.text[:500]}")

    forged_report_status = None
    forged_report_body = None
    if demo_task:
        from backend.models.analysis_task import AnalysisTaskRead

        stored_task = AnalysisTaskRead(**demo_task)
        forged_params = dict(stored_task.parameters_json or {})
        forged_params.pop("lab_preview_run", None)
        forged_params.pop("delivery_scope", None)
        stored_task.parameters_json = forged_params
        state_store.upsert_item("tasks", stored_task)
        forged = client.post(
            "/api/reports",
            headers=headers,
            json={"project_id": stored_task.project_id, "task_id": stored_task.id, "title": "Forged demo report should fail"},
        )
        forged_report_status = forged.status_code
        forged_report_body = forged.json()
        if forged.status_code != 422 or "REPORT_SOURCE_NOT_FORMAL_DELIVERY" not in json.dumps(forged_report_body, ensure_ascii=False):
            failures.append(f"forged_demo_report_not_rejected:{forged.status_code}:{forged.text[:500]}")

    formal_project, formal_task = _create_formal_uploaded_psd(client, headers)
    review_response = client.post(f"/api/tasks/{formal_task['id']}/result-review", headers=headers)
    if review_response.status_code != 200:
        failures.append(f"formal_result_review_failed:{review_response.status_code}:{review_response.text[:500]}")
    formal_report = client.post(
        "/api/reports",
        headers=headers,
        json={"project_id": formal_project["id"], "task_id": formal_task["id"], "title": "Formal uploaded EEG report"},
    )
    if formal_report.status_code != 200:
        failures.append(f"formal_uploaded_report_failed:{formal_report.status_code}:{formal_report.text[:500]}")

    payload = {
        "status": "passed" if not failures else "failed",
        "failures": failures,
        "checks": checks,
        "task_rejections": task_rejections,
        "formal_attempt_state_deltas": formal_attempt_deltas,
        "lab_demo_task_id": demo_task.get("id") if demo_task else None,
        "forged_demo_report_status": forged_report_status,
        "forged_demo_report_body": forged_report_body,
        "formal_task_id": formal_task.get("id"),
        "formal_report_status": formal_report.status_code,
        "formal_report_id": formal_report.json().get("id") if formal_report.status_code == 200 else None,
    }
    EVIDENCE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
