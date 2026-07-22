import csv
import hashlib
import json

import pytest

from qlanalyser_eeg64 import historical_exports


EXPECTED_HISTORICAL_TABLES = frozenset(
    {
        "alpha_hemisphere_summary.csv",
        "alpha_posterior_channels.csv",
        "band_peak_parameters.csv",
        "beta_hemisphere_channels.csv",
        "beta_hemisphere_summary.csv",
        "channel_bandpower.csv",
        "connectivity_edges.csv",
        "connectivity_global_summary.csv",
        "connectivity_node_strength.csv",
        "connectivity_regional_summary.csv",
        "cross_phase_coupling_channel_metrics.csv",
        "cross_phase_coupling_regional_summary.csv",
        "gfp_gmd_summary.csv",
        "gfp_timeseries.csv",
        "hemispheric_asymmetry.csv",
        "microstate_auto_information.csv",
        "microstate_direct_transitions.csv",
        "microstate_distribution_statistics.csv",
        "microstate_per_second.csv",
        "microstate_segments.csv",
        "microstate_transition_counts.csv",
        "microstate_transition_matrix.csv",
        "multiscale_entropy.csv",
        "pac_channel_metrics.csv",
        "pac_phase_amplitude_distribution.csv",
        "pac_regional_summary.csv",
        "qlanalyser_core_metrics.csv",
        "qlanalyser_narrowband_power.csv",
        "qlanalyser_power_ratios.csv",
        "regional_bandpower.csv",
        "report_compatibility_channel_spectral.csv",
        "spatial_complexity.csv",
        "spectral_parameterization.csv",
        "spectral_peaks.csv",
    }
)


def test_generated_table_keys_equal_immutable_exact_contract():
    assert isinstance(historical_exports.REQUIRED_HISTORICAL_TABLES, frozenset)
    assert historical_exports.REQUIRED_HISTORICAL_TABLES == EXPECTED_HISTORICAL_TABLES
    assert len(EXPECTED_HISTORICAL_TABLES) == 34

    bundle = historical_exports.build_historical_compatibility_tables({})

    assert frozenset(bundle.tables) == EXPECTED_HISTORICAL_TABLES


def test_microstate_exports_preserve_transition_probability_and_reconstruct_occurrences():
    summary = {
        "analysis_data": {"sampling_rate_hz": 500.0},
        "microstates": {
            "state_names": ["A", "B"],
            "direct_transition_counts": {"rows": [{
                "from_state": "A", "to_state": "B", "count": 2,
                "percent_of_outgoing": 50.0,
            }]},
            "segments": [
                {"state": "A", "start_sample": 0, "end_sample_exclusive": 100, "duration_ms": 200.0},
                {"state": "B", "start_sample": 100, "end_sample_exclusive": 500, "duration_ms": 800.0},
                {"state": "A", "start_sample": 500, "end_sample_exclusive": 750, "duration_ms": 500.0},
            ],
            "per_second_coverage": [
                {"start_sec": 0.0, "end_sec": 1.0, "state_coverage_fraction": {"A": 0.2, "B": 0.8}},
                {"start_sec": 1.0, "end_sec": 1.5, "state_coverage_fraction": {"A": 1.0, "B": 0.0}},
            ],
        },
    }

    bundle = historical_exports.build_historical_compatibility_tables(summary)

    direct = bundle.tables["microstate_direct_transitions.csv"]
    assert direct[0]["conditional_probability_percent"] == 50.0
    per_second = bundle.tables["microstate_per_second.csv"]
    assert [(row["A_occurrences"], row["B_occurrences"]) for row in per_second] == [(1, 1), (1, 0)]
    distribution = {row["state"]: row for row in bundle.tables["microstate_distribution_statistics.csv"]}
    assert distribution["A"]["longest_duration_sec"] == pytest.approx(0.5)
    assert distribution["A"]["per_second_occurrence_mean_hz"] == pytest.approx(1.5)
    assert "microstate_per_second.csv" not in bundle.partial


def test_microstate_occurrence_exports_declare_partial_when_segment_times_are_missing():
    bundle = historical_exports.build_historical_compatibility_tables({
        "microstates": {
            "state_names": ["A"],
            "segments": [{"state": "A", "duration_ms": 100.0}],
            "per_second_coverage": [{"state_coverage_fraction": {"A": 1.0}}],
        }
    })

    assert bundle.tables["microstate_per_second.csv"][0]["A_occurrences"] is None
    assert "microstate_per_second.csv" in bundle.partial
    assert "microstate_distribution_statistics.csv" in bundle.partial


def test_microstate_occurrence_reconstructs_missing_coverage_from_segments():
    bundle = historical_exports.build_historical_compatibility_tables({
        "analysis_data": {"sampling_rate_hz": 2.0},
        "microstates": {
            "state_names": ["A", "B"],
            "segments": [
                {"state": "A", "start_sample": 0, "end_sample_exclusive": 2, "duration_ms": 1000.0},
                {"state": "B", "start_sample": 2, "end_sample_exclusive": 3, "duration_ms": 500.0},
            ],
        },
    })

    per_second = bundle.tables["microstate_per_second.csv"]
    assert [(row["A_occurrences"], row["B_occurrences"]) for row in per_second] == [(1, 0), (0, 1)]
    assert per_second[-1]["B_contribution_percent"] == pytest.approx(100.0)
    assert "microstate_per_second.csv" not in bundle.partial


def test_microstate_occurrence_declares_partial_without_coverage_or_segment_timing():
    bundle = historical_exports.build_historical_compatibility_tables({
        "microstates": {
            "state_names": ["A"],
            "segments": [{"state": "A", "duration_ms": 100.0}],
        }
    })

    assert bundle.tables["microstate_per_second.csv"] == []
    assert "microstate_per_second.csv" in bundle.partial
    assert "microstate_distribution_statistics.csv" in bundle.partial


def test_gfp_timeseries_uses_persisted_source_time_mapping_gap():
    summary = {
        "quality_control": {
            "source_time_mapping": {
                "analysis_sampling_rate_hz": 2.0,
                "analysis_sample_count": 4,
                "retained_intervals": [
                    {
                        "analysis_sample_start": 0,
                        "analysis_sample_stop": 2,
                        "source_start_sec": 0.0,
                    },
                    {
                        "analysis_sample_start": 2,
                        "analysis_sample_stop": 4,
                        "source_start_sec": 3.0,
                    },
                ],
            }
        },
        "gfp_gmd": {
            "gfp_full_series": {
                "sampling_rate_hz": 1000.0,
                "values_uv": [1.0, 2.0, 3.0, 4.0],
            }
        },
    }

    rows = historical_exports.build_historical_compatibility_tables(summary).tables[
        "gfp_timeseries.csv"
    ]

    assert [row["time_sec"] for row in rows] == pytest.approx([0.0, 0.5, 3.0, 3.5])
    assert [row["gfp_uv"] for row in rows] == [1.0, 2.0, 3.0, 4.0]


def test_gfp_timeseries_recovers_source_gaps_from_legacy_persisted_epochs():
    summary = {
        "quality_control": {
            "epochs": [
                {"start_sec": 0.0, "end_sec": 1.0, "retained": True},
                {"start_sec": 1.0, "end_sec": 2.0, "retained": False},
                {"start_sec": 2.0, "end_sec": 3.0, "retained": True},
            ]
        },
        "gfp_gmd": {
            "gfp_full_series": {
                "sampling_rate_hz": 2.0,
                "values_uv": [1.0, 2.0, 3.0, 4.0],
            }
        },
    }

    rows = historical_exports.build_historical_compatibility_tables(summary).tables[
        "gfp_timeseries.csv"
    ]

    assert [row["time_sec"] for row in rows] == pytest.approx([0.0, 0.5, 2.0, 2.5])


def test_build_failure_preserves_existing_manifest(tmp_path):
    destination = tmp_path / "historical_compatibility"
    destination.mkdir()
    manifest_path = destination / "export_manifest.json"
    original = b'{"status":"existing"}\n'
    manifest_path.write_bytes(original)
    summary = {
        "gfp_gmd": {
            "gfp_full_series": {"sampling_rate_hz": 2.0, "values_uv": [1.0]}
        }
    }

    with pytest.raises(ValueError, match="source_time_mapping.*quality_control.epochs"):
        historical_exports.write_historical_compatibility_tables(summary, destination)

    assert manifest_path.read_bytes() == original


def test_writer_publishes_deterministic_complete_manifest_and_empty_tables(tmp_path):
    destination = tmp_path / "historical_compatibility"

    historical_exports.write_historical_compatibility_tables({}, destination)
    manifest_path = destination / "export_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    expected_names = sorted(EXPECTED_HISTORICAL_TABLES)
    assert manifest["required_tables"] == expected_names
    assert manifest["tables"] == expected_names
    assert manifest["table_count"] == 34
    assert set(manifest["table_metadata"]) == EXPECTED_HISTORICAL_TABLES

    first_publication = {path.name: path.read_bytes() for path in destination.iterdir()}
    for filename in expected_names:
        csv_path = destination / filename
        payload = csv_path.read_bytes()
        metadata = manifest["table_metadata"][filename]
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            records = list(csv.reader(handle))

        assert records[0] == metadata["header"]
        assert len(records) - 1 == metadata["data_row_count"]
        assert len(payload) == metadata["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == metadata["sha256"]

    empty_metadata = manifest["table_metadata"]["alpha_posterior_channels.csv"]
    assert empty_metadata["data_row_count"] == 0
    with (destination / "alpha_posterior_channels.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        assert len(list(csv.reader(handle))) == 1

    historical_exports.write_historical_compatibility_tables({}, destination)
    second_publication = {path.name: path.read_bytes() for path in destination.iterdir()}
    assert second_publication == first_publication


def test_writer_removes_only_unexpected_csvs_inside_destination(tmp_path):
    destination = tmp_path / "historical_compatibility"
    destination.mkdir()
    stale_csv = destination / "stale.csv"
    unrelated_inside = destination / "notes.txt"
    outside_csv = tmp_path / "outside.csv"
    stale_csv.write_text("stale\n", encoding="utf-8")
    unrelated_inside.write_text("keep\n", encoding="utf-8")
    outside_csv.write_text("keep\n", encoding="utf-8")

    historical_exports.write_historical_compatibility_tables({}, destination)

    assert not stale_csv.exists()
    assert unrelated_inside.read_text(encoding="utf-8") == "keep\n"
    assert outside_csv.read_text(encoding="utf-8") == "keep\n"


def test_failed_refresh_removes_manifest_before_partial_publication(tmp_path, monkeypatch):
    destination = tmp_path / "historical_compatibility"
    destination.mkdir()
    manifest_path = destination / "export_manifest.json"
    manifest_path.write_text('{"tables": ["stale.csv"]}\n', encoding="utf-8")
    real_write_csv_atomic = historical_exports._write_csv_atomic
    call_count = 0

    def fail_during_second_csv(path, header, rows):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise OSError("synthetic write failure")
        return real_write_csv_atomic(path, header, rows)

    monkeypatch.setattr(historical_exports, "_write_csv_atomic", fail_during_second_csv)

    with pytest.raises(OSError, match="synthetic write failure"):
        historical_exports.write_historical_compatibility_tables({}, destination)

    assert not manifest_path.exists()
