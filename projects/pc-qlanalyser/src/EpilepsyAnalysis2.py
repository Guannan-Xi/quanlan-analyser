from PyQt5.QtWidgets import (QWidget, QPushButton, QProgressBar, QLabel, 
                           QComboBox, QPlainTextEdit, QGridLayout, QHBoxLayout, 
                           QVBoxLayout, QMessageBox, QInputDialog, QSizePolicy, QSlider,
                           QStyle, QStyleOptionSlider, QFrame)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
import os
import scipy.signal
import joblib
import logging
import pandas as pd
from datetime import datetime
import sys
from scipy.signal import stft
import pyeeg  # 添加pyeeg库用于特征提取
logging.getLogger('matplotlib').setLevel(logging.WARNING)

#------------------------算法部分--------------------------------
def compute_tkeo(epoch):
    """Compute the Teager-Kaiser Energy Operator for a 1D signal epoch."""
    tkeo = np.empty_like(epoch)
    for i in range(len(epoch)):
        if i == 0 or i == len(epoch) - 1:
            tkeo[i] = epoch[i]
        else:
            tkeo[i] = epoch[i]**2 - epoch[i+1] * epoch[i-1]
    return tkeo

# 添加自定义的滤波器函数，加强错误处理
def butter_bandpass(lowcut, highcut, fs, order=6):

    nyq = 0.5 * fs
    
    # 参数验证
    if lowcut <= 0:
        lowcut = 0.1  # 避免使用0作为低频截止点
    
    if highcut >= nyq:
        highcut = nyq - 0.1  # 确保高频截止点低于Nyquist频率
    
    if lowcut >= highcut:
        # 如果低频截止点高于或等于高频截止点，调整为可行的带宽
        logging.warning(f"Invalid filter parameters: lowcut={lowcut}, highcut={highcut}, fs={fs}")
        lowcut = max(0.1, highcut - 1.0)
    
    # 计算归一化频率
    low = lowcut / nyq
    high = highcut / nyq
    
    try:
        b, a = scipy.signal.butter(order, [low, high], btype='band')
        return b, a
    except Exception as e:
        logging.error(f"Failed to create filter with params: lowcut={lowcut}, highcut={highcut}, fs={fs}: {e}")
        # 返回一个平坦的滤波器，不会修改信号
        return [1.0], [1.0]

def butter_bandpass_filter(data, lowcut, highcut, fs, order=6):
    
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    try:
        y = scipy.signal.filtfilt(b, a, data)
        return y
    except Exception as e:
        logging.error(f"Failed to apply filter: {e}")
        return data

def extract_features_using_epochs(data_segment, fs):
    """
    使用新算法提取特征
    
    参数：
        data_segment: 形状为 [num_epochs, 1, window_length_samples] 的EEG数据段
        fs: 采样频率
    
    返回：
        numpy数组，每行是一个epoch的特征向量
    """
    num_epochs = data_segment.shape[0]
    feature_list = []
    
    # 计算Nyquist频率
    nyq = 0.5 * fs
    
    # 处理每个epoch
    for i in range(num_epochs):
        epoch = data_segment[i, 0, :]
        
        # 提取特征
        feat = {}
        # 时域特征
        feat['mean'] = np.mean(epoch)
        # Hjorth参数: pyeeg.hjorth返回(activity, mobility, complexity)
        hj_params = pyeeg.hjorth(epoch.tolist())
        feat['mobility'] = hj_params[1]  # 使用mobility参数
        
        # Teager-Kaiser能量算子(TKEO)
        tkeo_epoch = compute_tkeo(epoch)
        feat['TKEO'] = np.mean(tkeo_epoch)
        
        # 频域特征: 不同频带的绝对功率
        # 确保滤波器频率不超过Nyquist频率
        
        # Delta带(0.1 - 4 Hz)
        delta = butter_bandpass_filter(epoch, 0.1, min(4, nyq-0.1), fs, order=6)
        feat['P_delta'] = np.mean(delta**2)
        
        # Theta带(4 - 8 Hz)
        if 4 < nyq:
            theta = butter_bandpass_filter(epoch, 4, min(8, nyq-0.1), fs, order=6)
            feat['P_theta'] = np.mean(theta**2)
        else:
            feat['P_theta'] = 0
        
        # Alpha带(8 - 16 Hz)
        if 8 < nyq:
            alpha = butter_bandpass_filter(epoch, 8, min(16, nyq-0.1), fs, order=6)
            feat['P_alpha'] = np.mean(alpha**2)
        else:
            feat['P_alpha'] = 0
        
        # Beta带(16 - 32 Hz)
        if 16 < nyq:
            beta = butter_bandpass_filter(epoch, 16, min(32, nyq-0.1), fs, order=6)
            feat['P_beta'] = np.mean(beta**2)
        else:
            feat['P_beta'] = 0
        
        # Gamma带(32 - 64 Hz)
        if 32 < nyq:
            gamma_high = min(64, nyq-0.1)
            if gamma_high > 32:  # 确保带通滤波器有足够的带宽
                gamma = butter_bandpass_filter(epoch, 32, gamma_high, fs, order=6)
                feat['P_gamma'] = np.mean(gamma**2)
            else:
                feat['P_gamma'] = 0
        else:
            feat['P_gamma'] = 0
        
        # 总功率
        feat['P_total'] = np.mean(epoch**2)
        
        # 相对功率特征
        total_power = feat['P_total']
        if total_power > 0:
            feat['rel_delta'] = feat['P_delta'] / total_power
            feat['rel_theta'] = feat['P_theta'] / total_power
            feat['rel_alpha'] = feat['P_alpha'] / total_power
            feat['rel_beta'] = feat['P_beta'] / total_power
            feat['rel_gamma'] = feat['P_gamma'] / total_power
        else:
            feat['rel_delta'] = 0
            feat['rel_theta'] = 0
            feat['rel_alpha'] = 0
            feat['rel_beta'] = 0
            feat['rel_gamma'] = 0
        
        # 使用pyeeg计算的分形维数
        feat['pfd'] = pyeeg.pfd(epoch.tolist())
        
        # 偏度和峭度
        feat['skew'] = scipy.stats.skew(epoch)
        feat['kurtosis'] = scipy.stats.kurtosis(epoch)
        
        # 方差
        feat['var'] = np.var(epoch)
        
        # 信号包络：解析信号幅值的平均值
        analytic_signal = scipy.signal.hilbert(epoch)
        envelope = np.abs(analytic_signal)
        feat['envelope'] = np.mean(envelope)
        
        feature_list.append(feat)
    
    # 将特征列表转换为数组
    feature_columns = ['mean', 'mobility', 'TKEO', 
                     'P_delta', 'P_theta', 'P_alpha', 
                     'P_beta', 'P_gamma', 'P_total', 
                     'rel_delta', 'rel_theta', 'rel_alpha', 'rel_beta', 
                     'rel_gamma', 'pfd', 'skew', 'kurtosis', 'var', 'envelope']
    
    features_df = pd.DataFrame(feature_list)
    X = features_df[feature_columns].values
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return np.clip(X, -1e6, 1e6).astype(np.float32)


def detect_seizures(classifications, data, sfreq, epoch_length=1.0, start_time_ts=None, min_no_seizure_epochs=3):
    """
    检测癫痫发作事件
    
    参数：
        classifications: 模型分类结果
        data: 原始EEG数据
        sfreq: 采样频率
        epoch_length: 每个epoch的长度（秒）
        start_time_ts: 开始时间的时间戳
        min_no_seizure_epochs: 两次发作之间的最小非发作epoch数
    
    返回：
        seizure_info_list: 癫痫发作信息列表
        seizure_per_minute_df: 每分钟发作频率信息的字典，包含 'Minute', 'Seizure Count', 'UTC Time' 键
    """
    try:
        if start_time_ts is None:
            start_time_ts = datetime.now().timestamp()
        
        seizure_info_list = []
        seizure_per_minute = {}
        
        # 初始化变量
        in_seizure = False
        seizure_start_idx = 0
        seizure_start_time = 0
        no_seizure_count = 0
        epoch_count = len(classifications)
        total_minutes = int(np.ceil(len(data) / sfreq / 60))
        
        # 初始化每分钟的发作计数
        for minute in range(total_minutes):
            seizure_per_minute[minute] = 0
        
        # 遍历所有的分类结果
        for i, is_seizure in enumerate(classifications):
            current_time = start_time_ts + i * epoch_length
            current_minute = int((current_time - start_time_ts) // 60)
            
            # 更新每分钟发作计数
            if current_minute not in seizure_per_minute:
                seizure_per_minute[current_minute] = 0
            
            if is_seizure == 1:
                # 记录每分钟发作数
                seizure_per_minute[current_minute] += 1
                
                # 如果当前不在发作状态，开始新的发作
                if not in_seizure:
                    in_seizure = True
                    seizure_start_idx = i
                    seizure_start_time = current_time
                    no_seizure_count = 0
            else:
                # 如果当前在发作状态，增加非发作计数
                if in_seizure:
                    no_seizure_count += 1
                    
                    # 如果非发作持续足够长，结束当前发作
                    if no_seizure_count >= min_no_seizure_epochs or i == epoch_count - 1:
                        # 计算发作持续时间
                        seizure_end_idx = i - no_seizure_count
                        if seizure_end_idx < seizure_start_idx:
                            seizure_end_idx = seizure_start_idx  # 至少包含一个发作epoch
                            
                        seizure_end_time = start_time_ts + seizure_end_idx * epoch_length
                        seizure_duration = seizure_end_time - seizure_start_time
                        
                        # 计算发作期间的最大振幅和RMS
                        seizure_start_sample = int(seizure_start_idx * epoch_length * sfreq)
                        seizure_end_sample = int((seizure_end_idx + 1) * epoch_length * sfreq)
                        if seizure_end_sample > len(data):
                            seizure_end_sample = len(data)
                            
                        seizure_data = data[seizure_start_sample:seizure_end_sample]
                        if len(seizure_data) > 0:
                            max_amp = np.max(np.abs(seizure_data))
                            rms_value = np.sqrt(np.mean(seizure_data ** 2))
                            max_amp = round(float(max_amp), 2)
                            rms_value = round(float(rms_value), 2)
                        else:
                            max_amp = 0
                            rms_value = 0
                        
                        # 计算时间戳和持续时间
                        start_timestamp = seizure_start_idx * epoch_length
                        end_timestamp = seizure_end_idx * epoch_length
                        duration_sec = round(end_timestamp - start_timestamp, 1)
                        
                        # 计算UTC时间
                        start_time_utc = start_timestamp + start_time_ts
                        end_time_utc = end_timestamp + start_time_ts
                        
                        # 添加发作信息
                        seizure_info = {
                            '癫痫发作编号': len(seizure_info_list) + 1,
                            'RMS值': rms_value,
                            '最大值': max_amp,
                            '开始时间戳 (s)': start_timestamp,
                            '结束时间戳 (s)': end_timestamp,
                            '开始时间 (UTC)': datetime.utcfromtimestamp(start_time_utc),
                            '结束时间 (UTC)': datetime.utcfromtimestamp(end_time_utc),
                            '持续时间 (s)': duration_sec,
                            '起始 epoch': seizure_start_idx,
                            '结束 epoch': seizure_end_idx
                        }
                        seizure_info_list.append(seizure_info)
                        
                        # 重置状态
                        in_seizure = False
        
        # 处理最后一个epoch如果仍在发作
        if in_seizure:
            seizure_end_idx = epoch_count - 1
            seizure_end_time = start_time_ts + seizure_end_idx * epoch_length
            seizure_duration = seizure_end_time - seizure_start_time
            
            seizure_start_sample = int(seizure_start_idx * epoch_length * sfreq)
            seizure_end_sample = int((seizure_end_idx + 1) * epoch_length * sfreq)
            if seizure_end_sample > len(data):
                seizure_end_sample = len(data)
            
            if seizure_start_sample < seizure_end_sample:
                seizure_data = data[seizure_start_sample:seizure_end_sample]
                max_amp = np.max(np.abs(seizure_data))
                rms_value = np.sqrt(np.mean(seizure_data ** 2))
                max_amp = round(float(max_amp), 2)
                rms_value = round(float(rms_value), 2)
                
                start_timestamp = seizure_start_idx * epoch_length
                end_timestamp = seizure_end_idx * epoch_length
                duration_sec = round(end_timestamp - start_timestamp, 1)
                
                # 计算UTC时间
                start_time_utc = start_timestamp + start_time_ts
                end_time_utc = end_timestamp + start_time_ts
                
                seizure_info = {
                    '癫痫发作编号': len(seizure_info_list) + 1,
                    'RMS值': rms_value,
                    '最大值': max_amp,
                    '开始时间戳 (s)': start_timestamp,
                    '结束时间戳 (s)': end_timestamp,
                    '开始时间 (UTC)': datetime.utcfromtimestamp(start_time_utc),
                    '结束时间 (UTC)': datetime.utcfromtimestamp(end_time_utc),
                    '持续时间 (s)': duration_sec,
                    '起始 epoch': seizure_start_idx,
                    '结束 epoch': seizure_end_idx
                }
                seizure_info_list.append(seizure_info)
        
        # 创建每分钟统计数据的字典
        seizure_per_minute_df = {
            'Minute': list(seizure_per_minute.keys()),
            'Seizure Count': list(seizure_per_minute.values()),
            'UTC Time': [datetime.utcfromtimestamp(start_time_ts + minute * 60) for minute in
                        seizure_per_minute.keys()]
        }
        
        return seizure_info_list, seizure_per_minute_df
        
    except Exception as e:
        logging.error(f"检测癫痫发作时出错: {e}", exc_info=True)
        return [], {
            'Minute': [],
            'Seizure Count': [],
            'UTC Time': []
        }

class Thread_run_analysis(QThread):
    signal = pyqtSignal('PyQt_PyObject')

    def __init__(self):
        QThread.__init__(self)
        self.raw_processed = None
        self.epoch_length = 1.0
        self.eeg_channel = None
        self.save_path = None
        self.timestamp_dir = None
    
    
    def calculate_spectrogram(self):
        """计算EEG信号的时频图数据"""
        try:
            # 检查数据是否存在
            if not hasattr(self, 'eeg_data'):
                logging.error("EEG data not found")
                return None
            
            # 获取采样率
            sfreq = self.raw_processed.info['sfreq']
            logging.info(f"Calculating spectrogram with sampling rate: {sfreq}Hz")
            
            # 打印数据基本信息
            logging.info(f"EEG data shape: {self.eeg_data.shape}")
            
            # 设置时频图参数
            nperseg = int(sfreq * 4)  
            noverlap = int(nperseg * 0.9)  
            logging.info(f"Spectrogram parameters - nperseg: {nperseg}, noverlap: {noverlap}")
            
                      
            # 更换时频图计算方法，消除时频图开头的空白
            f, t, Zxx = stft(self.eeg_data, fs=sfreq, nperseg=nperseg, noverlap=noverlap, boundary='zeros')
        
            
            # 计算对数功率谱
            Sxx = 10 * np.log10(np.abs(Zxx) + 1e-10)
            
            # 筛选感兴趣的频率范围
            good_freqs = np.logical_and(f >= 0.5, f <= 50)
            Sxx = Sxx[good_freqs, :]
            f = f[good_freqs]
            
            logging.info(f"Filtered spectrogram shape - f: {f.shape}, Sxx: {Sxx.shape}")
            
            # 计算颜色范围
            vmin = np.percentile(Sxx, 10)
            vmax = np.percentile(Sxx, 99)
            logging.info(f"Color range - vmin: {vmin}, vmax: {vmax}")
            
            return {
                'frequencies': f,
                'times': t,
                'power': Sxx,
                'vmin': vmin,
                'vmax': vmax
            }
        except Exception as e:
            logging.exception("Spectrogram calculation error")  # 记录完整堆栈跟踪
            return None  # 静默失败，让主线程处理

    def detect_high_energy_bands_in_thread(self, spectrogram_data, df_score, 
                                          threshold_percentile=99, 
                                          absolute_power_threshold=15.0,  # 绝对功率阈值(dB)
                                          min_duration_sec=0.1):
        """
        在线程中检测时频图中的高能量垂直带
        
        参数:
            spectrogram_data: 时频图数据
            df_score: 分数DataFrame
            threshold_percentile: 用于确定高能量的百分位阈值
            absolute_power_threshold: 绝对功率阈值 (dB)，直接与功率谱比较
            min_duration_sec: 高能量带的最小持续时间(秒)
        """
        try:
            if spectrogram_data is None or 'power' not in spectrogram_data:
                logging.error("Invalid spectrogram data")
                return [], 0
                
            # 获取功率数据和时间轴
            power = spectrogram_data['power']  
            times = spectrogram_data['times']
            
            # 计算时间分辨率
            if len(times) > 1:
                time_resolution = times[1] - times[0]
            else:
                time_resolution = 0.01
                
            # 最小持续时间对应的采样点数
            min_duration_points = int(min_duration_sec / time_resolution)
            
            logging.info(f"时间分辨率: {time_resolution:.4f}秒/点, 最小持续点数: {min_duration_points}点")
            
            # 计算每个时间点的平均功率
            mean_power_per_time = np.mean(power, axis=0)
            
            # 计算百分位阈值
            percentile_threshold = np.percentile(mean_power_per_time, threshold_percentile)
            
            logging.info(f"高能量检测阈值: 百分位={percentile_threshold:.2f}, 绝对={absolute_power_threshold:.2f}")
            
            # 创建两个掩码：一个用于百分位阈值，一个用于绝对阈值
            percentile_mask = mean_power_per_time > percentile_threshold
            
            # 对于绝对阈值，检查每个时间点上是否有任何频率分量超过绝对阈值
            absolute_mask = np.max(power, axis=0) > absolute_power_threshold
            
            # 合并两个掩码 - 只有同时满足百分位和绝对阈值的时间点才被标记
            high_energy_mask = np.logical_and(percentile_mask, absolute_mask)
            
            # 找出连续的高能量段
            high_energy_segments = []
            in_segment = False
            segment_start = 0
            
            for i, is_high in enumerate(high_energy_mask):
                if is_high and not in_segment:
                    # 开始一个新的高能量段
                    in_segment = True
                    segment_start = i
                elif not is_high and in_segment:
                    # 结束当前高能量段
                    segment_end = i - 1
                    segment_length = segment_end - segment_start + 1
                    
                    # 只保留持续时间足够长的段
                    if segment_length >= min_duration_points:
                        high_energy_segments.append((segment_start, segment_end))
                    
                    in_segment = False
                    
            # 处理最后一个可能的段
            if in_segment:
                segment_end = len(high_energy_mask) - 1
                segment_length = segment_end - segment_start + 1
                
                if segment_length >= min_duration_points:
                    high_energy_segments.append((segment_start, segment_end))
            
            # 如果没有找到符合条件的高能量段
            if not high_energy_segments:
                logging.info(f"未检测到同时满足百分位阈值和绝对阈值且持续时间大于{min_duration_sec}秒的高能量带")
                return [], 0
            
            logging.info(f"检测到{len(high_energy_segments)}个持续高能量段")
            
            # 获取所有高能量段的时间点
            high_energy_indices = []
            for start, end in high_energy_segments:
                high_energy_indices.extend(range(start, end + 1))
            
            # 记录检测信息
            for i, (start, end) in enumerate(high_energy_segments):
                duration = (end - start + 1) * time_resolution
                start_time = times[start]
                end_time = times[end]
                max_power = np.max(power[:, start:end+1])
                logging.info(f"高能量段 #{i+1}: 开始={start_time:.2f}秒, 结束={end_time:.2f}秒, 持续={duration:.2f}秒, 最大功率={max_power:.2f}dB")
            
            # 获取对应的时间点
            high_energy_times = times[high_energy_indices]
            
            # 计算对应的epoch
            high_energy_epochs = []
            for time_point in high_energy_times:
                epoch = int(time_point // self.epoch_length)
                if epoch not in high_energy_epochs and epoch < len(df_score):
                    high_energy_epochs.append(epoch)
            
            # 标记这些epoch为癫痫发作
            original_seizure_count = sum(df_score['Stage_Code'].values)
            marked_count = 0
            
            for epoch in high_energy_epochs:
                if epoch < len(df_score) and df_score.at[epoch, 'Stage_Code'] == 0:
                    df_score.at[epoch, 'Stage_Code'] = 1
                    df_score.at[epoch, 'Stage'] = 'Seizure'
                    marked_count += 1
            
            logging.info(f"检测到{len(high_energy_epochs)}个包含持续高能量带的epochs")
            logging.info(f"标记了{marked_count}个额外的epochs为癫痫发作")
            logging.info(f"癫痫发作epochs总数: {original_seizure_count} -> {original_seizure_count + marked_count}")
            
            return high_energy_epochs, marked_count
            
        except Exception as e:
            logging.error(f"检测高能量带时出错: {e}", exc_info=True)
            return [], 0

    def run(self):
        try:
            progress = 0
            self.signal.emit([progress, "Analysis started"])            
            
            if self.epoch_length == 3.0:
                model_path = os.path.join(os.path.dirname(__file__), 'newEpilepsy', 'model_n762_3s.sav')
                scaler_path = os.path.join(os.path.dirname(__file__), 'newEpilepsy', 'scaler_n762_3s.sav')
                self.signal.emit([progress, "Loading 3-second epoch model..."])
            elif self.epoch_length == 5.0:
                model_path = os.path.join(os.path.dirname(__file__), 'newEpilepsy', 'model_n1814_5s.sav')
                scaler_path = os.path.join(os.path.dirname(__file__), 'newEpilepsy', 'scaler_n1814_5s.sav')
                self.signal.emit([progress, "Loading 5-second epoch model..."])
            else:
                # 默认使用5秒模型
                model_path = os.path.join(os.path.dirname(__file__), 'newEpilepsy', 'model_n1814_5s.sav')
                scaler_path = os.path.join(os.path.dirname(__file__), 'newEpilepsy', 'scaler_n1814_5s.sav')
                self.signal.emit([progress, f"Using default 5-second model for {self.epoch_length}-second epochs..."])
            
            try:
               
                # 加载模型和标准化器
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                
                # 处理XGBoost模型的特殊属性
                if not hasattr(self.model, 'early_stopping_rounds'):
                    setattr(self.model, 'early_stopping_rounds', None)
                
                if not hasattr(self.model, 'callbacks'):
                    setattr(self.model, 'callbacks', [])
                
                if hasattr(self.model, 'use_label_encoder'):
                    self.model.use_label_encoder = False
                else:
                    setattr(self.model, 'use_label_encoder', False)
                    
                progress = 10
                self.signal.emit([progress, "Model loaded successfully"])
            except Exception as e:
                logging.error(f"Error loading model: {e}")
                self.signal.emit([progress, f"Error loading model: {e}"])
                raise

            # 确保raw_processed存在
            if self.raw_processed is None:
                raise ValueError("No data loaded")

            # 确保采样频率足够高，至少需要100Hz才能正确提取频带特征
            original_sfreq = self.raw_processed.info['sfreq']
            if original_sfreq < 100:
                logging.warning(f"采样频率过低({original_sfreq}Hz)，这可能影响特征提取。尝试使用更高采样率的数据。")
                self.signal.emit([progress, f"警告：采样频率较低({original_sfreq}Hz)，可能影响分析质量"])
            
            # 重采样到100Hz
            # self.raw_processed.resample(sfreq=100)
            # logging.info(f"数据已从{original_sfreq}Hz重采样至100Hz")

            # 使用时间戳目录
            self.timestamp_dir = self.raw_processed.info.get('description')
            if not self.timestamp_dir:
                raise ValueError("No valid save path found in raw.info['description']")
            self.save_path = os.path.join(self.timestamp_dir, 'Epilepsy Analysis')
            os.makedirs(self.save_path, exist_ok=True)

            # 获取所有通道数据
            self.eeg_data = self.raw_processed.get_data()[self.eeg_channel]
            self.emg_data = self.raw_processed.get_data()[self.emg_channel]
            self.acc_data = self.raw_processed.get_data()[self.acc_channel] * 1e-6
            self.sfreq = self.raw_processed.info['sfreq']
            
            # 计算时频图数据 - 在特征提取之前计算
            progress = 20
            self.signal.emit([progress, "Calculating spectrogram..."])
            self.spectrogram_data = self.calculate_spectrogram()
            if self.spectrogram_data is None:
                logging.warning("Failed to calculate spectrogram")
            else:
                logging.info("Spectrogram calculation completed")
            
            # 特征提取和预测
            progress = 30
            self.signal.emit([progress, "Extracting features..."])
            
            # 重新组织数据为epochs
            epoch_samples = int(self.epoch_length * self.sfreq)
            n_epochs = len(self.eeg_data) // epoch_samples
            eeg_data_epochs = self.eeg_data[:n_epochs * epoch_samples]
            eeg_data_epochs = eeg_data_epochs.reshape(n_epochs, 1, epoch_samples)

            # 使用新算法提取特征
            features = extract_features_using_epochs(eeg_data_epochs, self.sfreq)
            
            # 使用加载的标准化器缩放特征
            features_scaled = self.scaler.transform(features)
            
            progress = 60
            self.signal.emit([progress, "Making predictions..."])

            # 使用新模型进行预测
            predictions_proba = self.model.predict_proba(features_scaled)[:, 1]
            predictions = (predictions_proba >= 0.5).astype(int)

        
            logging.info(f"预测完成，共{len(predictions)}个时段，其中{sum(predictions)}个被识别为癫痫")

            # 创建结果DataFrame
            progress = 70
            self.signal.emit([progress, "Creating score file..."])

            df_score = pd.DataFrame({
                "Epoch No.": list(range(len(predictions))),
                "Stage_Code": predictions
            })
            
            # 添加阶段名称
            stage_code = {0: "Normal", 1: "Seizure"}
            df_score["Stage"] = df_score["Stage_Code"].map(stage_code)
            
            # 保存初始分期结果
            if self.save_path:
                # 直接创建最终的分期结果文件路径
                score_filepath = os.path.join(
                    self.save_path,
                    f"epoch_length_{self.epoch_length}_sec_scores.csv"
                )
                
                # 如果有时频图数据，添加基于高能量带检测的癫痫标记
                if self.spectrogram_data is not None:
                    progress = 80
                    self.signal.emit([progress, "Detecting high energy bands in spectrogram..."])
                    
                    try:
                        # 使用线程内的方法检测高能量带并标记
                        _, marked_count = self.detect_high_energy_bands_in_thread(
                            self.spectrogram_data, 
                            df_score,
                            threshold_percentile=99.2,      # 高百分位阈值
                            absolute_power_threshold=15.0,  # 绝对功率阈值(dB)
                            min_duration_sec=0.05            # 最小持续时间(秒)
                        )
                        
                        # 记录检测结果
                        if marked_count > 0:
                            self.signal.emit([progress, f"Marked {marked_count} additional epochs as seizure based on high energy bands"])
                    except Exception as e:
                        logging.error(f"Error in high energy band detection: {e}", exc_info=True)
                        self.signal.emit([progress, f"Warning: High energy band detection failed: {str(e)}"])
                
                # 保存最终的分期结果
                df_score.to_csv(score_filepath, index=False)
                self.signal.emit([progress, f"Saved score file to: {score_filepath}"])
            
            # 在完成预测和动态阈值筛选后，添加癫痫检测代码
            progress = 85
            self.signal.emit([progress, "Detecting seizures..."])

            # 获取测量时间
            meas_date = self.raw_processed.info.get('meas_date', None)
            if meas_date is None:
                start_time_ts = datetime.now().timestamp()
            else:
                start_time_ts = (meas_date[0] + meas_date[1] * 1e-6 
                               if isinstance(meas_date, tuple) 
                               else meas_date.timestamp())

            # 检测癫痫发作
            seizure_info, seizure_per_minute_df = detect_seizures(
                df_score['Stage_Code'].values,
                self.eeg_data,
                self.sfreq,
                epoch_length=self.epoch_length,
                start_time_ts=start_time_ts,
                min_no_seizure_epochs=3
            )

            progress = 90
            self.signal.emit([progress, "Saving results..."])

            # 保存癫痫发作信息到Excel文件
            if seizure_info:
                try:
                    # 创建DataFrame
                    seizure_df = pd.DataFrame(seizure_info)
                    
                    # 创建每分钟发作频率的DataFrame
                    minute_df = pd.DataFrame({
                        '分钟': seizure_per_minute_df['Minute'],
                        '癫痫发作次数': seizure_per_minute_df['Seizure Count'],
                        'UTC 时间': seizure_per_minute_df['UTC Time']
                    })
                    
                    # 保存到Excel文件
                    excel_path = os.path.join(self.save_path, 'seizure_info.xlsx')
                    
                    with pd.ExcelWriter(excel_path, engine='openpyxl', mode='w') as writer:
                        seizure_df.to_excel(writer, sheet_name='癫痫发作详情', index=False)
                        minute_df.to_excel(writer, sheet_name='每分钟发作频率', index=False)
                    
                    self.signal.emit([progress, f"Results saved to: {excel_path}"])
                except Exception as e:
                    logging.error(f"Error saving Excel: {str(e)}")
                    # 尝试保存为CSV作为备选
                    try:
                        csv_path = os.path.join(self.save_path, 'seizure_info.csv')
                        seizure_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                        self.signal.emit([progress, f"Results saved as CSV: {csv_path}"])
                    except Exception as csv_error:
                        logging.error(f"CSV save error: {str(csv_error)}")

            # 保存结果到内存以供后续使用
            self.df_score = df_score
            self.seizure_info = seizure_info
            self.seizure_per_minute = seizure_per_minute_df
            
            progress = 100
            self.signal.emit([progress, "Analysis completed"])

        except Exception as e:
            logging.exception("Analysis thread error")  
            self.signal.emit([-1, str(e)])  # 发送错误信号
            return  



class Ui_epilepsy_analysis(QWidget):
    def __init__(self):
        super().__init__()
        self.raw_processed = None
        self.map_colors = {0: "blue", 1: "red"}
        self.map_stages = {0: "Normal", 1: "Seizure"}
        self.thread_run = Thread_run_analysis()
        self.thread_run.signal.connect(self.update_progress)
        self.df_score = None
        self.current_selected_epoch = None
        self.highlight_lines = []
        self.n_epochs = 0
        self.epochlabels = []
        self.epoch_length = 5.0
        self.epoch_start = 0
        self.setup_logging()
        # 设置matplotlib
        plt.rcParams['agg.path.chunksize'] = 10000
        plt.rcParams['path.simplify'] = True
        plt.rcParams['path.simplify_threshold'] = 0.5
        
        # 添加全局异常处理
        sys.excepthook = self.handle_exception

    def setup_logging(self):
        """设置日志记录"""
        try:
            # 使用用户文档目录
            user_docs = os.path.expanduser('~\Documents')
            log_dir = os.path.join(user_docs, 'AR_Analyser_Logs')
            os.makedirs(log_dir, exist_ok=True)
            
            log_path = os.path.join(log_dir, 'epilepsy_analysis.log')
            
            # 配置日志记录
            logging.basicConfig(
                filename=log_path,
                level=logging.DEBUG,
                format='%(asctime)s - %(levelname)s - %(message)s',
                force=True  # 强制重新配置日志
            )
            
            # 添加一个控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            logging.getLogger().addHandler(console_handler)
            
            # 测试日志是否正常工作
            logging.info("=== New Session Started ===")
            logging.info(f"Log file created at: {log_path}")
            
        except Exception as e:
            # 确保即使日志设置失败，我们也能看到错误信息
            print(f"Failed to setup logging: {str(e)}")
            # 尝试写入一个简单的错误文件
            try:
                with open(os.path.join(user_docs, 'ar_analyser_error.txt'), 'w') as f:
                    f.write(f"Logging setup failed: {str(e)}")
            except:
                pass

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """全局异常处理器"""
        logging.error("Uncaught exception", 
                     exc_info=(exc_type, exc_value, exc_traceback))
        # 将错误信息添加到文本框，而不是显示弹窗
        error_msg = f"Error: {str(exc_value)}"
        if hasattr(self, 'textbox'):
            self.textbox.appendPlainText(error_msg)

    def setupUi(self, epilepsy_analysis):
        epilepsy_analysis.setObjectName("epilepsy_analysis")
        epilepsy_analysis.resize(1600, 1000)
        epilepsy_analysis.setWindowTitle("Epilepsy Analysis - AI based model")

        # 创建主布局
        self.main_layout = QHBoxLayout(epilepsy_analysis)

        # 左侧面板
        self.setup_left_panel()

        # 右侧面板
        self.setup_right_panel()

        # 连接信号
        self.connect_signals()

    def setup_left_panel(self):
        self.left_panel = QWidget()
        self.left_panel.setFixedWidth(400)
        left_layout = QVBoxLayout(self.left_panel)

        # Channel Selection
        
        channel_selection_layout = QHBoxLayout()
        self.label_channel_selection = QLabel("Channel Selection:")
        self.label_channel_selection.setStyleSheet("font: 10pt;")
        channel_selection_layout.addWidget(self.label_channel_selection)
        

        # EEG Channel
        eeg_layout = QHBoxLayout()
        self.label_channel = QLabel("EEG:")
        self.label_channel.setStyleSheet("font: 10pt;")
        self.combobox_channel = QComboBox()
        eeg_layout.addWidget(self.label_channel)
        eeg_layout.addWidget(self.combobox_channel)
        
        # EMG Channel
        emg_layout = QHBoxLayout()
        self.label_emg_channel = QLabel("EMG:")
        self.label_emg_channel.setStyleSheet("font: 10pt;")
        self.combobox_emg_channel = QComboBox()
        emg_layout.addWidget(self.label_emg_channel)
        emg_layout.addWidget(self.combobox_emg_channel)
        
        # ACC Channel
        acc_layout = QHBoxLayout()
        self.label_acc_channel = QLabel("ACC:")
        self.label_acc_channel.setStyleSheet("font: 10pt;")
        self.combobox_acc_channel = QComboBox()
        acc_layout.addWidget(self.label_acc_channel)
        acc_layout.addWidget(self.combobox_acc_channel)

        # Epoch Length
        epoch_length_layout = QHBoxLayout()
        self.label_epoch_length = QLabel("Epoch Length (sec):")
        self.label_epoch_length.setStyleSheet("font: 10pt;")
        self.combobox_epoch_length = QComboBox()
        self.combobox_epoch_length.addItems(["3", "5"])
        self.combobox_epoch_length.setStyleSheet("font: 10pt;")
        self.combobox_epoch_length.setCurrentText("5")  
        epoch_length_layout.addWidget(self.label_epoch_length)
        epoch_length_layout.addWidget(self.combobox_epoch_length)

        # Progress
        progress_layout = QVBoxLayout()
        self.label_progress = QLabel("Progress:")  # 添加Progress标签
        self.label_progress.setStyleSheet("font: 10pt;")
        self.progressBar = QProgressBar()
        self.label_status = QLabel("")
        progress_layout.addWidget(self.label_progress)
        progress_layout.addWidget(self.progressBar)
        progress_layout.addWidget(self.label_status)

        # Buttons
        self.button_analyze = QPushButton("Analyze and Save")
        self.button_analyze.setEnabled(False)
        self.button_analyze.setStyleSheet("font: 10pt;")

        self.button_visualize = QPushButton("Visualize")
        self.button_visualize.setStyleSheet("font: 10pt;")
        self.button_visualize.setEnabled(False)  # 初始状态禁用

        # Add Abort button after Visualize button
        self.button_abort = QPushButton("Abort")
        self.button_abort.setStyleSheet("font: 10pt;")
        self.button_abort.setEnabled(False)  # Initially disabled

        # Log TextBox
        self.textbox = QPlainTextEdit()
        self.textbox.setReadOnly(True)

        # Add to layout
        left_layout.addLayout(epoch_length_layout)
        left_layout.addLayout(channel_selection_layout)
        left_layout.addLayout(eeg_layout)
        left_layout.addLayout(emg_layout)
        left_layout.addLayout(acc_layout)        
        left_layout.addLayout(progress_layout)
        left_layout.addWidget(self.button_analyze)
        left_layout.addWidget(self.button_visualize)
        left_layout.addWidget(self.button_abort)  # Add abort button
        left_layout.addWidget(self.textbox)

        self.main_layout.addWidget(self.left_panel)

    def setup_right_panel(self):
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)

        # 顶部控制区
        top_controls = QHBoxLayout()

        # Navigation Buttons
        nav_buttons = QHBoxLayout()
        self.button_previous_more = QPushButton("<<")
        self.button_previous_more.setStyleSheet("font: 10pt;")
        self.button_previous_more.setEnabled(False)
        
        self.button_previous = QPushButton("<")
        self.button_previous.setStyleSheet("font: 10pt;")
        self.button_previous.setEnabled(False)
        
        self.button_goto_epoch = QPushButton("Go to Epoch")
        self.button_goto_epoch.setStyleSheet("font: 10pt;")
        self.button_goto_epoch.setEnabled(False)
        
        self.button_next = QPushButton(">")
        self.button_next.setStyleSheet("font: 10pt;")
        self.button_next.setEnabled(False)
        
        self.button_next_more = QPushButton(">>")
        self.button_next_more.setStyleSheet("font: 10pt;")
        self.button_next_more.setEnabled(False)

        nav_buttons.addWidget(self.button_previous_more)
        nav_buttons.addWidget(self.button_previous)
        nav_buttons.addWidget(self.button_goto_epoch)
        nav_buttons.addWidget(self.button_next)
        nav_buttons.addWidget(self.button_next_more)

        # Epochs per page selector
        epochs_control = QHBoxLayout()
        self.label_epochs_per_page = QLabel("Epochs per page:")
        self.label_epochs_per_page.setStyleSheet("font: 10pt;")
        self.label_epochs_per_page.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        epochs_control.addWidget(self.label_epochs_per_page)
        epochs_control.setSpacing(20)  # 设置组件之间的间距
        
        self.combobox_epochs_per_page = QComboBox()
        self.combobox_epochs_per_page.setStyleSheet("font: 10pt;")
        self.combobox_epochs_per_page.addItems(["All","200", "100", "50", "30", "20", "10", "5", "3"])
        self.combobox_epochs_per_page.setEnabled(False)
        epochs_control.addWidget(self.combobox_epochs_per_page)
        
        
        # Stage editor
        stage_selection = QHBoxLayout()
        self.label_stage = QLabel("Stage Edit and Save:")
        self.label_stage.setStyleSheet("font: 10pt;")
        self.label_stage.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        stage_selection.addWidget(self.label_stage)
        stage_selection.setSpacing(20)
        
        self.combobox_stage = QComboBox()
        self.combobox_stage.setStyleSheet("font: 10pt;")
        self.combobox_stage.addItems(["Normal", "Seizure"])
        stage_selection.addWidget(self.combobox_stage)

        # Add amplitude range selectors
        amplitude_control = QHBoxLayout()
        amplitude_control.addSpacing(100)  # 添加左侧间距
        
        # EEG amplitude selector
        self.label_amplitude = QLabel("EEG Range (uV):")
        self.label_amplitude.setStyleSheet("font: 10pt;")
        self.label_amplitude.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.combobox_amplitude = QComboBox()
        self.combobox_amplitude.setStyleSheet("font: 10pt;")
        self.combobox_amplitude.addItems(["±50", "±100", "±200", "±500", "±1000", "Auto"])
        self.combobox_amplitude.setCurrentText("±500")
        amplitude_control.addWidget(self.label_amplitude)
        amplitude_control.addWidget(self.combobox_amplitude)
        
        amplitude_control.addSpacing(20)  # 添加间距
        
        # EMG amplitude selector
        self.label_emg_amplitude = QLabel("EMG Range (uV):")
        self.label_emg_amplitude.setStyleSheet("font: 10pt;")
        self.label_emg_amplitude.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.combobox_emg_amplitude = QComboBox()
        self.combobox_emg_amplitude.setStyleSheet("font: 10pt;")
        self.combobox_emg_amplitude.addItems(["±50", "±100", "±200", "±500", "±1000", "Auto"])
        self.combobox_emg_amplitude.setCurrentText("±200")
        amplitude_control.addWidget(self.label_emg_amplitude)
        amplitude_control.addWidget(self.combobox_emg_amplitude)
        
        amplitude_control.addSpacing(20)  # 添加间距
        
        # ACC amplitude selector
        self.label_acc_amplitude = QLabel("ACC Range (mG):")
        self.label_acc_amplitude.setStyleSheet("font: 10pt;")
        self.label_acc_amplitude.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.combobox_acc_amplitude = QComboBox()
        self.combobox_acc_amplitude.setStyleSheet("font: 10pt;")
        self.combobox_acc_amplitude.addItems(["±500", "±1000", "±2000", "±4000", "Auto"])
        self.combobox_acc_amplitude.setCurrentText("±2000")
        amplitude_control.addWidget(self.label_acc_amplitude)
        amplitude_control.addWidget(self.combobox_acc_amplitude)

        # Add all controls to top layout
        top_controls.addLayout(nav_buttons)
        top_controls.addLayout(epochs_control)
        top_controls.addLayout(stage_selection)
        top_controls.addLayout(amplitude_control)
        right_layout.addLayout(top_controls)

        # Figure
        self.figure = Figure(dpi=20)
        self.figure.set_size_inches(15, 8)
        self.canvas = FigureCanvasQTAgg(self.figure)
        right_layout.addWidget(self.canvas)

        # Navigation Slider
        slider_layout = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setEnabled(False)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(1)
        self.slider.mousePressEvent = self.slider_mouse_press
        slider_layout.addWidget(self.slider)
        right_layout.addLayout(slider_layout)

        self.main_layout.addWidget(self.right_panel)

    def connect_signals(self):
        # 原有的信号连接
        # Add new signal connections for amplitude ranges
        self.combobox_amplitude.currentTextChanged.connect(self.update_signal_range)
        self.combobox_emg_amplitude.currentTextChanged.connect(self.update_signal_range)
        self.combobox_acc_amplitude.currentTextChanged.connect(self.update_signal_range)
        self.button_analyze.clicked.connect(self.run_analysis)
        self.button_visualize.clicked.connect(self.plot_results)
        self.button_previous_more.clicked.connect(self.update_display_previous_more)
        self.button_previous.clicked.connect(self.update_display_previous)
        self.button_goto_epoch.clicked.connect(self.update_display_goto_epoch)
        self.button_next.clicked.connect(self.update_display_next)
        self.button_next_more.clicked.connect(self.update_display_next_more)
        self.combobox_epochs_per_page.currentTextChanged.connect(self.update_display_n_epochs)
        self.combobox_stage.currentTextChanged.connect(self.user_edit_stage)
        self.combobox_epoch_length.currentTextChanged.connect(self.update_epoch_length)
        
        self.slider.valueChanged.connect(self.on_slider_changed)
       
        
        # Add new signal connection for amplitude range
        self.combobox_amplitude.currentTextChanged.connect(self.update_signal_range)

        self.button_abort.clicked.connect(self.abort_analysis)

    def import_raw(self, raw, selected_channel=None):
        self.raw_processed = raw
        self.thread_run.raw_processed = self.raw_processed
        
        if raw is not None:
            self.button_analyze.setEnabled(True)
            
            # 更新通道选择下拉菜单
            ch_names = raw.ch_names
            
            # Clear and update all channel comboboxes
            self.combobox_channel.clear()
            self.combobox_emg_channel.clear()
            self.combobox_acc_channel.clear()
            
            self.combobox_channel.addItems(ch_names)
            self.combobox_emg_channel.addItems(ch_names)
            self.combobox_acc_channel.addItems(ch_names)
            
            # Set default selections
            default_eeg = "EEG3"
            default_emg = "EEG1"  
            default_acc = "ACC1"  

            if default_eeg in ch_names:
                self.combobox_channel.setCurrentText(default_eeg)
            elif selected_channel is not None:
                self.combobox_channel.setCurrentIndex(selected_channel)
                
            if default_emg in ch_names:
                self.combobox_emg_channel.setCurrentText(default_emg)
                
            if default_acc in ch_names:
                self.combobox_acc_channel.setCurrentText(default_acc)
        

    def run_analysis(self):
        try:
            # Enable abort button when analysis starts
            self.button_abort.setEnabled(True)
            self.button_analyze.setEnabled(False)
            
            # 获取选择的通道
            selected_channel = self.combobox_channel.currentIndex()
            selected_emg = self.combobox_emg_channel.currentIndex()
            selected_acc = self.combobox_acc_channel.currentIndex()
            
            self.thread_run.eeg_channel = selected_channel
            self.thread_run.emg_channel = selected_emg
            self.thread_run.acc_channel = selected_acc
            
            # 获取epoch长度
            self.epoch_length = float(self.combobox_epoch_length.currentText())
            self.thread_run.epoch_length = self.epoch_length
            
            # 开始分析
            self.thread_run.start()
            
        except Exception as e:
            logging.error(f"Analysis error: {str(e)}")
            self.textbox.appendPlainText(f"Error: {str(e)}")
            
            # Reset buttons on error
            self.button_abort.setEnabled(False)
            self.button_analyze.setEnabled(True)

    def update_progress(self, data):
        try:
            progress, message = data
            self.progressBar.setValue(progress)
            self.label_status.setText(message)
            self.textbox.appendPlainText(message)
            
            if progress == 100:
                self.df_score = self.thread_run.df_score
                self.n_epochs = len(self.df_score)
                
                # 更新滑块设置
                self.slider.setEnabled(True)
                self.slider.setMaximum(max(0, self.n_epochs - self.get_n_epochs_display()))
                
                # 启用导航相关的控件
                self.button_visualize.setEnabled(True)
                self.combobox_epochs_per_page.setEnabled(True)
                self.button_previous_more.setEnabled(True)
                self.button_previous.setEnabled(True)
                self.button_goto_epoch.setEnabled(True)
                self.button_next.setEnabled(True)
                self.button_next_more.setEnabled(True)
                
                # Disable abort button when analysis completes
                self.button_abort.setEnabled(False)
                self.button_analyze.setEnabled(True)
                
            elif progress == -1:  # 错误情况
                # 将错误消息只输出到日志和文本框，不再弹窗
                logging.error(message)
                self.textbox.appendPlainText(message)
                
                # Reset buttons on error
                self.button_abort.setEnabled(False)
                self.button_analyze.setEnabled(True)
            
        except Exception as e:
            logging.error(f"Progress update error: {str(e)}")
            self.textbox.appendPlainText(f"Error updating progress: {str(e)}")

    def plot_results(self):
        try:
            # 完全清除当前图形及相关状态
            self.figure.clear()
            plt.close('all')  # 关闭所有可能存在的旧图形
            
            # 重置选中状态
            self.current_selected_epoch = None
            self.highlight_lines = []
            
            # 确保使用最新的分析结果
            self.df_score = self.thread_run.df_score
            self.n_epochs = len(self.df_score)
            self.epoch_start = 0  # 重置起始位置为0
            
            # 更新滑块设置 - 确保滑块范围与新的epoch数量匹配
            self.slider.setMaximum(max(0, self.n_epochs - self.get_n_epochs_display()))
            self.slider.setValue(0)  # 重置滑块位置
            
            # 创建子图 - 更新比例以适应5个子图
            gs = self.figure.add_gridspec(5, 1, height_ratios=[1, 2, 1, 1, 2])
            
            # 获取最新数据
            eeg_data = self.thread_run.eeg_data
            sfreq = self.thread_run.sfreq
            
            # 获取显示的epoch数量
            n_epochs_display = self.get_n_epochs_display()
            
            # 计算时间轴 - 确保使用最新的epoch长度
            time_epochs = np.arange(len(self.df_score)) * self.epoch_length
            time_sec = np.arange(len(eeg_data)) / sfreq
            
            # 日志输出当前epoch长度和分析结果
            logging.info(f"绘图 - 当前epoch长度: {self.epoch_length}秒, 检测到的总epoch数: {self.n_epochs}")
            logging.info(f"绘图 - 癫痫发作epoch数: {sum(self.df_score['Stage_Code'].values)}")
            
            # 1. 分期结果图
            ax_hypnogram = self.figure.add_subplot(gs[0])
            scores = self.df_score['Stage_Code'].values
            colors = [self.map_colors[score] for score in scores]
            
            # 计算时间点 - 使用当前epoch长度
            time_epochs_start = np.arange(len(scores)) * self.epoch_length
            time_epochs_end = time_epochs_start + self.epoch_length
            
            # 绘制分期结果
            ax_hypnogram.hlines(scores, time_epochs_start, time_epochs_end, 
                              colors=colors, linewidths=40)

            ax_hypnogram.set_yticks([0, 1])
            ax_hypnogram.set_yticklabels(["Normal", "Seizure"])
            ax_hypnogram.set_ylabel("Stage")
            ax_hypnogram.set_ylim(-0.5, 1.5)
            ax_hypnogram.set_xticklabels([])  # 去掉x轴刻度标签
            
            # 2. 原始信号和癫痫标记
            ax_signal = self.figure.add_subplot(gs[1])
            ax_signal.plot(time_sec, eeg_data, 'k-', linewidth=1)
            
            # 根据当前选择的范围设置y轴限制
            range_text = self.combobox_amplitude.currentText()
            if range_text != "Auto":
                amplitude = int(range_text.replace('±', ''))
                ax_signal.set_ylim([-amplitude, amplitude])
            
            # 标记癫痫区域 - 使用当前epoch长度
            for i, is_seizure in enumerate(scores):
                if is_seizure:
                    start = i * self.epoch_length
                    end = (i + 1) * self.epoch_length
                    ax_signal.axvspan(start, end, 
                                    color='red', alpha=0.3)
            
            ax_signal.set_ylabel('EEG Amplitude (uV)')
            ax_signal.set_xticklabels([])  # 去掉x轴刻度标签
            
            # EMG包络线图
            ax_emg = self.figure.add_subplot(gs[2])
            if hasattr(self.thread_run, 'emg_data'):
                emg_data = self.thread_run.emg_data
                # 计算EMG包络
                emg_envelope = np.abs(scipy.signal.hilbert(emg_data))
                ax_emg.plot(time_sec, emg_envelope, 'g-', linewidth=1)
                ax_emg.set_ylabel('EMG Envelope (uV)')
                ax_emg.set_xticklabels([])
                
                # 设置初始EMG范围
                emg_range = self.combobox_emg_amplitude.currentText()
                if emg_range != "Auto":
                    amplitude = int(emg_range.replace('±', ''))
                    ax_emg.set_ylim([0, amplitude])
            
            # ACC信号图
            ax_acc = self.figure.add_subplot(gs[3])
            if hasattr(self.thread_run, 'acc_data'):
                acc_data = self.thread_run.acc_data
                ax_acc.plot(time_sec, acc_data, 'b-', linewidth=1)
                ax_acc.set_ylabel('ACC Amplitude (mG)')
                ax_acc.set_xticklabels([])
                
                # 设置初始ACC范围
                acc_range = self.combobox_acc_amplitude.currentText()
                if acc_range != "Auto":
                    amplitude = int(acc_range.replace('±', ''))
                    ax_acc.set_ylim([-amplitude, amplitude])
            
            # 3. 时频图
            ax_spectrogram = self.figure.add_subplot(gs[4])
            
            if (hasattr(self.thread_run, 'spectrogram_data') and 
                self.thread_run.spectrogram_data is not None):
                
                spec_data = self.thread_run.spectrogram_data
                logging.info("Plotting spectrogram with data:")
                logging.info(f"Times range: {spec_data['times'].min():.2f} to {spec_data['times'].max():.2f}")
                logging.info(f"Frequencies range: {spec_data['frequencies'].min():.2f} to {spec_data['frequencies'].max():.2f}")
                logging.info(f"Power shape: {spec_data['power'].shape}")
                
                try:
                    im = ax_spectrogram.imshow(
                        spec_data['power'],
                        extent=[
                            spec_data['times'].min(),
                            spec_data['times'].max(),
                            spec_data['frequencies'].min(),
                            spec_data['frequencies'].max()
                        ],
                        aspect='auto',
                        origin='lower',
                        cmap='RdBu_r',
                        vmin=spec_data['vmin'],
                        vmax=spec_data['vmax']
                    )
                    ax_spectrogram.set_ylabel('EEG Frequency (Hz)')
                    ax_spectrogram.set_xlabel('Time (s)')
                    
                    logging.info("Spectrogram plotted successfully")
                except Exception as e:
                    logging.error(f"Error plotting spectrogram: {str(e)}")
                    ax_spectrogram.text(
                        0.5, 0.5,
                        f'Error plotting spectrogram: {str(e)}',
                        ha='center', va='center'
                    )
            else:
                logging.warning("No spectrogram data available")
                ax_spectrogram.text(
                    0.5, 0.5,
                    'Spectrogram data not available',
                    ha='center', va='center'
                )
            
            # 设置显示范围 - 使用当前epoch长度
            start_time = self.epoch_start * self.epoch_length
            end_time = start_time + (self.epoch_length * n_epochs_display)
            
            for ax in self.figure.axes:
                ax.set_xlim(start_time, end_time)
            
            # 添加epoch标签 - 使用当前epoch长度
            self.epochlabels = []  # 清除旧标签
            self.update_epoch_labels(n_epochs_display)
            
            # 设置点击事件
            self.canvas.mpl_connect('button_press_event', self.on_plot_click)
            
            # 在绘制图形时设置字体大小
            for ax in self.figure.axes:
                ax.tick_params(labelsize=40) 
                ax.set_xlabel(ax.get_xlabel(), fontsize=40)  
                ax.set_ylabel(ax.get_ylabel(), fontsize=40)  
                ax.set_title(ax.get_title(), fontsize=40)   
                
                # 设置轴标签的字体大小
                for label in ax.get_xticklabels():
                    label.set_fontsize(40)
                for label in ax.get_yticklabels():
                    label.set_fontsize(40)
            
            # 调整布局
            self.figure.tight_layout()
            
            # 显示当前使用的epoch长度和模型信息
            self.textbox.appendPlainText(f"Displaying results with epoch length: {self.epoch_length} seconds")
            self.textbox.appendPlainText(f"Detected seizure epochs: {sum(self.df_score['Stage_Code'].values)}/{len(self.df_score)}")
            
            # 绘制画布
            self.canvas.draw()
            
        except Exception as e:
            logging.error(f"Error in plot_results: {str(e)}")
            self.textbox.appendPlainText(f"绘图错误: {str(e)}")
            import traceback
            traceback.print_exc()

    def get_n_epochs_display(self):
        text = self.combobox_epochs_per_page.currentText()
        if text == "All":
            return self.n_epochs
        return int(text)

    def update_epoch_labels(self, n_epochs_display):
        """更新epoch标签"""
        # 清除现有标签
        for label in self.epochlabels:
            try:
                label.remove()
            except:
                pass
        self.epochlabels = []

        # 只在显示少于等于100个epoch时添加标签
        if n_epochs_display <= 100:
            hypnogram_ax = self.figure.axes[0]
            if hypnogram_ax is None:
                return
            
            max_epochs = len(self.df_score)
            label_interval = 5 if n_epochs_display > 20 else 1
            
            actual_n_epochs = min(n_epochs_display, max_epochs - self.epoch_start)
            
            for i in range(0, actual_n_epochs, label_interval):
                epoch_num = self.epoch_start + i
                if epoch_num < max_epochs:
                    x_pos = (epoch_num + 0.5) * self.epoch_length
                    label = hypnogram_ax.text(x_pos, -0.2, str(epoch_num),
                                            horizontalalignment='center',
                                            verticalalignment='top',
                                            fontsize=28)
                    self.epochlabels.append(label)
        
        self.canvas.draw()

    def on_plot_click(self, event):
        # 基本检查
        if event.inaxes is None or event.button != 1:
            return

        try:
            # 计算点击位置对应的epoch - 确保使用当前epoch长度
            new_epoch = int(event.xdata // self.epoch_length)
            
            # 打印日志，帮助调试
            logging.debug(f"Plot click at x={event.xdata}, 计算得到epoch={new_epoch}, 当前epoch长度={self.epoch_length}")
            
            # 验证epoch是否在有效范围内
            if new_epoch < 0 or new_epoch >= len(self.df_score):
                logging.debug(f"无效epoch: {new_epoch}, 超出范围 0-{len(self.df_score)-1}")
                return

            # 设置标志，防止combobox变化触发额外的更新
            self._ignore_combobox_change = True

            # 清除所有现有高亮
            for line in self.highlight_lines:
                try:
                    line.remove()
                except:
                    pass
            self.highlight_lines.clear()

            # 始终处理为新选择，除非点击当前选中的epoch
            if new_epoch == self.current_selected_epoch:
                # 取消选择
                self.current_selected_epoch = None
                self.combobox_stage.setEnabled(False)
                self.label_status.setText("No epoch selected")
            else:
                # 先更新内部状态
                self.current_selected_epoch = new_epoch
                
                # 立即添加高亮 - 使用当前epoch长度
                for ax in self.figure.axes:
                    line = ax.axvspan(
                        new_epoch * self.epoch_length,
                        (new_epoch + 1) * self.epoch_length,
                        color="pink",
                        alpha=0.3,
                        zorder=1000
                    )
                    self.highlight_lines.append(line)

                # 然后更新UI状态
                current_stage = self.df_score.iloc[new_epoch]['Stage']
                self.combobox_stage.setEnabled(True)
                self.combobox_stage.setCurrentText(current_stage)
                self.label_status.setText(f"Selected Epoch: {new_epoch}")

            # 立即重绘画布
            self.canvas.draw()
            
            # 重置标志
            self._ignore_combobox_change = False

        except Exception as e:
            logging.error(f"Error in on_plot_click: {str(e)}", exc_info=True)
            self.textbox.appendPlainText(f"点击处理错误: {str(e)}")
            self._ignore_combobox_change = False  # 确保在发生错误时也重置标志

    def user_edit_stage(self):
        """处理用户编辑的睡眠阶段"""
        # 如果是由点击事件触发的更改，则忽略
        if self._ignore_combobox_change:
            return

        if self.current_selected_epoch is not None:
            new_stage = self.combobox_stage.currentText()
            stage_code = 1 if new_stage == "Seizure" else 0
            
            self.df_score.at[self.current_selected_epoch, 'Stage_Code'] = stage_code
            self.df_score.at[self.current_selected_epoch, 'Stage'] = new_stage
            
            # 保存编辑后的结果
            edit_file = os.path.join(
                self.thread_run.save_path,
                f"epoch_length_{self.epoch_length}_scores_user_edit.csv"
            )
            self.df_score.to_csv(edit_file, index=False)
            
            # 重新绘图
            self.plot_results()

    def enable_navigation_buttons(self):
        """启用导航按钮"""
        self.button_previous_more.setEnabled(True)
        self.button_previous.setEnabled(True)
        self.button_goto_epoch.setEnabled(True)
        self.button_next.setEnabled(True)
        self.button_next_more.setEnabled(True)
        self.combobox_epochs_per_page.setEnabled(True)

    def update_display_previous(self):
        """显示上一页结果"""
        n_epochs_display = self.get_n_epochs_display()
        if self.epoch_start >= n_epochs_display:
            self.epoch_start -= n_epochs_display
        else:
            self.epoch_start = 0
        
        for ax in self.figure.axes:
            ax.set_xlim(
                self.epoch_length * self.epoch_start,
                self.epoch_length * (self.epoch_start + n_epochs_display)
            )
        self.update_epoch_labels(n_epochs_display)
        self.canvas.draw()

    def update_display_previous_more(self):
        """显示前几页结果"""
        n_epochs_display = self.get_n_epochs_display()
        if self.epoch_start >= n_epochs_display * 2:
            self.epoch_start -= n_epochs_display * 2
        else:
            self.epoch_start = 0
        
        for ax in self.figure.axes:
            ax.set_xlim(
                self.epoch_length * self.epoch_start,
                self.epoch_length * (self.epoch_start + n_epochs_display)
            )
        self.update_epoch_labels(n_epochs_display)
        self.canvas.draw()

    def update_display_next(self):
        """显示下一页结果"""
        n_epochs_display = self.get_n_epochs_display()
        max_start = max(0, self.n_epochs - n_epochs_display)
        if self.epoch_start < max_start:
            self.epoch_start += n_epochs_display
            self.epoch_start = min(self.epoch_start, max_start)
            
            for ax in self.figure.axes:
                ax.set_xlim(
                    self.epoch_length * self.epoch_start,
                    self.epoch_length * (self.epoch_start + n_epochs_display)
                )
            self.update_epoch_labels(n_epochs_display)
            self.canvas.draw()

    def update_display_next_more(self):
        """显示后几页结果"""
        n_epochs_display = self.get_n_epochs_display()
        max_start = max(0, self.n_epochs - n_epochs_display)
        new_start = self.epoch_start + n_epochs_display * 2
        self.epoch_start = min(new_start, max_start)
        
        for ax in self.figure.axes:
            ax.set_xlim(
                self.epoch_length * self.epoch_start,
                self.epoch_length * (self.epoch_start + n_epochs_display)
            )
        self.update_epoch_labels(n_epochs_display)
        self.canvas.draw()

    def update_display_goto_epoch(self):
        """跳转到特定epoch"""
        try:
            target_epoch, done = QInputDialog.getInt(
                self, 'Input Dialog', 'Enter the Epoch You Want to View:',
                min=0, max=self.n_epochs-1
            )
            if done:
                n_epochs_display = self.get_n_epochs_display()
                self.epoch_start = min(target_epoch, self.n_epochs - n_epochs_display)
                
                for ax in self.figure.axes:
                    ax.set_xlim(
                        self.epoch_length * self.epoch_start,
                        self.epoch_length * (self.epoch_start + n_epochs_display)
                    )
                self.update_epoch_labels(n_epochs_display)
                self.canvas.draw()
        except Exception as e:
            print(f"Error in update_display_goto_epoch: {str(e)}")

    def update_display_n_epochs(self):
        """更新显示的epoch数量"""
        try:
            n_epochs_display = self.get_n_epochs_display()
            
            # 确保epoch_start不会导致显示超出数据范围
            if self.epoch_start + n_epochs_display > self.n_epochs:
                self.epoch_start = max(0, self.n_epochs - n_epochs_display)
            
            # 更新滑块最大值
            self.slider.setMaximum(max(0, self.n_epochs - n_epochs_display))
            
            # 更新x轴范围
            for ax in self.figure.axes:
                ax.set_xlim(
                    self.epoch_length * self.epoch_start,
                    self.epoch_length * (self.epoch_start + n_epochs_display)
                )
            
            self.update_epoch_labels(n_epochs_display)
            self.canvas.draw()
        except Exception as e:
            print(f"Error in update_display_n_epochs: {str(e)}")

    def update_epoch_length(self):
        """处理epoch长度更新"""
        new_length = float(self.combobox_epoch_length.currentText())
        if new_length != self.epoch_length:
            self.epoch_length = new_length
            if self.thread_run is not None:
                self.thread_run.epoch_length = new_length
            # 不再自动运行分析
            # if self.raw_processed is not None:
            #     self.run_analysis()
            # 显示更新消息
            self.textbox.appendPlainText(f"Epoch length updated to {new_length} sec. Press 'Analyze and Save' to run analysis.")

    def on_slider_changed(self):
        """处理滑块值变化"""
        n_epochs_display = self.get_n_epochs_display()
        self.epoch_start = self.slider.value()
        
        # 更新显示范围
        for ax in self.figure.axes:
            ax.set_xlim(
                self.epoch_length * self.epoch_start,
                self.epoch_length * (self.epoch_start + n_epochs_display)
            )
        
        self.update_epoch_labels(n_epochs_display)
        self.canvas.draw()

    def slider_mouse_press(self, event):
        """处理滑块的鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            # 获取滑块的位置和大小
            opt = QStyleOptionSlider()
            self.slider.initStyleOption(opt)
            handle = self.slider.style().subControlRect(
                QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self.slider)
            
            # 如果点击的是滑块手柄，保持原有的拖动行为
            if handle.contains(event.pos()):
                # 调用原始的鼠标按下事件
                QSlider.mousePressEvent(self.slider, event)
                return
            
            # 如果点击的是轨道，直接跳转到该位置
            value = QStyle.sliderValueFromPosition(
                self.slider.minimum(),
                self.slider.maximum(),
                event.x(),
                self.slider.width()
            )
            self.slider.setValue(value)

    def update_signal_range(self):
        """更新所有信号图的幅度范围"""
        try:
            if len(self.figure.axes) >= 4:  # 确保有足够的子图
                # 更新EEG信号范围
                eeg_range = self.combobox_amplitude.currentText()
                ax_signal = self.figure.axes[1]
                if eeg_range == "Auto":
                    ax_signal.autoscale(axis='y')
                else:
                    amplitude = int(eeg_range.replace('±', ''))
                    ax_signal.set_ylim([-amplitude, amplitude])

                # 更新EMG包络线范围 - 只显示正值
                emg_range = self.combobox_emg_amplitude.currentText()
                ax_emg = self.figure.axes[2]
                if emg_range == "Auto":
                    ax_emg.autoscale(axis='y')
                else:
                    amplitude = int(emg_range.replace('±', ''))
                    ax_emg.set_ylim([0, amplitude])  # 只设置正值范围

                # 更新ACC信号范围
                acc_range = self.combobox_acc_amplitude.currentText()
                ax_acc = self.figure.axes[3]
                if acc_range == "Auto":
                    ax_acc.autoscale(axis='y')
                else:
                    amplitude = int(acc_range.replace('±', ''))
                    ax_acc.set_ylim([-amplitude , amplitude ])

                self.canvas.draw()
        except Exception as e:
            print(f"Error updating signal ranges: {str(e)}")

    def abort_analysis(self):
        try:
            # Terminate the analysis thread
            if self.thread_run.isRunning():
                self.thread_run.terminate()
                self.thread_run.wait()
            
            # Store the original data
            original_raw = self.thread_run.raw_processed
            
            # Reset analysis state while preserving data
            self.thread_run = Thread_run_analysis()
            self.thread_run.signal.connect(self.update_progress)
            self.thread_run.raw_processed = original_raw  # Restore the original data
            
            # Reset UI elements
            self.progressBar.setValue(0)
            self.label_status.setText("")
            self.button_abort.setEnabled(False)
            self.button_analyze.setEnabled(True)
            self.button_visualize.setEnabled(False)
            
            # Clear any previous results
            self.df_score = None
            self.n_epochs = 0
            
            # Display abort message
            self.textbox.appendPlainText("Analysis aborted")
            
        except Exception as e:
            logging.error(f"Error aborting analysis: {str(e)}")
            self.textbox.appendPlainText(f"Error aborting analysis: {str(e)}")

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        try:
            # 检查是否有分析正在运行
            if self.thread_run and self.thread_run.isRunning():
                # 断开信号连接，防止更新已删除的UI组件
                self.thread_run.signal.disconnect()
                
                # 终止线程
                self.thread_run.terminate()
                
                # 等待线程完全终止
                if not self.thread_run.wait(3000):  # 等待最多3秒
                    self.thread_run.terminate()  # 强制终止
            
            # 清理资源
            if hasattr(self, 'figure'):
                plt.close(self.figure)
            
            # 清理内存中的大对象
            self.raw_processed = None
            self.thread_run = None
            self.df_score = None
            
            # 接受关闭事件
            event.accept()
            
        except Exception as e:
            logging.error(f"Error during window closure: {str(e)}")
            # 即使出错也要确保窗口关闭
            event.accept()

    