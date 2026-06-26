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
from eeg_core.analysis.multitaper_psd_tfr import run_multitaper_psd_tfr, validate_multitaper_psd_tfr_parameters
from scripts.generate_teaching_oddball_case import build_raw


WORK = ROOT / "work" / "release_evidence" / "20260622-multitaper-psd-tfr-module"
DATA = WORK / "data"
RUNNER_OUTPUT = WORK / "runner_output"
EVIDENCE_PATH = WORK / "acceptance_multitaper_psd_tfr_module.json"


def _assert_file(path: Path, failures: list[str], label: str) -> None:
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        failures.append(f"missing_or_empty:{label}:{path}")


def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    DATA.mkdir(parents=True, exist_ok=True)

    raw = build_raw()
    fif_path = DATA / "multitaper_sample_raw.fif"
    raw.save(fif_path, overwrite=True, verbose="ERROR")

    failures: list[str] = []
    parameters = {
        "analysis_family": "tfr",
        "fmin": 1,
        "fmax": 40,
        "bandwidth": 4,
        "adaptive": False,
        "low_bias": True,
        "normalization": "length",
        "event_id": "",
        "tmin": -0.2,
        "tmax": 0.8,
        "baseline": [-0.2, 0.0],
        "baseline_mode": "logratio",
        "freqs": [8, 13, 30],
        "n_cycles": 7,
        "time_bandwidth": 4,
        "decim": 1,
        "return_itc": True,
    }
    runner_paths = run_multitaper_psd_tfr(fif_path, RUNNER_OUTPUT, parameters)
    required_outputs = [
        "multitaper_psd_by_channel_frequency",
        "multitaper_band_power",
        "multitaper_psd_curve",
        "multitaper_tfr_power_long",
        "multitaper_tfr_itc_long",
        "multitaper_tfr_heatmap",
        "method_comparison_preview",
        "multitaper_summary",
        "parameters",
        "frequency_grid",
        "method_description",
        "result",
        "manifest",
        "log",
    ]
    for label in required_outputs:
        _assert_file(Path(runner_paths[label]), failures, label)

    invalid_freq_rejected = False
    try:
        validate_multitaper_psd_tfr_parameters({"fmax": 500}, channels=["Cz"], sfreq=250, n_times=2500)
    except ValueError:
        invalid_freq_rejected = True
    if not invalid_freq_rejected:
        failures.append("invalid_frequency_not_rejected")

    lab_demo_service.ensure_demo_dataset()
    task = task_service.create_task(
        AnalysisTaskCreate(
            project_id=lab_demo_service.DEMO_PROJECT_ID,
            module_name="multitaper_psd_tfr",
            workflow_id="multitaper_psd_tfr",
            input_file_id=lab_demo_service.DEMO_FILE_ID,
            parameters_json=parameters,
        )
    )
    artifacts = task_service.list_task_artifacts(task.id)
    expected_labels = {
        "multitaper_summary",
        "multitaper_psd_by_channel_frequency",
        "multitaper_band_power",
        "multitaper_tfr_power_long",
        "multitaper_tfr_itc_long",
        "method_comparison_preview",
        "manifest",
        "result",
    }
    actual_labels = {artifact.label for artifact in artifacts}
    if task.status != "completed":
        failures.append(f"task_not_completed:{task.status}")
    missing = sorted(expected_labels - actual_labels)
    if missing:
        failures.append(f"missing_task_artifacts:{','.join(missing)}")

    payload = {
        "status": "passed" if not failures else "failed",
        "module": "multitaper_psd_tfr",
        "workflow": "multitaper_psd_tfr",
        "runner_output": str(RUNNER_OUTPUT),
        "task_id": task.id,
        "task_status": task.status,
        "artifact_count": len(artifacts),
        "failures": failures,
        "checked_outputs": required_outputs,
        "boundary": "Multitaper PSD / TFR beta validates descriptive sensor-space multitaper outputs only; no diagnosis, group comparison, causality, source localization, or treatment claim.",
    }
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
