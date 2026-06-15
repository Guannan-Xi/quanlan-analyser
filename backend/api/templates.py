from fastapi import APIRouter

from backend.services.task_service import WORKFLOW_TEMPLATES
from backend.services.product_catalog import ANALYSIS_TEMPLATES, PARADIGMS, RECOMMENDATION_RULES

router = APIRouter()


@router.get("/templates")
def list_templates() -> list[dict]:
    return WORKFLOW_TEMPLATES


@router.get("/templates/{template_id}")
def get_template(template_id: str) -> dict:
    return next(template for template in WORKFLOW_TEMPLATES if template["id"] == template_id)


@router.get("/analysis-templates")
def list_analysis_templates() -> list[dict]:
    return ANALYSIS_TEMPLATES


@router.get("/paradigms")
def list_paradigms() -> dict:
    return {"count": len(PARADIGMS), "records": PARADIGMS}


@router.get("/recommendation-rules")
def list_recommendation_rules() -> list[dict]:
    return RECOMMENDATION_RULES
