"""Reproduce the Violante et al. (2023) hippocampal TI protocol on ernie.

The script deliberately separates published parameters from implementation
substitutions. It solves two electrically isolated carrier-pair fields once,
then derives the published 1:1 and 1:3 current-ratio conditions by linear
superposition.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

# Direct invocation of a Windows Conda interpreter does not activate its DLL
# search path. Register it before NumPy and SimNIBS load their compiled modules.
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
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree

import simnibs
from simnibs import ElementTags, mesh_io, run_simnibs, sim_struct
from simnibs.utils import TI_utils, transformations


ROOT = Path(__file__).resolve().parents[1]
M2M = ROOT / "data" / "simnibs_examples_v4_1" / "extracted" / "m2m_ernie"
DEFAULT_OUTPUT = ROOT / "outputs" / "simnibs_ti_violante2023_reproduction_20260729"
ATLAS_ARCHIVE = Path.home() / "AppData/Local/Temp/ti_violante2023_research/HarvardOxford.tgz"
ATLAS_DIR = ROOT / "data" / "atlases" / "HarvardOxford"
ATLAS_VOLUME_NAME = "HarvardOxford-sub-maxprob-thr25-1mm.nii.gz"
ATLAS_XML_NAME = "HarvardOxford-Subcortical.xml"

PAPER = {
    "citation": "Violante et al., Nature Neuroscience 26, 1994-2004 (2023)",
    "doi": "10.1038/s41593-023-01456-8",
    "carrier_1_hz": 2005.0,
    "carrier_2_hz": 2000.0,
    "difference_hz": 5.0,
    "model_current_per_pair_peak_a": 0.001,
    "conditions": {
        "TI_1to1": {"pair_1_peak_a": 0.001, "pair_2_peak_a": 0.001},
        "TI_1to3": {"pair_1_peak_a": 0.0005, "pair_2_peak_a": 0.0015},
    },
    "model_electrode": "20 mm diameter circular electrode",
    "experimental_electrode": "15 x 15 mm square electrode with rounded corners",
    "reported_benchmarks": {
        "mida_ti_1to1_directional_envelope_v_per_m": {
            "summary": "median +/- s.d. across voxels",
            "hippocampus": [0.26, 0.04],
            "cortex_anterior": [0.18, 0.10],
            "cortex_middle": [0.12, 0.11],
            "cortex_posterior": [0.10, 0.09],
            "source": "Violante et al. 2023, Results, Fig. 1e",
        },
        "individualized_relative_hippocampal_exposure": {
            "summary": "participant median +/- s.d.; n=16; three regional values sum to approximately 1",
            "TI_1to1": {
                "hippocampus_anterior": [0.32, 0.03],
                "hippocampus_middle": [0.37, 0.02],
                "hippocampus_posterior": [0.31, 0.03],
            },
            "TI_1to3": {
                "hippocampus_anterior": [0.40, 0.02],
                "hippocampus_middle": [0.34, 0.01],
                "hippocampus_posterior": [0.26, 0.02],
            },
            "source": "Violante et al. 2023, Results, Fig. 2c",
        },
    },
}

# Standard-position substitutes chosen to preserve the published geometry:
# two left temporal electrodes approximately 5-6 cm apart and two contralateral
# return electrodes spanning the right frontal-to-posterior temporal scalp.
MONTAGE = {
    "e1": {"position": "FT7", "pair": 1, "polarity": 1},
    "e2": {"position": "Fp2", "pair": 1, "polarity": -1},
    "e3": {"position": "TP7", "pair": 2, "polarity": 1},
    "e4": {"position": "TP8", "pair": 2, "polarity": -1},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--reuse-fem", action="store_true")
    parser.add_argument("--atlas", type=Path, default=None)
    parser.add_argument("--atlas-xml", type=Path, default=None)
    parser.add_argument(
        "--allow-geometric-roi",
        action="store_true",
        help="Allow the documented MNI capsule fallback when the atlas is unavailable",
    )
    return parser.parse_args()


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    values = values[order]
    weights = weights[order]
    cutoff = q * weights.sum()
    return float(values[np.searchsorted(np.cumsum(weights), cutoff, side="left")])


def recompute_directional_ti(e1: np.ndarray, e2: np.ndarray, directions: np.ndarray) -> np.ndarray:
    unit = directions / np.linalg.norm(directions, axis=1)[:, None]
    return np.abs(
        np.abs(np.sum((e1 + e2) * unit, axis=1))
        - np.abs(np.sum((e1 - e2) * unit, axis=1))
    )


def recompute_timax(e1: np.ndarray, e2: np.ndarray) -> np.ndarray:
    first = np.array(e1, dtype=np.float64, copy=True)
    second = np.array(e2, dtype=np.float64, copy=True)
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


def summarize(values: np.ndarray, volumes: np.ndarray, mask: np.ndarray) -> dict:
    valid = mask & np.isfinite(values) & np.isfinite(volumes) & (volumes > 0)
    v = values[valid]
    w = volumes[valid]
    if v.size == 0:
        raise RuntimeError("ROI contains no finite positive-volume elements")
    return {
        "n_elements": int(v.size),
        "n_excluded_nonfinite_or_nonpositive": int(mask.sum() - v.size),
        "volume_mm3": float(w.sum()),
        "mean_v_per_m": float(np.average(v, weights=w)),
        "median_v_per_m": weighted_quantile(v, w, 0.5),
        "p95_v_per_m": weighted_quantile(v, w, 0.95),
        "max_v_per_m": float(v.max()),
    }


def focality_summary(
    values: np.ndarray,
    volumes: np.ndarray,
    target: np.ndarray,
    centers_mni: np.ndarray,
) -> dict:
    valid = np.isfinite(values) & np.isfinite(volumes) & (volumes > 0)
    threshold = weighted_quantile(values[valid], volumes[valid], 0.99)
    high_tail = valid & (values >= threshold)
    target_valid = target & valid
    off_target_valid = ~target & valid
    target_high = target & high_tail
    off_target_high = ~target & high_tail
    whole_high_volume = float(volumes[high_tail].sum())
    target_volume = float(volumes[target_valid].sum())
    off_target_volume = float(volumes[off_target_valid].sum())
    peak_index = int(np.nanargmax(np.where(valid, values, np.nan)))
    target_centroid = np.average(centers_mni[target_valid], axis=0, weights=volumes[target_valid])
    high_tail_centroid = np.average(centers_mni[high_tail], axis=0, weights=volumes[high_tail])
    return {
        "descriptive_threshold": {
            "definition": "whole-gray-matter volume-weighted P99 of the directional TI envelope",
            "value_v_per_m": float(threshold),
            "clinical_threshold": False,
        },
        "target_high_tail_capture_pct": 100.0 * float(volumes[target_high].sum()) / whole_high_volume,
        "target_coverage_pct": 100.0 * float(volumes[target_high].sum()) / target_volume,
        "off_target_coverage_pct": 100.0 * float(volumes[off_target_high].sum()) / off_target_volume,
        "off_target_high_tail_volume_mm3": float(volumes[off_target_high].sum()),
        "whole_gray_high_tail_volume_mm3": whole_high_volume,
        "peak_value_v_per_m": float(values[peak_index]),
        "peak_mni_mm": centers_mni[peak_index].tolist(),
        "peak_inside_target": bool(target[peak_index]),
        "peak_distance_to_target_centroid_mm": float(np.linalg.norm(centers_mni[peak_index] - target_centroid)),
        "high_tail_centroid_mni_mm": high_tail_centroid.tolist(),
        "high_tail_centroid_distance_to_target_centroid_mm": float(np.linalg.norm(high_tail_centroid - target_centroid)),
        "target_centroid_mni_mm": target_centroid.tolist(),
    }


def build_fem(out: Path, reuse: bool) -> list[Path]:
    fem = out / "raw" / "fem"
    expected = [fem / "ernie_TDCS_1_scalar.msh", fem / "ernie_TDCS_2_scalar.msh"]
    if reuse and all(path.is_file() for path in expected):
        return expected
    if fem.exists():
        shutil.rmtree(fem)
    fem.mkdir(parents=True)
    session = sim_struct.SESSION()
    session.subpath = str(M2M)
    session.pathfem = str(fem)
    session.open_in_gmsh = False
    session.fields = "eE"
    pair_1 = session.add_tdcslist()
    pair_1.currents = [0.001, -0.001, 0.0, 0.0]
    for channel, config in enumerate(MONTAGE.values(), start=1):
        electrode = pair_1.add_electrode()
        electrode.channelnr = channel
        electrode.centre = config["position"]
        electrode.shape = "ellipse"
        electrode.dimensions = [20.0, 20.0]
        electrode.thickness = 2.0
    pair_2 = session.add_tdcslist(deepcopy(pair_1))
    pair_2.currents = [0.0, 0.0, 0.001, -0.001]
    run_simnibs(session)
    if not all(path.is_file() for path in expected):
        raise RuntimeError("SimNIBS did not produce both carrier-pair fields")
    return expected


def crop_tissues(mesh: mesh_io.Msh) -> mesh_io.Msh:
    tags = np.hstack((
        np.arange(ElementTags.TH_START, ElementTags.SALINE_START - 1),
        np.arange(ElementTags.TH_SURFACE_START, ElementTags.SALINE_TH_SURFACE_START - 1),
    ))
    return mesh.crop_mesh(tags=tags)


def field(mesh: mesh_io.Msh, name: str) -> np.ndarray:
    for item in mesh.elmdata:
        if item.field_name == name:
            return np.asarray(item.value)
    raise KeyError(name)


def extract_atlas_archive() -> None:
    if not ATLAS_ARCHIVE.is_file():
        return
    ATLAS_DIR.mkdir(parents=True, exist_ok=True)
    wanted = {ATLAS_VOLUME_NAME, ATLAS_XML_NAME}
    with tarfile.open(ATLAS_ARCHIVE, "r:gz") as archive:
        members = {
            Path(member.name).name: member
            for member in archive.getmembers()
            if Path(member.name).name in wanted
        }
        missing = wanted - members.keys()
        if missing:
            raise RuntimeError(f"Harvard-Oxford archive lacks required files: {sorted(missing)}")
        for name, member in members.items():
            source = archive.extractfile(member)
            if source is None:
                raise RuntimeError(f"Cannot extract {name} from Harvard-Oxford archive")
            with source, (ATLAS_DIR / name).open("wb") as target:
                shutil.copyfileobj(source, target)


def locate_atlas(explicit: Path | None, explicit_xml: Path | None) -> tuple[Path | None, Path | None, str]:
    if not explicit and not explicit_xml and (not (ATLAS_DIR / ATLAS_VOLUME_NAME).is_file() or not (ATLAS_DIR / ATLAS_XML_NAME).is_file()):
        extract_atlas_archive()
    candidate_pairs = []
    if explicit:
        candidate_pairs.append((explicit, explicit_xml or explicit.parent / ATLAS_XML_NAME))
    candidate_pairs.extend([
        (
            Path.home() / "nilearn_data/fsl/data/atlases/HarvardOxford" / ATLAS_VOLUME_NAME,
            Path.home() / "nilearn_data/fsl/data/atlases/HarvardOxford" / ATLAS_XML_NAME,
        ),
        (ATLAS_DIR / ATLAS_VOLUME_NAME, ATLAS_DIR / ATLAS_XML_NAME),
        (ROOT / "data" / "atlases" / ATLAS_VOLUME_NAME, ROOT / "data" / "atlases" / ATLAS_XML_NAME),
    ])
    for volume, labels in candidate_pairs:
        if volume.is_file() and labels.is_file():
            return volume, labels, "Harvard-Oxford subcortical atlas, 25% max-probability"
    return None, None, "MNI-coordinate geometric hippocampal substitute"


def atlas_label_value(xml_path: Path, label_name: str) -> int:
    matches = []
    for label in ET.parse(xml_path).getroot().iter("label"):
        if (label.text or "").strip().casefold() == label_name.casefold():
            matches.append(int(label.attrib["index"]) + 1)
    if len(matches) != 1:
        raise RuntimeError(f"Expected one {label_name!r} label in {xml_path}, found {len(matches)}")
    return matches[0]


def atlas_roi(
    centers_gray: np.ndarray,
    atlas_path: Path | None,
    atlas_xml: Path | None,
) -> tuple[dict[str, np.ndarray], dict]:
    mni = np.asarray(transformations.subject2mni_coords(centers_gray, str(M2M)), dtype=np.float64)
    left = mni[:, 0] < 0
    right = mni[:, 0] > 0
    if atlas_path:
        if atlas_xml is None:
            raise RuntimeError("Atlas label XML is required with a Harvard-Oxford volume")
        image = nib.load(str(atlas_path))
        data = np.asarray(image.dataobj)
        inv = np.linalg.inv(image.affine)
        ijk = nib.affines.apply_affine(inv, mni)
        labels = map_coordinates(data, ijk.T, order=0, mode="constant", cval=0).astype(int)
        label_value = atlas_label_value(atlas_xml, "Left Hippocampus")
        right_label_value = atlas_label_value(atlas_xml, "Right Hippocampus")
        whole = labels == label_value
        right_hippocampus = labels == right_label_value
        source = {
            "method": "atlas",
            "atlas_label_name": "Left Hippocampus",
            "atlas_label_value": label_value,
            "off_target_atlas_label_name": "Right Hippocampus",
            "off_target_atlas_label_value": right_label_value,
            "atlas_label_rule": "XML index + 1",
        }
    else:
        # Explicit fallback: a curved ellipsoidal approximation in MNI space.
        p1 = np.array([-30.0, -32.0, -12.0])
        p2 = np.array([-22.0, -8.0, -20.0])
        segment = p2 - p1
        t = np.clip(((mni - p1) @ segment) / (segment @ segment), 0.0, 1.0)
        distance = np.linalg.norm(mni - (p1 + t[:, None] * segment), axis=1)
        whole = left & (distance <= 7.0)
        right_p1, right_p2 = p1 * np.array([-1.0, 1.0, 1.0]), p2 * np.array([-1.0, 1.0, 1.0])
        right_segment = right_p2 - right_p1
        right_t = np.clip(((mni - right_p1) @ right_segment) / (right_segment @ right_segment), 0.0, 1.0)
        right_distance = np.linalg.norm(mni - (right_p1 + right_t[:, None] * right_segment), axis=1)
        right_hippocampus = right & (right_distance <= 7.0)
        source = {"method": "MNI capsule substitute", "radius_mm": 7.0}
    source["coordinate_transform"] = {
        "tool": "simnibs.utils.transformations.subject2mni_coords",
        "direction": "subject2mni",
        "transformation_type": "nonl",
        "warp_field": "m2m_ernie/toMNI/Conform2MNI_nonl.nii.gz",
        "atlas_sampling": "nearest-neighbor labels at transformed gray-matter tetrahedron centers",
        "atlas_to_subject_resampling": False,
    }
    if whole.sum() < 20:
        raise RuntimeError("Left hippocampal ROI contains too few gray-matter elements")
    if right_hippocampus.sum() < 20:
        raise RuntimeError("Right hippocampal ROI contains too few gray-matter elements")
    y = mni[:, 1]
    rois = {
        "hippocampus": whole,
        "right_hippocampus": right_hippocampus,
        # Half-millimeter edges reproduce the paper's contiguous integer MNI-Y slices
        # when assigning continuous tetrahedron centers.
        "hippocampus_anterior": whole & (y >= -18.5) & (y < -3.5),
        "hippocampus_middle": whole & (y >= -29.5) & (y < -18.5),
        "hippocampus_posterior": whole & (y >= -40.5) & (y < -29.5),
    }
    source["reported_mni_y_slices_mm"] = {"anterior": [-18, -4], "middle": [-29, -19], "posterior": [-40, -30]}
    source["continuous_assignment_edges_mm"] = {"anterior": [-18.5, -3.5], "middle": [-29.5, -18.5], "posterior": [-40.5, -29.5]}
    return rois, {"source": source, "mni_coordinates_mm": mni}


def dti_principal_axis(centers: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    image = nib.load(str(M2M / "DTI_coregT1_tensor.nii.gz"))
    affine = np.asarray(image.affine, dtype=np.float64)
    ijk = nib.affines.apply_affine(np.linalg.inv(affine), centers)
    samples = np.empty((len(centers), 6), dtype=np.float32)
    for i in range(6):
        samples[:, i] = map_coordinates(
            np.asarray(image.dataobj[..., i], dtype=np.float32),
            ijk.T,
            order=1,
            mode="constant",
            cval=0.0,
            prefilter=True,
        )
    tensors = np.empty((len(samples), 3, 3), dtype=np.float32)
    tensors[:, 0, 0], tensors[:, 0, 1], tensors[:, 0, 2] = samples[:, 0], samples[:, 1], samples[:, 2]
    tensors[:, 1, 0], tensors[:, 1, 1], tensors[:, 1, 2] = samples[:, 1], samples[:, 3], samples[:, 4]
    tensors[:, 2, 0], tensors[:, 2, 1], tensors[:, 2, 2] = samples[:, 2], samples[:, 4], samples[:, 5]
    # Match SimNIBS cond_utils.py: rotate tensor values from image coordinates
    # into mesh/world coordinates before extracting the principal eigenvector.
    matrix = affine[:3, :3]
    matrix = matrix / np.linalg.norm(matrix, axis=0)[:, None]
    reflection = np.eye(3)
    if np.linalg.det(matrix) > 0:
        reflection[0, 0] = -1.0
    matrix = matrix @ reflection
    tensors = np.einsum("ij,njk,lk->nil", matrix, tensors, matrix)
    eigenvalues, vectors = np.linalg.eigh(tensors)
    valid = (
        np.isfinite(eigenvalues).all(axis=1)
        & (eigenvalues[:, -1] > 1e-12)
        & (eigenvalues[:, 0] >= -1e-8)
    )
    directions = vectors[:, :, -1].astype(np.float32)
    directions[~valid] = np.nan
    return directions, valid


def cortical_controls(centers_gray: np.ndarray) -> tuple[dict[str, np.ndarray], dict]:
    csv_path = M2M / "eeg_positions" / "EEG10-10_UI_Jurak_2007.csv"
    coordinates = {}
    with csv_path.open(encoding="utf-8") as stream:
        for row in csv.reader(stream):
            if len(row) >= 5:
                coordinates[row[4]] = np.array(row[1:4], dtype=float)
    tree = cKDTree(centers_gray)
    rois = {}
    metadata = {"definition": "10 mm Euclidean spheres centered on the nearest gray-matter element", "radius_mm": 10.0, "regions": {}}
    for name, position in (("cortex_anterior", coordinates["FT7"]), ("cortex_posterior", coordinates["TP7"])):
        nearest = centers_gray[tree.query(position)[1]]
        rois[name] = np.linalg.norm(centers_gray - nearest, axis=1) <= 10.0
        metadata["regions"][name] = {"anchor": "FT7" if name.endswith("anterior") else "TP7", "center_subject_mm": nearest.tolist()}
    midpoint = (coordinates["FT7"] + coordinates["TP7"]) / 2
    nearest = centers_gray[tree.query(midpoint)[1]]
    rois["cortex_middle"] = np.linalg.norm(centers_gray - nearest, axis=1) <= 10.0
    metadata["regions"]["cortex_middle"] = {"anchor": "FT7-TP7 scalp-coordinate midpoint", "center_subject_mm": nearest.tolist()}
    metadata["anatomical_atlas_regions"] = False
    return rois, metadata


def cap_coordinates(labels: list[str]) -> dict[str, np.ndarray]:
    csv_path = M2M / "eeg_positions" / "EEG10-10_UI_Jurak_2007.csv"
    coordinates = {}
    with csv_path.open(encoding="utf-8") as stream:
        for row in csv.reader(stream):
            if len(row) >= 5 and row[4] in labels:
                coordinates[row[4]] = np.asarray(row[1:4], dtype=np.float64)
    missing = sorted(set(labels) - coordinates.keys())
    if missing:
        raise RuntimeError(f"Missing electrode coordinates: {missing}")
    return coordinates


def export_gray_surface(
    mesh: mesh_io.Msh,
    fields: dict[str, np.ndarray],
    path: Path,
) -> None:
    surface = mesh.crop_mesh(tags=[ElementTags.GM_TH_SURFACE])
    if surface.elm.nr == 0:
        raise RuntimeError("Gray-matter surface is missing from the FEM mesh")
    gray_tetrahedra = mesh.elm.elm_number[
        (np.asarray(mesh.elm.elm_type) == 4)
        & (np.asarray(mesh.elm.tag1) == int(ElementTags.GM))
    ]
    arrays = {
        "coordinates_subject_mm": np.asarray(surface.nodes.node_coord, dtype=np.float32),
        "triangles_zero_based": np.asarray(surface.elm.node_number_list[:, :3], dtype=np.int32) - 1,
    }
    for name, values in fields.items():
        source = mesh_io.ElementData(values, name=name, mesh=mesh)
        arrays[name] = np.asarray(
            source.interpolate_to_surface(
                surface,
                out_fill="nearest",
                th_indices=gray_tetrahedra,
            ).value,
            dtype=np.float32,
        )
    np.savez_compressed(path, **arrays)


def solver_log_qc(fem_dir: Path) -> dict:
    logs = sorted(fem_dir.glob("simnibs_simulation_*.log"))
    if not logs:
        raise RuntimeError("SimNIBS solver log is missing")
    text = logs[-1].read_text(encoding="utf-8", errors="replace")
    errors = [float(value) for value in re.findall(r"Estimated current calibration error:\s*([0-9.]+)%", text)]
    if not errors or "SimNIBS finished running simulations" not in text:
        raise RuntimeError("SimNIBS solver log lacks completion or current-calibration evidence")
    return {
        "log": str(logs[-1]),
        "solver_completed": True,
        "basis_solve_current_calibration_error_pct": errors,
        "maximum_basis_solve_current_calibration_error_pct": max(errors),
        "acceptance_threshold": None,
        "note": "Values are SimNIBS estimates for internal channel-reference basis solves, not a measured device-current error.",
    }


def main() -> None:
    args = parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    paths = build_fem(out, args.reuse_fem)
    meshes = [crop_tissues(mesh_io.read_msh(str(path))) for path in paths]
    reference = meshes[0]
    mesh_checks = (
        np.allclose(reference.nodes.node_coord, meshes[1].nodes.node_coord),
        np.array_equal(reference.elm.node_number_list, meshes[1].elm.node_number_list),
        np.array_equal(reference.elm.elm_type, meshes[1].elm.elm_type),
        np.array_equal(reference.elm.tag1, meshes[1].elm.tag1),
    )
    if not all(mesh_checks):
        raise RuntimeError("Carrier-pair meshes are not element-aligned")
    e1 = field(meshes[0], "E").astype(np.float64)
    e2 = field(meshes[1], "E").astype(np.float64)
    centers = np.asarray(reference.elements_baricenters().value, dtype=np.float64)
    volumes = np.asarray(reference.elements_volumes_and_areas().value, dtype=np.float64)
    tetra = np.asarray(reference.elm.elm_type) == 4
    gray = tetra & (np.asarray(reference.elm.tag1) == int(ElementTags.GM))
    gray_element_indices = np.flatnonzero(gray)
    centers_gray = centers[gray]
    volumes_gray = volumes[gray]
    atlas_path, atlas_xml, atlas_description = locate_atlas(args.atlas, args.atlas_xml)
    if atlas_path is None and not args.allow_geometric_roi:
        raise RuntimeError(
            "Harvard-Oxford atlas and label XML are required for the final reproduction; "
            "use --allow-geometric-roi only for an explicitly labeled development run"
        )
    roi_masks, roi_meta = atlas_roi(centers_gray, atlas_path, atlas_xml)
    cortical_masks, cortical_meta = cortical_controls(centers_gray)
    roi_masks.update(cortical_masks)
    roi_masks["off_target_gray_matter"] = ~roi_masks["hippocampus"]
    roi_masks["whole_gray_matter"] = np.ones(gray_element_indices.size, dtype=bool)
    segment_names = ["hippocampus_anterior", "hippocampus_middle", "hippocampus_posterior"]
    segment_count = sum(roi_masks[name].astype(np.uint8) for name in segment_names)
    hippocampus = roi_masks["hippocampus"]
    roi_meta["segment_coverage"] = {
        "hippocampus_volume_mm3": float(volumes_gray[hippocampus].sum()),
        "assigned_to_three_segments_volume_mm3": float(volumes_gray[hippocampus & (segment_count == 1)].sum()),
        "outside_reported_segment_range_volume_mm3": float(volumes_gray[hippocampus & (segment_count == 0)].sum()),
        "overlap_volume_mm3": float(volumes_gray[hippocampus & (segment_count > 1)].sum()),
        "assigned_fraction": float(volumes_gray[hippocampus & (segment_count == 1)].sum() / volumes_gray[hippocampus].sum()),
    }
    roi_meta["cortical_control_regions"] = cortical_meta
    mni_coordinates_gray = roi_meta["mni_coordinates_mm"]
    direction_gray, dti_valid_gray = dti_principal_axis(centers_gray)
    direction_norm = np.linalg.norm(direction_gray[dti_valid_gray], axis=1)
    if not np.allclose(direction_norm, 1.0, atol=1e-5):
        raise RuntimeError("Finite DTI principal directions are not unit vectors")

    conditions = {}
    arrays = {}
    numerical_qc = {}
    solver_qc = solver_log_qc(out / "raw" / "fem")
    for condition, currents in PAPER["conditions"].items():
        f1 = e1 * (currents["pair_1_peak_a"] / 0.001)
        f2 = e2 * (currents["pair_2_peak_a"] / 0.001)
        abs_1 = np.linalg.norm(f1, axis=1)
        abs_2 = np.linalg.norm(f2, axis=1)
        carrier_sum = abs_1 + abs_2
        ti_directional_gray = np.full(gray_element_indices.size, np.nan, dtype=np.float64)
        ti_directional_gray[dti_valid_gray] = TI_utils.get_dirTI(
            f1[gray][dti_valid_gray],
            f2[gray][dti_valid_gray],
            direction_gray[dti_valid_gray],
        )
        ti_max = TI_utils.get_maxTI(f1, f2)
        reference_directional = recompute_directional_ti(
            f1[gray][dti_valid_gray],
            f2[gray][dti_valid_gray],
            direction_gray[dti_valid_gray],
        )
        reference_timax = recompute_timax(f1[gray], f2[gray])
        directional_error = float(np.max(np.abs(reference_directional - ti_directional_gray[dti_valid_gray])))
        timax_error = float(np.nanmax(np.abs(reference_timax - ti_max[gray])))
        numerical_qc[condition] = {
            "directional_ti_max_abs_error_v_per_m": directional_error,
            "timax_max_abs_error_v_per_m": timax_error,
            "acceptance_tolerance_v_per_m": 1e-12,
            "passed": bool(directional_error <= 1e-12 and timax_error <= 1e-12),
        }
        if not numerical_qc[condition]["passed"]:
            raise RuntimeError(f"Independent TI formula check failed for {condition}: {numerical_qc[condition]}")
        arrays[condition] = {
            "E1_gray": f1[gray].astype(np.float32), "E2_gray": f2[gray].astype(np.float32),
            "E1_magnitude_gray": abs_1[gray].astype(np.float32),
            "E2_magnitude_gray": abs_2[gray].astype(np.float32),
            "carrier_sum_magnitude_gray": carrier_sum[gray].astype(np.float32),
            "TI_directional_gray": ti_directional_gray.astype(np.float32),
            "TImax_gray": ti_max[gray].astype(np.float32),
        }
        metrics = {
            roi: {
                "TI_directional": summarize(ti_directional_gray, volumes_gray, mask),
                "TImax": summarize(ti_max[gray], volumes_gray, mask),
                "carrier_sum_magnitude": summarize(carrier_sum[gray], volumes_gray, mask),
            }
            for roi, mask in roi_masks.items() if mask.sum()
        }
        target_directional = metrics["hippocampus"]["TI_directional"]
        off_directional = metrics["off_target_gray_matter"]["TI_directional"]
        segment_medians = np.asarray([
            metrics[name]["TI_directional"]["median_v_per_m"]
            for name in segment_names
        ])
        conditions[condition] = {
            "currents": currents,
            "metrics": metrics,
            "target_to_offtarget": {
                key: target_directional[f"{key}_v_per_m"] / off_directional[f"{key}_v_per_m"]
                for key in ("mean", "median", "p95")
            },
            "relative_hippocampal_segment_exposure": {
                name: float(value / segment_medians.sum())
                for name, value in zip(segment_names, segment_medians)
            },
            "focality": focality_summary(
                ti_directional_gray,
                volumes_gray,
                roi_masks["hippocampus"],
                mni_coordinates_gray,
            ),
        }

    raw = out / "raw"
    tables = out / "tables"
    nifti_dir = raw / "nifti"
    raw.mkdir(exist_ok=True)
    tables.mkdir(exist_ok=True)
    nifti_dir.mkdir(exist_ok=True)
    roi_meta.pop("mni_coordinates_mm")
    with h5py.File(raw / "violante2023_reproduction_fields.h5", "w") as h5:
        h5.attrs["analysis_domain"] = "SimNIBS gray-matter tetrahedra only"
        h5.attrs["coordinate_space_subject"] = "SimNIBS subject conform space, mm"
        h5.attrs["coordinate_space_mni"] = "MNI space, mm"
        h5.attrs["electric_field_unit"] = "V/m"
        h5.create_dataset("mesh/gray_element_indices_zero_based", data=gray_element_indices, compression="gzip")
        h5.create_dataset("mesh/element_centers_subject_mm", data=centers_gray, compression="gzip")
        h5.create_dataset("mesh/element_centers_mni_mm", data=mni_coordinates_gray, compression="gzip")
        h5.create_dataset("mesh/element_volumes_mm3", data=volumes_gray, compression="gzip")
        h5.create_dataset("mesh/principal_dti_direction_world", data=direction_gray.astype(np.float32), compression="gzip")
        h5.create_dataset("mesh/dti_direction_valid", data=dti_valid_gray.astype(np.uint8), compression="gzip")
        for name, mask in roi_masks.items(): h5.create_dataset(f"masks/{name}", data=mask.astype(np.uint8), compression="gzip")
        for condition, fields in arrays.items():
            for name, values in fields.items(): h5.create_dataset(f"conditions/{condition}/{name}", data=values, compression="gzip")
    rows = []
    for condition, payload in conditions.items():
        for roi, metrics in payload["metrics"].items():
            for field_name, values in metrics.items():
                rows.append({"condition": condition, "roi": roi, "field": field_name, **values})
    with (tables / "roi_metrics.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    with (tables / "electrode_montage.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        coordinates = cap_coordinates([config["position"] for config in MONTAGE.values()])
        writer = csv.DictWriter(
            stream,
            fieldnames=["electrode", "position", "pair", "polarity", "x_subject_mm", "y_subject_mm", "z_subject_mm"],
        )
        writer.writeheader()
        for name, config in MONTAGE.items():
            xyz = coordinates[config["position"]]
            writer.writerow({
                "electrode": name,
                **config,
                "x_subject_mm": xyz[0],
                "y_subject_mm": xyz[1],
                "z_subject_mm": xyz[2],
            })

    result = {
        "schema": "qlanalyser.simnibs.violante2023-reproduction.v1",
        "software": {"name": "SimNIBS", "version": simnibs.__version__},
        "paper": PAPER,
        "implementation": {
            "head_model": "SimNIBS example subject ernie",
            "solver": "SimNIBS FEM, quasistatic linear superposition",
            "montage": MONTAGE,
            "electrode_coordinates_subject_mm": {
                name: coordinates[config["position"]].tolist()
                for name, config in MONTAGE.items()
            },
            "atlas": atlas_description,
            "roi": roi_meta,
            "field_metrics": {
                "TI_directional": "SimNIBS get_dirTI projected along local DTI principal axis; matches the paper's reported metric",
                "TImax": "direction-independent maximum modulation envelope; added for SimNIBS interoperability",
                "carrier_sum_magnitude": "sum of E1 and E2 vector magnitudes; descriptive carrier-exposure measure, not the paper's directional TI metric",
            },
        },
        "conditions": conditions,
        "quality": {
            "configured_current_balance_a": {
                "carrier_pair_1": 0.0,
                "carrier_pair_2": 0.0,
            },
            "carrier_mesh_alignment": True,
            "gray_tetrahedra": int(gray.sum()),
            "gray_volume_mm3": float(volumes_gray.sum()),
            "dti_valid_gray_tetrahedra": int(dti_valid_gray.sum()),
            "dti_valid_gray_fraction": float(dti_valid_gray.mean()),
            "dti_direction_norm_atol": 1e-5,
            "finite_E1": bool(np.isfinite(e1).all()),
            "finite_E2": bool(np.isfinite(e2).all()),
            "independent_formula_checks": numerical_qc,
            "solver_log": solver_qc,
        },
        "claim_boundary": "Method and structure reproduction on ernie; not a numerical replication of the MIDA model, cadaver measurements, original participants, fMRI, behavior, safety, or efficacy.",
    }
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result_mesh = deepcopy(reference)
    result_mesh.elmdata = []
    result_mesh.add_element_field(e1.astype(np.float32), "E1_unit_1mA")
    result_mesh.add_element_field(e2.astype(np.float32), "E2_unit_1mA")
    surface_fields = {}
    for condition, fields in arrays.items():
        directional_full = np.full(reference.elm.nr, np.nan, dtype=np.float32)
        directional_full[gray] = fields["TI_directional_gray"]
        timax_full = TI_utils.get_maxTI(
            e1 * (PAPER["conditions"][condition]["pair_1_peak_a"] / 0.001),
            e2 * (PAPER["conditions"][condition]["pair_2_peak_a"] / 0.001),
        ).astype(np.float32)
        result_mesh.add_element_field(directional_full, f"{condition}_TI_directional_GM_only")
        result_mesh.add_element_field(timax_full, f"{condition}_TImax")
        surface_fields[f"{condition}_TI_directional"] = directional_full
        surface_fields[f"{condition}_TImax"] = timax_full
    mesh_io.write_msh(result_mesh, str(raw / "violante2023_reproduction_fields.msh"))

    roi_mesh = deepcopy(reference)
    roi_mesh.elmdata = []
    for name, mask_gray in roi_masks.items():
        mask_full = np.zeros(reference.elm.nr, dtype=np.uint8)
        mask_full[gray] = mask_gray.astype(np.uint8)
        roi_mesh.add_element_field(mask_full, name)
    mesh_io.write_msh(roi_mesh, str(raw / "violante2023_reproduction_rois.msh"))

    export_gray_surface(
        reference,
        surface_fields,
        raw / "gray_surface_fields.npz",
    )

    transformations.interpolate_to_volume(
        result_mesh,
        str(M2M),
        str(nifti_dir / "ernie_violante2023"),
        method="linear",
        continuous=False,
        keep_tissues=[ElementTags.WM, ElementTags.GM],
    )
    transformations.interpolate_to_volume(
        roi_mesh,
        str(M2M),
        str(nifti_dir / "ernie_violante2023_roi"),
        method="linear",
        continuous=False,
        keep_tissues=[ElementTags.GM],
    )
    manifest = []
    for path in sorted(p for p in out.rglob("*") if p.is_file() and p.name != "manifest.json"):
        manifest.append({"path": path.relative_to(out).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    (out / "manifest.json").write_text(json.dumps({"files": manifest}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
