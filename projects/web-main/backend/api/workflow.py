from fastapi import APIRouter, HTTPException

from backend.services.task_service import WORKFLOW_TEMPLATES

router = APIRouter()


@router.get("/workflows/templates")
def list_workflow_templates() -> list[dict]:
    return WORKFLOW_TEMPLATES


@router.post("/workflows/estimate")
def estimate_workflow(template_id: str = "resting_psd") -> dict:
    template = next((item for item in WORKFLOW_TEMPLATES if item["id"] == template_id), None)
    if template is None:
        raise HTTPException(status_code=404, detail="Workflow template not found")
    return {
        "template_id": template_id,
        "module": template["module"],
        "enabled_in_v01": bool(template.get("outputs")),
        "required_outputs": template.get("outputs", []),
        "billing_enabled": False,
        "message": "V01 uses local research execution; no payment or credit estimate is applied.",
    }
