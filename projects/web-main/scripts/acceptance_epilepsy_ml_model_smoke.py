from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eeg_core.analysis.epilepsy_ml import (
    FEATURE_COLUMNS,
    _load_model_and_scaler,
    _model_info_for_epoch,
    _validated_model_manifest,
)


OUT_DIR = ROOT / "work" / "e2e_epilepsy_ml_migration"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = _validated_model_manifest()
    rows = {}
    for epoch_length in (3.0, 5.0):
        model_info, selected = _model_info_for_epoch(epoch_length, manifest)
        model, scaler = _load_model_and_scaler(model_info)
        feature_count = int(getattr(scaler, "n_features_in_", len(FEATURE_COLUMNS)))
        if feature_count != 19:
            raise AssertionError(f"Scaler feature count drifted for {epoch_length}: {feature_count}")
        features = np.zeros((3, len(FEATURE_COLUMNS)), dtype=np.float32)
        scaled = scaler.transform(features)
        probabilities = model.predict_proba(scaled)[:, 1]
        if probabilities.shape != (3,):
            raise AssertionError(f"Probability shape drifted for {epoch_length}: {probabilities.shape}")
        rows[str(epoch_length)] = {
            "selected_model_epoch_length_sec": selected,
            "model_file": model_info["model_file"],
            "scaler_file": model_info["scaler_file"],
            "scaler_n_features_in": feature_count,
            "probability_shape": list(probabilities.shape),
            "probability_preview": [float(value) for value in probabilities],
        }
    out_path = OUT_DIR / "model_smoke.json"
    out_path.write_text(json.dumps({"status": "PASS", "models": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "PASS", "evidence": str(out_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
