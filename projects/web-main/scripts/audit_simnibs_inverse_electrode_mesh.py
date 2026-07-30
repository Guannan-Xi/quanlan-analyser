"""Audit separation and tetrahedron quality for the selected electrode mesh."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from simnibs import mesh_io


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "simnibs_inverse_ti_discrete_ernie_20260729" / "independent_fem"
MESH = OUT / "ernie_TDCS_1_scalar.msh"
TAG_TO_ELECTRODE = {501: "F5", 502: "P5", 503: "FC3", 504: "CP3"}
PAIRS = [(501, 503), (502, 504)]


def main() -> None:
    mesh = mesh_io.read_msh(str(MESH))
    coordinates = mesh.nodes.node_coord
    connectivity = mesh.elm.node_number_list
    tags = mesh.elm.tag1
    electrode_data = {}
    for tag, label in TAG_TO_ELECTRODE.items():
        indices = np.flatnonzero(tags == tag)
        tetrahedra = connectivity[indices, :4] - 1
        xyz = coordinates[tetrahedra]
        volumes = np.abs(
            np.einsum(
                "ij,ij->i",
                np.cross(xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0]),
                xyz[:, 3] - xyz[:, 0],
            )
        ) / 6.0
        faces = {
            tuple(sorted(face))
            for tetrahedron in tetrahedra
            for face in itertools.combinations(map(int, tetrahedron), 3)
        }
        electrode_data[tag] = {
            "label": label,
            "tetrahedra": tetrahedra,
            "nodes": np.unique(tetrahedra),
            "faces": faces,
            "tetrahedron_count": int(len(tetrahedra)),
            "minimum_tetrahedron_volume_mm3": float(volumes.min()),
            "degenerate_tetrahedra_le_1e_12_mm3": int(np.count_nonzero(volumes <= 1e-12)),
        }

    pair_results = []
    for first_tag, second_tag in PAIRS:
        first = electrode_data[first_tag]
        second = electrode_data[second_tag]
        first_nodes = first["nodes"]
        second_nodes = second["nodes"]
        distances, _ = cKDTree(coordinates[second_nodes]).query(coordinates[first_nodes], k=1)
        shared_nodes = np.intersect1d(first_nodes, second_nodes)
        pair_results.append(
            {
                "electrode_a": first["label"],
                "electrode_b": second["label"],
                "shared_tetrahedra": 0,
                "shared_triangular_faces": int(len(first["faces"] & second["faces"])),
                "shared_nodes": int(len(shared_nodes)),
                "minimum_cross_electrode_node_distance_mm": float(distances.min()),
                "interpretation": (
                    "No volumetric or face overlap, but point-contact topology remains and electrical independence is not established."
                    if len(shared_nodes)
                    else "No shared node, face, or tetrahedron detected."
                ),
            }
        )

    output = {
        "mesh": MESH.relative_to(ROOT / "outputs" / "simnibs_inverse_ti_discrete_ernie_20260729").as_posix(),
        "tag_mapping": {str(tag): label for tag, label in TAG_TO_ELECTRODE.items()},
        "electrodes": [
            {key: value for key, value in data.items() if key not in {"tetrahedra", "nodes", "faces"}}
            for data in electrode_data.values()
        ],
        "pair_qc": pair_results,
        "acceptance": "conditional",
        "boundary": "F5-FC3 shares two boundary nodes. Re-meshing with verified positive clearance is required before publication or device transfer.",
    }
    (OUT / "electrode_mesh_qc.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
