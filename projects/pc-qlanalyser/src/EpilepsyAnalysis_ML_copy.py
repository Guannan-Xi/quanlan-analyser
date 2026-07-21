from PyQt5.QtCore import QCoreApplication, Qt
import time
import logging
import os
import datetime
import numpy as np
import pandas as pd
import scipy.signal
import scipy.stats
import joblib
from PyQt5.QtWidgets import QDialog, QMessageBox, QApplication, QProgressDialog
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import pyqtgraph as pg

import pyeeg
from .Control_Style import ControlStyle
from .Domain.OPLog.OPLog import OPLog, OPType

from .EpilepsyAnalysis import emit_and_schedule, detect_seizures
from .EpilepsyAnalysis import Thread_run_analysis, TopWidget, BottomRightTopWidget, Ui_epilepsy_analysis
from .Infrastructure.DB.SQLLiteAccessor import SQLLiteDB_Only_MainTread
from .Infrastructure.log.QLLogging import QLLogging

from .SavePicCPM import SavePictureDialog2, SavePictureDialog


def compute_tkeo(epoch):
    """Compute the Teager-Kaiser Energy Operator for a 1D signal epoch."""
    tkeo = np.empty_like(epoch)
    for i in range(len(epoch)):
        if i == 0 or i == len(epoch) - 1:
            tkeo[i] = epoch[i]
        else:
            tkeo[i] = epoch[i] ** 2 - epoch[i + 1] * epoch[i - 1]
    return tkeo


def butter_bandpass(lowcut, highcut, fs, order=6):
    nyq = 0.5 * fs

    # 参数验证
    if lowcut <= 0:
        lowcut = 0.1  # 避免使用0作为低频截止点

    if highcut >= nyq:
        highcut = nyq - 0.1  # 确保高频截止点低于Nyquist频率

    if lowcut >= highcut:
        # 如果低频截止点高于或等于高频截止点，调整为可行的带宽
        logging.warning(f"Invalid filter parameters: lowcut={lowcut}, highcut={highcut}, fs={fs}")
        lowcut = max(0.1, highcut - 1.0)

    # 计算归一化频率
    low = lowcut / nyq
    high = highcut / nyq

    try:
        b, a = scipy.signal.butter(order, [low, high], btype='band')
        return b, a
    except Exception as e:
        logging.error(f"Failed to create filter with params: lowcut={lowcut}, highcut={highcut}, fs={fs}: {e}")
        # 返回一个平坦的滤波器，不会修改信号
        return [1.0], [1.0]

def butter_bandpass_filter(data, lowcut, highcut, fs, order=6):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    try:
        y = scipy.signal.filtfilt(b, a, data)
        return y
    except Exception as e:
        logging.error(f"Failed to apply filter: {e}")
        return data

def extract_features_using_epochs(data_segment, fs):
    """
    使用新算法提取特征

    参数：
        data_segment: 形状为 [num_epochs, 1, window_length_samples] 的EEG数据段
        fs: 采样频率

    返回：
        numpy数组，每行是一个epoch的特征向量
    """
    num_epochs = data_segment.shape[0]
    feature_list = []

    # 计算Nyquist频率
    nyq = 0.5 * fs

    # 处理每个epoch
    for i in range(num_epochs):
        epoch = data_segment[i, 0, :]

        # 提取特征
        feat = {}
        # 时域特征
        feat['mean'] = np.mean(epoch)
        # Hjorth参数: pyeeg.hjorth返回(activity, mobility, complexity)
        hj_params = pyeeg.hjorth(epoch.tolist())
        feat['mobility'] = hj_params[1]  # 使用mobility参数

        # Teager-Kaiser能量算子(TKEO)
        tkeo_epoch = compute_tkeo(epoch)
        feat['TKEO'] = np.mean(tkeo_epoch)

        # 频域特征: 不同频带的绝对功率
        # 确保滤波器频率不超过Nyquist频率

        # Delta带(0.1 - 4 Hz)
        delta = butter_bandpass_filter(epoch, 0.1, min(4, nyq - 0.1), fs, order=6)
        feat['P_delta'] = np.mean(delta ** 2)

        # Theta带(4 - 8 Hz)
        if 4 < nyq:
            theta = butter_bandpass_filter(epoch, 4, min(8, nyq - 0.1), fs, order=6)
            feat['P_theta'] = np.mean(theta ** 2)
        else:
            feat['P_theta'] = 0

        # Alpha带(8 - 16 Hz)
        if 8 < nyq:
            alpha = butter_bandpass_filter(epoch, 8, min(16, nyq - 0.1), fs, order=6)
            feat['P_alpha'] = np.mean(alpha ** 2)
        else:
            feat['P_alpha'] = 0

        # Beta带(16 - 32 Hz)
        if 16 < nyq:
            beta = butter_bandpass_filter(epoch, 16, min(32, nyq - 0.1), fs, order=6)
            feat['P_beta'] = np.mean(beta ** 2)
        else:
            feat['P_beta'] = 0

        # Gamma带(32 - 64 Hz)
        if 32 < nyq:
            gamma_high = min(64, nyq - 0.1)
            if gamma_high > 32:  # 确保带通滤波器有足够的带宽
                gamma = butter_bandpass_filter(epoch, 32, gamma_high, fs, order=6)
                feat['P_gamma'] = np.mean(gamma ** 2)
            else:
                feat['P_gamma'] = 0
        else:
            feat['P_gamma'] = 0

        # 总功率
        feat['P_total'] = np.mean(epoch ** 2)

        # 相对功率特征
        total_power = feat['P_total']
        if total_power > 0:
            feat['rel_delta'] = feat['P_delta'] / total_power
            feat['rel_theta'] = feat['P_theta'] / total_power
            feat['rel_alpha'] = feat['P_alpha'] / total_power
            feat['rel_beta'] = feat['P_beta'] / total_power
            feat['rel_gamma'] = feat['P_gamma'] / total_power
        else:
            feat['rel_delta'] = 0
            feat['rel_theta'] = 0
            feat['rel_alpha'] = 0
            feat['rel_beta'] = 0
            feat['rel_gamma'] = 0

        # 使用pyeeg计算的分形维数
        feat['pfd'] = pyeeg.pfd(epoch.tolist())

        # 偏度和峭度
        feat['skew'] = scipy.stats.skew(epoch)
        feat['kurtosis'] = scipy.stats.kurtosis(epoch)

        # 方差
        feat['var'] = np.var(epoch)

        # 信号包络：解析信号幅值的平均值
        analytic_signal = scipy.signal.hilbert(epoch)
        envelope = np.abs(analytic_signal)
        feat['envelope'] = np.mean(envelope)

        feature_list.append(feat)

    # 将特征列表转换为数组
    feature_columns = ['mean', 'mobility', 'TKEO',
                       'P_delta', 'P_theta', 'P_alpha',
                       'P_beta', 'P_gamma', 'P_total',
                       'rel_delta', 'rel_theta', 'rel_alpha', 'rel_beta',
                       'rel_gamma', 'pfd', 'skew', 'kurtosis', 'var', 'envelope']

    features_df = pd.DataFrame(feature_list)
    X = features_df[feature_columns].values
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return np.clip(X, -1e6, 1e6).astype(np.float32)

class Thread_run_analysis_ML(Thread_run_analysis):

    def run(self):
        try:
            start_time = time.time()
            print("----------------------------------run begin")

            progress = 10
            self.signal.emit([progress, "Analysis started"])
            emit_and_schedule(self.signal, progress + 1, 8, self.progressBar)

            # 根据epoch_length选择不同的模型
            if self.epoch_length == 3.0:
                model_path = os.path.join(os.path.dirname(__file__), 'newEpilepsy', 'model_n762_3s.sav')
                scaler_path = os.path.join(os.path.dirname(__file__), 'newEpilepsy', 'scaler_n762_3s.sav')
                self.signal.emit([progress, "Loading 3-second epoch model..."])
            elif self.epoch_length == 5.0:
                model_path = os.path.join(os.path.dirname(__file__), 'newEpilepsy', 'model_n1814_5s.sav')
                scaler_path = os.path.join(os.path.dirname(__file__), 'newEpilepsy', 'scaler_n1814_5s.sav')
                self.signal.emit([progress, "Loading 5-second epoch model..."])
            else:
                # 默认使用5秒模型
                model_path = os.path.join(os.path.dirname(__file__), 'newEpilepsy', 'model_n1814_5s.sav')
                scaler_path = os.path.join(os.path.dirname(__file__), 'newEpilepsy', 'scaler_n1814_5s.sav')
                self.signal.emit([progress, f"Using default 5-second model for {self.epoch_length}-second epochs..."])

            try:

                # 加载模型和标准化器
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)

                end_time1 = time.time()
                print(f"----------------加载模型和标准化器：time{end_time1 - start_time}")  # 0.23

                # 处理XGBoost模型的特殊属性
                if not hasattr(self.model, 'early_stopping_rounds'):
                    setattr(self.model, 'early_stopping_rounds', None)

                if not hasattr(self.model, 'callbacks'):
                    setattr(self.model, 'callbacks', [])

                if hasattr(self.model, 'use_label_encoder'):
                    self.model.use_label_encoder = False
                else:
                    setattr(self.model, 'use_label_encoder', False)

                end_time2 = time.time()
                print(f"----------------处理XGBoost模型的特殊属性：time{end_time2 - end_time1}")  # 0.0

                progress = 20
                self.signal.emit([progress, "Model loaded successfully"])
                emit_and_schedule(self.signal, progress + 1, 8, self.progressBar)
            except Exception as e:
                logging.error(f"Error loading model: {e}")
                self.signal.emit([progress, f"Error loading model: {e}"])
                raise

            # 确保raw_processed存在
            if self.raw_processed is None:
                raise ValueError("No data loaded")

            # 确保采样频率足够高，至少需要100Hz才能正确提取频带特征
            original_sfreq = self.raw_processed.info['sfreq']
            if original_sfreq < 100:
                logging.warning(f"采样频率过低({original_sfreq}Hz)，这可能影响特征提取。尝试使用更高采样率的数据。")
                self.signal.emit([progress, f"警告：采样频率较低({original_sfreq}Hz)，可能影响分析质量"])

            # 获取所有通道数据
            end_time3 = time.time()
            self.sfreq = self.raw_processed.info['sfreq']
            # 只调用一次方式
            all_data = self.raw_processed.get_data()

            self.eeg_data = all_data[self.eeg_channel]
            self.emg_data = all_data[self.emg_channel]
            self.acc_data = all_data[self.acc_channel] * 1e-6

            end_time4 = time.time()
            print(f"----------------获取所有通道数据：time{end_time4 - end_time3}")  # 10.0

            # 计算时频图数据 - 在特征提取之前计算
            progress = 30
            self.signal.emit([progress, "Calculating spectrogram..."])
            emit_and_schedule(self.signal, progress + 1, 15, self.progressBar)
            self.emg_envelope = np.abs(scipy.signal.hilbert(self.emg_data))

            self.spectrogram_data = self.calculate_spectrogram(self.sfreq)
            if self.spectrogram_data is None:
                logging.warning("Failed to calculate spectrogram")
            else:
                logging.info("Spectrogram calculation completed")

            end_time4 = time.time()
            print(f"----------------计算时频图数据：time{end_time4 - end_time3}")  # 18.0

            # 特征提取和预测
            progress = 60
            self.signal.emit([progress, "Extracting features..."])
            emit_and_schedule(self.signal, progress + 1, 8, self.progressBar)

            # 重新组织数据为epochs
            epoch_samples = int(self.epoch_length * self.sfreq)
            n_epochs = len(self.eeg_data) // epoch_samples
            eeg_data_epochs = self.eeg_data[:n_epochs * epoch_samples]
            eeg_data_epochs = eeg_data_epochs.reshape(n_epochs, 1, epoch_samples)

            # 使用新算法提取特征
            features = extract_features_using_epochs(eeg_data_epochs, self.sfreq)

            end_time5 = time.time()
            print(f"----------------特征提取：time{end_time5 - end_time4}")  # 80.0

            # 使用加载的标准化器缩放特征
            features_scaled = self.scaler.transform(features)

            end_time_ = time.time()
            print(f"----------------特征提取：time{end_time_ - end_time5}")  # 80.0

            progress = 70
            self.signal.emit([progress, "Making predictions..."])
            emit_and_schedule(self.signal, progress + 1, 8, self.progressBar)

            # 使用新模型进行预测
            predictions_proba = self.model.predict_proba(features_scaled)[:, 1]
            predictions = (predictions_proba >= 0.5).astype(int)

            end_time6 = time.time()
            print(f"----------------使用新模型进行预测：time{end_time6 - end_time5}")  # 0.04

            # 创建结果DataFrame
            progress = 80
            self.signal.emit([progress, "Creating score file..."])
            emit_and_schedule(self.signal, progress + 1, 8, self.progressBar)

            df_score = pd.DataFrame({
                "Epoch No.": list(range(len(predictions))),
                "Stage_Code": predictions
            })

            # 添加阶段名称
            stage_code = {0: "Normal", 1: "Seizure"}
            df_score["Stage"] = df_score["Stage_Code"].map(stage_code)

            end_time7 = time.time()
            print(f"----------------保存初始分期结果：time{end_time7 - end_time6}")  # 0.08

            # 在完成预测和动态阈值筛选后，添加癫痫检测代码
            progress = 90
            self.signal.emit([progress, "Detecting seizures..."])
            emit_and_schedule(self.signal, progress + 1, 8, self.progressBar)

            # 获取测量时间
            meas_date = self.raw_processed.info.get('meas_date', None)
            if meas_date is None:
                start_time_ts = datetime.datetime.now().timestamp()
            else:
                start_time_ts = (meas_date[0] + meas_date[1] * 1e-6
                                 if isinstance(meas_date, tuple)
                                 else meas_date.timestamp())

            # 检测癫痫发作
            seizure_info, seizure_per_minute_df, seizure_epoch_mask = detect_seizures(
                df_score['Stage_Code'].values,
                self.eeg_data,
                self.sfreq,
                epoch_length=self.epoch_length,
                start_time_ts=start_time_ts,
                min_no_seizure_epochs=3
            )

            end_time8 = time.time()
            print(f"----------------检测癫痫发作：time{end_time8 - end_time7}")

            progress = 100
            self.signal.emit([progress, "Saving results..."])

            # 保存癫痫发作信息到Excel文件
            if seizure_info:
                seizure_df = pd.DataFrame(seizure_info)
                minute_df = pd.DataFrame({
                    '分钟': seizure_per_minute_df['Minute'],
                    '癫痫发作次数': seizure_per_minute_df['Seizure Count'],
                    'UTC 时间': seizure_per_minute_df['UTC Time']
                }) if seizure_per_minute_df is not None else None

                # 暴露给 UI，等用户点 Save Data 再统一写盘
                self.seizure_df = seizure_df
                self.minute_df = minute_df

            # 保存结果到内存以供后续使用

            self.df_score = df_score
            self.seizure_info = seizure_info
            self.seizure_per_minute = seizure_per_minute_df
            # 每个 epoch 是否属于某次癫痫发作（0/1 掩码）
            self.seizure_epoch_mask = seizure_epoch_mask
            self.start_time_ts = start_time_ts

            end_time9 = time.time()
            print(f"----------------保存癫痫发作信息到Excel文件：time{end_time9 - end_time8}")

            end_time = time.time()
            print(f"run end----------------------------{end_time - start_time}")

        except Exception as e:
            logging.exception("Analysis thread error")  # 这会记录完整的堆栈跟踪
            self.signal.emit([-1, str(e)])  # 发送错误信号
            return  # 确保线程正常退出

    def save_results_to(self, output_dir: str,formatted_time):
        import os, pandas as pd
        if not output_dir:
            raise ValueError("output_dir is empty")
        os.makedirs(output_dir, exist_ok=True)

        # 只写 seizure_info；优先写 Excel，失败回退 CSV
        if getattr(self, "seizure_df", None) is not None:
            excel_path = os.path.join(output_dir, f"seizure_info_ML_{formatted_time}.xlsx")
            try:
                with pd.ExcelWriter(excel_path, engine="openpyxl", mode="w") as w:
                    self.seizure_df.to_excel(w, sheet_name="癫痫发作详情", index=False)
                    if getattr(self, "minute_df", None) is not None:
                        self.minute_df.to_excel(w, sheet_name="每分钟发作频率", index=False)
            except Exception:
                self.seizure_df.to_csv(os.path.join(output_dir, f"seizure_info_ML_{formatted_time}.csv"),
                                       index=False, encoding="utf-8-sig")
                if getattr(self, "minute_df", None) is not None:
                    self.minute_df.to_csv(os.path.join(output_dir, f"seizure_info_per_minute_ML_{formatted_time}.csv"),
                                          index=False, encoding="utf-8-sig")


class TopWidget_ML(TopWidget):

    def initUI(self, parent=None):
        super().initUI(parent)
        self.retranslateUi()

BottomRightTopWidget_ML = BottomRightTopWidget

class Ui_epilepsy_analysis_ML(Ui_epilepsy_analysis):
    def open_save_picture_ui(self):

        # from datetime import datetime

        # 获取当前日期和时间
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d-%H%M%S")
        save_pic_dialog = SavePictureDialog(self)
        total_pages = self.get_total_page()
        if save_pic_dialog.exec_() == QDialog.Accepted:
            try:
                # 获取到要保存的路径，dpi和图片格式
                params = save_pic_dialog.get_save_parameters()
                img_format = params['format'].lower().replace('.', '')
                dpi = params['resolution']

                # 创建保存目录
                default_folder = "Epilepsy_ML_Analysis_pic"
                save_dir = os.path.join(params['path'], default_folder)
                os.makedirs(save_dir, exist_ok=True)

                error_segments = []
                current_page = self.getCurrentPage()

                if dpi < 200:
                    # 弹出“请等待”消息框
                    wait_box = QMessageBox(QMessageBox.Information, "Please wait",
                                           "Pic is being saved, do not close the window...",
                                           parent=self)
                else:
                    # 弹出“请等待”消息框
                    wait_box = QMessageBox(QMessageBox.Information, "Please wait",
                                           f"Saving <span style='color: blue;'>{dpi}</span> dpi image, please allow some time, kindly be patient."
                                           ,
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

                # 刷新 GUI
                QApplication.processEvents()

                import time
                time.sleep(0.2)  # 小延时以确保渲染完成
                # 保存当前段
                self._save_single_segment(
                    save_dir=save_dir,
                    formatted_time=formatted_time,
                    img_format=img_format,
                    dpi=dpi,
                    segment_idx=current_page,  # current_page 记录当前段索引

                )
                wait_box.close()

                # 显示保存结果
                result_msg = f"Successfully saved to\n{save_dir}"
                if error_segments:
                    result_msg += f"\n\n错误段：{', '.join(map(str, error_segments))}"
                QMessageBox.information(self, "Save Complete", result_msg)

                OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, '保存睡眠分析图片', 0)
                QLLogging.log.info(f"睡眠分析图片保存完成：{save_dir}")

            except Exception as e:
                # 异常时先关等待框，再报错
                try:
                    if wait_box and wait_box.isVisible():
                        wait_box.close()
                finally:
                    pass
                QLLogging.log.exception(f"保存图片失败: {str(e)}")
                QMessageBox.critical(self, "保存失败", f"保存图片时出错：{str(e)}")

            finally:
                # 兜底清理
                if wait_box:
                    try:
                        if wait_box.isVisible():
                            wait_box.close()
                    finally:
                        wait_box.deleteLater()

    def _save_single_segment(self, save_dir, formatted_time, img_format, dpi, segment_idx):
        """保存单个段的所有图片（EEG、EMG、ACC、频谱图）"""
        try:
            # 生成带段索引的文件名前缀
            segment_suffix = f"segment_{segment_idx}_{formatted_time}"
            result_path = os.path.join(save_dir, f"EpilepsyAnalysis_ML{segment_suffix}.{img_format}")

            for ax in self.figure.get_axes():
                # 隐藏Y轴（轴线、刻度、标签）
                ax.yaxis.set_visible(False)

                # 确保X轴保持可见
                ax.xaxis.set_visible(True)

            preSize = self.figure.get_size_inches()
            tmpSize = (64, 4)
            resetFlag = False
            if dpi > 200:
                resetFlag = True
                self.figure.set_size_inches(tmpSize)
            self.figure.savefig(
                result_path,
                dpi=dpi,
                format=img_format,
                bbox_inches='tight',  # 重要：防止裁剪
                pad_inches=0.1  # 可选：增加边缘空间
            )  # 这里有一个问题：figure有残缺的，无法保存完整的图片
            # 尺寸改回来
            if resetFlag:
                self.figure.set_size_inches(preSize)

            # 保存 plot_widget 图片
            self.save_plot_widget(self.plot_eeg, save_dir,
                                  f"EpilepsyAnalysis_ML_eeg{segment_suffix}.{img_format}", dpi, img_format)
            self.save_plot_widget(self.plot_emg, save_dir,
                                  f"EpilepsyAnalysis_ML_emg{segment_suffix}.{img_format}", dpi, img_format)
            self.save_plot_widget(self.plot_acc, save_dir,
                                  f"EpilepsyAnalysis_ML_acc{segment_suffix}.{img_format}", dpi, img_format)
            self.save_Frequencywidget_current(self.plot_widget, save_dir,
                                              f"EpilepsyAnalysis_ML_Frequency{segment_suffix}.{img_format}", dpi,
                                              img_format)
            QLLogging.log.debug(f"成功保存段 {segment_idx} 图片")
            return True

        except Exception as e:
            QLLogging.log.error(f"保存段 {segment_idx} 图片失败: {str(e)}")
            raise  # 抛出异常让上层处理

    def save_Frequencywidget_current(self, plot_widget, save_dir, filename, dpi, img_format):
        try:
            result_path = os.path.join(save_dir, filename)
            plot_item = plot_widget.plotItem
            img_items = [item for item in plot_item.items if isinstance(item, pg.ImageItem)]

            if img_items:
                img_item = img_items[0]
                img_data = img_item.image

                # 获取当前视图范围
                view_range = plot_item.getViewBox().viewRange()[0]
                x_min_view, x_max_view = view_range

                # 获取坐标转换参数
                tr = img_item.transform()
                x_start = tr.dx()
                x_scale = tr.m11()
                y_start = tr.dy()
                y_scale = tr.m22()

                # 计算裁剪范围
                start_col = int((x_min_view - x_start) / x_scale)
                end_col = int((x_max_view - x_start) / x_scale)
                start_col = max(0, start_col)
                end_col = min(img_data.shape[0], end_col)

                # 执行裁剪
                cropped_data = img_data[start_col:end_col, :]
                cropped_x_start = x_start + start_col * x_scale
                cropped_x_end = x_start + end_col * x_scale
                y_end = y_start + img_data.shape[1] * y_scale

                # 创建图形和绘图
                fig, ax = plt.subplots(figsize=(14, 4), dpi=dpi)

                # CET-R4 颜色映射的 RGB 值
                cet_r4_data = [
                    (0.0, 0.0, 0.3),
                    (0.0, 0.0, 1.0),
                    (0.0, 1.0, 1.0),
                    (1.0, 1.0, 0.0),
                    (1.0, 0.0, 0.0),
                    (0.5, 0.0, 0.0)
                ]

                # 创建 CET-R4 颜色映射
                cet_r4_cmap = LinearSegmentedColormap.from_list("CET-R4", cet_r4_data)
                # 绘制图像
                spec_data = self.thread_run.spectrogram_data
                vmin = spec_data.get('vmin', img_data.min())
                vmax = spec_data.get('vmax', img_data.max())

                im = ax.imshow(
                    cropped_data.T,
                    extent=[cropped_x_start, cropped_x_end, y_start, y_end],
                    aspect='auto',  # 自动适应宽高比，与PyQtGraph的缩放行为一致
                    origin='lower',  # 原点在左下角（低频在底部，对应PyQtGraph invertY=False）
                    cmap=cet_r4_cmap,  # 颜色映射，与PyQtGraph的CET-R4接近
                    vmin=vmin,
                    vmax=vmax
                )
                # 设置坐标轴
                ax.set_xlabel(plot_item.axes["bottom"]["item"].label.toPlainText())
                ax.set_ylabel(plot_item.axes["left"]["item"].label.toPlainText())

                # # 添加colorbar
                plt.colorbar(im, ax=ax, label='Power (dB)')
                # 保存图像
                fig.savefig(result_path,
                            format=img_format,
                            dpi=dpi,
                            bbox_inches='tight')
                plt.close(fig)
                return
        except ValueError as e:
            QLLogging.log.exception(f"open_save_picture_ui, error: {e}")

    def save_Frequencywidget(self, plot_widget, save_dir, filename, dpi, img_format):
        # 导出 PyQtGraph 图像
        try:
            result_path = os.path.join(save_dir, filename)
            # 处理频谱图
            plot_item = plot_widget.plotItem
            img_items = [item for item in plot_item.items if isinstance(item, pg.ImageItem)]

            if img_items:
                img_item = img_items[0]
                img_data = img_item.image

                # 创建matplotlib图形
                fig, ax = plt.subplots(figsize=(14, 4), dpi=dpi)

                # 获取坐标范围
                tr = img_item.transform()
                x_start = tr.dx()
                y_start = tr.dy()
                x_scale = tr.m11()
                y_scale = tr.m22()

                # 计算实际坐标
                x_end = x_start + img_data.shape[0] * x_scale
                y_end = y_start + img_data.shape[1] * y_scale
                # CET-R4 颜色映射的 RGB 值
                cet_r4_data = [
                    (0.0, 0.0, 0.3),
                    (0.0, 0.0, 1.0),
                    (0.0, 1.0, 1.0),
                    (1.0, 1.0, 0.0),
                    (1.0, 0.0, 0.0),
                    (0.5, 0.0, 0.0)
                ]

                # 创建 CET-R4 颜色映射
                cet_r4_cmap = LinearSegmentedColormap.from_list("CET-R4", cet_r4_data)
                # 绘制图像
                spec_data = self.thread_run.spectrogram_data
                vmin = spec_data.get('vmin', img_data.min())
                vmax = spec_data.get('vmax', img_data.max())
                im = ax.imshow(
                    img_data.T,  # 原始数据（不转置，与PyQtGraph数据方向一致）
                    extent=[x_start, x_end, y_start, y_end],  # 坐标范围：[x_min, x_max, y_min, y_max]
                    aspect='auto',  # 自动适应宽高比，与PyQtGraph的缩放行为一致
                    origin='lower',  # 原点在左下角（低频在底部，对应PyQtGraph invertY=False）
                    cmap=cet_r4_cmap,  # 颜色映射，与PyQtGraph的CET-R4接近
                    vmin=vmin,
                    vmax=vmax
                )
                # 设置坐标轴
                ax.set_xlabel(plot_item.axes["bottom"]["item"].label.toPlainText())
                ax.set_ylabel(plot_item.axes["left"]["item"].label.toPlainText())

                # # 添加colorbar
                plt.colorbar(im, ax=ax, label='Power (dB)')
                # 保存图像
                fig.savefig(result_path,
                            format=img_format,
                            dpi=dpi,
                            bbox_inches='tight')
                plt.close(fig)
                return

        except ValueError as e:
            QLLogging.log.exception(f"open_save_picture_ui, error: {e}")
    def open_save_data_ui(self):
        from .SavePicCPM import SaveDataDialog
        from .utils import pretreatment_df_score
        from datetime import timedelta

        # 获取当前日期和时间
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d-%H%M%S")
        df_display_score = self._get_display_score_df()  # 获取修正后的结果
        combined_data = pretreatment_df_score(self.thread_run, df_display_score)  # 保存修正后的序列
        save_data_dialog = SaveDataDialog(self)
        # 用北京时间替换第一列
        # 起始时间（界面里已经按北京时间设置过 self.start_datetime）
        start_dt = self.start_datetime.toPyDateTime()  # QDateTime -> datetime
        epoch_len = int(self.thread_run.epoch_length)
        n_epochs = len(self.df_score)

        # 生成每个 epoch 的北京时间戳（字符串或 datetime 都可以；这里用字符串便于 CSV）
        bj_times = [
            (start_dt + timedelta(seconds=i * epoch_len)).strftime("%Y-%m-%d %H:%M:%S")
            for i in range(n_epochs)
        ]
        print(bj_times)
        # 确保是字符串类型
        bj_times = list(map(str, bj_times))

        # combined_data 可能是 DataFrame 或 dict/Series；都兼容处理：
        try:
            # 如果是 DataFrame
            if "Epoch No." in combined_data.columns:
                combined_data.drop(columns=["Epoch No."], inplace=True)
            # 将时间列插入到第一列
            combined_data.insert(0, "Beijing_Time", bj_times)
        except AttributeError:
            # 如果是 dict-like
            combined_data.pop("Epoch No.", None)
            combined_data = pd.DataFrame(combined_data)
            combined_data.insert(0, "Beijing_Time", bj_times)
        save_data_dialog.combobox_data_format.addItem(".mat")
        save_data_dialog.combobox_data_format.addItem(".cache")
        if save_data_dialog.exec_() == QDialog.Accepted:
            try:
                # 获取保存的参数
                params = save_data_dialog.get_save_parameters()
                img_format = params['format'].lower().replace('.', '')
                # 创建保存目录
                default_folder = "Epilepsy_ML_Analysis_data"
                save_dir = os.path.join(params['path'], default_folder)
                os.makedirs(save_dir, exist_ok=True)

                # 弹出“请等待”消息框
                wait_box = QMessageBox(QMessageBox.Information, "请稍等", "数据正在保存中，请勿关闭窗口...", parent=self)
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

                # 刷新 GUI
                QApplication.processEvents()

                # 用修正后的 df_display_score 重新计算 seizure 统计，再写盘
                start_time_ts = getattr(self.thread_run, 'start_time_ts', None)
                new_seizure_info, new_seizure_per_minute_df, new_seizure_epoch_mask = detect_seizures(
                    self.df_display_score['Stage_Code'].values,
                    self.thread_run.eeg_data,
                    self.thread_run.sfreq,
                    epoch_length=self.thread_run.epoch_length,
                    start_time_ts=start_time_ts,
                    min_no_seizure_epochs=3
                )
                if new_seizure_info:
                    self.thread_run.seizure_df = pd.DataFrame(new_seizure_info)
                    self.thread_run.minute_df = pd.DataFrame({
                        '分钟': new_seizure_per_minute_df['Minute'],
                        '癫痫发作次数': new_seizure_per_minute_df['Seizure Count'],
                        'UTC 时间': new_seizure_per_minute_df['UTC Time']
                    }) if new_seizure_per_minute_df is not None else None
                    # # 同步更新基于最新分期结果的 epoch 掩码
                    # self.thread_run.seizure_epoch_mask = new_seizure_epoch_mask
                else:
                    self.thread_run.seizure_df = pd.DataFrame()
                    self.thread_run.minute_df = None

                self.thread_run.save_results_to(save_dir,formatted_time)

                if img_format == "csv":
                    file_path = os.path.join(save_dir,
                                             f"{self.file_name}-epilepsy_data{formatted_time}.csv")  # 拼接目录和文件名
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

                    QLLogging.log.info(f"save epilepsy_data.csv success")

                elif img_format == 'mat':
                    # 这里需要进行检测，还是有点问题
                    from scipy.io import savemat
                    file_path = os.path.join(save_dir,
                                             f"{self.file_name}-epilepsy_data{formatted_time}.mat")  # 拼接目录和文件名
                    combined_dict = combined_data.to_dict("list")
                    # 保存为MAT文件，'data'是MAT文件中存储数据的变量名
                    savemat(file_path, {'data': combined_dict})

                    QLLogging.log.info(f"save epilepsy_data.mat success")

                elif img_format == "npy":
                    file_path = os.path.join(save_dir,
                                             f"{self.file_name}-epilepsy_data{formatted_time}.npy")  # 拼接目录和文件名
                    # 假设 df 是你想要保存的 DataFrame
                    df = pd.DataFrame(combined_data)
                    # 将 DataFrame 转换成 NumPy 数组
                    numpy_data = df.to_numpy()
                    # 使用 numpy.save 保存数组到 .npy 文件
                    np.save(file_path, numpy_data)  # 注意文件路径最好是 '.npy' 结尾以便识别

                    QLLogging.log.info(f"save epilepsy_data.npy success")

                elif img_format == 'cache':

                    file_path = os.path.join(save_dir,
                                             f"{self.file_name}-epilepsy_data_history{formatted_time}.cache")  # 拼接目录和文件名
                    print("file_path", file_path)
                    self.save_history_cache(file_path)

                    QLLogging.log.info(f"save epilepsy_data_history.cache success")

                # 关闭提示框
                wait_box.close()
                # 显示保存结果
                result_msg = f"Successfully saved to\n{save_dir}"
                QMessageBox.information(self, "Save Complete", result_msg)

                OPLog.write(SQLLiteDB_Only_MainTread.user_db, OPType.ANALYSE.value, 'open save data ui', 0)

            except Exception as e:
                QLLogging.log.exception(f"open_save_picture_ui, error: {e}")
    def get_thread_run(self):
        return Thread_run_analysis_ML(self.progressBar)

    def create_top_widget(self, parent):
        return TopWidget_ML(parent)

    def create_bottom_right_top_widget(self, parent):
        return BottomRightTopWidget_ML(parent)

    def retranslateUi(self, epilepsy_analysis):
        super().retranslateUi(epilepsy_analysis)
        _translate = QCoreApplication.translate
        epilepsy_analysis.setWindowTitle(_translate("epilepsy_analysis", "ML Epilepsy Analysis"))
        self.top_widget.epilepsy_analysis_label.setText(_translate("epilepsy_analysis", "ML Epilepsy Analysis"))

    def get_cache_directory_name(self):
        return os.path.join('Epilepsy_data_History', 'ML')
