from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "work" / "release_evidence" / "20260621-click-only-user-journey" / "user_test_coverage_matrix.json"

EVIDENCE = {
    "click_only": ROOT / "work" / "release_evidence" / "20260621-click-only-user-journey" / "click_only_user_journey.json",
    "page_visual": ROOT / "work" / "release_evidence" / "20260620-page-visual-qa" / "page_visual_qa.json",
    "module_lab": ROOT / "work" / "release_evidence" / "20260620-module-lab-live-runner" / "module_lab_live_runner.json",
    "preset_analysis": ROOT / "work" / "release_evidence" / "20260620-customer-preset-analysis" / "customer_preset_analysis.json",
    "ops_ui": ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_ops_ui.json",
}


REQUIRED_PAGES = [
    "customer-login",
    "customer-register-email",
    "customer-register-phone",
    "customer-register-wechat",
    "customer-dashboard",
    "customer-upload",
    "customer-data-preparation",
    "customer-analysis-task",
    "customer-results",
    "customer-report-download",
    "customer-billing",
    "customer-invoice",
    "customer-inbox",
    "admin-overview",
    "admin-operations",
    "admin-finance",
    "admin-system",
    "module-lab",
    "preset-analysis",
]


REQUIRED_FUNCTIONS = [
    "customer_login_by_form",
    "customer_register_email_visible",
    "customer_register_phone_visible",
    "customer_register_wechat_visible",
    "sandbox_recharge_click",
    "invoice_request_click",
    "inbox_discovery_click",
    "project_create_click",
    "eeg_upload_click",
    "qc_click",
    "psd_bandpower_click",
    "erp_p300_click",
    "report_create_click",
    "report_download_visible",
    "admin_entry_click",
    "admin_overview_visible",
    "admin_invoice_issue_click",
    "admin_inbox_delivery_verified",
    "module_lab_qc_click",
    "module_lab_psd_click",
    "module_lab_erp_click",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    if not path.exists():
        return {"status": "missing", "__path__": str(path)}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    data = {name: read_json(path) for name, path in EVIDENCE.items()}
    click = data["click_only"]
    visual = data["page_visual"]
    lab = data["module_lab"]
    preset = data["preset_analysis"]
    ops = data["ops_ui"]

    visual_pages = set()
    if visual.get("status") == "passed":
        visual_pages = {state.get("page") for state in visual.get("states", []) if state.get("page")}

    customer_steps = set(click.get("customer", {}).get("steps", []))
    admin_steps = set(click.get("admin", {}).get("steps", []))
    register_steps = set(click.get("register", {}).get("steps", []))
    page_coverage = click.get("pageCoverage", {})
    customer_pages = set(page_coverage.get("customerPages", []))
    admin_pages = set(page_coverage.get("adminPages", []))
    external_pages = set(page_coverage.get("externalPages", []))
    lab_modules = lab.get("moduleChecks", {})

    click_page_checks = {
        "customer-login": "logged_in_by_form_click" in customer_steps,
        "customer-register-email": "covered_register_email" in register_steps,
        "customer-register-phone": "covered_register_phone" in register_steps,
        "customer-register-wechat": "covered_register_wechat" in register_steps,
        "customer-dashboard": "dashboard" in customer_pages,
        "customer-upload": "upload" in customer_pages,
        "customer-data-preparation": "analysis" in customer_pages,
        "customer-analysis-task": "workflow" in customer_pages,
        "customer-results": "statistics" in customer_pages,
        "customer-report-download": "publication" in customer_pages,
        "customer-billing": "billing" in customer_pages,
        "customer-invoice": "invoice" in customer_pages,
        "customer-inbox": "inbox" in customer_pages,
        "admin-overview": "adminDashboard" in admin_pages,
        "admin-operations": "adminOperations" in admin_pages,
        "admin-finance": "adminFinance" in admin_pages,
        "admin-system": "adminSystem" in admin_pages,
        "module-lab": "module-lab" in external_pages,
        "preset-analysis": "preset-analysis" in external_pages,
    }

    page_rows = []
    for page in REQUIRED_PAGES:
        visual_covered = page in visual_pages
        click_covered = bool(click_page_checks.get(page))
        page_rows.append({
            "page": page,
            "visual_qa": visual_covered,
            "click_covered": click_covered,
            "status": "covered" if visual_covered or click_covered else "needs_visual_or_click_evidence",
        })

    function_checks = {
        "customer_login_by_form": "logged_in_by_form_click" in customer_steps,
        "customer_register_email_visible": "covered_register_email" in register_steps or "customer-register-email" in visual_pages,
        "customer_register_phone_visible": "covered_register_phone" in register_steps or "customer-register-phone" in visual_pages,
        "customer_register_wechat_visible": "covered_register_wechat" in register_steps or "customer-register-wechat" in visual_pages,
        "sandbox_recharge_click": "clicked_sandbox_recharge" in customer_steps,
        "invoice_request_click": "submitted_invoice_by_click" in customer_steps,
        "inbox_discovery_click": "opened_inbox_by_nav_click" in customer_steps,
        "project_create_click": "created_project_by_click" in customer_steps,
        "eeg_upload_click": "uploaded_eeg_by_click" in customer_steps,
        "qc_click": "ran_qc_by_click" in customer_steps,
        "psd_bandpower_click": "ran_psd_by_click" in customer_steps and preset.get("status") == "passed",
        "erp_p300_click": "ran_erp_by_click" in customer_steps and preset.get("status") == "passed",
        "report_create_click": "created_report_by_click" in customer_steps,
        "report_download_visible": "downloaded_report_package_by_click" in customer_steps
        and bool(click.get("customer", {}).get("downloadedReport")),
        "admin_entry_click": "clicked_visible_admin_entry" in admin_steps,
        "admin_overview_visible": "adminDashboard" in admin_pages or "admin-overview" in visual_pages,
        "admin_invoice_issue_click": ops.get("issuedInvoiceStatus") == "issued",
        "admin_inbox_delivery_verified": ops.get("invoiceAttachmentDownloaded") is True,
        "module_lab_qc_click": lab_modules.get("qc", {}).get("passed") is True,
        "module_lab_psd_click": lab_modules.get("psd", {}).get("passed") is True,
        "module_lab_erp_click": lab_modules.get("erp", {}).get("passed") is True,
    }
    function_rows = [
        {"function": name, "covered": bool(function_checks.get(name)), "status": "covered" if function_checks.get(name) else "missing"}
        for name in REQUIRED_FUNCTIONS
    ]
    missing_pages = [row["page"] for row in page_rows if row["status"] != "covered"]
    missing_functions = [row["function"] for row in function_rows if row["status"] != "covered"]
    result = {
        "status": "passed" if not missing_functions and len(missing_pages) <= 4 else "needs_more_coverage",
        "generated_at": utc_now(),
        "policy": "User testing must be click-only for user actions; API evidence can support but not replace UI actions.",
        "evidence": {name: str(path) for name, path in EVIDENCE.items()},
        "coverage": {
            "pages_total": len(REQUIRED_PAGES),
            "pages_visual_covered": len(REQUIRED_PAGES) - len(missing_pages),
            "functions_total": len(REQUIRED_FUNCTIONS),
            "functions_covered": len(REQUIRED_FUNCTIONS) - len(missing_functions),
        },
        "pages": page_rows,
        "functions": function_rows,
        "missing_pages": missing_pages,
        "missing_functions": missing_functions,
        "next_required_tests": [] if not missing_pages and not missing_functions else [
            "Add click-only tests for every missing page/function listed above.",
            "Do not use API-only evidence as a substitute for user browser actions.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
