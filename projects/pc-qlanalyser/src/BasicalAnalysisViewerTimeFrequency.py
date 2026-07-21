import traceback

from PyQt5.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy,
    QLabel, QFrame, QLineEdit, QWidget, QComboBox, QSpacerItem, QMessageBox, QDialog, QProgressDialog
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from PyQt5.QtCore import QThread, pyqtSignal, QDateTime, Qt, QEvent, QTimer
from .BasicalAnalysisViewer import BasicalAnalysis, BasicalAnalysisViewer

from .Control_Style import ControlStyle
from .CustomControls import FrequencyCheckboxWidget, TimeSliderWidget, CustomFrequencyCheckboxWidget
from .utils import SaveUtils, RangeValidator
import sys
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QSpinBox, QPushButton
)
from .SavePicCPM import SavePictureDialog, SaveDataDialog, SavePictureDialog1
from PyQt5.QtCore import Qt
from .Infrastructure.log.QLLogging import QLLogging
import os
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import spectrogram
from datetime import timezone
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
from src.Infrastructure.DB.SQLLiteAccessor import SQLLiteDB_Only_MainTread
from src.Domain.OPLog.OPLog import OPLogTask, OPType, OPLog
from datetime import timezone, timedelta
import threading
from PyQt5.QtCore import QObject, pyqtSignal


ERS_ERD_INTERPRETATION_NOTE = (
    "Descriptive ERS/ERD layer only: labels compare each band-power trend "
    "window with the first available trend window for the same channel/band. "
    "ERS-like means relative power increase; ERD-like means relative power "
    "decrease. This belongs to the TFR/time-frequency result layer, not TRF "
    "(Temporal Response Function), and is not an independent event-locked "
    "statistical test."
)


def build_ers_erd_interpretation(band_power_stats, threshold_percent=5.0):
    """Build a descriptive ERS/ERD interpretation from TFR band-power trends.

    The interpretation intentionally stays inside the Time Frequency/TFR result layer.
    It is unrelated to TRF (Temporal Response Function) modeling, does not create
    a new runner, and does not claim event-locked inference.
    """
    if not band_power_stats or "Time (s)" not in band_power_stats:
        return {
            "note": ERS_ERD_INTERPRETATION_NOTE,
            "baseline": "unavailable",
            "bands": {}
        }

    bands = {}
    for key, values in band_power_stats.items():
        if not key.endswith("_Mean"):
            continue
        band = key[:-5]
        arr = np.asarray(values, dtype=float)
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            continue

        baseline = float(arr[0])
        latest = float(arr[-1])
        if abs(baseline) < 1e-12:
            relative_change_percent = None
            label = "baseline-near-zero"
        else:
            relative_change_percent = float(((latest - baseline) / abs(baseline)) * 100.0)
            if relative_change_percent >= threshold_percent:
                label = "ERS-like increase"
            elif relative_change_percent <= -threshold_percent:
                label = "ERD-like decrease"
            else:
                label = "neutral/stable"

        bands[band] = {
            "baseline_mean_power": baseline,
            "latest_mean_power": latest,
            "relative_change_percent": relative_change_percent,
            "label": label,
            "threshold_percent": threshold_percent,
        }

    return {
        "note": ERS_ERD_INTERPRETATION_NOTE,
        "baseline": "first available trend window in the same channel and band",
        "bands": bands,
    }


def compute_time_frequency_and_band_power(raw, winsize, channels, EEG_BANDS,
                                          lowfrequency=None, highfrequency=None, time_range=None,
                                          progress_callback=None, trend_window_sec=60):
    """
    计算时频图和频段功率数据。

    :param raw: 原始 EEG 数据对象
    :param winsize: 窗口大小（秒）
    :param channels: 要分析的通道列表
    :param EEG_BANDS: EEG 各频率波段定义
    :param lowfrequency: 最低频率，默认 None（分析全部频率）
    :param highfrequency: 最高频率，默认 None（分析全部频率）
    :param progress_callback: 可选的回调函数，用于报告进度
    :return: 包含时频图和频段功率数据的字典
    """
    sampling_rate = raw.info['sfreq']
    sfreq = raw.info['sfreq']
    # 如果指定了时间范围，提取对应时间段的数据
    if time_range:
        # 解包时间范围
        start_time, end_time = time_range

        # 如果时间范围是 QDateTime 类型，转换为 datetime
        if isinstance(start_time, QDateTime):
            start_time = start_time.toPyDateTime()
        if isinstance(end_time, QDateTime):
            end_time = end_time.toPyDateTime()

        # 获取测量起始时间
        meas_date = raw.info['meas_date']
        if isinstance(meas_date, tuple):  # 如果 meas_date 是元组，取第一个元素
            meas_date = meas_date[0]

        # 确保时间格式一致
        start_time = start_time.replace(tzinfo=timezone.utc)
        end_time = end_time.replace(tzinfo=timezone.utc)
        meas_date = meas_date.replace(tzinfo=timezone.utc)

        # 计算起始和结束索引
        start_idx = int(
            ((start_time - raw.info['meas_date'].replace(tzinfo=timezone.utc)).total_seconds()) * sfreq)
        end_idx = int(((end_time - raw.info['meas_date'].replace(
            tzinfo=timezone.utc)).total_seconds()) * sfreq) + sfreq
        # 添加边界检查
        if end_idx >= len(raw.times):
            end_idx = len(raw.times) - 1

        if end_idx <= start_idx:
            raise ValueError("Invalid time range: end time must be greater than start time.")

        # 裁剪数据
        raw = raw.copy().crop(tmin=start_idx / sfreq, tmax=end_idx / sfreq)

    # 提取通道数据
    data_dict_raw = {ch: raw.get_data(picks=ch) for ch in channels}
    all_ch = raw.info['ch_names']
    id_l = [all_ch.index(ch) + 1 for ch in channels]
    data_dict = {f'Ch{id_l[i]}_{channels[i]}': v for i, (k, v) in enumerate(data_dict_raw.items())}

    def no_filter(EEG, fs):
        return np.squeeze(EEG)

    data_dict = {ch: no_filter(data, sampling_rate) for ch, data in data_dict.items()}

    results = {}
    total_channels = len(data_dict)  # 总通道数
    current_channel = 0  # 当前处理的通道计数

    for channel, channel_data in data_dict.items():
        # 计算时频图
        nperseg = int(winsize * sampling_rate)
        noverlap = int(nperseg // 4 * 3)
        # 参数验证
        if nperseg > 1000000:  # 设置合理上限（根据实际需求调整）
            raise ValueError(f"nperseg 值过大 ({nperseg})。请减小窗口大小。")

        # 确保 nperseg 是正数
        if nperseg <= 0:
            raise ValueError("Window size is too small. Please increase the window size.")

        f, t, Sxx = spectrogram(channel_data, sampling_rate, nperseg=nperseg, noverlap=int(nperseg // 4 * 3))
        Sxx = 10 * np.log10(Sxx)  # 转换为分贝

        # 如果指定了频率范围，筛选频率
        if lowfrequency is not None and highfrequency is not None:
            good_freqs = np.logical_and(f >= lowfrequency, f <= highfrequency)
            Sxx = Sxx[good_freqs, :]
            f = f[good_freqs]

        # 保存时频图数据
        results[channel] = {
            "frequencies": f,
            "times": t,
            "spectrogram": Sxx
        }

        # 计算频段功率
        spectrogram_df = pd.DataFrame(Sxx, index=f, columns=t)
        band_power_stats = {"Time (s)": t}

        for band, (low, high) in EEG_BANDS.items():
            band_power = spectrogram_df.loc[(spectrogram_df.index >= low) & (spectrogram_df.index <= high)]
            mean_power = band_power.mean(axis=0)  # 按时间平均
            rms_power = np.sqrt(np.mean(np.square(band_power), axis=0))  # 计算 RMS

            band_power_stats[f"{band}_Mean"] = mean_power.values
            band_power_stats[f"{band}_RMS"] = rms_power.values

        # 保存频段功率数据

        n_timepoints = len(t)
        if len(t) < 2:
            raise ValueError("Time axis too short for trend computation.")

        time_step = t[1] - t[0]  # 每列的时间跨度（秒）
        interval = int(trend_window_sec / time_step)  # 一个趋势窗口跨多少列

        n_groups = n_timepoints // interval

        if n_groups >= 2:
            aggregated_stats = {"Time (s)": []}

            for i in range(n_groups):
                start_idx = i * interval
                end_idx = (i + 1) * interval
                aggregated_stats["Time (s)"].append(np.mean(t[start_idx:end_idx]))

            for band, (low, high) in EEG_BANDS.items():
                band_power = spectrogram_df.loc[(spectrogram_df.index >= low) & (spectrogram_df.index <= high)]

                aggregated_means = []
                aggregated_rms = []

                for i in range(n_groups):
                    start_idx = i * interval
                    end_idx = (i + 1) * interval
                    group_data = band_power.iloc[:, start_idx:end_idx]

                    mean_val = group_data.mean().mean()
                    rms_val = np.sqrt(np.mean(np.square(group_data)))

                    aggregated_means.append(mean_val)
                    aggregated_rms.append(rms_val)

                aggregated_stats[f"{band}_Mean"] = aggregated_means
                aggregated_stats[f"{band}_RMS"] = aggregated_rms

            results[channel]["band_power"] = aggregated_stats
        else:
            results[channel]["band_power"] = band_power_stats

        results[channel]["ers_erd_interpretation"] = build_ers_erd_interpretation(
            results[channel]["band_power"]
        )

        # 更新进度
        current_channel += 1
        if progress_callback:
            progress = int((current_channel / total_channels) * 100)
            progress_callback(progress)

    return results


from scipy.signal import spectrogram
import os


def save_window_analysis_data(f, t, Sxx, channel, EEG_BANDS, result_path, savetime,
                              data_format='.csv', trend_window_sec=60):
    """
    保存趋势分析（窗口分段统计）数据。

    Args:
        f: 频率数组
        t: 时间数组（spectrogram的列轴）
        Sxx: 频谱功率数据（频率 × 时间）
        channel: 当前通道名
        EEG_BANDS: EEG 频段定义 dict，如 {"Alpha": (8, 12)}
        result_path: 保存路径
        savetime: 文件名时间标记
        data_format: 保存格式（.csv / .npy / .mat）
        trend_window_sec: 趋势分析的窗口长度（单位：秒）
    """
    # 构造功率矩阵 DataFrame
    spectrogram_df = pd.DataFrame(Sxx, index=f, columns=t)

    if len(t) < 2:
        raise ValueError("Time axis is too short to compute time step.")

    # 计算时间步长（每一列代表多少秒）
    time_step = t[1] - t[0]
    trend_window_cols = int(trend_window_sec / time_step)  # 用秒数换算成列数

    n_timepoints = len(t)
    n_groups = n_timepoints // trend_window_cols

    aggregated_stats = {"Time (s)": []}

    if n_groups < 1:
        print("Trend window too large, not enough data to group.")
        return False

    # 计算每组时间的中心点
    for i in range(n_groups):
        start_idx = i * trend_window_cols
        end_idx = (i + 1) * trend_window_cols
        aggregated_stats["Time (s)"].append(np.mean(t[start_idx:end_idx]))

    # 遍历每个 EEG 频段
    for band, (low_f, high_f) in EEG_BANDS.items():
        band_power = spectrogram_df.loc[
            (spectrogram_df.index >= low_f) & (spectrogram_df.index <= high_f)
            ]

        aggregated_means = []
        aggregated_rms = []

        for i in range(n_groups):
            start_idx = i * trend_window_cols
            end_idx = (i + 1) * trend_window_cols

            group_data = band_power.iloc[:, start_idx:end_idx]
            mean_val = group_data.mean().mean()
            rms_val = np.sqrt(np.mean(np.square(group_data)))

            aggregated_means.append(mean_val)
            aggregated_rms.append(rms_val)

        aggregated_stats[f"{band}_Mean"] = aggregated_means
        aggregated_stats[f"{band}_RMS"] = aggregated_rms

    # 保存数据
    base_name = f'{channel}_trend_{trend_window_sec}s_analysis{savetime}'
    output_file = os.path.join(result_path, base_name + data_format)

    if data_format == '.csv':
        pd.DataFrame(aggregated_stats).to_csv(output_file, index=False)

    elif data_format == '.npy':
        save_dict = {
            'data': aggregated_stats,
            'trend_window_sec': trend_window_sec,
            'channel': channel
        }
        np.save(output_file, save_dict, allow_pickle=True)

    elif data_format == '.mat':
        from scipy.io import savemat
        save_dict = {
            'time': np.array(aggregated_stats["Time (s)"]),
            'trend_window_sec': trend_window_sec,
            'channel': channel
        }
        for band in EEG_BANDS.keys():
            if f"{band}_Mean" in aggregated_stats:
                save_dict[f"{band}_Mean"] = np.array(aggregated_stats[f"{band}_Mean"])
                save_dict[f"{band}_RMS"] = np.array(aggregated_stats[f"{band}_RMS"])
        savemat(output_file, save_dict)

    return True


def save_window_analysis_plots(f, t, Sxx, channel, EEG_BANDS, result_path, savetime,
                               img_format='png', dpi=300, trend_window_sec=60, start_time=None, end_time=None,
                               cancel_flag=None):
    """
    保存每个频段的趋势分析图（按指定时间窗口进行滑窗统计并绘图）。

    Args:
        f: 频率数组
        t: 时间数组（spectrogram时间轴）
        Sxx: 功率谱（频率 × 时间）
        channel: 当前通道名
        EEG_BANDS: EEG频段定义
        result_path: 图片保存路径
        savetime: 文件名时间标记
        img_format: 图片格式（png、svg 等）
        dpi: 图片分辨率
        trend_window_sec: 趋势分析的窗口大小（单位：秒）
    """
    # 默认频段颜色
    colors = {
        "Delta": "blue",
        "Theta": "orange",
        "Alpha": "green",
        "Beta": "red",
        "Gamma": "purple",
        "Other": "gray"
    }
    # 截取时间范围内的数据
    if start_time is not None and end_time is not None:
        time_mask = (t >= start_time) & (t <= end_time)
        if not np.any(time_mask):
            print(f"No data in time range {start_time}-{end_time}s for channel {channel}")
            return
        t = t[time_mask]
        Sxx = Sxx[:, time_mask]

    spectrogram_df = pd.DataFrame(Sxx, index=f, columns=t)

    if len(t) < 2:
        raise ValueError("Time axis too short.")

    # 计算每列代表的秒数（滑窗间隔）
    time_step = t[1] - t[0]
    trend_window_cols = int(trend_window_sec / time_step)

    n_timepoints = len(t)
    n_groups = n_timepoints // trend_window_cols

    if n_groups < 1:
        print(f"[{channel}] Trend window too large for plotting.")
        return

    # 计算每组中心时间点
    aggregated_times = [
        np.mean(t[i * trend_window_cols:(i + 1) * trend_window_cols])
        for i in range(n_groups)
    ]

    # 遍历频段，逐个绘图
    collected_num = 0
    for band, (low, high) in EEG_BANDS.items():
        # 检查取消标志
        if cancel_flag and cancel_flag():
            return collected_num
        plt.figure(figsize=(10, 6))

        # # 直接在原始数组上筛选频率范围
        # band_indices = np.where((f >= low) & (f <= high))[0]
        # band_power = Sxx[band_indices]

        band_power = spectrogram_df.loc[
            (spectrogram_df.index >= low) & (spectrogram_df.index <= high)
            ]

        aggregated_means = []
        aggregated_rms = []

        for i in range(n_groups):
            start_idx = i * trend_window_cols
            end_idx = (i + 1) * trend_window_cols
            group_data = band_power.iloc[:, start_idx:end_idx]
            mean_val = group_data.mean().mean()

            # group_data = band_power[:, start_idx:end_idx]
            # mean_val = np.mean(group_data)
            rms_val = np.sqrt(np.mean(np.square(group_data)))

            aggregated_means.append(mean_val)
            aggregated_rms.append(rms_val)

        # 画趋势图（均值±RMS）
        plt.errorbar(
            aggregated_times, aggregated_means,
            yerr=aggregated_rms,
            label=f"{band} Band",
            color=colors.get(band, "gray"),
            capsize=3, marker='o', linestyle='-'
        )

        plt.title(f"{channel} {band} Band Power Trend ({trend_window_sec}s window)")
        plt.xlabel("Time (s)")
        plt.ylabel("Power [a.u.]")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        filename = f'{channel}_{band}_band_power_{trend_window_sec}s_trend{savetime}.{img_format}'

        # 保存图像
        output_file = os.path.join(
            result_path,
            filename)
        plt.savefig(output_file, format=img_format, dpi=dpi, bbox_inches='tight')
        plt.close()
        collected_num += 1
    return collected_num


class TimeFrequencyWorker(QThread):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    error = pyqtSignal(str)
    result_ready = pyqtSignal(dict)  # 自定义信号，用于传递计算结果

    def __init__(self, raw, winsize, channels,
                 lowfrequency, highfrequency, selected_frequencies, time_range=None, result_path=None, Notch_50Hz=True,
                 Save_eps=False, trend_window_sec=60):
        super().__init__()
        self.raw = raw
        # self.HWratio = HWratio
        # self.timeinterval = timeinterval
        self.winsize = winsize
        self.channels = channels
        self.lowfrequency = lowfrequency
        self.highfrequency = highfrequency
        self.result_path = result_path
        self.Notch_50Hz = Notch_50Hz
        self.Save_eps = Save_eps
        self.time_range = time_range
        self.EEG_BANDS = selected_frequencies
        self.trend_window_sec = trend_window_sec

    def run(self):
        try:
            # from LFP_EEG_analyser.LFP_EEG_analyser.time_frequency_analysis import plot_time_frequency

            # Calculate total steps (one per channel)
            total_channels = len(self.channels)
            current_channel = 0

            def progress_callback(step):
                nonlocal current_channel
                current_channel += 1
                progress = int((current_channel / total_channels) * 100)
                self.progress.emit(progress)

            result_value = compute_time_frequency_and_band_power(self.raw, self.winsize, self.channels, self.EEG_BANDS,
                                                                 self.lowfrequency, self.highfrequency, self.time_range,
                                                                 progress_callback, self.trend_window_sec)
            self.finished.emit()
            self.result_ready.emit(result_value)

        except Exception as e:
            error_msg = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            self.error.emit(error_msg)


class TimeFrequencyCenterViewer(BasicalAnalysisViewer):
    # 定义信号，发送当前页码
    page_changed = pyqtSignal(int)

    def init_ui(self):
        # 首先调用父类的初始化
        super().init_ui()
        self.waveform_widget.getPlotItem().setContentsMargins(0, 10, 10, 10)
        self.waveform_widget.getAxis('left').setStyle(tickTextOffset=0)
        self.waveform_widget.getPlotItem().hideButtons()
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)  # 允许内容区域调整大小
        self.scroll_area.setStyleSheet(ControlStyle.get_scrollbar_style())
        # scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 禁用水平滚动条
        # scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 需要时显示垂直滚动条

        # 将图像区域设置为滚动区域的内容
        self.scroll_area.setWidget(self.plot_area)

        # 将滚动区域添加到主布局
        self.main_layout.addWidget(self.scroll_area)

        # 如果存在时间标签和滑块，先移除它们
        if hasattr(self, 'time_label_widget'):
            self.plot_layout.removeWidget(self.time_label_widget)
            self.time_label_widget.setParent(None)

        if hasattr(self, 'slider_widget'):
            self.plot_layout.removeWidget(self.slider_widget)
            self.slider_widget.setParent(None)

        self.main_layout.addWidget(self.time_label_widget)
        self.main_layout.addWidget(self.slider_widget)
        ## 其它各个频率 band power图片
        self.colors = {
            "Delta": "blue",
            "Theta": "orange",
            "Alpha": "green",
            "Beta": "red",
            "Gamma": "purple",
            "Other": "gray"
        }

        # 新增属性，控制显示时间范围
        # self.total_time_duration = 100  # 总时长，比如100秒，自己根据数据定
        self.visible_window = 10  # 可视窗口，比如只显示10秒

        self.full_tf_data = {}

    def eventFilter(self, source, event):
        # 拦截 waveform 和 heatmap 的滚轮事件
        wheels = (
            self.waveform_widget.viewport(),
            getattr(self, 'heatmap_widget', None) and self.heatmap_widget.viewport()
        )
        # if event.type() == QEvent.Wheel and source in wheels:
        #     delta = event.angleDelta().y()
        #     sb = self.scroll_area.verticalScrollBar()
        #     sb.setValue(sb.value() - delta)
        #     return True
        return super().eventFilter(source, event)

    def set_result_data_source(self, bar_data_source):
        """
        设置柱形图数据源。
        :param bar_data_source: 包含每个通道频段功率数据的列表
        """

        def rename_channels(data):
            """
            将通道名称从 'Ch1_EEG0' 修改为 'EEG0'。

            :param data: 包含通道数据的字典
            :return: 修改后的字典
            """
            renamed_data = {}
            for channel, channel_data in data.items():
                # 提取通道名称的后缀部分（去掉 'Ch1_' 或类似前缀）
                new_channel_name = channel.split('_', 1)[-1]
                renamed_data[new_channel_name] = channel_data
            return renamed_data

        self.result = rename_channels(bar_data_source)
        # print(bar_data_source)

    def plot_time_frequency_from_results(self):
        """
        根据计算结果绘制指定通道的时频图。
        """
        QLLogging.log.debug("Plotting time-frequency data from results...")
        results = self.result
        channel = self.channel_names[self.current_channel]

        if channel not in results:
            raise ValueError(f"Channel {channel} not found in results.")

        # 提取数据
        frequencies = results[channel]["frequencies"]
        times = results[channel]["times"]
        spectrogram = results[channel]["spectrogram"]  # (频率, 时间)

        # 清空旧图
        self.heatmap_widget.clear()

        # 动态设置颜色映射范围
        vmin = np.percentile(spectrogram, 10)
        vmax = np.percentile(spectrogram, 99)

        # 创建 ImageItem
        self.heatmap_img = pg.ImageItem()
        self.heatmap_widget.addItem(self.heatmap_img)

        # 设置位置和缩放
        self.heatmap_img.setImage(spectrogram.T)
        self.heatmap_img.setRect(pg.QtCore.QRectF(
            times[0], frequencies[0],
            times[-1] - times[0],
            frequencies[-1] - frequencies[0]
        ))

        # 设置颜色映射
        colormap = pg.colormap.get('CET-R4')
        self.heatmap_img.setColorMap(colormap)
        self.heatmap_img.setLevels([vmin, vmax])

        # 调整显示范围
        self.heatmap_widget.setYRange(frequencies[0], frequencies[-1])

        self.full_tf_data = {
            'frequencies': frequencies,
            'times': times,
            'spectrogram': spectrogram,
            'vmin': vmin,
            'vmax': vmax
        }

    # 统一时频图图和原图的左轴宽度（防止纵轴位数不一样导致不对齐）
    def _sync_left_axis_width(self):
        if not hasattr(self, 'waveform_widget') or not hasattr(self, 'heatmap_widget'):
            return
        a1 = self.waveform_widget.getAxis('left')
        a2 = self.heatmap_widget.getAxis('left')
        # 取当前两者中较大的轴宽，统一到同一个宽度
        # w = max(a1.width(), a2.width())
        # print(w)
        w = 60
        a1.setWidth(w)
        a2.setWidth(w)

    def init_bandpower_axes(self, num_bands):

        # 创建频带功率图子图
        if hasattr(self, 'heatmap_widget') and self.heatmap_widget:
            self.plot_layout.removeWidget(self.heatmap_widget)
            self.heatmap_widget.setParent(None)
            self.heatmap_widget.deleteLater()
            self.heatmap_widget = None

        # 清空 heatmap_img 引用
        if hasattr(self, 'heatmap_img'):
            self.heatmap_img = None

        self.heatmap_widget = pg.PlotWidget()
        self.heatmap_widget.setBackground('w')
        # 设置边距：左、底部、右、顶部
        self.heatmap_widget.getPlotItem().setContentsMargins(0, 10, 10, 10)

        self.heatmap_widget.getPlotItem().hideButtons()

        self.heatmap_widget.setLabel('left', 'Frequency (Hz)')
        # 隐藏 x 轴和 y 轴线，但保留刻度标签
        self.heatmap_widget.getAxis('bottom').setPen(None)
        self.heatmap_widget.getAxis('left').setPen(None)
        # 设置坐标轴字体颜色为深色
        self.heatmap_widget.getAxis('bottom').setTextPen(pg.mkPen('k'))
        self.heatmap_widget.getAxis('left').setTextPen(pg.mkPen('k'))
        self.heatmap_widget.setMouseEnabled(x=False, y=False)  # 禁用缩放/平移
        self.heatmap_widget.setMenuEnabled(False)  # 禁用右键菜单
        self.heatmap_widget.setMinimumHeight(300)  # 设置最小高度

        self.heatmap_widget.viewport().installEventFilter(self)
        self.plot_layout.insertWidget(1, self.heatmap_widget)

        # 清空画布
        self.figure.clear()
        self.bandpower_axes = []
        if num_bands > 0:

            # 设置固定的子图高度和间距
            SUBPLOT_HEIGHT = 2  # 每个子图的固定高度（英寸）
            SPACING = 0.5  # 子图之间的间距（英寸）

            # 计算总高度（包含间距）
            total_height = (SUBPLOT_HEIGHT * (num_bands)) + (SPACING * num_bands) + 0.1
            current_width = self.figure.get_figwidth()

            # 设置figure大小
            self.figure.set_size_inches(current_width, total_height)

            # 创建等高子图布局
            self.gs = self.figure.add_gridspec(
                num_bands,
                1,
                height_ratios=[1] * num_bands,  # 所有子图高度比例相等
                hspace=0.3  # 子图间距
            )

            # 为每个子图设置相同的高度
            for i in range(num_bands):
                ax = self.figure.add_subplot(self.gs[i])
                self.bandpower_axes.append(ax)

            # 统一设置所有子图的样式和大小
            for ax in self.bandpower_axes:
                # 基本样式设置
                ax.set_xticks([])
                ax.set_xticklabels([])
                for spine in ax.spines.values():
                    spine.set_visible(False)
                ax.tick_params(axis='both', which='both', length=0)

            # 调整整体布局
            self.figure.subplots_adjust(  # 范围 0-1
                left=0.07,  # 左边距
                right=0.98,  # 右边距
                bottom=0.1,  # 底部边距
                top=0.95,  # 顶部边距
                hspace=0.5  # 垂直间距
            )
            # 设置画布最小高度，确保所有画布高度一致
            pixels_per_inch = self.figure.get_dpi()
            subplot_height = (SUBPLOT_HEIGHT * pixels_per_inch)  # 每个子图的像素高度

            # 设置所有画布为相同高度
            self.canvas.setMinimumHeight(int(total_height * pixels_per_inch))
            QTimer.singleShot(0, self._sync_left_axis_width)

    def update_bandpower_canvases(self, trend_window_sec=60):
        """
        在单一画布上绘制不同频段的 band power 趋势曲线（以秒为单位窗口划分）。
        """

        QLLogging.log.debug("Updating bandpower canvases...")

        channel = self.channel_names[self.current_channel]
        if channel not in self.result:
            raise ValueError(f"Channel {channel} not found in data.")

        # 获取当前通道的频谱结果
        results = self.result[channel]
        f = results["frequencies"]
        t = results["times"]
        Sxx = results["spectrogram"]

        # 构造 DataFrame 便于操作
        spectrogram_df = pd.DataFrame(Sxx, index=f, columns=t)

        if len(t) < 2:
            QLLogging.log.warning("Time axis too short.")
            return

        # 时间步长（秒/列）
        time_step = t[1] - t[0]
        trend_window_cols = int(trend_window_sec / time_step)
        n_timepoints = len(t)
        n_groups = n_timepoints // trend_window_cols

        if n_groups < 1:
            QLLogging.log.warning(f"Not enough data to perform trend analysis for {trend_window_sec}s window.")
            return

        # 遍历频段
        for idx, ((band_name, (low_f, high_f)), ax) in enumerate(zip(self.EEG_BANDS.items(), self.bandpower_axes)):
            ax.clear()

            # 提取该频段的功率
            band_power = spectrogram_df.loc[
                (spectrogram_df.index >= low_f) & (spectrogram_df.index <= high_f)
                ]

            aggregated_means = []
            aggregated_rms = []
            aggregated_times = []

            for i in range(n_groups):
                start_idx = i * trend_window_cols
                end_idx = (i + 1) * trend_window_cols
                group_data = band_power.iloc[:, start_idx:end_idx]

                group_mean = group_data.mean().mean()
                group_rms = np.sqrt(np.mean(np.square(group_data)))

                aggregated_means.append(group_mean)
                aggregated_rms.append(group_rms)
                aggregated_times.append(np.mean(t[start_idx:end_idx]))

            # 绘制曲线（带误差条）
            ax.errorbar(
                aggregated_times, aggregated_means,
                yerr=aggregated_rms,
                label=f"{band_name} Band",
                color=self.colors.get(band_name, "gray"),
                capsize=3, marker='o', markersize=2,
                linewidth=1, linestyle='-'
            )

            if aggregated_means:
                baseline_power = aggregated_means[0]
                ax.axhline(
                    baseline_power,
                    color=self.colors.get(band_name, "gray"),
                    linestyle='--',
                    linewidth=0.8,
                    alpha=0.45,
                    label="ERS/ERD baseline"
                )
                interpretation = build_ers_erd_interpretation({
                    "Time (s)": aggregated_times,
                    f"{band_name}_Mean": aggregated_means,
                })
                label_text = interpretation.get("bands", {}).get(band_name, {}).get("label")
                if label_text:
                    ax.set_title(f"{band_name}: {label_text}", fontsize=9)

            # 美化图形
            ax.set_ylabel("Power [a.u.]")
            ax.set_xticks([])
            ax.set_xticklabels([])
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right')
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.tick_params(axis='both', which='both', length=0)

        # 刷新画布
        self.canvas.draw_idle()

    def set_para(self, window_size, selected_frequencies, min_frq,
                 max_frq):
        self.winsize = window_size
        self.EEG_BANDS = selected_frequencies
        # 初始化频带子图
        self.init_bandpower_axes(len(self.EEG_BANDS))
        self.lowfrequency = min_frq
        self.highfrequency = max_frq

    def update_plot_below(self):
        """
        根据当前通道更新柱形图和热力图,动态确定要绘制的列。
        """
        super().update_plot_below()
        # 清空所有子图
        for ax in self.bandpower_axes:
            ax.clear()
            # 重新设置基本样式（因为 clear 会清除所有设置）
            ax.set_xticks([])
            ax.set_xticklabels([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.tick_params(axis='both', which='both', length=0)

        # 更新频谱图
        self.plot_time_frequency_from_results()

        # 更新频带功率图 band power
        self.update_bandpower_canvases(trend_window_sec=self.trend_window_sec)

        self.scroll_time()
        QTimer.singleShot(0, self._sync_left_axis_width)

    def scroll_time(self):
        import time

        if not self.raw_data:
            return
        # 获取时间范围的起始时间
        start = self.start_time

        from PyQt5.QtCore import QDateTime
        qt_start = QDateTime(start)

        # # 获取时间戳
        start_timestamp = qt_start.toSecsSinceEpoch()

        pos = self.slider_widget.time_slider.value()

        start_time = pos
        end_time = pos + self.page_duration

        # 确保两个时间对象都有相同的时区设置
        meas_date = self.raw_data.info['meas_date']  # 获取测量日期
        if meas_date.tzinfo is None:
            meas_date = meas_date.replace(tzinfo=timezone.utc)

        if hasattr(self, 'waveform_left_text'):
            print(meas_date)
            self.waveform_left_text.set_meas_date(meas_date)

        # 【新增 1】关键：将 meas_date 传给父类创建的自定义坐标轴
        # 这样 RelativeTimeAxis 才能把 0,1,2 秒转换成 10:00:00, 10:00:01
        if hasattr(self, 'time_axis'):
            self.time_axis.set_meas_date(meas_date)

        total_start = self.total_start_time  # 分析起始时间
        if total_start is not None and total_start.tzinfo is None:
            total_start = total_start.replace(tzinfo=timezone.utc)

        # 计算开始时间
        start_time_waveform = (total_start - meas_date).total_seconds() + pos

        # 计算结束时间
        end_time_waveform = start_time_waveform + self.page_duration

        self._apply_waveform_page_guardrails(start_time_waveform, end_time_waveform)

        # 更新页码
        if not self.is_manually_changing_page:
            # self.current_page = int(start_time / self.page_duration) + 1
            self.get_current_page()
            self.page_changed.emit(self.current_page)

        # 创建4个均匀分布的时间点
        time_ticks = np.linspace(start_time, end_time, 4)
        time_strings = []
        # 将秒数转换为时分秒格式
        for seconds in time_ticks:
            # 计算实际时间戳
            actual_timestamp = start_timestamp + int(seconds)
            # 转换为 QDateTime
            actual_time = QDateTime.fromSecsSinceEpoch(actual_timestamp)
            # 格式化为时间字符串
            time_str = actual_time.toString('HH:mm:ss')
            time_strings.append(time_str)

        # 设置x轴刻度
        axis = self.heatmap_widget.getAxis('bottom')
        ticks = [(time_ticks[i], time_strings[i]) for i in range(len(time_ticks))]
        axis.setTicks([ticks])
        self.waveform_widget.getAxis('bottom').setTicks(None)

        self.heatmap_widget.setUpdatesEnabled(False)  # 禁用更新
        self.waveform_widget.setUpdatesEnabled(False)  # 禁用更新

        if hasattr(self, 'full_tf_data') and hasattr(self, 'heatmap_img') and self.heatmap_img:
            # 检查 ImageItem 是否已被销毁
            if not self.heatmap_img.isVisible():
                return  # 避免操作已销毁的对象
            # 计算当前窗口时间对应的索引
            all_times = self.full_tf_data['times']
            time_indices = np.where((all_times >= start_time) & (all_times <= end_time))[0]

            if len(time_indices) > 0:
                # 获取当前可见时间范围的频谱图数据
                visible_spectrogram = self.full_tf_data['spectrogram'][:, time_indices]
                visible_times = all_times[time_indices]
                frequencies = self.full_tf_data['frequencies']

                # 更新图像数据
                self.heatmap_img.setImage(visible_spectrogram.T)
                self.heatmap_img.setLevels([self.full_tf_data['vmin'], self.full_tf_data['vmax']])

                # 更新图像位置和范围
                self.heatmap_img.setRect(pg.QtCore.QRectF(
                    visible_times[0], frequencies[0],
                    visible_times[-1] - visible_times[0],
                    frequencies[-1] - frequencies[0]
                ))

        # 更新所有子图的时间范围
        for ax in self.bandpower_axes:
            ax.set_xlim(start_time, end_time)

        # 检查是否存在频带功率图
        if self.bandpower_axes:
            self.bandpower_axes[-1].set_xticks(time_ticks)
            self.bandpower_axes[-1].set_xticklabels(time_strings)

        # 统一刷新画布
        self.canvas.draw()  # 更新bandpower和热力图
        time_mask = (self.wave_times >= start_time_waveform) & (self.wave_times <= end_time_waveform)

        # 添加降采样
        wave_times_downsampled = self.wave_times[time_mask]
        wave_data_downsampled = self.wave_data[0][time_mask]

        # 应用降采样（针对大数据量）
        if len(wave_times_downsampled) > 1800000:
            wave_times_downsampled, wave_data_downsampled = self.downsample_data(
                wave_times_downsampled, wave_data_downsampled
            )
        # 更新ACC图像
        self.waveform_plot.setData(wave_times_downsampled, wave_data_downsampled)

        # self.waveform_plot.setData(self.wave_times[time_mask], self.wave_data[0][time_mask])
        self.heatmap_widget.setUpdatesEnabled(True)  # 启用更新
        self.waveform_widget.setUpdatesEnabled(True)  # 启用更新

    def downsample_data(self, x_data, y_data, max_points=1800000):
        """
        对数据进行降采样，确保绘制点数量不超过 max_points
        """
        if len(x_data) <= max_points:
            return x_data, y_data  # 数据点已足够少，无需降采样

        # 计算采样步长
        step = max(1, len(x_data) // max_points)

        # 固定间隔采样
        x_downsampled = x_data[::step]
        y_downsampled = y_data[::step]

        return x_downsampled, y_downsampled

    def save_data_without_path(self):
        """让用户选择保存路径并保存TimeFrequency分析数据"""
        try:
            # 检查数据有效性
            if not hasattr(self, 'result') or not self.result:
                QMessageBox.warning(
                    self.win,
                    "No Data",
                    "No analysis results to save.\nPlease perform TimeFrequency analysis first."
                )
                return False

            from datetime import datetime
            # 获取当前日期和时间
            current_time = datetime.now()
            formatted_time = current_time.strftime("%Y-%m-%d-%H%M%S")

            # 显示保存对话框
            dialog = SaveDataDialog(self)
            dialog.combobox_data_format.addItems([".mat"])
            if dialog.exec_() == QDialog.Accepted:
                # 获取保存参数
                params = dialog.get_save_parameters()
                save_path = params['path']
                data_format = params['format'].lower()

                # 创建保存目录
                default_folder = "TimeFrequency_Analysis_data"
                save_dir = os.path.join(save_path, default_folder)
                os.makedirs(save_dir, exist_ok=True)

                # 保存每个通道的数据
                for channel, data in self.result.items():
                    if data_format == '.csv':
                        # 1. 保存时频数据
                        spectrogram_df = pd.DataFrame(
                            data["spectrogram"],
                            index=data["frequencies"],
                            columns=data["times"]
                        )
                        spectrogram_df.to_csv(
                            os.path.join(save_dir, f'{channel}_time_frequency{formatted_time}.csv')
                        )

                        # 2. 保存频带功率数据
                        band_power_df = pd.DataFrame(data["band_power"])
                        band_power_df.to_csv(
                            os.path.join(save_dir, f'{channel}_band_power_stats{formatted_time}.csv'),
                            index=False
                        )

                    elif data_format == '.npy':
                        # 保存为单个NPY文件
                        np.save(
                            os.path.join(save_dir, f'{channel}_analysis_data{formatted_time}.npy'),
                            {
                                'spectrogram': data["spectrogram"],
                                'frequencies': data["frequencies"],
                                'times': data["times"],
                                'band_power': data["band_power"],
                                'ers_erd_interpretation': data.get("ers_erd_interpretation", {})
                            }
                        )

                    elif data_format == '.mat':
                        # 保存为MATLAB格式
                        from scipy.io import savemat
                        savemat(
                            os.path.join(save_dir, f'{channel}_analysis_data{formatted_time}.mat'),
                            {
                                'spectrogram': data["spectrogram"],
                                'frequencies': data["frequencies"],
                                'times': data["times"],
                                'band_power': data["band_power"]
                            }
                        )
                    # 3. 保存窗口分析数据
                    interpretation_path = os.path.join(
                        save_dir, f'{channel}_ers_erd_interpretation{formatted_time}.json'
                    )
                    with open(interpretation_path, 'w', encoding='utf-8') as f:
                        json.dump(
                            data.get("ers_erd_interpretation", {}),
                            f,
                            ensure_ascii=False,
                            indent=2
                        )

                    save_window_analysis_data(
                        data["frequencies"],
                        data["times"],
                        data["spectrogram"],
                        channel,
                        self.EEG_BANDS,
                        save_dir,
                        savetime=formatted_time,
                        data_format=data_format,
                        trend_window_sec=self.trend_window_sec
                    )

                # 显示成功消息
                QMessageBox.information(
                    self.win,
                    "Save Success",
                    f"Analysis results have been saved to:\n{save_dir}"
                )
                QLLogging.log.info(f"TimeFrequency analysis data saved successfully to {save_dir}")
                OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'Save Data', 0)
                return True

        except Exception as e:
            QMessageBox.critical(
                self.win,
                "Error",
                f"Failed to save data: {str(e)}"
            )
            QLLogging.log.exception(f"Error saving TimeFrequency analysis data: {str(e)}")
            return False

    def on_save_progress(self, percent, message, progress_dialog):
        """处理总体进度更新(更新进度条)"""
        progress_dialog.setValue(percent)
        progress_dialog.setLabelText(
            f"<span style='font-family:Microsoft YaHei'>Successfully saved : &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='color:#2A87DB'>{message}</span>")
        QApplication.processEvents()

    def cancel_save(self):
        """用户点击取消"""
        if hasattr(self, 'save_worker') and self.save_worker:
            self.save_worker.cancel()

    def on_save_finished(self, overall_progress, save_dir, progress_dialog):
        """保存完成"""
        progress_dialog.close()

        if hasattr(self, 'save_worker') and self.save_worker._is_cancelled:
            #     QMessageBox.information(self, "Cancelled",
            #                             f"Saving cancelled. Saved {overall_progress} pages.")
            # else:
            QMessageBox.information(self, "Save Complete",
                                    f"Successfully saved {overall_progress} pages to\n{save_dir}")

        # 清理资源
        if hasattr(self, 'save_thread') and self.save_thread:
            self.save_thread.quit()
            self.save_thread.wait()

    def _get_waveform_ylim(self, amplitude_str):
        """把幅值下拉（如 '±2000' / 'Auto'）解析为 (-max, +max)。单位 μV。Auto/异常返回 None。"""
        if not amplitude_str or str(amplitude_str).strip() == "Auto":
            return None
        try:
            vmax = float(str(amplitude_str).lstrip('±'))
            return (-vmax, vmax)
        except Exception:
            return None

    def _downsample_envelope(self, x, y, max_points):
        """
        包络式降采样：将 (x,y) 降到 <= max_points。
        对每个窗口保留 min/max，视觉近似无损，绘制/保存更快更省内存。
        """
        n = len(y)
        if n <= max_points or max_points <= 0:
            return x, y
        import numpy as np
        win = int(np.ceil(n / max_points))
        n_fit = (n // win) * win
        y_fit = y[:n_fit].reshape(-1, win)
        x_fit = x[:n_fit].reshape(-1, win)

        y_min = y_fit.min(axis=1)
        y_max = y_fit.max(axis=1)
        x_mid = x_fit[:, win // 2]

        x_ds = np.empty(y_min.size * 2, dtype=x.dtype)
        y_ds = np.empty(y_min.size * 2, dtype=y.dtype)
        x_ds[0::2] = x_mid;
        x_ds[1::2] = x_mid
        y_ds[0::2] = y_min;
        y_ds[1::2] = y_max

        if n_fit < n:  # 把尾部不足一窗的数据补上
            x_ds = np.concatenate([x_ds, x[n_fit:]])
            y_ds = np.concatenate([y_ds, y[n_fit:]])
        return x_ds, y_ds

    def save_figure_without_path(self):
        """让用户选择路径并保存图表
        目前逻辑是原始波形图和频域图做切片，可分为保存全部页和当前页
        频带功率图未切片"""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        import os
        from datetime import datetime
        if not hasattr(self, 'result') or not self.result:
            QMessageBox.warning(
                self.win,
                "No Data",
                "No analysis results to save.\nPlease perform TimeFrequency analysis first."
            )
            return

        from datetime import datetime
        # 获取当前日期和时间
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d-%H%M%S")

        # todo 2. 显示保存图片对话框
        dialog = SavePictureDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                # 3. 获取保存参数
                params = dialog.get_save_parameters()
                save_dir = params['path']
                img_format = params['format'].lower().replace('.', '')
                dpi = params['resolution']

                # 获取默认保存路径
                default_folder = f"TimeFrequency_Analysis_pic"

                # 创建保存文件夹
                result_path = os.path.join(save_dir, default_folder)
                os.makedirs(result_path, exist_ok=True)

                max_value = 0
                max_value += (len(self.EEG_BANDS) + 1) * len(self.result)
                max_value += len(self.result)
                progress_dialog = SavePictureDialog1.create_progress_dialog(
                    title="QLAnalyser",
                    label_text=f"<span style='font-family:Microsoft YaHei'>Saving page......",
                    max_value=max_value,
                    parent=self
                )
                progress_dialog.setValue(0)
                progress_dialog.show()
                self.save_worker = SaveWorker(
                    self, result_path, formatted_time, img_format, dpi, max_value
                )
                self.save_thread = QThread()

                # 将worker移动到线程
                self.save_worker.moveToThread(self.save_thread)

                # 连接信号
                # 更新进度条
                self.save_worker.progress.connect(
                    lambda percent, message: self.on_save_progress(percent, message, progress_dialog))
                # 连接取消按钮
                progress_dialog.canceled.connect(lambda: self.cancel_save())
                # 线程结束处理
                self.save_worker.finished.connect(
                    lambda percent: self.on_save_finished(percent, result_path, progress_dialog))
                self.save_worker.finished.connect(self.save_thread.quit)
                self.save_worker.finished.connect(self.save_worker.deleteLater)
                self.save_thread.finished.connect(self.save_thread.deleteLater)

                # 启动线程
                self.save_thread.started.connect(self.save_worker.run)
                self.save_thread.start()

            except Exception as e:
                # 错误消息提示
                QMessageBox.critical(
                    self.win,
                    "Error",
                    f"Failed to save figures: {str(e)}"
                )
                QLLogging.log.exception(f"Error saving figure:\n{str(e)}")

    def on_save_current_finished(self, wait_box):
        """保存完成后的处理"""
        wait_box.close()
        self.save_thread.join()  # 等待线程结束

        # 显示成功消息
        QMessageBox.information(
            self.win,
            "Save Success",
            f"Figures have been saved to:\n{self.save_worker.result_path}"
        )
        QLLogging.log.info(f"Figures saved successfully to {self.save_worker.result_path}")
        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'Save Pic', 0)

    def save_waveform_offscreen(self, channel_name, start_time, end_time, save_dir, filename, dpi, img_format):
        """
        离屏渲染波形图（加入 y 轴限制 & 超大数据“包络式”降采样），不更新当前显示
        """
        result_path = os.path.join(save_dir, filename)

        # 创建离屏图形
        fig, ax = plt.subplots(figsize=(16, 6), dpi=dpi)

        # 根据幅值下拉决定固定的 y 轴范围（与分析图一致）
        waveform_ylim = None
        try:
            if hasattr(self, 'amplitude_selector') and self.amplitude_selector is not None:
                waveform_ylim = self._get_waveform_ylim(self.amplitude_selector.currentText())
        except Exception:
            waveform_ylim = None

        # 获取指定通道的数据
        ch_index = self.channel_names.index(channel_name)
        ch_name = self.channel_names[ch_index]

        # 计算时间范围内的数据索引
        meas_date = self.raw_data.info['meas_date']
        if meas_date.tzinfo is None:
            meas_date = meas_date.replace(tzinfo=timezone.utc)

        total_start = self.total_start_time
        if total_start is not None and total_start.tzinfo is None:
            total_start = total_start.replace(tzinfo=timezone.utc)

        # 计算相对于 total_start 的绝对时间
        absolute_start_time = total_start + timedelta(seconds=start_time)
        absolute_end_time = total_start + timedelta(seconds=end_time)

        # 计算开始和结束索引
        start_idx = int(((absolute_start_time - meas_date).total_seconds()) * self.fs)
        end_idx = int(((absolute_end_time - meas_date).total_seconds()) * self.fs)

        # 获取数据
        wave_data, wave_times = self.raw_data[ch_name, start_idx: end_idx]

        if len(wave_times) == 0:
            plt.close(fig)
            return

        # 仅在数据极大时启用“包络式”降采样
        fig_w_px = int(fig.get_figwidth() * fig.get_dpi())  # 图像像素宽度
        max_pts = max(20000, fig_w_px * 4)  # 单条曲线最大点数上限（经验值）
        wt, wd = wave_times, wave_data[0]
        if len(wd) > max_pts:
            wt, wd = self._downsample_envelope(wt, wd, max_pts)

        # 绘制波形
        line, = ax.plot(wt, wd, color='black', linewidth=0.5)
        # 小优化：更省内存/更快
        line.set_antialiased(False)
        line.set_rasterized(False)

        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Amplitude(μV)')
        ax.set_title(f'{ch_name} Waveform')
        ax.margins(x=0, y=0)
        ax.grid(True, linestyle='--', alpha=0.7)

        # 设置 x 轴范围（相对时间）
        ax.set_xlim(start_time, end_time)

        # === y 轴：优先按幅值固定；否则自适应（含10%边距） ===
        if waveform_ylim is not None:
            ax.set_ylim(waveform_ylim)
        else:
            ymin = float(np.min(wd));
            ymax = float(np.max(wd))
            if np.isfinite(ymin) and np.isfinite(ymax) and ymax > ymin:
                y_range = ymax - ymin
                margin = y_range * 0.1 if y_range > 0 else 0.1
                ax.set_ylim(ymin - margin, ymax + margin)
            else:
                ax.set_ylim(-100, 100)

        # 保存
        fig.set_facecolor('white')
        fig.patch.set_edgecolor('none')
        fig.savefig(result_path, format=img_format, dpi=dpi,
                    bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close(fig)

        QLLogging.log.info(f"Saved waveform offscreen: {result_path}")

    def save_Frequencywidget(self, channel_name, frequencies, times, spectrogram, save_dir, dpi, img_format,
                             start_time=None, end_time=None):
        """
        使用 matplotlib 重新绘制频谱图并保存
        :param channel_name: 通道名称
        :param frequencies: 频率轴数据
        :param times: 时间轴数据
        :param spectrogram: 频谱图数据
        :param save_dir: 保存路径
        :param dpi: 图像分辨率
        :param img_format: 图像格式
        """
        try:
            # 如果没有指定时间范围，保存全部数据
            if start_time is None or end_time is None:
                time_mask = np.ones_like(times, dtype=bool)
            else:
                # 直接使用时频图的时间轴来截取当前页面范围
                time_mask = (times >= start_time) & (times <= end_time)

            # 如果没有数据在时间范围内，直接返回
            if not np.any(time_mask):
                QLLogging.log.warning(f"No data in time range {start_time}-{end_time}s for channel {channel_name}")
                return

            # 截取时间范围内的数据
            visible_times = times[time_mask]
            visible_spectrogram = spectrogram[:, time_mask]

            import matplotlib
            matplotlib.use('agg')
            import matplotlib.pyplot as aggplt

            # 创建matplotlib图形
            fig, ax = aggplt.subplots(figsize=(14, 4), dpi=dpi)

            # 动态设置颜色映射范围（基于可见数据）
            vmin = np.percentile(visible_spectrogram, 10)
            vmax = np.percentile(visible_spectrogram, 99)

            # 创建 CET-R4 颜色映射
            cet_r4_data = [
                (0.0, 0.0, 0.3),
                (0.0, 0.0, 1.0),
                (0.0, 1.0, 1.0),
                (1.0, 1.0, 0.0),
                (1.0, 0.0, 0.0),
                (0.5, 0.0, 0.0)
            ]
            cet_r4_cmap = LinearSegmentedColormap.from_list("CET-R4", cet_r4_data)

            # 绘制频谱图
            im = ax.imshow(
                visible_spectrogram,
                extent=[visible_times[0], visible_times[-1], frequencies[0], frequencies[-1]],
                aspect='auto',
                origin='lower',
                cmap=cet_r4_cmap,
                vmin=vmin,
                vmax=vmax
            )

            # 设置坐标轴标签
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Frequency (Hz)')

            # 添加时间范围到标题
            if start_time is not None and end_time is not None:
                ax.set_title(f'{channel_name} Time-Frequency Analysis ({start_time:.1f}-{end_time:.1f}s)')
            else:
                ax.set_title(f'{channel_name} Time-Frequency Analysis')

            # 添加colorbar
            cbar = aggplt.colorbar(im, ax=ax, label='Power (dB)')

            # 保存图像
            fig.savefig(save_dir,
                        format=img_format,
                        dpi=dpi,
                        bbox_inches='tight',
                        facecolor='white',
                        edgecolor='none')
            aggplt.close(fig)

            QLLogging.log.info(f"Saved frequency widget for channel {channel_name}: {save_dir}")

        except Exception as e:
            QLLogging.log.exception(f"save_Frequencywidget, error: {e}")


class TimeFrequencyAnalysisViewer(BasicalAnalysis):
    def __init__(self, title, channel_name, parent=None):
        super().__init__(title, channel_name, parent)
        self.setWindowTitle("Time Frequency Analysis")

    def init_center_and_bottom(self, content_layout):
        """自定义中央显示区域和底部按钮"""
        self.viewer = TimeFrequencyCenterViewer()
        super().init_center_and_bottom(content_layout)
        self.viewer.hide()
        self.h_layout.addWidget(self.viewer)

    def init_left_panel(self, content_layout):
        """自定义左侧控制栏"""
        # 调用父类的 init_left_panel 方法
        super().init_left_panel(content_layout)

        # 添加 time_selector
        self.left_layout.addWidget(self.time_selector)

        # 添加分割线
        separator_between_time_and_frequency = QFrame()
        separator_between_time_and_frequency.setFrameShape(QFrame.HLine)
        separator_between_time_and_frequency.setStyleSheet("background-color: #a9a9a9;")
        separator_between_time_and_frequency.setFixedHeight(1)
        self.left_layout.addWidget(separator_between_time_and_frequency)

        # 添加property选择控件
        property_layout = QVBoxLayout()
        property_layout.setContentsMargins(30, 10, 0, 10)
        property_layout.setSpacing(10)
        # 添加标题标签
        title_label = QLabel("Property")
        title_label.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(title_label, 12)
        property_layout.addWidget(title_label)
        # 行布局
        h_layout = QHBoxLayout()
        property_layout.addLayout(h_layout)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(5)
        # 左边标签
        label = QLabel("Frequency(Hz)")
        label.setFixedWidth(150)
        label.setStyleSheet(ControlStyle.get_wiget400_word_style(14))
        h_layout.addWidget(label)
        self.min_edit = QLineEdit("1.0")
        self.max_edit = QLineEdit("40.0")
        # 设置浮点数验证器（最小值：0.0，最大值：1.0，精度：1位小数）
        validator = RangeValidator(0.001, 30000.000, decimals=3, parent=None)  # 设置小数点后的精度显示
        self.min_edit.setValidator(validator)
        self.max_edit.setValidator(validator)
        for edit in (self.min_edit, self.max_edit):
            edit.setFixedWidth(60)
            edit.setAlignment(Qt.AlignCenter)
            # edit.setValidator(QDoubleValidator())
            edit.setStyleSheet(ControlStyle.get_lineEdit_style())

        dash = QLabel("_")
        dash.setFixedWidth(10)
        dash.setAlignment(Qt.AlignLeft)
        dash.setStyleSheet("color: #808080; font-size: 14px;")
        h_layout.addStretch()  # 左侧弹簧
        h_layout.addWidget(self.min_edit)
        h_layout.addWidget(dash)
        h_layout.addWidget(self.max_edit)
        h_layout.addStretch()  # 右侧弹簧

        # 行布局
        h_layout_window_size = QHBoxLayout()
        property_layout.addLayout(h_layout_window_size)
        h_layout_window_size.setContentsMargins(0, 0, 0, 0)
        h_layout_window_size.setSpacing(5)
        # 左边标签
        label = QLabel("Window size")
        label.setFixedWidth(150)
        label.setStyleSheet(ControlStyle.get_wiget400_word_style(14))
        h_layout_window_size.addWidget(label)
        self.edit_windoe_size = QLineEdit("4")
        validator1 = RangeValidator(0.001, 30000.000, decimals=3, parent=None)  # 设置小数点后的精度显示
        self.edit_windoe_size.setValidator(validator1)
        self.edit_windoe_size.setFixedWidth(40)
        self.edit_windoe_size.setAlignment(Qt.AlignCenter)
        # edit.setValidator(QDoubleValidator())
        self.edit_windoe_size.setStyleSheet(ControlStyle.get_lineEdit_style())

        h_layout_window_size.addStretch()  # 左侧弹簧
        h_layout_window_size.addWidget(self.edit_windoe_size)
        h_layout_window_size.addStretch()  # 右侧弹簧

        # 行布局
        h_layout_trend_window = QHBoxLayout()
        property_layout.addLayout(h_layout_trend_window)
        h_layout_trend_window.setContentsMargins(0, 0, 0, 0)
        h_layout_trend_window.setSpacing(5)
        # 左边标签
        label = QLabel("trend window")
        label.setFixedWidth(150)
        label.setStyleSheet(ControlStyle.get_wiget400_word_style(14))
        h_layout_trend_window.addWidget(label)
        self.edit_trend_window_sec = QLineEdit("60")
        validator1 = RangeValidator(0.001, 30000.000, decimals=3, parent=None)  # 设置小数点后的精度显示
        self.edit_trend_window_sec.setValidator(validator1)
        self.edit_trend_window_sec.setFixedWidth(40)
        self.edit_trend_window_sec.setAlignment(Qt.AlignCenter)
        self.edit_trend_window_sec.setStyleSheet(ControlStyle.get_lineEdit_style())

        h_layout_trend_window.addStretch()  # 左侧弹簧
        h_layout_trend_window.addWidget(self.edit_trend_window_sec)
        h_layout_trend_window.addStretch()  # 右侧弹簧

        explanation_label = QLabel(
            "ERS/ERD labels are descriptive TFR interpretations, not TRF modeling: "
            "relative increase/decrease vs the first trend window, not a separate event-locked test."
        )
        explanation_label.setWordWrap(True)
        explanation_label.setStyleSheet(ControlStyle.get_wiget400_word_style(11))
        property_layout.addWidget(explanation_label)

        self.left_layout.addLayout(property_layout)

        # 添加一个固定的下方空白区域
        bottom_spacer = QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.left_layout.addItem(bottom_spacer)

        # 添加分割线
        separator_between_time_and_frequency = QFrame()
        separator_between_time_and_frequency.setFrameShape(QFrame.HLine)
        separator_between_time_and_frequency.setStyleSheet("background-color: #a9a9a9;")
        separator_between_time_and_frequency.setFixedHeight(1)
        self.left_layout.addWidget(separator_between_time_and_frequency)

        # 添加频率选择控件
        freq_dict = {
            "Delta": (0.5, 4),
            "Theta": (4, 8),
            "Alpha": (8, 12),
            "Beta": (12, 30),
            "Gamma": (30, 100),
            "Other": (0.5, 200)
        }
        # self.frequency_selector = FrequencyCheckboxWidget(freq_dict=freq_dict, label_text="Frequency(Hz)")
        self.frequency_selector = CustomFrequencyCheckboxWidget(freq_dict=freq_dict, label_text="Frequency(Hz)")

        self.left_layout.setContentsMargins(0, 0, 0, 50)
        self.left_layout.addWidget(self.frequency_selector)
        # 创建一个空白区域
        spacerItem = QSpacerItem(314, 50, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.left_layout.addSpacerItem(spacerItem)
        self.left_layout.addStretch()  # 添加弹性空间

    def check_frequency_overlap(self, selected_frequencies):
        """检查所选频段是否存在频率交叉（排除Other频段）"""
        # 过滤掉"Other"频段，仅保留需要检查的频段
        filtered_bands = [
            (band, (min_freq, max_freq))
            for band, (min_freq, max_freq) in selected_frequencies.items()
            if band != "Other"  # 排除Other频段
        ]

        # 如果有效频段不足2个，无需检查交叉
        if len(filtered_bands) < 2:
            return False

        # 将剩余频段按最小值排序
        sorted_bands = sorted(filtered_bands, key=lambda x: x[1][0])

        # 检查相邻频段是否交叉
        for i in range(len(sorted_bands) - 1):
            current_band, (current_min, current_max) = sorted_bands[i]
            next_band, (next_min, next_max) = sorted_bands[i + 1]
            # 若当前频段最大值 > 下一个频段最小值，存在交叉
            if current_max > next_min:
                return True
        return False

    def on_analyse_clicked(self):
        """处理 Analyse 按钮点击事件"""
        try:
            self.get_valid_time_range()
            # 检查 scale_seconds 是否为有效值
            if not self.time_selector.validate_time_range() or not self.scale_seconds or self.scale_seconds <= 0:
                # 获取有效的时间范围
                start_time, end_time = self.time_selector.min_time, self.time_selector.max_time

                # 格式化时间显示
                start_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
                end_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
                QMessageBox.warning(
                    self.win,
                    "Time Range Error",
                    f"The specified time range is invalid.\n\n"
                    f"Valid time range:\n"
                    f"Start: {start_str}\n"
                    f"End: {end_str}"
                )
                print("on_analyse_clicked: Invalid time range or scale_seconds.")
                return None

            # 检查是否选择了通道
            selected_channels = self.channel_selector.get_selected_channels()
            if not selected_channels:
                QMessageBox.warning(self.win, "No Channel Selected", "Please select at least one channel!")
                print("on_analyse_clicked: No channel selected.")
                return None
            # 检查是否选择了频段
            selected_frequencies = self.frequency_selector.get_selected_frequencies()

            # 检查频率交叉（现在只返回一个布尔值）
            if self.check_frequency_overlap(selected_frequencies):
                QMessageBox.warning(
                    self.win,
                    "Frequency band overlap",
                    "One or more overlaps exist among the selected frequency bands！"
                )
                return  # 存在交叉，阻止分析

            # 获取window大小
            window_size = float(self.edit_windoe_size.text())

            # 获取frequency
            if float(self.min_edit.text()) >= float(self.max_edit.text()):
                QLLogging.log.error("Invalid frequency range.")
                QMessageBox.warning(self.win, "Invalid frequency range",
                                    "Low frequency must be less than high frequency.")
                return None

            selected_channels = self.channel_selector.get_selected_channels()

            # 获取trend_window_sec的值
            trend_window_sec = int(self.edit_trend_window_sec.text())

            # 验证输入是否为有效整数
            self.viewer.trend_window_sec = trend_window_sec  # 同步到viewer

            # 按钮禁用掉
            self.disable_buttons()

            # 在这里添加分析逻辑
            self.display_area.hide()
            self.viewer.hide()
            self.progressBar_widget.show()
            self.progressBar.resetValue()

            self.nav_buttons_widget.set_current_page(1)
            # 更新总页数
            start, end = self.time_selector.get_time_range()
            self.total_duration = end.toSecsSinceEpoch() - start.toSecsSinceEpoch()
            if self.total_duration < 0:
                self.total_duration = 0  # 确保总时长不为负数
            self.total_pages = int(np.ceil(self.total_duration / self.scale_seconds))
            self.nav_buttons_widget.set_total_pages(self.total_pages)
            QLLogging.log.debug("basical analysis-TimeFrequency Analyse begin.")
            OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value,
                        'basical analysis-TimeFrequency Analyse begin！', 0)

            # 将时间范围转换为秒
            # 调用 calculate_bandpower 时传入时间范围
            time_range = self.time_selector.get_time_range()
            self.viewer.start_time, self.viewer.end_time = time_range
            self.viewer.set_para(window_size, selected_frequencies, float(self.min_edit.text()),
                                 float(self.max_edit.text()))

            self.worker = TimeFrequencyWorker(
                self.raw,  ##原始数据
                window_size,
                selected_channels,
                float(self.min_edit.text()),
                float(self.max_edit.text()),
                selected_frequencies,
                time_range,
                trend_window_sec=trend_window_sec
            )

            # 连接信号
            self.worker.result_ready.connect(self.on_worker_result_ready)  # 连接结果信号
            self.worker.progress.connect(self.on_worker_progress)  # 可选：连接进度信号
            self.worker.error.connect(self.on_worker_error)  # 可选：连接错误信号

            self.worker.start()

            return True

        except Exception as e:
            stack_trace = traceback.format_exc()
            # 记录详细的错误信息
            QLLogging.log.error(
                f"{self.class_name} on_analyse_clicked failed:: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )

            QMessageBox.critical(self.win, "Analysis failed", f"Analysis failed: {str(e)}")
            # 恢复分析按钮
            self.analyse_btn.blockSignals(False)
            self.analyse_btn.setEnabled(True)


class SaveWorker(QObject):
    finished = pyqtSignal(int)
    progress = pyqtSignal(int, str)  # 进度值和消息

    # page_progress = pyqtSignal(int, int)  # 新增：当前页码，总页数

    def __init__(self, viewer, result_path, formatted_time, img_format, dpi, max_value):
        super().__init__()
        self.viewer = viewer
        self.result_path = result_path
        self.formatted_time = formatted_time
        self.img_format = img_format
        self.dpi = dpi
        self.max_value = max_value
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            total_channels = len(self.viewer.result)
            current_channel = 0
            overall_progress = 0
            # 计算页面时间范围
            for channel, data in self.viewer.result.items():
                page_start_time = (self.viewer.current_page - 1) * self.viewer.page_duration
                page_end_time = page_start_time + self.viewer.page_duration
                if self._is_cancelled:
                    break

                current_channel += 1
                # 1. 处理频谱图
                tf_result_path = os.path.join(
                    self.result_path,
                    f'{channel}_time_frequency{self.formatted_time}.{self.img_format}'
                )
                self.viewer.save_Frequencywidget(
                    channel,
                    data["frequencies"],
                    data["times"],
                    data["spectrogram"],
                    tf_result_path,
                    self.dpi,
                    self.img_format,
                    start_time=page_start_time,
                    end_time=page_end_time

                )
                overall_progress += 1
                self.progress.emit(overall_progress, f"{overall_progress}/{self.max_value}")

                if self._is_cancelled:
                    break

                # 2. 保存窗口分析图
                need_add = save_window_analysis_plots(
                    data["frequencies"],
                    data["times"],
                    data["spectrogram"],
                    channel,
                    self.viewer.EEG_BANDS,
                    self.result_path,
                    savetime=self.formatted_time,
                    img_format=self.img_format,
                    dpi=self.dpi,
                    trend_window_sec=self.viewer.trend_window_sec,
                    start_time=page_start_time,
                    end_time=page_end_time,
                    cancel_flag=lambda: self._is_cancelled  # 传递取消检查函数
                )
                # overall_progress += len(self.viewer.EEG_BANDS)
                overall_progress += need_add
                self.progress.emit(overall_progress, f"{overall_progress}/{self.max_value}")

                if not self._is_cancelled:
                    # 为每个通道保存波形图
                    self.viewer.save_waveform_offscreen(
                        channel_name=channel,
                        start_time=page_start_time,
                        end_time=page_end_time,
                        save_dir=self.result_path,
                        filename=f"Waveform_{channel}_{self.formatted_time}.{self.img_format}",
                        dpi=self.dpi,
                        img_format=self.img_format
                    )
                    overall_progress += 1
                    self.progress.emit(overall_progress, f"{overall_progress}/{self.max_value}")

        except Exception as e:
            self.progress.emit(-1, f"Error during save: {str(e)}")
        finally:
            self.finished.emit(overall_progress)
