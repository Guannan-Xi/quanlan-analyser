import json

import numpy as np
import pytest

mne = pytest.importorskip("mne")

from qlanalyser_eeg64 import qc


def _raw_with_a_middle_artifact():
    sfreq = 250.0
    times = np.arange(int(5 * sfreq)) / sfreq
    phases = (0.0, 0.7, 1.4, 2.1)
    data = np.vstack([12e-6 * np.sin(2 * np.pi * 10 * times + phase) for phase in phases])
    artifact_start, artifact_stop = int(2 * sfreq), int(3 * sfreq)
    data[0, artifact_start:artifact_stop] += 300e-6 * np.sin(2 * np.pi * 3 * times[:int(sfreq)])
    info = mne.create_info(["F3", "F4", "C3", "C4"], sfreq, "eeg")
    return mne.io.RawArray(data, info, verbose="ERROR")


def test_qc_source_time_mapping_preserves_middle_rejection_as_nan_gap(monkeypatch):
    def skip_ica(raw, _config):
        return {
            "raw": raw,
            "status": "completed",
            "component_count": 0,
            "excluded_components": [],
            "labels": [],
            "reason": None,
        }

    monkeypatch.setattr(qc, "_remove_iclabel_components", skip_ica)
    cleaned, summary = qc.run_auto_qc(
        _raw_with_a_middle_artifact(),
        qc.QCConfig(robust_z_limit=1e9),
    )

    rows = summary["source_epoch_rows"]
    assert summary["epochs"] == rows  # Existing consumers retain the legacy key.
    assert [row["retained"] for row in rows] == [True, True, False, True, True]
    assert rows[2]["analysis_sample_start"] is None
    assert rows[2]["analysis_sample_stop"] is None
    assert rows[2]["source_sample_start"] == 500
    assert rows[2]["source_sample_stop"] == 750
    assert rows[3]["analysis_sample_start"] == 500
    assert rows[3]["analysis_sample_stop"] == 750

    mapping = summary["source_time_mapping"]
    assert mapping["source_time_axis"] == "seconds_from_original_recording_start"
    assert mapping["analysis_sample_count"] == cleaned.n_times == 1000
    assert mapping["source_duration_sec"] == 5.0
    assert [(item["source_start_sec"], item["source_end_sec"]) for item in mapping["rejected_intervals"]] == [(2.0, 3.0)]
    assert json.loads(json.dumps(mapping))["schema_version"] == "1.0"
    assert json.loads(json.dumps(summary))["source_time_mapping"]["analysis_sample_count"] == 1000

    retained_times = qc.retained_sample_source_times(mapping)
    assert retained_times.shape == (1000,)
    assert retained_times[499] == pytest.approx(499 / 250)
    assert retained_times[500] == pytest.approx(3.0)

    source_times, restored = qc.restore_source_time_axis(cleaned.get_data(), mapping)
    assert source_times.shape == (1250,)
    assert source_times[-1] == pytest.approx(4.996)
    assert restored.shape == (4, 1250)
    assert np.isnan(restored[:, 500:750]).all()
    np.testing.assert_allclose(restored[:, :500], cleaned.get_data()[:, :500])
    np.testing.assert_allclose(restored[:, 750:], cleaned.get_data()[:, 500:])


def test_restore_source_time_axis_rejects_mismatched_analysis_length():
    mapping = {
        "source_duration_sec": 2.0,
        "screened_sampling_rate_hz": 10.0,
        "analysis_sample_count": 10,
        "retained_intervals": [
            {
                "analysis_sample_start": 0,
                "analysis_sample_stop": 10,
                "screened_sample_start": 0,
                "screened_sample_stop": 10,
            }
        ],
    }
    with pytest.raises(ValueError, match="mapping expects 10"):
        qc.restore_source_time_axis(np.zeros(9), mapping)
