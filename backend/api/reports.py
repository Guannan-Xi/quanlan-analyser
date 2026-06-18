from fastapi import APIRouter
from fastapi.responses import FileResponse

from backend.models.report import ReportCreate, ReportRead
from backend.services import report_service

router = APIRouter()


@router.post("/reports", response_model=ReportRead)
def create_report(payload: ReportCreate) -> ReportRead:
    return report_service.create_report(payload)


@router.get("/reports/{report_id}", response_model=ReportRead)
def get_report(report_id: str) -> ReportRead:
    return report_service.get_report(report_id)


@router.get("/reports/{report_id}/html")
def download_report_html(report_id: str) -> FileResponse:
    path = report_service.get_report_file(report_id, "html")
    return FileResponse(path, media_type="text/html", filename=path.name)


@router.get("/reports/{report_id}/package")
def download_report_package(report_id: str) -> FileResponse:
    path = report_service.get_report_file(report_id, "package")
    return FileResponse(path, media_type="application/zip", filename=path.name)
