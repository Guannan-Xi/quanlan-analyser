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
        assert plan["schema_version"] == "qlanalyser-data-preparation-v0.2"
        assert "erp" in plan["module_scope"]
        assert "multitaper_psd_tfr" in plan["module_scope"]
        assert "connectivity" in plan["module_scope"]

        read_back = client.get(f"/api/data-preparation/plans/{plan['id']}")
        assert read_back.status_code == 200
        assert read_back.json()["id"] == plan["id"]

        current_for_file = client.get("/api/eeg/files/eeg_api/data-preparation-plan")
        assert current_for_file.status_code == 200
        assert current_for_file.json()["id"] == plan["id"]

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
        assert conflict.json()["detail"]["error_code"] == "PLAN_REVISION_CONFLICT"

        reference = client.post(f"/api/data-preparation/plans/{plan['id']}/task-reference", json={
            "module_name": "psd",
            "workflow_id": "resting_psd",
            "expected_revision": 2,
        })
        assert reference.status_code == 200, reference.text
        body = reference.json()
        assert body["parameters_json"]["data_preparation_plan_id"] == plan["id"]

        erp_reference = client.post(f"/api/data-preparation/plans/{plan['id']}/task-reference", json={
            "module_name": "erp",
            "workflow_id": "erp_p300",
            "expected_revision": 2,
        })
        assert erp_reference.status_code == 200, erp_reference.text
        assert erp_reference.json()["module_name"] == "erp"

        multitaper_reference = client.post(f"/api/data-preparation/plans/{plan['id']}/task-reference", json={
            "module_name": "multitaper_psd_tfr",
            "workflow_id": "multitaper_psd_tfr",
            "expected_revision": 2,
        })
        assert multitaper_reference.status_code == 200, multitaper_reference.text
        assert multitaper_reference.json()["module_name"] == "multitaper_psd_tfr"

        connectivity_reference = client.post(f"/api/data-preparation/plans/{plan['id']}/task-reference", json={
            "module_name": "connectivity",
            "workflow_id": "connectivity",
            "expected_revision": 2,
        })
        assert connectivity_reference.status_code == 200, connectivity_reference.text
        assert connectivity_reference.json()["module_name"] == "connectivity"

        default_eeg = eeg_model.EEGFileRead(
            id="eeg_file_route", project_id="proj_api", original_filename="file-route.edf",
            stored_path=root / "uploads" / "file-route.edf", detected_format="edf",
        )
        state_store.upsert_item("eeg_files", default_eeg)
        default_response = client.get("/api/eeg/files/eeg_file_route/data-preparation-plan")
        assert default_response.status_code == 200
        assert default_response.json()["is_default"] is True
        saved_for_file = client.post("/api/eeg/files/eeg_file_route/data-preparation-plan", json={
            "project_id": "proj_api",
            "base_revision": 0,
            "bad_channels": [{"name": "Fp1", "reason": "muscle_artifact"}],
        })
        assert saved_for_file.status_code == 200, saved_for_file.text
        file_plan = saved_for_file.json()
        assert file_plan["revision"] == 1
        assert file_plan["bad_channels"][0]["name"] == "Fp1"
        stale_file_update = client.post("/api/eeg/files/eeg_file_route/data-preparation-plan", json={
            "project_id": "proj_api",
            "base_revision": 0,
            "description": "stale",
        })
        assert stale_file_update.status_code == 409
        assert stale_file_update.json()["detail"]["error_code"] == "PLAN_REVISION_CONFLICT"

        print(json.dumps({"status": "passed", "plan_id": plan["id"], "revision": 2}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
