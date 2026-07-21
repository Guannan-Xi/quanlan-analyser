from PyQt5.QtWidgets import (
    QFrame, QDialog, QMessageBox, QSpacerItem, QSizePolicy, QApplication, QProgressDialog
)
from .CustomControls import FrequencyCheckboxWidget, CustomFrequencyCheckboxWidget  # 导入自定义控件
import numpy as np
import pandas as pd
from scipy.signal import welch, butter, filtfilt
from .Infrastructure.log.QLLogging import QLLogging
from .BasicalAnalysisViewer import BasicalAnalysisViewer, BasicalAnalysis
from PyQt5.QtCore import QThread, pyqtSignal, QDateTime
from .utils import SaveUtils
from .SavePicCPM import SavePictureDialog, SaveDataDialog, SavePictureDialog1
import matplotlib.pyplot as plt
import os
from .Domain.OPLog.OPLog import OPLog, OPType
from src.Infrastructure.DB.SQLLiteAccessor import SQLLiteDB_Only_MainTread
from datetime import timezone
import time
from PyQt5 import QtWidgets, QtCore
from .Control_Style import ControlStyle
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtCore import QDateTime, QDate, QTime, Qt
from PyQt5.QtGui import QValidator
from PyQt5.QtWidgets import QLineEdit
from datetime import timezone, timedelta

import matplotlib as mpl
# 分片渲染，避免超长 path 一次性栅格化导致内存峰值过高
mpl.rcParams['agg.path.chunksize'] = 10000
# 路径简化（不会改变外观细节的前提下减少绘制点）
mpl.rcParams['path.simplify'] = True
mpl.rcParams['path.simplify_threshold'] = 0.2


# 计算数据的频段功率
def calculate_bandpower(raw, channels, bands, time_range=None, progress_callback=None):
    """
    计算 EEG 数据的频段功率。

    :param raw: 原始 EEG 数据对象
    :param channels: 要分析的通道列表
    :param bands: 频段字典，键为频段名称，值为频率范围 (fmin, fmax)
    :param time_range: 时间范围元组 (start_time, end_time)，以秒为单位
    :param progress_callback: 可选的回调函数，用于报告进度
    :return: 频段功率计算结果，包括每个通道的功率和平均功率
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

    # 提取通道数据
    data_dict_raw = {ch: raw.get_data(picks=ch) for ch in channels}

    # 通道数据字典
    all_ch = raw.info['ch_names']
    id_l = [all_ch.index(ch) + 1 for ch in channels]
    data_dict = {f'Ch{id_l[i]}_{channels[i]}': v for i, (k, v) in
                 enumerate(list(data_dict_raw.items())[:len(channels)])}

    # 定义陷波滤波器
    def notch_filter(EEG, fs, order=1):
        nyquist = 0.5 * fs
        for freq in [50, 100]:  # 去除 50Hz 和 100Hz 工频干扰
            low_cutoff = (freq - 0.5) / nyquist
            high_cutoff = (freq + 0.5) / nyquist
            b, a = butter(order, [low_cutoff, high_cutoff], btype='bandstop')
            EEG = np.squeeze(filtfilt(b, a, EEG))
        return EEG

    # 对每个通道的数据应用陷波滤波
    data_dict = {ch: notch_filter(data, sfreq) for ch, data in data_dict.items()}

    # 初始化结果存储
    bandpower_values = []
    avg_bandpower = {band: {'absolute_total': [], 'relative_total': [], 'absolute_per_Hz': [], 'relative_per_Hz': []}
                     for band in bands.keys()}

    # 总任务数
    total_steps = len(channels) * len(bands)
    current_step = 0

    # 计算频段功率
    for channel, channel_data in data_dict.items():
        bandpower = {'Channel': channel}

        for band, (fmin, fmax) in bands.items():
            band_freqs, band_psd = welch(channel_data, sfreq, nperseg=1024)
            band_psd = np.squeeze(band_psd)
            band_power = np.sum(band_psd[(band_freqs >= fmin) & (band_freqs <= fmax)])
            total_power = np.sum(band_psd)
            band_width = fmax - fmin

            # 计算功率指标
            bandpower[f'{band}_absolute_total'] = band_power
            bandpower[f'{band}_relative_total'] = band_power / total_power
            bandpower[f'{band}_absolute_per_Hz'] = band_power / band_width
            bandpower[f'{band}_relative_per_Hz'] = (band_power / total_power) / band_width

            # 累积到平均值计算
            avg_bandpower[band]['absolute_total'].append(band_power)
            avg_bandpower[band]['relative_total'].append(band_power / total_power)
            avg_bandpower[band]['absolute_per_Hz'].append(band_power / band_width)
            avg_bandpower[band]['relative_per_Hz'].append((band_power / total_power) / band_width)

            # 更新进度
            current_step += 1
            if progress_callback:
                progress = int((current_step / total_steps) * 100)
                progress_callback(progress)

        bandpower_values.append(bandpower)

    # 计算平均功率
    avg_bandpower_values = {'Channel': 'Average'}
    for band in bands.keys():
        avg_bandpower_values[f'{band}_absolute_total'] = np.mean(avg_bandpower[band]['absolute_total'])
        avg_bandpower_values[f'{band}_relative_total'] = np.mean(avg_bandpower[band]['relative_total'])
        avg_bandpower_values[f'{band}_absolute_per_Hz'] = np.mean(avg_bandpower[band]['absolute_per_Hz'])
        avg_bandpower_values[f'{band}_relative_per_Hz'] = np.mean(avg_bandpower[band]['relative_per_Hz'])

    bandpower_values.append(avg_bandpower_values)

    return bandpower_values


class BandpowerWorker(QThread):
    finished = pyqtSignal()  # 任务完成信号
    progress = pyqtSignal(int)  # 进度信号
    error = pyqtSignal(str)  # 错误信号
    result_ready = pyqtSignal(list)  # 自定义信号，用于传递计算结果

    def __init__(self, raw, channels, bands, time_range=None):
        super().__init__()
        self.raw = raw  # 原始 EEG 数据
        self.channels = channels  # 要分析的通道列表
        self.bands = bands  # 要分析的频段列表
        self.time_range = time_range
        # self.result_path = result_path  # 结果保存路径

    def run(self):
        try:
            total_steps = len(self.channels) * len(self.bands)
            current_step = 0  # 当前完成的步数

            def progress_callback(step):
                nonlocal current_step
                current_step += 1
                progress = int((current_step / total_steps) * 100)
                self.progress.emit(progress)  # 发出进度信号

            # 调用频段功率计算函数
            bandpower_values = calculate_bandpower(
                self.raw,
                self.channels,
                self.bands,
                self.time_range,
                progress_callback=progress_callback
            )
            # 发出结果信号
            self.result_ready.emit(bandpower_values)
            self.finished.emit()  # 任务完成后发出完成信号
        except Exception as e:
            self.error.emit(str(e))  # 发出错误信号


class BandpowerCenterViewer(BasicalAnalysisViewer):
    ##分析界面最中间区域
    def __init__(self, num_plots=4, parent=None):
        super().__init__(parent)

    def update_plot_below(self):  # 绘制四种柱状图
        # 检查图表是否存在，如果存在则清空
        if hasattr(self, 'figure'):
            self.figure.clear()
        # 获取当前通道名称
        # 清理现有图像并释放内存
        channel_name = self.channel_names[self.current_channel]  # EEG0

        bandpower_data = self.result
        bandpower_data = next((data for data in bandpower_data if data['Channel'] == channel_name), None)
        if not bandpower_data:
            # 如果未找到对应数据，不创建图表
            if hasattr(self, 'canvas'):
                self.canvas.draw_idle()
            return
        # 动态确定要绘制的列
        available_bands = ["Delta", "Theta", "Alpha", "Beta", "Gamma", "Other"]
        selected_bands = [band for band in available_bands if any(f"{band}_" in key for key in bandpower_data.keys())]
        if len(selected_bands) == 0:
            # 如果没有选中的频段，不创建图表
            if hasattr(self, 'canvas'):
                self.canvas.draw_idle()  # 更新画布
            return

        # 创建 1x4 的子图布局
        gs = self.figure.add_gridspec(1, 4, width_ratios=[1, 1, 1, 1],
                                      wspace=0.25,  # 子图之间的间距
                                      left=0.05,  # 左边距 (10%)
                                      right=0.98,  # 右边距 (10%)
                                      )

        # 创建4个水平排列的子图
        ax1 = self.figure.add_subplot(gs[0, 0])  # 第一个子图
        ax2 = self.figure.add_subplot(gs[0, 1])  # 第二个子图
        ax3 = self.figure.add_subplot(gs[0, 2])  # 第三个子图
        ax4 = self.figure.add_subplot(gs[0, 3])  # 第四个子图

        # 动态生成柱形图配置
        chart_config = [
            (
                selected_bands, [f"{band}_absolute_per_Hz" for band in selected_bands],
                "Average Absolute Per Hz Bandpower",
                "Bandpower(μV²/Hz)"),
            (selected_bands, [f"{band}_absolute_total" for band in selected_bands], "Average Absolute Total Bandpower",
             "Bandpower(μV²)"),
            (
                selected_bands, [f"{band}_relative_per_Hz" for band in selected_bands],
                "Average Relative Per Hz Bandpower",
                "Bandpower(ratio)"),
            (selected_bands, [f"{band}_relative_total" for band in selected_bands], "Average Relative Total Bandpower",
             "Bandpower(ratio)")
        ]

        # 更新柱形图
        for i, ax in enumerate(self.figure.get_axes()):
            ax.clear()
            if i < len(chart_config):
                labels, keys, title, y_label = chart_config[i]
                values = [bandpower_data.get(key, 0) for key in keys]

                # 设置柱形宽度和间距
                bar_width = 0.3  # 柱形宽度
                x_positions = range(len(labels))  # X 轴位置
                ax.bar(x_positions, values, width=bar_width, color='black')

                # 设置 X 轴标签、标题和 Y 轴标签
                ax.set_xticks([pos + bar_width / 2 for pos in x_positions])  # 调整标签位置
                ax.set_xticklabels(labels, fontsize=9, rotation=45, ha='right')  # 旋转45° 右对齐

                ax.set_title(title, fontsize=10)  # 设置标题
                ax.set_ylabel(y_label, fontsize=10)  # 设置 Y 轴标签

                # 设置 Y 轴刻度字体大小
                ax.tick_params(axis='y', labelsize=10)

        # 更新画布
        self.canvas.draw_idle()

    def _get_waveform_ylim(self, amplitude_str):
        """把幅值下拉（如 '±2000', 'Auto'）解析为 (-max, +max)。Auto/异常返回 None。单位 μV。"""
        if not amplitude_str or str(amplitude_str).strip() == "Auto":
            return None
        try:
            vmax = float(str(amplitude_str).lstrip('±'))
            return (-vmax, vmax)
        except Exception:
            return None

    def _downsample_envelope(self, x, y, max_points):
        """
        无损限点：将 (x,y) 降到 <= max_points。
        采用每窗 min/max 包络；视觉几乎与全量点一致，但渲染速度和内存占用显著下降。
        """
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

        # 交错 min/max，保留峰谷
        x_ds = np.empty(y_min.size * 2, dtype=x.dtype)
        y_ds = np.empty(y_min.size * 2, dtype=y.dtype)
        x_ds[0::2] = x_mid;
        x_ds[1::2] = x_mid
        y_ds[0::2] = y_min;
        y_ds[1::2] = y_max

        # 补上尾部不足一窗的数据
        if n_fit < n:
            x_ds = np.concatenate([x_ds, x[n_fit:]])
            y_ds = np.concatenate([y_ds, y[n_fit:]])
        return x_ds, y_ds

    def save_data_without_path(self):
        """让用户选择保存路径并保存数据"""
        if not hasattr(self, 'result') or not self.result:
            QMessageBox.warning(
                self,
                "No Data",
                "No analysis results to save.\nPlease perform Bandpower analysis first."
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
                default_folder = "Bandpower_Analysis_data"
                save_dir = os.path.join(save_path, default_folder)
                os.makedirs(save_dir, exist_ok=True)

                # 转换数据为DataFrame
                df = pd.DataFrame(self.result)
                # 重新排列列顺序，确保Channel列在第一列
                columns = df.columns.tolist()
                if 'Channel' in columns:
                    # 将'Channel'移到第一列
                    columns.remove('Channel')
                    columns.insert(0, 'Channel')
                    df = df[columns]
                # —— 强健删除 'Average' 行 ——
                # 1) 先找出真正的 Channel 列（容忍空格/大小写）
                ch_candidates = [c for c in df.columns if str(c).strip().lower() == 'channel']
                if ch_candidates:
                    ch = ch_candidates[0]
                    # 2) 规范化该列的字符串：Unicode标准化、合并空白、去首尾空白、转小写
                    norm = (
                        df[ch].astype(str)
                        .str.normalize('NFKC')
                        .str.replace(r'\s+', ' ', regex=True)
                        .str.strip()
                        .str.casefold()
                    )

                    # 3) 删除等于 'average' 的整行
                    before = len(df)
                    df = df.loc[~norm.eq('average')].copy()
                    removed = before - len(df)
                    QLLogging.log.info(f"Removed {removed} row(s) where {ch} == 'Average'.")
                else:
                    QLLogging.log.warning(f"No 'Channel' column found. Columns: {list(df.columns)}")
                # 生成文件名
                filename = f"bandpower_analysis_results{formatted_time}{data_format}"
                file_path = os.path.join(save_dir, filename)

                # 根据不同格式保存数据
                if data_format == '.csv':
                    df.to_csv(file_path, index=False, encoding='utf-8')
                elif data_format == '.mat':
                    from scipy.io import savemat
                    savemat(file_path, {'bandpower_data': df.to_dict()})
                elif data_format == '.npy':
                    np.save(file_path, df.to_numpy(), allow_pickle=True)

                # 显示成功消息
                QMessageBox.information(
                    self.win,
                    "Save Success",
                    f"Analysis results have been saved to:\n{file_path}"
                )
                QLLogging.log.info(f"Bandpower figures saved to: {save_dir}")
                OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'Save Data', 0)
                return True

            except Exception as e:
                QMessageBox.critical(
                    self.win,
                    "Error",
                    f"Failed to save results: {str(e)}"
                )
                QLLogging.log.exception(f"Error saving Bandpower results:\n{str(e)}")
                return False

    def save_figure_without_path(self):
        """让用户选择路径并保存频带分析图表"""
        # 1. 检查是否有数据可以保存
        if not hasattr(self, 'result') or not self.result:
            QMessageBox.warning(
                self.win,
                "No Data",
                "No analysis results to save.\nPlease perform Bandpower analysis first."
            )
            return

        from datetime import datetime
        # 获取当前日期和时间
        current_time = datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d%H%M%S")

        # 2. 显示保存对话框
        dialog = SavePictureDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                # 3. 获取保存参数
                params = dialog.get_save_parameters()
                save_dir = params['path']
                img_format = params['format'].lower().replace('.', '')
                dpi = params['resolution']

                # 3. 创建保存目录
                default_folder = f"Bandpower_Analysis_pic"
                save_dir = os.path.join(save_dir, default_folder)
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
                original_channel = self.current_channel

                # 4. 定义指标类型
                metrics = [
                    ('absolute_per_Hz', 'μV²/Hz'),
                    ('absolute_total', 'μV²'),
                    ('relative_per_Hz', 'ratio'),
                    ('relative_total', 'ratio')
                ]

                # 5. 提取频段名称
                bands = self._get_frequency_bands()

                # 6. 保存单个通道图表
                self._save_channel_plots(
                    save_dir=save_dir,
                    bands=bands,
                    metrics=metrics,
                    savetime=formatted_time,
                    img_format=img_format,
                    dpi=dpi
                )

                # 7. 保存平均值图表
                self._save_average_plots(
                    save_dir=save_dir,
                    bands=bands,
                    metrics=metrics,
                    savetime=formatted_time,
                    img_format=img_format,
                    dpi=dpi
                )

                # 计算页面时间范围
                page_start_time = (self.current_page - 1) * self.page_duration
                page_end_time = page_start_time + self.page_duration

                # 为每个通道保存波形图（离屏渲染，不更新界面）
                for data in self.result:
                    if data['Channel'] == 'Average':
                        continue
                    channel = data['Channel']
                    self.save_waveform_offscreen(
                        channel_name=channel,
                        start_time=page_start_time,
                        end_time=page_end_time,
                        save_dir=save_dir,
                        filename=f"Waveform_{channel}_{formatted_time}.{img_format}",
                        dpi=dpi,
                        img_format=img_format
                    )
                wait_box.close()

                QMessageBox.information(
                    self.win,
                    "Save Success",
                    f"Figures have been saved to:\n{save_dir}"
                )
                QLLogging.log.info(f"Bandpower figures saved to: {save_dir}")
                OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'Save Pic', 0)

            except Exception as e:
                # 异常时先关等待框，再报错
                try:
                    if wait_box and wait_box.isVisible():
                        wait_box.close()
                finally:
                    pass
                # 错误消息提示
                QMessageBox.critical(
                    self.win,
                    "Error",
                    f"Failed to save figures: {str(e)}"
                )
                QLLogging.log.exception(f"Error saving Bandpower figure:\n{str(e)}")
            finally:
                # 兜底清理
                if wait_box:
                    try:
                        if wait_box.isVisible():
                            wait_box.close()
                    finally:
                        wait_box.deleteLater()

    def save_waveform_offscreen(self, channel_name, start_time, end_time, save_dir, filename, dpi, img_format):
        """
        离屏渲染波形图（带 y 轴限制 & 超大数据无损降采样），不更新当前显示
        """
        result_path = os.path.join(save_dir, filename)

        # 创建离屏图形
        fig, ax = plt.subplots(figsize=(16, 6), dpi=dpi)

        # === 新：根据幅值选择器决定 y 轴固定范围（与分析图一致） ===
        waveform_ylim = None
        try:
            if hasattr(self, 'amplitude_selector') and self.amplitude_selector is not None:
                waveform_ylim = self._get_waveform_ylim(self.amplitude_selector.currentText())
        except Exception:
            waveform_ylim = None

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

        # 计算相对于 total_start 的绝对时间
        absolute_start_time = total_start + timedelta(seconds=start_time)
        absolute_end_time = total_start + timedelta(seconds=end_time)

        # 计算开始和结束索引
        start_idx = int(((absolute_start_time - meas_date).total_seconds()) * self.fs)
        end_idx = int(((absolute_end_time - meas_date).total_seconds()) * self.fs)

        # 获取数据
        wave_data, wave_times = self.raw_data[ch_name, start_idx: end_idx]

        if len(wave_times) == 0:
            plt.close(fig)
            return

        # === 新：针对超大数据做“包络式”无损降采样（仅在需要时触发） ===
        # 经验值：图像像素宽度 * 4 作为单曲线点数上限，且至少 2 万点
        fig_w_px = int(fig.get_figwidth() * fig.get_dpi())
        max_pts = max(20000, fig_w_px * 4)
        wt, wd = wave_times, wave_data[0]
        if len(wd) > max_pts:
            wt, wd = self._downsample_envelope(wt, wd, max_pts)

        # 绘制波形
        line, = ax.plot(wt, wd, color='black', linewidth=0.5)
        # 可选的小优化（PNG 同样适用）
        line.set_antialiased(False)
        line.set_rasterized(False)

        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Amplitude(μV)')
        ax.set_title(f'{ch_name} Waveform')
        ax.margins(x=0, y=0)
        ax.grid(True, linestyle='--', alpha=0.7)

        # x 轴范围使用相对时间（从 0 开始）
        ax.set_xlim(start_time, end_time)

        # === y 轴限制：优先用固定值；否则走自适应 ===
        if waveform_ylim is not None:
            ax.set_ylim(waveform_ylim)
        else:
            if len(wd) > 0:
                ymin = float(np.min(wd));
                ymax = float(np.max(wd))
                y_range = ymax - ymin
                margin = y_range * 0.1 if y_range > 0 else 0.1
                ax.set_ylim(ymin - margin, ymax + margin)
            else:
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

    def _get_frequency_bands(self):
        """从结果数据中提取频段名称"""
        if not self.result or len(self.result) == 0:
            return []

        first_data = self.result[0]
        bands = set()

        for key in first_data.keys():
            if '_' in key:
                band = key.split('_')[0]
                if band not in ['Channel']:
                    bands.add(band)

        return sorted(list(bands))

    def _save_channel_plots(self, save_dir, bands, metrics, savetime, img_format='png', dpi=300):
        """保存各通道的图表"""
        for data in self.result:
            if data['Channel'] == 'Average':
                continue

            channel = data['Channel']

            for metric, unit in metrics:
                # 创建图表
                plt.figure(figsize=(8, 6))

                # 获取数据并绘图
                values = [data[f"{band}_{metric}"] for band in bands]
                plt.bar(range(len(bands)), values, width=0.4, color='black')

                # 设置图表属性
                plt.title(f'{channel} {metric.replace("_", " ").title()} Bandpower')
                plt.xlabel('Frequency Bands')
                plt.ylabel(f'Bandpower ({unit})')
                plt.xticks(range(len(bands)), bands)
                plt.grid(True, alpha=0.3)
                plt.tight_layout()

                # 保存图表
                fname = f'{channel}_{metric}_bandpower{savetime}.{img_format}'
                plt.savefig(
                    os.path.join(save_dir, fname),
                    dpi=dpi,
                    bbox_inches='tight'
                )
                plt.close()

    def _save_average_plots(self, save_dir, bands, metrics, savetime, img_format='png', dpi=300):
        """保存平均值图表"""
        avg_data = next((data for data in self.result if data['Channel'] == 'Average'), None)
        if not avg_data:
            return

        for metric, unit in metrics:
            # 创建图表
            plt.figure(figsize=(8, 6))

            # 获取数据并绘图
            values = [avg_data[f"{band}_{metric}"] for band in bands]
            plt.bar(range(len(bands)), values, width=0.4, color='black')

            # 设置图表属性
            plt.title(f'Average {metric.replace("_", " ").title()} Bandpower')
            plt.xlabel('Frequency Bands')
            plt.ylabel(f'Bandpower ({unit})')
            plt.xticks(range(len(bands)), bands)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()

            # 保存图表
            fname = f'average_{metric}_bandpower{savetime}.{img_format}'
            plt.savefig(
                os.path.join(save_dir, fname),
                dpi=dpi,
                bbox_inches='tight'
            )
            plt.close()


class BandpowerAnalysisViewer(BasicalAnalysis):

    def __init__(self, title, channel_name, parent=None):
        super().__init__(title, channel_name, parent)
        self.setWindowTitle("Bandpower Analysis")

    def init_center_and_bottom(self, content_layout):
        self.viewer = BandpowerCenterViewer()
        super().init_center_and_bottom(content_layout)
        self.h_layout.addWidget(self.viewer)
        self.viewer.hide()

    def init_left_panel(self, content_layout):
        """自定义左侧控制栏"""
        # 调用父类的 init_left_panel 方法
        super().init_left_panel(content_layout)

        #添加 time_selector
        self.left_layout.addWidget(self.time_selector)

        # 添加分割线
        separator_between_time_and_frequency = QFrame()
        separator_between_time_and_frequency.setFrameShape(QFrame.HLine)
        separator_between_time_and_frequency.setStyleSheet("background-color: #a9a9a9;")
        separator_between_time_and_frequency.setFixedHeight(1)
        self.left_layout.addWidget(separator_between_time_and_frequency)

        # 添加频率选择控件
        freq_dict = {
            "Delta": (0.5, 4),
            "Theta": (4, 8),
            "Alpha": (8, 12),
            "Beta": (12, 30),
            "Gamma": (30, 100),
            "Other": (0.5, 200)
        }
        # self.frequency_selector = FrequencyCheckboxWidget(freq_dict=freq_dict, label_text="Frequency(Hz)")
        self.frequency_selector = CustomFrequencyCheckboxWidget(freq_dict=freq_dict, label_text="Frequency(Hz)")

        # self.left_layout.setContentsMargins(0,0,0,50)
        self.left_layout.addWidget(self.frequency_selector)

        # 创建一个空白区域
        spacerItem = QSpacerItem(314, 50, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.left_layout.addSpacerItem(spacerItem)
        self.left_layout.addStretch()

    def check_frequency_overlap(self, selected_frequencies):
        """检查所选频段是否存在频率交叉（排除Other频段）"""
        # 过滤掉"Other"频段，仅保留需要检查的频段
        filtered_bands = [
            (band, (min_freq, max_freq))
            for band, (min_freq, max_freq) in selected_frequencies.items()
            if band != "Other"  # 排除Other频段
        ]

        # 如果有效频段不足2个，无需检查交叉
        if len(filtered_bands) < 2:
            return False

        # 将剩余频段按最小值排序
        sorted_bands = sorted(filtered_bands, key=lambda x: x[1][0])

        # 检查相邻频段是否交叉
        for i in range(len(sorted_bands) - 1):
            current_band, (current_min, current_max) = sorted_bands[i]
            next_band, (next_min, next_max) = sorted_bands[i + 1]
            # 若当前频段最大值 > 下一个频段最小值，存在交叉
            if current_max > next_min:
                return True
        return False

    def on_analyse_clicked(self):
        """处理 Analyse 按钮点击事件"""

        # 获取已选频段
        selected_frequencies = self.frequency_selector.get_selected_frequencies()

        # 检查频率交叉（现在只返回一个布尔值）
        if self.check_frequency_overlap(selected_frequencies):
            QMessageBox.warning(
                self.win,
                "Frequency band overlap",
                "One or more overlaps exist among the selected frequency bands！"
            )
            return  # 存在交叉，阻止分析

        # 调用父类的检查逻辑
        if not super().on_analyse_clicked():
            return  # 如果父类返回 None，直接退出

        QLLogging.log.debug("basical analysis-Bandpower Analyse begin.")
        OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'basical analysis-Bandpower Analyse begin！',
                    0)
        # 将时间范围转换为秒
        # 调用 calculate_bandpower 时传入时间范围
        time_range = self.time_selector.get_time_range()
        self.worker = BandpowerWorker(self.raw, self.channel_selector.get_selected_channels(),
                                      self.frequency_selector.get_selected_frequencies(), time_range)
        # 连接信号
        self.worker.result_ready.connect(self.on_worker_result_ready)  # 连接结果信号
        self.worker.progress.connect(self.on_worker_progress)  # 可选：连接进度信号
        self.worker.error.connect(self.on_worker_error)  # 可选：连接错误信号

        self.worker.start()
        self.viewer.channel_names = self.channel_selector.get_selected_channels()
        QLLogging.log.debug(f"basical analysis-Bandpower Analyse started with channels: {self.viewer.channel_names} and bands: \
                            {self.frequency_selector.get_selected_frequencies()}")
