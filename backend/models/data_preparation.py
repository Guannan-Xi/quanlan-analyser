from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field

from backend.models.base import new_id, utc_now


PlanModuleName = Literal["qc", "psd", "erp", "epilepsy", "tfr", "pac", "reference_csd", "multitaper_psd_tfr", "connectivity"]
SUPPORTED_PLAN_MODULES = {"qc", "psd", "erp", "epilepsy", "tfr", "pac", "reference_csd", "multitaper_psd_tfr", "connectivity"}
DEFAULT_PLAN_MODULE_SCOPE: list[PlanModuleName] = ["qc", "psd", "erp", "epilepsy", "tfr", "pac", "reference_csd", "multitaper_psd_tfr", "connectivity"]


class DataPreparationPlanCreate(BaseModel):
    organization_id: str = "local-org"
    project_id: str
    input_file_id: str
    owner_user_id: str = "local-user"
    created_by: str = "local-user"
    updated_by: str | None = None
    visibility_scope: str = "organization"
    permission_policy: dict = Field(default_factory=dict)
    quota_account_id: str | None = None
    audit_trace_id: str | None = None
    schema_version: str = "qlanalyser-data-preparation-v0.2"
    scope: str = "common_qc_preparation"
    status: Literal["draft", "confirmed"] = "draft"
    module_scope: list[PlanModuleName] = Field(default_factory=lambda: list(DEFAULT_PLAN_MODULE_SCOPE))
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
    expected_revision: int | None = None


class DataPreparationPlanForFileSave(BaseModel):
    organization_id: str = "local-org"
    project_id: str
    owner_user_id: str = "local-user"
    created_by: str = "local-user"
    updated_by: str | None = None
    visibility_scope: str = "organization"
    permission_policy: dict = Field(default_factory=dict)
    quota_account_id: str | None = None
    audit_trace_id: str | None = None
    schema_version: str = "qlanalyser-data-preparation-v0.2"
    scope: str = "common_qc_preparation"
    status: Literal["draft", "confirmed"] = "draft"
    module_scope: list[PlanModuleName] = Field(default_factory=lambda: list(DEFAULT_PLAN_MODULE_SCOPE))
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
    expected_revision: int | None = Field(
        default=None,
        validation_alias=AliasChoices("expected_revision", "base_revision"),
    )


class DataPreparationPlanUpdate(BaseModel):
    organization_id: str | None = None
    owner_user_id: str | None = None
    updated_by: str | None = None
    visibility_scope: str | None = None
    permission_policy: dict | None = None
    quota_account_id: str | None = None
    audit_trace_id: str | None = None
    schema_version: str | None = None
    scope: str | None = None
    status: Literal["draft", "confirmed"] | None = None
    title: str | None = None
    description: str | None = None
    module_scope: list[PlanModuleName] | None = None
    source_file: dict | None = None
    metadata_review: dict | None = None
    preprocessing_json: dict | None = None
    qc_json: dict | None = None
    psd_json: dict | None = None
    channel_types: dict | None = None
    channel_renames: dict | None = None
    bad_channels: list[dict] | None = None
    bad_segments: list[dict] | None = None
    annotation_actions: list[dict] | None = None
    saved_preview_segments: list[dict] | None = None
    next_step_recommendation: dict | None = None
    warnings: list[str] | None = None
    artifact_contract_json: dict | None = None
    expected_revision: int = Field(validation_alias=AliasChoices("expected_revision", "base_revision"))


class DataPreparationPlanRead(BaseModel):
    id: str = Field(default_factory=lambda: new_id("prep"))
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
    status: str = "draft"
    module_scope: list[str] = Field(default_factory=lambda: list(DEFAULT_PLAN_MODULE_SCOPE))
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
    artifact_root: Path | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DataPreparationTaskReferenceCreate(BaseModel):
    module_name: PlanModuleName
    workflow_id: str
    expected_revision: int
    task_id: str | None = None


class DataPreparationTaskReferenceRead(BaseModel):
    plan_id: str
    revision: int
    project_id: str
    input_file_id: str
    module_name: str
    workflow_id: str
    task_id: str | None = None
    parameters_json: dict
    artifact_contract_json: dict
    artifact_root: Path
    created_at: datetime = Field(default_factory=utc_now)


class EpochSetCreate(BaseModel):
    organization_id: str = "local-org"
    project_id: str
    input_file_id: str
    owner_user_id: str = "local-user"
    created_by: str = "local-user"
    updated_by: str | None = None
    status: Literal["draft", "confirmed"] = "confirmed"
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
    expected_revision: int | None = None


class EpochSetUpdate(BaseModel):
    updated_by: str | None = None
    status: Literal["draft", "confirmed"] | None = None
    title: str | None = None
    data_preparation_plan_id: str | None = None
    data_preparation_revision: int | None = None
    event_id: dict | None = None
    event_mapping: list[dict] | None = None
    event_count: int | None = None
    estimated_epoch_count: int | None = None
    tmin: float | None = None
    tmax: float | None = None
    baseline: list[float | None] | None = None
    l_freq: float | None = None
    h_freq: float | None = None
    drop_log_preview: list[dict] | None = None
    boundary: str | None = None
    lineage_json: dict | None = None
    artifact_contract_json: dict | None = None
    expected_revision: int = Field(validation_alias=AliasChoices("expected_revision", "base_revision"))


class EpochSetRead(BaseModel):
    id: str = Field(default_factory=lambda: new_id("epoch"))
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
    artifact_root: Path | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class BadChannelAuditCreate(BaseModel):
    organization_id: str = "local-org"
    project_id: str
    input_file_id: str
    plan_id: str
    plan_revision: int
    actor_user_id: str = "local-user"
    session_id: str = "local-ui-session"
    decision: Literal["save", "discard"] = "save"
    changed_channels: list[dict] = Field(default_factory=list)
    reason: str = "UI review"
    note: str = ""
    provenance_json: dict = Field(default_factory=dict)


class BadChannelAuditRead(BaseModel):
    audit_id: str = Field(default_factory=lambda: new_id("badaudit"))
    organization_id: str = "local-org"
    project_id: str
    input_file_id: str
    plan_id: str
    plan_revision: int
    actor_user_id: str = "local-user"
    session_id: str = "local-ui-session"
    decision: str = "save"
    changed_channels: list[dict] = Field(default_factory=list)
    channels_tsv_path: Path | None = None
    audit_json_path: Path | None = None
    ui_evidence_path: Path | None = None
    source_integrity_path: Path | None = None
    artifact_root: Path
    boundary: str = "Bad-channel audit records review decisions only; it is not a clinical diagnosis."
    created_at: datetime = Field(default_factory=utc_now)
