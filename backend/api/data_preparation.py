from fastapi import APIRouter

from backend.models.data_preparation import (
    BadChannelAuditCreate,
    BadChannelAuditRead,
    DataPreparationPlanCreate,
    DataPreparationPlanForFileSave,
    DataPreparationPlanRead,
    DataPreparationPlanUpdate,
    DataPreparationTaskReferenceCreate,
    DataPreparationTaskReferenceRead,
    EpochSetCreate,
    EpochSetRead,
    EpochSetUpdate,
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


@router.get("/eeg/files/{file_id}/data-preparation-plan", response_model=DataPreparationPlanRead)
def get_current_data_preparation_plan_for_file(file_id: str) -> DataPreparationPlanRead:
    return data_preparation_service.get_current_plan_for_file(file_id)


@router.post("/eeg/files/{file_id}/data-preparation-plan", response_model=DataPreparationPlanRead)
def save_current_data_preparation_plan_for_file(file_id: str, payload: DataPreparationPlanForFileSave) -> DataPreparationPlanRead:
    return data_preparation_service.save_current_plan_for_file(file_id, payload)


@router.get("/eeg/files/{file_id}/data-preparation-plans", response_model=list[DataPreparationPlanRead])
def list_data_preparation_plans_for_file(file_id: str) -> list[DataPreparationPlanRead]:
    return data_preparation_service.list_plans(input_file_id=file_id)


@router.post("/eeg/files/{file_id}/epoch-sets", response_model=EpochSetRead)
def create_epoch_set_for_file(file_id: str, payload: EpochSetCreate) -> EpochSetRead:
    return data_preparation_service.save_epoch_set_for_file(file_id, payload)


@router.get("/eeg/files/{file_id}/epoch-sets", response_model=list[EpochSetRead])
def list_epoch_sets_for_file(file_id: str) -> list[EpochSetRead]:
    return data_preparation_service.list_epoch_sets(input_file_id=file_id)


@router.get("/epoch-sets/{epoch_set_id}", response_model=EpochSetRead)
def get_epoch_set(epoch_set_id: str) -> EpochSetRead:
    return data_preparation_service.get_epoch_set(epoch_set_id)


@router.put("/epoch-sets/{epoch_set_id}", response_model=EpochSetRead)
def update_epoch_set(epoch_set_id: str, payload: EpochSetUpdate) -> EpochSetRead:
    return data_preparation_service.update_epoch_set(epoch_set_id, payload)


@router.post("/eeg/files/{file_id}/bad-channel-audit", response_model=BadChannelAuditRead)
def save_bad_channel_audit_for_file(file_id: str, payload: BadChannelAuditCreate) -> BadChannelAuditRead:
    return data_preparation_service.save_bad_channel_audit_for_file(file_id, payload)
