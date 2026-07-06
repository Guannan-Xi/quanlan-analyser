import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.models.analysis_task import AnalysisTaskCreate, AnalysisTaskRead
from backend.models.artifact import ArtifactRead
from backend.models.governance import AccountRead, AuditEventRead
from backend.services import account_service, audit_service, task_service

router = APIRouter()

_DERIVATIVES_ROOT = (Path(__file__).resolve().parents[2] / "data" / "derivatives").resolve()
_CUSTOMER_ALLOWED_TASK_MODULES = {"qc", "preprocess", "psd", "erp"}


def _assert_path_within_derivatives(raw_path: Path) -> Path:
    """Defense-in-depth: ensure resolved artifact path stays inside derivatives root."""
    resolved = raw_path.resolve()
    try:
        resolved.relative_to(_DERIVATIVES_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Artifact path is outside the allowed directory") from exc
    return resolved


@router.post("/tasks", response_model=AnalysisTaskRead)
def create_task(payload: AnalysisTaskCreate, current: AccountRead = Depends(account_service.require_current_account)) -> AnalysisTaskRead:
    if current.role != "admin" and payload.module_name not in _CUSTOMER_ALLOWED_TASK_MODULES:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "MODULE_NOT_AVAILABLE_FOR_CUSTOMER_WORKFLOW",
                "message": "This analysis module is not available in the customer workflow.",
                "suggested_action": "Use PSD first, or ask an operator to enable a lab/internal workflow.",
            },
        )
    owned_payload = payload.model_copy(update={"owner_user_id": current.id, "created_by": current.id})
    return task_service.create_task(owned_payload, requesting_user_id=current.id)


@router.post("/tasks/{task_id}/result-review", response_model=AuditEventRead)
def mark_task_result_reviewed(task_id: str, current: AccountRead = Depends(account_service.require_current_account)) -> AuditEventRead:
    task = task_service.get_task(task_id, requesting_user_id=current.id)
    if task.status != "completed":
        raise HTTPException(status_code=422, detail="Only completed task results can be marked as reviewed")
    return audit_service.record_event(
        action="result.reviewed",
        object_type="analysis_task",
        object_id=task.id,
        organization_id=task.organization_id,
        project_id=task.project_id,
        actor_user_id=current.id,
        metadata_json={
            "module_name": task.module_name,
            "workflow_id": task.workflow_id,
            "source": "customer_results_view",
        },
    )


@router.get("/tasks/{task_id}", response_model=AnalysisTaskRead)
def get_task(task_id: str, current: AccountRead = Depends(account_service.require_current_account)) -> AnalysisTaskRead:
    # SEC-P0-01 FIX: Add ownership verification
    return task_service.get_task(task_id, requesting_user_id=current.id)


@router.get("/tasks/{task_id}/artifacts", response_model=list[ArtifactRead])
def get_task_artifacts(task_id: str, current: AccountRead = Depends(account_service.require_current_account)) -> list[ArtifactRead]:
    # SEC-P0-01 FIX: Verify task ownership before returning artifacts
    task = task_service.get_task(task_id, requesting_user_id=current.id)
    task_service.assert_task_artifacts_deliverable(task)
    return task_service.list_task_artifacts(task_id)


@router.post("/tasks/{task_id}/artifacts/batch")
def batch_download_task_artifacts(
    task_id: str,
    current: AccountRead = Depends(account_service.require_current_account)
) -> StreamingResponse:
    """Batch download all artifacts for a task as a ZIP file.
    
    Returns:
        StreamingResponse containing a ZIP archive of all task artifacts
    """
    # Get task to verify it exists and user has access
    task = task_service.get_task(task_id, requesting_user_id=current.id)
    task_service.assert_task_artifacts_deliverable(task)
    
    # Get all artifacts for this task
    artifacts = task_service.list_task_artifacts(task_id)
    
    if not artifacts:
        raise HTTPException(status_code=404, detail="No artifacts found for this task")
    
    # Create in-memory ZIP file
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for artifact in artifacts:
            try:
                if not task_service.is_artifact_download_allowed(artifact, task):
                    continue
                # Validate and resolve path
                artifact_path = _assert_path_within_derivatives(Path(artifact.path))
                
                if not artifact_path.exists() or not artifact_path.is_file():
                    continue
                
                # Add file to ZIP with artifact label as filename
                # Use a safe filename derived from the artifact label
                safe_name = artifact.label.replace("/", "_").replace("\\", "_")
                if not safe_name.endswith(artifact_path.suffix):
                    safe_name += artifact_path.suffix
                
                zip_file.write(artifact_path, arcname=safe_name)
                
            except (ValueError, HTTPException):
                # Skip artifacts that fail path validation
                continue
    
    # Prepare the ZIP for streaming
    zip_buffer.seek(0)
    
    # Generate a meaningful filename
    zip_filename = f"task_{task_id[:8]}_artifacts.zip"
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"'
        }
    )
