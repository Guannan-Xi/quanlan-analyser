from __future__ import annotations

import json
import os
import hashlib
from pathlib import Path

from fastapi import HTTPException

from backend.models.data_preparation import (
    BadChannelAuditCreate,
    BadChannelAuditRead,
    DataPreparationPlanCreate,
    DataPreparationPlanForFileSave,
    DataPreparationPlanRead,
    DataPreparationPlanUpdate,
    DataPreparationTaskReferenceCreate,
    DataPreparationTaskReferenceRead,
    DEFAULT_PLAN_MODULE_SCOPE,
    EpochSetCreate,
    EpochSetRead,
    EpochSetUpdate,
    SUPPORTED_PLAN_MODULES,
)
from backend.services import audit_service, object_storage_service, state_store, storage_service

ROOT = Path(__file__).resolve().parents[2]
DERIVATIVES_ROOT = Path(os.getenv("QLANALYSER_DERIVATIVES_ROOT", ROOT / "data" / "derivatives"))
REGISTRY = "data_preparation_plans"
EPOCH_SET_REGISTRY = "epoch_sets"
CONTRACT_VERSION = "qlanalyser-data-preparation-v0.2"
EPOCH_SET_CONTRACT_VERSION = "qlanalyser-epoch-set-v0.1"
LEGACY_DEFAULT_PLAN_MODULE_SCOPE = {"qc", "psd", "erp", "tfr", "pac", "reference_csd"}

DEFAULT_ARTIFACT_CONTRACT = {
    "contract_version": CONTRACT_VERSION,
    "scope": "common_analysis_data_preparation",
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
_epoch_sets: dict[str, EpochSetRead] = state_store.load_registry(EPOCH_SET_REGISTRY, EpochSetRead)


def _refresh_plans() -> None:
    _plans.clear()
    loaded = state_store.load_registry(REGISTRY, DataPreparationPlanRead)
    _plans.update({key: _normalize_legacy_default_scope(plan) for key, plan in loaded.items()})


def _refresh_epoch_sets() -> None:
    _epoch_sets.clear()
    _epoch_sets.update(state_store.load_registry(EPOCH_SET_REGISTRY, EpochSetRead))


def _plan_root(project_id: str, plan_id: str, revision: int) -> Path:
    return DERIVATIVES_ROOT / project_id / "data_preparation" / plan_id / f"revision_{revision}"


def _epoch_set_root(project_id: str, epoch_set_id: str, revision: int) -> Path:
    return DERIVATIVES_ROOT / project_id / "epoch_sets" / epoch_set_id / f"revision_{revision}"


def _json_default(value):
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")


def _file_sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _channels_tsv_path_from_plan(plan: DataPreparationPlanRead) -> Path | None:
    source_file = plan.source_file or {}
    for key in ("channels_tsv_path", "bids_channels_tsv_path", "source_channels_tsv_path"):
        value = source_file.get(key)
        if value:
            return Path(str(value))
    return None


def _bad_channel_source_integrity_snapshot(eeg_file, plan: DataPreparationPlanRead) -> dict:
    object_stat = {
        "object_key": eeg_file.object_key,
        "sha256": eeg_file.sha256,
        "size_bytes": eeg_file.size_bytes,
        "modified_at": None,
        "storage_backend": None,
        "stat_available": False,
    }
    if eeg_file.object_key:
        try:
            current_stat = object_storage_service.stat(eeg_file.object_key)
            object_stat.update({
                "sha256": current_stat.get("sha256"),
                "size_bytes": current_stat.get("size_bytes"),
                "modified_at": current_stat.get("modified_at"),
                "storage_backend": current_stat.get("storage_backend"),
                "stat_available": True,
            })
        except Exception as exc:
            object_stat["stat_error"] = str(exc)

    channels_tsv_path = _channels_tsv_path_from_plan(plan)
    channels_tsv_exists = bool(channels_tsv_path and channels_tsv_path.exists())
    return {
        "source_eeg_object": object_stat,
        "source_channels_tsv": {
            "path": str(channels_tsv_path) if channels_tsv_path else None,
            "exists": channels_tsv_exists,
            "sha256": _file_sha256(channels_tsv_path) if channels_tsv_exists and channels_tsv_path else None,
            "size_bytes": channels_tsv_path.stat().st_size if channels_tsv_exists and channels_tsv_path else None,
            "modified_at": channels_tsv_path.stat().st_mtime if channels_tsv_exists and channels_tsv_path else None,
        },
    }


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


def _normalize_legacy_default_scope(plan: DataPreparationPlanRead) -> DataPreparationPlanRead:
    current_scope = set(plan.module_scope or [])
    if current_scope == LEGACY_DEFAULT_PLAN_MODULE_SCOPE:
        plan.module_scope = list(DEFAULT_PLAN_MODULE_SCOPE)
        _write_plan_artifacts(plan)
        state_store.upsert_item(REGISTRY, plan)
    return plan


def _epoch_contract(epoch_set: EpochSetRead) -> dict:
    contract = {
        "contract_version": EPOCH_SET_CONTRACT_VERSION,
        "scope": "event_epoch_persistent_manifest",
        "required_files": [
            "reproducibility/epoch_set_manifest.json",
            "reproducibility/epoch_set_artifact_contract.json",
            "manifest.json",
        ],
        "task_parameter_keys": [
            "epoch_set_id",
            "epoch_set_revision",
            "epoch_set_contract_version",
        ],
        "boundary": epoch_set.boundary,
    }
    contract.update(epoch_set.artifact_contract_json or {})
    contract["contract_version"] = EPOCH_SET_CONTRACT_VERSION
    return contract


def _epoch_manifest_payload(epoch_set: EpochSetRead) -> dict:
    payload = epoch_set.model_dump(mode="json")
    payload["epoch_set_id"] = epoch_set.id
    payload["artifact_root"] = str(epoch_set.artifact_root) if epoch_set.artifact_root else None
    payload["contract_version"] = EPOCH_SET_CONTRACT_VERSION
    return payload


def _write_epoch_set_artifacts(epoch_set: EpochSetRead) -> Path:
    root = _epoch_set_root(epoch_set.project_id, epoch_set.id, epoch_set.revision)
    epoch_set.artifact_root = root
    contract = _epoch_contract(epoch_set)
    manifest_payload = _epoch_manifest_payload(epoch_set)
    _write_json(root / "reproducibility" / "epoch_set_manifest.json", manifest_payload)
    _write_json(root / "reproducibility" / "epoch_set_artifact_contract.json", contract)
    _write_json(root / "manifest.json", {
        "contract_version": EPOCH_SET_CONTRACT_VERSION,
        "schema_version": epoch_set.schema_version,
        "epoch_set_id": epoch_set.id,
        "revision": epoch_set.revision,
        "project_id": epoch_set.project_id,
        "input_file_id": epoch_set.input_file_id,
        "status": epoch_set.status,
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
        organization_id=eeg_file.organization_id,
        project_id=eeg_file.project_id,
        input_file_id=input_file_id,
        owner_user_id=eeg_file.owner_user_id,
        created_by=eeg_file.created_by,
        quota_account_id=eeg_file.quota_account_id,
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


def list_epoch_sets(project_id: str | None = None, input_file_id: str | None = None) -> list[EpochSetRead]:
    _refresh_epoch_sets()
    values = list(_epoch_sets.values())
    if project_id:
        values = [epoch_set for epoch_set in values if epoch_set.project_id == project_id]
    if input_file_id:
        values = [epoch_set for epoch_set in values if epoch_set.input_file_id == input_file_id]
    return sorted(values, key=lambda epoch_set: epoch_set.updated_at, reverse=True)


def get_epoch_set(epoch_set_id: str) -> EpochSetRead:
    _refresh_epoch_sets()
    try:
        return _epoch_sets[epoch_set_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Epoch set not found") from exc


def _validate_epoch_set_payload(input_file_id: str, payload: EpochSetCreate | EpochSetUpdate, current: EpochSetRead | None = None) -> None:
    eeg_file = storage_service.get_eeg_file(input_file_id)
    project_id = getattr(payload, "project_id", None) or (current.project_id if current else None)
    if project_id and eeg_file.project_id != project_id:
        raise HTTPException(status_code=422, detail="Epoch set project_id must match the EEG file project_id")
    tmin = payload.tmin if getattr(payload, "tmin", None) is not None else (current.tmin if current else None)
    tmax = payload.tmax if getattr(payload, "tmax", None) is not None else (current.tmax if current else None)
    if tmin is None or tmax is None or float(tmax) <= float(tmin):
        raise HTTPException(status_code=422, detail="Epoch set requires tmax > tmin")
    boundary = getattr(payload, "boundary", None) or (current.boundary if current else "")
    if "not for clinical diagnosis" not in str(boundary).lower():
        raise HTTPException(status_code=422, detail="Epoch set boundary must include a non-diagnostic statement")
    plan_id = getattr(payload, "data_preparation_plan_id", None)
    plan_revision = getattr(payload, "data_preparation_revision", None)
    if plan_id or plan_revision is not None:
        if not plan_id or plan_revision is None:
            raise HTTPException(status_code=422, detail="Both data_preparation_plan_id and data_preparation_revision are required for epoch set lineage")
        plan = assert_plan_revision(str(plan_id), int(plan_revision), "erp")
        if plan.input_file_id != input_file_id:
            raise HTTPException(status_code=422, detail="Epoch set data preparation plan must reference the same EEG file")


def save_epoch_set_for_file(input_file_id: str, payload: EpochSetCreate) -> EpochSetRead:
    eeg_file = storage_service.get_eeg_file(input_file_id)
    _validate_epoch_set_payload(input_file_id, payload)
    lineage = dict(payload.lineage_json or {})
    lineage.setdefault("source_file", {
        "file_id": eeg_file.id,
        "original_filename": eeg_file.original_filename,
        "sha256": eeg_file.sha256,
    })
    lineage.setdefault("data_preparation", {
        "plan_id": payload.data_preparation_plan_id,
        "revision": payload.data_preparation_revision,
    })
    lineage.setdefault("boundary", payload.boundary)
    epoch_set = EpochSetRead(
        organization_id=payload.organization_id,
        project_id=payload.project_id,
        input_file_id=input_file_id,
        owner_user_id=payload.owner_user_id,
        created_by=payload.created_by,
        updated_by=payload.updated_by,
        status=payload.status,
        schema_version=payload.schema_version,
        title=payload.title,
        data_preparation_plan_id=payload.data_preparation_plan_id,
        data_preparation_revision=payload.data_preparation_revision,
        event_id=payload.event_id,
        event_mapping=payload.event_mapping,
        event_count=payload.event_count,
        estimated_epoch_count=payload.estimated_epoch_count,
        tmin=payload.tmin,
        tmax=payload.tmax,
        baseline=payload.baseline,
        l_freq=payload.l_freq,
        h_freq=payload.h_freq,
        drop_log_preview=payload.drop_log_preview,
        boundary=payload.boundary,
        lineage_json=lineage,
        artifact_contract_json=payload.artifact_contract_json,
    )
    audit = audit_service.record_event(
        action="epoch_set.created",
        object_type="epoch_set",
        object_id=epoch_set.id,
        organization_id=epoch_set.organization_id,
        project_id=epoch_set.project_id,
        actor_user_id=epoch_set.owner_user_id,
        metadata_json={"input_file_id": epoch_set.input_file_id, "revision": epoch_set.revision},
    )
    epoch_set.lineage_json.setdefault("audit_trace_id", audit.audit_trace_id)
    _write_epoch_set_artifacts(epoch_set)
    _epoch_sets[epoch_set.id] = epoch_set
    state_store.upsert_item(EPOCH_SET_REGISTRY, epoch_set)
    return epoch_set


def update_epoch_set(epoch_set_id: str, payload: EpochSetUpdate) -> EpochSetRead:
    epoch_set = get_epoch_set(epoch_set_id)
    if payload.expected_revision != epoch_set.revision:
        raise _revision_conflict(epoch_set_id, payload.expected_revision, epoch_set.revision)
    _validate_epoch_set_payload(epoch_set.input_file_id, payload, epoch_set)
    updates = payload.model_dump(exclude_unset=True)
    updates.pop("expected_revision", None)
    for key, value in updates.items():
        setattr(epoch_set, key, value)
    epoch_set.revision += 1
    from backend.models.base import utc_now
    epoch_set.updated_at = utc_now()
    audit = audit_service.record_event(
        action="epoch_set.updated",
        object_type="epoch_set",
        object_id=epoch_set.id,
        organization_id=epoch_set.organization_id,
        project_id=epoch_set.project_id,
        actor_user_id=epoch_set.updated_by or epoch_set.owner_user_id,
        metadata_json={"input_file_id": epoch_set.input_file_id, "revision": epoch_set.revision},
    )
    epoch_set.lineage_json.setdefault("audit_trace_id", audit.audit_trace_id)
    _write_epoch_set_artifacts(epoch_set)
    _epoch_sets[epoch_set.id] = epoch_set
    state_store.upsert_item(EPOCH_SET_REGISTRY, epoch_set)
    return epoch_set


def save_bad_channel_audit_for_file(input_file_id: str, payload: BadChannelAuditCreate) -> BadChannelAuditRead:
    eeg_file = storage_service.get_eeg_file(input_file_id)
    if eeg_file.project_id != payload.project_id:
        raise HTTPException(status_code=422, detail="Bad-channel audit project_id must match the EEG file project_id")
    plan = assert_plan_revision(payload.plan_id, payload.plan_revision, "qc")
    if plan.input_file_id != input_file_id:
        raise HTTPException(status_code=422, detail="Bad-channel audit plan must reference the same EEG file")
    if payload.decision not in {"save", "discard"}:
        raise HTTPException(status_code=422, detail="Bad-channel audit decision must be save or discard")
    if not payload.changed_channels:
        raise HTTPException(status_code=422, detail="Bad-channel audit requires at least one channel review record")

    root = plan.artifact_root or _plan_root(plan.project_id, plan.id, plan.revision)
    audit_dir = root / "quality"
    audit_dir.mkdir(parents=True, exist_ok=True)
    source_before = _bad_channel_source_integrity_snapshot(eeg_file, plan)
    audit = BadChannelAuditRead(
        organization_id=payload.organization_id,
        project_id=payload.project_id,
        input_file_id=input_file_id,
        plan_id=payload.plan_id,
        plan_revision=payload.plan_revision,
        actor_user_id=payload.actor_user_id,
        session_id=payload.session_id,
        decision=payload.decision,
        changed_channels=payload.changed_channels,
        artifact_root=root,
    )
    rows = ["name\tstatus\tstatus_description\treview_decision\treason"]
    for item in payload.changed_channels:
        channel = str(item.get("channel") or item.get("name") or "").strip()
        if not channel:
            raise HTTPException(status_code=422, detail="Bad-channel audit changed_channels entries require channel")
        new_status = str(item.get("new_status") or item.get("status") or "bad").strip()
        previous_status = str(item.get("previous_status") or "good").strip()
        reason = str(item.get("reason") or payload.reason or "UI review").replace("\t", " ")
        rows.append(f"{channel}\t{new_status}\tprevious={previous_status}\t{payload.decision}\t{reason}")

    channels_tsv = audit_dir / f"{audit.audit_id}_channels.tsv"
    channels_tsv.write_text("\n".join(rows) + "\n", encoding="utf-8")
    audit_json = audit_dir / f"{audit.audit_id}_bad_channel_audit.json"
    ui_evidence = audit_dir / f"{audit.audit_id}_bad_channel_ui_evidence.json"
    source_integrity = audit_dir / f"{audit.audit_id}_source_integrity.json"
    source_after = _bad_channel_source_integrity_snapshot(eeg_file, plan)
    integrity_payload = {
        "schema_version": "qlanalyser-bad-channel-source-integrity-v0.1",
        "audit_id": audit.audit_id,
        "decision": payload.decision,
        "source_before": source_before,
        "source_after": source_after,
        "source_eeg_object_unchanged": (
            source_before.get("source_eeg_object", {}).get("sha256") == source_after.get("source_eeg_object", {}).get("sha256")
            and source_before.get("source_eeg_object", {}).get("size_bytes") == source_after.get("source_eeg_object", {}).get("size_bytes")
        ),
        "source_channels_tsv_modified": (
            source_before.get("source_channels_tsv", {}).get("sha256") != source_after.get("source_channels_tsv", {}).get("sha256")
        ),
        "audit_channels_tsv_path": str(channels_tsv),
        "audit_channels_tsv_role": "derivative_review_record_not_source_bids_channels_tsv",
        "boundary": (
            "This integrity record documents source EEG object and optional source channels.tsv hashes before and after review. "
            "The audit channels.tsv is a derivative review artifact and must not be interpreted as an in-place source BIDS rewrite."
        ),
    }
    _write_json(source_integrity, integrity_payload)
    audit_payload = audit.model_dump(mode="json")
    audit_payload.update(
        {
            "reason": payload.reason,
            "note": payload.note,
            "source_integrity": integrity_payload,
            "source_integrity_path": str(source_integrity),
            "audit_channels_tsv_role": "derivative_review_record_not_source_bids_channels_tsv",
            "provenance_json": {
                **(payload.provenance_json or {}),
                "source_file": {
                    "file_id": eeg_file.id,
                    "original_filename": eeg_file.original_filename,
                    "sha256": eeg_file.sha256,
                },
                "data_preparation_plan": {"plan_id": plan.id, "revision": plan.revision},
            },
        }
    )
    _write_json(audit_json, audit_payload)
    _write_json(
        ui_evidence,
        {
            "schema_version": "qlanalyser-bad-channel-ui-evidence-v0.1",
            "audit_id": audit.audit_id,
            "ui_surface": "preprocessing-readiness-panel",
            "visible_actions": ["save-bad-channel-audit", "discard-bad-channel-audit"],
            "decision": payload.decision,
            "changed_channels": payload.changed_channels,
            "source_integrity_path": str(source_integrity),
            "source_eeg_object_unchanged": integrity_payload["source_eeg_object_unchanged"],
            "source_channels_tsv_modified": integrity_payload["source_channels_tsv_modified"],
            "boundary": audit.boundary,
        },
    )
    audit.channels_tsv_path = channels_tsv
    audit.audit_json_path = audit_json
    audit.ui_evidence_path = ui_evidence
    audit.source_integrity_path = source_integrity
    audit_service.record_event(
        action=f"bad_channel_audit.{payload.decision}",
        object_type="bad_channel_audit",
        object_id=audit.audit_id,
        organization_id=payload.organization_id,
        project_id=payload.project_id,
        actor_user_id=payload.actor_user_id,
        metadata_json={
            "input_file_id": input_file_id,
            "plan_id": plan.id,
            "plan_revision": plan.revision,
            "changed_channel_count": len(payload.changed_channels),
        },
    )
    return audit


def save_plan(payload: DataPreparationPlanCreate) -> DataPreparationPlanRead:
    eeg_file = storage_service.get_eeg_file(payload.input_file_id)
    if eeg_file.project_id != payload.project_id:
        raise HTTPException(status_code=422, detail="Data preparation plan project_id must match the EEG file project_id")
    scope = _validate_scope(list(payload.module_scope))
    plan = DataPreparationPlanRead(
        organization_id=payload.organization_id,
        project_id=payload.project_id,
        input_file_id=payload.input_file_id,
        owner_user_id=payload.owner_user_id,
        created_by=payload.created_by,
        updated_by=payload.updated_by,
        visibility_scope=payload.visibility_scope,
        permission_policy=payload.permission_policy,
        quota_account_id=payload.quota_account_id,
        audit_trace_id=payload.audit_trace_id,
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
    audit = audit_service.record_event(
        action="data_preparation_plan.created",
        object_type="data_preparation_plan",
        object_id=plan.id,
        organization_id=plan.organization_id,
        project_id=plan.project_id,
        actor_user_id=plan.owner_user_id,
        metadata_json={"input_file_id": plan.input_file_id, "revision": plan.revision},
    )
    plan.audit_trace_id = plan.audit_trace_id or audit.audit_trace_id
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
    audit = audit_service.record_event(
        action="data_preparation_plan.updated",
        object_type="data_preparation_plan",
        object_id=plan.id,
        organization_id=plan.organization_id,
        project_id=plan.project_id,
        actor_user_id=plan.updated_by or plan.owner_user_id,
        metadata_json={"input_file_id": plan.input_file_id, "revision": plan.revision},
    )
    plan.audit_trace_id = plan.audit_trace_id or audit.audit_trace_id
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
        allowed = "/".join(sorted(SUPPORTED_PLAN_MODULES)).upper()
        raise HTTPException(status_code=422, detail=f"Data preparation plan is only supported for {allowed} tasks, not: {module_name}")
    try:
        expected_revision = int(revision)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="data_preparation_revision must be an integer") from exc
    plan = assert_plan_revision(str(plan_id), expected_revision, module_name)
    parameters_json.setdefault("data_preparation_contract_version", CONTRACT_VERSION)
    return plan
