from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import mne
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eeg_core.analysis.epilepsy_ml import (  # noqa: E402
    _load_model_and_scaler,
    _model_info_for_epoch,
    _validated_model_manifest,
    extract_features_using_epochs,
    run_epilepsy_ml,
)


FIXTURE_ID = "regular_epilepsy_labeled_60s_v1"
OUT_DIR = ROOT / "work" / "fixtures" / "epilepsy_regular_labeled"
EVIDENCE_DIR = ROOT / "work" / "release_evidence" / "20260629-regular-epilepsy-labeled-fixture"
RAW_PATH = OUT_DIR / "regular_epilepsy_labeled_60s_raw.fif"
EDF_PATH = OUT_DIR / "regular_epilepsy_labeled_60s.edf"
STAGE_PATH = OUT_DIR / "regular_epilepsy_labeled_stage_code.csv"
EVENTS_PATH = OUT_DIR / "regular_epilepsy_labeled_events.csv"
MANIFEST_PATH = OUT_DIR / "regular_epilepsy_labeled_manifest.json"
GENERATION_EVIDENCE_PATH = OUT_DIR / "regular_epilepsy_labeled_generation_evidence.json"
ALGORITHM_OUTPUT_DIR = EVIDENCE_DIR / "algorithm_replay"
ACCEPTANCE_PATH = EVIDENCE_DIR / "regular_epilepsy_labeled_fixture_acceptance.json"

SFREQ = 250.0
EPOCH_LENGTH_SEC = 5.0
CHANNELS = ["EEG0", "EEG1", "EEG2", "EEG3", "ACC0"]
CH_TYPES = ["eeg", "eeg", "eeg", "eeg", "misc"]
SELECTED_CHANNEL = "EEG3"
EXPECTED_STAGE_CODE = [0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0]
EXPECTED_EVENTS = [
    {
        "event_id": 1,
        "start_sec": 25.0,
        "end_sec": 35.0,
        "duration_sec": 10.0,
        "start_epoch": 5,
        "end_epoch": 6,
        "epoch_count": 2,
        "label": "synthetic_epileptiform_candidate",
    }
]


def candidate_epoch(fs: float, *, freq: float, amp: float, noise: float, burst: bool, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(int(EPOCH_LENGTH_SEC * fs)) / fs
    signal = amp * np.sin(2 * np.pi * freq * t)
    signal += 0.35 * amp * np.sin(2 * np.pi * min(freq * 2.7, 90.0) * t + 0.4)
    if burst:
        gate = ((t > 1.0) & (t < 1.9)) | ((t > 2.6) & (t < 3.3))
        signal[gate] += amp * 1.8 * np.sin(2 * np.pi * min(freq * 4.1, 95.0) * t[gate])
    signal += noise * rng.standard_normal(t.size)
    return signal.astype(np.float64)


def quiet_epoch(fs: float, *, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(int(EPOCH_LENGTH_SEC * fs)) / fs
    signal = 0.001 * np.sin(2 * np.pi * 8.0 * t)
    signal += 0.0001 * rng.standard_normal(t.size)
    return signal.astype(np.float64)


def find_trigger_candidate(fs: float) -> dict[str, Any]:
    manifest = _validated_model_manifest()
    model_info, _ = _model_info_for_epoch(EPOCH_LENGTH_SEC, manifest)
    model, scaler = _load_model_and_scaler(model_info)

    candidates = []
    for freq in [0.7, 1.5, 2.5, 4, 6, 8, 12, 18, 30, 45, 70]:
        for amp in np.logspace(-3, 5, 33):
            for burst in [False, True]:
                noise = float(amp) * 0.08
                epoch = candidate_epoch(
                    fs,
                    freq=float(freq),
                    amp=float(amp),
                    noise=noise,
                    burst=burst,
                    seed=int(freq * 1000 + amp) % 100000,
                )
                features = extract_features_using_epochs(epoch.reshape(1, 1, -1), fs)
                probability = float(model.predict_proba(scaler.transform(features))[:, 1][0])
                candidates.append(
                    {
                        "freq": float(freq),
                        "amp": float(amp),
                        "burst": bool(burst),
                        "probability": probability,
                    }
                )

    candidates.sort(key=lambda item: item["probability"], reverse=True)
    best = candidates[0]
    if best["probability"] < 0.5:
        raise RuntimeError(f"No trigger candidate reached 0.5; best={best}")
    return {"best": best, "top5": candidates[:5]}


def build_signal(best: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, list[float], list[int]]:
    normal_epoch = quiet_epoch(SFREQ, seed=1)
    trigger_epoch_a = candidate_epoch(
        SFREQ,
        freq=float(best["freq"]),
        amp=float(best["amp"]),
        noise=float(best["amp"]) * 0.08,
        burst=bool(best["burst"]),
        seed=2401,
    )
    trigger_epoch_b = candidate_epoch(
        SFREQ,
        freq=float(best["freq"]),
        amp=float(best["amp"]) * 1.05,
        noise=float(best["amp"]) * 0.08,
        burst=bool(best["burst"]),
        seed=2402,
    )
    epochs = [normal_epoch.copy() for _ in range(12)]
    epochs[5] = trigger_epoch_a
    epochs[6] = trigger_epoch_b
    eeg3 = np.concatenate(epochs)
    n_times = eeg3.size

    rng = np.random.default_rng(20260629)
    t = np.arange(n_times) / SFREQ
    data = np.vstack(
        [
            0.03 * np.sin(2 * np.pi * 8 * t) + 0.003 * rng.standard_normal(n_times),
            0.001 * np.sin(2 * np.pi * 11 * t) + 0.0001 * rng.standard_normal(n_times),
            0.001 * np.sin(2 * np.pi * 6 * t) + 0.0001 * rng.standard_normal(n_times),
            eeg3,
            0.005 * rng.standard_normal(n_times),
        ]
    )

    manifest = _validated_model_manifest()
    model_info, _ = _model_info_for_epoch(EPOCH_LENGTH_SEC, manifest)
    model, scaler = _load_model_and_scaler(model_info)
    features = extract_features_using_epochs(eeg3.reshape(12, 1, int(EPOCH_LENGTH_SEC * SFREQ)), SFREQ)
    probabilities = [float(value) for value in model.predict_proba(scaler.transform(features))[:, 1]]
    predictions = [int(value >= 0.5) for value in probabilities]
    return data, eeg3, probabilities, predictions


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_fixture_files(data: np.ndarray, probabilities: list[float], search: dict[str, Any]) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    raw = mne.io.RawArray(data, mne.create_info(CHANNELS, SFREQ, ch_types=CH_TYPES), verbose="ERROR")
    raw.save(RAW_PATH, overwrite=True, verbose="ERROR")

    edf_data = data.copy()
    edf_data[:4] = edf_data[:4] / 1e6
    edf_raw = mne.io.RawArray(edf_data, mne.create_info(CHANNELS, SFREQ, ch_types=CH_TYPES), verbose="ERROR")
    edf_raw.export(EDF_PATH, fmt="edf", overwrite=True, verbose="ERROR")

    stage_rows = []
    for index, code in enumerate(EXPECTED_STAGE_CODE):
        stage_rows.append(
            {
                "epoch_index": index,
                "start_sec": float(index * EPOCH_LENGTH_SEC),
                "end_sec": float((index + 1) * EPOCH_LENGTH_SEC),
                "duration_sec": EPOCH_LENGTH_SEC,
                "Stage_Code": code,
                "Stage": "Seizure" if code else "Normal",
                "expected_probability": probabilities[index],
                "truth_source": "synthetic_fixture_manifest",
            }
        )
    write_csv(
        STAGE_PATH,
        ["epoch_index", "start_sec", "end_sec", "duration_sec", "Stage_Code", "Stage", "expected_probability", "truth_source"],
        stage_rows,
    )
    write_csv(
        EVENTS_PATH,
        ["event_id", "start_sec", "end_sec", "duration_sec", "start_epoch", "end_epoch", "epoch_count", "label"],
        EXPECTED_EVENTS,
    )

    manifest = {
        "fixture_id": FIXTURE_ID,
        "mode": "regular_upload_test",
        "dataset_name": EDF_PATH.name,
        "edf_path": str(EDF_PATH),
        "fif_source_scale_path": str(RAW_PATH),
        "stage_code_truth_path": str(STAGE_PATH),
        "event_truth_path": str(EVENTS_PATH),
        "non_medical_boundary": "Synthetic research screening support only; not clinical EEG and not diagnosis.",
        "sfreq": SFREQ,
        "duration_sec": 60.0,
        "channels": CHANNELS,
        "selected_channel": SELECTED_CHANNEL,
        "epoch_length_sec": EPOCH_LENGTH_SEC,
        "expected_stage_code": EXPECTED_STAGE_CODE,
        "expected_events": EXPECTED_EVENTS,
        "recommended_parameters": {
            "method": "ml_epoch_classifier",
            "workflow_id": "epilepsy_ml_xgboost",
            "eeg_channel": SELECTED_CHANNEL,
            "epoch_length_sec": EPOCH_LENGTH_SEC,
            "probability_threshold": 0.5,
            "unit_mode": "source_compatible",
        },
        "regular_mode_note": "This fixture is not registered as protected teaching data; use it as a normal EDF upload/regression source.",
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    generation = {
        "status": "PASS",
        "fixture_id": FIXTURE_ID,
        "search": search,
        "epoch_probabilities": probabilities,
        "expected_stage_code": EXPECTED_STAGE_CODE,
        "outputs": {
            "edf": str(EDF_PATH),
            "fif_source_scale": str(RAW_PATH),
            "stage_code_truth": str(STAGE_PATH),
            "events_truth": str(EVENTS_PATH),
            "manifest": str(MANIFEST_PATH),
        },
    }
    GENERATION_EVIDENCE_PATH.write_text(json.dumps(generation, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def replay_algorithm(manifest: dict[str, Any]) -> dict[str, Any]:
    if ALGORITHM_OUTPUT_DIR.exists():
        shutil.rmtree(ALGORITHM_OUTPUT_DIR)
    params = dict(manifest["recommended_parameters"])
    params["fixture_id"] = FIXTURE_ID
    outputs = run_epilepsy_ml(EDF_PATH, ALGORITHM_OUTPUT_DIR, params)

    epoch_rows = read_csv_dicts(outputs["epilepsy_ml_epoch_predictions"])
    event_rows = read_csv_dicts(outputs["epilepsy_ml_events"])
    summary = json.loads(Path(outputs["epilepsy_ml_summary"]).read_text(encoding="utf-8"))
    observed_stage_code = [int(row["Stage_Code"]) for row in epoch_rows]
    observed_events = [
        {
            "start_sec": float(row["start_sec"]),
            "end_sec": float(row["end_sec"]),
            "start_epoch": int(row["start_epoch"]),
            "end_epoch": int(row["end_epoch"]),
            "epoch_count": int(row["epoch_count"]),
        }
        for row in event_rows
    ]

    checks = {
        "algorithm_status_computed": summary.get("status") == "computed",
        "selected_channel_EEG3": summary.get("channel") == SELECTED_CHANNEL,
        "stage_code_matches_truth": observed_stage_code == EXPECTED_STAGE_CODE,
        "single_expected_event_detected": len(observed_events) == 1
        and observed_events[0]["start_sec"] == 25.0
        and observed_events[0]["end_sec"] == 35.0
        and observed_events[0]["start_epoch"] == 5
        and observed_events[0]["end_epoch"] == 6,
        "non_medical_boundary_present": any(
            warning.get("name") == "non_medical_scope" for warning in summary.get("warnings", [])
        ),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    acceptance = {
        "status": status,
        "fixture_id": FIXTURE_ID,
        "manifest_path": str(MANIFEST_PATH),
        "algorithm_output_dir": str(ALGORITHM_OUTPUT_DIR),
        "checks": checks,
        "observed_stage_code": observed_stage_code,
        "expected_stage_code": EXPECTED_STAGE_CODE,
        "observed_events": observed_events,
        "expected_events": EXPECTED_EVENTS,
        "summary_snapshot": {
            "status": summary.get("status"),
            "module": summary.get("module"),
            "method": summary.get("method"),
            "channel": summary.get("channel"),
            "epoch_count": summary.get("epoch_count"),
            "event_count": summary.get("event_count"),
        },
        "outputs": {key: str(value) for key, value in outputs.items()},
    }
    ACCEPTANCE_PATH.write_text(json.dumps(acceptance, ensure_ascii=False, indent=2), encoding="utf-8")
    if status != "PASS":
        raise RuntimeError(json.dumps(acceptance, ensure_ascii=False, indent=2))
    return acceptance


def main() -> None:
    search = find_trigger_candidate(SFREQ)
    data, _eeg3, probabilities, predictions = build_signal(search["best"])
    if predictions != EXPECTED_STAGE_CODE:
        raise RuntimeError(
            "Generated regular epilepsy fixture does not isolate expected trigger window: "
            f"stage_code={predictions}, probabilities={probabilities}"
        )
    manifest = write_fixture_files(data, probabilities, search)
    acceptance = replay_algorithm(manifest)
    print(
        json.dumps(
            {
                "status": "PASS",
                "fixture_id": FIXTURE_ID,
                "edf_path": str(EDF_PATH),
                "manifest_path": str(MANIFEST_PATH),
                "acceptance_path": str(ACCEPTANCE_PATH),
                "observed_stage_code": acceptance["observed_stage_code"],
                "observed_events": acceptance["observed_events"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
