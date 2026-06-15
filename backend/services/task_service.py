from pathlib import Path

from fastapi import HTTPException

from backend.models.analysis_task import AnalysisTaskCreate, AnalysisTaskRead
from backend.models.artifact import ArtifactRead
from backend.models.base import utc_now
from backend.services import storage_service
from eeg_core.analysis.erp import run_erp
from eeg_core.analysis.psd import run_psd

ROOT = Path(__file__).resolve().parents[2]
DERIVATIVES_ROOT = ROOT / "data" / "derivatives"

WORKFLOW_TEMPLATES = [
    {
        "id": "resting_psd",
        "name": "Resting-state PSD",
        "module": "psd",
        "outputs": ["figures/psd.png", "tables/band_power.csv", "reproducibility/parameters.json"],
    },
    {
        "id": "erp_p300",
        "name": "ERP / P300",
        "module": "erp",
        "outputs": ["figures/erp_waveform.png", "tables/erp_metrics.csv", "reproducibility/parameters.json"],
    },
]

_tasks: dict[str, AnalysisTaskRead] = {}
_artifacts: dict[str, ArtifactRead] = {}


def create_task(payload: AnalysisTaskCreate) -> AnalysisTaskRead:
    eeg_file = storage_service.get_eeg_file(payload.input_file_id)
    task = AnalysisTaskRead(**payload.model_dump(), status="running", progress=10, started_at=utc_now())
    _tasks[task.id] = task

    output_dir = DERIVATIVES_ROOT / payload.project_id / task.id
    output_dir.mkdir(parents=True, exist_ok=True)

    if payload.module_name == "psd":
        result_paths = run_psd(eeg_file.stored_path, output_dir, payload.parameters_json)
    elif payload.module_name == "erp":
        result_paths = run_erp(eeg_file.stored_path, output_dir, payload.parameters_json)
    else:
        raise HTTPException(status_code=400, detail="Unsupported analysis module")

    for label, path in result_paths.items():
        artifact = ArtifactRead(
            task_id=task.id,
            artifact_type="result",
            label=label,
            path=path,
            mime_type=_guess_mime(path),
        )
        _artifacts[artifact.id] = artifact

    task.status = "completed"
    task.progress = 100
    task.finished_at = utc_now()
    return task


def get_task(task_id: str) -> AnalysisTaskRead:
    try:
        return _tasks[task_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


def list_task_artifacts(task_id: str) -> list[dict]:
    get_task(task_id)
    return [artifact.model_dump(mode="json") for artifact in _artifacts.values() if artifact.task_id == task_id]


def get_artifact_download_descriptor(artifact_id: str) -> dict:
    try:
        artifact = _artifacts[artifact_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Artifact not found") from exc
    return artifact.model_dump(mode="json")


def _guess_mime(path: Path) -> str:
    if path.suffix == ".csv":
        return "text/csv"
    if path.suffix == ".json":
        return "application/json"
    if path.suffix == ".html":
        return "text/html"
    if path.suffix == ".txt":
        return "text/plain"
    return "application/octet-stream"

