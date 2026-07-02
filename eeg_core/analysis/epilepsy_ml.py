from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import json
import logging
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import scipy.signal
import scipy.stats

from eeg_core.io.readers import read_raw
from eeg_core.report.reproducibility import (
    write_analysis_sidecars,
    write_output_contract,
    write_reproducibility_files,
)


RESOURCE_ROOT = Path(__file__).resolve().parents[1] / "resources" / "epilepsy_ml"
MODEL_MANIFEST_PATH = RESOURCE_ROOT / "model_manifest.json"

FEATURE_COLUMNS = [
    "mean",
    "mobility",
    "TKEO",
    "P_delta",
    "P_theta",
    "P_alpha",
    "P_beta",
    "P_gamma",
    "P_total",
    "rel_delta",
    "rel_theta",
    "rel_alpha",
    "rel_beta",
    "rel_gamma",
    "pfd",
    "skew",
    "kurtosis",
    "var",
    "envelope",
]

EPILEPSY_ML_PARAMETER_SCHEMA = {
    "workflow_id": {"type": "string", "default": "epilepsy_ml_xgboost"},
    "method": {"type": "string", "default": "ml_epoch_classifier", "enum": ["ml_epoch_classifier"]},
    "eeg_channel": {"type": ["string", "null"], "default": "EEG3"},
    "epoch_length_sec": {"type": "number", "default": 5.0, "enum": [3.0, 5.0]},
    "probability_threshold": {"type": "number", "default": 0.5, "const": 0.5},
    "unit_mode": {
        "type": "string",
        "default": "source_compatible",
        "enum": ["source_compatible", "raw", "mne_volts_to_uv"],
    },
    "bad_channels": {"type": "array", "items": "string", "default": []},
    "feature_chunk_epochs": {"type": "integer", "default": 256, "minimum": 1},
    "feature_worker_count": {"type": "integer", "default": 1, "minimum": 1},
    "spectrogram_preview_duration_sec": {"type": "number", "default": 600.0, "minimum": 1},
}


def run_epilepsy_ml(input_path: str | Path, output_dir: str | Path, parameters: dict | None = None) -> dict[str, Path]:
    output_path = Path(output_dir)
    tables = output_path / "tables"
    data_dir = output_path / "data"
    figures = output_path / "figures"
    reproducibility = output_path / "reproducibility"
    for directory in (tables, data_dir, figures, reproducibility):
        directory.mkdir(parents=True, exist_ok=True)

    raw = read_raw(input_path, preload=False)
    params = _validate_parameters(parameters)
    missing_bad_channels = [channel for channel in params["bad_channels"] if channel not in raw.ch_names]
    if missing_bad_channels:
        raise ValueError(f"Epilepsy ML bad channels not found: {', '.join(missing_bad_channels)}")
    raw.info["bads"] = sorted(set(raw.info.get("bads", [])) | set(params["bad_channels"]))

    channel, channel_warning = _select_eeg_channel(raw, params["eeg_channel"])
    sfreq = float(raw.info["sfreq"])
    data, unit_note = _selected_channel_data(raw, input_path, channel, params["unit_mode"])
    n_times = int(data.size)
    duration_sec = float(n_times / sfreq) if sfreq > 0 else 0.0

    manifest = _validated_model_manifest()
    model_info, selected_model_epoch = _model_info_for_epoch(params["epoch_length_sec"], manifest)
    model, scaler = _load_model_and_scaler(model_info)

    epoch_samples = int(params["epoch_length_sec"] * sfreq)
    if epoch_samples <= 0:
        raise ValueError("Epilepsy ML epoch_samples must be > 0")
    n_epochs = len(data) // epoch_samples
    if n_epochs <= 0:
        raise ValueError("Epilepsy ML input is shorter than one complete epoch")

    processing_plan = _build_processing_plan(
        n_times=n_times,
        n_epochs=n_epochs,
        epoch_samples=epoch_samples,
        feature_chunk_epochs=params["feature_chunk_epochs"],
        feature_worker_count=params["feature_worker_count"],
        spectrogram_preview_duration_sec=params["spectrogram_preview_duration_sec"],
        sfreq=sfreq,
    )
    features = extract_features_using_epochs_chunked(
        data,
        sfreq,
        epoch_samples=epoch_samples,
        n_epochs=n_epochs,
        chunk_epochs=params["feature_chunk_epochs"],
        worker_count=params["feature_worker_count"],
    )
    feature_diagnostics = _feature_matrix_diagnostics(features)
    features_scaled = scaler.transform(features)
    probabilities = model.predict_proba(features_scaled)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)

    event_rows, window_rows, event_mask = detect_seizures_source_compatible(
        predictions,
        data,
        sfreq,
        epoch_length=params["epoch_length_sec"],
        start_time_ts=_measurement_timestamp(raw),
    )
    epoch_rows = _build_epoch_rows(predictions, probabilities, event_mask, params["epoch_length_sec"], duration_sec)

    epoch_scores_path = tables / "epilepsy_ml_epoch_predictions.csv"
    _write_csv(
        epoch_scores_path,
        [
            "epoch_index",
            "Epoch No.",
            "start_sec",
            "end_sec",
            "duration_sec",
            "Stage_Code",
            "Stage",
            "probability",
            "above_threshold",
            "is_event_epoch",
            "mean_rms",
            "threshold",
        ],
        epoch_rows,
    )
    events_path = tables / "epilepsy_ml_events.csv"
    _write_csv(
        events_path,
        [
            "event_id",
            "start_sec",
            "end_sec",
            "duration_sec",
            "start_epoch",
            "end_epoch",
            "source_start_epoch_1based",
            "source_end_epoch_1based",
            "epoch_count",
            "rms",
            "max_abs_amplitude",
        ],
        event_rows,
    )
    window_stats_path = tables / "epilepsy_ml_window_stats_30min.csv"
    _write_csv(
        window_stats_path,
        [
            "window_index",
            "start_sec",
            "end_sec",
            "duration_sec",
            "event_count",
            "seizure_frequency_events_per_hour",
        ],
        window_rows,
    )
    features_path = tables / "epilepsy_ml_features.csv"
    _write_array_csv(features_path, FEATURE_COLUMNS, features)
    features_scaled_path = tables / "epilepsy_ml_features_scaled.csv"
    _write_array_csv(features_scaled_path, FEATURE_COLUMNS, features_scaled)
    spectrogram_samples = int(min(data.size, max(1, round(params["spectrogram_preview_duration_sec"] * sfreq))))
    spectrogram_payload = _build_pc_compatible_spectrogram_payload(
        data[:spectrogram_samples],
        sfreq,
        channel,
        full_duration_sec=duration_sec,
        preview_start_sec=0.0,
    )
    spectrogram_path = data_dir / "epilepsy_ml_spectrogram.json"
    spectrogram_path.write_text(json.dumps(spectrogram_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    event_timeline_figure_path = figures / "epilepsy_ml_event_timeline.svg"
    event_timeline_figure_path.write_text(
        _build_event_timeline_svg(epoch_rows, event_rows, duration_sec, channel),
        encoding="utf-8",
    )
    spectrogram_figure_path = figures / "epilepsy_ml_spectrogram_preview.svg"
    spectrogram_figure_path.write_text(
        _build_spectrogram_svg(spectrogram_payload),
        encoding="utf-8",
    )

    model_manifest_output_path = reproducibility / "epilepsy_ml_model_manifest.json"
    model_manifest_output_path.write_text(
        json.dumps(
            {
                "manifest": manifest,
                "selected_model_epoch_length_sec": selected_model_epoch,
                "selected_model_file": model_info["model_file"],
                "selected_scaler_file": model_info["scaler_file"],
                "hash_validation": "passed",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    warnings = [
        {
            "name": "non_medical_scope",
            "detail": "Research screening/support only; not for diagnosis, treatment, or clinical decision-making.",
        }
    ]
    scale_warning = _selected_channel_scale_warning(data, channel, params["unit_mode"])
    if scale_warning:
        warnings.append(scale_warning)
    if feature_diagnostics["clipped_or_non_finite_value_count"] > 0:
        warnings.append(
            {
                "name": "feature_scale_review_recommended",
                "detail": (
                    "Feature extraction produced non-finite or clipped values before model scoring. "
                    "Review EDF physical units/source scaling and high-amplitude artifacts before customer-facing interpretation."
                ),
                **feature_diagnostics,
            }
        )
    if channel_warning:
        warnings.append({"name": "channel_fallback", "detail": channel_warning})
    if selected_model_epoch != params["epoch_length_sec"]:
        warnings.append(
            {
                "name": "source_default_5s_model",
                "detail": "Source ML code falls back to the 5-second model when epoch_length is not exactly 3.0 or 5.0.",
            }
        )

    summary = {
        "status": "computed",
        "module": "epilepsy_ml",
        "method": "ml_epoch_classifier",
        "source_compatibility": "AR_analyser1 EpilepsyAnalysis_ML.py feature/model path",
        "scope": "research_screening_support_only",
        "channel": channel,
        "sfreq": sfreq,
        "duration_sec": duration_sec,
        "samples": n_times,
        "epoch_count": len(epoch_rows),
        "event_count": len(event_rows),
        "threshold": 0.5,
        "probability_threshold": 0.5,
        "max_probability": float(np.max(probabilities)) if probabilities.size else None,
        "mean_probability": float(np.mean(probabilities)) if probabilities.size else None,
        "selected_model_epoch_length_sec": selected_model_epoch,
        "unit_mode": params["unit_mode"],
        "unit_note": unit_note,
        "feature_columns": FEATURE_COLUMNS,
        "feature_diagnostics": feature_diagnostics,
        "processing_plan": processing_plan,
        "spectrogram": {
            "artifact": "data/epilepsy_ml_spectrogram.json",
            "figure": "figures/epilepsy_ml_spectrogram_preview.svg",
            "source_compatibility": spectrogram_payload["source_compatibility"],
            "method": spectrogram_payload["method"],
            "parameters": spectrogram_payload["parameters"],
            "preview": spectrogram_payload["preview"],
        },
        "figures": {
            "event_timeline": "figures/epilepsy_ml_event_timeline.svg",
            "spectrogram_preview": "figures/epilepsy_ml_spectrogram_preview.svg",
            "scope": "result_review_visual_evidence_only",
        },
        "parameters": params,
        "warnings": warnings,
    }
    summary_path = reproducibility / "epilepsy_ml_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    parameters_path = reproducibility / "parameters.json"
    parameters_path.write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")
    method_path = reproducibility / "method_description.txt"
    method_path.write_text(
        "Epilepsy ML source-compatible runner uses the original AR_analyser1 XGBoost model/scaler files, "
        "the original 19-column feature order, floor epoch truncation, predict_proba[:, 1], fixed threshold "
        "0.5, and source-compatible event aggregation requiring at least two consecutive seizure epochs. "
        "This output is research screening/support only and must not be used for diagnosis, treatment, "
        "or clinical decision-making.\n",
        encoding="utf-8",
    )

    reproducibility_paths = write_reproducibility_files(
        output_path,
        module_name="epilepsy_ml",
        input_path=input_path,
        parameters=params,
        workflow_steps=[
            {"name": "read_raw_header", "description": "Read EEG header without preloading all channels."},
            {"name": "select_eeg_channel", "description": "Use requested channel, source default EEG3, or first usable EEG fallback."},
            {"name": "load_selected_channel", "description": "Load only the selected EEG channel for ML scoring."},
            {"name": "source_unit_mode", "description": "Apply source-compatible EDF/BDF volts-to-microvolts handling when configured."},
            {"name": "asset_hash_validation", "description": "Validate model and scaler SHA256 before loading."},
            {"name": "chunked_feature_extraction", "description": "Extract the original 19 ML features from complete epochs in bounded chunks."},
            {"name": "bounded_pc_compatible_stft", "description": "Write a bounded EpilepsyAnalysis2.py-compatible STFT evidence preview."},
            {"name": "xgboost_probability", "description": "Run scaler.transform and model.predict_proba(features_scaled)[:, 1]."},
            {"name": "source_event_detection", "description": "Aggregate at least two consecutive seizure epochs into candidate events."},
            {"name": "write_outputs", "description": "Write epoch, event, feature, result figure, manifest, summary, sidecar, and contract files."},
        ],
    )
    sidecar_paths = write_analysis_sidecars(
        output_path,
        module_name="epilepsy_ml",
        parameter_schema=EPILEPSY_ML_PARAMETER_SCHEMA,
        effective_call={
            "engine": "joblib+xgboost",
            "call": "model.predict_proba(scaler.transform(features))[:, 1]",
            "kwargs": {
                "method": params["method"],
                "epoch_length_sec": params["epoch_length_sec"],
                "probability_threshold": 0.5,
                "selected_model_epoch_length_sec": selected_model_epoch,
                "unit_mode": params["unit_mode"],
                "feature_chunk_epochs": params["feature_chunk_epochs"],
                "feature_worker_count": params["feature_worker_count"],
                "spectrogram_preview_duration_sec": params["spectrogram_preview_duration_sec"],
            },
            "input_shape": {"channel": channel, "n_times": n_times, "sfreq": sfreq},
            "output_shape": {"epochs": len(epoch_rows), "events": len(event_rows), "features": list(features.shape)},
        },
        threshold_validation={
            "status": "passed",
            "checks": [
                {"field": "method", "rule": "== ml_epoch_classifier", "value": params["method"], "status": "passed"},
                {"field": "feature_count", "rule": "== 19", "value": int(features.shape[1]), "status": "passed"},
                {"field": "probability_threshold", "rule": "== source fixed 0.5", "value": 0.5, "status": "passed"},
                {"field": "model_hashes", "rule": "manifest SHA256 validation", "value": "passed", "status": "passed"},
            ],
        },
        table_dictionary=_table_dictionary(),
        scope_contract={
            "analysis_scope": "single_record_epilepsy_ml_source_compatible_research_screening",
            "stable_status": "source_model_migration_v0",
            "allowed_claims": [
                "Run the source AR_analyser1 epoch-level ML classifier on one EEG channel.",
                "Summarize ML-derived candidate events for research screening/support.",
            ],
            "disallowed_claims": [
                "diagnosis",
                "treatment_recommendation",
                "clinical_decision",
                "seizure_confirmation",
                "medical_triage",
            ],
            "required_boundary": "Research screening/support only; no diagnosis, treatment, or clinical decision-making.",
        },
        source_metadata=_source_metadata(input_path, raw, channel, params, selected_model_epoch, unit_note),
    )

    outputs = {
        "epilepsy_epoch_scores": epoch_scores_path,
        "epilepsy_events": events_path,
        "epilepsy_window_stats_30min": window_stats_path,
        "epilepsy_summary": summary_path,
        "epilepsy_ml_epoch_predictions": epoch_scores_path,
        "epilepsy_ml_events": events_path,
        "epilepsy_ml_window_stats_30min": window_stats_path,
        "epilepsy_ml_features": features_path,
        "epilepsy_ml_features_scaled": features_scaled_path,
        "epilepsy_ml_spectrogram": spectrogram_path,
        "epilepsy_ml_event_timeline_figure": event_timeline_figure_path,
        "epilepsy_ml_spectrogram_figure": spectrogram_figure_path,
        "epilepsy_ml_summary": summary_path,
        "epilepsy_ml_model_manifest": model_manifest_output_path,
        "parameters": parameters_path,
        "method_description": method_path,
        "software_versions": reproducibility_paths["software_versions"],
        "workflow": reproducibility_paths["workflow"],
        "parameter_schema_snapshot": sidecar_paths["parameter_schema_snapshot"],
        "threshold_validation": sidecar_paths["threshold_validation"],
        "effective_call": sidecar_paths["effective_call"],
        "source_metadata": sidecar_paths["source_metadata"],
        "table_dictionary": sidecar_paths["table_dictionary"],
        "scope_contract": sidecar_paths["scope_contract"],
    }
    contract_paths = write_output_contract(
        output_path,
        job_type="epilepsy_ml_xgboost",
        module_name="epilepsy_ml",
        input_path=input_path,
        parameters=params,
        summary=summary,
        outputs=outputs,
        log_lines=[
            f"channel={channel}",
            "probability_threshold=0.5",
            f"epoch_count={len(epoch_rows)}",
            f"event_count={len(event_rows)}",
            f"model_epoch={selected_model_epoch}",
            "spectrogram=EpilepsyAnalysis2.py_stft_4s_90pct_overlap_0.5_50hz",
            "figures=event_timeline_svg,spectrogram_preview_svg",
            "scope=research_screening_support_only_no_diagnosis_treatment_or_clinical_decision",
        ],
    )
    return {**outputs, **contract_paths}


def _build_pc_compatible_spectrogram_payload(
    data: np.ndarray,
    sfreq: float,
    channel: str,
    *,
    full_duration_sec: float | None = None,
    preview_start_sec: float = 0.0,
) -> dict[str, Any]:
    source_nperseg = max(1, int(float(sfreq) * 4))
    effective_nperseg = min(source_nperseg, max(1, int(data.size)))
    source_noverlap = int(source_nperseg * 0.9)
    effective_noverlap = min(int(effective_nperseg * 0.9), max(0, effective_nperseg - 1))
    frequencies, times, zxx = scipy.signal.stft(
        data,
        fs=sfreq,
        nperseg=effective_nperseg,
        noverlap=effective_noverlap,
        boundary="zeros",
    )
    power = 10 * np.log10(np.abs(zxx) + 1e-10)
    good_freqs = np.logical_and(frequencies >= 0.5, frequencies <= 50)
    filtered_freqs = frequencies[good_freqs]
    filtered_power = power[good_freqs, :]
    finite_power = filtered_power[np.isfinite(filtered_power)]
    if finite_power.size:
        vmin = float(np.percentile(finite_power, 10))
        vmax = float(np.percentile(finite_power, 99))
    else:
        vmin = 0.0
        vmax = 1.0
    max_time_bins = 2400
    if filtered_power.shape[1] > max_time_bins:
        keep = np.unique(np.linspace(0, filtered_power.shape[1] - 1, max_time_bins).astype(int))
        filtered_power = filtered_power[:, keep]
        times = times[keep]
        display_decimation = {
            "applied": True,
            "max_time_bins": max_time_bins,
            "original_time_bins": int(power.shape[1]),
            "retained_time_bins": int(filtered_power.shape[1]),
            "policy": "uniform_time_bin_retention_after_pc_stft",
        }
    else:
        display_decimation = {
            "applied": False,
            "original_time_bins": int(power.shape[1]),
            "retained_time_bins": int(filtered_power.shape[1]),
        }
    return {
        "schema_version": "qlanalyser-epilepsy-ml-spectrogram-v0.1",
        "source_compatibility": "AR_analyser1/AR_analyser_PC/src/EpilepsyAnalysis2.py::calculate_spectrogram",
        "method": "scipy.signal.stft",
        "channel": channel,
        "sfreq": float(sfreq),
        "duration_sec": float(data.size / sfreq) if sfreq else 0.0,
        "full_record_duration_sec": float(full_duration_sec) if full_duration_sec is not None else (float(data.size / sfreq) if sfreq else 0.0),
        "preview": {
            "is_bounded_preview": bool(
                full_duration_sec is not None and sfreq and float(data.size / sfreq) < float(full_duration_sec)
            ),
            "start_sec": float(preview_start_sec),
            "duration_sec": float(data.size / sfreq) if sfreq else 0.0,
            "samples": int(data.size),
            "policy": "pc_compatible_stft_on_bounded_review_window",
            "note": "The candidate-event classifier is computed over all complete epochs; this STFT artifact is a bounded review preview for long records.",
        },
        "parameters": {
            "window_sec": 4.0,
            "overlap_ratio": 0.9,
            "source_nperseg": int(source_nperseg),
            "source_noverlap": int(source_noverlap),
            "effective_nperseg": int(effective_nperseg),
            "effective_noverlap": int(effective_noverlap),
            "boundary": "zeros",
            "freq_min_hz": 0.5,
            "freq_max_hz": 50.0,
            "power_transform": "10*log10(abs(Zxx)+1e-10)",
            "vmin_percentile": 10,
            "vmax_percentile": 99,
        },
        "display_decimation": display_decimation,
        "frequencies_hz": np.round(filtered_freqs.astype(float), 4).tolist(),
        "times_sec": np.round(times.astype(float), 4).tolist(),
        "power_db": np.round(filtered_power.astype(float), 4).tolist(),
        "vmin": round(vmin, 4),
        "vmax": round(vmax, 4),
    }


def _build_event_timeline_svg(
    epoch_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    duration_sec: float,
    channel: str,
) -> str:
    width = 1280
    height = 360
    left = 80
    right = 36
    top = 92
    timeline_y = 178
    timeline_h = 42
    plot_w = width - left - right
    duration = max(1.0, float(duration_sec or 1.0))
    event_count = len(event_rows)
    seizure_epochs = sum(1 for row in epoch_rows if int(row.get("Stage_Code") or 0) == 1)
    title = "癫痫样候选事件初筛时间轴"
    subtitle = f"通道 {channel} · 候选事件 {event_count} 个 · 命中 epoch {seizure_epochs} 个"
    ticks = []
    for index in range(6):
      x = left + plot_w * index / 5
      t = duration * index / 5
      ticks.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{timeline_y + 78}" stroke="#d7e3ee" stroke-width="1"/>')
      ticks.append(f'<text x="{x:.1f}" y="{timeline_y + 104}" text-anchor="middle" font-size="12" fill="#607086">{t:.1f}s</text>')
    epoch_rects = []
    for row in epoch_rows:
        try:
            code = int(row.get("Stage_Code") or 0)
            start = float(row.get("start_sec") or 0)
            end = float(row.get("end_sec") or start)
        except (TypeError, ValueError):
            continue
        if end <= start:
            continue
        x = left + (start / duration) * plot_w
        w = max(1.5, ((end - start) / duration) * plot_w)
        color = "#f97316" if code == 1 else "#cbd5e1"
        opacity = "0.72" if code == 1 else "0.35"
        epoch_rects.append(f'<rect x="{x:.2f}" y="{timeline_y}" width="{w:.2f}" height="{timeline_h}" rx="3" fill="{color}" opacity="{opacity}"/>')
    event_rects = []
    for row in event_rows:
        try:
            start = float(row.get("start_sec") or 0)
            end = float(row.get("end_sec") or start)
        except (TypeError, ValueError):
            continue
        if end <= start:
            continue
        x = left + (start / duration) * plot_w
        w = max(3.0, ((end - start) / duration) * plot_w)
        label = html.escape(str(row.get("event_id") or "candidate"))
        event_rects.append(f'<rect x="{x:.2f}" y="{timeline_y - 28}" width="{w:.2f}" height="20" rx="4" fill="#dc2626" opacity="0.78"><title>{label}</title></rect>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="{left}" y="42" font-size="24" font-weight="700" fill="#0f172a">{html.escape(title)}</text>
  <text x="{left}" y="70" font-size="14" fill="#52657a">{html.escape(subtitle)}</text>
  <rect x="{left}" y="{top}" width="{plot_w}" height="178" rx="14" fill="#f8fbff" stroke="#dbe7f1"/>
  {''.join(ticks)}
  <text x="{left}" y="{timeline_y - 12}" font-size="13" font-weight="700" fill="#334155">候选事件</text>
  <text x="{left}" y="{timeline_y + 64}" font-size="13" font-weight="700" fill="#334155">Epoch 预测</text>
  <line x1="{left}" y1="{timeline_y + timeline_h / 2}" x2="{left + plot_w}" y2="{timeline_y + timeline_h / 2}" stroke="#94a3b8" stroke-width="1"/>
  {''.join(epoch_rects)}
  {''.join(event_rects)}
  <rect x="{left}" y="{height - 54}" width="{plot_w}" height="28" rx="8" fill="#fff7ed" stroke="#fed7aa"/>
  <text x="{left + 12}" y="{height - 35}" font-size="12" fill="#9a3412">科研初筛支持：候选事件需要人工复核；本图不用于诊断、治疗或临床分诊。</text>
</svg>
"""


def _build_spectrogram_svg(payload: dict[str, Any]) -> str:
    width = 1280
    height = 520
    left = 84
    right = 28
    top = 86
    bottom = 72
    plot_w = width - left - right
    plot_h = height - top - bottom
    freqs = np.asarray(payload.get("frequencies_hz") or [], dtype=float)
    times = np.asarray(payload.get("times_sec") or [], dtype=float)
    power = np.asarray(payload.get("power_db") or [], dtype=float)
    if power.ndim != 2 or not len(freqs) or not len(times):
        heatmap = f'<text x="{width/2:.0f}" y="{height/2:.0f}" text-anchor="middle" font-size="16" fill="#64748b">时频图数据不足</text>'
    else:
        max_cols = min(180, power.shape[1])
        max_rows = min(80, power.shape[0])
        col_idx = np.unique(np.linspace(0, power.shape[1] - 1, max_cols).astype(int))
        row_idx = np.unique(np.linspace(0, power.shape[0] - 1, max_rows).astype(int))
        sampled = power[np.ix_(row_idx, col_idx)]
        vmin = float(payload.get("vmin", np.nanmin(sampled)))
        vmax = float(payload.get("vmax", np.nanmax(sampled)))
        span = max(1e-9, vmax - vmin)
        cell_w = plot_w / max(1, len(col_idx))
        cell_h = plot_h / max(1, len(row_idx))
        cells = []
        for r, _freq_index in enumerate(row_idx):
            y = top + plot_h - (r + 1) * cell_h
            for c, _time_index in enumerate(col_idx):
                value = float(sampled[r, c])
                color = _spectrogram_svg_color((value - vmin) / span)
                x = left + c * cell_w
                cells.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell_w + 0.4:.2f}" height="{cell_h + 0.4:.2f}" fill="{color}"/>')
        heatmap = "".join(cells)
    title = "癫痫样事件初筛时频证据图"
    subtitle = (
        f"{html.escape(str(payload.get('channel') or 'channel'))} · "
        "PC STFT: 4s window, 90% overlap, 0.5-50 Hz"
    )
    duration = float(payload.get("duration_sec") or (float(times[-1]) if times.size else 0.0) or 0.0)
    freq_max = float(np.nanmax(freqs)) if freqs.size else 50.0
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="{left}" y="40" font-size="24" font-weight="700" fill="#0f172a">{html.escape(title)}</text>
  <text x="{left}" y="68" font-size="14" fill="#52657a">{subtitle}</text>
  <rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="#0f172a" stroke="#dbe7f1"/>
  {heatmap}
  <line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#334155"/>
  <line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#334155"/>
  <text x="{left}" y="{height - 42}" font-size="12" fill="#607086">0s</text>
  <text x="{left + plot_w}" y="{height - 42}" text-anchor="end" font-size="12" fill="#607086">{duration:.1f}s</text>
  <text x="{left - 16}" y="{top + plot_h}" text-anchor="end" font-size="12" fill="#607086">0.5 Hz</text>
  <text x="{left - 16}" y="{top + 8}" text-anchor="end" font-size="12" fill="#607086">{freq_max:.1f} Hz</text>
  <rect x="{left}" y="{height - 30}" width="{plot_w}" height="24" rx="8" fill="#fff7ed" stroke="#fed7aa"/>
  <text x="{left + 12}" y="{height - 13}" font-size="12" fill="#9a3412">科研初筛支持：时频图用于候选事件证据查看；不是正式诊断图或临床报告。</text>
</svg>
"""


def _spectrogram_svg_color(value: float) -> str:
    v = max(0.0, min(1.0, float(value) if math.isfinite(float(value)) else 0.0))
    stops = [
        (0.00, (12, 35, 64)),
        (0.25, (37, 99, 143)),
        (0.50, (102, 171, 170)),
        (0.75, (244, 181, 94)),
        (1.00, (179, 58, 48)),
    ]
    for index in range(1, len(stops)):
        p1, c1 = stops[index]
        p0, c0 = stops[index - 1]
        if v <= p1:
            k = (v - p0) / max(1e-9, p1 - p0)
            rgb = tuple(round(c0[channel] + (c1[channel] - c0[channel]) * k) for channel in range(3))
            return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"
    return "rgb(179,58,48)"


def compute_tkeo(epoch: np.ndarray) -> np.ndarray:
    tkeo = np.empty_like(epoch)
    for i in range(len(epoch)):
        if i == 0 or i == len(epoch) - 1:
            tkeo[i] = epoch[i]
        else:
            tkeo[i] = epoch[i] ** 2 - epoch[i + 1] * epoch[i - 1]
    return tkeo


def _pyeeg_hjorth_mobility(epoch: np.ndarray) -> float:
    x = np.asarray(epoch, dtype=np.float64)
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    if x.size < 2:
        return 0.0
    var_x = np.var(x)
    if not np.isfinite(var_x) or var_x <= 0:
        return 0.0
    dx = np.diff(x)
    var_dx = np.var(dx)
    if not np.isfinite(var_dx) or var_dx < 0:
        return 0.0
    return float(np.sqrt(var_dx / var_x))


def _pyeeg_pfd(epoch: np.ndarray) -> float:
    x = np.asarray(epoch, dtype=np.float64)
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    n = x.size
    if n < 2:
        return 0.0
    diff = np.diff(x)
    n_delta = 0 if diff.size < 2 else int(np.sum(diff[1:] * diff[:-1] < 0))
    denominator = np.log10(n) + np.log10(n / (n + 0.4 * n_delta))
    if not np.isfinite(denominator) or denominator == 0:
        return 0.0
    return float(np.log10(n) / denominator)


def butter_bandpass(lowcut: float, highcut: float, fs: float, order: int = 6):
    nyq = 0.5 * fs
    if lowcut <= 0:
        lowcut = 0.1
    if highcut >= nyq:
        highcut = nyq - 0.1
    if lowcut >= highcut:
        logging.warning("Invalid filter parameters: lowcut=%s, highcut=%s, fs=%s", lowcut, highcut, fs)
        lowcut = max(0.1, highcut - 1.0)
    low = lowcut / nyq
    high = highcut / nyq
    try:
        return scipy.signal.butter(order, [low, high], btype="band")
    except Exception as exc:
        logging.error("Failed to create filter with params: lowcut=%s, highcut=%s, fs=%s: %s", lowcut, highcut, fs, exc)
        return [1.0], [1.0]


def butter_bandpass_filter(data: np.ndarray, lowcut: float, highcut: float, fs: float, order: int = 6) -> np.ndarray:
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    try:
        return scipy.signal.filtfilt(b, a, data)
    except Exception as exc:
        logging.error("Failed to apply filter: %s", exc)
        return data


def _bandpower_for_epochs(epochs: np.ndarray, lowcut: float, highcut: float, fs: float, order: int = 6) -> np.ndarray:
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    try:
        filtered = scipy.signal.filtfilt(b, a, epochs, axis=1)
    except Exception as exc:
        logging.error("Failed to apply vectorized epoch filter: %s", exc)
        return np.mean(epochs**2, axis=1)
    return np.mean(filtered**2, axis=1)


def extract_features_using_epochs(data_segment: np.ndarray, fs: float) -> np.ndarray:
    feature_list = []
    nyq = 0.5 * fs
    epochs = np.asarray(data_segment[:, 0, :], dtype=np.float64)
    if epochs.ndim != 2:
        raise ValueError("Epilepsy ML feature extraction expects an epoch matrix.")
    epoch_count = int(epochs.shape[0])
    p_delta = _bandpower_for_epochs(epochs, 0.1, min(4, nyq - 0.1), fs, order=6)
    p_theta = np.zeros(epoch_count, dtype=np.float64)
    p_alpha = np.zeros(epoch_count, dtype=np.float64)
    p_beta = np.zeros(epoch_count, dtype=np.float64)
    p_gamma = np.zeros(epoch_count, dtype=np.float64)
    if 4 < nyq:
        p_theta = _bandpower_for_epochs(epochs, 4, min(8, nyq - 0.1), fs, order=6)
    if 8 < nyq:
        p_alpha = _bandpower_for_epochs(epochs, 8, min(16, nyq - 0.1), fs, order=6)
    if 16 < nyq:
        p_beta = _bandpower_for_epochs(epochs, 16, min(32, nyq - 0.1), fs, order=6)
    if 32 < nyq:
        gamma_high = min(64, nyq - 0.1)
        if gamma_high > 32:
            p_gamma = _bandpower_for_epochs(epochs, 32, gamma_high, fs, order=6)
    p_total = np.mean(epochs**2, axis=1)
    for i in range(data_segment.shape[0]):
        epoch = epochs[i, :]
        feat: dict[str, float] = {}
        feat["mean"] = np.mean(epoch)
        feat["mobility"] = _pyeeg_hjorth_mobility(epoch)
        feat["TKEO"] = np.mean(compute_tkeo(epoch))

        feat["P_delta"] = p_delta[i]
        feat["P_theta"] = p_theta[i]
        feat["P_alpha"] = p_alpha[i]
        feat["P_beta"] = p_beta[i]
        feat["P_gamma"] = p_gamma[i]
        feat["P_total"] = p_total[i]
        total_power = feat["P_total"]
        if total_power > 0:
            feat["rel_delta"] = feat["P_delta"] / total_power
            feat["rel_theta"] = feat["P_theta"] / total_power
            feat["rel_alpha"] = feat["P_alpha"] / total_power
            feat["rel_beta"] = feat["P_beta"] / total_power
            feat["rel_gamma"] = feat["P_gamma"] / total_power
        else:
            feat["rel_delta"] = 0
            feat["rel_theta"] = 0
            feat["rel_alpha"] = 0
            feat["rel_beta"] = 0
            feat["rel_gamma"] = 0

        feat["pfd"] = _pyeeg_pfd(epoch)
        feat["skew"] = scipy.stats.skew(epoch)
        feat["kurtosis"] = scipy.stats.kurtosis(epoch)
        feat["var"] = np.var(epoch)
        feat["envelope"] = np.mean(np.abs(scipy.signal.hilbert(epoch)))
        feature_list.append(feat)

    X = np.array([[row[column] for column in FEATURE_COLUMNS] for row in feature_list], dtype=np.float64)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return np.clip(X, -1e6, 1e6).astype(np.float32)


def extract_features_using_epochs_chunked(
    data: np.ndarray,
    fs: float,
    *,
    epoch_samples: int,
    n_epochs: int,
    chunk_epochs: int,
    worker_count: int = 1,
) -> np.ndarray:
    """Extract source-compatible features without materializing the full epoch matrix."""
    if epoch_samples <= 0:
        raise ValueError("Epilepsy ML epoch_samples must be > 0")
    if n_epochs <= 0:
        return np.empty((0, len(FEATURE_COLUMNS)), dtype=np.float32)
    chunk_epochs = max(1, int(chunk_epochs))
    chunk_specs: list[tuple[int, int, int, int]] = []
    for start_epoch in range(0, n_epochs, chunk_epochs):
        end_epoch = min(n_epochs, start_epoch + chunk_epochs)
        start_sample = start_epoch * epoch_samples
        end_sample = end_epoch * epoch_samples
        chunk_specs.append((start_epoch, end_epoch, start_sample, end_sample))

    def build_chunk(spec: tuple[int, int, int, int]) -> np.ndarray:
        _start_epoch, end_epoch, start_sample, end_sample = spec
        chunk = np.ascontiguousarray(data[start_sample:end_sample])
        if chunk.size != (end_epoch - _start_epoch) * epoch_samples:
            raise ValueError("Epilepsy ML chunk extraction encountered an incomplete epoch chunk.")
        chunk_epochs_data = chunk.reshape(end_epoch - _start_epoch, 1, epoch_samples)
        return extract_features_using_epochs(chunk_epochs_data, fs)

    worker_count = max(1, int(worker_count))
    if worker_count <= 1 or len(chunk_specs) <= 1:
        chunks = [build_chunk(spec) for spec in chunk_specs]
    else:
        # SciPy/NumPy filter kernels usually release the GIL; threads avoid copying
        # large EEG chunks into child processes on Windows.
        with ThreadPoolExecutor(max_workers=min(worker_count, len(chunk_specs))) as pool:
            chunks = list(pool.map(build_chunk, chunk_specs))
    if not chunks:
        return np.empty((0, len(FEATURE_COLUMNS)), dtype=np.float32)
    return np.vstack(chunks).astype(np.float32, copy=False)


def _feature_matrix_diagnostics(features: np.ndarray) -> dict[str, Any]:
    values = np.asarray(features)
    non_finite_count = int(np.size(values) - np.count_nonzero(np.isfinite(values)))
    clipped_count = int(np.count_nonzero(np.abs(np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)) >= 1e6))
    return {
        "feature_shape": [int(item) for item in values.shape],
        "non_finite_value_count": non_finite_count,
        "near_clip_value_count": clipped_count,
        "clipped_or_non_finite_value_count": int(non_finite_count + clipped_count),
        "max_abs_feature_value": float(np.max(np.abs(np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)))) if values.size else 0.0,
    }


def detect_seizures_source_compatible(
    classifications: np.ndarray,
    data: np.ndarray,
    sfreq: float,
    *,
    epoch_length: float,
    start_time_ts: float | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[int]]:
    if start_time_ts is None:
        start_time_ts = dt.datetime.now().timestamp()
    epoch_count = len(classifications)
    event_mask = [0] * epoch_count
    total_samples = len(data)
    total_duration = total_samples / float(sfreq) if sfreq > 0 else 0.0
    if epoch_count == 0 or total_samples == 0 or sfreq <= 0:
        return [], [], event_mask

    events: list[dict[str, Any]] = []
    event_start_times: list[float] = []
    in_seizure = False
    seizure_start_idx: int | None = None
    min_seizure_epochs = 2

    def add_event(start_idx: int, end_idx: int) -> None:
        epoch_span = end_idx - start_idx + 1
        if epoch_span < min_seizure_epochs:
            return
        start_timestamp = start_idx * epoch_length
        end_timestamp = min((end_idx + 1) * epoch_length, total_duration)
        start_sample = int(start_idx * epoch_length * sfreq)
        end_sample = int(min(total_samples, (end_idx + 1) * epoch_length * sfreq))
        if start_sample < end_sample:
            seizure_data = data[start_sample:end_sample]
            max_amp = round(float(np.max(np.abs(seizure_data))) if len(seizure_data) else 0.0, 2)
            rms_value = round(float(np.sqrt(np.mean(seizure_data**2))) if len(seizure_data) else 0.0, 2)
        else:
            max_amp = 0.0
            rms_value = 0.0
        events.append(
            {
                "event_id": len(events) + 1,
                "start_sec": float(start_timestamp),
                "end_sec": float(end_timestamp),
                "duration_sec": round(float(end_timestamp - start_timestamp), 1),
                "start_epoch": start_idx,
                "end_epoch": end_idx,
                "source_start_epoch_1based": start_idx + 1,
                "source_end_epoch_1based": end_idx + 1,
                "epoch_count": int(epoch_span),
                "rms": rms_value,
                "max_abs_amplitude": max_amp,
            }
        )
        event_start_times.append(start_timestamp)
        for idx in range(start_idx, end_idx + 1):
            event_mask[idx] = 1

    for index, is_seizure in enumerate(classifications):
        if int(is_seizure) == 1:
            if not in_seizure:
                in_seizure = True
                seizure_start_idx = index
        elif in_seizure and seizure_start_idx is not None:
            add_event(seizure_start_idx, index - 1)
            in_seizure = False
            seizure_start_idx = None
    if in_seizure and seizure_start_idx is not None:
        add_event(seizure_start_idx, epoch_count - 1)

    windows = _build_window_rows(event_start_times, total_duration)
    return events, windows, event_mask


def _validate_parameters(parameters: dict | None) -> dict[str, Any]:
    source = parameters or {}
    method = str(source.get("method", "ml_epoch_classifier")).strip().lower()
    if method in {"", "ml", "xgboost", "ml_xgboost"}:
        method = "ml_epoch_classifier"
    if method != "ml_epoch_classifier":
        raise ValueError("Epilepsy ML supports only method='ml_epoch_classifier'.")
    threshold = float(source.get("probability_threshold", 0.5))
    if threshold != 0.5:
        raise ValueError("Epilepsy ML source-compatible mode uses the fixed source threshold probability_threshold=0.5.")
    unit_mode = str(source.get("unit_mode", "source_compatible")).strip().lower()
    if unit_mode not in {"source_compatible", "raw", "mne_volts_to_uv"}:
        raise ValueError("Epilepsy ML unit_mode must be source_compatible, raw, or mne_volts_to_uv.")
    params = dict(source)
    params["workflow_id"] = source.get("workflow_id", "epilepsy_ml_xgboost")
    params["method"] = method
    params["eeg_channel"] = source.get("eeg_channel") or None
    params["epoch_length_sec"] = _positive_float(source.get("epoch_length_sec", 5.0), name="epoch_length_sec")
    params["probability_threshold"] = 0.5
    params["unit_mode"] = unit_mode
    params["bad_channels"] = _string_list(source.get("bad_channels"), name="bad_channels")
    params["feature_chunk_epochs"] = _positive_int(source.get("feature_chunk_epochs", 256), name="feature_chunk_epochs")
    params["feature_worker_count"] = _positive_int(source.get("feature_worker_count", 1), name="feature_worker_count")
    params["spectrogram_preview_duration_sec"] = _positive_float(
        source.get("spectrogram_preview_duration_sec", 600.0),
        name="spectrogram_preview_duration_sec",
    )
    return params


def _validated_model_manifest() -> dict[str, Any]:
    manifest = json.loads(MODEL_MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("feature_columns") != FEATURE_COLUMNS:
        raise ValueError("Epilepsy ML manifest feature columns do not match source contract.")
    for info in manifest.get("models", {}).values():
        _assert_file_hash(RESOURCE_ROOT / info["model_file"], info["model_sha256"], info["model_size_bytes"])
        _assert_file_hash(RESOURCE_ROOT / info["scaler_file"], info["scaler_sha256"], info["scaler_size_bytes"])
    return manifest


def _model_info_for_epoch(epoch_length: float, manifest: dict[str, Any]) -> tuple[dict[str, Any], float]:
    if epoch_length == 3.0:
        return manifest["models"]["3.0"], 3.0
    if epoch_length == 5.0:
        return manifest["models"]["5.0"], 5.0
    return manifest["models"]["5.0"], 5.0


def _load_model_and_scaler(model_info: dict[str, Any]):
    model = joblib.load(RESOURCE_ROOT / model_info["model_file"])
    scaler = joblib.load(RESOURCE_ROOT / model_info["scaler_file"])
    if not hasattr(model, "early_stopping_rounds"):
        setattr(model, "early_stopping_rounds", None)
    if not hasattr(model, "callbacks"):
        setattr(model, "callbacks", [])
    return model, scaler


def _build_processing_plan(
    *,
    n_times: int,
    n_epochs: int,
    epoch_samples: int,
    feature_chunk_epochs: int,
    feature_worker_count: int,
    spectrogram_preview_duration_sec: float,
    sfreq: float,
) -> dict[str, Any]:
    full_epoch_matrix_bytes_float64 = int(n_epochs) * int(epoch_samples) * np.dtype(np.float64).itemsize
    chunk_matrix_bytes_float64 = (
        min(int(n_epochs), max(1, int(feature_chunk_epochs))) * int(epoch_samples) * np.dtype(np.float64).itemsize
    )
    preview_samples = int(min(int(n_times), max(1, round(float(spectrogram_preview_duration_sec) * float(sfreq)))))
    return {
        "execution_strategy": "selected_channel_chunked_features_bounded_spectrogram",
        "selected_channel_samples": int(n_times),
        "epoch_count": int(n_epochs),
        "epoch_samples": int(epoch_samples),
        "feature_chunk_epochs": int(max(1, feature_chunk_epochs)),
        "feature_worker_count": int(max(1, feature_worker_count)),
        "parallel_feature_chunks_enabled": int(max(1, feature_worker_count)) > 1,
        "estimated_full_epoch_matrix_bytes_float64": full_epoch_matrix_bytes_float64,
        "estimated_chunk_epoch_matrix_bytes_float64": chunk_matrix_bytes_float64,
        "avoids_full_epoch_matrix_materialization": True,
        "spectrogram_preview_start_sec": 0.0,
        "spectrogram_preview_duration_sec": float(preview_samples / sfreq) if sfreq else 0.0,
        "spectrogram_preview_samples": preview_samples,
        "spectrogram_is_bounded_preview": preview_samples < int(n_times),
    }


def _assert_file_hash(path: Path, expected_sha256: str, expected_size: int) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Epilepsy ML asset missing: {path}")
    if path.stat().st_size != int(expected_size):
        raise ValueError(f"Epilepsy ML asset size mismatch: {path.name}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest().lower() != expected_sha256.lower():
        raise ValueError(f"Epilepsy ML asset hash mismatch: {path.name}")


def _select_eeg_channel(raw, requested: str | None) -> tuple[str, str | None]:
    bads = set(raw.info.get("bads", []))
    eeg_channels = [name for name, kind in zip(raw.ch_names, raw.get_channel_types()) if kind == "eeg" and name not in bads]
    if requested:
        if requested not in raw.ch_names:
            raise ValueError(f"Requested EEG channel not found: {requested}")
        if requested in bads:
            raise ValueError(f"Requested EEG channel is marked bad: {requested}")
        if raw.get_channel_types(picks=[requested])[0] != "eeg":
            raise ValueError(f"Requested channel is not EEG: {requested}")
        return requested, None
    if "EEG3" in eeg_channels:
        return "EEG3", None
    if not eeg_channels:
        raise ValueError("Epilepsy ML requires at least one usable EEG channel")
    return eeg_channels[0], f"Source default EEG3 was not present; selected {eeg_channels[0]}."


def _selected_channel_data(raw, input_path: str | Path, channel: str, unit_mode: str) -> tuple[np.ndarray, str]:
    data = raw.get_data(picks=[channel])[0].astype(np.float64, copy=False)
    suffix = Path(input_path).suffix.lower()
    if unit_mode == "mne_volts_to_uv" or (unit_mode == "source_compatible" and suffix in {".edf", ".bdf"}):
        return data * 1e6, "Applied source-compatible volts-to-microvolts scaling."
    return data, "Used raw MNE channel data without extra scaling."


def _selected_channel_scale_warning(data: np.ndarray, channel: str, unit_mode: str) -> dict[str, Any] | None:
    if data.size == 0:
        return None
    finite = np.asarray(data[np.isfinite(data)], dtype=np.float64)
    if finite.size == 0:
        return {
            "name": "selected_channel_non_finite",
            "detail": f"Selected channel {channel} has no finite samples after unit handling; review source data before interpretation.",
        }
    p99 = float(np.percentile(np.abs(finite), 99))
    max_abs = float(np.max(np.abs(finite)))
    if p99 > 5000 or max_abs > 50000:
        return {
            "name": "selected_channel_scale_review_recommended",
            "detail": (
                f"Selected channel {channel} has high amplitude after unit_mode={unit_mode} "
                f"(p99_abs={p99:.3g}, max_abs={max_abs:.3g}). Review EDF physical units/source scaling before customer-facing interpretation."
            ),
            "p99_abs": p99,
            "max_abs": max_abs,
            "unit_mode": unit_mode,
        }
    return None


def _measurement_timestamp(raw) -> float:
    meas_date = raw.info.get("meas_date", None)
    if meas_date is None:
        return dt.datetime.now().timestamp()
    if isinstance(meas_date, tuple):
        return float(meas_date[0] + meas_date[1] / 1e6)
    return float(meas_date.timestamp())


def _build_epoch_rows(
    predictions: np.ndarray,
    probabilities: np.ndarray,
    event_mask: list[int],
    epoch_length_sec: float,
    duration_sec: float,
) -> list[dict[str, Any]]:
    rows = []
    for index, stage_code in enumerate(predictions):
        start_sec = float(index * epoch_length_sec)
        end_sec = float(min((index + 1) * epoch_length_sec, duration_sec))
        probability = float(probabilities[index])
        rows.append(
            {
                "epoch_index": index,
                "Epoch No.": index,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration_sec": float(max(0.0, end_sec - start_sec)),
                "Stage_Code": int(stage_code),
                "Stage": "Seizure" if int(stage_code) == 1 else "Normal",
                "probability": probability,
                "above_threshold": bool(int(stage_code) == 1),
                "is_event_epoch": bool(event_mask[index]),
                "mean_rms": probability,
                "threshold": 0.5,
            }
        )
    return rows


def _build_window_rows(event_start_times: list[float], total_duration: float) -> list[dict[str, Any]]:
    if total_duration <= 0:
        return []
    window_count = int(math.ceil(total_duration / 1800.0))
    rows = []
    event_idx = 0
    for window_index in range(window_count):
        window_start = 1800.0 * window_index
        window_end = 1800.0 * (window_index + 1)
        while event_idx < len(event_start_times) and event_start_times[event_idx] < window_start:
            event_idx += 1
        scan_idx = event_idx
        event_count = 0
        while scan_idx < len(event_start_times) and window_start <= event_start_times[scan_idx] < window_end:
            event_count += 1
            scan_idx += 1
        event_idx = scan_idx
        if window_index < window_count - 1:
            duration = 1800.0
        else:
            duration = total_duration - 1800.0 * (window_count - 1)
            if duration <= 0:
                duration = 1800.0
        rows.append(
            {
                "window_index": window_index,
                "start_sec": window_start,
                "end_sec": min(total_duration, window_end),
                "duration_sec": duration,
                "event_count": event_count,
                "seizure_frequency_events_per_hour": round(float(event_count / (duration / 3600.0)), 4) if duration > 0 else 0.0,
            }
        )
    return rows


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_array_csv(path: Path, fieldnames: list[str], values: np.ndarray) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["epoch_index", *fieldnames])
        for index, row in enumerate(values):
            writer.writerow([index, *[float(value) for value in row]])


def _table_dictionary() -> dict[str, Any]:
    return {
        "tables/epilepsy_ml_epoch_predictions.csv": {
            "description": "Epoch-level source-compatible ML probabilities and Stage_Code.",
            "primary_key": ["epoch_index"],
        },
        "tables/epilepsy_ml_events.csv": {
            "description": "Candidate ML events after source-compatible two-consecutive-epoch filtering.",
            "primary_key": ["event_id"],
        },
        "tables/epilepsy_ml_features.csv": {
            "description": "Original 19 source feature columns before scaler.transform.",
            "primary_key": ["epoch_index"],
        },
        "tables/epilepsy_ml_features_scaled.csv": {
            "description": "Original 19 source feature columns after scaler.transform.",
            "primary_key": ["epoch_index"],
        },
    }


def _source_metadata(
    input_path: str | Path,
    raw,
    channel: str,
    params: dict[str, Any],
    selected_model_epoch: float,
    unit_note: str,
) -> dict[str, Any]:
    path = Path(input_path)
    return {
        "input_path": str(path),
        "filename": path.name,
        "selected_channel": channel,
        "sfreq": float(raw.info["sfreq"]),
        "n_times": int(raw.n_times),
        "duration_sec": float(raw.n_times / raw.info["sfreq"]),
        "all_channels": list(raw.ch_names),
        "bad_channels": list(params["bad_channels"]),
        "selected_model_epoch_length_sec": selected_model_epoch,
        "unit_mode": params["unit_mode"],
        "unit_note": unit_note,
    }


def _positive_float(value: Any, *, name: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise ValueError(f"Epilepsy ML {name} must be > 0")
    return parsed


def _positive_int(value: Any, *, name: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"Epilepsy ML {name} must be > 0")
    return parsed


def _string_list(value: Any, *, name: str) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Epilepsy ML {name} must be a list of strings")
    return value
