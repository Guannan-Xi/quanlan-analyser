import csv
import html
import json
from pathlib import Path
from typing import Any

import numpy as np

from eeg_core.analysis.psd import (
    BANDS as DEFAULT_BANDS,
    MNE_REFERENCE_PATHS,
    _apply_data_preparation_directives,
    _build_source_metadata,
    _optional_float,
    _optional_int,
    _object_list,
    _string_list,
    validate_psd_parameters,
)
from eeg_core.io.readers import read_raw
from eeg_core.report.reproducibility import stable_json_hash, write_analysis_sidecars, write_output_contract, write_reproducibility_files


BAND_POWER_PARAMETER_SCHEMA = {
    "workflow_id": {"type": "string", "default": "band_power_summary"},
    "data_preparation_plan_id": {"type": ["string", "null"], "default": None},
    "data_preparation_revision": {"type": ["integer", "string", "null"], "default": None},
    "bad_channels": {"type": "array", "items": "string", "default": []},
    "bad_segments": {"type": "array", "items": "object", "default": []},
    "annotation_actions": {"type": "array", "items": "object", "default": []},
    "fmin": {"type": "number", "default": 1.0, "minimum": 0.0},
    "fmax": {"type": "number", "default": "min(40.0, sfreq / 2 - 1.0)"},
    "bands": {"type": "object", "default": DEFAULT_BANDS},
    "l_freq": {"type": ["number", "null"], "default": None},
    "h_freq": {"type": ["number", "null"], "default": None},
    "notch_freq": {"type": ["number", "null"], "default": None},
    "n_fft": {"type": ["integer", "null"], "default": None, "minimum": 2},
    "n_overlap": {"type": ["integer", "null"], "default": None, "minimum": 0},
    "window": {"type": "string", "default": "hamming", "source": "MNE Welch default unless overridden upstream"},
    "average": {"type": "string", "default": "mean", "source": "MNE Welch default unless overridden upstream"},
    "reject_by_annotation": {"type": "boolean", "default": True},
}


def validate_band_power_parameters(parameters: dict | None, *, sfreq: float, n_times: int) -> dict[str, Any]:
    source = dict(parameters or {})
    source["workflow_id"] = source.get("workflow_id") or "band_power_summary"
    normalized = validate_psd_parameters(source, sfreq=sfreq, n_times=n_times)
    normalized["workflow_id"] = "band_power_summary"
    normalized["bad_channels"] = _string_list(source.get("bad_channels"), name="bad_channels")
    normalized["bad_segments"] = _object_list(source.get("bad_segments"), name="bad_segments")
    normalized["annotation_actions"] = _object_list(source.get("annotation_actions"), name="annotation_actions")
    normalized["l_freq"] = _optional_float(source.get("l_freq"), default=None, name="l_freq")
    normalized["h_freq"] = _optional_float(source.get("h_freq"), default=None, name="h_freq")
    normalized["notch_freq"] = _optional_float(source.get("notch_freq"), default=None, name="notch_freq")
    normalized["n_fft"] = _optional_int(source.get("n_fft"), default=None, name="n_fft")
    normalized["n_overlap"] = _optional_int(source.get("n_overlap"), default=None, name="n_overlap")
    bands = _normalize_band_definitions(source.get("bands") or DEFAULT_BANDS)
    band_contract = _effective_bands_for_sampling(bands, sfreq=sfreq, fmin=normalized["fmin"], fmax=normalized["fmax"])
    normalized.update(band_contract)
    return normalized


def run_band_power(input_path: str | Path, output_dir: str | Path, parameters: dict | None = None) -> dict[str, Path]:
    output_path = Path(output_dir)
    figures = output_path / "figures"
    tables = output_path / "tables"
    reproducibility = output_path / "reproducibility"
    for directory in (figures, tables, reproducibility):
        directory.mkdir(parents=True, exist_ok=True)

    raw = read_raw(input_path, preload=True)
    if not raw.get_channel_types().count("eeg"):
        raise ValueError("Band Power requires at least one EEG channel")

    parameters = validate_band_power_parameters(parameters, sfreq=float(raw.info["sfreq"]), n_times=raw.n_times)
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
    active_bands = parameters["bands"]

    band_rows = _compute_band_power_rows(power, freqs, active_bands, parameters.get("adjusted_bands") or [])
    channel_rows = _compute_channel_band_power_rows(picks.ch_names, power, freqs, active_bands)

    band_power_path = tables / "band_power.csv"
    _write_csv(
        band_power_path,
        ["band", "fmin", "fmax", "mean_band_power", "median_band_power", "band_status", "parameter_note"],
        band_rows,
    )
    channel_band_path = tables / "channel_band_power.csv"
    _write_csv(channel_band_path, ["channel", *active_bands.keys()], channel_rows)

    band_power_figure_path = figures / "band_power.svg"
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
        "parameter_schema": BAND_POWER_PARAMETER_SCHEMA,
        "data_preparation_plan_id": parameters.get("data_preparation_plan_id"),
        "data_preparation_revision": parameters.get("data_preparation_revision"),
        "applied_data_preparation": applied_directives,
        "band_power": band_rows,
        "adjusted_bands": parameters.get("adjusted_bands", []),
        "excluded_bands": parameters.get("excluded_bands", []),
        "parameter_notes": parameters.get("parameter_notes", {}),
    }
    summary_path = reproducibility / "band_power_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    parameters_path = reproducibility / "parameters.json"
    parameters_path.write_text(json.dumps(parameters, ensure_ascii=False, indent=2), encoding="utf-8")
    method_path = reproducibility / "method_description.txt"
    method_path.write_text(
        "Band Power computes descriptive EEG frequency-band power from selected EEG channels "
        "using MNE-Python Raw.compute_psd with Welch spectral estimation. Frequency bands are "
        "checked against the recording sampling rate before validation; clipped or excluded bands "
        "are recorded in parameters and summary sidecars.\n",
        encoding="utf-8",
    )
    reproducibility_paths = write_reproducibility_files(
        output_path,
        module_name="band_power",
        input_path=input_path,
        parameters=parameters,
        workflow_steps=[
            {"name": "read_raw", "description": "Read EEG data with MNE using a format-specific reader."},
            {"name": "normalize_bands", "description": "Clip or exclude configured frequency bands against Nyquist and effective fmax."},
            {"name": "select_eeg", "description": "Pick EEG channels, excluding marked bad channels."},
            {"name": "welch_psd", "description": "Compute Welch PSD via MNE Raw.compute_psd as the source for band power."},
            {"name": "band_power", "description": "Average power within validated frequency bands."},
            {"name": "write_outputs", "description": "Write tables, figure, summaries, method text, and reproducibility files."},
        ],
    )
    effective_method_kw = dict(method_kw)
    sidecar_paths = write_analysis_sidecars(
        output_path,
        module_name="band_power",
        parameter_schema=BAND_POWER_PARAMETER_SCHEMA,
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
                "bands": len(active_bands),
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
                {
                    "field": "bands",
                    "rule": "each included band has fmin < fmax < Nyquist",
                    "value": parameters["bands"],
                    "adjusted_bands": parameters.get("adjusted_bands", []),
                    "excluded_bands": parameters.get("excluded_bands", []),
                    "status": "passed",
                },
            ],
        },
        table_dictionary=_band_power_table_dictionary(active_bands),
        scope_contract={
            "analysis_scope": "single_record_descriptive_sensor_space_band_power",
            "stable_status": "stable_v01",
            "allowed_claims": [
                "Describe channel-level EEG power summarized by validated frequency bands for one uploaded recording.",
                "Compare relative frequency-band power within the same sensor-space recording when QC and reference are considered.",
            ],
            "disallowed_claims": [
                "diagnosis_or_treatment_recommendation",
                "group_or_population_inference",
                "statistical_significance_claim",
                "source_localization_or_brain_region_activation",
                "causal_or_mechanistic_conclusion",
            ],
            "customer_boundary_note": "Band Power is a descriptive research analysis method; it does not diagnose disease, determine treatment, or certify clinical state.",
        },
        source_metadata=_build_source_metadata(input_path, raw, parameters, applied_directives),
    )

    core_outputs = {
        "band_power": band_power_path,
        "channel_band_power": channel_band_path,
        "band_power_figure": band_power_figure_path,
        "parameters": parameters_path,
        "band_power_summary": summary_path,
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
        job_type="band_power_summary",
        module_name="band_power",
        input_path=input_path,
        parameters=parameters,
        summary=summary,
        outputs=core_outputs,
        log_lines=[
            f"channels={summary.get('channels')}",
            f"freq_range_hz={summary.get('freq_range_hz')}",
            f"bands={list(active_bands)}",
            f"adjusted_bands={parameters.get('adjusted_bands', [])}",
            f"excluded_bands={parameters.get('excluded_bands', [])}",
        ],
    )
    _annotate_manifest(
        contract_paths["manifest"],
        {
            "job_type": "band_power_summary",
            "module_name": "band_power",
            "parameter_notes": parameters.get("parameter_notes", {}),
            "adjusted_bands": parameters.get("adjusted_bands", []),
            "excluded_bands": parameters.get("excluded_bands", []),
        },
    )
    return {**core_outputs, **contract_paths}


def _annotate_manifest(path: Path, fields: dict[str, Any]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(fields)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_band_definitions(raw_bands: Any) -> dict[str, tuple[float, float]]:
    if not isinstance(raw_bands, dict):
        raise ValueError("Band Power bands must be an object mapping band name to [fmin, fmax]")
    bands = {}
    for name, bounds in raw_bands.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Band Power band names must be non-empty strings")
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            raise ValueError(f"Band Power band {name} must have [fmin, fmax]")
        fmin = float(bounds[0])
        fmax = float(bounds[1])
        if not np.isfinite(fmin) or not np.isfinite(fmax) or fmin < 0 or fmax <= fmin:
            raise ValueError(f"Band Power band {name} has invalid range {fmin}-{fmax} Hz")
        bands[name.strip()] = (fmin, fmax)
    return bands


def _effective_bands_for_sampling(
    bands: dict[str, tuple[float, float]],
    *,
    sfreq: float,
    fmin: float,
    fmax: float,
) -> dict[str, Any]:
    nyquist = sfreq / 2.0
    ceiling = min(fmax, np.nextafter(nyquist, 0.0))
    active: dict[str, tuple[float, float]] = {}
    adjusted = []
    excluded = []
    for band, (band_min, band_max) in bands.items():
        effective_min = max(float(band_min), float(fmin))
        effective_max = min(float(band_max), float(ceiling))
        if effective_max <= effective_min:
            excluded.append(
                {
                    "band": band,
                    "original_fmin": band_min,
                    "original_fmax": band_max,
                    "reason": "outside_effective_frequency_range_or_nyquist",
                    "nyquist_hz": nyquist,
                    "effective_fmax_hz": fmax,
                }
            )
            continue
        active[band] = (round(effective_min, 6), round(effective_max, 6))
        if effective_min != band_min or effective_max != band_max:
            adjusted.append(
                {
                    "band": band,
                    "original_fmin": band_min,
                    "original_fmax": band_max,
                    "effective_fmin": active[band][0],
                    "effective_fmax": active[band][1],
                    "reason": "clipped_to_effective_frequency_range_and_nyquist",
                    "nyquist_hz": nyquist,
                    "effective_fmax_hz": fmax,
                }
            )
    if not active:
        raise ValueError("Band Power has no frequency bands after applying sampling-rate limits")
    return {
        "bands": active,
        "adjusted_bands": adjusted,
        "excluded_bands": excluded,
        "parameter_notes": {
            "band_adjustment_policy": "Bands are clipped or excluded before validation when they reach Nyquist or the effective analysis fmax.",
            "nyquist_hz": nyquist,
            "effective_fmax_hz": fmax,
            "adjusted_band_count": len(adjusted),
            "excluded_band_count": len(excluded),
        },
    }


def _compute_band_power_rows(
    power: np.ndarray,
    freqs: np.ndarray,
    bands: dict[str, tuple[float, float]],
    adjusted_bands: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    adjusted_by_band = {item["band"]: item for item in adjusted_bands}
    rows = []
    for band, (band_min, band_max) in bands.items():
        mask = (freqs >= band_min) & (freqs < band_max)
        adjusted = adjusted_by_band.get(band)
        rows.append(
            {
                "band": band,
                "fmin": band_min,
                "fmax": band_max,
                "mean_band_power": float(np.nanmean(power[:, mask])) if mask.any() else None,
                "median_band_power": float(np.nanmedian(power[:, mask])) if mask.any() else None,
                "band_status": "adjusted" if adjusted else "included",
                "parameter_note": adjusted.get("reason", "") if adjusted else "",
            }
        )
    return rows


def _compute_channel_band_power_rows(channels: list[str], power: np.ndarray, freqs: np.ndarray, bands: dict[str, tuple[float, float]]) -> list[dict[str, Any]]:
    rows = []
    for channel, values in zip(channels, power):
        row = {"channel": channel}
        for band, (band_min, band_max) in bands.items():
            mask = (freqs >= band_min) & (freqs < band_max)
            row[band] = float(np.nanmean(values[mask])) if mask.any() else None
        rows.append(row)
    return rows


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_band_power_svg(path: Path, band_rows: list[dict[str, Any]]) -> None:
    values = np.array([row["mean_band_power"] or 0.0 for row in band_rows], dtype=float)
    max_value = float(np.nanmax(values)) if values.size and np.nanmax(values) > 0 else 1.0
    bars = []
    for index, row in enumerate(band_rows):
        x = 52 + index * 108
        bar_height = 190 * float(row["mean_band_power"] or 0.0) / max_value
        y = 252 - bar_height
        label = html.escape(str(row["band"]))
        bars.append(f'<rect x="{x}" y="{y:.2f}" width="64" height="{bar_height:.2f}" fill="#256f8f" />')
        bars.append(f'<text x="{x + 32}" y="278" text-anchor="middle" font-size="12">{label}</text>')
    path.write_text(_svg_frame("Band Power", "Band", "Mean band power", "\n".join(bars)), encoding="utf-8")


def _svg_frame(title: str, x_label: str, y_label: str, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="320" viewBox="0 0 640 320" role="img" aria-label="{html.escape(title)}">
  <rect width="640" height="320" fill="#ffffff"/>
  <text x="24" y="30" font-size="18" font-family="Arial" fill="#1f2933">{html.escape(title)}</text>
  <line x1="42" y1="252" x2="610" y2="252" stroke="#2f3a45" stroke-width="1"/>
  <line x1="42" y1="56" x2="42" y2="252" stroke="#2f3a45" stroke-width="1"/>
  <text x="326" y="306" font-size="12" text-anchor="middle" font-family="Arial" fill="#4f5b66">{html.escape(x_label)}</text>
  <text x="16" y="154" font-size="12" text-anchor="middle" font-family="Arial" fill="#4f5b66" transform="rotate(-90 16 154)">{html.escape(y_label)}</text>
  {body}
</svg>"""


def _band_power_table_dictionary(bands: dict[str, tuple[float, float]]) -> dict[str, Any]:
    return {
        "tables/band_power.csv": {
            "description": "Mean and median band power summarized by validated EEG frequency band across selected EEG channels.",
            "primary_key": ["band"],
            "columns": {
                "band": {"unit": None, "description": "Frequency band label."},
                "fmin": {"unit": "Hz", "description": "Effective inclusive lower frequency bound after sampling-rate checks."},
                "fmax": {"unit": "Hz", "description": "Effective exclusive upper frequency bound after sampling-rate checks."},
                "mean_band_power": {"unit": "power/Hz", "description": "Mean PSD over selected channels and effective band frequencies."},
                "median_band_power": {"unit": "power/Hz", "description": "Median PSD over selected channels and effective band frequencies."},
                "band_status": {"unit": None, "description": "Whether the band was included as configured or adjusted."},
                "parameter_note": {"unit": None, "description": "Reason for any frequency-band adjustment."},
            },
        },
        "tables/channel_band_power.csv": {
            "description": "Band power by selected EEG channel.",
            "primary_key": ["channel"],
            "columns": {
                "channel": {"unit": None, "description": "EEG channel name."},
                **{
                    band: {"unit": "power/Hz", "description": f"Mean PSD in the effective {band} band ({bounds[0]}-{bounds[1]} Hz)."}
                    for band, bounds in bands.items()
                },
            },
        },
    }
