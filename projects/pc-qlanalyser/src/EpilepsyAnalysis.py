import math

from PyQt5 import QtGui
from PyQt5.QtWidgets import (QWidget, QPushButton, QProgressBar, QLabel,
                             QComboBox, QPlainTextEdit, QGridLayout, QHBoxLayout,
                             QVBoxLayout, QMessageBox, QInputDialog, QSizePolicy, QSlider,
                             QStyle, QStyleOptionSlider, QFrame, QLineEdit, QSpacerItem,
                             QApplication, QComboBox, QWidget, QVBoxLayout, QListView,
                             QToolButton, QMenuBar, QMenu, QToolButton, QAction, QScrollArea,
                             QFileDialog, QDialog, QShortcut, QCheckBox)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QCoreApplication, QTime, QDateTime, QSettings, QTimer, QEvent
from PyQt5.QtGui import QIcon, QFont, QPixmap, QKeySequence, QMovie, QImage, QPainter
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
import os
import time
import random
import logging
import pandas as pd
import datetime
from typing import List
import mne
import sys
from scipy.signal import stft
from .utils import setup_short_cut, probe_pg
import pickle

logging.getLogger('matplotlib').setLevel(logging.WARNING)

from .CustomControls import IconWithTextWidget, TimeSliderWidget, LoadingOverlay, BottomLeftWidget, CollapsibleSidebar
from .QlassAnalysis import NavButtonsWidget
from .Control_Style import ControlStyle
from .Domain.HistoricalWarehouse import EpilepsyScoreWH
from .Infrastructure.log.QLLogging import QLLogging
from .MatplotEventHandler import MatplotlibEventHandler_
from .utils import SaveUtils, _highlight_current_amplitude
from .Infrastructure.QLWidgets.QLGifProgressBar import GifProgressBar
from .Domain.OPLog.OPLog import OPLog, OPType
from scipy.io import savemat
from src.Infrastructure.DB.SQLLiteAccessor import SQLLiteDB_Only_MainTread
import numpy as np
import scipy.signal
import scipy.stats
from scipy.linalg import hankel
import pyeeg  # 添加pyeeg库用于特征提取
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
import matplotlib.pyplot as plt
from PyQt5.QtGui import QPixmapCache
from datetime import timedelta
from .left_time_overlay import LeftTimeOverlay

QPixmapCache.setCacheLimit(1 * 1024 * 1024)  # 默认值： 10 * 1024 KB, 设置为1GB


def emit_and_schedule(signal, current_progress, remaining_times, progressBar):
    # 发送信号
    progress_value = progressBar.value()
    if progress_value >= current_progress:
        return

    signal.emit([current_progress, ""])

    import threading
    import time
    # 如果还有剩余次数，继续安排下一次执行
    if remaining_times > 1:
        next_progress = current_progress + 1
        timespan = 1
        time.sleep(random.uniform(0, 2))
        threading.Timer(
            timespan,
            emit_and_schedule,
            args=(signal, next_progress, remaining_times - 1, progressBar)
        ).start()


def detect_seizures(classifications, data, sfreq, epoch_length=1.0, start_time_ts=None, min_no_seizure_epochs=3):
    """
    检测癫痫发作事件

    参数：
        classifications: 模型分类结果（0=Normal, 1=Seizure）
        data: 原始EEG数据（一维数组，对应单通道）
        sfreq: 采样频率
        epoch_length: 每个epoch的长度（秒）
        start_time_ts: 开始时间的Unix时间戳（秒）
        min_no_seizure_epochs: 为保持向后兼容而保留，当前不再作为判定依据

    事件判定：
        - 连续的 Seizure epoch 构成一个候选事件区间。
        - 当该区间内 Seizure epoch 数量满足 epoch_count >= 2 时，判定为一次癫痫发作事件。
        - 事件的开始时间 s_i 为首个 Seizure epoch 的起始时间：s_i = start_idx * epoch_length。
        - 事件的结束时间 e_i 为由 Seizure 变为 Normal 的时间点，即 e_i = (end_idx + 1) * epoch_length，
          若事件持续到记录结束，则 e_i 取 EEG 记录结束时间。

    30 分钟时间窗统计：
        - 整段 EEG 总时长 L = len(data) / sfreq（秒）。
        - 划分 30 分钟时间窗 M_k = [1800(k-1), 1800k], k = 1..K，K = ceil(L / 1800)。
        - 第 k 个窗内的发作次数 h_k = |{ i | s_i ∈ M_k }|。
        - 有效时长 Δt_k：
            * k < K: Δt_k = 1800
            * k = K: Δt_k = L - 1800 (K-1)
        - 标准化发作频率 f_k = h_k / (Δt_k / 3600)（Events/h）。

    返回：
        seizure_info_list: 癫痫发作信息列表
        seizure_per_minute_df: 30 分钟时间窗统计字典，包含：
            'Minute'           : 每个窗口起始时间（单位：min，自 0 起算，步长 30）
            'Seizure Count'    : h_k（该窗内发作事件次数）
            'UTC Time'         : 每个窗口起始时间对应的 UTC 时间戳
            'Seizure Frequency (Events/h)': f_k（标准化发作频率）
        seizure_epoch_mask: 长度与 classifications 一致的 0/1 列表；
            1 表示该 epoch 属于某次确认为癫痫发作的事件区间，0 表示未被纳入任何发作事件
    """
    try:
        if start_time_ts is None:
            start_time_ts = datetime.datetime.now().timestamp()

        seizure_info_list = []

        # 针对每个 epoch 的 0/1 掩码，初始全为 0
        epoch_count = len(classifications)
        seizure_epoch_mask = [0] * epoch_count

        # 总时长 L（秒）
        if data is None or len(data) == 0 or sfreq <= 0:
            logging.warning("EEG 数据为空或采样率不合法，无法进行癫痫事件检测")
            return [], {
                'Minute': [],
                'Seizure Count': [],
                'UTC Time': [],
                'Seizure Frequency (Events/h)': []
            }, seizure_epoch_mask

        total_samples = len(data)
        total_duration = total_samples / float(sfreq)  # L（秒）

        if epoch_count == 0:
            return [], {
                'Minute': [],
                'Seizure Count': [],
                'UTC Time': [],
                'Seizure Frequency (Events/h)': []
            }, seizure_epoch_mask

        # 扫描 classifications，找到所有连续的 Seizure 段落
        MIN_SEIZURE_EPOCHS = 2  # 至少 2 个连续 epoch 判定为一次癫痫发作事件
        in_seizure = False
        seizure_start_idx = None
        event_start_times = []  # s_i 列表（秒，相对 EEG 起点）

        for i, is_seizure in enumerate(classifications):
            if is_seizure == 1:
                # 进入或处于发作状态
                if not in_seizure:
                    in_seizure = True
                    seizure_start_idx = i
            else:
                # 当前为 Normal，如果之前在发作状态，则结束该段
                if in_seizure and seizure_start_idx is not None:
                    seizure_end_idx = i - 1
                    epoch_span = seizure_end_idx - seizure_start_idx + 1
                    if epoch_span >= MIN_SEIZURE_EPOCHS:
                        # 记录事件
                        start_timestamp = seizure_start_idx * epoch_length
                        # 结束时间为第一个 Normal epoch 的起始时间
                        raw_end_timestamp = (seizure_end_idx + 1) * epoch_length
                        end_timestamp = min(raw_end_timestamp, total_duration)

                        # 样本索引区间
                        seizure_start_sample = int(seizure_start_idx * epoch_length * sfreq)
                        seizure_end_sample = int(min(total_samples, (seizure_end_idx + 1) * epoch_length * sfreq))

                        if seizure_start_sample < seizure_end_sample:
                            seizure_data = data[seizure_start_sample:seizure_end_sample]
                            max_amp = float(np.max(np.abs(seizure_data))) if len(seizure_data) > 0 else 0.0
                            rms_value = float(np.sqrt(np.mean(seizure_data ** 2))) if len(seizure_data) > 0 else 0.0
                            max_amp = round(max_amp, 2)
                            rms_value = round(rms_value, 2)
                        else:
                            max_amp = 0.0
                            rms_value = 0.0

                        duration_sec = round(end_timestamp - start_timestamp, 1)

                        # UTC 时间
                        start_time_utc = start_time_ts + start_timestamp
                        end_time_utc = start_time_ts + end_timestamp

                        seizure_info = {
                            '癫痫发作编号': len(seizure_info_list) + 1,
                            'RMS值': rms_value,
                            '最大值': max_amp,
                            '开始时间戳 (s)': start_timestamp,
                            '结束时间戳 (s)': end_timestamp,
                            '开始时间 (UTC)': datetime.datetime.utcfromtimestamp(start_time_utc),
                            '结束时间 (UTC)': datetime.datetime.utcfromtimestamp(end_time_utc),
                            '持续时间 (s)': duration_sec,
                            '起始 epoch': seizure_start_idx + 1,
                            '结束 epoch': seizure_end_idx + 1
                        }
                        seizure_info_list.append(seizure_info)
                        event_start_times.append(start_timestamp)

                        # 将该事件区间内的 epoch 标记为 1
                        for idx in range(seizure_start_idx, seizure_end_idx + 1):
                            seizure_epoch_mask[idx] = 1

                    # 重置状态
                    in_seizure = False
                    seizure_start_idx = None

        # 处理记录末尾仍处于发作状态的情况
        if in_seizure and seizure_start_idx is not None:
            seizure_end_idx = epoch_count - 1
            epoch_span = seizure_end_idx - seizure_start_idx + 1
            if epoch_span >= MIN_SEIZURE_EPOCHS:
                start_timestamp = seizure_start_idx * epoch_length
                raw_end_timestamp = (seizure_end_idx + 1) * epoch_length
                end_timestamp = min(raw_end_timestamp, total_duration)

                seizure_start_sample = int(seizure_start_idx * epoch_length * sfreq)
                seizure_end_sample = int(min(total_samples, (seizure_end_idx + 1) * epoch_length * sfreq))

                if seizure_start_sample < seizure_end_sample:
                    seizure_data = data[seizure_start_sample:seizure_end_sample]
                    max_amp = float(np.max(np.abs(seizure_data))) if len(seizure_data) > 0 else 0.0
                    rms_value = float(np.sqrt(np.mean(seizure_data ** 2))) if len(seizure_data) > 0 else 0.0
                    max_amp = round(max_amp, 2)
                    rms_value = round(rms_value, 2)
                else:
                    max_amp = 0.0
                    rms_value = 0.0

                duration_sec = round(end_timestamp - start_timestamp, 1)

                start_time_utc = start_time_ts + start_timestamp
                end_time_utc = start_time_ts + end_timestamp

                seizure_info = {
                    '癫痫发作编号': len(seizure_info_list) + 1,
                    'RMS值': rms_value,
                    '最大值': max_amp,
                    '开始时间戳 (s)': start_timestamp,
                    '结束时间戳 (s)': end_timestamp,
                    '开始时间 (UTC)': datetime.datetime.utcfromtimestamp(start_time_utc),
                    '结束时间 (UTC)': datetime.datetime.utcfromtimestamp(end_time_utc),
                    '持续时间 (s)': duration_sec,
                    '起始 epoch': seizure_start_idx + 1,
                    '结束 epoch': seizure_end_idx + 1
                }
                seizure_info_list.append(seizure_info)
                event_start_times.append(start_timestamp)

                # 将该事件区间内的 epoch 标记为 1
                for idx in range(seizure_start_idx, seizure_end_idx + 1):
                    seizure_epoch_mask[idx] = 1

        # 30 分钟时间窗统计（基于事件起始时间 s_i）
        # 若没有事件，仍按整段 EEG 时长生成 30 分钟时间窗，发作次数为 0
        if total_duration <= 0:
            return seizure_info_list, {
                'Minute': [],
                'Seizure Count': [],
                'UTC Time': [],
                'Seizure Frequency (Events/h)': []
            }, seizure_epoch_mask

        K = int(math.ceil(total_duration / 1800.0))
        minutes = []
        counts = []
        utc_times = []
        freqs = []

        # 事件起始时间已经按时间顺序加入列表，可顺序扫描
        event_idx = 0
        num_events = len(event_start_times)

        for k in range(1, K + 1):
            window_start = 1800.0 * (k - 1)
            window_end = 1800.0 * k

            # 计数 h_k：满足 1800(k-1) <= s_i < 1800k 的事件个数
            h_k = 0
            while event_idx < num_events and event_start_times[event_idx] < window_start:
                # 安全前移，理论上不会发生，因为事件按时间递增
                event_idx += 1

            scan_idx = event_idx
            while scan_idx < num_events and window_start <= event_start_times[scan_idx] < window_end:
                h_k += 1
                scan_idx += 1

            # 下一窗从当前 scan_idx 继续扫描，避免重复遍历
            event_idx = scan_idx

            # 有效观测时长 Δt_k
            if k < K:
                delta_t = 1800.0
            else:
                delta_t = total_duration - 1800.0 * (K - 1)
                if delta_t <= 0:
                    delta_t = 1800.0

            # 标准化频率 f_k（Events/h）
            f_k = h_k / (delta_t / 3600.0) if delta_t > 0 else 0.0

            minutes.append(int(window_start / 60.0))  # 以分钟为单位，0, 30, 60, ...
            counts.append(h_k)
            utc_times.append(datetime.datetime.utcfromtimestamp(start_time_ts + window_start))
            freqs.append(round(float(f_k), 4))

        seizure_per_minute_df = {
            'Minute': minutes,
            'Seizure Count': counts,
            'UTC Time': utc_times,
            'Seizure Frequency (Events/h)': freqs
        }

        return seizure_info_list, seizure_per_minute_df, seizure_epoch_mask

    except Exception as e:
        logging.error(f"检测癫痫发作时出错: {e}", exc_info=True)
        # 出错时返回与输入长度一致的全 0 掩码
        seizure_epoch_mask = [0] * len(classifications)
        return [], {
            'Minute': [],
            'Seizure Count': [],
            'UTC Time': [],
            'Seizure Frequency (Events/h)': []
        }, seizure_epoch_mask


class RelativeTimeAxis(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.meas_date = None  # 记录起始绝对时间

    def set_meas_date(self, date):
        self.meas_date = date

    def tickStrings(self, values, scale, spacing):
        """自动计算刻度文本"""
        if self.meas_date is None:
            return [str(v) for v in values]

        strings = []
        for v in values:
            try:
                # 将 x轴的相对秒数 加到 起始时间 上
                curr_time = self.meas_date + timedelta(seconds=v)
                # 根据缩放级别自动调整显示精度
                if spacing < 1:
                    strings.append(curr_time.strftime('%H:%M:%S.%f')[:-3])
                else:
                    strings.append(curr_time.strftime('%H:%M:%S'))
            except Exception:
                strings.append("")
        return strings


class Thread_run_analysis(QThread):
    signal = pyqtSignal('PyQt_PyObject')

    def __init__(self, progressBar):
        QThread.__init__(self)
        self.raw_processed = None
        self.epoch_length = 5.0
        self.eeg_channel = None
        self.emg_channel = None
        self.acc_channel = None
        self.save_path = None
        self.timestamp_dir = None
        self.df_score = None

        self.progressBar = progressBar

    def calculate_spectrogram(self, sfreq):
        """计算EEG信号的时频图数据"""
        try:
            # 检查数据是否存在
            if not hasattr(self, 'eeg_data'):
                logging.exception("EEG data not found")
                return None

            # 获取采样率
            # sfreq = self.raw_processed.info['sfreq']
            QLLogging.log.info(f"Calculating spectrogram with sampling rate: {sfreq}Hz")

            # 打印数据基本信息
            QLLogging.log.info(f"EEG data shape: {self.eeg_data.shape}")

            # 设置时频图参数
            nperseg = int(sfreq * 4)
            noverlap = int(nperseg * 0.9)
            QLLogging.log.info(f"Spectrogram parameters - nperseg: {nperseg}, noverlap: {noverlap}")

            # 更换时频图计算方法，消除时频图开头的空白
            f, t, Zxx = stft(self.eeg_data, fs=sfreq, nperseg=nperseg, noverlap=noverlap, boundary='zeros')

            # 计算对数功率谱
            Sxx = 10 * np.log10(np.abs(Zxx) + 1e-10)

            # 筛选感兴趣的频率范围
            good_freqs = np.logical_and(f >= 0.5, f <= 50)
            Sxx = Sxx[good_freqs, :]
            f = f[good_freqs]

            QLLogging.log.info(f"Filtered spectrogram shape - f: {f.shape}, Sxx: {Sxx.shape}")

            # 计算颜色范围
            vmin = np.percentile(Sxx, 10)
            vmax = np.percentile(Sxx, 99)
            QLLogging.log.info(f"Color range - vmin: {vmin}, vmax: {vmax}")

            return {
                'frequencies': f,
                'times': t,
                'power': Sxx,
                'vmin': vmin,
                'vmax': vmax
            }
        except Exception as e:
            QLLogging.log.exception(f"Spectrogram calculation error:{e}")  # 记录完整堆栈跟踪
            return None  # 静默失败，让主线程处理

    def calculate_spectrogram_optimized(self, eeg_data, sfreq):
        """计算EEG信号的时频图数据"""
        try:
            # 检查数据是否存在
            if not hasattr(self, 'eeg_data'):
                logging.exception("EEG data not found")
                return None

            QLLogging.log.info(f"Calculating spectrogram with sampling rate: {sfreq}Hz")

            # 打印数据基本信息
            QLLogging.log.info(f"EEG data shape: {eeg_data.shape}")

            # 设置时频图参数
            nperseg = int(sfreq * 2)
            noverlap = int(nperseg * 0.5)
            QLLogging.log.info(f"Spectrogram parameters - nperseg: {nperseg}, noverlap: {noverlap}")

            # 更换时频图计算方法，消除时频图开头的空白
            f, t, Zxx = stft(eeg_data, fs=sfreq, nperseg=nperseg, noverlap=noverlap, boundary='zeros')

            # 计算对数功率谱
            Sxx = 10 * np.log10(np.abs(Zxx) + 1e-10)

            # 筛选感兴趣的频率范围
            good_freqs = np.logical_and(f >= 0.5, f <= 50)
            Sxx = Sxx[good_freqs, :]
            f = f[good_freqs]

            QLLogging.log.info(f"Filtered spectrogram shape - f: {f.shape}, Sxx: {Sxx.shape}")

            # 计算颜色范围
            vmin = np.percentile(Sxx, 10)
            vmax = np.percentile(Sxx, 99)
            QLLogging.log.info(f"Color range - vmin: {vmin}, vmax: {vmax}")

            return {
                'frequencies': f,
                'times': t,
                'power': Sxx,
                'vmin': vmin,
                'vmax': vmax
            }
        except Exception as e:
            QLLogging.log.exception("Spectrogram calculation error")  # 记录完整堆栈跟踪
            return None  # 静默失败，让主线程处理

    def _get_all_channel_data(self):
        # 并行获取各通道数据（如果数据量很大）
        emg_data = self.raw_processed.get_data()[self.emg_channel]
        acc_data = self.raw_processed.get_data()[self.acc_channel] * 1e-6

        return emg_data, acc_data

    def _calculate_spectrogram_safe(self):
        """优化的时频图计算方法"""
        try:
            # 等待数据加载完成
            eeg_data, _, _, sfreq = data_future.result()

            # 优化时频图计算（使用之前讨论的优化版本）
            spectrogram_data = self.calculate_spectrogram_optimized(eeg_data, sfreq)

            if spectrogram_data is None:
                logging.warning("Spectrogram calculation failed")
                return None

            return spectrogram_data
        except Exception as e:
            logging.exception(f"Spectrogram calculation error: {e}")
            return None

    def run(self):
        pass


class TopWidget(QWidget):
    # 顶部窗口
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI(parent)
        self.setAcceptDrops(True)

    def initUI(self, parent=None):
        # 创建主布局
        self.top_widget_hlayout = QHBoxLayout(self)
        self.top_widget_hlayout.setObjectName("top_widget_hlayout")
        self.top_widget_hlayout.setContentsMargins(32, 0, 32, 24)
        self.top_widget_hlayout.setSpacing(0)

        # Epilepsy Analysis label
        self.epilepsy_analysis_label = QLabel(parent)
        self.epilepsy_analysis_label.setObjectName("epilepsy_analysis_label")
        self.epilepsy_analysis_label.setMinimumSize(230, 32)
        self.epilepsy_analysis_label.setStyleSheet(ControlStyle.get_label_word_style())
        ControlStyle.get_font_size(self.epilepsy_analysis_label, 12)
        self.top_widget_hlayout.addWidget(self.epilepsy_analysis_label)

        # 创建一个空白区域
        spacerItem1 = QSpacerItem(200, 32, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.top_widget_hlayout.addSpacerItem(spacerItem1)

        # 创建一个空白区域
        spacerItem2 = QSpacerItem(100, 32, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.top_widget_hlayout.addSpacerItem(spacerItem2)

        # Number of Epochs Display label + comboBox
        epochs_control = QHBoxLayout()
        epochs_control.setContentsMargins(0, 0, 0, 0)  # 外边距为0
        epochs_control.setSpacing(20)  # 设置组件之间的间距为5像素

        self.label_select_number_epochs = QLabel(parent)
        self.label_select_number_epochs.setObjectName("label_select_number_epochs")
        self.label_select_number_epochs.setMinimumSize(194, 32)
        self.label_select_number_epochs.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_select_number_epochs, 10)

        self.combobox_select_n_epochs = QComboBox(parent)
        self.combobox_select_n_epochs.setObjectName("combobox_select_n_epochs")
        self.combobox_select_n_epochs.setMinimumSize(112, 32)
        self.combobox_select_n_epochs.addItems(["All", "100", "50", "30", "20", "10", "5", "3"])
        self.combobox_select_n_epochs.setEnabled(False)
        self.combobox_select_n_epochs.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_select_n_epochs, 10)

        epochs_control.addWidget(self.label_select_number_epochs)
        epochs_control.addWidget(self.combobox_select_n_epochs)
        self.top_widget_hlayout.addLayout(epochs_control)

        # 创建一个空白区域
        spacerItem1 = QSpacerItem(32, 32)
        self.top_widget_hlayout.addSpacerItem(spacerItem1)

        # # 创建一个空白区域
        # spacerItem2 = QSpacerItem(31, 32)
        # self.top_widget_hlayout.addSpacerItem(spacerItem2)

        self.nav_buttons_widget = NavButtonsWidget(parent)
        self.top_widget_hlayout.addWidget(self.nav_buttons_widget)

    def retranslateUi(self):
        _translate = QCoreApplication.translate
        self.label_select_number_epochs.setText(_translate("TopWidget", "Number of Epochs to display"))


class BottomRightTopWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI(parent)
        self.setAcceptDrops(True)

    def initUI(self, parent=None):
        # 定义一个水平布局
        self.bottom_right_top_widget_hlayout = QHBoxLayout(self)
        self.bottom_right_top_widget_hlayout.setContentsMargins(32, 15, 32, 0)
        self.bottom_right_top_widget_hlayout.setSpacing(0)

        seizure_normal_hlayout = QHBoxLayout()
        seizure_normal_hlayout.setContentsMargins(0, 0, 0, 0)
        seizure_normal_hlayout.setSpacing(16)
        # Seizure button
        self.pushButton_seizure = QPushButton(parent)
        self.pushButton_seizure.setObjectName("pushButton_seizure")
        self.pushButton_seizure.setMinimumSize(96, 32)
        self.pushButton_seizure.setStyleSheet(ControlStyle.get_color_pushButton_style(color="FF3B3B"))
        self.pushButton_seizure.setToolTip("快捷方式为：Shift+2")
        ControlStyle.get_font_size(self.pushButton_seizure, 10)

        # normal button
        self.pushButton_normal = QPushButton(parent)
        self.pushButton_normal.setObjectName("pushButton_normal")
        self.pushButton_normal.setMinimumSize(96, 32)
        self.pushButton_normal.setStyleSheet(ControlStyle.get_color_pushButton_style(color="3131F6"))
        self.pushButton_normal.setToolTip("快捷方式为：Shift+1")
        ControlStyle.get_font_size(self.pushButton_normal, 10)

        seizure_normal_hlayout.addWidget(self.pushButton_seizure, alignment=Qt.AlignLeft)
        seizure_normal_hlayout.addWidget(self.pushButton_normal, alignment=Qt.AlignLeft)

        redo_set_hlayout = QHBoxLayout()
        redo_set_hlayout.setContentsMargins(24, 0, 24, 0)
        redo_set_hlayout.setSpacing(16)

        # redo
        self.pushButton_redo = QPushButton(parent)
        self.pushButton_redo.setObjectName("pushButton_redo")
        self.pushButton_redo.setMinimumSize(60, 32)
        self.pushButton_redo.setStyleSheet(ControlStyle.get_redo_undo_black_pushButton_style())
        ControlStyle.get_font_size(self.pushButton_redo, 10)
        self.pushButton_redo.setIcon(QIcon("./resource/picture/redo.png"))
        self.pushButton_redo.setEnabled(False)
        # undo
        self.pushButton_undo = QPushButton(parent)
        self.pushButton_undo.setObjectName("pushButton_undo")
        self.pushButton_undo.setMinimumSize(60, 32)
        self.pushButton_undo.setStyleSheet(ControlStyle.get_redo_undo_black_pushButton_style())
        ControlStyle.get_font_size(self.pushButton_undo, 10)
        self.pushButton_undo.setIcon(QIcon("./resource/picture/undo.png"))
        self.pushButton_undo.setEnabled(False)
        # reset
        self.pushButton_reset = QPushButton(parent)
        self.pushButton_reset.setObjectName("pushButton_reset")
        self.pushButton_reset.setMinimumSize(80, 32)
        self.pushButton_reset.setStyleSheet(ControlStyle.get_redo_set_pushButton_style())
        ControlStyle.get_font_size(self.pushButton_reset, 10)
        self.pushButton_reset.setIcon(QIcon("./resource/picture/reset.png"))

        redo_set_hlayout.addWidget(self.pushButton_redo)
        redo_set_hlayout.addWidget(self.pushButton_undo)
        redo_set_hlayout.addWidget(self.pushButton_reset)

        # 创建一个空白区域
        spacerItem = QSpacerItem(350, 32, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Amplitude setting menu  多级列表
        # 创建主工具按钮
        self.toolButton_amplitude_set = QToolButton(parent)
        self.toolButton_amplitude_set.setMinimumSize(190, 32)
        self.toolButton_amplitude_set.setPopupMode(QToolButton.InstantPopup)
        self.toolButton_amplitude_set.setStyleSheet(ControlStyle.get_toolbutton_style())
        ControlStyle.get_font_size(self.toolButton_amplitude_set, 10)
        # 创建主下拉菜单
        main_menu = QMenu()
        main_menu.setMinimumSize(160, 32)
        main_menu.setStyleSheet(ControlStyle.get_menuBar_style())
        ControlStyle.get_font_size(main_menu, 10)

        # 创建一级菜单（EEG，EMG，ACC）
        self.menu_eeg = QMenu()
        self.menu_eeg.setTitle("EEG  Amplitude (μv) ")
        self.menu_emg = QMenu()
        self.menu_emg.setTitle("EMG Amplitude (μv) ")
        self.menu_acc = QMenu()
        self.menu_acc.setTitle("ACC  Amplitude (μv) ")

        self.menu_eeg.setStyleSheet(ControlStyle.get_menuBar_style())
        self.menu_emg.setStyleSheet(ControlStyle.get_menuBar_style())
        self.menu_acc.setStyleSheet(ControlStyle.get_menuBar_style())

        ControlStyle.get_font_size(self.menu_eeg, 10)
        ControlStyle.get_font_size(self.menu_emg, 10)
        ControlStyle.get_font_size(self.menu_acc, 10)

        # 将一级菜单添加到菜单栏中
        main_menu.addMenu(self.menu_eeg)
        main_menu.addMenu(self.menu_emg)
        main_menu.addMenu(self.menu_acc)

        self.toolButton_amplitude_set.setMenu(main_menu)

        self.bottom_right_top_widget_hlayout.addLayout(seizure_normal_hlayout)
        self.bottom_right_top_widget_hlayout.addLayout(redo_set_hlayout)
        self.bottom_right_top_widget_hlayout.addSpacerItem(spacerItem)
        self.bottom_right_top_widget_hlayout.addWidget(self.toolButton_amplitude_set)

        self.retranslateUi()

    def retranslateUi(self):
        _translate = QCoreApplication.translate
        self.pushButton_seizure.setText(_translate("BottomRightTopWidget", "Seizure"))
        self.pushButton_normal.setText(_translate("BottomRightTopWidget", "Normal"))

        self.pushButton_redo.setText(_translate("BottomRightTopWidget", "Redo"))
        self.pushButton_undo.setText(_translate("BottomRightTopWidget", "Undo"))
        self.pushButton_reset.setText(_translate("BottomRightTopWidget", "Reset"))

        self.toolButton_amplitude_set.setText(_translate("BottomRightTopWidget", "Amplitude setting"))


class Ui_epilepsy_analysis(QWidget):
    # 定义一个自定义信号
    progressBar_completed = pyqtSignal()

    def __init__(self, epilepsy_analysis):
        super().__init__()

        self.progressBar = GifProgressBar()
        self.progressBar.setObjectName("progressBar")

        self.raw_processed = None
        self.map_colors = {0: "blue", 1: "red"}
        self.map_stages = {0: "Normal", 1: "Seizure"}
        self.thread_run = self.get_thread_run()
        self.thread_run.signal.connect(self.update_progress)
        self.df_score = None
        self.df_display_score = None
        self.current_selected_epoch = None
        self.n_epochs = 0
        self.epochlabels = []
        self._ignore_combobox_change = False  # 添加标志以防止循环触发
        self.setup_logging()
        self.edf_path = None
        self.epilepsy_score_wh = EpilepsyScoreWH()
        self.epilepsy_redo_score_wh = EpilepsyScoreWH()

        self.current_selected_epochs = []
        self.button_is_pressed = False
        self.mouse_is_dragged = False
        self.mouse_dragged_begin = None
        self.window = None

        # 设置matplotlib
        plt.rcParams['agg.path.chunksize'] = 10000
        plt.rcParams['path.simplify'] = True
        plt.rcParams['path.simplify_threshold'] = 0.5

        # 添加全局异常处理
        sys.excepthook = self.handle_exception

        self.pushButton_analyse = QPushButton(epilepsy_analysis)
        self.bottom_left_widget = BottomLeftWidget(epilepsy_analysis)

        self.sidebar = CollapsibleSidebar(parent=self, title="Control Panel")
        self.sidebar.set_expanded_width(370)  # 设置展开宽度
        self.sidebar.add_widget(self.bottom_left_widget)

        self.file_name = None

        # 管理非模态放大窗 & 对应标记
        self._zoom_windows = []  # 持有放大窗口引用，避免被回收
        self._zoom_markers = {}  # {zoom_dialog: {"plot": plot, "items": [line, scatter?]}}

        self._zoom_viewports = set()
        self._zoom_viewport_map = {}

        # 框选相关
        self._rb = None  # QRubberBand 实例
        self._rb_origin = None  # 起点（viewport 坐标，QPoint）
        self._rb_plot = None  # 当前承载 rubber band 的 PlotWidget
        self._rb_host = None  # 橡皮筋挂载的host（统一放在scrollarea的viewport上）

        # 选区高亮的状态
        self._range_markers = {}  # {plot_widget: LinearRegionItem}
        self._mpl_spans = []  # Matplotlib 里的 axvspan 引用，便于清理

        # 统一的样式（清爽的蓝色，半透明）
        self._hl_pen = pg.mkPen(100, 149, 237, 180, width=1)  # #6495ED
        self._hl_brush = pg.mkBrush(100, 149, 237, 60)

        self._is_input_hover = False
        self._is_slider_hover = False

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
            QLLogging.log.exception(f"Failed to setup logging: {str(e)}")
            # 尝试写入一个简单的错误文件
            try:
                with open(os.path.join(user_docs, 'ar_analyser_error.txt'), 'w') as f:
                    f.write(f"Logging setup failed: {str(e)}")
            except:
                pass

    def get_thread_run(self):
        """获取线程运行实例"""
        return Thread_run_analysis(self.progressBar)

    def create_top_widget(self, parent):
        return TopWidget(parent)

    def create_bottom_right_top_widget(self, parent):
        return BottomRightTopWidget(parent)

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """全局异常处理器"""
        QLLogging.log.exception("Uncaught exception",
                                exc_info=(exc_type, exc_value, exc_traceback))

    def setupUi(self, epilepsy_analysis):
        epilepsy_analysis.setObjectName("epilepsy_analysis")
        epilepsy_analysis.resize(1440, 900)
        epilepsy_analysis.setWindowTitle("Epilepsy Analysis - AI based model")
        epilepsy_analysis.setStyleSheet(ControlStyle.get_widget_style())

        # 创建主布局
        self.main_layout = QVBoxLayout(epilepsy_analysis)
        self.main_layout.setObjectName("main_layout")
        self.main_layout.setContentsMargins(0, 24, 0, 0)
        self.main_layout.setSpacing(0)

        # 创建出顶部窗口
        self.top_widget = self.create_top_widget(epilepsy_analysis)
        self.top_widget.setFixedHeight(80)
        top_widget_size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.top_widget.setSizePolicy(top_widget_size_policy)

        self.bottom_left_widget.combobox_epoch_length.addItems(["3", "5"])
        self.bottom_left_widget.combobox_epoch_length.setCurrentText("5")

        self.top_widget.nav_buttons_widget.button_goto_epoch.setEnabled(True)
        self.top_widget.nav_buttons_widget.button_next.setEnabled(True)
        self.top_widget.nav_buttons_widget.button_previous.setEnabled(True)
        self.top_widget.nav_buttons_widget.first_pushButton.setEnabled(True)
        self.top_widget.nav_buttons_widget.last_pushButton.setEnabled(True)

        # 添加行高
        # 创建 QListView 并设置行高
        view_n_epochs = QListView()
        view_n_epochs.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.top_widget.combobox_select_n_epochs.setView(view_n_epochs)  # 绑定视图到 QComboBox
        self.top_widget.combobox_select_n_epochs.setEnabled(True)

        # 添加行高
        # 创建 QListView 并设置行高
        view_epoch_length = QListView()
        view_epoch_length.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.bottom_left_widget.combobox_epoch_length.setView(view_epoch_length)  # 绑定视图到 QComboBox

        # 添加分割线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setStyleSheet("background-color: #a9a9a9;")
        separator.setFixedHeight(1)

        # 使用一个水平布局进行布局
        self.main_bottom_hlayout = QHBoxLayout(epilepsy_analysis)
        self.main_bottom_hlayout.setObjectName("main_bottom_hlayout")
        self.main_bottom_hlayout.setContentsMargins(0, 0, 0, 0)
        self.main_bottom_hlayout.setSpacing(0)

        # 创建出底部左边窗口
        self.bottom_left_widget.setMinimumSize(314, 789)
        bottom_left_widget_size_policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.bottom_left_widget.setSizePolicy(bottom_left_widget_size_policy)
        # self.main_bottom_hlayout.addWidget(self.bottom_left_widget, 314)
        self.main_bottom_hlayout.addWidget(self.sidebar, 314)

        # 添加行高
        # 创建 QListView 并设置行高
        view_eeg = QListView()
        view_eeg.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.bottom_left_widget.combobox_eeg.setView(view_eeg)  # 绑定视图到 QComboBox
        view_emg = QListView()
        view_emg.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.bottom_left_widget.combobox_emg.setView(view_emg)  # 绑定视图到 QComboBox
        view_acc = QListView()
        view_acc.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.bottom_left_widget.combobox_acc.setView(view_acc)  # 绑定视图到 QComboBox

        # 底部右边窗口
        self.bottom_right_widget = QWidget(epilepsy_analysis)
        self.bottom_right_widget.setMinimumSize(1126, 788)
        self.bottom_right_widget.setStyleSheet(ControlStyle.get_draw_pic_widget_style())
        self.main_bottom_hlayout.addWidget(self.bottom_right_widget, 1126)
        # 这里是底部右边窗口的布局
        self.bottom_right_widget_vlayout = QVBoxLayout(self.bottom_right_widget)
        self.bottom_right_widget_vlayout.setObjectName("bottom_right_widget_vlayout")
        self.bottom_right_widget_vlayout.setContentsMargins(0, 0, 0, 24)
        self.bottom_right_widget_vlayout.setSpacing(0)

        # 主要是绘画窗口
        # 先将初始化页面画出，当获取到点击事件之后，将其页面换成进度条，当进度条走完之后，将图形显示出来
        self.draw_pic_widget = QWidget()
        self.draw_pic_widget.setObjectName("draw_pic_widget")
        self.draw_pic_widget.setMinimumSize(1126, 692)

        draw_pic_vlayout = QVBoxLayout(self.draw_pic_widget)
        draw_pic_vlayout.setContentsMargins(0, 0, 32, 0)
        draw_pic_vlayout.setSpacing(0)

        # 创建一个首页页面
        self.icon_with_text_widget = IconWithTextWidget(
            icon_path="./resource/picture/Analyse.png",  # 图标路径
            text="请设置分析参数后点击“Analyse”开始分析"
        )
        self.icon_with_text_widget.setObjectName("icon_with_text_widget")
        self.icon_with_text_widget.setMinimumSize(1126, 692)

        # 创建进度条页面
        self.progressBar_widget = QWidget(epilepsy_analysis)
        self.progressBar_widget.setMinimumSize(1126, 692)

        progressBar_vlayout = QVBoxLayout(self.progressBar_widget)
        progressBar_vlayout.setContentsMargins(434, 0, 434, 0)
        progressBar_vlayout.setAlignment(Qt.AlignCenter)
        progressBar_vlayout.setSpacing(0)

        self.label_progressBar = QLabel(epilepsy_analysis)
        self.label_progressBar.setText("分析中")
        self.label_progressBar.setObjectName("label_progressBar")
        self.label_progressBar.setMinimumSize(50, 20)
        self.label_progressBar.setStyleSheet(ControlStyle.get_redo_set_pushButton_style())
        self.label_progressBar.hide()

        self.label_draw = QLabel(epilepsy_analysis)
        self.label_draw.setText("正在绘图中~~~")
        self.label_draw.setObjectName("label_draw")
        self.label_draw.setMinimumSize(150, 20)
        self.label_draw.setStyleSheet(ControlStyle.get_redo_set_pushButton_style())
        ControlStyle.get_font_size(self.label_draw, 16)
        self.label_draw.hide()
        self.progressBar.hide()

        # 刷新 GUI
        QApplication.processEvents()

        progressBar_vlayout.addWidget(self.progressBar)
        progressBar_vlayout.addWidget(self.label_progressBar, alignment=Qt.AlignLeft)
        progressBar_vlayout.addWidget(self.label_draw)

        # 这里需要添加一个顶部窗口
        self.bottom_right_top_widget = self.create_bottom_right_top_widget(epilepsy_analysis)
        self.bottom_right_top_widget.setObjectName("bottom_right_top_widget")
        self.bottom_right_top_widget.setFixedHeight(50)
        bottom_right_top_widget_size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.bottom_right_top_widget.setSizePolicy(bottom_right_top_widget_size_policy)

        # 添加数值选项
        values = ["±100", "±200", "±500", "±1000", "±2000", "Auto"]
        for value in values:
            action = QAction(value, self)
            self.bottom_right_top_widget.menu_eeg.addAction(action)
            action.triggered.connect(
                lambda checked, val=value: self.update_signal_range(sender="eeg", value=val)
            )
            # 设置 Auto 为默认选中
            if value == "Auto":
                action.setChecked(True)

        values = ["±50", "±100", "±200", "±500", "Auto"]
        for value in values:
            action = QAction(value, self)
            self.bottom_right_top_widget.menu_emg.addAction(action)
            action.triggered.connect(
                lambda checked, val=value: self.update_signal_range(sender="emg", value=val)
            )
            # 设置 Auto 为默认选中
            if value == "Auto":
                action.setChecked(True)

        values = ["±500", "±1000", "±2000", "±4000", "Auto"]
        for value in values:
            action = QAction(value, self)
            self.bottom_right_top_widget.menu_acc.addAction(action)
            action.triggered.connect(
                lambda checked, val=value: self.update_signal_range(sender="acc", value=val)
            )
            # 设置 Auto 为默认选中
            if value == "Auto":
                action.setChecked(True)

        self.bottom_right_top_widget.menu_eeg.aboutToShow.connect(
            lambda: _highlight_current_amplitude(self.bottom_right_top_widget.menu_eeg, lambda: probe_pg(self.plot_eeg))
        )
        self.bottom_right_top_widget.menu_emg.aboutToShow.connect(
            lambda: _highlight_current_amplitude(self.bottom_right_top_widget.menu_emg, lambda: probe_pg(self.plot_emg))
        )
        self.bottom_right_top_widget.menu_acc.aboutToShow.connect(
            lambda: _highlight_current_amplitude(self.bottom_right_top_widget.menu_acc, lambda: probe_pg(self.plot_acc))
        )

        # Figure
        self.figure = Figure(dpi=15)
        self.figure.set_size_inches(15, 8)
        self.canvas = FigureCanvasQTAgg(self.figure)
        # 创建子图 - 更新比例以适应新的布局
        self.gs = self.figure.add_gridspec(1, 1, height_ratios=[1])
        # 调整画布的尺寸以适应所有子图
        self.figure.subplots_adjust(left=0, right=1, bottom=0, top=1)

        self.widget_hypnogram = QWidget(epilepsy_analysis)
        hypnogram_layout = QVBoxLayout(self.widget_hypnogram)
        hypnogram_layout.setContentsMargins(50, 0, 0, 0)  # 消除小部件布局的边距
        hypnogram_layout.setSpacing(0)  # 消除小部件布局的间距
        hypnogram_layout.addWidget(self.canvas)

        self.spectrogram_time_axis_eeg = RelativeTimeAxis(orientation='bottom')
        self.spectrogram_time_axis_eeg.setPen(None)
        self.spectrogram_time_axis_eeg.setTextPen(pg.mkPen('k'))

        self.spectrogram_time_axis_emg = RelativeTimeAxis(orientation='bottom')
        self.spectrogram_time_axis_emg.setPen(None)
        self.spectrogram_time_axis_emg.setTextPen(pg.mkPen('k'))

        self.spectrogram_time_axis_acc = RelativeTimeAxis(orientation='bottom')
        self.spectrogram_time_axis_acc.setPen(None)
        self.spectrogram_time_axis_acc.setTextPen(pg.mkPen('k'))

        self.spectrogram_time_axis = RelativeTimeAxis(orientation='bottom')
        self.spectrogram_time_axis.setPen(None)
        self.spectrogram_time_axis.setTextPen(pg.mkPen('k'))

        self.plot_eeg = pg.PlotWidget(axisItems={'bottom': self.spectrogram_time_axis_eeg})
        self.plot_emg = pg.PlotWidget(axisItems={'bottom': self.spectrogram_time_axis_emg})
        self.plot_acc = pg.PlotWidget(axisItems={'bottom': self.spectrogram_time_axis_acc})
        # 将 axisItems 传入 plot_widget (频谱图)
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': self.spectrogram_time_axis})
        # --- Y 轴范围状态（新增） ---
        self._range_mode = {'eeg': 'Auto', 'emg': 'Auto', 'acc': 'Auto'}  # 记录当前是否为 Auto
        # 记录手动范围：EEG/ACC 对称，EMG 仅正值；默认值可按需调整
        self._manual_ranges = {'eeg': (-100, 100), 'emg': (0, 200), 'acc': (-1000, 1000)}

        # 隐藏自动缩放按钮
        for plot in [self.plot_eeg, self.plot_emg, self.plot_acc, self.plot_widget]:
            plot.getPlotItem().hideButtons()
            # 彻底隐藏自动缩放按钮
            if hasattr(plot.getPlotItem(), "autoBtn"):
                plot.getPlotItem().autoBtn.hide()
                plot.getPlotItem().autoBtn.setEnabled(False)
                plot.getPlotItem().autoBtn.setVisible(False)

        self.event_handler = MatplotlibEventHandler_(self.canvas, owner=self,
                                                     plot_widgets=[self.plot_eeg, self.plot_emg, self.plot_acc,
                                                                   self.plot_widget])

        # 将所有图表的 X 轴链接
        self.plot_emg.setXLink(self.plot_eeg)
        self.plot_acc.setXLink(self.plot_eeg)
        # self.plot_widget.setXLink(self.plot_eeg)

        # 为每个图表设置默认样式
        for plot in [self.plot_acc, self.plot_emg, self.plot_eeg, self.plot_widget]:
            plot.setBackground("w")
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.setMouseEnabled(x=True, y=False)  # 只允许水平缩放/平移
            if plot==self.plot_widget:
                plot.setMouseEnabled(x=False, y=False)
            plot.setMenuEnabled(False)  # 禁用右键菜单
            plot.getAxis('bottom').setTextPen(pg.mkPen('k'))
            plot.getAxis('left').setTextPen(pg.mkPen('k'))

            # plot.getViewBox().disableAutoRange(axis=pg.ViewBox.YAxis)

        self.plot_container = QWidget()
        main_layout = QVBoxLayout(self.plot_container)

        # 添加图表到布局并分配比例（拉伸因子）
        plots = [
            self.widget_hypnogram,  # 睡眠分析图
            self.plot_eeg,  # EEG图 - 较高比例
            self.plot_emg,  # EMG图 - 较高比例
            self.plot_acc,  # ACC图 - 中等比例
            self.plot_widget  # 其他图 - 较小比例
        ]

        # 定义每个图表的拉伸因子（高度比例）
        stretch_factors = [1, 2, 2, 2, 2]
        max_width = 50

        # 将图表添加到布局
        for i, plot in enumerate(plots):
            main_layout.addWidget(plot, stretch_factors[i])
            if plot == self.widget_hypnogram:
                continue
            # 设置左侧轴固定宽度
            axis = plot.getAxis("left")
            axis.setWidth(max_width)

        # 创建一个滚动区域
        self.scrollarea_canvas = QScrollArea(epilepsy_analysis)
        self.scrollarea_canvas.setObjectName("scrollarea_canvas")
        self.scrollarea_canvas.setMinimumSize(1085, 545)
        self.scrollarea_canvas.setWidgetResizable(True)  # 关键：启用内容自适应
        self.scrollarea_canvas.setHorizontalScrollBarPolicy(True)  # 强制显示水平滚动条（或设置为 AsNeeded）
        # self.scrollarea_canvas.setWidget(self.canvas)
        self.scrollarea_canvas.setWidget(self.plot_container)

        self.widget_time_slider = TimeSliderWidget(epilepsy_analysis)
        self.widget_time_slider.setObjectName("widget_time_slider")
        self.widget_time_slider.setMinimumSize(1126, 56)
        self.widget_time_slider.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.widget_time_slider.time_slider.setMinimum(0)

        draw_pic_vlayout.addWidget(self.icon_with_text_widget)
        draw_pic_vlayout.addWidget(self.progressBar_widget)
        draw_pic_vlayout.addWidget(self.bottom_right_top_widget)
        draw_pic_vlayout.addWidget(self.scrollarea_canvas)
        draw_pic_vlayout.addWidget(self.widget_time_slider)

        # self.icon_with_text_widget.hide()
        self.progressBar_widget.hide()
        self.bottom_right_top_widget.hide()
        self.scrollarea_canvas.hide()
        self.widget_time_slider.hide()

        # 下面是一个水平布局的窗口
        bottom_right_button_hlayout = QHBoxLayout()
        bottom_right_button_hlayout.setContentsMargins(32, 24, 32, 0)
        bottom_right_button_hlayout.setSpacing(24)

        # 添加分割线
        separator_bottom_right = QFrame()
        separator_bottom_right.setFrameShape(QFrame.HLine)
        separator_bottom_right.setFrameShadow(QFrame.Plain)
        separator_bottom_right.setStyleSheet("background-color: #a9a9a9;")
        separator_bottom_right.setFixedHeight(1)

        # analyse
        self.pushButton_analyse.setObjectName("pushButton_analyse")
        self.pushButton_analyse.setMinimumSize(145, 40)
        self.pushButton_analyse.setStyleSheet(ControlStyle.get_pushButton_style())
        ControlStyle.get_font_size(self.pushButton_analyse, 10)

        # 加载历史按钮
        self.pushButton_load_history = QPushButton(epilepsy_analysis)
        self.pushButton_load_history.setMinimumSize(145, 40)
        self.pushButton_load_history.setStyleSheet(ControlStyle.get_pushButton_style())
        ControlStyle.get_font_size(self.pushButton_load_history, 10)

        # 创建一个空白区域
        spacerItem = QSpacerItem(603, 32, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # save pic
        self.pushButton_save_pic = QPushButton(epilepsy_analysis)
        self.pushButton_save_pic.setObjectName("pushButton_save_pic")
        self.pushButton_save_pic.setMinimumSize(145, 40)
        self.pushButton_save_pic.setStyleSheet(ControlStyle.get_pushButton_style_white())
        self.pushButton_save_pic.setEnabled(False)
        ControlStyle.get_font_size(self.pushButton_save_pic, 10)

        # save data
        self.pushButton_save_data = QPushButton(epilepsy_analysis)
        self.pushButton_save_data.setObjectName("pushButton_save_data")
        self.pushButton_save_data.setMinimumSize(145, 40)
        self.pushButton_save_data.setStyleSheet(ControlStyle.get_pushButton_style_white())
        self.pushButton_save_data.setEnabled(False)
        ControlStyle.get_font_size(self.pushButton_save_data, 10)

        bottom_right_button_hlayout.addWidget(self.pushButton_analyse, alignment=Qt.AlignLeft)
        bottom_right_button_hlayout.addWidget(self.pushButton_load_history, alignment=Qt.AlignLeft)
        bottom_right_button_hlayout.addSpacerItem(spacerItem)
        bottom_right_button_hlayout.addWidget(self.pushButton_save_pic, alignment=Qt.AlignRight)
        bottom_right_button_hlayout.addWidget(self.pushButton_save_data, alignment=Qt.AlignRight)

        self.bottom_right_widget_vlayout.addWidget(self.draw_pic_widget)
        self.bottom_right_widget_vlayout.addWidget(separator_bottom_right)
        self.bottom_right_widget_vlayout.addLayout(bottom_right_button_hlayout)

        self.main_layout.addWidget(self.top_widget)
        self.main_layout.addWidget(separator)
        self.main_layout.addLayout(self.main_bottom_hlayout)

        self.retranslateUi(epilepsy_analysis)

        # 连接信号
        self.connect_signals()

        self.add_short_cut(epilepsy_analysis)

        # 加载界面
        self.loading_overlay = LoadingOverlay(self.draw_pic_widget)
        self.loading_overlay.setObjectName("loading_overlay")

        for pw in [self.plot_eeg, self.plot_emg, self.plot_acc, self.plot_widget]:
            pw.getViewBox().sigRangeChanged.connect(self._sync_hypnogram_xlim)

        self.widget_left_label = LeftTimeOverlay(self.plot_widget,  # 第二张图
                                                 anchor_parent=self.plot_widget,
                                                 corner='bottom-left', offset=(16, 0),
                                                 meas_date=None, dt_fmt='%Y-%m-%d %H:%M:%S', show_ms=True)
        # 调用绑定
        self._wire_box_select()
        self._init_epoch_boxes_ui()  # 先创建两个文本框
        self._connect_hover_signals()  # 再绑定悬浮信号（只读，不改绘图）

    # =================================================================
    # 新增方法：创建黄色警告栏
    # =================================================================
    def create_all_epochs_warning(self):
        """当选择 'All' 时显示顶部警告栏"""
        # 防止重复创建
        if hasattr(self, 'all_epochs_warning_bar'):
            return

        self.all_epochs_warning_bar = QFrame(self.draw_pic_widget)
        self.all_epochs_warning_bar.setObjectName("configWarningBar")
        self.all_epochs_warning_bar.setFixedHeight(40)

        # 【关键修改 2】样式表更新：
        # 1. 选择器改为 QFrame#configWarningBar
        # 2. 强制 QLabel 背景透明，防止文字遮挡黄色背景
        self.all_epochs_warning_bar.setStyleSheet("""
                    QFrame#configWarningBar {
                        background-color: #FFF4CE;  /* 淡黄色背景 */
                        border-bottom: 1px solid #E6D7A8;
                    }
                    QLabel {
                        background-color: transparent; /* 确保文字背景透明 */
                        color: #856404;  /* 深褐色文字 */
                        font-family: "Microsoft YaHei";
                        font-size: 14px;
                    }
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        border-radius: 3px;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        background-color: rgba(133, 100, 4, 0.1);
                    }
                """)

        # 创建水平布局
        layout = QHBoxLayout(self.all_epochs_warning_bar)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(10)

        # 警告图标
        warning_icon = QLabel()
        warning_pixmap = self.style().standardIcon(QStyle.SP_MessageBoxWarning).pixmap(16, 16)
        warning_icon.setPixmap(warning_pixmap)
        layout.addWidget(warning_icon)

        # 警告文本
        warning_text = QLabel()
        # 提示文本：显示所有 Epoch 可能导致性能卡顿
        text = "Zooming with the scroll wheel may cause lag when displaying all epochs."
        warning_text.setText(text)
        warning_text.setWordWrap(True)
        layout.addWidget(warning_text, 1)  # 添加伸缩因子

        # 关闭按钮
        close_btn = QPushButton()
        close_btn.setIcon(self.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        close_btn.setFixedSize(12, 12)
        close_btn.setToolTip("Close this message")
        close_btn.clicked.connect(self.close_all_epochs_warning)
        # 单独设置关闭按钮样式
        close_btn.setStyleSheet("""
                    QPushButton {
                        border: none; 
                        background: transparent;
                        padding: 8px;
                    }
                    QPushButton:hover {
                        background-color: rgba(133, 100, 4, 0.1);
                        border-radius: 1px;
                    }
                """)
        layout.addWidget(close_btn)

        # 将警告栏插入到 draw_pic_widget 的布局中
        # draw_pic_vlayout 的顺序通常是: 0:icon, 1:progress, 2:toolbar, 3:charts
        # 我们把它插在 Toolbar (索引2) 之后，Charts (索引3) 之前
        layout_instance = self.draw_pic_widget.layout()
        if layout_instance:
            # 插入到索引 3 的位置
            layout_instance.insertWidget(3, self.all_epochs_warning_bar)
            self.all_epochs_warning_bar.show()

    def close_all_epochs_warning(self):
        """关闭并清理警告栏"""
        if hasattr(self, 'all_epochs_warning_bar'):
            self.all_epochs_warning_bar.close()
            self.all_epochs_warning_bar.deleteLater()
            del self.all_epochs_warning_bar

    def _init_epoch_boxes_ui(self):
        """
        仅新增两个文本框，不修改任何已有布局和绘图。
        """
        try:
            self._left_extra_panel = QWidget(self)
            extra_layout = QVBoxLayout(self._left_extra_panel)
            # 调整边距/间距，让它和左侧参数区更接近
            extra_layout.setContentsMargins(32, 16, 32, 16)
            extra_layout.setSpacing(8)

            # 通用的文本框样式（对齐界面里其它白色输入框/按钮的风格）
            lineedit_style = """
                              QLineEdit {
                                  border: 1px solid #D4D6D9;
                                  border-radius: 4px;
                                  padding: 0 12px;
                                  background: #FFFFFF;
                                  color: #000000;
                              }
                              QLineEdit:focus {
                                  border: 1px solid #4A90E2;
                              }
                              QLineEdit:disabled {
                                  background: #F5F5F5;
                                  color: #A0A3A8;
                              }
                          """

            # 1) 跳转到 Epoch
            lbl_goto = QLabel("Turn to Epoch", self._left_extra_panel)
            lbl_goto.setObjectName("label_goto_epoch")
            # label 样式对齐其余参数区的小标题
            lbl_goto.setStyleSheet(ControlStyle.get_label_wordSmall_style())
            ControlStyle.get_font_size(lbl_goto, 10)

            self.lineedit_goto_epoch = QLineEdit(self._left_extra_panel)
            self.lineedit_goto_epoch.setObjectName("lineedit_goto_epoch")
            self.lineedit_goto_epoch.setPlaceholderText("Enter epoch 1~N:")
            self.lineedit_goto_epoch.setClearButtonEnabled(False)
            # 大小 / 形状
            self.lineedit_goto_epoch.setMinimumHeight(32)
            self.lineedit_goto_epoch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            # 文本框样式
            self.lineedit_goto_epoch.setStyleSheet(lineedit_style)
            ControlStyle.get_font_size(self.lineedit_goto_epoch, 10)
            # 初始化时默认禁用，防止未分析就输入
            self.lineedit_goto_epoch.setEnabled(False)
            # 安装事件过滤器（监听鼠标进入/离开事件）
            self.lineedit_goto_epoch.installEventFilter(self)
            self.lineedit_goto_epoch.setEnabled(False)
            self.lineedit_goto_epoch.setText("1")
            self.lineedit_goto_epoch.installEventFilter(self)


            # 2) 鼠标所在 Epoch（只读）
            lbl_mouse_epoch = QLabel("Current Epoch", self._left_extra_panel)
            lbl_mouse_epoch.setObjectName("label_mouse_epoch")
            lbl_mouse_epoch.setStyleSheet(ControlStyle.get_label_wordSmall_style())
            ControlStyle.get_font_size(lbl_mouse_epoch, 10)

            self.lineedit_mouse_epoch = QLineEdit(self._left_extra_panel)
            self.lineedit_mouse_epoch.setObjectName("lineedit_mouse_epoch")
            self.lineedit_mouse_epoch.setReadOnly(True)
            self.lineedit_mouse_epoch.setPlaceholderText("Move the mouse over graph...")
            self.lineedit_mouse_epoch.setMinimumHeight(32)
            self.lineedit_mouse_epoch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.lineedit_mouse_epoch.setStyleSheet(lineedit_style)
            ControlStyle.get_font_size(self.lineedit_mouse_epoch, 10)

            # ========== 滑动调整轴 ==========
            self.slider_goto_epoch = QSlider(Qt.Orientation.Horizontal, self._left_extra_panel)
            self.slider_goto_epoch.setValue(1)
            self.slider_goto_epoch.hide()  # 初始隐藏
            self.slider_goto_epoch.raise_()  # 置顶显示，避免被遮挡
            self.slider_goto_epoch.setStyleSheet(ControlStyle.get_slider_style())
            self.slider_goto_epoch.installEventFilter(self)  # 给滑块也装事件过滤器

            extra_layout.addWidget(lbl_goto)
            extra_layout.addWidget(self.lineedit_goto_epoch)
            extra_layout.addSpacing(6)
            extra_layout.addWidget(lbl_mouse_epoch)
            extra_layout.addWidget(self.lineedit_mouse_epoch)

            # 把这块挂到你的侧栏容器（保持原样，不拆改原控件）
            if hasattr(self, "sidebar"):
                self.sidebar.add_widget(self._left_extra_panel)
            else:
                # 若你没有 sidebar，就把它塞到主布局（如有）
                if hasattr(self, "verticalLayout"):
                    self.verticalLayout.addWidget(self._left_extra_panel)

            # 绑定“回车跳转” -> 严格走你现有的跳转与单 epoch 选中流程
            self.lineedit_goto_epoch.returnPressed.connect(self._on_goto_epoch_entered)
            self.lineedit_goto_epoch.textChanged.connect(self._on_goto_epoch_entered)

        except Exception as e:
            try:
                QLLogging.log.exception(f"_init_epoch_boxes_ui error: {e}")
            except Exception:
                print(f"_init_epoch_boxes_ui error: {e}")

    # 新增：滑块→输入框同步（简化逻辑，避免lambda拦截）
    def _on_slider_value_changed(self, value):
        """滑块值变化：直接赋值给输入框，确保范围有效"""
        if 1 <= value <= self.n_epochs:
            self.lineedit_goto_epoch.setText(str(value))

    # 新增：输入框→滑块同步（处理strip+范围）
    def _on_input_text_changed(self):
        """输入框值变化：处理后同步到滑块"""
        text = self.lineedit_goto_epoch.text().strip()
        if text.isdigit():
            val = int(text)
            if 1 <= val <= self.n_epochs:
                self.slider_goto_epoch.setValue(val)

    # ===== A.3 悬浮信号绑定（不改变绘图，只读鼠标位置） =====

    def _connect_hover_signals(self):
        """
        悬浮只读：从已存在的 pyqtgraph / Matplotlib 取鼠标 x，换算 epoch 序号 -> 显示到只读框。
        不改任何绘图与交互。
        """
        try:
            # 1) 绑定 pyqtgraph 场景的鼠标移动
            self._plots_for_hover = []
            for name in ("plot_eeg", "plot_emg", "plot_acc", "plot_widget"):
                if hasattr(self, name):
                    obj = getattr(self, name)
                    # 只要是 pg 的 PlotWidget（带 scene/plotItem 即可）
                    if hasattr(obj, "scene") or (hasattr(obj, "plotItem") and hasattr(obj.plotItem, "vb")):
                        self._plots_for_hover.append(obj)

            self._hover_proxies = []
            for p in self._plots_for_hover:
                proxy = pg.SignalProxy(p.scene().sigMouseMoved, rateLimit=60, slot=self._on_scene_mouse_moved)
                self._hover_proxies.append(proxy)

            # 2) 如你的分期图是 Matplotlib，同步监听（仍不做绘图改动）
            if hasattr(self, "canvas") and hasattr(self, "figure") and not hasattr(self, "_mpl_hover_cid"):
                self._mpl_hover_cid = self.canvas.mpl_connect("motion_notify_event", self._on_mpl_mouse_move)

        except Exception as e:
            try:
                QLLogging.log.exception(f"_connect_hover_signals error: {e}")
            except Exception:
                print(f"_connect_hover_signals error: {e}")

        # ===== A.4 “回车跳转”：调用你原有的分页/时间轴机制，然后调用你原本的“单 epoch 选中”逻辑 =====

    def _on_goto_epoch_entered(self):
        """
        严格遵循：不改绘图。
        步骤：
          1) 算该 epoch 所在页的起始时间（秒），把你现有的滑块挪过去 -> 触发 update_display_range()（与你现有 goto 流程一致）
          2) 调“你原本的单 epoch 选中逻辑”（和点击分期图的行为一致；通过多候选方法名自适配）
        """
        try:
            text = self.lineedit_goto_epoch.text().strip()
            if not text:
                return
            # e = int(text)
            # UI输入改为1-x 1~n_epochs
            user_idx = int(text)
            if not hasattr(self, "n_epochs") or self.n_epochs is None:
                QMessageBox.warning(self, "缺少信息", "未检测到 n_epochs。")
                return
            n_epochs = int(self.n_epochs)
            if user_idx < 0 or user_idx > n_epochs:
                QMessageBox.warning(self, "无效的 Epoch", f"请输入 1 ~ {n_epochs} 之间的整数。")
                return
            # 内部仍使用0-x索引
            e = user_idx - 1
            if not hasattr(self, "thread_run") or not hasattr(self.thread_run, "epoch_length"):
                QMessageBox.warning(self, "缺少信息", "未检测到 thread_run.epoch_length。")
                return

            epoch_len = int(self.thread_run.epoch_length)
            if epoch_len <= 0:
                QMessageBox.warning(self, "参数异常", "epoch_length 应为正整数。")
                return

            # —— (1) 仅用你已有的“分页/滑块”逻辑完成跳转（不改绘图）——
            # 当前每页显示多少个 epoch（你的现有函数）
            n_display = int(self.get_n_epochs_display()) if hasattr(self, "get_n_epochs_display") else 1
            total_sec = int(self.get_total_time_number().total_seconds()) if hasattr(self,
                                                                                     "get_total_time_number") else (
                    n_epochs * epoch_len)

            page_idx = e // max(1, n_display)
            page_start_sec = page_idx * max(1, n_display) * epoch_len
            page_start_sec = max(0, min(page_start_sec, max(0, total_sec - max(1, n_display) * epoch_len)))

            # 和你原先 update_display_goto_epoch 一致：直接设 slider 值 -> 触发刷新（不弹框）
            if hasattr(self, "widget_time_slider") and hasattr(self.widget_time_slider, "time_slider"):
                self.widget_time_slider.time_slider.setValue(int(page_start_sec))
            if hasattr(self, "update_display_range"):
                self.update_display_range()

            self._clear_range_markers(clear_zoom=False)
            self._clear_mpl_spans(clear_zoom=False)

            target_plots = []
            for name in ["plot_eeg", "plot_emg", "plot_acc", "plot_widget"]:
                if hasattr(self, name):
                    target_plots.append(getattr(self, name))

            self._mark_selected_range(
                target_plots,
                e * epoch_len,
                (e + 1) * epoch_len,
                persist_ms=0,
                also_mark_mpl=True,
                is_zoom=False  # 关键：标记为普通跳转高亮
            )

        except ValueError:
            QMessageBox.warning(self, "格式错误", "请输入整数 epoch 序号。")
        except Exception as ex:
            try:
                QLLogging.log.exception(f"_on_goto_epoch_entered error: {ex}")
            except Exception:
                print(f"_on_goto_epoch_entered error: {ex}")

        # ===== A.6 悬浮：pyqtgraph 图上动态显示鼠标所在 epoch（只读，不改图） =====

    def _on_scene_mouse_moved(self, evt):
        if not hasattr(self, "lineedit_mouse_epoch"):
            return
        try:
            pos = evt[0]
            if not hasattr(self, "thread_run") or not hasattr(self.thread_run, "epoch_length"):
                return
            epoch_len = int(self.thread_run.epoch_length)
            if epoch_len <= 0:
                return
            n_epochs = int(self.n_epochs) if hasattr(self, "n_epochs") else None

            # 找到当前鼠标所在的 ViewBox
            for p in getattr(self, "_plots_for_hover", []):
                if not hasattr(p, "plotItem") or not hasattr(p.plotItem, "vb"):
                    continue
                vb = p.plotItem.vb
                if not vb.sceneBoundingRect().contains(pos):
                    continue
                # 场景坐标 -> 数据坐标（x 单位 = 秒）
                x = float(vb.mapSceneToView(pos).x())
                if not math.isfinite(x):
                    continue
                e = int(x // epoch_len)
                if n_epochs is not None and (e < 0 or e >= n_epochs):
                    return
                # —— 仅更新文本框；不画任何东西 ——
                self.lineedit_mouse_epoch.setText(str(e + 1))
                return
        except Exception as ex:
            try:
                QLLogging.log.exception(f"_on_scene_mouse_moved error: {ex}")
            except Exception:
                print(f"_on_scene_mouse_moved error: {ex}")

        # ===== A.7 悬浮：Matplotlib 分期图（若使用 MPL）上动态显示 epoch（只读，不改图） =====

    def _on_mpl_mouse_move(self, event):
        if not hasattr(self, "lineedit_mouse_epoch"):
            return
        try:
            if event is None or event.xdata is None:
                return
            if not hasattr(self, "thread_run") or not hasattr(self.thread_run, "epoch_length"):
                return
            epoch_len = int(self.thread_run.epoch_length)
            if epoch_len <= 0:
                return
            x = float(event.xdata)
            if not math.isfinite(x):
                return
            e = int(x // epoch_len)
            if hasattr(self, "n_epochs") and self.n_epochs is not None:
                n_epochs = int(self.n_epochs)
                if e < 0 or e >= n_epochs:
                    return
            # —— 仅更新文本框；不画任何东西 ——
            self.lineedit_mouse_epoch.setText(str(e + 1))
        except Exception as ex:
            try:
                QLLogging.log.exception(f"_on_mpl_mouse_move error: {ex}")
            except Exception:
                print(f"_on_mpl_mouse_move error: {ex}")

    def _clear_range_markers(self, clear_zoom=False):
        """移除所有 pyqtgraph 选区高亮（仅在需要时手动调用）"""
        # 使用 list(items) 创建副本进行遍历，以便安全修改原列表
        for p, items in list(self._range_markers.items()):
            # 倒序遍历，方便移除
            for i in range(len(items) - 1, -1, -1):
                it = items[i]
                # 如果不是强制清除，且该 item 是放大高亮，则跳过（保留它）
                if not clear_zoom and getattr(it, 'is_zoom', False):
                    continue
                # 从图层移除
                try:
                    p.removeItem(it)
                except Exception:
                    pass
                # 从列表中移除引用
                items.pop(i)
            # 如果该 plot 下没有任何标记了，才删除 key
            if not items:
                del self._range_markers[p]

    def _clear_mpl_spans(self, clear_zoom=False):
        """移除所有 Matplotlib 选区高亮"""
        if getattr(self, "_mpl_spans", None):
            # 倒序遍历
            for i in range(len(self._mpl_spans) - 1, -1, -1):
                sp = self._mpl_spans[i]
                # 保留 zoom 高亮
                if not clear_zoom and getattr(sp, 'is_zoom', False):
                    continue
                # 移除
                try:
                    sp.remove()
                except Exception:
                    pass
                # 从列表中删除
                self._mpl_spans.pop(i)
            try:
                self.canvas.draw_idle()
            except Exception:
                pass

    def _mark_selected_range(self, plots, x_min, x_max, persist_ms=1500, also_mark_mpl=True, is_zoom=False):
        """
        在给定的 plots 上用 LinearRegionItem 标记 [x_min, x_max]。
        persist_ms: 持续时间；>0 则自动淡出；<=0 则常驻直到下次覆盖/清理。
        also_mark_mpl: 是否同时在 Matplotlib hypnogram 上画 axvspan。
        """

        for p in plots:
            region = pg.LinearRegionItem(values=(float(x_min), float(x_max)))
            region.setZValue(10)
            region.setMovable(False)
            region.setBrush(self._hl_brush)
            region.is_zoom = is_zoom
            try:
                region.setPen(self._hl_pen)  # 新版
            except Exception:
                for ln in getattr(region, "lines", []) or []:
                    try:
                        ln.setPen(self._hl_pen)
                    except Exception:
                        pass
            try:
                p.addItem(region)
                # 改为列表累积
                self._range_markers.setdefault(p, []).append(region)
            except Exception:
                pass

            # Matplotlib 分期图高亮（默认不启用）
        if also_mark_mpl and getattr(self, "figure", None) is not None:
            try:
                for ax in self.figure.axes:
                    sp = ax.axvspan(float(x_min), float(x_max),
                                    facecolor="#6495ED", alpha=0.15, edgecolor="#6495ED",
                                    linewidth=0, zorder=0)
                    sp.is_zoom = is_zoom
                    self._mpl_spans.append(sp)
                self.canvas.draw_idle()
            except Exception:
                pass

        # 自动淡出
        if persist_ms and persist_ms > 0:
            # 先取消之前的淡出计时器
            if getattr(self, "_marker_fade_timer", None):
                try:
                    self._marker_fade_timer.stop()
                    self._marker_fade_timer.deleteLater()
                except Exception:
                    pass
                self._marker_fade_timer = None

            step_ms = 40
            total_steps = max(1, int(persist_ms / step_ms))
            self._marker_fade_step = 0

            def _tick():
                self._marker_fade_step += 1
                t = self._marker_fade_step / float(total_steps)
                opacity = max(0.0, 1.0 - t)
                # pg 区域淡出
                for item in list(self._range_markers.values()):
                    try:
                        item.setOpacity(opacity)
                    except Exception:
                        pass
                # mpl 区域淡出
                for sp in getattr(self, "_mpl_spans", []):
                    try:
                        sp.set_alpha(0.15 * opacity)
                    except Exception:
                        pass
                try:
                    if getattr(self, "canvas", None):
                        self.canvas.draw_idle()
                except Exception:
                    pass

                if self._marker_fade_step >= total_steps:
                    # 结束后彻底清理
                    self._clear_range_markers()
                    self._clear_mpl_spans()
                    try:
                        self._marker_fade_timer.stop()
                        self._marker_fade_timer.deleteLater()
                    except Exception:
                        pass

            self._marker_fade_timer = QTimer(self)
            self._marker_fade_timer.timeout.connect(_tick)
            self._marker_fade_timer.start(step_ms)

    def _sync_hypnogram_xlim(self, viewbox, ranges):
        # ranges 形如 ((xMin, xMax), (yMin, yMax))
        # 分期图的缩放重绘
        try:
            (x_min, x_max), _ = ranges
        except Exception:
            (x_min, x_max), _ = viewbox.viewRange()  # 兜底

        # 同步所有 Matplotlib axes
        for ax in self.figure.axes:
            ax.set_xlim(x_min, x_max)

        # 轻量重绘，不卡 UI
        self.canvas.draw_idle()

    def _check_hide_slider(self):
        """统一检查滑块是否需要隐藏（核心逻辑）"""
        # 仅当鼠标既离开输入框、又离开滑块时，才隐藏滑块
        if not self._is_input_hover and not self._is_slider_hover:
            self.slider_goto_epoch.hide()

    def eventFilter(self, obj, event):
        # todo 事件过滤器：监听输入框的鼠标进入/离开
        if obj == self.lineedit_goto_epoch:
            # 鼠标进入输入框：计算位置+显示滑块
            if event.type() == QEvent.Enter:
                self._is_input_hover = True
                # 1. 计算输入框在面板中的绝对位置（关键！）
                input_rect = self.lineedit_goto_epoch.geometry()
                input_pos = self.lineedit_goto_epoch.mapToParent(input_rect.topLeft())
                # 滑块位置：输入框正下方（x相同，y=输入框y+高度+1像素）
                slider_x = input_rect.x()
                slider_y = input_rect.y() + input_rect.height() + 1
                # 滑块宽度：和输入框一致
                slider_width = input_rect.width()
                # 2. 设置滑块位置和大小
                self.slider_goto_epoch.setGeometry(slider_x, slider_y, slider_width, 40)
                # 3. 同步输入框值到滑块+显示+置顶
                text = self.lineedit_goto_epoch.text().strip()
                self.slider_goto_epoch.setValue(int(text) if text.isdigit() else 1)
                self.slider_goto_epoch.show()
                self.slider_goto_epoch.raise_()  # 确保置顶
                return False

            # 鼠标离开输入框：隐藏滑块
            elif event.type() == QEvent.Leave:
                self._is_input_hover = False
                QTimer.singleShot(200, self._check_hide_slider)
                return False

        elif obj == self.slider_goto_epoch:
            if event.type() == QEvent.Enter:
                self._is_slider_hover = True
                # 确保滑块保持显示（防止输入框Leave时误隐藏）
                self.slider_goto_epoch.show()
                print(self.slider_goto_epoch.value())
                return False

            elif event.type() == QEvent.Leave:
                self._is_slider_hover = False
                QTimer.singleShot(200, self._check_hide_slider)
                return False

        # 放大弹窗里的 Ctrl+滚轮：只缩放 Y 轴
        if hasattr(self, "_zoom_viewports") and obj in self._zoom_viewports:
            vb = self._zoom_viewport_map.get(obj)
            # 确保 vb 存在，且只处理鼠标/滚轮相关事件
            if vb is not None and event.type() in (
                    QEvent.Wheel, QEvent.MouseButtonPress, QEvent.MouseButtonRelease, QEvent.MouseMove):

                # 检查是否按下了 Ctrl 键
                if event.modifiers() & Qt.ControlModifier:
                    # 按下 Ctrl：禁用 X，启用 Y (实现 Y 轴拖拽和缩放)
                    vb.setMouseEnabled(x=False, y=True)
                else:
                    # 没按 Ctrl：启用 X，禁用 Y (恢复默认的时间轴拖拽和缩放)
                    vb.setMouseEnabled(x=True, y=False)

                # 【关键】返回 False，表示“我没处理完，请继续传递给原控件”。
                # 这样 PyQtGraph 就会接收到事件，并根据上面设置好的 x/y enabled 状态
                # 自动执行缩放或平移。
                return False

            # 非 Ctrl+滚轮（包括普通滚轮），交给默认处理
            return super().eventFilter(obj, event)
        # 找到触发这个事件的是哪个 PlotWidget
        plot_of = None
        title_of = None
        for p, t in getattr(self, "_plot_titles", {}).items():
            try:
                if p.viewport() is obj:
                    plot_of, title_of = p, t
                    break
            except RuntimeError:
                # 忽略已销毁的对象
                continue

        if plot_of is None:
            return super().eventFilter(obj, event)

        et = event.type()

        if et == QEvent.MouseButtonPress:
            self._clear_range_markers(clear_zoom=False)
            self._clear_mpl_spans(clear_zoom=False)

        # 1) 左键按下（无修饰键） => 开始矩形框（rubber band）
        if (et == QEvent.MouseButtonPress and event.button() == Qt.LeftButton and (
                event.modifiers() & Qt.ShiftModifier)):
            self._begin_rubber_band(plot_of, event.pos())
            return True  # 消费事件

        # 2) 鼠标移动 => 更新矩形
        if et == QEvent.MouseMove and self._rb is not None and self._rb_plot is plot_of:
            self._update_rubber_band(event.pos())
            return True

        # 3) 左键释放 => 结束矩形，拿到数据坐标矩形，执行后续动作
        if (et == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton
                and self._rb is not None and self._rb_plot is plot_of):
            x_min, x_max, plots_hit = self._finish_rubber_band_and_get_xrange_and_plots(plot_of)
            if x_min is not None:
                # 常驻：不淡出；且不在 Matplotlib 分期图上画高亮
                self._mark_selected_range(plots_hit, x_min, x_max, persist_ms=0, also_mark_mpl=False, is_zoom=True)
                # 为每个命中的 plot 开窗，并把“该 plot 的本次高亮 region”绑到对应窗上
                for p in plots_hit:
                    dlg = self.show_zoom_window_for_xrange(p, self._plot_titles[p], x_min, x_max)  # 注意此函数需返回对话框
                    # 将本次最新添加的 region 绑定到这个对话框（关闭窗时清除）
                    rlist = self._range_markers.get(p, [])
                    if rlist:
                        try:
                            self._zoom_markers[dlg]["items"].append(rlist[-1])
                        except Exception:
                            pass
            return True

        return super().eventFilter(obj, event)

    def _wire_box_select(self):
        """为四个plot绑定"""
        self._plot_titles = {
            self.plot_eeg: "EEG",
            self.plot_emg: "EMG",
            self.plot_acc: "ACC",
        }
        # 事件分发
        for p, title in self._plot_titles.items():
            p.viewport().installEventFilter(self)

    def show_zoom_window_for_xrange(self, source_plot, title, x_min, x_max):
        from .left_time_overlay import DateAxis
        """简洁版放大窗：与当前文件弹窗风格一致；Y 轴自适应，X 轴锁定到选区"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout
        import pyqtgraph as pg
        import numpy as np

        # 1) 轻量弹窗（统一大小/风格）
        dlg = QDialog(self)
        meas_date = self.raw_processed.info['meas_date']
        sec_start = round(float(x_min), 3)
        sec_end = round(float(x_max), 3)
        ms_start = int(round(sec_start * 1000))
        ms_end = int(round(sec_end * 1000))
        abs_start = meas_date + datetime.timedelta(milliseconds=ms_start)
        abs_end = meas_date + datetime.timedelta(milliseconds=ms_end)
        start_str = abs_start.strftime("%Y-%m-%d %H:%M:%S") + f".{ms_start % 1000:03d}"
        end_str = abs_end.strftime("%Y-%m-%d %H:%M:%S") + f".{ms_end % 1000:03d}"
        dlg.setWindowTitle(f"{title}  [{start_str} – {end_str}]")
        lay = QVBoxLayout(dlg)
        date_axis = DateAxis(meas_date, orientation='bottom')
        zoom_plot = pg.PlotWidget(axisItems={'bottom': date_axis})
        lay.addWidget(zoom_plot)
        dlg.resize(900, 320)  # 和文件里的弹窗尺寸保持一致
        zoom_plot.setBackground("w")
        zoom_plot.showGrid(x=True, y=True, alpha=0.3)
        zoom_plot.setMouseEnabled(x=True, y=False)
        zoom_plot.setMenuEnabled(False)
        zoom_pi = zoom_plot.getPlotItem()

        # 2) 仅复制“选区内”的曲线数据（去掉 ImageItem/复杂功能）
        ymins, ymaxs = [], []
        for it in source_plot.listDataItems():
            try:
                xd, yd = it.getData()
            except Exception:
                continue
            if xd is None or yd is None or len(xd) == 0:
                continue
            m = (xd >= x_min) & (xd <= x_max)
            if np.any(m):
                x_sel, y_sel = xd[m], yd[m]
                zoom_pi.addItem(pg.PlotDataItem(x=x_sel, y=y_sel, pen=it.opts.get('pen', None)))
                ymins.append(np.nanmin(y_sel))
                ymaxs.append(np.nanmax(y_sel))

        # 3) 轴范围：X 固定在选区；Y 按选区数据自适应（加少量边距）
        zoom_plot.setXRange(x_min, x_max, padding=0)
        if ymins and ymaxs:
            y0, y1 = float(np.min(ymins)), float(np.max(ymaxs))
            if np.isfinite(y0) and np.isfinite(y1) and y1 > y0:
                pad = (y1 - y0) * 0.10  # 10% 边距
                zoom_pi.setYRange(y0 - pad, y1 + pad, padding=0)
            else:
                zoom_pi.enableAutoRange(axis=pg.ViewBox.YAxis)
        else:
            # 选区里没有数据时，退回自动
            zoom_pi.enableAutoRange(axis=pg.ViewBox.YAxis)

        # 让放大弹窗支持 Ctrl+滚轮 单独缩放 Y 轴
        vp = zoom_plot.viewport()
        vp.installEventFilter(self)
        self._zoom_viewports.add(vp)
        self._zoom_viewport_map[vp] = zoom_pi.vb
        dlg._zoom_viewport = vp  # 方便关闭时清理

        # 绑定：为该弹窗准备一个记录槽位，并加入窗口列表
        self._zoom_markers[dlg] = {"plot": source_plot, "items": []}
        if dlg not in self._zoom_windows:
            self._zoom_windows.append(dlg)

        # 关闭时清理对应的高亮
        dlg.finished.connect(lambda _: self._cleanup_zoom_dialog(dlg))
        dlg.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        dlg.show()
        return dlg

    def _begin_rubber_band(self, plot, pos_in_viewport):
        from PyQt5.QtWidgets import QRubberBand
        from PyQt5.QtCore import QRect, QPoint, QSize

        # 统一把橡皮筋挂在 scrollarea 的 viewport 上，这样矩形可以跨越多个 PlotWidget
        host = self.scrollarea_canvas.viewport()
        self._rb_host = host
        self._rb_plot = plot  # 记住起始图，后续用它把 host-x 映射到数据x

        # 把点击点从“当前plot的viewport坐标” -> “host坐标”
        gpt = plot.viewport().mapToGlobal(pos_in_viewport)
        host_pt = host.mapFromGlobal(gpt)

        self._rb_origin = host_pt
        if self._rb is None:
            self._rb = QRubberBand(QRubberBand.Rectangle, host)
        self._rb.setGeometry(QRect(self._rb_origin, QSize()))
        self._rb.show()

    def _update_rubber_band(self, pos_in_viewport):
        from PyQt5.QtCore import QRect, QPoint
        if self._rb is None or self._rb_host is None or self._rb_plot is None:
            return
        # 传入的是当前plot的viewport坐标，转为host坐标
        gpt = self._rb_plot.viewport().mapToGlobal(pos_in_viewport)
        host_pt = self._rb_host.mapFromGlobal(gpt)
        rect = QRect(self._rb_origin, host_pt).normalized()
        self._rb.setGeometry(rect)

    def _finish_rubber_band_and_get_xrange_and_plots(self, start_plot):
        """
        以 host（scrollarea viewport）为坐标系：
        - 得到选框rect（仅取左右X，忽略Y）
        - 把左右X映射到 start_plot 的数据x（秒）
        - 找出与选框有垂直交集的所有 PlotWidget，返回列表
        """
        from PyQt5.QtCore import QPoint, QRect

        if self._rb is None or self._rb_host is None or self._rb_plot is None:
            return (None, None, [])

        # 1) 取host坐标系下的选框
        sel_rect_host = self._rb.geometry()
        self._rb.hide()
        # 清理句柄
        self._rb = None
        self._rb_origin = None

        # 2) 只要左右X，映射成 start_plot 的数据x
        def host_x_to_plot_x(host_x, plot):
            # 取该plot在host中的“竖向中线”高度（用于构造一个场景点）
            center_vp = plot.viewport().rect().center()
            center_host = self._rb_host.mapFromGlobal(plot.viewport().mapToGlobal(center_vp))
            # host点 -> global -> 目标plot的viewport -> scene -> data
            from PyQt5.QtCore import QPoint
            pt_host = QPoint(host_x, center_host.y())

            pt_vp = plot.viewport().mapFromGlobal(self._rb_host.mapToGlobal(pt_host))
            scene_pt = plot.mapToScene(pt_vp)
            data_pt = plot.getPlotItem().vb.mapSceneToView(scene_pt)
            return data_pt.x()

        x_min = host_x_to_plot_x(sel_rect_host.left(), start_plot)
        x_max = host_x_to_plot_x(sel_rect_host.right(), start_plot)
        if x_min > x_max:
            x_min, x_max = x_max, x_min

        vb = start_plot.getPlotItem().vb
        try:
            vis_x0, vis_x1 = vb.viewRange()[0]
            x_min = max(vis_x0, min(x_min, vis_x1))
            x_max = max(vis_x0, min(x_max, vis_x1))
        except Exception:
            pass

        # 3) 找和选框有“垂直方向交集”的所有plot（以host坐标判断矩形相交）
        plots_hit = []
        for p in self._plot_titles.keys():
            vp = p.viewport()
            # 把该plot的viewport矩形转换为host坐标
            top_left_host = self._rb_host.mapFromGlobal(vp.mapToGlobal(vp.rect().topLeft()))
            rect_host = QRect(top_left_host, vp.rect().size())
            if rect_host.intersects(sel_rect_host):
                plots_hit.append(p)

        # 清理当前起始plot记录
        self._rb_plot = None
        return (x_min, x_max, plots_hit)

    def _cleanup_zoom_dialog(self, dialog):
        info = self._zoom_markers.pop(dialog, None)
        if info:
            plot = info.get("plot")
            for it in list(info.get("items", [])):
                # 先从图上移除
                try:
                    plot.removeItem(it)
                except Exception:
                    pass
                # 再从追踪表里剔除
                try:
                    lst = self._range_markers.get(plot, [])
                    if it in lst:
                        lst.remove(it)
                        if not lst:
                            self._range_markers.pop(plot, None)
                except Exception:
                    pass

        # 清理放大窗 viewport 的事件过滤器和映射
        try:
            vp = getattr(dialog, "_zoom_viewport", None)
            if vp is not None and hasattr(self, "_zoom_viewports"):
                if vp in self._zoom_viewports:
                    try:
                        vp.removeEventFilter(self)
                    except Exception:
                        pass
                    self._zoom_viewports.discard(vp)
                    self._zoom_viewport_map.pop(vp, None)
        except Exception:
            pass

        # 最后移除窗口引用
        try:
            if dialog in self._zoom_windows:
                self._zoom_windows.remove(dialog)
        except Exception:
            pass

    def retranslateUi(self, epilepsy_analysis):
        _translate = QCoreApplication.translate
        self.top_widget.nav_buttons_widget.button_goto_epoch.setText(_translate("epilepsy_analysis", "0"))
        # self.bottom_left_widget.label_events.setText(_translate("epilepsy_analysis", "Events"))
        # self.bottom_left_widget.pushButton_events.setText(_translate("epilepsy_analysis", "import"))
        self.set_bottom_left_widget_start_end_time_text()
        self.pushButton_analyse.setText(_translate("epilepsy_analysis", "Analyse"))
        self.pushButton_load_history.setText(_translate("epilepsy_analysis", "Load History"))
        self.pushButton_save_pic.setText(_translate("epilepsy_analysis", "Save pic"))
        self.pushButton_save_data.setText(_translate("epilepsy_analysis", "Save data"))

    def connect_signals(self):
        self.top_widget.combobox_select_n_epochs.currentTextChanged.connect(self.update_display_n_epochs)
        self.top_widget.nav_buttons_widget.first_pushButton.clicked.connect(self.update_display_first)
        self.top_widget.nav_buttons_widget.last_pushButton.clicked.connect(self.update_display_last)
        self.top_widget.nav_buttons_widget.button_previous.clicked.connect(self.update_display_previous_more)
        self.top_widget.nav_buttons_widget.button_next.clicked.connect(self.update_display_next_more)
        self.top_widget.nav_buttons_widget.button_goto_epoch.clicked.connect(self.update_display_goto_epoch)

        self.pushButton_analyse.clicked.connect(self.analysis_clicked)
        self.pushButton_load_history.clicked.connect(self.on_pushButton_load_history_clicked)

        self.progressBar_completed.connect(self.progressBar_change_canvas_widget)

        self.widget_time_slider.time_slider.valueChanged.connect(self.on_slider_changed)

        self.bottom_right_top_widget.pushButton_normal.clicked.connect(lambda: self.seizure_normal_button_click(1))
        self.bottom_right_top_widget.pushButton_seizure.clicked.connect(lambda: self.seizure_normal_button_click(2))
        self.bottom_right_top_widget.pushButton_undo.clicked.connect(self.undo_edit)
        self.bottom_right_top_widget.pushButton_redo.clicked.connect(self.redo_edit)
        self.bottom_right_top_widget.pushButton_reset.clicked.connect(self.reset_edit)
        self.pushButton_save_pic.clicked.connect(self.open_save_picture_ui)
        self.pushButton_save_data.clicked.connect(self.open_save_data_ui)

    def add_short_cut(self, epilepsy_analysis):
        # 为Wake按钮添加Shift+1快捷键
        self.shortcut_normal = QShortcut(QKeySequence("Shift+1"), epilepsy_analysis)
        self.shortcut_normal.activated.connect(lambda: self.seizure_normal_button_click(1))

        # 为NREM按钮添加Shift+2快捷键
        self.shortcut_seizure = QShortcut(QKeySequence("Shift+2"), epilepsy_analysis)
        self.shortcut_seizure.activated.connect(lambda: self.seizure_normal_button_click(2))

        setup_short_cut(self.top_widget.nav_buttons_widget.button_previous,
                        self.top_widget.nav_buttons_widget.button_next,
                        epilepsy_analysis,
                        self.update_display_first,
                        self.update_display_last)

    def import_raw(self, raw, selected_channel=None):
        self.raw_processed = raw
        self.thread_run.raw_processed = self.raw_processed
        self.edf_path = raw.info['description']
        if raw is not None:
            # self.bottom_right_widget.pushButton
            self.pushButton_analyse.setEnabled(True)

            # 更新通道选择下拉菜单
            ch_names = raw.ch_names

            # Clear and update all channel comboboxes
            self.bottom_left_widget.combobox_eeg.clear()
            self.bottom_left_widget.combobox_emg.clear()
            self.bottom_left_widget.combobox_acc.clear()

            self.bottom_left_widget.combobox_emg.addItems(ch_names)
            self.bottom_left_widget.combobox_eeg.addItems(ch_names)
            self.bottom_left_widget.combobox_acc.addItems(ch_names)

            # Set default selections
            default_eeg = "EEG3"
            default_emg = "EEG1"  # Adjust as needed
            default_acc = "ACC0"  # Adjust as needed

            if default_eeg in ch_names:
                self.bottom_left_widget.combobox_eeg.setCurrentText(default_eeg)
            elif selected_channel is not None:
                self.bottom_left_widget.combobox_eeg.setCurrentIndex(selected_channel)

            if default_emg in ch_names:
                self.bottom_left_widget.combobox_emg.setCurrentText(default_emg)

            if default_acc in ch_names:
                self.bottom_left_widget.combobox_acc.setCurrentText(default_acc)

    def run_analysis(self):
        try:
            self._analysis_failed = False
            # 将首页页面隐藏，将进度条页面显示出来
            self.icon_with_text_widget.hide()
            # 将显示页面也隐藏
            self.bottom_right_top_widget.hide()
            self.scrollarea_canvas.hide()
            self.widget_time_slider.hide()
            self.progressBar_widget.show()
            self.bottom_left_widget.information_label.hide()

            # 获取选择的通道
            selected_channel = self.bottom_left_widget.combobox_eeg.currentIndex()
            selected_emg = self.bottom_left_widget.combobox_emg.currentIndex()
            selected_acc = self.bottom_left_widget.combobox_acc.currentIndex()

            self.thread_run.eeg_channel = selected_channel
            self.thread_run.emg_channel = selected_emg
            self.thread_run.acc_channel = selected_acc

            # 获取epoch长度
            epoch_length = float(self.bottom_left_widget.combobox_epoch_length.currentText())
            self.thread_run.epoch_length = epoch_length

            # 开始分析
            self.progressBar.resetValue()

            self.thread_run.start()  # 可以将这个使用两个线程来进行操作

            self.bottom_left_widget.connect_signals()  # 连接信号
            self.bottom_left_widget.combobox_epoch_length.currentTextChanged.connect(self.update_epoch_length)

        except Exception as e:
            QLLogging.log.exception(f"Analysis error: {str(e)}")

    def _handle_analysis_error(self, message):
        """收口后台线程错误，避免打包环境一直停留在“分析中”。"""
        self._analysis_failed = True
        error_message = str(message or "Unknown ML epilepsy analysis error")
        QLLogging.log.error(f"ML epilepsy analysis failed: {error_message}")

        try:
            if hasattr(self, "thread_run") and self.thread_run is not None and self.thread_run.isRunning():
                if not self.thread_run.wait(3000):
                    QLLogging.log.warning("ML epilepsy analysis thread did not stop within 3 seconds after error")
        except Exception:
            QLLogging.log.exception("Failed while waiting ML epilepsy analysis thread after error")

        # 打包环境中异常可能来自 hidden import / 模型路径；这里必须结束 loading 状态。
        for widget_name in ("label_progressBar", "progressBar", "label_draw", "progressBar_widget"):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.hide()

        icon_widget = getattr(self, "icon_with_text_widget", None)
        if icon_widget is not None:
            icon_widget.show()

        bottom_left = getattr(self, "bottom_left_widget", None)
        information_label = getattr(bottom_left, "information_label", None) if bottom_left is not None else None
        if information_label is not None:
            information_label.show()

        QApplication.processEvents()
        QMessageBox.critical(self, "ML Epilepsy Analysis Failed", error_message)

    def update_progress(self, emitted_signal):
        """更新进度条和状态"""
        if not hasattr(self, "progressBar") or not self.progressBar:
            QLLogging.log.exception("Progress bar does not exist, skipping update")
            return

        try:
            progress, message = emitted_signal
            if progress < 0:
                self._handle_analysis_error(message)
                return

            if getattr(self, "_analysis_failed", False):
                return

            value = self.progressBar.value()
            if value >= 100:
                return

            self.progressBar.setGreaterValue(progress)

            value = self.progressBar.value()
            if value >= 100 and progress >= 100:
                # 等待线程完成，但设置超时（例如5秒）
                if self.thread_run.wait(5000):  # 等待最多5秒
                    QLLogging.log.debug("Thread completed successfully")
                else:
                    QLLogging.log.warning("Thread did not complete within 5 seconds")

                # 将进度条隐藏，显示出文件
                self.label_progressBar.hide()
                self.progressBar.hide()
                self.label_draw.show()

                # 刷新 GUI
                QApplication.processEvents()

                # 确保从线程获取数据
                if hasattr(self.thread_run, 'df_score') and self.thread_run.df_score is not None:
                    self.df_score = self.thread_run.df_score
                    self.df_display_score = self._build_event_display_score()
                else:
                    QLLogging.log.warning("df_score is None or not available from thread")
                    return

                # 备份一下数据
                self.bank_df_score = self.df_score

                self.n_epochs = len(self.df_score)
                # 这里需要等待线程结束之后，获取到数据
                self.thread_run.wait()
                time.sleep(1)
                # 说明加载完成，发送自定义信号，将进度条页面隐藏，图形页面显示出来
                self.progressBar_completed.emit()


        except Exception as e:
            QLLogging.log.exception(f"Progress update error: {str(e)}")

    def _build_event_display_score(self): # 引用前一步的算法，将确认好的事件进行显示
        """根据算法确认的癫痫事件初始化顶部显示分期。"""
        if self.df_score is None: #数据非空
            return None

        display_df = self.df_score.copy(deep=True)
        if "Stage_Code" not in display_df.columns:
            return display_df

        display_df["Stage_Code"] = 0
        try:
            seizure_info, *_, = detect_seizures(
                self.df_score["Stage_Code"].values,
                self.thread_run.eeg_data,
                self.thread_run.sfreq,
                epoch_length=self.thread_run.epoch_length,
                start_time_ts=getattr(self.thread_run, "start_time_ts", None),
                min_no_seizure_epochs=3
            )
            epoch_length = float(getattr(self.thread_run, "epoch_length", 1.0) or 1.0)
            if len(display_df) > 0:
                for item in seizure_info or []:
                    start_ts = float(item.get("开始时间戳 (s)", 0))
                    end_ts = float(item.get("结束时间戳 (s)", start_ts))
                    start_idx = max(0, int(round(start_ts / epoch_length)))
                    end_idx = max(start_idx, int(round(end_ts / epoch_length)))
                    end_idx = min(len(display_df) - 1, end_idx)
                    display_df.loc[start_idx:end_idx, "Stage_Code"] = 1
        except Exception as e:
            QLLogging.log.exception(f"Build event display score failed: {e}")
            display_df = self.df_score.copy(deep=True)

        display_df["Stage"] = display_df["Stage_Code"].map(self.map_stages)
        return display_df

    def _get_display_score_df(self):
        if self.df_display_score is None and self.df_score is not None:
            self.df_display_score = self._build_event_display_score()
        return self.df_display_score

    def _get_export_score_df(self):
        display_df = self._get_display_score_df()
        return display_df if display_df is not None else self.df_score

    def fill_vline_per_hour(self, axes):
        try:
            next_start_hour, spans = self.get_start_end_time()
            print(f"next_start_hour：{next_start_hour}, spans:{spans}")

            across_days = 0
            for hour in spans:
                axes.axvline(x=hour, color='gray', linestyle='--', linewidth=10, alpha=0.7)

                formatted_next_start_hour = f"{next_start_hour:02d}:00"
                axes.text(hour + 10, -0.05, formatted_next_start_hour,
                          verticalalignment='top', horizontalalignment='left',
                          color='black', fontsize=60, fontweight='bold',
                          transform=axes.get_xaxis_transform())
                next_start_hour = next_start_hour + 1
                if next_start_hour >= 24:
                    next_start_hour = 0
                    across_days = across_days + 1
        except Exception as e:
            QLLogging.log.exception(f"fill_vline_per_hour error: {str(e)}")

    def get_start_end_time(self):
        # from datetime import datetime, timedelta
        import numpy as np
        time_span_total = len(self.thread_run.eeg_data) / self.raw_processed.info['sfreq']

        time_format = "%Y-%m-%d %H:%M:%S"
        start_time = self.raw_processed.info['meas_date'].replace(tzinfo=None)
        next_half_hour = (start_time + datetime.timedelta(minutes=30)).replace(
            minute=30 if start_time.minute < 30 else 0, second=0, microsecond=0)
        half_hour_span = next_half_hour - start_time

        spans = np.arange(half_hour_span.seconds, time_span_total, 1800)  # 1h span
        return next_half_hour.hour, spans

    def update_display_range(self):
        try:
            self.top_widget.nav_buttons_widget.label_of_page.setText(f" of {self.get_total_page()}")
            n_epochs_display = self.get_n_epochs_display()

            # 从滑块获取偏移（秒），更新起始 epoch
            pos_sec = self.widget_time_slider.time_slider.value()  # 滑块的偏移
            # 计算当前页总秒数和页面范围
            total_sec = n_epochs_display * self.thread_run.epoch_length
            x_min = pos_sec
            x_max = min(pos_sec + total_sec, self.get_total_time_number().total_seconds())

            # 统一给所有 PyQtGraph 视图加“护栏”
            plots = [self.plot_eeg, self.plot_emg, self.plot_acc, self.plot_widget]

            total = float(self.get_total_time_number().total_seconds())
            if self.top_widget.combobox_select_n_epochs.currentText() == "All":
                # 总是回到全段，不再沿用当前 viewRange
                x_min, x_max = 0.0, total
                min_zoom = float(getattr(self.thread_run, 'epoch_length', 5.0) or 5.0)

                for pw in plots:
                    vb = pw.getViewBox()
                    # 护栏照旧：允许继续缩放，但初始视图重置为全段
                    vb.setLimits(xMin=0.0, xMax=total, minXRange=min_zoom, maxXRange=total)
                    vb.setRange(xRange=(x_min, x_max), padding=0, update=True)

                # 同步 Matplotlib 的 hypnogram 轴
                for ax in self.figure.axes:
                    ax.set_xlim(x_min, x_max)
                self.canvas.draw_idle()
            else:
                # 只显示当前页：护栏就是当前可视窗口
                lim_min = float(x_min)
                lim_max = float(x_max)

                for pw in plots:
                    vb = pw.getViewBox()
                    # 先设限再设当前窗口，避免拖动后“跳出”
                    vb.setLimits(xMin=lim_min, xMax=lim_max, minXRange=None, maxXRange=None)
                    vb.setRange(xRange=(x_min, x_max), padding=0)
                width = float(x_max - x_min)

                # 内缩量：取窗口宽度的 1% 或 0.25s，取较大者
                pad = max(0.25, 0.01 * width)

                # 护栏仍然卡死在窗口
                vb.setLimits(xMin=float(x_min), xMax=float(x_max),
                             # 如果你想锁死页面宽度，就把下面两行放开
                             # minXRange=width, maxXRange=width
                             )

                # 可视范围收一点点，不会露出护栏外的数据
                vb.setRange(xRange=(x_min + pad, x_max - pad), padding=0)

            time_sec = np.arange(len(self.thread_run.eeg_data)) / self.thread_run.sfreq
            data_mapping = {
                self.plot_eeg: (time_sec, self.thread_run.eeg_data) if hasattr(self.thread_run, 'eeg_data') else None,
                self.plot_emg: (time_sec, self.thread_run.emg_data) if hasattr(self.thread_run, 'emg_data') else None,
                self.plot_acc: (time_sec, self.thread_run.acc_data) if hasattr(self.thread_run, 'acc_data') else None
            }

            # 更新显示范围
            for ax in self.figure.axes:
                current_xlim = ax.get_xlim()
                new_xlim = (x_min, x_max)
                if current_xlim != new_xlim:
                    ax.set_xlim(new_xlim)

            # 4 等分生成刻度位置（秒）和标签（时分秒）
            scale = 0.05  # 边界留白比例（5%）
            x_start = x_min + (x_max - x_min) * scale  # 从略大于x_min开始
            x_end = x_max - (x_max - x_min) * scale  # 到略小于x_max结束
            x_length = x_max - x_min
            epoch_display = x_length / self.thread_run.epoch_length
            if epoch_display in {3.0, 5.0}:
                sec_ticks = np.linspace(x_min, x_max, int(epoch_display + 1))
            elif epoch_display in {10.0, 20.0, 30.0, 50.0, 100.0}:
                sec_ticks = np.linspace(x_min, x_max, 11)
            else:
                sec_ticks = np.linspace(x_start, x_end, 4)  # 在缩小后的范围内生成4个刻度
            labels = []
            for s in sec_ticks:
                # 滑块偏移后真正的时间戳
                ts = self.start_datetime.toSecsSinceEpoch() + int(s)
                labels.append(QDateTime.fromSecsSinceEpoch(ts).toString("HH:mm:ss"))

            axis = self.plot_widget.getAxis('bottom')
            axis.setStyle(tickTextOffset=10)
            axis.setTicks(None)

            plots = [self.plot_acc, self.plot_emg, self.plot_eeg, self.plot_widget]
            for p in plots:
                p.setUpdatesEnabled(False)

            for plot in plots:
                # 只更新视图，不触发数据重绘
                plot.blockSignals(True)  # 避免触发信号循环
                # 直接设置视图范围
                plot.getViewBox().setRange(
                    xRange=(x_min, x_max),
                    update=True,
                    padding=0
                )

                full_data = data_mapping.get(plot)
                if full_data is not None:
                    x_full, y_full = full_data
                    mask = (x_full >= x_min) & (x_full <= x_max)
                    if mask.any():
                        x_visible = x_full[mask]
                        y_visible = y_full[mask]

                        # 更新曲线数据为可见部分
                        items = plot.getPlotItem().listDataItems()
                        if items:
                            items[0].setData(x_visible, y_visible)

                key = None
                if plot is self.plot_eeg:
                    key = 'eeg'
                elif plot is self.plot_emg:
                    key = 'emg'
                elif plot is self.plot_acc:
                    key = 'acc'

                if key is None:
                    # 其他图（如 hypnogram）保持原行为：自动
                    plot.enableAutoRange(axis=pg.ViewBox.YAxis)
                else:
                    if self._range_mode.get(key, 'Auto') == 'Auto':
                        plot.getPlotItem().getViewBox().enableAutoRange(axis=pg.ViewBox.YAxis)
                    else:
                        ymin, ymax = self._manual_ranges[key]
                        vb = plot.getViewBox()
                        vb.disableAutoRange(axis=pg.ViewBox.YAxis)
                        vb.setYRange(ymin, ymax, padding=0)
                        vb.updateViewRange()
                        plot.update()

            # 同时更新视图
            for plot in plots:
                plot.setUpdatesEnabled(True)
                plot.getViewBox().update()
                plot.blockSignals(False)

            self.canvas.draw_idle()

        except Exception as e:
            QLLogging.log.exception(f"Error updating display range: {str(e)}")

    def plot_results(self):
        from PyQt5.QtWidgets import QGraphicsItem
        """绘制分析结果"""
        self.label_draw.show()
        QLLogging.log.debug("Plot the results of the analysis")
        score_df = self._get_display_score_df() #绘制图像位置
        if score_df is None:
            QLLogging.log.info("No score data available")
            return

        try:
            self.event_handler.clear_highlight()  # 清除高亮
            self.figure.clear()
            self.current_selected_epoch = None
            self.current_selected_epochs = []

            # 更新总共的页数
            self.top_widget.nav_buttons_widget.button_goto_epoch.setText(str(self.getCurrentPage()))
            self.top_widget.nav_buttons_widget.label_of_page.setText(f" of {self.get_total_page()}")

            # 获取数据
            eeg_data = self.thread_run.eeg_data
            sfreq = self.thread_run.sfreq
            # 计算时间轴
            time_sec = np.arange(len(eeg_data)) / sfreq

            scores = score_df['Stage_Code'].values
            colors = [self.map_colors[score] for score in scores]

            # 计算时间点
            time_epochs_start = np.arange(len(scores)) * self.thread_run.epoch_length
            time_epochs_end = time_epochs_start + self.thread_run.epoch_length

            # 1. 分期结果图
            ax_hypnogram = self.figure.add_subplot(self.gs[0])
            ax_hypnogram.hlines(scores, time_epochs_start, time_epochs_end,
                                colors=colors, linewidths=40)
            # ax_hypnogram.set_yticks([0, 1])
            # ax_hypnogram.set_yticklabels(["Normal", "Seizure"])
            # ax_hypnogram.set_ylabel("Stage")
            ax_hypnogram.set_ylim(-0.5, 1.5)
            # ax_hypnogram.set_xticks([])  # 去掉x轴刻度
            # ax_hypnogram.set_xticklabels([])  # 去掉x轴刻度标签
            ax_hypnogram.margins(x=0, y=0)  # 消除子图内部边距

            # 在绘制图形时设置字体大小
            ax_hypnogram.tick_params(labelsize=40)  # 设置刻度标签字体大小
            ax_hypnogram.set_title(ax_hypnogram.get_title(), fontsize=40)  # 设置标题字体大小

            self.plot_eeg.clear()
            eeg_curve = pg.PlotCurveItem(
                x=time_sec,
                y=eeg_data,
                pen=pg.mkPen(color='k', width=1.0)
            )
            self.plot_eeg.addItem(eeg_curve)

            self.plot_eeg.setLabel('left', "EEG Amplitude", units="uV")

            # 隐藏 X 轴刻度（与 Matplotlib 保持一致）
            #self.plot_eeg.hideAxis('bottom')

            x_min = time_sec[0]
            x_max = time_sec[-1]
            self.plot_eeg.setXRange(x_min, x_max, padding=0)

            # 启用抗锯齿（提升视觉效果）
            # pg.setConfigOptions(antialias=True)

            scale = 0.05  # 边界留白比例（5%）
            x_start = x_min + (x_max - x_min) * scale  # 从略大于x_min开始
            x_end = x_max - (x_max - x_min) * scale  # 到略小于x_max结束
            x_ticks = np.linspace(x_start, x_end, 4)  # 在缩小后的范围内生成4个刻度
            # 读取用户指定的开始日期和时间
            date_start = self.bottom_left_widget.combobox_start.currentText()
            time_start = self.bottom_left_widget.lineedit_start.time().toString("HH:mm:ss")
            dt_start = QDateTime.fromString(f"{date_start} {time_start}", "yyyy-MM-dd HH:mm:ss")
            self.start_datetime = dt_start
            # 设置自定义坐标轴和悬浮标签的基准时间
            if hasattr(self, 'spectrogram_time_axis_eeg'):
                self.spectrogram_time_axis_eeg.set_meas_date(dt_start.toPyDateTime())

            # EMG包络线图
            if hasattr(self.thread_run, 'emg_data'):
                self.plot_emg.clear()

                while self.thread_run.emg_envelope is None:
                    time.sleep(0.1)  # 休眠100毫秒
                    QApplication.processEvents()  # 保持UI响应
                print("time_sec,self.thread_run.emg_envelope", len(time_sec), len(self.thread_run.emg_envelope))
                # 创建曲线（绿色，线宽 1.0）
                emg_curve = pg.PlotCurveItem(
                    x=time_sec,
                    y=self.thread_run.emg_envelope,
                    pen=pg.mkPen(color='g', width=1.0)
                )
                self.plot_emg.addItem(emg_curve)

                # 设置 Y 轴标签
                self.plot_emg.setLabel('left', 'EMG Envelope', units='uV')
                #self.plot_emg.hideAxis('bottom')

                x_min = time_sec[0]
                x_max = time_sec[-1]
                self.plot_emg.setXRange(x_min, x_max, padding=0)

                scale = 0.05  # 边界留白比例（5%）
                x_start = x_min + (x_max - x_min) * scale  # 从略大于x_min开始
                x_end = x_max - (x_max - x_min) * scale  # 到略小于x_max结束
                x_ticks = np.linspace(x_start, x_end, 4)  # 在缩小后的范围内生成4个刻度
                # 读取用户指定的开始日期和时间
                date_start = self.bottom_left_widget.combobox_start.currentText()
                time_start = self.bottom_left_widget.lineedit_start.time().toString("HH:mm:ss")
                dt_start = QDateTime.fromString(f"{date_start} {time_start}", "yyyy-MM-dd HH:mm:ss")
                self.start_datetime = dt_start
                # 设置自定义坐标轴和悬浮标签的基准时间
                if hasattr(self, 'spectrogram_time_axis_emg'):
                    self.spectrogram_time_axis_emg.set_meas_date(dt_start.toPyDateTime())

            # ACC信号图
            if hasattr(self.thread_run, 'acc_data'):
                acc_data = self.thread_run.acc_data
                self.plot_acc.clear()

                # 创建 PlotCurveItem
                acc_curve = pg.PlotCurveItem(
                    x=time_sec,
                    y=acc_data,
                    pen=pg.mkPen(color='b', width=1.0)  # 蓝色线条，线宽 1.0
                )
                self.plot_acc.addItem(acc_curve)

                # 设置 Y 轴标签
                self.plot_acc.setLabel('left', 'ACC Amplitude', units='mG')

                # 隐藏 X 轴标签（使用正确的 PyQtGraph 方法）
                x_axis = self.plot_acc.getAxis('bottom')
                x_axis.setTicks([[]])  # 清除刻度标签

                # 隐藏 X 轴刻度（与 Matplotlib 保持一致）
                #self.plot_acc.hideAxis('bottom')

                x_min = time_sec[0]
                x_max = time_sec[-1]
                self.plot_acc.setXRange(x_min, x_max, padding=0)

                scale = 0.05  # 边界留白比例（5%）
                x_start = x_min + (x_max - x_min) * scale  # 从略大于x_min开始
                x_end = x_max - (x_max - x_min) * scale  # 到略小于x_max结束
                x_ticks = np.linspace(x_start, x_end, 4)  # 在缩小后的范围内生成4个刻度
                # 读取用户指定的开始日期和时间
                date_start = self.bottom_left_widget.combobox_start.currentText()
                time_start = self.bottom_left_widget.lineedit_start.time().toString("HH:mm:ss")
                dt_start = QDateTime.fromString(f"{date_start} {time_start}", "yyyy-MM-dd HH:mm:ss")
                self.start_datetime = dt_start
                print("-------------", dt_start)
                print("-------------", dt_start.toPyDateTime())
                # 设置自定义坐标轴和悬浮标签的基准时间
                if hasattr(self, 'spectrogram_time_axis_acc'):
                    self.spectrogram_time_axis_acc.set_meas_date(dt_start.toPyDateTime())
                axis = self.plot_acc.getAxis('bottom')
                axis.setTicks(None)  # 恢复自动刻度计算
                axis.setStyle(tickTextOffset=12)

            if hasattr(self.thread_run, 'spectrogram_data'):
                spec_data = self.thread_run.spectrogram_data
                if spec_data is not None and isinstance(spec_data, dict):
                    try:
                        # 获取数据
                        power = spec_data['power']
                        times = spec_data['times']
                        freqs = spec_data['frequencies']

                        # 清除之前的绘图
                        self.plot_widget.clear()

                        # 创建图像项
                        img_item = pg.ImageItem()

                        # 设置图像数据（注意数据方向）
                        img_data = power.T  # 转置使时间在x轴，频率在y轴
                        img_item.setImage(img_data)

                        # 设置坐标变换
                        x_min, x_max = times[0], times[-1]
                        y_min, y_max = freqs[0], freqs[-1]

                        # 计算缩放和平移
                        tr = pg.QtGui.QTransform()
                        tr.translate(x_min, y_min)
                        tr.scale(
                            (x_max - x_min) / img_data.shape[0],
                            (y_max - y_min) / img_data.shape[1]
                        )
                        img_item.setTransform(tr)

                        # 添加图像到绘图区域
                        self.plot_widget.addItem(img_item)

                        # 设置颜色映射
                        colormap = pg.colormap.get('CET-R4')  # 接近 RdBu_r 的反转色
                        img_item.setColorMap(colormap)

                        # 设置色阶
                        vmin = spec_data.get('vmin', img_data.min())
                        vmax = spec_data.get('vmax', img_data.max())
                        img_item.setLevels([vmin, vmax])
                        # # 添加colorbar
                        # self.add_colorbar_to_plot(self.plot_widget, img_item, vmin, vmax)
                        # 设置坐标轴
                        self.plot_widget.setLabel('left', 'EEG Frequency', units='Hz')
                        # self.plot_widget.setLabel('bottom', 'Time', units='s')
                        self.plot_widget.setYRange(y_min, y_max, padding=0)
                        self.plot_widget.setXRange(x_min, x_max, padding=0)

                        scale = 0.05  # 边界留白比例（5%）
                        x_start = x_min + (x_max - x_min) * scale  # 从略大于x_min开始
                        x_end = x_max - (x_max - x_min) * scale  # 到略小于x_max结束
                        x_ticks = np.linspace(x_start, x_end, 4)  # 在缩小后的范围内生成4个刻度
                        # 读取用户指定的开始日期和时间
                        date_start = self.bottom_left_widget.combobox_start.currentText()
                        time_start = self.bottom_left_widget.lineedit_start.time().toString("HH:mm:ss")
                        dt_start = QDateTime.fromString(f"{date_start} {time_start}", "yyyy-MM-dd HH:mm:ss")
                        self.start_datetime = dt_start
                        # 设置自定义坐标轴和悬浮标签的基准时间
                        if hasattr(self, 'spectrogram_time_axis'):
                            self.spectrogram_time_axis.set_meas_date(dt_start.toPyDateTime())
                        if hasattr(self, 'widget_left_label'):
                            self.widget_left_label.set_meas_date(dt_start.toPyDateTime())
                        # ts_start = dt_start.toSecsSinceEpoch()
                        #
                        # date_end = self.bottom_left_widget.combobox_end.currentText()
                        # time_end = self.bottom_left_widget.lineedit_end.time().toString("HH:mm:ss")
                        # dt_end = QDateTime.fromString(f"{date_end} {time_end}", "yyyy-MM-dd HH:mm:ss")
                        # ts_end = dt_end.toSecsSinceEpoch()
                        #
                        # total_sec = ts_end - ts_start
                        # # sec_ticks = np.linspace(0, total_sec, 4)
                        # scale = 0.05  # 边界留白比例（5%）
                        # x_start = 0 + (total_sec - 0) * scale  # 从略大于x_min开始
                        # x_end = total_sec - (total_sec - 0) * scale  # 到略小于x_max结束
                        # sec_ticks = np.linspace(x_start, x_end, 4)  # 在缩小后的范围内生成4个刻度
                        # # 生成 “HH:mm:ss” 标签
                        # labels = [QDateTime.fromSecsSinceEpoch(ts_start + int(s)).toString("HH:mm:ss")
                        #           for s in sec_ticks]
                        #
                        # # 应用到谱图底轴
                        # axis = self.plot_widget.getAxis('bottom')
                        # axis.setTicks([list(zip(x_ticks, labels))])
                        axis = self.plot_widget.getAxis('bottom')
                        axis.setTicks(None)  # 恢复自动刻度计算
                        axis.setHeight(47)  # 关键：给底轴一个稳定高度
                        axis.setStyle(tickTextOffset=12)  # 可以比 10 稍大点，避免压线

                        # 反转Y轴使低频在下（模仿Matplotlib的origin='lower'）
                        self.plot_widget.invertY(False)  # False表示不反转（低频在底部）

                    except Exception as e:
                        QLLogging.log.exception(f"Error plotting spectrogram: {str(e)}")

            self.epilepsy_score_wh.finish_backup()
            self.epilepsy_redo_score_wh.finish_backup()
            self.update_display_n_epochs()  # 更新显示的epoch数量

            for pw in [self.plot_eeg, self.plot_emg, self.plot_acc, self.plot_widget]:
                pi = pw.getPlotItem()
                for it in pi.listDataItems():
                    it.setCacheMode(QGraphicsItem.NoCache)
                for it in pi.items:
                    if isinstance(it, pg.ImageItem):
                        it.setCacheMode(QGraphicsItem.NoCache)

        except Exception as e:
            QLLogging.log.exception(f"Error in plot_results: {str(e)}")
            import traceback
            traceback.print_exc()
        self.label_draw.hide()
        self.canvas.draw_idle()

    def add_colorbar_to_plot(self, plot_widget, img_item, vmin, vmax):
        """为plot_widget添加colorbar"""
        try:
            # 删除现有的colorbar
            for item in plot_widget.getPlotItem().items:
                if hasattr(item, 'is_colorbar') and item.is_colorbar:
                    plot_widget.removeItem(item)

            # 创建颜色条
            cmap = pg.colormap.get('CET-R4')

            # 使用ColorBarItem (PyQtGraph 0.12.0+)
            if hasattr(pg, 'ColorBarItem'):
                bar = pg.ColorBarItem(
                    values=(vmin, vmax),
                    colorMap=cmap,
                    label='Power (dB)',
                    orientation='right'
                )
                # 将colorbar与图像项关联
                bar.setImageItem(img_item)

                # 添加到绘图区域
                plot_widget.getPlotItem().layout.addItem(bar, 2, 3)

                # 标记为colorbar便于识别
                bar.is_colorbar = True

                return bar
            else:
                # 如果没有ColorBarItem，则使用简化版本
                QLLogging.log.warning("ColorBarItem not available in this version of PyQtGraph")
                return None

        except Exception as e:
            QLLogging.log.exception(f"Error in add_colorbar_to_plot: {str(e)}")
            return None

    def get_n_epochs_display(self):
        text = self.top_widget.combobox_select_n_epochs.currentText()
        if text == "All":
            self.widget_time_slider.hide()
            return self.n_epochs
        self.widget_time_slider.show()
        return int(text)


    def user_edit_stage(self, action_str):
        """处理用户编辑的癫痫阶段"""

        # 如果是由点击事件触发的更改，则忽略
        if self._ignore_combobox_change:
            return

        if self.current_selected_epochs is not None:
            score_df = self._get_display_score_df() #保存用户修改的地方
            if score_df is None:
                QLLogging.log.info("No display score data available")
                return
            # 获取当前视图范围
            view_range_eeg = self.plot_eeg.getViewBox().viewRange()
            x_range = view_range_eeg[0]

            # new_stage = self.combobox_stage.currentText()
            new_stage = action_str
            stage_code = 1 if new_stage == "Seizure" else 0
            for selected_epoch in self.current_selected_epochs:
                self.epilepsy_score_wh.record(selected_epoch, score_df.at[selected_epoch, 'Stage_Code'])
                score_df.at[selected_epoch, 'Stage_Code'] = stage_code
                score_df.at[selected_epoch, 'Stage'] = new_stage

            """绘制分析结果"""
            QLLogging.log.debug("Plot the results of the analysis")
            if score_df is None:
                QLLogging.log.info("No score data available")
                return

            try:
                self.figure.clear()
                self.current_selected_epoch = None
                self.current_selected_epochs = []

                # 更新总共的页数
                self.top_widget.nav_buttons_widget.label_of_page.setText(f" of {self.get_total_page()}")

                QLLogging.log.debug(f"更新的总页数：{self.get_total_page()}")

                # 获取数据
                eeg_data = self.thread_run.eeg_data
                sfreq = self.thread_run.sfreq

                QLLogging.log.debug(f"plot_results——eeg_data:{eeg_data}")
                QLLogging.log.debug(f"plot_results——sfreq:{sfreq}")

                # 计算时间轴
                time_sec = np.arange(len(eeg_data)) / sfreq
                QLLogging.log.debug(f"plot_results——time_sec:{time_sec}")

                scores = score_df['Stage_Code'].values
                colors = [self.map_colors[score] for score in scores]

                # 计算时间点
                time_epochs_start = np.arange(len(scores)) * self.thread_run.epoch_length
                time_epochs_end = time_epochs_start + self.thread_run.epoch_length

                QLLogging.log.debug(f"plot_results——time_epochs_start:{time_epochs_start}")
                QLLogging.log.debug(f"plot_results——time_epochs_end:{time_epochs_end}")
                QLLogging.log.debug(f"plot_results——np.arange(len(scores)):{np.arange(len(scores))}")

                # 1. 分期结果图
                ax_hypnogram = self.figure.add_subplot(self.gs[0])
                ax_hypnogram.hlines(scores, time_epochs_start, time_epochs_end,
                                    colors=colors, linewidths=40)

                ax_hypnogram.set_yticks([0, 1])
                ax_hypnogram.set_yticklabels(["Normal", "Seizure"])
                ax_hypnogram.set_ylabel("Stage")
                ax_hypnogram.set_ylim(-0.5, 1.5)
                # ax_hypnogram.set_xticks([])  # 去掉x轴刻度
                # ax_hypnogram.set_xticklabels([])  # 去掉x轴刻度标签
                ax_hypnogram.margins(x=0, y=0)  # 消除子图内部边距

                # 在绘制图形时设置字体大小
                ax_hypnogram.tick_params(labelsize=40)  # 设置刻度标签字体大小
                ax_hypnogram.set_ylabel(ax_hypnogram.get_ylabel(), fontsize=40)  # 设置y轴标签字体大小
                ax_hypnogram.set_title(ax_hypnogram.get_title(), fontsize=40)  # 设置标题字体大小

                # 设置轴标签的字体大小
                # for label in ax_hypnogram.get_xticklabels():
                #     label.set_fontsize(60)
                for label in ax_hypnogram.get_yticklabels():
                    label.set_fontsize(40)

                self.epilepsy_score_wh.finish_backup()
                self.epilepsy_redo_score_wh.finish_backup()

                self.event_handler.clear_highlight()

                self.update_display_range()

                # 恢复
                vb_eeg = self.plot_eeg.getViewBox()
                vb_eeg.disableAutoRange(axis=pg.ViewBox.XAxis)  # 禁用X轴自动适配
                vb_eeg.setXRange(x_range[0], x_range[1], padding=0)


            except Exception as e:
                QLLogging.log.exception(f"Error in plot_results: {str(e)}")
                import traceback
                traceback.print_exc()

            self.edit_post_process()

    def update_display_previous_more(self):
        """显示前一页结果"""
        current_page = self.getCurrentPage()

        # 计算前一页的页码
        target_page = max(1, current_page - 1)

        # 根据目标页码计算滑块位置（百分比）
        ts_min = self.widget_time_slider.time_slider.minimum()
        ts_max = self.widget_time_slider.time_slider.maximum()
        total_pages = self.get_total_page()

        # 计算目标页面在滑块中的位置（百分比）
        if total_pages > 1:
            page_percentage = (target_page - 1) / (total_pages - 1)  # 0到1之间
            target_slider_value = ts_min + page_percentage * (ts_max - ts_min)
        else:
            target_slider_value = ts_min

        # 更新滑块位置
        self.widget_time_slider.time_slider.setValue(math.ceil(target_slider_value))

        QLLogging.log.debug(f"Previous page: {target_page}, slider_value: {target_slider_value}")

        # 更新按钮显示
        self.top_widget.nav_buttons_widget.button_goto_epoch.setText(str(target_page + 1))

        # 更新显示范围
        self.update_display_range()

    def update_display_next_more(self):
        """显示下一页结果"""
        current_page = self.getCurrentPage()
        total_pages = self.get_total_page()

        # 计算下一页的页码
        target_page = min(total_pages, current_page + 1)

        # 根据目标页码计算滑块位置（百分比）
        ts_min = self.widget_time_slider.time_slider.minimum()
        ts_max = self.widget_time_slider.time_slider.maximum()

        # 计算目标页面在滑块中的位置（百分比）
        if total_pages > 1:
            page_percentage = (target_page - 1) / (total_pages - 1)  # 0到1之间
            target_slider_value = ts_min + page_percentage * (ts_max - ts_min)
        else:
            target_slider_value = ts_min

        # 更新滑块位置
        self.widget_time_slider.time_slider.setValue(math.ceil(target_slider_value))

        QLLogging.log.debug(f"Next page: {target_page}, slider_value: {target_slider_value}")

        # 更新按钮显示
        self.top_widget.nav_buttons_widget.button_goto_epoch.setText(str(target_page))

        # 更新显示范围
        self.update_display_range()

    def update_display_goto_epoch(self):
        """跳转到特定页面"""
        try:
            min_value = 1
            max_value = self.get_total_page()
            target_page, done = QInputDialog.getInt(
                self, 'Input Dialog', 'Enter the Page You Want to View:',
                min=min_value, max=max_value, value=self.getCurrentPage()
            )

            if done:
                # 根据目标页码计算滑块位置（百分比）
                ts_min = self.widget_time_slider.time_slider.minimum()
                ts_max = self.widget_time_slider.time_slider.maximum()
                total_pages = self.get_total_page()

                # 计算目标页面在滑块中的位置（百分比）
                if total_pages > 1:
                    page_percentage = (target_page - 1) / (total_pages - 1)  # 0到1之间
                    target_slider_value = ts_min + page_percentage * (ts_max - ts_min)
                else:
                    target_slider_value = ts_min

                # 更新滑块位置
                self.widget_time_slider.time_slider.setValue(math.ceil(target_slider_value))

                QLLogging.log.debug(f"Goto page: {target_page}, slider_value: {target_slider_value}")

                # 更新按钮显示
                self.top_widget.nav_buttons_widget.button_goto_epoch.setText(str(target_page))

                # 更新显示范围
                self.update_display_range()

        except Exception as e:
            QLLogging.log.exception(f"Error in update_display_goto_epoch: {str(e)}")

    def update_display_first(self):
        """显示第一页的结果"""
        ts_min = self.widget_time_slider.time_slider.minimum()

        # 第一页对应滑块的最小值
        self.widget_time_slider.time_slider.setValue(ts_min)

        # 更新按钮显示
        self.top_widget.nav_buttons_widget.button_goto_epoch.setText("1")

        # 更新显示范围
        self.update_display_range()

    def update_display_last(self):
        """显示最后一页的内容"""
        ts_max = self.widget_time_slider.time_slider.maximum()
        total_pages = self.get_total_page()

        # 最后一页对应滑块的最大值
        self.widget_time_slider.time_slider.setValue(ts_max)

        # 更新按钮显示
        self.top_widget.nav_buttons_widget.button_goto_epoch.setText(str(total_pages))

        # 更新显示范围
        self.update_display_range()

    def update_display_n_epochs(self):
        """更新显示的epoch数量"""
        try:
            n_epochs_display = self.get_n_epochs_display()

            # 设置滑块的最大值
            max_slider_value = max(0, (int(self.get_total_time_number().total_seconds()) -
                                       int(self.thread_run.epoch_length * n_epochs_display)))
            self.widget_time_slider.time_slider.setMaximum(max_slider_value)

            # 获取到总时间
            timediff = self.get_total_time_number()
            QLLogging.log.debug(
                timediff.total_seconds() / self.thread_run.epoch_length * self.widget_time_slider.time_slider.value() / 100)

            if self.top_widget.combobox_select_n_epochs.currentText() == "All":
                self.pushButton_save_pic.setEnabled(True)
                self.widget_time_slider.hide()
                self.widget_time_slider.time_slider.setValue(0)
                self.top_widget.nav_buttons_widget.button_goto_epoch.setText("1")
                self.create_all_epochs_warning()
            else:
                self.widget_time_slider.show()
                self.close_all_epochs_warning()

                # 尝试获取最后修改的epoch位置
                last_modified_epoch = self.get_last_modified_epoch()

                if last_modified_epoch is not None:
                    # 将epoch位置转换为时间位置（秒）
                    target_time_sec = last_modified_epoch * self.thread_run.epoch_length

                    # 确保在有效范围内
                    if target_time_sec <= max_slider_value:
                        # 设置滑块位置到最后修改的epoch
                        self.widget_time_slider.time_slider.setValue(int(target_time_sec))
                        QLLogging.log.debug(
                            f"Jumped to last modified epoch: {last_modified_epoch}, time: {target_time_sec}s")
                    else:
                        # 如果超出范围，设置到最大值
                        self.widget_time_slider.time_slider.setValue(max_slider_value)
                        QLLogging.log.debug(f"Last modified epoch out of range, set to max: {max_slider_value}s")
                else:
                    # 没有修改记录，确保当前滑块值在有效范围内
                    current_slider_value = self.widget_time_slider.time_slider.value()
                    if current_slider_value > max_slider_value:
                        self.widget_time_slider.time_slider.setValue(max_slider_value)

                # 根据滑块值计算当前页
                current_page = self.getCurrentPage()
                self.top_widget.nav_buttons_widget.button_goto_epoch.setText(str(current_page))

                QLLogging.log.debug(f"Current slider value: {self.widget_time_slider.time_slider.value()}")

            # 更新滑块的总页数
            self.widget_time_slider.time_slider.setTotalPages(self.get_total_page())

            # 更新显示范围
            self.update_display_range()

            OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'update display n epochs', 0)

        except Exception as e:
            QLLogging.log.exception(f"Error in update_display_n_epochs: {str(e)}")

    def get_last_modified_epoch(self):
        """获取最近一次状态修改的epoch位置"""
        try:
            # 从历史记录中获取最近的修改
            if not self.epilepsy_score_wh.is_empty():
                # 获取最近的修改记录
                last_backup = self.epilepsy_score_wh.get_last_backup()
                if last_backup:
                    # 返回最近修改的epoch中最小的那个（最开始的位置）
                    return min(last_backup.keys())

            return None

        except Exception as e:
            QLLogging.log.exception(f"Error getting last modified epoch: {str(e)}")
            return None

    def update_epoch_length(self):
        try:
            self.bottom_left_widget.information_label.show()
            OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'update epoch length', 0)

        except Exception as e:
            QLLogging.log.exception(f"update_epoch_length error: {str(e)}")

    def on_slider_changed(self):
        """处理滑块值变化"""
        try:
            # 根据滑块位置计算当前页码
            current_page = self.getCurrentPage()

            # 更新按钮显示为当前页码
            self.top_widget.nav_buttons_widget.button_goto_epoch.setText(str(current_page))

            # 更新显示范围
            self.update_display_range()

        except Exception as e:
            QLLogging.log.exception(f"on_slider_changed error: {str(e)}")

    def update_signal_range(self, sender=None, value=None):
        """更新所有信号图的幅度范围"""
        try:
            # 确定是哪个下拉菜单触发了更新
            if sender == "eeg" or sender is None:
                # 更新EEG信号范围
                if value == "Auto":
                    self._range_mode['eeg'] = 'Auto'
                    self.plot_eeg.enableAutoRange(axis=pg.ViewBox.YAxis)
                else:
                    amplitude = int(value.replace('±', ''))
                    self._range_mode['eeg'] = 'Manual'
                    self._manual_ranges['eeg'] = (-amplitude, amplitude)
                    vb = self.plot_eeg.getViewBox()
                    vb.disableAutoRange(axis=pg.ViewBox.YAxis)  # 关键步骤
                    # 设置新范围并立即更新
                    vb.setYRange(-amplitude, amplitude, padding=0)
                    # 强制立即刷新视图
                    vb.updateViewRange()
                    # 确保视图更新
                    self.plot_eeg.update()

            if sender == "emg" or sender is None:
                # 更新EMG包络线范围 - 只显示正值
                if value == "Auto":
                    self._range_mode['emg'] = 'Auto'
                    self.plot_emg.enableAutoRange(axis=pg.ViewBox.YAxis)
                else:
                    amplitude = int(value.replace('±', ''))
                    self._range_mode['emg'] = 'Manual'
                    self._manual_ranges['emg'] = (0, amplitude)
                    vb = self.plot_emg.getViewBox()
                    vb.disableAutoRange(axis=pg.ViewBox.YAxis)  # 关键步骤
                    # 设置新范围并立即更新
                    vb.setYRange(0, amplitude, padding=0)
                    # 强制立即刷新视图
                    vb.updateViewRange()
                    # 确保视图更新
                    self.plot_emg.update()

            if sender == "acc" or sender is None:
                # 更新ACC信号范围
                if value == "Auto":
                    self._range_mode['acc'] = 'Auto'
                    self.plot_acc.enableAutoRange(axis=pg.ViewBox.YAxis)
                else:
                    amplitude = int(value.replace('±', ''))
                    self._range_mode['acc'] = 'Manual'
                    self._manual_ranges['acc'] = (-amplitude, amplitude)
                    vb = self.plot_acc.getViewBox()
                    vb.disableAutoRange(axis=pg.ViewBox.YAxis)  # 关键步骤
                    # 设置新范围并立即更新
                    vb.setYRange(-amplitude, amplitude, padding=0)
                    # 强制立即刷新视图
                    vb.updateViewRange()
                    # 确保视图更新
                    self.plot_acc.update()

        except Exception as e:
            QLLogging.log.exception(f"Error updating signal ranges: {str(e)}")

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
            self.progressBar.resetValue()
            # 中止分析时，禁用跳转输入框
            if hasattr(self, 'lineedit_goto_epoch'):
                self.lineedit_goto_epoch.setEnabled(False)

            # Clear any previous results
            self.df_score = None
            self.df_display_score = None
            self.n_epochs = 0

        except Exception as e:
            QLLogging.log.exception(f"Error aborting analysis: {str(e)}")

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        try:
            self.close_all_epochs_warning()
            # 检查是否有分析正在运行
            if self.thread_run and self.thread_run.isRunning():
                # 断开信号连接，防止更新已删除的UI组件
                self.thread_run.signal.disconnect()
                # 终止线程
                self.thread_run.terminate()

                # 等待线程完全终止
                if not self.thread_run.wait(3000):  # 等待最多3秒
                    self.thread_run.terminate()  # 强制终止

            # 清理线程相关资源
            if hasattr(self, 'thread_run'):
                if self.thread_run.isRunning():
                    self.thread_run.quit()
                    self.thread_run.wait()
                del self.thread_run

            # 清理资源
            if hasattr(self, 'figure'):
                self.figure.clear()
                plt.close(self.figure)
                del self.figure

            if hasattr(self, 'canvas'):
                self.canvas.close()
                del self.canvas

            data_attributes = [
                'raw_processed',
                'df_score',
                'eeg_data',
                'emg_data',
                'acc_data',
                'spectrogram_data',
                'scores',
                'stages',
                'epochlabels',
                'current_selected_epoch',
                'n_epochs',
                'epoch_start',
                'edf_path'
            ]

            for attr in data_attributes:
                if hasattr(self, attr):
                    delattr(self, attr)

            self.event_handler.disconnect_events()

            # 7. 强制多次垃圾回收
            import gc
            gc.collect()
            gc.collect()

            # 8. 打印内存使用情况（用于调试）
            import psutil
            process = psutil.Process()
            QLLogging.log.debug(f"Memory usage after cleanup: {process.memory_info().rss / 1024 / 1024:.2f} MB")

            # 接受关闭事件
            event.accept()

        except Exception as e:
            QLLogging.log.exception(f"Error during window closure: {str(e)}")
            # 即使出错也要确保窗口关闭
            event.accept()

    def get_start_end_time_bottom_left_widget(self):
        try:
            start_time = self.raw_processed.info['meas_date'].replace(tzinfo=None)
            # end_time = start_time + datetime.timedelta(seconds=self.raw_processed.n_times / self.raw_processed.info['sfreq'])
            total_duration = int(self.raw_processed.times[-1])  # 转换为整数秒   数据总时长（秒）
            end_time = start_time + datetime.timedelta(seconds=total_duration)  # 终止时间
            start = start_time.strftime('%Y-%m-%d %H:%M:%S')
            end = end_time.strftime('%Y-%m-%d %H:%M:%S')
            # 使用 split() 方法按空格分割
            start_parts = start.split()
            end_parts = end.split()
            start_data_part = start_parts[0]
            start_time_part = start_parts[1]
            end_data_part = end_parts[0]
            end_time_part = end_parts[1]
        except Exception as e:
            QLLogging.log.exception(f"get_start_end_time_bottom_left_widget error: {str(e)}")

        return start_data_part, start_time_part, end_data_part, end_time_part

    def set_bottom_left_widget_start_end_time_text(self):
        # 界面左下角开始结束时间
        # from datetime import datetime, timedelta
        _translate = QCoreApplication.translate
        start_data_part, start_time_part, end_data_part, end_time_part = self.get_start_end_time_bottom_left_widget()
        start_time = QTime.fromString(start_time_part, "HH:mm:ss")
        end_time = QTime.fromString(end_time_part, "HH:mm:ss")
        self.bottom_left_widget.lineedit_start.setTime(start_time)
        self.bottom_left_widget.lineedit_end.setTime(end_time)
        if start_data_part == end_data_part:
            # 只有一个选项
            self.bottom_left_widget.combobox_start.addItem(f"{start_data_part}")
            self.bottom_left_widget.combobox_end.addItem(f"{start_data_part}")
            # 设置默认选项
            self.bottom_left_widget.combobox_start.setCurrentText(f"{start_data_part}")
            self.bottom_left_widget.combobox_end.setCurrentText(f"{end_data_part}")
        else:
            # 有两个选项
            self.bottom_left_widget.combobox_start.addItem(f"{start_data_part}")
            self.bottom_left_widget.combobox_start.addItem(f"{end_data_part}")
            self.bottom_left_widget.combobox_end.addItem(f"{start_data_part}")
            self.bottom_left_widget.combobox_end.addItem(f"{end_data_part}")
            # 设置默认选项
            self.bottom_left_widget.combobox_start.setCurrentText(f"{start_data_part}")
            self.bottom_left_widget.combobox_end.setCurrentText(f"{end_data_part}")

        # 添加行高
        # 创建 QListView 并设置行高
        view_start = QListView()
        view_start.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.bottom_left_widget.combobox_start.setView(view_start)  # 绑定视图到 QComboBox
        # 添加行高
        # 创建 QListView 并设置行高
        view_end = QListView()
        view_end.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.bottom_left_widget.combobox_end.setView(view_end)  # 绑定视图到 QComboBox

    def set_label_time_slider_diff(self):
        # from datetime import datetime
        start_data_part, start_time_part, end_data_part, end_time_part = self.get_start_end_time_bottom_left_widget()

        start_time = start_data_part + " " + start_time_part
        end_time = end_data_part + " " + end_time_part

        # 将字符串转换为datetime对象
        date_time_obj1 = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        date_time_obj2 = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        # 再将这个相对时间填充到label中，最后要进行更新开始时间

        # 计算时间差值
        time_diff = date_time_obj2 - date_time_obj1
        # 将这个差值转换为 时分秒 的形式
        hours = time_diff.seconds // 3600
        minutes = (time_diff.seconds % 3600) // 60
        seconds = time_diff.seconds % 60

        # 格式化输出，不足两位时前面补零
        formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        self.widget_time_slider.label_start_time.setText("00:00:00")
        self.widget_time_slider.label_end_time.setText(formatted_time)  # 如果不满足两位数，需要添加0

    def analysis_clicked(self):
        # 先进行刷新数据
        if self.crop_data() is None:  # 若裁剪失败，终止流程
            return
        start_time = time.time()
        self.set_pushButton_false()

        self.label_draw.hide()
        self.progressBar.show()
        self.label_progressBar.show()

        # 刷新 GUI
        QApplication.processEvents()

        # 先将进度条设置为0
        self.widget_time_slider.time_slider.setValue(0)
        # 然后将time_sdlider中的label中的时间更新
        self.set_label_time_slider_diff()
        self.run_analysis()

        end_time = time.time()
        print(f"analysis_clicked time: {end_time - start_time}-----------------------------")

        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'epilepsyanalysis analysis', 0)

    def progressBar_change_canvas_widget(self):
        """进度条完成后,开始绘图"""
        # 隐藏progressBar页面，显示canvas页面
        self.icon_with_text_widget.hide()
        self.progressBar_widget.hide()
        self.bottom_right_top_widget.show()
        self.scrollarea_canvas.show()
        self.widget_time_slider.show()

        # 将按钮解开禁用
        self.pushButton_save_pic.setEnabled(True)
        self.pushButton_save_data.setEnabled(True)
        self.pushButton_analyse.setEnabled(True)
        self.pushButton_load_history.setEnabled(True)
        # 分析完成后，启用跳转输入框
        if hasattr(self, 'lineedit_goto_epoch'):
            self.lineedit_goto_epoch.setEnabled(True)
            self.slider_goto_epoch.setRange(1, self.n_epochs)
            # 滑块值变化时同步到输入框
            self.slider_goto_epoch.valueChanged.connect(self._on_slider_value_changed)
            # 输入框内容变化时同步到滑块（仅有效数字）
            self.lineedit_goto_epoch.textChanged.connect(self._on_input_text_changed)

        self.plot_results()
        # self.canvas.draw_idle()

    def seizure_normal_button_click(self, index):
        # 判断是哪一个按钮触发了点击事件
        if index == 1:
            self.user_edit_stage("Normal")
            OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'Normal pushButton clicked', 0)
        elif index == 2:
            self.user_edit_stage("Seizure")
            OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'Seizure pushButton clicked', 0)

    def prepare_score_when_undo(self):
        score_df = self._get_display_score_df()
        if score_df is None:
            return
        restore_data = self.epilepsy_score_wh.get_restore_data()
        if len(restore_data) == 0:
            return
        for key, value in restore_data.items():
            self.epilepsy_redo_score_wh.record(key, score_df.at[key, 'Stage_Code'])
            score_df.at[key, 'Stage_Code'] = value
            score_df.at[key, 'Stage'] = self.map_stages[value]

    def prepare_score_when_redo(self):
        score_df = self._get_display_score_df()
        if score_df is None:
            return
        restore_data = self.epilepsy_redo_score_wh.get_restore_data()
        if len(restore_data) == 0:
            return
        for key, value in restore_data.items():
            self.epilepsy_score_wh.record(key, score_df.at[key, 'Stage_Code'])
            score_df.at[key, 'Stage_Code'] = value
            score_df.at[key, 'Stage'] = self.map_stages[value]

    def prepare_score_when_reset(self):
        score_df = self._get_display_score_df()
        if score_df is None:
            return
        # 将现在的sleep_score清空
        restore_data = self.epilepsy_score_wh.get_restore_data()
        if len(restore_data) == 0:
            return
        for key, value in restore_data.items():
            score_df.at[key, 'Stage_Code'] = value
            score_df.at[key, 'Stage'] = self.map_stages[value]

    def refresh_epilepsy_score(self):
        score_df = self._get_display_score_df()
        if score_df is None:
            return
        # 获取当前视图范围
        view_range_eeg = self.plot_eeg.getViewBox().viewRange()
        x_range = view_range_eeg[0]

        # 重新计算癫痫阶段统计
        stage_counts = score_df["Stage_Code"].value_counts()
        score_df.loc[0, "Normal_Count"] = stage_counts.get(0, 0)
        score_df.loc[0, "Seizure_Count"] = stage_counts.get(1, 0)

        # 这里逻辑有问题，更新的时候只有 canvas 更新，但是这个函数重绘了所有
        self.ax_hypnogram_plot()

        # 恢复
        vb_eeg = self.plot_eeg.getViewBox()
        vb_eeg.disableAutoRange(axis=pg.ViewBox.XAxis)  # 禁用X轴自动适配
        vb_eeg.setXRange(x_range[0], x_range[1], padding=0)

    def ax_hypnogram_plot(self):

        # """绘制分析结果"""
        QLLogging.log.debug("Plot the results of the analysis")
        score_df = self._get_display_score_df()
        if score_df is None:
            QLLogging.log.info("No score data available")
            return

        try:
            self.event_handler.clear_highlight()  # 清除高亮
            self.figure.clear()
            self.current_selected_epoch = None
            self.current_selected_epochs = []
            # 更新总共的页数
            self.top_widget.nav_buttons_widget.label_of_page.setText(f" of {self.get_total_page()}")

            QLLogging.log.debug(f"更新的总页数：{self.get_total_page()}")
            # 获取数据
            eeg_data = self.thread_run.eeg_data
            sfreq = self.thread_run.sfreq

            QLLogging.log.debug(f"plot_results——eeg_data:{eeg_data}")
            QLLogging.log.debug(f"plot_results——sfreq:{sfreq}")

            # 计算时间轴
            time_sec = np.arange(len(eeg_data)) / sfreq
            QLLogging.log.debug(f"plot_results——time_sec:{time_sec}")
            scores = score_df['Stage_Code'].values
            colors = [self.map_colors[score] for score in scores]

            # 计算时间点
            time_epochs_start = np.arange(len(scores)) * self.thread_run.epoch_length
            time_epochs_end = time_epochs_start + self.thread_run.epoch_length
            QLLogging.log.debug(f"plot_results——time_epochs_start:{time_epochs_start}")
            QLLogging.log.debug(f"plot_results——time_epochs_end:{time_epochs_end}")
            QLLogging.log.debug(f"plot_results——np.arange(len(scores)):{np.arange(len(scores))}")
            # 1. 分期结果图
            ax_hypnogram = self.figure.add_subplot(self.gs[0])
            ax_hypnogram.hlines(scores, time_epochs_start, time_epochs_end,
                                colors=colors, linewidths=40)
            ax_hypnogram.set_yticks([0, 1])
            ax_hypnogram.set_yticklabels(["Normal", "Seizure"])
            ax_hypnogram.set_ylabel("Stage")
            ax_hypnogram.set_ylim(-0.5, 1.5)
            # ax_hypnogram.set_xticks([])  # 去掉x轴刻度
            # ax_hypnogram.set_xticklabels([])  # 去掉x轴刻度标签
            ax_hypnogram.margins(x=0, y=0)  # 消除子图内部边距

            # 在绘制图形时设置字体大小
            ax_hypnogram.tick_params(labelsize=40)  # 设置刻度标签字体大小
            ax_hypnogram.set_ylabel(ax_hypnogram.get_ylabel(), fontsize=40)  # 设置y轴标签字体大小
            ax_hypnogram.set_title(ax_hypnogram.get_title(), fontsize=40)  # 设置标题字体大小

            # 设置轴标签的字体大小
            # for label in ax_hypnogram.get_xticklabels():
            #     label.set_fontsize(60)
            for label in ax_hypnogram.get_yticklabels():
                label.set_fontsize(40)

            self.epilepsy_score_wh.finish_backup()
            self.epilepsy_redo_score_wh.finish_backup()

            self.event_handler.clear_highlight()

            self.update_display_range()

        except Exception as e:
            QLLogging.log.exception(f"Error in plot_results: {str(e)}")
            import traceback
            traceback.print_exc()

    def undo_post_process(self):
        self.bottom_right_top_widget.pushButton_redo.setEnabled(True)
        if self.epilepsy_score_wh.is_empty():
            self.bottom_right_top_widget.pushButton_undo.setEnabled(False)

    def redo_post_process(self):
        self.bottom_right_top_widget.pushButton_undo.setEnabled(True)
        if self.epilepsy_redo_score_wh.is_empty():
            self.bottom_right_top_widget.pushButton_redo.setEnabled(False)

    def edit_post_process(self):
        if self.epilepsy_score_wh.is_empty():
            self.bottom_right_top_widget.pushButton_undo.setEnabled(False)
        else:
            self.bottom_right_top_widget.pushButton_undo.setEnabled(True)

        self.bottom_right_top_widget.pushButton_redo.setEnabled(False)
        self.epilepsy_redo_score_wh.clear()

    def reset_edit(self):
        while not self.epilepsy_score_wh.is_empty():
            self.prepare_score_when_reset()
            self.refresh_epilepsy_score()

        self.epilepsy_redo_score_wh.clear()
        self.epilepsy_score_wh.clear()
        self.bottom_right_top_widget.pushButton_undo.setEnabled(False)
        self.bottom_right_top_widget.pushButton_redo.setEnabled(False)

    def undo_edit(self):
        self.prepare_score_when_undo()
        self.refresh_epilepsy_score()
        self.undo_post_process()

    def redo_edit(self):
        self.prepare_score_when_redo()
        self.refresh_epilepsy_score()
        self.redo_post_process()

    def crop_data(self):
        """截取数据并立即更新"""
        QLLogging.log.debug("Capture data and update it instantly")
        # 读取时间输入
        start_str = self.bottom_left_widget.combobox_start.currentText() + " " + self.bottom_left_widget.lineedit_start.time().toString(
            "HH:mm:ss")
        end_str = self.bottom_left_widget.combobox_end.currentText() + " " + self.bottom_left_widget.lineedit_end.time().toString(
            "HH:mm:ss")

        # 定义时间格式
        time_format = "%Y-%m-%d %H:%M:%S"

        try:
            # 尝试将输入转换为datetime对象
            start_dt = datetime.datetime.strptime(start_str, time_format)
            end_dt = datetime.datetime.strptime(end_str, time_format)

            # 获取记录的开始时间
            meas_date = self.raw_processed.info['meas_date'].replace(tzinfo=None)
            # 获取原始数据的起始时间和终止时间
            end_time = meas_date + datetime.timedelta(
                seconds=int(self.raw_processed.n_times / self.raw_processed.info['sfreq']))  # 终止时间

            # 计算时间差，以获得相对于记录开始的秒数
            start_seconds = (start_dt - meas_date).total_seconds()
            end_seconds = (end_dt - meas_date).total_seconds()
            seconds = self.raw_processed.n_times / self.raw_processed.info['sfreq']

            # 检查时间是否有效
            if start_seconds < 0 or end_seconds > seconds or start_seconds > end_seconds:
                QMessageBox.warning(
                    self.window,
                    "Time Range Error",
                    f"The specified time range is invalid.\n\n"
                    f"Valid time range:\n"
                    f"Start: {meas_date}\n"
                    f"End: {end_time}"
                )
                return None
            # 更新数据
            if end_seconds == seconds:
                self.thread_run.raw_processed = self.thread_run.raw_processed.copy().crop(
                    tmin=start_seconds)  # 直接更新原始数据
                start_dt_utc = start_dt.replace(tzinfo=datetime.timezone.utc)
                self.thread_run.raw_processed.info.set_meas_date(start_dt_utc)
            else:
                self.thread_run.raw_processed = self.thread_run.raw_processed.copy().crop(tmin=start_seconds,
                                                                                          tmax=end_seconds)  # 直接更新原始数据
                start_dt_utc = start_dt.replace(tzinfo=datetime.timezone.utc)
                self.thread_run.raw_processed.info.set_meas_date(start_dt_utc)

            self.raw_processed = self.thread_run.raw_processed
            if hasattr(self, 'widget_left_label'):
                self.widget_left_label.set_meas_date(start_dt)
            return self.raw_processed

        except ValueError as e:
            QLLogging.log.exception(f"ValueError occurred: {e}")
            QMessageBox.warning(self.window, "Format Error", "The time should be in the format: YYYY-MM-DD HH:MM:SS.")

    def get_total_time_number(self):
        # 计算出总时间
        # from datetime import datetime
        start_data_part, start_time_part, end_data_part, end_time_part = self.get_start_end_time_bottom_left_widget()

        start_time = start_data_part + " " + start_time_part
        end_time = end_data_part + " " + end_time_part

        # 将字符串转换为datetime对象
        date_time_obj1 = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        date_time_obj2 = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        # 再将这个相对时间填充到label中，最后要进行更新开始时间

        # 计算时间差值
        time_diff = date_time_obj2 - date_time_obj1
        return time_diff

    def get_total_page(self):
        # 计算时间差值
        time_diff = self.get_total_time_number()
        # 计算出每一页的时间长度
        total_page_number = math.ceil(
            time_diff.total_seconds() / (self.thread_run.epoch_length * self.get_n_epochs_display()))
        if self.top_widget.combobox_select_n_epochs.currentText() == "All":
            return 1  # 如果是全部数据，则只显示一页
        return max(1, total_page_number)

    def getCurrentPage(self):
        """获取当前页码"""
        ts_value = self.widget_time_slider.time_slider.value()
        ts_min = self.widget_time_slider.time_slider.minimum()
        ts_max = self.widget_time_slider.time_slider.maximum()
        if ts_max == ts_min:
            return 1
        page = int((ts_value - ts_min) / (ts_max - ts_min) * (self.get_total_page() - 1)) + 1
        return max(1, min(page, self.get_total_page()))

    def open_save_picture_ui(self):
        from .SavePicCPM import SavePictureDialog
        # from datetime import datetime

        # 获取当前日期和时间
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d-%H%M%S")
        save_pic_dialog = SavePictureDialog(self)
        if save_pic_dialog.exec_() == QDialog.Accepted:
            try:
                # 获取到要保存的路径，dpi和图片格式
                params = save_pic_dialog.get_save_parameters()
                img_format = params['format'].lower().replace('.', '')
                dpi = params['resolution']

                # 创建保存目录
                default_folder = "Epilepsy_Analysis_pic"
                save_dir = os.path.join(params['path'], default_folder)
                os.makedirs(save_dir, exist_ok=True)

                # save_path = params['path']+ f"/SleepAnalysis{formatted_time}" + params['format']
                # 生成文件名
                result_path = os.path.join(save_dir, f"EpilepsyAnalysis{formatted_time}{params['format']}")

                # 弹出“请等待”消息框
                wait_box = QMessageBox(QMessageBox.Information, "请稍等", "数据正在保存中，请勿关闭窗口...", parent=self)
                wait_box.setStyleSheet(ControlStyle.get_widget_style())
                # 设置标准按钮为Ok，然后将其文本设置为空
                wait_box.setStandardButtons(QMessageBox.Ok)
                # 获取Ok按钮
                ok_button = wait_box.button(QMessageBox.Ok)
                if ok_button:
                    ok_button.setText("")  # 设置为空字符串

                # 隐藏关闭按钮
                wait_box.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint |
                                        Qt.WindowTitleHint)
                wait_box.show()

                # 刷新 GUI
                QApplication.processEvents()

                self.figure.savefig(
                    result_path,
                    dpi=dpi,
                    format=img_format,
                    bbox_inches='tight',  # 重要：防止裁剪
                    pad_inches=0.1  # 可选：增加边缘空间
                )  # 这里有一个问题：figure有残缺的，无法保存完整的图片

                # 保存 plot_widget 图片
                self.save_plot_widget(self.plot_eeg, save_dir,
                                      f"EpilepsyAnalysis_eeg{formatted_time}" + params['format'], dpi, img_format)
                self.save_plot_widget(self.plot_emg, save_dir,
                                      f"EpilepsyAnalysis_emg{formatted_time}" + params['format'], dpi, img_format)
                self.save_plot_widget(self.plot_acc, save_dir,
                                      f"EpilepsyAnalysis_acc{formatted_time}" + params['format'], dpi, img_format)
                self.save_Frequencywidget(self.plot_widget, save_dir,
                                          f"EpilepsyAnalysis_EEG_Frequency{formatted_time}" + params['format'], dpi,
                                          img_format)

                # 关闭提示框
                wait_box.close()

                OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'open save picture ui', 0)

            except ValueError as e:
                QLLogging.log.exception(f"open_save_picture_ui, error: {e}")

    def get_cache_directory_name(self):
        return 'Epilepsy_data_History'

    def open_save_data_ui(self):
        from .SavePicCPM import SaveDataDialog
        from .utils import pretreatment_df_score
        # from datetime import datetime

        # 获取当前日期和时间
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d-%H%M%S")
        export_df = self._get_export_score_df()
        if export_df is None:
            QMessageBox.information(self, "提示", "当前没有可保存的数据。")
            return
        combined_data = pretreatment_df_score(self.thread_run, export_df)
        save_data_dialog = SaveDataDialog(self)
        save_data_dialog.combobox_data_format.addItem(".mat")
        save_data_dialog.combobox_data_format.addItem(".cache")
        if save_data_dialog.exec_() == QDialog.Accepted:
            try:
                # 获取保存的参数
                params = save_data_dialog.get_save_parameters()
                img_format = params['format'].lower().replace('.', '')
                # 创建保存目录
                default_folder = "Epilepsy_Analysis_data"
                save_dir = os.path.join(params['path'], default_folder)
                os.makedirs(save_dir, exist_ok=True)

                # 弹出“请等待”消息框
                wait_box = QMessageBox(QMessageBox.Information, "请稍等", "数据正在保存中，请勿关闭窗口...", parent=self)
                wait_box.setStyleSheet(ControlStyle.get_widget_style())
                # 设置标准按钮为Ok，然后将其文本设置为空
                wait_box.setStandardButtons(QMessageBox.Ok)
                # 获取Ok按钮
                ok_button = wait_box.button(QMessageBox.Ok)
                if ok_button:
                    ok_button.setText("")  # 设置为空字符串

                # 隐藏关闭按钮
                wait_box.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint |
                                        Qt.WindowTitleHint)
                wait_box.show()

                # 刷新 GUI
                QApplication.processEvents()

                if img_format == "csv":
                    file_path = os.path.join(save_dir,
                                             f"{self.file_name}-epilepsy_data{formatted_time}.csv")  # 拼接目录和文件名
                    # 需要进行保存数据
                    df = pd.DataFrame(
                        combined_data
                    )

                    # 保存为CSV
                    df.to_csv(
                        file_path,  # 文件名
                        index=False,  # 是否保存索引
                        na_rep='nan',  # NaN值的表示方式
                    )

                    QLLogging.log.info(f"save epilepsy_data.csv success")

                elif img_format == 'mat':
                    # 这里需要进行检测，还是有点问题
                    from scipy.io import savemat
                    file_path = os.path.join(save_dir,
                                             f"{self.file_name}-epilepsy_data{formatted_time}.mat")  # 拼接目录和文件名
                    combined_dict = combined_data.to_dict("list")
                    # 保存为MAT文件，'data'是MAT文件中存储数据的变量名
                    savemat(file_path, {'data': combined_dict})

                    QLLogging.log.info(f"save epilepsy_data.mat success")

                elif img_format == "npy":
                    file_path = os.path.join(save_dir,
                                             f"{self.file_name}-epilepsy_data{formatted_time}.npy")  # 拼接目录和文件名
                    # 假设 df 是你想要保存的 DataFrame
                    df = pd.DataFrame(combined_data)
                    # 将 DataFrame 转换成 NumPy 数组
                    numpy_data = df.to_numpy()
                    # 使用 numpy.save 保存数组到 .npy 文件
                    np.save(file_path, numpy_data)  # 注意文件路径最好是 '.npy' 结尾以便识别

                    QLLogging.log.info(f"save epilepsy_data.npy success")

                elif img_format == 'cache':

                    file_path = os.path.join(save_dir,
                                             f"{self.file_name}-epilepsy_data_history{formatted_time}.cache")  # 拼接目录和文件名
                    print("file_path", file_path)
                    self.save_history_cache(file_path)

                    QLLogging.log.info(f"save epilepsy_data_history.cache success")

                # 关闭提示框
                wait_box.close()

                OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'open save data ui', 0)

            except Exception as e:
                QLLogging.log.exception(f"open_save_picture_ui, error: {e}")

    def set_pushButton_true(self):
        self.pushButton_save_pic.setEnabled(True)
        self.pushButton_save_data.setEnabled(True)
        self.pushButton_analyse.setEnabled(True)
        self.pushButton_load_history.setEnabled(True)

    def set_pushButton_false(self):
        self.pushButton_save_pic.setEnabled(False)
        self.pushButton_save_data.setEnabled(False)
        self.pushButton_analyse.setEnabled(False)
        self.pushButton_load_history.setEnabled(False)

        # 开始分析时，禁用跳转输入框
        if hasattr(self, 'lineedit_goto_epoch'):
            self.lineedit_goto_epoch.setEnabled(False)

    def on_pushButton_load_history_clicked(self):
        try:
            if self.open_history_cache() == None:
                return

            self.icon_with_text_widget.hide()
            self.draw_pic_widget.show()

            self.scrollarea_canvas.hide()
            self.bottom_right_top_widget.hide()
            self.widget_time_slider.hide()
            self.loading_overlay.showLoading()
            QApplication.processEvents()

            self.set_pushButton_false()

            # 清空 redo undo
            self.epilepsy_redo_score_wh.clear()
            self.epilepsy_score_wh.clear()
            self.bottom_right_top_widget.pushButton_undo.setEnabled(False)
            self.bottom_right_top_widget.pushButton_redo.setEnabled(False)

            self.plot_results()
            self.scrollarea_canvas.show()
            self.bottom_right_top_widget.show()
            self.top_widget.combobox_select_n_epochs.setCurrentText("All")
            self.top_widget.combobox_select_n_epochs.setEnabled(True)
            self.update_display_n_epochs()
            self.loading_overlay.hideLoading()

            self.set_pushButton_true()
            self.bottom_right_top_widget.pushButton_undo.setEnabled(True)
            self.bottom_right_top_widget.pushButton_redo.setEnabled(True)
            # 加载历史数据成功后，启用跳转输入框
            if hasattr(self, 'lineedit_goto_epoch'):
                self.lineedit_goto_epoch.setEnabled(True)

            OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.PREPROCESS.value, 'EpilepsyAnalysis load history', 0)

        except Exception as e:
            QLLogging.log.exception(f"Error in on_pushButton_load_history_clicked: {str(e)}")

    def save_Frequencywidget(self, plot_widget, save_dir, filename, dpi, img_format):
        # 导出 PyQtGraph 图像
        try:
            result_path = os.path.join(save_dir, filename)
            # 处理频谱图
            plot_item = plot_widget.plotItem
            img_items = [item for item in plot_item.items if isinstance(item, pg.ImageItem)]

            if img_items:
                img_item = img_items[0]
                img_data = img_item.image

                import matplotlib
                matplotlib.use('agg')
                import matplotlib.pyplot as aggplt

                # 创建matplotlib图形
                fig, ax = aggplt.subplots(figsize=(14, 4), dpi=dpi)

                # 获取坐标范围
                tr = img_item.transform()
                x_start = tr.dx()
                y_start = tr.dy()
                x_scale = tr.m11()
                y_scale = tr.m22()

                # 计算实际坐标
                x_end = x_start + img_data.shape[0] * x_scale
                y_end = y_start + img_data.shape[1] * y_scale
                # CET-R4 颜色映射的 RGB 值
                cet_r4_data = [
                    (0.0, 0.0, 0.3),
                    (0.0, 0.0, 1.0),
                    (0.0, 1.0, 1.0),
                    (1.0, 1.0, 0.0),
                    (1.0, 0.0, 0.0),
                    (0.5, 0.0, 0.0)
                ]

                # 创建 CET-R4 颜色映射
                cet_r4_cmap = LinearSegmentedColormap.from_list("CET-R4", cet_r4_data)
                # 绘制图像
                spec_data = self.thread_run.spectrogram_data
                vmin = spec_data.get('vmin', img_data.min())
                vmax = spec_data.get('vmax', img_data.max())
                im = ax.imshow(
                    img_data.T,  # 原始数据（不转置，与PyQtGraph数据方向一致）
                    extent=[x_start, x_end, y_start, y_end],  # 坐标范围：[x_min, x_max, y_min, y_max]
                    aspect='auto',  # 自动适应宽高比，与PyQtGraph的缩放行为一致
                    origin='lower',  # 原点在左下角（低频在底部，对应PyQtGraph invertY=False）
                    cmap=cet_r4_cmap,  # 颜色映射，与PyQtGraph的CET-R4接近
                    vmin=vmin,
                    vmax=vmax
                )
                # 设置坐标轴
                ax.set_xlabel(plot_item.axes["bottom"]["item"].label.toPlainText())
                ax.set_ylabel(plot_item.axes["left"]["item"].label.toPlainText())

                # # 添加colorbar
                aggplt.colorbar(im, ax=ax, label='Power (dB)')
                # 保存图像
                fig.savefig(result_path,
                            format=img_format,
                            dpi=dpi,
                            bbox_inches='tight')
                aggplt.close(fig)
                return

        except ValueError as e:
            QLLogging.log.exception(f"open_save_picture_ui, error: {e}")

    def save_plot_widget(self, plot_widget, save_dir, filename, dpi, img_format):
        """保存绘图部件为图像文件，确保与显示一致，根据当前视图范围进行单位转换"""
        try:
            result_path = os.path.join(save_dir, filename)
            fig, ax = plt.subplots(figsize=(14, 4), dpi=dpi)
            plot_item = plot_widget.plotItem

            # 获取当前视图范围
            view_range = plot_item.getViewBox().viewRange()
            x_range = view_range[0]
            y_range = view_range[1]

            # 获取原始Y轴标签
            original_ylabel = plot_item.axes["left"]["item"].label.toPlainText()

            # 根据当前视图的Y轴范围判断是否需要单位转换
            # 如果Y轴范围的最大绝对值大于1000，则进行单位转换
            max_abs_view = max(abs(y_range[0]), abs(y_range[1]))
            unit_converted = max_abs_view >= 1000
            scale_factor = 1000.0 if unit_converted else 1.0

            # 复制所有曲线，处理单位转换
            for curve in plot_item.curves:
                x, y = curve.getData()

                # 应用单位转换
                if unit_converted and y is not None:
                    y = y / scale_factor

                ax.plot(x, y,
                        color=curve.opts.get('pen', 'k').color().name(),
                        linewidth=curve.opts.get('pen', pg.mkPen('k')).width() if curve.opts.get('pen') else 1.0)

            # 设置坐标轴范围
            ax.set_xlim(x_range[0], x_range[1])

            # 调整Y轴范围（如果进行了单位转换）
            if unit_converted:
                ax.set_ylim(y_range[0] / scale_factor, y_range[1] / scale_factor)
            else:
                ax.set_ylim(y_range[0], y_range[1])

            ax.set_xlabel(plot_item.axes["bottom"]["item"].label.toPlainText())
            ax.set_ylabel(original_ylabel)

            if plot_item.titleLabel:
                ax.set_title(plot_item.titleLabel.text)

            ax.margins(x=0, y=0)

            if plot_item.showGrid(x=True, y=True):
                ax.grid(True, linestyle='--', alpha=0.7)

            if plot_item.legend is not None:
                ax.legend()

            fig.set_facecolor('white')
            fig.patch.set_edgecolor('none')

            # 保存图像
            fig.savefig(
                result_path,
                format=img_format,
                dpi=dpi,
                bbox_inches='tight',
                facecolor=fig.get_facecolor(),
                edgecolor='none'
            )
            plt.close(fig)

        except Exception as e:
            QLLogging.log.exception(f"Error saving plot: {e}")

    def open_history_cache(self):
        """打开历史缓冲文件，并进行绘图"""
        try:
            # 这里注意是写死的路径，如果路径修改需要进行修改
            user_docs = os.path.expanduser('~/Documents')
            log_dir = os.path.join(user_docs, self.get_cache_directory_name())

            # 确保文件夹存在
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # 打开文件选择对话框，只显示.cache文件
            file_path, _ = QFileDialog.getOpenFileName(
                parent=self,
                caption="选择癫痫数据缓存文件",
                directory=log_dir,
                filter="缓存文件 (*.cache);;所有文件 (*.*)"
            )

            if not file_path:
                return None  # 用户取消了选择

            # 确保选择的是.cache文件
            if not file_path.lower().endswith('.cache'):
                QMessageBox.warning(self, "文件类型错误", "请选择.cache类型的文件")
                return None

            # 读取.cache文件内容
            with open(file_path, 'rb') as f:
                content = pickle.load(f)

            if not self.compare_time(content):
                QMessageBox.information(self, "数据不匹配", "加载的文件与当前文件不匹配，请检查文件。")
                return None

            # 恢复所有保存的属性
            self.df_score = content["df_score"]
            self.df_display_score = None
            self.raw_processed = content["raw_processed"]
            self.thread_run.emg_channel = content['emg_channel']
            self.thread_run.acc_channel = content['acc_channel']
            self.thread_run.eeg_channel = content['eeg_channel']
            self.thread_run.emg_data = content['emg_data']
            self.thread_run.acc_data = content['acc_data']
            self.thread_run.eeg_data = content['eeg_data']
            self.thread_run.sfreq = content['sfreq']  # 添加采样率
            self.thread_run.emg_envelope = content['emg_envelope']
            self.thread_run.spectrogram_data = content['spectrogram_data']
            self.n_epochs = content['n_epochs']
            self.thread_run.epoch_length = content['epoch_length']

            return True

        except Exception as e:
            QLLogging.log.exception(f"open_history_cache error: {e}")

    def save_history_cache(self, file_path):
        """保存文件为历史缓冲文件"""
        try:
            data_to_cache = {
                'df_score': self.df_score,
                'raw_processed': self.raw_processed,
                'emg_channel': self.thread_run.emg_channel,  # 添加EMG通道属性
                'acc_channel': self.thread_run.acc_channel,
                'eeg_channel': self.thread_run.eeg_channel,
                'eeg_data': self.thread_run.eeg_data,
                'acc_data': self.thread_run.acc_data,
                'emg_data': self.thread_run.emg_data,
                'spectrogram_data': self.thread_run.spectrogram_data,
                'n_epochs': self.n_epochs,
                'epoch_length': self.thread_run.epoch_length,
                'sfreq': self.thread_run.sfreq,  # 添加采样率
                'emg_envelope': self.thread_run.emg_envelope  # 添加EMG包络线
            }

            with open(file_path, 'wb') as f:
                pickle.dump(data_to_cache, f)

        except Exception as e:
            QLLogging.log.exception(f"save_history_cache error: {e}")

    def compare_time(self, content):
        # 获取当前数据的时间信息
        current_start_time = self.raw_processed.info['meas_date'].replace(tzinfo=None)
        # current_end_time = current_start_time + datetime.timedelta(
        #     seconds=self.raw_processed.n_times / self.raw_processed.info['sfreq'])
        total_duration = int(self.raw_processed.times[-1])  # 转换为整数秒   数据总时长（秒）
        current_end_time = current_start_time + datetime.timedelta(seconds=total_duration)  # 终止时间

        # 获取缓存数据的时间信息
        cached_raw = content["raw_processed"]
        cached_start_time = cached_raw.info['meas_date'].replace(tzinfo=None)
        cached_end_time = cached_start_time + datetime.timedelta(
            seconds=cached_raw.n_times / cached_raw.info['sfreq'])

        # 比较时间信息（允许1秒的误差）
        time_tolerance = datetime.timedelta(seconds=1)

        start_time_match = abs(current_start_time - cached_start_time) <= time_tolerance
        end_time_match = abs(current_end_time - cached_end_time) <= time_tolerance

        if start_time_match and end_time_match:
            return True
        else:
            return False
