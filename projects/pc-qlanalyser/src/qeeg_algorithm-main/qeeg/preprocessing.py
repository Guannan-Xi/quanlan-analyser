"""EEG信号预处理模块"""

import numpy as np
from scipy import signal
from dataclasses import dataclass

from .models import PreprocessingParams
from .edf_reader import EDFData


@dataclass
class PreprocessingResult:
    """预处理结果"""
    data: np.ndarray
    channel_names: list
    sampling_frequency: float
    artifact_mask: np.ndarray = None
    artifact_ratio: float = 0.0
    bad_channels: list = None


def bandpass_filter(data, sfreq, lowcut, highcut, order=4):
    """带通滤波器。高采样率(如8kHz)下使用 sos 形式保证数值稳定，避免输出 NaN。"""
    nyq = sfreq / 2.0
    low = max(0.5, min(lowcut, nyq - 1))
    high = max(low + 1.0, min(highcut, nyq - 0.5))
    sos = signal.butter(order, [low, high], btype="band", output="sos", fs=sfreq)
    if data.ndim == 1:
        return signal.sosfiltfilt(sos, data)
    return np.array([signal.sosfiltfilt(sos, ch) for ch in data])


def highpass_filter(data, sfreq, cutoff, order=4):
    """高通滤波器。使用 sos 形式保证高采样率下数值稳定。"""
    cutoff_hz = max(0.5, min(cutoff, sfreq / 2.0 - 0.5))
    sos = signal.butter(order, cutoff_hz, btype="high", output="sos", fs=sfreq)
    if data.ndim == 1:
        return signal.sosfiltfilt(sos, data)
    return np.array([signal.sosfiltfilt(sos, ch) for ch in data])


def lowpass_filter(data, sfreq, cutoff, order=4):
    """低通滤波器。使用 sos 形式保证高采样率下数值稳定。"""
    cutoff_hz = max(1.0, min(cutoff, sfreq / 2.0 - 0.5))
    sos = signal.butter(order, cutoff_hz, btype="low", output="sos", fs=sfreq)
    if data.ndim == 1:
        return signal.sosfiltfilt(sos, data)
    return np.array([signal.sosfiltfilt(sos, ch) for ch in data])


def notch_filter(data, sfreq, freq, quality_factor=30.0):
    """陷波滤波器。高采样率下使用 sos 形式。"""
    nyq = sfreq / 2.0
    if freq >= nyq:
        return data
    b, a = signal.iirnotch(freq, quality_factor, fs=sfreq)
    sos = signal.tf2sos(b, a)
    if data.ndim == 1:
        return signal.sosfiltfilt(sos, data)
    return np.array([signal.sosfiltfilt(sos, ch) for ch in data])


def baseline_correction(data, method='mean'):
    """基线校正"""
    if method == 'mean':
        if data.ndim == 1:
            return data - np.mean(data)
        else:
            return data - np.mean(data, axis=1, keepdims=True)
    
    elif method == 'median':
        if data.ndim == 1:
            return data - np.median(data)
        else:
            return data - np.median(data, axis=1, keepdims=True)
    
    elif method == 'polynomial':
        if data.ndim == 1:
            return signal.detrend(data, type='linear')
        else:
            return np.array([signal.detrend(ch, type='linear') for ch in data])
    
    else:
        raise ValueError(f"未知的基线校正方法: {method}")


def detect_artifacts(data, sfreq, amplitude_threshold=100.0, gradient_threshold=50.0, window_size=0.2):
    """检测EEG伪迹"""
    n_channels, n_samples = data.shape
    window_samples = int(window_size * sfreq)
    
    artifact_mask = np.zeros(n_samples, dtype=bool)
    
    for ch_idx in range(n_channels):
        ch_data = data[ch_idx]
        
        amp_artifacts = np.abs(ch_data) > amplitude_threshold
        
        gradient = np.abs(np.diff(ch_data, prepend=ch_data[0]))
        grad_artifacts = gradient > gradient_threshold
        
        flat_artifacts = np.zeros(n_samples, dtype=bool)
        for i in range(0, n_samples - window_samples, window_samples // 2):
            window = ch_data[i:i + window_samples]
            if np.std(window) < 0.1:
                flat_artifacts[i:i + window_samples] = True
        
        ch_artifacts = amp_artifacts | grad_artifacts | flat_artifacts
        
        extended = np.zeros_like(ch_artifacts)
        for i in range(n_samples):
            if ch_artifacts[i]:
                start = max(0, i - window_samples // 2)
                end = min(n_samples, i + window_samples // 2)
                extended[start:end] = True
        
        artifact_mask |= extended
    
    artifact_ratio = np.sum(artifact_mask) / n_samples
    
    return artifact_mask, artifact_ratio


def interpolate_artifacts(data, artifact_mask, method='linear'):
    """插值修复伪迹区域"""
    result = data.copy()
    n_channels, n_samples = data.shape
    good_indices = np.where(~artifact_mask)[0]
    bad_indices = np.where(artifact_mask)[0]
    
    if len(bad_indices) == 0 or len(good_indices) < 2:
        return result
    
    for ch_idx in range(n_channels):
        if method == 'linear':
            result[ch_idx, bad_indices] = np.interp(
                bad_indices, 
                good_indices, 
                data[ch_idx, good_indices]
            )
        elif method == 'zero':
            result[ch_idx, bad_indices] = 0
        elif method == 'cubic':
            from scipy.interpolate import interp1d
            f = interp1d(good_indices, data[ch_idx, good_indices], 
                        kind='cubic', fill_value='extrapolate')
            result[ch_idx, bad_indices] = f(bad_indices)
    
    return result


def resample(data, original_sfreq, target_sfreq):
    """重采样"""
    if abs(original_sfreq - target_sfreq) < 0.1:
        return data
    
    ratio = target_sfreq / original_sfreq
    
    if data.ndim == 1:
        new_length = int(len(data) * ratio)
        return signal.resample(data, new_length)
    else:
        n_channels, n_samples = data.shape
        new_length = int(n_samples * ratio)
        return np.array([signal.resample(ch, new_length) for ch in data])


def preprocess(edf_data, params, verbose=False):
    """执行完整的EEG预处理流程"""
    data = np.asarray(edf_data.raw_data, dtype=np.float64).copy()
    if np.any(~np.isfinite(data)):
        if verbose:
            print("  警告: 原始数据含 NaN/inf，已置为 0 再继续预处理")
        data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
    sfreq = edf_data.sampling_frequency
    if verbose:
        print(f"开始预处理...")
        print(f"  原始数据形状: {data.shape}")
        print(f"  采样率: {sfreq} Hz")
    
    if params.baseline_correction:
        if verbose:
            print("  执行基线校正...")
        data = baseline_correction(data, method='mean')
    
    if verbose:
        print(f"  执行带通滤波 ({params.lowcut}-{params.highcut} Hz)...")
    data = bandpass_filter(data, sfreq, params.lowcut, params.highcut)
    
    if params.notch_freq is not None:
        if verbose:
            print(f"  执行陷波滤波 ({params.notch_freq} Hz)...")
        data = notch_filter(data, sfreq, params.notch_freq)
    
    artifact_mask = None
    artifact_ratio = 0.0
    
    if params.artifact_rejection:
        if verbose:
            print(f"  执行伪迹检测 (阈值: {params.amplitude_threshold} μV)...")
        artifact_mask, artifact_ratio = detect_artifacts(
            data, sfreq, params.amplitude_threshold
        )
        
        if verbose:
            print(f"  伪迹比例: {artifact_ratio * 100:.2f}%")
        
        if artifact_ratio < 0.5:
            data = interpolate_artifacts(data, artifact_mask, method='linear')
        else:
            if verbose:
                print(f"  警告: 伪迹比例过高 ({artifact_ratio * 100:.1f}%)，跳过插值修复")
    
    if params.target_sfreq is not None and params.target_sfreq != sfreq:
        if verbose:
            print(f"  执行重采样 ({sfreq} -> {params.target_sfreq} Hz)...")
        data = resample(data, sfreq, params.target_sfreq)
        sfreq = params.target_sfreq
    
    if verbose:
        print(f"  预处理完成，输出数据形状: {data.shape}")
    
    return PreprocessingResult(
        data=data,
        channel_names=edf_data.channel_names,
        sampling_frequency=sfreq,
        artifact_mask=artifact_mask,
        artifact_ratio=artifact_ratio,
        bad_channels=[],
    )
