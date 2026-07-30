"""Run a reproducible SimNIBS 4.6 inverse TI optimization on the ernie model.

This is an evidence-generating demo, not a customer-specific prescription. It
optimizes continuous scalp positions and then maps them to the subject's
EEG10-10 net so the delivery report can distinguish theoretical and executable
solutions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import simnibs
from simnibs import opt_struct


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_M2M = ROOT / "data" / "simnibs_examples_v4_1" / "extracted" / "m2m_ernie"
DEFAULT_OUTPUT = ROOT / "outputs" / "simnibs_inverse_ti_demo_ernie_20260729" / "raw_optimization"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m2m", type=Path, default=DEFAULT_M2M)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--maxiter", type=int, default=5)
    parser.add_argument("--popsize", type=int, default=4)
    parser.add_argument("--cpus", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260729)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    m2m = args.m2m.resolve()
    output = args.output.resolve()
    cap = m2m / "eeg_positions" / "EEG10-10_UI_Jurak_2007.csv"
    required = (m2m / "ernie.msh", m2m / "T1.nii.gz", cap)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing required ernie assets: {missing}")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)

    opt = opt_struct.TesFlexOptimization()
    opt.subpath = str(m2m)
    opt.output_folder = str(output)
    opt.goal = "mean"
    opt.e_postproc = "max_TI"
    opt.seed = args.seed
    opt.optimizer = "differential_evolution"
    opt.optimizer_options = {
        "maxiter": args.maxiter,
        "popsize": args.popsize,
        "tol": 0.1,
        "disp": True,
    }
    opt.polish = False
    opt.detailed_results = True
    opt.open_in_gmsh = False
    opt.run_final_electrode_simulation = True
    opt.map_to_net_electrodes = True
    opt.net_electrode_file = str(cap)
    opt.run_mapped_electrodes_simulation = True

    for _ in range(2):
        layout = opt.add_electrode_layout("ElectrodeArrayPair")
        layout.radius = [10]
        layout.current = [0.002, -0.002]

    roi = opt.add_roi()
    roi.method = "surface"
    roi.surface_type = "central"
    roi.roi_sphere_center_space = "subject"
    roi.roi_sphere_center = [-41.0, -13.0, 66.0]
    roi.roi_sphere_radius = 20

    run_contract = {
        "software": {"name": "SimNIBS", "version": simnibs.__version__},
        "task": "inverse_ti_continuous_position_optimization_with_net_mapping",
        "head_model": str(m2m),
        "target": {
            "definition": "20 mm spherical ROI on subject central gray-matter surface",
            "center_subject_mm": [-41.0, -13.0, 66.0],
            "source": "SimNIBS 4.6.0 tes_flex_ti_intensity.py example",
        },
        "objective": "maximize mean max_TI envelope in ROI",
        "stimulation": {
            "carrier_pairs": 2,
            "electrode_radius_mm": 10,
            "pair_currents_A": [[0.002, -0.002], [0.002, -0.002]],
            "current_convention": "peak amplitude as supplied to SimNIBS",
        },
        "optimizer": {
            "name": "differential_evolution",
            "maxiter": args.maxiter,
            "popsize": args.popsize,
            "tol": 0.1,
            "polish": False,
            "seed": args.seed,
            "budget_boundary": "demonstration budget; convergence must be assessed from generated optimizer evidence",
        },
        "mapping": {
            "continuous_solution": True,
            "net_file": str(cap),
            "mapped_solution_resimulated": True,
            "boundary": "EEG10-10 demo net is not a verified customer 64-channel cap",
        },
    }
    (output / "run_contract.json").write_text(
        json.dumps(run_contract, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    opt.run(cpus=args.cpus)


if __name__ == "__main__":
    main()
