"""Export the four-active-electrode TImax result to the ernie T1 grid."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import nibabel as nib
import numpy as np
from simnibs import mesh_io
from simnibs.mesh_tools import cython_msh


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "simnibs_inverse_ti_discrete_ernie_20260729"
M2M = ROOT / "data" / "simnibs_examples_v4_1" / "extracted" / "m2m_ernie"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


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


def invert_batched_3x3_without_lapack(matrices: np.ndarray) -> np.ndarray:
    values = np.asarray(matrices, dtype=float)
    if values.ndim != 3 or values.shape[1:] != (3, 3):
        raise ValueError(f"Expected an (N, 3, 3) array, got {values.shape}")
    a, b, c = values[:, 0, 0], values[:, 0, 1], values[:, 0, 2]
    d, e, f = values[:, 1, 0], values[:, 1, 1], values[:, 1, 2]
    g, h, i = values[:, 2, 0], values[:, 2, 1], values[:, 2, 2]
    determinant = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if np.any(np.abs(determinant) < 1e-18):
        raise ValueError("Degenerate tetrahedron encountered during grid interpolation")
    inverse = np.empty_like(values)
    inverse[:, 0, 0] = e * i - f * h
    inverse[:, 0, 1] = c * h - b * i
    inverse[:, 0, 2] = b * f - c * e
    inverse[:, 1, 0] = f * g - d * i
    inverse[:, 1, 1] = a * i - c * g
    inverse[:, 1, 2] = c * d - a * f
    inverse[:, 2, 0] = d * h - e * g
    inverse[:, 2, 1] = b * g - a * h
    inverse[:, 2, 2] = a * e - b * d
    inverse /= determinant[:, None, None]
    return inverse


def assign_elements_to_grid(field: mesh_io.ElementData, shape: tuple[int, int, int], affine: np.ndarray) -> np.ndarray:
    mesh = field.mesh
    tetrahedra = mesh.elm.get_tetrahedra()
    volume_mesh = mesh.crop_mesh(elm_type=4)
    inverse_affine = invert_affine_without_lapack(affine)
    coordinates = volume_mesh.nodes.node_coord
    voxel_nodes = np.empty_like(coordinates, dtype=float)
    for row in range(3):
        voxel_nodes[:, row] = inverse_affine[row, 3]
        for column in range(3):
            voxel_nodes[:, row] += coordinates[:, column] * inverse_affine[row, column]
    values = np.asarray(field.value)[tetrahedra].reshape(-1, 1).astype(float)
    original_inverse = np.linalg.inv
    np.linalg.inv = invert_batched_3x3_without_lapack
    try:
        image = cython_msh.interp_grid(
            np.asarray(shape, dtype=int),
            values,
            voxel_nodes.astype(float),
            (volume_mesh.elm.node_number_list - 1).astype(int),
        )
    finally:
        np.linalg.inv = original_inverse
    return np.squeeze(image, axis=3)


def main() -> None:
    source_mesh = OUT / "independent_fem" / "four_electrode_timax.msh"
    reference_path = M2M / "T1.nii.gz"
    output_path = OUT / "independent_fem" / "four_electrode_timax_T1grid.nii.gz"
    metadata_path = OUT / "independent_fem" / "four_electrode_timax_T1grid.json"

    mesh = mesh_io.read_msh(str(source_mesh))
    fields = [field for field in mesh.elmdata if field.field_name == "TImax_four_active_electrode"]
    if len(fields) != 1:
        raise ValueError(f"Expected one TImax_four_active_electrode field, found {len(fields)}")

    recompute = np.load(OUT / "independent_fem" / "independent_timax_recompute.npz")
    gray_matter_mask = np.asarray(recompute["whole_gray_matter_mask"], dtype=bool)
    if gray_matter_mask.shape != fields[0].value.shape:
        raise ValueError("Gray-matter mask and TImax element field are not aligned")
    fields[0].value = np.where(gray_matter_mask, fields[0].value, 0.0)

    reference = nib.load(str(reference_path))
    tissue_reference = nib.load(str(M2M / "final_tissues.nii.gz"))
    if tissue_reference.shape[:3] != reference.shape[:3] or not np.array_equal(tissue_reference.affine, reference.affine):
        raise ValueError("final_tissues and T1 are not on the same conform grid")
    reference_gray_matter_voxels = int(np.count_nonzero(np.asarray(tissue_reference.dataobj).squeeze() == 2))
    image = assign_elements_to_grid(fields[0], reference.shape[:3], reference.affine)
    image = np.asarray(image, dtype=np.float32)
    header = reference.header.copy()
    header.set_data_dtype(np.float32)
    header.set_xyzt_units("mm")
    header["descrip"] = b"SimNIBS four-active-electrode TImax; V/m; element assignment"
    nib.save(nib.Nifti1Image(image, reference.affine, header), str(output_path))

    exported = nib.load(str(output_path))
    if exported.shape != reference.shape[:3] or not np.array_equal(exported.affine, reference.affine):
        raise ValueError("Exported T1-grid NIfTI does not match the reference T1 grid")

    metadata = {
        "field": "TImax maximum envelope amplitude",
        "units": "V/m",
        "value_of_record": "four_active_electrode_fem_recomputation",
        "source_mesh": "independent_fem/four_electrode_timax.msh",
        "source_field": "TImax_four_active_electrode",
        "reference_image_source": "data/simnibs_examples_v4_1/extracted/m2m_ernie/T1.nii.gz",
        "reference_image_delivery_copy": "raw/anatomy/ernie_T1_conform.nii.gz",
        "reference_image_sha256": sha256(reference_path),
        "coordinate_space": "ernie individual conform space",
        "grid_identity": "The field NIfTI and delivered ernie T1 copy have identical shape, voxel size, and affine; no registration transform is required for direct overlay.",
        "affine_voxel_to_conform_mm": [[float(value) for value in row] for row in reference.affine],
        "analysis_domain": "gray-matter tetrahedra selected by whole_gray_matter_mask; all other mesh elements are zero",
        "interpolation": "SimNIBS cython_msh.interp_grid element assignment, equivalent to ElementData.interpolate_to_grid(method='assign'); each in-mesh voxel receives the value of its containing tetrahedron; no smoothing. A local 4x4 affine inverse avoids a Windows NumPy LAPACK crash.",
        "shape": [int(value) for value in image.shape],
        "voxel_size_mm": [float(value) for value in reference.header.get_zooms()[:3]],
        "nonzero_voxels": int(np.count_nonzero(image)),
        "reference_gray_matter_voxels": reference_gray_matter_voxels,
        "reference_gray_matter_coverage_pct": 100.0 * int(np.count_nonzero(image)) / reference_gray_matter_voxels,
        "minimum_v_per_m": float(image.min()),
        "maximum_v_per_m": float(image.max()),
        "quantitative_use_limitation": "Use tetrahedron-level NPZ/CSV/JSON for reported ROI statistics and volumes; voxel statistics from this NIfTI are interpolation-grid dependent. Non-gray-matter exposure is not represented.",
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"nifti": str(output_path), "metadata": str(metadata_path), **metadata}))


if __name__ == "__main__":
    main()
