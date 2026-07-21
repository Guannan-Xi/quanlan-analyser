from __future__ import annotations

import hashlib
import json
from pathlib import Path

import mne
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "work" / "fixtures" / "epilepsy_demo_10min_64ch"
EDF_PATH = OUTPUT_DIR / "synthetic_epilepsy_demo_10min_64ch_1000hz.edf"
MANIFEST_PATH = OUTPUT_DIR / "synthetic_epilepsy_demo_10min_64ch_1000hz.manifest.json"

SAMPLE_RATE_HZ = 1000.0
DURATION_SEC = 600.0
CHANNEL_NAMES = [f"EEG{index:02d}" for index in range(1, 65)]
EVENTS = [
    {"event_id": "SYN-E001", "start_sec": 120.0, "end_sec": 140.0, "channels": list(range(0, 16))},
    {"event_id": "SYN-E002", "start_sec": 300.0, "end_sec": 325.0, "channels": list(range(16, 40))},
    {"event_id": "SYN-E003", "start_sec": 480.0, "end_sec": 500.0, "channels": list(range(40, 64))},
]


def build_data() -> np.ndarray:
    sample_count = int(SAMPLE_RATE_HZ * DURATION_SEC)
    time = np.arange(sample_count, dtype=np.float64) / SAMPLE_RATE_HZ
    rng = np.random.default_rng(20260721)
    data = np.empty((len(CHANNEL_NAMES), sample_count), dtype=np.float64)

    for channel_index in range(len(CHANNEL_NAMES)):
        alpha_hz = 8.0 + (channel_index % 7) * 0.35
        theta_hz = 4.0 + (channel_index % 5) * 0.2
        phase = channel_index * 0.17
        baseline = 18e-6 * np.sin(2 * np.pi * alpha_hz * time + phase)
        baseline += 8e-6 * np.sin(2 * np.pi * theta_hz * time + phase * 0.5)
        baseline += rng.normal(0.0, 5e-6, sample_count)
        data[channel_index] = baseline

    for event_index, event in enumerate(EVENTS):
        start = int(event["start_sec"] * SAMPLE_RATE_HZ)
        stop = int(event["end_sec"] * SAMPLE_RATE_HZ)
        event_time = time[start:stop] - event["start_sec"]
        envelope = np.sin(np.pi * np.linspace(0.0, 1.0, stop - start)) ** 2
        base_frequency = 5.5 + event_index * 1.5
        for local_index, channel_index in enumerate(event["channels"]):
            phase = local_index * 0.11
            rhythmic = 145e-6 * np.sin(2 * np.pi * base_frequency * event_time + phase)
            harmonic = 65e-6 * np.sin(2 * np.pi * base_frequency * 2.4 * event_time + phase * 0.7)
            spike_train = 95e-6 * np.maximum(0.0, np.sin(2 * np.pi * 2.2 * event_time + phase)) ** 10
            data[channel_index, start:stop] += envelope * (rhythmic + harmonic + spike_train)

    return data


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = build_data()
    info = mne.create_info(CHANNEL_NAMES, SAMPLE_RATE_HZ, ch_types=["eeg"] * len(CHANNEL_NAMES))
    raw = mne.io.RawArray(data, info, verbose="ERROR")
    raw.export(EDF_PATH, fmt="edf", overwrite=True, verbose="ERROR")

    verified = mne.io.read_raw_edf(EDF_PATH, preload=False, verbose="ERROR")
    manifest = {
        "schema_version": "qlanalyser.synthetic_epilepsy_demo.v1",
        "dataset_name": EDF_PATH.name,
        "synthetic": True,
        "non_medical_scope": "research_screening_demo_only_not_clinical_diagnosis",
        "sample_rate_hz": float(verified.info["sfreq"]),
        "duration_sec": float(verified.n_times / verified.info["sfreq"]),
        "channel_count": len(verified.ch_names),
        "channels": list(verified.ch_names),
        "events": [
            {
                **{key: value for key, value in event.items() if key != "channels"},
                "duration_sec": event["end_sec"] - event["start_sec"],
                "channel_names": [CHANNEL_NAMES[index] for index in event["channels"]],
                "label": "synthetic_epileptiform_candidate",
            }
            for event in EVENTS
        ],
        "size_bytes": EDF_PATH.stat().st_size,
        "sha256": sha256(EDF_PATH),
        "generator": Path(__file__).name,
        "seed": 20260721,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
