import numpy as np
import pytest

mne = pytest.importorskip("mne")

from qlanalyser_eeg64.spectral import compute_spectral_features


def _alpha_raw():
    sfreq = 250.0
    times = np.arange(int(24 * sfreq)) / sfreq
    rng = np.random.default_rng(123)
    alpha = np.sin(2 * np.pi * 10 * times)
    beta = 0.2 * np.sin(2 * np.pi * 18 * times)
    data = np.vstack(
        [
            (10 + index) * 1e-6 * alpha + 2e-6 * beta + 0.2e-6 * rng.normal(size=times.size)
            for index in range(6)
        ]
    )
    info = mne.create_info(["F3", "F4", "Fz", "Cz", "O1", "O2"], sfreq, "eeg")
    return mne.io.RawArray(data, info, verbose="ERROR")


def test_spectral_recovery_exposes_historical_report_measures():
    result = compute_spectral_features(_alpha_raw())

    assert result["scope"] == "full_recording"
    assert len(result["absolute_band_power"]) == 5
    assert len(result["narrowband_power"]["bands"]) == 16
    assert len(result["power_ratios"]) == 12
    assert set(result["channel_spectral_statistics"]["O1"]) == {
        "spectral_entropy",
        "spectral_centroid_hz",
        "spectral_bandwidth_hz",
        "spectral_edge_50_hz",
        "spectral_edge_90_hz",
        "spectral_edge_95_hz",
        "alpha_centroid_hz",
    }
    assert len(result["band_peak_parameters"]["global"]) == 6
    assert len(result["band_peak_parameters"]["by_channel"]["O1"]) == 6


def test_spectral_recovery_identifies_alpha_and_serializes_without_nan():
    result = compute_spectral_features(_alpha_raw())

    assert result["markers"]["paf_hz"]["mean"] == pytest.approx(10.0, abs=0.25)
    assert result["posterior_alpha"]["hemisphere_summary"]["left"]["dominant_alpha_frequency_hz"] == pytest.approx(10.0, abs=0.25)
    assert result["posterior_alpha"]["hemisphere_summary"]["right"]["maximum_alpha_envelope_uv"] > 0
    assert result["channel_spectral_statistics"]["O1"]["spectral_edge_95_hz"] >= result["channel_spectral_statistics"]["O1"]["spectral_edge_90_hz"]
    assert all(np.isfinite(value) for value in result["channel_spectral_statistics"]["O1"].values())
