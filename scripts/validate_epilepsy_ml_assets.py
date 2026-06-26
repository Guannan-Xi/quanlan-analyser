from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "work" / "e2e_epilepsy_ml_migration"
sys.path.insert(0, str(ROOT))

from eeg_core.analysis.epilepsy_ml import FEATURE_COLUMNS, _validated_model_manifest


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = _validated_model_manifest()
    payload = {
        "status": "PASS",
        "manifest_contract": manifest.get("migration_contract"),
        "models": manifest.get("models"),
        "feature_columns": FEATURE_COLUMNS,
        "feature_count": len(FEATURE_COLUMNS),
    }
    out_path = OUT_DIR / "asset_validation.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "PASS", "evidence": str(out_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
