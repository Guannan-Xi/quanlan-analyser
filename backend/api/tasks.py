from fastapi import APIRouter

from backend.models.analysis_task import AnalysisTaskCreate, AnalysisTaskRead
from backend.models.artifact import ArtifactRead
from backend.services import task_service

router = APIRouter()


@router.post("/tasks", response_model=AnalysisTaskRead)
def create_task(payload: AnalysisTaskCreate) -> AnalysisTaskRead:
    return task_service.create_task(payload)


@router.get("/tasks/{task_id}", response_model=AnalysisTaskRead)
def get_task(task_id: str) -> AnalysisTaskRead:
    return task_service.get_task(task_id)


@router.get("/tasks/{task_id}/artifacts", response_model=list[ArtifactRead])
def get_task_artifacts(task_id: str) -> list[ArtifactRead]:
    return task_service.list_task_artifacts(task_id)

