import json
from importlib import reload
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.main import app
from backend.services import report_service, state_store, storage_service, task_service
from scripts.acceptance_v01_full import build_fif, run_task, upload_file


def assert_true(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"{name}: {detail}")


def main() -> None:
    client = TestClient(app)
    state_store.STATE_ROOT.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="qlanalyser-persist-") as temp_dir:
        eeg_path = Path(temp_dir) / "persistent-events.fif"
        build_fif(eeg_path, with_events=True)

        project = client.post(
            "/api/projects",
            json={"name": "Persistence Gate", "description": "restart registry check", "research_type": "erp"},
        ).json()
        subject = client.post(
            f"/api/projects/{project['id']}/subjects",
            json={"subject_code": "sub-persist", "group_name": "test"},
        ).json()
        eeg_file = upload_file(client, project["id"], eeg_path)
        patched = client.patch(f"/api/data/files/{eeg_file['id']}?label=persistent-label").json()
        assert_true("patch label", patched.get("label") == "persistent-label", json.dumps(patched))
        task, artifacts = run_task(client, project["id"], eeg_file["id"], "qc", "metadata_qc", {})
        report = client.post(
            "/api/reports",
            json={"project_id": project["id"], "task_id": task["id"], "title": "Persistent report"},
        ).json()

    expected_files = ["projects", "subjects", "eeg_files", "tasks", "artifacts", "reports"]
    for name in expected_files:
        path = state_store.STATE_ROOT / f"{name}.json"
        assert_true(f"state file {name}", path.exists(), str(path))
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert_true(f"state file list {name}", isinstance(raw, list), str(type(raw)))

    reload(storage_service)
    reload(task_service)
    reload(report_service)

    restored_project = storage_service.get_project(project["id"])
    restored_subjects = storage_service.list_subjects(project["id"])
    restored_file = storage_service.get_eeg_file(eeg_file["id"])
    restored_task = task_service.get_task(task["id"])
    restored_artifacts = task_service.list_task_artifacts(task["id"])
    restored_report = report_service.get_report(report["id"])

    assert_true("project restored", restored_project.id == project["id"])
    assert_true("subject restored", any(item.id == subject["id"] for item in restored_subjects))
    assert_true("file restored", restored_file.metadata_json.get("label") == "persistent-label", restored_file.model_dump_json())
    assert_true("task restored", restored_task.status == "completed", restored_task.model_dump_json())
    assert_true("artifacts restored", len(restored_artifacts) >= len(artifacts), str(len(restored_artifacts)))
    assert_true("report restored", restored_report.id == report["id"] and Path(restored_report.package_path).exists())

    readiness = client.get("/api/health/readiness").json()
    assert_true("readiness state root", readiness["storage_roots"]["state"]["writable"], json.dumps(readiness["storage_roots"]["state"], ensure_ascii=False))
    assert_true("readiness wording", any("JSON registry" in item for item in readiness["known_v01_limits"]), json.dumps(readiness["known_v01_limits"], ensure_ascii=False))

    summary = {
        "status": "passed",
        "project_id": project["id"],
        "subject_id": subject["id"],
        "file_id": eeg_file["id"],
        "task_id": task["id"],
        "report_id": report["id"],
        "state_root": str(state_store.STATE_ROOT),
    }
    output_dir = ROOT / "work" / "acceptance"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "v01_persistence_latest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
