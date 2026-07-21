from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import HTTPException

from backend.models.eeg_file import EEGFileRead
from eeg_core.io.readers import read_raw

MAX_DURATION_SEC = 300.0
MAX_CHANNELS = 64
DEFAULT_DISPLAY_SFREQ = 200.0
DEFAULT_WIDTH_PX = 1440
MAX_POINTS_PER_CHANNEL = 6000
MAX_CACHED_CHUNKS = 24


def get_waveform_chunk(
    eeg_file: EEGFileRead,
    *,
    start_sec: float = 0.0,
    duration_sec: float = 24.0,
    channels: str | None = None,
    channel_limit: int = 8,
    display_sfreq: float = DEFAULT_DISPLAY_SFREQ,
    mode: str = "minmax",
    width_px: int = DEFAULT_WIDTH_PX,
) -> dict[str, Any]:
    """Return a lightweight waveform display chunk without task/artifact side effects."""

    input_path = Path(eeg_file.stored_path)
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Stored EEG file is missing")

    stat = input_path.stat()
    return _get_waveform_chunk_cached(
        str(input_path),
        stat.st_mtime_ns,
        eeg_file.id,
        eeg_file.original_filename,
        round(float(start_sec or 0.0), 3),
        round(float(duration_sec or 24.0), 3),
        str(channels or ""),
        int(channel_limit or 8),
        round(float(display_sfreq or DEFAULT_DISPLAY_SFREQ), 3),
        str(mode or "minmax").lower(),
        int(width_px or DEFAULT_WIDTH_PX),
    )


@lru_cache(maxsize=MAX_CACHED_CHUNKS)
def _get_waveform_chunk_cached(
    input_path_str: str,
    mtime_ns: int,
    file_id: str,
    original_filename: str,
    start_sec: float,
    duration_sec: float,
    channels: str,
    channel_limit: int,
    display_sfreq: float,
    mode: str,
    width_px: int,
) -> dict[str, Any]:
    raw = _open_raw_cached(input_path_str)
    sfreq = float(raw.info["sfreq"])
    file_duration = _duration(raw)
    start, duration = _validate_window(start_sec, duration_sec, file_duration)
    stop = start + duration
    picks = _pick_channels(raw, channels=channels, channel_limit=channel_limit)
    raw_window = raw.copy().pick(picks).crop(tmin=start, tmax=stop, include_tmax=False)
    data = raw_window.get_data() * 1e6
    times = raw_window.times + start
    target_sfreq = _target_display_sfreq(display_sfreq, sfreq)
    display_mode = str(mode or "minmax").lower()
    if display_mode not in {"minmax", "sample"}:
        display_mode = "minmax"
    if display_mode == "minmax":
        times_out, data_out = _minmax_bucket(times, data, duration, target_sfreq, int(width_px or DEFAULT_WIDTH_PX))
        downsample = "min_max_bucket"
    else:
        times_out, data_out = _sample_bucket(times, data, duration, target_sfreq)
        downsample = "sample"

    annotations = _annotations(raw, start, stop)
    return {
        "schema_version": "qlanalyser-waveform-chunk-v0.1",
        "source": "waveform_chunk_api",
        "file_id": file_id,
        "input_file": original_filename,
        "start_sec": round(start, 6),
        "duration_sec": round(duration, 6),
        "file_duration_sec": round(file_duration, 6),
        "duration_total_sec": round(file_duration, 6),
        "sfreq_original": sfreq,
        "sfreq_display": target_sfreq,
        "display_sample_rate_hz": target_sfreq,
        "channels": [raw.ch_names[idx] for idx in picks],
        "unit": "uV",
        "times_sec": _round_list(times_out),
        "data_uv": _round_matrix(data_out),
        "events": annotations,
        "annotations": annotations,
        "bad_segments": [],
        "bad_channels": list(raw.info.get("bads") or []),
        "downsample": downsample,
        "decimation": {
            "enabled": len(times_out) < len(times),
            "mode": downsample,
            "preview_only": True,
            "max_points_per_channel": MAX_POINTS_PER_CHANNEL,
        },
        "resampling_policy": {
            "raw_data_resampled": False,
            "display_downsampling_only": True,
            "original_sampling_rate_hz": sfreq,
            "display_sampling_rate_hz": target_sfreq,
            "policy": "Waveform chunk API downsamples for display only and never modifies the uploaded EEG.",
        },
        "reference_policy": {
            "reference_changed": False,
            "policy": "Waveform chunk API does not change EEG reference.",
        },
    }


@lru_cache(maxsize=8)
def _open_raw_cached(path: str):
    return read_raw(path)


def _duration(raw) -> float:
    return float(raw.n_times) / float(raw.info["sfreq"])


def _validate_window(start_sec: float, duration_sec: float, file_duration: float) -> tuple[float, float]:
    start = max(0.0, float(start_sec or 0.0))
    requested = float(duration_sec or 24.0)
    if requested <= 0:
        raise HTTPException(status_code=422, detail="duration_sec must be > 0")
    duration = min(requested, MAX_DURATION_SEC, max(0.001, file_duration - start))
    if start >= file_duration:
        raise HTTPException(status_code=422, detail="start_sec is outside the recording")
    return start, duration


def _pick_channels(raw, *, channels: str | None, channel_limit: int) -> list[int]:
    names = [item.strip() for item in str(channels or "").split(",") if item.strip()]
    if names:
        lookup = {name.lower(): idx for idx, name in enumerate(raw.ch_names)}
        picks = [lookup[name.lower()] for name in names if name.lower() in lookup]
    else:
        try:
            import mne

            picks = list(mne.pick_types(raw.info, eeg=True, meg=False, eog=False, ecg=False, stim=False, exclude=[]))
        except Exception:
            picks = list(range(len(raw.ch_names)))
    limit = max(1, min(MAX_CHANNELS, int(channel_limit or 8)))
    return picks[:limit] or list(range(min(limit, len(raw.ch_names))))


def _target_display_sfreq(display_sfreq: float, sfreq: float) -> float:
    requested = float(display_sfreq or DEFAULT_DISPLAY_SFREQ)
    if requested <= 0:
        requested = DEFAULT_DISPLAY_SFREQ
    return float(min(sfreq, requested))


def _sample_bucket(times: np.ndarray, data: np.ndarray, duration: float, target_sfreq: float) -> tuple[np.ndarray, np.ndarray]:
    max_points = int(min(MAX_POINTS_PER_CHANNEL, max(2, duration * target_sfreq)))
    if data.shape[1] <= max_points:
        return times, data
    indices = np.linspace(0, data.shape[1] - 1, max_points).astype(int)
    return times[indices], data[:, indices]


def _minmax_bucket(times: np.ndarray, data: np.ndarray, duration: float, target_sfreq: float, width_px: int) -> tuple[np.ndarray, np.ndarray]:
    max_points = int(min(MAX_POINTS_PER_CHANNEL, max(2, duration * target_sfreq, width_px * 2)))
    n_samples = data.shape[1]
    if n_samples <= max_points:
        return times, data
    bucket_count = max(1, max_points // 2)
    edges = np.linspace(0, n_samples, bucket_count + 1).astype(int)
    out_times: list[float] = []
    out_rows = [[] for _ in range(data.shape[0])]
    for left, right in zip(edges[:-1], edges[1:]):
        if right <= left:
            continue
        segment = data[:, left:right]
        time_mid = float(times[left:right].mean())
        mins = segment.min(axis=1)
        maxs = segment.max(axis=1)
        out_times.extend([time_mid, time_mid])
        for row_idx in range(data.shape[0]):
            out_rows[row_idx].extend([float(mins[row_idx]), float(maxs[row_idx])])
    return np.asarray(out_times, dtype=float), np.asarray(out_rows, dtype=float)


def _annotations(raw, start: float, stop: float) -> list[dict[str, Any]]:
    annotations = []
    for onset, duration, description in zip(raw.annotations.onset, raw.annotations.duration, raw.annotations.description):
        onset = float(onset)
        if start <= onset <= stop:
            annotations.append(
                {
                    "onset_sec": round(onset, 6),
                    "time_sec": round(onset, 6),
                    "duration_sec": round(float(duration), 6),
                    "description": str(description),
                }
            )
    return annotations[:500]


def _round_list(values: np.ndarray) -> list[float]:
    return [round(float(value), 6) for value in values.tolist()]


def _round_matrix(values: np.ndarray) -> list[list[float]]:
    return [[round(float(value), 4) for value in row] for row in values.tolist()]
