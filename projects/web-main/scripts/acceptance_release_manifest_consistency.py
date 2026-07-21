from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "evidence_manifest.json"
OUTPUT = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_release_manifest_consistency.json"

REQUIRED_READINESS_KEYS = {
    "strict_preflight": ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "aliyun_staging_preflight.json",
    "owner_input_checklist": ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "owner_input_checklist.md",
    "owner_decision_packet": ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "owner_decision_packet.md",
    "owner_decision_acceptance": ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_owner_decision_packet.json",
    "completion_audit": ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "production_goal_completion_audit.md",
    "requirement_matrix": ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "production_goal_requirement_matrix.json",
    "release_gate_run": ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_review_gate_run.json",
    "release_gate_core": ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_review_gate_run.core.json",
    "release_gate_steps": ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_release_review_gate_steps.json",
    "utf8_text_preflight": ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_utf8_text_preflight.json",
    "visual_layout_design_spec": ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_visual_layout_design_spec.json",
    "analysis_module_contract": ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_analysis_module_contract.json",
    "cro_traceability_contract": ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_cro_traceability_contract.json",
    "manifest_consistency": ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_release_manifest_consistency.json",
    "public_deployment_evidence": ROOT / "work" / "release_evidence" / "20260620-v01-public" / "PUBLIC_DEPLOYMENT_EVIDENCE.md",
    "public_ops_ui_after_deploy": ROOT / "work" / "release_evidence" / "20260620-v01-public" / "acceptance_ops_ui_public_after_deploy.json",
    "review_access_checkpoint_packet": ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-review-access-validator-contract-fully-verified.json",
    "review_access_checkpoint_packet_md": ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-review-access-validator-contract-fully-verified.md",
    "mainline_eeg_module_expert_review": ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-mainline-eeg-module-expert-review.json",
    "mainline_eeg_module_expert_review_md": ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-mainline-eeg-module-expert-review.md",
    "mainline_eeg_contract_mapping_checkpoint": ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-07a-mainline-eeg-contract-mapping.json",
    "mainline_eeg_contract_mapping_consumption": ROOT / "work" / "release_evidence" / "mainline_eeg_review" / "mainline_eeg_contract_mapping_consumption.json",
    "psd_real_report_consumption": ROOT / "work" / "release_evidence" / "virtual_reviewer_p0" / "psd_real_report_consumption.json",
    "qc_real_report_consumption": ROOT / "work" / "release_evidence" / "virtual_reviewer_p0" / "qc_real_report_consumption.json",
    "pdf_ocr_artifact_qa": ROOT / "work" / "release_evidence" / "pdf_ocr_artifact_qa" / "pdf_ocr_artifact_qa.json",
    "round006_pac_real_report_consumption": ROOT / "work" / "release_evidence" / "virtual_reviewer_round_006" / "pac_real_report_consumption.json",
    "round006_tfr_real_report_consumption": ROOT / "work" / "release_evidence" / "virtual_reviewer_round_006" / "tfr_real_report_consumption.json",
    "round008_erp_real_report_consumption": ROOT / "work" / "release_evidence" / "virtual_reviewer_round_008" / "erp_real_report_consumption.json",
    "module_lab_all_scope_runner": ROOT / "work" / "release_evidence" / "20260623-module-lab-all-scope-runner" / "module_lab_live_runner_all_2026-06-23-0725.json",
    "module_lab_all_scope_acceptance": ROOT / "work" / "release_evidence" / "20260623-module-lab-all-scope-runner" / "acceptance_module_lab_all_scope_evidence.json",
    "module_lab_all_scope_screenshot": ROOT / "work" / "release_evidence" / "20260623-module-lab-all-scope-runner" / "module_lab_live_runner_all_2026-06-23-0725.png",
}


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    evidence = manifest.get("evidence", [])
    evidence_by_path = {item.get("path"): item for item in evidence}
    readiness = manifest.get("release_readiness_evidence", {})

    missing_readiness_keys = [key for key in REQUIRED_READINESS_KEYS if key not in readiness]
    wrong_targets = []
    missing_evidence_entries = []
    missing_files = []
    missing_or_bad_summary = []

    for key, expected_path in REQUIRED_READINESS_KEYS.items():
        expected_text = str(expected_path)
        actual_text = readiness.get(key)
        if actual_text != expected_text:
            wrong_targets.append({"key": key, "expected": expected_text, "actual": actual_text})
        if not expected_path.exists():
            missing_files.append(expected_text)
        item = evidence_by_path.get(expected_text)
        if item is None:
            missing_evidence_entries.append({"key": key, "path": expected_text})
            continue
        if key in {"release_gate_run", "manifest_consistency"}:
            continue
        summary = item.get("summary", {})
        if summary.get("status") in {None, "missing", "failed"}:
            missing_or_bad_summary.append({"key": key, "path": expected_text, "summary": summary})

    status = (
        "passed"
        if manifest.get("status") == "local_v01_acceptance_passed_with_external_boundaries"
        and not missing_readiness_keys
        and not wrong_targets
        and not missing_evidence_entries
        and not missing_files
        and not missing_or_bad_summary
        else "failed"
    )
    result = {
        "status": status,
        "manifest": str(MANIFEST),
        "evidence_count": len(evidence),
        "required_readiness_keys": sorted(REQUIRED_READINESS_KEYS),
        "missing_readiness_keys": missing_readiness_keys,
        "wrong_targets": wrong_targets,
        "missing_evidence_entries": missing_evidence_entries,
        "missing_files": missing_files,
        "missing_or_bad_summary": missing_or_bad_summary,
        "policy": "Release readiness pointers must match evidence entries and existing files.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
