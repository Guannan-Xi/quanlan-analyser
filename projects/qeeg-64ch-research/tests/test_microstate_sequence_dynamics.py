import json

import numpy as np
import pytest

from qlanalyser_eeg64.microstates import (
    _sequence_summary,
    _temporal_parameters,
    compute_microstate_information_dynamics,
    compute_microstate_lagged_information,
    compute_microstate_sequence_dynamics,
)


def _timeline_mapping(block_lengths, source_starts, sfreq=1.0):
    intervals = []
    analysis_cursor = 0
    for epoch_index, (length, source_start) in enumerate(zip(block_lengths, source_starts)):
        next_cursor = analysis_cursor + length
        intervals.append(
            {
                "analysis_start_sec": analysis_cursor / sfreq,
                "analysis_end_sec": next_cursor / sfreq,
                "source_start_sec": source_start,
                "source_end_sec": source_start + length / sfreq,
                "source_epoch_index": epoch_index,
            }
        )
        analysis_cursor = next_cursor
    return {
        "source_time_available": True,
        "retained_intervals": intervals,
    }


def _entropy_order(result, order):
    return next(row for row in result["block_entropy"]["orders"] if row["L"] == order)


def _jump_cell(result, before, after):
    return next(
        cell
        for cell in result["jump_chain_syntax"]["cells"]
        if cell["from_state"] == before and cell["to_state"] == after
    )


def test_ababab_block_entropy_uses_overlapping_non_circular_words():
    result = compute_microstate_sequence_dynamics(list("ABABAB"), ["A", "B"], 10.0)

    assert _entropy_order(result, 1)["H_L_bits"] == pytest.approx(1.0)
    assert _entropy_order(result, 1)["effective_word_count"] == pytest.approx(2.0)
    assert _entropy_order(result, 2)["eligible_word_count"] == 5
    assert _entropy_order(result, 2)["H_L_bits"] == pytest.approx(0.9709505945)
    assert _entropy_order(result, 3)["eligible_word_count"] == 4
    assert _entropy_order(result, 3)["observed_vocabulary"] == [
        ["A", "B", "A"],
        ["B", "A", "B"],
    ]
    assert _entropy_order(result, 4)["H_L_per_symbol_bits"] == pytest.approx(
        0.9182958341 / 4
    )


def test_two_source_blocks_do_not_create_pairs_words_or_jump_transitions():
    mapping = _timeline_mapping([2, 2], [0.0, 4.0])
    result = compute_microstate_sequence_dynamics(
        list("ABBA"),
        ["A", "B"],
        1.0,
        timeline_mapping=mapping,
    )

    assert result["continuous_blocks"]["block_count"] == 2
    assert result["sample_markov"]["eligible_pair_count"] == 2
    assert result["sample_markov"]["counts"] == [[0, 1], [1, 0]]
    assert result["jump_chain_syntax"]["eligible_transition_count"] == 2
    assert result["jump_chain_syntax"]["observed_counts"] == [[0, 1], [1, 0]]
    assert _entropy_order(result, 2)["eligible_word_count"] == 2
    assert _entropy_order(result, 3)["eligible_word_count"] == 0


def test_constant_sequence_and_unobserved_state_have_explicit_rules_and_strict_json():
    result = compute_microstate_sequence_dynamics(["A"] * 8, ["A", "B"], 4.0)
    lagged = compute_microstate_lagged_information(
        ["A"] * 8,
        ["A", "B"],
        4.0,
        start_ms=250.0,
        stop_ms=250.0,
        step_ms=250.0,
    )

    assert result["sample_markov"]["stationary_status"] == "unique"
    assert result["sample_markov"]["stationary_distribution"] == {"A": 1.0, "B": 0.0}
    assert result["lempel_ziv"]["K_active"] == 1
    assert result["lempel_ziv"]["normalized_value"] == 0.0
    assert result["lempel_ziv"]["status"] == "constant_alphabet_rule"
    assert lagged["state_self_information"][1]["self_information_bits"] is None
    json.dumps({"sequence": result, "lagged": lagged}, allow_nan=False)


def test_deterministic_periodic_and_known_markov_entropy_rates():
    periodic = compute_microstate_sequence_dynamics(list("ABABAB"), ["A", "B"], 1.0)
    assert periodic["sample_markov"]["empirical_first_order_entropy_rate_bits_per_sample"] == 0.0
    assert periodic["sample_markov"]["stationary_distribution"] == {"A": 0.5, "B": 0.5}
    assert periodic["sample_markov"]["stationary_weighted_entropy_rate_bits_per_sample"] == 0.0

    known = compute_microstate_sequence_dynamics(list("AABBAB"), ["A", "B"], 1.0)
    markov = known["sample_markov"]
    assert markov["counts"] == [[1, 2], [1, 1]]
    assert markov["empirical_first_order_entropy_rate_bits_per_sample"] == pytest.approx(
        3 / 5 * 0.9182958341 + 2 / 5
    )
    assert markov["stationary_distribution"] == pytest.approx({"A": 3 / 7, "B": 4 / 7})
    assert markov["stationary_weighted_entropy_rate_bits_per_sample"] == pytest.approx(
        3 / 7 * 0.9182958341 + 4 / 7
    )


def test_stationary_distribution_rejects_zero_outdegree_and_multiple_closed_classes():
    singleton_blocks = compute_microstate_sequence_dynamics(
        ["A", "B"],
        ["A", "B"],
        1.0,
        timeline_mapping=_timeline_mapping([1, 1], [0.0, 3.0]),
    )
    assert singleton_blocks["sample_markov"]["stationary_distribution"] is None
    assert (
        singleton_blocks["sample_markov"]["stationary_not_estimable_reason"]
        == "active_state_has_zero_outdegree"
    )

    reducible = compute_microstate_sequence_dynamics(
        list("AABB"),
        ["A", "B"],
        1.0,
        timeline_mapping=_timeline_mapping([2, 2], [0.0, 4.0]),
    )
    assert reducible["sample_markov"]["stationary_distribution"] is None
    assert (
        reducible["sample_markov"]["stationary_not_estimable_reason"]
        == "multiple_closed_communicating_classes"
    )


def test_jump_chain_independence_expected_counts_and_residuals():
    result = compute_microstate_sequence_dynamics(
        list("ABACAB"),
        ["A", "B", "C", "D"],
        1.0,
    )

    a_to_b = _jump_cell(result, "A", "B")
    b_to_a = _jump_cell(result, "B", "A")
    b_to_c = _jump_cell(result, "B", "C")
    a_to_a = _jump_cell(result, "A", "A")
    a_to_d = _jump_cell(result, "A", "D")
    assert a_to_b["expected_count"] == pytest.approx(2.0)
    assert a_to_b["raw_residual"] == pytest.approx(0.0)
    assert b_to_a["expected_count"] == pytest.approx(0.75)
    assert b_to_a["raw_residual"] == pytest.approx(0.25)
    assert b_to_a["pearson_residual"] == pytest.approx(0.25 / np.sqrt(0.75))
    assert b_to_c["pearson_residual"] == pytest.approx(-0.5)
    assert a_to_a["status"] == "structural_zero"
    assert a_to_d["expected_count"] == 0.0
    assert a_to_d["raw_residual"] is None
    assert a_to_d["pearson_residual"] is None
    assert a_to_d["status"] == "not_estimable_expected_zero"


def test_dwell_segments_split_same_label_at_gap_and_survival_is_monotone():
    result = compute_microstate_sequence_dynamics(
        list("AAAABBAA"),
        ["A", "B"],
        2.0,
        timeline_mapping=_timeline_mapping([4, 4], [0.0, 5.0], sfreq=2.0),
    )
    a_segments = [
        segment for segment in result["dwell_time"]["segments"] if segment["state"] == "A"
    ]

    assert [(segment["block_index"], segment["duration_samples"]) for segment in a_segments] == [
        (0, 4),
        (1, 2),
    ]
    assert a_segments[0]["left_censored"] is True
    assert a_segments[0]["right_censored"] is True
    assert a_segments[1]["right_censored"] is True
    curve = next(
        row for row in result["dwell_time"]["empirical_curves"] if row["state"] == "A"
    )
    survival = [point["survival_probability"] for point in curve["points"]]
    ecdf = [point["ecdf_probability"] for point in curve["points"]]
    assert survival == sorted(survival, reverse=True)
    assert ecdf == sorted(ecdf)
    assert "not Kaplan-Meier" in result["dwell_time"]["curve_definition"]


def test_per_second_occurrence_and_coverage_summaries_reset_at_blocks():
    result = compute_microstate_sequence_dynamics(
        list("AAAB"),
        ["A", "B"],
        2.0,
        timeline_mapping=_timeline_mapping([2, 2], [0.0, 3.0], sfreq=2.0),
    )
    summary = {
        row["state"]: row
        for row in result["per_second_distribution_summary"]["per_state"]
    }

    assert result["per_second_distribution_summary"]["eligible_window_count"] == 2
    assert summary["A"]["coverage_fraction_mean"] == pytest.approx(0.75)
    assert summary["A"]["coverage_fraction_standard_deviation"] == pytest.approx(0.25)
    assert summary["A"]["occurrences_per_sec_mean"] == pytest.approx(1.0)
    assert summary["B"]["occurrences_per_sec_mean"] == pytest.approx(0.5)


def test_lz76_is_finite_block_reset_and_not_clipped_to_one():
    result = compute_microstate_sequence_dynamics(list("ABABAB"), ["A", "B"], 1.0)
    split = compute_microstate_sequence_dynamics(
        list("ABABAB"),
        ["A", "B"],
        1.0,
        timeline_mapping=_timeline_mapping([3, 3], [0.0, 5.0]),
    )

    assert np.isfinite(result["lempel_ziv"]["normalized_value"])
    assert result["lempel_ziv"]["normalized_value"] > 1.0
    assert split["lempel_ziv"]["raw_phrase_count"] == sum(
        row["raw_phrase_count_c_n"] for row in split["lempel_ziv"]["per_block"]
    )
    assert "phrase" not in split["lempel_ziv"] or "phrase_trace" not in split["lempel_ziv"]


def test_information_functions_accept_block_boundaries_without_cross_gap_pairs():
    mapping = _timeline_mapping([2, 2], [0.0, 4.0])
    labels = list("ABBA")
    lagged = compute_microstate_lagged_information(
        labels,
        ["A", "B"],
        1.0,
        start_ms=1000.0,
        stop_ms=1000.0,
        step_ms=1000.0,
        timeline_mapping=mapping,
    )
    dynamics = compute_microstate_information_dynamics(
        labels,
        ["A", "B"],
        1.0,
        window_seconds=10.0,
        mutual_information_lag_ms=1000.0,
        timeline_mapping=mapping,
    )

    assert lagged["rows"][0]["pair_count"] == 2
    assert dynamics["summary"]["window_count"] == 2
    assert [row["lagged_pair_count"] for row in dynamics["rows"]] == [1, 1]
    json.dumps({"lagged": lagged, "dynamics": dynamics}, allow_nan=False)


def test_temporal_parameters_and_sequence_summary_do_not_merge_gap_boundaries():
    labels = np.zeros(8, dtype=int)
    segments = [
        {"state": "A", "duration_ms": 1000.0, "block_index": 0},
        {"state": "A", "duration_ms": 1000.0, "block_index": 1},
    ]

    parameters = _temporal_parameters(
        labels,
        ["A"],
        sfreq=4.0,
        similarity=np.ones((1, 8)),
        explained=np.ones(8),
        blocks=[(0, 4), (4, 8)],
    )
    summary = _sequence_summary(labels, ["A"], segments, state_switch_count=0)

    assert parameters[0]["occurrences_per_sec"] == 1.0
    assert parameters[0]["mean_duration_ms"] == 1000.0
    assert summary["segment_count"] == 2
    assert summary["state_switch_count"] == 0


def test_duration_summary_exposes_samples_milliseconds_and_seconds():
    result = compute_microstate_sequence_dynamics(list("AAAABB"), ["A", "B"], 2.0)
    rows = {
        row["state"]: row for row in result["duration_summary"]["per_state"]
    }

    assert result["duration_summary"]["sequence_domain"] == (
        "dwell_runs_within_source_contiguous_blocks"
    )
    assert rows["A"]["total_duration_samples"] == 4.0
    assert rows["A"]["total_duration_ms"] == 2000.0
    assert rows["A"]["total_duration_sec"] == 2.0
    assert rows["A"]["maximum_duration_samples"] == 4.0
    assert rows["A"]["maximum_duration_ms"] == 2000.0
    assert rows["A"]["maximum_duration_sec"] == 2.0
