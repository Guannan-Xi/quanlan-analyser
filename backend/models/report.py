from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from backend.models.base import new_id, utc_now


class ReportCreate(BaseModel):
    project_id: str
    task_id: str
    title: str = "Single-subject EEG report"


class ReportRead(ReportCreate):
    id: str = Field(default_factory=lambda: new_id("report"))
    html_path: Path
    package_path: Path | None = None
    created_at: datetime = Field(default_factory=utc_now)

