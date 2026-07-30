"""Render orthogonal TImax slab projections from delivered HDF5 arrays."""

import os
import sys
import json
from pathlib import Path

if sys.platform == "win32":
    env_root = Path(sys.executable).resolve().parent
    dll_dir = env_root / "Library" / "bin"
    os.environ["PATH"] = os.pathsep.join(str(path) for path in (dll_dir, env_root / "Scripts", env_root)) + os.pathsep + os.environ.get("PATH", "")
    if dll_dir.is_dir() and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(dll_dir))

import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "simnibs_inverse_ti_discrete_ernie_20260729"
H5 = OUT / "raw" / "fields" / "inverse_ti_results.h5"
TARGET = np.array([-41.0, -13.0, 66.0])


def render_field(centers, target_mask, off_mask, field, stem, figure_title, shared_vmax) -> dict:
    gray = target_mask | off_mask
    vmax = float(shared_vmax)
    off_indices = np.flatnonzero(off_mask)
    off_peak_index = int(off_indices[np.argmax(field[off_mask])])
    off_peak = centers[off_peak_index]
    off_peak_value = float(field[off_peak_index])
    layouts = [
        (0, 1, 2, "Sagittal", "P-A (mm)", "I-S (mm)"),
        (1, 0, 2, "Coronal", "L-R (mm)", "I-S (mm)"),
        (2, 0, 1, "Axial", "L-R (mm)", "P-A (mm)"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 10), constrained_layout=True)
    image = None
    for axis, (fixed, horizontal, vertical, plane_title, xlabel, ylabel) in zip(axes.flat[:3], layouts):
        slab = gray & (np.abs(centers[:, fixed] - TARGET[fixed]) <= 1.0)
        order = np.argsort(field[slab])
        x = centers[slab, horizontal][order]
        y = centers[slab, vertical][order]
        values = field[slab][order]
        image = axis.scatter(x, y, c=values, s=3, cmap="turbo", vmin=0, vmax=vmax, rasterized=True)
        circle = plt.Circle((TARGET[horizontal], TARGET[vertical]), 20, fill=False, color="#32CD32", lw=2)
        axis.add_patch(circle)
        axis.scatter([TARGET[horizontal]], [TARGET[vertical]], marker="+", color="#32CD32", s=90, linewidths=2)
        axis.set(title=f"{plane_title}: {TARGET[fixed]:.0f} mm", xlabel=xlabel, ylabel=ylabel, aspect="equal")
        axis.grid(False)
    axis = axes.flat[3]
    fixed, horizontal, vertical = 2, 0, 1
    slab = gray & (np.abs(centers[:, fixed] - off_peak[fixed]) <= 1.0)
    order = np.argsort(field[slab])
    image = axis.scatter(
        centers[slab, horizontal][order], centers[slab, vertical][order],
        c=field[slab][order], s=3, cmap="turbo", vmin=0, vmax=vmax, rasterized=True,
    )
    axis.scatter([off_peak[horizontal]], [off_peak[vertical]], marker="x", color="white", s=100, linewidths=2.5)
    axis.set(
        title=f"Exploratory single-tet off-target max: z={off_peak[fixed]:.0f} mm",
        xlabel="L-R (mm)", ylabel="P-A (mm)", aspect="equal",
    )
    axis.text(
        0.02, 0.98, f"single tetrahedron\n{off_peak_value:.3f} V/m\n({off_peak[0]:.0f}, {off_peak[1]:.0f}, {off_peak[2]:.0f}) mm",
        transform=axis.transAxes, va="top", color="white", fontsize=10,
        bbox={"facecolor": "black", "alpha": 0.65, "edgecolor": "none", "pad": 4},
    )
    colorbar = fig.colorbar(image, ax=axes, shrink=0.82, pad=0.02)
    colorbar.set_label(f"TImax (V/m); GM tetrahedra only; shared range 0-{vmax:.3f} V/m")
    fig.suptitle(figure_title, fontsize=17, fontweight="bold")
    figures = OUT / "figures"; figures.mkdir(exist_ok=True)
    fig.savefig(figures / f"{stem}.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(figures / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return {
        "off_target_peak_value_v_per_m": off_peak_value,
        "off_target_peak_conform_mm": [float(value) for value in off_peak],
        "distance_from_roi_center_mm": float(np.linalg.norm(off_peak - TARGET)),
        "roi_center_conform_mm": [float(value) for value in TARGET],
    }


def main() -> None:
    with h5py.File(H5, "r") as h5:
        centers = h5["mesh/element_centers_mm"][:]
        target_mask = h5["masks/target"][:].astype(bool)
        off_mask = h5["masks/off_target"][:].astype(bool)
        field = h5["candidates/F5-P5__FC3-CP3/TImax_V_per_m"][:]
    archive = np.load(OUT / "independent_fem" / "independent_timax_recompute.npz")
    recompute_target_mask = archive["target_mask"].astype(bool)
    recompute_off_mask = archive["off_target_mask"].astype(bool)
    recompute_field = archive["TImax_V_per_m"]
    shared_vmax = max(
        float(np.max(field[target_mask | off_mask])),
        float(np.max(recompute_field[recompute_target_mask | recompute_off_mask])),
    )
    search_extrema = render_field(
        centers, target_mask, off_mask, field,
        "figure_0_optimized_timax_slices",
        "Search field: F5-P5 + FC3-CP3",
        shared_vmax,
    )

    recompute_extrema = render_field(
        archive["element_centers_mm"],
        recompute_target_mask,
        recompute_off_mask,
        recompute_field,
        "figure_6_four_electrode_timax_slices",
        "Four-active-electrode field recomputation: F5-P5 + FC3-CP3",
        shared_vmax,
    )
    validation = json.loads((OUT / "independent_fem" / "independent_validation.json").read_text(encoding="utf-8"))
    target = validation["independent_metrics"]["target"]
    off_target = validation["independent_metrics"]["off_target"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), constrained_layout=True)
    labels = ["Target ROI", "Off-target GM"]
    colors = ["#176B50", "#A1433F"]
    x = np.arange(2)
    width = 0.34
    axes[0].bar(x - width / 2, [target["p95"], off_target["p95"]], width, label="P95", color="#245F8F")
    axes[0].bar(x + width / 2, [target["max"], off_target["max"]], width, label="Single-tet max", color="#A36B18")
    axes[0].set(ylabel="TImax (V/m)", title="Field intensity")
    axes[0].legend(frameon=False, fontsize=9)
    axes[1].bar(x, [target["threshold_coverage_pct"], off_target["threshold_coverage_pct"]], color=colors)
    axes[1].set(ylabel="Coverage (%)", title="Fixed-threshold coverage")
    axes[2].bar(x, [target["suprathreshold_volume_mm3"], off_target["suprathreshold_volume_mm3"]], color=colors)
    axes[2].set(ylabel="Volume (mm³)", title="Suprathreshold volume")
    for axis in axes:
        axis.set_xticks(x, labels)
        axis.tick_params(axis="x", rotation=12)
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", color="#d8dfdb", linewidth=0.7)
        axis.set_axisbelow(True)
    fig.suptitle("Four-active-electrode FEM: target and off-target results", fontsize=15, fontweight="bold")
    figures = OUT / "figures"
    fig.savefig(figures / "figure_7_four_electrode_quantitative.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(figures / "figure_7_four_electrode_quantitative.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    (OUT / "figures" / "spatial_extrema.json").write_text(
        json.dumps({
            "coordinate_space": "ernie individual conform space",
            "shared_color_scale_v_per_m": [0.0, shared_vmax],
            "search_field": search_extrema,
            "four_electrode_recompute_field": recompute_extrema,
        }, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__": main()
