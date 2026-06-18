import csv
import json
from pathlib import Path

import numpy as np

from eeg_core.io.readers import read_raw
from eeg_core.report.reproducibility import write_output_contract, write_reproducibility_files


BANDS = {
    "delta": (1.0, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma_low": (30.0, 40.0),
}


def run_psd(input_path: str | Path, output_dir: str | Path, parameters: dict | None = None) -> dict[str, Path]:
    parameters = parameters or {}
    output_path = Path(output_dir)
    figures = output_path / "figures"
    tables = output_path / "tables"
    reproducibility = output_path / "reproducibility"
    for directory in (figures, tables, reproducibility):
        directory.mkdir(parents=True, exist_ok=True)

    raw = read_raw(input_path, preload=True)
    if not raw.get_channel_types().count("eeg"):
        raise ValueError("PSD requires at least one EEG channel")

    picks = raw.copy().pick_types(eeg=True, meg=False, eog=False, ecg=False, stim=False, exclude="bads")
    if not picks.ch_names:
        raise ValueError("No usable EEG channels after excluding bad channels")

    l_freq = parameters.get("l_freq")
    h_freq = parameters.get("h_freq")
    notch = parameters.get("notch_freq")
    if l_freq or h_freq:
        picks.filter(l_freq=l_freq, h_freq=h_freq, verbose="ERROR")
    if notch:
        picks.notch_filter(freqs=np.atleast_1d(float(notch)), verbose="ERROR")

    fmin = float(parameters.get("fmin", 1.0))
    fmax = float(parameters.get("fmax", min(40.0, picks.info["sfreq"] / 2.0 - 1.0)))
    if fmax <= fmin:
        raise ValueError(f"Invalid PSD frequency range: {fmin}-{fmax} Hz")

    spectrum = picks.compute_psd(method="welch", fmin=fmin, fmax=fmax, n_fft=parameters.get("n_fft"), verbose="ERROR")
    power = spectrum.get_data()
    freqs = spectrum.freqs

    band_rows = []
    for band, (band_min, band_max) in BANDS.items():
        mask = (freqs >= band_min) & (freqs < band_max)
        band_rows.append({
            "band": band,
            "fmin": band_min,
            "fmax": band_max,
            "mean_psd": float(np.nanmean(power[:, mask])) if mask.any() else None,
            "median_psd": float(np.nanmedian(power[:, mask])) if mask.any() else None,
        })

    channel_rows = []
    for channel, values in zip(picks.ch_names, power):
        row = {"channel": channel}
        for band, (band_min, band_max) in BANDS.items():
            mask = (freqs >= band_min) & (freqs < band_max)
            row[band] = float(np.nanmean(values[mask])) if mask.any() else None
        channel_rows.append(row)

    band_power_path = tables / "band_power.csv"
    with band_power_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["band", "fmin", "fmax", "mean_psd", "median_psd"])
        writer.writeheader()
        writer.writerows(band_rows)

    channel_band_path = tables / "channel_band_power.csv"
    with channel_band_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["channel", *BANDS.keys()])
        writer.writeheader()
        writer.writerows(channel_rows)

    summary = {
        "status": "computed",
        "engine": "mne",
        "channels": len(picks.ch_names),
        "sfreq": float(picks.info["sfreq"]),
        "duration_sec": float(picks.n_times / picks.info["sfreq"]),
        "freq_range_hz": [fmin, fmax],
        "freq_bins": len(freqs),
        "band_power": band_rows,
        "parameters": parameters,
    }
    values = {row["band"]: row["mean_psd"] for row in band_rows}
    summary["alpha_theta_ratio"] = float(values["alpha"] / values["theta"]) if values.get("alpha") and values.get("theta") else None
    summary["alpha_beta_ratio"] = float(values["alpha"] / values["beta"]) if values.get("alpha") and values.get("beta") else None

    parameters_path = reproducibility / "parameters.json"
    parameters_path.write_text(json.dumps({"input": str(input_path), "module": "psd", "parameters": parameters, "engine": "mne"}, indent=2), encoding="utf-8")
    summary_path = reproducibility / "psd_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    method_path = reproducibility / "method_description.txt"
    method_path.write_text(
        "Resting-state PSD was computed from EEG channels using MNE-Python Welch spectra. "
        "Band powers were averaged within delta/theta/alpha/beta/low-gamma bands. "
        "Interpretation must consider reference, preprocessing, artifacts, and individual alpha peak variability.\n",
        encoding="utf-8",
    )
    reproducibility_paths = write_reproducibility_files(
        output_path,
        module_name="psd",
        input_path=input_path,
        parameters=parameters,
        workflow_steps=[
            {"name": "read_raw", "description": "Read EEG data with MNE using a format-specific reader."},
            {"name": "select_eeg", "description": "Pick EEG channels, excluding marked bad channels."},
            {"name": "optional_filter", "description": "Apply optional band-pass and notch filtering when parameters are provided."},
            {"name": "welch_psd", "description": "Compute Welch power spectral density via MNE."},
            {"name": "band_summary", "description": "Average power within canonical delta/theta/alpha/beta/low-gamma bands."},
            {"name": "write_outputs", "description": "Write tables, summaries, method text, and reproducibility files."},
        ],
    )

    core_outputs = {
        "band_power": band_power_path,
        "channel_band_power": channel_band_path,
        "parameters": parameters_path,
        "psd_summary": summary_path,
        "method_description": method_path,
        "software_versions": reproducibility_paths["software_versions"],
        "workflow": reproducibility_paths["workflow"],
    }
    contract_paths = write_output_contract(
        output_path,
        job_type="resting_psd",
        module_name="psd",
        input_path=input_path,
        parameters=parameters,
        summary=summary,
        outputs=core_outputs,
        log_lines=[
            f"channels={summary.get('channels')}",
            f"freq_range_hz={summary.get('freq_range_hz')}",
            f"freq_bins={summary.get('freq_bins')}",
        ],
    )
    return {**core_outputs, **contract_paths}
