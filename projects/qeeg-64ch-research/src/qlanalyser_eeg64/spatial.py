"""Spatial EEG complexity from the full-record channel correlation spectrum."""

from __future__ import annotations

import numpy as np


def compute_spatial_complexity(raw) -> dict:
    """Compute omega complexity from covariance eigenvalue entropy."""
    eeg = raw.copy().pick("eeg")
    data = eeg.get_data()
    correlation = np.corrcoef(data)
    eigenvalues = np.linalg.eigvalsh(correlation)
    probabilities = np.maximum(eigenvalues, 0) / max(np.maximum(eigenvalues, 0).sum(), np.finfo(float).eps)
    entropy = -np.sum(np.where(probabilities > 0, probabilities * np.log(probabilities), 0.0))
    omega = float(np.exp(entropy))
    channel_count = len(eeg.ch_names)
    return {"scope": "full_recording", "method": "omega_complexity_from_channel_correlation_eigenvalue_entropy", "channel_count": channel_count, "reference_rank_loss": 1, "maximum_effective_dimension": channel_count - 1, "omega_effective_dimension": omega, "omega_normalized": float(omega / max(channel_count - 1, 1)), "eigenvalue_entropy_nats": float(entropy), "matrix": "pearson_channel_correlation"}
