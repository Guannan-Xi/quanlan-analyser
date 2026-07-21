import csv
import json

import numpy as np
import pytest

mne = pytest.importorskip("mne")

from qlanalyser_eeg64.spectral import (
    SpectralConfig,
    _alpha_dispersion_row,
    compute_alpha_spectral_dispersion,
    compute_spectral_features,
    write_alpha_spectral_dispersion_csv,
)


def _alpha_raw(duration_sec=24.0, *, channels=None, zero=False):
    sfreq = 250.0
    times = np.arange(int(duration_sec * sfreq)) / sfreq
    alpha = np.sin(2 * np.pi * 10 * times)
    channel_names = channels or ["F3", "F4", "Fz", "Cz", "O1", "O2"]
    data = np.vstack(
        [np.zeros(times.size) if zero else (8 + index) * 1e-6 * alpha for index, _ in enumerate(channel_names)]
    )
    return mne.io.RawArray(data, mne.create_info(channel_names, sfreq, "eeg"), verbose="ERROR")


def test_alpha_dispersion_matches_historical_band_formula_and_window_contract():
    result = compute_alpha_spectral_dispersion(_alpha_raw())

    assert result["status"] == "calculated"
    assert result["frequency_step_hz"] == pytest.approx(0.25)
    assert result["definitions"]["alpha_band_hz"] == [7.0, 13.0]
    assert result["summary"]["modal_frequency_o1_hz"] == pytest.approx(10.0, abs=0.25)
    assert result["summary"]["modal_frequency_o2_hz"] == pytest.approx(10.0, abs=0.25)
    assert result["windowed_distribution"]["complete_window_count"] == 6
    assert result["windowed_distribution"]["analyzed_duration_sec"] == pytest.approx(24.0)
    assert result["windowed_distribution"]["continuity_rule"] == "complete non-overlapping windows of the supplied QC-retained continuous record"
    assert len(result["windowed_distribution"]["feature_rows"]) == 6 * 6
    assert len(result["windowed_distribution"]["normalized_spectrum_rows"]) == 6 * 6 * 25
    assert all(row["cd_alpha2"] >= row["cd_alpha1"] > 0 for row in result["channels"])
    assert all(np.isfinite(row["modal_frequency_hz"]) for row in result["channels"])
    json.dumps(result)


def test_alpha_dispersion_cd_alpha2_uses_half_hz_neighbourhood_not_one_hz():
    config = SpectralConfig()
    freqs_hz = np.arange(9.0, 11.25, 0.25)
    alpha_psd_uv2 = np.ones(freqs_hz.size)
    alpha_psd_uv2[np.where(freqs_hz == 10.0)[0][0]] = 10.0

    row = _alpha_dispersion_row("O1", freqs_hz, alpha_psd_uv2, config, 0.25)
    total = float(alpha_psd_uv2.sum())
    expected_half_hz = float(alpha_psd_uv2[np.abs(freqs_hz - 10.0) <= 0.5].sum() / total)
    expected_one_hz = float(alpha_psd_uv2[np.abs(freqs_hz - 10.0) <= 1.0].sum() / total)

    assert row["modal_frequency_hz"] == 10.0
    assert row["cd_alpha1"] == pytest.approx(10.0 / total)
    assert row["cd_alpha2"] == pytest.approx(expected_half_hz)
    assert row["cd_alpha2"] != pytest.approx(expected_one_hz)


def test_alpha_dispersion_is_compact_when_embedded_in_full_spectral_result():
    result = compute_spectral_features(_alpha_raw())

    dispersion = result["alpha_spectral_dispersion"]
    assert dispersion["windowed_distribution"]["complete_window_count"] == 6
    assert "normalized_spectrum_rows" not in dispersion["windowed_distribution"]
    json.dumps(result)


def test_alpha_dispersion_handles_short_zero_and_missing_electrode_data_without_nan():
    short_result = compute_alpha_spectral_dispersion(_alpha_raw(3.5, channels=["Cz"]))
    zero_result = compute_alpha_spectral_dispersion(_alpha_raw(4.0, channels=["Cz"], zero=True))

    assert short_result["windowed_distribution"]["status"] == "insufficient_data"
    assert short_result["windowed_distribution"]["complete_window_count"] == 0
    assert short_result["summary"]["cd_alpha1_o1"] is None
    assert zero_result["status"] == "insufficient_data"
    assert zero_result["channels"][0]["cd_alpha1"] is None
    assert zero_result["windowed_distribution"]["feature_rows"][0]["cd_alpha1"] is None
    json.dumps(short_result)
    json.dumps(zero_result)


def test_alpha_dispersion_csv_export_has_stable_headers_and_normalized_window_spectra(tmp_path):
    result = compute_alpha_spectral_dispersion(_alpha_raw())
    paths = write_alpha_spectral_dispersion_csv(result, tmp_path)

    assert all(path.exists() for path in paths.values())
    with paths["channel_features"].open(encoding="utf-8-sig", newline="") as handle:
        channel_rows = list(csv.DictReader(handle))
    with paths["window_features"].open(encoding="utf-8-sig", newline="") as handle:
        window_rows = list(csv.DictReader(handle))
    with paths["normalized_spectra"].open(encoding="utf-8-sig", newline="") as handle:
        spectrum_rows = list(csv.DictReader(handle))

    assert len(channel_rows) == 6
    assert len(window_rows) == 36
    assert len(spectrum_rows) == 900
    o1_window_zero = [
        float(row["alpha_power_fraction_per_bin"])
        for row in spectrum_rows
        if row["channel"] == "O1" and row["window_index"] == "0"
    ]
    assert sum(o1_window_zero) == pytest.approx(1.0)
