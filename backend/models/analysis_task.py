from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.base import new_id, utc_now


class AnalysisTaskCreate(BaseModel):
    project_id: str
    module_name: str
    workflow_id: str
    input_file_id: str
    parameters_json: dict = Field(default_factory=dict)


class AnalysisTaskRead(AnalysisTaskCreate):
    id: str = Field(default_factory=lambda: new_id("task"))
    status: str = "queued"
    progress: int = 0
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None

