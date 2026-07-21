from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "product" / "stage_gated_review_contract.json"
OUT_DIR = ROOT / "work" / "release_evidence" / "review_system_all_environments"
OUT_JSON = OUT_DIR / "review_system_all_environments.json"

REQUIRED_ENVIRONMENTS = {
    "development_workspace",
    "frontend_ui_e2e",
    "backend_api_runner",
    "runner_artifact_report",
    "release_gate",
    "checkpoint_review_access",
    "docs_living_system",
    "cross_department_handoff",
}

REQUIRED_FIELDS = {
    "environment_id",
    "entry",
    "gate",
    "command_or_entry",
    "blocking_rules",
    "evidence_path",
    "owner",
    "consumer",
}

REQUIRED_PRE_SUBMISSION_COMMANDS = {
    "node scripts/acceptance_edf_upload_to_results_ui_only.mjs",
    "node scripts/acceptance_workflow_pages_ui_gate.mjs",
}

REQUIRED_PRE_SUBMISSION_BLOCKERS = {
    "e2e_status_not_passed",
    "page_visual_review_missing",
    "checkpoint_created_without_fresh_e2e_and_visual_evidence",
}


def exists_from_root(value: str) -> bool:
    if value.startswith("http://") or value.startswith("https://"):
        return True
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    if path == OUT_JSON:
        return True
    return path.exists()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    issues: list[dict[str, Any]] = []
    if not CONTRACT.exists():
        issues.append({"issue": "missing_contract", "path": str(CONTRACT)})
        environments: list[dict[str, Any]] = []
    else:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        environments = contract.get("environment_gates") or contract.get("all_environment_gates") or []
        if not contract.get("all_environments_review_required"):
            issues.append({"issue": "missing_all_environments_review_required"})
        pre_submission_gate = contract.get("pre_submission_quality_gate") or {}
        applies_before = set(pre_submission_gate.get("applies_before") or [])
        required_applies = {"acceptance_submission", "checkpoint_packet", "review_artifact", "release_gate_final_receipt"}
        if not required_applies.issubset(applies_before):
            issues.append({
                "issue": "pre_submission_gate_missing_apply_targets",
                "missing": sorted(required_applies - applies_before),
            })
        commands = set(pre_submission_gate.get("required_commands") or [])
        missing_commands = sorted(REQUIRED_PRE_SUBMISSION_COMMANDS - commands)
        if missing_commands:
            issues.append({"issue": "pre_submission_gate_missing_commands", "missing": missing_commands})
        blockers = set(pre_submission_gate.get("blocking_rules") or [])
        missing_blockers = sorted(REQUIRED_PRE_SUBMISSION_BLOCKERS - blockers)
        if missing_blockers:
            issues.append({"issue": "pre_submission_gate_missing_blockers", "missing": missing_blockers})
        if not isinstance(environments, list):
            issues.append({"issue": "environment_gates_not_list"})
            environments = []

    env_by_id = {env.get("environment_id"): env for env in environments if isinstance(env, dict)}
    missing = sorted(REQUIRED_ENVIRONMENTS - set(env_by_id))
    for env_id in missing:
        issues.append({"issue": "missing_environment_gate", "environment_id": env_id})

    for env_id, env in sorted(env_by_id.items()):
        missing_fields = sorted(field for field in REQUIRED_FIELDS if not env.get(field))
        if missing_fields:
            issues.append({"issue": "missing_environment_fields", "environment_id": env_id, "fields": missing_fields})
        blocking_rules = env.get("blocking_rules")
        if not isinstance(blocking_rules, list) or not blocking_rules:
            issues.append({"issue": "missing_blocking_rules", "environment_id": env_id})
        evidence_path = env.get("evidence_path")
        if evidence_path and not exists_from_root(str(evidence_path)):
            issues.append({"issue": "evidence_path_not_found", "environment_id": env_id, "evidence_path": evidence_path})
        if env.get("gate") and not isinstance(env.get("gate"), str):
            issues.append({"issue": "gate_not_string", "environment_id": env_id})

    report = {
        "status": "passed" if not issues else "failed",
        "generated_at": datetime.now(UTC).isoformat(),
        "contract_path": str(CONTRACT),
        "evidence_path": str(OUT_JSON),
        "required_environments": sorted(REQUIRED_ENVIRONMENTS),
        "covered_environments": sorted(env_by_id),
        "missing_environments": missing,
        "issues": issues,
        "acceptance": {
            "review_system_integrated_only_if_passed": True,
            "no_environment_can_pass_by_prose_only": True,
            "must_include_gate_command_blocking_rule_and_evidence": True,
            "pre_submission_requires_fresh_e2e_and_page_visual_review": True,
        },
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
