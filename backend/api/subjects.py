from fastapi import APIRouter

from backend.models.subject import SubjectCreate, SubjectRead
from backend.services import storage_service

router = APIRouter()


@router.post("/projects/{project_id}/subjects", response_model=SubjectRead)
def create_subject(project_id: str, payload: SubjectCreate) -> SubjectRead:
    return storage_service.create_subject(project_id, payload)


@router.get("/projects/{project_id}/subjects", response_model=list[SubjectRead])
def list_subjects(project_id: str) -> list[SubjectRead]:
    return storage_service.list_subjects(project_id)

