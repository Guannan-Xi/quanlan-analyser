import mne
import numpy as np
from pyqtgraph.exporters import ImageExporter
from sklearn.preprocessing import MinMaxScaler
from .Infrastructure.log.QLLogging import QLLogging
import os
import time
import joblib
import threading
import pandas as pd
from scipy.io import savemat
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QApplication, QLineEdit, QWidget, QVBoxLayout, QLabel, QShortcut
from PyQt5.QtGui import QDoubleValidator, QPalette, QColor, QKeySequence
from PyQt5.QtCore import Qt
import sys


def ellip_filter(data, l_freq, h_freq, order, rp=1, rs=60, ftype='ellip'):
    copy_array = data.copy()
    data_array = copy_array.filter(l_freq=l_freq, h_freq=h_freq, method='iir',
                                   iir_params={'rp': rp, 'rs': rs, 'order': order, 'ftype': ftype})
    return data_array


def calc_NLEO(data_array, info, scale=1):
    data = data_array.get_data() * scale
    NLEO = np.zeros_like(data)
    # NLEO[:, :2] = data[:, :2]
    NLEO[:, :2] = 0
    for i in range(3, data.shape[1]):
        NLEO[0, i] = data[0, i] * data[0, i - 3] - data[0, i - 1] * data[0, i - 2]
    NLEO = np.abs(NLEO)
    nleo_array = mne.io.RawArray(NLEO, info)
    return nleo_array


def smooth_NLEO_bs(Fs, data_array, info, scale):
    window_len = int(Fs * 1)
    nleo_data = data_array.get_data()

    window = np.ones(window_len) / window_len
    smoothed_data = np.convolve(nleo_data[0], window, mode='same')

    scaler = MinMaxScaler()
    smoothed_data = np.array(smoothed_data).reshape(-1, 1)
    scaler.fit(smoothed_data)
    smoothed_data = scaler.transform(smoothed_data) * scale
    smoothed_data = np.reshape(smoothed_data, (1, -1))
    smoothed = mne.io.RawArray(smoothed_data, info)
    return smoothed


def smooth_NLEO(Fs, data_array, info, scale):
    window_len = int(Fs * 1)

    nleo_data = data_array.get_data() * scale

    window = np.ones(window_len) / window_len
    smoothed_data = np.convolve(nleo_data[0], window, mode='same')

    # scaler = MinMaxScaler()
    # smoothed_data = np.array(smoothed_data).reshape(-1, 1)
    # scaler.fit(smoothed_data)
    # smoothed_data = scaler.transform(smoothed_data) * 100
    smoothed_data = np.reshape(smoothed_data, (1, -1))
    smoothed = mne.io.RawArray(smoothed_data, info)
    return smoothed

    # smoothed_data = np.zeros_like(nleo_data)
    # smoothed_data[:, :window_len] = smoothed_data[:, :window_len]
    # for i in range(window_len, nleo_data.shape[-1]):
    #     tmp = nleo_data[:, (i-window_len):(i-1)]
    #     smoothed_data[:, i] = np.sum(tmp) / window_len
    # smoothed = mne.io.RawArray(smoothed_data, info)
    # return smoothed


def predict(smoothed_bs, smoothed_artifact, i, Fs, min_suppr_len, thr_artifact, thr_burst, thr_suppression):
    smoothed_bs_data = smoothed_bs.get_data()
    smoothed_artifact_data = smoothed_artifact.get_data()

    status = np.zeros(smoothed_bs_data.shape[-1])
    status[:2 * Fs] = 2

    if smoothed_artifact_data[:, i] >= thr_artifact and smoothed_bs_data[:, i] < thr_burst:
        burst_len = 0
        artifact_len += 1
        if artifact_len >= Fs and status[i - 1] != 0:
            status[i] = 2
            suppression_len = 0
        elif artifact_len >= 2 * Fs and status[i - 1] == 0:
            status[i] = 2
            suppression_len = 0
        elif suppression_len >= min_suppr_len * Fs:
            if smoothed_bs_data[:, i] <= thr_suppression:
                status[i] = 1
    elif smoothed_artifact_data[:, i] >= thr_artifact:
        suppression_len = 0
        artifact_len += 1
        burst_len += 1
        if artifact_len >= Fs and status[i - 1] != 0:
            status[i] = 2
            burst_len = 0
        elif artifact_len >= 2 * Fs and status[i - 1] == 0:
            status[i] = 2
            burst_len = 0
        # original
        elif burst_len >= Fs and status[i - 1] != 2:
            status[i] = 0
        elif burst_len >= 2 * Fs and status[i - 1] == 2:
            status[i] = 0
    elif smoothed_bs_data[:, i] >= thr_burst:
        artifact_len = 0
        suppression_len = 0
        burst_len += 1
        # original
        if burst_len >= Fs and status[i - 1] != 2:
            status[i] = 0
        elif burst_len >= 2 * Fs and status[i - 1] != 2:
            status[i] = 0
    else:
        artifact_len = 0
        burst_len = 0
        suppression_len += 1
        if suppression_len >= min_suppr_len * Fs:
            if smoothed_bs_data[:, i] <= thr_suppression:
                status[i] = 1


def truncate_to_multiple(arr, arr_length, multiple_of):
    """
    将数组裁剪为指定数的整数倍

    参数:
        arr: 输入的数组
        multiple_of: 目标整数倍数

    返回:
        裁剪后的数组
    """
    # 计算可以被整除的最大长度
    valid_length = arr_length * multiple_of
    # 截断数组
    return arr[:valid_length]


def pretreatment_df_score(thread_run, df_score):
    try:
        """处理数据"""
        block_size = int(len(thread_run.eeg_data) / len(df_score))

        # 进行裁剪成整数倍
        compressed_eeg_points = truncate_to_multiple(thread_run.eeg_data, len(df_score), block_size)  # 截取一下
        compressed_emg_points = truncate_to_multiple(thread_run.emg_data, len(df_score), block_size)  # 截取一下
        compressed_acc_points = truncate_to_multiple(thread_run.acc_data, len(df_score), block_size)  # 截取一下

        compressed_eeg_data = np.mean(compressed_eeg_points.reshape(-1, block_size), axis=1)
        compressed_emg_data = np.mean(compressed_emg_points.reshape(-1, block_size), axis=1)
        compressed_acc_data = np.mean(compressed_acc_points.reshape(-1, block_size), axis=1)

        df_score['EEG'] = compressed_eeg_data
        df_score['EMG'] = compressed_emg_data
        df_score['ACC'] = compressed_acc_data

        power = thread_run.spectrogram_data['power'].T

        block_size = int(len(power) / len(df_score))
        remaining_points = truncate_to_multiple(power, len(df_score), block_size)  # 截取一下

        # 将剩余点均分为1800块，每块10个点
        reshaped = remaining_points.reshape(len(df_score), block_size, len(thread_run.spectrogram_data['frequencies']))

        # 对每块的10个点取平均值
        compressed_power_data = np.mean(reshaped, axis=1)  # 形状: (1800, 199)

        compressed_df = pd.DataFrame(
            compressed_power_data,
            columns=[f'{i}Hz' for i in thread_run.spectrogram_data['frequencies']]
        )

        # 使用 Pandas 的 concat 保留列名
        combined_data = pd.concat([df_score, compressed_df], axis=1)
        print(f"拼接后形状: {combined_data.shape}")  # 输出: (1800, 204)

        # 将df_score的第一行的数字加1
        combined_data['Epoch No.'] = combined_data['Epoch No.'] + 1

    except Exception as e:
        QLLogging.log.exception(f"pretreatment_df_score error: {e}")
        # 【健壮性补充】异常时返回空df，避免程序崩溃
        combined_data = pd.DataFrame()

    return combined_data


def get_image_format(current_format):  # (["PNG", "JPEG", "SVG", "TIFF", "EPS"])
    if current_format == "PNG":
        return "png"
    elif current_format == "JPEG":
        return "jpg"
    elif current_format == "PNG":
        return "png"
    elif current_format == "SVG":
        return "svg"
    elif current_format == "TIFF":
        return "tif"
    elif current_format == "EPS":
        return "eps"


class SaveUtils:
    """文件和图片保存的工具类"""

    @staticmethod
    def save_data(df, default_dir=None, default_name=None, parent=None):
        """保存文件，格式为：.csv, .mat, .npy"""
        combined_data = pretreatment_df_score(parent.thread_run, df)

        # 打开文件对话框，支持多种格式
        options = QFileDialog.Options()

        # 构造默认路径
        if default_dir and default_name:
            default_path = os.path.join(default_dir, f"{default_name}.csv")
        else:
            default_path = ""

        file_path, _ = QFileDialog.getSaveFileName(
            parent,
            "保存文件",
            default_path,
            "CSV Files (*.csv);;MATLAB Files (*.mat);;NumPy Files (*.npy);;All Files (*)",
            options=options
        )

        if file_path:
            try:
                # 根据扩展名判断格式
                if file_path.endswith('.csv'):
                    df = pd.DataFrame(
                        combined_data
                    )

                    # 保存为CSV
                    df.to_csv(
                        file_path,  # 文件名
                        index=True,  # 是否保存索引
                        na_rep='nan',  # NaN值的表示方式
                        float_format='%.6f'  # 浮点数格式
                    )
                elif file_path.endswith('.mat'):
                    # 转化DataFrame为MATLAB格式并保存
                    mat_data = {col: df[col].values for col in df.columns}
                    savemat(file_path, mat_data)
                elif file_path.endswith('.npy'):
                    # 保存为 NumPy 数组（默认不保存列名和索引）
                    np.save(file_path, df.to_numpy())
                else:
                    QMessageBox.warning(parent.window, "Format Error", "Unsupported File Format")
                return True
            except Exception as e:
                QLLogging.log.exception(f"Error saving file: {e}")
                return False
        return False

    @staticmethod
    def save_pic(figure, default_dir=None, default_name=None, parent=None):
        """保存图片，格式为：.jpg, .png, .svg, .tif, .tiff, .eps"""
        # 打开文件对话框，支持多种格式
        options = QFileDialog.Options()

        # 构造默认路径
        if default_dir and default_name:
            default_path = os.path.join(default_dir, f"{default_name}.png")
        else:
            default_path = ""

        file_path, selected_filter = QFileDialog.getSaveFileName(
            parent,
            "保存图像",
            default_path,
            "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg);;SVG (*.svg);;TIFF (*.tif *.tiff);;EPS (*.eps);;All Files (*)",
            options=options
        )

        if file_path:
            # 根据用户选择的过滤器添加扩展名
            if 'JPEG' in selected_filter and not file_path.lower().endswith(('.jpg', '.jpeg')):
                file_path += '.jpg'
            elif 'PNG' in selected_filter and not file_path.lower().endswith('.png'):
                file_path += '.png'
            elif 'SVG' in selected_filter and not file_path.lower().endswith('.svg'):
                file_path += '.svg'
            elif 'TIFF' in selected_filter and not file_path.lower().endswith(('.tif', '.tiff')):
                file_path += '.tif'
            elif 'EPS' in selected_filter and not file_path.lower().endswith('.eps'):
                file_path += '.eps'

            try:
                figure.savefig(file_path)
                return True
            except Exception as e:
                QMessageBox.warning(parent.window, "Error", f"Save failed due to: {e}")
                return False
        return False


# 读取配置文件的单例类
class ConfigManager:
    _instance = None  # 存储的唯一实例

    def __new__(cls, file_path=None):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            # 初始化配置
            if file_path:
                cls._instance.config = cls._instance.read_dat_config(file_path)
            else:
                raise ValueError("file_path is not empty")
        return cls._instance  # 返回唯一实例

    def read_dat_config(cls, file_path):
        """读取配置文件的内容"""
        config = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):  # 跳过空行和注释
                        continue
                    key, value = line.split(':', 1)  # 按第一个冒号分割键值对
                    config[key.strip()] = value.strip().strip("'")  # 去除首尾空格和单引号

            return config
        except Exception as e:
            QLLogging.log.exception(f"read_dat_config exception: {e}")
            return

    def get_config(self):
        """获取当前配置"""
        return self.config


# 加载大模型数据的类
class ModelLoader:
    def __init__(self):
        self.model = None
        self.model_name = "2_LightGBM-1EEG"
        self.model_ready = threading.Event()  # 用于标记模型是否加载完成
        self.loading_lock = threading.Lock()  # 用于线程同步
        self.loading_error = None  # 存储加载过程中出现的错误
        # 创建加载模型的线程
        self.load_model_thread = threading.Thread(target=self._load_model_worker,
                                                  name="ModelLoaderThread",
                                                  daemon=True)

    def start_loading(self):
        """开始在线程中加载数据"""
        if not self.load_model_thread.is_alive():
            self.load_model_thread.start()

    def _load_model_worker(self):
        """在线程中执行的模型加载工作"""
        try:
            start_time = time.time()
            model_path = os.path.join(os.path.dirname(__file__), "Qlass", "models", f"{self.model_name}.pkl")

            with self.loading_lock:  # 确保线程安全
                self.model = joblib.load(model_path)
                print(self.model.get_params())
                self.loading_error = None

            end_time = time.time()
            print(f"模型加载完成，耗时：{end_time - start_time}秒")
            self.model_ready.set()  # 标记模型已加载

        except Exception as e:
            print(f"模型加载失败: {str(e)}")
            self.loading_error = e
            self.model_ready.set()  # 即使加载失败，也标记为已完成

    def is_model_ready(self):
        """检查模型是否已经加载完成"""
        return self.model_ready.is_set()

    def get_model(self, timeout=None):
        """获取模型，可选择等待模型加载完成

        Args:
            timeout: 等待模型加载的最长时间（秒），None表示无限等待

        Returns:
            加载好的模型或None

        Raises:
            Exception: 加载模型时发生的错误
        """
        # 如果模型还没加载好，等待
        if not self.model_ready.is_set():
            self.model_ready.wait(timeout=timeout)

        # 检查是否有加载错误
        if self.loading_error:
            raise self.loading_error

        return self.model


# 创建全局实例
model_loader = ModelLoader()


class RangeValidator(QDoubleValidator):
    def __init__(self, bottom, top, decimals=1, parent=None):
        # 明确参数顺序：bottom, top, decimals, parent
        super().__init__(bottom, top, decimals, parent)
        self.setNotation(QDoubleValidator.StandardNotation)

    def validate(self, input_text, pos):
        # 允许空输入（用户可能正在输入中）
        if input_text.strip() == "":
            return (QDoubleValidator.Intermediate, input_text, pos)

        # 允许单独的 0
        if input_text == "0":
            return (QDoubleValidator.Acceptable, input_text, pos)
        if input_text == "0.":
            return (QDoubleValidator.Intermediate, input_text, pos)
        if input_text == "0.0":
            return (QDoubleValidator.Intermediate, input_text, pos)
        if input_text == "0.00":
            return (QDoubleValidator.Intermediate, input_text, pos)

        # 检查小数点后的位数
        if '.' in input_text:
            decimal_part = input_text.split('.')[1]
            if len(decimal_part) > self.decimals():
                return (QDoubleValidator.Invalid, input_text, pos)

        try:
            value = float(input_text)
            if self.bottom() <= value <= self.top():
                return (QDoubleValidator.Acceptable, input_text, pos)
            else:
                return (QDoubleValidator.Invalid, input_text, pos)
        except ValueError:
            # 处理特殊情况，如仅输入小数点
            if input_text == '.':
                return (QDoubleValidator.Intermediate, input_text, pos)
            return (QDoubleValidator.Invalid, input_text, pos)


def setup_short_cut(button_previous, button_next, parent, callback_left, callback_right):
    # 为翻页添加箭头快捷键
    button_previous.setShortcut(Qt.Key_Left)
    button_next.setShortcut(Qt.Key_Right)

    # Shift+左箭头 - 例如：选择上一个时间窗口
    shortcut_shift_left = QShortcut(QKeySequence("Shift+Left"), parent)
    shortcut_shift_left.activated.connect(callback_left)

    # Shift+右箭头 - 例如：选择下一个时间窗口
    shortcut_shift_right = QShortcut(QKeySequence("Shift+Right"), parent)
    shortcut_shift_right.activated.connect(callback_right)


def save_plot_widget(plot_widget, save_dir, filename, dpi):
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


from PyQt5.QtWidgets import QActionGroup


def _ensure_persistent_style_and_group(menu):
    # 只做一次
    if getattr(menu, "_amp_group", None) is None:
        group = QActionGroup(menu)
        group.setExclusive(True)
        for act in menu.actions():
            act.setCheckable(True)  # 让每项可被“选中”（持久态）
            group.addAction(act)
        menu._amp_group = group

        # 样式：让“已选中”的项像高亮一样显眼；顺便把复选框隐藏掉
        menu.setStyleSheet("""
            QMenu::item:checked {
                background: palette(Highlight);
                color: palette(HighlightedText);
            }
            QMenu::indicator { width: 0px; } /* 隐藏小对勾 */
        """)


def _highlight_current_amplitude(menu, probe):
    """菜单弹出前，根据当前Y轴状态，高亮最匹配的菜单项"""
    try:
        _ensure_persistent_style_and_group(menu)
        # 由 probe 返回三元组：是否自动、ymin、ymax
        is_y_auto, y_min, y_max = probe()

        def _persist_select(act):
            # 持久标记：checked
            act.setChecked(True)
            # 让这项以“粗体默认项”呈现（不会随鼠标移动消失）
            menu.setDefaultAction(act)
            # 初始也设为 active，给用户一个起始高亮感（鼠标再动也不丢失持久标记）
            menu.setActiveAction(act)

        if is_y_auto:
            for act in menu.actions():
                if act.text().strip().lower() == 'auto':
                    _persist_select(act)
                    return

        # 幅度（对称菜单用 ±N；非对称如 0~N 也能算出 N）
        amp = int(round(max(abs(y_min), abs(y_max))))
        exact = f'±{amp}'

        # 完全匹配
        for act in menu.actions():
            if act.text().strip() == exact:
                _persist_select(act)
                return

        # 最近匹配
        import re
        closest_act, best = None, 10 ** 9
        for act in menu.actions():
            m = re.match(r'±\s*(\d+)', act.text().strip())
            if m:
                val = int(m.group(1))
                diff = abs(val - amp)
                if diff < best:
                    best = diff
                    closest_act = act
        if closest_act:
            _persist_select(closest_act)
    except Exception:
        pass


# 1) PyQtGraph
def probe_pg(plotwidget):
    vb = plotwidget.getPlotItem().getViewBox()
    auto_flags = vb.state.get('autoRange', [False, False])
    is_y_auto = bool(auto_flags[1])
    y_min, y_max = vb.viewRange()[1]
    return is_y_auto, y_min, y_max


# 2) Matplotlib高亮
def highlight_heart_rate_menu(menu, ax=None, fig=None, is_auto=False):
    """
    - 若 is_auto=True，高亮 'Auto'
    - 否则依据当前 Y 轴范围，按 ±N（或 0~N / N）匹配，找“完全匹配”，找不到则选“最接近”的一项
    返回 True/False 表示是否成功设置高亮（便于调试）
    """
    try:
        _ensure_persistent_style_and_group(menu)

        def _persist_select(act):
            # 持久标记：checked
            act.setChecked(True)
            # 让这项以“粗体默认项”呈现（不会随鼠标移动消失）
            menu.setDefaultAction(act)
            # 初始也设为 active，给用户一个起始高亮感（鼠标再动也不丢失持久标记）
            menu.setActiveAction(act)

        # 1) 取得 Axes
        if ax is None:
            if fig is None:
                return False
            axes = fig.get_axes()
            if not axes:
                return False
            ax = axes[0]

        # 2) Auto 情况：直接高亮 'Auto'
        if is_auto:
            for act in menu.actions():
                if act.text().strip().lower() == 'auto':
                    _persist_select(act)
                    return True
            # 没找到 'Auto' 也继续往下做一次数值匹配（容错）

        # 3) 读取当前 Y 轴范围 -> 计算幅度 N
        y_min, y_max = ax.get_ylim()
        # 心率常见在 [0, N]；但稳妥起见仍用 max(|ymin|, |ymax|)
        amp = int(round(max(abs(y_min), abs(y_max))))
        if amp <= 0:
            # 给个兜底，防止完全平坦时没有范围
            amp = 1

        # 4) 菜单文本可能有多种格式：±N / 0~N / 0-N / N
        import re

        def parse_upper_bound(text: str):
            t = text.strip().replace(' ', '')
            # ±N
            m = re.fullmatch(r'±(\d+)', t)
            if m:
                return int(m.group(1))
            # 0~N 或 0-N
            m = re.fullmatch(r'0[~-](\d+)', t)
            if m:
                return int(m.group(1))
            # 纯数字 N
            m = re.fullmatch(r'(\d+)', t)
            if m:
                return int(m.group(1))
            # Auto
            if t.lower() == 'auto':
                return None
            return None

        # 5) 先尝试完全匹配（优先 ±N 其后 0~N / 0-N / N ）
        candidates = []
        exact_texts = {f'±{amp}', f'0~{amp}', f'0-{amp}', f'{amp}'}
        for act in menu.actions():
            txt = act.text().strip()
            if txt in exact_texts:
                _persist_select(act)
                return True
            ub = parse_upper_bound(txt)
            if ub is not None:
                candidates.append((act, ub))

        # 6) 没有完全匹配：选择与 amp 差值最小的
        if candidates:
            best_act, best_diff = None, 10 ** 9
            for act, ub in candidates:
                diff = abs(ub - amp)
                if diff < best_diff:
                    best_act, best_diff = act, diff
            if best_act:
                _persist_select(best_act)
                return True

        return False
    except Exception:
        return False
