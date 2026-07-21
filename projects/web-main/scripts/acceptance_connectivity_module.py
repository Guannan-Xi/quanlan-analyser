from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.models.analysis_task import AnalysisTaskCreate
from backend.services import lab_demo_service, task_service
from eeg_core.analysis.connectivity import run_connectivity, validate_connectivity_parameters
from scripts.generate_teaching_oddball_case import build_raw


WORK = ROOT / "work" / "release_evidence" / "20260622-connectivity-module"
DATA = WORK / "data"
RUNNER_OUTPUT = WORK / "runner_output"
EVIDENCE_PATH = WORK / "acceptance_connectivity_module.json"


def _assert_file(path: Path, failures: list[str], label: str) -> None:
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        failures.append(f"missing_or_empty:{label}:{path}")


def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    DATA.mkdir(parents=True, exist_ok=True)
    raw = build_raw()
    fif_path = DATA / "connectivity_sample_raw.fif"
    raw.save(fif_path, overwrite=True, verbose="ERROR")

    failures: list[str] = []
    runner_paths = run_connectivity(
        fif_path,
        RUNNER_OUTPUT,
        {"method": "correlation", "fmin": 8, "fmax": 12, "segment_length_sec": 4, "edge_top_n": 20},
    )
    required_outputs = [
        "connectivity_matrix",
        "connectivity_edges_long",
        "connectivity_matrix_figure",
        "connectivity_sensor_network",
        "connectivity_summary",
        "parameters",
        "method_description",
        "result",
        "manifest",
        "log",
    ]
    for label in required_outputs:
        _assert_file(Path(runner_paths[label]), failures, label)

    invalid_frequency_rejected = False
    try:
        validate_connectivity_parameters({"fmin": 8, "fmax": 500}, channels=["Fz", "Cz"], sfreq=250, n_times=2500)
    except ValueError:
        invalid_frequency_rejected = True
    if not invalid_frequency_rejected:
        failures.append("invalid_frequency_not_rejected")

    lab_demo_service.ensure_demo_dataset()
    task = task_service.create_task(
        AnalysisTaskCreate(
            project_id=lab_demo_service.DEMO_PROJECT_ID,
            module_name="connectivity",
            workflow_id="connectivity",
            input_file_id=lab_demo_service.DEMO_FILE_ID,
            parameters_json={"method": "correlation", "fmin": 8, "fmax": 12, "segment_length_sec": 4, "edge_top_n": 20},
        )
    )
    artifacts = task_service.list_task_artifacts(task.id)
    expected_labels = {"connectivity_summary", "connectivity_matrix", "connectivity_edges_long", "manifest", "result"}
    actual_labels = {artifact.label for artifact in artifacts}
    if task.status != "completed":
        failures.append(f"task_not_completed:{task.status}")
    missing = sorted(expected_labels - actual_labels)
    if missing:
        failures.append(f"missing_task_artifacts:{','.join(missing)}")

    payload = {
        "status": "passed" if not failures else "failed",
        "module": "connectivity",
        "workflow": "connectivity",
        "runner_output": str(RUNNER_OUTPUT),
        "task_id": task.id,
        "task_status": task.status,
        "artifact_count": len(artifacts),
        "failures": failures,
        "checked_outputs": required_outputs,
    }
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
