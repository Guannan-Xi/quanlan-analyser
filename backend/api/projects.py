from fastapi import APIRouter, Depends, HTTPException

from backend.models.governance import AccountRead
from backend.models.project import ProjectCreate, ProjectRead, ProjectUpdate
from backend.services import account_service, storage_service

router = APIRouter()

# Teaching/learning projects are public read-only demos.
_TEACHING_PROJECT_IDS = {"proj_demo_learning", "proj_demo_epilepsy_lab"}


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
    return storage_service.list_projects()


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, current: AccountRead = Depends(account_service.require_current_account)) -> ProjectRead:
    return storage_service.get_project(project_id)


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
