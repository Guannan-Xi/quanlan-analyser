from fastapi import APIRouter, Depends

from backend.models.analysis_task import AnalysisTaskCreate, AnalysisTaskRead
from backend.models.artifact import ArtifactRead
from backend.models.governance import AccountRead
from backend.services import account_service, task_service

router = APIRouter()


@router.post("/tasks", response_model=AnalysisTaskRead)
def create_task(payload: AnalysisTaskCreate, current: AccountRead = Depends(account_service.require_current_account)) -> AnalysisTaskRead:
    return task_service.create_task(payload)


@router.get("/tasks/{task_id}", response_model=AnalysisTaskRead)
def get_task(task_id: str, current: AccountRead = Depends(account_service.require_current_account)) -> AnalysisTaskRead:
    return task_service.get_task(task_id)


@router.get("/tasks/{task_id}/artifacts", response_model=list[ArtifactRead])
def get_task_artifacts(task_id: str, current: AccountRead = Depends(account_service.require_current_account)) -> list[ArtifactRead]:
    return task_service.list_task_artifacts(task_id)
