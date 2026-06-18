from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.services import task_service

router = APIRouter()


@router.get("/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: str) -> FileResponse:
    descriptor = task_service.get_artifact_download_descriptor(artifact_id)
    path = Path(descriptor["path"])
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=410, detail="Artifact file is not available on disk")
    return FileResponse(
        path,
        media_type=descriptor.get("mime_type") or "application/octet-stream",
        filename=path.name,
    )
