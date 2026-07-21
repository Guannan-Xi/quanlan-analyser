"""频谱分析核心模块"""

import numpy as np
from scipy import signal


def compute_psd_welch(data, sfreq, nperseg=None, noverlap=None, nfft=None, freq_resolution=0.1):
    """使用Welch方法计算功率谱密度。输入中的 NaN/inf 会被置为 0，避免 PSD 全为 NaN。"""
    data = np.asarray(data, dtype=np.float64)
    if np.any(~np.isfinite(data)):
        data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
    if nperseg is None:
        nperseg = int(sfreq / freq_resolution)
        # 高采样率(如8kHz)时限制单段长度，避免要求过长数据且利于数值稳定
        max_nperseg = min(4 * sfreq, 8192 * 4)
        nperseg = min(max(nperseg, int(2 * sfreq)), max_nperseg)
    if noverlap is None:
        noverlap = nperseg // 2
    if nfft is None:
        nfft = int(2 ** np.ceil(np.log2(nperseg)))
    if data.ndim == 1:
        n_samples = len(data)
    else:
        n_samples = data.shape[1]
    if n_samples < nperseg:
        nperseg = max(256, n_samples)
        noverlap = nperseg // 2
        nfft = int(2 ** np.ceil(np.log2(nperseg)))
    freqs, psd = signal.welch(
        data,
        fs=sfreq,
        nperseg=nperseg,
        noverlap=noverlap,
        nfft=nfft,
        scaling="density",
        axis=-1,
    )
    return freqs, psd


def compute_psd_periodogram(data, sfreq, nfft=None):
    """使用周期图法计算功率谱密度"""
    if data.ndim == 1:
        n_samples = len(data)
    else:
        n_samples = data.shape[1]
    
    if nfft is None:
        nfft = int(2 ** np.ceil(np.log2(n_samples)))
    
    freqs, psd = signal.periodogram(
        data,
        fs=sfreq,
        nfft=nfft,
        scaling='density',
        axis=-1
    )
    
    return freqs, psd


def compute_band_power(psd, freqs, band):
    """计算指定频段的总功率"""
    low, high = band
    idx = np.where((freqs >= low) & (freqs <= high))[0]
    
    if len(idx) == 0:
        if psd.ndim == 1:
            return 0.0
        else:
            return np.zeros(psd.shape[0])
    
    trapz_func = getattr(np, 'trapezoid', None) or np.trapz
    
    if psd.ndim == 1:
        return trapz_func(psd[idx], freqs[idx])
    else:
        return np.array([trapz_func(psd[ch, idx], freqs[idx]) for ch in range(psd.shape[0])])


def compute_relative_power(psd, freqs, band, total_band=(0.5, 45.0)):
    """计算相对功率"""
    band_power = compute_band_power(psd, freqs, band)
    total_power = compute_band_power(psd, freqs, total_band)
    
    if np.isscalar(total_power):
        if total_power < 1e-10:
            return 0.0
        return band_power / total_power
    else:
        result = np.zeros_like(band_power)
        mask = total_power > 1e-10
        result[mask] = band_power[mask] / total_power[mask]
        return result


def find_peak_frequency(psd, freqs, band, method='max'):
    """在指定频段内找到峰值频率"""
    low, high = band
    idx = np.where((freqs >= low) & (freqs <= high))[0]
    
    if len(idx) == 0:
        return 0.0, 0.0
    
    band_freqs = freqs[idx]
    band_psd = psd[idx]
    
    if method == 'max':
        peak_idx = np.argmax(band_psd)
        return band_freqs[peak_idx], band_psd[peak_idx]
    
    elif method == 'cog':
        total_power = np.sum(band_psd)
        if total_power < 1e-10:
            return 0.0, 0.0
        peak_freq = np.sum(band_freqs * band_psd) / total_power
        nearest_idx = np.argmin(np.abs(band_freqs - peak_freq))
        return peak_freq, band_psd[nearest_idx]
    
    elif method == 'gaussian':
        peak_idx = np.argmax(band_psd)
        
        if peak_idx == 0 or peak_idx == len(band_psd) - 1:
            return band_freqs[peak_idx], band_psd[peak_idx]
        
        y0, y1, y2 = band_psd[peak_idx - 1:peak_idx + 2]
        x0, x1, x2 = band_freqs[peak_idx - 1:peak_idx + 2]
        
        denom = (x0 - x1) * (x0 - x2) * (x1 - x2)
        if abs(denom) < 1e-10:
            return band_freqs[peak_idx], band_psd[peak_idx]
        
        A = (x2 * (y1 - y0) + x1 * (y0 - y2) + x0 * (y2 - y1)) / denom
        B = (x2*x2 * (y0 - y1) + x1*x1 * (y2 - y0) + x0*x0 * (y1 - y2)) / denom
        
        if abs(A) < 1e-10:
            return band_freqs[peak_idx], band_psd[peak_idx]
        
        peak_freq = -B / (2 * A)
        peak_freq = np.clip(peak_freq, low, high)
        peak_power = band_psd[peak_idx]
        
        return peak_freq, peak_power
    
    else:
        raise ValueError(f"未知的峰值检测方法: {method}")


def compute_band_powers_multi(psd, freqs, bands):
    """计算多个频段的功率"""
    return {
        name: compute_band_power(psd, freqs, band)
        for name, band in bands.items()
    }


def compute_power_ratio(psd, freqs, numerator_band, denominator_band):
    """计算两个频段的功率比率"""
    num_power = compute_band_power(psd, freqs, numerator_band)
    den_power = compute_band_power(psd, freqs, denominator_band)
    
    if np.isscalar(den_power):
        if den_power < 1e-10:
            return 0.0
        return num_power / den_power
    else:
        result = np.zeros_like(num_power)
        mask = den_power > 1e-10
        result[mask] = num_power[mask] / den_power[mask]
        return result
