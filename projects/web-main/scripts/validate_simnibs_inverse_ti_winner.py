"""Independent FEM rerun of the selected discrete inverse TI montage."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path

import numpy as np
import h5py
from simnibs import ElementTags, mesh_io, run_simnibs, sim_struct
from simnibs.utils import TI_utils

from run_simnibs_ti_customer_demo import describe, field


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs" / "simnibs_inverse_ti_discrete_ernie_20260729"
M2M = ROOT / "data" / "simnibs_examples_v4_1" / "extracted" / "m2m_ernie"
FEM = BASE / "independent_fem"
TARGET = np.array([-41.0, -13.0, 66.0])


def add_montage(session, currents):
    tdcs = session.add_tdcslist()
    tdcs.currents = currents
    for channel, label in ((1, "F5"), (2, "P5"), (3, "FC3"), (4, "CP3")):
        electrode = tdcs.add_electrode()
        electrode.channelnr = channel
        electrode.centre = label
        electrode.shape = "ellipse"
        electrode.dimensions = [40, 40]
        electrode.thickness = 2
    return tdcs


def crop(mesh):
    tags = np.hstack((np.arange(ElementTags.TH_START, ElementTags.SALINE_START - 1), np.arange(ElementTags.TH_SURFACE_START, ElementTags.SALINE_TH_SURFACE_START - 1)))
    return mesh.crop_mesh(tags=tags)


def main() -> None:
    expected = [FEM / "ernie_TDCS_1_scalar.msh", FEM / "ernie_TDCS_2_scalar.msh"]
    if not all(path.is_file() for path in expected):
        if FEM.exists(): shutil.rmtree(FEM)
        FEM.mkdir(parents=True)
        session = sim_struct.SESSION(); session.subpath = str(M2M); session.pathfem = str(FEM); session.open_in_gmsh = False; session.fields = "eE"
        first = add_montage(session, [0.001, -0.001, 0.0, 0.0])
        second = session.add_tdcslist(deepcopy(first)); second.currents = [0.0, 0.0, 0.001, -0.001]
        run_simnibs(session)
    raw_first, raw_second = (mesh_io.read_msh(str(path)) for path in expected)
    element_types = np.asarray(raw_first.elm.elm_type)
    mesh_counts = {
        "nodes": int(len(raw_first.nodes.node_coord)),
        "tetrahedra": int(np.sum(element_types == 4)),
        "triangles": int(np.sum(element_types == 2)),
    }
    first, second = crop(raw_first), crop(raw_second)
    if not (np.allclose(first.nodes.node_coord, second.nodes.node_coord) and np.array_equal(first.elm.node_number_list, second.elm.node_number_list)):
        raise RuntimeError("Independent carrier meshes are not aligned")
    e1 = np.asarray(field(first, "E").value, dtype=float)
    e2 = np.asarray(field(second, "E").value, dtype=float)
    ti = np.asarray(TI_utils.get_maxTI(e1, e2), dtype=float)
    centers = np.asarray(first.elements_baricenters().value); volumes = np.asarray(first.elements_volumes_and_areas().value)
    gray = (np.asarray(first.elm.elm_type) == 4) & (np.asarray(first.elm.tag1) == int(ElementTags.GM))
    roi = gray & (np.linalg.norm(centers - TARGET, axis=1) <= 20.0)
    off = gray & ~roi
    search = json.loads((BASE / "raw" / "inverse_results.json").read_text(encoding="utf-8"))
    comparison_threshold = float(search["metrics"]["target"]["threshold_v_per_m"])
    independent_metrics = {
        "target": describe(ti, volumes, roi, comparison_threshold),
        "off_target": describe(ti, volumes, off, comparison_threshold),
        "whole_gray_matter": describe(ti, volumes, gray, comparison_threshold),
    }
    with h5py.File(BASE / "raw" / "fields" / "inverse_ti_results.h5", "r") as search_h5:
        search_centers = search_h5["mesh/element_centers_mm"][:]
        search_volumes = search_h5["mesh/element_volumes_mm3"][:]
        search_target = search_h5["masks/target"][:].astype(bool)
        search_off = search_h5["masks/off_target"][:].astype(bool)
    gray_domain = roi | off
    gray_domain_alignment = {
        "gray_tetrahedra": int(np.sum(gray_domain)),
        "target_mask_equal": bool(np.array_equal(roi, search_target)),
        "off_target_mask_equal": bool(np.array_equal(off, search_off)),
        "gray_centers_max_abs_difference_mm": float(np.max(np.abs(centers[gray_domain] - search_centers[gray_domain]))),
        "gray_volumes_max_abs_difference_mm3": float(np.max(np.abs(volumes[gray_domain] - search_volumes[gray_domain]))),
        "interpretation": "Full electrode meshes differ, but the gray-matter tetrahedra used as target/off-target statistical domains are geometrically identical.",
    }
    np.savez_compressed(
        FEM / "independent_timax_recompute.npz",
        E1_V_per_m=e1,
        E2_V_per_m=e2,
        TImax_V_per_m=ti,
        element_centers_mm=centers,
        element_volumes_mm3=volumes,
        target_mask=roi,
        off_target_mask=off,
        whole_gray_matter_mask=gray,
    )
    rerun_mean = float(np.average(ti[roi], weights=volumes[roi]))
    search_mean = float(search["winner"]["target_mean_v_per_m"])
    delta_pct = 100.0 * (rerun_mean - search_mean) / search_mean
    result = {
        "run_id": "ernie-independent-fem-f5p5-fc3cp3-20260729",
        "status": "completed",
        "selected_montage": ["F5-P5", "FC3-CP3"],
        "search_stage_roi_mean_v_per_m": search_mean,
        "independent_rerun_roi_mean_v_per_m": rerun_mean,
        "independent_metrics": independent_metrics,
        "independent_target_to_off_target_mean_ratio": independent_metrics["target"]["mean"] / independent_metrics["off_target"]["mean"],
        "comparison_threshold_v_per_m": comparison_threshold,
        "comparison_threshold_note": "Uses the same post-hoc exploratory absolute threshold as the search-stage report; it is not recomputed from the independent mesh.",
        "relative_difference_pct": delta_pct,
        "comparison_difference_assessment": {
            "relative_difference_pct": delta_pct,
            "interpretation": "Descriptive comparison only; no prospective acceptance tolerance was registered for this demonstration.",
            "acceptance_threshold_applied": False,
        },
        "active_electrodes": ["F5", "P5", "FC3", "CP3"],
        "electrode_geometry": "40 mm x 40 mm ellipse, 2 mm thickness",
        "conductivity_model": "same isotropic tissue conductivities as the search-stage SimNIBS session",
        "mesh_counts": mesh_counts,
        "gray_statistical_domain_alignment": gray_domain_alignment,
        "source_msh_vector_field": "E",
        "recompute_archive": "independent_timax_recompute.npz",
        "recompute_formula": "simnibs.utils.TI_utils.get_maxTI(E1_V_per_m, E2_V_per_m)",
        "mesh_boundary": "Independent rerun uses only the four active electrodes; search basis mesh also contained inactive candidate-library electrodes.",
    }
    (FEM / "independent_validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__": main()
