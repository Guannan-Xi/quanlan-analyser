import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="qlanalyser-prep-api-") as tmp:
        root = Path(tmp)
        os.environ["QLANALYSER_STATE_ROOT"] = str(root / "state")
        os.environ["QLANALYSER_DERIVATIVES_ROOT"] = str(root / "derivatives")

        import backend.services.state_store as state_store
        import backend.services.storage_service as storage_service
        import backend.services.data_preparation_service as data_preparation_service
        import backend.services.task_service as task_service
        import backend.main as main_app
        import backend.models.eeg_file as eeg_model

        importlib.reload(state_store)
        importlib.reload(storage_service)
        importlib.reload(data_preparation_service)
        importlib.reload(task_service)
        importlib.reload(main_app)

        from fastapi.testclient import TestClient

        eeg_file = eeg_model.EEGFileRead(
            id="eeg_api", project_id="proj_api", original_filename="api.edf",
            stored_path=root / "uploads" / "api.edf", detected_format="edf",
        )
        state_store.upsert_item("eeg_files", eeg_file)

        client = TestClient(main_app.app)
        created = client.post("/api/data-preparation/plans", json={
            "project_id": "proj_api",
            "input_file_id": "eeg_api",
            "preprocessing_json": {"reference": "average"},
        })
        assert created.status_code == 200, created.text
        plan = created.json()
        assert plan["revision"] == 1

        read_back = client.get(f"/api/data-preparation/plans/{plan['id']}")
        assert read_back.status_code == 200
        assert read_back.json()["id"] == plan["id"]

        updated = client.put(f"/api/data-preparation/plans/{plan['id']}", json={
            "expected_revision": 1,
            "psd_json": {"bands": {"alpha": [8, 12]}},
        })
        assert updated.status_code == 200, updated.text
        assert updated.json()["revision"] == 2

        conflict = client.put(f"/api/data-preparation/plans/{plan['id']}", json={
            "expected_revision": 1,
            "description": "stale",
        })
        assert conflict.status_code == 409

        reference = client.post(f"/api/data-preparation/plans/{plan['id']}/task-reference", json={
            "module_name": "psd",
            "workflow_id": "resting_psd",
            "expected_revision": 2,
        })
        assert reference.status_code == 200, reference.text
        body = reference.json()
        assert body["parameters_json"]["data_preparation_plan_id"] == plan["id"]

        print(json.dumps({"status": "passed", "plan_id": plan["id"], "revision": 2}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
