from fastapi import APIRouter, HTTPException

from backend.services.product_catalog import ANALYSIS_TEMPLATES, PARADIGMS, RECOMMENDATION_RULES
from backend.services.task_service import WORKFLOW_TEMPLATES

router = APIRouter()


@router.get("/templates")
def list_templates() -> list[dict]:
    return WORKFLOW_TEMPLATES


@router.get("/templates/{template_id}")
def get_template(template_id: str) -> dict:
    for template in WORKFLOW_TEMPLATES:
        if template["id"] == template_id:
            return template
    raise HTTPException(status_code=404, detail="Template not found")


@router.get("/analysis-templates")
def list_analysis_templates() -> list[dict]:
    return ANALYSIS_TEMPLATES


@router.get("/paradigms")
def list_paradigms() -> dict:
    return {"count": len(PARADIGMS), "records": PARADIGMS}


@router.get("/recommendation-rules")
def list_recommendation_rules() -> list[dict]:
    return RECOMMENDATION_RULES
