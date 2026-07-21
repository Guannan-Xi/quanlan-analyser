from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from backend.models.governance import AccountRead
from backend.services import account_service, customer_delivery_service, task_service

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
def download_artifact(
    artifact_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> FileResponse:
    descriptor = task_service.get_artifact_download_descriptor(artifact_id)
    task = task_service.get_task(str(descriptor["task_id"]), requesting_user_id=current.id)
    task_service.assert_task_artifacts_deliverable(task)
    task_service.assert_artifact_download_allowed(descriptor, task)
    path = customer_delivery_service.assert_customer_artifact_file(descriptor, task, task_service)
    safe_path = customer_delivery_service.customer_safe_file(path)
    return FileResponse(
        safe_path,
        media_type=descriptor.get("mime_type") or "application/octet-stream",
        filename=path.name,
    )
