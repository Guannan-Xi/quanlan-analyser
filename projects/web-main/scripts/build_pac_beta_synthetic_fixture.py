from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

try:
    import mne
except Exception:  # pragma: no cover
    mne = None


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "work" / "fixtures" / "pac_beta"
PHASE_BAND = [4.0, 8.0]
AMP_BAND = [70.0, 110.0]
CHANNELS = ["Cz", "Pz"]
FORBIDDEN_BOUNDARY = (
    "Single-record descriptive PAC beta output only; not for clinical diagnosis, "
    "treatment decisions, causality, statistical significance, group comparison, "
    "brain-region communication, or source localization."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_svg(path: Path, title: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="520" viewBox="0 0 900 520">
  <rect width="900" height="520" fill="#ffffff"/>
  <text x="40" y="48" font-family="Arial" font-size="24" fill="#1f2933">{title}</text>
  <text x="40" y="84" font-family="Arial" font-size="14" fill="#334155">{body}</text>
  <text x="40" y="492" font-family="Arial" font-size="12" fill="#475569">{FORBIDDEN_BOUNDARY}</text>
  <rect x="80" y="120" width="700" height="300" fill="#eef2ff" stroke="#64748b"/>
  <path d="M90 385 C 190 260, 260 360, 360 225 S 560 285, 680 170 S 760 240, 775 140" fill="none" stroke="#2563eb" stroke-width="5"/>
  <circle cx="680" cy="170" r="7" fill="#dc2626"/>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def build_raw(path: Path, seed: int, *, coupled: bool, duration: float, sfreq: float = 300.0) -> dict[str, Any]:
    if mne is None:
        raise RuntimeError("mne is required to build FIF PAC fixtures")
    rng = np.random.default_rng(seed)
    times = np.arange(int(sfreq * duration)) / sfreq
    theta = np.sin(2 * np.pi * 6.0 * times)
    gamma_carrier = np.sin(2 * np.pi * 90.0 * times)
    if coupled:
        envelope = 1.0 + 0.65 * (theta + 1.0) / 2.0
    else:
        envelope = 1.0 + 0.10 * rng.normal(size=times.shape)
    signal = 6e-6 * theta + 2.4e-6 * envelope * gamma_carrier + 0.4e-6 * rng.normal(size=times.shape)
    control = 4e-6 * np.sin(2 * np.pi * 10.0 * times) + 0.4e-6 * rng.normal(size=times.shape)
    data = np.vstack([signal, control])
    info = mne.create_info(CHANNELS, sfreq=sfreq, ch_types="eeg")
    raw = mne.io.RawArray(data, info, verbose=False)
    onsets = [onset for onset in [2.0, 8.0, 14.0] if onset < duration]
    if not onsets:
        onsets = [max(0.1, duration / 2.0)]
    raw.set_annotations(mne.Annotations(onset=onsets, duration=[0.0] * len(onsets), description=[f"window_{idx + 1}" for idx in range(len(onsets))]))
    raw.save(path, overwrite=True, verbose=False)
    return {
        "path": path.name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "sampling_rate_hz": sfreq,
        "channel_names": CHANNELS,
        "duration_sec": duration,
    }


def synthetic_mi(coupled: bool, phase_center: float, amp_center: float) -> float:
    phase_term = math.exp(-((phase_center - 6.0) ** 2) / 5.0)
    amp_term = math.exp(-((amp_center - 90.0) ** 2) / 250.0)
    base = 0.012 if coupled else 0.004
    scale = 0.095 if coupled else 0.018
    return round(base + scale * phase_term * amp_term, 6)


def build_artifact_case(out: Path, fixture_id: str, raw_meta: dict[str, Any], *, coupled: bool, seed: int) -> dict[str, Any]:
    case_dir = out / fixture_id / "artifact_bundle"
    if case_dir.exists():
        shutil.rmtree(case_dir)
    for rel in ["tables", "figures", "reproducibility"]:
        (case_dir / rel).mkdir(parents=True, exist_ok=True)

    phase_grid = [(4, 6), (6, 8), (8, 10)]
    amp_grid = [(60, 80), (80, 100), (100, 120)]
    comod_rows: list[dict[str, Any]] = []
    for pfmin, pfmax in phase_grid:
        for afmin, afmax in amp_grid:
            comod_rows.append(
                {
                    "file_id": fixture_id,
                    "prep_plan_id": "prep_pac_beta_synthetic_v1",
                    "epoch_set_id": "",
                    "channel": "Cz",
                    "channel_group": "single_channel",
                    "phase_fmin": pfmin,
                    "phase_fmax": pfmax,
                    "amp_fmin": afmin,
                    "amp_fmax": afmax,
                    "metric": "tort_modulation_index",
                    "mi_value": synthetic_mi(coupled, (pfmin + pfmax) / 2, (afmin + afmax) / 2),
                    "n_samples": int(raw_meta["sampling_rate_hz"] * raw_meta["duration_sec"]),
                    "unit": "a.u.",
                }
            )
    write_csv(
        case_dir / "tables" / "pac_comodulogram_long.csv",
        comod_rows,
        ["file_id", "prep_plan_id", "epoch_set_id", "channel", "channel_group", "phase_fmin", "phase_fmax", "amp_fmin", "amp_fmax", "metric", "mi_value", "n_samples", "unit"],
    )

    bins = []
    for idx in range(18):
        start = -math.pi + idx * (2 * math.pi / 18)
        end = -math.pi + (idx + 1) * (2 * math.pi / 18)
        bump = 0.15 * math.cos((start + end) / 2) if coupled else 0.02 * math.sin(idx)
        amp = 1.0 + bump
        bins.append(
            {
                "channel": "Cz",
                "phase_bin_index": idx,
                "phase_bin_start_rad": round(start, 6),
                "phase_bin_end_rad": round(end, 6),
                "mean_amplitude": round(amp, 6),
                "normalized_amplitude": round(amp / 18, 6),
                "sample_count": 120,
            }
        )
    write_csv(case_dir / "tables" / "pac_binned_amplitude.csv", bins, ["channel", "phase_bin_index", "phase_bin_start_rad", "phase_bin_end_rad", "mean_amplitude", "normalized_amplitude", "sample_count"])

    dynamic_rows = []
    for idx in range(5):
        start = idx * 4.0
        dynamic_rows.append(
            {
                "channel": "Cz",
                "window_start_sec": start,
                "window_end_sec": start + 8.0,
                "phase_band_label": "theta_4_8_hz",
                "amp_band_label": "high_gamma_70_110_hz",
                "metric": "tort_modulation_index",
                "mi_value": round((0.074 if coupled else 0.012) + idx * (0.002 if coupled else 0.0005), 6),
            }
        )
    write_csv(case_dir / "tables" / "pac_dynamic_curve.csv", dynamic_rows, ["channel", "window_start_sec", "window_end_sec", "phase_band_label", "amp_band_label", "metric", "mi_value"])

    peak = max(comod_rows, key=lambda row: float(row["mi_value"]))
    summary_rows = [
        {
            "channel": "Cz",
            "channel_group": "single_channel",
            "peak_phase_band": f"{peak['phase_fmin']}-{peak['phase_fmax']} Hz",
            "peak_amp_band": f"{peak['amp_fmin']}-{peak['amp_fmax']} Hz",
            "peak_mi": peak["mi_value"],
            "data_coverage_sec": raw_meta["duration_sec"],
            "warnings": "single-record descriptive beta; no statistical significance",
        }
    ]
    write_csv(case_dir / "tables" / "pac_channel_summary.csv", summary_rows, ["channel", "channel_group", "peak_phase_band", "peak_amp_band", "peak_mi", "data_coverage_sec", "warnings"])

    write_svg(case_dir / "figures" / "pac_comodulogram.svg", "PAC beta comodulogram", "MI by phase-frequency and amplitude-frequency grid; unit: a.u.")
    write_svg(case_dir / "figures" / "pac_phase_bins.svg", "PAC beta phase bins", "Mean high-frequency amplitude by low-frequency phase bin.")
    write_svg(case_dir / "figures" / "pac_dynamic_curve.svg", "PAC beta dynamic curve", "Windowed MI over time; descriptive beta output.")

    params = {
        "schema_version": "qlanalyser-pac-beta-parameters-v0.1",
        "module_id": "pac_cfc",
        "workflow_id": "pac_cfc_beta",
        "input_file_id": fixture_id,
        "data_preparation_plan_id": "prep_pac_beta_synthetic_v1",
        "data_preparation_revision": 1,
        "analysis_scope": "raw_window",
        "channels": ["Cz"],
        "phase_freqs": [4, 6, 8],
        "phase_band_width": 2,
        "amp_freqs": [70, 90, 110],
        "amp_band_width": 20,
        "metric": "tort_modulation_index",
        "n_phase_bins": 18,
        "filter_edge_padding_sec": 2.0,
        "edge_trim_sec": 1.0,
        "dynamic_window_sec": 8.0,
        "dynamic_step_sec": 4.0,
        "surrogate_quality_check": {"enabled": False, "label": "quality/context check only; no p-value or significance output"},
    }
    params_hash = hashlib.sha256(json.dumps(params, sort_keys=True).encode("utf-8")).hexdigest()
    params["parameters_hash"] = params_hash
    write_json(case_dir / "reproducibility" / "parameters.json", params)
    write_json(case_dir / "reproducibility" / "effective_call.json", {"function": "synthetic_pac_beta_fixture", "seed": seed, "parameters_hash": params_hash})
    write_json(case_dir / "reproducibility" / "frequency_grid.json", {"phase_bands_hz": phase_grid, "amplitude_bands_hz": amp_grid, "nyquist_hz": raw_meta["sampling_rate_hz"] / 2})
    write_json(case_dir / "reproducibility" / "filter_edge_policy.json", {"filter_edge_padding_sec": 2.0, "edge_trim_sec": 1.0, "window_too_short_policy": "block"})
    write_json(case_dir / "reproducibility" / "scope_contract.json", {"scope": "single_record_descriptive_beta", "forbidden": ["diagnosis", "p_value", "significance", "group_comparison", "causality", "brain_region_communication", "source_localization"]})
    write_json(
        case_dir / "reproducibility" / "table_dictionary.json",
        {
            "tables/pac_comodulogram_long.csv": {key: "PAC beta export column" for key in comod_rows[0]},
            "tables/pac_binned_amplitude.csv": {key: "PAC beta export column" for key in bins[0]},
            "tables/pac_dynamic_curve.csv": {key: "PAC beta export column" for key in dynamic_rows[0]},
            "tables/pac_channel_summary.csv": {key: "PAC beta export column" for key in summary_rows[0]},
        },
    )

    result = {
        "schema_version": "qlanalyser-pac-beta-result-v0.1",
        "module_id": "pac_cfc",
        "workflow_id": "pac_cfc_beta",
        "input_file_id": fixture_id,
        "data_preparation_plan_id": "prep_pac_beta_synthetic_v1",
        "parameters_hash": params_hash,
        "summary": {
            "peak_phase_band": summary_rows[0]["peak_phase_band"],
            "peak_amp_band": summary_rows[0]["peak_amp_band"],
            "peak_mi": summary_rows[0]["peak_mi"],
            "interpretation_boundary": FORBIDDEN_BOUNDARY,
        },
        "artifacts": [
            "tables/pac_comodulogram_long.csv",
            "tables/pac_binned_amplitude.csv",
            "tables/pac_dynamic_curve.csv",
            "tables/pac_channel_summary.csv",
            "figures/pac_comodulogram.svg",
            "figures/pac_phase_bins.svg",
            "figures/pac_dynamic_curve.svg",
        ],
        "warnings": ["PAC beta fixture validates artifact shape only; it is not biological evidence."],
    }
    write_json(case_dir / "result.json", result)

    zip_path = out / fixture_id / "pac_beta_artifact_bundle.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(case_dir.rglob("*")):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(case_dir).as_posix())
    return {"artifact_dir": str(case_dir), "bundle_zip": str(zip_path), "peak_mi": peak["mi_value"]}


def build_negative_cases(out: Path) -> None:
    missing = out / "negative_missing_plan" / "artifact_bundle"
    shutil.copytree(out / "positive_known_pac" / "artifact_bundle", missing, dirs_exist_ok=True)
    result = json.loads((missing / "result.json").read_text(encoding="utf-8"))
    result.pop("data_preparation_plan_id", None)
    write_json(missing / "result.json", result)

    forbidden = out / "negative_forbidden_claim" / "artifact_bundle"
    shutil.copytree(out / "positive_known_pac" / "artifact_bundle", forbidden, dirs_exist_ok=True)
    result = json.loads((forbidden / "result.json").read_text(encoding="utf-8"))
    result["summary"]["overclaim"] = "This proves significant brain-region communication for diagnosis."
    write_json(forbidden / "result.json", result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--seed", type=int, default=20260621)
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    positive_raw = out / "positive_known_pac_raw.fif"
    control_raw = out / "no_coupling_control_raw.fif"
    short_raw = out / "short_window_raw.fif"
    positive_meta = build_raw(positive_raw, args.seed, coupled=True, duration=24.0)
    control_meta = build_raw(control_raw, args.seed + 1, coupled=False, duration=24.0)
    short_meta = build_raw(short_raw, args.seed + 2, coupled=True, duration=1.5)
    positive_artifact = build_artifact_case(out, "positive_known_pac", positive_meta, coupled=True, seed=args.seed)
    control_artifact = build_artifact_case(out, "no_coupling_control", control_meta, coupled=False, seed=args.seed + 1)
    build_negative_cases(out)

    manifest = {
        "schema_version": "qlanalyser-pac-beta-fixture-manifest-v0.1",
        "fixture_id": "pac_beta_synthetic_suite",
        "privacy_status": "synthetic_only_no_real_participant_customer_or_phi",
        "seed": args.seed,
        "sampling_rate_hz": positive_meta["sampling_rate_hz"],
        "channel_names": CHANNELS,
        "duration_sec": positive_meta["duration_sec"],
        "known_phase_band_hz": PHASE_BAND,
        "known_amplitude_band_hz": AMP_BAND,
        "expected_peak_region": "theta phase by high-gamma amplitude",
        "expected_positive_vs_control_relation": "positive_known_pac peak MI higher than no_coupling_control",
        "raw_file_sha256": positive_meta["sha256"],
        "no_real_participant_or_customer_data": True,
        "cases": {
            "positive_known_pac": {"raw": positive_meta, **positive_artifact},
            "no_coupling_control": {"raw": control_meta, **control_artifact},
            "short_window_blocker": {"raw": short_meta, "expected_blocker": "WINDOW_TOO_SHORT_FOR_PHASE"},
            "nyquist_blocker_metadata": {"sampling_rate_hz": 160.0, "amp_freqs": [90, 120], "expected_blocker": "AMP_FREQ_EXCEEDS_NYQUIST"},
        },
        "generated_at": datetime.now(UTC).isoformat(),
        "boundary": FORBIDDEN_BOUNDARY,
    }
    write_json(out / "fixture_manifest.json", manifest)
    write_json(out / "nyquist_blocker_manifest.json", manifest["cases"]["nyquist_blocker_metadata"])
    print(json.dumps({"status": "built", "out": str(out), "manifest": str(out / "fixture_manifest.json")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
