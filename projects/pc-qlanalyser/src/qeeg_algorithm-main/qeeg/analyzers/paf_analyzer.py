"""PAF分析 (Peak Alpha Frequency)"""

import numpy as np

from ..models import PAFResult, PAF_SEARCH_BAND
from ..spectral import compute_psd_welch, find_peak_frequency


def analyze_paf(data, channel_names, sfreq, search_band=PAF_SEARCH_BAND,
                freq_resolution=0.1, peak_method='gaussian'):
    """执行PAF分析"""
    o1_idx = None
    o2_idx = None
    
    for i, name in enumerate(channel_names):
        name_upper = name.upper()
        if name_upper == 'O1':
            o1_idx = i
        elif name_upper == 'O2':
            o2_idx = i
    
    if o1_idx is None or o2_idx is None:
        missing = []
        if o1_idx is None:
            missing.append('O1')
        if o2_idx is None:
            missing.append('O2')
        print(f"PAF分析警告: 缺少必要通道 {missing}")
        return None
    
    o1_data = data[o1_idx]
    o2_data = data[o2_idx]
    
    freqs_o1, psd_o1 = compute_psd_welch(o1_data, sfreq, freq_resolution=freq_resolution)
    freqs_o2, psd_o2 = compute_psd_welch(o2_data, sfreq, freq_resolution=freq_resolution)
    
    actual_resolution = freqs_o1[1] - freqs_o1[0] if len(freqs_o1) > 1 else freq_resolution
    
    o1_peak_freq, o1_peak_power = find_peak_frequency(
        psd_o1, freqs_o1, search_band, method=peak_method
    )
    o2_peak_freq, o2_peak_power = find_peak_frequency(
        psd_o2, freqs_o2, search_band, method=peak_method
    )
    
    mean_peak = (o1_peak_freq + o2_peak_freq) / 2.0
    
    return PAFResult(
        o1_peak=o1_peak_freq,
        o2_peak=o2_peak_freq,
        mean_peak=mean_peak,
        o1_peak_power=o1_peak_power,
        o2_peak_power=o2_peak_power,
        frequency_resolution=actual_resolution,
    )
