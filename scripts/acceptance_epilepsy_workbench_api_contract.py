from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.main import app

EVIDENCE_ROOT = ROOT / "work" / "release_evidence" / "epilepsy_source_workbench_replica_acceptance"


def now_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def assert_ok(condition: bool, code: str, detail: Any) -> None:
    if not condition:
        raise AssertionError(f"{code}: {detail}")


def request_json(client: TestClient, method: str, path: str, **kwargs: Any) -> tuple[dict[str, Any], float, int]:
    start = time.perf_counter()
    response = getattr(client, method.lower())(path, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    status = response.status_code
    try:
        payload = response.json()
    except Exception:
        payload = {"raw_text": response.text}
    if status >= 400:
        raise AssertionError(f"HTTP {status} {method} {path}: {payload}")
    return payload, elapsed_ms, status


def main() -> int:
    run_id = now_run_id()
    evidence_dir = EVIDENCE_ROOT / run_id
    evidence_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "schema_version": "epilepsy_workbench_api_contract.v1",
        "run_id": run_id,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "checks": [],
        "timings_ms": {},
        "evidence_dir": str(evidence_dir),
    }

    def record(name: str, status: str, detail: Any = None) -> None:
        result["checks"].append({"name": name, "status": status, "detail": detail})

    try:
        with TestClient(app) as client:
            openapi, openapi_ms, _ = request_json(client, "GET", "/openapi.json")
            result["timings_ms"]["openapi"] = round(openapi_ms, 2)
            assert_ok("/api/eeg/files/{file_id}/waveform-window" in openapi.get("paths", {}), "OPENAPI_WAVEFORM_ROUTE_MISSING", list(openapi.get("paths", {}).keys())[-10:])
            record("openapi_waveform_route", "passed", {"path_count": len(openapi.get("paths", {}))})

            dataset, dataset_ms, _ = request_json(client, "GET", "/api/lab/demo/epilepsy")
            result["timings_ms"]["ensure_epilepsy_edf_fixture"] = round(dataset_ms, 2)
            file_info = dataset.get("file") or {}
            file_id = file_info.get("id")
            assert_ok(bool(file_id), "FIXTURE_FILE_ID_MISSING", dataset)
            assert_ok(str(file_info.get("detected_format", "")).lower() == "edf", "FIXTURE_NOT_EDF", file_info)
            record("edf_fixture_ready", "passed", {"file_id": file_id, "filename": file_info.get("original_filename"), "format": file_info.get("detected_format")})

            task, task_ms, _ = request_json(
                client,
                "POST",
                "/api/lab/demo/run/epilepsy_ml/configured",
                json={"parameters_json": {"method": "ml_epoch_classifier", "unit_mode": "source_compatible", "probability_threshold": 0.5}},
            )
            result["timings_ms"]["run_epilepsy_ml_task"] = round(task_ms, 2)
            assert_ok(task.get("status") == "completed", "TASK_NOT_COMPLETED", task)
            task_id = task.get("id")
            record("epilepsy_ml_task_completed", "passed", {"task_id": task_id, "workflow_id": task.get("workflow_id")})

            artifacts, artifacts_ms, _ = request_json(client, "GET", f"/api/tasks/{task_id}/artifacts")
            result["timings_ms"]["list_artifacts"] = round(artifacts_ms, 2)
            labels = {item.get("label") for item in artifacts}
            assert_ok("epilepsy_epoch_scores" in labels and "epilepsy_events" in labels and "epilepsy_summary" in labels, "REQUIRED_ARTIFACTS_MISSING", sorted(labels))
            record("source_artifacts_present", "passed", {"labels": sorted(labels)})

            session, session_ms, _ = request_json(
                client,
                "POST",
                f"/api/tasks/{task_id}/epilepsy-review-sessions",
                json={"input_file_id": file_id, "workflow_id": task.get("workflow_id"), "epoch_length_sec": 5, "current_epoch": 0},
            )
            result["timings_ms"]["create_review_session"] = round(session_ms, 2)
            session_id = session.get("id")
            assert_ok(bool(session_id), "SESSION_ID_MISSING", session)
            record("review_session_created", "passed", {"session_id": session_id})

            patch_payload = {
                "status": "reviewing",
                "current_epoch": 2,
                "selected_range": {"start": 2, "end": 3},
                "epoch_overrides": {"2": 1, "3": 1},
                "event_reviews": {
                    "1": {"event_id": "1", "status": "confirmed", "note": "API contract smoke", "reviewer": "contract-script"}
                },
                "actions": [
                    {"type": "set_stage", "target_range": {"start": 2, "end": 3}, "after": {"stage_code": 1}, "note": "API contract smoke", "source": "acceptance_script"}
                ],
                "ui_state": {"visible_epoch_count": "All", "selected_event_id": "1", "active_waveform_label": "raw_preview_figure"},
            }
            patched, patch_ms, _ = request_json(client, "PATCH", f"/api/epilepsy-review-sessions/{session_id}", json=patch_payload)
            result["timings_ms"]["patch_review_session"] = round(patch_ms, 2)
            assert_ok(patched.get("epoch_overrides", {}).get("2") == 1, "PATCH_OVERRIDE_MISSING", patched)
            record("review_session_patch", "passed", {"override_count": len(patched.get("epoch_overrides", {}))})

            manifest, manifest_ms, _ = request_json(client, "GET", f"/api/eeg/files/{file_id}/waveform-pyramid/manifest")
            result["timings_ms"]["waveform_manifest"] = round(manifest_ms, 2)
            assert_ok(manifest.get("unit") == "uV", "MANIFEST_UNIT_NOT_UV", manifest.get("unit_policy"))
            record("waveform_manifest", "passed", {"duration_sec": manifest.get("duration_sec"), "unit": manifest.get("unit")})

            raw_window, raw_ms, _ = request_json(
                client,
                "GET",
                f"/api/eeg/files/{file_id}/waveform-window?start_sec=2&duration_sec=8&max_points=1200&filter_profile_id=raw&include_events=true",
            )
            result["timings_ms"]["waveform_raw_window"] = round(raw_ms, 2)
            first_time = raw_window.get("channels", [{}])[0].get("times_sec", [None])[0]
            assert_ok(raw_window.get("filter_profile_id") == "raw", "RAW_PROFILE_INVALID", raw_window.get("filter_profile"))
            assert_ok(abs(float(first_time) - 2.0) < 0.02, "WAVEFORM_TIME_AXIS_OFFSET", {"first_time": first_time})
            assert_ok(raw_window.get("unit") == "uV", "RAW_UNIT_NOT_UV", raw_window.get("unit_policy"))
            record("waveform_raw_window", "passed", {"first_time": first_time, "channel_count": len(raw_window.get("channels", [])), "encoding": raw_window.get("channels", [{}])[0].get("encoding")})

            filter_window, filter_ms, _ = request_json(
                client,
                "GET",
                f"/api/eeg/files/{file_id}/waveform-window?start_sec=2&duration_sec=8&max_points=1200&filter_profile_id=preview_0p5_45_notch50&include_events=true",
            )
            result["timings_ms"]["waveform_filter_window"] = round(filter_ms, 2)
            assert_ok(filter_window.get("filter_profile", {}).get("applied") is True, "FILTER_NOT_APPLIED", filter_window.get("filter_profile"))
            record("waveform_filter_window", "passed", {"profile": filter_window.get("filter_profile_id"), "channel_count": len(filter_window.get("channels", []))})

            export, export_ms, _ = request_json(client, "POST", f"/api/epilepsy-review-sessions/{session_id}/exports")
            result["timings_ms"]["export_review_session"] = round(export_ms, 2)
            required_export_keys = {"reviewed_epoch_scores_csv", "reviewed_events_csv", "review_actions_jsonl", "review_session_manifest", "source_artifacts", "non_medical_scope"}
            assert_ok(required_export_keys.issubset(export.keys()), "EXPORT_KEYS_MISSING", sorted(set(export.keys())))
            assert_ok("review_stage_code" in export.get("reviewed_epoch_scores_csv", ""), "EXPORT_EPOCH_CSV_INVALID", export.get("reviewed_epoch_scores_csv", "")[:120])
            assert_ok(export.get("review_session_manifest", {}).get("immutability", {}).get("source_artifacts_readonly") is True, "EXPORT_IMMUTABILITY_MISSING", export.get("review_session_manifest"))
            record("review_export_contract", "passed", {"keys": sorted(required_export_keys), "source_artifact_count": len(export.get("source_artifacts", []))})

            (evidence_dir / "dataset.json").write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
            (evidence_dir / "task.json").write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
            (evidence_dir / "artifacts.json").write_text(json.dumps(artifacts, ensure_ascii=False, indent=2), encoding="utf-8")
            (evidence_dir / "session.json").write_text(json.dumps(patched, ensure_ascii=False, indent=2), encoding="utf-8")
            (evidence_dir / "waveform_raw_window.json").write_text(json.dumps(raw_window, ensure_ascii=False, indent=2), encoding="utf-8")
            (evidence_dir / "waveform_filter_window.json").write_text(json.dumps(filter_window, ensure_ascii=False, indent=2), encoding="utf-8")
            (evidence_dir / "export.json").write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")

        result["status"] = "passed"
        result["finished_at"] = datetime.now().isoformat()
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        result["finished_at"] = datetime.now().isoformat()
        (evidence_dir / "final_verdict.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    (evidence_dir / "final_verdict.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    latest = EVIDENCE_ROOT / "latest_final_verdict.json"
    latest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
