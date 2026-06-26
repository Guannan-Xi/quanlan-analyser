import csv
import html
import json
import math
from pathlib import Path
from typing import Any

import mne
import numpy as np

from eeg_core.io.readers import read_raw
from eeg_core.report.reproducibility import stable_json_hash, write_analysis_sidecars, write_output_contract, write_reproducibility_files


BANDS = {
    "delta": (1.0, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma_low": (30.0, 40.0),
}

PSD_PARAMETER_SCHEMA = {
    "workflow_id": {"type": "string", "default": "resting_psd"},
    "data_preparation_plan_id": {"type": ["string", "null"], "default": None},
    "data_preparation_revision": {"type": ["integer", "string", "null"], "default": None},
    "bad_channels": {"type": "array", "items": "string", "default": []},
    "bad_segments": {"type": "array", "items": "object", "default": []},
    "annotation_actions": {"type": "array", "items": "object", "default": []},
    "fmin": {"type": "number", "default": 1.0, "minimum": 0.0},
    "fmax": {"type": "number", "default": "min(40.0, sfreq / 2 - 1.0)"},
    "l_freq": {"type": ["number", "null"], "default": None},
    "h_freq": {"type": ["number", "null"], "default": None},
    "notch_freq": {"type": ["number", "null"], "default": None},
    "n_fft": {"type": ["integer", "null"], "default": None, "minimum": 2},
    "n_overlap": {"type": ["integer", "null"], "default": None, "minimum": 0},
    "window": {"type": "string", "default": "hamming", "source": "MNE Welch default unless overridden upstream"},
    "average": {"type": "string", "default": "mean", "source": "MNE Welch default unless overridden upstream"},
    "reject_by_annotation": {"type": "boolean", "default": True},
}

MNE_REFERENCE_PATHS = [
    "D:/Quanlan/Codes/Python/third_party_eeg_reference_sources/mne-python/mne/io/base.py:2340",
    "D:/Quanlan/Codes/Python/third_party_eeg_reference_sources/mne-python/mne/time_frequency/psd.py:98",
    "D:/Quanlan/Codes/Python/third_party_eeg_reference_sources/mne-python/mne/time_frequency/tests/test_psd.py",
]


def validate_psd_parameters(parameters: dict | None, *, sfreq: float, n_times: int) -> dict[str, Any]:
    """Normalize PSD P0 parameters while preserving the public runner signature."""
    source = parameters or {}
    nyquist = sfreq / 2.0
    normalized = dict(source)
    normalized.setdefault("workflow_id", "resting_psd")
    normalized.setdefault("data_preparation_plan_id", None)
    normalized.setdefault("data_preparation_revision", None)
    normalized["bad_channels"] = _string_list(source.get("bad_channels"), name="bad_channels")
    normalized["bad_segments"] = _object_list(source.get("bad_segments"), name="bad_segments")
    normalized["annotation_actions"] = _object_list(source.get("annotation_actions"), name="annotation_actions")
    normalized["fmin"] = _optional_float(source.get("fmin"), default=1.0, name="fmin")
    normalized["fmax"] = _optional_float(
        source.get("fmax"),
        default=max(normalized["fmin"], min(40.0, nyquist - 1.0)),
        name="fmax",
    )
    normalized["l_freq"] = _optional_float(source.get("l_freq"), default=None, name="l_freq")
    normalized["h_freq"] = _optional_float(source.get("h_freq"), default=None, name="h_freq")
    normalized["notch_freq"] = _optional_float(source.get("notch_freq"), default=None, name="notch_freq")
    normalized["n_fft"] = _optional_int(source.get("n_fft"), default=None, name="n_fft")
    normalized["n_overlap"] = _optional_int(source.get("n_overlap"), default=None, name="n_overlap")
    normalized["reject_by_annotation"] = bool(source.get("reject_by_annotation", True))

    fmin = normalized["fmin"]
    fmax = normalized["fmax"]
    if fmin < 0:
        raise ValueError("PSD fmin must be >= 0")
    if fmax >= nyquist:
        raise ValueError(f"PSD fmax must be below Nyquist ({nyquist:g} Hz)")
    if fmax <= fmin:
        raise ValueError(f"Invalid PSD frequency range: {fmin}-{fmax} Hz")

    l_freq = normalized["l_freq"]
    h_freq = normalized["h_freq"]
    if l_freq is not None and l_freq <= 0:
        raise ValueError("PSD l_freq must be > 0 when provided")
    if h_freq is not None and h_freq >= nyquist:
        raise ValueError(f"PSD h_freq must be below Nyquist ({nyquist:g} Hz)")
    if l_freq is not None and h_freq is not None and l_freq >= h_freq:
        raise ValueError("PSD l_freq must be < h_freq when both are provided")

    notch = normalized["notch_freq"]
    if notch is not None and (notch <= 0 or notch >= nyquist):
        raise ValueError(f"PSD notch_freq must be > 0 and below Nyquist ({nyquist:g} Hz)")

    n_fft = normalized["n_fft"]
    n_overlap = normalized["n_overlap"]
    if n_fft is not None:
        if n_fft < 2:
            raise ValueError("PSD n_fft must be >= 2")
        if n_fft > n_times:
            raise ValueError(f"PSD n_fft must be <= available samples ({n_times})")
    if n_overlap is not None and n_fft is not None and n_overlap >= n_fft:
        raise ValueError("PSD n_overlap must be < n_fft")

    return normalized


def run_psd(input_path: str | Path, output_dir: str | Path, parameters: dict | None = None) -> dict[str, Path]:
    output_path = Path(output_dir)
    figures = output_path / "figures"
    tables = output_path / "tables"
    reproducibility = output_path / "reproducibility"
    for directory in (figures, tables, reproducibility):
        directory.mkdir(parents=True, exist_ok=True)

    raw = read_raw(input_path, preload=True)
    if not raw.get_channel_types().count("eeg"):
        raise ValueError("PSD requires at least one EEG channel")

    parameters = validate_psd_parameters(parameters, sfreq=float(raw.info["sfreq"]), n_times=raw.n_times)
    applied_directives = _apply_data_preparation_directives(raw, parameters)

    picks = raw.copy().pick_types(eeg=True, meg=False, eog=False, ecg=False, stim=False, exclude="bads")
    if not picks.ch_names:
        raise ValueError("No usable EEG channels after excluding bad channels")

    l_freq = parameters.get("l_freq")
    h_freq = parameters.get("h_freq")
    notch = parameters.get("notch_freq")
    if l_freq is not None or h_freq is not None:
        picks.filter(l_freq=l_freq, h_freq=h_freq, verbose="ERROR")
    if notch is not None:
        picks.notch_filter(freqs=np.atleast_1d(float(notch)), verbose="ERROR")

    method_kw = {}
    if parameters.get("n_fft") is not None:
        method_kw["n_fft"] = parameters["n_fft"]
    if parameters.get("n_overlap") is not None:
        method_kw["n_overlap"] = parameters["n_overlap"]
    effective_method_kw = dict(method_kw)

    spectrum = picks.compute_psd(
        method="welch",
        fmin=parameters["fmin"],
        fmax=parameters["fmax"],
        reject_by_annotation=parameters["reject_by_annotation"],
        verbose="ERROR",
        **method_kw,
    )
    power = spectrum.get_data()
    freqs = spectrum.freqs

    band_rows = _compute_band_rows(power, freqs)
    channel_rows = _compute_channel_band_rows(picks.ch_names, power, freqs)

    band_power_path = tables / "band_power.csv"
    _write_csv(band_power_path, ["band", "fmin", "fmax", "mean_psd", "median_psd"], band_rows)

    channel_band_path = tables / "channel_band_power.csv"
    _write_csv(channel_band_path, ["channel", *BANDS.keys()], channel_rows)

    spectrum_long_path = tables / "spectrum_long.csv"
    _write_spectrum_long_csv(spectrum_long_path, picks.ch_names, freqs, power)

    mean_spectrum_path = figures / "psd_mean_spectrum.svg"
    _write_mean_spectrum_svg(mean_spectrum_path, freqs, power)
    band_power_figure_path = figures / "psd_band_power.svg"
    _write_band_power_svg(band_power_figure_path, band_rows)

    summary = {
        "status": "computed",
        "engine": "mne",
        "mne_reference": {
            "method": "Raw.compute_psd(method='welch')",
            "paths": MNE_REFERENCE_PATHS,
        },
        "channels": len(picks.ch_names),
        "sfreq": float(picks.info["sfreq"]),
        "duration_sec": float(picks.n_times / picks.info["sfreq"]),
        "freq_range_hz": [parameters["fmin"], parameters["fmax"]],
        "freq_bins": len(freqs),
        "parameter_schema": PSD_PARAMETER_SCHEMA,
        "data_preparation_plan_id": parameters.get("data_preparation_plan_id"),
        "data_preparation_revision": parameters.get("data_preparation_revision"),
        "applied_data_preparation": applied_directives,
        "band_power": band_rows,
    }
    summary_path = reproducibility / "psd_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    parameters_path = reproducibility / "parameters.json"
    parameters_path.write_text(json.dumps(parameters, ensure_ascii=False, indent=2), encoding="utf-8")
    method_path = reproducibility / "method_description.txt"
    method_path.write_text(
        "Resting-state PSD was computed from EEG channels using MNE-Python Raw.compute_psd "
        "with Welch spectral estimation. Band powers were averaged within delta, theta, "
        "alpha, beta, and low-gamma bands. Interpretation must consider reference, "
        "preprocessing, artifacts, and individual alpha peak variability.\n",
        encoding="utf-8",
    )
    reproducibility_paths = write_reproducibility_files(
        output_path,
        module_name="psd",
        input_path=input_path,
        parameters=parameters,
        workflow_steps=[
            {"name": "read_raw", "description": "Read EEG data with MNE using a format-specific reader."},
            {"name": "apply_data_preparation", "description": "Apply direct bad channel and bad segment directives when provided."},
            {"name": "select_eeg", "description": "Pick EEG channels, excluding marked bad channels."},
            {"name": "optional_filter", "description": "Apply optional band-pass and notch filtering when parameters are provided."},
            {"name": "welch_psd", "description": "Compute Welch power spectral density via MNE Raw.compute_psd."},
            {"name": "band_summary", "description": "Average power within canonical delta/theta/alpha/beta/low-gamma bands."},
            {"name": "write_outputs", "description": "Write tables, figures, summaries, method text, and reproducibility files."},
        ],
    )
    sidecar_paths = write_analysis_sidecars(
        output_path,
        module_name="psd",
        parameter_schema=PSD_PARAMETER_SCHEMA,
        effective_call={
            "engine": "mne",
            "call": "Raw.compute_psd",
            "method": "welch",
            "kwargs": {
                "method": "welch",
                "fmin": parameters["fmin"],
                "fmax": parameters["fmax"],
                "reject_by_annotation": parameters["reject_by_annotation"],
                **effective_method_kw,
            },
            "input_shape": {
                "channels": list(picks.ch_names),
                "n_times": int(picks.n_times),
                "sfreq": float(picks.info["sfreq"]),
            },
            "output_shape": {
                "channels": len(picks.ch_names),
                "frequencies": int(len(freqs)),
            },
            "reference_paths": MNE_REFERENCE_PATHS,
        },
        threshold_validation={
            "status": "passed",
            "checks": [
                {"field": "fmin", "rule": ">= 0", "value": parameters["fmin"], "status": "passed"},
                {
                    "field": "fmax",
                    "rule": "< Nyquist",
                    "value": parameters["fmax"],
                    "nyquist_hz": float(raw.info["sfreq"]) / 2.0,
                    "status": "passed",
                },
                {"field": "fmax", "rule": "> fmin", "value": parameters["fmax"], "fmin": parameters["fmin"], "status": "passed"},
                {
                    "field": "n_fft",
                    "rule": "null or <= n_times",
                    "value": parameters.get("n_fft"),
                    "n_times": int(raw.n_times),
                    "status": "passed",
                },
                {
                    "field": "n_overlap",
                    "rule": "null or < n_fft",
                    "value": parameters.get("n_overlap"),
                    "n_fft": parameters.get("n_fft"),
                    "status": "passed",
                },
            ],
        },
        table_dictionary=_psd_table_dictionary(),
        scope_contract={
            "analysis_scope": "single_record_descriptive_sensor_space_psd",
            "stable_status": "stable_v01",
            "allowed_claims": [
                "Describe channel-level EEG power spectral density for one uploaded recording.",
                "Summarize bandpower over predefined frequency bands.",
            ],
            "disallowed_claims": [
                "diagnosis_or_treatment_recommendation",
                "group_or_population_inference",
                "statistical_significance_claim",
                "source_localization_or_brain_region_activation",
                "causal_or_mechanistic_conclusion",
            ],
            "high_frequency_caution": "Low-gamma and higher-frequency power can be affected by EMG/muscle artifacts and must be interpreted with QC context.",
        },
        source_metadata=_build_source_metadata(input_path, raw, parameters, applied_directives),
    )

    core_outputs = {
        "band_power": band_power_path,
        "channel_band_power": channel_band_path,
        "spectrum_long": spectrum_long_path,
        "psd_mean_spectrum": mean_spectrum_path,
        "psd_band_power": band_power_figure_path,
        "parameters": parameters_path,
        "psd_summary": summary_path,
        "method_description": method_path,
        "software_versions": reproducibility_paths["software_versions"],
        "workflow": reproducibility_paths["workflow"],
        "parameter_schema_snapshot": sidecar_paths["parameter_schema_snapshot"],
        "threshold_validation": sidecar_paths["threshold_validation"],
        "effective_call": sidecar_paths["effective_call"],
        "source_metadata": sidecar_paths["source_metadata"],
        "table_dictionary": sidecar_paths["table_dictionary"],
        "scope_contract": sidecar_paths["scope_contract"],
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
            f"data_preparation_plan_id={parameters.get('data_preparation_plan_id')}",
            f"data_preparation_revision={parameters.get('data_preparation_revision')}",
        ],
    )
    return {**core_outputs, **contract_paths}


def _apply_data_preparation_directives(raw, parameters: dict[str, Any]) -> dict[str, Any]:
    bad_channels = [ch for ch in parameters["bad_channels"] if ch in raw.ch_names]
    raw.info["bads"] = sorted(set(raw.info.get("bads", [])) | set(bad_channels))

    bad_segments = []
    for item in parameters["bad_segments"]:
        onset, duration = _normalize_bad_segment_window(item)
        if onset is None or duration is None or onset < 0 or duration <= 0:
            raise ValueError(
                "PSD bad_segments entries require onset >= 0 and duration > 0, "
                "or start_sec >= 0 and end_sec > start_sec"
            )
        bad_segments.append({"onset": onset, "duration": duration, "description": item.get("description", "bad_psd_segment")})
    if bad_segments:
        annotations = mne.Annotations(
            onset=[item["onset"] for item in bad_segments],
            duration=[item["duration"] for item in bad_segments],
            description=[str(item["description"]) for item in bad_segments],
        )
        raw.set_annotations(raw.annotations + annotations)

    return {
        "bad_channels": bad_channels,
        "bad_segments": bad_segments,
        "annotation_actions": parameters["annotation_actions"],
        "annotation_actions_status": "recorded_only_p0",
    }


def _build_source_metadata(input_path: str | Path, raw, parameters: dict[str, Any], applied_directives: dict[str, Any]) -> dict[str, Any]:
    path = Path(input_path)
    return {
        "source_file": {
            "filename": path.name,
            "suffix": path.suffix.lower(),
            "size_bytes": path.stat().st_size if path.exists() else None,
            "sha256": _sha256_file(path) if path.exists() and path.is_file() else None,
        },
        "recording_metadata": {
            "sfreq_hz": float(raw.info["sfreq"]),
            "n_times": int(raw.n_times),
            "duration_sec": float(raw.n_times / raw.info["sfreq"]),
            "channel_names": list(raw.ch_names),
            "eeg_channel_count": int(raw.get_channel_types().count("eeg")),
            "bad_channels_after_directives": list(raw.info.get("bads", [])),
            "annotation_count": len(raw.annotations),
        },
        "data_preparation": applied_directives,
        "parameters_hash": stable_json_hash(parameters),
        "qc_boundary": "PSD source metadata records file identity and directives; it does not certify clinical data quality.",
    }


def _psd_table_dictionary() -> dict[str, Any]:
    return {
        "tables/band_power.csv": {
            "description": "Mean and median PSD summarized by canonical EEG frequency band across selected EEG channels.",
            "primary_key": ["band"],
            "columns": {
                "band": {"unit": None, "description": "Frequency band label."},
                "fmin": {"unit": "Hz", "description": "Inclusive lower frequency bound."},
                "fmax": {"unit": "Hz", "description": "Exclusive upper frequency bound."},
                "mean_psd": {"unit": "power/Hz", "description": "Mean PSD over selected channels and band frequencies."},
                "median_psd": {"unit": "power/Hz", "description": "Median PSD over selected channels and band frequencies."},
            },
        },
        "tables/channel_band_power.csv": {
            "description": "Bandpower by selected EEG channel.",
            "primary_key": ["channel"],
            "columns": {
                "channel": {"unit": None, "description": "EEG channel name."},
                **{band: {"unit": "power/Hz", "description": f"Mean PSD in the {band} band."} for band in BANDS},
            },
        },
        "tables/spectrum_long.csv": {
            "description": "Long-form channel-frequency PSD values.",
            "primary_key": ["channel", "frequency_hz"],
            "columns": {
                "channel": {"unit": None, "description": "EEG channel name."},
                "frequency_hz": {"unit": "Hz", "description": "PSD frequency bin."},
                "psd": {"unit": "power/Hz", "description": "Power spectral density value from MNE Welch estimate."},
            },
        },
    }


def _sha256_file(path: Path) -> str:
    digest = __import__("hashlib").sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_bad_segment_window(item: dict[str, Any]) -> tuple[float | None, float | None]:
    onset = _optional_float(item.get("onset"), default=None, name="bad_segments.onset")
    duration = _optional_float(item.get("duration"), default=None, name="bad_segments.duration")
    if onset is not None or duration is not None:
        return onset, duration

    start_sec = _optional_float(item.get("start_sec"), default=None, name="bad_segments.start_sec")
    end_sec = _optional_float(item.get("end_sec"), default=None, name="bad_segments.end_sec")
    if start_sec is None or end_sec is None:
        return None, None
    return start_sec, end_sec - start_sec


def _compute_band_rows(power: np.ndarray, freqs: np.ndarray) -> list[dict[str, Any]]:
    rows = []
    for band, (band_min, band_max) in BANDS.items():
        mask = (freqs >= band_min) & (freqs < band_max)
        rows.append(
            {
                "band": band,
                "fmin": band_min,
                "fmax": band_max,
                "mean_psd": float(np.nanmean(power[:, mask])) if mask.any() else None,
                "median_psd": float(np.nanmedian(power[:, mask])) if mask.any() else None,
            }
        )
    return rows


def _compute_channel_band_rows(channels: list[str], power: np.ndarray, freqs: np.ndarray) -> list[dict[str, Any]]:
    rows = []
    for channel, values in zip(channels, power):
        row = {"channel": channel}
        for band, (band_min, band_max) in BANDS.items():
            mask = (freqs >= band_min) & (freqs < band_max)
            row[band] = float(np.nanmean(values[mask])) if mask.any() else None
        rows.append(row)
    return rows


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_spectrum_long_csv(path: Path, channels: list[str], freqs: np.ndarray, power: np.ndarray) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["channel", "frequency_hz", "psd"])
        writer.writeheader()
        for channel, values in zip(channels, power):
            for freq, value in zip(freqs, values):
                writer.writerow({"channel": channel, "frequency_hz": float(freq), "psd": float(value)})


def _optional_float(value, *, default: float | None, name: str) -> float | None:
    if value is None or value == "":
        return default
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"PSD {name} must be a number") from exc
    if not math.isfinite(result):
        raise ValueError(f"PSD {name} must be finite")
    return result


def _optional_int(value, *, default: int | None, name: str) -> int | None:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise ValueError(f"PSD {name} must be an integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"PSD {name} must be an integer") from exc
    if result < 0:
        raise ValueError(f"PSD {name} must be >= 0")
    return result


def _string_list(value, *, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"PSD {name} must be a list of strings")
    return value


def _object_list(value, *, name: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"PSD {name} must be a list of objects")
    return value


def _write_mean_spectrum_svg(path: Path, freqs: np.ndarray, power: np.ndarray) -> None:
    mean_power = np.nanmean(power, axis=0)
    points = _svg_polyline_points(freqs, mean_power, width=640, height=260, padding=42)
    path.write_text(
        _svg_frame(
            "PSD mean spectrum",
            "Frequency (Hz)",
            "Power spectral density",
            f'<polyline points="{points}" fill="none" stroke="#147d78" stroke-width="3" stroke-linejoin="round" />',
        ),
        encoding="utf-8",
    )


def _write_band_power_svg(path: Path, band_rows: list[dict[str, Any]]) -> None:
    values = np.array([row["mean_psd"] or 0.0 for row in band_rows], dtype=float)
    max_value = float(np.nanmax(values)) if values.size and np.nanmax(values) > 0 else 1.0
    bars = []
    for index, row in enumerate(band_rows):
        x = 52 + index * 108
        bar_height = 190 * float(row["mean_psd"] or 0.0) / max_value
        y = 252 - bar_height
        label = html.escape(str(row["band"]))
        bars.append(f'<rect x="{x}" y="{y:.2f}" width="64" height="{bar_height:.2f}" fill="#147d78" />')
        bars.append(f'<text x="{x + 32}" y="278" text-anchor="middle" font-size="12">{label}</text>')
    path.write_text(_svg_frame("PSD band power", "Band", "Mean PSD", "\n".join(bars)), encoding="utf-8")


def _svg_polyline_points(x_values: np.ndarray, y_values: np.ndarray, *, width: int, height: int, padding: int) -> str:
    x_values = np.asarray(x_values, dtype=float)
    y_values = np.asarray(y_values, dtype=float)
    x_span = float(np.nanmax(x_values) - np.nanmin(x_values)) or 1.0
    y_span = float(np.nanmax(y_values) - np.nanmin(y_values)) or 1.0
    x_min = float(np.nanmin(x_values))
    y_min = float(np.nanmin(y_values))
    points = []
    for x_value, y_value in zip(x_values, y_values):
        x = padding + ((float(x_value) - x_min) / x_span) * (width - 2 * padding)
        y = height - padding - ((float(y_value) - y_min) / y_span) * (height - 2 * padding)
        points.append(f"{x:.2f},{y:.2f}")
    return " ".join(points)


def _svg_frame(title: str, x_label: str, y_label: str, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="320" viewBox="0 0 640 320" role="img" aria-label="{html.escape(title)}">
  <rect width="640" height="320" fill="#ffffff"/>
  <line x1="42" y1="252" x2="604" y2="252" stroke="#7a8b94" stroke-width="1"/>
  <line x1="42" y1="42" x2="42" y2="252" stroke="#7a8b94" stroke-width="1"/>
  <text x="320" y="25" text-anchor="middle" font-size="18" font-family="Arial, sans-serif" fill="#10242c">{html.escape(title)}</text>
  <text x="320" y="306" text-anchor="middle" font-size="13" font-family="Arial, sans-serif" fill="#10242c">{html.escape(x_label)}</text>
  <text x="18" y="158" text-anchor="middle" transform="rotate(-90 18 158)" font-size="13" font-family="Arial, sans-serif" fill="#10242c">{html.escape(y_label)}</text>
  {body}
</svg>
"""
