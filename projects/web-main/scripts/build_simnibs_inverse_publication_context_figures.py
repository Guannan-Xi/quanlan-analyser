"""Build publication-context figures from the final four-electrode SimNIBS result."""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    ENV_ROOT = Path(sys.executable).resolve().parent
    DLL_DIR = ENV_ROOT / "Library" / "bin"
    os.environ["PATH"] = os.pathsep.join(
        str(path) for path in (DLL_DIR, ENV_ROOT / "Scripts", ENV_ROOT)
    ) + os.pathsep + os.environ.get("PATH", "")
    if DLL_DIR.is_dir() and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(DLL_DIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import ListedColormap, Normalize
from matplotlib.patches import Circle, FancyArrowPatch, Patch
import nibabel as nib
import numpy as np
from simnibs import mesh_io
from simnibs.utils.csv_reader import read_csv_positions
from simnibs.utils.file_finder import SubjectFiles
from simnibs.utils.mesh_element_properties import ElementTags


# ============================================================
# CONFIGURATION - edit only this block
# ============================================================
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "simnibs_inverse_ti_discrete_ernie_20260729"
M2M = ROOT / "data" / "simnibs_examples_v4_1" / "extracted" / "m2m_ernie"
FIGURE_DIR = OUT / "figures"
FIGURE_DATA_DIR = FIGURE_DIR / "figure_data"
FINAL_MESH = OUT / "independent_fem" / "four_electrode_timax.msh"
FINAL_ARCHIVE = OUT / "independent_fem" / "independent_timax_recompute.npz"
TARGET_MM = np.array([-41.0, -13.0, 66.0], dtype=float)
ROI_RADIUS_MM = 20.0
ELECTRODE_LABELS = ["F5", "P5", "FC3", "CP3"]
CURRENT_MA = {"F5": 1.0, "P5": -1.0, "FC3": 1.0, "CP3": -1.0}
CARRIER = {"F5": "carrier_1", "P5": "carrier_1", "FC3": "carrier_2", "CP3": "carrier_2"}
DPI = 300
OUTPUT_FORMATS = ("png", "svg")
FIGSIZE = (10.0, 5.8)
FIELD_CMAP = "viridis"
# ============================================================
# END CONFIGURATION
# ============================================================


INK = "#17211d"
MUTED = "#5e6b64"
LINE = "#8b9891"
GREEN = "#1b7f5a"
RED = "#c13f3f"
BLUE = "#2b68a4"


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
            "font.size": 9,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.edgecolor": INK,
            "axes.linewidth": 0.8,
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.dpi": DPI,
            "savefig.bbox": "tight",
            "svg.fonttype": "none",
        }
    )


def save_figure(fig: plt.Figure, stem: str) -> None:
    for extension in OUTPUT_FORMATS:
        fig.savefig(FIGURE_DIR / f"{stem}.{extension}", dpi=DPI if extension == "png" else None)
    plt.close(fig)


def cap_coordinates() -> dict[str, np.ndarray]:
    cap_path = Path(SubjectFiles(subpath=str(M2M)).eeg_cap_1010)
    _, coordinates, _, names, _, _ = read_csv_positions(str(cap_path))
    mapping = {str(name): np.asarray(coord, dtype=float) for name, coord in zip(names, coordinates)}
    missing = [label for label in ELECTRODE_LABELS if label not in mapping]
    if missing:
        raise RuntimeError(f"EEG cap lacks electrode labels: {missing}")
    return {label: mapping[label] for label in ELECTRODE_LABELS}


def axis_coordinates(image: nib.Nifti1Image) -> list[np.ndarray]:
    affine = np.asarray(image.affine, dtype=float)
    if not np.allclose(affine[:3, :3], np.diag(np.diag(affine[:3, :3])), atol=1e-6):
        raise RuntimeError("Expected an axis-aligned canonical T1 affine")
    return [affine[axis, axis] * np.arange(image.shape[axis]) + affine[axis, 3] for axis in range(3)]


def render_anatomy_target() -> dict:
    t1_image = nib.as_closest_canonical(nib.load(M2M / "T1.nii.gz"))
    tissue_image = nib.as_closest_canonical(nib.load(M2M / "final_tissues.nii.gz"))
    if t1_image.shape[:3] != tissue_image.shape[:3] or not np.allclose(t1_image.affine, tissue_image.affine):
        raise RuntimeError("T1 and tissue labels are not aligned")
    t1 = np.asarray(t1_image.dataobj, dtype=np.float32)
    tissues = np.squeeze(np.asarray(tissue_image.dataobj, dtype=np.int16))
    if tissues.ndim != 3:
        raise RuntimeError(f"Expected a 3D tissue-label volume, got {tissues.shape}")
    target_voxel = nib.affines.apply_affine(np.linalg.inv(t1_image.affine), TARGET_MM)
    target_index = np.clip(np.rint(target_voxel).astype(int), 0, np.array(t1.shape) - 1)
    coordinates = axis_coordinates(t1_image)
    tissue_colors = [
        (0, 0, 0, 0),
        (0.86, 0.86, 0.86, 0.15),
        (0.50, 0.50, 0.50, 0.24),
        (0.25, 0.55, 0.90, 0.18),
        (0.95, 0.78, 0.30, 0.18),
        (0.90, 0.35, 0.25, 0.16),
    ]
    cmap = ListedColormap(tissue_colors)
    panels = [
        ("Sagittal", 0, 1, 2, "P-A (mm)", "I-S (mm)"),
        ("Coronal", 1, 0, 2, "L-R (mm)", "I-S (mm)"),
        ("Axial", 2, 0, 1, "L-R (mm)", "P-A (mm)"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=FIGSIZE, constrained_layout=True)
    for panel_label, (ax, (name, fixed, horizontal, vertical, xlabel, ylabel)) in enumerate(zip(axes, panels)):
        index = int(target_index[fixed])
        t1_slice = np.take(t1, index, axis=fixed).T
        tissue_slice = np.take(tissues, index, axis=fixed).T
        extent = [
            float(coordinates[horizontal][0]),
            float(coordinates[horizontal][-1]),
            float(coordinates[vertical][0]),
            float(coordinates[vertical][-1]),
        ]
        lo, hi = np.percentile(t1_slice[t1_slice > 0], [1, 99])
        ax.imshow(t1_slice, cmap="gray", origin="lower", extent=extent, vmin=lo, vmax=hi)
        display_tissues = np.where((tissue_slice >= 1) & (tissue_slice <= 5), tissue_slice, 0)
        ax.imshow(display_tissues, cmap=cmap, origin="lower", extent=extent, vmin=0, vmax=5, interpolation="nearest")
        ax.contour(
            coordinates[horizontal], coordinates[vertical], (tissue_slice == 2).astype(float),
            levels=[0.5], colors=[GREEN], linewidths=0.55, alpha=0.8,
        )
        ax.add_patch(Circle((TARGET_MM[horizontal], TARGET_MM[vertical]), ROI_RADIUS_MM, fill=False, edgecolor=GREEN, linewidth=1.6))
        ax.scatter(TARGET_MM[horizontal], TARGET_MM[vertical], marker="+", s=55, linewidths=1.6, color=GREEN, zorder=5)
        ax.text(0.02, 0.98, f"{chr(65 + panel_label)}  {name}\n{TARGET_MM[fixed]:.0f} mm", transform=ax.transAxes, va="top", color="white", fontsize=9, fontweight="bold", bbox={"facecolor": "black", "alpha": 0.52, "edgecolor": "none", "pad": 3})
        ax.set(xlabel=xlabel, ylabel=ylabel, aspect="equal")
        for side in ("top", "right", "left", "bottom"):
            ax.spines[side].set_visible(True)
    legend = [
        Patch(facecolor="#dddddd", edgecolor="none", label="WM"),
        Patch(facecolor="#808080", edgecolor=GREEN, label="GM boundary"),
        Patch(facecolor="#468cdc", edgecolor="none", label="CSF"),
        Patch(facecolor="#f2c74d", edgecolor="none", label="Bone"),
        Patch(facecolor="#df5d45", edgecolor="none", label="Scalp"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, -0.02))
    save_figure(fig, "fig00_model_target_registration")
    return {
        "coordinate_space": "ernie individual conform physical space",
        "target_subject_coordinate_mm": TARGET_MM.tolist(),
        "target_voxel_coordinate": target_voxel.tolist(),
        "target_voxel_index": target_index.tolist(),
        "roi_radius_mm": ROI_RADIUS_MM,
        "t1": "raw/anatomy/ernie_T1_conform.nii.gz",
        "tissue_labels": "data/simnibs_examples_v4_1/extracted/m2m_ernie/final_tissues.nii.gz",
        "displayed_tissues": {"1": "WM", "2": "GM", "3": "CSF", "4": "Bone", "5": "Scalp"},
    }


def surface_from_mesh(mesh: mesh_io.Msh, values: np.ndarray) -> dict[str, np.ndarray]:
    gm_surface = mesh.crop_mesh(tags=[ElementTags.GM_TH_SURFACE])
    scalp_surface = mesh.crop_mesh(tags=[ElementTags.SCALP_TH_SURFACE])
    if gm_surface.elm.nr == 0 or scalp_surface.elm.nr == 0:
        raise RuntimeError("Required GM or scalp surface is missing")
    source = mesh_io.ElementData(values, name="TImax", mesh=mesh)
    gm_tetrahedra = mesh.elm.elm_number[(mesh.elm.elm_type == 4) & (mesh.elm.tag1 == ElementTags.GM)]
    gm_values = np.asarray(source.interpolate_to_surface(gm_surface, out_fill="nearest", th_indices=gm_tetrahedra).value, dtype=np.float32)
    volume_gm_values = values[gm_tetrahedra - 1]
    tolerance = max(1e-7, float(np.max(volume_gm_values)) * 1e-6)
    if np.any(~np.isfinite(gm_values)) or float(np.max(gm_values)) > float(np.max(volume_gm_values)) + tolerance:
        raise RuntimeError("Surface interpolation exceeded the gray-matter volume range")
    return {
        "gm_coordinates": np.asarray(gm_surface.nodes.node_coord, dtype=np.float32),
        "gm_triangles": np.asarray(gm_surface.elm.node_number_list[:, :3], dtype=np.int32) - 1,
        "gm_timax_v_per_m": gm_values,
        "scalp_coordinates": np.asarray(scalp_surface.nodes.node_coord, dtype=np.float32),
        "scalp_triangles": np.asarray(scalp_surface.elm.node_number_list[:, :3], dtype=np.int32) - 1,
    }


def projected_faces(coords: np.ndarray, triangles: np.ndarray, axes: tuple[int, int, int], camera_sign: float) -> tuple[np.ndarray, np.ndarray]:
    triangle_coords = coords[triangles]
    normals = np.cross(triangle_coords[:, 1] - triangle_coords[:, 0], triangle_coords[:, 2] - triangle_coords[:, 0])
    visible = camera_sign * normals[:, axes[2]] > 0
    selected = np.flatnonzero(visible)
    depth = triangle_coords[selected, :, axes[2]].mean(axis=1)
    order = selected[np.argsort(camera_sign * depth)]
    return coords[triangles[order]][:, :, [axes[0], axes[1]]], order


def set_projected_limits(ax: plt.Axes, coords: np.ndarray, axes: tuple[int, int, int]) -> None:
    xy = coords[:, [axes[0], axes[1]]]
    lo = np.percentile(xy, 0.2, axis=0)
    hi = np.percentile(xy, 99.8, axis=0)
    padding = np.maximum((hi - lo) * 0.04, 2.0)
    ax.set_xlim(lo[0] - padding[0], hi[0] + padding[0])
    ax.set_ylim(lo[1] - padding[1], hi[1] + padding[1])
    ax.set_aspect("equal")
    ax.axis("off")


def add_electrodes(
    ax: plt.Axes,
    coords: dict[str, np.ndarray],
    axes: tuple[int, int, int],
    connect: bool,
    view_name: str,
) -> None:
    label_offsets = {
        "Left lateral": {"F5": (5, 7), "P5": (-32, 7), "FC3": (5, -12), "CP3": (-36, -12)},
        "Anterior": {"F5": (-34, 8), "P5": (-34, -14), "FC3": (7, 8), "CP3": (7, -14)},
        "Superior": {"F5": (-34, 7), "P5": (-34, -13), "FC3": (7, 7), "CP3": (7, -13)},
    }
    if connect:
        for start, end, color, linestyle in (("F5", "P5", RED, "-"), ("FC3", "CP3", BLUE, "--")):
            a = coords[start][[axes[0], axes[1]]]
            b = coords[end][[axes[0], axes[1]]]
            ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=10, linewidth=1.5, linestyle=linestyle, color=color, alpha=0.9, zorder=7))
    for label, coordinate in coords.items():
        x, y = coordinate[[axes[0], axes[1]]]
        color = RED if CURRENT_MA[label] > 0 else BLUE
        marker = "o" if CURRENT_MA[label] > 0 else "s"
        ax.scatter(x, y, s=44, marker=marker, facecolor=color, edgecolor="white", linewidth=0.8, zorder=8)
        offset = label_offsets[view_name][label]
        ax.annotate(
            f"{label} {CURRENT_MA[label]:+g}",
            (x, y),
            xytext=offset,
            textcoords="offset points",
            fontsize=7.5,
            fontweight="bold",
            color=INK,
            arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.55},
            zorder=9,
        )


def render_montage(surface: dict[str, np.ndarray], electrodes: dict[str, np.ndarray]) -> None:
    views = [("Left lateral", (1, 2, 0), -1.0), ("Anterior", (0, 2, 1), 1.0), ("Superior", (0, 1, 2), 1.0)]
    fig, axes = plt.subplots(1, 3, figsize=FIGSIZE, constrained_layout=True)
    scalp_coords = surface["scalp_coordinates"]
    scalp_triangles = surface["scalp_triangles"]
    for index, (ax, (label, view_axes, camera_sign)) in enumerate(zip(axes, views)):
        polygons, _ = projected_faces(scalp_coords, scalp_triangles, view_axes, camera_sign)
        ax.add_collection(PolyCollection(polygons, facecolors="#d9dfdc", edgecolors="none", rasterized=True))
        set_projected_limits(ax, scalp_coords, view_axes)
        add_electrodes(ax, electrodes, view_axes, connect=True, view_name=label)
        target_xy = TARGET_MM[[view_axes[0], view_axes[1]]]
        ax.scatter(*target_xy, s=58, facecolors="none", edgecolors=GREEN, linewidth=1.5, zorder=8)
        ax.text(0.02, 0.98, f"{chr(65 + index)}  {label}", transform=ax.transAxes, va="top", fontsize=9, fontweight="bold", color=INK)
    fig.text(0.5, 0.015, "circle/+1 mA: source electrode  |  square/-1 mA: return electrode  |  green ring: ROI center projected into each 2D view", ha="center", color=MUTED, fontsize=8)
    save_figure(fig, "fig00_inverse_electrode_montage")


def render_surface_field(surface: dict[str, np.ndarray], electrodes: dict[str, np.ndarray]) -> dict:
    views = [("Left lateral", (1, 2, 0), -1.0), ("Anterior", (0, 2, 1), 1.0), ("Superior", (0, 1, 2), 1.0)]
    coords = surface["gm_coordinates"]
    triangles = surface["gm_triangles"]
    values = surface["gm_timax_v_per_m"]
    positive = values[values > 0]
    vmax = float(np.percentile(positive, 99))
    norm = Normalize(vmin=0.0, vmax=vmax, clip=True)
    cmap = plt.get_cmap(FIELD_CMAP)
    face_values = values[triangles].mean(axis=1)
    fig, axes = plt.subplots(1, 3, figsize=FIGSIZE, constrained_layout=True)
    for index, (ax, (label, view_axes, camera_sign)) in enumerate(zip(axes, views)):
        polygons, order = projected_faces(coords, triangles, view_axes, camera_sign)
        ax.add_collection(PolyCollection(polygons, facecolors=cmap(norm(face_values[order])), edgecolors="none", rasterized=True))
        set_projected_limits(ax, coords, view_axes)
        add_electrodes(ax, electrodes, view_axes, connect=False, view_name=label)
        target_xy = TARGET_MM[[view_axes[0], view_axes[1]]]
        ax.scatter(*target_xy, s=68, facecolors="none", edgecolors=GREEN, linewidth=1.7, zorder=8)
        ax.text(0.02, 0.98, f"{chr(65 + index)}  {label}", transform=ax.transAxes, va="top", fontsize=9, fontweight="bold", color=INK)
    scalar = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    colorbar = fig.colorbar(scalar, ax=axes, fraction=0.025, pad=0.018)
    colorbar.set_label("TImax (V/m), display capped at surface P99")
    save_figure(fig, "fig00_four_electrode_timax_surface")
    return {
        "units": "V/m",
        "colormap": FIELD_CMAP,
        "display_vmin_v_per_m": 0.0,
        "display_vmax_v_per_m": vmax,
        "display_cap_definition": "99th percentile of strictly positive final four-electrode GM-surface TImax nodes",
        "surface_max_v_per_m": float(values.max()),
    }


def render_carrier_fields() -> dict:
    with np.load(FINAL_ARCHIVE) as archive:
        centers = archive["element_centers_mm"]
        gray_mask = archive["whole_gray_matter_mask"].astype(bool)
        e1 = np.linalg.norm(archive["E1_V_per_m"], axis=1)
        e2 = np.linalg.norm(archive["E2_V_per_m"], axis=1)
        timax = archive["TImax_V_per_m"]
    slab = gray_mask & (np.abs(centers[:, 2] - TARGET_MM[2]) <= 1.0)
    fields = [("|E1|", e1), ("|E2|", e2), ("TImax", timax)]
    reference_values = np.concatenate([values[gray_mask] for _, values in fields])
    vmax = float(np.percentile(reference_values[reference_values > 0], 99))
    fig, axes = plt.subplots(1, 3, figsize=FIGSIZE, constrained_layout=True)
    image = None
    for index, (ax, (label, values)) in enumerate(zip(axes, fields)):
        order = np.argsort(values[slab])
        image = ax.scatter(centers[slab, 0][order], centers[slab, 1][order], c=values[slab][order], s=2.5, cmap=FIELD_CMAP, vmin=0, vmax=vmax, rasterized=True)
        ax.add_patch(Circle((TARGET_MM[0], TARGET_MM[1]), ROI_RADIUS_MM, fill=False, edgecolor=GREEN, linewidth=1.3))
        ax.scatter(TARGET_MM[0], TARGET_MM[1], marker="+", s=50, linewidths=1.4, color=GREEN)
        ax.text(0.02, 0.98, f"{chr(65 + index)}  {label}", transform=ax.transAxes, va="top", color="white", fontsize=9, fontweight="bold", bbox={"facecolor": "black", "alpha": 0.45, "edgecolor": "none", "pad": 2.5})
        ax.set(xlabel="L-R (mm)", ylabel="P-A (mm)", aspect="equal")
        for side in ("top", "right", "left", "bottom"):
            ax.spines[side].set_visible(True)
    colorbar = fig.colorbar(image, ax=axes, fraction=0.025, pad=0.018)
    colorbar.set_label("Electric-field magnitude (V/m), shared P99 display cap")
    save_figure(fig, "fig00_four_electrode_e1_e2_timax")
    return {
        "slice_plane": "axial slab",
        "slice_center_z_mm": float(TARGET_MM[2]),
        "slice_half_thickness_mm": 1.0,
        "units": "V/m",
        "shared_display_vmin_v_per_m": 0.0,
        "shared_display_vmax_v_per_m": vmax,
        "display_cap_definition": "pooled 99th percentile of positive |E1|, |E2|, and TImax over final four-electrode GM tetrahedra",
        "machine_data": "independent_fem/independent_timax_recompute.npz",
    }


def main() -> None:
    configure_style()
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    anatomy = render_anatomy_target()
    electrodes = cap_coordinates()
    mesh = mesh_io.read_msh(str(FINAL_MESH))
    values = np.asarray(mesh.elmdata[0].value, dtype=float)
    surface = surface_from_mesh(mesh, values)
    np.savez_compressed(FIGURE_DATA_DIR / "fig00_final_surface_context.npz", **surface)
    with (FIGURE_DATA_DIR / "fig00_inverse_electrode_montage.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["label", "x_mm", "y_mm", "z_mm", "current_mA_peak", "carrier", "coordinate_space"])
        for label in ELECTRODE_LABELS:
            writer.writerow([label, *electrodes[label].tolist(), CURRENT_MA[label], CARRIER[label], "ernie individual conform physical space"])
    render_montage(surface, electrodes)
    surface_metadata = render_surface_field(surface, electrodes)
    carrier_metadata = render_carrier_fields()
    metadata = {
        "schema": "qlanalyser.simnibs.inverse.publication_context.v1",
        "run_id": "ernie-independent-fem-f5p5-fc3cp3-20260729",
        "source_mesh": "independent_fem/four_electrode_timax.msh",
        "source_archive": "independent_fem/independent_timax_recompute.npz",
        "anatomy_target_figure": anatomy,
        "electrode_montage": {
            "selected_montage": ["F5-P5", "FC3-CP3"],
            "electrode_coordinates": "figures/figure_data/fig00_inverse_electrode_montage.csv",
            "coordinate_space": "ernie individual conform physical space",
            "roi_marker_interpretation": "The green ring is the ROI center projected into each 2D view; it is not a scalp or cortical contact location.",
        },
        "carrier_field_figure": carrier_metadata,
        "surface_field_figure": surface_metadata,
        "surface_machine_data": "figures/figure_data/fig00_final_surface_context.npz",
        "publication_boundary": "Demo-only while F5-FC3 point contact and formal-study prerequisites remain unresolved.",
    }
    (FIGURE_DATA_DIR / "fig00_publication_context.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
