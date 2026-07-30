"""Build the customer and publication delivery for the Violante 2023 TI reproduction."""

from __future__ import annotations

import csv
import hashlib
import html
import importlib.metadata as importlib_metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    env_root = Path(sys.executable).resolve().parent
    dll_dir = env_root / "Library" / "bin"
    os.environ["PATH"] = os.pathsep.join(map(str, (dll_dir, env_root / "Scripts", env_root))) + os.pathsep + os.environ.get("PATH", "")
    if dll_dir.is_dir() and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(dll_dir))

import h5py
import matplotlib as mpl
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
from matplotlib import font_manager
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from scipy.ndimage import binary_dilation
from scipy.io import loadmat
from scipy.spatial import ConvexHull
from simnibs import ElementTags, mesh_io


# ============================================================
# CONFIGURATION - edit only this block
# ============================================================
ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "simnibs_ti_violante2023_reproduction_20260729"
M2M = ROOT / "data" / "simnibs_examples_v4_1" / "extracted" / "m2m_ernie"
PROJECT_TITLE = "基于 Violante 2023 刺激范式的 ernie 海马 TI 示例仿真"
CN_SANS_FALLBACK = ["Source Han Sans SC", "Microsoft YaHei", "Noto Sans CJK SC", "Arial Unicode MS", "sans-serif"]
EN_SANS_FALLBACK = ["Arial", "Liberation Sans", "DejaVu Sans", "sans-serif"]
OUTPUT_FORMATS = ["png", "svg", "pdf"]
DPI = 300
FIG_FIELD = (7.2, 5.2)
FIG_DOUBLE = (7.2, 3.8)
COLOR_11 = "#0072B2"
COLOR_13 = "#D55E00"
COLOR_TARGET = "#009E73"
COLOR_OFF = "#777777"
# ============================================================

RAW = OUTPUT_DIR / "raw"
TABLES = OUTPUT_DIR / "tables"
FIGURES = OUTPUT_DIR / "figures"
FIGURE_DATA = FIGURES / "figure_data"
CAPTIONS = FIGURES / "captions"
QC = OUTPUT_DIR / "quality_control"
METHODS = OUTPUT_DIR / "methods"
PACKAGES = OUTPUT_DIR / "packages"
REPRODUCIBILITY = OUTPUT_DIR / "reproducibility"
RESULT_PATH = OUTPUT_DIR / "result.json"
H5_PATH = RAW / "violante2023_reproduction_fields.h5"
RUN_ID = "ernie-violante2023-ti-forward-reproduction-20260729"

T1_PATH = M2M / "T1.nii.gz"
ROI_NIFTI = RAW / "nifti" / "ernie_violante2023_roi_hippocampus.nii.gz"
GM_NIFTI = RAW / "nifti" / "ernie_violante2023_roi_whole_gray_matter.nii.gz"


def resolve_font(candidates: list[str]) -> str:
    available = {item.name for item in font_manager.fontManager.ttflist}
    return next((name for name in candidates if name in available or name == "sans-serif"), "sans-serif")


CN_FONT = resolve_font(CN_SANS_FALLBACK)
EN_FONT = resolve_font(EN_SANS_FALLBACK)
mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": [EN_FONT, CN_FONT, "sans-serif"],
    "font.size": 9,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "axes.unicode_minus": False,
    "axes.spines.top": True,
    "axes.spines.right": True,
    "axes.spines.left": True,
    "axes.spines.bottom": True,
    "axes.edgecolor": "#222222",
    "axes.linewidth": 0.8,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "savefig.dpi": DPI,
    "svg.fonttype": "none",
})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def weighted_quantile(values: np.ndarray, weights: np.ndarray, quantile: float) -> float:
    order = np.argsort(values)
    sorted_values = values[order]
    sorted_weights = weights[order]
    cutoff = quantile * sorted_weights.sum()
    return float(sorted_values[np.searchsorted(np.cumsum(sorted_weights), cutoff, side="left")])


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"No rows for {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save_figure(fig: plt.Figure, slug: str) -> dict[str, str]:
    outputs = {}
    for extension in OUTPUT_FORMATS:
        directory = FIGURES / extension
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{slug}.{extension}"
        fig.savefig(path, dpi=DPI if extension == "png" else None, bbox_inches="tight")
        outputs[extension] = path.relative_to(OUTPUT_DIR).as_posix()
    plt.close(fig)
    return outputs


def style_axis(ax: plt.Axes) -> None:
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_linewidth(0.8)
    ax.grid(axis="y", color="#E6E8EB", linewidth=0.5)
    ax.set_axisbelow(True)


def add_panel_label(ax: plt.Axes, label: str) -> None:
    method = ax.text2D if hasattr(ax, "text2D") else ax.text
    method(-0.12, 1.05, label, transform=ax.transAxes, fontsize=10, fontweight="bold", va="top")


def metric(result: dict, condition: str, roi: str, field: str, statistic: str) -> float:
    return float(result["conditions"][condition]["metrics"][roi][field][f"{statistic}_v_per_m"])


def write_data_health(result: dict, roi_rows: list[dict[str, str]], h5: h5py.File) -> None:
    duplicate_count = len(roi_rows) - len({(row["condition"], row["roi"], row["field"]) for row in roi_rows})
    numeric_columns = ["n_elements", "volume_mm3", "mean_v_per_m", "median_v_per_m", "p95_v_per_m", "max_v_per_m"]
    nonfinite = {}
    for column in numeric_columns:
        values = np.asarray([float(row[column]) for row in roi_rows], dtype=float)
        nonfinite[column] = int((~np.isfinite(values)).sum())
    dti_valid = np.asarray(h5["mesh/dti_direction_valid"], dtype=bool)
    lines = [
        "# Data health",
        "",
        f"- ROI metric rows: {len(roi_rows)}",
        f"- Duplicate condition/ROI/field keys: {duplicate_count}",
        f"- Gray-matter elements: {len(dti_valid)}",
        f"- Valid DTI directions: {int(dti_valid.sum())} ({100*dti_valid.mean():.3f}%)",
        f"- Non-finite numeric cells: {json.dumps(nonfinite, ensure_ascii=False)}",
        f"- Atlas method: {result['implementation']['roi']['source']['method']}",
        "- Inferential statistics: not performed; ernie is one example subject.",
        "- Outlier deletion: none. Single-element maxima are retained as mesh QC, not as the primary regional endpoint.",
    ]
    (QC / "00_data_health.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if duplicate_count or any(nonfinite.values()) or result["implementation"]["roi"]["source"]["method"] != "atlas":
        raise RuntimeError("Final delivery data health gate failed")


def roi_polygon(points: np.ndarray, axes: tuple[int, int]) -> np.ndarray | None:
    projected = points[:, axes]
    if len(projected) < 3:
        return None
    hull = ConvexHull(projected)
    return projected[hull.vertices]


def load_canonical(path: Path) -> tuple[nib.Nifti1Image, np.ndarray]:
    image = nib.as_closest_canonical(nib.load(str(path)))
    return image, np.asarray(image.dataobj, dtype=np.float32)


def volume_center_voxel(mask: np.ndarray) -> np.ndarray:
    coordinates = np.argwhere(mask > 0.5)
    if not len(coordinates):
        raise RuntimeError("Target ROI NIfTI is empty")
    return np.rint(coordinates.mean(axis=0)).astype(int)


def slice_array(volume: np.ndarray, axis: int, index: int) -> np.ndarray:
    if axis == 0:
        return np.rot90(volume[index, :, :])
    if axis == 1:
        return np.rot90(volume[:, index, :])
    return np.rot90(volume[:, :, index])


def volume_field_panel(
    ax: plt.Axes,
    background: np.ndarray,
    field: np.ndarray,
    roi: np.ndarray,
    gray: np.ndarray,
    axis: int,
    index: int,
    title: str,
    vmax: float,
) -> None:
    anatomy = slice_array(background, axis, index)
    overlay = slice_array(field, axis, index)
    roi_slice = slice_array(roi, axis, index)
    gray_slice = slice_array(gray, axis, index) > 0.5
    positive = anatomy[anatomy > 0]
    lo, hi = np.percentile(positive, [1, 99])
    ax.imshow(anatomy, cmap="gray", vmin=lo, vmax=hi, interpolation="nearest")
    shown = np.ma.masked_where(~gray_slice | ~np.isfinite(overlay), overlay)
    ax.imshow(shown, cmap="cividis", norm=Normalize(0, vmax), alpha=0.84, interpolation="nearest")
    if np.any(roi_slice > 0.5):
        ax.contour(roi_slice, levels=[0.5], colors=[COLOR_TARGET], linewidths=1.2)
    brain = anatomy > 0
    yy, xx = np.where(brain)
    if len(xx):
        pad = 5
        ax.set_xlim(max(0, xx.min() - pad), min(anatomy.shape[1], xx.max() + pad))
        ax.set_ylim(min(anatomy.shape[0], yy.max() + pad), max(0, yy.min() - pad))
    orientation = {0: ("P", "A", "I", "S"), 1: ("L", "R", "I", "S"), 2: ("L", "R", "P", "A")}[axis]
    ax.text(0.01, 0.50, orientation[0], transform=ax.transAxes, color="white", va="center", ha="left", fontsize=7, fontweight="bold")
    ax.text(0.99, 0.50, orientation[1], transform=ax.transAxes, color="white", va="center", ha="right", fontsize=7, fontweight="bold")
    ax.text(0.50, 0.02, orientation[2], transform=ax.transAxes, color="white", va="bottom", ha="center", fontsize=7, fontweight="bold")
    ax.text(0.50, 0.98, orientation[3], transform=ax.transAxes, color="white", va="top", ha="center", fontsize=7, fontweight="bold")
    ax.set_title(title, fontsize=8)
    ax.set_xticks([])
    ax.set_yticks([])


def field_panel(
    ax: plt.Axes,
    centers: np.ndarray,
    values: np.ndarray,
    roi_points: np.ndarray,
    plane: str,
    center: np.ndarray,
    vmax: float,
) -> None:
    spec = {
        "Sagittal": (0, (1, 2), ("P", "A", "I", "S")),
        "Coronal": (1, (0, 2), ("L", "R", "I", "S")),
        "Axial": (2, (0, 1), ("L", "R", "P", "A")),
    }[plane]
    fixed, axes, labels = spec
    slab = np.abs(centers[:, fixed] - center[fixed]) <= 1.5
    order = np.argsort(values[slab])
    xy = centers[slab][:, axes][order]
    field_values = values[slab][order]
    ax.scatter(xy[:, 0], xy[:, 1], c=field_values, s=1.2, cmap="cividis", norm=Normalize(0, vmax), linewidths=0, rasterized=True)
    polygon = roi_polygon(roi_points[np.abs(roi_points[:, fixed] - center[fixed]) <= 3.0], axes)
    if polygon is not None:
        ax.add_patch(Polygon(polygon, closed=True, fill=False, edgecolor=COLOR_TARGET, linewidth=1.2))
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.text(0.01, 0.50, labels[0], transform=ax.transAxes, va="center", ha="left", fontsize=7)
    ax.text(0.99, 0.50, labels[1], transform=ax.transAxes, va="center", ha="right", fontsize=7)
    ax.text(0.50, 0.02, labels[2], transform=ax.transAxes, va="bottom", ha="center", fontsize=7)
    ax.text(0.50, 0.98, labels[3], transform=ax.transAxes, va="top", ha="center", fontsize=7)


def figure_anatomy(h5: h5py.File) -> tuple[dict[str, str], list[dict]]:
    t1_image, t1 = load_canonical(T1_PATH)
    roi_image, roi_volume = load_canonical(ROI_NIFTI)
    if t1.shape != roi_volume.shape or not np.allclose(t1_image.affine, roi_image.affine):
        raise RuntimeError("T1 and hippocampal ROI NIfTI are not aligned")
    center_voxel = volume_center_voxel(roi_volume)
    center_world = nib.affines.apply_affine(t1_image.affine, center_voxel)
    x, y, z = center_voxel
    panels = [
        (np.rot90(t1[x, :, :]), np.rot90(roi_volume[x, :, :]), "Sagittal", "P", "A"),
        (np.rot90(t1[:, y, :]), np.rot90(roi_volume[:, y, :]), "Coronal", "L", "R"),
        (np.rot90(t1[:, :, z]), np.rot90(roi_volume[:, :, z]), "Axial", "L", "R"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.55), constrained_layout=True)
    for index, (ax, (image, mask, title, left, right)) in enumerate(zip(axes, panels)):
        lo, hi = np.percentile(image[image > 0], [1, 99])
        ax.imshow(image, cmap="gray", vmin=lo, vmax=hi)
        if np.any(mask > 0.5):
            ax.contour(mask.astype(float), levels=[0.5], colors=[COLOR_TARGET], linewidths=1.1)
        ax.set_title(title, fontsize=9)
        ax.set_xticks([]); ax.set_yticks([])
        ax.text(0.02, 0.98, left, transform=ax.transAxes, color="white", va="top", fontweight="bold")
        ax.text(0.98, 0.98, right, transform=ax.transAxes, color="white", va="top", ha="right", fontweight="bold")
        add_panel_label(ax, chr(ord("A") + index))
    paths = save_figure(fig, "fig01_individual_anatomy_hippocampus")
    rows = [{"coordinate_space": "SimNIBS subject conform", "x_mm": center_world[0], "y_mm": center_world[1], "z_mm": center_world[2], "voxel_i": x, "voxel_j": y, "voxel_k": z}]
    write_csv(FIGURE_DATA / "fig01_target_center.csv", rows)
    return paths, rows


def figure_montage(result: dict, h5: h5py.File) -> tuple[dict[str, str], list[dict]]:
    coordinates = result["implementation"]["electrode_coordinates_subject_mm"]
    head = mesh_io.read_msh(str(RAW / "fem" / "ernie_TDCS_1_scalar.msh"))
    scalp = head.crop_mesh(tags=[ElementTags.SCALP_TH_SURFACE])
    scalp_vertices = np.asarray(scalp.nodes.node_coord, dtype=float)
    scalp_triangles = np.asarray(scalp.elm.node_number_list[:, :3], dtype=int) - 1
    roi = np.asarray(h5["masks/hippocampus"], dtype=bool)
    centers = np.asarray(h5["mesh/element_centers_subject_mm"])
    fig = plt.figure(figsize=(7.2, 2.55))
    fig.subplots_adjust(left=0.015, right=0.985, bottom=0.015, top=0.90, wspace=0.0)
    views = [(15, 165, "Left oblique"), (15, -15, "Anterior"), (90, -90, "Superior")]
    rows = []
    mins, maxs = scalp_vertices.min(axis=0), scalp_vertices.max(axis=0)
    extent = maxs - mins
    padding = extent * 0.035
    for panel, (elev, azim, title) in enumerate(views):
        ax = fig.add_subplot(1, 3, panel + 1, projection="3d")
        scalp_collection = Poly3DCollection(scalp_vertices[scalp_triangles], linewidths=0, antialiased=False, rasterized=True)
        scalp_collection.set_facecolor((0.72, 0.75, 0.78, 0.10))
        ax.add_collection3d(scalp_collection)
        ax.scatter(centers[roi, 0], centers[roi, 1], centers[roi, 2], s=1.2, color=COLOR_TARGET, alpha=0.48, depthshade=False, rasterized=True)
        for name, config in result["implementation"]["montage"].items():
            xyz = np.asarray(coordinates[name])
            color = COLOR_11 if config["pair"] == 1 else COLOR_13
            marker = "o" if config["polarity"] > 0 else "s"
            ax.scatter(*xyz, s=26, color=color, marker=marker, edgecolor="white", linewidth=0.5, depthshade=False)
            outward = xyz / max(np.linalg.norm(xyz), 1.0)
            label_position = xyz + 5.0 * outward
            sign = "+" if config["polarity"] > 0 else "−"
            ax.text(*label_position, f"{name}{sign}", fontsize=7.5, color="#111111", fontweight="bold", clip_on=False)
            if panel == 0:
                rows.append({"electrode": name, "position": config["position"], "pair": config["pair"], "polarity": config["polarity"], "x_subject_mm": xyz[0], "y_subject_mm": xyz[1], "z_subject_mm": xyz[2]})
        for first, second, color in (("e1", "e2", COLOR_11), ("e3", "e4", COLOR_13)):
            p1, p2 = np.asarray(coordinates[first]), np.asarray(coordinates[second])
            delta = p2 - p1
            ax.quiver(*p1, *delta, color=color, linewidth=1.1, arrow_length_ratio=0.07, linestyle="--")
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(title, fontsize=9)
        ax.set_xlim(mins[0] - padding[0], maxs[0] + padding[0])
        ax.set_ylim(mins[1] - padding[1], maxs[1] + padding[1])
        ax.set_zlim(mins[2] - padding[2], maxs[2] + padding[2])
        ax.set_box_aspect(extent, zoom=1.28)
        ax.set_proj_type("ortho")
        ax.set_axis_off()
        ax.text2D(0.01, 0.98, chr(ord("A") + panel), transform=ax.transAxes, fontsize=10, fontweight="bold", va="top")
    paths = save_figure(fig, "fig02_stimulation_montage")
    write_csv(FIGURE_DATA / "fig02_electrode_montage.csv", rows)
    return paths, rows


def figure_carriers(h5: h5py.File) -> dict[str, str]:
    t1_image, t1 = load_canonical(T1_PATH)
    roi_image, roi = load_canonical(ROI_NIFTI)
    gm_image, gray = load_canonical(GM_NIFTI)
    carrier_paths = [RAW / "nifti" / "ernie_violante2023_E1_unit_1mA.nii.gz", RAW / "nifti" / "ernie_violante2023_E2_unit_1mA.nii.gz"]
    values = []
    for path in carrier_paths:
        image, vectors = load_canonical(path)
        if vectors.ndim != 4 or vectors.shape[-1] != 3:
            raise RuntimeError(f"Carrier NIfTI is not a vector field: {path}")
        if image.shape[:3] != t1.shape or not np.allclose(image.affine, t1_image.affine):
            raise RuntimeError(f"Carrier NIfTI is not aligned to T1: {path}")
        values.append(np.linalg.norm(vectors, axis=-1))
    if not np.allclose(roi_image.affine, t1_image.affine) or not np.allclose(gm_image.affine, t1_image.affine):
        raise RuntimeError("Carrier supporting volumes are not aligned")
    valid = np.concatenate([value[gray > 0.5] for value in values])
    vmax = float(np.nanpercentile(valid, 99))
    center = volume_center_voxel(roi)
    fig, axes = plt.subplots(2, 3, figsize=FIG_FIELD, constrained_layout=True)
    for row, (name, field_values) in enumerate(zip(("E1", "E2"), values)):
        for column, (axis, plane) in enumerate(((0, "Sagittal"), (1, "Coronal"), (2, "Axial"))):
            volume_field_panel(axes[row, column], t1, field_values, roi, gray, axis, int(center[axis]), f"{name} | {plane}", vmax)
            add_panel_label(axes[row, column], chr(ord("A") + row * 3 + column))
    sm = mpl.cm.ScalarMappable(norm=Normalize(0, vmax), cmap="cividis")
    colorbar = fig.colorbar(sm, ax=axes, location="right", shrink=0.82, pad=0.02)
    colorbar.set_label("Electric field magnitude (V/m)")
    center_world = nib.affines.apply_affine(t1_image.affine, center)
    write_csv(FIGURE_DATA / "fig03_color_scale.csv", [{"vmin_v_per_m": 0.0, "vmax_v_per_m": vmax, "rule": "joint gray-matter P99 of E1 and E2; display clipping only", "slice_x_subject_mm": center_world[0], "slice_y_subject_mm": center_world[1], "slice_z_subject_mm": center_world[2]}])
    return save_figure(fig, "fig03_carrier_fields_E1_E2")


def figure_condition_fields(condition: str, shared_vmax: dict[str, float], number: int) -> dict[str, str]:
    t1_image, t1 = load_canonical(T1_PATH)
    roi_image, roi = load_canonical(ROI_NIFTI)
    gm_image, gray = load_canonical(GM_NIFTI)
    paths = [
        RAW / "nifti" / f"ernie_violante2023_{condition}_TI_directional_GM_only.nii.gz",
        RAW / "nifti" / f"ernie_violante2023_{condition}_TImax.nii.gz",
    ]
    values = []
    for path in paths:
        image, value = load_canonical(path)
        if image.shape != t1.shape or not np.allclose(image.affine, t1_image.affine):
            raise RuntimeError(f"TI NIfTI is not aligned to T1: {path}")
        values.append(value)
    if not np.allclose(roi_image.affine, t1_image.affine) or not np.allclose(gm_image.affine, t1_image.affine):
        raise RuntimeError("TI supporting volumes are not aligned")
    center = volume_center_voxel(roi)
    fig, axes = plt.subplots(2, 3, figsize=FIG_FIELD, constrained_layout=True)
    for row, (name, field_values, scale_key) in enumerate(zip(("Directional TI", "TImax"), values, ("directional", "timax"))):
        for column, (axis, plane) in enumerate(((0, "Sagittal"), (1, "Coronal"), (2, "Axial"))):
            volume_field_panel(axes[row, column], t1, field_values, roi, gray, axis, int(center[axis]), f"{name} | {plane}", shared_vmax[scale_key])
            add_panel_label(axes[row, column], chr(ord("A") + row * 3 + column))
    for row, (scale_key, label) in enumerate((("directional", "Directional TI (V/m)"), ("timax", "TImax (V/m)"))):
        sm = mpl.cm.ScalarMappable(norm=Normalize(0, shared_vmax[scale_key]), cmap="cividis")
        colorbar = fig.colorbar(sm, ax=axes[row, :], location="right", shrink=0.78, pad=0.02)
        colorbar.set_label(label)
    center_world = nib.affines.apply_affine(t1_image.affine, center)
    write_csv(FIGURE_DATA / f"fig{number:02d}_{condition}_slice_and_scale.csv", [
        {"metric": "TI_directional", "vmin_v_per_m": 0.0, "vmax_v_per_m": shared_vmax["directional"], "scale_rule": "joint GM P99 across TI 1:1 and TI 1:3 for this metric", "slice_x_subject_mm": center_world[0], "slice_y_subject_mm": center_world[1], "slice_z_subject_mm": center_world[2]},
        {"metric": "TImax", "vmin_v_per_m": 0.0, "vmax_v_per_m": shared_vmax["timax"], "scale_rule": "joint GM P99 across TI 1:1 and TI 1:3 for this metric", "slice_x_subject_mm": center_world[0], "slice_y_subject_mm": center_world[1], "slice_z_subject_mm": center_world[2]},
    ])
    return save_figure(fig, f"fig{number:02d}_{condition}_directional_and_TImax")


def figure_cortical_surface(shared_vmax: float) -> dict[str, str]:
    surface = np.load(RAW / "gray_surface_fields.npz")
    source_vertices = np.asarray(surface["coordinates_subject_mm"], dtype=float)
    source_triangles = np.asarray(surface["triangles_zero_based"], dtype=int)
    left = np.all(source_vertices[source_triangles, 0] < 2.0, axis=1)
    source_triangles = source_triangles[left]
    source_triangle_count = len(source_triangles)

    cluster_size_mm = 2.5
    used_vertices = np.unique(source_triangles)
    cluster_keys = np.floor(source_vertices[used_vertices] / cluster_size_mm + 0.5).astype(np.int32)
    _, inverse = np.unique(cluster_keys, axis=0, return_inverse=True)
    cluster_count = int(inverse.max() + 1)
    counts = np.bincount(inverse, minlength=cluster_count)
    vertices = np.column_stack([
        np.bincount(inverse, weights=source_vertices[used_vertices, axis], minlength=cluster_count) / counts
        for axis in range(3)
    ])
    source_to_cluster = np.full(len(source_vertices), -1, dtype=np.int32)
    source_to_cluster[used_vertices] = inverse
    triangles = source_to_cluster[source_triangles]
    nondegenerate = (
        (triangles[:, 0] != triangles[:, 1])
        & (triangles[:, 1] != triangles[:, 2])
        & (triangles[:, 0] != triangles[:, 2])
    )
    triangles = np.unique(np.sort(triangles[nondegenerate], axis=1), axis=0)
    fig = plt.figure(figsize=(7.2, 4.35))
    fig.subplots_adjust(left=0.01, right=0.865, bottom=0.015, top=0.93, wspace=0.0, hspace=0.02)
    conditions = (("TI_1to1", "TI 1:1"), ("TI_1to3", "TI 1:3"))
    views = ((10, 180, "Left lateral"), (10, 0, "Left medial"))
    norm = Normalize(0, shared_vmax)
    cmap = mpl.colormaps["cividis"]
    selected = vertices[vertices[:, 0] < 2.0]
    mins, maxs = selected.min(axis=0), selected.max(axis=0)
    extent = maxs - mins
    padding = extent * 0.025
    for row, (condition, label) in enumerate(conditions):
        source_values = np.asarray(surface[f"{condition}_TI_directional"], dtype=float)[used_vertices]
        finite = np.isfinite(source_values)
        value_counts = np.bincount(inverse[finite], minlength=cluster_count)
        values = np.divide(
            np.bincount(inverse[finite], weights=source_values[finite], minlength=cluster_count),
            value_counts,
            out=np.full(cluster_count, np.nan),
            where=value_counts > 0,
        )
        triangle_values = values[triangles]
        valid_count = np.isfinite(triangle_values).sum(axis=1)
        face_values = np.divide(
            np.nansum(triangle_values, axis=1),
            valid_count,
            out=np.full(len(triangles), np.nan),
            where=valid_count > 0,
        )
        for column, (elev, azim, view_label) in enumerate(views):
            ax = fig.add_subplot(2, 2, row * 2 + column + 1, projection="3d")
            collection = Poly3DCollection(vertices[triangles], linewidths=0, antialiased=False, rasterized=True)
            face_colors = cmap(norm(np.nan_to_num(face_values, nan=0.0)))
            face_colors[~np.isfinite(face_values), 3] = 0.0
            collection.set_facecolor(face_colors)
            ax.add_collection3d(collection)
            ax.set_xlim(mins[0] - padding[0], maxs[0] + padding[0])
            ax.set_ylim(mins[1] - padding[1], maxs[1] + padding[1])
            ax.set_zlim(mins[2] - padding[2], maxs[2] + padding[2])
            ax.set_box_aspect(extent, zoom=1.34)
            ax.set_proj_type("ortho")
            ax.view_init(elev=elev, azim=azim)
            ax.set_axis_off()
            ax.set_title(f"{label} | {view_label}", fontsize=8)
            ax.text2D(0.015, 0.98, chr(ord("A") + row * 2 + column), transform=ax.transAxes, fontsize=10, fontweight="bold", va="top")
    sm = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
    colorbar_ax = fig.add_axes([0.90, 0.15, 0.025, 0.70])
    colorbar = fig.colorbar(sm, cax=colorbar_ax)
    colorbar.set_label("Directional TI on GM surface (V/m)")
    write_csv(FIGURE_DATA / "fig10_cortical_surface_scale.csv", [{
        "vmin_v_per_m": 0.0,
        "vmax_v_per_m": shared_vmax,
        "rule": "joint surface P99 across TI 1:1 and TI 1:3; left gray-matter surface",
        "source_triangles": source_triangle_count,
        "rendered_triangles": len(triangles),
        "surface_decimation": f"vertex clustering at {cluster_size_mm:.1f} mm; all source faces remapped; degenerate and duplicate faces removed",
    }])
    return save_figure(fig, "fig10_directional_ti_cortical_surface")


def figure_hippocampal_segments(result: dict) -> tuple[dict[str, str], list[dict]]:
    segments = ["hippocampus_anterior", "hippocampus_middle", "hippocampus_posterior"]
    labels = ["Anterior", "Middle", "Posterior"]
    x = np.arange(3)
    fig, axes = plt.subplots(1, 2, figsize=FIG_DOUBLE, constrained_layout=True)
    rows = []
    for condition, color, marker, display in (("TI_1to1", COLOR_11, "o", "TI 1:1"), ("TI_1to3", COLOR_13, "s", "TI 1:3")):
        medians = [metric(result, condition, segment, "TI_directional", "median") for segment in segments]
        relative = [float(result["conditions"][condition]["relative_hippocampal_segment_exposure"][segment]) for segment in segments]
        axes[0].plot(x, medians, color=color, marker=marker, linewidth=1.6, label=display)
        axes[1].plot(x, relative, color=color, marker=marker, linewidth=1.6, label=f"ernie {display}")
        paper = result["paper"]["reported_benchmarks"]["individualized_relative_hippocampal_exposure"][condition]
        paper_values = [paper[segment][0] for segment in segments]
        paper_sd = [paper[segment][1] for segment in segments]
        axes[1].errorbar(x, paper_values, yerr=paper_sd, color=color, marker=marker, linestyle="--", linewidth=1.0, capsize=2.5, alpha=0.55, label=f"paper {display}")
        for segment, median, share, paper_value, paper_error in zip(segments, medians, relative, paper_values, paper_sd):
            rows.append({"condition": condition, "segment": segment, "ernie_directional_median_v_per_m": median, "ernie_relative_share": share, "paper_group_median_relative_share": paper_value, "paper_between_participant_sd": paper_error})
    for panel, ax in enumerate(axes):
        ax.set_xticks(x, labels)
        style_axis(ax)
        add_panel_label(ax, chr(ord("A") + panel))
    axes[0].set_ylabel("Directional TI median (V/m)")
    axes[1].set_ylabel("Relative hippocampal exposure")
    axes[1].set_ylim(0, max(0.5, axes[1].get_ylim()[1]))
    axes[0].legend(frameon=False)
    axes[1].legend(frameon=False, ncol=2, fontsize=7)
    paths = save_figure(fig, "fig06_hippocampal_segment_steering")
    write_csv(FIGURE_DATA / "fig06_hippocampal_segment_steering.csv", rows)
    return paths, rows


def figure_target_cortex(result: dict) -> tuple[dict[str, str], list[dict]]:
    rois = ["hippocampus", "cortex_anterior", "cortex_middle", "cortex_posterior"]
    labels = ["Hippocampus", "Cortex ant.", "Cortex mid.", "Cortex post."]
    x = np.arange(len(rois))
    width = 0.36
    fig, ax = plt.subplots(figsize=FIG_DOUBLE, constrained_layout=True)
    rows = []
    for offset, (condition, color, display) in zip((-width / 2, width / 2), (("TI_1to1", COLOR_11, "TI 1:1"), ("TI_1to3", COLOR_13, "TI 1:3"))):
        medians = [metric(result, condition, roi, "TI_directional", "median") for roi in rois]
        bars = ax.bar(x + offset, medians, width=width, color=color, edgecolor="black", linewidth=0.4, label=display)
        ax.bar_label(bars, labels=[f"{value:.3f}" for value in medians], fontsize=7, padding=2)
        rows.extend({"condition": condition, "roi": roi, "directional_ti_median_v_per_m": value} for roi, value in zip(rois, medians))
    ax.set_xticks(x, labels)
    ax.set_ylabel("Directional TI median (V/m)")
    ax.legend(frameon=False)
    style_axis(ax)
    paths = save_figure(fig, "fig07_hippocampus_overlying_cortex")
    write_csv(FIGURE_DATA / "fig07_hippocampus_overlying_cortex.csv", rows)
    return paths, rows


def figure_focality(result: dict) -> tuple[dict[str, str], list[dict]]:
    conditions = ["TI_1to1", "TI_1to3"]
    labels = ["TI 1:1", "TI 1:3"]
    colors = [COLOR_11, COLOR_13]
    ratios = np.asarray([[float(result["conditions"][condition]["target_to_offtarget"][key]) for key in ("mean", "median", "p95")] for condition in conditions])
    capture = np.asarray([float(result["conditions"][condition]["focality"]["target_high_tail_capture_pct"]) for condition in conditions])
    statistics = ("mean", "median", "p95")
    bilateral = {
        condition: {
            hemisphere: np.asarray([
                metric(result, condition, roi, "TI_directional", statistic)
                for statistic in statistics
            ])
            for hemisphere, roi in (("Left", "hippocampus"), ("Right", "right_hippocampus"))
        }
        for condition in conditions
    }
    fig, axes = plt.subplots(
        1,
        3,
        figsize=(7.2, 3.55),
        gridspec_kw={"width_ratios": [1.05, 1.2, 0.82]},
        constrained_layout=True,
    )
    x = np.arange(3)
    width = 0.34
    for index, (label, color) in enumerate(zip(labels, colors)):
        bars = axes[0].bar(x + (index - 0.5) * width, ratios[index], width=width, color=color, edgecolor="black", linewidth=0.45, label=label)
        axes[0].bar_label(bars, labels=[f"{value:.2f}" for value in ratios[index]], fontsize=7, padding=2)
    axes[0].axhline(1.0, color="#333333", linewidth=0.8, linestyle="--")
    axes[0].set_xticks(x, ["Mean", "Median", "P95"])
    axes[0].set_ylabel("Left / off-target ratio")
    axes[0].set_ylim(0, max(1.75, ratios.max() * 1.13))
    axes[0].legend(frameon=False, loc="upper right")

    for condition, color, condition_label in zip(conditions, colors, labels):
        axes[1].plot(x, bilateral[condition]["Left"], color=color, marker="o", linewidth=1.45, markersize=5.2, label=f"{condition_label} | Left")
        axes[1].plot(x, bilateral[condition]["Right"], color=color, marker="D", markerfacecolor="white", markeredgewidth=1.1, linestyle="--", linewidth=1.15, markersize=4.7, label=f"{condition_label} | Right")
    axes[1].set_xticks(x, ["Mean", "Median", "P95"])
    axes[1].set_ylabel("Directional TI (V/m)")
    axes[1].set_ylim(0, max(value.max() for sides in bilateral.values() for value in sides.values()) * 1.18)
    axes[1].legend(frameon=False, fontsize=6.6, ncol=2, loc="upper left", columnspacing=0.7, handlelength=1.8)

    y = np.asarray([1.0, 0.0])
    axes[2].hlines(y, 0, capture, colors=colors, linewidth=2.1)
    axes[2].scatter(capture, y, s=48, c=colors, edgecolors="black", linewidths=0.55, zorder=3)
    axes[2].set_yticks(y, labels)
    axes[2].set_xlabel("P99 tail captured (%)")
    axes[2].set_xlim(0, max(3.6, capture.max() * 1.20))
    axes[2].set_ylim(-0.55, 1.55)
    for value, ypos, color in zip(capture, y, colors):
        axes[2].annotate(f"{value:.2f}%", (value, ypos), xytext=(5, 0), textcoords="offset points", va="center", fontsize=8, color=color, fontweight="bold")
    for ax, label in zip(axes, ("A", "B", "C")):
        style_axis(ax); add_panel_label(ax, label)
    axes[2].grid(axis="x", color="#E6E8EB", linewidth=0.5)
    axes[2].grid(axis="y", visible=False)
    rows = []
    for condition, row_ratios, captured in zip(conditions, ratios, capture):
        focality = result["conditions"][condition]["focality"]
        rows.append({"condition": condition, "target_offtarget_mean_ratio": row_ratios[0], "target_offtarget_median_ratio": row_ratios[1], "target_offtarget_p95_ratio": row_ratios[2], "gm_p99_threshold_v_per_m": focality["descriptive_threshold"]["value_v_per_m"], "target_high_tail_capture_pct": captured, "target_coverage_pct": focality["target_coverage_pct"], "off_target_high_tail_volume_mm3": focality["off_target_high_tail_volume_mm3"]})
    paths = save_figure(fig, "fig08_targeting_and_focality")
    write_csv(FIGURE_DATA / "fig08_targeting_and_focality.csv", rows)
    bilateral_rows = [
        {
            "condition": condition,
            "hemisphere": hemisphere,
            "statistic": statistic,
            "directional_ti_v_per_m": values[index],
        }
        for condition in conditions
        for hemisphere, values in bilateral[condition].items()
        for index, statistic in enumerate(statistics)
    ]
    write_csv(FIGURE_DATA / "fig08_bilateral_hippocampus.csv", bilateral_rows)
    return paths, rows


def figure_focus_location(h5: h5py.File) -> tuple[dict[str, str], list[dict]]:
    centers_mni = np.asarray(h5["mesh/element_centers_mni_mm"], dtype=float)
    volumes = np.asarray(h5["mesh/element_volumes_mm3"], dtype=float)
    hippocampus = np.asarray(h5["masks/hippocampus"], dtype=bool)
    valid_geometry = hippocampus & np.isfinite(volumes) & (volumes > 0) & np.isfinite(centers_mni).all(axis=1)
    target_centroid = np.average(centers_mni[valid_geometry], axis=0, weights=volumes[valid_geometry])
    fig, ax = plt.subplots(figsize=(7.2, 2.75), constrained_layout=True)
    rows = []
    bounds = [(-40, -30, "Posterior"), (-29, -19, "Middle"), (-18, -4, "Anterior")]
    for start, end, name in bounds:
        ax.axvspan(start, end, color="#E9EDF1", alpha=0.72, zorder=0)
        ax.text((start + end) / 2, 0.82, name, ha="center", va="center", fontsize=8, zorder=1)
    for condition, color, label, y_position in (("TI_1to1", COLOR_11, "TI 1:1", 0.58), ("TI_1to3", COLOR_13, "TI 1:3", 0.32)):
        values = np.asarray(h5[f"conditions/{condition}/TI_directional_gray"], dtype=float)
        valid = valid_geometry & np.isfinite(values)
        threshold = weighted_quantile(values[valid], volumes[valid], 0.99)
        high_tail = valid & (values >= threshold)
        tail_centroid = np.average(centers_mni[high_tail], axis=0, weights=volumes[high_tail])
        peak_index = int(np.nanargmax(np.where(valid, values, np.nan)))
        peak = centers_mni[peak_index]
        ax.scatter([tail_centroid[1]], [y_position], s=58, color=color, edgecolor="white", linewidth=0.8, marker="o", zorder=4)
        ax.scatter([peak[1]], [y_position], s=50, facecolor="white", edgecolor=color, marker="D", linewidth=1.5, zorder=4)
        rows.append({
            "condition": condition,
            "hippocampal_roi_centroid_mni_y_mm": target_centroid[1],
            "hippocampal_p99_threshold_v_per_m": threshold,
            "hippocampal_p99_centroid_mni_y_mm": tail_centroid[1],
            "hippocampal_peak_mni_y_mm": peak[1],
            "hippocampal_p99_centroid_distance_to_roi_centroid_mm": float(np.linalg.norm(tail_centroid - target_centroid)),
            "hippocampal_peak_distance_to_roi_centroid_mm": float(np.linalg.norm(peak - target_centroid)),
        })
    ax.axvline(target_centroid[1], color="#333333", linewidth=0.9, linestyle="--", zorder=2)
    ax.set_xlim(-45, 0)
    ax.set_ylim(0.14, 0.90)
    ax.set_yticks([0.58, 0.32], ["TI 1:1", "TI 1:3"])
    ax.set_xlabel("MNI Y coordinate (mm): posterior to anterior")
    legend_handles = [
        Line2D([], [], color="#333333", marker="o", linestyle="None", markersize=6, label="Hippocampal P99 centroid"),
        Line2D([], [], color="#333333", marker="D", markerfacecolor="white", linestyle="None", markersize=5.5, label="Hippocampal peak"),
        Line2D([], [], color="#333333", linestyle="--", linewidth=0.9, label="ROI centroid"),
    ]
    ax.legend(handles=legend_handles, frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.01), columnspacing=1.2, handletextpad=0.5)
    style_axis(ax)
    paths = save_figure(fig, "fig09_focus_location_mni")
    write_csv(FIGURE_DATA / "fig09_focus_location_mni.csv", rows)
    return paths, rows


def build_captions(result: dict, figure_paths: dict[str, dict[str, str]], focus_rows: list[dict], focality_rows: list[dict]) -> list[dict]:
    share11 = result["conditions"]["TI_1to1"]["relative_hippocampal_segment_exposure"]
    share13 = result["conditions"]["TI_1to3"]["relative_hippocampal_segment_exposure"]
    shift_points = 100 * (share13["hippocampus_anterior"] - share11["hippocampus_anterior"])
    ratio11 = result["conditions"]["TI_1to1"]["target_to_offtarget"]["median"]
    ratio13 = result["conditions"]["TI_1to3"]["target_to_offtarget"]["median"]
    mean_ratio11 = result["conditions"]["TI_1to1"]["target_to_offtarget"]["mean"]
    mean_ratio13 = result["conditions"]["TI_1to3"]["target_to_offtarget"]["mean"]
    p95_ratio11 = result["conditions"]["TI_1to1"]["target_to_offtarget"]["p95"]
    p95_ratio13 = result["conditions"]["TI_1to3"]["target_to_offtarget"]["p95"]
    right11 = result["conditions"]["TI_1to1"]["metrics"]["right_hippocampus"]["TI_directional"]
    right13 = result["conditions"]["TI_1to3"]["metrics"]["right_hippocampus"]["TI_directional"]
    capture11 = result["conditions"]["TI_1to1"]["focality"]["target_high_tail_capture_pct"]
    capture13 = result["conditions"]["TI_1to3"]["focality"]["target_high_tail_capture_pct"]
    threshold11 = result["conditions"]["TI_1to1"]["focality"]["descriptive_threshold"]["value_v_per_m"]
    threshold13 = result["conditions"]["TI_1to3"]["focality"]["descriptive_threshold"]["value_v_per_m"]
    whole_valid_volume = result["conditions"]["TI_1to1"]["metrics"]["whole_gray_matter"]["TI_directional"]["volume_mm3"]
    target_valid_volume = result["conditions"]["TI_1to1"]["metrics"]["hippocampus"]["TI_directional"]["volume_mm3"]
    hippocampal_domain_fraction_pct = 100 * target_valid_volume / whole_valid_volume
    capture_to_volume_reference11 = capture11 / hippocampal_domain_fraction_pct
    capture_to_volume_reference13 = capture13 / hippocampal_domain_fraction_pct
    focality_support = {row["condition"]: row for row in focality_rows}
    tail_volume11 = float(focality_support["TI_1to1"]["target_high_tail_volume_mm3"])
    tail_volume13 = float(focality_support["TI_1to3"]["target_high_tail_volume_mm3"])
    tail_elements11 = int(focality_support["TI_1to1"]["target_high_tail_element_count"])
    tail_elements13 = int(focality_support["TI_1to3"]["target_high_tail_element_count"])
    focus = {row["condition"]: row for row in focus_rows}
    focus11 = focus["TI_1to1"]
    focus13 = focus["TI_1to3"]
    anterior_middle_boundary_mni_y_mm = -18.5
    boundary_margin11 = float(focus11["hippocampal_p99_centroid_mni_y_mm"]) - anterior_middle_boundary_mni_y_mm
    entries = [
        ("fig01", "个体解剖与左海马 ROI", "ernie 个体 T1 的矢状、冠状和轴状切面。绿色轮廓表示由 Harvard-Oxford 左海马标签映射到个体灰质网格的 ROI；切面通过 ROI 体积加权中心。本图确认分析区域的解剖位置，不代表客户 MRI。", "Individual T1 anatomy and the left hippocampal ROI. Green contours show the Harvard-Oxford left hippocampus mapped to the ernie gray-matter mesh; slices pass through the volume-weighted ROI centroid."),
        ("fig02", "刺激电极与两组载波回路", "四个 20 mm 圆电极在 ernie 头皮表面的位置，绿色为左海马。圆形为正极、方形为负极；蓝色虚线箭头配对 e1-e2（FT7-Fp2），橙色虚线箭头配对 e3-e4（TP7-TP8）。箭头只表示回路极性与配对，不表示头内电流路径。这些 10-10 位置是对论文连续头围坐标的实施替代。", "Electrode montage on the ernie scalp surface. Circles indicate positive electrodes and squares negative electrodes; dashed arrows denote circuit pairing and polarity, not intracranial current paths."),
        ("fig03", "两组载波电场 E1 与 E2", "E1 和 E2 在目标中心三正交切面上的幅值分布，单位为 V/m。两者均为各自电极对在 1 mA peak-to-baseline 电流下求得的载波基场，尚未按 TI 1:3 条件缩放。六个面板共用全灰质联合 P99 显示上限；超出上限的机器数值未截断。绿色轮廓表示左海马 ROI。", "Carrier-field magnitudes E1 and E2 in three orthogonal planes through the target. Each is the basis field for its electrode pair at 1 mA peak-to-baseline current, before TI 1:3 scaling. All panels share a joint gray-matter P99 display scale; machine values remain unchanged."),
        ("fig04", "TI 1:1 的方向投影包络场与 TImax", "TI 1:1 条件下，方向投影包络场沿 ernie DTI 主方向计算；TImax 为方向无关的最大包络幅值补充指标。每一行与图 5 的同名指标共享色标，方向投影 TI 与 TImax 则使用各自的显示范围。", "Directional TI envelope and TImax for TI 1:1. Each metric shares its display scale with the corresponding TI 1:3 panels; directional TI and TImax use separate ranges."),
        ("fig05", "TI 1:3 的方向投影包络场与 TImax", "TI 1:3 条件将 e1-e2 缩放为 0.5 mA、e3-e4 缩放为 1.5 mA。图 4 与图 5 对同一指标使用相同色标，因此可直接比较两种电流比下的空间分布与幅值。", "Directional TI envelope and TImax for TI 1:3, with e1-e2 scaled to 0.5 mA and e3-e4 to 1.5 mA. Matching metrics in Figures 4 and 5 share display scales."),
        ("fig06", "海马前、中、后段的场强与相对分配", f"左图为各段方向投影 TI 的体积加权中位数；右图中，本例相对份额定义为该段中位数除以三段中位数之和，前段由 {100*share11['hippocampus_anterior']:.2f}% 增至 {100*share13['hippocampus_anterior']:.2f}%（+{shift_points:.1f} 个百分点）。Violante 2023 图 2c 报告 16 名参与者个体 MRI 模型的海马分段包络幅值，正文以相对总海马暴露的 median ± s.d. 给出数值；本图将这些论文报告值原样并列，只用于观察前、中、后分布模式，不假定其归一化定义与本例完全相同，也不作数值一致性检验。ernie 的最大占比仍未转到前段，因此只支持部分向前重分配。该份额变化是当前网格与电极实现下的描述值；本示例未估计网格、电极位置或其他模型不确定性，不能据此认定已解析出稳定的纵轴 steering 效应。", "Absolute directional-TI medians and normalized anterior-middle-posterior allocation. Violante et al. (2023), Fig. 2c, reports hippocampal segment envelope amplitudes from individualized MRI models in 16 participants as median ± s.d. relative to total hippocampal exposure. Those paper-reported values are shown only as a structural reference; identical normalization is not assumed. The observed share change is descriptive for this discretized model and has no uncertainty bound; it does not establish a stable longitudinal steering effect."),
        ("fig07", "海马与蒙太奇相关皮层采样区的方向投影 TI", "柱高仅表示海马及三个蒙太奇相关皮层采样区的体积加权中位数；采样区是以 FT7、TP7 及二者中点附近灰质为中心、半径 10 mm 的球形区域，并非解剖图谱分区。mean/P95 采用同一组逐单元数据计算：TI 1:1 下前部采样区两项均高于海马，中部采样区的 P95 也高于海马；TI 1:3 下前部和中部采样区两项均高于海马。因此不能仅凭本图中位数判断表层暴露，完整数值见区域统计表与图 8。未进行组水平推断。", "Bars show only volume-weighted directional-TI medians in the hippocampus and three montage-related cortical sampling spheres with a 10-mm radius; these controls are not anatomical atlas regions. For mean/P95, both metrics exceed the hippocampus in the anterior sample and P95 also does so in the middle sample under TI 1:1; both metrics exceed the hippocampus in the anterior and middle samples under TI 1:3. Median-only bars therefore do not establish lower cortical exposure; full values are provided in the regional table and Figure 8. No group-level inference was performed."),
        ("fig08", "靶向比值与全灰质高值尾部", f"左图比较左海马与全部靶外灰质的 mean、median 和 P95 比值；靶外灰质定义为有效 DTI 分析域内排除左海马的灰质单元，因此包含右海马和其他深部灰质，也不另行排除三个皮层采样区。右海马的 mean/median/P95 为 TI 1:1 {right11['mean_v_per_m']:.4f}/{right11['median_v_per_m']:.4f}/{right11['p95_v_per_m']:.4f} V/m、TI 1:3 {right13['mean_v_per_m']:.4f}/{right13['median_v_per_m']:.4f}/{right13['p95_v_per_m']:.4f} V/m；完整区域统计见表。虚线 1 表示两者相等；TI 1:1 的 mean/median/P95 比值为 {mean_ratio11:.2f}/{ratio11:.2f}/{p95_ratio11:.2f}，TI 1:3 为 {mean_ratio13:.2f}/{ratio13:.2f}/{p95_ratio13:.2f}。TI 1:3 的 P95 比值约为 1.00，表示左海马与全部靶外灰质的 P95 基本相当。该总体比值不能说明左海马场强高于每个局部皮层或深部区域，也不能作为深部或侧化选择性证据。右图显示左海马捕获各条件自身全灰质 P99 高值尾部的体积比例，分别为 {capture11:.2f}% 和 {capture13:.2f}%；体积加权 P99 阈值分别为 {threshold11:.4f} 和 {threshold13:.4f} V/m。左海马占有效方向投影分析域体积的 {hippocampal_domain_fraction_pct:.2f}%，仅作为空间占比参照；TI 1:1 的高值尾部捕获比例约为该参照的 {capture_to_volume_reference11:.1f} 倍，TI 1:3 约为 {capture_to_volume_reference13:.3f} 倍。相应的左海马内高值尾部体积为 TI 1:1 {tail_volume11:.2f} mm³（{tail_elements11} 个四面体）、TI 1:3 {tail_volume13:.2f} mm³（{tail_elements13} 个四面体）；后者体积极小，对网格离散敏感，只作量级描述。两条件分别计算阈值，因此该比例描述各自高值尾部的空间位置，不能当作同一绝对阈值下的幅值比较。该体积参照不包含统计显著性假设；P99 是描述性分界，不是神经激活阈值。", f"Left-hippocampus-to-whole-off-target ratios and left-hippocampal capture of each condition's whole-gray-matter P99 tail. Off-target gray matter excludes only the left hippocampus and therefore includes the right hippocampus and other deep gray matter. Right-hippocampal mean/median/P95 values are {right11['mean_v_per_m']:.4f}/{right11['median_v_per_m']:.4f}/{right11['p95_v_per_m']:.4f} V/m for TI 1:1 and {right13['mean_v_per_m']:.4f}/{right13['median_v_per_m']:.4f}/{right13['p95_v_per_m']:.4f} V/m for TI 1:3. Mean/median/P95 target-to-off-target ratios are {mean_ratio11:.2f}/{ratio11:.2f}/{p95_ratio11:.2f} and {mean_ratio13:.2f}/{ratio13:.2f}/{p95_ratio13:.2f}, respectively. The global ratio does not establish superiority over every local cortical or deep region, deep selectivity, or lateralized selectivity. The hippocampus occupies {hippocampal_domain_fraction_pct:.2f}% of the valid directional-TI domain, used only as a spatial-volume reference; P99-tail capture is {capture_to_volume_reference11:.1f} and {capture_to_volume_reference13:.3f} times this reference. Corresponding left-hippocampal high-tail volumes are {tail_volume11:.2f} mm3 across {tail_elements11} tetrahedra and {tail_volume13:.2f} mm3 across {tail_elements13} tetrahedra. The latter is mesh-discretization sensitive and descriptive only; P99 is not a neural-activation threshold."),
        ("fig09", "海马内高值重心与峰值位置", f"沿 MNI Y 轴显示两条件在左海马 ROI 内分别计算的体积加权 P99 高值重心与海马内单单元峰值，并标出海马 ROI 体积重心及论文使用的前、中、后分段范围。TI 1:1 与 TI 1:3 的海马内 P99 阈值分别为 {float(focus11['hippocampal_p99_threshold_v_per_m']):.4f} 和 {float(focus13['hippocampal_p99_threshold_v_per_m']):.4f} V/m，重心 MNI Y 分别为 {float(focus11['hippocampal_p99_centroid_mni_y_mm']):.2f} 和 {float(focus13['hippocampal_p99_centroid_mni_y_mm']):.2f} mm；按论文分段边界，两者在当前离散结果中均归入前段，后者向前移动 {float(focus13['hippocampal_p99_centroid_mni_y_mm'])-float(focus11['hippocampal_p99_centroid_mni_y_mm']):.2f} mm。TI 1:1 重心距前/中边界仅 {boundary_margin11:.2f} mm，而本例未量化模型不确定度，因此无法确认这一分类裕度是否足够，其分段归属不应视为稳健分类。P99 重心只描述海马内场强最高约 1% 体积的位置；图 6 的分段中位数份额描述各整段的典型场强，因此当前离散结果中的重心分段与后段中位数份额最高并不矛盾，也不能据此认定发生或排除稳健的类别转变。该图不使用以皮层为主的全灰质高值尾部。单单元峰值对网格界面敏感，仅作为空间质控。由于未进行网格收敛、电极位置扰动或不确定性估计，1.65 mm 没有误差界限，不能解释为已验证的稳定方向性效应。", f"MNI-Y locations of the volume-weighted P99 centroid and single-element peak computed strictly within the left hippocampal ROI. Under the reported segment boundaries, both centroids fall in the anterior range in this discretized result; however, the TI 1:1 centroid is only {boundary_margin11:.2f} mm from the anterior-middle boundary. Because model uncertainty was not quantified, the adequacy of this classification margin cannot be established and the segment assignment should not be treated as robust. This top-tail location metric is distinct from the segment-median allocation in Figure 6. The 1.65-mm difference is descriptive and has no uncertainty bound; it neither establishes a stable steering effect nor a robust categorical transition."),
        ("fig10", "皮层表面的方向投影 TI", "TI 1:1 与 TI 1:3 在左侧灰质表面的方向投影包络场。两种条件共享全灰质 P99 显示上限；该表面图用于显示表层暴露的空间范围，不能代替深部海马切面和 ROI 定量。仅为加快可视化导出，表面采用 2.5 mm 顶点聚类，将全部源三角面重映射后删除退化与重复面；逐单元分析值和空间统计未做降采样。", "Directional TI on the left gray-matter surface for TI 1:1 and TI 1:3. Both conditions share a whole-gray-matter P99 display limit. A 2.5-mm vertex-clustered surface is used only for rendering; elementwise analysis data are not downsampled."),
    ]
    captions = []
    for index, (figure_id, title, zh, en) in enumerate(entries, start=1):
        if figure_id == "fig06":
            zh = f"左图为三段的体积加权中位数；右图为各段中位数在三段总和中的份额。前段由 {100*share11['hippocampus_anterior']:.2f}% 升至 {100*share13['hippocampus_anterior']:.2f}%（+{shift_points:.1f} 个百分点），但本例最高份额仍不在前段。Violante 2023 图 2c 报告 16 名参与者个体 MRI 模型的相对海马暴露；此处仅并列其分布模式。"
            en = f"Volume-weighted segment medians and their normalized allocation. The anterior share changes from {100*share11['hippocampus_anterior']:.2f}% to {100*share13['hippocampus_anterior']:.2f}% (+{shift_points:.1f} percentage points), while the largest share remains outside the anterior segment. Published Figure 2c values are shown only as a structural reference."
        elif figure_id == "fig07":
            zh = "柱高为海马及三个蒙太奇相关皮层采样区的体积加权中位数。采样区为 FT7、TP7 及其中点附近的 10 mm 球形灰质区，不是解剖图谱分区。柱高仅表示海马及三个蒙太奇相关皮层采样区的体积加权中位数；mean 和 P95 见区域统计表与图 8。"
            en = "Bars show volume-weighted medians in the hippocampus and three 10-mm montage-related cortical sampling spheres. These are sampling regions, not atlas ROIs; mean and P95 values are provided in the regional table and Figure 8."
        elif figure_id == "fig08":
            zh = f"A 面板给出左海马/全部靶外灰质的 mean、median 和 P95 比值，B 面板比较左右海马，C 面板给出 P99 尾部捕获率。靶外灰质包含右海马、其他深部灰质和皮层采样区。TI 1:1 与 TI 1:3 的比值分别为 {mean_ratio11:.2f}/{ratio11:.2f}/{p95_ratio11:.2f} 和 {mean_ratio13:.2f}/{ratio13:.2f}/{p95_ratio13:.2f}；P99 捕获率为 {capture11:.2f}% 和 {capture13:.2f}%。TI 1:3 海马内高值尾部为 {tail_volume13:.2f} mm³（{tail_elements13} 个四面体），对网格离散敏感。"
            en = f"Panels show left-to-off-target ratios, bilateral hippocampal statistics, and P99-tail capture. Off-target gray matter includes the right hippocampus, other deep gray matter, and cortical samples. TI 1:1 and TI 1:3 ratios are {mean_ratio11:.2f}/{ratio11:.2f}/{p95_ratio11:.2f} and {mean_ratio13:.2f}/{ratio13:.2f}/{p95_ratio13:.2f}; P99-tail capture is {capture11:.2f}% and {capture13:.2f}%."
        elif figure_id == "fig09":
            zh = f"图示左海马内 P99 重心和单单元峰值的 MNI Y 坐标。两条件重心均在前段，TI 1:3 较 TI 1:1 前移 {float(focus13['hippocampal_p99_centroid_mni_y_mm'])-float(focus11['hippocampal_p99_centroid_mni_y_mm']):.2f} mm；TI 1:1 重心距前/中边界仅 {boundary_margin11:.2f} mm。"
            en = f"MNI-Y locations of the left-hippocampal P99 centroid and single-element peak. Both centroids fall in the anterior range; TI 1:3 is {float(focus13['hippocampal_p99_centroid_mni_y_mm'])-float(focus11['hippocampal_p99_centroid_mni_y_mm']):.2f} mm anterior to TI 1:1, whose centroid is {boundary_margin11:.2f} mm from the anterior-middle boundary."
        if figure_id == "fig08":
            zh = zh.replace(
                "左图比较左海马与全部靶外灰质的 mean、median 和 P95 比值；",
                "A 面板比较左海马与全部靶外灰质的 mean、median 和 P95 比值；B 面板在同一 V/m 轴上直接比较左、右海马的 mean、median 和 P95；",
                1,
            ).replace(
                "右图显示左海马捕获各条件自身全灰质 P99 高值尾部的体积比例",
                "C 面板用固定大小标记和直接数值标注显示左海马捕获各条件自身全灰质 P99 高值尾部的体积比例",
                1,
            )
            en = en.replace(
                "Left-hippocampus-to-whole-off-target ratios and left-hippocampal capture of each condition's whole-gray-matter P99 tail.",
                "Panel A shows left-hippocampus-to-whole-off-target ratios; Panel B directly compares left- and right-hippocampal mean, median, and P95 on a common V/m axis; Panel C uses fixed-size markers and direct labels for left-hippocampal capture of each condition's whole-gray-matter P99 tail.",
                1,
            )
        if figure_id == "fig09":
            zh = zh.replace("按论文分段边界", "按相邻论文整数切片的中点边界")
            en = en.replace("Under the reported segment boundaries", "Under midpoint boundaries between adjacent reported integer slices")
        slug = f"fig{index:02d}"
        paths = figure_paths[figure_id]
        zh_path = CAPTIONS / f"{slug}_zh.txt"
        en_path = CAPTIONS / f"{slug}_en.txt"
        zh_path.write_text(f"图 {index}｜{title}。{zh}\n", encoding="utf-8")
        en_path.write_text(f"Figure {index}. {en}\n", encoding="utf-8")
        captions.append({"id": figure_id, "number": index, "title": title, "caption_zh": zh, "caption_en": en, "png": paths["png"], "svg": paths["svg"], "pdf": paths["pdf"], "caption_zh_file": zh_path.relative_to(OUTPUT_DIR).as_posix(), "caption_en_file": en_path.relative_to(OUTPUT_DIR).as_posix()})
    return captions


def add_sheet(workbook: Workbook, title: str, rows: list[dict]) -> None:
    sheet = workbook.create_sheet(title)
    if not rows:
        sheet.append(["No data"])
        return
    headers = list(rows[0])
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header) for header in headers])
    fill = PatternFill("solid", fgColor="17324D")
    for cell in sheet[1]:
        cell.fill = fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for column in sheet.columns:
        width = min(42, max(10, max(len(str(cell.value or "")) for cell in column) + 2))
        sheet.column_dimensions[column[0].column_letter].width = width
        for cell in column:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def build_workbook(result: dict, roi_rows: list[dict], electrode_rows: list[dict], captions: list[dict], segment_rows: list[dict], focality_rows: list[dict]) -> Path:
    workbook = Workbook()
    workbook.remove(workbook.active)
    add_sheet(workbook, "README", [{"item": "Purpose", "value": "Publication redraw and secondary descriptive analysis for the ernie Violante 2023 TI reproduction"}, {"item": "Primary field", "value": "Directional TI envelope (V/m), projected onto the local DTI principal direction"}, {"item": "Inference", "value": "None; one example subject"}, {"item": "Claim boundary", "value": result["claim_boundary"]}])
    add_sheet(workbook, "ROI metrics", roi_rows)
    add_sheet(workbook, "Hippocampal segments", segment_rows)
    add_sheet(workbook, "Focality", focality_rows)
    add_sheet(workbook, "Electrodes", electrode_rows)
    paper_rows = []
    benchmark = result["paper"]["reported_benchmarks"]
    for condition, segments in benchmark["individualized_relative_hippocampal_exposure"].items():
        if condition in {"summary", "source"}:
            continue
        for region, values in segments.items():
            paper_rows.append({"source": benchmark["individualized_relative_hippocampal_exposure"]["source"], "condition": condition, "region": region, "reported_group_median": values[0], "reported_between_participant_sd": values[1], "unit": "relative total hippocampal exposure"})
    add_sheet(workbook, "Paper benchmark", paper_rows)
    add_sheet(workbook, "Figure index", [{"figure": item["number"], "title": item["title"], "PNG": item["png"], "SVG": item["svg"], "PDF": item["pdf"], "Chinese caption": item["caption_zh_file"], "English caption": item["caption_en_file"]} for item in captions])
    quality = result["quality"]
    qc_rows = [
        {"check": "Carrier mesh alignment", "condition": "all", "value": quality["carrier_mesh_alignment"], "unit": "boolean", "interpretation": "E1 and E2 use identical nodes and elements"},
        {"check": "Gray-matter tetrahedra", "condition": "all", "value": quality["gray_tetrahedra"], "unit": "count", "interpretation": "analysis domain"},
        {"check": "Gray-matter volume", "condition": "all", "value": quality["gray_volume_mm3"], "unit": "mm3", "interpretation": "tetrahedron-volume sum"},
        {"check": "Finite DTI directions", "condition": "all", "value": quality["dti_valid_gray_fraction"], "unit": "fraction", "interpretation": "Finite unit-vector availability only; no FA/eigenvalue-anisotropy threshold and no claim of directional reliability; invalid directions remain NaN"},
        {"check": "Configured current balance pair 1", "condition": "all", "value": quality["configured_current_balance_a"]["carrier_pair_1"], "unit": "A", "interpretation": "configured source-current sum"},
        {"check": "Configured current balance pair 2", "condition": "all", "value": quality["configured_current_balance_a"]["carrier_pair_2"], "unit": "A", "interpretation": "configured source-current sum"},
        {"check": "Maximum internal basis current-calibration estimate", "condition": "FEM", "value": quality["solver_log"]["maximum_basis_solve_current_calibration_error_pct"], "unit": "%", "interpretation": "SimNIBS internal basis-solve estimate; not a measured device error and no acceptance threshold was declared"},
    ]
    for condition, checks in quality["independent_formula_checks"].items():
        qc_rows.extend([
            {"check": "Independent directional-TI formula max absolute error", "condition": condition, "value": checks["directional_ti_max_abs_error_v_per_m"], "unit": "V/m", "interpretation": f"acceptance <= {checks['acceptance_tolerance_v_per_m']} V/m"},
            {"check": "Independent TImax formula max absolute error", "condition": condition, "value": checks["timax_max_abs_error_v_per_m"], "unit": "V/m", "interpretation": f"acceptance <= {checks['acceptance_tolerance_v_per_m']} V/m"},
        ])
    coverage = result["implementation"]["roi"]["segment_coverage"]
    qc_rows.extend([
        {"check": "Hippocampal segment assigned fraction", "condition": "all", "value": coverage["assigned_fraction"], "unit": "fraction", "interpretation": "share within the paper-reported MNI Y range"},
        {"check": "Hippocampal segment overlap volume", "condition": "all", "value": coverage["overlap_volume_mm3"], "unit": "mm3", "interpretation": "must equal zero"},
        {"check": "Hippocampal volume outside reported segment range", "condition": "all", "value": coverage["outside_reported_segment_range_volume_mm3"], "unit": "mm3", "interpretation": "excluded from anterior/middle/posterior normalization"},
    ])
    add_sheet(workbook, "QC", qc_rows)

    simulation_mat = next((RAW / "fem").glob("simnibs_simulation_*.mat"))
    mat = loadmat(simulation_mat, simplify_cells=True)
    conductivities = [
        {"tissue_index": index + 1, "tissue": item["name"], "conductivity_s_per_m": item["value"], "model": "isotropic SimNIBS session value"}
        for index, item in enumerate(mat["poslist"][0]["cond"])
        if isinstance(item, dict) and np.isscalar(item.get("value"))
    ]
    add_sheet(workbook, "Conductivities", conductivities)

    dictionary_rows = [
        {"location": "tables/roi_metrics.csv", "field": "mean/median/p95/max_v_per_m", "shape_or_type": "numeric", "unit": "V/m", "coordinate_space": "ROI summary", "missing_values": "none", "definition": "Volume-weighted regional statistics; maximum is unweighted single-element maximum"},
        {"location": "tables/roi_metrics.csv", "field": "off_target_gray_matter / TI_directional", "shape_or_type": "ROI summary", "unit": "V/m and mm3", "coordinate_space": "SimNIBS gray-matter tetrahedra", "missing_values": "Invalid DTI-direction elements excluded", "definition": "All positive-volume gray-matter tetrahedra outside the left-hippocampal target mask with finite directional TI; includes the right hippocampus, other deep gray matter, and cortical sampling regions"},
        {"location": "tables/roi_metrics.csv", "field": "right_hippocampus / TI_directional", "shape_or_type": "ROI summary", "unit": "V/m and mm3", "coordinate_space": "Harvard-Oxford right hippocampus mapped to SimNIBS gray matter", "missing_values": "Invalid DTI-direction elements excluded", "definition": "Explicit contralateral homologous deep off-target ROI sampled with the same atlas, nonlinear coordinate transform, and nearest-neighbor rule as the left target"},
        {"location": "result.json", "field": "implementation.roi.cortical_control_regions", "shape_or_type": "metadata object", "unit": "mm", "coordinate_space": "SimNIBS subject conform", "missing_values": "none", "definition": "Exploratory gray-matter sampling spheres with a 10-mm radius, centered on the nearest gray-matter element to FT7, TP7, and the FT7-TP7 scalp-coordinate midpoint"},
        {"location": "result.json", "field": "implementation.field_metrics.TI_directional", "shape_or_type": "formula metadata", "unit": "V/m", "coordinate_space": "local DTI principal direction", "missing_values": "NaN where the DTI direction is invalid", "definition": "SimNIBS get_dirTI modulation amplitude: with unit vector u, a=E1 dot u and b=E2 dot u, A_dir=abs(abs(a+b)-abs(a-b))"},
        {"location": "result.json", "field": "implementation.field_metrics.TImax", "shape_or_type": "formula metadata", "unit": "V/m", "coordinate_space": "direction-independent", "missing_values": "none", "definition": "SimNIBS get_maxTI maximum modulation-envelope amplitude following Grossman et al. 2017; not RMS or carrier-field magnitude"},
        {"location": "result.json", "field": "target_to_offtarget", "shape_or_type": "numeric object", "unit": "ratio", "coordinate_space": "valid directional-TI gray-matter domain", "missing_values": "none", "definition": "Hippocampal statistic divided by the matching off-target-gray-matter statistic for mean, median, and P95"},
        {"location": "result.json", "field": "relative_hippocampal_segment_exposure", "shape_or_type": "three-value numeric object", "unit": "fraction", "coordinate_space": "hippocampal anterior/middle/posterior segments", "missing_values": "Hippocampal volume outside the three reported MNI-Y ranges excluded", "definition": "Each segment's volume-weighted directional-TI median divided by the sum of the three segment medians"},
        {"location": "result.json", "field": "target_high_tail_capture_pct", "shape_or_type": "numeric", "unit": "%", "coordinate_space": "whole gray matter", "missing_values": "none", "definition": "Hippocampal share of whole-GM volume at or above directional-TI P99; descriptive, not an activation threshold"},
        {"location": "figures/figure_data/fig08_targeting_and_focality.csv", "field": "hippocampal_domain_fraction_pct / capture_to_domain_fraction_ratio", "shape_or_type": "numeric", "unit": "% / ratio", "coordinate_space": "valid directional-TI gray-matter domain", "missing_values": "none", "definition": "Hippocampal volume fraction of the valid analysis domain and P99-tail capture divided by that volume fraction; descriptive spatial reference only, with no statistical-significance or neural-activation interpretation"},
        {"location": "figures/figure_data/fig08_targeting_and_focality.csv", "field": "target_high_tail_volume_mm3 / target_high_tail_element_count", "shape_or_type": "numeric", "unit": "mm3 / count", "coordinate_space": "hippocampal tetrahedra within each condition's whole-GM directional-TI P99 tail", "missing_values": "none", "definition": "Exact hippocampal high-tail volume and contributing tetrahedron count; small values are mesh-discretization sensitive and descriptive only"},
        {"location": "quality_control/03_coordinate_transform.json", "field": "subject_to_mni_transform", "shape_or_type": "metadata object", "unit": "none", "coordinate_space": "SimNIBS subject conform to MNI", "missing_values": "none", "definition": "SimNIBS subject2mni_coords nonlinear coordinate warp using m2m_ernie/toMNI/Conform2MNI_nonl.nii.gz; Harvard-Oxford labels sampled by nearest neighbor at transformed tetrahedron centers; registration uncertainty not evaluated"},
    ]
    with h5py.File(H5_PATH, "r") as h5:
        def add_dataset(name: str, item: h5py.Dataset) -> None:
            if not isinstance(item, h5py.Dataset):
                return
            unit = ""
            coordinate = ""
            missing = "none"
            definition = name.replace("_", " ")
            if name.startswith("conditions/"):
                unit, coordinate = "V/m", "SimNIBS gray-matter tetrahedra"
                missing = "NaN for invalid DTI direction in TI_directional; otherwise none"
            elif "centers_subject_mm" in name:
                unit, coordinate = "mm", "SimNIBS subject conform"
            elif "centers_mni_mm" in name:
                unit, coordinate = "mm", "MNI"
            elif "volumes_mm3" in name:
                unit, coordinate = "mm3", "SimNIBS gray-matter tetrahedra"
            elif "direction" in name:
                unit, coordinate, missing = "unit vector", "SimNIBS world axes", "NaN when dti_direction_valid is false"
            elif name.startswith("masks/"):
                unit, coordinate = "0/1", "SimNIBS gray-matter tetrahedra"
            elif "indices_zero_based" in name:
                unit, coordinate = "zero-based index", "full SimNIBS mesh"
            dictionary_rows.append({"location": "raw/violante2023_reproduction_fields.h5", "field": name, "shape_or_type": str(tuple(item.shape)) + " / " + str(item.dtype), "unit": unit, "coordinate_space": coordinate, "missing_values": missing, "definition": definition})
        h5.visititems(add_dataset)
    add_sheet(workbook, "Data dictionary", dictionary_rows)
    path = TABLES / "violante2023_ti_reproduction_results.xlsx"
    workbook.save(path)
    return path


def figure_html(item: dict) -> str:
    return f"""<figure id="{item['id']}">
      <a href="{html.escape(item['svg'])}" title="打开 SVG 矢量图"><img src="{html.escape(item['png'])}" alt="{html.escape(item['title'])}"></a>
      <figcaption><strong>图 {item['number']}｜{html.escape(item['title'])}</strong><span>{html.escape(item['caption_zh'])}</span><small>PNG · <a href="{html.escape(item['svg'])}">SVG</a> · <a href="{html.escape(item['pdf'])}">PDF</a> · <a href="{html.escape(item['caption_en_file'])}">英文图注</a></small></figcaption>
    </figure>"""


def clinical_figure_html(item: dict, caption: str) -> str:
    return f"""<figure id="{item['id']}">
      <a href="{html.escape(item['svg'])}" title="打开 SVG 矢量图"><img src="{html.escape(item['png'])}" alt="{html.escape(item['title'])}"></a>
      <figcaption><strong>图 {item['number']}｜{html.escape(item['title'])}</strong><span>{html.escape(caption)}</span><small><a href="{html.escape(item['svg'])}">SVG</a> · <a href="{html.escape(item['pdf'])}">PDF</a> · <a href="{html.escape(item['caption_en_file'])}">英文图注</a></small></figcaption>
    </figure>"""


def build_secondary_analysis_archives() -> dict[str, Path]:
    PACKAGES.mkdir(parents=True, exist_ok=True)
    csv_archive = PACKAGES / "figure_support_csv.zip"
    nifti_archive = PACKAGES / "nifti_fields.zip"
    for archive in (csv_archive, nifti_archive):
        if archive.exists():
            archive.unlink()

    csv_files = sorted(FIGURE_DATA.glob("*.csv")) + [
        TABLES / "roi_metrics.csv",
        TABLES / "electrode_montage.csv",
    ]
    if not csv_files or not all(path.is_file() for path in csv_files):
        raise FileNotFoundError("Incomplete CSV support files")
    with zipfile.ZipFile(csv_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in csv_files:
            prefix = "figures/figure_data" if path.parent == FIGURE_DATA else "tables"
            archive.write(path, f"{prefix}/{path.name}")

    nifti_files = sorted((RAW / "nifti").glob("*.nii*"))
    if not nifti_files:
        raise FileNotFoundError("Missing NIfTI files for secondary-analysis archive")
    with zipfile.ZipFile(nifti_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in nifti_files:
            archive.write(path, f"nifti/{path.name}")
    return {"csv": csv_archive, "nifti": nifti_archive}


def build_html(result: dict, captions: list[dict], focus_rows: list[dict], focality_rows: list[dict]) -> str:
    conditions = result["conditions"]
    hip11 = conditions["TI_1to1"]["metrics"]["hippocampus"]["TI_directional"]
    hip13 = conditions["TI_1to3"]["metrics"]["hippocampus"]["TI_directional"]
    right11 = conditions["TI_1to1"]["metrics"]["right_hippocampus"]["TI_directional"]
    right13 = conditions["TI_1to3"]["metrics"]["right_hippocampus"]["TI_directional"]
    left_right_ratios11 = {key: hip11[f"{key}_v_per_m"] / right11[f"{key}_v_per_m"] for key in ("mean", "median", "p95")}
    left_right_ratios13 = {key: hip13[f"{key}_v_per_m"] / right13[f"{key}_v_per_m"] for key in ("mean", "median", "p95")}
    share11 = conditions["TI_1to1"]["relative_hippocampal_segment_exposure"]
    share13 = conditions["TI_1to3"]["relative_hippocampal_segment_exposure"]
    anterior_shift = 100 * (share13["hippocampus_anterior"] - share11["hippocampus_anterior"])
    segment_zh = {"hippocampus_anterior": "前段", "hippocampus_middle": "中段", "hippocampus_posterior": "后段"}
    highest11 = segment_zh[max(share11, key=share11.get)]
    highest13 = segment_zh[max(share13, key=share13.get)]
    if highest11 == highest13:
        highest_segment_text = f"占比最高区域在两种电流比下均为{highest11}"
    else:
        highest_segment_text = f"占比最高区域由 {highest11} 变为 {highest13}"
    ratio11 = conditions["TI_1to1"]["target_to_offtarget"]["median"]
    ratio13 = conditions["TI_1to3"]["target_to_offtarget"]["median"]
    mean_ratio11 = conditions["TI_1to1"]["target_to_offtarget"]["mean"]
    mean_ratio13 = conditions["TI_1to3"]["target_to_offtarget"]["mean"]
    p95_ratio11 = conditions["TI_1to1"]["target_to_offtarget"]["p95"]
    p95_ratio13 = conditions["TI_1to3"]["target_to_offtarget"]["p95"]
    off_target_median11 = conditions["TI_1to1"]["metrics"]["off_target_gray_matter"]["TI_directional"]["median_v_per_m"]
    off_target_median13 = conditions["TI_1to3"]["metrics"]["off_target_gray_matter"]["TI_directional"]["median_v_per_m"]
    p99_threshold11 = conditions["TI_1to1"]["focality"]["descriptive_threshold"]["value_v_per_m"]
    p99_threshold13 = conditions["TI_1to3"]["focality"]["descriptive_threshold"]["value_v_per_m"]
    focus = {row["condition"]: row for row in focus_rows}
    hippocampal_tail_y11 = float(focus["TI_1to1"]["hippocampal_p99_centroid_mni_y_mm"])
    hippocampal_tail_y13 = float(focus["TI_1to3"]["hippocampal_p99_centroid_mni_y_mm"])
    hippocampal_tail_shift_mm = hippocampal_tail_y13 - hippocampal_tail_y11
    hippocampal_tail_boundary_margin11_mm = hippocampal_tail_y11 - (-18.5)
    quality = result["quality"]
    whole_valid_volume = conditions["TI_1to1"]["metrics"]["whole_gray_matter"]["TI_directional"]["volume_mm3"]
    target_valid_volume = conditions["TI_1to1"]["metrics"]["hippocampus"]["TI_directional"]["volume_mm3"]
    off_target_valid_volume = conditions["TI_1to1"]["metrics"]["off_target_gray_matter"]["TI_directional"]["volume_mm3"]
    hippocampal_domain_fraction_pct = 100 * target_valid_volume / whole_valid_volume
    capture11 = conditions["TI_1to1"]["focality"]["target_high_tail_capture_pct"]
    capture13 = conditions["TI_1to3"]["focality"]["target_high_tail_capture_pct"]
    capture_to_volume_reference11 = capture11 / hippocampal_domain_fraction_pct
    capture_to_volume_reference13 = capture13 / hippocampal_domain_fraction_pct
    focality_support = {row["condition"]: row for row in focality_rows}
    target_tail_volume11 = float(focality_support["TI_1to1"]["target_high_tail_volume_mm3"])
    target_tail_volume13 = float(focality_support["TI_1to3"]["target_high_tail_volume_mm3"])
    target_tail_elements11 = int(focality_support["TI_1to1"]["target_high_tail_element_count"])
    target_tail_elements13 = int(focality_support["TI_1to3"]["target_high_tail_element_count"])
    excluded_directional_elements = conditions["TI_1to1"]["metrics"]["whole_gray_matter"]["TI_directional"]["n_excluded_nonfinite_or_nonpositive"]
    excluded_directional_volume = quality["gray_volume_mm3"] - whole_valid_volume
    segment_coverage = result["implementation"]["roi"]["segment_coverage"]
    figure_map = {item["id"]: item for item in captions}
    roi_labels = {
        "hippocampus": "left hippocampus (target)",
        "right_hippocampus": "right hippocampus (contralateral)",
        "cortex_anterior": "anterior cortical sample",
        "cortex_middle": "middle cortical sample",
        "cortex_posterior": "posterior cortical sample",
        "off_target_gray_matter": "all off-target gray matter",
    }
    roi_rows = []
    for condition in ("TI_1to1", "TI_1to3"):
        for roi in ("hippocampus", "right_hippocampus", "cortex_anterior", "cortex_middle", "cortex_posterior", "off_target_gray_matter"):
            values = conditions[condition]["metrics"][roi]["TI_directional"]
            roi_rows.append(f"<tr><td>{condition.replace('_', ' ')}</td><td>{roi_labels[roi]}</td><td>{values['mean_v_per_m']:.4f}</td><td>{values['median_v_per_m']:.4f}</td><td>{values['p95_v_per_m']:.4f}</td><td>{values['volume_mm3']:.1f}</td></tr>")
    conclusion = (
        f"TI 1:1 的左海马方向投影 TI 高于 TI 1:3。"
        f"TI 1:3 使前段份额增加 {anterior_shift:+.1f} 个百分点，P99 重心前移 {hippocampal_tail_shift_mm:.2f} mm；"
        f"但{highest_segment_text}。TI 1:1 重心距前/中边界仅 {hippocampal_tail_boundary_margin11_mm:.2f} mm，"
        "因此不把这次位移解释为稳定的纵轴转移。"
    )
    right_hippocampus_note = (
        f'<p class="note">右海马采用与左海马相同的 Harvard-Oxford 图谱、非线性 subject-to-MNI 变换和最近邻采样链。'
        f"其 mean/median/P95 在 TI 1:1 为 {right11['mean_v_per_m']:.4f}/{right11['median_v_per_m']:.4f}/{right11['p95_v_per_m']:.4f} V/m，"
        f"在 TI 1:3 为 {right13['mean_v_per_m']:.4f}/{right13['median_v_per_m']:.4f}/{right13['p95_v_per_m']:.4f} V/m；"
        f"左/右海马的 mean/median/P95 比值分别为 {left_right_ratios11['mean']:.2f}/{left_right_ratios11['median']:.2f}/{left_right_ratios11['p95']:.2f} "
        f"和 {left_right_ratios13['mean']:.2f}/{left_right_ratios13['median']:.2f}/{left_right_ratios13['p95']:.2f}。"
        "全部靶外灰质包含右海马、其他深部灰质及皮层采样区，因此全局 target/off-target 比值不等同于侧化选择性。</p>"
    )
    report_id = f"{RUN_ID}-{sha256(RESULT_PATH)[:12]}"
    css = r"""
    :root{--ink:#18222d;--muted:#5e6a75;--line:#d8dee4;--paper:#fff;--wash:#f4f6f7;--blue:#0072b2;--orange:#d55e00;--green:#00866a;--max:1180px}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#eef1f3;color:var(--ink);font-family:Arial,'Microsoft YaHei',sans-serif;letter-spacing:0;line-height:1.75}a{color:#005f91;text-decoration-thickness:1px;text-underline-offset:3px}.shell{max-width:var(--max);margin:0 auto;background:var(--paper);min-height:100vh;box-shadow:0 0 32px rgba(24,34,45,.08)}header{padding:52px 64px 36px;border-bottom:1px solid var(--line)}.brand{font-size:13px;font-weight:700;color:var(--green);text-transform:uppercase}.eyebrow{margin-top:26px;color:var(--muted);font-size:14px}h1{font-size:38px;line-height:1.2;margin:8px 0 16px;max-width:900px;letter-spacing:0}header p{max-width:850px;margin:0;color:#3f4a54;font-size:17px}.meta{display:flex;gap:24px;flex-wrap:wrap;margin-top:24px;padding-top:18px;border-top:1px solid var(--line);font-size:13px;color:var(--muted)}nav{position:sticky;top:0;z-index:4;display:flex;gap:4px;overflow:auto;padding:10px 20px;background:rgba(255,255,255,.96);border-bottom:1px solid var(--line);backdrop-filter:blur(8px)}nav a{white-space:nowrap;padding:7px 10px;color:#34414c;text-decoration:none;font-size:13px;border-bottom:2px solid transparent}nav a:hover{border-color:var(--green)}main{padding:0 64px 72px}section{padding:48px 0;border-bottom:1px solid var(--line)}section:last-child{border-bottom:0}h2{font-size:25px;line-height:1.3;margin:0 0 18px}h3{font-size:18px;margin:30px 0 12px}.lead{font-size:17px;max-width:900px}.finding{border-left:4px solid var(--green);padding:18px 22px;background:#f1f7f5;font-size:17px}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line);margin:26px 0}.metric{background:#fff;padding:20px;min-height:126px}.metric b{display:block;font-size:28px;line-height:1.2;font-variant-numeric:tabular-nums}.metric span{display:block;color:var(--muted);font-size:13px;margin-top:8px}.protocol{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.protocol>div{border-top:3px solid var(--blue);padding:16px 0}.protocol>div:nth-child(2){border-color:var(--orange)}figure{margin:34px 0 48px}figure img{display:block;width:100%;height:auto;border:1px solid #cfd6dc;background:white}figcaption{display:block;margin-top:13px;font-size:14px;line-height:1.75}figcaption strong{display:block;font-size:15px}figcaption span{display:block;color:#35414b}figcaption small{display:block;color:var(--muted);margin-top:6px}.table-wrap{overflow:auto;border:1px solid var(--line)}table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}th,td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}th{background:#f3f5f6;font-weight:700}tr:last-child td{border-bottom:0}.note{padding:14px 18px;background:#fff7ed;border-left:4px solid var(--orange);font-size:14px}.downloads{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.downloads a{display:block;border:1px solid var(--line);padding:16px;text-decoration:none;color:var(--ink)}.downloads strong,.downloads span{display:block}.downloads span{color:var(--muted);font-size:13px;margin-top:4px}footer{padding:28px 64px;background:#1d2933;color:#dbe2e8;font-size:12px}.mono{font-family:Consolas,monospace;overflow-wrap:anywhere}@media(max-width:760px){header,main{padding-left:22px;padding-right:22px}header{padding-top:34px}h1{font-size:29px}.metrics{grid-template-columns:repeat(2,1fr)}.protocol,.downloads{grid-template-columns:1fr}section{padding:36px 0}footer{padding:24px 22px}}@media print{body{background:#fff}.shell{box-shadow:none;max-width:none}nav{display:none}header,main{padding-left:13mm;padding-right:13mm}main{padding-bottom:0}section{break-inside:auto}figure{break-inside:avoid}a{color:inherit}#delivery{break-before:page;padding-top:8mm;font-size:13px;line-height:1.55}#delivery h2{font-size:22px}#delivery h3{margin-top:6mm}.downloads{grid-template-columns:repeat(2,minmax(0,1fr));gap:2mm}.downloads a{padding:2mm}.downloads span{font-size:11px}.downloads a::after{content:attr(href);display:block;margin-top:1mm;font-size:8px;line-height:1.25;overflow-wrap:anywhere;color:#444}footer{padding:4mm 13mm;background:#fff;color:#333;border-top:1px solid #ccc}}
    """ + """
    .clinical-lead{font-size:18px;line-height:1.7;margin:0 0 18px}.clinical-lead strong{color:#006b56}
    .answer{padding:18px 22px;background:#f1f7f5;border-left:4px solid var(--green);margin:18px 0}.answer b{display:block;font-size:13px;color:#006b56;margin-bottom:5px}
    .annotation{margin:18px 0;border:1px solid #d8dee4;background:#f7f9fa}.annotation summary{cursor:pointer;padding:12px 16px;font-weight:700;color:#34414c}.annotation>div{padding:0 16px 14px;font-size:14px;color:#48545e}.annotation p{margin:8px 0}
    .term-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:20px 0}.term{border-top:2px solid #a9b5bd;padding:10px 0}.term b{display:block}.term span{display:block;color:var(--muted);font-size:14px}
    .reading-order{margin:20px 0;padding-left:22px}.reading-order li{margin:7px 0}
    @media(max-width:760px){nav{position:static}.term-grid{grid-template-columns:1fr}.clinical-lead{font-size:17px}}
    @media print{#field-definition{break-before:page;break-inside:avoid}#methods{font-size:13px;line-height:1.55}#methods h3{margin:5mm 0 2mm}#methods p{margin:0 0 3mm}.annotation{break-inside:avoid}.annotation>div{display:block!important}footer{padding:2mm 13mm;font-size:9px;line-height:1.3;break-inside:avoid}}
    """
    report_html = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(PROJECT_TITLE)}</title><meta name="report-id" content="{report_id}"><style>{css}</style></head><body><div class="shell">
    <header><div class="brand">QuanLan BrainScience · SimNIBS Research Delivery</div><div class="eyebrow">面向临床研究人员的正向电场仿真报告</div><h1>海马时间干涉刺激：两种电流配比的电场模拟</h1><p>本报告比较 TI 1:1 与 TI 1:3 两种刺激配比，重点观察左海马场强、海马前后方向的变化，以及皮层和其他非靶区的同步暴露。正文先给出临床研究者可直接阅读的结论，计算细节放在各节“专业注释”中。</p><div class="meta"><span>参考文献：Violante et al., 2023</span><span>SimNIBS {html.escape(result['software']['version'])}</span><span>单位：V/m</span><span class="mono">{report_id}</span></div></header>
    <nav><a href="#summary">先看结论</a><a href="#model">靶点</a><a href="#protocol">刺激设置</a><a href="#fields">电场分布</a><a href="#steering">海马前后变化</a><a href="#focality">非靶区暴露</a><a href="#localization">高值位置</a><a href="#field-definition">指标注释</a><a href="#methods">研究边界</a><a href="#delivery">数据下载</a></nav>
    <main><section id="summary"><h2>结果摘要</h2><p class="finding">{html.escape(conclusion)}</p><div class="metrics"><div class="metric"><b>{hip11['median_v_per_m']:.3f} V/m</b><span>TI 1:1 海马方向投影 TI 中位数</span></div><div class="metric"><b>{hip13['median_v_per_m']:.3f} V/m</b><span>TI 1:3 海马方向投影 TI 中位数</span></div><div class="metric"><b>{anterior_shift:+.1f} pp</b><span>1:3 相对 1:1 的前海马占比变化</span></div><div class="metric"><b>{ratio11:.2f} / {ratio13:.2f}</b><span>海马/全部靶外灰质中位数比（不代表深部选择性）</span></div></div><p class="note">本次结果来自真实 ernie MRI 头模型和真实 SimNIBS FEM 计算，但不是原论文的 MIDA 模型、原始参与者模型或客户 MRI。FT7-Fp2 与 TP7-TP8 是对论文连续头围坐标的 10-10 实施替代。论文数值只作为结构性基准，不用于数值一致性检验，也不支持临床疗效推断。</p></section>
    <section id="model"><h2>个体模型与左海马靶点</h2><p class="lead">ernie 灰质四面体中心经 SimNIBS 非线性变换到 MNI 空间后，以最近邻方式采样 Harvard-Oxford 25% 最大概率图谱中的左海马标签。海马按论文整数切片标签沿 MNI Y 轴分为前段（−18 至 −4 mm）、中段（−29 至 −19 mm）和后段（−40 至 −30 mm）；连续四面体中心使用相邻区间中点作为分类边界。</p>{figure_html(figure_map['fig01'])}</section>
    <section id="protocol"><h2>刺激方案</h2><div class="protocol"><div><h3>载波回路 E1</h3><p>e1 FT7 为正极，e2 Fp2 为负极。论文建模电流为 1 mA peak-to-baseline；TI 1:3 时缩放为 0.5 mA。</p></div><div><h3>载波回路 E2</h3><p>e3 TP7 为正极，e4 TP8 为负极。论文建模电流为 1 mA；TI 1:3 时缩放为 1.5 mA。</p></div></div><p>两回路载波频率分别为 2.005 kHz 和 2.000 kHz，差频 5 Hz。准静态 FEM 只计算空间电场；载波频率不改变本次线性空间场解。</p>{figure_html(figure_map['fig02'])}{figure_html(figure_map['fig03'])}</section>
    <section id="fields"><h2>方向投影 TI 与 TImax</h2><p class="lead">本报告以沿 DTI 主方向投影的包络场为主指标，对应 Violante 2023 结果部分所述沿 DTI 推导主纤维轴计算包络调制幅值和绝对幅值的方法。报告同时给出 SimNIBS TImax，便于软件互操作和方向无关的上限描述；两种指标回答的问题不同。</p>{figure_html(figure_map['fig04'])}{figure_html(figure_map['fig05'])}</section>
    <section id="steering"><h2>海马纵轴上的场强与移动</h2><p>绝对场强和相对空间分配分开报告。论文的个体模型图 2c 使用归一化相对暴露，因此不能与 V/m 直接混为一张数值轴。本次 1:3 让前段相对份额增加，但没有在 ernie 替代蒙太奇中形成论文所示的前段最大值。</p><p class="note">图 6 与图 9 回答不同问题：分段中位数份额衡量前、中、后整段的典型场强，P99 重心则定位海马内场强最高约 1% 体积。按论文分段边界，两条件的 P99 重心在当前离散结果中均归入前段，并由 MNI Y {hippocampal_tail_y11:.2f} mm 向前移动至 {hippocampal_tail_y13:.2f} mm；后段的分段中位数份额仍为最高。TI 1:1 重心距前/中边界只有 {hippocampal_tail_boundary_margin11_mm:.2f} mm，而本例未量化模型不确定度，因此该分段归属和 1.65 mm 差值都只能描述当前模型，不能认定为稳健的峰值类别或 steering 转变。</p>{figure_html(figure_map['fig06'])}</section>
    <section id="focality"><h2>海马、蒙太奇相关皮层与靶外暴露</h2><p>海马场强较高并不自动等于聚焦。报告同时比较三个以蒙太奇位置构造、半径 10 mm 的皮层球形采样区、全部靶外灰质，以及全灰质 P99 高值尾部有多少体积落在海马内。Target/off-target 比值和 P99 高值尾部是本交付包新增的描述性分析，不是 Violante 等人的原始主要终点。</p><p class="note">局部皮层采样区并非一致低于海马。按图 7 展示的 median，TI 1:1 下后部采样区略高于海马（0.0737 vs 0.0697 V/m）；TI 1:3 下中部和后部采样区均高于海马（0.0478、0.0430 vs 0.0383 V/m）。按 mean 和 P95，TI 1:1 下前部采样区两项均高于海马，中部采样区的 P95 也较高；TI 1:3 下前部和中部采样区两项均高于海马，后部采样区两项均较低。因此，海马相对全部靶外灰质的 median 比值大于 1，不等同于深部选择性，也不能替代局部表层暴露评估。</p>{figure_html(figure_map['fig07'])}{figure_html(figure_map['fig08'])}<h3>可复算区域统计</h3><div class="table-wrap"><table><thead><tr><th>Condition</th><th>ROI</th><th>Mean (V/m)</th><th>Median (V/m)</th><th>P95 (V/m)</th><th>Volume (mm³)</th></tr></thead><tbody>{''.join(roi_rows)}</tbody></table></div></section>
    <section id="localization"><h2>海马内高值位置与皮层表面暴露</h2><p>海马内高值位置和全脑表面暴露采用不同空间尺度展示。图 9 仅在左海马 ROI 内定位 P99 高值重心与单单元峰值，用于判断高值尾部沿海马纵轴的位置；图 10 将方向投影 TI 映射到灰质表面，用于识别表层热点及其与电极蒙太奇的空间关系。两图均为描述性空间分析，不代表神经激活范围。</p>{figure_html(figure_map['fig09'])}{figure_html(figure_map['fig10'])}</section>
    <section id="field-definition"><h2>电场定义与幅值约定</h2><p>下列定义直接对应本次 SimNIBS 4.6.0 实现。E1、E2 是按各条件声明的 peak-to-baseline 电流缩放后的载波电场向量；所有结果单位为 V/m。报告中的 TI 数值是包络调制幅度，不是 RMS、单个载波峰值，也不是 |E1|+|E2|。</p><h3>沿 DTI 主方向的包络</h3><p>令 <em>u</em> 为单位 DTI 主特征向量，<em>a</em> = E1·<em>u</em>、<em>b</em> = E2·<em>u</em>。方向投影 TI 使用 SimNIBS <span class="mono">get_dirTI</span>：</p><p class="formula"><strong>A<sub>dir</sub> = ||a+b| − |a−b||</strong></p><h3>方向无关的最大包络</h3><p>TImax 使用 SimNIBS <span class="mono">get_maxTI</span>（Grossman 等，2017）。先交换两载波场使 |E1| ≥ |E2|，必要时反转 E2 使夹角 α 为锐角。若 |E2| ≤ |E1|cosα，则 <strong>A<sub>max</sub> = 2|E2|</strong>；否则：</p><p class="formula"><strong>A<sub>max</sub> = 2|E2 × (E1−E2)| / |E1−E2|</strong></p><p>两项公式均在独立实现中逐单元复算；两条件与 SimNIBS 输出的最大绝对差均为 0 V/m，验收容差为 1×10<sup>−12</sup> V/m。本报告以方向投影 TI 为主指标，复现 Violante 2023 沿 DTI 推导主纤维轴计算包络场的分析口径；TImax 是方向无关的补充指标，二者不能互换。</p></section>
    <section id="methods"><h2>方法与解释边界</h2><h3>头模型与有限元求解</h3><p>采用 SimNIBS 官方 ernie 示例受试者的 CHARM 头模型。四个 20 mm 圆电极在同一电极化网格中定义；两次载波求解只改变四通道电流向量，使 E1 和 E2 可以逐单元组合。求解器为 SimNIBS hypre，各向同性组织电导率详见 Excel 的 Conductivities 工作表。本次灰质分析包含 {quality['gray_tetrahedra']:,} 个四面体，总体积 {quality['gray_volume_mm3']:.1f} mm³；两组载波网格逐节点、逐单元一致。</p><h3>DTI 方向与 TI 公式</h3><p>DTI 张量按 FSL 分量顺序读取，并使用 SimNIBS <span class="mono">cond_utils</span> 的坐标变换规则旋转到网格世界坐标，再提取主特征向量。有效 DTI 方向覆盖 {100*quality['dti_valid_gray_fraction']:.2f}% 的灰质单元；其余单元记为缺失，不写成零。方向投影 TI 和 TImax 均使用独立公式逐单元复算，两条件最大绝对误差均为 0 V/m（容差 1×10<sup>−12</sup> V/m）。</p><h3>ROI 与统计口径</h3><p>左海马来自 Harvard-Oxford 25% 最大概率图谱。论文报告的三个 MNI Y 范围覆盖本例海马体积的 {100*segment_coverage['assigned_fraction']:.2f}%，未覆盖部分不参与三段归一化。三个皮层对照是以 FT7、TP7 及二者中点附近灰质为中心、半径 10 mm 的球形采样区，不是解剖图谱分区。区域 mean 按四面体体积加权；median 与 P95 来自体积加权经验分布。</p><p>海马分段相对份额定义为该段方向投影 TI 的体积加权中位数除以前、中、后三段中位数之和；前段份额由 TI 1:1 的 {100*share11['hippocampus_anterior']:.2f}% 变为 TI 1:3 的 {100*share13['hippocampus_anterior']:.2f}%。论文图 2c 的报告值只作为前、中、后分布模式的结构性参照，不假定与本例归一化定义完全相同，也不用于数值一致性检验。海马内 P99 重心按同一分段边界作描述性归类；TI 1:1 重心距前/中边界仅 {hippocampal_tail_boundary_margin11_mm:.2f} mm，在未量化网格、电极与分割不确定度的情况下，不能将该分段归属视为稳健分类。</p><p>P99 高值尾部对每个条件分别在有效全灰质方向投影 TI 分布内按四面体体积加权计算；TI 1:1 与 TI 1:3 的阈值分别为 {p99_threshold11:.4f} 和 {p99_threshold13:.4f} V/m。海马占有效方向投影分析域体积的 {hippocampal_domain_fraction_pct:.2f}%，在图 8 中仅作为空间占比参照；TI 1:1 与 TI 1:3 的高值尾部捕获比例分别为该参照的 {capture_to_volume_reference11:.1f} 倍和 {capture_to_volume_reference13:.3f} 倍。相应海马内高值尾部为 TI 1:1 {target_tail_volume11:.2f} mm³（{target_tail_elements11} 个四面体）和 TI 1:3 {target_tail_volume13:.2f} mm³（{target_tail_elements13} 个四面体）；后者体积极小，对网格离散敏感，只作量级描述。该参照不假定高值尾部在全灰质均匀分布，也不表示统计显著性。各条件比例描述自身高值尾部落入海马的空间份额，不是共用绝对阈值下的幅值比较，也不是神经激活阈值；这与图 3 和图 10 为便于显示而采用的跨面板联合 P99 色标上限不同。</p><p>“全部靶外灰质”定义为灰质四面体中排除海马 ROI 后，方向投影 TI 有限且单元体积为正的部分；三个皮层采样区不另行排除。有效方向投影分析域体积为 {whole_valid_volume:.2f} mm³，其中海马 {target_valid_volume:.2f} mm³、靶外灰质 {off_target_valid_volume:.2f} mm³，两者之和与有效分析域闭合。原始灰质总体积与有效分析域相差 {excluded_directional_volume:.2f} mm³，对应 {excluded_directional_elements:,} 个缺少有效 DTI 方向的单元。</p><h3>已验证与未评估内容</h3><p>已验证网格一致性、电流配置平衡、DTI 方向有效率、TI 公式独立复算和输入输出校验。SimNIBS 日志中的最大 5.3% 为内部参考通道基场的电流校准估计，不是设备实测误差，且本项目未预先规定其验收阈值。本示例未进行网格收敛、电极位置扰动、组织电导率敏感性或跨受试者稳健性分析；这些项目在患者个体化研究或正式组水平发表中应另行完成。</p><h3>适用范围</h3><p>本报告支持比较所声明模型和参数下的电场分布。它不验证神经激活、安全剂量、治疗效果或个体处方。ernie 是单个示例受试者，因此没有组水平 p 值或置信区间。当前电极为标准 10-10 位置替代，不是原论文连续头围坐标，也不是客户 64 通道帽的实测配准结果。</p></section>
    <section id="delivery"><h2>论文重绘与二次分析文件</h2><p>每张图同时提供 300 dpi PNG、SVG、PDF及中英文图注；定量图另附支撑 CSV，空间场图可从 HDF5、NIfTI 和 MSH 复算。Excel 汇总表按图件和统计口径组织；HDF5 保存灰质单元中心、体积、ROI、DTI 方向及两条件派生场；MSH 和 NIfTI 供 SimNIBS、Gmsh、Python 或影像软件继续分析。</p><div class="downloads"><a href="tables/violante2023_ti_reproduction_results.xlsx"><strong>Excel 结果工作簿</strong><span>区域统计、聚焦性、论文基准、图件索引</span></a><a href="raw/violante2023_reproduction_fields.h5"><strong>HDF5 中间数据</strong><span>灰质逐单元矢量场与派生场</span></a><a href="raw/violante2023_reproduction_fields.msh"><strong>SimNIBS / Gmsh 网格</strong><span>E1、E2、方向投影 TI 与 TImax</span></a><a href="packages/figure_support_csv.zip"><strong>图件支撑 CSV</strong><span>逐图数据、ROI 统计与电极坐标</span></a><a href="packages/nifti_fields.zip"><strong>NIfTI 空间场</strong><span>15 份场图与 ROI 掩膜，供影像软件复算</span></a><a href="manifest.json"><strong>文件清单与校验值</strong><span>交付文件路径、大小与 SHA-256</span></a></div><h3>参考文献</h3><p>Violante IR et al. <em>Non-invasive temporal interference electrical stimulation of the human hippocampus.</em> Nature Neuroscience. 2023;26:1994–2004. doi:10.1038/s41593-023-01456-8.</p><p>Grossman N et al. <em>Noninvasive Deep Brain Stimulation via Temporally Interfering Electric Fields.</em> Cell. 2017;169:1029–1041.e16. doi:10.1016/j.cell.2017.05.024.</p></section></main>
    <footer>本报告由可追溯的本地 SimNIBS 计算结果生成。报告 ID：<span class="mono">{report_id}</span>。文件校验值见 manifest.json。</footer></div></body></html>"""
    old_dti_text = f"有效 DTI 方向覆盖 {100*quality['dti_valid_gray_fraction']:.2f}% 的灰质单元；其余单元记为缺失，不写成零。方向投影 TI 和 TImax 均使用独立公式逐单元复算"
    new_dti_text = f"有限的 DTI 方向向量覆盖 {100*quality['dti_valid_gray_fraction']:.2f}% 的灰质单元；其余单元记为缺失，不写成零。该比例只表示方向向量存在且数值有限，不表示方向估计可靠。本例未设置 FA 或特征值各向异性阈值；当张量各向异性较低时，主特征向量的定向可能不稳定，方向投影 TI 也会继承这项未量化的不确定性。方向投影 TI 和 TImax 均使用独立公式逐单元复算"
    report_html = report_html.replace(old_dti_text, new_dti_text, 1)
    report_html = report_html.replace("TI 1:1 海马方向投影 TI 中位数", "TI 1:1 左海马方向投影 TI 中位数", 1)
    report_html = report_html.replace("TI 1:3 海马方向投影 TI 中位数", "TI 1:3 左海马方向投影 TI 中位数", 1)
    report_html = report_html.replace("海马/全部靶外灰质中位数比（不代表深部选择性）", "左海马/全部靶外灰质中位数比（不代表深部选择性）", 1)
    report_html = report_html.replace(
        "报告同时比较三个以蒙太奇位置构造、半径 10 mm 的皮层球形采样区、全部靶外灰质",
        "报告同时比较对侧右海马、三个以蒙太奇位置构造且半径为 10 mm 的皮层球形采样区、全部靶外灰质",
        1,
    )
    report_html = report_html.replace(
        '<p class="note">局部皮层采样区并非一致低于海马。',
        right_hippocampus_note + '<p class="note">局部皮层采样区并非一致低于海马。',
        1,
    )
    report_html = report_html.replace("15 份场图与 ROI 掩膜", "16 份场图与 ROI 掩膜", 1)
    report_html = report_html.replace(
        "每张图同时提供 300 dpi PNG、SVG、PDF及中英文图注；",
        "每张图同时提供 300 dpi PNG、SVG、PDF及中英文图注；冻结的生成脚本、依赖版本和数据/代码可用性声明见 reproducibility 目录；",
        1,
    )
    report_html = report_html.replace(
        '<a href="manifest.json"><strong>文件清单与校验值</strong><span>交付文件路径、大小与 SHA-256</span></a></div>',
        '<a href="manifest.json"><strong>文件清单与校验值</strong><span>交付文件路径、大小与 SHA-256</span></a><a href="reproducibility/DATA_AND_CODE_AVAILABILITY.md"><strong>数据与代码可用性</strong><span>冻结脚本、依赖版本与复现边界</span></a></div>',
        1,
    )
    report_html = report_html.replace("按论文分段边界，两条件的 P99 重心", "按连续四面体中心的中点边界，两条件的 P99 重心", 1)
    report_html = report_html.replace(
        "左海马来自 Harvard-Oxford 25% 最大概率图谱。论文报告的三个 MNI Y 范围覆盖本例海马体积的",
        "灰质四面体中心先由 SimNIBS 4.6.0 transformations.subject2mni_coords 按默认 nonl 类型，经 m2m_ernie/toMNI/Conform2MNI_nonl.nii.gz 从 subject conform 非线性映射到 MNI；随后在这些 MNI 坐标以最近邻方式采样 Harvard-Oxford 25% 最大概率图谱的左、右海马标签，没有另行把 atlas 重采样回 subject。论文报告的三个 MNI Y 范围覆盖本例左海马体积的",
        1,
    )
    report_html = report_html.replace(
        "已验证网格一致性、电流配置平衡、DTI 方向有效率、TI 公式独立复算和输入输出校验。",
        "已验证网格一致性、电流配置平衡、有限 DTI 方向向量覆盖率、TI 公式独立复算和输入输出校验。",
        1,
    ).replace(
        "本示例未进行网格收敛、电极位置扰动、组织电导率敏感性或跨受试者稳健性分析；",
        "本示例未进行网格收敛、电极位置扰动、组织电导率敏感性、DTI 主方向定向不确定性、非线性 MNI 配准不确定性或跨受试者稳健性分析；",
        1,
    )

    def replace_section(document: str, section_id: str, replacement: str) -> str:
        updated, count = re.subn(
            rf'<section id="{section_id}">.*?</section>',
            replacement,
            document,
            count=1,
            flags=re.DOTALL,
        )
        if count != 1:
            raise RuntimeError(f"Could not compact report section: {section_id}")
        return updated

    compact_sections = {
        "summary": f'''<section id="summary"><h2>先看结论</h2><p class="clinical-lead"><strong>这次模拟没有显示 TI 1:3 优于 TI 1:1。</strong>TI 1:3 使左海马前部所占比例略有增加，但同时降低了左海马整体场强，而且高值区域仍主要位于后部。</p><div class="metrics"><div class="metric"><b>{hip11['median_v_per_m']:.3f} V/m</b><span>TI 1:1 左海马典型场强（中位数）</span></div><div class="metric"><b>{hip13['median_v_per_m']:.3f} V/m</b><span>TI 1:3 左海马典型场强（中位数）</span></div><div class="metric"><b>{anterior_shift:+.1f} 个百分点</b><span>改用 1:3 后，前部场强份额的变化</span></div><div class="metric"><b>{ratio11:.2f} / {ratio13:.2f}</b><span>左海马与其他灰质的中位数比值（1:1 / 1:3）</span></div></div><div class="answer"><b>怎样理解</b>在这个单一示例头模型中，1:1 配比给左海马带来的整体场强更高；1:3 只表现出轻微的前移趋势，证据不足以说明刺激中心发生了稳定转移。两种配比都存在明显的皮层和其他非靶区暴露。</div><h3>阅读本报告时只需先认识四个词</h3><div class="term-grid"><div class="term"><b>中位数</b><span>代表一个区域内较典型的场强，比单个最高值更稳定。</span></div><div class="term"><b>P95</b><span>区域内较高的一档场强，95% 的体积不超过它。</span></div><div class="term"><b>P99 重心</b><span>场强最高约 1% 体积的中心位置，用来描述高值区在哪里。</span></div><div class="term"><b>方向投影 TI</b><span>沿局部主要纤维方向计算的调制场，本报告的主要指标。</span></div></div><details class="annotation" open><summary>专业注释：研究对象与解释边界</summary><div><p>模型为 SimNIBS 官方 ernie 单受试者。电极采用 FT7-Fp2 和 TP7-TP8，属于对论文连续头围坐标的 10-10 实施替代。不是原论文的 MIDA 模型、原始参与者模型或客户 MRI。</p><p>本报告是正向电场模拟，只描述给定模型和参数下的电场分布，不直接代表神经激活、安全剂量、治疗效果或个体处方。</p></div></details></section>''',
        "model": f'''<section id="model"><h2>模拟靶点：左海马</h2><p class="clinical-lead"><strong>本次分析把左海马作为主要靶区，</strong>并沿海马长轴分成前、中、后三段，观察不同电流配比是否把高值区向前部移动。</p><div class="answer"><b>图 1 怎么看</b>绿色区域是本次计算采用的左海马范围。后续所有“海马场强”和“前后移动”都基于这个区域。</div><details class="annotation" open><summary>专业注释：海马分区方法</summary><div><p>灰质四面体中心经非线性变换到 MNI 空间，以最近邻方式采样 Harvard-Oxford 25% 图谱的左海马标签。前、中、后段分别为 MNI Y −18 至 −4、−29 至 −19、−40 至 −30 mm；边界取相邻区间中点。</p></div></details>{figure_html(figure_map['fig01'])}</section>''',
        "protocol": f'''<section id="protocol"><h2>比较的两种刺激设置</h2><p class="clinical-lead">两种设置使用相同的四个电极。<strong>TI 1:1 让两组回路强度相同；TI 1:3 减弱第一组、增强第二组，</strong>目的是观察这种配比变化能否把海马内的场分布向前部引导。</p><div class="protocol"><div><h3>TI 1:1</h3><p>E1 与 E2 均按 1 mA 建模。</p></div><div><h3>TI 1:3</h3><p>E1 按 0.5 mA、E2 按 1.5 mA 建模。</p></div></div><details class="annotation" open><summary>专业注释：电极与频率</summary><div><p>E1 为 FT7（正极）至 Fp2（负极），E2 为 TP7（正极）至 TP8（负极）。两回路载波频率分别为 2.005 kHz 和 2.000 kHz，差频为 5 Hz。电流幅值采用 peak-to-baseline 约定。</p><p>准静态有限元模型计算空间电场；在本次线性求解中，载波频率本身不改变空间场分布。</p></div></details>{figure_html(figure_map['fig02'])}{figure_html(figure_map['fig03'])}</section>''',
        "fields": f'''<section id="fields"><h2>全脑电场分布</h2><p class="clinical-lead"><strong>图 4 和图 5 用同一色标，可直接比较两种配比。</strong>整体上，TI 1:3 的左海马场强低于 TI 1:1；同时，两种配比都可见海马之外的电场分布。</p><div class="answer"><b>图 4、图 5 怎么看</b>优先看每张图上排的“方向投影 TI”，它是本报告的主要结果。颜色越接近色标高端，表示该位置的调制场越强。</div><details class="annotation" open><summary>专业注释：方向投影 TI 与 TImax</summary><div><p>方向投影 TI 沿 DTI 主方向计算，更接近本报告复现的论文分析口径。TImax 是不限定方向时可能达到的最大包络幅度，用作补充。两者含义不同，不能互换。</p></div></details>{figure_html(figure_map['fig04'])}{figure_html(figure_map['fig05'])}</section>''',
        "steering": f'''<section id="steering"><h2>是否向前海马移动</h2><p class="clinical-lead"><strong>有轻微前移迹象，但不足以认定发生了稳定转移。</strong>TI 1:3 将前段份额从 {100*share11['hippocampus_anterior']:.2f}% 提高到 {100*share13['hippocampus_anterior']:.2f}%，增加 {anterior_shift:+.1f} 个百分点；两种配比下，占比最高的仍是后段。</p><div class="answer"><b>临床研究含义</b>改变电流配比确实改变了海马内的相对分布，但变化幅度小，而且没有把主要场强从后段稳定地转到前段。</div><details class="annotation" open><summary>专业注释：为什么不能下“成功前移”的结论</summary><div><p>图 6 比较前、中、后三段的体积加权中位数。图 9 定位海马内场强最高约 1% 体积的 P99 重心。该重心由 MNI Y {hippocampal_tail_y11:.2f} mm 前移至 {hippocampal_tail_y13:.2f} mm。</p><p>TI 1:1 重心距前/中边界仅 {hippocampal_tail_boundary_margin11_mm:.2f} mm，且本例未量化模型不确定度，因此 1.65 mm 的位移不能视为稳健分类。论文图 2c 的相对暴露只作分布参照，不与本例 V/m 直接比较。</p></div></details>{figure_html(figure_map['fig06'])}</section>''',
        "focality": f'''<section id="focality"><h2>海马以外的暴露</h2><p class="clinical-lead"><strong>左海马场强高于全体靶外灰质的中位水平，但并不代表刺激只集中在海马。</strong>部分局部皮层采样区的场强与海马相当或更高；海马与全部靶外灰质的 P95 基本相当。</p><div class="answer"><b>图 7、图 8 怎么看</b>图 7 比较左海马与三个局部皮层采样区的典型场强。图 8 同时比较左、右海马、全部靶外灰质，以及全脑最高场强区域有多少落在左海马内。</div><details class="annotation" open><summary>专业注释：采样区、比值与高值尾部</summary><div><p>三个皮层区域均为半径 10 mm 的球形采样区，不是解剖图谱分区。右海马采用与左海马相同的 Harvard-Oxford 图谱、非线性 subject-to-MNI 变换和最近邻采样链。</p><p>右海马（right hippocampus (contralateral)）的 mean/median/P95 为 TI 1:1 {right11['mean_v_per_m']:.4f}/{right11['median_v_per_m']:.4f}/{right11['p95_v_per_m']:.4f} V/m，TI 1:3 {right13['mean_v_per_m']:.4f}/{right13['median_v_per_m']:.4f}/{right13['p95_v_per_m']:.4f} V/m。全部靶外灰质包含右海马、其他深部灰质及皮层采样区；全局 target/off-target 比值不等同于侧化选择性。</p><p>mean/P95 比值由 {mean_ratio11:.2f}/{p95_ratio11:.2f} 变为 {mean_ratio13:.2f}/{p95_ratio13:.2f}。左海马占有效方向投影分析域体积的 {hippocampal_domain_fraction_pct:.2f}%；TI 1:3 海马内高值尾部为 {target_tail_volume13:.2f} mm³（{target_tail_elements13} 个四面体），对网格离散敏感，只作量级描述。Target/off-target 和 P99 是本报告新增的描述性指标。</p></div></details>{figure_html(figure_map['fig07'])}{figure_html(figure_map['fig08'])}<h3>完整区域统计</h3><p>下表供复核和二次分析。正文判断优先采用中位数，同时结合 mean 与 P95 查看局部高值。</p><div class="table-wrap"><table><thead><tr><th>刺激设置</th><th>分析区域</th><th>平均值 (V/m)</th><th>中位数 (V/m)</th><th>P95 (V/m)</th><th>体积 (mm³)</th></tr></thead><tbody>{''.join(roi_rows)}</tbody></table></div></section>''',
        "localization": f'''<section id="localization"><h2>高值区在哪里</h2><p class="clinical-lead"><strong>海马内位置与皮层表面分布需要分开看。</strong>图 9 回答左海马内高值区位于前、中还是后部；图 10 显示左侧灰质表面的电场热点。</p><div class="answer"><b>结论</b>TI 1:3 的海马内高值重心较 TI 1:1 向前 1.65 mm，但该位移靠近分段边界。皮层表面仍存在较广泛暴露。</div><details class="annotation" open><summary>专业注释：空间指标</summary><div><p>图 9 同时给出左海马内 P99 重心和单单元峰值。P99 重心比单个峰值更能代表高值区域的位置。图 10 是表面可视化，不能替代深部海马切面和 ROI 定量。</p></div></details>{figure_html(figure_map['fig09'])}{figure_html(figure_map['fig10'])}</section>''',
        "field-definition": '''<section id="field-definition"><h2>指标怎么理解</h2><p class="clinical-lead">正文中的数值表示<strong>两组高频电场叠加后形成的低频调制包络强度</strong>，单位为 V/m。它是物理场指标，不是神经元放电强度，也不是治疗剂量。</p><div class="term-grid"><div class="term"><b>方向投影 TI</b><span>只计算沿局部主要纤维方向的调制场，是正文主要指标。</span></div><div class="term"><b>TImax</b><span>不限定方向时的最大包络幅度，用于补充观察。</span></div></div><details class="annotation" open><summary>专业注释：幅值约定与计算公式</summary><div><p>E1、E2 是按各条件声明的 peak-to-baseline 电流缩放后的载波电场向量。报告中的 TI 数值是包络调制幅度，不是 RMS、单个载波峰值，也不是 |E1|+|E2|。</p><p>令 <em>u</em> 为单位 DTI 主特征向量，<em>a</em> = E1·<em>u</em>、<em>b</em> = E2·<em>u</em>。方向投影 TI 使用 SimNIBS <span class="mono">get_dirTI</span>：</p><p class="formula"><strong>A<sub>dir</sub> = ||a+b| − |a−b||</strong></p><p>TImax 使用 SimNIBS <span class="mono">get_maxTI</span>（Grossman 等，2017）。先交换两载波场使 |E1| ≥ |E2|，必要时反转 E2 使夹角 α 为锐角。若 |E2| ≤ |E1|cosα，则 <strong>A<sub>max</sub> = 2|E2|</strong>；否则：</p><p class="formula"><strong>A<sub>max</sub> = 2|E2 × (E1−E2)| / |E1−E2|</strong></p><p>两项公式均逐单元独立复算，与 SimNIBS 输出的最大绝对差为 0 V/m；验收容差为 1×10<sup>−12</sup> V/m。</p></div></details></section>''',
        "methods": f'''<section id="methods"><h2>这份报告能说明什么</h2><p class="clinical-lead"><strong>它能比较两种刺激设置在这个头模型中的电场分布，不能直接回答疗效或安全性。</strong></p><ul class="reading-order"><li>可以回答：哪种设置在左海马产生更高场强，高值区位于海马何处，皮层和其他非靶区是否同时暴露。</li><li>不能回答：是否引起神经激活、是否达到治疗剂量、对患者是否有效或安全。</li><li>不能外推：本例只有一个官方示例头模型，没有患者队列、组水平统计或个体差异分析。</li></ul><details class="annotation" open><summary>专业注释：模型、ROI 与统计</summary><div><p>采用 SimNIBS ernie CHARM 头模型、四个 20 mm 圆电极和 hypre 求解器。两次载波求解共用网格，只改变四通道电流向量。灰质分析包括 {quality['gray_tetrahedra']:,} 个四面体，总体积 {quality['gray_volume_mm3']:.1f} mm³。</p><p>灰质四面体中心由 SimNIBS 4.6.0 <span class="mono">subject2mni_coords</span> 经 <span class="mono">Conform2MNI_nonl.nii.gz</span> 变换到 MNI，再以最近邻方式采样 Harvard-Oxford 左、右海马标签。区域 mean、median 和 P95 均按四面体体积加权；皮层对照为 FT7、TP7 及中点附近的 10 mm 球形采样区。</p></div></details><details class="annotation" open><summary>专业注释：质量控制与尚未评估的误差</summary><div><p>有限的 DTI 方向向量覆盖 {100*quality['dti_valid_gray_fraction']:.2f}% 的灰质单元；其余单元记为缺失，不写成零。该比例只表示方向向量存在且数值有限，不表示方向估计可靠。未设置 FA 或特征值各向异性阈值。方向投影 TI 与 TImax 已逐单元独立复算，最大误差为 0 V/m。</p><p>本示例未进行网格收敛、电极位置扰动、组织电导率敏感性、DTI 主方向定向不确定性、非线性 MNI 配准不确定性或跨受试者稳健性分析。它比较该模型和参数下的场分布，不用于推断神经激活、安全剂量、治疗效果或个体处方。</p></div></details></section>''',
        "delivery": '''<section id="delivery"><h2>图表与数据</h2><p>每张图提供 300 dpi PNG、SVG、PDF、中英文图注和支撑 CSV。HDF5、MSH、16 份场图与 ROI 掩膜、Excel 结果表、冻结脚本和依赖版本均随包提供。</p><div class="downloads"><a href="tables/violante2023_ti_reproduction_results.xlsx"><strong>Excel 结果工作簿</strong><span>区域统计、聚焦性、论文基准、图件索引</span></a><a href="raw/violante2023_reproduction_fields.h5"><strong>HDF5 中间数据</strong><span>灰质逐单元矢量场与派生场</span></a><a href="raw/violante2023_reproduction_fields.msh"><strong>SimNIBS / Gmsh 网格</strong><span>E1、E2、方向投影 TI 与 TImax</span></a><a href="packages/figure_support_csv.zip"><strong>图件支撑 CSV</strong><span>逐图数据、ROI 统计与电极坐标</span></a><a href="packages/nifti_fields.zip"><strong>NIfTI 空间场</strong><span>16 份场图与 ROI 掩膜</span></a><a href="manifest.json"><strong>文件清单与校验值</strong><span>交付文件路径、大小与 SHA-256</span></a><a href="reproducibility/DATA_AND_CODE_AVAILABILITY.md"><strong>数据与代码可用性</strong><span>冻结脚本、依赖版本与复现边界</span></a></div><h3>参考文献</h3><p>Violante IR et al. <em>Non-invasive temporal interference electrical stimulation of the human hippocampus.</em> Nature Neuroscience. 2023;26:1994–2004. doi:10.1038/s41593-023-01456-8.</p><p>Grossman N et al. <em>Noninvasive Deep Brain Stimulation via Temporally Interfering Electric Fields.</em> Cell. 2017;169:1029–1041.e16. doi:10.1016/j.cell.2017.05.024.</p></section>''',
    }
    for section_id, replacement in compact_sections.items():
        report_html = replace_section(report_html, section_id, replacement)
    report_html = report_html.replace(
        f"mean/P95 比值由 {mean_ratio11:.2f}/{p95_ratio11:.2f} 变为 {mean_ratio13:.2f}/{p95_ratio13:.2f}。",
        f"mean/P95 比值同时由 {mean_ratio11:.2f}/{p95_ratio11:.2f} 变为 {mean_ratio13:.2f}/{p95_ratio13:.2f}，海马与全部靶外灰质的 P95 基本相当。",
        1,
    ).replace(
        f"左海马占有效方向投影分析域体积的 {hippocampal_domain_fraction_pct:.2f}%；",
        f"左海马占有效方向投影分析域体积的 {hippocampal_domain_fraction_pct:.2f}%，仅作为空间占比参照；",
        1,
    ).replace(
        "Target/off-target 和 P99 是本报告新增的描述性指标。</p></div></details>",
        "图 7 的柱高仅表示海马及三个蒙太奇相关皮层采样区的体积加权中位数，不能仅凭本图中位数判断表层暴露。Target/off-target 和 P99 是本报告新增的描述性指标。</p></div></details>",
        1,
    ).replace(
        "论文图 2c 的相对暴露只作分布参照，不与本例 V/m 直接比较。",
        "Violante 2023 图 2c 报告 16 名参与者个体 MRI 模型的相对海马暴露；本报告复现 Violante 2023 沿 DTI 推导主纤维轴计算包络场的分析口径。论文图 2c 的相对暴露只作分布参照，不与本例 V/m 直接比较。",
        1,
    )

    clinical_roi_labels = {
        "hippocampus": "左海马（靶区）",
        "right_hippocampus": "右海马",
        "cortex_anterior": "前部皮层采样区",
        "cortex_middle": "中部皮层采样区",
        "cortex_posterior": "后部皮层采样区",
        "off_target_gray_matter": "全部非靶区灰质",
    }
    clinical_roi_rows = []
    for condition in ("TI_1to1", "TI_1to3"):
        condition_label = "TI 1:1" if condition == "TI_1to1" else "TI 1:3"
        for roi in ("hippocampus", "right_hippocampus", "cortex_anterior", "cortex_middle", "cortex_posterior", "off_target_gray_matter"):
            values = conditions[condition]["metrics"][roi]["TI_directional"]
            clinical_roi_rows.append(
                f"<tr><td>{condition_label}</td><td>{clinical_roi_labels[roi]}</td>"
                f"<td>{values['mean_v_per_m']:.4f}</td><td>{values['median_v_per_m']:.4f}</td>"
                f"<td>{values['p95_v_per_m']:.4f}</td><td>{values['volume_mm3']:.1f}</td></tr>"
            )

    clinical_main = f'''<main>
    <section id="summary"><h2>一、研究目的与主要结论</h2><p class="clinical-lead">本次模拟比较两种电流配比，观察它们在左海马产生的电场强度、海马内高值区的位置，以及海马以外的电场分布。</p><ol class="reading-order"><li><strong>左海马整体场强：</strong>TI 1:1 较高。左海马中位数为 {hip11['median_v_per_m']:.3f} V/m，TI 1:3 为 {hip13['median_v_per_m']:.3f} V/m。</li><li><strong>海马内位置：</strong>TI 1:3 时，高值区有轻微前移，但海马后部仍是场强占比最高的区域。现有结果不足以确认刺激中心已经转到前海马。</li><li><strong>非靶区暴露：</strong>两种配比都在皮层和其他灰质区域产生电场。部分皮层采样区的场强与左海马相当或更高。</li></ol><div class="metrics"><div class="metric"><b>{hip11['median_v_per_m']:.3f} V/m</b><span>TI 1:1 左海马中位数</span></div><div class="metric"><b>{hip13['median_v_per_m']:.3f} V/m</b><span>TI 1:3 左海马中位数</span></div><div class="metric"><b>{anterior_shift:+.1f} 个百分点</b><span>TI 1:3 时前海马场强份额的变化</span></div><div class="metric"><b>{hippocampal_tail_shift_mm:.2f} mm</b><span>左海马高值区重心的前移距离</span></div></div><p class="note">这是单一示例头模型的正向电场计算结果，不是疗效、安全性或患者个体化结论。</p></section>

    <section id="protocol"><h2>二、刺激方案</h2><p>靶区为左海马。四个圆形电极组成两组回路：FT7-Fp2 和 TP7-TP8。两种方案只改变两组回路的电流配比。</p><div class="protocol"><div><h3>TI 1:1</h3><p>两组回路均为 1.0 mA。</p></div><div><h3>TI 1:3</h3><p>第一组为 0.5 mA，第二组为 1.5 mA。</p></div></div>{clinical_figure_html(figure_map['fig01'], '绿色区域为左海马靶区，并按前、中、后三段进行分析。')}{clinical_figure_html(figure_map['fig02'], '四个电极在头皮上的位置及两组回路。箭头表示电极配对和极性，不表示头内电流路径。')}{clinical_figure_html(figure_map['fig03'], '两组回路各自在 1 mA 条件下形成的基础电场，后续按两种方案的电流比例进行组合。')}</section>

    <section id="results"><h2>三、模拟结果</h2><h3>左海马整体场强</h3><p>TI 1:1 在左海马产生的场强高于 TI 1:3。图 4 和图 5 使用相同色标，颜色越接近色标高端，场强越高。</p>{clinical_figure_html(figure_map['fig04'], 'TI 1:1 的电场分布。上排为本报告主要采用的方向投影 TI，下排为 TImax。')}{clinical_figure_html(figure_map['fig05'], 'TI 1:3 的电场分布。与图 4 使用相同色标，可直接比较场强和空间分布。')}<h3>海马内高值区的位置</h3><p>TI 1:3 将前段场强份额从 {100*share11['hippocampus_anterior']:.2f}% 提高到 {100*share13['hippocampus_anterior']:.2f}%。高值区重心向前移动 {hippocampal_tail_shift_mm:.2f} mm，但两种方案中场强占比最高的区域仍是海马后段。</p>{clinical_figure_html(figure_map['fig06'], '左图比较海马前、中、后三段的中位场强；右图显示各段在三段总和中的份额。')}{clinical_figure_html(figure_map['fig09'], '左海马内场强最高约 1% 区域的重心及单个最高值位置。')}<h3>海马以外的电场</h3><p>左海马的中位场强高于全部非靶区灰质的中位数，但局部皮层并不总是低于海马。海马与全部靶外灰质的 P95 基本相当，因此不能把这一结果解释为电场只集中在海马。</p>{clinical_figure_html(figure_map['fig07'], '左海马与三个局部皮层采样区的中位场强。部分皮层采样区与海马相当或更高。')}{clinical_figure_html(figure_map['fig08'], '左海马与全部非靶区灰质、右海马及全脑高值区的比较。')}{clinical_figure_html(figure_map['fig10'], '左侧灰质表面的方向投影 TI，显示两种方案均存在较广泛的表层电场。')}<h3>区域统计</h3><div class="table-wrap"><table><thead><tr><th>方案</th><th>区域</th><th>平均值 (V/m)</th><th>中位数 (V/m)</th><th>P95 (V/m)</th><th>体积 (mm³)</th></tr></thead><tbody>{''.join(clinical_roi_rows)}</tbody></table></div></section>

    <section id="interpretation"><h2>四、如何理解这些结果</h2><p>两种方案体现了不同取舍，不能脱离研究目标简单判断哪一种“更好”。</p><ul class="reading-order"><li>如果目标是在这个模型中获得更高的左海马整体场强，TI 1:1 更符合这一目标。</li><li>TI 1:3 改变了海马内的相对分布，高值区略向前移动，但左海马整体场强下降，也没有减少非靶区暴露。</li><li>前移距离只有 {hippocampal_tail_shift_mm:.2f} mm。TI 1:1 的高值区重心距前、中段边界仅 {hippocampal_tail_boundary_margin11_mm:.2f} mm，这一差异可能受分区边界和模型误差影响。</li></ul><p class="note">因此，本例支持“电流配比会改变场强和空间分布”，但不支持“TI 1:3 已实现稳定的前海马靶向”或“某一方案具有临床优势”。</p></section>

    <section id="methods"><h2>五、方法、术语与研究边界</h2><h3>模型与靶区</h3><p>采用 SimNIBS 官方 ernie 单受试者 CHARM 头模型和四个直径 20 mm 的圆电极。FT7-Fp2 与 TP7-TP8 是对论文连续头围坐标的 10-10 实施替代，不是原论文的 MIDA 模型、原始参与者模型或客户 MRI。</p><p>灰质四面体中心由 SimNIBS 4.6.0 <span class="mono">subject2mni_coords</span> 经 <span class="mono">Conform2MNI_nonl.nii.gz</span> 非线性变换到 MNI 空间，再以最近邻方式采样 Harvard-Oxford 25% 最大概率图谱中的左、右海马。三个皮层区域为半径 10 mm 的球形采样区，不是解剖图谱分区。</p><h3>主要指标</h3><p><strong>中位数</strong>表示区域内较典型的场强；<strong>P95</strong>表示区域内较高水平的场强；<strong>P99 重心</strong>表示场强最高约 1% 体积的中心位置。</p><div id="field-definition"><p><strong>方向投影 TI</strong>沿 DTI 推导的局部主方向计算，是本报告的主要指标。<strong>TImax</strong>是不限定方向时的最大包络幅度，两者不能互换。</p><p>E1、E2 为按 peak-to-baseline 电流缩放后的载波电场。报告中的 TI 数值是包络调制幅度，不是 RMS、单个载波峰值，也不是 |E1|+|E2|。</p><p>令 <em>u</em> 为单位 DTI 主特征向量，<em>a</em> = E1·<em>u</em>、<em>b</em> = E2·<em>u</em>：</p><p class="formula"><strong>A<sub>dir</sub> = ||a+b| − |a−b||</strong></p><p>TImax 使用 SimNIBS <span class="mono">get_maxTI</span>。当 |E2| ≤ |E1|cosα 时，A<sub>max</sub> = 2|E2|；否则：</p><p class="formula"><strong>A<sub>max</sub> = 2|E2 × (E1−E2)| / |E1−E2|</strong></p></div><h3>质量控制与限制</h3><p>灰质分析包含 {quality['gray_tetrahedra']:,} 个四面体。有限的 DTI 方向向量覆盖 {100*quality['dti_valid_gray_fraction']:.2f}% 的灰质单元；其余单元记为缺失，不写成零。该比例只表示方向向量存在且数值有限，不表示方向估计可靠。未设置 FA 或特征值各向异性阈值。方向投影 TI 与 TImax 已逐单元独立复算，最大误差为 0 V/m。</p><p>右海马采用与左海马相同的 Harvard-Oxford 图谱、非线性 subject-to-MNI 变换和最近邻采样链。右海马（right hippocampus (contralateral)）的 mean/median/P95 为 TI 1:1 {right11['mean_v_per_m']:.4f}/{right11['median_v_per_m']:.4f}/{right11['p95_v_per_m']:.4f} V/m，TI 1:3 {right13['mean_v_per_m']:.4f}/{right13['median_v_per_m']:.4f}/{right13['p95_v_per_m']:.4f} V/m。全部靶外灰质包含右海马、其他深部灰质及皮层采样区；全局 target/off-target 比值不等同于侧化选择性。mean/P95 比值同时由 {mean_ratio11:.2f}/{p95_ratio11:.2f} 变为 {mean_ratio13:.2f}/{p95_ratio13:.2f}。</p><p>左海马占有效方向投影分析域体积的 {hippocampal_domain_fraction_pct:.2f}%，仅作为空间占比参照。TI 1:3 海马内高值尾部为 {target_tail_volume13:.2f} mm³（{target_tail_elements13} 个四面体），对网格离散敏感，只作量级描述。图 7 的柱高仅表示海马及三个蒙太奇相关皮层采样区的体积加权中位数，不能仅凭本图中位数判断表层暴露。</p><p>Violante 2023 图 2c 报告 16 名参与者个体 MRI 模型的相对海马暴露。本报告复现其沿 DTI 推导主纤维轴计算包络场的分析口径；论文数值只作分布参照，不与本例 V/m 直接比较。</p><p>本示例未进行网格收敛、电极位置扰动、组织电导率敏感性、DTI 主方向定向不确定性、非线性 MNI 配准不确定性或跨受试者稳健性分析。结果不能用于推断神经激活、安全剂量、治疗效果或个体处方。</p><h3>图表与数据</h3><p>交付包包含 10 张图的 PNG、SVG、PDF、中英文图注和支撑 CSV，以及 Excel 结果表、HDF5、MSH、16 份场图与 ROI 掩膜、冻结脚本和依赖版本。</p><div class="downloads"><a href="tables/violante2023_ti_reproduction_results.xlsx"><strong>Excel 结果表</strong><span>区域统计、图件索引和计算口径</span></a><a href="packages/figure_support_csv.zip"><strong>图表数据</strong><span>各图对应的 CSV 文件</span></a><a href="packages/nifti_fields.zip"><strong>NIfTI 数据</strong><span>16 份场图与 ROI 掩膜</span></a><a href="raw/violante2023_reproduction_fields.h5"><strong>HDF5 数据</strong><span>逐单元电场与派生指标</span></a><a href="manifest.json"><strong>文件校验</strong><span>文件大小与 SHA-256</span></a><a href="reproducibility/DATA_AND_CODE_AVAILABILITY.md"><strong>复现说明</strong><span>冻结脚本、依赖和使用边界</span></a></div><h3>参考文献</h3><p>Violante IR et al. <em>Non-invasive temporal interference electrical stimulation of the human hippocampus.</em> Nature Neuroscience. 2023;26:1994–2004. doi:10.1038/s41593-023-01456-8.</p><p>Grossman N et al. <em>Noninvasive Deep Brain Stimulation via Temporally Interfering Electric Fields.</em> Cell. 2017;169:1029–1041.e16. doi:10.1016/j.cell.2017.05.024.</p></section>
    </main>'''
    clinical_main = clinical_main.replace(
        "本次模拟比较两种电流配比，观察它们在左海马产生的电场强度、海马内高值区的位置，以及海马以外的电场分布。",
        "本次模拟比较 TI 1:1 和 TI 1:3 两种电流配比，主要看三个结果：左海马场强、海马内高值区的位置、海马以外的电场分布。",
        1,
    ).replace(
        "现有结果不足以确认刺激中心已经转到前海马。",
        "不能据此认为主要高值区已经从海马后部转到前部。",
        1,
    ).replace(
        "两种方案体现了不同取舍，不能脱离研究目标简单判断哪一种“更好”。",
        "没有一种方案在所有指标上都占优。选择哪种配比，取决于研究更看重左海马整体场强，还是海马内高值区的位置变化。",
        1,
    ).replace(
        "因此，本例支持“电流配比会改变场强和空间分布”，但不支持“TI 1:3 已实现稳定的前海马靶向”或“某一方案具有临床优势”。",
        "就这个模型而言，改变电流配比会同时改变场强和分布。TI 1:3 使高值区略向前移动，但还不能认为它实现了稳定的前海马靶向，更不能据此判断临床优势。",
        1,
    ).replace(
        "距前、中段边界仅", "距前/中边界仅", 1
    ).replace(
        "mm，这一差异可能受分区边界和模型误差影响。",
        "mm，不能视为稳健分类；这一差异可能受分区边界和模型误差影响。",
        1,
    ).replace(
        "本报告复现其沿 DTI 推导主纤维轴计算包络场的分析口径",
        "本报告复现 Violante 2023 沿 DTI 推导主纤维轴计算包络场的分析口径",
        1,
    )
    report_html = re.sub(r"<main>.*?</main>", clinical_main, report_html, count=1, flags=re.DOTALL)
    report_html = re.sub(
        r"<header>.*?</header>",
        f'''<header><div class="brand">QuanLan BrainScience · SimNIBS</div><div class="eyebrow">海马时间干涉刺激 · 正向电场模拟</div><h1>两种电流配比下的海马电场分布</h1><p>基于 Violante 等（2023）的刺激思路，在 SimNIBS ernie 头模型中比较 TI 1:1 与 TI 1:3。重点观察左海马场强、海马内高值区的位置及非靶区暴露。</p><div class="meta"><span>单受试者示例模型</span><span>SimNIBS {html.escape(result['software']['version'])}</span><span>单位：V/m</span><span class="mono">{report_id}</span></div></header>''',
        report_html,
        count=1,
        flags=re.DOTALL,
    )
    report_html = re.sub(
        r"<nav>.*?</nav>",
        '<nav><a href="#summary">目的与结论</a><a href="#protocol">刺激方案</a><a href="#results">模拟结果</a><a href="#interpretation">结果解读</a><a href="#methods">方法与限制</a></nav>',
        report_html,
        count=1,
        flags=re.DOTALL,
    )
    return report_html


def find_edge() -> Path:
    candidates = [Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe", Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe"]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError("Microsoft Edge is required for PDF export")


def write_supporting_documents(result: dict, captions: list[dict], workbook_path: Path, focality_rows: list[dict]) -> None:
    METHODS.mkdir(parents=True, exist_ok=True)
    QC.mkdir(parents=True, exist_ok=True)
    whole_valid_volume = result["conditions"]["TI_1to1"]["metrics"]["whole_gray_matter"]["TI_directional"]["volume_mm3"]
    target_valid_volume = result["conditions"]["TI_1to1"]["metrics"]["hippocampus"]["TI_directional"]["volume_mm3"]
    hippocampal_domain_fraction_pct = 100 * target_valid_volume / whole_valid_volume
    capture11 = result["conditions"]["TI_1to1"]["focality"]["target_high_tail_capture_pct"]
    capture13 = result["conditions"]["TI_1to3"]["focality"]["target_high_tail_capture_pct"]
    focality_support = {row["condition"]: row for row in focality_rows}
    methods = f"""# Methods summary

## Scope

This package reproduces the forward-modeling structure of Violante et al. (2023) on the SimNIBS example subject `ernie`. It is not a numerical replication of the paper's MIDA model or participant cohort.

## Head model and montage

- Software: SimNIBS {result['software']['version']}
- Head model: SimNIBS CHARM example subject `ernie`
- Electrodes: four circular electrodes, 20 mm diameter
- Implementation montage: FT7-Fp2 and TP7-TP8
- Important: these 10-10 positions are an implementation substitute for the paper's continuous scalp coordinates.

## Electric-field calculation

The two carrier-pair fields were solved on the same electrodeized tetrahedral mesh. TI 1:1 uses 1.0 mA and 1.0 mA peak-to-baseline; TI 1:3 uses 0.5 mA and 1.5 mA. With unit principal direction `u`, define `a = E1 dot u` and `b = E2 dot u`. Directional TI follows SimNIBS `get_dirTI`: `A_dir = abs(abs(a+b) - abs(a-b))`. TImax follows SimNIBS `get_maxTI` (Grossman et al., 2017): after ordering the vectors so `|E1| >= |E2|` and making their angle `alpha` acute, `A_max = 2|E2|` when `|E2| <= |E1|cos(alpha)`; otherwise `A_max = 2|E2 x (E1-E2)| / |E1-E2|`. E1 and E2 are carrier fields scaled from the declared peak-to-baseline currents. These outputs are modulation-envelope amplitudes, not RMS values, individual carrier peaks, or the sum of carrier magnitudes.

## Regions and statistics

Gray-matter tetrahedron centers are transformed from subject conform to MNI coordinates with SimNIBS 4.6.0 `transformations.subject2mni_coords`, using its default nonlinear (`nonl`) mode and `m2m_ernie/toMNI/Conform2MNI_nonl.nii.gz`. Harvard-Oxford subcortical 25% maximum-probability labels are sampled by nearest neighbor at those MNI coordinates; the atlas is not separately resampled into subject space. Anterior, middle, and posterior segments use MNI Y slices reported by Violante et al.; continuous tetrahedron centers are assigned with half-millimeter edges. The three segments cover {100*result['implementation']['roi']['segment_coverage']['assigned_fraction']:.2f}% of the atlas hippocampal volume in this model and do not overlap. The cortical controls are exploratory spheres with a 10-mm radius centered near FT7, TP7, and their scalp-coordinate midpoint; they are not anatomical atlas ROIs. Regional mean, median, P95, and maximum are volume-weighted over gray-matter tetrahedra. The hippocampus occupies {hippocampal_domain_fraction_pct:.2f}% of the valid directional-TI gray-matter domain. This volume fraction is used only as a spatial reference for P99-tail capture: TI 1:1 capture is {capture11 / hippocampal_domain_fraction_pct:.1f} times the reference and TI 1:3 capture is {capture13 / hippocampal_domain_fraction_pct:.3f} times the reference. The corresponding hippocampal high-tail volumes are {float(focality_support['TI_1to1']['target_high_tail_volume_mm3']):.2f} mm3 across {int(focality_support['TI_1to1']['target_high_tail_element_count'])} tetrahedra and {float(focality_support['TI_1to3']['target_high_tail_volume_mm3']):.2f} mm3 across {int(focality_support['TI_1to3']['target_high_tail_element_count'])} tetrahedra. The latter is mesh-discretization sensitive and descriptive only. The volume reference does not assume a uniform high-tail distribution or imply statistical significance. P99 is a descriptive whole-gray-matter tail, not a neural activation threshold.

## Numerical quality control

The E1 and E2 carrier meshes are node- and element-aligned. Finite DTI direction vectors are available for {100*result['quality']['dti_valid_gray_fraction']:.2f}% of gray-matter tetrahedra. This is an availability measure, not directional-reliability evidence. No FA or eigenvalue-anisotropy threshold was applied; principal-direction uncertainty in low-anisotropy tensors was not quantified and propagates to directional TI. Independent elementwise recomputation of directional TI and TImax agrees with the SimNIBS functions to the declared tolerance of 1e-12 V/m. SimNIBS used the hypre solver. The log-reported maximum internal basis-solve current-calibration estimate is {result['quality']['solver_log']['maximum_basis_solve_current_calibration_error_pct']:.1f}%; this is not a measured device-current error, and no acceptance threshold was declared for this exploratory reproduction.

## Verification not performed

Mesh-convergence, electrode-displacement, conductivity-sensitivity, segmentation-uncertainty, DTI principal-direction uncertainty, nonlinear MNI-registration uncertainty, and cross-subject robustness analyses were not performed in this example package.

## Interpretation boundary

    This single-subject example supports spatial field comparison under the stated model and parameters. It does not establish neural activation, safety, efficacy, clinical response, or a patient-specific prescription.
"""
    methods = methods.replace(
        "Harvard-Oxford subcortical 25% maximum-probability labels are sampled by nearest neighbor at those MNI coordinates; the atlas is not separately resampled into subject space.",
        "The left and right hippocampi are sampled from the Harvard-Oxford subcortical 25% maximum-probability atlas by the same nearest-neighbor rule at those MNI coordinates; the atlas is not separately resampled into subject space. The right hippocampus is reported explicitly as the contralateral homologous deep off-target ROI and remains part of all off-target gray matter.",
        1,
    )
    (METHODS / "methods_summary.md").write_text(methods, encoding="utf-8")

    readme = f"""# {PROJECT_TITLE}

本目录是一套正向 TI 电场仿真示例交付包，基于真实 SimNIBS FEM 结果生成。

## 客户入口

- `report.html`：可直接在浏览器打开的中文结果报告
- `report.pdf`：便于发送和归档的打印版报告
- `{workbook_path.relative_to(OUTPUT_DIR).as_posix()}`：区域指标、聚焦性、论文基准和图件索引
- `figures/`：300 dpi PNG、SVG、PDF、双语图注和逐图支撑数据
- `raw/`：HDF5、MSH、NIfTI 和灰质表面数据，用于二次分析
- `reproducibility/`：冻结脚本、Python/依赖版本及数据与代码可用性声明

## 使用边界

本例采用 SimNIBS 官方 `ernie` 个体头模型。FT7-Fp2 与 TP7-TP8 是对论文连续头围坐标的 10-10 实施替代，不是论文原始电极坐标，也不是客户脑电帽的实测配准结果。报告不用于临床疗效或安全性判断。

## 图件

共 {len(captions)} 张主图。所有空间场对比使用明确单位和跨条件共享显示范围；各图的可编辑格式和支撑数据见 `figures/figure_data/` 与 `figures/captions/`。
"""
    (OUTPUT_DIR / "README.md").write_text(readme, encoding="utf-8")


def write_reproducibility_materials() -> None:
    REPRODUCIBILITY.mkdir(parents=True, exist_ok=True)
    script_names = (
        "run_violante2023_ti_reproduction.py",
        "build_violante2023_ti_delivery.py",
    )
    for name in script_names:
        source = ROOT / "scripts" / name
        if not source.is_file():
            raise FileNotFoundError(f"Missing reproducibility script: {source}")
        shutil.copy2(source, REPRODUCIBILITY / name)

    packages = ("simnibs", "numpy", "scipy", "matplotlib", "nibabel", "h5py", "openpyxl")
    versions = {name: importlib_metadata.version(name) for name in packages}
    environment = {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.system(),
        "packages": versions,
        "note": "No credentials, environment variables, or absolute interpreter paths are recorded.",
    }
    (REPRODUCIBILITY / "python_environment.json").write_text(
        json.dumps(environment, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    requirements = [f"{name}=={version}" for name, version in versions.items()]
    (REPRODUCIBILITY / "requirements-lock.txt").write_text("\n".join(requirements) + "\n", encoding="utf-8")

    availability = f"""# Data and Code Availability

## Data

This delivery contains the derived elementwise fields, ROI masks, summary tables, figure-support data, and publication figures used in the report. The primary machine-readable files are `../raw/violante2023_reproduction_fields.h5`, `../raw/violante2023_reproduction_fields.msh`, the NIfTI files under `../raw/nifti/`, `../result.json`, and the CSV/Excel tables.

The analysis uses the public SimNIBS example subject `ernie` and the Harvard-Oxford subcortical 25% maximum-probability atlas. Upstream anatomical and atlas source files remain subject to their original distribution terms and are not represented as participant data collected for this report. This package contains no original Violante et al. participant MRI data and is not a numerical reproduction of the paper's MIDA or participant cohort.

## Code

Frozen snapshots of the analysis and delivery generators are included in this directory:

- `run_violante2023_ti_reproduction.py`
- `build_violante2023_ti_delivery.py`

The Python and package versions used for this build are recorded in `python_environment.json` and `requirements-lock.txt`. The scripts use repository-relative paths and do not contain API keys or provider credentials.

## Reproduction boundary

From the repository root, place the frozen snapshots under `scripts/` (or confirm they match the working copies) and rebuild the report from the existing derived FEM outputs with:

```text
python scripts/build_violante2023_ti_delivery.py
```

A full FEM rerun additionally requires the SimNIBS `ernie` head model, the Harvard-Oxford atlas inputs, and the solver environment described above. The implemented FT7-Fp2 and TP7-TP8 montage is a 10-10 substitute for the continuous scalp coordinates in Violante et al. (2023). Mesh-convergence, electrode-position, conductivity, segmentation, DTI-direction, MNI-registration, and cross-subject uncertainty analyses were not performed.

## Integrity

Every delivered file except the manifest itself is listed with byte size and SHA-256 in `../manifest.json`. Report run ID: `{RUN_ID}`.
"""
    (REPRODUCIBILITY / "DATA_AND_CODE_AVAILABILITY.md").write_text(availability, encoding="utf-8")


def write_manifest() -> None:
    files = []
    for path in sorted(p for p in OUTPUT_DIR.rglob("*") if p.is_file() and p.name != "manifest.json"):
        files.append({
            "path": path.relative_to(OUTPUT_DIR).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    payload = {
        "schema": "qlanalyser.simnibs.delivery-manifest.v1",
        "run_id": RUN_ID,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    reuse_rendered = "--reuse-rendered" in sys.argv[1:]
    unknown_args = [arg for arg in sys.argv[1:] if arg != "--reuse-rendered"]
    if unknown_args:
        raise ValueError(f"Unknown arguments: {unknown_args}")
    required = [
        RESULT_PATH,
        H5_PATH,
        TABLES / "roi_metrics.csv",
        TABLES / "electrode_montage.csv",
        RAW / "violante2023_reproduction_fields.msh",
        RAW / "violante2023_reproduction_rois.msh",
        RAW / "gray_surface_fields.npz",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing analysis outputs:\n" + "\n".join(missing))
    if not (RAW / "nifti").is_dir() or not any((RAW / "nifti").glob("*.nii*")):
        raise FileNotFoundError("Missing NIfTI analysis outputs")

    for stale in (OUTPUT_DIR / "manifest.json", OUTPUT_DIR / "report.html", OUTPUT_DIR / "report.pdf"):
        if stale.exists():
            stale.unlink()

    # Regenerate presentation artifacts while preserving expensive FEM and analysis outputs.
    directories = (QC, METHODS, PACKAGES, REPRODUCIBILITY) if reuse_rendered else (FIGURES, QC, METHODS, PACKAGES, REPRODUCIBILITY)
    for directory in directories:
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)
    FIGURE_DATA.mkdir(parents=True, exist_ok=True)
    CAPTIONS.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)

    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    if result["implementation"]["roi"]["source"]["method"] != "atlas":
        raise RuntimeError("Customer delivery requires the real Harvard-Oxford atlas ROI")
    roi_rows = read_csv(TABLES / "roi_metrics.csv")
    electrode_rows = read_csv(TABLES / "electrode_montage.csv")

    figure_paths: dict[str, dict[str, str]] = {}
    with h5py.File(H5_PATH, "r") as h5:
        write_data_health(result, roi_rows, h5)
        shared_vmax = {}
        for key, field in (("directional", "TI_directional_gray"), ("timax", "TImax_gray")):
            display_values = np.concatenate([
                np.asarray(h5[f"conditions/{condition}/{field}"])[np.isfinite(np.asarray(h5[f"conditions/{condition}/{field}"]))]
                for condition in ("TI_1to1", "TI_1to3")
            ])
            shared_vmax[key] = float(np.percentile(display_values, 99))
            if not np.isfinite(shared_vmax[key]) or shared_vmax[key] <= 0:
                raise RuntimeError(f"Invalid shared field display range for {key}")

        if not reuse_rendered:
            figure_paths["fig01"], anatomy_rows = figure_anatomy(h5)
            figure_paths["fig02"], montage_rows = figure_montage(result, h5)
            write_csv(FIGURE_DATA / "fig01_anatomy_roi.csv", anatomy_rows)
            write_csv(FIGURE_DATA / "fig02_electrode_montage.csv", montage_rows)
            figure_paths["fig03"] = figure_carriers(h5)
            figure_paths["fig04"] = figure_condition_fields("TI_1to1", shared_vmax, 4)
            figure_paths["fig05"] = figure_condition_fields("TI_1to3", shared_vmax, 5)
            figure_paths["fig09"], focus_rows = figure_focus_location(h5)

    if not reuse_rendered:
        figure_paths["fig06"], segment_rows = figure_hippocampal_segments(result)
        figure_paths["fig07"], cortex_rows = figure_target_cortex(result)
        figure_paths["fig08"], focality_rows = figure_focality(result)
        figure_paths["fig10"] = figure_cortical_surface(shared_vmax["directional"])
    else:
        slugs = {
            "fig01": "fig01_individual_anatomy_hippocampus",
            "fig02": "fig02_stimulation_montage",
            "fig03": "fig03_carrier_fields_E1_E2",
            "fig04": "fig04_TI_1to1_directional_and_TImax",
            "fig05": "fig05_TI_1to3_directional_and_TImax",
            "fig06": "fig06_hippocampal_segment_steering",
            "fig07": "fig07_hippocampus_overlying_cortex",
            "fig08": "fig08_targeting_and_focality",
            "fig09": "fig09_focus_location_mni",
            "fig10": "fig10_directional_ti_cortical_surface",
        }
        for figure_id, slug in slugs.items():
            paths = {extension: f"figures/{extension}/{slug}.{extension}" for extension in OUTPUT_FORMATS}
            if not all((OUTPUT_DIR / path).is_file() for path in paths.values()):
                raise FileNotFoundError(f"Cannot reuse incomplete rendered figure: {figure_id}")
            figure_paths[figure_id] = paths
        segment_rows = read_csv(FIGURE_DATA / "fig06_hippocampal_segment_steering.csv")
        cortex_rows = read_csv(FIGURE_DATA / "fig07_hippocampus_overlying_cortex.csv")
        focality_rows = read_csv(FIGURE_DATA / "fig08_targeting_and_focality.csv")
        focus_rows = read_csv(FIGURE_DATA / "fig09_focus_location_mni.csv")

    whole_valid_volume = result["conditions"]["TI_1to1"]["metrics"]["whole_gray_matter"]["TI_directional"]["volume_mm3"]
    target_valid_volume = result["conditions"]["TI_1to1"]["metrics"]["hippocampus"]["TI_directional"]["volume_mm3"]
    hippocampal_domain_fraction_pct = 100 * target_valid_volume / whole_valid_volume
    focality_numeric_fields = (
        "target_offtarget_mean_ratio",
        "target_offtarget_median_ratio",
        "target_offtarget_p95_ratio",
        "gm_p99_threshold_v_per_m",
        "target_high_tail_capture_pct",
        "target_coverage_pct",
        "off_target_high_tail_volume_mm3",
    )
    for row in focality_rows:
        for field in focality_numeric_fields:
            row[field] = float(row[field])
        captured = float(row["target_high_tail_capture_pct"])
        row["hippocampal_domain_fraction_pct"] = hippocampal_domain_fraction_pct
        row["capture_to_domain_fraction_ratio"] = captured / hippocampal_domain_fraction_pct
        row["volume_reference_interpretation"] = "descriptive spatial-volume reference; no uniformity or statistical-significance assumption"
    with h5py.File(H5_PATH, "r") as h5:
        volumes = np.asarray(h5["mesh/element_volumes_mm3"], dtype=float)
        hippocampus = np.asarray(h5["masks/hippocampus"], dtype=bool)
        for row in focality_rows:
            condition = row["condition"]
            values = np.asarray(h5[f"conditions/{condition}/TI_directional_gray"], dtype=float)
            threshold = float(row["gm_p99_threshold_v_per_m"])
            target_high_tail = hippocampus & np.isfinite(values) & np.isfinite(volumes) & (volumes > 0) & (values >= threshold)
            row["target_high_tail_volume_mm3"] = float(volumes[target_high_tail].sum())
            row["target_high_tail_element_count"] = int(target_high_tail.sum())
            row["target_high_tail_mesh_sensitivity"] = "small-volume descriptor; mesh-convergence not evaluated"
    write_csv(FIGURE_DATA / "fig08_targeting_and_focality.csv", focality_rows)

    for row in focus_rows:
        centroid_y = float(row["hippocampal_p99_centroid_mni_y_mm"])
        row["distance_to_anterior_middle_boundary_mm"] = centroid_y - (-18.5)
        row["segment_assignment_interpretation"] = "descriptive only; robustness not established because model uncertainty was not quantified"
    write_csv(FIGURE_DATA / "fig09_focus_location_mni.csv", focus_rows)

    captions = build_captions(result, figure_paths, focus_rows, focality_rows)
    workbook_path = build_workbook(
        result,
        roi_rows,
        electrode_rows,
        captions,
        segment_rows,
        focality_rows,
    )
    write_supporting_documents(result, captions, workbook_path, focality_rows)
    write_reproducibility_materials()
    archives = build_secondary_analysis_archives()
    (QC / "01_display_scale.json").write_text(
        json.dumps({"shared_ti_display_vmax_v_per_m": shared_vmax, "rule": "separate joint gray-matter P99 scales by metric, each shared across both conditions"}, indent=2),
        encoding="utf-8",
    )
    (QC / "02_figure_support_index.json").write_text(
        json.dumps({"figures": captions, "additional_support": {"fig07": cortex_rows, "fig09": focus_rows}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (QC / "03_coordinate_transform.json").write_text(
        json.dumps({
            "tool": "simnibs.utils.transformations.subject2mni_coords",
            "simnibs_version": result["software"]["version"],
            "direction": "subject2mni",
            "transformation_type": "nonl",
            "warp_field": "m2m_ernie/toMNI/Conform2MNI_nonl.nii.gz",
            "atlas_sampling": "nearest-neighbor labels at transformed gray-matter tetrahedron centers",
            "atlas_to_subject_resampling": False,
            "registration_uncertainty_evaluated": False,
        }, indent=2),
        encoding="utf-8",
    )

    report_path = OUTPUT_DIR / "report.html"
    report_path.write_text(build_html(result, captions, focus_rows, focality_rows), encoding="utf-8")
    pdf_path = OUTPUT_DIR / "report.pdf"
    edge = find_edge()
    completed = subprocess.run(
        [str(edge), "--headless", "--disable-gpu", "--no-pdf-header-footer", "--print-to-pdf-no-header", f"--print-to-pdf={pdf_path}", report_path.as_uri()],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if completed.returncode != 0 or not pdf_path.is_file() or pdf_path.stat().st_size == 0:
        raise RuntimeError(f"PDF export failed ({completed.returncode}): {completed.stderr[-1000:]}")
    write_manifest()
    print(json.dumps({
        "report_html": str(report_path),
        "report_pdf": str(pdf_path),
        "workbook": str(workbook_path),
        "csv_archive": str(archives["csv"]),
        "nifti_archive": str(archives["nifti"]),
        "figures": len(captions),
        "shared_display_vmax_v_per_m": shared_vmax,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
