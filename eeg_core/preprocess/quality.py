import json
from pathlib import Path

from eeg_core.io.metadata import read_metadata
from eeg_core.io.readers import read_raw
from eeg_core.report.reproducibility import write_output_contract, write_reproducibility_files


DEFAULT_THRESHOLDS = {
    "min_sfreq": 100.0,
    "min_duration_sec": 5.0,
    "flat_threshold_uv": 1.0,
    "extreme_threshold_uv": 1000.0,
}


def summarize_quality(path: str | Path, parameters: dict | None = None) -> dict:
    parameters = parameters or {}
    file_path = Path(path)
    metadata = read_metadata(file_path)
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add("file_present", file_path.exists() and file_path.stat().st_size > 0 if file_path.exists() else False, "file existence/size check")
    add("format_supported", bool(metadata.get("supported")), f"format={metadata.get('format')} / reader={metadata.get('reader')}")
    add("metadata_readable", metadata.get("status") == "readable", metadata.get("error") or "MNE read OK")

    if metadata.get("status") != "readable":
        return {"status": "failed", "checks": checks, "metadata": metadata, "parameters": parameters}

    sfreq = float(metadata.get("sampling_rate") or 0)
    duration = float(metadata.get("duration_sec") or 0)
    eeg_channels = int(metadata.get("eeg_channel_count") or 0)
    add("sampling_rate_reasonable", sfreq >= float(parameters.get("min_sfreq", DEFAULT_THRESHOLDS["min_sfreq"])), f"sfreq={sfreq:g} Hz")
    add("duration_reasonable", duration >= float(parameters.get("min_duration_sec", DEFAULT_THRESHOLDS["min_duration_sec"])), f"duration={duration:.2f} s")
    add("eeg_channels_present", eeg_channels > 0, f"eeg_channels={eeg_channels}")

    try:
        raw = read_raw(file_path, preload=True)
        picks = raw.pick_types(eeg=True, meg=False, eog=False, ecg=False, stim=False, exclude=[])
        data = picks.get_data(reject_by_annotation="omit")
        import numpy as np
        ptp_uv = np.ptp(data, axis=1) * 1e6 if data.size else np.array([])
        flat_thr = float(parameters.get("flat_threshold_uv", DEFAULT_THRESHOLDS["flat_threshold_uv"]))
        extreme_thr = float(parameters.get("extreme_threshold_uv", DEFAULT_THRESHOLDS["extreme_threshold_uv"]))
        flat = int(np.sum(ptp_uv < flat_thr)) if ptp_uv.size else 0
        extreme = int(np.sum(ptp_uv > extreme_thr)) if ptp_uv.size else 0
        add("flat_channels", flat == 0, f"flat_channels={flat}")
        add("extreme_amplitude_channels", extreme == 0, f"extreme_channels={extreme}")
        status = "passed" if all(item["ok"] for item in checks) else "warning"
        return {
            "status": status,
            "checks": checks,
            "metadata": metadata,
            "parameters": parameters,
            "channel_ptp_uv": {name: float(value) for name, value in zip(picks.ch_names, ptp_uv)},
        }
    except Exception as exc:
        add("signal_qc", False, str(exc))
        return {"status": "warning", "checks": checks, "metadata": metadata, "parameters": parameters}


def run_quality_check(
    input_path: str | Path,
    output_dir: str | Path,
    parameters: dict | None = None,
) -> dict[str, Path]:
    parameters = parameters or {}
    output_path = Path(output_dir)
    reproducibility = output_path / "reproducibility"
    reproducibility.mkdir(parents=True, exist_ok=True)

    summary = summarize_quality(input_path, parameters)

    summary_path = reproducibility / "qc_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    parameters_path = reproducibility / "parameters.json"
    parameters_path.write_text(
        json.dumps(
            {
                "input": str(input_path),
                "module": "qc",
                "parameters": parameters,
                "defaults": DEFAULT_THRESHOLDS,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    method_path = reproducibility / "method_description.txt"
    method_path.write_text(
        "Quality control (QC) reads file metadata via MNE-Python and checks file presence, supported format, "
        "metadata readability, sampling rate, recording duration, EEG channel presence, and per-channel "
        "peak-to-peak amplitudes (flat/extreme channels). QC is descriptive; flagged items should be reviewed "
        "before downstream analyses.\n",
        encoding="utf-8",
    )

    reproducibility_paths = write_reproducibility_files(
        output_path,
        module_name="qc",
        input_path=input_path,
        parameters=parameters,
        workflow_steps=[
            {"name": "read_metadata", "description": "Inspect file size, format, reader, sampling rate, channels."},
            {"name": "read_raw", "description": "Open the recording with the MNE format-specific reader."},
            {"name": "amplitude_checks", "description": "Compute per-channel peak-to-peak amplitudes in microvolts."},
            {"name": "compile_checks", "description": "Aggregate QC checks and derive overall QC status."},
            {"name": "write_outputs", "description": "Write qc_summary.json, parameters.json, method text, and reproducibility files."},
        ],
    )

    core_outputs = {
        "qc_summary": summary_path,
        "parameters": parameters_path,
        "method_description": method_path,
        "software_versions": reproducibility_paths["software_versions"],
        "workflow": reproducibility_paths["workflow"],
    }
    contract_paths = write_output_contract(
        output_path,
        job_type="metadata_qc",
        module_name="qc",
        input_path=input_path,
        parameters=parameters,
        summary=summary,
        outputs=core_outputs,
        log_lines=[
            f"qc_status={summary.get('status')}",
            f"checks={len(summary.get('checks', []))}",
        ],
    )
    return {**core_outputs, **contract_paths}
