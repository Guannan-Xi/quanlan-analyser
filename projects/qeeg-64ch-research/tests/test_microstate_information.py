import csv

import numpy as np
import pytest

from qlanalyser_eeg64.microstates import (
    _direct_transition_counts,
    _transition_matrix,
    build_microstate_timeline_mapping,
    compute_microstate_lagged_information,
    compute_microstate_information_dynamics,
    map_microstate_segments_to_source_time,
    write_microstate_lagged_information_csv,
    write_microstate_information_csv,
    write_microstate_source_segments_csv,
    write_microstate_timeline_mapping_csv,
    write_microstate_transition_counts_csv,
)


def test_microstate_information_dynamics_returns_windowed_self_information_and_lagged_mi(tmp_path):
    result = compute_microstate_information_dynamics(
        ["A", "A", "B", "B"],
        ["A", "B"],
        sfreq=100.0,
        window_seconds=0.04,
        mutual_information_lag_ms=10.0,
    )

    assert result["scope"] == "full_recording_consecutive_windows"
    assert result["global_state_probability"] == {"A": 0.5, "B": 0.5}
    assert result["rows"][0]["mean_self_information_bits"] == pytest.approx(1.0)
    assert result["rows"][0]["lagged_mutual_information_bits"] == pytest.approx(0.251629, abs=1e-5)
    assert result["summary"]["window_count"] == 1

    output = write_microstate_information_csv(result, tmp_path / "microstate_information_dynamics.csv")
    with output.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["lagged_pair_count"] == "3"


def test_lagged_information_covers_4_to_40_ms_and_is_distinct_from_windowed_dynamics(tmp_path):
    labels = ["A", "B"] * 100
    result = compute_microstate_lagged_information(
        labels,
        ["A", "B"],
        sfreq=250.0,
    )

    assert [row["requested_lag_ms"] for row in result["rows"]] == list(range(4, 41, 4))
    assert [row["lag_samples"] for row in result["rows"]] == list(range(1, 11))
    assert all(row["pair_count"] > 0 for row in result["rows"])
    assert result["state_self_information"] == [
        {"state": "A", "sample_count": 100, "occupancy_probability": 0.5, "self_information_bits": 1.0},
        {"state": "B", "sample_count": 100, "occupancy_probability": 0.5, "self_information_bits": 1.0},
    ]
    assert "not interchangeable" in result["definition"]["comparison_with_information_dynamics"]

    output = write_microstate_lagged_information_csv(result, tmp_path / "lagged_information.csv")
    with output.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 10
    assert rows[0]["actual_lag_ms"] == "4.0"


def test_direct_transition_table_and_source_time_mapping_preserve_real_gaps(tmp_path):
    transitions = _transition_matrix(np.asarray([0, 0, 1, 1, 0]), ["A", "B"])
    counts = _direct_transition_counts(transitions)
    assert counts["total_transition_count"] == 2
    assert {(row["from_state"], row["to_state"]): row["count"] for row in counts["rows"]} == {
        ("A", "B"): 1,
        ("B", "A"): 1,
    }
    transition_csv = write_microstate_transition_counts_csv(counts, tmp_path / "transition_counts.csv")
    assert len(list(csv.DictReader(transition_csv.open(encoding="utf-8", newline="")))) == 2

    mapping = build_microstate_timeline_mapping(
        sample_count=500,
        sfreq=250.0,
        source_epoch_rows=[
            {"epoch_index": 0, "start_sec": 0.0, "end_sec": 1.0, "retained": True},
            {"epoch_index": 1, "start_sec": 1.0, "end_sec": 2.0, "retained": False},
            {"epoch_index": 2, "start_sec": 2.0, "end_sec": 3.0, "retained": True},
        ],
    )
    assert mapping["source_time_available"] is True
    assert mapping["unretained_source_intervals"] == [
        {"source_start_sec": 1.0, "source_end_sec": 2.0, "source_epoch_index": 1}
    ]
    assert mapping["retained_intervals"][1]["analysis_start_sec"] == 1.0
    assert mapping["retained_intervals"][1]["source_start_sec"] == 2.0

    source_segments = map_microstate_segments_to_source_time(
        [{"state": "A", "start_sec": 0.5, "end_sec": 1.5}],
        mapping,
    )
    assert source_segments == [
        {
            "state": "A",
            "analysis_start_sec": 0.5,
            "analysis_end_sec": 1.0,
            "source_start_sec": 0.5,
            "source_end_sec": 1.0,
            "source_epoch_index": 0,
        },
        {
            "state": "A",
            "analysis_start_sec": 1.0,
            "analysis_end_sec": 1.5,
            "source_start_sec": 2.0,
            "source_end_sec": 2.5,
            "source_epoch_index": 2,
        },
    ]
    assert write_microstate_timeline_mapping_csv(mapping, tmp_path / "timeline.csv").is_file()
    assert write_microstate_source_segments_csv(source_segments, tmp_path / "source_segments.csv").is_file()
