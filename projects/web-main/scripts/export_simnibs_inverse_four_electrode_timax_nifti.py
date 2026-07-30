"""Export the four-active-electrode TImax field to conform-space NIfTI."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import nibabel as nib


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs" / "simnibs_inverse_ti_discrete_ernie_20260729"
M2M = ROOT / "data" / "simnibs_examples_v4_1" / "extracted" / "m2m_ernie"
FEM = BASE / "independent_fem"


def main() -> None:
    print("loading archive", flush=True)
    archive = np.load(FEM / "independent_timax_recompute.npz")
    timax = np.asarray(archive["TImax_V_per_m"], dtype=np.float32)
    print("loaded TImax", flush=True)
    centers = np.asarray(archive["element_centers_mm"], dtype=np.float32)
    print("loaded centers", flush=True)
    gray_mask = archive["whole_gray_matter_mask"].astype(bool)
    print("loaded mask", flush=True)
    tissues_image = nib.load(str(M2M / "final_tissues.nii.gz"))
    tissues = np.squeeze(np.asarray(tissues_image.dataobj))
    print("loaded reference", flush=True)
    volume = np.zeros(tissues.shape, dtype=np.float32)
    print("allocated output", flush=True)
    expected_affine = np.array(
        [[0.0, 0.0, 1.0, -99.73745728], [-1.0, 0.0, 0.0, 154.1875], [0.0, 1.0, 0.0, -143.64227295], [0.0, 0.0, 0.0, 1.0]]
    )
    if not np.allclose(tissues_image.affine, expected_affine, atol=1e-5):
        raise RuntimeError("Unexpected conform affine; refusing to apply the frozen inverse mapping")
    gray_indices = np.flatnonzero(gray_mask)
    print(f"gray elements: {len(gray_indices)}", flush=True)
    shape = np.asarray(tissues.shape)
    for start in range(0, len(gray_indices), 100_000):
        element_indices = gray_indices[start : start + 100_000]
        world = centers[element_indices]
        voxel_indices = np.column_stack(
            (
                np.rint(154.1875 - world[:, 1]),
                np.rint(world[:, 2] + 143.64227295),
                np.rint(world[:, 0] + 99.73745728),
            )
        ).astype(np.int32)
        source_values = timax[element_indices]
        in_bounds = np.all((voxel_indices >= 0) & (voxel_indices < shape), axis=1)
        voxel_indices = voxel_indices[in_bounds]
        source_values = source_values[in_bounds]
        same_tissue = tissues[tuple(voxel_indices.T)] == 2
        voxel_indices = voxel_indices[same_tissue]
        source_values = source_values[same_tissue]
        np.maximum.at(volume, tuple(voxel_indices.T), source_values)
    sampled_voxels = int(np.count_nonzero(volume))
    gray_voxels = int(np.count_nonzero(tissues == 2))
    expected = FEM / "four_electrode_timax_conform_nearest_centroid.nii.gz"
    nib.save(nib.Nifti1Image(volume, tissues_image.affine, tissues_image.header), str(expected))
    metadata = {
        "file": expected.name,
        "reference": "m2m_ernie/final_tissues.nii.gz",
        "space": "ernie individual conform space",
        "units": "V/m",
        "sampling": "gray-matter tetrahedron centroids rounded to the nearest conform voxel; duplicate centroids use the maximum TImax; unsampled and non-GM voxels are zero",
        "sampled_gray_voxels": sampled_voxels,
        "reference_gray_voxels": gray_voxels,
        "sampled_gray_voxel_pct": 100.0 * sampled_voxels / gray_voxels,
        "quantitative_boundary": "Use Msh/NPZ for element-level statistics. This sparse centroid-rasterized NIfTI is for overlay/localization and is not a continuous interpolation or numerically identical to tetrahedron statistics.",
    }
    import json
    (FEM / "four_electrode_timax_conform_nearest_centroid.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
