from fastapi import APIRouter, UploadFile

from backend.models.eeg_file import EEGFileRead
from backend.services import metadata_service, storage_service

router = APIRouter()


@router.post("/eeg/upload", response_model=EEGFileRead)
async def upload_eeg(project_id: str, subject_id: str | None = None, file: UploadFile | None = None) -> EEGFileRead:
    return await storage_service.create_eeg_file(project_id=project_id, subject_id=subject_id, upload=file)


@router.get("/eeg/files/{file_id}", response_model=EEGFileRead)
def get_eeg_file(file_id: str) -> EEGFileRead:
    return storage_service.get_eeg_file(file_id)


@router.get("/eeg/files/{file_id}/metadata")
def get_eeg_metadata(file_id: str) -> dict:
    eeg_file = storage_service.get_eeg_file(file_id)
    return metadata_service.extract_metadata(eeg_file)

