from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.base import new_id, utc_now


class ProjectCreate(BaseModel):
    organization_id: str = "local-org"
    name: str
    description: str = ""
    research_type: str = "resting_state"
    owner_id: str = "local-user"
    owner_user_id: str = "local-user"
    created_by: str = "local-user"
    updated_by: str | None = None
    visibility_scope: str = "organization"
    permission_policy: dict = Field(default_factory=dict)
    quota_account_id: str | None = None
    storage_quota_bytes: int | None = None
    status: str = "active"


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    research_type: str | None = None
    updated_by: str | None = "local-user"
    status: str | None = None


class ProjectRead(ProjectCreate):
    id: str = Field(default_factory=lambda: new_id("proj"))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
