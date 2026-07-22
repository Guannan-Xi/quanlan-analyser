import hashlib
import json
from collections import defaultdict

import matplotlib.image as mpimg

from qlanalyser_eeg64.expanded_report import (
    _clinical_html,
    _microstate_extended_information_html,
    _microstate_method_atlas_html,
    _microstate_method_summary_rows,
    _page,
    _plot_microstate_lagged_information,
    _plot_microstate_state_self_information,
    _plot_microstate_information_dynamics,
    _report_build_contract,
    _technical_html,
    _write_microstate_information_table,
    _write_microstate_method_summary_csv,
    REPORT_PAGE_NAMES,
    REQUIRED_REPORT_ASSET_KEYS,
    VISUAL_MANIFEST_ARTIFACT_TYPE,
    VISUAL_MANIFEST_STATUS,
    validate_full_report,
)
from qlanalyser_eeg64.microstates import (
    compute_microstate_information_dynamics,
    compute_microstate_lagged_information,
)


def _information_dynamics():
    return compute_microstate_information_dynamics(
        ["A", "A", "B", "B", "A", "B", "B", "A"],
        ["A", "B"],
        sfreq=100.0,
        window_seconds=0.04,
        mutual_information_lag_ms=10.0,
    )


def _html_summary(information_dynamics):
    return {
        "source": {"filename": "synthetic.bdf", "duration_sec": 1.0, "sampling_rate_hz": 100.0},
        "analysis_data": {"duration_sec": 1.0, "sampling_rate_hz": 100.0, "eeg_channels": ["O1", "O2"]},
        "quality_control": {
            "epoch_summary": {"retained": 1, "total": 1, "rejected": 0, "retention_percent": 100.0},
            "ica": {"status": "not_run"},
            "preprocessing": {"steps": ["synthetic test"]},
        },
        "safety_gate": {"conclusion": "AUTO_PASS_BLOCKED", "reasons": ["synthetic test"]},
        "spectral": {"markers": {"paf_hz": {"mean": 10.0}, "tbr": {"mean": 1.0}, "faa_ln_f4_minus_ln_f3": 0.0}},
        "microstates": {"information_dynamics": information_dynamics},
    }


def _lagged_information():
    return compute_microstate_lagged_information(
        ["A", "A", "B", "B", "A", "B", "B", "A"],
        ["A", "B"],
        sfreq=100.0,
        start_ms=10.0,
        stop_ms=20.0,
        step_ms=10.0,
    )


def test_microstate_method_catalog_and_summary_csv_expose_restored_metrics(tmp_path):
    microstates = {
        "parameters": [{
            "state": "A",
            "mean_correlation": 0.8,
            "gev_percent": 12.0,
            "mean_duration_ms": 80.0,
            "occurrences_per_sec": 3.0,
            "time_coverage_percent": 25.0,
        }],
        "sequence": {
            "segment_count": 10,
            "state_switch_count": 9,
            "mean_segment_duration_ms": 100.0,
            "sample_label_shannon_entropy_bits": 1.0,
            "segment_label_shannon_entropy_bits": 1.2,
        },
        "duration_summary": [{
            "state": "A",
            "segment_count": 10,
            "mean_duration_ms": 100.0,
            "median_duration_ms": 90.0,
            "standard_deviation_ms": 20.0,
            "p95_duration_ms": 140.0,
            "maximum_duration_ms": 180.0,
        }],
        "timeline_mapping": {
            "analysis_duration_sec": 10.0,
            "source_duration_sec": 12.0,
            "scope": "retained_analysis_to_source_time",
            "boundary": "gaps remain gaps",
            "retained_intervals": [{}],
            "unretained_source_intervals": [{}],
        },
        "sequence_dynamics": {
            "eligible_counts": {
                "samples": 100,
                "sample_adjacent_pairs": 99,
                "jump_chain_segments": 10,
                "jump_chain_transitions": 9,
                "dwell_segments": 10,
                "per_second_windows": 10,
            },
            "continuous_blocks": {
                "block_count": 2,
                "eligible_sample_count": 100,
                "source_time_available": True,
            },
            "per_second_distribution_summary": {"per_state": [{
                "state": "A",
                "eligible_window_count": 10,
                "coverage_fraction_mean": 0.25,
                "coverage_fraction_standard_deviation": 0.1,
                "occurrences_per_sec_mean": 3.0,
                "occurrences_per_sec_standard_deviation": 1.0,
            }]},
            "sample_markov": {
                "empirical_first_order_entropy_rate_bits_per_sample": 0.5,
                "stationary_weighted_entropy_rate_bits_per_sample": 0.4,
                "stationary_status": "estimable",
            },
            "block_entropy": {"orders": [{
                "L": 1,
                "eligible_word_count": 100,
                "observed_vocabulary_size": 2,
                "H_L_bits": 1.0,
                "H_L_per_symbol_bits": 1.0,
                "conditional_increment_bits": 1.0,
            }]},
            "lempel_ziv": {
                "eligible_sample_count": 100,
                "raw_phrase_count": 20,
                "normalized_value": 0.3,
                "status": "ok",
            },
            "dwell_time": {
                "empirical_curves": [{
                    "state": "A",
                    "eligible_duration_count": 10,
                }],
                "status": "ok",
            },
        },
    }
    rows = _microstate_method_summary_rows(microstates)
    metrics = {row["metric"] for row in rows}
    assert {
        "topographic correlation", "duration median", "state switch count",
        "per-second occurrence standard deviation", "empirical Markov entropy rate",
        "block entropy H(L)", "normalized LZ76 complexity", "dwell curve status",
        "retained interval count",
    } <= metrics

    path = _write_microstate_method_summary_csv(microstates, tmp_path / "tables")
    assert path.is_file()
    assert "topographic correlation" in path.read_text(encoding="utf-8")

    files = defaultdict(lambda: "placeholder.png")
    summary = {"microstates": microstates}
    catalog = _microstate_method_atlas_html(summary, files)
    for label in (
        "GFP / GMD", "GFP-peak clustering and template reconstruction",
        "Direct transition counts", "Jump-chain transition syntax",
        "Sample-level Markov chain", "Markov entropy rate", "Block entropy",
        "Lempel-Ziv LZ76", "Dwell ECDF and survival",
        "Source-time mapping and gap-aware eligibility",
    ):
        assert label in catalog


def test_information_dynamics_is_exported_plotted_and_referenced_by_both_pages(tmp_path):
    information_dynamics = _information_dynamics()
    table_path = _write_microstate_information_table(
        {"information_dynamics": information_dynamics}, tmp_path / "tables"
    )
    assert table_path.name == "microstate_information_dynamics.csv"
    assert table_path.read_text(encoding="utf-8").splitlines()[0].startswith(
        ("start_sec,", "block_index,start_sec,")
    )

    figure_path = tmp_path / "microstate_information_dynamics.png"
    _plot_microstate_information_dynamics(
        {"microstates": {"information_dynamics": information_dynamics}}, figure_path
    )
    assert mpimg.imread(figure_path).shape[0] > 500

    files = defaultdict(lambda: "placeholder.png")
    files["micro_information_dynamics"] = figure_path.name
    summary = _html_summary(information_dynamics)
    assert figure_path.name in _clinical_html(summary, files)
    assert figure_path.name in _technical_html(summary, files)


def test_extended_microstate_information_is_plotted_and_required_by_manifest(tmp_path):
    lagged_information = _lagged_information()
    summary = _html_summary(_information_dynamics())
    summary["microstates"]["lagged_information"] = lagged_information
    lagged_path = tmp_path / "microstate_lagged_information.png"
    self_path = tmp_path / "microstate_state_self_information.png"

    _plot_microstate_lagged_information(summary, lagged_path)
    _plot_microstate_state_self_information(summary, self_path)

    assert mpimg.imread(lagged_path).shape[0] > 300
    assert mpimg.imread(self_path).shape[0] > 300
    files = {
        "micro_lagged_information": lagged_path.name,
        "micro_state_self_information": self_path.name,
    }
    html_text = _microstate_extended_information_html(summary, files)
    assert lagged_path.name in html_text
    assert self_path.name in html_text


def test_technical_traceability_only_links_existing_artifacts_and_validates_targets(tmp_path):
    destination = tmp_path / "report-output"
    assets = destination / "assets"
    tables = destination / "tables"
    assets.mkdir(parents=True)
    tables.mkdir()
    files = {key: f"{key}.png" for key in REQUIRED_REPORT_ASSET_KEYS}
    for filename in files.values():
        (assets / filename).write_bytes(b"png")
    (tables / "qc_epochs.csv").write_text("epoch,retained\n0,1\n", encoding="utf-8")
    (tables / "bandpower_by_channel.csv").write_text("channel,band\nO1,alpha\n", encoding="utf-8")
    summary = _html_summary(_information_dynamics())
    (destination / "analysis_summary.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )
    build, artifacts = _report_build_contract(summary, destination, files, {})
    report_text = _page(
        "Synthetic report",
        '<a href="technical-details.html">technical</a>',
        build_id=build["id"],
    )
    technical = _technical_html(
        summary, files, destination=destination, build_id=build["id"]
    )
    build["pages"] = {
        REPORT_PAGE_NAMES[0]: hashlib.sha256(report_text.encode("utf-8")).hexdigest(),
        REPORT_PAGE_NAMES[1]: hashlib.sha256(technical.encode("utf-8")).hexdigest(),
    }
    manifest = {
        "status": VISUAL_MANIFEST_STATUS,
        "artifact_type": VISUAL_MANIFEST_ARTIFACT_TYPE,
        "design_spec": {},
        "artifacts": artifacts,
        "report_build": build,
        "report_limitations": [],
        "warnings": [],
    }
    (destination / "visual_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (destination / "report.html").write_bytes(report_text.encode("utf-8"))
    (destination / "technical-details.html").write_bytes(technical.encode("utf-8"))

    assert 'href="tables/qc_epochs.csv"' in technical
    assert 'href="tables/bandpower_by_channel.csv"' in technical
    assert 'href="assets/qc.png"' in technical
    assert "connectivity_global.csv" not in technical
    validation = validate_full_report(destination, files)
    assert validation["status"] == "passed", validation["errors"]

    (assets / "qc.png").unlink()
    assert any("Missing or empty link target" in error for error in validate_full_report(destination, files)["errors"])
