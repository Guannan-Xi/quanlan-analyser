from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import mne
import numpy as np

from eeg_core.io.readers import read_raw
from eeg_core.report.reproducibility import (
    stable_json_hash,
    write_analysis_sidecars,
    write_output_contract,
    write_reproducibility_files,
)


MULTITAPER_PARAMETER_SCHEMA = {
    "workflow_id": {"type": "string", "default": "multitaper_psd_tfr"},
    "analysis_family": {"type": "string", "default": "psd", "enum": ["psd", "tfr"]},
    "event_id": {"type": ["string", "null"], "default": None},
    "picks": {"type": "array", "items": "string", "default": []},
    "bad_channels": {"type": "array", "items": "string", "default": []},
    "fmin": {"type": "number", "default": 1.0, "minimum": 0.0},
    "fmax": {"type": "number", "default": 40.0, "minimum": 0.0},
    "bandwidth": {"type": ["number", "null"], "default": None, "minimum": 0.0},
    "adaptive": {"type": "boolean", "default": False},
    "low_bias": {"type": "boolean", "default": True},
    "normalization": {"type": "string", "default": "length", "enum": ["length", "full"]},
    "remove_dc": {"type": "boolean", "default": True},
    "freqs": {"type": "array", "items": "number", "default": [8.0, 13.0, 30.0]},
    "n_cycles": {"type": ["number", "array"], "default": 7.0},
    "time_bandwidth": {"type": "number", "default": 4.0, "minimum": 1.0},
    "use_fft": {"type": "boolean", "default": True},
    "zero_mean": {"type": "boolean", "default": True},
    "decim": {"type": "integer", "default": 1, "minimum": 1},
    "average": {"type": "boolean", "default": True},
    "return_itc": {"type": "boolean", "default": True},
    "tmin": {"type": "number", "default": -0.2},
    "tmax": {"type": "number", "default": 0.8},
    "baseline": {"type": ["array", "null"], "items": "number", "default": [-0.2, 0.0]},
    "baseline_mode": {"type": "string", "default": "logratio", "enum": ["mean", "ratio", "logratio", "percent", "zscore", "zlogratio", "none"]},
    "n_jobs": {"type": "integer", "default": 1, "minimum": 1},
}

MULTITAPER_BOUNDARY = (
    "Multitaper PSD / TFR beta outputs are descriptive sensor-space research evidence only; "
    "not clinical diagnosis, treatment advice, source localization, group inference, or statistical significance."
)

PSD_BANDS = {
    "delta": (1.0, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma_low": (30.0, 40.0),
}


def describe_multitaper_scope() -> dict[str, Any]:
    return {
        "status": "beta_sensor_space_runner",
        "workflow_id": "multitaper_psd_tfr",
        "boundary": MULTITAPER_BOUNDARY,
    }


def run_multitaper_psd_tfr(input_path: str | Path, output_dir: str | Path, parameters: dict | None = None) -> dict[str, Path]:
    output_path = Path(output_dir)
    figures = output_path / "figures"
    tables = output_path / "tables"
    reproducibility = output_path / "reproducibility"
    for directory in (figures, tables, reproducibility):
        directory.mkdir(parents=True, exist_ok=True)

    raw = read_raw(input_path, preload=True)
    if raw.get_channel_types().count("eeg") < 1:
        raise ValueError("multitaper_psd_tfr requires at least one EEG channel")

    eeg_all = raw.copy().pick_types(eeg=True, meg=False, eog=False, ecg=False, stim=False, exclude=[])
    params = validate_multitaper_psd_tfr_parameters(
        parameters,
        channels=list(eeg_all.ch_names),
        sfreq=float(eeg_all.info["sfreq"]),
        n_times=int(eeg_all.n_times),
    )
    eeg_all.info["bads"] = sorted(set(eeg_all.info.get("bads", [])) | set(params["bad_channels"]))
    eeg = eeg_all.copy().pick_types(eeg=True, meg=False, eog=False, ecg=False, stim=False, exclude="bads")
    if not eeg.ch_names:
        raise ValueError("multitaper_psd_tfr requires at least one usable EEG channel after bad-channel exclusion")

    psd_outputs = _run_multitaper_psd(eeg, params, tables, figures)
    tfr_outputs = _run_multitaper_tfr(raw, eeg, params, tables, figures) if params["analysis_family"] == "tfr" else _write_empty_tfr_outputs(tables, figures, params)

    summary = {
        "status": "computed",
        "module_id": "multitaper_psd_tfr",
        "workflow_id": "multitaper_psd_tfr",
        "lifecycle_state": "beta",
        "analysis_family": params["analysis_family"],
        "engine": {
            "psd": "mne.Raw.compute_psd(method='multitaper')",
            "tfr": "mne.Epochs.compute_tfr(method='multitaper')",
        },
        "channels": list(eeg.ch_names),
        "sfreq": float(eeg.info["sfreq"]),
        "duration_sec": float(eeg.n_times / eeg.info["sfreq"]),
        "psd": psd_outputs["summary"],
        "tfr": tfr_outputs["summary"],
        "warnings": _collect_warnings(params, psd_outputs["summary"], tfr_outputs["summary"]),
        "boundary": MULTITAPER_BOUNDARY,
    }
    summary_path = reproducibility / "multitaper_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    params_path = reproducibility / "parameters.json"
    params_hash = stable_json_hash(params)
    recorded_params = {**params, "parameters_hash": params_hash}
    params_path.write_text(json.dumps(recorded_params, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    method_path = reproducibility / "method_description.txt"
    method_path.write_text(
        "Multitaper PSD / TFR beta computes descriptive sensor-space spectral estimates using MNE multitaper methods. "
        "PSD is generated from EEG channels with multitaper power spectra. When analysis_family=tfr, event-locked multitaper "
        "time-frequency power and optional ITC are also generated. Outputs are for research review only and do not support "
        "diagnosis, treatment guidance, source localization, group comparison, or significance claims.\n",
        encoding="utf-8",
    )

    frequency_grid_path = reproducibility / "frequency_grid.json"
    frequency_grid_path.write_text(
        json.dumps(
            {
                "freqs_hz": params["freqs"],
                "n_cycles": params["n_cycles"],
                "time_bandwidth": params["time_bandwidth"],
                "analysis_family": params["analysis_family"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    reproducibility_paths = write_reproducibility_files(
        output_path,
        module_name="multitaper_psd_tfr",
        input_path=input_path,
        parameters=recorded_params,
        workflow_steps=[
            {"name": "read_raw", "description": "Read EEG with MNE."},
            {"name": "validate", "description": "Validate spectral range, multitaper settings, and event-locked prerequisites."},
            {"name": "compute_psd", "description": "Compute multitaper PSD from EEG channels."},
            {"name": "compute_tfr", "description": "Compute event-locked multitaper TFR when analysis_family=tfr."},
            {"name": "write_outputs", "description": "Write tables, figures, summaries, and reproducibility files."},
        ],
    )

    sidecars = write_analysis_sidecars(
        output_path,
        module_name="multitaper_psd_tfr",
        parameter_schema=MULTITAPER_PARAMETER_SCHEMA,
        effective_call={
            "engine": "mne",
            "calls": {
                "psd": {
                    "call": "Raw.compute_psd",
                    "method": "multitaper",
                    "kwargs": {
                        "method": "multitaper",
                        "fmin": params["fmin"],
                        "fmax": params["fmax"],
                        "bandwidth": params["bandwidth"],
                        "adaptive": params["adaptive"],
                        "low_bias": params["low_bias"],
                        "normalization": params["normalization"],
                        "remove_dc": params["remove_dc"],
                        "n_jobs": params["n_jobs"],
                    },
                    "input_shape": {"channels": list(eeg.ch_names), "n_times": int(eeg.n_times), "sfreq": float(eeg.info["sfreq"])},
                    "output_shape": {"channels": len(eeg.ch_names), "frequencies": len(psd_outputs["freqs"])},
                },
                "tfr": tfr_outputs["effective_call"],
            },
        },
        threshold_validation=tfr_outputs["threshold_validation"] | {
            "status": "passed",
            "checks": [
                {"field": "fmin", "rule": ">= 0", "value": params["fmin"], "status": "passed"},
                {
                    "field": "fmax",
                    "rule": "< Nyquist",
                    "value": params["fmax"],
                    "nyquist_hz": float(eeg.info["sfreq"]) / 2.0,
                    "status": "passed",
                },
                {"field": "analysis_family", "rule": "supported enum", "value": params["analysis_family"], "status": "passed"},
            ],
        },
        table_dictionary=_table_dictionary(),
        scope_contract={
            "analysis_scope": "single_record_sensor_space_multitaper_beta",
            "stable_status": "beta_internal_validation",
            "allowed_claims": [
                "Describe sensor-space multitaper PSD and event-locked multitaper TFR for one recording.",
                "Export reproducibility evidence for research review and downstream report packaging.",
            ],
            "disallowed_claims": [
                "diagnosis_or_treatment_recommendation",
                "group_or_population_inference",
                "statistical_significance_claim",
                "source_localization",
                "brain_region_activation",
            ],
            "boundary": MULTITAPER_BOUNDARY,
        },
        source_metadata=_source_metadata(input_path, raw, eeg, params),
    )

    outputs = {
        "multitaper_psd_by_channel_frequency": psd_outputs["psd_long"],
        "multitaper_band_power": psd_outputs["band_power"],
        "multitaper_psd_curve": psd_outputs["psd_curve"],
        "multitaper_tfr_power_long": tfr_outputs["power_long"],
        "multitaper_tfr_itc_long": tfr_outputs["itc_long"],
        "multitaper_tfr_heatmap": tfr_outputs["heatmap"],
        "method_comparison_preview": tfr_outputs["comparison"],
        "multitaper_summary": summary_path,
        "parameters": params_path,
        "frequency_grid": frequency_grid_path,
        "method_description": method_path,
        "software_versions": reproducibility_paths["software_versions"],
        "workflow": reproducibility_paths["workflow"],
        "parameter_schema_snapshot": sidecars["parameter_schema_snapshot"],
        "threshold_validation": sidecars["threshold_validation"],
        "effective_call": sidecars["effective_call"],
        "source_metadata": sidecars["source_metadata"],
        "table_dictionary": sidecars["table_dictionary"],
        "scope_contract": sidecars["scope_contract"],
    }
    contracts = write_output_contract(
        output_path,
        job_type="multitaper_psd_tfr",
        module_name="multitaper_psd_tfr",
        input_path=input_path,
        parameters=recorded_params,
        summary=summary,
        outputs=outputs,
        log_lines=[
            f"analysis_family={params['analysis_family']}",
            f"channels={','.join(eeg.ch_names)}",
            f"freqs_hz={params['freqs']}",
            f"tfr_epoch_count={tfr_outputs['summary'].get('epoch_count', 0)}",
        ],
    )
    return {**outputs, **contracts}


def validate_multitaper_psd_tfr_parameters(parameters: dict | None, *, channels: list[str], sfreq: float, n_times: int) -> dict[str, Any]:
    source = parameters or {}
    params = dict(source)
    params.setdefault("workflow_id", "multitaper_psd_tfr")
    params["analysis_family"] = str(source.get("analysis_family") or "psd")
    if params["analysis_family"] not in {"psd", "tfr"}:
        raise ValueError("multitaper_psd_tfr analysis_family must be psd or tfr")
    params["event_id"] = source.get("event_id")
    params["picks"] = _string_list(source.get("picks"), name="picks")
    params["bad_channels"] = _string_list(source.get("bad_channels"), name="bad_channels")
    params["fmin"] = _optional_float(source.get("fmin"), default=1.0, name="fmin")
    params["fmax"] = _optional_float(source.get("fmax"), default=40.0, name="fmax")
    params["bandwidth"] = _optional_float(source.get("bandwidth"), default=None, name="bandwidth")
    params["adaptive"] = bool(source.get("adaptive", False))
    params["low_bias"] = bool(source.get("low_bias", True))
    params["normalization"] = str(source.get("normalization") or "length")
    params["remove_dc"] = bool(source.get("remove_dc", True))
    params["freqs"] = _float_list(source.get("freqs"), default=[8.0, 13.0, 30.0], name="freqs")
    params["n_cycles"] = _n_cycles_value(source.get("n_cycles"))
    params["time_bandwidth"] = _optional_float(source.get("time_bandwidth"), default=4.0, name="time_bandwidth")
    params["use_fft"] = bool(source.get("use_fft", True))
    params["zero_mean"] = bool(source.get("zero_mean", True))
    params["decim"] = _optional_int(source.get("decim"), default=1, name="decim")
    params["average"] = bool(source.get("average", True))
    params["return_itc"] = bool(source.get("return_itc", True))
    params["tmin"] = _optional_float(source.get("tmin"), default=-0.2, name="tmin")
    params["tmax"] = _optional_float(source.get("tmax"), default=0.8, name="tmax")
    params["baseline"] = _float_pair(source.get("baseline"), default=[-0.2, 0.0], name="baseline")
    params["baseline_mode"] = str(source.get("baseline_mode") or "logratio")
    params["n_jobs"] = _optional_int(source.get("n_jobs"), default=1, name="n_jobs")

    nyquist = sfreq / 2.0
    if params["fmin"] < 0:
        raise ValueError("multitaper_psd_tfr fmin must be >= 0")
    if params["fmax"] <= params["fmin"]:
        raise ValueError("multitaper_psd_tfr fmax must be greater than fmin")
    if params["fmax"] >= nyquist:
        raise ValueError(f"multitaper_psd_tfr fmax must be below Nyquist ({nyquist:g} Hz)")
    if params["bandwidth"] is not None and params["bandwidth"] <= 0:
        raise ValueError("multitaper_psd_tfr bandwidth must be positive when provided")
    if not params["freqs"]:
        raise ValueError("multitaper_psd_tfr requires at least one frequency")
    if min(params["freqs"]) <= 0:
        raise ValueError("multitaper_psd_tfr frequencies must be positive")
    if max(params["freqs"]) >= nyquist:
        raise ValueError(f"multitaper_psd_tfr frequencies must be below Nyquist ({nyquist:g} Hz)")
    if params["time_bandwidth"] < 1:
        raise ValueError("multitaper_psd_tfr time_bandwidth must be >= 1")
    if params["decim"] < 1:
        raise ValueError("multitaper_psd_tfr decim must be >= 1")
    if params["tmax"] <= params["tmin"]:
        raise ValueError("multitaper_psd_tfr tmax must be greater than tmin")
    if len(params["baseline"]) != 2 or params["baseline"][1] <= params["baseline"][0]:
        raise ValueError("multitaper_psd_tfr baseline must be a valid start/end pair")
    if params["baseline_mode"] not in {"mean", "ratio", "logratio", "percent", "zscore", "zlogratio", "none"}:
        raise ValueError("multitaper_psd_tfr baseline_mode is not supported")
    if params["normalization"] not in {"length", "full"}:
        raise ValueError("multitaper_psd_tfr normalization must be length or full")
    if params["n_cycles"] and isinstance(params["n_cycles"], list) and len(params["n_cycles"]) != len(params["freqs"]):
        raise ValueError("multitaper_psd_tfr n_cycles list must match the frequency grid")
    if params["event_id"] is not None and not isinstance(params["event_id"], str):
        params["event_id"] = str(params["event_id"])
    if any(channel not in set(channels) for channel in params["picks"]):
        missing = [channel for channel in params["picks"] if channel not in set(channels)]
        raise ValueError(f"multitaper_psd_tfr picks not found: {', '.join(missing)}")
    if any(channel not in set(channels) for channel in params["bad_channels"]):
        missing = [channel for channel in params["bad_channels"] if channel not in set(channels)]
        raise ValueError(f"multitaper_psd_tfr bad_channels not found: {', '.join(missing)}")
    if params["analysis_family"] == "tfr" and params["time_bandwidth"] <= 1:
        raise ValueError("multitaper_psd_tfr TFR time_bandwidth must be > 1")
    return params


def _run_multitaper_psd(eeg, params: dict[str, Any], tables: Path, figures: Path) -> dict[str, Any]:
    spectrum = eeg.compute_psd(
        method="multitaper",
        fmin=params["fmin"],
        fmax=params["fmax"],
        remove_dc=params["remove_dc"],
        n_jobs=params["n_jobs"],
        verbose="ERROR",
        bandwidth=params["bandwidth"],
        adaptive=params["adaptive"],
        low_bias=params["low_bias"],
        normalization=params["normalization"],
    )
    psd = spectrum.get_data()
    freqs = spectrum.freqs

    psd_long_rows = []
    for channel, values in zip(eeg.ch_names, psd):
        for frequency, value in zip(freqs, values, strict=False):
            psd_long_rows.append(
                {
                    "channel": channel,
                    "frequency_hz": round(float(frequency), 6),
                    "psd_db": round(float(10.0 * math.log10(max(float(value), np.finfo(float).tiny))), 6),
                    "unit": "db",
                }
            )

    band_rows = []
    for band, (fmin, fmax) in PSD_BANDS.items():
        band_mask = (freqs >= fmin) & (freqs < fmax)
        if not band_mask.any():
            continue
        band_values = psd[:, band_mask]
        flattened = band_values.reshape(-1)
        band_rows.append(
            {
                "band": band,
                "fmin": fmin,
                "fmax": fmax,
                "mean_psd_db": round(float(10.0 * math.log10(max(float(np.mean(flattened)), np.finfo(float).tiny))), 6),
                "median_psd_db": round(float(10.0 * math.log10(max(float(np.median(flattened)), np.finfo(float).tiny))), 6),
            }
        )

    psd_long_path = tables / "multitaper_psd_by_channel_frequency.csv"
    _write_csv(psd_long_path, psd_long_rows, ["channel", "frequency_hz", "psd_db", "unit"])
    band_power_path = tables / "multitaper_band_power.csv"
    _write_csv(band_power_path, band_rows, ["band", "fmin", "fmax", "mean_psd_db", "median_psd_db"])
    psd_curve_path = figures / "multitaper_psd_curve.svg"
    _write_line_svg(psd_curve_path, freqs.tolist(), np.mean(psd, axis=0).tolist(), "Multitaper PSD curve", "Frequency (Hz)", "Power")

    summary = {
        "status": "computed",
        "method": "multitaper",
        "channels": len(eeg.ch_names),
        "freq_bins": len(freqs),
        "freq_range_hz": [params["fmin"], params["fmax"]],
        "band_rows": band_rows,
    }
    return {
        "psd_long": psd_long_path,
        "band_power": band_power_path,
        "psd_curve": psd_curve_path,
        "freqs": [float(value) for value in freqs],
        "summary": summary,
    }


def _run_multitaper_tfr(raw, eeg, params: dict[str, Any], tables: Path, figures: Path) -> dict[str, Any]:
    event_map = _resolve_event_id(params["event_id"])
    if event_map is None:
        events, event_map = mne.events_from_annotations(raw, verbose=False)
    else:
        events, event_map = mne.events_from_annotations(raw, event_id=event_map, verbose=False)
    if events.size == 0:
        raise ValueError("multitaper_psd_tfr requires at least one event or annotation for the TFR branch")

    picks = params["picks"] or mne.pick_types(raw.info, eeg=True, meg=False, eog=False, ecg=False, stim=False, exclude="bads")
    if len(picks) == 0:
        raise ValueError("multitaper_psd_tfr TFR branch requires at least one usable EEG channel")

    epochs = mne.Epochs(
        raw,
        events,
        event_id=event_map,
        tmin=params["tmin"],
        tmax=params["tmax"],
        baseline=None,
        picks=picks,
        preload=True,
        reject_by_annotation=True,
        verbose=False,
    )
    if len(epochs) == 0:
        raise ValueError("multitaper_psd_tfr epoching produced no usable epochs")

    tfr_kwargs = {
        "method": "multitaper",
        "freqs": np.asarray(params["freqs"], dtype=float),
        "tmin": params["tmin"],
        "tmax": params["tmax"],
        "picks": list(range(len(picks))),
        "proj": False,
        "output": "power",
        "average": True,
        "return_itc": params["return_itc"],
        "decim": params["decim"],
        "n_jobs": params["n_jobs"],
        "verbose": "ERROR",
        "time_bandwidth": params["time_bandwidth"],
        "n_cycles": _n_cycles_for_compute(params["n_cycles"], len(params["freqs"])),
        "use_fft": params["use_fft"],
        "zero_mean": params["zero_mean"],
    }
    power, itc = epochs.compute_tfr(**tfr_kwargs)
    if params["baseline_mode"] != "none":
        power.apply_baseline(baseline=tuple(params["baseline"]), mode=params["baseline_mode"], verbose=False)

    power_rows = []
    for channel, channel_values in zip(power.ch_names, power.data, strict=False):
        for frequency, time_row in zip(power.freqs, channel_values, strict=False):
            for time_sec, value in zip(power.times, time_row, strict=False):
                power_rows.append(
                    {
                        "channel": channel,
                        "frequency_hz": round(float(frequency), 6),
                        "time_sec": round(float(time_sec), 6),
                        "power_value": round(float(value), 6),
                        "event_count": len(epochs),
                        "baseline": json.dumps(params["baseline"], ensure_ascii=False),
                        "unit": params["baseline_mode"] if params["baseline_mode"] != "none" else "power",
                    }
                )

    itc_rows = []
    if itc is not None:
        for channel, channel_values in zip(itc.ch_names, itc.data, strict=False):
            for frequency, time_row in zip(itc.freqs, channel_values, strict=False):
                for time_sec, value in zip(itc.times, time_row, strict=False):
                    itc_rows.append(
                        {
                            "channel": channel,
                            "frequency_hz": round(float(frequency), 6),
                            "time_sec": round(float(time_sec), 6),
                            "itc": round(float(value), 6),
                            "event_count": len(epochs),
                            "unit": "ratio",
                        }
                    )

    power_long_path = tables / "multitaper_tfr_power_long.csv"
    _write_csv(power_long_path, power_rows, ["channel", "frequency_hz", "time_sec", "power_value", "event_count", "baseline", "unit"])
    itc_long_path = tables / "multitaper_tfr_itc_long.csv"
    _write_csv(itc_long_path, itc_rows, ["channel", "frequency_hz", "time_sec", "itc", "event_count", "unit"])
    heatmap_path = figures / "multitaper_tfr_heatmap.svg"
    _write_heatmap_svg(heatmap_path, power.data, power.times.tolist(), power.freqs.tolist(), "Multitaper TFR heatmap")
    comparison_path = figures / "method_comparison_preview.svg"
    _write_text_svg(
        comparison_path,
        [
            "Multitaper PSD / TFR comparison",
            f"analysis_family={params['analysis_family']}",
            f"epochs={len(epochs)}",
            f"freqs={len(power.freqs)}",
            f"baseline_mode={params['baseline_mode']}",
        ],
    )

    summary = {
        "status": "computed",
        "epoch_count": len(epochs),
        "event_keys": sorted(set(event_map.values())) if isinstance(event_map, dict) else [],
        "freq_bins": len(power.freqs),
        "time_bins": len(power.times),
        "return_itc": params["return_itc"],
        "baseline_mode": params["baseline_mode"],
        "peak_power_value": float(np.max(power.data)) if power.data.size else None,
    }
    effective_call = {
        "call": "Epochs.compute_tfr",
        "method": "multitaper",
        "kwargs": {
            "method": "multitaper",
            "freqs": params["freqs"],
            "time_bandwidth": params["time_bandwidth"],
            "n_cycles": params["n_cycles"],
            "use_fft": params["use_fft"],
            "zero_mean": params["zero_mean"],
            "decim": params["decim"],
            "return_itc": params["return_itc"],
            "baseline_mode": params["baseline_mode"],
        },
        "input_shape": {"channels": list(epochs.ch_names), "n_epochs": len(epochs), "n_times": int(epochs.get_data().shape[-1]), "sfreq": float(raw.info["sfreq"])},
        "output_shape": {"channels": len(power.ch_names), "frequencies": len(power.freqs), "time_bins": len(power.times), "itc_available": itc is not None},
    }
    threshold_validation = {
        "status": "passed",
        "checks": [
            {"field": "events", "rule": "at least one annotation/event", "value": len(events), "status": "passed"},
            {"field": "freqs", "rule": "positive and below Nyquist", "value": len(power.freqs), "nyquist_hz": float(raw.info["sfreq"]) / 2.0, "status": "passed"},
            {"field": "time_bandwidth", "rule": "> 1", "value": params["time_bandwidth"], "status": "passed"},
        ],
    }
    return {
        "power_long": power_long_path,
        "itc_long": itc_long_path,
        "heatmap": heatmap_path,
        "comparison": comparison_path,
        "effective_call": effective_call,
        "threshold_validation": threshold_validation,
        "summary": summary,
    }


def _write_empty_tfr_outputs(tables: Path, figures: Path, params: dict[str, Any]) -> dict[str, Any]:
    power_long_path = tables / "multitaper_tfr_power_long.csv"
    _write_csv(power_long_path, [], ["channel", "frequency_hz", "time_sec", "power_value", "event_count", "baseline", "unit"])
    itc_long_path = tables / "multitaper_tfr_itc_long.csv"
    _write_csv(itc_long_path, [], ["channel", "frequency_hz", "time_sec", "itc", "event_count", "unit"])
    heatmap_path = figures / "multitaper_tfr_heatmap.svg"
    _write_text_svg(
        heatmap_path,
        [
            "Multitaper TFR not requested",
            f"analysis_family={params['analysis_family']}",
            "Select analysis_family=tfr to generate event-locked multitaper TFR outputs.",
        ],
    )
    comparison_path = figures / "method_comparison_preview.svg"
    _write_text_svg(
        comparison_path,
        [
            "Multitaper PSD / TFR comparison",
            f"analysis_family={params['analysis_family']}",
            "TFR branch not requested in this run.",
        ],
    )
    return {
        "power_long": power_long_path,
        "itc_long": itc_long_path,
        "heatmap": heatmap_path,
        "comparison": comparison_path,
        "effective_call": {
            "call": "Epochs.compute_tfr",
            "method": "multitaper",
            "kwargs": {"requested": False, "analysis_family": params["analysis_family"]},
            "input_shape": None,
            "output_shape": None,
        },
        "threshold_validation": {
            "status": "passed",
            "checks": [
                {"field": "analysis_family", "rule": "psd branch only", "value": params["analysis_family"], "status": "passed"},
            ],
        },
        "summary": {
            "status": "not_requested",
            "epoch_count": 0,
            "event_keys": [],
            "freq_bins": 0,
            "time_bins": 0,
            "return_itc": False,
            "baseline_mode": params["baseline_mode"],
            "peak_power_value": None,
        },
    }


def _collect_warnings(params: dict[str, Any], psd_summary: dict[str, Any], tfr_summary: dict[str, Any]) -> list[str]:
    warnings = [
        "Multitaper is descriptive research evidence only.",
        "Outputs do not provide diagnosis, treatment guidance, source localization, or group inference.",
    ]
    if params["analysis_family"] == "psd":
        warnings.append("TFR branch was not requested; the heatmap and comparison figure are placeholders.")
    else:
        warnings.append(f"TFR branch used {tfr_summary.get('epoch_count', 0)} epochs.")
    if len(psd_summary.get("band_rows") or []) < len(PSD_BANDS):
        warnings.append("Not all canonical PSD bands had bins in the requested frequency range.")
    return warnings


def _resolve_event_id(event_id: str | None) -> dict[str, int] | None:
    if not event_id:
        return None
    return {str(event_id): 1}


def _n_cycles_for_compute(value: Any, frequency_count: int) -> Any:
    if isinstance(value, list):
        return [float(item) for item in value]
    if isinstance(value, tuple):
        return [float(item) for item in value]
    return float(value)


def _table_dictionary() -> dict[str, dict[str, str]]:
    return {
        "tables/multitaper_psd_by_channel_frequency.csv": {key: "Multitaper PSD channel-frequency column" for key in ["channel", "frequency_hz", "psd_db", "unit"]},
        "tables/multitaper_band_power.csv": {key: "Multitaper PSD band-power column" for key in ["band", "fmin", "fmax", "mean_psd_db", "median_psd_db"]},
        "tables/multitaper_tfr_power_long.csv": {key: "Multitaper TFR power column" for key in ["channel", "frequency_hz", "time_sec", "power_value", "event_count", "baseline", "unit"]},
        "tables/multitaper_tfr_itc_long.csv": {key: "Multitaper TFR ITC column" for key in ["channel", "frequency_hz", "time_sec", "itc", "event_count", "unit"]},
    }


def _source_metadata(input_path: str | Path, raw, eeg, params: dict[str, Any]) -> dict[str, Any]:
    return {
        "input_path": str(input_path),
        "input_filename": Path(input_path).name,
        "analysis_family": params["analysis_family"],
        "channels": {
            "raw": list(raw.ch_names),
            "eeg": list(eeg.ch_names),
            "bad_channels": params["bad_channels"],
        },
        "sampling_rate_hz": float(raw.info["sfreq"]),
        "duration_sec": float(raw.n_times / raw.info["sfreq"]),
        "event_id": params["event_id"],
        "picks": params["picks"],
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def _write_line_svg(path: Path, xs: list[float], ys: list[float], title: str, x_label: str, y_label: str) -> Path:
    width, height = 860, 460
    margin = 60
    path.parent.mkdir(parents=True, exist_ok=True)
    if not xs or not ys:
        return _write_text_svg(path, [title, "No data to plot."])
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    if x_max == x_min:
        x_max = x_min + 1.0
    if y_max == y_min:
        y_max = y_min + 1.0

    def scale_x(value: float) -> float:
        return margin + (value - x_min) / (x_max - x_min) * (width - 2 * margin)

    def scale_y(value: float) -> float:
        return height - margin - (value - y_min) / (y_max - y_min) * (height - 2 * margin)

    points = " ".join(f"{scale_x(float(x)):.2f},{scale_y(float(y)):.2f}" for x, y in zip(xs, ys, strict=False))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#f8fafc"/>
  <text x="{width / 2:.1f}" y="28" text-anchor="middle" font-size="20" font-family="Arial" fill="#102a43">{_escape_svg(title)}</text>
  <line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" stroke="#94a3b8"/>
  <line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" stroke="#94a3b8"/>
  <polyline fill="none" stroke="#0f766e" stroke-width="2.5" points="{points}"/>
  <text x="{width / 2:.1f}" y="{height - 14}" text-anchor="middle" font-size="12" font-family="Arial" fill="#475569">{_escape_svg(x_label)}</text>
  <text x="18" y="{height / 2:.1f}" transform="rotate(-90 18 {height / 2:.1f})" text-anchor="middle" font-size="12" font-family="Arial" fill="#475569">{_escape_svg(y_label)}</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")
    return path


def _write_heatmap_svg(path: Path, data: np.ndarray, times: list[float], freqs: list[float], title: str) -> Path:
    width, height = 860, 460
    margin = 60
    path.parent.mkdir(parents=True, exist_ok=True)
    if data.size == 0 or not times or not freqs:
        return _write_text_svg(path, [title, "No TFR data to plot."])
    matrix = np.mean(np.asarray(data, dtype=float), axis=0)
    if matrix.ndim != 2:
        return _write_text_svg(path, [title, "Unexpected data shape."])
    freq_count, time_count = matrix.shape
    cell_w = (width - 2 * margin) / max(time_count, 1)
    cell_h = (height - 2 * margin) / max(freq_count, 1)
    max_value = float(np.max(matrix)) if np.isfinite(matrix).any() else 1.0
    min_value = float(np.min(matrix)) if np.isfinite(matrix).any() else 0.0
    if max_value == min_value:
        max_value = min_value + 1.0
    cells = []
    for row_index, row in enumerate(matrix):
        for col_index, value in enumerate(row):
            norm = (float(value) - min_value) / (max_value - min_value)
            color = _gradient_color(norm)
            x = margin + col_index * cell_w
            y = margin + row_index * cell_h
            cells.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell_w + 0.5:.2f}" height="{cell_h + 0.5:.2f}" fill="{color}" />')
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#f8fafc"/>
  <text x="{width / 2:.1f}" y="28" text-anchor="middle" font-size="20" font-family="Arial" fill="#102a43">{_escape_svg(title)}</text>
  {''.join(cells)}
  <line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" stroke="#94a3b8"/>
  <line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" stroke="#94a3b8"/>
  <text x="{width / 2:.1f}" y="{height - 14}" text-anchor="middle" font-size="12" font-family="Arial" fill="#475569">Time (s)</text>
  <text x="18" y="{height / 2:.1f}" transform="rotate(-90 18 {height / 2:.1f})" text-anchor="middle" font-size="12" font-family="Arial" fill="#475569">Frequency (Hz)</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")
    return path


def _write_text_svg(path: Path, lines: list[str]) -> Path:
    width, height = 860, max(220, 80 + 26 * len(lines))
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f'<text x="40" y="{90 + 26 * index}" font-size="18" font-family="Arial" fill="#102a43">{_escape_svg(line)}</text>' for index, line in enumerate(lines))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#f8fafc"/>
  {body}
</svg>
"""
    path.write_text(svg, encoding="utf-8")
    return path


def _escape_svg(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _gradient_color(value: float) -> str:
    value = max(0.0, min(1.0, value))
    r = int(15 + 220 * value)
    g = int(118 + 80 * (1.0 - abs(value - 0.5) * 2))
    b = int(132 + 90 * (1.0 - value))
    return f"#{r:02x}{g:02x}{b:02x}"


def _float_pair(value, *, default: list[float], name: str) -> list[float]:
    if value is None:
        return [float(default[0]), float(default[1])]
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"multitaper_psd_tfr {name} must be a two-item list")
    return [float(value[0]) if value[0] is not None else float(default[0]), float(value[1]) if value[1] is not None else float(default[1])]


def _float_list(value, *, default: list[float], name: str) -> list[float]:
    if value is None:
        return [float(item) for item in default]
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"multitaper_psd_tfr {name} must be a list")
    result = [float(item) for item in value]
    return result


def _optional_float(value, *, default: float | None, name: str) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"multitaper_psd_tfr {name} must be a number") from exc


def _optional_int(value, *, default: int, name: str) -> int:
    if value is None or value == "":
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"multitaper_psd_tfr {name} must be an integer") from exc


def _string_list(value, *, name: str) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"multitaper_psd_tfr {name} must be a list of strings")
    return [str(item) for item in value if str(item)]


def _n_cycles_value(value) -> float | list[float]:
    if value is None or value == "":
        return 7.0
    if isinstance(value, (list, tuple)):
        return [float(item) for item in value]
    return float(value)
