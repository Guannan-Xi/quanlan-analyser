from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs" / "product" / "stage_gated_development_review_system.md"
CONTRACT = ROOT / "docs" / "product" / "stage_gated_review_contract.json"
OUT = ROOT / "work" / "release_evidence" / "stage_gated_review_policy" / "acceptance_stage_gated_review_policy.json"

REQUIRED_GATES = [
    "route_gate",
    "requirement_gate",
    "design_gate",
    "implementation_gate",
    "unit_static_gate",
    "integration_gate",
    "ui_interaction_gate",
    "real_user_path_gate",
    "artifact_report_gate",
    "checkpoint_access_gate",
    "release_decision_gate",
]

REQUIRED_ENVIRONMENTS = [
    "product_docs",
    "frontend_ui",
    "backend_api",
    "runner_worker",
    "artifact_report",
    "review_checkpoint",
    "release_deploy",
]

REQUIRED_ENVIRONMENT_GATES = [
    "development_workspace",
    "frontend_ui_e2e",
    "backend_api_runner",
    "runner_artifact_report",
    "release_gate",
    "checkpoint_review_access",
    "docs_living_system",
    "cross_department_handoff",
]

REQUIRED_ENVIRONMENT_GATE_FIELDS = [
    "environment_id",
    "entry",
    "gate",
    "command_or_entry",
    "blocking_rules",
    "evidence_path",
    "owner",
    "consumer",
]

REQUIRED_ROUTE = [
    "route_decision",
    "execution_packet",
    "executor_evidence",
    "gpt55_acceptance",
    "final_receipt",
    "next_real_artifact",
]


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    issues: list[dict[str, object]] = []
    policy_text = POLICY.read_text(encoding="utf-8") if POLICY.exists() else ""
    contract = json.loads(CONTRACT.read_text(encoding="utf-8")) if CONTRACT.exists() else {}

    if not POLICY.exists():
        issues.append({"issue": "missing_policy_doc", "path": str(POLICY)})
    if not CONTRACT.exists():
        issues.append({"issue": "missing_contract_json", "path": str(CONTRACT)})

    for gate in REQUIRED_GATES:
        if gate not in policy_text:
            issues.append({"issue": "policy_missing_gate", "gate": gate})
        if gate not in (contract.get("gates") or {}):
            issues.append({"issue": "contract_missing_gate", "gate": gate})

    for env in REQUIRED_ENVIRONMENTS:
        if env not in policy_text:
            issues.append({"issue": "policy_missing_environment", "environment": env})
        if env not in (contract.get("environment_coverage") or {}):
            issues.append({"issue": "contract_missing_environment", "environment": env})

    route_chain = contract.get("route_chain") or []
    for item in REQUIRED_ROUTE:
        if item not in route_chain:
            issues.append({"issue": "contract_missing_route_item", "item": item})
        if item not in policy_text:
            issues.append({"issue": "policy_missing_receipt_item", "item": item})

    forbidden = contract.get("forbidden") or []
    if not any("advance_without_prior_gate_pass" in item for item in forbidden):
        issues.append({"issue": "missing_no_skip_forbidden_rule"})
    if "Executor Bus" not in policy_text or "allowlisted" not in policy_text:
        issues.append({"issue": "missing_executor_bus_allowlist_boundary"})
    if not contract.get("all_environments_review_required"):
        issues.append({"issue": "missing_all_environments_review_required"})

    environment_gates = contract.get("environment_gates") or []
    environment_gate_ids = {
        item.get("environment_id")
        for item in environment_gates
        if isinstance(item, dict)
    }
    for env in REQUIRED_ENVIRONMENT_GATES:
        if env not in policy_text:
            issues.append({"issue": "policy_missing_canonical_environment_gate", "environment": env})
        if env not in environment_gate_ids:
            issues.append({"issue": "contract_missing_canonical_environment_gate", "environment": env})
    for item in environment_gates:
        if not isinstance(item, dict):
            issues.append({"issue": "environment_gate_record_not_object"})
            continue
        missing_fields = [
            field for field in REQUIRED_ENVIRONMENT_GATE_FIELDS
            if not item.get(field)
        ]
        if missing_fields:
            issues.append({
                "issue": "environment_gate_missing_fields",
                "environment": item.get("environment_id"),
                "fields": missing_fields,
            })

    report = {
        "requirement_id": "QLANALYSER_STAGE_GATED_DEVELOPMENT_REVIEW_POLICY",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not issues else "failed",
        "policy_path": str(POLICY),
        "contract_path": str(CONTRACT),
        "required_gates": REQUIRED_GATES,
        "required_environments": REQUIRED_ENVIRONMENTS,
        "required_environment_gates": REQUIRED_ENVIRONMENT_GATES,
        "required_route": REQUIRED_ROUTE,
        "issues": issues,
        "acceptance": {
            "every_stage_has_gate": not any(
                item.get("issue") in {"policy_missing_gate", "contract_missing_gate"} for item in issues
            ),
            "every_environment_has_coverage": not any(
                item.get("issue") in {"policy_missing_environment", "contract_missing_environment"} for item in issues
            ),
            "canonical_environment_gates_complete": not any(
                item.get("issue") in {
                    "missing_all_environments_review_required",
                    "policy_missing_canonical_environment_gate",
                    "contract_missing_canonical_environment_gate",
                    "environment_gate_record_not_object",
                    "environment_gate_missing_fields",
                }
                for item in issues
            ),
            "qgcs_receipt_required": not any(
                str(item.get("issue", "")).startswith("contract_missing_route")
                or str(item.get("issue", "")).startswith("policy_missing_receipt")
                for item in issues
            ),
            "executor_bus_boundary_present": not any(
                item.get("issue") == "missing_executor_bus_allowlist_boundary" for item in issues
            ),
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
