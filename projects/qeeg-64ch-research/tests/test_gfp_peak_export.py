import csv

import numpy as np
import pytest

mne = pytest.importorskip("mne")

from qlanalyser_eeg64.gfp import compute_gfp_gmd, write_gfp_peak_topography_gmd_csv


def _raw_with_repeated_gfp_peaks():
    sfreq = 250.0
    times = np.arange(int(8 * sfreq)) / sfreq
    carrier = np.sin(2 * np.pi * 10 * times)
    modulation = 1 + 0.4 * np.sin(2 * np.pi * 2 * times)
    data = np.vstack(
        [
            12e-6 * modulation * carrier,
            -8e-6 * modulation * carrier,
            5e-6 * modulation * carrier,
            -3e-6 * modulation * carrier,
        ]
    )
    return mne.io.RawArray(
        data,
        mne.create_info(["F3", "F4", "C3", "C4"], sfreq, "eeg"),
        verbose="ERROR",
    )


def test_gfp_peak_topography_export_retains_peak_locations_and_historical_columns(tmp_path):
    result = compute_gfp_gmd(_raw_with_repeated_gfp_peaks())
    rows = result["successive_peak_topography_gmd"]["rows"]

    assert len(rows) == len(result["gfp_peak_indices"]) - 1
    assert rows[0]["peak_pair_index"] == 1
    assert rows[0]["first_peak_sample_index"] == result["gfp_peak_indices"][0]
    assert rows[0]["second_peak_sample_index"] == result["gfp_peak_indices"][1]
    assert rows[0]["first_peak_time_sec"] == pytest.approx(
        rows[0]["first_peak_sample_index"] / result["sampling_rate_hz"]
    )
    assert rows[0]["gmd"] == pytest.approx(result["successive_peak_gmd_series"]["values"][0])

    path = write_gfp_peak_topography_gmd_csv(result, tmp_path / "gfp_peak_topography_gmd.csv")
    with path.open(newline="", encoding="utf-8") as handle:
        exported = list(csv.DictReader(handle))

    assert len(exported) == len(rows)
    assert list(exported[0])[:4] == [
        "peak_pair_index",
        "first_peak_gfp_uv",
        "second_peak_gfp_uv",
        "gmd",
    ]
    assert int(exported[0]["first_peak_sample_index"]) == rows[0]["first_peak_sample_index"]
