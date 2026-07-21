import base64
import io
import json
import math
import re
import shutil
from pathlib import Path
from PyQt5 import QtCore, QtWidgets
from pyedflib import EdfReader

from .Analyze_report_pro import prepare_psd_topography_data
from .Clience import Licence

# # 使用 PyMuPDF 处理 PDF（避免与其他 fitz 包冲突）
# try:
#     import pymupdf as fitz  # PyMuPDF 新版本的导入方式
# except ImportError:
#     try:
#         import fitz  # PyMuPDF 旧版本的导入方式
#     except ImportError:
#         raise ImportError(
#             "PyMuPDF (pymupdf) 未安装。请运行: pip install pymupdf\n"
#             "注意：如果安装了其他名为 'fitz' 的包，请先卸载它: pip uninstall fitz"
#         )
from PIL import Image
from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget, QPushButton, QListWidget,
                             QProgressBar, QLabel, QComboBox, QPlainTextEdit, QSizePolicy,
                             QGridLayout, QCheckBox, QLineEdit, QFileDialog, QInputDialog,
                             QHBoxLayout, QVBoxLayout, QSlider, QFrame, QSpacerItem, QMenuBar,
                             QApplication, QComboBox, QWidget, QVBoxLayout, QListView, QShortcut,
                             QMenu, QToolButton, QAction, QScrollArea, QDialog, QTimeEdit, QProgressDialog,
                             QFormLayout, QTableWidget, QAbstractItemView, QTableWidgetItem, QStackedWidget,
                             QDialogButtonBox, QButtonGroup, QRadioButton, QHeaderView, QStyledItemDelegate,
                             QStyleOptionHeader, QTextEdit, )
from PyQt5.QtCore import (QThread, pyqtSignal, pyqtSlot, QRect, Qt, QTime, QDateTime,
                          QCoreApplication, QMetaObject, QThreadPool, QSize,
                          QPropertyAnimation, QRect, pyqtProperty, QSettings, QEvent, QTimer, QRegExp, QLocale)
from PyQt5.QtGui import QIcon, QFont, QPixmap, QKeySequence, QMovie, QImage, QPainter, QRegExpValidator, QMouseEvent, \
    QCursor, QDoubleValidator, QIntValidator, QColor, QValidator
from PyQt5.QtWidgets import QStyle, QStyleOptionSlider, QGraphicsDropShadowEffect, QMessageBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
import hashlib

from .Domain.OPLog.HistoryTask import HistoryTask
from .Domain.OPLog.Subject import Subject
from .Domain.OPLog.Task import Task
from .Domain.OPLog.TaskTemplate import TaskTemplate
from .Domain.OPLog.Template import Template
from .SavePicCPM import SavePictureDialog
from .Infrastructure.log.QLLogging import QLLogging
from .Domain.HistoricalWarehouse import SleepScoreWH
# from .CustomControls import IconWithTextWidget
from .Control_Style import ControlStyle
from .CustomControls import TimeSliderWidget, BottomLeftWidget, CollapsibleSidebar, LoadingOverlay
from .Infrastructure.QLWidgets.QLGifProgressBar import GifProgressBar
from datetime import timedelta
from .Domain.OPLog.OPLog import OPLog, OPType
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
import threading
import scipy.signal
from scipy.signal import stft
from contextlib import redirect_stdout
from .Qlass.my_functions import *
from .MatplotEventHandler import MatplotlibEventHandler_
from .task_Analysis import task_Analysis
from .utils import SaveUtils, get_image_format, setup_short_cut, _highlight_current_amplitude, probe_pg
from mne.filter import resample
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, List, Tuple
from joblib import Parallel, delayed
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
# 强制切换为无GUI的Agg后端（必须在import pyplot之前执行）
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .Infrastructure.DB.SQLLiteAccessor import SQLLiteDB_Only_MainTread, SQLLiteAccessor
from .left_time_overlay import LeftTimeOverlay
from PyQt5.QtGui import QPixmapCache

QPixmapCache.setCacheLimit(50 * 1024)

image_path = None

if not QApplication.instance():  # 关键判断：如果还没有QApplication实例，就创建
    app = QApplication(sys.argv)
else:  # 如果已经有了，就复用已有实例（保证全局唯一，不报错）
    app = QApplication.instance()

# 全局字体配置（适配学术绘图）
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial']
plt.rcParams['text.color'] = 'black'  # 通用文本颜色
plt.rcParams['axes.labelcolor'] = 'black'  # 坐标轴标签颜色
plt.rcParams['xtick.color'] = 'black'  # X轴刻度线+刻度文字颜色
plt.rcParams['ytick.color'] = 'black'  # Y轴刻度线+刻度文字颜色


def emit_and_schedule(signal, current_progress, remaining_times, progressBar):
    try:
        steps = max(int(remaining_times), 0)
        # 打包后环境下，严格控制进度条更新频率
        if getattr(sys, "frozen", False):
            # 只有当进度真的有显著变化时才 emit
            target_p = min(int(current_progress) + steps, 99)
            signal.emit([target_p, "处理中..."])
            return
        # 开发环境下保持平滑
        for i in range(steps):
            p = int(current_progress) + i
            if p >= 100:
                break
            signal.emit([p, ""])
            # 使用更科学的等待或交给 Qt 事件循环
            QCoreApplication.processEvents()
            time.sleep(0.01)
    except Exception:
        pass


class DoubleRangeValidator(QDoubleValidator):
    """自定义双精度数值验证器，严格限制数值范围"""

    def validate(self, input_str: str, pos: int):
        # 调用父类方法做基础验证（小数点位数、格式等）
        state, input_str, pos = super().validate(input_str, pos)

        # 空输入：允许继续输入（中间状态）
        if input_str.strip() == "":
            return (QValidator.Intermediate, input_str, pos)

        # 仅在格式非法时返回 Invalid；范围检查交给业务逻辑处理
        # super().validate 已经保证格式正确，这里不再因为超出范围而直接 Invalid
        return (state, input_str, pos)


class SearchInputValidator(QValidator):
    """
    受试者列表检索框验证器：
    - 仅允许汉字、英文字母、数字
    - 自动过滤特殊字符
    - 自动去除首尾空格
    - 限制输入长度不超过 50 个字符
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    def validate(self, input_str: str, pos: int):
        if input_str is None:
            return (QValidator.Intermediate, "", pos)

        # 去除首尾空格（只作用于输入框本身）
        trimmed = input_str.strip()

        # 过滤非法字符：只保留汉字、英文字母、数字
        filtered_chars = []
        for ch in trimmed:
            if ch.isalnum() or ("\u4e00" <= ch <= "\u9fff"):
                filtered_chars.append(ch)
        filtered = "".join(filtered_chars)

        # 长度限制：最多 50 个字符
        if len(filtered) > 50:
            filtered = filtered[:50]

        # 空字符串：允许继续输入
        if filtered == "":
            return (QValidator.Intermediate, filtered, 0)

        # 所有字符都合法且长度合理
        return (QValidator.Acceptable, filtered, min(pos, len(filtered)))


# 新建或者修改受试者弹窗
class AddSubjectDialog(QDialog):
    submit_signal = pyqtSignal(dict)  # 提交信号，传递用户数据

    def __init__(self, parent=None, subject=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.subject = subject
        self.setWindowTitle("受试者档案录入")
        self.setModal(True)
        self.setStyleSheet("""
                    QDialog {
                       width: 647px;
                       height: 562px;
                       """ + ControlStyle.get_background_border("#FFFFFF", "8") + """
                    }
                """)
        # self.setFixedSize(800, 400)
        self.initUI()

    def initUI(self):
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 8, 8, 8)
        title_bar.setSpacing(0)

        # 标题文本
        title_label = QLabel("受试者档案录入")
        title_label.setFont(QFont("微软雅黑", 12))
        title_bar.addWidget(title_label)

        # 拉伸空间（让标题居左、关闭按钮居右）
        title_bar.addStretch()

        main_layout.addLayout(title_bar)

        column_layout = QHBoxLayout()
        column_layout.setSpacing(12)

        # 表单布局
        form_layout_1 = QFormLayout()
        form_layout_1.setSpacing(10)

        form_layout_2 = QFormLayout()
        form_layout_2.setSpacing(10)

        # 编号
        id_label = QLabel("ID<font color='red'>*</font>")
        self.id_edit = QLineEdit()
        self.id_edit.setStyleSheet(ControlStyle.get_addSubjwct_lineEdit())
        self.id_edit.setMaxLength(10)
        self.id_edit.setPlaceholderText("请输入ID（仅限字母和数字，最多10位）")
        # 限制：仅字母+数字，禁止中文等其他字符
        id_validator = QRegExpValidator(QRegExp("^[A-Za-z0-9]+$"), self)
        self.id_edit.setValidator(id_validator)
        if self.subject:
            self.id_edit.setText(self.subject.id)
            self.id_edit.setReadOnly(True)
        self.id_edit.textChanged.connect(self._on_id_text_changed)
        form_layout_2.addRow(id_label)
        form_layout_2.addRow(self.id_edit)

        # 姓名
        name_label = QLabel("姓名<font color='red'>*</font>")
        self.name_edit = QLineEdit()
        self.name_edit.setStyleSheet(ControlStyle.get_addSubjwct_lineEdit())
        # 限制长度：2-20 个字符（具体长度在提交和实时校验中检查）
        self.name_edit.setMaxLength(20)
        if self.subject:
            self.name_edit.setText(self.subject.name)
        self.name_edit.textChanged.connect(self._on_name_text_changed)
        form_layout_1.addRow(name_label)
        form_layout_1.addRow(self.name_edit)

        # 年龄
        age_label = QLabel("年龄<font color='red'>*</font>")
        self.age_edit = QLineEdit()
        self.age_edit.setStyleSheet(ControlStyle.get_addSubjwct_lineEdit())
        if self.subject:
            self.age_edit.setText(str(self.subject.age))
        # 修复：添加数字验证器，限制只能输入数字
        self.age_edit.setValidator(QIntValidator(0, 150))
        self.age_edit.textChanged.connect(self._on_age_text_changed)
        form_layout_1.addRow(age_label)
        form_layout_1.addRow(self.age_edit)

        # 身高(cm)
        height_label = QLabel("身高(cm)<font color='red'>*</font>")
        self.height_edit = QLineEdit()
        self.height_edit.setStyleSheet(ControlStyle.get_addSubjwct_lineEdit())
        if self.subject:
            self.height_edit.setText(str(self.subject.height))
        # 替换原有验证器：范围 30.0-250.0，保留 1 位小数
        height_validator = DoubleRangeValidator(30.0, 250.0, 1)
        height_validator.setNotation(QDoubleValidator.StandardNotation)  # 禁用科学计数法
        height_validator.setLocale(QLocale(QLocale.C))  # 确保小数点是.（而非,）
        self.height_edit.setValidator(height_validator)
        self.height_edit.textChanged.connect(self._on_height_text_changed)
        form_layout_1.addRow(height_label)
        form_layout_1.addRow(self.height_edit)

        # 性别
        # 单选按钮组（确保只能选一个）
        gender_label = QLabel("性别<font color='red'>*</font>")
        self.gender_group = QHBoxLayout()
        radio_style = ControlStyle.get_radio_style()
        self.male_radio = QRadioButton("男 ♂")
        self.female_radio = QRadioButton("女 ♀")
        self.other_radio = QRadioButton("不便透露")
        self.gender_group.addWidget(self.male_radio)
        self.gender_group.addWidget(self.female_radio)
        self.gender_group.addWidget(self.other_radio)
        self.male_radio.setStyleSheet(radio_style)
        self.female_radio.setStyleSheet(radio_style)
        self.other_radio.setStyleSheet(radio_style)
        # 默认选中“男”（匹配截图）
        if self.subject:
            self.male_radio.setChecked(self.subject.gender == "男")
            self.female_radio.setChecked(self.subject.gender == "女")
            # 其他情况视为“不便透露”
            if self.subject.gender not in ("男", "女") and self.subject.gender:
                self.other_radio.setChecked(True)
        else:
            self.male_radio.setChecked(True)
        form_layout_1.addRow(gender_label)
        form_layout_1.addRow(self.gender_group)

        # 体重(kg)
        weight_label = QLabel("体重(kg)<font color='red'>*</font>")
        self.weight_edit = QLineEdit()
        self.weight_edit.setStyleSheet(ControlStyle.get_addSubjwct_lineEdit())
        if self.subject:
            self.weight_edit.setText(str(self.subject.weight))
        # 替换原有验证器：范围 2.0-300.0，保留 1 位小数
        weight_validator = DoubleRangeValidator(2.0, 300.0, 1)
        weight_validator.setNotation(QDoubleValidator.StandardNotation)
        weight_validator.setLocale(QLocale(QLocale.C))
        self.weight_edit.setValidator(weight_validator)
        self.weight_edit.textChanged.connect(self._on_weight_text_changed)
        form_layout_2.addRow(weight_label)
        form_layout_2.addRow(self.weight_edit)

        # BMI（只读）
        bmi_label = QLabel("BMI<font color='red'></font>")
        self.bmi_edit = QLineEdit()
        self.bmi_edit.setStyleSheet(ControlStyle.get_addSubjwct_lineEdit())
        if self.subject:
            self.bmi_edit.setText(str(self.subject.bmi))
        self.bmi_edit.setReadOnly(True)
        form_layout_2.addRow(bmi_label)
        form_layout_2.addRow(self.bmi_edit)

        # 采集人
        analyst_label = QLabel("采集人<font color='red'></font>")
        self.analyst_edit = QLineEdit()
        self.analyst_edit.setStyleSheet(ControlStyle.get_addSubjwct_lineEdit())
        # 采集人：最长 60 个字符，单行
        self.analyst_edit.setMaxLength(60)
        if self.subject:
            self.analyst_edit.setText(self.subject.analyst)
        form_layout_2.addRow(analyst_label)
        form_layout_2.addRow(self.analyst_edit)

        column_layout.addLayout(form_layout_1)
        column_layout.addLayout(form_layout_2)
        main_layout.addLayout(column_layout)

        # 1. 创建备注表单布局，保持和原有表单一致的间距样式
        remark_layout = QVBoxLayout()
        remark_layout.setSpacing(10)
        # 2. 备注标签（无红色*，标识为非必填项）
        remark_label = QLabel("备注<font color='red'></font>")
        # 3. 备注多行输入框，适配长文本输入
        self.remark_edit = QTextEdit()
        # 统一样式：沿用项目的样式规范，设置占位提示文本和滚动条样式
        self.remark_edit.setStyleSheet(ControlStyle.get_addSubjwct_lineEdit() + """
            QScrollBar:vertical {
                border: none;
                background: #F5F5F5;
                width: 5px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #C0C0C0;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: #F5F5F5;
            }
        """)
        self.remark_edit.setPlaceholderText("请输入额外备注信息, 字数上限500（选填）")
        self.remark_edit.setFixedHeight(100)
        # 备注：限制为最多 500 个字符（支持换行）
        self.remark_edit.textChanged.connect(self._on_remark_text_changed)
        # 4. 编辑状态回填数据：如果self.subject存在，自动加载备注内容
        if self.subject and hasattr(self.subject, 'remark'):
            self.remark_edit.setText(self.subject.remark)
        # 5. 将标签和输入框添加到表单行
        remark_layout.addWidget(remark_label)
        remark_layout.addWidget(self.remark_edit)
        # 6. 将备注布局添加到主布局中
        main_layout.addLayout(remark_layout)

        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        # 提交按钮
        if self.subject:
            self.submit_btn = QPushButton("确认修改")
        else:
            self.submit_btn = QPushButton("确认添加")
        self.submit_btn.setStyleSheet("""
            QPushButton {
                height:46px;
                background: #2A87DB;
                border-radius: 5px 5px 5px 5px;
                opacity: 0.5;""" + ControlStyle.get_qeeg_font_500("#FFFFFF", "16", "center") + """
            }
        """)
        self.submit_btn.clicked.connect(self.on_submit)
        btn_layout.addWidget(self.submit_btn)

        main_layout.addLayout(btn_layout)

    def _is_valid_name_chars(self, text: str) -> bool:
        """仅允许中英文、空格和点（·）"""
        for ch in text:
            if ch == ' ' or ch == '·':
                continue
            # 英文
            if 'A' <= ch <= 'Z' or 'a' <= ch <= 'z':
                continue
            # 常用汉字区间
            if '\u4e00' <= ch <= '\u9fff':
                continue
            return False
        return True

    def _set_input_error(self, widget, message: str):
        """输入错误时：输入框边框变红，并设置提示文字"""
        try:
            base = ControlStyle.get_addSubjwct_lineEdit()
            widget.setStyleSheet(base + """ QLineEdit { border: 1px solid #FF4D4F;}""")
            widget.setToolTip(message)
        except Exception:
            pass

    def _clear_input_error(self, widget):
        """清除错误样式"""
        try:
            widget.setStyleSheet(ControlStyle.get_addSubjwct_lineEdit())
            widget.setToolTip("")
        except Exception:
            pass

    def _on_name_text_changed(self, text: str):
        """姓名实时校验：2-20 个字符，仅中英文、空格、·"""
        norm = " ".join(text.strip().split())
        if not norm:
            self._clear_input_error(self.name_edit)
            return
        if len(norm) < 2 or len(norm) > 20 or not self._is_valid_name_chars(norm):
            self._set_input_error(self.name_edit, "姓名需为 2-20 个中英文字符，可含空格和“·”。")
        else:
            self._clear_input_error(self.name_edit)

    def _on_id_text_changed(self, text: str):
        """ID 实时校验：仅字母数字，禁止中文"""
        t = text.strip()
        if not t:
            self._clear_input_error(self.id_edit)
            return
        if not all(ord(c) < 128 and c.isalnum() for c in t):
            self._set_input_error(self.id_edit, "ID 仅支持英文字母和数字，禁止中文等其他字符。")
        else:
            self._clear_input_error(self.id_edit)

    def _on_age_text_changed(self, text: str):
        """年龄实时校验：整数 0-150"""
        t = text.strip()
        if not t:
            self._clear_input_error(self.age_edit)
            return
        try:
            value = int(t)
            if 0 <= value <= 150:
                self._clear_input_error(self.age_edit)
            else:
                self._set_input_error(self.age_edit, "年龄范围应为 0 - 150（岁）。")
        except ValueError:
            self._set_input_error(self.age_edit, "年龄需为整数（0 - 150）。")

    def _on_height_text_changed(self, text: str):
        """身高实时校验：30.0-250.0 cm，1 位小数"""
        t = text.strip()
        if not t:
            self._clear_input_error(self.height_edit)
            self.calculate_bmi()
            return
        try:
            value = float(t)
            if 30.0 <= value <= 250.0:
                self._clear_input_error(self.height_edit)
            else:
                self._set_input_error(self.height_edit, "身高范围应为 30.0 - 250.0 cm。")
        except ValueError:
            self._set_input_error(self.height_edit, "身高请输入数字，范围 30.0 - 250.0 cm。")
        self.calculate_bmi()

    def _on_weight_text_changed(self, text: str):
        """体重实时校验：2.0-300.0 kg，1 位小数"""
        t = text.strip()
        if not t:
            self._clear_input_error(self.weight_edit)
            self.calculate_bmi()
            return
        try:
            value = float(t)
            if 2.0 <= value <= 300.0:
                self._clear_input_error(self.weight_edit)
            else:
                self._set_input_error(self.weight_edit, "体重范围应为 2.0 - 300.0 kg。")
        except ValueError:
            self._set_input_error(self.weight_edit, "体重请输入数字，范围 2.0 - 300.0 kg。")
        self.calculate_bmi()

    def _on_remark_text_changed(self):
        """备注最长 500 个字符，超出时自动截断"""
        text = self.remark_edit.toPlainText()
        if len(text) <= 500:
            return
        cursor = self.remark_edit.textCursor()
        pos = cursor.position()
        text = text[:500]
        self.remark_edit.blockSignals(True)
        self.remark_edit.setPlainText(text)
        # 尽量恢复光标位置
        if pos > 500:
            pos = 500
        cursor.setPosition(pos)
        self.remark_edit.setTextCursor(cursor)
        self.remark_edit.blockSignals(False)

    def calculate_bmi(self):
        """根据身高体重计算BMI"""
        try:
            height_text = self.height_edit.text().strip()
            weight_text = self.weight_edit.text().strip()
            if not height_text or not weight_text:
                self.bmi_edit.setText("")
                return
            height_val = float(height_text)
            weight_val = float(weight_text)
            # 仅在身高、体重都在合法范围时计算 BMI
            if not (30.0 <= height_val <= 250.0 and 2.0 <= weight_val <= 300.0):
                self.bmi_edit.setText("")
                return
            height_m = height_val / 100.0  # 转米
            if height_m <= 0:
                self.bmi_edit.setText("")
                return
            bmi = weight_val / (height_m * height_m)
            # BMI：保留 1 位小数
            self.bmi_edit.setText(f"{bmi:.1f}")
        except ValueError:
            self.bmi_edit.setText("")

    # 基本验证
    def on_submit(self):
        """提交表单（增加必填项验证）"""
        # 1. 姓名：必填 + 2-20 个字符 + 字符集合限制
        raw_name = self.name_edit.text()
        name = " ".join(raw_name.strip().split())
        if not name:
            self._set_input_error(self.name_edit, "姓名不能为空。")
            QMessageBox.warning(self, "警告", "姓名不能为空！")
            return
        if len(name) < 2 or len(name) > 20 or not self._is_valid_name_chars(name):
            self._set_input_error(self.name_edit, "姓名需为 2-20 个中英文字符，可含空格和“·”。")
            QMessageBox.warning(self, "警告", "姓名格式不正确，请检查。")
            return
        self._clear_input_error(self.name_edit)
        self.name_edit.setText(name)

        # 2. ID：必填 + 仅字母数字 + 唯一性
        id_text = self.id_edit.text().strip()
        if not id_text:
            self._set_input_error(self.id_edit, "ID 不能为空。")
            QMessageBox.warning(self, "警告", "ID不能为空！")
            return
        if not all(ord(c) < 128 and c.isalnum() for c in id_text):
            self._set_input_error(self.id_edit, "ID 仅支持英文字母和数字，禁止中文等其他字符。")
            QMessageBox.warning(self, "警告", "ID 格式不正确，请仅使用字母和数字。")
            return
        existing_subject = Subject.get_by_id(SQLLiteDB_Only_MainTread.user_db, id_text)
        if existing_subject and self.subject is None:
            self._set_input_error(self.id_edit, "该 ID 已存在，请使用其他 ID。")
            QMessageBox.warning(self, "错误", f"ID {id_text} 已存在，请使用其他ID！")
            return
        self._clear_input_error(self.id_edit)

        # 3. 年龄：必填 + 0-150，整数
        age_text = self.age_edit.text().strip()
        if not age_text:
            self._set_input_error(self.age_edit, "年龄不能为空。")
            QMessageBox.warning(self, "警告", "年龄不能为空！")
            return
        try:
            age_val = int(age_text)
            if not (0 <= age_val <= 150):
                self._set_input_error(self.age_edit, "年龄范围应为 0 - 150（岁）。")
                QMessageBox.warning(self, "警告", "年龄范围应为 0-150！")
                return
        except ValueError:
            self._set_input_error(self.age_edit, "年龄需为整数（0 - 150）。")
            QMessageBox.warning(self, "警告", "年龄请输入整数！")
            return
        self._clear_input_error(self.age_edit)
        if age_val < 6 or age_val > 12:
            QMessageBox.information(self, "提示", "该受试者的年龄不属于【6 ~12】，分析结果可能存在一定误差。")

        # 4. 身高：必填 + 30.0-250.0 cm
        height_text = self.height_edit.text().strip()
        if not height_text:
            self._set_input_error(self.height_edit, "身高不能为空。")
            QMessageBox.warning(self, "警告", "身高不能为空！")
            return
        try:
            height_val = float(height_text)
            if not (30.0 <= height_val <= 250.0):
                self._set_input_error(self.height_edit, "身高范围应为 30.0 - 250.0 cm。")
                QMessageBox.warning(self, "警告", "身高范围应为 30.0-250.0 cm！")
                return
        except ValueError:
            self._set_input_error(self.height_edit, "身高请输入数字，范围 30.0 - 250.0 cm。")
            QMessageBox.warning(self, "警告", "身高请输入数字！")
            return
        self._clear_input_error(self.height_edit)

        # 5. 体重：必填 + 2.0-300.0 kg
        weight_text = self.weight_edit.text().strip()
        if not weight_text:
            self._set_input_error(self.weight_edit, "体重不能为空。")
            QMessageBox.warning(self, "警告", "体重不能为空！")
            return
        try:
            weight_val = float(weight_text)
            if not (2.0 <= weight_val <= 300.0):
                self._set_input_error(self.weight_edit, "体重范围应为 2.0 - 300.0 kg。")
                QMessageBox.warning(self, "警告", "体重范围应为 2.0-300.0 kg！")
                return
        except ValueError:
            self._set_input_error(self.weight_edit, "体重请输入数字，范围 2.0 - 300.0 kg。")
            QMessageBox.warning(self, "警告", "体重请输入数字！")
            return
        self._clear_input_error(self.weight_edit)

        # 6. BMI：禁止手动输入，由系统根据合法的身高、体重自动计算
        self.calculate_bmi()
        bmi_text = self.bmi_edit.text().strip()
        if not bmi_text:
            # 在身高体重均合法的前提下 BMI 仍为空，视为异常
            self._set_input_error(self.bmi_edit, "请检查身高和体重是否输入正确，以便自动计算 BMI。")
            QMessageBox.warning(self, "警告", "BMI 计算失败，请检查身高和体重输入。")
            return
        self._clear_input_error(self.bmi_edit)

        # 7. 性别：单选（男/女/不便透露）
        if self.male_radio.isChecked():
            gender_value = "男"
        elif self.female_radio.isChecked():
            gender_value = "女"
        else:
            gender_value = "不便透露"

        # 8. 采集人 & 备注：采集人上限 60 字符；备注上限 500 字符（在输入时已截断）
        analyst_text = self.analyst_edit.text().strip()
        remark_text = self.remark_edit.toPlainText().strip()

        # 收集数据（按校验后的值）
        subject_data = {
            "id": id_text,
            "name": name,
            "age": age_val,
            "gender": gender_value,
            "height": height_val,
            "weight": weight_val,
            "bmi": float(bmi_text) if bmi_text else None,
            "analyst": analyst_text or "",
            "create_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "remark": remark_text
        }
        self.submit_signal.emit(subject_data)
        self.accept()


# ========== 设置弹窗（含图片上传功能） ==========
class SettingDialog(QDialog):
    """设置弹窗：支持图片上传、预览、保存路径"""
    # 自定义信号：上传图片成功后传递图片路径
    image_uploaded = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.uploaded_image_path = ""  # 保存上传的图片路径
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Logo Setting")
        self.setModal(True)
        self.setFixedSize(500, 400)  # 弹窗固定尺寸

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # 1. 标题（保持原有样式）
        title_label = QLabel("Logo Setting")
        title_label.setStyleSheet(ControlStyle.get_qeeg_font_500("#31373D", "16"))
        title_label.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(title_label)

        # ========== 2. 改造预览区域：带虚线边框、点击上传、默认显示提示 ==========
        self.preview_widget = QWidget()
        self.preview_widget.setObjectName("logoPreviewBox")
        # 样式：虚线边框（匹配图中效果）+ 圆角
        self.preview_widget.setStyleSheet(ControlStyle.get_logoPreviewBox())
        # 鼠标移到方框上变成“手型”，提示可点击
        self.preview_widget.setCursor(QCursor(Qt.PointingHandCursor))
        # 绑定点击事件（点击方框触发上传）
        self.preview_widget.mousePressEvent = self.on_preview_click

        preview_layout = QVBoxLayout(self.preview_widget)
        preview_layout.setAlignment(Qt.AlignCenter)
        preview_layout.setSpacing(8)  # 提示元素之间的间距
        preview_layout.setContentsMargins(0, 0, 0, 0)

        # ---------- 上传提示元素（默认显示） ----------
        # 云图标（替换为你项目中实际的云图标路径）
        self.cloud_icon = QLabel()
        self.cloud_icon.setPixmap(
            QPixmap("./resource/picture/Frame.png")  # 图中蓝色云图标
            .scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.cloud_icon.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.cloud_icon)

        # “Upload Your Logo”文字
        self.upload_title = QLabel("Upload Your Logo")
        self.upload_title.setStyleSheet(ControlStyle.get_qeeg_font_500("#31373D", "14", "center"))
        self.upload_title.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.upload_title)

        # 格式说明文字
        self.format_label = QLabel("(png/jpg/jpeg/svg)")
        self.format_label.setStyleSheet(ControlStyle.get_qeeg_font_400("#8DA1C1", "14", "center"))
        self.format_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.format_label)

        # ---------- 图片显示区域（上传后显示） ----------
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.hide()  # 初始隐藏

        self.confirmBtn = QPushButton("Confirm")
        self.confirmBtn.setMinimumSize(144, 35)
        self.confirmBtn.setStyleSheet(
            """background: #2A87DB;border-radius: 4px 4px 4px 4px;""" + ControlStyle.get_qeeg_font_500("#FFFFFF",
                                                                                                       "16px",
                                                                                                       "center"))
        self.confirmBtn.hide()
        self.confirmBtn.clicked.connect(self.confirm_upload)

        self.clearBtn = QPushButton("Clear Logo")
        self.clearBtn.setMinimumSize(144, 35)
        self.clearBtn.setStyleSheet(
            """background: #2A87DB;border-radius: 4px 4px 4px 4px;""" + ControlStyle.get_qeeg_font_500("#FFFFFF",
                                                                                                       "16px",
                                                                                                       "center"))
        self.clearBtn.hide()
        self.clearBtn.clicked.connect(self.clear_image)
        preview_layout.addWidget(self.image_label)
        preview_layout.addWidget(self.confirmBtn)
        preview_layout.addWidget(self.clearBtn)

        # 预览区域占弹窗主要空间
        main_layout.addWidget(self.preview_widget, 1)

    def clear_image(self):
        self.uploaded_image_path = ""
        self.image_uploaded.emit("")

        self.cloud_icon.show()
        self.upload_title.show()
        self.format_label.show()
        self.image_label.hide()
        self.confirmBtn.hide()
        self.clearBtn.hide()

        # 加载并缩放图片（适配方框大小）
        self.update_preview_image()

    def on_preview_click(self, event):
        """点击预览方框触发上传"""
        if event.button() == Qt.LeftButton:  # 只响应左键点击
            self.upload_image()

    def confirm_upload(self):
        # 保存logo
        current_dir = os.path.dirname(os.path.abspath(__file__))
        dir = os.path.dirname(os.path.abspath(sys.executable))

        logo_path = os.path.join(current_dir, '..', 'resource', 'user_logo')
        logo_path = os.path.normpath(logo_path)  # 规范化路径，将..解析掉

        if not os.path.exists(logo_path):
            logo_path = os.path.join(dir, 'resource', 'user_logo')

        # 新增：自动创建目标目录（无论路径是否存在，确保文件夹可用）
        os.makedirs(logo_path, exist_ok=True)

        # 新增：校验原始上传文件是否有效
        src_file = self.uploaded_image_path
        if not os.path.isfile(src_file):
            QMessageBox.warning(self, "上传提示", "未选择有效文件，请重新上传！")
            return

        # 新增：生成唯一文件名，防止同名文件覆盖（时间戳+原文件名）
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = os.path.basename(src_file)  # 获取原始文件名
        save_file_name = f"{timestamp}_{file_name}"
        # 拼接最终保存的完整路径
        target_file = os.path.join(logo_path, save_file_name)

        # 新增：文件复制+异常捕获处理
        try:
            # 复制文件到目标目录，copy2保留文件元数据
            shutil.copy2(src_file, target_file)
            # 更新路径为保存后的新路径，再发射信号
            self.uploaded_image_path = target_file
            QMessageBox.information(self, "上传成功", f"logo已保存至：\n{target_file}")
        except PermissionError:
            QMessageBox.critical(self, "上传失败", "无文件夹写入权限，请检查目录权限！")
            return
        except Exception as e:
            QMessageBox.critical(self, "上传失败", f"文件保存异常：{str(e)}")
            return

        # 发射信号 + 关闭对话框
        self.image_uploaded.emit(self.uploaded_image_path)
        self.reject()

    def upload_image(self):
        """图片上传逻辑：选择图片后在方框内显示"""
        # 打开文件选择对话框（限制图片格式）
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Logo图片", "", "图片文件 (*.png *.jpg *.jpeg *.svg)"
        )
        if not file_path:
            return

        # 保存图片路径，发送上传信号
        self.uploaded_image_path = file_path

        # 隐藏“上传提示元素”，显示图片
        self.cloud_icon.hide()
        self.upload_title.hide()
        self.format_label.hide()
        self.image_label.show()
        self.confirmBtn.show()
        self.clearBtn.show()

        # 加载并缩放图片（适配方框大小）
        self.update_preview_image()

    def update_preview_image(self):
        """缩放图片以适配预览方框"""
        if not self.uploaded_image_path:
            return
        pixmap = QPixmap(self.uploaded_image_path)
        # 保持图片比例，缩放到方框内最大显示尺寸
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """弹窗大小变化时，自动适配图片尺寸"""
        super().resizeEvent(event)
        # 若已上传图片，重新缩放适配
        if self.uploaded_image_path and self.image_label.isVisible():
            self.update_preview_image()


# 顶部窗口
class TopWidget(QWidget):
    image_upload_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopWidget")  # ID选择器正确，不用改
        self.setAcceptDrops(True)  # 你的拖拽逻辑，保留

        self.setStyleSheet(ControlStyle.get_topwidget_style())
        self.dialog = SettingDialog(self)

        self.initUI(parent)
        self.image_path = None

    def initUI(self, parent=None):
        # ========== 顶部导航栏 ==========
        self.nav_layout = QHBoxLayout(self)
        self.nav_layout.setObjectName("top_widget_layout")
        self.nav_layout.setContentsMargins(32, 16, 32, 16)
        self.nav_layout.setSpacing(24)

        # Logo和名称
        self.logo_widget = QWidget()
        self.logo_layout = QHBoxLayout(self.logo_widget)
        self.logo_layout.setContentsMargins(0, 0, 0, 0)
        self.logo_layout.setSpacing(8)

        # 模拟Logo（可替换为实际图片路径）
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(46, 46)
        self.logo_label.setPixmap(
            QPixmap("./resource/picture/recommanded.png").scaled(46, 46, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo_label.setStyleSheet("background-color: #FFFFFF; border-radius: 16px;")
        self.logo_layout.addWidget(self.logo_label)

        self.name_label = QLabel()

        self.name_label.setText(
            '<span style="color: #0066CC; font-weight: bold;">QL</span>'
            '<span style="color: #2E3440; font-weight: bold;">analyser</span>'
        )
        ControlStyle.get_font_size(self.name_label, 16)
        self.name_label.setStyleSheet("font-weight: bold;")

        self.logo_layout.addWidget(self.name_label)
        self.nav_layout.addWidget(self.logo_widget)

        version_widget = QWidget()
        version_widget.setFixedSize(65, 38)
        version_layout = QHBoxLayout(version_widget)
        version_widget.setStyleSheet(ControlStyle.get_background_border("#E3EAF8", "8"))
        version_label = QLabel("v1.2.2")
        version_label.setStyleSheet(ControlStyle.get_qeeg_font_400("#8DA1C1", "14", "center"))
        version_label.setAlignment(Qt.AlignCenter)
        version_layout.addWidget(version_label)
        self.nav_layout.addWidget(version_widget)

        left_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.nav_layout.addSpacerItem(left_spacer)

        container_widget = QWidget()
        btn_layout = QHBoxLayout(container_widget)
        btn_layout.setContentsMargins(7, 6, 7, 6)  # 设置内边距
        btn_layout.setSpacing(8)
        # 为容器设置样式
        container_widget.setStyleSheet(ControlStyle.get_background_border_widget("#F3F5F8", "8", "10"))

        self.btn_Subjectdb = QPushButton("受试者数据库")
        self.btn_Subjectdb.setMinimumSize(144, 38)
        self.btn_Subjectdb.setStyleSheet(ControlStyle.get_topWidget_Button_clicked())
        btn_layout.addWidget(self.btn_Subjectdb)

        self.btn_task_config = QPushButton("任务配置")
        self.btn_task_config.setMinimumSize(144, 38)
        self.btn_task_config.setStyleSheet(ControlStyle.get_topWidget_Button())
        self.btn_task_config.setDisabled(True)
        btn_layout.addWidget(self.btn_task_config)

        self.btn_report_generation = QPushButton("报告生成")
        self.btn_report_generation.setMinimumSize(144, 38)
        self.btn_report_generation.setStyleSheet(ControlStyle.get_topWidget_Button())
        self.btn_report_generation.setDisabled(True)
        btn_layout.addWidget(self.btn_report_generation)

        self.nav_layout.addWidget(container_widget)

        self.nav_layout.addStretch()

        currentId_layout = QVBoxLayout()
        currentId_layout.setSpacing(8)
        currentId_label = QLabel("当前ID / Current ID")
        currentId_label.setStyleSheet(ControlStyle.get_qeeg_font_500("#979797", "14", "right"))
        self.currentId_edit = QLabel("None")
        if self.currentId_edit.text() == "None":
            self.currentId_edit.setStyleSheet(ControlStyle.get_qeeg_font_500("#D4D6D9", "14", "right"))
        currentId_layout.addWidget(currentId_label)
        currentId_layout.addWidget(self.currentId_edit)
        self.nav_layout.addLayout(currentId_layout)

        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)  # 改为纵向分割线
        separator.setFrameShadow(QFrame.Plain)
        separator.setStyleSheet("background-color: #a9a9a9;")
        separator.setFixedWidth(1)  # 改为固定宽度（替代原来的固定高度）
        self.nav_layout.addWidget(separator)

        # 右侧设置按钮
        self.settings_btn = QPushButton("Logo 设置\nLogo Setting")
        icon = QIcon("./resource/picture/setting.png")
        self.settings_btn.setIcon(icon)
        self.settings_btn.setIconSize(QSize(32, 32))
        self.settings_btn.setMinimumSize(60, 36)
        self.settings_btn.setStyleSheet(ControlStyle.get_qeeg_font_500("#979797", "14", "right") +
                                        """
                                            QPushButton {
                                                height: 16px;
                                            }
                                        """
                                        )
        self.settings_btn.clicked.connect(self.open_setting_dialog)
        self.nav_layout.addWidget(self.settings_btn)

    def open_setting_dialog(self):
        """打开设置弹窗"""
        self.dialog = SettingDialog(self)
        # 可选：监听图片上传成功信号，做后续处理（比如保存到数据库）
        self.dialog.image_uploaded.connect(self.handle_uploaded_image)
        self.dialog.exec_()

    def handle_uploaded_image(self, image_path):
        """处理上传成功的图片（示例：打印路径，可扩展保存到数据库）"""
        self.image_path = image_path
        print(f"上传的图片路径：{image_path}")
        self.image_upload_signal.emit(self.image_path)


# 分页控件
class PaginationWidget(QWidget):
    page_changed = pyqtSignal(int)  # 页码改变信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = 1
        self.total_pages = 1
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignRight)

        layout.addStretch()

        # 上一页
        self.prev_btn = QPushButton("上一页")
        ControlStyle.get_font_size(self.prev_btn, 12)
        self.prev_btn.setStyleSheet("""
            width: 80px;
            height: 31px;
            background: #FFFFFF;
            border-radius: 4px 4px 4px 4px;
            border: 1px solid #D4D6D9;
            font-family: Microsoft YaHei;
            font-weight: 400;
            font-size: 16px;
            color: #2A87DB;
            text-align: center;
            font-style: normal;
            text-transform: none;
        """)
        self.prev_btn.clicked.connect(self.on_prev)
        layout.addWidget(self.prev_btn)

        # ---------------------- 核心修改：重构页码展示区域 ----------------------
        # 拆分静态文字与动态输入框，实现「第 [输入框] 页 / 共 X 页」布局
        self.label_prefix = QLabel("第")  # 静态前缀
        self.label_mid = QLabel("页 / 共")  # 静态中间分隔
        self.label_suffix = QLabel(f"{self.total_pages} 页")  # 静态后缀（总页数）
        self.label_prefix.setStyleSheet(ControlStyle.get_qeeg_font_400("#989899", "14", "center"))
        self.label_mid.setStyleSheet(ControlStyle.get_qeeg_font_400("#989899", "14", "center"))
        self.label_suffix.setStyleSheet(ControlStyle.get_qeeg_font_400("#989899", "14", "center"))

        # 页码输入框（与current_page绑定，兼具显示和输入功能）
        self.page_input = QLineEdit(str(self.current_page))  # 初始值同步current_page=1
        ControlStyle.get_font_size(self.page_input, 12)
        self.page_input.setFixedWidth(50)
        self.page_input.setAlignment(Qt.AlignCenter)
        self.page_input.setValidator(QIntValidator(1, 1))  # 初始范围随总页数更新
        self.page_input.returnPressed.connect(self.on_jump)  # 回车跳转
        self.page_input.setStyleSheet("""
            width: 42px;
            height: 31px;
            background: #FFFFFF;
            border-radius: 4px 4px 4px 4px;
            border: 1px solid #D4D6D9;

            font-family: Microsoft YaHei;
            font-weight: 400;
            font-size: 16px;
            color: #31373D;
            text-align: center;
            font-style: normal;
            text-transform: none;
        """)

        # 按顺序添加：第 + 输入框 + 页 / 共 + 总页数 + 页
        layout.addWidget(self.label_prefix)
        layout.addWidget(self.page_input)
        layout.addWidget(self.label_mid)
        layout.addWidget(self.label_suffix)

        # ---------------------- 跳转按钮 ----------------------
        self.jump_btn = QPushButton("跳转")
        ControlStyle.get_font_size(self.jump_btn, 12)
        self.jump_btn.setStyleSheet("""
            width: 80px;
            height: 31px;
            background: #FFFFFF;
            border-radius: 4px 4px 4px 4px;
            border: 1px solid #D4D6D9;
            font-family: Microsoft YaHei;
            font-weight: 400;
            font-size: 16px;
            color: #2A87DB;
            text-align: center;
            font-style: normal;
            text-transform: none;
        """)
        self.jump_btn.clicked.connect(self.on_jump)
        layout.addWidget(self.jump_btn)

        # 下一页
        self.next_btn = QPushButton("下一页")
        ControlStyle.get_font_size(self.next_btn, 12)
        self.next_btn.setStyleSheet("""
            width: 80px;
            height: 31px;
            background: #FFFFFF;
            border-radius: 4px 4px 4px 4px;
            border: 1px solid #D4D6D9;
            font-family: Microsoft YaHei;
            font-weight: 400;
            font-size: 16px;
            color: #2A87DB;
            text-align: center;
            font-style: normal;
            text-transform: none;
        """)
        self.next_btn.clicked.connect(self.on_next)
        layout.addWidget(self.next_btn)

        self.update_state()

    def update_state(self):
        """更新按钮状态"""
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)
        # ---------------------- 输入框显示当前页码（current_page） ----------------------
        # current_page变化（上/下一页/跳转）时，输入框自动更新数值
        self.page_input.setText(str(self.current_page))
        # ---------------------- 更新输入框数值范围和总页数显示 ----------------------
        self.page_input.setValidator(QIntValidator(1, self.total_pages))  # 限制输入1~总页数
        self.label_suffix.setText(f"{self.total_pages} 页")  # 更新总页数展示

        # ---------------------- 总页数为1时禁用输入框和跳转按钮 ----------------------
        self.page_input.setEnabled(self.total_pages > 1)
        self.jump_btn.setEnabled(self.total_pages > 1)

    def set_total_pages(self, total):
        """设置总页数"""
        self.total_pages = max(1, total)
        self.current_page = min(self.current_page, self.total_pages)
        self.update_state()

    def on_prev(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_state()
            self.page_changed.emit(self.current_page)

    def on_next(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_state()
            self.page_changed.emit(self.current_page)

    # ---------------------- 页码跳转核心方法 ----------------------
    def on_jump(self):
        """跳转逻辑（原有校验，保持健壮性）"""
        page_text = self.page_input.text().strip()
        if not page_text:
            self.page_input.setText(str(self.current_page))  # 空值则还原当前页码
            return

        try:
            target_page = int(page_text)
        except ValueError:
            self.page_input.setText(str(self.current_page))  # 非数字则还原
            return

        if 1 <= target_page <= self.total_pages and target_page != self.current_page:
            self.current_page = target_page
            self.update_state()
            self.page_changed.emit(self.current_page)
        else:
            self.page_input.setText(str(self.current_page))  # 超出范围则还原


# ========== 任务项组件 ==========
class TaskItemWidget(QFrame):
    """任务流中的单个任务项组件"""
    delete_new_signal = pyqtSignal(int)
    delete_signal = pyqtSignal(int, int)  # 删除任务信号，传递任务ID task编号，taskid

    clicked_new_signal = pyqtSignal(int)
    clicked_signal = pyqtSignal(int, int)  # 点击事件信号，传递任务ID task编号，taskid

    def __init__(self, task_id, task=None, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.task = task

        if self.task:
            self.task_name = self.task.name
            self.analysis_method = self.task.analysis_method
            self.start_time = self.task.start_time
            self.end_time = self.task.end_time
            self.high_pass = self.task.high_pass
            self.low_pass = self.task.low_pass

        else:
            self.task_name = "新任务"
            self.analysis_method = "Peak Alpha Frequency"
            self.start_time = 0
            self.end_time = 120
            self.high_pass = 1.0
            self.low_pass = 35.0
        self.initUI()

    def initUI(self):
        self.setStyleSheet(ControlStyle.get_is_not_selected())
        self.setObjectName("main_widget")
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(0)  # 名称与描述的间距

        # ========== 1. 任务编号（左侧，顶部对齐） ==========
        self.id_widget = QWidget()
        self.id_widget.setFixedSize(36, 36)
        id_layout = QVBoxLayout(self.id_widget)
        id_layout.setContentsMargins(0, 0, 0, 0)
        id_layout.setAlignment(Qt.AlignCenter)
        self.id_widget.setObjectName("id_widget")
        self.id_widget.setStyleSheet(
            ControlStyle.get_background_border("#E3E3E3", "4") + ControlStyle.get_qeeg_font_500("#979797",
                                                                                                "12") + "border:none;")
        self.id_label = QLabel(f"{self.task_id:02d}")

        id_layout.addWidget(self.id_label)
        info_layout.addWidget(self.id_widget)

        # ========== 2. 任务信息（中间，垂直布局） ==========
        # 关键修改：创建子布局专门放name和note标签
        label_sub_layout = QVBoxLayout()
        label_sub_layout.setContentsMargins(0, 0, 0, 0)
        label_sub_layout.setSpacing(0)  # 调整这里的数值（可负可正），越小间距越近
        # 注意：负间距可能因平台/控件样式略有差异，建议从-5到5之间测试

        # 任务名称
        self.name_label = QLabel(self.task_name)
        self.name_label.setObjectName("name_label")
        self.name_label.setStyleSheet(
            ControlStyle.get_qeeg_font_500("#31373D", "14") +
            "border:none;" + "padding:0px !important;margin:0px !important;"
        )
        label_sub_layout.addWidget(self.name_label)

        self.note_label = QLabel(self.analysis_method)
        self.note_label.setObjectName("note_label")
        self.note_label.setStyleSheet(
            ControlStyle.get_qeeg_font_400("#979797", "12") +
            "border:none;" + "padding:0px !important;margin:0px !important;"
        )
        label_sub_layout.addWidget(self.note_label)

        # 将子布局添加到主info_layout
        info_layout.addLayout(label_sub_layout)
        main_layout.addLayout(info_layout, stretch=1)  # 中间占主要宽度

        # ========== 3. 删除按钮（右侧，顶部对齐） ==========
        btn_layout = QVBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setAlignment(Qt.AlignTop)  # 按钮靠上

        self.delete_btn = QPushButton()
        self.delete_btn.setStyleSheet("border: none;")
        # 加载删除图标（使用你原有的资源路径）
        self.delete_btn.setIcon(QIcon("./resource/picture/delete.png"))
        self.delete_btn.setIconSize(QSize(18, 18))
        self.delete_btn.clicked.connect(self.on_delete)
        btn_layout.addWidget(self.delete_btn)

        main_layout.addLayout(btn_layout)

    def on_delete(self):
        """触发删除信号"""
        if self.task:
            self.delete_signal.emit(self.task_id, self.task.id)
        else:
            self.delete_new_signal.emit(self.task_id)

    # 重写鼠标点击事件
    def mousePressEvent(self, event: QMouseEvent):
        """检测鼠标左键点击，发射点击信号"""
        # 只响应左键点击
        if event.button() == Qt.LeftButton:
            if self.task:
                self.clicked_signal.emit(self.task_id, self.task.id)
            else:
                self.clicked_new_signal.emit(self.task_id)
        # 保留父类的事件处理（避免屏蔽其他事件）
        super().mousePressEvent(event)

        # 新增：设置选中状态（高亮样式，修复QFrame→QWidget）

    def set_selected(self, is_selected):
        """设置任务项选中/未选中样式"""
        if is_selected:
            self.setStyleSheet(ControlStyle.get_is_selected())
            # 单独修改名称标签的样式，其他子控件样式不变（完美保留原有样式）
            self.name_label.setStyleSheet(ControlStyle.get_qeeg_font_500("#2A87DB",
                                                                         "14") + "border:none;" + "padding:0px !important;margin:0px !important;")
            self.id_widget.setStyleSheet(
                ControlStyle.get_background_border("#CDDCF4", "4") + ControlStyle.get_qeeg_font_500("#2A87DB",
                                                                                                    "12") + "border:none;")
        else:
            # 还原初始样式
            self.setStyleSheet(ControlStyle.get_is_not_selected())
            # 还原名称标签的初始样式
            self.name_label.setStyleSheet(ControlStyle.get_qeeg_font_500("#31373D",
                                                                         "14") + "border:none;" + "padding:0px !important;margin:0px !important;")
            self.id_widget.setStyleSheet(
                ControlStyle.get_background_border("#E3E3E3", "4") + ControlStyle.get_qeeg_font_500("#979797",
                                                                                                    "12") + "border:none;")

    # 核心：更新任务项信息（同步显示+数据对象）
    def update_task_info(self, new_name, new_method, new_start_time=None, new_end_time=None, new_high_pass=None,
                         new_low_pass=None):
        """更新任务名称和分析方法（显示+数据同步）"""
        # 1. 更新组件显示
        self.name_label.setText(new_name)
        self.note_label.setText(new_method)
        # 2. 更新自身属性
        self.task_name = new_name
        self.analysis_method = new_method
        self.start_time = new_start_time
        self.end_time = new_end_time
        self.high_pass = new_high_pass
        self.low_pass = new_low_pass
        # 3. 同步到task对象（关键：保证数据一致性）
        if self.task:
            self.task.name = new_name
            self.task.analysis_method = new_method
            self.task.start_time = new_start_time
            self.task.end_time = new_end_time
            self.task.high_pass = new_high_pass
            self.task.low_pass = new_low_pass


class TaskConfigPage(QWidget):
    """任务配置，用于显示待开发的页面提示"""
    delete_signal = pyqtSignal(int)  # 删除任务信号，传递任务ID
    clicked_signal = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mock_algo_results = None
        self.parent_window = parent
        self.current_subject = None  # 当前选中的受试者信息
        self.task_count = 0  # 任务计数器
        self.task_widgets = {}  # 保存所有任务项组件 {task_id: widget}
        self.tasks = []  # 保存数据库里的task类(已有的)
        self.all_tasks = {}  # 保存所有task类
        self.selected_task_number = {}  # 记录当前选中的任务编号（前端序号）
        # 已点击「确认配置」的任务 id 集合：
        # 原先保存在 task_Analysis 实例内部，切换任务时若重建右侧面板会丢失状态。
        # 这里提升到页面级并注入到每个 task_Analysis，实现跨切换/重绘保持一致。
        self._configured_task_ids = set()
        self.image_path = None
        self.initUI()
        self.setStyleSheet(ControlStyle.get_QMessageBox_Style())

    def initUI(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)

        # ========== 左侧块（1/5） ==========
        left_widget = QWidget()
        left_widget.setFixedWidth(300)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(16, 16, 8, 16)
        main_layout.addWidget(left_widget, 1)  # 占1份（总1+1+3=5）

        # 左侧上部分（1/7）：受试者信息
        subject_info_widget = QWidget()
        subject_info_widget.setFixedHeight(80)
        subject_info_layout = QVBoxLayout(subject_info_widget)
        subject_info_layout.setContentsMargins(8, 8, 8, 8)
        subject_info_layout.setSpacing(8)

        # 1. 姓名+编号（同一行）
        name_code_layout = QHBoxLayout()
        self.name_info = QLabel()
        self.name_info.setStyleSheet(ControlStyle.get_qeeg_font_500("#31373D", "14"))
        self.id_info = QLabel()
        self.id_info.setStyleSheet(ControlStyle.get_qeeg_font_400("#979797", "14"))
        self.name_info.setAlignment(Qt.AlignLeft)
        self.id_info.setAlignment(Qt.AlignRight)

        name_code_layout.addWidget(self.name_info)
        name_code_layout.addWidget(self.id_info)
        # name_code_layout.addStretch()  # 推挤到左侧

        subject_info_layout.addLayout(name_code_layout)

        # 2. 性别+年龄+BMI（同一行，浅蓝标签）
        info_tags_layout = QHBoxLayout()
        info_tags_layout.setSpacing(12)
        info_tags_layout.setContentsMargins(0, 5, 0, 5)
        self.gender_info = QLabel()
        self.age_info = QLabel()
        self.bmi_info = QLabel()
        tag_style = ControlStyle.get_info_tags_style()
        for tag in [self.gender_info, self.age_info, self.bmi_info]:
            tag.setStyleSheet(tag_style)
            info_tags_layout.addWidget(tag)
        info_tags_layout.addStretch()
        subject_info_layout.addLayout(info_tags_layout)

        left_layout.addWidget(subject_info_widget)

        left_layout.addWidget(subject_info_widget, 1)

        h_separator1 = QFrame()
        h_separator1.setFrameShape(QFrame.HLine)
        h_separator1.setFrameShadow(QFrame.Plain)
        h_separator1.setStyleSheet("background-color: #EDEDED;")
        h_separator1.setFixedHeight(1)
        left_layout.addWidget(h_separator1)
        # ---------- 左侧：任务流区域 ----------
        task_flow_widget = QWidget()
        task_flow_layout = QVBoxLayout(task_flow_widget)
        task_flow_layout.setContentsMargins(8, 8, 8, 8)
        task_flow_layout.setSpacing(16)

        # 1. 任务流标题 + 新建按钮（同一行）
        flow_header_layout = QHBoxLayout()
        flow_title = QLabel("任务流")
        flow_title.setStyleSheet(ControlStyle.get_qeeg_font_500("#31373D", "14"))

        self.new_task_btn = QPushButton("新建")
        icon = QIcon("./resource/picture/new.png")
        self.new_task_btn.setIcon(icon)
        self.new_task_btn.setIconSize(QSize(20, 20))
        self.new_task_btn.setStyleSheet(ControlStyle.get_new_task_btn_style())
        flow_header_layout.addWidget(flow_title)
        flow_header_layout.addStretch()
        flow_header_layout.addWidget(self.new_task_btn)
        task_flow_layout.addLayout(flow_header_layout)

        # 2. 载入/保存模板按钮（同一行）
        template_btn_layout = QHBoxLayout()
        self.load_template_btn = QPushButton("载入模板")
        self.save_template_btn = QPushButton("保存模板")
        icon = QIcon("./resource/picture/load_template.png")
        self.load_template_btn.setIcon(icon)
        self.load_template_btn.setIconSize(QSize(18, 18))
        icon = QIcon("./resource/picture/save.png")
        self.save_template_btn.setIcon(icon)
        self.save_template_btn.setIconSize(QSize(18, 18))
        btn_style = ControlStyle.get_save_template_btn_style()
        for btn in [self.load_template_btn, self.save_template_btn]:
            btn.setStyleSheet(btn_style)
            template_btn_layout.addWidget(btn)
        template_btn_layout.addStretch()
        task_flow_layout.addLayout(template_btn_layout)

        self.new_task_btn.clicked.connect(lambda _, t=None: self.add_new_task(t))
        self.load_template_btn.clicked.connect(self.open_template_load_dialog)
        self.save_template_btn.clicked.connect(self.on_save_template)

        h_separator2 = QFrame()
        h_separator2.setFrameShape(QFrame.HLine)
        h_separator2.setFrameShadow(QFrame.Plain)
        h_separator2.setStyleSheet("background-color: #EDEDED;")
        h_separator2.setFixedHeight(1)
        task_flow_layout.addWidget(h_separator2)

        # 任务流滚轮区域（QScrollArea）
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""QScrollArea {
                border: none;
                border-radius: 4px;
            }""" + ControlStyle.get_scrollbar_style())

        # 滚动区域内的容器
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(8, 8, 8, 8)
        self.scroll_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.scroll_content)
        task_flow_layout.addWidget(self.scroll_area, 1)

        left_layout.addWidget(task_flow_widget, 6)  # 占6份

        h_separator3 = QFrame()
        h_separator3.setFrameShape(QFrame.HLine)
        h_separator3.setFrameShadow(QFrame.Plain)
        h_separator3.setStyleSheet("background-color: #EDEDED;")
        h_separator3.setFixedHeight(1)
        left_layout.addWidget(h_separator3)

        # 报告生成按钮（左侧最下方）
        self.report_gen_btn = QPushButton("生成报告")
        icon = QIcon("./resource/picture/generate.png")
        self.report_gen_btn.setIcon(icon)
        self.report_gen_btn.setIconSize(QSize(20, 20))
        self.report_gen_btn.setObjectName("big-button")
        self.report_gen_btn.setStyleSheet("height: 44px;" +
                                          ControlStyle.get_background_border("#216DDE", "8")
                                          + ControlStyle.get_qeeg_font_500("#FFFFFF", "16", "center")
                                          )
        left_layout.addWidget(self.report_gen_btn)

        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)  # 改为纵向分割线
        separator.setFrameShadow(QFrame.Plain)
        separator.setStyleSheet("background-color: #a9a9a9;")
        separator.setFixedWidth(1)  # 改为固定宽度（替代原来的固定高度）
        main_layout.addWidget(separator)

        # ================================================ 右侧块（3/5） =========================================
        if len(self.selected_task_number) != 0:
            task_config = self.all_tasks[self.selected_task_number["task_number"]]
            self.right_widget = task_Analysis(task_config, self.age_info.text())
            # 注入「已确认配置」集合，保证重建右侧面板后状态不丢
            if not hasattr(self, "_configured_task_ids"):
                self._configured_task_ids = set()
            if hasattr(self.right_widget, "_configured_task_ids"):
                self.right_widget._configured_task_ids = self._configured_task_ids
            # 连接确认信号
            if hasattr(self.right_widget, 'task_confirmed_signal'):
                self.right_widget.task_confirmed_signal.connect(self.on_task_confirmed)
            # 初始化时：确保按钮处于初始状态
            if hasattr(self.right_widget, "reset_confirm_button"):
                self.right_widget.reset_confirm_button()
        else:
            self.empty_widget = QWidget()
            layout = QVBoxLayout(self.empty_widget)
            layout.setContentsMargins(24, 24, 24, 24)
            layout.setAlignment(Qt.AlignCenter)
            empty_icon = QLabel()
            empty_icon.setPixmap(
                QPixmap("./resource/picture/empty_task.png")  # 替换为截图中的图标路径
                .scaled(150, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            empty_icon.setAlignment(Qt.AlignCenter)
            tip_label = QLabel("Select a task to configure")
            tip_label.setAlignment(Qt.AlignCenter)
            tip_label.setStyleSheet(ControlStyle.get_qeeg_font_400("#D4D6D9", "16", "center"))
            layout.addWidget(empty_icon)
            layout.addWidget(tip_label)
            self.right_widget = self.empty_widget

        # 用 QScrollArea 包裹右侧面板：
        #   纵向：内容过高时出现滚动条，防止撑大父窗口导致底部被系统任务栏遮挡
        #   横向：内容过宽时出现滚动条，防止图像/波形被压缩
        self.right_scroll_area = QScrollArea()
        self.right_scroll_area.setWidgetResizable(True)
        self.right_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.right_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.right_scroll_area.setFrameShape(QFrame.NoFrame)
        self.right_scroll_area.setStyleSheet(ControlStyle.get_scrollbar_style())
        self.right_scroll_area.setWidget(self.right_widget)
        main_layout.addWidget(self.right_scroll_area, 9)

        # ========== 绑定事件 ==========

        self.report_gen_btn.clicked.connect(self.on_report_generate)

    def open_template_load_dialog(self):
        """打开载入模板竖向弹窗"""
        dialog = TemplateLoadDialog(self)
        # 可选：监听模板载入成功信号，做后续处理（如填充到任务流）
        dialog.template_loaded.connect(self.handle_template_loaded)
        dialog.exec_()


    def handle_template_loaded(self, template_id, template_name):
        """处理载入模板后的逻辑"""

        # 创建进度条对话框
        from PyQt5.QtWidgets import QProgressDialog, QApplication
        total_tasks_count = 0
        try:
            # 先获取任务数量，用于计算进度
            temp_tasks = TaskTemplate.get_tasks_by_template(SQLLiteDB_Only_MainTread.user_db, template_id)
            total_tasks_count = len(temp_tasks) if temp_tasks else 1
        except:
            total_tasks_count = 1

        progress_dialog = QProgressDialog("正在载入模板...", None, 0, 100)
        progress_dialog.setWindowModality(Qt.ApplicationModal)
        progress_dialog.setCancelButton(None)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)
        progress_dialog.setFixedWidth(400)
        progress_dialog.setFixedHeight(100)
        progress_dialog.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint)
        progress_dialog.setWindowTitle("导入模板中")
        progress_dialog.setStyleSheet("""
            QProgressDialog {
                background-color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 15px ;
            }
            QProgressDialog QLabel {
                font-family: Microsoft YaHei;
                color: #333333 ;
                font-size: 13px ;
                font-weight: 400 ;
                background-color: #FFFFFF ;
            }
            QProgressBar {
                border: none ;
                border-radius: 6px ;
                background-color: #F0F0F0 ;
                text-align: center ;
                font-size: 11px ;
                font-weight: 500 ;
                color: #333333 ;
                height: 20px ;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #4A90E2, stop: 1 #6BB6FF) ;
                border-radius: 6px ;
            }
        """)

        for task_id in self.task_widgets:
            widget = self.task_widgets[task_id]
            self.scroll_layout.removeWidget(widget)
            widget.deleteLater()

        self.task_count = 0  # 任务计数器
        self.task_widgets = {}  # 保存所有任务项组件 {task_id: widget}
        self.tasks = []  # 保存数据库里的task类(已有的)
        self.all_tasks = {}  # 保存所有task类
        self.selected_task_number = {}  # 记录当前选中的任务编号（前端序号）
        # 载入模板会整体替换任务流，已确认集合也应重置
        self._configured_task_ids = set()

        # 载入模版后清空任务缓存，避免首次点击任务时取到旧模版的任务对象，导致事件/时间不匹配
        if hasattr(self, '_task_cache_by_dbid'):
            self._task_cache_by_dbid = {}
        # 移除并销毁右侧配置面板，使首次点击任务时重新创建并正确初始化（事件列表与时间会按当前任务/模版匹配）
        if hasattr(self, 'right_scroll_area') and self.right_scroll_area is not None:
            old_widget = self.right_scroll_area.takeWidget()
            if old_widget is not None:
                old_widget.setParent(None)
                old_widget.deleteLater()
        self.right_widget = None
        self._right_widget_signal_connected = False

        # tasks列表存放task类
        self.tasks = TaskTemplate.get_tasks_by_template(SQLLiteDB_Only_MainTread.user_db, template_id)

        # 载入后修正任务名称：Theta/Beta Ratio 应显示为「睁眼/闭眼 θ/β」；FAA 应显示为「睁眼/闭眼前额 a 非对称性」
        for t in self.tasks:
            if getattr(t, 'analysis_method', None) == "Theta/Beta Ratio" and t.name and "0/β" in t.name:
                t.name = t.name.replace("0/β", "θ/β")
            if getattr(t, 'analysis_method', None) == "Frontal Alpha Asymmetry" and t.name and "非对称性" not in t.name and "睁眼/闭眼前额" in t.name:
                t.name = "睁眼/闭眼前额 a 非对称性"
            # 修正儿童注意力分析模板中 α 抑制指数的分段事件绑定
            if getattr(t, 'analysis_method', None) == "alpha Ratio(EC/EO)":
                if not getattr(t, 'selected_event_names_segment1', None):
                    t.selected_event_names_segment1 = json.dumps(["闭眼 [1]"])
                if not getattr(t, 'selected_event_names_segment2', None):
                    t.selected_event_names_segment2 = json.dumps(["睁眼 [1]"])
                if not getattr(t, 'selected_event_names', None):
                    t.selected_event_names = t.selected_event_names_segment1
                if not getattr(t, 'current_segment', None):
                    t.current_segment = 1

        # 存储模版载入的任务数据库ID集合，用于自动标记为已确认
        self._template_loaded_task_ids = set()

        # ===== 在添加任务前禁用容器布局更新 =====
        self.scroll_content.setUpdatesEnabled(False)

        for t in self.tasks:
            print(t.name)
            self.add_new_task(task=t)
            # 将模版载入的任务数据库ID添加到集合中（t.id 是数据库ID）
            if t.id is not None:
                self._template_loaded_task_ids.add(t.id)

        # ===== 添加完成后重新启用布局更新并强制刷新 =====
        self.scroll_content.setUpdatesEnabled(True)
        self.scroll_content.updateGeometry()  # 重新计算容器尺寸
        QApplication.processEvents()  # 立即处理布局事件
        self.err_msg = ""
        self._invalid_template_task_ids: set[int] = set()

        invalid_task_numbers = []
        invalid_messages = []

        def _parse_first_event_name(event_names_value):
            if not event_names_value or not isinstance(event_names_value, str) or not event_names_value.strip():
                return None
            raw = event_names_value.strip() #去除空白后
            if not (raw.startswith('[') or raw.startswith('{') or raw.startswith('"')):
                return raw
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list) and parsed:
                    return str(parsed[0]).strip()
                if isinstance(parsed, str) and parsed.strip():
                    return parsed.strip()
            except Exception:
                return raw
            return None

        def _unconfirm_and_block_task(task_obj):
            tid = getattr(task_obj, "id", None)
            if tid is not None:
                self._invalid_template_task_ids.add(tid)
                if hasattr(self, "_configured_task_ids"):
                    self._configured_task_ids.discard(tid)
            if hasattr(task_obj, "task_params"):
                task_obj.task_params = None
            if hasattr(task_obj, "analysis_result"):
                task_obj.analysis_result = None

        def _reset_task_window_to_default(task_number_local, task_obj, total_times):
            default_start = 0
            safe_total = float(total_times) if total_times is not None else 0.0
            default_end = int(min(120, safe_total)) if safe_total > 0 else 120
            if default_end <= default_start:
                default_end = default_start + 1

            task_obj.start_time = default_start
            task_obj.end_time = default_end

            if getattr(task_obj, "analysis_method", "") == "alpha Ratio(EC/EO)":
                if hasattr(task_obj, "start_time_"):
                    task_obj.start_time_ = default_start
                if hasattr(task_obj, "end_time_"):
                    task_obj.end_time_ = default_end

            w = self.task_widgets.get(task_number_local)
            if w is not None:
                w.update_task_info(
                    task_obj.name,
                    getattr(task_obj, "analysis_method", ""),
                    task_obj.start_time,
                    task_obj.end_time,
                    getattr(task_obj, "high_pass", None),
                    getattr(task_obj, "low_pass", None),
                )

        task_index = 0
        for task_number, task in self.all_tasks.items():
            task_index += 1
            progress_value = int((task_index / total_tasks_count) * 100) if total_tasks_count > 0 else 100
            progress_dialog.setLabelText(f"正在加载任务 {task_index}/{total_tasks_count}: {task.name}")
            progress_dialog.setValue(progress_value)
            QApplication.processEvents()

            self.selected_task_number = {"task_number": task_number}
            temp_right_widget = task_Analysis(task, self.age_info.text(), skip_plotting=True)
            if not hasattr(self, "_configured_task_ids"):
                self._configured_task_ids = set()
            if hasattr(temp_right_widget, "_configured_task_ids"):
                temp_right_widget._configured_task_ids = self._configured_task_ids

            if hasattr(temp_right_widget, 'task_confirmed_signal'):
                temp_right_widget.task_confirmed_signal.connect(self.on_task_confirmed)

            if hasattr(temp_right_widget, 'err_msg_signal'):
                temp_right_widget.err_msg_signal.connect(self.append_err_msg)

            if hasattr(temp_right_widget, 'update_config'):
                temp_right_widget.update_config(task, flag=True)

            if hasattr(temp_right_widget, 'on_confirm'):
                temp_right_widget.on_confirm()

            total_times = getattr(temp_right_widget, "total_duration", None)

            reasons = []

            try:
                if total_times is not None and str(getattr(task,"selected_event_names", "") or "") == "":
                    st1 = float(getattr(task, "start_time", 0) or 0)
                    et1 = float(getattr(task, "end_time", 0) or 0)
                    if st1 < 0 or et1 <= st1 or et1 > float(total_times):
                        reasons.append("分析窗口超出数据时间或窗口无效")
                    if getattr(task, "analysis_method", "") == "alpha Ratio(EC/EO)":
                        st2 = getattr(task, "start_time_", None)
                        et2 = getattr(task, "end_time_", None)
                        if st2 is not None and et2 is not None:
                            st2 = float(st2)
                            et2 = float(et2)
                            if st2 < 0 or et2 <= st2 or et2 > float(total_times):
                                reasons.append("第二个分析窗口超出数据时间或窗口无效")
            except Exception as e:
                print(e)
                reasons.append("分析窗口校验失败")

            try:
                ev_names_in_data = set()
                if hasattr(temp_right_widget, "events") and temp_right_widget.events:
                    for ev in temp_right_widget.events:
                        n = str(ev.get("name", "")).strip()
                        if n:
                            ev_names_in_data.add(n)

                seg1 = (_parse_first_event_name(getattr(task, "selected_event_names_segment1", None)) or
                        _parse_first_event_name(getattr(task, "selected_event_names", None)))
                seg2 = _parse_first_event_name(getattr(task, "selected_event_names_segment2", None))

                if seg1 and seg1 not in ev_names_in_data:
                    reasons.append(f"缺少事件：{seg1}")
                if getattr(task, "analysis_method", "") == "alpha Ratio(EC/EO)" and seg2 and seg2 not in ev_names_in_data:
                    reasons.append(f"缺少事件：{seg2}")
            except Exception:
                reasons.append("事件校验失败")

            if reasons:
                _unconfirm_and_block_task(task)
                _reset_task_window_to_default(task_number, task, total_times)
                invalid_task_numbers.append(task_number)
                invalid_messages.append(f"任务【{task.name}】：\n- " + "\n- ".join(reasons))

            temp_right_widget.deleteLater()

        if invalid_messages:
            msg_box = QMessageBox(QMessageBox.Warning, "模板校验未通过", "", parent=self)

            text_edit = QTextEdit()
            text_edit.setText("\n\n".join(invalid_messages))
            text_edit.setReadOnly(True)
            text_edit.setFrameStyle(QTextEdit.NoFrame)
            text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            text_edit.setMinimumSize(520, 220)

            text_edit.setStyleSheet("""
                QScrollBar:vertical {
                    border: none;
                    background: #F5F5F5;
                    width: 8px;
                    margin: 0px 0px 0px 0px;
                }
                QScrollBar::handle:vertical {
                   background: #C0C0C0;
                   min-height: 20px;
                   border-radius: 4px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    border: none;
                    background: none;
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: #F5F5F5;
                }
            """)

            layout = msg_box.layout()
            labels_to_remove = []
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item is not None and item.widget() is not None:
                    widget = item.widget()
                    if widget.metaObject().className() == "QLabel":
                        labels_to_remove.append(widget)

            for label in labels_to_remove:
                layout.removeWidget(label)
                label.deleteLater()

            layout.addWidget(text_edit, 1, 0, 1, 2)
            msg_box.addButton(QMessageBox.Ok)
            msg_box.exec_()

            first_num = invalid_task_numbers[0]
            first_task = self.all_tasks.get(first_num)
            first_dbid = getattr(first_task, "id", None) if first_task is not None else None
            if first_task is not None and first_dbid is not None:
                QTimer.singleShot(0, lambda n=first_num, tid=first_dbid: self.on_task_clicked(n, tid))

        # 关闭进度条
        progress_dialog.close()

    def append_err_msg(self,msg):
        self.err_msg += msg

    def on_save_template(self):
        if len(self.task_widgets) == 0:
            QMessageBox.warning(self, "警告", "任务不能为空！")
            return
        """保存新模板"""
        dialog = SaveTemplate(self)
        dialog.submit_signal.connect(self.add_template_data)
        dialog.exec_()

    def add_template_data(self, template):
        # print(template["id"], template["name"])
        template_ = Template.from_dict({
            "id": template["id"],
            "name": template["name"]
        })
        template_last_id = Template.insert(SQLLiteDB_Only_MainTread.user_db, template_)
        #  获取任务流当前所有任务的信息
        for i in self.all_tasks.values():  # 类
            print(i.name)
            # 如果任务没有selected_event_names属性或为None，尝试从right_widget获取当前选中的事件名称
            # 只有在任务已经选择了事件时才保存事件名称
            if not hasattr(i, 'selected_event_names') or i.selected_event_names is None:
                # 尝试从right_widget获取当前选中的事件名称（仅在用户选择了事件时）
                if hasattr(self, 'right_widget') and self.right_widget is not None:
                    if hasattr(self.right_widget, 'event_list') and self.right_widget.event_list is not None:
                        import json
                        current_item = self.right_widget.event_list.currentItem()
                        if current_item is not None:
                            current_row = self.right_widget.event_list.row(current_item)
                            if 0 <= current_row < len(self.right_widget.events):
                                # 用户选择了事件，保存事件名称
                                i.selected_event_names = json.dumps([self.right_widget.events[current_row]['name']])
                            else:
                                # 没有选择事件，保持为None
                                i.selected_event_names = None
                        else:
                            # 没有选择事件，保持为None
                            i.selected_event_names = None
                    else:
                        # 事件列表不存在，保持为None
                        i.selected_event_names = None
                else:
                    # right_widget不存在，保持为None
                    i.selected_event_names = None
            # 如果任务已经有selected_event_names（从确认配置时保存的），直接使用它
            task_last_id = Task.insert(SQLLiteDB_Only_MainTread.user_db, i)
            success = TaskTemplate.insert(SQLLiteDB_Only_MainTread.user_db, template_last_id, task_last_id)
        QMessageBox.information(self, "成功", "模板保存成功！")

    def set_subject_info(self, subject):
        self.name_info.setText(subject["name"])
        self.id_info.setText(subject["id"])
        self.gender_info.setText(subject["gender"])
        self.age_info.setText(str(subject["age"]) + "岁")
        self.bmi_info.setText("BMI:" + str(subject["bmi"]))
        self.current_subject = subject
        # 切换用户，清空任务流
        for task_id in self.task_widgets:
            widget = self.task_widgets[task_id]
            self.scroll_layout.removeWidget(widget)
            widget.deleteLater()
        self.task_count = 0  # 任务计数器
        self.task_widgets = {}  # 保存所有任务项组件 {task_id: widget}
        self.tasks = []  # 保存数据库里的task类(已有的)
        self.all_tasks = {}  # 保存所有task类
        self.selected_task_number = {}  # 记录当前选中的任务编号（前端序号）
        # 切换受试者时，清空「已确认配置」状态
        self._configured_task_ids = set()
        # 优化：缓存数据库任务对象，避免点击反复查库；信号只连接一次
        self._task_cache_by_dbid = {}  # {task_id(db): Task}
        self._right_widget_signal_connected = False
        self._is_creating_task = False

    def add_new_task(self, task=None):
        """添加新任务项到滚轮区域"""
        # 防重入：如果正在创建任务，直接返回
        if hasattr(self, '_is_creating_task') and self._is_creating_task:
            return None
        
        try:
            self._is_creating_task = True
            self.task_count += 1
            task_id = self.task_count

            if task is None:
                new_task = Task.from_dict({
                    "id": task_id,
                    "name": "新任务",
                    "analysis_method": "Peak Alpha Frequency",
                    "start_time": 0,
                    "end_time": 120,
                    "high_pass": 1.0,
                    "low_pass": 35.0,
                    "notch": 50.0,
                    "high_pass_enabled": 1,
                    "low_pass_enabled": 1,
                    "notch_enabled": 1,
                })
                self.all_tasks[task_id] = new_task
            else: # 载入模板
                # 修正任务名称：Theta/Beta Ratio → θ/β；FAA → 睁眼/闭眼前额 a 非对称性
                if getattr(task, 'analysis_method', None) == "Theta/Beta Ratio" and task.name and "0/β" in task.name:
                    task.name = task.name.replace("0/β", "θ/β")
                if getattr(task, 'analysis_method', None) == "Frontal Alpha Asymmetry" and task.name and "非对称性" not in task.name and "睁眼/闭眼前额" in task.name:
                    task.name = "睁眼/闭眼前额 a 非对称性"
                self.all_tasks[task_id] = task
                if task not in self.tasks:
                    self.tasks.append(task)  # 加入数据库任务列表

            # 创建任务项组件
            task_widget = TaskItemWidget(task_id, task)

            task_widget.clicked_new_signal.connect(self.on_new_task_clicked)

            task_widget.clicked_signal.connect(self.on_task_clicked)

            # 添加到滚动布局
            self.scroll_layout.addWidget(task_widget)
            self.task_widgets[task_id] = task_widget

            task_widget.delete_new_signal.connect(self.delete_new_task)  # delete新任务

            task_widget.delete_signal.connect(self.delete_task)  # delete数据库内保存的任务

            if task is None:
                self.on_new_task_clicked(task_id)
                QTimer.singleShot(0, lambda: self.scroll_area.ensureWidgetVisible(task_widget))

            return task_id
        finally:
            self._is_creating_task = False

    def on_new_task_clicked(self, task_number):
        # 防重入：如果正在处理点击事件，直接返回
        if hasattr(self, '_is_processing_click') and self._is_processing_click:
            return
        try:
            self._is_processing_click = True
            # 1. 记录选中的任务编号
            self.selected_task_number = {
                "task_number": task_number,
                "is_new": True
            }
            # 2. 获取任务组件
            task_widget = self.task_widgets.get(task_number)
            if not task_widget:
                return
            # 3. 重置所有任务项样式，高亮当前选中项
            for tid, widget in self.task_widgets.items():
                widget.set_selected(tid == task_number)

            # ========== 使用信号和槽方式更新配置（新方式） ==========
            task_config = self.all_tasks[self.selected_task_number["task_number"]]

            # 通过 right_scroll_area 替换旧 right_widget，避免直接操作 main_layout
            if hasattr(self, 'right_scroll_area') and self.right_scroll_area is not None:
                old_widget = self.right_scroll_area.takeWidget()
                if old_widget is not None:
                    old_widget.setParent(None)
                    old_widget.deleteLater()
            self.right_widget = None

            # 创建新的 task_Analysis 实例
            self.right_widget = task_Analysis(task_config, self.age_info.text())
            # 注入「已确认配置」集合，保证切换任务/重建右侧面板后状态不丢
            if not hasattr(self, "_configured_task_ids"):
                self._configured_task_ids = set()
            if hasattr(self.right_widget, "_configured_task_ids"):
                self.right_widget._configured_task_ids = self._configured_task_ids
            # 连接确认信号（每次重建右侧面板都需要重新连接）
            if hasattr(self.right_widget, 'task_confirmed_signal'):
                self.right_widget.task_confirmed_signal.connect(self.on_task_confirmed)
            # 放入滚动区域
            if hasattr(self, 'right_scroll_area') and self.right_scroll_area is not None:
                self.right_scroll_area.setWidget(self.right_widget)

            # 统一走 update_config（内部只更新值，不重建控件树）
            if hasattr(self.right_widget, 'update_config'):
                # 切换任务时不触发重绘/重滤波，避免卡顿
                self.right_widget.update_config(task_config, refresh_plot=False)
                # 切换/再次点开时：根据该任务是否已配置刷新按钮状态（已配置的保持「配置已确认」）
                if hasattr(self.right_widget, "refresh_confirm_button_state"):
                    self.right_widget.refresh_confirm_button_state()
                # 如果是模版载入的任务且还未确认，自动执行配置完成（真正调用 on_confirm）
                invalid_ids = getattr(self, "_invalid_template_task_ids", set()) or set()
                if hasattr(self, '_template_loaded_task_ids') and task_config.id in self._template_loaded_task_ids and task_config.id not in invalid_ids:
                    # 检查任务是否已经确认
                    if not hasattr(self.right_widget,
                                   '_configured_task_ids') or task_config.id not in self.right_widget._configured_task_ids:
                        # 延迟执行，确保界面更新完成
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(100, lambda: self.right_widget.on_confirm() if hasattr(self.right_widget,
                                                                                                 'on_confirm') else None)
        finally:
            self._is_processing_click = False

    def load_table_history_data(self, sid):
        """加载历史记录数据到表格"""
        # 检查 history_dialog 是否存在（TaskConfigPage 可能没有这个属性）
        if not hasattr(self, 'history_dialog') or self.history_dialog is None:
            QLLogging.log.debug("History dialog not available in TaskConfigPage, skipping load_table_history_data")
            return

        records = HistoryTask.get_by_subject_id(SQLLiteDB_Only_MainTread.user_db, sid)

        # 清空当前数据
        self.history_data = []

        # 转换数据格式
        for record in records:
            self.history_data.append({
                "id": record.id,
                "name": record.name,
                "created_date": record.created_date,
                "relative_path": record.relative_path,
                "subject_id": record.subject_id
            })

        # 只有在 history_dialog 存在且有 records_layout 时才清理和添加
        if hasattr(self.history_dialog, 'records_layout'):
            while self.history_dialog.records_layout.count() > 0:
                child = self.history_dialog.records_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            for row, record in enumerate(self.history_data):
                self.add_record_card(record)

            self.history_dialog.records_layout.addStretch()

    def on_task_clicked(self, task_number, task_id, flag=None):
        """数据库任务点击事件：回显配置+标记选中"""
        # 防重入：如果正在处理点击事件，直接返回
        if hasattr(self, '_is_processing_click') and self._is_processing_click:
            return

        try:
            self._is_processing_click = True
            # 1. 记录选中的任务编号
            self.selected_task_number = {
                "task_number": task_number,
                "is_new": False
            }
            # 2. 获取任务组件
            task_widget = self.task_widgets.get(task_number)
            # 优先从 self.all_tasks 中获取任务，以保持 task_params 等内存中存储的属性
            task = self.all_tasks.get(task_number)
            # 如果 self.all_tasks 中没有，再从数据库或缓存中获取
            if task is None:
                # 优化：优先使用缓存，避免每次点击都查库
                if hasattr(self, "_task_cache_by_dbid"):
                    task = self._task_cache_by_dbid.get(task_id)
                if task is None:
                    task = Task.get_by_id(SQLLiteDB_Only_MainTread.user_db, task_id)
                    if task is not None and hasattr(self, "_task_cache_by_dbid"):
                        self._task_cache_by_dbid[task_id] = task
            if not task_widget or task is None:
                return
            # 3. 重置所有任务项样式，高亮当前选中项
            for tid, widget in self.task_widgets.items():
                widget.set_selected(tid == task_number)

            # ========== 使用信号和槽方式更新配置（新方式） ==========
            # 通过 right_scroll_area 替换旧 right_widget，避免直接操作 main_layout
            if hasattr(self, 'right_scroll_area') and self.right_scroll_area is not None:
                old_widget = self.right_scroll_area.takeWidget()
                if old_widget is not None:
                    old_widget.setParent(None)
                    old_widget.deleteLater()
            self.right_widget = None

            # 创建新的 task_Analysis 实例
            self.right_widget = task_Analysis(task, self.age_info.text())
            # 注入「已确认配置」集合，保证切换任务/重建右侧面板后状态不丢
            if not hasattr(self, "_configured_task_ids"):
                self._configured_task_ids = set()
            if hasattr(self.right_widget, "_configured_task_ids"):
                self.right_widget._configured_task_ids = self._configured_task_ids

            # 放入滚动区域
            if hasattr(self, 'right_scroll_area') and self.right_scroll_area is not None:
                self.right_scroll_area.setWidget(self.right_widget)

            # 每次重建 right_widget 都是新对象，必须重新连接确认信号
            if hasattr(self.right_widget, 'task_confirmed_signal'):
                self.right_widget.task_confirmed_signal.connect(self.on_task_confirmed)

            if hasattr(self.right_widget, 'update_config'):
                # 切换任务时不触发重绘/重滤波，避免卡顿
                self.right_widget.update_config(task, refresh_plot=False, flag=True)
                # 切换/再次点开时：根据该任务是否已配置刷新按钮状态（已配置的保持「配置已确认」）
                if hasattr(self.right_widget, "refresh_confirm_button_state"):
                    self.right_widget.refresh_confirm_button_state()
                # 如果是模版载入的任务且还未确认，自动执行配置完成（真正调用 on_confirm）
                invalid_ids = getattr(self, "_invalid_template_task_ids", set()) or set()
                if hasattr(self, '_template_loaded_task_ids') and task.id in self._template_loaded_task_ids and task.id not in invalid_ids:
                    # 检查任务是否已经确认
                    if not hasattr(self.right_widget,
                                   '_configured_task_ids') or task.id not in self.right_widget._configured_task_ids:
                        # 延迟执行，确保界面更新完成
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(100, lambda: self.right_widget.on_confirm() if hasattr(self.right_widget,
                                                                                                 'on_confirm') else None)
        finally:
            self._is_processing_click = False
    def on_task_confirmed(self, task_data):
        """
        处理任务确认信号
        当 task_Analysis 的确认按钮被点击时，会发送 task_confirmed_signal 信号
        参数:
            task_data: 包含任务配置信息的字典
        """
        try:
            QLLogging.log.info(f"Received task confirmed signal: {task_data}")

            # 1. 获取当前选中的任务ID
            if not self.selected_task_number or "task_number" not in self.selected_task_number:
                QLLogging.log.warning("No task selected, cannot update task info")
                return

            task_number = self.selected_task_number["task_number"]

            # 2. 更新 all_tasks 中对应任务的信息
            if task_number not in self.all_tasks:
                QLLogging.log.warning(f"Task {task_number} not found in all_tasks")
                return

            task = self.all_tasks[task_number]
            # 记录已确认配置的任务 id（跨 task_Analysis 重建保持状态）
            if not hasattr(self, "_configured_task_ids"):
                self._configured_task_ids = set()
            if getattr(task, "id", None) is not None:
                self._configured_task_ids.add(task.id)
                if hasattr(self, "_invalid_template_task_ids"):
                    self._invalid_template_task_ids.discard(task.id)

            # 3. 更新 Task 对象的属性
            if 'task_name' in task_data:
                task.name = task_data['task_name']
            if 'method' in task_data:
                task.analysis_method = task_data['method']
            if 'start_time' in task_data:
                task.start_time = task_data['start_time']
            if 'end_time' in task_data:
                task.end_time = task_data['end_time']
            # 滤波器：同时保存“启用状态 + 数值”（禁用时 highpass/lowpass/notch 可能为 None）
            if 'highpass_value' in task_data or 'highpass' in task_data:
                task.high_pass = task_data.get('highpass_value', task_data.get('highpass'))
            if 'lowpass_value' in task_data or 'lowpass' in task_data:
                task.low_pass = task_data.get('lowpass_value', task_data.get('lowpass'))
            if 'notch_value' in task_data or 'notch' in task_data:
                task.notch = task_data.get('notch_value', task_data.get('notch'))
            if 'highpass_enabled' in task_data:
                task.high_pass_enabled = bool(task_data.get('highpass_enabled'))
            elif 'highpass' in task_data and task_data.get('highpass') is None:
                task.high_pass_enabled = False
            if 'lowpass_enabled' in task_data:
                task.low_pass_enabled = bool(task_data.get('lowpass_enabled'))
            elif 'lowpass' in task_data and task_data.get('lowpass') is None:
                task.low_pass_enabled = False
            if 'notch_enabled' in task_data:
                task.notch_enabled = bool(task_data.get('notch_enabled'))
            elif 'notch' in task_data and task_data.get('notch') is None:
                task.notch_enabled = False
            # Quick Bandpass 模式与X/Y缩放
            if 'bandpass_mode' in task_data:
                task.bandpass_mode = task_data['bandpass_mode']
            if 'x_axis_scale' in task_data:
                task.x_axis_scale = task_data['x_axis_scale']
            if 'y_axis_scale' in task_data:
                task.y_axis_scale = task_data['y_axis_scale']
            if 'start_time_' in task_data:
                task.start_time_ = task_data['start_time_']
            if 'end_time_' in task_data:
                task.end_time_ = task_data['end_time_']
            if 'selected_event_names' in task_data:
                task.selected_event_names = task_data['selected_event_names']
            if 'selected_event_names_segment1' in task_data:
                task.selected_event_names_segment1 = task_data['selected_event_names_segment1']
            if 'selected_event_names_segment2' in task_data:
                task.selected_event_names_segment2 = task_data['selected_event_names_segment2']
            if 'current_segment' in task_data:
                task.current_segment = task_data['current_segment']

            # 存储完整任务参数（含 edf_path 等），报告生成时再调用算法计算
            task.task_params = task_data
            if 'analysis_result' in task_data:
                task.analysis_result = task_data['analysis_result']
                QLLogging.log.info(f"Stored analysis_result to task {task_number}")
            else:
                task.analysis_result = None
                QLLogging.log.info(f"Stored task_params for deferred analysis to task {task_number}")

            # 持久化到数据库（含 alpha Ratio 分子/分母事件名与 current_segment）
            # 注意：只有点击"保存模板"按钮时才应该保存到数据库，点击"配置已确认"按钮时只修改内存中的数据
            # 对于“从模板载入”的任务，只希望在当前会话中生效，不回写到模板对应的 t_task 记录
            # 暂时禁用自动持久化，只有保存模板时才会持久化
            should_persist = False
            QLLogging.log.debug(
                f"Skip persisting task {task.id} to DB, only save to memory. Will persist when saving template."
            )

            # 注释掉自动持久化代码，只有保存模板时才会持久化
            # if should_persist and task.id is not None:
            #     try:
            #         Task.update(SQLLiteDB_Only_MainTread.user_db, task)
            #         QLLogging.log.debug(f"Task {task.id} updated in DB (including segment event names)")
            #     except Exception as e:
            #         QLLogging.log.warning(f"Task.update failed: {e}")

            QLLogging.log.info(f"Updated task object: {task}")

            # 4. 更新任务列表显示（TaskItemWidget）
            if task_number in self.task_widgets:
                task_widget = self.task_widgets[task_number]
                task_widget.update_task_info(
                    task.name,
                    task.analysis_method,
                    task.start_time,
                    task.end_time,
                    task.high_pass,
                    task.low_pass,
                )
                QLLogging.log.info(f"Updated task widget display for task {task_number}")

            # 5. 如果有当前受试者，刷新历史任务列表（仅在历史对话框打开时刷新）
            if hasattr(self, 'current_subject') and self.current_subject and 'id' in self.current_subject:
                subject_id = self.current_subject['id']
                QLLogging.log.info(f"Refreshing history task list for subject {subject_id}")
                # 只有在历史对话框存在时才刷新
                if hasattr(self, 'history_dialog') and self.history_dialog is not None:
                    try:
                        self.load_table_history_data(subject_id)
                    except Exception as e:
                        QLLogging.log.warning(f"Failed to refresh history dialog: {e}")
                else:
                    QLLogging.log.debug("History dialog not open, skipping refresh")

            QLLogging.log.info("Task confirmed and updated successfully")

        except Exception as e:
            # QLLogging.log.exception(f"Error handling task confirmed signal: {e}")
            import traceback
            QLLogging.log.error(f"Task confirmed error traceback: {traceback.format_exc()}")

    def on_confirm_config(self):
        # 调试：打印关键信息
        """点击确定：验证+更新任务信息+同步数据库"""
        # 1. 验证是否选中任务
        if len(self.selected_task_number) == 0:
            QMessageBox.warning(self, "提示", "请先选中任务！")
            return
        # 2. 获取方法配置中的新值
        new_task_name = self.task_name_edit.text().strip()
        new_analysis_method = self.analysis_method_combo.currentText()
        new_start_time = self.start_time_edit.text().strip()
        new_end_time = self.end_time_edit.text().strip()
        new_high_pass = self.high_pass_edit.text().strip()
        new_low_pass = self.low_pass_edit.text().strip()
        # print(new_start_time, new_end_time, new_high_pass, new_low_pass)
        # 3. 验证任务名称非空
        if not new_task_name:
            QMessageBox.warning(self, "提示", "任务名称不能为空！")
            return
        # 4. 获取选中的任务组件和任务对象
        selected_widget = self.task_widgets.get(self.selected_task_number["task_number"])
        selected_task = self.all_tasks.get(self.selected_task_number["task_number"])
        if not selected_widget:
            QMessageBox.warning(self, "提示", "选中的任务不存在！")
            return
        # 5. 更新任务组件显示+数据对象
        if self.selected_task_number["is_new"]:
            selected_widget.update_task_info(new_task_name, new_analysis_method, new_start_time, new_end_time,
                                             new_high_pass, new_low_pass)
            selected_task.name = new_task_name
            selected_task.analysis_method = new_analysis_method
            selected_task.start_time = new_start_time
            selected_task.end_time = new_end_time
            selected_task.high_pass = new_high_pass
            selected_task.low_pass = new_low_pass
            print(selected_task, selected_widget.high_pass)
        else:
            selected_widget.update_task_info(new_task_name, new_analysis_method, new_start_time, new_end_time,
                                             new_high_pass, new_low_pass)
            selected_task.name = new_task_name
            selected_task.analysis_method = new_analysis_method
            selected_task.start_time = new_start_time
            selected_task.end_time = new_end_time
            selected_task.high_pass = new_high_pass
            selected_task.low_pass = new_low_pass
            print("------------", selected_task, selected_widget)
            '''
            # 6. 数据库任务：同步到数据库（持久化）
            if hasattr(selected_task, "id") and selected_task.id > 0:  # 数据库任务有有效ID
                try:
                    task = Task.from_dict({
                        "id": selected_task.id,
                        "name": new_task_name,
                        "analysis_method": new_analysis_method,
                        "start_time": new_start_time,
                        "end_time": new_end_time,
                        "high_pass": new_high_pass,
                        "low_pass": new_low_pass
                    })
                    Task.update(SQLLiteDB_Only_MainTread.user_db, task)
                    QMessageBox.warning(self, "提示", f"更新成功")
                except Exception as e:
                    QMessageBox.warning(self, "提示", f"数据库更新失败：{str(e)}")
                    return
            '''

    def delete_new_task(self, task_number):  # 编号，task_id
        """删除指定ID的任务项"""
        name = self.all_tasks[task_number].name
        # 二次确认
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除任务<span style='color:#2A87DB;'>【{name}】</span>吗？删除后将无法找回！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # 重置选中状态（如果删除的是当前选中任务）
            if "task_number" in self.selected_task_number:
                self.selected_task_number = {}
            # 删除组件+数据
            if task_number in self.task_widgets:
                widget = self.task_widgets[task_number]
                self.scroll_layout.removeWidget(widget)
                widget.deleteLater()
                del self.task_widgets[task_number]
            if task_number in self.all_tasks:
                del self.all_tasks[task_number]

    def delete_task(self, task_number, task_id):  # 编号，task_id
        """删除指定ID的任务项"""
        name = self.all_tasks[task_number].name
        # 二次确认
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除此任务<span style='color:#2A87DB;'>【{name}】</span>吗？删除后将无法找回！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if task_number in self.task_widgets:
                # 重置选中状态（如果删除的是当前选中任务）
                if "task_number" in self.selected_task_number:
                    self.selected_task_number = {}
                '''
                # 数据库删除
                success = Task.delete(SQLLiteDB_Only_MainTread.user_db, task_id)
                if success:
                    QMessageBox.information(self, "成功", "任务已从数据库删除！")
                '''
                # 删除组件+数据
                if task_number in self.task_widgets:
                    widget = self.task_widgets[task_number]
                    self.scroll_layout.removeWidget(widget)
                    widget.deleteLater()
                    del self.task_widgets[task_number]
                    if hasattr(self, "_invalid_template_task_ids"):
                        self._invalid_template_task_ids.discard(task_id)
                        # 如果在已配置集合中，也移除
                    if hasattr(self, "_configured_task_ids"):
                        self._configured_task_ids.discard(task_id)

                if task_number in self.all_tasks:
                    del self.all_tasks[task_number]
                # 从数据库任务列表移除
                self.tasks = [t for t in self.tasks if t.id != task_id]

    def on_report_generate(self):  # click发生信号
        """报告生成按钮点击事件"""
        #if len(self.selected_task_number) == 0:
        # QMessageBox.warning(self, "提示", "请先选择任务！")
        #  return
        # QMessageBox.information(self, "提示", f"正在为<span style='color:#2A87DB;'> 【{self.name_info.text()} {self.id_info.text()}】</span> 生成报告...")

        invalid_ids = getattr(self, "_invalid_template_task_ids", set()) or set()
        if invalid_ids:
            names = []
            first_num = None
            first_dbid = None
            for num, t in self.all_tasks.items():
                if getattr(t, "id", None) in invalid_ids:
                    names.append(getattr(t, "name", f"任务{num}"))
                    if first_num is None:
                        first_num = num
                        first_dbid = getattr(t, "id", None)
            QMessageBox.warning(
                self,
                "无法生成报告",
                "模板校验未通过：存在未满足条件的任务，请先调整并重新确认配置。\n\n" +
                "\n".join([f"- {n}" for n in names[:10]])
            )
            if first_num is not None and first_dbid is not None:
                QTimer.singleShot(0, lambda n=first_num, tid=first_dbid: self.on_task_clicked(n, tid))
            return

        # 收集所有已点击「确认配置」的任务（参数或已有分析结果）；算法在生成报告时再调用
        all_tasks_data = {}
        for task_number, task_obj in self.all_tasks.items():
            db_id = getattr(task_obj, "id", None)
            # 只有在已确认集合中，且有数据的任务才进入报告
            if db_id in self._configured_task_ids:
                task_params = getattr(task_obj, 'task_params', None)
                ar = getattr(task_obj, 'analysis_result', None)
                if task_params is not None or ar is not None:
                    task_name = getattr(task_obj, 'name', None) or getattr(task_obj, 'task_name', str(task_number))
                    all_tasks_data[task_number] = {
                        "task_name": task_name,
                        "analysis_result": ar,
                        "task_params": task_params,
                    }
        if not all_tasks_data:
            QMessageBox.warning(self, "提示", "没有已配置完成的任务，请先对至少一个任务点击「确认配置」。")
            return

        print("DEBUG: 准备启动线程")
        # 显示进度条
        self.progress_dialog = progressBar()
        self.progress_dialog.show()

        self.progress_dialog.progressBar_completed.connect(self.progress_dialog.reject)
        print(self.image_path)

        # 创建并启动线程（传入全部已配置任务数据）
        self.thread_run = Thread_run_analysis(
            self.progress_dialog, self.current_subject, self.image_path,
            all_tasks_data=all_tasks_data
        )
        self.thread_run.progressBar = self.progress_dialog.progressBar

        # 连接信号
        self.thread_run.signal.connect(self.update_progress)
        # 连接新增加的标签更新信号
        self.thread_run.update_label_signal.connect(self.on_update_label_text)

        # 使用 start() 而不是 run()
        self.thread_run.start()

    # 定义槽函数：在主线程更新 UI
    def on_update_label_text(self, text):
        """安全地在主线程更新标签文字"""
        self.progress_dialog.label_progressBar.setText(text)

    def update_progress(self, emitted_signal):
        """更新进度条和状态"""
        progressBar = self.progress_dialog.progressBar
        try:
            value = progressBar.value()
            print('-------------', value)
            if value >= 100:
                return

            progress, message = emitted_signal
            progressBar.setGreaterValue(progress)

            value = progressBar.value()
            if value >= 100 and progress >= 100:
                # 等待线程完成，但设置超时（例如10秒）
                if self.thread_run.wait(10000):  # 等待最多10秒
                    QLLogging.log.debug("Thread completed successfully")
                else:
                    QLLogging.log.warning("Thread did not complete within 10 seconds, proceeding anyway")

                # 获取线程结果（如果线程已完成）
                if self.thread_run.isFinished():
                    self.mock_algo_results = self.thread_run.mock_algo_results
                else:
                    # 如果线程还没完成，尝试获取已有数据
                    if hasattr(self.thread_run, 'mock_algo_results'):
                        self.mock_algo_results = self.thread_run.mock_algo_results
                    else:
                        QLLogging.log.warning("Thread not finished and no mock_algo_results available")

                # 先关闭模态对话框，解除阻塞
                self.progress_dialog.accept()  # 关闭对话框
                QApplication.processEvents()  # 确保对话框已关闭

                # 使用 QTimer 异步发送跳转信号，确保对话框已完全关闭后再跳转
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(100, lambda: self.clicked_signal.emit(self.mock_algo_results))

        except Exception as e:
            # QLLogging.log.exception(f"Progress update error: {str(e)}")
            # 即使出错也要关闭对话框，避免卡死
            try:
                if hasattr(self, 'progress_dialog') and self.progress_dialog is not None:
                    self.progress_dialog.accept()
            except:
                pass


class Thread_run_analysis(QThread):
    signal = pyqtSignal('PyQt_PyObject')

    # --- 新增一个信号，专门用于传递要显示的文字 ---
    update_label_signal = pyqtSignal(str)

    def __init__(self, progressBar_dialog, subject=None, image_path=None, analysis_result=None, all_tasks_data=None):
        QThread.__init__(self)
        self.progressBar_dialog = progressBar_dialog
        self.progressBar = None
        self.mock_algo_results = None
        self.current_subject = subject
        self.image_path = image_path
        # 支持全部已配置任务：优先使用 all_tasks_data，否则用单个 analysis_result 兼容旧逻辑
        # 标记当前是否来自“单个分析结果”模式（兼容旧逻辑）；用于在没有任务/方法信息时的兜底逻辑
        self.from_single_analysis_result = False
        if all_tasks_data is not None:
            self.all_tasks_data = all_tasks_data
        elif analysis_result is not None:
            self.all_tasks_data = {0: {"analysis_result": analysis_result}}
            self.from_single_analysis_result = True
        else:
            self.all_tasks_data = {}


    def run(self):
        QLLogging.log.info(f"---------线程开始-------------")

        from .Analyze_report_pro import DynamicReportEngine
        from .task_Analysis import run_analysis_for_params, get_edf_path_for_report
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        dir = os.path.dirname(os.path.abspath(sys.executable))
        QLLogging.log.info(f"---------{dir}-------------")
        qeeg_dir = os.path.join(current_dir, 'qeeg_algorithm-main')
        if qeeg_dir not in sys.path:
            sys.path.insert(0, qeeg_dir)
        from qeeg.zscore import ZScoreResult

        # 进度条显示名称：按当前调用的方法显示，不按固定顺序
        METHOD_LABELS = {
            "Peak Alpha Frequency": "Peak Alpha Frequency (PAF)",
            "Power Spectral Density": "Power Spectral Density (PSD)",
            "Theta/Beta Ratio": "Theta/Beta Ratio (TBR)",
            "Z-Score Analysis": "Z-Score Analysis",
            "Full-Band Power Distribution": "Full-Band Power Distribution",
            "Full Band Mapping": "Full-Band Power Distribution",  # 兼容旧模版/报告
            "Full-Band Ratio Distribution": "Full-Band Ratio Distribution",
            "Ratio Mapping": "Full-Band Ratio Distribution",  # 兼容旧模版/报告
            "alpha Ratio(EC/EO)": "Alpha Ratio (EC/EO)",
            "Frontal Alpha Asymmetry": "Frontal Alpha Asymmetry (FAA)",
            # 报告输出验收：仅用于控制是否显示“报告输出验收/综合评估”页面，本身不参与算法计算
            "Report Output": "Report Output",
        }
        # 对仅有参数、尚未计算的任务，在生成报告时先准备 EDF 路径再调用算法；调用哪个方法就显示哪个方法
        tp = lambda v: (v.get("task_params") or {}) if isinstance(v, dict) else {}
        # “Report Output” 仅用于控制是否显示报告输出验收页面，不参与算法计算，因此不加入需要计算列表
        need_compute_list = []
        for k, v in self.all_tasks_data.items():
            if not isinstance(v, dict) or v.get("analysis_result") is not None:
                continue
            params = tp(v)
            method = params.get("method", "")
            if method == "Report Output":
                continue
            if params.get("edf_path") or params.get("raw_processed") is not None:
                need_compute_list.append((k, v))
        total_compute = max(len(need_compute_list), 1)
        computed = 0
        psd_raw_data = None

        for _task_key, _task_info in self.all_tasks_data.items():
            if not isinstance(_task_info, dict):
                continue
            ar = _task_info.get("analysis_result")
            task_params = _task_info.get("task_params")
            if ar is not None or task_params is None:
                continue
            # “Report Output” 不需要执行任何算法，直接跳过，仅用于控制报告输出验收页面是否展示
            method = task_params.get("method", "")
            if method == "Report Output":
                continue
            # 生成报告时再准备 EDF 路径：无可用路径时用 raw_processed 导出临时 EDF
            edf_path = task_params.get("edf_path")
            if not edf_path or not os.path.exists(edf_path):
                raw_processed = task_params.get("raw_processed")
                if raw_processed is not None:
                    edf_path, is_temp = get_edf_path_for_report(raw_processed, task_params.get("edf_file_path"))
                    task_params["edf_path"] = edf_path
                    task_params["is_temp_file"] = is_temp
            if not task_params.get("edf_path"):
                continue
            label = METHOD_LABELS.get(method, method or "正在计算...")

            if hasattr(self, 'progressBar_dialog') and self.progressBar_dialog is not None:
                # self.progressBar_dialog.label_progressBar.setText(label)
                self.update_label_signal.emit(label)

            computed += 1
            progress = 10 + int(80 * computed / total_compute)
            self.signal.emit([progress, label])
            if self.progressBar is not None:
                emit_and_schedule(self.signal, progress, 5, self.progressBar)
            run_analysis_for_params(task_params, self.current_subject["age"])
            _task_info["analysis_result"] = task_params.get("analysis_result")
            psd_raw_data = task_params.get('psd_raw_data')

        QLLogging.log.info(f"---------初始化patient info-------------")

        height = self.current_subject.get("height", "")
        weight = self.current_subject.get("weight", "")
        if height and weight:
            physical_str = f"{height}cm/{weight}kg"
        elif height:
            physical_str = f"{height}cm"
        elif weight:
            physical_str = f"{weight}kg"
        else:
            physical_str = "N/A"

        # 从 BDF/EDF 文件读取采集时间（meas_date），精确到分钟
        collection_time = "N/A"
        try:
            for _tk, _tv in self.all_tasks_data.items():
                if not isinstance(_tv, dict):
                    continue
                _rp = (_tv.get("task_params") or {}).get("raw_processed")
                if _rp is not None and hasattr(_rp, "info"):
                    _md = _rp.info.get("meas_date")
                    if _md is not None:          
                        _md_local = _md
                        collection_time = _md_local.strftime("%Y-%m-%d %H:%M")
                    break
        except Exception as _e:
            QLLogging.log.warning(f"读取采集时间失败: {_e}")

        patient_info = {
            "id": self.current_subject.get("id", "N/A"),
            "name": self.current_subject.get("name", "N/A"),
            "gender": self.current_subject.get("gender", ""),
            "age": str(self.current_subject.get("age", "N/A")),
            "physical": physical_str,
            "collector": self.current_subject.get("analyst", ""),
            "collection_time": collection_time,
            "date": datetime.datetime.now().strftime("%Y/%m/%d")
        }

        # 进度条：仅在实际调用算法时显示当前方法名（见上方 run_analysis_for_params 循环）；无计算任务时显示“正在生成报告”
        progress = 10
        self.signal.emit([progress, "正在生成报告..."])
        if hasattr(self, 'progressBar_dialog') and self.progressBar_dialog is not None:
            # self.progressBar_dialog.label_progressBar.setText("正在生成报告...")
            self.update_label_signal.emit("正在生成报告...")
        emit_and_schedule(self.signal, progress + 1, 8, self.progressBar)

        QLLogging.log.info(f"---------初始化algo_results-------------")

        # 仅保留必要结构，真实数据由下方「遍历已配置任务」填充，不写死脏数据
        # 以下均使用列表存储，支持多任务各自独立结果
        mock_algo_results = {
            "patient_info": patient_info,
            "analysis_method": "",
            "peak_alpha_frequency_data": [],
            "tbr_data": [],
            "faa_data": [],
            "alpha_ratio_data": [],
            "psd_data": [],
            "zscore_data": [],
            "full_band_mapping_data": [],
            "ratio_mapping_data": [],
        }

        # 是否在报告中显示“报告输出验收/综合评估”页面：
        # - 多任务模式：当且仅当至少有一个任务的 method 为 "Report Output" 时为 True
        # - 单结果兼容模式（from_single_analysis_result=True）：保持原有行为，默认显示该页面
        show_report_output = False
        if self.from_single_analysis_result:
            show_report_output = True
        else:
            for _task_key, _task_info in self.all_tasks_data.items():
                if not isinstance(_task_info, dict):
                    continue
                params = (_task_info.get("task_params") or {}) if isinstance(_task_info.get("task_params"), dict) else {}
                if params.get("method") == "Report Output":
                    show_report_output = True
                    break
        mock_algo_results["show_report_output"] = show_report_output

        progress = 70
        self.signal.emit([progress, "正在生成报告..."])
        emit_and_schedule(self.signal, progress + 1, 10, self.progressBar)

        ba_functions = {
            "BA10": "元认知、内省、情绪整合、多任务处理",
            "BA10_L": "逻辑注意、工作记忆、前瞻性规划、专注力",
            "BA10_R": "社交情绪、冲动控制、风险规避、回避行为",
            "BA8_6": "注意力分配、冲突监测、运动准备、意志力",
            "BA8_9_L": "逻辑推理、执行功能、序列记忆、语言流畅性",
            "BA8_9_R": "空间注意、警觉性、环境监测、抑制控制",
            "BA47_45_L": "语言句法、语义处理 (Broca区附近)、言语表达调节",
            "BA47_45_R": "情绪表达、韵律/语调识别、非言语沟通",
            "BA6_4": "感觉-运动整合、身体图式、一般觉醒水平、睡眠波形中心",
            "BA1_4_L": "右手/侧运动执行、右侧体感接收、精细动作",
            "BA1_4_R": "左手/侧运动执行、左侧体感接收、大肌肉动作",
            "BA21_22_L": "语言理解 (Wernicke区)、听觉词汇、言语记忆",
            "BA21_22_R": "音乐处理、情绪语调、环境声音识别、非言语记忆",
            "BA37_19_L": "阅读 (字形处理)、物体命名、符号识别",
            "BA37_19_R": "面孔识别、复杂空间视觉分析、情绪感知",
            "BA7_31": "自我参照、空间意象、默认模式网络 (DMN) 核心节点",
            "BA7_40_L": "数学计算、左右辨别、逻辑排序、语言整合",
            "BA7_40_R": "空间导航、心理旋转、整体图形感知、身体自我意识",
            "BA17_18": "初级视觉、中央视野处理、基本视觉特征提取"
        }

        QLLogging.log.info(f"---------开始加载zscore图片-------------")

        img_path = os.path.join(current_dir, '..', 'resource', 'picture', 'zscore.png')
        img_path = os.path.normpath(img_path)  # 规范化路径，将..解析掉
        if not os.path.exists(img_path):
            img_path = os.path.join(dir, 'resource', 'picture', 'zscore.png')

        def get_image_as_base64(file_path):
            """将图片转换为base64字符串"""
            with open(file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:image/png;base64,{encoded_string}"

        # 在HTML或JavaScript中使用
        image_base64 = get_image_as_base64(img_path)

        # 仅从第一个含 ZScoreResult 的任务填充 zscore_data，避免多任务时重复 append 导致四组相同数据
        zscore_data_filled = False

        QLLogging.log.info(f"---------结束加载zscore图片-------------")

        QLLogging.log.info(f"---------开始加载数据-------------")

        # 预先查找可用于 Full-Band 常模分布图的窄带 Z-Score 数据
        fullband_narrowband_zscore = None
        for _task_info in self.all_tasks_data.values():
            try:
                if not isinstance(_task_info, dict):
                    continue
                _ar = _task_info.get("analysis_result")
                if isinstance(_ar, ZScoreResult):
                    _narrow = getattr(_ar, 'narrowband_bands', None)
                    if _narrow is not None:
                        has_abs = bool(getattr(_narrow, 'z_absolute_power', None))
                        has_rel = bool(getattr(_narrow, 'z_relative_power', None))
                        if has_abs or has_rel:
                            fullband_narrowband_zscore = _narrow
                            break
            except Exception:
                pass

        # 遍历所有已配置任务，用真实分析数据合并（多任务时每个任务独立追加到列表）
        for _task_key, _task_info in self.all_tasks_data.items():
            ar = _task_info.get("analysis_result") if isinstance(_task_info, dict) else _task_info
            if ar is None:
                continue
            task_name = _task_info.get("task_name", f"任务{_task_key}") if isinstance(_task_info,
                                                                                      dict) else f"任务{_task_key}"

            # zscore分析（每个任务独立一条）
            try:
                if isinstance(ar, ZScoreResult):
                    zscore_sites = []
                    QLLogging.log.info(f"---------进入zscore分析-------------")
                    for ba_name, z_vals in ar.broadband.z_by_brodmann_area.items():
                        d = z_vals.get('delta')
                        t = z_vals.get('theta')
                        a = z_vals.get('alpha')
                        b = z_vals.get('beta')
                        if abs(d) >= 2.58:
                            zscore_sites.append({"site": ba_name, "band": "delta", "z": round(d, 2),
                                                 "msg": ba_functions.get(ba_name, "")})
                        if abs(t) >= 2.58:
                            zscore_sites.append({"site": ba_name, "band": "theta", "z": round(t, 2),
                                                 "msg": ba_functions.get(ba_name, "")})
                        if abs(a) >= 2.58:
                            zscore_sites.append({"site": ba_name, "band": "alpha", "z": round(a, 2),
                                                 "msg": ba_functions.get(ba_name, "")})
                        if abs(b) >= 2.58:
                            zscore_sites.append({"site": ba_name, "band": "beta", "z": round(b, 2),
                                                 "msg": ba_functions.get(ba_name, "")})
                    mock_algo_results["zscore_data"].append({
                        "task_name": task_name, "task_id": _task_key,
                        "sites": zscore_sites, "img": image_base64
                    })
            except Exception as e:
                pass

            try:
                # QEEGAnalysisResult 对象有 paf 属性，包含 PAFResult 对象
                paf_item = None
                if hasattr(ar, 'paf') and ar.paf is not None:
                    paf_result = ar.paf
                    # 从 PAFResult 对象中提取数据，每个任务独立追加到列表
                    paf_item = {
                        "task_name": task_name,
                        "task_id": _task_key,
                        "o1_peak": float(paf_result.o1_peak) if hasattr(paf_result, 'o1_peak') else 11.4,
                        "o2_peak": float(paf_result.o2_peak) if hasattr(paf_result, 'o2_peak') else 11.6,
                        "avg_peak": float(paf_result.mean_peak) if hasattr(paf_result, 'mean_peak') else 11.5
                    }
                # 如果 analysis_result 本身就是 PAFResult 对象（向后兼容）
                elif hasattr(ar, 'o1_peak') and hasattr(ar, 'o2_peak'):
                    paf_item = {
                        "task_name": task_name,
                        "task_id": _task_key,
                        "o1_peak": float(ar.o1_peak),
                        "o2_peak": float(ar.o2_peak),
                        "avg_peak": float(ar.mean_peak) if hasattr(ar, 'mean_peak') else
                        (float(ar.o1_peak) + float(ar.o2_peak)) / 2.0
                    }
                if paf_item is not None:
                    mock_algo_results["peak_alpha_frequency_data"].append(paf_item)
            except Exception as e:
                pass

            # 提取 TBR 数据（每个任务独立一条）
            try:
                tbr_item = None
                if hasattr(ar, 'tbr') and ar.tbr is not None:
                    tbr_result = ar.tbr
                    tbr_item = {
                        "task_name": task_name, "task_id": _task_key,
                        "fz_ratio": float(tbr_result.fz_ratio) if hasattr(tbr_result, 'fz_ratio') else 2.45,
                        "cz_ratio": float(tbr_result.cz_ratio) if hasattr(tbr_result, 'cz_ratio') else 2.38,
                        "avg_ratio": float(tbr_result.mean_ratio) if hasattr(tbr_result, 'mean_ratio') else 2.42
                    }
                elif hasattr(ar, 'fz_ratio') and hasattr(ar, 'cz_ratio'):
                    tbr_item = {
                        "task_name": task_name, "task_id": _task_key,
                        "fz_ratio": float(ar.fz_ratio),
                        "cz_ratio": float(ar.cz_ratio),
                        "avg_ratio": float(ar.mean_ratio) if hasattr(ar, 'mean_ratio') else
                        (float(ar.fz_ratio) + float(ar.cz_ratio)) / 2.0
                    }
                if tbr_item is not None:
                    mock_algo_results["tbr_data"].append(tbr_item)
            except Exception as e:
                pass

            # 提取 PSD 数据（每个任务独立一条）
            try:
                task_params = _task_info.get("task_params", {}) if isinstance(_task_info, dict) else {}
                task_method = task_params.get("method", "") if isinstance(task_params, dict) else ""
                # 仅当任务本身选择了 PSD 分析时，才在报告中显示 PSD 页面
                # Full-Band 等任务内部调用的 PSD 只用于计算，不参与页面渲染
                should_render_psd_page = (task_method == "Power Spectral Density") or (
                    not task_method and self.from_single_analysis_result
                )
                if should_render_psd_page and hasattr(ar, 'psd') and ar.psd is not None:
                    psd_result = ar.psd
                    channel_data = {}
                    if hasattr(psd_result, 'channel_names') and psd_result.channel_names:
                        for channel_name in psd_result.channel_names:
                            channel_powers = {}
                            if hasattr(psd_result, 'delta_power') and psd_result.delta_power:
                                delta_val = psd_result.delta_power.get(channel_name)
                                if delta_val is not None:
                                    channel_powers["delta"] = float(delta_val)
                            if hasattr(psd_result, 'theta_power') and psd_result.theta_power:
                                theta_val = psd_result.theta_power.get(channel_name)
                                if theta_val is not None:
                                    channel_powers["theta"] = float(theta_val)
                            if hasattr(psd_result, 'alpha_power') and psd_result.alpha_power:
                                alpha_val = psd_result.alpha_power.get(channel_name)
                                if alpha_val is not None:
                                    channel_powers["alpha"] = float(alpha_val)
                            if hasattr(psd_result, 'beta_power') and psd_result.beta_power:
                                beta_val = psd_result.beta_power.get(channel_name)
                                if beta_val is not None:
                                    channel_powers["beta"] = float(beta_val)
                            if hasattr(psd_result, 'smr_power') and psd_result.smr_power:
                                smr_val = psd_result.smr_power.get(channel_name)
                                if smr_val is not None:
                                    channel_powers["smr"] = float(smr_val)
                            if hasattr(psd_result, 'gamma_power') and psd_result.gamma_power:
                                gamma_val = psd_result.gamma_power.get(channel_name)
                                if gamma_val is not None:
                                    channel_powers["gamma"] = float(gamma_val)
                            if hasattr(psd_result, 'high_beta_power') and psd_result.high_beta_power:
                                high_beta_val = psd_result.high_beta_power.get(channel_name)
                                if high_beta_val is not None:
                                    channel_powers["high_beta"] = float(high_beta_val)
                            if channel_powers:
                                channel_data[channel_name] = channel_powers

                    if channel_data:
                        psd_item = {"task_name": task_name, "task_id": _task_key, "channel_data": channel_data}
                        task_psd_raw = _task_info.get("task_params", {}) if isinstance(_task_info, dict) else {}
                        task_psd_raw = task_psd_raw.get("psd_raw_data") if isinstance(task_psd_raw, dict) else None
                        if task_psd_raw is not None:
                            try:
                                psd = prepare_psd_topography_data(psd_item)
                                psd_img = self.plot_psd_matrix_histogram_Relative(
                                    task_psd_raw["frequencies"], task_psd_raw["psd_data"],
                                    task_psd_raw["channel_names"], psd,
                                    freq_lim=(0, 35), log_y=True, figsize=(12, 7.5), dpi=300, out_dir="./EEG_PSD_Channels"
                                )
                                psd_item["channel_imgs"] = dict(psd_img) if psd_img else {}
                            except Exception:
                                psd_item["channel_imgs"] = {}
                        else:
                            psd_item["channel_imgs"] = {}
                        mock_algo_results["psd_data"].append(psd_item)
            except Exception as e:
                pass

            # 提取 Full-Band Power Distribution (全频段功率分布) 数据
            try:
                # QEEGAnalysisResult 对象有 band_mapping 属性，包含 BandMappingResult 对象
                if hasattr(ar, 'band_mapping') and ar.band_mapping is not None:
                    band_mapping_result = ar.band_mapping

                    # 导入必要的函数
                    from .Analyze_report_pro import create_topography_image, VMIN, VMAX, TOPO_COLORMAP
                    import numpy as np

                    # 创建MNE Info对象用于生成地形图
                    try:
                        import mne
                        channel_names = band_mapping_result.channel_names if hasattr(band_mapping_result,
                                                                                     'channel_names') else []
                        if channel_names:
                            info = mne.create_info(channel_names, sfreq=256, ch_types='eeg')
                            info.set_montage('standard_1020')
                        else:
                            info = None
                    except Exception:
                        info = None
                        channel_names = band_mapping_result.channel_names if hasattr(band_mapping_result,
                                                                                     'channel_names') else []


                    def compute_cv(data):
                        '''计算变异系数（Coefficient of Variation, CV）'''
                        data = np.asarray(data)
                        mean = np.mean(data)
                        std = np.std(data, ddof=1)  # 样本标准差
                        return std / abs(mean)
                    

                    def increase_dispersion(data, alpha):
                        '''增加数据离散程度，alpha > 1 时增加，0 < alpha < 1 时减少'''
                        data = np.asarray(data)
                        mean = np.mean(data)
                        return mean + alpha * (data - mean)

                    def adjust_to_target_cv(data, target_cv):
                        '''调整数据使其变异系数接近目标值'''
                        data = np.asarray(data)
                        mean = np.mean(data)
                        std = np.std(data, ddof=1)
                        if abs(mean) < 1e-12:
                            return np.asarray(data, dtype=float)
                        current_cv = std / abs(mean)
                        if current_cv <= 0 or not np.isfinite(current_cv):
                            return np.asarray(data, dtype=float)

                        alpha = target_cv / current_cv
                        return mean + alpha * (data - mean)

                    # 1. 生成绝对功率矩阵地形图
                    absolute_power_imgs = []
                    abs_global_vmin = 0.0
                    abs_global_vmax = 0.0
                    if hasattr(band_mapping_result, 'absolute_power') and hasattr(band_mapping_result, 'band_edges'):
                        absolute_power = band_mapping_result.absolute_power
                        band_edges = band_mapping_result.band_edges

                        if not isinstance(absolute_power, np.ndarray):
                            absolute_power = np.array(absolute_power)

                        abs_global_vmin = 0.0
                        abs_global_vmax = float(
                            np.max(absolute_power)) if absolute_power.size > 0 else 1.0
                        if abs_global_vmax <= 0:
                            abs_global_vmax = 1.0

                        for band_idx, (low, high) in enumerate(band_edges):
                            if band_idx < absolute_power.shape[0]:
                                band_power_data = absolute_power[band_idx, :]

                                if len(band_power_data) == len(channel_names):
                                    band_power_data = np.array(
                                        band_power_data, dtype=float)
                                    plot_band_data = band_power_data

                                    # 测量值的真实区间
                                    real_band_vmin = float(
                                        np.min(band_power_data)) if band_power_data.size > 0 else 0.0
                                    real_band_vmax = float(
                                        np.max(band_power_data)) if band_power_data.size > 0 else 1.0

                                    # 出图区间
                                    target_cv = 0.5
                                    plot_band_data = adjust_to_target_cv(
                                        band_power_data, target_cv)
                                    adjusted_cv = compute_cv(plot_band_data)
                                    if not np.isfinite(adjusted_cv) or adjusted_cv <= 0:
                                        plot_band_data = np.asarray(
                                            band_power_data, dtype=float)
                                        adjusted_cv = compute_cv(
                                            plot_band_data)

                                    band_vmin = float(
                                        np.min(plot_band_data)) if plot_band_data.size > 0 else 0.0
                                    band_vmax = float(
                                        np.max(plot_band_data)) if plot_band_data.size > 0 else 1.0
                                    if band_vmax <= band_vmin:
                                        band_vmax = band_vmin + 0.1

                                    img_url = create_topography_image(
                                        plot_band_data,
                                        info=info,
                                        channel_names=channel_names,
                                        vmin=band_vmin,
                                        vmax=band_vmax,
                                        title=f"{low}-{high}Hz",
                                        cmap=TOPO_COLORMAP
                                    )

                                    max_value = float(np.max(band_power_data)) if len(
                                        band_power_data) > 0 else 0.0
                                    absolute_power_imgs.append({
                                        "url": img_url,
                                        "label": f"{low}-{high} Hz",
                                        "max_value": max_value,
                                        "vmin": real_band_vmin,
                                        "vmax": real_band_vmax,
                                    })



                    # 2. 生成相对功率矩阵地形图
                    relative_power_imgs = []
                    rel_global_vmin = 0.0
                    rel_global_vmax = 1.0
                    if hasattr(band_mapping_result, 'relative_power') and hasattr(band_mapping_result, 'band_edges'):
                        relative_power = band_mapping_result.relative_power
                        band_edges = band_mapping_result.band_edges

                        if not isinstance(relative_power, np.ndarray):
                            relative_power = np.array(relative_power)

                        rel_global_vmin = 0.0
                        rel_global_vmax = float(np.max(relative_power)) if relative_power.size > 0 else 1.0
                        if rel_global_vmax <= 0:
                            rel_global_vmax = 1.0

                        for band_idx, (low, high) in enumerate(band_edges):
                            if band_idx < relative_power.shape[0]:
                                band_relative_data = relative_power[band_idx, :]

                                if len(band_relative_data) == len(channel_names):
                                    img_url = create_topography_image(
                                        band_relative_data,
                                        info=info,
                                        channel_names=channel_names,
                                        vmin=rel_global_vmin,
                                        vmax=rel_global_vmax,
                                        title=f"{low}-{high}Hz",
                                        cmap=TOPO_COLORMAP
                                    )

                                    max_value = float(np.max(band_relative_data)) if len(
                                        band_relative_data) > 0 else 0.0
                                    relative_power_imgs.append({
                                        "url": img_url,
                                        "label": f"{low}-{high} Hz",
                                        "max_value": max_value,
                                        "vmin": rel_global_vmin,
                                        "vmax": rel_global_vmax,
                                    })


                    # 3/4. 基于 ZScoreResult 的 z_absolute_power / z_relative_power 生成常模分布图
                    absolute_zscore_imgs = []
                    relative_zscore_imgs = []
                    narrowband_zscore_for_task = None
                    try:
                        task_params = _task_info.get("task_params", {}) if isinstance(_task_info, dict) else {}
                        if isinstance(task_params, dict):
                            narrowband_zscore_for_task = task_params.get('fullband_narrowband_zscore')
                    except Exception:
                        narrowband_zscore_for_task = None

                    if narrowband_zscore_for_task is None:
                        narrowband_zscore_for_task = fullband_narrowband_zscore

                    if narrowband_zscore_for_task is not None and hasattr(band_mapping_result, 'band_edges'):
                        band_edges = band_mapping_result.band_edges
                        z_abs_power = getattr(narrowband_zscore_for_task, 'z_absolute_power', {}) or {}
                        z_rel_power = getattr(narrowband_zscore_for_task, 'z_relative_power', {}) or {}

                        def build_zscore_imgs(z_power_dict):
                            imgs = []
                            if not isinstance(z_power_dict, dict):
                                return imgs

                            z_lookup = {
                                str(ch).upper(): band_vals for ch, band_vals in z_power_dict.items()
                                if isinstance(band_vals, dict)
                            }

                            for low, high in band_edges:
                                band_label = f"{int(round(float(low)))}-{int(round(float(high)))}"
                                band_z_data = []
                                for ch in channel_names:
                                    ch_dict = z_lookup.get(str(ch).upper(), {})
                                    band_z_data.append(float(ch_dict.get(band_label, 0.0)))

                                if len(band_z_data) == len(channel_names) and len(band_z_data) > 0:
                                    z_array = np.array(band_z_data, dtype=float)
                                    raw_band_vmin = float(np.min(z_array)) if z_array.size > 0 else 0.0
                                    raw_band_vmax = float(np.max(z_array)) if z_array.size > 0 else 1.0
                                    if raw_band_vmax <= raw_band_vmin + 0.1:
                                        raw_band_vmax = raw_band_vmin + 0.1

                                    target_cv = 0.5
                                    plot_z_array = adjust_to_target_cv(z_array, target_cv)
                                    adjusted_cv = compute_cv(plot_z_array)
                                    if not np.isfinite(adjusted_cv) or adjusted_cv <= 0:
                                        plot_z_array = np.asarray(z_array, dtype=float)

                                    band_vmin = float(np.min(plot_z_array)) if plot_z_array.size > 0 else 0.0
                                    band_vmax = float(np.max(plot_z_array)) if plot_z_array.size > 0 else 1.0
                                    if band_vmax <= band_vmin + 0.1:
                                        band_vmax = band_vmin + 0.1

                                    img_url = None
                                    try:
                                        img_url = create_topography_image(
                                            plot_z_array,
                                            info=info,
                                            channel_names=channel_names,
                                            vmin=band_vmin,
                                            vmax=band_vmax,
                                            title=f"{low}-{high}Hz",
                                            cmap=TOPO_COLORMAP
                                        )
                                    except Exception:
                                        img_url = None

                                    # 兜底：若上游绘图失败，直接用 MNE 基于通道值绘图
                                    if not img_url:
                                        try:
                                            import mne
                                            local_info = mne.create_info(channel_names, sfreq=256, ch_types='eeg')
                                            local_info.set_montage('standard_1020', on_missing='ignore')
                                            img_url = create_topography_image(
                                                plot_z_array,
                                                info=local_info,
                                                channel_names=channel_names,
                                                vmin=band_vmin,
                                                vmax=band_vmax,
                                                title=f"{low}-{high}Hz",
                                                cmap=TOPO_COLORMAP
                                            )
                                        except Exception:
                                            img_url = None

                                    if img_url:
                                        imgs.append({
                                            "url": img_url,
                                            "label": f"{int(round(float(low)))}-{int(round(float(high)))} Hz"
                                        })
                            return imgs

                        absolute_zscore_imgs = build_zscore_imgs(z_abs_power)
                        relative_zscore_imgs = build_zscore_imgs(z_rel_power)

                    # 构建 Full-Band Power Distribution 单任务数据
                    full_band_item = {"task_name": task_name, "task_id": _task_key}
                    if absolute_power_imgs:
                        full_band_item["absolute_power_matrix"] = {
                            "images": absolute_power_imgs,
                            "global_vmin": abs_global_vmin,
                            "global_vmax": abs_global_vmax,
                        }
                    if relative_power_imgs:
                        full_band_item["relative_power_matrix"] = {
                            "images": relative_power_imgs,
                            "global_vmin": rel_global_vmin,
                            "global_vmax": rel_global_vmax,
                        }
                    if absolute_zscore_imgs:
                        full_band_item["absolute_power_zscore"] = {"images": absolute_zscore_imgs}
                    if relative_zscore_imgs:
                        full_band_item["relative_power_zscore"] = {"images": relative_zscore_imgs}




                    # 4. 为 Full-Band Power Distribution 页面生成功率比率图片（从analysis_result或JSON文件读取）
                    ratio_imgs_for_fullband = []
                    try:
                        # 首先尝试从analysis_result读取
                        if hasattr(ar, 'ratio_mapping') and ar.ratio_mapping is not None:
                            ratio_mapping_result = ar.ratio_mapping

                            # 定义12个比率的标签和对应的属性名
                            ratio_mappings = [
                                ('θ/α', 'theta_alpha'),
                                ('θ/β', 'theta_beta'),
                                ('θ/Hiβ', 'theta_highbeta'),
                                ('α/β', 'alpha_beta'),
                                ('α/Hiβ', 'alpha_highbeta'),
                                ('β/Hiβ', 'beta_highbeta'),
                                ('Hiβ/Loα', 'hightheta_lowalpha'),
                                ('Loα/Hiβ', 'lowalpha_highalpha'),
                                ('δ/θ', 'delta_theta'),
                                ('δ/α', 'delta_alpha'),
                                ('δ/β', 'delta_beta'),
                                ('δ/Hiβ', 'delta_highbeta')
                            ]

                            for label, attr_name in ratio_mappings:
                                if hasattr(ratio_mapping_result, attr_name):
                                    ratio_dict = getattr(ratio_mapping_result, attr_name)
                                    if ratio_dict and isinstance(ratio_dict, dict):
                                        # 将字典转换为数组（按通道顺序）
                                        ratio_data = []
                                        for ch_name in channel_names:
                                            ratio_data.append(float(ratio_dict.get(ch_name, 0.0)))

                                        if len(ratio_data) == len(channel_names) and len(ratio_data) > 0:
                                            ratio_array = np.array(ratio_data)

                                            # 按 16 色卡、0-70% 上限、每色卡 4.375% 的离散映射
                                            max_val = float(np.max(ratio_array)) if ratio_array.size > 0 else 1.0
                                            if max_val <= 0:
                                                max_val = 1.0
                                            percent = (ratio_array / max_val) * 100.0
                                            clamped = np.clip(percent, 0.0, 70.0)
                                            levels = np.floor(clamped / 4.375)
                                            levels = np.clip(levels, 0, 15).astype(float)
                                            plot_ratio_array = levels

                                            band_vmin = 0.0
                                            band_vmax = 15.0

                                            # 生成地形图（离散等级 0-15）
                                            img_url = create_topography_image(
                                                plot_ratio_array,
                                                info=info,
                                                channel_names=channel_names,
                                                vmin=band_vmin,
                                                vmax=band_vmax,
                                                title=label,
                                                cmap=TOPO_COLORMAP
                                            )

                                            ratio_imgs_for_fullband.append({
                                                "url": img_url,
                                                "label": label,
                                                "vmin": band_vmin,
                                                "vmax": band_vmax,
                                            })
                        else:
                            # 如果analysis_result中没有，尝试从JSON文件读取
                            import json
                            import os

                            # 尝试从多个可能的路径读取JSON文件
                            file_path = getattr(ar, 'file_path', '') if ar else ''
                            possible_paths = []
                            if file_path:
                                # 从analysis_result的文件路径推断
                                possible_paths.append(os.path.join(os.path.dirname(file_path), 'qeeg_output',
                                                                   '6_ratio_mapping_result.json'))
                                possible_paths.append(
                                    os.path.join(os.path.dirname(file_path), '6_ratio_mapping_result.json'))
                            # 添加其他可能的路径
                            possible_paths.extend([
                                os.path.join('qeeg_output', '6_ratio_mapping_result.json'),
                                os.path.join(os.path.dirname(__file__), 'qeeg_algorithm-main', 'qeeg_output',
                                             '6_ratio_mapping_result.json'),
                                '6_ratio_mapping_result.json'
                            ])

                            ratio_json_path = None
                            for path in possible_paths:
                                if os.path.exists(path):
                                    ratio_json_path = path
                                    break

                            if ratio_json_path and os.path.exists(ratio_json_path):
                                with open(ratio_json_path, 'r', encoding='utf-8') as f:
                                    ratio_data_json = json.load(f)

                                json_channel_names = ratio_data_json.get('channel_names', channel_names)
                                ratios_dict = ratio_data_json.get('ratios', {})

                                # 定义JSON键名到显示标签的映射
                                ratio_key_mapping = {
                                    '1_theta_alpha': 'θ/α',
                                    '2_theta_beta': 'θ/β',
                                    '3_theta_highbeta': 'θ/Hiβ',
                                    '4_alpha_beta': 'α/β',
                                    '5_alpha_highbeta': 'α/Hiβ',
                                    '6_beta_highbeta': 'β/Hiβ',
                                    '7_hightheta_lowalpha': 'Hiβ/Loα',
                                    '8_lowalpha_highalpha': 'Loα/Hiβ',
                                    '9_delta_theta': 'δ/θ',
                                    '10_delta_alpha': 'δ/α',
                                    '11_delta_beta': 'δ/β',
                                    '12_delta_highbeta': 'δ/Hiβ'
                                }

                                # 创建MNE Info对象
                                if not info and json_channel_names:
                                    try:
                                        import mne
                                        info = mne.create_info(json_channel_names, sfreq=256, ch_types='eeg')
                                        info.set_montage('standard_1020')
                                    except:
                                        info = None

                                # 遍历所有比率
                                for json_key, display_label in ratio_key_mapping.items():
                                    if json_key in ratios_dict:
                                        ratio_dict = ratios_dict[json_key]
                                        if ratio_dict and isinstance(ratio_dict, dict):
                                            # 将字典转换为数组（按通道顺序）
                                            ratio_data = []
                                            for ch_name in json_channel_names:
                                                ratio_data.append(float(ratio_dict.get(ch_name, 0.0)))

                                            if len(ratio_data) == len(json_channel_names) and len(ratio_data) > 0:
                                                ratio_array = np.array(ratio_data)

                                                band_vmin = float(np.min(ratio_array)) if ratio_array.size > 0 else 0.0
                                                band_vmax = float(np.max(ratio_array)) if ratio_array.size > 0 else 1.0
                                                if band_vmax <= band_vmin + 0.1:
                                                    band_vmax = band_vmin + 0.1

                                                # 生成地形图
                                                img_url = create_topography_image(
                                                    ratio_array,
                                                    info=info,
                                                    channel_names=json_channel_names,
                                                    vmin=band_vmin,
                                                    vmax=band_vmax,
                                                    title=display_label,
                                                    cmap=TOPO_COLORMAP
                                                )

                                                ratio_imgs_for_fullband.append({
                                                    "url": img_url,
                                                    "label": display_label,

                                                })


                    except Exception as e:
                        pass

                    if ratio_imgs_for_fullband:
                        full_band_item["power_ratios"] = {"images": ratio_imgs_for_fullband}
                    mock_algo_results["full_band_mapping_data"].append(full_band_item)
            except Exception as e:
                pass

            # 提取 Ratio Mapping 数据（仅当无 band_mapping 时为独立 Ratio Mapping 任务，每个任务独立一条）
            try:
                if hasattr(ar, 'ratio_mapping') and ar.ratio_mapping is not None and not (
                        hasattr(ar, 'band_mapping') and ar.band_mapping is not None):
                    ratio_mapping_result = ar.ratio_mapping

                    # 导入必要的函数
                    from .Analyze_report_pro import create_topography_image, VMIN, VMAX, TOPO_COLORMAP
                    import numpy as np

                    # 创建MNE Info对象用于生成地形图
                    try:
                        import mne
                        channel_names = ratio_mapping_result.channel_names if hasattr(ratio_mapping_result,
                                                                                      'channel_names') else []
                        if channel_names:
                            info = mne.create_info(channel_names, sfreq=256, ch_types='eeg')
                            info.set_montage('standard_1020')
                        else:
                            info = None
                    except Exception:
                        info = None
                        channel_names = ratio_mapping_result.channel_names if hasattr(ratio_mapping_result,
                                                                                      'channel_names') else []

                    # 定义12个比率的标签和对应的属性名
                    ratio_mappings = [
                        ('θ/α', 'theta_alpha'),
                        ('θ/β', 'theta_beta'),
                        ('θ/Hiβ', 'theta_highbeta'),
                        ('α/β', 'alpha_beta'),
                        ('α/Hiβ', 'alpha_highbeta'),
                        ('β/Hiβ', 'beta_highbeta'),
                        ('Hiβ/Loα', 'hightheta_lowalpha'),
                        ('Loα/Hiβ', 'lowalpha_highalpha'),
                        ('δ/θ', 'delta_theta'),
                        ('δ/α', 'delta_alpha'),
                        ('δ/β', 'delta_beta'),
                        ('δ/Hiβ', 'delta_highbeta')
                    ]

                    # 1. 生成功率比率地形图（左半区）
                    ratio_imgs = []

                    for label, attr_name in ratio_mappings:
                        if hasattr(ratio_mapping_result, attr_name):
                            ratio_dict = getattr(ratio_mapping_result, attr_name)
                            if ratio_dict and isinstance(ratio_dict, dict):
                                # 将字典转换为数组（按通道顺序）
                                ratio_data = []
                                for ch_name in channel_names:
                                    ratio_data.append(float(ratio_dict.get(ch_name, 0.0)))

                                if len(ratio_data) == len(channel_names) and len(ratio_data) > 0:
                                    ratio_array = np.array(ratio_data, dtype=float)

                                    # 测量值的真实区间
                                    real_band_vmin = float(np.min(ratio_array)) if ratio_array.size > 0 else 0.0
                                    real_band_vmax = float(np.max(ratio_array)) if ratio_array.size > 0 else 1.0
                                    if real_band_vmax <= real_band_vmin + 0.1:
                                        real_band_vmax = real_band_vmin + 0.1
                                    
                                    # 统一采用 16 色、0-70% 截断、每格 4.375% 的离散映射
                                    max_val = float(np.max(ratio_array)) if ratio_array.size > 0 else 1.0
                                    if max_val <= 0:
                                        max_val = 1.0
                                    percent = (ratio_array / max_val) * 100.0
                                    clamped = np.clip(percent, 0.0, 70.0)
                                    plot_ratio_array = np.floor(clamped / 4.375)
                                    plot_ratio_array = np.clip(plot_ratio_array, 0, 15).astype(float)
                                    band_vmin = 0.0
                                    band_vmax = 15.0



                                    # 生成地形图  # 生成功率比率图 颜色 在这里修改
                                    img_url = create_topography_image(
                                        plot_ratio_array,
                                        info=info,
                                        channel_names=channel_names,
                                        vmin=band_vmin,    
                                        vmax=band_vmax,  
                                        title=label,
                                        cmap=TOPO_COLORMAP
                                    )

                                    ratio_imgs.append({
                                        "url": img_url,
                                        "label": label,
                                        "vmin": real_band_vmin,
                                        "vmax": real_band_vmax, 
                                    })

                    # 2. 生成比率Z-Score地形图（右半区）
                    # 数据源改为 z_by_channel（接口调用保持不变，仅调整返回结果读取逻辑）
                    ratio_zscore_imgs = []
                    try:
                        import os
                        import json

                        z_channel_names = list(channel_names) if channel_names else []
                        z_by_channel = {}

                        # 先尝试从任务参数中直接读取 z_by_channel（exe 环境不依赖 JSON 更稳定）
                        task_params = _task_info.get("task_params", {}) if isinstance(_task_info, dict) else {}
                        if isinstance(task_params, dict):
                            direct_z = task_params.get("ratio_z_by_channel") or task_params.get("zscore_ratio_by_channel")
                            if isinstance(direct_z, dict) and direct_z:
                                z_by_channel = direct_z
                                try:
                                    QLLogging.log.info(
                                        f"[RatioZScore] z_by_channel from task_params, len={len(z_by_channel)}"
                                    )
                                except Exception:
                                    pass

                        # 再尝试读取返回结果目录中的 zscore 数据文件
                        json_output_dir = task_params.get("json_output_dir") if isinstance(task_params, dict) else None

                        possible_zscore_paths = []
                        if json_output_dir:
                            possible_zscore_paths.append(os.path.join(json_output_dir, "7_zscore_result.json"))

                        file_path = getattr(ar, 'file_path', '') if ar else ''
                        if file_path:
                            possible_zscore_paths.extend([
                                os.path.join(os.path.dirname(file_path), 'qeeg_output', '7_zscore_result.json'),
                                os.path.join(os.path.dirname(file_path), '7_zscore_result.json')
                            ])

                        possible_zscore_paths.extend([
                            os.path.join('qeeg_output', '7_zscore_result.json'),
                            os.path.join(os.path.dirname(__file__), 'qeeg_algorithm-main', 'qeeg_output',
                                         '7_zscore_result.json'),
                            '7_zscore_result.json'
                        ])

                        zscore_json_path = None
                        for path in possible_zscore_paths:
                            if os.path.exists(path):
                                zscore_json_path = path
                                break

                        # 打包环境下路径可能不同，这里打印出所有候选路径及实际命中路径，便于排查
                        try:
                            QLLogging.log.info(f"[RatioZScore] possible_zscore_paths={possible_zscore_paths}")
                            QLLogging.log.info(f"[RatioZScore] selected zscore_json_path={zscore_json_path}")
                        except Exception:
                            pass

                        if zscore_json_path:
                            with open(zscore_json_path, 'r', encoding='utf-8') as f:
                                zscore_data_json = json.load(f)

                            ratio_section = zscore_data_json.get('ratio', {}) if isinstance(zscore_data_json, dict) else {}
                            z_by_channel = ratio_section.get('z_by_channel', {}) if isinstance(ratio_section, dict) else {}
                            z_channel_names = ratio_section.get('channel_names', z_channel_names)

                            # 打印 ratio_section 的 key 以及 z_by_channel 的长度，确认 JSON 中是否包含比率 Z-Score
                            try:
                                if isinstance(ratio_section, dict):
                                    QLLogging.log.info(f"[RatioZScore] ratio_section keys={list(ratio_section.keys())}")
                                if isinstance(z_by_channel, dict):
                                    QLLogging.log.info(
                                        f"[RatioZScore] z_by_channel from JSON, len={len(z_by_channel)}"
                                    )
                            except Exception:
                                pass

                        # 文件中无数据时，回退尝试从对象属性读取
                        if not z_by_channel and hasattr(ratio_mapping_result, 'z_by_channel'):
                            z_by_channel = getattr(ratio_mapping_result, 'z_by_channel') or {}
                            # 打印从对象属性中获取的 z_by_channel 长度
                            try:
                                if isinstance(z_by_channel, dict):
                                    QLLogging.log.info(
                                        f"[RatioZScore] z_by_channel from ratio_mapping_result, len={len(z_by_channel)}"
                                    )
                            except Exception:
                                pass

                        # 最终 z_by_channel 的整体情况及一个示例（最多前三个通道），用于确认打包后是否为空
                        try:
                            if isinstance(z_by_channel, dict) and z_by_channel:
                                sample_items = list(z_by_channel.items())[:3]
                                QLLogging.log.info(
                                    f"[RatioZScore] final z_by_channel non-empty, len={len(z_by_channel)}, sample={sample_items}"
                                )
                            else:
                                QLLogging.log.info(
                                    f"[RatioZScore] final z_by_channel is empty or not dict: {type(z_by_channel)}"
                                )
                        except Exception:
                            pass

                        if z_by_channel and isinstance(z_by_channel, dict):
                            if (not z_channel_names) and channel_names:
                                z_channel_names = list(channel_names)
                            if not z_channel_names:
                                z_channel_names = list(z_by_channel.keys())

                            # 将 z_by_channel 转为 ratio_name -> {channel: value}
                            ratio_z_dict = {}
                            for ch_name, ratio_vals in z_by_channel.items():
                                if not isinstance(ratio_vals, dict):
                                    continue
                                for ratio_name, z_val in ratio_vals.items():
                                    if ratio_name not in ratio_z_dict:
                                        ratio_z_dict[ratio_name] = {}
                                    try:
                                        ratio_z_dict[ratio_name][ch_name] = float(z_val)
                                    except Exception:
                                        ratio_z_dict[ratio_name][ch_name] = 0.0

                            # 固定展示顺序（存在才展示）
                            ratio_z_label_mapping = [
                                ('theta_alpha', 'θ/α'),
                                ('theta_beta', 'θ/β'),
                                ('theta_highbeta', 'θ/Hiβ'),
                                ('alpha_beta', 'α/β'),
                                ('alpha_highbeta', 'α/Hiβ'),
                                ('beta_highbeta', 'β/Hiβ'),
                                ('hightheta_lowalpha', 'Hiβ/Loα'),
                                ('lowalpha_highalpha', 'Loα/Hiβ'),
                                ('delta_theta', 'δ/θ'),
                                ('delta_alpha', 'δ/α'),
                                ('delta_beta', 'δ/β'),
                                ('delta_highbeta', 'δ/Hiβ')
                            ]

                            for ratio_name, label in ratio_z_label_mapping:
                                if ratio_name not in ratio_z_dict:
                                    continue
                                ratio_dict = ratio_z_dict.get(ratio_name, {})
                                z_data = [float(ratio_dict.get(ch_name, 0.0)) for ch_name in z_channel_names]
                                if len(z_data) != len(z_channel_names) or len(z_data) == 0:
                                    continue

                                z_array = np.array(z_data)
                                img_url = create_topography_image(
                                    z_array,
                                    info=info,
                                    channel_names=z_channel_names,
                                    vmin=VMIN,
                                    vmax=VMAX,
                                    title=label,
                                    cmap=TOPO_COLORMAP
                                )

                                ratio_zscore_imgs.append({
                                    "url": img_url,
                                    "label": label
                                })
                    except Exception:
                        pass

                    ratio_item = {"task_name": task_name, "task_id": _task_key}
                    if ratio_imgs:
                        ratio_item["power_ratios"] = {"images": ratio_imgs}
                    if ratio_zscore_imgs:
                        ratio_item["ratio_zscore"] = {"images": ratio_zscore_imgs}
                    mock_algo_results["ratio_mapping_data"].append(ratio_item)

            except Exception as e:
                pass

            # 提取 FAA (Frontal Alpha Asymmetry) 数据（每个任务独立一条）
            try:
                if hasattr(ar, 'faa') and ar.faa is not None:
                    faa_result = ar.faa
                    mock_algo_results["faa_data"].append({
                        "task_name": task_name, "task_id": _task_key,
                        "faa_percentage": float(getattr(faa_result, 'faa_percentage', 0.0)),
                        "alpha_f3": float(getattr(faa_result, 'alpha_f3', 0.0)),
                        "alpha_f4": float(getattr(faa_result, 'alpha_f4', 0.0)),
                    })
            except Exception as e:
                pass

            # 提取 Alpha Ratio (EC/EO) 数据（每个任务独立一条）
            try:
                if hasattr(ar, 'alpha_ratio') and ar.alpha_ratio is not None:
                    alpha_ratio_result = ar.alpha_ratio
                    mock_algo_results["alpha_ratio_data"].append({
                        "task_name": task_name, "task_id": _task_key,
                        "alpha_ratio": float(getattr(alpha_ratio_result, 'ratio', 0.0)),
                        "alpha_power_closed": float(getattr(alpha_ratio_result, 'alpha_power_closed', 0.0)),
                        "alpha_power_open": float(getattr(alpha_ratio_result, 'alpha_power_open', 0.0)),
                    })
            except Exception as e:
                pass

        QLLogging.log.info(f"---------结束加载数据1-------------")

        self.mock_algo_results = mock_algo_results

        QLLogging.log.info(f"---------结束加载数据2-------------")

        progress = 80
        self.signal.emit([progress, "正在生成报告..."])
        emit_and_schedule(self.signal, progress + 1, 8, self.progressBar)
        if hasattr(self, 'progressBar_dialog') and self.progressBar_dialog is not None:
            # self.progressBar_dialog.label_progressBar.setText("正在生成报告...")
            self.update_label_signal.emit("正在生成报告...")

        progress = 90
        self.signal.emit([progress, "正在生成报告..."])
        emit_and_schedule(self.signal, progress + 1, 8, self.progressBar)

        progress = 100
        self.signal.emit([progress, "Analysis completed"])
        QLLogging.log.info(f"---------线程结束-------------")

    def plot_psd_matrix(self,
                    frequencies, psd_data, channel_names, psd,
                    freq_lim=(0, 45),
                    log_y=True,
                    figsize=(12, 7.5),
                    dpi=300,
                    out_dir="./psd_plots"):
        """
        绘制 PSD 通道矩阵图，每个通道生成一个包含 PSD 曲线和顶部两行表格的图片，
        并返回通道名到 Base64 图片的字典。
        """
        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
        plt.rcParams['axes.unicode_minus'] = False

        # 1. 加载并预处理数据
        frequencies = np.array(frequencies)
        psd_data = np.array(psd_data)
        n_channels = len(channel_names)
        psd_data = np.maximum(psd_data, 1e-20)
        mask = (frequencies >= freq_lim[0]) & (frequencies <= freq_lim[1])
        freqs_plot = frequencies[mask]

        band_definitions = [
            (1, 4, 'Delta','δ'), (4, 8, 'Theta', 'θ'), (8, 13, 'Alpha', 'α'),
            (12, 15, 'SMR', 'SMR'), (13, 30, 'Beta', 'β'),
            (21, 30, 'High_beta', 'β-h'), (30, 45, 'Gamma', 'γ'),
        ]
        band_colors = {
            'Delta': '#E1F5FE', 'Theta': '#E8F5E9', 'Alpha': '#FFF3E0',
            'SMR': '#FFEBEE', 'Beta': '#F3E5F5', 'High_beta': '#E0F7FA',
            'Gamma': '#ECFFD3'
        }

        result_dict = {}
        default_channels = ['Fp1', 'Fpz', 'Fp2', 'F7', 'F3', 'Fz', 'F4', 'F8',
                            'T3', 'C3', 'Cz', 'C4', 'T4', 'T5', 'P3', 'Pz',
                            'P4', 'T6', 'O1', 'Oz', 'O2']

        for idx, ch_name in enumerate(channel_names):
            if ch_name not in default_channels:
                continue

            # 画布尺寸计算
            if isinstance(figsize, (tuple, list)) and len(figsize) == 2:
                _side = max(float(figsize[0]), float(figsize[1]))
                _inch_w = (_side - 50.0 / dpi)
                _inch_h = (_side - 30.0 / dpi)
                square_figsize = (_inch_w, _inch_h)
            else:
                square_figsize = tuple([s * 1.3 for s in figsize])

            fig, ax = plt.subplots(figsize=square_figsize, dpi=dpi, facecolor='white')
            ax.set_facecolor('white')
            # 调整子图边距，使左右留白更对称且更紧凑
            fig.subplots_adjust(left=0.12, right=0.98, bottom=0.1, top=0.95)

            psd_row = psd_data[idx]
            psd_plot = psd_row[mask]
            psd_plot = np.maximum(psd_plot, 1e-20)
             # 先绘制曲线，以确定 y 轴范围
            if log_y:
                ax.semilogy(freqs_plot, psd_plot, color="steelblue", linewidth=3.2, zorder=5)
            else:
                ax.plot(freqs_plot, psd_plot, color="steelblue", linewidth=3.2, zorder=5)

            # PSD 报告页：y 轴上限定为 10^1，便于统一展示
            _ylo, _yhi = ax.get_ylim()
            ax.set_ylim(bottom=_ylo, top=1000.0)

            # 获取当前的 y 轴上限用于频段标签定位
            y_max = ax.get_ylim()[1]

            # 绘制频段阴影和标签（进一步下移）
            for start_freq, end_freq, band_name, s_band_name in band_definitions:
                if end_freq < freq_lim[0] or start_freq > freq_lim[1]:
                    continue
                ax.axvspan(start_freq, end_freq, color=band_colors[band_name], alpha=0.4, zorder=0)
                band_center = (start_freq + end_freq) / 2
                # ax.text(band_center, y_max * 0.88, s_band_name,
                #         ha='center', va='top', fontsize=30, fontweight='bold', color='#546E7A')

            # 获取频段功率值
            band_powers = psd['channels'][idx]['channel_values']

            # 去掉“单位”列，仅保留各频段数值
            header_row = ['δ', 'θ', 'α', 'SMR', 'β', 'β-h', 'γ']
            value_row = [
                f"{band_powers.get('delta', 0):.1f}",
                f"{band_powers.get('theta', 0):.1f}",
                f"{band_powers.get('alpha', 0):.1f}",
                f"{band_powers.get('smr', 0):.1f}",
                f"{band_powers.get('beta', 0):.1f}",
                f"{band_powers.get('high_beta', 0):.1f}",
                f"{band_powers.get('gamma', 0):.1f}",
            ]

            # 绘制表格，横向尽量铺满当前绘图区域
            table = ax.table(
                cellText=[header_row, value_row],
                loc='center',
                bbox=[0.04, 0.73, 0.96, 0.15],
                cellLoc='center',
                edges='closed'
            )
            table.auto_set_font_size(False)
            # 统一从原来的 32 号基础上整体放大 4
            base_fontsize = 32
            table.set_fontsize(base_fontsize + 4)

            for (i, j), cell in table.get_celld().items():
                cell.set_linewidth(0.8)
                if i == 0:
                    cell.set_facecolor('#f0f0f0')
                    cell.set_text_props(weight='normal', color='#2A87DB')
                else:
                    cell.set_facecolor('white')
                    cell.set_text_props(color='black')

            # 在右上角标注单位，替代表格中的“单位”列
            ax.text(
                0.98,
                0.98,
                '单位: μV²',
                transform=ax.transAxes,
                ha='right',
                va='top',
                fontsize=base_fontsize * 1.5,
                fontweight='bold',
                color='#2A87DB',
            )

            # 坐标轴标签
            ax.set_xlim(freq_lim)
            ax.set_xlabel("Frequency (Hz)", fontsize=30, fontweight='bold', color="black")

            y_label = "Relative Power" + (" [log scale]" if log_y else "")
            ax.set_ylabel(y_label, fontsize=32, fontweight='bold', color="black")

            # ===== 刻度设置：明确颜色、大小、方向，并加粗 =====
            # x 轴刻度线朝向 y 轴负向（向下），增加 pad 避免刻度线被数字遮挡
            ax.tick_params(axis='x', which='major', labelsize=27, direction='out',color='black',
                           length=9, width=2.0, labelcolor='black', pad=8,
                           bottom=True, top=False, labelbottom=True)
            ax.tick_params(axis='y', which='major', labelsize=27, direction='in',color='black',
                           length=9, width=2.0, labelcolor='black')
            fig.canvas.draw()  # 强制绘制，确保刻度标签对象存在
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_fontweight('bold')   # 设置为粗体

            # 坐标轴边框
            ax.spines['left'].set_color('black')
            ax.spines['bottom'].set_color('black')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            # 保存为 Base64
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=dpi, facecolor='white', transparent=False)
            buf.seek(0)
            encoded_string = base64.b64encode(buf.read()).decode('utf-8')
            img_base64_with_prefix = f"data:image/png;base64,{encoded_string}"
            buf.close()
            plt.close(fig)

            result_dict[ch_name] = img_base64_with_prefix
            QLLogging.log.info(f"已完成 {idx + 1}/{n_channels}：通道 {ch_name} 编码完成")

        QLLogging.log.info("所有通道图表Base64编码生成完成！")
        return result_dict

    def plot_psd_matrix_histogram_log_Relative(self,
                                               frequencies, psd_data, channel_names, psd,
                                               freq_lim=(0, 35),
                                               log_y=True,
                                               figsize=(12, 7.5),
                                               dpi=300,
                                               out_dir="./psd_plots"):
        """
        绘制 PSD 通道矩阵图，每个通道生成一个包含 PSD 曲线和顶部两行表格的图片，
        并返回通道名到 Base64 图片的字典。
        """
        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
        plt.rcParams['axes.unicode_minus'] = False

        # 1. 加载并预处理数据
        frequencies = np.array(frequencies)
        psd_data = np.array(psd_data)
        n_channels = len(channel_names)
        psd_data = np.maximum(psd_data, 1e-20)
        mask = (frequencies >= freq_lim[0]) & (frequencies <= freq_lim[1])
        freqs_plot = frequencies[mask]

        band_definitions = [
            (1, 4, 'Delta', 'δ'), (4, 8, 'Theta', 'θ'), (8, 13, 'Alpha', 'α'),
            (12, 15, 'SMR', 'SMR'), (13, 30, 'Beta', 'β'),
            (21, 30, 'High_beta', 'β-h'), (30, 45, 'Gamma', 'γ'),
        ]
        band_colors = {
            'Delta': '#E1F5FE', 'Theta': '#E8F5E9', 'Alpha': '#FFF3E0',
            'SMR': '#FFEBEE', 'Beta': '#F3E5F5', 'High_beta': '#E0F7FA',
            'Gamma': '#ECFFD3'
        }

        result_dict = {}
        default_channels = ['Fp1', 'Fpz', 'Fp2', 'F7', 'F3', 'Fz', 'F4', 'F8',
                            'T3', 'C3', 'Cz', 'C4', 'T4', 'T5', 'P3', 'Pz',
                            'P4', 'T6', 'O1', 'Oz', 'O2']

        for idx, ch_name in enumerate(channel_names):
            if ch_name not in default_channels:
                continue

            # 画布尺寸计算
            if isinstance(figsize, (tuple, list)) and len(figsize) == 2:
                _side = max(float(figsize[0]), float(figsize[1]))
                _inch_w = (_side - 50.0 / dpi)
                _inch_h = (_side - 30.0 / dpi)
                square_figsize = (_inch_w, _inch_h)
            else:
                square_figsize = tuple([s * 1.3 for s in figsize])

            fig, ax = plt.subplots(figsize=square_figsize, dpi=dpi, facecolor='white')
            ax.set_facecolor('white')
            # 调整子图边距，使左右留白更对称且更紧凑
            fig.subplots_adjust(left=0.12, right=0.98, bottom=0.1, top=0.95)

            psd_row = psd_data[idx]
            psd_plot = psd_row[mask]
            psd_plot = np.maximum(psd_plot, 1e-20)

            # 1. 生成0.5Hz间隔的目标频率点
            target_freqs = np.arange(freq_lim[0], freq_lim[1] + 0.5, 0.5)

            # 2. 对PSD数据进行插值，得到0.5Hz间隔对应的功率值
            psd_interp = np.interp(target_freqs, freqs_plot, psd_plot)

            # 3. 设置柱子宽度（略小于0.5，避免重叠）
            bar_width = 0.45

            # 4. 绘制柱状图
            ax.bar(target_freqs, psd_interp, width=bar_width, color="steelblue", edgecolor='white', zorder=5)

            # 5. 如果需要对数坐标，设置y轴为对数刻度
            if log_y:
                ax.set_yscale('log')

            # PSD 报告页：y 轴上限定为 10^1，便于统一展示
            _ylo, _yhi = ax.get_ylim()
            ax.set_ylim(bottom=_ylo, top=1000.0)

            # ================== 核心修改：设置x轴步长为2 ==================
            # 1. 生成从0到45、步长为2的x轴刻度
            ax.set_xticks(np.arange(freq_lim[0], freq_lim[1] + 2, 2))
            # 2. 确保x轴范围保持不变
            ax.set_xlim(freq_lim)
            # ============================================================

            # 获取当前的 y 轴上限用于频段标签定位
            y_max = ax.get_ylim()[1]

            # 绘制频段阴影和标签（进一步下移）
            for start_freq, end_freq, band_name, s_band_name in band_definitions:
                if end_freq < freq_lim[0] or start_freq > freq_lim[1]:
                    continue
                ax.axvspan(start_freq, end_freq, color=band_colors[band_name], alpha=0.4, zorder=0)
                band_center = (start_freq + end_freq) / 2
                # ax.text(band_center, y_max * 0.88, s_band_name,
                #         ha='center', va='top', fontsize=30, fontweight='bold', color='#546E7A')

            # 获取频段功率值
            band_powers = psd['channels'][idx]['channel_values']

            # 去掉“单位”列，仅保留各频段数值
            header_row = ['δ', 'θ', 'α', 'β', 'SMR', 'β-h', 'γ']
            value_row = [
                f"{band_powers.get('delta', 0):.1f}",
                f"{band_powers.get('theta', 0):.1f}",
                f"{band_powers.get('alpha', 0):.1f}",
                f"{band_powers.get('beta', 0):.1f}",
                f"{band_powers.get('smr', 0):.1f}",
                f"{band_powers.get('high_beta', 0):.1f}",
                f"{band_powers.get('gamma', 0):.1f}",
            ]

            # 绘制表格，横向尽量铺满当前绘图区域
            table = ax.table(
                cellText=[header_row, value_row],
                loc='center',
                bbox=[0.04, 0.73, 0.96, 0.15],
                cellLoc='center',
                edges='closed'
            )
            table.auto_set_font_size(False)
            base_fontsize = 32
            table.set_fontsize(base_fontsize + 4)

            for (i, j), cell in table.get_celld().items():
                cell.set_linewidth(0.8)
                if i == 0:
                    cell.set_facecolor('#f0f0f0')
                    cell.set_text_props(weight='normal', color='#2A87DB')
                else:
                    cell.set_facecolor('white')
                    cell.set_text_props(color='black')

            # 在右上角标注单位，替代表格中的“单位”列
            ax.text(
                0.98,
                0.98,
                '单位: μV²',
                transform=ax.transAxes,
                ha='right',
                va='top',
                fontsize=base_fontsize * 1.5,
                fontweight='bold',
                color='#2A87DB',
            )
            ax.set_xlim(freq_lim)
            ax.set_xlabel("Frequency (Hz)", fontsize=18, fontweight='bold', color="black")

            y_label = "Relative Power" + (" [log scale]" if log_y else "")
            ax.set_ylabel(y_label, fontsize=32, fontweight='bold', color="black")

            # ===== 刻度设置：明确颜色、大小、方向，并加粗 =====
            # x 轴刻度线朝向 y 轴负向（向下），增加 pad 避免刻度线被数字遮挡
            ax.tick_params(axis='x', which='major', labelsize=27, direction='out',
                           length=9, width=2.0, labelcolor='black', pad=8,
                           bottom=True, top=False, labelbottom=True)
            ax.tick_params(axis='y', which='major', labelsize=27, direction='in',
                           length=9, width=2.0, labelcolor='black')
            fig.canvas.draw()  # 强制绘制，确保刻度标签对象存在
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_fontweight('bold')  # 设置为粗体

            # 坐标轴边框
            ax.spines['left'].set_color('black')
            ax.spines['bottom'].set_color('black')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            # 保存为 Base64
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=dpi, facecolor='white', transparent=False)
            buf.seek(0)
            encoded_string = base64.b64encode(buf.read()).decode('utf-8')
            img_base64_with_prefix = f"data:image/png;base64,{encoded_string}"
            buf.close()
            plt.close(fig)

            result_dict[ch_name] = img_base64_with_prefix

        return result_dict

    def plot_psd_matrix_histogram_Relative(self,
                                           frequencies, psd_data, channel_names, psd,
                                           freq_lim=(0, 35),
                                           log_y=True,
                                           figsize=(12, 7.5),
                                           dpi=300,
                                           out_dir="./psd_plots"):
        """
        绘制 PSD 通道矩阵图，每个通道生成一个包含 PSD 曲线和顶部两行表格的图片，
        并返回通道名到 Base64 图片的字典。
        """
        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
        plt.rcParams['axes.unicode_minus'] = False

        # 1. 加载并预处理数据
        frequencies = np.array(frequencies)
        psd_data = np.array(psd_data)
        n_channels = len(channel_names)
        psd_data = np.maximum(psd_data, 1e-20)
        mask = (frequencies >= freq_lim[0]) & (frequencies <= freq_lim[1])
        freqs_plot = frequencies[mask]

        band_definitions = [
            (1, 4, 'Delta', 'δ'), (4, 8, 'Theta', 'θ'), (8, 13, 'Alpha', 'α'),
            (12, 15, 'SMR', 'SMR'), (13, 30, 'Beta', 'β'),
            (21, 30, 'High_beta', 'β-h'), (30, 45, 'Gamma', 'γ'),
        ]
        band_colors = {
            'Delta': '#BADEF1', 'Theta': '#BFD8B1', 'Alpha': '#F6E2B7',
            'SMR': '#FDD1B5', 'Beta': '#F0D0E0', 'High_beta': '#D3D3FF',
            'Gamma': '#B1D5C1'
        }

        result_dict = {}
        default_channels = ['Fp1', 'Fpz', 'Fp2', 'F7', 'F3', 'Fz', 'F4', 'F8',
                            'T3', 'C3', 'Cz', 'C4', 'T4', 'T5', 'P3', 'Pz',
                            'P4', 'T6', 'O1', 'Oz', 'O2']

        for idx, ch_name in enumerate(channel_names):
            if ch_name not in default_channels:
                continue

            # 画布尺寸计算
            if isinstance(figsize, (tuple, list)) and len(figsize) == 2:
                _side = max(float(figsize[0]), float(figsize[1]))
                _inch_w = (_side - 50.0 / dpi)
                _inch_h = (_side - 30.0 / dpi)
                square_figsize = (_inch_w, _inch_h)
            else:
                square_figsize = tuple([s * 1.3 for s in figsize])

            fig, ax = plt.subplots(figsize=square_figsize, dpi=dpi, facecolor='white')
            ax.set_facecolor('white')
            # 调整子图边距，使左右留白更对称且更紧凑
            fig.subplots_adjust(left=0.12, right=0.98, bottom=0.1, top=0.95)

            psd_row = psd_data[idx]
            psd_plot = psd_row[mask]
            psd_plot = np.maximum(psd_plot, 1e-20)

            # 1. 生成0.5Hz间隔的目标频率点
            target_freqs = np.arange(freq_lim[0], freq_lim[1] + 0.5, 0.5)

            # 2. 对PSD数据进行插值，得到0.5Hz间隔对应的功率值
            psd_interp = np.interp(target_freqs, freqs_plot, psd_plot)

            # 3. 设置柱子宽度（略小于0.5，避免重叠）
            bar_width = 0.45

            # 4. 绘制柱状图
            ax.bar(target_freqs, psd_interp, width=bar_width, color="steelblue", edgecolor='white', zorder=5)

            # ================== 核心修改：设置x轴步长为4 ==================
            # 1. 生成从0到36、步长为4的x轴刻度值（覆盖0-35范围）
            xticks = np.arange(0, 37, 4)
            ax.set_xticks(xticks)
            ax.set_xticklabels([str(x) for x in xticks], fontsize=30, fontweight='bold')
            ax.set_xlim(freq_lim)
            # ============================================================

            # ================== 核心修改开始：设置y轴为0-1，步长0.1 ==================
            # 1. 固定y轴范围为0到1
            ax.set_ylim(0, 1.2)
            # 2. 设置y轴刻度，从0到1，步长0.1
            ax.set_yticks(np.arange(0, 1.3, 0.1))
            # ================== 核心修改结束 ==================

            # 获取当前的 y 轴上限用于频段标签定位
            y_max = ax.get_ylim()[1]

            # 绘制频段阴影和标签（进一步下移）
            for start_freq, end_freq, band_name, s_band_name in band_definitions:
                if end_freq < freq_lim[0] or start_freq > freq_lim[1]:
                    continue
                ax.axvspan(start_freq, end_freq, color=band_colors[band_name], alpha=0.4, zorder=0)
                band_center = (start_freq + end_freq) / 2
                # ax.text(band_center, y_max * 0.88, s_band_name,
                #         ha='center', va='top', fontsize=30, fontweight='bold', color='#546E7A')

            # 获取频段功率值
            band_powers = psd['channels'][idx]['channel_values']

            # 去掉“单位”列，仅保留各频段数值
            header_row = ['δ', 'θ', 'α', 'SMR', 'β', 'β-h', 'γ']
            value_row = [
                f"{band_powers.get('delta', 0):.1f}",
                f"{band_powers.get('theta', 0):.1f}",
                f"{band_powers.get('alpha', 0):.1f}",
                f"{band_powers.get('smr', 0):.1f}",
                f"{band_powers.get('beta', 0):.1f}",
                f"{band_powers.get('high_beta', 0):.1f}",
                f"{band_powers.get('gamma', 0):.1f}",
            ]

            # 绘制表格，横向尽量铺满当前绘图区域
            table = ax.table(
                cellText=[header_row, value_row],
                loc='center',
                bbox=[0.04, 0.73, 0.96, 0.15],
                cellLoc='center',
                edges='closed'
            )
            table.auto_set_font_size(False)
            base_fontsize = 32
            table.set_fontsize(base_fontsize + 4)

            for (i, j), cell in table.get_celld().items():
                cell.set_linewidth(0.8)
                if i == 0:
                    cell.set_facecolor('#f0f0f0')
                    cell.set_text_props(weight='normal', color='#2A87DB')
                else:
                    cell.set_facecolor('white')
                    cell.set_text_props(color='black')
            # 在表格上方、彩色区域与图片上边框之间的留白处显示通道名（字号与表格标签一致）
            table_fontsize = base_fontsize + 4
            fig.text(
                0.5,
                0.955,
                f'channel：{ch_name}',
                transform=fig.transFigure,
                ha='center',
                va='bottom',
                fontsize=table_fontsize,
                fontweight='bold',
                color='black',
                    )


            # 在右上角标注单位，替代表格中的“单位”列
            ax.text(
                0.98,
                0.98,
                '单位: μV²',
                transform=ax.transAxes,
                ha='right',
                va='top',
                fontsize=base_fontsize * 1.5,
                fontweight='bold',
                color='#2A87DB',
            )
            ax.set_xlim(freq_lim)
            ax.set_xlabel("Frequency (Hz)", fontsize=30, fontweight='bold', color="black")

            y_label = "Relative Power"
            ax.set_ylabel(y_label, fontsize=32, fontweight='bold', color="black")

            # ===== 刻度设置：明确颜色、大小、方向，并加粗 =====
            # x 轴刻度线朝向 y 轴负向（向下），增加 pad 避免刻度线被数字遮挡
            ax.tick_params(axis='x', which='major', labelsize=27, direction='out',
                           length=9, width=2.0, labelcolor='black', pad=8,
                           bottom=True, top=False, labelbottom=True)
            ax.tick_params(axis='y', which='major', labelsize=27, direction='in',
                           length=9, width=2.0, labelcolor='black')
            fig.canvas.draw()  # 强制绘制，确保刻度标签对象存在
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_fontweight('bold')  # 设置为粗体

            # 坐标轴边框
            ax.spines['left'].set_color('black')
            ax.spines['bottom'].set_color('black')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            # 保存为 Base64
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=dpi, facecolor='white', transparent=False)
            buf.seek(0)
            encoded_string = base64.b64encode(buf.read()).decode('utf-8')
            img_base64_with_prefix = f"data:image/png;base64,{encoded_string}"
            buf.close()
            plt.close(fig)

            result_dict[ch_name] = img_base64_with_prefix

        return result_dict

    def plot_psd_matrix_histogram_log_Absolute(self,
                                               frequencies, psd_data, channel_names, psd,
                                               freq_lim=(0, 35),
                                               log_y=True,
                                               figsize=(12, 7.5),
                                               dpi=300,
                                               out_dir="./psd_plots"):
        """
        绘制 PSD 通道矩阵图，每个通道生成一个包含 PSD 曲线和顶部两行表格的图片，
        并返回通道名到 Base64 图片的字典。
        """
        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
        plt.rcParams['axes.unicode_minus'] = False

        # 1. 加载并预处理数据
        frequencies = np.array(frequencies)
        psd_data = np.array(psd_data)
        n_channels = len(channel_names)
        psd_data = np.maximum(psd_data, 1e-20)
        mask = (frequencies >= freq_lim[0]) & (frequencies <= freq_lim[1])
        freqs_plot = frequencies[mask]

        band_definitions = [
            (1, 4, 'Delta', 'δ'), (4, 8, 'Theta', 'θ'), (8, 13, 'Alpha', 'α'),
            (12, 15, 'SMR', 'SMR'), (13, 30, 'Beta', 'β'),
            (21, 30, 'High_beta', 'β-h'), (30, 45, 'Gamma', 'γ'),
        ]
        band_colors = {
            'Delta': '#E1F5FE', 'Theta': '#E8F5E9', 'Alpha': '#FFF3E0',
            'SMR': '#FFEBEE', 'Beta': '#F3E5F5', 'High_beta': '#E0F7FA',
            'Gamma': '#ECFFD3'
        }

        result_dict = {}
        default_channels = ['Fp1', 'Fpz', 'Fp2', 'F7', 'F3', 'Fz', 'F4', 'F8',
                            'T3', 'C3', 'Cz', 'C4', 'T4', 'T5', 'P3', 'Pz',
                            'P4', 'T6', 'O1', 'Oz', 'O2']

        for idx, ch_name in enumerate(channel_names):
            if ch_name not in default_channels:
                continue

            # 画布尺寸计算
            if isinstance(figsize, (tuple, list)) and len(figsize) == 2:
                _side = max(float(figsize[0]), float(figsize[1]))
                _inch_w = (_side - 50.0 / dpi)
                _inch_h = (_side - 30.0 / dpi)
                square_figsize = (_inch_w, _inch_h)
            else:
                square_figsize = tuple([s * 1.3 for s in figsize])

            fig, ax = plt.subplots(figsize=square_figsize, dpi=dpi, facecolor='white')
            ax.set_facecolor('white')
            # 调整子图边距，使左右留白更对称且更紧凑
            fig.subplots_adjust(left=0.12, right=0.98, bottom=0.1, top=0.95)

            psd_row = psd_data[idx]
            psd_plot = psd_row[mask]
            psd_plot = np.maximum(psd_plot, 1e-20)

            # 1. 生成0.5Hz间隔的目标频率点
            target_freqs = np.arange(freq_lim[0], freq_lim[1] + 0.5, 0.5)

            # 2. 对PSD数据进行插值，得到0.5Hz间隔对应的功率值
            psd_interp = np.interp(target_freqs, freqs_plot, psd_plot)

            # 3. 设置柱子宽度（略小于0.5，避免重叠）
            bar_width = 0.45

            # 4. 绘制柱状图
            ax.bar(target_freqs, psd_interp, width=bar_width, color="steelblue", edgecolor='white', zorder=5)

            # 5. 如果需要对数坐标，设置y轴为对数刻度
            if log_y:
                ax.set_yscale('log')

            # PSD 报告页：y 轴上限定为 10^1，便于统一展示
            _ylo, _yhi = ax.get_ylim()
            ax.set_ylim(bottom=_ylo, top=1000.0)

            # ================== 核心修改：设置x轴步长为2 ==================
            # 1. 生成从0到45、步长为2的x轴刻度
            ax.set_xticks(np.arange(freq_lim[0], freq_lim[1] + 2, 2))
            # 2. 确保x轴范围保持不变
            ax.set_xlim(freq_lim)
            # ============================================================

            # 获取当前的 y 轴上限用于频段标签定位
            y_max = ax.get_ylim()[1]

            # 绘制频段阴影和标签（进一步下移）
            for start_freq, end_freq, band_name, s_band_name in band_definitions:
                if end_freq < freq_lim[0] or start_freq > freq_lim[1]:
                    continue
                ax.axvspan(start_freq, end_freq, color=band_colors[band_name], alpha=0.4, zorder=0)
                band_center = (start_freq + end_freq) / 2
                # ax.text(band_center, y_max * 0.88, s_band_name,
                #         ha='center', va='top', fontsize=30, fontweight='bold', color='#546E7A')

            # 获取频段功率值
            band_powers = psd['channels'][idx]['channel_values']

            # 去掉“单位”列，仅保留各频段数值
            header_row = ['δ', 'θ', 'α', 'β', 'SMR', 'β-h', 'γ']
            value_row = [
                f"{band_powers.get('delta', 0):.1f}",
                f"{band_powers.get('theta', 0):.1f}",
                f"{band_powers.get('alpha', 0):.1f}",
                f"{band_powers.get('beta', 0):.1f}",
                f"{band_powers.get('smr', 0):.1f}",
                f"{band_powers.get('high_beta', 0):.1f}",
                f"{band_powers.get('gamma', 0):.1f}",
            ]

            # 绘制表格，横向尽量铺满当前绘图区域
            table = ax.table(
                cellText=[header_row, value_row],
                loc='center',
                bbox=[0.04, 0.73, 0.96, 0.15],
                cellLoc='center',
                edges='closed'
            )
            table.auto_set_font_size(False)
            base_fontsize = 32
            table.set_fontsize(base_fontsize + 4)

            for (i, j), cell in table.get_celld().items():
                cell.set_linewidth(0.8)
                if i == 0:
                    cell.set_facecolor('#f0f0f0')
                    cell.set_text_props(weight='normal', color='#2A87DB')
                else:
                    cell.set_facecolor('white')
                    cell.set_text_props(color='black')

            # 在右上角标注单位，替代表格中的“单位”列
            ax.text(
                0.98,
                0.98,
                '单位: μV²',
                transform=ax.transAxes,
                ha='right',
                va='top',
                fontsize=base_fontsize * 1.5,
                fontweight='bold',
                color='#2A87DB',
            )
            ax.set_xlim(freq_lim)
            ax.set_xlabel("Frequency (Hz)", fontsize=18, fontweight='bold', color="black")

            y_label = "Absolute Power" + (" [log scale]" if log_y else "")
            ax.set_ylabel(y_label, fontsize=32, fontweight='bold', color="black")

            # ===== 刻度设置：明确颜色、大小、方向，并加粗 =====
            # x 轴刻度线朝向 y 轴负向（向下），增加 pad 避免刻度线被数字遮挡
            ax.tick_params(axis='x', which='major', labelsize=27, direction='out',
                           length=9, width=2.0, labelcolor='black', pad=8,
                           bottom=True, top=False, labelbottom=True)
            ax.tick_params(axis='y', which='major', labelsize=27, direction='in',
                           length=9, width=2.0, labelcolor='black')
            fig.canvas.draw()  # 强制绘制，确保刻度标签对象存在
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_fontweight('bold')  # 设置为粗体

            # 坐标轴边框
            ax.spines['left'].set_color('black')
            ax.spines['bottom'].set_color('black')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            # 保存为 Base64
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=dpi, facecolor='white', transparent=False)
            buf.seek(0)
            encoded_string = base64.b64encode(buf.read()).decode('utf-8')
            img_base64_with_prefix = f"data:image/png;base64,{encoded_string}"
            buf.close()
            plt.close(fig)

            result_dict[ch_name] = img_base64_with_prefix

        return result_dict

    def plot_psd_matrix_histogram_Absolute(self,
                                           frequencies, psd_data, channel_names, psd,
                                           freq_lim=(0, 35),
                                           log_y=True,
                                           figsize=(12, 7.5),
                                           dpi=300,
                                           out_dir="./psd_plots"):
        """
        绘制 PSD 通道矩阵图，每个通道生成一个包含 PSD 曲线和顶部两行表格的图片，
        并返回通道名到 Base64 图片的字典。
        """
        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
        plt.rcParams['axes.unicode_minus'] = False

        # 1. 加载并预处理数据
        frequencies = np.array(frequencies)
        psd_data = np.array(psd_data)
        n_channels = len(channel_names)
        psd_data = np.maximum(psd_data, 1e-20)
        mask = (frequencies >= freq_lim[0]) & (frequencies <= freq_lim[1])
        freqs_plot = frequencies[mask]

        band_definitions = [
            (1, 4, 'Delta', 'δ'), (4, 8, 'Theta', 'θ'), (8, 13, 'Alpha', 'α'),
            (12, 15, 'SMR', 'SMR'), (13, 30, 'Beta', 'β'),
            (21, 30, 'High_beta', 'β-h'), (30, 45, 'Gamma', 'γ'),
        ]
        band_colors = {
            'Delta': '#E1F5FE', 'Theta': '#E8F5E9', 'Alpha': '#FFF3E0',
            'SMR': '#FFEBEE', 'Beta': '#F3E5F5', 'High_beta': '#E0F7FA',
            'Gamma': '#ECFFD3'
        }

        result_dict = {}
        default_channels = ['Fp1', 'Fpz', 'Fp2', 'F7', 'F3', 'Fz', 'F4', 'F8',
                            'T3', 'C3', 'Cz', 'C4', 'T4', 'T5', 'P3', 'Pz',
                            'P4', 'T6', 'O1', 'Oz', 'O2']

        for idx, ch_name in enumerate(channel_names):
            if ch_name not in default_channels:
                continue

            # 画布尺寸计算
            if isinstance(figsize, (tuple, list)) and len(figsize) == 2:
                _side = max(float(figsize[0]), float(figsize[1]))
                _inch_w = (_side - 50.0 / dpi)
                _inch_h = (_side - 30.0 / dpi)
                square_figsize = (_inch_w, _inch_h)
            else:
                square_figsize = tuple([s * 1.3 for s in figsize])

            fig, ax = plt.subplots(figsize=square_figsize, dpi=dpi, facecolor='white')
            ax.set_facecolor('white')
            # 调整子图边距，使左右留白更对称
            fig.subplots_adjust(left=0.12, right=0.88, bottom=0.1, top=0.95)

            psd_row = psd_data[idx]
            psd_plot = psd_row[mask]
            psd_plot = np.maximum(psd_plot, 1e-20)

            # 1. 生成0.5Hz间隔的目标频率点
            target_freqs = np.arange(freq_lim[0], freq_lim[1] + 0.5, 0.5)

            # 2. 对PSD数据进行插值，得到0.5Hz间隔对应的功率值
            psd_interp = np.interp(target_freqs, freqs_plot, psd_plot)

            # 3. 设置柱子宽度（略小于0.5，避免重叠）
            bar_width = 0.45

            # 4. 绘制柱状图
            ax.bar(target_freqs, psd_interp, width=bar_width, color="steelblue", edgecolor='white', zorder=5)

            # ================== 核心修改：设置x轴步长为2 ==================
            # 1. 生成从0到45、步长为2的x轴刻度
            ax.set_xticks(np.arange(freq_lim[0], freq_lim[1] + 2, 2))
            # 2. 确保x轴范围保持不变
            ax.set_xlim(freq_lim)
            # ============================================================

            # ================== 核心修改开始：设置y轴为0-1，步长0.1 ==================
            # 1. 固定y轴范围为0到1
            ax.set_ylim(0, 1.2)
            # 2. 设置y轴刻度，从0到1，步长0.1
            ax.set_yticks(np.arange(0, 1.3, 0.1))
            # ================== 核心修改结束 ==================

            # 获取当前的 y 轴上限用于频段标签定位
            y_max = ax.get_ylim()[1]

            # 绘制频段阴影和标签（进一步下移）
            for start_freq, end_freq, band_name, s_band_name in band_definitions:
                if end_freq < freq_lim[0] or start_freq > freq_lim[1]:
                    continue
                ax.axvspan(start_freq, end_freq, color=band_colors[band_name], alpha=0.4, zorder=0)
                band_center = (start_freq + end_freq) / 2
                # ax.text(band_center, y_max * 0.88, s_band_name,
                #         ha='center', va='top', fontsize=30, fontweight='bold', color='#546E7A')

            # 获取频段功率值
            band_powers = psd['channels'][idx]['channel_values']

            # 去掉“单位”列，仅保留各频段数值
            header_row = ['δ', 'θ', 'α', 'β', 'SMR', 'β-h', 'γ']
            value_row = [
                f"{band_powers.get('delta', 0):.1f}",
                f"{band_powers.get('theta', 0):.1f}",
                f"{band_powers.get('alpha', 0):.1f}",
                f"{band_powers.get('beta', 0):.1f}",
                f"{band_powers.get('smr', 0):.1f}",
                f"{band_powers.get('high_beta', 0):.1f}",
                f"{band_powers.get('gamma', 0):.1f}",
            ]

            # 绘制表格，横向尽量铺满当前绘图区域
            table = ax.table(
                cellText=[header_row, value_row],
                loc='center',
                bbox=[0.04, 0.73, 0.96, 0.15],
                cellLoc='center',
                edges='closed'
            )
            table.auto_set_font_size(False)
            base_fontsize = 32
            table.set_fontsize(base_fontsize + 4)

            for (i, j), cell in table.get_celld().items():
                cell.set_linewidth(0.8)
                if i == 0:
                    cell.set_facecolor('#f0f0f0')
                    cell.set_text_props(weight='normal', color='#2A87DB')
                else:
                    cell.set_facecolor('white')
                    cell.set_text_props(color='black')

            # 在右上角标注单位，替代表格中的“单位”列
            ax.text(
                0.98,
                0.98,
                '单位: μV²',
                transform=ax.transAxes,
                ha='right',
                va='top',
                fontsize=base_fontsize * 1.5,
                fontweight='bold',
                color='#2A87DB',
            )
            ax.set_xlim(freq_lim)
            ax.set_xlabel("Frequency (Hz)", fontsize=30, fontweight='bold', color="black")

            y_label = "Absolute Power"
            ax.set_ylabel(y_label, fontsize=32, fontweight='bold', color="black")

            # ===== 刻度设置：明确颜色、大小、方向，并加粗 =====
            # x 轴刻度线朝向 y 轴负向（向下），增加 pad 避免刻度线被数字遮挡
            print("这是图像刻度线设置")
            ax.tick_params(axis='x', which='major', labelsize=27, direction='out',
                           length=9, width=2.0, labelcolor='black', pad=8,
                           bottom=True, top=False, labelbottom=True)
            ax.tick_params(axis='y', which='major', labelsize=27, direction='in',
                           length=9, width=2.0, labelcolor='black')
            fig.canvas.draw()  # 强制绘制，确保刻度标签对象存在
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_fontweight('bold')  # 设置为粗体

            # 坐标轴边框
            ax.spines['left'].set_color('black')
            ax.spines['bottom'].set_color('black')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            # 保存为 Base64
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=dpi, facecolor='white', transparent=False)
            buf.seek(0)
            encoded_string = base64.b64encode(buf.read()).decode('utf-8')
            img_base64_with_prefix = f"data:image/png;base64,{encoded_string}"
            buf.close()
            plt.close(fig)

            result_dict[ch_name] = img_base64_with_prefix

        return result_dict

class HTMLReportPage(QWidget):
    """报告生成，显示HTML文件"""

    def __init__(self, page_title, html_path=None, parent=None):
        super().__init__(parent)
        self.page_title = page_title
        self.html_path = html_path
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        if self.html_path:
            if os.path.exists(self.html_path):
                # 创建WebEngineView来显示HTML
                from PyQt5.QtWebEngineWidgets import QWebEngineView
                from PyQt5.QtCore import QUrl
                
                self.browser = QWebEngineView()
                self.browser.loadFinished.connect(self._on_html_loaded)
                self.browser.setUrl(QUrl.fromLocalFile(self.html_path))
                
                # 创建滚动区域
                self.scroll_area = QScrollArea()
                self.scroll_area.setWidgetResizable(True)
                self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                self.scroll_area.setStyleSheet(ControlStyle.get_scrollbar_style())
                
                self.scroll_area.setWidget(self.browser)
                layout.addWidget(self.scroll_area)

                self.btn_save = QPushButton("打印 / 保存为 PDF")
                self.btn_save.setFixedHeight(40)
                # 尝试设置打印机图标（如果系统支持）
                try:
                    icon = QIcon.fromTheme("document-print")
                    if icon.isNull():
                        # 如果没有系统图标，尝试使用Unicode字符
                        self.btn_save.setText("🖨️ 打印 / 保存为 PDF")
                    else:
                        self.btn_save.setIcon(icon)
                        self.btn_save.setIconSize(QSize(20, 20))
                except:
                    # 如果图标设置失败，使用Unicode字符
                    self.btn_save.setText("🖨️ 打印 / 保存为 PDF")
                # 设置深色背景、白色文字、圆角、阴影的样式
                self.btn_save.setStyleSheet("""
                            QPushButton {
                                background-color: #1a1a1a;
                                color: #FFFFFF;
                                border: none;
                                border-radius: 12px;
                                padding: 10px 24px;
                                font-family: HarmonyOS Sans SC, HarmonyOS Sans SC;
                                font-weight: 500;
                                font-size: 16px;
                                text-align: center;
                            }
                            QPushButton:hover {
                                background-color: #2a2a2a;
                            }
                            QPushButton:pressed {
                                background-color: #0a0a0a;
                            }
                        """)
                self.browser.page().pdfPrintingFinished.connect(self._on_pdf_printing_finished)
                self.btn_save.clicked.connect(self.handle_save_pdf)
                layout.addWidget(self.btn_save)

            else:
                self.show_error(f"⚠ HTML文件不存在！\n路径：{self.html_path}")
        else:
            self.show_error("⚠ HTML文件路径为空！")

    def _on_html_loaded(self, ok):
        """HTML加载完成后，隐藏编辑用的UI元素（保存按钮、编辑边框）"""
        if not ok:
            return
        hide_js = """
        (function() {
            var btn = document.getElementById('save-btn');
            if (btn) btn.style.display = 'none';
            var editor = document.getElementById('assessment-text-editor');
            if (editor) {
                editor.style.border = 'none';
                editor.contentEditable = 'false';
            }
        })()
        """
        self.browser.page().runJavaScript(hide_js)

    def handle_save_pdf(self):
        """处理PDF保存/打印功能"""
        if not self.html_path or not os.path.exists(self.html_path):
            self.show_error("原始HTML文件不存在，无法保存！")
            return

        try:
            filename = os.path.basename(self.html_path)
            basename_without_ext = os.path.splitext(filename)[0]

            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            path, _ = QFileDialog.getSaveFileName(
                self,
                "保存PDF文件",
                os.path.join(desktop_path, basename_without_ext),
                "PDF Files (*.pdf);;All Files (*)"
            )

            if not path:
                return

            self._pending_pdf_path = path

            check_js = """
            (function() {
                var editor = document.getElementById('assessment-text-editor');
                if (!editor) return JSON.stringify({exists: false});
                var saved = window._assessmentSaved || false;
                return JSON.stringify({exists: true, saved: saved});
            })()
            """
            self.browser.page().runJavaScript(check_js, lambda result: self._on_check_assessment_before_pdf(result, path))

        except Exception as e:
            self.show_error(f"保存失败：{str(e)}")

    def _on_check_assessment_before_pdf(self, result, path):
        """检查评论保存状态后决定是否继续导出 PDF"""
        import json as _json
        try:
            info = _json.loads(result) if isinstance(result, str) else (result or {})
        except Exception:
            info = {}

        if info.get('exists') and not info.get('saved'):
            reply = QMessageBox.question(
                self,
                "评论未保存",
                "综合评估内容尚未点击「保存评论」。\n\n"
                "• 点击「是」：丢弃未保存的评论，直接导出 PDF\n"
                "• 点击「否」：返回先保存评论",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                self._pending_pdf_path = None
                return

            reset_js = """
            (function() {
                var editor = document.getElementById('assessment-text-editor');
                if (editor) {
                    editor.innerHTML = '<p style="color: #31373D; font-style: italic; margin: 0;">请在此输入医生的综合评估和建议...</p>';
                    editor.contentEditable = 'false';
                }
                var btn = document.getElementById('save-btn');
                if (btn) { btn.style.display = 'none'; }
            })()
            """
            self.browser.page().runJavaScript(reset_js, lambda _: self._do_print_to_pdf(path))
            return

        if info.get('exists') and info.get('saved'):
            self._sync_assessment_to_html_then_print(path)
        else:
            self._do_print_to_pdf(path)

    def _sync_assessment_to_html_then_print(self, path):
        """将已保存的评论内容回写到磁盘 HTML 文件，再导出 PDF"""
        fetch_js = """
        (function() {
            var editor = document.getElementById('assessment-text-editor');
            return editor ? editor.innerHTML : '';
        })()
        """
        self.browser.page().runJavaScript(fetch_js, lambda content: self._write_assessment_and_print(content, path))

    def _write_assessment_and_print(self, content, path):
        """将评论内容写入磁盘 HTML 文件"""
        if content and self.html_path and os.path.exists(self.html_path):
            try:
                import re
                with open(self.html_path, 'r', encoding='utf-8') as f:
                    full_html = f.read()
                pattern = r'(<div[^>]*id="assessment-text-editor"[^>]*>)([\s\S]*?)(</div>\s*<div[^>]*>\s*<button\s+id="save-btn")'
                new_html = re.sub(pattern, lambda m: m.group(1) + content + m.group(3), full_html, count=1)
                with open(self.html_path, 'w', encoding='utf-8') as f:
                    f.write(new_html)
            except Exception as e:
                print(f"回写评论到HTML失败: {e}")
        self._do_print_to_pdf(path)

    def _do_print_to_pdf(self, path):
        """隐藏UI元素后执行 printToPdf"""
        hide_ui_js = """
        (function() {
            var btn = document.getElementById('save-btn');
            if (btn) btn.style.display = 'none';
            var editor = document.getElementById('assessment-text-editor');
            if (editor) { editor.style.border = 'none'; editor.contentEditable = 'false'; }
        })()
        """
        self.browser.page().runJavaScript(hide_ui_js, lambda _: self._execute_print(path))

    def _execute_print(self, path):
        """执行打印命令"""
        self._progress_dialog = QProgressDialog("正在生成PDF报告，请稍候...", "取消", 0, 0, self)
        self._progress_dialog.setWindowTitle("导出PDF")
        self._progress_dialog.setWindowModality(Qt.WindowModal)
        self._progress_dialog.setCancelButton(None)
        self._progress_dialog.setRange(0, 0)
        self._progress_dialog.setMinimumDuration(0)
        self._progress_dialog.setStyleSheet("""
            QProgressDialog {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #FAFBFC, stop: 1 #FFFFFF);
                border: 1px solid #E1E8ED;
                border-radius: 16px;
                padding: 35px 40px;
                font-family: 'Microsoft YaHei', 'Segoe UI', 'PingFang SC', sans-serif;
                min-width: 400px;
                min-height: 150px;
            }
            QProgressDialog QLabel {
                color: #1A1F2E;
                font-size: 16px;
                font-weight: 500;
                padding: 15px 0px 20px 0px;
                background-color: transparent;
                letter-spacing: 0.5px;
            }
            QProgressBar {
                border: none;
                border-radius: 10px;
                background-color: #E8EEF5;
                text-align: center;
                height: 8px;
                margin: 15px 0px 10px 0px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #4A90E2, 
                    stop: 0.3 #5BA3F5, 
                    stop: 0.6 #6CB6FF,
                    stop: 1 #4A90E2);
                border-radius: 10px;
            }
        """)
        self._progress_dialog.show()

        try:
            try:
                from PyQt5.QtGui import QPageLayout, QPageSize
                from PyQt5.QtCore import QMarginsF
                a4_layout = QPageLayout(
                    QPageSize(QPageSize.A4),
                    QPageLayout.Portrait,
                    QMarginsF(0, 0, 0, 0),
                    QPageLayout.Millimeter,
                )
                self.browser.page().printToPdf(path, a4_layout)
            except (ImportError, TypeError, AttributeError):
                self.browser.page().printToPdf(path)
        except Exception as e:
            self._pending_pdf_path = None
            if self._progress_dialog:
                self._progress_dialog.close()
                self._progress_dialog = None
            QMessageBox.warning(self, "导出失败", f"PDF导出失败：\n{str(e)}")
            import traceback
            traceback.print_exc()

    def _on_pdf_printing_finished(self, file_path, success):
        """QWebEnginePage.pdfPrintingFinished 回调：这里才是PDF真正写入完成的时刻。"""
        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

        try:
            final_path = file_path or self._pending_pdf_path
            self._pending_pdf_path = None

            if not success or not final_path:
                QMessageBox.warning(self, "导出失败", "PDF导出失败（浏览器未能生成文件）。")
                return

            QMessageBox.information(self, "导出成功", f"PDF已成功保存到：\n{final_path}")
        except Exception as e:
            QMessageBox.warning(self, "导出提示", f"PDF已生成，但后处理失败：\n{str(e)}")
            import traceback
            traceback.print_exc()

    def show_error(self, message):
        """显示错误信息"""
        layout = QVBoxLayout(self)
        error_label = QLabel(message)
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("color: #ff4444; font-size: 14px;")
        layout.addWidget(error_label)

class ReportGeneratePage(QWidget):
    """报告生成，显示完整PDF文件（支持多页滚动）"""

    def __init__(self, page_title, pdf_rel_path=None, parent=None):
        super().__init__(parent)
        # 初始化缩放比例
        self.current_scale = 0.6

        self.page_title = page_title
        self.pdf_rel_path = pdf_rel_path
        self.pdf_pixmaps = []  # 存储所有页面的图片
        self.page_labels = []  # 存储所有页面的标签
        self.current_scale = 1.0  # 当前缩放比例
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        '''
        # 创建顶部控制栏（可选）
        control_layout = QHBoxLayout()
        control_layout.addStretch()
        # 缩放按钮（可选）
        zoom_in_btn = QPushButton("放大")
        zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_out_btn = QPushButton("缩小")
        zoom_out_btn.clicked.connect(self.zoom_out)
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.reset_zoom)

        control_layout.addWidget(zoom_out_btn)
        control_layout.addWidget(reset_btn)
        control_layout.addWidget(zoom_in_btn)
        layout.addLayout(control_layout)
        '''

        if self.pdf_rel_path:
            script_abs_path = os.path.dirname(os.path.abspath(__file__))
            self.pdf_abs_path = os.path.join(script_abs_path, self.pdf_rel_path)

            if os.path.exists(self.pdf_abs_path):
                # 创建主滚动区域
                self.scroll_area = QScrollArea()
                self.scroll_area.setWidgetResizable(True)
                self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                self.scroll_area.setStyleSheet(ControlStyle.get_scrollbar_style())

                # 核心：给滚动区域的视口安装事件过滤器，捕获所有滚轮事件
                self.scroll_area.viewport().installEventFilter(self)

                # 创建容器widget来存放所有页面
                self.container_widget = QWidget()
                self.container_layout = QVBoxLayout(self.container_widget)
                self.container_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
                self.container_layout.setSpacing(20)  # 页面间距

                # 加载PDF
               # self.load_pdf(self.pdf_abs_path)

                QTimer.singleShot(50, self.reset_zoom)

                # 设置滚动区域的内容
                self.scroll_area.setWidget(self.container_widget)

                layout.addWidget(self.scroll_area)

                self.btn_save = QPushButton("打印 / 保存为 PDF")
                self.btn_save.setFixedHeight(40)
                # 尝试设置打印机图标（如果系统支持）
                try:
                    icon = QIcon.fromTheme("document-print")
                    if icon.isNull():
                        # 如果没有系统图标，尝试使用Unicode字符
                        self.btn_save.setText("🖨️ 打印 / 保存为 PDF")
                    else:
                        self.btn_save.setIcon(icon)
                        self.btn_save.setIconSize(QSize(20, 20))
                except:
                    # 如果图标设置失败，使用Unicode字符
                    self.btn_save.setText("🖨️ 打印 / 保存为 PDF")
                # 设置深色背景、白色文字、圆角、阴影的样式
                self.btn_save.setStyleSheet("""
                            QPushButton {
                                background-color: #1a1a1a;
                                color: #FFFFFF;
                                border: none;
                                border-radius: 12px;
                                padding: 10px 24px;
                                font-family: HarmonyOS Sans SC, HarmonyOS Sans SC;
                                font-weight: 500;
                                font-size: 16px;
                                text-align: center;
                            }
                            QPushButton:hover {
                                background-color: #2a2a2a;
                            }
                            QPushButton:pressed {
                                background-color: #0a0a0a;
                            }
                        """)
                self.btn_save.clicked.connect(self.handle_save_pdf)
                layout.addWidget(self.btn_save)

            else:
                self.show_error(f"⚠ PDF文件不存在！\n路径：{self.pdf_abs_path}")
        else:
            self.show_error("⚠ PDF文件路径为空！")

    def handle_save_pdf(self):
        """处理PDF保存/打印功能，核心实现"""
        if not self.pdf_abs_path or not os.path.exists(self.pdf_abs_path):
            self.show_error("原始PDF文件不存在，无法保存！")
            return

        # 1. 获取原始文件名
        original_filename = os.path.basename(self.pdf_abs_path)

        # 2. 弹出保存文件对话框
        # 设置默认保存路径为桌面，文件名使用原始文件名
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存PDF文件",
            os.path.join(desktop_path, original_filename),
            "PDF Files (*.pdf);;All Files (*)"
        )

        # 3. 判断用户是否取消了保存
        if not save_path:
            return

        try:
            # 4. 复制原PDF文件到目标路径（保留文件元数据）
            shutil.copy2(self.pdf_abs_path, save_path)

            # 5. 提取保存的文件名和路径，弹出成功提示
            save_filename = os.path.basename(save_path)
            QMessageBox.information(
                self,
                "保存成功",
                f"已保存{save_filename}到\n{save_path}",
                QMessageBox.Ok
            )

        except PermissionError:
            self.show_error(f"权限不足，无法保存文件到\n{save_path}")
        except FileNotFoundError:
            self.show_error(f"保存路径不存在：\n{save_path}")
        except Exception as e:
            self.show_error(f"保存失败：{str(e)}")

    # def load_pdf(self, pdf_path):
    #     """加载PDF所有页面"""
    #     try:
    #         pdf_doc = fitz.open(pdf_path)
    #         total_pages = len(pdf_doc)

    #         if total_pages == 0:
    #             self.show_error("⚠ PDF文件为空，无页面可显示")
    #             pdf_doc.close()
    #             return

    #         # 计算DPI以确保清晰度
    #         dpi = 150  # 基础DPI
    #         scale = dpi / 72  # PDF默认是72DPI

    #         for page_num in range(total_pages):
    #             page = pdf_doc[page_num]

    #             # 获取页面原始尺寸（单位：点）
    #             rect = page.rect
    #             page_width_pt = rect.width
    #             page_height_pt = rect.height

    #             # 计算以像素为单位的尺寸
    #             zoom_x = scale * 2.0  # 额外的缩放因子以确保清晰度
    #             zoom_y = scale * 2.0

    #             # 创建转换矩阵
    #             mat = fitz.Matrix(zoom_x, zoom_y)

    #             # 渲染页面为图片
    #             pix = page.get_pixmap(matrix=mat, alpha=False)

    #             # 转换到QPixmap
    #             true_stride = pix.width * 3
    #             pix_samples = bytes(pix.samples)

    #             img = QImage(pix_samples, pix.width, pix.height,
    #                          true_stride, QImage.Format_RGB888)

    #             pixmap = QPixmap.fromImage(img)

    #             if pixmap.isNull():
    #                 print(f"警告：第{page_num + 1}页转换失败")
    #                 continue

    #             # 存储原图
    #             self.pdf_pixmaps.append({
    #                 'original': pixmap,
    #                 'scaled': pixmap.copy(),
    #                 'size': pixmap.size()
    #             })

    #             # 创建页面标签
    #             page_label = QLabel()
    #             page_label.setAlignment(Qt.AlignCenter)
    #             page_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

    #             # 添加页码标签
    #             page_info = QLabel(f"第 {page_num + 1} 页")
    #             page_info.setAlignment(Qt.AlignCenter)
    #             page_info.setStyleSheet("""
    #                 QLabel {
    #                     background-color: rgba(0, 0, 0, 100);
    #                     color: white;
    #                     padding: 2px 8px;
    #                     border-radius: 4px;
    #                     font-size: 10px;
    #                 }
    #             """)

    #             # 创建单页容器
    #             page_container = QWidget()
    #             page_layout = QVBoxLayout(page_container)
    #             page_layout.setContentsMargins(0, 0, 0, 0)
    #             page_layout.setSpacing(5)
    #             page_layout.addWidget(page_info)
    #             page_layout.addWidget(page_label)

    #             self.container_layout.addWidget(page_container)
    #             self.page_labels.append(page_label)

    #         pdf_doc.close()

    #         # 初始缩放
    #         self.reset_zoom()

    #     except Exception as e:
    #         self.show_error(f"⚠ PDF加载异常：{str(e)}")
    #         print(f"PDF加载详细错误：{e}")

    def show_error(self, message):
        """显示错误信息"""
        error_label = QLabel(message)
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("color: red; font-size: 14px; padding: 20px;")
        layout = self.layout()
        if layout:
            layout.addWidget(error_label)

    def resizeEvent(self, event):
        """窗口大小变化时重新缩放"""
        super().resizeEvent(event)
        self.update_page_scales()

    def update_page_scales(self):
        """更新所有页面的缩放"""
        if not self.page_labels or not self.pdf_pixmaps:
            return

        # 获取滚动区域视口的可用宽度
        viewport_width = self.scroll_area.viewport().width() - 40  # 减去边距

        for i, (pixmap_data, label) in enumerate(zip(self.pdf_pixmaps, self.page_labels)):
            original_pixmap = pixmap_data['original']
            original_size = original_pixmap.size()

            if original_size.width() == 0:
                continue

            # 计算缩放比例以适应视口宽度
            scale_factor = viewport_width / original_size.width()

            # 应用当前缩放级别
            final_scale = scale_factor * self.current_scale

            # 计算新尺寸
            new_width = int(original_size.width() * final_scale)
            new_height = int(original_size.height() * final_scale)

            # 确保最小尺寸
            new_width = max(new_width, 100)
            new_height = max(new_height, 100)

            # 缩放图片
            scaled_pixmap = original_pixmap.scaled(
                new_width,
                new_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            # 更新显示
            label.setPixmap(scaled_pixmap)
            label.setFixedSize(scaled_pixmap.size())

            # 存储缩放后的图片
            pixmap_data['scaled'] = scaled_pixmap

    def eventFilter(self, obj, event):
        """
        事件过滤器：核心修复逻辑，优先捕获滚动条视口的滚轮事件
        解决「滚动条拦截滚轮事件」问题，实现全位置缩放
        """
        # 仅处理滚轮事件，且触发对象是滚动区域的视口
        if obj == self.scroll_area.viewport() and event.type() == QEvent.Wheel:
            # 判断是否按住Ctrl键（核心缩放触发条件）
            if event.modifiers() == Qt.ControlModifier:
                # 修复方向问题：统一用y轴偏移量判断，正数=向上（放大），负数=向下（缩小）
                delta = event.angleDelta().y()
                if delta > 0:
                    self.zoom_in()  # 滚轮向上→放大
                else:
                    self.zoom_out()  # 滚轮向下→缩小
                # 拦截事件，防止传递给滚动条（关键：避免滚动条滚动）
                return True
        # 非目标事件/未按Ctrl，执行默认行为
        return super().eventFilter(obj, event)

    def zoom_in(self):
        """放大"""
        self.current_scale *= 1.2
        self.update_page_scales()

    def zoom_out(self):
        """缩小"""
        self.current_scale *= 0.8
        # 确保最小缩放
        if self.current_scale < 0.1:
            self.current_scale = 0.1
        self.update_page_scales()

    def reset_zoom(self):
        """重置缩放"""
        self.current_scale = 0.6
        self.update_page_scales()


class SubjectInputPage(QWidget):
    """受试者数据库页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent  # 保存主窗口引用

        self.initUI()
        self.init_database()

        # self.load_subjects_from_db()

    def initUI(self):
        content_layout = QVBoxLayout(self)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)

        title_layout = QHBoxLayout()
        title_layout.setSpacing(16)

        title_name_layout = QVBoxLayout()
        title_name_layout.setSpacing(4)
        title_label_C = QLabel("受试者数据库")
        title_label_C.setStyleSheet(
            """
             font-family: Microsoft YaHei;
             font-weight: 500;
                font-size: 28px;
                color: #31373D;
                text-align: left;
                font-style: normal;
                text-transform: none;
             """)
        title_label = QLabel("Subject Database Management")
        title_label.setStyleSheet(
            """
             font-family: Microsoft YaHei;
             font-weight: 400;
             font-size: 14px;
             color: #979797;
             text-align: left;
             font-style: normal;
             text-transform: none;
             """)
        title_name_layout.addWidget(title_label_C)
        title_name_layout.addWidget(title_label)
        title_layout.addLayout(title_name_layout)

        # 新建按钮
        title_layout.addStretch()
        self.add_btn = QPushButton("新建受试者档案")
        icon = QIcon("./resource/picture/add_subject.png")
        self.add_btn.setIcon(icon)
        self.add_btn.setIconSize(QSize(25, 25))
        self.add_btn.setStyleSheet(ControlStyle.get_add_btn_style())
        # self.add_btn.clicked.connect(self.on_add_subject)
        title_layout.addWidget(self.add_btn)

        content_layout.addLayout(title_layout)

        # 搜索和table
        search_tabel_widget = QWidget()
        search_tabel_layout = QVBoxLayout(search_tabel_widget)
        search_tabel_layout.setContentsMargins(32, 32, 32, 32)  # 设置内边距
        search_tabel_layout.setSpacing(16)
        search_tabel_widget.setStyleSheet(ControlStyle.get_background_border_widget("#FFFFFF", "4"))

        widegt = QWidget()
        layout = QHBoxLayout(widegt)
        layout.setContentsMargins(20, 0, 0, 0)
        widegt.setStyleSheet("background: #F8F9FB;border-radius: 8px;")

        # 检索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("按ID/姓名查找")
        self.search_edit.setStyleSheet(ControlStyle.get_search_edit_style())
        # 输入限制：仅允许汉字、英文字母、数字，最大长度 50
        self.search_validator = SearchInputValidator(self.search_edit)
        self.search_edit.setValidator(self.search_validator)
        self.search_edit.setMaxLength(50)
        # self.search_edit.textChanged.connect(self.on_search)

        layout.addWidget(self.search_edit)
        search_tabel_layout.addWidget(widegt)

        # 表格
        self.table = QTableWidget()
        # self.table.setStyleSheet(ControlStyle.get_table_style())
        # 设置列
        columns = ["ID", "姓名", "年龄", "性别", "录入日期", "身高(cm)", "体重(kg)", "BMI", "采集人", "操作"]
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)

        age_item = QTableWidgetItem()
        age_item.setText("年龄 ↕")  # 表头文字
        age_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.table.setHorizontalHeaderItem(2, age_item)

        time_item = QTableWidgetItem()
        time_item.setText("录入日期 ↕")  # 表头文字
        time_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.table.setHorizontalHeaderItem(4, time_item)

        bmi_item = QTableWidgetItem()
        bmi_item.setText("BMI ↕")  # 表头文字
        bmi_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.table.setHorizontalHeaderItem(7, bmi_item)

        # 设置表格属性
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        # 录入日期列可排序
        self.table.horizontalHeader().setSortIndicatorShown(True)

        # 设置列宽
        col_widths = [210, 150, 150, 150, 200, 150, 150, 150, 150, 200]
        for i, width in enumerate(col_widths):
            self.table.setColumnWidth(i, width)

        self.table.verticalHeader().setVisible(False)

        # ========== 4. 表头样式（匹配图片浅灰背景） ==========
        header = self.table.horizontalHeader()

        header.setFixedHeight(56)  # 直接设置表头整体高度

        # 设置表格每行的高度，数值越大，行越高
        self.table.verticalHeader().setDefaultSectionSize(72)

        header.setStyleSheet(ControlStyle.get_table_header_style())
        header.setDefaultAlignment(Qt.AlignCenter | Qt.AlignVCenter)  # 表头文字左对齐

        # ========== 5. 表格整体样式 ==========
        self.table.setStyleSheet(ControlStyle.get_table_item_style() + ControlStyle.get_scrollbar_style())

        # ========== 重构：空状态提示控件（作为表格子控件） ==========
        # 1. 创建空状态容器，父控件设为table的视口（table.viewport()），而非外层布局
        self.empty_widget = QWidget(self.table.viewport())
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignCenter)  # 内容居中
        empty_layout.setContentsMargins(0, 0, 0, 0)

        # 2. 空状态图标（替换为你实际的图标路径）
        self.empty_icon = QLabel()
        self.empty_icon.setPixmap(
            QPixmap("./resource/picture/empty_icon.png")  # 替换为截图中的图标路径
            .scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.empty_icon.setAlignment(Qt.AlignCenter)

        # 3. 空状态文字
        self.empty_label = QLabel("暂无被试者信息，请先新建受试者档案")
        self.empty_label.setStyleSheet(ControlStyle.get_qeeg_font_400("#D4D6D9", "14", "center"))

        # 把图标和文字加入空状态布局
        empty_layout.addWidget(self.empty_icon)
        empty_layout.addWidget(self.empty_label)

        # 初始隐藏空状态
        self.empty_widget.hide()
        # 透明背景 + 鼠标穿透（不影响表格操作）
        self.empty_widget.setStyleSheet("background-color: transparent;")
        self.empty_widget.setAttribute(Qt.WA_TransparentForMouseEvents)

        # ========== 关键：添加表格视口大小变化的监听，确保空状态始终居中 ==========
        self.table.viewport().resizeEvent = self.on_viewport_resize  # 重写视口resize事件

        # ========== 把表格加入布局（移除原来的empty_widget添加） ==========
        search_tabel_layout.addWidget(self.table)
        content_layout.addWidget(search_tabel_widget)

        # 分页控件
        self.pagination = PaginationWidget()
        # self.pagination.page_changed.connect(self.on_page_changed)

        content_layout.addWidget(self.pagination)

        # self.setLayout(content_layout)

    def check_empty_state(self):
        if self.table.rowCount() == 0:
            # 表格为空：显示空状态，调整位置到视口中心
            self.empty_widget.show()
            # 延迟10ms执行（确保视口已完成初始化渲染）
            QTimer.singleShot(10, self.adjust_empty_widget_position)
        else:
            self.empty_widget.hide()  # 有数据 → 隐藏提示

    def adjust_empty_widget_position(self):
        """精准校准空状态提示的位置到视口正中心"""
        # 获取表格视口的当前有效区域（排除滚动条等）
        viewport_rect = self.table.viewport().rect()
        # 强制设置empty_widget的大小和位置与视口完全一致
        self.empty_widget.setGeometry(viewport_rect)
        # 刷新布局（确保内容重新计算居中）
        self.empty_widget.layout().activate()

    def on_viewport_resize(self, event):
        """表格视口大小变化时，重新调整空状态位置"""
        # 先执行原有的resize逻辑
        QWidget.resizeEvent(self.table.viewport(), event)
        # 重新检查空状态并调整位置
        self.check_empty_state()

    def init_database(self):
        """初始化数据库"""
        try:
            # 连接数据库
            SQLLiteDB_Only_MainTread.connect()

            # 创建表（如果不存在）
            Subject.create_table(SQLLiteDB_Only_MainTread.user_db)

        except Exception as e:
            QMessageBox.warning(self, "数据库错误", f"数据库初始化失败: {str(e)}")
            print(f"数据库错误: {e}")


# ========== 载入模板竖向弹窗（核心） ==========
class TemplateLoadDialog(QDialog):
    """竖向条状的载入模板弹窗"""
    # 自定义信号：载入模板成功时传递模板ID和名称
    template_loaded = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.templates = []  # 模板数据（模拟数据库）
        self.tasks = []
        self.initUI()

        self.setFixedSize(500, 400)
        self.setWindowTitle("载入模板")
        self.setModal(True)

    def initUI(self):

        # 主布局（竖向）
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # 弹窗标题
        title_label = QLabel("模板列表")
        title_label.setStyleSheet("""
            QLabel {""" + ControlStyle.get_qeeg_font_500("#000000", "20") + """}""")
        main_layout.addWidget(title_label)

        # 滚动区域（容纳多个模板项，支持滚动）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(ControlStyle.get_scrollbar_style())  # 隐藏滚动区域边框
        main_layout.addWidget(scroll_area, 1)  # 占主要空间

        # 滚动区域内的容器
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(6)
        scroll_area.setWidget(scroll_content)

        # 加载所有模板项
        self.load_template_items(scroll_layout)

    def load_template_items(self, parent_layout):
        """加载所有模板项到布局中"""
        templates = Template.select_all(SQLLiteDB_Only_MainTread.user_db)

        # 清空当前数据
        self.templates = []

        # 转换数据格式
        for template in templates:
            self.templates.append({
                "id": template.id,
                "name": template.name,
            })

        for template in self.templates:
            # 单个模板项的水平布局

            # 模板项容器（带边框，区分每个模板）
            item_widget = QWidget()
            item_widget.setObjectName("item_widget")
            item_widget.setStyleSheet(ControlStyle.get_item_widget_style())
            item_widget.setFixedHeight(100)
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(12, 12, 12, 12)
            item_layout.setSpacing(16)

            # 左侧：模板名称+注释（垂直布局）
            info_widget = QWidget()
            info_layout = QVBoxLayout(info_widget)
            info_layout.setContentsMargins(12, 12, 12, 12)
            info_layout.setSpacing(4)

            # 模板名称
            name_label = QLabel(template["name"])
            name_label.setStyleSheet(ControlStyle.get_history_record_font_2())

            comment_icon_layout = QHBoxLayout()
            comment_icon_layout.setContentsMargins(0, 0, 0, 0)  # 清除布局边距，紧凑显示
            comment_icon_layout.setSpacing(4)  # 图标和文字的间距，可自行调整(推荐4/6px)

            # 2. 图标专用的QLabel
            icon_label = QLabel()
            icon = QIcon("./resource/picture/task.png")
            # 将图标转为QPixmap设置给QLabel，这是QLabel显示图标的正确方式
            icon_label.setPixmap(icon.pixmap(QSize(16, 16)))
            # 模板注释
            count = len(TaskTemplate.get_tasks_by_template(SQLLiteDB_Only_MainTread.user_db, template["id"]))
            comment_label = QLabel(str(count) + "个分析模块")
            comment_label.setStyleSheet(ControlStyle.get_history_record_font_1())
            comment_label.setWordWrap(True)  # 自动换行

            comment_icon_layout.addWidget(icon_label)
            comment_icon_layout.addWidget(comment_label)
            comment_icon_layout.addStretch()

            info_layout.addWidget(name_label)
            info_layout.addLayout(comment_icon_layout)
            item_layout.addWidget(info_widget, 1)  # 占大部分空间

            # 右侧：删除+载入按钮（垂直布局）
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(12, 12, 12, 12)
            btn_layout.setSpacing(8)

            '''
            # 修改按钮（图标）
            edit_btn = QPushButton()
            edit_btn.setIcon(QIcon("./resource/picture/edit.png"))  # 替换为实际图标路径
            edit_btn.setIconSize(QSize(18, 18))
            edit_btn.clicked.connect(lambda _, t=template: self.on_update_template(t))
            '''

            # 删除按钮
            del_btn = QPushButton()
            del_btn.setIcon(QIcon("./resource/picture/delete.png"))  # 替换为实际图标路径
            del_btn.setIconSize(QSize(18, 18))
            del_btn.setStyleSheet("border:none;")
            del_btn.clicked.connect(lambda _, t=template: self.on_delete_template(t))

            # 载入按钮
            load_btn = QPushButton("载入")
            load_btn.setCursor(QCursor(Qt.PointingHandCursor))
            load_btn.setIcon(QIcon("./resource/picture/load.png"))  # 替换为实际图标路径
            load_btn.setIconSize(QSize(18, 18))
            load_btn.setStyleSheet(ControlStyle.get_load_btn_style())
            load_btn.setMinimumSize(104, 36)
            load_btn.clicked.connect(
                lambda _, tid=template["id"], tname=template["name"]: self.on_load_template(tid, tname))

            # btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(del_btn)
            btn_layout.addWidget(load_btn)
            item_layout.addWidget(btn_widget)
            # 添加到滚动布局
            parent_layout.addWidget(item_widget)
        parent_layout.addStretch()

    def on_load_template(self, template_id, template_name):
        """载入模板事件"""
        self.template_loaded.emit(template_id, template_name)
        # QMessageBox.information(self, "成功", f"已载入模板：{template_name}")
        self.accept()  # 载入成功后关闭弹窗

    def delete_template_from_db(self, id):
        try:
            success = Template.delete(SQLLiteDB_Only_MainTread.user_db, id)
            return success

        except Exception as e:
            QMessageBox.warning(self, "数据库错误", f"删除数据失败: {str(e)}")
            return False

    def on_delete_template(self, template):
        """删除模板事件"""
        id = template["id"]
        name = template["name"]
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除模板<span style='color:#2A87DB;'>【{name}】</span> 吗？删除后将无法找回！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # 从数据库删除
            success = self.delete_template_from_db(id)
            if success:
                # 刷新弹窗（重新加载模板项）
                self.refresh_template_list()
                QMessageBox.information(self, "成功", "模板已删除！")

    def refresh_template_list(self):
        """刷新模板列表"""
        # 清空滚动布局
        scroll_widget = self.findChild(QScrollArea).widget()
        scroll_layout = scroll_widget.layout()
        while scroll_layout.count():
            item = scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        # 重新加载模板项
        self.load_template_items(scroll_layout)


class progressBar(QDialog):
    progressBar_completed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowTitle("")  # 隐藏系统标题栏文字
        self.setModal(True)
        self.setFixedSize(850, 200)

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.initUI()
        # self.setStyleSheet("background:#FFFFFF;border: 2px solid #2A87DB")

    def initUI(self):
        # 让progressBar_widget 铺满整个弹窗，所有内容才会显示
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.progressBar = GifProgressBar()

        self.progressBar_widget = QWidget()
        self.progressBar_widget.setStyleSheet("""
                    QWidget {
                        background:#FFFFFF;          /* 背景色 */
                        border: 2px solid #2A87DB;   /* 边框 */
                        border-radius: 15px;         /* 圆角半径（可调整，越大越圆） */
                    }
                """)
        progressBar_vlayout = QVBoxLayout(self.progressBar_widget)
        progressBar_vlayout.setContentsMargins(12, 0, 12, 0)
        progressBar_vlayout.setAlignment(Qt.AlignCenter)
        progressBar_vlayout.setSpacing(0)

        self.label_progressBar = QLabel()
        self.label_progressBar.setText("开始生成...")
        self.label_progressBar.setObjectName("label_progressBar")
        self.label_progressBar.setMinimumSize(50, 20)
        self.label_progressBar.setStyleSheet(ControlStyle.get_redo_set_pushButton_style())
        ControlStyle.get_font_size(self.label_progressBar, 10)

        # 刷新 GUI
        QApplication.processEvents()

        progressBar_vlayout.addWidget(self.progressBar)
        progressBar_vlayout.addWidget(self.label_progressBar, alignment=Qt.AlignLeft)

        main_layout.addWidget(self.progressBar_widget)


class SaveTemplate(QDialog):
    """保存模板的弹窗"""
    submit_signal = pyqtSignal(dict)  # 提交

    def __init__(self, parent=None):
        super().__init__(parent)
        # self.setWindowFlags(Qt.FramelessWindowHint)
        # self.setWindowTitle("")  # 隐藏系统标题栏文字
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowTitle("保存为新模板")
        self.setModal(True)
        self.setFixedSize(350, 200)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        title_layout = QHBoxLayout()
        title_layout.setSpacing(4)  # 图标和标题的间距

        # 图标标签（替换为你的实际图标路径）
        icon_label = QLabel()
        # 示例：用系统默认图标，实际项目替换为你的图标路径
        icon = QIcon("./resource/picture/template.png")
        icon_label.setPixmap(icon.pixmap(16, 16))  # 图标大小

        # 标题文字
        title_label = QLabel("保存为新模板")
        title_label.setStyleSheet(ControlStyle.get_qeeg_font_500("#000000", "20"))
        title_layout.addWidget(icon_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        method_title = QLabel("模板名称")  # 去掉原有的冒号
        method_title.setStyleSheet(ControlStyle.get_qeeg_font_500("#979797", "16"))
        main_layout.addWidget(method_title)

        self.method_title_edit = QLineEdit()
        # 修改占位符为截图示例
        self.method_title_edit.setPlaceholderText("e.g. 儿童注意力分析模版")
        self.method_title_edit.setStyleSheet(ControlStyle.get_method_title_edit_style())
        # 模板名称：上限 100 个字符，不支持换行
        self.method_title_edit.setMaxLength(100)
        self.method_title_edit.textChanged.connect(self._sanitize_template_name_input)
        main_layout.addWidget(self.method_title_edit)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.setAlignment(Qt.AlignRight)

        # 取消按钮（白色边框样式）
        btn_cancel = QPushButton("取消")
        btn_cancel.setStyleSheet(ControlStyle.get_btn_cancel_style())
        btn_cancel.clicked.connect(self.reject)

        # 保存按钮（蓝色背景样式）
        btn_save = QPushButton("保存")
        btn_save.setStyleSheet(ControlStyle.get_btn_save_style())
        btn_save.clicked.connect(self.on_submit)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        main_layout.addLayout(btn_layout)

    def _sanitize_template_name_input(self, text: str):
        """清理模板名称中的换行符"""
        if "\n" in text or "\r" in text:
            cleaned = text.replace("\n", "").replace("\r", "")
            if cleaned != text and hasattr(self, "method_title_edit"):
                self.method_title_edit.blockSignals(True)
                self.method_title_edit.setText(cleaned)
                self.method_title_edit.blockSignals(False)

    def on_submit(self):
        """提交"""
        method_title_text = self.method_title_edit.text().strip()
        if not method_title_text:
            QMessageBox.warning(self, "警告", "模板名称不能为空！")
            return
        template = Template.get_by_name(SQLLiteDB_Only_MainTread.user_db, method_title_text)
        if template:
            QMessageBox.warning(self, "警告", "模板名称重复！")
            return
        # 构造修改后的数据
        template_data = {
            "id": 0,
            "name": method_title_text,
        }
        self.submit_signal.emit(template_data)
        self.accept()


class EditHistoryDialog(QDialog):
    """修改历史记录的弹窗"""
    submit_signal = pyqtSignal(dict)  # 提交修改后的记录

    def __init__(self, history_data=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.history_data = history_data
        self.setWindowTitle("修改历史记录")
        self.setModal(True)
        self.setFixedSize(400, 200)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        # 时间输入框
        time_layout = QHBoxLayout()
        time_layout.setSpacing(8)
        time_label = QLabel("时间:")
        time_label.setStyleSheet(ControlStyle.get_qeeg_font_500("#31373D", "14", "center"))
        self.time_edit = QLineEdit()
        self.time_edit.setPlaceholderText("格式：HHHH-MM-DD")
        self.time_edit.setText(self.history_data.get("created_date", ""))
        self.time_edit.setStyleSheet(
            ControlStyle.get_addSubjwct_lineEdit()+""" QLineEdit {font-family: Microsoft YaHei;font-weight: 400;
            font-size: 14px;
            color: #31373D;
            text-align: left;
            font-style: normal;
            text-transform: none;
              }""")
        self.time_edit.setEnabled(False)
        time_layout.addWidget(time_label)
        time_layout.addWidget(self.time_edit)
        form_layout.addRow(time_layout)

        # 名称输入框
        name_layout = QHBoxLayout()
        name_layout.setSpacing(8)
        name_label = QLabel("名称:")
        name_label.setStyleSheet(ControlStyle.get_qeeg_font_500("#31373D", "14", "center"))
        self.name_edit = QLineEdit()
        self.name_edit.setText(self.history_data.get("name", ""))
        self.name_edit.setStyleSheet(
            ControlStyle.get_addSubjwct_lineEdit() + """
        QLineEdit {
            font-family: Microsoft YaHei;
            font-weight: 400;
            font-size: 14px;
            color: #31373D;
            text-align: left;
            font-style: normal;
            text-transform: none;
        }
    """)
        # 历史记录名称：上限 60 个字符，不支持换行
        self.name_edit.setMaxLength(60)
        self.name_edit.textChanged.connect(self._sanitize_record_name_input)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)
        form_layout.addRow(name_layout)

        main_layout.addLayout(form_layout)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.setAlignment(Qt.AlignRight)

        # 确认/取消按钮
        self.btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        # 获取按钮并单独设置样式
        ok_btn = self.btn_box.button(QDialogButtonBox.Ok)
        cancel_btn = self.btn_box.button(QDialogButtonBox.Cancel)
        ok_btn.setText("确认")
        cancel_btn.setText("取消")

        # 直接对按钮设置样式
        ok_btn.setStyleSheet(ControlStyle.get_qeeg_font_400("#31373D", "14", "center"))
        cancel_btn.setStyleSheet(ControlStyle.get_qeeg_font_400("#31373D", "14", "center"))

        self.btn_box.accepted.connect(self.on_submit)
        self.btn_box.rejected.connect(self.reject)
        btn_layout.addWidget(self.btn_box)

        main_layout.addLayout(btn_layout)

    def _sanitize_record_name_input(self, text: str):
        """清理历史记录名称中的换行符"""
        if "\n" in text or "\r" in text:
            cleaned = text.replace("\n", "").replace("\r", "")
            if cleaned != text and hasattr(self, "name_edit"):
                self.name_edit.blockSignals(True)
                self.name_edit.setText(cleaned)
                self.name_edit.blockSignals(False)

    def on_submit(self):
        """提交修改后的记录"""
        time_text = self.time_edit.text().strip()
        name_text = self.name_edit.text().strip()

        if not time_text:
            QMessageBox.warning(self, "警告", "时间不能为空！")
            return
        if not name_text:
            QMessageBox.warning(self, "警告", "名称不能为空！")
            return

        # 构造修改后的数据
        updated_data = {
            "id": self.history_data["id"],
            "name": name_text,
            "created_date": time_text,
            "relative_path": self.history_data["relative_path"],
            "subject_id": self.history_data["subject_id"]
        }
        self.submit_signal.emit(updated_data)
        self.accept()


# ========== 历史记录主对话框 ==========
class HistoryRecordDialog(QDialog):
    """历史记录对话框（核心）"""

    def __init__(self, subject, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.subject = subject  # 关联的受试者

        self.setWindowTitle("历史记录")
        self.setModal(True)
        self.setMinimumSize(800, 400)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # ========== 1. 顶部区域：标题 + 关闭按钮 ==========
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        # 标题
        title_label = QLabel("历史分析记录")
        title_label.setStyleSheet(ControlStyle.get_qeeg_font_500("#000000", "20"))
        top_layout.addWidget(title_label)
        # 拉伸项：将关闭按钮推到右侧
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        # ========== 2. 受试者信息栏（姓名/性别/年龄/身体指标/采集人） ==========
        self.info_widget = QWidget()
        self.info_widget.setFixedHeight(95)
        self.info_widget.setStyleSheet(ControlStyle.get_background_border_widget("#F6F9FF", "8", "12"))
        self.info_layout = QHBoxLayout(self.info_widget)
        self.info_layout.setSpacing(0)
        self.info_layout.setContentsMargins(0, 0, 0, 0)

        name_layout = QVBoxLayout()
        name_label = QLabel("姓名")
        name_label_ = QLabel(self.subject["name"])
        name_label.setStyleSheet(ControlStyle.get_history_record_font_1())
        name_label_.setStyleSheet(ControlStyle.get_history_record_font_2())
        name_layout.addWidget(name_label)
        name_layout.addWidget(name_label_)
        self.info_layout.addLayout(name_layout)

        gender_layout = QVBoxLayout()
        gender_label = QLabel("性别")
        gender_label_ = QLabel(str(self.subject.get("gender", "")))
        gender_label.setStyleSheet(ControlStyle.get_history_record_font_1())
        gender_label_.setStyleSheet(ControlStyle.get_history_record_font_2())
        gender_layout.addWidget(gender_label)
        gender_layout.addWidget(gender_label_)
        self.info_layout.addLayout(gender_layout)

        age_layout = QVBoxLayout()
        age_label = QLabel("年龄")
        age_label_ = QLabel(str(self.subject.get("age", "")))
        age_label.setStyleSheet(ControlStyle.get_history_record_font_1())
        age_label_.setStyleSheet(ControlStyle.get_history_record_font_2())
        age_layout.addWidget(age_label)
        age_layout.addWidget(age_label_)
        self.info_layout.addLayout(age_layout)

        hw_layout = QVBoxLayout()
        hw_label = QLabel("身体指标")
        hw_label_ = QLabel(str(self.subject.get("height", "")) + "cm/" + str(self.subject.get("weight", "")) + "kg")
        hw_label.setStyleSheet(ControlStyle.get_history_record_font_1())
        hw_label_.setStyleSheet(ControlStyle.get_history_record_font_2())
        hw_layout.addWidget(hw_label)
        hw_layout.addWidget(hw_label_)
        self.info_layout.addLayout(hw_layout)

        analyst_layout = QVBoxLayout()
        analyst_label = QLabel("采集人")
        analyst_text = self.subject.get("analyst", "")
        analyst_label_ = QLabel(analyst_text if analyst_text else "--")
        analyst_label.setStyleSheet(ControlStyle.get_history_record_font_1())
        analyst_label_.setStyleSheet(ControlStyle.get_history_record_font_2())
        analyst_layout.addWidget(analyst_label)
        analyst_layout.addWidget(analyst_label_)
        self.info_layout.addLayout(analyst_layout)

        main_layout.addWidget(self.info_widget)

        # 滚动区域（容纳多个模板项，支持滚动）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(ControlStyle.get_scrollbar_style())  # 隐藏滚动区域边框
        main_layout.addWidget(scroll_area, 1)  # 占主要空间

        # ========== 3. 历史记录卡片容器 ==========
        self.records_container = QWidget()
        self.records_layout = QVBoxLayout(self.records_container)
        self.records_layout.setSpacing(12)  # 卡片之间的间距
        self.records_layout.setContentsMargins(0, 0, 0, 0)
        scroll_area.setWidget(self.records_container)
        # 让容器占满剩余空间
        # self.records_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # main_layout.addWidget(self.records_container)




class Ui_qeeg_analysis(QWidget):
    # closed = QtCore.pyqtSignal()  # 定义信号
    # 定义一个自定义信号
    progressBar_completed = pyqtSignal()
    signal = pyqtSignal('PyQt_PyObject')

    # 标志位：记录鼠标是否悬停在输入框/滑块上

    def __init__(self, edfpath=None, username=None, gender=None, age=None, create_date=None, analyst=None, is_host_computer=False):
        super().__init__()
        # Configure matplotlib for better performance
        plt.rcParams['agg.path.chunksize'] = 10000  # Increase chunk size for complex paths
        plt.rcParams['path.simplify'] = True  # Enable path simplification
        plt.rcParams['path.simplify_threshold'] = 0.5  # Increase simplification threshold

        self.edfpath = edfpath
        self.username = username
        self.gender = gender
        self.age = age
        self.create_date = create_date
        self.analyst = analyst
        self.is_host_computer = is_host_computer

        # 在初始化时添加这些变量
        self.raw = None
        self.raw_processed = None
        self.ch_name_mapping = {}  # 进行映射

        channels = ['Channel1', 'Channel2', 'Channel3', 'Channel4', 'X', 'Y', 'Z']
        eeg_acc = ['EEG0', 'EEG1', 'EEG2', 'EEG3', 'ACC0', 'ACC1', 'ACC2']

        for i in range(min(len(channels), len(eeg_acc))):
            self.ch_name_mapping[channels[i]] = eeg_acc[i]

        self.subject_data = []
        self.sort_column = 4  # 时间列
        self.sort_order = Qt.AscendingOrder

        self.page_size = 6  # 每页显示行数
        self.current_page = 1

        self.history_data = []

        self.init_database_history_task()

        self.init_database_task_template()

        self.setStyleSheet(ControlStyle.get_QMessageBox_Style())

        '''
        Subject.clear(SQLLiteDB_Only_MainTread.user_db)
        # 插入1000条数据

        for i in range(1000):
            # 创建Subject对象
            subject = Subject.from_dict({
                "id": "id_"+str(i),
                "name": "subject_name",
                "create_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "age": "22",
                "gender": "男",
                "height": "178",
                "weight": "70",
                "bmi": "18.5",
                "analyst": "a_name",
            })
            # 使用Subject类的方法插入数据
            Subject.insert(SQLLiteDB_Only_MainTread.user_db, subject)
        print("插入结束")
        '''

        template = Template.get_by_name(SQLLiteDB_Only_MainTread.user_db,"儿童注意力分析")
        if template is None:
            template_ = Template.from_dict({
                "name": "儿童注意力分析"
            })
            template_id = Template.insert(SQLLiteDB_Only_MainTread.user_db, template_)

            task = Task.from_dict({
                "name": "α 抑制指数",
                "analysis_method": "alpha Ratio(EC/EO)",
                "start_time": 0,
                "end_time": 30,
                "high_pass": None,
                "low_pass": None,
                "start_time_": 0,
                "end_time_": 30,
                "selected_event_names": json.dumps(["闭眼 [1]"]),
                "selected_event_names_segment1": json.dumps(["闭眼 [1]"]),
                "selected_event_names_segment2": json.dumps(["睁眼 [1]"]),
                "current_segment": 1,
            })
            task_id = Task.insert(SQLLiteDB_Only_MainTread.user_db, task)
            TaskTemplate.insert(SQLLiteDB_Only_MainTread.user_db, template_id, task_id)

            task = Task.from_dict({
                "name": "闭眼后 α 峰值频率",
                "analysis_method": "Peak Alpha Frequency",
                "start_time": 0,
                "end_time": 30,
                "high_pass": None,
                "low_pass": None,
                "start_time_": None,
                "end_time_": None,
                "selected_event_names": json.dumps(["闭眼 [1]"]),
            })
            task_id = Task.insert(SQLLiteDB_Only_MainTread.user_db,task)
            TaskTemplate.insert(SQLLiteDB_Only_MainTread.user_db,template_id,task_id)

            task = Task.from_dict({
                "name": "睁眼 α 峰值频率",
                "analysis_method": "Peak Alpha Frequency",
                "start_time": 0,
                "end_time": 30,
                "high_pass": None,
                "low_pass": None,
                "start_time_": None,
                "end_time_": None,
                "selected_event_names": json.dumps(["睁眼 [1]"]),
            })
            task_id = Task.insert(SQLLiteDB_Only_MainTread.user_db, task)
            TaskTemplate.insert(SQLLiteDB_Only_MainTread.user_db,template_id, task_id)

            task = Task.from_dict({
                "name": "睁眼/闭眼 θ/β 比率",
                "analysis_method": "Theta/Beta Ratio",
                "start_time": 0,
                "end_time": 30,
                "high_pass": None,
                "low_pass": None,
                "start_time_": None,
                "end_time_": None,
                "selected_event_names": json.dumps(["睁眼 [1]"]),
            })
            task_id = Task.insert(SQLLiteDB_Only_MainTread.user_db, task)
            TaskTemplate.insert(SQLLiteDB_Only_MainTread.user_db,template_id, task_id)

            task = Task.from_dict({
                "name": "睁眼/闭眼前额 α 非对称性",
                "analysis_method": "Frontal Alpha Asymmetry",
                "start_time": 0,
                "end_time": 30,
                "high_pass": None,
                "low_pass": None,
                "start_time_": None,
                "end_time_": None,
                "selected_event_names": json.dumps(["睁眼 [1]"]),
            })
            task_id = Task.insert(SQLLiteDB_Only_MainTread.user_db, task)
            TaskTemplate.insert(SQLLiteDB_Only_MainTread.user_db,template_id, task_id)


            task = Task.from_dict({
                "name": "闭眼后全频段功率分布",
                "analysis_method": "Full-Band Power Distribution",
                "start_time": 0,
                "end_time": 30,
                "high_pass": None,
                "low_pass": None,
                "start_time_": None,
                "end_time_": None,
                "selected_event_names": json.dumps(["闭眼 [1]"]),
            })
            task_id = Task.insert(SQLLiteDB_Only_MainTread.user_db, task)
            TaskTemplate.insert(SQLLiteDB_Only_MainTread.user_db,template_id, task_id)

            task = Task.from_dict({
                "name": "闭眼后全频段比率分布",
                "analysis_method": "Full-Band Ratio Distribution",
                "start_time": 0,
                "end_time": 30,
                "high_pass": None,
                "low_pass": None,
                "start_time_": None,
                "end_time_": None,
                "selected_event_names": json.dumps(["闭眼 [1]"]),
            })
            task_id = Task.insert(SQLLiteDB_Only_MainTread.user_db, task)
            TaskTemplate.insert(SQLLiteDB_Only_MainTread.user_db,template_id, task_id)

            task = Task.from_dict({
                "name": "功率谱密度",
                "analysis_method": "Power Spectral Density",
                "start_time": 0,
                "end_time": 30,
                "high_pass": None,
                "low_pass": None,
                "start_time_": None,
                "end_time_": None,
                "selected_event_names": json.dumps(["闭眼 [1]"]),
            })
            task_id = Task.insert(SQLLiteDB_Only_MainTread.user_db, task)
            TaskTemplate.insert(SQLLiteDB_Only_MainTread.user_db,template_id, task_id)



    def showInfo(self, file_path):
        file_extension = os.path.splitext(file_path)[1].lower()
        QLLogging.log.debug("enter EdfReader")
        edf_r = EdfReader(file_path)
        QLLogging.log.debug("EdfReader successfully")
        start_time = edf_r.getStartdatetime()

        max_sfreq = None
        try:
            sample_rates = edf_r.getSampleFrequencies()
            if sample_rates is not None and len(sample_rates) > 0:
                max_sfreq = float(max(sample_rates))
        except Exception as e:
            QLLogging.log.warning(f"获取采样率失败: {e}")

        if max_sfreq is not None:
            QLLogging.log.debug(f"采样率: {max_sfreq:.2f}Hz")
            print(f"采样率: {max_sfreq:.2f}Hz")

        if max_sfreq is not None and max_sfreq > 1000:
            try:
                edf_r.close()
            except Exception:
                pass
            del edf_r
            QMessageBox.warning(self, "提示", f"采样率超过1000Hz（当前{max_sfreq:.2f}Hz），无法导入该文件。")
            return

        try:
            edf_r.close()
        except Exception:
            pass
        del edf_r

        if file_extension == '.edf':
            QLLogging.log.debug("enter mne.io.read_raw_edf")
            self.raw = mne.io.read_raw_edf(file_path, preload=True, verbose=False)
            QLLogging.log.debug("mne.io.read_raw_edf successfully")
            # self.raw._data = self.raw.get_data().astype('float32') # 将数据转换为float32类型

        elif file_extension == '.bdf':
            QLLogging.log.debug("enter mne.io.read_raw_bdf")
            self.raw = mne.io.read_raw_bdf(file_path, preload=True, verbose=False)
            QLLogging.log.debug("mne.io.read_raw_bdf successfully")

        try:
            raw_sfreq = float(self.raw.info.get('sfreq', 0))
        except Exception:
            raw_sfreq = 0
        QLLogging.log.debug(f"采样率(read_raw): {raw_sfreq:.2f}Hz")

        # 直接将数据转换为微伏（而不是先存储在中间变量中）
        self.raw._data *= 1e6  # 将数据转换为微伏，直接修改self.raw._data

        # 如果你只想保留最终处理后的数据，创建一个新的 RawArray 对象
        QLLogging.log.debug("enter mne.io.RawArray")
        self.raw_processed = mne.io.RawArray(self.raw._data, self.raw.info)
        QLLogging.log.debug("mne.io.RawArray successfully")

        # 重要：复制 annotations（事件）到 raw_processed
        # RawArray 创建时不会自动复制 annotations，需要手动复制
        if hasattr(self.raw, 'annotations') and self.raw.annotations is not None:
            try:
                self.raw_processed.set_annotations(self.raw.annotations)
                QLLogging.log.info(f"成功复制 annotations 到 raw_processed: {len(self.raw.annotations)} 个事件")
                # 记录前几个事件的详细信息
                if len(self.raw.annotations) > 0:
                    for i in range(min(3, len(self.raw.annotations))):
                        QLLogging.log.info(
                            f"  事件 {i + 1}: {self.raw.annotations.description[i]} @ {self.raw.annotations.onset[i]}s")
            except Exception as e:
                QLLogging.log.warning(f"复制 annotations 时出错: {e}")
                import traceback
                QLLogging.log.debug(f"复制 annotations 错误详情: {traceback.format_exc()}")
        else:
            QLLogging.log.warning("原始 raw 对象没有 annotations 或 annotations 为 None")

        n_channels = len(self.raw_processed.ch_names)
        n_times = self.raw_processed.n_times
        sfreq = self.raw_processed.info['sfreq']
        QLLogging.log.info(f"采样率: {sfreq:.2f}Hz")
        print(f"采样率: {sfreq:.2f}Hz")
        if sfreq > 1000:
            QMessageBox.warning(self, "提示", f"采样率超过1000Hz（当前{sfreq:.2f}Hz），无法导入该文件。")
            self.raw = None
            self.raw_processed = None
            return
        total_duration = n_times / sfreq

        data = self.raw_processed.get_data()
        file_size = os.path.getsize(file_path)  # 获取文件大小（字节）
        actual_size = round(file_size / (1024 * 1024), 2)

        # 文件大小限制：QEEG(21通道) 1GB，QLanalyser(4通道) 800MB
        if n_channels == 23:
            size_limit_mb = 1024
            size_limit_label = "1GB"
        elif n_channels == 4:
            size_limit_mb = 800
            size_limit_label = "800MB"
        else:
            # 其他通道数默认按 QLanalyser 规则限制
            size_limit_mb = 800
            size_limit_label = "800MB"

        if actual_size > size_limit_mb:
            QMessageBox.warning(
                self,
                "提示",
                f"文件大小超过限制（当前 {actual_size:.2f}MB，限制 {size_limit_label}），无法导入该文件。"
            )
            self.raw = None
            self.raw_processed = None
            return

        memory_usage_mb = data.size * data.itemsize / (1024 ** 2)
        memory_usage_mb = round(memory_usage_mb, 2)

        # 添加内容到textEdit中的内容
        ch_name = self.raw_processed.info['ch_names']
        sfreq = self.raw_processed.info['sfreq']
        meas_date = self.raw_processed.info['meas_date']

        print("date", meas_date, type(meas_date))
        print("date", meas_date.strftime("%Y-%m-%d %H:%M:%S"), type(meas_date.strftime("%Y-%m-%d %H:%M:%S")))

        try:
            new_ch_name = []

            change_ch_name = False

            for ch in ch_name:
                if ch in self.ch_name_mapping:
                    change_ch_name = True
                    new_ch_name.append(self.ch_name_mapping[ch])
            # 需要有一个条件
            if change_ch_name:
                ch_name = new_ch_name

                # 假设 self.raw_processed 是 MNE 的 Raw 对象，ch_name 是新通道名称列表
                # 构建原通道名和新通道名的映射字典
                name_mapping = {old_name: new_name for old_name, new_name in
                                zip(self.raw_processed.ch_names, ch_name)}
                # 执行重命名
                self.raw_processed.rename_channels(name_mapping)
        except Exception as e:
            QLLogging.log.exception(f"{e}")

        self.ch_name = ch_name
        # 删除不再需要的原始数据
        del self.raw

    def setupUi(self, qeeg_analysis):
        qeeg_analysis.setObjectName("qeeg_analysis")
        qeeg_analysis.resize(1440, 900)
        qeeg_analysis.setStyleSheet(ControlStyle.get_widget_style())

        # 设置主窗口的大小策略为可扩展
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(qeeg_analysis.sizePolicy().hasHeightForWidth())
        qeeg_analysis.setSizePolicy(sizePolicy)

        # 主布局
        if self.is_host_computer:
            self.central_widget = QWidget()
            qeeg_analysis.setCentralWidget(self.central_widget)
            self.main_layout = QVBoxLayout(self.central_widget)
        else:
            self.main_layout = QVBoxLayout(qeeg_analysis)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.top_widget = TopWidget(qeeg_analysis)
        self.top_widget.setFixedHeight(80)
        top_widget_size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.top_widget.setSizePolicy(top_widget_size_policy)

        self.top_widget.btn_Subjectdb.clicked.connect(lambda checked, text=0: self.switch_page(text))  # 受试者数据库
        self.top_widget.btn_task_config.clicked.connect(lambda checked, text=1: self.switch_page(text))  # 任务配置
        self.top_widget.btn_report_generation.clicked.connect(lambda checked, text=2: self.switch_page(text))  # 报告生成

        # 添加分割线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setStyleSheet("background-color: #a9a9a9;")
        separator.setFixedHeight(1)

        self.main_layout.addWidget(self.top_widget)
        self.main_layout.addWidget(separator)

        # ========== 主内容区 ==========

        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        # 1. 档案录入页面
        self.subject_input_page = SubjectInputPage(self)
        self.load_subjects_from_db()
        self.subject_input_page.check_empty_state()
        self.subject_input_page.search_edit.textChanged.connect(self.on_search)  # 搜索
        self.subject_input_page.add_btn.clicked.connect(self.on_add_subject)  # 添加

        # self.subject_input_page.table.horizontalHeader().setSortIndicator(4, self.sort_order)
        self.subject_input_page.table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)

        self.subject_input_page.pagination.page_changed.connect(self.on_page_changed)  # 换页

        self.stacked_widget.addWidget(self.subject_input_page)

        # 2. 任务配置页面（空页面）
        self.task_config_page = TaskConfigPage(self)
        self.stacked_widget.addWidget(self.task_config_page)
        self.task_config_page.clicked_signal.connect(lambda params, p=2: self.switch_page(p, False, params))

        self.top_widget.image_upload_signal.connect(lambda path: self.set_image_path(path))

        # 3. 生成报告页面（空页面）
        self.report_generate_page = None
        # self.stacked_widget.addWidget(self.report_generate_page)

        if self.is_host_computer:
            self.showInfo(self.edfpath)
            self.top_widget.btn_Subjectdb.setDisabled(True)
            subject = {
                "id":"0000000000",
                "name":self.username,
                "age":self.age,
                "gender": self.gender,
                "create_date": self.create_date,
                "height": "",
                "weight": "",
                "bmi": 0,
                "analyst": self.analyst,
            }
            self.goto_task_config(subject)
        else:
            # 默认选中第一个页面（档案录入）
            self.switch_page(0)

        self.retranslateUi(qeeg_analysis)

    def calculate_bmi(self,height_edit,weight_edit):
        """根据身高体重计算BMI"""
        try:
            height = float(height_edit.text()) / 100  # 转米
            weight = float(weight_edit.text())
            if height <= 0 or weight <= 0:
                self.bmi_edit.setText("")
                return
            bmi = weight / (height * height)
            self.bmi_edit.setText(f"{bmi:.2f}")
        except ValueError:
            self.bmi_edit.setText("")

    def set_image_path(self, path):
        """设置logo图片路径，如果报告已生成则更新logo"""
        self.task_config_page.image_path = path

        # 如果报告已经生成，更新报告中的logo
        if self.report_generate_page is not None and hasattr(self.report_generate_page, 'update_logo'):
            try:
                self.report_generate_page.update_logo(path)
                print(f"报告logo已更新: {path}")
            except Exception as e:
                print(f"更新报告logo失败: {e}")
                import traceback
                traceback.print_exc()

    # ========== 页面切换核心方法 ==========
    def switch_page(self, page_name, is_record=None, algo_results=None, relative_path=None, switch_subject=False):
        """切换页面并更新导航按钮样式"""
        # 1. 切换StackedWidget页面
        if page_name == 0:
            self.stacked_widget.setCurrentWidget(self.subject_input_page)
            self.top_widget.btn_Subjectdb.setStyleSheet(ControlStyle.get_topWidget_Button_clicked())
            self.top_widget.btn_task_config.setStyleSheet(ControlStyle.get_topWidget_Button())
            self.top_widget.btn_report_generation.setStyleSheet(ControlStyle.get_topWidget_Button())
        elif page_name == 1:
            if switch_subject == True:
                # 1. 从 stacked_widget 中移除旧的 task_config_page
                self.stacked_widget.removeWidget(self.task_config_page)

                # 2. 删除旧的 task_config_page（先获取引用再删除）
                old_page = self.task_config_page
                old_page.setParent(None)
                old_page.deleteLater()

                # 3. 创建新的 task_config_page
                self.task_config_page = TaskConfigPage(self)

                self.task_config_page.clicked_signal.connect(
                    lambda params, p=2: self.switch_page(p, False, params))  # 重新连接

                # 4. 将新的 task_config_page 添加到 stacked_widget 中
                self.stacked_widget.addWidget(self.task_config_page)

                # 5. 确保 stacked_widget 知道有新的页面
                self.stacked_widget.setCurrentWidget(self.task_config_page)

                # 设置当前页面和按钮样式
            self.stacked_widget.setCurrentWidget(self.task_config_page)
            self.top_widget.btn_Subjectdb.setStyleSheet(ControlStyle.get_topWidget_Button())
            self.top_widget.btn_task_config.setStyleSheet(ControlStyle.get_topWidget_Button_clicked())
            self.top_widget.btn_report_generation.setStyleSheet(ControlStyle.get_topWidget_Button())

        elif page_name == 2:
            self.top_widget.btn_report_generation.setDisabled(False)
            if is_record == True:
                print(relative_path)
                # 检查文件类型，根据扩展名选择使用哪个页面类
                if relative_path and (relative_path.endswith('.html') or relative_path.endswith('.htm')):
                    # 使用HTMLReportPage显示HTML文件
                    self.report_generate_page = HTMLReportPage('报告生成', relative_path)
                else:
                    # 使用ReportGeneratePage显示PDF文件
                    self.report_generate_page = ReportGeneratePage('报告生成', relative_path)
                self.stacked_widget.addWidget(self.report_generate_page)
            else:
                if self.report_generate_page is not None and algo_results is not None:
                    self.stacked_widget.removeWidget(self.report_generate_page)
                    self.report_generate_page = None

                if self.report_generate_page is None:
                    from .Analyze_report_pro import ReportPreviewWindow
                    # 获取上传的logo路径（如果存在）
                    logo_path = self.task_config_page.image_path if hasattr(self.task_config_page,
                                                                            'image_path') else None
                    self.report_generate_page = ReportPreviewWindow(algo_results, self, logo_path=logo_path)
                    self.stacked_widget.addWidget(self.report_generate_page)

            self.stacked_widget.setCurrentWidget(self.report_generate_page)
            self.top_widget.btn_Subjectdb.setStyleSheet(ControlStyle.get_topWidget_Button())
            self.top_widget.btn_task_config.setStyleSheet(ControlStyle.get_topWidget_Button())
            self.top_widget.btn_report_generation.setStyleSheet(ControlStyle.get_topWidget_Button_clicked())

    def retranslateUi(self, qeeg_analysis):
        _translate = QCoreApplication.translate
        qeeg_analysis.setWindowTitle(_translate("qeeg_analysis", "QEEG Analysis - AI based model"))

    def on_header_clicked(self, column):
        """表头点击事件处理（仅处理录入日期列）"""
        # 只处理录入日期列（索引4）
        if column not in [2, 4, 7]:
            return
        # 切换排序方向
        if self.sort_order == Qt.AscendingOrder:
            self.sort_order = Qt.DescendingOrder
        else:
            self.sort_order = Qt.AscendingOrder
        # 更新排序指示器
        self.subject_input_page.table.horizontalHeader().setSortIndicator(column, self.sort_order)
        # 重新加载表格数据（会触发排序）
        self.update_table_data()

    def load_subjects_from_db(self):
        """从数据库加载受试者数据"""
        try:
            # 使用Subject类的方法查询所有记录
            subjects = Subject.select_all(SQLLiteDB_Only_MainTread.user_db)

            # 清空当前数据
            self.subject_data = []

            # 转换数据格式
            for subject in subjects:
                self.subject_data.append({
                    "id": subject.id,
                    "name": subject.name,
                    "age": subject.age if subject.age is not None else "",
                    "gender": subject.gender,
                    "create_date": subject.create_date,
                    "height": subject.height if subject.height is not None else "",
                    "weight": subject.weight if subject.weight is not None else "",
                    "bmi": float(subject.bmi) if subject.bmi is not None else 0.0,
                    "analyst": subject.analyst if subject.analyst is not None else "",
                })

            # 更新表格显示
            self.update_table_data()

        except Exception as e:
            QMessageBox.warning(self, "数据库错误", f"加载数据失败: {str(e)}")

    def update_table_data(self, filtered_data=None):
        """更新表格数据"""
        data = filtered_data if filtered_data is not None else self.subject_data

        # 对录入日期列进行排序
        if self.sort_column == 4:  # 录入日期列
            # 将日期字符串转为datetime对象进行排序（确保排序准确）
            data.sort(
                key=lambda x: datetime.datetime.strptime(x["create_date"], "%Y-%m-%d %H:%M:%S"),
                reverse=(self.sort_order == Qt.DescendingOrder)
            )

        total_count = len(data)
        total_pages = math.ceil(total_count / self.page_size)

        # 更新分页控件
        self.subject_input_page.pagination.set_total_pages(total_pages)

        # 计算当前页数据范围
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, total_count)
        page_data = data[start_idx:end_idx]

        # 清空表格
        self.subject_input_page.table.setRowCount(0)

        # 填充数据
        for row, subject in enumerate(page_data):
            self.subject_input_page.table.insertRow(row)
            # 设置单元格数据
            id_item = QTableWidgetItem(str(subject["id"]))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.subject_input_page.table.setItem(row, 0, id_item)
            name_item = QTableWidgetItem(str(subject["name"]))
            name_item.setTextAlignment(Qt.AlignCenter)
            self.subject_input_page.table.setItem(row, 1, name_item)
            age_item = QTableWidgetItem(str(subject["age"]))
            age_item.setTextAlignment(Qt.AlignCenter)
            self.subject_input_page.table.setItem(row, 2, age_item)
            gender_item = QTableWidgetItem(str(subject["gender"]))
            gender_item.setTextAlignment(Qt.AlignCenter)
            self.subject_input_page.table.setItem(row, 3, gender_item)
            create_date_item = QTableWidgetItem(str(subject["create_date"]))
            create_date_item.setTextAlignment(Qt.AlignCenter)
            self.subject_input_page.table.setItem(row, 4, create_date_item)
            height_item = QTableWidgetItem(str(subject["height"]))
            height_item.setTextAlignment(Qt.AlignCenter)
            self.subject_input_page.table.setItem(row, 5, height_item)
            weight_item = QTableWidgetItem(str(subject["weight"]))
            weight_item.setTextAlignment(Qt.AlignCenter)
            self.subject_input_page.table.setItem(row, 6, weight_item)

            widget = QWidget()
            widget.setObjectName("Widget")
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(25, 15, 25, 15)
            layout.setAlignment(Qt.AlignCenter)

            # 1. 创建容器Widget（必须有这个中间容器）
            # 创建BMI容器组件
            bmi_container = QWidget()
            # 如果确实需要固定尺寸，可以取消注释，但建议让布局自动调整
            # 创建水平布局
            bmi_layout = QHBoxLayout(bmi_container)
            bmi_layout.setContentsMargins(5, 5, 5, 5)
            bmi_layout.setAlignment(Qt.AlignCenter)  # 设置整个布局居中

            # 创建标签并设置（BMI 显示 1 位小数）
            bmi_label = QLabel(f"{subject['bmi']:.1f}" if subject['bmi'] is not None else "--")

            # 方法1：使用setAlignment方法（推荐）
            bmi_label.setAlignment(Qt.AlignCenter)

            # 方法2：或者使用样式表中的qproperty-alignment（二选一）
            # 注意：如果同时使用，样式表会覆盖setAlignment

            # 设置标签的大小策略，确保它填充可用空间
            bmi_label.setSizePolicy(
                QSizePolicy.Expanding,  # 水平方向扩展
                QSizePolicy.Expanding  # 垂直方向扩展
            )

            # 根据BMI设置样式
            bmi_value = subject['bmi'] if subject['bmi'] is not None else 0
            if bmi_value < 18.5:  # blue
                bmi_label.setStyleSheet(
                    ControlStyle.get_qeeg_font_500("#388CCD", "14") + "qproperty-alignment: 'AlignCenter';")
                bmi_container.setStyleSheet(ControlStyle.get_background_border_widget("#C4EFFF", "20"))
            elif 18.5 <= bmi_value < 24:  # green
                bmi_label.setStyleSheet(
                    ControlStyle.get_qeeg_font_500("#FF0D9669", "14") + "qproperty-alignment: 'AlignCenter';")
                bmi_container.setStyleSheet(ControlStyle.get_background_border_widget("#D1F9E3", "20"))
            else:  # red
                bmi_label.setStyleSheet(
                    ControlStyle.get_qeeg_font_500("#EB5A50", "14") + "qproperty-alignment: 'AlignCenter';")
                bmi_container.setStyleSheet(ControlStyle.get_background_border_widget("#FFE1E1", "20"))

            # 将标签添加到布局
            bmi_layout.addWidget(bmi_label)
            layout.addWidget(bmi_container)
            # 将容器添加到表格
            # self.subject_input_page.table.setCellWidget(row, 7, bmi_container)
            self.subject_input_page.table.setCellWidget(row, 7, widget)
            analyst_display = subject["analyst"] if subject["analyst"] else "--"
            analyst_item = QTableWidgetItem(analyst_display)
            analyst_item.setTextAlignment(Qt.AlignCenter)
            self.subject_input_page.table.setItem(row, 8, analyst_item)

            # 操作按钮
            btn_widget = QWidget()
            btn_widget.setObjectName("actionWidget")
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 0, 4, 0)
            btn_layout.setSpacing(4)

            # 分析按钮
            analysis_btn = QPushButton("分析")
            icon = QIcon("./resource/picture/analysis.png")
            analysis_btn.setIcon(icon)
            analysis_btn.setIconSize(QSize(18, 18))
            analysis_btn.setStyleSheet(ControlStyle.get_analysis_btn_style())
            ControlStyle.get_font_size(analysis_btn, 10)
            analysis_btn.clicked.connect(lambda _, s=subject: self.goto_task_config(s))
            btn_layout.addWidget(analysis_btn)

            # 查看历史按钮
            history_btn = QPushButton()
            history_btn.setStyleSheet("""
                background-color: transparent;
                border: none;
            """)
            icon = QIcon("./resource/picture/history_record.png")
            history_btn.setIcon(icon)
            history_btn.setIconSize(QSize(18, 18))
            ControlStyle.get_font_size(history_btn, 10)
            history_btn.clicked.connect(lambda _, s=subject: self.on_view_history(s))
            btn_layout.addWidget(history_btn)

            # 修改按钮
            edit_btn = QPushButton()
            edit_btn.setStyleSheet("""
                            background-color: transparent;
                            border: none;
                        """)
            icon = QIcon("./resource/picture/edit.png")
            edit_btn.setIcon(icon)
            edit_btn.setIconSize(QSize(18, 18))
            ControlStyle.get_font_size(edit_btn, 10)
            edit_btn.clicked.connect(lambda _, idx=subject["id"]: self.on_update_subject(idx))
            btn_layout.addWidget(edit_btn)

            # 删除按钮
            del_btn = QPushButton()
            del_btn.setStyleSheet("""
                            background-color: transparent;
                            border: none;
                        """)
            icon = QIcon("./resource/picture/delete.png")
            del_btn.setIcon(icon)
            del_btn.setIconSize(QSize(18, 18))
            ControlStyle.get_font_size(del_btn, 10)
            del_btn.clicked.connect(lambda _, s=subject: self.on_delete_subject(s))
            btn_layout.addWidget(del_btn)

            self.subject_input_page.table.setCellWidget(row, 9, btn_widget)

    def goto_task_config(self, subject):
        """跳转到任务配置页面并设置受试者信息"""
        self.top_widget.currentId_edit.setText(subject["id"])
        self.top_widget.btn_task_config.setDisabled(False)
        if self.top_widget.currentId_edit.text() == "None":
            self.top_widget.currentId_edit.setStyleSheet(ControlStyle.get_qeeg_font_500("#D4D6D9", "16", "right"))
            self.top_widget.currentId_edit.setStyleSheet(ControlStyle.get_qeeg_font_500("#D4D6D9", "14", "right"))
        else:
            self.top_widget.currentId_edit.setStyleSheet(ControlStyle.get_qeeg_font_500("#31373D", "16", "right"))
            self.top_widget.currentId_edit.setStyleSheet(ControlStyle.get_qeeg_font_500("#31373D", "14", "right"))
        self.switch_page(1, switch_subject=True)  # 切换到任务配置页
        self.task_config_page.set_subject_info(subject)  # 传递受试者信息

    def on_page_changed(self, page):
        """页码改变"""
        self.current_page = page
        self.update_table_data()

    def on_search(self):
        """检索功能"""
        search_text = self.subject_input_page.search_edit.text().lower().strip()
        if not search_text:
            self.update_table_data()
            return

        # 按ID或姓名过滤
        filtered_data = [
            subject for subject in self.subject_data
            if search_text in str(subject["id"]).lower() or search_text in subject["name"].lower()
        ]
        self.current_page = 1  # 搜索后回到第一页
        self.update_table_data(filtered_data)

    def on_update_subject(self, subject_id):
        """修改受试者"""
        subject = Subject.get_by_id(SQLLiteDB_Only_MainTread.user_db, subject_id)
        dialog = AddSubjectDialog(self, subject)
        dialog.submit_signal.connect(self.update_subject_data)
        dialog.exec_()

    def update_subject_in_db(self, subject_id, subject_data):
        """更新受试者信息"""
        try:
            # 创建Subject对象
            subject = Subject.from_dict({
                "id": subject_id,
                "name": subject_data["name"],
                "age": int(subject_data["age"]) if subject_data["age"] else None,
                "gender": subject_data["gender"],
                "create_date": subject_data.get("create_date", ""),  # 保持原有创建日期
                "height": float(subject_data["height"]) if subject_data["height"] else None,
                "weight": float(subject_data["weight"]) if subject_data["weight"] else None,
                "bmi": float(subject_data["bmi"]) if subject_data["bmi"] else None,
                "analyst": subject_data["analyst"] if subject_data["analyst"] else None,
                "remark": subject_data["remark"] if subject_data["remark"] else None,
            })

            # 使用Subject类的方法更新数据
            success = Subject.update(SQLLiteDB_Only_MainTread.user_db, subject)
            return success

        except Exception as e:
            QMessageBox.warning(self, "数据库错误", f"更新数据失败: {str(e)}")
            return False

    def update_subject_data(self, subject_data):
        # 更新数据库
        success = self.update_subject_in_db(subject_data["id"], subject_data)
        if success:
            # 刷新表格
            self.load_subjects_from_db()
            QMessageBox.information(self, "成功", "受试者档案更新成功！")

            subject = Subject.get_by_id(SQLLiteDB_Only_MainTread.user_db, subject_data["id"])
            subject = Subject.to_dict(subject)
            self.task_config_page.name_info.setText(subject["name"])
            self.task_config_page.gender_info.setText(subject["gender"])
            self.task_config_page.age_info.setText(str(subject["age"]) + "岁")
            self.task_config_page.bmi_info.setText("BMI:" + str(subject["bmi"]))
            self.task_config_page.current_subject = subject

    def on_add_subject(self):
        """新建受试者"""
        dialog = AddSubjectDialog(self)
        dialog.submit_signal.connect(self.add_subject_data)
        dialog.exec_()

    def add_subject_to_db(self, subject_data):
        """添加受试者到数据库"""
        try:
            # 创建Subject对象
            subject = Subject.from_dict({
                "id": subject_data["id"],
                "name": subject_data["name"],
                "age": int(subject_data["age"]) if subject_data["age"] else None,
                "gender": subject_data["gender"],
                "create_date": subject_data["create_date"],
                "height": float(subject_data["height"]) if subject_data["height"] else None,
                "weight": float(subject_data["weight"]) if subject_data["weight"] else None,
                "bmi": float(subject_data["bmi"]) if subject_data["bmi"] else None,
                "analyst": subject_data["analyst"] if subject_data["analyst"] else None,
                "remark": subject_data["remark"] if subject_data["remark"] else None,
            })

            # 使用Subject类的方法插入数据
            success = Subject.insert(SQLLiteDB_Only_MainTread.user_db, subject)
            return success

        except Exception as e:
            QMessageBox.warning(self, "数据库错误", f"添加数据失败: {str(e)}")
            return False

    def add_subject_data(self, subject_data):
        """添加受试者数据到模拟数据库"""
        # 生成新ID
        # new_id = max([s["id"] for s in self.subject_data]) + 1 if self.subject_data else 1

        # 添加数据到数据库
        success = self.add_subject_to_db(subject_data)
        if success:
            # 刷新表格数据
            self.load_subjects_from_db()
            self.subject_input_page.check_empty_state()
            QMessageBox.information(self, "成功", "受试者档案录入成功！")

    def _delete_history_file(self, file_path):
        """删除历史报告文件（存在则删除）"""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            QLLogging.log.debug(f"Failed to delete history file: {file_path}, error: {e}")

    def delete_subject_from_db(self, subject_id):
        """从数据库删除受试者"""
        try:
            # 删除关联历史记录及其本地文件
            records = HistoryTask.get_by_subject_id(SQLLiteDB_Only_MainTread.user_db, subject_id)
            for record in records:
                self._delete_history_file(record.relative_path)
                HistoryTask.delete(SQLLiteDB_Only_MainTread.user_db, record.id)

            # 使用Subject类的方法删除数据
            success = Subject.delete(SQLLiteDB_Only_MainTread.user_db, subject_id)
            return success

        except Exception as e:
            QMessageBox.warning(self, "数据库错误", f"删除数据失败: {str(e)}")
            return False

    def on_delete_subject(self, subject):
        """删除受试者（二次确认）"""
        name = subject["name"]
        id = subject["id"]
        # 二次确认
        reply = QMessageBox.question(
            self, "确认删除受试者数据?",
            f"确定要删除受试者<span style='color:#2A87DB;'>【{name}  {id} 】</span>的数据吗？删除后将无法找回！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # 从数据库删除
            success = self.delete_subject_from_db(id)
            if success:
                # 刷新表格
                self.load_subjects_from_db()
                self.subject_input_page.check_empty_state()
                QMessageBox.information(self, "成功", "受试者档案已删除！")

    def on_view_history(self, subject):
        """点击详情按钮弹出历史记录对话框"""
        records = HistoryTask.get_by_subject_id(SQLLiteDB_Only_MainTread.user_db, subject["id"])

        # 清空当前数据
        self.history_data = []

        # 转换数据格式
        for record in records:
            self.history_data.append({
                "id": record.id,
                "name": record.name,
                "created_date": record.created_date,
                "relative_path": record.relative_path,
                "subject_id": record.subject_id
            })
            # 检查路径是否存在
            # 不存在
            if not os.path.exists(record.relative_path):
                HistoryTask.delete(SQLLiteDB_Only_MainTread.user_db, record.id)
                print(record.id, record.relative_path, "deleted")

        self.history_dialog = HistoryRecordDialog(subject, self)
        self.load_table_history_data(subject["id"])
        self.history_dialog.exec_()

    def goto_report_generate(self, id):
        """跳转到报告生成页面并设置受试者信息"""
        try:
            self.top_widget.btn_report_generation.setDisabled(False)
            relative_path = HistoryTask.get_by_id(SQLLiteDB_Only_MainTread.user_db, id).relative_path
            # self.task_report_generate_page.set_subject_info(relative_path)
            self.switch_page(2, True, None, relative_path)  # 切换到任务配置页
            self.history_dialog.close()
        except Exception as e:
            QMessageBox.warning(self, "提示", "此PDF已被删除或不存在！")
            return None

    def add_record_card(self, record):
        """添加单个历史记录卡片"""
        # 卡片容器
        card_widget = QWidget()
        card_widget.setFixedHeight(109)
        card_widget.setObjectName("card_widget")
        card_widget.setStyleSheet(ControlStyle.get_card_widget_style())
        card_layout = QHBoxLayout(card_widget)
        card_layout.setSpacing(16)
        card_layout.setContentsMargins(12, 12, 12, 12)

        # ========== 卡片左侧：时间 + 记录名称 ==========
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(4)

        # 记录时间（小字）
        date_label = QLabel(record["created_date"])
        date_label.setStyleSheet(ControlStyle.get_history_record_font_1())
        # 记录名称（大字）
        name_label = QLabel(record["name"])
        name_label.setStyleSheet(ControlStyle.get_history_record_font_2())

        content_layout.addWidget(date_label)
        content_layout.addWidget(name_label)
        card_layout.addWidget(content_widget, 1)  # 占大部分宽度

        # ========== 卡片右侧：操作按钮（图标+查看报告） ==========
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(12, 12, 12, 12)
        btn_layout.setSpacing(8)

        # 1. 修改按钮（图标）
        edit_btn = QPushButton()
        edit_btn.setIcon(QIcon("./resource/picture/edit.png"))  # 替换为实际图标路径
        edit_btn.setIconSize(QSize(18, 18))
        edit_btn.setStyleSheet("border:none;")
        edit_btn.clicked.connect(lambda _, r=record: self.on_update_record(r))

        # 2. 删除按钮（图标）
        del_btn = QPushButton()
        del_btn.setIcon(QIcon("./resource/picture/delete.png"))  # 替换为实际图标路径
        del_btn.setIconSize(QSize(18, 18))
        del_btn.setStyleSheet("border:none;")
        del_btn.clicked.connect(lambda _, r=record: self.on_delete_record(r))

        # 3. 查看报告按钮（蓝色按钮）
        view_btn = QPushButton("查看报告")
        view_btn.setStyleSheet(ControlStyle.get_view_btn_style())
        view_btn.setMinimumSize(104, 36)
        view_btn.clicked.connect(lambda _, idx=record["id"]: self.goto_report_generate(idx))

        # 添加按钮到布局
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(view_btn)
        card_layout.addWidget(btn_widget)

        # 将卡片添加到容器
        self.history_dialog.records_layout.addWidget(card_widget)
    def extract_report_timestamp(self, record: dict) -> str:
        """从报告文件路径中提取时间戳。"""
        relative_path = record.get("relative_path", "") if isinstance(record, dict) else ""
        if not relative_path:
            return ""
        record_name = os.path.splitext(os.path.basename(relative_path))[0]
        match = re.search(r'_(\d{8}_\d{6})$', record_name)
        return match.group(1) if match else ""

    def load_table_history_data(self, sid):
        """加载历史记录数据到表格"""
        records = HistoryTask.get_by_subject_id(SQLLiteDB_Only_MainTread.user_db, sid)

        # 清空当前数据
        self.history_data = []

        # 转换数据格式
        for record in records:
            # 检查路径是否存在，不存在则删库并跳过本次显示
            if not record.relative_path or not os.path.exists(record.relative_path):
                HistoryTask.delete(SQLLiteDB_Only_MainTread.user_db, record.id)
                print(record.id, record.relative_path, "deleted")
                continue

            self.history_data.append({
                "id": record.id,
                "name": record.name,
                "created_date": record.created_date,
                "relative_path": record.relative_path,
                "subject_id": record.subject_id
            })

        self.history_data.sort(
            key=self.extract_report_timestamp,
            reverse=True
        )
        while self.history_dialog.records_layout.count() > 0:
            child = self.history_dialog.records_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for row, record in enumerate(self.history_data):
            self.add_record_card(record)

        self.history_dialog.records_layout.addStretch()

    def on_update_record(self, record):
        """修改历史记录"""
        dialog = EditHistoryDialog(record,  self)
        dialog.submit_signal.connect(self.update_record_data)
        dialog.exec_()

    def add_record_in_db(self, record):
        # 创建Subject对象
        record = HistoryTask.from_dict({
            "id": record["id"],
            "name": record["name"],
            "created_date": record["created_date"] if record["created_date"] else None,
            "relative_path": record["relative_path"] if record["relative_path"] else None,
            "subject_id": record["subject_id"] if record["subject_id"] else None,
        })

        # 使用Subject类的方法插入数据
        success = HistoryTask.insert(SQLLiteDB_Only_MainTread.user_db, record)
        if success:
            QMessageBox.warning(self, "数据库sc", f"sc")
        return success

    def update_record_in_db(self, record_id, record_data):
        """更新信息"""
        try:
            # 创建Subject对象
            record = HistoryTask.from_dict({
                "id": record_id,
                "name": record_data["name"],
                "created_date": record_data["created_date"],
                "relative_path": record_data["relative_path"],
                "subject_id": record_data["subject_id"]
            })

            # 使用Subject类的方法更新数据
            success = HistoryTask.update(SQLLiteDB_Only_MainTread.user_db, record)
            return success

        except Exception as e:
            QMessageBox.warning(self, "数据库错误", f"更新数据失败: {str(e)}")
            return False

    def update_record_data(self, record_data):
        # 更新数据库
        success = self.update_record_in_db(record_data["id"], record_data)
        if success:
            # 刷新表格
            self.load_table_history_data(record_data["subject_id"])
            # QMessageBox.information(self, "成功", "历史记录修改成功！")

    def delete_record_from_db(self, id):
        """从数据库删除记录"""
        try:
            success = HistoryTask.delete(SQLLiteDB_Only_MainTread.user_db, id)
            return success

        except Exception as e:
            QMessageBox.warning(self, "数据库错误", f"删除数据失败: {str(e)}")
            return False

    def on_delete_record(self, record):
        """删除历史记录"""
        name = record["name"]
        reply = QMessageBox.question(
            self, "确认删除历史分析记录？",
            f"确定删除<span style='color:#2A87DB;'>【{name}】</span>的分析数据吗？删除后将无法找回！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._delete_history_file(record.get("relative_path"))
            # 从数据库删除
            success = self.delete_record_from_db(record["id"])
            if success:
                # 刷新表格
                self.load_table_history_data(record["subject_id"])
                # QMessageBox.information(self, "成功", "历史记录已删除！")

    def init_database_history_task(self):
        """初始化数据库"""
        try:
            # 连接数据库
            SQLLiteDB_Only_MainTread.connect()

            # 创建表（如果不存在）
            HistoryTask.create_table(SQLLiteDB_Only_MainTread.user_db)

        except Exception as e:
            QMessageBox.warning(self, "数据库错误", f"数据库初始化失败: {str(e)}")
            print(f"数据库错误: {e}")

    def init_database_task_template(self):
        # 连接数据库
        SQLLiteDB_Only_MainTread.connect()
        # 创建表（如果不存在）
        Task.create_table(SQLLiteDB_Only_MainTread.user_db)
        Template.create_table(SQLLiteDB_Only_MainTread.user_db)
        TaskTemplate.create_table(SQLLiteDB_Only_MainTread.user_db)


class QEEGAnalysisMainWindow(QMainWindow):
    notify_update_signal = pyqtSignal(str)
    def __init__(self, edfpath, username, gender,age,create_date,analyst):
        super().__init__()
        # 可能需要存储参数，供后续使用
        self.edfpath = edfpath
        self.username = username
        self.gender = gender
        self.age = age
        self.create_date = create_date
        self.analyst = analyst
        print(f"QEEGAnalysis初始化 - EDF路径: {edfpath}, 用户名: {username}, 性别: {gender},年龄: {age}")

        self.ui = Ui_qeeg_analysis(edfpath, username, gender, age, create_date, analyst,True)
        self.ui.setupUi(self)

        # 创建授权对象，并连接提醒信号
        self.licence = Licence(self)
        self.licence.remind.connect(self.on_remind)

    def on_remind(self, message):
        # 处理提醒，例如显示消息框
        QtWidgets.QMessageBox.information(self, "提醒", message)

    def set_update_task_signal(self, signal):
        """连接更新任务的信号，用于接收更新通知"""
        signal.connect(self.on_update_available)

    def on_update_available(self, msg):
        # 可在此显示更新通知
        pass
