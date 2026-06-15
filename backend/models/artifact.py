from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from backend.models.base import new_id, utc_now


class ArtifactRead(BaseModel):
    id: str = Field(default_factory=lambda: new_id("artifact"))
    task_id: str
    artifact_type: str
    label: str
    path: Path
    mime_type: str = "application/octet-stream"
    created_at: datetime = Field(default_factory=utc_now)

