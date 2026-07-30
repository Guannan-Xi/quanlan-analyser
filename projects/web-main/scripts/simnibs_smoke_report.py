"""Create auditable summary artifacts for a SimNIBS smoke-test mesh."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
import simnibs
from simnibs import mesh_io


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def describe(values: np.ndarray) -> dict[str, float | int]:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    return {
        "n": int(finite.size),
        "mean": float(np.mean(finite)),
        "median": float(np.median(finite)),
        "p95": float(np.percentile(finite, 95)),
        "max": float(np.max(finite)),
    }


def weighted_describe(values: np.ndarray, weights: np.ndarray) -> dict[str, float | int | str]:
    finite_values = np.asarray(values, dtype=float)
    finite_weights = np.asarray(weights, dtype=float)
    valid = np.isfinite(finite_values) & np.isfinite(finite_weights) & (finite_weights > 0)
    finite_values = finite_values[valid]
    finite_weights = finite_weights[valid]
    if finite_values.size == 0:
        raise ValueError("Weighted statistics require at least one finite value with positive weight")

    order = np.argsort(finite_values)
    sorted_values = finite_values[order]
    sorted_weights = finite_weights[order]
    cumulative = np.cumsum(sorted_weights)
    total_weight = float(cumulative[-1])

    def weighted_quantile(probability: float) -> float:
        index = int(np.searchsorted(cumulative, probability * total_weight, side="left"))
        return float(sorted_values[min(index, sorted_values.size - 1)])

    return {
        "n": int(finite_values.size),
        "volume_mm3": total_weight,
        "weighting": "tetrahedron_volume",
        "mean": float(np.average(finite_values, weights=finite_weights)),
        "median": weighted_quantile(0.50),
        "p95": weighted_quantile(0.95),
        "max": float(np.max(finite_values)),
    }


def field(mesh: mesh_io.Msh, name: str) -> np.ndarray:
    for item in mesh.elmdata:
        if item.field_name == name:
            return np.asarray(item.value)
    available = ", ".join(item.field_name for item in mesh.elmdata)
    raise ValueError(f"Missing field {name!r}; available fields: {available}")


def field_data(mesh: mesh_io.Msh, name: str) -> mesh_io.ElementData:
    for item in mesh.elmdata:
        if item.field_name == name:
            return item
    available = ", ".join(item.field_name for item in mesh.elmdata)
    raise ValueError(f"Missing field {name!r}; available fields: {available}")


def tetrahedron_volumes(mesh: mesh_io.Msh, volume_mask: np.ndarray) -> np.ndarray:
    tetrahedra = np.asarray(mesh.elm.node_number_list[volume_mask, :4], dtype=int) - 1
    coordinates = np.asarray(mesh.nodes.node_coord, dtype=float)[tetrahedra]
    edge_a = coordinates[:, 1] - coordinates[:, 0]
    edge_b = coordinates[:, 2] - coordinates[:, 0]
    edge_c = coordinates[:, 3] - coordinates[:, 0]
    volumes = np.abs(np.einsum("ij,ij->i", edge_a, np.cross(edge_b, edge_c))) / 6.0
    if not np.all(np.isfinite(volumes)) or np.any(volumes <= 0):
        raise ValueError("Result mesh contains non-finite or non-positive tetrahedron volumes")
    element_volumes = np.zeros(mesh.elm.nr, dtype=float)
    element_volumes[volume_mask] = volumes
    return element_volumes


def make_figure(
    mesh: mesh_io.Msh,
    magn_e_data: mesh_io.ElementData,
    tags: np.ndarray,
    volume_mask: np.ndarray,
    output: Path,
) -> dict[str, float]:
    magn_e = np.asarray(magn_e_data.value)
    color_max = float(np.percentile(magn_e[volume_mask], 99))
    inner_color_max = float(np.percentile(magn_e[volume_mask & (tags == 3)], 99))
    tag_data = mesh_io.ElementData(np.asarray(tags, dtype=float), mesh=mesh)
    coordinates = np.linspace(-102.0, 102.0, 321)
    horizontal_grid, vertical_grid = np.meshgrid(coordinates, coordinates)
    planes = (
        ("Axial (z = 0 mm)", 2, 0, 1, "x (mm)", "y (mm)"),
        ("Coronal (y = 0 mm)", 1, 0, 2, "x (mm)", "z (mm)"),
        ("Sagittal (x = 0 mm)", 0, 1, 2, "y (mm)", "z (mm)"),
    )
    fig, axes = plt.subplots(2, 3, figsize=(11.2, 7.0), constrained_layout=True)
    top_image = None
    inner_image = None
    panel_letters = ("A", "B", "C", "D", "E", "F")
    for column, (title, normal, horizontal, vertical, xlabel, ylabel) in enumerate(planes):
        points = np.zeros((horizontal_grid.size, 3), dtype=float)
        points[:, horizontal] = horizontal_grid.ravel()
        points[:, vertical] = vertical_grid.ravel()
        values = magn_e_data.interpolate_scattered(
            points, out_fill=np.nan, method="linear", continuous=False
        ).reshape(horizontal_grid.shape)
        tag_grid = tag_data.interpolate_scattered(
            points, out_fill=-1.0, method="assign"
        ).reshape(horizontal_grid.shape)

        top_axis = axes[0, column]
        top_image = top_axis.imshow(
            np.ma.masked_invalid(values),
            extent=(-102, 102, -102, 102),
            origin="lower",
            interpolation="nearest",
            cmap="viridis",
            vmin=0,
            vmax=color_max,
            rasterized=True,
        )
        top_axis.contour(
            coordinates,
            coordinates,
            tag_grid,
            levels=(3.5, 4.5),
            colors=("#F3F5F4", "#D7DDDA"),
            linewidths=(0.65, 0.65),
        )
        top_axis.contour(
            coordinates,
            coordinates,
            (tag_grid > 0).astype(float),
            levels=(0.5,),
            colors=("#27332E",),
            linewidths=(0.85,),
        )
        if column < 2:
            top_axis.scatter(
                (-95, 95),
                (0, 0),
                marker="o",
                s=28,
                facecolors=("#FFFFFF", "#FFFFFF"),
                edgecolors="#202A26",
                linewidths=0.8,
                zorder=4,
            )
            label_box = {"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 1.2}
            top_axis.text(
                -86, 8, "-1 mA", fontsize=6.5, ha="left", color="#202A26", bbox=label_box
            )
            top_axis.text(
                86, 8, "+1 mA", fontsize=6.5, ha="right", color="#202A26", bbox=label_box
            )

        inner_axis = axes[1, column]
        inner_values = np.ma.masked_where(tag_grid != 3, values)
        inner_image = inner_axis.imshow(
            inner_values,
            extent=(-102, 102, -102, 102),
            origin="lower",
            interpolation="nearest",
            cmap="viridis",
            vmin=0,
            vmax=inner_color_max,
            rasterized=True,
        )
        inner_axis.contour(
            coordinates,
            coordinates,
            (tag_grid == 3).astype(float),
            levels=(0.5,),
            colors=("#27332E",),
            linewidths=(0.85,),
        )

        for row, axis in enumerate((top_axis, inner_axis)):
            prefix = panel_letters[row * 3 + column]
            scope = "full model" if row == 0 else "inner region (tag 3)"
            axis.set_title(f"{prefix}  {title}; {scope}", fontsize=8.5)
            axis.set_xlabel(xlabel, fontsize=8)
            axis.set_ylabel(ylabel, fontsize=8)
            axis.set_aspect("equal")
            axis.set_xlim(-102, 102)
            axis.set_ylim(-102, 102)
            axis.set_xticks((-100, -50, 0, 50, 100))
            axis.set_yticks((-100, -50, 0, 50, 100))
            axis.tick_params(labelsize=7)
            axis.grid(False)

    full_colorbar = fig.colorbar(top_image, ax=axes[0, :], shrink=0.86, pad=0.015)
    full_colorbar.set_label("|E| (V/m), full-model P99 cap", fontsize=8)
    full_colorbar.ax.tick_params(labelsize=7)
    inner_colorbar = fig.colorbar(inner_image, ax=axes[1, :], shrink=0.86, pad=0.015)
    inner_colorbar.set_label("|E| (V/m), tag-3 P99 cap", fontsize=8)
    inner_colorbar.ax.tick_params(labelsize=7)
    fig.savefig(output, dpi=300, facecolor="white")
    plt.close(fig)
    return {
        "sampling": "SimNIBS tetrahedral interpolation on 321 x 321 planar grids",
        "interpolation": "linear within tissue; discontinuous across tissue boundaries",
        "full_model_color_max_v_per_m": color_max,
        "inner_tag_3_color_max_v_per_m": inner_color_max,
    }


def make_region_figure(
    magn_e: np.ndarray,
    volume_mask: np.ndarray,
    tags: np.ndarray,
    element_volumes: np.ndarray,
    output: Path,
) -> None:
    region_tags = [int(tag) for tag in np.unique(tags[volume_mask]) if int(tag) < 500]
    metrics = ("median", "mean", "p95", "max")
    x = np.arange(len(region_tags), dtype=float)
    width = 0.18
    colors = ("#456B62", "#6F8F85", "#C09248", "#9A534D")
    fig, axis = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
    for index, (metric, color) in enumerate(zip(metrics, colors)):
        values = [
            weighted_describe(
                magn_e[volume_mask & (tags == tag)],
                element_volumes[volume_mask & (tags == tag)],
            )[metric]
            for tag in region_tags
        ]
        axis.bar(x + (index - 1.5) * width, values, width, label=metric, color=color)
    axis.set_xticks(x, [f"Tag {tag}" for tag in region_tags])
    axis.set_ylabel("Electric-field magnitude (V/m)")
    axis.set_yscale("log")
    axis.legend(frameon=False, ncol=4, loc="upper left", title="Volume-weighted")
    axis.grid(axis="y", which="major", color="#D9DFDC", linewidth=0.7)
    for spine in axis.spines.values():
        spine.set_visible(True)
        spine.set_color("#7B8580")
    fig.savefig(output, dpi=300, facecolor="white")
    plt.close(fig)


def write_tables(
    output_dir: Path,
    magn_e: np.ndarray,
    magn_j: np.ndarray,
    volume_mask: np.ndarray,
    tags: np.ndarray,
    element_volumes: np.ndarray,
) -> None:
    rows = []
    for tag in np.unique(tags[volume_mask]):
        mask = volume_mask & (tags == tag)
        for field_name, unit, values in (
            ("magnE", "V/m", magn_e),
            ("magnJ", "A/m^2", magn_j),
        ):
            summary = weighted_describe(values[mask], element_volumes[mask])
            rows.append({"region_tag": int(tag), "field": field_name, "unit": unit, **summary})
    with (output_dir / "region_field_statistics.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "region_tag",
                "field",
                "unit",
                "n",
                "volume_mm3",
                "weighting",
                "mean",
                "median",
                "p95",
                "max",
            ),
        )
        writer.writeheader()
        writer.writerows(rows)

    with (output_dir / "electrode_currents.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(("electrode", "x_mm", "y_mm", "z_mm", "current_mA"))
        writer.writerow(("E1", 95.0, 0.0, 0.0, 1.0))
        writer.writerow(("E2", -95.0, 0.0, 0.0, -1.0))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mesh", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--skip-figures", action="store_true")
    args = parser.parse_args()

    mesh_path = args.mesh.resolve()
    output_dir = (args.output_dir or mesh_path.parent).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    mesh = mesh_io.read_msh(str(mesh_path))
    magn_e = field(mesh, "magnE")
    magn_j = field(mesh, "magnJ")
    element_types = np.asarray(mesh.elm.elm_type)
    tags = np.asarray(mesh.elm.tag1)
    volume_mask = element_types == 4
    element_volumes = tetrahedron_volumes(mesh, volume_mask)

    if args.skip_figures:
        figure_settings = {
            "status": "skipped",
            "reason": "Numerical statistics regenerated without the Matplotlib rendering step.",
        }
    else:
        figure_path = output_dir / "solver_smoke_test_magnE.png"
        figure_settings = make_figure(mesh, field_data(mesh, "magnE"), tags, volume_mask, figure_path)
        region_figure_path = output_dir / "solver_smoke_test_region_metrics.png"
        make_region_figure(magn_e, volume_mask, tags, element_volumes, region_figure_path)
    write_tables(output_dir, magn_e, magn_j, volume_mask, tags, element_volumes)

    stats = {
        "scope_note": "Synthetic sphere solver test only; not an anatomical, TI, or clinical result.",
        "units": {"magnE": "V/m", "magnJ": "A/m^2"},
        "all_elements": {"magnE": describe(magn_e), "magnJ": describe(magn_j)},
        "volume_elements": {
            "magnE": weighted_describe(magn_e[volume_mask], element_volumes[volume_mask]),
            "magnJ": weighted_describe(magn_j[volume_mask], element_volumes[volume_mask]),
        },
        "volume_elements_unweighted": {
            "magnE": describe(magn_e[volume_mask]),
            "magnJ": describe(magn_j[volume_mask]),
        },
        "volume_by_tissue_tag": {
            str(int(tag)): {
                "magnE": weighted_describe(
                    magn_e[volume_mask & (tags == tag)],
                    element_volumes[volume_mask & (tags == tag)],
                ),
                "magnJ": weighted_describe(
                    magn_j[volume_mask & (tags == tag)],
                    element_volumes[volume_mask & (tags == tag)],
                ),
            }
            for tag in np.unique(tags[volume_mask])
        },
    }
    stats_path = output_dir / "solver_smoke_test_statistics.json"
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    related_files = sorted(
        path for path in output_dir.iterdir() if path.is_file() and path.name != "manifest.json"
    )
    manifest = {
        "artifact_type": "simnibs_solver_smoke_test",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "classification": "engineering verification only",
        "limitations": [
            "Uses a synthetic three-layer sphere, not subject MRI anatomy.",
            "Contains one bipolar tDCS field solve, not two carrier fields or a TI envelope.",
            "Must not be used as evidence of subject-specific anatomy, targeting, TI, or clinical effects.",
        ],
        "stimulation": {
            "modality": "tDCS smoke test",
            "currents_mA": [1.0, -1.0],
            "electrode_shape": "ellipse",
            "electrode_dimensions_mm": [20.0, 20.0],
            "electrode_centers_mm": [[95.0, 0.0, 0.0], [-95.0, 0.0, 0.0]],
        },
        "software": {
            "simnibs": simnibs.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "mesh": {
            "path": str(mesh_path),
            "sha256": sha256(mesh_path),
            "nodes": int(mesh.nodes.node_coord.shape[0]),
            "elements": int(element_types.size),
            "volume_elements": int(np.count_nonzero(volume_mask)),
            "fields": [item.field_name for item in mesh.elmdata],
        },
        "figure": figure_settings,
        "artifacts": [
            {"file": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in related_files
        ],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if not args.skip_figures:
        print(f"Wrote {figure_path}")
    print(f"Wrote {stats_path}")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
