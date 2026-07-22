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
    filter_order: int = 4
    minimum_peak_distance_ms: float = 10.0
    display_sampling_hz: float = 10.0
    minimum_filter_cycles: float = 3.0


def compute_gfp_gmd(
    raw,
    config: GFPConfig | None = None,
    *,
    source_time_mapping: dict | None = None,
) -> dict:
    """Compute GFP and GMD on every retained sample of a recording.

    When rejected epochs were concatenated for quantitative analysis,
    ``source_time_mapping`` restores their original time coordinate for every
    exported time series and removes peak pairs that cross a rejected gap.
    """
    config = config or GFPConfig()
    retained_intervals = _retained_analysis_intervals(raw.n_times, source_time_mapping)
    minimum_interval_samples = _minimum_filter_interval_samples(raw, config)
    _validate_filter_interval_lengths(retained_intervals, minimum_interval_samples)
    signal = _filter_retained_intervals(raw, config, retained_intervals)
    gfp = signal.std(axis=0)
    distance = max(1, round(config.minimum_peak_distance_ms * raw.info["sfreq"] / 1000))
    peak_chunks = []
    gmd_chunks = []
    for start, stop in retained_intervals:
        interval_peaks, _ = find_peaks(gfp[start:stop], distance=distance)
        interval_peaks = interval_peaks + start
        peak_chunks.append(interval_peaks)
        maps = _normalize_maps(signal[:, interval_peaks])
        gmd_chunks.append(
            _polarity_invariant_gmd(maps[:, :-1], maps[:, 1:])
            if interval_peaks.size > 1
            else np.empty(0)
        )
    peaks = np.concatenate(peak_chunks) if peak_chunks else np.empty(0, dtype=int)
    first_peaks = np.concatenate([chunk[:-1] for chunk in peak_chunks]) if peak_chunks else np.empty(0, dtype=int)
    second_peaks = np.concatenate([chunk[1:] for chunk in peak_chunks]) if peak_chunks else np.empty(0, dtype=int)
    gmd = np.concatenate(gmd_chunks) if gmd_chunks else np.empty(0)
    sample_times = _source_times(raw, source_time_mapping)
    peak_pair_rows = _successive_peak_gmd_rows(
        first_peaks, second_peaks, gfp, gmd, raw.info["sfreq"], sample_times
    )
    display_stride = max(1, round(raw.info["sfreq"] / config.display_sampling_hz))
    display_indices, display_times, display_values = _display_series_on_source_axis(
        gfp, sample_times, source_time_mapping, display_stride
    )
    gmd_series = _gmd_series_on_source_axis(
        peak_chunks, gmd_chunks, sample_times, separate_intervals=source_time_mapping is not None
    )
    return {
        "scope": "full_recording",
        "filter_hz": [config.low_hz, config.high_hz],
        "filter_design": {
            "method": "iir",
            "family": "butterworth",
            "order": config.filter_order,
            "phase": "zero",
            "minimum_interval_cycles_at_low_cutoff": config.minimum_filter_cycles,
            "minimum_interval_duration_sec": minimum_interval_samples / float(raw.info["sfreq"]),
            "short_interval_policy": "reject",
        },
        "sampling_rate_hz": float(raw.info["sfreq"]),
        "duration_sec": float(gfp.size / raw.info["sfreq"]),
        "source_duration_sec": float(source_time_mapping["source_duration_sec"]) if source_time_mapping else float(gfp.size / raw.info["sfreq"]),
        "gfp_uv": _summary(gfp),
        "gfp_full_series": {
            "sampling_rate_hz": float(raw.info["sfreq"]),
            "sample_indices": np.arange(gfp.size, dtype=int).tolist(),
            "time_sec": sample_times.tolist(),
            "values_uv": gfp.tolist(),
            "description": "Every-sample GFP series across the complete QC-retained recording, with original source-time coordinates when available.",
        },
        "gfp_display_series": {
            "sampling_rate_hz": float(raw.info["sfreq"] / display_stride),
            "sample_indices": display_indices,
            "time_sec": display_times,
            "values_uv": display_values,
            "description": "Uniformly decimated GFP series on the original time axis; rejected epochs are null gaps. Summary statistics use every retained sample.",
        },
        "gfp_peak_indices": peaks.tolist(),
        "gfp_peak_times_sec": sample_times[peaks].tolist(),
        "gfp_peak_uv": _summary(gfp[peaks]),
        "successive_peak_gmd": _summary(gmd),
        "successive_peak_gmd_series": {
            **gmd_series,
            "description": "Polarity-invariant GMD between successive GFP-peak maps within continuous retained source intervals; pairs across rejected gaps are omitted and plot intervals are separated by nulls.",
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
    first_peaks: np.ndarray,
    second_peaks: np.ndarray,
    gfp: np.ndarray,
    gmd: np.ndarray,
    sfreq: float,
    sample_times: np.ndarray | None = None,
) -> list[dict]:
    """Return a lossless table joining peak locations, GFP amplitudes, and GMD."""
    return [
        {
            "peak_pair_index": pair_index,
            "first_peak_gfp_uv": float(gfp[first_peak]),
            "second_peak_gfp_uv": float(gfp[second_peak]),
            "gmd": float(value),
            "first_peak_sample_index": int(first_peak),
            "first_peak_time_sec": float((sample_times[first_peak] if sample_times is not None else first_peak / sfreq)),
            "second_peak_sample_index": int(second_peak),
            "second_peak_time_sec": float((sample_times[second_peak] if sample_times is not None else second_peak / sfreq)),
        }
        for pair_index, (first_peak, second_peak, value) in enumerate(
            zip(first_peaks, second_peaks, gmd), start=1
        )
    ]


def _source_times(raw, source_time_mapping: dict | None) -> np.ndarray:
    if source_time_mapping is None:
        return np.arange(raw.n_times, dtype=float) / float(raw.info["sfreq"])
    from .qc import retained_sample_source_times

    times = retained_sample_source_times(source_time_mapping)
    if len(times) != raw.n_times:
        raise ValueError("source_time_mapping does not match the GFP sample count")
    return times


def _retained_analysis_intervals(
    sample_count: int,
    source_time_mapping: dict | None,
) -> list[tuple[int, int]]:
    """Return analysis ranges merged only when they are contiguous in source time."""
    if source_time_mapping is None:
        return [(0, sample_count)] if sample_count else []

    retained = source_time_mapping.get("retained_intervals", [])
    intervals: list[tuple[int, int]] = []
    analysis_cursor = 0
    previous_source_stop = None
    for interval in retained:
        analysis_start = int(interval["analysis_sample_start"])
        analysis_stop = int(interval["analysis_sample_stop"])
        source_start = int(interval["screened_sample_start"])
        source_stop = int(interval["screened_sample_stop"])
        if analysis_start != analysis_cursor or analysis_stop <= analysis_start:
            raise ValueError("source_time_mapping retained analysis intervals must be contiguous and ordered")
        if source_stop - source_start != analysis_stop - analysis_start:
            raise ValueError("source_time_mapping retained interval sample counts do not match")
        if previous_source_stop is not None and source_start < previous_source_stop:
            raise ValueError("source_time_mapping retained source intervals must be ordered")
        if intervals and source_start == previous_source_stop:
            intervals[-1] = (intervals[-1][0], analysis_stop)
        else:
            intervals.append((analysis_start, analysis_stop))
        analysis_cursor = analysis_stop
        previous_source_stop = source_stop

    if analysis_cursor != sample_count:
        raise ValueError("source_time_mapping does not match the GFP sample count")
    return intervals


def _filter_retained_intervals(
    raw,
    config: GFPConfig,
    retained_intervals: list[tuple[int, int]],
) -> np.ndarray:
    eeg = raw.copy().pick("eeg")
    if retained_intervals == [(0, raw.n_times)]:
        return _filter_gfp_segment(eeg, config).get_data() * 1e6

    filtered = np.empty((len(eeg.ch_names), raw.n_times), dtype=float)
    sfreq = float(raw.info["sfreq"])
    for start, stop in retained_intervals:
        segment = eeg.copy().crop(
            tmin=start / sfreq,
            tmax=(stop - 1) / sfreq,
            include_tmax=True,
        )
        segment_data = _filter_gfp_segment(segment, config).get_data()
        if segment_data.shape[-1] != stop - start:
            raise ValueError("retained interval filtering changed the GFP sample count")
        filtered[:, start:stop] = segment_data
    return filtered * 1e6


def _minimum_filter_interval_samples(raw, config: GFPConfig) -> int:
    if config.low_hz <= 0:
        raise ValueError("GFP low_hz must be positive")
    if config.minimum_filter_cycles <= 0:
        raise ValueError("GFP minimum_filter_cycles must be positive")
    return int(np.ceil(config.minimum_filter_cycles * float(raw.info["sfreq"]) / config.low_hz))


def _validate_filter_interval_lengths(
    retained_intervals: list[tuple[int, int]],
    minimum_interval_samples: int,
) -> None:
    short = [stop - start for start, stop in retained_intervals if stop - start < minimum_interval_samples]
    if short:
        raise ValueError(
            "GFP filtering requires each continuous retained source interval to contain "
            f"at least {minimum_interval_samples} samples; shortest interval has {min(short)}. "
            "Short intervals lack enough source-time context for the configured low cutoff."
        )


def _filter_gfp_segment(segment, config: GFPConfig):
    """Use a fixed short-memory filter suitable for one-second QC intervals."""
    return segment.filter(
        config.low_hz,
        config.high_hz,
        method="iir",
        iir_params={"order": config.filter_order, "ftype": "butter"},
        phase="zero",
        verbose="ERROR",
    )


def _gmd_series_on_source_axis(
    peak_chunks: list[np.ndarray],
    gmd_chunks: list[np.ndarray],
    sample_times: np.ndarray,
    *,
    separate_intervals: bool,
) -> dict[str, list]:
    series = {
        "from_peak_indices": [],
        "to_peak_indices": [],
        "from_time_sec": [],
        "to_time_sec": [],
        "time_sec": [],
        "values": [],
    }
    for peaks, values in zip(peak_chunks, gmd_chunks):
        if not values.size:
            continue
        if separate_intervals and series["values"]:
            for field in series.values():
                field.append(None)
        from_times = sample_times[peaks[:-1]].tolist()
        to_times = sample_times[peaks[1:]].tolist()
        series["from_peak_indices"].extend(peaks[:-1].tolist())
        series["to_peak_indices"].extend(peaks[1:].tolist())
        series["from_time_sec"].extend(from_times)
        series["to_time_sec"].extend(to_times)
        series["time_sec"].extend(to_times)
        series["values"].extend(values.tolist())
    return series


def _display_series_on_source_axis(
    values: np.ndarray,
    sample_times: np.ndarray,
    source_time_mapping: dict | None,
    stride: int,
) -> tuple[list[int], list[float], list[float | None]]:
    indices = np.arange(0, len(values), stride, dtype=int)
    if source_time_mapping is None:
        return indices.tolist(), sample_times[indices].tolist(), values[indices].tolist()
    from .qc import restore_source_time_axis

    source_times, restored = restore_source_time_axis(values, source_time_mapping)
    source_indices = np.arange(0, len(restored), stride, dtype=int)
    missing = np.isnan(restored)
    gap_starts = np.flatnonzero(missing & np.concatenate(([True], ~missing[:-1])))
    retained_boundaries = []
    for interval in source_time_mapping.get("retained_intervals", []):
        start = int(interval["screened_sample_start"])
        stop = int(interval["screened_sample_stop"])
        if stop > start:
            retained_boundaries.extend((start, stop - 1))
    source_indices = np.unique(np.concatenate((source_indices, gap_starts, retained_boundaries)))
    displayed = restored[source_indices]
    return source_indices.tolist(), source_times[source_indices].tolist(), [None if np.isnan(value) else float(value) for value in displayed]


def _summary(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=float)
    if not values.size:
        return {"count": 0, "mean": None, "median": None, "standard_deviation": None, "p95": None, "maximum": None}
    return {"count": int(values.size), "mean": float(values.mean()), "median": float(np.median(values)), "standard_deviation": float(values.std()), "p95": float(np.quantile(values, 0.95)), "maximum": float(values.max())}
