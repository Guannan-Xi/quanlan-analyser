from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from backend.models.base import new_id, utc_now


class ArtifactRead(BaseModel):
    id: str = Field(default_factory=lambda: new_id("artifact"))
    task_id: str
    organization_id: str = "local-org"
    project_id: str | None = None
    input_file_id: str | None = None
    artifact_type: str
    label: str
    path: Path
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
    created_at: datetime = Field(default_factory=utc_now)
