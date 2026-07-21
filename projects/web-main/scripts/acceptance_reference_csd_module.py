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
from eeg_core.analysis.reference_csd import run_reference_csd, validate_reference_csd_parameters
from scripts.generate_teaching_oddball_case import build_raw


WORK = ROOT / "work" / "release_evidence" / "20260622-reference-csd-module"
DATA = WORK / "data"
RUNNER_OUTPUT = WORK / "runner_output"
EVIDENCE_PATH = WORK / "acceptance_reference_csd_module.json"


def _assert_file(path: Path, failures: list[str], label: str) -> None:
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        failures.append(f"missing_or_empty:{label}:{path}")


def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    DATA.mkdir(parents=True, exist_ok=True)

    raw = build_raw()
    fif_path = DATA / "reference_csd_sample_raw.fif"
    raw.save(fif_path, overwrite=True, verbose="ERROR")

    failures: list[str] = []
    runner_paths = run_reference_csd(
        fif_path,
        RUNNER_OUTPUT,
        {
            "reference_mode": "average",
            "preview": {"start_sec": 0, "duration_sec": 8, "channels": ["Fz", "Cz", "Pz", "Oz"]},
        },
    )
    required_runner_outputs = [
        "reference_channels",
        "bipolar_pairs",
        "reference_before_after_preview",
        "csd_before_after_preview",
        "reference_summary",
        "csd_summary",
        "reference_lineage",
        "parameters",
        "method_description",
        "result",
        "manifest",
        "log",
    ]
    for label in required_runner_outputs:
        _assert_file(Path(runner_paths[label]), failures, label)

    missing_channel_rejected = False
    try:
        validate_reference_csd_parameters(
            {"reference_mode": "specific_channels", "ref_channels": ["NO_SUCH_CHANNEL"]},
            channels=["Fz", "Cz", "Pz"],
            sfreq=250,
            n_times=2500,
            has_montage=True,
        )
    except ValueError:
        missing_channel_rejected = True
    if not missing_channel_rejected:
        failures.append("missing_channel_not_rejected")

    lab_demo_service.ensure_demo_dataset()
    task = task_service.create_task(
        AnalysisTaskCreate(
            project_id=lab_demo_service.DEMO_PROJECT_ID,
            module_name="reference_csd",
            workflow_id="reference_csd",
            input_file_id=lab_demo_service.DEMO_FILE_ID,
            parameters_json={
                "reference_mode": "average",
                "preview": {"start_sec": 0, "duration_sec": 8, "channels": ["Fz", "Cz", "Pz", "Oz"]},
            },
        )
    )
    task_artifacts = task_service.list_task_artifacts(task.id)
    expected_artifact_labels = {"reference_summary", "parameters", "manifest", "result", "reference_before_after_preview"}
    actual_labels = {artifact.label for artifact in task_artifacts}
    if task.status != "completed":
        failures.append(f"task_not_completed:{task.status}")
    missing_labels = sorted(expected_artifact_labels - actual_labels)
    if missing_labels:
        failures.append(f"missing_task_artifacts:{','.join(missing_labels)}")

    payload = {
        "status": "passed" if not failures else "failed",
        "module": "reference_csd",
        "workflow": "reference_csd",
        "runner_output": str(RUNNER_OUTPUT),
        "task_id": task.id,
        "task_status": task.status,
        "artifact_count": len(task_artifacts),
        "failures": failures,
        "checked_outputs": required_runner_outputs,
    }
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
