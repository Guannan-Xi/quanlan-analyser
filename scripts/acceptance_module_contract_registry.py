from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "work" / "release_evidence" / "20260621-module-contract-registry" / "acceptance_module_contract_registry.json"


def main() -> int:
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from backend.services.module_contract_service import load_module_contract_registry
    from backend.services.task_service import WORKFLOW_TEMPLATES

    registry = load_module_contract_registry()
    required_contracts = [
        "preprocessing_readiness",
        "event_epoch",
        "psd_bandpower",
        "erp_p300",
        "tfr_ersp_itc",
        "pac_cfc",
        "reference_csd",
        "multitaper_psd_tfr",
        "sensor_topography",
        "connectivity_sensor_method_design",
        "source_localization_boundary",
    ]
    required_workflows = [
        "preprocessing_readiness",
        "event_epoch_prepare",
        "resting_psd",
        "erp_p300",
        "tfr_ersp_itc",
        "pac_cfc",
        "reference_csd",
        "multitaper_psd_tfr",
        "sensor_topography",
        "connectivity",
        "source_localization_boundary",
    ]
    failures: list[str] = []

    for contract_id in required_contracts:
        contract = registry.get(contract_id)
        if not contract or contract.get("contract_status") != "loaded":
            failures.append(f"contract_not_loaded:{contract_id}")
            continue
        missing = [key for key, present in contract.get("required_keys_present", {}).items() if not present]
        if missing:
            failures.append(f"contract_missing_keys:{contract_id}:{','.join(missing)}")
        if not contract.get("non_medical_boundary_present"):
            failures.append(f"contract_missing_non_medical_boundary:{contract_id}")

    templates_by_id = {template["id"]: template for template in WORKFLOW_TEMPLATES}
    for workflow_id in required_workflows:
        template = templates_by_id.get(workflow_id)
        if not template:
            failures.append(f"workflow_missing:{workflow_id}")
            continue
        contract = template.get("module_contract") or {}
        if contract.get("contract_status") != "loaded":
            failures.append(f"workflow_contract_not_loaded:{workflow_id}")

    beta_workflows = {
        "tfr_ersp_itc": "beta",
        "multitaper_psd_tfr": "beta",
    }
    for workflow_id, expected_lifecycle in beta_workflows.items():
        contract = templates_by_id[workflow_id]["module_contract"]
        if contract.get("lifecycle_state") != expected_lifecycle:
            failures.append(f"beta_lifecycle_mismatch:{workflow_id}:{contract.get('lifecycle_state')}")
        if workflow_id == "tfr_ersp_itc":
            if templates_by_id[workflow_id].get("enabled") is not True:
                failures.append(f"beta_workflow_not_enabled:{workflow_id}")
        else:
            if templates_by_id[workflow_id].get("enabled") is not True:
                failures.append(f"beta_workflow_not_enabled:{workflow_id}")

    reference_csd = templates_by_id["reference_csd"]
    if reference_csd["module_contract"].get("lifecycle_state") != "beta":
        failures.append(f"reference_csd_lifecycle_mismatch:{reference_csd['module_contract'].get('lifecycle_state')}")
    if reference_csd.get("enabled") is not True:
        failures.append("reference_csd_runner_not_enabled")

    draft_workflows = {
        "sensor_topography": "draft",
        "source_localization_boundary": "draft",
    }
    for workflow_id, expected_lifecycle in draft_workflows.items():
        contract = templates_by_id[workflow_id]["module_contract"]
        if contract.get("lifecycle_state") != expected_lifecycle:
            failures.append(f"draft_lifecycle_mismatch:{workflow_id}:{contract.get('lifecycle_state')}")
        if templates_by_id[workflow_id].get("enabled") is not False:
            failures.append(f"draft_workflow_enabled_without_runner:{workflow_id}")

    connectivity = templates_by_id["connectivity"]
    if connectivity["module_contract"].get("lifecycle_state") not in {"draft", "beta"}:
        failures.append(f"connectivity_lifecycle_unexpected:{connectivity['module_contract'].get('lifecycle_state')}")
    if connectivity.get("enabled") is not True:
        failures.append("connectivity_runner_not_enabled")

    pac = templates_by_id["pac_cfc"]
    if pac["module_contract"].get("lifecycle_state") != "beta":
        failures.append(f"pac_lifecycle_mismatch:{pac['module_contract'].get('lifecycle_state')}")
    if pac.get("enabled") is not True:
        failures.append("pac_runner_not_enabled")

    stable_targets = {
        "preprocessing_readiness",
        "event_epoch",
        "psd_bandpower",
        "erp_p300",
    }
    for contract_id in stable_targets:
        contract = registry[contract_id]
        if contract.get("lifecycle_state") != "internal_validation":
            failures.append(f"stable_target_lifecycle_not_internal_validation:{contract_id}")
        if contract.get("promotion_target") != "stable":
            failures.append(f"stable_target_missing_promotion_target:{contract_id}")

    payload = {
        "status": "passed" if not failures else "failed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registry_count": len(registry),
        "workflow_count": len(WORKFLOW_TEMPLATES),
        "required_contracts": required_contracts,
        "required_workflows": required_workflows,
        "failures": failures,
        "workflow_contracts": {
            workflow_id: {
                "module": templates_by_id[workflow_id].get("module"),
                "production_status": templates_by_id[workflow_id].get("production_status"),
                "enabled": templates_by_id[workflow_id].get("enabled"),
                "contract": templates_by_id[workflow_id].get("module_contract"),
            }
            for workflow_id in required_workflows
            if workflow_id in templates_by_id
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
