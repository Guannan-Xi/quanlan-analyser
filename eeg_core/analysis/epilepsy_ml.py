from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import logging
import math
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
}


def run_epilepsy_ml(input_path: str | Path, output_dir: str | Path, parameters: dict | None = None) -> dict[str, Path]:
    output_path = Path(output_dir)
    tables = output_path / "tables"
    reproducibility = output_path / "reproducibility"
    for directory in (tables, reproducibility):
        directory.mkdir(parents=True, exist_ok=True)

    raw = read_raw(input_path, preload=True)
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

    trimmed = data[: n_epochs * epoch_samples]
    data_epochs = trimmed.reshape(n_epochs, 1, epoch_samples)
    features = extract_features_using_epochs(data_epochs, sfreq)
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
            {"name": "read_raw", "description": "Read EEG data with preload=True."},
            {"name": "select_eeg_channel", "description": "Use requested channel, source default EEG3, or first usable EEG fallback."},
            {"name": "source_unit_mode", "description": "Apply source-compatible EDF/BDF volts-to-microvolts handling when configured."},
            {"name": "asset_hash_validation", "description": "Validate model and scaler SHA256 before loading."},
            {"name": "feature_extraction", "description": "Extract the original 19 ML features from complete epochs only."},
            {"name": "xgboost_probability", "description": "Run scaler.transform and model.predict_proba(features_scaled)[:, 1]."},
            {"name": "source_event_detection", "description": "Aggregate at least two consecutive seizure epochs into candidate events."},
            {"name": "write_outputs", "description": "Write epoch, event, feature, manifest, summary, sidecar, and contract files."},
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
            "scope=research_screening_support_only_no_diagnosis_treatment_or_clinical_decision",
        ],
    )
    return {**outputs, **contract_paths}


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


def extract_features_using_epochs(data_segment: np.ndarray, fs: float) -> np.ndarray:
    feature_list = []
    nyq = 0.5 * fs
    for i in range(data_segment.shape[0]):
        epoch = data_segment[i, 0, :]
        feat: dict[str, float] = {}
        feat["mean"] = np.mean(epoch)
        feat["mobility"] = _pyeeg_hjorth_mobility(epoch)
        feat["TKEO"] = np.mean(compute_tkeo(epoch))

        delta = butter_bandpass_filter(epoch, 0.1, min(4, nyq - 0.1), fs, order=6)
        feat["P_delta"] = np.mean(delta**2)
        if 4 < nyq:
            theta = butter_bandpass_filter(epoch, 4, min(8, nyq - 0.1), fs, order=6)
            feat["P_theta"] = np.mean(theta**2)
        else:
            feat["P_theta"] = 0
        if 8 < nyq:
            alpha = butter_bandpass_filter(epoch, 8, min(16, nyq - 0.1), fs, order=6)
            feat["P_alpha"] = np.mean(alpha**2)
        else:
            feat["P_alpha"] = 0
        if 16 < nyq:
            beta = butter_bandpass_filter(epoch, 16, min(32, nyq - 0.1), fs, order=6)
            feat["P_beta"] = np.mean(beta**2)
        else:
            feat["P_beta"] = 0
        if 32 < nyq:
            gamma_high = min(64, nyq - 0.1)
            if gamma_high > 32:
                gamma = butter_bandpass_filter(epoch, 32, gamma_high, fs, order=6)
                feat["P_gamma"] = np.mean(gamma**2)
            else:
                feat["P_gamma"] = 0
        else:
            feat["P_gamma"] = 0

        feat["P_total"] = np.mean(epoch**2)
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
    data = raw.get_data(picks=[channel])[0].astype(float, copy=False)
    suffix = Path(input_path).suffix.lower()
    if unit_mode == "mne_volts_to_uv" or (unit_mode == "source_compatible" and suffix in {".edf", ".bdf"}):
        return data * 1e6, "Applied source-compatible volts-to-microvolts scaling."
    return data, "Used raw MNE channel data without extra scaling."


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


def _string_list(value: Any, *, name: str) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Epilepsy ML {name} must be a list of strings")
    return value
