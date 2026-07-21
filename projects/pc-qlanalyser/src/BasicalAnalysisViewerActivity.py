from PIL import Image
from PyQt5.QtSvg import QSvgGenerator
from PyQt5.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy,
    QLabel, QFrame, QLineEdit, QWidget, QComboBox, QSpacerItem, QMessageBox, QDialog, QRubberBand
)
from PyQt5.QtGui import QFont, QColor, QPainter, QCursor
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtCore import QThread, pyqtSignal, QDateTime, Qt, QRect, QSize, QEvent, QPoint, QTimer
from .BasicalAnalysisViewer import BasicalAnalysis, BasicalAnalysisViewer
from .SavePicCPM import SavePictureDialog, SaveDataDialog,SavePictureDialog1
import matplotlib.ticker as ticker
from .Control_Style import ControlStyle
from PyQt5.QtCore import QDateTime
from .CustomControls import StyledCheckboxWidget, TimeRangeSelector
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QSpinBox, QPushButton
)
from .Infrastructure.log.QLLogging import QLLogging
from .Infrastructure.DB.SQLLiteAccessor import SQLLiteDB_Only_MainTread
from src.Domain.OPLog.OPLog import OPLogTask, OPType, OPLog
import numpy as np
from matplotlib.figure import Figure
import pandas as pd
import time
from datetime import datetime
import os
from PyQt5.QtCore import pyqtSignal
import traceback
from datetime import timezone, timedelta
import pyqtgraph as pg
from pyqtgraph import SignalProxy, InfiniteLine, TextItem
from pyqtgraph.exporters import ImageExporter
from .left_time_overlay import DateAxis


class AccRmsWorker(QThread):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, viewer, channels):
        super().__init__()
        self.viewer = viewer
        self.channels = channels

    def run(self):
        try:
            self.viewer.compute_acc_rms(self.channels, self.progress)
            self.finished.emit()
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
                curr_time = self.meas_date + timedelta(seconds=v)
                # 根据缩放级别自动调整显示精度
                if spacing < 1:
                    strings.append(curr_time.strftime('%H:%M:%S.%f')[:-3])
                else:
                    strings.append(curr_time.strftime('%H:%M:%S'))
            except Exception:
                strings.append("")
        return strings

class ActivityCenterViewer(BasicalAnalysisViewer):
    # 分析界面最中间区域
    # 定义信号
    # progress_signal = pyqtSignal(int)  # 进度信号
    # finished_signal = pyqtSignal()  # 完成信号
    # error = pyqtSignal(str)
    page_changed = pyqtSignal(int)

    def __init__(self, num_plots=4, parent=None):
        super().__init__(parent)

        # 移除旧的 canvas 和 waveform_canvas
        if hasattr(self, 'canvas') and self.canvas:
            self.plot_layout.removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.canvas.deleteLater()

        # 移除 figure 对象
        if hasattr(self, 'figure'):
            self.figure = None

        self.waveform_widget.setLabel('bottom', '')

        # 【修改开始】使用自定义坐标轴初始化 acc_widget
        self.acc_time_axis = RelativeTimeAxis(orientation='bottom')
        self.acc_time_axis.setPen(None)
        self.acc_time_axis.setTextPen(pg.mkPen('k'))

        # 将 axisItems 传入 PlotWidget
        self.acc_widget = pg.PlotWidget(axisItems={'bottom': self.acc_time_axis})
        self.acc_widget.setBackground('w')
        # 设置边距：左、底部、右、顶部
        self.acc_widget.getPlotItem().setContentsMargins(90, 10, 10, 40)

        self.acc_widget.setLabel('left', 'Total ACC Value')
        self.acc_widget.setLabel('bottom', 'Time (s)')
        # 隐藏 x 轴和 y 轴线，但保留刻度标签
        self.acc_widget.getAxis('bottom').setPen(None)
        self.acc_widget.getAxis('left').setPen(None)
        # 设置坐标轴字体颜色为深色
        self.acc_widget.getAxis('bottom').setTextPen(pg.mkPen('k'))
        self.acc_widget.getAxis('left').setTextPen(pg.mkPen('k'))
        self.acc_widget.setMouseEnabled(x=True, y=False)  # 禁用鼠标交互
        self.acc_widget.setMenuEnabled(False)  # 禁用右键菜单
        self.acc_widget.getPlotItem().hideButtons()
        self.acc_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.acc_widget.setMinimumHeight(300)  # 设置最小高度

        self.acc_widget.setXLink(self.waveform_widget)  # 两图 X 同步

        # self.acc_widget.addLegend(offset=(-30, 30))   # 图例位置
        self.acc_plot = self.acc_widget.plot(pen=pg.mkPen('k', width=1), name="Total ACC")
        acc_bottom_axis = self.acc_widget.getAxis('bottom')
        acc_bottom_axis.setStyle(autoExpandTextSpace=False)  # 不随刻度文本自动扩展
        QTimer.singleShot(0, lambda: acc_bottom_axis.setHeight(acc_bottom_axis.height()))
        self.plot_layout.addWidget(self.acc_widget)

        self.total_acc_values = None

        # 如果存在时间标签和滑块，先移除它们
        if hasattr(self, 'time_label_widget'):
            self.plot_layout.removeWidget(self.time_label_widget)
            self.time_label_widget.setParent(None)

        if hasattr(self, 'slider_widget'):
            self.plot_layout.removeWidget(self.slider_widget)
            self.slider_widget.setParent(None)

        self.main_layout.addWidget(self.time_label_widget)
        self.main_layout.addWidget(self.slider_widget)

        self.amplitude_selector.clear()
        self.amplitude_selector.addItems(
            ["Auto", "±1000", "±2000", "±3000", "±4000", "±5000"])

        for w in (self.waveform_widget, self.acc_widget):
            pi = w.getPlotItem()
            # 方案A：直接固定左列宽度（最通用）
            try:
                pi.layout.setColumnFixedWidth(0, 85)   # 想要“固定”而不是“最小”就用这行
            except Exception:
                pass

        # —— 统一标注颜色（两图一致）
        self._hl_pen = pg.mkPen(52, 140, 212, 200, width=2)
        self._hl_brush = pg.mkBrush(52, 140, 212, 60)
        # 兼容旧变量名（若别处用到）
        self._acc_hl_pen = self._hl_pen
        self._acc_hl_brush = self._hl_brush

        # —— 全局橡皮筋（可跨两张图）
        self._rb_global = None
        self._rb_global_active = False
        self._rb_origin_global = None
        self._rb_min_px = 8
        self._rb_min_sec = 0.02
        self._rb_capture_all = False  # 是否临时拦截所有鼠标事件

        # —— 单图单窗的句柄（各自保留一个）
        self._wf_region = None
        self._wf_dialog = None
        self._acc_region = None
        self._acc_dialog = None
        # 👉 新增：记录所有放大弹窗的 viewport -> ViewBox 映射
        self._zoom_viewports = set()
        self._zoom_viewport_map = {}

        self._dlgs = []
        # 确保两张图的视口都安装事件过滤器（ACC 已有；waveform 也要）
        self.waveform_widget.viewport().installEventFilter(self)
        self.acc_widget.viewport().installEventFilter(self)
    def _get_amplitude_ylim(self, amplitude_str="Auto"):
        """解析幅值字符串，返回Y轴显示范围（min, max），Auto模式返回None"""
        if amplitude_str == "Auto":
            return None  # Auto模式：不限制Y轴，使用数据自然范围
        try:
            # 提取±后的数值（如"±2000" -> 最大显示2000）
            max_val = float(amplitude_str.lstrip('±'))
            return (0, max_val)  # ACC值非负，固定min=0
        except (ValueError, TypeError):
            return None  # 解析失败默认Auto

    def _get_waveform_ylim(self, amplitude_str="Auto"):
        """把幅值字符串(如 '±2000')解析为(-max, +max)。Auto 返回 None。单位 μV。"""
        if amplitude_str == "Auto":
            return None
        try:
            max_val = float(amplitude_str.lstrip('±'))
            return (-max_val, max_val)
        except (ValueError, TypeError):
            return None

    def _copy_plot_with_ylim(self, plot_item, ax, ylim=None):
        """复制完整数据到Matplotlib，并设置Y轴范围（核心修改）"""
        for curve in plot_item.curves:
            x_raw, y_raw = curve.getData()  # 获取完整原始数据（不筛选，长度不变）
            # 绘制全部数据（x和y长度与原始一致）
            ax.plot(
                x_raw, y_raw,
                label=curve.opts.get('name', ''),
                color=curve.opts.get('pen', 'k').color().name(),
                linewidth=curve.opts.get('pen', None).width() if hasattr(curve.opts.get('pen', None), 'width') else 1.0
            )
        # 设置Y轴显示范围（类似setYRange）
        if ylim is not None:
            ax.set_ylim(ylim)  # 固定Y轴范围，超出部分被截断显示
        # 复制其他样式（坐标轴标签、网格等）
        ax.set_xlabel(plot_item.axes["bottom"]["item"].label.toPlainText())
        ax.set_ylabel(plot_item.axes["left"]["item"].label.toPlainText())
        ax.set_title(plot_item.titleLabel.text if plot_item.titleLabel else "")
        if plot_item.showGrid(x=True, y=True):
            ax.grid(True, linestyle='--', alpha=0.7)
        if plot_item.legend is not None:
            ax.legend()

    def import_raw(self, raw, time_range=None, seconds=3600):
        QLLogging.log.debug("Importing raw data ...")
        sfreq = raw.info['sfreq']
        self.time_range = time_range
        self.page_duration = seconds
        start, end = self.time_range
        self.total_duration = end.toSecsSinceEpoch() - start.toSecsSinceEpoch()
        self.total_pages = int(np.ceil(self.total_duration / self.page_duration))
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
            start_idx = int(((start_time - raw.info['meas_date'].replace(tzinfo=timezone.utc)).total_seconds()) * sfreq)
            end_idx = int(((end_time - raw.info['meas_date'].replace(tzinfo=timezone.utc)).total_seconds()) * sfreq)

            if end_idx <= start_idx:
                raise ValueError("Invalid time range: end time must be greater than start time.")

            # 裁剪数据
            self.raw = raw.copy().crop(tmin=start_idx / sfreq, tmax=end_idx / sfreq)

    def compute_acc_rms(self, channels, signal_obj=None):
        """计算ACC总值并显示进度"""
        # 发送开始状态
        signal_obj.emit(0)

        # 1. 获取ACC通道
        if channels:
            # 筛选指定的通道
            acc_channels = [ch for ch in channels if ch in self.raw.ch_names]
        else:
            # 默认获取所有ACC通道
            acc_channels = [ch for ch in self.raw.ch_names if 'ACC' in ch.upper()]

        signal_obj.emit(10)
        # 2. 获取数据
        data, times = self.raw[acc_channels, :]
        data = data * 1e-6
        signal_obj.emit(50)
        # 3. 计算总ACC值
        self.total_acc_values = np.sqrt(np.sum(np.square(data), axis=0))
        self.full_times = times  # 保存完整时间数组（整个分析范围）
        self.full_acc = self.total_acc_values  # 保存完整ACC有效值（整个分析范围）
        signal_obj.emit(100)

    def on_amplitude_changed(self, value):
        super().on_amplitude_changed(value)    # 基类更新脑电图波形图
        self.on_below_amplitude_change(value)  # 子类更新ACC值

    def on_below_amplitude_change(self, value):
        acc_vb = self.acc_widget.getPlotItem().getViewBox()
        x_min, x_max = acc_vb.viewRange()[0]  # 获取当前x轴范围
        x, y = self.acc_plot.getData()  # 获取当前数据
        if x is None or y is None:
            QLLogging.log.warning("Waveform data is not initialized yet.")
            return
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
                acc_vb.setYRange(ymin - margin, ymax + margin)
                acc_vb.enableAutoRange(axis=pg.ViewBox.YAxis)
            else:
                acc_vb.enableAutoRange(axis=pg.ViewBox.YAxis)  # 自动范围
        else:
            try:
                amp = float(value.lstrip('±'))
                acc_vb.setYRange(0, amp, padding=0)  # 设置手动范围
            except ValueError:
                acc_vb.enableAutoRange(axis=pg.ViewBox.YAxis)  # 自动范围

    def update_waveform(self):
        """
        更新波形图，显示 self.start_time 到 self.end_time 对应的数据。
        """
        if self.raw_data is None or self.total_start_time is None or self.total_end_time is None:
            QLLogging.log.warning("Raw data or time range is not set.")
            QMessageBox.warning(self.win, "数据未加载", "请先加载数据文件。")
            return

        if not self.channel_names:
            QMessageBox.warning(self.win, "通道未选择", "请先选择一个通道进行查看。")
            return

        # 直接使用设置的 start_time 与 end_time（转换为 UTC 以保持一致）
        start_time = self.total_start_time.replace(tzinfo=timezone.utc)
        end_time = self.total_end_time.replace(tzinfo=timezone.utc)
        # 计算起始和结束索引
        start_idx = int(
            ((start_time - self.raw_data.info['meas_date'].replace(tzinfo=timezone.utc)).total_seconds()) * self.fs)
        end_idx = int(
            ((end_time - self.raw_data.info['meas_date'].replace(tzinfo=timezone.utc)).total_seconds()) * self.fs)
        
        if end_idx <= start_idx:
            return

        ch_name = self.channel_names[self.current_channel]
        self.wave_data, self.wave_times = self.raw_data[ch_name, start_idx : end_idx]
        if len(self.wave_times) == 0:
            return
        
        self.waveform_plot.clear() 
        self.waveform_plot.setData(self.wave_times, self.wave_data[0] * 1e-6)
        self.current_page = 1
        self.page_changed.emit(self.current_page)
        self.slider_widget.time_slider.setTotalPages(self.total_pages)
        self.slider_widget.time_slider.setValue(0)  # 时间滑块
        self.scroll_time()

    def scroll_time(self):
        if not self.raw_data:
            return
        # 获取时间范围的起始时间
        start = self.start_time
        qt_start = QDateTime(start)

        # 获取时间戳
        start_timestamp = qt_start.toSecsSinceEpoch()

        pos = self.slider_widget.time_slider.value()
        start_time = pos
        end_time = pos + self.page_duration

        # 确保两个时间对象都有相同的时区设置
        meas_date = self.raw_data.info['meas_date']
        if meas_date.tzinfo is None:
            meas_date = meas_date.replace(tzinfo=timezone.utc)

        if hasattr(self, 'waveform_left_text'):
            print(meas_date)
            self.waveform_left_text.set_meas_date(meas_date)

        if hasattr(self, 'acc_time_axis'):
            self.acc_time_axis.set_meas_date(meas_date)

        total_start = self.total_start_time
        if total_start is not None and total_start.tzinfo is None:
            total_start = total_start.replace(tzinfo=timezone.utc)

        # analysis 起点相对于 meas_date 的偏移（单位：秒）
        if total_start is None:
            analysis_offset = 0.0
        else:
            analysis_offset = (total_start - meas_date).total_seconds()

        # 计算开始时间
        start_time_waveform = analysis_offset + start_time

        # 计算结束时间
        end_time_waveform = start_time_waveform + self.page_duration

        if not getattr(self, "is_manually_changing_page", False):
            # 这里你原来就是调用 get_current_page + 发信号
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
        self.acc_widget.getAxis('bottom').setTicks(None)

        # 隐藏上方波形图的底部刻度
        self.waveform_widget.getAxis('bottom').setTicks([])

        ch_name = self.channel_names[self.current_channel]
        start_idx = int(start_time_waveform * self.fs)
        end_idx = int(end_time_waveform * self.fs)
        # 防御边界
        if start_idx < 0:
            start_idx = 0
        if end_idx <= start_idx:
            return

        self.wave_data, self.wave_times = self.raw_data[ch_name, start_idx:end_idx]

        self.current_times = self.wave_times
        # —— ACC：full_times 本来就是“相对时间”（0 开始），所以和 start_time/end_time 对齐即可
        time_mask = (self.full_times >= start_time) & (self.full_times <= end_time)
        current_acc_times = self.full_times[time_mask]
        current_acc_values = self.full_acc[time_mask]

        # —— 波形：wave_times 是“绝对时间”（自 meas_date 起），所以用 start_time_waveform/end_time_waveform
        time_mask_wave = (
                (self.wave_times >= start_time_waveform) &
                (self.wave_times <= end_time_waveform)
        )
        wave_times_downsampled = self.wave_times[time_mask_wave]
        wave_data_downsampled = self.wave_data[0][time_mask_wave]

        # 大数据量时降采样
        if len(current_acc_times) > 1800000:
            current_acc_times, current_acc_values = self.downsample_data(
                current_acc_times, current_acc_values
            )
        if len(wave_times_downsampled) > 1800000:
            wave_times_downsampled, wave_data_downsampled = self.downsample_data(
                wave_times_downsampled, wave_data_downsampled
            )

        # 8) 更新曲线
        self.acc_plot.setData(current_acc_times, current_acc_values)
        self.waveform_plot.setData(wave_times_downsampled, wave_data_downsampled * 1e-6)

        # 9) 更新视口范围
        self.acc_widget.setUpdatesEnabled(False)
        self.waveform_widget.setUpdatesEnabled(False)

        padding = (end_time - start_time) * 0.01
        # 波形用“绝对时间”范围
        self.waveform_widget.setXRange(
            start_time_waveform - padding,
            end_time_waveform + padding
        )
        # ACC 继续用 0 开始的“相对时间”
        self.acc_widget.setXRange(
            start_time - padding,
            end_time + padding
        )

        self.acc_widget.setUpdatesEnabled(True)
        self.waveform_widget.setUpdatesEnabled(True)

        self.waveform_widget.getViewBox().update()
        self.acc_widget.getViewBox().update()

        # 10) 限制拖拽不要离开当前页
        self._apply_acc_page_guardrails(start_time, end_time)
        self._apply_waveform_page_guardrails(start_time_waveform, end_time_waveform)
    def _apply_acc_page_guardrails(self, page_start: float, page_end: float):
        if page_end <= page_start:
            return
        vb = self.acc_widget.getPlotItem().vb
        eps = 1e-6
        vb.setLimits(
            xMin=page_start - eps,
            xMax=page_end + eps,
            minXRange=min(0.2, max(0.01, (page_end - page_start) * 0.1)),
            maxXRange=(page_end - page_start)
        )
        # 把视窗也回到当页
        self.acc_widget.setXRange(page_start, page_end, padding=0)

    def eventFilter(self, obj, event):
        # ==== 1. 放大弹出框里的 Ctrl+滚轮：只缩放 Y 轴 ====
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

            # 其他事件交给父类处理
            return super().eventFilter(obj, event)

        is_wave = (obj is self.waveform_widget.viewport())
        is_acc = (obj is self.acc_widget.viewport())

        # —— 若正在全局拖拽，临时接管所有鼠标移动/松开事件（无论落在哪个控件）
        if self._rb_capture_all and self._rb_global_active:
            t = event.type()
            if t == QEvent.MouseMove:
                gpos = getattr(event, "globalPos", None)
                if callable(gpos):
                    gpos = gpos()
                else:
                    gpos = QCursor.pos()
                rect = QRect(self.mapFromGlobal(self._rb_origin_global),
                             self.mapFromGlobal(gpos)).normalized()
                if self._rb_global:
                    self._rb_global.setGeometry(rect)
                return True

            if t == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                gpos = getattr(event, "globalPos", None)
                if callable(gpos):
                    gpos = gpos()
                else:
                    gpos = QCursor.pos()
                sel_rect = QRect(self.mapFromGlobal(self._rb_origin_global),
                                 self.mapFromGlobal(gpos)).normalized()
                # 结束拖拽
                self._rb_capture_all = False
                self._rb_global_active = False
                if self._rb_global:
                    self._rb_global.hide()

                # —— 针对每张图，计算选框与其视口的交集；命中则各自开窗
                self._handle_selection_for_plot(self.waveform_widget, sel_rect, is_waveform=True)
                self._handle_selection_for_plot(self.acc_widget, sel_rect, is_waveform=False)

                return True

        # —— Shift+按下：在任一视口启动“全局橡皮筋”拖拽
        if (event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton
                and (event.modifiers() & Qt.ShiftModifier)
                and (is_wave or is_acc)):
            # 起点（全局坐标）
            self._rb_origin_global = obj.mapToGlobal(event.pos())
            # 橡皮筋放在 self 上，跨两张图
            if self._rb_global is None or self._rb_global.parent() is not self:
                self._rb_global = QRubberBand(QRubberBand.Rectangle, self)
            self._rb_global.setGeometry(QRect(self.mapFromGlobal(self._rb_origin_global), QSize()))
            self._rb_global.show()
            self._rb_global_active = True
            self._rb_capture_all = True  # 临时接管后续移动/松开事件
            return True

        # 其他事件走默认流程（不影响滚轮缩放等）
        return super().eventFilter(obj, event)

    def _handle_selection_for_plot(self, plot_widget, sel_rect_in_self: QRect, is_waveform: bool):
        # 该图的 viewport 在 self 坐标系下的矩形
        vp = plot_widget.viewport()
        vp_rect_in_self = QRect(self.mapFromGlobal(vp.mapToGlobal(QPoint(0, 0))), vp.size())
        inter = sel_rect_in_self & vp_rect_in_self
        if inter.isEmpty() or inter.width() < self._rb_min_px:
            return

        # 取交集矩形的中线 y，左右 x；从 self -> global -> viewport -> scene -> data
        def _x_from_self_x(self_x):
            gpt = self.mapToGlobal(QPoint(self_x, inter.center().y()))
            vp_pt = vp.mapFromGlobal(gpt)  # viewport 坐标
            scene_pt = plot_widget.mapToScene(vp_pt)  # QGraphicsScene
            x = plot_widget.getPlotItem().vb.mapSceneToView(scene_pt).x()
            return x

        x0 = _x_from_self_x(inter.left())
        x1 = _x_from_self_x(inter.right())
        if x0 > x1:
            x0, x1 = x1, x0

        # === 新增：把选区钳制在“当前展示的最小/最大 X”之内 ===
        vb = plot_widget.getPlotItem().vb
        vis_x0, vis_x1 = vb.viewRange()[0]  # 当前可见 X 范围
        x0 = max(vis_x0, min(x0, vis_x1))
        x1 = max(vis_x0, min(x1, vis_x1))
        # 钳制后若过窄，直接忽略
        if (x1 - x0) < self._rb_min_sec:
            return

        region = pg.LinearRegionItem(values=(x0, x1), brush=self._hl_brush, pen=self._hl_pen, movable=False)
        plot_widget.addItem(region)

        # 2. 打开窗口并存入列表 (不再赋值给 self._wf_dialog)
        if is_waveform:
            d = self._show_waveform_zoom_dialog(x0, x1, region)
        else:
            d = self._show_acc_zoom_dialog(x0, x1, region)

        self._dlgs.append(d)
    def _show_waveform_zoom_dialog(self, x_min_abs: float, x_max_abs: float, region: pg.LinearRegionItem):
        dialog = QDialog(self)
        meas_date = self.raw_data.info['meas_date']
        sec_start = round(float(x_min_abs), 3)
        sec_end = round(float(x_max_abs), 3)
        ms_start = int(round(sec_start * 1000))
        ms_end = int(round(sec_end * 1000))
        abs_start = meas_date + timedelta(milliseconds=ms_start)
        abs_end = meas_date + timedelta(milliseconds=ms_end)
        start_str = abs_start.strftime("%Y-%m-%d %H:%M:%S") + f".{ms_start % 1000:03d}"
        end_str = abs_end.strftime("%Y-%m-%d %H:%M:%S") + f".{ms_end % 1000:03d}"
        #dialog.setWindowTitle(f"waveform  [{start_str}  ~  {end_str}]")
        #放大窗口标题改为当前通道名称
        # 放大窗口标题改为当前通道名称
        try:
            ch_name = ""
            if hasattr(self, "channel_names") and hasattr(self, "current_channel"):
                # 与 update_waveform / scroll_time 中取通道名的方式保持一致
                ch_name = self.channel_names[self.current_channel]
        except Exception:
            ch_name = ""

        title_prefix = ch_name if ch_name else "waveform"
        dialog.setWindowTitle(f"{title_prefix}  [{start_str}  ~  {end_str}]")


        from PyQt5.QtWidgets import QVBoxLayout
        date_axis = DateAxis(meas_date, orientation='bottom')
        zoom_plot = pg.PlotWidget(axisItems={'bottom': date_axis})
        layout = QVBoxLayout(dialog)
        layout.addWidget(zoom_plot)
        dialog.resize(900, 320)

        src_pi = self.waveform_widget.getPlotItem()
        dst_pi = zoom_plot.getPlotItem()

        # 复制并裁剪 waveform 曲线（x=绝对秒）
        for it in src_pi.listDataItems():
            try:
                x, y = it.getData()
            except Exception:
                continue
            if x is None or y is None or len(x) == 0:
                continue
            mask = (x >= x_min_abs) & (x <= x_max_abs)
            if mask.any():
                pen = it.opts.get('pen', None)
                dst_pi.addItem(pg.PlotDataItem(x=x[mask], y=y[mask], pen=pen))

        zoom_plot.setBackground("w")
        zoom_plot.showGrid(x=True, y=True, alpha=0.3)
        zoom_plot.setMouseEnabled(x=True, y=False)
        zoom_plot.setXRange(x_min_abs, x_max_abs, padding=0)
        zoom_plot.setMenuEnabled(False)
        vp = zoom_plot.viewport()
        vp.installEventFilter(self)
        self._zoom_viewports.add(vp)
        self._zoom_viewport_map[vp] = zoom_plot.getPlotItem().vb

        def _cleanup(_=None):
            # 原来的：关窗时去掉主图上的高亮
            try:
                self.waveform_widget.removeItem(region)
            except Exception:
                pass

            # 👉 新增：清理放大窗 viewport 的事件过滤器和映射
            try:
                vp = zoom_plot.viewport()
                if vp in self._zoom_viewports:
                    vp.removeEventFilter(self)
                    self._zoom_viewports.discard(vp)
                    self._zoom_viewport_map.pop(vp, None)
            except Exception:
                pass
        if dialog in self._dlgs:
            self._dlgs.remove(dialog)

        dialog.finished.connect(_cleanup)
        dialog.show()
        return dialog
    def _show_acc_zoom_dialog(self, x_min: float, x_max: float, region: pg.LinearRegionItem):
        dialog = QDialog(self)
        meas_date = self.raw_data.info['meas_date']
        abs_start = meas_date + timedelta(seconds=float(x_min))
        abs_end = meas_date + timedelta(seconds=float(x_max))
        start_str = abs_start.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        end_str = abs_end.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        dialog.setWindowTitle(f"ACC  [{start_str}  ~  {end_str}]")
        from PyQt5.QtWidgets import QVBoxLayout
        date_axis = DateAxis(meas_date, orientation='bottom')
        zoom_plot = pg.PlotWidget(axisItems={'bottom': date_axis})
        layout = QVBoxLayout(dialog)
        layout.addWidget(zoom_plot)
        dialog.resize(900, 320)

        src_pi = self.acc_widget.getPlotItem()
        dst_pi = zoom_plot.getPlotItem()

        # 复制并裁剪 ACC 曲线到放大窗
        for it in src_pi.listDataItems():
            try:
                x, y = it.getData()
            except Exception:
                continue
            if x is None or y is None or len(x) == 0:
                continue
            mask = (x >= x_min) & (x <= x_max)
            if mask.any():
                pen = it.opts.get('pen', None)
                dst_pi.addItem(pg.PlotDataItem(x=x[mask], y=y[mask], pen=pen))

        zoom_plot.setBackground("w")
        zoom_plot.showGrid(x=True, y=True, alpha=0.3)
        zoom_plot.setMouseEnabled(x=True, y=False)  # 放大窗也支持滚轮缩放（只限 X）
        zoom_plot.setXRange(x_min, x_max, padding=0)
        zoom_plot.setMenuEnabled(False)

        # 👉 让 ACC 放大窗也支持 Ctrl+滚轮单独缩放 Y 轴
        vp = zoom_plot.viewport()
        vp.installEventFilter(self)
        self._zoom_viewports.add(vp)
        self._zoom_viewport_map[vp] = zoom_plot.getPlotItem().vb

        # 关闭放大窗时移除 ACC 上的高亮
        def _cleanup(_=None):
            try:
                self.acc_widget.removeItem(region)
                self._acc_regions.remove(region)
            except Exception:
                pass

            # 👉 新增：清理放大窗 viewport 的事件过滤器和映射
            try:
                vp = zoom_plot.viewport()
                if vp in self._zoom_viewports:
                    vp.removeEventFilter(self)
                    self._zoom_viewports.discard(vp)
                    self._zoom_viewport_map.pop(vp, None)
            except Exception:
                pass
            if dialog in self._dlgs:
                self._dlgs.remove(dialog)

        dialog.finished.connect(_cleanup)
        dialog.show()
        return dialog
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

    def save_data_without_path(self):
        """让用户选择路径并保存数据"""
        try:

            # 获取当前日期和时间
            current_time = datetime.now()
            formatted_time = current_time.strftime("%Y-%m-%d%H%M%S")

            # 检查数据是否存在
            if not hasattr(self, 'full_times') or not hasattr(self, 'total_acc_values'):
                QMessageBox.warning(
                    self.win,
                    "No Data",
                    "No analysis results to save.\nPlease perform ACC analysis first."
                )
                return False

            # 显示保存对话框
            dialog = SaveDataDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                # 获取保存参数
                params = dialog.get_save_parameters()
                save_path = params['path']
                data_format = params['format'].lower()

                # 创建保存目录
                default_folder = "Activity_Analysis_data"
                save_dir = os.path.join(save_path, default_folder)
                os.makedirs(save_dir, exist_ok=True)

                # 创建数据字典
                data_dict = {
                    'Time': self.full_times,
                    'Total_ACC': self.total_acc_values
                }
                df = pd.DataFrame(data_dict)

                # 根据不同格式保存数据
                if data_format == '.csv':
                    file_path = os.path.join(save_dir, f'activity_analysis{formatted_time}.csv')
                    df.to_csv(file_path, index=False)
                elif data_format == '.npy':
                    file_path = os.path.join(save_dir, f'activity_analysis{formatted_time}.npy')
                    # 保存完整的数据结构
                    save_dict = {
                        'data': df.to_numpy(),
                        'columns': df.columns.tolist(),
                        'sampling_rate': self.raw.info['sfreq']  # 保存采样率等元数据
                    }
                    np.save(file_path, save_dict, allow_pickle=True)

                elif data_format == '.mat':
                    file_path = os.path.join(save_dir, f'activity_analysis{formatted_time}.mat')
                    from scipy.io import savemat
                    # 保存为MATLAB可读取的格式
                    save_dict = {
                        'data': df.to_numpy(),
                        'columns': df.columns.tolist(),
                        'sampling_rate': self.raw.info['sfreq']
                    }
                    savemat(file_path, save_dict)

                # 显示成功消息
                QMessageBox.information(
                    self.win,
                    "Save Success",
                    f"Data has been saved to:\n{file_path}"
                )
                QLLogging.log.info(f"Data saved successfully: {file_path}")
                OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'Save Data', 0)
                return True

        except Exception as e:
            stack_trace = traceback.format_exc()
            # 记录详细的错误信息
            QLLogging.log.error(
                f"Error saving activity_analysis data: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )

            QMessageBox.critical(
                self.win,
                "Error",
                f"Failed to save data: {str(e)}"
            )
            return False


    def _save_single_figure(self, result_path, img_format, dpi, target_widget, ylim=None):
        """
        保存单个图（wave 或 acc 单独保存）
        :param target_widget: 要保存的目标组件，传 self.waveform_widget 或 self.acc_widget
        ylim:振幅
        """
        root, ext = os.path.splitext(result_path)
        save_path_activaty = f"{root}_Total_ACC_Value{ext}"
        fig, ax = plt.subplots(figsize=(14, 6), dpi=dpi)
        plot_item = target_widget.plotItem
        self._copy_plot_with_ylim(plot_item, ax, ylim)  # 使用带Y轴限制的复制方法
        fig.set_facecolor('white')
        fig.savefig(save_path_activaty, format=img_format, dpi=dpi, bbox_inches='tight')
        plt.close(fig)

    def _save_single_segment(self, segment_index=None, save_params=None,current_amplitude="Auto"):

        """保存单个分段（支持外部传入保存参数，避免重复选择路径）"""
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d-%H%M%S")

        # 解析保存参数
        save_path = save_params['path']
        img_format = save_params['format'].lower().replace('.', '')
        dpi = save_params['resolution']

        # 创建保存目录
        default_folder = "Activity_Analysis_pic"
        save_dir = os.path.join(save_path, default_folder)
        os.makedirs(save_dir, exist_ok=True)

        # 生成带分段索引的文件名
        if segment_index is not None:
            filename = f"{formatted_time}_segment_{segment_index + 1}.{img_format}"
        else:
            filename = f"{formatted_time}.{img_format}"
        result_path = os.path.join(save_dir, filename)

        # ---- 处理幅值设置，Auto时不调整 ----
        if current_amplitude and current_amplitude != "Auto":
            # 非Auto时，触发幅值调整（确保保存时应用当前设置）
            self.on_below_amplitude_change(current_amplitude)
            # 延迟等待界面更新（可选，确保渲染完成）
            QApplication.processEvents()

        # 解析Y轴显示范围（关键：获取min和max）
        ylim = self._get_amplitude_ylim(current_amplitude)

        # 保存不同内容

        self._save_single_figure(result_path, img_format, dpi,self.acc_widget, ylim)


        # 计算页面时间范围
        page_start_time = (self.current_page - 1) * self.page_duration
        page_end_time = page_start_time + self.page_duration
        selected_channels = self.channel_names
        waveform_ylim = self._get_waveform_ylim(self.amplitude_selector.currentText())
        for data in selected_channels:
            if "ACC" not in data:
                continue
            self.save_waveform_offscreen(
                channel_name=data,
                start_time=page_start_time,
                end_time=page_end_time,
                save_dir=save_dir,
                filename=f"Waveform_{data}_{formatted_time}.{img_format}",
                dpi=dpi,
                img_format=img_format,
                ylim=waveform_ylim
            )

        return save_dir


    def save_waveform_offscreen(self, channel_name, start_time, end_time, save_dir, filename, dpi, img_format,ylim=None):
        """
        离屏渲染波形图，不更新当前显示
        """
        result_path = os.path.join(save_dir, filename)

        # 创建离屏图形
        fig, ax = plt.subplots(figsize=(16, 6), dpi=dpi)

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

        # 计算相对于total_start的绝对时间
        absolute_start_time = total_start + timedelta(seconds=start_time)
        absolute_end_time = total_start + timedelta(seconds=end_time)

        # 计算开始和结束索引
        start_idx = int(((absolute_start_time - meas_date).total_seconds()) * self.fs)
        end_idx = int(((absolute_end_time - meas_date).total_seconds()) * self.fs)

        # 获取数据
        wave_data, wave_times = self.raw_data[ch_name, start_idx: end_idx]
        wave_data=wave_data * 1e-6

        if len(wave_times) == 0:
            plt.close(fig)
            return

        # 绘制波形
        ax.plot(wave_times, wave_data[0], color='black', linewidth=0.5)

        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Amplitude(μV)')
        ax.set_title(f'{ch_name} Waveform')
        ax.margins(x=0, y=0)
        ax.grid(True, linestyle='--', alpha=0.7)

        # 设置x轴范围为相对时间（从0开始）
        ax.set_xlim(start_time, end_time)

        if ylim is not None:
            ax.set_ylim(ylim)
        else:
            # y轴自适应
            if len(wave_data[0]) > 0:
                ymin = np.min(wave_data[0])
                ymax = np.max(wave_data[0])
                y_range = ymax - ymin
                # 添加10%的边距
                margin = y_range * 0.1 if y_range > 0 else 0.1
                ax.set_ylim(ymin - margin, ymax + margin)
            else:
                # 如果没有数据，设置默认范围
                ax.set_ylim(-100, 100)

        # 应用保存参数
        fig.set_facecolor('white')
        fig.patch.set_edgecolor('none')

        # 保存图像
        fig.savefig(result_path, format=img_format, dpi=dpi,
                    bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close(fig)

        QLLogging.log.info(f"Saved waveform offscreen: {result_path}")

    def save_figure_without_path(self):
        """保存当前段或所有分段的图片，全部分段只选择一次文件夹"""
        from datetime import datetime
        try:
            # ---- 获取当前幅值设置 ----
            current_amplitude = self.amplitude_selector.currentText()
            QLLogging.log.info(f"当前幅值设置: {current_amplitude}")
            dialog = SavePictureDialog(self)
            if dialog.exec_() != QDialog.Accepted:
                return False
            save_params = dialog.get_save_parameters()
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
            # 保存当前显示的段
            s_path = self._save_single_segment(save_params=save_params,
                                               current_amplitude=current_amplitude)
            wait_box.close()

            if s_path:
                QMessageBox.information(
                    self.win,
                    "Save Success",
                    f"Figure has been saved to:\n{s_path}"
                )
                QLLogging.log.info(f"Figure saved successfully: {s_path}")
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
                f"Error saving activity_analysis figure: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )
            QMessageBox.critical(
                self.win,
                "Error",
                f"Failed to save figure: {str(e)}"
            )
            QLLogging.log.exception(f"Error saving figure: {str(e)}")
            return False
        finally:
            # 兜底清理
            if wait_box:
                try:
                    if wait_box.isVisible():
                        wait_box.close()
                finally:
                    wait_box.deleteLater()

class ActivityAnalysisViewer(BasicalAnalysis):

    def __init__(self, title, channel_name, parent=None):
        super().__init__(title, channel_name, parent)
        self.setWindowTitle("Activity Analysis")

    def init_center_and_bottom(self, content_layout):
        """自定义中央显示区域和底部按钮"""
        self.viewer = ActivityCenterViewer()
        super().init_center_and_bottom(content_layout)
        self.viewer.hide()
        self.h_layout.addWidget(self.viewer)

    def init_left_panel(self, content_layout):
        super().init_left_panel(content_layout)
        self.left_layout.addStretch()  # 添加弹性空间

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
            num_acc = 0
            for data in selected_channels:
                if "ACC" in data:
                    num_acc += 1
            if num_acc != 3:
                QMessageBox.warning(self.win, "Channel Selected", "Please select at least three ACC channel!")
                print("on_analyse_clicked: No channel selected.")
                return None

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

            QLLogging.log.debug("basical analysis-Activity Analyse begin.")
            OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value,
                        'basical analysis-Activity Analyse begin！', 0)

            time_range = self.time_selector.get_time_range()
            self.viewer.import_raw(self.raw, time_range, self.scale_seconds)

            self.acc_thread = AccRmsWorker(self.viewer, self.channel_selector.get_selected_channels())
            self.acc_thread.finished.connect(self.on_worker_result_ready)
            self.acc_thread.progress.connect(self.on_worker_progress)
            self.acc_thread.error.connect(self.on_worker_error)
            self.acc_thread.start()

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
