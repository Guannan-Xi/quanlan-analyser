from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QProgressBar, QApplication,
    QLineEdit, QInputDialog, QComboBox, QSpacerItem, QSizePolicy, QMessageBox, QListView, QToolButton,
    QMenu, QAction, QTextEdit
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QDateTime, QCoreApplication
from PyQt5.QtGui import QPixmap
from .Infrastructure.log.QLLogging import QLLogging
from .Control_Style import ControlStyle
import datetime
import re
import os.path
import warnings
warnings.filterwarnings("ignore")
import AR_neurokit2 as nk

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import signal
import os
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class Ui_Recommended(object):

    def setupUi(self, Recommended):
        Recommended.setObjectName("Recommanded")
        Recommended.resize(750, 350)
        Recommended.setFixedHeight(250)
        Recommended.setFixedWidth(650)
        # 设置一下背景颜色
        Recommended.setStyleSheet(ControlStyle.get_widget_style())

        # 设置整体水平布局
        self.ui_recommended_hlayout = QHBoxLayout(Recommended)
        self.ui_recommended_hlayout.setObjectName("ui_recommended_vlayout")
        self.ui_recommended_hlayout.setContentsMargins(32, 32, 32, 65)
        self.ui_recommended_hlayout.setSpacing(0)

        # 使用文本编辑框
        self.textEdit = QTextEdit(Recommended)
        self.textEdit.setObjectName("textEdit")
        self.textEdit.setMinimumSize(550, 350)  # 增加高度
        # 禁用垂直和水平滚动条
        self.textEdit.setVerticalScrollBarPolicy(3)  # ScrollBarAlwaysOff
        self.textEdit.setHorizontalScrollBarPolicy(3)  # ScrollBarAlwaysOff
        # 禁止编辑
        self.textEdit.setReadOnly(True)

        # 使用标签存储图片
        self.label_image = QLabel(Recommended)
        self.label_image.setObjectName("label_image")
        self.label_image.setMinimumSize(100, 100)

        pixmap = QPixmap("./resource/picture/recommanded.png")

        if pixmap.isNull():
            QLLogging.log.info("图片加载失败，请检查路径")
        else:
            scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio)
            self.label_image.setPixmap(scaled_pixmap)

        self.ui_recommended_hlayout.addWidget(self.textEdit, alignment=Qt.AlignLeft)
        self.ui_recommended_hlayout.addWidget(self.label_image, alignment=Qt.AlignRight)

        self.retranslateUi(Recommended)

    def retranslateUi(self, Recommended):
        _translate = QCoreApplication.translate
        Recommended.setWindowTitle(_translate("Recommended", "Recommended Configuration"))

        # 定义要显示的文本
        # lines = [
        #     "操作系统： Windows10 及以上",
        #     "CPU：4.9GHz 8 核以上处理器，i7 处理器及以上",
        #     "内存：≥32g",
        #     "分辨率：1920 x 1080"
        # ]
        lines = [
            "Operating System: Windows 10 or later",
            "CPU: 4.9GHz 8-core or higher (Intel Core i7 or above)",
            "Resolution: 1920 x 1080",
            "Memory: Sampling rate 500Hz",
            "recording time (0~12h)：32G; recording time (12~24h)：64G"
        ]

        html_text = ""
        for line in lines:
            # 找到冒号的位置
            colon_index = line.find(": ")
            if colon_index != -1:
                # 将冒号及之前的文字加粗
                bold_part = line[:colon_index + 1]
                normal_part = line[colon_index + 1:]

                # 处理时间范围和内存大小，将它们变为蓝色
                normal_part = re.sub(
                    r'(\d+~\d+h)|(32G|64G)',
                    r'<span style="color:#2A87DB">\g<0></span>',
                    normal_part
                )
                # 对于 "Memory" 行，使用 <span> 而不是 <p>，并移除自动换行
                if "recording" in line:
                    html_text += f"<span><b>{bold_part}</b>{normal_part}</span>"
                else:
                    html_text += f"<p><b>{bold_part}</b>{normal_part}</p>"
            else:
                # 没有冒号的行直接添加，并处理时间范围和内存大小
                line = re.sub(r'(\d+~\d+h)|(\d+G)', r'<span style="color:#2A87DB">\g<0></span>', line)
                html_text += f"<p>{line}</p>"

        self.textEdit.setHtml(html_text)
        ControlStyle.get_font_size(self.textEdit, 10)

