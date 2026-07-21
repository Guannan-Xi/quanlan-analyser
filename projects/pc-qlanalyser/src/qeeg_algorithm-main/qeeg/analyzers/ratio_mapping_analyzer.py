"""功率比率地形图 (Ratio Mapping)"""

import numpy as np

from ..models import RatioMappingResult, RATIO_BANDS
from ..spectral import compute_psd_welch, compute_band_power


def analyze_ratio_mapping(data, channel_names, sfreq):
    """执行功率比率地形图分析"""
    n_channels = len(channel_names)
    
    freqs, psd = compute_psd_welch(data, sfreq, freq_resolution=0.5)
    
    if psd.ndim == 1:
        psd = psd.reshape(1, -1)
    
    band_powers = {}
    for ch_idx in range(min(n_channels, psd.shape[0])):
        ch_name = channel_names[ch_idx]
        band_powers[ch_name] = {}
        for band_name, band_range in RATIO_BANDS.items():
            band_powers[ch_name][band_name] = compute_band_power(psd[ch_idx], freqs, band_range)
    
    def compute_ratio(numerator_band, denominator_band):
        result = {}
        for ch_name in channel_names:
            if ch_name in band_powers:
                num = band_powers[ch_name][numerator_band]
                den = band_powers[ch_name][denominator_band]
                result[ch_name] = num / den if den > 1e-10 else 0.0
            else:
                result[ch_name] = 0.0
        return result
    
    return RatioMappingResult(
        channel_names=channel_names,
        theta_alpha=compute_ratio('theta', 'alpha'),
        theta_beta=compute_ratio('theta', 'beta'),
        theta_highbeta=compute_ratio('theta', 'high_beta'),
        alpha_beta=compute_ratio('alpha', 'beta'),
        alpha_highbeta=compute_ratio('alpha', 'high_beta'),
        beta_highbeta=compute_ratio('beta', 'high_beta'),
        hightheta_lowalpha=compute_ratio('high_theta', 'low_alpha'),
        lowalpha_highalpha=compute_ratio('low_alpha', 'high_alpha'),
        delta_theta=compute_ratio('delta', 'theta'),
        delta_alpha=compute_ratio('delta', 'alpha'),
        delta_beta=compute_ratio('delta', 'beta'),
        delta_highbeta=compute_ratio('delta', 'high_beta'),
    )
