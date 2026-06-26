from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "work" / "release_evidence"
DEFAULT_OUTPUT_JSON = EVIDENCE_DIR / "20260620-v01-acceptance" / "release_gate_summary.json"
DEFAULT_OUTPUT_MD = EVIDENCE_DIR / "20260620-v01-acceptance" / "release_gate_summary.md"

PATHS = {
    "manifest": EVIDENCE_DIR / "20260620-v01-acceptance" / "evidence_manifest.json",
    "preflight": EVIDENCE_DIR / "20260620-aliyun-staging" / "aliyun_staging_preflight.json",
    "owner_checklist": EVIDENCE_DIR / "20260620-aliyun-staging" / "owner_input_checklist.md",
    "owner_decision_packet": EVIDENCE_DIR / "20260620-aliyun-staging" / "owner_decision_packet.md",
    "owner_decision_acceptance": EVIDENCE_DIR / "20260620-v01-acceptance" / "acceptance_owner_decision_packet.json",
    "release_gate_steps": EVIDENCE_DIR / "20260620-v01-acceptance" / "acceptance_release_review_gate_steps.json",
    "release_gate_run": EVIDENCE_DIR / "20260620-v01-acceptance" / "release_review_gate_run.core.json",
    "manifest_consistency": EVIDENCE_DIR / "20260620-v01-acceptance" / "acceptance_release_manifest_consistency.json",
    "completion_audit": EVIDENCE_DIR / "20260620-v01-acceptance" / "production_goal_completion_audit.md",
    "requirement_matrix": EVIDENCE_DIR / "20260620-v01-acceptance" / "production_goal_requirement_matrix.json",
    "requirement_matrix_md": EVIDENCE_DIR / "20260620-v01-acceptance" / "production_goal_requirement_matrix.md",
    "preset_analysis": EVIDENCE_DIR / "20260620-customer-preset-analysis" / "customer_preset_analysis.json",
    "page_visual_qa": EVIDENCE_DIR / "20260620-page-visual-qa" / "page_visual_qa.json",
    "utf8_text_preflight": EVIDENCE_DIR / "20260620-v01-acceptance" / "acceptance_utf8_text_preflight.json",
    "visual_layout_design_spec": EVIDENCE_DIR / "20260620-v01-acceptance" / "acceptance_visual_layout_design_spec.json",
    "analysis_module_contract": EVIDENCE_DIR / "20260620-v01-acceptance" / "acceptance_analysis_module_contract.json",
    "cro_traceability_contract": EVIDENCE_DIR / "20260620-v01-acceptance" / "acceptance_cro_traceability_contract.json",
    "public_deployment_evidence": EVIDENCE_DIR / "20260620-v01-public" / "PUBLIC_DEPLOYMENT_EVIDENCE.md",
    "public_ops_ui_after_deploy": EVIDENCE_DIR / "20260620-v01-public" / "acceptance_ops_ui_public_after_deploy.json",
    "review_access_checkpoint_packet": EVIDENCE_DIR / "checkpoints" / "2026-06-22-review-access-validator-contract-fully-verified.json",
    "review_access_checkpoint_packet_md": EVIDENCE_DIR / "checkpoints" / "2026-06-22-review-access-validator-contract-fully-verified.md",
    "mainline_eeg_module_expert_review": EVIDENCE_DIR / "checkpoints" / "2026-06-22-mainline-eeg-module-expert-review.json",
    "mainline_eeg_module_expert_review_md": EVIDENCE_DIR / "checkpoints" / "2026-06-22-mainline-eeg-module-expert-review.md",
    "mainline_eeg_bridge_checkpoint": EVIDENCE_DIR / "checkpoints" / "2026-06-22-0502-07a-mainline-eeg-bridge-checkpoint.json",
    "mainline_eeg_bridge_checkpoint_md": EVIDENCE_DIR / "checkpoints" / "2026-06-22-0502-07a-mainline-eeg-bridge-checkpoint.md",
    "mainline_eeg_bridge_acceptance": EVIDENCE_DIR / "mainline_eeg_review" / "mainline_eeg_review_bridge_acceptance.json",
    "mainline_eeg_handoff_checkpoint": EVIDENCE_DIR / "checkpoints" / "2026-06-22-0505-07a-mainline-eeg-handoff.json",
    "mainline_eeg_handoff_checkpoint_md": EVIDENCE_DIR / "checkpoints" / "2026-06-22-0505-07a-mainline-eeg-handoff.md",
    "mainline_eeg_brief_checkpoint": EVIDENCE_DIR / "checkpoints" / "2026-06-22-0506-07a-mainline-eeg-brief.json",
    "mainline_eeg_brief_checkpoint_md": EVIDENCE_DIR / "checkpoints" / "2026-06-22-0506-07a-mainline-eeg-brief.md",
    "mainline_eeg_index_checkpoint": EVIDENCE_DIR / "checkpoints" / "2026-06-22-0507-07a-mainline-eeg-index.md",
    "mainline_eeg_contract_mapping_checkpoint": EVIDENCE_DIR / "checkpoints" / "2026-06-22-07a-mainline-eeg-contract-mapping.json",
    "mainline_eeg_contract_mapping_checkpoint_md": EVIDENCE_DIR / "checkpoints" / "2026-06-22-07a-mainline-eeg-contract-mapping.md",
    "mainline_eeg_contract_mapping_consumption": EVIDENCE_DIR / "mainline_eeg_review" / "mainline_eeg_contract_mapping_consumption.json",
    "psd_real_report_consumption": EVIDENCE_DIR / "virtual_reviewer_p0" / "psd_real_report_consumption.json",
    "qc_real_report_consumption": EVIDENCE_DIR / "virtual_reviewer_p0" / "qc_real_report_consumption.json",
    "pdf_ocr_artifact_qa": EVIDENCE_DIR / "pdf_ocr_artifact_qa" / "pdf_ocr_artifact_qa.json",
    "round006_pac_real_report_consumption": EVIDENCE_DIR / "virtual_reviewer_round_006" / "pac_real_report_consumption.json",
    "round006_tfr_real_report_consumption": EVIDENCE_DIR / "virtual_reviewer_round_006" / "tfr_real_report_consumption.json",
    "round007_preprocessing_real_report_consumption": EVIDENCE_DIR / "virtual_reviewer_round_007" / "round_007_real_report_consumption.json",
    "round008_erp_real_report_consumption": EVIDENCE_DIR / "virtual_reviewer_round_008" / "erp_real_report_consumption.json",
    "v01_no_group_statistics_boundary": EVIDENCE_DIR / "virtual_reviewer_round_008" / "v01_no_group_statistics_boundary.json",
    "p0_fixture_validator_contract": EVIDENCE_DIR / "p0_fixture_validator" / "acceptance_p0_fixture_validator_contract.json",
    "p0_gap_repair_contract": EVIDENCE_DIR / "p0_gap_repair" / "acceptance_p0_gap_repair_contract.json",
    "module_lab_preview_selectors": EVIDENCE_DIR / "module_lab_preview_selectors" / "acceptance_module_lab_preview_selectors.json",
    "review_system_packet": EVIDENCE_DIR / "review_system" / "2026-06-22-07a-p0-contract-module-lab" / "review_packet.json",
    "review_system_packet_md": EVIDENCE_DIR / "review_system" / "2026-06-22-07a-p0-contract-module-lab" / "review_packet.md",
    "review_system_packet_acceptance": EVIDENCE_DIR / "review_system" / "2026-06-22-07a-p0-contract-module-lab" / "acceptance_07a_review_system_packet.json",
    "review_system_qa_table": EVIDENCE_DIR / "review_system" / "2026-06-22-07a-p0-contract-module-lab" / "qa_table.csv",
    "review_system_fix_plan": EVIDENCE_DIR / "review_system" / "2026-06-22-07a-p0-contract-module-lab" / "fix_plan.md",
    "stage_gated_review_policy": EVIDENCE_DIR / "stage_gated_review_policy" / "acceptance_stage_gated_review_policy.json",
    "report_artifact_label_readability": EVIDENCE_DIR / "report_artifact_label_readability" / "acceptance_report_artifact_label_readability.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def status_of(path: Path) -> str:
    if not path.exists():
        return "missing"
    if path.suffix == ".json":
        return str(read_json(path).get("status", "present"))
    return "present"


def latest_checkpoint_json() -> Path:
    checkpoint_dir = EVIDENCE_DIR / "checkpoints"
    candidates = sorted(checkpoint_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        return checkpoint_dir / "__missing_checkpoint__.json"
    return candidates[0]


def summarize() -> dict[str, Any]:
    manifest = read_json(PATHS["manifest"])
    preflight = read_json(PATHS["preflight"])
    owner_decision_acceptance = read_json(PATHS["owner_decision_acceptance"])
    release_gate_run = read_json(PATHS["release_gate_run"])
    manifest_consistency = read_json(PATHS["manifest_consistency"])
    preset = read_json(PATHS["preset_analysis"])
    visual = read_json(PATHS["page_visual_qa"])
    requirement_matrix = read_json(PATHS["requirement_matrix"])
    utf8_text_preflight = read_json(PATHS["utf8_text_preflight"])
    visual_layout_design_spec = read_json(PATHS["visual_layout_design_spec"])
    analysis_module_contract = read_json(PATHS["analysis_module_contract"])
    cro_traceability_contract = read_json(PATHS["cro_traceability_contract"])
    public_ops_ui = read_json(PATHS["public_ops_ui_after_deploy"])
    review_access_checkpoint = read_json(PATHS["review_access_checkpoint_packet"])
    mainline_eeg_review = read_json(PATHS["mainline_eeg_module_expert_review"])
    mainline_eeg_bridge_checkpoint = read_json(PATHS["mainline_eeg_bridge_checkpoint"])
    mainline_eeg_bridge_acceptance = read_json(PATHS["mainline_eeg_bridge_acceptance"])
    mainline_eeg_handoff_checkpoint = read_json(PATHS["mainline_eeg_handoff_checkpoint"])
    mainline_eeg_brief_checkpoint = read_json(PATHS["mainline_eeg_brief_checkpoint"])
    mainline_eeg_contract_mapping = read_json(PATHS["mainline_eeg_contract_mapping_checkpoint"])
    mainline_eeg_contract_mapping_consumption = read_json(PATHS["mainline_eeg_contract_mapping_consumption"])
    psd_real_report_consumption = read_json(PATHS["psd_real_report_consumption"])
    qc_real_report_consumption = read_json(PATHS["qc_real_report_consumption"])
    pdf_ocr_artifact_qa = read_json(PATHS["pdf_ocr_artifact_qa"])
    round006_pac_real_report_consumption = read_json(PATHS["round006_pac_real_report_consumption"])
    round006_tfr_real_report_consumption = read_json(PATHS["round006_tfr_real_report_consumption"])
    round007_preprocessing_real_report_consumption = read_json(PATHS["round007_preprocessing_real_report_consumption"])
    round008_erp_real_report_consumption = read_json(PATHS["round008_erp_real_report_consumption"])
    v01_no_group_statistics_boundary = read_json(PATHS["v01_no_group_statistics_boundary"])
    p0_fixture_validator_contract = read_json(PATHS["p0_fixture_validator_contract"])
    p0_gap_repair_contract = read_json(PATHS["p0_gap_repair_contract"])
    module_lab_preview_selectors = read_json(PATHS["module_lab_preview_selectors"])
    review_system_packet = read_json(PATHS["review_system_packet"])
    review_system_packet_acceptance = read_json(PATHS["review_system_packet_acceptance"])
    stage_gated_review_policy = read_json(PATHS["stage_gated_review_policy"])
    report_artifact_label_readability = read_json(PATHS["report_artifact_label_readability"])
    latest_checkpoint = latest_checkpoint_json()

    preflight_checks = preflight.get("checks", [])
    todo_checks = [check for check in preflight_checks if check.get("status") == "todo"]
    failed_checks = [check for check in preflight_checks if check.get("status") == "fail"]
    gate_steps = release_gate_run.get("steps", [])
    gate_failed_steps = [step.get("name") for step in gate_steps if not step.get("ok")]

    local_ready = (
        manifest.get("full_runner_result") == "V01 acceptance suite passed."
        and status_of(PATHS["page_visual_qa"]) == "passed"
        and status_of(PATHS["preset_analysis"]) == "passed"
        and status_of(PATHS["requirement_matrix"]) == "passed_with_external_boundaries"
        and not requirement_matrix.get("failed_requirements")
        and bool(preset.get("checks", {}).get("psd", {}).get("bandpowerOutputsPresent"))
        and bool(visual.get("pageVisualQa", {}).get("pass"))
        and utf8_text_preflight.get("status") == "passed"
        and visual_layout_design_spec.get("status") == "passed"
        and analysis_module_contract.get("status") == "passed"
        and cro_traceability_contract.get("status") == "passed"
    )
    cloud_ready = preflight.get("status") == "ready_for_strict_staging" and not todo_checks and not failed_checks
    public_ecs_sandbox_review_ready = (
        PATHS["public_deployment_evidence"].exists()
        and public_ops_ui.get("status") == "passed"
        and public_ops_ui.get("adminInvoiceUploadControlVisible") is True
        and public_ops_ui.get("issuedInvoiceStatus") == "issued"
        and public_ops_ui.get("invoiceAttachmentDownloaded") is True
    )

    return {
        "status": "blocked_external_inputs" if local_ready and not cloud_ready else ("ready_for_release_review" if local_ready and cloud_ready else "failed_local_gate"),
        "generated_at": utc_now(),
        "local_sandbox_review_ready": local_ready,
        "public_ecs_sandbox_review_ready": public_ecs_sandbox_review_ready,
        "public_cloud_ready": cloud_ready,
        "safe_claim": (
            "Local/sandbox V01 product loop is review-ready, and public ECS sandbox review evidence is available; strict public production/provider readiness remains blocked on preflight todos."
            if local_ready and public_ecs_sandbox_review_ready and not cloud_ready
            else (
                "Local/sandbox V01 product loop is review-ready; public cloud release remains blocked on preflight todos."
                if local_ready and not cloud_ready
                else "All gates represented in this summary are ready." if local_ready and cloud_ready else "Local/sandbox gate is incomplete."
            )
        ),
        "source_paths": {key: str(value) for key, value in PATHS.items()},
        "local_gates": {
            "full_acceptance": manifest.get("full_runner_result"),
            "page_visual_qa": visual.get("pageVisualQa", {}),
            "preset_analysis": {
                "status": preset.get("status"),
                "bandpowerOutputsPresent": preset.get("checks", {}).get("psd", {}).get("bandpowerOutputsPresent"),
            },
            "requirement_matrix": {
                "status": requirement_matrix.get("status"),
                "requirement_count": len(requirement_matrix.get("requirements", [])),
                "failed_requirements": requirement_matrix.get("failed_requirements", []),
                "external_boundaries": requirement_matrix.get("external_boundaries", []),
                "path": str(PATHS["requirement_matrix"]),
                "markdown_path": str(PATHS["requirement_matrix_md"]),
            },
            "release_gate_steps": {
                "status": release_gate_run.get("status"),
                "step_count": len(gate_steps),
                "missing_steps": [],
                "unexpected_failed_steps": gate_failed_steps,
                "path": str(PATHS["release_gate_run"]),
            },
            "manifest_consistency": {
                "status": manifest_consistency.get("status"),
                "evidence_count": manifest_consistency.get("evidence_count"),
                "missing_readiness_keys": manifest_consistency.get("missing_readiness_keys", []),
                "wrong_targets": manifest_consistency.get("wrong_targets", []),
                "missing_evidence_entries": manifest_consistency.get("missing_evidence_entries", []),
                "missing_files": manifest_consistency.get("missing_files", []),
                "missing_or_bad_summary": manifest_consistency.get("missing_or_bad_summary", []),
                "path": str(PATHS["manifest_consistency"]),
            },
            "analysis_module_contract": {
                "status": analysis_module_contract.get("status"),
                "path": str(PATHS["analysis_module_contract"]),
            },
            "utf8_text_preflight": {
                "status": utf8_text_preflight.get("status"),
                "rejects_non_utf8_text": utf8_text_preflight.get("checks", {}).get("rejects_non_utf8_text"),
                "rejects_literal_question_marks": utf8_text_preflight.get("checks", {}).get("rejects_literal_question_marks"),
                "path": str(PATHS["utf8_text_preflight"]),
            },
            "visual_layout_design_spec": {
                "status": visual_layout_design_spec.get("status"),
                "numeric_layout_budget": visual_layout_design_spec.get("checks", {}).get("numeric_layout_budget"),
                "literal_question_guard": visual_layout_design_spec.get("checks", {}).get("literal_question_guard"),
                "path": str(PATHS["visual_layout_design_spec"]),
            },
            "cro_traceability_contract": {
                "status": cro_traceability_contract.get("status"),
                "path": str(PATHS["cro_traceability_contract"]),
            },
            "stage_gated_review_policy": {
                "status": stage_gated_review_policy.get("status"),
                "path": str(PATHS["stage_gated_review_policy"]),
                "required_environments": stage_gated_review_policy.get("required_environments", []),
                "required_gates": stage_gated_review_policy.get("required_gates", []),
            },
            "report_artifact_label_readability": {
                "status": report_artifact_label_readability.get("status"),
                "path": str(PATHS["report_artifact_label_readability"]),
                "report_zip_path": report_artifact_label_readability.get("report_zip_path"),
                "issues": report_artifact_label_readability.get("issues", []),
            },
            "latest_checkpoint_access": {
                "path": str(latest_checkpoint),
                "status": status_of(latest_checkpoint),
            },
            "sanitized_bundle": manifest.get("sanitized_evidence", {}),
            "public_ecs_sandbox_review": {
                "ready": public_ecs_sandbox_review_ready,
                "deployment_evidence_path": str(PATHS["public_deployment_evidence"]),
                "ops_ui_status": public_ops_ui.get("status"),
                "ops_ui_path": str(PATHS["public_ops_ui_after_deploy"]),
                "strict_production_provider_boundary": "Public ECS sandbox review is separate from strict public production/provider readiness.",
            },
        },
        "cloud_gates": {
            "preflight_status": preflight.get("status"),
            "todo_count": len(todo_checks),
            "failed_count": len(failed_checks),
            "todo_names": [check.get("name") for check in todo_checks],
            "failed_names": [check.get("name") for check in failed_checks],
            "owner_checklist": str(PATHS["owner_checklist"]),
            "owner_decision_packet": str(PATHS["owner_decision_packet"]),
            "owner_decision_acceptance": {
                "status": owner_decision_acceptance.get("status"),
                "preflight_blocked_without_failures": owner_decision_acceptance.get("preflight_blocked_without_failures"),
                "path": str(PATHS["owner_decision_acceptance"]),
            },
            "next_commands": preflight.get("next_commands", []),
        },
        "recent_review_checkpoints": {
            "review_access_checkpoint_packet": {
                "status": review_access_checkpoint.get("status"),
                "path": str(PATHS["review_access_checkpoint_packet"]),
                "markdown_path": str(PATHS["review_access_checkpoint_packet_md"]),
                "credential_safety": review_access_checkpoint.get("review_access", {}).get("credential_safety"),
            },
            "mainline_eeg_module_expert_review": {
                "status": mainline_eeg_review.get("status"),
                "verdict": mainline_eeg_review.get("verdict"),
                "release_pass": mainline_eeg_review.get("release_pass"),
                "path": str(PATHS["mainline_eeg_module_expert_review"]),
                "markdown_path": str(PATHS["mainline_eeg_module_expert_review_md"]),
            },
            "mainline_eeg_bridge_checkpoint": {
                "status": mainline_eeg_bridge_checkpoint.get("results", {}).get("bridge_gate_status"),
                "product_gate": mainline_eeg_bridge_acceptance.get("product_gate"),
                "screenshot_count": mainline_eeg_bridge_acceptance.get("summary", {}).get("screenshot_count"),
                "path": str(PATHS["mainline_eeg_bridge_checkpoint"]),
                "markdown_path": str(PATHS["mainline_eeg_bridge_checkpoint_md"]),
                "bridge_acceptance_path": str(PATHS["mainline_eeg_bridge_acceptance"]),
            },
            "mainline_eeg_handoff_checkpoint": {
                "status": mainline_eeg_handoff_checkpoint.get("status"),
                "bridge_gate_status": mainline_eeg_handoff_checkpoint.get("results", {}).get("bridge_gate_status"),
                "path": str(PATHS["mainline_eeg_handoff_checkpoint"]),
                "markdown_path": str(PATHS["mainline_eeg_handoff_checkpoint_md"]),
            },
            "mainline_eeg_brief_checkpoint": {
                "status": mainline_eeg_brief_checkpoint.get("status"),
                "path": str(PATHS["mainline_eeg_brief_checkpoint"]),
                "markdown_path": str(PATHS["mainline_eeg_brief_checkpoint_md"]),
                "release_summary_status": mainline_eeg_brief_checkpoint.get("status_snapshot", {}).get("release_summary_status"),
            },
            "mainline_eeg_index_checkpoint": {
                "status": "present" if PATHS["mainline_eeg_index_checkpoint"].exists() else "missing",
                "path": str(PATHS["mainline_eeg_index_checkpoint"]),
            },
            "mainline_eeg_contract_mapping_checkpoint": {
                "status": mainline_eeg_contract_mapping.get("status"),
                "path": str(PATHS["mainline_eeg_contract_mapping_checkpoint"]),
                "markdown_path": str(PATHS["mainline_eeg_contract_mapping_checkpoint_md"]),
            },
            "mainline_eeg_contract_mapping_consumption": {
                "status": mainline_eeg_contract_mapping_consumption.get("status"),
                "path": str(PATHS["mainline_eeg_contract_mapping_consumption"]),
                "report_zip_path": mainline_eeg_contract_mapping_consumption.get("run_result", {}).get("report_zip_path"),
                "report_zip_missing_required_entries": mainline_eeg_contract_mapping_consumption.get("run_result", {}).get("report_zip_missing_required_entries"),
            },
            "psd_real_report_consumption": {
                "status": psd_real_report_consumption.get("status"),
                "requirement_id": psd_real_report_consumption.get("requirement_id"),
                "path": str(PATHS["psd_real_report_consumption"]),
                "report_zip_path": psd_real_report_consumption.get("report_zip_path"),
                "blockers": psd_real_report_consumption.get("blockers", []),
                "boundary": psd_real_report_consumption.get("important_boundary"),
            },
            "qc_real_report_consumption": {
                "status": qc_real_report_consumption.get("status"),
                "requirement_id": qc_real_report_consumption.get("requirement_id"),
                "path": str(PATHS["qc_real_report_consumption"]),
                "report_zip_path": qc_real_report_consumption.get("report_zip_path"),
                "blockers": qc_real_report_consumption.get("blockers", []),
                "warnings": qc_real_report_consumption.get("warnings", []),
                "boundary": qc_real_report_consumption.get("important_boundary"),
            },
            "pdf_ocr_artifact_qa": {
                "status": pdf_ocr_artifact_qa.get("status"),
                "requirement_id": pdf_ocr_artifact_qa.get("requirement_id"),
                "path": str(PATHS["pdf_ocr_artifact_qa"]),
                "report_zip_path": pdf_ocr_artifact_qa.get("report_zip_path"),
                "primary_parse": pdf_ocr_artifact_qa.get("primary_parse"),
                "auxiliary_text_layer_audit": pdf_ocr_artifact_qa.get("auxiliary_text_layer_audit"),
                "artifact_validator_verdict": pdf_ocr_artifact_qa.get("artifact_validator_verdict"),
                "blockers": pdf_ocr_artifact_qa.get("blockers", []),
                "boundary": pdf_ocr_artifact_qa.get("important_boundary"),
            },
            "round006_pac_real_report_consumption": {
                "status": round006_pac_real_report_consumption.get("status"),
                "requirement_id": round006_pac_real_report_consumption.get("requirement_id"),
                "path": str(PATHS["round006_pac_real_report_consumption"]),
                "report_zip_path": round006_pac_real_report_consumption.get("report_zip_path"),
                "blockers": round006_pac_real_report_consumption.get("blockers", []),
                "boundary": round006_pac_real_report_consumption.get("important_boundary"),
            },
            "round006_tfr_real_report_consumption": {
                "status": round006_tfr_real_report_consumption.get("status"),
                "requirement_id": round006_tfr_real_report_consumption.get("requirement_id"),
                "path": str(PATHS["round006_tfr_real_report_consumption"]),
                "report_zip_path": round006_tfr_real_report_consumption.get("report_zip_path"),
                "blockers": round006_tfr_real_report_consumption.get("blockers", []),
                "boundary": round006_tfr_real_report_consumption.get("important_boundary"),
            },
            "round007_preprocessing_real_report_consumption": {
                "status": round007_preprocessing_real_report_consumption.get("status"),
                "requirement_ids": round007_preprocessing_real_report_consumption.get("requirement_ids"),
                "path": str(PATHS["round007_preprocessing_real_report_consumption"]),
                "report_zip_path": round007_preprocessing_real_report_consumption.get("report_zip_path"),
                "blockers": round007_preprocessing_real_report_consumption.get("blockers", []),
                "boundary": round007_preprocessing_real_report_consumption.get("important_boundary"),
            },
            "round008_erp_real_report_consumption": {
                "status": round008_erp_real_report_consumption.get("status"),
                "requirement_id": round008_erp_real_report_consumption.get("requirement_id"),
                "path": str(PATHS["round008_erp_real_report_consumption"]),
                "report_zip_path": round008_erp_real_report_consumption.get("report_zip_path"),
                "blockers": round008_erp_real_report_consumption.get("blockers", []),
                "boundary": round008_erp_real_report_consumption.get("important_boundary"),
            },
            "v01_no_group_statistics_boundary": {
                "status": v01_no_group_statistics_boundary.get("status"),
                "path": str(PATHS["v01_no_group_statistics_boundary"]),
                "report_zip_path": v01_no_group_statistics_boundary.get("report_zip_path"),
                "blockers": v01_no_group_statistics_boundary.get("blockers", []),
                "boundary": v01_no_group_statistics_boundary.get("important_boundary"),
            },
            "p0_fixture_validator_contract": {
                "status": p0_fixture_validator_contract.get("status"),
                "path": str(PATHS["p0_fixture_validator_contract"]),
                "fixture_dir": p0_fixture_validator_contract.get("fixture_dir"),
                "evidence_dir": p0_fixture_validator_contract.get("evidence_dir"),
                "failures": p0_fixture_validator_contract.get("failures", []),
            },
            "p0_gap_repair_contract": {
                "status": p0_gap_repair_contract.get("status"),
                "path": str(PATHS["p0_gap_repair_contract"]),
                "checkpoint_path": p0_gap_repair_contract.get("checkpoint_path"),
                "product_gate_status": p0_gap_repair_contract.get("product_gate_status"),
                "failures": p0_gap_repair_contract.get("failures", []),
            },
            "module_lab_preview_selectors": {
                "status": module_lab_preview_selectors.get("status"),
                "path": str(PATHS["module_lab_preview_selectors"]),
                "preview_count": module_lab_preview_selectors.get("actual_count"),
                "expected_count": module_lab_preview_selectors.get("expected_count"),
            },
            "review_system_packet": {
                "status": review_system_packet_acceptance.get("status"),
                "verdict": review_system_packet.get("verdict"),
                "path": str(PATHS["review_system_packet"]),
                "markdown_path": str(PATHS["review_system_packet_md"]),
                "qa_table": str(PATHS["review_system_qa_table"]),
                "fix_plan": str(PATHS["review_system_fix_plan"]),
                "interaction_blockers": review_system_packet.get("interaction_blockers", []),
                "visual_blockers": review_system_packet.get("visual_blockers", []),
                "code_files_reviewed": review_system_packet.get("code_files_reviewed", []),
                "code_reviewable_rule_count": len(review_system_packet.get("code_reviewable_rule", [])),
                "all_scope_ui_evidence": review_system_packet.get("all_scope_ui_evidence", {}),
                "boundary": review_system_packet.get("decision_impact"),
            },
            "boundary": "Recent checkpoints are review/integration evidence and do not change strict production release status.",
        },
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# QLanalyser V01 Release Gate Summary",
        "",
        f"Generated: {summary['generated_at']}",
        "",
        f"- Status: `{summary['status']}`",
        f"- Local/sandbox review ready: `{summary['local_sandbox_review_ready']}`",
        f"- Public ECS sandbox review ready: `{summary['public_ecs_sandbox_review_ready']}`",
        f"- Public cloud ready: `{summary['public_cloud_ready']}`",
        f"- Safe claim: {summary['safe_claim']}",
        "",
        "## Local Gates",
        "",
        f"- Full acceptance: `{summary['local_gates']['full_acceptance']}`",
        f"- Page visual QA pass: `{summary['local_gates']['page_visual_qa'].get('pass')}`",
        f"- Page count: `{summary['local_gates']['page_visual_qa'].get('pageCount')}` x viewports `{summary['local_gates']['page_visual_qa'].get('viewportCount')}`",
        f"- Preset analysis: `{summary['local_gates']['preset_analysis']['status']}`",
        f"- Bandpower outputs present: `{summary['local_gates']['preset_analysis']['bandpowerOutputsPresent']}`",
        f"- Requirement matrix: `{summary['local_gates']['requirement_matrix']['status']}`",
        f"- Requirement count: `{summary['local_gates']['requirement_matrix']['requirement_count']}`",
        f"- Failed requirements: `{summary['local_gates']['requirement_matrix']['failed_requirements']}`",
        f"- Requirement matrix path: `{summary['local_gates']['requirement_matrix']['markdown_path']}`",
        f"- Core release gate status at summary build: `{summary['local_gates']['release_gate_steps']['status']}`",
        f"- Core release gate step count at summary build: `{summary['local_gates']['release_gate_steps']['step_count']}`",
        f"- Core release gate run path: `{summary['local_gates']['release_gate_steps']['path']}`",
        f"- UTF-8 text preflight: `{summary['local_gates']['utf8_text_preflight']['status']}`",
        f"- UTF-8 rejects non-UTF-8 text: `{summary['local_gates']['utf8_text_preflight']['rejects_non_utf8_text']}`",
        f"- UTF-8 rejects literal question marks: `{summary['local_gates']['utf8_text_preflight']['rejects_literal_question_marks']}`",
        f"- UTF-8 text preflight path: `{summary['local_gates']['utf8_text_preflight']['path']}`",
        f"- Visual layout DESIGN_SPEC: `{summary['local_gates']['visual_layout_design_spec']['status']}`",
        f"- Visual layout numeric budget: `{summary['local_gates']['visual_layout_design_spec']['numeric_layout_budget']}`",
        f"- Visual layout path: `{summary['local_gates']['visual_layout_design_spec']['path']}`",
        f"- Analysis module contract: `{summary['local_gates']['analysis_module_contract']['status']}`",
        f"- Analysis module contract path: `{summary['local_gates']['analysis_module_contract']['path']}`",
        f"- CRO traceability contract: `{summary['local_gates']['cro_traceability_contract']['status']}`",
        f"- CRO traceability contract path: `{summary['local_gates']['cro_traceability_contract']['path']}`",
        f"- Stage-gated review policy: `{summary['local_gates']['stage_gated_review_policy']['status']}`",
        f"- Stage-gated review policy path: `{summary['local_gates']['stage_gated_review_policy']['path']}`",
        f"- Stage-gated review environments: `{summary['local_gates']['stage_gated_review_policy']['required_environments']}`",
        f"- Report artifact label readability: `{summary['local_gates']['report_artifact_label_readability']['status']}`",
        f"- Report artifact label readability path: `{summary['local_gates']['report_artifact_label_readability']['path']}`",
        f"- Report artifact label issues: `{summary['local_gates']['report_artifact_label_readability']['issues']}`",
        f"- Latest checkpoint access packet: `{summary['local_gates']['latest_checkpoint_access']['status']}`",
        f"- Latest checkpoint access path: `{summary['local_gates']['latest_checkpoint_access']['path']}`",
        f"- Public ECS sandbox review: `{summary['local_gates']['public_ecs_sandbox_review']['ready']}`",
        f"- Public evidence path: `{summary['local_gates']['public_ecs_sandbox_review']['deployment_evidence_path']}`",
        f"- Public ops UI path: `{summary['local_gates']['public_ecs_sandbox_review']['ops_ui_path']}`",
        f"- Manifest consistency: `{summary['local_gates']['manifest_consistency']['status']}`",
        f"- Manifest evidence count: `{summary['local_gates']['manifest_consistency']['evidence_count']}`",
        f"- Manifest consistency path: `{summary['local_gates']['manifest_consistency']['path']}`",
        "",
        "## Recent Review Checkpoints",
        "",
        f"- REVIEW_ACCESS gate: `{summary['recent_review_checkpoints']['review_access_checkpoint_packet']['status']}`",
        f"- REVIEW_ACCESS evidence: `{summary['recent_review_checkpoints']['review_access_checkpoint_packet']['markdown_path']}`",
        f"- Mainline EEG expert review: `{summary['recent_review_checkpoints']['mainline_eeg_module_expert_review']['verdict']}`",
        f"- Mainline EEG evidence: `{summary['recent_review_checkpoints']['mainline_eeg_module_expert_review']['markdown_path']}`",
        f"- Mainline EEG bridge checkpoint: `{summary['recent_review_checkpoints']['mainline_eeg_bridge_checkpoint']['status']}`",
        f"- Mainline EEG bridge evidence: `{summary['recent_review_checkpoints']['mainline_eeg_bridge_checkpoint']['markdown_path']}`",
        f"- Mainline EEG bridge acceptance JSON: `{summary['recent_review_checkpoints']['mainline_eeg_bridge_checkpoint']['bridge_acceptance_path']}`",
        f"- Mainline EEG handoff packet: `{summary['recent_review_checkpoints']['mainline_eeg_handoff_checkpoint']['status']}`",
        f"- Mainline EEG handoff evidence: `{summary['recent_review_checkpoints']['mainline_eeg_handoff_checkpoint']['markdown_path']}`",
        f"- Mainline EEG brief packet: `{summary['recent_review_checkpoints']['mainline_eeg_brief_checkpoint']['status']}`",
        f"- Mainline EEG brief evidence: `{summary['recent_review_checkpoints']['mainline_eeg_brief_checkpoint']['markdown_path']}`",
        f"- Mainline EEG index packet: `{summary['recent_review_checkpoints']['mainline_eeg_index_checkpoint']['status']}`",
        f"- Mainline EEG contract mapping packet: `{summary['recent_review_checkpoints']['mainline_eeg_contract_mapping_checkpoint']['status']}`",
        f"- Mainline EEG contract mapping evidence: `{summary['recent_review_checkpoints']['mainline_eeg_contract_mapping_checkpoint']['markdown_path']}`",
        f"- Mainline EEG contract-consumption check: `{summary['recent_review_checkpoints']['mainline_eeg_contract_mapping_consumption']['status']}`",
        f"- Mainline EEG contract-consumption evidence: `{summary['recent_review_checkpoints']['mainline_eeg_contract_mapping_consumption']['path']}`",
        f"- Mainline EEG contract-consumption report ZIP: `{summary['recent_review_checkpoints']['mainline_eeg_contract_mapping_consumption']['report_zip_path']}`",
        f"- PSD real-report consumption: `{summary['recent_review_checkpoints']['psd_real_report_consumption']['status']}`",
        f"- PSD real-report evidence: `{summary['recent_review_checkpoints']['psd_real_report_consumption']['path']}`",
        f"- PSD real-report ZIP: `{summary['recent_review_checkpoints']['psd_real_report_consumption']['report_zip_path']}`",
        f"- QC methods real-report consumption: `{summary['recent_review_checkpoints']['qc_real_report_consumption']['status']}`",
        f"- QC methods real-report evidence: `{summary['recent_review_checkpoints']['qc_real_report_consumption']['path']}`",
        f"- QC methods real-report ZIP: `{summary['recent_review_checkpoints']['qc_real_report_consumption']['report_zip_path']}`",
        f"- QC methods real-report warnings: `{summary['recent_review_checkpoints']['qc_real_report_consumption']['warnings']}`",
        f"- PDF OCR-first artifact QA: `{summary['recent_review_checkpoints']['pdf_ocr_artifact_qa']['status']}`",
        f"- PDF OCR-first primary parse: `{summary['recent_review_checkpoints']['pdf_ocr_artifact_qa']['primary_parse']}`",
        f"- PDF OCR-first auxiliary text audit: `{summary['recent_review_checkpoints']['pdf_ocr_artifact_qa']['auxiliary_text_layer_audit']}`",
        f"- PDF OCR-first evidence: `{summary['recent_review_checkpoints']['pdf_ocr_artifact_qa']['path']}`",
        f"- Round 006 PAC real-report consumption: `{summary['recent_review_checkpoints']['round006_pac_real_report_consumption']['status']}`",
        f"- Round 006 PAC real-report evidence: `{summary['recent_review_checkpoints']['round006_pac_real_report_consumption']['path']}`",
        f"- Round 006 PAC real-report ZIP: `{summary['recent_review_checkpoints']['round006_pac_real_report_consumption']['report_zip_path']}`",
        f"- Round 006 TFR real-report consumption: `{summary['recent_review_checkpoints']['round006_tfr_real_report_consumption']['status']}`",
        f"- Round 006 TFR real-report evidence: `{summary['recent_review_checkpoints']['round006_tfr_real_report_consumption']['path']}`",
        f"- Round 006 TFR real-report ZIP: `{summary['recent_review_checkpoints']['round006_tfr_real_report_consumption']['report_zip_path']}`",
        f"- Round 007 preprocessing/ICA/epoch real-report consumption: `{summary['recent_review_checkpoints']['round007_preprocessing_real_report_consumption']['status']}`",
        f"- Round 007 preprocessing/ICA/epoch evidence: `{summary['recent_review_checkpoints']['round007_preprocessing_real_report_consumption']['path']}`",
        f"- Round 007 preprocessing/ICA/epoch report ZIP: `{summary['recent_review_checkpoints']['round007_preprocessing_real_report_consumption']['report_zip_path']}`",
        f"- Round 008 ERP real-report consumption: `{summary['recent_review_checkpoints']['round008_erp_real_report_consumption']['status']}`",
        f"- Round 008 ERP real-report evidence: `{summary['recent_review_checkpoints']['round008_erp_real_report_consumption']['path']}`",
        f"- Round 008 ERP real-report ZIP: `{summary['recent_review_checkpoints']['round008_erp_real_report_consumption']['report_zip_path']}`",
        f"- V01 no group/statistics boundary: `{summary['recent_review_checkpoints']['v01_no_group_statistics_boundary']['status']}`",
        f"- V01 no group/statistics boundary evidence: `{summary['recent_review_checkpoints']['v01_no_group_statistics_boundary']['path']}`",
        f"- V01 no group/statistics boundary ZIP: `{summary['recent_review_checkpoints']['v01_no_group_statistics_boundary']['report_zip_path']}`",
        f"- P0 fixture validator contract: `{summary['recent_review_checkpoints']['p0_fixture_validator_contract']['status']}`",
        f"- P0 fixture validator evidence: `{summary['recent_review_checkpoints']['p0_fixture_validator_contract']['path']}`",
        f"- P0 gap-repair contract: `{summary['recent_review_checkpoints']['p0_gap_repair_contract']['status']}`",
        f"- P0 gap-repair evidence: `{summary['recent_review_checkpoints']['p0_gap_repair_contract']['path']}`",
        f"- P0 gap-repair checkpoint: `{summary['recent_review_checkpoints']['p0_gap_repair_contract']['checkpoint_path']}`",
        f"- Module-lab preview selectors: `{summary['recent_review_checkpoints']['module_lab_preview_selectors']['status']}`",
        f"- Module-lab preview selector evidence: `{summary['recent_review_checkpoints']['module_lab_preview_selectors']['path']}`",
        f"- 07A review-system packet acceptance: `{summary['recent_review_checkpoints']['review_system_packet']['status']}`",
        f"- 07A review-system packet verdict: `{summary['recent_review_checkpoints']['review_system_packet']['verdict']}`",
        f"- 07A review-system evidence: `{summary['recent_review_checkpoints']['review_system_packet']['markdown_path']}`",
        f"- 07A review-system QA table: `{summary['recent_review_checkpoints']['review_system_packet']['qa_table']}`",
        f"- 07A review-system fix plan: `{summary['recent_review_checkpoints']['review_system_packet']['fix_plan']}`",
        f"- 07A UI interaction blockers: `{summary['recent_review_checkpoints']['review_system_packet']['interaction_blockers']}`",
        f"- 07A UI visual blockers: `{summary['recent_review_checkpoints']['review_system_packet']['visual_blockers']}`",
        f"- 07A code files reviewed: `{summary['recent_review_checkpoints']['review_system_packet']['code_files_reviewed']}`",
        f"- 07A code-reviewable rule count: `{summary['recent_review_checkpoints']['review_system_packet']['code_reviewable_rule_count']}`",
        f"- 07A all-scope UI evidence: `{summary['recent_review_checkpoints']['review_system_packet']['all_scope_ui_evidence'].get('status')}`",
        f"- 07A all-scope UI modules: `{summary['recent_review_checkpoints']['review_system_packet']['all_scope_ui_evidence'].get('module_ids')}`",
        f"- 07A all-scope task post count: `{summary['recent_review_checkpoints']['review_system_packet']['all_scope_ui_evidence'].get('task_post_count')}`",
        f"- 07A all-scope UI evidence path: `{summary['recent_review_checkpoints']['review_system_packet']['all_scope_ui_evidence'].get('runner_path')}`",
        f"- Boundary: {summary['recent_review_checkpoints']['boundary']}",
        "",
        "## Cloud / External Gates",
        "",
        f"- Preflight: `{summary['cloud_gates']['preflight_status']}`",
        f"- Todo: `{summary['cloud_gates']['todo_count']}`",
        f"- Failed: `{summary['cloud_gates']['failed_count']}`",
        f"- Owner decision packet: `{summary['cloud_gates']['owner_decision_packet']}`",
        f"- Owner decision acceptance: `{summary['cloud_gates']['owner_decision_acceptance']['status']}`",
        f"- Owner decision acceptance path: `{summary['cloud_gates']['owner_decision_acceptance']['path']}`",
        "",
        "Todo gates:",
        "",
    ]
    lines.extend([f"- `{name}`" for name in summary["cloud_gates"]["todo_names"]])
    lines.extend([
        "",
        "Owner checklist:",
        "",
        f"`{summary['cloud_gates']['owner_checklist']}`",
        "",
        "Commands after inputs are set:",
        "",
    ])
    for command in summary["cloud_gates"]["next_commands"]:
        lines.extend(["```powershell", command, "```", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build QLanalyser V01 release gate summary from current evidence.")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    args = parser.parse_args()

    summary = summarize()
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(output_md, summary)
    print(json.dumps({
        "status": "passed",
        "release_status": summary["status"],
        "output_json": str(output_json),
        "output_md": str(output_md),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
