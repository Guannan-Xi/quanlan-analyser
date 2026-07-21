from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "modules" / "analysis_module_contract.md"
TASK_SERVICE = ROOT / "backend" / "services" / "task_service.py"
OUTPUT = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_analysis_workflow_framework.json"


CONTRACT_PHRASES = [
    "Total Workflow Integration Contract",
    "not a collection of isolated side pages",
    "workflow template",
    "task schema",
    "task_service routing",
    "artifact manifest",
    "report mapping",
    "release evidence matrix",
    "Lab and beta pages may be used to validate a method",
    "not the long-term product home for stable methods",
    "reachable from the main customer analysis flow or a governed preset workflow",
    "must not bypass `/api/tasks`",
]

TASK_SERVICE_PHRASES = [
    "WORKFLOW_TEMPLATES",
    '"id": "metadata_qc"',
    '"id": "resting_psd"',
    '"id": "erp_p300"',
    '"id": "event_epoch_prepare"',
    '"production_status": "v01_required"',
    '"production_status": "v01_required_when_events_exist"',
    '"production_status": "internal_validation_contract_loaded"',
    "run_quality_check",
    "run_psd",
    "run_erp_p300",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    contract = CONTRACT.read_text(encoding="utf-8") if CONTRACT.exists() else ""
    task_service = TASK_SERVICE.read_text(encoding="utf-8") if TASK_SERVICE.exists() else ""
    missing_contract_phrases = [phrase for phrase in CONTRACT_PHRASES if phrase not in contract]
    missing_task_service_phrases = [phrase for phrase in TASK_SERVICE_PHRASES if phrase not in task_service]
    payload = {
        "status": "passed"
        if CONTRACT.exists()
        and TASK_SERVICE.exists()
        and not missing_contract_phrases
        and not missing_task_service_phrases
        else "failed",
        "generated_at": utc_now(),
        "contract": str(CONTRACT),
        "task_service": str(TASK_SERVICE),
        "checks": {
            "contract_exists": CONTRACT.exists(),
            "task_service_exists": TASK_SERVICE.exists(),
            "workflow_integration_contract": not missing_contract_phrases,
            "workflow_templates_present": not missing_task_service_phrases,
        },
        "missing_contract_phrases": missing_contract_phrases,
        "missing_task_service_phrases": missing_task_service_phrases,
        "policy": "Stable analysis methods must mount into the total analysis workflow via workflow templates, /api/tasks, artifacts, reports, audit, and evidence gates.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
