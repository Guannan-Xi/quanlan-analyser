from fastapi import APIRouter

router = APIRouter()


@router.get("/workflows/templates")
def list_workflow_templates() -> list[dict]:
    return [
        {"id": "research_psd", "steps": ["metadata", "preview", "preprocess", "psd", "report"]},
        {"id": "erp_ready", "steps": ["metadata", "events", "epochs", "erp", "report"]},
    ]


@router.post("/workflows/estimate")
def estimate_workflow_cost(template_id: str = "research_psd") -> dict:
    return {"template_id": template_id, "estimated_cost": 68.0, "currency": "CNY"}

