"""QEEG数据模型定义"""

from dataclasses import dataclass, field
import numpy as np


STANDARD_21_CHANNELS = [
    'Fp1', 'Fp2', 'C3', 'C4', 'O1', 'O2', 'Cz', 'T3', 'T4',
    'F3', 'F4', 'Fz', 'F7', 'F8', 'Pz', 'P3',
    'T5', 'P4', 'T6', 'Fpz', 'Oz'
]

CHANNEL_ALIASES = {
    "T7": "T3", "T8": "T4",
    "T3": "T3", "T4": "T4",
    "P7": "T5", "P8": "T6",
    "T5": "T5", "T6": "T6",
    "M1": "A1", "M2": "A2",
    "A1": "A1", "A2": "A2",
    "FP1": "Fp1", "FP2": "Fp2", "FPZ": "Fpz",
    "FZ": "Fz", "CZ": "Cz", "PZ": "Pz", "OZ": "Oz",
}

FREQ_BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "smr": (12.0, 15.0),
    "beta": (13.0, 30.0),
    "high_beta": (21.0, 30.0),
    "gamma": (30.0, 45.0),
}

TBR_THETA_BAND = (4.0, 8.0)
TBR_BETA_BAND = (13.0, 21.0)
PAF_SEARCH_BAND = (8.0, 13.0)

RATIO_BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "high_theta": (6.0, 8.0),
    "alpha": (8.0, 13.0),
    "low_alpha": (8.0, 10.0),
    "high_alpha": (10.0, 13.0),
    "beta": (13.0, 30.0),
    "high_beta": (21.0, 30.0),
}


@dataclass
class PreprocessingParams:
    """预处理参数配置"""
    lowcut = 0.5
    highcut = 45.0
    notch_freq = 50.0
    artifact_rejection = True
    amplitude_threshold = 100.0
    baseline_correction = True
    target_sfreq = None


@dataclass
class TimeWindow:
    """分析时间窗口"""
    start: float
    end: float
    
    def __post_init__(self):
        if self.end < self.start:
            raise ValueError(f"结束时间必须大于等于起始时间: start={self.start}, end={self.end}")
    
    @property
    def duration(self):
        return self.end - self.start


@dataclass
class PAFResult:
    """PAF分析结果"""
    o1_peak: float
    o2_peak: float
    mean_peak: float
    o1_peak_power: float = 0.0
    o2_peak_power: float = 0.0
    frequency_resolution: float = 0.1
    
    def to_dict(self):
        return {
            "o1_peak_hz": self.o1_peak,
            "o2_peak_hz": self.o2_peak,
            "mean_peak_hz": self.mean_peak,
            "o1_peak_power": self.o1_peak_power,
            "o2_peak_power": self.o2_peak_power,
            "frequency_resolution_hz": self.frequency_resolution,
        }


@dataclass
class TBRResult:
    """TBR分析结果"""
    fz_ratio: float
    cz_ratio: float
    mean_ratio: float
    fz_theta_power: float = 0.0
    fz_beta_power: float = 0.0
    cz_theta_power: float = 0.0
    cz_beta_power: float = 0.0
    
    def to_dict(self):
        return {
            "fz_ratio": self.fz_ratio,
            "cz_ratio": self.cz_ratio,
            "mean_ratio": self.mean_ratio,
            "fz_theta_power_uv2": self.fz_theta_power,
            "fz_beta_power_uv2": self.fz_beta_power,
            "cz_theta_power_uv2": self.cz_theta_power,
            "cz_beta_power_uv2": self.cz_beta_power,
        }


@dataclass
class PSDResult:
    """全脑PSD分析结果"""
    psd_array: np.ndarray
    psd_relative_array: np.ndarray
    freqs: np.ndarray
    channel_names: list
    
    delta_power: dict = field(default_factory=dict)
    theta_power: dict = field(default_factory=dict)
    alpha_power: dict = field(default_factory=dict)
    smr_power: dict = field(default_factory=dict)
    beta_power: dict = field(default_factory=dict)
    high_beta_power: dict = field(default_factory=dict)
    gamma_power: dict = field(default_factory=dict)
    
    delta_power_rel: dict = field(default_factory=dict)
    theta_power_rel: dict = field(default_factory=dict)
    alpha_power_rel: dict = field(default_factory=dict)
    smr_power_rel: dict = field(default_factory=dict)
    beta_power_rel: dict = field(default_factory=dict)
    high_beta_power_rel: dict = field(default_factory=dict)
    gamma_power_rel: dict = field(default_factory=dict)
    
    def to_dict(self):
        return {
            "channel_names": self.channel_names,
            "frequencies": self.freqs.tolist() if isinstance(self.freqs, np.ndarray) else self.freqs,
            "psd_shape": list(self.psd_array.shape) if isinstance(self.psd_array, np.ndarray) else None,
            "band_powers_absolute": {
                "delta_0.5-4Hz": self.delta_power,
                "theta_4-8Hz": self.theta_power,
                "alpha_8-13Hz": self.alpha_power,
                "smr_12-15Hz": self.smr_power,
                "beta_13-30Hz": self.beta_power,
                "high_beta_21-30Hz": self.high_beta_power,
                "gamma_30-45Hz": self.gamma_power,
            },
            "band_powers_relative": {
                "delta_0.5-4Hz": self.delta_power_rel,
                "theta_4-8Hz": self.theta_power_rel,
                "alpha_8-13Hz": self.alpha_power_rel,
                "smr_12-15Hz": self.smr_power_rel,
                "beta_13-30Hz": self.beta_power_rel,
                "high_beta_21-30Hz": self.high_beta_power_rel,
                "gamma_30-45Hz": self.gamma_power_rel,
            }
        }


@dataclass
class BandMappingResult:
    """全频段地形图矩阵结果"""
    band_edges: list
    channel_names: list
    absolute_power: np.ndarray
    relative_power: np.ndarray
    
    def to_dict(self):
        return {
            "band_edges_hz": self.band_edges,
            "channel_names": self.channel_names,
            "absolute_power_shape": list(self.absolute_power.shape),
            "relative_power_shape": list(self.relative_power.shape),
            "absolute_power": self.absolute_power.tolist() if isinstance(self.absolute_power, np.ndarray) else self.absolute_power,
            "relative_power": self.relative_power.tolist() if isinstance(self.relative_power, np.ndarray) else self.relative_power,
        }


@dataclass 
class RatioMappingResult:
    """功率比率地形图结果"""
    channel_names: list
    
    theta_alpha: dict = field(default_factory=dict)
    theta_beta: dict = field(default_factory=dict)
    theta_highbeta: dict = field(default_factory=dict)
    alpha_beta: dict = field(default_factory=dict)
    alpha_highbeta: dict = field(default_factory=dict)
    beta_highbeta: dict = field(default_factory=dict)
    hightheta_lowalpha: dict = field(default_factory=dict)
    lowalpha_highalpha: dict = field(default_factory=dict)
    delta_theta: dict = field(default_factory=dict)
    delta_alpha: dict = field(default_factory=dict)
    delta_beta: dict = field(default_factory=dict)
    delta_highbeta: dict = field(default_factory=dict)
    
    def to_dict(self):
        return {
            "channel_names": self.channel_names,
            "ratios": {
                "1_theta_alpha": self.theta_alpha,
                "2_theta_beta": self.theta_beta,
                "3_theta_highbeta": self.theta_highbeta,
                "4_alpha_beta": self.alpha_beta,
                "5_alpha_highbeta": self.alpha_highbeta,
                "6_beta_highbeta": self.beta_highbeta,
                "7_hightheta_lowalpha": self.hightheta_lowalpha,
                "8_lowalpha_highalpha": self.lowalpha_highalpha,
                "9_delta_theta": self.delta_theta,
                "10_delta_alpha": self.delta_alpha,
                "11_delta_beta": self.delta_beta,
                "12_delta_highbeta": self.delta_highbeta,
            }
        }


@dataclass
class FAAResult:
    """前额Alpha非对称性 (Frontal Alpha Asymmetry) 分析结果"""
    faa_percentage: float
    alpha_f3: float = 0.0
    alpha_f4: float = 0.0
    ln_alpha_f3: float = 0.0
    ln_alpha_f4: float = 0.0
    
    def to_dict(self):
        return {
            "faa_percentage": self.faa_percentage,
            "alpha_f3_power_uv2": self.alpha_f3,
            "alpha_f4_power_uv2": self.alpha_f4,
            "ln_alpha_f3": self.ln_alpha_f3,
            "ln_alpha_f4": self.ln_alpha_f4,
        }


@dataclass
class AlphaRatioResult:
    """闭眼/睁眼 Alpha 比例 (Alpha Ratio / 抑制指数) 分析结果"""
    ratio: float
    alpha_power_closed: float = 0.0
    alpha_power_open: float = 0.0
    alpha_o1_closed: float = 0.0
    alpha_o2_closed: float = 0.0
    alpha_o1_open: float = 0.0
    alpha_o2_open: float = 0.0

    def to_dict(self):
        return {
            "alpha_ratio": self.ratio,
            "alpha_power_closed_uv2": self.alpha_power_closed,
            "alpha_power_open_uv2": self.alpha_power_open,
            "alpha_o1_closed_uv2": self.alpha_o1_closed,
            "alpha_o2_closed_uv2": self.alpha_o2_closed,
            "alpha_o1_open_uv2": self.alpha_o1_open,
            "alpha_o2_open_uv2": self.alpha_o2_open,
        }


@dataclass
class QEEGAnalysisResult:
    """完整的QEEG分析结果汇总"""
    file_path: str
    analysis_time_window: TimeWindow
    preprocessing_params: PreprocessingParams
    sampling_frequency: float
    n_channels: int
    channel_names: list
    
    paf: 'PAFResult' = None
    tbr: 'TBRResult' = None
    psd: 'PSDResult' = None
    band_mapping: 'BandMappingResult' = None
    ratio_mapping: 'RatioMappingResult' = None
    faa: 'FAAResult' = None
    alpha_ratio: 'AlphaRatioResult' = None

    success: bool = True
    error_message: str = None
    
    def to_dict(self):
        return {
            "metadata": {
                "file_path": self.file_path,
                "time_window": {
                    "start_s": self.analysis_time_window.start,
                    "end_s": self.analysis_time_window.end,
                    "duration_s": self.analysis_time_window.duration,
                },
                "sampling_frequency_hz": self.sampling_frequency,
                "n_channels": self.n_channels,
                "channel_names": self.channel_names,
            },
            "results": {
                "paf": self.paf.to_dict() if self.paf else None,
                "tbr": self.tbr.to_dict() if self.tbr else None,
                "psd": self.psd.to_dict() if self.psd else None,
                "band_mapping": self.band_mapping.to_dict() if self.band_mapping else None,
                "ratio_mapping": self.ratio_mapping.to_dict() if self.ratio_mapping else None,
                "faa": self.faa.to_dict() if self.faa else None,
                "alpha_ratio": self.alpha_ratio.to_dict() if self.alpha_ratio else None,
            },
            "status": {
                "success": self.success,
                "error_message": self.error_message,
            }
        }
