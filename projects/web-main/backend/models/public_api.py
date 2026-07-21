from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from backend.models.artifact import ArtifactRead
from backend.models.data_preparation import (
    BadChannelAuditRead,
    DataPreparationPlanRead,
    DataPreparationTaskReferenceRead,
    EpochSetRead,
)
from backend.models.eeg_file import EEGFileRead
from backend.models.report import ReportRead


INTERNAL_METADATA_KEYS = {
    "absolute_path",
    "artifact_root",
    "audit_json_path",
    "channels_tsv_path",
    "edf_path",
    "events_tsv_path",
    "file_path",
    "html_path",
    "local_path",
    "package_path",
    "path",
    "repo_path",
    "root_dir",
    "source_integrity_path",
    "stored_path",
    "ui_evidence_path",
}


def _looks_like_internal_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return (
        ":/" in normalized
        or normalized.startswith("/")
        or "quanlan-analyser" in normalized.lower()
        or "/users/" in normalized.lower()
        or "/data/derivatives/" in normalized.lower()
    )


def sanitize_public_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in INTERNAL_METADATA_KEYS:
                continue
            sanitized[key_text] = sanitize_public_metadata(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_public_metadata(item) for item in value]
    if isinstance(value, Path):
        return value.name
    if isinstance(value, str) and _looks_like_internal_path(value):
        return Path(value).name
    return value


class ArtifactPublicRead(BaseModel):
    id: str
    task_id: str
    project_id: str | None = None
    input_file_id: str | None = None
    artifact_type: str
    label: str
    file_name: str
    display_name: str
    object_key: str | None = None
    storage_backend: str = "local"
    storage_tier: str = "hot"
    size_bytes: int | None = None
    sha256: str | None = None
    retention_policy: str = "project_default"
    download_policy: str = "project_member"
    expires_at: datetime | None = None
    quota_usage_json: dict = Field(default_factory=dict)
    mime_type: str = "application/octet-stream"
    download_url: str
    created_at: datetime


class ReportPublicRead(BaseModel):
    id: str
    organization_id: str = "local-org"
    project_id: str
    task_id: str
    title: str
    owner_user_id: str = "local-user"
    created_by: str = "local-user"
    html_object_key: str | None = None
    package_object_key: str | None = None
    storage_backend: str = "local"
    storage_tier: str = "hot"
    size_bytes: int | None = None
    sha256: str | None = None
    retention_policy: str = "project_default"
    download_policy: str = "project_member"
    audit_trace_id: str | None = None
    quota_usage_json: dict = Field(default_factory=dict)
    html_download_url: str
    package_download_url: str | None = None
    created_at: datetime
    updated_at: datetime


class EEGFilePublicRead(BaseModel):
    id: str
    organization_id: str = "local-org"
    project_id: str
    subject_id: str | None = None
    session_id: str | None = None
    original_filename: str
    detected_format: str
    object_key: str | None = None
    storage_backend: str = "local"
    storage_tier: str = "hot"
    size_bytes: int | None = None
    sha256: str | None = None
    content_type: str | None = None
    sampling_rate: float | None = None
    channel_count: int | None = None
    duration_sec: float | None = None
    metadata_json: dict = Field(default_factory=dict)
    status: str = "uploaded"
    upload_status: str = "uploaded"
    upload_authorization_confirmed: bool = False
    upload_authorization_text: str | None = None
    upload_authorization_confirmed_at: datetime | None = None
    owner_user_id: str = "local-user"
    created_by: str = "local-user"
    updated_by: str | None = None
    visibility_scope: str = "organization"
    permission_policy: dict = Field(default_factory=dict)
    quota_account_id: str | None = None
    audit_trace_id: str | None = None
    retention_policy: str = "project_default"
    deleted_at: datetime | None = None
    metadata_extracted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DataPreparationPlanPublicRead(BaseModel):
    id: str
    organization_id: str = "local-org"
    schema_version: str = "qlanalyser-data-preparation-v0.2"
    project_id: str
    input_file_id: str
    owner_user_id: str = "local-user"
    created_by: str = "local-user"
    updated_by: str | None = None
    visibility_scope: str = "organization"
    permission_policy: dict = Field(default_factory=dict)
    quota_account_id: str | None = None
    audit_trace_id: str | None = None
    scope: str = "common_qc_preparation"
    delivery_scope: str = "formal_delivery"
    status: str = "draft"
    module_scope: list[str] = Field(default_factory=list)
    title: str = "Common data preparation plan"
    description: str = ""
    source_file: dict = Field(default_factory=dict)
    metadata_review: dict = Field(default_factory=dict)
    preprocessing_json: dict = Field(default_factory=dict)
    qc_json: dict = Field(default_factory=dict)
    psd_json: dict = Field(default_factory=dict)
    channel_types: dict = Field(default_factory=dict)
    channel_renames: dict = Field(default_factory=dict)
    bad_channels: list[dict] = Field(default_factory=list)
    bad_segments: list[dict] = Field(default_factory=list)
    annotation_actions: list[dict] = Field(default_factory=list)
    saved_preview_segments: list[dict] = Field(default_factory=list)
    next_step_recommendation: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    artifact_contract_json: dict = Field(default_factory=dict)
    revision: int = 1
    is_default: bool = False
    created_at: datetime
    updated_at: datetime


class DataPreparationTaskReferencePublicRead(BaseModel):
    plan_id: str
    revision: int
    project_id: str
    input_file_id: str
    module_name: str
    workflow_id: str
    task_id: str | None = None
    parameters_json: dict
    artifact_contract_json: dict
    created_at: datetime


class EpochSetPublicRead(BaseModel):
    id: str
    organization_id: str = "local-org"
    project_id: str
    input_file_id: str
    owner_user_id: str = "local-user"
    created_by: str = "local-user"
    updated_by: str | None = None
    status: str = "confirmed"
    schema_version: str = "qlanalyser-epoch-set-manifest-v0.1"
    title: str = "ERP/P300 epoch set"
    data_preparation_plan_id: str | None = None
    data_preparation_revision: int | None = None
    event_id: dict = Field(default_factory=dict)
    event_mapping: list[dict] = Field(default_factory=list)
    event_count: int = 0
    estimated_epoch_count: int = 0
    tmin: float
    tmax: float
    baseline: list[float | None] = Field(default_factory=list)
    l_freq: float | None = None
    h_freq: float | None = None
    drop_log_preview: list[dict] = Field(default_factory=list)
    boundary: str = "Single-record sensor-space research workflow; not for clinical diagnosis, source localization, or causal inference."
    lineage_json: dict = Field(default_factory=dict)
    artifact_contract_json: dict = Field(default_factory=dict)
    revision: int = 1
    created_at: datetime
    updated_at: datetime


class BadChannelAuditPublicRead(BaseModel):
    audit_id: str
    organization_id: str = "local-org"
    project_id: str
    input_file_id: str
    plan_id: str
    plan_revision: int
    actor_user_id: str = "local-user"
    session_id: str = "local-ui-session"
    decision: str = "save"
    changed_channels: list[dict] = Field(default_factory=list)
    boundary: str = "Bad-channel audit records review decisions only; it is not a clinical diagnosis."
    created_at: datetime


def artifact_to_public(artifact: ArtifactRead) -> ArtifactPublicRead:
    file_name = Path(artifact.path).name if artifact.path else (artifact.label or artifact.artifact_type or artifact.id)
    return ArtifactPublicRead(
        id=artifact.id,
        task_id=artifact.task_id,
        project_id=artifact.project_id,
        input_file_id=artifact.input_file_id,
        artifact_type=artifact.artifact_type,
        label=artifact.label,
        file_name=file_name,
        display_name=artifact.label or file_name,
        object_key=artifact.object_key,
        storage_backend=artifact.storage_backend,
        storage_tier=artifact.storage_tier,
        size_bytes=artifact.size_bytes,
        sha256=artifact.sha256,
        retention_policy=artifact.retention_policy,
        download_policy=artifact.download_policy,
        expires_at=artifact.expires_at,
        quota_usage_json=artifact.quota_usage_json,
        mime_type=artifact.mime_type,
        download_url=f"/api/artifacts/{artifact.id}/download",
        created_at=artifact.created_at,
    )


def report_to_public(report: ReportRead) -> ReportPublicRead:
    return ReportPublicRead(
        id=report.id,
        organization_id=report.organization_id,
        project_id=report.project_id,
        task_id=report.task_id,
        title=report.title,
        owner_user_id=report.owner_user_id,
        created_by=report.created_by,
        html_object_key=report.html_object_key,
        package_object_key=report.package_object_key,
        storage_backend=report.storage_backend,
        storage_tier=report.storage_tier,
        size_bytes=report.size_bytes,
        sha256=report.sha256,
        retention_policy=report.retention_policy,
        download_policy=report.download_policy,
        audit_trace_id=report.audit_trace_id,
        quota_usage_json=report.quota_usage_json,
        html_download_url=f"/api/reports/{report.id}/html",
        package_download_url=f"/api/reports/{report.id}/package" if report.package_path else None,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


def eeg_file_to_public(eeg_file: EEGFileRead) -> EEGFilePublicRead:
    data = eeg_file.model_dump()
    data.pop("stored_path", None)
    data["metadata_json"] = sanitize_public_metadata(data.get("metadata_json") or {})
    return EEGFilePublicRead(**data)


def plan_to_public(plan: DataPreparationPlanRead) -> DataPreparationPlanPublicRead:
    data = plan.model_dump()
    data.pop("artifact_root", None)
    for key in ("source_file", "metadata_review", "preprocessing_json", "qc_json", "psd_json", "artifact_contract_json"):
        data[key] = sanitize_public_metadata(data.get(key) or {})
    data["bad_channels"] = sanitize_public_metadata(data.get("bad_channels") or [])
    data["bad_segments"] = sanitize_public_metadata(data.get("bad_segments") or [])
    data["annotation_actions"] = sanitize_public_metadata(data.get("annotation_actions") or [])
    data["saved_preview_segments"] = sanitize_public_metadata(data.get("saved_preview_segments") or [])
    return DataPreparationPlanPublicRead(**data)


def task_reference_to_public(reference: DataPreparationTaskReferenceRead) -> DataPreparationTaskReferencePublicRead:
    data = reference.model_dump()
    data.pop("artifact_root", None)
    data["parameters_json"] = sanitize_public_metadata(data.get("parameters_json") or {})
    data["artifact_contract_json"] = sanitize_public_metadata(data.get("artifact_contract_json") or {})
    return DataPreparationTaskReferencePublicRead(**data)


def epoch_set_to_public(epoch_set: EpochSetRead) -> EpochSetPublicRead:
    data = epoch_set.model_dump()
    data.pop("artifact_root", None)
    data["lineage_json"] = sanitize_public_metadata(data.get("lineage_json") or {})
    data["artifact_contract_json"] = sanitize_public_metadata(data.get("artifact_contract_json") or {})
    data["drop_log_preview"] = sanitize_public_metadata(data.get("drop_log_preview") or [])
    return EpochSetPublicRead(**data)


def bad_channel_audit_to_public(audit: BadChannelAuditRead) -> BadChannelAuditPublicRead:
    data = audit.model_dump()
    for key in ("artifact_root", "channels_tsv_path", "audit_json_path", "ui_evidence_path", "source_integrity_path"):
        data.pop(key, None)
    data["changed_channels"] = sanitize_public_metadata(data.get("changed_channels") or [])
    return BadChannelAuditPublicRead(**data)
