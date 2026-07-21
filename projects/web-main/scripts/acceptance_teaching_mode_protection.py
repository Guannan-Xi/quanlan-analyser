from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = (
    ROOT
    / "work"
    / "release_evidence"
    / "20260626-teaching-mode-independent-product-design"
    / "implementation"
    / "backend_protection_smoke.json"
)


def _as_detail(exc: Exception) -> dict:
    detail = getattr(exc, "detail", None)
    if isinstance(detail, dict):
        return detail
    return {"message": str(detail or exc)}


def _expect_protected(operation: str, fn) -> dict:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - acceptance script reports details.
        status_code = getattr(exc, "status_code", None)
        detail = _as_detail(exc)
        return {
            "operation": operation,
            "blocked": status_code == 409 and detail.get("code") == "TEACHING_DATASET_PROTECTED",
            "status_code": status_code,
            "detail": detail,
        }
    return {"operation": operation, "blocked": False, "status_code": None, "detail": "operation succeeded"}


def _expect_http_detail_code(operation: str, expected_status: int, expected_code: str, fn) -> dict:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - acceptance script reports details.
        status_code = getattr(exc, "status_code", None)
        detail = _as_detail(exc)
        serialized = json.dumps(detail, ensure_ascii=False)
        return {
            "operation": operation,
            "blocked": status_code == expected_status and expected_code in serialized,
            "status_code": status_code,
            "detail": detail,
        }
    return {"operation": operation, "blocked": False, "status_code": None, "detail": "operation succeeded"}


def _payload_count(state_store, registry: str) -> int:
    return len(state_store._load_payload_unlocked(registry))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ql_teaching_state_") as state_root:
        os.environ["QLANALYSER_STATE_ROOT"] = state_root
        sys.path.insert(0, str(ROOT))

        from backend.models.analysis_task import AnalysisTaskCreate, AnalysisTaskRead
        from backend.models.governance import AccountRead
        from backend.models.project import ProjectUpdate
        from backend.models.report import ReportCreate
        from backend.services import billing_service, lab_demo_service, report_service, state_store, storage_service, task_service

        regular = lab_demo_service.ensure_demo_dataset()
        epilepsy = lab_demo_service.ensure_epilepsy_demo_dataset()

        project = regular["project"]
        eeg_file = regular["file"]
        epilepsy_project = epilepsy["project"]
        epilepsy_file = epilepsy["file"]

        checks = [
            {
                "name": "regular_project_has_protection",
                "passed": bool(project.get("permission_policy", {}).get("protected_teaching_dataset")),
            },
            {
                "name": "regular_file_has_protection",
                "passed": bool(eeg_file.get("metadata_json", {}).get("protected_teaching_dataset"))
                and eeg_file.get("retention_policy") == "protected_teaching_demo",
            },
            {
                "name": "epilepsy_project_has_protection",
                "passed": bool(epilepsy_project.get("permission_policy", {}).get("protected_teaching_dataset")),
            },
            {
                "name": "epilepsy_file_has_protection",
                "passed": bool(epilepsy_file.get("metadata_json", {}).get("protected_teaching_dataset"))
                and epilepsy_file.get("retention_policy") == "protected_teaching_demo",
            },
        ]

        blocked_operations = [
            _expect_protected(
                "archive_regular_project",
                lambda: storage_service.archive_project(lab_demo_service.DEMO_PROJECT_ID),
            ),
            _expect_protected(
                "update_regular_project",
                lambda: storage_service.update_project(
                    lab_demo_service.DEMO_PROJECT_ID,
                    ProjectUpdate(name="should not change"),
                ),
            ),
            _expect_protected(
                "rename_regular_file",
                lambda: storage_service.update_eeg_file_label(lab_demo_service.DEMO_FILE_ID, "should not change"),
            ),
            _expect_protected(
                "delete_regular_file",
                lambda: storage_service.delete_eeg_file(lab_demo_service.DEMO_FILE_ID),
            ),
            _expect_protected(
                "archive_epilepsy_project",
                lambda: storage_service.archive_project(lab_demo_service.EPILEPSY_DEMO_PROJECT_ID),
            ),
            _expect_protected(
                "delete_epilepsy_file",
                lambda: storage_service.delete_eeg_file(lab_demo_service.EPILEPSY_DEMO_FILE_ID),
            ),
        ]
        formal_state_registries = ["tasks", "artifacts", "billing_transactions", "usage_records", "reports"]
        before_formal_attempt = {name: _payload_count(state_store, name) for name in formal_state_registries}
        formal_boundary_operations = [
            _expect_http_detail_code(
                "formal_task_rejects_regular_teaching_file",
                422,
                "FORMAL_TASK_REQUIRES_UPLOADED_AUTHORIZED_EEG",
                lambda: task_service.create_task(
                    AnalysisTaskCreate(
                        project_id=lab_demo_service.DEMO_PROJECT_ID,
                        input_file_id=lab_demo_service.DEMO_FILE_ID,
                        module_name="psd",
                        workflow_id="resting_psd",
                        owner_user_id="owner-b",
                        created_by="owner-b",
                        parameters_json={"fmin": 1, "fmax": 35},
                    ),
                    requesting_user_id="owner-b",
                ),
            )
        ]
        after_formal_attempt = {name: _payload_count(state_store, name) for name in formal_state_registries}
        formal_rejection_no_state_delta = before_formal_attempt == after_formal_attempt

        state_store.upsert_item(
            "accounts",
            AccountRead(
                id="owner-b",
                email="owner-b@example.test",
                balance_credits=100.0,
                trial_credits=0.0,
            ),
        )
        forged_task = AnalysisTaskRead(
            id="task_forged_demo_backed_formal_report_gate",
            project_id=lab_demo_service.DEMO_PROJECT_ID,
            input_file_id=lab_demo_service.DEMO_FILE_ID,
            module_name="psd",
            workflow_id="resting_psd",
            owner_user_id="owner-b",
            created_by="owner-b",
            status="completed",
            queue_status="completed",
            progress=100,
            parameters_json={"fmin": 1, "fmax": 35},
            quota_charge_preview_json={"estimated_credits": 1.0, "billing_account_id": "owner-b"},
        )
        billing_transaction = billing_service.charge_analysis_task(
            account_id="owner-b",
            task_id=forged_task.id,
            module_name=forged_task.module_name,
            quantity_credits=1.0,
        )
        forged_task.actual_resource_usage_json = {"billing_transaction_id": billing_transaction.id}
        state_store.upsert_item("tasks", forged_task)
        formal_boundary_operations.append(
            _expect_http_detail_code(
                "formal_report_rejects_demo_backed_completed_task",
                422,
                "REPORT_SOURCE_NOT_FORMAL_DELIVERY",
                lambda: report_service.create_report(
                    ReportCreate(
                        project_id=lab_demo_service.DEMO_PROJECT_ID,
                        task_id=forged_task.id,
                        title="Forged demo-backed report should fail",
                        owner_user_id="owner-b",
                        created_by="owner-b",
                    )
                ),
            )
        )

        post_regular_file = storage_service.get_eeg_file(lab_demo_service.DEMO_FILE_ID).model_dump(mode="json")
        post_epilepsy_file = storage_service.get_eeg_file(lab_demo_service.EPILEPSY_DEMO_FILE_ID).model_dump(mode="json")
        checks.extend(
            [
                {
                    "name": "regular_file_still_available",
                    "passed": post_regular_file.get("status") != "deleted"
                    and post_regular_file.get("upload_status") != "deleted",
                },
                {
                    "name": "epilepsy_file_still_available",
                    "passed": post_epilepsy_file.get("status") != "deleted"
                    and post_epilepsy_file.get("upload_status") != "deleted",
                },
            ]
        )

        checks.append(
            {
                "name": "formal_teaching_rejection_no_state_delta",
                "passed": formal_rejection_no_state_delta,
                "before": before_formal_attempt,
                "after": after_formal_attempt,
            }
        )

        passed = (
            all(item["passed"] for item in checks)
            and all(item["blocked"] for item in blocked_operations)
            and all(item["blocked"] for item in formal_boundary_operations)
        )
        result = {
            "status": "passed" if passed else "failed",
            "state_root": state_root,
            "checks": checks,
            "blocked_operations": blocked_operations,
            "formal_boundary_operations": formal_boundary_operations,
        }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
