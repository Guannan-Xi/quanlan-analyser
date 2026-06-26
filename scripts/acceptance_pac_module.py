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
from eeg_core.analysis.pac import run_pac, validate_pac_parameters
from scripts.generate_teaching_oddball_case import build_raw


WORK = ROOT / "work" / "release_evidence" / "20260622-pac-module"
DATA = WORK / "data"
RUNNER_OUTPUT = WORK / "runner_output"
EVIDENCE_PATH = WORK / "acceptance_pac_module.json"


def _assert_file(path: Path, failures: list[str], label: str) -> None:
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        failures.append(f"missing_or_empty:{label}:{path}")


def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    DATA.mkdir(parents=True, exist_ok=True)
    raw = build_raw()
    fif_path = DATA / "pac_sample_raw.fif"
    raw.save(fif_path, overwrite=True, verbose="ERROR")

    failures: list[str] = []
    parameters = {
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
    runner_paths = run_pac(fif_path, RUNNER_OUTPUT, parameters)
    required_outputs = [
        "pac_comodulogram_long",
        "pac_binned_amplitude",
        "pac_dynamic_curve",
        "pac_channel_summary",
        "pac_comodulogram",
        "pac_phase_bins",
        "pac_dynamic_curve_figure",
        "pac_summary",
        "frequency_grid",
        "filter_edge_policy",
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
        validate_pac_parameters({"phase_freqs": [40], "amp_freqs": [30]}, channels=["Cz"], sfreq=250, duration_sec=20)
    except ValueError:
        invalid_frequency_rejected = True
    if not invalid_frequency_rejected:
        failures.append("invalid_frequency_order_not_rejected")

    nyquist_rejected = False
    try:
        validate_pac_parameters({"amp_freqs": [130], "amp_band_width": 20}, channels=["Cz"], sfreq=250, duration_sec=20)
    except ValueError:
        nyquist_rejected = True
    if not nyquist_rejected:
        failures.append("nyquist_violation_not_rejected")

    lab_demo_service.ensure_demo_dataset()
    task = task_service.create_task(
        AnalysisTaskCreate(
            project_id=lab_demo_service.DEMO_PROJECT_ID,
            module_name="pac",
            workflow_id="pac_cfc",
            input_file_id=lab_demo_service.DEMO_FILE_ID,
            parameters_json=parameters,
        )
    )
    artifacts = task_service.list_task_artifacts(task.id)
    expected_labels = {"pac_summary", "pac_comodulogram_long", "pac_binned_amplitude", "pac_dynamic_curve", "manifest", "result"}
    actual_labels = {artifact.label for artifact in artifacts}
    if task.status != "completed":
        failures.append(f"task_not_completed:{task.status}")
    missing = sorted(expected_labels - actual_labels)
    if missing:
        failures.append(f"missing_task_artifacts:{','.join(missing)}")

    payload = {
        "status": "passed" if not failures else "failed",
        "module": "pac",
        "workflow": "pac_cfc",
        "runner_output": str(RUNNER_OUTPUT),
        "task_id": task.id,
        "task_status": task.status,
        "artifact_count": len(artifacts),
        "failures": failures,
        "checked_outputs": required_outputs,
        "boundary": "PAC beta validates single-record sensor-space descriptive outputs only; no significance, diagnosis, group comparison, causality, source localization, or brain-region communication claim.",
    }
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
