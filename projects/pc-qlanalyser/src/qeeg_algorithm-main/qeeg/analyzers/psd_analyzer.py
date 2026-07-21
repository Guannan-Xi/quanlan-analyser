"""全脑PSD分析 (Power Spectral Density)"""

import numpy as np

from ..models import PSDResult, FREQ_BANDS
from ..spectral import compute_psd_welch, compute_psd_periodogram, compute_band_power


def analyze_psd(data, channel_names, sfreq, method='welch', freq_resolution=0.5):
    """执行全脑PSD分析"""
    if method == 'welch':
        freqs, psd = compute_psd_welch(data, sfreq, freq_resolution=freq_resolution)
    else:
        freqs, psd = compute_psd_periodogram(data, sfreq)
    
    if psd.ndim == 1:
        psd = psd.reshape(1, -1)

    trapz_func = getattr(np, 'trapezoid', None) or np.trapz
    psd_relative = np.zeros_like(psd)
    for ch_idx in range(psd.shape[0]):
        total = trapz_func(psd[ch_idx], freqs)
        if total > 1e-10:
            psd_relative[ch_idx] = psd[ch_idx] / total

    n_channels = len(channel_names)
    total_power_range = (0.5, 45.0)
    
    delta_power = {}
    theta_power = {}
    alpha_power = {}
    smr_power = {}
    beta_power = {}
    high_beta_power = {}
    gamma_power = {}
    
    delta_power_rel = {}
    theta_power_rel = {}
    alpha_power_rel = {}
    smr_power_rel = {}
    beta_power_rel = {}
    high_beta_power_rel = {}
    gamma_power_rel = {}
    
    for i, ch_name in enumerate(channel_names):
        if i < psd.shape[0]:
            ch_psd = psd[i]
            
            delta = float(compute_band_power(ch_psd, freqs, FREQ_BANDS['delta']))
            theta = float(compute_band_power(ch_psd, freqs, FREQ_BANDS['theta']))
            alpha = float(compute_band_power(ch_psd, freqs, FREQ_BANDS['alpha']))
            smr = float(compute_band_power(ch_psd, freqs, FREQ_BANDS['smr']))
            beta = float(compute_band_power(ch_psd, freqs, FREQ_BANDS['beta']))
            high_beta = float(compute_band_power(ch_psd, freqs, FREQ_BANDS['high_beta']))
            gamma = float(compute_band_power(ch_psd, freqs, FREQ_BANDS['gamma']))
            
            delta_power[ch_name] = delta
            theta_power[ch_name] = theta
            alpha_power[ch_name] = alpha
            smr_power[ch_name] = smr
            beta_power[ch_name] = beta
            high_beta_power[ch_name] = high_beta
            gamma_power[ch_name] = gamma
            
            total_power = float(compute_band_power(ch_psd, freqs, total_power_range))
            
            if total_power > 1e-10:
                delta_power_rel[ch_name] = delta / total_power
                theta_power_rel[ch_name] = theta / total_power
                alpha_power_rel[ch_name] = alpha / total_power
                smr_power_rel[ch_name] = smr / total_power
                beta_power_rel[ch_name] = beta / total_power
                high_beta_power_rel[ch_name] = high_beta / total_power
                gamma_power_rel[ch_name] = gamma / total_power
            else:
                delta_power_rel[ch_name] = 0.0
                theta_power_rel[ch_name] = 0.0
                alpha_power_rel[ch_name] = 0.0
                smr_power_rel[ch_name] = 0.0
                beta_power_rel[ch_name] = 0.0
                high_beta_power_rel[ch_name] = 0.0
                gamma_power_rel[ch_name] = 0.0
    
    return PSDResult(
        psd_array=psd,
        psd_relative_array=psd_relative,
        freqs=freqs,
        channel_names=channel_names,
        delta_power=delta_power,
        theta_power=theta_power,
        alpha_power=alpha_power,
        smr_power=smr_power,
        beta_power=beta_power,
        high_beta_power=high_beta_power,
        gamma_power=gamma_power,
        delta_power_rel=delta_power_rel,
        theta_power_rel=theta_power_rel,
        alpha_power_rel=alpha_power_rel,
        smr_power_rel=smr_power_rel,
        beta_power_rel=beta_power_rel,
        high_beta_power_rel=high_beta_power_rel,
        gamma_power_rel=gamma_power_rel,
    )
