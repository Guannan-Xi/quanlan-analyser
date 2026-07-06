from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.models.base import new_id
from backend.models.analysis_task import AnalysisTaskCreate
from backend.models.eeg_file import EEGFileRead
from backend.models.governance import AccountRead
from backend.models.project import ProjectRead
from backend.services import state_store, task_service
from eeg_core.analysis.multitaper_psd_tfr import run_multitaper_psd_tfr, validate_multitaper_psd_tfr_parameters
from scripts.generate_teaching_oddball_case import build_raw


WORK = ROOT / "work" / "release_evidence" / "20260622-multitaper-psd-tfr-module"
DATA = WORK / "data"
RUNNER_OUTPUT = WORK / "runner_output"
EVIDENCE_PATH = WORK / "acceptance_multitaper_psd_tfr_module.json"


def _assert_file(path: Path, failures: list[str], label: str) -> None:
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        failures.append(f"missing_or_empty:{label}:{path}")


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    DATA.mkdir(parents=True, exist_ok=True)

    raw = build_raw()
    raw.crop(tmax=30.0 - (1.0 / float(raw.info["sfreq"])))
    fif_path = DATA / "multitaper_sample_raw.fif"
    raw.save(fif_path, overwrite=True, verbose="ERROR")

    failures: list[str] = []
    parameters = {
        "analysis_family": "tfr",
        "fmin": 1,
        "fmax": 30,
        "bandwidth": 1,
        "adaptive": False,
        "low_bias": True,
        "normalization": "length",
        "event_id": "",
        "tmin": -0.2,
        "tmax": 0.8,
        "baseline": [-0.2, 0.0],
        "baseline_mode": "logratio",
        "freqs": [8, 13],
        "n_cycles": 3,
        "time_bandwidth": 2,
        "decim": 2,
        "return_itc": True,
        "picks": ["Cz", "Pz"],
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
        "effective_call",
        "result",
        "manifest",
        "log",
    ]
    for label in required_outputs:
        _assert_file(Path(runner_paths[label]), failures, label)

    psd_channels = sorted({row["channel"] for row in _read_csv_rows(Path(runner_paths["multitaper_psd_by_channel_frequency"]))})
    if psd_channels != ["Cz", "Pz"]:
        failures.append(f"psd_picks_not_applied:{psd_channels}")
    effective_call = json.loads(Path(runner_paths["effective_call"]).read_text(encoding="utf-8"))
    effective_psd_channels = effective_call.get("calls", {}).get("psd", {}).get("input_shape", {}).get("channels", [])
    if effective_psd_channels != ["Cz", "Pz"]:
        failures.append(f"effective_call_psd_channels_not_picked:{effective_psd_channels}")

    invalid_freq_rejected = False
    try:
        validate_multitaper_psd_tfr_parameters({"fmax": 500}, channels=["Cz"], sfreq=250, n_times=2500)
    except ValueError:
        invalid_freq_rejected = True
    if not invalid_freq_rejected:
        failures.append("invalid_frequency_not_rejected")

    owner_id = new_id("acct")
    project_id = new_id("proj")
    file_id = new_id("eeg")
    state_store.upsert_item(
        "accounts",
        AccountRead(
            id=owner_id,
            email=f"{owner_id}@acceptance.qlanalyser.local",
            name="Multitaper acceptance account",
            organization_name="QLanalyser acceptance",
            balance_credits=500.0,
            trial_credits=500.0,
        ),
    )
    state_store.upsert_item(
        "projects",
        ProjectRead(
            id=project_id,
            name="Multitaper PSD/TFR acceptance",
            owner_user_id=owner_id,
            created_by=owner_id,
        ),
    )
    state_store.upsert_item(
        "eeg_files",
        EEGFileRead(
            id=file_id,
            project_id=project_id,
            original_filename=fif_path.name,
            stored_path=fif_path,
            detected_format="fif",
            size_bytes=fif_path.stat().st_size,
            sampling_rate=float(raw.info["sfreq"]),
            channel_count=len(raw.ch_names),
            duration_sec=float(raw.n_times / raw.info["sfreq"]),
            owner_user_id=owner_id,
            created_by=owner_id,
        ),
    )
    task = task_service.create_task(
        AnalysisTaskCreate(
            project_id=project_id,
            module_name="multitaper_psd_tfr",
            workflow_id="multitaper_psd_tfr",
            input_file_id=file_id,
            parameters_json=parameters,
            owner_user_id=owner_id,
            created_by=owner_id,
            idempotency_key=new_id("multitaper_acceptance"),
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
        "psd_channels": psd_channels,
        "effective_psd_channels": effective_psd_channels,
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
