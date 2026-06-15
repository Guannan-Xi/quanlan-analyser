from pydantic import BaseModel, Field


class WorkflowStep(BaseModel):
    name: str
    module: str
    parameters: dict = Field(default_factory=dict)


class WorkflowSpec(BaseModel):
    id: str
    name: str
    steps: list[WorkflowStep]

