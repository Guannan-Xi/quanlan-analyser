import json

from qlanalyser_eeg64 import report


def test_report_renderer_reuses_saved_qc_configuration(tmp_path, monkeypatch):
    source = tmp_path / "recording.bdf"
    source.write_bytes(b"synthetic")
    summary_path = tmp_path / "analysis_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "source": {"sha256": "expected"},
                "quality_control": {
                    "config": {"absolute_amplitude_uv": 123.0, "epoch_sec": 2.0},
                    "epoch_summary": {"total": 2, "retained": 2, "rejected": 0},
                },
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    monkeypatch.setattr(report, "file_sha256", lambda _: "expected")
    monkeypatch.setattr(report, "read_raw", lambda *args, **kwargs: "source-raw")
    monkeypatch.setattr(report, "prepare_analysis_raw", lambda raw: ("prepared-raw", {}))

    def fake_run_auto_qc(raw, config):
        captured["raw"] = raw
        captured["config"] = config
        return "cleaned-raw", {"epoch_summary": {"total": 2, "retained": 2, "rejected": 0}}

    monkeypatch.setattr(report, "run_auto_qc", fake_run_auto_qc)
    monkeypatch.setattr(report, "render_report", lambda *args: {"status": "rendered"})

    assert report.render_report_from_summary(source, summary_path, tmp_path / "out") == {"status": "rendered"}
    assert captured["raw"] == "prepared-raw"
    assert captured["config"].absolute_amplitude_uv == 123.0
    assert captured["config"].epoch_sec == 2.0
