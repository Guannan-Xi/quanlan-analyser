from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOTYPE_ROOT = Path(
    r"C:\Users\XGN\Documents\Codex\2026-06-19\new-chat-2\outputs\prototypes\real_eeg_v01"
)
OUT = (
    ROOT
    / "work"
    / "release_evidence"
    / "mainline_eeg_review"
    / "mainline_eeg_review_bridge_acceptance.json"
)

REQUIRED_MODULES = {"psd", "erp", "tfr", "pac"}
FORBIDDEN_SCOPE = {"Connectivity", "Source localization", "CSD"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_checkpoint(prototype_root: Path) -> Path:
    candidates = sorted(
        prototype_root.glob("07a_mainline_eeg_review_checkpoint_*.json"),
        key=lambda path: path.stat().st_mtime,
    )
    if not candidates:
        raise FileNotFoundError(f"no 07A mainline EEG checkpoint found in {prototype_root}")
    return candidates[-1]


def require_path(path: Path, failures: list[str], label: str) -> None:
    if not path.exists():
        failures.append(f"missing {label}: {path}")


def validate_review_access(checkpoint: dict[str, Any], failures: list[str]) -> None:
    access = checkpoint.get("review_access") or checkpoint.get("REVIEW_ACCESS") or {}
    if not isinstance(access, dict):
        failures.append("review_access missing or invalid")
        return
    required = [
        "front_end_url",
        "backend_health_url",
        "test_account",
        "test_password_or_login_method",
        "permission_scope",
        "if_no_account_needed_why",
        "credential_safety",
    ]
    for key in required:
        if not str(access.get(key, "")).strip():
            failures.append(f"review_access missing {key}")
    safety = str(access.get("credential_safety", "")).lower()
    if "no_production_secret" not in safety:
        failures.append("credential_safety must include no_production_secret or equivalent")


def screenshot_records(checkpoint: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = checkpoint.get("evidence_artifacts") or {}
    records = artifacts.get("screenshots") or []
    return records if isinstance(records, list) else []


def validate_checkpoint(
    checkpoint_path: Path,
    virtual_report_path: Path,
    artifact_report_path: Path,
) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    checkpoint = load_json(checkpoint_path)
    virtual_report = load_json(virtual_report_path)
    artifact_report = load_json(artifact_report_path)

    validate_review_access(checkpoint, failures)

    if checkpoint.get("final_marker") != "QLANALYSER_MAINLINE_REVIEW_READY":
        failures.append("checkpoint final_marker is not QLANALYSER_MAINLINE_REVIEW_READY")

    recommendation = (checkpoint.get("decision_for_07") or {}).get("07a_recommendation")
    if recommendation != "CONDITIONAL PASS for entering mainline integration review":
        failures.append("07A recommendation must be CONDITIONAL PASS for integration review")

    excluded = set(checkpoint.get("excluded_scope") or [])
    missing_exclusions = sorted(FORBIDDEN_SCOPE - excluded)
    if missing_exclusions:
        failures.append(f"excluded_scope missing boundary items: {missing_exclusions}")

    users = virtual_report.get("users") or []
    unsatisfied = [item.get("user") for item in users if item.get("status") != "satisfied"]
    if len(users) < 5:
        failures.append(f"expected at least 5 UI-only personas, found {len(users)}")
    if unsatisfied:
        failures.append(f"unsatisfied UI-only personas: {unsatisfied}")

    modules = artifact_report.get("modules") or []
    module_by_id = {item.get("module"): item for item in modules}
    missing_modules = sorted(REQUIRED_MODULES - set(module_by_id))
    if missing_modules:
        failures.append(f"artifact report missing modules: {missing_modules}")
    if artifact_report.get("overall") != "pass":
        failures.append("artifact contract overall is not pass")
    for module_id, item in module_by_id.items():
        if module_id in REQUIRED_MODULES:
            if item.get("status") != "pass":
                failures.append(f"{module_id} status is not pass")
            if item.get("missing"):
                failures.append(f"{module_id} has missing artifacts: {item.get('missing')}")
            if item.get("manifest_ok") is not True:
                failures.append(f"{module_id} manifest_ok is not true")

    screenshots = screenshot_records(checkpoint)
    if len(screenshots) < 5:
        failures.append(f"expected screenshot evidence, found {len(screenshots)} records")
    missing_screenshots: list[str] = []
    for record in screenshots:
        path = Path(str(record.get("path", "")))
        if not path.exists() or path.stat().st_size <= 0:
            missing_screenshots.append(str(path))
    if missing_screenshots:
        failures.append(f"missing or empty screenshots: {missing_screenshots}")

    summary = {
        "checkpoint_path": str(checkpoint_path),
        "virtual_user_acceptance_report": str(virtual_report_path),
        "mainline_acceptance_check_report": str(artifact_report_path),
        "ui_only_personas": len(users),
        "screenshot_count": len(screenshots),
        "modules": {
            module_id: {
                "status": module_by_id.get(module_id, {}).get("status"),
                "manifest_ok": module_by_id.get(module_id, {}).get("manifest_ok"),
                "missing_count": len(module_by_id.get(module_id, {}).get("missing") or []),
                "run_dir": module_by_id.get(module_id, {}).get("run_dir"),
            }
            for module_id in sorted(REQUIRED_MODULES)
        },
        "review_access": checkpoint.get("review_access") or checkpoint.get("REVIEW_ACCESS"),
        "recommendation": recommendation,
    }
    return failures, summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bridge the real_eeg_v01 mainline EEG prototype review checkpoint into main repo evidence."
    )
    parser.add_argument("--prototype-root", type=Path, default=DEFAULT_PROTOTYPE_ROOT)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--virtual-report", type=Path)
    parser.add_argument("--artifact-report", type=Path)
    args = parser.parse_args()

    prototype_root = args.prototype_root
    checkpoint_path = args.checkpoint or latest_checkpoint(prototype_root)
    virtual_report_path = args.virtual_report or prototype_root / "virtual_user_acceptance_report.json"
    artifact_report_path = args.artifact_report or prototype_root / "mainline_acceptance_check_report.json"

    failures: list[str] = []
    for path, label in [
        (checkpoint_path, "checkpoint"),
        (virtual_report_path, "virtual user report"),
        (artifact_report_path, "artifact contract report"),
    ]:
        require_path(path, failures, label)

    summary: dict[str, Any] = {}
    if not failures:
        try:
            failures, summary = validate_checkpoint(
                checkpoint_path=checkpoint_path,
                virtual_report_path=virtual_report_path,
                artifact_report_path=artifact_report_path,
            )
        except Exception as exc:  # pragma: no cover - CLI evidence should include exact error text.
            failures = [f"validation exception: {type(exc).__name__}: {exc}"]

    result = {
        "status": "passed" if not failures else "failed",
        "product_gate": "integration_review_evidence_only_not_release_pass",
        "scope": "QC/PSD/ERP/TFR/PAC mainline EEG prototype review bridge",
        "failures": failures,
        "summary": summary,
        "07A_SHORT_PACKET_METRICS": {
            "mini_script_packet_count": 1,
            "script_packet_used": "mainline EEG review bridge acceptance",
            "GPT_5_5_low_value_work_avoided": "checkpoint path lookup, JSON field checks, screenshot existence checks, module contract counting",
            "concurrency_frontier": "single deterministic bridge gate; no worker wave needed",
            "long_term_platform_asset_produced": "main repo acceptance gate for external mainline EEG prototype review packets",
            "owner_boundary_respected": "yes",
            "handoff_target": "07 main owner",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
