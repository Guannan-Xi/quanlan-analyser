import hashlib
from pathlib import Path

from fastapi import HTTPException

from backend.models.analysis_task import AnalysisTaskCreate, AnalysisTaskRead
from backend.models.artifact import ArtifactRead
from backend.models.base import utc_now
from backend.models.data_preparation import DataPreparationTaskReferenceCreate
from backend.services import audit_service, billing_service, data_preparation_service, module_contract_service, quota_service, state_store, storage_service
from eeg_core.analysis.erp import run_erp
from eeg_core.analysis.connectivity import run_connectivity
from eeg_core.analysis.epilepsy import run_epilepsy
from eeg_core.analysis.epilepsy_ml import run_epilepsy_ml
from eeg_core.analysis.multitaper_psd_tfr import run_multitaper_psd_tfr
from eeg_core.analysis.pac import run_pac
from eeg_core.analysis.psd import run_psd
from eeg_core.analysis.reference_csd import run_reference_csd
from eeg_core.analysis.tfr import run_tfr
from eeg_core.preprocess.quality import run_quality_check
from eeg_core.preprocess.qc_preview import QcPreviewError, run_qc_preview

ROOT = Path(__file__).resolve().parents[2]
DERIVATIVES_ROOT = ROOT / "data" / "derivatives"
run_erp_p300 = run_erp

_BASE_WORKFLOW_TEMPLATES = [
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
        "id": "preprocessing_readiness",
        "name": "Preprocessing readiness / data preparation",
        "module": "preprocess",
        "outputs": [],
        "production_status": "internal_validation_contract_loaded",
        "enabled": False,
    },
    {
        "id": "event_epoch_prepare",
        "name": "Event and epoch preparation",
        "module": "event_epoch",
        "outputs": [],
        "production_status": "internal_validation_contract_loaded",
        "enabled": False,
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
        "id": "epilepsy_std_threshold",
        "name": "Epileptiform event research screening / STD threshold",
        "module": "epilepsy",
        "outputs": [
            "tables/epilepsy_epoch_scores.csv",
            "tables/epilepsy_events.csv",
            "tables/epilepsy_window_stats_30min.csv",
            "reproducibility/epilepsy_summary.json",
            "reproducibility/parameters.json",
        ],
        "production_status": "internal_validation_non_medical_research_screening",
    },

    {
        "id": "epilepsy_ml_xgboost",
        "name": "Epilepsy ML source-compatible XGBoost screening",
        "module": "epilepsy_ml",
        "outputs": [
            "tables/epilepsy_ml_epoch_predictions.csv",
            "tables/epilepsy_ml_events.csv",
            "tables/epilepsy_ml_features.csv",
            "tables/epilepsy_ml_features_scaled.csv",
            "reproducibility/epilepsy_ml_summary.json",
            "reproducibility/epilepsy_ml_model_manifest.json",
            "reproducibility/parameters.json",
        ],
        "production_status": "source_model_migration_non_medical_research_screening",
    },
    {
        "id": "tfr_ersp_itc",
        "name": "Time-frequency / ERSP / ITC",
        "module": "tfr",
        "outputs": [],
        "production_status": "runnable_epoch_based_research_method",
        "enabled": True,
    },
    {
        "id": "pac_cfc",
        "name": "PAC / Cross-frequency coupling",
        "module": "pac",
        "outputs": [
            "tables/pac_comodulogram_long.csv",
            "tables/pac_binned_amplitude.csv",
            "tables/pac_dynamic_curve.csv",
            "tables/pac_channel_summary.csv",
            "figures/pac_comodulogram.svg",
            "reproducibility/pac_summary.json",
            "reproducibility/parameters.json",
        ],
        "production_status": "runnable_single_record_sensor_space_pac",
        "enabled": True,
    },
    {
        "id": "reference_csd",
        "name": "CSD 电流源密度计算",
        "module": "reference_csd",
        "outputs": [
            "tables/reference_channels.csv",
            "tables/bipolar_pairs.csv",
            "figures/reference_before_after_preview.svg",
            "figures/csd_before_after_preview.svg",
            "reproducibility/reference_summary.json",
            "reproducibility/csd_summary.json",
            "reproducibility/parameters.json",
        ],
        "production_status": "runnable_sensor_space_csd_requires_montage",
        "enabled": True,
    },
    {
        "id": "multitaper_psd_tfr",
        "name": "Multitaper PSD / TFR",
        "module": "multitaper_psd_tfr",
        "outputs": [
            "tables/multitaper_psd_by_channel_frequency.csv",
            "tables/multitaper_band_power.csv",
            "tables/multitaper_tfr_power_long.csv",
            "tables/multitaper_tfr_itc_long.csv",
            "figures/multitaper_psd_curve.svg",
            "figures/multitaper_tfr_heatmap.svg",
            "figures/method_comparison_preview.svg",
            "reproducibility/multitaper_summary.json",
            "reproducibility/parameters.json",
        ],
        "production_status": "runnable_multitaper_psd_tfr",
        "enabled": True,
    },
    {
        "id": "sensor_topography",
        "name": "Sensor topography",
        "module": "sensor_topography",
        "outputs": [],
        "production_status": "draft_sensor_space_only",
        "enabled": False,
    },
    {
        "id": "connectivity",
        "name": "Connectivity 连接性分析",
        "module": "connectivity",
        "outputs": [
            "tables/connectivity_matrix.csv",
            "tables/connectivity_edges_long.csv",
            "figures/connectivity_matrix.svg",
            "reproducibility/connectivity_summary.json",
            "reproducibility/parameters.json",
        ],
        "production_status": "runnable_sensor_space_connectivity",
        "enabled": True,
    },
    {
        "id": "source_localization_boundary",
        "name": "Source localization boundary",
        "module": "source_localization",
        "outputs": [],
        "production_status": "draft_boundary_only_no_v01_execution",
        "enabled": False,
    },
]

WORKFLOW_TEMPLATES = module_contract_service.enrich_workflow_templates(_BASE_WORKFLOW_TEMPLATES)

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


def _artifact_file_metadata(path: Path, project_id: str, task_id: str) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    try:
        relative = path.relative_to(DERIVATIVES_ROOT / project_id).as_posix()
    except ValueError:
        relative = f"external/{task_id}/{path.name}"
    return {
        "object_key": f"derivatives/{project_id}/{relative}",
        "size_bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
        "quota_usage_json": {
            "resource_type": "artifact_storage_bytes",
            "quantity": path.stat().st_size,
            "unit": "bytes",
            "billable": False,
        },
    }


def _register_data_preparation_artifacts(task: AnalysisTaskRead, artifact_root: Path) -> None:
    for relative, label in (
        ("reproducibility/data_preparation_plan.json", "Data preparation plan"),
        ("reproducibility/data_preparation_task_reference.json", "Data preparation task reference"),
        ("reproducibility/data_preparation_artifact_contract.json", "Data preparation artifact contract"),
    ):
        path = artifact_root / relative
        if not path.exists():
            continue
        artifact = ArtifactRead(
            task_id=task.id,
            organization_id=task.organization_id,
            project_id=task.project_id,
            input_file_id=task.input_file_id,
            artifact_type="json",
            label=label,
            path=path,
            mime_type="application/json",
            **_artifact_file_metadata(path, task.project_id, task.id),
        )
        _artifacts[artifact.id] = artifact
        state_store.upsert_item("artifacts", artifact)


def _channel_name(value) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        candidate = value.get("name") or value.get("channel") or value.get("channel_name") or value.get("label")
        return str(candidate) if candidate else None
    return None


def _segment_payload(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    start = value.get("onset", value.get("start", value.get("start_sec", value.get("startSec"))))
    duration = value.get("duration", value.get("duration_sec", value.get("durationSec")))
    end = value.get("end", value.get("end_sec", value.get("endSec")))
    try:
        onset = float(start)
        if duration is None and end is not None:
            duration = float(end) - onset
        duration = float(duration)
    except (TypeError, ValueError):
        return None
    if onset < 0 or duration <= 0:
        return None
    return {
        "onset": onset,
        "duration": duration,
        "description": str(value.get("description") or value.get("reason") or "bad_data_preparation_segment"),
    }


def _merge_plan_into_task_parameters(module_name: str, parameters: dict, plan) -> dict:
    if plan is None:
        return parameters
    merged = dict(parameters)
    merged.setdefault("data_preparation_plan_id", plan.id)
    merged.setdefault("data_preparation_revision", plan.revision)

    qc_json = plan.qc_json if isinstance(plan.qc_json, dict) else {}

    plan_bad_channels = list(plan.bad_channels or []) or list(qc_json.get("bad_channels") or [])
    bad_channels = []
    for item in plan_bad_channels:
        name = _channel_name(item)
        if name and name not in bad_channels:
            bad_channels.append(name)
    if bad_channels and not merged.get("bad_channels"):
        merged["bad_channels"] = bad_channels

    plan_bad_segments = list(plan.bad_segments or []) or list(qc_json.get("bad_segments") or [])
    bad_segments = []
    for item in plan_bad_segments:
        segment = _segment_payload(item)
        if segment:
            bad_segments.append(segment)
    if bad_segments and not merged.get("bad_segments"):
        merged["bad_segments"] = bad_segments

    annotation_actions = list(plan.annotation_actions or []) or list(qc_json.get("annotation_actions") or [])
    if annotation_actions and not merged.get("annotation_actions"):
        merged["annotation_actions"] = annotation_actions

    if module_name != "psd":
        return merged

    psd_json = plan.psd_json if isinstance(plan.psd_json, dict) else {}
    for key in ("fmin", "fmax", "l_freq", "h_freq", "notch_freq", "n_fft", "n_overlap", "reject_by_annotation"):
        if key in psd_json and key not in merged:
            merged[key] = psd_json[key]
    return merged


def create_task(payload: AnalysisTaskCreate) -> AnalysisTaskRead:
    eeg_file = storage_service.get_eeg_file(payload.input_file_id)
    data_preparation_plan = data_preparation_service.validate_task_parameters(payload.module_name, payload.parameters_json)
    effective_parameters = _merge_plan_into_task_parameters(payload.module_name, payload.parameters_json, data_preparation_plan)
    payload = payload.model_copy(update={"parameters_json": effective_parameters})
    estimate = quota_service.task_resource_estimate(payload.module_name, eeg_file.size_bytes, payload.parameters_json)
    quota_preview = quota_service.task_quota_preview(estimate)
    billing_account_id = billing_service.normalize_account_id(payload.owner_user_id)
    task_price_credits = billing_service.estimate_task_price(payload.module_name, payload.workflow_id)
    billing_service.assert_sufficient_balance(billing_account_id, task_price_credits)
    task = AnalysisTaskRead(
        **payload.model_dump(),
        status="queued",
        queue_status="queued",
        progress=0,
        resource_estimate_json=estimate,
        quota_charge_preview_json={**quota_preview, "estimated_credits": task_price_credits, "billing_account_id": billing_account_id},
        data_preparation_plan_id=data_preparation_plan.id if data_preparation_plan else None,
        data_preparation_revision=data_preparation_plan.revision if data_preparation_plan else None,
        data_preparation_contract_version=payload.parameters_json.get("data_preparation_contract_version"),
    )
    queued_audit = audit_service.record_event(
        action="analysis_task.queued",
        object_type="analysis_task",
        object_id=task.id,
        organization_id=task.organization_id,
        project_id=task.project_id,
        actor_user_id=task.owner_user_id,
        metadata_json={
            "module_name": task.module_name,
            "workflow_id": task.workflow_id,
            "input_file_id": task.input_file_id,
            "queue_name": task.queue_name,
        },
    )
    task.audit_trace_id = queued_audit.audit_trace_id
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
        _register_data_preparation_artifacts(task, data_preparation_reference.artifact_root)
    _tasks[task.id] = task
    state_store.upsert_item("tasks", task)
    task.status = "running"
    task.queue_status = "running"
    task.progress = 10
    task.worker_id = "local-sync-worker"
    task.started_at = utc_now()
    task.updated_at = utc_now()
    state_store.upsert_item("tasks", task)

    output_dir = DERIVATIVES_ROOT / payload.project_id / task.id
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if payload.module_name == "psd":
            result_paths = run_psd(eeg_file.stored_path, output_dir, payload.parameters_json)
        elif payload.module_name == "erp":
            result_paths = run_erp_p300(eeg_file.stored_path, output_dir, payload.parameters_json)
        elif payload.module_name == "epilepsy":
            result_paths = run_epilepsy(eeg_file.stored_path, output_dir, payload.parameters_json)
        elif payload.module_name == "epilepsy_ml":
            result_paths = run_epilepsy_ml(eeg_file.stored_path, output_dir, payload.parameters_json)
        elif payload.module_name == "reference_csd":
            result_paths = run_reference_csd(eeg_file.stored_path, output_dir, payload.parameters_json)
        elif payload.module_name == "connectivity":
            result_paths = run_connectivity(eeg_file.stored_path, output_dir, payload.parameters_json)
        elif payload.module_name == "pac":
            result_paths = run_pac(eeg_file.stored_path, output_dir, payload.parameters_json)
        elif payload.module_name in {"qc", "preprocess"}:
            if payload.workflow_id in {"qc_waveform_preview", "qc_filter_preview", "qc_snapshot"}:
                result_paths = run_qc_preview(eeg_file.stored_path, output_dir, payload.parameters_json)
            else:
                result_paths = run_quality_check(eeg_file.stored_path, output_dir, payload.parameters_json)
        elif payload.module_name == "tfr":
            result_paths = run_tfr(eeg_file.stored_path, output_dir, payload.parameters_json)
        elif payload.module_name == "multitaper_psd_tfr":
            result_paths = run_multitaper_psd_tfr(eeg_file.stored_path, output_dir, payload.parameters_json)
        elif payload.module_name in {"multitaper", "sensor_topography", "source_localization"}:
            raise ValueError(f"{payload.module_name} is not enabled in V01. Configure preprocessing, events, artifact control, and validation first.")
        else:
            raise ValueError(f"Unsupported analysis module: {payload.module_name}")
    except QcPreviewError as exc:
        task.status = "failed"
        task.queue_status = "failed"
        task.progress = 100
        task.error_code = exc.code
        task.error_message = f"{exc.code}: {exc.message}"
        task.finished_at = utc_now()
        task.updated_at = task.finished_at
        _tasks[task.id] = task
        state_store.upsert_item("tasks", task)
        audit_service.record_event(
            action="analysis_task.failed",
            object_type="analysis_task",
            object_id=task.id,
            organization_id=task.organization_id,
            project_id=task.project_id,
            actor_user_id=task.owner_user_id,
            metadata_json={"error_code": exc.code, "message": exc.message},
        )
        raise HTTPException(status_code=422, detail={"task_id": task.id, "error_code": exc.code, "message": exc.message, "detail": exc.detail}) from exc
    except Exception as exc:
        task.status = "failed"
        task.queue_status = "failed"
        task.progress = 100
        task.error_code = "TASK_EXECUTION_FAILED"
        task.error_message = str(exc)
        task.finished_at = utc_now()
        task.updated_at = task.finished_at
        _tasks[task.id] = task
        state_store.upsert_item("tasks", task)
        audit_service.record_event(
            action="analysis_task.failed",
            object_type="analysis_task",
            object_id=task.id,
            organization_id=task.organization_id,
            project_id=task.project_id,
            actor_user_id=task.owner_user_id,
            metadata_json={"error_code": task.error_code, "message": task.error_message},
        )
        raise HTTPException(status_code=422, detail={"task_id": task.id, "error": str(exc)}) from exc

    for label, path in result_paths.items():
        artifact = ArtifactRead(
            task_id=task.id,
            organization_id=task.organization_id,
            project_id=task.project_id,
            input_file_id=task.input_file_id,
            artifact_type=path.suffix.lstrip(".") or "file",
            label=label,
            path=path,
            mime_type=_guess_mime(path),
            **_artifact_file_metadata(path, task.project_id, task.id),
        )
        _artifacts[artifact.id] = artifact
        state_store.upsert_item("artifacts", artifact)

    task.status = "completed"
    task.queue_status = "completed"
    task.progress = 100
    task.finished_at = utc_now()
    task.updated_at = task.finished_at
    task.actual_resource_usage_json = {
        "artifact_count": len(result_paths),
        "output_storage_bytes": sum(Path(path).stat().st_size for path in result_paths.values() if Path(path).exists()),
        "worker_id": task.worker_id,
    }
    quota_service.record_usage(
        resource_type="analysis_task",
        action="analysis_task.completed",
        quantity=1,
        unit="task",
        source_type="analysis_task",
        source_id=task.id,
        organization_id=task.organization_id,
        project_id=task.project_id,
        owner_user_id=task.owner_user_id,
        metadata_json=task.actual_resource_usage_json,
    )
    billing_transaction = billing_service.charge_analysis_task(
        account_id=task.quota_charge_preview_json.get("billing_account_id"),
        task_id=task.id,
        module_name=task.module_name,
        quantity_credits=float(task.quota_charge_preview_json.get("estimated_credits") or 0),
        metadata_json=task.actual_resource_usage_json,
    )
    task.actual_resource_usage_json["billing_transaction_id"] = billing_transaction.id
    task.actual_resource_usage_json["charged_credits"] = task.quota_charge_preview_json.get("estimated_credits")
    audit_service.record_event(
        action="analysis_task.completed",
        object_type="analysis_task",
        object_id=task.id,
        organization_id=task.organization_id,
        project_id=task.project_id,
        actor_user_id=task.owner_user_id,
        metadata_json=task.actual_resource_usage_json,
    )
    _tasks[task.id] = task
    state_store.upsert_item("tasks", task)
    return task


def get_task(task_id: str) -> AnalysisTaskRead:
    _refresh_tasks()
    try:
        return _tasks[task_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


def list_tasks() -> list[AnalysisTaskRead]:
    _refresh_tasks()
    return list(_tasks.values())


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
