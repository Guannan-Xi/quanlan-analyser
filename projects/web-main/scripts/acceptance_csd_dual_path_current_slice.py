from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mne

from eeg_core.analysis.reference_csd import run_reference_csd
from scripts.generate_teaching_oddball_case import build_raw


EVIDENCE_ROOT = ROOT / "work" / "release_evidence" / "07-full-product-e2e-pdca" / "12_current_modules_teaching_mode"
WORK = EVIDENCE_ROOT / "06_methods" / "csd_dual_path"
DATA = WORK / "data"
POSITIVE_OUT = WORK / "positive_csd_with_montage"
NEGATIVE_OUT = WORK / "negative_csd_without_montage"
REFERENCE_OUT = WORK / "reference_average_dimension_check"
EVIDENCE_PATH = WORK / "csd_dual_path_acceptance.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_file(path: Path, failures: list[str], label: str) -> None:
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        failures.append(f"missing_or_empty:{label}:{path}")


def raw_without_montage() -> mne.io.Raw:
    source = build_raw()
    raw = mne.io.RawArray(
        source.get_data(),
        mne.create_info(source.ch_names, sfreq=float(source.info["sfreq"]), ch_types="eeg"),
        verbose="ERROR",
    )
    raw.set_annotations(source.annotations, verbose="ERROR")
    return raw


def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    DATA.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    positive_fif = DATA / "teaching_oddball_with_montage_raw.fif"
    negative_fif = DATA / "teaching_oddball_without_montage_raw.fif"
    build_raw().save(positive_fif, overwrite=True, verbose="ERROR")
    raw_without_montage().save(negative_fif, overwrite=True, verbose="ERROR")

    positive_paths = run_reference_csd(
        positive_fif,
        POSITIVE_OUT,
        {
            "reference_mode": "csd",
            "preview": {"start_sec": 0, "duration_sec": 8, "channels": ["Fz", "Cz", "Pz", "Oz"]},
            "csd": {"sphere": "auto", "lambda2": 0.00001, "stiffness": 4, "n_legendre_terms": 50},
        },
    )
    positive_required = [
        "reference_channels",
        "reference_before_after_preview",
        "csd_before_after_preview",
        "reference_summary",
        "csd_summary",
        "parameters",
        "method_description",
        "result",
        "manifest",
    ]
    for label in positive_required:
        assert_file(Path(positive_paths[label]), failures, f"positive:{label}")
    positive_summary = read_json(Path(positive_paths["reference_summary"]))
    positive_csd_summary = read_json(Path(positive_paths["csd_summary"]))
    if positive_summary.get("reference_mode") != "csd":
        failures.append(f"positive_reference_mode_not_csd:{positive_summary.get('reference_mode')}")
    if positive_summary.get("montage_status") != "present":
        failures.append(f"positive_montage_not_present:{positive_summary.get('montage_status')}")
    if positive_csd_summary.get("status") != "computed":
        failures.append(f"positive_csd_not_computed:{positive_csd_summary.get('status')}")
    if positive_summary.get("channels_before") != positive_summary.get("channels_after"):
        failures.append("positive_csd_channel_count_changed")

    reference_paths = run_reference_csd(
        positive_fif,
        REFERENCE_OUT,
        {
            "reference_mode": "average",
            "preview": {"start_sec": 0, "duration_sec": 8, "channels": ["Fz", "Cz", "Pz", "Oz"]},
        },
    )
    reference_summary = read_json(Path(reference_paths["reference_summary"]))
    if reference_summary.get("channels_before") != reference_summary.get("channels_after"):
        failures.append("average_reference_channel_count_changed")

    negative_error = ""
    try:
        run_reference_csd(
            negative_fif,
            NEGATIVE_OUT,
            {
                "reference_mode": "csd",
                "preview": {"start_sec": 0, "duration_sec": 8, "channels": ["Fz", "Cz", "Pz", "Oz"]},
            },
        )
        failures.append("negative_no_montage_csd_was_not_rejected")
    except ValueError as exc:
        negative_error = str(exc)
        if "MONTAGE_REQUIRED_FOR_CSD" not in negative_error:
            failures.append(f"negative_error_not_actionable:{negative_error}")

    method_text = Path(positive_paths["method_description"]).read_text(encoding="utf-8")
    forbidden_claims = ["brain-region activation", "diagnosis, or treatment guidance."]
    boundary_ok = "source localization" in method_text and "sensor-space" in method_text
    if not boundary_ok:
        failures.append("method_description_missing_sensor_space_boundary")

    payload = {
        "script": Path(__file__).name,
        "requirements": ["R-CSD-01", "R-CSD-02", "R-REF-01", "R-TEACH-01"],
        "status": "passed" if not failures else "failed",
        "positive": {
            "input": str(positive_fif),
            "reference_mode": positive_summary.get("reference_mode"),
            "montage_status": positive_summary.get("montage_status"),
            "channels_before": positive_summary.get("channels_before"),
            "channels_after": positive_summary.get("channels_after"),
            "csd_status": positive_csd_summary.get("status"),
            "outputs": {key: str(value) for key, value in positive_paths.items()},
        },
        "average_reference_dimension_check": {
            "channels_before": reference_summary.get("channels_before"),
            "channels_after": reference_summary.get("channels_after"),
            "status": "passed" if reference_summary.get("channels_before") == reference_summary.get("channels_after") else "failed",
        },
        "negative": {
            "input": str(negative_fif),
            "expected_error": "MONTAGE_REQUIRED_FOR_CSD",
            "actual_error": negative_error,
            "status": "passed" if negative_error.startswith("MONTAGE_REQUIRED_FOR_CSD") else "failed",
        },
        "boundary": {
            "method_text_sensor_space_boundary": boundary_ok,
            "forbidden_claims_not_used_as_allowed_claims": forbidden_claims,
            "replacement_for_rejected_fieldtrip_benchmark": "MNE compute_current_source_density invocation + positive/negative montage path + output and boundary evidence.",
        },
        "failures": failures,
    }
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
