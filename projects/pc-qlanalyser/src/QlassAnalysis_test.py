from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget, QPushButton, QListWidget,
                             QProgressBar, QLabel, QComboBox, QPlainTextEdit, QSizePolicy,
                             QGridLayout, QCheckBox, QLineEdit, QFileDialog, QInputDialog,
                             QHBoxLayout, QVBoxLayout, QSlider, QFrame, QSpacerItem, QMenuBar,
                             QApplication, QComboBox, QWidget, QVBoxLayout, QListView, QShortcut,
                             QMenu, QToolButton, QAction, QScrollArea, QDialog, QTimeEdit,)
from PyQt5.QtCore import (QThread, pyqtSignal, pyqtSlot, QRect, Qt, QTime,
                          QCoreApplication, QMetaObject, QThreadPool, QSize,
                          QPropertyAnimation, QRect, pyqtProperty)
from PyQt5.QtGui import QIcon, QFont, QPixmap, QKeySequence, QMovie
from PyQt5.QtWidgets import QStyle, QStyleOptionSlider, QGraphicsDropShadowEffect, QMessageBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import hashlib

from .Infrastructure.log.QLLogging import QLLogging
from .Domain.HistoricalWarehouse import SleepScoreWH
# from .CustomControls import IconWithTextWidget
from .Control_Style import ControlStyle
from .CustomControls import TimeSliderWidget
from datetime import timedelta

import matplotlib.pyplot as plt
import matplotlib.lines

import numpy as np
import pandas as pd
import datetime
import sys
import os
import time
import random
import mne
import joblib
import pickle
from contextlib import redirect_stdout


from .Qlass.my_functions import *
import os
import scipy.signal
from scipy.signal import stft

from .MatplotEventHandler import MatplotlibEventHandler_
from .utils import SaveUtils, get_image_format, setup_short_cut

from mne.filter import resample
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

from joblib import Parallel, delayed
import mne
import pyqtgraph as pg


import sys
import time
import numpy as np
from PyQt5.QtGui import QImage, QPainter, QPixmap
from PyQt5.QtCore import Qt, QSize
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
import matplotlib.pyplot as plt
import scipy.signal

class NavButtonsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI(parent)
        self.setAcceptDrops(True)
    def initUI(self, parent=None):
        # 整体布局为水平布局
        self.nav_button_widget_hlayout = QHBoxLayout(self)
        self.nav_button_widget_hlayout.setObjectName("nav_button_widget_hlayout")
        self.nav_button_widget_hlayout.setContentsMargins(0, 0, 0, 0)
        self.nav_button_widget_hlayout.setSpacing(0)

        # first button
        self.first_pushButton = QPushButton(parent)
        self.first_pushButton.setObjectName("first_pushButton")
        self.first_pushButton.setMinimumSize(60, 32)
        self.first_pushButton.setStyleSheet(ControlStyle.get_nav_pushButton_style())
        ControlStyle.get_font_size(self.first_pushButton, 10)

        # 创建一个空白区域
        spacerItem1 = QSpacerItem(12, 32)

        nav_page_hlayout = QHBoxLayout()
        nav_page_hlayout.setContentsMargins(0, 0, 0, 0)
        nav_page_hlayout.setSpacing(0)
        # < button
        self.button_previous = QPushButton(parent)
        self.button_previous.setObjectName("button_previous")
        self.button_previous.setMinimumSize(32, 32)
        self.button_previous.setStyleSheet(ControlStyle.get_nav_pushButton_style())
        ControlStyle.get_font_size(self.button_previous, 10)
        self.button_previous.setEnabled(False)
        # page button
        self.button_goto_epoch = QPushButton(parent)
        self.button_goto_epoch.setObjectName("button_goto_epoch")
        self.button_goto_epoch.setFixedSize(32, 32)
        ControlStyle.get_font_size(self.button_goto_epoch, 10)
        self.button_goto_epoch.setStyleSheet("border: 1px solid #D4D6D9;background: #FFFFFF;color: #000000;")
        self.button_goto_epoch.setEnabled(False)
        # of page label
        self.label_of_page = QLabel(parent)
        self.label_of_page.setObjectName("label_of_page")
        ControlStyle.get_font_size(self.label_of_page, 10)
        self.label_of_page.setMinimumSize(59, 32)
        # > button
        self.button_next = QPushButton(parent)
        self.button_next.setObjectName("button_next")
        self.button_next.setMinimumSize(32, 32)
        self.button_next.setStyleSheet(ControlStyle.get_nav_pushButton_style())
        ControlStyle.get_font_size(self.button_next, 10)
        self.button_next.setEnabled(False)

        nav_page_hlayout.addWidget(self.button_previous)
        nav_page_hlayout.addWidget(self.button_goto_epoch)
        nav_page_hlayout.addWidget(self.label_of_page)
        nav_page_hlayout.addWidget(self.button_next)

        # 创建一个空白区域
        spacerItem2 = QSpacerItem(12, 32)

        # last button
        self.last_pushButton = QPushButton(parent)
        self.last_pushButton.setObjectName("last_pushButton")
        self.last_pushButton.setMinimumSize(60, 32)
        self.last_pushButton.setStyleSheet(ControlStyle.get_nav_pushButton_style())
        ControlStyle.get_font_size(self.last_pushButton, 10)

        self.nav_button_widget_hlayout.addWidget(self.first_pushButton)
        self.nav_button_widget_hlayout.addSpacerItem(spacerItem1)
        self.nav_button_widget_hlayout.addLayout(nav_page_hlayout)
        self.nav_button_widget_hlayout.addSpacerItem(spacerItem2)
        self.nav_button_widget_hlayout.addWidget(self.last_pushButton)

        self.retranslateUi()

    def retranslateUi(self):
        _translate = QCoreApplication.translate
        self.first_pushButton.setText(_translate("NavButtonsWidget", "First"))
        self.button_previous.setText(_translate("NavButtonsWidget", "<"))
        self.label_of_page.setText(_translate("NavButtonsWidget", " of 1"))
        self.button_next.setText(_translate("NavButtonsWidget", ">"))
        self.last_pushButton.setText(_translate("NavButtonsWidget", "Last"))

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

        # Sleep Analysis label
        self.sleep_analysis_label = QLabel(parent)
        self.sleep_analysis_label.setObjectName("sleep_analysis_label")
        self.sleep_analysis_label.setMinimumSize(230, 32)
        self.sleep_analysis_label.setStyleSheet(ControlStyle.get_label_word_style())
        ControlStyle.get_font_size(self.sleep_analysis_label, 12)
        self.top_widget_hlayout.addWidget(self.sleep_analysis_label)

        # 创建一个空白区域
        spacerItem = QSpacerItem(150, 32, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.top_widget_hlayout.addSpacerItem(spacerItem)

        # Number of Epochs Display label + comboBox
        epochs_control = QHBoxLayout()
        epochs_control.setContentsMargins(0, 0, 0, 0)
        epochs_control.setSpacing(20)   # 设置组件之间的间距为5像素

        self.label_select_number_epochs = QLabel(parent)
        self.label_select_number_epochs.setObjectName("label_select_number_epochs")
        self.label_select_number_epochs.setMinimumSize(194, 32)
        self.label_select_number_epochs.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_select_number_epochs, 10)
        # self.label_select_number_epochs.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # 设置标签右对齐

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

        # Epochs length label + comboBox
        epoch_length_layout = QHBoxLayout()
        epoch_length_layout.setContentsMargins(0, 0, 0, 0)
        epoch_length_layout.setSpacing(20)

        self.label_epoch_length = QLabel(parent)
        self.label_epoch_length.setObjectName("label_epoch_length")
        self.label_epoch_length.setMinimumSize(115, 32)
        self.label_epoch_length.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_epoch_length, 10)
        # self.label_epoch_length.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # 设置标签右对齐

        self.combobox_epoch_length = QComboBox(parent)
        self.combobox_epoch_length.setObjectName("combobox_epoch_length")
        self.combobox_epoch_length.setMinimumSize(112, 32)

        self.combobox_epoch_length.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_epoch_length, 10)

        epoch_length_layout.addWidget(self.label_epoch_length)
        epoch_length_layout.addWidget(self.combobox_epoch_length)
        self.top_widget_hlayout.addLayout(epoch_length_layout)

        # 创建一个空白区域
        spacerItem2 = QSpacerItem(31, 32)
        self.top_widget_hlayout.addSpacerItem(spacerItem2)

        self.nav_buttons_widget = NavButtonsWidget(parent)
        self.top_widget_hlayout.addWidget(self.nav_buttons_widget)

        self.retranslateUi()

    def retranslateUi(self):
        _translate = QCoreApplication.translate
        self.label_select_number_epochs.setText(_translate("TopWidget", "Number of Epochs to display"))
        self.label_epoch_length.setText(_translate("TopWidget", "Epoch length (s)"))

class BottomLeftWidget(QWidget):
    # 底部左边窗口
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI(parent)
        self.setAcceptDrops(True)

    def initUI(self, parent=None):
        # 创建主布局
        self.bottom_left_widget_vlayout = QVBoxLayout(self)
        self.bottom_left_widget_vlayout.setObjectName("bottom_left_widget_vlayout")
        self.bottom_left_widget_vlayout.setContentsMargins(0, 0, 0, 0)
        self.bottom_left_widget_vlayout.setSpacing(8)

        # Channel Selection
        channel_selection_vlayout = QVBoxLayout()
        channel_selection_vlayout.setContentsMargins(32, 24, 32, 24)
        channel_selection_vlayout.setSpacing(8)

        self.label_channel_selection = QLabel(parent)
        self.label_channel_selection.setObjectName("label_channel_selection")
        self.label_channel_selection.setMinimumSize(250, 32)
        self.label_channel_selection.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_channel_selection, 12)

        # EEG Channel Selection
        eeg_layout = QHBoxLayout()
        eeg_layout.setContentsMargins(0, 0, 0, 0)
        eeg_layout.setSpacing(0)

        self.label_eeg = QLabel(parent)
        self.label_eeg.setObjectName("label_eeg")
        self.label_eeg.setMinimumSize(49, 32)
        self.label_eeg.setStyleSheet(ControlStyle.get_wiget400_word_style(16))
        ControlStyle.get_font_size(self.label_eeg, 10)

        self.combobox_eeg = QComboBox(parent)
        self.combobox_eeg.setObjectName("combobox_eeg")
        self.combobox_eeg.setMinimumSize(201, 32)
        self.combobox_eeg.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_eeg, 10)

        eeg_layout.addWidget(self.label_eeg)
        eeg_layout.addWidget(self.combobox_eeg)

        # EMG Channel Selection
        emg_layout = QHBoxLayout()
        emg_layout.setContentsMargins(0, 0, 0, 0)
        emg_layout.setSpacing(0)

        self.label_emg = QLabel(parent)
        self.label_emg.setObjectName("label_emg")
        self.label_emg.setMinimumSize(49, 32)
        self.label_emg.setStyleSheet(ControlStyle.get_wiget400_word_style(16))
        ControlStyle.get_font_size(self.label_emg, 10)

        self.combobox_emg = QComboBox(parent)
        self.combobox_emg.setObjectName("combobox_emg")
        self.combobox_emg.setMinimumSize(201, 32)
        self.combobox_emg.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_emg, 10)

        emg_layout.addWidget(self.label_emg)
        emg_layout.addWidget(self.combobox_emg)

        # ACC Channel Selection
        acc_layout = QHBoxLayout()
        acc_layout.setContentsMargins(0, 0, 0, 0)
        acc_layout.setSpacing(0)

        self.label_acc = QLabel(parent)
        self.label_acc.setObjectName("label_acc")
        self.label_acc.setMinimumSize(49, 32)
        self.label_acc.setStyleSheet(ControlStyle.get_wiget400_word_style(16))
        ControlStyle.get_font_size(self.label_acc, 10)

        self.combobox_acc = QComboBox(parent)
        self.combobox_acc.setObjectName("combobox_acc")
        self.combobox_acc.setMinimumSize(201, 32)
        self.combobox_acc.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_acc, 10)

        acc_layout.addWidget(self.label_acc)
        acc_layout.addWidget(self.combobox_acc)

        channel_selection_vlayout.addWidget(self.label_channel_selection, alignment=Qt.AlignLeft)
        channel_selection_vlayout.addLayout(eeg_layout)
        channel_selection_vlayout.addLayout(emg_layout)
        channel_selection_vlayout.addLayout(acc_layout)

        self.bottom_left_widget_vlayout.addLayout(channel_selection_vlayout)

        # 添加分割线
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setFrameShadow(QFrame.Plain)
        separator1.setStyleSheet("background-color: #a9a9a9;")
        separator1.setFixedHeight(1)

        self.bottom_left_widget_vlayout.addWidget(separator1)

        # time selection
        time_selection_vlayout = QVBoxLayout()
        time_selection_vlayout.setContentsMargins(32, 24, 32, 24)
        time_selection_vlayout.setSpacing(4)

        self.label_time_selection = QLabel(parent)
        self.label_time_selection.setObjectName("label_time_selection")
        self.label_time_selection.setMinimumSize(250, 32)
        self.label_time_selection.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_time_selection, 12)

        # start time
        start_layout = QHBoxLayout()
        start_layout.setContentsMargins(0, 0, 0, 0)
        start_layout.setSpacing(4)

        self.label_start = QLabel(parent)
        self.label_start.setObjectName("label_start")
        self.label_start.setMinimumSize(55, 32)
        self.label_start.setFixedWidth(55)
        self.label_start.setStyleSheet(ControlStyle.get_wiget400_word_style(14))
        ControlStyle.get_font_size(self.label_start, 10)

        self.combobox_start = QComboBox(parent)
        self.combobox_start.setObjectName("combobox_start")
        self.combobox_start.setMinimumSize(150, 32)
        self.combobox_start.setFixedWidth(150)
        self.combobox_start.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_start, 10)

        self.lineedit_start = QTimeEdit(QTime.currentTime())
        self.lineedit_start.setMinimumSize(95, 32)
        self.lineedit_start.setFixedWidth(95)
        self.lineedit_start.setStyleSheet(ControlStyle.get_timeEdit_style())
        ControlStyle.get_font_size(self.lineedit_start, 10)
        self.lineedit_start.setDisplayFormat("HH:mm:ss")  # 显示小时:分钟:秒

        start_layout.addWidget(self.label_start)
        start_layout.addWidget(self.combobox_start)
        start_layout.addWidget(self.lineedit_start)

        # end time
        end_layout = QHBoxLayout()
        end_layout.setContentsMargins(0, 0, 0, 0)
        end_layout.setSpacing(4)

        self.label_end = QLabel(parent)
        self.label_end.setObjectName("label_end")
        self.label_end.setMinimumSize(55, 32)
        self.label_end.setFixedWidth(55)
        self.label_end.setStyleSheet(ControlStyle.get_wiget400_word_style(14))
        ControlStyle.get_font_size(self.label_end, 10)

        self.combobox_end = QComboBox(parent)
        self.combobox_end.setObjectName("combobox_end")
        self.combobox_end.setMinimumSize(150, 32)
        self.combobox_end.setFixedWidth(150)
        self.combobox_end.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_end, 10)

        self.lineedit_end = QTimeEdit(parent)
        self.lineedit_end.setMinimumSize(95, 32)
        self.lineedit_end.setFixedWidth(95)
        self.lineedit_end.setStyleSheet(ControlStyle.get_timeEdit_style())
        ControlStyle.get_font_size(self.lineedit_end, 10)
        self.lineedit_end.setDisplayFormat("HH:mm:ss")  # 显示小时:分钟:秒

        end_layout.addWidget(self.label_end)
        end_layout.addWidget(self.combobox_end)
        end_layout.addWidget(self.lineedit_end)

        time_selection_vlayout.addWidget(self.label_time_selection, alignment=Qt.AlignLeft)
        time_selection_vlayout.addLayout(start_layout)
        time_selection_vlayout.addLayout(end_layout)

        self.bottom_left_widget_vlayout.addLayout(time_selection_vlayout)

        # 添加分割线
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Plain)
        separator2.setStyleSheet("background-color: #a9a9a9;")
        separator2.setFixedHeight(1)

        self.bottom_left_widget_vlayout.addWidget(separator2)

        # 创建一个空白区域
        spacerItem = QSpacerItem(314, 492, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.bottom_left_widget_vlayout.addSpacerItem(spacerItem)

        self.retranslateUi()

    def retranslateUi(self):
        _translate = QCoreApplication.translate
        self.label_channel_selection.setText(_translate("BottomLeftWidget", "Channel Select："))
        self.label_eeg.setText(_translate("BottomLeftWidget", "EEG"))
        self.label_emg.setText(_translate("BottomLeftWidget", "EMG"))
        self.label_acc.setText(_translate("BottomLeftWidget", "ACC"))
        self.label_time_selection.setText(_translate("BottomLeftWidget", "Time："))
        self.label_start.setText(_translate("BottomLeftWidget", "Start："))
        self.label_end.setText(_translate("BottomLeftWidget", "End："))

class IconWithTextWidget(QWidget):
    def __init__(self, icon_path, text, parent=None):
        super().__init__(parent)
        self.init_ui(icon_path, text)

    def init_ui(self, icon_path, text):
        self.setStyleSheet(ControlStyle.get_draw_pic_widget_style())
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)  # 图标和文字之间固定10像素

        # 设置布局对齐方式为居中
        layout.setAlignment(Qt.AlignCenter)

        # 添加图标
        icon_label = QLabel(self)
        icon_label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(icon_path)
        icon_label.setPixmap(pixmap)
        layout.addWidget(icon_label)

        # 添加文字
        text_label = QLabel(text, self)
        text_label.setAlignment(Qt.AlignCenter)
        # text_label.setStyleSheet("font-size: 14px; color: #808080;")
        text_label.setStyleSheet("""
                    width: 261px;
                    height: 10pt;
                    font-family: Microsoft YaHei;
                    font-weight: 400;
                    font-size: 14px;
                    color: #BBBDBF;
                    line-height: 14px;
                    text-align: left;
                    font-style: normal;
                    text-transform: none;
                """)
        layout.addWidget(text_label)

        # 设置主布局
        self.setLayout(layout)

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

        rem_wake_hlayout = QHBoxLayout()
        rem_wake_hlayout.setContentsMargins(0, 0, 0, 0)
        rem_wake_hlayout.setSpacing(16)
        # rem button
        self.pushButton_rem = QPushButton(parent)
        self.pushButton_rem.setObjectName("pushButton_rem")
        self.pushButton_rem.setMinimumSize(96, 32)
        self.pushButton_rem.setStyleSheet(ControlStyle.get_color_pushButton_style(color="FF3B3B"))
        self.pushButton_rem.setToolTip("快捷方式为：Shift+3")
        ControlStyle.get_font_size(self.pushButton_rem, 10)

        # nrem button
        self.pushButton_nrem = QPushButton(parent)
        self.pushButton_nrem.setObjectName("pushButton_nrem")
        self.pushButton_nrem.setMinimumSize(96, 32)
        self.pushButton_nrem.setStyleSheet(ControlStyle.get_color_pushButton_style(color="3131F6"))
        self.pushButton_nrem.setToolTip("快捷方式为：Shift+2")
        ControlStyle.get_font_size(self.pushButton_nrem, 10)

        # wake button
        self.pushButton_wake = QPushButton(parent)
        self.pushButton_wake.setObjectName("pushButton_wake")
        self.pushButton_wake.setMinimumSize(96, 32)
        self.pushButton_wake.setStyleSheet(ControlStyle.get_color_pushButton_style(color="F7B031"))
        self.pushButton_wake.setToolTip("快捷方式为：Shift+1")
        ControlStyle.get_font_size(self.pushButton_wake, 10)

        rem_wake_hlayout.addWidget(self.pushButton_rem)
        rem_wake_hlayout.addWidget(self.pushButton_nrem)
        rem_wake_hlayout.addWidget(self.pushButton_wake)

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
        # self.toolButton_amplitude_set.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        self.toolButton_amplitude_set.setStyleSheet(ControlStyle.get_toolbutton_style())
        ControlStyle.get_font_size(self.toolButton_amplitude_set, 10)
        # 创建主下拉菜单
        main_menu = QMenu()
        main_menu.setMinimumSize(160, 32)
        main_menu.setStyleSheet(ControlStyle.get_menuBar_style())
        ControlStyle.get_font_size(main_menu, 10)

        # 创建一级菜单（EEG，EMG，ACC）
        # menu_eeg = QMenu("EEG Amplitude (μv) ", self)
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

        self.bottom_right_top_widget_hlayout.addLayout(rem_wake_hlayout)
        self.bottom_right_top_widget_hlayout.addLayout(redo_set_hlayout)
        self.bottom_right_top_widget_hlayout.addSpacerItem(spacerItem)
        self.bottom_right_top_widget_hlayout.addWidget(self.toolButton_amplitude_set)

        self.retranslateUi()

    def retranslateUi(self):
        _translate = QCoreApplication.translate
        self.pushButton_rem.setText(_translate("BottomRightTopWidget", "REM"))
        self.pushButton_nrem.setText(_translate("BottomRightTopWidget", "NREM"))
        self.pushButton_wake.setText(_translate("BottomRightTopWidget", "Wake"))

        self.pushButton_redo.setText(_translate("BottomRightTopWidget", "Redo"))
        self.pushButton_undo.setText(_translate("BottomRightTopWidget", "Undo"))
        self.pushButton_reset.setText(_translate("BottomRightTopWidget", "Reset"))

        self.toolButton_amplitude_set.setText(_translate("BottomRightTopWidget", "Amplitude setting"))

class Thread_run_analysis(QThread):
    signal = pyqtSignal('PyQt_PyObject')

    def __init__(self):
        QThread.__init__(self)
        self.raw_processed = None
        self.model_name = "2_LightGBM-1EEG"  # 设置默认模型名称
        self.epoch_length = 4  # 默认值
        self.emg_channel = None  # 添加EMG通道属性
        self.eeg_channel = None  # 添加EEG通道属性
        self.acc_channel = None  # 添加 ACC 通道
        # self.save_path = None
        # self.timestamp_dir = None
        self._is_running = False

    def cleanup(self):
        """清理线程中的所有数据"""
        attributes = [
            'raw_processed', 'eeg_data', 'emg_data', 'acc_data',
            'model', 'spectrogram_data', 'df_score',
            'timestamp_dir', 'save_path'
        ]
        for attr in attributes:
            if hasattr(self, attr):
                delattr(self, attr)
        
        # 强制垃圾回收
        import gc
        gc.collect()

    @staticmethod
    def correct_sleep_transitions(df):
        """
        修正睡眠阶段转换，确保遵循 WAKE -> NREM -> REM 的顺序
        """
        corrected_data = df.copy()
        stages = corrected_data.iloc[:, 1].values
        stages = stages[::-1]

        for i in range(1, len(stages)):
            prev_stage = stages[i-1]
            current_stage = stages[i]
            
            # 修正 WAKE -> REM 转换
            if prev_stage == 3 and current_stage == 1:
                stages[i] = 2
            else:
                continue

        corrected_data.iloc[:, 1] = stages[::-1]
        return corrected_data

    def calculate_spectrogram(self):
        """计算EEG信号的时频图数据"""
        try:
            fs = self.raw_processed.info["sfreq"]
            nperseg = int(fs * 4)            
            noverlap = nperseg * 0.9
            
            # f, t, Sxx = scipy.signal.spectrogram(
            #     self.eeg_data,
            #     fs=fs,
            #     nperseg=nperseg,
            #     noverlap=noverlap
            # )
            
            # 更换时频图计算方法，消除时频图开头的空白
            f, t, Zxx = stft(self.eeg_data, fs=fs, nperseg=nperseg, noverlap=noverlap, boundary='zeros')
            
            # 计算对数功率谱
            Sxx = 10 * np.log10(np.abs(Zxx) + 1e-10)
            
            # 筛选感兴趣的频率范围
            good_freqs = np.logical_and(f >= 0.5, f <= 50)
            Sxx = np.squeeze(Sxx)
            Sxx = Sxx[good_freqs, :]
            f = f[good_freqs]
            
            # 计算颜色范围
            vmin = np.percentile(Sxx, 10)
            vmax = np.percentile(Sxx, 99)
            
            return {
                'frequencies': f,
                'times': t,
                'power': Sxx,
                'vmin': vmin,
                'vmax': vmax
            }
        except Exception as e:
            print(f"Error calculating spectrogram: {str(e)}")
            QLLogging.log.exception(f"Error calculating spectrogram: {str(e)}")
            return None

    def run(self):
        """运行睡眠阶段分析"""
        print("thread_run is running----------------")

        print(f"run----------- Current thread ID:{threading.get_ident()}")

        start_time = time.time()
        try:
            # progress = 1
            # self.signal.emit([progress, "Analysis started"])

            progress = 10
            self.signal.emit([progress, "Model loaded successfully"])

            # 在启动的时候进行加载数据
            from .utils import model_loader
            if model_loader.is_model_ready(): # 数据加载成功
                self.model = model_loader.model

            progress = 35
            self.signal.emit([progress, "Model loaded successfully"])

            end_time0 = time.time()

            self.raw_processed = self.raw_data_resample(self.raw_processed, sfreq=100)  # 这里也是比较耗时的  15s

            end_time1 = time.time()
            print(f"加载模型，时间为：{end_time1 - end_time0}")

            progress = 45
            self.signal.emit([progress, "Model loaded successfully"])

            # 获取通道索引
            ch_names = self.raw_processed.ch_names
            eeg_idx = ch_names.index(self.eeg_channel)
            emg_idx = ch_names.index(self.emg_channel)
            acc_idx = ch_names.index(self.acc_channel)
            # 获取所有通道数据

            end_time12 = time.time()
            print(f"获取所有通道数据，时间为：{end_time12 - end_time1}")

            progress = 65
            self.signal.emit([progress, "Model loaded successfully"])

            # 获取通道数据时立即降采样，减少内存使用
            data = self.raw_processed.get_data()
            self.eeg_data = data[eeg_idx]
            self.emg_data = data[emg_idx]
            self.acc_data = data[acc_idx] * 1e-6

            end_time2 = time.time()
            print(f"获取通道数据时立即降采样，时间为：{end_time2 - end_time12}")

            progress = 80
            self.signal.emit([progress, "Features extracted, making predictions..."])

            # 释放原始数据
            del data

            # 提取特征  启动   # 并行运行  25s
            self.signal.emit([progress, "Extracting features..."])
            features_df = extract_features_from_raw(
                self.raw_processed,
                epoch_len=self.epoch_length,
                model_name=self.model_name,
                save_path=None,
                emg_channel=self.emg_channel,
                eeg_channel=self.eeg_channel
            )
            # features_df.to_csv(os.path.join(
            #         self.save_path,"test.csv"))
            progress = 90
            self.signal.emit([progress, "Creating score file..."])

            end_time3 = time.time()
            print(f"提取体征，时间为：{end_time3 - end_time2}")

            # 预测  # 这里也是可以并行的  13s
            features, predictions = self.get_features_and_predictions(features_df, self.model)

            end_time34 = time.time()
            print(f"预测，时间为：{end_time34 - end_time3}")

            progress = 100
            self.signal.emit([progress, "Analysis completed"])

            # 创建得分文件  13s
            df_score = pd.DataFrame({
                "Epoch No.": list(range(len(predictions))),
                "Stage_Code": predictions
            })
            df_score["Stage_Code"] = df_score["Stage_Code"].astype("int")

            # 修正睡眠阶段转换
            df_score = self.correct_sleep_transitions(df_score)

            # 添加阶段名称
            stage_code = {1: "Wake", 2: "NREM", 3: "REM"}
            df_score["Stage"] = df_score["Stage_Code"].map(stage_code)

            # 添加睡眠阶段统计（只在第一行）
            stage_counts = df_score["Stage_Code"].value_counts()
            df_score.loc[0, "Wake_Count"] = stage_counts.get(1, 0)
            df_score.loc[0, "NREM_Count"] = stage_counts.get(2, 0)
            df_score.loc[0, "REM_Count"] = stage_counts.get(3, 0)

            # 保存结果到内存
            self.df_score = df_score


            end_time4 = time.time()
            print(f"保存结果到内存，时间为：{end_time4 - end_time3}")  # 10s

            # 在完成分析后立即清理大型数据
            if hasattr(self, 'model'):
                del self.model
            del features_df
            del features

            # 计算时频图数据
            self.spectrogram_data = self.calculate_spectrogram()

            end_time5 = time.time()
            print(f"计算时频图数据，时间为：{end_time5 - end_time4}")  # 1s

        except Exception as e:
            self.signal.emit([0, f"Error: {str(e)}"])
            QLLogging.log.exception(f"Error: {str(e)}")

        finally:
            self._is_running = False

        end_time = time.time()
        print(f"thread_run 结束，时间为：{end_time - start_time}")

    # def run(self):
    #     """运行睡眠阶段分析"""
    #     print("thread_run is running----------------")
    #     start_time = time.time()
    #     try:
    #         # np.random.seed(42)
    #         progress = 0
    #         self.signal.emit([progress, "Analysis started"])
    # 
    #         # 加载模型 启动
    #         model_path = os.path.join(os.path.dirname(__file__), "Qlass", "models", f"{self.model_name}.pkl")
    #         self.model = joblib.load(model_path)
    #         print(self.model.get_params())
    # 
    #         # from .utils import model_loader
    #         # if model_loader.is_model_ready():  # 数据加载成功
    #         #     self.model = model_loader.model
    # 
    #         progress = 10
    #         self.signal.emit([progress, "Model loaded successfully"])
    # 
    #         end_time0 = time.time()
    # 
    #         self.raw_processed.resample(sfreq=100)  # 这里也是比较耗时的  15s
    # 
    #         end_time1 = time.time()
    #         print(f"加载模型，时间为：{end_time1 - end_time0}")
    # 
    #         # 使用Data_Info.py创建的时间戳目录
    #         # self.timestamp_dir = self.raw_processed.info.get('description')
    #         # if not self.timestamp_dir:
    #         #     raise ValueError("No valid save path found in raw.info['description']")
    #         # self.save_path = os.path.join(self.timestamp_dir, 'Sleep Analysis')
    #         # os.makedirs(self.save_path, exist_ok=True)
    # 
    #         # 获取通道索引
    #         ch_names = self.raw_processed.ch_names
    #         eeg_idx = ch_names.index(self.eeg_channel)
    #         emg_idx = ch_names.index(self.emg_channel)
    #         acc_idx = ch_names.index(self.acc_channel)
    #         # 获取所有通道数据
    # 
    #         end_time12 = time.time()
    #         print(f"获取所有通道数据，时间为：{end_time12 - end_time1}")
    # 
    #         # 获取通道数据时立即降采样，减少内存使用
    #         data = self.raw_processed.get_data()
    #         self.eeg_data = data[eeg_idx]
    #         self.emg_data = data[emg_idx]
    #         self.acc_data = data[acc_idx] * 1e-6
    # 
    #         end_time2 = time.time()
    #         print(f"获取通道数据时立即降采样，时间为：{end_time2 - end_time12}")
    # 
    #         # 释放原始数据
    #         del data
    # 
    #         # 提取特征  启动   # 并行运行  25s
    #         self.signal.emit([progress, "Extracting features..."])
    #         features_df = extract_features_from_raw(
    #             self.raw_processed,
    #             epoch_len=self.epoch_length,
    #             model_name=self.model_name,
    #             save_path=None,
    #             emg_channel=self.emg_channel,
    #             eeg_channel=self.eeg_channel
    #         )
    #         # features_df.to_csv(os.path.join(
    #         #         self.save_path,"test.csv"))
    #         progress = 80
    #         self.signal.emit([progress, "Features extracted, making predictions..."])
    # 
    #         end_time3 = time.time()
    #         print(f"提取体征，时间为：{end_time3 - end_time2}")
    # 
    #         # 预测  # 这里也是可以并行的  13s
    #         features = features_df.columns.tolist()
    #         print(features)
    #         # X = pd.DataFrame()
    # 
    #         # predictions = self.model.predict(features_df[features])
    #         predictions = self.model.predict(features_df)
    # 
    #         end_time34 = time.time()
    #         print(f"预测，时间为：{end_time34 - end_time3}")
    # 
    #         progress = 90
    #         self.signal.emit([progress, "Creating score file..."])
    # 
    #         # 创建得分文件  13s
    #         df_score = pd.DataFrame({
    #             "Epoch No.": list(range(len(predictions))),
    #             "Stage_Code": predictions
    #         })
    #         df_score["Stage_Code"] = df_score["Stage_Code"].astype("int")
    # 
    #         # 修正睡眠阶段转换
    #         df_score = self.correct_sleep_transitions(df_score)
    # 
    #         # 添加阶段名称
    #         stage_code = {1: "Wake", 2: "NREM", 3: "REM"}
    #         df_score["Stage"] = df_score["Stage_Code"].map(stage_code)
    # 
    #         # 添加睡眠阶段统计（只在第一行）
    #         stage_counts = df_score["Stage_Code"].value_counts()
    #         df_score.loc[0, "Wake_Count"] = stage_counts.get(1, 0)
    #         df_score.loc[0, "NREM_Count"] = stage_counts.get(2, 0)
    #         df_score.loc[0, "REM_Count"] = stage_counts.get(3, 0)
    # 
    #         # 保存结果到内存
    #         self.df_score = df_score
    #         progress = 100
    #         self.signal.emit([progress, "Analysis completed"])
    # 
    #         end_time4 = time.time()
    #         print(f"保存结果到内存，时间为：{end_time4 - end_time3}")  # 10s
    # 
    #         # 在完成分析后立即清理大型数据
    #         if hasattr(self, 'model'):
    #             del self.model
    #         del features_df
    #         del features
    # 
    #         # 计算时频图数据
    #         self.spectrogram_data = self.calculate_spectrogram()
    # 
    #         end_time5 = time.time()
    #         print(f"计算时频图数据，时间为：{end_time5 - end_time4}")  # 1s
    # 
    #     except Exception as e:
    #         self.signal.emit([0, f"Error: {str(e)}"])
    #         QLLogging.log.exception(f"Error: {str(e)}")
    # 
    #     finally:
    #         self._is_running = False
    # 
    #     end_time = time.time()
    #     print(f"thread_run 结束，时间为：{end_time - start_time}")

    def raw_data_resample(self, raw_data, sfreq=100):
        """拆分出run函数中每一步函数操作的具体部分"""
        return raw_data.resample(sfreq=sfreq)

    # def resample_channel(self, raw_data, channel_idx, sfreq):
    #     """对单个通道的数据进行降采样"""
    #     # 获取单通道的数据
    #     data = raw_data.get_data()[channel_idx]
    #     # 创建临时的 RawArray 来存储单通道数据
    #     info = mne.create_info(['temp'], raw_data.info['sfreq'], ch_types=['eeg'])
    #     temp_raw = mne.io.RawArray(data[np.newaxis, :], info) ##
    #     # 对单通道数据进行降采样
    #     temp_raw.resample(sfreq=sfreq)
    #     return temp_raw.get_data()[0]  # 返回单通道数据

    # def raw_data_resample(self, raw_data, sfreq=100):
    #     """拆分出run函数中每一步函数操作的具体部分，并行化处理每个通道"""
    #     # 获取所有通道的类型列表
    #     channel_types = raw_data.get_channel_types()
    #
    #     # 准备结果存储
    #     results = [None] * len(raw_data.ch_names)
    #
    #     # 使用线程池并行处理
    #     with ThreadPoolExecutor(max_workers=len(channel_types)) as executor:
    #         # 提交所有通道的降采样任务
    #         future_to_idx = {
    #             executor.submit(self.resample_channel, raw_data, i, sfreq): i
    #             for i in range(len(raw_data.ch_names))
    #         }
    #
    #     # 处理完成的结果
    #     for future in as_completed(future_to_idx):
    #         channel_idx, channel_data = future.result()
    #         results[channel_idx] = channel_data
    #
    #     # 合并结果
    #     resampled_data = np.vstack(results)
    #
    #     # 创建新的Raw对象
    #     new_info = mne.create_info(
    #         ch_names=raw_data.ch_names,
    #         sfreq=sfreq,
    #         ch_types=channel_types
    #     )
    #
    #     return mne.io.RawArray(resampled_data, new_info)

    def get_features_and_predictions(self, features_df, model):
        """获取features和predictions数据"""
        # 预测  # 这里也是可以并行的  13s
        # features = features_df.columns.tolist()
        # predictions = model.predict(features_df)
        def prepare_features(features_df):
            return features_df.columns.tolist()
        def run_predictions(features_df, model):
            return model.predict(features_df)

        # 并行执行
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(prepare_features, features_df)
            features = future1.result()
            future2 = executor.submit(run_predictions, features_df, model)
            predictions = future2.result()

        return features, predictions

class Ui_qlass_analysis(QWidget):
    # closed = QtCore.pyqtSignal()  # 定义信号
    # 定义一个自定义信号
    progressBar_completed = pyqtSignal()

    def __init__(self, qlass_analysis = None):
        super().__init__()
        # Configure matplotlib for better performance
        plt.rcParams['agg.path.chunksize'] = 10000  # Increase chunk size for complex paths
        plt.rcParams['path.simplify'] = True  # Enable path simplification
        plt.rcParams['path.simplify_threshold'] = 0.5  # Increase simplification threshold
        
        self.raw_processed = None  # 添加raw_processed属性
        self.map_colors = {1: "orange", 2: "blue", 3: "red"}
        self.map_stages = {1:"Wake", 2:"NREM", 3:"REM"}
        self.thread_run = Thread_run_analysis()
        self.thread_run.signal.connect(self.update_progress)
        self.df_score = None
        self.current_selected_epoch = None
        self.current_selected_epochs = []
        self.shift_is_pressed = False
        self.button_is_pressed = False
        self.mouse_is_dragged = False
        self.mouse_dragged_begin = None
        self.shift_begin = None
        self.highlight_lines = []
        self.n_epochs = 0
        self.epochlabels = []
        self.epoch_length = 4  # 默认epoch长度
        self.epoch_start = 0  # 当前显示起始epoch
        self.model_name = "2_LightGBM-1EEG"  # 设置默认模型名称
        self.edf_path = None
        self.sleep_score_wh = SleepScoreWH()
        self.sleep_redo_score_wh = SleepScoreWH()

        # 初始化导航相关的变量
        self.current_page = 0
        self._ignore_combobox_change = False  # 添加标志以防止循环触发

        self.pushButton_analyse = QPushButton(qlass_analysis)
        self.bottom_left_widget = BottomLeftWidget(qlass_analysis)

        self.window = None

        self.save_pic_cpm_widget = None
        self.save_pic_cpm_ui = None

    def import_raw(self, raw):
        """导入原始数据"""
        try:
            self.raw_processed = raw
            self.thread_run.raw_processed = self.raw_processed
            self.edf_path = raw.info['description']
            if raw is not None:
                self.pushButton_analyse.setEnabled(True)

                # 更新通道选择下拉菜单
                ch_names = raw.ch_names

                # 清空并更新所有通道下拉菜单
                self.bottom_left_widget.combobox_emg.clear()
                self.bottom_left_widget.combobox_eeg.clear()
                self.bottom_left_widget.combobox_acc.clear()

                self.bottom_left_widget.combobox_emg.addItems(ch_names)
                self.bottom_left_widget.combobox_eeg.addItems(ch_names)
                self.bottom_left_widget.combobox_acc.addItems(ch_names)

                # 设置默认选择
                default_eeg = "EEG3"
                default_emg = "EEG1"
                default_acc = "ACC0"  # 设置 ACC0 为默认值

                if default_eeg in ch_names:
                    self.bottom_left_widget.combobox_eeg.setCurrentText(default_eeg)

                if default_emg in ch_names:
                    self.bottom_left_widget.combobox_emg.setCurrentText(default_emg)

                if default_acc in ch_names:
                    self.bottom_left_widget.combobox_acc.setCurrentText(default_acc)

        except Exception as e:
            QLLogging.log.exception(f"Error in import_raw: {str(e)}")

    def setupUi(self, qlass_analysis):
        qlass_analysis.setObjectName("qlass_analysis")
        qlass_analysis.resize(1440, 900)
        qlass_analysis.setStyleSheet(ControlStyle.get_widget_style())

        # 设置主窗口的大小策略为可扩展
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(qlass_analysis.sizePolicy().hasHeightForWidth())
        qlass_analysis.setSizePolicy(sizePolicy)

        # 创建布局
        self.main_layout = QVBoxLayout(qlass_analysis)
        self.main_layout.setContentsMargins(0, 24, 0, 0)
        self.main_layout.setSpacing(0)

        # 测试新界面
        self.top_widget = TopWidget(qlass_analysis)
        self.top_widget.setFixedHeight(80)
        top_widget_size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.top_widget.setSizePolicy(top_widget_size_policy)

        self.top_widget.combobox_epoch_length.addItems(["4", "10"])

        # 添加行高
        # 创建 QListView 并设置行高
        view_n_epochs = QListView()
        view_n_epochs.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.top_widget.combobox_select_n_epochs.setView(view_n_epochs)  # 绑定视图到 QComboBox

        # 添加行高
        # 创建 QListView 并设置行高
        view_epoch_length = QListView()
        view_epoch_length.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.top_widget.combobox_epoch_length.setView(view_epoch_length)  # 绑定视图到 QComboBox

        # 添加分割线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setStyleSheet("background-color: #a9a9a9;")
        separator.setFixedHeight(1)

        self.main_layout.addWidget(self.top_widget)
        self.main_layout.addWidget(separator)

        # 水平布局管理器
        self.bottom_hlayout = QHBoxLayout()
        self.bottom_hlayout.setContentsMargins(0, 0, 0, 0)
        self.bottom_hlayout.setSpacing(0)

        # 底部左边窗口
        self.bottom_left_widget.setMinimumWidth(360)
        bottom_left_widget_size_policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.bottom_left_widget.setSizePolicy(bottom_left_widget_size_policy)
        self.bottom_hlayout.addWidget(self.bottom_left_widget)

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
        self.bottom_right_widget = QWidget(qlass_analysis)
        self.bottom_right_widget.setMinimumSize(1126, 788)

        self.bottom_right_widget_vlayout = QVBoxLayout(self.bottom_right_widget)
        self.bottom_right_widget_vlayout.setObjectName("bottom_right_widget_vlayout")
        self.bottom_right_widget_vlayout.setContentsMargins(0, 0, 0, 24)
        self.bottom_right_widget_vlayout.setSpacing(0)

        # 主要是绘画窗口
        # 先将初始化页面画出，当获取到点击事件之后，将其页面换成进度条，当进度条走完之后，将图形显示出来
        draw_pic_vlayout = QVBoxLayout()
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
        self.progressBar_widget = QWidget(qlass_analysis)
        self.progressBar_widget.setMinimumSize(1126, 692)

        progressBar_vlayout = QVBoxLayout(self.progressBar_widget)
        progressBar_vlayout.setContentsMargins(434, 0, 434, 0)
        progressBar_vlayout.setAlignment(Qt.AlignCenter)
        progressBar_vlayout.setSpacing(0)

        progressBar_label_hlayout = QHBoxLayout()
        progressBar_label_hlayout.setContentsMargins(0, 0, 0, 0)
        progressBar_label_hlayout.setSpacing(0)

        self.label_progressBar = QLabel(qlass_analysis)
        self.label_progressBar.setText("分析中")
        self.label_progressBar.setObjectName("label_progressBar")
        self.label_progressBar.setMinimumSize(50, 20)
        self.label_progressBar.setStyleSheet(ControlStyle.get_redo_set_pushButton_style())
        ControlStyle.get_font_size(self.label_progressBar, 10)

        self.label_progressBar_count = QLabel(qlass_analysis)
        self.label_progressBar_count.setText("1%")
        self.label_progressBar_count.setObjectName("label_progressBar_count")
        self.label_progressBar_count.setMinimumSize(50, 20)
        self.label_progressBar_count.setStyleSheet(ControlStyle.get_redo_set_pushButton_style())
        ControlStyle.get_font_size(self.label_progressBar_count, 10)
        self.label_progressBar_count.setAlignment(Qt.AlignRight)

        progressBar_label_hlayout.addWidget(self.label_progressBar, alignment=Qt.AlignLeft)
        progressBar_label_hlayout.addWidget(self.label_progressBar_count, alignment=Qt.AlignRight)

        self.progressBar = QProgressBar(qlass_analysis)
        self.progressBar.setObjectName("progressBar")
        self.progressBar.setMinimumSize(258, 16)
        self.progressBar.setTextVisible(False)  # 关闭进度条中间的文本显示
        self.progressBar.setStyleSheet(ControlStyle.get_progressBar_style())

        self.container = QWidget(self.progressBar_widget)
        self.container.setStyleSheet("background-color: transparent; border: none;")
        self.container.setAttribute(Qt.WA_TranslucentBackground)

        # 创建gif图片
        self.label_gif = QLabel()
        self.label_gif.setParent(self.container)
        self.label_gif.move(434, 0)
        self.label_gif.setFixedSize(64, 64)
        self.movie = QMovie("./resource/gif/DinosaurProgressBar.gif")
        self.movie.setScaledSize(QSize(64, 64))
        self.label_gif.setMovie(self.movie)
        self.movie.start()

        self.label_draw = QLabel(qlass_analysis)
        self.label_draw.setText("正在绘图中~~~")
        self.label_draw.setObjectName("label_draw")
        self.label_draw.setMinimumSize(150, 20)
        self.label_draw.setStyleSheet(ControlStyle.get_redo_set_pushButton_style())
        ControlStyle.get_font_size(self.label_draw, 16)
        self.label_draw.hide()
        self.progressBar.show()
        self.label_progressBar_count.show()
        self.label_progressBar.show()
        self.label_gif.show()

        # 刷新 GUI
        QApplication.processEvents()

        progressBar_vlayout.addWidget(self.label_gif)
        progressBar_vlayout.addWidget(self.progressBar)
        progressBar_vlayout.addLayout(progressBar_label_hlayout)

        progressBar_vlayout.addWidget(self.label_draw)

        # 这里需要添加一个顶部窗口
        self.bottom_right_top_widget = BottomRightTopWidget(qlass_analysis)
        self.bottom_right_top_widget.setObjectName("bottom_right_top_widget")
        self.bottom_right_top_widget.setFixedHeight(50)
        bottom_right_top_widget_size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.bottom_right_top_widget.setSizePolicy(bottom_right_top_widget_size_policy)

        # 添加数值选项
        values = ["±100", "±200", "±500", "±1000", "Auto"]
        for value in values:
            action = QAction(value, self)
            ControlStyle.get_font_size(action, 10)
            self.bottom_right_top_widget.menu_eeg.addAction(action)
            action.triggered.connect(
                lambda checked, val=value: self.update_signal_range(sender="eeg", value=val)
            )

        values = ["±50", "±100", "±200", "±500", "Auto"]
        for value in values:
            action = QAction(value, self)
            ControlStyle.get_font_size(action, 10)
            self.bottom_right_top_widget.menu_emg.addAction(action)
            action.triggered.connect(
                lambda checked, val=value: self.update_signal_range(sender="emg", value=val)
            )

        values = ["±500", "±1000", "±2000", "±4000", "Auto"]
        for value in values:
            action = QAction(value, self)
            ControlStyle.get_font_size(action, 10)
            self.bottom_right_top_widget.menu_acc.addAction(action)
            action.triggered.connect(
                lambda checked, val=value: self.update_signal_range(sender="acc", value=val)
            )

        # 使用局部设置
        self.figure = Figure(dpi=15)
        # 设置此figure的字体大小
        self.figure.set_size_inches(15, 8)  # 保持原有的figure大小
        self.canvas = FigureCanvasQTAgg(self.figure)

        self.widget_hypnogram = QWidget(qlass_analysis)
        hypnogram_layout = QVBoxLayout(self.widget_hypnogram)
        hypnogram_layout.addWidget(self.canvas)

        self.plot_hypnogram = pg.PlotWidget()
        self.plot_eeg = pg.PlotWidget()
        self.plot_emg = pg.PlotWidget()
        self.plot_acc = pg.PlotWidget()
        self.plot_widget = pg.PlotWidget()

        self.event_handler = MatplotlibEventHandler_(self.canvas, owner=self, plot_widgets=[self.plot_hypnogram, self.plot_eeg, self.plot_emg, self.plot_acc, self.plot_widget])

        # 将所有图表的 X 轴链接到睡眠分期图
        self.plot_eeg.setXLink(self.plot_hypnogram)
        self.plot_emg.setXLink(self.plot_hypnogram)
        self.plot_acc.setXLink(self.plot_hypnogram)
        self.plot_widget.setXLink(self.plot_hypnogram)

        # 为每个图表设置默认样式
        for plot in [self.plot_acc, self.plot_emg, self.plot_eeg,
                     self.plot_hypnogram, self.plot_widget]:
            plot.setBackground("w")
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.setMouseEnabled(x=False, y=False)  # 只允许水平缩放/平移
            plot.setMenuEnabled(False)  # 禁用右键菜单

            plot.getViewBox().disableAutoRange(axis=pg.ViewBox.YAxis)

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
        stretch_factors = [1, 2, 1, 1, 2]

        common_font = QFont("Arial", 10)
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
        self.scrollarea_canvas = QScrollArea(qlass_analysis)
        self.scrollarea_canvas.setObjectName("scrollarea_canvas")
        self.scrollarea_canvas.setMinimumSize(1085, 545)
        self.scrollarea_canvas.setWidgetResizable(True)  # 关键：启用内容自适应
        self.scrollarea_canvas.setHorizontalScrollBarPolicy(True)  # 强制显示水平滚动条（或设置为 AsNeeded）
        self.scrollarea_canvas.setWidget(self.plot_container)
        # self.scrollarea_canvas.setWidget(self.canvas)
        self.scrollarea_canvas.hide()

        self.widget_time_slider = TimeSliderWidget(qlass_analysis)
        self.widget_time_slider.setObjectName("widget_time_slider")
        self.widget_time_slider.setMinimumSize(1126, 56)
        self.widget_time_slider.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.widget_time_slider.time_slider.setMinimum(0)
        self.widget_time_slider.time_slider.setMaximum(int(self.get_total_time_number().total_seconds()))
        # self.widget_time_slider.time_slider.setEnabled(False)

        draw_pic_vlayout.addWidget(self.icon_with_text_widget)
        draw_pic_vlayout.addWidget(self.progressBar_widget)
        draw_pic_vlayout.addWidget(self.bottom_right_top_widget)
        draw_pic_vlayout.addWidget(self.scrollarea_canvas)
        # draw_pic_vlayout.addWidget(self.plot_eeg)
        # draw_pic_vlayout.addWidget(self.plot_emg)
        # draw_pic_vlayout.addWidget(self.plot_acc)
        # draw_pic_vlayout.addWidget(self.plot_widget)
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

        
        # 创建一个空白区域
        spacerItem = QSpacerItem(603, 32, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # load_histoty
        self.pushButton_load_history = QPushButton(qlass_analysis)
        # self.pushButton_load_history.setObjectName("pushButton_analyse")
        self.pushButton_load_history.setMinimumSize(145, 40)
        self.pushButton_load_history.setStyleSheet(ControlStyle.get_pushButton_style())
        ControlStyle.get_font_size(self.pushButton_load_history, 10)
        self.pushButton_load_history.hide()
        # save pic
        self.pushButton_save_pic = QPushButton(qlass_analysis)
        self.pushButton_save_pic.setObjectName("pushButton_save_pic")
        self.pushButton_save_pic.setMinimumSize(145, 40)
        self.pushButton_save_pic.setStyleSheet(ControlStyle.get_pushButton_style_white())
        self.pushButton_save_pic.setEnabled(False)
        ControlStyle.get_font_size(self.pushButton_save_pic, 10)

        # save data
        self.pushButton_save_data = QPushButton(qlass_analysis)
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

        self.bottom_right_widget_vlayout.addLayout(draw_pic_vlayout)
        self.bottom_right_widget_vlayout.addWidget(separator_bottom_right)
        self.bottom_right_widget_vlayout.addLayout(bottom_right_button_hlayout)

        self.bottom_right_widget.setStyleSheet(ControlStyle.get_draw_pic_widget_style())
        self.bottom_hlayout.addWidget(self.bottom_right_widget)

        self.main_layout.addLayout(self.bottom_hlayout)
        self.retranslateUi(qlass_analysis)
        self.connect_actions(qlass_analysis)
        self.add_short_cut(qlass_analysis)
        QMetaObject.connectSlotsByName(qlass_analysis)

    def retranslateUi(self, qlass_analysis):

        _translate = QCoreApplication.translate
        qlass_analysis.setWindowTitle(_translate("qlass_analysis", "Sleep Analysis - AI based model"))
        self.pushButton_analyse.setText(_translate("qlass_analysis", "Analyse"))
        self.pushButton_load_history.setText(_translate("qlass_analysis", "Load History"))
        self.pushButton_save_pic.setText(_translate("qlass_analysis", "Save pic"))
        self.pushButton_save_data.setText(_translate("qlass_analysis", "Save data"))
        self.top_widget.nav_buttons_widget.button_goto_epoch.setText(_translate("qlass_analysis", "0"))
        # 更新总共的页数
        # self.top_widget.nav_buttons_widget.label_of_page.setText(f" of {self.get_new_page_number()}")

        self.set_bottom_left_widget_start_end_time_text()
        self.top_widget.sleep_analysis_label.setText(_translate("TopWidget", "Sleep Analysis"))
        self.set_label_time_slider_diff()


    def connect_actions(self, qlass_analysis):  # 功能连接方法
        self.pushButton_analyse.clicked.connect(self.analysis_clicked)
        self.pushButton_load_history.clicked.connect(self.on_pushButton_load_history_clicked)
        self.pushButton_load_history.setEnabled(False)
        self.pushButton_load_history.blockSignals(True)

        self.progressBar_completed.connect(self.progressBar_change_canvas_widget)

        self.top_widget.combobox_epoch_length.currentIndexChanged.connect(self.update_epoch_length)
        self.top_widget.combobox_select_n_epochs.currentIndexChanged.connect(self.update_display_n_epochs)
        self.top_widget.nav_buttons_widget.button_previous.clicked.connect(self.update_display_previous_more)
        self.top_widget.nav_buttons_widget.first_pushButton.clicked.connect(self.update_display_first)
        self.top_widget.nav_buttons_widget.last_pushButton.clicked.connect(self.update_display_last)
        self.top_widget.nav_buttons_widget.button_next.clicked.connect(self.update_display_next_more)
        self.top_widget.nav_buttons_widget.button_goto_epoch.clicked.connect(self.update_display_goto_epoch)
        self.bottom_right_top_widget.pushButton_undo.clicked.connect(self.undo_edit)
        self.bottom_right_top_widget.pushButton_redo.clicked.connect(self.redo_edit)
        self.bottom_right_top_widget.pushButton_reset.clicked.connect(self.reset_edit)
        self.bottom_right_top_widget.pushButton_wake.clicked.connect(lambda: self.rem_nrem_wake_button_click(1))
        self.bottom_right_top_widget.pushButton_nrem.clicked.connect(lambda: self.rem_nrem_wake_button_click(2))
        self.bottom_right_top_widget.pushButton_rem.clicked.connect(lambda: self.rem_nrem_wake_button_click(3))
        self.widget_time_slider.time_slider.valueChanged.connect(self.on_slider_changed)

        self.progressBar.valueChanged.connect(self.onProgressChanged)
        self.progressBar.valueChanged.connect(self.updateGifPosition)

        default_name_data = f"epoch_length_{self.epoch_length}_scores"
        default_name_pic = f"{self.top_widget.sleep_analysis_label.text()}_pic"

        # self.pushButton_save_data.clicked.connect(
        #     lambda: SaveUtils.save_data(self.df_score, self.thread_run.save_path, default_name_data, self))
        # self.pushButton_save_pic.clicked.connect(
        #     lambda: SaveUtils.save_pic(self.figure, self.thread_run.save_path, default_name_pic, self))
        self.pushButton_save_pic.clicked.connect(self.open_save_picture_ui)
        self.pushButton_save_data.clicked.connect(self.open_save_data_ui)

    def add_short_cut(self, qlass_analysis):
        # 为Wake按钮添加Shift+1快捷键
        self.shortcut_wake = QShortcut(QKeySequence("Shift+1"), qlass_analysis)
        self.shortcut_wake.activated.connect(lambda: self.rem_nrem_wake_button_click(1))

        # 为NREM按钮添加Shift+2快捷键
        self.shortcut_nrem = QShortcut(QKeySequence("Shift+2"), qlass_analysis)
        self.shortcut_nrem.activated.connect(lambda: self.rem_nrem_wake_button_click(2))

        # 为REM按钮添加Shift+3快捷键
        self.shortcut_rem = QShortcut(QKeySequence("Shift+3"), qlass_analysis)
        self.shortcut_rem.activated.connect(lambda: self.rem_nrem_wake_button_click(3))

        setup_short_cut(self.top_widget.nav_buttons_widget.button_previous,
                        self.top_widget.nav_buttons_widget.button_next,
                        qlass_analysis,
                        self.update_display_first,
                        self.update_display_last)

    # 计算出两个日期之间的时间差值
    def set_label_time_slider_diff(self):
        from datetime import datetime
        start_data_part, start_time_part, end_data_part, end_time_part = self.get_start_end_time_bottom_left_widget()

        start_time = start_data_part + " " + start_time_part
        end_time = end_data_part + " " + end_time_part

        # 将字符串转换为datetime对象
        date_time_obj1 = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        date_time_obj2 = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
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
        self.widget_time_slider.label_end_time.setText(formatted_time) # 如果不满足两位数，需要添加0

    def set_bottom_left_widget_start_end_time_text(self):
        _translate = QCoreApplication.translate
        start_data_part, start_time_part, end_data_part, end_time_part = self.get_start_end_time_bottom_left_widget()
        start_time = QTime.fromString(start_time_part, "HH:mm:ss")
        end_time = QTime.fromString(end_time_part, "HH:mm:ss")
        self.bottom_left_widget.lineedit_start.setTime(start_time)
        self.bottom_left_widget.lineedit_end.setTime(end_time)
        if start_data_part == end_data_part:
            # 只有一个选项
            self.bottom_left_widget.combobox_start.addItem(f"{start_data_part}")
            self.bottom_left_widget.combobox_end.addItem(f"{end_data_part}")
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

    def progressBar_change_canvas_widget(self):
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

        self.plot_results()
        self.canvas.draw()

    # 这里我们需要处理不满足的情况
    def analysis_clicked(self):
        start_time = time.time()

        self.label_draw.hide()
        self.progressBar.show()
        self.label_progressBar_count.show()
        self.label_progressBar.show()
        self.label_gif.show()

        # 刷新 GUI
        QApplication.processEvents()

        # 先进行刷新数据
        self.crop_data()
        # 先将进度条设置为0
        self.widget_time_slider.time_slider.setValue(0)
        # 然后将time_sdlier中的label中的时间更新
        self.set_label_time_slider_diff()
        self.run_analysis()
        end_time = time.time()
        print(f"准备开始进行绘制图片，时间为：{end_time - start_time}")

    def on_pushButton_load_history_clicked(self):
        # 计算原始数据的哈希值
        self.load_analysis_state(self.cached_results)

    def run_analysis(self):
        """运行分析"""
        QLLogging.log.debug("Run the analysis")

        print("run_analysis is running-------")
        start_time = time.time()

        self.pushButton_load_history.setEnabled(True)
        self.pushButton_load_history.blockSignals(False)

        # 将首页页面隐藏，将进度条页面显示出来
        self.icon_with_text_widget.hide()
        # 将显示图像页面也隐藏
        self.bottom_right_top_widget.hide()
        self.scrollarea_canvas.hide()
        self.widget_time_slider.hide()
        self.progressBar_widget.show()

        if self.raw_processed is not None:
            try:
                # 在开始新分析前清理旧数据
                if hasattr(self.thread_run, 'eeg_data'):
                    del self.thread_run.eeg_data
                if hasattr(self.thread_run, 'emg_data'):
                    del self.thread_run.emg_data
                if hasattr(self.thread_run, 'acc_data'):
                    del self.thread_run.acc_data
                if hasattr(self.thread_run, 'spectrogram_data'):
                    del self.thread_run.spectrogram_data

                # 更新线程的通道设置
                self.thread_run.emg_channel = self.bottom_left_widget.combobox_emg.currentText()
                self.thread_run.eeg_channel = self.bottom_left_widget.combobox_eeg.currentText()
                self.thread_run.acc_channel = self.bottom_left_widget.combobox_acc.currentText()
                self.thread_run.model_name = self.model_name

                # 开始分析
                self.progressBar.setValue(1)
                # self.pushButton_analyse.setEnabled(False)
                self.thread_run.start()

                end_time = time.time()
                print(f"线程开始启动，加载时间为：{end_time - start_time}")

            except Exception as e:
                QLLogging.log.exception(f"Error in run_analysis cleanup: {str(e)}")

    def abort_analysis(self):
        """中止分析过程"""
        QLLogging.log.debug("Abort the analysis process")
        try:
            # 停止线程
            if self.thread_run.isRunning():
                self.thread_run.terminate()  # 强制终止线程
                self.thread_run.wait()      # 等待线程完全停止
            
            # 清理数据
            for attr in ['eeg_data', 'emg_data', 'acc_data', 'model',
                        'spectrogram_data', 'df_score']:
                if hasattr(self.thread_run, attr):
                    delattr(self.thread_run, attr)
            
            # 重置进度条和状态
            self.progressBar.setValue(1)
            # self.label_status.setText("Analysis aborted")
            # self.textbox.appendPlainText("Analysis aborted by user")
            
            # 重置按钮状态
            # self.pushButton_analyse.setEnabled(True)
            # self.button_abort.setEnabled(False)
            # self.button_plot.setEnabled(False)
            
            # 重置其他UI元素
            self.top_widget.combobox_select_n_epochs.setEnabled(False)
            self.top_widget.nav_buttons_widget.first_pushButton.setEnabled(False)
            self.top_widget.nav_buttons_widget.last_pushButton.setEnabled(False)
            self.top_widget.nav_buttons_widget.button_previous.setEnabled(False)
            self.top_widget.nav_buttons_widget.button_next.setEnabled(False)
            self.top_widget.nav_buttons_widget.button_goto_epoch.setEnabled(False)
            self.bottom_right_top_widget.pushButton_undo.setEnabled(False)
            self.bottom_right_top_widget.pushButton_redo.setEnabled(False)
            self.slider.setEnabled(False)
            
            # 清理图形
            if hasattr(self, 'figure'):
                self.figure.clear()
                plt.close(self.figure)
                self.canvas.draw()
            
            # 强制垃圾回收
            import gc
            gc.collect()
            
        except Exception as e:
            print(f"Error during abort: {str(e)}")
            QLLogging.log.exception(f"Error during abort: {str(e)}")
            # self.textbox.appendPlainText(f"Error during abort: {str(e)}")

    def update_progress(self, emitted_signal):
        """更新进度条和状态"""
        # print(f"----------------current:{self.progressBar.value()}")
        # print(f"----------------progress:{progress}")
        if not hasattr(self, "progressBar") or not self.progressBar:
            QLLogging.log.exception("Progress bar does not exist, skipping update")
            return
        # print(f"Current thread ID:{threading.get_ident()}")

        try:
            progress, message = emitted_signal
            n_times = self.raw_processed.n_times
            sfreq = self.raw_processed.info['sfreq']
            total_duration = n_times / sfreq

            if progress != 100:
                steps = (progress - self.progressBar.value())
                for i in range(steps):
                    value = self.progressBar.value()
                    if value >= 100:
                        return
                    self.label_progressBar_count.setText(f"{min(value + 1, 100)}%")
                    self.progressBar.setValue(min(value + 1, 100))
                    QApplication.processEvents()  # 处理UI事件
                    # print(f"value:{value}------------------------------------Current thread ID:{threading.get_ident()}")
                    # time.sleep(random.uniform(0, 0.75))  # 控制动画速度
                    if total_duration >= 0 and total_duration < 3600:
                        hms_second = 0.5
                    elif total_duration >= 3600 and total_duration < 21600:
                        hms_second = 1
                    elif total_duration >= 21600 and total_duration < 43200:
                        hms_second = 1.5
                    elif total_duration >= 43200:
                        hms_second = 2
                    time.sleep(random.uniform(0, hms_second))
            # self.label_progressBar_count.setText(f"{progress}%")
            # self.progressBar.setValue(progress)

            if progress == 100:
                self.label_progressBar_count.setText(f"{progress}%")
                self.progressBar.setValue(progress)
                # print(f"progress:{progress}----------Current thread ID:{threading.get_ident()}")
                time.sleep(0.5) # 睡眠0.5秒

                # 将进度条隐藏，显示出文件
                self.label_draw.show()
                self.progressBar.hide()
                self.label_progressBar_count.hide()
                self.label_progressBar.hide()
                self.label_gif.hide()

                # 刷新 GUI
                QApplication.processEvents()

                self.df_score = self.thread_run.df_score
                # 备份一下数据
                self.bank_df_score = self.df_score

                self.n_epochs = len(self.df_score)
                # 这里需要等待线程结束之后，获取到数据
                self.thread_run.wait()
                # 说明加载完成，发送自定义信号，将进度条页面隐藏，图形页面显示出来
                self.progressBar_completed.emit()

                self.enable_navigation_controls()

        except Exception as e:
            QLLogging.log.exception(f"Progress update error: {str(e)}")

    def enable_navigation_controls(self):
        """启导航控件"""
        self.top_widget.combobox_select_n_epochs.setEnabled(True)
        self.top_widget.nav_buttons_widget.first_pushButton.setEnabled(True)
        self.top_widget.nav_buttons_widget.last_pushButton.setEnabled(True)
        self.top_widget.nav_buttons_widget.button_previous.setEnabled(True)
        self.top_widget.nav_buttons_widget.button_next.setEnabled(True)
        self.top_widget.nav_buttons_widget.button_goto_epoch.setEnabled(True)

    def get_start_end_time(self):
        from datetime import datetime, timedelta
        import numpy as np
        time_span_total = len(self.thread_run.eeg_data) / self.raw_processed.info['sfreq']

        time_format = "%Y-%m-%d %H:%M:%S"
        start_time = self.raw_processed.info['meas_date']
        next_half_hour = (start_time + timedelta(minutes=30)).replace(minute=30 if start_time.minute < 30 else 0, second=0, microsecond=0)
        half_hour_span = next_half_hour - start_time

        spans = np.arange(half_hour_span.seconds, time_span_total, 1800)  # 1h span
        return next_half_hour.hour, spans

    def get_start_end_time_bottom_left_widget(self):
        from datetime import timedelta
        start_time = self.raw_processed.info['meas_date']
        end_time = start_time + datetime.timedelta(seconds=self.raw_processed.n_times / self.raw_processed.info['sfreq'])
        start = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end = end_time.strftime('%Y-%m-%d %H:%M:%S')
        # 使用 split() 方法按空格分割
        start_parts = start.split()
        end_parts = end.split()
        start_data_part = start_parts[0]
        start_time_part = start_parts[1]
        end_data_part = end_parts[0]
        end_time_part = end_parts[1]
        return start_data_part, start_time_part, end_data_part, end_time_part

    def fill_vline_per_hour(self, axes):
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

    def plot_results(self):
        """绘制分析结果"""
        import time
        start_time = time.time()

        QLLogging.log.debug("Plot the results of the analysis")
        if self.df_score is None:
            print("No score data available")
            QLLogging.log.info("No score data available")
            return

        # 更新总共的页数
        print(f"self.get_new_page_number():{self.get_new_page_number()}")
        self.top_widget.nav_buttons_widget.button_goto_epoch.setText("1")
        self.top_widget.nav_buttons_widget.label_of_page.setText(f" of {self.get_new_page_number()}")

        try:
            # 在开始绘图前清理之前的状态
            if hasattr(self, 'highlight_lines'):
                for line in self.highlight_lines:
                    try:
                        line.remove()
                    except:
                        pass
                self.highlight_lines = []
            self.current_selected_epoch = None
            self.current_selected_epochs = []
            self.shift_begin = None

            # 清理之前的图形
            if hasattr(self, 'figure'):
                self.figure.clear()
                plt.close(self.figure)

            self.scores = self.df_score['Stage_Code'].values
            self.stages = self.df_score['Stage'].values
            self.color_epochs = [self.map_colors[score] for score in self.scores]

            # Clear previous plot
            self.figure.clf()

            # 重置高亮选择状态
            self.highlight_lines = []
            self.current_selected_epoch = None
            self.current_selected_epochs = []

            end_time1 = time.time()

            print(f"清理之前状态的数据，用时为：{end_time1 - start_time}")

            n_epochs_display = self.get_n_epochs_display()

            # 获取降采样数据
            print(self.raw_processed.info["sfreq"])
            resampled_data = self.raw_processed.get_data() * 1e-6
            eeg_data = self.thread_run.eeg_data

            # 计算时间数组 (使用100Hz采样率)
            time_sec = np.arange(0, len(eeg_data)/100, 1/100)
            time_epochs_start = np.arange(len(self.scores)) * self.epoch_length
            time_epochs_end = time_epochs_start + self.epoch_length

            ax_hypnogram = self.figure.add_axes([0.017, 0, 1, 1])

            # 创建子图 - 更新比例以适应新的布局
            # gs = self.figure.add_gridspec(1, 1, height_ratios=[1])
            # # 调整画布的尺寸以适应所有子图
            # self.figure.subplots_adjust(left=0.01, right=1, bottom=0, top=1)
            #
            # # 1. 睡眠分期图
            # ax_hypnogram = self.figure.add_subplot(gs[0])
            ax_hypnogram.hlines(self.scores, time_epochs_start, time_epochs_end,
                                colors=self.color_epochs, linewidths=40)  # 这里很耗时

            ax_hypnogram.set_yticks([1, 2, 3])
            ax_hypnogram.set_yticklabels(["Wake", "NREM", "REM"])
            ax_hypnogram.get_xaxis().set_visible(False)
            ax_hypnogram.set_ylim(0, 3.5)
            ax_hypnogram.set_ylabel("Stage")

            ax_hypnogram.tick_params(labelsize=40)  # 设置刻度标签字体大小
            # ax_hypnogram.set_xlabel(ax_hypnogram.get_xlabel(), fontsize=40)  # 设置x轴标签字体大小
            ax_hypnogram.set_ylabel(ax_hypnogram.get_ylabel(), fontsize=40)  # 设置y轴标签字体大小
            ax_hypnogram.set_title(ax_hypnogram.get_title(), fontsize=40)  # 设置标题字体大小

            # 设置轴标签的字体大小
            for label in ax_hypnogram.get_xticklabels():
                label.set_fontsize(80)
            for label in ax_hypnogram.get_yticklabels():
                label.set_fontsize(40)

            ax_hypnogram.margins(x=0, y=0)  # 消除子图内部边距

            self.canvas.setFocusPolicy(Qt.StrongFocus)
            self.canvas.setFocus()

            # 更新epoch标签
            self.update_epoch_labels(n_epochs_display)

            self.canvas.draw()
            self.sleep_score_wh.finish_backup()
            self.sleep_redo_score_wh.finish_backup()

        except Exception as e:
            print(f"Error in plot_results: {str(e)}")
            QLLogging.log.exception(f"Error in plot_results: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # 强制清理不需要的数据
            if hasattr(self, 'highlight_lines'):
                self.highlight_lines.clear()

        self.plot_eeg.clear()

        eeg_curve = pg.PlotCurveItem(
            x=time_sec,
            y=eeg_data,
            pen=pg.mkPen(color='k', width=1.0)
        )
        self.plot_eeg.addItem(eeg_curve)

        self.plot_eeg.setLabel('left', "EEG Amplitude", units="uV")

        # 隐藏 X 轴刻度（与 Matplotlib 保持一致）
        self.plot_eeg.hideAxis('bottom')

        x_min = time_sec[0]
        x_max = time_sec[-1]
        self.plot_eeg.setXRange(x_min, x_max, padding=0)

        # 动态设置 Y 轴范围
        eeg_range = "±500"
        if eeg_range != "Auto":
            amplitude = float(eeg_range.replace('±', ''))
            print(amplitude)
            self.plot_eeg.setYRange(-amplitude, amplitude)

        # 启用抗锯齿（提升视觉效果）
        pg.setConfigOptions(antialias=True)

        if hasattr(self.thread_run, 'emg_data'):
            emg_data = self.thread_run.emg_data
            emg_envelope = np.abs(scipy.signal.hilbert(emg_data))

            self.plot_emg.clear()

            # 创建曲线（绿色，线宽 1.0）
            emg_curve = pg.PlotCurveItem(
                x=time_sec,
                y=emg_envelope,
                pen=pg.mkPen(color='g', width=1.0)
            )
            self.plot_emg.addItem(emg_curve)

            # 设置 Y 轴标签
            self.plot_emg.setLabel('left', 'EMG Envelope', units='uV')

            x_min = time_sec[0]
            x_max = time_sec[-1]
            self.plot_emg.setXRange(x_min, x_max, padding=0)

            # 动态设置 Y 轴范围（EMG 包络线为非负值）
            emg_range = "±200"
            if emg_range != "Auto":
                amplitude = int(emg_range.replace('±', ''))
                self.plot_emg.setYRange(0, amplitude)

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

            x_min = time_sec[0]
            x_max = time_sec[-1]
            self.plot_acc.setXRange(x_min, x_max, padding=0)

            # 动态设置 Y 轴范围
            acc_range = "±2000"
            if acc_range != "Auto":
                amplitude = int(acc_range.replace('±', ''))
                self.plot_acc.setYRange(-amplitude, amplitude)

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

                    # 设置坐标轴
                    self.plot_widget.setLabel('left', 'EEG Frequency', units='Hz')
                    self.plot_widget.setLabel('bottom', 'Time', units='s')
                    self.plot_widget.setYRange(y_min, y_max, padding=0)
                    self.plot_widget.setXRange(x_min, x_max, padding=0)

                    # 反转Y轴使低频在下（模仿Matplotlib的origin='lower'）
                    self.plot_widget.invertY(False)  # False表示不反转（低频在底部）

                except Exception as e:
                    print(f"Error plotting spectrogram: {str(e)}")
        end_time7 = time.time()

        # print(f"绘制EEG时频图，用时为：{end_time7 - end_time6}")


    def drag_end(self, event):
        print("drag_end")
        self.button_is_pressed = False
        self.mouse_is_dragged = False
        self.mouse_dragged_begin = None

    def if_select_all_epochs(self):
        return "ALL" == self.top_widget.combobox_select_n_epochs.currentText()

    def get_n_epochs_display(self):
        """获取显示的epoch数量"""
        text = self.top_widget.combobox_select_n_epochs.currentText()
        if text == "All":
            self.widget_time_slider.hide()
            return self.n_epochs
        self.widget_time_slider.show()
        return int(text)

    def update_epoch_labels(self, n_epochs_display):
        # 更新一下label
        self.top_widget.nav_buttons_widget.label_of_page.setText(f" of {self.get_new_page_number()}")

        """更新epoch标签"""
        # 确保有效的轴索引
        if not hasattr(self, 'epochlabels'):
            self.epochlabels = []

        # 清除现有标签
        for label in self.epochlabels:
            try:
                label.remove()
            except:
                pass
        self.epochlabels = []

        # 只在显示少于等于50个epoch时添加标签
        if n_epochs_display <= 100:
            try:
                # 使用第一个轴（hypnogram）
                hypnogram_ax = self.figure.axes[0]
                if hypnogram_ax is None:
                    return

                # 确保epoch_start不会导致标签超出数据范围
                max_epochs = len(self.df_score)

                # 根据显示的epoch数量调整标签间隔
                if n_epochs_display <= 20:
                    label_interval = 1  # 每个epoch都显示标签
                else:  # 50个epochs的情况
                    label_interval = 5  # 每5个epoch显示一个标签

                # 计算实际可显示的epoch数量
                actual_n_epochs = min(n_epochs_display, max_epochs - self.epoch_start)

                for i in range(0, actual_n_epochs, label_interval):
                    epoch_num = self.epoch_start + i
                    if epoch_num < max_epochs:  # 确保不超出数据范围
                        # 计算标签位置
                        x_pos = (epoch_num + 0.5) * self.epoch_length

                        label = hypnogram_ax.annotate(
                            str(epoch_num),
                            xy=(x_pos, 0),  # 在y=0位置
                            # xytext=(x_pos, -0.2),  # 文本位置稍低一些
                            xytext=(x_pos, 0.5),  # 文本位置稍低一些
                            ha="center",
                            va="top",
                            fontsize=28
                        )
                        self.epochlabels.append(label)

                # 强制更新画布
                self.canvas.draw()
            except Exception as e:
                print(f"Error in update_epoch_labels: {str(e)}")
                QLLogging.log.exception(f"Error in update_epoch_labels: {str(e)}")
    def reset_edit(self):
        while not self.sleep_score_wh.is_empty():
            self.prepare_score_when_reset()
            self.refresh_sleep_score()

        self.sleep_redo_score_wh.clear()
        self.sleep_score_wh.clear()
        self.bottom_right_top_widget.pushButton_undo.setEnabled(False)
        self.bottom_right_top_widget.pushButton_redo.setEnabled(False)

    def undo_edit(self):
        self.prepare_score_when_undo()
        self.refresh_sleep_score()
        self.undo_post_process()

    def redo_edit(self):
        self.prepare_score_when_redo()
        self.refresh_sleep_score()
        self.redo_post_process()

    def update_display_previous(self):
        """显示上一个结果"""
        # epochs_per_page = self.get_epochs_per_page()
        n_epochs_display = self.get_n_epochs_display()
        if self.epoch_start >= 1:
            self.epoch_start -= 1
        else:
            self.epoch_start = 0
        # 更新所有轴的显示范围
        n_epochs_display = self.get_n_epochs_display()

        # 需要更新button_goto_spoch的页面
        self.top_widget.nav_buttons_widget.button_goto_epoch.setText(str(self.epoch_start / self.get_n_epochs_display()))

        for ax in self.figure.axes:
            ax.set_xlim(
                self.epoch_length * self.epoch_start,
                self.epoch_length * (self.epoch_start + n_epochs_display)
            )
        x_min = self.epoch_length * self.epoch_start
        x_max = self.epoch_length * (self.epoch_start + n_epochs_display)
        for plot in [self.plot_acc, self.plot_emg, self.plot_eeg,
                     self.plot_hypnogram, self.plot_widget]:
            # 只更新视图，不触发数据重绘
            plot.blockSignals(True)  # 避免触发信号循环

            # 直接设置视图范围
            plot.getViewBox().disableAutoRange(axis=pg.ViewBox.XAxis)
            plot.getViewBox().setRange(
                xRange=(x_min, x_max),
                update=True,  # 立即更新视图
                padding=0
            )

            plot.blockSignals(False)  # 避免触发信号循环

        self.update_epoch_labels(n_epochs_display)
        self.canvas.draw()

    def update_display_first(self):
        """显示第一页的结果"""
        # 获取每页显示的epoch数量
        n_epochs_display = self.get_n_epochs_display()
        # 将起始epoch设置为第一页
        self.epoch_start = 0

        # 需要更新一下进度条的事情
        self.widget_time_slider.time_slider.setValue(self.epoch_start)

        # 需要更新button_goto_spoch的页面
        self.top_widget.nav_buttons_widget.button_goto_epoch.setText(str(int(self.epoch_start / self.get_n_epochs_display()) + 1))

        # # 更新所有轴的显示范围
        for ax in self.figure.axes:
            ax.set_xlim(
                self.epoch_length * self.epoch_start,
                self.epoch_length * (self.epoch_start + n_epochs_display)
            )

        x_min = self.epoch_length * self.epoch_start
        x_max = self.epoch_length * (self.epoch_start + n_epochs_display)
        for plot in [self.plot_acc, self.plot_emg, self.plot_eeg,
                     self.plot_hypnogram, self.plot_widget]:
            # 只更新视图，不触发数据重绘
            plot.blockSignals(True)  # 避免触发信号循环

            # 直接设置视图范围
            plot.getViewBox().disableAutoRange(axis=pg.ViewBox.XAxis)
            plot.getViewBox().setRange(
                xRange=(x_min, x_max),
                update=True,  # 立即更新视图
                padding=0
            )

            plot.blockSignals(False)  # 避免触发信号循环

        self.update_epoch_labels(n_epochs_display)
        self.canvas.draw()

    def update_display_previous_more(self):
        """显示前页结果"""
        n_epochs_display = self.get_n_epochs_display()
        if self.epoch_start >= n_epochs_display:
            self.epoch_start -= n_epochs_display
        else:
            self.epoch_start = 0

        self.widget_time_slider.time_slider.setValue(int(self.epoch_start * self.epoch_length))

        # # 需要更新进度条的进度
        # self.widget_time_slider.time_slider.setValue(self.epoch_start)

        # 需要更新button_goto_spoch的页面
        self.top_widget.nav_buttons_widget.button_goto_epoch.setText(str(int(self.epoch_start / self.get_n_epochs_display()) + 1))

        for ax in self.figure.axes:
            ax.set_xlim(
                self.epoch_length * self.epoch_start,
                self.epoch_length * (self.epoch_start + n_epochs_display)
            )

        x_min = self.epoch_length * self.epoch_start
        x_max = self.epoch_length * (self.epoch_start + n_epochs_display)
        for plot in [self.plot_acc, self.plot_emg, self.plot_eeg,
                     self.plot_hypnogram, self.plot_widget]:
            # 只更新视图，不触发数据重绘
            plot.blockSignals(True)  # 避免触发信号循环

            # 直接设置视图范围
            plot.getViewBox().disableAutoRange(axis=pg.ViewBox.XAxis)
            plot.getViewBox().setRange(
                xRange=(x_min, x_max),
                update=True,  # 立即更新视图
                padding=0
            )

            plot.blockSignals(False)  # 避免触发信号循环

        self.update_epoch_labels(n_epochs_display)
        self.canvas.draw()

    def update_display_next(self):
        """显示下一个结果"""
        n_epochs_display = self.get_n_epochs_display()
        max_start = max(0, self.n_epochs - n_epochs_display)
        if self.epoch_start < max_start:
            # self.epoch_start += epochs_per_page
            self.epoch_start += 1
            # 确保不会超出最大起始位置
            self.epoch_start = min(self.epoch_start, max_start)

            # 需要更新button_goto_spoch的页面
            self.top_widget.nav_buttons_widget.button_goto_epoch.setText(str(int(self.epoch_start / self.get_n_epochs_display())))

            # # 更新所有轴的显示范围
            for ax in self.figure.axes:
                ax.set_xlim(
                    self.epoch_length * self.epoch_start,
                    self.epoch_length * (self.epoch_start + n_epochs_display)
                )

            x_min = self.epoch_length * self.epoch_start
            x_max = self.epoch_length * (self.epoch_start + n_epochs_display)
            for plot in [self.plot_acc, self.plot_emg, self.plot_eeg,
                         self.plot_hypnogram, self.plot_widget]:
                # 只更新视图，不触发数据重绘
                plot.blockSignals(True)  # 避免触发信号循环

                # 直接设置视图范围
                plot.getViewBox().disableAutoRange(axis=pg.ViewBox.XAxis)
                plot.getViewBox().setRange(
                    xRange=(x_min, x_max),
                    update=True,  # 立即更新视图
                    padding=0
                )

                plot.blockSignals(False)  # 避免触发信号循环

            self.update_epoch_labels(n_epochs_display)
            self.canvas.draw()

    def update_display_last(self):
        """显示最后一页的内容"""
        # 获取每页显示的epoch数量
        n_epochs_display = self.get_n_epochs_display()
        # 计算总 epoch 数量
        total_epochs = self.n_epochs
        # 计算最后一页的起始epoch
        max_start = max(0, total_epochs - n_epochs_display)
        self.epoch_start = max_start

        # 需要更新进度条的进度
        self.widget_time_slider.time_slider.setValue(int(self.epoch_start * self.epoch_length))

        # 需要更新button_goto_spoch的页面
        self.top_widget.nav_buttons_widget.button_goto_epoch.setText(str(int(self.epoch_start / self.get_n_epochs_display()) + 1))

        # 更新所有轴的显示范围
        for ax in self.figure.axes:
            ax.set_xlim(
                self.epoch_length * self.epoch_start,  # 起始位置
                self.epoch_length * min(self.epoch_start + n_epochs_display, total_epochs)  # 结束位置
            )

            # 更新 epoch 标签
        self.update_epoch_labels(n_epochs_display)

        # 刷新画布
        self.canvas.draw()

    def update_display_next_more(self):
        """显示后几页结果"""
        n_epochs_display = self.get_n_epochs_display()
        max_start = max(0, self.n_epochs - n_epochs_display)
        new_start = self.epoch_start + n_epochs_display
        self.epoch_start = min(new_start, max_start)

        self.widget_time_slider.time_slider.setValue(int(self.epoch_start * self.epoch_length))

        # 需要更新button_goto_spoch的页面
        self.top_widget.nav_buttons_widget.button_goto_epoch.setText(str(int(self.epoch_start / self.get_n_epochs_display()) + 1))

        # # 需要更新进度条的进度
        # self.widget_time_slider.time_slider.setValue(self.epoch_start)

        # 更新所有轴的显示范围
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
            min_value = 1
            max_value = self.get_new_page_number()
            prompt = f"Enter the Epoch You Want to View:[{min_value}, {max_value}]"
            target_epoch, done = QInputDialog.getInt(
                self.window, 'Input Dialog', prompt,
                min=min_value, max=max_value)
            if done:
                # self.top_widget.nav_buttons_widget.button_goto_epoch.setText(QCoreApplication.translate("qlass_analysis", str(target_epoch)))

                # 设置进度条的值
                self.widget_time_slider.time_slider.setValue(int((target_epoch - 1) * self.epoch_length * self.get_n_epochs_display()))
                self.goto_epoch((target_epoch - 1) * self.get_n_epochs_display())
        except Exception as e:
            print(f"Error in update_display_goto_epoch: {str(e)}")
            QLLogging.log.exception(f"Error in update_display_goto_epoch: {str(e)}")

    def goto_epoch(self, target_epoch):
        try:
            self.epoch_start = target_epoch
            n_epochs_display = self.get_n_epochs_display()
            # 更新所有轴的显示范围
            for ax in self.figure.axes:
                ax.set_xlim(
                    self.epoch_length * self.epoch_start,
                    self.epoch_length * (self.epoch_start + n_epochs_display)
                )
            self.update_epoch_labels(n_epochs_display)
            self.canvas.draw()
        except Exception as e:
            print(f"Error in goto_epoch: {str(e)}")
            QLLogging.log.exception(f"Error in goto_epoch: {str(e)}")

    def update_display_n_epochs(self):
        """更新显示的epoch数量"""
        try:
            n_epochs_display = self.get_n_epochs_display()

            if self.top_widget.combobox_select_n_epochs.currentText() == "All":
                self.pushButton_save_pic.setEnabled(True)
                self.widget_time_slider.hide()
                self.widget_time_slider.time_slider.setValue(0)
                # 以第一个选中的为中心
                self.epoch_start = self.widget_time_slider.time_slider.value() / self.epoch_length
                self.top_widget.nav_buttons_widget.button_goto_epoch.setText(str(int(self.epoch_start // n_epochs_display) + 1))
            else:
                self.pushButton_save_pic.setEnabled(False)
                self.widget_time_slider.show()
                # 以第一个选中的为中心
                self.epoch_start = self.widget_time_slider.time_slider.value() / self.epoch_length
                self.top_widget.nav_buttons_widget.button_goto_epoch.setText(str(int(self.epoch_start // n_epochs_display) + 1))

            # 更新x轴范围
            for ax in self.figure.axes:
                ax.set_xlim(
                    self.epoch_length * self.epoch_start,
                    self.epoch_length * (self.epoch_start + n_epochs_display)
                )

            x_min = self.epoch_length * self.epoch_start
            x_max = self.epoch_length * (self.epoch_start + n_epochs_display)
            for plot in [self.plot_acc, self.plot_emg, self.plot_eeg,
                     self.plot_hypnogram, self.plot_widget]:
                # 只更新视图，不触发数据重绘
                plot.blockSignals(True)  # 避免触发信号循环

                # 直接设置视图范围
                plot.getViewBox().disableAutoRange(axis=pg.ViewBox.XAxis)
                plot.getViewBox().setRange(
                    xRange=(x_min, x_max),
                    update=True,  # 立即更新视图
                    padding=0
                )
                plot.blockSignals(False)  # 恢复信号

            self.update_epoch_labels(n_epochs_display)
            self.canvas.draw()
        except Exception as e:
            print(f"Error in update_display_n_epochs: {str(e)}")
            QLLogging.log.exception(f"Error in update_display_n_epochs: {str(e)}")

    def get_selected_new_start(self, n_epochs_display):
        for one_epoch in self.current_selected_epochs:
            new_start = one_epoch - n_epochs_display / 2
            new_start = max(0, new_start)
            return new_start
        return self.epoch_start


    def prepare_score_when_edit(self, action_str):
        # 更新选中epoch的睡眠阶段
        # 这里需要改变，
        new_stage = action_str
        stage_code = {v: k for k, v in self.map_stages.items()}[new_stage]
        for selected_epoch in self.current_selected_epochs:
            self.sleep_score_wh.record(selected_epoch, self.df_score.at[selected_epoch, 'Stage_Code']);
            self.df_score.at[selected_epoch, 'Stage_Code'] = stage_code
            self.df_score.at[selected_epoch, 'Stage'] = new_stage
            # print("user_edit_stage:", selected_epoch,  new_stage, stage_code)
    def prepare_score_when_reset(self):
        # 将现在的sleep_score清空
        restore_data = self.sleep_score_wh.get_restore_data()
        if len(restore_data) == 0:
            return
        for key, value in restore_data.items():
            self.df_score.at[key, 'Stage_Code'] = value
            self.df_score.at[key, 'Stage'] = self.map_stages[value]
    def prepare_score_when_undo(self):
        restore_data = self.sleep_score_wh.get_restore_data()
        if len(restore_data) == 0:
            return
        for key, value in restore_data.items():
            self.sleep_redo_score_wh.record(key, self.df_score.at[key, 'Stage_Code'] )
            self.df_score.at[key, 'Stage_Code'] = value
            self.df_score.at[key, 'Stage'] = self.map_stages[value]

    def prepare_score_when_redo(self):
        restore_data = self.sleep_redo_score_wh.get_restore_data()
        if len(restore_data) == 0:
            return
        for key, value in restore_data.items():
            self.sleep_score_wh.record(key, self.df_score.at[key, 'Stage_Code'] )
            self.df_score.at[key, 'Stage_Code'] = value
            self.df_score.at[key, 'Stage'] = self.map_stages[value]

    def refresh_sleep_score(self):
        # 重新计算睡眠阶段统计
        stage_counts = self.df_score["Stage_Code"].value_counts()
        self.df_score.loc[0, "Wake_Count"] = stage_counts.get(1, 0)
        self.df_score.loc[0, "NREM_Count"] = stage_counts.get(2, 0)
        self.df_score.loc[0, "REM_Count"] = stage_counts.get(3, 0)

        self.plot_results()
        n_epochs_display = self.get_n_epochs_display()

        x_min = self.epoch_length * self.epoch_start
        x_max = self.epoch_length * (self.epoch_start + n_epochs_display)

        for ax in self.figure.axes:
            ax.set_xlim(
                x_min,
                x_max
            )

        self.canvas.draw()

        for plot in [self.plot_acc, self.plot_emg, self.plot_eeg, self.plot_widget]:
            # 只更新视图，不触发数据重绘
            plot.blockSignals(True)  # 避免触发信号循环
            # 直接设置视图范围
            plot.getViewBox().disableAutoRange(axis=pg.ViewBox.XAxis)
            plot.getViewBox().setRange(
                xRange=(x_min, x_max),
                update=True,  # 立即更新视图
                padding=0
            )
            plot.blockSignals(False)  # 恢复信号

        # """绘制分析结果"""
        # import time
        # start_time = time.time()
        #
        # QLLogging.log.debug("Plot the results of the analysis")
        # if self.df_score is None:
        #     print("No score data available")
        #     QLLogging.log.info("No score data available")
        #     return
        #
        # # 更新总共的页数
        # print(f"self.get_new_page_number():{self.get_new_page_number()}")
        # self.top_widget.nav_buttons_widget.button_goto_epoch.setText("1")
        # self.top_widget.nav_buttons_widget.label_of_page.setText(f" of {self.get_new_page_number()}")
        #
        # try:
        #     # 在开始绘图前清理之前的状态
        #     if hasattr(self, 'highlight_lines'):
        #         for line in self.highlight_lines:
        #             try:
        #                 line.remove()
        #             except:
        #                 pass
        #         self.highlight_lines = []
        #     self.current_selected_epoch = None
        #     self.current_selected_epochs = []
        #     self.shift_begin = None
        #
        #     # 清理之前的图形
        #     if hasattr(self, 'figure'):
        #         self.figure.clear()
        #         plt.close(self.figure)
        #
        #     self.scores = self.df_score['Stage_Code'].values
        #     self.stages = self.df_score['Stage'].values
        #     self.color_epochs = [self.map_colors[score] for score in self.scores]
        #
        #     # Clear previous plot
        #     self.figure.clf()
        #
        #     # 重置高亮选择状态
        #     self.highlight_lines = []
        #     self.current_selected_epoch = None
        #     self.current_selected_epochs = []
        #
        #     end_time1 = time.time()
        #
        #     print(f"清理之前状态的数据，用时为：{end_time1 - start_time}")
        #
        #     n_epochs_display = self.get_n_epochs_display()
        #
        #     # 获取降采样数据
        #     print(self.raw_processed.info["sfreq"])
        #     resampled_data = self.raw_processed.get_data() * 1e-6
        #     eeg_data = self.thread_run.eeg_data
        #
        #     # 计算时间数组 (使用100Hz采样率)
        #     time_sec = np.arange(0, len(eeg_data) / 100, 1 / 100)
        #     time_epochs_start = np.arange(len(self.scores)) * self.epoch_length
        #     time_epochs_end = time_epochs_start + self.epoch_length
        #
        #     ax_hypnogram = self.figure.add_axes([0.017, 0, 1, 1])
        #
        #     ax_hypnogram.hlines(self.scores, time_epochs_start, time_epochs_end,
        #                         colors=self.color_epochs, linewidths=40)  # 这里很耗时
        #
        #     ax_hypnogram.set_yticks([1, 2, 3])
        #     ax_hypnogram.set_yticklabels(["Wake", "NREM", "REM"])
        #     ax_hypnogram.get_xaxis().set_visible(False)
        #     ax_hypnogram.set_ylim(0, 3.5)
        #     ax_hypnogram.set_ylabel("Stage")
        #
        #     ax_hypnogram.tick_params(labelsize=40)  # 设置刻度标签字体大小
        #     # ax_hypnogram.set_xlabel(ax_hypnogram.get_xlabel(), fontsize=40)  # 设置x轴标签字体大小
        #     ax_hypnogram.set_ylabel(ax_hypnogram.get_ylabel(), fontsize=40)  # 设置y轴标签字体大小
        #     ax_hypnogram.set_title(ax_hypnogram.get_title(), fontsize=40)  # 设置标题字体大小
        #
        #     # 设置轴标签的字体大小
        #     for label in ax_hypnogram.get_xticklabels():
        #         label.set_fontsize(80)
        #     for label in ax_hypnogram.get_yticklabels():
        #         label.set_fontsize(40)
        #
        #     ax_hypnogram.margins(x=0, y=0)  # 消除子图内部边距
        #
        #     self.canvas.setFocusPolicy(Qt.StrongFocus)
        #     self.canvas.setFocus()
        #
        #     # 更新epoch标签
        #     self.update_epoch_labels(n_epochs_display)
        #
        #     self.sleep_score_wh.finish_backup()
        #     self.sleep_redo_score_wh.finish_backup()
        #
        #     # 更新所有轴的显示范围
        #     n_epochs_display = self.get_n_epochs_display()
        #
        #     x_min = self.epoch_length * self.epoch_start
        #     x_max = self.epoch_length * (self.epoch_start + n_epochs_display)
        #
        #     for ax in self.figure.axes:
        #         ax.set_xlim(
        #             x_min,
        #             x_max
        #         )
        #
        #     self.canvas.draw()
        #
        #     for plot in [self.plot_acc, self.plot_emg, self.plot_eeg, self.plot_widget]:
        #         # 只更新视图，不触发数据重绘
        #         plot.blockSignals(True)  # 避免触发信号循环
        #         # 直接设置视图范围
        #         plot.getViewBox().disableAutoRange(axis=pg.ViewBox.XAxis)
        #         plot.getViewBox().setRange(
        #             xRange=(x_min, x_max),
        #             update=True,  # 立即更新视图
        #             padding=0
        #         )
        #         plot.blockSignals(False)  # 恢复信号
        #
        # except Exception as e:
        #     print(f"Error in plot_results: {str(e)}")
        #     QLLogging.log.exception(f"Error in plot_results: {str(e)}")
        #     import traceback
        #     traceback.print_exc()
        # finally:
        #     # 强制清理不需要的数据
        #     if hasattr(self, 'highlight_lines'):
        #         self.highlight_lines.clear()

    def rem_nrem_wake_button_click(self, index):
        print(f"------------------{index}__________________")
        # 判断是哪一个按钮触发了点击事件
        if index == 1:
            self.user_edit_stage("Wake")
        elif index == 2:
            self.user_edit_stage("NREM")
        elif index == 3:
            self.user_edit_stage("REM")

    def user_edit_stage(self, action_str):
        """处理用户编辑的睡眠阶段"""
        # 如果是由点击事件触发的更改，则忽略
        if self._ignore_combobox_change:
            return

        if self.current_selected_epochs is not None:
            self.prepare_score_when_edit(action_str)
            self.refresh_sleep_score()
            self.edit_post_process()

    def edit_post_process(self):
        if self.sleep_score_wh.is_empty():
            self.bottom_right_top_widget.pushButton_undo.setEnabled(False)
        else:
            self.bottom_right_top_widget.pushButton_undo.setEnabled(True)

        self.bottom_right_top_widget.pushButton_redo.setEnabled(False)
        self.sleep_redo_score_wh.clear()

    def undo_post_process(self):
        self.bottom_right_top_widget.pushButton_redo.setEnabled(True)
        if self.sleep_score_wh.is_empty():
            self.bottom_right_top_widget.pushButton_undo.setEnabled(False)

    def redo_post_process(self):
        self.bottom_right_top_widget.pushButton_undo.setEnabled(True)
        if self.sleep_redo_score_wh.is_empty():
            self.bottom_right_top_widget.pushButton_redo.setEnabled(False)

    def update_epoch_length(self):
        try:
            """处理epoch长度更新"""
            new_length = int(self.top_widget.combobox_epoch_length.currentText())
            if new_length != self.epoch_length:
                self.epoch_length = new_length
                # 需要更新
                if self.thread_run is not None:
                    self.thread_run.epoch_length = new_length
                    print(new_length)

        except Exception as e:
            print(e)
            QLLogging.log.exception(f"update_epoch_length error: {str(e)}")


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

    def on_slider_changed(self):
        try:
            """处理滑块值变化"""
            from datetime import datetime
            """处理label_start的时间变化"""
            # 计算当前时间
            # current_time = self.widget_time_slider.time_slider.value()
            # 将当前时间转换为时分秒的字符串形式
            # hours = int(current_time) // 3600
            # minutes = (int(current_time) % 3600) // 60
            # seconds = int(current_time) % 60
            # current_time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
            # self.widget_time_slider.label_start_time.setText(current_time_str)

            n_epochs_display = self.get_n_epochs_display()
            # self.epoch_start = self.widget_time_slider.time_slider.value() / self.epoch_length # 这里会越界

            self.epoch_start = min(self.widget_time_slider.time_slider.value() / self.epoch_length, self.get_total_time_number().total_seconds() / self.epoch_length - n_epochs_display)

            # 需要更新button_goto_spoch的页面
            # 计算两个值
            value1 = int(self.epoch_start / self.get_n_epochs_display()) + 1
            value2 = self.get_new_page_number()

            # 设置按钮文本为这两个值中的最小值
            self.top_widget.nav_buttons_widget.button_goto_epoch.setText(str(min(value1, value2)))

            # 更新显示范围
            for ax in self.figure.axes:
                current_xlim = ax.get_xlim()
                new_xlim = (self.epoch_length * self.epoch_start,
                            self.epoch_length * (self.epoch_start + n_epochs_display))
                if current_xlim != new_xlim:
                    ax.set_xlim(new_xlim)
            x_min = self.epoch_length * self.epoch_start
            x_max = self.epoch_length * (self.epoch_start + n_epochs_display)
            for plot in [self.plot_acc, self.plot_emg, self.plot_eeg,
                     self.plot_hypnogram, self.plot_widget]:
                # 只更新视图，不触发数据重绘
                plot.blockSignals(True)  # 避免触发信号循环

                # 直接设置视图范围
                plot.getViewBox().disableAutoRange(axis=pg.ViewBox.XAxis)
                plot.getViewBox().setRange(
                    xRange=(x_min, x_max),
                    update=True,  # 立即更新视图
                    padding=0
                )

                plot.blockSignals(False)  # 恢复信号

            self.update_epoch_labels(n_epochs_display)
            self.canvas.draw()
        except Exception as e:
            QLLogging.log.exception(f"on_slider_changed error: {str(e)}")

    def update_signal_range(self, sender=None, value=None):
        """更新信号图的幅度范围"""
        try:
            # 确定是哪个下拉菜单触发了更新
            if sender == "eeg" or sender is None:
                # 更新EEG信号范围
                if value == "Auto":
                    self.plot_eeg.enableAutoRange(axis=pg.ViewBox.YAxis)
                else:
                    amplitude = int(value.replace('±', ''))
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
                    self.plot_emg.enableAutoRange(axis=pg.ViewBox.YAxis)
                else:
                    amplitude = int(value.replace('±', ''))
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
                    self.plot_acc.enableAutoRange(axis=pg.ViewBox.YAxis)
                else:
                    amplitude = int(value.replace('±', ''))
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

    def closeEvent(self, event):
        """重写closeEvent以在关闭窗口时完全清理所有资源"""
        try:
            # 1. 如果正在分析，先中止分析
            if hasattr(self, 'thread_run') and self.thread_run.isRunning():
                self.abort_analysis()

            # 2. 清理线程相关资源
            if hasattr(self, 'thread_run'):
                if self.thread_run.isRunning():
                    self.thread_run.quit()
                    self.thread_run.wait()
                del self.thread_run

            # 3. 清理图形资源
            if hasattr(self, 'figure'):
                self.figure.clear()
                plt.close(self.figure)
                del self.figure

            if hasattr(self, 'canvas'):
                self.canvas.close()
                del self.canvas

            # 4. 清理数据资源
            data_attributes = [
                'raw_processed',
                'df_score',
                'eeg_data',
                'emg_data',
                'acc_data',
                'spectrogram_data',
                'scores',
                'stages',
                'color_epochs',
                'highlight_lines',
                'epochlabels',
                'current_selected_epoch',
                'n_epochs',
                'epoch_start',
                'edf_path'
            ]

            for attr in data_attributes:
                if hasattr(self, attr):
                    delattr(self, attr)

            # 5. 断开所有信号连接
            self.event_handler.disconnect_events()

            # 6. 重置所有UI元素状态
            self.progressBar.setValue(1)
            self.top_widget.combobox_select_n_epochs.setEnabled(False)

            # 7. 强制多次垃圾回收
            import gc
            gc.collect()
            gc.collect()

            # 8. 打印内存使用情况（用于调试）
            import psutil
            process = psutil.Process()
            QLLogging.log.debug(f"Memory usage after cleanup: {process.memory_info().rss / 1024 / 1024:.2f} MB")

            # 9. 接受关闭事件
            event.accept()

        except Exception as e:
            QLLogging.log.exception(f"Error during window closing: {str(e)}")
            import traceback
            traceback.print_exc()
            event.accept()  # 即使发生错误也关闭窗口

    def crop_data(self):
        """截取数据并立即更新"""
        QLLogging.log.debug("Capture data and update it instantly")
        # 读取时间输入
        start_str = self.bottom_left_widget.combobox_start.currentText() + " " + self.bottom_left_widget.lineedit_start.time().toString("HH:mm:ss")
        end_str = self.bottom_left_widget.combobox_end.currentText() + " " + self.bottom_left_widget.lineedit_end.time().toString("HH:mm:ss")

        # 定义时间格式
        time_format = "%Y-%m-%d %H:%M:%S"

        try:
            # 尝试将输入转换为datetime对象
            start_dt = datetime.datetime.strptime(start_str, time_format)
            end_dt = datetime.datetime.strptime(end_str, time_format)

            # 获取记录的开始时间
            meas_date = self.raw_processed.info['meas_date'].replace(tzinfo=None)

            # 计算时间差，以获得相对于记录开始的秒数
            start_seconds = (start_dt - meas_date).total_seconds()
            end_seconds = (end_dt - meas_date).total_seconds()
            seconds = self.raw_processed.n_times / self.raw_processed.info['sfreq']

            # print(f"seconds:{seconds}")
            # print(f"self.raw_processed.n_times:{self.raw_processed.n_times}")
            # print(f"self.raw_processed.info['sfreq']:{self.raw_processed.info['sfreq']}")

            # 检查时间是否有效
            if start_seconds < 0 or end_seconds > seconds:
                QMessageBox.warning(self.window, "Time Range Error",
                                    "The specified time range is out of the recorded data bounds.")

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

            # # print(type(self.raw_processed))
            # #
            # # # 遍历一下数据内容
            # data_array = self.raw_processed.get_data()
            # channel_types = self.raw_processed.get_channel_types()  # 获取全部通道类型
            #
            # for ch_idx in range(data_array.shape[0]):
            #     channel_data = data_array[ch_idx]
            #     ch_name = self.raw_processed.ch_names[ch_idx]
            #     channel_type = channel_types[ch_idx]
            #
            #     print(f"\n通道 {ch_name}:{channel_type}")
            #     print(f"  数据长度: {len(channel_data)}")
            #     print(f"  均值: {np.mean(channel_data):.4f}")
            #     print(f"  标准差: {np.std(channel_data):.4f}")
            #     print(f"  最小值: {np.min(channel_data):.4f}")
            #     print(f"  最大值: {np.max(channel_data):.4f}")

        except ValueError as e:
            QLLogging.log.exception(f"ValueError occurred: {e}")
            QMessageBox.warning(self.window, "Format Error", "The time should be in the format: YYYY-MM-DD HH:MM:SS.")

    def get_total_time_number(self):
        # 计算出总时间
        from datetime import datetime
        start_data_part, start_time_part, end_data_part, end_time_part = self.get_start_end_time_bottom_left_widget()

        start_time = start_data_part + " " + start_time_part
        end_time = end_data_part + " " + end_time_part

        # 将字符串转换为datetime对象
        date_time_obj1 = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        date_time_obj2 = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        # 再将这个相对时间填充到label中，最后要进行更新开始时间

        # 计算时间差值
        time_diff = date_time_obj2 - date_time_obj1
        return time_diff

    def get_new_page_number(self):
        try:
            # 计算出总页数
            # 计算时间差值
            time_diff = self.get_total_time_number()
            # 计算出每一页的时间长度
            new_page_number = int(time_diff.total_seconds() / (self.epoch_length * self.get_n_epochs_display()))

        except ValueError as e:
            QLLogging.log.exception(f"get_new_page_number error: {e}")

        return new_page_number

    def onProgressChanged(self, value):
        """
        当进度条的值发生变化时调用此函数。
        根据进度条的值决定按钮是否可用。
        """
        if value < self.progressBar.maximum():
            self.pushButton_analyse.setEnabled(False)
            self.pushButton_save_pic.setEnabled(False)
            self.pushButton_save_data.setEnabled(False)

    def updateGifPosition(self):
        try:
            """ 根据进度条的值调整 GIF 的位置 """
            progress_value = self.progressBar.value()
            gif_width = self.label_gif.width()
            bar_width = self.progressBar.width()

            # 计算新的X坐标
            new_x = (progress_value / self.progressBar.maximum()) * (bar_width - gif_width) + 434

            # 设置新的位置
            # self.label_gif.move(int(new_x) + 500, self.label_gif.y())

            self.container.setFixedSize(self.progressBar_widget.width(), self.progressBar_widget.height())

            # 设置目标控件在容器中的绝对位置
            self.label_gif.setGeometry(int(new_x), self.label_gif.y(),
                                       self.label_gif.width(), self.label_gif.height())

            # 刷新 GUI
            QApplication.processEvents()
        except ValueError as e:
            print(f"e:{e}")
            QLLogging.log.exception(f"updateGifPosition, error: {e}")

    def open_save_picture_ui(self):
        from .SavePicCPM import SavePictureDialog
        from datetime import datetime
        # 获取当前日期和时间
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d%H%M%S")
        save_pic_dialog = SavePictureDialog(self)
        if save_pic_dialog.exec_() == QDialog.Accepted:
            try:
                # 获取到要保存的路径，dpi和图片格式
                params = save_pic_dialog.get_save_parameters()
                # print(params)
                save_dir = params['path'] + f"/SleepAnalysis{formatted_time}" + params['format']
                img_format = params['format'].lower().replace('.', '')
                dpi = params['resolution']

                print(save_dir)

                # 弹出“请等待”消息框
                wait_box = QMessageBox(QMessageBox.Information, "请稍等", "图片正在保存中，请勿关闭窗口...", parent=self)
                wait_box.show()

                # 刷新 GUI
                QApplication.processEvents()

                import time
                time.sleep(0.2)  # 小延时以确保渲染完成

                self.figure.savefig(save_dir,
                    dpi=dpi,
                    format=img_format,
                    bbox_inches='tight',   # 重要：防止裁剪
                    pad_inches=0.1         # 可选：增加边缘空间
                )

                # 保存 plot_widget 图片
                self.save_plot_widget(self.plot_eeg, params['path'], f"SleepAnalysis_eeg{formatted_time}" + params['format'], dpi)
                self.save_plot_widget(self.plot_emg, params['path'], f"SleepAnalysis_emg{formatted_time}" + params['format'], dpi)
                self.save_plot_widget(self.plot_acc, params['path'], f"SleepAnalysis_acc{formatted_time}" + params['format'], dpi)
                self.save_plot_widget(self.plot_widget, params['path'], f"SleepAnalysis_widget{formatted_time}" + params['format'], dpi)

                # 关闭提示框
                wait_box.close()

                # 提示用户保存成功
                # QMessageBox.information(self, "保存成功", "图片已成功保存。")

            except ValueError as e:
                print(f"open_save_picture_ui, error: {e}")
                QLLogging.log.exception(f"open_save_picture_ui, error: {e}")

    def open_save_data_ui(self):
        from .SavePicCPM import SaveDataDialog
        from .utils import pretreatment_df_score
        from datetime import datetime
        # 获取当前日期和时间
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d%H%M%S")
        combined_data = pretreatment_df_score(self.thread_run, self.df_score)
        save_data_dialog = SaveDataDialog(self)
        save_data_dialog.combobox_data_format.addItem(".mat")
        if save_data_dialog.exec_() == QDialog.Accepted:
            try:
                # 获取保存的参数
                params = save_data_dialog.get_save_parameters()
                print(params)
                save_dir = params['path']
                img_format = params['format'].lower().replace('.', '')

                # 弹出“请等待”消息框
                wait_box = QMessageBox(QMessageBox.Information, "请稍等", "数据正在保存中，请勿关闭窗口...", parent=self)
                wait_box.show()

                # 刷新 GUI
                QApplication.processEvents()

                if img_format == "csv":
                    file_path = os.path.join(save_dir, f"sleep_data{formatted_time}.csv")  # 拼接目录和文件名
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

                    QLLogging.log.info(f"save sleep_data.csv success")

                elif img_format == 'mat':
                    # 这里需要进行检测，还是有点问题
                    from scipy.io import savemat
                    file_path = os.path.join(save_dir, f"sleep_data{formatted_time}.mat")  # 拼接目录和文件名
                    combined_dict = combined_data.to_dict("list")
                    # 保存为MAT文件，'data'是MAT文件中存储数据的变量名
                    savemat(file_path, {'data': combined_dict})

                    QLLogging.log.info(f"save sleep_data.mat success")

                elif img_format == 'npy':
                    file_path = os.path.join(save_dir, f"sleep_data{formatted_time}.npy")  # 拼接目录和文件名
                    # 假设 df 是你想要保存的 DataFrame
                    df = pd.DataFrame(combined_data)
                    # 将 DataFrame 转换成 NumPy 数组
                    numpy_data = df.to_numpy()
                    # 使用 numpy.save 保存数组到 .npy 文件
                    np.save(file_path, numpy_data)  # 注意文件路径最好是 '.npy' 结尾以便识别

                    QLLogging.log.info(f"save sleep_data.npy success")

                # 关闭提示框
                wait_box.close()
                # 提示用户保存成功
                # QMessageBox.information(self, "保存成功", "数据已成功保存。")

            except Exception as e:
                print(e)
                QLLogging.log.exception(f"save_data, error: {e}")

    def save_analysis_state(self, save_path):
        """保存分析状态到文件

        Args:
            save_path: 保存文件的路径

        Returns:
            bool: 保存是否成功
        """
        # 准备要保存的数据
        save_data = {
            # 'raw_processed': self.raw_processed,
            'df_score': self.df_score,
            'emg_channel': self.thread_run.emg_channel , # 添加EMG通道属性
            'acc_channel': self.thread_run.acc_channel ,
            'eeg_channel': self.thread_run.eeg_channel ,
            'eeg_data': self.thread_run.eeg_data,
            'acc_data': self.thread_run.acc_data,
            'emg_data': self.thread_run.emg_data,
            'spectrogram_data': self.thread_run.spectrogram_data,
            # 'thread_run': self.thread_run,
            # 'current_selected_epoch': self.current_selected_epoch,
            # 'current_selected_epochs': self.current_selected_epochs,
            # 'shift_begin': self.shift_begin,
            'n_epochs': self.n_epochs,
            # 'epochlabels': self.epochlabels,
            'epoch_length': self.epoch_length,
            # 'epoch_start': self.epoch_start,
            # 'model_name': self.model_name,
            # 'edf_path': self.edf_path,
            # 'sleep_score_wh': self.sleep_score_wh,
            # 'sleep_redo_score_wh': self.sleep_redo_score_wh,
            # 'current_page': self.current_page,
            # '_ignore_combobox_change': self._ignore_combobox_change
        }
        # 使用pickle保存数据
        with open(save_path, 'wb') as f:
            pickle.dump(save_data, f, protocol=pickle.HIGHEST_PROTOCOL)

        QLLogging.log.info(f"Analysis state saved to: {save_path}")
        return True

        # try:
        #     # 准备要保存的数据
        #     save_data = {
        #         # 'raw_processed': self.raw_processed,
        #         'df_score': self.df_score,
        #         'thread_run': self.thread_run,
        #         # 'current_selected_epoch': self.current_selected_epoch,
        #         # 'current_selected_epochs': self.current_selected_epochs,
        #         # 'shift_begin': self.shift_begin,
        #         # 'n_epochs': self.n_epochs,
        #         # 'epochlabels': self.epochlabels,
        #         # 'epoch_length': self.epoch_length,
        #         # 'epoch_start': self.epoch_start,
        #         # 'model_name': self.model_name,
        #         # 'edf_path': self.edf_path,
        #         # 'sleep_score_wh': self.sleep_score_wh,
        #         # 'sleep_redo_score_wh': self.sleep_redo_score_wh,
        #         # 'current_page': self.current_page,
        #         # '_ignore_combobox_change': self._ignore_combobox_change
        #     }
        #
        #     # 使用pickle保存数据
        #     with open(save_path, 'wb') as f:
        #         pickle.dump(save_data, f, protocol=pickle.HIGHEST_PROTOCOL)
        #
        #     QLLogging.log.info(f"Analysis state saved to: {save_path}")
        #     return True
        #
        # except Exception as e:
        #     QLLogging.log.error(f"Error saving analysis state: {str(e)}")
        #     return False

    def load_analysis_state(self, load_path):
        """从文件加载分析状态到当前对象

        Args:
            load_path: 保存文件的路径

        Returns:
            bool: 加载是否成功
        """
        try:
            # 加载保存的数据
            with open(load_path, 'rb') as f:
                save_data = pickle.load(f)
            print("save_data")
            print(save_data)
            # 恢复所有保存的属性
            # self.raw_processed = save_data['raw_processed']
            self.df_score = save_data['df_score']
            # self.thread_run = save_data['thread_run']
            self.thread_run.emg_channel =  save_data['emg_channel']
            self.thread_run.acc_channel =  save_data['acc_channel']
            self.thread_run.eeg_channel =  save_data['eeg_channel']
            self.thread_run.emg_data = save_data['emg_data']
            self.thread_run.acc_data = save_data['acc_data']
            self.thread_run.eeg_data = save_data['eeg_data']
            self.thread_run.spectrogram_data = save_data['spectrogram_data']
            # self.current_selected_epoch = save_data['current_selected_epoch']
            # self.current_selected_epochs = save_data['current_selected_epochs']
            # self.shift_begin = save_data['shift_begin']
            self.n_epochs = save_data['n_epochs']
            # self.epochlabels = save_data['epochlabels']
            self.epoch_length = save_data['epoch_length']
            # self.epoch_start = save_data['epoch_start']
            # self.model_name = save_data['model_name']
            # self.edf_path = save_data['edf_path']
            # self.sleep_score_wh = save_data['sleep_score_wh']
            # self.sleep_redo_score_wh = save_data['sleep_redo_score_wh']
            # self.current_page = save_data['current_page']
            # self._ignore_combobox_change = save_data['_ignore_combobox_change']

            # 初始化其他不需要保存的属性
            self.highlight_lines = []

            QLLogging.log.info(f"Analysis state loaded from: {load_path}")
            # return True

        except Exception as e:
            QLLogging.log.error(f"Error loading analysis state: {str(e)}")
            return False

        # 将首页页面隐藏，将进度条页面隐藏出来
        self.icon_with_text_widget.hide()
        self.progressBar_widget.hide()
        # 将显示图像页面显示
        self.scrollarea_canvas.show()
        self.bottom_right_top_widget.show()
        self.widget_time_slider.show()
        # 重新绘制图形界面
        self.plot_results()
        self.enable_navigation_controls()

    def calculate_file_hash(self, file_path):
        """计算文件的MD5哈希值"""
        try:
            md5_hash = hashlib.md5()
            with open(file_path, "rb") as f:
                # 分块读取大文件
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except Exception as e:
            QLLogging.log.error(f"Error calculating file hash: {str(e)}")
            return None

    def get_cache_path(self, file_hash):
        """获取缓存文件路径"""
        try:
            cache_dir = os.path.join(os.path.expanduser("~"), ".QLanalyser", "cache")
            os.makedirs(cache_dir, exist_ok=True)
            return os.path.join(cache_dir, f"{file_hash}.cache")
        except Exception as e:
            QLLogging.log.error(f"Error getting cache path: {str(e)}")
            return None

    def load_cache_by_hash(self, file_hash):
        """根据哈希值加载缓存文件"""
        try:
            cache_path = self.get_cache_path(file_hash)
            if not cache_path or not os.path.exists(cache_path):
                return None

            return cache_path

        except Exception as e:
            QLLogging.log.error(f"Error loading cache: {str(e)}")
            return None

    def set_cached_results(self,cached_results):
        self.cached_results = cached_results
        self.pushButton_load_history.setEnabled(True)
        self.pushButton_load_history.blockSignals(False)

    def save_cache(self,file_hash):
        """保存分析结果到缓存"""
        try:
            if not file_hash:
                return False

            cache_path = self.get_cache_path(file_hash)
            if not cache_path:
                return False

            # 保存分析结果
            return self.save_analysis_state(cache_path)

        except Exception as e:
            QLLogging.log.error(f"Error saving cache: {str(e)}")
            return False

    def clean_cache(self, max_size_mb=2000, max_age_days=30):
        """清理缓存目录

        Args:
            max_size_mb: 缓存目录最大容量(MB)
            max_age_days: 缓存文件最大保留天数

        Returns:
            tuple: (清理的文件数, 释放的空间大小(MB))
        """
        try:
            # 获取缓存目录
            cache_dir = os.path.join(os.path.expanduser("~"), ".QLanalyser", "cache")
            if not os.path.exists(cache_dir):
                return 0, 0

            files_removed = 0
            space_freed = 0
            current_time = time.time()

            # 收集所有缓存文件信息
            cache_files = []
            for filename in os.listdir(cache_dir):
                file_path = os.path.join(cache_dir, filename)
                try:
                    stats = os.stat(file_path)
                    # 收集文件信息:(路径,大小,访问时间)
                    cache_files.append((
                        file_path,
                        stats.st_size / (1024 * 1024),  # 转换为MB
                        stats.st_atime  # 最后访问时间
                    ))
                except OSError:
                    continue

            # 按访问时间排序,最旧的在前
            cache_files.sort(key=lambda x: x[2])

            # 计算当前缓存总大小
            total_size = sum(size for _, size, _ in cache_files)

            # 遍历缓存文件
            for file_path, size, atime in cache_files:
                should_remove = False

                # 检查是否过期
                age_in_days = (current_time - atime) / (24 * 3600)
                if age_in_days > max_age_days:
                    should_remove = True

                # 检查是否超出总大小限制
                if total_size > max_size_mb:
                    should_remove = True
                    total_size -= size

                # 删除文件
                if should_remove:
                    try:
                        os.remove(file_path)
                        files_removed += 1
                        space_freed += size
                    except OSError as e:
                        QLLogging.log.error(f"Error removing cache file {file_path}: {str(e)}")
                        continue

            QLLogging.log.info(
                f"Cache cleanup complete: removed {files_removed} files, "
                f"freed {space_freed:.2f}MB"
            )
            return files_removed, space_freed

        except Exception as e:
            QLLogging.log.error(f"Error cleaning cache: {str(e)}")
            return 0, 0

    def save_plot_widget(self, plot_widget, save_dir, filename, dpi):
        # 导出 PyQtGraph 图像
        try:
            result_path = os.path.join(save_dir, filename)
            exporter = ImageExporter(plot_widget.plotItem)
            exporter.parameters()['width'] = int(plot_widget.width() * dpi / 100)
            exporter.parameters()['height'] = int(plot_widget.height() * dpi / 100)
            exporter.export(result_path)
        except ValueError as e:
            print(f"open_save_picture_ui, error: {e}")
            QLLogging.log.exception(f"open_save_picture_ui, error: {e}")