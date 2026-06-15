import csv
import json
from pathlib import Path


BANDS = {
    "delta": (1, 4),
    "theta": (4, 8),
    "alpha": (8, 13),
    "beta": (13, 30),
    "gamma_low": (30, 40),
}


def run_psd(input_path: str | Path, output_dir: str | Path, parameters: dict) -> dict[str, Path]:
    output_path = Path(output_dir)
    figures = output_path / "figures"
    tables = output_path / "tables"
    reproducibility = output_path / "reproducibility"
    for directory in (figures, tables, reproducibility):
        directory.mkdir(parents=True, exist_ok=True)

    input_file = Path(input_path)
    psd_summary = _try_mne_psd(input_file, parameters)
    band_rows = psd_summary["band_power"] if psd_summary else _placeholder_band_rows()

    band_power_path = tables / "band_power.csv"
    with band_power_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["band", "fmin", "fmax", "mean_psd"])
        writer.writeheader()
        writer.writerows(band_rows)

    parameters_path = reproducibility / "parameters.json"
    parameters_path.write_text(
        json.dumps(
            {"input": str(input_path), "module": "psd", "parameters": parameters, "engine": "mne" if psd_summary else "placeholder"},
            indent=2,
        ),
        encoding="utf-8",
    )

    summary_path = reproducibility / "psd_summary.json"
    summary_path.write_text(
        json.dumps(psd_summary or {"status": "placeholder", "band_power": band_rows}, indent=2),
        encoding="utf-8",
    )

    method_path = reproducibility / "method_description.txt"
    method_path.write_text(
        "Resting-state PSD analysis using MNE Raw.compute_psd with Welch method.\n"
        if psd_summary
        else "Resting-state PSD analysis placeholder pending readable EEG input.\n",
        encoding="utf-8",
    )

    return {
        "band_power": band_power_path,
        "psd_summary": summary_path,
        "parameters": parameters_path,
        "method_description": method_path,
    }


def _try_mne_psd(input_path: Path, parameters: dict) -> dict | None:
    if input_path.suffix.lower() not in {".bdf", ".edf"} or not input_path.exists():
        return None

    try:
        import mne
        import numpy as np

        reader = mne.io.read_raw_bdf if input_path.suffix.lower() == ".bdf" else mne.io.read_raw_edf
        raw = reader(input_path, preload=False, verbose="ERROR")
        duration = float(parameters.get("duration_sec", 30))
        tmax = min(duration, raw.n_times / raw.info["sfreq"])
        raw = raw.copy().crop(tmin=0, tmax=tmax, include_tmax=False).load_data(verbose="ERROR")
        spectrum = raw.compute_psd(
            method="welch",
            fmin=float(parameters.get("fmin", 1)),
            fmax=float(parameters.get("fmax", 40)),
            n_fft=int(parameters.get("n_fft", 2048)),
            n_overlap=int(parameters.get("n_overlap", 1024)),
            verbose="ERROR",
        )
        power = spectrum.get_data()
        freqs = spectrum.freqs
        rows = []
        for band, (fmin, fmax) in BANDS.items():
            mask = (freqs >= fmin) & (freqs < fmax)
            rows.append(
                {
                    "band": band,
                    "fmin": fmin,
                    "fmax": fmax,
                    "mean_psd": float(np.nanmean(power[:, mask])) if mask.any() else None,
                }
            )
        band_values = {row["band"]: row["mean_psd"] for row in rows}
        theta = band_values.get("theta")
        alpha = band_values.get("alpha")
        beta = band_values.get("beta")
        return {
            "status": "computed",
            "engine": "mne",
            "mne_version": mne.__version__,
            "channels": int(len(raw.ch_names)),
            "sfreq": float(raw.info["sfreq"]),
            "duration_sec_used": float(tmax),
            "freq_bins": int(len(freqs)),
            "band_power": rows,
            "alpha_theta_ratio": float(alpha / theta) if alpha and theta else None,
            "alpha_beta_ratio": float(alpha / beta) if alpha and beta else None,
        }
    except Exception as exc:
        return {"status": "failed", "error": str(exc), "band_power": _placeholder_band_rows()}


def _placeholder_band_rows() -> list[dict]:
    return [
        {"band": "theta", "fmin": 4, "fmax": 8, "mean_psd": "placeholder"},
        {"band": "alpha", "fmin": 8, "fmax": 13, "mean_psd": "placeholder"},
        {"band": "beta", "fmin": 13, "fmax": 30, "mean_psd": "placeholder"},
    ]
