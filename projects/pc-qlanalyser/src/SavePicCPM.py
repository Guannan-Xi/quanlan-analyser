"""保存图片参数的弹窗"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QProgressBar, QApplication,
    QLineEdit, QInputDialog, QComboBox, QSpacerItem, QSizePolicy, QMessageBox, QListView, QToolButton,
    QMenu, QAction, QTextEdit, QFileDialog,QDialog, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QDateTime, QCoreApplication
from PyQt5.QtGui import QPixmap, QIcon
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
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QProgressDialog, QProgressBar, QPushButton
from PyQt5.QtCore import Qt

class SavePictureDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_format = None
        self.save_path = None
        self.resolution = None
        self.win = None
        # 设置窗口标志，允许最小化最大化
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        self.setupUi()
    def setupUi(self):
        self.setObjectName("SavePicCPM")
        self.resize(530, 300)
        self.setFixedHeight(300)
        # 设置一下背景颜色
        self.setStyleSheet(ControlStyle.get_widget_style())

        # 设置整体垂直布局
        self.ui_save_pic_cpm_vlayout = QVBoxLayout(self)
        self.ui_save_pic_cpm_vlayout.setObjectName("ui_save_pic_cpm_vlayout")
        self.ui_save_pic_cpm_vlayout.setContentsMargins(24, 32, 24, 32)
        self.ui_save_pic_cpm_vlayout.setSpacing(30)

        hlayout1 = QHBoxLayout()
        hlayout1.setContentsMargins(0, 0, 0, 0)
        hlayout1.setSpacing(0)

        # format 图片样式 PNG Files (*.png);;JPEG Files (*.jpg *.jpeg);;SVG (*.svg);;TIFF (*.tif *.tiff);;EPS (*.eps);;All Files (*)
        image_format_vlayout = QVBoxLayout()
        image_format_vlayout.setContentsMargins(0, 0, 0, 0)
        image_format_vlayout.setSpacing(0)

        self.label_image_format = QLabel(self)
        self.label_image_format.setObjectName("label_image_format")
        self.label_image_format.setFixedSize(220, 30)
        self.label_image_format.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_image_format, 10)

        self.combobox_image_format = QComboBox(self)
        self.combobox_image_format.setObjectName("combobox_image_format")
        self.combobox_image_format.setFixedSize(220, 40)
        self.combobox_image_format.addItems([".jpg", ".png", ".svg", ".tiff", ".eps"])
        self.combobox_image_format.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_image_format, 10)

        # 添加行高
        # 创建 QListView 并设置行高
        view_image_format = QListView()
        view_image_format.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.combobox_image_format.setView(view_image_format)  # 绑定视图到 QComboBox


        image_format_vlayout.addWidget(self.label_image_format)
        image_format_vlayout.addWidget(self.combobox_image_format)

        # 图形 dpi 设置
        resolution_valyout = QVBoxLayout()
        resolution_valyout.setContentsMargins(0, 0, 0, 0)
        resolution_valyout.setSpacing(0)

        self.label_resolution = QLabel(self)
        self.label_resolution.setObjectName("label_resolution")
        self.label_resolution.setFixedSize(220, 30)
        self.label_resolution.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_resolution, 10)

        self.combobox_resolution = QComboBox(self)
        self.combobox_resolution.setObjectName("combobox_resolution")
        self.combobox_resolution.setFixedSize(220, 40)
        self.combobox_resolution.addItems(["75", "100", "150", "200", "300", "500"])
        self.combobox_resolution.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_resolution, 10)

        # 添加行高
        # 创建 QListView 并设置行高
        view_resolution = QListView()
        view_resolution.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.combobox_resolution.setView(view_resolution)  # 绑定视图到 QComboBox

        resolution_valyout.addWidget(self.label_resolution)
        resolution_valyout.addWidget(self.combobox_resolution)

        hlayout1.addLayout(image_format_vlayout)
        hlayout1.addStretch(1)  # 添加伸缩空间
        hlayout1.addLayout(resolution_valyout)

        # 选择路径
        save_location_vlayout = QVBoxLayout()
        save_location_vlayout.setContentsMargins(0, 0, 0, 0)
        save_location_vlayout.setSpacing(0)

        self.label_save_location = QLabel(self)
        self.label_save_location.setObjectName("label_save_location")
        self.label_save_location.setFixedSize(360, 30)
        self.label_save_location.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_save_location, 10)

        hlayout2 = QHBoxLayout()
        hlayout2.setContentsMargins(0, 0, 0, 0)
        hlayout2.setSpacing(12)

        self.lineEdit_save_location = QLineEdit(self)
        self.lineEdit_save_location.setObjectName("lineEdit_save_location")
        self.lineEdit_save_location.setMinimumSize(350, 40)
        self.lineEdit_save_location.setStyleSheet(ControlStyle.get_lineEdit_style())
        ControlStyle.get_font_size(self.lineEdit_save_location, 10)

        # QIcon file_icon("./resource/picture/file.png")
        # file_icon.addFile(":/image/Max.png")
        # self.pushButton_Browse.setIcon(icon)
        # self.pushButton_Browse.setIconSize(QSize(40, 40))

        self.pushButton_Browse = QPushButton(self)
        self.pushButton_Browse.setObjectName("pushButton_Browse")
        self.pushButton_Browse.setIcon(QIcon("./resource/picture/file.png"))
        self.pushButton_Browse.setFixedSize(40, 40)
        self.pushButton_Browse.setStyleSheet(ControlStyle.get_pushButton_style_white())
        ControlStyle.get_font_size(self.pushButton_Browse, 10)

        hlayout2.addWidget(self.lineEdit_save_location)
        hlayout2.addWidget(self.pushButton_Browse)

        save_location_vlayout.addWidget(self.label_save_location)
        save_location_vlayout.addLayout(hlayout2)

        hlayout3 = QHBoxLayout()
        hlayout3.setContentsMargins(0, 0, 0, 0)
        hlayout3.setSpacing(0)
        hlayout3.setAlignment(Qt.AlignRight)

        self.pushButton_save = QPushButton(self)
        self.pushButton_save.setObjectName("pushButton_save")
        self.pushButton_save.setFixedSize(135, 40)
        self.pushButton_save.setStyleSheet(ControlStyle.get_pushButton_style())
        ControlStyle.get_font_size(self.pushButton_save, 10)

        hlayout3.addWidget(self.pushButton_save)

        self.ui_save_pic_cpm_vlayout.addLayout(hlayout1)
        self.ui_save_pic_cpm_vlayout.addLayout(save_location_vlayout)
        self.ui_save_pic_cpm_vlayout.addLayout(hlayout3)

        self.retranslateUi(self)
        self.connect_actions()

    def retranslateUi(self, SavePicCPM):
        _translate = QCoreApplication.translate
        SavePicCPM.setWindowTitle(_translate("SavePicCPM", "Save Picture"))

        self.label_image_format.setText(_translate("SavePicCPM", "Image Format："))
        self.label_resolution.setText(_translate("SavePicCPM", "Resolution (dpi)："))
        self.label_save_location.setText(_translate("SavePicCPM", "Save Location："))
        self.pushButton_save.setText(_translate("SavePicCPM", "Save"))

    def connect_actions(self):  # 功能连接方法
        self.pushButton_Browse.clicked.connect(self.select_path)
        self.pushButton_save.clicked.connect(self._handle_save)
    def select_path(self):
        selected_path = QFileDialog.getExistingDirectory(
            self.win,
            "Select Save Location"
        )
        if selected_path:
            self.lineEdit_save_location.setText(selected_path)
        else:
            self.lineEdit_save_location.setText("No valid path selected")

    def _handle_save(self):
        """处理保存操作"""
        # 获取所有参数
        self.image_format = self.combobox_image_format.currentText()
        self.resolution = int(self.combobox_resolution.currentText())
        self.save_path = self.lineEdit_save_location.text()

        if not self.save_path or self.save_path == "No valid path selected":
            QMessageBox.warning(
                self.win,
                "Warning",
                "Please select a valid save location."
            )
            return

        # 接受对话框
        self.accept()

    def get_save_parameters(self):
        """返回保存参数"""
        return {
            'format': self.image_format,
            'resolution': self.resolution,
            'path': self.save_path
        }

class SaveDataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_format = None
        self.save_path = None
        self.win = None
        # 设置窗口标志，允许最小化最大化
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        self.setupUi()
    def setupUi(self):
        self.setObjectName("SavePicCPM")
        self.resize(530, 300)
        self.setFixedHeight(300)
        # 设置一下背景颜色
        self.setStyleSheet(ControlStyle.get_widget_style())

        # 设置整体垂直布局
        self.ui_save_pic_cpm_vlayout = QVBoxLayout(self)
        self.ui_save_pic_cpm_vlayout.setObjectName("ui_save_pic_cpm_vlayout")
        self.ui_save_pic_cpm_vlayout.setContentsMargins(24, 32, 24, 32)
        self.ui_save_pic_cpm_vlayout.setSpacing(30)

        # format 图片样式 PNG Files (*.png);;JPEG Files (*.jpg *.jpeg);;SVG (*.svg);;TIFF (*.tif *.tiff);;EPS (*.eps);;All Files (*)
        data_format_vlayout = QVBoxLayout()
        data_format_vlayout.setContentsMargins(0, 0, 0, 0)
        data_format_vlayout.setSpacing(0)

        self.label_data_format = QLabel(self)
        self.label_data_format.setObjectName("label_data_format")
        self.label_data_format.setFixedSize(220, 30)
        self.label_data_format.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_data_format, 10)

        self.combobox_data_format = QComboBox(self)
        self.combobox_data_format.setObjectName("combobox_data_format")
        self.combobox_data_format.setFixedSize(220, 40)
        self.combobox_data_format.addItems([".csv", ".npy"])
        self.combobox_data_format.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_data_format, 10)

        # 添加行高
        # 创建 QListView 并设置行高
        view_image_format = QListView()
        view_image_format.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.combobox_data_format.setView(view_image_format)  # 绑定视图到 QComboBox


        data_format_vlayout.addWidget(self.label_data_format)
        data_format_vlayout.addWidget(self.combobox_data_format)

        # 选择路径
        save_location_vlayout = QVBoxLayout()
        save_location_vlayout.setContentsMargins(0, 0, 0, 0)
        save_location_vlayout.setSpacing(0)

        self.label_save_location = QLabel(self)
        self.label_save_location.setObjectName("label_save_location")
        self.label_save_location.setFixedSize(360, 30)
        self.label_save_location.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_save_location, 10)

        hlayout2 = QHBoxLayout()
        hlayout2.setContentsMargins(0, 0, 0, 0)
        hlayout2.setSpacing(12)

        self.lineEdit_save_location = QLineEdit(self)
        self.lineEdit_save_location.setObjectName("lineEdit_save_location")
        self.lineEdit_save_location.setMinimumSize(350, 40)
        self.lineEdit_save_location.setStyleSheet(ControlStyle.get_lineEdit_style())
        ControlStyle.get_font_size(self.lineEdit_save_location, 10)

        self.pushButton_Browse = QPushButton(self)
        self.pushButton_Browse.setObjectName("pushButton_Browse")

        self.pushButton_Browse.setIcon(QIcon("./resource/picture/file.png"))
        self.pushButton_Browse.setFixedSize(40, 40)

        self.pushButton_Browse.setStyleSheet(ControlStyle.get_pushButton_style_white())
        ControlStyle.get_font_size(self.pushButton_Browse, 10)

        hlayout2.addWidget(self.lineEdit_save_location)
        hlayout2.addWidget(self.pushButton_Browse)

        save_location_vlayout.addWidget(self.label_save_location)
        save_location_vlayout.addLayout(hlayout2)

        hlayout3 = QHBoxLayout()
        hlayout3.setContentsMargins(0, 0, 0, 0)
        hlayout3.setSpacing(0)
        hlayout3.setAlignment(Qt.AlignRight)

        self.pushButton_save = QPushButton(self)
        self.pushButton_save.setObjectName("pushButton_save")
        self.pushButton_save.setFixedSize(135, 40)
        self.pushButton_save.setStyleSheet(ControlStyle.get_pushButton_style())
        ControlStyle.get_font_size(self.pushButton_save, 10)

        hlayout3.addWidget(self.pushButton_save)

        self.ui_save_pic_cpm_vlayout.addLayout(data_format_vlayout)
        self.ui_save_pic_cpm_vlayout.addLayout(save_location_vlayout)
        self.ui_save_pic_cpm_vlayout.addLayout(hlayout3)

        self.retranslateUi(self)
        self.connect_actions()

    def retranslateUi(self, SavePicCPM):
        _translate = QCoreApplication.translate
        SavePicCPM.setWindowTitle(_translate("SavePicCPM", "Save Data"))

        self.label_data_format.setText(_translate("SavePicCPM", "File Format："))
        self.label_save_location.setText(_translate("SavePicCPM", "Save Location："))

        self.pushButton_save.setText(_translate("SavePicCPM", "Save"))

    def connect_actions(self):  # 功能连接方法
        self.pushButton_Browse.clicked.connect(self.select_path)
        self.pushButton_save.clicked.connect(self._handle_save)
        # self.combobox_data_format.currentIndexChanged.connect(self.hide_controls)

    def hide_controls(self):
        """当选择为cache时，将部分控件隐藏"""
        if self.combobox_data_format.currentText() == ".cache":
            self.lineEdit_save_location.hide()
            self.label_save_location.hide()
            self.pushButton_Browse.hide()
            self.lineEdit_save_location.setText("/history")
        else:
            self.lineEdit_save_location.show()
            self.label_save_location.show()
            self.pushButton_Browse.show()
        return

    def select_path(self):
        selected_path = QFileDialog.getExistingDirectory(
            self.win,
            "Select Save Location"
        )
        if selected_path:
            self.lineEdit_save_location.setText(selected_path)
        else:
            self.lineEdit_save_location.setText("No valid path selected")

    def _handle_save(self):
        """处理保存操作"""
        # 获取所有参数
        self.data_format = self.combobox_data_format.currentText()
        self.save_path = self.lineEdit_save_location.text()

        # 验证保存路径
        if not self.save_path or self.save_path == "No valid path selected":
            QMessageBox.warning(
                self.win,
                "Warning",
                "Please select a valid save location."
            )
            return
        # 接受对话框
        self.accept()

    def get_save_parameters(self):
        """返回保存参数"""
        return {
            'format': self.data_format,
            'path': self.save_path
        }


class SaveStatisticalDataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_format = ".xlsx"
        self.save_path = ""
        self.intervention_enabled = False
        self.intervention_time = ""
        self.win = None
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setupUi()

    def _default_intervention_time(self):
        return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    def setupUi(self):
        self.setObjectName("SaveStatisticalData")
        self.resize(620, 320)
        self.setMinimumSize(620, 320)
        self.setStyleSheet(ControlStyle.get_widget_style())
        self.setWindowIcon(QIcon('QL1.ico'))

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(16)
        root_layout.addStretch(1)

        row2_hbox = QHBoxLayout()
        row2_hbox.setContentsMargins(0, 0, 0, 0)
        row2_hbox.setSpacing(12)

        self.label_file_format = QLabel(self)
        self.label_file_format.setObjectName("label_file_format")
        self.label_file_format.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_file_format, 10)
        # root_layout.addWidget(self.label_file_format)

        self.combobox_data_format = QComboBox(self)
        self.combobox_data_format.setObjectName("combobox_data_format")
        self.combobox_data_format.setMinimumSize(180, 40)
        self.combobox_data_format.addItems([".xlsx"])
        self.combobox_data_format.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_data_format, 10)

        view_data_format = QListView()
        view_data_format.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.combobox_data_format.setView(view_data_format)

        self.check_intervention_time = QCheckBox(self)
        self.check_intervention_time.setObjectName("check_intervention_time")
        # self.check_intervention_time.setChecked(True)
        self.check_intervention_time.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.check_intervention_time, 10)

        self.lineEdit_intervention = QLineEdit(self)
        self.lineEdit_intervention.setObjectName("lineEdit_intervention")
        self.lineEdit_intervention.setMinimumSize(100, 40)
        self.lineEdit_intervention.setPlaceholderText("e.g. 20260413-143012")
        self.lineEdit_intervention.setEnabled(False)
        # self.lineEdit_intervention.setText(self._default_intervention_time())
        self.lineEdit_intervention.setStyleSheet(ControlStyle.get_lineEdit_style())
        ControlStyle.get_font_size(self.lineEdit_intervention, 10)

        # self.label_intervention_unit = QLabel(self)
        # self.label_intervention_unit.setObjectName("label_intervention_unit")
        # self.label_intervention_unit.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        # ControlStyle.get_font_size(self.label_intervention_unit, 10)

        row2_vbox_right = QVBoxLayout()
        row2_vbox_right.setContentsMargins(0, 0, 0, 0)
        row2_vbox_right.setSpacing(16)
        row2_vbox_right.addWidget(self.check_intervention_time)
        row2_vbox_right.addWidget(self.lineEdit_intervention)

        row2_vbox_left = QVBoxLayout()
        row2_vbox_left.setContentsMargins(0, 0, 0, 0)
        row2_vbox_left.setSpacing(0)
        row2_vbox_left.addWidget(self.label_file_format)
        row2_vbox_left.addWidget(self.combobox_data_format)

        # root_layout.addLayout(row3)
        # row2.addLayout(self.combobox_data_format)s
        # row2.addStretch(1)
        row2_hbox.addLayout(row2_vbox_left)
        row2_hbox.addLayout(row2_vbox_right)
        row2_hbox.setAlignment(Qt.AlignTop)  # 这一行就够了
        # row2.addWidget(self.check_intervention_time)
        # row2.addWidget(self.lineEdit_intervention)
        # row2.addWidget(self.label_intervention_unit)
        root_layout.addLayout(row2_hbox)



        row4_vbox = QVBoxLayout()
        row4_vbox.setContentsMargins(0, 0, 0, 0)
        row4_vbox.setSpacing(16)

        row4_hbox = QHBoxLayout()
        row4_hbox.setContentsMargins(0, 0, 0, 0)
        row4_hbox.setSpacing(12)

        self.label_save_location = QLabel(self)
        self.label_save_location.setObjectName("label_save_location")
        self.label_save_location.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_save_location, 10)
        # root_layout.addWidget(self.label_save_location)
        row4_vbox.addWidget(self.label_save_location)


        self.lineEdit_save_location = QLineEdit(self)
        self.lineEdit_save_location.setObjectName("lineEdit_save_location")
        self.lineEdit_save_location.setMinimumSize(0, 40)
        # self.lineEdit_save_location.setText("../Sleep_Statistical_data")
        self.lineEdit_save_location.setStyleSheet(ControlStyle.get_lineEdit_style())
        ControlStyle.get_font_size(self.lineEdit_save_location, 10)

        self.pushButton_Browse = QPushButton(self)
        self.pushButton_Browse.setObjectName("pushButton_Browse")
        self.pushButton_Browse.setIcon(QIcon("./resource/picture/file.png"))
        self.pushButton_Browse.setFixedSize(40, 40)
        self.pushButton_Browse.setStyleSheet(ControlStyle.get_pushButton_style_white())
        ControlStyle.get_font_size(self.pushButton_Browse, 10)

        row4_hbox.addWidget(self.lineEdit_save_location)
        row4_hbox.addWidget(self.pushButton_Browse)

        row4_vbox.addLayout(row4_hbox)

        # root_layout.addLayout(row4_vbox)

        # row5 = QHBoxLayout()
        # row5.setContentsMargins(0, 0, 0, 0)
        # row5.setSpacing(0)
        # row5.addStretch(1)

        row4_hbox_right = QHBoxLayout()
        row4_hbox_right.setContentsMargins(0, 0, 0, 0)
        row4_hbox_right.setSpacing(0)
        row4_hbox_right.addStretch(1)

        self.pushButton_save = QPushButton(self)
        self.pushButton_save.setObjectName("pushButton_save")
        self.pushButton_save.setFixedSize(135, 40)
        self.pushButton_save.setStyleSheet(ControlStyle.get_pushButton_style())
        ControlStyle.get_font_size(self.pushButton_save, 10)
        row4_hbox_right.addWidget(self.pushButton_save)
        # root_layout.addLayout(row5)
        row4_vbox.addLayout(row4_hbox_right)
        root_layout.addLayout(row4_vbox)
        root_layout.addStretch(1)

        self.retranslateUi(self)
        self.connect_actions()

    def retranslateUi(self, save_dialog):
        _translate = QCoreApplication.translate
        save_dialog.setWindowTitle(_translate("SaveStatisticalData", "Statistical data"))
        self.label_file_format.setText(_translate("SaveStatisticalData", "File Format:"))
        self.check_intervention_time.setText(_translate("SaveStatisticalData", "Intervention time"))
        # self.label_intervention_unit.setText(_translate("SaveStatisticalData", "timestamp"))
        self.label_save_location.setText(_translate("SaveStatisticalData", "Saving Location:"))
        self.pushButton_save.setText(_translate("SaveStatisticalData", "Save"))

    def connect_actions(self):
        self.pushButton_Browse.clicked.connect(self.select_path)
        self.pushButton_save.clicked.connect(self._handle_save)
        self.check_intervention_time.toggled.connect(self.lineEdit_intervention.setEnabled)

    def select_path(self):
        selected_path = QFileDialog.getExistingDirectory(self.win, "Select Save Location")
        if selected_path:
            self.lineEdit_save_location.setText(selected_path)
        else:
            self.lineEdit_save_location.setText("No valid path selected")

    def _handle_save(self):
        self.data_format = self.combobox_data_format.currentText()
        self.save_path = self.lineEdit_save_location.text().strip()
        self.intervention_enabled = self.check_intervention_time.isChecked()

        if not self.save_path or self.save_path == "No valid path selected":
            QMessageBox.warning(self.win, "Warning", "Please select a valid save location.")
            return

        if self.intervention_enabled:
            try:
                text = self.lineEdit_intervention.text().strip() or self._default_intervention_time()
                datetime.datetime.strptime(text, "%Y%m%d-%H%M%S")
                self.intervention_time = text
            except Exception:
                QMessageBox.warning(self.win, "Warning", "Please enter Intervention time in YYYYmmdd-HHMMSS format.")
                return
        else:
            self.intervention_time = ""

        self.accept()

    def get_save_parameters(self):
        return {
            'format': self.data_format,
            'path': self.save_path,
            'intervention_enabled': self.intervention_enabled,
            'intervention_time': self.intervention_time
        }

from PyQt5.QtWidgets import QCheckBox

class SavePictureDialog1(QDialog):
    """
    保存当前段/所有段
    保存分析/分析加原图
    保存目录
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_format = None
        self.save_path = None
        self.resolution = None
        self.win = None
        # 设置窗口标志，允许最小化最大化
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        self.setupUi()
        # 连接复选框互斥事件
        self.connect_checkbox_events()

    def setupUi(self):
        self.setObjectName("SavePicCPM")
        self.resize(700, 450)  # 调整窗口大小适配新增内容
        self.setFixedHeight(450)
        # 设置一下背景颜色
        self.setStyleSheet(ControlStyle.get_widget_style())

        # 设置整体垂直布局
        self.ui_save_pic_cpm_vlayout = QVBoxLayout(self)
        self.ui_save_pic_cpm_vlayout.setObjectName("ui_save_pic_cpm_vlayout")
        self.ui_save_pic_cpm_vlayout.setContentsMargins(24, 32, 24, 32)
        self.ui_save_pic_cpm_vlayout.setSpacing(20)  # 调整间距

        # ========== 新增 Save Option 部分 ==========
        save_option_layout = QHBoxLayout()
        save_option_layout.setContentsMargins(0, 0, 0, 0)
        save_option_layout.setSpacing(10)

        self.label_save_option = QLabel(self)
        self.label_save_option.setText("Save Segments:")
        self.label_save_option.setFixedSize(150, 30)
        self.label_save_option.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_save_option, 10)

        # 创建一个容器用于放置复选框，确保它们对齐
        checkbox_container = QHBoxLayout()
        checkbox_container.setSpacing(120)  # 增加两个复选框之间的间距

        self.chk_current_segment = QCheckBox("Current", self)
        self.chk_current_segment.setChecked(True)  # 默认选当前段
        self.chk_current_segment.setStyleSheet(ControlStyle.get_checkbox_style())
        ControlStyle.get_font_size(self.chk_current_segment, 10)

        self.chk_all_segments = QCheckBox("All", self)
        self.chk_all_segments.setStyleSheet(ControlStyle.get_checkbox_style())
        ControlStyle.get_font_size(self.chk_all_segments, 10)

        # 添加复选框到容器
        checkbox_container.addWidget(self.chk_current_segment)
        checkbox_container.addWidget(self.chk_all_segments)

        save_option_layout.addWidget(self.label_save_option)
        save_option_layout.addLayout(checkbox_container)
        save_option_layout.addStretch()

        self.ui_save_pic_cpm_vlayout.addLayout(save_option_layout)

        # ========== 新增 Save Mode 部分 ==========
        save_mode_layout = QHBoxLayout()
        save_mode_layout.setContentsMargins(0, 0, 0, 0)
        save_mode_layout.setSpacing(10)

        self.label_save_mode = QLabel(self)
        self.label_save_mode.setText("Save figures:")
        self.label_save_mode.setFixedSize(150, 30)
        self.label_save_mode.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_save_mode, 10)

        # 创建一个容器用于放置复选框，确保它们与上方的复选框对齐
        mode_checkbox_container = QHBoxLayout()
        mode_checkbox_container.setSpacing(105)  # 使用相同的间距值保持对齐

        self.chk_single_graph = QCheckBox("Analysed", self)
        self.chk_single_graph.setChecked(True)  # 默认选单图
        self.chk_single_graph.setStyleSheet(ControlStyle.get_checkbox_style())
        ControlStyle.get_font_size(self.chk_single_graph, 10)

        self.chk_combined_graphs = QCheckBox("Raw", self)
        self.chk_combined_graphs.setStyleSheet(ControlStyle.get_checkbox_style())
        ControlStyle.get_font_size(self.chk_combined_graphs, 10)

        # 添加复选框到容器
        mode_checkbox_container.addWidget(self.chk_single_graph)
        mode_checkbox_container.addWidget(self.chk_combined_graphs)

        save_mode_layout.addWidget(self.label_save_mode)
        save_mode_layout.addLayout(mode_checkbox_container)
        save_mode_layout.addStretch()

        self.ui_save_pic_cpm_vlayout.addLayout(save_mode_layout)

        # ========== 原有 Image Format 和 Resolution 部分 ==========
        hlayout1 = QHBoxLayout()
        hlayout1.setContentsMargins(0, 0, 0, 0)
        hlayout1.setSpacing(20)

        # format 图片样式
        image_format_vlayout = QVBoxLayout()
        image_format_vlayout.setContentsMargins(0, 0, 0, 0)
        image_format_vlayout.setSpacing(0)

        self.label_image_format = QLabel(self)
        self.label_image_format.setText("Image Format:")
        self.label_image_format.setFixedSize(200, 30)
        self.label_image_format.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_image_format, 10)

        self.combobox_image_format = QComboBox(self)
        self.combobox_image_format.setObjectName("combobox_image_format")
        self.combobox_image_format.setFixedSize(300, 40)
        self.combobox_image_format.addItems([".jpg", ".png", ".svg", ".tiff", ".eps"])
        self.combobox_image_format.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_image_format, 10)

        # 添加行高
        view_image_format = QListView()
        view_image_format.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.combobox_image_format.setView(view_image_format)

        image_format_vlayout.addWidget(self.label_image_format)
        image_format_vlayout.addWidget(self.combobox_image_format)

        # 图形 dpi 设置
        resolution_valyout = QVBoxLayout()
        resolution_valyout.setContentsMargins(0, 0, 0, 0)
        resolution_valyout.setSpacing(0)

        self.label_resolution = QLabel(self)
        self.label_resolution.setText("Resolution (dpi):")
        self.label_resolution.setFixedSize(200, 30)
        self.label_resolution.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_resolution, 10)

        self.combobox_resolution = QComboBox(self)
        self.combobox_resolution.setObjectName("combobox_resolution")
        self.combobox_resolution.setFixedSize(300, 40)
        self.combobox_resolution.addItems(["75", "100", "150", "200"])
        self.combobox_resolution.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_resolution, 10)

        # 添加行高
        view_resolution = QListView()
        view_resolution.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.combobox_resolution.setView(view_resolution)

        resolution_valyout.addWidget(self.label_resolution)
        resolution_valyout.addWidget(self.combobox_resolution)

        hlayout1.addLayout(image_format_vlayout)
        hlayout1.addLayout(resolution_valyout)

        self.ui_save_pic_cpm_vlayout.addLayout(hlayout1)

        # ========== 原有 Save Location 部分 ==========
        save_location_vlayout = QVBoxLayout()
        save_location_vlayout.setContentsMargins(0, 0, 0, 0)
        save_location_vlayout.setSpacing(0)

        self.label_save_location = QLabel(self)
        self.label_save_location.setText("Save Location:")
        self.label_save_location.setFixedSize(200, 30)
        self.label_save_location.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_save_location, 10)

        hlayout2 = QHBoxLayout()
        hlayout2.setContentsMargins(0, 0, 0, 0)
        hlayout2.setSpacing(10)

        self.lineEdit_save_location = QLineEdit(self)
        self.lineEdit_save_location.setObjectName("lineEdit_save_location")
        self.lineEdit_save_location.setMinimumSize(300, 40)
        self.lineEdit_save_location.setStyleSheet(ControlStyle.get_lineEdit_style())
        ControlStyle.get_font_size(self.lineEdit_save_location, 10)

        self.pushButton_Browse = QPushButton(self)
        self.pushButton_Browse.setObjectName("pushButton_Browse")
        self.pushButton_Browse.setIcon(QIcon("./resource/picture/file.png"))
        self.pushButton_Browse.setFixedSize(40, 40)
        self.pushButton_Browse.setStyleSheet(ControlStyle.get_pushButton_style_white())
        ControlStyle.get_font_size(self.pushButton_Browse, 10)

        hlayout2.addWidget(self.lineEdit_save_location)
        hlayout2.addWidget(self.pushButton_Browse)

        save_location_vlayout.addWidget(self.label_save_location)
        save_location_vlayout.addLayout(hlayout2)

        self.ui_save_pic_cpm_vlayout.addLayout(save_location_vlayout)

        # ========== 按钮布局 ==========
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(20)
        btn_layout.setAlignment(Qt.AlignRight)

        self.pushButton_save = QPushButton(self)
        self.pushButton_save.setObjectName("pushButton_save")
        self.pushButton_save.setText("Save")
        self.pushButton_save.setFixedSize(100, 40)
        self.pushButton_save.setStyleSheet(ControlStyle.get_pushButton_style())
        ControlStyle.get_font_size(self.pushButton_save, 10)

        self.pushButton_close = QPushButton(self)
        self.pushButton_close.setObjectName("pushButton_close")
        self.pushButton_close.setText("Close")
        self.pushButton_close.setFixedSize(100, 40)
        self.pushButton_close.setStyleSheet(ControlStyle.get_pushButton_style_gray())
        ControlStyle.get_font_size(self.pushButton_close, 10)

        btn_layout.addWidget(self.pushButton_close)
        btn_layout.addWidget(self.pushButton_save)

        self.ui_save_pic_cpm_vlayout.addLayout(btn_layout)

        self.retranslateUi(self)
        self.connect_actions()

    def retranslateUi(self, SavePicCPM):
        _translate = QCoreApplication.translate
        SavePicCPM.setWindowTitle(_translate("SavePicCPM", "Save Picture"))
        self.pushButton_save.setText(_translate("SavePicCPM", "Save"))
        self.pushButton_close.setText(_translate("SavePicCPM", "Close"))

    def connect_actions(self):
        self.pushButton_Browse.clicked.connect(self.select_path)
        self.pushButton_save.clicked.connect(self._handle_save)
        self.pushButton_close.clicked.connect(self.reject)  # 关闭对话框

    def connect_checkbox_events(self):
        """连接复选框事件，实现互斥功能"""
        # Save Option 互斥
        self.chk_current_segment.clicked.connect(self.on_current_segment_checked)
        self.chk_all_segments.clicked.connect(self.on_all_segments_checked)

        # Save Mode 多选但至少选一个
        self.chk_single_graph.clicked.connect(self.on_graph_option_checked)
        self.chk_combined_graphs.clicked.connect(self.on_graph_option_checked)

    def on_graph_option_checked(self):
        """当图形选项被点击时，确保至少有一个选项被选中"""
        if not self.chk_single_graph.isChecked() and not self.chk_combined_graphs.isChecked():
            # 如果两个都没选中，重新选中当前点击的复选框
            sender = self.sender()
            if sender == self.chk_single_graph:
                self.chk_combined_graphs.setChecked(True)
            else:
                self.chk_single_graph.setChecked(True)

    def on_current_segment_checked(self):
        """当Current Segment被选中时，取消All Segments的选中状态，且不可取消选中"""
        if not self.chk_current_segment.isChecked():
            self.chk_current_segment.setChecked(True)
        else:
            self.chk_all_segments.setChecked(False)

    def on_all_segments_checked(self):
        """当All Segments被选中时，取消Current Segment的选中状态，且不可取消选中"""
        if not self.chk_all_segments.isChecked():
            self.chk_all_segments.setChecked(True)
        else:
            self.chk_current_segment.setChecked(False)

    def on_single_graph_checked(self):
        """当Single Graph被选中时，取消Combined Graphs的选中状态，且不可取消选中"""
        if not self.chk_single_graph.isChecked():
            self.chk_single_graph.setChecked(True)
        else:
            self.chk_combined_graphs.setChecked(False)

    def on_combined_graphs_checked(self):
        """当Combined Graphs被选中时，取消Single Graph的选中状态，且不可取消选中"""
        if not self.chk_combined_graphs.isChecked():
            self.chk_combined_graphs.setChecked(True)
        else:
            self.chk_single_graph.setChecked(False)

    def select_path(self):
        selected_path = QFileDialog.getExistingDirectory(
            self,
            "Select Save Location"
        )
        if selected_path:
            self.lineEdit_save_location.setText(selected_path)
        else:
            self.lineEdit_save_location.setText("No valid path selected")

    def _handle_save(self):
        """处理保存操作"""
        # 获取所有参数
        self.image_format = self.combobox_image_format.currentText()
        self.resolution = int(self.combobox_resolution.currentText())
        self.save_path = self.lineEdit_save_location.text()

        # 获取 Save Option 选择 (由于已实现互斥，这里至少有一个被选中)
        is_current_segment = self.chk_current_segment.isChecked()
        is_all_segments = self.chk_all_segments.isChecked()

        # 获取 Save Mode 选择 (现在支持多选)
        is_single_graph = self.chk_single_graph.isChecked()
        is_combined_graphs = self.chk_combined_graphs.isChecked()

        if not self.save_path or self.save_path == "No valid path selected":
            QMessageBox.warning(
                self,
                "Warning",
                "Please select a valid save location."
            )
            return

        # 接受对话框，确认保存
        self.accept()

    def get_save_parameters(self):
        """返回保存参数，包含新增的选项"""
        save_modes = []
        if self.chk_single_graph.isChecked():
            save_modes.append('single')
        if self.chk_combined_graphs.isChecked():
            save_modes.append('combined')

        return {
            'format': self.image_format,
            'resolution': self.resolution,
            'path': self.save_path,
            'save_option': 'current' if self.chk_current_segment.isChecked() else 'all',
            'save_mode': save_modes  # 现在返回列表，如 ['single'] 或 ['combined'] 或 ['single', 'combined']
        }

    def create_progress_dialog(title, label_text, max_value, parent=None):
        """
        创建一个样式化的进度对话框

        :param title: 对话框标题
        :param label_text: 标签文本
        :param max_value: 进度条最大值
        :param parent: 父对象
        :return: 配置好的 QProgressDialog 实例
        """
        progress_dialog = QProgressDialog(label_text, "Cancel", 0, max_value, parent)
        progress_dialog.setWindowTitle(title)
        progress_dialog.setWindowFlags(progress_dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumWidth(300)
        progress_dialog.setMinimumHeight(120)

        # 设置进度条样式
        progress_bar = progress_dialog.findChild(QProgressBar)
        if progress_bar:
            progress_bar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    background-color: #f0f0f0;
                    border-radius: 6px;
                    text-align: left;
                    height: 25px;
                    color: white;
                }
                QProgressBar::chunk {
                    background-color: #2A87DB;
                    width: 20px;
                    margin: 0px;
                }
            """)

        # 设置取消按钮样式
        cancel_btn = progress_dialog.findChild(QPushButton)
        if cancel_btn:
            cancel_btn.setStyleSheet("""
                font-family: Microsoft YaHei;
                color: #2A87DB;
                border: 1px solid #2A87DB;
                border-radius: 6px;
                padding: 5px 10px;
                background-color: white;
            """)

        progress_dialog.setValue(0)
        return progress_dialog


class SavePictureDialog2(QDialog):
    """
    保存当前段/所有段
    保存目录
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_format = None
        self.save_path = None
        self.resolution = None
        self.win = None
        # 设置窗口标志，允许最小化最大化
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        self.setupUi()
        # 连接复选框互斥事件
        self.connect_checkbox_events()

    def setupUi(self):
        self.setObjectName("SavePicCPM")
        self.resize(700, 450)  # 调整窗口大小适配新增内容
        self.setFixedHeight(450)
        # 设置一下背景颜色
        self.setStyleSheet(ControlStyle.get_widget_style())

        # 设置整体垂直布局
        self.ui_save_pic_cpm_vlayout = QVBoxLayout(self)
        self.ui_save_pic_cpm_vlayout.setObjectName("ui_save_pic_cpm_vlayout")
        self.ui_save_pic_cpm_vlayout.setContentsMargins(24, 32, 24, 32)
        self.ui_save_pic_cpm_vlayout.setSpacing(20)  # 调整间距

        # ========== 新增 Save Option 部分 ==========
        save_option_layout = QHBoxLayout()
        save_option_layout.setContentsMargins(0, 0, 0, 0)
        save_option_layout.setSpacing(10)

        self.label_save_option = QLabel(self)
        self.label_save_option.setText("Save Segments:")
        self.label_save_option.setFixedSize(150, 30)
        self.label_save_option.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_save_option, 10)

        # 创建一个容器用于放置复选框，确保它们对齐
        checkbox_container = QHBoxLayout()
        checkbox_container.setSpacing(120)  # 增加两个复选框之间的间距

        self.chk_current_segment = QCheckBox("Current", self)
        self.chk_current_segment.setChecked(True)  # 默认选当前段
        self.chk_current_segment.setStyleSheet(ControlStyle.get_checkbox_style())
        ControlStyle.get_font_size(self.chk_current_segment, 10)

        self.chk_all_segments = QCheckBox("All", self)
        self.chk_all_segments.setStyleSheet(ControlStyle.get_checkbox_style())
        ControlStyle.get_font_size(self.chk_all_segments, 10)

        # 添加复选框到容器
        checkbox_container.addWidget(self.chk_current_segment)
        checkbox_container.addWidget(self.chk_all_segments)

        save_option_layout.addWidget(self.label_save_option)
        save_option_layout.addLayout(checkbox_container)
        save_option_layout.addStretch()

        self.ui_save_pic_cpm_vlayout.addLayout(save_option_layout)

        # ========== 原有 Image Format 和 Resolution 部分 ==========
        hlayout1 = QHBoxLayout()
        hlayout1.setContentsMargins(0, 0, 0, 0)
        hlayout1.setSpacing(20)

        # format 图片样式
        image_format_vlayout = QVBoxLayout()
        image_format_vlayout.setContentsMargins(0, 0, 0, 0)
        image_format_vlayout.setSpacing(0)

        self.label_image_format = QLabel(self)
        self.label_image_format.setText("Image Format:")
        self.label_image_format.setFixedSize(200, 30)
        self.label_image_format.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_image_format, 10)

        self.combobox_image_format = QComboBox(self)
        self.combobox_image_format.setObjectName("combobox_image_format")
        self.combobox_image_format.setFixedSize(300, 40)
        self.combobox_image_format.addItems([".jpg", ".png", ".svg", ".tiff", ".eps"])
        self.combobox_image_format.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_image_format, 10)

        # 添加行高
        view_image_format = QListView()
        view_image_format.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.combobox_image_format.setView(view_image_format)

        image_format_vlayout.addWidget(self.label_image_format)
        image_format_vlayout.addWidget(self.combobox_image_format)

        # 图形 dpi 设置
        resolution_valyout = QVBoxLayout()
        resolution_valyout.setContentsMargins(0, 0, 0, 0)
        resolution_valyout.setSpacing(0)

        self.label_resolution = QLabel(self)
        self.label_resolution.setText("Resolution (dpi):")
        self.label_resolution.setFixedSize(200, 30)
        self.label_resolution.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_resolution, 10)

        self.combobox_resolution = QComboBox(self)
        self.combobox_resolution.setObjectName("combobox_resolution")
        self.combobox_resolution.setFixedSize(300, 40)
        self.combobox_resolution.addItems(["75", "100", "150", "200"])
        self.combobox_resolution.setStyleSheet(ControlStyle.get_comboBox_word_style())
        ControlStyle.get_font_size(self.combobox_resolution, 10)

        # 添加行高
        view_resolution = QListView()
        view_resolution.setStyleSheet(ControlStyle.get_combobox_list_view())
        self.combobox_resolution.setView(view_resolution)

        resolution_valyout.addWidget(self.label_resolution)
        resolution_valyout.addWidget(self.combobox_resolution)

        hlayout1.addLayout(image_format_vlayout)
        hlayout1.addLayout(resolution_valyout)

        self.ui_save_pic_cpm_vlayout.addLayout(hlayout1)

        # ========== 原有 Save Location 部分 ==========
        save_location_vlayout = QVBoxLayout()
        save_location_vlayout.setContentsMargins(0, 0, 0, 0)
        save_location_vlayout.setSpacing(0)

        self.label_save_location = QLabel(self)
        self.label_save_location.setText("Save Location:")
        self.label_save_location.setFixedSize(200, 30)
        self.label_save_location.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(self.label_save_location, 10)

        hlayout2 = QHBoxLayout()
        hlayout2.setContentsMargins(0, 0, 0, 0)
        hlayout2.setSpacing(10)

        self.lineEdit_save_location = QLineEdit(self)
        self.lineEdit_save_location.setObjectName("lineEdit_save_location")
        self.lineEdit_save_location.setMinimumSize(300, 40)
        self.lineEdit_save_location.setStyleSheet(ControlStyle.get_lineEdit_style())
        ControlStyle.get_font_size(self.lineEdit_save_location, 10)

        self.pushButton_Browse = QPushButton(self)
        self.pushButton_Browse.setObjectName("pushButton_Browse")
        self.pushButton_Browse.setIcon(QIcon("./resource/picture/file.png"))
        self.pushButton_Browse.setFixedSize(40, 40)
        self.pushButton_Browse.setStyleSheet(ControlStyle.get_pushButton_style_white())
        ControlStyle.get_font_size(self.pushButton_Browse, 10)

        hlayout2.addWidget(self.lineEdit_save_location)
        hlayout2.addWidget(self.pushButton_Browse)

        save_location_vlayout.addWidget(self.label_save_location)
        save_location_vlayout.addLayout(hlayout2)

        self.ui_save_pic_cpm_vlayout.addLayout(save_location_vlayout)

        # ========== 按钮布局 ==========
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(20)
        btn_layout.setAlignment(Qt.AlignRight)

        self.pushButton_save = QPushButton(self)
        self.pushButton_save.setObjectName("pushButton_save")
        self.pushButton_save.setText("Save")
        self.pushButton_save.setFixedSize(100, 40)
        self.pushButton_save.setStyleSheet(ControlStyle.get_pushButton_style())
        ControlStyle.get_font_size(self.pushButton_save, 10)

        self.pushButton_close = QPushButton(self)
        self.pushButton_close.setObjectName("pushButton_close")
        self.pushButton_close.setText("Close")
        self.pushButton_close.setFixedSize(100, 40)
        self.pushButton_close.setStyleSheet(ControlStyle.get_pushButton_style_gray())
        ControlStyle.get_font_size(self.pushButton_close, 10)

        btn_layout.addWidget(self.pushButton_close)
        btn_layout.addWidget(self.pushButton_save)

        self.ui_save_pic_cpm_vlayout.addLayout(btn_layout)

        self.retranslateUi(self)
        self.connect_actions()

    def retranslateUi(self, SavePicCPM):
        _translate = QCoreApplication.translate
        SavePicCPM.setWindowTitle(_translate("SavePicCPM", "Save Picture"))
        self.pushButton_save.setText(_translate("SavePicCPM", "Save"))
        self.pushButton_close.setText(_translate("SavePicCPM", "Close"))

    def connect_actions(self):
        self.pushButton_Browse.clicked.connect(self.select_path)
        self.pushButton_save.clicked.connect(self._handle_save)
        self.pushButton_close.clicked.connect(self.reject)  # 关闭对话框

    def connect_checkbox_events(self):
        """连接复选框事件，实现互斥功能"""
        # Save Option 互斥
        self.chk_current_segment.clicked.connect(self.on_current_segment_checked)
        self.chk_all_segments.clicked.connect(self.on_all_segments_checked)

    def on_current_segment_checked(self):
        """当Current Segment被选中时，取消All Segments的选中状态，且不可取消选中"""
        if not self.chk_current_segment.isChecked():
            self.chk_current_segment.setChecked(True)
        else:
            self.chk_all_segments.setChecked(False)

    def on_all_segments_checked(self):
        """当All Segments被选中时，取消Current Segment的选中状态，且不可取消选中"""
        if not self.chk_all_segments.isChecked():
            self.chk_all_segments.setChecked(True)
        else:
            self.chk_current_segment.setChecked(False)


    def select_path(self):
        selected_path = QFileDialog.getExistingDirectory(
            self,
            "Select Save Location"
        )
        if selected_path:
            self.lineEdit_save_location.setText(selected_path)
        else:
            self.lineEdit_save_location.setText("No valid path selected")

    def _handle_save(self):
        """处理保存操作"""
        # 获取所有参数
        self.image_format = self.combobox_image_format.currentText()
        self.resolution = int(self.combobox_resolution.currentText())
        self.save_path = self.lineEdit_save_location.text()

        # 获取 Save Option 选择 (由于已实现互斥，这里至少有一个被选中)
        is_current_segment = self.chk_current_segment.isChecked()
        is_all_segments = self.chk_all_segments.isChecked()


        if not self.save_path or self.save_path == "No valid path selected":
            QMessageBox.warning(
                self,
                "Warning",
                "Please select a valid save location."
            )
            return

        # 接受对话框，确认保存
        self.accept()

    def get_save_parameters(self):
        """返回保存参数，包含新增的选项"""
        return {
            'format': self.image_format,
            'resolution': self.resolution,
            'path': self.save_path,
            'save_option': 'current' if self.chk_current_segment.isChecked() else 'all',
        }
