import hashlib
import json
import os
from pathlib import Path

import pytest

from qlanalyser_eeg64 import expanded_report, report
from qlanalyser_eeg64.historical_exports import GFP_REPORT_LIMITATION_CODE
import qlanalyser_eeg64.io as eeg_io
import qlanalyser_eeg64.qc as eeg_qc


def _summary():
    return {
        "source": {"filename": "synthetic.bdf", "duration_sec": 1.0, "sampling_rate_hz": 100.0},
        "analysis_data": {"duration_sec": 1.0, "sampling_rate_hz": 100.0, "eeg_channels": ["O1", "O2"]},
        "quality_control": {
            "epoch_summary": {"retained": 1, "total": 1, "rejected": 0, "retention_percent": 100.0},
            "ica": {"status": "not_run"},
            "preprocessing": {"steps": ["synthetic test"]},
        },
        "safety_gate": {"conclusion": "AUTO_PASS_BLOCKED", "reasons": ["synthetic test"]},
        "spectral": {
            "markers": {
                "paf_hz": {"mean": 10.0},
                "tbr": {"mean": 1.0},
                "faa_ln_f4_minus_ln_f3": 0.0,
            }
        },
        "microstates": {},
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


def _write_saved_bundle(tmp_path, summary=None):
    summary = summary or _summary()
    assets = tmp_path / "assets"
    (tmp_path / "tables").mkdir()
    assets.mkdir()
    expected_psd, expected_connectivity = expanded_report._expected_dynamic_report_asset_keys(summary)
    keys = set(expanded_report.REQUIRED_REPORT_ASSET_KEYS) | expected_psd | expected_connectivity
    if summary.get("microstates", {}).get("sequence_dynamics"):
        keys |= set(expanded_report.MICROSTATE_SEQUENCE_DYNAMICS_ASSET_KEYS)
    if summary.get("microstates", {}).get("lagged_information"):
        keys |= set(expanded_report.MICROSTATE_EXTENDED_INFORMATION_ASSET_KEYS)
    entries = []
    for key in sorted(keys):
        filename = f"{key}.png"
        content = f"synthetic-png:{key}".encode("ascii")
        (assets / filename).write_bytes(content)
        entries.append({
            "name": key,
            "path": f"assets/{filename}",
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        })
    (tmp_path / "analysis_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False), encoding="utf-8"
    )
    manifest = {
        "status": expanded_report.VISUAL_MANIFEST_STATUS,
        "artifact_type": expanded_report.VISUAL_MANIFEST_ARTIFACT_TYPE,
        "artifacts": entries,
        "warnings": [],
    }
    (tmp_path / "visual_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "report.html").write_text("old report", encoding="utf-8")
    (tmp_path / "technical-details.html").write_text("old technical", encoding="utf-8")
    return summary, manifest


def _summary_with_historical_gfp(*, short_interval=True):
    summary = _summary()
    retained_ranges = [(0.0, 1.0), (1.0, 2.0)]
    if short_interval:
        retained_ranges.append((3.0, 4.0))
    else:
        retained_ranges.extend(((3.0, 4.0), (4.0, 5.0)))
    epochs = [
        {"start_sec": start, "end_sec": stop, "retained": True}
        for start, stop in retained_ranges[:2]
    ]
    epochs.append({"start_sec": 2.0, "end_sec": 3.0, "retained": False})
    epochs.extend(
        {"start_sec": start, "end_sec": stop, "retained": True}
        for start, stop in retained_ranges[2:]
    )
    sample_count = 300 if short_interval else 400
    summary["quality_control"]["epochs"] = epochs
    summary["gfp_gmd"] = {
        "filter_hz": [2.0, 20.0],
        "sampling_rate_hz": 100.0,
        "gfp_full_series": {
            "sampling_rate_hz": 100.0,
            "values_uv": [0.0] * sample_count,
        },
    }
    return summary


def _bundle_bytes(tmp_path):
    return {
        name: (tmp_path / name).read_bytes()
        for name in (*expanded_report.REPORT_PAGE_NAMES, "visual_manifest.json")
    }


def test_saved_report_pages_are_rebuilt_with_bound_build_identity(tmp_path):
    summary, _ = _write_saved_bundle(tmp_path)

    result = expanded_report.rerender_saved_report_pages(summary, tmp_path, {})

    assert result["validation"]["status"] == "passed"
    manifest = json.loads((tmp_path / "visual_manifest.json").read_text(encoding="utf-8"))
    build = manifest["report_build"]
    assert build["contract_version"] == expanded_report.REPORT_BUILD_CONTRACT_VERSION
    assert build["asset_count"] == len(manifest["artifacts"])
    assert all("sha256" in artifact for artifact in manifest["artifacts"])
    for page_name in expanded_report.REPORT_PAGE_NAMES:
        page = tmp_path / page_name
        page_text = page.read_text(encoding="utf-8")
        assert f'<meta name="report-build-id" content="{build["id"]}">' in page_text
        assert f'data-report-build="{build["id"]}"' in page_text
        assert build["pages"][page_name] == hashlib.sha256(page.read_bytes()).hexdigest()
    assert 'id="waveform"' in (tmp_path / "report.html").read_text(encoding="utf-8")


def test_saved_report_surfaces_and_deduplicates_historical_gfp_limitation(tmp_path):
    summary, _ = _write_saved_bundle(
        tmp_path, _summary_with_historical_gfp(short_interval=True)
    )

    expanded_report.rerender_saved_report_pages(summary, tmp_path, {})
    first_bundle = _bundle_bytes(tmp_path)
    expanded_report.rerender_saved_report_pages(summary, tmp_path, {})

    manifest = json.loads((tmp_path / "visual_manifest.json").read_text(encoding="utf-8"))
    matching_warnings = [
        warning for warning in manifest["warnings"]
        if isinstance(warning, dict) and warning.get("code") == GFP_REPORT_LIMITATION_CODE
    ]
    assert len(matching_warnings) == 1
    assert manifest["report_limitations"] == matching_warnings
    assert manifest["report_build"]["limitations_sha256"]
    audit = matching_warnings[0]["audit"]
    assert audit["mapping_source"] == "quality_control.epochs"
    assert audit["continuous_interval_count"] == 2
    assert audit["short_interval_count"] == 1
    assert audit["minimum_interval_samples"] == 150
    assert audit["shortest_interval_samples"] == 100
    for page_name in expanded_report.REPORT_PAGE_NAMES:
        page = (tmp_path / page_name).read_text(encoding="utf-8")
        assert f'data-warning-code="{GFP_REPORT_LIMITATION_CODE}"' in page
        assert "需从原始记录重新运行后方可完成科学验收" in page
    assert _bundle_bytes(tmp_path) == first_bundle


def test_saved_report_omits_gfp_limitation_when_all_intervals_meet_policy(tmp_path):
    summary, _ = _write_saved_bundle(
        tmp_path, _summary_with_historical_gfp(short_interval=False)
    )

    expanded_report.rerender_saved_report_pages(summary, tmp_path, {})

    manifest = json.loads((tmp_path / "visual_manifest.json").read_text(encoding="utf-8"))
    assert manifest["report_limitations"] == []
    assert not any(
        isinstance(warning, dict) and warning.get("code") == GFP_REPORT_LIMITATION_CODE
        for warning in manifest["warnings"]
    )
    for page_name in expanded_report.REPORT_PAGE_NAMES:
        page = (tmp_path / page_name).read_text(encoding="utf-8")
        assert GFP_REPORT_LIMITATION_CODE not in page


def test_saved_report_gfp_limitation_accepts_source_time_mapping(tmp_path):
    summary = _summary_with_historical_gfp(short_interval=True)
    summary["quality_control"].pop("epochs")
    summary["quality_control"]["source_time_mapping"] = {
        "analysis_sampling_rate_hz": 100.0,
        "analysis_sample_count": 300,
        "retained_intervals": [
            {
                "analysis_sample_start": 0,
                "analysis_sample_stop": 200,
                "screened_sample_start": 0,
                "screened_sample_stop": 200,
            },
            {
                "analysis_sample_start": 200,
                "analysis_sample_stop": 300,
                "screened_sample_start": 300,
                "screened_sample_stop": 400,
            },
        ],
    }
    summary, _ = _write_saved_bundle(tmp_path, summary)

    expanded_report.rerender_saved_report_pages(summary, tmp_path, {})

    manifest = json.loads((tmp_path / "visual_manifest.json").read_text(encoding="utf-8"))
    assert manifest["report_limitations"][0]["audit"]["mapping_source"] == (
        "quality_control.source_time_mapping"
    )


def test_bound_manifest_rejects_missing_gfp_limitation_warning(tmp_path):
    summary, _ = _write_saved_bundle(
        tmp_path, _summary_with_historical_gfp(short_interval=True)
    )
    expanded_report.rerender_saved_report_pages(summary, tmp_path, {})
    manifest = json.loads((tmp_path / "visual_manifest.json").read_text(encoding="utf-8"))
    manifest["warnings"] = []
    (tmp_path / "visual_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="warnings are missing report limitations"):
        expanded_report.rerender_saved_report_pages(summary, tmp_path, {})


def test_saved_report_refresh_rejects_missing_required_asset(tmp_path):
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "visual_manifest.json").write_text(json.dumps({
        "status": expanded_report.VISUAL_MANIFEST_STATUS,
        "artifact_type": expanded_report.VISUAL_MANIFEST_ARTIFACT_TYPE,
        "artifacts": [],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="missing required report assets"):
        expanded_report.rerender_saved_report_pages(_summary(), tmp_path, {})


def test_saved_report_refresh_requires_extended_microstate_information_assets(tmp_path):
    summary = _summary()
    summary["microstates"] = {
        "lagged_information": {
            "rows": [],
            "state_self_information": [],
        }
    }
    _summary_data, manifest = _write_saved_bundle(tmp_path, summary)
    manifest["artifacts"] = [
        artifact
        for artifact in manifest["artifacts"]
        if artifact["name"] != "micro_lagged_information"
    ]
    (tmp_path / "visual_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="missing required report assets"):
        expanded_report.rerender_saved_report_pages(summary, tmp_path, {})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("status", "failed", "unsupported status"),
        ("artifact_type", "other", "unsupported artifact_type"),
    ],
)
def test_saved_report_refresh_rejects_manifest_identity_fields(tmp_path, field, value, message):
    summary, manifest = _write_saved_bundle(tmp_path)
    manifest[field] = value
    (tmp_path / "visual_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        expanded_report.rerender_saved_report_pages(summary, tmp_path, {})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("size_bytes", 1, "size_bytes mismatch"),
        ("sha256", "0" * 64, "sha256 mismatch"),
    ],
)
def test_saved_report_refresh_rejects_asset_metadata_mismatch(tmp_path, field, value, message):
    summary, manifest = _write_saved_bundle(tmp_path)
    manifest["artifacts"][0][field] = value
    (tmp_path / "visual_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        expanded_report.rerender_saved_report_pages(summary, tmp_path, {})


def test_saved_report_refresh_rejects_duplicate_asset_path(tmp_path):
    summary, manifest = _write_saved_bundle(tmp_path)
    duplicate = dict(manifest["artifacts"][0])
    duplicate["name"] = "different_logical_name"
    manifest["artifacts"].append(duplicate)
    (tmp_path / "visual_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate artifact path"):
        expanded_report.rerender_saved_report_pages(summary, tmp_path, {})


def test_saved_report_refresh_rejects_case_alias_asset_path_on_windows(tmp_path):
    if os.name != "nt":
        pytest.skip("case-insensitive path alias is Windows-specific")
    summary, manifest = _write_saved_bundle(tmp_path)
    duplicate = dict(manifest["artifacts"][0])
    duplicate["name"] = "different_logical_name"
    duplicate["path"] = duplicate["path"].upper()
    manifest["artifacts"].append(duplicate)
    (tmp_path / "visual_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate artifact path"):
        expanded_report.rerender_saved_report_pages(summary, tmp_path, {})


def test_saved_report_refresh_rejects_bound_manifest_summary_mismatch(tmp_path):
    summary, _ = _write_saved_bundle(tmp_path)
    expanded_report.rerender_saved_report_pages(summary, tmp_path, {})
    original = _bundle_bytes(tmp_path)
    changed_summary = json.loads(json.dumps(summary))
    changed_summary["source"]["duration_sec"] = 2.0

    with pytest.raises(ValueError, match="summary_sha256 mismatch"):
        expanded_report.rerender_saved_report_pages(changed_summary, tmp_path, {})

    assert _bundle_bytes(tmp_path) == original


def test_saved_report_refresh_rejects_bound_manifest_asset_rebinding(tmp_path):
    summary, _ = _write_saved_bundle(tmp_path)
    expanded_report.rerender_saved_report_pages(summary, tmp_path, {})
    original = _bundle_bytes(tmp_path)
    manifest = json.loads((tmp_path / "visual_manifest.json").read_text(encoding="utf-8"))
    artifact = manifest["artifacts"][0]
    asset = tmp_path / artifact["path"]
    asset.write_bytes(b"replacement synthetic asset")
    artifact["size_bytes"] = asset.stat().st_size
    artifact["sha256"] = hashlib.sha256(asset.read_bytes()).hexdigest()
    (tmp_path / "visual_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    before_attempt = _bundle_bytes(tmp_path)

    with pytest.raises(ValueError, match="asset_set_sha256 mismatch"):
        expanded_report.rerender_saved_report_pages(summary, tmp_path, {})

    assert _bundle_bytes(tmp_path) == before_attempt
    assert before_attempt != original


def test_saved_report_refresh_enforces_exact_dynamic_asset_keys(tmp_path):
    summary = _summary()
    summary["spectral"]["psd_uv2_per_hz"] = {f"C{index}": [] for index in range(9)}
    summary["connectivity"] = {"bands": {"Theta": {"imcoh": {}, "aec": {}}}}
    summary, manifest = _write_saved_bundle(tmp_path, summary)
    manifest["artifacts"] = [
        artifact for artifact in manifest["artifacts"]
        if artifact["name"] != "psd_atlas_02"
    ]
    (tmp_path / "visual_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="dynamic report assets are incomplete"):
        expanded_report.rerender_saved_report_pages(summary, tmp_path, {})

    extra = tmp_path / "assets" / "connectivity_unexpected.png"
    extra.write_bytes(b"extra")
    manifest["artifacts"].append({
        "name": "connectivity_unexpected",
        "path": "assets/connectivity_unexpected.png",
        "size_bytes": 5,
        "sha256": hashlib.sha256(b"extra").hexdigest(),
    })
    (tmp_path / "visual_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="dynamic report assets are incomplete"):
        expanded_report.rerender_saved_report_pages(summary, tmp_path, {})


def test_report_bundle_rolls_back_all_files_when_second_commit_fails(tmp_path, monkeypatch):
    summary, _ = _write_saved_bundle(tmp_path)
    original = _bundle_bytes(tmp_path)
    real_commit = expanded_report._commit_staged_file
    calls = []

    def fail_second_commit(staged, target):
        calls.append(Path(target).name)
        if len(calls) == 2:
            raise OSError("forced second commit failure")
        real_commit(staged, target)

    monkeypatch.setattr(expanded_report, "_commit_staged_file", fail_second_commit)

    with pytest.raises(OSError, match="forced second commit failure"):
        expanded_report.rerender_saved_report_pages(summary, tmp_path, {})

    assert _bundle_bytes(tmp_path) == original
    assert not list(tmp_path.glob(".*.tmp"))
    assert not list(tmp_path.glob(".*.rollback"))


def test_report_bundle_rolls_back_when_post_publish_validation_fails(tmp_path, monkeypatch):
    summary, _ = _write_saved_bundle(tmp_path)
    original = _bundle_bytes(tmp_path)
    monkeypatch.setattr(
        expanded_report,
        "validate_full_report",
        lambda *_args, **_kwargs: {"status": "failed", "errors": ["forced validation failure"]},
    )

    with pytest.raises(RuntimeError, match="forced validation failure"):
        expanded_report.rerender_saved_report_pages(summary, tmp_path, {})

    assert _bundle_bytes(tmp_path) == original


def test_report_bundle_surfaces_incomplete_rollback(tmp_path, monkeypatch):
    summary, _ = _write_saved_bundle(tmp_path)
    real_commit = expanded_report._commit_staged_file
    calls = []

    def fail_second_commit(staged, target):
        calls.append(Path(target).name)
        if len(calls) == 2:
            raise OSError("publish failed")
        real_commit(staged, target)

    monkeypatch.setattr(expanded_report, "_commit_staged_file", fail_second_commit)
    monkeypatch.setattr(
        expanded_report,
        "_restore_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("rollback failed")),
    )

    with pytest.raises(expanded_report.ReportBundleTransactionError) as raised:
        expanded_report.rerender_saved_report_pages(summary, tmp_path, {})

    assert isinstance(raised.value.original_error, OSError)
    assert raised.value.rollback_errors


def test_validation_detects_page_hash_or_dom_identity_tampering(tmp_path):
    summary, _ = _write_saved_bundle(tmp_path)
    result = expanded_report.rerender_saved_report_pages(summary, tmp_path, {})
    report = tmp_path / "report.html"
    report.write_text(report.read_text(encoding="utf-8").replace(
        'data-report-build="', 'data-report-build="tampered-'
    ), encoding="utf-8")

    validation = expanded_report.validate_full_report(tmp_path, result["assets"])

    assert validation["status"] == "failed"
    assert any("body build marker mismatch" in error for error in validation["errors"])
    assert any("page SHA-256 mismatch" in error for error in validation["errors"])


def test_traceability_excludes_unmanifested_csv_and_png(tmp_path):
    summary, _ = _write_saved_bundle(tmp_path)
    compatibility = tmp_path / "tables" / "historical_compatibility"
    compatibility.mkdir()
    (compatibility / "declared.csv").write_text("field\nvalue\n", encoding="utf-8")
    (compatibility / "rogue.csv").write_text("field\nvalue\n", encoding="utf-8")
    (compatibility / "export_manifest.json").write_text(
        json.dumps({"tables": ["declared.csv"]}), encoding="utf-8"
    )
    (tmp_path / "tables" / "rogue.csv").write_text("field\nvalue\n", encoding="utf-8")
    (tmp_path / "assets" / "rogue.png").write_bytes(b"rogue")

    expanded_report.rerender_saved_report_pages(summary, tmp_path, {})
    technical = (tmp_path / "technical-details.html").read_text(encoding="utf-8")

    assert "historical_compatibility/declared.csv" in technical
    assert "rogue.csv" not in technical
    assert "rogue.png" not in technical


def test_saved_refresh_entrypoint_is_raw_free_and_preserves_enriched_export_manifest(
    tmp_path, monkeypatch
):
    _write_saved_bundle(tmp_path)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("saved refresh must not access or process raw EEG")

    monkeypatch.setattr(report, "read_raw", fail_if_called)
    monkeypatch.setattr(report, "prepare_analysis_raw", fail_if_called)
    monkeypatch.setattr(report, "run_auto_qc", fail_if_called)
    monkeypatch.setattr(eeg_io, "read_raw", fail_if_called)
    monkeypatch.setattr(eeg_io, "prepare_analysis_raw", fail_if_called)
    monkeypatch.setattr(eeg_qc, "run_auto_qc", fail_if_called)

    result = report.refresh_report_from_saved_artifacts(
        tmp_path / "analysis_summary.json"
    )

    export_manifest_path = result["historical_export_manifest_path"]
    export_manifest = json.loads(export_manifest_path.read_text(encoding="utf-8"))
    assert result["historical_table_count"] == 34
    assert (tmp_path / "tables" / "spatial_complexity.csv").is_file()
    technical = (tmp_path / "technical-details.html").read_text(encoding="utf-8")
    assert 'href="tables/spatial_complexity.csv"' in technical
    assert export_manifest["table_count"] == 34
    assert len(export_manifest["required_tables"]) == 34
    assert len(export_manifest["table_metadata"]) == 34
    for metadata in export_manifest["table_metadata"].values():
        assert set(metadata) == {"header", "data_row_count", "size_bytes", "sha256"}


def test_invalid_visual_manifest_does_not_modify_compatibility_outputs(tmp_path):
    _summary_data, manifest = _write_saved_bundle(tmp_path)
    compatibility = tmp_path / "tables" / "historical_compatibility"
    compatibility.mkdir()
    existing_csv = compatibility / "existing.csv"
    export_manifest = compatibility / "export_manifest.json"
    existing_csv.write_bytes(b"existing compatibility data\n")
    export_manifest.write_bytes(b'{"status":"existing"}\n')
    original_files = {
        path.name: path.read_bytes() for path in compatibility.iterdir() if path.is_file()
    }

    manifest["status"] = "failed"
    (tmp_path / "visual_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="unsupported status"):
        report.refresh_report_from_saved_artifacts(tmp_path / "analysis_summary.json")

    assert {
        path.name: path.read_bytes() for path in compatibility.iterdir() if path.is_file()
    } == original_files


def test_missing_required_visual_asset_does_not_modify_compatibility_outputs(
    tmp_path,
):
    _summary_data, manifest = _write_saved_bundle(tmp_path)
    compatibility = tmp_path / "tables" / "historical_compatibility"
    compatibility.mkdir()
    existing_csv = compatibility / "existing.csv"
    export_manifest = compatibility / "export_manifest.json"
    existing_csv.write_bytes(b"existing compatibility data\n")
    export_manifest.write_bytes(b'{"status":"existing"}\n')
    original_files = {
        path.name: path.read_bytes() for path in compatibility.iterdir() if path.is_file()
    }

    manifest["artifacts"] = [
        artifact for artifact in manifest["artifacts"] if artifact["name"] != "qc"
    ]
    (tmp_path / "visual_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="missing required report assets"):
        report.refresh_report_from_saved_artifacts(tmp_path / "analysis_summary.json")

    assert {
        path.name: path.read_bytes() for path in compatibility.iterdir() if path.is_file()
    } == original_files


def test_page_publish_failure_restores_compatibility_outputs(tmp_path, monkeypatch):
    _write_saved_bundle(tmp_path)
    compatibility = tmp_path / "tables" / "historical_compatibility"
    compatibility.mkdir()
    (compatibility / "existing.csv").write_bytes(b"existing compatibility data\n")
    (compatibility / "export_manifest.json").write_bytes(b'{"status":"existing"}\n')
    original_files = {
        path.name: path.read_bytes() for path in compatibility.iterdir() if path.is_file()
    }
    monkeypatch.setattr(
        expanded_report,
        "rerender_saved_report_pages",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("forced page publish failure")
        ),
    )

    with pytest.raises(RuntimeError, match="forced page publish failure"):
        report.refresh_report_from_saved_artifacts(tmp_path / "analysis_summary.json")

    assert {
        path.name: path.read_bytes() for path in compatibility.iterdir() if path.is_file()
    } == original_files
    assert not list(compatibility.parent.glob(".historical_compatibility.*.rollback"))
    assert not (compatibility.parent / "spatial_complexity.csv").exists()
    assert not list(compatibility.parent.glob(".spatial_complexity.csv.*.rollback"))
