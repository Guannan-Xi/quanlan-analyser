from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services.lab_demo_service import ensure_epilepsy_demo_dataset
from eeg_core.analysis.epilepsy_ml import run_epilepsy_ml


OUT_DIR = ROOT / "work" / "e2e_epilepsy_ml_migration" / "fixture_run"


def main() -> None:
    fixture = ensure_epilepsy_demo_dataset()
    file_payload = fixture["file"]
    outputs = run_epilepsy_ml(
        file_payload["stored_path"],
        OUT_DIR,
        {
            "method": "ml_epoch_classifier",
            "epoch_length_sec": 5,
            "probability_threshold": 0.5,
            "unit_mode": "source_compatible",
            "lab_fixture_id": fixture["fixture_id"],
        },
    )
    summary_path = outputs["epilepsy_ml_summary"]
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    evidence = {
        "status": "PASS",
        "fixture_id": fixture["fixture_id"],
        "file_id": file_payload["id"],
        "output_dir": str(OUT_DIR),
        "summary": summary,
        "outputs": {key: str(value) for key, value in outputs.items()},
    }
    out_path = ROOT / "work" / "e2e_epilepsy_ml_migration" / "fixture_run_evidence.json"
    out_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "PASS", "evidence": str(out_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
