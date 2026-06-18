import csv
import json
from pathlib import Path

import numpy as np

from eeg_core.io.readers import read_raw
from eeg_core.report.reproducibility import write_output_contract, write_reproducibility_files


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

    epochs = mne.Epochs(raw, events, event_id=selected, tmin=tmin, tmax=tmax, baseline=baseline_tuple, reject=reject, preload=True, verbose="ERROR")
    if len(epochs) == 0:
        raise ValueError("No ERP epochs remained after epoching/rejection")

    windows = parameters.get("components") or {
        "N100": [0.08, 0.14],
        "P200": [0.16, 0.26],
        "P300": [0.28, 0.45],
    }
    picks = mne.pick_types(epochs.info, eeg=True, meg=False, eog=False, ecg=False, stim=False, exclude="bads")
    if len(picks) == 0:
        raise ValueError("No EEG channels available for ERP metrics")

    rows = []
    evoked_index = {}
    for condition in selected:
        evoked = epochs[condition].average()
        evoked_index[condition] = {"n_epochs": int(len(epochs[condition])), "channels": list(evoked.ch_names)}
        for component, window in windows.items():
            start, stop = float(window[0]), float(window[1])
            mask = (evoked.times >= start) & (evoked.times <= stop)
            if not mask.any():
                continue
            data_uv = evoked.data[picks][:, mask] * 1e6
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
            })

    if not rows:
        raise ValueError("ERP metrics could not be computed for the requested component windows")

    metrics_path = tables / "erp_metrics.csv"
    with metrics_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["condition", "component", "window_ms", "amplitude_uv", "latency_ms", "n_epochs"])
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "status": "computed",
        "engine": "mne",
        "event_id": selected,
        "events_total": int(len(events)),
        "epochs_total": int(len(epochs)),
        "tmin": tmin,
        "tmax": tmax,
        "baseline": baseline,
        "components": windows,
        "conditions": evoked_index,
        "parameters": parameters,
    }
    parameters_path = reproducibility / "parameters.json"
    parameters_path.write_text(json.dumps({"input": str(input_path), "module": "erp", "parameters": parameters, "engine": "mne"}, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path = reproducibility / "erp_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    method_path = reproducibility / "method_description.txt"
    method_path.write_text(
        "ERP analysis used MNE-Python annotations/events to epoch EEG around event markers, baseline-correct epochs, "
        "average by condition, and extract N100/P200/P300 window amplitudes and latencies. Marker timing and condition semantics must be verified before interpretation.\n",
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
            {"name": "filter_reference", "description": "Apply band-pass filter and re-reference (default average)."},
            {"name": "epoch", "description": "Epoch around event markers with baseline correction and optional amplitude rejection."},
            {"name": "evoked", "description": "Average epochs per condition to compute evoked responses."},
            {"name": "component_metrics", "description": "Extract windowed component peak amplitude and latency."},
            {"name": "write_outputs", "description": "Write tables, summaries, method text, and reproducibility files."},
        ],
    )
    core_outputs = {
        "erp_metrics": metrics_path,
        "parameters": parameters_path,
        "erp_summary": summary_path,
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
            f"conditions={list(summary.get('conditions', {}).keys())}",
        ],
    )
    return {**core_outputs, **contract_paths}
