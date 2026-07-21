"""Phase-amplitude and n:m cross-phase coupling on complete EEG recordings."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import hilbert


@dataclass(frozen=True)
class CouplingConfig:
    pac_phase_band_hz: tuple[float, float] = (4.0, 8.0)
    pac_amplitude_band_hz: tuple[float, float] = (13.0, 30.0)
    cpc_low_band_hz: tuple[float, float] = (4.0, 8.0)
    cpc_high_band_hz: tuple[float, float] = (8.0, 13.0)
    cpc_low_phase_multiplier: int = 2
    cpc_high_phase_multiplier: int = 1
    phase_bins: int = 18


def compute_coupling(raw, config: CouplingConfig | None = None) -> dict:
    """Compute Tort MI, mean vector length and n:m PLV for each scalp channel."""
    config = config or CouplingConfig()
    eeg = raw.copy().pick("eeg")
    data = eeg.get_data() * 1e6
    phase = _analytic(data, eeg.info["sfreq"], *config.pac_phase_band_hz)
    amplitude = np.abs(_analytic(data, eeg.info["sfreq"], *config.pac_amplitude_band_hz))
    low = np.angle(_analytic(data, eeg.info["sfreq"], *config.cpc_low_band_hz))
    high = np.angle(_analytic(data, eeg.info["sfreq"], *config.cpc_high_band_hz))
    pac = []
    cpc = []
    for index, channel in enumerate(eeg.ch_names):
        phase_angles = np.angle(phase[index])
        pac.append(
            {
                "channel": channel,
                "coupling": "theta_beta_pac",
                "phase_band_hz": list(config.pac_phase_band_hz),
                "amplitude_band_hz": list(config.pac_amplitude_band_hz),
                "modulation_index": _tort_mi(phase_angles, amplitude[index], config.phase_bins),
                "mean_vector_length": float(abs(np.mean(amplitude[index] * np.exp(1j * phase_angles)))),
                "phase_amplitude_binned_curve": _phase_amplitude_curve(phase_angles, amplitude[index], config.phase_bins),
                "analyzed_samples": int(data.shape[1]),
                "analyzed_duration_sec": float(data.shape[1] / eeg.info["sfreq"]),
            }
        )
        cpc.append({"channel": channel, "coupling": "theta_alpha_1_2", "low_phase_band_hz": list(config.cpc_low_band_hz), "high_phase_band_hz": list(config.cpc_high_band_hz), "low_phase_multiplier": config.cpc_low_phase_multiplier, "high_phase_multiplier": config.cpc_high_phase_multiplier, "n_m_phase_locking_value": float(abs(np.mean(np.exp(1j * (config.cpc_low_phase_multiplier * low[index] - config.cpc_high_phase_multiplier * high[index]))))), "analyzed_samples": int(data.shape[1]), "analyzed_duration_sec": float(data.shape[1] / eeg.info["sfreq"])})
    return {"scope": "full_recording", "pac": pac, "cross_phase_coupling": cpc, "boundary": "Sensor-space descriptive coupling only; use artifact-aware interpretation and do not infer causality."}


def _analytic(data, sfreq, low, high):
    from mne.filter import filter_data
    return hilbert(filter_data(data, sfreq, low, high, verbose="ERROR"), axis=-1)


def _tort_mi(phase, amplitude, bins):
    edges = np.linspace(-np.pi, np.pi, bins + 1)
    means = np.array([amplitude[(phase >= edges[index]) & (phase < edges[index + 1])].mean() if np.any((phase >= edges[index]) & (phase < edges[index + 1])) else 0.0 for index in range(bins)])
    probability = means / max(means.sum(), np.finfo(float).eps)
    entropy = -np.sum(np.where(probability > 0, probability * np.log(probability), 0.0))
    return float((np.log(bins) - entropy) / np.log(bins))


def _phase_amplitude_curve(phase: np.ndarray, amplitude: np.ndarray, bins: int) -> dict:
    """Preserve the phase-binned amplitude curve used by the Tort MI calculation."""
    edges = np.linspace(-np.pi, np.pi, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    mean_amplitude = []
    sample_count = []
    for index in range(bins):
        mask = (phase >= edges[index]) & (phase < edges[index + 1])
        mean_amplitude.append(float(amplitude[mask].mean()) if np.any(mask) else None)
        sample_count.append(int(mask.sum()))
    values = np.asarray([value if value is not None else 0.0 for value in mean_amplitude], dtype=float)
    distribution = values / max(values.sum(), np.finfo(float).eps)
    return {
        "phase_bin_edges_radians": edges.tolist(),
        "phase_bin_centers_radians": centers.tolist(),
        "phase_bin_centers_degrees": np.rad2deg(centers).tolist(),
        "mean_amplitude_uv": mean_amplitude,
        "normalized_amplitude_distribution": distribution.tolist(),
        "sample_count": sample_count,
    }
