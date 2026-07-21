import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from eeg_core.io.readers import read_raw
from eeg_core.report.reproducibility import (
    write_analysis_sidecars,
    write_output_contract,
    write_reproducibility_files,
)


EPILEPSY_PARAMETER_SCHEMA = {
    "workflow_id": {"type": "string", "default": "epilepsy_std_threshold"},
    "method": {"type": "string", "default": "std_threshold", "enum": ["std_threshold"]},
    "eeg_channel": {"type": ["string", "null"], "default": None},
    "epoch_length_sec": {"type": "number", "default": 5.0, "minimum": 0.001},
    "std_factor": {"type": "number", "default": 2.0, "minimum": 0.0},
    "rms_window_samples": {"type": "integer", "default": 15, "minimum": 1},
    "merge_gap_epoch_num": {"type": "integer", "default": 1, "minimum": 0},
    "min_event_epochs": {"type": "integer", "default": 2, "minimum": 1},
    "event_window_sec": {"type": "number", "default": 1800.0, "minimum": 1.0},
    "bad_channels": {"type": "array", "items": "string", "default": []},
}


def run_epilepsy(input_path: str | Path, output_dir: str | Path, parameters: dict | None = None) -> dict[str, Path]:
    output_path = Path(output_dir)
    tables = output_path / "tables"
    reproducibility = output_path / "reproducibility"
    for directory in (tables, reproducibility):
        directory.mkdir(parents=True, exist_ok=True)

    raw = read_raw(input_path, preload=True)
    params = _validate_parameters(parameters)
    missing_bad_channels = [channel for channel in params["bad_channels"] if channel not in raw.ch_names]
    if missing_bad_channels:
        raise ValueError(f"Epilepsy bad channels not found: {', '.join(missing_bad_channels)}")
    raw.info["bads"] = sorted(set(raw.info.get("bads", [])) | set(params["bad_channels"]))

    channel = _select_eeg_channel(raw, params["eeg_channel"])
    sfreq = float(raw.info["sfreq"])
    data = raw.get_data(picks=[channel])[0].astype(float, copy=False)
    n_times = int(data.size)
    duration_sec = float(n_times / sfreq) if sfreq > 0 else 0.0

    sliding_rms = _compute_sliding_rms(data, params["rms_window_samples"])
    threshold = float(np.mean(sliding_rms) + params["std_factor"] * np.std(sliding_rms))
    exceed_mask = sliding_rms > threshold

    epoch_samples = max(1, int(round(params["epoch_length_sec"] * sfreq)))
    epoch_rows = _build_epoch_rows(data, sliding_rms, exceed_mask, epoch_samples, sfreq, threshold)
    merged_ranges = _merge_event_epochs(
        [bool(row["above_threshold"]) for row in epoch_rows],
        merge_gap_epoch_num=params["merge_gap_epoch_num"],
        min_event_epochs=params["min_event_epochs"],
    )
    event_rows = _build_event_rows(data, sliding_rms, epoch_samples, sfreq, merged_ranges)
    event_epoch_indices = {
        index
        for start_epoch, end_epoch in merged_ranges
        for index in range(start_epoch, end_epoch + 1)
    }
    for row in epoch_rows:
        row["is_event_epoch"] = bool(row["epoch_index"] in event_epoch_indices)
    window_rows = _build_window_rows(event_rows, epoch_rows, duration_sec, params["event_window_sec"])

    epoch_scores_path = tables / "epilepsy_epoch_scores.csv"
    _write_csv(
        epoch_scores_path,
        [
            "epoch_index",
            "start_sec",
            "end_sec",
            "duration_sec",
            "above_threshold",
            "is_event_epoch",
            "above_threshold_sample_count",
            "above_threshold_fraction",
            "mean_rms",
            "max_rms",
            "threshold",
            "max_abs_amplitude",
        ],
        epoch_rows,
    )
    events_path = tables / "epilepsy_events.csv"
    _write_csv(
        events_path,
        [
            "event_id",
            "start_sec",
            "end_sec",
            "duration_sec",
            "start_epoch",
            "end_epoch",
            "epoch_count",
            "rms",
            "max_abs_amplitude",
        ],
        event_rows,
    )
    window_stats_path = tables / "epilepsy_window_stats_30min.csv"
    _write_csv(
        window_stats_path,
        [
            "window_index",
            "start_sec",
            "end_sec",
            "duration_sec",
            "event_count",
            "event_duration_sec",
            "event_epoch_count",
            "max_event_rms",
            "max_epoch_rms",
            "max_abs_amplitude",
        ],
        window_rows,
    )

    summary = {
        "status": "computed",
        "module": "epilepsy",
        "method": "std_threshold",
        "scope": "research_screening_support_only",
        "channel": channel,
        "sfreq": sfreq,
        "duration_sec": duration_sec,
        "samples": n_times,
        "epoch_count": len(epoch_rows),
        "event_count": len(event_rows),
        "threshold": threshold,
        "rms_mean": float(np.mean(sliding_rms)),
        "rms_std": float(np.std(sliding_rms)),
        "max_rms": float(np.max(sliding_rms)) if sliding_rms.size else None,
        "max_abs_amplitude": float(np.max(np.abs(data))) if data.size else None,
        "parameters": params,
        "warnings": [
            {
                "name": "non_medical_scope",
                "detail": "Research screening/support only; not for diagnosis, treatment, or clinical decision-making.",
            }
        ],
    }
    summary_path = reproducibility / "epilepsy_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    parameters_path = reproducibility / "parameters.json"
    parameters_path.write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")
    method_path = reproducibility / "method_description.txt"
    method_path.write_text(
        "Epilepsy STD threshold screening computes sliding RMS as sqrt(convolve(data**2, "
        "ones(window)/window, mode='same')). The threshold is mean(RMS) + std_factor * std(RMS). "
        "Samples above threshold are mapped to fixed-length epochs, adjacent candidate epochs are "
        "merged across gaps up to merge_gap_epoch_num, and events shorter than min_event_epochs are "
        "discarded. This output is research screening/support only and must not be used for diagnosis, "
        "treatment, or clinical decision-making.\n",
        encoding="utf-8",
    )

    reproducibility_paths = write_reproducibility_files(
        output_path,
        module_name="epilepsy",
        input_path=input_path,
        parameters=params,
        workflow_steps=[
            {"name": "read_raw", "description": "Read EEG data with preload=True."},
            {"name": "select_eeg_channel", "description": "Select the requested EEG channel, or the first usable EEG channel."},
            {"name": "sliding_rms", "description": "Compute RMS with numpy convolution over the selected channel."},
            {"name": "std_threshold", "description": "Apply mean plus std_factor times standard deviation threshold."},
            {"name": "epoch_mapping", "description": "Map above-threshold samples to epoch-level scores."},
            {"name": "event_merge", "description": "Merge adjacent candidate epochs and filter short events."},
            {"name": "write_outputs", "description": "Write tables, summary, sidecars, manifest, result, and log."},
        ],
    )
    sidecar_paths = write_analysis_sidecars(
        output_path,
        module_name="epilepsy",
        parameter_schema=EPILEPSY_PARAMETER_SCHEMA,
        effective_call={
            "engine": "numpy",
            "call": "sqrt(convolve(data**2, ones/window, mode='same'))",
            "kwargs": {
                "method": params["method"],
                "std_factor": params["std_factor"],
                "rms_window_samples": params["rms_window_samples"],
                "epoch_length_sec": params["epoch_length_sec"],
                "merge_gap_epoch_num": params["merge_gap_epoch_num"],
                "min_event_epochs": params["min_event_epochs"],
            },
            "input_shape": {"channel": channel, "n_times": n_times, "sfreq": sfreq},
            "output_shape": {"epochs": len(epoch_rows), "events": len(event_rows), "windows": len(window_rows)},
        },
        threshold_validation={
            "status": "passed",
            "checks": [
                {"field": "method", "rule": "== std_threshold", "value": params["method"], "status": "passed"},
                {"field": "eeg_channel", "rule": "usable EEG channel", "value": channel, "status": "passed"},
                {"field": "epoch_length_sec", "rule": "> 0", "value": params["epoch_length_sec"], "status": "passed"},
                {"field": "rms_window_samples", "rule": ">= 1", "value": params["rms_window_samples"], "status": "passed"},
                {"field": "threshold", "rule": "mean_rms + std_factor * std_rms", "value": threshold, "status": "passed"},
            ],
        },
        table_dictionary=_table_dictionary(),
        scope_contract={
            "analysis_scope": "single_record_epilepsy_std_threshold_research_screening",
            "stable_status": "minimal_std_threshold_v01",
            "allowed_claims": [
                "Flag high-amplitude RMS threshold epochs in one EEG channel.",
                "Summarize threshold-derived candidate events for research screening/support.",
            ],
            "disallowed_claims": [
                "diagnosis",
                "treatment_recommendation",
                "clinical_decision",
                "seizure_confirmation",
                "medical_triage",
                "machine_learning_classification",
            ],
            "required_boundary": "Research screening/support only; no diagnosis, treatment, or clinical decision-making.",
        },
        source_metadata=_source_metadata(input_path, raw, channel, params),
    )

    outputs = {
        "epilepsy_epoch_scores": epoch_scores_path,
        "epilepsy_events": events_path,
        "epilepsy_window_stats_30min": window_stats_path,
        "epilepsy_summary": summary_path,
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
        job_type="epilepsy_std_threshold",
        module_name="epilepsy",
        input_path=input_path,
        parameters=params,
        summary=summary,
        outputs=outputs,
        log_lines=[
            f"channel={channel}",
            f"threshold={threshold}",
            f"epoch_count={len(epoch_rows)}",
            f"event_count={len(event_rows)}",
            "scope=research_screening_support_only_no_diagnosis_treatment_or_clinical_decision",
        ],
    )
    return {**outputs, **contract_paths}


def _validate_parameters(parameters: dict | None) -> dict[str, Any]:
    source = parameters or {}
    params = dict(source)
    method = str(source.get("method", "std_threshold")).strip().lower()
    if method in {"", "std"}:
        method = "std_threshold"
    if method != "std_threshold":
        raise ValueError("Epilepsy analysis currently supports only method='std_threshold'; ML methods are not implemented.")
    params["workflow_id"] = source.get("workflow_id", "epilepsy_std_threshold")
    params["method"] = method
    params["eeg_channel"] = source.get("eeg_channel")
    params["epoch_length_sec"] = _positive_float(source.get("epoch_length_sec", 5.0), name="epoch_length_sec")
    params["std_factor"] = _non_negative_float(source.get("std_factor", 2.0), name="std_factor")
    params["rms_window_samples"] = _positive_int(source.get("rms_window_samples", 15), name="rms_window_samples")
    params["merge_gap_epoch_num"] = _non_negative_int(source.get("merge_gap_epoch_num", 1), name="merge_gap_epoch_num")
    params["min_event_epochs"] = _positive_int(source.get("min_event_epochs", 2), name="min_event_epochs")
    params["event_window_sec"] = _positive_float(source.get("event_window_sec", 1800.0), name="event_window_sec")
    params["bad_channels"] = _string_list(source.get("bad_channels"), name="bad_channels")
    return params


def _select_eeg_channel(raw, requested: str | None) -> str:
    eeg_channels = [name for name, kind in zip(raw.ch_names, raw.get_channel_types()) if kind == "eeg" and name not in raw.info.get("bads", [])]
    if requested:
        if requested not in raw.ch_names:
            raise ValueError(f"Requested EEG channel not found: {requested}")
        if requested in raw.info.get("bads", []):
            raise ValueError(f"Requested EEG channel is marked bad: {requested}")
        channel_type = raw.get_channel_types(picks=[requested])[0]
        if channel_type != "eeg":
            raise ValueError(f"Requested channel is not EEG: {requested}")
        return requested
    if not eeg_channels:
        raise ValueError("Epilepsy STD threshold requires at least one usable EEG channel")
    return eeg_channels[0]


def _compute_sliding_rms(data: np.ndarray, window_samples: int) -> np.ndarray:
    window = np.ones(int(window_samples), dtype=float) / float(window_samples)
    return np.sqrt(np.convolve(np.square(data), window, mode="same"))


def _build_epoch_rows(
    data: np.ndarray,
    sliding_rms: np.ndarray,
    exceed_mask: np.ndarray,
    epoch_samples: int,
    sfreq: float,
    threshold: float,
) -> list[dict[str, Any]]:
    rows = []
    epoch_count = int(math.ceil(len(data) / epoch_samples)) if len(data) else 0
    for epoch_index in range(epoch_count):
        start_sample = epoch_index * epoch_samples
        end_sample = min(len(data), start_sample + epoch_samples)
        epoch_data = data[start_sample:end_sample]
        epoch_rms = sliding_rms[start_sample:end_sample]
        epoch_exceed = exceed_mask[start_sample:end_sample]
        duration = float((end_sample - start_sample) / sfreq)
        exceed_count = int(np.count_nonzero(epoch_exceed))
        rows.append(
            {
                "epoch_index": epoch_index,
                "start_sec": float(start_sample / sfreq),
                "end_sec": float(end_sample / sfreq),
                "duration_sec": duration,
                "above_threshold": bool(exceed_count > 0),
                "above_threshold_sample_count": exceed_count,
                "above_threshold_fraction": float(exceed_count / len(epoch_exceed)) if len(epoch_exceed) else 0.0,
                "mean_rms": float(np.mean(epoch_rms)) if len(epoch_rms) else None,
                "max_rms": float(np.max(epoch_rms)) if len(epoch_rms) else None,
                "threshold": threshold,
                "max_abs_amplitude": float(np.max(np.abs(epoch_data))) if len(epoch_data) else None,
            }
        )
    return rows


def _merge_event_epochs(mask: list[bool], *, merge_gap_epoch_num: int, min_event_epochs: int) -> list[tuple[int, int]]:
    ranges = []
    start = None
    last_true = None
    gap_count = 0
    for index, value in enumerate(mask):
        if value:
            if start is None:
                start = index
            last_true = index
            gap_count = 0
        elif start is not None:
            gap_count += 1
            if gap_count > merge_gap_epoch_num:
                ranges.append((start, last_true))
                start = None
                last_true = None
                gap_count = 0
    if start is not None and last_true is not None:
        ranges.append((start, last_true))
    return [(start_idx, end_idx) for start_idx, end_idx in ranges if end_idx - start_idx + 1 >= min_event_epochs]


def _build_event_rows(
    data: np.ndarray,
    sliding_rms: np.ndarray,
    epoch_samples: int,
    sfreq: float,
    ranges: list[tuple[int, int]],
) -> list[dict[str, Any]]:
    rows = []
    for event_index, (start_epoch, end_epoch) in enumerate(ranges, start=1):
        start_sample = start_epoch * epoch_samples
        end_sample = min(len(data), (end_epoch + 1) * epoch_samples)
        event_data = data[start_sample:end_sample]
        event_rms = sliding_rms[start_sample:end_sample]
        rows.append(
            {
                "event_id": event_index,
                "start_sec": float(start_sample / sfreq),
                "end_sec": float(end_sample / sfreq),
                "duration_sec": float((end_sample - start_sample) / sfreq),
                "start_epoch": start_epoch,
                "end_epoch": end_epoch,
                "epoch_count": int(end_epoch - start_epoch + 1),
                "rms": float(np.mean(event_rms)) if len(event_rms) else None,
                "max_abs_amplitude": float(np.max(np.abs(event_data))) if len(event_data) else None,
            }
        )
    return rows


def _build_window_rows(
    event_rows: list[dict[str, Any]],
    epoch_rows: list[dict[str, Any]],
    duration_sec: float,
    window_sec: float,
) -> list[dict[str, Any]]:
    window_count = max(1, int(math.ceil(duration_sec / window_sec))) if duration_sec > 0 else 1
    rows = []
    for window_index in range(window_count):
        start_sec = float(window_index * window_sec)
        end_sec = float(min(duration_sec, start_sec + window_sec))
        events = [row for row in event_rows if row["start_sec"] < end_sec and row["end_sec"] > start_sec]
        epochs = [row for row in epoch_rows if row["start_sec"] < end_sec and row["end_sec"] > start_sec]
        rows.append(
            {
                "window_index": window_index,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration_sec": max(0.0, end_sec - start_sec),
                "event_count": len(events),
                "event_duration_sec": float(sum(row["duration_sec"] for row in events)),
                "event_epoch_count": int(sum(row["epoch_count"] for row in events)),
                "max_event_rms": _max_or_none(row["rms"] for row in events),
                "max_epoch_rms": _max_or_none(row["max_rms"] for row in epochs),
                "max_abs_amplitude": _max_or_none(row["max_abs_amplitude"] for row in epochs),
            }
        )
    return rows


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _table_dictionary() -> dict[str, Any]:
    return {
        "tables/epilepsy_epoch_scores.csv": {
            "description": "Epoch-level STD threshold scores for one selected EEG channel.",
            "primary_key": ["epoch_index"],
        },
        "tables/epilepsy_events.csv": {
            "description": "Merged candidate threshold events after minimum duration filtering.",
            "primary_key": ["event_id"],
        },
        "tables/epilepsy_window_stats_30min.csv": {
            "description": "Window-level summary using event_window_sec, defaulting to 30 minutes.",
            "primary_key": ["window_index"],
        },
    }


def _source_metadata(input_path: str | Path, raw, channel: str, params: dict[str, Any]) -> dict[str, Any]:
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
    }


def _positive_float(value: Any, *, name: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise ValueError(f"Epilepsy {name} must be > 0")
    return parsed


def _non_negative_float(value: Any, *, name: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise ValueError(f"Epilepsy {name} must be >= 0")
    return parsed


def _positive_int(value: Any, *, name: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"Epilepsy {name} must be > 0")
    return parsed


def _non_negative_int(value: Any, *, name: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise ValueError(f"Epilepsy {name} must be >= 0")
    return parsed


def _string_list(value: Any, *, name: str) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Epilepsy {name} must be a list of strings")
    return value


def _max_or_none(values) -> float | None:
    filtered = [value for value in values if value is not None]
    return float(max(filtered)) if filtered else None
