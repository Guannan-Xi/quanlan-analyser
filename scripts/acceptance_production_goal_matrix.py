from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance"
OUTPUT_JSON = OUTPUT_DIR / "production_goal_requirement_matrix.json"
OUTPUT_MD = OUTPUT_DIR / "production_goal_requirement_matrix.md"

PATHS = {
    "manifest": OUTPUT_DIR / "evidence_manifest.json",
    "full_api": ROOT / "work" / "acceptance" / "v01_acceptance_latest.json",
    "ops": OUTPUT_DIR / "acceptance_ops_billing_invoice.json",
    "ops_ui": OUTPUT_DIR / "acceptance_ops_ui.json",
    "page_visual": ROOT / "work" / "release_evidence" / "20260620-page-visual-qa" / "page_visual_qa.json",
    "preset": ROOT / "work" / "release_evidence" / "20260620-customer-preset-analysis" / "customer_preset_analysis.json",
    "lab": ROOT / "work" / "release_evidence" / "20260620-module-lab-live-runner" / "module_lab_live_runner.json",
    "queue": OUTPUT_DIR / "acceptance_task_queue_capacity.json",
    "large_200": OUTPUT_DIR / "acceptance_large_upload_10x200mb.json",
    "large_1g": OUTPUT_DIR / "acceptance_large_upload_1x1gb.json",
    "report_zip": ROOT / "work" / "release_evidence" / "20260620-report-zip-evidence-matrix" / "report_zip_evidence_matrix.json",
    "review_gate": OUTPUT_DIR / "release_review_gate_run.core.json",
    "release_gate_steps": OUTPUT_DIR / "acceptance_release_review_gate_steps.json",
    "release_no_misclaim": OUTPUT_DIR / "release_no_misclaim.json",
    "utf8_text_preflight": OUTPUT_DIR / "acceptance_utf8_text_preflight.json",
    "visual_layout_design_spec": OUTPUT_DIR / "acceptance_visual_layout_design_spec.json",
    "analysis_module_contract": OUTPUT_DIR / "acceptance_analysis_module_contract.json",
    "cro_traceability_contract": OUTPUT_DIR / "acceptance_cro_traceability_contract.json",
    "sanitized_acceptance": OUTPUT_DIR / "acceptance_sanitized_review_package.json",
    "sanitized_package": ROOT / "work" / "release_evidence" / "20260620-v01-sanitized-review-package.json",
    "public_ops_ui": ROOT / "work" / "release_evidence" / "20260620-v01-public" / "acceptance_ops_ui_public_after_deploy.json",
    "preflight": ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "aliyun_staging_preflight.json",
    "aliyun_runbook": ROOT / "docs" / "release" / "aliyun_v1_staging_smoke.md",
    "owner_checklist": ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "owner_input_checklist.md",
    "owner_packet": ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "owner_decision_packet.md",
    "owner_packet_acceptance": OUTPUT_DIR / "acceptance_owner_decision_packet.json",
    "p0_ui_evidence": ROOT / "work" / "release_evidence" / "p0_ui_only_runner" / "p0-ui-only-runner-evidence.json",
    "p0_ui_acceptance": ROOT / "work" / "release_evidence" / "p0_ui_only_runner" / "acceptance_p0_ui_only_runner_contract.json",
    "round_005": ROOT / "work" / "release_evidence" / "virtual_reviewer_round_005" / "round_005_dry_run.json",
    "round_006": ROOT / "work" / "release_evidence" / "virtual_reviewer_round_006" / "round_006_dry_run.json",
    "psd_real_report_consumption": ROOT / "work" / "release_evidence" / "virtual_reviewer_p0" / "psd_real_report_consumption.json",
    "qc_real_report_consumption": ROOT / "work" / "release_evidence" / "virtual_reviewer_p0" / "qc_real_report_consumption.json",
    "pdf_ocr_artifact_qa": ROOT / "work" / "release_evidence" / "pdf_ocr_artifact_qa" / "pdf_ocr_artifact_qa.json",
    "round_006_pac_real_report_consumption": ROOT / "work" / "release_evidence" / "virtual_reviewer_round_006" / "pac_real_report_consumption.json",
    "round_006_tfr_real_report_consumption": ROOT / "work" / "release_evidence" / "virtual_reviewer_round_006" / "tfr_real_report_consumption.json",
    "round_007": ROOT / "work" / "release_evidence" / "virtual_reviewer_round_007" / "round_007_dry_run.json",
    "round_008": ROOT / "work" / "release_evidence" / "virtual_reviewer_round_008" / "round_008_dry_run.json",
    "round_008_erp_real_report_consumption": ROOT / "work" / "release_evidence" / "virtual_reviewer_round_008" / "erp_real_report_consumption.json",
    "v01_no_group_statistics_boundary": ROOT / "work" / "release_evidence" / "virtual_reviewer_round_008" / "v01_no_group_statistics_boundary.json",
    "source_integrity_checkpoint": ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-21-2157-bad-channel-source-integrity-checkpoint.json",
    "round_007_checkpoint": ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-21-2203-round007-preprocessing-ica-epoch-checkpoint.json",
    "backup_restore_current_dir": ROOT / "work" / "release_evidence" / "20260621-backup-restore-current",
    "ops_current": ROOT / "work" / "release_evidence" / "20260621-ops-current" / "acceptance_ops_billing_invoice_current.json",
    "large_current_200": ROOT / "work" / "release_evidence" / "20260621-large-upload-current" / "acceptance_large_upload_10x200mb_current.json",
    "large_current_1g": ROOT / "work" / "release_evidence" / "20260621-large-upload-current" / "acceptance_large_upload_1x1gb_current.json",
    "queue_current": ROOT / "work" / "release_evidence" / "20260621-task-queue-current" / "acceptance_task_queue_capacity_current.json",
}

JSON_PATH_KEYS = {
    "manifest",
    "full_api",
    "ops",
    "ops_ui",
    "page_visual",
    "preset",
    "lab",
    "queue",
    "large_200",
    "large_1g",
    "report_zip",
    "review_gate",
    "release_gate_steps",
    "release_no_misclaim",
    "utf8_text_preflight",
    "visual_layout_design_spec",
    "analysis_module_contract",
    "cro_traceability_contract",
    "sanitized_acceptance",
    "sanitized_package",
    "public_ops_ui",
    "preflight",
    "owner_packet_acceptance",
    "p0_ui_evidence",
    "p0_ui_acceptance",
    "round_005",
    "round_006",
    "psd_real_report_consumption",
    "qc_real_report_consumption",
    "pdf_ocr_artifact_qa",
    "round_006_pac_real_report_consumption",
    "round_006_tfr_real_report_consumption",
    "round_007",
    "round_008",
    "round_008_erp_real_report_consumption",
    "v01_no_group_statistics_boundary",
    "source_integrity_checkpoint",
    "round_007_checkpoint",
    "ops_current",
    "large_current_200",
    "large_current_1g",
    "queue_current",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"__missing__": True, "__path__": str(path)}
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def latest_json(directory: Path, pattern: str) -> tuple[Path | None, dict[str, Any]]:
    if not directory.exists():
        return None, {"__missing__": True, "__path__": str(directory), "__pattern__": pattern}
    candidates = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        return None, {"__missing__": True, "__path__": str(directory), "__pattern__": pattern}
    return candidates[0], read_json(candidates[0])


def exists(path_text: str | None) -> bool:
    return bool(path_text) and Path(path_text).exists()


def count_requests(payload: dict[str, Any], method: str, url_suffix: str) -> int:
    return sum(
        1
        for request in payload.get("requests", [])
        if request.get("method") == method and url_suffix in str(request.get("url", ""))
    )


def has_browser_auth_request(payload: dict[str, Any], method: str, pathname: str) -> bool:
    for request in payload.get("browserAuthRequests", []):
        if (
            request.get("method") == method
            and request.get("pathname") == pathname
            and request.get("hasBearer") is True
            and request.get("authorization") == "Bearer <redacted>"
        ):
            return True
    return False


def ops_ui_invoice_closed_loop(payload: dict[str, Any]) -> bool:
    invoice_id = payload.get("invoiceId")
    message_id = payload.get("invoiceMessageId")
    if not invoice_id or not message_id:
        return False
    return (
        payload.get("status") == "passed"
        and payload.get("adminInvoiceUploadControlVisible") is True
        and payload.get("issuedInvoiceStatus") == "issued"
        and payload.get("invoiceAttachmentDownloaded") is True
        and has_browser_auth_request(payload, "POST", f"/api/admin/invoices/{invoice_id}/issue")
        and has_browser_auth_request(payload, "GET", "/api/inbox")
        and has_browser_auth_request(payload, "GET", f"/api/inbox/{message_id}/attachment")
    )


def row(
    requirement: str,
    claim: str,
    ok: bool,
    evidence: list[str],
    status: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    return {
        "requirement": requirement,
        "claim": claim,
        "status": status or ("proved" if ok else "failed"),
        "ok": ok,
        "evidence": evidence,
        "note": note,
    }


def main() -> int:
    data = {name: read_json(PATHS[name]) for name in JSON_PATH_KEYS}
    manifest = data["manifest"]
    full_api = data["full_api"]
    ops = data["ops"]
    ops_ui = data["ops_ui"]
    page_visual = data["page_visual"]
    preset = data["preset"]
    lab = data["lab"]
    queue = data["queue"]
    large_200 = data["large_200"]
    large_1g = data["large_1g"]
    report_zip = data["report_zip"]
    review_gate = data["review_gate"]
    release_gate_steps = data["release_gate_steps"]
    release_no_misclaim = data["release_no_misclaim"]
    utf8_text_preflight = data["utf8_text_preflight"]
    visual_layout_design_spec = data["visual_layout_design_spec"]
    analysis_module_contract = data["analysis_module_contract"]
    cro_traceability_contract = data["cro_traceability_contract"]
    sanitized_acceptance = data["sanitized_acceptance"]
    sanitized_package = data["sanitized_package"]
    public_ops_ui = data["public_ops_ui"]
    preflight = data["preflight"]
    aliyun_runbook_text = read_text(PATHS["aliyun_runbook"])
    owner_checklist_text = read_text(PATHS["owner_checklist"])
    owner_packet_text = read_text(PATHS["owner_packet"])
    owner_packet_acceptance = read_json(PATHS["owner_packet_acceptance"])
    p0_ui_evidence = read_json(PATHS["p0_ui_evidence"])
    p0_ui_acceptance = read_json(PATHS["p0_ui_acceptance"])
    round_005 = read_json(PATHS["round_005"])
    round_006 = read_json(PATHS["round_006"])
    psd_real_report_consumption = read_json(PATHS["psd_real_report_consumption"])
    qc_real_report_consumption = read_json(PATHS["qc_real_report_consumption"])
    pdf_ocr_artifact_qa = read_json(PATHS["pdf_ocr_artifact_qa"])
    round_006_pac_real_report_consumption = read_json(PATHS["round_006_pac_real_report_consumption"])
    round_006_tfr_real_report_consumption = read_json(PATHS["round_006_tfr_real_report_consumption"])
    round_007 = read_json(PATHS["round_007"])
    round_008 = read_json(PATHS["round_008"])
    round_008_erp_real_report_consumption = read_json(PATHS["round_008_erp_real_report_consumption"])
    v01_no_group_statistics_boundary = read_json(PATHS["v01_no_group_statistics_boundary"])
    source_integrity_checkpoint = read_json(PATHS["source_integrity_checkpoint"])
    round_007_checkpoint = read_json(PATHS["round_007_checkpoint"])
    backup_restore_current_path, backup_restore_current = latest_json(
        PATHS["backup_restore_current_dir"],
        "backup_restore_drill_local_*.json",
    )
    ops_current = read_json(PATHS["ops_current"])
    large_current_200 = read_json(PATHS["large_current_200"])
    large_current_1g = read_json(PATHS["large_current_1g"])
    queue_current = read_json(PATHS["queue_current"])

    full_tasks = full_api.get("tasks", {})
    preset_psd = preset.get("checks", {}).get("psd", {})
    preset_erp = preset.get("checks", {}).get("erp", {})
    lab_requests = lab.get("requests", [])
    review_gate_steps = review_gate.get("steps", [])
    review_gate_failed_steps = [step.get("name") for step in review_gate_steps if not step.get("ok")]
    page_pages = set(page_visual.get("pageVisualQa", {}).get("pages", []))
    if not page_pages:
        page_pages = {state.get("page") for state in page_visual.get("states", []) if state.get("page")}

    requirements = [
        row(
            "customer_register_login",
            "Email, phone, and WeChat registration/login are available in sandbox evidence.",
            ops.get("status") == "passed"
            and ops.get("email_provider_mode") == "sandbox"
            and ops.get("phone_provider_mode") == "sandbox"
            and bool(ops.get("wechat_account_id")),
            [str(PATHS["ops"])],
        ),
        row(
            "sandbox_payment_wallet_deduction",
            "Alipay and WeChat sandbox recharge, wallet balance, ledger, usage records, and deduction evidence exist.",
            ops.get("status") == "passed"
            and set(ops.get("payment_modes", [])) >= {"alipay_sandbox", "wechat_pay_sandbox"}
            and float(ops.get("wallet_balance", 0)) > 0
            and int(ops.get("wallet_transaction_count", 0)) >= 2
            and queue.get("usage_records") == 50,
            [str(PATHS["ops"]), str(PATHS["queue"])],
        ),
        row(
            "invoice_admin_inbox",
            "Customer invoice submission, admin issuance/upload, and customer inbox PDF delivery are proved by API and browser evidence.",
            ops.get("status") == "passed"
            and ops.get("invoice_status") == "issued"
            and ops.get("invoice_file_name") == "invoice.pdf"
            and int(ops.get("inbox_messages", 0)) >= 1
            and int(ops.get("admin_issued_invoices", 0)) >= 1
            and ops_ui_invoice_closed_loop(ops_ui),
            [str(PATHS["ops"]), str(PATHS["ops_ui"])],
        ),
        row(
            "rbac_admin_boundaries",
            "Admin-only and cross-account negative checks protect operational pages and APIs.",
            ops.get("status") == "passed" and len(ops.get("rbac_negative_checks", [])) >= 10,
            [str(PATHS["ops"])],
        ),
        row(
            "main_upload_analysis_report_zip",
            "Formal customer UI can create a project, upload EEG, run QC/PSD/ERP, create report, and download ZIP.",
            full_api.get("status") == "passed"
            and {"qc", "psd", "erp"} <= set(full_tasks.keys())
            and exists(full_api.get("package_path")),
            [str(PATHS["full_api"]), str(PATHS["report_zip"])],
        ),
        row(
            "preprocessing_qc_real_execution",
            "QC/preprocessing path produces a completed real task in the core flow.",
            full_api.get("status") == "passed" and bool(full_tasks.get("qc")),
            [str(PATHS["full_api"])],
        ),
        row(
            "psd_bandpower_real_execution",
            "PSD and bandpower run through real tasks and export band_power plus channel_band_power CSV artifacts.",
            preset.get("status") == "passed"
            and preset_psd.get("taskCompleted") is True
            and preset_psd.get("bandpowerOutputsPresent") is True
            and {"band_power", "channel_band_power"}
            <= {artifact.get("label") for artifact in preset_psd.get("bandpowerArtifacts", [])},
            [str(PATHS["preset"])],
        ),
        row(
            "erp_p300_real_execution",
            "ERP/P300 preset flow submits parameters, links the preparation plan, completes a task, and exposes downloads.",
            preset.get("status") == "passed"
            and preset_erp.get("taskCompleted") is True
            and preset_erp.get("parametersSubmitted") is True
            and preset_erp.get("planLinked") is True
            and int(preset_erp.get("downloadLinks", 0)) > 0,
            [str(PATHS["preset"])],
        ),
        row(
            "analysis_lab_live_runner",
            "Analysis lab has real customer-file inputs and executes QC, PSD/bandpower, and ERP/P300 backend tasks instead of static screenshots/text.",
            bool(lab.get("checks", {}).get("uploadedFileId"))
            and bool(lab.get("checks", {}).get("selectedFileId"))
            and lab.get("checks", {}).get("customerFileSelected") is True
            and lab.get("checks", {}).get("uploadedFileSelected") is True
            and count_requests(lab, "POST", "/api/eeg/upload") >= 1
            and count_requests(lab, "POST", "/api/tasks") >= 3
            and all(
                lab.get("moduleChecks", {}).get(module, {}).get("passed") is True
                and lab.get("moduleChecks", {}).get(module, {}).get("taskUsesSelectedFile") is True
                and int(lab.get("moduleChecks", {}).get(module, {}).get("downloadLinks", 0)) > 0
                for module in ("qc", "psd", "erp")
            )
            and any(req.get("method") == "POST" and "/api/eeg/upload" in req.get("url", "") for req in lab_requests),
            [str(PATHS["lab"])],
            note="Scoped to QC/PSD/ERP evidence. TFR/PAC beta runner failures must be tracked by their beta gates, not this P0 matrix row.",
        ),
        row(
            "preset_analysis_customer_page",
            "Preset analysis customer path is wired to current-task artifacts and not only static method cards.",
            preset.get("status") == "passed"
            and preset_psd.get("taskCompleted") is True
            and preset_erp.get("taskCompleted") is True
            and not preset.get("errors"),
            [str(PATHS["preset"])],
        ),
        row(
            "page_visual_qa_customer_admin",
            "Customer and admin pages pass desktop/mobile/narrow page visual QA with screenshot evidence.",
            page_visual.get("status") == "passed"
            and page_visual.get("pageVisualQa", {}).get("pass") is True
            and int(page_visual.get("pageVisualQa", {}).get("pageCount", 0)) >= 15
            and int(page_visual.get("pageVisualQa", {}).get("viewportCount", 0)) >= 3
            and {
                "customer-login",
                "customer-register-email",
                "customer-register-phone",
                "customer-register-wechat",
                "customer-billing",
                "customer-invoice",
                "customer-inbox-empty",
                "customer-report-download",
                "lab-workbench",
                "preset-analysis-library",
                "admin-overview",
                "admin-operations",
                "admin-finance",
            }
            <= page_pages,
            [str(PATHS["page_visual"])],
        ),
        row(
            "capacity_10_users_50_tasks",
            "Local queue-ready capacity evidence covers 10 users, 50 completed tasks, audit events, and usage records.",
            queue.get("status") == "passed"
            and queue.get("users") == 10
            and queue.get("tasks") == 50
            and queue.get("completed") == 50
            and queue.get("distinct_task_owners") == 10
            and queue.get("audit_completed_events") == 50
            and queue.get("usage_records") == 50,
            [str(PATHS["queue"])],
        ),
        row(
            "large_upload_capacity",
            "Upload evidence covers 10 users at 200MB and one 1GB upload.",
            large_200.get("status") == "passed"
            and large_200.get("users") == 10
            and large_200.get("actual_mb_per_upload") == 200
            and len(large_200.get("files", [])) == 10
            and large_1g.get("status") == "passed"
            and large_1g.get("actual_mb_per_upload") == 1024
            and len(large_1g.get("files", [])) == 1,
            [str(PATHS["large_200"]), str(PATHS["large_1g"])],
        ),
        row(
            "sanitized_external_review_package",
            "External-readable review ZIP exists and sanitized-package acceptance has sensitive findings empty.",
            sanitized_package.get("status") == "passed"
            and sanitized_acceptance.get("status") == "passed"
            and sanitized_acceptance.get("missing") == []
            and sanitized_acceptance.get("sensitive_findings") == [],
            [str(PATHS["sanitized_package"]), str(PATHS["sanitized_acceptance"])],
        ),
        row(
            "local_release_review_gate",
            "Independent local release gate core prerequisites are present before the post-output packaging steps run.",
            review_gate.get("status") == "passed"
            and len(review_gate_steps) >= 10
            and review_gate_failed_steps == []
            and any(step.get("name") == "accept_utf8_text_preflight" for step in review_gate_steps)
            and any(step.get("name") == "accept_analysis_module_contract" for step in review_gate_steps)
            and any(step.get("name") == "accept_cro_traceability_contract" for step in review_gate_steps),
            [str(PATHS["review_gate"])],
        ),
        row(
            "public_ecs_sandbox_review_deployment",
            "Public ECS sandbox review deployment is smoke-tested separately from strict production provider readiness.",
            public_ops_ui.get("status") == "passed"
            and public_ops_ui.get("adminInvoiceUploadControlVisible") is True
            and public_ops_ui.get("issuedInvoiceStatus") == "issued"
            and public_ops_ui.get("invoiceAttachmentDownloaded") is True,
            [
                str(ROOT / "work" / "release_evidence" / "20260620-v01-public" / "PUBLIC_DEPLOYMENT_EVIDENCE.md"),
                str(PATHS["public_ops_ui"]),
            ],
            note="This proves the public sandbox paid-pilot review loop, not strict public production/provider readiness.",
        ),
        row(
            "utf8_text_preflight",
            "Persisted text release gate rejects non-UTF-8 files and literal question-mark mojibake before acceptance.",
            utf8_text_preflight.get("status") == "passed"
            and utf8_text_preflight.get("checks", {}).get("rejects_non_utf8_text") is True
            and utf8_text_preflight.get("checks", {}).get("rejects_literal_question_marks") is True
            and utf8_text_preflight.get("checks", {}).get("accepts_good_utf8") is True,
            [str(PATHS["utf8_text_preflight"])],
        ),
        row(
            "visual_layout_design_spec_gate",
            "All generated visual assets require a numeric DESIGN_SPEC before rendering and must fail preflight on layout or encoding violations.",
            visual_layout_design_spec.get("status") == "passed"
            and visual_layout_design_spec.get("checks", {}).get("numeric_layout_budget") is True
            and visual_layout_design_spec.get("checks", {}).get("literal_question_guard") is True,
            [str(PATHS["visual_layout_design_spec"])],
        ),
        row(
            "analysis_module_contract_gate",
            "Stable and beta EEG methods must follow the module contract for lifecycle, schema, runner, artifacts, report mapping, and evidence.",
            analysis_module_contract.get("status") == "passed"
            and analysis_module_contract.get("checks", {}).get("contract_exists") is True
            and analysis_module_contract.get("checks", {}).get("contract_required_phrases") is True
            and analysis_module_contract.get("checks", {}).get("roadmap_required_phrases") is True,
            [str(PATHS["analysis_module_contract"])],
        ),
        row(
            "cro_traceability_contract_gate",
            "CRO-style traceability must preserve audit, role, report, module, artifact, and non-medical boundary evidence.",
            cro_traceability_contract.get("status") == "passed"
            and cro_traceability_contract.get("checks", {}).get("contract_exists") is True
            and cro_traceability_contract.get("checks", {}).get("audit_model_fields") is True
            and cro_traceability_contract.get("checks", {}).get("module_contract_has_artifact_manifest") is True,
            [str(PATHS["cro_traceability_contract"])],
        ),
        row(
            "aliyun_ops_runbook_and_rollback_prepared",
            "Aliyun staging, rollback, owner input checklist, and post-input verification commands are documented and accepted without secrets.",
            all(
                phrase in aliyun_runbook_text
                for phrase in [
                    "Strict Cloud Smoke",
                    "Rollback",
                    "python scripts\\acceptance_aliyun_storage_contract.py --target aliyun --strict",
                    "python scripts\\acceptance_backup_restore_drill.py --target aliyun --strict",
                    "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\run_v01_acceptance.ps1",
                ]
            )
            and "Blocking Inputs" in owner_checklist_text
            and "Commands After Inputs Are Set" in owner_checklist_text
            and "Required Cloud Evidence After Inputs" in owner_packet_text
            and owner_packet_acceptance.get("status") == "passed"
            and owner_packet_acceptance.get("preflight_blocked_without_failures") is True,
            [
                str(PATHS["aliyun_runbook"]),
                str(PATHS["owner_checklist"]),
                str(PATHS["owner_packet"]),
                str(PATHS["owner_packet_acceptance"]),
            ],
        ),
        row(
            "executable_virtual_reviewer_scientific_gates",
            "P0 UI-only runner and virtual reviewer rounds 005-008 have current evidence for source integrity, advanced boundary, preprocessing/ICA/epoch rejection, ERP count, grand-average, and cluster-statistics checks.",
            p0_ui_evidence.get("verdict") == "pass"
            and p0_ui_acceptance.get("status") == "passed"
            and p0_ui_acceptance.get("product_gate_status") == "not_blocked_by_this_contract"
            and round_005.get("product_gate_status") == "not_blocked_by_round_005_dry_run"
            and round_006.get("product_gate_status") == "not_blocked_by_round_006_dry_run"
            and round_007.get("product_gate_status") == "not_blocked_by_round_007_dry_run"
            and round_008.get("product_gate_status") == "not_blocked_by_round_008_dry_run"
            and source_integrity_checkpoint.get("validation", {}).get("vr_eo_0015_decision") == "pass"
            and source_integrity_checkpoint.get("discard_source_integrity_summary", {}).get("source_eeg_object_unchanged") is True
            and source_integrity_checkpoint.get("discard_source_integrity_summary", {}).get("source_channels_tsv_modified") is False
            and round_007_checkpoint.get("validation", {}).get("VR-EO-0020", {}).get("decision") == "pass"
            and round_007_checkpoint.get("validation", {}).get("VR-EO-0021", {}).get("decision") == "pass"
            and round_007_checkpoint.get("validation", {}).get("VR-EO-0022", {}).get("decision") == "pass",
            [
                str(PATHS["p0_ui_evidence"]),
                str(PATHS["p0_ui_acceptance"]),
                str(PATHS["round_005"]),
                str(PATHS["round_006"]),
                str(PATHS["round_007"]),
                str(PATHS["round_008"]),
                str(PATHS["source_integrity_checkpoint"]),
                str(PATHS["round_007_checkpoint"]),
            ],
            note="Object-layer and runner evidence only; does not claim full product release, clinical/scientific approval, or advanced module stable promotion.",
        ),
        row(
            "round006_pac_real_report_consumption",
            "Real UI-only report ZIP exposes PAC frequency grids, surrogate method, normalization, random state, source/topomap boundary, and forbidden-claim scan evidence for VR-EO-0019.",
            round_006_pac_real_report_consumption.get("status") == "passed"
            and round_006_pac_real_report_consumption.get("requirement_id") == "VR-EO-0019"
            and round_006_pac_real_report_consumption.get("blockers") == []
            and exists(round_006_pac_real_report_consumption.get("report_zip_path")),
            [str(PATHS["round_006_pac_real_report_consumption"])],
            note="PAC beta artifact consumption only; not stable promotion, group-statistics, clinical, or scientific-interpretation pass.",
        ),
        row(
            "psd_real_report_consumption",
            "Real UI-only report ZIP exposes PSD/bandpower method metadata, frequency range, band/channel tables, data-preparation lineage, and sensor-space boundary evidence.",
            psd_real_report_consumption.get("status") == "passed"
            and psd_real_report_consumption.get("requirement_id") == "VR-EO-0003"
            and psd_real_report_consumption.get("blockers") == []
            and exists(psd_real_report_consumption.get("report_zip_path")),
            [str(PATHS["psd_real_report_consumption"])],
            note="PSD/bandpower artifact consumption only; not release pass, source localization, group-statistics, clinical, or scientific-interpretation pass.",
        ),
        row(
            "qc_methods_real_report_consumption",
            "Real UI-only report ZIP exposes metadata QC, QC waveform/filter preview artifacts, bad-channel audit records, method parameters, workflow, warnings, software versions, and non-diagnostic boundary evidence.",
            qc_real_report_consumption.get("status") == "passed"
            and qc_real_report_consumption.get("requirement_id") == "VR-EO-0014-qc-methods-report-consumption"
            and qc_real_report_consumption.get("blockers") == []
            and exists(qc_real_report_consumption.get("report_zip_path")),
            [str(PATHS["qc_real_report_consumption"])],
            note="Script-layer QC/methods artifact consumption only; not release pass, clinical data-quality approval, or scientific interpretation pass.",
        ),
        row(
            "pdf_ocr_artifact_qa",
            "Report PDFs are rendered page-by-page and checked through PaddleOCR as the primary parse, with native text-layer audit kept as auxiliary evidence.",
            pdf_ocr_artifact_qa.get("status") == "passed"
            and pdf_ocr_artifact_qa.get("requirement_id") == "QLANALYSER_PDF_OCR_ARTIFACT_QA_READY"
            and pdf_ocr_artifact_qa.get("primary_parse") == "PaddleOCR_all_pages"
            and pdf_ocr_artifact_qa.get("auxiliary_text_layer_audit") == "yes"
            and pdf_ocr_artifact_qa.get("artifact_validator_verdict") == "pass"
            and pdf_ocr_artifact_qa.get("blockers") == []
            and exists(pdf_ocr_artifact_qa.get("report_zip_path")),
            [str(PATHS["pdf_ocr_artifact_qa"])],
            note="PDF artifact QA only; not release pass, clinical/diagnostic validation, statistical approval, or scientific interpretation approval.",
        ),
        row(
            "round006_tfr_real_report_consumption",
            "Real UI-only report ZIP exposes TFR power/ITC measure, frequency/time axes, baseline, units, method parameters, warnings, and beta boundary evidence for VR-EO-0017.",
            round_006_tfr_real_report_consumption.get("status") == "passed"
            and round_006_tfr_real_report_consumption.get("requirement_id") == "VR-EO-0017"
            and round_006_tfr_real_report_consumption.get("blockers") == []
            and exists(round_006_tfr_real_report_consumption.get("report_zip_path")),
            [str(PATHS["round_006_tfr_real_report_consumption"])],
            note="Artifact consumption only; not an advanced-method release, group-statistics, clinical, or scientific-interpretation pass.",
        ),
        row(
            "round008_erp_real_report_consumption",
            "Real UI-only report ZIP exposes ERP baseline, event mapping, drop-log, per-condition epoch counts, units, and workflow evidence for VR-EO-0023.",
            round_008_erp_real_report_consumption.get("status") == "passed"
            and round_008_erp_real_report_consumption.get("requirement_id") == "VR-EO-0023"
            and round_008_erp_real_report_consumption.get("blockers") == []
            and exists(round_008_erp_real_report_consumption.get("report_zip_path")),
            [str(PATHS["round_008_erp_real_report_consumption"])],
            note="Artifact consumption only; not a group-statistics, release, clinical, or scientific-interpretation pass.",
        ),
        row(
            "v01_no_group_statistics_boundary",
            "Current V01 frontend, latest UI-only evidence, and latest report ZIP do not present group statistics, p-values, FDR, cluster permutation, grand-average, or significance as enabled product outputs.",
            v01_no_group_statistics_boundary.get("status") == "passed"
            and v01_no_group_statistics_boundary.get("blockers") == []
            and exists(v01_no_group_statistics_boundary.get("report_zip_path")),
            [str(PATHS["v01_no_group_statistics_boundary"])],
            note="Product-boundary wording/artifact check only; not a statistics approval, release pass, clinical approval, or scientific interpretation verdict.",
        ),
        row(
            "backup_restore_service_drill_current",
            "Backup/restore service API and local deterministic restore drill preserve state/object manifests with SHA-256 verification.",
            backup_restore_current.get("status") == "passed"
            and backup_restore_current.get("target") == "local"
            and not [check for check in backup_restore_current.get("checks", []) if check.get("status") != "pass"]
            and any(check.get("name") == "backup_restore_api" and check.get("status") == "pass" for check in backup_restore_current.get("checks", []))
            and any(check.get("name") == "restore_hashes" and check.get("status") == "pass" for check in backup_restore_current.get("checks", []))
            and any(check.get("name") == "restore_state_validation" and check.get("status") == "pass" for check in backup_restore_current.get("checks", [])),
            [str(backup_restore_current_path or PATHS["backup_restore_current_dir"])],
            note="Local service-level drill only; strict Aliyun/OSS backup restore still requires provider credentials and isolated staging evidence.",
        ),
        row(
            "fresh_ops_billing_invoice_closed_loop_current",
            "Current API evidence proves registration/login, sandbox recharge, wallet ledger, invoice issue/upload, inbox delivery, and RBAC negative checks.",
            ops_current.get("status") == "passed"
            and ops_current.get("email_provider_mode") == "sandbox"
            and ops_current.get("phone_provider_mode") == "sandbox"
            and bool(ops_current.get("wechat_account_id"))
            and set(ops_current.get("payment_modes", [])) >= {"alipay_sandbox", "wechat_pay_sandbox"}
            and float(ops_current.get("wallet_balance", 0)) > 0
            and int(ops_current.get("wallet_transaction_count", 0)) >= 2
            and ops_current.get("invoice_status") == "issued"
            and ops_current.get("invoice_file_name") == "invoice.pdf"
            and int(ops_current.get("inbox_messages", 0)) >= 1
            and len(ops_current.get("rbac_negative_checks", [])) >= 10,
            [str(PATHS["ops_current"])],
            note="Fresh API-level evidence; browser invoice/inbox evidence remains covered by invoice_admin_inbox.",
        ),
        row(
            "fresh_large_upload_capacity_current",
            "Current streaming upload evidence covers 10 users at 200MB and one 1GB file with bounded chunk reads, audit records, and usage records.",
            large_current_200.get("status") == "passed"
            and large_current_200.get("mode") == "real_capacity"
            and large_current_200.get("users") == 10
            and large_current_200.get("actual_mb_per_upload") == 200
            and len(large_current_200.get("files", [])) == 10
            and int(large_current_200.get("max_read_bytes", 0)) <= 64 * 1024
            and large_current_1g.get("status") == "passed"
            and large_current_1g.get("mode") == "real_capacity"
            and large_current_1g.get("users") == 1
            and large_current_1g.get("actual_mb_per_upload") == 1024
            and len(large_current_1g.get("files", [])) == 1
            and int(large_current_1g.get("max_read_bytes", 0)) <= 64 * 1024,
            [str(PATHS["large_current_200"]), str(PATHS["large_current_1g"])],
            note="Fresh local streaming-capacity evidence using synthetic byte streams; not a public cloud throughput claim.",
        ),
        row(
            "fresh_task_queue_capacity_current",
            "Current queue-ready lifecycle evidence covers 10 users, 50 completed tasks, audit completed events, and usage records.",
            queue_current.get("status") == "passed"
            and queue_current.get("mode") == "local_queue_ready_contract"
            and queue_current.get("users") == 10
            and queue_current.get("created_accounts") == 10
            and queue_current.get("distinct_task_owners") == 10
            and queue_current.get("tasks") == 50
            and queue_current.get("completed") == 50
            and queue_current.get("audit_completed_events") == 50
            and queue_current.get("usage_records") == 50,
            [str(PATHS["queue_current"])],
            note="Fresh local queue-ready lifecycle evidence; distributed worker capacity remains a deployment gate.",
        ),
        row(
            "aliyun_provider_boundary",
            "Public cloud/provider production readiness is explicitly blocked rather than falsely claimed.",
            preflight.get("status") == "blocked_missing_prerequisites"
            and not [check for check in preflight.get("checks", []) if check.get("status") == "fail"],
            [str(PATHS["preflight"])],
            status="external_blocked_documented",
            note="This is expected until Aliyun/OSS/backup/provider and latest DeepSeek official-direct inputs are present.",
        ),
    ]

    expected_requirement_count = 34
    if len(requirements) != expected_requirement_count:
        requirements.append(
            row(
                "requirement_matrix_count_guard",
                f"Requirement matrix must contain exactly {expected_requirement_count} requirements.",
                False,
                [str(OUTPUT_JSON)],
                note=f"Actual requirement count: {len(requirements)}",
            )
        )

    failed = [item for item in requirements if not item["ok"]]
    local_failed = [item for item in failed if item["status"] != "external_blocked_documented"]
    output_status = "passed_with_external_boundaries" if not local_failed else "failed"
    result = {
        "status": output_status,
        "generated_at": utc_now(),
        "safe_claim": (
            "Local/sandbox product goal evidence is requirement-mapped, public ECS sandbox review evidence is present, and strict public cloud/provider production remains externally blocked."
            if output_status == "passed_with_external_boundaries"
            else "One or more local/sandbox production-goal requirements are not proved."
        ),
        "requirements": requirements,
        "failed_requirements": [item["requirement"] for item in local_failed],
        "external_boundaries": [
            item["requirement"] for item in requirements if item["status"] == "external_blocked_documented"
        ],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not local_failed else 1


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# QLanalyser V01 Requirement Evidence Matrix",
        "",
        f"Generated: {result['generated_at']}",
        "",
        f"Status: `{result['status']}`",
        "",
        f"Safe claim: {result['safe_claim']}",
        "",
        "| Requirement | Status | Evidence | Note |",
        "|---|---|---|---|",
    ]
    for item in result["requirements"]:
        evidence = "<br>".join(item["evidence"])
        note = item.get("note", "")
        lines.append(f"| `{item['requirement']}` | `{item['status']}` | {evidence} | {note} |")
    lines.extend(
        [
            "",
            "Public ECS sandbox review evidence is mapped separately. Strict public cloud/provider production remains outside the pass claim until strict preflight inputs are complete.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
