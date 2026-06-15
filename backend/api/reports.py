from fastapi import APIRouter

from backend.models.report import ReportCreate, ReportRead
from backend.services import report_service

router = APIRouter()


@router.post("/reports", response_model=ReportRead)
def create_report(payload: ReportCreate) -> ReportRead:
    return report_service.create_report(payload)


@router.get("/reports/{report_id}", response_model=ReportRead)
def get_report(report_id: str) -> ReportRead:
    return report_service.get_report(report_id)

