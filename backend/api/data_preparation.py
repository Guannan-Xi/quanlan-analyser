from fastapi import APIRouter, Depends

from backend.models.eeg_file import EEGFileRead
from backend.models.governance import AccountRead
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
from backend.services import account_service, data_preparation_service, storage_service

router = APIRouter()


def _requesting_user_id(current: AccountRead) -> str | None:
    return None if current.role == "admin" else current.id


def _assert_file_access(file_id: str, current: AccountRead) -> EEGFileRead:
    return storage_service.get_eeg_file(file_id, requesting_user_id=_requesting_user_id(current))


def _plan_visible_to_current(plan: DataPreparationPlanRead, current: AccountRead) -> bool:
    if current.role == "admin" or plan.owner_user_id == current.id:
        return True
    try:
        _assert_file_access(plan.input_file_id, current)
        return True
    except Exception:
        return False


def _epoch_visible_to_current(epoch_set: EpochSetRead, current: AccountRead) -> bool:
    if current.role == "admin" or epoch_set.owner_user_id == current.id:
        return True
    try:
        _assert_file_access(epoch_set.input_file_id, current)
        return True
    except Exception:
        return False


def _owner_for_file(eeg_file: EEGFileRead, current: AccountRead) -> str:
    return eeg_file.owner_user_id if current.role == "admin" else current.id


@router.post("/data-preparation/plans", response_model=DataPreparationPlanRead)
def create_data_preparation_plan(
    payload: DataPreparationPlanCreate,
    current: AccountRead = Depends(account_service.require_current_account),
) -> DataPreparationPlanRead:
    eeg_file = _assert_file_access(payload.input_file_id, current)
    owned_payload = payload.model_copy(
        update={
            "organization_id": eeg_file.organization_id,
            "project_id": eeg_file.project_id,
            "owner_user_id": _owner_for_file(eeg_file, current),
            "created_by": current.id,
        }
    )
    return data_preparation_service.save_plan(owned_payload)


@router.get("/data-preparation/plans", response_model=list[DataPreparationPlanRead])
def list_data_preparation_plans(
    project_id: str | None = None,
    input_file_id: str | None = None,
    current: AccountRead = Depends(account_service.require_current_account),
) -> list[DataPreparationPlanRead]:
    if input_file_id:
        _assert_file_access(input_file_id, current)
    plans = data_preparation_service.list_plans(project_id=project_id, input_file_id=input_file_id)
    return [plan for plan in plans if _plan_visible_to_current(plan, current)]


@router.get("/data-preparation/plans/{plan_id}", response_model=DataPreparationPlanRead)
def get_data_preparation_plan(
    plan_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> DataPreparationPlanRead:
    plan = data_preparation_service.get_plan(plan_id)
    _assert_file_access(plan.input_file_id, current)
    return plan


@router.put("/data-preparation/plans/{plan_id}", response_model=DataPreparationPlanRead)
def update_data_preparation_plan(
    plan_id: str,
    payload: DataPreparationPlanUpdate,
    current: AccountRead = Depends(account_service.require_current_account),
) -> DataPreparationPlanRead:
    plan = data_preparation_service.get_plan(plan_id)
    _assert_file_access(plan.input_file_id, current)
    owned_payload = payload.model_copy(update={"owner_user_id": plan.owner_user_id, "updated_by": current.id})
    return data_preparation_service.update_plan(plan_id, owned_payload)


@router.post("/data-preparation/plans/{plan_id}/task-reference", response_model=DataPreparationTaskReferenceRead)
def create_data_preparation_task_reference(
    plan_id: str,
    payload: DataPreparationTaskReferenceCreate,
    current: AccountRead = Depends(account_service.require_current_account),
) -> DataPreparationTaskReferenceRead:
    plan = data_preparation_service.get_plan(plan_id)
    _assert_file_access(plan.input_file_id, current)
    return data_preparation_service.create_task_reference(plan_id, payload)


@router.get("/eeg/files/{file_id}/data-preparation-plan", response_model=DataPreparationPlanRead)
def get_current_data_preparation_plan_for_file(
    file_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> DataPreparationPlanRead:
    _assert_file_access(file_id, current)
    return data_preparation_service.get_current_plan_for_file(file_id)


@router.post("/eeg/files/{file_id}/data-preparation-plan", response_model=DataPreparationPlanRead)
def save_current_data_preparation_plan_for_file(
    file_id: str,
    payload: DataPreparationPlanForFileSave,
    current: AccountRead = Depends(account_service.require_current_account),
) -> DataPreparationPlanRead:
    eeg_file = _assert_file_access(file_id, current)
    owned_payload = payload.model_copy(
        update={
            "organization_id": eeg_file.organization_id,
            "project_id": eeg_file.project_id,
            "owner_user_id": _owner_for_file(eeg_file, current),
            "created_by": current.id,
            "updated_by": current.id,
        }
    )
    return data_preparation_service.save_current_plan_for_file(file_id, owned_payload)


@router.get("/eeg/files/{file_id}/data-preparation-plans", response_model=list[DataPreparationPlanRead])
def list_data_preparation_plans_for_file(
    file_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> list[DataPreparationPlanRead]:
    _assert_file_access(file_id, current)
    return data_preparation_service.list_plans(input_file_id=file_id)


@router.post("/eeg/files/{file_id}/epoch-sets", response_model=EpochSetRead)
def create_epoch_set_for_file(
    file_id: str,
    payload: EpochSetCreate,
    current: AccountRead = Depends(account_service.require_current_account),
) -> EpochSetRead:
    eeg_file = _assert_file_access(file_id, current)
    owned_payload = payload.model_copy(
        update={
            "organization_id": eeg_file.organization_id,
            "project_id": eeg_file.project_id,
            "input_file_id": file_id,
            "owner_user_id": _owner_for_file(eeg_file, current),
            "created_by": current.id,
        }
    )
    return data_preparation_service.save_epoch_set_for_file(file_id, owned_payload)


@router.get("/eeg/files/{file_id}/epoch-sets", response_model=list[EpochSetRead])
def list_epoch_sets_for_file(
    file_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> list[EpochSetRead]:
    _assert_file_access(file_id, current)
    return data_preparation_service.list_epoch_sets(input_file_id=file_id)


@router.get("/epoch-sets/{epoch_set_id}", response_model=EpochSetRead)
def get_epoch_set(
    epoch_set_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> EpochSetRead:
    epoch_set = data_preparation_service.get_epoch_set(epoch_set_id)
    _assert_file_access(epoch_set.input_file_id, current)
    return epoch_set


@router.put("/epoch-sets/{epoch_set_id}", response_model=EpochSetRead)
def update_epoch_set(
    epoch_set_id: str,
    payload: EpochSetUpdate,
    current: AccountRead = Depends(account_service.require_current_account),
) -> EpochSetRead:
    epoch_set = data_preparation_service.get_epoch_set(epoch_set_id)
    _assert_file_access(epoch_set.input_file_id, current)
    owned_payload = payload.model_copy(update={"updated_by": current.id})
    return data_preparation_service.update_epoch_set(epoch_set_id, owned_payload)


@router.post("/eeg/files/{file_id}/bad-channel-audit", response_model=BadChannelAuditRead)
def save_bad_channel_audit_for_file(
    file_id: str,
    payload: BadChannelAuditCreate,
    current: AccountRead = Depends(account_service.require_current_account),
) -> BadChannelAuditRead:
    eeg_file = _assert_file_access(file_id, current)
    owned_payload = payload.model_copy(
        update={
            "organization_id": eeg_file.organization_id,
            "project_id": eeg_file.project_id,
            "input_file_id": file_id,
            "actor_user_id": current.id,
        }
    )
    return data_preparation_service.save_bad_channel_audit_for_file(file_id, owned_payload)
