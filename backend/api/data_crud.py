from fastapi import APIRouter

from backend.services import storage_service

router = APIRouter()


@router.get("/data/files")
def list_customer_files() -> list[dict]:
    return [file.model_dump(mode="json") for file in storage_service.list_eeg_files()]


@router.patch("/data/files/{file_id}")
def update_customer_file(file_id: str, label: str) -> dict:
    storage_service.get_eeg_file(file_id)
    return storage_service.update_eeg_file_label(file_id, label)


@router.delete("/data/files/{file_id}")
def delete_customer_file(file_id: str) -> dict:
    storage_service.delete_eeg_file(file_id)
    return {"id": file_id, "status": "deleted", "delete_mode": "soft"}
