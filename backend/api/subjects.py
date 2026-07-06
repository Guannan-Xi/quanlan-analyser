from fastapi import APIRouter, Depends

from backend.models.governance import AccountRead
from backend.models.subject import SubjectCreate, SubjectRead
from backend.services import account_service, storage_service

router = APIRouter()


def _requesting_user_id(current: AccountRead) -> str | None:
    return None if current.role == "admin" else current.id


@router.post("/projects/{project_id}/subjects", response_model=SubjectRead)
def create_subject(
    project_id: str,
    payload: SubjectCreate,
    current: AccountRead = Depends(account_service.require_current_account),
) -> SubjectRead:
    return storage_service.create_subject(
        project_id,
        payload,
        requesting_user_id=_requesting_user_id(current),
    )


@router.get("/projects/{project_id}/subjects", response_model=list[SubjectRead])
def list_subjects(
    project_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> list[SubjectRead]:
    return storage_service.list_subjects(project_id, requesting_user_id=_requesting_user_id(current))
