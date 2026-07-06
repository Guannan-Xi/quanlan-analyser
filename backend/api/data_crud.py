from fastapi import APIRouter, Depends

from backend.models.governance import AccountRead
from backend.services import account_service
from backend.services import storage_service

router = APIRouter()


def _requesting_user_id(current: AccountRead) -> str | None:
    return None if current.role == "admin" else current.id


def _is_visible_file(file, current: AccountRead) -> bool:
    if current.role == "admin" or file.owner_user_id == current.id:
        return True
    metadata = file.metadata_json or {}
    policy = file.permission_policy or {}
    return bool(
        metadata.get("protected_teaching_dataset")
        or metadata.get("teaching_mode")
        or policy.get("protected_teaching_dataset")
        or policy.get("teaching_mode")
        or file.retention_policy == "protected_teaching_demo"
    )


@router.get("/data/files")
def list_customer_files(
    project_id: str | None = None,
    input_file_id: str | None = None,
    current: AccountRead = Depends(account_service.require_current_account),
) -> list[dict]:
    files = [file for file in storage_service.list_eeg_files() if _is_visible_file(file, current)]
    if project_id:
        files = [file for file in files if file.project_id == project_id]
    if input_file_id:
        files = [file for file in files if file.id == input_file_id]
    return [file.model_dump(mode="json") for file in files]


@router.patch("/data/files/{file_id}")
def update_customer_file(
    file_id: str,
    label: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> dict:
    storage_service.get_eeg_file(file_id, requesting_user_id=_requesting_user_id(current))
    return storage_service.update_eeg_file_label(file_id, label)


@router.delete("/data/files/{file_id}")
def delete_customer_file(
    file_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> dict:
    storage_service.get_eeg_file(file_id, requesting_user_id=_requesting_user_id(current))
    storage_service.delete_eeg_file(file_id)
    return {"id": file_id, "status": "deleted", "delete_mode": "soft"}
