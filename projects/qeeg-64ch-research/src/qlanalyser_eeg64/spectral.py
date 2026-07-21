"""Full-recording spectral measures retained from the 64-channel report.

The public result returned by :func:`compute_spectral_features` intentionally
contains plain Python values only.  It is therefore suitable for direct JSON
serialization and for reuse by both HTML and future service-layer renderers.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from scipy.signal import butter, find_peaks, hilbert, peak_widths, sosfiltfilt, welch
from scipy.stats import kurtosis, skew


EPSILON = np.finfo(float).eps
POSTERIOR_ALPHA_CHANNELS = {
    "left": ("P7", "P3", "PO7", "PO3", "O1"),
    "right": ("P8", "P4", "PO8", "PO4", "O2"),
}
PEAK_BANDS = (
    ("delta", 0.5, 4.0),
    ("theta", 4.0, 8.0),
    ("alpha", 8.0, 13.0),
    ("beta1", 13.0, 20.0),
    ("beta2", 20.0, 30.0),
    ("gamma", 30.0, 40.0),
)
POWER_RATIO_DEFINITIONS = (
    ("theta/alpha", "theta", 4.0, 8.0, "alpha", 8.0, 13.0),
    ("theta/beta", "theta", 4.0, 8.0, "beta", 13.0, 30.0),
    ("theta/high_beta", "theta", 4.0, 8.0, "high_beta", 20.0, 30.0),
    ("alpha/beta", "alpha", 8.0, 13.0, "beta", 13.0, 30.0),
    ("alpha/high_beta", "alpha", 8.0, 13.0, "high_beta", 20.0, 30.0),
    ("beta/high_beta", "beta", 13.0, 30.0, "high_beta", 20.0, 30.0),
    ("high_theta/low_alpha", "high_theta", 6.0, 8.0, "low_alpha", 8.0, 10.0),
    ("low_alpha/high_alpha", "low_alpha", 8.0, 10.0, "high_alpha", 10.0, 13.0),
    ("delta/theta", "delta", 1.0, 4.0, "theta", 4.0, 8.0),
    ("delta/alpha", "delta", 1.0, 4.0, "alpha", 8.0, 13.0),
    ("delta/beta", "delta", 1.0, 4.0, "beta", 13.0, 30.0),
    ("delta/high_beta", "delta", 1.0, 4.0, "high_beta", 20.0, 30.0),
)


@dataclass(frozen=True)
class SpectralConfig:
    bands: tuple[tuple[str, float, float], ...] = (
        ("delta", 1.0, 4.0),
        ("theta", 4.0, 8.0),
        ("alpha", 8.0, 13.0),
        ("beta", 13.0, 30.0),
        ("gamma", 30.0, 45.0),
    )
    psd_low_hz: float = 0.5
    psd_high_hz: float = 45.0
    welch_window_sec: float = 4.0
    alpha_envelope_low_hz: float = 8.0
    alpha_envelope_high_hz: float = 13.0
    peak_min_prominence_log10: float = 0.05
    alpha_dispersion_low_hz: float = 7.0
    alpha_dispersion_high_hz: float = 13.0
    alpha_dispersion_peak_half_width_hz: float = 0.5
    alpha_dispersion_window_sec: float = 4.0


def compute_spectral_features(raw, config: SpectralConfig | None = None) -> dict:
    """Compute historical-report-compatible measures from the full input raw.

    The caller owns preprocessing and epoch exclusion.  Consequently this
    function never selects a display segment: every returned feature uses all
    samples present in ``raw``.
    """
    config = config or SpectralConfig()
    eeg = raw.copy().pick("eeg")
    n_fft = min(eeg.n_times, max(8, round(config.welch_window_sec * eeg.info["sfreq"])))
    spectrum = eeg.compute_psd(
        method="welch",
        fmin=config.psd_low_hz,
        fmax=config.psd_high_hz,
        n_fft=n_fft,
        verbose="ERROR",
    )
    psd, freqs = spectrum.get_data(return_freqs=True)
    psd_uv2 = psd * 1e12
    channels = eeg.ch_names

    broad_band_rows = _band_power_rows(psd_uv2, freqs, channels, config.bands)
    broad_band_by_name = {row["band"]: row for row in broad_band_rows}
    narrowband_rows = _band_power_rows(psd_uv2, freqs, channels, _narrowband_definitions())
    alpha_envelopes = _alpha_envelopes(eeg, config)
    beta_envelopes = _beta_envelopes(eeg)
    posterior_alpha = _posterior_alpha(psd_uv2, freqs, channels, alpha_envelopes)
    channel_statistics = _channel_spectral_statistics(psd_uv2, freqs, channels)
    band_peaks = _band_peaks(psd_uv2, freqs, channels, config.peak_min_prominence_log10)
    alpha_dispersion = compute_alpha_spectral_dispersion(
        eeg,
        config,
        full_recording_psd_uv2=psd_uv2,
        full_recording_freqs_hz=freqs,
        include_windowed_spectra=False,
    )

    return {
        "scope": "full_recording",
        "config": asdict(config),
        "frequencies_hz": freqs.tolist(),
        "psd_uv2_per_hz": {channel: row.tolist() for channel, row in zip(channels, psd_uv2)},
        "absolute_band_power": broad_band_rows,
        "narrowband_power": {
            "definition": "successive 2 Hz bands from 2 to 34 Hz",
            "bands": narrowband_rows,
        },
        "power_ratios": _power_ratios(psd_uv2, freqs, channels),
        "channel_spectral_statistics": channel_statistics,
        "posterior_alpha": posterior_alpha,
        "alpha_spectral_dispersion": alpha_dispersion,
        "beta_envelopes": beta_envelopes,
        "band_peak_parameters": band_peaks,
        "markers": {
            "paf_hz": _paf(psd_uv2, freqs, channels),
            "tbr": _tbr(broad_band_rows),
            "faa_ln_f4_minus_ln_f3": _faa(broad_band_rows),
            "alpha_centroid_hz_by_channel": {
                channel: values["alpha_centroid_hz"] for channel, values in channel_statistics.items()
            },
            "spectral_entropy_by_channel": {
                channel: values["spectral_entropy"] for channel, values in channel_statistics.items()
            },
        },
    }


def compute_alpha_spectral_dispersion(
    raw,
    config: SpectralConfig | None = None,
    *,
    full_recording_psd_uv2: np.ndarray | None = None,
    full_recording_freqs_hz: np.ndarray | None = None,
    include_windowed_spectra: bool = True,
) -> dict:
    """Compute the historical 7--13 Hz Alpha spectral-dispersion measures.

    ``CD-alpha1`` is the modal PSD-bin power divided by the summed Alpha-bin
    power. ``CD-alpha2`` uses the sum of bins within the modal frequency plus
    or minus 0.5 Hz as its numerator.  Both are ratios, not integrated power.

    The windowed distribution is formed from complete, non-overlapping four
    second windows of the *supplied* QC-retained raw.  The present QC contract
    can concatenate retained epochs, so this function deliberately does not
    claim to recreate unavailable rejected-time gap boundaries.
    """
    config = config or SpectralConfig()
    eeg = raw.copy().pick("eeg")
    channels = list(eeg.ch_names)
    sfreq = float(eeg.info["sfreq"])
    if sfreq <= 0:
        raise ValueError("EEG sampling frequency must be positive")

    if (full_recording_psd_uv2 is None) != (full_recording_freqs_hz is None):
        raise ValueError("Full-recording PSD and frequency bins must be supplied together")
    if full_recording_psd_uv2 is None:
        full_psd_uv2, full_freqs_hz = _welch_psd_uv2(
            eeg.get_data(),
            sfreq,
            config.welch_window_sec,
            config.alpha_dispersion_low_hz,
            config.alpha_dispersion_high_hz,
        )
    else:
        full_psd_uv2 = np.asarray(full_recording_psd_uv2, dtype=float)
        full_freqs_hz = np.asarray(full_recording_freqs_hz, dtype=float)
        if full_psd_uv2.ndim != 2 or full_psd_uv2.shape[0] != len(channels):
            raise ValueError("Full-recording PSD must have one row for every EEG channel")
        if full_psd_uv2.shape[1] != full_freqs_hz.size:
            raise ValueError("Full-recording PSD columns must match the supplied frequency bins")

    channel_rows = _alpha_dispersion_rows(
        full_psd_uv2,
        full_freqs_hz,
        channels,
        config,
    )
    frequency_step_hz = _frequency_step(full_freqs_hz)
    windowed_distribution = _windowed_alpha_dispersion(
        eeg,
        config,
        include_windowed_spectra=include_windowed_spectra,
    )
    result_status = "calculated" if any(row["cd_alpha1"] is not None for row in channel_rows) else "insufficient_data"
    return {
        "scope": "complete_qc_retained_recording",
        "status": result_status,
        "definitions": {
            "alpha_band_hz": [float(config.alpha_dispersion_low_hz), float(config.alpha_dispersion_high_hz)],
            "cd_alpha1": "modal PSD-bin power divided by summed 7-13 Hz PSD-bin power",
            "cd_alpha2": "summed PSD-bin power within modal frequency +/-0.5 Hz divided by summed 7-13 Hz PSD-bin power",
            "cd_units": "ratio",
            "modal_frequency_unit": "Hz",
            "skewness_unit": "dimensionless",
            "excess_kurtosis_unit": "dimensionless",
        },
        "frequency_step_hz": frequency_step_hz,
        "channels": channel_rows,
        "summary": _alpha_dispersion_summary(channel_rows, config, frequency_step_hz),
        "windowed_distribution": windowed_distribution,
    }


def write_alpha_spectral_dispersion_csv(result: dict, output_dir: str | Path) -> dict[str, Path]:
    """Write stable CSV exports for the Alpha spectral-dispersion result.

    To export the normalized window spectra, call
    :func:`compute_alpha_spectral_dispersion` with
    ``include_windowed_spectra=True`` (the public default).  Results embedded
    in ``compute_spectral_features`` omit those high-volume rows intentionally.
    """
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    windowed = result.get("windowed_distribution", {})
    paths = {
        "channel_features": destination / "alpha_spectral_dispersion.csv",
        "window_features": destination / "alpha_spectral_dispersion_windows.csv",
        "normalized_spectra": destination / "alpha_spectral_dispersion_spectra.csv",
    }
    _write_csv(paths["channel_features"], _ALPHA_CHANNEL_FIELDS, result.get("channels", []))
    _write_csv(paths["window_features"], _ALPHA_WINDOW_FIELDS, windowed.get("feature_rows", []))
    _write_csv(paths["normalized_spectra"], _ALPHA_SPECTRUM_FIELDS, windowed.get("normalized_spectrum_rows", []))
    return paths


_ALPHA_CHANNEL_FIELDS = (
    "channel",
    "modal_frequency_hz",
    "cd_alpha1",
    "cd_alpha2",
    "alpha_spectral_skewness",
    "alpha_spectral_excess_kurtosis",
    "alpha_low_hz",
    "alpha_high_hz",
    "frequency_step_hz",
)
_ALPHA_WINDOW_FIELDS = (
    "continuous_segment_index",
    "window_index_within_segment",
    "window_index",
    "segment_offset_start_sec",
    "source_start_sec",
    "source_end_sec",
    "window_duration_sec",
    "channel",
    "hemisphere",
    "modal_frequency_hz",
    "cd_alpha1",
    "cd_alpha2",
    "alpha_spectral_skewness",
    "alpha_spectral_excess_kurtosis",
    "alpha_low_hz",
    "alpha_high_hz",
    "frequency_step_hz",
)
_ALPHA_SPECTRUM_FIELDS = (
    "continuous_segment_index",
    "window_index_within_segment",
    "window_index",
    "source_start_sec",
    "source_end_sec",
    "channel",
    "frequency_hz",
    "alpha_power_fraction_per_bin",
)


def _welch_psd_uv2(data, sfreq, window_sec, fmin, fmax):
    """Return a Welch PSD in uV^2/Hz with a four-second frequency resolution."""
    window_samples = max(1, int(round(window_sec * sfreq)))
    nperseg = min(window_samples, data.shape[1])
    if nperseg < 2:
        return np.zeros((data.shape[0], 0), dtype=float), np.empty(0, dtype=float)
    frequencies, psd = welch(
        data,
        fs=sfreq,
        nperseg=nperseg,
        nfft=window_samples,
        noverlap=0,
        axis=-1,
        detrend="constant",
        scaling="density",
    )
    band_mask = (frequencies >= fmin) & (frequencies <= fmax)
    return psd[:, band_mask] * 1e12, frequencies[band_mask]


def _alpha_dispersion_rows(psd_uv2, freqs_hz, channels, config):
    mask = (freqs_hz >= config.alpha_dispersion_low_hz) & (freqs_hz <= config.alpha_dispersion_high_hz)
    alpha_freqs_hz = freqs_hz[mask]
    alpha_psd_uv2 = psd_uv2[:, mask] if psd_uv2.ndim == 2 else np.empty((len(channels), 0), dtype=float)
    frequency_step_hz = _frequency_step(alpha_freqs_hz)
    return [
        _alpha_dispersion_row(channel, alpha_freqs_hz, alpha_psd_uv2[index], config, frequency_step_hz)
        for index, channel in enumerate(channels)
    ]


def _alpha_dispersion_row(channel, alpha_freqs_hz, alpha_psd_uv2, config, frequency_step_hz):
    base = {
        "channel": channel,
        "modal_frequency_hz": None,
        "cd_alpha1": None,
        "cd_alpha2": None,
        "alpha_spectral_skewness": None,
        "alpha_spectral_excess_kurtosis": None,
        "alpha_low_hz": float(config.alpha_dispersion_low_hz),
        "alpha_high_hz": float(config.alpha_dispersion_high_hz),
        "frequency_step_hz": frequency_step_hz,
    }
    if alpha_freqs_hz.size == 0 or alpha_psd_uv2.size == 0:
        return base
    finite_power = np.where(np.isfinite(alpha_psd_uv2), np.maximum(alpha_psd_uv2, 0.0), 0.0)
    total_power = float(np.sum(finite_power))
    if total_power <= EPSILON:
        return base
    modal_index = int(np.argmax(finite_power))
    modal_frequency_hz = float(alpha_freqs_hz[modal_index])
    local_mask = np.abs(alpha_freqs_hz - modal_frequency_hz) <= config.alpha_dispersion_peak_half_width_hz + EPSILON
    normalized = finite_power / total_power
    has_distribution_shape = finite_power.size >= 4 and np.ptp(finite_power) > EPSILON
    return {
        **base,
        "modal_frequency_hz": modal_frequency_hz,
        "cd_alpha1": float(normalized[modal_index]),
        "cd_alpha2": float(np.sum(normalized[local_mask])),
        "alpha_spectral_skewness": _finite_statistic(skew(finite_power, bias=True)) if has_distribution_shape else None,
        "alpha_spectral_excess_kurtosis": _finite_statistic(kurtosis(finite_power, fisher=True, bias=True)) if has_distribution_shape else None,
    }


def _windowed_alpha_dispersion(eeg, config, *, include_windowed_spectra):
    sfreq = float(eeg.info["sfreq"])
    window_samples = int(round(config.alpha_dispersion_window_sec * sfreq))
    input_duration_sec = float(eeg.n_times / sfreq)
    if window_samples < 2:
        raise ValueError("Alpha dispersion window must contain at least two samples")
    complete_window_count = eeg.n_times // window_samples
    metadata = {
        "status": "calculated" if complete_window_count else "insufficient_data",
        "band_hz": [float(config.alpha_dispersion_low_hz), float(config.alpha_dispersion_high_hz)],
        "continuous_segment_count": 1 if eeg.n_times else 0,
        "eligible_continuous_segment_count": 1 if complete_window_count else 0,
        "complete_window_count": int(complete_window_count),
        "window_duration_sec": float(config.alpha_dispersion_window_sec),
        "window_step_sec": float(config.alpha_dispersion_window_sec),
        "analyzed_duration_sec": float(complete_window_count * window_samples / sfreq),
        "input_duration_sec": input_duration_sec,
        "discarded_tail_duration_sec": float((eeg.n_times % window_samples) / sfreq),
        "welch_window_sec": float(config.alpha_dispersion_window_sec),
        "welch_overlap_ratio": 0.0,
        "time_base": "supplied_qc_retained_recording",
        "continuity_rule": "complete non-overlapping windows of the supplied QC-retained continuous record",
        "feature_rows": [],
    }
    if include_windowed_spectra:
        metadata["normalized_spectrum_rows"] = []
    if complete_window_count == 0:
        return metadata

    data = eeg.get_data()
    channels = list(eeg.ch_names)
    for window_index in range(complete_window_count):
        start_sample = window_index * window_samples
        stop_sample = start_sample + window_samples
        psd_uv2, freqs_hz = _welch_psd_uv2(
            data[:, start_sample:stop_sample],
            sfreq,
            config.alpha_dispersion_window_sec,
            config.alpha_dispersion_low_hz,
            config.alpha_dispersion_high_hz,
        )
        feature_rows = _alpha_dispersion_rows(psd_uv2, freqs_hz, channels, config)
        window_start_sec = float(start_sample / sfreq)
        window_end_sec = float(stop_sample / sfreq)
        for channel_index, feature_row in enumerate(feature_rows):
            metadata["feature_rows"].append(
                {
                    "continuous_segment_index": 0,
                    "window_index_within_segment": window_index,
                    "window_index": window_index,
                    "segment_offset_start_sec": window_start_sec,
                    "source_start_sec": window_start_sec,
                    "source_end_sec": window_end_sec,
                    "window_duration_sec": float(config.alpha_dispersion_window_sec),
                    "hemisphere": _hemisphere(feature_row["channel"]),
                    **feature_row,
                }
            )
            if include_windowed_spectra:
                alpha_power = np.where(np.isfinite(psd_uv2[channel_index]), np.maximum(psd_uv2[channel_index], 0.0), 0.0)
                total_alpha_power = float(np.sum(alpha_power))
                fractions = alpha_power / total_alpha_power if total_alpha_power > EPSILON else np.zeros_like(alpha_power)
                metadata["normalized_spectrum_rows"].extend(
                    {
                        "continuous_segment_index": 0,
                        "window_index_within_segment": window_index,
                        "window_index": window_index,
                        "source_start_sec": window_start_sec,
                        "source_end_sec": window_end_sec,
                        "channel": feature_row["channel"],
                        "frequency_hz": float(frequency),
                        "alpha_power_fraction_per_bin": float(fraction),
                    }
                    for frequency, fraction in zip(freqs_hz, fractions)
                )
    return metadata


def _alpha_dispersion_summary(channel_rows, config, frequency_step_hz):
    by_channel = {row["channel"]: row for row in channel_rows}
    left_rows = [row for row in channel_rows if _hemisphere(row["channel"]) == "left" and row["modal_frequency_hz"] is not None]
    right_rows = [row for row in channel_rows if _hemisphere(row["channel"]) == "right" and row["modal_frequency_hz"] is not None]
    return {
        "cd_alpha1_o1": _channel_field(by_channel, "O1", "cd_alpha1"),
        "cd_alpha1_o2": _channel_field(by_channel, "O2", "cd_alpha1"),
        "cd_alpha1_max_left_hemisphere": _maximum_field(left_rows, "cd_alpha1"),
        "cd_alpha1_max_right_hemisphere": _maximum_field(right_rows, "cd_alpha1"),
        "cd_alpha2_f3": _channel_field(by_channel, "F3", "cd_alpha2"),
        "cd_alpha2_f4": _channel_field(by_channel, "F4", "cd_alpha2"),
        "cd_alpha2_o1": _channel_field(by_channel, "O1", "cd_alpha2"),
        "cd_alpha2_o2": _channel_field(by_channel, "O2", "cd_alpha2"),
        "modal_frequency_o1_hz": _channel_field(by_channel, "O1", "modal_frequency_hz"),
        "modal_frequency_o2_hz": _channel_field(by_channel, "O2", "modal_frequency_hz"),
        "modal_frequency_left_hemisphere_hz": _mean_field(left_rows, "modal_frequency_hz"),
        "modal_frequency_right_hemisphere_hz": _mean_field(right_rows, "modal_frequency_hz"),
        "occipital_frontal_delta_left_hz": _paired_delta(by_channel, "O1", "F3"),
        "occipital_frontal_delta_right_hz": _paired_delta(by_channel, "O2", "F4"),
        "alpha_low_hz": float(config.alpha_dispersion_low_hz),
        "alpha_high_hz": float(config.alpha_dispersion_high_hz),
        "frequency_step_hz": frequency_step_hz,
    }


def _frequency_step(freqs_hz):
    return float(np.median(np.diff(freqs_hz))) if freqs_hz.size > 1 else None


def _finite_statistic(value):
    value = float(value)
    return value if np.isfinite(value) else None


def _channel_field(by_channel, channel, field):
    value = by_channel.get(channel, {}).get(field)
    return float(value) if value is not None else None


def _maximum_field(rows, field):
    values = [row[field] for row in rows if row[field] is not None]
    return float(max(values)) if values else None


def _mean_field(rows, field):
    values = [row[field] for row in rows if row[field] is not None]
    return float(np.mean(values)) if values else None


def _paired_delta(by_channel, occipital_channel, frontal_channel):
    occipital = _channel_field(by_channel, occipital_channel, "modal_frequency_hz")
    frontal = _channel_field(by_channel, frontal_channel, "modal_frequency_hz")
    return float(occipital - frontal) if occipital is not None and frontal is not None else None


def _write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _band_power_rows(psd_uv2, freqs, channels, definitions):
    reference_mask = (freqs >= 1.0) & (freqs <= 45.0)
    relative_reference = np.trapezoid(psd_uv2[:, reference_mask], freqs[reference_mask], axis=1)
    rows = []
    for name, low, high in definitions:
        power = _integrated_power(psd_uv2, freqs, low, high)
        rows.append(
            {
                "band": name,
                "low_hz": float(low),
                "high_hz": float(high),
                "absolute_power_uv2": _channel_values(channels, power),
                "relative_power": _channel_values(channels, power / np.maximum(relative_reference, EPSILON)),
            }
        )
    return rows


def _narrowband_definitions():
    return tuple((f"{low}-{low + 2} Hz", float(low), float(low + 2)) for low in range(2, 34, 2))


def _integrated_power(psd_uv2, freqs, low_hz, high_hz):
    mask = (freqs >= low_hz) & (freqs <= high_hz)
    if np.count_nonzero(mask) < 2:
        return np.zeros(psd_uv2.shape[0], dtype=float)
    return np.trapezoid(psd_uv2[:, mask], freqs[mask], axis=1)


def _power_ratios(psd_uv2, freqs, channels):
    ratios = []
    for ratio, numerator_name, numerator_low, numerator_high, denominator_name, denominator_low, denominator_high in POWER_RATIO_DEFINITIONS:
        numerator = _integrated_power(psd_uv2, freqs, numerator_low, numerator_high)
        denominator = _integrated_power(psd_uv2, freqs, denominator_low, denominator_high)
        values = numerator / np.maximum(denominator, EPSILON)
        ratios.append(
            {
                "ratio": ratio,
                "numerator_band": numerator_name,
                "denominator_band": denominator_name,
                "numerator_range_hz": [float(numerator_low), float(numerator_high)],
                "denominator_range_hz": [float(denominator_low), float(denominator_high)],
                "numerator_power_uv2": _channel_values(channels, numerator),
                "denominator_power_uv2": _channel_values(channels, denominator),
                "value": _channel_values(channels, values),
                "mean": float(np.mean(values)),
            }
        )
    return ratios


def _channel_spectral_statistics(psd_uv2, freqs, channels):
    probability = psd_uv2 / np.maximum(np.sum(psd_uv2, axis=1, keepdims=True), EPSILON)
    entropy = -np.sum(probability * np.log(np.maximum(probability, EPSILON)), axis=1) / np.log(psd_uv2.shape[1])
    centroid = np.sum(psd_uv2 * freqs[None, :], axis=1) / np.maximum(np.sum(psd_uv2, axis=1), EPSILON)
    bandwidth = np.sqrt(
        np.sum(psd_uv2 * (freqs[None, :] - centroid[:, None]) ** 2, axis=1)
        / np.maximum(np.sum(psd_uv2, axis=1), EPSILON)
    )
    alpha_centroid = _spectral_centroid_in_band(psd_uv2, freqs, 7.0, 13.0)
    edge_frequencies = {percentile: _spectral_edge_frequency(psd_uv2, freqs, percentile) for percentile in (50, 90, 95)}
    return {
        channel: {
            "spectral_entropy": float(entropy[index]),
            "spectral_centroid_hz": float(centroid[index]),
            "spectral_bandwidth_hz": float(bandwidth[index]),
            "spectral_edge_50_hz": float(edge_frequencies[50][index]),
            "spectral_edge_90_hz": float(edge_frequencies[90][index]),
            "spectral_edge_95_hz": float(edge_frequencies[95][index]),
            "alpha_centroid_hz": float(alpha_centroid[index]),
        }
        for index, channel in enumerate(channels)
    }


def _spectral_centroid_in_band(psd_uv2, freqs, low_hz, high_hz):
    mask = (freqs >= low_hz) & (freqs <= high_hz)
    band_psd = psd_uv2[:, mask]
    band_freqs = freqs[mask]
    return np.sum(band_psd * band_freqs[None, :], axis=1) / np.maximum(np.sum(band_psd, axis=1), EPSILON)


def _spectral_edge_frequency(psd_uv2, freqs, percentile):
    cumulative = np.cumsum(psd_uv2, axis=1)
    targets = cumulative[:, -1] * (percentile / 100.0)
    indices = np.array([np.searchsorted(cumulative[row], targets[row], side="left") for row in range(psd_uv2.shape[0])])
    return freqs[np.clip(indices, 0, freqs.size - 1)]


def _alpha_envelopes(eeg, config):
    if eeg.n_times < 32:
        return {channel: {"max_uv": None, "p95_uv": None} for channel in eeg.ch_names}
    sos = butter(
        4,
        [config.alpha_envelope_low_hz, config.alpha_envelope_high_hz],
        btype="bandpass",
        fs=eeg.info["sfreq"],
        output="sos",
    )
    filtered = sosfiltfilt(sos, eeg.get_data(), axis=1)
    envelopes_uv = np.abs(hilbert(filtered, axis=1)) * 1e6
    return {
        channel: {"max_uv": float(np.max(envelopes_uv[index])), "p95_uv": float(np.percentile(envelopes_uv[index], 95))}
        for index, channel in enumerate(eeg.ch_names)
    }


def _beta_envelopes(eeg):
    """Full-recording Hilbert envelopes for the historical Beta1/Beta2 view."""
    result = {}
    data = eeg.get_data()
    for name, low, high in (("beta1", 13.0, 20.0), ("beta2", 20.0, 30.0)):
        sos = butter(4, [low, high], btype="bandpass", fs=eeg.info["sfreq"], output="sos")
        envelope = np.abs(hilbert(sosfiltfilt(sos, data, axis=1), axis=1)) * 1e6
        rows = [{"channel": channel, "max_uv": float(envelope[index].max()), "p95_uv": float(np.percentile(envelope[index], 95))} for index, channel in enumerate(eeg.ch_names)]
        left = [row for row in rows if _hemisphere(row["channel"]) == "left"]
        right = [row for row in rows if _hemisphere(row["channel"]) == "right"]
        result[name] = {
            "range_hz": [low, high], "channels": rows,
            "hemisphere_summary": {side: _envelope_summary(items) for side, items in (("left", left), ("right", right))},
        }
    return result


def _hemisphere(channel):
    digits = "".join(char for char in channel if char.isdigit())
    return "left" if digits and int(digits) % 2 else "right" if digits else "midline"


def _envelope_summary(rows):
    if not rows:
        return {"channel_count": 0, "mean_p95_uv": None, "maximum_p95_uv": None, "maximum_p95_channel": None}
    maximum = max(rows, key=lambda row: row["p95_uv"])
    return {"channel_count": len(rows), "mean_p95_uv": float(np.mean([row["p95_uv"] for row in rows])), "maximum_p95_uv": maximum["p95_uv"], "maximum_p95_channel": maximum["channel"]}


def _posterior_alpha(psd_uv2, freqs, channels, alpha_envelopes):
    alpha_power = _integrated_power(psd_uv2, freqs, 8.0, 13.0)
    alpha_mask = (freqs >= 8.0) & (freqs <= 13.0)
    records = []
    summaries = {}
    channel_indices = {channel: index for index, channel in enumerate(channels)}
    for hemisphere, requested_channels in POSTERIOR_ALPHA_CHANNELS.items():
        active_channels = [channel for channel in requested_channels if channel in channel_indices]
        hemisphere_records = []
        for channel in active_channels:
            index = channel_indices[channel]
            modal_index = int(np.argmax(psd_uv2[index, alpha_mask]))
            record = {
                "hemisphere": hemisphere,
                "channel": channel,
                "alpha_modal_frequency_hz": float(freqs[alpha_mask][modal_index]),
                "alpha_peak_psd_uv2_per_hz": float(psd_uv2[index, alpha_mask][modal_index]),
                "alpha_integrated_power_uv2": float(alpha_power[index]),
                "alpha_envelope_max_uv": alpha_envelopes[channel]["max_uv"],
                "alpha_envelope_p95_uv": alpha_envelopes[channel]["p95_uv"],
            }
            records.append(record)
            hemisphere_records.append(record)
        summaries[hemisphere] = _posterior_hemisphere_summary(hemisphere_records)
    left_power = summaries["left"]["mean_alpha_integrated_power_uv2"]
    right_power = summaries["right"]["mean_alpha_integrated_power_uv2"]
    asymmetry = None
    if left_power is not None and right_power is not None:
        asymmetry = float(100.0 * (right_power - left_power) / max((right_power + left_power) / 2.0, EPSILON))
    return {"channels": records, "hemisphere_summary": summaries, "posterior_alpha_asymmetry_percent": asymmetry}


def _posterior_hemisphere_summary(records):
    if not records:
        return {
            "channels": [],
            "dominant_peak_psd_channel": None,
            "dominant_alpha_frequency_hz": None,
            "dominant_alpha_peak_psd_uv2_per_hz": None,
            "maximum_envelope_channel": None,
            "maximum_alpha_envelope_uv": None,
            "p95_envelope_channel": None,
            "p95_alpha_envelope_uv": None,
            "mean_alpha_integrated_power_uv2": None,
        }
    peak_record = max(records, key=lambda row: row["alpha_peak_psd_uv2_per_hz"])
    envelope_record = max(records, key=lambda row: row["alpha_envelope_max_uv"])
    p95_record = max(records, key=lambda row: row["alpha_envelope_p95_uv"])
    return {
        "channels": [row["channel"] for row in records],
        "dominant_peak_psd_channel": peak_record["channel"],
        "dominant_alpha_frequency_hz": peak_record["alpha_modal_frequency_hz"],
        "dominant_alpha_peak_psd_uv2_per_hz": peak_record["alpha_peak_psd_uv2_per_hz"],
        "maximum_envelope_channel": envelope_record["channel"],
        "maximum_alpha_envelope_uv": envelope_record["alpha_envelope_max_uv"],
        "p95_envelope_channel": p95_record["channel"],
        "p95_alpha_envelope_uv": p95_record["alpha_envelope_p95_uv"],
        "mean_alpha_integrated_power_uv2": float(np.mean([row["alpha_integrated_power_uv2"] for row in records])),
    }


def _band_peaks(psd_uv2, freqs, channels, min_prominence):
    global_log_psd = np.log10(np.maximum(np.mean(psd_uv2, axis=0), EPSILON))
    return {
        "scope": "welch_log10_psd_uv2_per_hz",
        "global": [_find_band_peak(global_log_psd, freqs, name, low, high, min_prominence) for name, low, high in PEAK_BANDS],
        "by_channel": {
            channel: [_find_band_peak(np.log10(np.maximum(psd_uv2[index], EPSILON)), freqs, name, low, high, min_prominence) for name, low, high in PEAK_BANDS]
            for index, channel in enumerate(channels)
        },
    }


def _find_band_peak(log_psd, freqs, name, low_hz, high_hz, min_prominence):
    mask = (freqs >= low_hz) & (freqs <= high_hz)
    band_values = log_psd[mask]
    band_freqs = freqs[mask]
    base = {
        "band": name,
        "requested_low_hz": float(low_hz),
        "requested_high_hz": float(high_hz),
        "fitted_low_hz": float(band_freqs[0]) if band_freqs.size else None,
        "fitted_high_hz": float(band_freqs[-1]) if band_freqs.size else None,
        "detected_peak_count": 0,
        "peak_detected": False,
        "peak_frequency_hz": None,
        "peak_bandwidth_hz": None,
        "peak_prominence_log10": None,
    }
    if band_values.size < 3:
        return base
    peak_indices, properties = find_peaks(band_values, prominence=min_prominence)
    base["detected_peak_count"] = int(peak_indices.size)
    if peak_indices.size == 0:
        return base
    selected = int(peak_indices[np.argmax(properties["prominences"])])
    width = peak_widths(band_values, [selected], rel_height=0.5)[0][0] * np.median(np.diff(band_freqs))
    return {
        **base,
        "peak_detected": True,
        "peak_frequency_hz": float(band_freqs[selected]),
        "peak_bandwidth_hz": float(width),
        "peak_prominence_log10": float(properties["prominences"][np.argmax(properties["prominences"])]),
    }


def _paf(psd, freqs, channels):
    mask = (freqs >= 8.0) & (freqs <= 13.0)
    points = {}
    for electrode in ("O1", "O2"):
        if electrode in channels:
            index = channels.index(electrode)
            points[electrode] = float(freqs[mask][np.argmax(psd[index, mask])])
    return {"by_channel_hz": points, "mean": float(np.mean(list(points.values()))) if points else None}


def _tbr(rows):
    by_name = {row["band"]: row for row in rows}
    if not {"theta", "beta"} <= by_name.keys():
        return {"by_channel": {}, "mean": None}
    values = {
        channel: theta / max(by_name["beta"]["absolute_power_uv2"][channel], EPSILON)
        for channel, theta in by_name["theta"]["absolute_power_uv2"].items()
    }
    selected = [values[name] for name in ("Fz", "Cz") if name in values]
    return {"by_channel": values, "mean": float(np.mean(selected or list(values.values())))}


def _faa(rows):
    alpha = next((row for row in rows if row["band"] == "alpha"), None)
    if not alpha or not {"F3", "F4"} <= alpha["absolute_power_uv2"].keys():
        return None
    return float(np.log(alpha["absolute_power_uv2"]["F4"]) - np.log(alpha["absolute_power_uv2"]["F3"]))


def _channel_values(channels, values):
    return {channel: float(value) for channel, value in zip(channels, values)}
