from pydantic import BaseModel, Field

from backend.models.base import new_id


class SubjectCreate(BaseModel):
    subject_code: str
    group_name: str = "default"
    age: int | None = None
    sex: str | None = None
    notes: str = ""


class SubjectRead(SubjectCreate):
    id: str = Field(default_factory=lambda: new_id("sub"))
    project_id: str

