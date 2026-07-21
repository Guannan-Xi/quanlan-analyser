import hashlib
import json
from pathlib import Path

from fastapi import HTTPException

from backend.models.analysis_task import AnalysisTaskCreate, AnalysisTaskRead
from backend.models.artifact import ArtifactRead
from backend.models.base import utc_now
from backend.models.data_preparation import DataPreparationTaskReferenceCreate
from backend.services import audit_service, billing_service, data_preparation_service, data_source_policy, module_contract_service, quota_service, state_store, storage_service
from eeg_core.analysis.erp import run_erp
from eeg_core.analysis.connectivity import run_connectivity
from eeg_core.analysis.epilepsy import run_epilepsy
from eeg_core.analysis.epilepsy_ml import run_epilepsy_ml
from eeg_core.analysis.multitaper_psd_tfr import run_multitaper_psd_tfr
from eeg_core.analysis.pac import run_pac
from eeg_core.analysis.pac_v2 import run_pac_v2
from eeg_core.analysis.band_power import run_band_power
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
        "outputs": ["tables/spectrum_long.csv", "figures/psd_mean_spectrum.svg", "reproducibility/psd_summary.json", "reproducibility/parameters.json"],
        "production_status": "v01_required",
    },
    {
        "id": "band_power",
        "name": "Band Power",
        "module": "band_power",
        "outputs": [
            "tables/band_power.csv",
            "tables/channel_band_power.csv",
            "figures/band_power.svg",
            "reproducibility/band_power_summary.json",
            "reproducibility/parameters.json",
        ],
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
            "data/epilepsy_ml_spectrogram.json",
            "figures/epilepsy_ml_event_timeline.svg",
            "figures/epilepsy_ml_spectrogram_preview.svg",
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
        "id": "pac_cfc_v2",
        "name": "PAC V2 / lab-only coupling metrics",
        "module": "pac_v2",
        "outputs": [
            "tables/pac_v2_long.csv",
            "tables/pac_v2_channel_summary.csv",
            "reproducibility/parameters.json",
            "reproducibility/table_dictionary.json",
            "reproducibility/scope_contract.json",
        ],
        "production_status": "beta_lab_only_not_formal_delivery",
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

EPILEPSY_RESEARCH_MODULES = {"epilepsy", "epilepsy_ml"}
FORMAL_EPILEPSY_EVIDENCE_BLOCKED_MARKERS = {
    "all_events_evidence_package",
    "event_evidence_package",
    "evidence_package.zip",
    "evidence_packages/",
    "focus_1_35hz",
    "synthetic_preview",
}

_MODULES_ALLOWED_BEFORE_DATA_PREPARATION = {"qc"}
_STRICT_WORKFLOW_BY_MODULE = {
    "epilepsy_ml": "epilepsy_ml_xgboost",
}


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


def _artifact_policy_text(artifact: ArtifactRead | dict) -> str:
    def value(name: str) -> str:
        if isinstance(artifact, dict):
            return str(artifact.get(name) or "")
        return str(getattr(artifact, name, "") or "")

    return " ".join(
        [
            value("label"),
            value("object_key"),
            value("path"),
            value("artifact_type"),
        ]
    ).replace("\\", "/").lower()


def is_artifact_download_allowed(artifact: ArtifactRead | dict, task: AnalysisTaskRead | None = None) -> bool:
    if task is None or task.module_name not in EPILEPSY_RESEARCH_MODULES:
        return True
    text = _artifact_policy_text(artifact)
    return not any(marker in text for marker in FORMAL_EPILEPSY_EVIDENCE_BLOCKED_MARKERS)


def is_task_artifact_delivery_ready(task: AnalysisTaskRead) -> bool:
    if task.status != "completed" or task.queue_status != "completed":
        return False
    billing_transaction_id = task.actual_resource_usage_json.get("billing_transaction_id")
    return billing_service.has_posted_analysis_task_charge(
        task.id,
        transaction_id=str(billing_transaction_id) if billing_transaction_id else None,
        account_id=task.quota_charge_preview_json.get("billing_account_id") or task.owner_user_id,
        module_name=task.module_name,
        expected_credits=float(task.quota_charge_preview_json.get("estimated_credits") or 0) or None,
    )


def assert_task_artifacts_deliverable(task: AnalysisTaskRead) -> None:
    if is_task_artifact_delivery_ready(task):
        return
    if task.status == "payment_failed" or task.error_code == "TASK_PAYMENT_FAILED":
        raise HTTPException(
            status_code=402,
            detail={
                "code": "TASK_PAYMENT_REQUIRED_FOR_ARTIFACT_DELIVERY",
                "message": "Analysis results were generated but the billing charge did not post, so artifacts are not deliverable.",
            },
        )
    if task.status != "completed" or task.queue_status != "completed":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "TASK_ARTIFACTS_NOT_READY",
                "message": "Artifacts are available only after the analysis task completes.",
                "task_status": task.status,
            },
        )
    raise HTTPException(
        status_code=402,
        detail={
            "code": "TASK_CHARGE_REQUIRED_FOR_ARTIFACT_DELIVERY",
            "message": "Completed task artifacts require a posted billing transaction before delivery.",
        },
    )


def assert_artifact_download_allowed(artifact: ArtifactRead | dict, task: AnalysisTaskRead | None = None) -> None:
    if task is not None:
        assert_task_artifacts_deliverable(task)
    if is_artifact_download_allowed(artifact, task):
        return
    raise HTTPException(
        status_code=409,
        detail={
            "code": "FORMAL_EPILEPSY_EVIDENCE_REQUIRES_REAL_WAVEFORM_WINDOWS",
            "message": "Synthetic or legacy epilepsy evidence package artifacts are not source waveform evidence.",
            "suggested_action": "Use real EDF waveform-window extraction before delivering formal epilepsy evidence packages.",
        },
    )


def _data_preparation_artifact_records(task: AnalysisTaskRead, artifact_root: Path) -> list[ArtifactRead]:
    records: list[ArtifactRead] = []
    for relative, label in (
        ("reproducibility/data_preparation_plan.json", "Data preparation plan"),
        ("reproducibility/data_preparation_task_reference.json", "Data preparation task reference"),
        ("reproducibility/data_preparation_artifact_contract.json", "Data preparation artifact contract"),
    ):
        path = artifact_root / relative
        if not path.exists():
            continue
        records.append(
            ArtifactRead(
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
        )
    return records


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

    if module_name not in {"psd", "band_power"}:
        return merged

    psd_json = plan.psd_json if isinstance(plan.psd_json, dict) else {}
    for key in ("fmin", "fmax", "l_freq", "h_freq", "notch_freq", "n_fft", "n_overlap", "reject_by_annotation"):
        if key in psd_json and key not in merged:
            merged[key] = psd_json[key]
    return merged


def _canonical_json_hash(payload: dict) -> str:
    serialized = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _effective_idempotency_key(payload: AnalysisTaskCreate) -> str:
    if payload.idempotency_key:
        return f"client:{payload.idempotency_key}"
    fingerprint = {
        "project_id": payload.project_id,
        "input_file_id": payload.input_file_id,
        "module_name": payload.module_name,
        "workflow_id": payload.workflow_id,
        "parameters_json_sha256": _canonical_json_hash(payload.parameters_json),
    }
    return f"generated:{_canonical_json_hash(fingerprint)}"


def _find_idempotent_task(payload: AnalysisTaskCreate) -> AnalysisTaskRead | None:
    idempotency_key = payload.idempotency_key
    if not idempotency_key:
        return None
    _refresh_tasks()
    for existing_task in _tasks.values():
        if existing_task.owner_user_id != payload.owner_user_id:
            continue
        if existing_task.idempotency_key == idempotency_key:
            return existing_task
    return None


def create_task(payload: AnalysisTaskCreate, requesting_user_id: str | None = None) -> AnalysisTaskRead:
    if requesting_user_id is not None and payload.owner_user_id != requesting_user_id:
        raise HTTPException(status_code=403, detail="Task owner must match the authenticated user")
    project = storage_service.get_project(payload.project_id, requesting_user_id=requesting_user_id)
    eeg_file = storage_service.get_eeg_file(payload.input_file_id, requesting_user_id=requesting_user_id)
    if eeg_file.project_id != payload.project_id:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "TASK_FILE_PROJECT_MISMATCH",
                "message": "The selected EEG file belongs to a different project.",
            },
        )
    if not payload.parameters_json.get("lab_preview_run"):
        data_source_policy.assert_formal_customer_eeg_source(
            project,
            eeg_file,
            owner_user_id=payload.owner_user_id,
            context="task",
        )
    strict_workflow = _STRICT_WORKFLOW_BY_MODULE.get(payload.module_name)
    if strict_workflow and payload.workflow_id != strict_workflow:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "WORKFLOW_CONTRACT_MISMATCH",
                "message": f"{payload.module_name} requires workflow_id={strict_workflow}.",
                "suggested_action": f"Use workflow_id={strict_workflow} for this module.",
            },
        )
    if (
        getattr(eeg_file, "upload_authorization_confirmed", False)
        and payload.module_name not in _MODULES_ALLOWED_BEFORE_DATA_PREPARATION
        and not payload.parameters_json.get("data_preparation_plan_id")
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "DATA_PREPARATION_REQUIRED",
                "message": "Please confirm a data preparation plan before running formal analysis on uploaded EEG data.",
                "suggested_action": "Open Data Preparation, confirm the preparation plan, then start this analysis again.",
            },
        )
    data_preparation_plan = data_preparation_service.validate_task_parameters(
        payload.module_name,
        payload.parameters_json,
        requesting_user_id=payload.owner_user_id,
    )
    if data_preparation_plan is not None:
        if data_preparation_plan.owner_user_id != payload.owner_user_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "DATA_PREPARATION_PLAN_PERMISSION_DENIED",
                    "message": "The data preparation plan belongs to a different user.",
                    "suggested_action": "Use a preparation plan owned by the task owner.",
                },
            )
        if data_preparation_plan.status != "confirmed":
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "DATA_PREPARATION_PLAN_NOT_CONFIRMED",
                    "message": "Formal analysis requires a confirmed data preparation plan.",
                    "suggested_action": "Confirm the data preparation plan before starting analysis.",
                },
            )
        if data_preparation_plan.delivery_scope == "lab_preview_only" and not payload.parameters_json.get("lab_preview_run"):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "LAB_PREVIEW_PLAN_NOT_FORMAL_DELIVERY",
                    "message": "This data preparation plan was created for Module Lab preview and cannot be used as a formal delivery source.",
                    "suggested_action": "Create a formal data preparation plan, or mark the task as a lab preview run.",
                },
            )
        if data_preparation_plan.input_file_id != payload.input_file_id:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "DATA_PREPARATION_FILE_MISMATCH",
                    "message": "The data preparation plan belongs to a different EEG file.",
                    "suggested_action": "Use the confirmed preparation plan for the selected EEG file.",
                },
            )
        if data_preparation_plan.project_id != payload.project_id:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "DATA_PREPARATION_PROJECT_MISMATCH",
                    "message": "The data preparation plan belongs to a different project.",
                    "suggested_action": "Use a preparation plan from the current project.",
                },
            )
    effective_parameters = _merge_plan_into_task_parameters(payload.module_name, payload.parameters_json, data_preparation_plan)
    payload = payload.model_copy(update={"parameters_json": effective_parameters})
    payload = payload.model_copy(update={"idempotency_key": _effective_idempotency_key(payload)})
    existing_task = _find_idempotent_task(payload)
    if existing_task is not None:
        return existing_task
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
    data_preparation_artifacts: list[ArtifactRead] = []
    if data_preparation_plan is not None:
        data_preparation_reference = data_preparation_service.create_task_reference(
            data_preparation_plan.id,
            DataPreparationTaskReferenceCreate(
                module_name=payload.module_name,
                workflow_id=payload.workflow_id,
                expected_revision=data_preparation_plan.revision,
                task_id=task.id,
            ),
            requesting_user_id=payload.owner_user_id,
        )
        data_preparation_artifacts = _data_preparation_artifact_records(task, data_preparation_reference.artifact_root)
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
        elif payload.module_name == "band_power":
            result_paths = run_band_power(eeg_file.stored_path, output_dir, payload.parameters_json)
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
        elif payload.module_name == "pac_v2":
            result_paths = run_pac_v2(eeg_file.stored_path, output_dir, payload.parameters_json)
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
        
        # P0-DATA-01 FIX: Do NOT refund on failure
        # Current billing model: charge AFTER success, so no refund needed on failure
        # (Previous code incorrectly refunded, causing balance increase)
        
        audit_service.record_event(
            action="analysis_task.failed",
            object_type="analysis_task",
            object_id=task.id,
            organization_id=task.organization_id,
            project_id=task.project_id,
            actor_user_id=task.owner_user_id,
            metadata_json={"error_code": exc.code, "message": exc.message},
        )
        raise HTTPException(status_code=422, detail={"task_id": task.id, "error_code": exc.code, "message": exc.message}) from exc
    except Exception as exc:
        task.status = "failed"
        task.queue_status = "failed"
        task.progress = 100
        task.error_code = "TASK_EXECUTION_FAILED"
        task.error_message = "Analysis task failed during execution. Contact support with the task_id if the issue persists."
        task.finished_at = utc_now()
        task.updated_at = task.finished_at
        _tasks[task.id] = task
        state_store.upsert_item("tasks", task)
        
        # P0-DATA-01 FIX: Do NOT refund on failure
        # Current billing model: charge AFTER success, so no refund needed on failure
        
        audit_service.record_event(
            action="analysis_task.failed",
            object_type="analysis_task",
            object_id=task.id,
            organization_id=task.organization_id,
            project_id=task.project_id,
            actor_user_id=task.owner_user_id,
            metadata_json={"error_code": task.error_code, "message": task.error_message},
        )
        raise HTTPException(status_code=422, detail={"task_id": task.id, "error_code": task.error_code, "message": task.error_message}) from exc

    charged = False
    try:
        registered_object_keys: set[str] = set()
        registered_paths: set[str] = set()
        artifact_records: list[ArtifactRead] = list(data_preparation_artifacts)
        for label, raw_path in result_paths.items():
            path = Path(raw_path)
            metadata = _artifact_file_metadata(path, task.project_id, task.id)
            object_key = str(metadata.get("object_key") or "")
            path_key = str(path.resolve())
            if (object_key and object_key in registered_object_keys) or path_key in registered_paths:
                continue
            if object_key:
                registered_object_keys.add(object_key)
            registered_paths.add(path_key)
            artifact_records.append(
                ArtifactRead(
                    task_id=task.id,
                    organization_id=task.organization_id,
                    project_id=task.project_id,
                    input_file_id=task.input_file_id,
                    artifact_type=path.suffix.lstrip(".") or "file",
                    label=label,
                    path=path,
                    mime_type=_guess_mime(path),
                    **metadata,
                )
            )

        task.actual_resource_usage_json = {
            "artifact_count": len(artifact_records),
            "output_storage_bytes": sum(int(artifact.size_bytes or 0) for artifact in artifact_records),
            "worker_id": task.worker_id,
        }
        billing_transaction = billing_service.charge_analysis_task(
            account_id=task.quota_charge_preview_json.get("billing_account_id"),
            task_id=task.id,
            module_name=task.module_name,
            quantity_credits=float(task.quota_charge_preview_json.get("estimated_credits") or 0),
            metadata_json=task.actual_resource_usage_json,
        )
        charged = True
        task.actual_resource_usage_json["billing_transaction_id"] = billing_transaction.id
        task.actual_resource_usage_json["charged_credits"] = task.quota_charge_preview_json.get("estimated_credits")
        for artifact in artifact_records:
            _artifacts[artifact.id] = artifact
        state_store.upsert_items("artifacts", artifact_records)
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
            quota_account_id=task.quota_charge_preview_json.get("billing_account_id"),
            metadata_json=task.actual_resource_usage_json,
        )
        task.status = "completed"
        task.queue_status = "completed"
        task.progress = 100
        task.finished_at = utc_now()
        task.updated_at = task.finished_at
        _tasks[task.id] = task
        state_store.upsert_item("tasks", task)
        try:
            audit_service.record_event(
                action="analysis_task.completed",
                object_type="analysis_task",
                object_id=task.id,
                organization_id=task.organization_id,
                project_id=task.project_id,
                actor_user_id=task.owner_user_id,
                metadata_json=task.actual_resource_usage_json,
            )
        except Exception:
            pass
        return task
    except HTTPException as exc:
        if not charged and exc.status_code == 402:
            task.status = "payment_failed"
            task.queue_status = "payment_failed"
            task.progress = 100
            task.error_code = "TASK_PAYMENT_FAILED"
            task.error_message = "Analysis task finished but billing charge failed; no completed usage was recorded."
            task.finished_at = utc_now()
            task.updated_at = task.finished_at
            _tasks[task.id] = task
            state_store.upsert_item("tasks", task)
            audit_service.record_event(
                action="analysis_task.payment_failed",
                object_type="analysis_task",
                object_id=task.id,
                organization_id=task.organization_id,
                project_id=task.project_id,
                actor_user_id=task.owner_user_id,
                metadata_json={"error_code": task.error_code, "message": task.error_message},
            )
        raise
    except Exception as exc:
        if charged:
            task.status = "delivery_failed_after_charge"
            task.queue_status = "failed"
            task.progress = 100
            task.error_code = "TASK_DELIVERY_FAILED_AFTER_CHARGE"
            task.error_message = "Analysis task was charged, but artifact delivery finalization failed. Contact support with the task_id."
            task.finished_at = task.finished_at or utc_now()
            task.updated_at = utc_now()
            _tasks[task.id] = task
            state_store.upsert_item("tasks", task)
            audit_service.record_event(
                action="analysis_task.delivery_failed_after_charge",
                object_type="analysis_task",
                object_id=task.id,
                organization_id=task.organization_id,
                project_id=task.project_id,
                actor_user_id=task.owner_user_id,
                metadata_json={
                    "error_code": task.error_code,
                    "message": task.error_message,
                    "billing_transaction_id": task.actual_resource_usage_json.get("billing_transaction_id"),
                },
            )
            raise HTTPException(status_code=422, detail={"task_id": task.id, "error_code": task.error_code, "message": task.error_message}) from exc
        task.status = "failed"
        task.queue_status = "failed"
        task.progress = 100
        task.error_code = "TASK_FINALIZATION_FAILED"
        task.error_message = "Analysis task finished but result registration failed. Contact support with the task_id."
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
        raise HTTPException(status_code=422, detail={"task_id": task.id, "error_code": task.error_code, "message": task.error_message}) from exc


def get_task(task_id: str, requesting_user_id: str | None = None) -> AnalysisTaskRead:
    """Get task by ID with optional permission check.
    
    Args:
        task_id: The task ID to retrieve
        requesting_user_id: If provided, check that the user owns the task
        
    Raises:
        HTTPException: 404 if task not found, 403 if permission denied
    """
    _refresh_tasks()
    try:
        task = _tasks[task_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc
    
    # P0-SEC-01 FIX: Add ownership check to prevent cross-user access
    if requesting_user_id is not None and task.owner_user_id != requesting_user_id:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PERMISSION_DENIED",
                "message": "You do not have permission to access this task"
            }
        )
    
    return task


def list_tasks(owner_user_id: str | None = None) -> list[AnalysisTaskRead]:
    """List tasks with optional filtering by owner.
    
    Args:
        owner_user_id: If provided, only return tasks owned by this user
        
    Returns:
        List of tasks matching the criteria
    """
    _refresh_tasks()
    # P0-SEC-01 FIX: Filter tasks by owner to prevent cross-user access
    if owner_user_id is not None:
        return [task for task in _tasks.values() if task.owner_user_id == owner_user_id]
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
        "task_id": artifact.task_id,
        "project_id": artifact.project_id,
        "label": artifact.label,
        "artifact_type": artifact.artifact_type,
        "path": str(artifact.path),
        "object_key": artifact.object_key,
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
