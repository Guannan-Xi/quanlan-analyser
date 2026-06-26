import csv
import html
import json
import math
from pathlib import Path
from typing import Any

import mne
import numpy as np

from eeg_core.io.readers import read_raw
from eeg_core.report.reproducibility import stable_json_hash, write_analysis_sidecars, write_output_contract, write_reproducibility_files


CONNECTIVITY_PARAMETER_SCHEMA = {
    "workflow_id": {"type": "string", "default": "connectivity"},
    "method": {"type": "string", "default": "correlation", "enum": ["correlation", "coherence"]},
    "fmin": {"type": "number", "default": 8.0, "minimum": 0.0},
    "fmax": {"type": "number", "default": 12.0, "minimum": 0.0},
    "segment_length_sec": {"type": "number", "default": 4.0, "minimum": 1.0},
    "reference": {"type": "string", "default": "current_recording"},
    "bad_channels": {"type": "array", "items": "string", "default": []},
    "edge_top_n": {"type": "integer", "default": 20, "minimum": 1},
}


def describe_connectivity_scope() -> dict:
    return {
        "status": "beta_sensor_space_runner",
        "methods": ["correlation", "coherence"],
        "boundary": "Single-record sensor-space association/synchrony only; not causality or brain-region communication.",
    }


def run_connectivity(input_path: str | Path, output_dir: str | Path, parameters: dict | None = None) -> dict[str, Path]:
    output_path = Path(output_dir)
    figures = output_path / "figures"
    tables = output_path / "tables"
    reproducibility = output_path / "reproducibility"
    for directory in (figures, tables, reproducibility):
        directory.mkdir(parents=True, exist_ok=True)

    raw = read_raw(input_path, preload=True)
    if raw.get_channel_types().count("eeg") < 2:
        raise ValueError("connectivity requires at least two EEG channels")
    eeg_all = raw.copy().pick_types(eeg=True, meg=False, eog=False, ecg=False, stim=False, exclude=[])
    params = validate_connectivity_parameters(parameters, channels=list(eeg_all.ch_names), sfreq=float(eeg_all.info["sfreq"]), n_times=int(eeg_all.n_times))
    eeg_all.info["bads"] = sorted(set(eeg_all.info.get("bads", [])) | set(params["bad_channels"]))
    eeg = eeg_all.copy().pick_types(eeg=True, meg=False, eog=False, ecg=False, stim=False, exclude="bads")
    if len(eeg.ch_names) < 2:
        raise ValueError("connectivity requires at least two usable EEG channels after bad-channel exclusion")

    data = eeg.get_data(reject_by_annotation="omit")
    matrix = _compute_matrix(data, float(eeg.info["sfreq"]), params)
    edges = _edge_rows(eeg.ch_names, matrix, params["edge_top_n"])

    matrix_path = tables / "connectivity_matrix.csv"
    _write_matrix_csv(matrix_path, eeg.ch_names, matrix)
    edges_path = tables / "connectivity_edges_long.csv"
    _write_csv(edges_path, ["source", "target", "value", "rank", "method", "fmin", "fmax"], edges)
    matrix_svg_path = figures / "connectivity_matrix.svg"
    _write_matrix_svg(matrix_svg_path, eeg.ch_names, matrix, params)
    network_svg_path = figures / "connectivity_sensor_network.svg"
    _write_network_svg(network_svg_path, eeg.ch_names, matrix, params)

    segment_count = int(data.shape[1] // max(int(params["segment_length_sec"] * eeg.info["sfreq"]), 1))
    warnings = _warnings(params, segment_count)
    summary = {
        "status": "computed",
        "module_id": "connectivity",
        "workflow_id": "connectivity",
        "lifecycle_state": "runnable_research_method",
        "engine": "numpy",
        "method": params["method"],
        "channels": len(eeg.ch_names),
        "sfreq": float(eeg.info["sfreq"]),
        "duration_sec": float(eeg.n_times / eeg.info["sfreq"]),
        "freq_range_hz": [params["fmin"], params["fmax"]],
        "segment_length_sec": params["segment_length_sec"],
        "segment_count": segment_count,
        "edge_count": len(edges),
        "warnings": warnings,
        "parameter_schema": CONNECTIVITY_PARAMETER_SCHEMA,
    }
    summary_path = reproducibility / "connectivity_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    params_path = reproducibility / "parameters.json"
    params_path.write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")
    method_path = reproducibility / "method_description.txt"
    method_path.write_text(
        "Connectivity analysis computes a single-record channel-by-channel association/synchrony matrix. "
        "The correlation method uses Pearson correlation of EEG channel signals. The coherence method uses a "
        "simple FFT cross-spectrum ratio averaged in the selected frequency band. Results are sensor-space "
        "descriptive outputs only and must not be interpreted as causality, source localization, brain-region "
        "communication, diagnosis, or group statistics.\n",
        encoding="utf-8",
    )
    reproducibility_paths = write_reproducibility_files(
        output_path,
        module_name="connectivity",
        input_path=input_path,
        parameters=params,
        workflow_steps=[
            {"name": "read_raw", "description": "Read EEG with MNE."},
            {"name": "validate", "description": "Validate channels, frequency range, segment length, and method."},
            {"name": "compute_matrix", "description": "Compute sensor-space connectivity matrix."},
            {"name": "write_outputs", "description": "Write matrix, edge table, figures, summaries, and reproducibility files."},
        ],
    )
    sidecars = write_analysis_sidecars(
        output_path,
        module_name="connectivity",
        parameter_schema=CONNECTIVITY_PARAMETER_SCHEMA,
        effective_call={
            "engine": "numpy",
            "call": "corrcoef" if params["method"] == "correlation" else "fft_cross_spectrum_coherence",
            "kwargs": {"method": params["method"], "fmin": params["fmin"], "fmax": params["fmax"]},
            "input_shape": {"channels": list(eeg.ch_names), "n_times": int(eeg.n_times), "sfreq": float(eeg.info["sfreq"])},
            "output_shape": {"matrix": [len(eeg.ch_names), len(eeg.ch_names)], "edges": len(edges)},
        },
        threshold_validation={
            "status": "passed",
            "checks": [
                {"field": "eeg_channels", "rule": ">= 2 usable EEG channels", "value": len(eeg.ch_names), "status": "passed"},
                {"field": "fmax", "rule": "< Nyquist", "value": params["fmax"], "nyquist_hz": float(eeg.info["sfreq"]) / 2.0, "status": "passed"},
                {"field": "segment_count", "rule": "reported, warning if < 3", "value": segment_count, "status": "passed"},
            ],
        },
        table_dictionary=_table_dictionary(),
        scope_contract={
            "analysis_scope": "single_record_sensor_space_connectivity_beta",
            "stable_status": "beta_internal_validation",
            "allowed_claims": [
                "Describe channel-level sensor-space association or synchrony for one recording.",
                "Export a matrix and ranked edge table for downstream review.",
            ],
            "disallowed_claims": [
                "causality",
                "diagnosis_or_treatment_recommendation",
                "brain_region_communication",
                "source_localization",
                "group_or_population_inference",
                "statistical_significance_claim",
            ],
        },
        source_metadata=_source_metadata(input_path, raw, eeg, params),
    )

    outputs = {
        "connectivity_matrix": matrix_path,
        "connectivity_edges_long": edges_path,
        "connectivity_matrix_figure": matrix_svg_path,
        "connectivity_sensor_network": network_svg_path,
        "connectivity_summary": summary_path,
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
        job_type="connectivity_beta",
        module_name="connectivity",
        input_path=input_path,
        parameters=params,
        summary=summary,
        outputs=outputs,
        log_lines=[
            f"method={params['method']}",
            f"freq_range_hz={[params['fmin'], params['fmax']]}",
            f"channels={len(eeg.ch_names)}",
            f"segment_count={segment_count}",
        ],
    )
    return {**outputs, **contracts}


def validate_connectivity_parameters(parameters: dict | None, *, channels: list[str], sfreq: float, n_times: int) -> dict[str, Any]:
    source = parameters or {}
    params = dict(source)
    params.setdefault("workflow_id", "connectivity")
    params["method"] = str(source.get("method") or "correlation")
    params["fmin"] = _optional_float(source.get("fmin"), default=8.0, name="fmin")
    params["fmax"] = _optional_float(source.get("fmax"), default=12.0, name="fmax")
    params["segment_length_sec"] = _optional_float(source.get("segment_length_sec"), default=4.0, name="segment_length_sec")
    params["reference"] = str(source.get("reference") or "current_recording")
    params["bad_channels"] = _string_list(source.get("bad_channels"), name="bad_channels")
    params["edge_top_n"] = _optional_int(source.get("edge_top_n"), default=20, name="edge_top_n")
    if params["method"] not in {"correlation", "coherence"}:
        raise ValueError("connectivity method must be correlation or coherence")
    nyquist = sfreq / 2.0
    if params["fmin"] < 0 or params["fmax"] <= params["fmin"] or params["fmax"] >= nyquist:
        raise ValueError(f"connectivity frequency range must satisfy 0 <= fmin < fmax < Nyquist ({nyquist:g} Hz)")
    if params["segment_length_sec"] < 1 or params["segment_length_sec"] > n_times / sfreq:
        raise ValueError("connectivity segment_length_sec must fit within the recording")
    if params["edge_top_n"] < 1:
        raise ValueError("connectivity edge_top_n must be >= 1")
    missing = [channel for channel in params["bad_channels"] if channel not in set(channels)]
    if missing:
        raise ValueError(f"connectivity bad channels not found: {', '.join(missing)}")
    return params


def _compute_matrix(data: np.ndarray, sfreq: float, params: dict[str, Any]) -> np.ndarray:
    if params["method"] == "correlation":
        matrix = np.corrcoef(data)
        return np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
    return _coherence_matrix(data, sfreq, params["fmin"], params["fmax"], params["segment_length_sec"])


def _coherence_matrix(data: np.ndarray, sfreq: float, fmin: float, fmax: float, segment_length_sec: float) -> np.ndarray:
    segment_len = max(int(segment_length_sec * sfreq), 2)
    n_segments = max(data.shape[1] // segment_len, 1)
    trimmed = data[:, : n_segments * segment_len]
    segments = trimmed.reshape(data.shape[0], n_segments, segment_len)
    window = np.hanning(segment_len)
    freqs = np.fft.rfftfreq(segment_len, d=1.0 / sfreq)
    mask = (freqs >= fmin) & (freqs <= fmax)
    if not mask.any():
        raise ValueError("connectivity selected frequency range has no FFT bins")
    spectra = np.fft.rfft(segments * window, axis=2)[:, :, mask]
    n_channels = data.shape[0]
    matrix = np.eye(n_channels)
    for i in range(n_channels):
        for j in range(i + 1, n_channels):
            sxy = np.mean(spectra[i] * np.conj(spectra[j]))
            sxx = np.mean(np.abs(spectra[i]) ** 2)
            syy = np.mean(np.abs(spectra[j]) ** 2)
            value = float(np.abs(sxy) ** 2 / max(float(sxx * syy), np.finfo(float).eps))
            value = max(0.0, min(1.0, value))
            matrix[i, j] = matrix[j, i] = value
    return matrix


def _edge_rows(channels: list[str], matrix: np.ndarray, edge_top_n: int) -> list[dict[str, Any]]:
    rows = []
    for i, source in enumerate(channels):
        for j, target in enumerate(channels):
            if j <= i:
                continue
            rows.append({"source": source, "target": target, "value": float(matrix[i, j])})
    rows.sort(key=lambda row: abs(float(row["value"])), reverse=True)
    selected = rows[:edge_top_n]
    for rank, row in enumerate(selected, start=1):
        row["rank"] = rank
    return selected


def _write_matrix_csv(path: Path, channels: list[str], matrix: np.ndarray) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["channel", *channels])
        for channel, row in zip(channels, matrix):
            writer.writerow([channel, *[float(value) for value in row]])


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_matrix_svg(path: Path, channels: list[str], matrix: np.ndarray, params: dict[str, Any]) -> None:
    size = 34
    left = 128
    top = 56
    width = left + len(channels) * size + 32
    height = top + len(channels) * size + 92
    max_abs = float(np.max(np.abs(matrix))) or 1.0
    cells = []
    for row_index, source in enumerate(channels):
        cells.append(f'<text x="{left - 8}" y="{top + row_index * size + 22}" text-anchor="end" font-size="11">{html.escape(source)}</text>')
        for col_index, target in enumerate(channels):
            if row_index == 0:
                cells.append(f'<text x="{left + col_index * size + 17}" y="{top - 8}" text-anchor="middle" font-size="11">{html.escape(target)}</text>')
            value = float(matrix[row_index, col_index])
            color = _cell_color(value, max_abs)
            cells.append(f'<rect x="{left + col_index * size}" y="{top + row_index * size}" width="{size}" height="{size}" fill="{color}" stroke="#ffffff" stroke-width="1"/>')
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Connectivity matrix">
  <rect width="{width}" height="{height}" fill="#ffffff"/>
  <text x="{width / 2:.1f}" y="26" text-anchor="middle" font-size="18" font-family="Arial, sans-serif" fill="#10242c">Sensor connectivity matrix</text>
  <text x="{width / 2:.1f}" y="{height - 28}" text-anchor="middle" font-size="12" font-family="Arial, sans-serif" fill="#52616a">{html.escape(params['method'])}, {params['fmin']:g}-{params['fmax']:g} Hz; sensor-space association only</text>
  {''.join(cells)}
</svg>
""",
        encoding="utf-8",
    )


def _write_network_svg(path: Path, channels: list[str], matrix: np.ndarray, params: dict[str, Any]) -> None:
    width, height = 720, 420
    cx, cy, radius = 360, 210, 138
    positions = {}
    for index, channel in enumerate(channels):
        angle = -math.pi / 2 + index * 2 * math.pi / len(channels)
        positions[channel] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
    edges = _edge_rows(channels, matrix, min(params["edge_top_n"], 24))
    max_abs = max([abs(float(edge["value"])) for edge in edges] or [1.0])
    body = []
    for edge in edges:
        x1, y1 = positions[edge["source"]]
        x2, y2 = positions[edge["target"]]
        opacity = 0.2 + 0.7 * abs(float(edge["value"])) / max_abs
        body.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#176b87" stroke-width="2" opacity="{opacity:.2f}"/>')
    for channel, (x, y) in positions.items():
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="14" fill="#ffffff" stroke="#24343b" stroke-width="1.5"/>')
        body.append(f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" font-size="10" fill="#24343b">{html.escape(channel)}</text>')
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Connectivity sensor network">
  <rect width="{width}" height="{height}" fill="#ffffff"/>
  <text x="360" y="32" text-anchor="middle" font-size="18" font-family="Arial, sans-serif" fill="#10242c">Top sensor associations</text>
  <text x="360" y="392" text-anchor="middle" font-size="12" font-family="Arial, sans-serif" fill="#52616a">Edges are descriptive sensor-space associations; not causality or source localization.</text>
  {''.join(body)}
</svg>
""",
        encoding="utf-8",
    )


def _cell_color(value: float, max_abs: float) -> str:
    scale = abs(value) / max_abs
    blue = int(245 - 115 * scale)
    green = int(247 - 55 * scale)
    red = int(250 - 210 * scale)
    return f"rgb({red},{green},{blue})"


def _warnings(params: dict[str, Any], segment_count: int) -> list[dict[str, str]]:
    warnings = [
        {"name": "boundary", "detail": "Connectivity is sensor-space association/synchrony, not causality or brain-region communication."},
        {"name": "single_record", "detail": "This beta output describes one recording only and does not include group statistics."},
    ]
    if segment_count < 3:
        warnings.append({"name": "few_segments", "detail": "Segment count is low; interpret connectivity cautiously."})
    if params["reference"] == "current_recording":
        warnings.append({"name": "reference_context", "detail": "The current recording reference is used; reference changes can alter sensor connectivity."})
    return warnings


def _table_dictionary() -> dict[str, Any]:
    return {
        "tables/connectivity_matrix.csv": {"description": "Square channel-by-channel connectivity matrix.", "primary_key": ["channel"]},
        "tables/connectivity_edges_long.csv": {"description": "Ranked upper-triangle channel pairs.", "primary_key": ["rank"]},
    }


def _source_metadata(input_path: str | Path, raw, eeg, params: dict[str, Any]) -> dict[str, Any]:
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
            "used_eeg_channels": list(eeg.ch_names),
        },
        "parameters_hash": stable_json_hash(params),
    }


def _sha256_file(path: Path) -> str:
    digest = __import__("hashlib").sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _optional_float(value, *, default: float | None, name: str) -> float | None:
    if value is None or value == "":
        return default
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"connectivity {name} must be a number") from exc
    if not math.isfinite(result):
        raise ValueError(f"connectivity {name} must be finite")
    return result


def _optional_int(value, *, default: int | None, name: str) -> int:
    if value is None or value == "":
        return int(default)
    if isinstance(value, bool):
        raise ValueError(f"connectivity {name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"connectivity {name} must be an integer") from exc


def _string_list(value, *, name: str) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"connectivity {name} must be a list of strings")
    return value
