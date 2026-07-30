"""Cluster four-electrode off-target suprathreshold GM tetrahedra by shared faces."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from simnibs import ElementTags, mesh_io


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "simnibs_inverse_ti_discrete_ernie_20260729"
M2M = ROOT / "data" / "simnibs_examples_v4_1" / "extracted" / "m2m_ernie"
ARCHIVE = OUT / "independent_fem" / "independent_timax_recompute.npz"
MSH = OUT / "independent_fem" / "ernie_TDCS_1_scalar.msh"
ROI_CENTER = np.array([-41.0, -13.0, 66.0])


def crop_native_tissues(mesh):
    tags = np.hstack((
        np.arange(ElementTags.TH_START, ElementTags.SALINE_START - 1),
        np.arange(ElementTags.TH_SURFACE_START, ElementTags.SALINE_TH_SURFACE_START - 1),
    ))
    return mesh.crop_mesh(tags=tags)


def connected_components(tetra_nodes: np.ndarray) -> list[np.ndarray]:
    parent = np.arange(len(tetra_nodes), dtype=np.int64)

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = int(parent[index])
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    owners: dict[tuple[int, int, int], int] = {}
    for local_index, nodes in enumerate(tetra_nodes):
        a, b, c, d = (int(value) for value in nodes)
        for face in ((a, b, c), (a, b, d), (a, c, d), (b, c, d)):
            key = tuple(sorted(face))
            previous = owners.get(key)
            if previous is None:
                owners[key] = local_index
            else:
                union(local_index, previous)

    groups: dict[int, list[int]] = {}
    for index in range(len(tetra_nodes)):
        groups.setdefault(find(index), []).append(index)
    return [np.asarray(indices, dtype=np.int64) for indices in groups.values()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.32454395294189453)
    parser.add_argument("--suffix", default="", help="Filename suffix, including a leading underscore when desired")
    args = parser.parse_args()
    threshold = args.threshold
    suffix = args.suffix
    if suffix and any(character not in "_-.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for character in suffix):
        raise ValueError("suffix contains unsupported characters")
    archive = np.load(ARCHIVE)
    field = archive["TImax_V_per_m"]
    centers = archive["element_centers_mm"]
    volumes = archive["element_volumes_mm3"]
    target = archive["target_mask"].astype(bool)
    off_target = archive["off_target_mask"].astype(bool)
    active = off_target & (field >= threshold)
    target_active = target & (field >= threshold)
    active_centers_path = OUT / "independent_fem" / f"four_electrode_offtarget_suprathreshold_centers_mm{suffix}.npy"
    np.save(active_centers_path, centers[active])

    mesh = crop_native_tissues(mesh_io.read_msh(str(MSH)))
    if len(mesh.elm.elm_type) != len(field):
        raise RuntimeError(f"Mesh/field length mismatch: {len(mesh.elm.elm_type)} != {len(field)}")
    active_indices = np.flatnonzero(active)
    tetra_nodes = np.asarray(mesh.elm.node_number_list[active_indices, :4], dtype=np.int64)
    components = connected_components(tetra_nodes)
    target_faces = set()
    for nodes in np.asarray(mesh.elm.node_number_list[np.flatnonzero(target_active), :4], dtype=np.int64):
        a, b, c, d = (int(value) for value in nodes)
        target_faces.update(tuple(sorted(face)) for face in ((a, b, c), (a, b, d), (a, c, d), (b, c, d)))

    records = []
    cluster_labels = np.zeros(len(field), dtype=np.int32)
    for component in components:
        global_indices = active_indices[component]
        component_volumes = volumes[global_indices]
        total_volume = float(component_volumes.sum())
        centroid = np.average(centers[global_indices], axis=0, weights=component_volumes)
        peak_index = int(global_indices[np.argmax(field[global_indices])])
        peak = centers[peak_index]
        center_distances = np.sqrt(np.sum((centers[global_indices] - ROI_CENTER) ** 2, axis=1))
        component_nodes = np.asarray(mesh.elm.node_number_list[global_indices, :4], dtype=np.int64)
        touches_target_suprathreshold = False
        for nodes in component_nodes:
            a, b, c, d = (int(value) for value in nodes)
            if any(tuple(sorted(face)) in target_faces for face in ((a, b, c), (a, b, d), (a, c, d), (b, c, d))):
                touches_target_suprathreshold = True
                break
        records.append({
            "n_tetrahedra": int(len(global_indices)),
            "volume_mm3": total_volume,
            "centroid_conform_mm": [float(value) for value in centroid],
            "centroid_distance_from_roi_center_mm": float(np.linalg.norm(centroid - ROI_CENTER)),
            "min_tetrahedron_center_distance_from_roi_center_mm": float(center_distances.min()),
            "max_tetrahedron_center_distance_from_roi_center_mm": float(center_distances.max()),
            "bounding_box_min_conform_mm": [float(value) for value in centers[global_indices].min(axis=0)],
            "bounding_box_max_conform_mm": [float(value) for value in centers[global_indices].max(axis=0)],
            "shares_face_with_target_suprathreshold": touches_target_suprathreshold,
            "max_v_per_m": float(field[peak_index]),
            "peak_conform_mm": [float(value) for value in peak],
            "peak_distance_from_roi_center_mm": float(np.linalg.norm(peak - ROI_CENTER)),
            "element_indices_zero_based": [int(value) for value in global_indices],
        })

    records.sort(key=lambda record: record["volume_mm3"], reverse=True)
    for cluster_id, record in enumerate(records, start=1):
        record["cluster_id"] = cluster_id
        cluster_labels[np.asarray(record.pop("element_indices_zero_based"), dtype=np.int64)] = cluster_id

    output_json = OUT / "tables" / f"four_electrode_offtarget_suprathreshold_clusters{suffix}.json"
    output_csv = OUT / "tables" / f"four_electrode_offtarget_suprathreshold_clusters{suffix}.csv"
    output_json.write_text(json.dumps({
        "coordinate_space": "ernie individual conform space",
        "connectivity": "tetrahedra sharing one complete triangular face",
        "threshold_v_per_m": threshold,
        "threshold_origin": (
            "fixed post-hoc search-field whole-GM single-tetrahedron maximum times 0.5"
            if not suffix
            else "post-hoc four-active-electrode whole-GM single-tetrahedron maximum times 0.5 sensitivity threshold"
        ),
        "roi_center_conform_mm": ROI_CENTER.tolist(),
        "cluster_count": len(records),
        "total_off_target_suprathreshold_volume_mm3": float(volumes[active].sum()),
        "clusters": records,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    with output_csv.open("w", newline="", encoding="utf-8-sig") as stream:
        columns = [
            "cluster_id", "n_tetrahedra", "volume_mm3", "centroid_x_mm", "centroid_y_mm", "centroid_z_mm",
            "centroid_distance_from_roi_center_mm", "max_v_per_m", "peak_x_mm", "peak_y_mm", "peak_z_mm",
            "peak_distance_from_roi_center_mm",
            "min_tetrahedron_center_distance_from_roi_center_mm", "max_tetrahedron_center_distance_from_roi_center_mm",
            "bbox_min_x_mm", "bbox_min_y_mm", "bbox_min_z_mm", "bbox_max_x_mm", "bbox_max_y_mm", "bbox_max_z_mm",
            "shares_face_with_target_suprathreshold",
        ]
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for record in records:
            writer.writerow({
                "cluster_id": record["cluster_id"],
                "n_tetrahedra": record["n_tetrahedra"],
                "volume_mm3": record["volume_mm3"],
                "centroid_x_mm": record["centroid_conform_mm"][0],
                "centroid_y_mm": record["centroid_conform_mm"][1],
                "centroid_z_mm": record["centroid_conform_mm"][2],
                "centroid_distance_from_roi_center_mm": record["centroid_distance_from_roi_center_mm"],
                "max_v_per_m": record["max_v_per_m"],
                "peak_x_mm": record["peak_conform_mm"][0],
                "peak_y_mm": record["peak_conform_mm"][1],
                "peak_z_mm": record["peak_conform_mm"][2],
                "peak_distance_from_roi_center_mm": record["peak_distance_from_roi_center_mm"],
                "min_tetrahedron_center_distance_from_roi_center_mm": record["min_tetrahedron_center_distance_from_roi_center_mm"],
                "max_tetrahedron_center_distance_from_roi_center_mm": record["max_tetrahedron_center_distance_from_roi_center_mm"],
                "bbox_min_x_mm": record["bounding_box_min_conform_mm"][0],
                "bbox_min_y_mm": record["bounding_box_min_conform_mm"][1],
                "bbox_min_z_mm": record["bounding_box_min_conform_mm"][2],
                "bbox_max_x_mm": record["bounding_box_max_conform_mm"][0],
                "bbox_max_y_mm": record["bounding_box_max_conform_mm"][1],
                "bbox_max_z_mm": record["bounding_box_max_conform_mm"][2],
                "shares_face_with_target_suprathreshold": record["shares_face_with_target_suprathreshold"],
            })

    print(json.dumps({"cluster_count": len(records), "json": str(output_json), "active_centers": str(active_centers_path)}))


if __name__ == "__main__":
    main()
