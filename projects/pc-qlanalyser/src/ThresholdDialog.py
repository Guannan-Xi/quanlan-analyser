""" 弹出用户自定设置阈值的窗口
    两个参数：Threshold, Duration
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QProgressBar, QApplication,
    QLineEdit, QInputDialog, QComboBox, QSpacerItem, QSizePolicy, QMessageBox, QListView, QToolButton,
    QMenu, QAction, QTextEdit, QGraphicsView, QGraphicsScene, QDialog, QSlider, QSpinBox, QDoubleSpinBox

)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QDateTime, QCoreApplication, pyqtSlot
from PyQt5.QtGui import QPixmap, QImage, QPainter
from .Infrastructure.log.QLLogging import QLLogging
from .Control_Style import ControlStyle
import datetime

import os.path
import warnings
warnings.filterwarnings("ignore")
# import AR_neurokit2 as nk

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import signal
import os
import io
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from concurrent.futures import ProcessPoolExecutor, as_completed

def create_no_click_slider(parent):
    """创建禁用点击跳转的滑块"""
    slider = QSlider(parent)
    
    # 保存原始的 mousePressEvent 方法
    original_mousePressEvent = slider.mousePressEvent
    
    def custom_mousePressEvent(event):
        """自定义鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            # 获取滑块样式选项
            from PyQt5.QtWidgets import QStyleOptionSlider, QStyle
            opt = QStyleOptionSlider()
            slider.initStyleOption(opt)
            
            # 计算滑块手柄的矩形区域
            handle_rect = slider.style().subControlRect(
                QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, slider
            )
            
            # 只有点击在滑块手柄上时才处理事件
            if handle_rect.contains(event.pos()):
                original_mousePressEvent(event)
            # 否则忽略点击事件
        else:
            original_mousePressEvent(event)
    
    # 替换 mousePressEvent 方法
    slider.mousePressEvent = custom_mousePressEvent
    return slider


class ThresholdWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()

    def setupUi(self, parent=None):
        self.setObjectName("SetThresholdDialog")
        # 设置一下背景颜色
        self.setStyleSheet(ControlStyle.get_widget_style())

        # 设置整体垂直布局
        self.ui_set_threshold_vlayout = QVBoxLayout(self)
        self.ui_set_threshold_vlayout.setObjectName("ui_set_threshold_vlayout")
        self.ui_set_threshold_vlayout.setContentsMargins(30, 32, 24, 32)
        self.ui_set_threshold_vlayout.setSpacing(10)

        self.threshold_widget = QLabel(parent)
        self.threshold_widget.setObjectName("threshold_widget")
        self.threshold_widget.setMinimumSize(200, 32)
        self.threshold_widget.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.threshold_widget, 12)

        # Threshold  label  Slider lineEdit
        threshold_hlayout = QHBoxLayout()
        threshold_hlayout.setContentsMargins(0, 0, 0, 0)
        threshold_hlayout.setSpacing(0)

        threshold_vlayout = QVBoxLayout()
        threshold_vlayout.setContentsMargins(0, 0, 0, 0)
        threshold_vlayout.setSpacing(10)

        self.label_threshold = QLabel(parent)
        self.label_threshold.setObjectName("label_threshold")
        self.label_threshold.setFixedSize(200, 32)
        self.label_threshold.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_threshold, 10)

        self.spinbox_threshold = QDoubleSpinBox(parent)
        self.spinbox_threshold.setObjectName("spinbox_threshold")
        self.spinbox_threshold.setMinimumSize(50, 32)
        self.spinbox_threshold.setFixedWidth(100)
        self.spinbox_threshold.setStyleSheet(ControlStyle.get_doublespinbox_style())
        self.spinbox_threshold.setRange(1, 4.0)
        self.spinbox_threshold.setDecimals(1)  # 设置小数位数为1位
        self.spinbox_threshold.setSingleStep(0.1)  # 设置步长为0.1
        self.spinbox_threshold.setValue(2.0)  # 默认值为2

        threshold_hlayout.addWidget(self.label_threshold, alignment=Qt.AlignLeft)
        threshold_hlayout.addWidget(self.spinbox_threshold)

        self.slider_threshold = create_no_click_slider(parent)
        self.slider_threshold.setObjectName("slider_threshold")
        self.slider_threshold.setStyleSheet(ControlStyle.get_slider_style())
        self.slider_threshold.setMinimumSize(100, 32)
        self.slider_threshold.setOrientation(Qt.Horizontal)  # 设置为水平方向
        self.slider_threshold.setRange(15, 40)
        self.slider_threshold.setValue(20)  # 默认值为20

        threshold_vlayout.addLayout(threshold_hlayout)
        threshold_vlayout.addWidget(self.slider_threshold)
        
        # Duration label lineEdit
        duration_hlayout = QHBoxLayout()
        duration_hlayout.setContentsMargins(0, 0, 0, 0)
        duration_hlayout.setSpacing(0)

        # duration_vlayout = QVBoxLayout()
        # duration_vlayout.setContentsMargins(0, 5, 0, 5)
        # duration_vlayout.setSpacing(10)

        self.label_duration = QLabel(parent)
        self.label_duration.setObjectName("label_duration")
        self.label_duration.setFixedSize(200, 32)
        self.label_duration.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_duration, 10)

        self.spinbox_duration = QSpinBox(parent)
        self.spinbox_duration.setObjectName("spinbox_duration")
        self.spinbox_duration.setMinimumSize(50, 32)
        self.spinbox_duration.setFixedWidth(100)
        self.spinbox_duration.setStyleSheet(ControlStyle.get_spinbox_style())
        self.spinbox_duration.setRange(0, 10)
        self.spinbox_duration.setValue(3)  # 默认值为3秒
        self.spinbox_duration.setEnabled(False)  # 禁用输入框

        duration_hlayout.addWidget(self.label_duration, alignment=Qt.AlignLeft)
        duration_hlayout.addWidget(self.spinbox_duration)

        # self.slider_duration = QSlider(parent)
        # self.slider_duration.setObjectName("slider_duration")
        # self.slider_duration.setStyleSheet(ControlStyle.get_slider_style())
        # self.slider_duration.setMinimumSize(100, 32)
        # self.slider_duration.setOrientation(Qt.Horizontal)  # 设置为水平方向
        # self.slider_duration.setRange(0, 10)
        # self.slider_duration.setValue(3)  # 默认值为3秒
        # self.slider_duration.setEnabled(False)  # 禁用滑块

        # duration_vlayout.addLayout(duration_hlayout)
        # duration_vlayout.addWidget(self.slider_duration)

        # apply 按钮
        # self.pushButton_apply = QPushButton(parent)
        # self.pushButton_apply.setObjectName("label_duration")
        # self.pushButton_apply.setFixedSize(150, 32)
        # self.pushButton_apply.setStyleSheet(ControlStyle.get_pushButton_style())
        # ControlStyle.get_font_size(self.pushButton_apply, 10)

        self.ui_set_threshold_vlayout.addWidget(self.threshold_widget,alignment=Qt.AlignLeft)
        self.ui_set_threshold_vlayout.addLayout(threshold_vlayout)
        # self.ui_set_threshold_vlayout.addLayout(duration_vlayout)
        # self.ui_set_threshold_vlayout.addWidget(self.pushButton_apply, alignment=Qt.AlignHCenter)

        self.retranslateUi()
        self.connect_actions()

    def retranslateUi(self):
        _translate = QCoreApplication.translate
        # SetThresholdDialog.setWindowTitle(_translate("SetThresholdDialog", "Set Threshold"))
        # self.pushButton_apply.setText(_translate("SetThresholdDialog", "Apply"))
        self.label_threshold.setText(_translate("SetThresholdDialog", "Threshold:"))
        self.label_duration.setText(_translate("SetThresholdDialog",  "Duration(s):"))
        self.threshold_widget.setText(_translate("SetThresholdDialog", "Set Threshold"))

    def connect_actions(self):  # 功能连接方法
        # 修改双向绑定以处理滑块和浮点数之间的转换
        self.slider_threshold.valueChanged.connect(self.on_slider_threshold_changed)
        self.spinbox_threshold.valueChanged.connect(self.on_spinbox_threshold_changed)
        
        # Duration的双向绑定
        # self.slider_duration.valueChanged.connect(self.spinbox_duration.setValue)
        # self.spinbox_duration.valueChanged.connect(self.slider_duration.setValue)

    def on_slider_threshold_changed(self, value):
        """滑块值改变时更新SpinBox"""
        # 将滑块值15-40映射到1.5-4.0
        float_value = value / 10.0
        self.spinbox_threshold.blockSignals(True)  # 防止循环触发
        self.spinbox_threshold.setValue(float_value)
        self.spinbox_threshold.blockSignals(False)

    def on_spinbox_threshold_changed(self, value):
        """SpinBox值改变时更新滑块"""
        # 将浮点值1.5-4.0映射到15-40
        int_value = int(value * 10)
        self.slider_threshold.blockSignals(True)  # 防止循环触发
        self.slider_threshold.setValue(int_value)
        self.slider_threshold.blockSignals(False)
