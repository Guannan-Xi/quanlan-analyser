"""Discrete inverse TI search using real SimNIBS FEM fields on ernie.

The search space is an explicitly declared montage library. Every basis field
is solved on one shared electrode mesh; all admissible carrier-pair
combinations are then exhaustively evaluated with SimNIBS ``get_maxTI``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from copy import deepcopy
from itertools import combinations
from pathlib import Path

import h5py
import numpy as np
import simnibs
from simnibs import ElementTags, mesh_io, run_simnibs, sim_struct
from simnibs.utils import TI_utils
from simnibs.utils import transformations

from run_simnibs_ti_customer_demo import describe, field


ROOT = Path(__file__).resolve().parents[1]
M2M = ROOT / "data" / "simnibs_examples_v4_1" / "extracted" / "m2m_ernie"
OUTPUT = ROOT / "outputs" / "simnibs_inverse_ti_discrete_ernie_20260729" / "raw"
TARGET_SUBJECT = np.array([-41.0, -13.0, 66.0])
ROI_RADIUS_MM = 20.0
PAIR_LIBRARY = [
    ("F5-P5", "F5", "P5"),
    ("F6-P6", "F6", "P6"),
    ("FC3-CP3", "FC3", "CP3"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--reuse-fem", action="store_true")
    return parser.parse_args()


def crop_native_tissues(mesh: mesh_io.Msh) -> mesh_io.Msh:
    tags = np.hstack((
        np.arange(ElementTags.TH_START, ElementTags.SALINE_START - 1),
        np.arange(ElementTags.TH_SURFACE_START, ElementTags.SALINE_TH_SURFACE_START - 1),
    ))
    return mesh.crop_mesh(tags=tags)


def build_fem(out: Path, reuse: bool) -> list[Path]:
    fem = out / "fem"
    expected = [fem / f"ernie_TDCS_{index}_scalar.msh" for index in range(1, len(PAIR_LIBRARY) + 1)]
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
    labels = list(dict.fromkeys(label for _, a, b in PAIR_LIBRARY for label in (a, b)))
    for pair_index, (_, anode, cathode) in enumerate(PAIR_LIBRARY):
        tdcs = session.add_tdcslist()
        tdcs.currents = [0.001, -0.001]
        for label in labels:
            electrode = tdcs.add_electrode()
            if label == anode:
                electrode.channelnr = 1
            elif label == cathode:
                electrode.channelnr = 2
            else:
                electrode.channelnr = 3
            electrode.centre = label
            electrode.shape = "ellipse"
            electrode.dimensions = [40, 40]
            electrode.thickness = 2
        # Inactive channels must appear in the current vector so every solve uses
        # the identical electrode geometry and element ordering.
        tdcs.currents = [0.001, -0.001, 0.0]
    run_simnibs(session)
    if not all(path.is_file() for path in expected):
        raise RuntimeError("SimNIBS did not produce the complete basis-field library")
    return expected


def main() -> None:
    args = parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not (M2M / "ernie.msh").is_file():
        raise FileNotFoundError(M2M / "ernie.msh")
    paths = build_fem(out, args.reuse_fem)
    meshes = [crop_native_tissues(mesh_io.read_msh(str(path))) for path in paths]
    reference = meshes[0]
    for mesh in meshes[1:]:
        if not (
            np.allclose(reference.nodes.node_coord, mesh.nodes.node_coord)
            and np.array_equal(reference.elm.node_number_list, mesh.elm.node_number_list)
            and np.array_equal(reference.elm.tag1, mesh.elm.tag1)
        ):
            raise RuntimeError("Basis fields are not aligned on the same FEM mesh")
    fields = [np.asarray(field(mesh, "E").value, dtype=np.float64) for mesh in meshes]
    centers = np.asarray(reference.elements_baricenters().value, dtype=np.float64)
    volumes = np.asarray(reference.elements_volumes_and_areas().value, dtype=np.float64)
    gray = (np.asarray(reference.elm.elm_type) == 4) & (np.asarray(reference.elm.tag1) == int(ElementTags.GM))
    roi = gray & (np.linalg.norm(centers - TARGET_SUBJECT, axis=1) <= ROI_RADIUS_MM)
    off = gray & ~roi
    if np.count_nonzero(roi) < 10:
        raise RuntimeError("Target ROI contains too few gray-matter tetrahedra")

    rows = []
    arrays = {}
    for first, second in combinations(range(len(PAIR_LIBRARY)), 2):
        labels = set(PAIR_LIBRARY[first][1:]) | set(PAIR_LIBRARY[second][1:])
        if len(labels) != 4:
            continue
        ti = np.asarray(TI_utils.get_maxTI(fields[first], fields[second]), dtype=np.float64)
        target_mean = float(np.average(ti[roi], weights=volumes[roi]))
        off_mean = float(np.average(ti[off], weights=volumes[off]))
        score = target_mean / off_mean if off_mean > 0 else float("nan")
        candidate_id = f"{PAIR_LIBRARY[first][0]}__{PAIR_LIBRARY[second][0]}"
        arrays[candidate_id] = ti.astype(np.float32)
        rows.append({
            "candidate_id": candidate_id,
            "carrier_1": PAIR_LIBRARY[first][0],
            "carrier_2": PAIR_LIBRARY[second][0],
            "target_mean_v_per_m": target_mean,
            "off_target_mean_v_per_m": off_mean,
            "target_to_off_target_mean_ratio": score,
            "objective_value_v_per_m": target_mean,
            "admissible": True,
            "current_balance_error_A": 0.0,
            "individual_current_limit_A": 0.001,
            "individual_current_limit_hit": True,
        })
    rows.sort(key=lambda row: row["objective_value_v_per_m"], reverse=True)
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    winner = rows[0]
    winner_ti = arrays[winner["candidate_id"]]
    threshold = 0.5 * float(np.max(winner_ti[gray]))
    metrics = {
        "target": describe(winner_ti, volumes, roi, threshold),
        "off_target": describe(winner_ti, volumes, off, threshold),
        "whole_gray_matter": describe(winner_ti, volumes, gray, threshold),
    }

    tables = out / "tables"
    fields_dir = out / "fields"
    tables.mkdir(exist_ok=True)
    fields_dir.mkdir(exist_ok=True)
    with (tables / "candidate_ranking.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    np.savez_compressed(fields_dir / "candidate_timax_fields.npz", **arrays)
    result_mesh = deepcopy(reference)
    result_mesh.elmdata = []
    result_mesh.add_element_field(winner_ti, "TImax_discrete_optimum")
    mesh_io.write_msh(result_mesh, str(fields_dir / "ernie_inverse_ti_optimum.msh"))
    nifti_path = fields_dir / "ernie_inverse_ti_TImax_discrete_optimum.nii.gz"
    if not nifti_path.is_file():
        transformations.interpolate_to_volume(
            result_mesh,
            str(M2M),
            str(fields_dir / "ernie_inverse_ti"),
            method="linear",
            continuous=False,
            keep_tissues=[ElementTags.WM, ElementTags.GM],
        )
    if not nifti_path.is_file():
        raise RuntimeError(f"Expected NIfTI export was not created: {nifti_path}")
    with h5py.File(fields_dir / "inverse_ti_results.h5", "w") as h5:
        h5.create_dataset("mesh/element_centers_mm", data=centers, compression="gzip")
        h5.create_dataset("mesh/element_volumes_mm3", data=volumes, compression="gzip")
        h5.create_dataset("masks/target", data=roi.astype(np.uint8), compression="gzip")
        h5.create_dataset("masks/off_target", data=off.astype(np.uint8), compression="gzip")
        for name, values in arrays.items():
            h5.create_dataset(f"candidates/{name}/TImax_V_per_m", data=values, compression="gzip")
    result = {
        "schema": "qlanalyser.simnibs.inverse-ti-discrete-demo.v1",
        "software": {"name": "SimNIBS", "version": simnibs.__version__},
        "data_source": "SimNIBS example dataset v4.1, subject ernie",
        "task": "exhaustive discrete inverse TI montage search",
        "objective": "maximize volume-weighted mean TImax in target ROI",
        "search_space": {"basis_pairs": [item[0] for item in PAIR_LIBRARY], "admissible_candidates": len(rows)},
        "constraints": {
            "two_disjoint_bipolar_carrier_pairs": True,
            "pair_current_peak_A": 0.001,
            "net_current_per_pair_A": 0.0,
            "electrode_shape": "40 mm x 40 mm ellipse, 2 mm thickness",
        },
        "target": {"space": "subject", "center_mm": TARGET_SUBJECT.tolist(), "radius_mm": ROI_RADIUS_MM, "tissue": "gray matter"},
        "winner": winner,
        "metrics": metrics,
        "all_candidates": rows,
        "convergence": {
            "type": "finite exhaustive enumeration",
            "all_admissible_candidates_evaluated": True,
            "iterative_convergence_curve_applicable": False,
        },
        "execution_boundary": "Best only among the three admissible dual-carrier candidates formed from the declared three basis pairs; not continuous global optimization and not customer 64-channel cap validation.",
        "clinical_boundary": "Electric-field modeling only; no inference of neural activation, safety, efficacy, or clinical outcome.",
        "native_tesflex_attempt": {
            "status": "failed_before_optimization",
            "stage": "head-model preparation",
            "windows_exception_code": "0xc06d007f",
            "interpretation": "No native TesFlex optimization result or convergence claim was produced.",
        },
    }
    (out / "inverse_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = []
    for path in sorted(p for p in out.rglob("*") if p.is_file() and p.name != "raw_manifest.json"):
        manifest.append({"path": path.relative_to(out).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    (out / "raw_manifest.json").write_text(json.dumps({"files": manifest}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
