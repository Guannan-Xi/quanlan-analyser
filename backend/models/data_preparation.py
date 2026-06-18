from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field

from backend.models.base import new_id, utc_now


SUPPORTED_PLAN_MODULES = {"qc", "psd"}


class DataPreparationPlanCreate(BaseModel):
    project_id: str
    input_file_id: str
    schema_version: str = "qlanalyser-data-preparation-v0.2"
    scope: str = "common_qc_preparation"
    status: Literal["draft", "confirmed"] = "draft"
    module_scope: list[Literal["qc", "psd"]] = Field(default_factory=lambda: ["qc", "psd"])
    title: str = "QC / PSD data preparation plan"
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
    project_id: str
    schema_version: str = "qlanalyser-data-preparation-v0.2"
    scope: str = "common_qc_preparation"
    status: Literal["draft", "confirmed"] = "draft"
    module_scope: list[Literal["qc", "psd"]] = Field(default_factory=lambda: ["qc", "psd"])
    title: str = "QC / PSD data preparation plan"
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
    schema_version: str | None = None
    scope: str | None = None
    status: Literal["draft", "confirmed"] | None = None
    title: str | None = None
    description: str | None = None
    module_scope: list[Literal["qc", "psd"]] | None = None
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
    schema_version: str = "qlanalyser-data-preparation-v0.2"
    project_id: str
    input_file_id: str
    scope: str = "common_qc_preparation"
    status: str = "draft"
    module_scope: list[str] = Field(default_factory=lambda: ["qc", "psd"])
    title: str = "QC / PSD data preparation plan"
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
    module_name: Literal["qc", "psd"]
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
