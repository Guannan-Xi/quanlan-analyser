"""Composable entry points for the recovered 64-channel analysis methods."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from .complexity import ComplexityConfig, compute_complexity
from .aperiodic import AperiodicConfig, compute_aperiodic_spectrum
from .connectivity import ConnectivityConfig, compute_connectivity
from .coupling import CouplingConfig, compute_coupling
from .gfp import GFPConfig, compute_gfp_gmd
from .io import file_sha256, prepare_analysis_raw, read_raw
from .microstates import MicrostateConfig, compute_microstates
from .preprocess import PreprocessConfig, preprocess_full_recording
from .qc import QCConfig, run_auto_qc
from .spectral import SpectralConfig, compute_spectral_features
from .spatial import compute_spatial_complexity


def run_full_recording_spectral_pipeline(input_path, output_dir, *, preprocess: PreprocessConfig | None = None, spectral: SpectralConfig | None = None):
    """Run only the validated spectral baseline on a complete continuous recording."""
    source, destination = Path(input_path), Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    source_raw = read_raw(source, preload=True)
    raw, input_preparation = prepare_analysis_raw(source_raw)
    processed, preprocessing = preprocess_full_recording(raw, preprocess)
    result = _base_summary(source, source_raw, processed, input_preparation)
    result.update({"pipeline": "qlanalyser_eeg64.spectral_baseline", "input_preparation": input_preparation, "preprocessing": preprocessing, "spectral": compute_spectral_features(processed, spectral)})
    return _write_summary(destination, result)


def run_recovered_full_pipeline(input_path, output_dir, *, qc: QCConfig | None = None, spectral: SpectralConfig | None = None, gfp: GFPConfig | None = None, microstates: MicrostateConfig | None = None, complexity: ComplexityConfig | None = None, connectivity: ConnectivityConfig | None = None, coupling: CouplingConfig | None = None, aperiodic: AperiodicConfig | None = None, include_aperiodic: bool = False):
    """Run all recovered methods on full-record QC-retained samples.

    A blocked safety gate is never converted to a pass by this function. The
    resulting quantitative outputs are retained as descriptive review material.
    """
    source, destination = Path(input_path), Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    source_raw = read_raw(source, preload=True)
    raw, input_preparation = prepare_analysis_raw(source_raw)
    cleaned, qc_result = run_auto_qc(raw, qc)
    result = _base_summary(source, source_raw, cleaned, input_preparation)
    result.update({"pipeline": "qlanalyser_eeg64.recovered_full_recording", "input_preparation": input_preparation, "quality_control": qc_result, "safety_gate": qc_result["safety_gate"], "spectral": compute_spectral_features(cleaned, spectral), "gfp_gmd": compute_gfp_gmd(cleaned, gfp, source_time_mapping=qc_result["source_time_mapping"]), "microstates": compute_microstates(cleaned, microstates, source_epoch_rows=qc_result["epochs"]), "complexity": compute_complexity(cleaned, complexity), "spatial_complexity": compute_spatial_complexity(cleaned), "connectivity": compute_connectivity(cleaned, connectivity), "coupling": compute_coupling(cleaned, coupling)})
    if include_aperiodic:
        result["aperiodic_spectrum"] = compute_aperiodic_spectrum(cleaned, aperiodic)
    return _write_summary(destination, result)


def run_recovered_full_report_pipeline(input_path, output_dir, **kwargs):
    """Run all recovered analyses and render the standalone HTML report.

    The renderer reloads the BDF and verifies its SHA256 against the freshly
    written summary.  This provides one reproducible command from raw input to
    figures, tables, HTML pages, and visual-manifest checks.
    """
    result = run_recovered_full_pipeline(input_path, output_dir, **kwargs)
    from .report import render_report_from_summary

    rendered = render_report_from_summary(input_path, result["summary_path"], output_dir)
    return {**result, "report": rendered}


def _base_summary(source, raw, analysed, input_preparation):
    source_eeg_channels = input_preparation["source_eeg_channels"]
    return {"version": "0.2.0", "created_at_utc": datetime.now(UTC).isoformat(), "source": {"filename": source.name, "sha256": file_sha256(source), "sampling_rate_hz": float(raw.info["sfreq"]), "duration_sec": float(raw.n_times / raw.info["sfreq"])}, "analysis_data": {"scope": "complete_recording", "sampling_rate_hz": float(analysed.info["sfreq"]), "duration_sec": float(analysed.n_times / analysed.info["sfreq"]), "eeg_channels": analysed.ch_names}}


def _write_summary(destination, result):
    path = destination / "analysis_summary.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return {"summary_path": path, "summary": result}
