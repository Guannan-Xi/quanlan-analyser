""" 弹出HRV分析窗口
    发出信号，然后其进行分析
    进度条页面出现，完成之后变为新的界面
"""
from PyQt5 import QtGui

from .Infrastructure.QLWidgets.QLGifProgressBar import GifProgressBar

"""使用QGraphicsView展示图片"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QProgressBar, QApplication,
    QLineEdit, QInputDialog, QComboBox, QSpacerItem, QSizePolicy, QMessageBox, QListView, QToolButton,

    QMenu, QAction, QTextEdit, QGraphicsView, QGraphicsScene, QDialog

)
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QDateTime, QCoreApplication, pyqtSlot, QTimer
from PyQt5.QtGui import QPixmap, QImage, QPainter
from .Infrastructure.log.QLLogging import QLLogging
from .Control_Style import ControlStyle
import datetime

import os.path
import warnings
warnings.filterwarnings("ignore")
import AR_neurokit2 as nk
from AR_neurokit2.hrv.hrv_frequency import _hrv_frequency_show
from AR_neurokit2.hrv.hrv_nonlinear import _hrv_nonlinear_show
from AR_neurokit2.hrv.hrv_utils import _hrv_format_input
from AR_neurokit2.hrv.intervals_process import intervals_process
from AR_neurokit2.hrv.intervals_utils import _intervals_successive

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import signal
import os
import io
import time
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from concurrent.futures import ProcessPoolExecutor, as_completed

HRV_FREQUENCY_KWARGS = {
    "ulf": (0, 0.02),
    "vlf": (0.02, 0.15),
    "lf": (0.15, 1.5),
    "hf": (1.5, 5),
    "vhf": (5, 10),
    "normalize": False,
    "interpolation_rate": 100,
}

def calculate_hrv_time(peaks, sampling_rate):
    """计算HRV频域指标并返回结果DataFrame"""
    # 计算HRV频域指标，不保存图片
    hrv_time = nk.hrv_time(
        peaks,
        sampling_rate=sampling_rate,
        show=False,  # 不显示图表
        plot_path=None  # 不保存图表
    )
    return hrv_time

def calculate_hrv_frequency(peaks, sampling_rate):
    """计算HRV频域指标并返回结果DataFrame和fig"""
    # 计算HRV频域指标，不保存图片
    # hrv_frequency, fig = nk.hrv_frequency(
    #     peaks,
    #     sampling_rate=sampling_rate,
    #     show=True,  # 不显示图表
    #     plot_path=None  # 不保存图表
    # )

    hrv_frequency, fig = nk.hrv_frequency(
        peaks,
        sampling_rate=sampling_rate,
        show=False,
        plot_path=None,
        return_fig=True,
        **HRV_FREQUENCY_KWARGS,
    )


    
    return hrv_frequency, fig


def plot_hrv_frequency(peaks, sampling_rate, hrv_frequency):
    """Build the frequency-domain figure after numeric HRV work is complete."""
    rri, rri_time, _ = _hrv_format_input(peaks, sampling_rate=sampling_rate)
    rri, rri_time, processed_rate = intervals_process(
        rri,
        intervals_time=rri_time,
        interpolate=True,
        interpolation_rate=HRV_FREQUENCY_KWARGS["interpolation_rate"],
    )
    frequency_band = [
        HRV_FREQUENCY_KWARGS["ulf"],
        HRV_FREQUENCY_KWARGS["vlf"],
        HRV_FREQUENCY_KWARGS["lf"],
        HRV_FREQUENCY_KWARGS["hf"],
        HRV_FREQUENCY_KWARGS["vhf"],
    ]
    max_frequency = np.max([np.max(i) for i in frequency_band])
    row = hrv_frequency.iloc[0]
    out_bands = {
        "ULF": row["HRV_ULF"],
        "VLF": row["HRV_VLF"],
        "LF": row["HRV_LF"],
        "HF": row["HRV_HF"],
        "VHF": row["HRV_VHF"],
    }
    _, _, fig = _hrv_frequency_show(
        rri,
        out_bands,
        ulf=HRV_FREQUENCY_KWARGS["ulf"],
        vlf=HRV_FREQUENCY_KWARGS["vlf"],
        lf=HRV_FREQUENCY_KWARGS["lf"],
        hf=HRV_FREQUENCY_KWARGS["hf"],
        vhf=HRV_FREQUENCY_KWARGS["vhf"],
        sampling_rate=processed_rate,
        normalize=HRV_FREQUENCY_KWARGS["normalize"],
        max_frequency=max_frequency,
        plot_path=None,
    )
    return fig

def calculate_hrv_nonlinear(peaks, sampling_rate):
    """计算HRV非线性指标并返回结果DataFrame和fig"""

    # 计算HRV非线性指标，不保存图片
    hrv_nonlinear = nk.hrv_nonlinear(
        peaks,
        sampling_rate=sampling_rate,
        show=False,
        plot_path=None,  # 不保存图表
        complexity_backend="rust",  # 使用Rust版本
    )
    fig = None
    return hrv_nonlinear, fig


def plot_hrv_nonlinear(peaks, sampling_rate, hrv_nonlinear):
    """Build the nonlinear Poincare figure without recomputing HRV metrics."""
    rri, rri_time, rri_missing = _hrv_format_input(peaks, sampling_rate=sampling_rate)
    successive_mask = None
    if rri_missing:
        successive_mask = _intervals_successive(rri, intervals_time=rri_time)

    out = {}
    row = hrv_nonlinear.iloc[0]
    for column in hrv_nonlinear.columns:
        key = column[4:] if column.startswith("HRV_") else column
        out[key] = row[column]

    fig = _hrv_nonlinear_show(
        rri,
        rri_time=rri_time,
        rri_missing=rri_missing,
        out=out,
        rri_prev=rri[:-1],
        rri_next=rri[1:],
        successive_mask=successive_mask,
    )
    return fig



def save_hrv_data(hrv_data, result_path, file_name, img_format):
    if img_format == 'csv':
        """将HRV频域分析结果保存为CSV文件"""
        hrv_csv_path = os.path.join(result_path, f'{file_name}.csv')
        hrv_data.to_csv(hrv_csv_path, index=False)
    elif img_format == 'npy':
        """将HRV频域分析结果保存为NPY文件"""
        hrv_csv_path = os.path.join(result_path, f'{file_name}.npy')
        np.save(hrv_csv_path, hrv_data)
    return hrv_csv_path

def RR_interval_distribution_plot(r_peaks_times):
    try:
        # 创建 RR 间隔分布图
        fig = plt.figure(figsize=(20, 12))

        # 计算R-R间隔（单位：秒）
        rr_intervals = np.diff(r_peaks_times)

        # 将RR间隔转换为毫秒
        rr_intervals_ms = rr_intervals * 1000  # 转换为毫秒

        # 方法1：使用四分位数范围(IQR)方法去除异常值
        def remove_outliers_iqr(data, k=1.5):
            Q1 = np.percentile(data, 25)
            Q3 = np.percentile(data, 75)
            IQR = Q3 - Q1
            lower_bound = Q1 - k * IQR
            upper_bound = Q3 + k * IQR
            return data[(data >= lower_bound) & (data <= upper_bound)]

        # 在计算统计指标前先处理异常值
        rr_intervals_ms_cleaned = remove_outliers_iqr(rr_intervals_ms)

        # 使用清理后的数据计算统计指标
        mean_rr = np.mean(rr_intervals_ms_cleaned)
        std_rr = np.std(rr_intervals_ms_cleaned)
        median_rr = np.median(rr_intervals_ms_cleaned)

        # 创建bins，从0到150ms，每5ms一个bin
        bins = np.arange(0, 141, 2)  # 0, 5, 10, ..., 150
        #
        # 创建直方图
        n, bins, patches = plt.hist(rr_intervals_ms, bins=bins, color='skyblue', alpha=0.75)
        #
        # 获取y轴的最大值，用于设置标记的位置
        ymax = plt.ylim()[1]
        mark_position = ymax * 0.06

        # 添加箱型图风格的标记
        # 中心线（median）
        median_line = plt.plot([median_rr, median_rr], [mark_position - ymax * 0.05, mark_position + ymax * 0.05],
                               'g--', linewidth=2)[0]
        # 箱子（mean ± SD）
        sd_line = plt.plot([mean_rr - std_rr, mean_rr + std_rr], [mark_position, mark_position],
                           'k--', linewidth=2)[0]
        plt.plot([mean_rr - std_rr, mean_rr - std_rr], [mark_position - ymax * 0.025, mark_position + ymax * 0.025],
                 'k--', linewidth=2)
        plt.plot([mean_rr + std_rr, mean_rr + std_rr], [mark_position - ymax * 0.025, mark_position + ymax * 0.025],
                 'k--', linewidth=2)
        # 均值点和线
        mean_line = plt.plot([mean_rr, mean_rr], [mark_position - ymax * 0.05, mark_position + ymax * 0.05],
                             'k--', linewidth=2)[0]
        plt.plot(mean_rr, mark_position, 'ko', markersize=10)

        # 设置图表属性
        plt.title('Distribution of RR Intervals', fontsize=26)
        plt.xlabel('RR Interval (ms)', fontsize=24)
        plt.ylabel('Frequency', fontsize=24)
        plt.xlim(40, 140)

        # 添加图例
        plt.legend([mean_line, median_line, sd_line], [
            f'Mean: {mean_rr:.1f} ms',
            f'Median: {median_rr:.1f} ms',
            f'SD: {std_rr:.1f} ms'
        ], fontsize=24)

        plt.grid(True, alpha=0.3)

        # 在内存中保存图像
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)

        # 临时保存文件（后面需要删除）保存图片
        # png_path = os.path.join("", 'hrv_analysis.png')
        # plt.savefig(png_path, format="jpg", dpi=300, bbox_inches='tight')
        plt.close()

    except Exception as e:
        QLLogging.log.exception(f"RR_interval_distribution_plot error, the reason is as follows: {e}")

    return buffer, fig


class HrvAnalysisThread(QThread):
    progress_updated = pyqtSignal(int) # 定义信号用于更新进度条
    analysis_finished = pyqtSignal(dict) # 定义信号用于通知分析完成，传递hrv的分析结果
    image_show_view = pyqtSignal(bytes) # 定义信号用于传递需要展示的图片
    memory_error = pyqtSignal(str)    # 新增内存错误信
    thread_aborted = pyqtSignal()   # 新增：线程被中止的信号

    def __init__(self, results):
        super().__init__()
        self.peaks = results['Peaks']
        self.sampling_rate = results['sampling_rate']
        self.r_peaks_times = results['r_peaks_times']
        self.progressBar = None
        self._scheduled_progress = 0
        self._is_aborted = False  # 添加中止标志

    def abort(self):
        """中止线程执行"""
        self._is_aborted = True
        self.quit()
        self.wait(1000)  # 等待1秒让线程结束
        if self.isRunning():
            self.terminate()  # 强制终止
            self.wait()

    def emit_and_schedule(self, current_progress, remaining_times):
        if self._is_aborted:
            return
        if current_progress <= self._scheduled_progress:
            return
        self._scheduled_progress = current_progress
        self.progress_updated.emit(current_progress)

    def run(self):
        """重写run方法，在此方法中执行耗时操作"""
        """这里还是有点慢，需要进行优化"""
        start_time = time.time()
        try:
            total_steps = 4  # 假设HRV分析有三个主要步骤
            current_step = 0

            # 检查是否已被中止
            if self._is_aborted:
                self.thread_aborted.emit()
                return

            # Step 1: 时间域分析
            hrv_time = calculate_hrv_time(self.peaks, self.sampling_rate)
            progress = 3
            self.progress_updated.emit(progress)
            self.emit_and_schedule(progress + 1, 17)

            QLLogging.log.debug("hrv_time finish")

            # Step 2: 频率域分析
            hrv_frequency, hrv_frequency_fig = calculate_hrv_frequency(self.peaks, self.sampling_rate)
            progress = 25
            self.progress_updated.emit(progress)
            self.emit_and_schedule(progress + 1, 60)

            QLLogging.log.debug("hrv_frequency finish")

            # Step 3: 非线性分析
            hrv_nonlinear, hrv_nonlinear_fig = calculate_hrv_nonlinear(self.peaks, self.sampling_rate)
            progress = 90
            self.progress_updated.emit(progress)
            self.emit_and_schedule(progress + 1, 8)

            QLLogging.log.debug("hrv_nonlinear finish")

            hrv_frequency_fig = plot_hrv_frequency(self.peaks, self.sampling_rate, hrv_frequency)
            hrv_nonlinear_fig = plot_hrv_nonlinear(self.peaks, self.sampling_rate, hrv_nonlinear)

            # 绘制RR图形
            buffer, rr_fig = RR_interval_distribution_plot(self.r_peaks_times)

            # 发送分析结果
            result = {
                'hrv_time': hrv_time,
                'hrv_frequency': hrv_frequency,
                'hrv_nonlinear': hrv_nonlinear,
                'hrv_frequency_fig': hrv_frequency_fig,
                'hrv_nonlinear_fig': hrv_nonlinear_fig,
                'rr_fig': rr_fig,
            }

            # 传递图片给UI进行展示
            self.image_show_view.emit(buffer.getvalue())

            progress = 100
            self.progress_updated.emit(progress)
            QLLogging.log.debug("result finish")

            self.analysis_finished.emit(result)

        except MemoryError as mem_err:
            # 捕获内存不足的异常
            progress = 100
            self.progress_updated.emit(progress)
            self.memory_error.emit("Insufficient memory occurred while calculating HRV nonlinear metrics. Please slice the data or increase system memory and try again.")
            QLLogging.log.exception(f"MemoryError in calculate_hrv_nonlinear: {mem_err}")
            return

        except Exception as e:
            if not self._is_aborted:  # 只有非中止导致的异常才记录
                progress = 100
                self.progress_updated.emit(progress)
                QLLogging.log.exception(f"HrvAnalysisThread error, the reason is as follows: {e}")
            return

        end_time = time.time()
        print(f"run time: {end_time - start_time}")

# 自定义 QGraphicsView 子类以支持自动缩放
class ScalableGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

    def resizeEvent(self, event):
        """窗口大小变化时自动调整图像比例"""
        super().resizeEvent(event)
        if self.scene():
            self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)

class Ui_ECG_HRV(object):
    def __init__(self):
        super().__init__()

        self.hrv_thread = None # 用于存储当前的分析进程
        self.ecg_analysis_worker_results = None
        self.hrv_result = {} # 保存hrv的分析结果
        self.figures = []
        self.rr_interval_plt = None
        self._is_closing = False

    def setupUi(self, ECG_HRV):
        ECG_HRV.setObjectName("ECG_HRV")
        ECG_HRV.setMinimumSize(1400, 800)
        # 设置一下背景颜色
        ECG_HRV.setStyleSheet(ControlStyle.get_widget_style())

        # 设置整体垂直布局
        self.ui_ecg_hrv_vlayout = QVBoxLayout(ECG_HRV)
        self.ui_ecg_hrv_vlayout.setObjectName("ui_ecg_hrv_vlayout")
        self.ui_ecg_hrv_vlayout.setContentsMargins(32, 32, 32, 32)
        self.ui_ecg_hrv_vlayout.setSpacing(0)

        # 创建 HRV 标题
        self.label_hrv = QLabel(ECG_HRV)
        self.label_hrv.setObjectName("label_hrv")
        self.label_hrv.setMinimumSize(1300, 30)
        self.label_hrv.setFixedHeight(30)
        self.label_hrv.setStyleSheet(ControlStyle.get_label_word_style())
        ControlStyle.get_font_size(self.label_hrv, 12)

        self.view_widget = QWidget(ECG_HRV)
        self.view_widget.setMinimumSize(1300, 650)
        view_widget_vlayout = QVBoxLayout(self.view_widget)
        view_widget_vlayout.setContentsMargins(0, 0, 0, 0)  # 移除边距

        # 创建展示图片的窗口
        scene = QGraphicsScene()
        # 加载图片，可以是本地路径或资源路径
        pixmap = QPixmap("./resource/picture/Frame.png")
        # 创建一个 QGraphicsPixmapItem 并设置 QPixmap
        pixmap_item = scene.addPixmap(pixmap)
        # 可选：调整场景的矩形范围以适应图像大小
        scene.setSceneRect(pixmap_item.boundingRect())
        # 创建QGraphicsView和QGraphicsScene
        self.view = ScalableGraphicsView(scene, self.view_widget)
        view_widget_vlayout.addWidget(self.view)
        # 将 QGraphicsScene 设置给 QGraphicsView
        self.view.setScene(scene)
        # 取消水平和垂直滚动条
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 强制图片适应视图大小（关键步骤）
        self.view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)  # 保持宽高比
        # 启用抗锯齿（可选，提升显示效果）
        self.view.setRenderHint(QPainter.Antialiasing)
        # 显示视图
        self.view_widget.show()

        # 创建一个进度条窗口
        self.progressBar_widget = QWidget(ECG_HRV)
        self.progressBar_widget.setMinimumSize(1300, 650)

        progressBar_vlayout = QVBoxLayout(self.progressBar_widget)
        progressBar_vlayout.setContentsMargins(65, 0, 65, 0)
        progressBar_vlayout.setAlignment(Qt.AlignCenter)
        progressBar_vlayout.setSpacing(0)

        progressBar_label_hlayout = QHBoxLayout()
        progressBar_label_hlayout.setContentsMargins(0, 0, 0, 0)
        progressBar_label_hlayout.setSpacing(0)

        self.label_progressBar = QLabel(ECG_HRV)
        self.label_progressBar.setText("分析中")
        self.label_progressBar.setObjectName("label_progressBar")
        self.label_progressBar.setMinimumSize(50, 20)
        self.label_progressBar.setStyleSheet(ControlStyle.get_redo_set_pushButton_style())
        ControlStyle.get_font_size(self.label_progressBar, 10)

        progressBar_label_hlayout.addWidget(self.label_progressBar, alignment=Qt.AlignLeft)
        # progressBar_label_hlayout.addWidget(self.label_progressBar_count, alignment=Qt.AlignRight)

        self.progressBar = GifProgressBar()
        self.progressBar.setParent(ECG_HRV)
        self.progressBar.setObjectName("progressBar")
        self.progressBar.setMinimumSize(258, 16)

        self.progressBar.setStyleSheet(ControlStyle.get_progressBar_style())

        progressBar_vlayout.addWidget(self.progressBar)
        progressBar_vlayout.addLayout(progressBar_label_hlayout)

        # 下面是一个水平布局的窗口
        save_pic_data_hlayout = QHBoxLayout()
        save_pic_data_hlayout.setContentsMargins(0, 0, 0, 0)
        save_pic_data_hlayout.setSpacing(24)
        save_pic_data_hlayout.setAlignment(Qt.AlignCenter)

        # save pic
        self.pushButton_save_pic = QPushButton(ECG_HRV)
        self.pushButton_save_pic.setObjectName("pushButton_save_pic")
        self.pushButton_save_pic.setFixedSize(145, 40)
        self.pushButton_save_pic.setStyleSheet(ControlStyle.get_pushButton_style_white())
        ControlStyle.get_font_size(self.pushButton_save_pic, 10)
        self.pushButton_save_pic.setEnabled(False)  # 初始状态禁用

        # save data
        self.pushButton_save_data = QPushButton(ECG_HRV)
        self.pushButton_save_data.setObjectName("pushButton_save_data")
        self.pushButton_save_data.setFixedSize(145, 40)
        self.pushButton_save_data.setStyleSheet(ControlStyle.get_pushButton_style_white())
        ControlStyle.get_font_size(self.pushButton_save_data, 10)
        self.pushButton_save_data.setEnabled(False)  # 初始状态禁用

        save_pic_data_hlayout.addWidget(self.pushButton_save_pic)
        save_pic_data_hlayout.addWidget(self.pushButton_save_data)

        self.view_widget.hide()
        # self.progressBar_widget.hide()

        self.ui_ecg_hrv_vlayout.addWidget(self.label_hrv, 1)
        self.ui_ecg_hrv_vlayout.addWidget(self.view_widget, 50)
        self.ui_ecg_hrv_vlayout.addWidget(self.progressBar_widget, 50)
        self.ui_ecg_hrv_vlayout.addStretch(1)  # 添加一个拉伸项，将底部内容推到底部
        self.ui_ecg_hrv_vlayout.addLayout(save_pic_data_hlayout)

        self.retranslateUi(ECG_HRV)
        self.connect_actions()

        self.start_hrv_analysis()

    def retranslateUi(self, ECG_HRV):
        _translate = QCoreApplication.translate
        ECG_HRV.setWindowTitle(_translate("ECG_HRV", "HRV分析弹窗"))

        self.label_hrv.setText(_translate("ECG_HRV", "HRV                This step will take a relatively long time. Please wait patiently."))
        self.pushButton_save_pic.setText(_translate("ECG_HRV", "Save pic"))
        self.pushButton_save_data.setText(_translate("ECG_HRV", "Save data"))

    def connect_actions(self):
        """连接的槽函数"""
        self.pushButton_save_data.clicked.connect(self.save_data)
        self.pushButton_save_pic.clicked.connect(self.save_pic)
        self.progressBar.valueChanged.connect(self.onProgressChanged)

    def start_hrv_analysis(self):
        # 获取数据,数据已经拿到了
        # 创建并显示进度对话框
        self.view_widget.hide()
        self.progressBar_widget.show()
        # 创建并启动HRV分析线程
        try:
            self.hrv_thread = HrvAnalysisThread(self.ecg_analysis_worker_results)
            self.hrv_thread.progress_updated.connect(self.update_progress)
            self.hrv_thread.analysis_finished.connect(self.on_analysis_finished)
            self.hrv_thread.image_show_view.connect(self.image_display_view)
            self.hrv_thread.memory_error.connect(self.handle_memory_error)  # 连接内存错误信号
            self.hrv_thread.start()
        except Exception as e:
            QLLogging.log.exception(f"HrvAnalysisThread start error, the reason is as follows: {e}")

    def handle_memory_error(self, error_msg):
        """处理内存错误 - 在主线程中显示弹窗"""
        try:
            self.label_hrv.setText("")
            # 在主线程中显示内存错误
            parent = QApplication.activeWindow()
            result = QMessageBox.critical(
                parent,
                "Insufficient Memory",
                error_msg,
                QMessageBox.Ok
            )
            # 当用户点击OK后关闭当前页面
            if result == QMessageBox.Ok:
                for widget in QApplication.topLevelWidgets():
                    if widget.objectName() == "ECG_HRV":
                        widget.close()
        except Exception as e:
            QLLogging.log.exception(f"Error handling memory error: {e}")

    def update_progress(self, value):
        """更新进度对话框"""
        if self._is_closing:  # 如果窗口正在关闭，不再更新UI
            return
        self.progressBar.setGreaterValue(value)

    def on_analysis_finished(self, result):
        if self._is_closing:  # 如果窗口正在关闭，不再处理结果
            return
        """处理分析完成后的结果"""
        print("HRV Analysis Finished")
        self.progressBar_widget.hide()
        self.view_widget.show()
        # 显示在界面上
        self.hrv_result = result
        # 移除提示文字
        self.label_hrv.setText("")

    def image_display_view(self, image_data):
        """将图片显示在view中"""
        try:
            if isinstance(image_data, QPixmap):
                pixmap = image_data
            else:
                hrv_image = QImage()
                hrv_image.loadFromData(image_data)
                pixmap = QPixmap.fromImage(hrv_image)
            scene = QGraphicsScene()
            # 创建一个 QGraphicsPixmapItem 并设置 QPixmap
            pixmap_item = scene.addPixmap(pixmap)
            scene.setSceneRect(pixmap_item.boundingRect())
            # 将 QGraphicsScene 设置给 QGraphicsView
            self.view.setScene(scene)

            # 启用抗锯齿以获得更清晰的图像
            self.view.setRenderHint(QtGui.QPainter.Antialiasing)
            self.view.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

            # 设置视图属性以适应窗口大小
            self.view.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
            self.view.setResizeAnchor(QGraphicsView.AnchorViewCenter)

            # 初始适应窗口
            self.fit_image_to_view()

            # 连接窗口大小变化事件
            self.resizeEvent = self.on_resize

            # self.view.resize(1300, 650)
        except Exception as e:
            QLLogging.log.exception(f"image_display_view error, the reason is as follows: {e}")

    def fit_image_to_view(self):
        """将图片适应视图大小"""
        if self.view.scene():
            # 使用KeepAspectRatio保持图片比例
            self.view.fitInView(self.view.scene().itemsBoundingRect(), Qt.KeepAspectRatio)

    def on_resize(self, event):
        """窗口大小变化时重新适应图像"""
        self.fit_image_to_view()
        super().resizeEvent(event)

    def save_pic(self):
        """保存图片分析结果"""
        from .SavePicCPM import SavePictureDialog
        from datetime import datetime
        # 获取当前日期和时间
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d%H%M%S")
        save_pic_dialog = SavePictureDialog()
        if save_pic_dialog.exec_() == QDialog.Accepted:
            try:
                # 获取到要保存的路径，dpi和图片格式
                params = save_pic_dialog.get_save_parameters()
                img_format = params['format'].lower().replace('.', '')
                dpi = params['resolution']
                base_path = params['path']  # 用户选择的根路径
                # 定义目标文件夹名称
                target_folder = "ECG_HRV_pic"
                # 拼接完整的文件夹路径（根路径 + 目标文件夹）
                folder_path = os.path.join(base_path, target_folder)
                # 若文件夹不存在，则创建（递归创建，避免路径中多级文件夹不存在的问题）
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path, exist_ok=True)
                    QLLogging.log.debug(f"创建文件夹成功：{folder_path}")
                # 拼接每张图片的完整保存路径（文件夹路径 + 文件名 + 格式）
                save_hrv_frequency_dir = os.path.join(folder_path, f"hrv_frequency_{formatted_time}.{img_format}")
                save_hrv_nonlinear_dir = os.path.join(folder_path, f"hrv_nonlinear_{formatted_time}.{img_format}")
                save_hrv_analysis_dir = os.path.join(folder_path, f"hrv_analysis_{formatted_time}.{img_format}")

                # 刷新 GUI
                QApplication.processEvents()

                # 需要进行保存结果
                self.hrv_result['hrv_frequency_fig'].savefig(save_hrv_frequency_dir, dpi=dpi, format=img_format)
                self.hrv_result['hrv_nonlinear_fig'].savefig(save_hrv_nonlinear_dir, dpi=dpi, format=img_format)
                self.hrv_result['rr_fig'].savefig(save_hrv_analysis_dir, dpi=dpi, format=img_format)

                parent = QApplication.activeWindow()
                # 提示用户保存成功
                QMessageBox.information(parent, "Save Successful", "The pictures have been saved successfully.")

            except ValueError as e:
                QLLogging.log.exception(f"open_save_picture_ui, error: {e}")

    def save_data(self):
        """保存hrv分析的结果 保存文件，格式为：.csv, .npy"""
        from .SavePicCPM import SaveDataDialog
        from datetime import datetime
        # 获取当前日期和时间
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d%H%M%S")
        data_dialog = SaveDataDialog()

        if data_dialog.exec_() == QDialog.Accepted:
            try:
                # 获取保存参数
                params = data_dialog.get_save_parameters()
                # print(params)
                save_dir = params['path']
                file_format = params['format'].lower().replace('.', '')

                # 定义目标文件夹名称
                target_folder = "ECG_HRV_data"
                # 拼接完整的文件夹路径
                folder_path = os.path.join(save_dir, target_folder)

                # 若文件夹不存在，则创建
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path, exist_ok=True)
                    QLLogging.log.debug(f"创建文件夹成功：{folder_path}")
                # 刷新 GUI
                QApplication.processEvents()

                # 保存各类HRV数据到目标文件夹
                save_hrv_data(self.hrv_result['hrv_time'], folder_path, f"hrv_time_{formatted_time}", file_format)
                save_hrv_data(self.hrv_result['hrv_frequency'], folder_path, f"hrv_frequency_{formatted_time}",file_format)
                save_hrv_data(self.hrv_result['hrv_nonlinear'], folder_path, f"hrv_nonlinear_{formatted_time}",file_format)

                parent = QApplication.activeWindow()
                # 提示用户保存成功
                QMessageBox.information(parent, "Save Successful", "The data has been saved successfully.")

            except Exception as e:
                QLLogging.log.exception(f"save_data, error: {e}")

    def onProgressChanged(self, value):
        """
        当进度条的值发生变化时调用此函数。
        根据进度条的值决定按钮是否可用。
        """
        if value >= self.progressBar.maximum():
            self.pushButton_save_data.setEnabled(True)
            self.pushButton_save_pic.setEnabled(True)
        else:
            self.pushButton_save_data.setEnabled(False)
            self.pushButton_save_pic.setEnabled(False)

    def cleanup(self):
        """专门的清理方法，可以在外部调用"""
        self._is_closing = True
        self.abort_analysis()

        # 清理matplotlib图形
        for fig in self.figures:
            if hasattr(fig, 'close'):
                fig.close()

        # 清理其他资源
        self.figures.clear()
        self.hrv_result.clear()

        import gc
        gc.collect()

    def abort_analysis(self):
        """中止分析过程"""
        QLLogging.log.debug("Abort the analysis process")
        try:
            # 停止线程
            if self.thread_run.isRunning():
                self.hrv_thread.abort()

            # 清理数据
            for attr in ['peaks', 'sampling_rate', 'r_peaks_times']:
                if hasattr(self.hrv_thread, attr):
                    delattr(self.hrv_thread, attr)

            # 强制垃圾回收
            import gc
            gc.collect()

        except Exception as e:
            print(f"Error during abort: {str(e)}")
            QLLogging.log.exception(f"Error during abort: {str(e)}")

    def closeEvent(self, event):
        """重写closeEvent以在关闭窗口时完全清理所有资源"""
        self._is_closing = True  # 设置关闭标志
        try:
            # 1. 如果正在分析，先中止分析
            if hasattr(self, 'hrv_thread') and self.hrv_thread:
                print("Attempting to abort thread...")
                # 断开所有信号连接
                try:
                    self.hrv_thread.progress_updated.disconnect()
                except:
                    pass
                try:
                    self.hrv_thread.analysis_finished.disconnect()
                except:
                    pass
                try:
                    self.hrv_thread.image_show_view.disconnect()
                except:
                    pass
                try:
                    self.hrv_thread.memory_error.disconnect()
                except:
                    pass

                # 请求线程终止
                self.hrv_thread.abort()
                # 等待线程结束，但设置超时
                if self.hrv_thread.isRunning():
                    if not self.hrv_thread.wait(500):  # 等待500ms
                        print("Thread not responding, terminating...")
                        self.hrv_thread.terminate()
                        self.hrv_thread.wait(300)  # 再等待300ms

                del self.hrv_thread

            # 2. 清理线程相关资源
            if hasattr(self, 'hrv_thread'):
                if self.hrv_thread.isRunning():
                    self.hrv_thread.quit()
                    self.hrv_thread.wait()
                del self.hrv_thread

            # 3. 清理数据资源
            data_attributes = [
                'hrv_thread',
                'ecg_analysis_worker_results',
                'hrv_result',
                'figures',
                'rr_interval_plt'
            ]

            for attr in data_attributes:
                if hasattr(self, attr):
                    delattr(self, attr)

            # 4. 强制多次垃圾回收
            import gc
            gc.collect()
            gc.collect()

            # 5. 打印内存使用情况（用于调试）
            import psutil
            process = psutil.Process()
            QLLogging.log.debug(f"Memory usage after cleanup: {process.memory_info().rss / 1024 / 1024:.2f} MB")

            # 6. 接受关闭事件
            event.accept()

        except Exception as e:
            QLLogging.log.exception(f"Error during window closing: {str(e)}")
            import traceback
            traceback.print_exc()
            event.accept()  # 即使发生错误也关闭窗口
