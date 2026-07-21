"""Sensor-space microstate segmentation with full-recording temporal metrics."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks
from sklearn.cluster import KMeans

from .gfp import _normalize_maps


@dataclass(frozen=True)
class MicrostateConfig:
    states: int = 6
    low_hz: float = 2.0
    high_hz: float = 20.0
    minimum_peak_distance_ms: float = 10.0
    minimum_segment_ms: float = 30.0
    information_window_seconds: float = 1.0
    information_mutual_information_lag_ms: float = 40.0
    information_lag_start_ms: float = 4.0
    information_lag_stop_ms: float = 40.0
    information_lag_step_ms: float = 4.0
    random_state: int = 42


def compute_microstates(
    raw,
    config: MicrostateConfig | None = None,
    *,
    source_epoch_rows: list[dict] | None = None,
) -> dict:
    """Fit maps at all GFP peaks then label every sample in the continuous record.

    State labels are data-specific cluster labels, not named functional networks.
    """
    config = config or MicrostateConfig()
    if config.states < 2:
        raise ValueError("microstate state count must be at least two")
    cleaned = raw.copy().pick("eeg").filter(config.low_hz, config.high_hz, verbose="ERROR")
    data = cleaned.get_data() * 1e6
    normalized = _normalize_maps(data)
    gfp = data.std(axis=0)
    distance = max(1, round(config.minimum_peak_distance_ms * cleaned.info["sfreq"] / 1000))
    peaks, _ = find_peaks(gfp, distance=distance)
    if peaks.size < config.states:
        raise ValueError("recording has fewer GFP peaks than requested microstate states")
    peak_maps = normalized[:, peaks].T
    model = KMeans(n_clusters=config.states, n_init=30, random_state=config.random_state)
    peak_labels = model.fit_predict(peak_maps)
    templates = _normalize_maps(model.cluster_centers_.T).T
    similarity = templates @ normalized
    labels = np.argmax(np.abs(similarity), axis=0)
    labels = _merge_short_segments(labels, max(1, round(config.minimum_segment_ms * cleaned.info["sfreq"] / 1000)))
    explained = np.max(np.abs(similarity), axis=0) ** 2
    names = [chr(ord("A") + index) for index in range(config.states)]
    parameters = _temporal_parameters(labels, names, cleaned.info["sfreq"], similarity, explained)
    transitions = _transition_matrix(labels, names)
    segments = _segments(labels, names, cleaned.info["sfreq"])
    timeline_mapping = build_microstate_timeline_mapping(
        labels.size,
        cleaned.info["sfreq"],
        source_epoch_rows=source_epoch_rows,
    )
    source_timeline_segments = map_microstate_segments_to_source_time(
        segments,
        timeline_mapping,
    )
    information_dynamics = compute_microstate_information_dynamics(
        [names[index] for index in labels],
        names,
        cleaned.info["sfreq"],
        window_seconds=config.information_window_seconds,
        mutual_information_lag_ms=config.information_mutual_information_lag_ms,
    )
    lagged_information = compute_microstate_lagged_information(
        [names[index] for index in labels],
        names,
        cleaned.info["sfreq"],
        start_ms=config.information_lag_start_ms,
        stop_ms=config.information_lag_stop_ms,
        step_ms=config.information_lag_step_ms,
    )
    direct_transition_counts = _direct_transition_counts(transitions)
    return {
        "scope": "full_recording",
        "config": {
            "states": config.states,
            "filter_hz": [config.low_hz, config.high_hz],
            "minimum_segment_ms": config.minimum_segment_ms,
            "information_window_seconds": config.information_window_seconds,
            "information_mutual_information_lag_ms": config.information_mutual_information_lag_ms,
            "information_lag_range_ms": [config.information_lag_start_ms, config.information_lag_stop_ms],
            "information_lag_step_ms": config.information_lag_step_ms,
            "random_state": config.random_state,
        },
        "state_names": names,
        "templates_uv_normalized": {name: templates[index].tolist() for index, name in enumerate(names)},
        "gfp_peak_indices": peaks.tolist(),
        "peak_labels": [names[index] for index in peak_labels],
        "sample_labels": [names[index] for index in labels],
        "parameters": parameters,
        "transition_matrix": transitions,
        "direct_transition_counts": direct_transition_counts,
        "transition_count_table": direct_transition_counts["rows"],
        "duration_summary": _duration_summary(segments, names),
        "per_second_coverage": _per_second_coverage(labels, names, cleaned.info["sfreq"]),
        "outgoing_transitions": _outgoing_transitions(transitions),
        "sequence": _sequence_summary(labels, names, segments),
        "information_dynamics": information_dynamics,
        "lagged_information": lagged_information,
        "segments": segments,
        "timeline_mapping": timeline_mapping,
        "source_timeline_segments": source_timeline_segments,
        "continuous_geV_percent": float(100 * explained.mean()),
        "boundary": "State labels are clustering labels for this recording and do not identify fixed functional networks or diseases.",
    }


def compute_microstate_lagged_information(
    sample_labels: list[str],
    state_names: list[str],
    sfreq: float,
    *,
    start_ms: float = 4.0,
    stop_ms: float = 40.0,
    step_ms: float = 4.0,
) -> dict:
    """Pool microstate information measures over the entire retained record.

    This function is intentionally distinct from
    :func:`compute_microstate_information_dynamics`: it pools every eligible
    pair in the complete retained sequence for each requested lag, whereas
    ``information_dynamics`` reports time-varying values in consecutive
    one-second windows.  Neither output is a functional-connectivity metric.
    """
    labels, global_probability = _validate_and_index_labels(sample_labels, state_names, sfreq)
    if start_ms <= 0 or stop_ms < start_ms or step_ms <= 0:
        raise ValueError("lag range must satisfy 0 < start_ms <= stop_ms and step_ms > 0")

    requested_lags = np.arange(start_ms, stop_ms + step_ms / 2, step_ms, dtype=float)
    rows = []
    for requested_lag_ms in requested_lags:
        lag_samples = max(1, round(requested_lag_ms * sfreq / 1000))
        actual_lag_ms = float(1000 * lag_samples / sfreq)
        if lag_samples >= labels.size:
            rows.append(
                {
                    "requested_lag_ms": float(requested_lag_ms),
                    "lag_samples": int(lag_samples),
                    "actual_lag_ms": actual_lag_ms,
                    "pair_count": 0,
                    "mutual_information_bits": None,
                    "normalized_mutual_information": None,
                    "mean_conditional_self_information_bits": None,
                    "mean_marginal_self_information_bits": None,
                }
            )
            continue

        before, after = labels[:-lag_samples], labels[lag_samples:]
        mutual_information = _discrete_mutual_information_bits(before, after, len(state_names))
        before_probability = np.bincount(before, minlength=len(state_names)) / before.size
        after_probability = np.bincount(after, minlength=len(state_names)) / after.size
        entropy_before = _shannon_entropy(before_probability)
        entropy_after = _shannon_entropy(after_probability)
        conditional_self_information = float(entropy_after - mutual_information)
        marginal_self_information = float(
            np.mean(-np.log2(np.maximum(global_probability[after], np.finfo(float).tiny)))
        )
        rows.append(
            {
                "requested_lag_ms": float(requested_lag_ms),
                "lag_samples": int(lag_samples),
                "actual_lag_ms": actual_lag_ms,
                "pair_count": int(before.size),
                "mutual_information_bits": mutual_information,
                "normalized_mutual_information": float(
                    2 * mutual_information / (entropy_before + entropy_after)
                ) if entropy_before + entropy_after > 0 else 0.0,
                "mean_conditional_self_information_bits": conditional_self_information,
                "mean_marginal_self_information_bits": marginal_self_information,
            }
        )

    return {
        "scope": "full_retained_recording_pooled_lag_statistics",
        "time_coordinate": "retained_analysis_time",
        "definition": {
            "state_self_information": "-log2(p(state)), where p(state) is estimated from all labels in the retained recording.",
            "mean_conditional_self_information": "Average -log2(p(S_t+lag | S_t)); equivalently H(S_t+lag | S_t) over all eligible pairs.",
            "lagged_mutual_information": "Discrete I(S_t; S_t+lag) pooled over all eligible label pairs at each lag.",
            "comparison_with_information_dynamics": "This table pools the full retained recording by lag. information_dynamics instead reports consecutive one-second windows and a single configured lag; their values are not interchangeable.",
        },
        "state_self_information": [
            {
                "state": name,
                "sample_count": int(np.sum(labels == index)),
                "occupancy_probability": float(global_probability[index]),
                "self_information_bits": float(-np.log2(max(global_probability[index], np.finfo(float).tiny))),
            }
            for index, name in enumerate(state_names)
        ],
        "rows": rows,
    }


def compute_microstate_information_dynamics(
    sample_labels: list[str],
    state_names: list[str],
    sfreq: float,
    *,
    window_seconds: float = 1.0,
    mutual_information_lag_ms: float = 40.0,
) -> dict:
    """Calculate full-record microstate self-information and short-time MI.

    Self-information is ``-log2(p(state))``, where ``p(state)`` is estimated
    from the complete labelled recording.  The curve reports its mean in each
    consecutive time window.  Lagged mutual information is calculated within
    the same window between labels separated by the configured lag; it
    summarizes short-term state-sequence predictability rather than a
    connectivity measure.
    """
    if not sample_labels:
        raise ValueError("sample_labels must contain at least one label")
    if not state_names:
        raise ValueError("state_names must contain at least one state")
    if sfreq <= 0:
        raise ValueError("sfreq must be positive")
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")
    if mutual_information_lag_ms <= 0:
        raise ValueError("mutual_information_lag_ms must be positive")

    index_by_name = {name: index for index, name in enumerate(state_names)}
    if len(index_by_name) != len(state_names):
        raise ValueError("state_names must be unique")
    try:
        labels = np.asarray([index_by_name[name] for name in sample_labels], dtype=int)
    except KeyError as error:
        raise ValueError(f"sample_labels contains unknown state {error.args[0]!r}") from error

    state_count = len(state_names)
    global_probability = np.bincount(labels, minlength=state_count) / labels.size
    self_information = -np.log2(np.maximum(global_probability[labels], np.finfo(float).tiny))
    window_samples = max(1, round(window_seconds * sfreq))
    lag_samples = max(1, round(mutual_information_lag_ms * sfreq / 1000))
    rows = []
    for start in range(0, labels.size, window_samples):
        end = min(labels.size, start + window_samples)
        window = labels[start:end]
        if window.size > lag_samples:
            before, after = window[:-lag_samples], window[lag_samples:]
            mutual_information = _discrete_mutual_information_bits(before, after, state_count)
            entropy_before = _shannon_entropy(np.bincount(before, minlength=state_count) / before.size)
            entropy_after = _shannon_entropy(np.bincount(after, minlength=state_count) / after.size)
            normalized_mutual_information = float(
                2 * mutual_information / (entropy_before + entropy_after)
            ) if entropy_before + entropy_after > 0 else 0.0
            pair_count = int(before.size)
        else:
            mutual_information = None
            normalized_mutual_information = None
            pair_count = 0
        window_probability = np.bincount(window, minlength=state_count) / window.size
        rows.append(
            {
                "start_sec": float(start / sfreq),
                "end_sec": float(end / sfreq),
                "sample_count": int(window.size),
                "mean_self_information_bits": float(self_information[start:end].mean()),
                "state_entropy_bits": _shannon_entropy(window_probability),
                "lagged_mutual_information_bits": mutual_information,
                "lagged_normalized_mutual_information": normalized_mutual_information,
                "lagged_pair_count": pair_count,
            }
        )

    usable_mutual_information = [
        row["lagged_mutual_information_bits"]
        for row in rows
        if row["lagged_mutual_information_bits"] is not None
    ]
    return {
        "scope": "full_recording_consecutive_windows",
        "time_coordinate": "retained_analysis_time",
        "definition": {
            "self_information": "-log2(p(state)); p(state) is the state occupancy over the full labelled recording.",
            "lagged_mutual_information": "Discrete mutual information I(S_t; S_t+lag) calculated within each consecutive window.",
            "comparison_with_lagged_information": "This output is a time-resolved sequence of consecutive windows at one configured lag. lagged_information pools the entire retained recording separately for every requested lag; the values are not interchangeable.",
        },
        "window_seconds": float(window_seconds),
        "mutual_information_lag_ms": float(mutual_information_lag_ms),
        "mutual_information_lag_samples": int(lag_samples),
        "global_state_probability": {
            name: float(global_probability[index]) for index, name in enumerate(state_names)
        },
        "rows": rows,
        "summary": {
            "mean_self_information_bits": float(self_information.mean()),
            "mean_window_state_entropy_bits": float(np.mean([row["state_entropy_bits"] for row in rows])),
            "mean_lagged_mutual_information_bits": float(np.mean(usable_mutual_information)) if usable_mutual_information else None,
            "window_count": int(len(rows)),
        },
    }


def write_microstate_information_csv(information_dynamics: dict, path: str | Path) -> Path:
    """Write the information-dynamics curve in a renderer-independent CSV."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "start_sec",
        "end_sec",
        "sample_count",
        "mean_self_information_bits",
        "state_entropy_bits",
        "lagged_mutual_information_bits",
        "lagged_normalized_mutual_information",
        "lagged_pair_count",
    ]
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(information_dynamics["rows"])
    return destination


def write_microstate_transition_counts_csv(
    direct_transition_counts: dict,
    path: str | Path,
) -> Path:
    """Write actual state-change boundary counts, including zero-count pairs."""
    return _write_rows_csv(
        direct_transition_counts["rows"],
        path,
        [
            "from_state",
            "to_state",
            "count",
            "percent_of_outgoing",
            "percent_of_all_transitions",
        ],
    )


def write_microstate_lagged_information_csv(
    lagged_information: dict,
    path: str | Path,
) -> Path:
    """Write the full-record, per-lag information table for reuse outside reports."""
    return _write_rows_csv(
        lagged_information["rows"],
        path,
        [
            "requested_lag_ms",
            "lag_samples",
            "actual_lag_ms",
            "pair_count",
            "mutual_information_bits",
            "normalized_mutual_information",
            "mean_conditional_self_information_bits",
            "mean_marginal_self_information_bits",
        ],
    )


def write_microstate_state_self_information_csv(
    lagged_information: dict,
    path: str | Path,
) -> Path:
    """Write full-record state occupancy and its corresponding self-information."""
    return _write_rows_csv(
        lagged_information["state_self_information"],
        path,
        ["state", "sample_count", "occupancy_probability", "self_information_bits"],
    )


def write_microstate_timeline_mapping_csv(timeline_mapping: dict, path: str | Path) -> Path:
    """Write only verified retained-to-source intervals; no discarded gap is imputed."""
    return _write_rows_csv(
        timeline_mapping["retained_intervals"],
        path,
        [
            "analysis_start_sec",
            "analysis_end_sec",
            "source_start_sec",
            "source_end_sec",
            "source_epoch_index",
        ],
    )


def write_microstate_source_segments_csv(
    source_timeline_segments: list[dict],
    path: str | Path,
) -> Path:
    """Write state segments mapped to verified source time when such timing exists."""
    return _write_rows_csv(
        source_timeline_segments,
        path,
        [
            "state",
            "analysis_start_sec",
            "analysis_end_sec",
            "source_start_sec",
            "source_end_sec",
            "source_epoch_index",
        ],
    )


def _write_rows_csv(rows: list[dict], path: str | Path, fieldnames: list[str]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return destination


def _discrete_mutual_information_bits(before: np.ndarray, after: np.ndarray, state_count: int) -> float:
    """Return discrete mutual information for two equally sized label vectors."""
    joint_counts = np.zeros((state_count, state_count), dtype=float)
    np.add.at(joint_counts, (before, after), 1)
    joint_probability = joint_counts / before.size
    probability_before = joint_probability.sum(axis=1, keepdims=True)
    probability_after = joint_probability.sum(axis=0, keepdims=True)
    nonzero = joint_probability > 0
    return float(
        np.sum(
            joint_probability[nonzero]
            * np.log2((joint_probability / np.maximum(probability_before * probability_after, np.finfo(float).tiny))[nonzero])
        )
    )


def build_microstate_timeline_mapping(
    sample_count: int,
    sfreq: float,
    *,
    source_epoch_rows: list[dict] | None = None,
) -> dict:
    """Describe how concatenated retained samples map to real source time.

    ``run_auto_qc`` returns a concatenated retained record.  Passing its
    ``quality_control['epochs']`` rows makes the original time coordinates
    recoverable without inventing data in rejected gaps.  Without those rows,
    only the honest retained-analysis time coordinate is available.
    """
    if sample_count < 0:
        raise ValueError("sample_count must be non-negative")
    if sfreq <= 0:
        raise ValueError("sfreq must be positive")

    analysis_duration_sec = float(sample_count / sfreq)
    if source_epoch_rows is None:
        return {
            "scope": "retained_analysis_time_only",
            "source_time_available": False,
            "analysis_duration_sec": analysis_duration_sec,
            "source_duration_sec": None,
            "retained_intervals": [
                {
                    "analysis_start_sec": 0.0,
                    "analysis_end_sec": analysis_duration_sec,
                    "source_start_sec": None,
                    "source_end_sec": None,
                    "source_epoch_index": None,
                }
            ] if sample_count else [],
            "unretained_source_intervals": [],
            "boundary": "Source timing was not supplied. Do not place this sequence on an original-record time axis or infer gaps.",
        }

    normalised_rows = _validate_source_epoch_rows(source_epoch_rows, sfreq)
    retained_rows = [row for row in normalised_rows if row["retained"]]
    expected_samples = sum(row["sample_count"] for row in retained_rows)
    if expected_samples != sample_count:
        raise ValueError(
            "retained source epochs contain "
            f"{expected_samples} samples, but the microstate sequence contains {sample_count}; "
            "a source-time mapping cannot be inferred."
        )

    analysis_cursor = 0
    retained_intervals = []
    for row in retained_rows:
        next_cursor = analysis_cursor + row["sample_count"]
        retained_intervals.append(
            {
                "analysis_start_sec": float(analysis_cursor / sfreq),
                "analysis_end_sec": float(next_cursor / sfreq),
                "source_start_sec": row["start_sec"],
                "source_end_sec": row["end_sec"],
                "source_epoch_index": row["epoch_index"],
            }
        )
        analysis_cursor = next_cursor

    return {
        "scope": "retained_analysis_to_source_time",
        "source_time_available": True,
        "analysis_duration_sec": analysis_duration_sec,
        "source_duration_sec": float(max(row["end_sec"] for row in normalised_rows)) if normalised_rows else 0.0,
        "retained_intervals": retained_intervals,
        "unretained_source_intervals": [
            {
                "source_start_sec": row["start_sec"],
                "source_end_sec": row["end_sec"],
                "source_epoch_index": row["epoch_index"],
            }
            for row in normalised_rows
            if not row["retained"]
        ],
        "boundary": "Only retained intervals have labels. Rejected source intervals remain gaps and are never filled with inferred microstate labels.",
    }


def map_microstate_segments_to_source_time(
    segments: list[dict],
    timeline_mapping: dict,
) -> list[dict]:
    """Split labelled segments at verified source-time discontinuities.

    The return value can drive a raster with true gaps.  It never bridges a
    rejected epoch and returns retained-analysis coordinates only when no
    source epoch table was supplied.
    """
    retained_intervals = timeline_mapping.get("retained_intervals", [])
    output = []
    for segment in segments:
        for interval in retained_intervals:
            overlap_start = max(segment["start_sec"], interval["analysis_start_sec"])
            overlap_end = min(segment["end_sec"], interval["analysis_end_sec"])
            if overlap_end <= overlap_start:
                continue
            source_start = source_end = None
            if interval["source_start_sec"] is not None:
                source_start = float(
                    interval["source_start_sec"]
                    + (overlap_start - interval["analysis_start_sec"])
                )
                source_end = float(
                    interval["source_start_sec"]
                    + (overlap_end - interval["analysis_start_sec"])
                )
            output.append(
                {
                    "state": segment["state"],
                    "analysis_start_sec": float(overlap_start),
                    "analysis_end_sec": float(overlap_end),
                    "source_start_sec": source_start,
                    "source_end_sec": source_end,
                    "source_epoch_index": interval["source_epoch_index"],
                }
            )
    return output


def _validate_source_epoch_rows(source_epoch_rows: list[dict], sfreq: float) -> list[dict]:
    normalised_rows = []
    previous_end = -np.inf
    for fallback_index, row in enumerate(source_epoch_rows):
        required = {"start_sec", "end_sec", "retained"}
        missing = required.difference(row)
        if missing:
            raise ValueError(f"source_epoch_rows[{fallback_index}] is missing {sorted(missing)}")
        start_sec, end_sec = float(row["start_sec"]), float(row["end_sec"])
        if not np.isfinite(start_sec) or not np.isfinite(end_sec) or end_sec <= start_sec:
            raise ValueError(f"source_epoch_rows[{fallback_index}] must have finite increasing times")
        if start_sec < previous_end - 1 / sfreq:
            raise ValueError("source_epoch_rows must be ordered and non-overlapping")
        sample_count = round((end_sec - start_sec) * sfreq)
        if sample_count <= 0 or not np.isclose(sample_count / sfreq, end_sec - start_sec, atol=1 / sfreq / 1000):
            raise ValueError(
                f"source_epoch_rows[{fallback_index}] duration is not representable at the supplied sampling rate"
            )
        normalised_rows.append(
            {
                "epoch_index": int(row.get("epoch_index", fallback_index)),
                "start_sec": start_sec,
                "end_sec": end_sec,
                "retained": bool(row["retained"]),
                "sample_count": int(sample_count),
            }
        )
        previous_end = end_sec
    return normalised_rows


def _validate_and_index_labels(
    sample_labels: list[str], state_names: list[str], sfreq: float
) -> tuple[np.ndarray, np.ndarray]:
    if not sample_labels:
        raise ValueError("sample_labels must contain at least one label")
    if not state_names:
        raise ValueError("state_names must contain at least one state")
    if sfreq <= 0:
        raise ValueError("sfreq must be positive")
    index_by_name = {name: index for index, name in enumerate(state_names)}
    if len(index_by_name) != len(state_names):
        raise ValueError("state_names must be unique")
    try:
        labels = np.asarray([index_by_name[name] for name in sample_labels], dtype=int)
    except KeyError as error:
        raise ValueError(f"sample_labels contains unknown state {error.args[0]!r}") from error
    return labels, np.bincount(labels, minlength=len(state_names)) / labels.size


def _merge_short_segments(labels: np.ndarray, minimum: int) -> np.ndarray:
    labels = labels.copy()
    changed = True
    while changed:
        changed = False
        edges = np.flatnonzero(np.diff(labels) != 0) + 1
        starts = np.r_[0, edges]
        ends = np.r_[edges, labels.size]
        for start, end in zip(starts, ends):
            if end - start >= minimum or (start == 0 and end == labels.size):
                continue
            replacement = labels[end] if end < labels.size else labels[start - 1]
            labels[start:end] = replacement
            changed = True
            break
    return labels


def _temporal_parameters(labels, names, sfreq, similarity, explained):
    result = []
    for index, name in enumerate(names):
        mask = labels == index
        starts = np.flatnonzero(np.diff(np.r_[False, mask, False].astype(int)) == 1)
        ends = np.flatnonzero(np.diff(np.r_[False, mask, False].astype(int)) == -1)
        durations = (ends - starts) * 1000 / sfreq
        result.append({"state": name, "mean_correlation": float(np.mean(np.abs(similarity[index, mask]))) if mask.any() else None, "gev_percent": float(100 * explained[mask].sum() / max(explained.sum(), np.finfo(float).eps)), "occurrences_per_sec": float(len(starts) / (labels.size / sfreq)), "time_coverage_percent": float(100 * mask.mean()), "mean_duration_ms": float(durations.mean()) if durations.size else None})
    return result


def _transition_matrix(labels, names):
    matrix = np.zeros((len(names), len(names)), dtype=int)
    for before, after in zip(labels[:-1], labels[1:]):
        if before != after:
            matrix[before, after] += 1
    return {"states": names, "counts": matrix.tolist(), "row_normalized_percent": (100 * matrix / np.maximum(matrix.sum(axis=1, keepdims=True), 1)).tolist()}


def _direct_transition_counts(transitions: dict) -> dict:
    """Flatten the observed state-change matrix into a lossless tabular form."""
    states = transitions["states"]
    counts = np.asarray(transitions["counts"], dtype=int)
    total = int(counts.sum())
    rows = []
    for from_index, from_state in enumerate(states):
        outgoing_count = int(counts[from_index].sum())
        for to_index, to_state in enumerate(states):
            if from_index == to_index:
                continue
            count = int(counts[from_index, to_index])
            rows.append(
                {
                    "from_state": from_state,
                    "to_state": to_state,
                    "count": count,
                    "percent_of_outgoing": float(100 * count / outgoing_count) if outgoing_count else 0.0,
                    "percent_of_all_transitions": float(100 * count / total) if total else 0.0,
                }
            )
    return {
        "scope": "full_retained_recording_segment_boundaries",
        "definition": "Counts are observed state changes between adjacent merged microstate segments. Self-transitions are omitted by definition.",
        "total_transition_count": total,
        "rows": rows,
    }


def _segments(labels: np.ndarray, names: list[str], sfreq: float) -> list[dict]:
    """Return every contiguous state run, preserving full-recording timing."""
    edges = np.flatnonzero(np.diff(labels) != 0) + 1
    starts = np.r_[0, edges]
    ends = np.r_[edges, labels.size]
    return [
        {
            "state": names[int(labels[start])],
            "start_sample": int(start),
            "end_sample_exclusive": int(end),
            "start_sec": float(start / sfreq),
            "end_sec": float(end / sfreq),
            "duration_ms": float(1000 * (end - start) / sfreq),
        }
        for start, end in zip(starts, ends)
    ]


def _duration_summary(segments: list[dict], names: list[str]) -> list[dict]:
    result = []
    for name in names:
        durations = np.asarray([segment["duration_ms"] for segment in segments if segment["state"] == name], dtype=float)
        result.append(
            {
                "state": name,
                "segment_count": int(durations.size),
                "mean_duration_ms": float(durations.mean()) if durations.size else None,
                "median_duration_ms": float(np.median(durations)) if durations.size else None,
                "standard_deviation_ms": float(durations.std()) if durations.size else None,
                "p95_duration_ms": float(np.quantile(durations, 0.95)) if durations.size else None,
                "maximum_duration_ms": float(durations.max()) if durations.size else None,
            }
        )
    return result


def _per_second_coverage(labels: np.ndarray, names: list[str], sfreq: float) -> list[dict]:
    """Summarize state occupancy in each elapsed second without truncating the last second."""
    starts = np.arange(0, labels.size, max(1, round(sfreq)), dtype=int)
    coverage = []
    for start in starts:
        end = min(labels.size, start + max(1, round(sfreq)))
        window = labels[start:end]
        fractions = {name: float(np.mean(window == index)) for index, name in enumerate(names)}
        coverage.append(
            {
                "start_sec": float(start / sfreq),
                "end_sec": float(end / sfreq),
                "state_coverage_fraction": fractions,
                "dominant_state": names[int(np.argmax(np.bincount(window, minlength=len(names))))],
            }
        )
    return coverage


def _outgoing_transitions(transitions: dict) -> list[dict]:
    counts = np.asarray(transitions["counts"], dtype=int)
    names = transitions["states"]
    result = []
    for index, name in enumerate(names):
        total = int(counts[index].sum())
        destinations = [
            {
                "to_state": names[target],
                "count": int(counts[index, target]),
                "percent_of_outgoing": float(100 * counts[index, target] / total) if total else 0.0,
            }
            for target in range(len(names))
            if target != index
        ]
        result.append({"from_state": name, "outgoing_transition_count": total, "destinations": destinations})
    return result


def _sequence_summary(labels: np.ndarray, names: list[str], segments: list[dict]) -> dict:
    occupancy = np.bincount(labels, minlength=len(names)) / max(labels.size, 1)
    segment_labels = np.asarray([names.index(segment["state"]) for segment in segments], dtype=int)
    segment_occupancy = np.bincount(segment_labels, minlength=len(names)) / max(segment_labels.size, 1)
    return {
        "sample_label_shannon_entropy_bits": _shannon_entropy(occupancy),
        "segment_label_shannon_entropy_bits": _shannon_entropy(segment_occupancy),
        "state_switch_count": int(max(0, len(segments) - 1)),
        "segment_count": int(len(segments)),
        "mean_segment_duration_ms": float(np.mean([segment["duration_ms"] for segment in segments])) if segments else None,
    }


def _shannon_entropy(probability: np.ndarray) -> float:
    probability = np.asarray(probability, dtype=float)
    positive = probability[probability > 0]
    return float(-np.sum(positive * np.log2(positive)))
