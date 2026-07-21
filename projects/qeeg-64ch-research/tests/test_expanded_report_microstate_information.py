from collections import defaultdict

import matplotlib.image as mpimg

from qlanalyser_eeg64.expanded_report import (
    _clinical_html,
    _plot_microstate_information_dynamics,
    _technical_html,
    _write_microstate_information_table,
    validate_full_report,
)
from qlanalyser_eeg64.microstates import compute_microstate_information_dynamics


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


def test_information_dynamics_is_exported_plotted_and_referenced_by_both_pages(tmp_path):
    information_dynamics = _information_dynamics()
    table_path = _write_microstate_information_table(
        {"information_dynamics": information_dynamics}, tmp_path / "tables"
    )
    assert table_path.name == "microstate_information_dynamics.csv"
    assert table_path.read_text(encoding="utf-8").splitlines()[0].startswith("start_sec,")

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


def test_technical_traceability_only_links_existing_artifacts_and_validates_targets(tmp_path):
    destination = tmp_path / "report-output"
    assets = destination / "assets"
    tables = destination / "tables"
    assets.mkdir(parents=True)
    tables.mkdir()
    (assets / "qc.png").write_bytes(b"png")
    (assets / "micro_information_dynamics.png").write_bytes(b"png")
    (tables / "qc_epochs.csv").write_text("epoch,retained\n0,1\n", encoding="utf-8")
    (tables / "bandpower_by_channel.csv").write_text("channel,band\nO1,alpha\n", encoding="utf-8")
    (destination / "analysis_summary.json").write_text("{}", encoding="utf-8")
    (destination / "visual_manifest.json").write_text("{}", encoding="utf-8")
    files = {"qc": "qc.png", "micro_information_dynamics": "micro_information_dynamics.png"}
    summary = _html_summary(_information_dynamics())
    (destination / "report.html").write_text('<a href="technical-details.html">technical</a>', encoding="utf-8")
    technical = _technical_html(summary, files, destination=destination)
    (destination / "technical-details.html").write_text(technical, encoding="utf-8")

    assert 'href="tables/qc_epochs.csv"' in technical
    assert 'href="tables/bandpower_by_channel.csv"' in technical
    assert 'href="assets/qc.png"' in technical
    assert "connectivity_global.csv" not in technical
    assert validate_full_report(destination, files)["status"] == "passed"

    (assets / "qc.png").unlink()
    assert any("Missing or empty link target" in error for error in validate_full_report(destination, files)["errors"])
