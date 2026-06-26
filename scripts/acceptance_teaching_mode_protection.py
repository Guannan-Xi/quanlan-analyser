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


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ql_teaching_state_") as state_root:
        os.environ["QLANALYSER_STATE_ROOT"] = state_root
        sys.path.insert(0, str(ROOT))

        from backend.models.project import ProjectUpdate
        from backend.services import lab_demo_service, storage_service

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

        passed = all(item["passed"] for item in checks) and all(item["blocked"] for item in blocked_operations)
        result = {
            "status": "passed" if passed else "failed",
            "state_root": state_root,
            "checks": checks,
            "blocked_operations": blocked_operations,
        }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
