"""Command-line entry point for the recovered 64-channel report workflow."""

from __future__ import annotations

import argparse

from .pipeline import run_recovered_full_report_pipeline


def main():
    parser = argparse.ArgumentParser(description="Run full-recording 64-channel QEEG analysis and report rendering.")
    parser.add_argument("input_bdf", help="Input BDF/EDF/FIF recording; read only.")
    parser.add_argument("output_dir", help="New or empty output directory.")
    parser.add_argument("--include-aperiodic", action="store_true", help="Run Specparam aperiodic spectrum parameterization.")
    args = parser.parse_args()
    result = run_recovered_full_report_pipeline(args.input_bdf, args.output_dir, include_aperiodic=args.include_aperiodic)
    print(result["report"]["report_path"])


if __name__ == "__main__":
    main()
