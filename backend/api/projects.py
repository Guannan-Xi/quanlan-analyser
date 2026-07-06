import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.models.governance import AccountRead
from backend.models.project import ProjectCreate, ProjectRead, ProjectUpdate
from backend.services import account_service, storage_service, task_service

router = APIRouter()

# Teaching/learning projects are public read-only demos.
_TEACHING_PROJECT_IDS = {"proj_demo_learning", "proj_demo_epilepsy_lab"}

_DERIVATIVES_ROOT = (Path(__file__).resolve().parents[2] / "data" / "derivatives").resolve()


def _assert_path_within_derivatives(raw_path: Path) -> Path:
    """Defense-in-depth: ensure resolved artifact path stays inside derivatives root."""
    resolved = raw_path.resolve()
    try:
        resolved.relative_to(_DERIVATIVES_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Artifact path is outside the allowed directory") from exc
    return resolved


def _require_project_mutate(project_id: str, current: AccountRead) -> ProjectRead:
    """Enforce owner/admin authz on mutation endpoints only (update/archive/delete).
    Read endpoints remain open so customers can browse all data in V01 sandbox."""
    project = storage_service.get_project(project_id)
    if project.id in _TEACHING_PROJECT_IDS:
        raise HTTPException(status_code=409, detail="Teaching projects are protected and cannot be modified")
    if current.role != "admin" and getattr(project, "owner_user_id", None) != current.id:
        raise HTTPException(status_code=403, detail="You do not have permission to modify this project")
    return project


@router.post("/projects", response_model=ProjectRead)
def create_project(payload: ProjectCreate, current: AccountRead = Depends(account_service.require_current_account)) -> ProjectRead:
    if not (payload.name or "").strip():
        raise HTTPException(status_code=422, detail="Project name is required")
    payload.owner_user_id = current.id
    payload.created_by = current.id
    return storage_service.create_project(payload)


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(current: AccountRead = Depends(account_service.require_current_account)) -> list[ProjectRead]:
    # SEC-P0-02 FIX: Filter projects by user ownership
    if current.role == "admin":
        return storage_service.list_projects()
    # Non-admin users only see their own projects
    all_projects = storage_service.list_projects()
    return [p for p in all_projects if getattr(p, "owner_user_id", None) == current.id or p.id in _TEACHING_PROJECT_IDS]


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, current: AccountRead = Depends(account_service.require_current_account)) -> ProjectRead:
    project = storage_service.get_project(project_id)
    # SEC-P0-01 FIX: Verify user has access to this project
    if current.role != "admin" and getattr(project, "owner_user_id", None) != current.id and project.id not in _TEACHING_PROJECT_IDS:
        raise HTTPException(status_code=403, detail="You do not have permission to access this project")
    return project


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: str, payload: ProjectUpdate, current: AccountRead = Depends(account_service.require_current_account)) -> ProjectRead:
    _require_project_mutate(project_id, current)
    return storage_service.update_project(project_id, payload)


@router.post("/projects/{project_id}/archive", response_model=ProjectRead)
def archive_project(project_id: str, current: AccountRead = Depends(account_service.require_current_account)) -> ProjectRead:
    _require_project_mutate(project_id, current)
    return storage_service.archive_project(project_id)


@router.delete("/projects/{project_id}", response_model=ProjectRead)
def delete_project(project_id: str, current: AccountRead = Depends(account_service.require_current_account)) -> ProjectRead:
    _require_project_mutate(project_id, current)
    return storage_service.delete_project(project_id)


@router.post("/projects/{project_id}/tasks/{task_id}/artifacts/batch")
def batch_download_project_task_artifacts(
    project_id: str,
    task_id: str,
    current: AccountRead = Depends(account_service.require_current_account)
) -> StreamingResponse:
    """Batch download all artifacts for a task as a ZIP file.
    
    Args:
        project_id: Project ID (for REST resource hierarchy)
        task_id: Task ID to download artifacts from
        current: Current authenticated user
        
    Returns:
        StreamingResponse containing a ZIP archive of all task artifacts
    """
    # Verify project exists and user has access
    storage_service.get_project(project_id)
    
    # Get task to verify it exists and user has access
    task = task_service.get_task(task_id, requesting_user_id=current.id)
    task_service.assert_task_artifacts_deliverable(task)
    
    # Verify task belongs to the specified project
    if task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found in this project")
    
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
