from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.base import new_id, utc_now


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    research_type: str = "resting_state"
    owner_id: str = "local-user"


class ProjectRead(ProjectCreate):
    id: str = Field(default_factory=lambda: new_id("proj"))
    created_at: datetime = Field(default_factory=utc_now)

