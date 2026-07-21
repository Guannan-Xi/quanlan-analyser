from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from backend.models.report import ReportCreate
from backend.models.governance import AccountRead
from backend.models.public_api import ReportPublicRead, report_to_public
from backend.services import account_service, audit_service, report_service, task_service

router = APIRouter()


def _requesting_user_id(current: AccountRead) -> str | None:
    return None if current.role == "admin" else current.id


@router.post("/reports", response_model=ReportPublicRead)
def create_report(payload: ReportCreate, current: AccountRead = Depends(account_service.require_current_account)) -> ReportPublicRead:
    task = task_service.get_task(payload.task_id, requesting_user_id=current.id)
    if task.project_id != payload.project_id:
        raise HTTPException(status_code=422, detail="Report project_id must match the task project_id")
    if task.status != "completed":
        raise HTTPException(status_code=422, detail="Report requires a completed analysis task")
    report_service.assert_default_report_primary_module(task)
    reviewed_events = audit_service.list_events(
        action="result.reviewed",
        object_type="analysis_task",
        object_id=task.id,
        actor_user_id=current.id,
        project_id=task.project_id,
    )
    if not reviewed_events:
        raise HTTPException(status_code=422, detail="Please review the analysis results before generating a report")
    owned_payload = payload.model_copy(update={"owner_user_id": current.id, "created_by": current.id})
    return report_to_public(report_service.create_report(owned_payload))


@router.get("/reports/{report_id}", response_model=ReportPublicRead)
def get_report(report_id: str, current: AccountRead = Depends(account_service.require_current_account)) -> ReportPublicRead:
    return report_to_public(report_service.get_report(report_id, requesting_user_id=_requesting_user_id(current)))


@router.get("/reports/{report_id}/html")
def download_report_html(report_id: str, current: AccountRead = Depends(account_service.require_current_account)) -> FileResponse:
    path = report_service.get_report_file(report_id, "html", requesting_user_id=_requesting_user_id(current))
    return FileResponse(path, media_type="text/html", filename=path.name)


@router.get("/reports/{report_id}/package")
def download_report_package(report_id: str, current: AccountRead = Depends(account_service.require_current_account)) -> FileResponse:
    path = report_service.get_report_file(report_id, "package", requesting_user_id=_requesting_user_id(current))
    return FileResponse(path, media_type="application/zip", filename=path.name)
