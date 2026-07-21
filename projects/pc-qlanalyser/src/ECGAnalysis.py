from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QProgressBar, QApplication,
    QLineEdit, QInputDialog, QComboBox, QSpacerItem, QSizePolicy, QMessageBox, QListView, QToolButton, QDialog,
    QMenu, QAction, QDateTimeEdit, QDialogButtonBox, QTimeEdit, QProgressDialog, QRubberBand
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QDateTime, QPropertyAnimation, QTime, QObject, QRect, \
    QCoreApplication, QEvent, QSize, QPoint
from PyQt5.uic.properties import QtWidgets, QtCore

from .DataSelect import Ui_Data_Select
from .Infrastructure.log.QLLogging import QLLogging
from .CustomControls import StyledCheckboxWidget, TimeRangeSelector,IconWithTextWidget,TimeSliderWidget,FrequencyCheckboxWidget,NavButtonsWidget,PropertyWidget
from .Control_Style import ControlStyle
import datetime
import traceback
import os.path
import warnings
warnings.filterwarnings("ignore")
import AR_neurokit2 as nk
from .SavePicCPM import  SaveDataDialog, SavePictureDialog
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from scipy import signal
import os
import time
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pyqtgraph as pg
from .utils import setup_short_cut,probe_pg,highlight_heart_rate_menu,_highlight_current_amplitude
from src.Infrastructure.QLWidgets.QLGifProgressBar import GifProgressBar
from src.Infrastructure.DB.SQLLiteAccessor import SQLLiteDB_Only_MainTread
from src.Domain.OPLog.OPLog  import OPLogTask, OPType, OPLog
from .CustomControls import CollapsibleSidebar
from .left_time_overlay import LeftTimeOverlay

def find_channel_index(ch_names, channel_name_to_find):
    """
    在给定的通道名称列表中查找通道的索引。

    参数:
    - ch_names (list): 通道名称的列表。
    - channel_name_to_find (str): 要查找的通道名称。

    返回:
    - int: 通道的索引，如果找不到则返回-1。
    """
    try:
        return ch_names.index(channel_name_to_find)
    except ValueError:
        print(f"Channel name '{channel_name_to_find}' not found.")
        return -1

def bandpass_filter(signal, sampling_rate, lowcut=8, highcut=40, order=4):
    from scipy.signal import butter, filtfilt
    nyquist = 0.5 * sampling_rate
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, signal)

def _ecg_debug(message):
    """统一输出 ECG 调试信息，便于在控制台和日志中追踪输入数据。"""
    text = f"[ECGAnalysis DEBUG] {message}"
    print(text)
    try:
        QLLogging.log.info(text)
    except Exception:
        pass

def _ecg_warning(message):
    """统一输出 ECG 警告信息，避免某个片段失败导致整个软件崩溃。"""
    text = f"[ECGAnalysis WARNING] {message}"
    print(text)
    try:
        QLLogging.log.warning(text)
    except Exception:
        try:
            QLLogging.log.info(text)
        except Exception:
            pass

def _summarize_signal(name, values):
    """生成一维信号的基础统计，重点检查 NaN、Inf、常数和全零。"""
    array = np.asarray(values).squeeze()
    flat = array.reshape(-1) if array.size else array
    finite = flat[np.isfinite(flat)] if flat.size else flat
    summary = {
        "shape": array.shape,
        "dtype": array.dtype,
        "size": int(flat.size),
        "nan_count": int(np.isnan(flat).sum()) if flat.size else 0,
        "inf_count": int(np.isinf(flat).sum()) if flat.size else 0,
        "first10": flat[:10].tolist() if flat.size else [],
    }

    if finite.size:
        finite_min = float(np.min(finite))
        finite_max = float(np.max(finite))
        finite_mean = float(np.mean(finite))
        finite_std = float(np.std(finite))
        summary.update({
            "min": finite_min,
            "max": finite_max,
            "mean": finite_mean,
            "std": finite_std,
            "all_zero": bool(np.allclose(finite, 0.0)),
            "constant": bool(np.allclose(finite, finite[0])),
        })
    else:
        summary.update({
            "min": None,
            "max": None,
            "mean": None,
            "std": None,
            "all_zero": False,
            "constant": False,
        })

    _ecg_debug(f"{name}: {summary}")
    return summary

def _is_invalid_ecg_segment(segment, sampling_rate, segment_no, start, end_idx, warnings_list):
    """在调用 nk.ecg_peaks 前拦截明显无效的片段。"""
    summary = _summarize_signal(
        f"segment[{segment_no}] before nk.ecg_peaks samples={start}:{end_idx}",
        segment,
    )
    min_segment_samples = max(int(float(sampling_rate) * 2), 3)
    reason = None

    if summary["size"] == 0:
        reason = "segment 为空"
    elif summary["size"] < min_segment_samples:
        reason = f"segment 太短，长度 {summary['size']} < {min_segment_samples}"
    elif summary["nan_count"] > 0 or summary["inf_count"] > 0:
        reason = f"segment 包含 NaN/Inf，NaN={summary['nan_count']} Inf={summary['inf_count']}"
    elif summary["std"] is None:
        reason = "segment 没有有限数值"
    elif summary["all_zero"]:
        reason = "segment 全 0"
    elif summary["constant"] or np.isclose(summary["std"], 0.0):
        reason = f"segment 为常数或近似常数，std={summary['std']}"

    if reason:
        message = f"跳过第 {segment_no} 段 ECG：{reason}"
        warnings_list.append(message)
        _ecg_warning(message)
        return True

    return False

def process_ecg_data(raw, selected_channel, time_range, progress_callback=None):
    """
    处理ECG数据并返回计算结果

    Parameters:
    -----------
    raw : mne.io.Raw
        原始数据
    selected_channel : str
        选中的通道名
    progress_callback : callable, optional
        进度回调函数(current_step, total_steps)

    Returns:
    --------
    dict : 包含处理结果的字典
    """
    total_steps = 10  # 总步骤数
    current_step = 0
    warnings_list = []
    failed_segments = []

    if raw is None:
        raise ValueError("ECG analysis input raw is None.")

    # 先记录 Raw 的轻量元信息，不主动加载完整数据，避免大文件额外占用内存。
    raw_n_channels = len(getattr(raw, "ch_names", []))
    raw_n_times = int(getattr(raw, "n_times", len(getattr(raw, "times", []))))
    raw_dtype = "unknown"
    try:
        if raw_n_channels > 0 and raw_n_times > 0:
            raw_dtype = raw.get_data(start=0, stop=1).dtype
    except Exception as e:
        raw_dtype = f"unavailable: {e}"

    _ecg_debug(
        f"process_ecg_data start raw_shape=({raw_n_channels}, {raw_n_times}) "
        f"raw_dtype={raw_dtype} raw_empty={raw_n_channels == 0 or raw_n_times == 0} "
        f"selected_channel={selected_channel} time_range={time_range}"
    )

    if raw_n_channels == 0 or raw_n_times == 0:
        raise ValueError(f"ECG analysis raw is empty: shape=({raw_n_channels}, {raw_n_times}).")

    sampling_rate = float(raw.info['sfreq'])
    _ecg_debug(f"sampling_rate={sampling_rate}")
    if not np.isfinite(sampling_rate) or sampling_rate <= 0:
        raise ValueError(f"Invalid sampling_rate for ECG analysis: {sampling_rate}.")
    if sampling_rate <= 90:
        raise ValueError(
            f"Sampling rate {sampling_rate}Hz is too low for ECG bandpass 10-45Hz; "
            "please check the input file or choose a higher-rate ECG channel."
        )

    if time_range:
        from datetime import timezone
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
        if meas_date is None:
            raise ValueError("Invalid ECG time range: raw.info['meas_date'] is None.")

        # 确保时间格式一致
        start_time = start_time.replace(tzinfo=timezone.utc)
        end_time = end_time.replace(tzinfo=timezone.utc)
        meas_date = meas_date.replace(tzinfo=timezone.utc)

        # 计算起始和结束索引
        start_idx = int(((start_time - meas_date).total_seconds()) * sampling_rate)
        end_idx = int(((end_time - meas_date).total_seconds()) * sampling_rate)+int(sampling_rate)
        _ecg_debug(
            f"time_range converted start={start_time} end={end_time} meas_date={meas_date} "
            f"start_idx={start_idx} end_idx={end_idx} raw_n_times={len(raw.times)}"
        )
        # 添加边界检查
        if end_idx >= len(raw.times):
            end_idx = len(raw.times)-1
        if start_idx < 0 or end_idx < 0:
            raise ValueError(
                f"Invalid ECG time range: start_idx={start_idx}, end_idx={end_idx}, raw_n_times={len(raw.times)}."
            )

        if end_idx <= start_idx:
            raise ValueError("Invalid time range: end time must be greater than start time.")

        # 裁剪数据
        raw = raw.copy().crop(tmin=start_idx / sampling_rate, tmax=end_idx / sampling_rate)
        _ecg_debug(f"cropped raw shape=({len(raw.ch_names)}, {raw.n_times})")

    # 1. 提取数据
    index = find_channel_index(raw.ch_names,selected_channel)
    _ecg_debug(f"selected_channel={selected_channel} channel_index={index} available_channels={raw.ch_names}")
    if index < 0 or index >= len(raw.ch_names):
        raise ValueError(
            f"Selected ECG channel '{selected_channel}' is not available. "
            f"Available channels: {raw.ch_names}"
        )

    ecg_signal, _ = raw[index, :]
    ecg_signal = ecg_signal.squeeze()
    ecg_signal_summary = _summarize_signal("selected raw ECG channel before filter", ecg_signal)
    if ecg_signal_summary["size"] == 0:
        raise ValueError("Selected ECG channel is empty after time crop.")
    if ecg_signal_summary["nan_count"] > 0 or ecg_signal_summary["inf_count"] > 0:
        raise ValueError(
            "Selected ECG channel contains NaN/Inf before filtering: "
            f"NaN={ecg_signal_summary['nan_count']} Inf={ecg_signal_summary['inf_count']}."
        )
    if ecg_signal_summary["constant"] or np.isclose(ecg_signal_summary["std"], 0.0):
        raise ValueError(
            f"Selected ECG channel is constant or near-constant before filtering; std={ecg_signal_summary['std']}."
        )
    if progress_callback:
        current_step += 1
        progress_callback(current_step, total_steps)

    # 2. 信号处理
    try:
        ecg_cleaned = bandpass_filter(ecg_signal, sampling_rate, lowcut=10, highcut=45, order=2)
    except Exception as e:
        raise ValueError(f"ECG bandpass filter failed before peak detection: {e}") from e
    _summarize_signal("ECG channel after bandpass filter 10-45Hz", ecg_cleaned)

    # 分段处理以避免内存问题
    segment_length = int(sampling_rate * 100)  # 每段100s
    total_length = len(ecg_cleaned)
    r_peaks_list = []
    num_segments   = int(np.ceil(total_length / segment_length))
    seg_steps      = total_steps - 2 - 1

    if progress_callback:
        current_step += 1
        progress_callback(current_step, total_steps)

    # 逐段处理数据
    for i, start in enumerate(range(0, total_length, segment_length)):
        end_idx = min(start + segment_length, total_length)
        segment = ecg_cleaned[start:end_idx]
        segment_no = i + 1

        if _is_invalid_ecg_segment(segment, sampling_rate, segment_no, start, end_idx, warnings_list):
            failed_segments.append({
                "segment": segment_no,
                "start": int(start),
                "end": int(end_idx),
                "reason": warnings_list[-1] if warnings_list else "invalid segment",
            })
            continue

        _ecg_debug(
            f"calling nk.ecg_peaks segment={segment_no}/{num_segments} "
            f"samples={start}:{end_idx} length={len(segment)}"
        )
        try:
            _, segment_peaks = nk.ecg_peaks(segment, sampling_rate=sampling_rate, method='neurokit')
        except Exception as e:
            # 第三方 QRS 检测在无有效 QRS 起点时可能抛 IndexError；这里记录失败片段并继续后续片段。
            reason = (
                f"第 {segment_no} 段 nk.ecg_peaks 失败: {type(e).__name__}: {e}; "
                f"samples={start}:{end_idx}"
            )
            warnings_list.append(reason)
            failed_segments.append({
                "segment": segment_no,
                "start": int(start),
                "end": int(end_idx),
                "reason": reason,
            })
            _ecg_warning(reason)
            continue

        segment_r_peaks = np.asarray(segment_peaks.get('ECG_R_Peaks', []))
        _ecg_debug(f"nk.ecg_peaks finished segment={segment_no} r_peaks_count={len(segment_r_peaks)}")

        # 调整峰值索引并添加到列表
        if len(segment_r_peaks) > 0:
            adjusted_peaks = segment_r_peaks + start
            r_peaks_list.extend(adjusted_peaks)

        if progress_callback:
            step = 2 + int((i + 1) / num_segments * seg_steps)
            progress_callback(step, total_steps)

    # 3. 计算心率相关指标
    r_peaks_idx_cleaned = [x for x in r_peaks_list if not np.isnan(x)]
    r_peaks_times = np.array(r_peaks_idx_cleaned) / sampling_rate
    if len(r_peaks_idx_cleaned) == 0:
        warning = "No ECG R-peaks detected after processing all valid segments."
        warnings_list.append(warning)
        _ecg_warning(warning)
        ecg_rate = np.array([])
    elif len(r_peaks_idx_cleaned) < 2:
        warning = f"Only {len(r_peaks_idx_cleaned)} ECG R-peak detected; heart rate and RR intervals are empty."
        warnings_list.append(warning)
        _ecg_warning(warning)
        ecg_rate = np.array([])
    else:
        try:
            ecg_rate = nk.ecg_rate(r_peaks_idx_cleaned, sampling_rate=sampling_rate)
        except Exception as e:
            warning = f"nk.ecg_rate failed after peak detection: {type(e).__name__}: {e}"
            warnings_list.append(warning)
            _ecg_warning(warning)
            ecg_rate = np.array([])
    rr_intervals = np.diff(r_peaks_times)
    if progress_callback:
        current_step = total_steps
        progress_callback(current_step, total_steps)
        
    delta_rr = np.diff(rr_intervals)  # 计算Delta RR（单位：秒）
    return {
        'ecg_signal': ecg_signal,
        'ecg_cleaned': ecg_cleaned,
        'r_peaks_idx': r_peaks_idx_cleaned,
        'r_peaks_times': r_peaks_times,
        'heart_rate': ecg_rate,
        'rr_intervals': rr_intervals,
        'DeltaRR': delta_rr,
        'Peaks': {'ECG_R_Peaks': np.array(r_peaks_list)},
        'sampling_rate': sampling_rate,
        'r_peaks_list': r_peaks_list,
        'warnings': warnings_list,
        'failed_segments': failed_segments
    }


def _padded_ecg_export_column(values, target_len):
    """为 ECG 导出构造局部 padded array，避免修改 self.results 里的原始数组。"""
    array = np.asarray(values)
    if len(array) >= target_len:
        return array.copy()
    padding = np.full(target_len - len(array), np.nan)
    return np.append(array, padding)


def _build_ecg_save_data_frame(results, start_time):
    """构造 ECG save_data 导出表；只使用局部副本，不改变 results 的任何字段。"""
    columns_of_interest = ['heart_rate', 'r_peaks_times', 'rr_intervals', 'DeltaRR']

    # test_time 仍按原始 r_peaks_times 生成，保持旧导出文件内容不变。
    time_deltas = [datetime.timedelta(seconds=t) for t in results['r_peaks_times']]
    test_times = [(start_time + delta).strftime("%H:%M:%S") for delta in time_deltas]

    max_len = max(
        len(test_times),
        max(len(results[col]) for col in columns_of_interest if col in results),
    )
    export_columns = {
        col: _padded_ecg_export_column(results[col], max_len)
        for col in columns_of_interest
        if col in results
    }

    return pd.DataFrame({
        'Epoch No.': range(len(test_times)),
        'test_time': test_times,
        'heart_rate': export_columns['heart_rate'],
        'r_peaks_times': export_columns['r_peaks_times'],
        'rr_intervals': export_columns['rr_intervals'],
        'DeltaRR': export_columns['DeltaRR']
    })[['Epoch No.', 'test_time', 'heart_rate', 'r_peaks_times', 'rr_intervals', 'DeltaRR']]


class ECGAnalysisWorker(QThread):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, raw, channel, time_range = None,result_path= None):
        super().__init__()
        self.raw = raw
        self.channel = channel
        self.result_path = result_path
        self.time_range = time_range

    def run(self):
        try:
            # 定义进度回调函数
            def progress_callback(step, total_steps):
                progress = int((step / total_steps) * 100)
                self.progress.emit(progress)

            # 计算结果
            results = process_ecg_data(self.raw, self.channel, self.time_range, progress_callback)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

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
                curr_time = self.meas_date + datetime.timedelta(seconds=v)
                # 根据缩放级别自动调整显示精度
                if spacing < 1:
                    strings.append(curr_time.strftime('%H:%M:%S.%f')[:-3])
                else:
                    strings.append(curr_time.strftime('%H:%M:%S'))
            except Exception:
                strings.append("")
        return strings

class Ui_ECG_compute(QWidget):
    page_changed = pyqtSignal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.raw = None
        self.page_duration = 5
        self.current_page = 1
        self.total_pages = 60
        self.total_duration = 300
        self.time_range = None
        self.manual_y_range = None  # 初始使用自动幅度范围 y轴
        self.setupUi()
        self.win = None
        self.is_heart_auto=True

        self.scale_map = {
            50: 10,
            100: 25,
            200: 50,
            500: 100,
            1000: 200,
            2000: 500,
            3000: 500, 
            4000: 1000,
            5000: 1000
        }
        self.is_manually_changing_page = False # 标记是否手动更改页码

        # 使用自定义坐标轴初始化 ecg_widget
        self.ecg_time_axis = RelativeTimeAxis(orientation='bottom')
        self.ecg_time_axis.setPen(None)
        self.ecg_time_axis.setTextPen(pg.mkPen('k'))

        # 将 axisItems 传入 PlotWidget
        self.ecg_widget = pg.PlotWidget(axisItems={'bottom': self.ecg_time_axis})

        self.ecg_widget.setBackground('w')
        # 设置坐标轴字体颜色为深色
        self.ecg_widget.getAxis('bottom').setPen(pg.mkPen(color='k', width=1))  # 黑色x轴标签
        self.ecg_widget.getAxis('left').setPen(pg.mkPen(color='k', width=1))  # 黑色y轴标签

        # 设置边距：左、底部、右、顶部
        self.ecg_widget.getPlotItem().setContentsMargins(45, 0, 30, 0)
        self.ecg_widget.setLabel('left', 'Amplitude(μV)')
        self.ecg_widget.setTitle('ECG Signal with R Peaks', color='k')
        # 隐藏 x 轴和 y 轴线，但保留刻度标签
        self.ecg_widget.getAxis('bottom').setPen(None)
        self.ecg_widget.getAxis('left').setPen(None)
        self.ecg_widget.getAxis('left').setTextPen(pg.mkPen(color='k'))
        self.ecg_widget.getAxis('bottom').setTextPen(pg.mkPen('k'))

        self.ecg_widget.setMouseEnabled(x=True, y=False)  # 禁用缩放/平移
        self.ecg_widget.setMenuEnabled(False)  # 关右键菜单，避免误触
        self.ecg_widget.getPlotItem().hideButtons()  # 隐藏左上角的“A”按钮
        self.ecg_widget.setMenuEnabled(False)  # 禁用右键菜单
        self.ecg_widget.setMinimumHeight(300)  # 设置最小高度
        self.main_layout.addWidget(self.ecg_widget)
        self.ecg_left_text = LeftTimeOverlay(
            self.ecg_widget,
            anchor_parent=self.ecg_widget,
            corner='bottom-left', offset=(16, 0),
            meas_date=None,  # 先不设，稍后在 scroll_time 里赋值
            dt_fmt='%Y-%m-%d %H:%M:%S',  # 含日期
            show_ms=True  # 显示毫秒
        )

        self.figure = Figure()  # 不需要指定固定的figsize
        self.canvas = FigureCanvas(self.figure)
        # 设置画布的尺寸策略为扩展
        self.canvas.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        # 设置最小尺寸以防止过度缩小
        self.canvas.setMinimumSize(400, 300)
        self.main_layout.addWidget(self.canvas)

        # 添加时间滚动条
        self.slider_widget = TimeSliderWidget()
        self.main_layout.addWidget(self.slider_widget)
        self.visible_window = 10  # 可视窗口，比如只显示10秒
        self.slider_widget.time_slider.setMinimum(0)
        self.slider_widget.time_slider.setValue(0)
        self.slider_widget.time_slider.valueChanged.connect(self.scroll_time)
        # 在设置最大值之前先计算确保非负
        max_value = max(0, int(self.total_duration - self.page_duration))
        self.slider_widget.time_slider.setMaximum(max_value)

        self.ecg_results = None
        self.vlines = []
        self._scroll_time_cache_key = None
        self._cached_x_time = None
        self._cached_r_peaks_times = None

        # 框选 RubberBand 与高亮所需的状态
        self._ecg_rb = None
        self._ecg_rb_origin = None
        self._ecg_rb_host = self.ecg_widget.viewport()
        self._ecg_rb_active = False  # <— 新增：是否正在框选
        self._ecg_min_px = 8  # <— 新增：最小像素宽度（小于则忽略）
        self._ecg_min_sec = 0.02  # <— 新增：最小秒宽（小于则忽略）
        self._ecg_regions = []  # 保存所有高亮 LinearRegionItem
        self._ecg_zoom_windows = []  # 保存所有非模态放大窗
        self._ecg_dialog_region = {}  # dialog -> region
        self._ecg_hl_pen = pg.mkPen(100, 149, 237, 180, width=1)  # #6495ED
        self._ecg_hl_brush = pg.mkBrush(100, 149, 237, 60)

        self._zoom_viewports = set()
        self._zoom_viewport_map = {}

        # 仅给 ECG 这张图安装事件过滤器（其它图不受影响）
        self.ecg_widget.viewport().installEventFilter(self)

    def setupUi(self):
        # 创建主布局
        self.main_layout = QVBoxLayout(self)

        # self.amplitude_label = QLabel("Amplitude(mG)")
        # self.amplitude_label.setStyleSheet(ControlStyle.get_label_wordSmall_style())

        # 创建主工具按钮
        self.toolButton_amplitude_set = QToolButton(self)
        self.toolButton_amplitude_set.setText("Amplitude setting")
        self.toolButton_amplitude_set.setMinimumSize(190, 32)
        self.toolButton_amplitude_set.setPopupMode(QToolButton.InstantPopup)
        # self.toolButton_amplitude_set.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        self.toolButton_amplitude_set.setStyleSheet(ControlStyle.get_toolbutton_style())
        ControlStyle.get_font_size(self.toolButton_amplitude_set, 10)

        # 创建主下拉菜单
        main_menu = QMenu()
        main_menu.setMinimumSize(160, 32)
        main_menu.setStyleSheet(ControlStyle.get_menuBar_style())
        ControlStyle.get_font_size(main_menu, 10)

        # 创建一级菜单（Amplitude(uV)，Heart Rate(BPM)）
        # menu_eeg = QMenu("EEG Amplitude (μv) ", self)
        self.menu_amplitude = QMenu()
        self.menu_amplitude.setTitle("Amplitude(uV) ")
        self.menu_heart_rate = QMenu()
        self.menu_heart_rate.setTitle("Heart Rate(BPM)")

        self.menu_amplitude.setStyleSheet(ControlStyle.get_menuBar_style())
        self.menu_heart_rate.setStyleSheet(ControlStyle.get_menuBar_style())

        ControlStyle.get_font_size(self.menu_amplitude, 10)
        ControlStyle.get_font_size(self.menu_heart_rate, 10)

        # 将一级菜单添加到菜单栏中
        main_menu.addMenu(self.menu_amplitude)
        main_menu.addMenu(self.menu_heart_rate)

        self.toolButton_amplitude_set.setMenu(main_menu)

        # Amplitude(uV) 下拉菜单选项
        values = ["Auto", "±100", "±200", "±500", "±1000"]
        for value in values:
            action = QAction(value, self)
            ControlStyle.get_font_size(action, 10)
            self.menu_amplitude.addAction(action)
            action.triggered.connect(
                lambda checked, val=value: self.on_amplitude_changed(val)
            )

        # Heart Rate(BPM) 下拉菜单选项
        values = ["Auto", "±100", "±200", "±500", "±1000"]
        for value in values:
            action = QAction(value, self)
            ControlStyle.get_font_size(action, 10)
            self.menu_heart_rate.addAction(action)
            action.triggered.connect(
                lambda checked, val=value: self.on_heart_rate_changed(val)
            )

        self.menu_amplitude.aboutToShow.connect(
            lambda: _highlight_current_amplitude(
                self.menu_amplitude,
                lambda: probe_pg(self.ecg_widget)
            )
        )

        # Heart Rate(BPM)（Matplotlib）
        self.menu_heart_rate.aboutToShow.connect(
            lambda: highlight_heart_rate_menu(
                self.menu_heart_rate,
                fig=self.figure,  # 或者 ax=self.figure.get_axes()[0]
                is_auto=self.is_heart_auto)
        )


        control_layout = QHBoxLayout()
        control_layout.addStretch()
        control_layout.addWidget(self.toolButton_amplitude_set)
        # control_layout.addWidget(self.amplitude_label)
        # control_layout.addWidget(self.amplitude_selector)
        # 添加一个固定大小的空白区域
        spacer_fixed = QSpacerItem(20, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        control_layout.addSpacerItem(spacer_fixed)
        self.main_layout.addLayout(control_layout)

        self.setLayout(self.main_layout)

    def plot_ecg_results(self, results, sfreq):
        """
        在self.figure上绘制ECG分析结果

        Parameters:
        -----------
        results : dict
            process_ecg_data函数返回的结果字典
        """
        self.ecg_results = results
        self.sfreq = sfreq
        self._invalidate_scroll_time_cache()
        self.figure.clear()
        self.ecg_widget.clear()

        # 创建子图
        gs = self.figure.add_gridspec(2, 1, height_ratios=[0.5, 1.5])
        ax = self.figure.add_subplot(gs[1])


        # 调整画布的尺寸以适应所有子图
        self.figure.subplots_adjust(left=0.02, right=0.98, bottom=0, top=1)

        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(axis='both', which='both', length=0)

        # 绘制ECG信号和R峰
        self.ecg_plot = self.ecg_widget.plot(pen=pg.mkPen('r', width=0.7), name="ECG Signal")

        time_in_minutes = results['r_peaks_times']

        ax.plot(time_in_minutes[:-1], results['heart_rate'][:-1], 'g', linewidth=0.5, color='black')
        ax.set_xlabel('Time (seconds)')
        ax.set_ylabel('Heart Rate (BPM)')
        ax.set_title('Heart Rate over Time')
        ax.grid(True)
        # 调整布局并更新画布
        self.figure.tight_layout()
        # 调整布局
        self.figure.subplots_adjust(
            left=0.07,  # 左边距
            right=0.97,  # 右边距
            bottom=0.2,  # 底部边距
            top=0.95,  # 顶部边距
            hspace=0.4  # 子图之间的垂直间距
        )

        self.scroll_time()

    def _invalidate_scroll_time_cache(self):
        """清空 scroll_time 派生数组缓存，确保新输入不会复用旧时间轴。"""
        self._scroll_time_cache_key = None
        self._cached_x_time = None
        self._cached_r_peaks_times = None

    def _time_range_cache_signature(self):
        """生成 time_range 的稳定签名，用于判断当前页面时间基准是否变化。"""
        if not self.time_range:
            return None

        def _time_value(value):
            if hasattr(value, 'toMSecsSinceEpoch'):
                return int(value.toMSecsSinceEpoch())
            if hasattr(value, 'toSecsSinceEpoch'):
                return int(value.toSecsSinceEpoch()) * 1000
            if hasattr(value, 'timestamp'):
                return int(value.timestamp() * 1000)
            return id(value)

        try:
            start, end = self.time_range
            return (_time_value(start), _time_value(end))
        except Exception:
            return id(self.time_range)

    def _array_cache_signature(self, values):
        """低成本描述 ECG/R peak 输入；避免每次滚动为 key 重新复制数组。"""
        if values is None:
            return None

        try:
            length = len(values)
        except Exception:
            length = None

        shape = getattr(values, 'shape', None)
        dtype = str(getattr(values, 'dtype', ''))
        data_pointer = None
        try:
            data_pointer = values.__array_interface__['data'][0]
        except Exception:
            pass

        first_value = None
        last_value = None
        if length:
            try:
                first_value = float(values[0])
                last_value = float(values[-1])
            except Exception:
                first_value = id(values[0])
                last_value = id(values[-1])

        return (id(values), shape, dtype, data_pointer, length, first_value, last_value)

    def _make_scroll_time_cache_key(self):
        """缓存 key 同时绑定 ECG signal、采样率、time_range 和 R peak 输入。"""
        results = self.ecg_results or {}
        return (
            id(results),
            self._array_cache_signature(results.get('ecg_signal')),
            float(self.sfreq),
            self._time_range_cache_signature(),
            self._array_cache_signature(results.get('r_peaks_idx')),
        )

    def _get_scroll_time_arrays(self):
        """返回 scroll_time 使用的时间轴数组；输入签名变化时自动重建。"""
        cache_key = self._make_scroll_time_cache_key()
        if cache_key != self._scroll_time_cache_key or self._cached_x_time is None or self._cached_r_peaks_times is None:
            ecg_signal = self.ecg_results['ecg_signal']
            # x_time 只由当前 ECG 长度和采样率决定，滚动位置变化不需要重建。
            self._cached_x_time = np.arange(len(ecg_signal)) / self.sfreq
            # R peak 竖线位置只由当前峰索引和采样率决定，翻页时复用同一秒轴。
            self._cached_r_peaks_times = np.asarray(self.ecg_results['r_peaks_idx']) / self.sfreq
            self._scroll_time_cache_key = cache_key
        return self._cached_x_time, self._cached_r_peaks_times

    def scroll_time(self):

        # 获取时间范围的起始时间
        start, end = self.time_range
        # 将 start 转换为 Unix 时间戳
        start_timestamp = start.toSecsSinceEpoch()
        if hasattr(self, 'ecg_left_text'):
            base_dt = start.toPyDateTime()  # 当前界面的绝对基准时间
            self.ecg_left_text.set_meas_date(base_dt)  # 之后随 XRange 变化自动刷新
        # 将基准时间传给自定义坐标轴
        if hasattr(self, 'ecg_time_axis'):
            self.ecg_time_axis.set_meas_date(start.toPyDateTime())

        # 获取当前滚动条位置并加上起始时间
        pos = self.slider_widget.time_slider.value()
        start_time = max(0, pos)
        end_time = start_time + self.page_duration

        # 确保不超出数据总范围
        total_duration = int(len(self.ecg_results['ecg_signal']) / self.sfreq)
        # 处理时间范围小于页面持续时间的情况
        if total_duration <= self.page_duration:
            start_time = 0
            end_time = total_duration - 1
            # 禁用滚动条
            self.slider_widget.time_slider.setEnabled(False)
        else:
            # 更新滚动条位置
            self.slider_widget.time_slider.setValue(int(start_time))
            # 启用滚动条
            self.slider_widget.time_slider.setEnabled(True)

        # 更新当前页码
        if not self.is_manually_changing_page:
            # self.current_page = int(start_time / self.page_duration) + 1
            self.get_current_page()
            self.page_changed.emit(self.current_page)

        # # 创建4个均匀分布的时间点
        # time_ticks = np.linspace(start_time, end_time, end_time-start_time+1)
        # time_strings = []
        #
        # # 将秒数转换为时分秒格式
        # for seconds in time_ticks:
        #     # 计算实际时间戳
        #     actual_timestamp = start_timestamp + int(seconds)
        #     # 转换为 QDateTime
        #     actual_time = QDateTime.fromSecsSinceEpoch(actual_timestamp)
        #     # 格式化为时间字符串
        #     time_str = actual_time.toString('HH:mm:ss')
        #     time_strings.append(time_str)
        #
        # axis = self.ecg_widget.getAxis('bottom')
        # ticks = [(time_ticks[i], time_strings[i]) for i in range(len(time_ticks))]
        # axis.setTicks([ticks])
        self.ecg_widget.getAxis('bottom').setTicks(None)
        axis = self.ecg_widget.getAxis('bottom')
        axis.setHeight(50)  # 关键：给底轴一个稳定高度
        axis.setStyle(tickTextOffset=12)  # 可以比 10 稍大点，避免压线

        # 设置ECG widget的x轴范围（基于实际数据范围）
        self.ecg_widget.setXRange(start_time, end_time, padding=0)

        # 更新所有子图的显示范围和刻度
        axs = self.figure.get_axes()
        for ax in axs:
            # 设置显示范围
            ax.set_xlim(start_time, end_time)

        if self.is_heart_auto:
            self.on_heart_rate_changed("Auto")
        else:
            # 重绘图形
            self.canvas.draw()

        # 更新ECG信号显示
        x_time, r_peaks_times = self._get_scroll_time_arrays()
        time_mask = (x_time >= start_time) & (x_time <= end_time)
        self.ecg_plot.setData(x_time[time_mask], self.ecg_results['ecg_signal'][time_mask])
        self._apply_ecg_page_guardrails(start_time, end_time)

        # 清除旧竖线
        for line in self.vlines:
            self.ecg_widget.removeItem(line)
        self.vlines.clear()

        for x in r_peaks_times:
            if start_time <= x <= end_time:
                vline = pg.InfiniteLine(
                    pos=x, angle=90,
                    pen=pg.mkPen('k', style=Qt.PenStyle.DashLine, width=0.7)
                )
                self.ecg_widget.addItem(vline)
                self.vlines.append(vline)
    def eventFilter(self, obj, event):
        # ECG 放大弹窗里的 Ctrl+滚轮：只缩放 Y 轴
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

                # 【关键】返回 False，让 PyQtGraph 接收事件并执行默认的缩放/平移逻辑
                return False

            # 非 Ctrl+滚轮（包括普通滚轮）交给默认处理（pyqtgraph 用 x=True,y=False 缩 X 轴）
            return super().eventFilter(obj, event)
        if obj is not self.ecg_widget.viewport():
            return super().eventFilter(obj, event)

        # 1) Shift + 左键按下：开始框选
        if (event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton
                and (event.modifiers() & Qt.ShiftModifier)):
            self._ecg_rb_active = True
            self._ecg_rb_origin = event.pos()
            if self._ecg_rb is None:
                self._ecg_rb = QRubberBand(QRubberBand.Rectangle, self._ecg_rb_host)
            self._ecg_rb.setGeometry(QRect(self._ecg_rb_origin, QSize()))
            self._ecg_rb.show()
            return True  # 截断事件，避免传递

        # 2) 拖动时更新选框（仅在“框选进行中”）
        if (event.type() == QEvent.MouseMove
                and self._ecg_rb_active
                and self._ecg_rb is not None
                and self._ecg_rb.isVisible()):
            rect = QRect(self._ecg_rb_origin, event.pos()).normalized()
            self._ecg_rb.setGeometry(rect)
            return True

        # 3) 左键松开：结束框选（仅在“框选进行中”）
        if (event.type() == QEvent.MouseButtonRelease
                and event.button() == Qt.LeftButton):
            if not (self._ecg_rb_active and self._ecg_rb and self._ecg_rb.isVisible()):
                # 不是框选态的普通点击：不处理，防止误高亮/误弹窗
                return False

            # 结束框选
            sel_rect = self._ecg_rb.geometry()
            self._ecg_rb.hide()
            self._ecg_rb_active = False

            # 3.1 像素宽度阈值（避免单击或极窄框触发）
            if sel_rect.width() < self._ecg_min_px:
                return True

            # 3.2 像素 -> 数据坐标（只在本 ECG 图上）
            def vp_x_to_data_x(px):
                scene_pt = self.ecg_widget.mapToScene(QPoint(px, sel_rect.center().y()))
                data_pt = self.ecg_widget.getPlotItem().vb.mapSceneToView(scene_pt)
                return data_pt.x()

            x_min = vp_x_to_data_x(sel_rect.left())
            x_max = vp_x_to_data_x(sel_rect.right())
            if x_min > x_max:
                x_min, x_max = x_max, x_min

            vb = self.ecg_widget.getPlotItem().vb
            vis_x0, vis_x1 = vb.viewRange()[0]
            x_min = max(vis_x0, min(x_min, vis_x1))
            x_max = max(vis_x0, min(x_max, vis_x1))

            # 3.3 时间宽度阈值（避免极窄窗）
            if (x_max - x_min) < self._ecg_min_sec:
                return True

            # 仅在 ECG 原图上高亮，并弹出只含 ECG 的放大窗
            region = pg.LinearRegionItem(values=(x_min, x_max),
                                         brush=self._ecg_hl_brush,
                                         pen=self._ecg_hl_pen,
                                         movable=False)
            self.ecg_widget.addItem(region)
            self._ecg_regions.append(region)
            self._show_ecg_zoom_dialog(x_min, x_max, region)
            return True

        return super().eventFilter(obj, event)

    def _apply_ecg_page_guardrails(self, page_start: float, page_end: float):
        """把 ECG ViewBox 的护栏限制到【当前页窗口】内"""
        try:
            if page_end <= page_start:
                return
            vb = self.ecg_widget.getPlotItem().vb
            # 给一点极小余量，避免浮点边界导致的“卡边”（可按需调小/去掉）
            eps = 1e-6
            vb.setLimits(
                xMin=page_start - eps,
                xMax=page_end + eps,
                minXRange=min(0.2, max(0.01, (page_end - page_start) * 0.1)),  # 最小可缩到当前页宽度的 10%，上限 0.2s
                maxXRange=(page_end - page_start)  # 最大不能超过一整页
            )
            # 将视窗也切回这一页（防止仍停留在上一页的范围）
            self.ecg_widget.setXRange(page_start, page_end, padding=0)
        except Exception:
            pass


    def _show_ecg_zoom_dialog(self, x_min: float, x_max: float, region: pg.LinearRegionItem):
        """弹出只包含 ECG 的非模态放大窗；关闭后移除对应高亮"""
        dialog = QDialog(self)
        meas_date = self.time_range[0].toPyDateTime()
        sec_start = round(float(x_min), 3)
        sec_end = round(float(x_max), 3)
        ms_start = int(round(sec_start * 1000))
        ms_end = int(round(sec_end * 1000))
        abs_start = meas_date + datetime.timedelta(milliseconds=ms_start)
        abs_end = meas_date + datetime.timedelta(milliseconds=ms_end)
        start_str = abs_start.strftime("%Y-%m-%d %H:%M:%S") + f".{ms_start % 1000:03d}"
        end_str = abs_end.strftime("%Y-%m-%d %H:%M:%S") + f".{ms_end % 1000:03d}"
        dialog.setWindowTitle(f"ECG  [{start_str}  ~  {end_str}]")
        layout = QVBoxLayout(dialog)
        from .left_time_overlay import DateAxis
        date_axis = DateAxis(meas_date, orientation='bottom')
        zoom_plot = pg.PlotWidget(axisItems={'bottom': date_axis})
        layout.addWidget(zoom_plot)
        dialog.resize(900, 320)

        # 复制框选区域的 ECG 数据
        x_time = np.arange(len(self.ecg_results['ecg_signal'])) / self.sfreq
        time_mask = (x_time >= x_min) & (x_time <= x_max)  # 只保留框选区域内的数据
        selected_data = self.ecg_results['ecg_signal'][time_mask]  # 获取框选区域内的数据
        selected_time = x_time[time_mask]  # 获取框选区域内的时间数据

        # 绘制框选区域的 ECG 曲线
        zoom_plot.plot(selected_time, selected_data, pen=pg.mkPen('r', width=0.7), name="ECG Signal")

        zoom_plot.setBackground("w")
        zoom_plot.showGrid(x=True, y=True, alpha=0.3)
        zoom_plot.setMouseEnabled(x=True, y=False)  # 放大窗也可滚轮缩放（只限 X）
        zoom_plot.setXRange(x_min, x_max, padding=0)
        zoom_plot.setMenuEnabled(False)
        # 添加 R 峰虚线（样式与主界面保持一致）
        r_peaks_times = np.array(self.ecg_results['r_peaks_idx']) / self.sfreq
        for x in r_peaks_times:
            if x_min <= x <= x_max:
                vline = pg.InfiniteLine(
                    pos=x, angle=90,
                    pen=pg.mkPen('k', style=Qt.PenStyle.DashLine, width=0.7)
                )
                zoom_plot.addItem(vline)

        vp = zoom_plot.viewport()
        vp.installEventFilter(self)
        self._zoom_viewports.add(vp)
        self._zoom_viewport_map[vp] = zoom_plot.getPlotItem().vb
        dialog._zoom_viewport = vp  # 方便关闭时清理

        # 放大窗关闭 -> 移除对应高亮
        dialog.finished.connect(lambda _: self._cleanup_ecg_zoom_dialog(dialog))
        dialog.show()

        self._ecg_zoom_windows.append(dialog)
        self._ecg_dialog_region[dialog] = region

    def _cleanup_ecg_zoom_dialog(self, dialog):
        """关闭放大窗时，把对应的高亮从原图移除"""
        try:
            region = self._ecg_dialog_region.pop(dialog, None)
            if region is not None:
                try:
                    self.ecg_widget.removeItem(region)
                except Exception:
                    pass
                try:
                    self._ecg_regions.remove(region)
                except ValueError:
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

            try:
                self._ecg_zoom_windows.remove(dialog)
            except ValueError:
                pass
        except Exception:
            pass

    def _downsample_envelope(self, x, y, max_points):
        """
        包络式降采样：每个窗口保留 min/max，两点描述一个“像素列”，
        视觉近似无损，渲染/保存显著加速、降内存。
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

        if n_fit < n:
            x_ds = np.concatenate([x_ds, x[n_fit:]])
            y_ds = np.concatenate([y_ds, y[n_fit:]])
        return x_ds, y_ds

    def _mpl_line_spec_from_pg_pen(self, pen, fig_dpi, fallback_px=1.0):
        """
        将 pyqtgraph 的笔（像素宽度）映射到 matplotlib 的线（pt 宽度 + 颜色），
        使“保存图”的线宽观感 ≈ 界面。
        """
        color = 'k'
        try:
            color = pen.color().name()
        except Exception:
            pass

        wpx = fallback_px
        try:
            if hasattr(pen, 'widthF'):
                wpx = float(pen.widthF())
            elif hasattr(pen, 'width'):
                wpx = float(pen.width())
        except Exception:
            pass

        lw_pt = max(0.4, wpx * 72.0 / float(fig_dpi))  # px -> pt；给个下限
        return color, lw_pt

    def _add_export_vlines(self, ax, x_positions, linewidth, color='k', linestyle='--', alpha=0.7):
        """批量添加导出图里的 R 峰竖线，避免每个峰创建一个独立 artist。"""
        if not x_positions:
            return

        from matplotlib.collections import LineCollection

        ymin, ymax = ax.get_ylim()
        # 竖线坐标仍使用原始 R peak 秒位置，只把多个 artist 合并为一个集合。
        segments = [((float(x), ymin), (float(x), ymax)) for x in x_positions]
        collection = LineCollection(
            segments,
            colors=color,
            linewidths=linewidth,
            linestyles=linestyle,
            alpha=alpha,
        )
        ax.add_collection(collection)

    def save_figure(self):
        """保存所有页面的图形"""
        wait_box = None
        try:
            from datetime import datetime
            import time
            # 获取当前日期和时间
            current_time = datetime.now()
            formatted_time = current_time.strftime("%Y-%m-%d-%H%M%S")

            # 显示保存对话框
            dialog = SavePictureDialog(self)
            if dialog.exec_() != QDialog.Accepted:
                return False

            # 获取保存参数
            params = dialog.get_save_parameters()
            print("params",params)
            save_path = params['path']
            img_format = params['format'].lower().replace('.', '')
            dpi = params['resolution']

            # 创建保存目录
            default_folder = "ECG_Analysis_pic"
            save_dir = os.path.join(save_path, default_folder)
            os.makedirs(save_dir, exist_ok=True)

            # 弹出“请等待”消息框
            wait_box = QMessageBox(QMessageBox.Information, "Please wait",
                                   "Pic is being saved, please do not close the window...",
                                   parent=self)
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
            QApplication.processEvents()
            # 生成文件名
            filename = f"ecg_Heart_rate{formatted_time}.{img_format}"
            result_path = os.path.join(save_dir, filename)
            # 保存figure
            self.figure.savefig(
                result_path,
                format=img_format,
                dpi=dpi,
                bbox_inches='tight',
                facecolor='white',
                edgecolor='none'
            )

            # 保存 plot_widget 图片
            self.save_plot_widget(self.ecg_widget, save_dir,
                                  f"ECGsignals_with_R_peaks{formatted_time}" + params['format'], dpi, img_format)
            wait_box.close()
             # 显示成功消息
            QMessageBox.information(
                self.win,
                "Save Success",
                f"Figure has been saved to:\n{save_dir}"
            )
            QLLogging.log.info(f"ECG analysis figure saved successfully: {result_path}")
            OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'Save Pic', 0)
            return True

        except Exception as e:
            # 异常时先关等待框，再报错
            try:
                if wait_box and wait_box.isVisible():
                    wait_box.close()
            finally:
                pass
            stack_trace = traceback.format_exc()
            QLLogging.log.error(
                f"Error saving  ECG figures: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )
            QMessageBox.critical(
                self.win,
                "Error",
                f"Failed to save figures: {str(e)}"
            )
            return False

        finally:
            # 兜底清理
            if wait_box:
                try:
                    if wait_box.isVisible():
                        wait_box.close()
                finally:
                    wait_box.deleteLater()

    def save_plot_widget_offscreen(self, start_time, end_time, save_dir, filename, dpi, img_format):
        """
        离屏渲染ECG波形图，不更新当前显示
        """
        result_path = os.path.join(save_dir, filename)
        fig = None

        try:
            # 创建离屏图形
            fig, ax = plt.subplots(figsize=(14, 4), dpi=dpi)

            # 绘制ECG信号（基于已有数据）
            x_time = np.arange(len(self.ecg_results['ecg_signal'])) / self.sfreq
            time_mask = (x_time >= start_time) & (x_time <= end_time)
            # 获取当前时间窗口内的ECG数据用于y轴自适应
            ecg_data_window = self.ecg_results['ecg_signal'][time_mask]
            x_plot = x_time[time_mask]
            y_plot = self.ecg_results['ecg_signal'][time_mask]
            fig_w_px = int(fig.get_figwidth() * fig.get_dpi())
            max_pts = max(20000, fig_w_px * 4)
            if len(y_plot) > max_pts:
                # 只压缩导出显示点，不改 ECG 原始数据和任何分析结果。
                x_plot, y_plot = self._downsample_envelope(x_plot, y_plot, max_pts)
            ax.plot(x_plot, y_plot, color='red', linewidth=0.7, label="ECG Signal")

            # 绘制R峰标记线
            r_peaks_times = np.array(self.ecg_results['r_peaks_idx']) / self.sfreq
            visible_r_peaks = []
            for x in r_peaks_times:
                if start_time <= x <= end_time:
                    visible_r_peaks.append(x)

            ax.set_xlabel('Time (seconds)')
            ax.set_ylabel('Amplitude(μV)')
            ax.set_title('ECG Signal with R Peaks')
            ax.margins(x=0, y=0)

            # 设置x轴范围
            ax.set_xlim(start_time, end_time)
            if len(ecg_data_window) > 0:
                ymin = np.min(ecg_data_window)
                ymax = np.max(ecg_data_window)
                y_range = ymax - ymin
                # 添加10%的边距
                margin = y_range * 0.1 if y_range > 0 else 0.1
                ax.set_ylim(ymin - margin, ymax + margin)
            else:
                # 如果没有数据，设置默认范围
                ax.set_ylim(-100, 100)
            self._add_export_vlines(ax, visible_r_peaks, linewidth=0.7)
            # 应用保存参数
            fig.set_facecolor('white')
            fig.patch.set_edgecolor('none')
            # 固定边距避免 savefig tight bbox 的额外遍历，保持标题和坐标轴文字可见。
            fig.subplots_adjust(left=0.07, right=0.995, bottom=0.18, top=0.90)

            # 保存图像
            fig.savefig(result_path, format=img_format, dpi=dpi,
                        facecolor=fig.get_facecolor(), edgecolor='none')

            QLLogging.log.info(f"Saved ECG plot offscreen: {result_path}")
        finally:
            if fig is not None:
                plt.close(fig)

    def save_plot_widget(self, plot_widget, save_dir, filename, dpi, img_format):
        """
        导出 PyQtGraph 图像到 Matplotlib：
        - 同步当前可见范围（x、y 都按界面来）
        - 针对超大数据做包络式降采样
        - 线宽按像素等效，观感 ≈ 界面
        """
        fig = None
        try:
            result_path = os.path.join(save_dir, filename)
            fig, ax = plt.subplots(figsize=(14, 4), dpi=dpi)
            plot_item = plot_widget.plotItem

            # 0) 当前可见范围
            x_range, y_range = None, None
            try:
                xr, yr = plot_item.vb.viewRange()
                x_range, y_range = xr, yr
            except Exception:
                pass

            # 1) 曲线（含降采样 + 线宽映射）
            fig_w_px = int(fig.get_figwidth() * fig.get_dpi())
            max_pts = max(20000, fig_w_px * 4)

            for curve in plot_item.curves:
                x, y = curve.getData()
                if x is None or y is None or len(x) == 0:
                    continue
                if len(y) > max_pts:
                    x, y = self._downsample_envelope(x, y, max_pts)

                pen = curve.opts.get('pen', None)
                color, lw_pt = self._mpl_line_spec_from_pg_pen(pen, fig.dpi, fallback_px=1.0)

                line, = ax.plot(
                    x, y, color=color, linewidth=lw_pt, alpha=0.95,
                    solid_capstyle='round', solid_joinstyle='round',
                    label=curve.opts.get('name', '')
                )
                line.set_antialiased(True)
                line.set_rasterized(False)

            # 2) R 峰 InfiniteLine
            visible_r_peaks = []
            for item in plot_item.items:
                if isinstance(item, pg.InfiniteLine) and item.angle == 90:
                    x_pos = item.value()
                    if x_range and len(x_range) == 2 and not (x_range[0] <= x_pos <= x_range[1]):
                        continue
                    visible_r_peaks.append(x_pos)

            # 3) 坐标/标题/网格/图例
            ax.set_xlabel(plot_item.axes["bottom"]["item"].label.toPlainText())
            ax.set_ylabel(plot_item.axes["left"]["item"].label.toPlainText())
            ax.set_title(plot_item.titleLabel.text if plot_item.titleLabel else "")
            ax.margins(x=0, y=0)
            if plot_item.showGrid(x=True, y=True):
                ax.grid(True, linestyle='--', alpha=0.7)
            if plot_item.legend is not None:
                ax.legend()

            # 4) 同步当前可见范围（关键：把界面 y 限制也带上）
            if x_range and len(x_range) == 2:
                ax.set_xlim(x_range[0], x_range[1])
            if y_range and len(y_range) == 2:
                ax.set_ylim(y_range[0], y_range[1])
            one_px_pt = max(0.4, 72.0 / float(dpi))
            self._add_export_vlines(ax, visible_r_peaks, linewidth=one_px_pt)

            # 5) 保存
            fig.set_facecolor('white');
            fig.patch.set_edgecolor('none')
            # 固定边距替代 bbox_inches='tight'，减少长序列导出时的 tight bbox 计算。
            fig.subplots_adjust(left=0.07, right=0.995, bottom=0.18, top=0.90)
            fig.savefig(result_path, format=img_format, dpi=dpi,
                        facecolor=fig.get_facecolor(), edgecolor='none')
        except ValueError as e:
            QLLogging.log.exception(f"save widget plot, error: {e}")
        finally:
            if fig is not None:
                plt.close(fig)
    def get_current_page(self):
        """
        获取当前页码。
        """
        ts_value = self.slider_widget.time_slider.value()
        ts_min = self.slider_widget.time_slider.minimum()
        ts_max = self.slider_widget.time_slider.maximum()
        if ts_max - ts_min == 0:
            # 当时间范围为0时，默认显示第一页
            page = 1
        else:
            page = int((ts_value - ts_min) / (ts_max - ts_min) * (self.total_pages - 1) + 1)
        self.current_page = min(page, self.total_pages)

    def show_first_page(self):
        self.current_page = 1
        # 直接计算对应页的起始时间位置
        pos = (self.current_page - 1) * self.page_duration
        self.slider_widget.time_slider.setValue(int(pos))
        if self.is_heart_auto:
            self.on_heart_rate_changed("Auto")
        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'show_first_page', 0)

    def show_last_page(self):
        self.current_page = self.total_pages

        self.is_manually_changing_page = True
        pos = (self.current_page - 1) * self.page_duration
        self.slider_widget.time_slider.setValue(int(pos))
        self.page_changed.emit(self.current_page)
        self.is_manually_changing_page = False
        if self.is_heart_auto:
            self.on_heart_rate_changed("Auto")
        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'show_last_page', 0)

    def show_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
        else:
            self.current_page = self.total_pages  # 循环到最后一页
        self.is_manually_changing_page = True
        pos = (self.current_page - 1) * self.page_duration
        self.slider_widget.time_slider.setValue(int(pos))
        self.page_changed.emit(self.current_page)
        self.is_manually_changing_page = False
        if self.is_heart_auto:
            self.on_heart_rate_changed("Auto")
        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'show_prev_page', 0)

    def show_next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
        else:
            self.current_page = 1  # 循环到第一页
        self.is_manually_changing_page = True
        pos = (self.current_page - 1) * self.page_duration
        self.slider_widget.time_slider.setValue(int(pos))
        self.page_changed.emit(self.current_page)
        self.is_manually_changing_page = False
        if self.is_heart_auto:
            self.on_heart_rate_changed("Auto")
        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'show_next_page', 0)

    def set_current_page(self, page):
        """
        设置显示指定页，并更新画面。
        """
        if 1 <= page <= self.total_pages:
            self.current_page = page
        pos = (self.current_page - 1) / max((self.total_pages - 1), 1) * (self.total_duration - self.page_duration)
        self.slider_widget.time_slider.setValue(int(pos))

    def set_page_duration(self, seconds):
        """
        设置每页显示的秒数，并跳转到第一页重新显示画面。
        """
        return None
        self.page_duration = seconds
        self.current_page = 1

        start, end = self.time_range
        self.total_duration = end.toSecsSinceEpoch() - start.toSecsSinceEpoch()
        self.total_pages = int(np.ceil(self.total_duration / self.page_duration))
        self.slider_widget.time_slider.setMaximum(int(self.total_duration - seconds))

        ##更新图像
        pos = self.slider_widget.time_slider.value()
        start_time = pos
        end_time = start_time + self.page_duration
        # 更新所有子图的显示范围
        axs = self.figure.get_axes()
        for ax in axs:
            ax.set_xlim(start_time, end_time)

        # 重绘canvas
        self.canvas.draw_idle()

        # 发送页码更新信号
        self.page_changed.emit(self.current_page)

    def on_amplitude_changed(self, value):
        """
        处理振幅范围选择变化
        Parameters:
        -----------
        value : str
            下拉框选中的值，格式为 "Auto" 或 "±数值"
        """
        ecg_vb = self.ecg_widget.getPlotItem().getViewBox()
        x_min, x_max = ecg_vb.viewRange()[0]  # 获取当前x轴范围
        x, y = self.ecg_plot.getData()  # 获取当前数据
        # 根据当前x轴范围筛选数据
        if value == "Auto":
            # 获取当前显示范围内的数据
            mask = (x >= x_min) & (x <= x_max)
            visible_ydata = y[mask]

            if len(visible_ydata) > 0:
                # 计算数据范围
                ymin = visible_ydata.min()
                ymax = visible_ydata.max()

                # 添加10%的边距
                margin = (ymax - ymin) * 0.1
                ecg_vb.setYRange(ymin - margin, ymax + margin)
                ecg_vb.enableAutoRange(axis=pg.ViewBox.YAxis)
            else:
                ecg_vb.enableAutoRange(axis=pg.ViewBox.YAxis)  # 自动范围
        else:
            try:
                amp = float(value.lstrip('±'))
                ecg_vb.setYRange(-amp, amp, padding=0)  # 设置手动范围
            except ValueError:
                ecg_vb.enableAutoRange(axis=pg.ViewBox.YAxis)  # 自动范围

    def on_heart_rate_changed(self, value):
        """
        处理心率范围选择变化

        Parameters:
        -----------
        value : str
            下拉框选中的值，格式为 "Auto" 或 "±数值"
        """
        axs = self.figure.get_axes()
        if value == "Auto":
            self.manual_y_range = None
            self.is_heart_auto = True
        else:
            try:
                self.is_heart_auto = False
                # 去掉±符号并提取数值
                if value.startswith("±"):
                    value = value[1:]
                amp = float(value)
                self.manual_y_range = (0, amp)

            except ValueError:
                self.manual_y_range = None

        # 更新图表显示
        if hasattr(self, 'figure') and len(self.figure.get_axes()) > 0:
            if self.manual_y_range is None:
                # 自动范围时重置y轴
                try:
                    # 获取当前显示范围内的数据
                    xmin, xmax = axs[0].get_xlim()
                    line = axs[0].lines[0]
                    xdata = line.get_xdata()
                    ydata = line.get_ydata()

                    # 找到当前显示范围内的数据索引
                    mask = (xdata >= xmin) & (xdata <= xmax)
                    visible_ydata = ydata[mask]

                    if len(visible_ydata) > 0:
                        # 计算数据范围
                        ymin = visible_ydata.min()
                        ymax = visible_ydata.max()

                        # 添加10%的边距
                        margin = (ymax - ymin) * 0.3
                        self.manual_y_range = ( ymin - margin, ymax + margin)
                    else:
                        print(",,,,,,")
                        self.manual_y_range = None

                except Exception as e:
                    print(f"自动计算y轴范围时出错: {str(e)}")
                    self.manual_y_range = None

            # 使用手动设置的范围
            axs[0].set_ylim(self.manual_y_range)

            # 重绘图表
            self.canvas.draw_idle()

class ECGAnalysisViewer(QWidget):
    def __init__(self, title, parent=None):
        super().__init__()
        self.setWindowTitle("ECG Analysis")
        self.setStyleSheet(ControlStyle.get_widget_style())
        self.setGeometry(100, 100, 1440, 900)  # 初始窗口大小
        self.title = title
        self.init_ui()
        self.connect_actions()

        self.win = None
        self.results = None
        self.hrv_window = None
        self.select_window = None
        self.select_ui = None

    def init_ui(self):
        """初始化界面布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 设置主布局的边距
        main_layout.setSpacing(0)
        # 顶部栏
        self.init_header(main_layout)

        # 主体区域：左侧控制 + 右侧显示
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        # 左侧控制栏
        self.init_left_panel(content_layout)

        # 中央显示区域和底部按钮
        self.init_center_and_bottom(content_layout)

        # 将主体布局添加到主布局
        main_layout.addLayout(content_layout)

        self.add_short_cut(self)

    def add_short_cut(self, layout):
        setup_short_cut(self.nav_buttons_widget.button_previous,
                self.nav_buttons_widget.button_next,
                layout,
                self.viewer.show_prev_page,
                self.viewer.show_next_page)

    def init_header(self, main_layout):
        """初始化顶部栏"""
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(30, 20, 20, 20)  # 设置顶部栏的边距

        # 标题
        title_label = QLabel(self.title)
        title_label.setStyleSheet(ControlStyle.get_label_word_style())
        ControlStyle.get_font_size(title_label, 12)
        header_layout.addWidget(title_label)

        header_layout.addStretch()  # 添加弹性空间，确保右侧控件靠右

        # 添加其他控件（如导航按钮）
        self.nav_buttons_widget = NavButtonsWidget(parent=self)
        # self.nav_buttons_widget.label_time_scale.setText("Time Scale(min):")
        # self.nav_buttons_widget.combo_time_scale.clear()
        # self.nav_buttons_widget.combo_time_scale.addItems(["5", "10", "20", "30", "60", "All"])
        self.nav_buttons_widget.label_time_scale.hide()
        self.nav_buttons_widget.combo_time_scale.hide()
        header_layout.addWidget(self.nav_buttons_widget)

        # 将顶部栏添加到主布局
        main_layout.addLayout(header_layout)

        # 添加分割线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setStyleSheet("background-color: #a9a9a9;")
        separator.setFixedHeight(1)
        main_layout.addWidget(separator)

    def init_left_panel(self, content_layout):
        """初始化左侧控制栏"""
        self.sidebar = CollapsibleSidebar(
            parent=self,
            title="Control Panel",
            initial_state=True  # 初始为展开状态
        )
        self.sidebar.set_expanded_width(400)
        self.left_layout = QVBoxLayout()
        self.left_layout.setContentsMargins(0, 0, 0, 40)
        # 通道选择
        # self.channel_selector =
        channel_selection_vlayout = QVBoxLayout()
        channel_selection_vlayout.setContentsMargins(32, 24, 32, 24)
        channel_selection_vlayout.setSpacing(8)

        label_channel_selection = QLabel()
        label_channel_selection.setObjectName("label_channel_selection")
        label_channel_selection.setText("Channel Select：")
        label_channel_selection.setMinimumSize(250, 32)
        label_channel_selection.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(label_channel_selection, 12)
        channel_selection_vlayout.addWidget(label_channel_selection)
        # EMG Channel Selection
        emg_layout = QHBoxLayout()
        emg_layout.setContentsMargins(0, 0, 0, 0)
        emg_layout.setSpacing(0)

        label_emg = QLabel()
        label_emg.setText("ECG")
        label_emg.setObjectName("label_emg")
        label_emg.setMinimumSize(49, 32)
        label_emg.setStyleSheet(ControlStyle.get_wiget400_word_style(16))
        ControlStyle.get_font_size(label_emg, 10)

        self.combobox_emg = QComboBox()
        self.combobox_emg.setObjectName("combobox_emg")
        self.combobox_emg.setMinimumSize(201, 32)
        self.combobox_emg.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_emg, 10)

        emg_layout.addWidget(label_emg)
        emg_layout.addWidget(self.combobox_emg)
        channel_selection_vlayout.addLayout(emg_layout)
        self.left_layout.addLayout(channel_selection_vlayout)
        # 分割线
        separator_between_channel_and_time = QFrame()
        separator_between_channel_and_time.setFrameShape(QFrame.HLine)
        separator_between_channel_and_time.setStyleSheet("background-color: #a9a9a9;")
        separator_between_channel_and_time.setFixedHeight(1)
        self.left_layout.addWidget(separator_between_channel_and_time)

        # 时间选择
        self.time_selector = TimeRangeSelector()
        self.left_layout.addWidget(self.time_selector)
        # 分割线
        separator_between_channel_and_time = QFrame()
        separator_between_channel_and_time.setFrameShape(QFrame.HLine)
        separator_between_channel_and_time.setStyleSheet("background-color: #a9a9a9;")
        separator_between_channel_and_time.setFixedHeight(1)
        self.left_layout.addWidget(separator_between_channel_and_time)

        # 添加一个固定的下方空白区域
        bottom_spacer = QSpacerItem(0, 300, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.left_layout.addItem(bottom_spacer)
        self.left_layout.addStretch()

        # 将侧边栏添加到主体布局（原直接添加left_layout的位置改为添加sidebar）
        self.sidebar.content_layout.addLayout(self.left_layout)
        content_layout.addWidget(self.sidebar)

    def init_center_and_bottom(self, content_layout):
        """初始化中央显示区域和底部按钮"""
        center_and_bottom_widget = QWidget(self)  # 创建一个 QWidget 作为布局的容器
        center_and_bottom_widget.setStyleSheet("background-color: white;")  # 设置背景为白色
        center_and_bottom_layout = QVBoxLayout(center_and_bottom_widget)
        center_and_bottom_layout.setContentsMargins(0, 0, 0, 0)

        # 中央显示区域
        # 创建水平布局
        self.h_layout = QHBoxLayout()
        self.h_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        self.h_layout.setSpacing(0)  # 移除控件间的间距

        center_and_bottom_layout.addLayout(self.h_layout, stretch=3)  # 中央显示区域占 3 份
        self.display_area = IconWithTextWidget(
            icon_path="./resource/picture/Analyse.png",  # 图标路径
            text="请设置分析参数后点击“Analyse”开始分析"
        )
        self.h_layout.addWidget(self.display_area)
        # self.display_area.setAlignment(Qt.AlignCenter)

        # 创建进度条页面
        self.progressBar_widget = QWidget(self)
        self.progressBar_widget.setMinimumSize(1126, 692)

        progressBar_vlayout = QVBoxLayout(self.progressBar_widget)
        progressBar_vlayout.setContentsMargins(434, 0, 434, 0)
        progressBar_vlayout.setAlignment(Qt.AlignCenter)
        progressBar_vlayout.setSpacing(0)

        self.label_progressBar = QLabel()
        self.label_progressBar.setText("分析中")
        self.label_progressBar.setObjectName("label_progressBar")
        self.label_progressBar.setMinimumSize(50, 20)
        self.label_progressBar.setStyleSheet(ControlStyle.get_redo_set_pushButton_style())

        self.progressBar = GifProgressBar()
        self.progressBar.setObjectName("progressBar")
        self.progressBar.setMinimumSize(258, 16)
        self.progressBar.setStyleSheet(ControlStyle.get_progressBar_style())

        progressBar_vlayout.addWidget(self.progressBar)
        progressBar_vlayout.addWidget(self.label_progressBar)
        self.h_layout.addWidget(self.progressBar_widget)
        self.progressBar_widget.hide()

        # 显示图像的页面
        self.viewer = Ui_ECG_compute()
        self.h_layout.addWidget(self.viewer)
        self.viewer.hide()
        # 添加分割线
        separator_below_display = QFrame()
        separator_below_display.setFrameShape(QFrame.HLine)
        separator_below_display.setStyleSheet("background-color: #d3d3d3;")
        separator_below_display.setFixedHeight(1)
        center_and_bottom_layout.addWidget(separator_below_display)

        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(10, 20, 20, 20)
        bottom_layout.setSpacing(20)  # 设置按钮之间的间距为 20 像素

        self.analyse_btn = QPushButton("Analyse")
        self.analyse_btn.setStyleSheet(ControlStyle.get_pushButton_style())
        ControlStyle.get_font_size(self.analyse_btn, 10)
        self.analyse_btn.setMinimumSize(145, 40)

        self.hrv_ana_btn = QPushButton("HRV ana")
        self.hrv_ana_btn.setStyleSheet(ControlStyle.get_pushButton_style_white())
        self.hrv_ana_btn.setMinimumSize(145, 40)
        ControlStyle.get_font_size(self.hrv_ana_btn, 10)

        self.save_pic_btn = QPushButton("Save Pic")
        self.save_pic_btn.setStyleSheet(ControlStyle.get_pushButton_style_white())
        self.save_pic_btn.setMinimumSize(145, 40)
        ControlStyle.get_font_size(self.save_pic_btn, 10)

        self.save_data_btn = QPushButton("Save Data")
        self.save_data_btn.setStyleSheet(ControlStyle.get_pushButton_style_white())
        self.save_data_btn.setMinimumSize(145, 40)
        ControlStyle.get_font_size(self.save_data_btn, 10)

        self.average_HR_btn = QPushButton("Average HR")
        self.average_HR_btn.setStyleSheet(ControlStyle.get_pushButton_style_white())
        self.average_HR_btn.setMinimumSize(145, 40)
        ControlStyle.get_font_size(self.average_HR_btn, 10)

        self.disable_save_buttons()

        bottom_layout.addWidget(self.analyse_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.average_HR_btn)
        bottom_layout.addWidget(self.hrv_ana_btn)
        bottom_layout.addWidget(self.save_pic_btn)
        bottom_layout.addWidget(self.save_data_btn)


        center_and_bottom_layout.addLayout(bottom_layout)

        # 将中央和底部布局添加到主体布局
        content_layout.addWidget(center_and_bottom_widget, stretch=7)  # 中央显示区域占 7 份

    def update_channel_list(self):
        """
        更新通道选择下拉框

        Parameters:
        -----------
        raw : mne.io.Raw
            原始数据对象
        """
        # 清空现有项
        self.combobox_emg.clear()

        # 获取所有通道名
        channel_names = self.raw.info['ch_names']

        # 添加所有通道
        for ch_name in channel_names:
            self.combobox_emg.addItem(ch_name)

        # 添加行高
        # 创建 QListView 并设置行高
        view_emg = QListView()
        view_emg.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.combobox_emg.setView(view_emg)  # 绑定视图到 QComboBox

        # 默认选择第一个通道
        if len(channel_names) > 0:
            self.combobox_emg.setCurrentIndex(0)

    def import_raw(self, raw):
        """
        导入原始数据，并设置默认的时间范围。
        """
        self.raw = raw.copy()

        # 获取原始数据的起始时间和终止时间
        self.meas_dat = raw.info['meas_date'].replace(tzinfo=None)  # 起始时间
        self.total_duration = int(raw.times[-1])  # 转换为整数秒   数据总时长（秒）
        self.end_time = self.meas_dat + datetime.timedelta(seconds=self.total_duration)  # 终止时间

        # 设置时间选择器的默认时间范围
        self.time_selector.set_time_range(self.meas_dat, self.end_time)
        self.time_selector.set_max_time(self.end_time)
        self.time_selector.set_min_time(self.meas_dat)

        # 获取所有通道名称        ##根据数据设置通道
        self.update_channel_list()

    def connect_actions(self):
        """连接按钮的槽函数"""
        self.analyse_btn.clicked.connect(self.on_analyse_clicked)  # 开始分析按钮
        self.save_data_btn.clicked.connect(self.save_data)  # 保存数据按钮
        self.average_HR_btn.clicked.connect(self.average_HR)  # 平均心率分析
        self.save_pic_btn.clicked.connect(self.save_figure)  # 保存图片按钮
        self.hrv_ana_btn.clicked.connect(self.open_hrv_analysis) # 弹出hrv窗口

        self.nav_buttons_widget.first_pushButton.clicked.connect(self.viewer.show_first_page)  # 第一页
        self.nav_buttons_widget.last_pushButton.clicked.connect(self.viewer.show_last_page)   # 最后一页
        self.nav_buttons_widget.button_previous.clicked.connect(self.viewer.show_prev_page)  # 上一页
        self.nav_buttons_widget.button_next.clicked.connect(self.viewer.show_next_page)  # 下一页

        self.viewer.page_changed.connect(self.nav_buttons_widget.set_current_page)
        self.nav_buttons_widget.combo_time_scale.currentTextChanged.connect(self.time_scale_change)  # 一页大小
        self.nav_buttons_widget.button_goto_epoch.clicked.connect(self.update_display_goto_epoch)  # 跳转到指定页面

    def save_data(self):
        """保存ECG分析结果"""
        self.disable_buttons()
        try:
            # 检查是否有分析结果
            if not hasattr(self, 'results') or not self.results:
                QMessageBox.warning(
                    self,
                    "No Data",
                    "No analysis results to save.\nPlease perform ECG analysis first."
                )
                return False

            from datetime import datetime,timedelta
            # 获取当前日期和时间
            current_time = datetime.now()
            formatted_time = current_time.strftime("%Y-%m-%d%H%M%S")

            # 显示保存对话框
            dialog = SaveDataDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                # 获取保存参数
                params = dialog.get_save_parameters()
                save_path = params['path']
                data_format = params['format'].lower()

                # 创建保存目录
                default_folder = "ECG_Analysis_data"
                save_dir = os.path.join(save_path, default_folder)
                os.makedirs(save_dir, exist_ok=True)

                start_time = self.time_selector.get_time_range()[0].toPyDateTime()
                # 导出表使用局部 padded arrays，避免保存数据时改变后续绘图/HRV 使用的 self.results。
                results_df_subset = _build_ecg_save_data_frame(self.results, start_time)

                # 根据不同格式保存数据
                if data_format == '.csv':
                    file_path = os.path.join(save_dir, f'ecg_analysis_results{formatted_time}.csv')
                    results_df_subset.to_csv(file_path, index=False)
                elif data_format == '.npy':
                    file_path = os.path.join(save_dir, f'ecg_analysis_results{formatted_time}.npy')
                    save_dict = {
                        'data': results_df_subset.to_numpy(),
                        'columns': results_df_subset.columns.tolist(),
                        # 'index': results_df_subset.index.tolist(),
                        'sampling_rate': self.results['sampling_rate']
                    }
                    np.save(file_path, save_dict, allow_pickle=True)

                elif data_format == '.mat':
                    file_path = os.path.join(save_dir, f'ecg_analysis_results{formatted_time}.mat')
                    from scipy.io import savemat
                    save_dict = {
                        'data': results_df_subset.to_numpy(),
                        'columns': results_df_subset.columns.tolist(),
                        # 'index': results_df_subset.index.tolist(),
                        'sampling_rate': self.results['sampling_rate']
                    }
                    savemat(file_path, save_dict)

                # 显示成功消息
                QMessageBox.information(
                    self.win,
                    "Save Success",
                    f"Analysis results have been saved to:\n{file_path}"
                )
                QLLogging.log.info(f"ECG analysis results saved successfully: {file_path}")
                OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'Save Data', 0)
                return True

        except Exception as e:
            stack_trace = traceback.format_exc()
            QLLogging.log.error(
                f"Failed to save ECGAnalysis results: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )
            QMessageBox.critical(
                self.win,
                "Error",
                f"Failed to save ECGAnalysis results: {str(e)}"
            )
            return False

        finally:
            self.enable_buttons()

    def average_HR(self):
        from datetime import timedelta
        """求某时间段的平均心率"""
        try:
            # 检查是否有分析结果
            if not hasattr(self, 'results') or 'heart_rate' not in self.results:
                QMessageBox.warning(self, "无数据", "请先完成ECG分析")
                return

            if self.select_window is None:
                starttime, endtime = self.time_selector.get_time_range()
                start_time = starttime.toPyDateTime()
                end_time = endtime.toPyDateTime()
                self.select_window = QWidget()
                self.select_ui = Averageui(results = self.results,start_time=start_time,end_time=end_time)  # 创建 Averageui 实例
                self.select_ui.import_raw(self.raw)
                self.select_ui.setupUi(self.select_window)

            if self.select_window.isMinimized():
                self.select_window.setWindowState(
                    self.select_window.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
            self.select_window.show()
            self.select_window.raise_()

        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"发生错误:\n{str(e)}")

    def calculate_avg_hr(self, start_seconds, end_seconds):
        """根据时间范围计算平均心率"""
        try:
            r_peaks = self.results['r_peaks_times']  # R峰时间点（秒）
            heart_rates = self.results['heart_rate']

            # 筛选时间段内的心跳
            valid_indices = [i for i, t in enumerate(r_peaks) if start_seconds <= t <= end_seconds]

            if not valid_indices:
                QMessageBox.warning(self, "无数据", "在所选时间范围内未检测到心跳")
                return

            period_hr = heart_rates[valid_indices]
            avg_hr = np.mean(period_hr)

        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"发生错误:\n{str(e)}")

    def save_figure(self):
        try:
            self.disable_buttons()
            import time
            start_time1 = time.time()
            self.viewer.save_figure()
            end_time = time.time() - start_time1
            print("总时长：", end_time)
            self.enable_buttons()
        except Exception as e:
            stack_trace = traceback.format_exc()
            QLLogging.log.error(
                f"Failed to save ECGAnalysis figure: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )
            return

    def update_display_goto_epoch(self):
        """跳转到特定epoch"""
        try:
            target_page, done = QInputDialog.getInt(
                self.win, 'Input Dialog', 'Enter the Page You Want to View:',
                min=1, max=self.total_pages
            )
            if done:
                current_page = min(target_page, self.total_pages)
                self.viewer.set_current_page(current_page)
                self.nav_buttons_widget.set_current_page(current_page)
                if self.viewer.is_heart_auto:
                    self.viewer.on_heart_rate_changed("Auto")

        except Exception as e:
            print(f"Error in update_display_goto_epoch: {str(e)}")

    def time_scale_change(self):
        """
            当 Time Scale 复选框的值改变时，更新页面持续时间。
            """
        # 获取当前选择的时间刻度（秒）
        self.scale_seconds = self.nav_buttons_widget.get_time_scale_min()

        # 如果选择的不是 "All"，更新页面持续时间
        if self.scale_seconds is not None:
            self.scale_seconds = min(self.scale_seconds, self.total_duration)
        else:
            # 如果选择的是 "All"，将页面持续时间设置为总持续时间
            self.scale_seconds = self.total_duration

        self.viewer.set_page_duration(self.scale_seconds)

        self.total_pages = int(np.ceil(self.total_duration / self.scale_seconds))
        self.nav_buttons_widget.set_total_pages(self.total_pages)

    def disable_buttons(self):
        """
        禁用分析和保存按钮
        """
        # 禁用分析按钮
        self.analyse_btn.blockSignals(True)
        self.analyse_btn.setEnabled(False)

        # 禁用保存数据按钮
        self.save_data_btn.blockSignals(True)
        self.save_data_btn.setEnabled(False)
        # 禁用保存数据按钮
        self.average_HR_btn.blockSignals(True)
        self.average_HR_btn.setEnabled(False)

        # 禁用保存图片按钮
        self.save_pic_btn.blockSignals(True)
        self.save_pic_btn.setEnabled(False)

        # 禁用HRV ana按钮
        self.hrv_ana_btn.blockSignals(True)
        self.hrv_ana_btn.setEnabled(False)

    def disable_save_buttons(self):
        # 禁用保存数据按钮
        self.save_data_btn.blockSignals(True)
        self.save_data_btn.setEnabled(False)

        self.average_HR_btn.blockSignals(True)
        self.average_HR_btn.setEnabled(False)
        # 禁用保存图片按钮
        self.save_pic_btn.blockSignals(True)
        self.save_pic_btn.setEnabled(False)

        # 禁用HRV ana按钮
        self.hrv_ana_btn.blockSignals(True)
        self.hrv_ana_btn.setEnabled(False)

    def enable_buttons(self):
        """
        恢复按钮的使用
        """
        # 恢复分析按钮
        self.analyse_btn.blockSignals(False)
        self.analyse_btn.setEnabled(True)

        # 恢复保存数据按钮
        self.save_data_btn.blockSignals(False)
        self.save_data_btn.setEnabled(True)
        self.average_HR_btn.blockSignals(False)
        self.average_HR_btn.setEnabled(True)
        # 恢复保存图片按钮
        self.save_pic_btn.blockSignals(False)
        self.save_pic_btn.setEnabled(True)

        # 恢复保存图片按钮
        self.hrv_ana_btn.blockSignals(False)
        self.hrv_ana_btn.setEnabled(True)

    def on_analyse_clicked(self):
        """处理 Analyse 按钮点击事件"""
        try:
            self.select_window = None
            QLLogging.log.info("Starting ECG analysis...")
            OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'ECG analysis begin!', 0)
            self.get_valid_time_range()
            # 检查 scale_seconds 是否为有效值
            if not self.time_selector.validate_time_range() or not self.scale_seconds or self.scale_seconds <= 0:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self.win,
                    "Time Range Error",
                    f"The specified time range is invalid.\n\n"
                    f"Valid time range:\n"
                    f"Start: {self.meas_dat }\n"
                    f"End: {self.end_time }"
                )
                return
            # 检查是否选择了通道
            selected_channels = self.combobox_emg.currentText()
            if not selected_channels:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self.win,"No Channel Selected",
                    "Please select at least one channel!")
                return None
            
            # 禁用按钮
            self.disable_buttons()
            # 在这里添加分析逻辑
            self.display_area.hide()
            self.viewer.hide()
            self.progressBar_widget.show()
            self.progressBar.resetValue()  # 重置进度条

            self.nav_buttons_widget.set_current_page(1)
            # 更新总页数
            start, end = self.time_selector.get_time_range()
            self.total_duration = end.toSecsSinceEpoch() - start.toSecsSinceEpoch()
            if self.total_duration < 0:
                self.total_duration = 0  # 确保总时长不为负数

            # 开始创建分析线程
            result_path = os.path.join(self.raw.info['description'], 'EMG')
            self.worker = ECGAnalysisWorker(
                self.raw,  ##原始数据
                selected_channels,
                self.time_selector.get_time_range(),
                result_path
            )
            # 连接信号
            self.worker.finished.connect(self.on_worker_result_ready)  # 连接结果信号
            self.worker.progress.connect(self.on_worker_progress)  # 可选：连接进度信号
            self.worker.error.connect(self.on_worker_error)  # 可选：连接错误信号

            self.worker.start()
            self.viewer.time_range = self.time_selector.get_time_range()
            # self.viewer.set_page_duration(self.scale_seconds)

            self.viewer.slider_widget.label_start_time.setText('00:00:00')
            total_duration = min(1800, self.total_duration)
            self.viewer.total_duration = total_duration
            self.viewer.slider_widget.time_slider.setMaximum(int(total_duration - 5))

            hours = int(total_duration // 3600)
            minutes = int((total_duration % 3600) // 60)
            seconds = int(total_duration % 60)
            self.viewer.slider_widget.label_end_time.setText(f"{hours:02}:{minutes:02}:{seconds:02}")

            self.total_pages = int(np.ceil(total_duration / 5))
            self.nav_buttons_widget.set_total_pages(self.total_pages)
            self.viewer.total_pages =self.total_pages
            return True
        
        except Exception as e:
            stack_trace = traceback.format_exc()
            QLLogging.log.error(
                f"Error in on_analyse_clicked(ECG analysis): {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )
            QMessageBox.critical(
                self.win,
                "Analysis Error",
                f"Failed to start analysis: {str(e)}"
            )
            # 恢复分析按钮
            self.analyse_btn.blockSignals(False)
            self.analyse_btn.setEnabled(True)
            return False

    def on_worker_result_ready(self, values=None):
        try:
            self.progressBar_widget.hide()
            self.viewer.show()
            self.viewer.slider_widget.time_slider.setTotalPages(self.total_pages)
            # 更新图表
            self.viewer.plot_ecg_results(values, self.raw.info['sfreq'])  # 数据数据画图
            self.viewer.on_heart_rate_changed("Auto")
            # 恢复按钮状态
            self.results = values
            self.enable_buttons()
            QLLogging.log.info("ECG analysis results successfully processed and displayed")

        except Exception as e:
            stack_trace = traceback.format_exc()
            QLLogging.log.error(
                f"Error processing ECG analysis results: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )
            QMessageBox.critical(
                self.win,
                "Analysis Error",
                f"Failed to process analysis results: {str(e)}"
            )
            # 恢复UI状态
            self.analyse_btn.blockSignals(False)
            self.analyse_btn.setEnabled(True)

    def on_worker_progress(self, progress):
        """
        处理 Worker 的进度信号。
        :param progress: 当前进度百分比
        """
        self.progressBar.setGreaterValue(progress)

    def on_worker_error(self, error_message):
        """
        处理 Worker 的错误信号。
        :param error_message: 错误信息
        """
        from PyQt5.QtWidgets import QMessageBox
        # 记录错误日志
        QLLogging.log.error(f"ECG analysis computation worker error occurred: {error_message}")

        # 向用户显示错误消息
        QMessageBox.critical(
            self.win,
            "Error",
            f"An error occurred during computation:\n{error_message}"
        )

        # 恢复信号
        # self.enable_buttons()

        # 恢复分析按钮
        self.analyse_btn.blockSignals(False)
        self.analyse_btn.setEnabled(True)

    def get_valid_time_range(self):
        """
        获取用户选择的时间范围和有效的时间刻度。

        :return: (user_start, user_end, scale_seconds) 或 None 如果时间范围无效
        """
        # 获取用户选择的时间范围
        self.user_start, self.user_end = self.time_selector.get_time_range()
        self.user_start = self.user_start.toPyDateTime()  # 转换为 datetime 对象
        self.user_end = self.user_end.toPyDateTime()  # 转换为 datetime 对象

        # 计算用户选择的时间范围（以秒为单位）
        user_time_range = (self.user_end - self.user_start).total_seconds()

        # 提取时长标签，转换为以秒为单位
        self.scale_seconds = self.nav_buttons_widget.get_time_scale_min()  # 获取 scale_seconds
        if self.scale_seconds is None:
            self.scale_seconds = user_time_range
        print(f"Original scale_seconds: {self.scale_seconds}")

        # 更新 scale_seconds 为用户选择的时间范围与 scale_seconds 的最小值
        self.scale_seconds = min(user_time_range, self.scale_seconds)
        print(f"Updated scale_seconds: {self.scale_seconds}")

    def open_hrv_analysis(self):
        from .ECG_HRV_Analysis import Ui_ECG_HRV
        self.hrv_window = QWidget()
        self.hrv_ui = Ui_ECG_HRV()
        self.hrv_ui.ecg_analysis_worker_results = self.results
        self.hrv_ui.setupUi(self.hrv_window)

        self.hrv_window.closeEvent = self.create_close_handler()

        self.hrv_window.show()

    def create_close_handler(self):
        """创建一个闭包来处理关闭事件"""
        def handle_close(event):
            self.close_hrv_ui(event)

        return handle_close

    def close_hrv_ui(self, event):
        """重写closeEvent以在关闭窗口时完全清理所有资源"""
        try:
            # 调用一下 HRV 的close
            if hasattr(self, 'hrv_ui') and self.hrv_ui:
                # 创建一个虚拟的关闭事件
                from PyQt5.QtCore import QEvent
                event = QEvent(QEvent.Close)
                self.hrv_ui.closeEvent(event)


            QLLogging.log.info("Starting hrv Analysis cleanup...")
            if self.hrv_ui is not None:
                # 清理所有大型数据属性
                large_data_attrs = [
                    'hrv_thread',
                    'ecg_analysis_worker_results',
                    'hrv_result',
                    'figures',
                    'rr_interval_plt'
                ]

                for attr in large_data_attrs:
                    if hasattr(self.hrv_ui, attr):
                        delattr(self.hrv_ui, attr)

            # 关闭并删除窗口
            if self.hrv_window is not None:
                self.hrv_window.close()
                self.hrv_window.deleteLater()
                self.hrv_window = None

            # 强制多次垃圾回收
            import gc
            gc.collect()
            gc.collect()

        except Exception as e:
            QLLogging.log.info(f"Error during hrv Analysis cleanup: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            if event:
                event.accept()

class Averageui(QObject,Ui_Data_Select):
    def __init__(self, results=None, start_time=None, end_time=None,parent=None):
        super().__init__()  # 调用父类构造函数
        self.parent = parent
        self.results = results  # 存储传入的心率值
        self.base_width = 1920  # 基准分辨率宽度
        self.base_height = 1080  # 基准分辨率高度
        self.start_time = start_time
        self.end_time = end_time

    def setupUi(self, Dialog):
        # 调用父类的setupUi方法来设置基本UI
        super().setupUi(Dialog)
        _translate = QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Data_Select", "Average HR"))

        # 获取当前屏幕分辨率
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        current_width = screen_geometry.width()
        current_height = screen_geometry.height()

        # 计算缩放比例
        width_scale = current_width / self.base_width
        height_scale = current_height / self.base_height

        # 添加平均心率相关的控件
        self.average_hr_label = QLabel(Dialog)
        self.average_hr_label.setText("Average HR: ")
        # 应用缩放比例到位置和大小
        self.average_hr_label.setGeometry(QRect(
            30, 310, # 顶点坐标
            int(150 * width_scale), int(30 * height_scale) # 长宽
        ))
        self.average_hr_label.setStyleSheet("""
             font-family: Microsoft YaHei;
             font-weight: 500;          /* 加粗 */
             color: #000000;             /* 字体颜色 */
             line-height: 20px; /* 增大行高 */
             font-size: 12pt;   /* 增大字体大小 */
             text-align: center;
             font-style: normal;
             text-transform: none;
         """)
        self.average_hr_lineedit = QLineEdit(Dialog)
        # 应用缩放比例到位置和大小
        self.average_hr_lineedit.setGeometry(QRect(
            180, 310, # 顶点坐标
            int(100 * width_scale), int(30 * height_scale) # 长宽
        ))
        self.average_hr_lineedit.setReadOnly(True)  # 设置为只读
        self.average_hr_lineedit.setStyleSheet("""
            font-family: Microsoft YaHei;
            font-size: 10pt;            /* 12磅 */
            color: #2A87DB;             /* 字体颜色 */
        """)
        self.average_hr_lineedit.setText(" ")


    def update_timelabel(self):
        try:
            start_time = self.start_time
            end_time = self.end_time
            start = start_time.strftime('%Y-%m-%d %H:%M:%S')
            end = end_time.strftime('%Y-%m-%d %H:%M:%S')
            self.time_label.setText(f"Available range：{start} ～ {end}")
            # 将时间分成两部分，一部分设置到comboBox,一部分设置到lineEdit中
            # 使用 split() 方法按空格分割
            start_parts = start.split()
            end_parts = end.split()
            start_data_part = start_parts[0]
            start_time_part = QTime.fromString(start_parts[1], "HH:mm:ss")
            end_data_part = end_parts[0]
            end_time_part = QTime.fromString(end_parts[1], "HH:mm:ss")
            self.time_lineEdit_1.setTime(start_time_part)
            self.time_lineEdit_2.setTime(end_time_part)

        except ValueError as e:
            QLLogging.log.exception(f"update_timelabel error: {e}")

        if start_data_part == end_data_part:
            # 只有一个选项
            self.date_comboBox_1.addItem(f"{start_data_part}")
            self.date_comboBox_2.addItem(f"{end_data_part}")
            # 设置默认选项
            self.date_comboBox_1.setCurrentText(f"{start_data_part}")
            self.date_comboBox_2.setCurrentText(f"{end_data_part}")
        else:
            # 有两个选项
            self.date_comboBox_1.addItem(f"{start_data_part}")
            self.date_comboBox_1.addItem(f"{end_data_part}")
            self.date_comboBox_2.addItem(f"{start_data_part}")
            self.date_comboBox_2.addItem(f"{end_data_part}")
            # 设置默认选项
            self.date_comboBox_1.setCurrentText(f"{start_data_part}")
            self.date_comboBox_2.setCurrentText(f"{end_data_part}")

    def apply_DataSelect(self):
        # 读取时间输入
        start_str = self.date_comboBox_1.currentText() + " " + self.time_lineEdit_1.text()
        end_str = self.date_comboBox_2.currentText() + " " + self.time_lineEdit_2.text()

        # 定义时间格式
        time_format = "%Y-%m-%d %H:%M:%S"

        try:
            # 尝试将输入转换为datetime对象
            start_dt = datetime.datetime.strptime(start_str, time_format)
            end_dt = datetime.datetime.strptime(end_str, time_format)

            # 获取记录的开始时间
            # meas_date = self.raw.info['meas_date'].replace(tzinfo=None)
            meas_date = self.start_time
            # 获取原始数据的起始时间和终止时间
            total_duration = int(self.raw.times[-1])  # 转换为整数秒   数据总时长（秒）
            end_time = meas_date + datetime.timedelta(seconds=total_duration)  # 终止时间

            # 计算时间差，用户选择的时间范围相对于数据记录开始时间的秒数偏移量
            start_seconds = (start_dt - meas_date).total_seconds()
            end_seconds = (end_dt - meas_date).total_seconds()
            seconds = self.raw.n_times / self.raw.info['sfreq']#整个数据总时长

            start_limit=self.start_time
            end_limit=self.end_time

            # 检查时间是否有效,开始时间不小于起始，结束时间不大于总时长
            if (start_limit - start_dt).total_seconds() > 0 or (end_limit - end_dt).total_seconds() < 0 or (start_dt - end_dt).total_seconds() > 0:
                QMessageBox.warning(
                    self.win,
                    "Time Range Error",
                    f"The specified time range is invalid.\n\n"
                    f"Valid time range:\n"
                    f"Start: {start_limit}\n"
                    f"End: {end_limit}"
                )
                return

            r_peaks = self.results['r_peaks_times']  # R峰时间点（秒）
            heart_rates = self.results['heart_rate']

            # 筛选时间段内的心跳
            valid_indices = [i for i, t in enumerate(r_peaks) if start_seconds <= t <= end_seconds]
            print(valid_indices)
            print(r_peaks[valid_indices])

            if not valid_indices:
                QMessageBox.warning(self, "无数据", "在所选时间范围内未检测到心跳")
                return

            period_hr = heart_rates[valid_indices]
            avg_hr = np.mean(period_hr)
            self.average_hr_lineedit.setText(f"{avg_hr:.1f} BPM")

        except ValueError as e:
            QLLogging.log.exception(f"apply_DataSelect error: {e}")
