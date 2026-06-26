from __future__ import annotations

import csv
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mne
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "frontend" / "assets" / "customer_oddball_case"
SOURCE_EDF = ROOT / "frontend" / "assets" / "teaching_oddball.edf"
SOURCE_EVENTS = ROOT / "frontend" / "assets" / "teaching_oddball_events.tsv"
SOURCE_SUBJECT_METRICS = ROOT / "frontend" / "assets" / "subject_level_metrics.csv"
SOURCE_STATISTICS = ROOT / "frontend" / "assets" / "statistics_summary.csv"
SOURCE_METHODS = ROOT / "frontend" / "assets" / "methods_snippet.txt"
SOURCE_CAPTION = ROOT / "frontend" / "assets" / "figure_caption.txt"
SOURCE_ANALYSIS_MANIFEST = ROOT / "frontend" / "assets" / "analysis_manifest.json"
SOURCE_SUMMARY = ROOT / "work" / "learning_case" / "teaching_oddball_run_summary.json"
PACKAGE_ZIP = ASSET_DIR / "customer_oddball_erp_package.zip"

CHANNEL_PLOT = "Pz"
TIMEPOINT_SEC = 0.34
ERP_TMIN = -0.2
ERP_TMAX = 0.8
ERP_BASELINE = (None, 0.0)
ERP_L_FREQ = 0.1
ERP_H_FREQ = 30.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def ensure_dir() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)


def copy_static_assets() -> dict[str, Path]:
    copied: dict[str, Path] = {}
    mapping = {
        "sub-001_oddball.edf": SOURCE_EDF,
        "sub-002_oddball.edf": SOURCE_EDF,
        "sub-001_events.tsv": SOURCE_EVENTS,
        "sub-002_events.tsv": SOURCE_EVENTS,
        "customer_subject_level_metrics.csv": SOURCE_SUBJECT_METRICS,
        "customer_statistics_summary.csv": SOURCE_STATISTICS,
        "customer_methods.txt": SOURCE_METHODS,
        "customer_figure_caption.txt": SOURCE_CAPTION,
    }
    for target_name, source_path in mapping.items():
        target_path = ASSET_DIR / target_name
        shutil.copy2(source_path, target_path)
        copied[target_name] = target_path
    shutil.copy2(SOURCE_ANALYSIS_MANIFEST, ASSET_DIR / "customer_analysis_reference_manifest.json")
    if SOURCE_SUMMARY.exists():
        shutil.copy2(SOURCE_SUMMARY, ASSET_DIR / "customer_oddball_run_summary.json")
    return copied


def generate_erp_plot(target_dir: Path) -> Path:
    raw = mne.io.read_raw_edf(str(SOURCE_EDF), preload=True, verbose="ERROR")
    raw.set_montage("standard_1020", on_missing="ignore", verbose="ERROR")
    raw.filter(ERP_L_FREQ, ERP_H_FREQ, verbose="ERROR")
    events, event_id = mne.events_from_annotations(raw, verbose="ERROR")
    if not events.size:
        raise RuntimeError("No annotations found in teaching oddball EDF")
    selected = {key: value for key, value in event_id.items() if key in {"standard", "target"}}
    if set(selected) != {"standard", "target"}:
        raise RuntimeError(f"Expected standard and target annotations, got {selected}")
    epochs = mne.Epochs(
        raw,
        events,
        event_id=selected,
        tmin=ERP_TMIN,
        tmax=ERP_TMAX,
        baseline=ERP_BASELINE,
        preload=True,
        verbose="ERROR",
    )
    evoked_standard = epochs["standard"].average().copy().pick([CHANNEL_PLOT])
    evoked_target = epochs["target"].average().copy().pick([CHANNEL_PLOT])
    times_ms = evoked_standard.times * 1000.0

    fig, ax = plt.subplots(figsize=(10, 5), dpi=160)
    ax.plot(times_ms, evoked_standard.data[0] * 1e6, label="standard", color="#64748b", linewidth=2.0)
    ax.plot(times_ms, evoked_target.data[0] * 1e6, label="target", color="#dc2626", linewidth=2.4)
    ax.axvspan(280, 450, color="#f59e0b", alpha=0.15, label="P300 window")
    ax.axvline(0, color="#111827", linestyle="--", linewidth=1.0, alpha=0.7)
    ax.set_title("Customer Oddball ERP at Pz")
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Amplitude (uV)")
    ax.grid(True, alpha=0.2)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    output = target_dir / "customer_oddball_erp_pz.png"
    fig.savefig(output, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return output


def generate_topomap_plot(target_dir: Path) -> Path:
    raw = mne.io.read_raw_edf(str(SOURCE_EDF), preload=True, verbose="ERROR")
    raw.set_montage("standard_1020", on_missing="ignore", verbose="ERROR")
    raw.filter(ERP_L_FREQ, ERP_H_FREQ, verbose="ERROR")
    events, event_id = mne.events_from_annotations(raw, verbose="ERROR")
    selected = {key: value for key, value in event_id.items() if key in {"standard", "target"}}
    epochs = mne.Epochs(
        raw,
        events,
        event_id=selected,
        tmin=ERP_TMIN,
        tmax=ERP_TMAX,
        baseline=ERP_BASELINE,
        preload=True,
        verbose="ERROR",
    )
    evoked_target = epochs["target"].average().copy().pick("eeg")
    evoked_standard = epochs["standard"].average().copy().pick("eeg")
    diff = mne.EvokedArray(evoked_target.data - evoked_standard.data, evoked_target.info.copy(), tmin=evoked_target.times[0])
    times = diff.times
    idx = int(np.argmin(np.abs(times - TIMEPOINT_SEC)))
    data_uv = diff.data[:, idx] * 1e6
    fig, ax = plt.subplots(figsize=(7.4, 6.2), dpi=160)
    mne.viz.plot_topomap(
        data_uv,
        diff.info,
        axes=ax,
        show=False,
        cmap="RdBu_r",
        contours=6,
        sensors=True,
        names=None,
        vlim=(-np.max(np.abs(data_uv)), np.max(np.abs(data_uv))),
    )
    ax.set_title("Target - Standard P300, 340 ms", pad=16)
    output = target_dir / "customer_oddball_p300_topomap.png"
    fig.savefig(output, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return output


def write_manifest(files: list[Path]) -> Path:
    manifest = {
        "schema_version": "qlanalyser-customer-oddball-case-v1",
        "generated_at": utc_now(),
        "case_name": "customer_oddball_case",
        "source": {
            "edf": "teaching_oddball.edf",
            "events_tsv": "teaching_oddball_events.tsv",
            "analysis_reference_manifest": "customer_analysis_reference_manifest.json",
            "learning_case_summary": "customer_oddball_run_summary.json",
        },
        "analysis_notes": [
            "Files in this folder are customer-facing aliases of the teaching oddball sample.",
            "The EDF/event pair is duplicated under sub-001 and sub-002 names so the UI can offer multiple selectable examples without dead links.",
            "Images were generated from the teaching oddball sample and summarize the Pz waveform and the 340 ms target-standard topography.",
        ],
        "files": [
            {
                "path": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in files
        ],
    }
    manifest_path = ASSET_DIR / "customer_analysis_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def build_package() -> Path:
    files = sorted(path for path in ASSET_DIR.iterdir() if path.is_file() and path.name != PACKAGE_ZIP.name)
    temp_zip = PACKAGE_ZIP.with_suffix(".tmp")
    if temp_zip.exists():
        temp_zip.unlink()
    with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.name)
    temp_zip.replace(PACKAGE_ZIP)
    return PACKAGE_ZIP


def main() -> int:
    ensure_dir()
    copied = copy_static_assets()
    generated = [
        generate_erp_plot(ASSET_DIR),
        generate_topomap_plot(ASSET_DIR),
    ]
    manifest_path = write_manifest(list(copied.values()) + generated + [ASSET_DIR / "customer_analysis_reference_manifest.json"])
    package_path = build_package()

    summary = {
        "status": "passed",
        "generated_at": utc_now(),
        "asset_dir": str(ASSET_DIR),
        "manifest": str(manifest_path),
        "package": str(package_path),
        "files": sorted([path.name for path in ASSET_DIR.iterdir() if path.is_file()]),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
