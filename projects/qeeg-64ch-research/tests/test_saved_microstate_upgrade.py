import hashlib
import json
from pathlib import Path

import pytest

from qlanalyser_eeg64 import expanded_report, microstates, report
import qlanalyser_eeg64.io as eeg_io
import qlanalyser_eeg64.pipeline as eeg_pipeline
import qlanalyser_eeg64.qc as eeg_qc


def _summary():
    return {
        "source": {
            "filename": "synthetic.bdf",
            "duration_sec": 0.08,
            "sampling_rate_hz": 100.0,
        },
        "analysis_data": {
            "duration_sec": 0.08,
            "sampling_rate_hz": 100.0,
            "eeg_channels": ["O1", "O2"],
        },
        "quality_control": {
            "epoch_summary": {
                "retained": 1,
                "total": 1,
                "rejected": 0,
                "retention_percent": 100.0,
            },
            "ica": {"status": "not_run"},
            "preprocessing": {"steps": ["synthetic saved bundle"]},
        },
        "safety_gate": {
            "conclusion": "AUTO_PASS_BLOCKED",
            "reasons": ["synthetic saved bundle"],
        },
        "spectral": {
            "markers": {
                "paf_hz": {"mean": 10.0},
                "tbr": {"mean": 1.0},
                "faa_ln_f4_minus_ln_f3": 0.0,
            }
        },
        "microstates": {
            "sample_labels": ["A", "A", "B", "B", "A", "B", "B", "A"],
            "state_names": ["A", "B"],
            "timeline_mapping": {
                "source_time_available": True,
                "analysis_sampling_rate_hz": 100.0,
                "analysis_sample_count": 8,
                "retained_intervals": [
                    {
                        "analysis_start_sec": 0.0,
                        "analysis_end_sec": 0.08,
                        "source_start_sec": 0.1,
                        "source_end_sec": 0.18,
                        "source_epoch_index": 0,
                        "analysis_sample_start": 0,
                        "analysis_sample_stop": 8,
                        "screened_sample_start": 10,
                        "screened_sample_stop": 18,
                    }
                ],
            },
        },
        "spatial_complexity": {
            "method": "omega_complexity",
            "channel_count": 2,
            "reference_rank_loss": 1,
            "maximum_effective_dimension": 1,
            "omega_effective_dimension": 1.0,
            "omega_normalized": 1.0,
            "eigenvalue_entropy_nats": 0.0,
        },
    }


def _write_frozen_bundle(root):
    root.mkdir()
    assets = root / "assets"
    tables = root / "tables"
    assets.mkdir()
    tables.mkdir()
    summary = _summary()
    expected_psd, expected_connectivity = (
        expanded_report._expected_dynamic_report_asset_keys(summary)
    )
    keys = (
        set(expanded_report.REQUIRED_REPORT_ASSET_KEYS)
        | expected_psd
        | expected_connectivity
    )
    artifacts = []
    for key in sorted(keys):
        filename = f"{key}.png"
        content = f"frozen-asset:{key}".encode("ascii")
        (assets / filename).write_bytes(content)
        artifacts.append(
            {
                "name": key,
                "path": f"assets/{filename}",
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    (tables / "frozen.csv").write_text("value\n1\n", encoding="utf-8")
    (root / "analysis_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False), encoding="utf-8"
    )
    manifest = {
        "status": expanded_report.VISUAL_MANIFEST_STATUS,
        "artifact_type": expanded_report.VISUAL_MANIFEST_ARTIFACT_TYPE,
        "artifacts": artifacts,
        "warnings": [],
    }
    (root / "visual_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    (root / "report.html").write_text("frozen report", encoding="utf-8")
    (root / "technical-details.html").write_text(
        "frozen technical details", encoding="utf-8"
    )
    return root / "analysis_summary.json"


def _tree_bytes(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _patch_saved_only_dependencies(monkeypatch, *, fail_outputs=False):
    def fail_raw(*_args, **_kwargs):
        raise AssertionError("saved report upgrade must not access raw EEG")

    for module, name in (
        (report, "read_raw"),
        (report, "prepare_analysis_raw"),
        (report, "run_auto_qc"),
        (eeg_io, "read_raw"),
        (eeg_io, "prepare_analysis_raw"),
        (eeg_pipeline, "read_raw"),
        (eeg_pipeline, "prepare_analysis_raw"),
        (eeg_pipeline, "run_auto_qc"),
        (eeg_qc, "run_auto_qc"),
    ):
        monkeypatch.setattr(module, name, fail_raw)

    calls = {}
    real_compute = microstates.compute_microstate_sequence_dynamics

    def compute(sample_labels, state_names, sfreq, *, timeline_mapping):
        calls.update(
            sample_labels=list(sample_labels),
            state_names=list(state_names),
            sfreq=sfreq,
            timeline_mapping=timeline_mapping,
        )
        return real_compute(
            sample_labels,
            state_names,
            sfreq,
            timeline_mapping=timeline_mapping,
        )

    def write_outputs(summary, destination):
        destination = Path(destination)
        sequence_tables = destination / "tables" / "sequence_dynamics"
        sequence_tables.mkdir(parents=True, exist_ok=True)
        (sequence_tables / "markov_transition_entropy.csv").write_text(
            "state,entropy_bits\nA,0.5\n", encoding="utf-8"
        )
        assets = destination / "assets"
        created = {}
        for key in sorted(expanded_report.MICROSTATE_SEQUENCE_DYNAMICS_ASSET_KEYS):
            filename = f"{key}.png"
            (assets / filename).write_bytes(f"upgraded:{key}".encode("ascii"))
            created[key] = filename
        if fail_outputs:
            raise RuntimeError("forced sequence output failure")
        assert summary["microstates"]["sequence_dynamics"]["sample_count"] == 8
        return created

    monkeypatch.setattr(
        microstates,
        "compute_microstate_sequence_dynamics",
        compute,
        raising=False,
    )
    monkeypatch.setattr(
        expanded_report,
        "write_microstate_sequence_dynamics_outputs",
        write_outputs,
        raising=False,
    )
    return calls


def test_upgrade_saved_report_is_raw_free_atomic_and_rebinds_bundle(tmp_path, monkeypatch):
    source = tmp_path / "frozen"
    summary_path = _write_frozen_bundle(source)
    source_before = _tree_bytes(source)
    calls = _patch_saved_only_dependencies(monkeypatch)
    destination = tmp_path / "upgraded"

    result = report.upgrade_saved_microstate_report(summary_path, destination)

    assert _tree_bytes(source) == source_before
    assert result["output_dir"] == destination.resolve()
    assert result["validation"]["status"] == "passed"
    assert result["historical_table_count"] == 34
    assert calls == {
        "sample_labels": ["A", "A", "B", "B", "A", "B", "B", "A"],
        "state_names": ["A", "B"],
        "sfreq": 100.0,
        "timeline_mapping": _summary()["microstates"]["timeline_mapping"],
    }

    upgraded_summary = json.loads(
        (destination / "analysis_summary.json").read_text(encoding="utf-8")
    )
    sequence_dynamics = upgraded_summary["microstates"]["sequence_dynamics"]
    assert sequence_dynamics["sample_count"] == 8
    assert sequence_dynamics["status"] == "ok"
    assert sequence_dynamics["continuous_blocks"]["source_time_available"] is True
    assert (
        destination
        / "tables"
        / "sequence_dynamics"
        / "markov_transition_entropy.csv"
    ).is_file()
    assert (
        destination / "tables" / "microstate_sequence_summary.csv"
    ).is_file()
    compatibility_manifest = json.loads(
        result["historical_export_manifest_path"].read_text(encoding="utf-8")
    )
    assert compatibility_manifest["table_count"] == 34

    manifest = json.loads(
        (destination / "visual_manifest.json").read_text(encoding="utf-8")
    )
    artifact_by_name = {item["name"]: item for item in manifest["artifacts"]}
    assert set(result["new_assets"]) == set(
        expanded_report.MICROSTATE_SEQUENCE_DYNAMICS_ASSET_KEYS
    )
    for key, filename in result["new_assets"].items():
        asset = destination / "assets" / filename
        assert asset.is_file()
        assert artifact_by_name[key]["sha256"] == hashlib.sha256(
            asset.read_bytes()
        ).hexdigest()
    build = manifest["report_build"]
    assert build == result["report_build"]
    assert build["summary_sha256"] == expanded_report._json_sha256(upgraded_summary)
    assert build["asset_set_sha256"] == expanded_report._json_sha256(
        manifest["artifacts"]
    )
    assert expanded_report.validate_full_report(
        destination, result["assets"]
    )["status"] == "passed"
    assert not list(tmp_path.glob(".upgraded.*.staging"))


def test_upgrade_failure_removes_staging_and_preserves_source(tmp_path, monkeypatch):
    source = tmp_path / "frozen"
    summary_path = _write_frozen_bundle(source)
    source_before = _tree_bytes(source)
    _patch_saved_only_dependencies(monkeypatch, fail_outputs=True)
    destination = tmp_path / "failed-upgrade"

    with pytest.raises(RuntimeError, match="forced sequence output failure"):
        report.upgrade_saved_microstate_report(summary_path, destination)

    assert _tree_bytes(source) == source_before
    assert not destination.exists()
    assert not list(tmp_path.glob(".failed-upgrade.*.staging"))


def test_upgrade_refuses_existing_or_source_destination(tmp_path, monkeypatch):
    source = tmp_path / "frozen"
    summary_path = _write_frozen_bundle(source)
    source_before = _tree_bytes(source)
    _patch_saved_only_dependencies(monkeypatch)
    existing = tmp_path / "existing"
    existing.mkdir()
    sentinel = existing / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="already exists"):
        report.upgrade_saved_microstate_report(summary_path, existing)
    with pytest.raises(ValueError, match="must differ"):
        report.upgrade_saved_microstate_report(summary_path, source)

    assert sentinel.read_text(encoding="utf-8") == "keep"
    assert _tree_bytes(source) == source_before
    assert not list(tmp_path.glob(".*.staging"))


def test_upgrade_fails_clearly_when_saved_labels_are_unavailable(tmp_path):
    source = tmp_path / "frozen"
    summary_path = _write_frozen_bundle(source)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    del summary["microstates"]["sample_labels"]
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False), encoding="utf-8"
    )
    source_before = _tree_bytes(source)
    destination = tmp_path / "missing-label-upgrade"

    with pytest.raises(ValueError, match=r"microstates\.sample_labels"):
        report.upgrade_saved_microstate_report(summary_path, destination)

    assert _tree_bytes(source) == source_before
    assert not destination.exists()
    assert not list(tmp_path.glob(".missing-label-upgrade.*.staging"))
