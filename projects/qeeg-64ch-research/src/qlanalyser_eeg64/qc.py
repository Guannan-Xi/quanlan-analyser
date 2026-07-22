"""Automated, auditable EEG quality-control and denoising workflow.

The workflow is intentionally conservative: absent ICLabel or spatial geometry
blocks automatic approval instead of claiming that artifacts were removed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import mne
import numpy as np

from .preprocess import PreprocessConfig, preprocess_full_recording


@dataclass(frozen=True)
class QCConfig:
    epoch_sec: float = 1.0
    absolute_amplitude_uv: float = 250.0
    flat_std_uv: float = 0.5
    robust_z_limit: float = 5.0
    maximum_bad_channel_fraction: float = 0.15
    minimum_retained_epochs: int = 20
    residual_peak_to_peak_uv: float = 200.0
    ica_variance_fraction: float = 0.99
    ica_random_state: int = 42
    eye_heart_probability: float = 0.90
    other_artifact_probability: float = 0.95
    maximum_ica_exclusion_fraction: float = 0.15


def run_auto_qc(raw, config: QCConfig | None = None) -> tuple[mne.io.BaseRaw, dict[str, Any]]:
    """Run automatic QC on the complete record and return clean retained samples.

    The returned raw has rejected epochs omitted. A non-pass safety gate means
    results remain available for review but must not be labelled auto-approved.
    """
    config = config or QCConfig()
    scalp = raw.copy().pick("eeg")
    candidate_bads = _candidate_bad_channels(scalp, config)
    can_interpolate = bool(candidate_bads) and all(np.isfinite(scalp._get_channel_positions()[:, :2]).any(axis=1))
    if candidate_bads and can_interpolate:
        scalp.info["bads"] = candidate_bads
        scalp.interpolate_bads(reset_bads=False, verbose="ERROR")
    processed, trace = preprocess_full_recording(scalp, PreprocessConfig(bad_channels=tuple(candidate_bads)))
    ica_result = _remove_iclabel_components(processed, config)
    cleaned = ica_result.pop("raw")
    epoch_data, epoch_rows = _screen_epochs(cleaned, config)
    # Keep only complete one-second epochs that passed the deterministic screen.
    keep = np.array([row["retained"] for row in epoch_rows], dtype=bool)
    if keep.any():
        retained_data = epoch_data[keep].transpose(1, 0, 2).reshape(len(cleaned.ch_names), -1)
        concatenated = mne.io.RawArray(retained_data, cleaned.info.copy(), verbose="ERROR")
    else:
        concatenated = cleaned.copy().crop(tmin=0, tmax=0, include_tmax=False)
    source_epoch_rows = _add_analysis_coordinates(
        epoch_rows,
        source_sampling_rate_hz=float(raw.info["sfreq"]),
    )
    source_time_mapping = build_source_time_mapping(
        source_epoch_rows,
        source_duration_sec=float(raw.n_times / raw.info["sfreq"]),
        source_sampling_rate_hz=float(raw.info["sfreq"]),
        screened_sampling_rate_hz=float(cleaned.info["sfreq"]),
        source_sample_count=int(raw.n_times),
        screened_sample_count=int(cleaned.n_times),
        analysis_sample_count=int(concatenated.n_times),
    )
    gate_reasons = _gate_reasons(config, candidate_bads, len(scalp.ch_names), can_interpolate, ica_result, epoch_rows)
    safety_gate = "AUTO_PASS" if not gate_reasons else "AUTO_PASS_BLOCKED"
    summary = {"config": asdict(config), "source_duration_sec": float(raw.n_times / raw.info["sfreq"]), "analysis_duration_sec": float(concatenated.n_times / concatenated.info["sfreq"]), "channel_count": len(scalp.ch_names), "candidate_bad_channels": candidate_bads, "interpolated_channels": candidate_bads if can_interpolate else [], "preprocessing": trace, "ica": ica_result, "epochs": source_epoch_rows, "source_epoch_rows": source_epoch_rows, "source_time_mapping": source_time_mapping, "epoch_summary": {"total": len(epoch_rows), "retained": int(keep.sum()), "rejected": int((~keep).sum()), "retention_percent": float(100 * keep.mean()) if keep.size else 0.0}, "residual_artifact_epochs": int(sum(row["residual_artifact"] for row in epoch_rows if row["retained"])), "safety_gate": {"conclusion": safety_gate, "reasons": gate_reasons}}
    return concatenated, summary


def _candidate_bad_channels(raw, config):
    data = raw.get_data() * 1e6
    score = np.log(np.maximum(np.std(data, axis=1), np.finfo(float).eps))
    median = np.median(score)
    mad = np.median(np.abs(score - median))
    z = 0.6745 * (score - median) / max(mad, np.finfo(float).eps)
    flat = np.std(data, axis=1) < config.flat_std_uv
    return [name for name, value, is_flat in zip(raw.ch_names, z, flat) if abs(value) > config.robust_z_limit or is_flat]


def _remove_iclabel_components(raw, config):
    try:
        from mne_icalabel import label_components
    except ImportError:
        return {"raw": raw, "status": "blocked_missing_dependency", "component_count": 0, "excluded_components": [], "labels": [], "reason": "Install mne-icalabel to classify ICA components automatically."}
    ica_raw = raw.copy().filter(1.0, min(100.0, raw.info["sfreq"] / 2 - 1), verbose="ERROR")
    ica = mne.preprocessing.ICA(n_components=config.ica_variance_fraction, method="infomax", fit_params={"extended": True}, random_state=config.ica_random_state, max_iter="auto")
    try:
        ica.fit(ica_raw, verbose="ERROR")
    except RuntimeError as exc:
        return {
            "raw": raw,
            "status": "blocked_ica_fit",
            "component_count": 0,
            "excluded_components": [],
            "labels": [],
            "reason": f"Extended Infomax ICA could not be fit with the configured variance threshold: {exc}",
        }
    try:
        classified = label_components(ica_raw, ica, method="iclabel")
    except (RuntimeError, ValueError) as exc:
        # ICLabel requires electrode locations and may reject non-standard
        # recordings. Preserve the data and explicitly block auto-approval.
        return {
            "raw": raw,
            "status": "blocked_classification_unavailable",
            "component_count": int(ica.n_components_),
            "excluded_components": [],
            "labels": [],
            "reason": f"ICLabel classification could not be completed: {exc}",
        }
    labels = classified["labels"]
    probabilities = np.asarray(classified["y_pred_proba"])
    excluded = []
    rows = []
    for component, (label, probs) in enumerate(zip(labels, probabilities)):
        probability = float(np.max(probs))
        threshold = config.eye_heart_probability if label in {"eye blink", "heart beat"} else config.other_artifact_probability
        remove = label in {"eye blink", "heart beat", "muscle artifact", "line noise", "channel noise", "other"} and probability >= threshold
        if remove:
            excluded.append(component)
        rows.append({"component": component, "label": label, "probability": probability, "automatically_excluded": remove})
    maximum = int(np.floor(config.maximum_ica_exclusion_fraction * len(labels)))
    if len(excluded) > maximum:
        return {"raw": raw, "status": "blocked_exclusion_limit", "component_count": len(labels), "excluded_components": excluded, "labels": rows, "reason": "ICA exclusion count exceeds configured safety limit."}
    ica.exclude = excluded
    output = raw.copy()
    ica.apply(output, verbose="ERROR")
    return {"raw": output, "status": "completed", "component_count": len(labels), "excluded_components": excluded, "labels": rows, "reason": None}


def _screen_epochs(raw, config):
    epoch_samples = int(round(config.epoch_sec * raw.info["sfreq"]))
    count = raw.n_times // epoch_samples
    data = raw.get_data()[:, : count * epoch_samples].reshape(len(raw.ch_names), count, epoch_samples).transpose(1, 0, 2)
    rows = []
    for index, segment in enumerate(data):
        sample_start = int(index * epoch_samples)
        sample_stop = int((index + 1) * epoch_samples)
        peak_to_peak = float(np.ptp(segment * 1e6, axis=1).max())
        flat = bool(np.std(segment * 1e6, axis=1).min() < config.flat_std_uv)
        residual = peak_to_peak > config.residual_peak_to_peak_uv
        retained = not (peak_to_peak > config.absolute_amplitude_uv or flat)
        rows.append({"epoch_index": index, "start_sec": float(index * config.epoch_sec), "end_sec": float((index + 1) * config.epoch_sec), "screened_sample_start": sample_start, "screened_sample_stop": sample_stop, "peak_to_peak_uv": peak_to_peak, "flat_channel_present": flat, "residual_artifact": residual, "retained": retained})
    return data, rows


def _add_analysis_coordinates(
    epoch_rows: list[dict[str, Any]],
    *,
    source_sampling_rate_hz: float,
) -> list[dict[str, Any]]:
    """Attach original and concatenated coordinates without changing legacy fields."""
    analysis_cursor = 0
    mapped_rows = []
    for row in epoch_rows:
        mapped = dict(row)
        sample_count = int(mapped["screened_sample_stop"] - mapped["screened_sample_start"])
        mapped["source_sample_start"] = int(round(mapped["start_sec"] * source_sampling_rate_hz))
        mapped["source_sample_stop"] = int(round(mapped["end_sec"] * source_sampling_rate_hz))
        if mapped["retained"]:
            mapped["analysis_sample_start"] = analysis_cursor
            analysis_cursor += sample_count
            mapped["analysis_sample_stop"] = analysis_cursor
            mapped["analysis_start_sec"] = float(mapped["analysis_sample_start"] / sample_count * (mapped["end_sec"] - mapped["start_sec"]))
            mapped["analysis_end_sec"] = float(mapped["analysis_sample_stop"] / sample_count * (mapped["end_sec"] - mapped["start_sec"]))
        else:
            mapped["analysis_sample_start"] = None
            mapped["analysis_sample_stop"] = None
            mapped["analysis_start_sec"] = None
            mapped["analysis_end_sec"] = None
        mapped_rows.append(mapped)
    return mapped_rows


def build_source_time_mapping(
    source_epoch_rows: list[dict[str, Any]],
    *,
    source_duration_sec: float,
    source_sampling_rate_hz: float,
    screened_sampling_rate_hz: float,
    source_sample_count: int,
    screened_sample_count: int,
    analysis_sample_count: int,
) -> dict[str, Any]:
    """Build a serializable map from concatenated samples to original record time.

    The map deliberately models rejected epochs as gaps.  It is therefore safe
    to use for full-recording figures: callers can restore a time axis with
    :func:`restore_source_time_axis` rather than drawing a false continuous
    trace across discarded intervals.
    """
    if source_duration_sec < 0 or source_sampling_rate_hz <= 0 or screened_sampling_rate_hz <= 0:
        raise ValueError("source duration and sampling rates must be positive")

    retained_intervals = []
    rejected_intervals = []
    expected_analysis_samples = 0
    for fallback_index, row in enumerate(source_epoch_rows):
        required = {
            "epoch_index", "start_sec", "end_sec", "retained",
            "screened_sample_start", "screened_sample_stop",
            "source_sample_start", "source_sample_stop",
            "analysis_sample_start", "analysis_sample_stop",
        }
        missing = required.difference(row)
        if missing:
            raise ValueError(f"source_epoch_rows[{fallback_index}] is missing {sorted(missing)}")
        start_sec, end_sec = float(row["start_sec"]), float(row["end_sec"])
        screened_start = int(row["screened_sample_start"])
        screened_stop = int(row["screened_sample_stop"])
        source_start = int(row["source_sample_start"])
        source_stop = int(row["source_sample_stop"])
        if not (np.isfinite(start_sec) and np.isfinite(end_sec) and end_sec > start_sec):
            raise ValueError(f"source_epoch_rows[{fallback_index}] has invalid source times")
        if screened_stop <= screened_start:
            raise ValueError(f"source_epoch_rows[{fallback_index}] has invalid screened sample bounds")
        if source_stop <= source_start:
            raise ValueError(f"source_epoch_rows[{fallback_index}] has invalid original sample bounds")
        base = {
            "source_epoch_index": int(row["epoch_index"]),
            "source_start_sec": start_sec,
            "source_end_sec": end_sec,
            "source_sample_start": source_start,
            "source_sample_stop": source_stop,
            "screened_sample_start": screened_start,
            "screened_sample_stop": screened_stop,
        }
        if bool(row["retained"]):
            analysis_start = int(row["analysis_sample_start"])
            analysis_stop = int(row["analysis_sample_stop"])
            if analysis_stop - analysis_start != screened_stop - screened_start:
                raise ValueError(f"source_epoch_rows[{fallback_index}] has incompatible analysis sample bounds")
            if analysis_start != expected_analysis_samples:
                raise ValueError("retained analysis sample bounds must be contiguous and ordered")
            base.update({
                "analysis_sample_start": analysis_start,
                "analysis_sample_stop": analysis_stop,
                "analysis_start_sec": float(analysis_start / screened_sampling_rate_hz),
                "analysis_end_sec": float(analysis_stop / screened_sampling_rate_hz),
            })
            retained_intervals.append(base)
            expected_analysis_samples = analysis_stop
        else:
            rejected_intervals.append(base)

    if expected_analysis_samples != analysis_sample_count:
        raise ValueError(
            "retained source epochs contain "
            f"{expected_analysis_samples} samples, but analysis data contain {analysis_sample_count}"
        )

    screened_duration_sec = float(screened_sample_count / screened_sampling_rate_hz)
    screened_epoch_end_sec = float(max((row["end_sec"] for row in source_epoch_rows), default=0.0))
    tail = None
    if source_duration_sec > screened_epoch_end_sec:
        tail = {
            "source_start_sec": screened_epoch_end_sec,
            "source_end_sec": float(source_duration_sec),
            "reason": "partial_epoch_not_screened",
        }
    return {
        "schema_version": "1.0",
        "scope": "concatenated_retained_samples_to_original_recording_time",
        "source_time_axis": "seconds_from_original_recording_start",
        "source_duration_sec": float(source_duration_sec),
        "source_sampling_rate_hz": float(source_sampling_rate_hz),
        "source_sample_count": int(source_sample_count),
        "screened_sampling_rate_hz": float(screened_sampling_rate_hz),
        "screened_sample_count": int(screened_sample_count),
        "screened_duration_sec": screened_duration_sec,
        "analysis_sampling_rate_hz": float(screened_sampling_rate_hz),
        "analysis_sample_count": int(analysis_sample_count),
        "analysis_duration_sec": float(analysis_sample_count / screened_sampling_rate_hz),
        "source_epoch_rows_key": "source_epoch_rows",
        "retained_intervals": retained_intervals,
        "rejected_intervals": rejected_intervals,
        "unmapped_source_tail": tail,
        "gap_representation": "Rejected or unscreened source intervals must be rendered as NaN/blank gaps; they are not concatenated on the source-time axis.",
    }


def retained_sample_source_times(source_time_mapping: dict[str, Any]) -> np.ndarray:
    """Return the original-recording time coordinate for every retained sample.

    The returned vector is discontinuous when epochs were rejected.  Use
    :func:`restore_source_time_axis` for line plots so those discontinuities
    become visible gaps instead of bridged lines.
    """
    sfreq = float(source_time_mapping["analysis_sampling_rate_hz"])
    chunks = []
    for interval in source_time_mapping.get("retained_intervals", []):
        sample_count = int(interval["analysis_sample_stop"] - interval["analysis_sample_start"])
        start_sec = float(interval["source_start_sec"])
        chunks.append(start_sec + np.arange(sample_count, dtype=float) / sfreq)
    times = np.concatenate(chunks) if chunks else np.array([], dtype=float)
    expected = int(source_time_mapping["analysis_sample_count"])
    if len(times) != expected:
        raise ValueError("source_time_mapping retained intervals do not match analysis_sample_count")
    return times


def restore_source_time_axis(
    analysis_data: np.ndarray,
    source_time_mapping: dict[str, Any],
    *,
    fill_value: float = np.nan,
) -> tuple[np.ndarray, np.ndarray]:
    """Place concatenated QC-retained data back on the original time axis.

    ``analysis_data`` may be one-dimensional or have arbitrary leading
    dimensions, but its final dimension must equal the concatenated retained
    sample count.  Rejected epochs and unscreened tail samples are filled with
    ``NaN`` by default, making missing data explicit in full-recording plots.
    """
    values = np.asarray(analysis_data)
    if values.ndim == 0:
        raise ValueError("analysis_data must have a sample dimension")
    expected = int(source_time_mapping["analysis_sample_count"])
    if values.shape[-1] != expected:
        raise ValueError(
            f"analysis_data has {values.shape[-1]} samples, but mapping expects {expected}"
        )
    sfreq = float(source_time_mapping["screened_sampling_rate_hz"])
    grid_samples = int(round(float(source_time_mapping["source_duration_sec"]) * sfreq))
    restored = np.full(values.shape[:-1] + (grid_samples,), fill_value, dtype=float)
    for interval in source_time_mapping.get("retained_intervals", []):
        analysis_start = int(interval["analysis_sample_start"])
        analysis_stop = int(interval["analysis_sample_stop"])
        source_start = int(interval["screened_sample_start"])
        source_stop = int(interval["screened_sample_stop"])
        if source_stop > grid_samples:
            raise ValueError("retained interval exceeds the reconstructed source-time grid")
        restored[..., source_start:source_stop] = values[..., analysis_start:analysis_stop]
    return np.arange(grid_samples, dtype=float) / sfreq, restored


def _gate_reasons(config, bads, channel_count, can_interpolate, ica_result, rows):
    reasons = []
    if bads and not can_interpolate:
        reasons.append("Bad channels were identified but electrode geometry was unavailable for interpolation.")
    if len(bads) > config.maximum_bad_channel_fraction * channel_count:
        reasons.append("Bad-channel fraction exceeds configured safety limit.")
    if ica_result["status"] != "completed":
        reasons.append(ica_result["reason"])
    retained = sum(row["retained"] for row in rows)
    if retained < config.minimum_retained_epochs:
        reasons.append("Too few clean one-second epochs remain after screening.")
    return [reason for reason in reasons if reason]
