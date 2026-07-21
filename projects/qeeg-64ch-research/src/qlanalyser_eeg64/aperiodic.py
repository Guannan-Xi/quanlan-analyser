"""Aperiodic/periodic spectrum parameterization using optional Specparam."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AperiodicConfig:
    low_hz: float = 2.0
    high_hz: float = 45.0
    peak_width_limits_hz: tuple[float, float] = (1.0, 12.0)


def compute_aperiodic_spectrum(raw, config: AperiodicConfig | None = None) -> dict:
    """Fit 1/f offset, exponent and oscillatory peaks on whole-record PSD.

    Requires the explicit `aperiodic` optional dependency because this project
    must not silently replace Specparam's fitting model with another algorithm.
    """
    config = config or AperiodicConfig()
    try:
        from specparam import SpectralModel
    except ImportError as exc:
        raise RuntimeError("Specparam is required. Install qlanalyser-eeg64-recovery[aperiodic].") from exc
    eeg = raw.copy().pick("eeg")
    spectrum = eeg.compute_psd(method="welch", fmin=config.low_hz, fmax=config.high_hz, verbose="ERROR")
    psd, freqs = spectrum.get_data(return_freqs=True)
    mean_psd = psd.mean(axis=0) * 1e12
    model = SpectralModel(peak_width_limits=config.peak_width_limits_hz, verbose=False)
    model.fit(freqs, mean_psd, [config.low_hz, config.high_hz])
    aperiodic = np.asarray(model.get_params("aperiodic"), dtype=float)
    peaks = np.atleast_2d(np.asarray(model.get_params("peak"), dtype=float))
    peaks = peaks[np.isfinite(peaks).all(axis=1)]
    return {"scope": "full_recording_global_mean_psd", "frequency_range_hz": [config.low_hz, config.high_hz], "aperiodic_offset_log10_uv2_per_hz": float(aperiodic[0]), "aperiodic_exponent": float(aperiodic[-1]), "fit_r_squared": float(model.results.metrics.get_metrics("gof", "rsquared")), "fit_mae_log10_power": float(model.results.metrics.get_metrics("error", "mae")), "peaks": [{"center_frequency_hz": float(row[0]), "power_above_aperiodic": float(row[1]), "bandwidth_hz": float(row[2])} for row in peaks]}
