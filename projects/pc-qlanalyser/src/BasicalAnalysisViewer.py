from PyQt5.QtCore import Qt, pyqtSignal, QEvent, QSize, QRect, QPoint, QTimer
from .CustomControls import StyledCheckboxWidget, TimeRangeSelector, IconWithTextWidget, TimeSliderWidget, \
    FrequencyCheckboxWidget, NavButtonsWidget, PropertyWidget
from .Control_Style import ControlStyle
import numpy as np
from datetime import datetime, timedelta
import time
from PyQt5.QtWidgets import (QWidget, QPushButton, QProgressBar, QLabel,
                             QComboBox, QHBoxLayout, QMessageBox, QInputDialog, QSizePolicy,
                             QFrame, QSpacerItem, QToolButton, QMenuBar, QApplication, QRubberBand, QDialog)
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from .Infrastructure.log.QLLogging import QLLogging
import gc
from datetime import timezone
from .Domain.OPLog.OPLog import OPLog, OPType
from src.Infrastructure.DB.SQLLiteAccessor import SQLLiteDB_Only_MainTread
import traceback
import matplotlib.ticker as ticker
import pyqtgraph as pg
from .utils import setup_short_cut
from src.Infrastructure.QLWidgets.QLGifProgressBar import GifProgressBar
from .CustomControls import LoadingOverlay
from .left_time_overlay import LeftTimeOverlay, DateAxis


class BasicalAnalysisViewer(QWidget):  ##中间的界面
    # 定义信号，发送当前页码
    page_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.visited = 0
        self.original_y = []
        self.init_ui()
        self.setContentsMargins(0, 0, 0, 0)
        self.raw_data = None
        self.start_time = None
        self.end_time = None
        self.total_start_time = None
        self.total_end_time = None
        self.fs = 250  # default sampling frequency
        self.channel_names = []  ##选择的通道
        self.current_channel = 0  ##现在展示的通道
        self.x_label = "Time"
        self.y_label = "Amplitude (μV)"
        self.page_duration = 3600  # 默认一页为3600秒
        self.total_duration = 0
        self.manual_y_range = None  # 初始使用自动幅度范围 y轴
        self.total_pages = 1  # 总页数
        self.current_page = 1  # 当前页
        self.result = []  # 存储柱形图数据
        self.win = None
        # 设置振幅范围映射
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
        self.is_manually_changing_page = False  # 是否手动更改页面
        self.class_name = self.__class__.__name__
        self.wave_times = None

        # 添加加载提示组件
        self.loading_overlay = LoadingOverlay(self)
        self.loading_overlay.setObjectName("loading_overlay")

        # 框选 RubberBand 与高亮所需的状态
        self._waveform_rb = None
        self._waveform_rb_origin = None
        self._waveform_rb_host = self.waveform_widget.viewport()
        self._waveform_rb_active = False  # <— 新增：是否正在框选
        self._waveform_min_px = 8  # <— 新增：最小像素宽度（小于则忽略）
        self._waveform_min_sec = 0.02  # <— 新增：最小秒宽（小于则忽略）
        self._waveform_regions = []  # 保存所有高亮 LinearRegionItem
        self._waveform_zoom_windows = []  # 保存所有非模态放大窗
        self._waveform_dialog_region = {}  # dialog -> region
        self._waveform_hl_pen = pg.mkPen(100, 149, 237, 180, width=1)  # #6495ED
        self._waveform_hl_brush = pg.mkBrush(100, 149, 237, 60)

        # 仅这张图安装事件过滤器（其它图不受影响）
        self.waveform_widget.viewport().installEventFilter(self)

        # 替换原来的self._zoom_viewport/self._zoom_vb，用字典存储所有放大窗口的视口->ViewBox映射
        self._zoom_viewport_map = {}  # key: viewport对象, value: 对应的ViewBox对象

    def init_ui(self):
        self.setWindowTitle("EEG Viewer")
        self.setMinimumSize(1000, 600)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        # Top Control Bar
        control_layout = QHBoxLayout()

        self.prev_button = QPushButton("<")
        self.prev_button.setMinimumSize(30, 32)
        self.prev_button.setStyleSheet(ControlStyle.get_nav_pushButton_style())
        self.channel_selector = QLabel("EEGO")
        self.channel_selector.setMaximumHeight(32)  # 设置最大高度（可选）
        self.channel_selector.setMinimumSize(50, 32)
        self.channel_selector.setStyleSheet("""
            font-family: Microsoft YaHei;
            background: #FFFFFF;
            border-radius: 0px 0px 0px 0px; /* 设置圆角为 0 */
            border: 1px solid #D4D6D9; /* 边框颜色 */
            padding: 4px; /* 内边距 */
            line-height: 14px; /* 行高 */
            background-color: #ffffff; /* 背景颜色 */
            color: #2A87DB; /* 字体颜色 */
        """)

        self.channel_selector.setAlignment(Qt.AlignCenter)
        self.next_button = QPushButton(">")
        self.next_button.setMinimumSize(30, 32)
        self.next_button.setStyleSheet(ControlStyle.get_nav_pushButton_style())
        self.amplitude_label = QLabel("Amplitude(μV)")
        self.amplitude_label.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.amplitude_label, 10)
        self.amplitude_selector = QComboBox()
        self.amplitude_selector.addItems(
            ["Auto", "±50", "±100", "±200", "±500", "±1000"])
        self.amplitude_selector.setMinimumSize(100, 32)
        self.amplitude_selector.setStyleSheet(ControlStyle.get_comboBox_word_style())
        self.amplitude_selector.currentTextChanged.connect(self.on_amplitude_changed)

        control_layout.addWidget(self.prev_button)
        control_layout.addWidget(self.channel_selector)
        control_layout.addWidget(self.next_button)
        control_layout.addStretch()
        control_layout.addWidget(self.amplitude_label)
        # 添加空白区域
        spacer_between_label_and_selector = QSpacerItem(5, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        control_layout.addSpacerItem(spacer_between_label_and_selector)
        control_layout.addWidget(self.amplitude_selector)
        # 添加一个固定大小的空白区域
        spacer_fixed = QSpacerItem(20, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        control_layout.addSpacerItem(spacer_fixed)

        self.main_layout.addLayout(control_layout)

        # 创建图像区域容器和布局
        self.plot_area = QWidget()
        self.plot_layout = QVBoxLayout(self.plot_area)
        self.plot_layout.setContentsMargins(0, 0, 0, 10)  # 左上右下
        self.plot_layout.setSpacing(0)
        # 3. 添加各种图片或canvas
        # Waveform Canvas  ##第一张折线图画布

        self.time_axis = RelativeTimeAxis(orientation='bottom')
        self.time_axis.setPen(None)  # 隐藏轴线(保持你原有的样式)
        self.time_axis.setTextPen(pg.mkPen('k'))  # 设置字体颜色

        # 将 axisItems 传入 PlotWidget
        self.waveform_widget = pg.PlotWidget(axisItems={'bottom': self.time_axis})
        self.waveform_widget.setBackground('w')
        # 设置边距：左、底部、右、顶部
        self.waveform_widget.getPlotItem().setContentsMargins(90, 10, 10, 10)
        self.waveform_widget.setLabel('left', 'Amplitude(μV)')
        self.waveform_widget.setLabel('bottom', 'Time (s)')
        # 隐藏 x 轴和 y 轴线，但保留刻度标签
        self.waveform_widget.getAxis('bottom').setPen(None)
        self.waveform_widget.getAxis('left').setPen(None)
        # 设置坐标轴字体颜色为深色
        self.waveform_widget.getAxis('bottom').setTextPen(pg.mkPen('k'))
        self.waveform_widget.getAxis('left').setTextPen(pg.mkPen('k'))
        self.waveform_widget.setMouseEnabled(x=True, y=False)  # 禁用缩放/平移
        self.waveform_widget.setMenuEnabled(False)  # 禁用右键菜单
        self.waveform_widget.getPlotItem().hideButtons()
        self.waveform_widget.setMinimumHeight(300)  # 设置最小高度
        self.plot_layout.addWidget(self.waveform_widget)
        self.waveform_plot = self.waveform_widget.plot(pen=pg.mkPen('k', width=0.5), name="waveform_plot")
        bottom_axis = self.waveform_widget.getAxis('bottom')
        bottom_axis.setStyle(autoExpandTextSpace=False)  # 不再随刻度文本自动扩展
        QTimer.singleShot(0, lambda: bottom_axis.setHeight(bottom_axis.height()))  # 用当前(有刻度)高度锁定
        # 左侧时刻文本框
        self.waveform_left_text = LeftTimeOverlay(
            self.waveform_widget,
            anchor_parent=self.waveform_widget,
            corner='bottom-left', offset=(16, 8),
            meas_date=None,  # 先不设，稍后在 scroll_time 里赋值
            dt_fmt='%Y-%m-%d %H:%M:%S',  # 含日期
            show_ms=True  # 显示毫秒
        )

        # 安装事件过滤器
        self.waveform_widget.viewport().installEventFilter(self)

        # 创建时间标签容器
        self.time_label_widget = QWidget()
        self.time_label_layout = QHBoxLayout(self.time_label_widget)
        self.time_label_layout.setContentsMargins(0, 0, 0, 0)
        self.time_label_layout.setSpacing(0)

        # 先把时间标签加到主布局（在waveform_canvas上面）
        self.plot_layout.addWidget(self.time_label_widget)

        # 添加时间滚动条
        self.slider_widget = TimeSliderWidget()
        self.slider_widget.time_slider.setMinimum(0)
        self.slider_widget.time_slider.setValue(0)
        self.plot_layout.addWidget(self.slider_widget)

        # # 添加一个空白区域
        # spacer = QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding)
        # self.plot_layout.addSpacerItem(spacer)

        # 创建单个画布
        self.figure = Figure(constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)  # 除波形图
        self.plot_layout.addWidget(self.canvas)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 将图像区域添加到主布局
        self.main_layout.addWidget(self.plot_area)
        # Connect controls
        self.prev_button.clicked.connect(self.show_prev_channel)
        self.next_button.clicked.connect(self.show_next_channel)
        self.slider_widget.time_slider.valueChanged.connect(self.scroll_time)

    # 放大窗口 eventFilter
    def eventFilter(self, obj, event):
        # ==== A. 放大弹窗里：Ctrl + 滚轮 -> 只缩放 Y 轴 ====
        # 检查obj是否是任意一个放大窗口的视口（从字典中判断）
        if obj in self._zoom_viewport_map:
            vb = self._zoom_viewport_map[obj]  # 取出当前视口对应的ViewBox

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

            return super().eventFilter(obj, event)
        if obj is not self.waveform_widget.viewport():
            return super().eventFilter(obj, event)

        # 1) Shift + 左键按下：开始框选
        if (event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton
                and (event.modifiers() & Qt.ShiftModifier)):
            self._waveform_rb_active = True
            self._waveform_rb_origin = event.pos()
            if self._waveform_rb is None:
                self._waveform_rb = QRubberBand(QRubberBand.Rectangle, self._waveform_rb_host)
            self._waveform_rb.setGeometry(QRect(self._waveform_rb_origin, QSize()))
            self._waveform_rb.show()
            return True  # 截断事件，避免传递

        # 2) 拖动时更新选框（仅在“框选进行中”）
        if (event.type() == QEvent.MouseMove
                and self._waveform_rb_active
                and self._waveform_rb is not None
                and self._waveform_rb.isVisible()):
            rect = QRect(self._waveform_rb_origin, event.pos()).normalized()
            self._waveform_rb.setGeometry(rect)
            return True

        # 3) 左键松开：结束框选（仅在“框选进行中”）
        if (event.type() == QEvent.MouseButtonRelease
                and event.button() == Qt.LeftButton):
            if not (self._waveform_rb_active and self._waveform_rb and self._waveform_rb.isVisible()):
                # 不是框选态的普通点击：不处理，防止误高亮/误弹窗
                return False

            # 结束框选
            sel_rect = self._waveform_rb.geometry()
            self._waveform_rb.hide()
            self._waveform_rb_active = False

            # 3.1 像素宽度阈值（避免单击或极窄框触发）
            if sel_rect.width() < self._waveform_min_px:
                return True

            # 3.2 像素 -> 数据坐标（只在本 waveform 图上）
            def vp_x_to_data_x(px):
                scene_pt = self.waveform_widget.mapToScene(QPoint(px, sel_rect.center().y()))
                data_pt = self.waveform_widget.getPlotItem().vb.mapSceneToView(scene_pt)
                return data_pt.x()

            x_min = vp_x_to_data_x(sel_rect.left())
            x_max = vp_x_to_data_x(sel_rect.right())
            if x_min > x_max:
                x_min, x_max = x_max, x_min

            vb = self.waveform_widget.getPlotItem().vb
            vis_x0, vis_x1 = vb.viewRange()[0]  # 当前可见的 X 范围
            x_min = max(vis_x0, min(x_min, vis_x1))  # clamp 下界
            x_max = max(vis_x0, min(x_max, vis_x1))  # clamp 上界

            # 3.3 时间宽度阈值（避免极窄窗）
            if (x_max - x_min) < self._waveform_min_sec:
                return True

            # 仅在 waveform 原图上高亮，并弹出只含 waveform 的放大窗
            region = pg.LinearRegionItem(values=(x_min, x_max),
                                         brush=self._waveform_hl_brush,
                                         pen=self._waveform_hl_pen,
                                         movable=False)
            self.waveform_widget.addItem(region)
            self._waveform_regions.append(region)
            self._show_waveform_zoom_dialog(x_min, x_max, region)
            return True

        return super().eventFilter(obj, event)

    def _apply_waveform_page_guardrails(self, page_start: float, page_end: float):
        """把ViewBox 的护栏限制到【当前页窗口】内"""
        try:
            if page_end <= page_start:
                return
            vb = self.waveform_widget.getPlotItem().vb
            # 给一点极小余量，避免浮点边界导致的“卡边”（可按需调小/去掉）
            eps = 1e-6
            vb.setLimits(
                xMin=page_start - eps,
                xMax=page_end + eps,
                minXRange=min(0.2, max(0.01, (page_end - page_start) * 0.1)),  # 最小可缩到当前页宽度的 10%，上限 0.2s
                maxXRange=(page_end - page_start)  # 最大不能超过一整页
            )
            # 将视窗也切回这一页（防止仍停留在上一页的范围）
            self.waveform_widget.setXRange(page_start, page_end, padding=0)
        except Exception:
            pass

    #放大弹窗 _show_waveform_zoom_dialog
    def _show_waveform_zoom_dialog(self, x_min: float, x_max: float, region: pg.LinearRegionItem):
        """弹出只包含waveform的非模态放大窗；关闭后移除对应高亮"""
        dialog = QDialog(self)

        # 计算绝对时间与字符串
        meas_date = self.raw_data.info['meas_date']
        sec_start = round(float(x_min), 3)
        sec_end = round(float(x_max), 3)
        ms_start = int(round(sec_start * 1000))
        ms_end = int(round(sec_end * 1000))
        abs_start = meas_date + timedelta(milliseconds=ms_start)
        abs_end = meas_date + timedelta(milliseconds=ms_end)
        start_str = abs_start.strftime("%Y-%m-%d %H:%M:%S") + f".{ms_start % 1000:03d}"
        end_str = abs_end.strftime("%Y-%m-%d %H:%M:%S") + f".{ms_end % 1000:03d}"

        # 放大窗标题改为“当前通道名 [时间范围]”，便于区分不同通道的放大窗口
        ch_name = ""
        try:
            if hasattr(self, "channel_names") and hasattr(self, "current_channel"):
                if (
                        isinstance(self.channel_names, (list, tuple))
                        and isinstance(self.current_channel, int)
                        and 0 <= self.current_channel < len(self.channel_names)
                ):
                    ch_name = str(self.channel_names[self.current_channel])
        except Exception as ex:
            # 出错时记录日志，但不中断放大窗逻辑
            try:
                QLLogging.log.exception(f"_show_waveform_zoom_dialog get channel name error: {ex}")
            except Exception:
                pass
            ch_name = ""

        title_prefix = ch_name if ch_name else "waveform"
        dialog.setWindowTitle(f"{title_prefix}  [{start_str}  ~  {end_str}]")

        layout = QVBoxLayout(dialog)
        date_axis = DateAxis(meas_date, orientation='bottom')
        zoom_plot = pg.PlotWidget(axisItems={'bottom': date_axis})
        layout.addWidget(zoom_plot)
        dialog.resize(900, 320)

        #获取图上的数据，筛选框选区域的数据
        src_pi = self.waveform_widget.getPlotItem()
        dst_pi = zoom_plot.getPlotItem()

        # 遍历数据项并复制框选区域的数据
        for it in src_pi.listDataItems():
            try:
                x, y = it.getData()
            except Exception:
                continue
            if x is None or y is None or len(x) == 0:
                continue


            # 修改
            # if len(self.original_y) != 0:
            #     y = self.original_y
            x, y = it.getData()

            # 只保留框选区域的数据
            mask = (x >= x_min) & (x <= x_max)
            x_filtered = x[mask]
            y_aligned = y[:len(mask)]
            y_filtered = y_aligned[mask]



            # 绘制筛选后的数据到放大窗口
            if len(x_filtered) > 0:
                pen = it.opts.get('pen', None)
                dst_pi.addItem(pg.PlotDataItem(x=x_filtered, y=y_filtered, pen=pen))

        # 处理图像项（如果存在）
        for it in src_pi.items:
            if isinstance(it, pg.ImageItem):
                img = pg.ImageItem()
                img.setImage(it.image)
                img.setTransform(it.transform())
                dst_pi.addItem(img)

        zoom_plot.setBackground("w")
        zoom_plot.showGrid(x=True, y=True, alpha=0.3)
        zoom_plot.setMouseEnabled(x=True, y=False)  # 放大窗也可滚轮缩放（只限 X）
        zoom_plot.setXRange(x_min, x_max, padding=0)
        zoom_plot.setMenuEnabled(False)  # 禁用 pyqtgraph 自带的 PlotMenu

        # 记录放大窗的 viewport 和 ViewBox，用来处理 Ctrl+滚轮
        # 修复：改用字典存储所有窗口的视口和ViewBox，而非单值变量
        vp = zoom_plot.viewport()
        vp.installEventFilter(self)
        self._zoom_viewport = vp
        self._zoom_viewport_map[vp] = zoom_plot.getPlotItem().vb  # 存入字典

        # 放大窗关闭 -> 移除对应高亮
        dialog.finished.connect(lambda _: self._cleanup_waveform_zoom_dialog(dialog))
        dialog.show()

        self._waveform_zoom_windows.append(dialog)
        self._waveform_dialog_region[dialog] = region

    def _cleanup_waveform_zoom_dialog(self, dialog):
        """关闭放大窗时，把对应的高亮从原图移除"""
        try:
            region = self._waveform_dialog_region.pop(dialog, None)
            if region is not None:
                try:
                    self.waveform_widget.removeItem(region)
                except Exception:
                    pass
                try:
                    self._waveform_regions.remove(region)
                except ValueError:
                    pass
            try:
                self._waveform_zoom_windows.remove(dialog)
            except ValueError:
                pass
        except Exception:
            pass

    def preprocess_result_data_source(self, result_data_source):
        """
        处理柱形图数据源，剔除通道名称前面的字符（如 'Ch1_'）。

        :param bar_data_source: 原始柱形图数据源
        :return: 处理后的柱形图数据源
        """
        processed_data = []
        for data in result_data_source:
            # 提取通道名称并剔除前缀（如 'Ch1_'）
            if 'Channel' in data:
                original_channel = data['Channel']
                # 剔除前缀部分
                processed_channel = original_channel.split('_', 1)[-1]
                data['Channel'] = processed_channel
            processed_data.append(data)
        return processed_data

    def set_result_data_source(self, result_data_source):
        """
        设置柱形图数据源。
        :param bar_data_source: 包含每个通道频段功率数据的列表
        """
        if result_data_source:
            self.result = self.preprocess_result_data_source(result_data_source)

    #amplitude_changed
    def on_amplitude_changed(self, value):
        if self.visited == 0:
            self.visited = self.visited + 1
            x, self.original_y = self.waveform_plot.getData()
        QLLogging.log.debug(f"on_amplitude_changed called with value: {value}")
        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, f'amplitude_changed:{value}', 0)
        waveform_vb = self.waveform_widget.getPlotItem().getViewBox()
        x_min, x_max = waveform_vb.viewRange()[0]  # 获取当前x轴范围
        x, y = self.waveform_plot.getData()  # 获取当前数据
        if x is None or y is None:
            QLLogging.log.warning("Waveform data is not initialized yet.")
            return

        # 获取当前显示范围内的数据
        mask = (x >= x_min) & (x <= x_max)
        visible_ydata = y[mask]

        if len(visible_ydata) > 0:
            # 计算数据范围
            ymin = visible_ydata.min()
            ymax = visible_ydata.max()
            # 添加10%的边距
            margin = (ymax - ymin) * 0.1

        # 根据当前x轴范围筛选数据
        if value == "Auto":
            # 获取当前显示范围内的数据
            if len(visible_ydata) > 0:
                waveform_vb.setYRange(ymin - margin, ymax + margin)
                waveform_vb.enableAutoRange(axis=pg.ViewBox.YAxis)
            else:
                waveform_vb.enableAutoRange(axis=pg.ViewBox.YAxis)  # 自动范围
        else:
            try:
                amp = float(value.lstrip('±'))
                # 问题:导致原图的y轴改变
                waveform_vb.setYRange(-amp, amp, padding=0)  # 设置手动范围

            except ValueError:
                waveform_vb.enableAutoRange(axis=pg.ViewBox.YAxis)  # 自动范围

    def set_raw_data(self, raw, start_time, end_time):
        self.raw_data = raw
        self.start_time = start_time  ##显示的开始时间
        self.total_start_time = start_time  ##用户选择的时间的开始
        self.total_end_time = end_time
        self.fs = raw.info['sfreq']
        self.total_duration = (end_time - start_time).total_seconds()
        self.update_total_pages()
        self.end_time = self.start_time + timedelta(seconds=self.page_duration)  ##一页的显示结束时间

        self.slider_widget.label_start_time.setText('00:00:00')
        hours = int(self.total_duration // 3600)
        minutes = int((self.total_duration % 3600) // 60)
        seconds = int(self.total_duration % 60)
        self.slider_widget.label_end_time.setText(f"{hours:02}:{minutes:02}:{seconds:02}")
        self.slider_widget.time_slider.setRange(0, int(self.total_duration - self.page_duration))
        self.result = []

    def update_plot_below(self):
        """
        根据当前通道更新柱形图，动态确定要绘制的列。
        """

        # # 获取当前通道名称
        # current_channel_name = self.channel_names[self.current_channel]
        #
        # self.plot_below(current_channel_name, self.bar_data_source)

    def set_channel_names(self, names):
        self.channel_names = names
        if self.current_channel >= len(names):
            self.current_channel = 0
        self.update_channel_label()

    def update_channel_label(self):
        if self.channel_names and 0 <= self.current_channel < len(self.channel_names):
            self.channel_selector.setText(self.channel_names[self.current_channel])
        else:
            self.channel_selector.setText(f"Channel {self.current_channel + 1}")

    def scroll_time(self):
        if not self.raw_data:
            return
        pos = self.slider_widget.time_slider.value()

        # 确保两个时间对象都有相同的时区设置
        meas_date = self.raw_data.info['meas_date']
        if meas_date.tzinfo is None:
            meas_date = meas_date.replace(tzinfo=timezone.utc)

        if hasattr(self, 'waveform_left_text'):
            print(meas_date)
            self.waveform_left_text.set_meas_date(meas_date)
        if hasattr(self, 'time_axis'):
            self.time_axis.set_meas_date(meas_date)

        total_start = self.total_start_time
        if total_start is not None and total_start.tzinfo is None:
            total_start = total_start.replace(tzinfo=timezone.utc)

        # 计算开始时间
        start_time = (total_start - meas_date).total_seconds() + pos

        # 计算结束时间
        end_time = start_time + self.page_duration

        self._apply_waveform_page_guardrails(start_time, end_time)

        if not self.is_manually_changing_page:
            self.get_current_page()
            self.page_changed.emit(self.current_page)
        #
        # # 设置 4 个均匀分布的时间刻度
        # time_ticks = np.linspace(start_time, end_time, 4)  # 生成 4 个均匀分布的时间点
        # # 转换时间点为时间字符串
        # time_strings = []
        # for t in time_ticks:
        #     # 计算实际时间
        #     actual_time = self.raw_data.info['meas_date'] + timedelta(seconds=float(t))
        #     # 格式化为 HH:MM:SS
        #     time_str = actual_time.strftime('%H:%M:%S')
        #     time_strings.append(time_str)
        #
        # # 设置刻度位置和标签
        # axis = self.waveform_widget.getAxis('bottom')
        # ticks = [(time_ticks[i], time_strings[i]) for i in range(len(time_ticks))]
        # axis.setTicks([ticks, ticks])
        if len(self.wave_times) == 0:
            return
        # 更新波形图数据
        time_mask = (self.wave_times >= start_time) & (self.wave_times <= end_time)

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
        self.wave_data, self.wave_times = self.raw_data[ch_name, start_idx: end_idx]
        if len(self.wave_times) == 0:
            return

        self.waveform_plot.clear()
        self.waveform_plot.setData(self.wave_times, self.wave_data[0])
        self.current_page = 1
        self.page_changed.emit(self.current_page)
        self.slider_widget.time_slider.setTotalPages(self.total_pages)
        self.slider_widget.time_slider.setValue(0)  # 时间滑块
        # self.amplitude_selector.currentTextChanged.connect(self.on_amplitude_changed)

        self.scroll_time()  # 更新时间滑块位置

    def show_prev_channel(self):
        """
        显示上一通道的波形和柱形图。
        """
        QLLogging.log.debug(f"{self.class_name} show_prev_channel called")
        try:
            if self.raw_data is None:
                return

            if not self.channel_names:
                QMessageBox.warning(self.win, "No Channel Selected", "Please select at least one channel to view")
                return
            # 如果只有一个或没有通道，直接返回
            if len(self.channel_names) <= 1:
                return

            # self.plot_area.hide()
            # 显示加载提示
            self.loading_overlay.showLoading()
            QApplication.processEvents()  # 确保UI更新

            # 更新当前通道索引
            self.current_channel = (self.current_channel - 1) % len(self.channel_names)

            self.update_waveform()
            self.update_plot_below()
            self.update_channel_label()

            self.plot_area.show()
            # 隐藏加载提示
            self.loading_overlay.hideLoading()

        except IndexError as e:
            QLLogging.log.error(f"Index error when switching channels: {str(e)}")
            QMessageBox.warning(self.win, "Error", "Error accessing channel data")

        except Exception as e:
            QLLogging.log.exception(f"Unexpected error in show_prev_channel: {str(e)}")
            QMessageBox.warning(self.win, "Error", f"An unexpected error occurred: {str(e)}")

    def show_next_channel(self):
        """
        显示下一通道的波形和柱形图。
        """
        QLLogging.log.debug(f"{self.class_name} show_next_channel called")
        try:
            if self.raw_data is None:
                return
            if not self.channel_names:
                QMessageBox.warning(self.win, "No Channel Selected", "Please select at least one channel to view")
                return

            if len(self.channel_names) <= 1:
                return

            # self.plot_area.hide()
            # 显示加载提示
            self.loading_overlay.showLoading()
            QApplication.processEvents()  # 确保UI更新

            # 更新当前通道索引
            self.current_channel = (self.current_channel + 1) % len(self.channel_names)

            self.update_waveform()
            self.update_plot_below()
            self.update_channel_label()

            self.plot_area.show()
            # 隐藏加载提示
            self.loading_overlay.hideLoading()

        except IndexError as e:
            QLLogging.log.error(f"Index error when switching channels: {str(e)}")
            QMessageBox.warning(self.win, "Error", "Error accessing channel data")

        except Exception as e:
            QLLogging.log.exception(f"Unexpected error in show_next_channel: {str(e)}")
            QMessageBox.warning(self.win, "Error", f"An unexpected error occurred: {str(e)}")

    def get_current_time_range(self):
        return self.start_time, self.end_time

    def set_page_duration(self, seconds):
        """
        设置每页显示的秒数，并跳转到第一页重新显示画面。
        """
        self.page_duration = seconds
        self.update_total_pages()
        self.slider_widget.time_slider.setMinimum(0)
        self.slider_widget.time_slider.setMaximum(int(self.total_duration - self.page_duration))

    def update_total_pages(self):
        """
        根据总时间和每页显示的秒数计算总页数。
        """
        if self.raw_data and self.total_duration > 0:
            self.total_pages = int(np.ceil(self.total_duration / self.page_duration))
        else:
            self.total_pages = 1

    def get_total_pages(self):
        """
        获取总页数。
        """
        return self.total_pages

    def get_current_page(self):
        """
        获取当前页码。
        """
        ts_value = self.slider_widget.time_slider.value()
        ts_min = self.slider_widget.time_slider.minimum()
        ts_max = self.slider_widget.time_slider.maximum()
        if ts_max == ts_min:
            self.current_page = 1
        else:
            page = int((ts_value - ts_min) / (ts_max - ts_min) * (self.get_total_pages() - 1) + 1)
            self.current_page = min(page, self.get_total_pages())

    def set_current_page(self, page):
        """
        设置显示指定页，并更新画面。
        """
        try:
            if 1 <= page <= self.total_pages:
                self.current_page = page
            self.is_manually_changing_page = True
            pos = (self.current_page - 1) * self.page_duration
            self.slider_widget.time_slider.setValue(int(pos))
            self.page_changed.emit(self.current_page)
            self.is_manually_changing_page = False
        except Exception as e:
            stack_trace = traceback.format_exc()
            QLLogging.log.error(
                f"{self.class_name} Error in set_current_page: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )
            QMessageBox.critical(
                self.win,
                "Navigation Error",
                f"Failed to set current page: {str(e)}"
            )

    def show_prev_page(self):
        """
        显示上一页。
        """
        QLLogging.log.debug(f"{self.class_name} show_prev_page called")
        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'show_prev_page', 0)
        try:
            if self.current_page > 1:
                self.current_page -= 1
            else:
                self.current_page = self.total_pages  # 循环到最后一页
            self.is_manually_changing_page = True
            pos = (self.current_page - 1) * self.page_duration
            self.slider_widget.time_slider.setValue(int(pos))
            self.page_changed.emit(self.current_page)
            self.is_manually_changing_page = False
        except Exception as e:
            stack_trace = traceback.format_exc()
            QLLogging.log.error(
                f"{self.class_name} Error in show_prev_page: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )
            QMessageBox.critical(
                self.win,
                "Navigation Error",
                f"Failed to show previous page: {str(e)}"
            )

    def show_next_page(self):
        """
        显示下一页。
        """
        QLLogging.log.debug(f"{self.class_name} show_next_page called")
        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'show_next_page', 0)
        try:
            if self.current_page < self.total_pages:
                self.current_page += 1
            else:
                self.current_page = 1  # 循环到第一页
            self.is_manually_changing_page = True
            pos = (self.current_page - 1) * self.page_duration
            self.slider_widget.time_slider.setValue(int(pos))
            self.page_changed.emit(self.current_page)
            self.is_manually_changing_page = False

        except Exception as e:
            stack_trace = traceback.format_exc()
            QLLogging.log.error(
                f"{self.class_name} Error in show_next_page: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )
            QMessageBox.critical(
                self.win,
                "Navigation Error",
                f"Failed to show next page: {str(e)}"
            )

    def show_first_page(self):
        """
        显示第一页。
        """
        QLLogging.log.debug(f"{self.class_name} show_first_page called")
        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'show_first_page', 0)
        try:
            self.current_page = 1
            self.is_manually_changing_page = True
            pos = (self.current_page - 1) * self.page_duration
            self.slider_widget.time_slider.setValue(int(pos))
            self.page_changed.emit(self.current_page)
            self.is_manually_changing_page = False
        except Exception as e:
            stack_trace = traceback.format_exc()
            QLLogging.log.error(
                f"{self.class_name} Error in show_first_page: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )
            QMessageBox.critical(
                self.win,
                "Navigation Error",
                f"Failed to show first page: {str(e)}"
            )

    def show_last_page(self):
        """
        显示最后一页。
        """
        QLLogging.log.debug(f"{self.class_name} show_last_page called")
        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'show_last_page', 0)
        try:
            self.current_page = self.total_pages
            self.is_manually_changing_page = True
            pos = (self.current_page - 1) * self.page_duration
            self.slider_widget.time_slider.setValue(int(pos))
            self.page_changed.emit(self.current_page)
            self.is_manually_changing_page = False
        except Exception as e:
            stack_trace = traceback.format_exc()
            QLLogging.log.error(
                f"{self.class_name} Error in show_last_page: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )
            QMessageBox.critical(
                self.win,
                "Navigation Error",
                f"Failed to show last page: {str(e)}"
            )

    def save_data_without_path(self):
        return

    def save_figure_without_path(self):
        return


class RelativeTimeAxis(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.meas_date = None  # 记录起始绝对时间

    def set_meas_date(self, date):
        self.meas_date = date

    def tickStrings(self, values, scale, spacing):
        """
        pyqtgraph 会自动调用这个方法来获取刻度文本。
        values: x轴的坐标值列表（这里是相对时间的秒数）
        """
        if self.meas_date is None:
            return [str(v) for v in values]

        strings = []
        for v in values:
            try:
                # 将 x轴的秒数 加到 起始时间 上
                curr_time = self.meas_date + timedelta(seconds=v)
                # 根据缩放级别(spacing)自动调整格式
                if spacing < 1:
                    # 如果刻度间隔小于1秒，显示毫秒
                    strings.append(curr_time.strftime('%H:%M:%S.%f')[:-3])
                else:
                    # 否则只显示到秒
                    strings.append(curr_time.strftime('%H:%M:%S'))
            except Exception:
                strings.append("")
        return strings


class BasicalAnalysis(QWidget):

    def __init__(self, title=None, channel_name=None, parent=None):
        super().__init__()
        self.setWindowTitle("QLanalyser")
        self.setStyleSheet(ControlStyle.get_widget_style())
        self.setGeometry(100, 100, 1440, 900)  # 初始窗口大小
        self.title = title
        self.channel_name = channel_name  # 当前选择的通道名称

        self.viewer = None  # 中间显示图片的界面
        self.raw = None
        self.meas_dat = None  # 起始时间
        self.total_duration = None  # 转换为整数秒   数据总时长（秒）
        self.end_time = None  # 终止时间
        self.win = None

        self.class_name = self.__class__.__name__

        self.init_ui()
        self.connect_actions()

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
        content_layout.setSpacing(int(self.devicePixelRatio() * 10))
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
        self.channel_selector = StyledCheckboxWidget(
            channel_names=self.channel_name,
            label_text="Channel Select"
        )
        self.left_layout.addWidget(self.channel_selector)
        self.channel_selector.setFixedHeight(300)  # 设置固定高度

        # 分割线
        separator_between_channel_and_time = QFrame()
        separator_between_channel_and_time.setFrameShape(QFrame.HLine)
        separator_between_channel_and_time.setStyleSheet("background-color: #a9a9a9;")
        separator_between_channel_and_time.setFixedHeight(1)
        self.left_layout.addWidget(separator_between_channel_and_time)

        # 时间选择
        self.time_selector = TimeRangeSelector()
        self.time_selector.setFixedHeight(150)  # 设置固定高度
        self.left_layout.addWidget(self.time_selector)

        self.sidebar.content_layout.addLayout(self.left_layout)  # 关键：将left_layout加入侧边栏
        # 将侧边栏添加到主体布局（原直接添加left_layout的位置改为添加sidebar）
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
        self.h_layout.addWidget(self.viewer)
        # 添加分割线
        separator_below_display = QFrame()
        separator_below_display.setFrameShape(QFrame.HLine)
        separator_below_display.setStyleSheet("background-color: #d3d3d3;")
        separator_below_display.setFixedHeight(1)
        center_and_bottom_layout.addWidget(separator_below_display)

        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(10, 20, 20, 20)
        bottom_layout.setSpacing(int(self.devicePixelRatio() * 20))  # 设置按钮之间的间距为 20 像素

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
        content_layout.addWidget(center_and_bottom_widget, stretch=7)  # 中央显示区域占 7 份

    def import_raw(self, raw):
        """
        导入原始数据，并设置默认的时间范围。
        """
        QLLogging.log.debug("Importing raw data ...")

        try:
            self.raw = raw.copy()
            # 获取原始数据的起始时间和终止时间
            self.meas_dat = raw.info['meas_date']  # 起始时间
            self.total_duration = int(raw.times[-1])  # 转换为整数秒   数据总时长（秒）

            self.end_time = self.meas_dat + timedelta(seconds=self.total_duration)  # 终止时间

            # 设置时间选择器的默认时间范围
            self.time_selector.set_time_range(self.meas_dat, self.end_time)
            self.time_selector.set_max_time(self.end_time)
            self.time_selector.set_min_time(self.meas_dat)

            # 获取所有通道名称  ##根据数据设置通道选择范围
            channel_names = raw.info['ch_names']
            self.channel_selector.set_setEnabled_channels(channel_names)
        except Exception as e:
            stack_trace = traceback.format_exc()
            # 记录详细的错误信息
            QLLogging.log.error(
                f"basic analysis import raw failed: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )
            QMessageBox.critical(self.win, "import raw failed", f"Import raw failed: {str(e)}")
            # self.enable_analysis_buttons()

    def connect_actions(self):
        """连接按钮的槽函数"""
        self.analyse_btn.clicked.connect(self.on_analyse_clicked)  # 开始分析按钮
        self.save_data_btn.clicked.connect(self.on_savedata)  # 保存数据按钮
        self.save_pic_btn.clicked.connect(self.on_savefig)  # 保存图片按钮

        self.nav_buttons_widget.first_pushButton.clicked.connect(self.viewer.show_first_page)  # 第一页
        self.nav_buttons_widget.last_pushButton.clicked.connect(self.viewer.show_last_page)  # 最后一页
        self.nav_buttons_widget.button_previous.clicked.connect(self.viewer.show_prev_page)  # 上一页
        self.nav_buttons_widget.button_next.clicked.connect(self.viewer.show_next_page)  # 下一页

        self.viewer.page_changed.connect(self.nav_buttons_widget.set_current_page)
        self.nav_buttons_widget.combo_time_scale.currentTextChanged.connect(self.time_scale_change)
        self.nav_buttons_widget.button_goto_epoch.clicked.connect(self.update_display_goto_epoch)

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

    def on_savedata(self):
        self.disable_buttons()
        self.viewer.save_data_without_path()
        self.enable_buttons()

    def on_savefig(self):
        self.disable_buttons()
        try:
            start_time1 = time.time()
            self.viewer.save_figure_without_path()
            end_time = time.time() - start_time1
            print("总时长：", end_time)
        finally:
            self.enable_buttons()  # ✅ 确保一定会恢复按钮

    def time_scale_change(self):
        """
        当 Time Scale 复选框的值改变时，更新页面持续时间。
        """
        # 获取当前选择的时间刻度（秒）
        self.scale_seconds = self.nav_buttons_widget.get_time_scale_hours()
        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, f'scale_seconds:{self.scale_seconds}', 0)

        # 如果选择的不是 "All"，更新页面持续时间
        if self.scale_seconds is not None:
            self.scale_seconds = min(self.scale_seconds, self.total_duration)
        else:
            # 如果选择的是 "All"，将页面持续时间设置为总持续时间
            self.scale_seconds = self.total_duration

        self.viewer.set_page_duration(self.scale_seconds)

        self.total_pages = int(np.ceil(self.total_duration / self.scale_seconds))
        self.nav_buttons_widget.set_total_pages(self.total_pages)
        self.viewer.slider_widget.time_slider.setTotalPages(self.total_pages)
        self.viewer.update_waveform()
        self.viewer.scroll_time()

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

    def on_worker_result_ready(self, values=None):
        QLLogging.log.debug(f"{self.class_name}: Analysis finished.")
        try:
            self.viewer.set_raw_data(self.raw, self.user_start, self.user_end)
            # 将计算结果传递给 viewer
            self.viewer.set_result_data_source(values)
            self.progressBar_widget.hide()
            self.viewer.show()

            self.viewer.set_page_duration(self.scale_seconds)
            self.viewer.set_channel_names(self.channel_selector.get_selected_channels())

            self.viewer.update_waveform()
            self.viewer.update_plot_below()

            # 恢复信号
            self.enable_buttons()

            self.worker = None
            gc.collect()  # 手动回收

        except Exception as e:
            stack_trace = traceback.format_exc()
            # 记录详细的错误信息
            QLLogging.log.error(
                f"{self.class_name} on_worker_result_ready failed: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )

            QMessageBox.critical(self.win, f"{self.class_name} failed", f"{self.class_name} failed: {str(e)}")
            # 恢复分析按钮
            self.analyse_btn.blockSignals(False)
            self.analyse_btn.setEnabled(True)

    def on_worker_progress(self, progress):
        """
        处理 Worker 的进度信号。
        :param progress: 当前进度百分比
        """
        # print("progress:",progress)
        self.progressBar.setGreaterValue(progress)

    def on_worker_error(self, error_message):
        """
        处理 Worker 的错误信号。
        :param error_message: 错误信息
        """
        # 记录错误日志
        stack_trace = traceback.format_exc()
        # 记录详细的错误信息
        QLLogging.log.error(
            f"{self.class_name} computation worker error occurred: {str(error_message)}\n"
            f"Stack trace:\n{stack_trace}"
        )

        # 向用户显示错误消息
        QMessageBox.critical(
            self.win,
            "Error",
            f"An error occurred during computation:\n{error_message}"
        )
        # 恢复信号
        # 恢复分析按钮
        self.analyse_btn.blockSignals(False)
        self.analyse_btn.setEnabled(True)
        print(f"Error in {self.class_name} computation worker: {error_message}")

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

    def closeEvent(self, event):
        """重写closeEvent,在窗口关闭时清理资源"""
        try:
            # 1. 清理图形资源
            if hasattr(self, 'viewer'):
                if hasattr(self.viewer, 'figure'):
                    self.viewer.figure.clear()
                if hasattr(self.viewer, 'canvas'):
                    self.viewer.canvas.close()
                if hasattr(self.viewer, 'waveform_canvas'):
                    self.viewer.waveform_canvas.clear()
                # 清理数据
                self.viewer.raw_data = None
                self.viewer.bar_data_source = []
                self.viewer.channel_names = []

            # 2. 清理工作线程
            if hasattr(self, 'worker'):
                self.worker.quit()
                self.worker.wait()
                self.worker = None

            # 3. 清理其他大型数据
            self.raw = None
            self.viewer = None

            # 5. 调用父类的closeEvent
            super().closeEvent(event)
            # 7. 确保窗口被销毁
            self.close()
        except Exception as e:
            # print(f"Error during cleanup: {str(e)}")
            stack_trace = traceback.format_exc()
            # 记录详细的错误信息
            QLLogging.log.error(
                f"Error during BasicalAnalysis closeEvent: {str(e)}\n"
                f"Stack trace:\n{stack_trace}"
            )
            # 仍然关闭窗口
            event.accept()


class CollapsibleSidebar(QWidget):
    """可折叠的侧边栏组件"""

    def __init__(self, parent=None, title="Sidebar", initial_state=True):
        """
        初始化侧边栏

        参数:
            parent: 父窗口
            title: 侧边栏标题
            initial_state: 初始状态 (True=展开, False=折叠)
        """
        super().__init__(parent)

        # 设置侧边栏基本属性
        self.setObjectName("collapsibleSidebar")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # 记录侧边栏状态
        self.is_expanded = initial_state
        self.original_width = 400  # 默认展开宽度，可根据需要调整
        self.collapsed_width = 35  # 折叠后宽度，仅显示按钮

        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(10)

        # 创建折叠按钮
        self.toggle_button = QPushButton("<<")
        self.toggle_button.setObjectName("sidebarToggleButton")
        self.toggle_button.setStyleSheet("""
            QPushButton {
                border: none;
                padding: 5px;
                font-weight: bold;

                border-radius: 4px;
                min-width: 20px;
                min-height: 20px;
            }
            QPushButton:hover {
                /* 鼠标悬停时的样式 */
                background-color: #E3EAF8;
            }
        """)
        self.toggle_button.move(5, 5)
        self.toggle_button.setFixedSize(30, 30)  # 固定按钮尺寸
        self.toggle_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toggle_button.clicked.connect(self.toggle_sidebar)

        # 创建内容区域
        self.content_widget = QWidget()
        self.content_widget.setObjectName("sidebarContent")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # 将组件添加到主布局
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.content_widget)

        # 初始化侧边栏状态
        self.update_sidebar_state()

    def add_widget(self, widget):
        """向侧边栏添加控件"""
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        """向侧边栏添加布局"""
        self.content_layout.addLayout(layout)

    def set_expanded_width(self, width):
        """设置侧边栏展开时的宽度"""
        self.original_width = width
        if self.is_expanded:
            self.setFixedWidth(self.original_width)

    def toggle_sidebar(self):
        """切换侧边栏展开/折叠状态"""
        self.is_expanded = not self.is_expanded
        self.update_sidebar_state()

    def update_sidebar_state(self):
        """更新侧边栏状态（展开/折叠）"""
        if self.is_expanded:
            # 展开侧边栏
            self.content_widget.show()
            self.setFixedWidth(self.original_width)
            self.toggle_button.setText("<<")
            self.toggle_button.move(5, 5)  # 展开时定位到左上角
        else:
            # 折叠侧边栏
            self.content_widget.hide()
            self.setFixedWidth(self.collapsed_width)
            self.toggle_button.setText(">>")
            self.toggle_button.move(5, 5)  # 折叠时定位到左上角
