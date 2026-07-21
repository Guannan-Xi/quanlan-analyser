"""闭眼/睁眼 Alpha 比例 (Alpha Ratio / 抑制指数)"""

import numpy as np

from ..models import AlphaRatioResult, FREQ_BANDS
from ..spectral import compute_psd_welch, compute_band_power


def _get_o1_o2_indices(channel_names):
    """获取 O1、O2 通道索引"""
    o1_idx = o2_idx = None
    for i, name in enumerate(channel_names):
        name_upper = name.upper().strip()
        if name_upper == 'O1':
            o1_idx = i
        elif name_upper == 'O2':
            o2_idx = i
    return o1_idx, o2_idx


def _alpha_power_o1_o2_mean(data, channel_names, sfreq, alpha_band):
    """计算枕区 O1、O2 的 Alpha 功率均值"""
    o1_idx, o2_idx = _get_o1_o2_indices(channel_names)
    if o1_idx is None or o2_idx is None:
        return None, None, None, None
    freqs_o1, psd_o1 = compute_psd_welch(data[o1_idx], sfreq)
    freqs_o2, psd_o2 = compute_psd_welch(data[o2_idx], sfreq)
    alpha_o1 = float(compute_band_power(psd_o1, freqs_o1, alpha_band))
    alpha_o2 = float(compute_band_power(psd_o2, freqs_o2, alpha_band))
    mean_alpha = (alpha_o1 + alpha_o2) / 2.0
    return mean_alpha, alpha_o1, alpha_o2, (o1_idx, o2_idx)


def analyze_alpha_ratio(closed_eye_data, open_eye_data, channel_names, sfreq, alpha_band=None):
    """计算闭眼/睁眼 Alpha 比例 (抑制指数)"""
    if alpha_band is None:
        alpha_band = FREQ_BANDS['alpha']

    o1_idx, o2_idx = _get_o1_o2_indices(channel_names)
    if o1_idx is None or o2_idx is None:
        missing = []
        if o1_idx is None:
            missing.append('O1')
        if o2_idx is None:
            missing.append('O2')
        print(f"Alpha Ratio 分析警告: 缺少必要通道 {missing}")
        return None

    # 闭眼：O1、O2 Alpha 功率及均值
    closed_mean, alpha_o1_closed, alpha_o2_closed, _ = _alpha_power_o1_o2_mean(
        closed_eye_data, channel_names, sfreq, alpha_band
    )
    # 睁眼：O1、O2 Alpha 功率及均值
    open_mean, alpha_o1_open, alpha_o2_open, _ = _alpha_power_o1_o2_mean(
        open_eye_data, channel_names, sfreq, alpha_band
    )

    if open_mean is None:
        return None

    
    if open_mean <= 1e-10:
        ratio = 0.0
    else:
        ratio = float(closed_mean / open_mean)

    return AlphaRatioResult(
        ratio=ratio,
        alpha_power_closed=float(closed_mean),
        alpha_power_open=float(open_mean),
        alpha_o1_closed=alpha_o1_closed,
        alpha_o2_closed=alpha_o2_closed,
        alpha_o1_open=alpha_o1_open,
        alpha_o2_open=alpha_o2_open,
    )
