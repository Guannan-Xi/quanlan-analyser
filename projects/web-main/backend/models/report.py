from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from backend.models.base import new_id, utc_now


class ReportCreate(BaseModel):
    organization_id: str = "local-org"
    project_id: str
    task_id: str
    title: str = "单被试脑电分析报告"
    owner_user_id: str = "local-user"
    created_by: str = "local-user"


class ReportRead(ReportCreate):
    id: str = Field(default_factory=lambda: new_id("report"))
    html_path: Path
    package_path: Path | None = None
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
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
