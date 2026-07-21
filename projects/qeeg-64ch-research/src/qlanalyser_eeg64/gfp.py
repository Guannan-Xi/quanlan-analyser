"""Global field power and global map dissimilarity for continuous EEG."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks


@dataclass(frozen=True)
class GFPConfig:
    low_hz: float = 2.0
    high_hz: float = 20.0
    minimum_peak_distance_ms: float = 10.0
    display_sampling_hz: float = 10.0


def compute_gfp_gmd(raw, config: GFPConfig | None = None) -> dict:
    """Compute GFP and polarity-invariant GMD on every sample of a recording."""
    config = config or GFPConfig()
    signal = raw.copy().pick("eeg").filter(config.low_hz, config.high_hz, verbose="ERROR").get_data() * 1e6
    gfp = signal.std(axis=0)
    distance = max(1, round(config.minimum_peak_distance_ms * raw.info["sfreq"] / 1000))
    peaks, _ = find_peaks(gfp, distance=distance)
    maps = _normalize_maps(signal[:, peaks])
    gmd = _polarity_invariant_gmd(maps[:, :-1], maps[:, 1:]) if peaks.size > 1 else np.empty(0)
    peak_pair_rows = _successive_peak_gmd_rows(peaks, gfp, gmd, raw.info["sfreq"])
    display_stride = max(1, round(raw.info["sfreq"] / config.display_sampling_hz))
    display_indices = np.arange(0, gfp.size, display_stride, dtype=int)
    return {
        "scope": "full_recording",
        "filter_hz": [config.low_hz, config.high_hz],
        "sampling_rate_hz": float(raw.info["sfreq"]),
        "duration_sec": float(gfp.size / raw.info["sfreq"]),
        "gfp_uv": _summary(gfp),
        "gfp_full_series": {
            "sampling_rate_hz": float(raw.info["sfreq"]),
            "values_uv": gfp.tolist(),
            "description": "Every-sample GFP series across the complete QC-retained recording.",
        },
        "gfp_display_series": {
            "sampling_rate_hz": float(raw.info["sfreq"] / display_stride),
            "sample_indices": display_indices.tolist(),
            "time_sec": (display_indices / raw.info["sfreq"]).tolist(),
            "values_uv": gfp[display_indices].tolist(),
            "description": "Uniformly decimated full-recording GFP series for display; summary statistics use every sample.",
        },
        "gfp_peak_indices": peaks.tolist(),
        "gfp_peak_times_sec": (peaks / raw.info["sfreq"]).tolist(),
        "gfp_peak_uv": _summary(gfp[peaks]),
        "successive_peak_gmd": _summary(gmd),
        "successive_peak_gmd_series": {
            "from_peak_indices": peaks[:-1].tolist(),
            "to_peak_indices": peaks[1:].tolist(),
            "from_time_sec": (peaks[:-1] / raw.info["sfreq"]).tolist(),
            "to_time_sec": (peaks[1:] / raw.info["sfreq"]).tolist(),
            "values": gmd.tolist(),
            "description": "Polarity-invariant GMD between each successive pair of GFP-peak maps.",
        },
        "successive_peak_topography_gmd": {
            "scope": "full_qc_retained_recording_successive_gfp_peak_pairs",
            "definition": (
                "Each row compares the normalized, demeaned scalp maps at two adjacent GFP peaks. "
                "GMD is the lower RMS distance after testing the direct and polarity-inverted maps."
            ),
            "rows": peak_pair_rows,
        },
        "definition": {
            "gfp": "population standard deviation across average-referenced scalp channels",
            "gmd": "polarity-invariant RMS distance between GFP-peak maps after channel demeaning and GFP normalization",
        },
    }


def write_gfp_peak_topography_gmd_csv(result: dict, path: str | Path) -> Path:
    """Write one traceable row for every successive GFP-peak topography pair.

    The first four columns preserve the historical report's table contract.
    Sample indices and elapsed times are included so downstream software can
    locate both maps in the QC-retained recording without re-running peak
    detection.
    """
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "peak_pair_index",
        "first_peak_gfp_uv",
        "second_peak_gfp_uv",
        "gmd",
        "first_peak_sample_index",
        "first_peak_time_sec",
        "second_peak_sample_index",
        "second_peak_time_sec",
    ]
    rows = result.get("successive_peak_topography_gmd", {}).get("rows", [])
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return destination


def _normalize_maps(maps: np.ndarray) -> np.ndarray:
    centered = maps - maps.mean(axis=0, keepdims=True)
    norm = np.linalg.norm(centered, axis=0, keepdims=True)
    return centered / np.maximum(norm, np.finfo(float).eps)


def _polarity_invariant_gmd(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    direct = np.sqrt(np.mean((left - right) ** 2, axis=0))
    inverted = np.sqrt(np.mean((left + right) ** 2, axis=0))
    return np.minimum(direct, inverted)


def _successive_peak_gmd_rows(
    peaks: np.ndarray,
    gfp: np.ndarray,
    gmd: np.ndarray,
    sfreq: float,
) -> list[dict]:
    """Return a lossless table joining peak locations, GFP amplitudes, and GMD."""
    return [
        {
            "peak_pair_index": pair_index,
            "first_peak_gfp_uv": float(gfp[first_peak]),
            "second_peak_gfp_uv": float(gfp[second_peak]),
            "gmd": float(value),
            "first_peak_sample_index": int(first_peak),
            "first_peak_time_sec": float(first_peak / sfreq),
            "second_peak_sample_index": int(second_peak),
            "second_peak_time_sec": float(second_peak / sfreq),
        }
        for pair_index, (first_peak, second_peak, value) in enumerate(
            zip(peaks[:-1], peaks[1:], gmd), start=1
        )
    ]


def _summary(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=float)
    if not values.size:
        return {"count": 0, "mean": None, "median": None, "standard_deviation": None, "p95": None, "maximum": None}
    return {"count": int(values.size), "mean": float(values.mean()), "median": float(np.median(values)), "standard_deviation": float(values.std()), "p95": float(np.quantile(values, 0.95)), "maximum": float(values.max())}
