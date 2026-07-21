from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "evidence_manifest.json"

STRICT_PREFLIGHT_PATH = ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "aliyun_staging_preflight.json"
OWNER_INPUT_CHECKLIST_PATH = ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "owner_input_checklist.md"
OWNER_DECISION_PACKET_PATH = ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "owner_decision_packet.md"
OWNER_DECISION_ACCEPTANCE_PATH = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_owner_decision_packet.json"
COMPLETION_AUDIT_PATH = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "production_goal_completion_audit.md"
REQUIREMENT_MATRIX_PATH = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "production_goal_requirement_matrix.json"
MAINLINE_EEG_BRIDGE_ACCEPTANCE_PATH = ROOT / "work" / "release_evidence" / "mainline_eeg_review" / "mainline_eeg_review_bridge_acceptance.json"
MAINLINE_EEG_BRIDGE_CHECKPOINT_PATH = ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-0502-07a-mainline-eeg-bridge-checkpoint.json"
MAINLINE_EEG_HANDOFF_CHECKPOINT_PATH = ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-0505-07a-mainline-eeg-handoff.json"
MAINLINE_EEG_BRIEF_CHECKPOINT_PATH = ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-0506-07a-mainline-eeg-brief.json"
MAINLINE_EEG_INDEX_CHECKPOINT_PATH = ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-0507-07a-mainline-eeg-index.md"
MAINLINE_EEG_CONTRACT_MAPPING_PATH = ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-07a-mainline-eeg-contract-mapping.json"
MAINLINE_EEG_CONTRACT_CONSUMPTION_PATH = ROOT / "work" / "release_evidence" / "mainline_eeg_review" / "mainline_eeg_contract_mapping_consumption.json"
PSD_REAL_REPORT_CONSUMPTION_PATH = ROOT / "work" / "release_evidence" / "virtual_reviewer_p0" / "psd_real_report_consumption.json"
QC_REAL_REPORT_CONSUMPTION_PATH = ROOT / "work" / "release_evidence" / "virtual_reviewer_p0" / "qc_real_report_consumption.json"
PDF_OCR_ARTIFACT_QA_PATH = ROOT / "work" / "release_evidence" / "pdf_ocr_artifact_qa" / "pdf_ocr_artifact_qa.json"
ROUND006_PAC_REAL_REPORT_CONSUMPTION_PATH = ROOT / "work" / "release_evidence" / "virtual_reviewer_round_006" / "pac_real_report_consumption.json"
ROUND006_TFR_REAL_REPORT_CONSUMPTION_PATH = ROOT / "work" / "release_evidence" / "virtual_reviewer_round_006" / "tfr_real_report_consumption.json"
ROUND008_ERP_REAL_REPORT_CONSUMPTION_PATH = ROOT / "work" / "release_evidence" / "virtual_reviewer_round_008" / "erp_real_report_consumption.json"
V01_NO_GROUP_STATISTICS_BOUNDARY_PATH = ROOT / "work" / "release_evidence" / "virtual_reviewer_round_008" / "v01_no_group_statistics_boundary.json"
P0_FIXTURE_VALIDATOR_CONTRACT_PATH = ROOT / "work" / "release_evidence" / "p0_fixture_validator" / "acceptance_p0_fixture_validator_contract.json"
P0_GAP_REPAIR_CONTRACT_PATH = ROOT / "work" / "release_evidence" / "p0_gap_repair" / "acceptance_p0_gap_repair_contract.json"
REVIEW_SYSTEM_PACKET_PATH = ROOT / "work" / "release_evidence" / "review_system" / "2026-06-22-07a-p0-contract-module-lab" / "review_packet.json"
REVIEW_SYSTEM_QA_TABLE_PATH = ROOT / "work" / "release_evidence" / "review_system" / "2026-06-22-07a-p0-contract-module-lab" / "qa_table.csv"
REVIEW_SYSTEM_FIX_PLAN_PATH = ROOT / "work" / "release_evidence" / "review_system" / "2026-06-22-07a-p0-contract-module-lab" / "fix_plan.md"
REVIEW_SYSTEM_ACCEPTANCE_PATH = ROOT / "work" / "release_evidence" / "review_system" / "2026-06-22-07a-p0-contract-module-lab" / "acceptance_07a_review_system_packet.json"
MODULE_LAB_ALL_SCOPE_RUNNER_PATH = ROOT / "work" / "release_evidence" / "20260623-module-lab-all-scope-runner" / "module_lab_live_runner_all_2026-06-23-0725.json"
MODULE_LAB_ALL_SCOPE_ACCEPTANCE_PATH = ROOT / "work" / "release_evidence" / "20260623-module-lab-all-scope-runner" / "acceptance_module_lab_all_scope_evidence.json"
MODULE_LAB_ALL_SCOPE_SCREENSHOT_PATH = ROOT / "work" / "release_evidence" / "20260623-module-lab-all-scope-runner" / "module_lab_live_runner_all_2026-06-23-0725.png"

RELEASE_EVIDENCE = [
    (
        STRICT_PREFLIGHT_PATH,
        "Aliyun strict preflight blocks public staging until external inputs are present.",
    ),
    (
        OWNER_INPUT_CHECKLIST_PATH,
        "Owner-fillable input checklist generated from the strict preflight todo gates.",
    ),
    (
        OWNER_DECISION_PACKET_PATH,
        "Owner decision packet for Aliyun/provider inputs, verification commands, and evidence sharing boundaries.",
    ),
    (
        OWNER_DECISION_ACCEPTANCE_PATH,
        "Machine check that the owner decision packet preserves cloud inputs, commands, and evidence sharing boundaries.",
    ),
    (
        COMPLETION_AUDIT_PATH,
        "Requirement-by-requirement completion audit with verified local/sandbox evidence and external boundaries.",
    ),
    (
        REQUIREMENT_MATRIX_PATH,
        "Machine-checked requirement matrix proving local/sandbox coverage for the full V01 production goal.",
    ),
    (
        ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "production_goal_requirement_matrix.md",
        "Human-readable requirement matrix for the full V01 production goal.",
    ),
    (
        ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "START_HERE_RELEASE_REVIEW.md",
        "Single entry point for the current release review evidence and safe claim.",
    ),
    (
        ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_gate_summary.json",
        "One-file release gate summary combining local readiness and cloud/provider blockers.",
    ),
    (
        ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_gate_summary.md",
        "Human-readable release gate summary for review.",
    ),
    (
        MAINLINE_EEG_BRIDGE_ACCEPTANCE_PATH,
        "Bridge acceptance JSON for the real_eeg_v01 mainline EEG prototype review packet.",
    ),
    (
        MAINLINE_EEG_BRIDGE_CHECKPOINT_PATH,
        "Checkpoint for the mainline EEG bridge gate.",
    ),
    (
        MAINLINE_EEG_HANDOFF_CHECKPOINT_PATH,
        "Handoff packet for the mainline EEG review evidence chain.",
    ),
    (
        MAINLINE_EEG_BRIEF_CHECKPOINT_PATH,
        "Brief packet for the mainline EEG review evidence chain.",
    ),
    (
        MAINLINE_EEG_INDEX_CHECKPOINT_PATH,
        "Index packet for the mainline EEG review evidence chain.",
    ),
    (
        MAINLINE_EEG_CONTRACT_MAPPING_PATH,
        "Contract mapping packet normalizing the mainline EEG evidence chain for 07 review intake.",
    ),
    (
        MAINLINE_EEG_CONTRACT_CONSUMPTION_PATH,
        "Executable contract-consumption check linking the mainline EEG mapping to the UI runner report artifact contract.",
    ),
    (
        PSD_REAL_REPORT_CONSUMPTION_PATH,
        "Executable real-report consumption check for PSD/bandpower method, frequency range, band/channel tables, lineage, and boundary evidence.",
    ),
    (
        QC_REAL_REPORT_CONSUMPTION_PATH,
        "Executable real-report consumption check for metadata QC, QC waveform/filter preview artifacts, bad-channel audit records, method, parameters, warnings, and non-diagnostic boundary evidence.",
    ),
    (
        PDF_OCR_ARTIFACT_QA_PATH,
        "OCR-first PDF report artifact QA using PaddleOCR on rendered pages with auxiliary native text-layer audit.",
    ),
    (
        ROUND006_PAC_REAL_REPORT_CONSUMPTION_PATH,
        "Executable real-report consumption check for round_006 PAC VR-EO-0019 frequency grids, surrogate/normalization, random state, and source boundary evidence.",
    ),
    (
        ROUND006_TFR_REAL_REPORT_CONSUMPTION_PATH,
        "Executable real-report consumption check for round_006 TFR VR-EO-0017 method, axes, baseline, units, and boundary evidence.",
    ),
    (
        ROUND008_ERP_REAL_REPORT_CONSUMPTION_PATH,
        "Executable real-report consumption check for round_008 ERP VR-EO-0023 baseline, event mapping, drop-log, units, and epoch-count evidence.",
    ),
    (
        V01_NO_GROUP_STATISTICS_BOUNDARY_PATH,
        "Executable V01 boundary check that current UI/report artifacts do not present group statistics, p-values, FDR, cluster permutation, grand-average, or significance as enabled product outputs.",
    ),
    (
        P0_FIXTURE_VALIDATOR_CONTRACT_PATH,
        "Executable P0 synthetic fixture and artifact-validator contract check with positive and negative paths for preprocessing, event/epoch, PSD, and ERP.",
    ),
    (
        P0_GAP_REPAIR_CONTRACT_PATH,
        "Executable P0 gap-repair checkpoint consumer for durable epoch_set evidence and product-gate boundary preservation.",
    ),
    (
        REVIEW_SYSTEM_PACKET_PATH,
        "GPT-5.5/Codex-owned QLanalyser review-system packet tying real artifacts, contract checkers, QA table, fix plan, and integration gate evidence together.",
    ),
    (
        REVIEW_SYSTEM_QA_TABLE_PATH,
        "QA table for the 07A P0 contract checker and module-lab live runner review packet.",
    ),
    (
        REVIEW_SYSTEM_FIX_PLAN_PATH,
        "Fix plan for the 07A P0 contract checker and module-lab live runner review packet.",
    ),
    (
        REVIEW_SYSTEM_ACCEPTANCE_PATH,
        "Machine acceptance for the 07A review-system packet contract.",
    ),
    (
        MODULE_LAB_ALL_SCOPE_RUNNER_PATH,
        "All-scope module-lab live UI runner evidence covering QC, PSD, ERP, TFR, PAC, Reference-CSD, Multitaper, and Connectivity with taskPostCount=8.",
    ),
    (
        MODULE_LAB_ALL_SCOPE_ACCEPTANCE_PATH,
        "Machine acceptance for all-scope module-lab UI runner evidence, requiring scope=all, taskPostCount=8, errors=[], all module ids, and screenshot/readback paths.",
    ),
    (
        MODULE_LAB_ALL_SCOPE_SCREENSHOT_PATH,
        "Browser screenshot captured by the all-scope module-lab live UI runner.",
    ),
    (
        ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_review_gate_run.json",
        "One-command local release review gate run with strict preflight external-input block recorded as expected.",
    ),
    (
        ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_review_gate_run.core.json",
        "Core release review gate snapshot used by the release summary before post-output packaging steps.",
    ),
    (
        ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_release_review_gate_steps.json",
        "Machine check that the one-command release gate preserved every critical review step.",
    ),
    (
        ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_utf8_text_preflight.json",
        "Machine check that persisted text preflight rejects non-UTF-8 files and literal question-mark mojibake.",
    ),
    (
        ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_visual_layout_design_spec.json",
        "Machine check that visual assets require numeric DESIGN_SPEC before rendering and reject overflow, collision, mojibake, and density violations.",
    ),
    (
        ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_analysis_module_contract.json",
        "Machine check that analysis methods are governed by the module lifecycle, schema, artifact, report, and evidence contract.",
    ),
    (
        ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_cro_traceability_contract.json",
        "Machine check that CRO-style traceability, audit, role, report, module, artifact, and non-medical boundaries are governed.",
    ),
    (
        ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_release_manifest_consistency.json",
        "Machine check that release readiness pointers match evidence entries and existing files.",
    ),
    (
        ROOT / "work" / "release_evidence" / "20260620-v01-public" / "PUBLIC_DEPLOYMENT_EVIDENCE.md",
        "Public ECS sandbox review deployment index with public URLs, demo accounts, and strict production-provider boundary.",
    ),
    (
        ROOT / "work" / "release_evidence" / "20260620-v01-public" / "acceptance_ops_ui_public_after_deploy.json",
        "Public ECS sandbox review browser evidence for recharge, invoice, inbox, and admin operations.",
    ),
    (
        ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_no_misclaim.json",
        "Machine check that release artifacts do not claim public cloud or production readiness while strict preflight is blocked.",
    ),
    (
        ROOT / "work" / "release_evidence" / "20260620-v01-sanitized-review-package.json",
        "Portable ZIP package manifest for external-readable sanitized review evidence.",
    ),
    (
        ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-review-access-validator-contract-fully-verified.json",
        "REVIEW_ACCESS checkpoint packet gate with demo credential safety and checkpoint path validation.",
    ),
    (
        ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-review-access-validator-contract-fully-verified.md",
        "Human-readable REVIEW_ACCESS checkpoint packet gate with front-end URL, backend health, demo account, and credential safety boundary.",
    ),
    (
        ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-mainline-eeg-module-expert-review.json",
        "Mainline EEG module expert review checkpoint for QC, PSD/Bandpower, ERP, TFR, and PAC staged integration.",
    ),
    (
        ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-mainline-eeg-module-expert-review.md",
        "Human-readable mainline EEG module expert review with conditional pass, P0/P1/P2 findings, and integration recommendation.",
    ),
    (
        ROOT / "work" / "release_evidence" / "module_lab_preview_selectors" / "acceptance_module_lab_preview_selectors.json",
        "UI-only acceptance for module-lab preview selectors covering CSD, TFR, PAC, and Connectivity beta/preview boundaries.",
    ),
]


def load_summary(path: Path, note: str) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "missing",
            "note": note,
        }
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {
            "status": payload.get("status"),
            "note": note,
        }
    return {
        "status": "present",
        "note": note,
    }


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    evidence = manifest.setdefault("evidence", [])
    existing = {item.get("path"): item for item in evidence}

    for path, note in RELEASE_EVIDENCE:
        path_text = str(path)
        item = {
            "path": path_text,
            "summary": load_summary(path, note),
        }
        if path_text in existing:
            existing[path_text].update(item)
        else:
            evidence.append(item)

    manifest.setdefault("release_readiness_evidence", {})
    manifest["release_readiness_evidence"].update({
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "strict_preflight": str(STRICT_PREFLIGHT_PATH),
        "owner_input_checklist": str(OWNER_INPUT_CHECKLIST_PATH),
        "owner_decision_packet": str(OWNER_DECISION_PACKET_PATH),
        "owner_decision_acceptance": str(OWNER_DECISION_ACCEPTANCE_PATH),
        "completion_audit": str(COMPLETION_AUDIT_PATH),
        "requirement_matrix": str(REQUIREMENT_MATRIX_PATH),
        "release_gate_run": str(ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_review_gate_run.json"),
        "release_gate_core": str(ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_review_gate_run.core.json"),
        "release_gate_steps": str(ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_release_review_gate_steps.json"),
        "utf8_text_preflight": str(ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_utf8_text_preflight.json"),
        "visual_layout_design_spec": str(ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_visual_layout_design_spec.json"),
        "analysis_module_contract": str(ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_analysis_module_contract.json"),
        "cro_traceability_contract": str(ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_cro_traceability_contract.json"),
        "manifest_consistency": str(ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_release_manifest_consistency.json"),
        "public_deployment_evidence": str(ROOT / "work" / "release_evidence" / "20260620-v01-public" / "PUBLIC_DEPLOYMENT_EVIDENCE.md"),
        "public_ops_ui_after_deploy": str(ROOT / "work" / "release_evidence" / "20260620-v01-public" / "acceptance_ops_ui_public_after_deploy.json"),
        "mainline_eeg_bridge_acceptance": str(MAINLINE_EEG_BRIDGE_ACCEPTANCE_PATH),
        "mainline_eeg_bridge_checkpoint": str(MAINLINE_EEG_BRIDGE_CHECKPOINT_PATH),
        "mainline_eeg_handoff_checkpoint": str(MAINLINE_EEG_HANDOFF_CHECKPOINT_PATH),
        "mainline_eeg_brief_checkpoint": str(MAINLINE_EEG_BRIEF_CHECKPOINT_PATH),
        "mainline_eeg_index_checkpoint": str(MAINLINE_EEG_INDEX_CHECKPOINT_PATH),
        "mainline_eeg_contract_mapping_checkpoint": str(MAINLINE_EEG_CONTRACT_MAPPING_PATH),
        "mainline_eeg_contract_mapping_consumption": str(MAINLINE_EEG_CONTRACT_CONSUMPTION_PATH),
        "psd_real_report_consumption": str(PSD_REAL_REPORT_CONSUMPTION_PATH),
        "qc_real_report_consumption": str(QC_REAL_REPORT_CONSUMPTION_PATH),
        "pdf_ocr_artifact_qa": str(PDF_OCR_ARTIFACT_QA_PATH),
        "round006_pac_real_report_consumption": str(ROUND006_PAC_REAL_REPORT_CONSUMPTION_PATH),
        "round006_tfr_real_report_consumption": str(ROUND006_TFR_REAL_REPORT_CONSUMPTION_PATH),
        "round008_erp_real_report_consumption": str(ROUND008_ERP_REAL_REPORT_CONSUMPTION_PATH),
        "v01_no_group_statistics_boundary": str(V01_NO_GROUP_STATISTICS_BOUNDARY_PATH),
        "p0_fixture_validator_contract": str(P0_FIXTURE_VALIDATOR_CONTRACT_PATH),
        "p0_gap_repair_contract": str(P0_GAP_REPAIR_CONTRACT_PATH),
        "review_system_packet": str(REVIEW_SYSTEM_PACKET_PATH),
        "review_system_qa_table": str(REVIEW_SYSTEM_QA_TABLE_PATH),
        "review_system_fix_plan": str(REVIEW_SYSTEM_FIX_PLAN_PATH),
        "review_system_packet_acceptance": str(REVIEW_SYSTEM_ACCEPTANCE_PATH),
        "module_lab_all_scope_runner": str(MODULE_LAB_ALL_SCOPE_RUNNER_PATH),
        "module_lab_all_scope_acceptance": str(MODULE_LAB_ALL_SCOPE_ACCEPTANCE_PATH),
        "module_lab_all_scope_screenshot": str(MODULE_LAB_ALL_SCOPE_SCREENSHOT_PATH),
        "review_access_checkpoint_packet": str(ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-review-access-validator-contract-fully-verified.json"),
        "review_access_checkpoint_packet_md": str(ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-review-access-validator-contract-fully-verified.md"),
        "mainline_eeg_module_expert_review": str(ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-mainline-eeg-module-expert-review.json"),
        "mainline_eeg_module_expert_review_md": str(ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-mainline-eeg-module-expert-review.md"),
        "module_lab_preview_selectors": str(ROOT / "work" / "release_evidence" / "module_lab_preview_selectors" / "acceptance_module_lab_preview_selectors.json"),
    })

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "passed",
        "manifest": str(MANIFEST),
        "release_evidence_count": len(RELEASE_EVIDENCE),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
