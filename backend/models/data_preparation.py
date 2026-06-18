from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from backend.models.base import new_id, utc_now


SUPPORTED_PLAN_MODULES = {"qc", "psd"}


class DataPreparationPlanCreate(BaseModel):
    project_id: str
    input_file_id: str
    module_scope: list[Literal["qc", "psd"]] = Field(default_factory=lambda: ["qc", "psd"])
    title: str = "QC / PSD data preparation plan"
    description: str = ""
    preprocessing_json: dict = Field(default_factory=dict)
    qc_json: dict = Field(default_factory=dict)
    psd_json: dict = Field(default_factory=dict)
    artifact_contract_json: dict = Field(default_factory=dict)
    expected_revision: int | None = None


class DataPreparationPlanUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    module_scope: list[Literal["qc", "psd"]] | None = None
    preprocessing_json: dict | None = None
    qc_json: dict | None = None
    psd_json: dict | None = None
    artifact_contract_json: dict | None = None
    expected_revision: int


class DataPreparationPlanRead(BaseModel):
    id: str = Field(default_factory=lambda: new_id("prep"))
    project_id: str
    input_file_id: str
    module_scope: list[str] = Field(default_factory=lambda: ["qc", "psd"])
    title: str = "QC / PSD data preparation plan"
    description: str = ""
    preprocessing_json: dict = Field(default_factory=dict)
    qc_json: dict = Field(default_factory=dict)
    psd_json: dict = Field(default_factory=dict)
    artifact_contract_json: dict = Field(default_factory=dict)
    revision: int = 1
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
