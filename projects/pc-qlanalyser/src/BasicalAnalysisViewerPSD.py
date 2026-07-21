import traceback

from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QSizePolicy,
                             QLabel, QFrame, QLineEdit, QSpacerItem, QMessageBox, QDialog, QApplication,
                             QProgressDialog, QPushButton, QProgressBar)
import matplotlib.pyplot as plt
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QDateTime
import numpy as np
import os
from scipy.signal import welch

from .Infrastructure.log.QLLogging import QLLogging
from .Control_Style import ControlStyle
from .BasicalAnalysisViewer import BasicalAnalysisViewer, BasicalAnalysis
from .utils import SaveUtils, RangeValidator
from .SavePicCPM import SaveDataDialog, SavePictureDialog
from src.Domain.OPLog.OPLog import OPLogTask, OPType, OPLog
from src.Infrastructure.DB.SQLLiteAccessor import SQLLiteDB_Only_MainTread
import time
from datetime import timezone, timedelta

import matplotlib as mpl

# —— 大幅降低 draw_path 内存峰值 ——
# 分片渲染：把超长 Path 拆成块渲染，避免一次吃下所有顶点
mpl.rcParams['agg.path.chunksize'] = 10000  # 1万/块通常很稳，可按机器再调大或调小

# 路径简化：对高密度点做几何简化，不改变整体波形外观
mpl.rcParams['path.simplify'] = True
mpl.rcParams['path.simplify_threshold'] = 0.2  # 0.1~0.3 经验值；越大越快，形状越“紧”


def calculate_psd(raw, channels, fmin, fmax, time_range=None, progress_callback=None):
    """
    计算 PSD（功率谱密度）并返回结果。

    :param raw: 原始数据对象
    :param channels: 要计算的通道列表
    :param fmin: 最小频率
    :param fmax: 最大频率
    :return: 包含 PSD 结果的字典和频率数组
    """
    sfreq = raw.info['sfreq']
    # 如果指定了时间范围，提取对应时间段的数据
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
        start_idx = int(
            ((start_time - raw.info['meas_date'].replace(tzinfo=timezone.utc)).total_seconds()) * sfreq)
        end_idx = int(((end_time - raw.info['meas_date'].replace(
            tzinfo=timezone.utc)).total_seconds()) * sfreq) + sfreq
        # 添加边界检查
        if end_idx >= len(raw.times):
            end_idx = len(raw.times) - 1

        if end_idx <= start_idx:
            raise ValueError("Invalid time range: end time must be greater than start time.")

        # 裁剪数据
        raw = raw.copy().crop(tmin=start_idx / sfreq, tmax=end_idx / sfreq)

    data_dict_raw = {ch: raw.get_data(picks=ch) for ch in channels}

    all_ch = raw.info['ch_names']
    id_l = [all_ch.index(ch) + 1 for ch in channels]
    data_dict = {f'Ch{id_l[i]}_{channels[i]}': v for i, (k, v) in
                 enumerate(list(data_dict_raw.items())[:len(channels)])}

    psd_values = {}
    all_psd = []

    # 总任务数
    total_steps = len(channels)
    current_step = 0
    for channel, channel_data in data_dict.items():
        freqs, psd = welch(channel_data, sfreq, nperseg=2048)
        psd[psd <= 0] = np.nan
        psd = np.squeeze(psd)
        psd = 10 * np.log10(psd)
        freqs_filtered = freqs[(freqs >= fmin) & (freqs <= fmax)]
        psd_filtered = psd[(freqs >= fmin) & (freqs <= fmax)]
        psd_values[channel] = psd_filtered
        all_psd.append(psd_filtered)

        # 更新进度
        current_step += 1
        if progress_callback:
            progress = int((current_step / total_steps) * 100)
            progress_callback(progress)

    # avg_psd = np.nanmean(all_psd, axis=0)
    # psd_values['Average'] = avg_psd

    # print("psd_values")
    # print(psd_values)
    # print("freqs_filtered")
    # print(freqs_filtered)
    return psd_values, freqs_filtered


class PSDWorker(QThread):
    finished = pyqtSignal()  # 任务完成信号
    progress = pyqtSignal(int)  # 进度信号
    error = pyqtSignal(str)  # 错误信号
    result_ready = pyqtSignal(tuple)  # 自定义信号，用于传递计算结果

    def __init__(self, raw, channels, fmin, fmax, time_range):
        super().__init__()
        self.raw = raw
        self.channels = channels
        self.fmin = fmin
        self.fmax = fmax
        self.time_range = time_range

    def run(self):
        try:
            total_steps = len(self.channels)
            current_step = 0  # 当前完成的步数

            def progress_callback(step):
                nonlocal current_step
                current_step += 1
                progress = int((current_step / total_steps) * 100)
                self.progress.emit(progress)  # 发出进度信号

            PSD_values = calculate_psd(
                self.raw,
                self.channels,
                self.fmin,
                self.fmax,
                self.time_range,
                progress_callback=progress_callback
            )

            # 发出结果信号
            self.result_ready.emit(PSD_values)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class PSDCenterViewer(BasicalAnalysisViewer):
    # 分析界面最中间区域
    def __init__(self, num_plots=4, parent=None):
        super().__init__(parent)
        self.figure.set_constrained_layout(False)
        ax = self.figure.add_subplot(111)  # 创建单个子图
        # 调整子图边距
        self.figure.subplots_adjust(
            left=0.3,  # 左边距
            right=0.7,  # 右边距
            bottom=0.15,  # 底部边距
            top=0.9  # 顶部边距
        )

    def update_plot_below(self):
        # 获取当前通道名称
        channel_name = self.channel_names[self.current_channel]
        psd_values, freqs_filtered = self.result

        # 去掉通道名称前缀（如 "Ch1_"）
        processed_psd_values = {key.split('_', 1)[-1]: value for key, value in psd_values.items()}

        # 检查指定的通道是否存在
        if channel_name not in processed_psd_values:
            print(f"Channel {channel_name} not found in PSD data.")
            return

        # 获取指定通道的 PSD 数据
        psd = processed_psd_values[channel_name]

        # 获取当前子图
        ax = self.canvas.figure.get_axes()[0]  # 获取第一个子图

        # 清空画布并绘制
        ax.clear()
        ax.plot(freqs_filtered, psd, color='black')
        ax.set_title(f'{channel_name} PSD', fontsize=10)
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('Power Spectral Density (dB/Hz)')
        ax.set_xlim(freqs_filtered[0], freqs_filtered[-1])
        ax.grid(True)

        # 更新画布
        self.canvas.draw_idle()

    # todo sasve data
    def save_data_without_path(self):
        """让用户选择保存路径并保存数据"""
        if not hasattr(self, 'result') or not self.result:
            QMessageBox.warning(
                self.win,
                "No Data",
                "No analysis results to save.\nPlease perform PSD analysis first."
            )
            return

        from datetime import datetime
        # 获取当前日期和时间
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d%H%M%S")

        # 显示保存对话框
        dialog = SaveDataDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                # 获取保存参数
                params = dialog.get_save_parameters()
                save_path = params['path']
                data_format = params['format'].lower()

                # 创建保存目录
                default_folder = "PSD_Analysis_data"
                save_dir = os.path.join(save_path, default_folder)
                os.makedirs(save_dir, exist_ok=True)

                # 准备数据
                import pandas as pd
                psd_values, freqs_filtered = self.result
                df = pd.DataFrame(psd_values, index=freqs_filtered)
                df.columns = [col + '(dB/Hz)' for col in df.columns]

                # 重命名索引列，这样保存CSV时会有列名
                df.index.name = 'Frequency (Hz)'
                # 计算并添加平均值列
                df['Average(dB/Hz)'] = df.mean(axis=1)  # 计算每个频率点的平均值

                # 生成文件名
                filename = f"psd_analysis_results{formatted_time}{data_format}"
                file_path = os.path.join(save_dir, filename)

                # 根据不同格式保存数据
                if data_format == '.csv':
                    df.to_csv(file_path, index=True, encoding='utf-8')
                elif data_format == '.npy':
                    # 保存完整的数据结构
                    save_dict = {
                        'data': df.to_numpy(),
                        'columns': df.columns.tolist(),
                        'index': df.index.tolist()
                    }
                    np.save(file_path, save_dict, allow_pickle=True)
                    # np.save(file_path, df.to_numpy(),allow_pickle=True)

                # 显示成功消息
                QMessageBox.information(
                    self.win,
                    "Save Success",
                    f"Analysis results have been saved to:\n{file_path}"
                )
                QLLogging.log.info(f"PSD results saved to: {file_path}")
                OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'Save Data', 0)
                return True

            except Exception as e:
                QMessageBox.critical(
                    self.win,
                    "Error",
                    f"Failed to save results: {str(e)}"
                )
                QLLogging.log.exception(f"Error saving PSD results:\n{str(e)}")
                return False

    def save_figure_without_path(self):
        """让用户选择路径和格式并保存所有通道的 PSD 图表"""
        if not hasattr(self, 'result') or not self.result:
            QMessageBox.warning(
                self.win,
                "No Data",
                "No analysis results to save.\nPlease perform PSD analysis first."
            )
            return

        from datetime import datetime
        # 获取当前日期和时间
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d%H%M%S")

        # 1. 显示保存对话框
        dialog = SavePictureDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                # 2. 获取保存参数
                params = dialog.get_save_parameters()
                save_path = params['path']
                img_format = params['format'].lower().replace('.', '')
                dpi = params['resolution']

                # 3. 创建保存目录
                default_folder = f"PSD_Analysis_pic"
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

                # 4. 获取数据
                psd_values, freqs_filtered = self.result
                processed_psd_values = {key.split('_', 1)[-1]: value
                                        for key, value in psd_values.items()}
                channels = list(processed_psd_values.keys())  # 所有通道名称

                # 5. 计算并保存平均 PSD
                all_psd_values = list(processed_psd_values.values())
                avg_psd = np.nanmean(all_psd_values, axis=0)

                # 获取数据
                psd_values, freqs_filtered = self.result
                processed_psd_values = {key.split('_', 1)[-1]: value
                                        for key, value in psd_values.items()}
                channels = list(processed_psd_values.keys())  # 所有通道名称

                # 计算并保存平均 PSD
                all_psd_values = list(processed_psd_values.values())
                avg_psd = np.nanmean(all_psd_values, axis=0)

                self._save_average_psd(
                    save_dir=save_dir,
                    freqs=freqs_filtered,
                    avg_psd=avg_psd,
                    savetime=formatted_time,
                    img_format=img_format,
                    dpi=dpi
                )

                # 6. 保存各通道 PSD
                self._save_channel_psds(
                    save_dir=save_dir,
                    freqs=freqs_filtered,
                    psd_values=processed_psd_values,
                    savetime=formatted_time,
                    img_format=img_format,
                    dpi=dpi
                )

                # 计算页面时间范围
                page_start_time = (self.current_page - 1) * self.page_duration
                page_end_time = page_start_time + self.page_duration
                waveform_ylim = self._get_waveform_ylim(self.amplitude_selector.currentText())

                # 为每个通道保存波形图（离屏渲染，不更新界面）
                for channel in channels:
                    self.save_waveform_offscreen(
                        channel_name=channel,
                        start_time=page_start_time,
                        end_time=page_end_time,
                        save_dir=save_dir,
                        filename=f"Waveform_{channel}_{formatted_time}.{img_format}",
                        dpi=dpi,
                        img_format=img_format,
                        ylim=waveform_ylim,
                    )

                wait_box.close()

                # 7. 显示成功消息
                QMessageBox.information(
                    self.win,
                    "Success",
                    f"Figures have been saved to:\n{save_dir}"
                )
                QLLogging.log.info(f"PSD figures saved to: {save_dir}")
                OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'Save Pic', 0)

            except Exception as e:
                # 异常时先关等待框，再报错
                try:
                    if wait_box and wait_box.isVisible():
                        wait_box.close()
                finally:
                    pass
                QMessageBox.critical(
                    self.win,
                    "Error",
                    f"Error saving figures: {str(e)}"
                )
                QLLogging.log.exception(f"Error saving PSD figures:\n{str(e)}")
            finally:
                # 兜底清理
                if wait_box:
                    try:
                        if wait_box.isVisible():
                            wait_box.close()
                    finally:
                        wait_box.deleteLater()

    def _get_waveform_ylim(self, amplitude_str="Auto"):
        if amplitude_str == "Auto" or amplitude_str is None:
            return None
        try:
            vmax = float(str(amplitude_str).lstrip('±'))
            return (-vmax, vmax)
        except Exception:
            return None

    def _downsample_envelope(self, x, y, max_points):
        """把 (x,y) 降到 <= max_points，采用每窗 min/max 包络，外观几乎不变。"""
        n = len(y)
        if n <= max_points or max_points <= 0:
            return x, y
        win = int(np.ceil(n / max_points))
        n_fit = (n // win) * win
        y_fit = y[:n_fit].reshape(-1, win)
        x_fit = x[:n_fit].reshape(-1, win)

        y_min = y_fit.min(axis=1)
        y_max = y_fit.max(axis=1)
        x_mid = x_fit[:, win // 2]

        x_ds = np.empty(y_min.size * 2, dtype=x.dtype)
        y_ds = np.empty(y_min.size * 2, dtype=y.dtype)
        x_ds[0::2] = x_mid;
        x_ds[1::2] = x_mid
        y_ds[0::2] = y_min;
        y_ds[1::2] = y_max

        if n_fit < n:
            x_ds = np.concatenate([x_ds, x[n_fit:]])
            y_ds = np.concatenate([y_ds, y[n_fit:]])
        return x_ds, y_ds

    def save_waveform_offscreen(self, channel_name, start_time, end_time, save_dir, filename, dpi, img_format,
                                ylim=None):
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
        # 计算开始和结束索引

        start_idx = int(((total_start + timedelta(seconds=start_time) - meas_date).total_seconds()) * self.fs)
        end_idx = int(((total_start + timedelta(seconds=end_time) - meas_date).total_seconds()) * self.fs)
        # 获取数据
        wave_data, wave_times = self.raw_data[ch_name, start_idx: end_idx]
        if len(wave_times) == 0:
            plt.close(fig)
            return

        # 绘制波形
        # —— 只在数据极大时触发限点 ——
        fig = ax.figure
        fig_w_px = int(fig.get_figwidth() * fig.get_dpi())
        max_pts = max(20000, fig_w_px * 4)  # 像素宽度的 ~4倍，上限至少2万

        wt, wd = wave_times, wave_data[0]
        if len(wd) > max_pts:
            wt, wd = self._downsample_envelope(wt, wd, max_pts)

        ax.plot(wt, wd, color='black', linewidth=0.5)

        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Amplitude(μV)')
        ax.set_title(f'{ch_name} Waveform')
        ax.margins(x=0, y=0)
        ax.grid(True, linestyle='--', alpha=0.7)

        # 设置x轴范围
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

    def save_plot_widget(self, plot_widget, save_dir, filename, dpi, img_format):
        """
        保存plot_widget图片
        """
        try:
            result_path = os.path.join(save_dir, filename)
            # --- PyQtGraph 转 Matplotlib ---
            fig, ax = plt.subplots(figsize=(16, 6), dpi=dpi)
            plot_item = plot_widget.plotItem

            # 1. 复制所有曲线
            for curve in plot_item.curves:
                x, y = curve.getData()
                ax.plot(x, y,
                        label=curve.opts.get('name', ''),
                        color=curve.opts.get('pen', 'k').color().name(),
                        linewidth=curve.opts.get('pen', None).width() if hasattr(curve.opts.get('pen', None),
                                                                                 'width') else 1.0)

            # 2. 复制坐标轴设置
            ax.set_xlabel(plot_item.axes["bottom"]["item"].label.toPlainText())
            ax.set_ylabel(plot_item.axes["left"]["item"].label.toPlainText())
            ax.set_title(plot_item.titleLabel.text if plot_item.titleLabel else "")
            ax.margins(x=0, y=0)

            # 3. 复制网格线
            if plot_item.showGrid(x=True, y=True):
                ax.grid(True, linestyle='--', alpha=0.7)

            # 4. 复制图例
            if plot_item.legend is not None:
                ax.legend()

            # 5. 应用保存参数
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
        except ValueError as e:
            QLLogging.log.exception(f"save widget plot, error: {e}")

    def _save_average_psd(self, save_dir, freqs, avg_psd, savetime, img_format='png', dpi=300):
        """保存平均 PSD 图"""
        plt.figure(figsize=(10, 6))
        plt.plot(freqs, avg_psd, color='black', label='Average PSD')
        plt.title('Average PSD (Log)', fontsize=10)
        plt.xlabel('Frequency (Hz)')
        plt.ylabel('Power Spectral Density (dB/Hz)')
        plt.xlim(freqs[0], freqs[-1])
        plt.grid(True)
        plt.legend()
        plt.tight_layout()

        # 保存图表
        fname = f'PSD_average{savetime}.{img_format}'
        plt.savefig(
            os.path.join(save_dir, fname),
            format=img_format,
            dpi=dpi,
            bbox_inches='tight'
        )
        plt.close()

    def _save_channel_psds(self, save_dir, freqs, psd_values, savetime, img_format='png', dpi=300):
        """保存各通道 PSD 图"""
        for channel_name, psd in psd_values.items():
            plt.figure(figsize=(10, 6))
            plt.plot(freqs, psd, color='black')
            plt.title(f'{channel_name} PSD', fontsize=10)
            plt.xlabel('Frequency (Hz)')
            plt.ylabel('Power Spectral Density (dB/Hz)')
            plt.xlim(freqs[0], freqs[-1])
            plt.grid(True)
            plt.tight_layout()

            # 保存图表
            fname = f'PSD_{channel_name}{savetime}.{img_format}'
            plt.savefig(
                os.path.join(save_dir, fname),
                format=img_format,
                dpi=dpi,
                bbox_inches='tight'
            )
            plt.close()


class PSDAnalysisViewer(BasicalAnalysis):

    def __init__(self, title, channel_name, parent=None):
        super().__init__(title, channel_name, parent)
        self.setWindowTitle("PSD Analysis")

    def init_center_and_bottom(self, content_layout):
        self.viewer = PSDCenterViewer()
        super().init_center_and_bottom(content_layout)
        self.h_layout.addWidget(self.viewer)
        self.viewer.hide()

    def init_left_panel(self, content_layout):
        """自定义左侧控制栏"""
        # 调用父类的 init_left_panel 方法
        super().init_left_panel(content_layout)

        # 添加 time_selector
        self.left_layout.addWidget(self.time_selector)

        # 添加分割线
        separator_between_time_and_frequency = QFrame()
        separator_between_time_and_frequency.setFrameShape(QFrame.HLine)
        separator_between_time_and_frequency.setStyleSheet("background-color: #a9a9a9;")
        separator_between_time_and_frequency.setFixedHeight(1)
        self.left_layout.addWidget(separator_between_time_and_frequency)

        # 添加 property 选择控件
        property_layout = QVBoxLayout()
        property_layout.setContentsMargins(30, 10, 0, 10)
        property_layout.setSpacing(int(self.devicePixelRatio() * 10))  # self.devicePixelRatio() 当前显示屏的像素缩放比

        # 添加标题标签
        title_label = QLabel("Property")
        title_label.setStyleSheet(ControlStyle.get_label_wordSmall_style())
        ControlStyle.get_font_size(title_label, 12)
        property_layout.addWidget(title_label)

        # 添加一个固定像素的垂直间距
        h_layout = QHBoxLayout()
        property_layout.addLayout(h_layout)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(int(self.devicePixelRatio() * 5))

        # 左边标签
        label = QLabel("Frequency(Hz)")
        label.setFixedWidth(120)
        label.setStyleSheet(ControlStyle.get_wiget400_word_style(14))
        h_layout.addWidget(label)

        self.min_edit = QLineEdit("1.0")
        self.max_edit = QLineEdit("40.0")
        # 设置浮点数验证器（最小值：0.0，最大值：1.0，精度：1位小数）
        validator = RangeValidator(0.001, 30000.000, decimals=3, parent=None)  # 设置小数点后的精度显示
        self.min_edit.setValidator(validator)
        self.max_edit.setValidator(validator)
        for edit in (self.min_edit, self.max_edit):
            edit.setFixedWidth(60)
            edit.setAlignment(Qt.AlignCenter)
            edit.setStyleSheet(ControlStyle.get_lineEdit_style())

        dash = QLabel("_")
        dash.setFixedWidth(10)
        dash.setAlignment(Qt.AlignLeft)
        dash.setStyleSheet("color: #808080; font-size: 14px;")
        h_layout.addStretch()  # 左侧弹簧
        h_layout.addWidget(self.min_edit)
        h_layout.addWidget(dash)
        h_layout.addWidget(self.max_edit)
        h_layout.addStretch()  # 右侧弹簧

        self.left_layout.addLayout(property_layout)

        # 添加一个固定的下方空白区域
        bottom_spacer = QSpacerItem(0, 300, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.left_layout.addItem(bottom_spacer)
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
            if not selected_channels:
                QMessageBox.warning(self.win, "No Channel Selected", "Please select at least one channel!")
                print("on_analyse_clicked: No channel selected.")
                return None

            if not self.scale_seconds or self.scale_seconds <= 0:
                QLLogging.log.error("Invalid time scale selected.")
                QMessageBox.warning(self.win, "Invalid Time Range",
                                    "Invalid time range. Please select a valid time range!")
                return None

            if float(self.min_edit.text()) >= float(self.max_edit.text()):
                QLLogging.log.error("Invalid frequency range.")
                QMessageBox.warning(self.win, "Invalid frequency range",
                                    "Low frequency must be less than high frequency.")
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

            QLLogging.log.debug("basical analysis-PSD Analyse begin.")
            OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'basical analysis-PSD Analyse begin！',
                        0)

            # 开始计算
            # 将时间范围转换为秒
            # 调用 calculate_bandpower 时传入时间范围
            time_range = self.time_selector.get_time_range()

            self.worker = PSDWorker(self.raw, selected_channels,
                                    float(self.min_edit.text()), float(self.max_edit.text()), time_range)
            # 连接信号
            self.worker.result_ready.connect(self.on_worker_result_ready)  # 连接结果信号
            self.worker.progress.connect(self.on_worker_progress)  # 可选：连接进度信号
            self.worker.error.connect(self.on_worker_error)  # 可选：连接错误信号

            self.worker.start()

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
