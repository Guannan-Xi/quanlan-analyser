"""Full-recording channel-wise EEG complexity features."""

from __future__ import annotations

from dataclasses import dataclass
import math

import antropy as ant
import numpy as np


@dataclass(frozen=True)
class ComplexityConfig:
    maximum_samples_per_channel: int = 5000
    multiscale_max_scale: int = 20
    random_state: int = 42


def compute_complexity(raw, config: ComplexityConfig | None = None) -> dict:
    """Compute complexity on each channel using samples spanning the full recording."""
    config = config or ComplexityConfig()
    data = raw.copy().pick("eeg").get_data() * 1e6
    indices = np.linspace(0, data.shape[1] - 1, min(data.shape[1], config.maximum_samples_per_channel), dtype=int)
    sampled = data[:, indices]
    rows = []
    curves = []
    for name, channel in zip(raw.copy().pick("eeg").ch_names, sampled):
        row, curve = _channel_features(name, channel, raw.info["sfreq"], config)
        rows.append(row)
        curves.append(curve)
    scales = list(range(1, max((len(curve) for curve in curves), default=0) + 1))
    mean_curve = [
        float(np.nanmean([curve[scale - 1] for curve in curves if len(curve) >= scale]))
        for scale in scales
    ]
    return {
        "scope": "full_recording_evenly_subsampled_for_nonlinear_estimators",
        "sample_count_per_channel": int(sampled.shape[1]),
        "channel_metrics": rows,
        "global_means": {key: float(np.nanmean([row[key] for row in rows])) for key in rows[0] if key != "channel"},
        "multiscale_entropy": {
            "scales": scales,
            "mean_sample_entropy": mean_curve,
            "channel_curves": {row["channel"]: curve for row, curve in zip(rows, curves)},
        },
    }


def _channel_features(name, signal, sfreq, config):
    signal = np.ascontiguousarray(signal, dtype=np.float64)
    first = np.diff(signal)
    second = np.diff(first)
    activity = float(np.var(signal))
    mobility = float(math.sqrt(np.var(first) / max(activity, np.finfo(float).eps)))
    complexity = float(math.sqrt(np.var(second) / max(np.var(first), np.finfo(float).eps)) / max(mobility, np.finfo(float).eps))
    curve = _multiscale_entropy_curve(signal, config.multiscale_max_scale)
    return ({"channel": name, "hjorth_activity_uv2": activity, "hjorth_mobility": mobility, "hjorth_complexity": complexity, "sample_entropy": _finite(ant.sample_entropy(signal)), "higuchi_fd": _finite(ant.higuchi_fd(signal)), "hurst_exponent": _hurst_rs(signal), "permutation_entropy": _finite(ant.perm_entropy(signal, normalize=True)), "dfa_exponent": _finite(ant.detrended_fluctuation(signal)), "lempel_ziv_complexity": _finite(ant.lziv_complexity(signal > np.median(signal), normalize=True)), "svd_entropy": _finite(ant.svd_entropy(signal, normalize=True)), "petrosian_fd": _finite(ant.petrosian_fd(signal)), "katz_fd": _finite(ant.katz_fd(signal)), "multiscale_entropy_complexity_index": float(np.trapezoid(curve, dx=1)) if len(curve) > 1 else float("nan")}, curve)


def _multiscale_entropy_curve(signal, max_scale):
    values = []
    for scale in range(1, max_scale + 1):
        size = signal.size // scale
        if size < 20:
            break
        coarse = signal[: size * scale].reshape(size, scale).mean(axis=1)
        values.append(_finite(ant.sample_entropy(coarse)))
    return values


def _hurst_rs(signal):
    """Estimate Hurst exponent from the slope of rescaled-range statistics."""
    windows = [size for size in (16, 32, 64, 128, 256, 512, 1024, 2048) if size <= signal.size // 2]
    values = []
    for size in windows:
        blocks = signal[: signal.size // size * size].reshape(-1, size)
        centered = blocks - blocks.mean(axis=1, keepdims=True)
        span = np.ptp(np.cumsum(centered, axis=1), axis=1)
        deviation = blocks.std(axis=1)
        ratio = span / np.maximum(deviation, np.finfo(float).eps)
        values.append(float(np.mean(ratio)))
    if len(values) < 2:
        return float("nan")
    return _finite(np.polyfit(np.log(windows), np.log(np.maximum(values, np.finfo(float).eps)), 1)[0])


def _finite(value):
    value = float(value)
    return value if np.isfinite(value) else float("nan")
