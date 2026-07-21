from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.base import new_id, utc_now


class AnalysisTaskCreate(BaseModel):
    organization_id: str = "local-org"
    project_id: str
    module_name: str
    workflow_id: str
    input_file_id: str
    parameters_json: dict = Field(default_factory=dict)
    owner_user_id: str = "local-user"
    created_by: str = "local-user"
    priority: int = 0
    queue_name: str = "analysis-default"
    idempotency_key: str | None = None
    max_retries: int = 0


class AnalysisTaskRead(AnalysisTaskCreate):
    id: str = Field(default_factory=lambda: new_id("task"))
    status: str = "queued"
    queue_status: str = "created"
    progress: int = 0
    error_message: str | None = None
    error_code: str | None = None
    resource_estimate_json: dict = Field(default_factory=dict)
    quota_charge_preview_json: dict = Field(default_factory=dict)
    actual_resource_usage_json: dict = Field(default_factory=dict)
    retry_count: int = 0
    worker_id: str | None = None
    data_preparation_plan_id: str | None = None
    data_preparation_revision: int | None = None
    data_preparation_contract_version: str | None = None
    audit_trace_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utc_now)
