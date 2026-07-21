from PIL import Image
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QProgressBar, QApplication,
    QInputDialog, QComboBox, QSpacerItem, QSizePolicy, QMessageBox, QToolButton, QListView, QDialog,
    QMenu, QAction, QProgressDialog, QRubberBand
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QDateTime, QEvent, QRect, QSize, QPoint
from matplotlib import pyplot as plt

from .Infrastructure.log.QLLogging import QLLogging
from .CustomControls import StyledCheckboxWidget, TimeRangeSelector,IconWithTextWidget,TimeSliderWidget,FrequencyCheckboxWidget,NavButtonsWidget,PropertyWidget
from .Control_Style import ControlStyle
import datetime
from .SavePicCPM import SavePictureDialog, SaveDataDialog, SavePictureDialog1

import os.path
import warnings
warnings.filterwarnings("ignore")
import AR_neurokit2 as nk
from src.Domain.OPLog.OPLog  import OPLogTask, OPType, OPLog
from src.Infrastructure.DB.SQLLiteAccessor import SQLLiteDB_Only_MainTread
import numpy as np
import pandas as pd
import traceback
from scipy import signal
import os
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
import time
from .utils import setup_short_cut,_highlight_current_amplitude,probe_pg
from src.Infrastructure.QLWidgets.QLGifProgressBar import GifProgressBar
from .left_time_overlay import LeftTimeOverlay
from .CustomControls import CollapsibleSidebar
import matplotlib as mpl
# 大数据保存时用分片渲染 & 路径简化，降内存/提速
mpl.rcParams['agg.path.chunksize'] = 10000
mpl.rcParams['path.simplify'] = True
mpl.rcParams['path.simplify_threshold'] = 0.2

def process_emg_data(raw, selected_channel, time_range, progress_callback=None):
    """
    处理EMG数据并返回计算结果

    Parameters:
    -----------
    raw : mne.io.Raw
        原始MNE数据对象
    selected_channel : str
        要处理的EMG通道名
    progress_callback : callable, optional
        进度回调函数

    Returns:
    --------
    dict : 包含处理结果的字典
    """
    sampling_rate = raw.info['sfreq']
    total_steps = 3
    current_step = 0
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

        # 确保时间格式一致
        start_time = start_time.replace(tzinfo=timezone.utc)
        end_time = end_time.replace(tzinfo=timezone.utc)
        meas_date = meas_date.replace(tzinfo=timezone.utc)

        # 计算起始和结束索引
        start_idx = int(
            ((start_time - raw.info['meas_date'].replace(tzinfo=timezone.utc)).total_seconds()) * sampling_rate)
        end_idx = int(((end_time - raw.info['meas_date'].replace(
            tzinfo=timezone.utc)).total_seconds()) * sampling_rate) + sampling_rate
        # 添加边界检查
        if end_idx >= len(raw.times):
            end_idx = len(raw.times) - 1

        if end_idx <= start_idx:
            raise ValueError("Invalid time range: end time must be greater than start time.")

        # 裁剪数据
        raw = raw.copy().crop(tmin=start_idx / sampling_rate, tmax=end_idx / sampling_rate)

    # 1. 数据提取
    index = raw.ch_names.index(selected_channel)
    emg_signal, _ = raw[index, :]
    emg_signal = emg_signal.squeeze()
    if progress_callback:
        current_step += 1
        progress_callback(current_step, total_steps)

    # 2. 信号滤波
    nyquist = sampling_rate / 2.0
    low_freq = 20.0
    high_freq = min(450.0, nyquist - 1)

    # 检查频率有效性
    low_cut = low_freq / nyquist
    high_cut = high_freq / nyquist
    if low_cut >= high_cut or high_cut >= 1:
        raise ValueError(f"Invalid filter frequencies. Low cut: {low_cut}, High cut: {high_cut}")

    b, a = signal.butter(4, [low_cut, high_cut], btype='band')
    filtered_emg = signal.filtfilt(b, a, emg_signal)
    if progress_callback:
        current_step += 1
        progress_callback(current_step, total_steps)

    # 3. 计算包络
    envelope = nk.emg_amplitude(filtered_emg)
    if progress_callback:
        current_step += 1
        progress_callback(current_step, total_steps)

    return {
        'emg_signal': emg_signal,
        'filtered_emg': filtered_emg,
        'envelope': envelope,
        'sampling_rate': sampling_rate,
        'filter_freqs': (low_freq, high_freq)
    }

class EMGAnalysisWorker(QThread):
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
            results = process_emg_data(self.raw, self.channel,self.time_range, progress_callback)
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

class Ui_EMG_compute(QWidget):
    page_changed = pyqtSignal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.raw = None
        self.page_duration = 3600
        self.current_page = 1
        self.total_pages =1
        self.time_range = None
        self.manual_y_range = None  # 初始使用自动幅度范围 y轴
        self.setupUi()
        self.win = None

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

        self.is_manually_changing_page = False  # 用于标记是否手动更改页码

        # 初始化 EMG图像显示区域
        self.emg_widget = pg.PlotWidget()
        self.emg_widget.setBackground('w')
        # 设置边距：左、上、右、下边距
        self.emg_widget.getPlotItem().setContentsMargins(100, 10, 30, 10)
        self.emg_widget.setLabel('left', 'Amplitude(μV)')
        self.emg_widget.setTitle('Raw EMG Signal', color='k')
        # 隐藏 x 轴和 y 轴线，但保留刻度标签
        self.emg_widget.getAxis('bottom').setPen(None)
        self.emg_widget.getAxis('left').setPen(None)
        self.emg_widget.getAxis('bottom').setTextPen(pg.mkPen('k'))
        self.emg_widget.getAxis('left').setTextPen(pg.mkPen('k'))
        self.emg_widget.setMouseEnabled(x=True, y=False)  # 禁用缩放/平移
        self.emg_widget.setMenuEnabled(False)  # 禁用右键菜单
        self.emg_widget.getPlotItem().hideButtons()
        self.emg_widget.setMinimumHeight(300)  # 设置最小高度
        self.main_layout.addWidget(self.emg_widget)

        # 初始化 EMG分析结果显示区域 (envelope_widget)
        # 使用自定义坐标轴
        self.envelope_time_axis = RelativeTimeAxis(orientation='bottom')
        self.envelope_time_axis.setPen(None)
        self.envelope_time_axis.setTextPen(pg.mkPen('k'))

        # 将 axisItems 传入 PlotWidget
        self.envelope_widget = pg.PlotWidget(axisItems={'bottom': self.envelope_time_axis})
        self.envelope_widget.setBackground('w')
        # 设置边距：左、底部、右、顶部
        self.envelope_widget.getPlotItem().setContentsMargins(100, 10, 30, 10)
        self.envelope_widget.setLabel('left', 'Amplitude(μV)')
        self.envelope_widget.setLabel('bottom', 'Time (s)')
        self.envelope_widget.setTitle('EMG Envelope', color='k')
        # 隐藏 x 轴和 y 轴线，但保留刻度标签
        self.envelope_widget.getAxis('bottom').setPen(None)
        self.envelope_widget.getAxis('left').setPen(None)
        # 设置坐标轴字体颜色为深色
        self.envelope_widget.getAxis('bottom').setTextPen(pg.mkPen('k'))
        self.envelope_widget.getAxis('left').setTextPen(pg.mkPen('k'))
        self.envelope_widget.setMouseEnabled(x=True, y=False)  # 禁用缩放/平移S
        self.envelope_widget.setMenuEnabled(False)  # 禁用右键菜单
        self.envelope_widget.getPlotItem().hideButtons()
        self.envelope_widget.setMinimumHeight(300)  # 设置最小高度
        self.main_layout.addWidget(self.envelope_widget)
        self.env_left_label = LeftTimeOverlay(self.emg_widget,  # 第二张图
                                              anchor_parent=self.emg_widget,
                                              corner='bottom-left', offset=(16, 0),
                                              meas_date=None, dt_fmt='%Y-%m-%d %H:%M:%S', show_ms=True)

        # 添加时间滚动条
        self.slider_widget = TimeSliderWidget()
        self.main_layout.addWidget(self.slider_widget)
        self.slider_widget.time_slider.setMinimum(0)
        self.slider_widget.time_slider.setValue(0)
        self.slider_widget.time_slider.valueChanged.connect(self.scroll_time)

        self.results = []
        def _sync_from_emg():
            if self._emg_env_syncing:
                return
            self._emg_env_syncing = True
            try:
                x0, x1 = self.emg_widget.getPlotItem().vb.viewRange()[0]
                self.envelope_widget.setXRange(x0, x1, padding=0)
            finally:
                self._emg_env_syncing = False

        def _sync_from_env():
            if self._emg_env_syncing:
                return
            self._emg_env_syncing = True
            try:
                x0, x1 = self.envelope_widget.getPlotItem().vb.viewRange()[0]
                self.emg_widget.setXRange(x0, x1, padding=0)
            finally:
                self._emg_env_syncing = False

        self.emg_widget.getPlotItem().vb.sigRangeChanged.connect(lambda *_: _sync_from_emg())
        self.envelope_widget.getPlotItem().vb.sigRangeChanged.connect(lambda *_: _sync_from_env())

        self._emg_env_syncing = False

        # —— RubberBand & 高亮（跨两图公用）——
        self._rb = None
        self._rb_active = False
        self._rb_origin = None
        self._rb_host = self  # 以本页面 widget 作为“画布”，能覆盖上下两张图
        self._min_px = 8  # 框选最小像素宽度
        self._min_sec = 0.02  # 框选最小时间宽度（秒）

        self._hl_pen = pg.mkPen(100, 149, 237, 180, width=1)  # 高亮样式
        self._hl_brush = pg.mkBrush(100, 149, 237, 60)

        # 记录高亮与弹窗映射：dialog -> {"plot": plot, "region": region}
        self._zoom_markers = {}
        self._zoom_windows = []

        # 记录所有放大弹窗的 viewport -> ViewBox 映射
        self._zoom_viewports = set()
        self._zoom_viewport_map = {}

        # 两个 viewport 都装过滤器（只影响这两张图）
        self.emg_widget.viewport().installEventFilter(self)
        self.envelope_widget.viewport().installEventFilter(self)

    def setupUi(self):
        # 创建主布局
        self.main_layout = QVBoxLayout(self)

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
        self.menu_amplitude.setTitle("Raw EMG Signal")
        self.menu_heart_rate = QMenu()
        self.menu_heart_rate.setTitle("EMG Envelope")

        self.menu_amplitude.setStyleSheet(ControlStyle.get_menuBar_style())
        self.menu_heart_rate.setStyleSheet(ControlStyle.get_menuBar_style())

        ControlStyle.get_font_size(self.menu_amplitude, 10)
        ControlStyle.get_font_size(self.menu_heart_rate, 10)

        # 将一级菜单添加到菜单栏中
        main_menu.addMenu(self.menu_amplitude)
        main_menu.addMenu(self.menu_heart_rate)

        self.toolButton_amplitude_set.setMenu(main_menu)

        # Raw EMG Signal 振幅范围选项
        values = ["Auto", "±50", "±100", "±200", "±500"]
        for value in values:
            action = QAction(value, self)
            ControlStyle.get_font_size(action, 10)
            self.menu_amplitude.addAction(action)
            action.triggered.connect(
                lambda checked, val=value: self.on_amplitude_changed(val)
            )

        # EMG Envelope 振幅范围选项
        values = ["Auto", "±200", "±500", "±1000", "±2000"]
        for value in values:
            action = QAction(value, self)
            ControlStyle.get_font_size(action, 10)
            self.menu_heart_rate.addAction(action)
            action.triggered.connect(
                lambda checked, val=value: self.emg_envelope_changed(val)
            )
        self.menu_amplitude.aboutToShow.connect(
            lambda: _highlight_current_amplitude(self.menu_amplitude, lambda: probe_pg(self.emg_widget))
        )
        self.menu_heart_rate.aboutToShow.connect(
            lambda: _highlight_current_amplitude(self.menu_heart_rate, lambda: probe_pg(self.envelope_widget))
        )

        control_layout = QHBoxLayout()
        control_layout.addStretch()
        control_layout.addWidget(self.toolButton_amplitude_set)
        # 添加一个固定大小的空白区域
        spacer_fixed = QSpacerItem(20, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        control_layout.addSpacerItem(spacer_fixed)
        self.main_layout.addLayout(control_layout)
        
        self.setLayout(self.main_layout)

    def plot_emg_results(self, results):
        """
        绘制EMG分析结果

        Parameters:
        -----------
        results : dict
            process_emg_data返回的结果字典，需包含sampling_rate
        """
        self.results = results
        self.envelope_widget.clear()
        self.emg_widget.clear()

        # 原始EMG信号
        self.emg_plot = self.emg_widget.plot(pen=pg.mkPen('k', width=0.5), name="EMG Signal")

        # EMG分析
        self.envelope_plot = self.envelope_widget.plot(pen=pg.mkPen('k', width=0.5), name="EMG Envelope")

        self.scroll_time()

    def scroll_time(self):
        
        # 获取时间范围的起始时间
        start, end = self.time_range
        # 将 start 转换为 Unix 时间戳
        start_timestamp = start.toSecsSinceEpoch()

        # 获取当前滚动条位置并加上起始时间
        pos = self.slider_widget.time_slider.value()
        start_time = pos
        end_time = start_time + self.page_duration

        # 护栏
        self._apply_page_guardrails(self.emg_widget, start_time, end_time)
        self._apply_page_guardrails(self.envelope_widget, start_time, end_time)

        # 更新当前页码
        if not self.is_manually_changing_page:
            # self.current_page = int(start_time / self.page_duration) + 1
            self.get_current_page()
            self.page_changed.emit(self.current_page)

        base_dt = self.time_range[0].toPyDateTime()
        if hasattr(self, 'envelope_time_axis'):
            self.envelope_time_axis.set_meas_date(base_dt)

        # # 创建4个均匀分布的时间点
        # time_ticks = np.linspace(start_time, end_time, 4)
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
        # # 设置刻度位置和标签
        # axis = self.envelope_widget.getAxis('bottom')
        # ticks = [(time_ticks[i], time_strings[i]) for i in range(len(time_ticks))]
        # axis.setTicks([ticks, ticks])
        self.envelope_widget.getAxis('bottom').setTicks(None)
        if not hasattr(self, "_env_axis_locked"):
            from PyQt5.QtCore import QTimer
            axis = self.envelope_widget.getAxis('bottom')
            axis.setStyle(autoExpandTextSpace=False)
            QTimer.singleShot(0, lambda a=axis: a.setHeight(a.height()))
            self._env_axis_locked = True
        # base_dt = self.time_range[0].toPyDateTime()  # 本页起始的绝对时间
        if hasattr(self, 'env_left_label'):
            self.env_left_label.set_meas_date(base_dt)
        self.emg_widget.getAxis('bottom').setTicks([])  # 清除左侧x轴刻度

        sampling_rate = self.results['sampling_rate']
        x_time = np.arange(len(self.results['emg_signal'])) / sampling_rate  # 转换为秒
        time_mask = (x_time >= start_time) & (x_time <= end_time)

        self.envelope_widget.setUpdatesEnabled(False)  # 禁用更新
        self.emg_widget.setUpdatesEnabled(False)  # 禁用更新

        #添加降采样
        envelope_times = x_time[time_mask]
        envelope_values = self.results['envelope'][time_mask]
        emg_times = x_time[time_mask]
        emg_data = self.results['emg_signal'][time_mask]

        # 应用降采样（针对大数据量）
        if len(envelope_times) > 1800000:
            envelope_times, envelope_values = self.downsample_data(
                envelope_times, envelope_values
            )
        if len(emg_times) > 1800000:
            emg_times, emg_data = self.downsample_data(
                emg_times, emg_data
            )        # 更新图像

        self.envelope_plot.setData(envelope_times, envelope_values)
        self.emg_plot.setData(emg_times ,emg_data)

        self.envelope_widget.setUpdatesEnabled(True)  # 启用更新
        self.emg_widget.setUpdatesEnabled(True)  # 启用更新
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

    def _downsample_envelope(self, x, y, max_points):
        """
        将 (x,y) 降到 <= max_points：每个窗口保留 min/max（包络式），
        视觉近似无损，但渲染/保存极大提速、降内存。
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

        # 交错输出：min,max，保留峰/谷
        x_ds = np.empty(y_min.size * 2, dtype=x.dtype)
        y_ds = np.empty(y_min.size * 2, dtype=y.dtype)
        x_ds[0::2] = x_mid;
        x_ds[1::2] = x_mid
        y_ds[0::2] = y_min;
        y_ds[1::2] = y_max

        # 补上尾巴
        if n_fit < n:
            x_ds = np.concatenate([x_ds, x[n_fit:]])
            y_ds = np.concatenate([y_ds, y[n_fit:]])
        return x_ds, y_ds
    def save_figure(self):
        """保存当前显示的图形"""
        wait_box = None
        try:
            from datetime import datetime
            # 获取当前日期和时间
            current_time = datetime.now()
            formatted_time = current_time.strftime("%Y-%m-%d-%H%M%S")
            # 显示保存对话框
            dialog = SavePictureDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                # 获取保存参数
                params = dialog.get_save_parameters()
                save_path = params['path']
                img_format = params['format'].lower().replace('.', '')
                dpi = params['resolution']
                # 创建保存目录
                default_folder = "EMG_Analysis_pic"
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

                # 保存 EMG Envelope 图片
                self.save_plot_widget(self.envelope_widget , save_dir,
                                      f"EMGEnvelope{formatted_time}.{img_format}" , dpi, img_format)

                #保存Raw EMG Signal
                self.save_plot_widget(self.emg_widget , save_dir,
                                      f"EMGSignal{formatted_time}.{img_format}" , dpi, img_format)
                wait_box.close()
                # 显示成功消息
                QMessageBox.information(
                    self.win,
                    "Save Success",
                    f"Figure has been saved to:\n{save_dir}"
                )
                QLLogging.log.info(f"EMG figures saved to: {save_dir}")
                OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'Save Pic', 0)
                return True

        except Exception as e:
            # 异常时先关等待框，再报错
            try:
                if wait_box and wait_box.isVisible():
                    wait_box.close()
            finally:
                pass
            # 显示错误消息
            stack_trace = traceback.format_exc()
            QLLogging.log.error(
                f"Error saving EMGAnalysis analysis figure:{str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )

            QMessageBox.critical(
                self.win,
                "Error",
                f"Failed to save figure: {str(e)}"
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

    def save_plot_widget(self, plot_widget, save_dir, filename, dpi, img_format):
        """
        保存 plot_widget 图片：
        1) 同步 PyQtGraph 当前可见范围（含 y 轴限制 & x 轴窗口）
        2) 针对超大数据做包络式降采样，避免保存时内存暴涨/卡死
        """
        try:
            result_path = os.path.join(save_dir, filename)

            # --- PyQtGraph -> Matplotlib ---
            fig, ax = plt.subplots(figsize=(14, 6), dpi=dpi)
            plot_item = plot_widget.plotItem

            # 先取“当前可见范围”（x、y 都要）
            x_range, y_range = None, None
            try:
                xr, yr = plot_item.vb.viewRange()
                x_range, y_range = xr, yr
            except Exception:
                pass

            # 1) 复制所有曲线（含大数据降采样）
            for curve in plot_item.curves:
                x, y = curve.getData()
                if x is None or y is None or len(x) == 0:
                    continue

                # 只在需要时做“包络式”降采样
                fig_w_px = int(fig.get_figwidth() * fig.get_dpi())
                max_pts = max(20000, fig_w_px * 4)
                if len(y) > max_pts:
                    x, y = self._downsample_envelope(x, y, max_pts)

                line, = ax.plot(
                    x, y,
                    label=curve.opts.get('name', ''),
                    color=curve.opts.get('pen', 'k').color().name(),
                    linewidth=curve.opts.get('pen', None).width() if hasattr(curve.opts.get('pen', None),
                                                                             'width') else 1.0
                )
                # 小优化：更省内存/更快（对 PNG 同样安全）
                line.set_antialiased(False)
                line.set_rasterized(False)

            # 2) 复制坐标轴/标题
            ax.set_xlabel(plot_item.axes["bottom"]["item"].label.toPlainText())
            ax.set_ylabel(plot_item.axes["left"]["item"].label.toPlainText())
            ax.set_title(plot_item.titleLabel.text if plot_item.titleLabel else "")
            ax.margins(x=0, y=0)

            # 3) 复制网格
            if plot_item.showGrid(x=True, y=True):
                ax.grid(True, linestyle='--', alpha=0.7)

            # 4) 复制图例
            if plot_item.legend is not None:
                ax.legend()

            # === 5) 同步可见范围（关键：把当前看的 y 轴限制也保存下来） ===
            if x_range and len(x_range) == 2:
                ax.set_xlim(x_range[0], x_range[1])
            if y_range and len(y_range) == 2:
                ax.set_ylim(y_range[0], y_range[1])

            # 6) 应用保存参数
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
            QLLogging.log.exception(f"save widget plot, error: {e}")

    def get_current_page(self):
        """
        获取当前页码。
        """
        ts_value = self.slider_widget.time_slider.value()
        ts_min = self.slider_widget.time_slider.minimum()
        ts_max = self.slider_widget.time_slider.maximum()
        # 处理滑块范围为0的情况
        if ts_max <= ts_min:
            self.current_page = 1  # 只有一页
            return
        page = int((ts_value - ts_min) / (ts_max - ts_min) * self.total_pages + 1)
        self.current_page = min(page, self.total_pages)

    def show_first_page(self):
        self.current_page = 1
        # 直接计算对应页的起始时间位置
        pos = (self.current_page - 1) * self.page_duration
        self.slider_widget.time_slider.setValue(int(pos))
        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'show_first_page', 0)

    def show_last_page(self):
        self.current_page = self.total_pages

        self.is_manually_changing_page = True
        pos = (self.current_page - 1) * self.page_duration
        self.slider_widget.time_slider.setValue(int(pos))
        self.page_changed.emit(self.current_page)
        self.is_manually_changing_page = False

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
        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'show_next_page', 0)

    def set_current_page(self, page):
        """
        设置显示指定页，并更新画面。
        """
        if 1 <= page <= self.total_pages:
            self.current_page = page
        pos = (self.current_page - 1) * self.page_duration
        self.slider_widget.time_slider.setValue(int(pos))

    def set_page_duration(self, seconds):
        """
        设置每页显示的秒数，并跳转到第一页重新显示画面。
        """
        self.page_duration = seconds
        self.current_page = 1

        start, end = self.time_range
        self.total_duration = end.toSecsSinceEpoch() - start.toSecsSinceEpoch()
        self.total_pages = int(np.ceil(self.total_duration / self.page_duration))
        self.slider_widget.time_slider.setMaximum(int(self.total_duration - seconds))

        # 更新图像
        # pos = self.slider_widget.time_slider.value()
        # start_time = pos
        # end_time = start_time + self.page_duration

        # 更新所有子图的显示范围
        # sampling_rate = self.results['sampling_rate']
        # x_time = np.arange(len(self.results['emg_signal'])) / sampling_rate  # 转换为秒
        # time_mask = (x_time >= start_time) & (x_time <= end_time)

        # self.envelope_widget.setUpdatesEnabled(False)  # 禁用更新
        # self.emg_widget.setUpdatesEnabled(False)  # 禁用更新
        # self.envelope_plot.setData(x_time[time_mask], self.results['envelope'][time_mask])
        # self.emg_plot.setData(x_time[time_mask], self.results['emg_signal'][time_mask])
        # self.envelope_widget.setUpdatesEnabled(True)  # 启用更新
        # self.emg_widget.setUpdatesEnabled(True)  # 启用更新

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
        emg_vb = self.emg_widget.getPlotItem().getViewBox()
        x_min, x_max = emg_vb.viewRange()[0] # 获取当前x轴范围
        x, y = self.emg_plot.getData()  # 获取当前数据
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
                emg_vb.setYRange(ymin - margin, ymax + margin)
                emg_vb.enableAutoRange(axis=pg.ViewBox.YAxis)
            else:
                emg_vb.enableAutoRange(axis=pg.ViewBox.YAxis)  # 自动范围
        else:
            try:
                amp = float(value.lstrip('±'))
                emg_vb.setYRange(-amp, amp, padding=0)  # 设置手动范围
            except ValueError:
                emg_vb.enableAutoRange(axis=pg.ViewBox.YAxis)  # 自动范围

    def emg_envelope_changed(self, value):
        """
        处理振幅范围选择变化

        Parameters:
        -----------
        value : str
            下拉框选中的值，格式为 "Auto" 或 "±数值"
        """
        envelope_vb = self.envelope_widget.getPlotItem().getViewBox()
        x_min, x_max = envelope_vb.viewRange()[0]  # 获取当前x轴范围
        x, y = self.envelope_plot.getData()  # 获取当前数据
        # 根据当前x轴范围筛选数据
        if value == "Auto":
            # 获取当前显示范围内的数据
            mask = (x >= x_min) & (x <= x_max)
            visible_ydata = y[mask]

            if len(visible_ydata) > 0:
                # 计算数据范围
                ymin = visible_ydata.min()
                ymax = visible_ydata.max()

                margin = (ymax - ymin) * 0.1
                envelope_vb.setYRange(ymin - margin, ymax + margin)
                envelope_vb.enableAutoRange(axis=pg.ViewBox.YAxis)
            else:
                envelope_vb.enableAutoRange(axis=pg.ViewBox.YAxis)  # 自动范围
        else:
            try:
                amp = float(value.lstrip('±'))
                envelope_vb.setYRange(0, amp, padding=0)  # 设置手动范围
            except ValueError:
                envelope_vb.enableAutoRange(axis=pg.ViewBox.YAxis)  # 自动范围

    def eventFilter(self, obj, event):
        # 放大弹出框里的 Ctrl+滚轮：只缩放 Y 轴 ====
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

            # 普通滚轮等，交给默认处理（pyqtgraph 会按 x=True, y=False 缩放 X）
            return super().eventFilter(obj, event)
        # 只处理 EMG 上下两图
        vp_list = [self.emg_widget.viewport(), self.envelope_widget.viewport()]
        if obj not in vp_list:
            return super().eventFilter(obj, event)

        # —— Shift + 左键按下：开始跨图框选 ——
        if (event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton
                and (event.modifiers() & Qt.ShiftModifier)):
            self._rb_active = True
            self._rb_origin = event.pos()
            if self._rb is None:
                self._rb = QRubberBand(QRubberBand.Rectangle, self._rb_host)
            # 起点映射到 host 坐标
            top_left = self._rb_host.mapFromGlobal(obj.mapToGlobal(self._rb_origin))
            self._rb.setGeometry(QRect(top_left, QSize()))
            self._rb.show()
            return True

        # —— 拖动：更新矩形 ——
        if (event.type() == QEvent.MouseMove
                and self._rb_active and self._rb is not None and self._rb.isVisible()):
            cur = self._rb_host.mapFromGlobal(obj.mapToGlobal(event.pos()))
            origin = self._rb_host.mapFromGlobal(obj.mapToGlobal(self._rb_origin))
            rect = QRect(origin, cur).normalized()
            self._rb.setGeometry(rect)
            return True

        # —— 左键松开：结束框选，命中几张图就开几个放大窗 ——
        if (event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton):
            if not (self._rb_active and self._rb and self._rb.isVisible()):
                return False  # 普通点击，放过
            sel_rect_host = self._rb.geometry()
            self._rb.hide()
            self._rb_active = False

            # 1) 像素宽度阈值
            if sel_rect_host.width() < self._min_px:
                return True

            # 2) 计算命中的图：与选框在 host 坐标下有交集的 viewport
            def vp_rect_in_host(pw):
                vp = pw.viewport()
                tl = self._rb_host.mapFromGlobal(vp.mapToGlobal(vp.rect().topLeft()))
                return QRect(tl, vp.rect().size())

            hits = []
            for pw in [self.emg_widget, self.envelope_widget]:
                if vp_rect_in_host(pw).intersects(sel_rect_host):
                    hits.append(pw)
            if not hits:
                return True

            # 3) host X -> 各 plot 的数据 X
            def host_x_to_plot_x(host_x, plot):
                # 取该 plot viewport 的中心 y 来反算 x
                vp = plot.viewport()
                vp_center = vp.rect().center()
                center_host = self._rb_host.mapFromGlobal(vp.mapToGlobal(vp_center))
                pt_host = QPoint(host_x, center_host.y())
                pt_vp = vp.mapFromGlobal(self._rb_host.mapToGlobal(pt_host))
                scene_pt = plot.mapToScene(pt_vp)
                data_pt = plot.getPlotItem().vb.mapSceneToView(scene_pt)
                return data_pt.x()

            x_min = min(host_x_to_plot_x(sel_rect_host.left(), hits[0]),
                        host_x_to_plot_x(sel_rect_host.right(), hits[0]))
            x_max = max(host_x_to_plot_x(sel_rect_host.left(), hits[0]),
                        host_x_to_plot_x(sel_rect_host.right(), hits[0]))

            vb = hits[0].getPlotItem().vb
            vis_x0, vis_x1 = vb.viewRange()[0]
            x_min = max(vis_x0, min(x_min, vis_x1))
            x_max = max(vis_x0, min(x_max, vis_x1))

            # 4) 时间阈值
            if (x_max - x_min) < self._min_sec:
                return True

            # 5) 对命中的每张图：高亮 + 弹窗
            for pw in hits:
                region = pg.LinearRegionItem(values=(x_min, x_max),
                                             brush=self._hl_brush, pen=self._hl_pen, movable=False)
                pw.addItem(region)
                self._show_zoom_dialog_for_plot(pw, x_min, x_max, region)
            return True

        return super().eventFilter(obj, event)


    def _show_zoom_dialog_for_plot(self, src_plot, x_min, x_max, region):
        dialog = QDialog(self)
        title = "EMG" if src_plot is self.emg_widget else "Envelope"
        meas_date = self.time_range[0].toPyDateTime()
        sec_start = round(float(x_min), 3)
        sec_end = round(float(x_max), 3)
        ms_start = int(round(sec_start * 1000))
        ms_end = int(round(sec_end * 1000))
        abs_start = meas_date + datetime.timedelta(milliseconds=ms_start)
        abs_end = meas_date + datetime.timedelta(milliseconds=ms_end)
        start_str = abs_start.strftime("%Y-%m-%d %H:%M:%S") + f".{ms_start % 1000:03d}"
        end_str = abs_end.strftime("%Y-%m-%d %H:%M:%S") + f".{ms_end % 1000:03d}"
        dialog.setWindowTitle(f"{title}  [{start_str}  ~  {end_str}]")
        layout = QVBoxLayout(dialog)
        from .left_time_overlay import DateAxis
        date_axis = DateAxis(meas_date, orientation='bottom')
        zoom_plot = pg.PlotWidget(axisItems={'bottom': date_axis})
        layout.addWidget(zoom_plot)
        dialog.resize(900, 320)

        # 复制曲线/图像
        src_pi = src_plot.getPlotItem()
        dst_pi = zoom_plot.getPlotItem()
        for it in src_pi.listDataItems():
            try:
                x, y = it.getData()
            except Exception:
                continue
            if x is None or y is None or len(x) == 0:
                continue
                # 只取框选区间
            mask = (x >= x_min) & (x <= x_max)
            if not getattr(mask, "any", lambda: False)():
                continue

            x_sel = x[mask]
            y_sel = y[mask]
            if len(x_sel) == 0:
                continue

            # （可选）大数据做一次轻量抽稀，避免放大窗卡顿
            try:
                # 10 万点上限，可按需调整
                x_sel, y_sel = self._downsample_envelope(x_sel, y_sel, max_points=100_000)
            except Exception:
                pass
            pen = it.opts.get('pen', None)
            dst_pi.addItem(pg.PlotDataItem(x=x_sel, y=y_sel, pen=pen))
        for it in src_pi.items:
            if isinstance(it, pg.ImageItem):
                img = pg.ImageItem()
                img.setImage(it.image)
                img.setTransform(it.transform())
                dst_pi.addItem(img)

        zoom_plot.setBackground("w")
        zoom_plot.showGrid(x=True, y=True, alpha=0.3)
        zoom_plot.setMouseEnabled(x=True, y=False)  # 放大窗也能横向滚轮缩放
        zoom_plot.setXRange(x_min, x_max, padding=0)
        zoom_plot.setMenuEnabled(False)

        # 👉 让放大弹窗支持 Ctrl+滚轮单独缩放 Y 轴
        vp = zoom_plot.viewport()
        vp.installEventFilter(self)
        self._zoom_viewports.add(vp)
        self._zoom_viewport_map[vp] = zoom_plot.getPlotItem().vb
        dialog._zoom_viewport = vp  # 方便关闭时清理

        # 关闭 -> 清理对应高亮
        dialog.finished.connect(lambda _: self._cleanup_zoom_dialog(dialog))
        dialog.show()

        self._zoom_windows.append(dialog)
        self._zoom_markers[dialog] = {"plot": src_plot, "region": region}

    def _cleanup_zoom_dialog(self, dialog):
        info = self._zoom_markers.pop(dialog, None)
        if info:
            plot, region = info["plot"], info["region"]
            try:
                plot.removeItem(region)
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

        try:
            self._zoom_windows.remove(dialog)
        except ValueError:
            pass

    def _apply_page_guardrails(self, plot, page_start: float, page_end: float):
        """把某个 PlotWidget 的可见/可拖动范围限制在当前页窗口内"""
        try:
            if page_end <= page_start:
                return
            vb = plot.getPlotItem().vb
            eps = 1e-6
            vb.setLimits(
                xMin=page_start - eps,
                xMax=page_end + eps,
                minXRange=min(0.2, max(0.01, (page_end - page_start) * 0.1)),  # 最小可到一页宽的10%
                maxXRange=(page_end - page_start)  # 最大不超过一整页
            )
            plot.setXRange(page_start, page_end, padding=0)
        except Exception:
            pass

class EMGAnalysisViewer(QWidget):
    def __init__(self,title, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EMG Analysis")
        self.setStyleSheet(ControlStyle.get_widget_style())
        self.setGeometry(100, 100, 1440, 900)  # 初始窗口大小
        self.title = title

        self.init_ui()
        self.connect_actions()

        self.win = None

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
        self.nav_buttons_widget = NavButtonsWidget(parent=self)  # 占位控件，可在子类中替换
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
        label_emg.setText("EMG")
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
        #self.display_area.setAlignment(Qt.AlignCenter)

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

        # progressBar_vlayout.addLayout(progressBar_label_hlayout)
        progressBar_vlayout.addWidget(self.progressBar)
        progressBar_vlayout.addWidget(self.label_progressBar)
        self.h_layout.addWidget(self.progressBar_widget)
        self.progressBar_widget.hide()

        # 显示图像的页面
        self.viewer = Ui_EMG_compute()
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

        self.save_pic_btn = QPushButton("Save Pic")
        self.save_pic_btn.setStyleSheet(ControlStyle.get_pushButton_style_white())
        self.save_pic_btn.setMinimumSize(145, 40)
        ControlStyle.get_font_size(self.save_pic_btn, 10)

        self.save_data_btn = QPushButton("Save Data")
        self.save_data_btn.setStyleSheet(ControlStyle.get_pushButton_style_white())
        self.save_data_btn.setMinimumSize(145, 40)
        ControlStyle.get_font_size(self.save_data_btn, 10)

        self.disable_save_buttons()

        bottom_layout.addWidget(self.analyse_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.save_pic_btn)
        bottom_layout.addWidget(self.save_data_btn)

        center_and_bottom_layout.addLayout(bottom_layout)

        # 将中央和底部布局添加到主体布局
        content_layout.addWidget(center_and_bottom_widget,  stretch=7)  # 中央显示区域占 7 份

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

        # 默认选择第一个通道
        if len(channel_names) > 0:
            self.combobox_emg.setCurrentIndex(1)
    
    def import_raw(self, raw):
        """
        导入原始数据，并设置默认的时间范围。
        """
        self.raw = raw.copy()

        # 获取原始数据的起始时间和终止时间
        self.meas_dat = raw.info['meas_date'].replace(tzinfo=None)  # 起始时间
        self.total_duration =  int(raw.times[-1])  # 转换为整数秒   数据总时长（秒）
        self.end_time = self.meas_dat + datetime.timedelta(seconds=self.total_duration)  # 终止时间

        # 设置时间选择器的默认时间范围
        self.time_selector.set_time_range(self.meas_dat, self.end_time)
        self.time_selector.set_max_time(self.end_time)
        self.time_selector.set_min_time(self.meas_dat)

        # 获取所有通道名称        ##根据数据设置通道
        self.update_channel_list()

    def connect_actions(self):
        """连接按钮的槽函数"""
        self.analyse_btn.clicked.connect(self.on_analyse_clicked)  #开始分析按钮
        self.save_data_btn.clicked.connect(self.save_data)  #保存数据按钮
        self.save_pic_btn.clicked.connect(self.save_figure)  #保存图片按钮

        self.nav_buttons_widget.first_pushButton.clicked.connect(self.viewer.show_first_page) #第一页
        self.nav_buttons_widget.last_pushButton.clicked.connect(self.viewer.show_last_page)
        self.nav_buttons_widget.button_previous.clicked.connect(self.viewer.show_prev_page)   #上一页
        self.nav_buttons_widget.button_next.clicked.connect(self.viewer.show_next_page)     #下一页
        
        self.viewer.page_changed.connect(self.nav_buttons_widget.set_current_page)
        self.nav_buttons_widget.combo_time_scale.currentTextChanged.connect(self.time_scale_change) #一页大小
        self.nav_buttons_widget.button_goto_epoch.clicked.connect(self.update_display_goto_epoch) #跳转到指定页面

    def save_data(self):
        """保存EMG分析结果"""
        self.disable_buttons()
        try:
            from datetime import datetime
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
                default_folder = "EMG_Analysis_data"
                save_dir = os.path.join(save_path, default_folder)
                os.makedirs(save_dir, exist_ok=True)

                # 获取分析结果
                results = process_emg_data(
                    self.raw,
                    self.combobox_emg.currentText(),
                    self.time_selector.get_time_range()
                )

                # 创建数据字典
                data_dict = {
                    'Time(s)': np.arange(len(results['emg_signal'])) / results['sampling_rate'],
                    'EMG_Raw': results['emg_signal'],
                    'EMG_Filtered': results['filtered_emg'],
                    'EMG_Envelope': results['envelope']
                }

                # 根据不同格式保存数据
                if data_format == '.csv':
                    file_path = os.path.join(save_dir, f'emg_data{formatted_time}.csv')
                    pd.DataFrame(data_dict).to_csv(file_path, index=False)
                elif data_format == '.npy':
                    file_path = os.path.join(save_dir, f'emg_data{formatted_time}.npy')
                    np.save(file_path, data_dict)

                # elif data_format == '.npy':
                #     file_path = os.path.join(save_dir, 'emg_data.npy')
                #     # 保存完整的数据结构
                #     save_dict = {
                #         'data': data_dict,
                #         'sampling_rate': self.raw.info['sfreq'],
                #         'channels': list(data_dict.keys())
                #     }
                #     np.save(file_path, save_dict, allow_pickle=True)

                elif data_format == '.mat':
                    from scipy.io import savemat
                    file_path = os.path.join(save_dir, f'emg_data{formatted_time}.mat')
                    # 转换为MATLAB兼容格式
                    save_dict = {
                        'data': data_dict,
                        'sampling_rate': self.raw.info['sfreq'],
                        'channels': list(data_dict.keys())
                    }
                    savemat(file_path, save_dict)
                # 显示成功消息
                QMessageBox.information(
                    self.win,
                    "Save Success",
                    f"Analysis results have been saved to:\n{file_path}"
                )
                QLLogging.log.info(f"EMGAnalysis results saved to: {file_path}")
                OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'Save Data', 0)
                return True

        except Exception as e:
            stack_trace = traceback.format_exc()
            QLLogging.log.error(
                f"Failed to save EMGAnalysis results: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )
            QMessageBox.critical(
                self.win,
                "Error",
                f"Failed to save analysis results: {str(e)}"
            )
            return False

        finally:
            self.enable_buttons()

    def save_figure(self):
        self.disable_buttons()
        import time
        start_time1 = time.time()
        self.viewer.save_figure()
        end_time = time.time() - start_time1
        print("总时长：", end_time)
        self.enable_buttons()
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

        except Exception as e:
            print(f"Error in update_display_goto_epoch: {str(e)}")

    def time_scale_change(self):
        """
            当 Time Scale 复选框的值改变时，更新页面持续时间。
            """
        # 获取当前选择的时间刻度（秒）
        self.scale_seconds = self.nav_buttons_widget.get_time_scale_hours()

        # 如果选择的不是 "All"，更新页面持续时间
        if self.scale_seconds is not None:
            self.scale_seconds = min(self.scale_seconds,self.total_duration)
        else:
            # 如果选择的是 "All"，将页面持续时间设置为总持续时间
            self.scale_seconds = self.total_duration

        self.viewer.set_page_duration(self.scale_seconds)

        self.total_pages = int(np.ceil(self.total_duration / self.scale_seconds))
        self.nav_buttons_widget.set_total_pages(self.total_pages)
        self.viewer.slider_widget.time_slider.setTotalPages(self.total_pages)
        self.viewer.scroll_time()

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

        # 禁用保存图片按钮
        self.save_pic_btn.blockSignals(True)
        self.save_pic_btn.setEnabled(False)

    def disable_save_buttons(self):
        # 禁用保存数据按钮
        self.save_data_btn.blockSignals(True)
        self.save_data_btn.setEnabled(False)

        # 禁用保存图片按钮
        self.save_pic_btn.blockSignals(True)
        self.save_pic_btn.setEnabled(False)

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

        # 恢复保存图片按钮
        self.save_pic_btn.blockSignals(False)
        self.save_pic_btn.setEnabled(True)

    def on_analyse_clicked(self):
        """处理 Analyse 按钮点击事件"""
        try:
            QLLogging.log.info("Starting EMG analysis...")
            OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'EMG analysis gebin！', 0)
            self.get_valid_time_range()
            # 检查 scale_seconds 是否为有效值
            if not self.time_selector.validate_time_range() or not self.scale_seconds or self.scale_seconds <= 0:
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
            # selected_channels = self.channel_selector.get_selected_channels()
            selected_channels = self.combobox_emg.currentText()
            if not selected_channels:
                QMessageBox.warning(self.win, "未选择通道", "请至少选择一个通道！")
                return None
            # 分析按钮禁用掉# 阻断信号
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
            self.total_pages = int(np.ceil(self.total_duration / self.scale_seconds))
            self.nav_buttons_widget.set_total_pages(self.total_pages)

            # 开始创建分析线程
            result_path = os.path.join(self.raw.info['description'], 'EMG')
            self.worker = EMGAnalysisWorker(
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
            self.viewer.set_page_duration(self.scale_seconds)
            self.viewer.slider_widget.label_start_time.setText('00:00:00')
            hours = int(self.total_duration // 3600)
            minutes = int((self.total_duration % 3600) // 60)
            seconds = int(self.total_duration % 60)
            self.viewer.slider_widget.label_end_time.setText(f"{hours:02}:{minutes:02}:{seconds:02}")
            return True
        
        except Exception as e:
            stack_trace = traceback.format_exc()
            QLLogging.log.error(
                f"Error in on_analyse_clicked(EMG analysis): {str(e)}\n"
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

    def on_worker_result_ready(self, values = None):
        """
        处理 BandpowerWorker 的结果信号。
        :param bandpower_values: 频段功率计算结果
        """
        try:
            self.progressBar_widget.hide()
            self.viewer.show()
            self.viewer.slider_widget.time_slider.setTotalPages(self.total_pages)
            # 更新图表
            self.viewer.plot_emg_results(values)  # 数据画图
            # 恢复按钮状态
            self.enable_buttons()
        except Exception as e:
            stack_trace = traceback.format_exc()
            QLLogging.log.error(
                f"Error processing EMG analysis results: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )
            QMessageBox.critical(
                self.win,
                "Analysis Error",
                f"Failed to process analysis results: {str(e)}"
            )
            # 恢复UI状态
            # 恢复分析按钮
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
        # 记录错误日志
        QLLogging.log.error(f"computation worker error occurred: {error_message}")

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
        self.scale_seconds = self.nav_buttons_widget.get_time_scale_hours()  # 获取 scale_seconds
        if self.scale_seconds is None:
            self.scale_seconds = user_time_range
        print(f"Original scale_seconds: {self.scale_seconds}")

        # 更新 scale_seconds 为用户选择的时间范围与 scale_seconds 的最小值
        self.scale_seconds = min(user_time_range, self.scale_seconds)
        print(f"Updated scale_seconds: {self.scale_seconds}")



