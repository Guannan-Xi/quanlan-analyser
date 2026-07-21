
import numpy as np
from pathlib import Path
import mne
from dataclasses import dataclass

from .models import STANDARD_21_CHANNELS, CHANNEL_ALIASES


@dataclass
class EDFData:
    """EDF数据容器"""
    raw_data: np.ndarray
    channel_names: list
    sampling_frequency: float
    duration: float
    n_channels: int
    n_samples: int
    file_path: str
    channel_indices: dict = None
    
    def __post_init__(self):
        if self.channel_indices is None:
            self.channel_indices = {name: i for i, name in enumerate(self.channel_names)}
    
    def get_channel_data(self, channel_name):
        if channel_name in self.channel_indices:
            return self.raw_data[self.channel_indices[channel_name]]
        
        normalized = normalize_channel_name(channel_name)
        if normalized in self.channel_indices:
            return self.raw_data[self.channel_indices[normalized]]
        
        for alias, standard in CHANNEL_ALIASES.items():
            if standard == channel_name and alias in self.channel_indices:
                return self.raw_data[self.channel_indices[alias]]
        
        return None
    
    def get_channels_data(self, channel_names):
        data_list = []
        found_channels = []
        
        for name in channel_names:
            ch_data = self.get_channel_data(name)
            if ch_data is not None:
                data_list.append(ch_data)
                found_channels.append(name)
        
        if not data_list:
            return np.array([]), []
        
        return np.array(data_list), found_channels
    
    def get_time_segment(self, start_sec, end_sec):
        start_idx = int(start_sec * self.sampling_frequency)
        end_idx = int(end_sec * self.sampling_frequency)
        
        start_idx = max(0, start_idx)
        end_idx = min(self.n_samples, end_idx)
        
        segmented_data = self.raw_data[:, start_idx:end_idx]
        new_n_samples = segmented_data.shape[1]
        new_duration = new_n_samples / self.sampling_frequency
        
        return EDFData(
            raw_data=segmented_data,
            channel_names=self.channel_names.copy(),
            sampling_frequency=self.sampling_frequency,
            duration=new_duration,
            n_channels=self.n_channels,
            n_samples=new_n_samples,
            file_path=self.file_path,
            channel_indices=self.channel_indices.copy(),
        )


def normalize_channel_name(name):
    """标准化通道名称"""
    name = name.strip()
    name = name.replace("EEG ", "").replace("EEG-", "").replace("eeg ", "")
    
    for suffix in ["-Ref", "-REF", "-ref", "-LE", "-le", "-AVG", "-avg"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    
    if len(name) >= 2:
        if name[:2].upper() in ["FP", "FZ", "CZ", "PZ", "OZ"]:
            name = name[:2].capitalize() + name[2:]
        else:
            name = name[0].upper() + name[1:]
    
    name_upper = name.upper()
    if name_upper in {k.upper(): k for k in CHANNEL_ALIASES}:
        for alias, standard in CHANNEL_ALIASES.items():
            if alias.upper() == name_upper:
                return standard
    
    return name


def read_edf(file_path, verbose=False, select_channels=None):
    """读取EDF/EDF+文件"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"EDF文件不存在: {file_path}")
    
    if path.suffix.lower() not in ['.edf', '.bdf']:
        raise ValueError(f"不支持的文件格式: {path.suffix}")
    
    raw = mne.io.read_raw_edf(
        file_path, 
        preload=True, 
        verbose='WARNING' if not verbose else 'INFO'
    )
    
    original_ch_names = raw.ch_names
    sfreq = raw.info['sfreq']
    
    if verbose:
        print(f"已读取EDF文件: {file_path}")
        print(f"  采样率: {sfreq} Hz")
        print(f"  原始通道数: {len(original_ch_names)}")
    
    normalized_original = {normalize_channel_name(name): name for name in original_ch_names}
    upper_to_original = {name.upper(): name for name in original_ch_names}
    upper_to_normalized = {norm.upper(): orig for norm, orig in normalized_original.items()}
    
    if select_channels is not None:
        selected_original_names = []
        selected_normalized_names = []
        missing_channels = []
        
        for ch in select_channels:
            ch_normalized = normalize_channel_name(ch)
            ch_upper = ch.upper()
            
            found = False
            original_name = None
            
            if ch in original_ch_names:
                original_name = ch
                found = True
            elif ch_upper in upper_to_original:
                original_name = upper_to_original[ch_upper]
                found = True
            elif ch_normalized in normalized_original:
                original_name = normalized_original[ch_normalized]
                found = True
            elif ch_normalized.upper() in upper_to_normalized:
                original_name = upper_to_normalized[ch_normalized.upper()]
                found = True
            else:
                for alias, standard in CHANNEL_ALIASES.items():
                    if standard.upper() == ch_upper or alias.upper() == ch_upper:
                        test_names = [alias, standard, alias.upper(), standard.upper()]
                        for test in test_names:
                            if test in original_ch_names:
                                original_name = test
                                found = True
                                break
                            elif test.upper() in upper_to_original:
                                original_name = upper_to_original[test.upper()]
                                found = True
                                break
                    if found:
                        break
            
            if found and original_name:
                selected_original_names.append(original_name)
                selected_normalized_names.append(ch_normalized)
            else:
                missing_channels.append(ch)
        
        if missing_channels and verbose:
            print(f"  警告: 未找到以下通道: {missing_channels}")
        
        if not selected_original_names:
            raise ValueError(f"在EDF文件中未找到任何指定通道。可用通道: {original_ch_names[:10]}...")
        
        raw.pick_channels(selected_original_names)
        
        if verbose:
            print(f"  已选择 {len(selected_original_names)}/{len(select_channels)} 个通道")
            print(f"  选择的通道: {selected_normalized_names}")
        
        ch_names = selected_normalized_names
    else:
        ch_names = [normalize_channel_name(name) for name in original_ch_names]
    
    data = raw.get_data()
    data = data * 1e6  # 转换为μV
    
    n_samples = data.shape[1]
    duration = n_samples / sfreq
    
    channel_indices = {name: i for i, name in enumerate(ch_names)}
    
    if verbose:
        print(f"  时长: {duration:.2f} 秒")
        print(f"  输出通道数: {len(ch_names)}")
    
    return EDFData(
        raw_data=data,
        channel_names=ch_names,
        sampling_frequency=sfreq,
        duration=duration,
        n_channels=len(ch_names),
        n_samples=n_samples,
        file_path=file_path,
        channel_indices=channel_indices,
    )


def validate_channels(edf_data, required_channels):
    """验证EDF数据是否包含所需通道"""
    missing = []
    for ch in required_channels:
        if edf_data.get_channel_data(ch) is None:
            missing.append(ch)
    
    return len(missing) == 0, missing


def find_available_channels(edf_data):
    """查找EDF数据中可用的标准21导联"""
    found = {}
    for std_ch in STANDARD_21_CHANNELS:
        for data_ch in edf_data.channel_names:
            normalized = normalize_channel_name(data_ch)
            if normalized == std_ch or normalized.upper() == std_ch.upper():
                found[std_ch] = data_ch
                break
        
        if std_ch not in found:
            for alias, standard in CHANNEL_ALIASES.items():
                if standard == std_ch:
                    for data_ch in edf_data.channel_names:
                        normalized = normalize_channel_name(data_ch)
                        if normalized == alias or normalized.upper() == alias.upper():
                            found[std_ch] = data_ch
                            break
    
    return found
