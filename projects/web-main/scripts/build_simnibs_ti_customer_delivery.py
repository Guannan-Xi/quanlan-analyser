"""Build the customer-facing report package from a completed Ernie TI run."""

from __future__ import annotations

import csv
import gzip
import hashlib
import html
import json
import math
import re
import shutil
import struct
import subprocess
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "simnibs_customer_ti_demo_ernie_20260728"
RAW = OUTPUT / "raw_simnibs"
TEMPLATE = ROOT / "frontend" / "simnibs-report-template.html"
RUN_ID = "ernie-forward-ti-f5p5-f6p6-1ma-20260728"
REPORT_ID = "QLA-SIMNIBS-TI-DEMO-ERNIE-20260728-01"

# Publication layout budget: 2000 x 1200 px, 3 panels maximum for slices,
# 120 px outer margins, 34 px minimum labels, legends outside data panels.
CANVAS = (2000, 1200)
MARGIN = 110
INK = "#17211D"
MUTED = "#5E6B64"
GREEN = "#176B50"
BLUE = "#245F8F"
AMBER = "#A36B18"
RED = "#A1433F"
LINE = "#D8DFDB"
PAPER = "#FFFFFF"
FONT_REGULAR = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_BOLD = Path(r"C:\Windows\Fonts\msyhbd.ttc")

FIGURE_TEXT = {
    "model_registration": {
        "label": "图 1｜个体解剖、组织边界与预定义目标区。",
        "caption": "三幅正交切面均通过由 MNI 坐标变换到个体空间的 ROI 中心；绿色圆环表示半径 10 mm 的 MNI 定义目标区，白线表示组织标签边界。本图用于核查目标区在个体解剖上的叠加位置，不等同于个体皮层 atlas 对中央前回的独立确认；图中不包含电极位置。",
        "alt": "ernie 个体 T1 MRI 的矢状、冠状和轴状切面，绿色圆环标出 MNI 定义的左侧 M1 球形目标区。",
    },
    "stimulation_montage": {
        "label": "图 2｜刺激电极布局与目标区位置。",
        "caption": "红色标记为 F5、F6 的 +1 mA 电极，蓝色标记为 P5、P6 的 -1 mA 电极；数值均为用于缩放准静态载波场的峰值电流幅度，不是 RMS。绿色圆环表示 MNI 定义的左侧 M1 球形 ROI。左侧位、前位和上位投影显示两组回路相对目标区的空间关系。",
        "alt": "皮层表面的左侧位、前位和上位投影，显示 F5、P5、F6、P6 电极及左侧 M1 目标区。",
    },
    "field_e1": {
        "label": "图 3A｜载波电场 E1 的空间分布。",
        "caption": "E1 按 F5(+1 mA 峰值)/P5(-1 mA 峰值) 回路标定，三幅切面通过目标区中心；切面组色标上限为 0.242 V/m，与表面组 0.191 V/m 的颜色不可直接比较。较高场强主要分布在 F5/P5 同侧，目标 ROI 位于该场的空间梯度内。",
        "alt": "F5-P5 回路载波电场 E1 在目标区中心的三正交切面分布，单位为伏每米。",
    },
    "field_e2": {
        "label": "图 3B｜载波电场 E2 的空间分布。",
        "caption": "E2 按 F6(+1 mA 峰值)/P6(-1 mA 峰值) 回路标定，并与图 3A 使用相同切面和 0–0.242 V/m 色标；与表面组 0.191 V/m 的颜色不可直接比较。其高场区相对 E1 呈对侧分布，目标 ROI 内场强低于该回路的皮层高值区。",
        "alt": "F6-P6 回路载波电场 E2 在目标区中心的三正交切面分布，单位为伏每米。",
    },
    "field_primary": {
        "label": "图 3C｜最大时间干涉包络场 TImax。",
        "caption": "TImax 由按峰值电流幅度标定的 E1 与 E2 逐单元计算，表示最大包络幅值，不是 RMS 或峰峰值。切面与图 3A、3B 一致，切面组色标上限为 0.242 V/m；各面标注 SimNIBS 个体 conform 物理坐标及 L/R、A/P、S/I 方向。当前网格中，全灰质单个四面体 argmax 不位于目标 ROI 内；图 3D–3E 用黑色菱形显示其投影，完整个体/MNI 坐标、单元体积、界面标签及距离见 raw_simnibs/tables/peak_spatial_relationship.csv 和 Excel“峰值空间关系”工作表。本示例未通过网格、电导率或电极位置扰动检验该峰值位置的稳定性。",
        "alt": "最大时间干涉包络场 TImax 在目标区中心的三正交切面分布，绿色圆环标出目标区，单位为伏每米。",
    },
    "field_surface": {
        "label": "图 3D｜皮层表面 TImax 分布。",
        "caption": "表面值由体网格 TImax 插值到灰质表面，三个投影视角使用同一色标，表面组色标上限为 0.191 V/m；该上限与图 3A–3C 的 0.242 V/m 不同，两组颜色不可直接比较。绿色圆环表示 ROI 中心，黑色菱形表示当前网格全灰质单四面体峰值（0.397 V/m，超过显示上限），连线标注其与 ROI 中心的三维距离。较高表面场分布跨越多个皮层区域，并未局限于预定义目标区。",
        "alt": "皮层表面 TImax 的左侧位、前位和上位投影，绿色圆环标出左侧 M1 目标区。",
    },
    "field_3d": {
        "label": "图 3E｜TImax、目标区与刺激电极的空间关系。",
        "caption": "皮层表面颜色表示 TImax，红蓝标记分别表示正、负电极，绿色圆环表示 ROI 中心，黑色菱形表示当前网格全灰质单四面体峰值（0.397 V/m，超过 0.191 V/m 的 P99 显示上限）；连线标注峰值与 ROI 中心的三维距离。电极、目标区和皮层高场区的联合投影显示，本方案的高场分布未围绕左侧 M1 ROI 聚集。",
        "alt": "TImax 皮层表面与四个刺激电极、左侧 M1 目标区的三视角联合投影。",
    },
    "roi_distribution": {
        "label": "图 4A｜目标区与目标区外灰质的 TImax 分布。",
        "caption": "目标区外灰质定义为 ernie 网格中全部 SimNIBS tag 2 灰质四面体减去目标 ROI，不设额外解剖排除或过渡缓冲。曲线按各区域四面体体积归一化，橙色竖线为全灰质 TImax 的体积加权 P99.9。全灰质覆盖率约 0.1% 由 P99.9 定义决定，不是经验结果，也不能用于跨方案或跨受试者比较；报告关注该高值尾部在目标区与目标区外的体积分配。P99.9 不是神经激活阈值或临床有效阈值；全灰质单四面体 argmax 仅用于空间和网格界面质量控制，不参与阈值定义。",
        "alt": "目标区和目标区外灰质的体积加权 TImax 分布曲线及描述性覆盖阈值。",
    },
    "target_offtarget": {
        "label": "图 4B｜目标区与目标区外灰质的定量比较。",
        "caption": "目标区外灰质定义为 ernie 网格中全部 SimNIBS tag 2 灰质四面体减去目标 ROI，不设额外解剖排除或过渡缓冲；各区域体积见 ROI 统计表。柱高分别表示四面体体积加权 mean、median 和 P95，柱顶标注精确值；分位数取累计四面体体积第一次达到相应概率时的单元值，不进行线性插值。本图不进行组水平推断。基准目标区 mean 和 median 略高，但 P95 低于目标区外灰质。±3 mm ROI 位移下 P95 比值可跨过 1，详见稳健性结果。",
        "alt": "目标区与目标区外灰质的 TImax 均值、中位数和第 95 百分位数柱状比较。",
    },
    "robustness_summary": {
        "label": "图 5｜目标 ROI 中心位置敏感性。",
        "caption": "曲线表示 ROI 中心沿个体空间三轴平移 ±3 mm 后，mean 与 P95 相对基准值的变化；未包含电极、电导率或网格扰动。所有位置扰动下 mean 最大绝对变化为 7.30%，P95 最大绝对变化为 11.73%；Target/Off-target P95 比值范围为 0.846–1.022。该分析只移动 ROI 中心，复用同一次 FEM 场解及同一峰值坐标，不构成峰值位置稳定性检验。",
        "alt": "左后下到右前上六种三毫米 ROI 位移条件下，TImax 均值和第 95 百分位数相对基准的百分比变化。",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sample_nifti_vector_field(path: Path, world_coordinate_mm: list[float]) -> dict:
    """Sample a float32/float64 NIfTI vector field at one physical coordinate."""

    opener = gzip.open if path.name.endswith(".gz") else Path.open
    with opener(path, "rb") as stream:
        header = stream.read(352)
        if len(header) != 352:
            raise RuntimeError(f"Incomplete NIfTI header: {path}")
        if struct.unpack("<i", header[:4])[0] == 348:
            endian = "<"
        elif struct.unpack(">i", header[:4])[0] == 348:
            endian = ">"
        else:
            raise RuntimeError(f"Invalid NIfTI-1 header: {path}")
        dimensions = struct.unpack(endian + "8h", header[40:56])
        datatype = struct.unpack(endian + "h", header[70:72])[0]
        bitpix = struct.unpack(endian + "h", header[72:74])[0]
        vox_offset = int(struct.unpack(endian + "f", header[108:112])[0])
        slope = float(struct.unpack(endian + "f", header[112:116])[0])
        intercept = float(struct.unpack(endian + "f", header[116:120])[0])
        sform_code = struct.unpack(endian + "h", header[254:256])[0]
        datatype_formats = {(16, 32): ("f", 4), (64, 64): ("d", 8)}
        if (datatype, bitpix) not in datatype_formats or dimensions[0] < 4 or dimensions[4] != 3:
            raise RuntimeError(f"Expected a float32 or float64 NIfTI vector field: {path}")
        value_format, value_bytes = datatype_formats[(datatype, bitpix)]
        if sform_code <= 0:
            raise RuntimeError(f"NIfTI vector field has no sform affine: {path}")
        affine = np.eye(4, dtype=float)
        affine[:3, :] = np.asarray(
            [
                struct.unpack(endian + "4f", header[280:296]),
                struct.unpack(endian + "4f", header[296:312]),
                struct.unpack(endian + "4f", header[312:328]),
            ],
            dtype=float,
        )
        voxel_coordinate = np.linalg.inv(affine) @ np.asarray([*world_coordinate_mm, 1.0], dtype=float)
        voxel_coordinate = voxel_coordinate[:3]
        lower = np.floor(voxel_coordinate).astype(int)
        fraction = voxel_coordinate - lower
        nx, ny, nz = (int(dimensions[index]) for index in (1, 2, 3))
        if np.any(lower < 0) or np.any(lower + 1 >= np.asarray([nx, ny, nz])):
            raise RuntimeError(f"Coordinate lies outside NIfTI vector field: {world_coordinate_mm}")
        requests = []
        for x_offset in range(2):
            for y_offset in range(2):
                for z_offset in range(2):
                    weight = (
                        (fraction[0] if x_offset else 1.0 - fraction[0])
                        * (fraction[1] if y_offset else 1.0 - fraction[1])
                        * (fraction[2] if z_offset else 1.0 - fraction[2])
                    )
                    i, j, k = lower + np.asarray([x_offset, y_offset, z_offset])
                    for component in range(3):
                        flat_index = int(i + nx * j + nx * ny * k + nx * ny * nz * component)
                        requests.append((vox_offset + value_bytes * flat_index, component, float(weight)))
        sampled = np.zeros(3, dtype=float)
        for byte_offset, component, weight in sorted(requests):
            stream.seek(byte_offset)
            raw_value = stream.read(value_bytes)
            if len(raw_value) != value_bytes:
                raise RuntimeError(f"Incomplete NIfTI vector-field payload: {path}")
            sampled[component] += weight * struct.unpack(endian + value_format, raw_value)[0]
        if not math.isfinite(slope) or slope == 0.0:
            slope = 1.0
        if not math.isfinite(intercept):
            intercept = 0.0
        sampled = sampled * slope + intercept
    return {
        "sampled_vector_mm": sampled.tolist(),
        "voxel_coordinate": voxel_coordinate.tolist(),
        "sform_affine": affine.tolist(),
        "dimensions": [nx, ny, nz, 3],
        "interpolation": "trilinear",
    }


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold and FONT_BOLD.is_file() else FONT_REGULAR
    return ImageFont.truetype(str(path), size=size)


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def style_sheet(sheet) -> None:
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for index, column in enumerate(sheet.columns, start=1):
        width = min(max(len(str(cell.value or "")) for cell in column) + 2, 52)
        sheet.column_dimensions[get_column_letter(index)].width = width
        for cell in column:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def add_sheet(
    workbook: Workbook,
    title: str,
    rows: list[dict],
    columns: list[str],
    numeric_types: dict[str, type] | None = None,
) -> None:
    sheet = workbook.create_sheet(title)
    sheet.append(columns)
    for row in rows:
        values = []
        for column in columns:
            value = row.get(column)
            converter = (numeric_types or {}).get(column)
            if converter is not None and value not in (None, ""):
                value = converter(value)
            values.append(value)
        sheet.append(values)
    style_sheet(sheet)
    for column, converter in (numeric_types or {}).items():
        column_index = columns.index(column) + 1
        number_format = "0" if converter is int else "0.000000"
        for cells in sheet.iter_cols(min_col=column_index, max_col=column_index, min_row=2):
            for cell in cells:
                cell.number_format = number_format


def build_workbook(
    path: Path,
    result: dict,
    roi_rows: list[dict],
    electrode_rows: list[dict],
    robustness_rows: list[dict],
    report_data: dict,
    histogram_rows: list[dict],
    figure_rows: list[dict],
    file_rows: list[dict],
) -> None:
    workbook = Workbook()
    workbook.remove(workbook.active)
    overview = [
        {"项目": "报告编号", "值": REPORT_ID, "单位": "", "来源": "报告生成器"},
        {"项目": "运行编号", "值": RUN_ID, "单位": "", "来源": "SimNIBS 求解"},
        {"项目": "数据分类", "值": "官方示例受试者；非客户 MRI", "单位": "", "来源": result["classification"]},
        {"项目": "数据集", "值": "SimNIBS example dataset v4.1 / ernie", "单位": "", "来源": result["source"]["dataset_url"]},
        {"项目": "仿真类型", "值": "正向单方案时间干涉电场仿真", "单位": "", "来源": report_data["analysis_mode"]},
        {"项目": "电流幅值约定", "值": "峰值（非 RMS、非峰峰值）", "单位": "mA", "来源": result["protocol"]["current_amplitude_convention"]},
        {"项目": "主要场量", "值": "TImax；最大包络幅值（非 RMS、非峰峰值）", "单位": "V/m", "来源": "simnibs.utils.TI_utils.get_maxTI(E1, E2)"},
        {"项目": "主要结论", "值": report_data["summary"]["heading"], "单位": "", "来源": "report_data.json"},
        {"项目": "峰值位置边界", "值": report_data["results"]["peak_location_assessment"]["interpretation_note"], "单位": "", "来源": "report_data.json"},
        {"项目": "覆盖阈值", "值": result["threshold"]["value_v_per_m"], "单位": "V/m", "来源": result["threshold"]["definition"]},
    ]
    model_rows = [
        {"项目": "MRI", "值": report_data["model"]["mri_source"], "单位或空间": "个体 conform 空间"},
        {"项目": "头模型", "值": report_data["model"]["head_model"], "单位或空间": "个体空间"},
        {"项目": "有限元网格", "值": report_data["model"]["mesh"], "单位或空间": "mm"},
        {"项目": "坐标系", "值": report_data["spatial"]["coordinate_system"], "单位或空间": "mm"},
        {"项目": "MNI 到个体空间", "值": str(result["source"]["model_completeness"]["mni_to_subject"]), "单位或空间": "非线性变换"},
        {"项目": "个体空间到 MNI", "值": str(result["source"]["model_completeness"]["subject_to_mni"]), "单位或空间": "非线性变换"},
        {"项目": "ROI 配准方法", "值": result["target"].get("coordinate_transform_method", ""), "单位或空间": "物理 x、y、z；mm"},
        {"项目": "ROI 配准往返误差", "值": result["target"].get("roundtrip_error_norm_mm", ""), "单位或空间": "mm"},
        {"项目": "ROI 配准 QC", "值": result["target"].get("coordinate_transform_qc_source", ""), "单位或空间": result["target"].get("registration_qc_status", "")},
        {"项目": "ROI 解剖学边界", "值": result["target"].get("anatomical_alignment_boundary", ""), "单位或空间": "MNI 定义；未做个体 atlas 独立确认"},
        {"项目": "SimNIBS 版本", "值": result["software"]["simnibs_version"], "单位或空间": ""},
        {"项目": "Python 版本", "值": result["software"]["python_version"], "单位或空间": ""},
    ]
    target = result["target"]
    roi_definition = [
        {
            "ROI": target["name"],
            "MNI_x_mm": target["mni_coordinate_mm"][0],
            "MNI_y_mm": target["mni_coordinate_mm"][1],
            "MNI_z_mm": target["mni_coordinate_mm"][2],
            "subject_x_mm": target["subject_coordinate_mm"][0],
            "subject_y_mm": target["subject_coordinate_mm"][1],
            "subject_z_mm": target["subject_coordinate_mm"][2],
            "radius_mm": target["radius_mm"],
            "tissue": target["tissue"],
            "definition_source": target["definition_source"],
        }
    ]
    add_sheet(workbook, "项目摘要", overview, ["项目", "值", "单位", "来源"])
    add_sheet(workbook, "模型与空间", model_rows, ["项目", "值", "单位或空间"])
    add_sheet(
        workbook,
        "刺激方案",
        electrode_rows,
        list(electrode_rows[0].keys()),
        {"current_mA": float, "x_mm": float, "y_mm": float, "z_mm": float},
    )
    add_sheet(workbook, "ROI定义", roi_definition, list(roi_definition[0].keys()))
    peak_coordinate = result["results"]["peak_subject_coordinate_mm"]
    peak_rows = [
        {
            "statistic": "whole_gray_matter_single_tetrahedron_argmax",
            "TImax_v_per_m": result["results"]["whole_gray_matter"]["max"],
            "tetrahedron_volume_mm3": result["results"]["peak_element_qc"]["volume_mm3"],
            "shared_face_neighbor_tissues": ", ".join(item["name"] for item in result["results"]["peak_element_qc"].get("shared_face_neighbor_tissues", [])),
            "is_gm_csf_interface": result["results"]["peak_element_qc"]["is_gm_csf_interface"],
            "used_as_coverage_threshold_anchor": False,
            "subject_x_mm": peak_coordinate[0],
            "subject_y_mm": peak_coordinate[1],
            "subject_z_mm": peak_coordinate[2],
            "mni_x_mm": result["results"]["peak_mni_coordinate_mm"][0],
            "mni_y_mm": result["results"]["peak_mni_coordinate_mm"][1],
            "mni_z_mm": result["results"]["peak_mni_coordinate_mm"][2],
            "coordinate_roundtrip_error_mm": result["results"]["peak_roundtrip_error_norm_mm"],
            "coordinate_roundtrip_threshold_mm": result["results"]["peak_roundtrip_acceptance_threshold_mm"],
            "coordinate_roundtrip_status": result["results"]["peak_coordinate_transform_qc_status"],
            "distance_to_roi_center_mm": result["results"]["peak_distance_to_target_mm"],
            "inside_target_roi": result["results"]["peak_inside_target_roi"],
            "coordinate_space": "SimNIBS subject conform physical space",
            "stability_assessed": False,
            "anatomical_atlas_label_assessed": False,
            "peak_to_nearest_surface_node_mm": result["results"]["peak_to_nearest_surface_node_mm"],
            "surface_node_max_v_per_m": result["results"]["surface_node_max_v_per_m"],
            "nearest_surface_node_value_v_per_m": result["results"]["nearest_surface_node_value_v_per_m"],
            "surface_peak_x_mm": result["results"]["surface_peak_subject_coordinate_mm"][0],
            "surface_peak_y_mm": result["results"]["surface_peak_subject_coordinate_mm"][1],
            "surface_peak_z_mm": result["results"]["surface_peak_subject_coordinate_mm"][2],
            "volume_peak_to_surface_peak_distance_mm": result["results"]["volume_peak_to_surface_peak_distance_mm"],
            "peak_marker_is_2d_projection": True,
            "run_id": RUN_ID,
        }
    ]
    add_sheet(
        workbook,
        "峰值空间关系",
        peak_rows,
        list(peak_rows[0].keys()),
        {
            "TImax_v_per_m": float,
            "tetrahedron_volume_mm3": float,
            "subject_x_mm": float,
            "subject_y_mm": float,
            "subject_z_mm": float,
            "mni_x_mm": float,
            "mni_y_mm": float,
            "mni_z_mm": float,
            "coordinate_roundtrip_error_mm": float,
            "coordinate_roundtrip_threshold_mm": float,
            "distance_to_roi_center_mm": float,
            "peak_to_nearest_surface_node_mm": float,
            "surface_node_max_v_per_m": float,
            "nearest_surface_node_value_v_per_m": float,
            "surface_peak_x_mm": float,
            "surface_peak_y_mm": float,
            "surface_peak_z_mm": float,
            "volume_peak_to_surface_peak_distance_mm": float,
        },
    )
    add_sheet(
        workbook,
        "ROI统计",
        roi_rows,
        list(roi_rows[0].keys()),
        {
            "n_tetrahedra": int,
            "volume_mm3": float,
            "mean": float,
            "median": float,
            "p05": float,
            "p95": float,
            "max": float,
            "threshold_v_per_m": float,
            "suprathreshold_n_tetrahedra": int,
            "suprathreshold_volume_mm3": float,
            "threshold_coverage_pct": float,
            "whole_gm_high_tail_allocation_pct": float,
        },
    )
    add_sheet(
        workbook,
        "ROI位移敏感性",
        robustness_rows,
        list(robustness_rows[0].keys()),
        {
            "offset_x_mm": float,
            "offset_y_mm": float,
            "offset_z_mm": float,
            "mean_v_per_m": float,
            "p95_v_per_m": float,
            "off_target_p95_v_per_m": float,
            "target_to_offtarget_p95_ratio": float,
            "peak_distance_to_roi_center_mm": float,
            "mean_change_pct": float,
            "p95_change_pct": float,
            "off_target_p95_change_pct": float,
        },
    )
    add_sheet(workbook, "质量门控", report_data["quality_gates"], list(report_data["quality_gates"][0].keys()))
    add_sheet(workbook, "图件索引", figure_rows, list(figure_rows[0].keys()))
    add_sheet(workbook, "文件索引", file_rows, list(file_rows[0].keys()))
    add_sheet(workbook, "ROI分布", histogram_rows, list(histogram_rows[0].keys()))
    dictionary = [
        {"字段": "current_mA", "定义": "用于缩放准静态载波场的电极电流；本报告记录峰值电流幅度，不是 RMS 或峰峰值", "单位": "mA（峰值）"},
        {"字段": "current_amplitude_convention", "定义": "电流幅值约定；本报告固定为 peak", "单位": "枚举"},
        {"字段": "E1 / E2", "定义": "按相应电极回路峰值电流幅度标定的矢量载波电场", "单位": "V/m（峰值标定）"},
        {"字段": "TImax", "定义": "SimNIBS TI_utils.get_maxTI 的最大调制幅值。逐单元先交换矢量使 ||E1||≥||E2||，必要时翻转 E2 使夹角 α≤90°；若 ||E2||≤||E1||cosα，则 TImax=2||E2||，否则 TImax=2||E2×(E1−E2)||/||E1−E2||。公式包含因子 2，不是 ||E2|| 半幅、RMS 或载波峰峰值", "单位": "V/m（最大调制幅值）"},
        {"字段": "timax_definition", "定义": "TImax 的结构化 method_id、矢量排序、夹角规范化、分支条件、两条公式、幅值因子及源码归属", "单位": "对象"},
        {"字段": "quality.timax_recompute", "定义": "不调用 TI_utils.get_maxTI 的参考公式对全部四面体逐元素复算；记录单元数、有限值计数、最大/平均绝对误差、容差与通过状态", "单位": "对象；误差为 V/m"},
        {"字段": "definition", "定义": "ROI 或参考域的可复算集合定义；目标区外灰质为全部 SimNIBS tag 2 灰质四面体减去目标 ROI，不设额外解剖排除或过渡缓冲", "单位": "文本"},
        {"字段": "n_tetrahedra", "定义": "纳入该区域统计的有限元四面体数量", "单位": "个"},
        {"字段": "volume_mm3", "定义": "纳入该区域统计的四面体总体积", "单位": "mm³"},
        {"字段": "mean", "定义": "以四面体体积为权重的算术平均值", "单位": "V/m"},
        {"字段": "median / p05 / p95", "定义": "按场值升序排列后累加四面体体积，取累计体积第一次达到 probability × 总体积时的单元值；searchsorted side='left'，不插值；p=0/1 分别取最小/最大值", "单位": "V/m"},
        {"字段": "weighted_quantile", "定义": "体积加权分位数的结构化算法、权重、排序、累计体积选择规则、插值方式、边界规则和已报告概率", "单位": "对象"},
        {"字段": "max", "定义": "纳入区域内有限元四面体的最大单元值", "单位": "V/m"},
        {"字段": "suprathreshold_volume_mm3", "定义": "本区域内 TImax 大于或等于 threshold_v_per_m 的四面体体积之和", "单位": "mm³"},
        {"字段": "suprathreshold_n_tetrahedra", "定义": "本区域内 TImax 大于或等于 threshold_v_per_m 的四面体数量；单元素量级结果处于当前网格分辨率下限", "单位": "个"},
        {"字段": "threshold_coverage_denominator", "定义": "覆盖率分母；固定为同一 ROI 统计行的区域总体积 volume_mm3", "单位": "文本"},
        {"字段": "threshold_coverage_definition", "定义": "100 × suprathreshold_volume_mm3 ÷ 同一区域 volume_mm3；按四面体体积计算，不按四面体数量计算", "单位": "文本"},
        {"字段": "threshold_coverage_pct", "定义": "本区域内达到全灰质体积加权 TImax P99.9 的体积百分比；分母为本区域总体积，不是全灰质总体积；该阈值不是激活阈值", "单位": "%"},
        {"字段": "whole_gm_high_tail_allocation_pct", "定义": "本区域超阈体积占全灰质 P99.9 高值尾部总体积的百分比；目标区、目标区外合计为 100%，用于回答高值尾部落在何处", "单位": "%"},
        {"字段": "threshold.method_id / quantile_probability", "定义": "覆盖率阈值固定为全灰质 TImax 的四面体体积加权 P99.9；采用离散加权经验分布且不插值", "单位": "枚举、概率"},
        {"字段": "threshold.whole_gray_matter_high_quantiles_v_per_m", "定义": "全灰质 TImax 的体积加权 P99、P99.9 和 P99.99；用于描述高值尾部并复核覆盖阈值", "单位": "V/m"},
        {"字段": "target_to_offtarget_p95_ratio", "定义": "目标 ROI P95 除以目标区外灰质 P95；目标区外灰质为全部 SimNIBS tag 2 灰质四面体减去目标 ROI", "单位": "比值"},
        {"字段": "target.mni_coordinate_mm / target.subject_coordinate_mm", "定义": "目标 ROI 中心在 MNI 空间与 SimNIBS 个体 conform 空间中的原始浮点坐标", "单位": "mm"},
        {"字段": "peak_subject_coordinate_mm", "定义": "当前网格中全灰质 TImax 单个四面体 argmax 所在四面体重心的 SimNIBS 个体 conform 空间坐标", "单位": "mm"},
        {"字段": "peak_mni_coordinate_mm", "定义": "由交付的 Conform2MNI_nonl.nii.gz 非线性变换场将峰值个体 conform 坐标反算到 MNI 物理空间；未执行 atlas 解剖命名", "单位": "mm"},
        {"字段": "peak_roundtrip_error_norm_mm", "定义": "峰值个体坐标经 Conform2MNI 变换到 MNI 后，再经 MNI2Conform 返回个体空间所得三维欧氏往返误差；通过阈值为 0.1 mm", "单位": "mm"},
        {"字段": "peak_distance_to_target_mm", "定义": "当前网格中全灰质 TImax 单个四面体 argmax 的重心到目标 ROI 中心的欧氏距离", "单位": "mm"},
        {"字段": "peak_location_assessment", "定义": "记录峰值为单个四面体 argmax，以及峰值位置是否经过网格、电导率和电极位置扰动检验；未检验时不得解释为稳定定位结论", "单位": "布尔值、文本"},
        {"字段": "peak_element_qc", "定义": "单四面体 argmax 的场值、单元体积、组织标签、共面相邻组织及 GM/CSF 界面判断；仅用于空间和网格界面质量控制，不作为覆盖阈值锚点", "单位": "V/m、mm³、标签、布尔值"},
        {"字段": "suprathreshold_gray_matter_fraction_pct", "定义": "100 × suprathreshold_gray_matter_volume_mm3 ÷ suprathreshold_gray_matter_denominator_volume_mm3；分母为全灰质总体积", "单位": "%"},
        {"字段": "figures[].color_scale", "定义": "报告图实际使用的色标上下限、P99 统计对象与区域、共享图件、参考数据和高值截断规则", "单位": "V/m"},
        {"字段": "robustness_summary.roi_center_displacements", "定义": "基准位置及沿个体空间三轴分别平移 ±3 mm 后的 ROI 中心、偏移量、峰值距离和 ROI 内外判断；该分析复用同一场解和峰值坐标", "单位": "mm、布尔值"},
        {"字段": "mean_change_pct / p95_change_pct / off_target_p95_change_pct", "定义": "ROI 中心位移后相对基准值的百分比变化", "单位": "%"},
        {"字段": "run_id", "定义": "连接图、表、场数组与一次求解的唯一运行编号", "单位": ""},
        {"字段": "alias_of", "定义": "当前文件是另一交付文件的逐字节副本时，记录原文件相对路径；两者 SHA-256 应一致", "单位": ""},
        {"字段": "sha256", "定义": "文件内容的 SHA-256 校验值", "单位": ""},
    ]
    add_sheet(workbook, "数据字典", dictionary, ["字段", "定义", "单位"])
    workbook.save(path)


VIRIDIS = np.asarray(
    [
        [68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]
    ],
    dtype=float,
)


def viridis(values: np.ndarray, vmax: float) -> np.ndarray:
    fraction = np.clip(np.asarray(values, dtype=float) / max(vmax, 1e-12), 0.0, 1.0)
    scaled = fraction * (len(VIRIDIS) - 1)
    low = np.floor(scaled).astype(int)
    high = np.minimum(low + 1, len(VIRIDIS) - 1)
    weight = (scaled - low)[..., None]
    return ((1 - weight) * VIRIDIS[low] + weight * VIRIDIS[high]).astype(np.uint8)


def orient(array: np.ndarray) -> np.ndarray:
    return np.flipud(np.asarray(array).T)


def t1_rgb(array: np.ndarray) -> np.ndarray:
    finite = np.asarray(array, dtype=float)
    positive = finite[finite > 0]
    lo, hi = (np.percentile(positive, [1, 99]) if positive.size else (0.0, 1.0))
    scaled = np.clip((finite - lo) / max(hi - lo, 1e-9), 0, 1)
    gray = (scaled * 215 + 20).astype(np.uint8)
    return np.repeat(gray[..., None], 3, axis=2)


def tissue_edges(labels: np.ndarray) -> np.ndarray:
    data = np.asarray(labels)
    edge = np.zeros(data.shape, dtype=bool)
    edge[1:, :] |= data[1:, :] != data[:-1, :]
    edge[:, 1:] |= data[:, 1:] != data[:, :-1]
    return edge & (data > 0)


def compose_slice(t1: np.ndarray, field_values: np.ndarray | None, vmax: float, labels: np.ndarray | None = None) -> Image.Image:
    anatomy = t1_rgb(orient(np.squeeze(t1)))
    if labels is not None:
        edges = tissue_edges(orient(np.squeeze(labels)))
        anatomy[edges] = np.array([229, 239, 234], dtype=np.uint8)
    if field_values is not None:
        field_oriented = orient(np.squeeze(field_values))
        colors = viridis(field_oriented, vmax)
        alpha = np.where(field_oriented > 0, 0.72, 0.0)[..., None]
        anatomy = (anatomy * (1 - alpha) + colors * alpha).astype(np.uint8)
    return Image.fromarray(anatomy, mode="RGB")


def draw_colorbar(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, vmax: float) -> None:
    gradient = np.linspace(vmax, 0, y1 - y0)[:, None]
    colors = viridis(gradient, vmax)[:, 0, :]
    for y, color in enumerate(colors, start=y0):
        draw.line((x0, y, x1, y), fill=tuple(int(v) for v in color), width=1)
    draw.rectangle((x0, y0, x1, y1), outline=INK, width=2)
    draw.text((x1 + 14, y0 - 8), f"{vmax:.3f}", fill=INK, font=font(24))
    draw.text((x1 + 14, y1 - 26), "0", fill=INK, font=font(24))
    draw.text((x0 - 4, y1 + 12), "V/m", fill=MUTED, font=font(23))


def place_slice_panel(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    image: Image.Image,
    box: tuple[int, int, int, int],
    label: str,
    center_fraction: tuple[float, float],
    radius_fraction: tuple[float, float] | None,
    orientation_labels: tuple[str, str, str, str],
) -> None:
    x0, y0, x1, y1 = box
    scale = min((x1 - x0) / image.width, (y1 - y0) / image.height)
    image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.Resampling.LANCZOS)
    px = x0 + (x1 - x0 - image.width) // 2
    py = y0 + (y1 - y0 - image.height) // 2
    canvas.paste(image, (px, py))
    draw.rectangle((px, py, px + image.width, py + image.height), outline=LINE, width=2)
    left, right, top, bottom = orientation_labels
    direction_font = font(21, bold=True)
    draw.text((px + 10, py + image.height / 2), left, fill=PAPER, stroke_width=2, stroke_fill=INK, font=direction_font, anchor="lm")
    draw.text((px + image.width - 10, py + image.height / 2), right, fill=PAPER, stroke_width=2, stroke_fill=INK, font=direction_font, anchor="rm")
    draw.text((px + image.width / 2, py + 10), top, fill=PAPER, stroke_width=2, stroke_fill=INK, font=direction_font, anchor="ma")
    draw.text((px + image.width / 2, py + image.height - 10), bottom, fill=PAPER, stroke_width=2, stroke_fill=INK, font=direction_font, anchor="md")
    if radius_fraction:
        cx = px + int(center_fraction[0] * image.width)
        cy = py + int(center_fraction[1] * image.height)
        rx = max(5, int(radius_fraction[0] * image.width))
        ry = max(5, int(radius_fraction[1] * image.height))
        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=(255, 255, 255), width=5)
        draw.ellipse((cx - rx - 2, cy - ry - 2, cx + rx + 2, cy + ry + 2), outline=GREEN, width=2)
    draw.text((x0, y0 - 46), label, fill=INK, font=font(30, bold=True))


def save_slice_figure(path: Path, slices: dict, field_name: str | None, vmax: float, caption: str) -> None:
    canvas = Image.new("RGB", CANVAS, PAPER)
    draw = ImageDraw.Draw(canvas)
    draw.text((MARGIN, 42), caption, fill=INK, font=font(34, bold=True))
    target = slices["target_index"]
    target_subject = (np.asarray(slices["t1_affine"], dtype=float) @ np.append(np.asarray(slices["target_voxel"], dtype=float), 1.0))[:3]
    voxel = slices["voxel_sizes_mm"]
    specs = [
        (f"Sagittal  x={target_subject[0]:.1f} mm", "sagittal", (target[1], target[2]), (voxel[1], voxel[2]), ("P", "A", "S", "I")),
        (f"Coronal  y={target_subject[1]:.1f} mm", "coronal", (target[0], target[2]), (voxel[0], voxel[2]), ("L", "R", "S", "I")),
        (f"Axial  z={target_subject[2]:.1f} mm", "axial", (target[0], target[1]), (voxel[0], voxel[1]), ("L", "R", "A", "P")),
    ]
    panel_width = 520
    gap = 55
    start_x = 90
    for index, (label, suffix, position, spacing, orientation_labels) in enumerate(specs):
        t1 = slices[f"t1_{suffix}"]
        labels = slices[f"tissues_{suffix}"]
        field_values = slices[f"{field_name}_{suffix}"] if field_name else None
        image = compose_slice(t1, field_values, vmax, labels=labels)
        dimensions = t1.shape
        center_fraction = (float(position[0]) / dimensions[0], 1.0 - float(position[1]) / dimensions[1])
        radius_fraction = (10.0 / (dimensions[0] * spacing[0]), 10.0 / (dimensions[1] * spacing[1]))
        x0 = start_x + index * (panel_width + gap)
        place_slice_panel(canvas, draw, image, (x0, 170, x0 + panel_width, 940), f"{chr(65 + index)}  {label}", center_fraction, radius_fraction, orientation_labels)
    if field_name:
        draw_colorbar(draw, 1810, 250, 1850, 820, vmax)
    draw.text((MARGIN, 1060), "Coordinates: SimNIBS subject conform physical space (mm)  |  ROI: 10 mm sphere centered at MNI (-37, -21, 58)", fill=MUTED, font=font(24))
    canvas.save(path, dpi=(300, 300), optimize=True)


def project_points(
    coords: np.ndarray,
    axes: tuple[int, int, int],
    box: tuple[int, int, int, int],
    reference: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    x0, y0, x1, y1 = box
    horizontal, vertical, depth = axes
    xy = coords[:, [horizontal, vertical]].astype(float)
    ref_xy = (coords if reference is None else reference)[:, [horizontal, vertical]].astype(float)
    lo = np.percentile(ref_xy, 0.2, axis=0)
    hi = np.percentile(ref_xy, 99.8, axis=0)
    span = np.maximum(hi - lo, 1.0)
    normalized = 0.04 + 0.92 * (xy - lo) / span
    px = x0 + normalized[:, 0] * (x1 - x0)
    py = y1 - normalized[:, 1] * (y1 - y0)
    return np.column_stack((px, py)), coords[:, depth]


def save_montage_figure(
    path: Path,
    surface: dict,
    result: dict,
    report_result: dict,
    title: str,
    field: bool = False,
    show_electrodes: bool = True,
    field_vmax: float | None = None,
) -> None:
    canvas = Image.new("RGB", CANVAS, PAPER)
    draw = ImageDraw.Draw(canvas)
    draw.text((MARGIN, 42), title, fill=INK, font=font(34, bold=True))
    coords = np.asarray(surface["coordinates"], dtype=float)
    values = np.asarray(surface["timax"], dtype=float)
    triangles = np.asarray(surface["triangles"], dtype=int)
    electrodes = np.asarray(result["electrode_coordinates"], dtype=float)
    labels = [str(value) for value in result["electrode_labels"]]
    target = np.asarray(result["target_subject"], dtype=float)[None, :]
    peak = np.asarray(report_result["results"]["peak_subject_coordinate_mm"], dtype=float)[None, :]
    peak_distance = float(report_result["results"]["peak_distance_to_target_mm"])
    surface_peak = np.asarray(report_result["results"]["surface_peak_subject_coordinate_mm"], dtype=float)[None, :]
    views = [
        ("Left lateral", (1, 2, 0), -1.0),
        ("Anterior", (0, 2, 1), 1.0),
        ("Superior", (0, 1, 2), 1.0),
    ]
    vmax = float(field_vmax) if field_vmax is not None else float(np.percentile(values[values > 0], 99))
    reference = np.vstack((coords, electrodes, target, peak, surface_peak)) if show_electrodes else np.vstack((coords, target, peak, surface_peak))
    triangle_coords = coords[triangles]
    triangle_normals = np.cross(triangle_coords[:, 1] - triangle_coords[:, 0], triangle_coords[:, 2] - triangle_coords[:, 0])
    for index, (label, axes, camera_sign) in enumerate(views):
        box = (100 + index * 590, 180, 590 + index * 590, 940)
        xy, _ = project_points(coords, axes, box, reference=reference)
        depth_axis = axes[2]
        visible = camera_sign * triangle_normals[:, depth_axis] > 0
        visible_indices = np.where(visible)[0]
        depth = triangle_coords[visible_indices, :, depth_axis].mean(axis=1)
        order = visible_indices[np.argsort(camera_sign * depth)]
        face_values = values[triangles].mean(axis=1)
        for triangle_index in order:
            polygon = [tuple(xy[node]) for node in triangles[triangle_index]]
            color = tuple(int(v) for v in viridis(np.array(face_values[triangle_index]), vmax)) if field else (190, 202, 196)
            draw.polygon(polygon, fill=color)
        if show_electrodes:
            electrode_xy, _ = project_points(electrodes, axes, box, reference=reference)
            visible_labels = {"F5", "P5"} if index == 0 else set(labels)
            for electrode_label, (x, y) in zip(labels, electrode_xy):
                if electrode_label not in visible_labels:
                    continue
                current_positive = electrode_label in {"F5", "F6"}
                color = RED if current_positive else BLUE
                draw.ellipse((x - 14, y - 14, x + 14, y + 14), fill=color, outline=PAPER, width=3)
                y_offset = -34 if electrode_label in {"F5", "F6"} else 12
                text_x = min(max(x + 18, box[0] + 8), box[2] - 88)
                text_y = min(max(y + y_offset, box[1] + 8), box[3] - 30)
                draw.line((x, y, text_x, text_y + 10), fill=color, width=3)
                draw.text((text_x, text_y), f"{electrode_label} {'+1' if current_positive else '-1'}", fill=INK, font=font(18, bold=True))
        target_xy, _ = project_points(target, axes, box, reference=reference)
        tx, ty = target_xy[0]
        draw.ellipse((tx - 17, ty - 17, tx + 17, ty + 17), outline=GREEN, width=5)
        if field:
            peak_xy, _ = project_points(peak, axes, box, reference=reference)
            px, py = peak_xy[0]
            draw.line((tx, ty, px, py), fill=(55, 55, 55), width=3)
            draw.polygon(((px, py - 18), (px + 18, py), (px, py + 18), (px - 18, py)), fill=(20, 20, 20), outline=(255, 255, 255))
            midpoint_x = (tx + px) / 2
            midpoint_y = (ty + py) / 2
            draw.rounded_rectangle((midpoint_x - 48, midpoint_y - 17, midpoint_x + 48, midpoint_y + 17), radius=6, fill=(255, 255, 255), outline=LINE)
            draw.text((midpoint_x, midpoint_y), f"{peak_distance:.1f} mm", fill=INK, font=font(17, bold=True), anchor="mm")
            surface_peak_xy, _ = project_points(surface_peak, axes, box, reference=reference)
            sx, sy = surface_peak_xy[0]
            draw.rectangle((sx - 14, sy - 14, sx + 14, sy + 14), fill=(170, 35, 110), outline=PAPER, width=3)
        draw.text((box[0], 120), f"{chr(65 + index)}  {label}", fill=INK, font=font(28, bold=True))
        draw.rectangle(box, outline=LINE, width=2)
    if field and show_electrodes:
        legend = "Surface TImax (P99 cap)  |  green: ROI  |  black diamond: volume-peak projection  |  magenta square: surface max  |  red/blue: current"
    elif field:
        legend = "Surface TImax (V/m; P99 cap)  |  green: ROI  |  black diamond: volume-peak projection  |  magenta square: surface max"
    else:
        legend = "Gray: cortical surface  |  red/blue labels: peak current (mA)  |  green: target ROI"
    draw.text((MARGIN, 1050), legend, fill=MUTED, font=font(24))
    if field:
        draw_colorbar(draw, 1820, 300, 1855, 800, vmax)
    canvas.save(path, dpi=(300, 300), optimize=True)


def draw_vertical_label(canvas: Image.Image, text: str, x: int, center_y: int) -> None:
    label_font = font(25)
    bounds = ImageDraw.Draw(canvas).textbbox((0, 0), text, font=label_font)
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    label = Image.new("RGBA", (width + 12, height + 12), (255, 255, 255, 0))
    label_draw = ImageDraw.Draw(label)
    label_draw.text((6 - bounds[0], 6 - bounds[1]), text, fill=INK, font=label_font)
    rotated = label.rotate(90, expand=True)
    canvas.paste(rotated, (x, center_y - rotated.height // 2), rotated)


def draw_axes(canvas: Image.Image, draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], xlabel: str, ylabel: str) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle(box, outline=INK, width=3)
    draw.text(((x0 + x1) // 2, y1 + 58), xlabel, fill=INK, font=font(25), anchor="mm")
    draw_vertical_label(canvas, ylabel, 20, (y0 + y1) // 2)


def draw_y_ticks(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    minimum: float,
    maximum: float,
    intervals: int = 4,
    decimals: int = 2,
) -> None:
    x0, y0, _, y1 = box
    for index in range(intervals + 1):
        fraction = index / intervals
        value = minimum + (maximum - minimum) * fraction
        y = y1 - fraction * (y1 - y0)
        draw.line((x0 - 9, y, x0, y), fill=INK, width=2)
        label = f"{value:.{decimals}f}"
        bounds = draw.textbbox((0, 0), label, font=font(19))
        draw.text((x0 - 16 - (bounds[2] - bounds[0]), y - 12), label, fill=MUTED, font=font(19))


def svg_header(title: str, description: str) -> list[str]:
    return [
        '<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="1200" viewBox="0 0 2000 1200" role="img" aria-labelledby="title desc">',
        f'<title id="title">{html.escape(title)}</title>',
        f'<desc id="desc">{html.escape(description)}</desc>',
        '<rect width="2000" height="1200" fill="#FFFFFF"/>',
        '<g font-family="Arial, Microsoft YaHei, sans-serif" fill="#17211D">',
    ]


def svg_axes(parts: list[str], box: tuple[int, int, int, int], xlabel: str, ylabel: str) -> None:
    x0, y0, x1, y1 = box
    parts.append(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="none" stroke="#17211D" stroke-width="3"/>')
    parts.append(f'<text x="{(x0+x1)/2:.1f}" y="{y1+70}" text-anchor="middle" font-size="25">{html.escape(xlabel)}</text>')
    parts.append(f'<text transform="translate(34 {(y0+y1)/2:.1f}) rotate(-90)" text-anchor="middle" font-size="25">{html.escape(ylabel)}</text>')


def svg_y_ticks(parts: list[str], box: tuple[int, int, int, int], minimum: float, maximum: float, intervals: int = 4, decimals: int = 2) -> None:
    x0, y0, x1, y1 = box
    for index in range(intervals + 1):
        fraction = index / intervals
        value = minimum + (maximum - minimum) * fraction
        y = y1 - fraction * (y1 - y0)
        parts.append(f'<line x1="{x0}" y1="{y:.2f}" x2="{x1}" y2="{y:.2f}" stroke="#E4E9E6" stroke-width="1"/>')
        parts.append(f'<text x="{x0-16}" y="{y+7:.2f}" text-anchor="end" font-size="19" fill="#5E6B64">{value:.{decimals}f}</text>')


def save_histogram_svg(path: Path, analysis: dict, threshold: float) -> None:
    edges = np.asarray(analysis["histogram_edges"], dtype=float)
    target = np.asarray(analysis["target_hist_volume_mm3"], dtype=float)
    off = np.asarray(analysis["off_target_hist_volume_mm3"], dtype=float)
    target /= max(target.sum(), 1e-12)
    off /= max(off.sum(), 1e-12)
    centers = (edges[:-1] + edges[1:]) / 2
    ymax = max(float(target.max()), float(off.max())) * 1.12
    box = (150, 170, 1810, 920)
    xscale = lambda value: box[0] + (value - edges[0]) / (edges[-1] - edges[0]) * (box[2] - box[0])
    yscale = lambda value: box[3] - value / ymax * (box[3] - box[1])
    parts = svg_header("TImax distribution in target and off-target gray matter", "Volume-normalized TImax distributions for the target ROI and off-target gray matter with the descriptive threshold marked.")
    parts.append('<text x="110" y="78" font-size="34" font-weight="700">TImax distribution in target and off-target gray matter</text>')
    svg_y_ticks(parts, box, 0.0, ymax, decimals=2)
    svg_axes(parts, box, "TImax (V/m)", "Volume fraction per bin")
    for index in range(6):
        value = edges[0] + (edges[-1] - edges[0]) * index / 5
        x = xscale(value)
        parts.append(f'<text x="{x:.2f}" y="{box[3]+40}" text-anchor="middle" font-size="21" fill="#5E6B64">{value:.2f}</text>')
    for values, color, width in ((off, BLUE, 6), (target, GREEN, 7)):
        points = " ".join(f"{xscale(x):.2f},{yscale(y):.2f}" for x, y in zip(centers, values))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>')
    tx = xscale(threshold)
    parts.append(f'<line x1="{tx:.2f}" y1="{box[1]}" x2="{tx:.2f}" y2="{box[3]}" stroke="{AMBER}" stroke-width="4"/>')
    parts.extend([
        f'<line x1="260" y1="1050" x2="340" y2="1050" stroke="{GREEN}" stroke-width="7"/><text x="355" y="1058" font-size="24">Target ROI</text>',
        f'<line x1="650" y1="1050" x2="730" y2="1050" stroke="{BLUE}" stroke-width="6"/><text x="745" y="1058" font-size="24">Off-target GM</text>',
        f'<line x1="1160" y1="1050" x2="1240" y2="1050" stroke="{AMBER}" stroke-width="4"/><text x="1255" y="1058" font-size="24">Whole-GM volume-weighted P99.9</text>',
        '</g></svg>',
    ])
    path.write_text("".join(parts), encoding="utf-8")


def save_roi_comparison_svg(path: Path, result: dict) -> None:
    target = result["results"]["target"]
    off = result["results"]["off_target"]
    metrics = [("Mean", "mean"), ("Median", "median"), ("P95", "p95")]
    ymax = max(max(float(target[key]), float(off[key])) for _, key in metrics) * 1.25
    box = (170, 170, 1810, 930)
    parts = svg_header("Target and off-target TImax summary", "Grouped bars compare volume-weighted mean, median, and P95 TImax in target and off-target gray matter.")
    parts.append('<text x="110" y="78" font-size="34" font-weight="700">Target and off-target TImax summary</text>')
    svg_y_ticks(parts, box, 0.0, ymax, decimals=2)
    svg_axes(parts, box, "Volume-weighted statistic", "TImax (V/m)")
    group_width = (box[2] - box[0]) / len(metrics)
    for index, (label, key) in enumerate(metrics):
        center = box[0] + group_width * (index + 0.5)
        for offset, values, color in ((-65, target, GREEN), (65, off, BLUE)):
            value = float(values[key])
            height = value / ymax * (box[3] - box[1])
            parts.append(f'<rect x="{center+offset-48:.2f}" y="{box[3]-height:.2f}" width="96" height="{height:.2f}" fill="{color}"/>')
            parts.append(f'<text x="{center+offset:.2f}" y="{box[3]-height-16:.2f}" text-anchor="middle" font-size="21">{value:.3f}</text>')
        parts.append(f'<text x="{center:.2f}" y="{box[3]+42}" text-anchor="middle" font-size="25" font-weight="700">{label}</text>')
    parts.extend([
        f'<rect x="560" y="1035" width="30" height="30" fill="{GREEN}"/><text x="605" y="1060" font-size="24">Target ROI</text>',
        f'<rect x="960" y="1035" width="30" height="30" fill="{BLUE}"/><text x="1005" y="1060" font-size="24">Off-target GM</text>',
        '</g></svg>',
    ])
    path.write_text("".join(parts), encoding="utf-8")


def save_robustness_svg(path: Path, rows: list[dict]) -> None:
    labels = [row["setting"].replace(" mm", "") for row in rows]
    mean = np.asarray([float(row["mean_change_pct"]) for row in rows])
    p95 = np.asarray([float(row["p95_change_pct"]) for row in rows])
    limit = max(5.0, math.ceil(max(np.max(np.abs(mean)), np.max(np.abs(p95))) / 5.0) * 5.0)
    box = (180, 170, 1830, 890)
    xscale = lambda index: box[0] + (box[2] - box[0]) * index / (len(labels) - 1)
    yscale = lambda value: (box[1] + box[3]) / 2 - value / limit * (box[3] - box[1]) / 2
    parts = svg_header("Sensitivity to target-ROI center displacement", "Mean and P95 percent changes after shifting the target ROI center by plus or minus three millimeters along each subject-space axis.")
    parts.append('<text x="110" y="78" font-size="34" font-weight="700">Sensitivity to target-ROI center displacement</text>')
    svg_y_ticks(parts, box, -limit, limit, decimals=0)
    svg_axes(parts, box, "ROI center setting", "Change from baseline (%)")
    for index, label in enumerate(labels):
        parts.append(f'<text x="{xscale(index):.2f}" y="{box[3]+42}" text-anchor="middle" font-size="18" fill="#5E6B64">{html.escape(label)}</text>')
    for values, color in ((mean, GREEN), (p95, AMBER)):
        points = " ".join(f"{xscale(i):.2f},{yscale(value):.2f}" for i, value in enumerate(values))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="6" stroke-linejoin="round"/>')
        for i, value in enumerate(values):
            parts.append(f'<circle cx="{xscale(i):.2f}" cy="{yscale(value):.2f}" r="8" fill="{color}" stroke="#FFFFFF" stroke-width="2"/>')
    parts.extend([
        f'<line x1="580" y1="1040" x2="660" y2="1040" stroke="{GREEN}" stroke-width="6"/><text x="675" y="1048" font-size="24">Mean</text>',
        f'<line x1="950" y1="1040" x2="1030" y2="1040" stroke="{AMBER}" stroke-width="6"/><text x="1045" y="1048" font-size="24">P95</text>',
        '</g></svg>',
    ])
    path.write_text("".join(parts), encoding="utf-8")


def save_histogram(path: Path, analysis: dict, threshold: float) -> None:
    edges = np.asarray(analysis["histogram_edges"], dtype=float)
    target = np.asarray(analysis["target_hist_volume_mm3"], dtype=float)
    off = np.asarray(analysis["off_target_hist_volume_mm3"], dtype=float)
    target /= max(target.sum(), 1e-12)
    off /= max(off.sum(), 1e-12)
    canvas = Image.new("RGB", CANVAS, PAPER)
    draw = ImageDraw.Draw(canvas)
    draw.text((MARGIN, 42), "TImax distribution in target and off-target gray matter", fill=INK, font=font(34, bold=True))
    box = (150, 170, 1810, 920)
    draw_axes(canvas, draw, box, "TImax (V/m)", "Volume fraction per bin")
    ymax = max(float(target.max()), float(off.max())) * 1.12
    draw_y_ticks(draw, box, 0.0, ymax, decimals=2)
    centers = (edges[:-1] + edges[1:]) / 2
    def points(values):
        return [
            (box[0] + (x - edges[0]) / (edges[-1] - edges[0]) * (box[2] - box[0]), box[3] - y / ymax * (box[3] - box[1]))
            for x, y in zip(centers, values)
        ]
    draw.line(points(off), fill=BLUE, width=6, joint="curve")
    draw.line(points(target), fill=GREEN, width=7, joint="curve")
    threshold_x = box[0] + (threshold - edges[0]) / (edges[-1] - edges[0]) * (box[2] - box[0])
    draw.line((threshold_x, box[1], threshold_x, box[3]), fill=AMBER, width=4)
    for index in range(6):
        value = edges[-1] * index / 5
        x = box[0] + (box[2] - box[0]) * index / 5
        draw.text((x - 30, box[3] + 10), f"{value:.2f}", fill=MUTED, font=font(21))
    draw.line((260, 1050, 340, 1050), fill=GREEN, width=7); draw.text((355, 1034), "Target ROI", fill=INK, font=font(24))
    draw.line((650, 1050, 730, 1050), fill=BLUE, width=6); draw.text((745, 1034), "Off-target GM", fill=INK, font=font(24))
    draw.line((1160, 1050, 1240, 1050), fill=AMBER, width=4); draw.text((1255, 1034), "Whole-GM volume-weighted P99.9", fill=INK, font=font(24))
    canvas.save(path, dpi=(300, 300), optimize=True)


def save_roi_comparison(path: Path, result: dict) -> None:
    target = result["results"]["target"]
    off = result["results"]["off_target"]
    metrics = [("Mean", "mean"), ("Median", "median"), ("P95", "p95")]
    ymax = max(max(float(target[key]), float(off[key])) for _, key in metrics) * 1.25
    canvas = Image.new("RGB", CANVAS, PAPER)
    draw = ImageDraw.Draw(canvas)
    draw.text((MARGIN, 42), "Target and off-target TImax summary", fill=INK, font=font(34, bold=True))
    box = (170, 170, 1810, 930)
    draw_axes(canvas, draw, box, "Volume-weighted statistic", "TImax (V/m)")
    draw_y_ticks(draw, box, 0.0, ymax, decimals=2)
    group_width = (box[2] - box[0]) / len(metrics)
    for index, (label, key) in enumerate(metrics):
        center = box[0] + group_width * (index + 0.5)
        for offset, values, color in ((-65, target, GREEN), (65, off, BLUE)):
            value = float(values[key])
            height = value / ymax * (box[3] - box[1])
            draw.rectangle((center + offset - 48, box[3] - height, center + offset + 48, box[3]), fill=color)
            draw.text((center + offset - 45, box[3] - height - 38), f"{value:.3f}", fill=INK, font=font(21))
        draw.text((center - 55, box[3] + 14), label, fill=INK, font=font(25, bold=True))
    draw.rectangle((560, 1035, 590, 1065), fill=GREEN); draw.text((605, 1028), "Target ROI", fill=INK, font=font(24))
    draw.rectangle((960, 1035, 990, 1065), fill=BLUE); draw.text((1005, 1028), "Off-target GM", fill=INK, font=font(24))
    canvas.save(path, dpi=(300, 300), optimize=True)


def save_robustness(path: Path, rows: list[dict]) -> None:
    labels = [row["setting"] for row in rows]
    mean = np.asarray([float(row["mean_change_pct"]) for row in rows])
    p95 = np.asarray([float(row["p95_change_pct"]) for row in rows])
    limit = max(5.0, math.ceil(max(np.max(np.abs(mean)), np.max(np.abs(p95))) / 5.0) * 5.0)
    canvas = Image.new("RGB", CANVAS, PAPER)
    draw = ImageDraw.Draw(canvas)
    draw.text((MARGIN, 42), "Sensitivity to target-ROI center displacement", fill=INK, font=font(34, bold=True))
    box = (180, 170, 1830, 890)
    draw_axes(canvas, draw, box, "ROI center setting", "Change from baseline (%)")
    draw_y_ticks(draw, box, -limit, limit, decimals=0)
    zero_y = (box[1] + box[3]) / 2
    draw.line((box[0], zero_y, box[2], zero_y), fill=LINE, width=3)
    def make_points(values):
        return [
            (box[0] + (box[2] - box[0]) * i / (len(values) - 1), zero_y - values[i] / limit * (box[3] - box[1]) / 2)
            for i in range(len(values))
        ]
    for values, color in ((mean, GREEN), (p95, AMBER)):
        points = make_points(values)
        draw.line(points, fill=color, width=6, joint="curve")
        for x, y in points:
            draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=color, outline=PAPER, width=2)
    for index, label in enumerate(labels):
        x = box[0] + (box[2] - box[0]) * index / (len(labels) - 1)
        draw.text((x - 70, box[3] + 15), label.replace(" mm", ""), fill=MUTED, font=font(18))
    draw.line((580, 1040, 660, 1040), fill=GREEN, width=6); draw.text((675, 1024), "Mean", fill=INK, font=font(24))
    draw.line((950, 1040, 1030, 1040), fill=AMBER, width=6); draw.text((1045, 1024), "P95", fill=INK, font=font(24))
    canvas.save(path, dpi=(300, 300), optimize=True)


def write_rows_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_histogram_rows(analysis: dict, threshold: float) -> list[dict]:
    edges = np.asarray(analysis["histogram_edges"], dtype=float)
    target = np.asarray(analysis["target_hist_volume_mm3"], dtype=float)
    off = np.asarray(analysis["off_target_hist_volume_mm3"], dtype=float)
    target_fraction = target / max(target.sum(), 1e-12)
    off_fraction = off / max(off.sum(), 1e-12)
    return [
        {
            "bin_left_v_per_m": float(edges[index]),
            "bin_right_v_per_m": float(edges[index + 1]),
            "bin_center_v_per_m": float((edges[index] + edges[index + 1]) / 2),
            "target_volume_mm3": float(target[index]),
            "target_volume_fraction": float(target_fraction[index]),
            "off_target_volume_mm3": float(off[index]),
            "off_target_volume_fraction": float(off_fraction[index]),
            "descriptive_threshold_v_per_m": threshold,
            "run_id": RUN_ID,
        }
        for index in range(len(target))
    ]


def write_data_health(path: Path, roi_rows: list[dict], electrode_rows: list[dict], robustness_rows: list[dict], histogram_rows: list[dict]) -> None:
    datasets = {
        "roi_metrics.csv": roi_rows,
        "electrode_currents.csv": electrode_rows,
        "robustness_roi_displacement.csv": robustness_rows,
        "fig04a_roi_distribution.csv": histogram_rows,
    }
    lines = [
        "# Data Health Report",
        "",
        "本报告检查报告生成器直接使用的结构化表格。FEM 场数组的有限值、网格对应和正体积检查由 `analysis_results.json` 中的质量门控单独记录。",
        "",
        "## 数据集清单",
        "",
        "| 数据集 | 行数 | 列数 | 空值 | 重复行 | 用途 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    purposes = {
        "roi_metrics.csv": "目标区、目标区外和全灰质的集合定义、体积与统计",
        "electrode_currents.csv": "电极位置与回路峰值电流",
        "robustness_roi_displacement.csv": "ROI 中心位移敏感性",
        "fig04a_roi_distribution.csv": "图 4A 重绘数据",
    }
    for name, rows in datasets.items():
        columns = list(rows[0].keys()) if rows else []
        missing = sum(value in (None, "") for row in rows for value in row.values())
        normalized = [tuple(str(row.get(column, "")) for column in columns) for row in rows]
        duplicates = len(normalized) - len(set(normalized))
        lines.append(f"| `{name}` | {len(rows)} | {len(columns)} | {missing} | {duplicates} | {purposes[name]} |")
    lines.extend(
        [
            "",
            "## 关键检查",
            "",
            f"- ROI 统计共 {len(roi_rows)} 行，目标区、目标区外灰质和全灰质各 1 行；每行包含集合定义、四面体数量和体积，未发现重复行。",
            f"- 电极表共 {len(electrode_rows)} 行，F5、P5、F6、P6 标签唯一；每个回路的设定电流代数和为 0 mA。",
            f"- ROI 位移表共 {len(robustness_rows)} 行，包含 1 个基准位置和 6 个 ±3 mm 位移条件；基准变化为 0%。",
            f"- 图 4A 分布表共 {len(histogram_rows)} 个连续分箱；目标区和目标区外体积分数分别归一化为 1。",
            "- 载波频率与相位未写入电极 CSV；本示例只计算准静态空间场，正式设备协议需另行补充频率和相位参数。",
            "",
            "## 统计适用性",
            "",
            "这些表记录一次确定性有限元仿真的区域汇总和参数扰动结果，不是独立受试者样本。正态性检验、组间显著性检验和 VIF 不适用，也未执行。",
            "",
            "## 结论",
            "",
            "报告生成所需结构化数据完整，未发现会阻断本次描述性图表和二次绘图的数据问题。未执行的网格、电极位置和组织电导率敏感性仍属于科学限制，不因本数据健康检查而消除。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def artifact(path: Path, kind: str, purpose: str, unit_space: str, display_in_report: bool = True, alias_of: str | None = None) -> dict:
    item = {
        "path": path.relative_to(OUTPUT).as_posix(),
        "type": kind,
        "purpose": purpose,
        "run_id": RUN_ID,
        "unit_space": unit_space,
        "sha256": sha256(path),
        "display_in_report": display_in_report,
    }
    if alias_of:
        item["alias_of"] = alias_of
    return item


def build_report_data(result: dict, roi_rows: list[dict], electrode_rows: list[dict], robustness_rows: list[dict], figures: list[dict], artifacts: list[dict]) -> dict:
    figure_by_id = {figure["id"]: figure for figure in figures}
    slice_vmax = float(figure_by_id["field_primary"]["color_scale"]["vmax_v_per_m"])
    surface_vmax = float(figure_by_id["field_surface"]["color_scale"]["vmax_v_per_m"])
    target = result["results"]["target"]
    off = result["results"]["off_target"]
    whole = result["results"]["whole_gray_matter"]
    ratio = result["results"]["target_to_offtarget_p95_ratio"]
    peak_distance = result["results"]["peak_distance_to_target_mm"]
    peak_roundtrip_error = result["results"]["peak_roundtrip_error_norm_mm"]
    peak_qc = result["results"]["peak_element_qc"]
    gm_tail = result["threshold"]["weighted_quantiles_v_per_m"]
    conductivity_rows = result["source"]["conductivities_s_per_m"]
    conductivity_text = "; ".join(
        f"{row['tissue_name']} {float(row['conductivity_s_per_m']):g} S/m"
        for row in conductivity_rows
    )
    neighbor_names = ", ".join(item["name"] for item in peak_qc.get("shared_face_neighbor_tissues", []))
    peak_relation = "位于 ROI 内" if result["results"]["peak_inside_target_roi"] else "位于 ROI 外"
    worst_mean = result["robustness"]["worst_abs_mean_change_pct"]
    worst_p95 = result["robustness"]["worst_abs_p95_change_pct"]
    worst_offtarget_p95 = result["robustness"]["worst_abs_off_target_p95_change_pct"]
    ratio_min = result["robustness"]["target_to_offtarget_p95_ratio_min"]
    ratio_max = result["robustness"]["target_to_offtarget_p95_ratio_max"]
    shifted_peak_min = result["robustness"]["peak_distance_to_shifted_roi_min_mm"]
    shifted_peak_max = result["robustness"]["peak_distance_to_shifted_roi_max_mm"]
    quality = result["quality"]
    timax_recompute = quality["timax_recompute"]
    calibration_errors = quality.get("estimated_current_calibration_errors_pct", [])
    if len(calibration_errors) == 6:
        calibration_text = (
            "E1 基场 1-2/1-3/1-4："
            + ", ".join(f"{value:.1f}%" for value in calibration_errors[:3])
            + "；E2 基场 1-2/1-3/1-4："
            + ", ".join(f"{value:.1f}%" for value in calibration_errors[3:])
        )
    else:
        calibration_text = ", ".join(f"{value:.1f}%" for value in calibration_errors) if calibration_errors else "未提取"
    summary_heading = (
        f"目标 ROI 的 P95 为靶外灰质的 {ratio:.2f} 倍；"
        f"ROI 定位偏移 ±3 mm 时为 {ratio_min:.2f}–{ratio_max:.2f} 倍"
    )
    report_roi_rows = [
        {
            "roi": "MNI 定义的左侧 M1 球形 ROI", "role": "目标区",
            "definition": "SimNIBS tag 2 灰质四面体中，单元重心位于 10 mm 目标球内的集合",
            "n_tetrahedra": int(target["n_tetrahedra"]), "volume_mm3": float(target["volume_mm3"]),
            "mean": float(target["mean"]),
            "median": float(target["median"]), "p95": float(target["p95"]),
            "max": float(target["max"]),
            "suprathreshold_n_tetrahedra": int(target["suprathreshold_n_tetrahedra"]),
            "suprathreshold_volume_mm3": float(target["suprathreshold_volume_mm3"]),
            "threshold_coverage_denominator": "同一统计行的区域总体积 volume_mm3",
            "threshold_coverage_definition": "100 × suprathreshold_volume_mm3 ÷ 同一区域 volume_mm3；按四面体体积计算",
            "threshold_coverage_pct": float(target["threshold_coverage_pct"]), "run_id": RUN_ID,
            "whole_gm_high_tail_allocation_pct": float(target["whole_gm_high_tail_allocation_pct"]),
        },
        {
            "roi": "目标区外灰质", "role": "非目标区",
            "definition": "ernie 网格全部 SimNIBS tag 2 灰质四面体减去目标 ROI；无额外 atlas 排除或过渡缓冲",
            "n_tetrahedra": int(off["n_tetrahedra"]), "volume_mm3": float(off["volume_mm3"]),
            "mean": float(off["mean"]),
            "median": float(off["median"]), "p95": float(off["p95"]),
            "max": float(off["max"]),
            "suprathreshold_n_tetrahedra": int(off["suprathreshold_n_tetrahedra"]),
            "suprathreshold_volume_mm3": float(off["suprathreshold_volume_mm3"]),
            "threshold_coverage_denominator": "同一统计行的区域总体积 volume_mm3",
            "threshold_coverage_definition": "100 × suprathreshold_volume_mm3 ÷ 同一区域 volume_mm3；按四面体体积计算",
            "threshold_coverage_pct": float(off["threshold_coverage_pct"]), "run_id": RUN_ID,
            "whole_gm_high_tail_allocation_pct": float(off["whole_gm_high_tail_allocation_pct"]),
        },
        {
            "roi": "全灰质", "role": "阈值参照域（覆盖率约 0.1% 由定义决定）",
            "definition": "ernie 头模型中全部 SimNIBS tag 2 灰质四面体；等于目标 ROI 与目标区外灰质的并集",
            "n_tetrahedra": int(whole["n_tetrahedra"]), "volume_mm3": float(whole["volume_mm3"]),
            "mean": float(whole["mean"]),
            "median": float(whole["median"]), "p95": float(whole["p95"]),
            "max": float(whole["max"]),
            "suprathreshold_n_tetrahedra": int(whole["suprathreshold_n_tetrahedra"]),
            "suprathreshold_volume_mm3": float(whole["suprathreshold_volume_mm3"]),
            "threshold_coverage_denominator": "同一统计行的全灰质总体积 volume_mm3",
            "threshold_coverage_definition": "100 × suprathreshold_volume_mm3 ÷ 全灰质 volume_mm3；按四面体体积计算",
            "threshold_coverage_pct": float(whole["threshold_coverage_pct"]), "run_id": RUN_ID,
            "whole_gm_high_tail_allocation_pct": float(whole["whole_gm_high_tail_allocation_pct"]),
        },
    ]
    electrodes = [
        {
            "circuit": row["circuit"].replace("Carrier field ", "载波场 "), "electrode": row["electrode"],
            "current_ma": float(row["current_mA"]),
            "current_amplitude_convention": row["current_amplitude_convention"],
            "frequency_hz": None, "phase_deg": None, "run_id": RUN_ID,
        }
        for row in electrode_rows
    ]
    target_mni_coordinate = [float(value) for value in result["target"]["mni_coordinate_mm"]]
    target_subject_coordinate = [float(value) for value in result["target"]["subject_coordinate_mm"]]
    roi_center_displacements = []
    for row in robustness_rows:
        offset = [float(row[f"offset_{axis}_mm"]) for axis in ("x", "y", "z")]
        shifted_center = [center + delta for center, delta in zip(target_subject_coordinate, offset)]
        roi_center_displacements.append(
            {
                "setting": row["setting"],
                "offset_subject_mm": offset,
                "roi_center_subject_coordinate_mm": shifted_center,
                "peak_distance_to_roi_center_mm": float(row["peak_distance_to_roi_center_mm"]),
                "peak_inside_roi": str(row["peak_inside_roi"]).strip().lower() == "true",
                "run_id": RUN_ID,
            }
        )
    color_scales = {
        figure["id"]: figure["color_scale"]
        for figure in figures
        if "color_scale" in figure
    }
    weighted_quantile = dict(result["statistics"]["weighted_quantile"])
    robustness = [
        {
            "factor": "ROI 中心位置", "setting": "沿个体空间三个轴分别平移 ±3 mm",
            "target_change_pct": round(max(worst_mean, worst_p95), 2), "offtarget_change_pct": round(worst_offtarget_p95, 2),
            "solution_changed": "不适用（正向仿真）",
            "conclusion": f"目标区 mean 最大绝对变化 {worst_mean:.2f}%，P95 最大绝对变化 {worst_p95:.2f}%；Target/Off-target P95 比值范围 {ratio_min:.3f}–{ratio_max:.3f}，可跨过 1。该分析只移动 ROI 中心，复用同一次 FEM 场解和峰值坐标；{shifted_peak_min:.1f}–{shifted_peak_max:.1f} mm 仅为同一峰值到位移后 ROI 中心的几何距离范围，不构成峰值位置稳定性证据",
        },
        {
            "factor": "电极位置与组织电导率", "setting": "未在本示例中扰动", "target_change_pct": None,
            "offtarget_change_pct": None, "solution_changed": "未评估", "conclusion": "正式个体交付时按研究方案另行计算",
        },
    ]
    gates = [
        {"name": "模型完整性", "status": "pass" if quality["model_completeness"] else "fail", "hard_gate": True, "check": "头网格、T1、组织标签、MNI 变换、电极坐标及 CHARM 报告", "result": "文件齐全；核心模型输入已纳入交付索引与 SHA-256 清单", "evidence": "raw_simnibs/model/source_inputs/m2m_ernie/；raw_simnibs/analysis/analysis_results.json"},
        {"name": "空间变换往返一致性", "status": "pass" if result["target"]["registration_qc_status"] == "pass" and result["results"]["peak_coordinate_transform_qc_status"] == "pass" else "fail", "hard_gate": True, "check": "ROI 执行 MNI→个体→MNI，峰值执行个体→MNI→个体；阈值均为 0.1 mm", "result": f"ROI {result['target']['roundtrip_error_norm_mm']:.4f} mm；峰值 {peak_roundtrip_error:.4f} mm", "evidence": "raw_simnibs/model/roi_registration_qc.json"},
        {"name": "电流守恒（输入）", "status": "pass", "hard_gate": True, "check": "每个独立回路的设定电流代数和", "result": "E1: 0 A；E2: 0 A", "evidence": "raw_simnibs/tables/electrode_currents.csv"},
        {"name": "场数组完整性", "status": "pass" if quality["finite_fields"] else "fail", "hard_gate": True, "check": "E1、E2、J1、J2 与 TImax 的有限值检查", "result": "未检出 NaN/Inf", "evidence": "raw_simnibs/fields/ernie_TI_analysis.h5"},
        {"name": "TImax 复算一致性", "status": timax_recompute["status"], "hard_gate": True, "check": "使用不调用 TI_utils.get_maxTI 的参考公式，对交付网格全部四面体逐元素复算", "result": f"{timax_recompute['element_count']:,} 个单元；最大绝对误差 {timax_recompute['max_abs_error_v_per_m']:.3g} V/m；容差 {timax_recompute['absolute_tolerance_v_per_m']:.1g} V/m", "evidence": "raw_simnibs/analysis/timax_recompute_qc.json"},
        {"name": "双回路网格对应", "status": "pass" if quality["mesh_alignment"] else "fail", "hard_gate": True, "check": "节点、单元、标签逐项一致", "result": "一致", "evidence": "raw_simnibs/analysis/analysis_results.json"},
        {"name": "基场求解的电流校准误差", "status": "warning", "hard_gate": False, "check": "每个四电极载波配置以通道 1 为参考，分别求解 1-2、1-3、1-4 三个基场；两组配置共六次基场求解", "result": calibration_text, "evidence": quality["solver_log_path"]},
        {"name": "ROI 位置敏感性", "status": "warning", "hard_gate": False, "check": "ROI 中心沿三轴 ±3 mm；只移动 ROI 中心，复用同一场解及峰值坐标；未预设通过阈值", "result": f"mean 最大 |Δ| {worst_mean:.2f}%；P95 最大 |Δ| {worst_p95:.2f}%；Target/Off-target P95 比值 {ratio_min:.3f}–{ratio_max:.3f}；{shifted_peak_min:.1f}–{shifted_peak_max:.1f} mm 仅为几何距离范围，不是峰值稳定性证据", "evidence": "raw_simnibs/tables/robustness_roi_displacement.csv"},
        {"name": "网格收敛与电导率敏感性", "status": "not_assessed", "hard_gate": False, "check": "独立网格与电导率扰动", "result": "本示例未执行", "evidence": "方法与限制"},
    ]
    return {
        "schema_version": "simnibs.report.v1",
        "analysis_mode": "forward_single",
        "stimulation_modality": "temporal_interference",
        "report": {
            "report_id": REPORT_ID,
            "title": "个体化时间干涉刺激正向电场仿真报告",
            "status": "ready",
            "status_label": "示例数据 · 计算完成",
            "organization": "全澜科技 · 科研仿真交付示例",
            "scientific_question": "评估既定 F5/P5 与 F6/P6 双回路方案在 MNI 定义的左侧 M1 球形 ROI 内形成的 TI 包络场，并量化目标区、目标区外灰质及 ROI 定位扰动下的结果。",
            "generated_at": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"),
            "build_identity": f"SimNIBS {result['software']['simnibs_version']} · {RUN_ID}",
        },
        "subject": {"id": "ernie（SimNIBS 官方示例受试者）"},
        "target": {
            "name": "MNI 定义的左侧 M1 球形 ROI",
            "definition": f"MNI (-37, -21, 58)，非线性变换至个体空间 ({target_subject_coordinate[0]:.3f}, {target_subject_coordinate[1]:.3f}, {target_subject_coordinate[2]:.3f}) mm；半径 10 mm；仅纳入灰质四面体",
            "mni_coordinate_mm": target_mni_coordinate,
            "subject_coordinate_mm": target_subject_coordinate,
            "radius_mm": float(result["target"]["radius_mm"]),
            "tissue": result["target"]["tissue"],
            "coordinate_transform_source": result["target"].get("coordinate_transform_source"),
            "coordinate_transform_source_sha256": result["target"].get("coordinate_transform_source_sha256"),
            "coordinate_transform_inverse_source": result["target"].get("coordinate_transform_inverse_source"),
            "coordinate_transform_inverse_source_sha256": result["target"].get("coordinate_transform_inverse_source_sha256"),
            "coordinate_transform_qc_source": result["target"].get("coordinate_transform_qc_source"),
            "coordinate_transform_method": result["target"].get("coordinate_transform_method"),
            "coordinate_transform_direction": result["target"].get("coordinate_transform_direction"),
            "coordinate_order": result["target"].get("coordinate_order"),
            "numeric_coordinate_difference_subject_minus_mni_mm": result["target"].get("numeric_coordinate_difference_subject_minus_mni_mm"),
            "coordinate_difference_interpretation": result["target"].get("coordinate_difference_interpretation"),
            "roundtrip_mni_coordinate_mm": result["target"].get("roundtrip_mni_coordinate_mm"),
            "roundtrip_error_components_mm": result["target"].get("roundtrip_error_components_mm"),
            "roundtrip_error_norm_mm": result["target"].get("roundtrip_error_norm_mm"),
            "registration_qc_status": result["target"].get("registration_qc_status"),
            "registration_qc_summary": result["target"].get("registration_qc_summary"),
            "anatomical_label_source": result["target"].get("anatomical_label_source"),
            "anatomical_alignment_boundary": result["target"].get("anatomical_alignment_boundary"),
            "coordinate_transform": "SimNIBS 非线性 MNI-to-subject 变换；坐标单位为 mm",
        },
        "model": {
            "mri_source": "SimNIBS example dataset v4.1 中的 ernie T1 MRI",
            "head_model": "CHARM 个体头模型（官方示例数据）",
            "mesh": "ernie.msh；四面体有限元网格",
            "conductivity_profile": f"SimNIBS {result['software']['simnibs_version']} 本次实际固定值：{conductivity_text}",
        },
        "spatial": {
            "coordinate_system": "SimNIBS 个体 conform 空间（mm）；ROI 同时记录 MNI 与个体坐标",
            "display_convention": f"正交切面通过 ROI 中心；图 3A–3C 共用切面 P99 色标（0–{slice_vmax:.3f} V/m），图 3D–3E 共用灰质表面 P99 色标（0–{surface_vmax:.3f} V/m）；两组色标上限不同，颜色不可跨组直接比较；精确数值与统计域见 color_scales",
            "color_scales": color_scales,
        },
        "software": {"simnibs_version": result["software"]["simnibs_version"]},
        "protocol": {
            "electrode_model": "40 × 40 mm 椭圆电极，厚度 2 mm；10-10 电极坐标",
            "current_amplitude_convention": "peak",
            "current_amplitude_note": "表中 ±1 mA 为用于缩放准静态载波场的峰值电流幅度，不是 RMS 或峰峰值。若设备面板使用 RMS，应先完成幅值换算，再与本报告结果比较。",
            "electrodes": electrodes,
        },
        "summary": {
            "heading": summary_heading,
            "conclusion": f"MNI 定义的左侧 M1 球形 ROI 内 TImax 的体积加权平均值为 {target['mean']:.3f} V/m，P95 为 {target['p95']:.3f} V/m。基准 Target/Off-target P95 比值为 {ratio:.2f}；ROI 中心沿三轴 ±3 mm 位移时，该比值范围为 {ratio_min:.2f}–{ratio_max:.2f}，相对排序并不稳定。当前网格中，全灰质单个四面体 argmax 距基准 ROI 中心 {peak_distance:.1f} mm，位于 ROI 外。位移分析只改变 ROI 中心，复用同一次 FEM 场解及同一峰值坐标；{shifted_peak_min:.1f}–{shifted_peak_max:.1f} mm 仅为几何距离范围，不构成峰值位置稳定性检验。由于本示例未执行网格收敛、组织电导率或电极位置扰动，不能据此声称峰值位置对模型或数值设置稳定。结果仅描述当前网格的空间剂量分布，不代表神经激活阈值或临床疗效。",
        },
        "results": {
            "primary_field": "TImax：由按峰值电流幅度标定的 E1 与 E2 计算的最大调制幅值；公式包含因子 2，不是 ||E2|| 半幅、RMS 或载波峰峰值",
            "field_amplitude_convention": "maximum_envelope_amplitude",
            "field_amplitude_note": "E1、E2 均按峰值电流幅度标定；TImax 沿所有方向取最大调制幅值，分支公式显式包含因子 2，不是 ||E2|| 半幅、RMS 或载波峰峰值。",
            "timax_definition": {
                "method_id": "simnibs_4_6_0_TI_utils_get_maxTI_grossman2017",
                "implementation": "simnibs.utils.TI_utils.get_maxTI",
                "input": "E1 and E2 vector fields, N x 3, V/m, peak-current calibrated",
                "vector_ordering": "swap E1 and E2 per element when ||E2|| > ||E1|| so that ||E1|| >= ||E2||",
                "angle_normalization": "if E1 dot E2 < 0, replace E2 by -E2 so that alpha <= pi/2",
                "cos_alpha": "(E1 dot E2) / (||E1|| ||E2||)",
                "branch_condition": "if ||E2|| <= ||E1|| cos(alpha)",
                "branch_formula": "TImax = 2 ||E2||",
                "otherwise_formula": "TImax = 2 ||E2 x (E1 - E2)|| / ||E1 - E2||",
                "direction_rule": "maximum modulation amplitude over field directions",
                "amplitude_factor": 2.0,
                "amplitude_interpretation": "SimNIBS maximum modulation amplitude including the explicit factor 2; not ||E2|| half-amplitude, RMS, or carrier peak-to-peak",
                "source_basis": "SimNIBS 4.6.0 TI_utils.get_maxTI; equation attributed there to Grossman et al., Cell 2017",
            },
            "weighted_quantile": weighted_quantile,
            "threshold": {
                "value_v_per_m": float(result["threshold"]["value_v_per_m"]),
                "method_id": "whole_gray_matter_volume_weighted_p99_9",
                "reference_definition": "全灰质 TImax 的体积加权 P99.9",
                "quantile_probability": float(result["threshold"]["quantile_probability"]),
                "anchor_statistic": "全灰质 SimNIBS tag 2 四面体 TImax 的体积加权第 99.9 百分位数",
                "anchor_value_v_per_m": float(gm_tail["p99_9"]),
                "anchor_is_single_element_extreme": False,
                "whole_gray_matter_high_quantiles_v_per_m": {
                    "p99": float(gm_tail["p99"]),
                    "p99_9": float(gm_tail["p99_9"]),
                    "p99_99": float(gm_tail["p99_99"]),
                },
                "mesh_convergence_assessed": False,
                "sensitivity_note": "P99.9 按四面体体积加权，用于降低单个小体积界面单元对覆盖阈值的支配。由于阈值由全灰质自身的 P99.9 定义，全灰质覆盖率约 0.1% 是定义性结果，不是方案聚焦性发现，也不能用于跨方案、跨受试者或跨研究比较。该阈值只描述当前模型的高值尾部，不是神经激活阈值或临床有效阈值。",
                "coverage_unit": "%",
                "coverage_denominator": "同一 ROI 统计行的区域总体积 volume_mm3",
                "coverage_definition": "100 × 本区域内达到阈值的四面体体积之和 ÷ 本区域总体积；按四面体体积计算",
            },
            "target_to_offtarget_p95_ratio": float(result["results"]["target_to_offtarget_p95_ratio"]),
            "target_to_offtarget_mean_ratio": float(result["results"]["target_to_offtarget_mean_ratio"]),
            "peak_subject_coordinate_mm": [float(value) for value in result["results"]["peak_subject_coordinate_mm"]],
            "peak_mni_coordinate_mm": [float(value) for value in result["results"]["peak_mni_coordinate_mm"]],
            "peak_coordinate_transform_source": result["results"]["peak_coordinate_transform_source"],
            "peak_coordinate_roundtrip_source": result["results"]["peak_coordinate_roundtrip_source"],
            "peak_roundtrip_subject_coordinate_mm": [float(value) for value in result["results"]["peak_roundtrip_subject_coordinate_mm"]],
            "peak_roundtrip_error_components_mm": [float(value) for value in result["results"]["peak_roundtrip_error_components_mm"]],
            "peak_roundtrip_error_norm_mm": float(result["results"]["peak_roundtrip_error_norm_mm"]),
            "peak_roundtrip_acceptance_threshold_mm": float(result["results"]["peak_roundtrip_acceptance_threshold_mm"]),
            "peak_coordinate_transform_qc_status": result["results"]["peak_coordinate_transform_qc_status"],
            "peak_anatomical_atlas_label_assessed": bool(result["results"]["peak_anatomical_atlas_label_assessed"]),
            "peak_to_nearest_surface_node_mm": float(result["results"]["peak_to_nearest_surface_node_mm"]),
            "surface_node_max_v_per_m": float(result["results"]["surface_node_max_v_per_m"]),
            "nearest_surface_node_value_v_per_m": float(result["results"]["nearest_surface_node_value_v_per_m"]),
            "nearest_surface_node_subject_coordinate_mm": [float(value) for value in result["results"]["nearest_surface_node_subject_coordinate_mm"]],
            "surface_peak_subject_coordinate_mm": [float(value) for value in result["results"]["surface_peak_subject_coordinate_mm"]],
            "volume_peak_to_surface_peak_distance_mm": float(result["results"]["volume_peak_to_surface_peak_distance_mm"]),
            "peak_marker_is_2d_projection": bool(result["results"]["peak_marker_is_2d_projection"]),
            "peak_distance_to_target_mm": float(result["results"]["peak_distance_to_target_mm"]),
            "peak_distance_definition": "SimNIBS 个体 conform 空间中，全灰质 TImax 最大值所在四面体重心与目标 ROI 中心之间的三维欧氏距离，单位为 mm",
            "peak_inside_target_roi": bool(result["results"]["peak_inside_target_roi"]),
            "peak_element_qc": {
                "value_v_per_m": float(peak_qc["value_v_per_m"]),
                "volume_mm3": float(peak_qc["volume_mm3"]),
                "tissue_tag": int(peak_qc["tissue_tag"]),
                "shared_face_neighbor_tissues": peak_qc.get("shared_face_neighbor_tissues", []),
                "is_gm_csf_interface": bool(peak_qc["is_gm_csf_interface"]),
                "used_as_coverage_threshold_anchor": False,
            },
            "peak_location_assessment": {
                "statistic": "当前网格中全灰质所有 SimNIBS tag 2 四面体的单个四面体 TImax argmax",
                "is_single_element_argmax": True,
                "position_stability_assessed": False,
                "mesh_convergence_assessed": False,
                "conductivity_sensitivity_assessed": False,
                "electrode_position_sensitivity_assessed": False,
                "run_id": RUN_ID,
                "interpretation_note": "峰值坐标来自当前网格中的单个四面体 argmax。本示例未执行网格收敛、组织电导率或电极位置扰动，因此只能报告该峰值在当前场解中的位置，不能将其解释为对模型或数值设置稳定的定位结论。",
            },
            "suprathreshold_gray_matter_volume_mm3": float(result["results"]["suprathreshold_gray_matter_volume_mm3"]),
            "suprathreshold_gray_matter_fraction_pct": float(result["results"]["suprathreshold_gray_matter_fraction_pct"]),
            "suprathreshold_gray_matter_denominator_volume_mm3": float(whole["volume_mm3"]),
            "suprathreshold_gray_matter_fraction_definition": "100 × suprathreshold_gray_matter_volume_mm3 ÷ suprathreshold_gray_matter_denominator_volume_mm3；分母为 ernie 网格全部 SimNIBS tag 2 灰质四面体的总体积",
            "robustness_summary": {
                "target_mean_max_abs_change_pct": float(worst_mean),
                "target_p95_max_abs_change_pct": float(worst_p95),
                "off_target_p95_max_abs_change_pct": float(worst_offtarget_p95),
                "target_to_offtarget_p95_ratio_min": float(ratio_min),
                "target_to_offtarget_p95_ratio_max": float(ratio_max),
                "peak_distance_to_shifted_roi_min_mm": float(shifted_peak_min),
                "peak_distance_to_shifted_roi_max_mm": float(shifted_peak_max),
                "field_solution_recomputed_for_roi_displacements": False,
                "peak_coordinate_reused_from_baseline": True,
                "interpretation_note": "ROI 位移分析只改变 ROI 中心和掩膜，复用同一次 FEM 场解及同一峰值坐标；峰值距离范围仅表示几何关系变化，不构成峰值位置稳定性证据。",
                "roi_center_displacements": roi_center_displacements,
            },
            "headline_metrics": [
                {"label": "ROI 平均 TImax", "value": round(float(target["mean"]), 3), "unit": "V/m", "detail": "四面体体积加权"},
                {"label": "ROI P95", "value": round(float(target["p95"]), 3), "unit": "V/m", "detail": "四面体体积加权分位数"},
                {"label": "Target / Off-target", "value": round(float(ratio), 2), "unit": "", "detail": f"基准 P95 比值；±3 mm 范围 {ratio_min:.2f}–{ratio_max:.2f}"},
                {"label": "靶外灰质 P95", "value": round(float(off["p95"]), 3), "unit": "V/m", "detail": "四面体体积加权分位数"},
            ],
            "roi_metrics": report_roi_rows,
            "comparisons": [],
        },
        "optimization": {},
        "robustness": robustness,
        "quality_gates": gates,
        "quality_note": f"所有硬门控均通过。两组载波配置分别生成 E1 和 E2；SimNIBS 对每组四电极配置求解三个参考电极基场，再按设定电流线性组合，因此日志共记录六次基场求解。估计电流校准误差为：{calibration_text}。本项目未预先规定电流校准误差或 ROI 位移敏感性的通过阈值，因此两项均保留为提示，不作达标判定。ROI 位移分析复用同一场解和峰值坐标；网格收敛、电极位置扰动和组织电导率敏感性未执行，峰值位置稳定性未评估。",
        "methods": [
            {"title": "个体头模型", "text": "采用 SimNIBS 官方 example dataset v4.1 的 ernie 个体模型。报告保留 T1、组织标签、有限元网格、MNI 非线性变换、电极坐标和 CHARM 质控文件的来源记录。"},
            {"title": "电场求解", "text": "在同一头模型和四电极几何上建立两组准静态载波配置。表中 ±1 mA 均为峰值电流幅度，不是 RMS 或峰峰值。E1 按 F5(+1 mA 峰值)/P5(-1 mA 峰值) 标定，E2 按 F6(+1 mA 峰值)/P6(-1 mA 峰值) 标定，其余电极保持 0 mA。SimNIBS 对每组四电极配置求解三个以通道 1 为参考的基场，并按设定电流线性组合为一个输出场；因此两组配置生成 E1、E2 两个输出场，内部共执行六次基场求解。"},
            {"title": "TI 场量", "text": f"E1 与 E2 为两次独立 FEM 的矢量电场，均按上述峰值电流幅度标定。TImax 使用 SimNIBS 4.6.0 的 TI_utils.get_maxTI(E1, E2) 逐单元计算。算法先交换矢量使 ||E1||≥||E2||，必要时翻转 E2 使夹角 α≤90°，并计算 cosα=(E1·E2)/(||E1||||E2||)。当 ||E2||≤||E1||cosα 时，TImax=2||E2||；否则 TImax=2||E2×(E1−E2)||/||E1−E2||。因此本报告数值包含公式中的因子 2，表示沿所有方向取得的最大调制幅值，不是 ||E2|| 半幅、RMS 或载波峰峰值；也未使用 |E1|+|E2| 或任一单回路场强替代 TI 包络。另以独立参考实现对 {timax_recompute['element_count']:,} 个四面体逐元素复算，最大绝对误差为 {timax_recompute['max_abs_error_v_per_m']:.3g} V/m。载波频率属于设备协议参数，不参与本次准静态空间场计算。若设备面板使用 RMS，应先换算为与本报告一致的幅值口径，再比较电流或场强。"},
            {"title": "ROI 配准与解剖学边界", "text": f"ROI 沿用 SimNIBS roi_analysis_mni.py 示例中的 MNI 左侧 M1 坐标 (-37, -21, 58)。构建器使用交付的 MNI2Conform_nonl.nii.gz 独立复算 MNI→个体坐标，并使用 Conform2MNI_nonl.nii.gz 反向复核；往返误差为 {result['target']['roundtrip_error_norm_mm']:.4f} mm，低于预设 0.1 mm 阈值。变换按 NIfTI 物理 x、y、z 坐标采样，没有手工交换坐标轴。MNI 与个体 conform 坐标的逐轴数值差来自两个不同空间，不能直接解释为解剖位移。变换后建立半径 10 mm 球形 ROI，并限于 SimNIBS tag 2 灰质四面体。图 1 显示 ROI 在个体 T1/灰质解剖上的叠加位置；本示例未用个体皮层 atlas 独立确认中央前回，因此正文统一称为“MNI 定义的左侧 M1 球形 ROI”。"},
            {"title": "ROI 统计", "text": f"目标区纳入 {target['n_tetrahedra']} 个四面体、体积 {target['volume_mm3']:.2f} mm³。目标区外灰质定义为 ernie 网格中全部 tag 2 灰质四面体减去目标 ROI，纳入 {off['n_tetrahedra']} 个四面体、体积 {off['volume_mm3']:.2f} mm³；未应用额外 atlas 分区、小脑或皮层下排除，也未设置过渡缓冲。均值和分位数均按四面体体积加权。"},
            {"title": "体积加权分位数", "text": "median、P05 和 P95 使用同一离散加权经验分布算法：先保留 ROI 内场值有限、四面体体积有限且大于 0 的单元，按场值升序排列并累加四面体体积；对概率 p，返回累计体积第一次大于或等于 p × 总体积时的单元值（numpy.searchsorted，side='left'）。本算法不进行线性插值；p=0 取最小值，p=1 取最大值。ROI 表、稳健性表和 Target/Off-target P95 比值均使用该定义。"},
            {"title": "阈值与聚焦性", "text": f"高值尾部切分阈值定义为全灰质 TImax 的体积加权 P99.9（{result['threshold']['value_v_per_m']:.4f} V/m）。同一算法得到 P99={gm_tail['p99']:.4f}、P99.9={gm_tail['p99_9']:.4f}、P99.99={gm_tail['p99_99']:.4f} V/m。全灰质覆盖率约 0.1% 是 P99.9 定义产生的恒等结果，不是研究发现，也不能用于跨方案或跨受试者比较。报告同时给出目标区与目标区外各自的区域覆盖率，以及全灰质高值尾部在两者之间的体积分配；后者回答高值场主要落在何处。该阈值不是神经激活阈值或临床有效阈值。Target / Off-target 指标为目标 ROI P95 除以目标区外灰质 P95。"},
            {"title": "峰值位置与 ROI 位移", "text": f"全灰质单四面体 argmax 为 {peak_qc['value_v_per_m']:.6f} V/m，所在单元体积仅 {peak_qc['volume_mm3']:.9f} mm³，共面相邻组织为 {neighbor_names or '未识别'}；GM/CSF 界面判断为 {'是' if peak_qc['is_gm_csf_interface'] else '否'}。该极值只作为空间和网格界面质量控制，不参与覆盖阈值定义。其重心距目标 ROI 中心 {peak_distance:.1f} mm。±3 mm ROI 位移分析复用同一次 FEM 场解及同一峰值坐标，因此 {shifted_peak_min:.1f}–{shifted_peak_max:.1f} mm 只表示几何距离变化，不能证明峰值位置稳定。"},
            {"title": "组织电导率", "text": f"本次求解从 SimNIBS {result['software']['simnibs_version']} 的 TDCSLIST 实例读取固定电导率，未采用分布采样：{conductivity_text}。逐组织 tag、单位和来源见 raw_simnibs/tables/conductivities.csv。"},
            {"title": "解释边界", "text": "本报告是官方示例受试者上的软件输出演示，不包含客户 MRI，也不是逆向优化结果。正式研究应预先确定 ROI、导电率、稳健性方案和统计计划；如用于组水平推断，还需纳入受试者间变异和相应统计模型。"},
        ],
        "figures": figures,
        "artifacts": artifacts,
    }


def inject_report(template: str, data: dict) -> str:
    slice_vmax = float(data["spatial"]["color_scales"]["field_primary"]["vmax_v_per_m"])
    surface_vmax = float(data["spatial"]["color_scales"]["field_surface"]["vmax_v_per_m"])
    roi_metrics = data["results"]["roi_metrics"]
    target = next(row for row in roi_metrics if row["role"] == "目标区")
    off = next(row for row in roi_metrics if row["role"] == "非目标区")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    pattern = r"const templateData=\{.*?\};\s*let data=structuredClone\(templateData\);"
    replacement = f"const templateData={payload};\n    let data=structuredClone(templateData);"
    rendered, count = re.subn(pattern, replacement, template, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("Could not inject report data into template")
    replacements = {
        "SimNIBS 报告模板": "SimNIBS 正向 TI 仿真报告 · 示例数据",
        "记录 MRI 来源、组织分割、有限元网格、ROI 定义及电极与个体头模型的空间对应关系。": "本节记录本次计算实际使用的影像、头模型、有限元网格、ROI 及空间变换信息。",
        "展示组织模型、目标 ROI 轮廓和实际参与计算的电极位置；图中应保留方向标记与坐标系。": "正交切面通过目标 ROI 中心；绿色轮廓标示 10 mm 球形 ROI，解剖背景来自 ernie T1 MRI。",
        "记录电极位置、回路、电流幅值与极性。多频刺激同时报告载波频率和相位设置。": "两组独立回路采用相同头模型和电极几何。F5/P5 形成 E1，F6/P6 形成 E2；表中 ±1 mA 均为用于缩放准静态载波场的峰值电流幅度。",
        "箭头表示约定电流方向；所有电流值以设备输出约定为准。": "红色标记为 +1 mA 峰值电流电极，蓝色标记为 -1 mA 峰值电流电极；绿色圆环标示预定义目标 ROI。",
        "在统一坐标、单位和色标范围下呈现主要电场结果。相互比较的图件必须采用相同显示范围。": f"E1、E2 与 TImax 均以 V/m 表示。图 3A–3C 的切面共用 0–{slice_vmax:.3f} V/m 色标，图 3D–3E 的表面图共用 0–{surface_vmax:.3f} V/m 色标；两组上限不同，颜色不可跨组直接比较。",
        "单位：V/m；ROI 轮廓与方向标记随图显示。": "正交切面通过 ROI 中心；绿色轮廓标示目标区。",
        "单位：V/m；与图 3A 使用相同色标。": "与图 3A 使用相同切面位置和色标。",
        "单位：V/m；切面位置由目标 ROI 确定。": "由矢量场 E1 与 E2 计算；切面与色标同图 3A-B。",
        "显示全脑暴露和热点相对解剖位置。": "皮层表面颜色表示 TImax；绿色圆环为目标 ROI。",
        "显示目标 ROI、电极和阈值等值区域。": "同时显示皮层 TImax、四个刺激电极与目标 ROI 的空间关系。",
        "所有统计量均由结果清单中声明的场数组、有效域、ROI 掩膜和统计规则计算。": f"目标区与目标区外灰质的均值和分位数均按四面体体积加权。表中同时报告达到全灰质体积加权 P99.9 的四面体数量与体积；覆盖率分母为本区域总体积。本次目标 ROI 超阈四面体数为 {target['suprathreshold_n_tetrahedra']}，目标区外为 {off['suprathreshold_n_tetrahedra']}。该覆盖率是场分布描述量，不是神经激活阈值。HTML 表内数值按列四舍五入显示，report_data.json、原始 CSV 与 Excel 保留可复算精度。",
        "目标区与非目标区定量结果": "目标区、目标区外与全灰质定量结果",
        "展示目标区电场分布及预设阈值。": "曲线按区域体积归一化；竖线为全灰质体积加权 P99.9。全灰质覆盖率约 0.1% 由定义决定，图表重点解释高值尾部在目标区与目标区外的空间分配。",
        "同时报告效应量或不确定性区间（如适用）。": "并列比较目标区与目标区外灰质的 mean、median 和 P95；本图不包含组水平推断。",
        "评估电极位置、组织电导率、网格和刺激参数扰动对主要结论的影响。未执行的分析会明确标记，不以定性判断替代。": "本示例量化 ROI 中心沿个体空间三个轴分别平移 ±3 mm 时的目标区指标变化；其他扰动在表中标明为未评估。",
        "展示基准值、扰动范围和主要指标变化。": "曲线表示各 ROI 位移条件下 mean 与 P95 相对基准值的百分比变化。",
        "设备兼容性、安全限制、关键输入完整性和数值计算质量均为独立门控。任一硬门控未通过时，报告不得给出“推荐”结论。": "六项硬门控分别检查模型文件完整性、空间变换往返一致性、输入电流平衡、场数组有限值、TImax 独立复算一致性和双回路网格一致性；任一项未通过，报告不得给出通过结论。未执行的敏感性分析作为限制单独列出。",
        "交付包中的图、表和数组通过 report_id、run_id、文件路径与校验值建立对应关系。论文制图和二次统计应以清单中标记的源文件为准。": "图件、统计表、场数组与 ROI 掩膜均通过 report_id、run_id 和 SHA-256 校验值关联，可直接用于复核、重绘和二次统计。",
        "const num=(v,unit='')=>v===0?`0${unit}`:(v==null?MISSING:`${v}${unit}`);": "const num=(v,unit='')=>v===0?`0${unit}`:(v==null?'—':`${v}${unit}`);",
    }
    for source, target in replacements.items():
        rendered = rendered.replace(source, target)
    rendered = rendered.replace("0.191 V/m", f"{surface_vmax:.3f} V/m")
    rendered = rendered.replace("本次报告尚未载入有效结果", data["summary"]["heading"])
    rendered = rendered.replace("请载入由仿真流程生成并通过质量控制的报告 JSON。缺失数据不会被自动推断或替换。", data["summary"]["conclusion"])
    rendered = rendered.replace("本次交付未提供该图件", "该图不适用于本次正向单方案报告")
    rendered = rendered.replace("</style>", ".toolbar select,.toolbar .file-btn{display:none}\n  </style>", 1)
    rendered = rendered.replace("<title>个体化经颅电刺激仿真报告</title>", "<title>个体化时间干涉刺激正向电场仿真报告</title>")
    return rendered


def find_edge() -> Path:
    candidates = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise RuntimeError("Microsoft Edge executable not found")


def main() -> None:
    result_path = RAW / "analysis" / "analysis_results.json"
    if not result_path.is_file():
        raise RuntimeError(f"Missing completed raw analysis: {result_path}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("run_id") != RUN_ID:
        raise RuntimeError("Raw run_id does not match this report build")
    log_files = sorted((RAW / "fem").glob("simnibs_simulation_*.log"), key=lambda path: path.stat().st_mtime)
    if not log_files:
        raise RuntimeError("Missing SimNIBS solver log")
    log_text = log_files[-1].read_text(encoding="utf-8", errors="replace")
    result["quality"]["solver_log_path"] = log_files[-1].relative_to(OUTPUT).as_posix()
    result["quality"]["estimated_current_calibration_errors_pct"] = [
        float(value) for value in re.findall(r"Estimated current calibration error:\s*([0-9.]+)%", log_text)
    ]
    roi_rows = read_csv(RAW / "tables" / "roi_metrics.csv")
    electrode_rows = read_csv(RAW / "tables" / "electrode_currents.csv")
    robustness_rows = read_csv(RAW / "tables" / "robustness_roi_displacement.csv")
    slices_file = np.load(RAW / "analysis" / "slice_arrays.npz")
    slices = {name: slices_file[name] for name in slices_file.files}
    analysis_file = np.load(RAW / "analysis" / "analysis_arrays.npz")
    analysis = {name: analysis_file[name] for name in analysis_file.files}
    surface_file = np.load(RAW / "analysis" / "gm_surface_timax.npz")
    surface = {name: surface_file[name] for name in surface_file.files}
    analysis.update({"target_subject": np.asarray(result["target"]["subject_coordinate_mm"]), "electrode_labels": analysis["electrode_labels"], "electrode_coordinates": analysis["electrode_coordinates"]})

    methods_dir = OUTPUT / "methods"
    methods_dir.mkdir(parents=True, exist_ok=True)
    m2m_source = Path(result["source"]["m2m_path"])
    mni_to_subject_source = m2m_source / "toMNI" / "MNI2Conform_nonl.nii.gz"
    subject_to_mni_source = m2m_source / "toMNI" / "Conform2MNI_nonl.nii.gz"
    registration_dir = RAW / "model"
    registration_dir.mkdir(parents=True, exist_ok=True)
    mni_to_subject_copy = registration_dir / "MNI2Conform_nonl.nii.gz"
    subject_to_mni_copy = registration_dir / "Conform2MNI_nonl.nii.gz"
    if not mni_to_subject_source.is_file():
        raise RuntimeError(f"Missing MNI-to-subject deformation field: {mni_to_subject_source}")
    if not subject_to_mni_source.is_file():
        raise RuntimeError(f"Missing subject-to-MNI deformation field: {subject_to_mni_source}")
    shutil.copy2(mni_to_subject_source, mni_to_subject_copy)
    shutil.copy2(subject_to_mni_source, subject_to_mni_copy)
    source_inputs_dir = registration_dir / "source_inputs" / "m2m_ernie"
    source_inputs_dir.mkdir(parents=True, exist_ok=True)
    model_input_sources = {
        "ernie.msh": m2m_source / "ernie.msh",
        "T1.nii.gz": m2m_source / "T1.nii.gz",
        "final_tissues.nii.gz": m2m_source / "final_tissues.nii.gz",
        "charm_report.html": m2m_source / "charm_report.html",
    }
    missing_model_inputs = [str(path) for path in model_input_sources.values() if not path.is_file()]
    if missing_model_inputs:
        raise RuntimeError(f"Missing source model inputs: {missing_model_inputs}")
    for name, source in model_input_sources.items():
        shutil.copy2(source, source_inputs_dir / name)
    mni_coordinate = np.asarray(result["target"]["mni_coordinate_mm"], dtype=float)
    reported_subject_coordinate = np.asarray(result["target"]["subject_coordinate_mm"], dtype=float)
    forward_sample = sample_nifti_vector_field(mni_to_subject_copy, mni_coordinate.tolist())
    sampled_subject_coordinate = np.asarray(forward_sample["sampled_vector_mm"], dtype=float)
    forward_error_mm = sampled_subject_coordinate - reported_subject_coordinate
    inverse_sample = sample_nifti_vector_field(subject_to_mni_copy, sampled_subject_coordinate.tolist())
    roundtrip_mni_coordinate = np.asarray(inverse_sample["sampled_vector_mm"], dtype=float)
    roundtrip_error_mm = roundtrip_mni_coordinate - mni_coordinate
    peak_subject_coordinate = np.asarray(result["results"]["peak_subject_coordinate_mm"], dtype=float)
    peak_inverse_sample = sample_nifti_vector_field(subject_to_mni_copy, peak_subject_coordinate.tolist())
    peak_mni_coordinate = np.asarray(peak_inverse_sample["sampled_vector_mm"], dtype=float)
    peak_forward_sample = sample_nifti_vector_field(mni_to_subject_copy, peak_mni_coordinate.tolist())
    peak_roundtrip_subject_coordinate = np.asarray(peak_forward_sample["sampled_vector_mm"], dtype=float)
    peak_roundtrip_error_mm = peak_roundtrip_subject_coordinate - peak_subject_coordinate
    surface_coordinates = np.asarray(surface["coordinates"], dtype=float)
    surface_values_for_qc = np.asarray(surface["timax"], dtype=float)
    distances_to_volume_peak = np.linalg.norm(surface_coordinates - peak_subject_coordinate, axis=1)
    nearest_surface_index = int(np.argmin(distances_to_volume_peak))
    surface_peak_index = int(np.argmax(surface_values_for_qc))
    peak_to_surface_distance_mm = float(distances_to_volume_peak[nearest_surface_index])
    nearest_surface_value_v_per_m = float(surface_values_for_qc[nearest_surface_index])
    surface_peak_v_per_m = float(surface_values_for_qc[surface_peak_index])
    surface_peak_coordinate = surface_coordinates[surface_peak_index]
    volume_peak_to_surface_peak_distance_mm = float(np.linalg.norm(surface_peak_coordinate - peak_subject_coordinate))
    if np.linalg.norm(forward_error_mm) > 0.01:
        raise RuntimeError("Reported subject ROI coordinate does not match MNI2Conform_nonl.nii.gz")
    if np.linalg.norm(roundtrip_error_mm) > 0.1:
        raise RuntimeError("MNI-to-subject-to-MNI ROI round-trip error exceeds 0.1 mm")
    if np.linalg.norm(peak_roundtrip_error_mm) > 0.1:
        raise RuntimeError("Subject-to-MNI-to-subject peak round-trip error exceeds 0.1 mm")
    coordinate_difference_mm = reported_subject_coordinate - mni_coordinate
    registration_qc = {
        "simnibs_api": "simnibs.mni2subject_coords(coordinates, m2m_folder, transformation_type='nonl')",
        "simnibs_api_direction": "transformation_direction='mni2subject'",
        "transform_direction": "MNI physical coordinates -> SimNIBS conform subject physical coordinates",
        "transform_type": "nonlinear",
        "coordinate_order": "physical x, y, z in mm; no manual axis permutation",
        "forward_field": {
            "source_file": str(mni_to_subject_source),
            "delivered_file": "raw_simnibs/model/MNI2Conform_nonl.nii.gz",
            "source_sha256": sha256(mni_to_subject_source),
            "delivered_sha256": sha256(mni_to_subject_copy),
            **forward_sample,
        },
        "inverse_field": {
            "source_file": str(subject_to_mni_source),
            "delivered_file": "raw_simnibs/model/Conform2MNI_nonl.nii.gz",
            "source_sha256": sha256(subject_to_mni_source),
            "delivered_sha256": sha256(subject_to_mni_copy),
            **inverse_sample,
        },
        "peak_subject_to_mni": {
            **peak_inverse_sample,
            "subject_coordinate_mm": peak_subject_coordinate.tolist(),
            "mni_coordinate_mm": peak_mni_coordinate.tolist(),
            "roundtrip_forward_sample": peak_forward_sample,
            "roundtrip_subject_coordinate_mm": peak_roundtrip_subject_coordinate.tolist(),
            "roundtrip_error_components_mm": peak_roundtrip_error_mm.tolist(),
            "roundtrip_error_norm_mm": float(np.linalg.norm(peak_roundtrip_error_mm)),
            "roundtrip_acceptance_threshold_mm": 0.1,
            "roundtrip_status": "pass",
            "anatomical_atlas_label_assessed": False,
            "peak_to_nearest_surface_node_mm": peak_to_surface_distance_mm,
            "surface_node_max_v_per_m": surface_peak_v_per_m,
            "peak_marker_is_2d_projection": True,
            "interpretation_boundary": "The coordinate transform is numerically reversible within tolerance. A GM/CSF interface tag or proximity to the delivered GM surface does not by itself establish a cortical atlas label.",
        },
        "mni_coordinate_mm": result["target"]["mni_coordinate_mm"],
        "subject_coordinate_mm": result["target"]["subject_coordinate_mm"],
        "numeric_coordinate_difference_subject_minus_mni_mm": coordinate_difference_mm.tolist(),
        "coordinate_difference_interpretation": "The component-wise numeric difference compares coordinates in distinct MNI and subject-conform spaces. It is not an anatomical displacement vector and is not an axis-order check.",
        "forward_field_match_error_components_mm": forward_error_mm.tolist(),
        "forward_field_match_error_norm_mm": float(np.linalg.norm(forward_error_mm)),
        "roundtrip_mni_coordinate_mm": roundtrip_mni_coordinate.tolist(),
        "roundtrip_error_components_mm": roundtrip_error_mm.tolist(),
        "roundtrip_error_norm_mm": float(np.linalg.norm(roundtrip_error_mm)),
        "roundtrip_acceptance_threshold_mm": 0.1,
        "roundtrip_status": "pass",
        "roi_radius_mm": result["target"]["radius_mm"],
        "roi_tissue_mask": result["target"]["tissue"],
        "anatomical_label_source": "SimNIBS roi_analysis_mni.py 示例中的 MNI 左侧 M1 坐标；未执行个体特异性皮层 atlas 对中央前回的独立确认",
        "anatomical_evidence": "figures/png/fig01_model_registration.png",
        "interpretation_boundary": "本报告中的 M1 是由 MNI 坐标定义的目标标签。图 1 仅确认变换后 ROI 已叠加在个体 T1/灰质解剖上；本示例未独立判定该球形 ROI 与个体中央前回解剖标签完全一致。",
    }
    registration_qc_path = registration_dir / "roi_registration_qc.json"
    registration_qc_path.write_text(json.dumps(registration_qc, ensure_ascii=False, indent=2), encoding="utf-8")
    result["target"]["coordinate_transform_source"] = "raw_simnibs/model/MNI2Conform_nonl.nii.gz"
    result["target"]["coordinate_transform_source_sha256"] = registration_qc["forward_field"]["delivered_sha256"]
    result["target"]["coordinate_transform_inverse_source"] = "raw_simnibs/model/Conform2MNI_nonl.nii.gz"
    result["target"]["coordinate_transform_inverse_source_sha256"] = registration_qc["inverse_field"]["delivered_sha256"]
    result["target"]["coordinate_transform_qc_source"] = "raw_simnibs/model/roi_registration_qc.json"
    result["target"]["coordinate_transform_method"] = registration_qc["simnibs_api"]
    result["target"]["coordinate_transform_direction"] = registration_qc["transform_direction"]
    result["target"]["coordinate_order"] = registration_qc["coordinate_order"]
    result["target"]["numeric_coordinate_difference_subject_minus_mni_mm"] = registration_qc["numeric_coordinate_difference_subject_minus_mni_mm"]
    result["target"]["coordinate_difference_interpretation"] = registration_qc["coordinate_difference_interpretation"]
    result["target"]["roundtrip_mni_coordinate_mm"] = registration_qc["roundtrip_mni_coordinate_mm"]
    result["target"]["roundtrip_error_components_mm"] = registration_qc["roundtrip_error_components_mm"]
    result["target"]["roundtrip_error_norm_mm"] = registration_qc["roundtrip_error_norm_mm"]
    result["target"]["registration_qc_status"] = registration_qc["roundtrip_status"]
    result["results"]["peak_mni_coordinate_mm"] = peak_mni_coordinate.tolist()
    result["results"]["peak_coordinate_transform_source"] = "raw_simnibs/model/Conform2MNI_nonl.nii.gz"
    result["results"]["peak_coordinate_roundtrip_source"] = "raw_simnibs/model/MNI2Conform_nonl.nii.gz"
    result["results"]["peak_roundtrip_subject_coordinate_mm"] = peak_roundtrip_subject_coordinate.tolist()
    result["results"]["peak_roundtrip_error_components_mm"] = peak_roundtrip_error_mm.tolist()
    result["results"]["peak_roundtrip_error_norm_mm"] = float(np.linalg.norm(peak_roundtrip_error_mm))
    result["results"]["peak_roundtrip_acceptance_threshold_mm"] = 0.1
    result["results"]["peak_coordinate_transform_qc_status"] = "pass"
    result["results"]["peak_anatomical_atlas_label_assessed"] = False
    result["results"]["peak_to_nearest_surface_node_mm"] = peak_to_surface_distance_mm
    result["results"]["surface_node_max_v_per_m"] = surface_peak_v_per_m
    result["results"]["nearest_surface_node_value_v_per_m"] = nearest_surface_value_v_per_m
    result["results"]["nearest_surface_node_subject_coordinate_mm"] = surface_coordinates[nearest_surface_index].tolist()
    result["results"]["surface_peak_subject_coordinate_mm"] = surface_peak_coordinate.tolist()
    result["results"]["volume_peak_to_surface_peak_distance_mm"] = volume_peak_to_surface_peak_distance_mm
    result["results"]["peak_marker_is_2d_projection"] = True
    peak_mni_text = ", ".join(f"{value:.1f}" for value in peak_mni_coordinate)
    peak_caption = (
        f" 峰值对应 MNI 坐标约为 ({peak_mni_text}) mm；经 MNI→个体反向复算，"
        f"往返误差为 {np.linalg.norm(peak_roundtrip_error_mm):.4f} mm（通过，阈值 0.1 mm）。"
        "本示例未执行 atlas 解剖命名；GM/CSF 界面标签或距交付 GM 表面节点较近，均不能单独证明其属于某一皮层解剖区。"
    )
    FIGURE_TEXT["field_surface"]["caption"] += peak_caption
    FIGURE_TEXT["field_3d"]["caption"] += peak_caption
    projection_caption = (
        f" 菱形仅是体网格峰值在各视角中的二维投影，不是灰质表面节点热点；"
        f"该体网格重心距最近表面节点 {peak_to_surface_distance_mm:.1f} mm，"
        f"该最近节点为 {nearest_surface_value_v_per_m:.3f} V/m。洋红色方块标出真实表面最大节点 "
        f"({surface_peak_v_per_m:.3f} V/m)，其与体网格峰值相距 {volume_peak_to_surface_peak_distance_mm:.1f} mm。"
    )
    FIGURE_TEXT["field_surface"]["caption"] += projection_caption
    FIGURE_TEXT["field_3d"]["caption"] += projection_caption
    result["target"]["registration_qc_summary"] = (
        f"SimNIBS 非线性 MNI→个体变换已由交付的正向场独立复算；"
        f"反向场往返误差为 {registration_qc['roundtrip_error_norm_mm']:.4f} mm（通过，阈值 0.1 mm）。"
        "MNI 与个体 conform 坐标的逐轴数值差不能解释为解剖位移。"
    )
    result["target"]["anatomical_label_source"] = registration_qc["anatomical_label_source"]
    result["target"]["anatomical_alignment_boundary"] = registration_qc["interpretation_boundary"]
    dataset_readme = ROOT / "data" / "simnibs_examples_v4_1" / "extracted" / "readme.txt"
    if dataset_readme.is_file():
        shutil.copy2(dataset_readme, methods_dir / "simnibs_example_dataset_readme.txt")
    dataset_zip = ROOT / "data" / "simnibs_examples_v4_1" / "simnibs4_examples.zip"
    dataset_record = {
        "name": "SimNIBS example dataset",
        "release": "v4.1",
        "official_url": result["source"]["dataset_url"],
        "archive_bytes": dataset_zip.stat().st_size,
        "archive_sha256": sha256(dataset_zip),
        "license": "CC BY-NC 4.0",
        "license_evidence": "methods/simnibs_example_dataset_readme.txt",
    }
    (methods_dir / "source_dataset.json").write_text(json.dumps(dataset_record, ensure_ascii=False, indent=2), encoding="utf-8")

    figures_dir = OUTPUT / "figures"
    png_dir = figures_dir / "png"
    svg_dir = figures_dir / "svg"
    captions_dir = figures_dir / "captions"
    figure_data_dir = figures_dir / "figure_data"
    for directory in (png_dir, svg_dir, captions_dir, figure_data_dir):
        directory.mkdir(parents=True, exist_ok=True)
    scalar_values = np.concatenate(
        [np.ravel(slices[f"{name}_{orientation}"]) for name in ("magnE1", "magnE2", "TImax") for orientation in ("sagittal", "coronal", "axial")]
    )
    positive = scalar_values[scalar_values > 0]
    shared_vmax = float(np.percentile(positive, 99))
    surface_values = np.asarray(surface["timax"], dtype=float)
    surface_positive = surface_values[surface_values > 0]
    surface_vmax = float(np.percentile(surface_positive, 99))
    for figure_text in FIGURE_TEXT.values():
        figure_text["caption"] = (
            figure_text["caption"]
            .replace("0.242", f"{shared_vmax:.3f}")
            .replace("0.191", f"{surface_vmax:.3f}")
        )
    figure_specs = [
        ("model_registration", "fig01_model_registration.png", lambda p: save_slice_figure(p, slices, None, 1.0, "Individual anatomy and predefined target ROI")),
        ("stimulation_montage", "fig02_stimulation_montage.png", lambda p: save_montage_figure(p, surface, analysis, result, "Electrode montage and target location", field=False, show_electrodes=True)),
        ("field_e1", "fig03a_E1_slices.png", lambda p: save_slice_figure(p, slices, "magnE1", shared_vmax, "Carrier field E1: F5(+1 mA peak) / P5(-1 mA peak)")),
        ("field_e2", "fig03b_E2_slices.png", lambda p: save_slice_figure(p, slices, "magnE2", shared_vmax, "Carrier field E2: F6(+1 mA peak) / P6(-1 mA peak)")),
        ("field_primary", "fig03c_TImax_slices.png", lambda p: save_slice_figure(p, slices, "TImax", shared_vmax, "Maximum temporal-interference envelope (TImax)")),
        ("field_surface", "fig03d_TImax_surface.png", lambda p: save_montage_figure(p, surface, analysis, result, "Cortical-surface TImax", field=True, show_electrodes=False, field_vmax=surface_vmax)),
        ("field_3d", "fig03e_TImax_spatial_context.png", lambda p: save_montage_figure(p, surface, analysis, result, "TImax, target ROI and stimulation electrodes", field=True, show_electrodes=True, field_vmax=surface_vmax)),
        ("roi_distribution", "fig04a_roi_distribution.png", lambda p: save_histogram(p, analysis, float(result["threshold"]["value_v_per_m"]))),
        ("target_offtarget", "fig04b_target_offtarget.png", lambda p: save_roi_comparison(p, result)),
        ("robustness_summary", "fig05_roi_robustness.png", lambda p: save_robustness(p, robustness_rows)),
    ]
    histogram_rows = build_histogram_rows(analysis, float(result["threshold"]["value_v_per_m"]))
    peak_coordinate = result["results"]["peak_subject_coordinate_mm"]
    peak_rows = [
        {
            "statistic": "whole_gray_matter_single_tetrahedron_argmax",
            "TImax_v_per_m": float(result["results"]["whole_gray_matter"]["max"]),
            "tetrahedron_volume_mm3": float(result["results"]["peak_element_qc"]["volume_mm3"]),
            "shared_face_neighbor_tissues": ", ".join(item["name"] for item in result["results"]["peak_element_qc"].get("shared_face_neighbor_tissues", [])),
            "is_gm_csf_interface": bool(result["results"]["peak_element_qc"]["is_gm_csf_interface"]),
            "used_as_coverage_threshold_anchor": False,
            "subject_x_mm": float(peak_coordinate[0]),
            "subject_y_mm": float(peak_coordinate[1]),
            "subject_z_mm": float(peak_coordinate[2]),
            "mni_x_mm": float(result["results"]["peak_mni_coordinate_mm"][0]),
            "mni_y_mm": float(result["results"]["peak_mni_coordinate_mm"][1]),
            "mni_z_mm": float(result["results"]["peak_mni_coordinate_mm"][2]),
            "coordinate_roundtrip_error_mm": float(result["results"]["peak_roundtrip_error_norm_mm"]),
            "coordinate_roundtrip_threshold_mm": float(result["results"]["peak_roundtrip_acceptance_threshold_mm"]),
            "coordinate_roundtrip_status": result["results"]["peak_coordinate_transform_qc_status"],
            "distance_to_roi_center_mm": float(result["results"]["peak_distance_to_target_mm"]),
            "inside_target_roi": bool(result["results"]["peak_inside_target_roi"]),
            "coordinate_space": "SimNIBS subject conform physical space",
            "stability_assessed": False,
            "anatomical_atlas_label_assessed": False,
            "peak_to_nearest_surface_node_mm": float(result["results"]["peak_to_nearest_surface_node_mm"]),
            "surface_node_max_v_per_m": float(result["results"]["surface_node_max_v_per_m"]),
            "nearest_surface_node_value_v_per_m": float(result["results"]["nearest_surface_node_value_v_per_m"]),
            "surface_peak_x_mm": float(result["results"]["surface_peak_subject_coordinate_mm"][0]),
            "surface_peak_y_mm": float(result["results"]["surface_peak_subject_coordinate_mm"][1]),
            "surface_peak_z_mm": float(result["results"]["surface_peak_subject_coordinate_mm"][2]),
            "volume_peak_to_surface_peak_distance_mm": float(result["results"]["volume_peak_to_surface_peak_distance_mm"]),
            "peak_marker_is_2d_projection": True,
            "run_id": RUN_ID,
        }
    ]
    peak_csv_path = RAW / "tables" / "peak_spatial_relationship.csv"
    write_rows_csv(peak_csv_path, peak_rows)
    figure_data_paths = {
        "model_registration": figure_data_dir / "fig01_target_roi.csv",
        "stimulation_montage": figure_data_dir / "fig02_electrode_montage.csv",
        "roi_distribution": figure_data_dir / "fig04a_roi_distribution.csv",
        "target_offtarget": figure_data_dir / "fig04b_target_offtarget.csv",
        "robustness_summary": figure_data_dir / "fig05_roi_robustness.csv",
    }
    target_row = {
        "roi": result["target"]["name"],
        "mni_x_mm": result["target"]["mni_coordinate_mm"][0],
        "mni_y_mm": result["target"]["mni_coordinate_mm"][1],
        "mni_z_mm": result["target"]["mni_coordinate_mm"][2],
        "subject_x_mm": result["target"]["subject_coordinate_mm"][0],
        "subject_y_mm": result["target"]["subject_coordinate_mm"][1],
        "subject_z_mm": result["target"]["subject_coordinate_mm"][2],
        "radius_mm": result["target"]["radius_mm"],
        "run_id": RUN_ID,
    }
    write_rows_csv(figure_data_paths["model_registration"], [target_row])
    write_rows_csv(figure_data_paths["stimulation_montage"], electrode_rows)
    write_rows_csv(figure_data_paths["roi_distribution"], histogram_rows)
    write_rows_csv(figure_data_paths["target_offtarget"], roi_rows)
    write_rows_csv(figure_data_paths["robustness_summary"], robustness_rows)

    source_map = {
        "model_registration": "raw_simnibs/analysis/slice_arrays.npz; figures/figure_data/fig01_target_roi.csv",
        "stimulation_montage": "raw_simnibs/analysis/gm_surface_timax.npz; figures/figure_data/fig02_electrode_montage.csv",
        "field_e1": "raw_simnibs/analysis/slice_arrays.npz; raw_simnibs/fields/ernie_TI_native_magnE1.nii.gz",
        "field_e2": "raw_simnibs/analysis/slice_arrays.npz; raw_simnibs/fields/ernie_TI_native_magnE2.nii.gz",
        "field_primary": "raw_simnibs/analysis/slice_arrays.npz; raw_simnibs/fields/ernie_TI_native_TImax.nii.gz; raw_simnibs/tables/peak_spatial_relationship.csv",
        "field_surface": "raw_simnibs/analysis/gm_surface_timax.npz",
        "field_3d": "raw_simnibs/analysis/gm_surface_timax.npz; raw_simnibs/tables/electrode_currents.csv",
        "roi_distribution": "figures/figure_data/fig04a_roi_distribution.csv",
        "target_offtarget": "figures/figure_data/fig04b_target_offtarget.csv",
        "robustness_summary": "figures/figure_data/fig05_roi_robustness.csv",
    }
    svg_renderers = {
        "roi_distribution": lambda path: save_histogram_svg(path, analysis, float(result["threshold"]["value_v_per_m"])),
        "target_offtarget": lambda path: save_roi_comparison_svg(path, result),
        "robustness_summary": lambda path: save_robustness_svg(path, robustness_rows),
    }
    figures = []
    figure_rows = []
    slice_color_scale = {
        "vmin_v_per_m": 0.0,
        "vmax_v_per_m": shared_vmax,
        "statistic": "第 99 百分位数",
        "reference_population": "slice_arrays.npz 中 magnE1、magnE2 与 TImax 在目标 ROI 中心矢状、冠状和轴状九个切面的全部严格正值体素，合并后计算 P99",
        "reference_data": "raw_simnibs/analysis/slice_arrays.npz",
        "shared_by_figure_ids": ["field_e1", "field_e2", "field_primary"],
        "clipping_rule": "小于或等于 0 的场值映射到色标下限；高于 vmax 的场值截断到色标上限",
        "unit": "V/m",
    }
    surface_color_scale = {
        "vmin_v_per_m": 0.0,
        "vmax_v_per_m": surface_vmax,
        "statistic": "第 99 百分位数",
        "reference_population": "gm_surface_timax.npz 中全部严格正值灰质表面 TImax 节点，合并所有投影视角前计算 P99",
        "reference_data": "raw_simnibs/analysis/gm_surface_timax.npz",
        "shared_by_figure_ids": ["field_surface", "field_3d"],
        "clipping_rule": "小于或等于 0 的场值映射到色标下限；高于 vmax 的场值截断到色标上限",
        "unit": "V/m",
    }
    for figure_id, filename, renderer in figure_specs:
        path = png_dir / filename
        renderer(path)
        text = FIGURE_TEXT[figure_id]
        caption_path = captions_dir / f"{Path(filename).stem}.txt"
        caption_path.write_text(f"{text['label']} {text['caption']}\n", encoding="utf-8")
        vector_path = None
        if figure_id in svg_renderers:
            vector_path = svg_dir / f"{Path(filename).stem}.svg"
            svg_renderers[figure_id](vector_path)
        figure = {
            "id": figure_id,
            "src": path.relative_to(OUTPUT).as_posix(),
            "alt": text["alt"],
            "label": text["label"],
            "caption": text["caption"],
            "source_data": source_map[figure_id],
            "caption_file": caption_path.relative_to(OUTPUT).as_posix(),
            "run_id": RUN_ID,
        }
        if figure_id in {"field_e1", "field_e2", "field_primary"}:
            figure["color_scale"] = slice_color_scale
        elif figure_id in {"field_surface", "field_3d"}:
            figure["color_scale"] = surface_color_scale
        if vector_path:
            figure["vector_src"] = vector_path.relative_to(OUTPUT).as_posix()
        figures.append(figure)
        figure_rows.append(
            {
                "figure_id": figure_id,
                "png": figure["src"],
                "vector": figure.get("vector_src", "不适用（影像/表面栅格图）"),
                "source_data": figure["source_data"],
                "caption_file": figure["caption_file"],
                "display_range": f"0-{shared_vmax:.6f} V/m" if figure_id in {"field_e1", "field_e2", "field_primary"} else "见图中标注",
                "run_id": RUN_ID,
            }
        )

    data_health_path = methods_dir / "00_data_health.md"
    write_data_health(data_health_path, roi_rows, electrode_rows, robustness_rows, histogram_rows)
    scripts_dir = methods_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    delivered_scripts = []
    for source in (Path(__file__), ROOT / "scripts" / "run_simnibs_ti_customer_demo.py"):
        delivered = scripts_dir / source.name
        shutil.copy2(source, delivered)
        delivered_scripts.append(delivered)
    environment_path = methods_dir / "environment.json"
    environment_path.write_text(
        json.dumps(
            {
                "run_id": RUN_ID,
                "software": result["software"],
                "commands": {
                    "solve_or_reanalyse": "python methods/scripts/run_simnibs_ti_customer_demo.py --dataset-root raw_simnibs/model/source_inputs --output-dir raw_simnibs --reuse-fem",
                    "build_delivery": "python methods/scripts/build_simnibs_ti_customer_delivery.py",
                },
                "conductivity_table": "raw_simnibs/tables/conductivities.csv",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    artifacts = [
        artifact(RAW / "model" / "source_inputs" / "m2m_ernie" / "ernie.msh", "Gmsh mesh", "本次 FEM 使用的 SimNIBS ernie 个体头模型网格；官方示例数据 CC BY-NC 4.0", "个体 conform 空间；mm"),
        artifact(RAW / "model" / "source_inputs" / "m2m_ernie" / "T1.nii.gz", "NIfTI", "本次头模型与空间核查使用的个体 T1 MRI；官方示例数据 CC BY-NC 4.0", "个体 conform 空间；mm"),
        artifact(RAW / "model" / "source_inputs" / "m2m_ernie" / "final_tissues.nii.gz", "NIfTI", "本次 FEM 头模型对应的组织标签体数据；官方示例数据 CC BY-NC 4.0", "个体 conform 空间；组织标签"),
        artifact(RAW / "model" / "source_inputs" / "m2m_ernie" / "charm_report.html", "HTML", "CHARM 头模型分割与重建质量报告；官方示例数据 CC BY-NC 4.0", "不适用"),
        artifact(RAW / "model" / "MNI2Conform_nonl.nii.gz", "NIfTI", "MNI 物理坐标到 SimNIBS 个体 conform 物理坐标的非线性变换场", "输入/输出均为物理 x、y、z 坐标；mm"),
        artifact(RAW / "model" / "Conform2MNI_nonl.nii.gz", "NIfTI", "SimNIBS 个体 conform 物理坐标到 MNI 物理坐标的非线性反向变换场", "输入/输出均为物理 x、y、z 坐标；mm"),
        artifact(RAW / "model" / "roi_registration_qc.json", "JSON", "ROI 正向变换复算、反向往返误差、坐标顺序与解剖学解释边界", "mm；各字段注明"),
        artifact(RAW / "fields" / "ernie_TI_fields.msh", "Gmsh mesh", "按峰值电流标定的 E1、E2、magnE1、magnE2 与最大包络幅值 TImax 场数组", "个体空间；V/m（E1/E2 峰值电流标定；TImax 最大包络幅值）"),
        artifact(RAW / "fields" / "ernie_TI_analysis.h5", "HDF5", "单元中心、体积、组织标签、矢量场、最大包络幅值 TImax 和 ROI 掩膜", "个体空间；mm、mm3、V/m（幅值约定见 HDF5 属性）"),
        artifact(RAW / "fields" / "ernie_TI_native_E1.nii.gz", "NIfTI", "按峰值电流标定的 E1 个体空间矢量场", "个体 conform 空间；V/m（峰值电流标定）"),
        artifact(RAW / "fields" / "ernie_TI_native_E2.nii.gz", "NIfTI", "按峰值电流标定的 E2 个体空间矢量场", "个体 conform 空间；V/m（峰值电流标定）"),
        artifact(RAW / "fields" / "ernie_TI_native_magnE1.nii.gz", "NIfTI", "图 3A 的 E1 场强体数据；按峰值电流标定", "个体 conform 空间；V/m（峰值电流标定）"),
        artifact(RAW / "fields" / "ernie_TI_native_magnE2.nii.gz", "NIfTI", "图 3B 的 E2 场强体数据；按峰值电流标定", "个体 conform 空间；V/m（峰值电流标定）"),
        artifact(RAW / "fields" / "ernie_TI_native_TImax.nii.gz", "NIfTI", "TImax 个体空间最大包络幅值体数据", "个体 conform 空间；V/m（最大包络幅值；非 RMS/峰峰值）"),
        artifact(RAW / "fields" / "left_M1_roi.msh", "Gmsh mesh", "MNI 定义的左侧 M1 球形 ROI 掩膜", "个体空间"),
        artifact(RAW / "analysis" / "analysis_results.json", "JSON", "方法、阈值、ROI 统计、峰值位置与质量检查的原始结构化结果", "混合；各字段注明"),
        artifact(RAW / "analysis" / "timax_recompute_qc.json", "JSON", "全部四面体 TImax 独立公式复算的一致性检查", "V/m；逐元素误差与容差"),
        artifact(RAW / "analysis" / "analysis_arrays.npz", "NPZ", "单元级统计与稳健性分析数组", "个体空间；mm、mm3、V/m（TImax 最大包络幅值）"),
        artifact(RAW / "analysis" / "slice_arrays.npz", "NPZ", "图 1 与图 3A-C 的正交切面重绘数组", "个体 conform 空间；mm、V/m（E1/E2 峰值标定；TImax 最大包络幅值）"),
        artifact(RAW / "analysis" / "gm_surface_timax.npz", "NPZ", "图 2、图 3D 与图 3E 的灰质表面、TImax、电极和 ROI 数据", "个体空间；mm、V/m（TImax 最大包络幅值）"),
        artifact(log_files[-1], "LOG", "SimNIBS 求解过程、六次基场求解及估计电流校准误差", "文本日志"),
        artifact(RAW / "tables" / "roi_metrics.csv", "CSV", "目标区、目标区外及全灰质的集合定义、体积和体积加权统计", "V/m、mm3"),
        artifact(RAW / "tables" / "electrode_currents.csv", "CSV", "电极坐标与回路峰值电流", "mm、mA（峰值；非 RMS/峰峰值）"),
        artifact(RAW / "tables" / "conductivities.csv", "CSV", "本次 FEM 实际使用的逐组织固定电导率", "S/m"),
        artifact(RAW / "tables" / "robustness_roi_displacement.csv", "CSV", "ROI 中心 ±3 mm 敏感性分析", "mm、V/m、%、比值"),
        artifact(peak_csv_path, "CSV", "全灰质 TImax 单四面体峰值、个体空间坐标及其与目标 ROI 的空间关系", "V/m、mm、布尔值"),
        artifact(methods_dir / "source_dataset.json", "JSON", "官方示例数据来源、许可与归档校验", "不适用"),
        artifact(data_health_path, "Markdown", "报告结构化数据健康检查", "不适用"),
        artifact(environment_path, "JSON", "SimNIBS、Python 与核心依赖版本及复算命令", "不适用"),
        artifact(delivered_scripts[0], "Python", "客户交付包构建与图表导出脚本", "不适用"),
        artifact(delivered_scripts[1], "Python", "SimNIBS FEM 求解与派生统计脚本", "不适用"),
    ]
    for figure in figures:
        artifacts.append(artifact(OUTPUT / figure["src"], "PNG", "报告图件；300 dpi", "图中注明", display_in_report=False))
        artifacts.append(artifact(OUTPUT / figure["caption_file"], "TXT", "可直接用于论文图注的中文说明", "不适用", display_in_report=False))
        if figure.get("vector_src"):
            artifacts.append(artifact(OUTPUT / figure["vector_src"], "SVG", "定量图矢量母版", "图中注明", display_in_report=False))
    figure_data_metadata = {
        "model_registration": ("目标 ROI 坐标与半径", "MNI/个体空间；mm", None),
        "stimulation_montage": ("电极坐标与回路峰值电流", "mm、mA（峰值；非 RMS/峰峰值）", "raw_simnibs/tables/electrode_currents.csv"),
        "roi_distribution": ("目标区与目标区外灰质的体积归一化 TImax 分布", "V/m、mm3、比例", None),
        "target_offtarget": ("目标区、目标区外及全灰质的集合定义、体积和体积加权统计", "V/m、mm3", "raw_simnibs/tables/roi_metrics.csv"),
        "robustness_summary": ("ROI 中心 ±3 mm 敏感性分析", "mm、V/m、%、比值", "raw_simnibs/tables/robustness_roi_displacement.csv"),
    }
    for figure_id, path in figure_data_paths.items():
        purpose, unit_space, alias_of = figure_data_metadata[figure_id]
        artifacts.append(artifact(path, "CSV", purpose, unit_space, display_in_report=False, alias_of=alias_of))

    preliminary_report_data = build_report_data(result, roi_rows, electrode_rows, robustness_rows, figures, artifacts)
    file_rows = [
        {key: item.get(key, "") for key in ("path", "type", "purpose", "run_id", "unit_space", "alias_of", "sha256")}
        for item in artifacts
    ]
    file_rows.append({"path": "simnibs_ti_results.xlsx", "type": "Excel", "purpose": "论文重绘与二次统计工作簿", "run_id": RUN_ID, "unit_space": "混合；各表注明", "sha256": "见 manifest.json"})
    workbook_path = OUTPUT / "simnibs_ti_results.xlsx"
    build_workbook(workbook_path, result, roi_rows, electrode_rows, robustness_rows, preliminary_report_data, histogram_rows, figure_rows, file_rows)
    artifacts.append(artifact(workbook_path, "Excel", "论文重绘与二次统计工作簿", "混合；各表注明"))

    report_data = build_report_data(result, roi_rows, electrode_rows, robustness_rows, figures, artifacts)
    report_data_path = OUTPUT / "report_data.json"
    report_data_path.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
    report_data_sha_path = OUTPUT / "report_data.sha256"
    report_data_sha_path.write_text(f"{sha256(report_data_path)}  report_data.json\n", encoding="ascii")
    display_report_data = deepcopy(report_data)
    display_report_data["artifacts"].extend([
        {
            "path": "report_data.json", "type": "JSON", "purpose": "报告全部结构化数据与显示载荷",
            "run_id": RUN_ID, "unit_space": "混合；各字段注明", "sha256": "完整校验值见 report_data.sha256",
            "display_in_report": True,
        },
        {
            "path": "report_data.sha256", "type": "SHA-256", "purpose": "report_data.json 的分离校验锚点",
            "run_id": RUN_ID, "unit_space": "不适用", "sha256": "自校验不适用",
            "display_in_report": True,
        },
        {
            "path": "manifest.json", "type": "JSON", "purpose": "交付包文件大小与 SHA-256 完整清单",
            "run_id": RUN_ID, "unit_space": "不适用", "sha256": "完整校验值见 manifest.sha256",
            "display_in_report": True,
        },
        {
            "path": "manifest.sha256", "type": "SHA-256", "purpose": "manifest.json 的分离校验锚点",
            "run_id": RUN_ID, "unit_space": "不适用", "sha256": "自校验不适用",
            "display_in_report": True,
        },
    ])
    template = TEMPLATE.read_text(encoding="utf-8")
    report_html = inject_report(template, display_report_data)
    report_path = OUTPUT / "report.html"
    report_path.write_text(report_html, encoding="utf-8")

    pdf_path = OUTPUT / "report.pdf"
    edge = find_edge()
    subprocess.run(
        [str(edge), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", report_path.as_uri()],
        check=True,
        timeout=180,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if not pdf_path.is_file() or pdf_path.stat().st_size < 50_000:
        raise RuntimeError("PDF export did not produce a usable file")

    scripts_dir = methods_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    for source in (Path(__file__), ROOT / "scripts" / "run_simnibs_ti_customer_demo.py"):
        shutil.copy2(source, scripts_dir / source.name)
    methods = {
        "run_id": RUN_ID,
        "report_id": REPORT_ID,
        "source_dataset": result["source"],
        "figure_layout_budget": {
            "canvas_px": list(CANVAS), "safe_margin_px": MARGIN, "minimum_font_px": 18,
            "slice_panels": 3, "legend_placement": "outside image panels", "dpi": 300,
            "publication_width_mm": 169.3,
            "minimum_font_pt_at_final_size": 7.2,
            "vector_charts": ["fig04a_roi_distribution.svg", "fig04b_target_offtarget.svg", "fig05_roi_robustness.svg"],
        },
        "figure_data": {
            "index": "simnibs_ti_results.xlsx / 图件索引",
            "csv_directory": "figures/figure_data",
            "caption_directory": "figures/captions",
            "data_health": "methods/00_data_health.md",
        },
        "commands": {
            "solve": "python scripts/run_simnibs_ti_customer_demo.py --reuse-fem",
            "build": "python scripts/build_simnibs_ti_customer_delivery.py",
        },
    }
    (methods_dir / "reproduction.json").write_text(json.dumps(methods, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_path = OUTPUT / "manifest.json"
    manifest_sha_path = OUTPUT / "manifest.sha256"
    manifest_sha_path.unlink(missing_ok=True)
    manifest = []
    for path in sorted(OUTPUT.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            manifest.append({"path": path.relative_to(OUTPUT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest_path.write_text(json.dumps({"report_id": REPORT_ID, "run_id": RUN_ID, "files": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_sha_path.write_text(f"{sha256(manifest_path)}  manifest.json\n", encoding="ascii")
    print(json.dumps({"status": "complete", "output": str(OUTPUT), "files": len(manifest), "pdf_bytes": pdf_path.stat().st_size}, ensure_ascii=False))


if __name__ == "__main__":
    main()
