from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KB_CONTRACT_DIR = Path(r"D:\QuanLanKnowledgeBase\learning-notes\qlanalyser\module-contracts")

CONTRACT_FILENAMES = {
    "preprocessing_readiness": "preprocessing_readiness.module_contract.yaml",
    "event_epoch": "event_epoch.module_contract.yaml",
    "psd_bandpower": "psd_bandpower.module_contract.yaml",
    "erp_p300": "erp_p300.module_contract.yaml",
    "ica_artifact_review": "ica_artifact_review.beta_contract.yaml",
    "tfr_ersp_itc": "tfr_ersp_itc.beta_contract.yaml",
    "pac_cfc": "pac_cfc.beta_contract.yaml",
    "reference_csd": "reference_csd.beta_contract.yaml",
    "multitaper_psd_tfr": "multitaper_psd_tfr.beta_contract.yaml",
    "sensor_topography": "sensor_topography.draft_contract.yaml",
    "connectivity_sensor_method_design": "connectivity.method_design_contract.yaml",
    "source_localization_boundary": "source_localization.boundary_contract.yaml",
}

WORKFLOW_CONTRACT_MAP = {
    "metadata_qc": "preprocessing_readiness",
    "qc_waveform_preview": "preprocessing_readiness",
    "preprocessing_readiness": "preprocessing_readiness",
    "event_epoch_prepare": "event_epoch",
    "resting_psd": "psd_bandpower",
    "erp_p300": "erp_p300",
    "tfr_ersp_itc": "tfr_ersp_itc",
    "pac_cfc": "pac_cfc",
    "reference_csd": "reference_csd",
    "multitaper_psd_tfr": "multitaper_psd_tfr",
    "sensor_topography": "sensor_topography",
    "connectivity": "connectivity_sensor_method_design",
    "source_localization_boundary": "source_localization_boundary",
}


@lru_cache(maxsize=1)
def load_module_contract_registry() -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for module_id, filename in CONTRACT_FILENAMES.items():
        path = DEFAULT_KB_CONTRACT_DIR / filename
        if not path.exists():
            registry[module_id] = {
                "module_id": module_id,
                "contract_status": "missing",
                "source_path": str(path),
            }
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        registry[module_id] = _contract_summary(payload, path)
    return registry


def enrich_workflow_templates(templates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    registry = load_module_contract_registry()
    enriched: list[dict[str, Any]] = []
    for template in templates:
        record = dict(template)
        contract_id = WORKFLOW_CONTRACT_MAP.get(record.get("id"))
        if contract_id:
            record["module_contract"] = registry.get(
                contract_id,
                {"module_id": contract_id, "contract_status": "missing"},
            )
        enriched.append(record)
    return enriched


def _contract_summary(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    required_keys = [
        "input_requirements",
        "parameters_schema",
        "execution_contract",
        "output_schema",
        "artifact_manifest",
        "report_mapping",
        "ui_contract",
        "acceptance_gates",
        "scientific_boundaries",
    ]
    execution = payload.get("execution_contract") or {}
    output_schema = payload.get("output_schema") or {}
    acceptance_gates = payload.get("acceptance_gates") or {}
    boundaries = payload.get("scientific_boundaries") or {}
    return {
        "contract_status": "loaded",
        "source_path": str(path),
        "schema_version": payload.get("schema_version"),
        "module_id": payload.get("module_id"),
        "display_name": payload.get("display_name"),
        "lifecycle_state": payload.get("lifecycle_state"),
        "promotion_target": payload.get("promotion_target"),
        "version": payload.get("version"),
        "task_module": execution.get("task_module"),
        "workflow_id": execution.get("workflow_id"),
        "runner": execution.get("runner"),
        "output_schema_keys": sorted(output_schema.keys()),
        "acceptance_gate_keys": sorted(acceptance_gates.keys()),
        "forbidden_claim_count": len(boundaries.get("forbidden_claims") or []) if isinstance(boundaries, dict) else 0,
        "required_keys_present": {key: key in payload for key in required_keys},
        "non_medical_boundary_present": bool(payload.get("non_medical_boundary")),
    }
