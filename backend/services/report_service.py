from pathlib import Path

from fastapi import HTTPException

from backend.models.report import ReportCreate, ReportRead
from backend.services import task_service
from eeg_core.report.html_report import write_html_report

ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "data" / "reports"

_reports: dict[str, ReportRead] = {}


def create_report(payload: ReportCreate) -> ReportRead:
    task = task_service.get_task(payload.task_id)
    report_dir = REPORT_ROOT / payload.project_id / task.id
    report_dir.mkdir(parents=True, exist_ok=True)
    html_path = write_html_report(report_dir, payload.title, task.model_dump(mode="json"))
    report = ReportRead(**payload.model_dump(), html_path=html_path)
    _reports[report.id] = report
    return report


def get_report(report_id: str) -> ReportRead:
    try:
        return _reports[report_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Report not found") from exc

