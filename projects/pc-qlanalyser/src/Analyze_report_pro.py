import math
import sys
import os
import re
import cv2
from pathlib import Path

from .Control_Style import ControlStyle


# ==========================================
# 修复conda环境检测错误：彻底清除可能误识别venv为conda的环境变量
# 这必须在导入任何其他库之前执行
# ==========================================
def fix_conda_env_detection():
    """修复conda环境误检测问题 - 彻底清除指向venv的conda环境变量"""
    # 所有可能的conda环境变量
    conda_env_vars = [
        'CONDA_PREFIX',
        'CONDA_DEFAULT_ENV',
        'CONDA_PROMPT_MODIFIER',
        'CONDA_PYTHON_EXE',
        'CONDA_SHLVL',
        'CONDA_EXE'
    ]

    removed_vars = []

    # 获取当前脚本所在目录（项目根目录）
    project_root = None
    try:
        # 尝试获取当前文件所在目录
        if '__file__' in globals():
            current_file = __file__
        else:
            current_file = sys.argv[0] if sys.argv else None

        if current_file:
            current_dir = os.path.dirname(os.path.abspath(current_file))
            # 向上查找项目根目录（包含venv的目录）
            check_dir = current_dir
            max_levels = 5  # 最多向上查找5级
            level = 0
            while check_dir and level < max_levels:
                venv_path = os.path.join(check_dir, 'venv')
                if os.path.exists(venv_path):
                    project_root = check_dir
                    break
                parent = os.path.dirname(check_dir)
                if parent == check_dir:  # 到达根目录
                    break
                check_dir = parent
                level += 1
    except Exception as e:
        # 如果获取失败，不影响后续处理
        pass

    for var_name in conda_env_vars:
        if var_name in os.environ:
            var_value = os.environ[var_name]
            if var_value:
                var_path = os.path.normpath(var_value)
                should_remove = False

                # 策略1: 如果路径包含venv字符串，且没有conda-meta目录
                if 'venv' in var_path.lower():
                    if os.path.exists(var_path):
                        conda_meta_path = os.path.join(var_path, 'conda-meta')
                        if not os.path.exists(conda_meta_path):
                            should_remove = True
                    else:
                        # 路径不存在但包含venv，也清除
                        should_remove = True

                # 策略2: 如果路径指向项目目录下的venv
                elif project_root and var_path.startswith(project_root):
                    venv_path = os.path.join(project_root, 'venv')
                    if var_path == venv_path or var_path.startswith(venv_path):
                        should_remove = True

                # 策略3: 检查是否是venv结构（有Scripts/bin但没有conda-meta）
                elif os.path.exists(var_path):
                    conda_meta_path = os.path.join(var_path, 'conda-meta')
                    has_scripts = os.path.exists(os.path.join(var_path, 'Scripts'))
                    has_bin = os.path.exists(os.path.join(var_path, 'bin'))
                    has_conda_meta = os.path.exists(conda_meta_path)

                    # 如果有Scripts或bin但没有conda-meta，很可能是venv
                    if (has_scripts or has_bin) and not has_conda_meta:
                        should_remove = True

                if should_remove:
                    os.environ.pop(var_name, None)
                    removed_vars.append(f"{var_name}={var_value}")

    if removed_vars:
        print(f"[环境修复] 已清除误识别的conda环境变量: {', '.join(removed_vars)}")

    return len(removed_vars) > 0


# 执行修复（在导入任何库之前）
fix_conda_env_detection()

import base64
import io
from datetime import datetime
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QFileDialog, QMessageBox, \
    QProgressDialog

# 尝试导入 PyQtWebEngine，如果失败则设置标志
WEBENGINE_AVAILABLE = False
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage

    WEBENGINE_AVAILABLE = True
except ImportError:
    # 如果导入失败，创建占位类
    class QWebEngineView:
        pass


    class QWebEnginePage:
        pass

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from jinja2 import Template
import matplotlib
from matplotlib.colors import ListedColormap
from .Domain.OPLog.HistoryTask import HistoryTask
from .Infrastructure.DB.SQLLiteAccessor import SQLLiteDB_Only_MainTread

matplotlib.use('Agg')
import matplotlib.pyplot as plt

if WEBENGINE_AVAILABLE:
    class ReportPreviewWebPage(QWebEnginePage):
        def __init__(self, host, parent=None):
            super().__init__(parent)
            self._host = host

        def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
            try:
                prefix = "QL_ASSESSMENT_SAVED:"
                if isinstance(message, str) and message.startswith(prefix):
                    payload = message[len(prefix):]
                    if self._host is not None:
                        self._host._on_assessment_saved_from_console(payload)
            except Exception:
                pass
            super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)

# ==========================================
# 地形图统一色标配置（Power/Ratio）
# ==========================================
HEX_COLORS = [
    "#0606fc",
    "#0532fb",
    "#055dfb",
    "#0689fc",
    "#06b4fc",
    "#06dffb",
    "#23fbfc",
    "#b3fbfb",
    "#fbfbfb",
    "#fbfbd0",
    "#fcfc7a",
    "#fbfb22",
    "#fbde06",
    "#fbb305",
    "#fc8906",
    "#fc5d06",
    "#fc3206",
]

# HEX_COLORS = [
#     "#3a3aff",  # 深蓝色（功率最小值）
#     "#4f5cff",
#     "#6275ff",
#     "#7aa0ff",
#     "#9ac8ff",
#     "#06b4fc",
#     "#06dffb",
#     "#23fbfc",
#     "#03fa5a",  # 青绿色（中功率锚点）
#     "#2efa4a",
#     "#5af93a",
#     "#85f42a",
#     "#b0ef1a",
#     "#dbfa0a",
#     "#faa503",
#     "#fa5a03",
#     "#fd3206",  # 鲜红色（功率最大值）
# ]


VMIN, VMAX = -5, 3.0
# Z-Score 范围(标准差)
RVMIN, RVMAX = -3, 3
TOPO_COLORMAP = ListedColormap(HEX_COLORS, name='ql_power_ratio_map')
# 由 HEX_COLORS 动态生成 CSS linear-gradient 字符串，供 HTML 模板色度条使用
HEX_COLORS_CSS = "linear-gradient(to right, " + ", ".join(HEX_COLORS) + ")"
# 设置为 True 可在控制台打印每次地形图绘制数据与色图参数
TOPO_PLOT_DEBUG = True
TOPO_DEBUG_PRINT = os.environ.get("QL_TOPO_DEBUG", "0") == "1"


# ==========================================
# 辅助工具：图像转 Base64
# ==========================================
def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    plt.close(fig)
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"


# ==========================================
# 地形图生成工具（）
# ==========================================
def create_topography_image(data, info=None, channel_names=None, vmin=None, vmax=None,
                            title="", cmap=None):
    """创建地形图并转换为Base64"""
    try:
        # 统一将默认/历史 RdBu_r 映射到项目标准色板
        if cmap is None or cmap == 'RdBu_r':
            cmap = TOPO_COLORMAP
        # 未显式指定范围时，固定使用统一色标范围
        if vmin is None:
            vmin = VMIN
        if vmax is None:
            vmax = VMAX
        if TOPO_DEBUG_PRINT:
            data_arr = np.asarray(data, dtype=float)
            cmap_name = getattr(cmap, "name", str(cmap))
            color_count = len(getattr(cmap, "colors", [])) if hasattr(cmap, "colors") else -1
            print(
                f"[TOPO_DEBUG] title={title} size={data_arr.size} "
                f"data_min={data_arr.min():.6f} data_max={data_arr.max():.6f} "
                f"vmin={float(vmin):.6f} vmax={float(vmax):.6f} "
                f"cmap={cmap_name} color_count={color_count} "
                f"sample={np.round(data_arr[:5], 6).tolist()}"
            )
        data_arr = np.array(data, dtype=float)
        if TOPO_PLOT_DEBUG:
            cmap_name = getattr(cmap, 'name', str(cmap))
            cmap_len = len(getattr(cmap, 'colors', [])) if hasattr(cmap, 'colors') else -1
            sample_vals = np.round(data_arr[:8], 4).tolist()
            print(f"[TOPO_DEBUG] title={title} cmap={cmap_name} colors={cmap_len} "
                  f"vlim=({vmin},{vmax}) data_min={float(np.min(data_arr)):.4f} "
                  f"data_max={float(np.max(data_arr)):.4f} sample={sample_vals}")

        # 尝试导入mne，如果遇到conda环境错误，捕获并处理
        try:
            import mne
            from mne.channels import make_dig_montage
        except Exception as e:
            # 如果是conda环境相关错误，尝试清除环境变量后重新导入
            if 'conda' in str(e).lower() or 'DirectoryNotACondaEnvironmentError' in str(type(e).__name__):
                # 清除可能引起问题的conda环境变量
                for key in ['CONDA_PREFIX', 'CONDA_DEFAULT_ENV', 'CONDA_PROMPT_MODIFIER']:
                    if key in os.environ and 'venv' in os.environ.get(key, '').lower():
                        os.environ.pop(key, None)
                # 重新尝试导入
                import mne
                from mne.channels import make_dig_montage
            else:
                # 其他错误直接抛出
                raise

        if info is None and channel_names:
            try:
                montage = mne.channels.make_standard_montage('standard_1020')
                info = mne.create_info(
                    ch_names=channel_names[:len(data)],
                    sfreq=256.0,
                    ch_types=['eeg'] * len(data)
                )
                info.set_montage(montage, match_case=False, on_missing='ignore')
            except:
                info = None

        if info is None:
            return create_simple_topography_image(data, title, vmin, vmax, cmap)

        if len(data_arr) != len(info.ch_names):
            if len(data_arr) > len(info.ch_names):
                data_arr = np.array(data_arr[:len(info.ch_names)])
            else:
                padding = np.zeros(len(info.ch_names) - len(data_arr))
                data_arr = np.concatenate([np.array(data_arr), padding])

        # 使用透明背景，去掉黑色填充，缩小图片尺寸以适应边框内的等分区域
        fig, ax = plt.subplots(figsize=(1.6, 1.6), facecolor='none', edgecolor='none',dpi=300)
        fig.patch.set_alpha(0)  # 设置整个figure为透明

        try:
            # im, cm = mne.viz.plot_topomap(
            #     data_arr, info, axes=ax, show=False,
            #     vlim=(vmin, vmax), cmap=cmap,
            #     mask_params=dict(marker='o', markerfacecolor='w',
            #                      markeredgecolor='k', linewidth=0, markersize=1),
            #     sensors=False,  # 隐藏电极点
            #     contours=0,  # 不显示等高线
            #     outlines='head'  # 只显示头部轮廓

            # )

            im, cm =mne.viz.plot_topomap(
                data_arr, info, axes=ax, show=False,
                vlim=(vmin, vmax), cmap=cmap,

                sensors=False,  # 隐藏电极点
                contours=0,  # 不显示等高线
                outlines='head', 
                extrapolate="head",
                # image_interp="linear"
                )

            # 不显示标题，因为标签会在HTML中显示在图片下方
            ax.axis('off')
            ax.axis('off')
            # 设置axes背景为透明
            ax.patch.set_alpha(0)
            plt.tight_layout(pad=0.15)


        except:
            ax.clear() 
            ax.axis('off')

        # return fig_to_base64(fig)
        return fig_to_base64_with_remap(fig)
    except:
        return create_simple_topography_image(data, title, vmin, vmax, cmap)



'''
新增 将正圆脑图 映射为 脑轮廓
'''
# 全局缓存（避免重复加载mask）
_MASK_CACHE = {}

def _get_resource_path(filename):
    meipass = Path(getattr(sys, "_MEIPASS", ""))
    exe_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else None
    here = Path(__file__).resolve().parent

    candidates = []
    if getattr(sys, "frozen", False):
        candidates += [
            meipass / "resource" / filename,
            exe_dir / "resource" / filename,
            meipass.parent / "resource" / filename,
        ]
    else:
        candidates.append(here.parent / "resource" / filename)

    for p in candidates:
        if p and p.exists():
            return str(p)

    fallback = exe_dir / "resource" / filename if exe_dir else here.parent / "resource" / filename
    return str(fallback)


def _load_masks(H, W):
    """加载并缓存mask"""
    key = (H, W)

    if key in _MASK_CACHE:
        return _MASK_CACHE[key]

    brain_path = _get_resource_path("Template_brain_binary.png")
    head_path = _get_resource_path("Template_head_binary.png")

    brain = cv2.imread(brain_path, cv2.IMREAD_GRAYSCALE)
    head = cv2.imread(head_path, cv2.IMREAD_GRAYSCALE)

    if brain is None or head is None:
        raise FileNotFoundError("Mask image not found")

    brain = (brain > 0).astype(np.uint8)
    head = (head < 10).astype(np.uint8)

    if brain.shape != (H, W):
        brain = cv2.resize(brain, (W, H), interpolation=cv2.INTER_NEAREST)
        head = cv2.resize(head, (W, H), interpolation=cv2.INTER_NEAREST)

    _MASK_CACHE[key] = (brain, head)

    return brain, head


def fig_to_base64_with_remap(fig):

    fig.canvas.draw()

    # 直接获取 RGBA
    img = np.asarray(fig.canvas.buffer_rgba())
    H, W = img.shape[:2]
    brain_mask, head_mask = _load_masks(H, W)

    # --------------------------
    # brain alpha mask
    # --------------------------
    img = img.copy()
    img[:, :, 3] *= brain_mask

    canvas = img[:, :, :3]

    # --------------------------
    # head outline
    # --------------------------
    alpha = 0.7
    line_thresh = 200
    line_darken = 0.6

    head_binary = head_mask > 0

    head_outline = np.zeros_like(canvas)
    head_outline[head_binary] = (0, 0, 0)

    blended = (
        alpha * canvas.astype(np.float32) +
        (1 - alpha) * head_outline.astype(np.float32)
    ).astype(np.uint8)

    gray_outline = cv2.cvtColor(head_outline, cv2.COLOR_BGR2GRAY)
    is_line = gray_outline < line_thresh

    blended[is_line] = (blended[is_line] * line_darken).astype(np.uint8)

    canvas_final = np.where(
        head_binary[:, :, None],
        blended,
        canvas
    )

    img[:, :, :3] = canvas_final
    img[head_binary, 3] = 255

    # --------------------------
    # RGBA -> BGRA 
    # --------------------------
    img_bgra = cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA)

    # --------------------------
    # PNG encode
    # --------------------------
    success, buffer = cv2.imencode(".png", img_bgra)


    if not success:
        raise ValueError("Failed to encode image")

    return "data:image/png;base64," + base64.b64encode(buffer.tobytes()).decode()



# def fig_to_base64_with_remap(fig):

#     current_dir = os.path.dirname(os.path.abspath(__file__))

#     # 构造 resource 文件路径
#     map_x_path = os.path.join(current_dir, "..", "resource", "map_x.npy")
#     map_y_path = os.path.join(current_dir, "..", "resource", "map_y.npy")

#     map_x = np.load(map_x_path)
#     map_y = np.load(map_y_path)

#     fig.canvas.draw()
#     img = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
#     img = img.reshape(fig.canvas.get_width_height()[::-1] + (4,))

#     # 目前先设置成256*256（和im size 64*64 扭转的图会有裂）
#     img_resized = cv2.resize(img, (256, 256), interpolation=cv2.INTER_AREA)

#     warped = cv2.remap(
#         img_resized,
#         map_x.astype(np.float32),
#         map_y.astype(np.float32),
#         interpolation=cv2.INTER_CUBIC,
#         borderMode=cv2.BORDER_CONSTANT
#     )

#     img = cv2.resize(warped, (64, 64), interpolation=cv2.INTER_AREA)
#     plt.close(fig)

#     _, buffer = cv2.imencode(".png", img)
#     return f"data:image/png;base64,{base64.b64encode(buffer).decode()}"



def create_simple_topography_image(data, title="", vmin=None, vmax=None, cmap=None):
    """创建简单的地形图（不使用MNE）"""
    if cmap is None or cmap == 'RdBu_r':
        cmap = TOPO_COLORMAP
    if vmin is None:
        vmin = VMIN
    if vmax is None:
        vmax = VMAX
    if TOPO_DEBUG_PRINT:
        data_arr = np.asarray(data, dtype=float)
        cmap_name = getattr(cmap, "name", str(cmap))
        color_count = len(getattr(cmap, "colors", [])) if hasattr(cmap, "colors") else -1
        print(
            f"[TOPO_DEBUG_SIMPLE] title={title} size={data_arr.size} "
            f"data_min={data_arr.min():.6f} data_max={data_arr.max():.6f} "
            f"vmin={float(vmin):.6f} vmax={float(vmax):.6f} "
            f"cmap={cmap_name} color_count={color_count} "
            f"sample={np.round(data_arr[:5], 6).tolist()}"
        )
    # 使用透明背景，去掉黑色填充，缩小图片尺寸以适应边框内的等分区域
    fig, ax = plt.subplots(figsize=(1.6, 1.6), facecolor='none', edgecolor='none')
    fig.patch.set_alpha(0)  # 设置整个figure为透明
    n_channels = len(data)
    angles = np.linspace(0, 2 * np.pi, n_channels, endpoint=False)
    x = np.cos(angles)
    y = np.sin(angles)

    if vmin is None:
        vmin = np.min(data)
    if vmax is None:
        vmax = np.max(data)

    scatter = ax.scatter(x, y, c=data, s=40, cmap=cmap, vmin=vmin, vmax=vmax,
                         edgecolors='black', linewidths=0.5)
    cbar = plt.colorbar(scatter, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_ticks([VMIN, VMAX])
    cbar.ax.tick_params(labelsize=7)

    # 不显示标题，因为标签会在HTML中显示在图片下方
    ax.axis('off')

    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_aspect('equal')
    ax.axis('off')
    # 设置axes背景为透明
    ax.patch.set_alpha(0)
    plt.tight_layout(pad=0.2)

    return fig_to_base64(fig)


def generate_topography_matrix(data_dict, info=None, channel_names=None,
                               frequencies=None, global_vlim=True, cmap=None, fixed_vlim=True):
    """生成地形图矩阵"""
    topo_imgs = []
    if cmap is None:
        cmap = TOPO_COLORMAP

    all_values = []
    for values in data_dict.values():
        all_values.extend(values)

    if all_values:
        global_vmin = np.min(all_values)
        global_vmax = np.max(all_values)
    else:
        global_vmin = None
        global_vmax = None

    keys = frequencies if frequencies else sorted(data_dict.keys())

    for key in keys:
        if key not in data_dict:
            continue

        data = np.array(data_dict[key])

        if fixed_vlim:
            vmin = VMIN
            vmax = VMAX
        elif global_vlim:
            vmin = global_vmin
            vmax = global_vmax
        else:
            vmin = np.min(data)
            vmax = np.max(data)

        title = f"{key}Hz" if frequencies else str(key)
        if TOPO_DEBUG_PRINT:
            print(
                f"[TOPO_MATRIX_DEBUG] key={key} fixed_vlim={fixed_vlim} global_vlim={global_vlim} "
                f"selected_vmin={float(vmin):.6f} selected_vmax={float(vmax):.6f}"
            )

        img_url = create_topography_image(
            data, info=info, channel_names=channel_names,
            vmin=vmin, vmax=vmax, title=title, cmap=cmap
        )

        if TOPO_PLOT_DEBUG:
            print(f"[TOPO_DEBUG] matrix_key={key} vlim=({vmin},{vmax}) "
                  f"data_min={float(np.min(data)):.4f} data_max={float(np.max(data)):.4f}")

        max_value = np.max(data)

        topo_imgs.append({
            'freq' if frequencies else 'name': key,
            'url': img_url,
            'max_value': max_value,
            'vmin': vmin,
            'vmax': vmax,
        })

    return topo_imgs


# ==========================================
# PSD数据处理：转换为地形图格式
# ==========================================
def format_scientific_notation(value, precision=1, threshold=1000):
    """
    将数值格式化为科学计数法（1位小数）
    例如: 368907435402.1 -> "3.6×10¹¹"
    小数值（小于threshold）保持常规格式

    参数:
        value: 要格式化的数值
        precision: 小数位数（默认1位）
        threshold: 使用科学计数法的阈值（默认1000）

    返回:
        格式化后的字符串
    """
    try:
        val = float(value)
        if val == 0:
            return "0.0"

        # 如果数值小于阈值，使用常规格式
        if abs(val) < threshold:
            return f"{val:.{precision}f}"

        # 上标数字映射
        superscript_map = {
            '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
            '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
            '+': '⁺', '-': '⁻'
        }

        # 使用科学计数法格式化
        # 格式: {mantissa:.{precision}e} -> 例如: 3.689074e+11
        formatted = f"{val:.{precision}e}"

        # 解析科学计数法字符串
        if 'e' in formatted or 'E' in formatted:
            parts = formatted.lower().split('e')
            mantissa = float(parts[0])
            exponent = int(parts[1])

            # 将指数转换为上标
            exp_str = str(exponent)
            exp_superscript = ''.join(superscript_map.get(c, c) for c in exp_str)

            # 格式化为: mantissa×10^exponent (使用上标)
            # 例如: 3.6×10¹¹
            return f"{mantissa:.{precision}f}×10{exp_superscript}"
        else:
            # 如果不是科学计数法，直接返回格式化后的值
            return f"{val:.{precision}f}"
    except (ValueError, TypeError):
        return str(value)


# 预定义频段符号映射表 (low, high) -> symbol
BAND_SYMBOLS = {
      
    (2, 4): "δ",
    (4, 6): "θ1",
    (6, 8): "θ2",
    (8, 10): "α1",
    (10, 12): "α2",
    (12, 14): "SMR",
    (14, 16): "β1",
    (16, 18): "β2",
    (18, 20): "β2",
    (20, 22): "β3",
    (22, 24): "β3",
    (24, 26): "β3",
    (26, 28): "β3",
    (28, 30): "β3",
    (30, 32): "γ",
    (32, 34): "γ",
}

def normalize_band_hz_label(raw_value, index=None, step_hz=2, base_start_hz=2):
    low = None
    high = None

    if raw_value is None:
        if index is not None:
            low = int(base_start_hz + index * step_hz)
            high = int(low + step_hz)
    elif isinstance(raw_value, (int, float)):
        low = int(float(raw_value))
        high = int(low + step_hz)
    elif isinstance(raw_value, str):
        s = raw_value.strip()
        s = s.replace("Hz", "").replace("hz", "").strip()

        m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", s)
        if m:
            low = int(float(m.group(1)))
            high = int(float(m.group(2)))
        else:
            m2 = re.fullmatch(r"(\d+(?:\.\d+)?)", s)
            if m2:
                low = int(float(m2.group(1)))
                high = int(low + step_hz)
    
    # 如果通过 raw_value 解析失败，但有 index，尝试兜底计算
    if low is None and index is not None:
        low = int(base_start_hz + index * step_hz)
        high = int(low + step_hz)

    # 最终组装
    if low is not None and high is not None:
        base_label = f"{low}-{high}Hz"
        # 查找对应符号
        symbol = BAND_SYMBOLS.get((low, high), "")
        if symbol:
            return f"{base_label}({symbol})"
        return base_label

    # 如果实在无法解析且无 index，直接返回字符串
    return str(raw_value) if raw_value is not None else ""


def prepare_psd_topography_data(psd_results):
    """
    将PSD分析结果转换为地形图显示格式
    
    psd_results格式：
    {
        "channel_data": {
            "Fp1": {
                "delta": 2.6,      # 0.5-4 Hz 绝对功率 (µV²)
                "theta": 15.3,     # 4-8 Hz
                "alpha": 4.1,      # 8-13 Hz
                "beta": 5.3        # 13-30 Hz
            },
            ...
        }
    }
    
    支持通道名称映射：T3->T7, T4->T8, T5->P7, T6->P8
    
    返回21个通道的位置和显示数据（只包含4个频段：δ, θ, α, β）
    """
    # 标准10-20系统21通道位置（百分比坐标，相对于圆形区域）
    # 位置改为水平行布局，保持原有样式
    # 计算34px间距的坐标（基于容器宽度665px）
    # 卡片宽度：扩大15px，从9.5%（约63px）增加到约11.76%（约78px）
    # 间距：缩小6px，从40px减少到34px ≈ 5.113%
    card_width_pct = 21  # 约11.76%，扩大15px
    gap_pct = 0 / 760 * 100  # 约1.05%，间距缩小

    # 第1行（3个通道）：3个卡片 + 2个间距
    row1_total = 3 * card_width_pct + 2 * gap_pct
    row1_start = (100 - row1_total) / 2
    row1_x1 = row1_start + card_width_pct / 2
    row1_x2 = row1_start + card_width_pct + gap_pct + card_width_pct / 2
    row1_x3 = row1_start + 2 * (card_width_pct + gap_pct) + card_width_pct / 2

    # 第2-4行（5个通道）：5个卡片 + 4个间距
    row2_total = 5 * card_width_pct + 4 * gap_pct
    row2_start = (100 - row2_total) / 2
    row2_x1 = row2_start + card_width_pct / 2
    row2_x2 = row2_start + card_width_pct + gap_pct + card_width_pct / 2
    row2_x3 = row2_start + 2 * (card_width_pct + gap_pct) + card_width_pct / 2
    row2_x4 = row2_start + 3 * (card_width_pct + gap_pct) + card_width_pct / 2
    row2_x5 = row2_start + 4 * (card_width_pct + gap_pct) + card_width_pct / 2

    # 第5行（3个通道）：3个卡片 + 2个间距
    row5_total = 3 * card_width_pct + 2 * gap_pct
    row5_start = (100 - row5_total) / 2
    row5_x1 = row5_start + card_width_pct / 2
    row5_x2 = row5_start + card_width_pct + gap_pct + card_width_pct / 2
    row5_x3 = row5_start + 2 * (card_width_pct + gap_pct) + card_width_pct / 2

    # 向下平移（容器正方形732px，减少上下留白，使卡片更紧凑）
    y_offset = -4  # 整体上移，减少顶部留白

    # 进一步缩小行间距，使卡片纵向更紧凑
    y_gap_reduction = -50 / 732 * 100  # 约3.28%，缩小行间距

    # 计算每行的y坐标（紧凑布局，减少上下留白）
    row1_y = 18 + y_offset
    row2_y = 32 + y_offset - y_gap_reduction  # 第2行向上移动，缩小与第1行的间距
    row3_y = 46 + y_offset - y_gap_reduction * 2  # 第3行向上移动，缩小与第2行的间距
    row4_y = 60 + y_offset - y_gap_reduction * 3  # 第4行向上移动，缩小与第3行的间距
    row5_y = 74 + y_offset - y_gap_reduction * 4  # 第5行向上移动，缩小与第4行的间距

    channel_positions = {
        # 第1行（3个通道）- 17px间距
        'Fp1': {'x': row1_x1, 'y': row1_y},
        'Fpz': {'x': row1_x2, 'y': row1_y},
        'Fp2': {'x': row1_x3, 'y': row1_y},
        # 第2行（5个通道）- 17px间距
        'F7': {'x': row2_x1, 'y': row2_y},
        'F3': {'x': row2_x2, 'y': row2_y},
        'Fz': {'x': row2_x3, 'y': row2_y},
        'F4': {'x': row2_x4, 'y': row2_y},
        'F8': {'x': row2_x5, 'y': row2_y},
        # 第3行（5个通道）- 17px间距
        'T7': {'x': row2_x1, 'y': row3_y},
        'T3': {'x': row2_x1, 'y': row3_y},  # 映射到T7
        'C3': {'x': row2_x2, 'y': row3_y},
        'Cz': {'x': row2_x3, 'y': row3_y},
        'C4': {'x': row2_x4, 'y': row3_y},
        'T8': {'x': row2_x5, 'y': row3_y},
        'T4': {'x': row2_x5, 'y': row3_y},  # 映射到T8
        # 第4行（5个通道）- 17px间距
        'P7': {'x': row2_x1, 'y': row4_y},
        'T5': {'x': row2_x1, 'y': row4_y},  # 映射到P7
        'P3': {'x': row2_x2, 'y': row4_y},
        'Pz': {'x': row2_x3, 'y': row4_y},
        'P4': {'x': row2_x4, 'y': row4_y},
        'P8': {'x': row2_x5, 'y': row4_y},
        'T6': {'x': row2_x5, 'y': row4_y},  # 映射到P8
        # 第5行（3个通道）- 17px间距
        'O1': {'x': row5_x1, 'y': row5_y},
        'Oz': {'x': row5_x2, 'y': row5_y},
        'O2': {'x': row5_x3, 'y': row5_y}
    }
    '''
    # 通道名称映射：旧名称 -> 新名称
    channel_name_mapping = {
        'T3': 'T7',
        'T4': 'T8',
        'T5': 'P7',
        'T6': 'P8'
    }
    '''

    # 默认通道顺序（使用标准名称）
    default_channels = ['Fp1', 'Fpz', 'Fp2', 'F7', 'F3', 'Fz', 'F4', 'F8',
                        'T3', 'C3', 'Cz', 'C4', 'T4', 'T5', 'P3', 'Pz',
                        'P4', 'T6', 'O1', 'Oz', 'O2']

    channel_data = psd_results.get('channel_data', {})
    # 可选：算法直接返回每个通道的“结果图像”（base64 data url 或 http/本地url）
    # 约定格式：
    # psd_results["channel_imgs"] = {
    #   "Fp1": "data:image/png;base64,...",
    #   "Fpz": "data:image/svg+xml;base64,...",
    #   ...
    # }
    channel_imgs = psd_results.get('channel_imgs', {}) or {}


    normalized_channel_data = {}
    for ch_name, ch_data in channel_data.items():
        normalized_channel_data[ch_name] = ch_data

    # 准备每个通道的显示数据
    channels_for_template = []
    for ch_name in default_channels:
        if ch_name not in normalized_channel_data:
            # 如果缺少通道数据，使用默认值
            ch_data = {
                'delta': 0, 'theta': 0, 'alpha': 0, 'beta': 0, 'smr': 0, 'high_beta': 0, 'gamma': 0
            }
        else:
            ch_data = normalized_channel_data[ch_name]

        # 获取位置
        pos = channel_positions.get(ch_name, {'x': 50, 'y': 50})

        # 归一化柱状图高度
        delta_val = ch_data.get('delta', 0)
        theta_val = ch_data.get('theta', 0)
        alpha_val = ch_data.get('alpha', 0)
        beta_val = ch_data.get('beta', 0)
        smr_val = ch_data.get('smr', 0)
        high_beta_val = ch_data.get('high_beta', 0)
        gamma_val = ch_data.get('gamma', 0)

        # 1. 定义目标波段
        target_bands = ['delta', 'theta', 'alpha', 'beta', 'smr', 'high_beta', 'gamma']
        # 2. 读取原始数据
        raw_values = [ch_data.get(band, 0) for band in target_bands]

        # 3. 对数变换核心逻辑：处理0和负数，避免log计算异常
        log_values = []
        for val in raw_values:
            if val <= 0:
                # 非正数赋值极小值，保证对数有效，不影响可视化
                log_val = math.log10(1e-10)
            else:
                # 以10为底取对数，适配科学计数法数据
                log_val = math.log10(val)
            log_values.append(log_val)

        # 4. 对对数变换后的数据做最大值归一化到0-100%
        max_log = max(log_values) if log_values else 1.0
        bar_heights = {
            band: round((log_val / max_log) * 100, 2)
            for band, log_val in zip(target_bands, log_values)
        }

        # 绑定该通道的图像（如果算法返回）
        ch_img = channel_imgs.get(ch_name)

        def format_psd_value(val):
            # val = val / 1e12
            val = np.maximum(val, 1e-20)
            return round(val,2)

        channels_for_template.append({
            'name': ch_name,
            'x': pos['x'],
            'y': pos['y'],
            'img': ch_img,
            'bar_heights': bar_heights,
            'channel_values': {  # 只保留四个字母对应的数值
                'delta': format_psd_value(delta_val),
                'theta': format_psd_value(theta_val),
                'alpha': format_psd_value(alpha_val),
                'beta': format_psd_value(beta_val),
                'smr': format_psd_value(smr_val),
                'high_beta': format_psd_value(high_beta_val),
                'gamma': format_psd_value(gamma_val)
            }
        })

    return {'channels': channels_for_template}


# ==========================================
# QEEG Mapping数据处理：转换为地形图格式
# ==========================================
def prepare_qeeg_mapping_data(qeeg_results):
    """
    将Quantitative EEG Mapping结果转换为地形图显示格式
    
    qeeg_results格式：
    {
        "absolute_power_matrix": {
            "images": [...] or "data": {...}  # 16个频段（2-4Hz到32-34Hz）
        },
        "relative_power_zscore": {
            "images": [...] or "data": {...}  # 16个频段的Z-Score
        },
        "power_ratios": {
            "images": [...] or "data": {...}  # 12个比率
        },
        "ratio_zscore": {
            "images": [...] or "data": {...}  # 12个比率的Z-Score
        }
    }
    
    返回准备渲染的数据
    """
    result = {}

    # 处理绝对功率矩阵（16个频段：2-4, 4-6, ..., 32-34Hz）
    if 'absolute_power_matrix' in qeeg_results:
        abs_data = qeeg_results['absolute_power_matrix']
        absolute_imgs = abs_data.get('images') or abs_data.get('topo_imgs') or []

        # 如果没有图片，但有数据，则生成图片
        if not absolute_imgs and 'data' in abs_data:
            info = qeeg_results.get('info')
            channel_names = qeeg_results.get('channel_names')
            # 默认16个频段（2-4Hz到32-34Hz，步进2Hz）
            freq_bands = [(2 + i * 2, 4 + i * 2) for i in range(16)]  # [(2,4), (4,6), ..., (32,34)]

            # 生成地形图
            if isinstance(abs_data['data'], dict):
                # 如果数据是字典格式，需要转换key以匹配频率标签
                # 数据可能使用数字key (2, 4, 6...) 或字符串key ("2-4", "4-6"...)
                data_dict = abs_data['data']

                # 尝试匹配频率key
                freq_keys = []
                for low, high in freq_bands:
                    # 尝试多种可能的key格式
                    possible_keys = [
                        f"{low}-{high}",  # "2-4"
                        f"{low}",  # "2"
                        low,  # 2 (数字)
                        (low, high),  # (2, 4) 元组
                    ]
                    # 找到第一个匹配的key
                    matched_key = None
                    for key in possible_keys:
                        if key in data_dict:
                            matched_key = key
                            break
                    if matched_key:
                        freq_keys.append(matched_key)

                # 如果找到了匹配的key，重新组织数据
                if freq_keys:
                    reorganized_data = {}
                    for i, key in enumerate(freq_keys):
                        freq_label = f"{freq_bands[i][0]}-{freq_bands[i][1]}"
                        reorganized_data[freq_label] = data_dict[key]

                    absolute_imgs = generate_topography_matrix(
                        reorganized_data, info=info, channel_names=channel_names,
                        frequencies=[f"{low}-{high}" for low, high in freq_bands],
                        global_vlim=True, cmap=TOPO_COLORMAP
                    )
                else:
                    # 如果无法匹配，直接使用原始数据（假设key已经是正确的格式）
                    absolute_imgs = generate_topography_matrix(
                        data_dict, info=info, channel_names=channel_names,
                        frequencies=[f"{low}-{high}" for low, high in freq_bands],
                        global_vlim=True, cmap=TOPO_COLORMAP
                    )
            else:
                # 如果是其他格式，尝试转换
                print("警告: 绝对功率数据格式需要调整")

        # 格式化标签（使用 normalize_band_hz_label 统一格式，如 "2-4Hz(δ)"）
        formatted_abs_imgs = []
        for i, img in enumerate(absolute_imgs):
            # 处理图片数据，可能是字典或已有url的图片
            if isinstance(img, dict):
                url = img.get('url', '')
                freq = img.get('freq')
                label = normalize_band_hz_label(freq, index=i)
            else:
                url = str(img)  # 如果直接是字符串URL
                label = normalize_band_hz_label(None, index=i)

            formatted_abs_imgs.append({
                'url': url,
                'label': label
            })
        result['absolute_power_imgs'] = formatted_abs_imgs

    # 处理相对功率Z-Score（16个频段）
    if 'relative_power_zscore' in qeeg_results:
        rel_zscore_data = qeeg_results['relative_power_zscore']
        relative_zscore_imgs = rel_zscore_data.get('images') or rel_zscore_data.get('topo_imgs') or []

        if not relative_zscore_imgs and 'data' in rel_zscore_data:
            info = qeeg_results.get('info')
            channel_names = qeeg_results.get('channel_names')
            freq_bands = [(2 + i * 2, 4 + i * 2) for i in range(16)]

            if isinstance(rel_zscore_data['data'], dict):
                relative_zscore_imgs = generate_topography_matrix(
                    rel_zscore_data['data'], info=info, channel_names=channel_names,
                    frequencies=[f"{low}-{high}" for low, high in freq_bands],
                    global_vlim=True, cmap=TOPO_COLORMAP
                )

        formatted_rel_zscore_imgs = []
        for i, img in enumerate(relative_zscore_imgs):
            if isinstance(img, dict):
                url = img.get('url', '')
                freq = img.get('freq')
                label = normalize_band_hz_label(freq, index=i)
            else:
                url = str(img)
                label = normalize_band_hz_label(None, index=i)

            formatted_rel_zscore_imgs.append({
                'url': url,
                'label': label
            })
        result['relative_zscore_imgs'] = formatted_rel_zscore_imgs

    # 注意：功率比率已移至 Ratio Mapping 分析方法，不再在 Quantitative EEG Mapping 中处理
    # Ratio Mapping 的12种比率标签:
    # 1. θ/α, 2. θ/β, 3. θ/Hiβ, 4. α/β, 5. α/Hiβ, 6. β/Hiβ
    # 7. Hiθ/Loα, 8. Loα/Hiα, 9. δ/θ, 10. δ/α, 11. δ/β, 12. δ/Hiβ

    # 保留旧代码但不再在QEEG中使用（向后兼容）
    ratio_labels = ['θ/α', 'θ/β', 'θ/高频', 'α/β', 'α/高频', 'β/高频',
                    '高频/低频', '低频/高频', 'δ/θ', 'δ/α', 'δ/β', 'δ/高频']

    # 注释掉QEEG中的比率处理，这些数据现在由Ratio Mapping单独处理
    """
    if 'power_ratios' in qeeg_results:
        ratio_data = qeeg_results['power_ratios']
        ratio_imgs = ratio_data.get('images') or ratio_data.get('topo_imgs') or []

        if not ratio_imgs and 'data' in ratio_data:
            info = qeeg_results.get('info')
            channel_names = qeeg_results.get('channel_names')

            if isinstance(ratio_data['data'], dict):
                ratio_imgs = generate_topography_matrix(
                    ratio_data['data'], info=info, channel_names=channel_names,
                    frequencies=None, global_vlim=True, cmap=TOPO_COLORMAP
                )

        formatted_ratio_imgs = []
        for i, img in enumerate(ratio_imgs):
            if isinstance(img, dict):
                url = img.get('url', '')
                # 如果图片数据中有name或label字段，使用它；否则使用预定义的标签
                label = img.get('name') or img.get('label') or (
                    ratio_labels[i] if i < len(ratio_labels) else f"Ratio{i + 1}")
            else:
                url = str(img)
                label = ratio_labels[i] if i < len(ratio_labels) else f"Ratio{i + 1}"

            formatted_ratio_imgs.append({
                'url': url,
                'label': label
            })
        result['ratio_imgs'] = formatted_ratio_imgs

    # 处理比率Z-Score（12个比率）
    if 'ratio_zscore' in qeeg_results:
        ratio_zscore_data = qeeg_results['ratio_zscore']
        ratio_zscore_imgs = ratio_zscore_data.get('images') or ratio_zscore_data.get('topo_imgs') or []

        if not ratio_zscore_imgs and 'data' in ratio_zscore_data:
            info = qeeg_results.get('info')
            channel_names = qeeg_results.get('channel_names')

            if isinstance(ratio_zscore_data['data'], dict):
                ratio_zscore_imgs = generate_topography_matrix(
                    ratio_zscore_data['data'], info=info, channel_names=channel_names,
                    frequencies=None, global_vlim=True, cmap=TOPO_COLORMAP
                )

        formatted_ratio_zscore_imgs = []
        for i, img in enumerate(ratio_zscore_imgs):
            if isinstance(img, dict):
                url = img.get('url', '')
                label = img.get('name') or img.get('label') or (
                    ratio_labels[i] if i < len(ratio_labels) else f"Ratio{i + 1}")
            else:
                url = str(img)
                label = ratio_labels[i] if i < len(ratio_labels) else f"Ratio{i + 1}"

            formatted_ratio_zscore_imgs.append({
                'url': url,
                'label': label
            })
        result['ratio_zscore_imgs'] = formatted_ratio_zscore_imgs
    """

    return result


def prepare_ratio_mapping_data(algo_results):
    """
    准备 Ratio Mapping 数据用于渲染
    
    期望输入格式:
    {
        "power_ratios": {
            "images": [...] or "data": {...}  # 12个比率
        },
        "ratio_zscore": {
            "images": [...] or "data": {...}  # 12个比率的Z-Score
        },
        "info": {...},  # MNE Info对象（可选）
        "channel_names": [...]  # 通道名称列表（可选）
    }
    
    返回准备渲染的数据
    """
    result = {}

    # Ratio Mapping 的12种比率标签:
    # 1. θ/α, 2. θ/β, 3. θ/Hiβ, 4. α/β, 5. α/Hiβ, 6. β/Hiβ
    # 7. Hiθ/Loα, 8. Loα/Hiα, 9. δ/θ, 10. δ/α, 11. δ/β, 12. δ/Hiβ
    ratio_labels = ['θ/α', 'θ/β', 'θ/高频', 'α/β', 'α/高频', 'β/高频',
                    '高频/低频', '低频/高频', 'δ/θ', 'δ/α', 'δ/β', 'δ/高频']

    # 处理功率比率（12个比率）
    if 'power_ratios' in algo_results:
        ratio_data = algo_results['power_ratios']
        ratio_imgs = ratio_data.get('images') or ratio_data.get('topo_imgs') or []

        if not ratio_imgs and 'data' in ratio_data:
            info = algo_results.get('info')
            channel_names = algo_results.get('channel_names')

            if isinstance(ratio_data['data'], dict):
                ratio_imgs = generate_topography_matrix(
                    ratio_data['data'], info=info, channel_names=channel_names,
                    frequencies=None, global_vlim=True, cmap=TOPO_COLORMAP
                )

        formatted_ratio_imgs = []
        for i, img in enumerate(ratio_imgs):
            if isinstance(img, dict):
                url = img.get('url', '')
                # 如果图片数据中有name或label字段，使用它；否则使用预定义的标签
                label = img.get('name') or img.get('label') or (
                    ratio_labels[i] if i < len(ratio_labels) else f"Ratio{i + 1}")
            else:
                url = str(img)
                label = ratio_labels[i] if i < len(ratio_labels) else f"Ratio{i + 1}"

            vmin = img.get('vmin') if isinstance(img, dict) else None
            vmax = img.get('vmax') if isinstance(img, dict) else None

            formatted_ratio_imgs.append({
                'url': url,
                'label': label,
                'vmin': vmin ,
                'vmax': vmax  ,
            })
        result['ratio_imgs'] = formatted_ratio_imgs

    # 处理比率Z-Score（12个比率）
    if 'ratio_zscore' in algo_results:
        ratio_zscore_data = algo_results['ratio_zscore']
        ratio_zscore_imgs = ratio_zscore_data.get('images') or ratio_zscore_data.get('topo_imgs') or []

        if not ratio_zscore_imgs and 'data' in ratio_zscore_data:
            info = algo_results.get('info')
            channel_names = algo_results.get('channel_names')

            if isinstance(ratio_zscore_data['data'], dict):
                ratio_zscore_imgs = generate_topography_matrix(
                    ratio_zscore_data['data'], info=info, channel_names=channel_names,
                    frequencies=None, global_vlim=True, cmap=TOPO_COLORMAP
                )

        formatted_ratio_zscore_imgs = []
        for i, img in enumerate(ratio_zscore_imgs):
            if isinstance(img, dict):
                url = img.get('url', '')
                label = img.get('name') or img.get('label') or (
                    ratio_labels[i] if i < len(ratio_labels) else f"Ratio{i + 1}")
            else:
                url = str(img)
                label = ratio_labels[i] if i < len(ratio_labels) else f"Ratio{i + 1}"

            formatted_ratio_zscore_imgs.append({
                'url': url,
                'label': label,
            })
        result['ratio_zscore_imgs'] = formatted_ratio_zscore_imgs

    return result


from src.Infrastructure.log.QLLogging import QLLogging


# ==========================================
# 核心报告引擎：动态组装 HTML
# ==========================================
class DynamicReportEngine:
    def __init__(self, logo_path=None, parent=None):
        """初始化报告引擎，加载logo图片和headmodel背景图片
        
        Args:
            logo_path: 可选的logo图片路径。如果提供，将使用该路径；否则使用默认路径
            parent: 可选的父窗口（QWidget），用于显示消息框
        """
        self.parent = parent  # 保存父窗口引用，用于显示消息框
        current_dir = os.path.dirname(os.path.abspath(__file__))
        dir = os.path.dirname(os.path.abspath(sys.executable))

        user_logo_path = os.path.join(current_dir, '..', 'resource', 'user_logo')
        user_logo_path = os.path.normpath(user_logo_path)  # 规范化路径，将..解析掉
        if not os.path.exists(user_logo_path):
            user_logo_path = os.path.join(dir, 'resource', 'user_logo')

        # 新增：自动创建目标目录（无论路径是否存在，确保文件夹可用）
        os.makedirs(user_logo_path, exist_ok=True)

        logo_img = self.get_latest_image(user_logo_path)

        if logo_path is not None:
            self.logo_base64 = self._load_logo_image(logo_path)
        elif logo_img is not None:
            self.logo_base64 = self._load_logo_image(logo_img)
        else:
            self.logo_base64 = self._load_logo_image()  # 加载默认logo

        # 头模型图片
        self.headmodel_base64 = self._load_headmodel_image()

    def get_latest_image(self, directory):
        """
        遍历指定目录，按修改时间获取最新的图片文件
        :param directory: 目标文件夹路径
        :return: 最新图片的完整路径，无有效文件则返回 None
        """
        # 1. 定义支持的图片格式（可自行增删）
        SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff')

        # 2. 校验目录是否存在
        if not os.path.isdir(directory):
            # 使用保存的父窗口，如果没有则使用None（避免类型错误）
            parent_widget = self.parent if hasattr(self, 'parent') else None
            QMessageBox.warning(parent_widget, "提示", "图片目录不存在！")
            return None

        image_files = []
        # 3. 遍历目录，筛选图片文件
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            # 只处理文件，排除子目录
            if os.path.isfile(file_path):
                # 小写后缀名，兼容大小写格式
                if filename.lower().endswith(SUPPORTED_FORMATS):
                    # 获取文件创建时间戳
                    mtime = os.path.getctime(file_path)
                    image_files.append((mtime, file_path))

        # 4. 无图片文件时
        if not image_files:
            return None

        # 5. 按时间戳【降序】排序，取第一个即为最新文件
        image_files.sort(reverse=True, key=lambda x: x[0])
        latest_image_path = image_files[0][1]
        return latest_image_path

    def _load_logo_image(self, custom_logo_path=None):
        """加载logo图片并转换为base64
        
        Args:
            custom_logo_path: 可选的logo图片路径。如果提供，将使用该路径；否则使用默认路径
        """
        try:
            # 如果提供了自定义路径，使用它；否则使用默认路径
            if custom_logo_path and os.path.exists(custom_logo_path):
                logo_path = os.path.normpath(custom_logo_path)
            else:
                # 获取当前文件所在目录
                current_dir = os.path.dirname(os.path.abspath(__file__))
                # 构建logo图片路径：AR_analyser_PC/resource/picture/qlanalyser logo2x.png
                logo_path = os.path.join(current_dir, '..', 'resource', 'picture', 'qlanalyser logo2x.png')
                logo_path = os.path.normpath(logo_path)

            if os.path.exists(logo_path):
                with open(logo_path, 'rb') as f:
                    img_data = f.read()
                    img_base64 = base64.b64encode(img_data).decode()
                    # 根据文件扩展名确定MIME类型
                    ext = os.path.splitext(logo_path)[1].lower()
                    mime_type = 'image/png'
                    if ext == '.jpg' or ext == '.jpeg':
                        mime_type = 'image/jpeg'
                    elif ext == '.svg':
                        mime_type = 'image/svg+xml'
                    return f"data:{mime_type};base64,{img_base64}"
            else:
                if custom_logo_path:
                    print(f"警告: 自定义Logo图片未找到: {logo_path}")
                else:
                    print(f"警告: Logo图片未找到: {logo_path}")
                return None
        except Exception as e:
            print(f"加载logo图片失败: {e}")
            return None

    def update_logo(self, logo_path=None):
        """更新logo图片
        
        Args:
            logo_path: 可选的logo图片路径。如果提供，将使用该路径；否则使用默认路径
        """
        self.logo_base64 = self._load_logo_image(logo_path)
        return self.logo_base64

    def _load_headmodel_image(self):
        """加载headmodel背景图片并转换为base64"""
        try:
            # 获取当前文件所在目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            dir = os.path.dirname(os.path.abspath(sys.executable))

            # 构建headmodel图片路径：AR_analyser_PC/resource/picture/headmodel.png
            headmodel_path = os.path.join(current_dir, '..', 'resource', 'picture', 'headmodel.png')
            headmodel_path = os.path.normpath(headmodel_path)
            if not os.path.exists(headmodel_path):
                headmodel_path = os.path.join(dir, 'resource', 'picture', 'headmodel.png')

            if os.path.exists(headmodel_path):
                with open(headmodel_path, 'rb') as f:
                    img_data = f.read()
                    img_base64 = base64.b64encode(img_data).decode()
                    return f"data:image/png;base64,{img_base64}"
            else:
                print(f"警告: Headmodel图片未找到: {headmodel_path}")
                return None
        except Exception as e:
            print(f"加载headmodel图片失败: {e}")
            return None

    @staticmethod
    def _make_psd_channel_img_data_url(channel_name: str, values: dict):
        """
        生成一个“伪PSD结果图像”（SVG -> data url）。
        目的：在 main 中模拟“算法直接返回每个通道的结果图像”而不引入额外依赖（如PIL）。
        """
        print(np.linspace(1, 30, 7))
        try:
            import urllib.parse

            delta_val = float(values.get('delta', 0) or 0)
            theta_val = float(values.get('theta', 0) or 0)
            alpha_val = float(values.get('alpha', 0) or 0)
            beta_val = float(values.get('beta', 0) or 0)
            smr_val = float(values.get('alpha', 0) or 0)
            high_beta_val = float(values.get('high_beta', 0) or 0)
            gamma_val = float(values.get('gamma', 0) or 0)

            maxv = max(delta_val, theta_val, alpha_val, beta_val, smr_val, high_beta_val, gamma_val, 1.0)

            # 1. 定义目标波段
            target_bands = ['delta', 'theta', 'alpha', 'beta', 'smr', 'high_beta', 'gamma']
            # 2. 读取原始数据
            raw_values = [values.get(band, 0) for band in target_bands]

            # 3. 对数变换核心逻辑：处理0和负数，避免log计算异常
            log_values = []
            for val in raw_values:
                if val <= 0:
                    # 非正数赋值极小值，保证对数有效，不影响可视化
                    log_val = math.log10(1e-10)
                else:
                    # 以10为底取对数，适配科学计数法数据
                    log_val = math.log10(val)
                log_values.append(log_val)

            # 4. 对对数变换后的数据做最大值归一化到0-100%
            max_log = max(log_values) if log_values else 1.0
            psd_values = {
                band: round((log_val / max_log) * 100, 2)
                for band, log_val in zip(target_bands, log_values)
            }

            # --- 1. 环境与风格配置 ---
            # 设置全局字体，学术图表常用 Arial 或 Helvetica
            plt.rcParams['font.family'] = 'sans-serif'
            plt.rcParams['font.sans-serif'] = ['Arial']

            # 创建画布，尺寸放大 1.5 倍以提升报告中的可视化尺寸
            fig, ax = plt.subplots(figsize=(12, 7.5), dpi=180)

            # --- 2. 定义 Cell 风格配色方案 ---
            # 线条颜色：深青色 (Deep Teal)
            line_color = '#00796B'
            # 频段背景色：鲜艳但高透明度的浅色调
            band_colors = {
                'Delta': '#D9F7FF',  # 浅蓝
                'Theta': '#DBFAE0',  # 浅绿
                'Alpha': '#FFF3E0',  # 浅橙
                'SMR': '#FFE9F6',  # 浅粉红
                'Beta': '#FDF3FF',  # 浅紫
                'High_beta': '#DEEEFF',  # 浅青蓝
                'Gamma': '#ECF7CF',  # 浅柠绿
            }

            # 定义波段范围
            bands = [
                (1, 4, 'Delta'),
                (4, 8, 'Theta'),
                (8, 13, 'Alpha'),
                (12, 15, 'SMR'),
                (13, 30, 'Beta'),
                (21, 30, 'High_beta'),
                (30, 45, 'Gamma'),
            ]

            # --- 3. 绘制频段背景阴影 (The Bands) ---
            # 我们先画阴影，再画线，这样线会浮在阴影上方
            for start, end, name in bands:
                # axvspan 用于绘制垂直跨度的矩形
                # alpha=0.9 确保颜色鲜艳，zorder=1 放在底层
                ax.axvspan(start, end, color=band_colors[name], alpha=1, zorder=1)

                # 在阴影上方添加波段名称标注
                # 放置在 y 轴顶部，稍微偏移
                ax.text((start + end) / 2, max(psd_values) * 1.05, name,
                        ha='center', va='bottom', fontsize=10,
                        color='#78909C', fontweight='bold', transform=ax.transData)

            # --- 4. 绘制 PSD 主曲线 ---
            # linewidth=2.5 让线条更清晰
            # zorder=5 确保线条在阴影和网格之上
            freqs = np.linspace(0, 30, 600)

            ax.plot(freqs, psd_values, color=line_color, linewidth=2.5, zorder=5)

            # --- 5. 坐标轴修饰 (Cell 风格精髓) ---
            # 设定范围
            ax.set_xlim(0, 30)
            # 去掉频段名称后 y 轴顶部不再因文字被撑高，设置小量顶部 margin 消除多余空白
            ax.margins(y=0.05)

            # 设置标签，加粗字体
            ax.set_xlabel('Frequency (Hz)', fontsize=14, fontweight='bold', labelpad=10)
            ax.set_ylabel('Relative Power', fontsize=14, fontweight='bold', labelpad=10)

            # 移除顶部和右侧的“框框” (Spines)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            # 加粗左侧和底部的轴线
            ax.spines['left'].set_linewidth(1.5)
            ax.spines['bottom'].set_linewidth(1.5)

            # 刻度设置：向内显示，加粗线宽
            ax.tick_params(direction='in', length=6, width=1.5, labelsize=12)

            # 添加淡色水平参考网格线
            ax.yaxis.grid(True, linestyle='--', alpha=0.3, zorder=0)

            # 自动调整布局，防止标签被切掉
            plt.tight_layout()

            print("绘图完成！建议保存为 PDF 或高 DPI 的 PNG。")
            return fig

            # SVG 坐标：宽100 高60，底部留出文字区
            # 柱子从下往上画：y = 46 - height
            svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="100" height="60" viewBox="0 0 100 60">
  <rect x="0" y="0" width="100" height="60" fill="#ffffff"/>
  <text x="50" y="10" text-anchor="middle" font-size="10" fill="#1f2d3d">{channel_name}</text>
  <line x1="6" y1="46" x2="94" y2="46" stroke="#dfe7f1" stroke-width="1"/>
  <rect x="16" y="{46 - h(d)}" width="10" height="{h(d)}" fill="#4A90E2"/>
  <rect x="34" y="{46 - h(t)}" width="10" height="{h(t)}" fill="#50C878"/>
  <rect x="52" y="{46 - h(a)}" width="10" height="{h(a)}" fill="#FFD700"/>
  <rect x="70" y="{46 - h(b)}" width="10" height="{h(b)}" fill="#FF6B6B"/>
  <text x="21" y="57" text-anchor="middle" font-size="8" fill="#667085">δ</text>
  <text x="39" y="57" text-anchor="middle" font-size="8" fill="#667085">θ</text>
  <text x="57" y="57" text-anchor="middle" font-size="8" fill="#667085">α</text>
  <text x="75" y="57" text-anchor="middle" font-size="8" fill="#667085">β</text>
</svg>"""
            # 用 utf8 svg + urlencoded（避免 base64 体积更大且不需要额外模块）
            return "data:image/svg+xml;utf8," + urllib.parse.quote(svg)
        except Exception as e:
            print(f"生成通道SVG失败: {e}")
            return None

    @staticmethod
    def _format_faa_value(faa_data):
        """从 faa_data 中取出 faa_percentage（百分比如163.1%），显示为比值（如 1.6）。"""
        if not faa_data or not isinstance(faa_data, dict):
            return None
        val = faa_data.get('faa_percentage')
        if val is None:
            return None
        try:
            # 计算比值
            ratio = float(val) / 100.0
            # 四舍五入保留1位小数
            rounded_ratio = round(ratio, 1)
            # 解决 -0.0 显示问题：如果结果为0，统一显示 "0.0"
            if rounded_ratio == 0:
                return "0.0"
            return f"{rounded_ratio:.1f}"
        except (ValueError, TypeError):
            return None

    # 定义各组件的 HTML 模板片段
    COMPONENTS = {
        "header": """
            <div class="header">
                <h1>Carebird 知心鸟 - 脑电分析报告</h1>
                <div class="patient-info">
                    <span>姓名: {{ name }}</span> | <span>年龄: {{ age }}</span> | <span>测试日期: {{ date }}</span>
                </div>
            </div>
        """,
        "page_header": """
            <div class="page-header">
                <div class="page-header-left">
                    <div class="logo-section">
                        {% if logo_base64 %}
                        <img src="{{ logo_base64 }}" alt="QLanalyser" class="logo-image" />
                        {% else %}
                        <div class="logo-icon">
                            <svg width="40" height="40" viewBox="0 0 40 40">
                                <circle cx="20" cy="20" r="18" fill="#4A90E2" opacity="0.9"/>
                                <path d="M10 20 Q15 12, 20 15 T30 20" stroke="#B0D4FF" stroke-width="2" fill="none"/>
                                <path d="M10 20 Q15 18, 20 21 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                <path d="M10 20 Q15 22, 20 19 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                            </svg>
                        </div>
                        <div class="logo-text"><span class="ql-part">QL</span><span class="analyser-part">analyser</span></div>
                        {% endif %}
                    </div>
                </div>
                <div class="page-header-right">
                    <div class="report-title-main">脑电分析报告</div>
                    <div class="report-date">报告日期: {{ date }}</div>
                </div>
            </div>
            <div class="header-divider"></div>
            {% if patient_info %}
            <div class="patient-info-box">
                <div class="info-row">
                    <div class="info-item">
                        <span class="info-label">姓名:</span>
                        <span class="info-value">{{ patient_info.name or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">性别:</span>
                        <span class="info-value">{{ patient_info.gender or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">年龄:</span>
                        <span class="info-value">{{ patient_info.age or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">采集时间:</span>
                        <span class="info-value">{{ patient_info.collection_time or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">采集人:</span>
                        <span class="info-value">{{ patient_info.collector or 'N/A' }}</span>
                    </div>
                </div>
            </div>
            {% endif %}
        """,
        "neuro_metrics_analysis": """
            <div class="page-section">
                <div class="page-header">
                    <div class="page-header-left">
                        <div class="logo-section">
                            {% if logo_base64 %}
                            <img src="{{ logo_base64 }}" alt="QLanalyser" class="logo-image" />
                            {% else %}
                            <div class="logo-icon">
                                <svg width="40" height="40" viewBox="0 0 40 40">
                                    <circle cx="20" cy="20" r="18" fill="#4A90E2" opacity="0.9"/>
                                    <path d="M10 20 Q15 12, 20 15 T30 20" stroke="#B0D4FF" stroke-width="2" fill="none"/>
                                    <path d="M10 20 Q15 18, 20 21 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                    <path d="M10 20 Q15 22, 20 19 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                </svg>
                            </div>
                            <div class="logo-text"><span class="ql-part">QL</span><span class="analyser-part">analyser</span></div>
                            {% endif %}
                        </div>
                    </div>
                    <div class="page-header-right">
                        <div class="report-title-main">脑电分析报告</div>
                        <div class="report-date">报告日期: {{ patient_info.date or 'N/A' }}</div>
                    </div>
                </div>
                <div class="header-divider"></div>
                <div class="patient-info-box">
                    <div class="info-row">
                    <div class="info-item">
                        <span class="info-label">姓名:</span>
                        <span class="info-value">{{ patient_info.name or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">性别:</span>
                        <span class="info-value">{{ patient_info.gender or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">年龄:</span>
                        <span class="info-value">{{ patient_info.age or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">采集时间:</span>
                        <span class="info-value">{{ patient_info.collection_time or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">采集人:</span>
                        <span class="info-value">{{ patient_info.collector or 'N/A' }}</span>
                    </div>
                    </div>
                </div>
                <div class="section-content">
                <div class="analysis-name analysis-name-two-line">
                    <span class="analysis-name-main">脑功能核心指标分析</span>
                    <span class="analysis-name-en">Core Neuro Metrics Analysis</span>
                </div>
                <!--  指标卡片区域 -->
                <div class="neuro-metrics-container">
                    <div class="metrics-grid">
                    
                    <!-- 卡片：Alpha峰频(PAF)，支持多任务每任务一卡 -->
                        {% if has_paf %}
                        {% for paf_item in paf_items %}
                        <div class="metric-card card-1">
                            <div class="card-header">
                                <div class="card-header-left card-header-compact">
                                    <div class="card-title card-title-compact">Alpha峰频(PAF){% if paf_item.task_name %} - {{ paf_item.task_name }}{% endif %}</div>
                                    <div class="card-subtitle card-subtitle-compact">A波峰值频率</div>
                                    <div class="card-subtitle card-subtitle-compact card-subtitle-en">Peak Alpha Frequency（PAF）</div>
                                </div>
                                <div class="card-header-right">
                                    <div class="metric-value-large">{% if paf_item.paf_value is not none %}{{ "%.1f"|format(paf_item.paf_value|float) }} Hz{% else %}N/A{% endif %}</div>
                                    <div class="ref-value-simple">参考: 8-12 Hz</div>
                                </div>
                            </div>
                            <div class="card-content">
                                <div class="score-bar">
                                    <!-- 分段色块 -->
                                    <div class="bar-segments">
                                        <!-- 左边红色区间（超出范围） -->
                                        <div class="segment seg-out-left" style="background-color: #ef4444;"></div>
                                        {% set grade_segments = [
                                            {'class': 'seg-f', 'label': paf_grade_labels[0] if paf_grade_labels|length > 0 else 'E'},
                                            {'class': 'seg-e', 'label': paf_grade_labels[1] if paf_grade_labels|length > 1 else 'C'},
                                            {'class': 'seg-d', 'label': paf_grade_labels[2] if paf_grade_labels|length > 2 else 'A'},
                                            {'class': 'seg-c', 'label': paf_grade_labels[3] if paf_grade_labels|length > 3 else 'C'},
                                            {'class': 'seg-b', 'label': paf_grade_labels[4] if paf_grade_labels|length > 4 else 'E'}
                                        ] %}
                                        {% for segment in grade_segments %}
                                        <div class="segment {{ segment.class }}">{{ segment.label }}</div>
                                        {% endfor %}
                                        <!-- 右边红色区间（超出范围） -->
                                        <div class="segment seg-out-right" style="background-color: #ef4444;"></div>
                                    </div>
                                    <!-- 底部刻度 -->
                                    <div class="scale">
                                        <span class="tick tick-out-left">4</span>
                                        <span class="tick">6</span>
                                        <span class="tick">8</span>
                                        <span class="tick">12</span>
                                        <span class="tick">14</span>
                                        <span class="tick">16</span>
                                        <span class="tick tick-out-right"></span>
                                    </div>
                                    {% if paf_item.paf_pointer_position is not none %}
                                    <div class="arrow-indicator" style="left: {{ paf_item.paf_pointer_position }}%;"></div>
                                    {% endif %}
                                </div>
                                <div class="description-section">
                                    <div class="description-row">
                                        <i class="fas fa-chart-bar section-icon"></i>
                                        <span class="description-label">行为特征关联:</span>
                                        <span class="description-content">低PAF(<8Hz)通常与大脑处理信息的速度变慢有关,可能会表现为反应迟缓或工作记忆效率降低。</span>
                                    </div>
                                    <div class="description-row">
                                        <i class="fas fa-microscope section-icon"></i>
                                        <span class="description-label">指标生理含义:</span>
                                        <span class="description-content">反映丘脑-皮层神经环路(Thalamo-cortical Loop)的振荡频率,被视为大脑基础信息处理的"时钟速度"(Clock Speed)。</span>
                                    </div>
                                </div>
                                <div class="spacer-after-description"></div>
                            </div>
                        </div>
                        {% endfor %}
                        {% endif %}
                        
                        <!-- 卡片2：注意力指数 (TBR)，支持多任务 -->
                        {% if has_tbr %}
                        {% for tbr_item in tbr_items %}
                        <div class="metric-card card-2">
                            <div class="card-header">
                                <div class="card-header-left card-header-compact">
                                    <div class="card-title card-title-compact">注意力指数 (TBR){% if tbr_item.task_name %} - {{ tbr_item.task_name }}{% endif %}</div>
                                    <div class="card-subtitle card-subtitle-compact">Θ/B 比值(THETA/BETA 比率)</div>
                                    <div class="card-subtitle card-subtitle-compact card-subtitle-en">Theta/Beta Ratio (TBR)</div>
                                </div>
                                <div class="card-header-right">
                                    <div class="metric-value-large">{% if tbr_item.tbr_value is not none %}{{ "%.1f"|format(tbr_item.tbr_value|float) }}{% else %}N/A{% endif %}</div>
                                    <div class="ref-value-simple">参考: &lt; 1.0</div>
                                </div>
                            </div>
                            <div class="card-content">
                                <div class="score-bar">
                                    <div class="bar-segments">
                                        {% set tbr_grade_segments = [
                                            {'class': 'seg-a', 'label': tbr_grade_labels[0] if tbr_grade_labels|length > 0 else 'A'},
                                            {'class': 'seg-b', 'label': tbr_grade_labels[1] if tbr_grade_labels|length > 1 else 'B'},
                                            {'class': 'seg-c', 'label': tbr_grade_labels[2] if tbr_grade_labels|length > 2 else 'C'},
                                            {'class': 'seg-d', 'label': tbr_grade_labels[3] if tbr_grade_labels|length > 3 else 'D'},
                                            {'class': 'seg-e', 'label': tbr_grade_labels[4] if tbr_grade_labels|length > 4 else 'E'}
                                        ] %}
                                        {% for segment in tbr_grade_segments %}
                                        <div class="segment {{ segment.class }}">{{ segment.label }}</div>
                                        {% endfor %}
                                        <!-- 右边红色区间（超出范围） -->
                                        <div class="segment seg-out-right" style="background-color: #ef4444;"></div>
                                    </div>
                                    <div class="scale">
                                        <span class="tick tick-out-left">1</span>
                                        <span class="tick">1.5</span>
                                        <span class="tick">2</span>
                                        <span class="tick">2.5</span>
                                        <span class="tick">3</span>
                                        <span class="tick tick-out-right"></span>
                                    </div>
                                    {% if tbr_item.tbr_pointer_position is not none %}
                                    <div class="arrow-indicator" style="left: {{ tbr_item.tbr_pointer_position }}%;"></div>
                                    {% endif %}
                                </div>
                                <div class="description-section">
                                    <div class="description-row">
                                        <i class="fas fa-chart-bar section-icon"></i>
                                        <span class="description-label">行为特征关联:</span>
                                        <span class="description-content">这是评估专注力的经典指标。较高的比值意味着"慢波过多、快波过少",通常与注意力难以集中、容易分心或执行任务时感到疲倦有关。</span>
                                    </div>
                                    <div class="description-row">
                                        <i class="fas fa-microscope section-icon"></i>
                                        <span class="description-label">指标生理含义:</span>
                                        <span class="description-content">量化皮层唤醒水平(Cortical Arousal)。Theta 波代表皮层抑制或困倦,Beta 波代表皮层兴奋或认知加工状态。</span>
                                    </div>
                                </div>
                                <div class="spacer-after-description"></div>
                            </div>
                        </div>
                        {% endfor %}
                        {% endif %}
                        
                        <!-- 卡片3：前额 Alpha 非对称性 (FAA)，支持多任务 -->
                        {% if has_ffa %}
                        {% for faa_item in faa_items %}
                        <div class="metric-card card-3">
                            <div class="card-header">
                                <div class="card-header-left card-header-compact">
                                    <div class="card-title card-title-compact">情绪动机(FAA){% if faa_item.task_name %} - {{ faa_item.task_name }}{% endif %}</div>
                                    <div class="card-subtitle card-subtitle-compact">前额 Alpha 非对称性</div>
                                    <div class="card-subtitle card-subtitle-compact card-subtitle-en">Frontal Alpha Asymmetry (FAA)</div>
                                </div>
                                <div class="card-header-right">
                                    <div class="metric-value-large">{% if faa_item.faa_value is not none and faa_item.faa_value != 'N/A' %}{{ faa_item.faa_value }}{% else %}N/A{% endif %}</div>
                                    <div class="ref-value-simple">参考: -10% ~ 10%</div>
                                </div>
                            </div>
                            <div class="card-content">
                                <div class="score-bar">
                                    <div class="bar-segments">
                                        <!-- 左无名区间 -∞～-30（不标无穷） -->
                                        <div class="segment seg-out-left" style="background-color: #ef4444;"></div>
                                        {% set faa_grade_segments = [
                                            {'class': 'seg-f', 'label': faa_grade_labels[0] if faa_grade_labels|length > 0 else 'E'},
                                            {'class': 'seg-e', 'label': faa_grade_labels[1] if faa_grade_labels|length > 1 else 'C'},
                                            {'class': 'seg-d', 'label': faa_grade_labels[2] if faa_grade_labels|length > 2 else 'A'},
                                            {'class': 'seg-c', 'label': faa_grade_labels[3] if faa_grade_labels|length > 3 else 'C'},
                                            {'class': 'seg-b', 'label': faa_grade_labels[4] if faa_grade_labels|length > 4 else 'E'},
                                            {'class': 'seg-out-right', 'label': faa_grade_labels[5] if faa_grade_labels|length > 5 else ''}
                                        ] %}
                                        {% for segment in faa_grade_segments %}
                                        <div class="segment {{ segment.class }}" {% if segment.style %}style="{{ segment.style }}"{% endif %}>{{ segment.label }}</div>
                                        {% endfor %}
                                    </div>
                                    <div class="scale">
                                        <span class="tick tick-out-left">-30</span>
                                        <span class="tick tick-no-value"></span>
                                        <span class="tick">-10</span>
                                        <span class="tick">0</span>
                                        <span class="tick">10</span>
                                        <span class="tick tick-no-value"></span>
                                        <span class="tick">30</span>
                                        <span class="tick tick-out-right"></span>
                                    </div>
                                    {% if faa_item.faa_pointer_position is not none %}
                                    <div class="arrow-indicator" style="left: {{ faa_item.faa_pointer_position }}%;"></div>
                                    {% endif %}
                                </div>
                                <div class="description-section">
                                    <div class="description-row">
                                        <i class="fas fa-chart-bar section-icon"></i>
                                        <span class="description-label">行为特征关联:</span>
                                        <span class="description-content">用于评估情绪倾向和动机模式。右侧额叶相对不活跃(即右侧Alpha高)可能与回避型动机、退缩行为或难以调节负面情绪有关。</span>
                                    </div>
                                    <div class="description-row">
                                        <i class="fas fa-microscope section-icon"></i>
                                        <span class="description-label">指标生理含义:</span>
                                        <span class="description-content">反映大脑半球间的功能侧化差异。该指标揭示了左右额叶在处理"趋近"与"回避"动机时的相对活跃度。</span>
                                    </div>
                                </div>
                                <div class="spacer-after-description"></div>
                            </div>
                        </div>
                        {% endfor %}
                        {% endif %}
                    
                        <!-- 卡片4：抑制指数 (Alpha Ratio)，支持多任务 -->
                        {% if has_alpha_ratio %}
                        {% for ar_item in alpha_ratio_items %}
                        <div class="metric-card card-4">
                            <div class="card-header">
                                <div class="card-header-left card-header-compact">
                                    <div class="card-title card-title-compact">抑制指数 (Alpha Ratio){% if ar_item.task_name %} - {{ ar_item.task_name }}{% endif %}</div>
                                    <div class="card-subtitle card-subtitle-compact">ALPHA 抑制指数</div>
                                    <div class="card-subtitle card-subtitle-compact card-subtitle-en">Alpha Ratio (EC/EO)</div>
                                </div>
                                <div class="card-header-right">
                                    <div class="metric-value-large">{% if ar_item.alpha_ratio_value and ar_item.alpha_ratio_value != 'N/A' %}{{ "%.1f"|format(ar_item.alpha_ratio_value|float) }}{% else %}N/A{% endif %}</div>
                                    <div class="ref-value-simple">参考: &gt; 1.2</div>
                                </div>
                            </div>
                            <div class="card-content">
                                <div class="score-bar">
                                    <!-- 分段色块 -->
                                    <div class="bar-segments">
                                        <!-- 左边红色区间（超出范围） -->
                                        <div class="segment seg-out-left" style="background-color: #ef4444;"></div>
                                        {% set alpha_ratio_grade_segments = [
                                            {'class': 'seg-f', 'label': alpha_ratio_grade_labels[0] if alpha_ratio_grade_labels|length > 0 else 'E'},
                                            {'class': 'seg-e', 'label': alpha_ratio_grade_labels[1] if alpha_ratio_grade_labels|length > 1 else 'D'},
                                            {'class': 'seg-d', 'label': alpha_ratio_grade_labels[2] if alpha_ratio_grade_labels|length > 2 else 'B'},
                                            {'class': 'seg-a', 'label': alpha_ratio_grade_labels[3] if alpha_ratio_grade_labels|length > 3 else 'A'},
                                            {'class': 'seg-out-right', 'label': '', 'style': 'background-color: #34d399;'}
                                        ] %}
                                        {% for segment in alpha_ratio_grade_segments %}
                                        <div class="segment {{ segment.class }}" {% if segment.style %}style="{{ segment.style }}"{% endif %}>{{ segment.label }}</div>
                                        {% endfor %}
                                    </div>
                                    <!-- 底部刻度 -->
                                    <div class="scale">
                                        <span class="tick tick-out-left">0.8</span>
                                        <span class="tick">1</span>
                                        <span class="tick">1.2</span>
                                        <span class="tick">1.4</span>
                                        <span class="tick">1.6</span>
                                        <span class="tick tick-out-right"></span>
                                    </div>
                                    {% if ar_item.alpha_ratio_pointer_position is not none %}
                                    <div class="arrow-indicator" style="left: {{ ar_item.alpha_ratio_pointer_position }}%;"></div>
                                    {% endif %}
                                </div>
                                <div class="description-section">
                                    <div class="description-row">
                                        <i class="fas fa-chart-bar section-icon"></i>
                                        <span class="description-label">行为特征关联:</span>
                                        <span class="description-content">该指标反映大脑从休息状态切换到工作状态的灵活性。比值偏低意味着大脑在睁眼准备处理信息时,未能有效抑制背景干扰,容易导致持续性注意力难以维持。</span>
                                    </div>
                                    <div class="description-row">
                                        <i class="fas fa-microscope section-icon"></i>
                                        <span class="description-label">指标生理含义:</span>
                                        <span class="description-content">衡量神经系统的视觉反应性与“去同步化”机制。反映了网状激活系统对Alpha 节律的阻滞能力。</span>
                                    </div>
                                </div>
                                <div class="spacer-after-description"></div>
                            </div>
                        </div>
                        {% endfor %}
                        {% endif %}
                        
                    </div>
                </div>
                </div>
                <!-- 页脚 -->
                <div class="page-footer">
                    <div class="footer-divider"></div>
                    <div class="footer-content">
                        <div class="footer-left">Generated by QL_analyser</div>
                        <div class="footer-right">Page <span class="current-page">{{ current_page }}</span> of {{ total_pages }}</div>
                    </div>
                </div>
            </div>
        """,
        "psd": """
            <div class="page-section psd-topography-section">
                <div class="page-header">
                    <div class="page-header-left">
                        <div class="logo-section">
                            {% if logo_base64 %}
                            <img src="{{ logo_base64 }}" alt="QLanalyser" class="logo-image" />
                            {% else %}
                            <div class="logo-icon">
                                <svg width="40" height="40" viewBox="0 0 40 40">
                                    <circle cx="20" cy="20" r="18" fill="#4A90E2" opacity="0.9"/>
                                    <path d="M10 20 Q15 12, 20 15 T30 20" stroke="#B0D4FF" stroke-width="2" fill="none"/>
                                    <path d="M10 20 Q15 18, 20 21 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                    <path d="M10 20 Q15 22, 20 19 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                </svg>
                            </div>
                            <div class="logo-text"><span class="ql-part">QL</span><span class="analyser-part">analyser</span></div>
                            {% endif %}
                        </div>
                    </div>
                    <div class="page-header-right">
                        <div class="report-title-main">脑电分析报告</div>
                        <div class="report-date">报告日期: {{ patient_info.date or 'N/A' }}</div>
                    </div>
                </div>
                <div class="header-divider"></div>
                <div class="patient-info-box">
                    <div class="info-row">
                    <div class="info-item">
                        <span class="info-label">姓名:</span>
                        <span class="info-value">{{ patient_info.name or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">性别:</span>
                        <span class="info-value">{{ patient_info.gender or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">年龄:</span>
                        <span class="info-value">{{ patient_info.age or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">采集时间:</span>
                        <span class="info-value">{{ patient_info.collection_time or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">采集人:</span>
                        <span class="info-value">{{ patient_info.collector or 'N/A' }}</span>
                    </div>
                    </div>
                </div>
                <div class="section-content">
                {% if analysis_method and 'PSD' not in analysis_method and 'Full-Band Power Distribution' not in analysis_method and 'Full-Band Ratio Distribution' not in analysis_method %}
                <div class="analysis-name">{{ (analysis_method or '')|replace(' - 新任务', '') }}</div>
                {% endif %}
                <!-- 分析方法描述区域 -->
                <div class="analysis-description-box">
                    <div class="analysis-description-content">
                        <div class="task-name-title">任务名称</div>
                        <div class="analysis-method-label">
                            分析方法: <span class="analysis-method-value">{{ (analysis_method or 'N/A')|replace(' - 新任务', '') }}</span>
                            {% if analysis_method and 'PSD' in analysis_method %}
                            <span class="analysis-method-chinese">功率谱密度分析</span>
                            {% elif analysis_method and 'Z-Score' in analysis_method %}
                            <span class="analysis-method-chinese">Z-Score分析</span>
                            {% elif analysis_method and 'Quantitative EEG Mapping' in analysis_method %}
                            <span class="analysis-method-chinese">定量脑电地形图</span>
                            {% elif analysis_method and '功率矩阵' in analysis_method %}
                            <span class="analysis-method-chinese">功率矩阵分析</span>
                            {% endif %}
                        </div>
                        <div class="analysis-description-text">
                            {% if analysis_method and 'PSD' in analysis_method %}
                            PSD分析展示了全脑各导联在不同频率下的能量分布情况,通过Welch法计算功率谱密度,能够直观地反映各频段(δ、θ、α、β)的能量特征,为临床诊断提供重要参考依据。
                            {% elif analysis_method and 'Z-Score' in analysis_method %}
                            Z-Score分析通过将个体数据与标准数据库进行对比,计算标准化得分,能够识别出与正常范围存在显著差异的脑区,为异常检测和诊断提供量化指标。
                            {% elif analysis_method and 'Quantitative EEG Mapping' in analysis_method %}
                            定量脑电地形图通过多频段功率分析和地形图可视化,全面展示全脑各区域的电活动特征,结合绝对功率、相对功率和比率分析,为临床评估提供综合性的量化数据。
                            {% elif analysis_method and '功率矩阵' in analysis_method %}
                            功率矩阵分析展示了各导联在不同频率下的功率分布情况,通过矩阵形式直观呈现全脑的能量分布模式,有助于识别异常脑区和频率特征。
                            {% else %}
                            本分析通过先进的信号处理算法,对脑电数据进行深入分析,提取关键特征参数,为临床诊断和评估提供科学依据。
                            {% endif %}
                        </div>
                    </div>
                </div>
                <div class="topography-container">
                    <div class="channels-wrapper">
                        {% for channel in channels %}
                        <div class="channel-panel" style="left: {{ channel.x }}%; top: {{ channel.y }}%;">
                            <div class="channel-header">{{ channel.name }}</div>
                            <div class="channel-content">
                                <div class="bar-chart">
                                    {% if channel.img %}
                                    <!-- 图片模式：只替换“左侧小图区域”，保持整体卡片布局/数值区不变 -->
                                    <img src="{{ channel.img }}" class="psd-channel-spark" alt="PSD {{ channel.name }}" />
                                    {% else %}
                                    <!-- 折线图模式：每个通道使用自己的坐标轴范围 -->
                                    <div class="line-chart-container">
                                        <svg class="line-chart-svg" viewBox="0 0 100 100" preserveAspectRatio="none" width="100%" height="100%">
                                            
                                                {# 首先计算当前通道的极值 #}
                                                {% set heights = [
                                                    channel.bar_heights.delta, 
                                                    channel.bar_heights.theta, 
                                                    channel.bar_heights.alpha, 
                                                    channel.bar_heights.beta
                                                ] %}
                                                {% set min_val = heights|min %}
                                                {% set max_val = heights|max %}
                                                {% set range_val = max_val - min_val if max_val > min_val else 1 %}
                                                
                                                {# 归一化函数：将值映射到10-80范围内（留出上下边距） #}
                                                {% macro normalize(value) -%}
                                                    {{ 80 - ((value - min_val) / range_val * 60) + 10 }}
                                                {%- endmacro %}
                                                
                                                <!-- 折线（蓝色） -->
                                                <polyline 
                                                    class="line-chart-path"
                                                    points="5,{{ normalize(channel.bar_heights.delta) }} 
                                                            20,{{ normalize(channel.bar_heights.theta) }} 
                                                            35,{{ normalize(channel.bar_heights.alpha) }} 
                                                            50,{{ normalize(channel.bar_heights.smr) }} 
                                                            65,{{ normalize(channel.bar_heights.beta) }},
                                                            80,{{ normalize(channel.bar_heights.high_beta) }},
                                                            95,{{ normalize(channel.bar_heights.gamma) }},"
                                                    fill="none"
                                                    stroke="#4A90E2"
                                                    stroke-width="2.5"
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                />
                                                
                                                <!-- 数据点（蓝色，带白色边框） -->
                                                <circle class="line-chart-point" cx="5" cy="{{ normalize(channel.bar_heights.delta) }}" r="3" fill="#4A90E2" stroke="white" stroke-width="1.5"/>
                                                <circle class="line-chart-point" cx="20" cy="{{ normalize(channel.bar_heights.theta) }}" r="3" fill="#4A90E2" stroke="white" stroke-width="1.5"/>
                                                <circle class="line-chart-point" cx="35" cy="{{ normalize(channel.bar_heights.alpha) }}" r="3" fill="#4A90E2" stroke="white" stroke-width="1.5"/>
                                                <circle class="line-chart-point" cx="50" cy="{{ normalize(channel.bar_heights.smr) }}" r="3" fill="#4A90E2" stroke="white" stroke-width="1.5"/>
                                                <circle class="line-chart-point" cx="65" cy="{{ normalize(channel.bar_heights.beta) }}" r="3" fill="#4A90E2" stroke="white" stroke-width="1.5"/>
                                                <circle class="line-chart-point" cx="80" cy="{{ normalize(channel.bar_heights.high_beta) }}" r="3" fill="#4A90E2" stroke="white" stroke-width="1.5"/>
                                                <circle class="line-chart-point" cx="95" cy="{{ normalize(channel.bar_heights.gamma) }}" r="3" fill="#4A90E2" stroke="white" stroke-width="1.5"/>
                                            
                                            <!-- 可选的背景网格线 -->
                                            <line class="line-grid" x1="5" y1="0" x2="5" y2="100" stroke="#f0f0f0" stroke-width="1" stroke-dasharray="2,2"/>
                                            <line class="line-grid" x1="20" y1="0" x2="20" y2="100" stroke="#f0f0f0" stroke-width="1" stroke-dasharray="2,2"/>
                                            <line class="line-grid" x1="35" y1="0" x2="35" y2="100" stroke="#f0f0f0" stroke-width="1" stroke-dasharray="2,2"/>
                                            <line class="line-grid" x1="50" y1="0" x2="50" y2="100" stroke="#f0f0f0" stroke-width="1" stroke-dasharray="2,2"/>
                                            <line class="line-grid" x1="65" y1="0" x2="65" y2="100" stroke="#f0f0f0" stroke-width="1" stroke-dasharray="2,2"/>
                                            <line class="line-grid" x1="80" y1="0" x2="80" y2="100" stroke="#f0f0f0" stroke-width="1" stroke-dasharray="2,2"/>
                                            <line class="line-grid" x1="95" y1="0" x2="95" y2="100" stroke="#f0f0f0" stroke-width="1" stroke-dasharray="2,2"/>
                                            
                                            <!-- X轴基线 -->
                                            <line class="line-axis" x1="0" y1="100" x2="100" y2="100" stroke="#cccccc" stroke-width="2"/>
                                        </svg>
                                    </div>
                                    {% endif %}
                                </div>                                
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                </div>
                <!-- 页脚 -->
                <div class="page-footer">
                    <div class="footer-divider"></div>
                    <div class="footer-content">
                        <div class="footer-left">Generated by QL_analyser</div>
                        <div class="footer-right">Page <span class="current-page">{{ current_page }}</span> of {{ total_pages }}</div>
                    </div>
                </div>
            </div>
        """,
        "zscore": """
            <div class="page-section">
                <div class="page-header">
                    <div class="page-header-left">
                        <div class="logo-section">
                            {% if logo_base64 %}
                            <img src="{{ logo_base64 }}" alt="QLanalyser" class="logo-image" />
                            {% else %}
                            <div class="logo-icon">
                                <svg width="40" height="40" viewBox="0 0 40 40">
                                    <circle cx="20" cy="20" r="18" fill="#4A90E2" opacity="0.9"/>
                                    <path d="M10 20 Q15 12, 20 15 T30 20" stroke="#B0D4FF" stroke-width="2" fill="none"/>
                                    <path d="M10 20 Q15 18, 20 21 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                    <path d="M10 20 Q15 22, 20 19 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                </svg>
                            </div>
                            <div class="logo-text"><span class="ql-part">QL</span><span class="analyser-part">analyser</span></div>
                            {% endif %}
                        </div>
                    </div>
                    <div class="page-header-right">
                        <div class="report-title-main">脑电分析报告</div>
                        <div class="report-date">报告日期: {{ patient_info.date or 'N/A' }}</div>
                    </div>
                </div>
                <div class="header-divider"></div>
                <div class="patient-info-box">
                    <div class="info-row">
                    <div class="info-item">
                        <span class="info-label">姓名:</span>
                        <span class="info-value">{{ patient_info.name or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">性别:</span>
                        <span class="info-value">{{ patient_info.gender or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">年龄:</span>
                        <span class="info-value">{{ patient_info.age or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">采集时间:</span>
                        <span class="info-value">{{ patient_info.collection_time or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">采集人:</span>
                        <span class="info-value">{{ patient_info.collector or 'N/A' }}</span>
                    </div>
                    </div>
                </div>
                <div class="section-content">
                <!-- 这里不再显示任务名称和Z-Score分析方法描述,直接展示Z评分结果 -->
                <!-- Z评分偏离分布图模块 -->
                <div class="zscore-deviation-section">
                    <div class="zscore-left-right-container">
                        <!-- 左侧：图片容器（移到首位） -->
                        <div class="zscore-right-img-box">
                          <img src="{{ img }}" alt="Z评分地形分布图" class="zscore-random-img">
                        </div>
                        <!-- 右侧：原有文字内容（顺序后移，无任何修改） -->
                        <div class="zscore-text-content">
                          <div class="zscore-map-header">
                            <h2 class="zscore-title">Z评分偏离分布图</h2>
                            <p class="zscore-title-en">Z-SCORE DEVIATION MAP</p>
                          </div>
                          <div class="zscore-map-desc">
                            <p>显著偏离(|Z|≥3.0)的地形分布。红色表示活动增强，蓝色表示活动减弱。</p>
                            <p class="zscore-desc-en">Topographic distribution of significant deviations.</p>
                          </div>
                          <div class="zscore-total-box">
                            <div class="zscore-total-icon">✓</div>
                            <div class="zscore-total-text">
                              <span class="zscore-total-label">偏离总数:</span>
                              <span class="zscore-total-num">{{ total_number }}</span>
                            </div>
                            <p class="zscore-total-en">TOTAL DEVIATIONS</p>
                          </div>
                        </div>
                    </div>
                    <div class="zscore-physio-box">
                        <h3 class="zscore-physio-title">生理含义说明 (Physiological Interpretation):</h3>
                        <p class="zscore-physio-text">
                            Z评分基于高斯分布统计模型，量化了受试者脑电特征与同年龄/性别健康常模数据库的偏离程度。<span class="zscore-red">红色(+Z)</span> 表示功率异常增强，通常与皮层去抑制、过度兴奋或代偿性活动有关（如焦虑、癫痫倾向）；<span class="zscore-blue">蓝色(-Z)</span> 表示功率异常降低，通常与皮层萎缩、神经元丢失或功能连接断裂有关（如脑损伤、认知退化）。
                        </p>
                    </div>
                </div>
                <table class="zscore-table">
                    <colgroup>
                      <col style="width: 18%;">  <!-- 第1列：区域列 -->
                      <col style="width: 13%;">  <!-- 第2列：频段列 -->
                      <col style="width: 13%;">  <!-- 第3列：zscore值列 -->
                      <col style="width: 56%;">  <!-- 第4列：功能列 -->
                    </colgroup>
                    <thead>
                        <tr>
                            <th>脑区名称</th>
                            <th>频段名称</th>
                            <th>Z 分数</th>
                            <th>功能解释</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in sites %}
                        {% set z_val = item.z if item.z is defined else (item.zscore if item.zscore is defined else 0) %}
                        {% set z_num = z_val | float %}
                        <tr>
                            <td class="col-region" >{{ item.site or item.ba_region or 'N/A' }}</td>
                            <td class="col-band" >{{ item.band or item.freq_band or 'N/A' }}</td>
                            <td class="zscore-value {% if z_num >= 0 %}zscore-positive{% else %}zscore-negative{% endif %}">
                                {% if z_num > 0 %}+{% endif %}{{ "%.2f"|format(z_num) }}
                            </td>
                            <td   class="col-func"  >{{ item.msg or item.functional_interp or 'N/A' }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                </div>
                <!-- 页脚 -->
                <div class="page-footer">
                    <div class="footer-divider"></div>
                    <div class="footer-content">
                        <div class="footer-left">Generated by QL_analyser</div>
                        <div class="footer-right">Page <span class="current-page">{{ current_page }}</span> of {{ total_pages }}</div>
                    </div>
                </div>
            </div>
        """,
        "absolute_power_matrix": """
            <div class="power-matrix-section">
                <div class="power-matrix-header">
                    <div class="power-matrix-title">绝对功率</div>
                    <div class="power-matrix-unit">单位: Hz</div>
                </div>
                <div class="power-matrix-divider"></div>
                <div class="topo-matrix-grid">
                    {% for img in topo_imgs %}
                    <div class="topo-matrix-item">
                        <img src="{{ img.url }}" alt="{{ img.freq }}">
                        <div class="topo-label">
                            <div class="freq-label">{{ img.freq }}</div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        """,
        "relative_power_matrix": """
            <div class="power-matrix-section">
                <div class="power-matrix-header">
                    <div class="power-matrix-title">相对功率</div>
                    <div class="power-matrix-unit">单位: Hz</div>
                </div>
                <div class="power-matrix-divider"></div>
                <div class="topo-matrix-grid">
                    {% for img in topo_imgs %}
                    <div class="topo-matrix-item">
                        <img src="{{ img.url }}" alt="{{ img.freq }}">
                        <div class="topo-label">
                            <div class="freq-label">{{ img.freq }}</div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        """,
        "power_matrices_container": """
            <div class="page-section power-mapping-page">
                <div class="page-header">
                    <div class="page-header-left">
                        <div class="logo-section">
                            {% if logo_base64 %}
                            <img src="{{ logo_base64 }}" alt="QLanalyser" class="logo-image" />
                            {% else %}
                            <div class="logo-icon">
                                <svg width="40" height="40" viewBox="0 0 40 40">
                                    <circle cx="20" cy="20" r="18" fill="#4A90E2" opacity="0.9"/>
                                    <path d="M10 20 Q15 12, 20 15 T30 20" stroke="#B0D4FF" stroke-width="2" fill="none"/>
                                    <path d="M10 20 Q15 18, 20 21 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                    <path d="M10 20 Q15 22, 20 19 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                </svg>
                            </div>
                            <div class="logo-text"><span class="ql-part">QL</span><span class="analyser-part">analyser</span></div>
                            {% endif %}
                        </div>
                    </div>
                    <div class="page-header-right">
                        <div class="report-title-main">脑电分析报告</div>
                        <div class="report-date">报告日期: {{ patient_info.date or 'N/A' }}</div>
                    </div>
                </div>
                <div class="header-divider"></div>
                <div class="patient-info-box">
                    <div class="info-row">
                    <div class="info-item">
                        <span class="info-label">姓名:</span>
                        <span class="info-value">{{ patient_info.name or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">性别:</span>
                        <span class="info-value">{{ patient_info.gender or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">年龄:</span>
                        <span class="info-value">{{ patient_info.age or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">采集时间:</span>
                        <span class="info-value">{{ patient_info.collection_time or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">采集人:</span>
                        <span class="info-value">{{ patient_info.collector or 'N/A' }}</span>
                    </div>
                    </div>
                </div>
                <div class="section-content">
                {% if analysis_method and 'PSD' not in analysis_method and 'Full-Band Power Distribution' not in analysis_method and 'Full-Band Ratio Distribution' not in analysis_method %}
                <div class="analysis-name">{{ (analysis_method or '')|replace(' - 新任务', '') }}</div>
                {% endif %}
                <!-- 分析方法描述区域 -->
                <div class="analysis-description-box">
                    <div class="analysis-description-content">
                        <div class="task-name-title">任务名称</div>
                        <div class="analysis-method-label">
                            分析方法: <span class="analysis-method-value">{{ (analysis_method or 'N/A')|replace(' - 新任务', '') }}</span>
                            {% if analysis_method and ('Full-Band Power Distribution' in analysis_method or '全频段功率分布' in analysis_method or 'Full Band Mapping' in analysis_method or '功率矩阵' in analysis_method) %}
                            <span class="analysis-method-chinese">全频段功率分布</span>
                            {% endif %}
                        </div>
                        <div class="analysis-description-text">
                            {% if analysis_method and ('Full-Band Power Distribution' in analysis_method or '全频段功率分布' in analysis_method or 'Full Band Mapping' in analysis_method or '功率矩阵' in analysis_method) %}
                            生成 2-34Hz (2Hz步进)的绝对功率与相对功率地形图矩阵,展示全频段能量空间分布特征。展示绝对功率、绝对功率在常模中的分布(Z-Score)、相对功率和相对功率在常模中的分布(Z-Score)四个维度的分析结果,为临床诊断和评估提供全面的量化指标。
                            {% else %}
                            本分析通过先进的信号处理算法,对脑电数据进行深入分析,提取关键特征参数,为临床诊断和评估提供科学依据。
                            {% endif %}
                        </div>
                    </div>
                </div>
                <!-- Full-Band Power Distribution 布局：绝对功率、相对功率、绝对功率Z-Score、相对功率Z-Score - 2x2网格布局 -->
                <div class="power-matrices-container">

                    <!-- 左上：绝对功率 -->
                    <div class="power-matrix-section">
                        <div class="power-matrix-header">
                            <div class="power-matrix-title power-matrix-title-two-line">
                                <span class="power-matrix-title-main">绝对功率(μV<sup>2</sup>)</span>
                                <span class="power-matrix-title-en">Absolute Power</span>
                            </div>
                        </div>
                        <div class="power-matrix-divider"></div>
                        {% if absolute_topo_imgs %}
                        <div class="topo-matrix-grid topo-matrix-grid-4x4">
                            {% for img in absolute_topo_imgs %}
                            <div class="topo-matrix-item" data-label="{{ img.get('freq', img.get('label', '')) }}">
                                <img src="{{ img.url }}" alt="{{ img.get('freq', img.get('label', '')) }}">
                                <span class="topo-label" style="font-size: 9px; color: #333; text-align: center; margin-top: 1px;">{{ img.get('freq', img.get('label', '')) }}</span>
                                
                                <!-- 增加子图色度条 -->
                                <div style="width: 100%; margin-top: 1px;">
                                    <div style="width: 50px; margin: 0 auto; height: 3px; border-radius: 2px; background: {{ hex_colors_css }};"></div>
                                    <div style="display:flex; justify-content:space-between;  width: calc(100% - 20px); padding-left:10px;font-size:6px; color:#666; line-height:1.1; margin-top:1px;">
                                        <span>{{ "%.1f"|format((img.get('vmin', 999))|float) }}</span>
                                        <span>{{ "%.1f"|format((img.get('vmax', 999))|float) }} μV<sup>2</sup></span>
                                    </div>
                                </div>                        

                            </div>
                            {% endfor %}
                        </div>
                        {% else %}
                        <div class="matrix-placeholder">
                            <p>暂无数据</p>
                        </div>
                        {% endif %}
                    </div>

                    <!-- 右上：绝对功率在常模中的分布 -->
                    <div class="power-matrix-section">
                        <div class="power-matrix-header">
                            <div class="power-matrix-title power-matrix-title-two-line">
                                <span class="power-matrix-title-main">绝对功率在常模中的分布(Z-Score)</span>
                                <span class="power-matrix-title-en">Abs. Power Norm Distribution (Z-Score)</span>
                            </div>
                        </div>
                        <div class="power-matrix-divider"></div>
                        {% if absolute_zscore_topo_imgs %}
                        <div class="topo-matrix-grid topo-matrix-grid-4x4">
                            {% for img in absolute_zscore_topo_imgs[:9] %}
                            <div class="topo-matrix-item" data-label="{{ img.get('freq', img.get('label', '')) }}">
                                <img src="{{ img.url }}" alt="{{ img.get('freq', img.get('label', '')) }}">
                                <span class="topo-label" style="font-size: 9px; color: #333; text-align: center; margin-top: 1px;">{{ img.get('freq', img.get('label', '')) }}</span>
                            
                            </div>
                            {% endfor %}
                        </div>
                        {% else %}
                        <div class="matrix-placeholder">
                            <p>暂无数据</p>
                        </div>
                        {% endif %}
                        <div class="module-colorbar-wrap" style="margin-top: 7px;">
                            <div class="module-colorbar-legend">
                                <span class="cb-tick">-3</span>
                                <span class="cb-bar" style="background: {{ hex_colors_css }};"></span>
                                <span class="cb-tick">3</span>
                                <span class="cb-unit">SD</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="power-matrices-container">
                    <!-- 左下：相对功率 -->
                    <div class="power-matrix-section">
                        <div class="power-matrix-header">
                            <div class="power-matrix-title power-matrix-title-two-line">
                                <span class="power-matrix-title-main">相对功率</span>
                                <span class="power-matrix-title-en">Relative Power</span>
                            </div>
                        </div>
                        <div class="power-matrix-divider"></div>
                        {% if relative_topo_imgs %}
                        <div class="topo-matrix-grid topo-matrix-grid-4x4">
                            {% for img in relative_topo_imgs %}
                            <div class="topo-matrix-item" data-label="{{ img.get('freq', img.get('label', '')) }}">
                                <img src="{{ img.url }}" alt="{{ img.get('freq', img.get('label', '')) }}">
                                <span class="topo-label" style="font-size: 9px; color: #333; text-align: center; margin-top: 1px;">{{ img.get('freq', img.get('label', '')) }}</span>
                            
                                <!-- 增加子图色度条 -->
                                <div style="width: 100%; margin-top: 1px;">
                                    <div style="width: 50px; margin: 0 auto; height: 3px; border-radius: 2px; background: {{ hex_colors_css }};"></div>
                                    <div style="display:flex; justify-content:space-between;  width: calc(100% - 20px); padding-left:10px;font-size:6px; color:#666; line-height:1.1; margin-top:1px;">
                                        <span>{{ "%.1f"|format((img.get('vmin', 999))|float) }}</span>
                                        <span>{{ "%.1f"|format((img.get('vmax', 999))|float) }}</span>
                                    </div>
                                </div> 
                            
                            </div>
                            {% endfor %}
                        </div>
                        {% else %}
                        <div class="matrix-placeholder">
                            <p>暂无数据</p>
                        </div>
                        {% endif %}
                        <div class="module-colorbar-wrap" style="margin-top: 8px;">
                        </div>
                    </div>


                    <!-- 右下：相对功率在常模中的分布 -->
                    <div class="power-matrix-section">
                        <div class="power-matrix-header">
                            <div class="power-matrix-title power-matrix-title-two-line">
                                <span class="power-matrix-title-main">相对功率在常模中的分布(Z-Score)</span>
                                <span class="power-matrix-title-en">Rel. Power Norm Distribution (Z-Score)</span>
                            </div>
                        </div>
                        <div class="power-matrix-divider"></div>
                        {% if relative_zscore_topo_imgs %}
                        <div class="topo-matrix-grid topo-matrix-grid-4x4">
                            {% for img in relative_zscore_topo_imgs[:9] %}
                            <div class="topo-matrix-item" data-label="{{ img.get('freq', img.get('label', '')) }}">
                                <img src="{{ img.url }}" alt="{{ img.get('freq', img.get('label', '')) }}">
                                <span class="topo-label" style="font-size: 9px; color: #333; text-align: center; margin-top: 1px;">{{ img.get('freq', img.get('label', '')) }}</span>

                            </div>
                            {% endfor %}
                        </div>
                        {% else %}
                        <div class="matrix-placeholder">
                            <p>暂无数据</p>
                        </div>
                        {% endif %}
                        <div class="module-colorbar-wrap" style="margin-top: 7px;">

                        <div class="module-colorbar-legend">
                            <span class="cb-tick">-3</span>
                            <span class="cb-bar" style="background: {{ hex_colors_css }};"></span>
                            <span class="cb-tick">3</span>
                            <span class="cb-unit">SD</span>
                        </div>

                        </div>
                    </div>
                </div>
                </div>
                <!-- 页脚 -->
                <div class="page-footer">
                    <div class="footer-divider"></div>
                    <div class="footer-content">
                        <div class="footer-left">Generated by QL_analyser</div>
                        <div class="footer-right">Page <span class="current-page">{{ current_page }}</span> of {{ total_pages }}</div>
                    </div>
                </div>
            </div>
        """,
        "absolute_power_matrix_single": """
            <div class="page-section">
                <div class="page-header">
                    <div class="page-header-left">
                        <div class="logo-section">
                            {% if logo_base64 %}
                            <img src="{{ logo_base64 }}" alt="QLanalyser" class="logo-image" />
                            {% else %}
                            <div class="logo-icon">
                                <svg width="40" height="40" viewBox="0 0 40 40">
                                    <circle cx="20" cy="20" r="18" fill="#4A90E2" opacity="0.9"/>
                                    <path d="M10 20 Q15 12, 20 15 T30 20" stroke="#B0D4FF" stroke-width="2" fill="none"/>
                                    <path d="M10 20 Q15 18, 20 21 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                    <path d="M10 20 Q15 22, 20 19 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                </svg>
                            </div>
                            <div class="logo-text"><span class="ql-part">QL</span><span class="analyser-part">analyser</span></div>
                            {% endif %}
                        </div>
                    </div>
                    <div class="page-header-right">
                        <div class="report-title-main">脑电分析报告</div>
                        <div class="report-date">报告日期: {{ patient_info.date or 'N/A' }}</div>
                    </div>
                </div>
                <div class="header-divider"></div>
                <div class="patient-info-box">
                    <div class="info-row">
                    <div class="info-item">
                        <span class="info-label">姓名:</span>
                        <span class="info-value">{{ patient_info.name or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">性别:</span>
                        <span class="info-value">{{ patient_info.gender or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">年龄:</span>
                        <span class="info-value">{{ patient_info.age or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">采集时间:</span>
                        <span class="info-value">{{ patient_info.collection_time or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">采集人:</span>
                        <span class="info-value">{{ patient_info.collector or 'N/A' }}</span>
                    </div>
                    </div>
                </div>
                <div class="section-content">
                {% if analysis_method %}
                <div class="analysis-name">{{ analysis_method }}</div>
                {% endif %}
                <!-- 分析方法描述区域 -->
                <div class="analysis-description-box">
                    <div class="analysis-description-content">
                        <div class="task-name-title">任务名称</div>
                        <div class="analysis-method-label">
                            分析方法: <span class="analysis-method-value">{{ analysis_method or 'N/A' }}</span>
                            {% if analysis_method and '绝对功率' in analysis_method %}
                            <span class="analysis-method-chinese">绝对功率分析</span>
                            {% endif %}
                        </div>
                        <div class="analysis-description-text">
                            {% if analysis_method and '绝对功率' in analysis_method %}
                            绝对功率分析展示了各导联在不同频率下的绝对功率值,通过地形图矩阵形式直观呈现全脑的能量分布模式,有助于识别异常脑区和频率特征。
                            {% else %}
                            本分析通过先进的信号处理算法,对脑电数据进行深入分析,提取关键特征参数,为临床诊断和评估提供科学依据。
                            {% endif %}
                        </div>
                    </div>
                </div>
                <div class="power-matrix-section">
                    <div class="power-matrix-header">
                        <div class="power-matrix-title">绝对功率</div>
                        <div class="power-matrix-unit">单位: Hz</div>
                    </div>
                    <div class="power-matrix-divider"></div>
                    <div class="topo-matrix-grid">
                        {% for img in topo_imgs %}
                        <div class="topo-matrix-item">
                            <img src="{{ img.url }}" alt="{{ img.freq }}">
                            <div class="topo-label">
                                <div class="freq-label">{{ img.freq }}</div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                </div>
                <!-- 页脚 -->
                <div class="page-footer">
                    <div class="footer-divider"></div>
                    <div class="footer-content">
                        <div class="footer-left">Generated by QL_analyser</div>
                        <div class="footer-right">Page <span class="current-page">{{ current_page }}</span> of {{ total_pages }}</div>
                    </div>
                </div>
            </div>
        """,
        "relative_power_matrix_single": """
            <div class="page-section">
                <div class="page-header">
                    <div class="page-header-left">
                        <div class="logo-section">
                            {% if logo_base64 %}
                            <img src="{{ logo_base64 }}" alt="QLanalyser" class="logo-image" />
                            {% else %}
                            <div class="logo-icon">
                                <svg width="40" height="40" viewBox="0 0 40 40">
                                    <circle cx="20" cy="20" r="18" fill="#4A90E2" opacity="0.9"/>
                                    <path d="M10 20 Q15 12, 20 15 T30 20" stroke="#B0D4FF" stroke-width="2" fill="none"/>
                                    <path d="M10 20 Q15 18, 20 21 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                    <path d="M10 20 Q15 22, 20 19 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                </svg>
                            </div>
                            <div class="logo-text"><span class="ql-part">QL</span><span class="analyser-part">analyser</span></div>
                            {% endif %}
                        </div>
                    </div>
                    <div class="page-header-right">
                        <div class="report-title-main">脑电分析报告</div>
                        <div class="report-date">报告日期: {{ patient_info.date or 'N/A' }}</div>
                    </div>
                </div>
                <div class="header-divider"></div>
                <div class="patient-info-box">
                    <div class="info-row">
                    <div class="info-item">
                        <span class="info-label">姓名:</span>
                        <span class="info-value">{{ patient_info.name or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">性别:</span>
                        <span class="info-value">{{ patient_info.gender or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">年龄:</span>
                        <span class="info-value">{{ patient_info.age or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">采集时间:</span>
                        <span class="info-value">{{ patient_info.collection_time or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">采集人:</span>
                        <span class="info-value">{{ patient_info.collector or 'N/A' }}</span>
                    </div>
                    </div>
                </div>
                <div class="section-content">
                {% if analysis_method %}
                <div class="analysis-name">{{ analysis_method }}</div>
                {% endif %}
                <!-- 分析方法描述区域 -->
                <div class="analysis-description-box">
                    <div class="analysis-description-content">
                        <div class="task-name-title">任务名称</div>
                        <div class="analysis-method-label">
                            分析方法: <span class="analysis-method-value">{{ analysis_method or 'N/A' }}</span>
                            {% if analysis_method and '相对功率' in analysis_method %}
                            <span class="analysis-method-chinese">相对功率分析</span>
                            {% endif %}
                        </div>
                        <div class="analysis-description-text">
                            {% if analysis_method and '相对功率' in analysis_method %}
                            相对功率分析展示了各导联在不同频率下的相对功率百分比,通过地形图矩阵形式直观呈现全脑的能量分布模式,有助于识别异常脑区和频率特征。
                            {% else %}
                            本分析通过先进的信号处理算法,对脑电数据进行深入分析,提取关键特征参数,为临床诊断和评估提供科学依据。
                            {% endif %}
                        </div>
                    </div>
                </div>
                <div class="power-matrix-section">
                    <div class="power-matrix-header">
                        <div class="power-matrix-title">相对功率</div>
                        <div class="power-matrix-unit">单位: Hz</div>
                    </div>
                    <div class="power-matrix-divider"></div>
                    <div class="topo-matrix-grid">
                        {% for img in topo_imgs %}
                        <div class="topo-matrix-item">
                            <img src="{{ img.url }}" alt="{{ img.freq }}">
                            <div class="topo-label">
                                <div class="freq-label">{{ img.freq }}</div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                </div>
                <!-- 页脚 -->
                <div class="page-footer">
                    <div class="footer-divider"></div>
                    <div class="footer-content">
                        <div class="footer-left">Generated by QL_analyser</div>
                        <div class="footer-right">Page <span class="current-page">{{ current_page }}</span> of {{ total_pages }}</div>
                    </div>
                </div>
            </div>
        """,
        "qeeg_mapping": """
        <div class="page-section qeeg-mapping-section">
            <div class="page-header">
                <div class="page-header-left">
                    <div class="logo-section">
                        {% if logo_base64 %}
                        <img src="{{ logo_base64 }}" alt="QLanalyser" class="logo-image" />
                        {% else %}
                        <div class="logo-icon">
                            <svg width="40" height="40" viewBox="0 0 40 40">
                                <circle cx="20" cy="20" r="18" fill="#4A90E2" opacity="0.9"/>
                                <path d="M10 20 Q15 12, 20 15 T30 20" stroke="#B0D4FF" stroke-width="2" fill="none"/>
                                <path d="M10 20 Q15 18, 20 21 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                <path d="M10 20 Q15 22, 20 19 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                            </svg>
                        </div>
                        <div class="logo-text"><span class="ql-part">QL</span><span class="analyser-part">analyser</span></div>
                        {% endif %}
                    </div>
                </div>
                <div class="page-header-right">
                    <div class="report-title-main">脑电分析报告</div>
                    <div class="report-date">报告日期: {{ patient_info.date or 'N/A' }}</div>
                </div>
            </div>
            <div class="header-divider"></div>
            <div class="patient-info-box">
                <div class="info-row">
                    <div class="info-item">
                        <span class="info-label">姓名:</span>
                        <span class="info-value">{{ patient_info.name or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">性别:</span>
                        <span class="info-value">{{ patient_info.gender or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">年龄:</span>
                        <span class="info-value">{{ patient_info.age or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">采集时间:</span>
                        <span class="info-value">{{ patient_info.collection_time or 'N/A' }}</span>
                    </div>
                    <div class="info-separator"></div>
                    <div class="info-item">
                        <span class="info-label">采集人:</span>
                        <span class="info-value">{{ patient_info.collector or 'N/A' }}</span>
                    </div>
                </div>
            </div>
            <div class="section-content">
                {% if analysis_method %}
                <div class="analysis-name">{{ analysis_method }}</div>
                {% endif %}
                <!-- 分析方法描述区域 -->
                <div class="analysis-description-box">
                    <div class="analysis-description-content">
                        <div class="task-name-title">任务名称</div>
                        <div class="analysis-method-label">
                            分析方法: <span class="analysis-method-value">{{ analysis_method or 'N/A' }}</span>
                            {% if analysis_method and 'Quantitative EEG Mapping' in analysis_method %}
                            <span class="analysis-method-chinese">定量脑电地形图</span>
                            {% endif %}
                        </div>
                        <div class="analysis-description-text">
                            {% if analysis_method and 'Quantitative EEG Mapping' in analysis_method %}
                            定量脑电地形图通过多频段功率分析和地形图可视化,全面展示全脑各区域的电活动特征,结合绝对功率和相对功率分析,为临床评估提供综合性的量化数据。
                            {% else %}
                            本分析通过先进的信号处理算法,对脑电数据进行深入分析,提取关键特征参数,为临床诊断和评估提供科学依据。
                            {% endif %}
                        </div>
                    </div>
                </div>
               
               <div class="qeeg-quad-wrapper">
                <div class="qeeg-quad-grid">
                    <!-- 左上：绝对功率 -->
                    <div class="qeeg-quad-item">
                        <h4 class="qeeg-quad-title">绝对功率</h4>
                        <div class="qeeg-matrix-grid-4x4">
                            {% for img in absolute_power_imgs %}
                            <div class="qeeg-matrix-cell">
                                <img src="{{ img.url }}" alt="{{ img.label }}">
                                <div class="qeeg-cell-label">{{ img.label }}</div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    <!-- 右上：相对功率 Z-Score -->
                    <div class="qeeg-quad-item">
                        <h4 class="qeeg-quad-title">相对功率</h4>
                        <div class="qeeg-matrix-grid-4x4">
                            {% for img in relative_zscore_imgs %}
                            <div class="qeeg-matrix-cell">
                                <img src="{{ img.url }}" alt="{{ img.label }}">
                                <div class="qeeg-cell-label">{{ img.label }}</div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
             </div>    
            </div>
        
        <!-- 页脚 -->
        <div class="page-footer">
            <div class="footer-divider"></div>
            <div class="footer-content">
                <div class="footer-left">Generated by QL_analyser</div>
                <div class="footer-right">Page <span class="current-page">{{ current_page }}</span> of {{ total_pages }}</div>
            </div>
        </div>
        </div>
        """,
        "comprehensive_assessment": """
            <div class="page-section assessment-section">
                <div class="page-header">
                    <div class="page-header-left">
                        <div class="logo-section">
                            {% if logo_base64 %}
                            <img src="{{ logo_base64 }}" alt="QLanalyser" class="logo-image" />
                            {% else %}
                            <div class="logo-icon">
                                <svg width="40" height="40" viewBox="0 0 40 40">
                                    <circle cx="20" cy="20" r="18" fill="#4A90E2" opacity="0.9"/>
                                    <path d="M10 20 Q15 12, 20 15 T30 20" stroke="#B0D4FF" stroke-width="2" fill="none"/>
                                    <path d="M10 20 Q15 18, 20 21 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                    <path d="M10 20 Q15 22, 20 19 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                </svg>
                            </div>
                            <div class="logo-text"><span class="ql-part">QL</span><span class="analyser-part">analyser</span></div>
                            {% endif %}
                        </div>
                    </div>
                    <div class="page-header-right">
                        <div class="report-title-main">脑电分析报告</div>
                        <div class="report-date">报告日期: {{ patient_info.date or 'N/A' }}</div>
                    </div>
                </div>
                <div class="header-divider"></div>
                {% if patient_info %}
                <div class="patient-info-box">
                    <div class="info-row">
                        <div class="info-item">
                            <span class="info-label">姓名:</span>
                            <span class="info-value">{{ patient_info.name or 'N/A' }}</span>
                        </div>
                        <div class="info-separator"></div>
                        <div class="info-item">
                            <span class="info-label">性别:</span>
                            <span class="info-value">{{ patient_info.gender or 'N/A' }}</span>
                        </div>
                        <div class="info-separator"></div>
                        <div class="info-item">
                            <span class="info-label">年龄:</span>
                            <span class="info-value">{{ patient_info.age or 'N/A' }}</span>
                        </div>
                        <div class="info-separator"></div>
                        <div class="info-item">
                            <span class="info-label">采集时间:</span>
                            <span class="info-value">{{ patient_info.collection_time or 'N/A' }}</span>
                        </div>
                        <div class="info-separator"></div>
                        <div class="info-item">
                            <span class="info-label">采集人:</span>
                            <span class="info-value">{{ patient_info.collector or 'N/A' }}</span>
                        </div>
                    </div>
                </div>
                {% endif %}
                <div class="section-content">
                    <div class="assessment-container">
                        <h2 class="assessment-title">综合评估与建议</h2>
                        <div class="assessment-content" style="position: relative;">
                            <div class="assessment-text" contenteditable="true" id="assessment-text-editor" 
                                 style="min-height: 150px; text-align: left; vertical-align: top; padding: 10px; border: 1px solid #ddd;">
                                {% if assessment_text %}
                                    {{ assessment_text }}
                                {% else %}
                                    <p style="color: #31373D; font-style: italic; margin: 0;">请在此输入医生的综合评估和建议...</p>
                                {% endif %}
                            </div>
                            <div style="text-align: right; margin-top: 10px;">
                                <button id="save-btn" onclick="saveAssessment()" class="btn-save">保存评论</button>
                            </div>
                        </div>
                        {% if doctor_name or assessment_date %}
                        <div class="assessment-footer">
                            {% if doctor_name %}
                            <div class="doctor-signature">
                                <span class="signature-label">医生签名:</span>
                                <span class="signature-value">{{ doctor_name }}</span>
                            </div>
                            {% endif %}
                            {% if assessment_date %}
                            <div class="assessment-date">
                                <span class="date-label">日期:</span>
                                <span class="date-value">{{ assessment_date }}</span>
                            </div>
                            {% endif %}
                        </div>
                        {% endif %}
                    </div>
                </div>
                <!-- 页脚 -->
                <div class="page-footer">
                    <div class="footer-divider"></div>
                    <div class="footer-content">
                        <div class="footer-left">Generated by QL_analyser</div>
                        <div class="footer-right">Page <span class="current-page">{{ current_page }}</span> of {{ total_pages }}</div>
                    </div>
                </div>
            </div>
        """,
        "ratio_mapping": """
            <div class="page-section ratio-mapping-section">
                <div class="page-header">
                    <div class="page-header-left">
                        <div class="logo-section">
                            {% if logo_base64 %}
                            <img src="{{ logo_base64 }}" alt="QLanalyser" class="logo-image" />
                            {% else %}
                            <div class="logo-icon">
                                <svg width="40" height="40" viewBox="0 0 40 40">
                                    <circle cx="20" cy="20" r="18" fill="#4A90E2" opacity="0.9"/>
                                    <path d="M10 20 Q15 12, 20 15 T30 20" stroke="#B0D4FF" stroke-width="2" fill="none"/>
                                    <path d="M10 20 Q15 18, 20 21 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                    <path d="M10 20 Q15 22, 20 19 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                </svg>
                            </div>
                            <div class="logo-text"><span class="ql-part">QL</span><span class="analyser-part">analyser</span></div>
                            {% endif %}
                        </div>
                    </div>
                    <div class="page-header-right">
                        <div class="report-title-main">脑电分析报告</div>
                        <div class="report-date">报告日期: {{ patient_info.date or 'N/A' }}</div>
                    </div>
                </div>
                <div class="header-divider"></div>
                <div class="patient-info-box">
                    <div class="info-row">
                        <div class="info-item">
                            <span class="info-label">姓名:</span>
                            <span class="info-value">{{ patient_info.name or 'N/A' }}</span>
                        </div>
                        <div class="info-separator"></div>
                        <div class="info-item">
                            <span class="info-label">性别:</span>
                            <span class="info-value">{{ patient_info.gender or 'N/A' }}</span>
                        </div>
                        <div class="info-separator"></div>
                        <div class="info-item">
                            <span class="info-label">年龄:</span>
                            <span class="info-value">{{ patient_info.age or 'N/A' }}</span>
                        </div>
                        <div class="info-separator"></div>
                        <div class="info-item">
                            <span class="info-label">采集时间:</span>
                            <span class="info-value">{{ patient_info.collection_time or 'N/A' }}</span>
                        </div>
                        <div class="info-separator"></div>
                        <div class="info-item">
                            <span class="info-label">采集人:</span>
                            <span class="info-value">{{ patient_info.collector or 'N/A' }}</span>
                        </div>
                    </div>
                </div>
                <div class="section-content">
                    {% if analysis_method and 'Full-Band Ratio Distribution' not in analysis_method %}
                    <div class="analysis-name">{{ (analysis_method or '')|replace(' - 新任务', '') }}</div>
                    {% endif %}
                    <!-- 分析方法描述区域 -->
                    <div class="analysis-description-box">
                        <div class="analysis-description-content">
                            <div class="task-name-title">任务名称</div>
                            <div class="analysis-method-label">
                                分析方法: <span class="analysis-method-value">{{ (analysis_method or 'N/A')|replace(' - 新任务', '') }}</span>
                                {% if analysis_method and ('Full-Band Ratio Distribution' in analysis_method or '全频段比率分布' in analysis_method or 'Ratio Mapping' in analysis_method) %}
                                <span class="analysis-method-chinese">全频段比率分布</span>
                                {% endif %}
                            </div>
                            <div class="analysis-description-text">
                                {% if analysis_method and ('Full-Band Ratio Distribution' in analysis_method or '全频段比率分布' in analysis_method or 'Ratio Mapping' in analysis_method) %}
                                全频段比率分布展示了12种不同频段功率比率组合的地形分布，包括θ/α、θ/β、α/β等关键比率，通过地形图可视化直观呈现全脑各区域的功率比率特征，为临床评估提供重要的量化指标。
                                {% else %}
                                本分析通过先进的信号处理算法，对脑电数据进行深入分析，提取关键特征参数，为临床诊断和评估提供科学依据。
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    <!-- 两列布局：功率比率 和 功率比率Z-Score，使用与绝对功率相同的容器类 -->
                    <div class="power-matrices-container">
                        <!-- 第一列：功率比率 -->
                        <div class="power-matrix-section">
                            <div class="power-matrix-header">
                                <div class="power-matrix-title power-matrix-title-two-line">
                                    <span class="power-matrix-title-main">功率比率</span>
                                    <span class="power-matrix-title-en">Power Ratios</span>
                                </div>
                            </div>
                            <div class="power-matrix-divider"></div>
                            <div class="topo-matrix-grid topo-matrix-grid-4x4">
                                {% for img in ratio_imgs %}
                                <div class="topo-matrix-item" data-label="{{ img.label }}">
                                    <img src="{{ img.url }}" alt="{{ img.label }}">
                                    <span class="topo-label">{{ img.label }}</span>


                                <!-- 增加子图色度条 -->
                                <div style="width: 100%; margin-top: 1px;">
                                    <div style="width: 50px; margin: 0 auto; height: 3px; border-radius: 2px; background: {{ hex_colors_css }};"></div>
                                    <div style="display:flex; justify-content:space-between;  width: calc(100% - 20px); padding-left:10px;font-size:6px; color:#666; line-height:1.1; margin-top:1px;">
                                        <span>{{ "%.1f"|format((img.get('vmin', 999))|float) }}</span>
                                        <span>{{ "%.1f"|format((img.get('vmax', 999))|float) }}</span>
                                    </div>
                                </div> 


                                </div>
                                {% endfor %}
                            </div>
                            <div class="module-colorbar-wrap" style="margin-top: 8px;">

                            <!-- 注释掉全局色度条
                                <div class="module-colorbar-legend">
                                    <span class="cb-tick">-3</span>
                                    <span class="cb-bar" style="background: linear-gradient(to right, #0606fc, #0532fb, #055dfb, #0689fc, #06b4fc, #06dffb, #23fbfc, #b3fbfb, #fbfbfb, #fbfbd0, #fcfc7a, #fbfb22, #fbde06, #fbb305, #fc8906, #fc5d06, #fc3206);"></span>
                                    <span class="cb-tick">3</span>
                                    <span class="cb-unit">SD</span>
                                </div>
                            -->
                                    
                            </div>
                        </div>



                        <!-- 第二列：功率比率在常模中的分布(Z-Score) -->
                        <div class="power-matrix-section">
                            <div class="power-matrix-header">
                                <div class="power-matrix-title power-matrix-title-two-line">
                                    <span class="power-matrix-title-main">功率比率在常模中的分布(Z-Score)</span>
                                    <span class="power-matrix-title-en">Ratio Norm Distribution (Z-Score)</span>
                                </div>
                            </div>
                            <div class="power-matrix-divider"></div>
                            <div class="topo-matrix-grid topo-matrix-grid-4x4">
                                {% for img in ratio_zscore_imgs %}
                                <div class="topo-matrix-item" data-label="{{ img.label }}">
                                    <img src="{{ img.url }}" alt="{{ img.label }}">
                                    <span class="topo-label">{{ img.label }}</span>
                                </div>
                                {% endfor %}
                            </div>
                            <div class="module-colorbar-wrap" style="margin-top: 7px;">
                                <div class="module-colorbar-legend">
                                    <span class="cb-tick">-3</span>
                                    <span class="cb-bar" style="background: linear-gradient(to right, #0606fc, #0532fb, #055dfb, #0689fc, #06b4fc, #06dffb, #23fbfc, #b3fbfb, #fbfbfb, #fbfbd0, #fcfc7a, #fbfb22, #fbde06, #fbb305, #fc8906, #fc5d06, #fc3206);"></span>
                                    <span class="cb-tick">3</span>
                                    <span class="cb-unit">SD</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <!-- 页脚 -->
                <div class="page-footer">
                    <div class="footer-divider"></div>
                    <div class="footer-content">
                        <div class="footer-left">Generated by QL_analyser</div>
                        <div class="footer-right">Page <span class="current-page">{{ current_page }}</span> of {{ total_pages }}</div>
                    </div>
                </div>
            </div>
        """,
        "empty_page": """
            <div class="page-section ">
                <div class="page-header">
                    <div class="page-header-left">
                        <div class="logo-section">
                            {% if logo_base64 %}
                            <img src="{{ logo_base64 }}" alt="QLanalyser" class="logo-image" />
                            {% else %}
                            <div class="logo-icon">
                                <svg width="40" height="40" viewBox="0 0 40 40">
                                    <circle cx="20" cy="20" r="18" fill="#4A90E2" opacity="0.9"/>
                                    <path d="M10 20 Q15 12, 20 15 T30 20" stroke="#B0D4FF" stroke-width="2" fill="none"/>
                                    <path d="M10 20 Q15 18, 20 21 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                    <path d="M10 20 Q15 22, 20 19 T30 20" stroke="#B0D4FF" stroke-width="1.5" fill="none"/>
                                </svg>
                            </div>
                            <div class="logo-text"><span class="ql-part">QL</span><span class="analyser-part">analyser</span></div>
                            {% endif %}
                        </div>
                    </div>
                    <div class="page-header-right">
                        <div class="report-title-main">脑电分析报告</div>
                        <div class="report-date">报告日期: {{ patient_info.date or 'N/A' }}</div>
                    </div>
                </div>
                <div class="header-divider"></div>
                <div class="section-content">
                    <table class="zscore-table">
                        <colgroup>
                          <col style="width: 18%;">  <!-- 第1列：区域列 -->
                          <col style="width: 13%;">  <!-- 第2列：频段列 -->
                          <col style="width: 13%;">  <!-- 第3列：zscore值列 -->
                          <col style="width: 56%;">  <!-- 第4列：功能列 -->
                        </colgroup>
                        <thead>
                            <tr>
                                <th>脑区名称</th>
                                <th>频段名称</th>
                                <th>Z 分数</th>
                                <th>功能解释</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for item in sites %}
                            {% set z_val = item.z if item.z is defined else (item.zscore if item.zscore is defined else 0) %}
                            {% set z_num = z_val | float %}
                            <tr>
                                <td class="col-region" >{{ item.site or item.ba_region or 'N/A' }}</td>
                                <td class="col-band" >{{ item.band or item.freq_band or 'N/A' }}</td>
                                <td class="zscore-value {% if z_num >= 0 %}zscore-positive{% else %}zscore-negative{% endif %}">
                                    {% if z_num > 0 %}+{% endif %}{{ "%.2f"|format(z_num) }}
                                </td>
                                <td   class="col-func"  >{{ item.msg or item.functional_interp or 'N/A' }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>

                </div>
                <!-- 页脚 -->
                <div class="page-footer">
                    <div class="footer-divider"></div>
                    <div class="footer-content">
                        <div class="footer-left">Generated by QL_analyser</div>
                        <div class="footer-right">Page <span class="current-page">{{ current_page }}</span> of {{ total_pages }}</div>
                    </div>
                </div>
            </div>
        """
    }
    '''
    <div class="channel-values">
                                    <div class="value-row">
                                        <div class="value-item"><span class="label">δ Delta</span><span class="value">{{ channel.channel_values.delta }}μV<sup>2</sup></span></div>
                                        <div class="value-item"><span class="label">β Beta</span><span class="value">{{ channel.channel_values.beta }}μV<sup>2</sup></span></div>
                                    </div>    
                                    <div class="value-row">
                                        <div class="value-item"><span class="label label-theta">θ Theta</span><span class="value">{{ channel.channel_values.theta }}μV<sup>2</sup></span></div>
                                        <div class="value-item"><span class="label">Hi-β</span><span class="value">{{ channel.channel_values.high_beta }}μV<sup>2</sup></span></div>
                                    </div>
                                    <div class="value-row">
                                        <div class="value-item"><span class="label label-alpha">α Alpha</span><span class="value">{{ channel.channel_values.alpha }}μV<sup>2</sup></span></div>
                                        <div class="value-item"><span class="label">γ Gamma</span><span class="value">{{ channel.channel_values.gamma }}μV<sup>2</sup></span></div>
                                    </div>
                                    <div class="value-row">
                                        <div class="value-item"><span class="label">SMR</span><span class="value">{{ channel.channel_values.smr }}μV<sup>2</sup></span></div>
                                        <div class="value-item"></div>
                                    </div>
                                </div>
    '''

    def build(self, algo_results):
        """根据返回的数据键值动态拼接组件"""
        # 修复：如果 algo_results 为 None，使用空字典避免报错

        if algo_results is None:
            algo_results = {}

        full_body = []

        # 注意：不再渲染开头的header，因为每个page-section都有自己的page-header
        # 这样每个分析方法都会独占一页，并且每页都有页头

        # 动态判断并添加分析板块（保持原有功能）
        patient_info = algo_results.get('patient_info', {})

        # 是否显示“综合评估 / 报告输出验收”页面：
        # - 来自 QEEGAnalysis.Thread_run_analysis 的多任务模式会显式传入 show_report_output 标记
        # - 其它旧调用若未提供该标记，则默认显示该页面（保持兼容）
        show_report_output = algo_results.get('show_report_output')
        if show_report_output is None:
            show_report_output = True

        # 计算总页数（统计会被渲染的分析方法数量，支持多任务列表）
        total_pages = 0
        _psd = algo_results.get('psd_data')
        _psd_cnt = len(_psd) if isinstance(_psd, list) else (1 if _psd else 0)
        total_pages += _psd_cnt

        _zscore = algo_results.get('zscore_data')
        _zscore_cnt = len(_zscore) if isinstance(_zscore, list) else (1 if _zscore and isinstance(_zscore, dict) else 0)
        total_pages += _zscore_cnt

        analysis_method = algo_results.get('analysis_method') or algo_results.get('analysis_type') or algo_results.get(
            'method_name', '')
        is_qeeg = (str(analysis_method) == 'Quantitative EEG Mapping' or
                   str(analysis_method) == 'Quantitative EEG' or
                   str(analysis_method) == 'QEEM' or
                   ('Quantitative' in str(analysis_method) and 'EEG' in str(analysis_method) and 'Mapping' in str(
                       analysis_method)))

        if is_qeeg:
            # 检查是否有数据
            try:
                qeeg_formatted = prepare_qeeg_mapping_data(algo_results)
                if (qeeg_formatted.get('absolute_power_imgs') or qeeg_formatted.get('relative_zscore_imgs')):
                    total_pages += 1
            except:
                pass
        else:
            _fullband = algo_results.get('full_band_mapping_data')
            _fullband_cnt = len(_fullband) if isinstance(_fullband, list) else 0
            if _fullband_cnt == 0:
                has_absolute = 'absolute_power_matrix' in algo_results
                has_relative = 'relative_power_matrix' in algo_results
                has_absolute_zscore = 'absolute_power_zscore' in algo_results
                has_relative_zscore = 'relative_power_zscore' in algo_results
                has_ratios = 'power_ratios' in algo_results
                if has_absolute or has_relative or has_absolute_zscore or has_relative_zscore or has_ratios:
                    _fullband_cnt = 1
            total_pages += _fullband_cnt

        _ratio_map = algo_results.get('ratio_mapping_data')
        _ratio_cnt = len(_ratio_map) if isinstance(_ratio_map, list) else 0
        if _ratio_cnt == 0 and ('power_ratios' in algo_results or 'ratio_zscore' in algo_results):
            try:
                ratio_formatted = prepare_ratio_mapping_data(algo_results)
                if ratio_formatted.get('ratio_imgs') or ratio_formatted.get('ratio_zscore_imgs'):
                    _ratio_cnt = 1
            except:
                pass
        total_pages += _ratio_cnt

        # TBR 分析页面
        if 'tbr_data' in algo_results:
            try:
                tbr_data = algo_results['tbr_data']
                # 检查是否有有效的比率数据
                has_fz = any(key in tbr_data for key in
                             ['fz_ratio', 'Fz_ratio', 'Fz比率', 'Fz 比率', 'FZ_ratio', 'FZ比率', 'FZ 比率'])
                has_cz = any(key in tbr_data for key in
                             ['cz_ratio', 'Cz_ratio', 'Cz比率', 'Cz 比率', 'CZ_ratio', 'CZ比率', 'CZ 比率'])
                has_avg = any(key in tbr_data for key in ['avg_ratio', 'average_ratio', '平均比率'])

            except:
                # 如果检查失败，只要有 tbr_data 就增加页数
                pass

        # Peak Alpha Frequency 分析页面（支持多任务列表）
        paf_data_key = 'peak_alpha_frequency_data' if 'peak_alpha_frequency_data' in algo_results else 'paf_data' if 'paf_data' in algo_results else None
        if paf_data_key:
            try:
                paf_raw_check = algo_results[paf_data_key]
                if isinstance(paf_raw_check, list):
                    for _p in paf_raw_check:
                        if isinstance(_p, dict) and any(k in _p for k in ['o1_peak', 'O1_peak', 'o2_peak', 'O2_peak', 'avg_peak', 'average_peak']):
                            break
                elif isinstance(paf_raw_check, dict):
                    pass  # 旧格式，下方条件会处理
            except:
                pass

        # 脑功能核心标准分析
        # FAA 与 PAF/TBR 同页渲染（脑功能核心指标），每页最多4张卡片，超过则分页
        def _count_neuro_cards(results):
            n = 0
            paf_raw = results.get('peak_alpha_frequency_data') or results.get('paf_data')
            if isinstance(paf_raw, dict):
                n += 1
            elif isinstance(paf_raw, list) and len(paf_raw) > 0:
                n += len(paf_raw)
            def _list_len(raw):
                if raw is None:
                    return 0
                if isinstance(raw, dict):
                    return 1
                return len(raw) if isinstance(raw, list) and len(raw) > 0 else 0
            n += _list_len(results.get('tbr_data'))
            n += _list_len(results.get('faa_data'))
            n += _list_len(results.get('alpha_ratio_data'))
            return n

        if (len(algo_results.get("peak_alpha_frequency_data"))>0
            or len(algo_results.get("tbr_data"))>0
            or len(algo_results.get("faa_data")) > 0
            or len(algo_results.get("alpha_ratio_data")) > 0):
            neuro_card_count = _count_neuro_cards(algo_results)
            total_pages += max(1, math.ceil(neuro_card_count / 6))

        # 综合评估 / 报告输出验收 页面：仅在显式启用时统计页数
        if show_report_output:
            total_pages += 1

        _zlist = algo_results.get("zscore_data")
        if isinstance(_zlist, list):
            for _z in _zlist:
                if isinstance(_z, dict):
                    _sites = _z.get("sites") or []
                    if len(_sites) > 7:
                        total_pages += math.ceil((len(_sites) - 7) / 20)
        elif isinstance(_zlist, dict) and _zlist.get("sites"):
            if len(_zlist["sites"]) > 7:
                total_pages += math.ceil((len(_zlist["sites"]) - 7) / 20)

        # 当前页码计数器
        current_page = 0

        # 脑功能核心指标分析
        # 检查是否有任何核心指标数据（PAF、TBR、FAA 等）
        # PAF 支持多任务：peak_alpha_frequency_data 为列表，每项对应一个任务
        paf_raw = algo_results.get('peak_alpha_frequency_data') or algo_results.get('paf_data')
        if isinstance(paf_raw, dict):
            # 向后兼容：旧格式为单个 dict，转为单元素列表
            paf_list = [dict(paf_raw, task_name=paf_raw.get('task_name', '任务1'), task_id=paf_raw.get('task_id', 0))]
        elif isinstance(paf_raw, list) and len(paf_raw) > 0:
            paf_list = paf_raw
        else:
            paf_list = []
        has_paf = len(paf_list) > 0
        # TBR/FAA/Alpha Ratio 支持多任务列表
        def _to_list(raw, default_task_name='任务1'):
            if isinstance(raw, dict):
                return [dict(raw, task_name=raw.get('task_name', default_task_name), task_id=raw.get('task_id', 0))]
            return raw if isinstance(raw, list) and len(raw) > 0 else []
        tbr_list = _to_list(algo_results.get('tbr_data'))
        faa_list = _to_list(algo_results.get('faa_data'))
        alpha_ratio_list = _to_list(algo_results.get('alpha_ratio_data'))
        has_tbr = len(tbr_list) > 0
        has_ffa = len(faa_list) > 0
        has_alpha_ratio = len(alpha_ratio_list) > 0

        if has_paf or has_tbr or has_ffa or has_alpha_ratio:
            neuro_formatted = {
                'patient_info': patient_info,
                'logo_base64': self.logo_base64,
                'analysis_method': '脑功能核心指标分析 (Core Neuro Metrics Analysis)',
            }

            # ========== 四个刻度表区间划分说明（与参考图一致，超出范围归入最左/最右区间）==========
            # 1. PAF (Alpha峰频) 刻度 4,6,8,12,14,16 Hz
            #    E(红): x<6 最左 | C(黄): 6≤x<8 | A(绿): 8≤x≤12 | C(黄): 12<x≤14 | E(红): x>14 最右
            # 2. TBR (注意力指数) 刻度 1, 1.5, 2, 2.5, 3
            #    A(绿): x<1 最左 | B(浅绿): 1≤x<1.5 | C(黄): 1.5≤x<2 | D(橙): 2≤x<2.5 | E(红): x≥2.5 最右
            # 3. FAA (情绪动机) 分两半，正中为A。左无名(-∞,-30)不标无穷；E左-30；E/C与C/E交界不标值有分界；C右-10；A(-10,10)；右C左10；E右30；右无名(30,∞)不标无穷
            # 4. Alpha Ratio (抑制指数) 刻度 0.8, 1, 1.2, 1.4, 1.6（最右 1.6~∞ 不标值、无区间名）
            #    E(红): [0.8,1) | D(橙): [1,1.2) | B(浅绿): [1.2,1.4) | A(绿): [1.4,1.6] | 最右[1.6,∞)无名称
            # ==========
            # 提取PAF数据（支持多任务，每个任务单独一条）
            paf_items = []
            if has_paf:
                for paf_data in paf_list:
                    task_name = paf_data.get('task_name', '')
                    # 先初始化默认值
                    paf_value = None
                    paf_pointer_position = None
                    paf_grade = 'N/A'
                    paf_status = 'N/A'
                    paf_status_color = 'gray'
                    
                    avg_peak = (paf_data.get('avg_peak') or
                                paf_data.get('average_peak') or
                                paf_data.get('平均峰值') or
                                paf_data.get('average_peak_frequency'))
                    # 如果没有avg_peak，尝试从o1和o2计算
                    if not avg_peak:
                        o1_peak = paf_data.get('o1_peak') or paf_data.get('O1_peak')
                        o2_peak = paf_data.get('o2_peak') or paf_data.get('O2_peak')
                        if o1_peak is not None and o2_peak is not None:
                            try:
                                avg_peak = (float(o1_peak) + float(o2_peak)) / 2.0
                            except (ValueError, TypeError):
                                pass
                    if avg_peak is not None:
                        try:
                            avg_val = float(avg_peak)
                            paf_value = round(avg_val, 2)
                            # 使用线性刻度表计算指针位置
                            # 刻度：4, 6, 8, 12, 14, 16 Hz。结构：左溢出(0-10%) + 有效区(10%-90%) + 右溢出(90%-100%)
                            # 区间划分（与参考图一致，超出范围归入最左/最右）：
                            #   E(红): x < 6  → 最左；  x > 14 → 最右
                            #   C(黄): 6 <= x < 8；  12 < x <= 14
                            #   A(绿): 8 <= x <= 12
                            paf_min = 4.0
                            paf_max = 16.0
                            if avg_val < paf_min:
                                paf_pointer_position = 5.0  # 左无名区域正中间
                            elif avg_val > paf_max:
                                paf_pointer_position = 95.0  # 右无名区域正中间
                            else:
                                paf_pointer_position = round(10 + (avg_val - paf_min) / (paf_max - paf_min) * 80, 2)
                            # 等级判定：任意实数值均有区间，超出刻度尺归入最左/最右 E
                            if avg_val < 6.0:
                                paf_grade, paf_status, paf_status_color = 'E', '严重偏低', 'red'
                            elif avg_val < 8.0:
                                paf_grade, paf_status, paf_status_color = 'C', '临界', '#cccc00'
                            elif avg_val <= 12.0:
                                paf_grade, paf_status, paf_status_color = 'A', '正常', 'green'
                            elif avg_val <= 14.0:
                                paf_grade, paf_status, paf_status_color = 'C', '临界', '#cccc00'
                            else:
                                paf_grade, paf_status, paf_status_color = 'E', '严重偏高', 'red'
                        except (ValueError, TypeError):
                            pass

                    paf_items.append({
                        'task_name': task_name,
                        'paf_value': paf_value,
                        'paf_pointer_position': paf_pointer_position,
                        'paf_grade': paf_grade,
                        'paf_status': paf_status,
                        'paf_status_color': paf_status_color
                    })

            # 提取TBR数据（支持多任务）
            tbr_items = []
            if has_tbr:
                for tbr_data in tbr_list:
                    avg_ratio = (tbr_data.get('avg_ratio') or tbr_data.get('average_ratio') or tbr_data.get('平均比率'))
                    if not avg_ratio:
                        fz_ratio = tbr_data.get('fz_ratio') or tbr_data.get('Fz_ratio')
                        cz_ratio = tbr_data.get('cz_ratio') or tbr_data.get('Cz_ratio')
                        if fz_ratio is not None and cz_ratio is not None:
                            try:
                                avg_ratio = (float(fz_ratio) + float(cz_ratio)) / 2.0
                            except (ValueError, TypeError):
                                pass
                    if not avg_ratio and tbr_data.get('tbr_value') is not None:
                        try:
                            avg_ratio = float(tbr_data.get('tbr_value'))
                        except (ValueError, TypeError):
                            pass
                    tbr_value, tbr_pointer_position = None, None
                    tbr_grade, tbr_status, tbr_status_color = 'N/A', 'N/A', 'gray'
                    if avg_ratio is not None:
                        try:
                            avg_val = float(avg_ratio)
                            tbr_value = round(avg_val, 2)
                            # 根据刻度值精确计算指针位置
                            # 刻度：1, 1.5, 2, 2.5, 3
                            # 区间：A(<1), B[1,1.5), C[1.5,2), D[2,2.5), E(>=2.5)
                            # 结构：左边红色区间(0-10%) + 中间有效区间(10%-90%) + 右边红色区间(90%-100%)
                            # 中间有效区间：1对应10%，3对应90%
                            
                            tbr_ticks = [1.00, 1.50, 2.00, 2.50, 3.00]
                            tbr_positions = [10.0, 30.0, 50.0, 70.0, 90.0]
                            
                            # 计算指针位置，支持超出范围的值
                            if avg_val < 1.00:
                                tbr_pointer_position = 5.0  # 左无名区域正中间
                            elif avg_val >= 3.00:
                                tbr_pointer_position = 95.0  # 右无名区域正中间
                            else:
                                # 值在1-3范围内，显示在中间有效区间（10%-90%）
                                if avg_val <= tbr_ticks[0]:
                                    tbr_pointer_position = tbr_positions[0]
                                elif avg_val >= tbr_ticks[-1]:
                                    tbr_pointer_position = tbr_positions[-1]
                                else:
                                    for i in range(len(tbr_ticks) - 1):
                                        if tbr_ticks[i] <= avg_val <= tbr_ticks[i + 1]:
                                            tick_range = tbr_ticks[i + 1] - tbr_ticks[i]
                                            pos_range = tbr_positions[i + 1] - tbr_positions[i]
                                            ratio = (avg_val - tbr_ticks[i]) / tick_range
                                            tbr_pointer_position = round(tbr_positions[i] + ratio * pos_range, 2)
                                            break
                            
                            # 确定等级和状态（区间：A<1, B[1,1.5), C[1.5,2), D[2,2.5), E>=2.5）
                            if avg_val < 1.00:
                                tbr_grade, tbr_status, tbr_status_color = 'A', '优秀', 'green'
                            elif 1.00 <= avg_val < 1.50:
                                tbr_grade, tbr_status, tbr_status_color = 'B', '良好', 'lightgreen'
                            elif 1.50 <= avg_val < 2.00:
                                tbr_grade, tbr_status, tbr_status_color = 'C', '临界', '#cccc00'
                            elif 2.00 <= avg_val < 2.50:
                                tbr_grade, tbr_status, tbr_status_color = 'D', '轻度异常', 'orange'
                            else:
                                tbr_grade, tbr_status, tbr_status_color = 'E', '严重异常', 'red'
                        except (ValueError, TypeError):
                            pass
                    tbr_items.append({
                        'task_name': tbr_data.get('task_name', ''),
                        'tbr_value': tbr_value, 'tbr_pointer_position': tbr_pointer_position,
                        'tbr_grade': tbr_grade, 'tbr_status': tbr_status, 'tbr_status_color': tbr_status_color
                    })

            # 提取 FAA 数据（支持多任务）
            faa_items = []
            if has_ffa:
                for faa_data in faa_list:
                    faa_value_str = self._format_faa_value(faa_data)
                    pct = faa_data.get('faa_percentage')
                    faa_pointer_position = None
                    faa_grade, faa_status, faa_status_color = 'N/A', 'N/A', 'gray'
                    if pct is not None:
                        try:
                            pct_f = float(pct)
                            # 显示值 = 百分比/100（如163.1% -> 1.6），用显示值在 -30~30 刻度上定位指针
                            display_val = pct_f / 100.0
                            faa_scale_min, faa_scale_max = -30, 30
                            faa_pos_min, faa_pos_max = 10.0, 90.0
                            if display_val <= faa_scale_min:
                                faa_pointer_position = 5.0  # 左无名区域正中间
                            elif display_val >= faa_scale_max:
                                faa_pointer_position = 95.0  # 右无名区域正中间
                            else:
                                r = (display_val - faa_scale_min) / (faa_scale_max - faa_scale_min)
                                faa_pointer_position = round(faa_pos_min + r * (faa_pos_max - faa_pos_min), 2)
                            # 等级：左无名(<-30)→—； E[-30,-20) C[-20,-10] A(-10,10] C(10,20] A(20,30] 右无名(>30)→—
                            if pct_f < -30:
                                faa_grade, faa_status, faa_status_color = '—', '—', 'gray'
                            elif pct_f < -20:
                                faa_grade, faa_status, faa_status_color = 'E', '异常', 'red'
                            elif pct_f <= -10:
                                faa_grade, faa_status, faa_status_color = 'C', '临界', '#cccc00'
                            elif pct_f <= 10:
                                faa_grade, faa_status, faa_status_color = 'A', '正常', 'green'
                            elif pct_f <= 20:
                                faa_grade, faa_status, faa_status_color = 'C', '临界', '#cccc00'
                            elif pct_f <= 30:
                                faa_grade, faa_status, faa_status_color = 'E', '异常', 'red'
                            else:
                                faa_grade, faa_status, faa_status_color = '—', '正常', 'green'
                        except (ValueError, TypeError):
                            pass
                    faa_items.append({
                        'task_name': faa_data.get('task_name', ''),
                        'faa_value': faa_value_str, 'faa_pointer_position': faa_pointer_position,
                        'faa_grade': faa_grade, 'faa_status': faa_status, 'faa_status_color': faa_status_color
                    })

            # 提取 Alpha Ratio 数据（支持多任务）
            alpha_ratio_items = []
            if has_alpha_ratio:
                for ar_data in alpha_ratio_list:
                    alpha_ratio_val = ar_data.get('alpha_ratio')
                    alpha_ratio_value = None
                    alpha_ratio_pointer_position = None
                    alpha_ratio_grade, alpha_ratio_status, alpha_ratio_status_color = 'N/A', 'N/A', 'gray'
                    if alpha_ratio_val is not None:
                        try:
                            alpha_ratio_value = round(float(alpha_ratio_val), 4)
                            alpha_ratio_val_f = float(alpha_ratio_val)
                            # 刻度：0.8, 1, 1.2, 1.4, 1.6（最右 1.6~∞ 不标数值）。E/D/B/A 区间等长0.2，刻度条等宽：左(10%)+E(20%)+D(20%)+B(20%)+A(20%)+右(10%)
                            alpha_ratio_ticks = [0.8, 1.0, 1.2, 1.4, 1.6]
                            alpha_ratio_positions = [10.0, 30.0, 50.0, 70.0, 90.0]  # 对应刻度位置（等区间等宽）
                            if alpha_ratio_val_f < 0.8:
                                alpha_ratio_pointer_position = 5.0  # 左无名区域正中间
                            elif alpha_ratio_val_f > 1.6:
                                alpha_ratio_pointer_position = 95.0  # 右无名区域(1.6,∞)正中间
                            else:
                                if alpha_ratio_val_f <= alpha_ratio_ticks[0]:
                                    alpha_ratio_pointer_position = alpha_ratio_positions[0]
                                elif alpha_ratio_val_f >= alpha_ratio_ticks[-1]:
                                    alpha_ratio_pointer_position = alpha_ratio_positions[-1]
                                else:
                                    for i in range(len(alpha_ratio_ticks) - 1):
                                        if alpha_ratio_ticks[i] <= alpha_ratio_val_f <= alpha_ratio_ticks[i + 1]:
                                            ratio = (alpha_ratio_val_f - alpha_ratio_ticks[i]) / (alpha_ratio_ticks[i + 1] - alpha_ratio_ticks[i])
                                            alpha_ratio_pointer_position = round(alpha_ratio_positions[i] + ratio * (alpha_ratio_positions[i + 1] - alpha_ratio_positions[i]), 2)
                                            break
                            # 等级：x<0.8→E； E[0.8,1)； D[1,1.2)； B[1.2,1.4)； A[1.4,1.6]； ≥1.6 最右区间无名称
                            if alpha_ratio_val_f < 0.8:
                                alpha_ratio_grade, alpha_ratio_status, alpha_ratio_status_color = 'E', '异常', 'red'
                            elif alpha_ratio_val_f < 1.0:
                                alpha_ratio_grade, alpha_ratio_status, alpha_ratio_status_color = 'E', '异常', 'red'
                            elif alpha_ratio_val_f < 1.2:
                                alpha_ratio_grade, alpha_ratio_status, alpha_ratio_status_color = 'D', '轻度异常', 'orange'
                            elif alpha_ratio_val_f < 1.4:
                                alpha_ratio_grade, alpha_ratio_status, alpha_ratio_status_color = 'B', '良好', 'lightgreen'
                            elif alpha_ratio_val_f < 1.6:
                                alpha_ratio_grade, alpha_ratio_status, alpha_ratio_status_color = 'A', '正常', 'green'
                            else:
                                alpha_ratio_grade, alpha_ratio_status, alpha_ratio_status_color = '—', '正常', 'green'
                        except (ValueError, TypeError):
                            pass
                    alpha_ratio_items.append({
                        'task_name': ar_data.get('task_name', ''),
                        'alpha_ratio_value': alpha_ratio_value,
                        'alpha_ratio_pointer_position': alpha_ratio_pointer_position,
                        'alpha_ratio_grade': alpha_ratio_grade,
                        'alpha_ratio_status': alpha_ratio_status,
                        'alpha_ratio_status_color': alpha_ratio_status_color
                    })

            # 按顺序合并所有卡片：PAF -> TBR -> FAA -> Alpha Ratio，每页最多6张
            all_cards = []
            for item in paf_items:
                all_cards.append(('paf', item))
            for item in tbr_items:
                all_cards.append(('tbr', item))
            for item in faa_items:
                all_cards.append(('faa', item))
            for item in alpha_ratio_items:
                all_cards.append(('alpha_ratio', item))

            neuro_pages = max(1, math.ceil(len(all_cards) / 6))
            for page_idx in range(neuro_pages):
                start = page_idx * 6
                end = min(start + 6, len(all_cards))
                page_cards = all_cards[start:end]
                page_paf = [it for t, it in page_cards if t == 'paf']
                page_tbr = [it for t, it in page_cards if t == 'tbr']
                page_faa = [it for t, it in page_cards if t == 'faa']
                page_ar = [it for t, it in page_cards if t == 'alpha_ratio']
                # 定义PAF等级标签列表（从低到高，对应seg-f到seg-b的顺序）
                # 根据图片显示：E(4-6红色), C(6-8绿色), A(8-12浅绿色), C(12-14橙色), E(14-16红色)
                # HTML模板中从左到右显示：seg-f, seg-e, seg-d, seg-c, seg-b
                # 对应区间：seg-f(4-6), seg-e(6-8), seg-d(8-12), seg-c(12-14), seg-b(14-16)
                paf_grade_labels = ['E', 'C', 'A', 'C', 'E']
                
                # 定义TBR等级标签列表（从左到右，对应seg-a到seg-e的顺序，5段）
                # 区间：A(<1), B[1,1.5), C[1.5,2), D[2,2.5), E(>=2.5)
                tbr_grade_labels = ['A', 'B', 'C', 'D', 'E']
                
                # FAA：左无名(-∞,-30) E C A C A 右无名(30~∞)。区间：-∞~-30,-30~-20,-20~-10,-10~10,10~20,20~30,30~∞。无穷大、-20、20不显示竖线不显示数值
                faa_grade_labels = ['E', 'C', 'A', 'C', 'E', '']
                # Alpha Ratio：E[0.8,1) D[1,1.2) B[1.2,1.4) A[1.4,1.6] 最右[1.6,∞)无名称
                alpha_ratio_grade_labels = ['E', 'D', 'B', 'A', '']
                
                neuro_formatted.update({
                    'has_paf': len(page_paf) > 0, 'paf_items': page_paf,
                    'has_tbr': len(page_tbr) > 0, 'tbr_items': page_tbr,
                    'has_ffa': len(page_faa) > 0, 'faa_items': page_faa,
                    'has_alpha_ratio': len(page_ar) > 0, 'alpha_ratio_items': page_ar,
                    'paf_grade_labels': paf_grade_labels,  # 添加PAF等级标签列表
                    'tbr_grade_labels': tbr_grade_labels,  # 添加TBR等级标签列表
                    'faa_grade_labels': faa_grade_labels,  # 添加FAA等级标签列表
                    'alpha_ratio_grade_labels': alpha_ratio_grade_labels,  # 添加Alpha Ratio等级标签列表
                })
                current_page += 1
                neuro_formatted['current_page'] = current_page
                neuro_formatted['total_pages'] = total_pages
                full_body.append(Template(self.COMPONENTS['neuro_metrics_analysis']).render(neuro_formatted))

        psd_raw = algo_results.get('psd_data')
        psd_list = psd_raw if isinstance(psd_raw, list) and len(psd_raw) > 0 else ([psd_raw] if isinstance(psd_raw, dict) and psd_raw else [])
        for psd_item in psd_list:
            try:
                task_name = psd_item.get('task_name', '')
                psd_data = psd_item if isinstance(psd_item, dict) else {}
                if 'channel_data' in psd_data:
                    psd_formatted = prepare_psd_topography_data(psd_data)
                else:
                    psd_formatted = prepare_psd_topography_data({'channel_data': {}})
                current_page += 1
                psd_formatted['patient_info'] = patient_info
                psd_formatted['logo_base64'] = self.logo_base64
                psd_formatted['analysis_method'] = f"全脑 PSD 分析 (Power Spectral Density){' - ' + task_name if task_name else ''}"
                psd_formatted['current_page'] = current_page
                psd_formatted['total_pages'] = total_pages
                full_body.append(Template(self.COMPONENTS['psd']).render(psd_formatted))
            except Exception as e:
                print(f"渲染PSD数据失败: {e}")
                import traceback
                traceback.print_exc()

        zscore_raw = algo_results.get('zscore_data')
        zscore_list = zscore_raw if isinstance(zscore_raw, list) and len(zscore_raw) > 0 else ([zscore_raw] if zscore_raw and isinstance(zscore_raw, dict) else [])
        for zscore_item in zscore_list:
            try:
                zscore_data = zscore_item.copy() if isinstance(zscore_item, dict) else {}
                zscore_sites = (zscore_data.get('sites') or []).copy() if isinstance(zscore_data.get('sites'), list) else []
                if not zscore_sites:
                    continue
                task_name = zscore_data.get('task_name', '')
                current_page += 1
                zscore_data['sites'] = zscore_sites[:7]
                zscore_data['patient_info'] = patient_info
                zscore_data['logo_base64'] = self.logo_base64
                zscore_data['analysis_method'] = f"Z-Score分析 (Z-Score Analysis){' - ' + task_name if task_name else ''}"
                zscore_data['current_page'] = current_page
                zscore_data['total_pages'] = total_pages
                zscore_data['total_number'] = len(zscore_sites)
                full_body.append(Template(self.COMPONENTS['zscore']).render(zscore_data))
                if len(zscore_sites) > 7:
                    for i in range(7, len(zscore_sites) + 1, 20):
                        current_page += 1
                        zscore_data['current_page'] = current_page
                        zscore_data['total_pages'] = total_pages
                        zscore_data['sites'] = zscore_sites[i:min(i + 20, len(zscore_sites))]
                        full_body.append(Template(self.COMPONENTS['empty_page']).render(zscore_data))
            except Exception as e:
                print(f"渲染Z-Score数据失败: {e}")
                import traceback
                traceback.print_exc()

        # 3. Quantitative EEG Mapping 分析（新增功能）
        analysis_method = algo_results.get('analysis_method') or algo_results.get('analysis_type') or algo_results.get(
            'method_name', '')

        # 检查是否是 Quantitative EEG Mapping 分析方法
        is_qeeg = (str(analysis_method) == 'Quantitative EEG Mapping' or
                   str(analysis_method) == 'Quantitative EEG' or
                   str(analysis_method) == 'QEEM' or
                   ('Quantitative' in str(analysis_method) and 'EEG' in str(analysis_method) and 'Mapping' in str(
                       analysis_method)))

        if is_qeeg:
            try:
                # 准备QEEG Mapping数据
                qeeg_formatted = prepare_qeeg_mapping_data(algo_results)
                qeeg_formatted['patient_info'] = patient_info
                qeeg_formatted['logo_base64'] = self.logo_base64
                # QEEG Mapping使用特定的名称
                qeeg_formatted['analysis_method'] = 'Quantitative EEG Mapping'

                # 确保所有必需的数据都存在，如果缺少则提供空列表（不包含ratio数据，因为Ratio Mapping单独处理）
                if 'absolute_power_imgs' not in qeeg_formatted:
                    qeeg_formatted['absolute_power_imgs'] = []
                if 'relative_zscore_imgs' not in qeeg_formatted:
                    qeeg_formatted['relative_zscore_imgs'] = []

                # 只有至少有一组数据才渲染（不包含ratio数据，因为Ratio Mapping单独处理）
                if (qeeg_formatted['absolute_power_imgs'] or qeeg_formatted['relative_zscore_imgs']):
                    current_page += 1
                    qeeg_formatted['current_page'] = current_page
                    qeeg_formatted['total_pages'] = total_pages
                    qeeg_formatted['hex_colors_css'] = HEX_COLORS_CSS
                    qeeg_formatted['rvmin'] = RVMIN
                    qeeg_formatted['rvmax'] = RVMAX
                    full_body.append(Template(self.COMPONENTS['qeeg_mapping']).render(qeeg_formatted))
            except Exception as e:
                print(f"渲染Quantitative EEG Mapping数据失败: {e}")
                import traceback
                traceback.print_exc()

        # 4. Full-Band Power Distribution (全频段功率分布) - 支持多任务列表
        if not is_qeeg:
            fullband_list = algo_results.get('full_band_mapping_data') or []
            if not isinstance(fullband_list, list):
                fullband_list = []
            if len(fullband_list) == 0:
                has_absolute = 'absolute_power_matrix' in algo_results
                has_relative = 'relative_power_matrix' in algo_results
                has_absolute_zscore = 'absolute_power_zscore' in algo_results
                has_relative_zscore = 'relative_power_zscore' in algo_results
                has_ratios = 'power_ratios' in algo_results
                if has_absolute or has_relative or has_absolute_zscore or has_relative_zscore or has_ratios:
                    fullband_list = [algo_results]
            for _fb_item in fullband_list:
                has_absolute = 'absolute_power_matrix' in _fb_item
                has_relative = 'relative_power_matrix' in _fb_item
                has_absolute_zscore = 'absolute_power_zscore' in _fb_item
                has_relative_zscore = 'relative_power_zscore' in _fb_item
                has_ratios = 'power_ratios' in _fb_item
                if not (has_absolute or has_relative or has_absolute_zscore or has_relative_zscore or has_ratios):
                    continue
                try:
                    _task_name = _fb_item.get('task_name', '')
                    absolute_topo_imgs = []
                    relative_topo_imgs = []
                    absolute_zscore_topo_imgs = []
                    relative_zscore_topo_imgs = []
                    ratio_topo_imgs = []

                    # 处理绝对功率矩阵（左上）
                    abs_global_vmin = 0.0
                    abs_global_vmax = 1.0
                    if has_absolute:
                        abs_data = _fb_item['absolute_power_matrix']
                        abs_global_vmin = abs_data.get('global_vmin', 0.0)
                        abs_global_vmax = abs_data.get('global_vmax', 1.0)
                        absolute_topo_imgs = abs_data.get('images') or abs_data.get('topo_imgs') or []
                        if not absolute_topo_imgs and 'data' in abs_data and abs_data['data']:
                            info = _fb_item.get('info') or algo_results.get('info')
                            channel_names = _fb_item.get('channel_names') or algo_results.get('channel_names')
                            frequencies = abs_data.get('frequencies',
                                                       [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32])
                            absolute_topo_imgs = generate_topography_matrix(
                                abs_data['data'], info=info, channel_names=channel_names,
                                frequencies=frequencies, global_vlim=True, cmap=TOPO_COLORMAP,
                                fixed_vlim=False
                            )
                        formatted_abs_imgs = []
                        for i, img in enumerate(absolute_topo_imgs):
                            if isinstance(img, dict):
                                url = img.get('url', '')
                                img_vmin = img.get('vmin', abs_global_vmin)
                                img_vmax = img.get('vmax', abs_global_vmax)

                                raw_for_label = img.get('label') if 'label' in img else img.get('freq')
                                label = normalize_band_hz_label(raw_for_label, index=i, step_hz=2, base_start_hz=2)
                            else:
                                url = str(img)
                                img_vmin = abs_global_vmin
                                img_vmax = abs_global_vmax
                                label = normalize_band_hz_label(None, index=i, step_hz=2, base_start_hz=2)
                            formatted_abs_imgs.append({
                                'url': url,
                                'freq': label,
                                'label': label,
                                'vmin': img_vmin,
                                'vmax': img_vmax,
                            })
                        absolute_topo_imgs = formatted_abs_imgs


                    # 处理相对功率矩阵（右上）
                    rel_global_vmin = 0.0
                    rel_global_vmax = 1.0
                    if has_relative:
                        rel_data = _fb_item['relative_power_matrix']
                        rel_global_vmin = rel_data.get('global_vmin', 0.0)
                        rel_global_vmax = rel_data.get('global_vmax', 1.0)
                        relative_topo_imgs = rel_data.get('images') or rel_data.get('topo_imgs') or []
                        if not relative_topo_imgs and 'data' in rel_data and rel_data['data']:
                            info = _fb_item.get('info') or algo_results.get('info')
                            channel_names = _fb_item.get('channel_names') or algo_results.get('channel_names')
                            frequencies = rel_data.get('frequencies',
                                                       [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32])
                            relative_topo_imgs = generate_topography_matrix(
                                rel_data['data'], info=info, channel_names=channel_names,
                                frequencies=frequencies, global_vlim=True, cmap=TOPO_COLORMAP,
                                fixed_vlim=False
                            )

                        formatted_rel_imgs = []
                        for i, img in enumerate(relative_topo_imgs):
                            if isinstance(img, dict):
                                url = img.get('url', '')
                                img_vmin = img.get('vmin', rel_global_vmin)
                                img_vmax = img.get('vmax', rel_global_vmax)
                                raw_for_label = img.get('label') if 'label' in img else img.get('freq')
                                label = normalize_band_hz_label(raw_for_label, index=i, step_hz=2, base_start_hz=2)
                            else:
                                url = str(img)
                                img_vmin = rel_global_vmin
                                img_vmax = rel_global_vmax
                                label = normalize_band_hz_label(None, index=i, step_hz=2, base_start_hz=2)
                            formatted_rel_imgs.append({
                                'url': url,
                                'freq': label,
                                'label': label,
                                'vmin': img_vmin,
                                'vmax': img_vmax,
                            })
                        relative_topo_imgs = formatted_rel_imgs

                    # 处理功率比率（左下）
                    if has_ratios:
                        ratio_data = _fb_item['power_ratios']
                        ratio_topo_imgs = ratio_data.get('images') or ratio_data.get('topo_imgs') or []
                        # 如果没有图片，但有数据，则生成图片（后备方案）
                        if not ratio_topo_imgs and 'data' in ratio_data and ratio_data['data']:
                            info = _fb_item.get('info') or algo_results.get('info')
                            channel_names = _fb_item.get('channel_names') or algo_results.get('channel_names')
                            if isinstance(ratio_data['data'], dict):
                                ratio_topo_imgs = generate_topography_matrix(
                                    ratio_data['data'], info=info, channel_names=channel_names,
                                    frequencies=None, global_vlim=True, cmap=TOPO_COLORMAP
                                )
                        # 格式化标签
                        ratio_labels = ['θ/α', 'θ/β', 'θ/高频', 'α/β', 'α/高频', 'β/高频',
                                        '高频/低频', '低频/高频', 'δ/θ', 'δ/α', 'δ/β', 'δ/高频']
                        formatted_ratio_imgs = []
                        for i, img in enumerate(ratio_topo_imgs):
                            if isinstance(img, dict):
                                url = img.get('url', '')
                                # 优先使用label字段
                                label = img.get('label') or img.get('name') or (
                                    ratio_labels[i] if i < len(ratio_labels) else f"Ratio{i + 1}")
                            else:
                                url = str(img)
                                label = ratio_labels[i] if i < len(ratio_labels) else f"Ratio{i + 1}"
                            formatted_ratio_imgs.append({
                                'url': url,
                                'label': label
                            })
                        ratio_topo_imgs = formatted_ratio_imgs

                    # 处理绝对功率Z-Score（左下）
                    if has_absolute_zscore:
                        abs_zscore_data = _fb_item['absolute_power_zscore']
                        absolute_zscore_topo_imgs = abs_zscore_data.get('images') or abs_zscore_data.get(
                            'topo_imgs') or []
                        if not absolute_zscore_topo_imgs and 'data' in abs_zscore_data and abs_zscore_data['data']:
                            info = _fb_item.get('info') or algo_results.get('info')
                            channel_names = _fb_item.get('channel_names') or algo_results.get('channel_names')
                            frequencies = abs_zscore_data.get('frequencies',
                                                              [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30,
                                                               32])
                            absolute_zscore_topo_imgs = generate_topography_matrix(
                                abs_zscore_data['data'], info=info, channel_names=channel_names,
                                frequencies=frequencies, global_vlim=True, cmap=TOPO_COLORMAP
                            )
                        formatted_abs_zscore_imgs = []
                        for i, img in enumerate(absolute_zscore_topo_imgs):
                            if isinstance(img, dict):
                                url = img.get('url', '')
                                raw_for_label = img.get('label') if 'label' in img else img.get('freq')
                                label = normalize_band_hz_label(raw_for_label, index=i, step_hz=2, base_start_hz=2)
                            else:
                                url = str(img)
                                label = normalize_band_hz_label(None, index=i, step_hz=2, base_start_hz=2)
                            formatted_abs_zscore_imgs.append({
                                'url': url,
                                'freq': label,
                                'label': label
                            })
                        absolute_zscore_topo_imgs = formatted_abs_zscore_imgs

                    # 处理相对功率Z-Score（右下）
                    if has_relative_zscore:
                        rel_zscore_data = _fb_item['relative_power_zscore']
                        relative_zscore_topo_imgs = rel_zscore_data.get('images') or rel_zscore_data.get(
                            'topo_imgs') or []
                        # 如果没有图片，但有数据，则生成图片（后备方案）
                        if not relative_zscore_topo_imgs and 'data' in rel_zscore_data and rel_zscore_data['data']:
                            info = _fb_item.get('info') or algo_results.get('info')
                            channel_names = _fb_item.get('channel_names') or algo_results.get('channel_names')
                            frequencies = rel_zscore_data.get('frequencies',
                                                              [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30,
                                                               32])
                            relative_zscore_topo_imgs = generate_topography_matrix(
                                rel_zscore_data['data'], info=info, channel_names=channel_names,
                                frequencies=frequencies, global_vlim=True, cmap=TOPO_COLORMAP
                            )
                        # 格式化标签
                        formatted_rel_zscore_imgs = []
                        for i, img in enumerate(relative_zscore_topo_imgs):
                            if isinstance(img, dict):
                                url = img.get('url', '')
                                raw_for_label = img.get('label') if 'label' in img else img.get('freq')
                                label = normalize_band_hz_label(raw_for_label, index=i, step_hz=2, base_start_hz=2)
                            else:
                                url = str(img)
                                label = normalize_band_hz_label(None, index=i, step_hz=2, base_start_hz=2)
                            formatted_rel_zscore_imgs.append({
                                'url': url,
                                'freq': label,
                                'label': label
                            })
                        relative_zscore_topo_imgs = formatted_rel_zscore_imgs


                    # 渲染 Full-Band Power Distribution 页面
                    current_page += 1
                    matrix_data = {
                        'absolute_topo_imgs': absolute_topo_imgs,
                        'relative_topo_imgs': relative_topo_imgs,
                        'absolute_zscore_topo_imgs': absolute_zscore_topo_imgs,
                        'relative_zscore_topo_imgs': relative_zscore_topo_imgs,
                        'ratio_topo_imgs': ratio_topo_imgs,
                        'abs_global_vmin': abs_global_vmin,
                        'abs_global_vmax': abs_global_vmax,
                        'rel_global_vmin': rel_global_vmin,
                        'rel_global_vmax': rel_global_vmax,
                        'patient_info': patient_info,
                        'logo_base64': self.logo_base64,
                        'analysis_method': f"Full-Band Power Distribution{' - ' + _task_name if _task_name else ''}",
                        'current_page': current_page,
                        'total_pages': total_pages,
                        'hex_colors_css': HEX_COLORS_CSS,
                        'rvmin': RVMIN,
                        'rvmax': RVMAX,
                        'total_pages': total_pages
                    }
                    full_body.append(Template(self.COMPONENTS['power_matrices_container']).render(matrix_data))
                except Exception as e:
                    print(f"渲染 Full-Band Power Distribution 失败: {e}")
                    import traceback
                    traceback.print_exc()

        # 5. Ratio Mapping 分析（支持多任务列表）
        ratio_map_list = algo_results.get('ratio_mapping_data') or []
        if not isinstance(ratio_map_list, list):
            ratio_map_list = []
        if len(ratio_map_list) == 0 and ('power_ratios' in algo_results or 'ratio_zscore' in algo_results):
            ratio_map_list = [algo_results]
        for _rm_item in ratio_map_list:
            try:
                ratio_formatted = prepare_ratio_mapping_data(_rm_item)
                if ratio_formatted.get('ratio_imgs') or ratio_formatted.get('ratio_zscore_imgs'):
                    ratio_formatted['patient_info'] = patient_info
                    ratio_formatted['logo_base64'] = self.logo_base64
                    _rn = _rm_item.get('task_name', '') if isinstance(_rm_item, dict) else ''
                    ratio_formatted['analysis_method'] = f"Full-Band Ratio Distribution{' - ' + _rn if _rn else ''}"
                    current_page += 1
                    ratio_formatted['current_page'] = current_page
                    ratio_formatted['total_pages'] = total_pages
                    if 'ratio_zscore_imgs' not in ratio_formatted:
                        ratio_formatted['ratio_zscore_imgs'] = []
                    ratio_formatted['hex_colors_css'] = HEX_COLORS_CSS
                    ratio_formatted['rvmin'] = RVMIN
                    ratio_formatted['rvmax'] = RVMAX
                    full_body.append(Template(self.COMPONENTS['ratio_mapping']).render(ratio_formatted))
            except Exception as e:
                print(f"渲染 Full-Band Ratio Distribution 数据失败: {e}")
                import traceback
                traceback.print_exc()

        # 6. TBR 分析（支持多任务列表）
        tbr_section_list = algo_results.get('tbr_data')
        if isinstance(tbr_section_list, dict):
            tbr_section_list = [tbr_section_list]
        if not isinstance(tbr_section_list, list):
            tbr_section_list = []
        for tbr_data in tbr_section_list:
            if not isinstance(tbr_data, dict):
                continue
            try:
                # 尝试多种可能的字段名
                fz_ratio = (tbr_data.get('fz_ratio') or
                            tbr_data.get('Fz_ratio') or
                            tbr_data.get('Fz比率') or
                            tbr_data.get('Fz 比率') or
                            tbr_data.get('FZ_ratio') or
                            tbr_data.get('FZ比率') or
                            tbr_data.get('FZ 比率'))

                cz_ratio = (tbr_data.get('cz_ratio') or
                            tbr_data.get('Cz_ratio') or
                            tbr_data.get('Cz比率') or
                            tbr_data.get('Cz 比率') or
                            tbr_data.get('CZ_ratio') or
                            tbr_data.get('CZ比率') or
                            tbr_data.get('CZ 比率'))

                avg_ratio = (tbr_data.get('avg_ratio') or
                             tbr_data.get('average_ratio') or
                             tbr_data.get('平均比率') or
                             tbr_data.get('average_ratio'))

                # 如果有Fz或Cz比率，计算平均比率（如果未提供）
                if (fz_ratio is not None and cz_ratio is not None) and not avg_ratio:
                    try:
                        fz_val = float(fz_ratio)
                        cz_val = float(cz_ratio)
                        avg_ratio = f"{(fz_val + cz_val) / 2:.2f}"
                    except (ValueError, TypeError):
                        pass

                # 格式化数值显示（保留2位小数）

                # 格式化数值显示（保留2位小数，四舍五入）
                if fz_ratio is not None:
                    try:
                        fz_ratio = f"{round(float(fz_ratio), 2):.2f}"
                    except (ValueError, TypeError):
                        pass

                if cz_ratio is not None:
                    try:
                        cz_ratio = f"{round(float(cz_ratio), 2):.2f}"
                    except (ValueError, TypeError):
                        pass

                if avg_ratio is not None:
                    try:
                        # 如果avg_ratio已经是字符串格式（计算出来的），需要重新格式化
                        if isinstance(avg_ratio, str):
                            avg_ratio = f"{round(float(avg_ratio), 2):.2f}"
                        else:
                            avg_ratio = f"{round(float(avg_ratio), 2):.2f}"
                    except (ValueError, TypeError):
                        pass

                # 只要有至少一个比率数据就渲染（即使没有全部数据）
                if fz_ratio is not None or cz_ratio is not None or avg_ratio is not None:
                    # 计算指针位置和等级信息
                    pointer_position = None
                    grade = 'N/A'
                    status = 'N/A'
                    status_color = 'gray'

                    if avg_ratio and avg_ratio != 'N/A':
                        try:
                            avg_val = float(avg_ratio)
                            if 1.0 <= avg_val <= 3.0:
                                # 计算指针位置：从1.0到3.0，共2.0范围
                                pointer_position = round(((avg_val - 1.0) / 2.0 * 100), 2)

                                # 确定等级和状态（区间：A<1, B[1,1.5), C[1.5,2), D[2,2.5), E>=2.5）
                                if avg_val < 1.0:
                                    grade = 'A'
                                    status = '优秀'
                                    status_color = 'green'
                                elif 1.0 <= avg_val < 1.5:
                                    grade = 'B'
                                    status = '良好'
                                    status_color = 'lightgreen'
                                elif 1.5 <= avg_val < 2.0:
                                    grade = 'C'
                                    status = '临界'
                                    status_color = '#cccc00'
                                elif 2.0 <= avg_val < 2.5:
                                    grade = 'D'
                                    status = '轻度异常'
                                    status_color = 'orange'
                                else:
                                    grade = 'E'
                                    status = '严重异常'
                                    status_color = 'red'
                        except (ValueError, TypeError):
                            pass

                    _tbr_task = tbr_data.get('task_name', '')
                    tbr_formatted = {
                        'patient_info': patient_info,
                        'logo_base64': self.logo_base64,
                        'analysis_method': f"TBR 分析 (Theta/Beta Ratio){' - ' + _tbr_task if _tbr_task else ''}",
                        'fz_ratio': fz_ratio or 'N/A',
                        'cz_ratio': cz_ratio or 'N/A',
                        'avg_ratio': avg_ratio or 'N/A',
                        'pointer_position': pointer_position,
                        'grade': grade,
                        'status': status,
                        'status_color': status_color
                    }

                    tbr_formatted['current_page'] = current_page
                    tbr_formatted['total_pages'] = total_pages
                else:
                    print("警告: TBR分析数据存在但没有有效的比率值（fz_ratio、cz_ratio 或 avg_ratio）")
            except Exception as e:
                print(f"渲染TBR分析数据失败: {e}")
                import traceback
                traceback.print_exc()

        # 7. Peak Alpha Frequency 分析（支持多任务列表）
        paf_section_raw = algo_results.get('peak_alpha_frequency_data') or algo_results.get('paf_data')
        paf_section_list = paf_section_raw if isinstance(paf_section_raw, list) and len(paf_section_raw) > 0 else ([paf_section_raw] if isinstance(paf_section_raw, dict) else [])
        for paf_data in paf_section_list:
            if not isinstance(paf_data, dict):
                continue
            try:
                # 尝试多种可能的字段名
                o1_peak = (paf_data.get('o1_peak') or
                           paf_data.get('O1_peak') or
                           paf_data.get('O1峰值') or
                           paf_data.get('O1 峰值') or
                           paf_data.get('O1_peak_frequency') or
                           paf_data.get('o1_peak_frequency'))

                o2_peak = (paf_data.get('o2_peak') or
                           paf_data.get('O2_peak') or
                           paf_data.get('O2峰值') or
                           paf_data.get('O2 峰值') or
                           paf_data.get('O2_peak_frequency') or
                           paf_data.get('o2_peak_frequency'))

                avg_peak = (paf_data.get('avg_peak') or
                            paf_data.get('average_peak') or
                            paf_data.get('平均峰值') or
                            paf_data.get('average_peak_frequency'))

                # 如果有O1或O2峰值，计算平均峰值（如果未提供）
                if (o1_peak is not None and o2_peak is not None) and not avg_peak:
                    try:
                        o1_val = float(o1_peak)
                        o2_val = float(o2_peak)
                        avg_peak = f"{round((o1_val + o2_val) / 2, 2):.2f}"
                    except (ValueError, TypeError):
                        pass

                # 格式化数值显示（保留2位小数）

                # 格式化数值显示（保留2位小数，四舍五入）
                if o1_peak is not None:
                    try:
                        o1_peak = f"{round(float(o1_peak), 2):.2f}"
                    except (ValueError, TypeError):
                        pass

                if o2_peak is not None:
                    try:
                        o2_peak = f"{round(float(o2_peak), 2):.2f}"
                    except (ValueError, TypeError):
                        pass

                if avg_peak is not None:
                    try:
                        # 如果avg_peak已经是字符串格式（计算出来的），需要重新格式化
                        if isinstance(avg_peak, str):
                            avg_peak = f"{round(float(avg_peak), 2):.2f}"
                        else:
                            avg_peak = f"{round(float(avg_peak), 2):.2f}"
                    except (ValueError, TypeError):
                        pass

                # 只要有至少一个峰值数据就渲染（即使没有全部数据）
                if o1_peak is not None or o2_peak is not None or avg_peak is not None:
                    # 计算指针位置和等级信息
                    pointer_position = None
                    grade = 'N/A'
                    status = 'N/A'
                    status_color = 'gray'

                    if avg_peak and avg_peak != 'N/A':
                        try:
                            avg_val = float(avg_peak)
                            # 使用线性刻度表计算指针位置
                            # 刻度范围：4-14 Hz
                            # 线性映射：最小值4对应0%，最大值14对应100%
                            paf_min = 4.0
                            paf_max = 14.0
                            
                            # 计算指针位置
                            if paf_min <= avg_val <= paf_max:
                                # 线性计算：位置 = (值 - 最小值) / (最大值 - 最小值) * 100
                                pointer_position = round((avg_val - paf_min) / (paf_max - paf_min) * 100, 2)
                            elif avg_val < paf_min:
                                # 小于最小值时，指针指向0%
                                pointer_position = 0.0
                            elif avg_val > paf_max:
                                # 大于最大值时，指针指向100%
                                pointer_position = 100.0
                            else:
                                # 超出范围时，指针指向中间位置（50%）
                                pointer_position = 50.0

                            # 确定等级和状态（仅在有效范围内）
                            if 4.0 <= avg_val < 5.0:
                                grade = 'F'
                                status = '严重偏低'
                                status_color = 'red'
                            elif 5.0 <= avg_val < 6.0:
                                grade = 'E'
                                status = '中度偏低'
                                status_color = 'darkorange'
                            elif 6.0 <= avg_val < 7.0:
                                grade = 'D'
                                status = '轻度偏低'
                                status_color = 'orange'
                            elif 7.0 <= avg_val < 8.0:
                                grade = 'C/B'
                                status = '临界/良好'
                                status_color = '#cccc00'
                            elif 8.0 <= avg_val <= 12.0:
                                grade = 'A'
                                status = '正常'
                                status_color = 'green'
                            elif 12.0 < avg_val <= 14.0:
                                grade = 'B-F'
                                status = '偏高'
                                status_color = '#90EE90'
                        except (ValueError, TypeError):
                            pass
                    _paf_task = paf_data.get('task_name', '')
                    paf_formatted = {
                        'patient_info': patient_info,
                        'logo_base64': self.logo_base64,
                        'analysis_method': f"Peak Alpha Frequency{' - ' + _paf_task if _paf_task else ''}",
                        'o1_peak': o1_peak or 'N/A',
                        'o2_peak': o2_peak or 'N/A',
                        'avg_peak': avg_peak or 'N/A',
                        'pointer_position': pointer_position,
                        'grade': grade,
                        'status': status,
                        'status_color': status_color
                    }
                    paf_formatted['current_page'] = current_page
                    paf_formatted['total_pages'] = total_pages
                else:
                    print("警告: Peak Alpha Frequency分析数据存在但没有有效的峰值数据（o1_peak、o2_peak 或 avg_peak）")
            except Exception as e:
                print(f"渲染Peak Alpha Frequency分析数据失败: {e}")
                import traceback
                traceback.print_exc()

        # 8. 添加综合评估和建议组件（报告输出验收页面）
        # 仅当 show_report_output 为 True 时才在报告末尾渲染该页面
        if show_report_output:
            try:
                current_page += 1
                assessment_data = {
                    'patient_info': patient_info,
                    'logo_base64': self.logo_base64,
                    'assessment_text': algo_results.get('assessment_text', ''),
                    'doctor_name': algo_results.get('doctor_name', ''),
                    'assessment_date': algo_results.get('assessment_date', patient_info.get('date', '')),
                    'current_page': current_page,
                    'total_pages': total_pages
                }
                full_body.append(Template(self.COMPONENTS['comprehensive_assessment']).render(assessment_data))
            except Exception as e:
                print(f"渲染综合评估组件失败: {e}")
                import traceback
                traceback.print_exc()

        # 6. 合并完整 HTML
        try:
            # 动态生成 CSS，添加 headmodel 背景图片（如果存在）
            dynamic_css = ControlStyle.get_CSS()
            if self.headmodel_base64:
                # 在 .topography-container 样式中添加背景图片
                headmodel_bg_css = f"""
            .topography-container {{
                background-image: url({self.headmodel_base64});
                background-color: transparent;
            }}
"""
                # 在 </style> 之前插入动态 CSS
                dynamic_css = dynamic_css.replace('</style>', headmodel_bg_css + '        </style>')
            else:
                # 如果没有 headmodel 图片，使用渐变背景作为后备
                fallback_bg_css = """
            .topography-container {
                background: linear-gradient(135deg, #e8f0f8 0%, #f0f5fa 100%);
            }
"""
                dynamic_css = dynamic_css.replace('</style>', fallback_bg_css + '        </style>')

            html = f"<html><head><meta charset=\"UTF-8\">{dynamic_css}</head><body>{''.join(full_body)}</body></html>"
            return html
        except Exception as e:
            print(f"生成HTML失败: {e}")
            import traceback
            traceback.print_exc()
            # 返回至少包含页眉的错误页面
            error_html = f"<html><head><meta charset=\"UTF-8\">{ControlStyle.get_CSS()}</head><body><div class='section'><h3>错误</h3><p>报告生成失败: {str(e)}</p></div></body></html>"
            return error_html


# ==========================================
# PyQt 预览窗口（可嵌入的Widget）
# ==========================================
class ReportPreviewWindow(QWidget):
    # 定义信号：PDF生成完成时发出，传递PDF路径
    pdf_generated = pyqtSignal(str)

    def __init__(self, algo_results, parent=None, logo_path=None):
        super().__init__(parent)

        # 初始化PDF路径属性
        self.pdf_path = None
        # 保存HTML文件路径
        self.html_path = None
        # 保存生成报告所需的上下文（用于后续入库）
        self.algo_results = algo_results or {}
        # 记录一次导出时选择的路径（printToPdf是异步的，真正成功/失败在pdfPrintingFinished里）
        self._pending_pdf_path = None
        # 进度对话框（用于显示PDF打印进度）
        self._progress_dialog = None

        # 如果提供了上传的logo路径，使用它；否则使用默认logo
        self.engine = DynamicReportEngine(logo_path=logo_path, parent=self)
        try:
            # 修复：使用处理过的 self.algo_results（确保不是 None），而不是原始的 algo_results

            self.html_content = self.engine.build(self.algo_results)
            html_size_mb = len(self.html_content) / (1024 * 1024)
            print(f"HTML生成成功，长度: {len(self.html_content)} 字节 ({html_size_mb:.2f} MB)")

            # 检查HTML内容是否有效
            if not self.html_content or len(self.html_content) < 100:
                print("警告: HTML内容过短，可能生成失败")
            else:
                # 检查HTML结构
                if '<html' in self.html_content and '</html>' in self.html_content:
                    print("HTML结构正确")
                else:
                    print("警告: HTML结构可能不完整")

                # 显示HTML的前500个字符用于调试
                print(f"HTML开头: {self.html_content[:500]}...")

        except Exception as e:
            print(f"生成HTML内容失败: {e}")
            import traceback
            traceback.print_exc()
            # 生成错误页面
            self.html_content = f"<html><head><meta charset=\"UTF-8\">{ControlStyle.get_CSS()}</head><body><div class='section'><h3>错误</h3><p>报告生成失败: {str(e)}</p></div></body></html>"

        # UI
        # 检查 WebEngine 是否可用
        if not WEBENGINE_AVAILABLE:
            error_label = QWidget()
            error_layout = QVBoxLayout(error_label)
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Warning)
            error_msg.setWindowTitle("缺少依赖")
            error_msg.setText("PyQtWebEngine 未安装")
            error_msg.setInformativeText(
                "报告预览功能需要 PyQtWebEngine 库。\n\n"
                "请运行以下命令安装：\n"
                "pip install PyQtWebEngine\n\n"
                "注意：PyQt5.QtWebEngineWidgets 需要单独安装 PyQtWebEngine 包，"
                "仅安装 PyQt5 是不够的。"
            )
            error_layout.addWidget(error_msg)
            self.browser = error_label
            QMessageBox.warning(
                parent if parent else None,
                "缺少依赖",
                "PyQtWebEngine 未安装。请运行: pip install PyQtWebEngine\n\n"
                "注意：PyQt5.QtWebEngineWidgets 需要单独安装 PyQtWebEngine 包"
            )
        else:
            self.browser = QWebEngineView()
            try:
                self.browser.setPage(ReportPreviewWebPage(self, self.browser))
            except Exception:
                pass

            # 启用内容编辑功能
            page = self.browser.page()
            page.settings().setAttribute(page.settings().WebAttribute.LocalContentCanAccessRemoteUrls, True)
            page.settings().setAttribute(page.settings().WebAttribute.LocalContentCanAccessFileUrls, True)
            # 监听PDF打印完成（filePath, success）
            try:
                page.pdfPrintingFinished.connect(self._on_pdf_printing_finished)
            except Exception:
                # 兼容性兜底：某些环境可能没有该信号
                pass

            # 连接加载完成信号
            self.browser.loadFinished.connect(self.on_load_finished)

        # 设置HTML内容 - 对于大文件使用临时文件方式
        if WEBENGINE_AVAILABLE:
            print("正在加载HTML到浏览器...")
            try:
                self._generate_and_load_html()
            except Exception as e:
                print(f"加载HTML失败: {e}")
                import traceback
                traceback.print_exc()
                # 显示错误页面
                error_html = f"<html><head><meta charset=\"UTF-8\">{ControlStyle.get_CSS()}</head><body><div class='section'><h3>加载错误</h3><p>HTML加载失败: {str(e)}</p><p>HTML大小: {len(self.html_content)} 字节</p></div></body></html>"
                from PyQt5.QtCore import QUrl
                base_url = QUrl("about:blank")
                self.browser.setHtml(error_html, base_url)
        else:
            print("警告: WebEngine 不可用，无法显示报告预览")

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

        layout = QVBoxLayout()
        layout.addWidget(self.browser)
        layout.addWidget(self.btn_save)
        layout.setContentsMargins(0, 0, 0, 0)  # 移除边距，便于嵌入
        self.setLayout(layout)

        # 初始化临时文件路径
        self.temp_html_file = None
        
    def _generate_and_load_html(self):
        """生成HTML文件并加载到浏览器"""
        import os
        import datetime
        import sys
        
        # 获取患者信息用于文件名
        patient_info = (self.algo_results or {}).get("patient_info") or {}
        patient_id = patient_info.get("id", "unknown")
        patient_name = patient_info.get("name", "unknown")
        
        # 生成唯一的HTML文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        html_filename = f"脑电报告_{patient_id}_{patient_name}_{timestamp}.html"
        
        # 参考user_logo的路径设置，保存到resource/html_reports目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        html_parent_dir = os.path.join(current_dir, '..', 'resource')
        html_parent_dir = os.path.normpath(html_parent_dir)  # 规范化路径，将..解析掉
        html_dir = os.path.join(html_parent_dir, 'html_reports')

        if getattr(sys, "frozen", False):
            dir = os.path.dirname(os.path.abspath(sys.executable))
            html_dir = os.path.join(dir, 'resource', 'html_reports')
        
        # 自动创建目标目录
        os.makedirs(html_dir, exist_ok=True)
        
        self.html_path = os.path.join(html_dir, html_filename)
        
        # 写入HTML文件
        with open(self.html_path, 'w', encoding='utf-8') as f:
            f.write(self.html_content)
        
        print(f"HTML文件已保存到: {self.html_path}")
        
        # 加载HTML文件
        from PyQt5.QtCore import QUrl
        file_url = QUrl.fromLocalFile(self.html_path)
        self.browser.setUrl(file_url)
        
        # 保存HTML文件路径以便后续清理
        self.temp_html_file = self.html_path
        
        # 保存HTML路径到数据库
        self._save_html_path_to_db()

    def _save_html_path_to_db(self):
        """保存HTML文件路径到数据库"""
        if not self.html_path:
            return
        
        try:
            # 组装 record dict（字段对齐 HistoryTask.from_dict 要求）
            patient_info = (self.algo_results or {}).get("patient_info") or {}
            record_dict = {
                # t_history_task.id 是数据库自增主键，这里保持 None
                "id": None,
                # 这里的 name 用“病人姓名”
                # 从HTML文件路径中提取文件名（去掉路径和扩展名）
                # 例如：/path/to/脑电报告1.html -> 脑电报告1
                "name": os.path.splitext(os.path.basename(self.html_path))[0] if self.html_path else "N/A",
                # 报告生成时间
                "created_date": patient_info.get("collection_time"),
                "relative_path": self.html_path,
                # 这里的 subject_id 用“病人ID”
                "subject_id": patient_info.get("id") or None,
            }

            # 创建Subject对象（HistoryTask对象）
            record = HistoryTask.from_dict({
                "id": record_dict["id"],
                "name": record_dict["name"],
                "created_date": record_dict["created_date"] if record_dict["created_date"] else None,
                "relative_path": record_dict["relative_path"] if record_dict["relative_path"] else None,
                "subject_id": record_dict["subject_id"] if record_dict["subject_id"] else None,
            })

            # 使用Subject类的方法插入数据
            success_db = HistoryTask.insert(SQLLiteDB_Only_MainTread.user_db, record)
            
            if success_db:
                print(f"HTML路径已成功保存到数据库: {self.html_path}")
            else:
                print("警告: HTML路径写入数据库失败")
                
        except Exception as e:
            print(f"保存HTML路径到数据库失败: {e}")
            import traceback
            traceback.print_exc()

    def update_logo(self, logo_path=None):
        """
        更新logo图片并重新生成报告
        
        参数:
            logo_path: 新的logo图片路径。如果为None，将使用默认logo
        """
        try:
            print(f"更新报告logo，路径: {logo_path}")

            # 更新logo
            self.engine.update_logo(logo_path)

            # 重新生成HTML内容（使用现有的algo_results）
            self.html_content = self.engine.build(self.algo_results)
            html_size_mb = len(self.html_content) / (1024 * 1024)
            print(f"HTML重新生成成功（logo已更新），长度: {len(self.html_content)} 字节 ({html_size_mb:.2f} MB)")

            # 更新浏览器显示
            if WEBENGINE_AVAILABLE:
                # 清理旧的临时文件
                if hasattr(self, 'temp_html_file') and self.temp_html_file:
                    try:
                        if os.path.exists(self.temp_html_file):
                            os.unlink(self.temp_html_file)
                    except Exception:
                        pass

                # 生成新的HTML文件并加载
                self._generate_and_load_html()
                print(f"HTML文件已更新并保存到: {self.html_path}")
            else:
                print("警告: WebEngine 不可用，无法更新报告预览")

        except Exception as e:
            print(f"更新logo失败: {e}")
            import traceback
            traceback.print_exc()
            # 生成错误页面
            if WEBENGINE_AVAILABLE:
                error_html = f"<html><head><meta charset=\"UTF-8\">{ControlStyle.get_CSS()}</head><body><div class='section'><h3>更新错误</h3><p>Logo更新失败: {str(e)}</p></div></body></html>"
                from PyQt5.QtCore import QUrl
                base_url = QUrl("about:blank")
                self.browser.setHtml(error_html, base_url)

    def on_load_finished(self, success):
        """HTML加载完成回调"""
        if success:
            print("HTML加载成功，浏览器应该显示内容了")
        else:
            print("警告: HTML加载失败，浏览器可能显示空白")
            # 尝试获取更多错误信息
            print(f"当前URL: {self.browser.url().toString()}")

    def cleanup(self):
        """清理临时文件（可在外部调用或在销毁时自动调用）"""
        try:
            if hasattr(self, 'temp_html_file') and self.temp_html_file and os.path.exists(self.temp_html_file):
                os.unlink(self.temp_html_file)
                print(f"已删除临时文件: {self.temp_html_file}")
                self.temp_html_file = None
        except Exception as e:
            print(f"删除临时文件失败: {e}")

    def closeEvent(self, event):
        """窗口关闭事件，清理临时文件"""
        self.cleanup()
        super().closeEvent(event)

    def _persist_assessment_to_html(self, content):# 把评论内容写回到磁盘上的 HTML 文件（self.html_path）里
        if not content:
            return
        if not hasattr(self, 'html_path') or not self.html_path:
            return
        if not os.path.exists(self.html_path):
            return

        try:
            with open(self.html_path, 'r', encoding='utf-8') as f:
                full_html = f.read()
            pattern = r'(<div[^>]*id="assessment-text-editor"[^>]*>)([\s\S]*?)(</div>\s*<div[^>]*>\s*<button\s+id="save-btn")'
            new_html = re.sub(pattern, lambda m: m.group(1) + content + m.group(3), full_html, count=1)
            with open(self.html_path, 'w', encoding='utf-8') as f:
                f.write(new_html)
            try:
                self.algo_results["assessment_text"] = content
            except Exception:
                pass
        except Exception as e:
            print(f"回写评论到HTML失败: {e}")
#接收“网页侧发来的保存事件”，把 payload 解码成真正的 HTML 内容，然后调用上面的落盘函数
    def _on_assessment_saved_from_console(self, payload):
        try:
            from urllib.parse import unquote
            content = unquote(payload or "")
        except Exception:
            content = payload or ""
        self._persist_assessment_to_html(content)
#导出 PDF 时，先确保评论已经写入 HTML 文件，再调用原来的 printToPdf 导出
    def handle_save_pdf(self):
        if not WEBENGINE_AVAILABLE:
            QMessageBox.warning(
                self,
                "功能不可用",
                "PDF导出功能需要 PyQtWebEngine 库。\n\n"
                "请运行以下命令安装：\n"
                "pip install PyQtWebEngine\n\n"
                "注意：PyQt5.QtWebEngineWidgets 需要单独安装 PyQtWebEngine 包"
            )
            return

        patient_info = (self.algo_results or {}).get("patient_info") or {}
        id = patient_info.get("id")
        name = patient_info.get("name")

        print(f"id={id}, name={name}")
        path, _ = QFileDialog.getSaveFileName(self, "导出 PDF", "脑电报告_" + id + "_" + name + ".pdf",
                                              "PDF Files (*.pdf)")
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
                # 批注：清理“待导出”的路径状态（防止后面误触发导出）
                return 
            # 批注：直接返回，不再继续导出
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
        self._persist_assessment_to_html(content)
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
        # 关闭进度对话框
        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

        try:
            # 以回调里的file_path为准；若为空则回退到pending
            final_path = file_path or self._pending_pdf_path
            self._pending_pdf_path = None

            if not success or not final_path:
                QMessageBox.warning(self, "导出失败", "PDF导出失败（浏览器未能生成文件）。")
                return

            # 保存PDF路径 + 发出信号
            self.pdf_path = final_path
            # self.pdf_generated.emit(final_path)

            # UI提示
            QMessageBox.information(self, "导出成功", f"PDF已成功保存到：\n{final_path}")
        except Exception as e:
            QMessageBox.warning(self, "导出提示", f"PDF已生成，但后处理失败：\n{str(e)}")
            import traceback
            traceback.print_exc()

    def get_pdf_path(self):
        """获取最后生成的PDF路径"""
        return self.pdf_path
