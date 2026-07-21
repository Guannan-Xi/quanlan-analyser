from fastapi import APIRouter, Depends, HTTPException

from backend.models.eeg_file import EEGFileRead
from backend.models.governance import AccountRead
from backend.models.public_api import (
    BadChannelAuditPublicRead,
    DataPreparationPlanPublicRead,
    DataPreparationTaskReferencePublicRead,
    EpochSetPublicRead,
    bad_channel_audit_to_public,
    epoch_set_to_public,
    plan_to_public,
    task_reference_to_public,
)
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
from backend.services import account_service, data_preparation_service, data_source_policy, storage_service

router = APIRouter()


def _requesting_user_id(current: AccountRead) -> str | None:
    return None if current.role == "admin" else current.id


def _assert_file_access(file_id: str, current: AccountRead) -> EEGFileRead:
    eeg_file = storage_service.get_eeg_file(file_id, requesting_user_id=_requesting_user_id(current))
    if current.role != "admin" and data_source_policy.is_protected_teaching_file(eeg_file):
        raise HTTPException(status_code=403, detail="Teaching/demo EEG files are only available through the lab demo sandbox")
    return eeg_file


def _plan_visible_to_current(plan: DataPreparationPlanRead, current: AccountRead) -> bool:
    return current.role == "admin" or plan.owner_user_id == current.id


def _epoch_visible_to_current(epoch_set: EpochSetRead, current: AccountRead) -> bool:
    return current.role == "admin" or epoch_set.owner_user_id == current.id


def _owner_for_file(eeg_file: EEGFileRead, current: AccountRead) -> str:
    return eeg_file.owner_user_id if current.role == "admin" else current.id


@router.post("/data-preparation/plans", response_model=DataPreparationPlanPublicRead)
def create_data_preparation_plan(
    payload: DataPreparationPlanCreate,
    current: AccountRead = Depends(account_service.require_current_account),
) -> DataPreparationPlanPublicRead:
    eeg_file = _assert_file_access(payload.input_file_id, current)
    owned_payload = payload.model_copy(
        update={
            "organization_id": eeg_file.organization_id,
            "project_id": eeg_file.project_id,
            "owner_user_id": _owner_for_file(eeg_file, current),
            "created_by": current.id,
        }
    )
    return plan_to_public(data_preparation_service.save_plan(owned_payload))


@router.get("/data-preparation/plans", response_model=list[DataPreparationPlanPublicRead])
def list_data_preparation_plans(
    project_id: str | None = None,
    input_file_id: str | None = None,
    current: AccountRead = Depends(account_service.require_current_account),
) -> list[DataPreparationPlanPublicRead]:
    if input_file_id:
        _assert_file_access(input_file_id, current)
    plans = data_preparation_service.list_plans(
        project_id=project_id,
        input_file_id=input_file_id,
        owner_user_id=_requesting_user_id(current),
    )
    return [plan_to_public(plan) for plan in plans if _plan_visible_to_current(plan, current)]


@router.get("/data-preparation/plans/{plan_id}", response_model=DataPreparationPlanPublicRead)
def get_data_preparation_plan(
    plan_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> DataPreparationPlanPublicRead:
    plan = data_preparation_service.get_plan(plan_id, requesting_user_id=_requesting_user_id(current))
    return plan_to_public(plan)


@router.put("/data-preparation/plans/{plan_id}", response_model=DataPreparationPlanPublicRead)
def update_data_preparation_plan(
    plan_id: str,
    payload: DataPreparationPlanUpdate,
    current: AccountRead = Depends(account_service.require_current_account),
) -> DataPreparationPlanPublicRead:
    plan = data_preparation_service.get_plan(plan_id, requesting_user_id=_requesting_user_id(current))
    owned_payload = payload.model_copy(update={"owner_user_id": plan.owner_user_id, "updated_by": current.id})
    return plan_to_public(data_preparation_service.update_plan(plan_id, owned_payload, requesting_user_id=_requesting_user_id(current)))


@router.post("/data-preparation/plans/{plan_id}/task-reference", response_model=DataPreparationTaskReferencePublicRead)
def create_data_preparation_task_reference(
    plan_id: str,
    payload: DataPreparationTaskReferenceCreate,
    current: AccountRead = Depends(account_service.require_current_account),
) -> DataPreparationTaskReferencePublicRead:
    data_preparation_service.get_plan(plan_id, requesting_user_id=_requesting_user_id(current))
    return task_reference_to_public(data_preparation_service.create_task_reference(plan_id, payload, requesting_user_id=_requesting_user_id(current)))


@router.get("/eeg/files/{file_id}/data-preparation-plan", response_model=DataPreparationPlanPublicRead)
def get_current_data_preparation_plan_for_file(
    file_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> DataPreparationPlanPublicRead:
    _assert_file_access(file_id, current)
    return plan_to_public(data_preparation_service.get_current_plan_for_file(file_id, requesting_user_id=_requesting_user_id(current)))


@router.post("/eeg/files/{file_id}/data-preparation-plan", response_model=DataPreparationPlanPublicRead)
def save_current_data_preparation_plan_for_file(
    file_id: str,
    payload: DataPreparationPlanForFileSave,
    current: AccountRead = Depends(account_service.require_current_account),
) -> DataPreparationPlanPublicRead:
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
    return plan_to_public(
        data_preparation_service.save_current_plan_for_file(
            file_id,
            owned_payload,
            requesting_user_id=_requesting_user_id(current),
        )
    )


@router.get("/eeg/files/{file_id}/data-preparation-plans", response_model=list[DataPreparationPlanPublicRead])
def list_data_preparation_plans_for_file(
    file_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> list[DataPreparationPlanPublicRead]:
    _assert_file_access(file_id, current)
    return [
        plan_to_public(plan) for plan in data_preparation_service.list_plans(
        input_file_id=file_id,
        owner_user_id=_requesting_user_id(current),
        )
    ]


@router.post("/eeg/files/{file_id}/epoch-sets", response_model=EpochSetPublicRead)
def create_epoch_set_for_file(
    file_id: str,
    payload: EpochSetCreate,
    current: AccountRead = Depends(account_service.require_current_account),
) -> EpochSetPublicRead:
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
    return epoch_set_to_public(
        data_preparation_service.save_epoch_set_for_file(
            file_id,
            owned_payload,
            requesting_user_id=_requesting_user_id(current),
        )
    )


@router.get("/eeg/files/{file_id}/epoch-sets", response_model=list[EpochSetPublicRead])
def list_epoch_sets_for_file(
    file_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> list[EpochSetPublicRead]:
    _assert_file_access(file_id, current)
    return [
        epoch_set_to_public(epoch_set) for epoch_set in data_preparation_service.list_epoch_sets(
            input_file_id=file_id,
            owner_user_id=_requesting_user_id(current),
        )
    ]


@router.get("/epoch-sets/{epoch_set_id}", response_model=EpochSetPublicRead)
def get_epoch_set(
    epoch_set_id: str,
    current: AccountRead = Depends(account_service.require_current_account),
) -> EpochSetPublicRead:
    epoch_set = data_preparation_service.get_epoch_set(epoch_set_id, requesting_user_id=_requesting_user_id(current))
    _assert_file_access(epoch_set.input_file_id, current)
    return epoch_set_to_public(epoch_set)


@router.put("/epoch-sets/{epoch_set_id}", response_model=EpochSetPublicRead)
def update_epoch_set(
    epoch_set_id: str,
    payload: EpochSetUpdate,
    current: AccountRead = Depends(account_service.require_current_account),
) -> EpochSetPublicRead:
    epoch_set = data_preparation_service.get_epoch_set(epoch_set_id, requesting_user_id=_requesting_user_id(current))
    _assert_file_access(epoch_set.input_file_id, current)
    owned_payload = payload.model_copy(update={"updated_by": current.id})
    return epoch_set_to_public(
        data_preparation_service.update_epoch_set(
            epoch_set_id,
            owned_payload,
            requesting_user_id=_requesting_user_id(current),
        )
    )


@router.post("/eeg/files/{file_id}/bad-channel-audit", response_model=BadChannelAuditPublicRead)
def save_bad_channel_audit_for_file(
    file_id: str,
    payload: BadChannelAuditCreate,
    current: AccountRead = Depends(account_service.require_current_account),
) -> BadChannelAuditPublicRead:
    eeg_file = _assert_file_access(file_id, current)
    owned_payload = payload.model_copy(
        update={
            "organization_id": eeg_file.organization_id,
            "project_id": eeg_file.project_id,
            "input_file_id": file_id,
            "actor_user_id": current.id,
        }
    )
    return bad_channel_audit_to_public(
        data_preparation_service.save_bad_channel_audit_for_file(
            file_id,
            owned_payload,
            requesting_user_id=_requesting_user_id(current),
        )
    )
