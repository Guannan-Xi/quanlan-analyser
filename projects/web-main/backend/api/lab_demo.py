import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from pydantic import BaseModel, Field
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from backend.models.analysis_task import AnalysisTaskRead
from backend.services import lab_demo_service, task_service

# Direct module runners for uploaded-file analysis (no task system)
from eeg_core.analysis.connectivity import run_connectivity
from eeg_core.analysis.erp import run_erp
from eeg_core.analysis.multitaper_psd_tfr import run_multitaper_psd_tfr
from eeg_core.analysis.pac_v2 import run_pac_v2
from eeg_core.analysis.psd import run_psd
from eeg_core.analysis.reference_csd import run_reference_csd
from eeg_core.analysis.tfr import run_tfr

_RUNNER_BY_MODULE = {
    "psd": run_psd,
    "erp": run_erp,
    "erp_p300": run_erp,
    "tfr": run_tfr,
    "multitaper_psd_tfr": run_multitaper_psd_tfr,
    "pac_v2": run_pac_v2,
    "connectivity": run_connectivity,
    "reference_csd": run_reference_csd,
}

_UPLOAD_TEMP = Path(tempfile.gettempdir()) / "qlanalyser_lab_uploads"
_UPLOAD_RESULTS = Path(tempfile.gettempdir()) / "qlanalyser_lab_results"
_SAMPLE_DATA_DIR = Path(__file__).resolve().parents[2] / "work" / "sample_data"
MAX_DEMO_UPLOAD_BYTES = 50 * 1024 * 1024

router = APIRouter()

_TRUE_ENV_VALUES = {"1", "true", "yes", "on", "y"}
_LOCAL_LAB_DEMO_ENVS = {"local", "dev", "development", "test", "ci", "sandbox"}
_DEMO_PROJECT_IDS = {"proj_demo_learning", "proj_demo_epilepsy_lab"}
_DERIVATIVES_ROOT = (Path(__file__).resolve().parents[2] / "data" / "derivatives").resolve()


class LabDemoRunRequest(BaseModel):
    parameters_json: dict = Field(default_factory=dict)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in _TRUE_ENV_VALUES


def _public_lab_demo_enabled() -> bool:
    if _env_flag("QLANALYSER_PUBLIC_LAB_DEMO_ENABLED"):
        return True
    if _env_flag("QLANALYSER_SANDBOX_MODE"):
        return True
    app_env = os.getenv("QLANALYSER_ENV", "").strip().lower()
    return app_env in _LOCAL_LAB_DEMO_ENVS


def _assert_public_lab_demo_enabled() -> None:
    if not _public_lab_demo_enabled():
        raise HTTPException(status_code=404, detail="Public lab demo is disabled")


def _assert_demo_task(task_id: str) -> AnalysisTaskRead:
    """Only serve artifacts for demo-project tasks — no auth needed, but project must be demo."""
    _assert_public_lab_demo_enabled()
    task = task_service.get_task(task_id, requesting_user_id=None)
    if task.project_id not in _DEMO_PROJECT_IDS:
        raise HTTPException(status_code=403, detail="Artifacts only available for demo tasks")
    task_service.assert_task_artifacts_deliverable(task)
    return task


def _assert_path_within_derivatives(raw_path: Path) -> Path:
    resolved = raw_path.resolve()
    try:
        resolved.relative_to(_DERIVATIVES_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Artifact path is outside the allowed directory") from exc
    return resolved


@router.get("/lab/demo/dataset")
def get_demo_dataset() -> dict:
    _assert_public_lab_demo_enabled()
    return lab_demo_service.ensure_demo_dataset()


@router.get("/lab/demo/epilepsy")
def get_epilepsy_demo_dataset() -> dict:
    _assert_public_lab_demo_enabled()
    return lab_demo_service.ensure_epilepsy_demo_dataset()


@router.post("/lab/demo/run/{module}", response_model=AnalysisTaskRead)
def run_demo_module(module: str) -> AnalysisTaskRead:
    _assert_public_lab_demo_enabled()
    try:
        return lab_demo_service.run_demo_task(module, parameters={"__acceptance_run_id": uuid.uuid4().hex})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/lab/demo/run/{module}/configured", response_model=AnalysisTaskRead)
def run_configured_demo_module(module: str, payload: LabDemoRunRequest) -> AnalysisTaskRead:
    _assert_public_lab_demo_enabled()
    try:
        parameters = dict(payload.parameters_json or {})
        parameters.setdefault("__acceptance_run_id", uuid.uuid4().hex)
        return lab_demo_service.run_demo_task(module, parameters=parameters)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/lab/demo/run-all")
def run_all_demo_modules() -> dict:
    _assert_public_lab_demo_enabled()
    tasks = {}
    for module in ("qc", "psd", "band_power", "erp", "reference_csd", "connectivity"):
        tasks[module] = lab_demo_service.run_demo_task(module, parameters={"__acceptance_run_id": uuid.uuid4().hex}).model_dump(mode="json")
    return {"dataset": lab_demo_service.ensure_demo_dataset(), "tasks": tasks}


# ── Public artifact endpoints (no auth, demo-project only) ──

@router.get("/lab/demo/artifacts/{task_id}")
def list_demo_artifacts(task_id: str) -> list[dict]:
    """List artifacts for a demo task. No auth required — restricted to demo projects."""
    task = _assert_demo_task(task_id)
    artifacts = task_service.list_task_artifacts(task_id)
    return [
        {
            "id": a.id,
            "label": a.label or a.artifact_type or "",
            "artifact_type": a.artifact_type,
            "mime_type": a.mime_type,
            "filename": Path(a.path).name if a.path else "",
        }
        for a in artifacts
        if task_service.is_artifact_download_allowed(a, task)
    ]


@router.get("/lab/demo/artifacts/{task_id}/download/{filename:path}")
def download_demo_artifact(task_id: str, filename: str) -> FileResponse:
    """Download a demo artifact by filename. No auth required — restricted to demo projects."""
    task = _assert_demo_task(task_id)
    artifacts = task_service.list_task_artifacts(task_id)
    match = None
    for a in artifacts:
        label = a.label or a.artifact_type or ""
        if label == filename or (a.path and Path(a.path).name == filename):
            match = a
            break
    if not match:
        raise HTTPException(status_code=404, detail=f"Artifact '{filename}' not found for task {task_id}")
    task_service.assert_artifact_download_allowed(match, task)
    path = _assert_path_within_derivatives(Path(match.path)) if match.path else None
    if not path or not path.exists() or not path.is_file():
        raise HTTPException(status_code=410, detail="Artifact file is not available on disk")
    return FileResponse(path, media_type=match.mime_type or "application/octet-stream", filename=path.name)


# ── Upload + analyze (no task system, temp-only, no persistence) ──

@router.post("/lab/demo/analyze-upload")
async def analyze_uploaded_file(
    request: Request,
    file: UploadFile = File(...),
    module: str = Form(...),
    parameters_json: str = Form("{}"),
):
    """Run analysis on an uploaded EEG file. Temp-only, no persistent storage."""
    _assert_public_lab_demo_enabled()
    module = module.lower()
    runner = _RUNNER_BY_MODULE.get(module)
    if runner is None:
        raise HTTPException(status_code=400, detail=f"Unsupported module: {module}. Supported: {', '.join(sorted(_RUNNER_BY_MODULE))}")
    content_length = int(request.headers.get("content-length") or 0)
    if content_length > MAX_DEMO_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Demo upload is too large")

    # Save uploaded file
    suffix = Path(file.filename or "upload").suffix or ".fif"
    run_id = uuid.uuid4().hex[:12]
    _UPLOAD_TEMP.mkdir(parents=True, exist_ok=True)
    tmp_path = _UPLOAD_TEMP / f"lab_upload_{run_id}{suffix}"
    try:
        upload_bytes = await file.read(MAX_DEMO_UPLOAD_BYTES + 1)
        if len(upload_bytes) > MAX_DEMO_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Demo upload is too large")
        tmp_path.write_bytes(upload_bytes)
    except HTTPException:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Failed to read uploaded file")

    # Run analysis
    output_dir = _UPLOAD_RESULTS / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        params = json.loads(parameters_json) if parameters_json else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="parameters_json must be valid JSON") from exc

    try:
        result_paths = runner(str(tmp_path), str(output_dir), params or None)
    except Exception as exc:
        shutil.rmtree(output_dir, ignore_errors=True)
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="Analysis failed for this uploaded file") from exc

    # Cleanup uploaded file (keep results for download)
    tmp_path.unlink(missing_ok=True)

    # Build artifact list
    artifacts = []
    for label, path in result_paths.items():
        p = Path(path)
        if p.exists() and p.is_file():
            mime = "application/json" if p.suffix == ".json" else "text/csv" if p.suffix == ".csv" else "text/plain" if p.suffix == ".txt" else "image/svg+xml" if p.suffix == ".svg" else "application/octet-stream"
            artifacts.append({
                "label": label,
                "filename": p.name,
                "size": p.stat().st_size,
                "mime_type": mime,
            })

    # Register run_id for later download
    _UPLOAD_RUNS[run_id] = {"output_dir": str(output_dir), "artifacts": artifacts, "module": module}

    return {"run_id": run_id, "module": module, "artifact_count": len(artifacts), "artifacts": artifacts}


_UPLOAD_RUNS: dict[str, dict] = {}


@router.get("/lab/demo/upload-result/{run_id}")
def get_upload_result(run_id: str) -> dict:
    """Get result summary for an upload analysis run."""
    _assert_public_lab_demo_enabled()
    if run_id not in _UPLOAD_RUNS:
        raise HTTPException(status_code=404, detail="Run not found (results expire on restart)")
    run = _UPLOAD_RUNS[run_id]
    artifacts = list(run.get("artifacts") or [])
    return {
        "run_id": run_id,
        "module": run.get("module"),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


@router.get("/lab/demo/upload-result/{run_id}/download/{filename:path}")
def download_upload_result(run_id: str, filename: str) -> FileResponse:
    """Download an artifact from an upload analysis run."""
    _assert_public_lab_demo_enabled()
    if run_id not in _UPLOAD_RUNS:
        raise HTTPException(status_code=404, detail="Run not found")
    output_dir = Path(_UPLOAD_RUNS[run_id]["output_dir"]).resolve()
    file_path = (output_dir / filename).resolve()
    try:
        file_path.relative_to(output_dir)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Requested file is outside this run") from exc
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"File '{Path(filename).name}' not found")
    return FileResponse(file_path, filename=file_path.name)


# ── Built-in sample data (zero auth) ──

@router.get("/lab/demo/sample-files")
def list_sample_files() -> dict:
    _assert_public_lab_demo_enabled()
    samples = []
    labels = {
        "resting_alpha": "静息态 Alpha 示例（PSD / Connectivity / PAC）",
        "oddball_p300": "Oddball P300 示例（ERP / TFR）",
        "high_density_32ch": "32通道连接性示例",
    }
    for path in sorted(_SAMPLE_DATA_DIR.glob("*")) if _SAMPLE_DATA_DIR.exists() else []:
        if path.suffix.lower() not in {".fif", ".edf", ".bdf"}:
            continue
        stem = path.stem
        samples.append({
            "id": path.name,
            "filename": path.name,
            "label": labels.get(stem, stem),
            "format": path.suffix.lower().lstrip("."),
            "size_bytes": path.stat().st_size,
        })
    return {"root": "work/sample_data", "samples": samples}


@router.get("/lab/demo/sample-files/{filename:path}")
def download_sample_file(filename: str) -> FileResponse:
    _assert_public_lab_demo_enabled()
    path = (_SAMPLE_DATA_DIR / filename).resolve()
    try:
        path.relative_to(_SAMPLE_DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid sample file path")
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Sample file not found")
    if path.suffix.lower() not in {".fif", ".edf", ".bdf"}:
        raise HTTPException(status_code=403, detail="Unsupported sample file type")
    return FileResponse(path, filename=path.name)
