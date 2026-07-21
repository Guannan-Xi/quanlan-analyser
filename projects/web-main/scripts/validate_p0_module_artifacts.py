from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


P0_MODULES = {"preprocessing_readiness", "event_epoch", "psd_bandpower", "erp_p300"}
FORBIDDEN = re.compile(r"\b(diagnosis|diagnostic|treatment|significant|p-value|source localization|brain activation|脑源|诊断|显著|脑区激活)\b", re.IGNORECASE)
SAFE_NEGATED_BOUNDARY = re.compile(
    r"\b(not\s+for\s+clinical\s+diagnosis|not\s+for\s+.*treatment\s+decisions|no\s+clinical\s+diagnosis|non[- ]diagnostic)\b",
    re.IGNORECASE,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate P0 module fixture/artifact directories.")
    parser.add_argument("--module-id", required=True, choices=sorted(P0_MODULES))
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = validate(args.module_id, Path(args.artifact_dir))
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    raise SystemExit(0 if result["verdict"] == "pass" else 1)


def validate(module_id: str, artifact_dir: Path) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    missing: list[str] = []
    checks: dict[str, Any] = {}
    if module_id not in P0_MODULES:
        failures.append(f"UNSUPPORTED_MODULE:{module_id}")
    result = _read_json(artifact_dir / "result.json", missing, "result.json")
    checks["result_json_present"] = bool(result)
    for rel in ["manifest.json", "reproducibility/workflow.json", "reproducibility/software_versions.json"]:
        _require_file(artifact_dir / rel, missing, rel)
    if result:
        _require_field(result, "data_preparation_plan_id", failures)
        _require_field(result, "parameters_hash", failures)
        if module_id in {"event_epoch", "erp_p300"}:
            _require_field(result, "epoch_set_id", failures)
        if "non_diagnostic_boundary" not in result:
            failures.append("MISSING_FIELD:non_diagnostic_boundary")
    if module_id == "psd_bandpower":
        _validate_psd(artifact_dir, result, failures, missing, checks)
    if module_id == "event_epoch":
        _require_file(artifact_dir / "tables/events.csv", missing, "tables/events.csv")
        _require_file(artifact_dir / "reproducibility/epoch_set_manifest.json", missing, "reproducibility/epoch_set_manifest.json")
    if module_id == "erp_p300":
        _require_file(artifact_dir / "tables/erp_metrics.csv", missing, "tables/erp_metrics.csv")
        _require_file(artifact_dir / "reproducibility/epoch_set_manifest.json", missing, "reproducibility/epoch_set_manifest.json")
    boundary_scan = _scan_boundary_text(artifact_dir)
    if boundary_scan["findings"]:
        failures.append("FORBIDDEN_BOUNDARY_LANGUAGE_FOUND")
    if missing:
        failures.append("MISSING_REQUIRED_FILES")
    return {
        "module_id": module_id,
        "artifact_dir": str(artifact_dir),
        "verdict": "pass" if not failures else "revise",
        "checks": checks,
        "failures": failures,
        "warnings": warnings,
        "missing_files": missing,
        "boundary_scan": boundary_scan,
        "created_at": datetime.now(UTC).isoformat(),
    }


def _validate_psd(artifact_dir: Path, result: dict[str, Any], failures: list[str], missing: list[str], checks: dict[str, Any]) -> None:
    band_power = artifact_dir / "tables/band_power.csv"
    _require_file(band_power, missing, "tables/band_power.csv")
    if band_power.exists():
        with band_power.open("r", newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        checks["psd_rows"] = len(rows)
        if not rows or not all(row.get("unit") for row in rows):
            failures.append("PSD_UNIT_MISSING")
    if result:
        fmax = (result.get("frequency_range_hz") or [None, None])[1]
        nyquist = result.get("nyquist_hz")
        checks["psd_nyquist"] = {"fmax": fmax, "nyquist_hz": nyquist}
        if fmax is not None and nyquist is not None and float(fmax) >= float(nyquist):
            failures.append("PSD_NYQUIST_VIOLATION")


def _scan_boundary_text(artifact_dir: Path) -> dict[str, Any]:
    findings = []
    for path in artifact_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".csv", ".txt", ".md"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in FORBIDDEN.finditer(text):
                context_start = max(0, match.start() - 80)
                context_end = min(len(text), match.end() + 80)
                context = text[context_start:context_end]
                if SAFE_NEGATED_BOUNDARY.search(context):
                    continue
                findings.append({"path": str(path.relative_to(artifact_dir)).replace("\\", "/"), "match": match.group(0)})
    return {"patterns": ["diagnosis", "treatment", "significant", "p-value", "source localization", "brain activation"], "findings": findings}


def _read_json(path: Path, missing: list[str], label: str) -> dict[str, Any]:
    if not path.exists():
        missing.append(label)
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _require_file(path: Path, missing: list[str], label: str) -> None:
    if not path.exists():
        missing.append(label)


def _require_field(payload: dict[str, Any], field: str, failures: list[str]) -> None:
    if not payload.get(field):
        failures.append(f"MISSING_FIELD:{field}")


if __name__ == "__main__":
    main()
