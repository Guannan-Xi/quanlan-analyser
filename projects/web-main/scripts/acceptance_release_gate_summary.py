from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_gate_summary.json"
SUMMARY_MD = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_gate_summary.md"


def main() -> int:
    payload = json.loads(SUMMARY.read_text(encoding="utf-8"))
    markdown = SUMMARY_MD.read_text(encoding="utf-8")
    cloud_gates = payload.get("cloud_gates", {})
    owner_decision_acceptance = cloud_gates.get("owner_decision_acceptance", {})
    local_gates = payload.get("local_gates", {})
    requirement_matrix = local_gates.get("requirement_matrix", {})
    release_gate_steps = local_gates.get("release_gate_steps", {})
    manifest_consistency = local_gates.get("manifest_consistency", {})
    public_ecs_sandbox_review = local_gates.get("public_ecs_sandbox_review", {})
    visual_layout_design_spec = local_gates.get("visual_layout_design_spec", {})
    stage_gated_review_policy = local_gates.get("stage_gated_review_policy", {})
    report_artifact_label_readability = local_gates.get("report_artifact_label_readability", {})
    latest_checkpoint_access = local_gates.get("latest_checkpoint_access", {})
    recent_checkpoints = payload.get("recent_review_checkpoints", {})
    review_access_checkpoint = recent_checkpoints.get("review_access_checkpoint_packet", {})
    mainline_eeg_review = recent_checkpoints.get("mainline_eeg_module_expert_review", {})
    mainline_eeg_contract_mapping = recent_checkpoints.get("mainline_eeg_contract_mapping_checkpoint", {})
    mainline_eeg_contract_consumption = recent_checkpoints.get("mainline_eeg_contract_mapping_consumption", {})
    psd_real_report_consumption = recent_checkpoints.get("psd_real_report_consumption", {})
    qc_real_report_consumption = recent_checkpoints.get("qc_real_report_consumption", {})
    pdf_ocr_artifact_qa = recent_checkpoints.get("pdf_ocr_artifact_qa", {})
    round006_pac_real_report_consumption = recent_checkpoints.get("round006_pac_real_report_consumption", {})
    round006_tfr_real_report_consumption = recent_checkpoints.get("round006_tfr_real_report_consumption", {})
    round007_preprocessing_real_report_consumption = recent_checkpoints.get("round007_preprocessing_real_report_consumption", {})
    round008_erp_real_report_consumption = recent_checkpoints.get("round008_erp_real_report_consumption", {})
    v01_no_group_statistics_boundary = recent_checkpoints.get("v01_no_group_statistics_boundary", {})
    p0_fixture_validator_contract = recent_checkpoints.get("p0_fixture_validator_contract", {})
    p0_gap_repair_contract = recent_checkpoints.get("p0_gap_repair_contract", {})
    module_lab_preview_selectors = recent_checkpoints.get("module_lab_preview_selectors", {})
    review_system_packet = recent_checkpoints.get("review_system_packet", {})
    all_scope_ui_evidence = review_system_packet.get("all_scope_ui_evidence", {})
    expected_all_scope_modules = {
        "qc",
        "psd",
        "erp",
        "tfr",
        "pac",
        "reference_csd",
        "multitaper_psd_tfr",
        "connectivity",
    }
    checks = {
        "status_blocked_external_inputs": payload.get("status") == "blocked_external_inputs",
        "local_ready_true": payload.get("local_sandbox_review_ready") is True,
        "public_ecs_sandbox_review_ready": payload.get("public_ecs_sandbox_review_ready") is True
        and public_ecs_sandbox_review.get("ready") is True,
        "cloud_ready_false": payload.get("public_cloud_ready") is False,
        "todo_count_positive": cloud_gates.get("todo_count", 0) > 0,
        "bandpower_present": payload.get("local_gates", {}).get("preset_analysis", {}).get("bandpowerOutputsPresent") is True,
        "visual_layout_design_spec_passed": visual_layout_design_spec.get("status") == "passed"
        and visual_layout_design_spec.get("numeric_layout_budget") is True,
        "requirement_matrix_passed_with_external_boundaries": requirement_matrix.get("status") == "passed_with_external_boundaries",
        "requirement_matrix_count_at_least_22": requirement_matrix.get("requirement_count", 0) >= 22,
        "requirement_matrix_no_failed_requirements": requirement_matrix.get("failed_requirements") == [],
        "requirement_matrix_external_boundary": requirement_matrix.get("external_boundaries") == ["aliyun_provider_boundary"],
        "release_gate_steps_passed": release_gate_steps.get("status") == "passed",
        "release_gate_core_steps_count_at_least_27": release_gate_steps.get("step_count", 0) >= 27,
        "release_gate_steps_no_missing": release_gate_steps.get("missing_steps") == [],
        "release_gate_steps_no_failed": release_gate_steps.get("unexpected_failed_steps") == [],
        "utf8_text_preflight_passed": local_gates.get("utf8_text_preflight", {}).get("status") == "passed",
        "utf8_text_preflight_rejects_non_utf8": local_gates.get("utf8_text_preflight", {}).get("rejects_non_utf8_text") is True,
        "utf8_text_preflight_rejects_question_marks": local_gates.get("utf8_text_preflight", {}).get("rejects_literal_question_marks") is True,
        "analysis_module_contract_passed": local_gates.get("analysis_module_contract", {}).get("status") == "passed",
        "cro_traceability_contract_passed": local_gates.get("cro_traceability_contract", {}).get("status") == "passed",
        "stage_gated_review_policy_passed": stage_gated_review_policy.get("status") == "passed",
        "stage_gated_review_policy_environments_present": len(stage_gated_review_policy.get("required_environments", [])) >= 7,
        "report_artifact_label_readability_passed": report_artifact_label_readability.get("status") == "passed",
        "report_artifact_label_readability_no_issues": report_artifact_label_readability.get("issues") == [],
        "latest_checkpoint_access_passed": latest_checkpoint_access.get("status") == "passed",
        "manifest_consistency_passed": manifest_consistency.get("status") == "passed",
        "manifest_consistency_no_missing_readiness_keys": manifest_consistency.get("missing_readiness_keys") == [],
        "manifest_consistency_no_wrong_targets": manifest_consistency.get("wrong_targets") == [],
        "manifest_consistency_no_missing_evidence_entries": manifest_consistency.get("missing_evidence_entries") == [],
        "manifest_consistency_no_missing_files": manifest_consistency.get("missing_files") == [],
        "manifest_consistency_no_missing_or_bad_summary": manifest_consistency.get("missing_or_bad_summary") == [],
        "owner_decision_packet_present": bool(cloud_gates.get("owner_decision_packet")),
        "owner_decision_acceptance_passed": owner_decision_acceptance.get("status") == "passed",
        "owner_decision_preflight_blocked_without_failures": owner_decision_acceptance.get("preflight_blocked_without_failures") is True,
        "review_access_checkpoint_passed": review_access_checkpoint.get("status") == "passed",
        "mainline_eeg_review_conditional_pass": mainline_eeg_review.get("verdict") == "CONDITIONAL PASS",
        "mainline_eeg_review_not_release_pass": mainline_eeg_review.get("release_pass") is False,
        "mainline_eeg_contract_mapping_ready": mainline_eeg_contract_mapping.get("status") == "ready_for_07_review",
        "mainline_eeg_contract_consumption_passed": mainline_eeg_contract_consumption.get("status") == "passed",
        "mainline_eeg_contract_consumption_report_zip_present": bool(mainline_eeg_contract_consumption.get("report_zip_path")),
        "mainline_eeg_contract_consumption_report_zip_complete": mainline_eeg_contract_consumption.get("report_zip_missing_required_entries") == [],
        "psd_real_report_consumption_passed": psd_real_report_consumption.get("status") == "passed",
        "psd_real_report_consumption_vr_eo_0003": psd_real_report_consumption.get("requirement_id") == "VR-EO-0003",
        "psd_real_report_consumption_no_blockers": psd_real_report_consumption.get("blockers") == [],
        "psd_real_report_consumption_report_zip_present": bool(psd_real_report_consumption.get("report_zip_path")),
        "qc_real_report_consumption_passed": qc_real_report_consumption.get("status") == "passed",
        "qc_real_report_consumption_vr_eo_0014_methods": qc_real_report_consumption.get("requirement_id") == "VR-EO-0014-qc-methods-report-consumption",
        "qc_real_report_consumption_no_blockers": qc_real_report_consumption.get("blockers") == [],
        "qc_real_report_consumption_report_zip_present": bool(qc_real_report_consumption.get("report_zip_path")),
        "qc_real_report_consumption_boundary_visible": "does not certify clinical data quality" in str(qc_real_report_consumption.get("boundary")),
        "pdf_ocr_artifact_qa_passed": pdf_ocr_artifact_qa.get("status") == "passed",
        "pdf_ocr_artifact_qa_primary_parse": pdf_ocr_artifact_qa.get("primary_parse") == "PaddleOCR_all_pages",
        "pdf_ocr_artifact_qa_auxiliary_text_audit": pdf_ocr_artifact_qa.get("auxiliary_text_layer_audit") == "yes",
        "pdf_ocr_artifact_qa_verdict_pass": pdf_ocr_artifact_qa.get("artifact_validator_verdict") == "pass",
        "pdf_ocr_artifact_qa_no_blockers": pdf_ocr_artifact_qa.get("blockers") == [],
        "pdf_ocr_artifact_qa_report_zip_present": bool(pdf_ocr_artifact_qa.get("report_zip_path")),
        "pdf_ocr_artifact_qa_boundary_visible": "not release pass" in str(pdf_ocr_artifact_qa.get("boundary")),
        "round006_pac_real_report_consumption_passed": round006_pac_real_report_consumption.get("status") == "passed",
        "round006_pac_real_report_consumption_vr_eo_0019": round006_pac_real_report_consumption.get("requirement_id") == "VR-EO-0019",
        "round006_pac_real_report_consumption_no_blockers": round006_pac_real_report_consumption.get("blockers") == [],
        "round006_pac_real_report_consumption_report_zip_present": bool(round006_pac_real_report_consumption.get("report_zip_path")),
        "round006_tfr_real_report_consumption_passed": round006_tfr_real_report_consumption.get("status") == "passed",
        "round006_tfr_real_report_consumption_vr_eo_0017": round006_tfr_real_report_consumption.get("requirement_id") == "VR-EO-0017",
        "round006_tfr_real_report_consumption_no_blockers": round006_tfr_real_report_consumption.get("blockers") == [],
        "round006_tfr_real_report_consumption_report_zip_present": bool(round006_tfr_real_report_consumption.get("report_zip_path")),
        "round007_preprocessing_real_report_consumption_passed": round007_preprocessing_real_report_consumption.get("status") == "passed",
        "round007_preprocessing_real_report_consumption_vr_eo_0020_0021_0022": round007_preprocessing_real_report_consumption.get("requirement_ids") == ["VR-EO-0020", "VR-EO-0021", "VR-EO-0022"],
        "round007_preprocessing_real_report_consumption_no_blockers": round007_preprocessing_real_report_consumption.get("blockers") == [],
        "round007_preprocessing_real_report_consumption_report_zip_present": bool(round007_preprocessing_real_report_consumption.get("report_zip_path")),
        "round008_erp_real_report_consumption_passed": round008_erp_real_report_consumption.get("status") == "passed",
        "round008_erp_real_report_consumption_vr_eo_0023": round008_erp_real_report_consumption.get("requirement_id") == "VR-EO-0023",
        "round008_erp_real_report_consumption_no_blockers": round008_erp_real_report_consumption.get("blockers") == [],
        "round008_erp_real_report_consumption_report_zip_present": bool(round008_erp_real_report_consumption.get("report_zip_path")),
        "v01_no_group_statistics_boundary_passed": v01_no_group_statistics_boundary.get("status") == "passed",
        "v01_no_group_statistics_boundary_no_blockers": v01_no_group_statistics_boundary.get("blockers") == [],
        "v01_no_group_statistics_boundary_report_zip_present": bool(v01_no_group_statistics_boundary.get("report_zip_path")),
        "p0_fixture_validator_contract_passed": p0_fixture_validator_contract.get("status") == "passed",
        "p0_fixture_validator_contract_no_failures": p0_fixture_validator_contract.get("failures") == [],
        "p0_fixture_validator_contract_fixture_dir_present": bool(p0_fixture_validator_contract.get("fixture_dir")),
        "p0_gap_repair_contract_passed": p0_gap_repair_contract.get("status") == "passed",
        "p0_gap_repair_contract_no_failures": p0_gap_repair_contract.get("failures") == [],
        "p0_gap_repair_contract_not_blocked_by_this_contract": p0_gap_repair_contract.get("product_gate_status") == "not_blocked_by_this_contract",
        "p0_gap_repair_contract_checkpoint_present": bool(p0_gap_repair_contract.get("checkpoint_path")),
        "module_lab_preview_selectors_passed": module_lab_preview_selectors.get("status") == "passed",
        "module_lab_preview_selectors_count_matches_expected": (
            module_lab_preview_selectors.get("preview_count")
            == module_lab_preview_selectors.get("expected_count")
        ),
        "review_system_packet_acceptance_passed": review_system_packet.get("status") == "passed",
        "review_system_packet_verdict_pass": review_system_packet.get("verdict") == "pass",
        "review_system_packet_no_ui_blockers": review_system_packet.get("interaction_blockers") == []
        and review_system_packet.get("visual_blockers") == [],
        "review_system_packet_has_code_files": len(review_system_packet.get("code_files_reviewed", [])) >= 3,
        "review_system_packet_has_code_reviewable_rules": review_system_packet.get("code_reviewable_rule_count", 0) >= 1,
        "review_system_packet_all_scope_status_passed": all_scope_ui_evidence.get("status") == "passed",
        "review_system_packet_all_scope_runner_passed": all_scope_ui_evidence.get("runner_status") == "passed",
        "review_system_packet_all_scope_scope_all": all_scope_ui_evidence.get("module_scope") == "all",
        "review_system_packet_all_scope_task_post_count_8": all_scope_ui_evidence.get("task_post_count") == 8,
        "review_system_packet_all_scope_errors_empty": all_scope_ui_evidence.get("errors") == [],
        "review_system_packet_all_scope_modules_complete": set(all_scope_ui_evidence.get("module_ids", [])) == expected_all_scope_modules,
        "review_system_packet_all_scope_runner_path_exists": bool(all_scope_ui_evidence.get("runner_path"))
        and Path(str(all_scope_ui_evidence.get("runner_path"))).exists(),
        "review_system_packet_all_scope_acceptance_path_exists": bool(all_scope_ui_evidence.get("acceptance_path"))
        and Path(str(all_scope_ui_evidence.get("acceptance_path"))).exists(),
        "review_system_packet_all_scope_screenshot_exists": bool(all_scope_ui_evidence.get("screenshot"))
        and Path(str(all_scope_ui_evidence.get("screenshot"))).exists(),
        "markdown_recent_review_checkpoints_visible": "Recent Review Checkpoints" in markdown,
        "markdown_review_access_checkpoint_visible": "2026-06-22-review-access-validator-contract-fully-verified.md" in markdown,
        "markdown_mainline_eeg_review_visible": "2026-06-22-mainline-eeg-module-expert-review.md" in markdown,
        "markdown_mainline_eeg_contract_mapping_visible": "2026-06-22-07a-mainline-eeg-contract-mapping.md" in markdown,
        "markdown_mainline_eeg_contract_consumption_visible": "mainline_eeg_contract_mapping_consumption.json" in markdown,
        "markdown_psd_real_report_consumption_visible": "psd_real_report_consumption.json" in markdown,
        "markdown_qc_real_report_consumption_visible": "qc_real_report_consumption.json" in markdown,
        "markdown_pdf_ocr_artifact_qa_visible": "pdf_ocr_artifact_qa.json" in markdown
        and "PaddleOCR_all_pages" in markdown,
        "markdown_round006_pac_real_report_consumption_visible": "pac_real_report_consumption.json" in markdown,
        "markdown_round006_tfr_real_report_consumption_visible": "tfr_real_report_consumption.json" in markdown,
        "markdown_round007_preprocessing_real_report_consumption_visible": "round_007_real_report_consumption.json" in markdown,
        "markdown_round008_erp_real_report_consumption_visible": "erp_real_report_consumption.json" in markdown,
        "markdown_v01_no_group_statistics_boundary_visible": "v01_no_group_statistics_boundary.json" in markdown,
        "markdown_p0_fixture_validator_contract_visible": "acceptance_p0_fixture_validator_contract.json" in markdown,
        "markdown_p0_gap_repair_contract_visible": "acceptance_p0_gap_repair_contract.json" in markdown,
        "markdown_module_lab_preview_selectors_visible": "module_lab_preview_selectors" in markdown or "Module-lab preview selectors" in markdown,
        "markdown_review_system_packet_visible": "07A review-system packet verdict" in markdown
        and "review_packet.md" in markdown
        and "code-reviewable rule count" in markdown,
        "markdown_all_scope_ui_evidence_visible": "07A all-scope UI evidence" in markdown
        and "07A all-scope task post count" in markdown,
        "markdown_safe_claim": "Safe claim" in markdown and "blocked" in markdown.lower(),
        "markdown_owner_decision_visible": "Owner decision packet" in markdown and "Owner decision acceptance" in markdown,
        "markdown_release_gate_steps_visible": "Core release gate status at summary build" in markdown,
        "markdown_utf8_text_preflight_visible": "UTF-8 text preflight" in markdown,
        "markdown_visual_layout_design_spec_visible": "Visual layout DESIGN_SPEC" in markdown,
        "markdown_analysis_module_contract_visible": "Analysis module contract" in markdown,
        "markdown_cro_traceability_contract_visible": "CRO traceability contract" in markdown,
        "markdown_stage_gated_review_policy_visible": "Stage-gated review policy" in markdown,
        "markdown_report_artifact_label_readability_visible": "Report artifact label readability" in markdown,
        "markdown_latest_checkpoint_access_visible": "Latest checkpoint access" in markdown,
        "markdown_public_ecs_sandbox_review_visible": "Public ECS sandbox review" in markdown
        and "PUBLIC_DEPLOYMENT_EVIDENCE.md" in markdown
        and "acceptance_ops_ui_public_after_deploy.json" in markdown,
        "markdown_manifest_consistency_visible": "Manifest consistency" in markdown,
    }
    result = {
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "summary": str(SUMMARY),
        "summary_md": str(SUMMARY_MD),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
