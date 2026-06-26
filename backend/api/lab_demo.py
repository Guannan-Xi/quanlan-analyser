from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from backend.models.analysis_task import AnalysisTaskRead
from backend.services import lab_demo_service


router = APIRouter()


class LabDemoRunRequest(BaseModel):
    parameters_json: dict = Field(default_factory=dict)


@router.get("/lab/demo/dataset")
def get_demo_dataset() -> dict:
    return lab_demo_service.ensure_demo_dataset()


@router.get("/lab/demo/epilepsy")
def get_epilepsy_demo_dataset() -> dict:
    return lab_demo_service.ensure_epilepsy_demo_dataset()


@router.post("/lab/demo/run/{module}", response_model=AnalysisTaskRead)
def run_demo_module(module: str) -> AnalysisTaskRead:
    try:
        return lab_demo_service.run_demo_task(module)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/lab/demo/run/{module}/configured", response_model=AnalysisTaskRead)
def run_configured_demo_module(module: str, payload: LabDemoRunRequest) -> AnalysisTaskRead:
    try:
        return lab_demo_service.run_demo_task(module, parameters=payload.parameters_json)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/lab/demo/run-all")
def run_all_demo_modules() -> dict:
    tasks = {}
    for module in ("qc", "psd", "erp", "reference_csd", "connectivity"):
        tasks[module] = lab_demo_service.run_demo_task(module).model_dump(mode="json")
    return {"dataset": lab_demo_service.ensure_demo_dataset(), "tasks": tasks}
