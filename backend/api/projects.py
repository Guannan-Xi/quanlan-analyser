from fastapi import APIRouter

from backend.models.project import ProjectCreate, ProjectRead, ProjectUpdate
from backend.services import storage_service

router = APIRouter()


@router.post("/projects", response_model=ProjectRead)
def create_project(payload: ProjectCreate) -> ProjectRead:
    return storage_service.create_project(payload)


@router.get("/projects", response_model=list[ProjectRead])
def list_projects() -> list[ProjectRead]:
    return storage_service.list_projects()


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: str) -> ProjectRead:
    return storage_service.get_project(project_id)


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: str, payload: ProjectUpdate) -> ProjectRead:
    return storage_service.update_project(project_id, payload)


@router.post("/projects/{project_id}/archive", response_model=ProjectRead)
def archive_project(project_id: str) -> ProjectRead:
    return storage_service.archive_project(project_id)
