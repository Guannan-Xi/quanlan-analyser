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
    timeline_mapping = build_microstate_timeline_mapping(
        labels.size,
        cleaned.info["sfreq"],
        source_epoch_rows=source_epoch_rows,
    )
    continuous_blocks = _source_contiguous_blocks(
        labels.size,
        cleaned.info["sfreq"],
        timeline_mapping,
    )
    minimum_segment_samples = max(
        1,
        round(config.minimum_segment_ms * cleaned.info["sfreq"] / 1000),
    )
    for block in continuous_blocks["blocks"]:
        start = block["start_sample"]
        end = block["end_sample_exclusive"]
        labels[start:end] = _merge_short_segments(labels[start:end], minimum_segment_samples)
    explained = np.max(np.abs(similarity), axis=0) ** 2
    names = [chr(ord("A") + index) for index in range(config.states)]
    block_ranges = [
        (block["start_sample"], block["end_sample_exclusive"])
        for block in continuous_blocks["blocks"]
    ]
    parameters = _temporal_parameters(
        labels,
        names,
        cleaned.info["sfreq"],
        similarity,
        explained,
        blocks=block_ranges,
    )
    sequence_dynamics = compute_microstate_sequence_dynamics(
        [names[index] for index in labels],
        names,
        cleaned.info["sfreq"],
        timeline_mapping=timeline_mapping,
    )
    jump_chain = sequence_dynamics["jump_chain_syntax"]
    transitions = {
        "states": names,
        "counts": jump_chain["observed_counts"],
        "row_normalized_percent": jump_chain["row_normalized_percent"],
    }
    segments = sequence_dynamics["dwell_time"]["segments"]
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
        timeline_mapping=timeline_mapping,
    )
    lagged_information = compute_microstate_lagged_information(
        [names[index] for index in labels],
        names,
        cleaned.info["sfreq"],
        start_ms=config.information_lag_start_ms,
        stop_ms=config.information_lag_stop_ms,
        step_ms=config.information_lag_step_ms,
        timeline_mapping=timeline_mapping,
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
        "duration_summary": sequence_dynamics["duration_summary"]["per_state"],
        "per_second_coverage": sequence_dynamics["per_second_distribution_summary"]["windows"],
        "outgoing_transitions": _outgoing_transitions(transitions),
        "sequence": _sequence_summary(
            labels,
            names,
            segments,
            state_switch_count=jump_chain["eligible_transition_count"],
        ),
        "sequence_dynamics": sequence_dynamics,
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
    timeline_mapping: dict | None = None,
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
    continuous_blocks = _source_contiguous_blocks(labels.size, sfreq, timeline_mapping)
    block_ranges = [
        (block["start_sample"], block["end_sample_exclusive"])
        for block in continuous_blocks["blocks"]
    ]

    requested_lags = np.arange(start_ms, stop_ms + step_ms / 2, step_ms, dtype=float)
    rows = []
    for requested_lag_ms in requested_lags:
        lag_samples = max(1, round(requested_lag_ms * sfreq / 1000))
        actual_lag_ms = float(1000 * lag_samples / sfreq)
        eligible_pairs = [
            (
                labels[start : end - lag_samples],
                labels[start + lag_samples : end],
            )
            for start, end in block_ranges
            if end - start > lag_samples
        ]
        if not eligible_pairs:
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

        before = np.concatenate([pair[0] for pair in eligible_pairs])
        after = np.concatenate([pair[1] for pair in eligible_pairs])
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
        "sequence_domain": continuous_blocks["sequence_domain"],
        "continuous_block_count": continuous_blocks["block_count"],
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
                "self_information_bits": (
                    float(-np.log2(global_probability[index]))
                    if global_probability[index] > 0
                    else None
                ),
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
    timeline_mapping: dict | None = None,
) -> dict:
    """Calculate full-record microstate self-information and short-time MI.

    Self-information is ``-log2(p(state))``, where ``p(state)`` is estimated
    from the complete labelled recording.  The curve reports its mean in each
    consecutive time window.  Lagged mutual information is calculated within
    the same window between labels separated by the configured lag; it
    summarizes short-term state-sequence predictability rather than a
    connectivity measure.
    """
    labels, global_probability = _validate_and_index_labels(sample_labels, state_names, sfreq)
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")
    if mutual_information_lag_ms <= 0:
        raise ValueError("mutual_information_lag_ms must be positive")

    state_count = len(state_names)
    self_information = -np.log2(np.maximum(global_probability[labels], np.finfo(float).tiny))
    window_samples = max(1, round(window_seconds * sfreq))
    lag_samples = max(1, round(mutual_information_lag_ms * sfreq / 1000))
    continuous_blocks = _source_contiguous_blocks(labels.size, sfreq, timeline_mapping)
    rows = []
    for block in continuous_blocks["blocks"]:
        block_start = block["start_sample"]
        block_end = block["end_sample_exclusive"]
        for start in range(block_start, block_end, window_samples):
            end = min(block_end, start + window_samples)
            window = labels[start:end]
            if window.size > lag_samples:
                before, after = window[:-lag_samples], window[lag_samples:]
                mutual_information = _discrete_mutual_information_bits(before, after, state_count)
                entropy_before = _shannon_entropy(
                    np.bincount(before, minlength=state_count) / before.size
                )
                entropy_after = _shannon_entropy(
                    np.bincount(after, minlength=state_count) / after.size
                )
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
                    "block_index": block["block_index"],
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
        "sequence_domain": continuous_blocks["sequence_domain"],
        "continuous_block_count": continuous_blocks["block_count"],
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


def compute_microstate_sequence_dynamics(
    sample_labels: list[str],
    state_names: list[str],
    sfreq: float,
    *,
    timeline_mapping: dict | None = None,
    block_orders: tuple[int, ...] = (1, 2, 3, 4),
) -> dict:
    """Compute gap-aware microstate sequence statistics over retained samples.

    Every adjacency-based estimator is reset at source-time discontinuities.
    When source timing is unavailable, the retained sequence is explicitly
    treated as one block because no source gaps can be reconstructed.
    """
    labels, _ = _validate_and_index_labels(sample_labels, state_names, sfreq)
    orders = _validate_block_orders(block_orders)
    continuous_blocks = _source_contiguous_blocks(labels.size, sfreq, timeline_mapping)
    block_ranges = [
        (block["start_sample"], block["end_sample_exclusive"])
        for block in continuous_blocks["blocks"]
    ]
    segments = _segments(labels, list(state_names), sfreq, blocks=block_ranges)
    sample_markov = _sample_markov_dynamics(labels, list(state_names), block_ranges)
    jump_chain = _jump_chain_dynamics(segments, list(state_names))
    block_entropy = _block_entropy_dynamics(labels, list(state_names), block_ranges, orders)
    lempel_ziv = _lempel_ziv_dynamics(labels, list(state_names), block_ranges)
    duration_summary, empirical_curves = _dwell_duration_statistics(
        segments,
        list(state_names),
        sfreq,
    )
    per_second_distribution = _per_second_distribution(
        labels,
        list(state_names),
        sfreq,
        block_ranges,
        segments,
    )
    active_states = [
        state_names[index]
        for index in np.flatnonzero(np.bincount(labels, minlength=len(state_names)))
    ]
    return {
        "sequence_domain": continuous_blocks["sequence_domain"],
        "method": "All adjacency, run, word, and parsing operations reset at source-contiguous sample-block boundaries.",
        "status": (
            "ok"
            if continuous_blocks["source_time_available"]
            else "ok_source_continuity_unavailable_single_block_assumption"
        ),
        "sample_count": int(labels.size),
        "state_names": list(state_names),
        "active_states": active_states,
        "eligible_counts": {
            "samples": int(labels.size),
            "sample_adjacent_pairs": sample_markov["eligible_pair_count"],
            "jump_chain_segments": jump_chain["eligible_segment_count"],
            "jump_chain_transitions": jump_chain["eligible_transition_count"],
            "dwell_segments": int(len(segments)),
            "per_second_windows": per_second_distribution["eligible_window_count"],
        },
        "continuous_blocks": continuous_blocks,
        "sample_markov": sample_markov,
        "jump_chain_syntax": jump_chain,
        "block_entropy": block_entropy,
        "lempel_ziv": lempel_ziv,
        "dwell_time": {
            "sequence_domain": continuous_blocks["sequence_domain"],
            "method": "Maximal equal-label runs are segmented independently in each continuous block; boundary flags are descriptive censoring markers.",
            "status": "ok",
            "eligible_segment_count": int(len(segments)),
            "segments": segments,
            "empirical_curves": empirical_curves,
            "curve_definition": "Empirical ECDF F(t)=P(D<=t) and survival S(t)=P(D>t); this is descriptive and is not Kaplan-Meier inference.",
        },
        "duration_summary": {
            "sequence_domain": "dwell_runs_within_source_contiguous_blocks",
            "method": "Per-state descriptive duration statistics pool block-delimited dwell runs in samples, milliseconds, and seconds.",
            "status": "ok",
            "eligible_segment_count": int(len(segments)),
            "per_state": duration_summary,
        },
        "per_second_distribution_summary": per_second_distribution,
    }


def _validate_block_orders(block_orders) -> tuple[int, ...]:
    try:
        orders = tuple(block_orders)
    except TypeError as error:
        raise ValueError("block_orders must be a non-empty iterable of positive integers") from error
    if not orders or any(isinstance(order, bool) or not isinstance(order, (int, np.integer)) or order <= 0 for order in orders):
        raise ValueError("block_orders must be a non-empty iterable of positive integers")
    if len(set(int(order) for order in orders)) != len(orders):
        raise ValueError("block_orders must not contain duplicates")
    return tuple(sorted(int(order) for order in orders))


def _sample_markov_dynamics(
    labels: np.ndarray,
    state_names: list[str],
    block_ranges: list[tuple[int, int]],
) -> dict:
    state_count = len(state_names)
    counts = np.zeros((state_count, state_count), dtype=int)
    for start, end in block_ranges:
        if end - start > 1:
            np.add.at(counts, (labels[start : end - 1], labels[start + 1 : end]), 1)
    row_totals = counts.sum(axis=1)
    probabilities = [
        (counts[index] / row_totals[index]).astype(float).tolist()
        if row_totals[index] > 0
        else [None] * state_count
        for index in range(state_count)
    ]
    row_entropies = [
        _shannon_entropy(counts[index] / row_totals[index])
        if row_totals[index] > 0
        else None
        for index in range(state_count)
    ]
    eligible_pair_count = int(row_totals.sum())
    empirical_entropy_rate = (
        float(
            sum(
                row_totals[index] * row_entropies[index]
                for index in range(state_count)
                if row_entropies[index] is not None
            )
            / eligible_pair_count
        )
        if eligible_pair_count
        else None
    )
    active_indices = np.flatnonzero(np.bincount(labels, minlength=state_count)).tolist()
    stationary, stationary_status, reason = _unique_stationary_distribution(
        counts,
        active_indices,
    )
    stationary_entropy_rate = None
    if stationary is not None:
        stationary_entropy_rate = float(
            sum(
                stationary[index] * (row_entropies[index] or 0.0)
                for index in range(state_count)
            )
        )
    return {
        "sequence_domain": "within_source_contiguous_sample_blocks",
        "method": "Empirical first-order sample-label Markov chain including self-transitions.",
        "status": "ok" if eligible_pair_count else "not_estimable",
        "not_estimable_reason": None if eligible_pair_count else "no_within_block_adjacent_sample_pairs",
        "eligible_sample_count": int(labels.size),
        "eligible_pair_count": eligible_pair_count,
        "active_support": [state_names[index] for index in active_indices],
        "states": state_names,
        "counts": counts.tolist(),
        "row_totals": row_totals.astype(int).tolist(),
        "transition_matrix": probabilities,
        "per_state_transition_entropy_bits_per_sample": [
            {
                "state": state_names[index],
                "outgoing_pair_count": int(row_totals[index]),
                "entropy_bits_per_sample": row_entropies[index],
                "status": "ok" if row_entropies[index] is not None else "not_estimable_zero_outdegree",
            }
            for index in range(state_count)
        ],
        "empirical_first_order_entropy_rate_bits_per_sample": empirical_entropy_rate,
        "stationary_distribution": (
            {state_names[index]: float(stationary[index]) for index in range(state_count)}
            if stationary is not None
            else None
        ),
        "stationary_status": stationary_status,
        "stationary_not_estimable_reason": reason,
        "stationary_weighted_entropy_rate_bits_per_sample": stationary_entropy_rate,
    }


def _unique_stationary_distribution(
    counts: np.ndarray,
    active_indices: list[int],
) -> tuple[np.ndarray | None, str, str | None]:
    if not active_indices:
        return None, "not_estimable", "no_active_states"
    row_totals = counts.sum(axis=1)
    if any(row_totals[index] == 0 for index in active_indices):
        return None, "not_estimable", "active_state_has_zero_outdegree"
    active = np.asarray(active_indices, dtype=int)
    probability = counts[np.ix_(active, active)] / row_totals[active, None]
    adjacency = probability > 0

    def reachable(origin: int) -> set[int]:
        seen = {origin}
        pending = [origin]
        while pending:
            current = pending.pop()
            for target in np.flatnonzero(adjacency[current]):
                target = int(target)
                if target not in seen:
                    seen.add(target)
                    pending.append(target)
        return seen

    reachability = [reachable(index) for index in range(len(active_indices))]
    classes = []
    assigned = set()
    for index in range(len(active_indices)):
        if index in assigned:
            continue
        component = {
            target
            for target in range(len(active_indices))
            if target in reachability[index] and index in reachability[target]
        }
        classes.append(component)
        assigned.update(component)
    closed_classes = [
        component
        for component in classes
        if all(
            not any(adjacency[index, target] for target in range(len(active_indices)) if target not in component)
            for index in component
        )
    ]
    if len(closed_classes) != 1:
        return None, "not_estimable", "multiple_closed_communicating_classes"
    closed = sorted(closed_classes[0])
    closed_probability = probability[np.ix_(closed, closed)]
    coefficient = np.vstack(
        [closed_probability.T - np.eye(len(closed)), np.ones((1, len(closed)))]
    )
    target = np.r_[np.zeros(len(closed)), 1.0]
    solution = np.linalg.lstsq(coefficient, target, rcond=None)[0]
    solution[np.abs(solution) < 1e-12] = 0.0
    if np.any(solution < 0) or solution.sum() <= 0:
        return None, "not_estimable", "stationary_linear_solution_invalid"
    solution = solution / solution.sum()
    stationary = np.zeros(counts.shape[0], dtype=float)
    for local_index, probability_value in zip(closed, solution):
        stationary[active_indices[local_index]] = probability_value
    return stationary, "unique", None


def _jump_chain_dynamics(segments: list[dict], state_names: list[str]) -> dict:
    state_count = len(state_names)
    index_by_name = {name: index for index, name in enumerate(state_names)}
    segment_indices = np.asarray(
        [index_by_name[segment["state"]] for segment in segments],
        dtype=int,
    )
    observed = np.zeros((state_count, state_count), dtype=int)
    by_block = {}
    for segment, state_index in zip(segments, segment_indices):
        by_block.setdefault(segment["block_index"], []).append(int(state_index))
    for block_states in by_block.values():
        for before, after in zip(block_states[:-1], block_states[1:]):
            observed[before, after] += 1
    segment_counts = np.bincount(segment_indices, minlength=state_count)
    q = segment_counts / max(segment_indices.size, 1)
    row_totals = observed.sum(axis=1)
    expected_probabilities = [[None] * state_count for _ in range(state_count)]
    expected_counts = [[None] * state_count for _ in range(state_count)]
    raw_residuals = [[None] * state_count for _ in range(state_count)]
    pearson_residuals = [[None] * state_count for _ in range(state_count)]
    cell_status = [["structural_zero"] * state_count for _ in range(state_count)]
    cells = []
    has_zero_expected = False
    for from_index, from_state in enumerate(state_names):
        denominator = 1.0 - q[from_index]
        for to_index, to_state in enumerate(state_names):
            if from_index == to_index:
                cells.append(
                    {
                        "from_state": from_state,
                        "to_state": to_state,
                        "structural_zero": True,
                        "observed_count": 0,
                        "expected_conditional_probability": None,
                        "expected_count": None,
                        "raw_residual": None,
                        "pearson_residual": None,
                        "status": "structural_zero",
                    }
                )
                continue
            expected_probability = float(q[to_index] / denominator) if denominator > 0 else None
            expected = (
                float(row_totals[from_index] * expected_probability)
                if expected_probability is not None
                else None
            )
            expected_probabilities[from_index][to_index] = expected_probability
            expected_counts[from_index][to_index] = expected
            if expected is not None and expected > 0:
                raw = float(observed[from_index, to_index] - expected)
                pearson = float(raw / np.sqrt(expected))
                raw_residuals[from_index][to_index] = raw
                pearson_residuals[from_index][to_index] = pearson
                cell_status[from_index][to_index] = "ok"
            else:
                raw = pearson = None
                cell_status[from_index][to_index] = "not_estimable_expected_zero"
                has_zero_expected = True
            cells.append(
                {
                    "from_state": from_state,
                    "to_state": to_state,
                    "structural_zero": False,
                    "observed_count": int(observed[from_index, to_index]),
                    "expected_conditional_probability": expected_probability,
                    "expected_count": expected,
                    "raw_residual": raw,
                    "pearson_residual": pearson,
                    "status": cell_status[from_index][to_index],
                }
            )
    eligible_transition_count = int(observed.sum())
    if not eligible_transition_count:
        status = "not_estimable"
        reason = "no_within_block_jump_chain_transitions"
    else:
        status = "ok_with_zero_expected_cells" if has_zero_expected else "ok"
        reason = None
    return {
        "sequence_domain": "run_collapsed_within_source_contiguous_blocks",
        "method": "Observed jump-chain transitions versus an independence expectation with structural-zero diagonal, P0(j|i)=q_j/(1-q_i).",
        "status": status,
        "not_estimable_reason": reason,
        "states": state_names,
        "eligible_segment_count": int(segment_indices.size),
        "eligible_transition_count": eligible_transition_count,
        "segment_state_frequency_q": {
            state_names[index]: float(q[index]) for index in range(state_count)
        },
        "observed_counts": observed.tolist(),
        "row_totals": row_totals.astype(int).tolist(),
        "row_normalized_percent": (
            100 * observed / np.maximum(row_totals[:, None], 1)
        ).astype(float).tolist(),
        "expected_conditional_probabilities": expected_probabilities,
        "expected_counts": expected_counts,
        "raw_residuals": raw_residuals,
        "pearson_residuals": pearson_residuals,
        "cell_status": cell_status,
        "cells": cells,
    }


def _block_entropy_dynamics(
    labels: np.ndarray,
    state_names: list[str],
    block_ranges: list[tuple[int, int]],
    orders: tuple[int, ...],
) -> dict:
    entropy_by_order = {}
    counts_by_order = {}
    eligible_by_order = {}
    for order in range(1, max(orders) + 1):
        word_counts = {}
        eligible = 0
        for start, end in block_ranges:
            block = labels[start:end]
            for offset in range(max(0, block.size - order + 1)):
                word = tuple(int(value) for value in block[offset : offset + order])
                word_counts[word] = word_counts.get(word, 0) + 1
                eligible += 1
        counts_by_order[order] = word_counts
        eligible_by_order[order] = eligible
        entropy_by_order[order] = (
            _shannon_entropy(np.asarray(list(word_counts.values()), dtype=float) / eligible)
            if eligible
            else None
        )
    rows = []
    for order in orders:
        entropy = entropy_by_order[order]
        previous_entropy = 0.0 if order == 1 else entropy_by_order[order - 1]
        vocabulary = [
            [state_names[index] for index in word]
            for word in sorted(counts_by_order[order])
        ]
        rows.append(
            {
                "L": order,
                "status": "ok" if entropy is not None else "not_estimable_no_eligible_words",
                "eligible_word_count": int(eligible_by_order[order]),
                "observed_vocabulary": vocabulary,
                "observed_vocabulary_size": int(len(vocabulary)),
                "effective_word_count": float(2**entropy) if entropy is not None else None,
                "H_L_bits": entropy,
                "H_L_per_symbol_bits": float(entropy / order) if entropy is not None else None,
                "conditional_increment_bits": (
                    float(entropy - previous_entropy)
                    if entropy is not None and previous_entropy is not None
                    else None
                ),
            }
        )
    return {
        "sequence_domain": "overlapping_non_circular_words_within_source_contiguous_blocks",
        "method": "Words are counted separately within each block and then pooled; no word wraps or crosses a block boundary.",
        "status": "ok" if any(row["eligible_word_count"] for row in rows) else "not_estimable",
        "orders": rows,
    }


def _lempel_ziv_dynamics(
    labels: np.ndarray,
    state_names: list[str],
    block_ranges: list[tuple[int, int]],
) -> dict:
    active_count = int(np.count_nonzero(np.bincount(labels, minlength=len(state_names))))
    per_block = []
    total_phrases = 0
    short_block_count = 0
    for block_index, (start, end) in enumerate(block_ranges):
        block = labels[start:end]
        phrase_count = _lz76_exhaustive_phrase_count(block)
        total_phrases += phrase_count
        normalized, status = _lz76_normalized_value(phrase_count, int(block.size), active_count)
        if block.size < 2:
            short_block_count += 1
        per_block.append(
            {
                "block_index": block_index,
                "sample_count_n": int(block.size),
                "raw_phrase_count_c_n": int(phrase_count),
                "normalized_value": normalized,
                "status": status,
            }
        )
    normalized, normalization_status = _lz76_normalized_value(
        total_phrases,
        int(labels.size),
        active_count,
    )
    return {
        "sequence_domain": "block_reset_multisymbol_lz76_exhaustive_parsing",
        "method": "LZ76 exhaustive parsing is restarted for every continuous block; phrase traces are intentionally not retained.",
        "status": normalization_status,
        "eligible_sample_count": int(labels.size),
        "block_count": int(len(block_ranges)),
        "short_block_count": int(short_block_count),
        "K_active": active_count,
        "raw_phrase_count": int(total_phrases),
        "normalization_formula": "c(n) * log_K(n) / n",
        "normalization_scope": "For the pooled value, c(n) is the sum of block-reset phrase counts and n is the total retained sample count.",
        "constant_alphabet_rule": "When K_active=1, normalized_value is defined as 0.0 because log base 1 is undefined and the sequence has no symbolic diversity.",
        "short_sequence_rule": "When n<2, normalized_value is defined as 0.0.",
        "normalized_value": normalized,
        "per_block": per_block,
    }


def _lz76_normalized_value(phrase_count: int, sample_count: int, alphabet_size: int):
    if alphabet_size == 1:
        return 0.0, "constant_alphabet_rule"
    if sample_count < 2:
        return 0.0, "short_sequence_rule"
    value = float(phrase_count * (np.log(sample_count) / np.log(alphabet_size)) / sample_count)
    return value, "ok"


def _lz76_exhaustive_phrase_count(sequence: np.ndarray) -> int:
    """Return the mult symbol LZ76 exhaustive-history phrase count."""
    values = np.asarray(sequence)
    length = int(values.size)
    if length == 0:
        return 0
    if length == 1:
        return 1
    complexity = 1
    history_index = 0
    phrase_start = 1
    match_length = 1
    longest_match = 1
    while True:
        if values[history_index + match_length - 1] == values[phrase_start + match_length - 1]:
            match_length += 1
            if phrase_start + match_length > length:
                complexity += 1
                return complexity
        else:
            longest_match = max(longest_match, match_length)
            history_index += 1
            if history_index == phrase_start:
                complexity += 1
                phrase_start += longest_match
                if phrase_start + 1 > length:
                    return complexity
                history_index = 0
                match_length = 1
                longest_match = 1
            else:
                match_length = 1


def _dwell_duration_statistics(
    segments: list[dict],
    state_names: list[str],
    sfreq: float,
) -> tuple[list[dict], list[dict]]:
    summaries = []
    curves = []
    for state in state_names:
        durations = np.asarray(
            [segment["duration_samples"] for segment in segments if segment["state"] == state],
            dtype=float,
        )
        summaries.append(_duration_summary_row(state, durations, sfreq))
        points = []
        if durations.size:
            for duration_samples in np.unique(durations):
                points.append(
                    {
                        "duration_samples": int(duration_samples),
                        "duration_ms": float(1000 * duration_samples / sfreq),
                        "duration_sec": float(duration_samples / sfreq),
                        "ecdf_probability": float(np.mean(durations <= duration_samples)),
                        "survival_probability": float(np.mean(durations > duration_samples)),
                    }
                )
        curves.append(
            {
                "state": state,
                "status": "ok" if durations.size else "not_estimable_state_unobserved",
                "eligible_duration_count": int(durations.size),
                "points": points,
            }
        )
    return summaries, curves


def _duration_summary_row(state: str, durations: np.ndarray, sfreq: float) -> dict:
    def statistic(function):
        return float(function(durations)) if durations.size else None

    result = {
        "state": state,
        "status": "ok" if durations.size else "not_estimable_state_unobserved",
        "segment_count": int(durations.size),
    }
    values = {
        "total": statistic(np.sum),
        "mean": statistic(np.mean),
        "median": statistic(np.median),
        "standard_deviation": statistic(np.std),
        "p95": statistic(lambda value: np.quantile(value, 0.95)),
        "maximum": statistic(np.max),
    }
    for name, sample_value in values.items():
        result[f"{name}_duration_samples"] = sample_value
        result[f"{name}_duration_ms"] = (
            float(1000 * sample_value / sfreq) if sample_value is not None else None
        )
        result[f"{name}_duration_sec"] = (
            float(sample_value / sfreq) if sample_value is not None else None
        )
    # Preserve established duration-summary field names.
    result["standard_deviation_ms"] = result["standard_deviation_duration_ms"]
    return result


def _per_second_distribution(
    labels: np.ndarray,
    state_names: list[str],
    sfreq: float,
    block_ranges: list[tuple[int, int]],
    segments: list[dict],
) -> dict:
    second_samples = max(1, round(sfreq))
    rows = []
    for block_index, (block_start, block_end) in enumerate(block_ranges):
        for start in range(block_start, block_end, second_samples):
            end = min(block_end, start + second_samples)
            window = labels[start:end]
            duration_sec = float(window.size / sfreq)
            coverage = {
                state: float(np.mean(window == index))
                for index, state in enumerate(state_names)
            }
            occurrences = {
                state: int(
                    sum(
                        segment["state"] == state
                        and start <= segment["start_sample"] < end
                        for segment in segments
                    )
                )
                for state in state_names
            }
            rows.append(
                {
                    "block_index": block_index,
                    "start_sec": float(start / sfreq),
                    "end_sec": float(end / sfreq),
                    "sample_count": int(window.size),
                    "window_duration_sec": duration_sec,
                    "state_coverage_fraction": coverage,
                    "state_occurrence_count": occurrences,
                    "state_occurrences_per_sec": {
                        state: float(occurrences[state] / duration_sec)
                        for state in state_names
                    },
                    "dominant_state": state_names[
                        int(np.argmax(np.bincount(window, minlength=len(state_names))))
                    ],
                }
            )
    state_summaries = []
    for state in state_names:
        coverage_values = np.asarray(
            [row["state_coverage_fraction"][state] for row in rows],
            dtype=float,
        )
        occurrence_values = np.asarray(
            [row["state_occurrences_per_sec"][state] for row in rows],
            dtype=float,
        )
        state_summaries.append(
            {
                "state": state,
                "eligible_window_count": int(len(rows)),
                "coverage_fraction_mean": float(coverage_values.mean()),
                "coverage_fraction_standard_deviation": float(coverage_values.std()),
                "occurrences_per_sec_mean": float(occurrence_values.mean()),
                "occurrences_per_sec_standard_deviation": float(occurrence_values.std()),
            }
        )
    return {
        "sequence_domain": "non_overlapping_one_second_windows_reset_at_continuous_blocks",
        "method": "Coverage and run-onset occurrence rates are computed in block-local one-second windows; partial final windows are retained and rates use their actual duration.",
        "status": "ok",
        "eligible_window_count": int(len(rows)),
        "windows": rows,
        "per_state": state_summaries,
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
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
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


def _source_contiguous_blocks(
    sample_count: int,
    sfreq: float,
    timeline_mapping: dict | None,
) -> dict:
    """Build maximal retained blocks whose source-time intervals are contiguous."""
    source_time_available = bool(
        timeline_mapping is not None and timeline_mapping.get("source_time_available")
    )
    tolerance_sec = float(1.0 / sfreq)
    if not source_time_available:
        blocks = [
            {
                "block_index": 0,
                "start_sample": 0,
                "end_sample_exclusive": int(sample_count),
                "sample_count": int(sample_count),
                "analysis_start_sec": 0.0,
                "analysis_end_sec": float(sample_count / sfreq),
                "source_start_sec": None,
                "source_end_sec": None,
                "source_epoch_indices": [],
                "left_boundary": "recording_start_or_source_unknown",
                "right_boundary": "recording_end_or_source_unknown",
            }
        ] if sample_count else []
        return {
            "sequence_domain": "retained_analysis_sequence_source_continuity_unknown_single_block",
            "method": "Source time is unavailable, so the complete retained sequence is treated as one block.",
            "status": "source_time_unavailable_single_block_assumption",
            "source_time_available": False,
            "source_continuity_tolerance_sec": None,
            "eligible_sample_count": int(sample_count),
            "block_count": int(len(blocks)),
            "blocks": blocks,
        }

    retained_intervals = timeline_mapping.get("retained_intervals")
    if not isinstance(retained_intervals, list):
        raise ValueError("timeline_mapping.retained_intervals must be a list")
    interval_rows = []
    analysis_cursor = 0
    for interval_index, interval in enumerate(retained_intervals):
        try:
            analysis_start = float(interval["analysis_start_sec"])
            analysis_end = float(interval["analysis_end_sec"])
            source_start = float(interval["source_start_sec"])
            source_end = float(interval["source_end_sec"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                f"timeline_mapping.retained_intervals[{interval_index}] has invalid coordinates"
            ) from error
        if not all(np.isfinite(value) for value in (analysis_start, analysis_end, source_start, source_end)):
            raise ValueError("timeline_mapping retained interval coordinates must be finite")
        start_sample = round(analysis_start * sfreq)
        end_sample = round(analysis_end * sfreq)
        if start_sample != analysis_cursor or end_sample <= start_sample:
            raise ValueError(
                "timeline_mapping retained intervals must cover the concatenated analysis sequence in order"
            )
        if not np.isclose(start_sample / sfreq, analysis_start, atol=tolerance_sec, rtol=0.0) or not np.isclose(
            end_sample / sfreq,
            analysis_end,
            atol=tolerance_sec,
            rtol=0.0,
        ):
            raise ValueError("timeline_mapping analysis coordinates are not representable at sfreq")
        if source_end <= source_start or not np.isclose(
            source_end - source_start,
            (end_sample - start_sample) / sfreq,
            atol=tolerance_sec,
            rtol=0.0,
        ):
            raise ValueError("timeline_mapping source interval duration does not match sample count")
        interval_rows.append(
            {
                "start_sample": int(start_sample),
                "end_sample_exclusive": int(end_sample),
                "source_start_sec": source_start,
                "source_end_sec": source_end,
                "source_epoch_index": interval.get("source_epoch_index"),
            }
        )
        analysis_cursor = end_sample
    if analysis_cursor != sample_count:
        raise ValueError(
            "timeline_mapping retained intervals do not cover all microstate samples"
        )

    blocks = []
    for interval in interval_rows:
        is_contiguous = bool(
            blocks
            and abs(interval["source_start_sec"] - blocks[-1]["source_end_sec"])
            <= tolerance_sec
        )
        if is_contiguous:
            block = blocks[-1]
            block["end_sample_exclusive"] = interval["end_sample_exclusive"]
            block["sample_count"] = block["end_sample_exclusive"] - block["start_sample"]
            block["analysis_end_sec"] = float(block["end_sample_exclusive"] / sfreq)
            block["source_end_sec"] = interval["source_end_sec"]
            block["source_epoch_indices"].append(interval["source_epoch_index"])
            block["right_boundary"] = "recording_end"
            continue
        if blocks:
            blocks[-1]["right_boundary"] = "source_time_discontinuity"
        blocks.append(
            {
                "block_index": len(blocks),
                "start_sample": interval["start_sample"],
                "end_sample_exclusive": interval["end_sample_exclusive"],
                "sample_count": interval["end_sample_exclusive"] - interval["start_sample"],
                "analysis_start_sec": float(interval["start_sample"] / sfreq),
                "analysis_end_sec": float(interval["end_sample_exclusive"] / sfreq),
                "source_start_sec": interval["source_start_sec"],
                "source_end_sec": interval["source_end_sec"],
                "source_epoch_indices": [interval["source_epoch_index"]],
                "left_boundary": "recording_start" if not blocks else "source_time_discontinuity",
                "right_boundary": "recording_end",
            }
        )
    return {
        "sequence_domain": "source_contiguous_retained_sample_blocks",
        "method": "Adjacent retained intervals merge only when source_end and next source_start differ by no more than one sample period.",
        "status": "ok",
        "source_time_available": True,
        "source_continuity_tolerance_sec": tolerance_sec,
        "eligible_sample_count": int(sample_count),
        "block_count": int(len(blocks)),
        "blocks": blocks,
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
    if sample_labels is None or len(sample_labels) == 0:
        raise ValueError("sample_labels must contain at least one label")
    if state_names is None or len(state_names) == 0:
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


def _temporal_parameters(labels, names, sfreq, similarity, explained, *, blocks=None):
    segments = _segments(labels, names, sfreq, blocks=blocks)
    result = []
    for index, name in enumerate(names):
        mask = labels == index
        state_segments = [segment for segment in segments if segment["state"] == name]
        durations = np.asarray([segment["duration_ms"] for segment in state_segments], dtype=float)
        result.append({"state": name, "mean_correlation": float(np.mean(np.abs(similarity[index, mask]))) if mask.any() else None, "gev_percent": float(100 * explained[mask].sum() / max(explained.sum(), np.finfo(float).eps)), "occurrences_per_sec": float(len(state_segments) / (labels.size / sfreq)), "time_coverage_percent": float(100 * mask.mean()), "mean_duration_ms": float(durations.mean()) if durations.size else None})
    return result


def _transition_matrix(labels, names, *, blocks=None):
    matrix = np.zeros((len(names), len(names)), dtype=int)
    ranges = blocks if blocks is not None else [(0, len(labels))]
    for start, end in ranges:
        for before, after in zip(labels[start : end - 1], labels[start + 1 : end]):
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


def _segments(labels: np.ndarray, names: list[str], sfreq: float, *, blocks=None) -> list[dict]:
    """Return maximal state runs without crossing supplied block boundaries."""
    ranges = blocks if blocks is not None else [(0, labels.size)]
    result = []
    for block_index, (block_start, block_end) in enumerate(ranges):
        block = labels[block_start:block_end]
        if not block.size:
            continue
        edges = np.flatnonzero(np.diff(block) != 0) + 1
        starts = np.r_[0, edges]
        ends = np.r_[edges, block.size]
        for run_index, (local_start, local_end) in enumerate(zip(starts, ends)):
            start = int(block_start + local_start)
            end = int(block_start + local_end)
            duration_samples = end - start
            result.append(
                {
                    "state": names[int(labels[start])],
                    "block_index": int(block_index),
                    "start_sample": start,
                    "end_sample_exclusive": end,
                    "start_sec": float(start / sfreq),
                    "end_sec": float(end / sfreq),
                    "duration_samples": int(duration_samples),
                    "duration_ms": float(1000 * duration_samples / sfreq),
                    "duration_sec": float(duration_samples / sfreq),
                    "left_censored": bool(run_index == 0),
                    "right_censored": bool(run_index == len(starts) - 1),
                }
            )
    return result


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


def _sequence_summary(
    labels: np.ndarray,
    names: list[str],
    segments: list[dict],
    *,
    state_switch_count: int | None = None,
) -> dict:
    occupancy = np.bincount(labels, minlength=len(names)) / max(labels.size, 1)
    segment_labels = np.asarray([names.index(segment["state"]) for segment in segments], dtype=int)
    segment_occupancy = np.bincount(segment_labels, minlength=len(names)) / max(segment_labels.size, 1)
    if state_switch_count is None:
        if segments and "block_index" in segments[0]:
            block_counts = np.bincount([segment["block_index"] for segment in segments])
            state_switch_count = int(np.sum(np.maximum(block_counts - 1, 0)))
        else:
            state_switch_count = int(max(0, len(segments) - 1))
    return {
        "sample_label_shannon_entropy_bits": _shannon_entropy(occupancy),
        "segment_label_shannon_entropy_bits": _shannon_entropy(segment_occupancy),
        "state_switch_count": int(state_switch_count),
        "segment_count": int(len(segments)),
        "mean_segment_duration_ms": float(np.mean([segment["duration_ms"] for segment in segments])) if segments else None,
    }


def _shannon_entropy(probability: np.ndarray) -> float:
    probability = np.asarray(probability, dtype=float)
    positive = probability[probability > 0]
    return float(-np.sum(positive * np.log2(positive)))
