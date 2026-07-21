"""TBR分析 (Theta/Beta Ratio)"""

import numpy as np

from ..models import TBRResult, TBR_THETA_BAND, TBR_BETA_BAND
from ..spectral import compute_psd_welch, compute_band_power


def analyze_tbr(data, channel_names, sfreq, theta_band=TBR_THETA_BAND, beta_band=TBR_BETA_BAND):
    """执行TBR分析"""
    fz_idx = None
    cz_idx = None
    
    for i, name in enumerate(channel_names):
        name_upper = name.upper()
        if name_upper == 'FZ':
            fz_idx = i
        elif name_upper == 'CZ':
            cz_idx = i
    
    if fz_idx is None or cz_idx is None:
        missing = []
        if fz_idx is None:
            missing.append('Fz')
        if cz_idx is None:
            missing.append('Cz')
        print(f"TBR分析警告: 缺少必要通道 {missing}")
        return None
    
    fz_data = data[fz_idx]
    cz_data = data[cz_idx]
    
    freqs_fz, psd_fz = compute_psd_welch(fz_data, sfreq)
    freqs_cz, psd_cz = compute_psd_welch(cz_data, sfreq)
    
    fz_theta = compute_band_power(psd_fz, freqs_fz, theta_band)
    fz_beta = compute_band_power(psd_fz, freqs_fz, beta_band)
    cz_theta = compute_band_power(psd_cz, freqs_cz, theta_band)
    cz_beta = compute_band_power(psd_cz, freqs_cz, beta_band)
    
    fz_ratio = fz_theta / fz_beta if fz_beta > 1e-10 else 0.0
    cz_ratio = cz_theta / cz_beta if cz_beta > 1e-10 else 0.0
    
    mean_ratio = (fz_ratio + cz_ratio) / 2.0
    
    return TBRResult(
        fz_ratio=fz_ratio,
        cz_ratio=cz_ratio,
        mean_ratio=mean_ratio,
        fz_theta_power=fz_theta,
        fz_beta_power=fz_beta,
        cz_theta_power=cz_theta,
        cz_beta_power=cz_beta,
    )
