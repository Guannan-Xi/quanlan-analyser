from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main import app

FIXTURE_PATH = ROOT / "work" / "fixtures" / "epilepsy_regular_labeled" / "regular_epilepsy_labeled_60s.edf"
EVIDENCE_PATH = ROOT / "work" / "release_evidence" / "20260629-epilepsy-cloud-trial-v0-1-upload-to-export" / "cloud_upload_to_export_contract.json"
DATA_PREPARATION_CONTRACT_VERSION = "qlanalyser-data-preparation-v0.2"
EXPECTED_STAGE_CODE = "000001100000"


def ensure_fixture() -> None:
    if FIXTURE_PATH.exists():
        return
    from scripts.generate_regular_epilepsy_labeled_fixture import main as generate_fixture

    generate_fixture()
    if not FIXTURE_PATH.exists():
        raise AssertionError(f"Fixture was not generated: {FIXTURE_PATH}")


def rows_from_artifact(artifacts: list[dict[str, Any]], label: str) -> list[dict[str, str]]:
    matches = [item for item in artifacts if item.get("label") == label]
    if not matches:
        raise AssertionError(f"Missing artifact label: {label}; labels={sorted(item.get('label') for item in artifacts)}")
    path = Path(matches[0]["path"])
    if not path.exists():
        raise AssertionError(f"Artifact path missing: {path}")
    return list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))


def stage_code_from_rows(rows: list[dict[str, str]]) -> str:
    return "".join(str(row.get("Stage_Code", "")).strip() for row in rows)


def main() -> None:
    ensure_fixture()
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    evidence: dict[str, Any] = {
        "status": "RUNNING",
        "fixture_path": str(FIXTURE_PATH),
        "expected_stage_code": EXPECTED_STAGE_CODE,
        "expected_event": {"start_sec": 25.0, "end_sec": 35.0},
        "checks": {},
    }
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/projects",
                json={"name": "Epilepsy cloud trial upload-to-export acceptance", "description": "v0.1 upload path", "research_type": "epilepsy_cloud_trial_v0_1"},
            )
            response.raise_for_status()
            project = response.json()

            with FIXTURE_PATH.open("rb") as handle:
                response = client.post(
                    f"/api/eeg/upload?project_id={project['id']}&upload_authorization_confirmed=true&upload_authorization_text=authorized_cloud_trial_fixture",
                    files={"file": (FIXTURE_PATH.name, handle, "application/edf")},
                )
            response.raise_for_status()
            eeg_file = response.json()
            evidence["checks"]["upload_authorized"] = bool(eeg_file.get("upload_authorization_confirmed"))

            response = client.get(f"/api/eeg/files/{eeg_file['id']}/metadata")
            response.raise_for_status()
            metadata = response.json()
            evidence["checks"]["metadata_readable"] = metadata.get("status") == "readable"

            response = client.post(
                "/api/data-preparation/plans",
                json={
                    "project_id": project["id"],
                    "input_file_id": eeg_file["id"],
                    "status": "confirmed",
                    "title": "Epilepsy cloud trial accepted preparation plan",
                    "description": "Confirmed plan for upload-to-export acceptance.",
                    "source_file": {
                        "file_id": eeg_file["id"],
                        "original_filename": eeg_file["original_filename"],
                        "detected_format": eeg_file["detected_format"],
                    },
                    "metadata_review": {
                        "status": "accepted_for_epilepsy_screening",
                        "channel_count": metadata.get("channel_count"),
                        "duration_sec": metadata.get("duration_sec"),
                    },
                },
            )
            response.raise_for_status()
            plan = response.json()
            prep_params = {
                "data_preparation_plan_id": plan["id"],
                "data_preparation_revision": plan["revision"],
                "data_preparation_contract_version": DATA_PREPARATION_CONTRACT_VERSION,
            }
            evidence["checks"]["preparation_confirmed"] = plan.get("status") == "confirmed"

            response = client.post(
                "/api/data-preparation/plans",
                json={
                    "project_id": project["id"],
                    "input_file_id": eeg_file["id"],
                    "status": "draft",
                    "title": "Draft plan must not run formal analysis",
                },
            )
            response.raise_for_status()
            draft_plan = response.json()
            response = client.post(
                "/api/tasks",
                json={
                    "project_id": project["id"],
                    "module_name": "epilepsy_ml",
                    "workflow_id": "epilepsy_ml_xgboost",
                    "input_file_id": eeg_file["id"],
                    "parameters_json": {
                        "method": "ml_epoch_classifier",
                        "eeg_channel": "EEG3",
                        "epoch_length_sec": 5,
                        "probability_threshold": 0.5,
                        "unit_mode": "source_compatible",
                        "data_preparation_plan_id": draft_plan["id"],
                        "data_preparation_revision": draft_plan["revision"],
                        "data_preparation_contract_version": DATA_PREPARATION_CONTRACT_VERSION,
                    },
                },
            )
            evidence["checks"]["draft_plan_rejected"] = response.status_code == 422 and "DATA_PREPARATION_PLAN_NOT_CONFIRMED" in response.text

            response = client.post(
                "/api/projects",
                json={"name": "Epilepsy cloud trial mismatch project", "description": "wrong-file negative", "research_type": "epilepsy_cloud_trial_v0_1"},
            )
            response.raise_for_status()
            mismatch_project = response.json()
            with FIXTURE_PATH.open("rb") as handle:
                response = client.post(
                    f"/api/eeg/upload?project_id={mismatch_project['id']}&upload_authorization_confirmed=true&upload_authorization_text=authorized_cloud_trial_fixture",
                    files={"file": (FIXTURE_PATH.name, handle, "application/edf")},
                )
            response.raise_for_status()
            mismatch_file = response.json()
            response = client.post(
                "/api/tasks",
                json={
                    "project_id": project["id"],
                    "module_name": "epilepsy_ml",
                    "workflow_id": "epilepsy_ml_xgboost",
                    "input_file_id": mismatch_file["id"],
                    "parameters_json": {
                        "method": "ml_epoch_classifier",
                        "eeg_channel": "EEG3",
                        "epoch_length_sec": 5,
                        "probability_threshold": 0.5,
                        "unit_mode": "source_compatible",
                        **prep_params,
                    },
                },
            )
            evidence["checks"]["wrong_file_plan_rejected"] = response.status_code == 422 and (
                "DATA_PREPARATION_FILE_MISMATCH" in response.text or "DATA_PREPARATION_PROJECT_MISMATCH" in response.text
            )

            task_payload = {
                "project_id": project["id"],
                "module_name": "epilepsy_ml",
                "workflow_id": "epilepsy_ml_xgboost",
                "input_file_id": eeg_file["id"],
                "parameters_json": {
                    "method": "ml_epoch_classifier",
                    "eeg_channel": "EEG3",
                    "epoch_length_sec": 5,
                    "probability_threshold": 0.5,
                    "unit_mode": "source_compatible",
                    **prep_params,
                },
            }
            wrong_workflow_payload = dict(task_payload)
            wrong_workflow_payload["workflow_id"] = "epilepsy_wrong_workflow"
            response = client.post("/api/tasks", json=wrong_workflow_payload)
            evidence["checks"]["wrong_epilepsy_workflow_rejected"] = response.status_code == 422 and "WORKFLOW_CONTRACT_MISMATCH" in response.text

            response = client.post("/api/tasks", json=task_payload)
            response.raise_for_status()
            task = response.json()
            if task.get("status") != "completed":
                raise AssertionError(f"Epilepsy ML task did not complete: {task}")
            evidence["checks"]["epilepsy_ml_completed"] = True
            evidence["task"] = {
                "id": task["id"],
                "module_name": task["module_name"],
                "workflow_id": task["workflow_id"],
                "data_preparation_plan_id": task.get("data_preparation_plan_id"),
                "data_preparation_revision": task.get("data_preparation_revision"),
                "data_preparation_contract_version": task.get("data_preparation_contract_version"),
            }

            response = client.get(f"/api/tasks/{task['id']}/artifacts")
            response.raise_for_status()
            artifacts = response.json()
            epoch_rows = rows_from_artifact(artifacts, "epilepsy_epoch_scores")
            event_rows = rows_from_artifact(artifacts, "epilepsy_events")
            detected_stage_code = stage_code_from_rows(epoch_rows)
            evidence["detected_stage_code"] = detected_stage_code
            evidence["checks"]["stage_code_matches_truth"] = detected_stage_code == EXPECTED_STAGE_CODE
            evidence["checks"]["candidate_event_detected"] = any(
                abs(float(row.get("start_sec", -1)) - 25.0) < 0.01 and abs(float(row.get("end_sec", -1)) - 35.0) < 0.01
                for row in event_rows
            )

            response = client.post(
                f"/api/tasks/{task['id']}/epilepsy-review-sessions",
                json={"input_file_id": eeg_file["id"], "workflow_id": task["workflow_id"], "epoch_length_sec": 5, "current_epoch": 5},
            )
            response.raise_for_status()
            session = response.json()

            response = client.patch(
                f"/api/epilepsy-review-sessions/{session['id']}",
                json={
                    "status": "reviewing",
                    "current_epoch": 5,
                    "selected_range": {"start": 5, "end": 6},
                    "epoch_overrides": {"5": 1, "6": 1},
                    "event_reviews": {
                        "1": {"event_id": "1", "status": "confirmed", "note": "upload-to-export acceptance", "reviewer": "acceptance-script"}
                    },
                    "actions": [
                        {
                            "type": "set_stage",
                            "target_range": {"start": 5, "end": 6},
                            "after": {"stage_code": 1},
                            "note": "confirm fixture event",
                            "source": "acceptance_epilepsy_cloud_trial_upload_to_export",
                        }
                    ],
                },
            )
            response.raise_for_status()

            response = client.post(f"/api/epilepsy-review-sessions/{session['id']}/exports")
            response.raise_for_status()
            export = response.json()
            labels = {item.get("label") for item in export.get("registered_artifacts", [])}
            expected_labels = {
                "epoch_predictions.csv",
                "candidate_events.csv",
                "manual_corrections.csv",
                "final_review_events.csv",
                "summary.json",
                "parameters.json",
                "model_manifest.json",
                "review_revision.json",
                "scope_contract.json",
            }
            review_revision = export.get("review_revision_json") or {}
            evidence["checks"]["v01_export_labels_registered"] = expected_labels.issubset(labels)
            evidence["checks"]["review_revision_carries_preparation_plan"] = review_revision.get("data_preparation_plan_id") == plan["id"]
            evidence["checks"]["review_revision_carries_preparation_revision"] = review_revision.get("data_preparation_revision") == plan["revision"]
            evidence["checks"]["review_revision_carries_preparation_contract"] = review_revision.get("data_preparation_contract_version") == DATA_PREPARATION_CONTRACT_VERSION
            evidence["export"] = {
                "session_id": export.get("session_id"),
                "registered_labels": sorted(labels),
                "review_revision_json": review_revision,
                "scope_contract_json": export.get("scope_contract_json"),
            }

        failed = {key: value for key, value in evidence["checks"].items() if value is not True}
        if failed:
            evidence["status"] = "FAIL"
            evidence["failed_checks"] = failed
            raise AssertionError(json.dumps(failed, ensure_ascii=False))
        evidence["status"] = "PASS"
    except Exception as exc:
        evidence["status"] = "FAIL"
        evidence["error"] = str(exc)
        EVIDENCE_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(evidence, ensure_ascii=False, indent=2))
        raise
    EVIDENCE_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "PASS", "evidence": str(EVIDENCE_PATH)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
