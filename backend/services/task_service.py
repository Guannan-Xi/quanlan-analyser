from pathlib import Path

from fastapi import HTTPException

from backend.models.analysis_task import AnalysisTaskCreate, AnalysisTaskRead
from backend.models.artifact import ArtifactRead
from backend.models.base import utc_now
from backend.models.data_preparation import DataPreparationTaskReferenceCreate
from backend.services import data_preparation_service, state_store, storage_service
from eeg_core.analysis.erp import run_erp
from eeg_core.analysis.psd import run_psd
from eeg_core.preprocess.quality import run_quality_check
from eeg_core.preprocess.qc_preview import QcPreviewError, run_qc_preview

ROOT = Path(__file__).resolve().parents[2]
DERIVATIVES_ROOT = ROOT / "data" / "derivatives"

WORKFLOW_TEMPLATES = [
    {
        "id": "metadata_qc",
        "name": "Metadata and QC",
        "module": "qc",
        "outputs": ["reproducibility/qc_summary.json"],
        "production_status": "v01_required",
    },
    {
        "id": "qc_waveform_preview",
        "name": "QC waveform / filter preview",
        "module": "qc",
        "outputs": ["data/waveform_preview.json", "data/filter_preview.json", "figures/waveform_raw_preview.svg", "figures/snapshots/snapshot_001.svg"],
        "production_status": "lab_service_preview",
    },
    {
        "id": "resting_psd",
        "name": "Resting-state PSD",
        "module": "psd",
        "outputs": ["tables/band_power.csv", "tables/channel_band_power.csv", "reproducibility/psd_summary.json", "reproducibility/parameters.json"],
        "production_status": "v01_required",
    },
    {
        "id": "erp_p300",
        "name": "ERP / P300",
        "module": "erp",
        "outputs": ["tables/erp_metrics.csv", "reproducibility/erp_summary.json", "reproducibility/parameters.json"],
        "production_status": "v01_required_when_events_exist",
    },
    {
        "id": "tfr_ersp_itc",
        "name": "Time-frequency / ERSP / ITC",
        "module": "tfr",
        "outputs": [],
        "production_status": "planned_requires_epoch_design",
    },
    {
        "id": "pac_cfc",
        "name": "PAC / Cross-frequency coupling",
        "module": "pac",
        "outputs": [],
        "production_status": "planned_requires_artifact_control_surrogates",
    },
    {
        "id": "connectivity",
        "name": "Connectivity",
        "module": "connectivity",
        "outputs": [],
        "production_status": "planned_requires_reference_and_volume_conduction_controls",
    },
]

_tasks: dict[str, AnalysisTaskRead] = state_store.load_registry("tasks", AnalysisTaskRead)
_artifacts: dict[str, ArtifactRead] = state_store.load_registry("artifacts", ArtifactRead)


def _refresh_tasks() -> None:
    _tasks.clear()
    _tasks.update(state_store.load_registry("tasks", AnalysisTaskRead))


def _refresh_artifacts() -> None:
    _artifacts.clear()
    _artifacts.update(state_store.load_registry("artifacts", ArtifactRead))


def _save_tasks() -> None:
    for task in _tasks.values():
        state_store.upsert_item("tasks", task)


def _save_artifacts() -> None:
    for artifact in _artifacts.values():
        state_store.upsert_item("artifacts", artifact)


def _register_data_preparation_artifacts(task_id: str, artifact_root: Path) -> None:
    for relative, label in (
        ("reproducibility/data_preparation_plan.json", "Data preparation plan"),
        ("reproducibility/data_preparation_task_reference.json", "Data preparation task reference"),
        ("reproducibility/data_preparation_artifact_contract.json", "Data preparation artifact contract"),
    ):
        path = artifact_root / relative
        if not path.exists():
            continue
        artifact = ArtifactRead(
            task_id=task_id,
            artifact_type="json",
            label=label,
            path=path,
            mime_type="application/json",
        )
        _artifacts[artifact.id] = artifact
        state_store.upsert_item("artifacts", artifact)


def create_task(payload: AnalysisTaskCreate) -> AnalysisTaskRead:
    eeg_file = storage_service.get_eeg_file(payload.input_file_id)
    data_preparation_plan = data_preparation_service.validate_task_parameters(payload.module_name, payload.parameters_json)
    task = AnalysisTaskRead(**payload.model_dump(), status="running", progress=10, started_at=utc_now())
    if data_preparation_plan is not None:
        data_preparation_reference = data_preparation_service.create_task_reference(
            data_preparation_plan.id,
            DataPreparationTaskReferenceCreate(
                module_name=payload.module_name,
                workflow_id=payload.workflow_id,
                expected_revision=data_preparation_plan.revision,
                task_id=task.id,
            ),
        )
        _register_data_preparation_artifacts(task.id, data_preparation_reference.artifact_root)
    _tasks[task.id] = task
    state_store.upsert_item("tasks", task)

    output_dir = DERIVATIVES_ROOT / payload.project_id / task.id
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if payload.module_name == "psd":
            result_paths = run_psd(eeg_file.stored_path, output_dir, payload.parameters_json)
        elif payload.module_name == "erp":
            result_paths = run_erp(eeg_file.stored_path, output_dir, payload.parameters_json)
        elif payload.module_name in {"qc", "preprocess"}:
            if payload.workflow_id in {"qc_waveform_preview", "qc_filter_preview", "qc_snapshot"}:
                result_paths = run_qc_preview(eeg_file.stored_path, output_dir, payload.parameters_json)
            else:
                result_paths = run_quality_check(eeg_file.stored_path, output_dir, payload.parameters_json)
        elif payload.module_name in {"tfr", "pac", "connectivity"}:
            raise ValueError(f"{payload.module_name} is not enabled in V01. Configure preprocessing, events, artifact control, and validation first.")
        else:
            raise ValueError(f"Unsupported analysis module: {payload.module_name}")
    except QcPreviewError as exc:
        task.status = "failed"
        task.progress = 100
        task.error_message = f"{exc.code}: {exc.message}"
        task.finished_at = utc_now()
        _tasks[task.id] = task
        state_store.upsert_item("tasks", task)
        raise HTTPException(status_code=422, detail={"task_id": task.id, "error_code": exc.code, "message": exc.message, "detail": exc.detail}) from exc
    except Exception as exc:
        task.status = "failed"
        task.progress = 100
        task.error_message = str(exc)
        task.finished_at = utc_now()
        _tasks[task.id] = task
        state_store.upsert_item("tasks", task)
        raise HTTPException(status_code=422, detail={"task_id": task.id, "error": str(exc)}) from exc

    for label, path in result_paths.items():
        artifact = ArtifactRead(
            task_id=task.id,
            artifact_type=path.suffix.lstrip(".") or "file",
            label=label,
            path=path,
            mime_type=_guess_mime(path),
        )
        _artifacts[artifact.id] = artifact
        state_store.upsert_item("artifacts", artifact)

    task.status = "completed"
    task.progress = 100
    task.finished_at = utc_now()
    _tasks[task.id] = task
    state_store.upsert_item("tasks", task)
    return task


def get_task(task_id: str) -> AnalysisTaskRead:
    _refresh_tasks()
    try:
        return _tasks[task_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


def list_task_artifacts(task_id: str) -> list[ArtifactRead]:
    _refresh_artifacts()
    return [artifact for artifact in _artifacts.values() if artifact.task_id == task_id]


def get_artifact_download_descriptor(artifact_id: str) -> dict:
    _refresh_artifacts()
    artifact = _artifacts.get(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {
        "artifact_id": artifact.id,
        "label": artifact.label,
        "path": str(artifact.path),
        "mime_type": artifact.mime_type,
    }


def _guess_mime(path: Path) -> str:
    if path.suffix == ".csv":
        return "text/csv"
    if path.suffix == ".json":
        return "application/json"
    if path.suffix == ".html":
        return "text/html"
    if path.suffix == ".txt":
        return "text/plain"
    if path.suffix == ".png":
        return "image/png"
    if path.suffix == ".svg":
        return "image/svg+xml"
    if path.suffix == ".zip":
        return "application/zip"
    return "application/octet-stream"
