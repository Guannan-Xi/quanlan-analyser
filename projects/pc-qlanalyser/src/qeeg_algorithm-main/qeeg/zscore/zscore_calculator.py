"""Z-Score计算模块"""

import numpy as np
from dataclasses import dataclass, field
from pathlib import Path

from .norms_reader import (
    read_norms_broadband,
    read_norms_narrowband,
    get_norms_filepath,
    CUBAN_19_CHANNELS,
)
from ..spectral import compute_band_power


BA_ELECTRODES = {
    "BA10": ["Fpz", "Fp1", "Fp2"],
    "BA8_6": ["Fz"],
    "BA8_9_L": ["F3"],
    "BA8_9_R": ["F4"],
    "BA47_45_L": ["F7"],
    "BA47_45_R": ["F8"],
    "BA6_4": ["Cz"],
    "BA1_4_L": ["C3"],
    "BA1_4_R": ["C4"],
    "BA21_22_L": ["T3"],
    "BA21_22_R": ["T4"],
    "BA37_19_L": ["T5"],
    "BA37_19_R": ["T6"],
    "BA7_31": ["Pz"],
    "BA7_40_L": ["P3"],
    "BA7_40_R": ["P4"],
    "BA17_18": ["Oz", "O1", "O2"],
}

BA_REGIONS = {
    "Frontal": ["BA10", "BA8_6", "BA8_9_L", "BA8_9_R", "BA47_45_L", "BA47_45_R"],
    "Central": ["BA6_4", "BA1_4_L", "BA1_4_R"],
    "Temporal": ["BA21_22_L", "BA21_22_R", "BA37_19_L", "BA37_19_R"],
    "Parietal": ["BA7_31", "BA7_40_L", "BA7_40_R"],
    "Occipital": ["BA17_18"],
}


@dataclass
class BroadBandZScore:
    """宽带模型Z-Score结果"""
    z_absolute_power: dict = field(default_factory=dict)
    z_relative_power: dict = field(default_factory=dict)
    z_median_freq: dict = field(default_factory=dict)
    band_names: list = field(default_factory=list)
    channel_names: list = field(default_factory=list)
    z_by_brodmann_area: dict = field(default_factory=dict)
    z_by_region: dict = field(default_factory=dict)
    
    def to_dict(self):
        return {
            "z_absolute_power": self.z_absolute_power,
            "z_relative_power": self.z_relative_power,
            "z_median_frequency": self.z_median_freq,
            "band_names": self.band_names,
            "channel_names": self.channel_names,
            "z_by_brodmann_area": self.z_by_brodmann_area,
            "z_by_region": self.z_by_region,
        }


@dataclass
class NarrowBandZScore:
    """窄带模型Z-Score结果"""
    z_matrix: np.ndarray = None
    frequencies: np.ndarray = None
    channel_names: list = field(default_factory=list)
    z_by_channel: dict = field(default_factory=dict)
    log_offset_used: float = 0.0
    
    def to_dict(self):
        return {
            "z_by_channel": self.z_by_channel,
            "frequencies": self.frequencies.tolist() if self.frequencies is not None else [],
            "channel_names": self.channel_names,
            "z_matrix_shape": list(self.z_matrix.shape) if self.z_matrix is not None else None,
            "log_offset_used": self.log_offset_used,
        }


def _narrow_band_edges(start=2.0, end=34.0, step=2.0):
    """2-4, 4-6, 6-8 Hz 等"""
    edges = []
    f = start
    while f < end:
        edges.append((f, f + step))
        f += step
    return edges


@dataclass
class NarrowBandZScoreBands:
    """窄带按频段(2-4,4-6,…Hz)的绝对/相对功率Z-Score"""
    band_edges: list = field(default_factory=list)
    channel_names: list = field(default_factory=list)
    z_absolute_power: dict = field(default_factory=dict)
    z_relative_power: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "band_edges_hz": self.band_edges,
            "channel_names": self.channel_names,
            "z_absolute_power": self.z_absolute_power,
            "z_relative_power": self.z_relative_power,
        }


RATIO_DEFINITIONS = [
    ('theta_alpha', 'theta', 'alpha'),
    ('theta_beta', 'theta', 'beta'),
    ('alpha_beta', 'alpha', 'beta'),
    ('delta_theta', 'delta', 'theta'),
    ('delta_alpha', 'delta', 'alpha'),
    ('delta_beta', 'delta', 'beta'),
]


@dataclass
class RatioZScore:
    """频段功率比率的Z-Score结果"""
    ratio_names: list = field(default_factory=list)
    channel_names: list = field(default_factory=list)
    z_by_channel: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "ratio_names": self.ratio_names,
            "channel_names": self.channel_names,
            "z_by_channel": self.z_by_channel,
        }


@dataclass
class ZScoreResult:
    """完整Z-Score分析结果"""
    age: float
    state: str
    broadband: 'BroadBandZScore' = None
    narrowband: 'NarrowBandZScore' = None
    narrowband_bands: 'NarrowBandZScoreBands' = None
    ratio: 'RatioZScore' = None
    n_significant_deviations: int = 0
    significant_channels: list = field(default_factory=list)
    
    def to_dict(self):
        return {
            "age": self.age,
            "state": self.state,
            "broadband": self.broadband.to_dict() if self.broadband else None,
            "narrowband": self.narrowband.to_dict() if self.narrowband else None,
            "narrowband_bands": self.narrowband_bands.to_dict() if self.narrowband_bands else None,
            "ratio": self.ratio.to_dict() if self.ratio else None,
            "summary": {
                "n_significant_deviations": self.n_significant_deviations,
                "significant_channels": self.significant_channels,
            }
        }


class ZScoreCalculator:
    """Z-Score计算器"""
    
    BROAD_BANDS = {
        'delta': (1.56, 3.51),
        'theta': (3.9, 7.41),
        'alpha': (7.8, 12.48),
        'beta': (12.87, 19.11),
        'total': (1.56, 30.0),
    }
    
    def __init__(self, norms_dir):
        self.norms_dir = Path(norms_dir)
        if not self.norms_dir.exists():
            raise FileNotFoundError(f"规范数据目录不存在: {norms_dir}")
        self._norms_cache = {}
    
    def _get_norms(self, age, state, model, pg_correct=True):
        cache_key = (age, state, model, pg_correct)
        
        if cache_key not in self._norms_cache:
            filepath = get_norms_filepath(
                str(self.norms_dir),
                state=state,
                model=model,
                pg_correct=pg_correct
            )
            
            if model == 'broadband':
                self._norms_cache[cache_key] = read_norms_broadband(filepath, age)
            else:
                self._norms_cache[cache_key] = read_norms_narrowband(filepath, age)
        
        return self._norms_cache[cache_key]
    
    def _map_channels(self, input_channels, input_data):
        mapped = np.zeros(19, dtype=np.float32)
        valid_indices = []
        
        input_lookup = {ch.upper(): ch for ch in input_channels}
        
        for i, cuban_ch in enumerate(CUBAN_19_CHANNELS):
            cuban_upper = cuban_ch.upper()
            
            if cuban_upper in input_lookup:
                original_name = input_lookup[cuban_upper]
                if original_name in input_data:
                    mapped[i] = input_data[original_name]
                    valid_indices.append(i)
        
        return mapped, valid_indices
    
    def _calculate_brodmann_area_zscore(self, z_by_channel, band_names):
        z_by_ba = {}
        
        channel_lookup = {ch.upper(): ch for ch in z_by_channel.keys()}
        
        for ba_name, electrodes in BA_ELECTRODES.items():
            z_by_ba[ba_name] = {}
            
            for band in band_names:
                z_values = []
                
                for electrode in electrodes:
                    electrode_upper = electrode.upper()
                    
                    if electrode_upper in channel_lookup:
                        actual_ch = channel_lookup[electrode_upper]
                        if band in z_by_channel.get(actual_ch, {}):
                            z_values.append(z_by_channel[actual_ch][band])
                
                if z_values:
                    z_by_ba[ba_name][band] = float(np.mean(z_values))
                else:
                    z_by_ba[ba_name][band] = None
        
        return z_by_ba
    
    def _calculate_region_zscore(self, z_by_ba, band_names):
        z_by_region = {}
        
        for region_name, ba_list in BA_REGIONS.items():
            z_by_region[region_name] = {}
            
            for band in band_names:
                z_values = []
                
                for ba_name in ba_list:
                    if ba_name in z_by_ba:
                        z_val = z_by_ba[ba_name].get(band)
                        if z_val is not None:
                            z_values.append(z_val)
                
                if z_values:
                    z_by_region[region_name][band] = float(np.mean(z_values))
                else:
                    z_by_region[region_name][band] = None
        
        return z_by_region
    
    def calculate_broadband_zscore(self, absolute_power, relative_power, input_channels,
                                   age, state='eyes_closed', pg_correct=True, log_offset=None):
        """计算宽带模型Z-Score"""
        norms = self._get_norms(age, state, 'broadband', pg_correct)
        
        band_names = list(self.BROAD_BANDS.keys())[:norms.n_bands]
        
        channel_mapping = {}
        for ch_idx, cuban_ch in enumerate(CUBAN_19_CHANNELS):
            cuban_upper = cuban_ch.upper()
            for ich in input_channels:
                if ich.upper() == cuban_upper:
                    channel_mapping[cuban_ch] = (ch_idx, ich)
                    break
        
        if log_offset is None:
            offsets = []
            for cuban_ch, (ch_idx, input_ch) in channel_mapping.items():
                for band_idx, band_name in enumerate(band_names):
                    if band_name in absolute_power and input_ch in absolute_power[band_name]:
                        obs_log = np.log(absolute_power[band_name][input_ch] + 1e-10)
                        norm_mean = norms.mean_pa[ch_idx, band_idx]
                        offsets.append(norm_mean - obs_log)
            
            if offsets:
                log_offset = float(np.median(offsets))
            else:
                log_offset = 0.0
        
        z_pa = {}
        z_pr = {}
        matched_channels = []
        
        for cuban_ch, (ch_idx, input_ch) in channel_mapping.items():
            matched_channels.append(cuban_ch)
            z_pa[cuban_ch] = {}
            z_pr[cuban_ch] = {}
            
            for band_idx, band_name in enumerate(band_names):
                if band_name in absolute_power and input_ch in absolute_power[band_name]:
                    obs_pa = np.log(absolute_power[band_name][input_ch] + 1e-10) + log_offset
                    mean_pa = norms.mean_pa[ch_idx, band_idx]
                    std_pa = norms.std_pa[ch_idx, band_idx]
                    
                    if std_pa > 1e-10:
                        z_pa[cuban_ch][band_name] = float((obs_pa - mean_pa) / std_pa)
                    else:
                        z_pa[cuban_ch][band_name] = 0.0
                
                if band_idx < norms.n_bands - 1:
                    if band_name in relative_power and input_ch in relative_power[band_name]:
                        obs_pr = relative_power[band_name][input_ch]
                        mean_pr = norms.mean_pr[ch_idx, band_idx]
                        std_pr = norms.std_pr[ch_idx, band_idx]
                        
                        if std_pr > 1e-10:
                            z_pr[cuban_ch][band_name] = float((obs_pr - mean_pr) / std_pr)
                        else:
                            z_pr[cuban_ch][band_name] = 0.0
        
        z_by_ba = self._calculate_brodmann_area_zscore(z_pa, band_names)
        z_by_region = self._calculate_region_zscore(z_by_ba, band_names)
        
        return BroadBandZScore(
            z_absolute_power=z_pa,
            z_relative_power=z_pr,
            z_median_freq={},
            band_names=band_names,
            channel_names=matched_channels,
            z_by_brodmann_area=z_by_ba,
            z_by_region=z_by_region,
        )
    
    def calculate_narrowband_zscore(self, psd_data, psd_freqs, input_channels, age,
                                    state='eyes_closed', pg_correct=True, log_offset=None):
        """计算窄带模型Z-Score"""
        norms = self._get_norms(age, state, 'narrowband', pg_correct)
        
        norm_freqs = norms.frequencies
        matched_freq_indices = []
        matched_psd_indices = []
        
        for i, nf in enumerate(norm_freqs):
            diff = np.abs(psd_freqs - nf)
            min_idx = np.argmin(diff)
            if diff[min_idx] < 0.5:
                matched_freq_indices.append(i)
                matched_psd_indices.append(min_idx)
        
        if len(matched_freq_indices) == 0:
            return NarrowBandZScore(
                z_matrix=np.array([]),
                frequencies=np.array([]),
                channel_names=[],
                z_by_channel={},
            )
        
        channel_mapping = {}
        for ch_idx, cuban_ch in enumerate(CUBAN_19_CHANNELS):
            cuban_upper = cuban_ch.upper()
            for i, ich in enumerate(input_channels):
                if ich.upper() == cuban_upper:
                    channel_mapping[ch_idx] = i
                    break
        
        if log_offset is None:
            offsets = []
            for ch_idx, input_idx in channel_mapping.items():
                if input_idx >= psd_data.shape[0]:
                    continue
                for norm_idx, psd_idx in zip(matched_freq_indices, matched_psd_indices):
                    obs_log = np.log(psd_data[input_idx, psd_idx] + 1e-10)
                    norm_mean = norms.mean_coef[ch_idx, norm_idx]
                    offsets.append(norm_mean - obs_log)
            
            if offsets:
                log_offset = float(np.median(offsets))
            else:
                log_offset = 0.0
        
        n_matched_freqs = len(matched_freq_indices)
        z_matrix = np.zeros((19, n_matched_freqs), dtype=np.float32)
        z_by_channel = {}
        matched_channels = []
        
        for ch_idx, cuban_ch in enumerate(CUBAN_19_CHANNELS):
            if ch_idx not in channel_mapping:
                continue
            
            input_idx = channel_mapping[ch_idx]
            if input_idx >= psd_data.shape[0]:
                continue
            
            matched_channels.append(cuban_ch)
            z_values = []
            
            for j, (norm_idx, psd_idx) in enumerate(zip(matched_freq_indices, matched_psd_indices)):
                psd_val = psd_data[input_idx, psd_idx]
                
                obs = np.log(psd_val + 1e-10) + log_offset
                
                mean_val = norms.mean_coef[ch_idx, norm_idx]
                std_val = norms.std_coef[ch_idx, norm_idx]
                
                if std_val > 1e-10:
                    z = (obs - mean_val) / std_val
                else:
                    z = 0.0
                
                z_matrix[ch_idx, j] = z
                z_values.append(float(z))
            
            z_by_channel[cuban_ch] = z_values
        
        return NarrowBandZScore(
            z_matrix=z_matrix,
            frequencies=norm_freqs[matched_freq_indices],
            channel_names=matched_channels,
            z_by_channel=z_by_channel,
            log_offset_used=log_offset,
        )

    def calculate_narrowband_band_zscore(self, psd_data, psd_freqs, input_channels, age,
                                        state='eyes_closed', pg_correct=True, log_offset=None,
                                        start_freq=2.0, end_freq=34.0, step=2.0, total_power_range=(0.5, 45.0)):
        """窄带频段(2-4,4-6,…Hz)绝对/相对功率Z-Score"""
        norms = self._get_norms(age, state, 'narrowband', pg_correct)
        band_edges = _narrow_band_edges(start_freq, end_freq, step)
        norm_freqs = norms.frequencies
        channel_mapping = {}
        for ch_idx, cuban_ch in enumerate(CUBAN_19_CHANNELS):
            for i, ich in enumerate(input_channels):
                if ich.upper() == cuban_ch.upper():
                    channel_mapping[ch_idx] = i
                    break
        if not channel_mapping:
            return NarrowBandZScoreBands(band_edges=band_edges, channel_names=[], z_absolute_power={}, z_relative_power={})

        n_channels = norms.n_channels
        n_freqs = norms.n_freqs
        if psd_data.ndim == 1:
            psd_data = psd_data.reshape(1, -1)

        total_obs = np.zeros(n_channels)
        for ch_idx, input_idx in channel_mapping.items():
            if input_idx >= psd_data.shape[0]:
                continue
            total_obs[ch_idx] = float(compute_band_power(psd_data[input_idx], psd_freqs, total_power_range))
        total_obs[total_obs <= 0] = 1e-10

        if log_offset is None:
            log_offset = 0.0

        z_abs = {}
        z_rel = {}
        matched_channels = []
        rel_std_default = 0.05

        for ch_idx, cuban_ch in enumerate(CUBAN_19_CHANNELS):
            if ch_idx not in channel_mapping:
                continue
            input_idx = channel_mapping[ch_idx]
            if input_idx >= psd_data.shape[0]:
                continue
            matched_channels.append(cuban_ch)
            z_abs[cuban_ch] = {}
            z_rel[cuban_ch] = {}

            total_norm = np.sum(np.exp(np.clip(norms.mean_coef[ch_idx, :], -20, 20)))
            total_norm = max(total_norm, 1e-10)

            for band_idx, (low, high) in enumerate(band_edges):
                band_label = f"{low:.0f}-{high:.0f}"
                obs_abs = float(compute_band_power(psd_data[input_idx], psd_freqs, (low, high)))
                obs_abs = max(obs_abs, 1e-10)
                obs_rel = obs_abs / total_obs[ch_idx]

                mask = (norm_freqs >= low) & (norm_freqs < high)
                if not np.any(mask):
                    z_abs[cuban_ch][band_label] = 0.0
                    z_rel[cuban_ch][band_label] = 0.0
                    continue
                norm_mean_log = float(np.mean(norms.mean_coef[ch_idx, mask]))
                norm_std_log = float(np.sqrt(np.mean(norms.std_coef[ch_idx, mask] ** 2)))
                norm_std_log = max(norm_std_log, 1e-10)
                obs_log = np.log(obs_abs) + log_offset
                z_abs[cuban_ch][band_label] = float((obs_log - norm_mean_log) / norm_std_log)

                band_norm = np.sum(np.exp(np.clip(norms.mean_coef[ch_idx, mask], -20, 20)))
                norm_rel = band_norm / total_norm
                z_rel[cuban_ch][band_label] = float((obs_rel - norm_rel) / rel_std_default)

        return NarrowBandZScoreBands(
            band_edges=band_edges,
            channel_names=matched_channels,
            z_absolute_power=z_abs,
            z_relative_power=z_rel,
        )

    def calculate_ratio_zscore(self, absolute_power, input_channels, age,
                               state='eyes_closed', pg_correct=True):
        """计算频段功率比率的Z-Score (基于宽带常模)"""
        norms = self._get_norms(age, state, 'broadband', pg_correct)
        band_names = list(self.BROAD_BANDS.keys())[:norms.n_bands]
        band_index = {name: idx for idx, name in enumerate(band_names)}

        channel_mapping = {}
        for ch_idx, cuban_ch in enumerate(CUBAN_19_CHANNELS):
            for ich in input_channels:
                if ich.upper() == cuban_ch.upper():
                    channel_mapping[cuban_ch] = (ch_idx, ich)
                    break

        ratio_names = [r[0] for r in RATIO_DEFINITIONS]
        z_by_channel = {}
        matched_channels = []

        for cuban_ch, (ch_idx, input_ch) in channel_mapping.items():
            matched_channels.append(cuban_ch)
            z_by_channel[cuban_ch] = {}

            for ratio_name, num_band, den_band in RATIO_DEFINITIONS:
                if num_band not in band_index or den_band not in band_index:
                    z_by_channel[cuban_ch][ratio_name] = 0.0
                    continue

                num_idx = band_index[num_band]
                den_idx = band_index[den_band]

                num_val = absolute_power.get(num_band, {}).get(input_ch)
                den_val = absolute_power.get(den_band, {}).get(input_ch)
                if num_val is None or den_val is None or num_val <= 0 or den_val <= 0:
                    z_by_channel[cuban_ch][ratio_name] = 0.0
                    continue

                # ln(ratio) = ln(num) - ln(den)，log_offset 在相减时自动抵消
                obs_ln_ratio = np.log(num_val) - np.log(den_val)

                norm_mean_ln_ratio = float(
                    norms.mean_pa[ch_idx, num_idx] - norms.mean_pa[ch_idx, den_idx])
                norm_std_ln_ratio = float(np.sqrt(
                    norms.std_pa[ch_idx, num_idx] ** 2 + norms.std_pa[ch_idx, den_idx] ** 2))

                if norm_std_ln_ratio > 1e-10:
                    z_by_channel[cuban_ch][ratio_name] = float(
                        (obs_ln_ratio - norm_mean_ln_ratio) / norm_std_ln_ratio)
                else:
                    z_by_channel[cuban_ch][ratio_name] = 0.0

        return RatioZScore(
            ratio_names=ratio_names,
            channel_names=matched_channels,
            z_by_channel=z_by_channel,
        )

    def calculate(self, psd_result, age, state='eyes_closed', calculate_broadband=True,
                  calculate_narrowband=True, pg_correct=True, log_offset=None):
        """计算完整的Z-Score分析"""
        if age < 5 or age > 87:
            raise ValueError(f"年龄必须在5-87岁范围内，当前: {age}")
        
        broadband_result = None
        narrowband_result = None
        
        if calculate_broadband:
            abs_power = {
                'delta': psd_result.delta_power,
                'theta': psd_result.theta_power,
                'alpha': psd_result.alpha_power,
                'beta': psd_result.beta_power,
            }
            rel_power = {
                'delta': psd_result.delta_power_rel,
                'theta': psd_result.theta_power_rel,
                'alpha': psd_result.alpha_power_rel,
                'beta': psd_result.beta_power_rel,
            }
            
            broadband_result = self.calculate_broadband_zscore(
                absolute_power=abs_power,
                relative_power=rel_power,
                input_channels=psd_result.channel_names,
                age=age,
                state=state,
                pg_correct=pg_correct,
                log_offset=log_offset,
            )
        
        ratio_result = None
        if calculate_broadband:
            ratio_result = self.calculate_ratio_zscore(
                absolute_power=abs_power,
                input_channels=psd_result.channel_names,
                age=age,
                state=state,
                pg_correct=pg_correct,
            )

        narrowband_bands_result = None
        if calculate_narrowband:
            narrowband_result = self.calculate_narrowband_zscore(
                psd_data=psd_result.psd_array,
                psd_freqs=psd_result.freqs,
                input_channels=psd_result.channel_names,
                age=age,
                state=state,
                pg_correct=pg_correct,
                log_offset=log_offset,
            )
            narrowband_bands_result = self.calculate_narrowband_band_zscore(
                psd_data=psd_result.psd_array,
                psd_freqs=psd_result.freqs,
                input_channels=psd_result.channel_names,
                age=age,
                state=state,
                pg_correct=pg_correct,
                log_offset=log_offset,
            )
        else:
            narrowband_result = None

        n_significant = 0
        significant_channels = set()
        
        if broadband_result:
            for ch, bands in broadband_result.z_absolute_power.items():
                for band, z in bands.items():
                    if abs(z) >= 1.96:
                        n_significant += 1
                        significant_channels.add(ch)
        
        return ZScoreResult(
            age=age,
            state=state,
            broadband=broadband_result,
            narrowband=narrowband_result,
            narrowband_bands=narrowband_bands_result,
            ratio=ratio_result,
            n_significant_deviations=n_significant,
            significant_channels=list(significant_channels),
        )


def interpret_zscore(z):
    """解读Z值的临床意义"""
    abs_z = abs(z)
    direction = "elevated" if z > 0 else "reduced"
    
    if abs_z < 1.0:
        return "within normal range"
    elif abs_z < 1.96:
        return f"mildly {direction}"
    elif abs_z < 2.58:
        return f"significantly {direction} (p<0.05)"
    else:
        return f"highly significantly {direction} (p<0.01)"
