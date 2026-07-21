"""
PAC V2 — Phase-Amplitude Coupling analysis module (beta/lab-only).

This module implements multiple PAC metrics (MI, MVL, KL divergence) for
research and lab validation purposes only. Not for formal customer tasks,
billing, reports, or clinical use.

Retained in beta/lab-only status after validation review:
- 6 real EEG scenarios, MI correlation r=1.000000 with V1
- 2.22x-4.74x speed improvement over V1
- E2E lab integration verified
- P1 issues resolved (parameters now visible by default)
- P2 bug fixed (duration_sec now uses actual sfreq)

Status: beta/lab-only; requires method-owner review before any formal delivery promotion.
Owner: 07 PM / QLanalyser lab lane
"""

from __future__ import annotations

import csv
import json
import logging
import math
import time
from pathlib import Path
from typing import Any

import mne
import numpy as np
from scipy.signal import hilbert

from eeg_core.io.readers import read_raw
from eeg_core.report.reproducibility import stable_json_hash, write_analysis_sidecars, write_output_contract, write_reproducibility_files

PAC_V2_PARAMETER_SCHEMA = {
    "channels": {"type": "array", "items": {"type": "string"}, "default": "first_two_eeg_channels"},
    "phase_freqs": {"type": "array", "items": {"type": "number"}, "default": [4.0, 6.0, 8.0]},
    "amp_freqs": {"type": "array", "items": {"type": "number"}, "default": [30.0, 50.0, 70.0]},
    "phase_band_width": {"type": "number", "default": 2.0},
    "amp_band_width": {"type": "number", "default": 20.0},
    "n_phase_bins": {"type": "integer", "default": 18},
    "coupling_metric": {"type": "string", "enum": ["mi", "mvl", "kl_divergence"], "default": "mi"},
    "n_surrogates": {"type": "integer", "default": 100},
    "random_state": {"type": "integer", "default": 20260703},
    "time_window": {"type": "object", "default": {"start_sec": 0.0, "end_sec": "recording_end"}},
}

# Non-medical boundary statement
PAC_V2_BOUNDARY = (
    "Single-record descriptive sensor-space PAC/CFC lab output only. "
    "Not for diagnosis, treatment, clinical decision support, causality, "
    "source localization, brain-region communication, or group-level inference."
)


def run_pac_v2(
    input_path: str | Path, 
    output_dir: str | Path, 
    parameters: dict | None = None
) -> dict[str, Path]:
    """
    Run PAC V2 lab-only analysis with multiple coupling metrics.
    
    Parameters:
        input_path: Path to EEG file (.fif, .edf)
        output_dir: Output directory for artifacts
        parameters: Optional parameters dict
        
    Returns:
        Dict mapping artifact names to paths
        
    Output structure:
        result.json
        manifest.json
        log.txt
        tables/pac_v2_long.csv
        tables/pac_v2_channel_summary.csv
        reproducibility/parameters.json
        reproducibility/method_description.txt
    """
    start_time = time.time()
    output_path = Path(output_dir)
    tables = output_path / "tables"
    reproducibility = output_path / "reproducibility"
    
    for directory in (tables, reproducibility):
        directory.mkdir(parents=True, exist_ok=True)
    
    # Setup logging
    log_lines = []
    log_lines.append(f"PAC V2 started at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_lines.append(f"Input: {input_path}")
    
    # Load data
    raw = read_raw(input_path, preload=True)
    if raw.get_channel_types().count("eeg") < 1:
        raise ValueError("PAC V2 requires at least one EEG channel")
    
    eeg_all = raw.copy().pick_types(eeg=True, meg=False, eog=False, ecg=False, stim=False, exclude=[])
    log_lines.append(f"Loaded {len(eeg_all.ch_names)} EEG channels")
    
    # Validate parameters
    params = _validate_pac_v2_parameters(
        parameters,
        channels=list(eeg_all.ch_names),
        sfreq=float(eeg_all.info["sfreq"]),
        duration_sec=float(eeg_all.n_times / eeg_all.info["sfreq"])
    )
    log_lines.append(f"Parameters validated: {params['coupling_metric']} metric")
    
    # Select channels
    eeg = eeg_all.copy().pick_channels(params["channels"])
    if not eeg.ch_names:
        raise ValueError("PAC V2 requires at least one selected EEG channel")
    
    log_lines.append(f"Selected channels: {', '.join(eeg.ch_names)}")
    
    # Extract time window
    start_sample = int(params["time_window"]["start_sec"] * eeg.info["sfreq"])
    end_sample = int(params["time_window"]["end_sec"] * eeg.info["sfreq"])
    data = eeg.get_data(reject_by_annotation="omit")[:, start_sample:end_sample]
    
    if data.shape[1] < 4:
        raise ValueError("PAC V2 analysis window has too few samples")
    
    log_lines.append(f"Data shape: {data.shape[0]} channels x {data.shape[1]} samples")
    
    # Build frequency bands
    phase_bands = _bands_from_centers(params["phase_freqs"], params["phase_band_width"])
    amp_bands = _bands_from_centers(params["amp_freqs"], params["amp_band_width"])
    
    log_lines.append(f"Phase bands: {phase_bands}")
    log_lines.append(f"Amplitude bands: {amp_bands}")
    
    # Compute PAC
    pac_rows = _compute_pac_v2(
        data=data,
        channels=eeg.ch_names,
        sfreq=float(eeg.info["sfreq"]),
        phase_bands=phase_bands,
        amp_bands=amp_bands,
        params=params,
        log_lines=log_lines
    )
    
    log_lines.append(f"Computed {len(pac_rows)} PAC combinations")
    
    # Compute channel summary
    summary_rows = _compute_channel_summary(pac_rows, eeg.ch_names, float(eeg.info["sfreq"]))
    
    # Write tables
    pac_long_path = tables / "pac_v2_long.csv"
    _write_csv(pac_long_path, pac_rows, [
        "channel", "phase_fmin", "phase_fmax", "amp_fmin", "amp_fmax",
        "coupling_metric", "pac_value", "n_surrogates", "surrogate_mean",
        "surrogate_std", "normalized_z", "random_state", "n_samples"
    ])
    
    summary_path = tables / "pac_v2_channel_summary.csv"
    _write_csv(summary_path, summary_rows, [
        "channel", "coupling_metric", "peak_phase_band", "peak_amp_band",
        "peak_pac_value", "duration_sec", "warnings"
    ])
    
    log_lines.append(f"Tables written to {tables}")
    
    # Write reproducibility files
    params_hash = stable_json_hash(params)
    recorded_params = {**params, "parameters_hash": params_hash}
    
    parameters_path = reproducibility / "parameters.json"
    parameters_path.write_text(
        json.dumps(recorded_params, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    
    method_path = reproducibility / "method_description.txt"
    method_path.write_text(
        "PAC V2 lab-only module computes phase-amplitude coupling using configurable metrics "
        "(MI, MVL, KL divergence). Outputs describe one recording in sensor/channel space only. "
        "This module is for research validation and does not output p-values, group statistics, "
        "causality, diagnosis, source localization, or brain-region communication.\n",
        encoding="utf-8"
    )
    
    log_lines.append("Reproducibility files written")
    
    elapsed_time = time.time() - start_time
    log_lines.append(f"PAC V2 completed in {elapsed_time:.2f} seconds")

    reproducibility_paths = write_reproducibility_files(
        output_path,
        module_name="pac_v2",
        input_path=input_path,
        parameters=recorded_params,
        workflow_steps=[
            {"name": "read_raw", "description": "Read EEG data with MNE using a format-specific reader."},
            {"name": "select_channels", "description": "Select configured EEG channels."},
            {"name": "filter_hilbert", "description": "Extract low-frequency phase and high-frequency amplitude envelope."},
            {"name": "compute_pac_v2", "description": "Compute configured PAC metric values for channel and band combinations."},
            {"name": "write_outputs", "description": "Write tables, method text, sidecars, result, manifest, and log."},
        ],
    )
    sidecars = write_analysis_sidecars(
        output_path,
        module_name="pac_v2",
        parameter_schema=PAC_V2_PARAMETER_SCHEMA,
        effective_call={
            "engine": "mne_filter_plus_scipy_hilbert",
            "call": "pac_v2_configurable_metric",
            "kwargs": {
                "phase_bands_hz": phase_bands,
                "amplitude_bands_hz": amp_bands,
                "coupling_metric": params["coupling_metric"],
                "n_phase_bins": params["n_phase_bins"],
                "n_surrogates": params["n_surrogates"],
                "random_state": params["random_state"],
            },
            "input_shape": {"channels": list(eeg.ch_names), "n_times": int(data.shape[1]), "sfreq": float(eeg.info["sfreq"])},
            "output_shape": {"pac_rows": len(pac_rows), "channel_summary_rows": len(summary_rows)},
        },
        threshold_validation={
            "status": "passed",
            "checks": [
                {"field": "amp_freqs", "rule": "max amplitude band < Nyquist", "value": max(params["amp_freqs"]), "nyquist_hz": float(eeg.info["sfreq"]) / 2.0, "status": "passed"},
                {"field": "phase_amp_order", "rule": "phase frequencies lower than amplitude frequencies", "status": "passed"},
                {"field": "window", "rule": "analysis window supports at least four cycles of lowest phase frequency", "status": "passed"},
                {"field": "coupling_metric", "rule": "supported PAC V2 metric", "value": params["coupling_metric"], "status": "passed"},
            ],
        },
        table_dictionary=_table_dictionary(),
        scope_contract={
            "analysis_scope": "single_record_descriptive_sensor_space_pac_v2_beta",
            "stable_status": "beta_lab_only",
            "allowed_claims": [
                "Describe PAC V2 metric values for one uploaded recording in sensor/channel space.",
                "Compare configured exploratory coupling metrics for research method review.",
            ],
            "disallowed_claims": [
                "diagnosis_or_treatment_recommendation",
                "p_value_or_statistical_significance_claim",
                "group_or_population_inference",
                "causal_or_mechanistic_conclusion",
                "brain_region_communication_claim",
                "source_localization_or_brain_region_activation",
            ],
            "customer_boundary_note": PAC_V2_BOUNDARY,
        },
        source_metadata=_source_metadata(input_path, raw, eeg, recorded_params),
    )

    summary = {
        "module_id": "pac_cfc_v2",
        "workflow_id": "pac_v2_lab",
        "lifecycle_state": "beta_lab_only",
        "status": "completed",
        "coupling_metric": params["coupling_metric"],
        "channels": list(eeg.ch_names),
        "sfreq_hz": float(eeg.info["sfreq"]),
        "duration_sec": float(data.shape[1] / eeg.info["sfreq"]),
        "n_phase_bands": len(phase_bands),
        "n_amp_bands": len(amp_bands),
        "n_combinations": len(pac_rows),
        "peak_pac_value": max(float(row["pac_value"]) for row in pac_rows) if pac_rows else 0.0,
        "parameters_hash": params_hash,
        "elapsed_sec": round(elapsed_time, 3),
        "warnings": [
            "Lab-only output; not for customer delivery.",
            "Single-record descriptive PAC V2 output only.",
            "No p-value, significance, diagnosis, causality, or clinical conclusion is produced.",
        ],
        "boundary": PAC_V2_BOUNDARY,
    }

    outputs = {
        "pac_v2_long": pac_long_path,
        "pac_v2_channel_summary": summary_path,
        "parameters": parameters_path,
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
        job_type="pac_v2_lab",
        module_name="pac_v2",
        input_path=input_path,
        parameters=recorded_params,
        summary=summary,
        outputs=outputs,
        log_lines=log_lines,
    )

    return {
        "pac_v2_long": pac_long_path,
        "pac_v2_channel_summary": summary_path,
        "parameters": parameters_path,
        "method_description": method_path,
        **reproducibility_paths,
        **sidecars,
        **contracts,
    }


def _table_dictionary() -> dict[str, Any]:
    return {
        "tables/pac_v2_long.csv": {
            "description": "Long-form PAC V2 metric values by channel, phase band, and amplitude band.",
            "columns": {
                "channel": {"unit": "label", "description": "EEG channel name."},
                "phase_fmin": {"unit": "Hz", "description": "Lower edge of the phase-frequency band."},
                "phase_fmax": {"unit": "Hz", "description": "Upper edge of the phase-frequency band."},
                "amp_fmin": {"unit": "Hz", "description": "Lower edge of the amplitude-frequency band."},
                "amp_fmax": {"unit": "Hz", "description": "Upper edge of the amplitude-frequency band."},
                "coupling_metric": {"unit": "label", "description": "PAC V2 metric used for the row."},
                "pac_value": {"unit": "metric_value", "description": "Descriptive coupling value for the selected metric."},
                "n_surrogates": {"unit": "count", "description": "Number of surrogate samples configured."},
                "surrogate_mean": {"unit": "metric_value", "description": "Mean surrogate value when computed."},
                "surrogate_std": {"unit": "metric_value", "description": "Surrogate standard deviation when computed."},
                "normalized_z": {"unit": "z_score", "description": "Exploratory normalized score, not a formal significance claim."},
                "random_state": {"unit": "seed", "description": "Random seed for reproducible surrogate operations."},
                "n_samples": {"unit": "samples", "description": "Number of time samples used in the analysis window."},
            },
        },
        "tables/pac_v2_channel_summary.csv": {
            "description": "Per-channel summary of the peak PAC V2 metric value.",
            "columns": {
                "channel": {"unit": "label", "description": "EEG channel name."},
                "coupling_metric": {"unit": "label", "description": "PAC V2 metric summarized."},
                "peak_phase_band": {"unit": "Hz_range", "description": "Phase band with the highest descriptive PAC value."},
                "peak_amp_band": {"unit": "Hz_range", "description": "Amplitude band with the highest descriptive PAC value."},
                "peak_pac_value": {"unit": "metric_value", "description": "Peak descriptive PAC value for this channel."},
                "duration_sec": {"unit": "seconds", "description": "Duration of the analysis window."},
                "warnings": {"unit": "text", "description": "Lab-only interpretation boundary notes."},
            },
        },
    }


def _source_metadata(input_path: str | Path, raw, eeg, params: dict[str, Any]) -> dict[str, Any]:
    path = Path(input_path)
    return {
        "input_filename": path.name,
        "input_suffix": path.suffix.lower(),
        "sfreq_hz": float(raw.info["sfreq"]),
        "raw_n_times": int(raw.n_times),
        "raw_duration_sec": float(raw.n_times / raw.info["sfreq"]),
        "selected_channels": list(eeg.ch_names),
        "selected_channel_count": len(eeg.ch_names),
        "time_window": params.get("time_window"),
        "parameters_hash": params.get("parameters_hash"),
    }


def _validate_pac_v2_parameters(
    parameters: dict | None,
    *,
    channels: list[str],
    sfreq: float,
    duration_sec: float
) -> dict[str, Any]:
    """Validate and fill defaults for PAC V2 parameters."""
    source = parameters or {}
    params = {}
    
    # Channels
    selected = source.get("channels", [])
    if not selected:
        params["channels"] = channels[:min(2, len(channels))]
    else:
        params["channels"] = selected if isinstance(selected, list) else [selected]
    
    missing = [ch for ch in params["channels"] if ch not in channels]
    if missing:
        raise ValueError(f"PAC V2 channels not found: {', '.join(missing)}")
    
    # Frequency parameters
    params["phase_freqs"] = source.get("phase_freqs", [4.0, 6.0, 8.0])
    params["amp_freqs"] = source.get("amp_freqs", [30.0, 50.0, 70.0])
    params["phase_band_width"] = source.get("phase_band_width", 2.0)
    params["amp_band_width"] = source.get("amp_band_width", 20.0)
    params["n_phase_bins"] = source.get("n_phase_bins", 18)
    
    # Coupling metric
    params["coupling_metric"] = source.get("coupling_metric", "mi")
    if params["coupling_metric"] not in ["mi", "mvl", "kl_divergence"]:
        raise ValueError(f"Invalid coupling_metric: {params['coupling_metric']}")
    
    # Surrogate parameters
    params["n_surrogates"] = source.get("n_surrogates", 100)
    params["random_state"] = source.get("random_state", 20260703)
    
    # Time window
    window = source.get("time_window", {})
    start_sec = window.get("start_sec", 0.0)
    end_sec = window.get("end_sec", duration_sec)
    params["time_window"] = {"start_sec": start_sec, "end_sec": end_sec}
    
    # Validation checks
    nyquist = sfreq / 2.0
    if params["phase_band_width"] <= 0 or params["amp_band_width"] <= 0:
        raise ValueError("PAC V2 band widths must be positive")
    
    if not (6 <= params["n_phase_bins"] <= 72):
        raise ValueError("PAC V2 n_phase_bins must be between 6 and 72")
    
    if max(params["phase_freqs"]) >= min(params["amp_freqs"]):
        raise ValueError("PAC V2 phase frequencies must be lower than amplitude frequencies")
    
    if max(params["amp_freqs"]) + params["amp_band_width"] / 2.0 >= nyquist:
        raise ValueError(f"PAC V2 amplitude band must be below Nyquist ({nyquist:.1f} Hz)")
    
    lowest_phase = min(params["phase_freqs"]) - params["phase_band_width"] / 2.0
    if lowest_phase <= 0:
        raise ValueError("PAC V2 lowest phase band edge must be > 0 Hz")
    
    if (end_sec - start_sec) < 4.0 / lowest_phase:
        raise ValueError("PAC V2 analysis window is too short for the lowest phase frequency")
    
    if params["n_surrogates"] < 0:
        raise ValueError("PAC V2 n_surrogates must be non-negative")
    
    return params


def _compute_pac_v2(
    data: np.ndarray,
    channels: list[str],
    sfreq: float,
    phase_bands: list[tuple[float, float]],
    amp_bands: list[tuple[float, float]],
    params: dict[str, Any],
    log_lines: list[str]
) -> list[dict[str, Any]]:
    """Compute PAC values for all channel/band combinations."""
    rows = []
    metric = params["coupling_metric"]
    
    for ch_index, channel in enumerate(channels):
        signal = data[ch_index]
        
        for phase_band in phase_bands:
            phase = _extract_phase(signal, sfreq, phase_band)
            
            for amp_band in amp_bands:
                amp = _extract_amplitude_envelope(signal, sfreq, amp_band)
                
                # Compute coupling metric
                if metric == "mi":
                    pac_value = _compute_modulation_index(phase, amp, params["n_phase_bins"])
                elif metric == "mvl":
                    pac_value = _compute_mean_vector_length(phase, amp)
                elif metric == "kl_divergence":
                    pac_value = _compute_kl_divergence(phase, amp, params["n_phase_bins"])
                else:
                    raise ValueError(f"Unknown metric: {metric}")
                
                # Compute surrogates if requested
                if params["n_surrogates"] > 0:
                    surrogate_stats = _compute_surrogate_stats(
                        phase, amp, metric, params["n_phase_bins"],
                        params["n_surrogates"],
                        int(params["random_state"]) + ch_index * 1009 + len(rows)
                    )
                    surrogate_mean = surrogate_stats["mean"]
                    surrogate_std = surrogate_stats["std"]
                    normalized_z = (pac_value - surrogate_mean) / surrogate_std if surrogate_std > 0 else 0.0
                else:
                    surrogate_mean = 0.0
                    surrogate_std = 0.0
                    normalized_z = 0.0
                
                rows.append({
                    "channel": channel,
                    "phase_fmin": phase_band[0],
                    "phase_fmax": phase_band[1],
                    "amp_fmin": amp_band[0],
                    "amp_fmax": amp_band[1],
                    "coupling_metric": metric,
                    "pac_value": round(pac_value, 8),
                    "n_surrogates": params["n_surrogates"],
                    "surrogate_mean": round(surrogate_mean, 8),
                    "surrogate_std": round(surrogate_std, 8),
                    "normalized_z": round(normalized_z, 8),
                    "random_state": params["random_state"],
                    "n_samples": int(signal.size),
                })
    
    return rows


def _extract_phase(signal: np.ndarray, sfreq: float, band: tuple[float, float]) -> np.ndarray:
    """Extract instantaneous phase for a frequency band."""
    filtered = mne.filter.filter_data(
        signal.astype(float), sfreq=sfreq, l_freq=band[0], h_freq=band[1], verbose=False
    )
    analytic_signal = hilbert(filtered)
    return np.angle(analytic_signal)


def _extract_amplitude_envelope(signal: np.ndarray, sfreq: float, band: tuple[float, float]) -> np.ndarray:
    """Extract amplitude envelope for a frequency band."""
    filtered = mne.filter.filter_data(
        signal.astype(float), sfreq=sfreq, l_freq=band[0], h_freq=band[1], verbose=False
    )
    analytic_signal = hilbert(filtered)
    return np.abs(analytic_signal)


def _compute_modulation_index(phase: np.ndarray, amp: np.ndarray, n_bins: int) -> float:
    """Compute Tort-style modulation index (normalized KL divergence)."""
    edges = np.linspace(-math.pi, math.pi, n_bins + 1)
    means = []
    
    for i in range(n_bins):
        if i < n_bins - 1:
            mask = (phase >= edges[i]) & (phase < edges[i + 1])
        else:
            mask = (phase >= edges[i]) & (phase <= edges[i + 1])
        
        mean_amp = float(np.mean(amp[mask])) if np.any(mask) else 0.0
        means.append(mean_amp)
    
    means_arr = np.asarray(means, dtype=float)
    total = means_arr.sum()
    
    if total <= 0:
        return 0.0
    
    probs = means_arr / total
    entropy = -float(np.sum([p * math.log(p) for p in probs if p > 0]))
    mi = (math.log(n_bins) - entropy) / math.log(n_bins)
    
    return max(0.0, float(mi))


def _compute_mean_vector_length(phase: np.ndarray, amp: np.ndarray) -> float:
    """Compute mean vector length (amplitude-weighted phase consistency)."""
    if amp.size == 0:
        return 0.0
    
    # Amplitude-weighted complex exponential
    weighted_vectors = amp * np.exp(1j * phase)
    mean_vector = np.mean(weighted_vectors)
    mvl = np.abs(mean_vector)
    
    return float(mvl)


def _compute_kl_divergence(phase: np.ndarray, amp: np.ndarray, n_bins: int) -> float:
    """Compute raw KL divergence (not normalized)."""
    edges = np.linspace(-math.pi, math.pi, n_bins + 1)
    means = []
    
    for i in range(n_bins):
        if i < n_bins - 1:
            mask = (phase >= edges[i]) & (phase < edges[i + 1])
        else:
            mask = (phase >= edges[i]) & (phase <= edges[i + 1])
        
        mean_amp = float(np.mean(amp[mask])) if np.any(mask) else 0.0
        means.append(mean_amp)
    
    means_arr = np.asarray(means, dtype=float)
    total = means_arr.sum()
    
    if total <= 0:
        return 0.0
    
    probs = means_arr / total
    uniform = 1.0 / n_bins
    
    # KL divergence: sum(p * log(p / uniform))
    kl = sum([p * math.log(p / uniform) for p in probs if p > 0])
    
    return max(0.0, float(kl))


def _compute_surrogate_stats(
    phase: np.ndarray,
    amp: np.ndarray,
    metric: str,
    n_bins: int,
    n_surrogates: int,
    seed: int
) -> dict[str, float]:
    """Compute surrogate distribution statistics."""
    if amp.size < 4 or n_surrogates < 1:
        return {"mean": 0.0, "std": 0.0}
    
    rng = np.random.default_rng(seed)
    values = []
    
    low = max(1, int(0.1 * amp.size))
    high = max(low + 1, int(0.9 * amp.size))
    
    for _ in range(n_surrogates):
        shift = int(rng.integers(low, high))
        shifted_amp = np.roll(amp, shift)
        
        if metric == "mi":
            surrogate_value = _compute_modulation_index(phase, shifted_amp, n_bins)
        elif metric == "mvl":
            surrogate_value = _compute_mean_vector_length(phase, shifted_amp)
        elif metric == "kl_divergence":
            surrogate_value = _compute_kl_divergence(phase, shifted_amp, n_bins)
        else:
            surrogate_value = 0.0
        
        values.append(surrogate_value)
    
    values_arr = np.asarray(values, dtype=float)
    
    return {
        "mean": float(np.mean(values_arr)),
        "std": float(np.std(values_arr, ddof=1)) if values_arr.size > 1 else 0.0,
    }


def _compute_channel_summary(
    pac_rows: list[dict[str, Any]],
    channels: list[str],
    sfreq: float,
) -> list[dict[str, Any]]:
    """Compute channel-level summary statistics."""
    by_channel = {}
    for row in pac_rows:
        ch = row["channel"]
        if ch not in by_channel:
            by_channel[ch] = []
        by_channel[ch].append(row)

    summary = []
    for channel in channels:
        if channel not in by_channel:
            continue

        channel_rows = by_channel[channel]
        peak = max(channel_rows, key=lambda r: float(r["pac_value"]))

        duration_sec = peak["n_samples"] / sfreq if sfreq > 0 else 0.0

        summary.append({
            "channel": channel,
            "coupling_metric": peak["coupling_metric"],
            "peak_phase_band": f"{peak['phase_fmin']}-{peak['phase_fmax']} Hz",
            "peak_amp_band": f"{peak['amp_fmin']}-{peak['amp_fmax']} Hz",
            "peak_pac_value": peak["pac_value"],
            "duration_sec": round(duration_sec, 6),
            "warnings": "lab-only; single-record descriptive; no statistical inference",
        })

    return summary


def _bands_from_centers(centers: list[float], width: float) -> list[tuple[float, float]]:
    """Convert frequency centers and width to band tuples."""
    return [(round(center - width / 2.0, 6), round(center + width / 2.0, 6)) for center in centers]


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    """Write rows to CSV file."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
