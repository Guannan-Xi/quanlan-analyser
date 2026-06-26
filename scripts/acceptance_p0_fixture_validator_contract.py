from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "work" / "fixtures" / "p0_modules"
EVIDENCE_DIR = ROOT / "work" / "release_evidence" / "p0_fixture_validator"
MODULES = ["preprocessing_readiness", "event_epoch", "psd_bandpower", "erp_p300"]


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "scripts/build_p0_synthetic_fixtures.py", "--out", str(FIXTURE_DIR), "--seed", "20260621"], cwd=ROOT, check=True)
    positive = {}
    failures = []
    for module_id in MODULES:
        output = EVIDENCE_DIR / f"{module_id}_validator.json"
        proc = subprocess.run(
            [sys.executable, "scripts/validate_p0_module_artifacts.py", "--module-id", module_id, "--artifact-dir", str(FIXTURE_DIR / module_id), "--output", str(output)],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        positive[module_id] = {"returncode": proc.returncode, "stdout": proc.stdout[-1000:], "stderr": proc.stderr[-1000:]}
        if proc.returncode != 0:
            failures.append(f"positive_failed:{module_id}")
    negative_dir = EVIDENCE_DIR / "negative_case_psd"
    if negative_dir.exists():
        shutil.rmtree(negative_dir)
    shutil.copytree(FIXTURE_DIR / "psd_bandpower", negative_dir)
    result_path = negative_dir / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result.pop("data_preparation_plan_id", None)
    result["frequency_range_hz"] = [1.0, 150.0]
    result["interpretation"] = "This source localization diagnosis is significant."
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    band = negative_dir / "tables" / "band_power.csv"
    band.write_text("band,value,unit\nalpha,1.0,\n", encoding="utf-8")
    negative_output = EVIDENCE_DIR / "negative_case_psd_validator.json"
    negative_proc = subprocess.run(
        [sys.executable, "scripts/validate_p0_module_artifacts.py", "--module-id", "psd_bandpower", "--artifact-dir", str(negative_dir), "--output", str(negative_output)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if negative_proc.returncode == 0:
        failures.append("negative_case_unexpected_pass")
    payload = {
        "status": "passed" if not failures else "failed",
        "created_at": datetime.now(UTC).isoformat(),
        "fixture_dir": str(FIXTURE_DIR),
        "evidence_dir": str(EVIDENCE_DIR),
        "positive": positive,
        "negative": {"returncode": negative_proc.returncode, "stdout": negative_proc.stdout[-1500:], "stderr": negative_proc.stderr[-1000:]},
        "failures": failures,
    }
    out = EVIDENCE_DIR / "acceptance_p0_fixture_validator_contract.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
