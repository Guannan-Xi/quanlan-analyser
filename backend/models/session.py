from pydantic import BaseModel, Field

from backend.models.base import new_id


class SessionRead(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ses"))
    project_id: str
    subject_id: str
    task_name: str = "default"

