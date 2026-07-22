import numpy as np
import pytest

mne = pytest.importorskip("mne")

import qlanalyser_eeg64.gfp as gfp_module
from qlanalyser_eeg64.gfp import GFPConfig, compute_gfp_gmd


def _raw(data_uv: np.ndarray, sfreq: float):
    info = mne.create_info(["F3", "F4", "C3", "C4"], sfreq, "eeg")
    return mne.io.RawArray(data_uv * 1e-6, info, verbose="ERROR")


def _mapping(sfreq: float, interval_length: int, gap_length: int) -> dict:
    second_source_start = interval_length + gap_length
    source_sample_count = second_source_start + interval_length
    return {
        "analysis_sampling_rate_hz": sfreq,
        "screened_sampling_rate_hz": sfreq,
        "analysis_sample_count": 2 * interval_length,
        "source_duration_sec": source_sample_count / sfreq,
        "retained_intervals": [
            {
                "analysis_sample_start": 0,
                "analysis_sample_stop": interval_length,
                "screened_sample_start": 0,
                "screened_sample_stop": interval_length,
                "source_start_sec": 0.0,
            },
            {
                "analysis_sample_start": interval_length,
                "analysis_sample_stop": 2 * interval_length,
                "screened_sample_start": second_source_start,
                "screened_sample_stop": source_sample_count,
                "source_start_sec": second_source_start / sfreq,
            },
        ],
    }


def test_source_adjacent_epochs_merge_but_rejected_gap_splits_processing():
    mapping = {
        "retained_intervals": [
            {
                "analysis_sample_start": 0,
                "analysis_sample_stop": 10,
                "screened_sample_start": 0,
                "screened_sample_stop": 10,
            },
            {
                "analysis_sample_start": 10,
                "analysis_sample_stop": 20,
                "screened_sample_start": 10,
                "screened_sample_stop": 20,
            },
            {
                "analysis_sample_start": 20,
                "analysis_sample_stop": 30,
                "screened_sample_start": 30,
                "screened_sample_stop": 40,
            },
        ]
    }

    assert gfp_module._retained_analysis_intervals(30, mapping) == [(0, 20), (20, 30)]


def test_filtering_matches_independent_source_intervals_not_concatenated_signal():
    sfreq = 100.0
    interval_length = 400
    time = np.arange(interval_length) / sfreq
    first = np.vstack(
        [
            12 * np.sin(2 * np.pi * 7 * time),
            -8 * np.sin(2 * np.pi * 7 * time),
            5 * np.sin(2 * np.pi * 7 * time),
            -3 * np.sin(2 * np.pi * 7 * time),
        ]
    )
    second = np.vstack(
        [
            20 * np.sin(2 * np.pi * 15 * time + 1.2),
            -4 * np.sin(2 * np.pi * 15 * time + 1.2),
            9 * np.sin(2 * np.pi * 15 * time + 1.2),
            -15 * np.sin(2 * np.pi * 15 * time + 1.2),
        ]
    )
    raw = _raw(np.concatenate((first, second), axis=1), sfreq)
    mapping = _mapping(sfreq, interval_length, gap_length=200)

    result = compute_gfp_gmd(raw, source_time_mapping=mapping)
    expected = np.concatenate(
        [
            compute_gfp_gmd(_raw(first, sfreq))["gfp_full_series"]["values_uv"],
            compute_gfp_gmd(_raw(second, sfreq))["gfp_full_series"]["values_uv"],
        ]
    )
    concatenated = np.asarray(compute_gfp_gmd(raw)["gfp_full_series"]["values_uv"])
    actual = np.asarray(result["gfp_full_series"]["values_uv"])

    np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-10)
    assert np.max(np.abs(concatenated - expected)) > 0.01


def test_minimum_valid_interval_uses_declared_short_memory_iir_filter():
    sfreq = 250.0
    time = np.arange(375) / sfreq
    data = np.vstack([
        np.sin(2 * np.pi * frequency * time)
        for frequency in (4.0, 7.0, 12.0, 18.0)
    ])

    result = compute_gfp_gmd(_raw(data, sfreq))

    assert len(result["gfp_full_series"]["values_uv"]) == 375
    assert result["filter_design"] == {
        "method": "iir", "family": "butterworth", "order": 4, "phase": "zero",
        "minimum_interval_cycles_at_low_cutoff": 3.0,
        "minimum_interval_duration_sec": 1.5,
        "short_interval_policy": "reject",
    }


def test_short_interval_is_rejected_before_filtering():
    sfreq = 100.0
    data = np.zeros((4, 149))

    with pytest.raises(ValueError, match="at least 150 samples; shortest interval has 149"):
        compute_gfp_gmd(_raw(data, sfreq))


def test_peak_distance_and_plot_lines_reset_at_source_gap(monkeypatch):
    sfreq = 100.0
    interval_length = 10
    gap_length = 10
    raw = _raw(np.zeros((4, 2 * interval_length)), sfreq)
    mapping = _mapping(sfreq, interval_length, gap_length)
    curve = np.zeros(2 * interval_length)
    curve[[2, 8, 11, 17]] = [3.0, 5.0, 4.0, 3.0]
    filtered_signal = np.vstack((curve, -curve, 0.5 * curve, -0.5 * curve))

    monkeypatch.setattr(
        gfp_module,
        "_filter_retained_intervals",
        lambda _raw, _config, _intervals: filtered_signal,
    )
    result = compute_gfp_gmd(
        raw,
        GFPConfig(
            minimum_peak_distance_ms=50.0,
            display_sampling_hz=sfreq,
            minimum_filter_cycles=0.1,
        ),
        source_time_mapping=mapping,
    )

    assert result["gfp_peak_indices"] == [2, 8, 11, 17]
    assert result["gfp_peak_times_sec"] == pytest.approx([0.02, 0.08, 0.21, 0.27])
    assert result["successive_peak_gmd_series"]["values"][1] is None
    assert result["successive_peak_gmd_series"]["to_time_sec"][1] is None

    display = result["gfp_display_series"]
    gap_positions = [index for index, value in enumerate(display["values_uv"]) if value is None]
    assert gap_positions
    assert display["time_sec"][gap_positions[0]] == pytest.approx(0.1)
    assert display["time_sec"][gap_positions[-1]] == pytest.approx(0.19)


def test_display_series_keeps_short_retained_interval_boundaries():
    values = np.arange(20, dtype=float)
    sample_times = np.arange(20, dtype=float) / 10
    mapping = {
        "screened_sampling_rate_hz": 10.0,
        "source_duration_sec": 4.0,
        "analysis_sample_count": 20,
        "retained_intervals": [
            {"analysis_sample_start": 0, "analysis_sample_stop": 10, "screened_sample_start": 0, "screened_sample_stop": 10},
            {"analysis_sample_start": 10, "analysis_sample_stop": 12, "screened_sample_start": 15, "screened_sample_stop": 17},
            {"analysis_sample_start": 12, "analysis_sample_stop": 20, "screened_sample_start": 25, "screened_sample_stop": 33},
        ],
    }

    indices, _times, displayed = gfp_module._display_series_on_source_axis(
        values, sample_times, mapping, stride=10
    )

    for boundary in (0, 9, 15, 16, 25, 32):
        assert boundary in indices
    assert displayed[indices.index(15)] == 10.0
    assert displayed[indices.index(16)] == 11.0
