from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "work" / "fixtures" / "pac_beta"
EVIDENCE_DIR = ROOT / "work" / "release_evidence" / "pac_beta"
ACCEPTANCE_PATH = EVIDENCE_DIR / "acceptance_pac_beta_contract.json"


def run(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
    }


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[dict] = []
    warnings: list[dict] = []
    results: dict[str, dict] = {}
    product_blockers: list[dict] = []
    method_sanity: dict = {"positive_vs_control_mi_relation": "not_checked"}

    manifest_path = FIXTURE_DIR / "fixture_manifest.json"
    if not manifest_path.exists():
        results["fixture_builder"] = run([sys.executable, "scripts\\build_pac_beta_synthetic_fixture.py", "--out", str(FIXTURE_DIR), "--seed", "20260621"])
        if results["fixture_builder"]["returncode"] != 0:
            failures.append({"code": "FIXTURE_BUILDER_FAILED", "detail": results["fixture_builder"]})
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    required_cases = ["positive_known_pac", "no_coupling_control", "short_window_blocker", "nyquist_blocker_metadata"]
    for case in required_cases:
        if case not in (manifest.get("cases") or {}):
            failures.append({"code": "FIXTURE_CASE_MISSING", "detail": case})

    positive_zip = FIXTURE_DIR / "positive_known_pac" / "pac_beta_artifact_bundle.zip"
    control_zip = FIXTURE_DIR / "no_coupling_control" / "pac_beta_artifact_bundle.zip"
    positive_dir = FIXTURE_DIR / "positive_known_pac" / "artifact_bundle"
    negative_missing = FIXTURE_DIR / "negative_missing_plan" / "artifact_bundle"
    negative_forbidden = FIXTURE_DIR / "negative_forbidden_claim" / "artifact_bundle"

    validation_targets = {
        "positive_zip": (positive_zip, True),
        "control_zip": (control_zip, True),
        "positive_dir": (positive_dir, True),
        "negative_missing_plan": (negative_missing, False),
        "negative_forbidden_claim": (negative_forbidden, False),
    }
    for name, (target, should_pass) in validation_targets.items():
        if not target.exists():
            failures.append({"code": "VALIDATION_TARGET_MISSING", "detail": f"{name}: {target}"})
            continue
        out_path = EVIDENCE_DIR / f"{name}_validator.json"
        result = run([sys.executable, "scripts\\validate_pac_beta_artifacts.py", str(target), "--out", str(out_path)])
        results[name] = result
        if should_pass and result["returncode"] != 0:
            failures.append({"code": "POSITIVE_VALIDATOR_FAILED", "detail": name})
        if not should_pass and result["returncode"] == 0:
            failures.append({"code": "NEGATIVE_VALIDATOR_DID_NOT_FAIL", "detail": name})

    if manifest:
        pos_peak = float(manifest["cases"]["positive_known_pac"].get("peak_mi", 0))
        control_peak = float(manifest["cases"]["no_coupling_control"].get("peak_mi", 0))
        method_sanity = {
            "positive_known_pac_peak_mi": pos_peak,
            "no_coupling_control_peak_mi": control_peak,
            "positive_vs_control_mi_relation": "pass" if pos_peak > control_peak else "fail",
            "boundary": "Synthetic method sanity only; this is not biological PAC evidence or statistical significance.",
        }
        if pos_peak <= control_peak:
            failures.append({"code": "POSITIVE_CONTROL_RELATION_FAILED", "detail": f"positive={pos_peak}, control={control_peak}"})
        if manifest.get("privacy_status") != "synthetic_only_no_real_participant_customer_or_phi":
            failures.append({"code": "PRIVACY_STATUS_INVALID", "detail": str(manifest.get("privacy_status"))})

    ui_evidence_path = EVIDENCE_DIR / "pac-beta-ui-only-runner-evidence.json"
    if ui_evidence_path.exists():
        ui = json.loads(ui_evidence_path.read_text(encoding="utf-8"))
        if ui.get("protocol") != "QLANALYSER_PAC_BETA_UI_ONLY_RUNNER":
            failures.append({"code": "UI_RUNNER_PROTOCOL_INVALID", "detail": str(ui.get("protocol"))})
        if ui.get("no_direct_api_mutation") is not True:
            failures.append({"code": "UI_ONLY_POLICY_MISSING", "detail": "no_direct_api_mutation must be true"})
        if ui.get("verdict") == "error":
            failures.append({"code": "UI_RUNNER_ERROR", "detail": ui.get("error", "")})
        if ui.get("verdict") != "pass":
            product_blockers.append({"code": "PAC_UI_RUNNER_NOT_PASS", "detail": f"PAC UI-only runner verdict={ui.get('verdict')}"})
        missing_selectors = [item.get("selector") for item in ui.get("selectors", []) if item.get("visible") is not True]
        if missing_selectors:
            product_blockers.append({"code": "PAC_REQUIRED_SELECTORS_MISSING", "detail": missing_selectors})
        for download in ui.get("downloads", []):
            if "current product UI does not expose" in str(download.get("via", "")):
                product_blockers.append({"code": "PAC_DOWNLOAD_NOT_UI_EXPOSED", "detail": download.get("via")})
        if not ui.get("product_gaps"):
            warnings.append({"code": "WARN_NO_PAC_UI_GAP_RECORDED", "detail": "Current product may already expose PAC selectors; verify manually."})
    else:
        warnings.append({"code": "WARN_UI_RUNNER_NOT_RUN", "detail": str(ui_evidence_path)})
        product_blockers.append({"code": "PAC_UI_RUNNER_EVIDENCE_MISSING", "detail": str(ui_evidence_path)})

    output = {
        "schema_version": "qlanalyser-pac-beta-acceptance-v0.1",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not failures else "failed",
        "product_gate_status": "blocked" if product_blockers else "not_blocked_by_this_contract",
        "product_blockers": product_blockers,
        "method_sanity": method_sanity,
        "important_boundary": "This validates PAC beta fixture and artifact-validator contracts. It is not PAC product UI pass, stable promotion, release pass, clinical evidence, or statistical significance.",
        "manifest_path": str(manifest_path),
        "ui_evidence_path": str(ui_evidence_path),
        "failures": failures,
        "warnings": warnings,
        "results": results,
    }
    ACCEPTANCE_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
