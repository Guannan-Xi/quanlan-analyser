from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "compliance" / "cro_traceability_contract.md"
MODULE_CONTRACT = ROOT / "docs" / "modules" / "analysis_module_contract.md"
STATUS = ROOT / "docs" / "PROJECT_STATUS_CURRENT.md"
OUTPUT = (
    ROOT
    / "work"
    / "release_evidence"
    / "20260620-v01-acceptance"
    / "acceptance_cro_traceability_contract.json"
)


REQUIRED_CONTRACT_PHRASES = [
    "research EEG analysis tool and CRO infrastructure",
    "not a claim of GxP, medical, or regulatory certification",
    "Who did what, when, with which source data",
    "Minimum V1 Trace Objects",
    "Audit Event Contract",
    "Data Integrity Principles",
    "Review and Approval Ladder",
    "Report Package Traceability",
    "Role Boundary",
    "Evidence Matrix",
    "scripts/acceptance_audit_quota_contract.py",
    "scripts/acceptance_ops_billing_invoice.py",
    "scripts/acceptance_report_zip_contract.py",
    "scripts/acceptance_analysis_module_contract.py",
    "Formal CRO/GxP validation remains a future controlled-validation activity.",
]

REQUIRED_MODEL_FIELDS = [
    "audit_trace_id",
    "organization_id",
    "project_id",
    "actor_user_id",
    "action",
    "object_type",
    "object_id",
    "metadata_json",
    "created_at",
]


def missing(text: str, phrases: list[str]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


def main() -> int:
    contract_text = CONTRACT.read_text(encoding="utf-8") if CONTRACT.exists() else ""
    module_text = MODULE_CONTRACT.read_text(encoding="utf-8") if MODULE_CONTRACT.exists() else ""
    status_text = STATUS.read_text(encoding="utf-8") if STATUS.exists() else ""
    governance_model = (ROOT / "backend" / "models" / "governance.py").read_text(encoding="utf-8")

    checks = {
        "contract_exists": CONTRACT.exists(),
        "module_contract_exists": MODULE_CONTRACT.exists(),
        "status_exists": STATUS.exists(),
        "contract_required_phrases": not missing(contract_text, REQUIRED_CONTRACT_PHRASES),
        "audit_model_fields": not missing(governance_model, REQUIRED_MODEL_FIELDS),
        "module_contract_has_artifact_manifest": "artifact_manifest:" in module_text,
        "status_mentions_cro": "CRO" in status_text,
    }
    payload = {
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "contract": str(CONTRACT),
        "module_contract": str(MODULE_CONTRACT),
        "status_doc": str(STATUS),
        "missing_contract_phrases": missing(contract_text, REQUIRED_CONTRACT_PHRASES),
        "missing_audit_model_fields": missing(governance_model, REQUIRED_MODEL_FIELDS),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
