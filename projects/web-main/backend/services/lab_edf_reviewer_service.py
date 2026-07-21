"""
EDF Reviewer Service for QLanalyser Analysis Lab

Lab-only EDF waveform processing service for public demo/research use.
No persistent storage, no billing, no customer auth integration.

Boundaries:
- Temporary processing only (tempfile cleanup)
- No database persistence
- No integration with main business APIs
- Public research tool
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Tuple

import mne
import numpy as np
from scipy import signal


def _read_raw_auto(path: str | Path) -> mne.io.BaseRaw:
    """Read EEG file with auto-format detection (.fif, .edf, .bdf)."""
    import re
    p = Path(path)
    suffix = p.suffix.lower()
    try:
        if suffix in (".fif", ".fiff"):
            return mne.io.read_raw_fif(p, preload=False, verbose="ERROR")
        if suffix in (".bdf"):
            return mne.io.read_raw_bdf(p, preload=False, verbose="ERROR")
        return mne.io.read_raw_edf(p, preload=False, verbose="ERROR")
    except Exception:
        return mne.io.read_raw_edf(p, preload=False, verbose="ERROR")


def inspect_edf_bytes(raw_bytes: bytes, filename: str = "") -> dict:
    """
    Parse EDF metadata without loading full data.
    
    Args:
        raw_bytes: Raw EDF file bytes
        
    Returns:
        Dict with sfreq, duration, channels, meas_date, channel_count, file_hash
        
    Raises:
        Exception: If EDF parsing fails
    """
    file_hash = hashlib.sha256(raw_bytes).hexdigest()[:16]
    suffix = Path(filename).suffix if filename else ".edf"
    
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = tmp.name
    
    try:
        raw = _read_raw_auto(tmp_path)
        return {
            "sfreq": float(raw.info["sfreq"]),
            "duration": float(raw.n_times / raw.info["sfreq"]),
            "channels": list(raw.ch_names),
            "meas_date": str(raw.info.get("meas_date")),
            "channel_count": len(raw.ch_names),
            "file_hash": file_hash,
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def process_edf_waveform(
    raw_bytes: bytes,
    channels: list[str],
    highpass: float,
    lowpass: float,
    notch: float,
    max_points: int,
    filename: str = "",
) -> dict:
    """
    Extract, filter, downsample, and normalize waveform data for display.
    
    Args:
        raw_bytes: Raw EDF file bytes
        channels: List of channel names to extract
        highpass: Highpass filter cutoff (Hz), 0 to disable
        lowpass: Lowpass filter cutoff (Hz), 0 to disable
        notch: Notch filter frequency (Hz), 0 to disable
        max_points: Maximum points for frontend display (downsampling)
        
    Returns:
        Dict with times, values, channels, base_scale, unit_label, sfreq, filter_summary
        
    Raises:
        Exception: If processing fails
    """
    if not channels:
        raise ValueError("At least one channel must be selected")
    
    if highpass > 0 and lowpass > 0 and highpass >= lowpass:
        raise ValueError("Highpass frequency must be lower than lowpass frequency")
    
    # Read selected channels
    data, times, sfreq = _read_edf_data(raw_bytes, channels, filename)
    
    # Auto-scale to microvolts if needed
    data, unit_label = _maybe_microvolts(data, list(channels))
    
    # Apply filters
    data = _apply_filters(data, sfreq, highpass, lowpass, notch)
    
    # Downsample for display
    data, times = _decimate(data, times, max_points)
    
    # Append ACC RMS if ACC channels present
    data, channels_out, acc_count = _append_acc_rms(data, list(channels))
    
    # Normalize by robust scale
    base_scale = _robust_scale(data)
    normalized = data / base_scale
    
    return {
        "times": np.round(times, 4).tolist(),
        "values": np.round(normalized, 6).tolist(),
        "channels": channels_out,
        "base_scale": float(base_scale),
        "unit_label": unit_label,
        "sfreq": float(sfreq),
        "filter_summary": _filter_summary(highpass, lowpass, notch),
        "acc_rms_derived": acc_count > 0,
        "acc_rms_source_count": acc_count,
    }


def _read_edf_data(raw_bytes: bytes, channels: list[str], filename: str = "") -> Tuple[np.ndarray, np.ndarray, float]:
    """Read selected channels from EEG bytes (auto-detect format)."""
    suffix = Path(filename).suffix if filename else ".edf"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = tmp.name
    
    try:
        raw = _read_raw_auto(tmp_path)
        raw.load_data()
        sfreq = float(raw.info["sfreq"])
        data, times = raw.get_data(picks=list(channels), return_times=True)
        return data, times, sfreq
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _maybe_microvolts(data: np.ndarray, channel_names: list[str]) -> Tuple[np.ndarray, str]:
    """
    Auto-scale to microvolts if EEG channels appear to be in volts.
    
    If EEG-like channels have 95th percentile < 0.01, assume volts and scale to µV.
    """
    eeg_like = [name for name in channel_names if name.upper().startswith("EEG")]
    if eeg_like and np.nanpercentile(np.abs(data[: len(eeg_like)]), 95) < 0.01:
        return data * 1e6, "uV（按电压读数换算）"
    return data, "原始 EDF 单位"


def _apply_filters(
    data: np.ndarray,
    sfreq: float,
    highpass: float,
    lowpass: float,
    notch: float,
) -> np.ndarray:
    """Apply highpass, lowpass, and notch filters."""
    filtered = data.copy()
    
    # Apply IIR bandpass/highpass/lowpass
    if highpass > 0 or lowpass > 0:
        filtered = mne.filter.filter_data(
            filtered,
            sfreq=sfreq,
            l_freq=highpass if highpass > 0 else None,
            h_freq=lowpass if lowpass > 0 else None,
            method="iir",
            verbose="ERROR",
        )
    
    # Apply notch filter
    if notch > 0:
        b, a = signal.iirnotch(w0=notch, Q=30, fs=sfreq)
        filtered = signal.filtfilt(b, a, filtered, axis=1)
    
    return filtered


def _decimate(data: np.ndarray, times: np.ndarray, max_points: int) -> Tuple[np.ndarray, np.ndarray]:
    """Downsample data to max_points for frontend display."""
    if data.shape[1] <= max_points:
        return data, times
    step = int(np.ceil(data.shape[1] / max_points))
    return data[:, ::step], times[::step]


def _append_acc_rms(data: np.ndarray, channel_names: list[str]) -> Tuple[np.ndarray, list[str], int]:
    """
    Append a derived ACC RMS channel if ACC axes are present.
    
    Returns:
        (data_with_rms, channels_with_rms, acc_source_count)
    """
    # Check if ACC RMS already exists
    if any("ACC RMS" in str(name).upper() or "体动RMS" in str(name) for name in channel_names):
        return data, list(channel_names), 0
    
    # Find ACC channel indices
    acc_indices = [idx for idx, name in enumerate(channel_names) if _is_acc_channel(name)]
    if not acc_indices:
        return data, list(channel_names), 0
    
    # Compute RMS from ACC axes
    acc_data = data[acc_indices, :]
    rms = np.sqrt(np.nanmean(np.square(acc_data), axis=0, keepdims=True))
    
    return np.vstack([data, rms]), [*channel_names, "ACC RMS（体动）"], len(acc_indices)


def _is_acc_channel(name: str) -> bool:
    """Check if channel name represents an accelerometer axis."""
    upper = str(name or "").upper().replace(" ", "")
    return upper.startswith("ACC") or (upper.startswith("X") and "ACC" in upper)


def _robust_scale(data: np.ndarray) -> float:
    """
    Compute robust scale using 95th percentile of absolute values.
    
    Used for normalization to avoid outlier influence.
    """
    q = np.nanpercentile(np.abs(data), 95)
    if not np.isfinite(q) or q == 0:
        return 1.0
    return float(q)


def _filter_summary(highpass: float, lowpass: float, notch: float) -> str:
    """Generate human-readable filter summary."""
    parts = []
    if highpass > 0:
        parts.append(f"高通 {highpass:g} Hz")
    if lowpass > 0:
        parts.append(f"低通 {lowpass:g} Hz")
    if notch > 0:
        parts.append(f"陷波 {notch:g} Hz")
    return "；".join(parts) if parts else "未滤波"
