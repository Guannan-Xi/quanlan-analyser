from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException

from backend.models.report import ReportCreate, ReportRead
from backend.services import state_store, task_service
from eeg_core.report.html_report import write_html_report

ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "data" / "reports"
DERIVATIVES_ROOT = ROOT / "data" / "derivatives"

_reports: dict[str, ReportRead] = state_store.load_registry("reports", ReportRead)


def _refresh_reports() -> None:
    _reports.clear()
    _reports.update(state_store.load_registry("reports", ReportRead))


def _save_reports() -> None:
    for report in _reports.values():
        state_store.upsert_item("reports", report)


def create_report(payload: ReportCreate) -> ReportRead:
    task = task_service.get_task(payload.task_id)
    if task.project_id != payload.project_id:
        raise HTTPException(status_code=422, detail="Report project_id must match the task project_id")

    report = ReportRead(**payload.model_dump(), html_path=REPORT_ROOT / payload.project_id / "pending" / "report.html")
    report_dir = REPORT_ROOT / payload.project_id / report.id
    report_dir.mkdir(parents=True, exist_ok=True)

    artifacts = [artifact.model_dump(mode="json") for artifact in task_service.list_task_artifacts(task.id)]
    task_output_dir = DERIVATIVES_ROOT / task.project_id / task.id
    context = {
        "task": task.model_dump(mode="json"),
        "artifacts": artifacts,
        "task_output_dir": str(task_output_dir),
    }
    html_path = write_html_report(report_dir, payload.title, context)
    package_path = _write_report_package(report_dir, report.id, html_path, task_output_dir, artifacts)

    report.html_path = html_path
    report.package_path = package_path
    _reports[report.id] = report
    state_store.upsert_item("reports", report)
    return report


def get_report(report_id: str) -> ReportRead:
    _refresh_reports()
    try:
        return _reports[report_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Report not found") from exc


def get_report_file(report_id: str, kind: str) -> Path:
    report = get_report(report_id)
    if kind == "html":
        path = report.html_path
    elif kind == "package":
        path = report.package_path
    else:
        raise HTTPException(status_code=404, detail="Unknown report file kind")
    if path is None or not Path(path).exists():
        raise HTTPException(status_code=410, detail="Report file is not available on disk")
    return Path(path)


def _write_report_package(report_dir: Path, report_id: str, html_path: Path, task_output_dir: Path, artifacts: list[dict]) -> Path:
    package_path = report_dir / f"{report_id}.zip"
    written: set[str] = set()

    def add_file(archive: ZipFile, source: Path, archive_name: str) -> None:
        normalized = archive_name.replace("\\", "/")
        if normalized in written:
            return
        archive.write(source, normalized)
        written.add(normalized)

    with ZipFile(package_path, "w", compression=ZIP_DEFLATED) as archive:
        add_file(archive, html_path, "reports/report.html")
        manifest = report_dir / "manifest.txt"
        manifest.write_text(
            "QLanalyser EEG V01 report package\n"
            f"report_id={report_id}\n"
            f"task_output_dir={task_output_dir}\n"
            "Included directories preserve task-relative paths where possible.\n",
            encoding="utf-8",
        )
        add_file(archive, manifest, "manifest.txt")

        if task_output_dir.exists():
            for child in task_output_dir.rglob("*"):
                if child.is_file():
                    add_file(archive, child, child.relative_to(task_output_dir).as_posix())

        for artifact in artifacts:
            path = Path(artifact.get("path", ""))
            if path.exists() and path.is_file():
                try:
                    relative = path.relative_to(task_output_dir).as_posix()
                except ValueError:
                    relative = f"artifacts/{path.name}"
                add_file(archive, path, relative)
    return package_path
