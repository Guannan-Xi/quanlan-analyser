from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from backend.models.analysis_task import AnalysisTaskCreate, AnalysisTaskRead
from backend.models.eeg_file import EEGFileRead
from backend.models.project import ProjectRead
from backend.services import storage_service, task_service
from scripts.generate_teaching_oddball_case import build_raw


ROOT = Path(__file__).resolve().parents[2]
DEMO_ROOT = ROOT / "data" / "demo"
DEMO_PROJECT_ID = "proj_demo_learning"
DEMO_FILE_ID = "eeg_demo_teaching_oddball"
EPILEPSY_DEMO_PROJECT_ID = "proj_demo_epilepsy_lab"
EPILEPSY_DEMO_FILE_ID = "eeg_demo_epilepsy_high_amplitude"
EPILEPSY_DEMO_FIXTURE_ID = "epilepsy_ml_demo_source_channels_v1"
EPILEPSY_DEMO_ROOT = ROOT / "work" / "e2e_epilepsy_ml_demo"
EPILEPSY_DEMO_RAW_PATH = EPILEPSY_DEMO_ROOT / "epilepsy_ml_demo_source_channels.edf"
EPILEPSY_DEMO_METADATA_PATH = EPILEPSY_DEMO_ROOT / "epilepsy_ml_demo_source_channels_metadata.json"

WORKFLOW_BY_MODULE = {
    "qc": "metadata_qc",
    "psd": "resting_psd",
    "erp": "erp_p300",
    "epilepsy": "epilepsy_std_threshold",
    "epilepsy_ml": "epilepsy_ml_xgboost",
    "pac": "pac_cfc",
    "reference_csd": "reference_csd",
    "multitaper_psd_tfr": "multitaper_psd_tfr",
    "connectivity": "connectivity",
}


def ensure_demo_dataset() -> dict:
    DEMO_ROOT.mkdir(parents=True, exist_ok=True)
    edf_path = DEMO_ROOT / "teaching_oddball.edf"
    fif_path = DEMO_ROOT / "teaching_oddball_with_montage_raw.fif"
    events_tsv_path = DEMO_ROOT / "teaching_oddball_events.tsv"
    if not edf_path.exists() or not fif_path.exists() or not events_tsv_path.exists():
        raw = build_raw()
        raw.save(fif_path, overwrite=True, verbose="ERROR")
        raw.export(edf_path, fmt="edf", overwrite=True, verbose="ERROR")
        with events_tsv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["onset", "duration", "trial_type"], delimiter="\t")
            writer.writeheader()
            for onset, duration, description in zip(raw.annotations.onset, raw.annotations.duration, raw.annotations.description):
                writer.writerow(
                    {
                        "onset": f"{float(onset):.3f}",
                        "duration": f"{float(duration):.3f}",
                        "trial_type": str(description),
                    }
                )

    project = ProjectRead(
        id=DEMO_PROJECT_ID,
        name="体验中心示例项目",
        description="内置合成 oddball EEG，用于学习 QC、数据准备、CSD 和分析报告的完整流程。",
        research_type="event_related_learning_demo",
        owner_id="public-demo",
        permission_policy={
            "teaching_mode": True,
            "protected_teaching_dataset": True,
            "archive_policy": "not_allowed",
            "delete_policy": "not_allowed",
            "rename_policy": "not_allowed",
        },
    )
    storage_service.upsert_project(project)

    eeg_file = EEGFileRead(
        id=DEMO_FILE_ID,
        project_id=DEMO_PROJECT_ID,
        subject_id="demo_subject_01",
        original_filename="teaching_oddball_with_montage_raw.fif",
        stored_path=fif_path,
        detected_format="fif",
        sampling_rate=250.0,
        channel_count=8,
        duration_sec=60.0,
        metadata_json={
            "demo": True,
            "teaching_mode": True,
            "protected_teaching_dataset": True,
            "delete_policy": "not_allowed",
            "rename_policy": "not_allowed",
            "description": "Synthetic posterior 10 Hz alpha plus target-enhanced P300-like response.",
            "events": {"standard": 24, "target": 12},
            "channels": ["Fz", "Cz", "Pz", "Oz", "P3", "P4", "O1", "O2"],
            "edf_path": str(edf_path),
            "events_tsv_path": str(events_tsv_path),
            "montage": "standard_1020",
        },
        permission_policy={
            "teaching_mode": True,
            "protected_teaching_dataset": True,
            "delete_policy": "not_allowed",
            "rename_policy": "not_allowed",
        },
        retention_policy="protected_teaching_demo",
    )
    storage_service.register_eeg_file(eeg_file)
    return {"project": project.model_dump(mode="json"), "file": eeg_file.model_dump(mode="json")}


def ensure_epilepsy_demo_dataset() -> dict:
    _ensure_epilepsy_fixture_exists()
    metadata = _read_epilepsy_metadata()
    project = ProjectRead(
        id=EPILEPSY_DEMO_PROJECT_ID,
        name="Epilepsy research lab demo",
        description="Synthetic high-amplitude EEG fixture for epilepsy research screening workbench and ML migration tests.",
        research_type="epilepsy_research_screening_demo",
        owner_id="public-demo",
        permission_policy={
            "teaching_mode": True,
            "protected_teaching_dataset": True,
            "archive_policy": "not_allowed",
            "delete_policy": "not_allowed",
            "rename_policy": "not_allowed",
        },
    )
    storage_service.upsert_project(project)

    eeg_file = EEGFileRead(
        id=EPILEPSY_DEMO_FILE_ID,
        project_id=EPILEPSY_DEMO_PROJECT_ID,
        subject_id="epilepsy_demo_subject_01",
        original_filename=EPILEPSY_DEMO_RAW_PATH.name,
        stored_path=EPILEPSY_DEMO_RAW_PATH,
        detected_format="edf",
        sampling_rate=float(metadata.get("sfreq") or 250.0),
        channel_count=len(metadata.get("channels") or []),
        duration_sec=float(metadata.get("duration_sec") or 60.0),
        size_bytes=EPILEPSY_DEMO_RAW_PATH.stat().st_size,
        sha256=_sha256(EPILEPSY_DEMO_RAW_PATH),
        metadata_json={
            "demo": True,
            "teaching_mode": True,
            "protected_teaching_dataset": True,
            "delete_policy": "not_allowed",
            "rename_policy": "not_allowed",
            "fixture_id": EPILEPSY_DEMO_FIXTURE_ID,
            "ml_fixture_ready": True,
            "description": "Synthetic source-channel research/demo EEG with ML-trigger candidate epochs.",
            "channels": metadata.get("channels") or [],
            "selected_channel": metadata.get("selected_channel"),
            "expected_trigger_window_sec": metadata.get("expected_trigger_window_sec"),
            "source_metadata_path": str(EPILEPSY_DEMO_METADATA_PATH),
            "non_medical_boundary": "Synthetic research/demo data only; not clinical EEG and not for diagnosis.",
        },
        permission_policy={
            "teaching_mode": True,
            "protected_teaching_dataset": True,
            "delete_policy": "not_allowed",
            "rename_policy": "not_allowed",
        },
        retention_policy="protected_teaching_demo",
        status="metadata_ready",
        upload_status="registered_demo_fixture",
    )
    storage_service.register_eeg_file(eeg_file)
    return {
        "fixture_id": EPILEPSY_DEMO_FIXTURE_ID,
        "status": "ready",
        "project": project.model_dump(mode="json"),
        "file": eeg_file.model_dump(mode="json"),
    }


def default_parameters(module: str) -> dict:
    if module == "qc":
        return {}
    if module == "psd":
        return {"fmin": 1, "fmax": 40}
    if module == "erp":
        return {
            "event_id": {"standard": 1, "target": 2},
            "event_id_confirmed": True,
            "tmin": -0.2,
            "tmax": 0.8,
            "baseline": [None, 0],
            "l_freq": 0.1,
            "h_freq": 30.0,
            "reference": "average",
        }
    if module == "epilepsy":
        return {
            "method": "std_threshold",
            "epoch_length_sec": 5,
            "std_factor": 2.0,
            "rms_window_samples": 15,
            "merge_gap_epoch_num": 1,
            "min_event_epochs": 2,
            "event_window_sec": 1800,
        }
    if module == "epilepsy_ml":
        return {
            "method": "ml_epoch_classifier",
            "epoch_length_sec": 5,
            "probability_threshold": 0.5,
            "unit_mode": "source_compatible",
            "lab_mode": True,
            "lab_fixture_id": EPILEPSY_DEMO_FIXTURE_ID,
            "non_medical_boundary": "Research screening/support only; no diagnosis, treatment, or clinical decision-making.",
        }
    if module == "reference_csd":
        return {
            "reference_mode": "csd",
            "preview": {"start_sec": 0, "duration_sec": 8, "channels": ["Fz", "Cz", "Pz", "Oz"]},
            "csd": {"sphere": "auto", "lambda2": 0.00001, "stiffness": 4, "n_legendre_terms": 50},
        }
    if module == "pac":
        return {
            "channels": ["Cz", "Pz"],
            "phase_freqs": [4, 6, 8],
            "phase_band_width": 2,
            "amp_freqs": [70, 90, 110],
            "amp_band_width": 20,
            "n_phase_bins": 18,
            "time_window": {"start_sec": 0, "end_sec": 20},
            "dynamic_window_sec": 8,
            "dynamic_step_sec": 4,
        }
    if module == "connectivity":
        return {"method": "correlation", "fmin": 8, "fmax": 12, "segment_length_sec": 4, "edge_top_n": 20}
    if module == "multitaper_psd_tfr":
        return {
            "analysis_family": "tfr",
            "fmin": 1,
            "fmax": 40,
            "bandwidth": 4,
            "adaptive": False,
            "low_bias": True,
            "normalization": "length",
            "freqs": [8, 13, 30],
            "n_cycles": 7,
            "time_bandwidth": 4,
            "use_fft": True,
            "zero_mean": True,
            "decim": 1,
            "average": True,
            "return_itc": True,
            "tmin": -0.2,
            "tmax": 0.8,
            "baseline": [-0.2, 0],
            "baseline_mode": "logratio",
        }
    raise ValueError(f"Unsupported demo module: {module}")


def run_demo_task(module: str, parameters: dict | None = None) -> AnalysisTaskRead:
    module = module.lower()
    if module not in WORKFLOW_BY_MODULE:
        raise ValueError("Demo supports qc, psd, erp, epilepsy, pac, reference_csd, multitaper_psd_tfr, and connectivity")
    if module == "epilepsy_ml":
        ensure_epilepsy_demo_dataset()
        project_id = EPILEPSY_DEMO_PROJECT_ID
        file_id = EPILEPSY_DEMO_FILE_ID
    else:
        ensure_demo_dataset()
        project_id = DEMO_PROJECT_ID
        file_id = DEMO_FILE_ID
    task_parameters = default_parameters(module)
    if parameters:
        task_parameters.update(parameters)
    payload = AnalysisTaskCreate(
        project_id=project_id,
        module_name=module,
        workflow_id=WORKFLOW_BY_MODULE[module],
        input_file_id=file_id,
        parameters_json=task_parameters,
    )
    return task_service.create_task(payload)


def _read_epilepsy_metadata() -> dict:
    if EPILEPSY_DEMO_METADATA_PATH.exists():
        return json.loads(EPILEPSY_DEMO_METADATA_PATH.read_text(encoding="utf-8"))
    return {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ensure_epilepsy_fixture_exists() -> None:
    if EPILEPSY_DEMO_RAW_PATH.exists():
        return
    from scripts.generate_epilepsy_ml_trigger_fixture import main as generate_epilepsy_ml_trigger_fixture

    generate_epilepsy_ml_trigger_fixture()
