"""Export a centroid-sampled NIfTI mask for four-electrode off-target exposure."""

from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "simnibs_inverse_ti_discrete_ernie_20260729"
M2M = ROOT / "data" / "simnibs_examples_v4_1" / "extracted" / "m2m_ernie"
THRESHOLD = 0.32454395294189453


def invert_affine_without_lapack(affine: np.ndarray) -> np.ndarray:
    augmented = [
        [float(affine[row, column]) for column in range(4)]
        + [1.0 if row == column else 0.0 for column in range(4)]
        for row in range(4)
    ]
    for pivot_column in range(4):
        pivot_row = max(range(pivot_column, 4), key=lambda row: abs(augmented[row][pivot_column]))
        if abs(augmented[pivot_row][pivot_column]) < 1e-15:
            raise ValueError("Reference affine is singular")
        augmented[pivot_column], augmented[pivot_row] = augmented[pivot_row], augmented[pivot_column]
        pivot = augmented[pivot_column][pivot_column]
        augmented[pivot_column] = [value / pivot for value in augmented[pivot_column]]
        for row in range(4):
            if row == pivot_column:
                continue
            factor = augmented[row][pivot_column]
            augmented[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row], augmented[pivot_column])
            ]
    return np.asarray([row[4:] for row in augmented], dtype=float)


def main() -> None:
    centers = np.load(OUT / "independent_fem" / "four_electrode_offtarget_suprathreshold_centers_mm.npy")
    reference = nib.load(str(M2M / "T1.nii.gz"))
    inverse_affine = invert_affine_without_lapack(reference.affine)
    voxel_coordinates = np.empty_like(centers, dtype=float)
    for row in range(3):
        voxel_coordinates[:, row] = inverse_affine[row, 3]
        for column in range(3):
            voxel_coordinates[:, row] += centers[:, column] * inverse_affine[row, column]
    voxel_indices = np.rint(voxel_coordinates).astype(int)
    valid = np.all((voxel_indices >= 0) & (voxel_indices < np.asarray(reference.shape[:3])), axis=1)
    mask_data = np.zeros(reference.shape[:3], dtype=np.uint8)
    valid_indices = voxel_indices[valid]
    mask_data[valid_indices[:, 0], valid_indices[:, 1], valid_indices[:, 2]] = 1
    mask_nifti = OUT / "independent_fem" / "four_electrode_offtarget_suprathreshold_centroid_mask.nii.gz"
    header = reference.header.copy()
    header.set_data_dtype(np.uint8)
    nib.save(nib.Nifti1Image(mask_data, reference.affine, header), str(mask_nifti))
    metadata = {
        "mask_semantics": "binary voxel mask of suprathreshold off-target GM tetrahedron centroids; not tetrahedron-volume rasterization",
        "coordinate_space": "ernie individual conform space on m2m_ernie/T1.nii.gz grid",
        "source_tetrahedra": int(len(centers)),
        "in_bounds_centroids": int(valid.sum()),
        "occupied_voxels": int(mask_data.sum()),
        "threshold_v_per_m": THRESHOLD,
    }
    metadata_path = OUT / "independent_fem" / "four_electrode_offtarget_suprathreshold_centroid_mask.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"mask_nifti": str(mask_nifti), "metadata": str(metadata_path), **metadata}))


if __name__ == "__main__":
    main()
