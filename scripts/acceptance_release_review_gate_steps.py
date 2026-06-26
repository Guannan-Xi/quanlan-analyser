from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE_RUN = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_review_gate_run.json"
OUTPUT = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_release_review_gate_steps.json"

REQUIRED_STEPS = [
    "compile_release_gate_scripts",
    "mojibake_check",
    "accept_utf8_text_preflight",
    "accept_visual_layout_design_spec",
    "strict_preflight_expected_block",
    "owner_input_checklist",
    "accept_start_here_release_review",
    "accept_owner_input_checklist",
    "accept_owner_decision_packet",
    "accept_production_goal_matrix",
    "accept_release_no_misclaim",
    "build_07a_review_system_packet",
    "accept_07a_review_system_packet",
    "accept_analysis_module_contract",
    "accept_analysis_workflow_framework",
    "accept_cro_traceability_contract",
    "accept_round006_pac_real_report_consumption",
    "accept_psd_real_report_consumption",
    "accept_qc_real_report_consumption",
    "accept_pdf_ocr_artifact_qa",
    "accept_round006_tfr_real_report_consumption",
    "accept_mainline_eeg_contract_mapping_consumption",
    "accept_round007_preprocessing_real_report_consumption",
    "accept_round008_erp_real_report_consumption",
    "accept_v01_no_group_statistics_boundary",
    "accept_p0_fixture_validator_contract",
    "accept_p0_gap_repair_contract",
    "accept_stage_gated_review_policy",
    "accept_report_artifact_label_readability",
    "validate_latest_checkpoint_access",
    "accept_latest_checkpoint_access",
    "sanitized_evidence_bundle",
    "sanitized_review_package",
    "accept_sanitized_review_package",
]

REQUIRED_SAFE_CLAIM_PARTS = [
    "Local/sandbox release review gate passed",
    "public cloud release remains blocked",
    "external inputs",
]


def main() -> int:
    payload = json.loads(GATE_RUN.read_text(encoding="utf-8"))
    step_names = [step.get("name") for step in payload.get("steps", [])]
    missing_steps = [name for name in REQUIRED_STEPS if name not in step_names]
    unexpected_failed = [step.get("name") for step in payload.get("steps", []) if not step.get("ok")]
    safe_claim = payload.get("safe_claim", "")
    missing_safe_claim_parts = [part for part in REQUIRED_SAFE_CLAIM_PARTS if part not in safe_claim]
    status = (
        "passed"
        if payload.get("status") == "passed"
        and not missing_steps
        and not unexpected_failed
        and not missing_safe_claim_parts
        else "failed"
    )
    result = {
        "status": status,
        "gate_run": str(GATE_RUN),
        "required_steps": REQUIRED_STEPS,
        "actual_steps": step_names,
        "step_count": len(step_names),
        "missing_steps": missing_steps,
        "unexpected_failed_steps": unexpected_failed,
        "safe_claim": safe_claim,
        "missing_safe_claim_parts": missing_safe_claim_parts,
        "policy": "The one-command release gate must keep all critical local/sandbox, evidence, packaging, and external-boundary checks.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
