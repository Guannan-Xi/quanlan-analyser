from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services.lab_demo_service import ensure_epilepsy_demo_dataset
from eeg_core.analysis.epilepsy_ml import run_epilepsy_ml


OUT_DIR = ROOT / "work" / "e2e_epilepsy_ml_migration" / "fixture_run"


def main() -> None:
    fixture = ensure_epilepsy_demo_dataset()
    file_payload = fixture["file"]
    outputs = run_epilepsy_ml(
        file_payload["stored_path"],
        OUT_DIR,
        {
            "method": "ml_epoch_classifier",
            "epoch_length_sec": 5,
            "probability_threshold": 0.5,
            "unit_mode": "source_compatible",
            "lab_fixture_id": fixture["fixture_id"],
        },
    )
    summary_path = outputs["epilepsy_ml_summary"]
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    spectrogram_path = outputs["epilepsy_ml_spectrogram"]
    spectrogram = json.loads(Path(spectrogram_path).read_text(encoding="utf-8"))
    spectrogram_checks = {
        "schema_version": spectrogram.get("schema_version") == "qlanalyser-epilepsy-ml-spectrogram-v0.1",
        "source_compatibility": "EpilepsyAnalysis2.py::calculate_spectrogram" in spectrogram.get("source_compatibility", ""),
        "method": spectrogram.get("method") == "scipy.signal.stft",
        "window_sec": float(spectrogram.get("parameters", {}).get("window_sec", 0)) == 4.0,
        "overlap_ratio": float(spectrogram.get("parameters", {}).get("overlap_ratio", 0)) == 0.9,
        "freq_min_hz": float(spectrogram.get("parameters", {}).get("freq_min_hz", 0)) == 0.5,
        "freq_max_hz": float(spectrogram.get("parameters", {}).get("freq_max_hz", 0)) == 50.0,
        "power_transform": spectrogram.get("parameters", {}).get("power_transform") == "10*log10(abs(Zxx)+1e-10)",
        "has_matrix": bool(spectrogram.get("frequencies_hz")) and bool(spectrogram.get("times_sec")) and bool(spectrogram.get("power_db")),
    }
    if not all(spectrogram_checks.values()):
        raise AssertionError(f"Epilepsy ML spectrogram checks failed: {spectrogram_checks}")
    figure_paths = {
        "event_timeline": Path(outputs["epilepsy_ml_event_timeline_figure"]),
        "spectrogram_preview": Path(outputs["epilepsy_ml_spectrogram_figure"]),
    }
    figure_checks = {}
    for name, figure_path in figure_paths.items():
        content = figure_path.read_text(encoding="utf-8") if figure_path.exists() else ""
        figure_checks[name] = {
            "exists": figure_path.exists(),
            "non_empty": figure_path.stat().st_size > 256 if figure_path.exists() else False,
            "is_svg": content.lstrip().startswith("<svg"),
            "has_research_boundary": "科研初筛支持" in content,
            "has_non_diagnostic_boundary": "诊断" in content and "临床" in content,
            "has_expected_title": (
                "癫痫样候选事件初筛时间轴" in content
                if name == "event_timeline"
                else "癫痫样事件初筛时频证据图" in content
            ),
        }
    failed_figure_checks = {
        name: checks
        for name, checks in figure_checks.items()
        if not all(checks.values())
    }
    if failed_figure_checks:
        raise AssertionError(f"Epilepsy ML figure checks failed: {failed_figure_checks}")
    evidence = {
        "status": "PASS",
        "fixture_id": fixture["fixture_id"],
        "file_id": file_payload["id"],
        "output_dir": str(OUT_DIR),
        "summary": summary,
        "spectrogram_checks": spectrogram_checks,
        "spectrogram_summary": {
            "path": str(spectrogram_path),
            "source_compatibility": spectrogram.get("source_compatibility"),
            "method": spectrogram.get("method"),
            "parameters": spectrogram.get("parameters"),
            "frequency_bins": len(spectrogram.get("frequencies_hz", [])),
            "time_bins": len(spectrogram.get("times_sec", [])),
        },
        "figure_checks": figure_checks,
        "outputs": {key: str(value) for key, value in outputs.items()},
    }
    out_path = ROOT / "work" / "e2e_epilepsy_ml_migration" / "fixture_run_evidence.json"
    out_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "PASS", "evidence": str(out_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
