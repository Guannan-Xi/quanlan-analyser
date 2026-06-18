from fastapi import APIRouter

from backend.models.data_preparation import (
    DataPreparationPlanCreate,
    DataPreparationPlanRead,
    DataPreparationPlanUpdate,
    DataPreparationTaskReferenceCreate,
    DataPreparationTaskReferenceRead,
)
from backend.services import data_preparation_service

router = APIRouter()


@router.post("/data-preparation/plans", response_model=DataPreparationPlanRead)
def create_data_preparation_plan(payload: DataPreparationPlanCreate) -> DataPreparationPlanRead:
    return data_preparation_service.save_plan(payload)


@router.get("/data-preparation/plans", response_model=list[DataPreparationPlanRead])
def list_data_preparation_plans(project_id: str | None = None, input_file_id: str | None = None) -> list[DataPreparationPlanRead]:
    return data_preparation_service.list_plans(project_id=project_id, input_file_id=input_file_id)


@router.get("/data-preparation/plans/{plan_id}", response_model=DataPreparationPlanRead)
def get_data_preparation_plan(plan_id: str) -> DataPreparationPlanRead:
    return data_preparation_service.get_plan(plan_id)


@router.put("/data-preparation/plans/{plan_id}", response_model=DataPreparationPlanRead)
def update_data_preparation_plan(plan_id: str, payload: DataPreparationPlanUpdate) -> DataPreparationPlanRead:
    return data_preparation_service.update_plan(plan_id, payload)


@router.post("/data-preparation/plans/{plan_id}/task-reference", response_model=DataPreparationTaskReferenceRead)
def create_data_preparation_task_reference(plan_id: str, payload: DataPreparationTaskReferenceCreate) -> DataPreparationTaskReferenceRead:
    return data_preparation_service.create_task_reference(plan_id, payload)
