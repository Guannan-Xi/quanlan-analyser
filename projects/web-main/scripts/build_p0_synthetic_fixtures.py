from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import mne
import numpy as np


P0_MODULES = ["preprocessing_readiness", "event_epoch", "psd_bandpower", "erp_p300"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic synthetic fixtures for QLanalyser P0 modules.")
    parser.add_argument("--out", default="work/fixtures/p0_modules")
    parser.add_argument("--seed", type=int, default=20260621)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    raw_path = out / "p0_synthetic_with_events_raw.fif"
    raw = _build_raw(args.seed)
    raw.save(raw_path, overwrite=True, verbose="ERROR")

    raw_meta = _file_meta(raw_path)
    common = {
        "schema_version": "qlanalyser-p0-fixture-manifest-v0.1",
        "created_at": datetime.now(UTC).isoformat(),
        "fixture_id": "p0_synthetic_with_events_v0_1",
        "privacy_status": "synthetic_only_no_real_participant_customer_or_phi",
        "source": "deterministic_mne_rawarray_generated_by_build_p0_synthetic_fixtures.py",
        "license_terms": "internal synthetic fixture for QLanalyser validation",
        "seed": args.seed,
        "raw_file": {"path": raw_path.name, **raw_meta},
        "sampling_rate_hz": float(raw.info["sfreq"]),
        "channel_names": list(raw.ch_names),
        "channel_count": len(raw.ch_names),
        "duration_sec": float(raw.times[-1] + 1.0 / raw.info["sfreq"]),
        "annotations": [
            {"onset": float(onset), "duration": float(duration), "description": str(desc)}
            for onset, duration, desc in zip(raw.annotations.onset, raw.annotations.duration, raw.annotations.description)
        ],
        "event_summary": {"standard": 8, "target": 4, "boundary": 1, "duplicate_target": 1},
        "non_diagnostic_boundary": "Synthetic research fixture only; not for clinical diagnosis or treatment decisions.",
    }
    (out / "fixture_manifest.json").write_text(json.dumps(common, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for module_id in P0_MODULES:
        _write_module_artifacts(out / module_id, module_id, common)
    print(json.dumps({"status": "built", "out": str(out), "modules": P0_MODULES, "raw": str(raw_path)}, ensure_ascii=False, indent=2))


def _build_raw(seed: int):
    sfreq = 200.0
    duration = 12.0
    times = np.arange(int(sfreq * duration)) / sfreq
    rng = np.random.default_rng(seed)
    ch_names = ["Fp1", "Fz", "Cz", "Pz", "P3", "P4", "Oz", "C3"]
    info = mne.create_info(ch_names, sfreq=sfreq, ch_types="eeg")
    alpha = 6e-6 * np.sin(2 * np.pi * 10.0 * times)
    theta = 1.5e-6 * np.sin(2 * np.pi * 6.0 * times)
    line = 0.4e-6 * np.sin(2 * np.pi * 50.0 * times)
    data = 0.25e-6 * rng.normal(size=(len(ch_names), len(times)))
    for idx in range(len(ch_names)):
        data[idx] += alpha * (1.0 - idx * 0.05) + theta * 0.2 + line
    target_onsets = [2.0, 4.0, 6.0, 8.0]
    for onset in target_onsets:
        center = onset + 0.32
        bump = 4e-6 * np.exp(-0.5 * ((times - center) / 0.045) ** 2)
        for ch in ["Pz", "P3", "P4"]:
            data[ch_names.index(ch)] += bump
    raw = mne.io.RawArray(data, info, verbose="ERROR")
    raw.set_montage("standard_1020", on_missing="ignore", verbose="ERROR")
    annotations = mne.Annotations(
        onset=[0.5, 1.0, 2.0, 3.0, 4.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.6, 11.9],
        duration=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.25, 0],
        description=[
            "boundary",
            "standard",
            "target",
            "standard",
            "target",
            "duplicate_target",
            "standard",
            "target",
            "standard",
            "target",
            "standard",
            "standard",
            "bad_segment",
            "standard",
        ],
    )
    raw.set_annotations(annotations)
    return raw


def _write_module_artifacts(module_dir: Path, module_id: str, common: dict[str, Any]) -> None:
    (module_dir / "reproducibility").mkdir(parents=True, exist_ok=True)
    (module_dir / "tables").mkdir(parents=True, exist_ok=True)
    manifest = {
        "module_id": module_id,
        "fixture_id": common["fixture_id"],
        "data_preparation_plan_id": "prep_p0_synthetic_v0_1",
        "parameters_hash": hashlib.sha256(module_id.encode()).hexdigest(),
        "non_diagnostic_boundary": common["non_diagnostic_boundary"],
        "source_data_refs": {"raw_file": "../p0_synthetic_with_events_raw.fif", "fixture_manifest": "../fixture_manifest.json"},
        "warnings": [],
    }
    if module_id in {"event_epoch", "erp_p300"}:
        manifest["epoch_set_id"] = "epochset_p0_synthetic_oddball_v0_1"
    if module_id == "preprocessing_readiness":
        manifest["bad_channels"] = ["Fp1"]
        manifest["bad_segments"] = [{"start_sec": 11.6, "duration_sec": 0.25, "reason": "synthetic_bad_segment"}]
    if module_id == "psd_bandpower":
        manifest["frequency_range_hz"] = [1.0, 40.0]
        manifest["nyquist_hz"] = common["sampling_rate_hz"] / 2.0
        _write_csv(module_dir / "tables" / "band_power.csv", ["band", "value", "unit"], [["alpha", "1.0", "uV^2/Hz"], ["beta", "0.2", "uV^2/Hz"]])
        _write_json(module_dir / "reproducibility" / "table_dictionary.json", {"tables/band_power.csv": {"columns": {"band": {"unit": "label"}, "value": {"unit": "uV^2/Hz"}, "unit": {"unit": "text"}}}})
    if module_id == "event_epoch":
        _write_csv(module_dir / "tables" / "events.csv", ["event_id", "label", "onset_sec"], [["1", "standard", "1.0"], ["2", "target", "2.0"]])
        _write_json(module_dir / "reproducibility" / "epoch_set_manifest.json", {"epoch_set_id": manifest["epoch_set_id"], "event_counts": {"standard": 8, "target": 4}})
    if module_id == "erp_p300":
        _write_csv(module_dir / "tables" / "erp_metrics.csv", ["condition", "component", "latency_ms", "amplitude_uv", "unit"], [["target", "P300", "320", "4.2", "uV"]])
        _write_json(module_dir / "reproducibility" / "epoch_set_manifest.json", {"epoch_set_id": manifest["epoch_set_id"], "event_counts": {"standard": 8, "target": 4}})
    _write_json(module_dir / "result.json", manifest)
    _write_json(module_dir / "reproducibility" / "workflow.json", {"steps": ["synthetic_fixture_build", module_id]})
    _write_json(module_dir / "reproducibility" / "software_versions.json", {"mne": mne.__version__, "numpy": np.__version__})
    _write_json(module_dir / "manifest.json", {"module_id": module_id, "files": sorted(str(p.relative_to(module_dir)).replace("\\", "/") for p in module_dir.rglob("*") if p.is_file())})


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _file_meta(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"size_bytes": path.stat().st_size, "sha256": digest.hexdigest()}


if __name__ == "__main__":
    main()
