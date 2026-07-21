"""FAA分析 (Frontal Alpha Asymmetry - 前额Alpha非对称性)"""

import numpy as np

from ..models import FAAResult, FREQ_BANDS
from ..spectral import compute_psd_welch, compute_band_power


def analyze_faa(data, channel_names, sfreq, alpha_band=None):
    """执行FAA分析"""
    if alpha_band is None:
        alpha_band = FREQ_BANDS['alpha']
    
    f3_idx = None
    f4_idx = None
    
    for i, name in enumerate(channel_names):
        name_upper = name.upper()
        if name_upper == 'F3':
            f3_idx = i
        elif name_upper == 'F4':
            f4_idx = i
    
    if f3_idx is None or f4_idx is None:
        missing = []
        if f3_idx is None:
            missing.append('F3')
        if f4_idx is None:
            missing.append('F4')
        print(f"FAA分析警告: 缺少必要通道 {missing}")
        return None
    
    f3_data = data[f3_idx]
    f4_data = data[f4_idx]
    
    freqs_f3, psd_f3 = compute_psd_welch(f3_data, sfreq)
    freqs_f4, psd_f4 = compute_psd_welch(f4_data, sfreq)
    
    alpha_f3 = compute_band_power(psd_f3, freqs_f3, alpha_band)
    alpha_f4 = compute_band_power(psd_f4, freqs_f4, alpha_band)
    
    # 转换为float
    alpha_f3 = float(alpha_f3)
    alpha_f4 = float(alpha_f4)
    
    # 计算自然对数，避免对0或负数取对数
    if alpha_f3 <= 0:
        ln_alpha_f3 = 0.0
    else:
        ln_alpha_f3 = np.log(alpha_f3)
    
    if alpha_f4 <= 0:
        ln_alpha_f4 = 0.0
    else:
        ln_alpha_f4 = np.log(alpha_f4)
    
    faa_raw = ln_alpha_f4 - ln_alpha_f3
    
    # 换为百分比
    faa_percentage = faa_raw * 100.0
    
    return FAAResult(
        faa_percentage=faa_percentage,
        alpha_f3=alpha_f3,
        alpha_f4=alpha_f4,
        ln_alpha_f3=ln_alpha_f3,
        ln_alpha_f4=ln_alpha_f4,
    )
