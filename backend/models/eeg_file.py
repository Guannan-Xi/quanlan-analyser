from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from backend.models.base import new_id, utc_now


class EEGFileRead(BaseModel):
    id: str = Field(default_factory=lambda: new_id("eeg"))
    project_id: str
    subject_id: str | None = None
    session_id: str | None = None
    original_filename: str
    stored_path: Path
    detected_format: str
    sampling_rate: float | None = None
    channel_count: int | None = None
    duration_sec: float | None = None
    metadata_json: dict = Field(default_factory=dict)
    status: str = "uploaded"
    created_at: datetime = Field(default_factory=utc_now)

