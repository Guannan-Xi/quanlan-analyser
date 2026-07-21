"""全频段地形图矩阵 (Full Band Mapping)"""

import numpy as np

from ..models import BandMappingResult
from ..spectral import compute_psd_welch, compute_band_power


def generate_narrow_bands(start_freq=2.0, end_freq=34.0, step=2.0):
    """生成窄带频段列表"""
    bands = []
    current = start_freq
    while current < end_freq:
        bands.append((current, current + step))
        current += step
    return bands


def analyze_band_mapping(data, channel_names, sfreq, start_freq=2.0, end_freq=34.0,
                         step=2.0, total_power_range=(0.5, 45.0)):
    """执行全频段地形图矩阵分析"""
    band_edges = generate_narrow_bands(start_freq, end_freq, step)
    n_bands = len(band_edges)
    n_channels = len(channel_names)
    
    freqs, psd = compute_psd_welch(data, sfreq, freq_resolution=0.5)
    
    if psd.ndim == 1:
        psd = psd.reshape(1, -1)
    
    absolute_power = np.zeros((n_bands, n_channels))
    relative_power = np.zeros((n_bands, n_channels))
    
    total_powers = np.zeros(n_channels)
    for ch_idx in range(min(n_channels, psd.shape[0])):
        total_powers[ch_idx] = compute_band_power(psd[ch_idx], freqs, total_power_range)
    
    for band_idx, (low, high) in enumerate(band_edges):
        for ch_idx in range(min(n_channels, psd.shape[0])):
            abs_power = compute_band_power(psd[ch_idx], freqs, (low, high))
            absolute_power[band_idx, ch_idx] = abs_power
            
            if total_powers[ch_idx] > 1e-10:
                relative_power[band_idx, ch_idx] = abs_power / total_powers[ch_idx]
    
    return BandMappingResult(
        band_edges=band_edges,
        channel_names=channel_names,
        absolute_power=absolute_power,
        relative_power=relative_power,
    )
