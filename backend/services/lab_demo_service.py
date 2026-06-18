from __future__ import annotations

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

WORKFLOW_BY_MODULE = {
    "qc": "metadata_qc",
    "psd": "resting_psd",
    "erp": "erp_p300",
}


def ensure_demo_dataset() -> dict:
    DEMO_ROOT.mkdir(parents=True, exist_ok=True)
    edf_path = DEMO_ROOT / "teaching_oddball.edf"
    if not edf_path.exists():
        raw = build_raw()
        raw.export(edf_path, fmt="edf", overwrite=True, verbose="ERROR")

    project = ProjectRead(
        id=DEMO_PROJECT_ID,
        name="体验中心示例项目",
        description="内置合成 oddball EEG，用于学习 QC、PSD、ERP 的完整流程。",
        research_type="event_related_learning_demo",
        owner_id="public-demo",
    )
    storage_service.upsert_project(project)

    eeg_file = EEGFileRead(
        id=DEMO_FILE_ID,
        project_id=DEMO_PROJECT_ID,
        subject_id="demo_subject_01",
        original_filename="teaching_oddball.edf",
        stored_path=edf_path,
        detected_format="edf",
        sampling_rate=250.0,
        channel_count=8,
        duration_sec=60.0,
        metadata_json={
            "demo": True,
            "description": "Synthetic posterior 10 Hz alpha plus target-enhanced P300-like response.",
            "events": {"standard": 24, "target": 12},
            "channels": ["Fz", "Cz", "Pz", "Oz", "P3", "P4", "O1", "O2"],
        },
    )
    storage_service.register_eeg_file(eeg_file)
    return {"project": project.model_dump(mode="json"), "file": eeg_file.model_dump(mode="json")}


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
    raise ValueError(f"Unsupported demo module: {module}")


def run_demo_task(module: str) -> AnalysisTaskRead:
    module = module.lower()
    if module not in WORKFLOW_BY_MODULE:
        raise ValueError("Demo supports qc, psd, and erp")
    ensure_demo_dataset()
    payload = AnalysisTaskCreate(
        project_id=DEMO_PROJECT_ID,
        module_name=module,
        workflow_id=WORKFLOW_BY_MODULE[module],
        input_file_id=DEMO_FILE_ID,
        parameters_json=default_parameters(module),
    )
    return task_service.create_task(payload)

