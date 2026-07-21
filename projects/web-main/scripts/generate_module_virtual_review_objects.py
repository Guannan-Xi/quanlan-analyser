from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = Path(r"D:\QuanLanKnowledgeBase\learning-notes\qlanalyser\module-contracts")
OUT_DIR = ROOT / "work" / "release_evidence" / "20260621-module-review-objects"
PACK_OUT = OUT_DIR / "module_virtual_review_pack.v0.1.1-draft.json"
CHECKLIST_OUT = OUT_DIR / "module_artifact_validator_checklists.json"

REVIEWER_PANEL = [
    "beginner_eeg_user_reviewer",
    "expert_eeg_reviewer",
    "lab_pi_reviewer",
    "data_lab_engineer_reviewer",
    "scientific_boundary_reviewer",
    "ux_accessibility_reviewer",
    "artifact_validator_agent",
    "chief_arbiter",
]


def main() -> None:
    contracts = _load_contracts()
    pack = {
        "pack_id": "qlanalyser-module-contract-review-objects-v0.1.1-draft",
        "product": "QLanalyser",
        "version": "v0.1.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(CONTRACT_DIR),
        "normalization": {
            "source": "module_contract_registry",
            "status": "draft_generated_for_executable_review",
        },
        "user_signal_atoms": [],
        "experience_cases": [],
        "interaction_test_cases": [_interaction_case(index, contract) for index, contract in enumerate(contracts, start=1)],
        "fixture_requirements": [_fixture_requirement(index, contract) for index, contract in enumerate(contracts, start=1)],
        "expected_output_requirements": [_expected_output_requirement(index, contract) for index, contract in enumerate(contracts, start=1)],
        "boundaries": [
            "Generated review objects are draft acceptance targets, not product pass or release approval.",
            "V01 remains single-dataset descriptive and non-diagnostic.",
            "Beta and draft lifecycle modules must remain disabled until real runner, fixture, artifact validator, UI trace, and expert review evidence exist.",
            "Sensor-space outputs must not be described as source localization, brain-region activation, causality, information flow, diagnosis, or treatment guidance.",
        ],
    }
    checklists = {
        "generated_at": pack["created_at"],
        "source_root": str(CONTRACT_DIR),
        "module_count": len(contracts),
        "checklists": [_artifact_checklist(contract) for contract in contracts],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PACK_OUT.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    CHECKLIST_OUT.write_text(json.dumps(checklists, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pack": str(PACK_OUT), "checklists": str(CHECKLIST_OUT), "module_count": len(contracts)}, ensure_ascii=False, indent=2))


def _load_contracts() -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for path in sorted(CONTRACT_DIR.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        payload["_source_file"] = path.name
        contracts.append(payload)
    return sorted(contracts, key=lambda item: str(item.get("module_id")))


def _interaction_case(index: int, contract: dict[str, Any]) -> dict[str, Any]:
    module_id = contract["module_id"]
    lifecycle = contract.get("lifecycle_state")
    task_id = f"VR-MOD-{index:04d}"
    return {
        "task_id": task_id,
        "user_goal": f"Run or inspect the {module_id} module path from upload through report evidence without overclaiming results.",
        "preconditions": [
            "Synthetic or public-license EEG fixture is available.",
            "No real participant, customer, PHI, or sensitive clinical data is used.",
            f"Module lifecycle is {lifecycle}; UI must show this lifecycle boundary.",
        ],
        "fixture_files": [f"fixtures/{module_id}/fixture_manifest.json"],
        "steps": [
            {"step_id": f"{task_id}-S01", "action": "open", "target": "QLanalyser workbench"},
            {"step_id": f"{task_id}-S02", "action": "click", "target": "New Project or existing synthetic project"},
            {"step_id": f"{task_id}-S03", "action": "upload", "target": f"{module_id} synthetic fixture"},
            {"step_id": f"{task_id}-S04", "action": "wait", "target": "Metadata, QC, and prerequisite state"},
            {"step_id": f"{task_id}-S05", "action": "click", "target": f"{module_id} module card"},
            {"step_id": f"{task_id}-S06", "action": "screenshot", "target": "Module parameters and lifecycle boundary"},
            {"step_id": f"{task_id}-S07", "action": "download", "target": "Report or artifact bundle when enabled"},
            {"step_id": f"{task_id}-S08", "action": "artifact_inspect", "target": f"{module_id} expected output requirement"},
        ],
        "expected_ui_states": _expected_ui_states(contract),
        "expected_downloads": [f"{module_id}_review_bundle.zip"],
        "expected_warnings_or_errors": _expected_warnings(contract),
        "artifact_validators": [f"artifact_validator_checklists:{module_id}"],
        "reviewer_panel_config": REVIEWER_PANEL,
        "blocking_criteria": _blocking_criteria(contract),
    }


def _fixture_requirement(index: int, contract: dict[str, Any]) -> dict[str, Any]:
    module_id = contract["module_id"]
    lifecycle = contract.get("lifecycle_state")
    category = "valid" if lifecycle == "internal_validation" else "boundary" if lifecycle == "beta" else "scientific_misread_risk"
    return {
        "fixture_id": f"VR-FX-MOD-{index:04d}",
        "category": category,
        "fixture_subtype": f"{module_id}_synthetic_or_public_fixture",
        "format": "EEG fixture plus manifest JSON",
        "purpose": f"Exercise {module_id} module prerequisites, parameters, outputs, and boundary warnings.",
        "must_include": _fixture_must_include(contract),
        "must_not_include": [
            "Real customer data",
            "PHI or patient identifiers",
            "Clinical labels or diagnosis fields",
            "Private local absolute paths in reusable artifacts",
        ],
        "privacy_status": "synthetic_or_public_license_only_no_real_participant_data",
        "validator_expectation": f"Fixture manifest validates module_id={module_id}, lifecycle={lifecycle}, checksum, license, parameters, and expected output references.",
    }


def _expected_output_requirement(index: int, contract: dict[str, Any]) -> dict[str, Any]:
    module_id = contract["module_id"]
    return {
        "requirement_id": f"VR-EO-MOD-{index:04d}",
        "artifact_type": "report_bundle",
        "artifact_subtype": f"{module_id}_module_result_or_boundary_bundle",
        "checks": [
            "Report ZIP or boundary bundle is downloadable when the workflow allows it.",
            "report.json records schema version, module_id, workflow_id, parameters, processing steps, warnings, timestamp, and source data references.",
            "CSV tables match table_dictionary.json where tables are produced.",
            "PDF or HTML report contains method summary and lifecycle limitations.",
            "Artifact manifest records hashes, software versions, and package-relative paths.",
        ],
        "schema_or_fields": _schema_fields(contract),
        "scientific_boundary_checks": _scientific_boundary_checks(contract),
        "blocking_criteria": _blocking_criteria(contract),
    }


def _artifact_checklist(contract: dict[str, Any]) -> dict[str, Any]:
    module_id = contract["module_id"]
    return {
        "module_id": module_id,
        "source_file": contract.get("_source_file"),
        "lifecycle_state": contract.get("lifecycle_state"),
        "checklist": [
            "Verify report.pdf/report.html, report.json, manifest.json, effective_call.json, workflow.json, software_versions.json, table_dictionary.json, and source_metadata.json when applicable.",
            "Verify units, axes, colorbar, sampling rate, frequency/time ranges, and channel or epoch counts where applicable.",
            "Verify parameters and effective_call reflect resolved runtime values, not only UI defaults.",
            "Verify warnings are structured and visible in customer-facing report surfaces.",
            "Scan customer-visible text for diagnosis, treatment, causality, significance, source localization, brain-region activation, and information-flow overclaims.",
            *_module_specific_checks(module_id),
        ],
    }


def _expected_ui_states(contract: dict[str, Any]) -> list[str]:
    lifecycle = contract.get("lifecycle_state")
    states = ["default", "loading", "error", "success", "disabled", "focus_keyboard"]
    if lifecycle in {"beta", "draft"}:
        states.append(f"{lifecycle}_boundary_visible")
    return states


def _expected_warnings(contract: dict[str, Any]) -> list[str]:
    lifecycle = contract.get("lifecycle_state")
    warnings = [
        "Research-use descriptive EEG output; not for clinical diagnosis or treatment decisions.",
        "No statistical significance, causality, or clinical interpretation is implied unless separately validated.",
    ]
    if lifecycle == "beta":
        warnings.append("Beta module: not a default stable paid conclusion.")
    if lifecycle == "draft":
        warnings.append("Draft or boundary module: no V01 execution or customer conclusion.")
    return warnings


def _blocking_criteria(contract: dict[str, Any]) -> list[str]:
    module_id = contract["module_id"]
    criteria = [
        "Missing fixture manifest, checksum, or license/source status.",
        "Missing parameters/effective_call/workflow/software version evidence.",
        "Missing non-diagnostic boundary in report or export.",
        "Customer-visible text contains diagnosis, treatment, unsupported significance, causality, or clinical decision language.",
    ]
    if module_id in {"sensor_topography", "source_localization_boundary"}:
        criteria.append("Sensor-level results are labeled as brain-region activation or source localization.")
    if "connectivity" in module_id:
        criteria.append("Connectivity output is described as causality, information flow, or brain-region communication.")
    if module_id == "source_localization_boundary":
        criteria.append("Source localization execution is allowed without MRI/head model/forward/inverse/source-space evidence.")
    return criteria


def _fixture_must_include(contract: dict[str, Any]) -> list[str]:
    module_id = contract["module_id"]
    items = [
        "fixture_manifest.json",
        "dataset card or synthetic generation note",
        "sha256 checksums",
        "sampling rate and channel names",
        "non-sensitive source/license statement",
    ]
    if module_id in {"event_epoch", "erp_p300", "tfr_ersp_itc"}:
        items.extend(["event markers", "epoch window metadata"])
    if module_id in {"sensor_topography", "reference_csd", "source_localization_boundary"}:
        items.append("montage or electrode-position boundary statement")
    return items


def _schema_fields(contract: dict[str, Any]) -> list[str]:
    module_id = contract["module_id"]
    fields = [
        "module_id",
        "workflow_id",
        "parameters",
        "effective_call",
        "processing_steps",
        "warnings",
        "timestamp",
        "software_versions",
        "source_data_refs",
        "non_diagnostic_boundary",
    ]
    if module_id in {"event_epoch", "erp_p300", "tfr_ersp_itc"}:
        fields.extend(["epoch_set_id", "events", "drop_log"])
    if module_id == "pac_cfc":
        fields.extend(["phase_frequency_grid", "amplitude_frequency_grid", "bins", "mi_metric"])
    if module_id == "reference_csd":
        fields.extend(["reference_mode", "montage_status", "csd_parameters"])
    return fields


def _scientific_boundary_checks(contract: dict[str, Any]) -> list[str]:
    module_id = contract["module_id"]
    checks = [
        "non_diagnostic_boundary_present",
        "no_treatment_or_clinical_decision_claim",
        "no_unsupported_significance_claim",
        "no_causality_claim",
    ]
    if module_id in {"sensor_topography", "source_localization_boundary"}:
        checks.append("no_sensor_space_to_source_space_overclaim")
    if "connectivity" in module_id:
        checks.append("no_information_flow_or_causality_claim")
    return checks


def _module_specific_checks(module_id: str) -> list[str]:
    if module_id == "multitaper_psd_tfr":
        return ["Check time_bandwidth/bandwidth/adaptive/low_bias, Nyquist, and segment/window constraints."]
    if module_id == "sensor_topography":
        return ["Check montage/electrode positions, channel-level input values, colorbar, unit, and sensor-space wording."]
    if "connectivity" in module_id:
        return ["Check reference strategy, volume conduction controls, node/edge definitions, and no causality wording."]
    if module_id == "source_localization_boundary":
        return ["Check blockers for MRI/head model/forward/inverse/noise covariance/source space/coregistration."]
    if module_id == "pac_cfc":
        return ["Check phase/amplitude grids, bins, MI metric, surrogate quality note, and no p-value/significance output."]
    if module_id == "tfr_ersp_itc":
        return ["Check frequency grid, n_cycles, baseline metadata, ITC table, and gamma muscle-risk warning."]
    if module_id == "erp_p300":
        return ["Check epoch_set_id, event confirmation, ROI/component window, drop log, and waveform long table."]
    return []


if __name__ == "__main__":
    main()
