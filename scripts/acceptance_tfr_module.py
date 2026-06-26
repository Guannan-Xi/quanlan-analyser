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
from eeg_core.analysis.tfr import run_tfr, validate_tfr_parameters
from scripts.generate_teaching_oddball_case import build_raw


WORK = ROOT / "work" / "release_evidence" / "20260622-tfr-module"
DATA = WORK / "data"
RUNNER_OUTPUT = WORK / "runner_output"
EVIDENCE_PATH = WORK / "acceptance_tfr_module.json"


def _assert_file(path: Path, failures: list[str], label: str) -> None:
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        failures.append(f"missing_or_empty:{label}:{path}")


def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    DATA.mkdir(parents=True, exist_ok=True)
    raw = build_raw()
    fif_path = DATA / "tfr_sample_raw.fif"
    raw.save(fif_path, overwrite=True, verbose="ERROR")

    failures: list[str] = []
    parameters = {
        "event_id": "",
        "tmin": -0.2,
        "tmax": 0.8,
        "baseline": [-0.2, 0.0],
        "freqs": [8, 13, 30],
        "n_cycles": 3,
        "decim": 2,
        "return_itc": True,
    }
    runner_paths = run_tfr(fif_path, RUNNER_OUTPUT, parameters)
    required_outputs = [
        "tfr_power_long",
        "tfr_summary_table",
        "tfr_power",
        "parameters",
        "frequency_grid",
        "method_description",
        "tfr_summary",
        "result",
        "manifest",
        "log",
    ]
    for label in required_outputs:
        _assert_file(Path(runner_paths[label]), failures, label)

    invalid_freq_rejected = False
    try:
        validate_tfr_parameters({"freqs": [0]}, raw=raw)
    except ValueError:
        invalid_freq_rejected = True
    if not invalid_freq_rejected:
        failures.append("invalid_frequency_not_rejected")

    lab_demo_service.ensure_demo_dataset()
    task = task_service.create_task(
        AnalysisTaskCreate(
            project_id=lab_demo_service.DEMO_PROJECT_ID,
            module_name="tfr",
            workflow_id="tfr_ersp_itc",
            input_file_id=lab_demo_service.DEMO_FILE_ID,
            parameters_json=parameters,
        )
    )
    artifacts = task_service.list_task_artifacts(task.id)
    expected_labels = {"tfr_summary", "tfr_power_long", "tfr_summary_table", "manifest", "result"}
    actual_labels = {artifact.label for artifact in artifacts}
    if task.status != "completed":
        failures.append(f"task_not_completed:{task.status}")
    missing = sorted(expected_labels - actual_labels)
    if missing:
        failures.append(f"missing_task_artifacts:{','.join(missing)}")

    payload = {
        "status": "passed" if not failures else "failed",
        "module": "tfr",
        "workflow": "tfr_ersp_itc",
        "runner_output": str(RUNNER_OUTPUT),
        "task_id": task.id,
        "task_status": task.status,
        "artifact_count": len(artifacts),
        "failures": failures,
        "checked_outputs": required_outputs,
        "boundary": "TFR beta validates single-record event-locked sensor-space descriptive outputs only; no significance, diagnosis, group comparison, causality, or source localization claim.",
    }
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
