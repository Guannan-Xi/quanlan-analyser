from __future__ import annotations

import csv
import html
import json
import math
import zipfile
from pathlib import Path
from typing import Any

import mne
import numpy as np
from scipy.signal import hilbert

from eeg_core.io.readers import read_raw
from eeg_core.report.reproducibility import stable_json_hash, write_analysis_sidecars, write_manifest, write_output_contract, write_reproducibility_files


PAC_PARAMETER_SCHEMA = {
    "workflow_id": {"type": "string", "default": "pac_cfc_beta"},
    "channels": {"type": "array", "items": "string", "default": []},
    "phase_freqs": {"type": "array", "items": "number", "default": [4.0, 6.0, 8.0]},
    "phase_band_width": {"type": "number", "default": 2.0, "minimum": 0.5},
    "amp_freqs": {"type": "array", "items": "number", "default": [70.0, 90.0, 110.0]},
    "amp_band_width": {"type": "number", "default": 20.0, "minimum": 1.0},
    "n_phase_bins": {"type": "integer", "default": 18, "minimum": 6, "maximum": 72},
    "time_window": {"type": "object", "default": {"start_sec": 0.0, "end_sec": None}},
    "dynamic_window_sec": {"type": "number", "default": 8.0, "minimum": 1.0},
    "dynamic_step_sec": {"type": "number", "default": 4.0, "minimum": 0.1},
    "bad_channels": {"type": "array", "items": "string", "default": []},
    "metric": {"type": "string", "default": "tort_modulation_index", "enum": ["tort_modulation_index"]},
    "surrogate_method": {"type": "string", "default": "time_shift", "enum": ["time_shift"]},
    "n_surrogates": {"type": "integer", "default": 20, "minimum": 1},
    "normalization": {"type": "string", "default": "zscore_against_surrogates", "enum": ["zscore_against_surrogates"]},
    "random_state": {"type": "integer", "default": 20260621},
}

PAC_BOUNDARY = (
    "Single-record descriptive PAC beta output only; not for clinical diagnosis, treatment decisions, "
    "causality, statistical inference, group comparison, brain-region communication, or source localization."
)


def describe_pac_scope() -> dict[str, Any]:
    return {
        "status": "beta_sensor_space_runner",
        "workflow_id": "pac_cfc_beta",
        "boundary": PAC_BOUNDARY,
    }


def run_pac(input_path: str | Path, output_dir: str | Path, parameters: dict | None = None) -> dict[str, Path]:
    output_path = Path(output_dir)
    figures = output_path / "figures"
    tables = output_path / "tables"
    reproducibility = output_path / "reproducibility"
    for directory in (figures, tables, reproducibility):
        directory.mkdir(parents=True, exist_ok=True)

    raw = read_raw(input_path, preload=True)
    if raw.get_channel_types().count("eeg") < 1:
        raise ValueError("PAC requires at least one EEG channel")
    eeg_all = raw.copy().pick_types(eeg=True, meg=False, eog=False, ecg=False, stim=False, exclude=[])
    params = validate_pac_parameters(parameters, channels=list(eeg_all.ch_names), sfreq=float(eeg_all.info["sfreq"]), duration_sec=float(eeg_all.n_times / eeg_all.info["sfreq"]))
    eeg_all.info["bads"] = sorted(set(eeg_all.info.get("bads", [])) | set(params["bad_channels"]))
    eeg = eeg_all.copy().pick_channels(params["channels"])
    if not eeg.ch_names:
        raise ValueError("PAC requires at least one usable selected EEG channel")

    start_sample = int(params["time_window"]["start_sec"] * eeg.info["sfreq"])
    end_sample = int(params["time_window"]["end_sec"] * eeg.info["sfreq"])
    data = eeg.get_data(reject_by_annotation="omit")[:, start_sample:end_sample]
    if data.shape[1] < 4:
        raise ValueError("PAC analysis window has too few samples")

    phase_bands = _bands_from_centers(params["phase_freqs"], params["phase_band_width"])
    amp_bands = _bands_from_centers(params["amp_freqs"], params["amp_band_width"])
    comod_rows, first_bins = _comodulogram_rows(data, eeg.ch_names, float(eeg.info["sfreq"]), phase_bands, amp_bands, params)
    dynamic_rows = _dynamic_rows(data, eeg.ch_names, float(eeg.info["sfreq"]), phase_bands[0], amp_bands[min(1, len(amp_bands) - 1)], params)
    summary_rows = _summary_rows(comod_rows, duration_sec=data.shape[1] / float(eeg.info["sfreq"]))

    comod_path = tables / "pac_comodulogram_long.csv"
    _write_csv(comod_path, comod_rows, ["file_id", "prep_plan_id", "epoch_set_id", "channel", "channel_group", "phase_fmin", "phase_fmax", "amp_fmin", "amp_fmax", "metric", "mi_value", "surrogate_method", "n_surrogates", "surrogate_mean_mi", "surrogate_std_mi", "normalized_mi_z", "random_state", "n_samples", "unit"])
    bins_path = tables / "pac_binned_amplitude.csv"
    _write_csv(bins_path, first_bins, ["channel", "phase_bin_index", "phase_bin_start_rad", "phase_bin_end_rad", "mean_amplitude", "normalized_amplitude", "sample_count"])
    dynamic_path = tables / "pac_dynamic_curve.csv"
    _write_csv(dynamic_path, dynamic_rows, ["channel", "window_start_sec", "window_end_sec", "phase_band_label", "amp_band_label", "metric", "mi_value"])
    summary_table_path = tables / "pac_channel_summary.csv"
    _write_csv(summary_table_path, summary_rows, ["channel", "channel_group", "peak_phase_band", "peak_amp_band", "peak_mi", "data_coverage_sec", "warnings"])

    comod_svg = figures / "pac_comodulogram.svg"
    bins_svg = figures / "pac_phase_bins.svg"
    dynamic_svg = figures / "pac_dynamic_curve.svg"
    _write_comod_svg(comod_svg, comod_rows, eeg.ch_names[0])
    _write_bins_svg(bins_svg, first_bins)
    _write_dynamic_svg(dynamic_svg, dynamic_rows)

    parameters_path = reproducibility / "parameters.json"
    params_hash = stable_json_hash(params)
    recorded_params = {**params, "parameters_hash": params_hash}
    parameters_path.write_text(json.dumps(recorded_params, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    frequency_grid_path = reproducibility / "frequency_grid.json"
    frequency_grid_path.write_text(json.dumps({
        "phase_bands_hz": phase_bands,
        "amplitude_bands_hz": amp_bands,
        "nyquist_hz": float(eeg.info["sfreq"]) / 2.0,
        "surrogate_method": params["surrogate_method"],
        "normalization": params["normalization"],
        "random_state": params["random_state"],
        "n_surrogates": params["n_surrogates"],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    filter_policy_path = reproducibility / "filter_edge_policy.json"
    filter_policy_path.write_text(json.dumps({"filter_engine": "mne.filter.filter_data", "hilbert_engine": "scipy.signal.hilbert", "edge_trim_sec": 0.0, "window_too_short_policy": "block"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    method_path = reproducibility / "method_description.txt"
    method_path.write_text(
        "PAC beta computes Tort-style modulation index from low-frequency phase bins and high-frequency amplitude envelope. "
        "Outputs describe one recording in sensor/channel space only. This module does not output p-values, group statistics, "
        "causality, diagnosis, source localization, or brain-region communication.\n",
        encoding="utf-8",
    )
    summary = {
        "status": "computed",
        "module_id": "pac_cfc",
        "workflow_id": "pac_cfc_beta",
        "lifecycle_state": "beta",
        "engine": "mne_filter_plus_scipy_hilbert",
        "channels": list(eeg.ch_names),
        "sfreq": float(eeg.info["sfreq"]),
        "duration_sec": float(data.shape[1] / eeg.info["sfreq"]),
        "peak_mi": max(float(row["mi_value"]) for row in comod_rows),
        "surrogate_method": params["surrogate_method"],
        "normalization": params["normalization"],
        "random_state": params["random_state"],
        "n_surrogates": params["n_surrogates"],
        "warnings": [
            "Single-record descriptive PAC beta output only.",
            "No p-value, significance, group comparison, diagnosis, causality, or source-localization conclusion is produced.",
        ],
        "boundary": PAC_BOUNDARY,
    }
    pac_summary_path = reproducibility / "pac_summary.json"
    pac_summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    reproducibility_paths = write_reproducibility_files(
        output_path,
        module_name="pac_cfc",
        input_path=input_path,
        parameters=recorded_params,
        workflow_steps=[
            {"name": "read_raw", "description": "Read EEG with MNE."},
            {"name": "validate", "description": "Validate channels, frequency bands, Nyquist, and analysis window."},
            {"name": "filter_hilbert", "description": "Extract low-frequency phase and high-frequency amplitude envelope."},
            {"name": "compute_mi", "description": "Compute Tort-style modulation index and phase-bin amplitude tables."},
            {"name": "write_outputs", "description": "Write tables, figures, summaries, and reproducibility files."},
        ],
    )
    sidecars = write_analysis_sidecars(
        output_path,
        module_name="pac_cfc",
        parameter_schema=PAC_PARAMETER_SCHEMA,
        effective_call={
            "engine": "mne_filter_plus_scipy_hilbert",
            "call": "mne.filter.filter_data + scipy.signal.hilbert + tort_modulation_index",
            "kwargs": {
                "phase_bands_hz": phase_bands,
                "amplitude_bands_hz": amp_bands,
                "n_phase_bins": params["n_phase_bins"],
                "surrogate_method": params["surrogate_method"],
                "normalization": params["normalization"],
                "random_state": params["random_state"],
                "n_surrogates": params["n_surrogates"],
            },
            "input_shape": {"channels": list(eeg.ch_names), "n_times": int(data.shape[1]), "sfreq": float(eeg.info["sfreq"])},
            "output_shape": {"comodulogram_rows": len(comod_rows), "dynamic_rows": len(dynamic_rows)},
        },
        threshold_validation={
            "status": "passed",
            "checks": [
                {"field": "amp_freqs", "rule": "max amplitude band < Nyquist", "value": max(params["amp_freqs"]), "nyquist_hz": float(eeg.info["sfreq"]) / 2.0, "status": "passed"},
                {"field": "phase_amp_order", "rule": "phase frequencies lower than amplitude frequencies", "status": "passed"},
                {"field": "window", "rule": "analysis window supports at least four cycles of lowest phase frequency", "status": "passed"},
            ],
        },
        table_dictionary=_table_dictionary(),
        scope_contract={
            "scope": "single_record_descriptive_beta",
            "forbidden": ["diagnosis", "p_value", "significance", "group_comparison", "causality", "brain_region_communication", "source_localization"],
            "boundary": PAC_BOUNDARY,
        },
        source_metadata=_source_metadata(input_path, raw, eeg, recorded_params),
    )
    table_dictionary_path = sidecars["table_dictionary"]
    table_dictionary_path.write_text(json.dumps(_table_dictionary(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    outputs = {
        "pac_beta_artifact_bundle": output_path / "pac_beta_artifact_bundle.zip",
        "pac_comodulogram_long": comod_path,
        "pac_binned_amplitude": bins_path,
        "pac_dynamic_curve": dynamic_path,
        "pac_channel_summary": summary_table_path,
        "pac_comodulogram": comod_svg,
        "pac_phase_bins": bins_svg,
        "pac_dynamic_curve_figure": dynamic_svg,
        "parameters": parameters_path,
        "frequency_grid": frequency_grid_path,
        "filter_edge_policy": filter_policy_path,
        "pac_summary": pac_summary_path,
        "method_description": method_path,
        "software_versions": reproducibility_paths["software_versions"],
        "workflow": reproducibility_paths["workflow"],
        "parameter_schema_snapshot": sidecars["parameter_schema_snapshot"],
        "threshold_validation": sidecars["threshold_validation"],
        "effective_call": sidecars["effective_call"],
        "source_metadata": sidecars["source_metadata"],
        "table_dictionary": sidecars["table_dictionary"],
        "scope_contract": sidecars["scope_contract"],
    }
    contracts = write_output_contract(
        output_path,
        job_type="pac_cfc_beta",
        module_name="pac_cfc",
        input_path=input_path,
        parameters=recorded_params,
        summary={
            "schema_version": "qlanalyser-pac-beta-result-v0.1",
            "module_id": "pac_cfc",
            "workflow_id": "pac_cfc_beta",
            "input_file_id": str(Path(input_path).name),
            "data_preparation_plan_id": str(params.get("data_preparation_plan_id") or "none"),
            "parameters_hash": params_hash,
            "summary": summary,
            "artifacts": [str(path.relative_to(output_path).as_posix()) for path in outputs.values() if path.exists() and path.is_relative_to(output_path)],
            "warnings": summary["warnings"],
        },
        outputs=outputs,
        log_lines=[
            f"channels={','.join(eeg.ch_names)}",
            f"phase_bands_hz={phase_bands}",
            f"amplitude_bands_hz={amp_bands}",
            f"rows={len(comod_rows)}",
        ],
    )
    _merge_pac_result_contract(contracts["result"], params, params_hash, summary, outputs, output_path)
    contracts["manifest"] = write_manifest(output_path)
    bundle_path = outputs["pac_beta_artifact_bundle"]
    _write_bundle_zip(
        bundle_path,
        output_path,
        [
            bundle_path,
            comod_path,
            bins_path,
            dynamic_path,
            summary_table_path,
            comod_svg,
            bins_svg,
            dynamic_svg,
            parameters_path,
            frequency_grid_path,
            filter_policy_path,
            pac_summary_path,
            method_path,
            reproducibility_paths["software_versions"],
            reproducibility_paths["workflow"],
            sidecars["parameter_schema_snapshot"],
            sidecars["threshold_validation"],
            sidecars["effective_call"],
            sidecars["source_metadata"],
            sidecars["table_dictionary"],
            sidecars["scope_contract"],
        ],
    )
    return {**outputs, **contracts}


def _write_bundle_zip(bundle_path: Path, output_root: Path, preferred_paths: list[Path]) -> None:
    ordered: list[Path] = []
    seen: set[Path] = set()
    for path in preferred_paths:
        if path == bundle_path or not path.exists() or not path.is_file():
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(path)
    for path in sorted(output_root.rglob("*")):
        if path == bundle_path or not path.is_file():
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(path)
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in ordered:
            try:
                arcname = path.relative_to(output_root).as_posix()
            except ValueError:
                arcname = path.name
            zf.write(path, arcname)


def validate_pac_parameters(parameters: dict | None, *, channels: list[str], sfreq: float, duration_sec: float) -> dict[str, Any]:
    source = parameters or {}
    params = dict(source)
    params["workflow_id"] = "pac_cfc_beta"
    params["metric"] = "tort_modulation_index"
    params["surrogate_method"] = "time_shift"
    params["normalization"] = "zscore_against_surrogates"
    params["n_surrogates"] = _optional_int(source.get("n_surrogates"), default=20, name="n_surrogates")
    params["random_state"] = _optional_int(source.get("random_state"), default=20260621, name="random_state")
    params["bad_channels"] = _string_list(source.get("bad_channels"), name="bad_channels")
    usable_channels = [channel for channel in channels if channel not in set(params["bad_channels"])]
    selected = _string_list(source.get("channels"), name="channels")
    params["channels"] = selected or usable_channels[: min(2, len(usable_channels))]
    missing = [channel for channel in params["channels"] + params["bad_channels"] if channel not in set(channels)]
    if missing:
        raise ValueError(f"PAC channels not found: {', '.join(sorted(set(missing)))}")
    if not params["channels"]:
        raise ValueError("PAC requires at least one selected channel")
    params["phase_freqs"] = _number_list(source.get("phase_freqs"), default=[4.0, 6.0, 8.0], name="phase_freqs")
    params["amp_freqs"] = _number_list(source.get("amp_freqs"), default=[70.0, 90.0, 110.0], name="amp_freqs")
    params["phase_band_width"] = _optional_float(source.get("phase_band_width"), default=2.0, name="phase_band_width")
    params["amp_band_width"] = _optional_float(source.get("amp_band_width"), default=20.0, name="amp_band_width")
    params["n_phase_bins"] = _optional_int(source.get("n_phase_bins"), default=18, name="n_phase_bins")
    params["dynamic_window_sec"] = _optional_float(source.get("dynamic_window_sec"), default=8.0, name="dynamic_window_sec")
    params["dynamic_step_sec"] = _optional_float(source.get("dynamic_step_sec"), default=4.0, name="dynamic_step_sec")
    params["filter_edge_padding_sec"] = _optional_float(source.get("filter_edge_padding_sec"), default=2.0, name="filter_edge_padding_sec")
    params["edge_trim_sec"] = _optional_float(source.get("edge_trim_sec"), default=0.0, name="edge_trim_sec")
    window = source.get("time_window") if isinstance(source.get("time_window"), dict) else {}
    start_sec = _optional_float(window.get("start_sec"), default=0.0, name="time_window.start_sec")
    end_raw = window.get("end_sec")
    end_sec = duration_sec if end_raw in (None, "") else _optional_float(end_raw, default=duration_sec, name="time_window.end_sec")
    params["time_window"] = {"start_sec": start_sec, "end_sec": end_sec}
    nyquist = sfreq / 2.0
    if params["phase_band_width"] <= 0 or params["amp_band_width"] <= 0:
        raise ValueError("PAC band widths must be positive")
    if not (6 <= params["n_phase_bins"] <= 72):
        raise ValueError("PAC n_phase_bins must be between 6 and 72")
    if max(params["phase_freqs"]) >= min(params["amp_freqs"]):
        raise ValueError("PAC phase frequencies must be lower than amplitude frequencies")
    if max(params["amp_freqs"]) + params["amp_band_width"] / 2.0 >= nyquist:
        raise ValueError(f"PAC amplitude band must be below Nyquist ({nyquist:g} Hz)")
    if start_sec < 0 or end_sec <= start_sec or end_sec > duration_sec + 1e-6:
        raise ValueError("PAC time_window must fit inside the recording")
    lowest_phase = min(params["phase_freqs"]) - params["phase_band_width"] / 2.0
    if lowest_phase <= 0:
        raise ValueError("PAC lowest phase band edge must be > 0 Hz")
    if (end_sec - start_sec) < 4.0 / lowest_phase:
        raise ValueError("PAC analysis window is too short for the lowest phase frequency")
    if params["dynamic_window_sec"] > (end_sec - start_sec):
        params["dynamic_window_sec"] = end_sec - start_sec
    if params["dynamic_step_sec"] <= 0:
        raise ValueError("PAC dynamic_step_sec must be positive")
    if params["filter_edge_padding_sec"] < 0 or params["edge_trim_sec"] < 0:
        raise ValueError("PAC filter_edge_padding_sec and edge_trim_sec must be non-negative")
    if params["n_surrogates"] < 1:
        raise ValueError("PAC n_surrogates must be >= 1")
    params.setdefault("data_preparation_plan_id", source.get("data_preparation_plan_id") or "none")
    params.setdefault("data_preparation_revision", source.get("data_preparation_revision"))
    return params


def _comodulogram_rows(data: np.ndarray, channels: list[str], sfreq: float, phase_bands: list[tuple[float, float]], amp_bands: list[tuple[float, float]], params: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    first_bins: list[dict[str, Any]] = []
    for ch_index, channel in enumerate(channels):
        signal = data[ch_index]
        for phase_band in phase_bands:
            phase = _phase_signal(signal, sfreq, phase_band)
            for amp_band in amp_bands:
                amp = _amplitude_envelope(signal, sfreq, amp_band)
                mi, bins = _tort_mi(phase, amp, params["n_phase_bins"])
                surrogate = _surrogate_stats(
                    phase,
                    amp,
                    params["n_phase_bins"],
                    params["n_surrogates"],
                    int(params["random_state"]) + ch_index * 1009 + len(rows),
                )
                rows.append(
                    {
                        "file_id": str(params.get("input_file_id") or "current_file"),
                        "prep_plan_id": str(params.get("data_preparation_plan_id") or "none"),
                        "epoch_set_id": "",
                        "channel": channel,
                        "channel_group": "single_channel",
                        "phase_fmin": phase_band[0],
                        "phase_fmax": phase_band[1],
                        "amp_fmin": amp_band[0],
                        "amp_fmax": amp_band[1],
                        "metric": "tort_modulation_index",
                        "mi_value": round(mi, 8),
                        "surrogate_method": params["surrogate_method"],
                        "n_surrogates": params["n_surrogates"],
                        "surrogate_mean_mi": round(surrogate["mean"], 8),
                        "surrogate_std_mi": round(surrogate["std"], 8),
                        "normalized_mi_z": round((mi - surrogate["mean"]) / surrogate["std"], 8) if surrogate["std"] > 0 else 0.0,
                        "random_state": params["random_state"],
                        "n_samples": int(signal.size),
                        "unit": "a.u.",
                    }
                )
                if not first_bins:
                    first_bins = [
                        {
                            "channel": channel,
                            "phase_bin_index": item["phase_bin_index"],
                            "phase_bin_start_rad": item["phase_bin_start_rad"],
                            "phase_bin_end_rad": item["phase_bin_end_rad"],
                            "mean_amplitude": round(item["mean_amplitude"], 10),
                            "normalized_amplitude": round(item["normalized_amplitude"], 10),
                            "sample_count": item["sample_count"],
                        }
                        for item in bins
                    ]
    return rows, first_bins


def _dynamic_rows(data: np.ndarray, channels: list[str], sfreq: float, phase_band: tuple[float, float], amp_band: tuple[float, float], params: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    win = max(int(params["dynamic_window_sec"] * sfreq), 4)
    step = max(int(params["dynamic_step_sec"] * sfreq), 1)
    for ch_index, channel in enumerate(channels):
        signal = data[ch_index]
        for start in range(0, max(signal.size - win + 1, 1), step):
            chunk = signal[start : start + win]
            if chunk.size < win:
                continue
            phase = _phase_signal(chunk, sfreq, phase_band)
            amp = _amplitude_envelope(chunk, sfreq, amp_band)
            mi, _ = _tort_mi(phase, amp, params["n_phase_bins"])
            rows.append(
                {
                    "channel": channel,
                    "window_start_sec": round(start / sfreq, 6),
                    "window_end_sec": round((start + win) / sfreq, 6),
                    "phase_band_label": f"{phase_band[0]:g}-{phase_band[1]:g} Hz",
                    "amp_band_label": f"{amp_band[0]:g}-{amp_band[1]:g} Hz",
                    "metric": "tort_modulation_index",
                    "mi_value": round(mi, 8),
                }
            )
    return rows


def _phase_signal(signal: np.ndarray, sfreq: float, band: tuple[float, float]) -> np.ndarray:
    filtered = mne.filter.filter_data(signal.astype(float), sfreq=sfreq, l_freq=band[0], h_freq=band[1], verbose=False)
    return np.angle(hilbert(filtered))


def _amplitude_envelope(signal: np.ndarray, sfreq: float, band: tuple[float, float]) -> np.ndarray:
    filtered = mne.filter.filter_data(signal.astype(float), sfreq=sfreq, l_freq=band[0], h_freq=band[1], verbose=False)
    return np.abs(hilbert(filtered))


def _tort_mi(phase: np.ndarray, amp: np.ndarray, n_bins: int) -> tuple[float, list[dict[str, Any]]]:
    edges = np.linspace(-math.pi, math.pi, n_bins + 1)
    means = []
    rows = []
    for index in range(n_bins):
        mask = (phase >= edges[index]) & (phase < edges[index + 1] if index < n_bins - 1 else phase <= edges[index + 1])
        mean_amp = float(np.mean(amp[mask])) if np.any(mask) else 0.0
        means.append(mean_amp)
        rows.append(
            {
                "phase_bin_index": index,
                "phase_bin_start_rad": round(float(edges[index]), 8),
                "phase_bin_end_rad": round(float(edges[index + 1]), 8),
                "mean_amplitude": mean_amp,
                "sample_count": int(np.sum(mask)),
            }
        )
    means_arr = np.asarray(means, dtype=float)
    total = float(means_arr.sum())
    if total <= 0:
        probs = np.ones(n_bins) / n_bins
    else:
        probs = means_arr / total
    entropy = -float(np.sum([p * math.log(p) for p in probs if p > 0]))
    mi = (math.log(n_bins) - entropy) / math.log(n_bins)
    for row, prob in zip(rows, probs):
        row["normalized_amplitude"] = float(prob)
    return max(0.0, float(mi)), rows


def _surrogate_stats(phase: np.ndarray, amp: np.ndarray, n_bins: int, n_surrogates: int, seed: int) -> dict[str, float]:
    if amp.size < 4:
        return {"mean": 0.0, "std": 0.0}
    rng = np.random.default_rng(seed)
    values = []
    low = max(1, int(0.1 * amp.size))
    high = max(low + 1, int(0.9 * amp.size))
    for _ in range(n_surrogates):
        shift = int(rng.integers(low, high))
        shifted_amp = np.roll(amp, shift)
        mi, _ = _tort_mi(phase, shifted_amp, n_bins)
        values.append(mi)
    values_arr = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(values_arr)),
        "std": float(np.std(values_arr, ddof=1)) if values_arr.size > 1 else 0.0,
    }


def _summary_rows(comod_rows: list[dict[str, Any]], *, duration_sec: float) -> list[dict[str, Any]]:
    by_channel: dict[str, list[dict[str, Any]]] = {}
    for row in comod_rows:
        by_channel.setdefault(str(row["channel"]), []).append(row)
    rows = []
    for channel, channel_rows in by_channel.items():
        peak = max(channel_rows, key=lambda item: float(item["mi_value"]))
        rows.append(
            {
                "channel": channel,
                "channel_group": "single_channel",
                "peak_phase_band": f"{peak['phase_fmin']}-{peak['phase_fmax']} Hz",
                "peak_amp_band": f"{peak['amp_fmin']}-{peak['amp_fmax']} Hz",
                "peak_mi": peak["mi_value"],
                "data_coverage_sec": round(duration_sec, 6),
                "warnings": "single-record descriptive beta; no statistical inference",
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_comod_svg(path: Path, rows: list[dict[str, Any]], channel: str) -> None:
    selected = [row for row in rows if row["channel"] == channel]
    phases = sorted({(float(row["phase_fmin"]), float(row["phase_fmax"])) for row in selected})
    amps = sorted({(float(row["amp_fmin"]), float(row["amp_fmax"])) for row in selected})
    lookup = {(float(row["phase_fmin"]), float(row["amp_fmin"])): float(row["mi_value"]) for row in selected}
    max_value = max(lookup.values() or [1.0])
    cell = 58
    left, top = 130, 70
    body = []
    for y, amp in enumerate(amps):
        body.append(f'<text x="{left - 10}" y="{top + y * cell + 34}" text-anchor="end" font-size="12">{amp[0]:g}-{amp[1]:g}</text>')
        for x, phase in enumerate(phases):
            if y == 0:
                body.append(f'<text x="{left + x * cell + 29}" y="{top - 10}" text-anchor="middle" font-size="12">{phase[0]:g}-{phase[1]:g}</text>')
            value = lookup.get((phase[0], amp[0]), 0.0)
            body.append(f'<rect x="{left + x * cell}" y="{top + y * cell}" width="{cell}" height="{cell}" fill="{_heat_color(value, max_value)}" stroke="#ffffff"/>')
            body.append(f'<text x="{left + x * cell + 29}" y="{top + y * cell + 34}" text-anchor="middle" font-size="10" fill="#172026">{value:.3f}</text>')
    width = left + len(phases) * cell + 80
    height = top + len(amps) * cell + 100
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="#ffffff"/>
  <text x="{width / 2:.1f}" y="30" text-anchor="middle" font-size="18" fill="#10242c">PAC comodulogram</text>
  <text x="{width / 2:.1f}" y="{height - 30}" text-anchor="middle" font-size="12" fill="#52616a">MI values describe one sensor channel only; no statistical inference.</text>
  <text x="24" y="{top + len(amps) * cell / 2:.1f}" transform="rotate(-90 24 {top + len(amps) * cell / 2:.1f})" text-anchor="middle" font-size="12">Amplitude band Hz</text>
  <text x="{left + len(phases) * cell / 2:.1f}" y="{height - 58}" text-anchor="middle" font-size="12">Phase band Hz</text>
  {''.join(body)}
</svg>
""",
        encoding="utf-8",
    )


def _write_bins_svg(path: Path, rows: list[dict[str, Any]]) -> None:
    width, height = 820, 420
    left, bottom, top = 72, 340, 70
    plot_w = 700
    max_amp = max(float(row["mean_amplitude"]) for row in rows) or 1.0
    bars = []
    for row in rows:
        index = int(row["phase_bin_index"])
        x = left + index * (plot_w / len(rows))
        bar_h = (float(row["mean_amplitude"]) / max_amp) * (bottom - top)
        bars.append(f'<rect x="{x:.1f}" y="{bottom - bar_h:.1f}" width="{plot_w / len(rows) - 2:.1f}" height="{bar_h:.1f}" fill="#2f80a7"/>')
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="#ffffff"/>
  <text x="410" y="32" text-anchor="middle" font-size="18" fill="#10242c">Mean amplitude by phase bin</text>
  <line x1="{left}" y1="{bottom}" x2="{left + plot_w}" y2="{bottom}" stroke="#334155"/>
  <line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#334155"/>
  {''.join(bars)}
  <text x="410" y="390" text-anchor="middle" font-size="12" fill="#52616a">Bins run from -pi to pi. Uneven distribution yields higher MI.</text>
</svg>
""",
        encoding="utf-8",
    )


def _write_dynamic_svg(path: Path, rows: list[dict[str, Any]]) -> None:
    selected = rows[: max(1, min(len(rows), 24))]
    width, height = 820, 420
    left, bottom, top = 72, 340, 70
    plot_w = 700
    max_mi = max(float(row["mi_value"]) for row in selected) or 1.0
    points = []
    for index, row in enumerate(selected):
        x = left + index * (plot_w / max(len(selected) - 1, 1))
        y = bottom - (float(row["mi_value"]) / max_mi) * (bottom - top)
        points.append((x, y))
    path_data = " ".join([f"{'M' if idx == 0 else 'L'} {x:.1f} {y:.1f}" for idx, (x, y) in enumerate(points)])
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="#ffffff"/>
  <text x="410" y="32" text-anchor="middle" font-size="18" fill="#10242c">PAC dynamic curve</text>
  <line x1="{left}" y1="{bottom}" x2="{left + plot_w}" y2="{bottom}" stroke="#334155"/>
  <line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#334155"/>
  <path d="{path_data}" fill="none" stroke="#b33f62" stroke-width="3"/>
  <text x="410" y="390" text-anchor="middle" font-size="12" fill="#52616a">Windowed MI over time; descriptive only, not a window comparison test.</text>
</svg>
""",
        encoding="utf-8",
    )


def _heat_color(value: float, max_value: float) -> str:
    scale = 0.0 if max_value <= 0 else max(0.0, min(1.0, value / max_value))
    red = int(248 - 70 * scale)
    green = int(244 - 155 * scale)
    blue = int(236 - 190 * scale)
    return f"rgb({red},{green},{blue})"


def _bands_from_centers(centers: list[float], width: float) -> list[tuple[float, float]]:
    return [(round(center - width / 2.0, 6), round(center + width / 2.0, 6)) for center in centers]


def _table_dictionary() -> dict[str, Any]:
    return {
        "tables/pac_comodulogram_long.csv": {key: "PAC beta long-format comodulogram column" for key in ["file_id", "prep_plan_id", "epoch_set_id", "channel", "channel_group", "phase_fmin", "phase_fmax", "amp_fmin", "amp_fmax", "metric", "mi_value", "surrogate_method", "n_surrogates", "surrogate_mean_mi", "surrogate_std_mi", "normalized_mi_z", "random_state", "n_samples", "unit"]},
        "tables/pac_binned_amplitude.csv": {key: "PAC beta phase-bin amplitude column" for key in ["channel", "phase_bin_index", "phase_bin_start_rad", "phase_bin_end_rad", "mean_amplitude", "normalized_amplitude", "sample_count"]},
        "tables/pac_dynamic_curve.csv": {key: "PAC beta dynamic-curve column" for key in ["channel", "window_start_sec", "window_end_sec", "phase_band_label", "amp_band_label", "metric", "mi_value"]},
        "tables/pac_channel_summary.csv": {key: "PAC beta channel-summary column" for key in ["channel", "channel_group", "peak_phase_band", "peak_amp_band", "peak_mi", "data_coverage_sec", "warnings"]},
    }


def _source_metadata(input_path: str | Path, raw, eeg, params: dict[str, Any]) -> dict[str, Any]:
    path = Path(input_path)
    return {
        "source_file": {"filename": path.name, "suffix": path.suffix.lower(), "size_bytes": path.stat().st_size if path.exists() else None},
        "recording_metadata": {
            "sfreq_hz": float(raw.info["sfreq"]),
            "n_times": int(raw.n_times),
            "duration_sec": float(raw.n_times / raw.info["sfreq"]),
            "channel_names": list(raw.ch_names),
            "used_eeg_channels": list(eeg.ch_names),
        },
        "parameters_hash": stable_json_hash(params),
    }


def _merge_pac_result_contract(result_path: Path, params: dict[str, Any], params_hash: str, summary: dict[str, Any], outputs: dict[str, Path], output_path: Path) -> None:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    artifacts = []
    for path in outputs.values():
        if path.exists() and path.is_file():
            try:
                artifacts.append(path.relative_to(output_path).as_posix())
            except ValueError:
                artifacts.append(path.name)
    result.update(
        {
            "schema_version": "qlanalyser-pac-beta-result-v0.1",
            "module_id": "pac_cfc",
            "workflow_id": "pac_cfc_beta",
            "input_file_id": str(params.get("input_file_id") or result.get("input", {}).get("filename") or "current_file"),
            "data_preparation_plan_id": str(params.get("data_preparation_plan_id") or "none"),
            "parameters_hash": params_hash,
            "artifacts": artifacts,
            "warnings": summary.get("warnings", []),
        }
    )
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _optional_float(value, *, default: float | None, name: str) -> float:
    if value is None or value == "":
        return float(default)
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"PAC {name} must be a number") from exc
    if not math.isfinite(result):
        raise ValueError(f"PAC {name} must be finite")
    return result


def _optional_int(value, *, default: int, name: str) -> int:
    if value is None or value == "":
        return int(default)
    if isinstance(value, bool):
        raise ValueError(f"PAC {name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"PAC {name} must be an integer") from exc


def _number_list(value, *, default: list[float], name: str) -> list[float]:
    if value is None or value == "":
        return list(default)
    if isinstance(value, str):
        raw_values = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, list):
        raw_values = value
    else:
        raise ValueError(f"PAC {name} must be a number list")
    try:
        values = [float(item) for item in raw_values]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"PAC {name} must contain only numbers") from exc
    if not values or any(not math.isfinite(item) or item <= 0 for item in values):
        raise ValueError(f"PAC {name} must contain positive finite numbers")
    return values


def _string_list(value, *, name: str) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"PAC {name} must be a list of strings")
    return value
