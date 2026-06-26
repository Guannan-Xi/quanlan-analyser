from __future__ import annotations

import json
import sys
from pathlib import Path

import mne
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eeg_core.analysis.epilepsy_ml import (
    RESOURCE_ROOT,
    _load_model_and_scaler,
    _model_info_for_epoch,
    _validated_model_manifest,
    extract_features_using_epochs,
)


OUT_DIR = ROOT / "work" / "e2e_epilepsy_ml_demo"
RAW_PATH = OUT_DIR / "epilepsy_ml_demo_source_channels_raw.fif"
EDF_PATH = OUT_DIR / "epilepsy_ml_demo_source_channels.edf"
METADATA_PATH = OUT_DIR / "epilepsy_ml_demo_source_channels_metadata.json"
SEARCH_EVIDENCE_PATH = OUT_DIR / "epilepsy_ml_demo_search_evidence.json"


def candidate_epoch(fs: float, *, freq: float, amp: float, noise: float, burst: bool, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(int(5.0 * fs)) / fs
    signal = amp * np.sin(2 * np.pi * freq * t)
    signal += 0.35 * amp * np.sin(2 * np.pi * min(freq * 2.7, 90.0) * t + 0.4)
    if burst:
        gate = ((t > 1.0) & (t < 1.9)) | ((t > 2.6) & (t < 3.3))
        signal[gate] += amp * 1.8 * np.sin(2 * np.pi * min(freq * 4.1, 95.0) * t[gate])
    signal += noise * rng.standard_normal(t.size)
    return signal.astype(np.float64)


def quiet_epoch(fs: float, *, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(int(5.0 * fs)) / fs
    signal = 0.001 * np.sin(2 * np.pi * 8.0 * t)
    signal += 0.0001 * rng.standard_normal(t.size)
    return signal.astype(np.float64)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fs = 250.0
    manifest = _validated_model_manifest()
    model_info, _ = _model_info_for_epoch(5.0, manifest)
    model, scaler = _load_model_and_scaler(model_info)

    candidates = []
    for freq in [0.7, 1.5, 2.5, 4, 6, 8, 12, 18, 30, 45, 70]:
        for amp in np.logspace(-3, 5, 33):
            for burst in [False, True]:
                noise = amp * 0.08
                epoch = candidate_epoch(fs, freq=freq, amp=float(amp), noise=float(noise), burst=burst, seed=int(freq * 1000 + amp) % 100000)
                features = extract_features_using_epochs(epoch.reshape(1, 1, -1), fs)
                proba = float(model.predict_proba(scaler.transform(features))[:, 1][0])
                candidates.append({"freq": freq, "amp": float(amp), "burst": burst, "probability": proba})
    candidates.sort(key=lambda item: item["probability"], reverse=True)
    best = candidates[0]
    if best["probability"] < 0.5:
        raise RuntimeError(f"No trigger candidate reached 0.5; best={best}")

    normal_epoch = quiet_epoch(fs, seed=1)
    trigger_epoch_a = candidate_epoch(
        fs,
        freq=float(best["freq"]),
        amp=float(best["amp"]),
        noise=float(best["amp"]) * 0.08,
        burst=bool(best["burst"]),
        seed=2401,
    )
    trigger_epoch_b = candidate_epoch(
        fs,
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
    rng = np.random.default_rng(20260626)
    data = np.vstack(
        [
            0.03 * np.sin(2 * np.pi * 8 * np.arange(n_times) / fs) + 0.003 * rng.standard_normal(n_times),
            0.001 * np.sin(2 * np.pi * 11 * np.arange(n_times) / fs) + 0.0001 * rng.standard_normal(n_times),
            0.001 * np.sin(2 * np.pi * 6 * np.arange(n_times) / fs) + 0.0001 * rng.standard_normal(n_times),
            eeg3,
            0.005 * rng.standard_normal(n_times),
        ]
    )
    channels = ["EEG0", "EEG1", "EEG2", "EEG3", "ACC0"]
    ch_types = ["eeg", "eeg", "eeg", "eeg", "misc"]
    raw = mne.io.RawArray(data, mne.create_info(channels, fs, ch_types=ch_types), verbose="ERROR")
    raw.save(RAW_PATH, overwrite=True, verbose="ERROR")
    edf_data = data.copy()
    edf_data[:4] = edf_data[:4] / 1e6
    edf_raw = mne.io.RawArray(edf_data, mne.create_info(channels, fs, ch_types=ch_types), verbose="ERROR")
    edf_raw.export(EDF_PATH, fmt="edf", overwrite=True, verbose="ERROR")

    features = extract_features_using_epochs(eeg3.reshape(12, 1, int(5 * fs)), fs)
    probabilities = model.predict_proba(scaler.transform(features))[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    expected_stage_code = [0] * 12
    expected_stage_code[5] = 1
    expected_stage_code[6] = 1
    if [int(value) for value in predictions] != expected_stage_code:
        raise RuntimeError(
            "Generated epilepsy ML fixture does not isolate the expected trigger window: "
            f"stage_code={[int(value) for value in predictions]}, probabilities={[float(value) for value in probabilities]}"
        )
    evidence = {
        "status": "PASS",
        "raw_path": str(RAW_PATH),
        "edf_path": str(EDF_PATH),
        "best_candidate": best,
        "epoch_probabilities": [float(value) for value in probabilities],
        "stage_code": [int(value) for value in predictions],
        "expected_stage_code": expected_stage_code,
        "expected_trigger_epochs_zero_based": [5, 6],
        "selected_channel": "EEG3",
        "unit_note": "EDF stores EEG in volts; migrated ML source_compatible mode multiplies EDF/BDF EEG by 1e6 before features.",
    }
    SEARCH_EVIDENCE_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    METADATA_PATH.write_text(
        json.dumps(
            {
                "dataset_name": EDF_PATH.name,
                "raw_path": str(EDF_PATH),
                "fif_source_scale_path": str(RAW_PATH),
                "edf_path": str(EDF_PATH),
                "sfreq": fs,
                "duration_sec": n_times / fs,
                "channels": channels,
                "selected_channel": "EEG3",
                "expected_trigger_epochs_zero_based": [5, 6],
                "expected_trigger_window_sec": [25.0, 35.0],
                "search_evidence_path": str(SEARCH_EVIDENCE_PATH),
                "non_medical_boundary": "Synthetic research/demo data only; not clinical EEG and not for diagnosis.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"status": "PASS", "raw_path": str(EDF_PATH), "fif_source_scale_path": str(RAW_PATH), "evidence": str(SEARCH_EVIDENCE_PATH)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
