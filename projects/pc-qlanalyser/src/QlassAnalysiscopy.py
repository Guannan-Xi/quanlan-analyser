from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget, QPushButton, QListWidget,
                             QProgressBar, QLabel, QComboBox, QPlainTextEdit, QSizePolicy,
                             QGridLayout, QCheckBox, QLineEdit, QFileDialog, QInputDialog, QHBoxLayout, QVBoxLayout,
                             QSlider, QFrame)
from PyQt5.QtCore import (QThread, pyqtSignal, pyqtSlot, QRect, Qt,
                          QCoreApplication, QMetaObject)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import QStyle, QStyleOptionSlider
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.lines

import numpy as np
import pandas as pd
import sys
import os
import time
import mne
import joblib
import pickle
from contextlib import redirect_stdout
import io

from .Qlass.my_functions import *
import os
import scipy.signal
from .Domain.HistoricalWarehouse import SleepScoreWH
from scipy.signal import stft


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
        self.save_path = None
        self.timestamp_dir = None
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
            prev_stage = stages[i - 1]
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
            return None

    def run(self):
        """运行睡眠阶段分析"""
        try:
            # np.random.seed(42)
            progress = 0
            self.signal.emit([progress, "Analysis started"])

            # 加载模型
            model_path = os.path.join(os.path.dirname(__file__), "Qlass", "models", f"{self.model_name}.pkl")
            self.model = joblib.load(model_path)
            print(self.model.get_params())
            progress = 10
            self.signal.emit([progress, "Model loaded successfully"])

            self.raw_processed.resample(sfreq=100)

            # 使用Data_Info.py创建的时间戳目录
            self.timestamp_dir = self.raw_processed.info.get('description')
            if not self.timestamp_dir:
                raise ValueError("No valid save path found in raw.info['description']")
            self.save_path = os.path.join(self.timestamp_dir, 'Sleep Analysis')
            os.makedirs(self.save_path, exist_ok=True)

            # 获取通道索引
            ch_names = self.raw_processed.ch_names
            eeg_idx = ch_names.index(self.eeg_channel)
            emg_idx = ch_names.index(self.emg_channel)
            acc_idx = ch_names.index(self.acc_channel)

            # 获取所有通道数据

            # 获取通道数据时立即降采样，减少内存使用
            data = self.raw_processed.get_data()
            self.eeg_data = data[eeg_idx]
            self.emg_data = data[emg_idx]
            self.acc_data = data[acc_idx] * 1e-6

            # 释放原始数据
            del data

            # 提取特征
            self.signal.emit([progress, "Extracting features..."])
            features_df = extract_features_from_raw(
                self.raw_processed,
                epoch_len=self.epoch_length,
                model_name=self.model_name,
                save_path=self.save_path,
                emg_channel=self.emg_channel,
                eeg_channel=self.eeg_channel
            )
            # features_df.to_csv(os.path.join(
            #         self.save_path,"test.csv"))
            progress = 80
            self.signal.emit([progress, "Features extracted, making predictions..."])

            # 预测
            # features = features_df.columns.tolist()
            features = features_df.columns.tolist()
            print(features)
            # X = pd.DataFrame()

            # predictions = self.model.predict(features_df[features])
            predictions = self.model.predict(features_df)
            # del features_df

            progress = 90
            self.signal.emit([progress, "Creating score file..."])

            # 创建得分文件
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

            # 保存分期结果
            if self.save_path:
                print(self.save_path)

                score_filepath = os.path.join(
                    self.save_path,
                    f"epoch_length_{self.epoch_length}_.csv"
                )
                df_score.to_csv(score_filepath, index=False)
                self.signal.emit([progress, f"Saved score file to: {score_filepath}"])
            else:
                self.signal.emit([progress, "Score file not saved - no valid file path available"])

            # 保存结果到内存
            self.df_score = df_score
            progress = 100
            self.signal.emit([progress, "Analysis completed"])

            # 在完成分析后立即清理大型数据
            if hasattr(self, 'model'):
                del self.model
            del features_df
            del features

            # 计算时频图数据
            self.spectrogram_data = self.calculate_spectrogram()



        except Exception as e:
            self.signal.emit([0, f"Error: {str(e)}"])
        finally:
            self._is_running = False


class Ui_qlass_analysis(QWidget):
    # closed = QtCore.pyqtSignal()  # 定义信号

    def __init__(self):
        super().__init__()
        # Configure matplotlib for better performance
        plt.rcParams['agg.path.chunksize'] = 10000  # Increase chunk size for complex paths
        plt.rcParams['path.simplify'] = True  # Enable path simplification
        plt.rcParams['path.simplify_threshold'] = 0.5  # Increase simplification threshold

        self.raw_processed = None  # 添加raw_processed属性
        self.map_colors = {1: "orange", 2: "blue", 3: "red"}
        self.map_stages = {1: "Wake", 2: "NREM", 3: "REM"}
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

    def import_raw(self, raw):
        """导入原始数据"""
        try:
            self.raw_processed = raw
            self.thread_run.raw_processed = self.raw_processed
            self.edf_path = raw.info['description']
            if raw is not None:
                self.button_run.setEnabled(True)

                # 更新通道选择下拉菜单
                ch_names = raw.ch_names

                # 清空并更新所有通道下拉菜单
                self.combobox_emg.clear()
                self.combobox_eeg.clear()
                self.combobox_acc.clear()

                self.combobox_emg.addItems(ch_names)
                self.combobox_eeg.addItems(ch_names)
                self.combobox_acc.addItems(ch_names)

                # 设置默认选择
                default_eeg = "EEG3"
                default_emg = "EEG1"
                default_acc = "ACC0"  # 设置 ACC0 为默认值

                if default_eeg in ch_names:
                    self.combobox_eeg.setCurrentText(default_eeg)

                if default_emg in ch_names:
                    self.combobox_emg.setCurrentText(default_emg)

                if default_acc in ch_names:
                    self.combobox_acc.setCurrentText(default_acc)
        except Exception as e:
            print(f"Error in import_raw: {str(e)}")

    def setupUi(self, qlass_analysis):
        qlass_analysis.setObjectName("qlass_analysis")
        qlass_analysis.resize(1600, 1000)

        # 设置主窗口的大小策略为可扩展
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(qlass_analysis.sizePolicy().hasHeightForWidth())
        qlass_analysis.setSizePolicy(sizePolicy)

        # 创建布局
        self.main_layout = QHBoxLayout(qlass_analysis)

        # 左侧面板
        self.left_panel = QWidget()
        self.left_panel.setFixedWidth(400)
        left_layout = QVBoxLayout(self.left_panel)

        epoch_length_layout = QHBoxLayout()
        self.label_epoch_length = QLabel("Epoch Length(sec):")
        self.label_epoch_length.setStyleSheet("font: 10pt;")
        self.combobox_epoch_length = QComboBox()
        self.combobox_epoch_length.setStyleSheet("font: 10pt;")
        self.combobox_epoch_length.addItems(["4", "10", "20"])

        epoch_length_layout.addWidget(self.label_epoch_length)
        epoch_length_layout.addWidget(self.combobox_epoch_length)

        left_layout.addLayout(epoch_length_layout)

        # Channel Selection
        channel_selection_layout = QHBoxLayout()
        self.label_channel_selection = QLabel("Channel Selection:")
        self.label_channel_selection.setStyleSheet("font: 10pt;")
        channel_selection_layout.addWidget(self.label_channel_selection)
        left_layout.addLayout(channel_selection_layout)

        # EEG Channel Selection
        eeg_layout = QHBoxLayout()
        self.label_eeg = QLabel("EEG:")
        self.label_eeg.setStyleSheet("font: 10pt;")
        self.combobox_eeg = QComboBox()
        self.combobox_eeg.setStyleSheet("font: 10pt;")
        eeg_layout.addWidget(self.label_eeg)
        eeg_layout.addWidget(self.combobox_eeg)
        left_layout.addLayout(eeg_layout)

        # EMG Channel Selection
        emg_layout = QHBoxLayout()
        self.label_emg = QLabel("EMG:")
        self.label_emg.setStyleSheet("font: 10pt;")
        self.combobox_emg = QComboBox()
        self.combobox_emg.setStyleSheet("font: 10pt;")
        emg_layout.addWidget(self.label_emg)
        emg_layout.addWidget(self.combobox_emg)
        left_layout.addLayout(emg_layout)

        # ACC Channel Selection
        acc_layout = QHBoxLayout()
        self.label_acc = QLabel("ACC:")
        self.label_acc.setStyleSheet("font: 10pt;")
        self.combobox_acc = QComboBox()
        self.combobox_acc.setStyleSheet("font: 10pt;")
        acc_layout.addWidget(self.label_acc)
        acc_layout.addWidget(self.combobox_acc)
        left_layout.addLayout(acc_layout)

        # Progress Label and Bar
        progress_layout = QVBoxLayout()

        # 添加标签
        self.label_progress = QLabel("Progress:")
        self.label_progress.setStyleSheet("font: 10pt;")
        progress_layout.addWidget(self.label_progress)

        # 添加上方间距
        progress_layout.addSpacing(5)  # 添加5个像素的间距

        # 进度条
        self.progressBar = QProgressBar()
        self.progressBar.setStyleSheet("QProgressBar {background-color: lightgray; height: 20px;}")
        progress_layout.addWidget(self.progressBar)

        # 添加下方间距
        progress_layout.addSpacing(10)  # 添加10个像素的间距

        # 将progress_layout添加到left_layout
        left_layout.addLayout(progress_layout)

        self.label_status = QLabel("")
        self.label_status.setStyleSheet("font: 10pt;")
        left_layout.addWidget(self.label_status)

        # Run Button
        self.button_run = QPushButton("Score and Save")
        self.button_run.setStyleSheet("font: 10pt;")
        left_layout.addWidget(self.button_run)

        # Plot Button
        self.button_plot = QPushButton("Visualize")
        self.button_plot.setStyleSheet("font: 10pt;")
        self.button_plot.setEnabled(False)
        left_layout.addWidget(self.button_plot)

        # Add Abort Button
        self.button_abort = QPushButton("Abort")
        self.button_abort.setStyleSheet("font: 10pt;")
        self.button_abort.setEnabled(False)  # 初始状态禁用
        left_layout.addWidget(self.button_abort)

        # Log TextBox
        self.textbox = QPlainTextEdit()
        self.textbox.setStyleSheet("font: 10pt;")
        self.textbox.setReadOnly(True)
        left_layout.addWidget(self.textbox)

        # 右侧面板
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)

        # 顶部控制区
        top_controls = QHBoxLayout()

        # Navigation Buttons
        nav_buttons = QHBoxLayout()
        self.button_previous_more = QPushButton("<<")
        self.button_previous_more.setStyleSheet("font: 10pt;")
        self.button_previous_more.setEnabled(False)

        self.button_previous = QPushButton("<")
        self.button_previous.setStyleSheet("font: 10pt;")
        self.button_previous.setEnabled(False)

        self.button_goto_epoch = QPushButton("Go to Epoch")
        self.button_goto_epoch.setStyleSheet("font: 10pt;")
        self.button_goto_epoch.setEnabled(False)

        self.button_next = QPushButton(">")
        self.button_next.setStyleSheet("font: 10pt;")
        self.button_next.setEnabled(False)

        self.button_next_more = QPushButton(">>")
        self.button_next_more.setStyleSheet("font: 10pt;")
        self.button_next_more.setEnabled(False)

        nav_buttons.addWidget(self.button_previous_more)
        nav_buttons.addWidget(self.button_previous)
        nav_buttons.addWidget(self.button_goto_epoch)
        nav_buttons.addWidget(self.button_next)
        nav_buttons.addWidget(self.button_next_more)

        # Select number of epochs to display
        epochs_control = QHBoxLayout()
        self.label_select_number_epochs = QLabel("Epochs per page:")
        self.label_select_number_epochs.setStyleSheet("font: 10pt;")
        self.label_select_number_epochs.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # 设置标签右对齐
        epochs_control.addWidget(self.label_select_number_epochs)
        epochs_control.setSpacing(20)  # 设置组件之间的间距为5像素
        self.combobox_select_n_epochs = QComboBox()
        self.combobox_select_n_epochs.addItems(["All", "100", "50", "30", "20", "10", "5", "3"])
        self.combobox_select_n_epochs.setEnabled(False)
        epochs_control.addWidget(self.combobox_select_n_epochs)

        # Stage Selection
        stage_selection = QHBoxLayout()
        self.label_selected_epoch_stage = QLabel("Stage Edit and Save:")
        self.label_selected_epoch_stage.setStyleSheet("font: 10pt;")
        self.label_selected_epoch_stage.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # 设置标签右对齐
        stage_selection.addWidget(self.label_selected_epoch_stage)
        stage_selection.setSpacing(20)
        self.combobox_selected_epoch_stage = QComboBox()
        self.combobox_selected_epoch_stage.addItems(["Wake", "NREM", "REM"])
        self.combobox_selected_epoch_stage.setEnabled(False)
        stage_selection.addWidget(self.combobox_selected_epoch_stage)
        self.undo_button = QPushButton("Undo")
        self.undo_button.setEnabled(False)
        self.undo_button.setFixedWidth(50)
        stage_selection.addWidget(self.undo_button)
        self.redo_button = QPushButton("Redo")
        self.redo_button.setEnabled(False)
        self.redo_button.setFixedWidth(50)

        stage_selection.addWidget(self.redo_button)

        # Add amplitude range selectors
        amplitude_control = QHBoxLayout()
        # Add some spacing
        amplitude_control.addSpacing(100)

        # EEG amplitude selector
        self.label_eeg_amplitude = QLabel("EEG Range (uV):")
        self.label_eeg_amplitude.setStyleSheet("font: 10pt;")
        self.label_eeg_amplitude.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.combobox_eeg_amplitude = QComboBox()
        self.combobox_eeg_amplitude.setStyleSheet("font: 10pt;")
        self.combobox_eeg_amplitude.addItems(["±100", "±200", "±500", "±1000", "Auto"])
        self.combobox_eeg_amplitude.setCurrentText("±500")
        amplitude_control.addWidget(self.label_eeg_amplitude)
        amplitude_control.addWidget(self.combobox_eeg_amplitude)

        # Add some spacing
        amplitude_control.addSpacing(20)

        # EMG amplitude selector
        self.label_emg_amplitude = QLabel("EMG Range (uV):")
        self.label_emg_amplitude.setStyleSheet("font: 10pt;")
        self.label_emg_amplitude.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.combobox_emg_amplitude = QComboBox()
        self.combobox_emg_amplitude.setStyleSheet("font: 10pt;")
        self.combobox_emg_amplitude.addItems(["±50", "±100", "±200", "±500", "Auto"])
        self.combobox_emg_amplitude.setCurrentText("±200")
        amplitude_control.addWidget(self.label_emg_amplitude)
        amplitude_control.addWidget(self.combobox_emg_amplitude)

        # Add some spacing
        amplitude_control.addSpacing(20)

        # ACC amplitude selector
        self.label_acc_amplitude = QLabel("ACC Range (mG):")
        self.label_acc_amplitude.setStyleSheet("font: 10pt;")
        self.label_acc_amplitude.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.combobox_acc_amplitude = QComboBox()
        self.combobox_acc_amplitude.setStyleSheet("font: 10pt;")
        self.combobox_acc_amplitude.addItems(["±500", "±1000", "±2000", "±4000", "Auto"])
        self.combobox_acc_amplitude.setCurrentText("±2000")
        amplitude_control.addWidget(self.label_acc_amplitude)
        amplitude_control.addWidget(self.combobox_acc_amplitude)

        # Add all controls to top layout
        top_controls.addLayout(nav_buttons)
        top_controls.addLayout(epochs_control)
        top_controls.addLayout(stage_selection)
        top_controls.addLayout(amplitude_control)
        right_layout.addLayout(top_controls)

        # Matplotlib Figure
        # self.figure = Figure(figsize=(15, 8))
        # 使用局部设置
        self.figure = Figure(dpi=20)
        # 设置此figure的字体大小
        self.figure.set_size_inches(15, 8)  # 保持原有的figure大小

        self.canvas = FigureCanvasQTAgg(self.figure)

        from .Infrastructure.QLWidgets.QLToolbar.QLNavigationToolbar import QLNavigationToolbar as NavigationToolbar

        self.toolbar = NavigationToolbar(self.canvas, self, self.textbox)
        right_layout.addWidget(self.toolbar)
        right_layout.addWidget(self.canvas)

        # 添加滑块
        slider_layout = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setEnabled(False)  # 初始禁用
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)  # 初始设为0，后续会更新
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(1)

        # 添加鼠标点击事件处理
        self.slider.mousePressEvent = self.slider_mouse_press

        slider_layout.addWidget(self.slider)
        right_layout.addLayout(slider_layout)

        # Add panels to main layout
        self.main_layout.addWidget(self.left_panel)
        self.main_layout.addWidget(self.right_panel)

        # Connect signals
        self.button_run.clicked.connect(self.run_analysis)
        self.button_plot.clicked.connect(self.plot_results)
        self.button_previous.clicked.connect(self.update_display_previous)

        self.button_previous_more.clicked.connect(self.update_display_previous_more)
        self.button_next.clicked.connect(self.update_display_next)
        self.button_next_more.clicked.connect(self.update_display_next_more)
        self.button_goto_epoch.clicked.connect(self.update_display_goto_epoch)
        self.combobox_select_n_epochs.currentIndexChanged.connect(self.update_display_n_epochs)
        self.combobox_selected_epoch_stage.currentIndexChanged.connect(self.user_edit_stage)
        self.combobox_epoch_length.currentIndexChanged.connect(self.update_epoch_length)
        self.undo_button.clicked.connect(self.undo_edit);
        self.redo_button.clicked.connect(self.redo_edit);
        self.slider.valueChanged.connect(self.on_slider_changed)
        self.combobox_eeg_amplitude.currentTextChanged.connect(
            lambda: self.update_signal_range(self.combobox_eeg_amplitude))
        self.combobox_emg_amplitude.currentTextChanged.connect(
            lambda: self.update_signal_range(self.combobox_emg_amplitude))
        self.combobox_acc_amplitude.currentTextChanged.connect(
            lambda: self.update_signal_range(self.combobox_acc_amplitude))

        # Connect abort button
        self.button_abort.clicked.connect(self.abort_analysis)

        self.retranslateUi(qlass_analysis)
        QMetaObject.connectSlotsByName(qlass_analysis)

    def retranslateUi(self, qlass_analysis):
        _translate = QCoreApplication.translate
        qlass_analysis.setWindowTitle(_translate("qlass_analysis", "Sleep Analysis - AI based model"))
        # self.label_wake_code.setText(_translate("qlass_analysis", f"Wake: {1}"))
        # self.label_nrem_code.setText(_translate("qlass_analysis", f"NREM: {2}"))
        # self.label_rem_code.setText(_translate("qlass_analysis", f"REM: {3}"))

    def run_analysis(self):
        """运行分析"""
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
                self.thread_run.emg_channel = self.combobox_emg.currentText()
                self.thread_run.eeg_channel = self.combobox_eeg.currentText()
                self.thread_run.acc_channel = self.combobox_acc.currentText()
                self.thread_run.model_name = self.model_name

                # 开始分析
                self.progressBar.setValue(0)
                self.button_run.setEnabled(False)
                self.button_abort.setEnabled(True)  # 启用中止按钮
                self.thread_run.start()

            except Exception as e:
                print(f"Error in run_analysis cleanup: {str(e)}")

    def abort_analysis(self):
        """中止分析过程"""
        try:
            # 停止线程
            if self.thread_run.isRunning():
                self.thread_run.terminate()  # 强制终止线程
                self.thread_run.wait()  # 等待线程完全停止

            # 清理数据
            for attr in ['eeg_data', 'emg_data', 'acc_data', 'model',
                         'spectrogram_data', 'df_score']:
                if hasattr(self.thread_run, attr):
                    delattr(self.thread_run, attr)

            # 重置进度条和状态
            self.progressBar.setValue(0)
            self.label_status.setText("Analysis aborted")
            self.textbox.appendPlainText("Analysis aborted by user")

            # 重置按钮状态
            self.button_run.setEnabled(True)
            self.button_abort.setEnabled(False)
            self.button_plot.setEnabled(False)

            # 重置其他UI元素
            self.combobox_select_n_epochs.setEnabled(False)
            self.combobox_selected_epoch_stage.setEnabled(False)
            self.button_previous.setEnabled(False)
            self.button_previous_more.setEnabled(False)
            self.button_next.setEnabled(False)
            self.button_next_more.setEnabled(False)
            self.button_goto_epoch.setEnabled(False)
            self.redo_button.setEnabled(False)
            self.undo_button.setEnabled(False)
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
            self.textbox.appendPlainText(f"Error during abort: {str(e)}")

    def update_progress(self, emitted_signal):
        """更新进度条和状态"""
        progress, message = emitted_signal
        self.progressBar.setValue(progress)
        self.label_status.setText(message)
        self.textbox.appendPlainText(message)

        if progress == 100:
            self.df_score = self.thread_run.df_score
            self.n_epochs = len(self.df_score)

            # 更新滑块设置
            self.slider.setEnabled(True)
            self.slider.setMaximum(max(0, self.n_epochs - self.get_n_epochs_display()))

            self.button_plot.setEnabled(True)
            self.button_abort.setEnabled(False)  # 分析完成后禁用中止按钮
            self.enable_navigation_controls()

    def enable_navigation_controls(self):
        """启导航控件"""
        self.combobox_select_n_epochs.setEnabled(True)
        self.button_previous.setEnabled(True)
        self.button_previous_more.setEnabled(True)
        self.button_next.setEnabled(True)
        self.button_next_more.setEnabled(True)
        self.button_goto_epoch.setEnabled(True)
        self.combobox_selected_epoch_stage.setEnabled(True)

    def get_start_end_time(self):
        from datetime import datetime, timedelta
        import numpy as np
        time_span_total = len(self.thread_run.eeg_data) / self.raw_processed.info['sfreq']

        time_format = "%Y-%m-%d %H:%M:%S"
        start_time = self.raw_processed.info['meas_date']
        next_hour = (start_time + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        hour_span1 = next_hour - start_time

        spans = np.arange(hour_span1.seconds, time_span_total, 3600)  # 1h span
        return next_hour.hour, spans

    def fill_vline_per_hour(self, axes):
        next_start_hour, spans = self.get_start_end_time()
        print(f"next_start_hour：{next_start_hour}, spans:{spans}")

        across_days = 0
        across_day_text = ""
        for hour in spans:
            axes.axvline(x=hour, color='gray', linestyle='--', linewidth=10, alpha=0.7)

            # 在虚线上方添加文本描述
            if across_days > 0:
                across_day_text = f"(+{across_days})"
            formatted_next_start_hour = f"{next_start_hour:02d}:00 {across_day_text}"
            axes.text(hour + 10, 0.1, formatted_next_start_hour,
                      verticalalignment='top', horizontalalignment='left',
                      color='black', fontsize=40, fontweight='bold',
                      transform=axes.get_xaxis_transform())
            next_start_hour = next_start_hour + 1
            if next_start_hour >= 24:
                next_start_hour = 0
                across_days = across_days + 1

    def plot_results(self):
        """绘制分析结果"""
        if self.df_score is None:
            print("No score data available")
            return

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

            # 断开之前的事件连接
            if hasattr(self, '_onclick_cid'):
                self.canvas.mpl_disconnect(self._onclick_cid)
            if hasattr(self, 'key_press_event'):
                self.canvas.mpl_disconnect(self.key_press_event)
            if hasattr(self, 'key_release_event'):
                self.canvas.mpl_disconnect(self.key_release_event)

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

            n_epochs_display = self.get_n_epochs_display()

            # 获取降采样数据

            # print(self.raw_processed.info["sfreq"])
            # resampled_data = self.raw_processed.get_data() * 1e-6
            eeg_data = self.thread_run.eeg_data

            # 计算时间数组 (使用100Hz采样率)
            time_sec = np.arange(0, len(eeg_data) / 100, 1 / 100)
            time_epochs_start = np.arange(len(self.scores)) * self.epoch_length
            time_epochs_end = time_epochs_start + self.epoch_length

            # 创建子图 - 更新比例以适应新的布局
            gs = self.figure.add_gridspec(5, 1, height_ratios=[1, 2, 1, 1, 2])

            # 1. 睡眠分期图
            ax_hypnogram = self.figure.add_subplot(gs[0])
            # ax_hypnogram.plot(time_epochs_start, self.scores, "|", markersize=70, color="black")
            ax_hypnogram.hlines(self.scores, time_epochs_start, time_epochs_end,
                                colors=self.color_epochs, linewidths=40)

            ax_hypnogram.set_yticks([1, 2, 3])
            ax_hypnogram.set_yticklabels(["Wake", "NREM", "REM"])
            ax_hypnogram.get_xaxis().set_visible(False)
            ax_hypnogram.set_ylim(0, 3.5)
            ax_hypnogram.set_ylabel("Stage")

            # 整点垂线
            self.fill_vline_per_hour(ax_hypnogram)

            # 2. EEG信号
            ax_eeg = self.figure.add_subplot(gs[1])
            ax_eeg.plot(time_sec, eeg_data, 'k-', linewidth=1.0)  # 增加线宽到1.0
            ax_eeg.set_ylabel("EEG Amplitude\n(uV)")
            ax_eeg.get_xaxis().set_visible(False)

            # 根据当前选择的范围设置EEG y轴限制
            eeg_range = self.combobox_eeg_amplitude.currentText()
            if eeg_range != "Auto":
                amplitude = float(eeg_range.replace('±', ''))
                ax_eeg.set_ylim([-amplitude, amplitude])

            # 3. EMG包络线 - 增加线宽
            ax_emg = self.figure.add_subplot(gs[2])
            if hasattr(self.thread_run, 'emg_data'):
                emg_data = self.thread_run.emg_data
                emg_envelope = np.abs(scipy.signal.hilbert(emg_data))
                ax_emg.plot(time_sec, emg_envelope, 'g-', linewidth=1.0)  # 增加线宽到1.0
                ax_emg.set_ylabel('EMG Envelope\n(uV)')
                ax_emg.set_xticklabels([])

                # 设置EMG包络线范围
                emg_range = self.combobox_emg_amplitude.currentText()
                if emg_range != "Auto":
                    amplitude = int(emg_range.replace('±', ''))
                    ax_emg.set_ylim([0, amplitude])

            # 4. ACC信号 - 增加线宽
            ax_acc = self.figure.add_subplot(gs[3])
            if hasattr(self.thread_run, 'acc_data'):
                acc_data = self.thread_run.acc_data
                ax_acc.plot(time_sec, acc_data, 'b-', linewidth=1.0)  # 增加线宽到1.0
                ax_acc.set_ylabel('ACC Amplitude\n(mG)')
                ax_acc.set_xticklabels([])

                # 设置ACC范围
                acc_range = self.combobox_acc_amplitude.currentText()
                if acc_range != "Auto":
                    amplitude = int(acc_range.replace('±', ''))
                    ax_acc.set_ylim([-amplitude, amplitude])

            # 5. EEG时频图
            ax_spectrogram = self.figure.add_subplot(gs[4])
            if hasattr(self.thread_run, 'spectrogram_data'):
                spec_data = self.thread_run.spectrogram_data
                if spec_data is not None and isinstance(spec_data, dict):  # 确保spec_data是字典且不为空
                    try:
                        ax_spectrogram.imshow(
                            spec_data['power'],
                            extent=[
                                spec_data['times'][0],  # 使用数组的第一个和最后一个元素
                                spec_data['times'][-1],
                                spec_data['frequencies'][0],
                                spec_data['frequencies'][-1]
                            ],
                            aspect='auto',
                            origin='lower',
                            cmap='RdBu_r',
                            vmin=spec_data.get('vmin', None),  # 使用get方法安全访问
                            vmax=spec_data.get('vmax', None)
                        )
                        ax_spectrogram.set_ylabel('EEG Frequency\n(Hz)')
                        ax_spectrogram.get_xaxis().set_visible(False)
                    except Exception as e:
                        print(f"Error plotting spectrogram: {str(e)}")
                        # 如果时频图绘制失败，至少显示一个空白区域
                        ax_spectrogram.text(0.5, 0.5, 'Spectrogram not available',
                                            ha='center', va='center')
            else:
                # 如果没有时频图数据，显示提示信息
                ax_spectrogram.text(0.5, 0.5, 'Spectrogram not available',
                                    ha='center', va='center')

            # 设置x轴范围
            start_time = self.epoch_start * self.epoch_length
            end_time = start_time + (self.epoch_length * n_epochs_display)
            max_time = len(time_sec) / 100
            end_time = min(end_time, max_time)

            for ax in self.figure.axes:
                ax.set_xlim(start_time, end_time)

            # 在绘制图形时设置字体大小
            for ax in self.figure.axes:
                ax.tick_params(labelsize=40)  # 设置刻度标签字体大小
                ax.set_xlabel(ax.get_xlabel(), fontsize=40)  # 设置x轴标签字体大小
                ax.set_ylabel(ax.get_ylabel(), fontsize=40)  # 设置y轴标签字体大小
                ax.set_title(ax.get_title(), fontsize=40)  # 设置标题字体大小

                # 设置轴标签的字体大小
                for label in ax.get_xticklabels():
                    label.set_fontsize(40)
                for label in ax.get_yticklabels():
                    label.set_fontsize(40)

            # 重定义点击事件处理
            def onclick(event):
                self.button_is_pressed = False

                is_in_dragged = self.mouse_is_dragged
                drag_end(event)
                if is_in_dragged:
                    return

                # 基本检查
                if event.inaxes is None or event.button != 1:
                    return

                try:
                    # 计算点击位置对应的epoch
                    new_epoch = int(event.xdata // self.epoch_length)

                    # 验证epoch是否在有效范围内
                    if new_epoch < 0 or new_epoch >= len(self.scores):
                        return

                    # 设置标志，防止combobox变化触发额外的更新
                    self._ignore_combobox_change = True

                    multi_ctrl_selected = False
                    multi_shift_selected = False
                    if event.guiEvent.modifiers() & Qt.ControlModifier:
                        multi_ctrl_selected = True
                        pass
                    else:
                        # 清除所有现有高亮
                        for line in self.highlight_lines:
                            try:
                                line.remove()
                            except:
                                pass
                        self.highlight_lines.clear()
                        if self.shift_is_pressed and self.shift_begin is not None:
                            multi_shift_selected = True

                    if self.shift_is_pressed and self.shift_begin is None:
                        self.shift_begin = new_epoch

                    self.current_selected_epoch = new_epoch
                    print("new_epoch:", new_epoch, self.shift_is_pressed, self.shift_begin, multi_shift_selected,
                          multi_ctrl_selected, self.highlight_lines, self.current_selected_epoch,
                          self.current_selected_epochs)
                    # 始终处理为新选择，除非点击当前选中的epoch
                    if multi_shift_selected:
                        self.current_selected_epochs = []
                        start, end = sorted([new_epoch, self.shift_begin])
                        for epoch_idx in range(start, end + 1):
                            self.current_selected_epochs.append(epoch_idx)

                            # 立即添加高亮
                            for ax in self.figure.axes:
                                line = ax.axvspan(
                                    epoch_idx * self.epoch_length,
                                    (epoch_idx + 1) * self.epoch_length,
                                    color="pink",
                                    alpha=0.3,
                                    zorder=1000
                                )
                                self.highlight_lines.append(line)
                            current_stage = self.df_score.iloc[new_epoch]['Stage']
                            self.combobox_selected_epoch_stage.setEnabled(True)
                            self.combobox_selected_epoch_stage.setCurrentText(current_stage)
                            self.label_status.setText(f"Selected Epoch: {self.current_selected_epochs}")
                            # print("after  multi_shift_selected:", start, end, self.epoch_length, len(self.highlight_lines), len(self.current_selected_epochs))
                    elif new_epoch in self.current_selected_epochs:
                        # 取消选择
                        self.current_selected_epochs.remove(new_epoch)
                        self.current_selected_epoch = None
                        print("before  fiax:", len(self.highlight_lines))
                        for light in self.highlight_lines[:]:
                            if (light.get_xy()[
                                0] == new_epoch * self.epoch_length and light.get_width() == self.epoch_length):
                                light.remove()
                                self.highlight_lines.remove(light)

                            print("after  :", light.get_xy()[0], light.get_width(), new_epoch * self.epoch_length,
                                  self.epoch_length, len(self.highlight_lines))
                        if not multi_ctrl_selected:
                            self.current_selected_epochs = []
                        if len(self.current_selected_epochs) == 0:
                            self.combobox_selected_epoch_stage.setEnabled(False)
                            self.label_status.setText("No epoch selected")
                            self.current_selected_epochs = []
                        print("double clicked:", len(self.highlight_lines), len(self.current_selected_epochs))
                    else:
                        # 先更新内部状态
                        # self.current_selected_epoch = new_epoch
                        if not multi_ctrl_selected:
                            self.current_selected_epochs = []

                        self.current_selected_epochs.append(new_epoch)

                        # 立即添加高亮
                        for ax in self.figure.axes:
                            line = ax.axvspan(
                                new_epoch * self.epoch_length,
                                (new_epoch + 1) * self.epoch_length,
                                color="pink",
                                alpha=0.3,
                                zorder=1000
                            )
                            self.highlight_lines.append(line)

                        # 然后更新UI状态
                        current_stage = self.df_score.iloc[new_epoch]['Stage']
                        self.combobox_selected_epoch_stage.setEnabled(True)
                        self.combobox_selected_epoch_stage.setCurrentText(current_stage)
                        self.label_status.setText(f"Selected Epoch: {self.current_selected_epochs}")
                        print("Selected Epoch:", new_epoch, current_stage)
                    # 立即重绘画布
                    self.canvas.draw()

                    # 重置标志
                    self._ignore_combobox_change = False

                except Exception as e:
                    print(f"Error in onclick: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    self._ignore_combobox_change = False  # 确保在发生错误时也重置标志

            def on_key_press(event):
                print("on_key_press:", event.key)
                if event.key == 'shift':
                    self.shift_is_pressed = True
                    if self.shift_begin is None and self.current_selected_epoch is not None:
                        self.shift_begin = self.current_selected_epoch

            def on_key_release(event):
                if event.key == 'shift':
                    self.shift_is_pressed = False
                    self.shift_begin = None

            def on_press(event):
                # 基本检查
                if event.inaxes is None or event.button != 1:
                    return

                if self.shift_is_pressed or (event.guiEvent.modifiers() & Qt.ControlModifier):
                    return

                try:
                    # 计算点击位置对应的epoch
                    new_epoch = int(event.xdata // self.epoch_length)

                    # 验证epoch是否在有效范围内
                    if new_epoch < 0 or new_epoch >= len(self.scores):
                        return

                    self.button_is_pressed = True;

                    if self.mouse_dragged_begin is None:
                        self.mouse_dragged_begin = new_epoch

                    self.current_selected_epochs = []
                    self.current_selected_epoch = new_epoch
                    for per_line in self.highlight_lines:
                        try:
                            per_line.remove()
                        except:
                            pass
                    self.highlight_lines.clear()

                    # 设置标志，防止combobox变化触发额外的更新
                    self._ignore_combobox_change = True

                    # 不能设置，此处并未真正确认行为，只有等待下个动作，比如release或者motion才能确认真正行为
                    # self.current_selected_epochs.append(new_epoch)
                    # self.current_selected_epoch = new_epoch
                    # 立即添加高亮
                    for ax in self.figure.axes:
                        line = ax.axvspan(
                            new_epoch * self.epoch_length,
                            (new_epoch + 1) * self.epoch_length,
                            color="pink",
                            alpha=0.3,
                            zorder=1000
                        )
                        self.highlight_lines.append(line)

                    # print("on_press:", self.highlight_lines)

                    # 然后更新UI状态
                    current_stage = self.df_score.iloc[new_epoch]['Stage']
                    self.combobox_selected_epoch_stage.setCurrentText(current_stage)
                    self.label_status.setText(f"Selected Epoch: {new_epoch}")
                    # print("Selected Epoch:", new_epoch, current_stage)
                    # 立即重绘画布
                    self.canvas.draw()

                    # 重置标志
                    self._ignore_combobox_change = False
                except Exception as e:
                    print(f"Error in onclick: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    self._ignore_combobox_change = False  # 确保在发生错误时也重置标志

            def drag_end(event):
                self.button_is_pressed = False
                self.mouse_is_dragged = False
                self.mouse_dragged_begin = None

            def on_motion(event):
                if not self.button_is_pressed:
                    return;
                # 基本检查
                if event.inaxes is None or event.button != 1:
                    return

                try:
                    # 计算点击位置对应的epoch
                    new_epoch = int(event.xdata // self.epoch_length)
                    # 验证epoch是否在有效范围内
                    if new_epoch < 0 or new_epoch >= len(self.scores):
                        return
                    if new_epoch == self.mouse_dragged_begin:
                        return
                    self.mouse_is_dragged = True
                    # 设置标志，防止combobox变化触发额外的更新
                    self._ignore_combobox_change = True

                    self.current_selected_epochs = []
                    self.current_selected_epoch = new_epoch
                    for per_line in self.highlight_lines:
                        try:
                            per_line.remove()
                        except:
                            pass
                    self.highlight_lines.clear()

                    start, end = sorted([new_epoch, self.mouse_dragged_begin])
                    for epoch_idx in range(start, end + 1):
                        self.current_selected_epochs.append(epoch_idx)
                        # 立即添加高亮
                        for axes in self.figure.axes:
                            per_line = axes.axvspan(
                                epoch_idx * self.epoch_length,
                                (epoch_idx + 1) * self.epoch_length,
                                color="pink",
                                alpha=0.3,
                                zorder=1000
                            )

                            self.highlight_lines.append(per_line)

                    # print("on_motion:", start, end, len(self.highlight_lines))

                    # 然后更新UI状态
                    current_stage = self.df_score.iloc[new_epoch]['Stage']
                    self.combobox_selected_epoch_stage.setCurrentText(current_stage)
                    self.label_status.setText(f"Selected Epoch: {self.current_selected_epochs}")
                    # print("Selected Epoch:", new_epoch, current_stage)
                    # 立即重绘画布
                    self.canvas.draw()

                    # 重置标志
                    self._ignore_combobox_change = False
                except Exception as e:
                    print(f"Error in onclick: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    self._ignore_combobox_change = False  # 确保在发生错误时也重置标志

            def on_mouse_scroll(event):
                if self.if_select_all_epochs():
                    return
                if event.step > 0:
                    self.update_display_previous()
                else:
                    self.update_display_next()

            # 绑定点击事件
            self._onclick_cid = self.canvas.mpl_connect('button_release_event', onclick)

            self._mouse_press_cid = self.canvas.mpl_connect('button_press_event', on_press)
            self._mouse_motion_cid = self.canvas.mpl_connect('motion_notify_event', on_motion)
            self._mouse_scroll_cid = self.canvas.mpl_connect('scroll_event', on_mouse_scroll)
            self._onkey_press_cid = self.canvas.mpl_connect('key_press_event', on_key_press)
            self._onkey_release_cid = self.canvas.mpl_connect('key_release_event', on_key_release)

            self.canvas.setFocusPolicy(Qt.StrongFocus)
            self.canvas.setFocus()

            # 添加鼠标移动事件以显示当前位置
            def on_mouse_move(event):
                if self.mouse_is_dragged or self.shift_is_pressed:
                    return

                if event.inaxes:
                    try:
                        epoch = int(event.xdata // self.epoch_length)
                        if 0 <= epoch < len(self.scores):
                            self.label_status.setText(f"Epoch: {epoch}")
                    except:
                        pass

            # 连接鼠标移动事件
            self._onmove_cid = self.canvas.mpl_connect('motion_notify_event', on_mouse_move)

            # 更新epoch标签
            self.update_epoch_labels(n_epochs_display)

            # 调整布局
            self.figure.tight_layout()

            # 绘制画布
            self.canvas.draw()
            self.sleep_score_wh.finish_backup()
            self.sleep_redo_score_wh.finish_backup()

            # del self.raw_processed

        except Exception as e:
            print(f"Error in plot_results: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # 强制清理不需要的数据
            if hasattr(self, 'highlight_lines'):
                self.highlight_lines.clear()

    def if_select_all_epochs(self):
        return "ALL" == self.combobox_select_n_epochs.currentText()

    def get_n_epochs_display(self):
        """获取显示的epoch数量"""
        text = self.combobox_select_n_epochs.currentText()
        if text == "All":
            return self.n_epochs
        return int(text)

    def update_epoch_labels(self, n_epochs_display):
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
        # n_epochs_display = self.get_n_epochs_display()
        for ax in self.figure.axes:
            ax.set_xlim(
                self.epoch_length * self.epoch_start,
                self.epoch_length * (self.epoch_start + n_epochs_display)
            )
        self.update_epoch_labels(n_epochs_display)
        self.canvas.draw()

    def update_display_previous_more(self):
        """显示前页结果"""
        n_epochs_display = self.get_n_epochs_display()
        if self.epoch_start >= n_epochs_display:
            self.epoch_start -= n_epochs_display
        else:
            self.epoch_start = 0

        for ax in self.figure.axes:
            ax.set_xlim(
                self.epoch_length * self.epoch_start,
                self.epoch_length * (self.epoch_start + n_epochs_display)
            )
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
            # 更新所有轴的显示范围
            for ax in self.figure.axes:
                ax.set_xlim(
                    self.epoch_length * self.epoch_start,
                    self.epoch_length * (self.epoch_start + n_epochs_display)
                )
            self.update_epoch_labels(n_epochs_display)
            self.canvas.draw()

    def update_display_next_more(self):
        """显示后几页结果"""
        n_epochs_display = self.get_n_epochs_display()
        max_start = max(0, self.n_epochs - n_epochs_display)
        new_start = self.epoch_start + n_epochs_display
        self.epoch_start = min(new_start, max_start)
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
            min_value = 0
            max_value = self.n_epochs - 1
            prompt = f"Enter the Epoch You Want to View:[{min_value}, {max_value}]"
            target_epoch, done = QInputDialog.getInt(
                self, 'Input Dialog', prompt,
                min=min_value, max=max_value)
            if done:
                self.goto_epoch(target_epoch)
        except Exception as e:
            print(f"Error in update_display_goto_epoch: {str(e)}")

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

    def update_display_n_epochs(self):
        """更新显示的epoch数量"""
        try:
            n_epochs_display = self.get_n_epochs_display()

            # 以第一个选中的为中心
            self.epoch_start = self.get_selected_new_start(n_epochs_display)

            # 确保epoch_start不会导致显示超出数据范围
            if self.epoch_start + n_epochs_display > self.n_epochs:
                self.epoch_start = max(0, self.n_epochs - n_epochs_display)

            # 更新滑块最大值
            self.slider.setMaximum(max(0, self.n_epochs - n_epochs_display))

            # 更新x轴范围
            for ax in self.figure.axes:
                ax.set_xlim(
                    self.epoch_length * self.epoch_start,
                    self.epoch_length * (self.epoch_start + n_epochs_display)
                )

            self.update_epoch_labels(n_epochs_display)
            self.canvas.draw()
        except Exception as e:
            print(f"Error in update_display_n_epochs: {str(e)}")

    def get_selected_new_start(self, n_epochs_display):
        for one_epoch in self.current_selected_epochs:
            new_start = one_epoch - n_epochs_display / 2
            new_start = max(0, new_start)
            return new_start
        return self.epoch_start

    def prepare_score_when_edit(self):
        # 更新选中epoch的睡眠阶段
        new_stage = self.combobox_selected_epoch_stage.currentText()

        stage_code = {v: k for k, v in self.map_stages.items()}[new_stage]
        for selected_epoch in self.current_selected_epochs:
            self.sleep_score_wh.record(selected_epoch, self.df_score.at[selected_epoch, 'Stage_Code']);
            self.df_score.at[selected_epoch, 'Stage_Code'] = stage_code
            self.df_score.at[selected_epoch, 'Stage'] = new_stage
            # print("user_edit_stage:", selected_epoch,  new_stage, stage_code)

    def prepare_score_when_undo(self):
        restore_data = self.sleep_score_wh.get_restore_data()
        if len(restore_data) == 0:
            return
        for key, value in restore_data.items():
            self.sleep_redo_score_wh.record(key, self.df_score.at[key, 'Stage_Code'])
            self.df_score.at[key, 'Stage_Code'] = value
            self.df_score.at[key, 'Stage'] = self.map_stages[value]

    def prepare_score_when_redo(self):
        restore_data = self.sleep_redo_score_wh.get_restore_data()
        if len(restore_data) == 0:
            return
        for key, value in restore_data.items():
            self.sleep_score_wh.record(key, self.df_score.at[key, 'Stage_Code'])
            self.df_score.at[key, 'Stage_Code'] = value
            self.df_score.at[key, 'Stage'] = self.map_stages[value]

    def refresh_sleep_score(self):
        # 重新计算睡眠阶段统计
        stage_counts = self.df_score["Stage_Code"].value_counts()
        self.df_score.loc[0, "Wake_Count"] = stage_counts.get(1, 0)
        self.df_score.loc[0, "NREM_Count"] = stage_counts.get(2, 0)
        self.df_score.loc[0, "REM_Count"] = stage_counts.get(3, 0)

        # 获取文件路径信息
        edf_filepath = self.edf_path
        base_path = os.path.dirname(edf_filepath)
        parent_dir = os.path.basename(base_path)

        if parent_dir == 'Result':
            result_path = base_path
        else:
            result_path = os.path.join(base_path, 'Result')

        # 获取最新的时间戳文件夹
        timestamp_folders = [d for d in os.listdir(result_path) if os.path.isdir(os.path.join(result_path, d))]
        latest_folder = max(timestamp_folders)
        qlass_path = os.path.join(result_path, latest_folder, 'Sleep Analysis')

        # 保存更新后的分期结果
        edit_file = os.path.join(qlass_path, f"epoch_length_{self.epoch_length}_scores_user_edit.csv")
        self.df_score.to_csv(edit_file, index=False)

        self.plot_results()

    # def save_as_image(self):
    #     try:
    #         from datetime import datetime
    #         # 自动保存完整图
    #         default_path = os.path.join(self.thread_run.save_path if self.thread_run.save_path else os.getcwd())
    #         default_filename = f"sleep_analysis_complete{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    #         file_path = os.path.join(default_path, default_filename)
    #
    #         self.label_status.setText("Saving image...")
    #         self.textbox.appendPlainText(f"Saving image...{default_filename} {datetime.now()}")
    #
    #         # 保存图形
    #         self.figure.savefig(
    #             file_path,
    #             dpi=300,
    #             bbox_inches='tight',
    #             pad_inches=0.1
    #         )
    #
    #         self.label_status.setText(f"Analysis complete. Figure saved to: {file_path}")
    #         self.textbox.appendPlainText(f"Figure saved to: {file_path}, {datetime.now()}")
    #     except Exception as e:
    #         import traceback
    #         traceback.print_exc()
    #         print(f"Error in saving image: {str(e)}")
    #         self.label_status.setText("Error in sSaving image")
    #         self.textbox.appendPlainText(f"Error in saving image: {str(e)}")

    def user_edit_stage(self):
        """处理用户编辑的睡眠阶段"""
        # 如果是由点击事件触发的更改，则忽略
        if self._ignore_combobox_change:
            return

        if self.current_selected_epochs is not None:
            self.prepare_score_when_edit()
            self.refresh_sleep_score()
            self.edit_post_process()

    def edit_post_process(self):
        if self.sleep_score_wh.is_empty():
            self.undo_button.setEnabled(False)
        else:
            self.undo_button.setEnabled(True)

        self.redo_button.setEnabled(False)
        self.sleep_redo_score_wh.clear()

    def undo_post_process(self):
        self.redo_button.setEnabled(True)
        if self.sleep_score_wh.is_empty():
            self.undo_button.setEnabled(False)

    def redo_post_process(self):
        self.undo_button.setEnabled(True)
        if self.sleep_redo_score_wh.is_empty():
            self.redo_button.setEnabled(False)

    def update_epoch_length(self):
        """处理epoch长度更新"""
        new_length = int(self.combobox_epoch_length.currentText())
        if new_length != self.epoch_length:
            self.epoch_length = new_length
            if self.thread_run is not None:
                self.thread_run.epoch_length = new_length
            # 重新运行分析
            if self.raw_processed is not None:
                self.run_analysis()

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
        """处理滑块值变化"""
        n_epochs_display = self.get_n_epochs_display()
        self.epoch_start = self.slider.value()

        # 更新显示范围
        for ax in self.figure.axes:
            ax.set_xlim(
                self.epoch_length * self.epoch_start,
                self.epoch_length * (self.epoch_start + n_epochs_display)
            )

        self.update_epoch_labels(n_epochs_display)
        self.canvas.draw()

    def update_signal_range(self, sender=None):
        """更新信号图的幅度范围"""
        try:
            if len(self.figure.axes) >= 5:  # 确保有足够的子图
                # 确定是哪个下拉菜单触发了更新
                if sender == self.combobox_eeg_amplitude or sender is None:
                    # 更新EEG信号范围
                    eeg_range = self.combobox_eeg_amplitude.currentText()
                    ax_signal = self.figure.axes[1]
                    if eeg_range == "Auto":
                        ax_signal.autoscale(axis='y')
                    else:
                        amplitude = int(eeg_range.replace('±', ''))
                        ax_signal.set_ylim([-amplitude, amplitude])

                if sender == self.combobox_emg_amplitude or sender is None:
                    # 更新EMG包络线范围 - 只显示正值
                    emg_range = self.combobox_emg_amplitude.currentText()
                    ax_emg = self.figure.axes[2]
                    if emg_range == "Auto":
                        ax_emg.autoscale(axis='y')
                    else:
                        amplitude = int(emg_range.replace('±', ''))
                        ax_emg.set_ylim([0, amplitude])

                if sender == self.combobox_acc_amplitude or sender is None:
                    # 更新ACC信号范围
                    acc_range = self.combobox_acc_amplitude.currentText()
                    ax_acc = self.figure.axes[3]
                    if acc_range == "Auto":
                        ax_acc.autoscale(axis='y')
                    else:
                        amplitude = int(acc_range.replace('±', ''))
                        ax_acc.set_ylim([-amplitude, amplitude])

                self.canvas.draw()
        except Exception as e:
            print(f"Error updating signal ranges: {str(e)}")

    def connect_signals(self):
        # ... existing code ...
        self.combobox_eeg_amplitude.currentTextChanged.connect(
            lambda: self.update_signal_range(self.combobox_eeg_amplitude))
        self.combobox_emg_amplitude.currentTextChanged.connect(
            lambda: self.update_signal_range(self.combobox_emg_amplitude))
        self.combobox_acc_amplitude.currentTextChanged.connect(
            lambda: self.update_signal_range(self.combobox_acc_amplitude))

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
                "current_selected_epochs",
                'n_epochs',
                'epoch_start',
                'edf_path'
            ]

            for attr in data_attributes:
                if hasattr(self, attr):
                    delattr(self, attr)

            # 5. 断开所有信号连接
            if hasattr(self, '_onclick_cid') and hasattr(self, 'canvas'):
                self.canvas.mpl_disconnect(self._onclick_cid)
            if hasattr(self, 'key_press_event') and hasattr(self, 'canvas'):
                self.canvas.mpl_disconnect(self.key_press_event)
            if hasattr(self, 'key_release_event') and hasattr(self, 'canvas'):
                self.canvas.mpl_disconnect(self.key_release_event)
            if hasattr(self, '_onmove_cid') and hasattr(self, 'canvas'):
                self.canvas.mpl_disconnect(self._onmove_cid)

            # 6. 重置所有UI元素状态
            self.progressBar.setValue(0)
            self.button_run.setEnabled(False)
            self.button_plot.setEnabled(False)
            self.button_abort.setEnabled(False)
            self.combobox_select_n_epochs.setEnabled(False)
            self.combobox_selected_epoch_stage.setEnabled(False)
            self.slider.setEnabled(False)

            # 7. 强制多次垃圾回收
            import gc
            gc.collect()
            gc.collect()

            # 8. 打印内存使用情况（用于调试）
            import psutil
            process = psutil.Process()
            print(f"Memory usage after cleanup: {process.memory_info().rss / 1024 / 1024:.2f} MB")

            # 9. 接受关闭事件
            event.accept()

        except Exception as e:
            print(f"Error during window closing: {str(e)}")
            import traceback
            traceback.print_exc()
            event.accept()  # 即使发生错误也关闭窗口