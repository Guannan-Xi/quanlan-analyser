"""Band-limited sensor-space EEG connectivity over every usable epoch."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import hilbert


@dataclass(frozen=True)
class ConnectivityConfig:
    bands: tuple[tuple[str, float, float], ...] = (("theta", 4.0, 8.0), ("alpha", 8.0, 13.0), ("beta", 13.0, 30.0))
    epoch_sec: float = 2.0


def compute_connectivity(raw, config: ConnectivityConfig | None = None) -> dict:
    """Compute eight historical report metrics over all non-overlapping epochs.

    Results are sensor-space summaries. They are not source connectivity or
    causal interaction estimates.
    """
    config = config or ConnectivityConfig()
    eeg = raw.copy().pick("eeg")
    data = eeg.get_data() * 1e6
    epoch_samples = int(round(config.epoch_sec * eeg.info["sfreq"]))
    epochs = _epochs(data, epoch_samples)
    if epochs.shape[0] < 2:
        raise ValueError("connectivity requires at least two complete epochs")
    result = {"scope": "full_recording_complete_epochs", "epoch_sec": config.epoch_sec, "epoch_count": int(epochs.shape[0]), "channels": eeg.ch_names, "bands": {}}
    for name, low, high in config.bands:
        analytic = _analytic_band_epochs(epochs, eeg.info["sfreq"], low, high)
        result["bands"][name] = _metrics(analytic, eeg.ch_names)
    return result


def _epochs(data, epoch_samples):
    count = data.shape[1] // epoch_samples
    return data[:, : count * epoch_samples].reshape(data.shape[0], count, epoch_samples).transpose(1, 0, 2)


def _analytic_band_epochs(epochs, sfreq, low, high):
    from mne.filter import filter_data
    filtered = filter_data(epochs.reshape(-1, epochs.shape[-1]), sfreq, low, high, verbose="ERROR")
    return hilbert(filtered.reshape(epochs.shape), axis=-1)


def _metrics(analytic, channels):
    phase = np.angle(analytic)
    amplitude = np.abs(analytic)
    n_channels = analytic.shape[1]
    methods = {name: np.eye(n_channels, dtype=float) for name in ("imcoh", "wpli2_debiased", "ciplv", "ppc", "coherence", "plv", "pli", "aec")}
    for left in range(n_channels):
        for right in range(left + 1, n_channels):
            cross = analytic[:, left] * np.conj(analytic[:, right])
            imaginary = np.imag(cross).ravel()
            delta = (phase[:, left] - phase[:, right]).ravel()
            plv_complex = np.mean(np.exp(1j * delta))
            coherence = np.abs(np.mean(cross)) ** 2 / max(np.mean(np.abs(analytic[:, left]) ** 2) * np.mean(np.abs(analytic[:, right]) ** 2), np.finfo(float).eps)
            imcoh = abs(np.imag(np.mean(cross)) / max(np.sqrt(np.mean(np.abs(analytic[:, left]) ** 2) * np.mean(np.abs(analytic[:, right]) ** 2)), np.finfo(float).eps))
            imaginary_sum = imaginary.sum()
            squared_sum = (imaginary**2).sum()
            wpli2 = (imaginary_sum**2 - squared_sum) / max(np.abs(imaginary).sum() ** 2 - squared_sum, np.finfo(float).eps)
            plv_abs = abs(plv_complex)
            ciplv = abs(np.imag(plv_complex)) / max(np.sqrt(1 - np.real(plv_complex) ** 2), np.finfo(float).eps)
            ppc = (np.abs(np.exp(1j * delta).sum()) ** 2 - delta.size) / max(delta.size * (delta.size - 1), 1)
            pli = abs(np.mean(np.sign(np.sin(delta))))
            aec = abs(_pearson(amplitude[:, left].ravel(), amplitude[:, right].ravel()))
            values = {"imcoh": imcoh, "wpli2_debiased": wpli2, "ciplv": ciplv, "ppc": ppc, "coherence": coherence, "plv": plv_abs, "pli": pli, "aec": aec}
            for method, value in values.items():
                methods[method][left, right] = methods[method][right, left] = float(value)
    return {method: _summarize_matrix(matrix, channels) for method, matrix in methods.items()}


def _summarize_matrix(matrix, channels):
    upper = np.triu_indices(len(channels), 1)
    node_strength = (matrix.sum(axis=1) - np.diag(matrix)) / max(len(channels) - 1, 1)
    edges = [{"source": channels[left], "target": channels[right], "value": float(matrix[left, right])} for left, right in zip(*upper)]
    regional = {}
    for source_region in sorted({_region(channel) for channel in channels}):
        for target_region in sorted({_region(channel) for channel in channels}):
            if target_region < source_region:
                continue
            values = [edge["value"] for edge in edges if {_region(edge["source"]), _region(edge["target"])} == {source_region, target_region}]
            if source_region == target_region:
                values = [edge["value"] for edge in edges if _region(edge["source"]) == source_region and _region(edge["target"]) == target_region]
            regional[f"{source_region}-{target_region}"] = float(np.mean(values)) if values else None
    return {"matrix": matrix.tolist(), "global_mean": float(matrix[upper].mean()), "global_median": float(np.median(matrix[upper])), "node_strength": {channel: float(value) for channel, value in zip(channels, node_strength)}, "edges": edges, "regional_mean": regional}


def _region(channel):
    label = channel.upper()
    if label.startswith(("FP", "AF", "F")):
        return "frontal"
    if label.startswith(("FT", "T", "TP")):
        return "temporal"
    if label.startswith(("CP", "P")):
        return "parietal"
    if label.startswith(("FC", "C")):
        return "central"
    return "occipital"


def _pearson(left, right):
    denom = np.std(left) * np.std(right)
    return 0.0 if denom <= np.finfo(float).eps else np.corrcoef(left, right)[0, 1]
