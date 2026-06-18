from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import HTTPException

from backend.models.data_preparation import (
    DataPreparationPlanCreate,
    DataPreparationPlanForFileSave,
    DataPreparationPlanRead,
    DataPreparationPlanUpdate,
    DataPreparationTaskReferenceCreate,
    DataPreparationTaskReferenceRead,
    SUPPORTED_PLAN_MODULES,
)
from backend.services import state_store, storage_service

ROOT = Path(__file__).resolve().parents[2]
DERIVATIVES_ROOT = Path(os.getenv("QLANALYSER_DERIVATIVES_ROOT", ROOT / "data" / "derivatives"))
REGISTRY = "data_preparation_plans"
CONTRACT_VERSION = "qlanalyser-data-preparation-v0.2"

DEFAULT_ARTIFACT_CONTRACT = {
    "contract_version": CONTRACT_VERSION,
    "scope": "qc_psd_common_data_preparation",
    "required_files": [
        "reproducibility/data_preparation_plan.json",
        "reproducibility/data_preparation_task_reference.json",
        "reproducibility/data_preparation_artifact_contract.json",
        "manifest.json",
    ],
    "task_parameter_keys": [
        "data_preparation_plan_id",
        "data_preparation_revision",
        "data_preparation_contract_version",
    ],
    "allowed_modules": sorted(SUPPORTED_PLAN_MODULES),
}

_plans: dict[str, DataPreparationPlanRead] = state_store.load_registry(REGISTRY, DataPreparationPlanRead)


def _refresh_plans() -> None:
    _plans.clear()
    _plans.update(state_store.load_registry(REGISTRY, DataPreparationPlanRead))


def _plan_root(project_id: str, plan_id: str, revision: int) -> Path:
    return DERIVATIVES_ROOT / project_id / "data_preparation" / plan_id / f"revision_{revision}"


def _json_default(value):
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")


def _merged_contract(plan: DataPreparationPlanRead) -> dict:
    contract = dict(DEFAULT_ARTIFACT_CONTRACT)
    contract.update(plan.artifact_contract_json or {})
    contract["contract_version"] = CONTRACT_VERSION
    contract["allowed_modules"] = sorted(set(plan.module_scope) & SUPPORTED_PLAN_MODULES)
    return contract


def _write_plan_artifacts(plan: DataPreparationPlanRead) -> Path:
    root = _plan_root(plan.project_id, plan.id, plan.revision)
    plan.artifact_root = root
    plan_payload = plan.model_dump(mode="json")
    plan_payload["artifact_root"] = str(root)
    contract = _merged_contract(plan)
    _write_json(root / "reproducibility" / "data_preparation_plan.json", plan_payload)
    _write_json(root / "reproducibility" / "data_preparation_artifact_contract.json", contract)
    _write_json(root / "manifest.json", {
        "contract_version": CONTRACT_VERSION,
        "schema_version": plan.schema_version,
        "plan_id": plan.id,
        "revision": plan.revision,
        "project_id": plan.project_id,
        "input_file_id": plan.input_file_id,
        "scope": plan.scope,
        "status": plan.status,
        "files": contract["required_files"],
    })
    return root


def _revision_conflict(plan_id: str, expected_revision: int, current_revision: int) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "error_code": "PLAN_REVISION_CONFLICT",
            "legacy_error_code": "data_preparation_revision_conflict",
            "plan_id": plan_id,
            "expected_revision": expected_revision,
            "current_revision": current_revision,
        },
    )


def _validate_scope(scope: list[str]) -> list[str]:
    normalized = []
    for item in scope:
        if item not in SUPPORTED_PLAN_MODULES:
            raise HTTPException(status_code=422, detail=f"Unsupported data preparation module scope: {item}")
        if item not in normalized:
            normalized.append(item)
    if not normalized:
        raise HTTPException(status_code=422, detail="Data preparation plan must support at least one module")
    return normalized


def list_plans(project_id: str | None = None, input_file_id: str | None = None) -> list[DataPreparationPlanRead]:
    _refresh_plans()
    values = list(_plans.values())
    if project_id:
        values = [plan for plan in values if plan.project_id == project_id]
    if input_file_id:
        values = [plan for plan in values if plan.input_file_id == input_file_id]
    return sorted(values, key=lambda plan: plan.updated_at, reverse=True)


def get_plan(plan_id: str) -> DataPreparationPlanRead:
    _refresh_plans()
    try:
        return _plans[plan_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Data preparation plan not found") from exc


def get_current_plan_for_file(input_file_id: str) -> DataPreparationPlanRead:
    storage_service.get_eeg_file(input_file_id)
    plans = list_plans(input_file_id=input_file_id)
    if plans:
        return plans[0]
    eeg_file = storage_service.get_eeg_file(input_file_id)
    return DataPreparationPlanRead(
        project_id=eeg_file.project_id,
        input_file_id=input_file_id,
        revision=0,
        is_default=True,
        source_file={
            "file_id": eeg_file.id,
            "original_filename": eeg_file.original_filename,
            "detected_format": eeg_file.detected_format,
        },
        metadata_review={
            "sfreq": eeg_file.sampling_rate,
            "duration_sec": eeg_file.duration_sec,
            "n_channels": eeg_file.channel_count,
        },
    )


def save_plan(payload: DataPreparationPlanCreate) -> DataPreparationPlanRead:
    eeg_file = storage_service.get_eeg_file(payload.input_file_id)
    if eeg_file.project_id != payload.project_id:
        raise HTTPException(status_code=422, detail="Data preparation plan project_id must match the EEG file project_id")
    scope = _validate_scope(list(payload.module_scope))
    plan = DataPreparationPlanRead(
        project_id=payload.project_id,
        input_file_id=payload.input_file_id,
        schema_version=payload.schema_version,
        scope=payload.scope,
        status=payload.status,
        module_scope=scope,
        title=payload.title,
        description=payload.description,
        source_file=payload.source_file,
        metadata_review=payload.metadata_review,
        preprocessing_json=payload.preprocessing_json,
        qc_json=payload.qc_json,
        psd_json=payload.psd_json,
        channel_types=payload.channel_types,
        channel_renames=payload.channel_renames,
        bad_channels=payload.bad_channels,
        bad_segments=payload.bad_segments,
        annotation_actions=payload.annotation_actions,
        saved_preview_segments=payload.saved_preview_segments,
        next_step_recommendation=payload.next_step_recommendation,
        warnings=payload.warnings,
        artifact_contract_json=payload.artifact_contract_json,
    )
    _write_plan_artifacts(plan)
    _plans[plan.id] = plan
    state_store.upsert_item(REGISTRY, plan)
    return plan


def save_current_plan_for_file(input_file_id: str, payload: DataPreparationPlanForFileSave) -> DataPreparationPlanRead:
    eeg_file = storage_service.get_eeg_file(input_file_id)
    if eeg_file.project_id != payload.project_id:
        raise HTTPException(status_code=422, detail="Data preparation plan project_id must match the EEG file project_id")
    current_plans = list_plans(project_id=payload.project_id, input_file_id=input_file_id)
    current_plan = current_plans[0] if current_plans else None
    expected_revision = payload.expected_revision
    if current_plan is None:
        if expected_revision not in (None, 0):
            raise _revision_conflict(f"default:{input_file_id}", expected_revision, 0)
        return save_plan(DataPreparationPlanCreate(input_file_id=input_file_id, **payload.model_dump()))
    if expected_revision is None:
        raise HTTPException(status_code=422, detail="base_revision or expected_revision is required when updating an existing data preparation plan")
    update_payload = DataPreparationPlanUpdate(**payload.model_dump(exclude={"project_id", "expected_revision"}), expected_revision=expected_revision)
    return update_plan(current_plan.id, update_payload)


def update_plan(plan_id: str, payload: DataPreparationPlanUpdate) -> DataPreparationPlanRead:
    plan = get_plan(plan_id)
    if payload.expected_revision != plan.revision:
        raise _revision_conflict(plan_id, payload.expected_revision, plan.revision)
    updates = payload.model_dump(exclude_unset=True)
    updates.pop("expected_revision", None)
    for key, value in updates.items():
        if key == "module_scope" and value is not None:
            value = _validate_scope(list(value))
        setattr(plan, key, value)
    plan.revision += 1
    from backend.models.base import utc_now
    plan.updated_at = utc_now()
    _write_plan_artifacts(plan)
    _plans[plan.id] = plan
    state_store.upsert_item(REGISTRY, plan)
    return plan


def assert_plan_revision(plan_id: str, expected_revision: int, module_name: str | None = None) -> DataPreparationPlanRead:
    plan = get_plan(plan_id)
    if expected_revision != plan.revision:
        raise _revision_conflict(plan_id, expected_revision, plan.revision)
    if module_name and module_name not in plan.module_scope:
        raise HTTPException(status_code=422, detail=f"Data preparation plan does not support module: {module_name}")
    return plan


def create_task_reference(plan_id: str, payload: DataPreparationTaskReferenceCreate) -> DataPreparationTaskReferenceRead:
    plan = assert_plan_revision(plan_id, payload.expected_revision, payload.module_name)
    root = plan.artifact_root or _plan_root(plan.project_id, plan.id, plan.revision)
    contract = _merged_contract(plan)
    parameters_json = {
        "data_preparation_plan_id": plan.id,
        "data_preparation_revision": plan.revision,
        "data_preparation_contract_version": CONTRACT_VERSION,
    }
    reference = DataPreparationTaskReferenceRead(
        plan_id=plan.id,
        revision=plan.revision,
        project_id=plan.project_id,
        input_file_id=plan.input_file_id,
        module_name=payload.module_name,
        workflow_id=payload.workflow_id,
        task_id=payload.task_id,
        parameters_json=parameters_json,
        artifact_contract_json=contract,
        artifact_root=root,
    )
    _write_json(root / "reproducibility" / "data_preparation_task_reference.json", reference.model_dump(mode="json"))
    return reference


def validate_task_parameters(module_name: str, parameters_json: dict) -> DataPreparationPlanRead | None:
    plan_id = parameters_json.get("data_preparation_plan_id")
    revision = parameters_json.get("data_preparation_revision")
    if not plan_id and revision is None:
        return None
    if not plan_id or revision is None:
        raise HTTPException(status_code=422, detail="Both data_preparation_plan_id and data_preparation_revision are required")
    if module_name not in SUPPORTED_PLAN_MODULES:
        raise HTTPException(status_code=422, detail=f"Data preparation plan is only supported for QC/PSD tasks, not: {module_name}")
    try:
        expected_revision = int(revision)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="data_preparation_revision must be an integer") from exc
    plan = assert_plan_revision(str(plan_id), expected_revision, module_name)
    parameters_json.setdefault("data_preparation_contract_version", CONTRACT_VERSION)
    return plan
