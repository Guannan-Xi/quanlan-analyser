import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from eeg_core.io.readers import read_raw
from eeg_core.report.reproducibility import write_output_contract, write_reproducibility_files

DEFAULT_PREVIEW = {
    "start_sec": 0.0,
    "duration_sec": 12.0,
    "channel_limit": 8,
    "display_sfreq": 200.0,
    "amplitude_unit": "uV",
    "show_annotations": True,
    "show_events": True,
    "vertical_scale_uv": 100.0,
}

DEFAULT_FILTER_PREVIEW = {
    "enabled": True,
    "bandpass": {"enabled": True, "l_freq": 1.0, "h_freq": 40.0, "method": "fir"},
    "notch": {"enabled": True, "freqs": [50.0], "method": "fir"},
    "compare_mode": "stacked",
    "apply_to": "preview_window_only",
}

MAX_DURATION_SEC = 30.0
MAX_CHANNELS = 32
MAX_DISPLAY_POINTS = 1200


class QcPreviewError(ValueError):
    def __init__(self, code: str, message: str, detail: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail or {}


def run_qc_preview(input_path: str | Path, output_dir: str | Path, parameters: dict | None = None) -> dict[str, Path]:
    """Generate a service-style QC waveform/filter preview package.

    The uploaded EEG file is never modified. Band-pass and notch settings are
    applied only to the selected preview window and are recorded as preview-only
    evidence for user review.
    """
    input_file = Path(input_path)
    output_path = Path(output_dir)
    data_dir = output_path / "data"
    figure_dir = output_path / "figures"
    snapshot_dir = figure_dir / "snapshots"
    repro_dir = output_path / "reproducibility"
    for folder in (data_dir, figure_dir, snapshot_dir, repro_dir):
        folder.mkdir(parents=True, exist_ok=True)

    parameters = parameters or {}
    preview = {**DEFAULT_PREVIEW, **(parameters.get("preview") or {})}
    filter_preview = _merge_filter(parameters.get("filter_preview") or {})
    snapshot = parameters.get("snapshot") or {}

    raw = read_raw(input_file)
    sfreq = float(raw.info["sfreq"])
    duration_sec = _duration(raw)
    picks = _pick_channels(raw, preview)
    start_sec, duration = _validate_window(preview, duration_sec)
    stop_sec = start_sec + duration

    raw_window = raw.copy().pick(picks).crop(tmin=start_sec, tmax=stop_sec, include_tmax=False)
    display_sfreq = _display_sfreq(preview, sfreq)
    raw_display = raw_window.copy()
    if display_sfreq < sfreq:
        raw_display.resample(display_sfreq, npad="auto", verbose="ERROR")
    raw_uv, times = _window_data(raw_display, start_sec)

    filtered_uv = None
    filter_warnings = ["Filtering is for preview only and does not modify the uploaded file."]
    if filter_preview.get("enabled"):
        _validate_filter(filter_preview, sfreq)
        filtered_display = raw_window.copy().load_data(verbose="ERROR")
        bandpass = filter_preview.get("bandpass") or {}
        notch = filter_preview.get("notch") or {}
        if bandpass.get("enabled"):
            filtered_display.filter(
                l_freq=_float_or_none(bandpass.get("l_freq")),
                h_freq=_float_or_none(bandpass.get("h_freq")),
                method=str(bandpass.get("method") or "fir"),
                verbose="ERROR",
            )
        if notch.get("enabled"):
            freqs = [float(item) for item in notch.get("freqs") or []]
            if freqs:
                filtered_display.notch_filter(freqs=freqs, method=str(notch.get("method") or "fir"), verbose="ERROR")
        if display_sfreq < sfreq:
            filtered_display.resample(display_sfreq, npad="auto", verbose="ERROR")
        filtered_uv, _ = _window_data(filtered_display, start_sec)

    annotations = _annotation_preview(raw, start_sec, stop_sec) if preview.get("show_annotations", True) else []
    channel_names = [raw.ch_names[idx] for idx in picks]

    waveform_payload = {
        "input_file": str(input_file),
        "start_sec": start_sec,
        "duration_sec": duration,
        "sfreq_original": sfreq,
        "sfreq_display": display_sfreq,
        "channels": channel_names,
        "unit": "uV",
        "times_sec": _round_list(times),
        "data_uv": _round_matrix(raw_uv),
        "annotations": annotations,
        "decimation": {"enabled": display_sfreq < sfreq, "reason": "display_only"},
    }
    waveform_path = _write_json(data_dir / "waveform_preview.json", waveform_payload)

    filter_payload = {
        "filter_preview_only": True,
        "enabled": bool(filter_preview.get("enabled")),
        "parameters": filter_preview,
        "input_window": {"start_sec": start_sec, "duration_sec": duration, "channels": channel_names},
        "sfreq_original": sfreq,
        "sfreq_display": display_sfreq,
        "unit": "uV",
        "times_sec": _round_list(times),
        "data_uv": _round_matrix(filtered_uv) if filtered_uv is not None else [],
        "warnings": filter_warnings,
    }
    filter_path = _write_json(data_dir / "filter_preview.json", filter_payload)

    raw_figure_path = figure_dir / "waveform_raw_preview.svg"
    filter_figure_path = figure_dir / "waveform_filter_preview.svg"
    snapshot_path = snapshot_dir / "snapshot_001.svg"
    _write_svg(raw_figure_path, times, raw_uv, channel_names, title="QC raw waveform preview", annotations=annotations)
    _write_svg(
        filter_figure_path,
        times,
        filtered_uv if filtered_uv is not None else raw_uv,
        channel_names,
        title="QC filter preview",
        annotations=annotations,
        compare=raw_uv if filtered_uv is not None else None,
    )
    _write_svg(
        snapshot_path,
        times,
        filtered_uv if filtered_uv is not None else raw_uv,
        channel_names,
        title=str(snapshot.get("label") or "QC preview snapshot"),
        annotations=annotations,
        compare=raw_uv if filtered_uv is not None else None,
    )

    snapshot_payload = {
        "snapshot_id": "snapshot_001",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "label": snapshot.get("label") or "QC preview snapshot",
        "input_file": str(input_file),
        "time_window": {"start_sec": start_sec, "duration_sec": duration},
        "channels": channel_names,
        "filter_preview": filter_preview,
        "figure": "figures/snapshots/snapshot_001.svg",
        "review_note": "User-visible preview snapshot; not a clinical interpretation.",
    }
    snapshot_json_path = _write_json(data_dir / "snapshot_001.json", snapshot_payload)

    parameters_path = _write_json(
        repro_dir / "parameters.json",
        {
            "input": str(input_file),
            "module": "qc",
            "job_type": "qc_waveform_preview",
            "parameters": parameters,
            "defaults": {"preview": DEFAULT_PREVIEW, "filter_preview": DEFAULT_FILTER_PREVIEW},
            "preview_only_filtering": True,
        },
    )
    method_path = repro_dir / "method_description.txt"
    method_path.write_text(
        "QC preview reads a selected EEG time window with MNE-Python, renders raw waveforms, "
        "optionally applies band-pass and notch filtering to the preview window only, and exports "
        "a user-visible snapshot. Filtering is preview-only and does not modify the uploaded file.\n",
        encoding="utf-8",
    )
    reproducibility_paths = write_reproducibility_files(
        output_path,
        module_name="qc",
        input_path=input_file,
        parameters=parameters,
        workflow_steps=[
            {"name": "read_raw", "description": "Open the EEG recording with the MNE reader selected by file suffix."},
            {"name": "select_preview_window", "description": "Select requested channels and time window for display."},
            {"name": "optional_filter_preview", "description": "Apply band-pass and notch filters only to the copied preview window."},
            {"name": "write_preview_artifacts", "description": "Write waveform JSON, SVG figures, snapshot metadata, and contract files."},
        ],
    )

    summary = {
        "status": "completed",
        "preview_status": "ready",
        "filter_preview_only": True,
        "start_sec": start_sec,
        "duration_sec": duration,
        "sfreq_original": sfreq,
        "sfreq_display": display_sfreq,
        "n_channels": len(channel_names),
        "channels": channel_names,
        "filter_enabled": bool(filter_preview.get("enabled")),
        "snapshot": "figures/snapshots/snapshot_001.svg",
        "warnings": filter_warnings,
    }

    core_outputs = {
        "waveform_preview": waveform_path,
        "filter_preview": filter_path,
        "snapshot_json": snapshot_json_path,
        "raw_preview_figure": raw_figure_path,
        "filter_preview_figure": filter_figure_path,
        "snapshot_figure": snapshot_path,
        "parameters": parameters_path,
        "method_description": method_path,
        "software_versions": reproducibility_paths["software_versions"],
        "workflow": reproducibility_paths["workflow"],
    }
    contract_paths = write_output_contract(
        output_path,
        job_type="qc_waveform_preview",
        module_name="qc",
        input_path=input_file,
        parameters=parameters,
        summary=summary,
        outputs=core_outputs,
        log_lines=[
            f"preview_window={start_sec}-{stop_sec}s",
            f"channels={','.join(channel_names)}",
            "filter_preview_only=true",
        ],
    )
    return {**core_outputs, **contract_paths}


def _merge_filter(overrides: dict) -> dict:
    merged = {
        **DEFAULT_FILTER_PREVIEW,
        **overrides,
        "bandpass": {**DEFAULT_FILTER_PREVIEW["bandpass"], **(overrides.get("bandpass") or {})},
        "notch": {**DEFAULT_FILTER_PREVIEW["notch"], **(overrides.get("notch") or {})},
    }
    return merged


def _duration(raw) -> float:
    return float(raw.n_times) / float(raw.info["sfreq"])


def _pick_channels(raw, preview: dict) -> list[int]:
    requested = [str(item) for item in (preview.get("channels") or []) if str(item).strip()]
    if requested:
        missing = [name for name in requested if name not in raw.ch_names]
        if missing:
            raise QcPreviewError("CHANNEL_NOT_FOUND", f"Channels not found: {', '.join(missing)}", {"missing": missing})
        picks = [raw.ch_names.index(name) for name in requested]
    else:
        eeg_picks = raw.copy().pick("eeg", exclude=[]).ch_names
        names = eeg_picks or raw.ch_names
        limit = min(int(preview.get("channel_limit") or DEFAULT_PREVIEW["channel_limit"]), MAX_CHANNELS)
        picks = [raw.ch_names.index(name) for name in names[:limit]]
    if not picks:
        raise QcPreviewError("NO_EEG_CHANNELS", "No channels are available for preview")
    if len(picks) > MAX_CHANNELS:
        raise QcPreviewError("TOO_MANY_CHANNELS", f"Preview supports up to {MAX_CHANNELS} channels", {"max_channels": MAX_CHANNELS})
    return picks


def _validate_window(preview: dict, duration_sec: float) -> tuple[float, float]:
    start_sec = float(preview.get("start_sec") or 0.0)
    duration = float(preview.get("duration_sec") or DEFAULT_PREVIEW["duration_sec"])
    if start_sec < 0:
        raise QcPreviewError("TIME_WINDOW_OUT_OF_RANGE", "Preview start must be >= 0", {"duration_sec": duration_sec})
    if duration <= 0:
        raise QcPreviewError("TIME_WINDOW_OUT_OF_RANGE", "Preview duration must be > 0", {"duration_sec": duration_sec})
    if duration > MAX_DURATION_SEC:
        raise QcPreviewError("TIME_WINDOW_TOO_LONG", f"Preview duration cannot exceed {MAX_DURATION_SEC} seconds", {"max_duration_sec": MAX_DURATION_SEC})
    if start_sec >= duration_sec or start_sec + duration > duration_sec + 1e-9:
        raise QcPreviewError(
            "TIME_WINDOW_OUT_OF_RANGE",
            "Preview time window is outside the recording",
            {"recording_duration_sec": duration_sec, "start_sec": start_sec, "duration_sec": duration},
        )
    return start_sec, duration


def _display_sfreq(preview: dict, sfreq: float) -> float:
    requested = float(preview.get("display_sfreq") or DEFAULT_PREVIEW["display_sfreq"])
    if requested <= 0:
        return sfreq
    return min(sfreq, requested)


def _validate_filter(filter_preview: dict, sfreq: float) -> None:
    nyquist = sfreq / 2.0
    bandpass = filter_preview.get("bandpass") or {}
    notch = filter_preview.get("notch") or {}
    if bandpass.get("enabled"):
        l_freq = _float_or_none(bandpass.get("l_freq"))
        h_freq = _float_or_none(bandpass.get("h_freq"))
        if l_freq is not None and l_freq < 0:
            raise QcPreviewError("INVALID_FILTER_PARAMETER", "Band-pass low cutoff must be >= 0")
        if h_freq is not None and h_freq >= nyquist:
            raise QcPreviewError("INVALID_FILTER_PARAMETER", "Band-pass high cutoff must be lower than Nyquist frequency", {"nyquist": nyquist})
        if l_freq is not None and h_freq is not None and l_freq >= h_freq:
            raise QcPreviewError("INVALID_FILTER_PARAMETER", "Band-pass low cutoff must be lower than high cutoff")
    if notch.get("enabled"):
        for freq in notch.get("freqs") or []:
            value = float(freq)
            if value <= 0 or value >= nyquist:
                raise QcPreviewError("INVALID_FILTER_PARAMETER", "Notch frequency must be between 0 and Nyquist frequency", {"nyquist": nyquist})


def _float_or_none(value: Any) -> float | None:
    if value in (None, "", "none"):
        return None
    return float(value)


def _window_data(raw_window, start_sec: float) -> tuple[np.ndarray, np.ndarray]:
    data = raw_window.get_data() * 1e6
    n_times = data.shape[1]
    sfreq = float(raw_window.info["sfreq"])
    times = start_sec + np.arange(n_times) / sfreq
    if n_times > MAX_DISPLAY_POINTS:
        idx = np.linspace(0, n_times - 1, MAX_DISPLAY_POINTS).astype(int)
        data = data[:, idx]
        times = times[idx]
    return data, times


def _annotation_preview(raw, start_sec: float, stop_sec: float) -> list[dict]:
    annotations = []
    for annotation in raw.annotations:
        onset = float(annotation["onset"])
        if start_sec <= onset <= stop_sec:
            annotations.append({
                "onset_sec": onset,
                "relative_sec": onset - start_sec,
                "duration_sec": float(annotation["duration"]),
                "description": str(annotation["description"]),
            })
    return annotations[:50]


def _round_list(values: np.ndarray) -> list[float]:
    return [round(float(item), 6) for item in values.tolist()]


def _round_matrix(values: np.ndarray | None) -> list[list[float]]:
    if values is None:
        return []
    return [[round(float(item), 4) for item in row] for row in values.tolist()]


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_svg(path: Path, times: np.ndarray, data_uv: np.ndarray, channels: list[str], *, title: str, annotations: list[dict], compare: np.ndarray | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 1100
    row_height = 62
    top = 62
    left = 92
    right = 28
    height = top + max(1, len(channels)) * row_height + 44
    plot_width = width - left - right
    x_min = float(times[0]) if len(times) else 0.0
    x_max = float(times[-1]) if len(times) else x_min + 1.0
    if math.isclose(x_min, x_max):
        x_max = x_min + 1.0

    rows = []
    for row_index, channel in enumerate(channels):
        y_mid = top + row_index * row_height + row_height / 2
        values = data_uv[row_index]
        comp_values = compare[row_index] if compare is not None else None
        scale = max(float(np.nanmax(np.abs(values))) if values.size else 1.0, 1.0)
        if comp_values is not None and comp_values.size:
            scale = max(scale, float(np.nanmax(np.abs(comp_values))), 1.0)
        scale *= 1.12
        rows.append(f'<text x="12" y="{y_mid + 4:.1f}" class="label">{_xml(channel)}</text>')
        rows.append(f'<line x1="{left}" y1="{y_mid:.1f}" x2="{width-right}" y2="{y_mid:.1f}" class="baseline"/>')
        if comp_values is not None:
            rows.append(f'<polyline class="trace raw" points="{_points(times, comp_values, x_min, x_max, left, plot_width, y_mid, row_height, scale)}"/>')
        rows.append(f'<polyline class="trace filtered" points="{_points(times, values, x_min, x_max, left, plot_width, y_mid, row_height, scale)}"/>')
    annotation_lines = []
    for item in annotations:
        x = left + ((float(item["onset_sec"]) - x_min) / (x_max - x_min)) * plot_width
        annotation_lines.append(f'<line x1="{x:.1f}" y1="{top - 18}" x2="{x:.1f}" y2="{height - 34}" class="annotation"/>')
        annotation_lines.append(f'<text x="{x + 4:.1f}" y="{top - 22}" class="annotation-label">{_xml(item["description"])}</text>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>
    .title {{ font: 700 22px system-ui, sans-serif; fill: #10242c; }}
    .subtitle {{ font: 500 12px system-ui, sans-serif; fill: #5d6e78; }}
    .label {{ font: 700 12px system-ui, sans-serif; fill: #344451; }}
    .baseline {{ stroke: #dbe7ea; stroke-width: 1; }}
    .trace {{ fill: none; stroke-width: 1.3; }}
    .trace.raw {{ stroke: #9aa8b2; opacity: .72; }}
    .trace.filtered {{ stroke: #147d78; }}
    .annotation {{ stroke: #d95f43; stroke-width: 1; stroke-dasharray: 4 4; }}
    .annotation-label {{ font: 600 11px system-ui, sans-serif; fill: #9f341f; }}
    .axis {{ stroke: #8aa0a8; stroke-width: 1; }}
  </style>
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="24" y="32" class="title">{_xml(title)}</text>
  <text x="24" y="52" class="subtitle">{x_min:.3f}s - {x_max:.3f}s · {len(channels)} channels · unit: uV · preview-only filtering when shown</text>
  <line x1="{left}" y1="{height-32}" x2="{width-right}" y2="{height-32}" class="axis"/>
  <text x="{left}" y="{height-12}" class="subtitle">{x_min:.2f}s</text>
  <text x="{width-right-58}" y="{height-12}" class="subtitle">{x_max:.2f}s</text>
  {''.join(annotation_lines)}
  {''.join(rows)}
</svg>
'''
    path.write_text(svg, encoding="utf-8")
    return path


def _points(times: np.ndarray, values: np.ndarray, x_min: float, x_max: float, left: int, plot_width: int, y_mid: float, row_height: int, scale: float) -> str:
    if len(times) == 0:
        return ""
    xs = left + ((times - x_min) / (x_max - x_min)) * plot_width
    ys = y_mid - (values / scale) * (row_height * 0.35)
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))


def _xml(value: Any) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")