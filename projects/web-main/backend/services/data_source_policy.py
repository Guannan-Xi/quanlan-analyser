from __future__ import annotations

from typing import Any

from fastapi import HTTPException


PROTECTED_TEACHING_PROJECT_IDS = {"proj_demo_learning", "proj_demo_epilepsy_lab"}
PROTECTED_TEACHING_FILE_IDS = {"eeg_demo_teaching_oddball", "eeg_demo_epilepsy_high_amplitude"}
PROTECTED_TEACHING_RETENTION_POLICY = "protected_teaching_demo"
FORMAL_UPLOAD_STATUSES = {"uploaded", "metadata_ready", "owner_authorized_manifest"}
LAB_PREVIEW_DELIVERY_SCOPES = {"lab_preview_only", "teaching_demo", "sandbox", "demo"}


def is_protected_teaching_project(project: Any | None) -> bool:
    if project is None:
        return False
    policy = getattr(project, "permission_policy", None) or {}
    project_id = str(getattr(project, "id", "") or "")
    return bool(
        project_id in PROTECTED_TEACHING_PROJECT_IDS
        or project_id.startswith("proj_demo_")
        or policy.get("protected_teaching_dataset")
        or policy.get("teaching_mode")
    )


def is_protected_teaching_file(eeg_file: Any | None) -> bool:
    if eeg_file is None:
        return False
    metadata = getattr(eeg_file, "metadata_json", None) or {}
    policy = getattr(eeg_file, "permission_policy", None) or {}
    file_id = str(getattr(eeg_file, "id", "") or "")
    project_id = str(getattr(eeg_file, "project_id", "") or "")
    return bool(
        file_id in PROTECTED_TEACHING_FILE_IDS
        or file_id.startswith("eeg_demo_")
        or project_id in PROTECTED_TEACHING_PROJECT_IDS
        or project_id.startswith("proj_demo_")
        or metadata.get("demo")
        or metadata.get("protected_teaching_dataset")
        or metadata.get("teaching_mode")
        or policy.get("protected_teaching_dataset")
        or policy.get("teaching_mode")
        or getattr(eeg_file, "retention_policy", None) == PROTECTED_TEACHING_RETENTION_POLICY
    )


def formal_input_blockers(project: Any, eeg_file: Any, *, owner_user_id: str | None = None) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    if is_protected_teaching_project(project):
        blockers.append({"code": "TEACHING_PROJECT_NOT_FORMAL_INPUT", "project_id": getattr(project, "id", None)})
    if is_protected_teaching_file(eeg_file):
        blockers.append({"code": "TEACHING_DATA_NOT_FORMAL_INPUT", "input_file_id": getattr(eeg_file, "id", None)})
    if owner_user_id and getattr(project, "owner_user_id", None) != owner_user_id:
        blockers.append({"code": "FORMAL_PROJECT_OWNER_MISMATCH", "project_owner_user_id": getattr(project, "owner_user_id", None)})
    if owner_user_id and getattr(eeg_file, "owner_user_id", None) != owner_user_id:
        blockers.append({"code": "FORMAL_FILE_OWNER_MISMATCH", "file_owner_user_id": getattr(eeg_file, "owner_user_id", None)})

    upload_status = str(getattr(eeg_file, "upload_status", "") or "").strip()
    if upload_status not in FORMAL_UPLOAD_STATUSES:
        blockers.append({"code": "FORMAL_INPUT_UPLOAD_STATUS_REQUIRED", "upload_status": upload_status})
    if getattr(eeg_file, "upload_authorization_confirmed", False) is not True:
        blockers.append({"code": "FORMAL_INPUT_UPLOAD_AUTHORIZATION_REQUIRED"})
    if not str(getattr(eeg_file, "upload_authorization_text", "") or "").strip():
        blockers.append({"code": "FORMAL_INPUT_UPLOAD_AUTHORIZATION_TEXT_REQUIRED"})
    if getattr(eeg_file, "upload_authorization_confirmed_at", None) is None:
        blockers.append({"code": "FORMAL_INPUT_UPLOAD_AUTHORIZATION_TIMESTAMP_REQUIRED"})
    sha256 = str(getattr(eeg_file, "sha256", "") or "")
    if len(sha256) != 64:
        blockers.append({"code": "FORMAL_INPUT_SHA256_REQUIRED", "sha256_length": len(sha256)})
    if getattr(eeg_file, "retention_policy", None) in LAB_PREVIEW_DELIVERY_SCOPES:
        blockers.append({"code": "FORMAL_INPUT_DELIVERY_SCOPE_REQUIRED", "retention_policy": getattr(eeg_file, "retention_policy", None)})
    return blockers


def assert_formal_customer_eeg_source(project: Any, eeg_file: Any, *, owner_user_id: str | None = None, context: str = "task") -> None:
    blockers = formal_input_blockers(project, eeg_file, owner_user_id=owner_user_id)
    if not blockers:
        return
    code = "REPORT_SOURCE_NOT_FORMAL_DELIVERY" if context == "report" else "FORMAL_TASK_REQUIRES_UPLOADED_AUTHORIZED_EEG"
    raise HTTPException(
        status_code=422,
        detail={
            "code": code,
            "message": "Formal customer analysis requires an uploaded, authorized customer EEG file. Teaching/demo/lab-preview data cannot be used for formal delivery.",
            "blockers": blockers,
            "project_id": getattr(project, "id", None),
            "input_file_id": getattr(eeg_file, "id", None),
        },
    )
