import csv
import html
import json
import math
from pathlib import Path
from typing import Any

import mne
import numpy as np
from mne.preprocessing import compute_current_source_density

from eeg_core.io.readers import read_raw
from eeg_core.report.reproducibility import (
    stable_json_hash,
    write_analysis_sidecars,
    write_output_contract,
    write_reproducibility_files,
)


REFERENCE_CSD_PARAMETER_SCHEMA = {
    "workflow_id": {"type": "string", "default": "reference_csd"},
    "reference_mode": {
        "type": "string",
        "default": "average",
        "enum": ["keep_original", "existing", "average", "specific_channels", "bipolar", "csd"],
    },
    "ref_channels": {"type": "array", "items": "string", "default": []},
    "bipolar_pairs": {"type": "array", "items": "object", "default": []},
    "bad_channels": {"type": "array", "items": "string", "default": []},
    "bad_segments": {"type": "array", "items": "object", "default": []},
    "csd": {
        "type": "object",
        "properties": {
            "sphere": {"type": ["string", "array"], "default": "auto"},
            "lambda2": {"type": "number", "default": 0.00001, "minimum": 0},
            "stiffness": {"type": "integer", "default": 4, "minimum": 1},
            "n_legendre_terms": {"type": "integer", "default": 50, "minimum": 1},
        },
    },
    "preview": {
        "type": "object",
        "properties": {
            "start_sec": {"type": "number", "default": 0, "minimum": 0},
            "duration_sec": {"type": "number", "default": 12, "minimum": 1, "maximum": 30},
            "channels": {"type": "array", "items": "string", "default": []},
        },
    },
}


def run_reference_csd(input_path: str | Path, output_dir: str | Path, parameters: dict | None = None) -> dict[str, Path]:
    output_path = Path(output_dir)
    figures = output_path / "figures"
    tables = output_path / "tables"
    reproducibility = output_path / "reproducibility"
    for directory in (figures, tables, reproducibility):
        directory.mkdir(parents=True, exist_ok=True)

    raw = read_raw(input_path, preload=True)
    eeg = raw.copy().pick_types(eeg=True, meg=False, eog=False, ecg=False, stim=False, exclude=[])
    if len(eeg.ch_names) < 2:
        raise ValueError("reference_csd requires at least two EEG channels")

    has_montage = _has_montage(eeg)
    params = validate_reference_csd_parameters(
        parameters,
        channels=list(eeg.ch_names),
        sfreq=float(eeg.info["sfreq"]),
        n_times=int(eeg.n_times),
        has_montage=has_montage,
    )
    _apply_bad_directives(eeg, params)
    before = eeg.copy().pick_types(eeg=True, meg=False, eog=False, ecg=False, stim=False, exclude="bads")
    if len(before.ch_names) < 2:
        raise ValueError("reference_csd requires at least two usable EEG channels after bad-channel exclusion")
    after = _apply_transform(before.copy(), params)

    reference_channels_path = tables / "reference_channels.csv"
    _write_csv(
        reference_channels_path,
        ["channel", "used_before", "used_after", "is_bad", "reference_mode"],
        _reference_rows(before, after, params, has_montage),
    )
    bipolar_pairs_path = tables / "bipolar_pairs.csv"
    _write_csv(
        bipolar_pairs_path,
        ["anode", "cathode", "ch_name", "drop_refs"],
        [
            {
                "anode": pair.get("anode", ""),
                "cathode": pair.get("cathode", ""),
                "ch_name": pair.get("ch_name", ""),
                "drop_refs": bool(pair.get("drop_refs", False)),
            }
            for pair in params["bipolar_pairs"]
        ],
    )

    preview_path = figures / "reference_before_after_preview.svg"
    _write_before_after_svg(preview_path, before, after, params, "CSD / reference transform before-after preview")
    csd_preview_path = figures / "csd_before_after_preview.svg"
    if params["reference_mode"] == "csd":
        _write_before_after_svg(csd_preview_path, before, after, params, "CSD before-after preview")
    else:
        csd_preview_path.write_text(
            _empty_svg("CSD preview not generated", "Set reference_mode=csd and provide montage/electrode positions."),
            encoding="utf-8",
        )

    summary = {
        "status": "computed",
        "module_id": "reference_csd",
        "workflow_id": "reference_csd",
        "engine": "mne",
        "reference_mode": params["reference_mode"],
        "channels_before": len(before.ch_names),
        "channels_after": len(after.ch_names),
        "sfreq": float(after.info["sfreq"]),
        "duration_sec": float(after.n_times / after.info["sfreq"]),
        "montage_status": "present" if has_montage else "missing",
        "data_preparation_plan_id": params.get("data_preparation_plan_id"),
        "data_preparation_revision": params.get("data_preparation_revision"),
        "warnings": _warnings(params, has_montage),
        "parameter_schema": REFERENCE_CSD_PARAMETER_SCHEMA,
    }
    summary_path = reproducibility / "reference_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    csd_summary_path = reproducibility / "csd_summary.json"
    csd_summary_path.write_text(
        json.dumps(
            {
                "status": "computed" if params["reference_mode"] == "csd" else "not_requested",
                "montage_status": summary["montage_status"],
                "csd_parameters": params["csd"],
                "boundary": "CSD is a scalp surface Laplacian / sensor-space spatial filter, not source localization.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    lineage_path = reproducibility / "reference_lineage.json"
    lineage_path.write_text(json.dumps(_lineage(input_path, params, raw, before, after), ensure_ascii=False, indent=2), encoding="utf-8")
    params_path = reproducibility / "parameters.json"
    params_path.write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")
    method_path = reproducibility / "method_description.txt"
    method_path.write_text(
        "CSD current source density calculation applies MNE current source density surface Laplacian "
        "when reference_mode=csd; other reference modes remain preprocessing transforms. Outputs describe "
        "sensor-space derivatives only. CSD requires electrode positions or a valid montage and must not "
        "be described as source localization, brain-region activation, diagnosis, or treatment guidance.\n",
        encoding="utf-8",
    )

    reproducibility_paths = write_reproducibility_files(
        output_path,
        module_name="reference_csd",
        input_path=input_path,
        parameters=params,
        workflow_steps=[
            {"name": "read_raw", "description": "Read EEG with MNE."},
            {"name": "validate", "description": "Validate reference mode, channels, preview window, and CSD montage prerequisites."},
            {"name": "apply_transform", "description": "Apply reference or CSD transform."},
            {"name": "write_outputs", "description": "Write figures, tables, summaries, method text, and reproducibility files."},
        ],
    )
    sidecars = write_analysis_sidecars(
        output_path,
        module_name="reference_csd",
        parameter_schema=REFERENCE_CSD_PARAMETER_SCHEMA,
        effective_call={
            "engine": "mne",
            "call": _effective_call_name(params["reference_mode"]),
            "kwargs": _effective_call_kwargs(params),
            "input_shape": {"channels": list(before.ch_names), "n_times": int(before.n_times), "sfreq": float(before.info["sfreq"])},
            "output_shape": {"channels": list(after.ch_names), "n_times": int(after.n_times), "sfreq": float(after.info["sfreq"])},
        },
        threshold_validation={
            "status": "passed",
            "checks": [
                {"field": "eeg_channels", "rule": ">= 2 usable EEG channels", "value": len(before.ch_names), "status": "passed"},
                {"field": "reference_mode", "rule": "supported enum", "value": params["reference_mode"], "status": "passed"},
                {"field": "montage", "rule": "required when reference_mode=csd", "value": has_montage, "status": "passed"},
                {"field": "preview.duration_sec", "rule": "<= 30", "value": params["preview"]["duration_sec"], "status": "passed"},
            ],
        },
        table_dictionary=_table_dictionary(),
        scope_contract={
            "analysis_scope": "single_record_sensor_space_csd_and_reference_transform",
            "stable_status": "runnable_research_workflow",
            "allowed_claims": [
                "Document and apply sensor-space EEG reference transforms.",
                "Generate before/after preview and reproducibility evidence for one uploaded recording.",
            ],
            "disallowed_claims": [
                "diagnosis_or_treatment_recommendation",
                "source_localization_or_brain_region_activation",
                "group_or_population_inference",
                "statistical_significance_claim",
            ],
            "csd_boundary": "CSD is a scalp surface Laplacian / sensor-space spatial filter, not a brain-source map.",
        },
        source_metadata=_source_metadata(input_path, raw, params, has_montage),
    )

    outputs = {
        "reference_channels": reference_channels_path,
        "bipolar_pairs": bipolar_pairs_path,
        "reference_before_after_preview": preview_path,
        "csd_before_after_preview": csd_preview_path,
        "reference_summary": summary_path,
        "csd_summary": csd_summary_path,
        "reference_lineage": lineage_path,
        "parameters": params_path,
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
        job_type="reference_csd",
        module_name="reference_csd",
        input_path=input_path,
        parameters=params,
        summary=summary,
        outputs=outputs,
        log_lines=[
            f"reference_mode={params['reference_mode']}",
            f"montage_status={summary['montage_status']}",
            f"channels_before={summary['channels_before']}",
            f"channels_after={summary['channels_after']}",
        ],
    )
    return {**outputs, **contracts}


def validate_reference_csd_parameters(
    parameters: dict | None,
    *,
    channels: list[str],
    sfreq: float,
    n_times: int,
    has_montage: bool,
) -> dict[str, Any]:
    source = parameters or {}
    params = dict(source)
    params.setdefault("workflow_id", "reference_csd")
    params.setdefault("data_preparation_plan_id", None)
    params.setdefault("data_preparation_revision", None)
    params["reference_mode"] = str(source.get("reference_mode") or "average")
    params["ref_channels"] = _string_list(source.get("ref_channels"), name="ref_channels")
    params["bipolar_pairs"] = _object_list(source.get("bipolar_pairs"), name="bipolar_pairs")
    params["bad_channels"] = _string_list(source.get("bad_channels"), name="bad_channels")
    params["bad_segments"] = _object_list(source.get("bad_segments"), name="bad_segments")

    if params["reference_mode"] not in {"keep_original", "existing", "average", "specific_channels", "bipolar", "csd"}:
        raise ValueError("reference_csd reference_mode is not supported")
    channel_set = set(channels)
    _require_channels(params["bad_channels"], channel_set, "bad_channels")
    if len([ch for ch in channels if ch not in params["bad_channels"]]) < 2:
        raise ValueError("reference_csd requires at least two usable EEG channels after bad-channel exclusion")
    if params["reference_mode"] == "specific_channels":
        if not params["ref_channels"]:
            raise ValueError("reference_csd specific_channels requires ref_channels")
        _require_channels(params["ref_channels"], channel_set, "ref_channels")
    if params["reference_mode"] == "bipolar":
        if not params["bipolar_pairs"]:
            raise ValueError("reference_csd bipolar mode requires bipolar_pairs")
        for pair in params["bipolar_pairs"]:
            anode = str(pair.get("anode") or "")
            cathode = str(pair.get("cathode") or "")
            if not anode or not cathode or anode == cathode:
                raise ValueError("reference_csd bipolar pairs require distinct anode and cathode")
            _require_channels([anode, cathode], channel_set, "bipolar_pairs")
    if params["reference_mode"] == "csd" and not has_montage:
        raise ValueError("MONTAGE_REQUIRED_FOR_CSD: CSD requires electrode positions or a valid montage")

    csd = dict(source.get("csd") or {})
    csd["sphere"] = csd.get("sphere", "auto")
    csd["lambda2"] = _optional_float(csd.get("lambda2"), default=0.00001, name="csd.lambda2")
    csd["stiffness"] = _optional_int(csd.get("stiffness"), default=4, name="csd.stiffness")
    csd["n_legendre_terms"] = _optional_int(csd.get("n_legendre_terms"), default=50, name="csd.n_legendre_terms")
    if csd["lambda2"] < 0 or csd["stiffness"] < 1 or csd["n_legendre_terms"] < 1:
        raise ValueError("reference_csd CSD parameters are out of range")
    params["csd"] = csd

    preview = dict(source.get("preview") or {})
    preview["start_sec"] = _optional_float(preview.get("start_sec"), default=0.0, name="preview.start_sec")
    preview["duration_sec"] = _optional_float(preview.get("duration_sec"), default=12.0, name="preview.duration_sec")
    preview["channels"] = _string_list(preview.get("channels"), name="preview.channels")
    if preview["start_sec"] < 0 or preview["start_sec"] >= n_times / sfreq:
        raise ValueError("reference_csd preview.start_sec is outside the recording")
    if preview["duration_sec"] <= 0 or preview["duration_sec"] > 30:
        raise ValueError("reference_csd preview.duration_sec must be within 0-30 seconds")
    _require_channels(preview["channels"], channel_set, "preview.channels")
    params["preview"] = preview
    return params


def _apply_transform(raw, params: dict[str, Any]):
    mode = params["reference_mode"]
    if mode in {"keep_original", "existing"}:
        return raw
    if mode == "average":
        raw.set_eeg_reference("average", projection=False, verbose="ERROR")
        return raw
    if mode == "specific_channels":
        raw.set_eeg_reference(ref_channels=params["ref_channels"], projection=False, verbose="ERROR")
        return raw
    if mode == "bipolar":
        for pair in params["bipolar_pairs"]:
            raw = mne.set_bipolar_reference(
                raw,
                anode=str(pair["anode"]),
                cathode=str(pair["cathode"]),
                ch_name=str(pair.get("ch_name") or f"{pair['anode']}-{pair['cathode']}"),
                drop_refs=bool(pair.get("drop_refs", False)),
                copy=False,
                verbose="ERROR",
            )
        return raw
    if mode == "csd":
        return compute_current_source_density(
            raw,
            sphere=params["csd"]["sphere"],
            lambda2=params["csd"]["lambda2"],
            stiffness=params["csd"]["stiffness"],
            n_legendre_terms=params["csd"]["n_legendre_terms"],
            copy=True,
            verbose="ERROR",
        )
    raise ValueError(f"Unsupported reference_csd mode: {mode}")


def _apply_bad_directives(raw, params: dict[str, Any]) -> None:
    raw.info["bads"] = sorted(set(raw.info.get("bads", [])) | set(params["bad_channels"]))
    segments = []
    for item in params["bad_segments"]:
        onset = _optional_float(item.get("onset", item.get("start_sec")), default=None, name="bad_segments.onset")
        duration = _optional_float(item.get("duration"), default=None, name="bad_segments.duration")
        end_sec = _optional_float(item.get("end_sec"), default=None, name="bad_segments.end_sec")
        if duration is None and onset is not None and end_sec is not None:
            duration = end_sec - onset
        if onset is None or duration is None or onset < 0 or duration <= 0:
            raise ValueError("reference_csd bad_segments require onset/start_sec and positive duration or end_sec")
        segments.append({"onset": onset, "duration": duration, "description": str(item.get("description") or "bad_reference_csd_segment")})
    if segments:
        raw.set_annotations(
            raw.annotations
            + mne.Annotations(
                onset=[item["onset"] for item in segments],
                duration=[item["duration"] for item in segments],
                description=[item["description"] for item in segments],
            )
        )


def _write_before_after_svg(path: Path, before, after, params: dict[str, Any], title: str) -> None:
    start = params["preview"]["start_sec"]
    duration = params["preview"]["duration_sec"]
    sfreq = float(before.info["sfreq"])
    start_idx = int(start * sfreq)
    stop_idx = min(int((start + duration) * sfreq), before.n_times)
    channels = params["preview"]["channels"] or before.ch_names[: min(4, len(before.ch_names))]
    channels = [channel for channel in channels if channel in before.ch_names and channel in after.ch_names][:4]
    if not channels:
        channels = before.ch_names[: min(4, len(before.ch_names))]
    before_data = before.copy().pick(channels).get_data(start=start_idx, stop=stop_idx)
    after_data = after.copy().pick([channel for channel in channels if channel in after.ch_names]).get_data(start=start_idx, stop=stop_idx)
    x_values = np.arange(before_data.shape[1]) / sfreq if before_data.size else np.array([0.0])
    body = []
    colors = ["#176b87", "#b65f2a", "#557a46", "#7a4f9a"]
    for index, channel in enumerate(channels[: after_data.shape[0]]):
        y_base = 82 + index * 54
        body.append(f'<text x="56" y="{y_base - 18}" font-size="12" fill="#24343b">{html.escape(channel)}</text>')
        body.append(f'<polyline points="{_series_points(x_values, before_data[index] * 1e6, y_base)}" fill="none" stroke="#94a3ad" stroke-width="1.5" />')
        body.append(f'<polyline points="{_series_points(x_values, after_data[index] * 1e6, y_base)}" fill="none" stroke="{colors[index % len(colors)]}" stroke-width="2" />')
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="720" height="340" viewBox="0 0 720 340" role="img" aria-label="{html.escape(title)}">
  <rect width="720" height="340" fill="#ffffff"/>
  <text x="360" y="28" text-anchor="middle" font-size="18" font-family="Arial, sans-serif" fill="#10242c">{html.escape(title)}</text>
  <text x="58" y="52" font-size="12" font-family="Arial, sans-serif" fill="#52616a">EEG sensor-space preview; y-axis amplitude is scaled per channel in microvolts (uV)</text>
  <text x="58" y="318" font-size="12" font-family="Arial, sans-serif" fill="#52616a">gray = before, color = after, x-axis time {start:g}-{start + duration:g} s, channels labelled at left</text>
  <text x="360" y="306" text-anchor="middle" font-size="12" font-family="Arial, sans-serif" fill="#52616a">Time (s)</text>
  <text x="18" y="180" transform="rotate(-90 18 180)" text-anchor="middle" font-size="12" font-family="Arial, sans-serif" fill="#52616a">Amplitude (uV, per-channel scale)</text>
  <line x1="56" y1="286" x2="664" y2="286" stroke="#b6c0c6" stroke-width="1"/>
  {''.join(body)}
</svg>
""",
        encoding="utf-8",
    )


def _series_points(x_values: np.ndarray, y_values: np.ndarray, y_base: float) -> str:
    x_span = float(np.nanmax(x_values) - np.nanmin(x_values)) or 1.0
    max_abs = float(np.nanmax(np.abs(y_values))) or 1.0
    x_min = float(np.nanmin(x_values))
    return " ".join(
        f"{80 + ((float(x) - x_min) / x_span) * 584:.2f},{y_base - (float(y) / max_abs) * 18:.2f}"
        for x, y in zip(x_values, y_values)
    )


def _empty_svg(title: str, detail: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="720" height="220" viewBox="0 0 720 220" role="img" aria-label="{html.escape(title)}">
  <rect width="720" height="220" fill="#ffffff"/>
  <text x="360" y="90" text-anchor="middle" font-size="18" font-family="Arial, sans-serif" fill="#10242c">{html.escape(title)}</text>
  <text x="360" y="124" text-anchor="middle" font-size="13" font-family="Arial, sans-serif" fill="#52616a">{html.escape(detail)}</text>
  <text x="360" y="150" text-anchor="middle" font-size="12" font-family="Arial, sans-serif" fill="#52616a">Sensor-space reference/CSD context; no source localization, diagnosis, or clinical interpretation.</text>
  <text x="360" y="174" text-anchor="middle" font-size="12" font-family="Arial, sans-serif" fill="#52616a">Expected axes when generated: Time (s) and Amplitude (uV) by EEG channel.</text>
</svg>
"""


def _has_montage(raw) -> bool:
    montage = raw.get_montage()
    if montage is None:
        return False
    positions = montage.get_positions().get("ch_pos") or {}
    return any(channel in positions for channel in raw.ch_names)


def _reference_rows(before, after, params: dict[str, Any], has_montage: bool) -> list[dict[str, Any]]:
    after_channels = set(after.ch_names)
    rows = [
        {
            "channel": channel,
            "used_before": True,
            "used_after": channel in after_channels,
            "is_bad": channel in set(params["bad_channels"]),
            "reference_mode": params["reference_mode"],
        }
        for channel in before.ch_names
    ]
    rows.append({"channel": "_montage_status", "used_before": has_montage, "used_after": has_montage, "is_bad": False, "reference_mode": params["reference_mode"]})
    return rows


def _warnings(params: dict[str, Any], has_montage: bool) -> list[dict[str, str]]:
    warnings = [{"name": "boundary", "detail": "Reference/CSD outputs are sensor-space research preprocessing evidence, not diagnosis or source localization."}]
    if params["reference_mode"] != "csd":
        warnings.append({"name": "csd_not_requested", "detail": "CSD figure is a placeholder because reference_mode is not csd."})
    if not has_montage:
        warnings.append({"name": "montage_missing", "detail": "CSD requires montage/electrode positions."})
    return warnings


def _lineage(input_path: str | Path, params: dict[str, Any], raw, before, after) -> dict[str, Any]:
    return {
        "input_file": str(input_path),
        "parameters_hash": stable_json_hash(params),
        "data_preparation_plan_id": params.get("data_preparation_plan_id"),
        "data_preparation_revision": params.get("data_preparation_revision"),
        "original_channels": list(raw.ch_names),
        "usable_channels_before_transform": list(before.ch_names),
        "channels_after_transform": list(after.ch_names),
        "boundary": "Derivative reference/CSD artifact; original EEG file is not rewritten.",
    }


def _source_metadata(input_path: str | Path, raw, params: dict[str, Any], has_montage: bool) -> dict[str, Any]:
    path = Path(input_path)
    return {
        "source_file": {
            "filename": path.name,
            "suffix": path.suffix.lower(),
            "size_bytes": path.stat().st_size if path.exists() else None,
            "sha256": _sha256_file(path) if path.exists() and path.is_file() else None,
        },
        "recording_metadata": {
            "sfreq_hz": float(raw.info["sfreq"]),
            "n_times": int(raw.n_times),
            "duration_sec": float(raw.n_times / raw.info["sfreq"]),
            "channel_names": list(raw.ch_names),
            "eeg_channel_count": int(raw.get_channel_types().count("eeg")),
            "has_montage": has_montage,
        },
        "parameters_hash": stable_json_hash(params),
    }


def _table_dictionary() -> dict[str, Any]:
    return {
        "tables/reference_channels.csv": {
            "description": "Channel-level record before and after the reference/CSD transform.",
            "primary_key": ["channel"],
        },
        "tables/bipolar_pairs.csv": {
            "description": "Configured bipolar reference pairs, empty when not using bipolar mode.",
            "primary_key": ["ch_name"],
        },
    }


def _effective_call_name(mode: str) -> str:
    if mode == "csd":
        return "mne.preprocessing.compute_current_source_density"
    if mode == "bipolar":
        return "mne.set_bipolar_reference"
    return "Raw.set_eeg_reference"


def _effective_call_kwargs(params: dict[str, Any]) -> dict[str, Any]:
    if params["reference_mode"] == "csd":
        return dict(params["csd"])
    if params["reference_mode"] == "bipolar":
        return {"bipolar_pairs": params["bipolar_pairs"]}
    if params["reference_mode"] == "specific_channels":
        return {"ref_channels": params["ref_channels"], "projection": False}
    if params["reference_mode"] == "average":
        return {"ref_channels": "average", "projection": False}
    return {"reference_mode": params["reference_mode"]}


def _require_channels(values: list[str], channel_set: set[str], name: str) -> None:
    missing = [value for value in values if value not in channel_set]
    if missing:
        raise ValueError(f"reference_csd {name} not found: {', '.join(missing)}")


def _sha256_file(path: Path) -> str:
    digest = __import__("hashlib").sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _optional_float(value, *, default: float | None, name: str) -> float | None:
    if value is None or value == "":
        return default
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"reference_csd {name} must be a number") from exc
    if not math.isfinite(result):
        raise ValueError(f"reference_csd {name} must be finite")
    return result


def _optional_int(value, *, default: int | None, name: str) -> int | None:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise ValueError(f"reference_csd {name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"reference_csd {name} must be an integer") from exc


def _string_list(value, *, name: str) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"reference_csd {name} must be a list of strings")
    return value


def _object_list(value, *, name: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"reference_csd {name} must be a list of objects")
    return value
