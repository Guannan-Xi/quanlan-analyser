from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.services import task_service

router = APIRouter()

_DERIVATIVES_ROOT = (Path(__file__).resolve().parents[2] / "data" / "derivatives").resolve()


def _assert_path_within_derivatives(raw_path: Path) -> Path:
    """Defense-in-depth: ensure resolved artifact path stays inside derivatives root.

    Uses Path.relative_to() instead of string startswith() to avoid false
    positives on sibling directories that share a name prefix.
    """
    resolved = raw_path.resolve()
    try:
        resolved.relative_to(_DERIVATIVES_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Artifact path is outside the allowed directory") from exc
    return resolved


@router.get("/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: str) -> FileResponse:
    descriptor = task_service.get_artifact_download_descriptor(artifact_id)
    path = _assert_path_within_derivatives(Path(descriptor["path"]))
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=410, detail="Artifact file is not available on disk")
    return FileResponse(
        path,
        media_type=descriptor.get("mime_type") or "application/octet-stream",
        filename=path.name,
    )
