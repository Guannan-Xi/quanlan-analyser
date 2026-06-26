import csv
import html
import json
from pathlib import Path

import mne
import numpy as np

from eeg_core.io.readers import read_raw
from eeg_core.report.reproducibility import write_output_contract, write_reproducibility_files


DEFAULT_COMPONENT_ROIS = {
    "N100": ["Fz", "Cz"],
    "P200": ["Fz", "Cz", "Pz"],
    "P300": ["Pz", "P3", "P4"],
}


def _normalize_roi_parameters(parameters: dict, components: dict, eeg_channel_names: list[str]) -> tuple[dict, list[str]]:
    roi_param = parameters.get("roi_channels") or parameters.get("roi")
    available = {channel.lower(): channel for channel in eeg_channel_names}
    requested_missing: list[str] = []

    def resolve(names: list[str]) -> list[str]:
        resolved: list[str] = []
        for name in names:
            channel = available.get(str(name).lower())
            if channel and channel not in resolved:
                resolved.append(channel)
            elif not channel:
                requested_missing.append(str(name))
        return resolved

    if roi_param is None:
        roi_by_component = {component: resolve(DEFAULT_COMPONENT_ROIS.get(component, [])) for component in components}
    elif isinstance(roi_param, list):
        resolved = resolve(roi_param)
        roi_by_component = {component: list(resolved) for component in components}
    elif isinstance(roi_param, dict):
        roi_by_component = {}
        default_roi = roi_param.get("default") or roi_param.get("all")
        for component in components:
            names = roi_param.get(component, default_roi)
            if names is None:
                names = DEFAULT_COMPONENT_ROIS.get(component, [])
            if not isinstance(names, list):
                raise ValueError("ERP roi_channels values must be channel lists")
            roi_by_component[component] = resolve(names)
    else:
        raise ValueError("ERP roi_channels must be a channel list or a component-to-channel mapping")

    fallback = list(eeg_channel_names)
    for component in components:
        if not roi_by_component.get(component):
            roi_by_component[component] = fallback
    return roi_by_component, sorted(set(requested_missing))


def _summarize_drop_log(epochs) -> dict:
    reasons: dict[str, int] = {}
    dropped = 0
    for entry in epochs.drop_log:
        if entry:
            dropped += 1
            for reason in entry:
                reasons[str(reason)] = reasons.get(str(reason), 0) + 1
    return {
        "total_input_events": len(epochs.drop_log),
        "kept_epochs": int(len(epochs)),
        "dropped_epochs": int(dropped),
        "drop_rate": float(dropped / len(epochs.drop_log)) if epochs.drop_log else 0.0,
        "reasons": reasons,
    }


def _epoch_rejection_policy(parameters: dict, applied_directives: dict, reject: dict | None, reject_by_annotation: bool) -> dict:
    bad_segments = list(applied_directives.get("bad_segments") or [])
    rejection_thresholds = {
        "eeg": reject.get("eeg") if reject else None,
        "source": "parameters.reject_eeg_uv" if reject else "not_configured",
        "unit": "V" if reject else None,
    }
    return {
        "reject_by_annotation": reject_by_annotation,
        "bad_spans": bad_segments,
        "bad_spans_policy": "Applied as BAD annotations before epoching when provided; explicit none when empty.",
        "breaks": [],
        "break_policy": "No break detection was configured for this V01 ERP run.",
        "rejection_thresholds": rejection_thresholds,
        "threshold_policy": "Amplitude rejection threshold is explicit when reject_eeg_uv is provided; otherwise no amplitude threshold is applied.",
        "condition_balance_warning_policy": "Review per-condition epoch counts and drop_rate before interpretation.",
    }


def _channel_name(value) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        candidate = value.get("name") or value.get("channel") or value.get("channel_name") or value.get("label")
        return str(candidate) if candidate else None
    return None


def _bad_segment_window(item: dict) -> tuple[float | None, float | None]:
    start = item.get("onset", item.get("start", item.get("start_sec", item.get("startSec"))))
    duration = item.get("duration", item.get("duration_sec", item.get("durationSec")))
    end = item.get("end", item.get("end_sec", item.get("endSec")))
    try:
        onset = float(start)
        if duration is None and end is not None:
            duration = float(end) - onset
        duration = float(duration)
    except (TypeError, ValueError):
        return None, None
    return onset, duration


def _apply_data_preparation_directives(raw, parameters: dict) -> dict:
    bad_channels = []
    for item in parameters.get("bad_channels") or []:
        name = _channel_name(item)
        if name and name in raw.ch_names and name not in bad_channels:
            bad_channels.append(name)
    if bad_channels:
        raw.info["bads"] = sorted(set(raw.info.get("bads", [])) | set(bad_channels))

    bad_segments = []
    for item in parameters.get("bad_segments") or []:
        if not isinstance(item, dict):
            raise ValueError("ERP bad_segments entries must be objects")
        onset, duration = _bad_segment_window(item)
        if onset is None or duration is None or onset < 0 or duration <= 0:
            raise ValueError("ERP bad_segments entries require onset >= 0 and duration > 0")
        description = str(item.get("description") or item.get("reason") or "data_preparation_segment")
        if not description.upper().startswith("BAD"):
            description = f"BAD_{description}"
        bad_segments.append({"onset": onset, "duration": duration, "description": description})
    if bad_segments:
        raw.set_annotations(raw.annotations + mne.Annotations(
            onset=[item["onset"] for item in bad_segments],
            duration=[item["duration"] for item in bad_segments],
            description=[item["description"] for item in bad_segments],
        ))

    return {
        "bad_channels": bad_channels,
        "bad_segments": bad_segments,
        "annotation_actions": list(parameters.get("annotation_actions") or []),
        "annotation_actions_status": "recorded_only_p0",
    }


def run_erp(input_path: str | Path, output_dir: str | Path, parameters: dict | None = None) -> dict[str, Path]:
    parameters = parameters or {}
    output_path = Path(output_dir)
    figures = output_path / "figures"
    tables = output_path / "tables"
    reproducibility = output_path / "reproducibility"
    for directory in (figures, tables, reproducibility):
        directory.mkdir(parents=True, exist_ok=True)

    try:
        import mne
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("MNE-Python is required for ERP analysis") from exc

    raw = read_raw(input_path, preload=True)
    if not raw.get_channel_types().count("eeg"):
        raise ValueError("ERP requires at least one EEG channel")
    applied_directives = _apply_data_preparation_directives(raw, parameters)
    eeg_channels = [name for name, kind in zip(raw.ch_names, raw.get_channel_types()) if kind == "eeg"]

    event_id = parameters.get("event_id")
    if event_id and not isinstance(event_id, dict):
        raise ValueError("event_id must be a mapping such as {'target': 2}")

    events, discovered_event_id = mne.events_from_annotations(raw, verbose="ERROR")
    if len(events) == 0:
        raise ValueError("ERP analysis requires event markers or annotations; none were found")
    if not event_id:
        event_id = discovered_event_id
    selected = {str(k): int(v) for k, v in event_id.items() if int(v) in set(events[:, 2])}
    if not selected:
        raise ValueError("None of the requested ERP event_id values are present in the file")
    event_confirmation = {
        "source": "annotations",
        "discovered_event_id": {str(k): int(v) for k, v in discovered_event_id.items()},
        "selected_event_id": selected,
        "confirmed": bool(parameters.get("event_id_confirmed", False)),
        "note": "Event labels should be checked against the task protocol before interpretation.",
    }

    l_freq = parameters.get("l_freq", 0.1)
    h_freq = parameters.get("h_freq", 30.0)
    raw.filter(l_freq=l_freq, h_freq=h_freq, verbose="ERROR")
    reference = parameters.get("reference", "average")
    if reference:
        raw.set_eeg_reference(reference, verbose="ERROR")

    tmin = float(parameters.get("tmin", -0.2))
    tmax = float(parameters.get("tmax", 0.8))
    baseline = parameters.get("baseline", [None, 0.0])
    baseline_tuple = tuple(baseline) if baseline is not None else None
    reject_by_annotation = bool(parameters.get("reject_by_annotation", True))
    reject_uv = parameters.get("reject_eeg_uv")
    reject = {"eeg": float(reject_uv) * 1e-6} if reject_uv else None
    epoch_rejection_policy = _epoch_rejection_policy(parameters, applied_directives, reject, reject_by_annotation)
    windows = parameters.get("components") or {
        "N100": [0.08, 0.14],
        "P200": [0.16, 0.26],
        "P300": [0.28, 0.45],
    }
    roi_by_component, missing_roi_channels = _normalize_roi_parameters(parameters, windows, eeg_channels)

    epochs = mne.Epochs(
        raw,
        events,
        event_id=selected,
        tmin=tmin,
        tmax=tmax,
        baseline=baseline_tuple,
        reject=reject,
        reject_by_annotation=reject_by_annotation,
        preload=True,
        verbose="ERROR",
    )
    if len(epochs) == 0:
        raise ValueError("No ERP epochs remained after epoching/rejection")

    rows = []
    evoked_by_condition = {}
    evoked_index = {}
    for condition in selected:
        evoked = epochs[condition].average()
        evoked_by_condition[condition] = evoked
        evoked_index[condition] = {
            "n_epochs": int(len(epochs[condition])),
            "channels": list(evoked.ch_names),
            "reference": reference,
            "roi_channels_by_component": roi_by_component,
        }
        for component, window in windows.items():
            start, stop = sorted([float(window[0]), float(window[1])])
            mask = (evoked.times >= start) & (evoked.times <= stop)
            if not mask.any():
                raise ValueError(f"ERP component window for {component} is outside the epoch time range")
            roi_channels = roi_by_component.get(component) or eeg_channels
            missing = [name for name in roi_channels if name not in evoked.ch_names]
            if missing:
                raise ValueError(f"ERP ROI channels missing for {component}: {missing}")
            roi_index = [evoked.ch_names.index(name) for name in roi_channels]
            data_uv = evoked.data[roi_index][:, mask] * 1e6
            mean_by_time = data_uv.mean(axis=0)
            if component.upper().startswith("N"):
                idx = int(np.argmin(mean_by_time))
            else:
                idx = int(np.argmax(mean_by_time))
            rows.append({
                "condition": condition,
                "component": component,
                "window_ms": f"{int(start*1000)}-{int(stop*1000)}",
                "amplitude_uv": float(mean_by_time[idx]),
                "latency_ms": float(evoked.times[mask][idx] * 1000.0),
                "n_epochs": int(len(epochs[condition])),
                "reference": reference,
                "roi_name": component,
                "roi_channels": ",".join(roi_channels),
            })

    if not rows:
        raise ValueError("ERP metrics could not be computed for the requested component windows")
    per_condition_epoch_counts = {condition: int(info["n_epochs"]) for condition, info in evoked_index.items()}

    metrics_path = tables / "erp_metrics.csv"
    with metrics_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["condition", "component", "window_ms", "amplitude_uv", "latency_ms", "n_epochs", "reference", "roi_name", "roi_channels"])
        writer.writeheader()
        writer.writerows(rows)

    waveform_path = figures / "erp_roi_waveform.svg"
    _write_erp_waveform_svg(waveform_path, evoked_by_condition, roi_by_component, windows, reference)

    drop_log_summary = _summarize_drop_log(epochs)
    drop_log_summary["epoch_rejection_policy"] = epoch_rejection_policy
    drop_log_summary["warnings"] = [
        "Review per-condition epoch counts and drop_rate before interpreting ERP descriptors.",
    ]
    drop_log_path = reproducibility / "drop_log_summary.json"
    drop_log_path.write_text(json.dumps(drop_log_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    event_confirmation_path = reproducibility / "event_confirmation.json"
    event_confirmation_path.write_text(json.dumps(event_confirmation, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "status": "computed",
        "engine": "mne",
        "event_id": selected,
        "events_total": int(len(events)),
        "epochs_total": int(len(epochs)),
        "drop_log": drop_log_summary,
        "event_confirmation": event_confirmation,
        "tmin": tmin,
        "tmax": tmax,
        "baseline": baseline,
        "baseline_state": "baseline_correction_applied" if baseline is not None else "no_baseline_correction",
        "reject_by_annotation": reject_by_annotation,
        "epoch_rejection_policy": epoch_rejection_policy,
        "bad_spans": epoch_rejection_policy["bad_spans"],
        "breaks": epoch_rejection_policy["breaks"],
        "rejection_thresholds": epoch_rejection_policy["rejection_thresholds"],
        "warnings": [
            "Review per-condition epoch counts and drop_rate before interpreting ERP descriptors.",
        ],
        "nave": per_condition_epoch_counts,
        "per_condition_epoch_counts": per_condition_epoch_counts,
        "units": "uV",
        "channel_units": {"eeg": "uV"},
        "components": windows,
        "roi_by_component": roi_by_component,
        "missing_roi_channels": missing_roi_channels,
        "conditions": evoked_index,
        "parameters": parameters,
        "data_preparation_plan_id": parameters.get("data_preparation_plan_id"),
        "data_preparation_revision": parameters.get("data_preparation_revision"),
        "applied_data_preparation": applied_directives,
    }
    parameters_path = reproducibility / "parameters.json"
    parameters_path.write_text(json.dumps({"input": str(input_path), "module": "erp", "parameters": parameters, "engine": "mne", "roi_by_component": roi_by_component, "event_confirmation": event_confirmation, "epoch_rejection_policy": epoch_rejection_policy}, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path = reproducibility / "erp_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    method_path = reproducibility / "method_description.txt"
    method_path.write_text(
        "ERP analysis used MNE-Python annotations/events to epoch EEG around event markers, baseline-correct epochs, "
        "average by condition, and extract N100/P200/P300 window amplitudes and latencies from ROI-aware channel sets. "
        "Marker timing, condition semantics, reference choice, and ROI selection must be verified before interpretation. "
        "This descriptive single-record ERP output is not diagnostic, clinical, causal, or group-level evidence.\n",
        encoding="utf-8",
    )
    scope_contract_path = reproducibility / "scope_contract.json"
    scope_contract_path.write_text(
        json.dumps(
            {
                "module": "erp",
                "analysis_scope": "single_record_descriptive_event_locked_sensor_space_erp",
                "stable_status": "v01_required_when_events_exist",
                "allowed_claims": [
                    "Describe event-locked sensor-space ERP amplitudes and latencies for one recording.",
                    "Report per-condition epoch counts, baseline window, reference, ROI channels, and drop-log context.",
                ],
                "disallowed_claims": [
                    "diagnosis_or_treatment_recommendation",
                    "group_or_population_inference",
                    "statistical_significance_claim",
                    "causal_or_mechanistic_conclusion",
                    "source_localization_or_brain_region_activation",
                ],
                "interpretation_boundary": "ERP descriptors require verified event semantics, QC, reference, ROI, baseline, and epoch rejection context before interpretation.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    reproducibility_paths = write_reproducibility_files(
        output_path,
        module_name="erp",
        input_path=input_path,
        parameters=parameters,
        workflow_steps=[
            {"name": "read_raw", "description": "Read EEG data with MNE using a format-specific reader."},
            {"name": "apply_data_preparation", "description": "Apply confirmed bad channel and bad segment directives when provided."},
            {"name": "events_from_annotations", "description": "Derive events and event_id from MNE annotations."},
            {"name": "event_confirmation", "description": "Record discovered event_id, selected event_id, and whether the mapping was confirmed by the user or protocol."},
            {"name": "filter_reference", "description": "Apply band-pass filter and re-reference (default average)."},
            {"name": "epoch", "description": "Epoch around event markers with baseline correction and optional amplitude rejection."},
            {"name": "evoked", "description": "Average epochs per condition to compute evoked responses."},
            {"name": "roi_metrics", "description": "Extract component metrics from ROI-aware channel sets and record the ROI used per component."},
            {"name": "drop_log", "description": "Summarize rejected and dropped epochs with human-readable reasons."},
            {"name": "write_outputs", "description": "Write tables, summaries, method text, and reproducibility files."},
        ],
    )
    core_outputs = {
        "erp_metrics": metrics_path,
        "erp_roi_waveform": waveform_path,
        "parameters": parameters_path,
        "erp_summary": summary_path,
        "event_confirmation": event_confirmation_path,
        "drop_log_summary": drop_log_path,
        "method_description": method_path,
        "software_versions": reproducibility_paths["software_versions"],
        "workflow": reproducibility_paths["workflow"],
        "scope_contract": scope_contract_path,
    }
    contract_paths = write_output_contract(
        output_path,
        job_type="erp_p300",
        module_name="erp",
        input_path=input_path,
        parameters=parameters,
        summary=summary,
        outputs=core_outputs,
        log_lines=[
            f"events_total={summary.get('events_total')}",
            f"epochs_total={summary.get('epochs_total')}",
            f"drop_rate={summary.get('drop_log', {}).get('drop_rate')}",
            f"conditions={list(summary.get('conditions', {}).keys())}",
            f"data_preparation_plan_id={parameters.get('data_preparation_plan_id')}",
            f"data_preparation_revision={parameters.get('data_preparation_revision')}",
        ],
    )
    return {**core_outputs, **contract_paths}


def _write_erp_waveform_svg(path: Path, evoked_by_condition: dict, roi_by_component: dict, windows: dict, reference: str) -> None:
    width, height = 760, 420
    left, right, top, bottom = 76, 34, 72, 92
    plot_w = width - left - right
    plot_h = height - top - bottom
    colors = ["#155c9c", "#b7791f", "#2b8a54", "#7c3aed"]
    series = []
    for idx, (condition, evoked) in enumerate(evoked_by_condition.items()):
        roi_channels = roi_by_component.get("P300") or roi_by_component.get(next(iter(roi_by_component), "")) or evoked.ch_names
        usable = [name for name in roi_channels if name in evoked.ch_names] or list(evoked.ch_names)
        picks = [evoked.ch_names.index(name) for name in usable]
        y_uv = evoked.data[picks].mean(axis=0) * 1e6
        series.append({"condition": condition, "times": evoked.times, "uv": y_uv, "color": colors[idx % len(colors)], "channels": usable})
    if not series:
        path.write_text(_empty_erp_svg("ERP waveform unavailable", "No evoked conditions were available for plotting."), encoding="utf-8")
        return
    x_min = min(float(np.min(item["times"])) for item in series)
    x_max = max(float(np.max(item["times"])) for item in series)
    max_abs = max(float(np.max(np.abs(item["uv"]))) for item in series) or 1.0

    def x_pos(value: float) -> float:
        return left + ((value - x_min) / ((x_max - x_min) or 1.0)) * plot_w

    def y_pos(value: float) -> float:
        return top + plot_h / 2 - (value / max_abs) * (plot_h * 0.44)

    body = [
        f'<line x1="{left}" y1="{top + plot_h / 2:.1f}" x2="{left + plot_w}" y2="{top + plot_h / 2:.1f}" stroke="#cbd5df" stroke-width="1"/>',
        f'<line x1="{x_pos(0):.1f}" y1="{top}" x2="{x_pos(0):.1f}" y2="{top + plot_h}" stroke="#94a3ad" stroke-dasharray="4 4" stroke-width="1"/>',
    ]
    for component, window in windows.items():
        start, stop = sorted([float(window[0]), float(window[1])])
        body.append(f'<rect x="{x_pos(start):.1f}" y="{top}" width="{max(1.0, x_pos(stop)-x_pos(start)):.1f}" height="{plot_h}" fill="#eaf4ff" opacity="0.28"/>')
        body.append(f'<text x="{(x_pos(start)+x_pos(stop))/2:.1f}" y="{top + 14}" text-anchor="middle" font-size="10" font-family="Arial, sans-serif" fill="#52616a">{html.escape(str(component))}</text>')
    for item in series:
        points = " ".join(f"{x_pos(float(x)):.2f},{y_pos(float(y)):.2f}" for x, y in zip(item["times"], item["uv"]))
        body.append(f'<polyline points="{points}" fill="none" stroke="{item["color"]}" stroke-width="2.2"/>')
    legend = []
    for idx, item in enumerate(series):
        y = 58 + idx * 18
        legend.append(f'<line x1="560" y1="{y}" x2="586" y2="{y}" stroke="{item["color"]}" stroke-width="2.4"/>')
        legend.append(f'<text x="592" y="{y + 4}" font-size="12" font-family="Arial, sans-serif" fill="#24343b">{html.escape(str(item["condition"]))} ROI: {html.escape(",".join(item["channels"][:4]))}</text>')
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="ERP ROI waveform">
  <rect width="{width}" height="{height}" fill="#ffffff"/>
  <text x="{width / 2:.1f}" y="28" text-anchor="middle" font-size="18" font-family="Arial, sans-serif" fill="#10242c">ERP ROI waveform</text>
  <text x="{left}" y="52" font-size="12" font-family="Arial, sans-serif" fill="#52616a">Sensor-space event-locked ERP; y-axis amplitude is microvolts (uV); reference: {html.escape(reference)}</text>
  <rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#cbd5df" stroke-width="1"/>
  {''.join(body)}
  {''.join(legend)}
  <text x="{left + plot_w / 2:.1f}" y="{height - 42}" text-anchor="middle" font-size="12" font-family="Arial, sans-serif" fill="#52616a">Time from event onset (s); shaded windows mark component measurement ranges</text>
  <text x="20" y="{top + plot_h / 2:.1f}" transform="rotate(-90 20 {top + plot_h / 2:.1f})" text-anchor="middle" font-size="12" font-family="Arial, sans-serif" fill="#52616a">Amplitude (uV)</text>
  <text x="{width / 2:.1f}" y="{height - 16}" text-anchor="middle" font-size="11" font-family="Arial, sans-serif" fill="#6b7280">Descriptive single-record ERP only; not diagnosis, source localization, causality, group statistics, or clinical evidence.</text>
</svg>
""",
        encoding="utf-8",
    )


def _empty_erp_svg(title: str, detail: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="720" height="220" viewBox="0 0 720 220" role="img" aria-label="{html.escape(title)}">
  <rect width="720" height="220" fill="#ffffff"/>
  <text x="360" y="90" text-anchor="middle" font-size="18" font-family="Arial, sans-serif" fill="#10242c">{html.escape(title)}</text>
  <text x="360" y="124" text-anchor="middle" font-size="13" font-family="Arial, sans-serif" fill="#52616a">{html.escape(detail)}</text>
</svg>
"""
