from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eeg_core.analysis.epilepsy_ml import (
    FEATURE_COLUMNS,
    detect_seizures_source_compatible,
    extract_features_using_epochs,
)


OUT_DIR = ROOT / "work" / "e2e_epilepsy_ml_migration"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fs = 250.0
    epoch_samples = int(5.0 * fs)
    t = np.arange(epoch_samples) / fs
    epochs = []
    for idx in range(4):
        epochs.append((0.1 * (idx + 1) * np.sin(2 * np.pi * (6 + idx) * t)).astype(np.float64))
    data_segment = np.asarray(epochs).reshape(4, 1, epoch_samples)

    features = extract_features_using_epochs(data_segment, fs)
    assert_true(features.shape == (4, 19), f"feature shape mismatch: {features.shape}")
    assert_true(features.dtype == np.float32, f"feature dtype mismatch: {features.dtype}")
    assert_true(FEATURE_COLUMNS == [
        "mean", "mobility", "TKEO", "P_delta", "P_theta", "P_alpha", "P_beta", "P_gamma", "P_total",
        "rel_delta", "rel_theta", "rel_alpha", "rel_beta", "rel_gamma", "pfd", "skew", "kurtosis", "var", "envelope",
    ], "feature column order drifted")
    assert_true(np.isfinite(features).all(), "features contain nan/inf")

    classifications = np.asarray([0, 1, 0, 1, 1, 0, 1, 1, 1], dtype=int)
    data = np.sin(2 * np.pi * 8 * np.arange(int(len(classifications) * epoch_samples)) / fs)
    events, windows, mask = detect_seizures_source_compatible(classifications, data, fs, epoch_length=5.0, start_time_ts=0)
    assert_true(len(events) == 2, f"expected 2 events; got {len(events)}")
    assert_true(events[0]["start_epoch"] == 3 and events[0]["end_epoch"] == 4, "first event epoch range drifted")
    assert_true(events[0]["source_start_epoch_1based"] == 4, "source 1-based start epoch drifted")
    assert_true(mask == [0, 0, 0, 1, 1, 0, 1, 1, 1], f"event mask drifted: {mask}")
    assert_true(windows and windows[0]["event_count"] == 2, "30-minute event window count drifted")

    out_path = OUT_DIR / "feature_contract.json"
    out_path.write_text(
        json.dumps(
            {
                "status": "PASS",
                "feature_shape": list(features.shape),
                "feature_dtype": str(features.dtype),
                "feature_columns": FEATURE_COLUMNS,
                "event_rows": events,
                "window_rows": windows,
                "event_mask": mask,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"status": "PASS", "evidence": str(out_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
