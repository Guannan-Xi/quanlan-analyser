from fastapi import APIRouter

from backend.services import task_service

router = APIRouter()


@router.get("/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: str) -> dict:
    return task_service.get_artifact_download_descriptor(artifact_id)

