from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from backend.models.base import new_id, utc_now


class EEGFileRead(BaseModel):
    id: str = Field(default_factory=lambda: new_id("eeg"))
    organization_id: str = "local-org"
    project_id: str
    subject_id: str | None = None
    session_id: str | None = None
    original_filename: str
    stored_path: Path
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
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
