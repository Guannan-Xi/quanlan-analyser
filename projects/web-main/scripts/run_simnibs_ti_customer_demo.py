"""Run the official Ernie two-pair TI example and export auditable analysis data.

This script must run inside the SimNIBS environment. It performs numerical work
only; report rendering is handled by ``build_simnibs_ti_customer_delivery.py``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

# Directly invoking a Windows Conda environment does not activate its DLL path.
# Register it before importing NumPy/SimNIBS, whose BLAS is loaded lazily.
if sys.platform == "win32":
    env_root = Path(sys.executable).resolve().parent
    dll_dir = env_root / "Library" / "bin"
    search_dirs = [dll_dir, env_root / "Scripts", env_root]
    os.environ["PATH"] = os.pathsep.join(str(path) for path in search_dirs) + os.pathsep + os.environ.get("PATH", "")
    if dll_dir.is_dir() and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(dll_dir))

import h5py
import nibabel as nib
import numpy as np
import simnibs
from simnibs import ElementTags, mesh_io, run_simnibs, sim_struct
from simnibs.utils import TI_utils
from simnibs.utils import transformations
from simnibs.utils.csv_reader import read_csv_positions
from simnibs.utils.file_finder import SubjectFiles


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "simnibs_examples_v4_1" / "extracted"
DEFAULT_OUTPUT = ROOT / "outputs" / "simnibs_customer_ti_demo_ernie_20260728" / "raw_simnibs"
RUN_ID = "ernie-forward-ti-f5p5-f6p6-1ma-20260728"
MNI_TARGET = np.array([-37.0, -21.0, 58.0])
ROI_RADIUS_MM = 10.0
CURRENT_AMPLITUDE_CONVENTION = "peak"
FIELD_AMPLITUDE_CONVENTION = "maximum_envelope_amplitude"
TARGET_REGION_DEFINITION = "SimNIBS ElementTags.GM (tag 2) tetrahedra with barycenters inside the 10 mm target sphere"
OFF_TARGET_REGION_DEFINITION = "All SimNIBS ElementTags.GM (tag 2) tetrahedra outside the target ROI; no atlas exclusion or transition buffer"
WHOLE_GM_REGION_DEFINITION = "All SimNIBS ElementTags.GM (tag 2) tetrahedra in the Ernie head mesh"
THRESHOLD_QUANTILE = 0.999
THRESHOLD_COVERAGE_DENOMINATOR = "same_region_volume_mm3"
THRESHOLD_COVERAGE_DEFINITION = (
    "100 * sum(volume_mm3 of included tetrahedra with TImax >= threshold_v_per_m) "
    "/ volume_mm3 of the same region"
)
HIGH_TAIL_ALLOCATION_DEFINITION = (
    "100 * region suprathreshold_volume_mm3 / whole-gray-matter suprathreshold_volume_mm3"
)
WEIGHTED_QUANTILE_METHOD = "weighted_empirical_cdf_inverted_cdf_no_interpolation"
WEIGHTED_QUANTILE_DEFINITION = (
    "Filter to included elements with finite values, finite positive tetrahedron-volume weights; "
    "sort values ascending; compute cumulative tetrahedron volume; return the first sorted value "
    "whose cumulative volume is >= probability * total volume (numpy.searchsorted side='left'); "
    "do not interpolate. Probability 0 returns the minimum and probability 1 returns the maximum."
)
TIMAX_RECOMPUTE_METHOD_ID = "independent_reference_simnibs_4_6_0_get_maxTI_formula"
TIMAX_RECOMPUTE_TOLERANCE_V_PER_M = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--reuse-fem", action="store_true", help="Reuse complete FEM meshes if present")
    parser.add_argument("--rebuild-surface", action="store_true", help="Recompute the GM-constrained surface projection")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def find_m2m_ernie(root: Path) -> Path:
    direct = root / "m2m_ernie"
    candidates = [direct] if direct.is_dir() else []
    candidates.extend(path for path in root.rglob("m2m_ernie") if path.is_dir())
    valid = [path for path in candidates if (path / "ernie.msh").is_file()]
    unique = list(dict.fromkeys(path.resolve() for path in valid))
    if len(unique) != 1:
        raise RuntimeError(f"Expected one complete m2m_ernie under {root}, found {len(unique)}")
    return unique[0]


def field(mesh: mesh_io.Msh, name: str) -> mesh_io.ElementData:
    try:
        return mesh.field[name]
    except KeyError as exc:
        available = ", ".join(item.field_name for item in mesh.elmdata)
        raise RuntimeError(f"Missing field {name!r}; available: {available}") from exc


def weighted_quantile(values: np.ndarray, weights: np.ndarray, probability: float) -> float:
    if not 0.0 <= probability <= 1.0:
        raise ValueError("weighted quantile probability must be between 0 and 1")
    order = np.argsort(values)
    sorted_values = values[order]
    sorted_weights = weights[order]
    cumulative = np.cumsum(sorted_weights)
    index = int(np.searchsorted(cumulative, probability * cumulative[-1], side="left"))
    return float(sorted_values[min(index, sorted_values.size - 1)])


def recompute_timax_reference(e1: np.ndarray, e2: np.ndarray) -> np.ndarray:
    """Recompute TImax from the documented SimNIBS formula without calling get_maxTI."""
    first = np.array(e1, dtype=np.float64, copy=True)
    second = np.array(e2, dtype=np.float64, copy=True)
    if first.shape != second.shape or first.ndim != 2 or first.shape[1] != 3:
        raise ValueError("E1 and E2 must have matching (n, 3) shapes")

    swap = np.linalg.norm(second, axis=1) > np.linalg.norm(first, axis=1)
    original_first = first.copy()
    first[swap] = second[swap]
    second[swap] = original_first[swap]
    second[np.sum(first * second, axis=1) < 0] *= -1

    norm_first = np.linalg.norm(first, axis=1)
    norm_second = np.linalg.norm(second, axis=1)
    dot = np.sum(first * second, axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        cos_alpha = dot / (norm_first * norm_second)
        result = 2 * np.linalg.norm(np.cross(second, first - second), axis=1) / np.linalg.norm(first - second, axis=1)
    parallel = norm_second <= norm_first * cos_alpha
    result[parallel] = 2 * norm_second[parallel]
    return result


def describe(values: np.ndarray, weights: np.ndarray, mask: np.ndarray, threshold: float) -> dict:
    valid = mask & np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    data = values[valid]
    volume = weights[valid]
    if data.size == 0:
        raise RuntimeError("ROI statistic contains no finite tetrahedra")
    total_volume = float(volume.sum())
    suprathreshold = data >= threshold
    above = float(volume[suprathreshold].sum())
    return {
        "n_tetrahedra": int(data.size),
        "volume_mm3": total_volume,
        "mean": float(np.average(data, weights=volume)),
        "median": weighted_quantile(data, volume, 0.50),
        "p05": weighted_quantile(data, volume, 0.05),
        "p95": weighted_quantile(data, volume, 0.95),
        "max": float(np.max(data)),
        "threshold_v_per_m": float(threshold),
        "suprathreshold_n_tetrahedra": int(np.count_nonzero(suprathreshold)),
        "suprathreshold_volume_mm3": above,
        "threshold_coverage_denominator": THRESHOLD_COVERAGE_DENOMINATOR,
        "threshold_coverage_definition": THRESHOLD_COVERAGE_DEFINITION,
        "threshold_coverage_pct": 100.0 * above / total_volume,
    }


def add_four_electrode_montage(session, currents: list[float]):
    tdcs = session.add_tdcslist()
    tdcs.currents = currents
    for channel, centre in ((1, "F5"), (2, "P5"), (3, "F6"), (4, "P6")):
        electrode = tdcs.add_electrode()
        electrode.channelnr = channel
        electrode.centre = centre
        electrode.shape = "ellipse"
        electrode.dimensions = [40, 40]
        electrode.thickness = 2
    return tdcs


def run_fem(m2m: Path, fem_dir: Path, reuse: bool) -> tuple[Path, Path]:
    mesh_1 = fem_dir / "ernie_TDCS_1_scalar.msh"
    mesh_2 = fem_dir / "ernie_TDCS_2_scalar.msh"
    if reuse and mesh_1.is_file() and mesh_2.is_file():
        return mesh_1, mesh_2

    if fem_dir.exists():
        shutil.rmtree(fem_dir)
    fem_dir.mkdir(parents=True)
    session = sim_struct.SESSION()
    session.subpath = str(m2m)
    session.pathfem = str(fem_dir)
    session.open_in_gmsh = False
    session.fields = "eEjJ"
    # Both carrier-field solves use the same four-electrode geometry. Zero-current
    # channels keep inactive electrodes in the mesh so E1 and E2 share one exact
    # spatial discretization, rather than combining fields from independently
    # deformed scalp meshes.
    pair_1 = add_four_electrode_montage(session, [0.001, -0.001, 0.0, 0.0])
    pair_2 = session.add_tdcslist(deepcopy(pair_1))
    pair_2.currents = [0.0, 0.0, 0.001, -0.001]
    run_simnibs(session)
    if not mesh_1.is_file() or not mesh_2.is_file():
        raise RuntimeError("SimNIBS completed without both expected scalar meshes")
    return mesh_1, mesh_2


def crop_native_tissues(mesh: mesh_io.Msh) -> mesh_io.Msh:
    tags_keep = np.hstack(
        (
            np.arange(ElementTags.TH_START, ElementTags.SALINE_START - 1),
            np.arange(ElementTags.TH_SURFACE_START, ElementTags.SALINE_TH_SURFACE_START - 1),
        )
    )
    return mesh.crop_mesh(tags=tags_keep)


def assert_same_mesh(first: mesh_io.Msh, second: mesh_io.Msh) -> None:
    checks = (
        first.nodes.node_coord.shape == second.nodes.node_coord.shape,
        first.elm.node_number_list.shape == second.elm.node_number_list.shape,
        np.allclose(first.nodes.node_coord, second.nodes.node_coord),
        np.array_equal(first.elm.node_number_list, second.elm.node_number_list),
        np.array_equal(first.elm.elm_type, second.elm.elm_type),
        np.array_equal(first.elm.tag1, second.elm.tag1),
    )
    if not all(checks):
        raise RuntimeError("The two cropped FEM result meshes are not element-wise aligned")


def cap_coordinates(m2m: Path, labels: list[str]) -> dict[str, list[float]]:
    cap_path = Path(SubjectFiles(subpath=str(m2m)).eeg_cap_1010)
    _, coordinates, _, names, _, _ = read_csv_positions(str(cap_path))
    mapping = {str(name): np.asarray(coord, dtype=float) for name, coord in zip(names, coordinates)}
    missing = [label for label in labels if label not in mapping]
    if missing:
        raise RuntimeError(f"EEG cap lacks electrode labels: {missing}")
    return {label: mapping[label].tolist() for label in labels}


def extract_slices(m2m: Path, volume_paths: dict[str, Path], target_subject: np.ndarray, out: Path) -> None:
    subject = SubjectFiles(subpath=str(m2m))
    t1_image = nib.as_closest_canonical(nib.load(subject.reference_volume))
    t1 = np.asarray(t1_image.dataobj, dtype=np.float32)
    target_voxel = nib.affines.apply_affine(np.linalg.inv(t1_image.affine), target_subject)
    index = np.rint(target_voxel).astype(int)
    index = np.clip(index, 0, np.array(t1.shape[:3]) - 1)

    arrays: dict[str, np.ndarray] = {
        "t1_affine": np.asarray(t1_image.affine, dtype=np.float64),
        "target_voxel": target_voxel.astype(np.float64),
        "target_index": index.astype(np.int32),
        "voxel_sizes_mm": np.asarray(t1_image.header.get_zooms()[:3], dtype=np.float64),
    }
    tissue_image = nib.as_closest_canonical(nib.load(subject.final_labels))
    if tissue_image.shape[:3] != t1_image.shape[:3] or not np.allclose(tissue_image.affine, t1_image.affine):
        raise RuntimeError("Canonical tissue labels do not align with canonical T1")
    tissue_labels = np.asarray(tissue_image.dataobj, dtype=np.int16)
    volumes = {"t1": t1, "tissues": tissue_labels}
    for name, path in volume_paths.items():
        image = nib.as_closest_canonical(nib.load(path))
        if image.shape[:3] != t1_image.shape[:3] or not np.allclose(image.affine, t1_image.affine):
            raise RuntimeError(f"Canonical NIfTI for {name} does not align with canonical T1")
        values = np.asarray(image.dataobj, dtype=np.float32)
        if values.ndim != 3:
            raise RuntimeError(f"Expected scalar 3D NIfTI for {name}, got {values.shape}")
        volumes[name] = values

    x, y, z = index
    for name, values in volumes.items():
        arrays[f"{name}_sagittal"] = np.asarray(values[x, :, :], dtype=np.float32)
        arrays[f"{name}_coronal"] = np.asarray(values[:, y, :], dtype=np.float32)
        arrays[f"{name}_axial"] = np.asarray(values[:, :, z], dtype=np.float32)
    np.savez_compressed(out, **arrays)


def export_surface(mesh: mesh_io.Msh, ti_values: np.ndarray, out: Path) -> None:
    surface = mesh.crop_mesh(tags=[ElementTags.GM_TH_SURFACE])
    if surface.elm.nr == 0:
        raise RuntimeError("GM surface is missing from result mesh")
    source = mesh_io.ElementData(ti_values, name="TImax", mesh=mesh)
    gm_tetrahedra = mesh.elm.elm_number[
        (mesh.elm.elm_type == 4) & (mesh.elm.tag1 == ElementTags.GM)
    ]
    if gm_tetrahedra.size == 0:
        raise RuntimeError("Gray-matter tetrahedra are missing from result mesh")
    surface_values = np.asarray(
        source.interpolate_to_surface(surface, out_fill="nearest", th_indices=gm_tetrahedra).value,
        dtype=np.float32,
    )
    gm_values = np.asarray(ti_values, dtype=float)[gm_tetrahedra - 1]
    tolerance = max(1e-7, float(np.max(gm_values)) * 1e-6)
    if np.any(~np.isfinite(surface_values)) or float(np.max(surface_values)) > float(np.max(gm_values)) + tolerance:
        raise RuntimeError("GM-constrained surface interpolation exceeded the gray-matter volume range")
    triangles = np.asarray(surface.elm.node_number_list[:, :3], dtype=np.int32) - 1
    np.savez_compressed(
        out,
        coordinates=np.asarray(surface.nodes.node_coord, dtype=np.float32),
        triangles=triangles,
        timax=surface_values,
    )


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    m2m = find_m2m_ernie(args.dataset_root.resolve())
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    fem_dir = output / "fem"
    fields_dir = output / "fields"
    tables_dir = output / "tables"
    analysis_dir = output / "analysis"
    for directory in (fields_dir, tables_dir, analysis_dir):
        directory.mkdir(parents=True, exist_ok=True)

    mesh_1_path, mesh_2_path = run_fem(m2m, fem_dir, args.reuse_fem)
    mesh_1 = crop_native_tissues(mesh_io.read_msh(str(mesh_1_path)))
    mesh_2 = crop_native_tissues(mesh_io.read_msh(str(mesh_2_path)))
    assert_same_mesh(mesh_1, mesh_2)

    e1 = np.asarray(field(mesh_1, "E").value, dtype=np.float64)
    e2 = np.asarray(field(mesh_2, "E").value, dtype=np.float64)
    j1 = np.asarray(field(mesh_1, "J").value, dtype=np.float64)
    j2 = np.asarray(field(mesh_2, "J").value, dtype=np.float64)
    mag_e1 = np.linalg.norm(e1, axis=1)
    mag_e2 = np.linalg.norm(e2, axis=1)
    ti_max = np.asarray(TI_utils.get_maxTI(e1, e2), dtype=np.float64)
    if not all(np.all(np.isfinite(values)) for values in (e1, e2, j1, j2, ti_max)):
        raise RuntimeError("Non-finite values detected in FEM fields")

    combined = deepcopy(mesh_1)
    combined.elmdata = []
    combined.add_element_field(e1, "E1")
    combined.add_element_field(e2, "E2")
    combined.add_element_field(mag_e1, "magnE1")
    combined.add_element_field(mag_e2, "magnE2")
    combined.add_element_field(ti_max, "TImax")
    combined_path = fields_dir / "ernie_TI_fields.msh"
    mesh_io.write_msh(combined, str(combined_path))

    volume_paths = {
        name: fields_dir / f"ernie_TI_native_{name}.nii.gz"
        for name in ("magnE1", "magnE2", "TImax")
    }
    vector_volume_paths = {
        name: fields_dir / f"ernie_TI_native_{name}.nii.gz"
        for name in ("E1", "E2")
    }
    reusable_volumes = [*volume_paths.values(), *vector_volume_paths.values()]
    if not (args.reuse_fem and all(path.is_file() for path in reusable_volumes)):
        volume_prefix = fields_dir / "ernie_TI_native"
        transformations.interpolate_to_volume(
            combined,
            str(m2m),
            str(volume_prefix),
            method="linear",
            continuous=False,
            keep_tissues=[ElementTags.WM, ElementTags.GM],
        )
    missing_volumes = [str(path) for path in volume_paths.values() if not path.is_file()]
    if missing_volumes:
        raise RuntimeError(f"Missing interpolated scalar volumes: {missing_volumes}")

    element_type = np.asarray(combined.elm.elm_type)
    tags = np.asarray(combined.elm.tag1)
    centers = np.asarray(combined.elements_baricenters().value, dtype=np.float64)
    volumes = np.asarray(combined.elements_volumes_and_areas().value, dtype=np.float64)
    tetrahedra = element_type == 4
    gray_matter = tetrahedra & (tags == int(ElementTags.GM))
    timax_reference = recompute_timax_reference(e1[tetrahedra], e2[tetrahedra])
    delivered_timax = ti_max[tetrahedra]
    timax_abs_error = np.abs(timax_reference - delivered_timax)
    timax_recompute_qc = {
        "schema_version": "simnibs.timax_recompute_qc.v1",
        "run_id": RUN_ID,
        "status": "pass" if (
            np.all(np.isfinite(timax_reference))
            and np.all(np.isfinite(delivered_timax))
            and np.all(timax_abs_error <= TIMAX_RECOMPUTE_TOLERANCE_V_PER_M)
        ) else "fail",
        "element_domain": "all tetrahedra in the delivered native head mesh",
        "element_count": int(delivered_timax.size),
        "reference_finite_count": int(np.count_nonzero(np.isfinite(timax_reference))),
        "delivered_finite_count": int(np.count_nonzero(np.isfinite(delivered_timax))),
        "exact_equal": bool(np.array_equal(timax_reference, delivered_timax)),
        "allclose": bool(np.allclose(timax_reference, delivered_timax, rtol=0.0, atol=TIMAX_RECOMPUTE_TOLERANCE_V_PER_M)),
        "absolute_tolerance_v_per_m": TIMAX_RECOMPUTE_TOLERANCE_V_PER_M,
        "max_abs_error_v_per_m": float(np.max(timax_abs_error)),
        "mean_abs_error_v_per_m": float(np.mean(timax_abs_error)),
        "reference_method_id": TIMAX_RECOMPUTE_METHOD_ID,
        "delivered_method_id": "simnibs_4_6_0_TI_utils_get_maxTI_grossman2017",
        "reference_implementation": "Independent local implementation of the documented vector ordering, sign normalization, and two-branch TImax formula; TI_utils.get_maxTI is not called by the reference function.",
    }
    timax_recompute_path = analysis_dir / "timax_recompute_qc.json"
    timax_recompute_path.write_text(json.dumps(timax_recompute_qc, ensure_ascii=False, indent=2), encoding="utf-8")
    if timax_recompute_qc["status"] != "pass":
        raise RuntimeError(f"TImax independent recomputation failed: {timax_recompute_qc}")
    target_subject = np.asarray(simnibs.mni2subject_coords(MNI_TARGET, str(m2m)), dtype=float)
    distance = np.linalg.norm(centers - target_subject, axis=1)
    target_mask = gray_matter & (distance < ROI_RADIUS_MM)
    off_target_mask = gray_matter & ~target_mask
    if np.count_nonzero(target_mask) < 10:
        raise RuntimeError("Transformed M1 ROI contains too few GM tetrahedra")

    gm_values = ti_max[gray_matter]
    gm_volumes = volumes[gray_matter]
    brain_max = float(np.max(gm_values))
    gm_weighted_quantiles = {
        "p99": weighted_quantile(gm_values, gm_volumes, 0.99),
        "p99_9": weighted_quantile(gm_values, gm_volumes, THRESHOLD_QUANTILE),
        "p99_99": weighted_quantile(gm_values, gm_volumes, 0.9999),
    }
    # A single boundary tetrahedron can dominate argmax. Use a volume-weighted
    # upper-tail percentile for descriptive coverage and retain argmax as QC.
    display_threshold = gm_weighted_quantiles["p99_9"]
    target_stats = describe(ti_max, volumes, target_mask, display_threshold)
    off_target_stats = describe(ti_max, volumes, off_target_mask, display_threshold)
    whole_gm_stats = describe(ti_max, volumes, gray_matter, display_threshold)
    whole_gm_high_tail_volume = whole_gm_stats["suprathreshold_volume_mm3"]
    for stats in (target_stats, off_target_stats, whole_gm_stats):
        stats["whole_gm_high_tail_allocation_pct"] = (
            100.0 * stats["suprathreshold_volume_mm3"] / whole_gm_high_tail_volume
        )
        stats["whole_gm_high_tail_allocation_definition"] = HIGH_TAIL_ALLOCATION_DEFINITION
    peak_candidates = np.where(gray_matter)[0]
    peak_index = int(peak_candidates[np.argmax(ti_max[gray_matter])])
    peak_subject = centers[peak_index]
    peak_distance = float(np.linalg.norm(peak_subject - target_subject))
    peak_nodes = np.asarray(combined.elm.node_number_list[peak_index, :4], dtype=int)
    tetra_node_numbers = np.asarray(combined.elm.node_number_list[:, :4], dtype=int)
    shared_node_counts = np.isin(tetra_node_numbers, peak_nodes).sum(axis=1)
    shared_node_counts[peak_index] = 0
    shared_face_tags = sorted(set(tags[tetrahedra & (shared_node_counts >= 3)].astype(int).tolist()))
    shared_edge_tags = sorted(set(tags[tetrahedra & (shared_node_counts >= 2)].astype(int).tolist()))
    shared_face_tissues = [
        {"tag": tag, "name": ElementTags(tag).name if tag in ElementTags._value2member_map_ else "UNKNOWN"}
        for tag in shared_face_tags
    ]
    peak_element_qc = {
        "array_index_zero_based": peak_index,
        "msh_element_number": int(np.asarray(combined.elm.elm_number)[peak_index]),
        "tissue_tag": int(tags[peak_index]),
        "value_v_per_m": float(ti_max[peak_index]),
        "volume_mm3": float(volumes[peak_index]),
        "shared_face_neighbor_tissue_tags": shared_face_tags,
        "shared_face_neighbor_tissues": shared_face_tissues,
        "shared_edge_or_face_neighbor_tissue_tags": shared_edge_tags,
        "is_gm_csf_interface": int(ElementTags.GM) in shared_face_tags and int(ElementTags.CSF) in shared_face_tags,
    }

    roi_rows = []
    for name, role, definition, stats in (
        ("Left M1 spherical ROI", "target", TARGET_REGION_DEFINITION, target_stats),
        ("Gray matter outside target ROI", "off-target", OFF_TARGET_REGION_DEFINITION, off_target_stats),
        ("Whole gray matter", "reference", WHOLE_GM_REGION_DEFINITION, whole_gm_stats),
    ):
        roi_rows.append({
            "roi": name,
            "role": role,
            "definition": definition,
            **stats,
            "weighted_quantile_method": WEIGHTED_QUANTILE_METHOD,
            "weighted_quantile_definition": WEIGHTED_QUANTILE_DEFINITION,
            "run_id": RUN_ID,
        })
    write_csv(
        tables_dir / "roi_metrics.csv",
        roi_rows,
        [
            "roi", "role", "definition", "n_tetrahedra", "volume_mm3", "mean", "median", "p05", "p95", "max",
            "threshold_v_per_m", "suprathreshold_n_tetrahedra", "suprathreshold_volume_mm3", "threshold_coverage_denominator",
            "threshold_coverage_definition", "threshold_coverage_pct", "whole_gm_high_tail_allocation_pct",
            "whole_gm_high_tail_allocation_definition", "weighted_quantile_method",
            "weighted_quantile_definition", "run_id",
        ],
    )

    offsets = [
        ("Baseline", np.array([0.0, 0.0, 0.0])),
        ("L-R -3 mm", np.array([-3.0, 0.0, 0.0])),
        ("L-R +3 mm", np.array([3.0, 0.0, 0.0])),
        ("P-A -3 mm", np.array([0.0, -3.0, 0.0])),
        ("P-A +3 mm", np.array([0.0, 3.0, 0.0])),
        ("I-S -3 mm", np.array([0.0, 0.0, -3.0])),
        ("I-S +3 mm", np.array([0.0, 0.0, 3.0])),
    ]
    robustness_rows = []
    for label, offset in offsets:
        shifted_distance = np.linalg.norm(centers - (target_subject + offset), axis=1)
        shifted_mask = gray_matter & (shifted_distance < ROI_RADIUS_MM)
        stats = describe(ti_max, volumes, shifted_mask, display_threshold)
        shifted_off_target_stats = describe(ti_max, volumes, gray_matter & ~shifted_mask, display_threshold)
        shifted_peak_distance = float(np.linalg.norm(peak_subject - (target_subject + offset)))
        robustness_rows.append(
            {
                "factor": "ROI center displacement",
                "setting": label,
                "offset_x_mm": float(offset[0]),
                "offset_y_mm": float(offset[1]),
                "offset_z_mm": float(offset[2]),
                "mean_v_per_m": stats["mean"],
                "p95_v_per_m": stats["p95"],
                "off_target_p95_v_per_m": shifted_off_target_stats["p95"],
                "target_to_offtarget_p95_ratio": stats["p95"] / shifted_off_target_stats["p95"],
                "peak_distance_to_roi_center_mm": shifted_peak_distance,
                "peak_inside_roi": shifted_peak_distance < ROI_RADIUS_MM,
                "mean_change_pct": 100.0 * (stats["mean"] / target_stats["mean"] - 1.0),
                "p95_change_pct": 100.0 * (stats["p95"] / target_stats["p95"] - 1.0),
                "off_target_p95_change_pct": 100.0 * (shifted_off_target_stats["p95"] / off_target_stats["p95"] - 1.0),
                "weighted_quantile_method": WEIGHTED_QUANTILE_METHOD,
                "weighted_quantile_definition": WEIGHTED_QUANTILE_DEFINITION,
                "run_id": RUN_ID,
            }
        )
    write_csv(
        tables_dir / "robustness_roi_displacement.csv",
        robustness_rows,
        list(robustness_rows[0].keys()),
    )

    electrode_coords = cap_coordinates(m2m, ["F5", "P5", "F6", "P6"])
    electrode_rows = [
        {"circuit": "Carrier field E1", "electrode": "F5", "current_mA": 1.0, "current_amplitude_convention": CURRENT_AMPLITUDE_CONVENTION, "x_mm": electrode_coords["F5"][0], "y_mm": electrode_coords["F5"][1], "z_mm": electrode_coords["F5"][2], "run_id": RUN_ID},
        {"circuit": "Carrier field E1", "electrode": "P5", "current_mA": -1.0, "current_amplitude_convention": CURRENT_AMPLITUDE_CONVENTION, "x_mm": electrode_coords["P5"][0], "y_mm": electrode_coords["P5"][1], "z_mm": electrode_coords["P5"][2], "run_id": RUN_ID},
        {"circuit": "Carrier field E2", "electrode": "F6", "current_mA": 1.0, "current_amplitude_convention": CURRENT_AMPLITUDE_CONVENTION, "x_mm": electrode_coords["F6"][0], "y_mm": electrode_coords["F6"][1], "z_mm": electrode_coords["F6"][2], "run_id": RUN_ID},
        {"circuit": "Carrier field E2", "electrode": "P6", "current_mA": -1.0, "current_amplitude_convention": CURRENT_AMPLITUDE_CONVENTION, "x_mm": electrode_coords["P6"][0], "y_mm": electrode_coords["P6"][1], "z_mm": electrode_coords["P6"][2], "run_id": RUN_ID},
    ]
    write_csv(tables_dir / "electrode_currents.csv", electrode_rows, list(electrode_rows[0].keys()))

    conductivity_rows = []
    default_tdcs = sim_struct.SESSION().add_tdcslist()
    for tissue_tag, conductivity in enumerate(default_tdcs.cond, start=1):
        if conductivity.name is None or conductivity.value is None:
            continue
        conductivity_rows.append({
            "tissue_tag": tissue_tag,
            "tissue_name": conductivity.name,
            "conductivity_s_per_m": float(conductivity.value),
            "distribution_type": conductivity.distribution_type or "fixed",
            "source": f"SimNIBS {simnibs.__version__} sim_struct default TDCSLIST",
            "run_id": RUN_ID,
        })
    write_csv(tables_dir / "conductivities.csv", conductivity_rows, list(conductivity_rows[0].keys()))

    histogram_edges = np.linspace(0.0, brain_max, 41)
    target_hist, _ = np.histogram(ti_max[target_mask], bins=histogram_edges, weights=volumes[target_mask])
    off_hist, _ = np.histogram(ti_max[off_target_mask], bins=histogram_edges, weights=volumes[off_target_mask])
    np.savez_compressed(
        analysis_dir / "analysis_arrays.npz",
        histogram_edges=histogram_edges,
        target_hist_volume_mm3=target_hist,
        off_target_hist_volume_mm3=off_hist,
        target_subject=target_subject,
        target_mni=MNI_TARGET,
        electrode_labels=np.asarray(list(electrode_coords.keys())),
        electrode_coordinates=np.asarray(list(electrode_coords.values()), dtype=np.float64),
    )
    extract_slices(m2m, volume_paths, target_subject, analysis_dir / "slice_arrays.npz")
    surface_path = analysis_dir / "gm_surface_timax.npz"
    if args.rebuild_surface or not (args.reuse_fem and surface_path.is_file()):
        export_surface(combined, ti_max, surface_path)

    h5_path = fields_dir / "ernie_TI_analysis.h5"
    with h5py.File(h5_path, "w") as h5:
        h5.attrs["run_id"] = RUN_ID
        h5.attrs["coordinate_space"] = "SimNIBS subject conform space, mm"
        h5.attrs["field_unit"] = "V/m"
        h5.attrs["current_amplitude_convention"] = CURRENT_AMPLITUDE_CONVENTION
        h5.attrs["field_amplitude_convention"] = FIELD_AMPLITUDE_CONVENTION
        h5.attrs["target_region_definition"] = TARGET_REGION_DEFINITION
        h5.attrs["off_target_region_definition"] = OFF_TARGET_REGION_DEFINITION
        h5.attrs["threshold_coverage_denominator"] = THRESHOLD_COVERAGE_DENOMINATOR
        h5.attrs["threshold_coverage_definition"] = THRESHOLD_COVERAGE_DEFINITION
        h5.attrs["whole_gm_high_tail_allocation_definition"] = HIGH_TAIL_ALLOCATION_DEFINITION
        h5.attrs["threshold_definition"] = "whole-gray-matter volume-weighted P99.9 TImax"
        h5.attrs["threshold_quantile_probability"] = THRESHOLD_QUANTILE
        h5.attrs["threshold_value_v_per_m"] = display_threshold
        h5.attrs["whole_gm_weighted_p99_v_per_m"] = gm_weighted_quantiles["p99"]
        h5.attrs["whole_gm_weighted_p99_9_v_per_m"] = gm_weighted_quantiles["p99_9"]
        h5.attrs["whole_gm_weighted_p99_99_v_per_m"] = gm_weighted_quantiles["p99_99"]
        h5.attrs["peak_element_volume_mm3"] = peak_element_qc["volume_mm3"]
        h5.attrs["peak_element_is_gm_csf_interface"] = peak_element_qc["is_gm_csf_interface"]
        h5.attrs["peak_element_shared_face_neighbor_tissue_tags"] = np.asarray(shared_face_tags, dtype=np.int32)
        h5.attrs["weighted_quantile_method"] = WEIGHTED_QUANTILE_METHOD
        h5.attrs["weighted_quantile_definition"] = WEIGHTED_QUANTILE_DEFINITION
        h5.attrs["weighted_quantile_weight"] = "tetrahedron_volume_mm3"
        h5.attrs["weighted_quantile_interpolation"] = "none"
        h5.attrs["target_suprathreshold_n_tetrahedra"] = target_stats["suprathreshold_n_tetrahedra"]
        h5.attrs["off_target_suprathreshold_n_tetrahedra"] = off_target_stats["suprathreshold_n_tetrahedra"]
        h5.attrs["whole_gray_matter_suprathreshold_n_tetrahedra"] = whole_gm_stats["suprathreshold_n_tetrahedra"]
        h5.attrs["target_mni"] = MNI_TARGET
        h5.attrs["target_subject"] = target_subject
        h5.attrs["roi_radius_mm"] = ROI_RADIUS_MM
        for name, values in (
            ("element_centers_mm", centers[tetrahedra]),
            ("element_volumes_mm3", volumes[tetrahedra]),
            ("tissue_tags", tags[tetrahedra]),
            ("E1_V_per_m", e1[tetrahedra]),
            ("E2_V_per_m", e2[tetrahedra]),
            ("TImax_V_per_m", ti_max[tetrahedra]),
            ("target_roi_mask", target_mask[tetrahedra].astype(np.uint8)),
            ("suprathreshold_mask", (ti_max[tetrahedra] >= display_threshold).astype(np.uint8)),
        ):
            h5.create_dataset(name, data=values, compression="gzip", shuffle=True)

    roi_mask_mesh = deepcopy(combined)
    roi_mask_mesh.elmdata = []
    roi_mask_mesh.add_element_field(target_mask.astype(np.uint8), "Left_M1_ROI")
    roi_mask_path = fields_dir / "left_M1_roi.msh"
    mesh_io.write_msh(roi_mask_mesh, str(roi_mask_path))

    worst_mean = max(abs(row["mean_change_pct"]) for row in robustness_rows[1:])
    worst_p95 = max(abs(row["p95_change_pct"]) for row in robustness_rows[1:])
    model_files = SubjectFiles(subpath=str(m2m))
    required_model_files = {
        "head_mesh": Path(model_files.fnamehead),
        "T1": Path(model_files.reference_volume),
        "tissue_labels": Path(model_files.final_labels),
        "mni_to_subject": Path(model_files.mni2conf_nonl),
        "subject_to_mni": Path(model_files.conf2mni_nonl),
        "eeg_cap": Path(model_files.eeg_cap_1010),
        "charm_report": Path(model_files.summary_report),
    }
    model_completeness = {name: path.is_file() for name, path in required_model_files.items()}
    if not all(model_completeness.values()):
        raise RuntimeError(f"Incomplete Ernie model: {model_completeness}")

    result = {
        "schema_version": "simnibs.ti.raw.v1",
        "run_id": RUN_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "classification": "official example-subject demonstration; not customer MRI",
        "source": {
            "dataset": "SimNIBS example dataset",
            "dataset_release": "v4.1",
            "dataset_url": "https://github.com/simnibs/example-dataset/releases/download/v4.1/simnibs4_examples.zip",
            "m2m_path": str(m2m),
            "model_completeness": model_completeness,
            "conductivity_table": "tables/conductivities.csv",
            "conductivities_s_per_m": conductivity_rows,
        },
        "software": {
            "simnibs_version": simnibs.__version__,
            "python_version": platform.python_version(),
            "numpy_version": np.__version__,
            "h5py_version": h5py.__version__,
            "nibabel_version": nib.__version__,
            "platform": platform.platform(),
        },
        "protocol": {
            "pair_1": {"positive": "F5", "negative": "P5", "current_mA": [1.0, -1.0]},
            "pair_2": {"positive": "F6", "negative": "P6", "current_mA": [1.0, -1.0]},
            "current_amplitude_convention": CURRENT_AMPLITUDE_CONVENTION,
            "current_amplitude_note": "The +/-1 mA values are peak current amplitudes used to scale the quasi-static carrier fields, not RMS or peak-to-peak values.",
            "electrode_shape": "ellipse",
            "electrode_dimensions_mm": [40.0, 40.0],
            "electrode_thickness_mm": 2.0,
            "carrier_frequencies_hz": None,
            "frequency_note": "Quasi-static FEM computes spatial carrier fields; carrier frequencies are device-level protocol parameters and were not assigned in this example.",
        },
        "target": {
            "name": "Left M1 spherical ROI",
            "mni_coordinate_mm": MNI_TARGET.tolist(),
            "subject_coordinate_mm": target_subject.tolist(),
            "radius_mm": ROI_RADIUS_MM,
            "tissue": "gray matter (SimNIBS tag 2)",
            "definition_source": "SimNIBS roi_analysis_mni.py example",
        },
        "region_definition": {
            "analysis_domain": WHOLE_GM_REGION_DEFINITION,
            "target": TARGET_REGION_DEFINITION,
            "off_target": OFF_TARGET_REGION_DEFINITION,
            "additional_anatomical_exclusions": None,
            "transition_buffer_mm": 0.0,
        },
        "field_definition": {
            "E1": "Vector electric field scaled to F5(+1 mA peak)/P5(-1 mA peak)",
            "E2": "Vector electric field scaled to F6(+1 mA peak)/P6(-1 mA peak)",
            "TImax": "Maximum temporal-interference envelope amplitude computed with simnibs.utils.TI_utils.get_maxTI(E1, E2); not RMS or peak-to-peak",
            "field_amplitude_convention": FIELD_AMPLITUDE_CONVENTION,
        },
        "threshold": {
            "value_v_per_m": display_threshold,
            "definition": "Volume-weighted P99.9 of TImax across whole gray matter",
            "quantile_probability": THRESHOLD_QUANTILE,
            "reference_region": WHOLE_GM_REGION_DEFINITION,
            "weighted_quantiles_v_per_m": gm_weighted_quantiles,
            "argmax_excluded_as_anchor": True,
            "coverage_unit": "%",
            "coverage_denominator": THRESHOLD_COVERAGE_DENOMINATOR,
            "coverage_definition": THRESHOLD_COVERAGE_DEFINITION,
            "interpretation": "Descriptive upper-tail partition threshold; not a neural activation or clinical efficacy threshold. Whole-GM coverage is approximately 0.1% by the P99.9 definition and is not an empirical outcome or cross-subject comparison metric. The informative quantity is how that high-tail volume is allocated between target and off-target regions. The single-tetrahedron argmax is retained only as spatial and mesh-interface QC.",
        },
        "statistics": {
            "weighted_mean_weight": "tetrahedron_volume_mm3",
            "weighted_quantile": {
                "method_id": WEIGHTED_QUANTILE_METHOD,
                "definition": WEIGHTED_QUANTILE_DEFINITION,
                "weight": "tetrahedron_volume_mm3",
                "sort_order": "value_ascending",
                "selection_rule": "first cumulative weight >= probability * total weight",
                "search_side": "left",
                "interpolation": "none",
                "boundary_rule": "probability 0 returns minimum; probability 1 returns maximum",
                "reported_probabilities": [0.05, 0.50, 0.95, 0.99, 0.999, 0.9999],
            },
        },
        "results": {
            "target": target_stats,
            "off_target": off_target_stats,
            "whole_gray_matter": whole_gm_stats,
            "target_to_offtarget_p95_ratio": target_stats["p95"] / off_target_stats["p95"],
            "target_to_offtarget_mean_ratio": target_stats["mean"] / off_target_stats["mean"],
            "peak_subject_coordinate_mm": peak_subject.tolist(),
            "peak_distance_to_target_mm": peak_distance,
            "peak_element_qc": peak_element_qc,
            "peak_inside_target_roi": bool(peak_distance < ROI_RADIUS_MM),
            "suprathreshold_gray_matter_volume_mm3": whole_gm_stats["suprathreshold_volume_mm3"],
            "suprathreshold_gray_matter_fraction_pct": whole_gm_stats["threshold_coverage_pct"],
        },
        "robustness": {
            "analysis": "ROI center displacement by +/-3 mm along each subject-space axis",
            "worst_abs_mean_change_pct": worst_mean,
            "worst_abs_p95_change_pct": worst_p95,
            "worst_abs_off_target_p95_change_pct": max(abs(row["off_target_p95_change_pct"]) for row in robustness_rows),
            "target_to_offtarget_p95_ratio_min": min(row["target_to_offtarget_p95_ratio"] for row in robustness_rows),
            "target_to_offtarget_p95_ratio_max": max(row["target_to_offtarget_p95_ratio"] for row in robustness_rows),
            "target_to_offtarget_p95_ratio_crosses_one": min(row["target_to_offtarget_p95_ratio"] for row in robustness_rows) < 1.0 < max(row["target_to_offtarget_p95_ratio"] for row in robustness_rows),
            "peak_distance_to_shifted_roi_min_mm": min(row["peak_distance_to_roi_center_mm"] for row in robustness_rows),
            "peak_distance_to_shifted_roi_max_mm": max(row["peak_distance_to_roi_center_mm"] for row in robustness_rows),
            "peak_inside_any_shifted_roi": any(row["peak_inside_roi"] for row in robustness_rows),
            "electrode_position_perturbation": "not assessed",
            "conductivity_perturbation": "not assessed",
            "mesh_convergence": "not assessed",
        },
        "quality": {
            "configured_current_balance_a": [0.0, 0.0],
            "finite_fields": True,
            "mesh_alignment": True,
            "positive_tetrahedron_volumes": bool(np.all(volumes[tetrahedra] > 0)),
            "model_completeness": all(model_completeness.values()),
            "timax_recompute": timax_recompute_qc,
        },
        "artifacts": {
            "fem_mesh_1": str(mesh_1_path),
            "fem_mesh_2": str(mesh_2_path),
            "combined_mesh": str(combined_path),
            "hdf5": str(h5_path),
            "timax_recompute_qc": str(timax_recompute_path),
            "roi_mask_mesh": str(roi_mask_path),
            "native_nifti": {name: str(path) for name, path in volume_paths.items()},
        },
    }
    result_path = analysis_dir / "analysis_results.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "raw_manifest.json":
            manifest.append({"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    (output / "raw_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": "complete", "run_id": RUN_ID, "output": str(output), "files": len(manifest)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
