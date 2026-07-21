from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QLineEdit, QSpinBox,
                             QListWidget, QListWidgetItem, QScrollArea,
                             QFrame, QSizePolicy, QRadioButton, QButtonGroup,
                             QDoubleSpinBox, QCheckBox, QProgressDialog, QStyledItemDelegate, QStyle,
                             QStyleOptionComboBox, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtProperty, QEvent, QSize, QRectF, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import QFont, QColor, QPainter
import numpy as np
import mne
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
# qEEG 模块导入（在需要时动态导入，避免初始化错误）

from .CustomControls import CustomSlider

plt.rcParams['font.sans-serif'] = ['SimHei']  # 黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号问题

import matplotlib.patches as mpatches
import matplotlib.transforms as mtrans
from matplotlib import font_manager as mfont

# 123132123132313
# 处理相对导入和绝对导入
try:
    from .Control_Style import ControlStyle
    from .Infrastructure.log.QLLogging import QLLogging
except ImportError:
    # 直接运行时使用绝对导入
    import sys
    import os

    # 添加项目路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
from src.Control_Style import ControlStyle
from src.Infrastructure.log.QLLogging import QLLogging


def _get_available_event_label_font_family():
    """优先使用 HarmonyOS Sans SC；不可用时回退到常见中文字体。"""
    try:
        installed_fonts = {f.name for f in mfont.fontManager.ttflist}
        for candidate in [
            'HarmonyOS Sans SC',
            'HarmonyOS Sans SC Regular',
            'Microsoft YaHei',
            'SimHei'
        ]:
            if candidate in installed_fonts:
                return candidate
    except Exception:
        pass
    return 'sans-serif'


def run_analysis_for_params(task_params, subject_age):
    """
    根据任务参数执行算法计算，在「生成报告」时调用。
    会修改并返回 task_params，填充 analysis_result；若为临时 EDF 则在计算后删除。
    """
    import os
    try:
        from qeeg import QEEGAnalyzer
        from qeeg.models import PreprocessingParams
        from qeeg.zscore import ZScoreCalculator
    except ImportError:
        import sys
        current_dir = os.path.dirname(os.path.abspath(__file__))
        qeeg_dir = os.path.join(current_dir, 'qeeg_algorithm-main')
        if qeeg_dir not in sys.path:
            sys.path.insert(0, qeeg_dir)
        from qeeg import QEEGAnalyzer
        from qeeg.models import PreprocessingParams
        from qeeg.zscore import ZScoreCalculator

    method = task_params.get('method')
    temp_edf_path = task_params.get('edf_path')
    is_temp_file = task_params.get('is_temp_file', False)
    start_time = task_params.get('start_time', 0)
    end_time = task_params.get('end_time', 60)
    highpass = task_params.get('highpass')
    lowpass = task_params.get('lowpass')
    notch = task_params.get('notch')

    CHANNELS_21 = [
        'Fp1', 'Fp2', 'C3', 'C4', 'O1', 'O2', 'Cz', 'T3', 'T4',
        'F3', 'F4', 'Fz', 'F7', 'F8', 'Pz', 'P3',
        'T5', 'P4', 'T6', 'Fpz', 'Oz'
    ]

    if not temp_edf_path or not os.path.exists(temp_edf_path):
        return task_params

    def _parse_subject_age(age_value, default_age=30):
        """尽量鲁棒地将年龄解析为5-87范围内的整数。"""
        import re
        try:
            age_text = str(age_value).strip()
            age_num = int(float(age_text))
        except Exception:
            match = re.search(r'(\d+(?:\.\d+)?)', str(age_value))
            if match:
                try:
                    age_num = int(float(match.group(1)))
                except Exception:
                    age_num = default_age
            else:
                age_num = default_age
        return max(5, min(87, age_num))

    # 仅在此处执行算法，确认配置时不执行
    print("[生成报告] 开始执行算法 run_analysis_for_params，分析方法:", method)
    try:
        if method == "Peak Alpha Frequency":
            preprocessing_params = PreprocessingParams()
            if highpass is not None:
                preprocessing_params.lowcut = float(highpass)
            if lowpass is not None:
                preprocessing_params.highcut = float(lowpass)
            if notch is not None:
                preprocessing_params.notch_freq = float(notch)
            analyzer = QEEGAnalyzer(preprocessing_params=preprocessing_params, verbose=False)
            result = analyzer.analyze(
                temp_edf_path,
                time_window=(float(start_time), float(end_time)),
                analyses=['paf'],
                select_channels=['O1', 'O2']
            )
            task_params['analysis_result'] = result
            print("[生成报告] 在此步执行了 analyzer.analyze (PAF)，分析方法: Peak Alpha Frequency")

        elif method == "Power Spectral Density":
            preprocessing_params = PreprocessingParams()
            if highpass is not None:
                preprocessing_params.lowcut = float(highpass)
            if lowpass is not None:
                preprocessing_params.highcut = float(lowpass)
            if notch is not None:
                preprocessing_params.notch_freq = float(notch)
            analyzer = QEEGAnalyzer(preprocessing_params=preprocessing_params, verbose=False)
            result = analyzer.analyze(
                temp_edf_path,
                time_window=(float(start_time), float(end_time)),
                analyses=['psd'],
                select_channels=CHANNELS_21
            )
            task_params['analysis_result'] = result

            psd_raw = {
                "frequencies": result.psd.freqs.tolist(),
                "psd_data": result.psd.psd_relative_array.tolist(),
                "channel_names": result.psd.channel_names,
            }
            task_params['psd_raw_data'] = psd_raw

            print("[生成报告] 在此步执行了 analyzer.analyze (PSD)，分析方法: Power Spectral Density")


        elif method == "Theta/Beta Ratio":
            preprocessing_params = PreprocessingParams()
            if highpass is not None:
                preprocessing_params.lowcut = float(highpass)
            if lowpass is not None:
                preprocessing_params.highcut = float(lowpass)
            if notch is not None:
                preprocessing_params.notch_freq = float(notch)
            analyzer = QEEGAnalyzer(preprocessing_params=preprocessing_params, verbose=False)
            result = analyzer.analyze(
                temp_edf_path,
                time_window=(float(start_time), float(end_time)),
                analyses=['tbr'],
                select_channels=['Fz', 'Cz']
            )
            task_params['analysis_result'] = result
            print("[生成报告] 在此步执行了 analyzer.analyze (TBR)，分析方法: Theta/Beta Ratio")

        elif method == "Z-Score Analysis":
            preprocessing_params = PreprocessingParams()
            if highpass is not None:
                preprocessing_params.lowcut = float(highpass)
            if lowpass is not None:
                preprocessing_params.highcut = float(lowpass)
            if notch is not None:
                preprocessing_params.notch_freq = float(notch)
            analyzer = QEEGAnalyzer(preprocessing_params=preprocessing_params, verbose=False)
            result = analyzer.analyze(
                temp_edf_path,
                time_window=(float(start_time), float(end_time))
            )
            script_dir = os.path.dirname(os.path.abspath(__file__))
            norms_dir = os.path.join(script_dir, "./qeeg_algorithm-main/EEGnorms")
            zscore_calc = ZScoreCalculator(norms_dir=norms_dir)
            age_int = _parse_subject_age(subject_age, default_age=30)
            zscore_result = zscore_calc.calculate(result.psd, age_int)
            task_params['analysis_result'] = zscore_result
            print("[生成报告] 在此步执行了 analyzer.analyze + ZScoreCalculator.calculate，分析方法: Z-Score Analysis")

        elif method == "Full-Band Power Distribution":
            preprocessing_params = PreprocessingParams()
            if highpass is not None:
                preprocessing_params.lowcut = float(highpass)
            if lowpass is not None:
                preprocessing_params.highcut = float(lowpass)
            if notch is not None:
                preprocessing_params.notch_freq = float(notch)
            analyzer = QEEGAnalyzer(preprocessing_params=preprocessing_params, verbose=False)
            result = analyzer.analyze(
                temp_edf_path,
                time_window=(float(start_time), float(end_time)),
                analyses=['psd', 'band_mapping', 'ratio_mapping']
            )
            task_params['analysis_result'] = result
            # 为 Full-Band 页面补充常模分布所需的窄带 Z-Score（2-34Hz, 2Hz步进）
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                norms_dir = os.path.join(script_dir, "./qeeg_algorithm-main/EEGnorms")
                zscore_calc = ZScoreCalculator(norms_dir=norms_dir)
                age_int = _parse_subject_age(subject_age, default_age=30)
                if result is not None and getattr(result, 'psd', None) is not None:
                    zscore_result = zscore_calc.calculate(result.psd, age_int)
                    if zscore_result is not None and getattr(zscore_result, 'narrowband_bands', None) is not None:
                        task_params['fullband_narrowband_zscore'] = zscore_result.narrowband_bands
                else:
                    print("[生成报告] Full-Band 未获得PSD结果，跳过窄带Z-Score计算")
            except Exception as e:
                print(f"[生成报告] Full-Band 计算窄带Z-Score失败: {e}")
            output_dir = os.path.join(os.path.dirname(temp_edf_path), 'qeeg_output')
            os.makedirs(output_dir, exist_ok=True)
            analyzer.save_results(result, output_dir, split_files=True)
            task_params['json_output_dir'] = output_dir
            print(
                "[生成报告] 在此步执行了 analyzer.analyze (band_mapping+ratio_mapping)，分析方法: Full-Band Power Distribution")

        elif method == "Full-Band Ratio Distribution":
            preprocessing_params = PreprocessingParams()
            if highpass is not None:
                preprocessing_params.lowcut = float(highpass)
            if lowpass is not None:
                preprocessing_params.highcut = float(lowpass)
            if notch is not None:
                preprocessing_params.notch_freq = float(notch)
            analyzer = QEEGAnalyzer(preprocessing_params=preprocessing_params, verbose=False)
            # 同时计算 PSD 和 Ratio Mapping，便于后续基于 PSD 计算 Z-Score（包含 z_by_channel）
            result = analyzer.analyze(
                temp_edf_path,
                time_window=(float(start_time), float(end_time)),
                analyses=['psd', 'ratio_mapping']
            )
            task_params['analysis_result'] = result

            # 为 Full-Band Ratio 页面补充功率比率在常模中的分布所需的 z_by_channel
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                norms_dir = os.path.join(script_dir, "./qeeg_algorithm-main/EEGnorms")
                zscore_calc = ZScoreCalculator(norms_dir=norms_dir)
                age_int = _parse_subject_age(subject_age, default_age=30)
                if result is not None and getattr(result, 'psd', None) is not None:
                    zscore_result = zscore_calc.calculate(result.psd, age_int)
                    ratio_part = getattr(zscore_result, 'ratio', None)
                    if ratio_part is not None and isinstance(getattr(ratio_part, 'z_by_channel', None), dict):
                        task_params['ratio_z_by_channel'] = ratio_part.z_by_channel
                        try:
                            QLLogging.log.info(
                                f"[FullBandRatio] ratio_z_by_channel generated, len={len(ratio_part.z_by_channel)}"
                            )
                        except Exception:
                            pass
                else:
                    print("[生成报告] Full-Band Ratio 未获得PSD结果，跳过比率Z-Score计算")
            except Exception as e:
                print(f"[生成报告] Full-Band Ratio 计算比率Z-Score失败: {e}")

            print("[生成报告] 在此步执行了 analyzer.analyze (psd+ratio_mapping)，分析方法: Full-Band Ratio Distribution")

        elif method == "alpha Ratio(EC/EO)":
            preprocessing_params = PreprocessingParams()
            if highpass is not None:
                preprocessing_params.lowcut = float(highpass)
            if lowpass is not None:
                preprocessing_params.highcut = float(lowpass)
            if notch is not None:
                preprocessing_params.notch_freq = float(notch)
            analyzer = QEEGAnalyzer(preprocessing_params=preprocessing_params, verbose=False)
            segment2 = task_params.get('segment2', {})
            seg2_start = float(segment2.get('start_time', 0))
            seg2_end = float(segment2.get('end_time', 60))
            # 兼容两套算法接口：
            # - 旧接口：QEEGAnalyzer.analyze_alpha_ratio(...)
            # - 新接口：仅提供 analyze(...)，需要手动按两段窗口计算 alpha_ratio
            if hasattr(analyzer, 'analyze_alpha_ratio'):
                result = analyzer.analyze_alpha_ratio(
                    temp_edf_path,
                    time_window=(float(start_time), float(end_time)),
                    time_window2=(seg2_start, seg2_end),
                    analyses=['alpha_ratio'],
                    select_channels=['O1', 'O2']
                )
            else:
                from types import SimpleNamespace
                from qeeg.edf_reader import read_edf
                from qeeg.preprocessing import preprocess
                from qeeg.analyzers import analyze_alpha_ratio as _analyze_alpha_ratio

                edf_data = read_edf(temp_edf_path, verbose=False, select_channels=['O1', 'O2'])
                dur = float(getattr(edf_data, 'duration', 0.0) or 0.0)

                s1 = max(0.0, float(start_time))
                e1 = min(dur, float(end_time))
                s2 = max(0.0, float(seg2_start))
                e2 = min(dur, float(seg2_end))

                # 窗口非法时退回到最小安全窗口，避免空切片导致计算失败
                if e1 <= s1:
                    s1, e1 = 0.0, min(dur, max(1.0, dur))
                if e2 <= s2:
                    s2, e2 = s1, e1

                seg1 = edf_data.get_time_segment(s1, e1)
                seg2 = edf_data.get_time_segment(s2, e2)

                p1 = preprocess(seg1, preprocessing_params, verbose=False)
                p2 = preprocess(seg2, preprocessing_params, verbose=False)

                alpha_ratio_res = _analyze_alpha_ratio(
                    p1.data, p2.data, p1.channel_names, p1.sampling_frequency
                )
                result = SimpleNamespace(alpha_ratio=alpha_ratio_res)

            task_params['analysis_result'] = result
            print("[生成报告] 在此步执行了 analyzer.analyze_alpha_ratio，分析方法: alpha Ratio(EC/EO)")
            res = task_params.get('analysis_result')
            if res is not None and hasattr(res, 'alpha_ratio') and getattr(res, 'alpha_ratio', None) is not None:
                ar = res.alpha_ratio
                task_params['alpha_ratio_value'] = float(getattr(ar, 'ratio', 0.0))
                task_params['alpha_ratio_data'] = {
                    'alpha_ratio': float(getattr(ar, 'ratio', 0.0)),
                    'alpha_power_closed': float(getattr(ar, 'alpha_power_closed', 0.0)),
                    'alpha_power_open': float(getattr(ar, 'alpha_power_open', 0.0)),
                }

        elif method == "Frontal Alpha Asymmetry":
            preprocessing_params = PreprocessingParams()
            if highpass is not None:
                preprocessing_params.lowcut = float(highpass)
            if lowpass is not None:
                preprocessing_params.highcut = float(lowpass)
            if notch is not None:
                preprocessing_params.notch_freq = float(notch)
            analyzer = QEEGAnalyzer(preprocessing_params=preprocessing_params, verbose=False)
            result = analyzer.analyze(
                temp_edf_path,
                time_window=(float(start_time), float(end_time)),
                analyses=['faa'],
                select_channels=['F3', 'F4']
            )
            task_params['analysis_result'] = result
            print("[生成报告] 在此步执行了 analyzer.analyze (FAA)，分析方法: Frontal Alpha Asymmetry")
            res = task_params.get('analysis_result')
            if res is not None and hasattr(res, 'faa') and getattr(res, 'faa', None) is not None:
                faa_res = res.faa
                task_params['faa_percentage'] = float(getattr(faa_res, 'faa_percentage', 0.0))
                task_params['faa_data'] = {
                    'faa_percentage': float(getattr(faa_res, 'faa_percentage', 0.0)),
                    'alpha_f3': float(getattr(faa_res, 'alpha_f3', 0.0)),
                    'alpha_f4': float(getattr(faa_res, 'alpha_f4', 0.0)),
                }
        else:
            QLLogging.log.warning(f"run_analysis_for_params: Unknown method: {method}")
    except Exception as e:
        QLLogging.log.exception(f"run_analysis_for_params error: {e}")
    finally:
        if is_temp_file and temp_edf_path and os.path.exists(temp_edf_path):
            try:
                os.remove(temp_edf_path)
                QLLogging.log.info(f"Cleaned up temporary EDF file: {temp_edf_path}")
            except Exception as e:
                QLLogging.log.warning(f"Failed to remove temporary EDF file {temp_edf_path}: {e}")
    return task_params


def get_edf_path_for_report(raw_processed, edf_file_path=None):
    """
    在「生成报告」时根据 raw_processed 或原始路径得到可用的 EDF 路径。
    优先使用原始文件路径；若无则从 raw_processed.filenames 取；再否则导出为临时 EDF。
    返回 (temp_edf_path, is_temp_file)。
    """
    import os
    import tempfile
    temp_edf_path = None
    is_temp_file = False
    if raw_processed is None:
        return None, False
    try:
        if edf_file_path and os.path.exists(edf_file_path):
            return edf_file_path, False
        if hasattr(raw_processed, 'filenames') and raw_processed.filenames:
            original_path = raw_processed.filenames[0]
            if original_path and isinstance(original_path, (str, bytes)) and os.path.exists(
                    original_path) and original_path.lower().endswith(('.edf', '.bdf')):
                return original_path, False
        with tempfile.NamedTemporaryFile(suffix='.edf', delete=False) as temp_file:
            temp_edf_path = temp_file.name
        is_temp_file = True
        raw_to_export = raw_processed.copy()
        raw_to_export._data = raw_to_export.get_data() / 1e6
        try:
            from datetime import datetime
            raw_to_export.set_meas_date(datetime.now())
        except Exception:
            try:
                raw_to_export.set_meas_date(None)
            except Exception:
                pass
        try:
            raw_to_export.export(temp_edf_path, overwrite=True, fmt='edf', physical_range='channelwise')
        except Exception:
            try:
                raw_to_export.export(temp_edf_path, overwrite=True, fmt='edf', physical_range=(-9999999, 9999999))
            except Exception:
                raw_to_export.export(temp_edf_path, overwrite=True, fmt='edf', physical_range=(-1000000, 1000000))
        QLLogging.log.info(f"Exported raw data to temporary EDF for report: {temp_edf_path}")
        return temp_edf_path, is_temp_file
    except Exception as e:
        QLLogging.log.exception(f"get_edf_path_for_report error: {e}")
        if is_temp_file and temp_edf_path and os.path.exists(temp_edf_path):
            try:
                os.remove(temp_edf_path)
            except Exception:
                pass
        return None, False


# 滑动条窗口
class TimeSliderWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI(parent)
        self.setAcceptDrops(True)

    def initUI(self, parent=None):
        self.setStyleSheet("background:#08223C;border-radius: 2px;")
        # 整体为垂直布局
        self.time_slider_widget_vlayout = QVBoxLayout(self)
        self.time_slider_widget_vlayout.setObjectName("time_slider_widget_vlayout")
        self.time_slider_widget_vlayout.setContentsMargins(0, 0, 0, 5)
        self.time_slider_widget_vlayout.setSpacing(0)

        # 水平布局
        label_time_hlayout = QHBoxLayout()
        label_time_hlayout.setContentsMargins(0, 0, 0, 0)
        label_time_hlayout.setSpacing(0)

        self.time_slider = CustomSlider(self)
        self.time_slider.setObjectName("time_slider")
        self.time_slider.setOrientation(Qt.Horizontal)  # 设置为水平方向
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(100)
        self.time_slider.setValue(0)
        self.time_slider.setTotalPages(1)  # 设置总页数为1
        self.time_slider.setStyleSheet(ControlStyle.get_time_slider_style())

        self.time_slider_widget_vlayout.addWidget(self.time_slider)


class SlideSwitch(QCheckBox):
    """带动画的滑块开关（蓝底=开启，灰底=关闭；白色圆点滑动）"""

    def __init__(
            self,
            parent=None,
            *,
            checked: bool = True,
            width: int = 40,
            height: int = 20,
            on_color: QColor = QColor("#007ACC"),
            off_color: QColor = QColor("#CCCCCC"),
            knob_color: QColor = QColor("#FFFFFF"),
            duration_ms: int = 160,
    ):
        super().__init__(parent)
        self.setText("")
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(width, height)

        self._on_color = on_color
        self._off_color = off_color
        self._knob_color = knob_color

        # 先设置初始状态，避免初始化时触发动画
        super().setChecked(bool(checked))
        self._offset = 1.0 if self.isChecked() else 0.0  # 0=左(关) 1=右(开)

        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(int(duration_ms))
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.toggled.connect(self._start_anim)

        # 清掉可能的QSS影响（用paintEvent自绘）
        self.setStyleSheet("QCheckBox{background:transparent; padding:0px; margin:0px;}")

    def setChecked(self, checked: bool):
        """
        兼容外部代码在 blockSignals(True) 时调用 setChecked：
        - Qt 会阻止 toggled/stateChanged 信号，从而不会触发动画回调
        - 这里确保在“信号被阻止”的情况下，视觉状态也会立刻同步
        """
        was_blocked = self.signalsBlocked()
        super().setChecked(bool(checked))
        if was_blocked:
            self._anim.stop()
            self._offset = 1.0 if self.isChecked() else 0.0
            self.update()

    def setCheckState(self, state):
        was_blocked = self.signalsBlocked()
        super().setCheckState(state)
        if was_blocked:
            self._anim.stop()
            self._offset = 1.0 if self.isChecked() else 0.0
            self.update()

    def _start_anim(self, checked: bool):
        self._anim.stop()
        self._anim.setStartValue(float(self._offset))
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def getOffset(self) -> float:
        return float(self._offset)

    def setOffset(self, value: float):
        self._offset = max(0.0, min(1.0, float(value)))
        self.update()

    offset = pyqtProperty(float, fget=getOffset, fset=setOffset)

    @staticmethod
    def _lerp(a: int, b: int, t: float) -> int:
        return int(a + (b - a) * t)

    def _bg_color(self) -> QColor:
        t = float(self._offset)
        return QColor(
            self._lerp(self._off_color.red(), self._on_color.red(), t),
            self._lerp(self._off_color.green(), self._on_color.green(), t),
            self._lerp(self._off_color.blue(), self._on_color.blue(), t),
        )

    def hitButton(self, pos):
        """重写 hitButton 方法，使整个滑动开关区域都可以点击"""
        # 返回 True 表示整个控件区域都可以点击
        return self.rect().contains(pos)

    def paintEvent(self, event):
        w = self.width()
        h = self.height()
        radius = h / 2.0

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)

        # 背景胶囊
        p.setBrush(self._bg_color())
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), radius, radius)

        # 白色圆点（滑块）
        margin = 2.0
        d = h - margin * 2.0
        x = margin + (w - h) * float(self._offset)  # 0=左 1=右
        y = margin
        p.setBrush(self._knob_color)
        p.drawEllipse(QRectF(x, y, d, d))


class CustomSpinBox(QWidget):
    """自定义SpinBox，使用左右箭头按钮（按钮在输入框内部）"""
    valueChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.spinbox = QSpinBox()
        self.spinbox.setButtonSymbols(QSpinBox.NoButtons)  # 隐藏默认按钮
        # spinbox去掉边框，让它看起来像在容器内部，文本居中显示
        self.spinbox.setStyleSheet("""
            QSpinBox {
                border: none;
                background-color: transparent;
                padding: 0px;
                text-align: center;
            }
        """)
        # 设置文本对齐方式为居中
        self.spinbox.setAlignment(Qt.AlignCenter)

        # 创建左右按钮（使用Unicode字符作为箭头）
        self.left_btn = QPushButton("◄")
        self.right_btn = QPushButton("►")

        # 设置按钮固定大小（12px x 12px）
        self.left_btn.setFixedSize(12, 12)
        self.right_btn.setFixedSize(12, 12)

        # 设置按钮样式（只显示箭头，无背景和边框）
        button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 0px;
                color: #000000;
                font-size: 10px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                color: #4169E1;
            }
            QPushButton:pressed {
                color: #2E4FC7;
            }
            QPushButton:disabled {
                color: #CCCCCC;
            }
        """
        self.left_btn.setStyleSheet(button_style)
        self.right_btn.setStyleSheet(button_style)

        # 连接信号
        self.left_btn.clicked.connect(self.decrease)
        self.right_btn.clicked.connect(self.increase)
        self.spinbox.valueChanged.connect(self.valueChanged.emit)

        # 主布局：左按钮 -> spinbox -> 右按钮（都在同一个容器内，self作为边框容器）
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # 无外边距
        layout.setSpacing(4)  # 按钮和输入框之间的间距
        layout.addWidget(self.left_btn, 0, Qt.AlignVCenter)  # 左箭头垂直居中
        layout.addWidget(self.spinbox, 1, Qt.AlignCenter)  # spinbox占据剩余空间并居中
        layout.addWidget(self.right_btn, 0, Qt.AlignVCenter)  # 右箭头垂直居中

    def decrease(self):
        self.spinbox.stepDown()

    def increase(self):
        self.spinbox.stepUp()

    def setMinimum(self, value):
        self.spinbox.setMinimum(value)

    def setMaximum(self, value):
        self.spinbox.setMaximum(value)

    def setValue(self, value):
        self.spinbox.setValue(value)

    def value(self):
        return self.spinbox.value()

    def setSingleStep(self, step):
        self.spinbox.setSingleStep(step)

    def setSuffix(self, suffix):
        self.spinbox.setSuffix(suffix)

    def setEnabled(self, enabled):
        self.spinbox.setEnabled(enabled)
        self.left_btn.setEnabled(enabled)
        self.right_btn.setEnabled(enabled)

    def blockSignals(self, block):
        return self.spinbox.blockSignals(block)

    def setStyleSheet(self, style):
        # 将样式应用到外层widget（self），让边框在外层，按钮和spinbox都在边框内部
        import re
        if 'QSpinBox' in style:
            # 将QSpinBox替换为QWidget，应用到外层容器
            container_style = style.replace('QSpinBox {', 'QWidget {').replace('QSpinBox:', 'QWidget:')
            # 移除所有子控件样式（::up-button, ::down-button, ::up-arrow, ::down-arrow等），因为我们使用自定义按钮
            container_style = re.sub(r'QWidget::[^{]*\{[^}]*\}', '', container_style)
            super().setStyleSheet(container_style)
        elif 'QWidget' in style:
            # 如果样式是QWidget，直接应用
            container_style = re.sub(r'QWidget::[^{]*\{[^}]*\}', '', style)
            super().setStyleSheet(container_style)

        # 从样式中提取字体大小并应用到内部spinbox
        font_size_match = re.search(r'font-size:\s*(\d+(?:\.\d+)?)px', style)
        if font_size_match:
            font_size = font_size_match.group(1)
            self.spinbox.setStyleSheet(f"""
                QSpinBox {{
                    border: none;
                    background-color: transparent;
                    padding: 0px;
                    font-size: {font_size}px;
                    text-align: center;
                }}
            """)
            # 确保文本居中
            self.spinbox.setAlignment(Qt.AlignCenter)


class CustomDoubleSpinBox(QWidget):
    """自定义DoubleSpinBox，使用左右箭头按钮（按钮在输入框内部）"""
    valueChanged = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.spinbox = QDoubleSpinBox()
        self.spinbox.setButtonSymbols(QDoubleSpinBox.NoButtons)  # 隐藏默认按钮
        # spinbox去掉边框，让它看起来像在容器内部，文本居中显示
        self.spinbox.setStyleSheet("""
            QDoubleSpinBox {
                border: none;
                background-color: transparent;
                padding: 0px;
                text-align: center;
            }
        """)
        # 设置文本对齐方式为居中
        self.spinbox.setAlignment(Qt.AlignCenter)

        # 创建左右按钮（使用Unicode字符作为箭头）
        self.left_btn = QPushButton("◄")
        self.right_btn = QPushButton("►")

        # 设置按钮固定大小（12px x 12px）
        self.left_btn.setFixedSize(12, 12)
        self.right_btn.setFixedSize(12, 12)

        # 设置按钮样式（只显示箭头，无背景和边框）
        button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 0px;
                color: #000000;
                font-size: 10px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                color: #4169E1;
            }
            QPushButton:pressed {
                color: #2E4FC7;
            }
            QPushButton:disabled {
                color: #CCCCCC;
            }
        """
        self.left_btn.setStyleSheet(button_style)
        self.right_btn.setStyleSheet(button_style)

        # 连接信号
        self.left_btn.clicked.connect(self.decrease)
        self.right_btn.clicked.connect(self.increase)
        self.spinbox.valueChanged.connect(self.valueChanged.emit)

        # 主布局：左按钮 -> spinbox -> 右按钮（都在同一个容器内，self作为边框容器）
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # 无外边距
        layout.setSpacing(4)  # 按钮和输入框之间的间距
        layout.addWidget(self.left_btn, 0, Qt.AlignVCenter)  # 左箭头垂直居中
        layout.addWidget(self.spinbox, 1, Qt.AlignCenter)  # spinbox占据剩余空间并居中
        layout.addWidget(self.right_btn, 0, Qt.AlignVCenter)  # 右箭头垂直居中

    def decrease(self):
        self.spinbox.stepDown()

    def increase(self):
        self.spinbox.stepUp()

    def setMinimum(self, value):
        self.spinbox.setMinimum(value)

    def setMaximum(self, value):
        self.spinbox.setMaximum(value)

    def setValue(self, value):
        self.spinbox.setValue(value)

    def value(self):
        return self.spinbox.value()

    def setSingleStep(self, step):
        self.spinbox.setSingleStep(step)

    def setDecimals(self, decimals):
        self.spinbox.setDecimals(decimals)

    def setSuffix(self, suffix):
        self.spinbox.setSuffix(suffix)

    def setEnabled(self, enabled):
        self.spinbox.setEnabled(enabled)
        self.left_btn.setEnabled(enabled)
        self.right_btn.setEnabled(enabled)

    def setStyleSheet(self, style):
        # 将样式应用到外层widget（self），让边框在外层，按钮和spinbox都在边框内部
        import re
        if 'QDoubleSpinBox' in style:
            # 将QDoubleSpinBox替换为QWidget，应用到外层容器
            container_style = style.replace('QDoubleSpinBox {', 'QWidget {').replace('QDoubleSpinBox:', 'QWidget:')
            # 移除所有子控件样式（::up-button, ::down-button, ::up-arrow, ::down-arrow等），因为我们使用自定义按钮
            container_style = re.sub(r'QWidget::[^{]*\{[^}]*\}', '', container_style)
            super().setStyleSheet(container_style)
        elif 'QWidget' in style:
            # 如果样式是QWidget，直接应用
            container_style = re.sub(r'QWidget::[^{]*\{[^}]*\}', '', style)
            super().setStyleSheet(container_style)

        # 从样式中提取字体大小并应用到内部spinbox
        font_size_match = re.search(r'font-size:\s*(\d+(?:\.\d+)?)px', style)
        if font_size_match:
            font_size = font_size_match.group(1)
            self.spinbox.setStyleSheet(f"""
                QDoubleSpinBox {{
                    border: none;
                    background-color: transparent;
                    padding: 0px;
                    font-size: {font_size}px;
                    text-align: center;
                }}
            """)
            # 确保文本居中
            self.spinbox.setAlignment(Qt.AlignCenter)


class DraggableRectangle(Rectangle):
    """可拖动和调整大小的矩形，用于分析窗口"""

    def __init__(self, xy, width, height, task_analysis_instance, is_segment2=False, axes=None, **kwargs):
        super().__init__(xy, width, height, **kwargs)
        self.axes = axes  # 保存关联的坐标轴对象
        self.figure = self.axes.figure  # 从Axes获取所属Figure，赋值给self.figure
        self.axes.add_patch(self)  # 将矩形添加到Axes，完成Artist与Axes的绑定

        self.task_analysis = task_analysis_instance
        self.press = None
        self.background = None
        self.resize_mode = None  # 'left', 'right', 'move', None
        self.edge_threshold = 5  # 边缘检测阈值（秒）
        self.is_segment2 = is_segment2  # 是否为分段2的矩形
        self._is_connected = False  # 防止重复绑定 canvas 事件

    def connect(self):
        """连接鼠标事件"""
        if self._is_connected:
            # 幂等处理：避免重复连接导致旧事件残留
            self.disconnect()
        self.cidpress = self.figure.canvas.mpl_connect('button_press_event', self.on_press)
        self.cidrelease = self.figure.canvas.mpl_connect('button_release_event', self.on_release)
        self.cidmotion = self.figure.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self._is_connected = True

    def disconnect(self):
        """断开鼠标事件（确保所有事件都断开）"""
        if hasattr(self, 'cidpress') and self.figure is not None:
            self.figure.canvas.mpl_disconnect(self.cidpress)
            delattr(self, 'cidpress')
        if hasattr(self, 'cidrelease') and self.figure is not None:
            self.figure.canvas.mpl_disconnect(self.cidrelease)
            delattr(self, 'cidrelease')
        if hasattr(self, 'cidmotion') and self.figure is not None:
            self.figure.canvas.mpl_disconnect(self.cidmotion)
            delattr(self, 'cidmotion')
        self._is_connected = False

    def _detect_resize_mode(self, event):
        """检测鼠标是否在边缘，决定是调整大小还是拖动"""
        if event.inaxes != self.axes or event.xdata is None:
            return None

        x0, y0 = self.xy
        width = self.get_width()
        x_left = x0
        x_right = x0 + width

        # 检查是否在左边缘
        if abs(event.xdata - x_left) < self.edge_threshold:
            return 'left'
        # 检查是否在右边缘
        elif abs(event.xdata - x_right) < self.edge_threshold:
            return 'right'
        # 检查是否在矩形内
        elif x_left <= event.xdata <= x_right:
            return 'move'
        return None

    def on_press(self, event):
        """鼠标按下事件"""
        # 新增：空值防护
        if self.figure is None or self.axes is None:
            return
        if event.inaxes != self.axes:
            return

        # 检测操作模式
        self.resize_mode = self._detect_resize_mode(event)
        if self.resize_mode is None:
            return

        # 记录按下位置和当前矩形状态
        x0, y0 = self.xy
        width = self.get_width()
        self.press = x0, width, event.xdata, event.ydata

    def on_motion(self, event):
        """鼠标移动事件（拖动或调整大小）"""
        # 新增：空值防护（核心修复）
        if self.figure is None or self.axes is None:
            return
        # 如果不在拖动状态，更新光标样式
        if self.press is None:
            resize_mode = self._detect_resize_mode(event)
            if resize_mode == 'left' or resize_mode == 'right':
                self.figure.canvas.setCursor(Qt.SizeHorCursor)
            elif resize_mode == 'move':
                self.figure.canvas.setCursor(Qt.SizeAllCursor)
            else:
                self.figure.canvas.setCursor(Qt.ArrowCursor)
            return

        # 拖动或调整大小
        if self.resize_mode is None:
            return
        if event.inaxes != self.axes:
            return
        if event.xdata is None:
            return

        x0, width0, xpress, ypress = self.press
        dx = event.xdata - xpress

        if self.resize_mode == 'move':
            # 拖动模式：移动整个矩形
            new_x = x0 + dx

            # 限制拖动范围：不能超出数据范围（使用实际数据长度）
            min_x = 0
            max_duration = self.task_analysis.total_duration if self.task_analysis.total_duration > 0 else 600
            max_x = max_duration - self.get_width()

            # 确保不超出边界
            if new_x < min_x:
                new_x = min_x
            elif new_x > max_x:
                new_x = max_x

            # 更新矩形位置
            self.set_x(new_x)

            # 更新分析窗口参数（根据是否是分段2）
            if self.is_segment2:
                self.task_analysis.segment2_start_time = new_x
                self.task_analysis.segment2_duration = self.get_width()
                self.task_analysis.segment2_end_time = new_x + self.get_width()
            else:
                self.task_analysis.analysis_start_time = new_x
                self.task_analysis.analysis_duration = self.get_width()
                self.task_analysis.analysis_end_time = new_x + self.get_width()

        elif self.resize_mode == 'left':
            # 调整左边缘：改变开始位置和宽度
            new_x = x0 + dx
            new_width = width0 - dx

            # 限制范围
            min_x = 0
            min_width = 1  # 最小宽度1秒

            if new_x < min_x:
                new_x = min_x
                new_width = x0 + width0 - min_x

            if new_width < min_width:
                new_width = min_width
                new_x = x0 + width0 - min_width

            # 确保结束时间不超过实际数据长度
            max_duration = self.task_analysis.total_duration if self.task_analysis.total_duration > 0 else 600
            if new_x + new_width > max_duration:
                new_width = max_duration - new_x
                if new_width < min_width:
                    new_width = min_width
                    new_x = max_duration - min_width

            # 更新矩形
            self.set_x(new_x)
            self.set_width(new_width)

            # 更新分析窗口参数（根据是否是分段2）
            if self.is_segment2:
                self.task_analysis.segment2_start_time = new_x
                self.task_analysis.segment2_duration = new_width
                self.task_analysis.segment2_end_time = new_x + new_width
            else:
                self.task_analysis.analysis_start_time = new_x
                self.task_analysis.analysis_duration = new_width
                self.task_analysis.analysis_end_time = new_x + new_width

        elif self.resize_mode == 'right':
            # 调整右边缘：只改变宽度
            new_width = width0 + dx

            # 限制范围（使用实际数据长度）
            min_width = 1  # 最小宽度1秒
            max_duration = self.task_analysis.total_duration if self.task_analysis.total_duration > 0 else 600
            max_width = max_duration - x0  # 最大宽度不能超过实际数据长度

            if new_width < min_width:
                new_width = min_width
            elif new_width > max_width:
                new_width = max_width

            # 更新矩形宽度
            self.set_width(new_width)

            # 更新分析窗口参数（根据是否是分段2）
            if self.is_segment2:
                self.task_analysis.segment2_start_time = x0
                self.task_analysis.segment2_duration = new_width
                self.task_analysis.segment2_end_time = x0 + new_width
            else:
                self.task_analysis.analysis_start_time = x0
                self.task_analysis.analysis_duration = new_width
                self.task_analysis.analysis_end_time = x0 + new_width

        # 获取当前操作的开始时间、结束时间和时长
        if self.is_segment2:
            current_start = int(self.task_analysis.segment2_start_time)
            current_end = int(self.task_analysis.segment2_end_time)
            current_duration = int(self.task_analysis.segment2_duration)
        else:
            current_start = int(self.task_analysis.analysis_start_time)
            current_end = int(self.task_analysis.analysis_end_time)
            current_duration = int(self.task_analysis.analysis_duration)

        # 通过拖动/缩放分析窗口矩形手动修改时间时，当前分段不再与事件时间严格对齐，取消事件绑定与高亮
        if hasattr(self.task_analysis, '_clear_event_binding_for_current_segment'):
            self.task_analysis._clear_event_binding_for_current_segment()

        # 更新 start_spinbox（开始时间）和 duration_spinbox（持续时间）
        if hasattr(self.task_analysis, 'start_spinbox'):
            self.task_analysis.start_spinbox.blockSignals(True)
            self.task_analysis.start_spinbox.setValue(current_start)
            self.task_analysis.start_spinbox.blockSignals(False)

        if hasattr(self.task_analysis, 'duration_spinbox'):
            self.task_analysis.duration_spinbox.blockSignals(True)
            self.task_analysis.duration_spinbox.setValue(current_duration)
            self.task_analysis.duration_spinbox.blockSignals(False)

        if hasattr(self.task_analysis, 'end_spinbox'):
            self.task_analysis.end_spinbox.blockSignals(True)
            self.task_analysis.end_spinbox.setValue(current_end)
            self.task_analysis.end_spinbox.blockSignals(False)

        # 更新selection_label（如果存在）
        if hasattr(self.task_analysis, 'selection_label'):
            self.task_analysis.selection_label.setText(f"Selection: {current_duration} Sec")

        # 更新隐藏的时间标签（兼容性）
        self.task_analysis.update_time_labels()

        # 只重绘当前画布，不重新绘制整个图形
        self.figure.canvas.draw_idle()

    def on_release(self, event):
        """鼠标释放事件"""
        # 新增：空值防护
        if self.figure is not None:
            self.figure.canvas.setCursor(Qt.ArrowCursor)  # 恢复默认光标
        self.press = None
        self.resize_mode = None
        # 只在figure非空时重绘
        if self.figure is not None:
            self.figure.canvas.draw()


class TwoLineComboDelegate(QStyledItemDelegate):
    """下拉项两行显示：中文一行、英文一行（同一方法占两行）"""

    def sizeHint(self, option, index):
        text = index.data(Qt.DisplayRole) or ""
        lines = (text or "").split("\n")
        fm = option.fontMetrics
        line_height = fm.height()
        padding = 8
        height = max(1, len(lines)) * line_height + padding
        return QSize(option.rect.width(), height)

    def paint(self, painter, option, index):
        painter.save()
        text = index.data(Qt.DisplayRole) or ""
        lines = (text or "").split("\n")
        if not lines:
            painter.restore()
            return
        opt = option
        if opt.state & QStyle.State_Selected:
            painter.fillRect(opt.rect, opt.palette.highlight())
            painter.setPen(opt.palette.highlightedText().color())
        else:
            painter.setPen(opt.palette.text().color())
        fm = opt.fontMetrics
        line_height = fm.height()
        y = opt.rect.y() + fm.ascent() + 4
        for line in lines:
            painter.drawText(opt.rect.x() + 8, y, line.strip())
            y += line_height
        painter.restore()


class TwoLineComboBox(QComboBox):
    """收起时也在文字框内两行显示当前选中项（中文一行、英文一行）"""

    def mousePressEvent(self, event):
        """点击整个文本框任意位置都能触发下拉展开/收起"""
        if event.button() == Qt.LeftButton:
            if self.view().isVisible():
                self.hidePopup()
            else:
                self.showPopup()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        edit_rect = self.style().subControlRect(
            QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxEditField, self)
        if not edit_rect.isValid():
            return
        text = self.currentText()
        if not text:
            return
        lines = [s.strip() for s in text.split("\n") if s.strip()]
        if not lines:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        fm = self.fontMetrics()
        line_height = fm.height()

        # 计算总文本高度
        total_text_height = len(lines) * line_height
        # 计算垂直居中的起始y坐标
        # edit_rect 的中心y坐标
        rect_center_y = edit_rect.y() + edit_rect.height() / 2
        # 文本块的顶部应该在中心上方 total_text_height / 2 的位置
        # 第一行的基线位置 = 文本块顶部 + ascent
        first_line_baseline = rect_center_y - total_text_height / 2 + fm.ascent()

        # 绘制每一行
        for i, line in enumerate(lines):
            # 每行的基线y坐标
            line_baseline_y = first_line_baseline + i * line_height
            if i == 0:
                # 第一行：正常颜色（使用样式表中定义的颜色）
                normal_color = QColor(50, 50, 50)  # #323232，与样式表一致
                painter.setPen(normal_color)
            else:
                # 第二行及以后：灰色
                gray_color = QColor(153, 153, 153)  # #999999
                painter.setPen(gray_color)
            painter.drawText(edit_rect.x() + 8, int(line_baseline_y), line)
        painter.end()


class task_Analysis(QWidget):
    """任务分析界面 - 信号滤波和分析窗口配置"""

    # 定义统一的信号：用于传输任务配置数据
    task_confirmed_signal = pyqtSignal(dict)  # 发送包含所有当前页面设置的数据字典

    err_msg_signal = pyqtSignal(str)

    def __init__(self, task_config=None, subject_age=None, parent=None, skip_plotting=False):
        """
        初始化任务分析界面
        
        参数:
            task_config (dict): 任务配置字典，包含以下键：
                - task_id: 任务ID
                - task_name: 任务名称
                - analysis_method: 分析方法
                - start_time: 起始时间（秒）
                - end_time: 结束时间（秒）
                - highpass: High-pass滤波频率（Hz）
                - lowpass: Low-pass滤波频率（Hz）
                - raw_processed: MNE Raw对象（EDF文件数据）
            parent: 父窗口
            skip_plotting: 是否跳过绘图操作（用于模板加载等场景）
        """
        self.skip_plotting = skip_plotting
        self.inside_axes = []  # 存储所有内嵌子图inside_ax，用于滚动联动
        self.visible_window = 600
        self.subject_age = subject_age

        try:
            super().__init__(parent)
            # 设置主页面容器标识，用于设置背景颜色
            self.setObjectName("task_analysis_main")

            # 验证并提取配置参数
            if task_config is None:
                task_config = {}
            else:
                task_config = task_config.to_dict()
                print(task_config["id"], task_config["name"])
            # 从字典中提取参数，如果不存在则使用默认值
            self.task_id = task_config.get('id', '')
            # 已点击「确认配置」的任务 id 集合，切换任务时用于保持按钮状态
            self._configured_task_ids = set()
            self.task_name = task_config.get('name', '新任务')
            self.analysis_method = task_config.get('analysis_method', 'Peak Alpha Frequency')
            self.analysis_start_time = int(
                float(task_config.get('start_time') if task_config.get('start_time') is not None else 0))
            self.analysis_end_time = int(
                float(task_config.get('end_time') if task_config.get('end_time') is not None else 120))
            hp_raw = task_config.get('high_pass')
            lp_raw = task_config.get('low_pass')
            notch_raw = task_config.get('notch')
            # “数值”永远保留给 UI；缺失时使用默认值
            self.highpass_value = float(hp_raw) if hp_raw is not None else 1.0
            self.lowpass_value = float(lp_raw) if lp_raw is not None else 35.0
            self.notch_value = float(notch_raw) if notch_raw is not None else 50.0

            # 是否启用：优先用显式字段；否则兼容旧数据（值为 None 视为禁用）
            hp_enabled_raw = task_config.get('high_pass_enabled')
            lp_enabled_raw = task_config.get('low_pass_enabled')
            notch_enabled_raw = task_config.get('notch_enabled')
            self.highpass_enabled = bool(int(hp_enabled_raw)) if hp_enabled_raw is not None else (hp_raw is not None)
            self.lowpass_enabled = bool(int(lp_enabled_raw)) if lp_enabled_raw is not None else (lp_raw is not None)
            # notch 若旧数据缺失（notch_raw is None）默认启用；若显式为 None 则禁用
            self.notch_enabled = bool(int(notch_enabled_raw)) if notch_enabled_raw is not None else True
            if notch_enabled_raw is None and notch_raw is None and 'notch' in task_config:
                self.notch_enabled = False

            # effective（用于滤波）：禁用 -> None
            self.highpass = self.highpass_value if self.highpass_enabled else None
            self.lowpass = self.lowpass_value if self.lowpass_enabled else None
            self.notch = self.notch_value if self.notch_enabled else None
            # raw_processed 在对象创建时初始化为 None，不依赖外界传入
            self.raw_processed = None  # MNE Raw对象，将在导入数据时设置

            # 计算分析窗口时长
            self.analysis_duration = self.analysis_end_time - self.analysis_start_time
            if self.analysis_duration <= 0:
                QLLogging.log.warning(f"Invalid duration: {self.analysis_duration}s, using default 120s")
                self.analysis_duration = 120
                self.analysis_end_time = self.analysis_start_time + self.analysis_duration

            # 数据相关属性
            self.raw_filtered = None  # 滤波后的数据
            self.channel_names = []  # 通道名称列表
            self.sfreq = None  # 采样率
            self.total_duration = 0  # 总时长（秒）
            self.is_init = True # 该变量用于判断是否是一次载入变量
            # 事件锚点列表
            self.events = []
            # alpha Ratio(EC/EO) 下分子/分母各自记忆事件选择
            self._selected_event_name_by_segment = {1: None, 2: None}
            # 控制是否在事件选中时跳过时间更新（用于仅恢复高亮而不改时间）
            self._suppress_time_update_on_event_select = False

            # 可拖动矩形引用（用于断开事件连接）
            self.analysis_rect = None
            # 波形图「点击设起点、拖动设持续时间」交互状态
            self._define_window_press_x = None
            self._main_waveform_ax = None
            self._cid_define_press = self._cid_define_motion = self._cid_define_release = None

            # alpha Ratio(EC/EO) 分析方法的分段2参数
            self.segment2_start_time = int(
                float(task_config.get('start_time_') if task_config.get('start_time_') is not None else 0))
            self.segment2_end_time = int(
                float(task_config.get('end_time_') if task_config.get('end_time_') is not None else 60))
            self.segment2_duration = self.segment2_end_time - self.segment2_start_time  # 分段2时长（秒）
            self.segment2_rect = None  # 分段2的红色矩形
            saved_segment = task_config.get('current_segment')
            self.current_segment = int(saved_segment) if saved_segment in (1, 2, '1', '2') else 1  # 当前选中的分段 (1 或 2)
            self._canvas_resize_fixup_count = 0

            # Quick Bandpass 模式、X/Y 缩放初始值（与滤波器一样从 task_config 读取，用于回显）
            self.bandpass_mode = task_config.get('bandpass_mode')
            self.x_axis_scale = task_config.get('x_axis_scale')
            self.y_axis_scale = task_config.get('y_axis_scale')

            # 初始化UI
            QLLogging.log.info(f"Initializing Task Analysis UI 冯1for task: {self.task_name} (ID: {self.task_id})")
            self.init_ui()

            # 自动从 Data_Info 获取 raw_processed 数据（参考 Data_Info.py 的数据加载方式）
            self._auto_load_raw_data()

            # 如果获取到了 raw_processed，自动导入数据
            if self.raw_processed is not None:
                self.import_raw(self.raw_processed)

            QLLogging.log.info("Task Analysis UI initialized successfully")



        except Exception as e:
            QLLogging.log.exception(f"Error initializing Task Analysis: {e}")
            import traceback
            QLLogging.log.error(f"Init error traceback: {traceback.format_exc()}")
            # 即使初始化失败，也要确保对象可以创建，避免闪退
            raise  # 重新抛出异常，让调用者知道初始化失败

    def _auto_load_raw_data(self):
        """
        自动从 Data_Info 获取 raw_processed 数据
        这个方法可以被 __init__ 和 update_config 调用
        """
        if self.raw_processed is not None:
            QLLogging.log.debug("raw_processed already loaded, skipping auto-load")
            return

        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                QLLogging.log.warning("QApplication instance not found, cannot auto-load data")
                return

            # 尝试多种方式找到主窗口
            main_window = None

            # 方法1: 通过 activeWindow 获取
            main_window = app.activeWindow()

            print("mainwindow",main_window)

            # 方法2: 如果 activeWindow 为空，从所有顶层窗口中找到主窗口
            if main_window is None or not hasattr(main_window, 'ui_main'):
                QLLogging.log.debug("activeWindow not found or invalid, searching all top-level widgets")
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'ui_main'):
                        # 检查是否有 raw_processed 属性
                        if hasattr(widget.ui_main, 'raw_processed'):
                            main_window = widget
                            QLLogging.log.debug(f"Found main window: {type(main_window).__name__}")
                            break

            if main_window is None or not hasattr(main_window, 'ui'):
                QLLogging.log.debug("activeWindow not found or invalid, searching all top-level widgets")
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'ui'):
                        # 检查是否有 raw_processed 属性
                        if hasattr(widget.ui, 'raw_processed'):
                            main_window = widget
                            QLLogging.log.debug(f"Found main window: {type(main_window).__name__}")
                            break

            # 方法3: 尝试通过 parent 链向上查找
            if main_window is None and self.parent() is not None:
                QLLogging.log.debug("Trying to find main window through parent chain")
                parent = self.parent()
                max_depth = 10  # 防止无限循环
                depth = 0
                while parent is not None and depth < max_depth:
                    if hasattr(parent, 'ui_main') and hasattr(parent.ui_main, 'raw_processed'):
                        main_window = parent
                        QLLogging.log.debug(f"Found main window through parent chain: {type(main_window).__name__}")
                        break
                    parent = parent.parent()
                    depth += 1

            if main_window is None and self.parent() is not None:
                QLLogging.log.debug("Trying to find main window through parent chain")
                parent = self.parent()
                max_depth = 10  # 防止无限循环
                depth = 0
                while parent is not None and depth < max_depth:
                    if hasattr(parent, 'ui') and hasattr(parent.ui, 'raw_processed'):
                        main_window = parent
                        QLLogging.log.debug(f"Found main window through parent chain: {type(main_window).__name__}")
                        break
                    parent = parent.parent()
                    depth += 1

            # 获取数据
            if main_window is not None and hasattr(main_window, 'ui_main'):
                data_info = main_window.ui_main
                if hasattr(data_info, 'raw_processed') and data_info.raw_processed is not None:
                    self.raw_processed = data_info.raw_processed
                    QLLogging.log.info("Auto-loaded raw_processed from Data_Info")
                    return

            if main_window is not None and hasattr(main_window, 'ui'):
                qeeg_info = main_window.ui
                if hasattr(qeeg_info, 'raw_processed') and qeeg_info.raw_processed is not None:
                    self.raw_processed = qeeg_info.raw_processed
                    QLLogging.log.info("Auto-loaded raw_processed from qeeg_info")
                    return

            QLLogging.log.warning("Could not find main window with raw_processed data")

        except Exception as e:
            QLLogging.log.exception(f"Failed to auto-load raw_processed from Data_Info: {e}")
            import traceback
            QLLogging.log.debug(f"Auto-load error traceback: {traceback.format_exc()}")

    def init_ui(self):
        """初始化UI界面"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧配置面板
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, stretch=0)

        # 右侧面板（包含SIGNAL FILTERING和波形显示）
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, stretch=1)

        self.setStyleSheet(ControlStyle.get_widget_style())

        # 设置整个页面的背景颜色（只影响主容器，不影响子控件）
        self.setStyleSheet(self.styleSheet() + """
            QWidget#task_analysis_main {
                background-color: #F6F9FF;
            }
        """)

        # 确保按钮创建后重置到初始状态
        if hasattr(self, 'confirm_button'):
            self.reset_confirm_button()

    def get_current_analysis_method(self):
        """返回当前选中的分析方法内部键（用于逻辑判断），与下拉显示的中英文无关。"""
        data = self.method_combo.currentData(Qt.UserRole)
        return data if data is not None else self.method_combo.currentText()

    def create_left_panel(self):
        """创建左侧配置面板"""
        left_widget = QWidget()
        left_widget.setFixedWidth(350)
        left_widget.setStyleSheet("""
            QWidget {
                /* 大页面底色：跟随主背景 */
                background-color: #F6F9FF;
            }
        """)

        layout = QVBoxLayout(left_widget)
        layout.setContentsMargins(15, 25, 15, 25)  # 左右边距减小以适应250px宽度
        layout.setSpacing(20)

        # 任务命名 + 分析方式（用卡片容器包裹：圆角矩形）
        task_method_card = QWidget()
        task_method_card.setAttribute(Qt.WA_StyledBackground, True)
        task_method_card.setObjectName("task_method_card")
        task_method_card.setStyleSheet("""
            QWidget#task_method_card {
                background-color: #FFFFFF;
                border-radius: 12px;
            }
        """)
        task_method_layout = QVBoxLayout(task_method_card)
        task_method_layout.setContentsMargins(12, 12, 12, 12)
        task_method_layout.setSpacing(10)

        # 标题：方法配置（放在组件内部）
        config_title = QLabel("方法配置")
        config_title.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        config_title.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-weight: 500;
                font-size: 14px;
                color: #000000;
                background-color: white;
                padding-bottom: 10px;
                letter-spacing: 1px;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        task_method_layout.addWidget(config_title)

        # 1. 任务命名
        task_label = QLabel("任务命名")
        task_label.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-weight: 500;
                font-size: 14px;
                color: #979797;
                margin-top: 0px;
                background-color: white;
                padding: 4px 8px;
                border-radius: 6px;
            }
        """)
        task_method_layout.addWidget(task_label)

        self.task_name_input = QLineEdit()
        self.task_name_input.setText(self.task_name)  # 使用从配置中获取的任务名称
        # 任务名称：上限 100 个字符，不支持换行
        self.task_name_input.setMaxLength(100)
        self.task_name_input.textChanged.connect(self._sanitize_task_name_input)
        # 彻底关闭控件自带边框（避免样式残留边线）
        self.task_name_input.setFrame(False)
        self.task_name_input.setStyleSheet("""
            QLineEdit {
                font-family: Microsoft YaHei;
                border: 1px solid rgba(141, 161, 193, 102);
                outline: none;
                border-radius: 8px;
                padding: 10px 12px;
                background-color: white;
                font-size: 10pt;
                selection-background-color: #007ACC;
            }
            QLineEdit:focus {
                border: 1px solid rgba(141, 161, 193, 102);
                outline: none;
                background-color: white;
            }
            QLineEdit:hover {
                border: 1px solid rgba(141, 161, 193, 102);
                outline: none;
                background-color: white;
            }
        """)
        task_method_layout.addWidget(self.task_name_input)

        # 2. 分析方法
        method_label = QLabel("分析方法")
        method_label.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-weight: 500;
                font-size: 14px;
                color: #979797;
                margin-top: 0px;
                background-color: white;
                padding: 4px 8px;
                border-radius: 6px;
            }
        """)
        task_method_layout.addWidget(method_label)

        # 下拉显示：中英文两行（中文一行、英文一行，同一方法占两行）；内部方法键用 setItemData 存储
        METHOD_DISPLAY = [
            ("α波峰值频率\nPeak Alpha Frequency (PAF)", "Peak Alpha Frequency"),
            ("功率谱密度\nPower Spectral Density (PSD)", "Power Spectral Density"),
            ("θ/β 比值 (Theta/Beta 比率)\nTheta/Beta Ratio (TBR)", "Theta/Beta Ratio"),
            ("Z分数分析 (标准化评分分析)\nZ-Score Analysis", "Z-Score Analysis"),
            ("全频段功率分布\nFull-Band Power Distribution", "Full-Band Power Distribution"),
            ("全频段比率分布\nFull-Band Ratio Distribution", "Full-Band Ratio Distribution"),
            ("Alpha 抑制指数\nAlpha Ratio (EC/EO)", "alpha Ratio(EC/EO)"),
            ("前额 Alpha 不对称性\nFrontal Alpha Asymmetry (FAA)", "Frontal Alpha Asymmetry"),
            # 报告输出验收：仅用于控制是否在生成报告中显示“报告输出验收/综合评估”页面，本身不触发算法计算
            ("报告总结编辑区\nReport Output", "Report Output"),
        ]
        self.method_combo = TwoLineComboBox()
        for display_text, method_key in METHOD_DISPLAY:
            self.method_combo.addItem(display_text, method_key)
            '''
            if method_key == "Z-Score Analysis" and int(self.subject_age[:-1]) < 5 or int(self.subject_age[:-1]) > 87:
                # 创建一个禁用状态的项
                self.method_combo.addItem(display_text, method_key)
                # 获取最后添加的项的索引
                last_idx = self.method_combo.count() - 1
                # 获取该项的模型项并设置为禁用
                model = self.method_combo.model()
                item = model.item(last_idx)
                item.setEnabled(False)
                # 设置前景色为灰色
                item.setData(QColor(128, 128, 128), Qt.ForegroundRole)
                # 设置背景色为灰色
                item.setData(QColor(220, 220, 220), Qt.BackgroundRole)
            else:
                self.method_combo.addItem(display_text, method_key)
            '''

        # 下拉列表两行显示：对弹出列表的 view 设置 Delegate，并允许非统一行高
        popup_view = self.method_combo.view()
        popup_view.setItemDelegate(TwoLineComboDelegate(self.method_combo))
        popup_view.setUniformItemSizes(False)  # 允许每项高度不同，才能用 delegate 的 sizeHint
        # 按内部方法键选中当前项（兼容从配置加载）
        idx = self.method_combo.findData(self.analysis_method, Qt.UserRole)
        if idx >= 0:
            self.method_combo.setCurrentIndex(idx)
        else:
            self.method_combo.setCurrentIndex(0)
        # 高度略增以便选中时能显示两行
        self.method_combo.setMinimumHeight(50)
        self.method_combo.setFixedHeight(50)
        self.method_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # 彻底关闭控件自带边框（避免样式残留边线）
        self.method_combo.setFrame(False)
        # 让显示文本可左对齐（非editable时alignment不稳定，改为只读lineEdit承载显示）
        self.method_combo.setEditable(True)
        if self.method_combo.lineEdit() is not None:
            self.method_combo.lineEdit().setReadOnly(True)
            self.method_combo.lineEdit().setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.method_combo.lineEdit().setCursor(Qt.ArrowCursor)
            # 隐藏 lineEdit，由 TwoLineComboBox.paintEvent 在内容区绘制两行文字
            self.method_combo.lineEdit().setVisible(False)
            # 优化交互：点击“文字区域”也能展开下拉（不必点右侧箭头）
            self.method_combo.lineEdit().installEventFilter(self)
        self.method_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid rgba(141, 161, 193, 102);
                outline: none;
                border-radius: 4px;
                padding: 0px 8px;
                background-color: white;
                font-family: Microsoft YaHei;
                font-weight: 400;
                font-size: 14px;
                color: #323232;
                font-style: normal;
            }
            QComboBox QLineEdit {
                border: none;
                background: transparent;
                padding: 0;
                margin: 0;
                text-align: left;
            }
            QComboBox:hover {
                border: 1px solid rgba(141, 161, 193, 102);
                outline: none;
                background-color: white;
            }
            QComboBox:focus {
                border: 1px solid rgba(141, 161, 193, 102);
                outline: none;
                background-color: white;
            }
            QComboBox::drop-down {
                border: 0px solid transparent;
                background: transparent;
                width: 16px;
            }
            QComboBox::down-arrow {
                image: url(./resource/picture/arrowhead.png);
                width: 16px;
                height: 16px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid rgba(141, 161, 193, 102);
                border-radius: 2px;
                background-color: white;
                selection-background-color: #E3F2FD;
                selection-color: #323232;
                color: #323232;
                padding: 4px;
                text-align: left;
            }
            QComboBox QAbstractItemView::item {
                color: #323232;
                padding: 4px 8px;
                background-color: transparent;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #E8F4FD;
                color: #323232;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #E3F2FD;
                color: #323232;
            }
            QComboBox QAbstractItemView::item:selected:hover {
                background-color: #BBDEFB;
                color: #323232;
            }
            
        """)
        task_method_layout.addWidget(self.method_combo)

        # 连接分析方法切换信号（currentTextChanged 仍会触发，显示文字变化时回调）
        self.method_combo.currentTextChanged.connect(self.on_analysis_method_changed)

        layout.addWidget(task_method_card)

        # 3. 分析窗口定义 + 选择事件锚点（合并为一个卡片）
        layout.addSpacing(16)

        # 创建合并卡片容器
        analysis_window_card = QWidget()
        analysis_window_card.setObjectName("analysis_window_card")
        analysis_window_card.setStyleSheet("""
            QWidget#analysis_window_card {
                background-color: #FFFFFF;
                border: 1px solid #E8E8E8;
                border-radius: 12px;
            }
        """)

        card_layout = QVBoxLayout(analysis_window_card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(10)

        # 标题行：分析窗口定义
        window_label = QLabel("分析窗口定义")
        window_label.setAlignment(Qt.AlignLeft)
        window_label.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-weight: 600;
                font-size: 14px;
                color: #000000;
                background-color: #FFFFFF;
            }
        """)
        card_layout.addWidget(window_label)

        # 分段切换容器（仅alpha Ratio方法时显示）
        self.segment_switch_container = QWidget()
        self.segment_switch_container.setStyleSheet("background-color: #FFFFFF;")
        # 隐藏时保留布局占位，避免切换方法时界面整体抖动/缩放感
        _segment_policy = self.segment_switch_container.sizePolicy()
        _segment_policy.setRetainSizeWhenHidden(True)
        self.segment_switch_container.setSizePolicy(_segment_policy)
        segment_switch_layout = QHBoxLayout(self.segment_switch_container)
        segment_switch_layout.setContentsMargins(0, 0, 0, 0)
        segment_switch_layout.setSpacing(8)

        # 分段1按钮（分子）- 蓝色
        self.segment1_btn = QPushButton("● 分段 1 (分子)")
        self.segment1_btn.setCheckable(True)
        self.segment1_btn.setChecked(True)
        self.segment1_btn.setStyleSheet("""
            QPushButton {
                font-family: Microsoft YaHei;
                background-color: #3B5998;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:checked {
                background-color: #3B5998;
            }
            QPushButton:!checked {
                background-color: #F0F0F0;
                color: #666666;
            }
            QPushButton:hover:!checked {
                background-color: #E0E0E0;
            }
        """)
        self.segment1_btn.clicked.connect(lambda: self.switch_segment(1))
        segment_switch_layout.addWidget(self.segment1_btn)

        # 分段2按钮（分母）- 橙色
        self.segment2_btn = QPushButton("● 分段 2 (分母)")
        self.segment2_btn.setCheckable(True)
        self.segment2_btn.setChecked(False)
        self.segment2_btn.setStyleSheet("""
            QPushButton {
                font-family: Microsoft YaHei;
                background-color: #E67E22;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:checked {
                background-color: #E67E22;
            }
            QPushButton:!checked {
                background-color: #F0F0F0;
                color: #666666;
            }
            QPushButton:hover:!checked {
                background-color: #E0E0E0;
            }
        """)
        self.segment2_btn.clicked.connect(lambda: self.switch_segment(2))
        segment_switch_layout.addWidget(self.segment2_btn)

        segment_switch_layout.addStretch()

        # 固定容器高度，保证显示/隐藏状态下占位一致
        self.segment_switch_container.setFixedHeight(self.segment_switch_container.sizeHint().height())
        # 默认隐藏分段切换容器
        self.segment_switch_container.hide()
        card_layout.addWidget(self.segment_switch_container)

        # Start 输入框（可编辑的 SpinBox）
        start_layout = QHBoxLayout()
        start_layout.setContentsMargins(0, 0, 0, 0)
        self.start_label = QLabel("Start (s)")
        self.start_label.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-weight: 500;
                font-size: 14px;
                color: #979797;
                background-color: white;
                padding: 4px 8px;
                border-radius: 6px;
            }
        """)
        start_layout.addWidget(self.start_label)
        start_layout.addStretch()

        self.start_spinbox = CustomSpinBox()
        self.start_spinbox.setMinimum(0)
        self.start_spinbox.setMaximum(36000)  # 最大10小时
        self.start_spinbox.setValue(int(self.analysis_start_time))
        self.start_spinbox.valueChanged.connect(self.on_start_time_changed)
        self.start_spinbox.setFixedSize(100, 32)
        self.start_spinbox.setStyleSheet("""
            QWidget {
                font-family: Microsoft YaHei;
                border: none;
                background-color: transparent;
                font-size: 14px;
            }
        """)
        start_layout.addWidget(self.start_spinbox)
        card_layout.addLayout(start_layout)

        # 保留隐藏的 start_time_label 用于兼容性
        self.start_time_label = QLineEdit(str(int(self.analysis_start_time)))
        self.start_time_label.hide()

        # Duration 输入框（持续时间，单位秒）- 与图片一致：开始时间 + 持续时间
        duration_layout = QHBoxLayout()
        duration_layout.setContentsMargins(0, 0, 0, 0)
        duration_label = QLabel("Duration (s)")
        duration_label.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-weight: 500;
                font-size: 14px;
                color: #979797;
                background-color: white;
                padding: 4px 8px;
                border-radius: 6px;
            }
        """)
        duration_layout.addWidget(duration_label)
        duration_layout.addStretch()

        self.duration_spinbox = CustomSpinBox()
        self.duration_spinbox.setMinimum(1)
        self.duration_spinbox.setMaximum(36000)  # 最大10小时
        self.duration_spinbox.setValue(int(self.analysis_duration))
        self.duration_spinbox.valueChanged.connect(self.on_duration_changed)
        self.duration_spinbox.setFixedSize(100, 32)
        self.duration_spinbox.setStyleSheet("""
            QWidget {
                font-family: Microsoft YaHei;
                border: none;
                background-color: transparent;
                font-size: 14px;
            }
        """)
        duration_layout.addWidget(self.duration_spinbox)
        card_layout.addLayout(duration_layout)

        # 兼容性：保留 end_spinbox 和 end_time_label 但不显示，内部 end = start + duration
        self.end_spinbox = CustomSpinBox()
        self.end_spinbox.setMinimum(1)
        self.end_spinbox.setMaximum(36000)
        self.end_spinbox.setValue(int(self.analysis_end_time))
        self.end_spinbox.hide()
        self.end_time_label = QLineEdit(str(int(self.analysis_end_time)))
        self.end_time_label.hide()

        # Selection 显示（仅alpha Ratio方法时可见）
        self.selection_label = QLabel(f"Selection: {int(self.analysis_duration)} Sec")
        self.selection_label.setAlignment(Qt.AlignCenter)
        self.selection_label.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-weight: 500;
                font-size: 13px;
                color: #3B5998;
                background-color: #FFFFFF;
                padding: 4px 8px;
            }
        """)
        card_layout.addWidget(self.selection_label)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #E8E8E8; max-height: 1px;")
        card_layout.addWidget(separator)

        # 选择事件锚点标题（与"分析窗口定义"和"方法配置"标题对齐）
        anchor_label = QLabel("选择事件锚点")
        anchor_label.setAlignment(Qt.AlignLeft)
        anchor_label.setStyleSheet("""
            QLabel {
                font-weight: 600;
                font-family: Microsoft YaHei;
                font-size: 14px;
                color: #000000;
                margin-top: 4px;
                background-color: white;
            }
        """)
        card_layout.addWidget(anchor_label)

        # 事件列表容器（添加左边距以与内容对齐）
        event_list_container = QWidget()
        event_list_container.setStyleSheet("background-color: transparent;")
        event_list_layout = QVBoxLayout(event_list_container)
        event_list_layout.setContentsMargins(8, 0, 0, 0)  # 左边距8px，与Start、End等内容对齐
        event_list_layout.setSpacing(0)

        self.event_list = QListWidget()
        self.event_list.setFocusPolicy(Qt.NoFocus)
        self.event_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.event_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 禁用水平滚动条
        # 增加高度以显示更多事件：每个事件项62px，间距6px，多显示2个事件需要增加约130px
        # 原高度150px + 130px = 280px
        self.event_list.setMinimumHeight(280)
        self.event_list.setSpacing(6)  # 设置列表项之间的间距，防止叠层
        self.event_list.setWordWrap(False)  # 禁用文字换行
        self.event_list.setTextElideMode(Qt.ElideRight)  # 超出部分用省略号显示
        self.event_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                outline: none;
            }
            QListWidget::item {
                border-radius: 8px;
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
            QListWidget::item:hover {
                background-color: transparent;
            }
            QListWidget::item:selected {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #F5F5F5;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #CCCCCC;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #999999;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                border: none;
                background-color: #F5F5F5;
                height: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background-color: #CCCCCC;
                min-width: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #999999;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        self.event_list.itemClicked.connect(self.on_event_selected)
        # 添加resize事件处理，确保窗口大小变化时更新事件项宽度
        self.event_list.installEventFilter(self)
        event_list_layout.addWidget(self.event_list)
        card_layout.addWidget(event_list_container)

        # 隐藏的 total_duration_label（保持兼容性）
        self.total_duration_label = QLabel(f"{self.analysis_duration:.1f} Sec")
        self.total_duration_label.hide()

        layout.addWidget(analysis_window_card)

        layout.addStretch()

        # 确认按钮
        self.confirm_button = QPushButton("确认配置")
        self.confirm_button.setStyleSheet("""
            QPushButton {
                font-family: Microsoft YaHei;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007ACC, stop:1 #005A9E);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px 20px;
                font-weight: bold;
                font-size: 12pt;
                min-height: 45px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0088DD, stop:1 #0066BB);
                transform: translateY(-2px);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #004080, stop:1 #003366);
                transform: translateY(0px);
            }
        """)
        self.confirm_button.clicked.connect(self.on_confirm)

        layout.addWidget(self.confirm_button)

        return left_widget

    def eventFilter(self, obj, event):
        """让分析方法下拉框：点击文字区域也能展开；处理事件列表resize事件；canvas首次resize修正"""
        try:
            if hasattr(self, 'canvas') and obj is self.canvas and event.type() == QEvent.Resize:
                # 画布尺寸变化时始终同步一次（去抖），避免仅前三次生效导致尺寸错位
                if not getattr(self, '_canvas_sync_pending', False):
                    self._canvas_sync_pending = True
                    QTimer.singleShot(0, self._sync_figure_size_to_canvas_debounced)

            if hasattr(self, "method_combo") and self.method_combo is not None:
                le = self.method_combo.lineEdit() if hasattr(self.method_combo, "lineEdit") else None
                if le is not None and obj == le:
                    if event.type() == QEvent.MouseButtonPress:
                        # 若已展开则关闭；否则展开
                        if self.method_combo.view().isVisible():
                            self.method_combo.hidePopup()
                        else:
                            self.method_combo.showPopup()
                        return True
            # 处理事件列表的resize事件，更新事件项宽度
            if hasattr(self, "event_list") and self.event_list is not None and obj == self.event_list:
                if event.type() == QEvent.Resize:
                    self._update_event_items_width()
                    return False  # 继续处理resize事件
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _update_event_items_width(self):
        """更新事件列表项的宽度，确保与列表宽度匹配"""
        if not hasattr(self, 'event_list') or self.event_list is None:
            return
        list_width = self.event_list.width()
        if list_width <= 0:
            return
        # 计算可用宽度（减去滚动条宽度约20px和边距10px）
        item_width = max(200, list_width - 30)
        available_width = list_width - 24 - 20  # 减去左右边距(12*2)和滚动条宽度(约20)

        # 更新所有事件项的宽度和标签文本
        for i in range(self.event_list.count()):
            item = self.event_list.item(i)
            if item is None:
                continue
            # 更新item的宽度
            item.setSizeHint(QSize(item_width, 62))
            # 更新widget中name_label的宽度和文本
            item_widget = self.event_list.itemWidget(item)
            if item_widget is not None:
                # 查找name_label（第二个QLabel）
                layout = item_widget.layout()
                if layout is not None and layout.count() >= 2:
                    name_label = layout.itemAt(1).widget()
                    if name_label is not None and isinstance(name_label, QLabel):
                        name_label.setMaximumWidth(available_width)
                        name_label.setMinimumWidth(available_width)
                        # 重新计算省略文本
                        if hasattr(self, 'events') and i < len(self.events):
                            event_name = self.events[i]['name']
                            fm = name_label.fontMetrics()
                            elided_text = fm.elidedText(event_name, Qt.ElideRight, available_width)
                            name_label.setText(elided_text)

    def create_filter_bar(self):
        """创建顶部信号滤波栏"""
        filter_bar = QWidget()
        filter_bar.setAttribute(Qt.WA_StyledBackground, True)
        filter_bar.setObjectName("filter_bar_card")
        # 使用垂直布局时，需要更多的高度空间，移除固定高度限制或设置为更大的值
        # filter_bar.setFixedHeight(90)  # 注释掉固定高度，让布局自适应
        # 圆角矩形样式，与左侧方法配置卡片保持一致
        filter_bar.setStyleSheet("""
            QWidget#filter_bar_card {
                background-color: #FFFFFF;
                border-radius: 12px;
            }
        """)

        # 使用垂直布局
        layout = QVBoxLayout(filter_bar)
        layout.setContentsMargins(12, 12, 12, 12)  # 内边距与左侧卡片一致
        layout.setSpacing(15)  # 减小间距，从35改为15

        # 设置滤波器和 QuickBANdpass 为水平布局

        HorizonLayout = QHBoxLayout()
        HorizonLayout.setSpacing(6)  # 设置较小的间距
        # 标题（与左侧"方法配置"标题保持顶部对齐）
        filter_title = QLabel("滤波器")
        filter_title.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        filter_title.setStyleSheet("""
            QLabel {
             
                letter-spacing: 1px;
                font-family: Microsoft YaHei;
                font-weight: 500;
                font-size: 14px;
                color: #000000;
                background-color: white;
                padding-bottom: 10px;
            }
        """)
        HorizonLayout.addWidget(filter_title, alignment=Qt.AlignTop)

        # 添加弹性空间，实现比例布局而非固定距离
        HorizonLayout.addStretch(1)

        # Quick Bandpass 下拉菜单（放在最前面）
        bp_layout = QHBoxLayout()
        bp_layout.setSpacing(4)  # 设置固定间距，紧凑但不挨着（从8px改为4px）
        bp_label = QLabel("QUICK BANDPASS:")
        bp_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #979797;
                font-family: Microsoft YaHei;
                font-weight: 500;
                font-style: normal;
                background-color: white;
            }
        """)
        bp_layout.addWidget(bp_label)

        self.bandpass_combo = QComboBox()
        self.bandpass_combo.addItems([
            "Delta (0.5-4.0Hz)",
            "Theta (4.0-8.0Hz)",
            "Alpha (8.0-13.0Hz)",
            "SMR (12.0-15.0Hz)",
            "Beta (13.0-30.0Hz)",
            "Custom (0.5-30.0Hz)"
        ])
        # Quick Bandpass 初始模式：优先使用任务配置中的 bandpass_mode
        initial_bandpass = getattr(self, 'bandpass_mode', None)
        if initial_bandpass in [self.bandpass_combo.itemText(i) for i in range(self.bandpass_combo.count())]:
            self.bandpass_combo.setCurrentText(initial_bandpass)
        else:
            self.bandpass_combo.setCurrentText("Custom (0.5-30.0Hz)")
        self.bandpass_combo.currentTextChanged.connect(self.on_bandpass_changed)
        self.bandpass_combo.setFixedSize(165, 24)  # 加宽以完整显示 "Custom (0.5-30.0Hz)" 等文本
        self.bandpass_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid rgba(141, 161, 193, 102);
                border-radius: 2px;
                padding: 0px 8px;
                background-color: white;
                font-family: Microsoft YaHei;
                font-weight: 400;
                font-size: 14px;
                color: #323232;
                font-style: normal;
            }
            QComboBox:hover {
                border: 1px solid rgba(141, 161, 193, 153);
                background-color: white;
                color: #323232;
            }
            QComboBox:focus {
                border: 1px solid rgba(141, 161, 193, 204);
                background-color: white;
            }
            QComboBox::drop-down {
                border: none;
                background: transparent;
                width: 16px;
            }
            QComboBox::down-arrow {
                image: url(./resource/picture/arrowhead.png);
                width: 16px;
                height: 16px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid rgba(141, 161, 193, 102);
                border-radius: 2px;
                background-color: white;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                padding: 4px 8px;
                color: #323232;
                background-color: white;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: white;
                color: #323232;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #2A87DB;
                color: white;
            }
        """)
        bp_layout.addWidget(self.bandpass_combo)
        # layout.addLayout(bp_layout)
        HorizonLayout.addLayout(bp_layout, stretch=0)  # 不拉伸，保持固定大小
        layout.addLayout(HorizonLayout)

        HorizonLayout1 = QHBoxLayout()
        # High-pass 控件（开关 + 数值输入）
        hp_layout = QHBoxLayout()
        hp_layout.setSpacing(10)

        # High-pass 开关
        # 需求：初始(启用)=蓝底且白色圆点在右；点击后圆点右->左滑动且背景蓝->灰
        self.highpass_checkbox = SlideSwitch(checked=bool(getattr(self, 'highpass_enabled', True)), width=40, height=20)
        self.highpass_checkbox.stateChanged.connect(self.on_highpass_toggle)
        hp_layout.addWidget(self.highpass_checkbox)

        # High-pass 标签
        self.highpass_label = QLabel("High-pass")
        self.highpass_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #2A87DB;
                font-weight: 500;
                font-family: Microsoft YaHei;
            }
        """)
        hp_layout.addWidget(self.highpass_label)

        # High-pass 数值输入（使用CustomDoubleSpinBox，支持左右箭头）
        self.highpass_spinbox = CustomDoubleSpinBox()
        self.highpass_spinbox.setMinimum(0.1)
        self.highpass_spinbox.setMaximum(100.0)
        self.highpass_spinbox.setValue(getattr(self, 'highpass_value', 1.0))  # 使用从配置中获取的值（即使禁用也保留）
        self._apply_filter_upper_bound()
        self.highpass_spinbox.setSingleStep(0.1)  # 每次调整0.1
        self.highpass_spinbox.setDecimals(1)  # 保留1位小数
        self.highpass_spinbox.setSuffix(" Hz")
        self.highpass_spinbox.setEnabled(self.highpass_checkbox.isChecked())
        self.highpass_spinbox.valueChanged.connect(self.update_filter_params)
        # 设置整个输入框的固定大小，增加宽度以完整显示文字
        self.highpass_spinbox.setFixedSize(120, 24)
        # 使用自定义DoubleSpinBox，样式应用到外层容器
        self.highpass_spinbox.setStyleSheet("""
            QWidget {
                font-family: Microsoft YaHei;
                border: none;
                background-color: transparent;
                font-size: 14px;
            }
        """)
        hp_layout.addWidget(self.highpass_spinbox)

        hp_layout.addStretch()
        HorizonLayout1.addLayout(hp_layout)

        # Low-pass 控件（开关 + 数值输入）
        lp_layout = QHBoxLayout()
        lp_layout.setSpacing(10)

        # Low-pass 开关
        self.lowpass_checkbox = SlideSwitch(checked=bool(getattr(self, 'lowpass_enabled', True)), width=40, height=20)
        self.lowpass_checkbox.stateChanged.connect(self.on_lowpass_toggle)
        lp_layout.addWidget(self.lowpass_checkbox)

        # Low-pass 标签
        self.lowpass_label = QLabel("Low-pass")
        self.lowpass_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #2A87DB;
                font-weight: 500;
                font-family: Microsoft YaHei;
            }
        """)
        lp_layout.addWidget(self.lowpass_label)

        # Low-pass 数值输入（使用CustomDoubleSpinBox，支持左右箭头）
        self.lowpass_spinbox = CustomDoubleSpinBox()
        self.lowpass_spinbox.setMinimum(0.1)
        self.lowpass_spinbox.setMaximum(200.0)
        self.lowpass_spinbox.setValue(getattr(self, 'lowpass_value', 35.0))  # 使用从配置中获取的值（即使禁用也保留）
        self.lowpass_spinbox.setSingleStep(0.1)  # 每次调整0.1
        self.lowpass_spinbox.setDecimals(1)  # 保留1位小数
        self.lowpass_spinbox.setSuffix(" Hz")
        self.lowpass_spinbox.setEnabled(self.lowpass_checkbox.isChecked())
        self.lowpass_spinbox.valueChanged.connect(self.update_filter_params)
        # 设置整个输入框的固定大小，增加宽度以完整显示文字
        self.lowpass_spinbox.setFixedSize(120, 24)
        # 使用自定义DoubleSpinBox，样式应用到外层容器
        self.lowpass_spinbox.setStyleSheet("""
            QWidget {
                font-family: Microsoft YaHei;
                border: none;
                background-color: transparent;
                font-size: 14px;
            }
        """)
        lp_layout.addWidget(self.lowpass_spinbox)

        lp_layout.addStretch()
        HorizonLayout1.addLayout(lp_layout)

        # Notch 控件（开关 + 数值输入）
        notch_layout = QHBoxLayout()
        notch_layout.setSpacing(10)

        # Notch 开关
        self.notch_checkbox = SlideSwitch(checked=bool(getattr(self, 'notch_enabled', True)), width=40, height=20)
        self.notch_checkbox.stateChanged.connect(self.on_notch_toggle)
        notch_layout.addWidget(self.notch_checkbox)

        # Notch 标签
        self.notch_label = QLabel("Notch")
        self.notch_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #2A87DB;
                font-weight: 500;
                font-family: Microsoft YaHei;
            }
        """)
        notch_layout.addWidget(self.notch_label)

        # Notch 数值输入（使用自定义DoubleSpinBox，支持左右箭头）
        self.notch_spinbox = CustomDoubleSpinBox()
        self.notch_spinbox.setMinimum(0.1)
        self.notch_spinbox.setMaximum(200.0)
        self.notch_spinbox.setValue(getattr(self, 'notch_value', 50.0))  # 使用从配置中获取的值（即使禁用也保留）
        self.notch_spinbox.setSingleStep(0.1)  # 每次调整0.1
        self.notch_spinbox.setDecimals(1)  # 保留1位小数
        self.notch_spinbox.setSuffix(" Hz")
        self.notch_spinbox.setEnabled(self.notch_checkbox.isChecked())
        self.notch_spinbox.valueChanged.connect(self.update_filter_params)
        # 使用setButtonSymbols移除默认按钮，然后通过CSS样式无法实现左右箭头
        # PyQt5的QDoubleSpinBox不支持通过CSS将箭头改为左右方向
        # 需要创建自定义控件或使用图像
        # 设置整个输入框的固定大小，增加宽度以完整显示文字
        self.notch_spinbox.setFixedSize(120, 24)
        # 使用自定义DoubleSpinBox，样式应用到外层容器
        self.notch_spinbox.setStyleSheet("""
            QWidget {
                font-family: Microsoft YaHei;
                border: none;
                background-color: transparent;
                font-size: 14px;
            }
        """)
        notch_layout.addWidget(self.notch_spinbox)

        notch_layout.addStretch()
        HorizonLayout1.addLayout(notch_layout)
        layout.addLayout(HorizonLayout1)

        layout.addStretch()

        # 初次创建时不主动调用 on_bandpass_changed，避免覆盖从配置恢复的自定义滤波参数。
        # 仅根据开关状态刷新输入框可用性与标签颜色（不触发重滤波/重绘）。
        try:
            if hasattr(self, 'highpass_label') and hasattr(self, 'highpass_checkbox'):
                self.highpass_label.setStyleSheet("""
                    QLabel {
                        font-size: 14px;
                        color: %s;
                        font-weight: 500;
                        font-family: Microsoft YaHei;
                    }
                """ % ("#007ACC" if self.highpass_checkbox.isChecked() else "#999999"))
            if hasattr(self, 'lowpass_label') and hasattr(self, 'lowpass_checkbox'):
                self.lowpass_label.setStyleSheet("""
                    QLabel {
                        font-size: 14px;
                        color: %s;
                        font-weight: 500;
                        font-family: Microsoft YaHei;
                    }
                """ % ("#007ACC" if self.lowpass_checkbox.isChecked() else "#999999"))
            if hasattr(self, 'notch_label') and hasattr(self, 'notch_checkbox'):
                self.notch_label.setStyleSheet("""
                    QLabel {
                        font-size: 14px;
                        color: %s;
                        font-weight: 500;
                        font-family: Microsoft YaHei;
                    }
                """ % ("#007ACC" if self.notch_checkbox.isChecked() else "#999999"))
        except Exception:
            pass

        return filter_bar

    # 右侧面板（包含SIGNAL FILTERING和波形显示）
    def create_right_panel(self):
        """创建右侧面板（包含信号滤波栏和波形显示）"""
        right_widget = QWidget()
        right_widget.setStyleSheet("""
            QWidget {
                /* 大页面底色：跟随主背景 */
                background-color: #F6F9FF;
            }
        """)

        layout = QVBoxLayout(right_widget)
        layout.setContentsMargins(0, 25, 15, 25)  # 顶部边距25px与左侧面板对齐
        layout.setSpacing(15)  # 滤波器组件与波形图之间的间距

        # 顶部信号滤波栏
        filter_bar = self.create_filter_bar()
        layout.addWidget(filter_bar, stretch=0)

        # 波形显示面板
        plot_widget = QWidget()
        plot_widget.setAttribute(Qt.WA_StyledBackground, True)
        plot_widget.setObjectName("plot_widget_card")
        # 设置暗蓝色背景和圆角矩形样式
        plot_widget.setStyleSheet("""
            QWidget#plot_widget_card {
                background-color: #08223C;
                border-radius: 15px;
                border: 2px solid #2a3f5f;
            }
        """)

        plot_layout = QVBoxLayout(plot_widget)
        plot_layout.setContentsMargins(2, 2, 2, 2)  # 添加边距让圆角可见
        plot_layout.setSpacing(0)

        # todo 下拉框
        # ========== 顶部工具栏（包含下拉框） ==========
        top_toolbar = QWidget()
        top_toolbar.setFixedHeight(40)  # 设置工具栏高度
        top_toolbar.setStyleSheet("""
                QWidget {
                    background-color: #08223C;
                    border-top-left-radius: 13px;
                    border-top-right-radius: 13px;
                }
            """)

        toolbar_layout = QHBoxLayout(top_toolbar)
        toolbar_layout.setContentsMargins(15, 0, 15, 0)
        toolbar_layout.setSpacing(10)

        # 添加标签
        toolbar_label_x = QLabel("X轴缩放：")
        toolbar_label_x.setStyleSheet(ControlStyle.get_qeeg_font_400("#FFFFFF", "12", "left"))
        toolbar_layout.addWidget(toolbar_label_x)

        # 添加下拉框
        self.plot_combo_x = QComboBox()
        self.plot_combo_x.addItems(
            ["Auto", "5 秒/页", "10 秒/页", "15 秒/页", "20 秒/页", "30 秒/页", "60 秒/页", "15 分钟/页", "20 分钟/页",
             "1 小时/页"])  # Auto为10分钟/页
        # 回显已保存的 X 轴缩放模式
        if getattr(self, 'x_axis_scale', None) in [self.plot_combo_x.itemText(i) for i in range(self.plot_combo_x.count())]:
            self.plot_combo_x.setCurrentText(self.x_axis_scale)
        self.plot_combo_x.setFixedSize(120, 28)  # 设置固定大小
        self.plot_combo_x.setStyleSheet(ControlStyle.get_QComboBox_style())
        self.plot_combo_x.currentTextChanged.connect(self.on_plot_combo_changed_x)
        toolbar_layout.addWidget(self.plot_combo_x)

        toolbar_label_y = QLabel("Y轴缩放：")
        toolbar_label_y.setStyleSheet(ControlStyle.get_qeeg_font_400("#FFFFFF", "12", "left") + "margin-left:10px;")
        toolbar_layout.addWidget(toolbar_label_y)

        # 添加下拉框
        self.plot_combo_y = QComboBox()
        self.plot_combo_y.addItems(
            ["Auto", "10000 uV", "5000 uV", "2000 uV", "1000 uV", "500 uV", "200 uV", "100 uV", "50 uV", "20 uV",
             "10 uV",
             "5 uV"])
        # 回显已保存的 Y 轴缩放模式
        if getattr(self, 'y_axis_scale', None) in [self.plot_combo_y.itemText(i) for i in range(self.plot_combo_y.count())]:
            self.plot_combo_y.setCurrentText(self.y_axis_scale)
        self.plot_combo_y.setFixedSize(120, 28)  # 设置固定大小
        self.plot_combo_y.setStyleSheet(ControlStyle.get_QComboBox_style())
        self.plot_combo_y.setMaxVisibleItems(12)
        self.plot_combo_y.currentTextChanged.connect(self.on_plot_combo_changed_y)
        toolbar_layout.addWidget(self.plot_combo_y)

        toolbar_layout.addStretch()  # 添加弹性空间，使下拉框靠左

        # 将工具栏添加到波形图容器的顶部
        plot_layout.addWidget(top_toolbar, stretch=0)

        # ========== 波形图画布区域 ==========

        # 创建canvas容器Widget
        canvas_container = QWidget()
        canvas_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # 启用样式背景
        canvas_container.setAttribute(Qt.WA_StyledBackground, True)
        canvas_container.setObjectName("canvas_container")
        canvas_container.setStyleSheet("""
            QWidget#canvas_container {
                background-color: #08223C;
                border-radius: 13px;
                border: none;
            }
        """)
        canvas_container_layout = QVBoxLayout(canvas_container)
        canvas_container_layout.setContentsMargins(10, 10, 10, 10)  # 添加边距避免canvas覆盖圆角
        canvas_container_layout.setSpacing(0)

        # 创建matplotlib图形
        # 暗蓝色背景
        dark_blue_color = '#08223C'  # 暗蓝色
        self.figure = Figure(figsize=(8, 5), facecolor=dark_blue_color)
        self.canvas = FigureCanvas(self.figure)
        # 设置canvas的大小策略，让布局完全控制其大小
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # 不设置固定大小，让布局管理
        # canvas背景色与容器一致
        self.canvas.setStyleSheet("""
            background-color: #08223C;
            border: none;
        """)
        # 确保canvas由布局管理，不超出父组件范围
        self.canvas.setParent(canvas_container)
        self.canvas.installEventFilter(self)

        # # 将canvas添加到布局中，让布局完全管理其大小和位置
        canvas_container_layout.addWidget(self.canvas, stretch=1)

        # 将canvas容器添加到主布局，并添加stretch让它占据可用空间
        plot_layout.addWidget(canvas_container, stretch=1)

        # 添加X轴滚动条
        from PyQt5.QtWidgets import QScrollBar
        self.x_scrollbar = QScrollBar(Qt.Horizontal)
        self.x_scrollbar.setMinimum(0)
        self.x_scrollbar.setMaximum(0)  # 初始为0，数据加载后更新
        self.x_scrollbar.setPageStep(100)  # 可见窗口大小（秒 * 10）
        self.x_scrollbar.setValue(0)
        self.x_scrollbar.valueChanged.connect(self.on_x_scroll)
        self.x_scrollbar.setStyleSheet("""
            QScrollBar:horizontal {
                border: none;
                background: #1a3a5c;
                height: 12px;
                margin: 0px 0px 0px 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background: #4a7a9c;
                min-width: 30px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #5a8aac;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)
        plot_layout.addWidget(self.x_scrollbar)

        '''
        self.widget_time_slider = TimeSliderWidget()
        plot_layout.addWidget(self.widget_time_slider)
        self.widget_time_slider.time_slider.valueChanged.connect(self.on_slider_changed)
        '''

        # 底部时间信息
        # 创建底部时间信息容器Widget
        bottom_time_widget = QWidget()
        bottom_time_widget.setAttribute(Qt.WA_StyledBackground, True)
        bottom_time_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 15px;
            }
        """)
        time_info_layout = QHBoxLayout(bottom_time_widget)
        time_info_layout.setContentsMargins(15, 10, 15, 10)
        time_info_layout.setSpacing(15)

        # 左侧：START 和 END
        left_time_layout = QHBoxLayout()
        left_time_layout.setSpacing(15)

        # START 标题和时间分开
        start_container = QHBoxLayout()
        start_container.setSpacing(5)
        start_title_label = QLabel("START")
        start_title_label.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-weight: 500;
                font-size: 14px;
                color: #979797;
                border: none;
                background-color: transparent;
            }
        """)
        start_container.addWidget(start_title_label)
        self.bottom_start_label = QLabel("0:00")
        self.bottom_start_label.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-weight: 500;
                font-size: 14px;
                color: #31373D;
                border: none;
                background-color: transparent;
            }
        """)
        start_container.addWidget(self.bottom_start_label)
        left_time_layout.addLayout(start_container)

        # END 标题和时间分开
        end_container = QHBoxLayout()
        end_container.setSpacing(5)
        end_title_label = QLabel("END")
        end_title_label.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-weight: 500;
                font-size: 14px;
                color: #979797;
                border: none;
                background-color: transparent;
            }
        """)
        end_container.addWidget(end_title_label)
        self.bottom_end_label = QLabel("1:00")
        self.bottom_end_label.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-weight: 500;
                font-size: 14px;
                color: #31373D;
                border: none;
                background-color: transparent;
            }
        """)
        end_container.addWidget(self.bottom_end_label)
        left_time_layout.addLayout(end_container)

        time_info_layout.addLayout(left_time_layout)
        time_info_layout.addStretch()  # 中间添加弹性空间

        # 右侧：TOTAL DURATION
        total_container = QHBoxLayout()
        total_container.setSpacing(5)
        total_title_label = QLabel("TOTAL DURATION")
        total_title_label.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-weight: 500;
                font-size: 14px;
                color: #979797;
                border: none;
                background-color: transparent;
            }
        """)
        total_container.addWidget(total_title_label)
        self.bottom_total_label = QLabel("60.0 Sec")
        self.bottom_total_label.setStyleSheet("""
            QLabel {
                font-family: Microsoft YaHei;
                font-weight: 500;
                font-size: 14px;
                color: #31373D;
                border: none;
                background-color: transparent;
            }
        """)
        total_container.addWidget(self.bottom_total_label)
        time_info_layout.addLayout(total_container)

        # 将波形显示面板添加到右侧主布局
        layout.addWidget(plot_widget, stretch=1)

        # 将底部时间信息容器添加到右侧主布局（在波形图区域下方，保持15px间距）
        layout.addWidget(bottom_time_widget, stretch=0)

        return right_widget

    def on_plot_combo_changed_x(self, text):
        """波形图上方的下拉框变化处理 - 只更新X轴范围与滚动条，不重新绘制波形图"""
        try:
            QLLogging.log.info(f"Plot combo changed to: {text}")
            # 保存当前 X 轴缩放模式，供任务配置持久化
            self.x_axis_scale = text
            text = text.strip()
            total_time = self.total_duration if self.total_duration > 0 else 600
            if text == "Auto":
                # Auto：固定 600 秒可见窗口（与 plot_waveforms 一致）
                visible_window = min(600, total_time)
            else:
                if text[-3] == '秒':
                    visible_window = float(text.split(" ")[0])
                elif text[-3] == '钟':
                    visible_window = float(text.split(" ")[0]) * 60
                elif text[-3] == '时':
                    visible_window = float(text.split(" ")[0]) * 3600
                visible_window = min(visible_window, total_time)

            QLLogging.log.debug(f"X轴缩放: visible_window={visible_window}s, total={total_time}s")

            # 更新 X 轴显示范围（0 ~ visible_window）
            self.on_x_scroll(0, visible_window)

            # 同步更新滚动条范围与显隐，使非 Auto 时能通过滚动条查看全部数据，且滚动条始终在需要时存在
            self._update_x_scrollbar_range(total_time, visible_window)

            # 波形缩放后，禁用滤波器checkbox
            self.disable_filter_checkboxes()

        except Exception as e:
            QLLogging.log.exception(f"Error in on_plot_combo_changed_x: {e}")

    def on_plot_combo_changed_y(self, text):
        """波形图上方的下拉框变化处理 - Y轴缩放需要重新绘制"""
        try:
            QLLogging.log.info(f"Plot combo changed to: {text}")
            # 保存当前选中的选项，供任务配置持久化
            self.current_plot_option = text
            self.y_axis_scale = text

            # Y轴缩放需要重新绘制波形图（因为每个通道的y轴范围需要更新）
            # 但需要确保数据已准备好，避免清空画布后无法绘制
            if self.raw_filtered is not None:
                # 检查是否有有效的axes，如果有则只更新y轴范围，避免完全重绘
                if hasattr(self, 'inside_axes') and len(self.inside_axes) > 0:
                    # 尝试只更新y轴范围，不重新绘制
                    try:
                        amplitude = text
                        if amplitude != "Auto":
                            scale_amplitude = int(amplitude[:-2])
                            for inside_ax in self.inside_axes:
                                if inside_ax is not None:
                                    inside_ax.set_ylim([-scale_amplitude, scale_amplitude])
                        else:
                            for inside_ax in self.inside_axes:
                                if inside_ax is not None:
                                    inside_ax.autoscale(axis='y')

                        # 更新画布
                        if hasattr(self, 'canvas') and self.canvas is not None:
                            self.canvas.draw_idle()
                        QLLogging.log.debug(f"Y轴范围已更新，无需重新绘制")
                    except Exception as e:
                        QLLogging.log.warning(f"只更新Y轴范围失败，将重新绘制: {e}")
                        # 如果更新失败，回退到重新绘制
                        self.plot_waveforms()
                else:
                    # 如果没有axes，需要重新绘制
                    self.plot_waveforms()
            else:
                QLLogging.log.warning("No filtered data available for Y-axis scaling")

            # 波形缩放后，禁用滤波器checkbox
            self.disable_filter_checkboxes()

        except Exception as e:
            QLLogging.log.exception(f"Error in on_plot_combo_changed_y: {e}")

    def update_config(self, task_config, refresh_plot=False, flag=None):
        """
        更新任务配置（用于信号和槽方式，避免重新创建实例）
        
        参数:
            task_config: Task对象或字典，包含任务配置信息
        """
        try:
            # 将Task对象转换为字典
            if hasattr(task_config, 'to_dict'):
                task_config_dict = task_config.to_dict()
            elif isinstance(task_config, dict):
                task_config_dict = task_config
            else:
                # 如果是Task对象但没有to_dict方法，直接访问属性
                task_config_dict = {
                    'id': getattr(task_config, 'id', None),
                    'name': getattr(task_config, 'name', None),
                    'task_name': getattr(task_config, 'name', None),  # Task对象使用name属性
                    'analysis_method': getattr(task_config, 'analysis_method', None),
                    'start_time': getattr(task_config, 'start_time', None),
                    'end_time': getattr(task_config, 'end_time', None),
                    'high_pass': getattr(task_config, 'high_pass', None),
                    'low_pass': getattr(task_config, 'low_pass', None),
                    'notch': getattr(task_config, 'notch', None),
                    'high_pass_enabled': getattr(task_config, 'high_pass_enabled', None),
                    'low_pass_enabled': getattr(task_config, 'low_pass_enabled', None),
                    'notch_enabled': getattr(task_config, 'notch_enabled', None),
                    'bandpass_mode': getattr(task_config, 'bandpass_mode', None),
                    'x_axis_scale': getattr(task_config, 'x_axis_scale', None),
                    'y_axis_scale': getattr(task_config, 'y_axis_scale', None),
                    'selected_event_names': getattr(task_config, 'selected_event_names', None),  # 添加事件名称支持
                    'selected_event_names_segment1': getattr(task_config, 'selected_event_names_segment1', None),
                    'selected_event_names_segment2': getattr(task_config, 'selected_event_names_segment2', None),
                    'current_segment': getattr(task_config, 'current_segment', None),  # alpha Ratio(EC/EO) 当前分段
                }

            # 兼容：Task.to_dict 目前未包含 current_segment，这里从对象属性补齐
            if isinstance(task_config_dict, dict) and task_config_dict.get('current_segment') is None and hasattr(
                    task_config, 'current_segment'):
                task_config_dict['current_segment'] = getattr(task_config, 'current_segment')

            # 兼容：从 task 属性或 task_params 中补齐分段事件名称（Task.to_dict 可能未包含或来自旧库）
            if isinstance(task_config_dict, dict):
                if task_config_dict.get('selected_event_names_segment1') is None and hasattr(task_config, 'selected_event_names_segment1'):
                    task_config_dict['selected_event_names_segment1'] = getattr(task_config, 'selected_event_names_segment1', None)
                if task_config_dict.get('selected_event_names_segment2') is None and hasattr(task_config, 'selected_event_names_segment2'):
                    task_config_dict['selected_event_names_segment2'] = getattr(task_config, 'selected_event_names_segment2', None)
                if hasattr(task_config, 'task_params') and isinstance(task_config.task_params, dict):
                    tp = task_config.task_params
                    if task_config_dict.get('selected_event_names_segment1') is None:
                        task_config_dict['selected_event_names_segment1'] = tp.get('selected_event_names_segment1')
                    if task_config_dict.get('selected_event_names_segment2') is None:
                        task_config_dict['selected_event_names_segment2'] = tp.get('selected_event_names_segment2')
                    # 与滤波器一致：从 task_params 补齐 bandpass_mode、x_axis_scale、y_axis_scale（Task.to_dict 可能缺）
                    if task_config_dict.get('bandpass_mode') is None:
                        task_config_dict['bandpass_mode'] = tp.get('bandpass_mode')
                    if task_config_dict.get('x_axis_scale') is None:
                        task_config_dict['x_axis_scale'] = tp.get('x_axis_scale')
                    if task_config_dict.get('y_axis_scale') is None:
                        task_config_dict['y_axis_scale'] = tp.get('y_axis_scale')

            # 更新内部配置参数
            # 支持两种键名：'name' 和 'task_name'（Task对象使用name，字典可能使用task_name）
            task_name = task_config_dict.get('task_name') or task_config_dict.get('name')
            if task_name:
                self.task_name = task_name

            task_id = task_config_dict.get('id')
            if task_id is not None:
                self.task_id = task_id

            analysis_method = task_config_dict.get('analysis_method')
            if analysis_method:
                self.analysis_method = analysis_method

            # 更新开始时间和结束时间
            # 如果值为 None，使用默认值或保持当前值（避免影响其他任务）
            start_time = task_config_dict.get('start_time')
            if start_time is not None:
                self.analysis_start_time = int(float(start_time))
            # 如果 start_time 为 None，不更新（保持当前实例的值，避免影响其他任务）
            # 但如果是第一次加载，应该使用默认值
            elif not hasattr(self, 'analysis_start_time') or self.analysis_start_time is None:
                self.analysis_start_time = 0  # 默认值

            end_time = task_config_dict.get('end_time')
            if end_time is not None:
                self.analysis_end_time = int(float(end_time))
            # self.analysis_end_time = int(end_time)
            # 如果 end_time 为 None，不更新（保持当前实例的值，避免影响其他任务）
            # 但如果是第一次加载，应该使用默认值
            elif not hasattr(self, 'analysis_end_time') or self.analysis_end_time is None:
                self.analysis_end_time = 120  # 默认值

            high_pass = task_config_dict.get('high_pass')
            if high_pass is not None:
                self.highpass_value = float(high_pass)
            elif not hasattr(self, 'highpass_value') or self.highpass_value is None:
                self.highpass_value = 0.8
            # 恢复 high-pass 是否启用（优先显式字段，否则兼容旧数据：值为 None 视为禁用）
            hp_enabled = task_config_dict.get('high_pass_enabled')
            if hp_enabled is not None:
                self.highpass_enabled = bool(int(hp_enabled))
            elif high_pass is None:
                self.highpass_enabled = False
            else:
                self.highpass_enabled = True
            self.highpass = self.highpass_value if self.highpass_enabled else None

            low_pass = task_config_dict.get('low_pass')
            if low_pass is not None:
                self.lowpass_value = float(low_pass)
            elif not hasattr(self, 'lowpass_value') or self.lowpass_value is None:
                self.lowpass_value = 71.0
            lp_enabled = task_config_dict.get('low_pass_enabled')
            if lp_enabled is not None:
                self.lowpass_enabled = bool(int(lp_enabled))
            elif low_pass is None:
                self.lowpass_enabled = False
            else:
                self.lowpass_enabled = True
            self.lowpass = self.lowpass_value if self.lowpass_enabled else None

            notch = task_config_dict.get('notch')
            if notch is not None:
                self.notch_value = float(notch)
            elif not hasattr(self, 'notch_value') or self.notch_value is None:
                self.notch_value = 50.0
            notch_enabled = task_config_dict.get('notch_enabled')
            if notch_enabled is not None:
                self.notch_enabled = bool(int(notch_enabled))
            elif notch is None and 'notch' in task_config_dict:
                # 显式传了 notch=None（旧逻辑有效值）时视为禁用
                self.notch_enabled = False
            else:
                # 缺失 notch 字段时默认启用
                self.notch_enabled = True
            self.notch = self.notch_value if self.notch_enabled else None

            # 恢复 Quick Bandpass 模式、X/Y 缩放（与滤波器一致：更新内部属性）
            bandpass_mode = task_config_dict.get('bandpass_mode')
            if bandpass_mode is not None:
                self.bandpass_mode = bandpass_mode
            x_axis_scale = task_config_dict.get('x_axis_scale')
            if x_axis_scale is not None:
                self.x_axis_scale = x_axis_scale
            y_axis_scale = task_config_dict.get('y_axis_scale')
            if y_axis_scale is not None:
                self.y_axis_scale = y_axis_scale

            # 计算分析窗口时长
            self.analysis_duration = self.analysis_end_time - self.analysis_start_time
            if self.analysis_duration <= 0:
                QLLogging.log.warning(f"Invalid duration: {self.analysis_duration}s, using default 120s")
                self.analysis_duration = 120
                self.analysis_end_time = self.analysis_start_time + self.analysis_duration

            # 恢复 segment2（分母）时间参数（alpha Ratio EC/EO 方法专用）
            # 已配置过的任务会有 start_time_/end_time_，新建任务这两个值为 None，需要重置为默认值
            start_time_ = task_config_dict.get('start_time_')
            end_time_ = task_config_dict.get('end_time_')
            self.segment2_start_time = int(float(start_time_)) if start_time_ is not None else 0
            self.segment2_end_time = int(float(end_time_)) if end_time_ is not None else 60
            self.segment2_duration = self.segment2_end_time - self.segment2_start_time
            if self.segment2_duration <= 0:
                self.segment2_duration = 60
                self.segment2_end_time = self.segment2_start_time + self.segment2_duration
            QLLogging.log.debug(
                f"Segment2 times: start={self.segment2_start_time}, "
                f"end={self.segment2_end_time}, duration={self.segment2_duration}")

            # 恢复 alpha Ratio(EC/EO) 当前分段（1=分子，2=分母）
            current_segment = task_config_dict.get('current_segment')
            if current_segment in (1, 2, '1', '2'):
                self.current_segment = int(current_segment)
            elif not hasattr(self, 'current_segment') or self.current_segment not in (1, 2):
                self.current_segment = 1

            # 更新UI元素
            QLLogging.log.info(f"Updating UI for task: {self.task_name} (ID: {self.task_id})")

            if hasattr(self, 'task_name_input'):
                self.task_name_input.setText(self.task_name)
                QLLogging.log.debug(f"Updated task_name_input to: {self.task_name}")

            if hasattr(self, 'method_combo'):
                # 按内部方法键选中（下拉显示为中英文，键存于 UserData）
                method_index = self.method_combo.findData(self.analysis_method, Qt.UserRole)
                if method_index >= 0:
                    self.method_combo.setCurrentIndex(method_index)
                    QLLogging.log.debug(f"Updated method_combo to: {self.analysis_method}")
                else:
                    QLLogging.log.warning(f"Analysis method '{self.analysis_method}' not found in combo box")

            # 更新分析时长spinbox（秒）：
            # alpha Ratio(EC/EO) 且当前为分段2时，显示分段2时长
            current_method = self.get_current_analysis_method() if hasattr(self,
                                                                           'method_combo') else self.analysis_method
            use_segment2 = current_method == "alpha Ratio(EC/EO)" and getattr(self, 'current_segment', 1) == 2
            if hasattr(self, 'duration_spinbox'):
                duration_sec = max(1, int(self.segment2_duration if use_segment2 else self.analysis_duration))
                self.duration_spinbox.blockSignals(True)
                self.duration_spinbox.setValue(duration_sec)
                self.duration_spinbox.blockSignals(False)
                QLLogging.log.debug(f"Updated duration_spinbox to: {duration_sec} sec")

            # 更新selection_label
            if hasattr(self, 'selection_label'):
                self.selection_label.setText(
                    f"Selection: {int(self.segment2_duration if use_segment2 else self.analysis_duration)} Sec")

            # 根据采样率更新滤波器上限（Nyquist）
            self._apply_filter_upper_bound()

            # 更新滤波参数spinbox
            if hasattr(self, 'highpass_spinbox') and hasattr(self, 'highpass_checkbox'):
                self.highpass_spinbox.blockSignals(True)
                self.highpass_checkbox.blockSignals(True)
                self.highpass_spinbox.setValue(float(getattr(self, 'highpass_value', 0.8)))
                self.highpass_checkbox.setChecked(bool(getattr(self, 'highpass_enabled', True)))
                self.highpass_spinbox.setEnabled(self.highpass_checkbox.isChecked())
                self.highpass_checkbox.blockSignals(False)
                self.highpass_spinbox.blockSignals(False)
                QLLogging.log.debug(f"Updated highpass_spinbox to: {getattr(self, 'highpass_value', None)} Hz")

            if hasattr(self, 'lowpass_spinbox') and hasattr(self, 'lowpass_checkbox'):
                self.lowpass_spinbox.blockSignals(True)
                self.lowpass_checkbox.blockSignals(True)
                self.lowpass_spinbox.setValue(float(getattr(self, 'lowpass_value', 71.0)))
                self.lowpass_checkbox.setChecked(bool(getattr(self, 'lowpass_enabled', True)))
                self.lowpass_spinbox.setEnabled(self.lowpass_checkbox.isChecked())
                self.lowpass_checkbox.blockSignals(False)
                self.lowpass_spinbox.blockSignals(False)
                QLLogging.log.debug(f"Updated lowpass_spinbox to: {getattr(self, 'lowpass_value', None)} Hz")

            if hasattr(self, 'notch_spinbox') and hasattr(self, 'notch_checkbox'):
                self.notch_spinbox.blockSignals(True)
                self.notch_checkbox.blockSignals(True)
                notch_value = float(getattr(self, 'notch_value', 50.0))
                self.notch_spinbox.setValue(notch_value)
                self.notch_checkbox.setChecked(bool(getattr(self, 'notch_enabled', True)))
                self.notch_spinbox.setEnabled(self.notch_checkbox.isChecked())
                self.notch_checkbox.blockSignals(False)
                self.notch_spinbox.blockSignals(False)
                QLLogging.log.debug(f"Updated notch_spinbox to: {notch_value} Hz")

            # 更新滤波器标签颜色（不触发 update_filter_params）
            try:
                if hasattr(self, 'highpass_label') and hasattr(self, 'highpass_checkbox'):
                    self.highpass_label.setStyleSheet("""
                        QLabel {
                            font-size: 14px;
                            color: %s;
                            font-weight: 500;
                            font-family: Microsoft YaHei;
                        }
                    """ % ("#007ACC" if self.highpass_checkbox.isChecked() else "#999999"))
                if hasattr(self, 'lowpass_label') and hasattr(self, 'lowpass_checkbox'):
                    self.lowpass_label.setStyleSheet("""
                        QLabel {
                            font-size: 14px;
                            color: %s;
                            font-weight: 500;
                            font-family: Microsoft YaHei;
                        }
                    """ % ("#007ACC" if self.lowpass_checkbox.isChecked() else "#999999"))
                if hasattr(self, 'notch_label') and hasattr(self, 'notch_checkbox'):
                    self.notch_label.setStyleSheet("""
                        QLabel {
                            font-size: 14px;
                            color: %s;
                            font-weight: 500;
                            font-family: Microsoft YaHei;
                        }
                    """ % ("#007ACC" if self.notch_checkbox.isChecked() else "#999999"))
            except Exception:
                pass

            # 回显 Quick Bandpass 模式、X/Y 缩放（仅更新下拉框选中项，不触发重计算）
            saved_x = None
            saved_y = None
            try:
                if hasattr(self, 'bandpass_combo'):
                    saved_bandpass = task_config_dict.get('bandpass_mode')
                    if saved_bandpass and saved_bandpass in [self.bandpass_combo.itemText(i) for i in range(self.bandpass_combo.count())]:
                        self.bandpass_combo.blockSignals(True)
                        self.bandpass_combo.setCurrentText(saved_bandpass)
                        self.bandpass_combo.blockSignals(False)
                if hasattr(self, 'plot_combo_x'):
                    saved_x = task_config_dict.get('x_axis_scale')
                    if saved_x and saved_x in [self.plot_combo_x.itemText(i) for i in range(self.plot_combo_x.count())]:
                        self.plot_combo_x.blockSignals(True)
                        self.plot_combo_x.setCurrentText(saved_x)
                        self.plot_combo_x.blockSignals(False)
                if hasattr(self, 'plot_combo_y'):
                    saved_y = task_config_dict.get('y_axis_scale')
                    if saved_y and saved_y in [self.plot_combo_y.itemText(i) for i in range(self.plot_combo_y.count())]:
                        self.plot_combo_y.blockSignals(True)
                        self.plot_combo_y.setCurrentText(saved_y)
                        self.plot_combo_y.blockSignals(False)
            except Exception:
                pass

            # 切换任务时，combo 的信号被阻止不会触发缩放，这里主动同步 X 轴范围
            if saved_x and hasattr(self, 'raw_filtered') and self.raw_filtered is not None:
                try:
                    self.on_plot_combo_changed_x(saved_x)
                except Exception:
                    pass

            # alpha Ratio 切换任务会触发 plot_waveforms，若画布尺寸尚未稳定会导致图像缩小
            # 这里在当前事件循环结束后强制同步一次 figure 尺寸，确保波形占满画布
            try:
                current_method_after_update = self.get_current_analysis_method() if hasattr(self, 'method_combo') else self.analysis_method
                if current_method_after_update == "alpha Ratio(EC/EO)" and hasattr(self, '_sync_figure_size_to_canvas'):
                    QTimer.singleShot(0, self._sync_figure_size_to_canvas)
            except Exception:
                pass

            # 更新时间标签
            if hasattr(self, 'update_time_labels'):
                self.update_time_labels()
                QLLogging.log.debug("Updated time labels")

            # 根据模板中保存的事件名称匹配并选中对应的事件（只有在有保存的事件名称时才执行）
            if hasattr(self, 'event_list') and self.event_list is not None:
                import json
                def _parse_first_event_name(event_names_value):
                    if not event_names_value or not isinstance(event_names_value, str) or not event_names_value.strip():
                        return None
                    raw = event_names_value.strip()
                    # 兼容新格式（纯字符串）与旧格式（JSON 列表字符串）
                    if not (raw.startswith('[') or raw.startswith('{') or raw.startswith('"')):
                        return raw
                    try:
                        parsed = json.loads(raw)
                        if isinstance(parsed, list) and len(parsed) > 0:
                            return parsed[0]
                        if isinstance(parsed, str) and parsed.strip():
                            return parsed.strip()
                    except Exception:
                        return raw
                    return None

                # 读取分子/分母独立事件（兼容旧字段 selected_event_names）
                seg1_name = _parse_first_event_name(task_config_dict.get('selected_event_names_segment1'))
                seg2_name = _parse_first_event_name(task_config_dict.get('selected_event_names_segment2'))
                if seg1_name is None:
                    seg1_name = _parse_first_event_name(task_config_dict.get('selected_event_names'))
                self._selected_event_name_by_segment = {1: seg1_name, 2: seg2_name}

                current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
                target_segment = 2 if (current_method == "alpha Ratio(EC/EO)" and getattr(self, 'current_segment', 1) == 2) else 1
                target_event_name = self._selected_event_name_by_segment.get(target_segment)

                if target_event_name:
                    if self.event_list.count() == 0:
                        self._pending_event_name_to_select = target_event_name
                        self._pending_event_name_warning = True
                        QLLogging.log.info(
                            f"Event list empty, set _pending_event_name_to_select: {target_event_name}")
                    else:
                        # 模板载入/任务切换场景：
                        # - 默认(update_time=True)：按事件重置分析时间窗口
                        # - flag=True 时(update_time=False)：仅恢复事件高亮，不覆盖数据库中已保存的时间
                        # reset_when_missing = not bool(flag)
                        reset_when_missing = not bool(flag)
                        self._select_event_by_name(
                            target_event_name,
                            reset_time_when_not_found=reset_when_missing,
                            show_warning_when_not_found=True,
                            update_time=not bool(flag)
                        )
                else:
                    self._clear_event_selection_visual()

                # alpha Ratio：即使当前停留在分段1，也要同步分段2的事件时间，保证橙色框初始位置正确
                if current_method == "alpha Ratio(EC/EO)" and seg2_name and self.event_list.count() > 0:
                    try:
                        seg2_name_stripped = str(seg2_name).strip()
                        seg2_time = None
                        for ev in self.events:
                            ev_name = str(ev.get('name', '')).strip()
                            if ev_name == seg2_name_stripped:
                                seg2_time = ev.get('time')
                                break
                        if seg2_time is not None:
                            self.segment2_start_time = float(seg2_time)
                            self.segment2_end_time = self.segment2_start_time + float(self.segment2_duration)
                    except Exception as _e:
                        QLLogging.log.debug(f"Failed to sync segment2 time by event: {_e}")

                QLLogging.log.debug("Restored event selection by current segment")

            # 性能优化：切换任务时即使不重绘全图，也要同步更新蓝色分析窗口遮罩
            # 否则会出现“开始/结束时间变了，但蓝色遮罩不动”的问题
            self._update_analysis_rect_only()

            # 强制同步“分析方法相关UI”（如 alpha Ratio 的双段切换区）。
            # 模板载入后 update_config 可能不会触发 currentTextChanged（方法值未变化），
            # 导致 segment_switch_container 仍保持旧状态（首次不显示，需手动切换才出现）。
            current_method_after_update = self.get_current_analysis_method() if hasattr(self, 'method_combo') else self.analysis_method
            if hasattr(self, 'segment_switch_container'):
                should_show_segment_switch = (current_method_after_update == "alpha Ratio(EC/EO)")
                if should_show_segment_switch:
                    self.segment_switch_container.show()
                else:
                    self.segment_switch_container.hide()

            # 性能优化：切换任务时默认只更新UI字段，不自动加载数据/不重滤波重绘
            # 需要刷新波形时，调用方显式传 refresh_plot=True
            if refresh_plot:
                # 如果还没有数据，尝试自动加载
                if self.raw_processed is None:
                    QLLogging.log.debug("raw_processed is None, attempting to auto-load data")
                    self._auto_load_raw_data()

                # 如果已有数据，重新应用滤波并绘制波形
                if self.raw_processed is not None:
                    try:
                        # 如果之前没有导入过数据，现在导入
                        if not hasattr(self, 'channel_names') or len(self.channel_names) == 0:
                            QLLogging.log.debug("Importing raw data for the first time")
                            self.import_raw(self.raw_processed)
                        else:
                            QLLogging.log.debug("Reapplying filter and replotting waveforms")
                            self.apply_filter()
                            self.plot_waveforms()
                            QLLogging.log.debug("Filter and waveforms updated successfully")
                    except Exception as e:
                        QLLogging.log.exception(f"Error updating plot after config change: {e}")
                else:
                    QLLogging.log.warning(
                        "No raw_processed data available after auto-load attempt, skipping filter and plot update")

            QLLogging.log.info(f"Task config updated successfully: {self.task_name} (ID: {self.task_id})")
            # 切换任务后根据该任务是否已配置刷新确认按钮状态
            self.refresh_confirm_button_state()

        except Exception as e:
            QLLogging.log.exception(f"Error updating task config: {e}")
            import traceback
            QLLogging.log.error(f"Update config error traceback: {traceback.format_exc()}")

    def _update_analysis_rect_only(self):
        """仅更新蓝色分析窗口矩形位置/宽度（轻量），不重绘整幅波形。"""
        try:
            # 检查画布是否存在
            if not hasattr(self, "canvas") or self.canvas is None:
                QLLogging.log.debug("Canvas not available, skipping rect update")
                return

            # 检查是否有数据可以绘制
            if not hasattr(self, "raw_filtered") or self.raw_filtered is None:
                QLLogging.log.debug("No filtered data available, skipping rect update")
                return

            # 检查矩形是否存在且有效
            rect_exists = hasattr(self, "analysis_rect") and self.analysis_rect is not None
            rect_valid = False

            if rect_exists:
                rect = self.analysis_rect
                # 检查矩形是否有有效的axes
                if hasattr(rect, "axes") and rect.axes is not None:
                    # 检查axes是否还在figure中（figure.clear()后axes可能被移除）
                    try:
                        ax = rect.axes
                        # 尝试获取ylim，如果能获取说明axes有效
                        ylim = ax.get_ylim()
                        rect_valid = True
                    except Exception:
                        QLLogging.log.debug("Rect axes is invalid, will recreate")
                        rect_valid = False

            # 如果矩形不存在或无效，需要重新创建（通过plot_waveforms）
            if not rect_exists or not rect_valid:
                QLLogging.log.debug("Analysis rect missing or invalid, calling plot_waveforms to recreate")
                self.plot_waveforms()
                return

            # 矩形存在且有效，直接更新位置和大小
            rect = self.analysis_rect
            ax = rect.axes
            ylim = ax.get_ylim()

            # 更新矩形：x=开始时间，宽度=分析时长；y铺满当前y范围
            new_x = float(self.analysis_start_time)
            new_width = float(self.analysis_duration)
            new_y = float(ylim[0])
            new_height = float(ylim[1] - ylim[0])

            # 蓝色矩形独立判断是否需要更新
            current_x = rect.get_x()
            current_width = rect.get_width()
            current_y = rect.get_y()
            current_height = rect.get_height()
            needs_update_analysis_rect = not (
                    abs(current_x - new_x) < 0.01 and
                    abs(current_width - new_width) < 0.01 and
                    abs(current_y - new_y) < 0.01 and
                    abs(current_height - new_height) < 0.01
            )

            if needs_update_analysis_rect:
                QLLogging.log.debug(
                    f"Updating analysis rect: x={current_x}->{new_x}, width={current_width}->{new_width}, y={new_y}, height={new_height}")

                # 使用matplotlib Rectangle的方法更新位置和大小
                # 注意：必须先断开事件连接，更新后再重新连接（避免拖动时冲突）
                was_connected = False
                try:
                    if hasattr(rect, 'cidpress'):
                        rect.disconnect()
                        was_connected = True
                except Exception:
                    pass

                # 更新矩形属性
                rect.set_xy((new_x, new_y))  # 设置位置
                rect.set_width(new_width)  # 设置宽度
                rect.set_height(new_height)  # 设置高度

                # 重新连接事件（如果之前是连接的）
                if was_connected:
                    try:
                        rect.connect()
                    except Exception as e:
                        QLLogging.log.warning(f"Failed to reconnect rect events: {e}")
            else:
                QLLogging.log.debug(
                    f"Analysis rect already at correct position (x={current_x}, width={current_width}), skipping blue rect update")

            # 同步更新橙色 segment2 矩形（分母），逻辑与蓝色矩形一致
            current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
            seg2_updated = False
            if current_method == "alpha Ratio(EC/EO)" and hasattr(self,
                                                                  'segment2_rect') and self.segment2_rect is not None:
                try:
                    seg2_rect = self.segment2_rect
                    if hasattr(seg2_rect, "axes") and seg2_rect.axes is not None:
                        seg2_new_x = float(self.segment2_start_time)
                        seg2_new_width = float(self.segment2_duration)
                        seg2_current_x = seg2_rect.get_x()
                        seg2_current_width = seg2_rect.get_width()
                        seg2_current_y = seg2_rect.get_y()
                        seg2_current_height = seg2_rect.get_height()
                        needs_update_seg2_rect = not (
                                abs(seg2_current_x - seg2_new_x) < 0.01 and
                                abs(seg2_current_width - seg2_new_width) < 0.01 and
                                abs(seg2_current_y - new_y) < 0.01 and
                                abs(seg2_current_height - new_height) < 0.01
                        )

                        if not needs_update_seg2_rect:
                            QLLogging.log.debug(
                                f"Segment2 rect already at correct position (x={seg2_current_x}, width={seg2_current_width}), skipping orange rect update")
                        else:
                            seg2_was_connected = False
                            try:
                                if hasattr(seg2_rect, 'cidpress'):
                                    seg2_rect.disconnect()
                                    seg2_was_connected = True
                            except Exception:
                                pass

                            seg2_rect.set_xy((seg2_new_x, new_y))
                            seg2_rect.set_width(seg2_new_width)
                            seg2_rect.set_height(new_height)
                            seg2_updated = True

                            if seg2_was_connected:
                                try:
                                    seg2_rect.connect()
                                except Exception:
                                    pass

                            QLLogging.log.debug(
                                f"Segment2 rect updated: x={seg2_new_x}, width={seg2_new_width}")
                except Exception as e_seg2:
                    QLLogging.log.warning(f"Failed to update segment2 rect: {e_seg2}")

            # 只有蓝色和橙色都无需更新时才跳过刷新
            if not needs_update_analysis_rect and not seg2_updated:
                return

            # 强制刷新画布（使用draw而不是draw_idle确保立即更新）
            self.canvas.draw()
            # 确保事件立即处理
            self.canvas.flush_events()
            QLLogging.log.debug(f"Analysis rect updated successfully: x={rect.get_x()}, width={rect.get_width()}")
        except Exception as e:
            QLLogging.log.exception(f"Failed to update analysis rect only: {e}")
            import traceback
            QLLogging.log.error(f"Update rect error traceback: {traceback.format_exc()}")
            # 如果更新失败，尝试重新绘制（兜底方案）
            try:
                if hasattr(self, "raw_filtered") and self.raw_filtered is not None:
                    QLLogging.log.debug("Fallback: calling plot_waveforms after update failure")
                    self.plot_waveforms()
            except Exception as e2:
                QLLogging.log.exception(f"Fallback plot_waveforms also failed: {e2}")

    def create_unified_progress_dialog(self, initial_text="处理中..."):
        """创建统一的进度条对话框"""
        from PyQt5.QtWidgets import QProgressDialog, QApplication

        progress_dialog = QProgressDialog(initial_text, None, 0, 100)
        # 核心：设置为应用程序级模态（主界面完全无法操作）
        progress_dialog.setWindowModality(Qt.ApplicationModal)
        progress_dialog.setWindowTitle("加载任务中")
        progress_dialog.setCancelButton(None)  # 不允许取消
        progress_dialog.setMinimumDuration(0)  # 立即显示
        progress_dialog.setValue(0)

        # 设置进度条对话框的尺寸
        progress_dialog.setFixedWidth(500)  # 设置固定宽度为500px
        progress_dialog.setFixedHeight(120)  # 设置固定高度

        # 优化窗口标志：保留模态的同时设置总在最前（修复原代码可能的标志冲突）
        progress_dialog.setWindowFlags(
            Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.WindowTitleHint | Qt.ApplicationModal
        )

        # 美化进度条样式
        progress_dialog.setStyleSheet("""
            QProgressDialog {
                background-color: #FFFFFF;
                border: none ;
                border-radius: 8px;
                padding: 15px;
            }
            QProgressDialog QLabel {
                font-family: Microsoft YaHei;
                color: #333333;
                font-size: 13px;
                ont-weight: 400 ;
                padding: 5px 0px;
                background-color: #FFFFFF;
            }
            QProgressBar {
                font-family: Microsoft YaHei;
                border: none ;
                border-radius: 6px;
                background-color: #F0F0F0 ;
                text-align: center;
                font-size: 11px;
                font-weight: 500;
                color: #333333 ;
                height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #4A90E2, stop: 0.5 #5BA3F5, stop: 1 #6BB6FF);
                border-radius: 6px;
                border: none;
            }
        """)

        QApplication.processEvents()
        return progress_dialog

    def _get_filter_upper_bound(self):
        """滤波器频率上限：采样率的一半（Nyquist）"""
        try:
            if self.sfreq is None:
                return None
            return max(0.1, float(self.sfreq) / 2.0)
        except Exception:
            return None

    def _apply_filter_upper_bound(self):
        """根据采样率更新滤波器上限并裁剪当前值"""
        max_freq = self._get_filter_upper_bound()
        if max_freq is None:
            return

        def _clamp(value):
            if value is None:
                return None
            return min(float(value), max_freq)

        try:
            if hasattr(self, 'highpass_spinbox'):
                self.highpass_spinbox.setMaximum(max_freq)
                if self.highpass_spinbox.value() > max_freq:
                    self.highpass_spinbox.setValue(max_freq)
            if hasattr(self, 'lowpass_spinbox'):
                self.lowpass_spinbox.setMaximum(max_freq)
                if self.lowpass_spinbox.value() > max_freq:
                    self.lowpass_spinbox.setValue(max_freq)
            if hasattr(self, 'notch_spinbox'):
                self.notch_spinbox.setMaximum(max_freq)
                if self.notch_spinbox.value() > max_freq:
                    self.notch_spinbox.setValue(max_freq)
        except Exception:
            pass

        self.highpass_value = _clamp(getattr(self, 'highpass_value', None))
        self.lowpass_value = _clamp(getattr(self, 'lowpass_value', None))
        self.notch_value = _clamp(getattr(self, 'notch_value', None))
        self.highpass = self.highpass_value if getattr(self, 'highpass_enabled', True) else None
        self.lowpass = self.lowpass_value if getattr(self, 'lowpass_enabled', True) else None
        self.notch = self.notch_value if getattr(self, 'notch_enabled', True) else None

    def import_raw(self, raw):
        """导入EDF数据"""
        from PyQt5.QtWidgets import QApplication
        
        if self.skip_plotting:
            progress_dialog = None
        else:
            progress_dialog = self.create_unified_progress_dialog("正在导入数据...")

        def update_progress(label, value):
            if progress_dialog:
                progress_dialog.setLabelText(label)
                progress_dialog.setValue(value)
                QApplication.processEvents()

        try:
            self.raw_processed = raw
            if raw is None:
                QLLogging.log.warning("Raw data is None")
                if progress_dialog:
                    progress_dialog.close()
                return

            update_progress("正在初始化数据...", 5)

            self.channel_names = raw.ch_names
            self.sfreq = raw.info['sfreq']
            self.total_duration = raw.times[-1]

            # 根据采样率更新滤波器上限（Nyquist）
            self._apply_filter_upper_bound()

            update_progress("正在初始化事件列表...", 10)

            try:
                self.init_default_events()
            except Exception as e:
                QLLogging.log.exception(f"Error initializing default events: {e}")
                self.events = []

            update_progress("滤波中...", 15)

            try:
                self.apply_filter()
            except Exception as e:
                QLLogging.log.exception(f"Error applying filter: {e}")
                self.raw_filtered = self.raw_processed.copy() if self.raw_processed else None

            update_progress("FFT计算中...", 30)

            if not self.skip_plotting:
                update_progress("绘图中...", 30)
                try:
                    self.plot_waveforms(progress_dialog, start_progress=30)
                except Exception as e:
                    QLLogging.log.exception(f"Error plotting waveforms: {e}")
                    import traceback
                    QLLogging.log.error(f"Plot error traceback: {traceback.format_exc()}")
            else:
                pass
                
            if progress_dialog:
                update_progress("完成", 100)

            QLLogging.log.info(f"Imported {len(self.channel_names)} channels, duration: {self.total_duration:.2f}s")

        except Exception as e:
            QLLogging.log.exception(f"Error importing raw data: {e}")
            import traceback
            QLLogging.log.error(f"Import error traceback: {traceback.format_exc()}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Import Error", f"Error importing data: {str(e)}\n\nCheck logs for details.")
        finally:
            if progress_dialog:
                progress_dialog.close()

    def init_default_events(self):
        """从BDF文件中读取事件列表，如果无法读取则使用空列表"""
        self.events = []

        QLLogging.log.info("=" * 60)
        QLLogging.log.info("开始初始化事件列表 - init_default_events")
        QLLogging.log.info("=" * 60)

        # 尝试从 raw_processed 中读取 annotations（事件）
        try:
            # 步骤1: 检查 raw_processed 是否存在
            QLLogging.log.info(f"[步骤1] 检查 raw_processed 是否存在: {self.raw_processed is not None}")
            if self.raw_processed is None:
                QLLogging.log.warning("[步骤1] raw_processed 为 None，无法读取事件")
                QLLogging.log.info("=" * 60)
                return

            # 步骤2: 检查 raw_processed 的类型和属性
            QLLogging.log.info(f"[步骤2] raw_processed 类型: {type(self.raw_processed)}")
            QLLogging.log.info(
                f"[步骤2] raw_processed 是否有 annotations 属性: {hasattr(self.raw_processed, 'annotations')}")

            if not hasattr(self.raw_processed, 'annotations'):
                QLLogging.log.warning("[步骤2] raw_processed 没有 annotations 属性，无法读取事件")
                QLLogging.log.info(f"[步骤2] raw_processed 的所有属性: {dir(self.raw_processed)}")
                QLLogging.log.info("=" * 60)
                return

            # 步骤3: 获取 annotations
            annotations = self.raw_processed.annotations
            QLLogging.log.info(f"[步骤3] annotations 是否为 None: {annotations is None}")
            QLLogging.log.info(f"[步骤3] annotations 类型: {type(annotations)}")

            if annotations is None:
                QLLogging.log.warning("[步骤3] annotations 为 None，BDF文件中没有事件")
                QLLogging.log.info("=" * 60)
                return

            # 步骤4: 检查 annotations 的长度和内容
            annotations_len = len(annotations)
            QLLogging.log.info(f"[步骤4] annotations 长度: {annotations_len}")

            if annotations_len == 0:
                QLLogging.log.warning("[步骤4] annotations 长度为 0，BDF文件中没有事件")
                QLLogging.log.info("=" * 60)
                return

            # 步骤5: 检查 annotations 的结构
            QLLogging.log.info(f"[步骤5] annotations 是否有 description 属性: {hasattr(annotations, 'description')}")
            QLLogging.log.info(f"[步骤5] annotations 是否有 onset 属性: {hasattr(annotations, 'onset')}")

            if not hasattr(annotations, 'description') or not hasattr(annotations, 'onset'):
                QLLogging.log.warning("[步骤5] annotations 缺少必要属性（description 或 onset）")
                QLLogging.log.info(f"[步骤5] annotations 的所有属性: {dir(annotations)}")
                QLLogging.log.info("=" * 60)
                return

            # 步骤6: 获取 descriptions 和 onsets
            descriptions = annotations.description
            onsets = annotations.onset
            QLLogging.log.info(
                f"[步骤6] descriptions 类型: {type(descriptions)}, 长度: {len(descriptions) if hasattr(descriptions, '__len__') else 'N/A'}")
            QLLogging.log.info(
                f"[步骤6] onsets 类型: {type(onsets)}, 长度: {len(onsets) if hasattr(onsets, '__len__') else 'N/A'}")

            # 步骤7: 打印前几个事件的详细信息（用于调试）
            debug_count = min(5, annotations_len)
            QLLogging.log.info(f"[步骤7] 前 {debug_count} 个事件的详细信息:")
            for i in range(debug_count):
                try:
                    onset = onsets[i]
                    description = descriptions[i]
                    QLLogging.log.info(
                        f"  事件 {i + 1}: onset={onset} (类型: {type(onset)}), description={description} (类型: {type(description)})")
                except Exception as e:
                    QLLogging.log.warning(f"  事件 {i + 1} 读取失败: {e}")

            # 步骤8: 读取所有事件
            QLLogging.log.info(f"[步骤8] 开始读取所有 {annotations_len} 个事件...")
            events_read_count = 0

            for i in range(annotations_len):
                try:
                    onset = float(onsets[i])  # 事件发生时间（秒）
                    description = descriptions[i]  # 事件名称

                    # 将 description 转换为字符串（处理各种可能的格式）
                    if isinstance(description, (bytes, bytearray)):
                        event_name = description.decode('utf-8', errors='ignore')
                    elif isinstance(description, np.ndarray):
                        # 如果是numpy数组，尝试获取标量值
                        if description.size == 1:
                            event_name = str(description.item())
                        else:
                            event_name = str(description)
                    elif isinstance(description, (list, tuple)):
                        # 如果是列表或元组，取第一个元素
                        event_name = str(description[0]) if len(description) > 0 else ""
                    else:
                        event_name = str(description)

                    # 格式化时间为 "分:秒" 格式
                    minutes = int(onset // 60)
                    seconds = int(onset % 60)
                    formatted_time = f"{minutes}:{seconds:02d}"

                    # 添加到事件列表
                    self.events.append({
                        "name": event_name,
                        "time": onset,
                        "formatted": formatted_time
                    })
                    events_read_count += 1

                    # 记录前几个事件的详细信息
                    if i < 3:
                        QLLogging.log.info(
                            f"  成功读取事件 {i + 1}: name='{event_name}', time={onset}s, formatted='{formatted_time}'")

                except Exception as e:
                    QLLogging.log.warning(f"  读取事件 {i + 1} 时出错: {e}")
                    import traceback
                    QLLogging.log.debug(f"  事件 {i + 1} 错误详情: {traceback.format_exc()}")

            # 步骤9: 总结
            QLLogging.log.info(f"[步骤9] 事件读取完成: 成功读取 {events_read_count}/{annotations_len} 个事件")
            QLLogging.log.info(f"[步骤9] 最终事件列表长度: {len(self.events)}")

            if len(self.events) > 0:
                QLLogging.log.info(f"[步骤9] 事件列表内容预览:")
                for i, event in enumerate(self.events[:5]):  # 只显示前5个
                    QLLogging.log.info(f"  [{i + 1}] {event['formatted']} - {event['name']}")
                if len(self.events) > 5:
                    QLLogging.log.info(f"  ... 还有 {len(self.events) - 5} 个事件")
            else:
                QLLogging.log.warning("[步骤9] 事件列表为空，没有成功读取任何事件")

        except Exception as e:
            QLLogging.log.exception(f"[异常] 读取BDF文件事件时出错: {e}")
            import traceback
            QLLogging.log.error(f"[异常] 完整错误堆栈:\n{traceback.format_exc()}")
            # 如果读取失败，使用空列表
            self.events = []

        QLLogging.log.info("=" * 60)
        QLLogging.log.info(f"事件列表初始化完成，最终事件数量: {len(self.events)}")
        QLLogging.log.info("=" * 60)

        # 保存需要匹配的事件名称（在事件列表创建后使用）
        # 只有在任务有保存的事件名称时才设置待匹配的事件名称
        self._pending_event_name_to_select = None
        if hasattr(self, 'task_id') and self.task_id:
            try:
                from ...Domain.OPLog.Task import Task
                from ...Infrastructure.DB.SQLLiteAccessor import SQLLiteDB_Only_MainTread
                task = Task.get_by_id(SQLLiteDB_Only_MainTread.user_db, self.task_id)
                # 只有在有有效的事件名称时才设置待匹配的事件名称（分子/分母独立）
                if task:
                    import json

                    def _parse_first_event_name(event_names_value):
                        if not event_names_value or not isinstance(event_names_value, str) or not event_names_value.strip():
                            return None
                        raw = event_names_value.strip()
                        # 兼容新格式（纯字符串）与旧格式（JSON 列表字符串）
                        if not (raw.startswith('[') or raw.startswith('{') or raw.startswith('"')):
                            return raw
                        try:
                            parsed = json.loads(raw)
                            if isinstance(parsed, list) and len(parsed) > 0:
                                return parsed[0]
                            if isinstance(parsed, str) and parsed.strip():
                                return parsed.strip()
                        except Exception:
                            return raw
                        return None

                    seg1_name = _parse_first_event_name(getattr(task, 'selected_event_names_segment1', None))
                    seg2_name = _parse_first_event_name(getattr(task, 'selected_event_names_segment2', None))
                    if seg1_name is None:
                        seg1_name = _parse_first_event_name(getattr(task, 'selected_event_names', None))
                    self._selected_event_name_by_segment = {1: seg1_name, 2: seg2_name}

                    target_segment = 2 if (
                            self.get_current_analysis_method() == "alpha Ratio(EC/EO)" and getattr(self, 'current_segment', 1) == 2) else 1
                    self._pending_event_name_to_select = self._selected_event_name_by_segment.get(target_segment)
            except Exception as e:
                QLLogging.log.warning(f"Failed to load task event names: {e}")

        print(self._pending_event_name_to_select)

        self.event_list.clear()
        for event in self.events:
            # 创建自定义widget，垂直布局
            item_widget = QWidget()
            item_widget.setObjectName("eventItemWidget")  # 设置对象名称用于精确样式选择
            item_widget.setFixedHeight(62)  # 只固定高度，宽度自适应
            item_widget.setStyleSheet("""
                QWidget#eventItemWidget {
                    background-color: white;
                    border-radius: 8px;
                    border: none;
                }
            """)
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(12, 10, 12, 10)
            item_layout.setSpacing(4)

            # 时间标签（上面）
            time_label = QLabel(event['formatted'])
            time_label.setStyleSheet("""
                QLabel {
                    font-weight: 400;
                    font-size: 12px;
                    color: #2A87DB;
                    background-color: transparent;
                    border: none;
                }
            """)
            item_layout.addWidget(time_label)

            # 事件名称标签（下面）
            name_label = QLabel(event['name'])
            name_label.setStyleSheet("""
                QLabel {
                    font-family: Microsoft YaHei;
                    font-weight: 400;
                    font-size: 14px;
                    color: #31373D;
                    background-color: transparent;
                    border: none;
                }
            """)
            # 设置标签文本省略模式，超出部分显示省略号
            name_label.setWordWrap(False)
            name_label.setTextFormat(Qt.PlainText)
            # 计算合适的宽度（列表宽度减去左右边距和滚动条宽度）
            list_width = self.event_list.width() if self.event_list.width() > 0 else 300
            available_width = list_width - 24 - 20  # 减去左右边距(12*2)和滚动条宽度(约20)
            name_label.setMaximumWidth(available_width)
            name_label.setMinimumWidth(available_width)
            # 使用省略号显示超长文本
            fm = name_label.fontMetrics()
            elided_text = fm.elidedText(event['name'], Qt.ElideRight, available_width)
            name_label.setText(elided_text)
            item_layout.addWidget(name_label)
            item_layout.addStretch()

            # 创建QListWidgetItem并设置widget
            item = QListWidgetItem()
            # 宽度设置为列表宽度减去滚动条宽度（约20px）和边距（10px）
            item_width = max(200, list_width - 30)  # 最小宽度200，确保不会太小
            item.setSizeHint(QSize(item_width, 62))
            self.event_list.addItem(item)
            self.event_list.setItemWidget(item, item_widget)

        # 确保初始化时没有任何项目被选中
        self.event_list.clearSelection()
        self.event_list.setCurrentRow(-1)

        # 重置所有项目的样式为非选中状态
        for i in range(self.event_list.count()):
            list_item = self.event_list.item(i)
            item_widget = self.event_list.itemWidget(list_item)
            if item_widget:
                item_widget.setStyleSheet("""
                    QWidget#eventItemWidget {
                        background-color: white;
                        border-radius: 8px;
                        border: none;
                    }
                """)

        # 事件列表创建完成后，如果有待匹配的事件名称，则选中对应的事件
        if hasattr(self, '_pending_event_name_to_select') and self._pending_event_name_to_select:
            from PyQt5.QtCore import QTimer
            pending_name = self._pending_event_name_to_select
            warn_flag = getattr(self, '_pending_event_name_warning', False)
            self._pending_event_name_to_select = None
            self._pending_event_name_warning = False
            QTimer.singleShot(
                100,
                lambda name=pending_name, warn=warn_flag: self._select_event_by_name(
                    name,
                    show_warning_when_not_found=warn
                )
            )

    def _clear_event_selection_visual(self):
        """仅清空事件列表选中态和样式，不改时间参数。"""
        if not hasattr(self, 'event_list') or self.event_list is None:
            return
        self.event_list.clearSelection()
        self.event_list.setCurrentRow(-1)
        for i in range(self.event_list.count()):
            list_item = self.event_list.item(i)
            item_widget = self.event_list.itemWidget(list_item)
            if item_widget:
                item_widget.setStyleSheet("""
                    QWidget#eventItemWidget {
                        background-color: white;
                        border-radius: 8px;
                        border: none;
                    }
                """)

    def _clear_event_binding_for_current_segment(self):
        """手动修改时间后，取消当前分段与事件的绑定和高亮。"""
        # 若尚未初始化事件绑定结构，直接返回
        if not hasattr(self, '_selected_event_name_by_segment'):
            return
        try:
            current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
            is_alpha_ratio = current_method == "alpha Ratio(EC/EO)"
        except Exception:
            current_method = ""
            is_alpha_ratio = False

        # 根据当前方法/分段确定需要清除的分段索引
        segment = 2 if (is_alpha_ratio and getattr(self, 'current_segment', 1) == 2) else 1
        self._selected_event_name_by_segment[segment] = None
        # 清空事件列表的高亮状态
        self._clear_event_selection_visual()

    def _select_event_by_name(self, event_name, reset_time_when_not_found=True,
                              show_warning_when_not_found=False, update_time=True):
        """
        根据事件名称选中对应的事件
        
        参数:
            event_name: 要选中的事件名称（字符串）
            reset_time_when_not_found: 找不到事件时是否重置时间窗口
            show_warning_when_not_found: 找不到事件时是否弹出提示
        """
        if not event_name or not isinstance(event_name, str):
            QLLogging.log.warning(f"Invalid event name for selection: {event_name}")
            return

        if not hasattr(self, 'event_list') or self.event_list is None:
            QLLogging.log.warning("Event list not available for event selection")
            return

        if not hasattr(self, 'events') or not self.events:
            QLLogging.log.warning("Events data not available for event selection")
            return

        # 在当前事件列表中查找匹配的事件名称（忽略首尾空格，兼容模版保存与列表项名称）
        event_name_stripped = str(event_name).strip() if event_name else ""
        matched = False
        for i in range(self.event_list.count()):
            if i < len(self.events):
                event = self.events[i]
                ev_name = event.get('name')
                ev_name_stripped = str(ev_name).strip() if ev_name else ""
                if ev_name_stripped == event_name_stripped:
                    # 找到匹配的事件，选中它
                    list_item = self.event_list.item(i)
                    if list_item is not None:
                        self.event_list.setCurrentItem(list_item)
                        if update_time or self.is_init: # 判断刷新事件 若为第一次载入则刷新
                            # 触发完整事件选中逻辑（包含时间同步）
                            self.on_event_selected(list_item)
                            self.is_init = False
                        else:
                            # 仅恢复高亮样式，不改动当前分析时间（用于任务切换后的回显）
                            self._suppress_time_update_on_event_select = True
                            try:
                                self.on_event_selected(list_item)
                            finally:
                                self._suppress_time_update_on_event_select = False
                        QLLogging.log.info(
                            f"Matched and selected event by name: {event_name} (time: {event.get('time', 'N/A')}s)")
                        matched = True
                        break

        if not matched:
            QLLogging.log.warning(f"Event with name '{event_name}' not found in current event list")
            self._clear_event_selection_visual()

            # 模板载入等场景下，提示当前数据中不存在该事件
            if show_warning_when_not_found and event_name_stripped:
                try:
                    # 发送信号
                    self.err_msg_signal.emit(f"任务{self.task_name}:该数据没有 {event_name_stripped} 事件\n")
                except Exception as e:
                    QLLogging.log.warning(f"Failed to show missing-event message box: {e}")

            if not reset_time_when_not_found:
                return
            #检测是否是alpha事件，如果没有这个事件，那么分段2也重置
            try:
                current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
                is_alpha_ratio = current_method == "alpha Ratio(EC/EO)"
            except Exception:
                current_method = ""
                is_alpha_ratio = False

            # 确定当前操作的分段
            current_segment = getattr(self, 'current_segment', 1) if is_alpha_ratio else 1
            # 如果找不到匹配的事件，将分段1时间重置为默认值（保持旧行为）
            default_start_time = 0
            default_end_time = 120
            default_duration = default_end_time - default_start_time

            if is_alpha_ratio and current_segment == 2:
            # 重置分段2的时间参数
                self.segment2_start_time = default_start_time
                self.segment2_end_time = default_end_time
                self.segment2_duration = default_duration
                QLLogging.log.info(f"Reset segment 2 time to default: start={default_start_time}, end={default_end_time}, duration={default_duration}")
            else:
            # 重置分段1的时间参数
                self.analysis_start_time = default_start_time
                self.analysis_end_time = default_end_time
                self.analysis_duration = default_duration
            QLLogging.log.info(f"Reset segment 1 time to default: start={default_start_time}, end={default_end_time}, duration={default_duration}")
            # 更新时间标签显示
            if hasattr(self, 'update_time_labels'):
                self.update_time_labels()

            # 更新UI元素
            if hasattr(self, 'start_spinbox'):
                self.start_spinbox.blockSignals(True)
                self.start_spinbox.setValue(default_start_time)
                self.start_spinbox.blockSignals(False)

            if hasattr(self, 'duration_spinbox'):
                self.duration_spinbox.blockSignals(True)
                self.duration_spinbox.setValue(default_duration)
                self.duration_spinbox.blockSignals(False)

            if hasattr(self, 'end_spinbox'):
                self.end_spinbox.blockSignals(True)
                self.end_spinbox.setValue(default_end_time)
                self.end_spinbox.blockSignals(False)

            # 更新蓝色分析窗口矩形的位置
            if hasattr(self, '_update_analysis_rect_only'):
                self._update_analysis_rect_only()

            QLLogging.log.info(
                f"Reset analysis time to default: start={default_start_time}s, end={default_end_time}s, duration={default_duration}s")

    def on_highpass_toggle(self, state):
        """High-pass开关状态改变"""
        enabled = state == Qt.Checked
        if hasattr(self, 'highpass_spinbox'):
            self.highpass_spinbox.setEnabled(enabled)
            # 更新标签颜色
            if hasattr(self, 'highpass_label'):
                if enabled:
                    self.highpass_label.setStyleSheet("""
                        QLabel {
                            font-size: 14px;
                            color: #007ACC;
                            font-weight: 500;
                            font-family: Microsoft YaHei;
                        }
                    """)
                else:
                    self.highpass_label.setStyleSheet("""
                        QLabel {
                            font-size: 14px;
                            color: #999999;
                            font-weight: 500;
                            font-family: Microsoft YaHei;
                        }
                    """)
        self.update_filter_params()

    def on_lowpass_toggle(self, state):
        """Low-pass开关状态改变"""
        enabled = state == Qt.Checked
        if hasattr(self, 'lowpass_spinbox'):
            self.lowpass_spinbox.setEnabled(enabled)
            # 更新标签颜色
            if hasattr(self, 'lowpass_label'):
                if enabled:
                    self.lowpass_label.setStyleSheet("""
                        QLabel {
                            font-size: 14px;
                            color: #007ACC;
                            font-weight: 500;
                            font-family: Microsoft YaHei;
                        }
                    """)
                else:
                    self.lowpass_label.setStyleSheet("""
                        QLabel {
                            font-size: 14px;
                            color: #999999;
                            font-weight: 500;
                            font-family: Microsoft YaHei;
                        }
                    """)
        self.update_filter_params()

    def on_notch_toggle(self, state):
        """Notch开关状态改变"""
        enabled = state == Qt.Checked
        if hasattr(self, 'notch_spinbox'):
            self.notch_spinbox.setEnabled(enabled)
            # 更新标签颜色
            if hasattr(self, 'notch_label'):
                if enabled:
                    self.notch_label.setStyleSheet("""
                        QLabel {
                            font-size: 14px;
                            color: #007ACC;
                            font-weight: 500;
                            font-family: Microsoft YaHei;
                        }
                    """)
                else:
                    self.notch_label.setStyleSheet("""
                        QLabel {
                            font-size: 14px;
                            color: #999999;
                            font-weight: 500;
                            font-family: Microsoft YaHei;
                        }
                    """)
        self.update_filter_params()

    def _update_x_scrollbar_range(self, total_time, visible_window):
        """根据总时长与可见窗口更新 X 轴滚动条范围；滚动条始终显示（含 Auto 全量显示时）"""
        if not hasattr(self, 'x_scrollbar') or self.x_scrollbar is None:
            return
        try:
            if total_time > visible_window:
                max_scroll = int((total_time - visible_window) * 10)
                self.x_scrollbar.setMaximum(max(0, max_scroll))
                self.x_scrollbar.setPageStep(int(visible_window * 10))
                self.x_scrollbar.setValue(0)
            else:
                self.x_scrollbar.setMaximum(0)
                self.x_scrollbar.setValue(0)
            self.x_scrollbar.setVisible(True)  # 始终显示滚动条（含 Auto 时）
        except Exception as e:
            QLLogging.log.exception(f"Error in _update_x_scrollbar_range: {e}")

    def on_x_scroll(self, value, visible_window=None):
        """处理X轴滚动条滚动事件"""
        try:
            if not hasattr(self, 'figure') or self.figure is None:
                return

            # 获取当前axes
            axes = self.figure.get_axes()
            if not axes:
                return
            ax = axes[0]

            # 解析滚动条值，计算新的x轴范围（与你原有滚动逻辑一致，*10还原为实际时间）
            scroll_time = value / 10.0

            if visible_window is not None:
                self.visible_window = visible_window

            # 计算新的x轴起始/结束值
            new_x_min = scroll_time
            new_x_max = scroll_time + self.visible_window

            # 1. 更新父图ax的x轴范围（核心驱动）
            ax.set_xlim(new_x_min, new_x_max)
            ax.margins(x=0, y=0)  # 确保父图始终无留白

            # 2. 【核心】批量更新所有inside_ax的x轴范围，与ax完全同步
            for inside_ax in self.inside_axes:
                if inside_ax is not None:
                    inside_ax.set_xlim(new_x_min, new_x_max)  # 跟随父图ax
                    inside_ax.margins(x=0, y=0.05)  # 保持x轴无留白，y轴小边距

            # 3. 强制重绘画布，立即生效
            self.figure.canvas.draw_idle()
            QLLogging.log.debug(f"Scrolled to x: {new_x_min:.1f} - {new_x_max:.1f}s")

        except Exception as e:
            QLLogging.log.exception(f"Error in on_x_scroll: {e}")

    def update_filter_params(self):
        """更新滤波参数"""
        # skip_plotting模式下直接返回，不执行滤波和绘图（用于模板加载场景）
        if getattr(self, 'skip_plotting', False):
            QLLogging.log.debug("Skipping update_filter_params in skip_plotting mode")
            return
            
        # 只要用户手动改动了HP/LP/Notch等参数（包括开关或数值），
        # Quick Bandpass 显示应自动切回 Custom（但不能触发 on_bandpass_changed 去覆盖用户参数）
        try:
            applying_preset = getattr(self, "_applying_bandpass_preset", False)
            if (not applying_preset) and hasattr(self, "bandpass_combo"):
                # if self.bandpass_combo.currentText() != "Custom (0.5-30.0Hz)":
                #     self.bandpass_combo.blockSignals(True)
                #     self.bandpass_combo.setCurrentText("Custom (0.5-30.0Hz)")
                #     self.bandpass_combo.blockSignals(False)
                # 关键：如果之前模式（如 Theta）曾强制禁用输入框，
                # 切到 Custom 后应按“开关是否勾选”来决定输入框是否可调
                # if self.bandpass_combo.currentText() == "Custom (0.5-30.0Hz)":
                if hasattr(self, "highpass_spinbox") and hasattr(self, "highpass_checkbox"):
                    self.highpass_spinbox.setEnabled(self.highpass_checkbox.isChecked())
                if hasattr(self, "lowpass_spinbox") and hasattr(self, "lowpass_checkbox"):
                    self.lowpass_spinbox.setEnabled(self.lowpass_checkbox.isChecked())
                if hasattr(self, "notch_spinbox") and hasattr(self, "notch_checkbox"):
                    self.notch_spinbox.setEnabled(self.notch_checkbox.isChecked())
                # else:
                #     # 非 Custom 的预设模式：像 Theta 一样，禁止修改 HP/LP 数值
                #     if hasattr(self, "highpass_spinbox"):
                #         self.highpass_spinbox.setEnabled(False)
                #     if hasattr(self, "lowpass_spinbox"):
                #         self.lowpass_spinbox.setEnabled(False)
        except Exception:
            # 这里不影响滤波主流程
            pass

        # 从DoubleSpinBox获取High-pass值（如果启用）
        if hasattr(self, 'highpass_spinbox') and hasattr(self, 'highpass_checkbox'):
            self.highpass_value = float(self.highpass_spinbox.value())
            if self.highpass_checkbox.isChecked():
                self.highpass = self.highpass_value
            else:
                self.highpass = None  # 禁用时设为None（但 value 保留）

        # 从DoubleSpinBox获取Low-pass值（如果启用）
        if hasattr(self, 'lowpass_spinbox') and hasattr(self, 'lowpass_checkbox'):
            self.lowpass_value = float(self.lowpass_spinbox.value())
            if self.lowpass_checkbox.isChecked():
                self.lowpass = self.lowpass_value
            else:
                self.lowpass = None  # 禁用时设为None（但 value 保留）

        # 从DoubleSpinBox获取Notch值（如果启用）
        if hasattr(self, 'notch_spinbox') and hasattr(self, 'notch_checkbox'):
            self.notch_value = float(self.notch_spinbox.value())
            if self.notch_checkbox.isChecked():
                self.notch = self.notch_value
            else:
                self.notch = None  # 禁用时设为None（但 value 保留）

        # 为了让用户“一点击就立刻看到进度条”，
        # 在执行耗时的滤波和绘图之前，先创建并显示进度对话框。
        from PyQt5.QtWidgets import QProgressDialog, QApplication

        progress_dialog = QProgressDialog("正在更新滤波并绘制波形图...", None, 0, 100, self)
        # 核心：设置为应用程序级模态（主界面完全无法操作）
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setCancelButton(None)  # 不允许取消
        progress_dialog.setMinimumDuration(0)  # 立即显示
        progress_dialog.setValue(0)

        # 设置进度条对话框的尺寸（更长更宽）
        progress_dialog.setFixedWidth(500)  # 设置固定宽度为500px
        progress_dialog.setFixedHeight(120)  # 设置固定高度

        # 美化进度条样式（与plot_waveforms内部保持一致）
        progress_dialog.setStyleSheet("""
            QProgressDialog {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 20px;
            }
            QProgressDialog QLabel {
                font-family: Microsoft YaHei;
                color: #333333;
                font-size: 14px;
                font-weight: 500;
                padding: 5px 0px;
            }
            QProgressBar {
                font-family: Microsoft YaHei;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                background-color: #F5F5F5;
                text-align: center;
                font-size: 12px;
                font-weight: 500;
                color: #666666;
                height: 28px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #4A90E2, stop: 0.5 #5BA3F5, stop: 1 #6BB6FF);
                border-radius: 6px;
                border: none;
            }
        """)

        # 优化窗口标志：保留模态的同时设置总在最前（修复原代码可能的标志冲突）
        progress_dialog.setWindowFlags(
            Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.WindowTitleHint | Qt.ApplicationModal
        )

        QApplication.processEvents()

        try:
            # 先应用滤波（可能比较耗时）
            progress_dialog.setLabelText("绘图中...")
            progress_dialog.setValue(30)
            QApplication.processEvents()
            self.apply_filter()

            # 再进入原有的绘图流程（传递进度条，绘图阶段占60%-100%）
            progress_dialog.setLabelText("绘图中...")
            progress_dialog.setValue(60)
            QApplication.processEvents()

            # 传递进度条给plot_waveforms，绘图阶段的进度会映射到60%-100%
            self.plot_waveforms(progress_dialog)

            progress_dialog.setLabelText("完成")
            progress_dialog.setValue(100)
            QApplication.processEvents()
        finally:
            progress_dialog.close()

    def on_bandpass_changed(self, text):
        """快速带通选择改变"""
        # 定义各模式的滤波参数：(highpass, lowpass, notch_enabled)
        bandpass_map = {
            "Delta (0.5-4.0Hz)": (0.5, 4.0, True),
            "Theta (4.0-8.0Hz)": (4.0, 8.0, True),
            "Alpha (8.0-13.0Hz)": (8.0, 13.0, True),
            "SMR (12.0-15.0Hz)": (12.0, 15.0, True),
            "Beta (13.0-30.0Hz)": (13.0, 30.0, True),
            "Custom (0.5-30.0Hz)": (0.5, 30.0, True)  # Custom模式：HP=0.5, LP=30, Notch默认ON
        }

        if text in bandpass_map:
            hp, lp, notch_enabled = bandpass_map[text]
            # 记录当前 Quick Bandpass 模式，作为任务配置的一部分
            self.bandpass_mode = text

            # 临时阻止信号触发，避免多次调用 update_filter_params 导致多个进度条
            self._applying_bandpass_preset = True
            # 设置High-pass值并启用
            if hasattr(self, 'highpass_spinbox') and hasattr(self, 'highpass_checkbox'):
                self.highpass_spinbox.blockSignals(True)
                self.highpass_checkbox.blockSignals(True)
                self.highpass_spinbox.setValue(hp)
                self.highpass_checkbox.setChecked(True)
                self.highpass_spinbox.blockSignals(False)
                self.highpass_checkbox.blockSignals(False)

            # 设置Low-pass值并启用
            if hasattr(self, 'lowpass_spinbox') and hasattr(self, 'lowpass_checkbox'):
                self.lowpass_spinbox.blockSignals(True)
                self.lowpass_checkbox.blockSignals(True)
                self.lowpass_spinbox.setValue(lp)
                self.lowpass_checkbox.setChecked(True)
                self.lowpass_spinbox.blockSignals(False)
                self.lowpass_checkbox.blockSignals(False)

            # 设置Notch状态
            if hasattr(self, 'notch_checkbox') and hasattr(self, 'notch_spinbox'):
                self.notch_checkbox.blockSignals(True)
                self.notch_checkbox.setChecked(notch_enabled)
                self.notch_spinbox.setEnabled(notch_enabled)
                self.notch_checkbox.blockSignals(False)
                # 手动更新 Notch 标签颜色（因为信号被阻止了）
                if hasattr(self, 'notch_label'):
                    if notch_enabled:
                        self.notch_label.setStyleSheet("""
                            QLabel {
                                font-size: 14px;
                                color: #007ACC;
                                font-weight: 500;
                                font-family: Microsoft YaHei;
                            }
                        """)
                    else:
                        self.notch_label.setStyleSheet("""
                            QLabel {
                                font-size: 14px;
                                color: #999999;
                                font-weight: 500;
                                font-family: Microsoft YaHei;
                            }
                        """)

            # 行为规则：
            # - 非 Custom 的所有预设模式：像 Theta 一样，禁止修改 HP/LP 数值（输入框禁用）
            # - Custom 模式：只要对应开关启用，就允许修改
            # if text == "Custom (0.5-30.0Hz)":
            if hasattr(self, 'highpass_spinbox') and hasattr(self, 'highpass_checkbox'):
                self.highpass_spinbox.setEnabled(self.highpass_checkbox.isChecked())
            if hasattr(self, 'lowpass_spinbox') and hasattr(self, 'lowpass_checkbox'):
                self.lowpass_spinbox.setEnabled(self.lowpass_checkbox.isChecked())
            # else:
            #     if hasattr(self, 'highpass_spinbox'):
            #         self.highpass_spinbox.setEnabled(False)
            #     if hasattr(self, 'lowpass_spinbox'):
            #         self.lowpass_spinbox.setEnabled(False)

            # 只调用一次 update_filter_params，只产生一个进度条
            try:
                self.update_filter_params()
            finally:
                self._applying_bandpass_preset = False

    # 滤波的使用
    def apply_filter(self):
        """应用滤波"""
        if self.raw_processed is None:
            return

        try:
            # 复制数据以避免修改原始数据
            self.raw_filtered = self.raw_processed.copy()

            # 应用带通滤波（如果参数有效）
            # l_freq和h_freq可以是None，表示不过滤该方向

            # self.lowpass = 40  :去掉 40 Hz 以上的成分
            # 'iir' → 无限冲激响应滤波器
            self.raw_filtered.filter(
                l_freq=self.highpass,
                h_freq=self.lowpass,
                method='iir',
                iir_params={'order': 4, 'ftype': 'butter'}
            )

            # 应用Notch滤波（如果启用）
            if self.notch is not None:
                self.raw_filtered.notch_filter(
                    freqs=self.notch,
                    method='iir',
                    iir_params={'order': 4, 'ftype': 'butter'}
                )

            hp_str = f"{self.highpass:.1f}" if self.highpass is not None else "off"
            lp_str = f"{self.lowpass:.1f}" if self.lowpass is not None else "off"
            notch_str = f"{self.notch:.1f}" if self.notch is not None else "off"
            QLLogging.log.debug(f"Applied filter: High-pass={hp_str} Hz, Low-pass={lp_str} Hz, Notch={notch_str} Hz")

        except Exception as e:
            QLLogging.log.exception(f"Error applying filter: {e}")
            self.raw_filtered = self.raw_processed

    def update_analysis_window(self):
        """更新分析窗口参数"""
        try:
            duration_sec = self.duration_spinbox.value()

            # 检查是否是alpha Ratio方法且选中了分段2
            current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
            is_alpha_ratio = current_method == "alpha Ratio(EC/EO)"

            if is_alpha_ratio and self.current_segment == 2:
                # 更新分段2的参数
                self.segment2_duration = duration_sec
                self.segment2_end_time = self.segment2_start_time + self.segment2_duration
                QLLogging.log.info(
                    f"Updating segment2 window: duration={self.segment2_duration}s, start={self.segment2_start_time}s, end={self.segment2_end_time}s")
            else:
                # 更新分段1的参数
                self.analysis_duration = duration_sec
                self.analysis_end_time = self.analysis_start_time + self.analysis_duration
                QLLogging.log.info(
                    f"Updating analysis window: duration={self.analysis_duration}s, start={self.analysis_start_time}s, end={self.analysis_end_time}s")

            # 更新selection_label
            if hasattr(self, 'selection_label'):
                self.selection_label.setText(f"Selection: {duration_sec} Sec")

            # 更新显示标签
            self.update_time_labels()

            # 确保有数据可以绘制
            if self.raw_filtered is None:
                QLLogging.log.warning("Cannot update window: no filtered data available")
                return

            # 重新绘制
            self.plot_waveforms()

            QLLogging.log.info(f"Analysis window updated successfully")
        except Exception as e:
            QLLogging.log.exception(f"Error in update_analysis_window: {e}")

    def on_start_time_changed(self, value):
        """开始时间改变时的处理（保持持续时间不变，end = start + duration）"""
        try:
            current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
            is_alpha_ratio = current_method == "alpha Ratio(EC/EO)"
            # 文件总时长（秒），用于约束 start 与 start+duration 不超过记录时长
            total = getattr(self, 'total_duration', 0)
            has_total = total is not None and total > 0

            # 手动修改开始时间时，当前分段不再与事件时间严格对齐，取消事件绑定与高亮
            if hasattr(self, '_clear_event_binding_for_current_segment'):
                self._clear_event_binding_for_current_segment()

            if is_alpha_ratio and self.current_segment == 2:
                # 分段2：约束 start 与 start+duration
                start = int(value)
                duration = int(self.segment2_duration) if getattr(self, 'segment2_duration', None) is not None else 1
                if duration <= 0:
                    duration = 1
                if has_total:
                    # 若 duration 大于总时长，则最多只显示 total-1 秒
                    if duration >= total:
                        duration = max(1, int(total) - 1)
                        self.segment2_duration = duration
                    max_start = max(0, int(total) - duration)
                    start = max(0, min(start, max_start))
                # 若发生截断，回写到 spinbox，保证 UI 与内部一致
                if hasattr(self, 'start_spinbox') and start != value:
                    self.start_spinbox.blockSignals(True)
                    self.start_spinbox.setValue(int(start))
                    self.start_spinbox.blockSignals(False)
                self.segment2_start_time = start
                self.segment2_end_time = self.segment2_start_time + self.segment2_duration
                if hasattr(self, 'end_spinbox'):
                    self.end_spinbox.blockSignals(True)
                    self.end_spinbox.setValue(int(self.segment2_end_time))
                    self.end_spinbox.blockSignals(False)
                QLLogging.log.info(
                    f"Segment2 start time changed: start={self.segment2_start_time}s, duration={self.segment2_duration}s, end={self.segment2_end_time}s")
            else:
                # 普通分析窗口：约束 start 与 start+duration
                start = int(value)
                duration = int(self.analysis_duration) if getattr(self, 'analysis_duration', None) is not None else 1
                if duration <= 0:
                    duration = 1
                if has_total:
                    if duration >= total:
                        duration = max(1, int(total) - 1)
                        self.analysis_duration = duration
                    max_start = max(0, int(total) - duration)
                    start = max(0, min(start, max_start))
                if hasattr(self, 'start_spinbox') and start != value:
                    self.start_spinbox.blockSignals(True)
                    self.start_spinbox.setValue(int(start))
                    self.start_spinbox.blockSignals(False)
                self.analysis_start_time = start
                self.analysis_end_time = self.analysis_start_time + self.analysis_duration
                if hasattr(self, 'end_spinbox'):
                    self.end_spinbox.blockSignals(True)
                    self.end_spinbox.setValue(int(self.analysis_end_time))
                    self.end_spinbox.blockSignals(False)
                QLLogging.log.info(
                    f"Analysis start time changed: start={self.analysis_start_time}s, duration={self.analysis_duration}s, end={self.analysis_end_time}s")

            if hasattr(self, 'selection_label'):
                if is_alpha_ratio and self.current_segment == 2:
                    self.selection_label.setText(f"Selection: {int(self.segment2_duration)} Sec")
                else:
                    self.selection_label.setText(f"Selection: {int(self.analysis_duration)} Sec")

            self._update_rect_position()

        except Exception as e:
            QLLogging.log.exception(f"Error in on_start_time_changed: {e}")

    def on_duration_changed(self, value):
        """持续时间改变时的处理（end = start + duration）"""
        try:
            current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
            is_alpha_ratio = current_method == "alpha Ratio(EC/EO)"
            # 文件总时长（秒），用于约束 start 与 start+duration 不超过记录时长
            total = getattr(self, 'total_duration', 0)
            has_total = total is not None and total > 0
            orig_value = value

            # 手动修改持续时间时，当前分段不再与事件时间严格对齐，取消事件绑定与高亮
            if hasattr(self, '_clear_event_binding_for_current_segment'):
                self._clear_event_binding_for_current_segment()

            if is_alpha_ratio and self.current_segment == 2:
                # 分段2：约束持续时间不超过总时长
                duration = max(1, int(value))
                if has_total:
                    start = int(self.segment2_start_time) if getattr(self, 'segment2_start_time', None) is not None else 0
                    max_duration = max(1, int(total) - max(0, start))
                    if duration > max_duration:
                        duration = max_duration
                if hasattr(self, 'duration_spinbox') and duration != orig_value:
                    self.duration_spinbox.blockSignals(True)
                    self.duration_spinbox.setValue(int(duration))
                    self.duration_spinbox.blockSignals(False)
                self.segment2_duration = duration
                self.segment2_end_time = self.segment2_start_time + self.segment2_duration
                if hasattr(self, 'end_spinbox'):
                    self.end_spinbox.blockSignals(True)
                    self.end_spinbox.setValue(int(self.segment2_end_time))
                    self.end_spinbox.blockSignals(False)
                QLLogging.log.info(
                    f"Segment2 duration changed: start={self.segment2_start_time}s, duration={self.segment2_duration}s, end={self.segment2_end_time}s")
            else:
                # 普通分析窗口：约束持续时间不超过总时长
                duration = max(1, int(value))
                if has_total:
                    start = int(self.analysis_start_time) if getattr(self, 'analysis_start_time', None) is not None else 0
                    max_duration = max(1, int(total) - max(0, start))
                    if duration > max_duration:
                        duration = max_duration
                if hasattr(self, 'duration_spinbox') and duration != orig_value:
                    self.duration_spinbox.blockSignals(True)
                    self.duration_spinbox.setValue(int(duration))
                    self.duration_spinbox.blockSignals(False)
                self.analysis_duration = duration
                self.analysis_end_time = self.analysis_start_time + self.analysis_duration
                if hasattr(self, 'end_spinbox'):
                    self.end_spinbox.blockSignals(True)
                    self.end_spinbox.setValue(int(self.analysis_end_time))
                    self.end_spinbox.blockSignals(False)
                QLLogging.log.info(
                    f"Analysis duration changed: start={self.analysis_start_time}s, duration={self.analysis_duration}s, end={self.analysis_end_time}s")

            if hasattr(self, 'selection_label'):
                if is_alpha_ratio and self.current_segment == 2:
                    self.selection_label.setText(f"Selection: {int(self.segment2_duration)} Sec")
                else:
                    self.selection_label.setText(f"Selection: {int(self.analysis_duration)} Sec")

            self.update_time_labels()
            self._update_rect_position()

        except Exception as e:
            QLLogging.log.exception(f"Error in on_duration_changed: {e}")

    def on_end_time_changed(self, value):
        """兼容：内部 end_spinbox 变更时保持 start+duration 一致（一般不直接由用户触发）"""
        try:
            current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
            is_alpha_ratio = current_method == "alpha Ratio(EC/EO)"

            # 手动修改结束时间时，当前分段不再与事件时间严格对齐，取消事件绑定与高亮
            if hasattr(self, '_clear_event_binding_for_current_segment'):
                self._clear_event_binding_for_current_segment()

            if is_alpha_ratio and self.current_segment == 2:
                self.segment2_end_time = value
                if self.segment2_end_time <= self.segment2_start_time:
                    self.segment2_start_time = self.segment2_end_time - 1
                    if self.segment2_start_time < 0:
                        self.segment2_start_time = 0
                        self.segment2_end_time = 1
                    if hasattr(self, 'start_spinbox'):
                        self.start_spinbox.blockSignals(True)
                        self.start_spinbox.setValue(int(self.segment2_start_time))
                        self.start_spinbox.blockSignals(False)
                self.segment2_duration = self.segment2_end_time - self.segment2_start_time
                if hasattr(self, 'duration_spinbox'):
                    self.duration_spinbox.blockSignals(True)
                    self.duration_spinbox.setValue(int(self.segment2_duration))
                    self.duration_spinbox.blockSignals(False)
            else:
                self.analysis_end_time = value
                if self.analysis_end_time <= self.analysis_start_time:
                    self.analysis_start_time = self.analysis_end_time - 1
                    if self.analysis_start_time < 0:
                        self.analysis_start_time = 0
                        self.analysis_end_time = 1
                    if hasattr(self, 'start_spinbox'):
                        self.start_spinbox.blockSignals(True)
                        self.start_spinbox.setValue(int(self.analysis_start_time))
                        self.start_spinbox.blockSignals(False)
                self.analysis_duration = self.analysis_end_time - self.analysis_start_time
                if hasattr(self, 'duration_spinbox'):
                    self.duration_spinbox.blockSignals(True)
                    self.duration_spinbox.setValue(int(self.analysis_duration))
                    self.duration_spinbox.blockSignals(False)

            if hasattr(self, 'selection_label'):
                if is_alpha_ratio and self.current_segment == 2:
                    self.selection_label.setText(f"Selection: {int(self.segment2_duration)} Sec")
                else:
                    self.selection_label.setText(f"Selection: {int(self.analysis_duration)} Sec")

            self._update_rect_position()

        except Exception as e:
            QLLogging.log.exception(f"Error in on_end_time_changed: {e}")

    def _update_rect_position(self):
        """只更新矩形位置，不重新绘制整个波形图（避免进度条）"""
        try:
            # 检查是否是alpha Ratio方法且选中了分段2
            current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
            is_alpha_ratio = current_method == "alpha Ratio(EC/EO)"

            # 更新分段1（蓝色）矩形
            if hasattr(self, 'analysis_rect') and self.analysis_rect is not None:
                try:
                    ax = self.analysis_rect.axes
                    if ax is not None:
                        ylim = ax.get_ylim()
                        # 更新矩形位置和大小
                        self.analysis_rect.set_x(self.analysis_start_time)
                        self.analysis_rect.set_width(self.analysis_duration)
                        self.analysis_rect.set_y(ylim[0])
                        self.analysis_rect.set_height(ylim[1] - ylim[0])
                except Exception as e:
                    QLLogging.log.debug(f"Could not update analysis_rect: {e}")

            # 更新分段2（红色/橙色）矩形（仅alpha Ratio方法）
            if is_alpha_ratio and hasattr(self, 'segment2_rect') and self.segment2_rect is not None:
                try:
                    ax = self.segment2_rect.axes
                    if ax is not None:
                        ylim = ax.get_ylim()
                        # 更新矩形位置和大小
                        self.segment2_rect.set_x(self.segment2_start_time)
                        self.segment2_rect.set_width(self.segment2_duration)
                        self.segment2_rect.set_y(ylim[0])
                        self.segment2_rect.set_height(ylim[1] - ylim[0])
                except Exception as e:
                    QLLogging.log.debug(f"Could not update segment2_rect: {e}")

            # 刷新画布（不重绘波形，只更新矩形显示）
            if hasattr(self, 'canvas') and self.canvas is not None:
                self.canvas.draw_idle()

        except Exception as e:
            QLLogging.log.exception(f"Error in _update_rect_position: {e}")

    def _on_canvas_press_define_window(self, event):
        """波形图上左键按下：若不在蓝色矩形上，则开始「点击设起点、拖动设持续时间」"""
        if event.inaxes is None or event.button != 1 or event.xdata is None:
            return
        if getattr(self, '_main_waveform_ax', None) is None or event.inaxes != self._main_waveform_ax:
            return
        # alpha Ratio 的分段2（分母）模式下，禁止通过画布定义逻辑修改蓝色分段1
        current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
        if current_method == "alpha Ratio(EC/EO)" and getattr(self, 'current_segment', 1) == 2:
            self._define_window_press_x = None
            return
        # 若正在拖动矩形，不进入定义模式（由 DraggableRectangle 处理）
        if hasattr(self, 'analysis_rect') and self.analysis_rect is not None and self.analysis_rect.press is not None:
            return
        if hasattr(self, 'segment2_rect') and self.segment2_rect is not None and self.segment2_rect.press is not None:
            return
        # 若点击在蓝色矩形内，不进入定义模式
        if hasattr(self, 'analysis_rect') and self.analysis_rect is not None:
            x0, w = self.analysis_rect.get_x(), self.analysis_rect.get_width()
            if x0 <= event.xdata <= x0 + w:
                return
        self._define_window_press_x = event.xdata

    def _on_canvas_motion_define_window(self, event):
        """拖动中：实时更新分析窗口为 起点=min(按下,当前) 持续时间=abs(当前-按下)"""
        if self._define_window_press_x is None:
            return
        # alpha Ratio 的分段2（分母）模式下，不允许该回调更新蓝色分段1
        current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
        if current_method == "alpha Ratio(EC/EO)" and getattr(self, 'current_segment', 1) == 2:
            self._define_window_press_x = None
            return
        if event.inaxes != getattr(self, '_main_waveform_ax', None) or event.xdata is None:
            return
        if not hasattr(self, 'analysis_rect') or self.analysis_rect is None:
            return
        total = self.total_duration if self.total_duration > 0 else 600
        start = min(self._define_window_press_x, event.xdata)
        duration = abs(event.xdata - self._define_window_press_x)
        start = max(0, min(start, total - 1))
        duration = max(1, min(duration, total - start))
        self.analysis_rect.set_x(start)
        self.analysis_rect.set_width(duration)
        if hasattr(self, 'canvas') and self.canvas is not None:
            self.canvas.draw_idle()

    def _on_canvas_release_define_window(self, event):
        """释放：确认分析窗口为 开始时间=min(按下,释放) 持续时间=abs(释放-按下)"""
        if self._define_window_press_x is None:
            return
        # alpha Ratio 的分段2（分母）模式下，不允许该回调更新蓝色分段1
        current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
        if current_method == "alpha Ratio(EC/EO)" and getattr(self, 'current_segment', 1) == 2:
            self._define_window_press_x = None
            return
        total = self.total_duration if self.total_duration > 0 else 600
        release_x = event.xdata if (event.inaxes and event.xdata is not None) else self._define_window_press_x
        start = min(self._define_window_press_x, release_x)
        duration = abs(release_x - self._define_window_press_x)
        start = max(0, min(start, total - 1))
        duration = max(1, min(duration, total - start))

        # 通过画布手动框选分析窗口时，当前分段不再与事件时间严格对齐，取消事件绑定与高亮
        if hasattr(self, '_clear_event_binding_for_current_segment'):
            self._clear_event_binding_for_current_segment()

        self.analysis_start_time = start
        self.analysis_duration = duration
        self.analysis_end_time = start + duration
        # 同步更新波形上的选中矩形，使松开后（含双击 1 秒）显示与数字一致
        if hasattr(self, 'analysis_rect') and self.analysis_rect is not None:
            self.analysis_rect.set_x(start)
            self.analysis_rect.set_width(duration)
        if hasattr(self, 'start_spinbox'):
            self.start_spinbox.blockSignals(True)
            self.start_spinbox.setValue(int(start))
            self.start_spinbox.blockSignals(False)
        if hasattr(self, 'duration_spinbox'):
            self.duration_spinbox.blockSignals(True)
            self.duration_spinbox.setValue(int(duration))
            self.duration_spinbox.blockSignals(False)
        if hasattr(self, 'end_spinbox'):
            self.end_spinbox.blockSignals(True)
            self.end_spinbox.setValue(int(self.analysis_end_time))
            self.end_spinbox.blockSignals(False)
        if hasattr(self, 'selection_label'):
            self.selection_label.setText(f"Selection: {int(duration)} Sec")
        self.update_time_labels()
        self._define_window_press_x = None
        if hasattr(self, 'canvas') and self.canvas is not None:
            self.canvas.draw_idle()

    def clear_segment2_rect(self):
        """清理第二个橙色框（segment2_rect）的资源，避免内存泄漏和空引用"""
        if self.segment2_rect is not None:
            # 断开鼠标事件连接
            self.segment2_rect.disconnect()
            # 从axes中移除矩形（如果axes存在）
            if self.segment2_rect.axes is not None:
                self.segment2_rect.remove()
            # 置空figure/axes，避免残留引用
            self.segment2_rect.figure = None
            self.segment2_rect.axes = None
            # 清空引用
            self.segment2_rect = None

    def on_analysis_method_changed(self, method):
        """分析方法切换时的处理"""
        try:
            # 先清理第二个框
            self.clear_segment2_rect()

            QLLogging.log.info(f"Analysis method changed to: {method}")

            if self.get_current_analysis_method() == "alpha Ratio(EC/EO)":
                # 显示分段切换按钮
                if hasattr(self, 'segment_switch_container'):
                    self.segment_switch_container.show()

                # 保持上次分段选择（默认分段1）
                target_segment = self.current_segment if self.current_segment in (1, 2) else 1
                self.current_segment = target_segment
                if hasattr(self, 'segment1_btn'):
                    self.segment1_btn.setChecked(target_segment == 1)
                if hasattr(self, 'segment2_btn'):
                    self.segment2_btn.setChecked(target_segment == 2)

                # 更新selection_label显示为当前分段对应颜色和时长
                if hasattr(self, 'selection_label'):
                    if target_segment == 2:
                        self.selection_label.setStyleSheet("""
                            QLabel {
                                font-family: Microsoft YaHei;
                                font-weight: 500;
                                font-size: 13px;
                                color: #E67E22;
                                background-color: #FFFFFF;
                                padding: 4px 8px;
                            }
                        """)
                        self.selection_label.setText(f"Selection: {int(self.segment2_duration)} Sec")
                    else:
                        self.selection_label.setStyleSheet("""
                            QLabel {
                                font-family: Microsoft YaHei;
                                font-weight: 500;
                                font-size: 13px;
                                color: #3B5998;
                                background-color: #FFFFFF;
                                padding: 4px 8px;
                            }
                        """)
                        self.selection_label.setText(f"Selection: {int(self.analysis_duration)} Sec")

                # 使时间输入框与当前分段一致（避免切换后仍显示分段1时长）
                if hasattr(self, 'duration_spinbox'):
                    self.duration_spinbox.blockSignals(True)
                    self.duration_spinbox.setValue(
                        int(self.segment2_duration if target_segment == 2 else self.analysis_duration))
                    self.duration_spinbox.blockSignals(False)

                # 重新绘制波形图以显示红色矩形
                if self.raw_filtered is not None:
                    self.plot_waveforms()
            else:
                # 隐藏分段切换按钮
                if hasattr(self, 'segment_switch_container'):
                    self.segment_switch_container.hide()

                # 重新绘制波形图以隐藏红色矩形
                if self.raw_filtered is not None:
                    self.plot_waveforms()

        except Exception as e:
            QLLogging.log.exception(f"Error in on_analysis_method_changed: {e}")

    def switch_segment(self, segment):
        """切换当前选中的分段"""
        try:
            # 已确认配置时锁定分段，不允许切换
            if hasattr(self, '_configured_task_ids') and self.task_id in self._configured_task_ids:
                locked_segment = self.current_segment if self.current_segment in (1, 2) else 1
                if hasattr(self, 'segment1_btn') and hasattr(self, 'segment2_btn'):
                    self.segment1_btn.blockSignals(True)
                    self.segment2_btn.blockSignals(True)
                    self.segment1_btn.setChecked(locked_segment == 1)
                    self.segment2_btn.setChecked(locked_segment == 2)
                    self.segment1_btn.blockSignals(False)
                    self.segment2_btn.blockSignals(False)
                QLLogging.log.debug(f"Task {self.task_id} is confirmed; segment switch ignored")
                return

            if segment == self.current_segment:
                return  # 如果已经是当前分段，不做任何操作

            self.current_segment = segment
            QLLogging.log.info(f"Switched to segment {segment}")

            # 更新按钮状态
            if hasattr(self, 'segment1_btn') and hasattr(self, 'segment2_btn'):
                self.segment1_btn.setChecked(segment == 1)
                self.segment2_btn.setChecked(segment == 2)

            # 根据选中的分段切换矩形的可拖动状态
            if segment == 1:
                # 分段1选中：蓝色矩形可拖动，红色矩形不可拖动
                if self.analysis_rect is not None:
                    self.analysis_rect.connect()
                if self.segment2_rect is not None:
                    self.segment2_rect.disconnect()

                # 更新selection_label为分段1的颜色和数据
                if hasattr(self, 'selection_label'):
                    self.selection_label.setStyleSheet("""
                        QLabel {
                            font-family: Microsoft YaHei;
                            font-weight: 500;
                            font-size: 13px;
                            color: #3B5998;
                            background-color: #FFFFFF;
                            padding: 4px 8px;
                        }
                    """)
                    self.selection_label.setText(f"Selection: {int(self.analysis_duration)} Sec")

                # 更新时间标签显示分段1的数据
                if hasattr(self, 'duration_spinbox'):
                    self.duration_spinbox.blockSignals(True)
                    self.duration_spinbox.setValue(int(self.analysis_duration))
                    self.duration_spinbox.blockSignals(False)

            else:
                # 分段2选中：红色矩形可拖动，蓝色矩形不可拖动
                if self.analysis_rect is not None:
                    self.analysis_rect.disconnect()
                if self.segment2_rect is not None:
                    self.segment2_rect.connect()

                # 更新selection_label为分段2的颜色和数据
                if hasattr(self, 'selection_label'):
                    self.selection_label.setStyleSheet("""
                        QLabel {
                            font-family: Microsoft YaHei;
                            font-weight: 500;
                            font-size: 13px;
                            color: #E67E22;
                            background-color: #FFFFFF;
                            padding: 4px 8px;
                        }
                    """)
                    self.selection_label.setText(f"Selection: {int(self.segment2_duration)} Sec")

                # 更新时间标签显示分段2的数据
                if hasattr(self, 'duration_spinbox'):
                    self.duration_spinbox.blockSignals(True)
                    self.duration_spinbox.setValue(int(self.segment2_duration))
                    self.duration_spinbox.blockSignals(False)

            # 更新时间标签
            self.update_time_labels()

            # alpha Ratio 下按分段恢复各自事件选中态：
            # 分段1显示分子事件，分段2显示分母事件；若该分段未选事件则不高亮任何项
            current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
            if current_method == "alpha Ratio(EC/EO)":
                if not hasattr(self, '_selected_event_name_by_segment') or self._selected_event_name_by_segment is None:
                    self._selected_event_name_by_segment = {1: None, 2: None}
                target_event_name = self._selected_event_name_by_segment.get(segment)
                if target_event_name:
                    if hasattr(self, 'event_list') and self.event_list is not None and self.event_list.count() == 0:
                        self._pending_event_name_to_select = target_event_name
                        self._pending_event_name_warning = False
                    else:
                        # 分段切换场景：保持原有行为，不弹窗、不重置时间
                        self._select_event_by_name(target_event_name, reset_time_when_not_found=False)
                else:
                    self._clear_event_selection_visual()

        except Exception as e:
            QLLogging.log.exception(f"Error in switch_segment: {e}")

    def on_event_selected(self, item):
        """事件锚点被选中 - 只更新起始点和分析窗口矩形，不重新绘制波形图"""
        # 更新所有事件项的样式
        for i in range(self.event_list.count()):
            list_item = self.event_list.item(i)
            item_widget = self.event_list.itemWidget(list_item)
            if item_widget:
                if list_item == item:
                    # 选中状态样式 - 使用精确选择器只应用到item_widget本身
                    item_widget.setStyleSheet("""
                        QWidget#eventItemWidget {
                            background-color: #E8F4FD;
                            border-radius: 8px;
                            border: 1px solid #2A87DB;
                        }
                    """)
                else:
                    # 非选中状态样式
                    item_widget.setStyleSheet("""
                        QWidget#eventItemWidget {
                            background-color: white;
                            border-radius: 8px;
                            border: none;
                        }
                    """)

        row = self.event_list.row(item)
        if 0 <= row < len(self.events):
            event = self.events[row]
            # 按当前分段更新对应时间：
            # - 分段1（分子）更新蓝色框 analysis_*
            # - 分段2（分母）更新橙色框 segment2_*
            current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
            is_alpha_ratio = current_method == "alpha Ratio(EC/EO)"
            event_time = event['time']
            event_name = event.get('name')

            suppress_time = getattr(self, '_suppress_time_update_on_event_select', False)

            if not suppress_time:
                if is_alpha_ratio and getattr(self, 'current_segment', 1) == 2:
                    self.segment2_start_time = event_time
                    self.segment2_end_time = self.segment2_start_time + self.segment2_duration
                    self._selected_event_name_by_segment[2] = event_name
                else:
                    self.analysis_start_time = event_time
                    self.analysis_end_time = self.analysis_start_time + self.analysis_duration
                    self._selected_event_name_by_segment[1] = event_name

                # 更新时间标签显示
                self.update_time_labels()
                # 只更新蓝色分析窗口矩形的位置，不重新绘制波形图
                # 使用轻量级更新方法，只更新矩形位置和大小
                self._update_analysis_rect_only()
            else:
                # 仅更新当前分段记录的事件名称，保持时间不变（用于任务切换时的纯回显）
                if is_alpha_ratio and getattr(self, 'current_segment', 1) == 2:
                    self._selected_event_name_by_segment[2] = event_name
                else:
                    self._selected_event_name_by_segment[1] = event_name

    def update_time_labels(self):
        """更新时间标签显示"""
        # 检查是否是alpha Ratio方法且选中了分段2
        current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
        is_alpha_ratio = current_method == "alpha Ratio(EC/EO)"
        if is_alpha_ratio and self.current_segment == 2:
            # 显示分段2的时间
            start_val = int(self.segment2_start_time)
            end_val = int(self.segment2_end_time)
            total_str = f"{self.segment2_duration:.1f}"
        else:
            # 显示分段1（默认）的时间
            start_val = int(self.analysis_start_time)
            end_val = int(self.analysis_end_time)
            total_str = f"{self.analysis_duration:.1f}"

        # 更新 start_spinbox、duration_spinbox 和 end_spinbox（兼容）
        if hasattr(self, 'start_spinbox'):
            self.start_spinbox.blockSignals(True)
            self.start_spinbox.setValue(start_val)
            self.start_spinbox.blockSignals(False)

        duration_val = end_val - start_val
        if hasattr(self, 'duration_spinbox'):
            self.duration_spinbox.blockSignals(True)
            self.duration_spinbox.setValue(max(1, duration_val))
            self.duration_spinbox.blockSignals(False)

        if hasattr(self, 'end_spinbox'):
            self.end_spinbox.blockSignals(True)
            self.end_spinbox.setValue(end_val)
            self.end_spinbox.blockSignals(False)

        # 更新隐藏的标签（兼容性）
        self.start_time_label.setText(str(start_val))
        self.end_time_label.setText(str(end_val))
        self.total_duration_label.setText(f"{total_str} Sec")

        # 更新selection_label
        if hasattr(self, 'selection_label'):
            if is_alpha_ratio and self.current_segment == 2:
                self.selection_label.setText(f"Selection: {int(self.segment2_duration)} Sec")
            else:
                self.selection_label.setText(f"Selection: {int(self.analysis_duration)} Sec")

        # 格式化时间为 MM:SS 格式
        start_str = self.format_time(start_val)
        end_str = self.format_time(end_val)
        self.bottom_start_label.setText(start_str)
        self.bottom_end_label.setText(end_str)
        self.bottom_total_label.setText(f"{total_str} Sec")

    def format_time(self, seconds):
        """格式化时间为 MM:SS 格式"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    def plot_waveforms(self, progress_dialog=None, start_progress=0):
        """绘制波形图 - 所有通道在同一个坐标系中
        
        Args:
            progress_dialog: 可选的进度条对话框。如果提供，将使用它并映射进度到start_progress%-100%范围。
                            如果不提供，将创建新的进度条对话框。
            start_progress: 绘图阶段的起始进度百分比（默认0，如果传入外部进度条，通常为30）
        """
        # skip_plotting模式下直接返回，不绘图也不弹框
        if getattr(self, 'skip_plotting', False):
            QLLogging.log.debug("Skipping plot_waveforms in skip_plotting mode")
            return
            
        if self.raw_filtered is None:
            QLLogging.log.warning("No filtered data available for plotting")
            return
        # 用于在执行绘图操作前，检查“画布（Canvas）”或“窗口（Figure）”是否已经创建好。
        if not hasattr(self, 'figure') or self.figure is None:
            QLLogging.log.warning("Figure canvas not initialized")
            return

        QLLogging.log.debug(
            f"plot_waveforms called: analysis_duration={self.analysis_duration}s, analysis_start_time={self.analysis_start_time}s")

        # 如果没有传入进度条，创建新的；如果传入了，使用传入的（映射到start_progress%-100%范围）
        create_new_dialog = (progress_dialog is None)

        if create_new_dialog:
            # 创建统一的进度条对话框
            progress_dialog = self.create_unified_progress_dialog("绘图中...")

        # 定义进度映射函数：将绘图阶段的进度（0-100）映射到整体进度范围
        # 如果使用外部进度条，映射到start_progress%-100%；如果使用内部进度条，保持0%-100%
        def map_progress(value):
            """将绘图阶段的进度值映射到整体进度范围"""
            if create_new_dialog:
                return value  # 使用内部进度条，保持0-100
            else:
                # 使用外部进度条，映射到start_progress-100范围
                # 绘图阶段占(100-start_progress)%的进度
                progress_range = 100 - start_progress
                return int(start_progress + value * progress_range / 100)

        from PyQt5.QtWidgets import QApplication
        if create_new_dialog:
            QApplication.processEvents()  # 确保进度条立即显示

        try:
            # 先断开旧的事件连接
            if self.analysis_rect is not None:
                self.analysis_rect.disconnect()
                self.analysis_rect = None

            progress_dialog.setValue(map_progress(10))
            progress_dialog.setLabelText(f"{self.task_name} 绘图中...")
            QApplication.processEvents()

            # 在清空画布之前，先验证数据是否准备好
            # 获取数据
            data = self.raw_filtered.get_data()
            times = self.raw_filtered.times

            if data is None or len(data) == 0:
                QLLogging.log.warning("No data to plot, skipping clear and plot")
                return

            n_channels = len(self.channel_names)

            if n_channels == 0:
                QLLogging.log.warning("No channels to plot, skipping clear and plot")
                return

            # 只有在数据准备好后才清空画布
            self.figure.clear()

            progress_dialog.setValue(map_progress(20))
            progress_dialog.setLabelText(f"{self.task_name} 绘图中...")
            QApplication.processEvents()

            # 限制通道数量，避免过多通道导致显示混乱
            max_channels = 21  # 最多显示21个通道
            if n_channels > max_channels:
                QLLogging.log.warning(f"Too many channels ({n_channels}), limiting to {max_channels}")
                n_channels = max_channels
                channel_names = self.channel_names[:max_channels]
                data = data[:max_channels]
            else:
                channel_names = self.channel_names

            # 不再截取数据，绘制全部数据
            # 记录实际数据时长
            actual_duration = times[-1] if len(times) > 0 else 0
            QLLogging.log.debug(f"Plotting full data: {actual_duration:.1f} seconds")

            # 对于大数据，进行降采样以提高性能
            max_points = 10000  # 每个通道最多显示10000个点
            if len(times) > max_points:
                step = len(times) // max_points
                times = times[::step]
                data = data[:, ::step]
                QLLogging.log.debug(f"Downsampled data for plotting: step={step}")

            self.inside_axes.clear()  # 每次重新绘图，清空旧的内嵌子图实例

            # 创建单个子图
            # 划分每个图的区域
            ax = self.figure.add_subplot(1, 1, 1)
            # 设置子图背景为暗蓝色，与整体界面保持一致
            dark_blue_color = '#08223C'  # 暗蓝色
            ax.set_facecolor(dark_blue_color)

            ax.margins(x=0, y=0)  # 父图x/y轴边距设为0，无任何留白
            ax.set_aspect('auto')  # 自动适配宽高，避免拉伸导致贴合失效

            # 计算每个通道的数据范围和统计信息
            channel_ranges = []
            channel_stds = []
            channel_means = []

            for i in range(n_channels):
                if len(data[i]) > 0:
                    ch_data = data[i]
                    # 使用标准差和范围来评估数据的变化程度
                    ch_std = np.std(ch_data)
                    ch_range = np.max(ch_data) - np.min(ch_data)
                    ch_mean = np.mean(ch_data)
                    # 使用标准差和范围的最大值，更准确地反映数据变化
                    ch_variation = max(ch_std, ch_range / 2.0) if ch_range > 0 else ch_std
                    channel_ranges.append(ch_variation)
                    channel_stds.append(ch_std)
                    channel_means.append(ch_mean)
                else:
                    channel_ranges.append(0)
                    channel_stds.append(0)
                    channel_means.append(0)

            if len(channel_ranges) == 0 or max(channel_ranges) == 0:
                QLLogging.log.warning("No valid data ranges")
                return

            # 过滤掉零值或极小的值，计算有效范围
            valid_ranges = [r for r in channel_ranges if r > 0.01]  # 过滤掉小于0.01的值

            if len(valid_ranges) == 0:
                QLLogging.log.warning("All channels have zero or near-zero variation")
                # 使用一个默认值
                base_range = 10
            else:
                # 使用有效范围的中位数作为基础，更稳健
                median_range = np.median(valid_ranges)
                mean_range = np.mean(valid_ranges)
                # 使用中位数和平均值的较大值
                base_range = max(median_range, mean_range)

            # 如果基础范围太小，使用一个合理的最小值
            if base_range < 1:
                base_range = max(10, np.mean([abs(m) for m in channel_means if abs(m) > 0.1]))
                if base_range < 1:
                    base_range = 10  # 最后的后备值

            # 通道间距：使用基础范围的倍数
            # 使用较小的倍数（2.5-3.0），让波形更紧凑但仍然清晰可见
            channel_spacing = base_range * 2.8

            # 定义颜色列表（使用不同颜色区分通道）
            colors = plt.cm.tab20(np.linspace(0, 1, n_channels))  # 使用tab20颜色映射

            progress_dialog.setValue(map_progress(40))
            progress_dialog.setLabelText(f"{self.task_name} 绘图中...")
            QApplication.processEvents()

            # 绘制所有通道
            # --- 1. 定义视觉显示的标准高度 ---
            # 不再依赖数据的原始 range，而是定义一个固定的“画布高度”
            VIRTUAL_HEIGHT = 100.0
            # 通道间距设为高度的 1.5 倍，确保波形互不重叠
            channel_spacing = VIRTUAL_HEIGHT * 1.5

            y_ticks = []
            y_tick_labels = []

            # 用于收集所有处理后的数据，最后计算 y_lim
            all_plotted_points = []

            inset_left = 0  # 所有内嵌子图的水平起始位置（归一化，0~1）
            inset_width = 1  # 所有内嵌子图的水平宽度（归一化，0~1）
            gap = 0.02  # 子图之间的垂直间距（归一化，避免重叠，建议0.01~0.05）
            # 计算每个内嵌子图的高度：总高度(1) 减去 (N-1)个间距，再平均分给N个子图
            inset_height = (1 - (n_channels - 1) * gap) / n_channels

            for i, ch_name in enumerate(channel_names):
                try:
                    # 更新进度（40% + 每个通道占 40% / n_channels）
                    progress = 40 + int((i + 1) * 40 / n_channels)
                    progress_dialog.setValue(map_progress(progress))
                    progress_dialog.setLabelText(f"{self.task_name} 绘图中...")
                    QApplication.processEvents()

                    # 第0个（第一个）子图bottom=0，第1个=inset_height+gap，第2个=2*(inset_height+gap)，以此类推
                    inset_bottom = i * (inset_height + gap)
                    # 创建内嵌子图：bounds=[左, 下, 宽, 高]
                    inside_ax = ax.inset_axes(bounds=[inset_left, inset_bottom, inset_width, inset_height])
                    inside_ax.set_facecolor(dark_blue_color)

                    ch_data = data[i].copy()

                    #  绘图
                    inside_ax.plot(times, ch_data,
                                   color=colors[i], linewidth=0.8, alpha=0.9,
                                   label=ch_name)

                    inside_ax.margins(x=0, y=0.05)  # x轴边距设为0（左右紧贴），y轴留5%边距（避免波形顶上下边缘）

                    # todo 根据下拉框对y轴缩放
                    amplitude = self.plot_combo_y.currentText()
                    if amplitude != "Auto":
                        scale_amplitude = int(amplitude[:-2])
                        inside_ax.set_ylim([-scale_amplitude, scale_amplitude])
                    else:
                        inside_ax.autoscale(axis='y')
                        # # 获取自动缩放后的范围
                        y_min, y_max = inside_ax.get_ylim()

                    # 隐藏所有坐标轴边框
                    inside_ax.spines['top'].set_visible(False)
                    inside_ax.spines['right'].set_visible(False)
                    inside_ax.spines['bottom'].set_visible(False)
                    inside_ax.spines['left'].set_visible(False)

                    # 隐藏x轴和y轴刻度
                    inside_ax.set_xticks([])
                    inside_ax.set_yticks([])
                    inside_ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

                    self.inside_axes.append(inside_ax)  # 保存实例，后续批量更新x轴

                    '''
                    # 计算基线偏移（从上往下排列）
                    offset = (n_channels - 1 - i) * channel_spacing
                    ch_data = data[i].copy()
                    
                    if len(ch_data) > 0:
                        # 1. 彻底去直流 (Zero-center)
                        # 无论原始值是 0 还是 30亿，减去均值后都围绕 0 波动
                        norm_data = ch_data - np.mean(ch_data)

                        # 2. 计算该通道的峰峰值 (PTP)
                        ptp = np.ptp(norm_data)

                        if ptp > 1e-9:
                            # 3. 强制归一化缩放
                            # 无论原始 PTP 是多少，缩放后其视觉高度都固定为 VIRTUAL_HEIGHT
                            scale_factor = VIRTUAL_HEIGHT / ptp
                            ch_plot_data = (norm_data * scale_factor) + offset
                        else:
                            # 如果完全没波动，就画在基线上
                            ch_plot_data = np.full_like(ch_data, offset)

                        # 调试日志
                        QLLogging.log.debug(f"Plotting {ch_name}: PTP={ptp:.2e}, Offset={offset}")
                    else:
                        ch_plot_data = np.array([])

                    # 4. 绘图
                    ax.plot(times, ch_plot_data,
                            color=colors[i], linewidth=0.8, alpha=0.9,
                            label=ch_name)

                    # 绘制基线
                    ax.axhline(y=offset, color=colors[i], linestyle='--',
                               linewidth=0.5, alpha=0.2)

                    y_ticks.append(offset)
                    y_tick_labels.append(ch_name)

                    # 收集数据点用于设置 Y 轴边界
                    if len(ch_plot_data) > 0:
                        all_plotted_points.extend([offset - VIRTUAL_HEIGHT / 2, offset + VIRTUAL_HEIGHT / 2])
                    '''

                except Exception as e:
                    QLLogging.log.exception(f"Error plotting channel {i}: {e}")

            # --- 2. 设置坐标轴 ---
            # 不设置刻度标签（隐藏刻度）

            # 强制重设 Y 轴范围
            if y_ticks:
                # 顶部多给一点空间显示标签，底部也留出边距
                y_min = min(y_ticks) - channel_spacing * 0.5
                y_max = max(y_ticks) + channel_spacing * 0.5
                ax.set_ylim(y_min, y_max)

            # 隐藏所有坐标轴边框
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            ax.spines['left'].set_visible(False)

            # 隐藏x轴和y轴刻度
            ax.set_xticks([])
            ax.set_yticks([])
            ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

            progress_dialog.setValue(map_progress(85))
            progress_dialog.setLabelText(f"{self.task_name} 绘图中...")
            QApplication.processEvents()

            # 绘制分析窗口（蓝色可拖动矩形）
            try:
                # 先断开旧的事件连接
                if self.analysis_rect is not None:
                    self.analysis_rect.disconnect()

                ylim = ax.get_ylim()
                # 创建可拖动矩形
                QLLogging.log.debug(
                    f"Creating rectangle: start={self.analysis_start_time}s, duration={self.analysis_duration}s, end={self.analysis_start_time + self.analysis_duration}s")
                self.analysis_rect = DraggableRectangle(
                    (self.analysis_start_time, ylim[0]),
                    self.analysis_duration,
                    ylim[1] - ylim[0],
                    self,  # 传递task_Analysis实例
                    is_segment2=False,
                    axes=ax,
                    linewidth=2,
                    edgecolor='#6495ED',
                    facecolor='#6495ED',
                    alpha=0.2,
                    label='ANALYSIS WINDOW',
                    zorder=7  # 核心新增：层级≥6，覆盖内嵌子图（默认zorder=5）
                )
                ax.add_patch(self.analysis_rect)
                # 连接鼠标事件
                self.analysis_rect.connect()

                # 保存主波形 axes，并连接「点击设起点、拖动设持续时间」的 canvas 回调
                self._main_waveform_ax = ax
                fig = self.figure
                if fig and fig.canvas:
                    if self._cid_define_press is not None:
                        fig.canvas.mpl_disconnect(self._cid_define_press)
                    if self._cid_define_motion is not None:
                        fig.canvas.mpl_disconnect(self._cid_define_motion)
                    if self._cid_define_release is not None:
                        fig.canvas.mpl_disconnect(self._cid_define_release)
                    self._cid_define_press = fig.canvas.mpl_connect(
                        'button_press_event', self._on_canvas_press_define_window)
                    self._cid_define_motion = fig.canvas.mpl_connect(
                        'motion_notify_event', self._on_canvas_motion_define_window)
                    self._cid_define_release = fig.canvas.mpl_connect(
                        'button_release_event', self._on_canvas_release_define_window)

                # 如果是alpha Ratio方法，添加S1: NUMERATOR标签
                current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
                if current_method == "alpha Ratio(EC/EO)":
                    # 在蓝色矩形中心添加标签
                    label_x = self.analysis_start_time + self.analysis_duration / 2
                    label_y = (ylim[0] + ylim[1]) / 2
                    ax.text(label_x, label_y, 'S1: NUMERATOR',
                            color='white', fontsize=10, fontweight='bold',
                            ha='center', va='center',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='#3B5998', alpha=0.8),
                            zorder=10)

                QLLogging.log.debug(f"Rectangle created successfully with width={self.analysis_rect.get_width()}s")
            except Exception as e:
                QLLogging.log.exception(f"Error adding analysis window: {e}")

            # 绘制分段2矩形（红色/橙色可拖动矩形）- 仅alpha Ratio方法使用
            try:
                # 先断开旧的事件连接
                if self.segment2_rect is not None:
                    self.segment2_rect.disconnect()
                    self.segment2_rect = None

                # 检查是否是alpha Ratio方法
                current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
                if current_method == "alpha Ratio(EC/EO)":
                    ylim = ax.get_ylim()
                    # 创建分段2的可拖动矩形（红色/橙色）
                    QLLogging.log.debug(
                        f"Creating segment2 rectangle: start={self.segment2_start_time}s, duration={self.segment2_duration}s")
                    self.segment2_rect = DraggableRectangle(
                        (self.segment2_start_time, ylim[0]),
                        self.segment2_duration,
                        ylim[1] - ylim[0],
                        self,  # 传递task_Analysis实例
                        is_segment2=True,  # 标记为分段2
                        axes=ax,
                        linewidth=2,
                        edgecolor='#E67E22',  # 橙色边框
                        facecolor='#E67E22',  # 橙色填充
                        alpha=0.2,
                        label='S2: DENOMINATOR',
                        zorder=7  # 核心新增：层级≥6，覆盖内嵌子图（默认zorder=5）
                    )
                    ax.add_patch(self.segment2_rect)

                    # 在红色矩形中心添加S2: DENOMINATOR标签
                    label_x = self.segment2_start_time + self.segment2_duration / 2
                    label_y = (ylim[0] + ylim[1]) / 2
                    ax.text(label_x, label_y, 'S2: DENOMINATOR',
                            color='white', fontsize=10, fontweight='bold',
                            ha='center', va='center',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='#E67E22', alpha=0.8),
                            zorder=10)

                    # 根据当前选中的分段决定哪个矩形可拖动
                    if self.current_segment == 1:
                        self.analysis_rect.connect()
                        # segment2_rect 不连接事件（不可拖动）
                    else:
                        self.analysis_rect.disconnect()
                        self.segment2_rect.connect()

                    QLLogging.log.debug(
                        f"Segment2 rectangle created successfully with width={self.segment2_rect.get_width()}s")
            except Exception as e:
                QLLogging.log.exception(f"Error adding segment2 rectangle: {e}")

            # 添加事件标记：垂直黄色线条 + 右侧「指令：事件名」标签（与黄线同逻辑、同可见性）
            try:
                # 标签 y 位置：倒数第一行与倒数第二行数据中间（axes 坐标，0 在下）
                if n_channels >= 2:
                    label_y_axes = (n_channels - 1) * (inset_height + gap) - gap / 2
                else:
                    label_y_axes = inset_height / 2
                trans_label = mtrans.blended_transform_factory(ax.transData, ax.transAxes)
                x_offset = 0.5  # 标签在黄线右侧的小偏移（秒），与黄线同属波形图
                label_font_family = _get_available_event_label_font_family()
                for event in self.events:
                    event_time = event.get('time', 0)
                    if 0 <= event_time <= self.total_duration:
                        # 垂直黄色线条
                        ax.axvline(x=event_time, color='#EFD25B', linewidth=1, linestyle='-', zorder=6)
                        # 黄线右侧标签：黄金色圆角背景、深色字，大小与滑动箭头相近
                        event_name = event.get('name', '')
                        label_text = f"指令：{event_name}"
                        t = ax.text(
                            event_time + x_offset,
                            label_y_axes,
                            label_text,
                            transform=trans_label,
                            fontsize=12,
                            fontfamily=label_font_family,
                            fontweight='normal',
                            color='#1a1a1a',
                            ha='left',
                            va='center',
                            bbox=dict(boxstyle='round,pad=0.25', facecolor='#EFD25B', edgecolor='#c9b84a',
                                      linewidth=0.8),
                            zorder=6,
                        )
                        t.set_in_layout(False)  # 不参与布局计算，避免标签导致波形显示区域变小
            except Exception as e:
                QLLogging.log.exception(f"Error adding event markers: {e}")

            # 设置x轴范围 - 初始显示窗口，支持滚动查看全部数据
            try:
                per_page_time = self.plot_combo_x.currentText()
                total_time = self.total_duration if self.total_duration > 0 else (times[-1] if len(times) > 0 else 600)
                if per_page_time == "Auto":
                    # Auto：固定 600 秒可见窗口（与 on_plot_combo_changed_x 一致）
                    visible_window = min(600, total_time)
                else:
                    if per_page_time[-3] == '秒':
                        visible_window = float(per_page_time.split(" ")[0])
                    elif per_page_time[-3] == '钟':
                        visible_window = float(per_page_time.split(" ")[0]) * 60
                    elif per_page_time[-3] == '时':
                        visible_window = float(per_page_time.split(" ")[0]) * 3600
                    visible_window = min(visible_window, total_time)

                if total_time <= visible_window:
                    # 显示全部（不加额外边距，避免起点偏移）
                    x_min = 0
                    x_max = total_time
                    ax.set_xlim(x_min, x_max)
                else:
                    # 数据超过 visible_window，显示首段
                    ax.set_xlim(0, visible_window)

                # 让所有内嵌子图与主轴保持一致的 X 轴范围
                current_xlim = ax.get_xlim()
                for inside_ax in self.inside_axes:
                    if inside_ax is not None:
                        inside_ax.set_xlim(current_xlim)
                        inside_ax.margins(x=0, y=0.05)

                self.visible_window = visible_window
                QLLogging.log.info(
                    f"X-axis initial view: 0 - {min(visible_window, total_time):.1f} seconds (total: {total_time:.1f}s)")

                # 统一更新滚动条：需要时显示，保证始终一致
                self._update_x_scrollbar_range(total_time, visible_window)

            except Exception as e:
                QLLogging.log.exception(f"Error setting x-axis limits: {e}")
                # 后备方案：使用数据范围
                if len(times) > 0:
                    ax.set_xlim(-5, times[-1] + 5)
                else:
                    ax.set_xlim(-5, 605)

            # 不显示网格线

            # 将 figure 英寸尺寸同步到 canvas 实际像素，避免 tight_layout 基于错误尺寸计算
            try:
                cw, ch = self.canvas.width(), self.canvas.height()
                if cw > 0 and ch > 0:
                    self.figure.set_size_inches(cw / self.figure.dpi, ch / self.figure.dpi, forward=False)
            except Exception:
                pass

            # 调整布局
            try:
                current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
                # alpha Ratio 会额外绘制文本/矩形，tight_layout 会为这些元素自动留白，导致绘图区变小
                if current_method == "alpha Ratio(EC/EO)":
                    self.figure.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)
                else:
                    self.figure.tight_layout()
            except Exception as e:
                QLLogging.log.warning(f"Error in tight_layout: {e}, trying alternative layout")
                try:
                    self.figure.subplots_adjust(left=0.15, right=0.95, top=0.95, bottom=0.1)
                except Exception as e2:
                    QLLogging.log.exception(f"Error in subplots_adjust: {e2}")

            # self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0, wspace=0, hspace=0)
            progress_dialog.setValue(map_progress(95))
            progress_dialog.setLabelText(f"{self.task_name} 绘图中...")
            QApplication.processEvents()

            # 绘制画布
            try:
                self.canvas.draw()
                # 强制刷新画布
                self.canvas.flush_events()
                QLLogging.log.debug(f"Canvas drawn successfully, rectangle width={self.analysis_duration}s")
            except Exception as e:
                QLLogging.log.exception(f"Error drawing canvas: {e}")

            progress_dialog.setValue(map_progress(100))
            progress_dialog.setLabelText(f"{self.task_name} 绘图中...")
            QApplication.processEvents()

        except Exception as e:
            QLLogging.log.exception(f"Error plotting waveforms: {e}")
            import traceback
            QLLogging.log.error(f"Plot error traceback: {traceback.format_exc()}")
        finally:
            # 只有在创建了新对话框时才关闭它（外部传入的进度条由外部管理）
            if create_new_dialog:
                try:
                    progress_dialog.close()
                except Exception:
                    pass

    def disable_filter_checkboxes(self):
        """禁用滤波器checkbox（highpass、lowpass、notch），使其在波形缩放后不可点击"""
        # 如果当前任务不在已确认集合中，直接返回，不执行置灰
        if not (hasattr(self, '_configured_task_ids') and self.task_id in self._configured_task_ids):
            return
        try:
            # 禁用 High-pass checkbox
            if hasattr(self, 'highpass_checkbox'):
                self.highpass_checkbox.setEnabled(False)
                # 同时禁用对应的spinbox
                if hasattr(self, 'highpass_spinbox'):
                    self.highpass_spinbox.setEnabled(False)

            # 禁用 Low-pass checkbox
            if hasattr(self, 'lowpass_checkbox'):
                self.lowpass_checkbox.setEnabled(False)
                # 同时禁用对应的spinbox
                if hasattr(self, 'lowpass_spinbox'):
                    self.lowpass_spinbox.setEnabled(False)

            # 禁用 Notch checkbox
            if hasattr(self, 'notch_checkbox'):
                self.notch_checkbox.setEnabled(False)
                # 同时禁用对应的spinbox
                if hasattr(self, 'notch_spinbox'):
                    self.notch_spinbox.setEnabled(False)

            QLLogging.log.debug("滤波器checkbox已禁用（波形缩放后）")
        except Exception as e:
            QLLogging.log.warning(f"禁用滤波器checkbox时出错: {e}")

    def _sanitize_task_name_input(self, text: str):
        """清理任务名称中的换行符"""
        if "\n" in text or "\r" in text:
            cleaned = text.replace("\n", "").replace("\r", "")
            if cleaned != text:
                self.task_name_input.blockSignals(True)
                self.task_name_input.setText(cleaned)
                self.task_name_input.blockSignals(False)

    def disable_all_controls(self):
        """禁用所有可调整的控件"""
        try:
            # 禁用任务名称输入框
            if hasattr(self, 'task_name_input'):
                self.task_name_input.setEnabled(False)
                self.task_name_input.setReadOnly(True)

            # 禁用分析方法下拉框
            if hasattr(self, 'method_combo'):
                self.method_combo.setEnabled(False)
                # 确保 lineEdit 也被禁用（如果存在）
                if self.method_combo.lineEdit() is not None:
                    self.method_combo.lineEdit().setReadOnly(True)

            # 禁用开始时间输入框（包括左右箭头按钮）
            if hasattr(self, 'start_spinbox'):
                self.start_spinbox.setEnabled(False)

            # 禁用分析时长输入框
            if hasattr(self, 'duration_spinbox'):
                self.duration_spinbox.setEnabled(False)

            # 禁用 Quick Bandpass 下拉框
            if hasattr(self, 'bandpass_combo'):
                self.bandpass_combo.setEnabled(False)

            # 禁用 High-pass 控件
            if hasattr(self, 'highpass_checkbox'):
                self.highpass_checkbox.setEnabled(False)
            if hasattr(self, 'highpass_spinbox'):
                self.highpass_spinbox.setEnabled(False)

            # 禁用 Low-pass 控件
            if hasattr(self, 'lowpass_checkbox'):
                self.lowpass_checkbox.setEnabled(False)
            if hasattr(self, 'lowpass_spinbox'):
                self.lowpass_spinbox.setEnabled(False)

            # 禁用 Notch 控件
            if hasattr(self, 'notch_checkbox'):
                self.notch_checkbox.setEnabled(False)
            if hasattr(self, 'notch_spinbox'):
                self.notch_spinbox.setEnabled(False)

            # 禁用事件锚点列表
            if hasattr(self, 'event_list'):
                self.event_list.setEnabled(False)
                # 断开信号连接，防止点击事件锚点
                try:
                    self.event_list.itemClicked.disconnect(self.on_event_selected)
                except (TypeError, RuntimeError):
                    # 如果信号未连接或已断开，忽略错误
                    pass

            # 禁用分析窗口的拖拽交互（蓝色遮罩）
            if hasattr(self, 'analysis_rect') and self.analysis_rect is not None:
                self.analysis_rect.disconnect()
            # 禁用分段2橙色框拖拽交互
            if hasattr(self, 'segment2_rect') and self.segment2_rect is not None:
                self.segment2_rect.disconnect()

            # 禁用分段切换按钮（alpha Ratio 分子/分母）
            if hasattr(self, 'segment1_btn'):
                self.segment1_btn.setEnabled(False)
            if hasattr(self, 'segment2_btn'):
                self.segment2_btn.setEnabled(False)

            QLLogging.log.debug("所有控件已禁用")
        except Exception as e:
            QLLogging.log.warning(f"禁用控件时出错: {e}")

    def enable_all_controls(self):
        """恢复所有可调整的控件"""
        try:
            # 恢复任务名称输入框
            if hasattr(self, 'task_name_input'):
                self.task_name_input.setEnabled(True)
                self.task_name_input.setReadOnly(False)

            # 恢复分析方法下拉框
            if hasattr(self, 'method_combo'):
                self.method_combo.setEnabled(True)
                # 恢复 lineEdit 的只读状态（保持原有的只读设置）
                if self.method_combo.lineEdit() is not None:
                    self.method_combo.lineEdit().setReadOnly(True)

            # 恢复开始时间输入框（包括左右箭头按钮）
            if hasattr(self, 'start_spinbox'):
                self.start_spinbox.setEnabled(True)

            # 恢复分析时长输入框
            if hasattr(self, 'duration_spinbox'):
                self.duration_spinbox.setEnabled(True)

            # 恢复 Quick Bandpass 下拉框
            if hasattr(self, 'bandpass_combo'):
                self.bandpass_combo.setEnabled(True)

            # 恢复 High-pass 控件
            if hasattr(self, 'highpass_checkbox'):
                self.highpass_checkbox.setEnabled(True)
            if hasattr(self, 'highpass_spinbox'):
                # 根据 checkbox 状态决定是否启用
                if hasattr(self, 'highpass_checkbox') and self.highpass_checkbox.isChecked():
                    self.highpass_spinbox.setEnabled(True)
                else:
                    self.highpass_spinbox.setEnabled(False)

            # 恢复 Low-pass 控件
            if hasattr(self, 'lowpass_checkbox'):
                self.lowpass_checkbox.setEnabled(True)
            if hasattr(self, 'lowpass_spinbox'):
                # 根据 checkbox 状态决定是否启用
                if hasattr(self, 'lowpass_checkbox') and self.lowpass_checkbox.isChecked():
                    self.lowpass_spinbox.setEnabled(True)
                else:
                    self.lowpass_spinbox.setEnabled(False)

            # 恢复 Notch 控件
            if hasattr(self, 'notch_checkbox'):
                self.notch_checkbox.setEnabled(True)
            if hasattr(self, 'notch_spinbox'):
                # 根据 checkbox 状态决定是否启用
                if hasattr(self, 'notch_checkbox') and self.notch_checkbox.isChecked():
                    self.notch_spinbox.setEnabled(True)
                else:
                    self.notch_spinbox.setEnabled(False)

            # 恢复事件锚点列表
            if hasattr(self, 'event_list'):
                self.event_list.setEnabled(True)
                # 重新连接信号（使用 Qt.UniqueConnection 确保只连接一次，避免多个进度条）
                try:
                    # 先断开已有连接，防止重复连接
                    self.event_list.itemClicked.disconnect(self.on_event_selected)
                except (TypeError, RuntimeError):
                    # 如果信号未连接，忽略错误
                    pass
                # 重新连接信号
                self.event_list.itemClicked.connect(self.on_event_selected)

            # 恢复分析窗口的拖拽交互（蓝色遮罩）
            current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
            is_alpha_ratio = current_method == "alpha Ratio(EC/EO)"
            if is_alpha_ratio and getattr(self, 'current_segment', 1) == 2:
                if hasattr(self, 'analysis_rect') and self.analysis_rect is not None:
                    self.analysis_rect.disconnect()
                if hasattr(self, 'segment2_rect') and self.segment2_rect is not None:
                    self.segment2_rect.connect()
            else:
                if hasattr(self, 'analysis_rect') and self.analysis_rect is not None:
                    self.analysis_rect.connect()
                if hasattr(self, 'segment2_rect') and self.segment2_rect is not None:
                    self.segment2_rect.disconnect()

            # 恢复分段切换按钮（alpha Ratio 分子/分母）
            if hasattr(self, 'segment1_btn'):
                self.segment1_btn.setEnabled(True)
            if hasattr(self, 'segment2_btn'):
                self.segment2_btn.setEnabled(True)

            QLLogging.log.debug("所有控件已恢复")
        except Exception as e:
            QLLogging.log.warning(f"恢复控件时出错: {e}")

    def reset_confirm_button(self):
        """重置确认按钮到初始状态（兼容旧调用，实际根据当前任务是否已配置刷新状态）"""
        self.refresh_confirm_button_state()

    def refresh_confirm_button_state(self):
        """根据当前任务是否已配置，刷新确认按钮的文案与样式（切换任务后保持已配置状态）"""
        if not hasattr(self, 'confirm_button') or self.confirm_button is None:
            return
        if not hasattr(self, '_configured_task_ids'):
            self._configured_task_ids = set()
        try:
            if self.task_id in self._configured_task_ids:
                # 当前任务已配置：显示「配置已确认」样式并禁用控件
                self.confirm_button.setText("配置已确认")
                self.confirm_button.setStyleSheet("""
                    QPushButton {
                        background-color: #2CCF37;
                        color: white;
                        border: none;
                        border-radius: 10px;
                        padding: 12px 20px;
                        font-weight: bold;
                        font-size: 12pt;
                        min-height: 45px;
                    }
                    QPushButton:hover {
                        background-color: #25B32E;
                    }
                    QPushButton:pressed {
                        background-color: #1E9A26;
                    }
                """)
                self.disable_all_controls()
                # 强制保持确认时的分段显示（避免切任务后按钮显示与状态错位）
                current_method = self.get_current_analysis_method() if hasattr(self, 'method_combo') else ""
                if current_method == "alpha Ratio(EC/EO)" and hasattr(self, 'segment1_btn') and hasattr(self,
                                                                                                        'segment2_btn'):
                    locked_segment = self.current_segment if self.current_segment in (1, 2) else 1
                    self.segment1_btn.blockSignals(True)
                    self.segment2_btn.blockSignals(True)
                    self.segment1_btn.setChecked(locked_segment == 1)
                    self.segment2_btn.setChecked(locked_segment == 2)
                    self.segment1_btn.blockSignals(False)
                    self.segment2_btn.blockSignals(False)
            else:
                # 当前任务未配置：显示「确认配置」样式并启用控件
                self.confirm_button.setText("确认配置")
                self.confirm_button.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #007ACC, stop:1 #005A9E);
                        color: white;
                        border: none;
                        border-radius: 10px;
                        padding: 12px 20px;
                        font-weight: bold;
                        font-size: 12pt;
                        min-height: 45px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #0088DD, stop:1 #0066BB);
                        transform: translateY(-2px);
                    }
                    QPushButton:pressed {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #004080, stop:1 #003366);
                        transform: translateY(0px);
                    }
                """)
                self.enable_all_controls()
        except Exception as e:
            QLLogging.log.warning(f"刷新确认按钮状态时出错: {e}")

    def showEvent(self, event):
        """窗口显示时根据当前任务是否已配置刷新按钮状态"""
        super().showEvent(event)
        self.refresh_confirm_button_state()

    def _sync_figure_size_to_canvas(self):
        """将 Figure 英寸尺寸同步到 canvas 实际像素，并重绘，消除首次显示时的布局偏差。"""
        try:
            if not hasattr(self, 'canvas') or self.canvas is None:
                return
            w = self.canvas.width()
            h = self.canvas.height()
            if w > 0 and h > 0:
                dpival = self.figure.dpi
                self.figure.set_size_inches(w / dpival, h / dpival, forward=False)
                # 仅同步尺寸，不再调用 tight_layout，避免二次压缩绘图区
                self.canvas.draw_idle()
        except Exception as e:
            QLLogging.log.warning(f"Figure尺寸同步失败: {e}")

    def _sync_figure_size_to_canvas_debounced(self):
        """去抖版尺寸同步：确保 resize 后最终尺寸被应用。"""
        try:
            self._sync_figure_size_to_canvas()
        finally:
            self._canvas_sync_pending = False

    def on_confirm(self):
        """确认按钮点击事件 - 支持切换确认/取消状态"""
        try:
            # 检查当前按钮状态
            current_text = self.confirm_button.text()

            # 如果当前是"配置已确认"状态，则取消配置
            if current_text == "配置已确认":
                if hasattr(self, '_configured_task_ids'):
                    self._configured_task_ids.discard(self.task_id)
                # 恢复按钮到初始状态
                self.confirm_button.setText("确认配置")
                self.confirm_button.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #007ACC, stop:1 #005A9E);
                        color: white;
                        border: none;
                        border-radius: 10px;
                        padding: 12px 20px;
                        font-weight: bold;
                        font-size: 12pt;
                        min-height: 45px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #0088DD, stop:1 #0066BB);
                        transform: translateY(-2px);
                    }
                    QPushButton:pressed {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #004080, stop:1 #003366);
                        transform: translateY(0px);
                    }
                """)

                # 恢复所有控件的可编辑状态
                self.enable_all_controls()

                QLLogging.log.info("配置已取消，可以重新修改配置")
                return

            # 如果当前是"确认配置"状态，则执行确认操作
            # 先进行验证，验证通过后再修改按钮状态

            # 获得当前任务的id
            task_id = self.task_id
            # 获得当前的任务名称
            task_name = self.task_name_input.text()
            # 获得当前的分析方法（内部键，用于逻辑与上报）
            method = self.get_current_analysis_method()
            # 获得分析窗口参数
            start_time = self.analysis_start_time
            end_time = self.analysis_end_time
            duration = self.analysis_duration
            # 获得滤波参数
            highpass_enabled = bool(self.highpass_checkbox.isChecked())
            lowpass_enabled = bool(self.lowpass_checkbox.isChecked())
            notch_enabled = bool(self.notch_checkbox.isChecked())
            # 数值始终保存（即使禁用也保留用户设置值）
            highpass_value = float(self.highpass_spinbox.value())
            lowpass_value = float(self.lowpass_spinbox.value())
            notch_value = float(self.notch_spinbox.value())
            # “有效值”：禁用时置 None（供算法/滤波逻辑使用）
            highpass = highpass_value if highpass_enabled else None
            lowpass = lowpass_value if lowpass_enabled else None
            notch = notch_value if notch_enabled else None
            # 获得当前选中的事件名称（只有在用户选择了事件时才保存）
            selected_event_names = None
            selected_event_names_segment1 = None
            selected_event_names_segment2 = None
            if hasattr(self, 'event_list') and self.event_list is not None:
                current_item = self.event_list.currentItem()
                if current_item is not None:
                    current_row = self.event_list.row(current_item)
                    if 0 <= current_row < len(self.events):
                        # 用户选择了事件，保存事件名称
                        selected_event_names = self.events[current_row]['name']

            # alpha Ratio 下分别保存分子/分母事件；兼容旧字段 selected_event_names 继续写分子事件
            seg1_event_name = (self._selected_event_name_by_segment.get(1)
                               if hasattr(self, '_selected_event_name_by_segment') else None)
            seg2_event_name = (self._selected_event_name_by_segment.get(2)
                               if hasattr(self, '_selected_event_name_by_segment') else None)

            # 兜底：若当前界面没有选中事件，保留该任务已保存的事件，避免被 None 覆盖
            if (selected_event_names is None and not seg1_event_name and not seg2_event_name
                    and getattr(self, 'task_id', None)):
                try:
                    from ...Domain.OPLog.Task import Task
                    from ...Infrastructure.DB.SQLLiteAccessor import SQLLiteDB_Only_MainTread
                    old_task = Task.get_by_id(SQLLiteDB_Only_MainTread.user_db, self.task_id)
                    if old_task is not None:
                        selected_event_names = getattr(old_task, 'selected_event_names', None)
                except Exception as _e:
                    QLLogging.log.debug(f"Fallback old selected_event_names failed: {_e}")

            if seg1_event_name:
                selected_event_names_segment1 = seg1_event_name
                selected_event_names = selected_event_names_segment1
            if seg2_event_name:
                selected_event_names_segment2 = seg2_event_name

            # 兜底：当本次未从UI读到任何事件时，保留任务中已保存的事件字段，避免被 None 覆盖
            if (selected_event_names is None and
                    selected_event_names_segment1 is None and
                    selected_event_names_segment2 is None and
                    getattr(self, 'task_id', None)):
                try:
                    from ...Domain.OPLog.Task import Task
                    from ...Infrastructure.DB.SQLLiteAccessor import SQLLiteDB_Only_MainTread
                    existing_task = Task.get_by_id(SQLLiteDB_Only_MainTread.user_db, self.task_id)
                    if existing_task is not None:
                        selected_event_names = getattr(existing_task, 'selected_event_names', None)
                except Exception as e:
                    QLLogging.log.warning(f"Fallback existing selected_event_names failed: {e}")

            # 验证通过，修改按钮状态
            if hasattr(self, '_configured_task_ids'):
                self._configured_task_ids.add(self.task_id)
            # 修改按钮样式和文字
            self.confirm_button.setText("配置已确认")
            self.confirm_button.setStyleSheet("""
                QPushButton {
                    background-color: #2CCF37;
                    color: white;
                    border: none;
                    border-radius: 10px;
                    padding: 12px 20px;
                    font-weight: bold;
                    font-size: 12pt;
                    min-height: 45px;
                }
                QPushButton:hover {
                    background-color: #25B32E;
                }
                QPushButton:pressed {
                    background-color: #1E9A26;
                }
            """)

            # 禁用所有可调整的控件
            self.disable_all_controls()

            # 获得原始数据
            # raw_data = self.raw_filtered if self.raw_filtered is not None else self.raw_processed

            QLLogging.log.info(
                f"Task confirmed: {task_name} (ID: {task_id}), Method: {method}, "
                f"Window: {start_time:.1f}s - {end_time:.1f}s, "
                f"Filter: High-pass={highpass}Hz, Low-pass={lowpass}Hz"
            )

            # 根据不同的分析方法进行判断和数据处理
            # 准备通用的数据传输字典（只传参数，算法在「生成报告」时再计算）
            # 只传参；EDF 路径/导出在「生成报告」时再执行（get_edf_path_for_report）
            data_to_transmit = {
                'task_id': task_id,
                'task_name': task_name,
                'method': method,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'highpass': highpass,
                'lowpass': lowpass,
                'notch': notch,
                'highpass_enabled': highpass_enabled,
                'lowpass_enabled': lowpass_enabled,
                'notch_enabled': notch_enabled,
                # 与滤波器一致：直接从 UI 控件读取当前值，不依赖回调是否触发过
                'bandpass_mode': self.bandpass_combo.currentText() if hasattr(self, 'bandpass_combo') else None,
                'x_axis_scale': self.plot_combo_x.currentText() if hasattr(self, 'plot_combo_x') else None,
                'y_axis_scale': self.plot_combo_y.currentText() if hasattr(self, 'plot_combo_y') else None,
                'highpass_value': highpass_value,
                'lowpass_value': lowpass_value,
                'notch_value': notch_value,
                'edf_path': None,
                'is_temp_file': False,
                'raw_processed': self.raw_processed,
                'edf_file_path': getattr(self, 'edf_file_path', None),
                'selected_event_names': selected_event_names,  # None 或事件名称字符串
                'selected_event_names_segment1': selected_event_names_segment1,
                'selected_event_names_segment2': selected_event_names_segment2,
            }

            # 根据不同的分析方法只传递参数，不在此处调用 analyzer.analyze
            if method == "Peak Alpha Frequency":
                QLLogging.log.info(f"Peak Alpha Frequency params for task: {task_name}")
                peak_alpha_data = data_to_transmit.copy()
                peak_alpha_data.update({
                    'start_time': start_time,
                    'end_time': end_time,
                    'frequency_band': {'low': 8.0, 'high': 13.0},
                })
                QLLogging.log.info(f"Peak Alpha Frequency params: {peak_alpha_data}")
                self.task_confirmed_signal.emit(peak_alpha_data)

            elif method == "Power Spectral Density":
                QLLogging.log.info(f"Power Spectral Density params for task: {task_name}")
                psd_data = data_to_transmit.copy()
                psd_data.update({'start_time': start_time, 'end_time': end_time})
                self.task_confirmed_signal.emit(psd_data)

            elif method == "Theta/Beta Ratio":
                QLLogging.log.info(f"Theta/Beta Ratio params for task: {task_name}")
                self.task_confirmed_signal.emit(data_to_transmit)

            elif method == "Z-Score Analysis":
                QLLogging.log.info(f"Z-Score Analysis params for task: {task_name}")
                data_to_transmit['subject_age'] = self.subject_age
                self.task_confirmed_signal.emit(data_to_transmit)

            elif method == "Full-Band Power Distribution":
                QLLogging.log.info(f"Full-Band Power Distribution params for task: {task_name}")
                full_band_data = data_to_transmit.copy()
                full_band_data.update({'start_time': start_time, 'end_time': end_time})
                self.task_confirmed_signal.emit(full_band_data)

            elif method == "Full-Band Ratio Distribution":
                QLLogging.log.info(f"Full-Band Ratio Distribution params for task: {task_name}")
                ratio_data = data_to_transmit.copy()
                ratio_data.update({'start_time': start_time, 'end_time': end_time})
                self.task_confirmed_signal.emit(ratio_data)

            elif method == "alpha Ratio(EC/EO)":
                QLLogging.log.info(f"alpha Ratio(EC/EO) params for task: {task_name}")
                alpha_ratio_data = data_to_transmit.copy()
                alpha_ratio_data.update({
                    'segment1': {
                        'start_time': self.analysis_start_time,
                        'end_time': self.analysis_end_time,
                        'duration': self.analysis_duration,
                    },
                    'segment2': {
                        'start_time': self.segment2_start_time,
                        'end_time': self.segment2_end_time,
                        'duration': self.segment2_duration,
                    },
                    'current_segment': self.current_segment,
                    'start_time_': self.segment2_start_time,
                    'end_time_': self.segment2_end_time,
                    'frequency_band': {'low': 8.0, 'high': 13.0},
                })
                QLLogging.log.info(
                    f"alpha Ratio(EC/EO) params: segment1={alpha_ratio_data['segment1']}, segment2={alpha_ratio_data['segment2']}")
                self.task_confirmed_signal.emit(alpha_ratio_data)

            elif method == "Frontal Alpha Asymmetry":
                QLLogging.log.info(f"Frontal Alpha Asymmetry params for task: {task_name}")
                faa_data_to_send = data_to_transmit.copy()
                faa_data_to_send.update({
                    'start_time': start_time,
                    'end_time': end_time,
                    'frequency_band': {'low': 8.0, 'high': 13.0},
                    'target_channels': ['F3', 'F4'],
                })
                self.task_confirmed_signal.emit(faa_data_to_send)

            elif method == "Report Output":
                # “报告输出验收 / Report Output” 仅用于控制是否在报告末尾显示“综合评估/报告输出验收”页面
                # 不需要在生成报告线程中执行任何算法，这里只透传参数，方便后续根据 method 判断是否选中过该分析方法
                QLLogging.log.info(
                    f"Report Output params for task: {task_name}（仅用于控制报告输出验收页面显示，不触发算法）")
                self.task_confirmed_signal.emit(data_to_transmit)

            else:
                # 未知的分析方法
                QLLogging.log.warning(f"Unknown analysis method: {method}")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "警告", f"未知的分析方法: {method}")

            # 临时 EDF 在「生成报告」时由 run_analysis_for_params 计算后再清理，此处不删除

        except Exception as e:
            QLLogging.log.exception(f"Error in confirm action: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"确认操作时发生错误: {str(e)}")
