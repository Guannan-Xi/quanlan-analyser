import csv
import json
from pathlib import Path

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
    reject_uv = parameters.get("reject_eeg_uv")
    reject = {"eeg": float(reject_uv) * 1e-6} if reject_uv else None
    windows = parameters.get("components") or {
        "N100": [0.08, 0.14],
        "P200": [0.16, 0.26],
        "P300": [0.28, 0.45],
    }
    roi_by_component, missing_roi_channels = _normalize_roi_parameters(parameters, windows, eeg_channels)

    epochs = mne.Epochs(raw, events, event_id=selected, tmin=tmin, tmax=tmax, baseline=baseline_tuple, reject=reject, preload=True, verbose="ERROR")
    if len(epochs) == 0:
        raise ValueError("No ERP epochs remained after epoching/rejection")

    rows = []
    evoked_index = {}
    for condition in selected:
        evoked = epochs[condition].average()
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

    metrics_path = tables / "erp_metrics.csv"
    with metrics_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["condition", "component", "window_ms", "amplitude_uv", "latency_ms", "n_epochs", "reference", "roi_name", "roi_channels"])
        writer.writeheader()
        writer.writerows(rows)

    drop_log_summary = _summarize_drop_log(epochs)
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
        "components": windows,
        "roi_by_component": roi_by_component,
        "missing_roi_channels": missing_roi_channels,
        "conditions": evoked_index,
        "parameters": parameters,
    }
    parameters_path = reproducibility / "parameters.json"
    parameters_path.write_text(json.dumps({"input": str(input_path), "module": "erp", "parameters": parameters, "engine": "mne", "roi_by_component": roi_by_component, "event_confirmation": event_confirmation}, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path = reproducibility / "erp_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    method_path = reproducibility / "method_description.txt"
    method_path.write_text(
        "ERP analysis used MNE-Python annotations/events to epoch EEG around event markers, baseline-correct epochs, "
        "average by condition, and extract N100/P200/P300 window amplitudes and latencies from ROI-aware channel sets. "
        "Marker timing, condition semantics, reference choice, and ROI selection must be verified before interpretation.\n",
        encoding="utf-8",
    )
    reproducibility_paths = write_reproducibility_files(
        output_path,
        module_name="erp",
        input_path=input_path,
        parameters=parameters,
        workflow_steps=[
            {"name": "read_raw", "description": "Read EEG data with MNE using a format-specific reader."},
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
        "parameters": parameters_path,
        "erp_summary": summary_path,
        "event_confirmation": event_confirmation_path,
        "drop_log_summary": drop_log_path,
        "method_description": method_path,
        "software_versions": reproducibility_paths["software_versions"],
        "workflow": reproducibility_paths["workflow"],
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
        ],
    )
    return {**core_outputs, **contract_paths}
