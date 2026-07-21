from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import mne
import numpy as np

from eeg_core.io.readers import read_raw
from eeg_core.report.reproducibility import stable_json_hash, write_analysis_sidecars, write_manifest, write_output_contract, write_reproducibility_files


TFR_PARAMETER_SCHEMA = {
    "workflow_id": {"type": "string", "default": "tfr_ersp_itc"},
    "event_id": {"type": "string", "default": ""},
    "tmin": {"type": "number", "default": -0.2},
    "tmax": {"type": "number", "default": 0.8},
    "baseline": {"type": "array", "items": "number", "default": [-0.2, 0.0]},
    "freqs": {"type": "array", "items": "number", "default": [8.0, 13.0, 30.0]},
    "n_cycles": {"type": "number", "default": 3.0},
    "decim": {"type": "integer", "default": 2, "minimum": 1},
    "return_itc": {"type": "boolean", "default": True},
    "method": {"type": "string", "default": "morlet"},
    "average": {"type": "boolean", "default": True},
    "picks": {"type": "array", "items": "string", "default": []},
}

TFR_BOUNDARY = (
    "Single-record descriptive TFR beta output only; not for clinical diagnosis, treatment decisions, "
    "causality, statistical inference, group comparison, or source localization."
)


def describe_tfr_scope() -> dict[str, Any]:
    return {
        "status": "beta_epoch_based_runner",
        "workflow_id": "tfr_ersp_itc",
        "boundary": TFR_BOUNDARY,
    }


def run_tfr(input_path: str | Path, output_dir: str | Path, parameters: dict | None = None) -> dict[str, Path]:
    output_path = Path(output_dir)
    figures = output_path / "figures"
    tables = output_path / "tables"
    reproducibility = output_path / "reproducibility"
    for directory in (figures, tables, reproducibility):
        directory.mkdir(parents=True, exist_ok=True)

    raw = read_raw(input_path, preload=True)
    params = validate_tfr_parameters(parameters, raw=raw)

    # Crop to analysis window if provided (allows TFR to follow the waveform preview window)
    analysis_window = params.get("analysis_window")
    if analysis_window and isinstance(analysis_window, dict):
        aw_start = float(analysis_window.get("start_sec", 0))
        aw_duration = float(analysis_window.get("duration_sec", 0))
        file_duration = raw.n_times / float(raw.info["sfreq"])
        if aw_start >= 0 and aw_duration > 0 and aw_start < file_duration:
            aw_stop = min(aw_start + aw_duration, file_duration)
            raw = raw.copy().crop(tmin=aw_start, tmax=aw_stop, include_tmax=False)
            params = {**params, "analysis_window": {**analysis_window, "actual_crop_start_sec": round(aw_start, 2), "actual_crop_end_sec": round(aw_stop, 2)}}

    event_id = _resolve_event_id(raw, params["event_id"])
    events, event_map = mne.events_from_annotations(raw, event_id=event_id, verbose=False)
    if events.size == 0:
        raise ValueError("TFR requires at least one event or annotation to epoch")
    picks = params["picks"] or mne.pick_types(raw.info, eeg=True, meg=False, eog=False, ecg=False, stim=False, exclude="bads")
    if len(picks) == 0:
        raise ValueError("TFR requires at least one usable EEG channel")
    epochs = mne.Epochs(
        raw,
        events,
        event_id=event_map,
        tmin=params["tmin"],
        tmax=params["tmax"],
        baseline=tuple(params["baseline"]) if params["baseline"] else None,
        picks=picks,
        preload=True,
        reject_by_annotation=True,
        verbose=False,
    )
    if len(epochs) == 0:
        raise ValueError("TFR epoching produced no usable epochs")
    freqs = np.asarray(params["freqs"], dtype=float)
    n_cycles = params["n_cycles"]
    power, itc = mne.time_frequency.tfr_morlet(
        epochs,
        freqs=freqs,
        n_cycles=n_cycles,
        return_itc=bool(params["return_itc"]),
        average=True,
        decim=int(params["decim"]),
        picks=list(range(len(picks))),
        verbose=False,
    )

    power_path = tables / "tfr_power_long.csv"
    power_rows = _power_rows(power, freqs, epochs.ch_names)
    _write_csv(power_path, power_rows, ["channel", "frequency_hz", "time_sec", "power_db", "event_count", "baseline", "unit"])
    itc_path = tables / "tfr_itc_long.csv"
    itc_rows = _itc_rows(itc, freqs, epochs.ch_names) if itc is not None else []
    _write_csv(itc_path, itc_rows, ["channel", "frequency_hz", "time_sec", "itc", "event_count", "unit"]) if itc_rows else None
    summary_path = tables / "tfr_summary.csv"
    summary_rows = _summary_rows(power_rows, itc_rows, epochs.ch_names)
    _write_csv(summary_path, summary_rows, ["channel", "peak_frequency_hz", "peak_time_sec", "peak_power_db", "itc_available", "warnings"])

    power_svg = figures / "tfr_power.svg"
    itc_svg = figures / "tfr_itc.svg"
    _write_heatmap_svg(power_svg, power.data, power.times, freqs.tolist(), "TFR power (dB)")
    if itc is not None:
        _write_heatmap_svg(itc_svg, itc.data, itc.times, freqs.tolist(), "TFR ITC")

    params_path = reproducibility / "parameters.json"
    params_hash = stable_json_hash(params)
    recorded_params = {**params, "parameters_hash": params_hash}
    params_path.write_text(json.dumps(recorded_params, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    frequency_grid_path = reproducibility / "frequency_grid.json"
    frequency_grid_path.write_text(json.dumps({"freqs_hz": freqs.tolist(), "n_cycles": n_cycles, "decim": int(params["decim"])}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    method_path = reproducibility / "method_description.txt"
    method_path.write_text(
        "TFR beta computes Morlet time-frequency power and optional ITC from event-locked epochs. "
        "Outputs describe one recording in sensor/channel space only. This module does not output p-values, "
        "group statistics, causality, diagnosis, or source localization.\n",
        encoding="utf-8",
    )
    summary = {
        "status": "computed",
        "module_id": "tfr_ersp_itc",
        "workflow_id": "tfr_ersp_itc",
        "lifecycle_state": "beta",
        "method": params["method"],
        "channels": list(epochs.ch_names),
        "sfreq": float(raw.info["sfreq"]),
        "epoch_count": len(epochs),
        "freq_count": len(freqs),
        "warnings": [
            "Single-record descriptive TFR beta output only.",
            "No p-value, significance, group comparison, diagnosis, causality, or source-localization conclusion is produced.",
        ],
        "boundary": TFR_BOUNDARY,
    }
    tfr_summary_path = reproducibility / "tfr_summary.json"
    tfr_summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reproducibility_paths = write_reproducibility_files(
        output_path,
        module_name="tfr_ersp_itc",
        input_path=input_path,
        parameters=recorded_params,
        workflow_steps=[
            {"name": "read_raw", "description": "Read EEG with MNE."},
            {"name": "validate", "description": "Validate events, epoch window, baseline, frequency grid, and decimation."},
            {"name": "epoch", "description": "Create event-locked epochs."},
            {"name": "compute_tfr", "description": "Compute Morlet power and optional ITC."},
            {"name": "write_outputs", "description": "Write tables, figures, summaries, and reproducibility files."},
        ],
    )
    sidecars = write_analysis_sidecars(
        output_path,
        module_name="tfr_ersp_itc",
        parameter_schema=TFR_PARAMETER_SCHEMA,
        effective_call={
            "engine": "mne_time_frequency_tfr_morlet",
            "call": "mne.time_frequency.tfr_morlet",
            "kwargs": {"freqs": freqs.tolist(), "n_cycles": n_cycles, "return_itc": bool(params["return_itc"]), "decim": int(params["decim"])},
            "input_shape": {"channels": list(epochs.ch_names), "n_epochs": len(epochs), "n_times": int(epochs.get_data().shape[-1]), "sfreq": float(raw.info["sfreq"])},
            "output_shape": {"power_channels": len(power.ch_names), "power_freqs": len(freqs), "itc_available": bool(itc is not None)},
        },
        threshold_validation={
            "status": "passed",
            "checks": [
                {"field": "baseline", "rule": "baseline must be non-empty", "status": "passed"},
                {"field": "freqs", "rule": "frequency grid must be non-empty and positive", "status": "passed"},
                {"field": "decim", "rule": "decim must be >= 1", "status": "passed"},
            ],
        },
        table_dictionary=_table_dictionary(),
        scope_contract={
            "analysis_scope": "single_record_descriptive_sensor_space_tfr_beta",
            "stable_status": "beta_lab_only",
            "allowed_claims": [
                "Describe event-locked time-frequency power and optional ITC for one uploaded recording.",
                "Summarize exploratory ERSP/ITC patterns for research review with event and baseline context.",
            ],
            "disallowed_claims": [
                "diagnosis_or_treatment_recommendation",
                "p_value_or_statistical_significance_claim",
                "group_or_population_inference",
                "causal_or_mechanistic_conclusion",
                "source_localization_or_brain_region_activation",
            ],
            "customer_boundary_note": TFR_BOUNDARY,
        },
        source_metadata=_source_metadata(input_path, raw, epochs, recorded_params),
    )
    outputs = {
        "tfr_power_long": power_path,
        "tfr_summary_table": summary_path,
        "tfr_power": power_svg,
        "parameters": params_path,
        "frequency_grid": frequency_grid_path,
        "method_description": method_path,
        "tfr_summary": tfr_summary_path,
        "software_versions": reproducibility_paths["software_versions"],
        "workflow": reproducibility_paths["workflow"],
        "parameter_schema_snapshot": sidecars["parameter_schema_snapshot"],
        "threshold_validation": sidecars["threshold_validation"],
        "effective_call": sidecars["effective_call"],
        "source_metadata": sidecars["source_metadata"],
        "table_dictionary": sidecars["table_dictionary"],
        "scope_contract": sidecars["scope_contract"],
    }
    if itc is not None:
        outputs["tfr_itc_long"] = itc_path
        outputs["tfr_itc"] = itc_svg
    contracts = write_output_contract(
        output_path,
        job_type="tfr_ersp_itc",
        module_name="tfr_ersp_itc",
        input_path=input_path,
        parameters=recorded_params,
        summary={
            "schema_version": "qlanalyser-tfr-result-v0.1",
            "module_id": "tfr_ersp_itc",
            "workflow_id": "tfr_ersp_itc",
            "input_file_id": str(Path(input_path).name),
            "data_preparation_plan_id": str(params.get("data_preparation_plan_id") or "none"),
            "parameters_hash": params_hash,
            "summary": summary,
            "artifacts": [str(path.relative_to(output_path).as_posix()) for path in outputs.values() if path.exists() and path.is_relative_to(output_path)],
            "warnings": summary["warnings"],
        },
        outputs=outputs,
        log_lines=[
            f"channels={','.join(epochs.ch_names)}",
            f"freqs_hz={freqs.tolist()}",
            f"epochs={len(epochs)}",
        ],
    )
    contracts["manifest"] = write_manifest(output_path)
    return {**outputs, **contracts}


def validate_tfr_parameters(parameters: dict | None, *, raw) -> dict[str, Any]:
    source = parameters or {}
    params = dict(source)
    params["workflow_id"] = "tfr_ersp_itc"
    params["method"] = "morlet"
    params["event_id"] = str(source.get("event_id") or "")
    params["tmin"] = _float(source.get("tmin"), default=-0.2)
    params["tmax"] = _float(source.get("tmax"), default=0.8)
    params["baseline"] = _float_pair(source.get("baseline"), default=[-0.2, 0.0], name="baseline")
    params["freqs"] = _float_list(source.get("freqs"), default=[8.0, 13.0, 30.0], name="freqs")
    params["n_cycles"] = _float(source.get("n_cycles"), default=3.0)
    params["decim"] = _int(source.get("decim"), default=2)
    params["return_itc"] = _bool(source.get("return_itc"), default=True)
    params["average"] = _bool(source.get("average"), default=True)
    params["picks"] = _string_list(source.get("picks"), name="picks")
    params.setdefault("data_preparation_plan_id", source.get("data_preparation_plan_id") or "none")
    params.setdefault("data_preparation_revision", source.get("data_preparation_revision"))
    
    # P0-ALGO-02: Nyquist frequency validation
    sfreq = float(raw.info["sfreq"])
    nyquist = sfreq / 2.0
    
    if not params["freqs"]:
        raise ValueError("TFR requires at least one frequency")
    if min(params["freqs"]) <= 0:
        raise ValueError("TFR frequencies must be positive")
    if max(params["freqs"]) >= nyquist:
        raise ValueError(f"TFR frequencies must be below Nyquist ({nyquist:.2f} Hz). Requested max: {max(params['freqs']):.2f} Hz")
    
    # P0-ALGO-02: Memory estimation for TFR
    n_channels = raw.get_channel_types().count("eeg")
    if n_channels < 1:
        raise ValueError("TFR requires at least one EEG channel")
    
    # Estimate time points after epoching
    epoch_duration = params["tmax"] - params["tmin"]
    time_points = int(epoch_duration * sfreq / params["decim"])
    freq_points = len(params["freqs"])
    
    # Estimate memory: freq_points × time_points × channels × 8 bytes (float64)
    # Include both power and ITC if requested
    memory_per_epoch_mb = (freq_points * time_points * n_channels * 8) / (1024 * 1024)
    if params["return_itc"]:
        memory_per_epoch_mb *= 2  # Both power and ITC
    
    # Set conservative limit at 2GB
    memory_limit_mb = 2048
    if memory_per_epoch_mb > memory_limit_mb:
        raise ValueError(
            f"TFR memory estimate ({memory_per_epoch_mb:.1f} MB) exceeds limit ({memory_limit_mb} MB). "
            f"Reduce frequency points ({freq_points}), increase decimation (current: {params['decim']}), "
            f"or reduce time window (current: {epoch_duration:.2f}s)"
        )
    
    if params["n_cycles"] <= 0:
        raise ValueError("TFR n_cycles must be positive")
    if params["decim"] < 1:
        raise ValueError("TFR decim must be >= 1")
    if len(params["baseline"]) != 2 or params["baseline"][1] <= params["baseline"][0]:
        raise ValueError("TFR baseline must be a valid start/end pair")
    if params["tmax"] <= params["tmin"]:
        raise ValueError("TFR tmax must be greater than tmin")
    
    return params


def _resolve_event_id(raw, event_id: str) -> dict[str, int] | None:
    if event_id:
        return {event_id: 1}
    annotations = list(raw.annotations.description) if len(raw.annotations) else []
    if annotations:
        return {desc: idx + 1 for idx, desc in enumerate(sorted(set(str(desc) for desc in annotations)))}
    return None


def _power_rows(power, freqs: np.ndarray, channels: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    data = np.asarray(power.data)
    for ch_index, channel in enumerate(channels):
        for freq_index, freq in enumerate(freqs):
            for time_index, time_sec in enumerate(power.times):
                rows.append({
                    "channel": channel,
                    "frequency_hz": round(float(freq), 6),
                    "time_sec": round(float(time_sec), 6),
                    "power_db": round(float(data[ch_index, freq_index, time_index]), 10),
                    "event_count": int(power.data.shape[0]),
                    "baseline": "[-0.2, 0.0]",
                    "unit": "dB",
                })
    return rows


def _itc_rows(itc, freqs: np.ndarray, channels: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    data = np.asarray(itc.data)
    for ch_index, channel in enumerate(channels):
        for freq_index, freq in enumerate(freqs):
            for time_index, time_sec in enumerate(itc.times):
                rows.append({
                    "channel": channel,
                    "frequency_hz": round(float(freq), 6),
                    "time_sec": round(float(time_sec), 6),
                    "itc": round(float(data[ch_index, freq_index, time_index]), 10),
                    "event_count": int(itc.data.shape[0]),
                    "unit": "unitless",
                })
    return rows


def _summary_rows(power_rows: list[dict[str, Any]], itc_rows: list[dict[str, Any]], channels: list[str]) -> list[dict[str, Any]]:
    rows = []
    power_by_channel: dict[str, list[dict[str, Any]]] = {}
    for row in power_rows:
        power_by_channel.setdefault(str(row["channel"]), []).append(row)
    for channel in channels:
        channel_rows = power_by_channel.get(channel, [])
        peak = max(channel_rows, key=lambda item: float(item["power_db"])) if channel_rows else {"frequency_hz": 0, "time_sec": 0, "power_db": 0}
        rows.append({
            "channel": channel,
            "peak_frequency_hz": peak["frequency_hz"],
            "peak_time_sec": peak["time_sec"],
            "peak_power_db": peak["power_db"],
            "itc_available": bool(itc_rows),
            "warnings": "single-record descriptive beta; no statistical inference",
        })
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_heatmap_svg(path: Path, data: np.ndarray, times: np.ndarray, freqs: list[float], title: str) -> None:
    width, height = 860, 460
    left, top = 120, 70
    plot_w, plot_h = 660, 280
    rows = []
    # 使用百分位范围（p2–p98）作为颜色映射区间，避免极端值挤压分布
    flat = data.ravel()
    vmin = float(np.percentile(flat, 2)) if flat.size > 1 else float(np.nanmin(data))
    vmax = float(np.percentile(flat, 98)) if flat.size > 1 else float(np.nanmax(data))
    if vmax - vmin < 1e-12:
        vmax = vmin + 1.0
    for y, freq in enumerate(freqs):
        rows.append(f'<text x="{left - 10}" y="{top + (y + 0.5) * (plot_h / len(freqs))}" text-anchor="end" font-size="12">{freq:g} Hz</text>')
        for x, time_sec in enumerate(times):
            if y == 0:
                rows.append(f'<text x="{left + (x + 0.5) * (plot_w / len(times))}" y="{top - 10}" text-anchor="middle" font-size="12">{time_sec:g}</text>')
            value = float(np.mean(data[:, y, x])) if data.ndim >= 3 else float(data[y, x])
            rows.append(f'<rect x="{left + x * (plot_w / len(times)):.1f}" y="{top + y * (plot_h / len(freqs)):.1f}" width="{plot_w / len(times):.1f}" height="{plot_h / len(freqs):.1f}" fill="{_heat_color(value, vmin, vmax)}" stroke="#ffffff"/>')
    # 颜色图例
    legend_x = left + plot_w + 20
    for i in range(10):
        y_legend = top + i * (plot_h / 10)
        frac = 1.0 - i / 9.0
        rows.append(f'<rect x="{legend_x}" y="{y_legend:.1f}" width="16" height="{plot_h/10:.1f}" fill="{_heat_color(vmin + frac * (vmax - vmin), vmin, vmax)}" stroke="none"/>')
    rows.append(f'<text x="{legend_x + 20}" y="{top + 10}" font-size="10" fill="#333">{vmax:.1f} dB</text>')
    rows.append(f'<text x="{legend_x + 20}" y="{top + plot_h - 4}" font-size="10" fill="#333">{vmin:.1f} dB</text>')
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="#ffffff"/>
  <text x="{width / 2:.1f}" y="30" text-anchor="middle" font-size="18" fill="#10242c">{title}</text>
  {''.join(rows)}
  <text x="{width / 2:.1f}" y="{height - 26}" text-anchor="middle" font-size="12" fill="#52616a">Descriptive sensor-space display only; no significance or group inference.</text>
</svg>
""",
        encoding="utf-8",
    )


def _heat_color(value: float, min_value: float, max_value: float) -> str:
    span = max(max_value - min_value, 1e-9)
    scale = max(0.0, min(1.0, (value - min_value) / span))
    red = int(248 - 70 * scale)
    green = int(244 - 155 * scale)
    blue = int(236 - 190 * scale)
    return f"rgb({red},{green},{blue})"


def _table_dictionary() -> dict[str, Any]:
    return {
        "tables/tfr_power_long.csv": {key: "TFR beta power column" for key in ["channel", "frequency_hz", "time_sec", "power_db", "event_count", "baseline", "unit"]},
        "tables/tfr_summary.csv": {key: "TFR beta summary column" for key in ["channel", "peak_frequency_hz", "peak_time_sec", "peak_power_db", "itc_available", "warnings"]},
        "tables/tfr_itc_long.csv": {key: "TFR beta ITC column" for key in ["channel", "frequency_hz", "time_sec", "itc", "event_count", "unit"]},
    }


def _source_metadata(input_path: str | Path, raw, epochs, params: dict[str, Any]) -> dict[str, Any]:
    return {
        "input_path": str(input_path),
        "reader": "mne",
        "channels": list(epochs.ch_names),
        "sfreq": float(raw.info["sfreq"]),
        "epoch_count": len(epochs),
        "parameter_hash": stable_json_hash(params),
    }


def _float(value: Any, *, default: float) -> float:
    return float(default if value in (None, "") else value)


def _int(value: Any, *, default: int) -> int:
    return int(default if value in (None, "") else value)


def _bool(value: Any, *, default: bool) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _float_list(value: Any, *, default: list[float], name: str) -> list[float]:
    if value in (None, ""):
        return list(default)
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        raise ValueError(f"{name} must be a list or comma-separated string")
    result = [float(item) for item in items]
    if not result:
        raise ValueError(f"{name} must not be empty")
    return result


def _float_pair(value: Any, *, default: list[float], name: str) -> list[float]:
    result = _float_list(value, default=default, name=name)
    if len(result) != 2:
        raise ValueError(f"{name} must contain two values")
    return result


def _string_list(value: Any, *, name: str) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, (list, tuple)):
        items = [str(item).strip() for item in value if str(item).strip()]
    else:
        raise ValueError(f"{name} must be a list or comma-separated string")
    return items
