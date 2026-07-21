import json

import numpy as np
import pytest

mne = pytest.importorskip("mne")

from qlanalyser_eeg64.complexity import compute_complexity
from qlanalyser_eeg64.aperiodic import compute_aperiodic_spectrum
from qlanalyser_eeg64.connectivity import compute_connectivity
from qlanalyser_eeg64.coupling import compute_coupling
from qlanalyser_eeg64.gfp import compute_gfp_gmd
from qlanalyser_eeg64.microstates import compute_microstates
from qlanalyser_eeg64.qc import run_auto_qc
from qlanalyser_eeg64.spatial import compute_spatial_complexity


def _raw():
    sfreq = 250.0
    times = np.arange(int(24 * sfreq)) / sfreq
    rng = np.random.default_rng(42)
    alpha = np.sin(2 * np.pi * 10 * times)
    data = np.vstack([(8 + index) * 1e-6 * alpha + 1e-6 * rng.normal(size=times.size) for index in range(6)])
    return mne.io.RawArray(data, mne.create_info(["F3", "F4", "Fz", "Cz", "O1", "O2"], sfreq, "eeg"), verbose="ERROR")


def test_recovered_modules_analyse_qc_retained_full_recording():
    cleaned, qc = run_auto_qc(_raw())
    assert qc["safety_gate"]["conclusion"] == "AUTO_PASS_BLOCKED"
    gfp = compute_gfp_gmd(cleaned)
    assert len(gfp["gfp_peak_indices"]) > 6
    assert len(gfp["gfp_full_series"]["values_uv"]) == cleaned.n_times
    assert gfp["gfp_display_series"]["time_sec"][-1] < gfp["duration_sec"]
    assert len(gfp["successive_peak_gmd_series"]["values"]) == len(gfp["gfp_peak_indices"]) - 1
    json.dumps(gfp)
    microstates = compute_microstates(cleaned)
    assert len(microstates["parameters"]) == 6
    assert len(microstates["per_second_coverage"]) == 24
    assert len(microstates["duration_summary"]) == 6
    assert sum(item["outgoing_transition_count"] for item in microstates["outgoing_transitions"]) == microstates["sequence"]["state_switch_count"]
    assert microstates["segments"][0]["start_sec"] == 0.0
    assert len(microstates["direct_transition_counts"]["rows"]) == 30
    assert microstates["direct_transition_counts"]["total_transition_count"] == microstates["sequence"]["state_switch_count"]
    assert len(microstates["lagged_information"]["rows"]) == 10
    assert microstates["timeline_mapping"]["source_time_available"] is False
    json.dumps(microstates)
    assert len(compute_complexity(cleaned)["channel_metrics"]) == 6
    assert compute_spatial_complexity(cleaned)["channel_count"] == 6
    assert "plv" in compute_connectivity(cleaned)["bands"]["alpha"]
    coupling = compute_coupling(cleaned)
    assert len(coupling["pac"]) == 6
    curve = coupling["pac"][0]["phase_amplitude_binned_curve"]
    assert len(curve["phase_bin_centers_degrees"]) == 18
    assert sum(curve["sample_count"]) == coupling["pac"][0]["analyzed_samples"]
    json.dumps(coupling)


def test_aperiodic_spectrum_uses_current_specparam_api():
    result = compute_aperiodic_spectrum(_raw())
    assert np.isfinite(result["aperiodic_exponent"])
    assert 0 <= result["fit_r_squared"] <= 1
