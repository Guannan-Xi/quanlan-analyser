from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "work" / "release_evidence" / "07-full-product-e2e-pdca"
OUT_DIR = EVIDENCE_ROOT / "10_acceptance_packet"
OUT_JSON = OUT_DIR / "full_product_e2e_acceptance_packet_20260626.json"
OUT_MD = OUT_DIR / "full_product_e2e_acceptance_packet_20260626.md"

PATHS = {
    "manifest": EVIDENCE_ROOT / "full_product_e2e_pdca_manifest.json",
    "preflight": EVIDENCE_ROOT / "03_preflight" / "preflight.json",
    "running_backend_contract": EVIDENCE_ROOT / "04_backend_api" / "running_backend_contract_check.json",
    "backend_api_smoke": EVIDENCE_ROOT / "04_backend_api" / "backend_api_smoke.json",
    "method_matrix": EVIDENCE_ROOT / "05_methods" / "method_source_comparison_matrix.json",
    "deepseek_method_checks": EVIDENCE_ROOT / "05_methods" / "deepseek_adoption_method_checks.json",
    "synthetic_fixture": EVIDENCE_ROOT / "02_fixtures" / "synthetic_edf_fixture_manifest.json",
    "scientific_figure_audit": EVIDENCE_ROOT / "07_reports" / "scientific_figure_audit.json",
    "ui_screenshot_manifest": EVIDENCE_ROOT / "08_ui_visual_scroll" / "screenshot_manifest.json",
    "ui_scroll_review": EVIDENCE_ROOT / "08_ui_visual_scroll" / "scroll_review.json",
    "ui_color_audit": EVIDENCE_ROOT / "08_ui_visual_scroll" / "design_token_color_audit.json",
    "product_wide_copy_governance": EVIDENCE_ROOT / "08_ui_visual_scroll" / "product_wide_ux_copy_governance.json",
    "deepseek_visual_checks": EVIDENCE_ROOT / "08_ui_visual_scroll" / "deepseek_adoption_visual_checks.json",
    "deepseek_adoption": EVIDENCE_ROOT / "09_deepseek" / "researcher_logic_review_adoption.json",
    "main_workbench_clickthrough": EVIDENCE_ROOT / "06_main_workbench" / "main_workbench_clickthrough_e2e" / "main_workbench_direct_method_clickthrough_e2e.json",
    "full_researcher_path": EVIDENCE_ROOT / "06_main_workbench" / "full_researcher_path" / "edf_upload_to_results_ui_only.json",
    "report_zip_inventory": EVIDENCE_ROOT / "07_reports" / "report_zip_inventory.json",
    "report_claim_scan": EVIDENCE_ROOT / "07_reports" / "report_forbidden_claim_scan.json",
    "real_dataset_owner_packet": EVIDENCE_ROOT / "11_real_dataset_owner_review" / "05_owner_packet" / "real_dataset_owner_review_final_packet.json",
}

REQUIRED_REPORT_ENTRIES = [
    "reports/report.html",
    "reports/report_manifest.json",
    "reports/report.json",
    "reports/report.pdf",
]

UNSAFE_CLAIM_PATTERNS = [
    re.compile(r"\bclinical decision\b", re.I),
    re.compile(r"\btreatment recommendation\b", re.I),
    re.compile(r"\bdiagnostic conclusion\b", re.I),
    re.compile(r"\bproves? causality\b", re.I),
    re.compile(r"\bexact source localization\b", re.I),
    re.compile(r"\breal[- ]time analysis\b", re.I),
    re.compile(r"\ball EEG formats\b", re.I),
    re.compile(r"\bmulti[- ]user collaboration\b", re.I),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: str | Path) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except (ValueError, OSError):
        return str(p).replace("\\", "/")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def status_of(path: Path, default: str = "missing") -> str:
    payload = read_json(path)
    if not isinstance(payload, dict):
        return default
    return str(payload.get("status", default))


def find_report_zip(e2e: dict[str, Any]) -> Path | None:
    for item in e2e.get("downloads", []):
        if item.get("header") == "504b0304" and item.get("path"):
            path = Path(item["path"])
            if path.exists():
                return path
    return None


def inspect_report_zip(zip_path: Path | None) -> dict[str, Any]:
    if zip_path is None or not zip_path.exists():
        result = {
            "status": "failed",
            "generated_at": now_iso(),
            "zip_path": None,
            "missing": REQUIRED_REPORT_ENTRIES,
            "analysis_prefixes": [],
            "entry_count": 0,
        }
        write_json(PATHS["report_zip_inventory"], result)
        return result

    with zipfile.ZipFile(zip_path) as zf:
        names = sorted(zf.namelist())
        missing = [name for name in REQUIRED_REPORT_ENTRIES if name not in names]
        analysis_prefixes = sorted({name.split("/")[1] for name in names if name.startswith("analyses/") and len(name.split("/")) > 2})
        result = {
            "status": "passed" if not missing and analysis_prefixes else "failed",
            "generated_at": now_iso(),
            "zip_path": rel(zip_path),
            "required_entries": REQUIRED_REPORT_ENTRIES,
            "missing": missing,
            "entry_count": len(names),
            "analysis_prefixes": analysis_prefixes,
            "sample_entries": names[:80],
        }
    write_json(PATHS["report_zip_inventory"], result)
    return result


def scan_report_claims(zip_path: Path | None) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    scanned_entries: list[str] = []
    if zip_path is not None and zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if not name.lower().endswith((".html", ".json", ".txt", ".md", ".csv")):
                    continue
                scanned_entries.append(name)
                try:
                    text = zf.read(name).decode("utf-8", errors="ignore")
                except Exception:  # noqa: BLE001
                    continue
                for pattern in UNSAFE_CLAIM_PATTERNS:
                    match = pattern.search(text)
                    if match:
                        start = max(0, match.start() - 80)
                        end = min(len(text), match.end() + 80)
                        blockers.append({"entry": name, "pattern": pattern.pattern, "context": text[start:end]})

    result = {
        "status": "passed" if not blockers and zip_path is not None and zip_path.exists() else "failed",
        "generated_at": now_iso(),
        "zip_path": rel(zip_path) if zip_path else None,
        "scanned_entries": scanned_entries,
        "unsafe_claim_blockers": blockers,
        "boundary": "Scan catches unsupported positive claims; boundary/limitation statements remain allowed.",
    }
    write_json(PATHS["report_claim_scan"], result)
    return result


def check(name: str, path: Path, expected: set[str] | None = None) -> dict[str, Any]:
    expected = expected or {"passed", "prepared", "adopted_with_boundaries"}
    exists = path.exists()
    payload = read_json(path, {}) if exists else {}
    status = payload.get("status") if isinstance(payload, dict) else None
    passed = exists and status in expected
    return {
        "name": name,
        "path": rel(path),
        "exists": exists,
        "status": status,
        "passed": passed,
    }


def check_scientific_figure_audit() -> dict[str, Any]:
    path = PATHS["scientific_figure_audit"]
    exists = path.exists()
    payload = read_json(path, {}) if exists else {}
    status = payload.get("status") if isinstance(payload, dict) else None
    if status is None and isinstance(payload, dict) and "SCIENTIFIC_COLORMAP_AUDIT" in payload:
        rows = payload.get("SCIENTIFIC_COLORMAP_AUDIT") or []
        status = "passed" if rows and all(item.get("decision") == "pass" for item in rows) else "failed"
    return {
        "name": "scientific_figure_audit",
        "path": rel(path),
        "exists": exists,
        "status": status,
        "passed": exists and status == "passed",
    }


def check_copy_governance() -> dict[str, Any]:
    path = PATHS["product_wide_copy_governance"]
    exists = path.exists()
    payload = read_json(path, {}) if exists else {}
    if isinstance(payload, dict) and payload.get("passed") is True:
        status = "passed"
    elif isinstance(payload, dict):
        status = payload.get("status")
    else:
        status = None
    return {
        "name": "product_wide_copy_governance",
        "path": rel(path),
        "exists": exists,
        "status": status,
        "passed": exists and status == "passed",
    }


def copy_governance_status() -> str:
    payload = read_json(PATHS["product_wide_copy_governance"], {})
    if isinstance(payload, dict) and payload.get("passed") is True:
        return "passed"
    if isinstance(payload, dict):
        return str(payload.get("status", "missing"))
    return "missing"


def build_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# QLanalyser Full Product E2E Acceptance Packet",
        "",
        f"- status: `{packet['status']}`",
        f"- generated_at: `{packet['generated_at']}`",
        f"- final_receipt: `{packet['final_receipt']['type']}`",
        "",
        "## Required Checks",
    ]
    for row in packet["gpt55_acceptance"]["required_checks"]:
        mark = "PASS" if row["passed"] else "FAIL"
        lines.append(f"- {mark} `{row['name']}`: `{row['status']}` -> `{row['path']}`")
    lines.extend(
        [
            "",
            "## Blockers",
        ]
    )
    blockers = packet["gpt55_acceptance"]["blockers"]
    if blockers:
        lines.extend(f"- {item}" for item in blockers)
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Next Real Artifact",
            packet["next_real_artifact"]["name"],
            "",
            packet["next_real_artifact"]["scope"],
            "",
            f"- current_status: `{packet['next_real_artifact'].get('current_status', 'not_generated')}`",
            f"- current_packet: `{packet['next_real_artifact'].get('current_packet', '')}`",
        ]
    )
    current_blockers = packet["next_real_artifact"].get("current_blockers") or []
    if current_blockers:
        lines.append("- current_blockers:")
        lines.extend(f"  - {item}" for item in current_blockers)
    return "\n".join(lines)


def main() -> int:
    e2e = read_json(PATHS["full_researcher_path"], {})
    zip_path = find_report_zip(e2e if isinstance(e2e, dict) else {})
    report_inventory = inspect_report_zip(zip_path)
    report_claim_scan = scan_report_claims(zip_path)

    required_checks = [
        check("pdca_manifest", PATHS["manifest"], {"prepared"}),
        check("preflight", PATHS["preflight"], {"passed"}),
        check("backend_api_smoke", PATHS["backend_api_smoke"], {"passed"}),
        check("synthetic_fixture", PATHS["synthetic_fixture"], {"passed"}),
        check("method_source_comparison", PATHS["method_matrix"], {"passed"}),
        check_scientific_figure_audit(),
        check("deepseek_method_checks", PATHS["deepseek_method_checks"], {"passed"}),
        check("ui_screenshot_manifest", PATHS["ui_screenshot_manifest"], {"passed"}),
        check("ui_scroll_review", PATHS["ui_scroll_review"], {"passed"}),
        check("ui_color_audit", PATHS["ui_color_audit"], {"passed"}),
        check_copy_governance(),
        check("deepseek_visual_checks", PATHS["deepseek_visual_checks"], {"passed"}),
        check("main_workbench_clickthrough", PATHS["main_workbench_clickthrough"], {"passed"}),
        check("full_researcher_path_report", PATHS["full_researcher_path"], {"passed"}),
        check("report_zip_inventory", PATHS["report_zip_inventory"], {"passed"}),
        check("report_claim_scan", PATHS["report_claim_scan"], {"passed"}),
        check("deepseek_adoption", PATHS["deepseek_adoption"], {"adopted_with_boundaries"}),
    ]
    blockers = [f"{row['name']} status={row['status']} path={row['path']}" for row in required_checks if not row["passed"]]
    status = "completed_final_receipt" if not blockers else "blocked_final_receipt"

    method_matrix = read_json(PATHS["method_matrix"], {})
    ui_scroll = read_json(PATHS["ui_scroll_review"], {})
    color_audit = read_json(PATHS["ui_color_audit"], {})
    copy_governance = read_json(PATHS["product_wide_copy_governance"], {})
    main_click = read_json(PATHS["main_workbench_clickthrough"], {})
    backend_smoke = read_json(PATHS["backend_api_smoke"], {})
    real_dataset_owner_packet = read_json(PATHS["real_dataset_owner_packet"], {})

    packet = {
        "status": status,
        "generated_at": now_iso(),
        "route_decision": {
            "primary": "gpt55_planner_or_acceptance",
            "executor_lanes": ["script_validator", "subagent_or_thread_worker", "deepseek_or_polish_lane"],
            "business_unit_handoff": "02_to_07_mainline_integration_continued_into_full_product_e2e",
            "router_headroom_ipc_gateway_changed": False,
        },
        "reused_pool_or_new_pool": {
            "decision": "reused_current_07_pool",
            "pool": "QGCS-07-REVIEW-SYSTEM-ALL-ENVIRONMENTS-E2E-VISUAL-20260623",
            "new_pool_created": False,
            "reason": "Continuation/full-product acceptance slice in the current 07 lane; no router or release-pool change was needed.",
        },
        "execution_packets": [
            {
                "id": "full_product_pdca_docs",
                "status": status_of(PATHS["manifest"], "missing"),
                "artifacts": [
                    "docs/product/qlanalyser_full_product_e2e_requirements_20260626.md",
                    "docs/product/qlanalyser_full_product_e2e_design_20260626.md",
                    "docs/product/qlanalyser_full_product_e2e_test_plan_20260626.md",
                    "docs/product/qlanalyser_full_product_e2e_execution_packet_20260626.md",
                ],
            },
            {
                "id": "synthetic_fixture_method_source_comparison",
                "status": status_of(PATHS["method_matrix"]),
                "artifacts": [rel(PATHS["synthetic_fixture"]), rel(PATHS["method_matrix"])],
            },
            {
                "id": "ui_visual_scroll_color_review",
                "status": "passed" if status_of(PATHS["ui_scroll_review"]) == "passed" and status_of(PATHS["ui_color_audit"]) == "passed" else "failed",
                "artifacts": [rel(PATHS["ui_screenshot_manifest"]), rel(PATHS["ui_scroll_review"]), rel(PATHS["ui_color_audit"])],
            },
            {
                "id": "backend_admin_smoke_and_copy_guard",
                "status": "passed" if status_of(PATHS["backend_api_smoke"]) == "passed" and copy_governance_status() == "passed" else "failed",
                "artifacts": [
                    rel(PATHS["backend_api_smoke"]),
                    rel(PATHS["running_backend_contract"]),
                    rel(PATHS["product_wide_copy_governance"]),
                ],
            },
            {
                "id": "full_researcher_path_report_chain",
                "status": status_of(PATHS["full_researcher_path"]),
                "artifacts": [rel(PATHS["full_researcher_path"]), rel(PATHS["report_zip_inventory"]), rel(PATHS["report_claim_scan"])],
            },
        ],
        "executor_evidence": {
            "subagent_evidence_consumed": [
                "019effe7-7ebe-72d3-8d4f-935f61da2d00 pages/backend/admin/report inventory",
                "019f0047-a3da-78c1-a7e6-0fc4f8564660 method/source comparison inventory",
                "019f0047-b8a2-7de2-aaee-3e97873bc07d UI/visual/scroll/state inventory",
                "019effe5-6e56-7373-b5a6-4408033377a9 historical evidence audit",
            ],
            "current_cycle_evidence": {key: rel(value) for key, value in PATHS.items()},
        },
        "targeted_or_full_e2e": {
            "method_source_comparison": {
                "scope": "synthetic_fixture_all_method_families_and_9_ui_rows",
                "status": method_matrix.get("status"),
                "method_count": method_matrix.get("method_count"),
                "backend_method_family_count": method_matrix.get("backend_method_family_count"),
                "evidence": rel(PATHS["method_matrix"]),
            },
            "main_workbench_direct_clickthrough": {
                "scope": "full_ui_clickthrough_to_real_api_tasks_for_8_direct_analysis_actions",
                "status": main_click.get("status"),
                "action_count": len(main_click.get("actionResults", [])) if isinstance(main_click, dict) else None,
                "evidence": rel(PATHS["main_workbench_clickthrough"]),
            },
            "full_researcher_path_report": {
                "scope": "upload_prepare_analyze_report_download",
                "status": e2e.get("status") if isinstance(e2e, dict) else None,
                "report_zip": rel(zip_path) if zip_path else None,
                "evidence": rel(PATHS["full_researcher_path"]),
            },
            "report_zip_inventory": report_inventory,
            "report_claim_scan": report_claim_scan,
            "backend_admin_api_smoke": {
                "scope": "health_readiness_openapi_customer_admin_auth_admin_routes_customer_resources_demo_dataset_run_all",
                "status": backend_smoke.get("status") if isinstance(backend_smoke, dict) else None,
                "check_count": len(backend_smoke.get("smoke_checks", [])) if isinstance(backend_smoke, dict) else None,
                "run_all_modules": backend_smoke.get("run_all_modules") if isinstance(backend_smoke, dict) else None,
                "running_contract_status": backend_smoke.get("running_contract", {}).get("status") if isinstance(backend_smoke, dict) else None,
                "evidence": rel(PATHS["backend_api_smoke"]),
            },
        },
        "page_visual_review": {
            "status": "passed" if status_of(PATHS["ui_scroll_review"]) == "passed" and status_of(PATHS["ui_color_audit"]) == "passed" else "failed",
            "scroll_review": {
                "status": ui_scroll.get("status"),
                "p0_count": len(ui_scroll.get("p0Issues", [])) if isinstance(ui_scroll, dict) else None,
                "evidence": rel(PATHS["ui_scroll_review"]),
            },
            "color_audit": {
                "status": color_audit.get("status"),
                "green_navigation_findings": len(color_audit.get("greenNavigationFindings", [])) if isinstance(color_audit, dict) else None,
                "evidence": rel(PATHS["ui_color_audit"]),
            },
            "copy_governance": {
                "status": "passed" if copy_governance.get("passed") is True else copy_governance.get("status"),
                "check_count": len(copy_governance.get("checks", [])) if isinstance(copy_governance, dict) else None,
                "evidence": rel(PATHS["product_wide_copy_governance"]),
            },
            "screenshots": rel(PATHS["ui_screenshot_manifest"]),
        },
        "deepseek_review": {
            "adoption": rel(PATHS["deepseek_adoption"]),
            "method_checks": rel(PATHS["deepseek_method_checks"]),
            "visual_checks": rel(PATHS["deepseek_visual_checks"]),
        },
        "gpt55_acceptance": {
            "decision": "accepted_completed" if not blockers else "blocked_until_failed_checks_are_repaired",
            "required_checks": required_checks,
            "blockers": blockers,
            "boundary": "Local synthetic E2E validates workflow, contracts, UI state, and report packaging; it is not clinical or real-cohort validation.",
        },
        "final_receipt": {
            "type": status,
            "blocked": bool(blockers),
            "summary": (
                "Full-product PDCA acceptance completed with current-cycle evidence."
                if not blockers
                else "Full-product PDCA acceptance is blocked by required checks listed in gpt55_acceptance.blockers."
            ),
        },
        "next_real_artifact": {
            "name": "real_dataset_regression_and_owner_release_review_packet",
            "scope": "After synthetic/local acceptance, run anonymized real-dataset regression and owner-facing release review before external pilot or release claim.",
            "suggested_root": "work/release_evidence/07-full-product-e2e-pdca/11_real_dataset_owner_review/",
            "current_status": real_dataset_owner_packet.get("status", "not_generated") if isinstance(real_dataset_owner_packet, dict) else "not_generated",
            "current_packet": rel(PATHS["real_dataset_owner_packet"]),
            "current_blockers": real_dataset_owner_packet.get("gpt55_acceptance", {}).get("blockers", []) if isinstance(real_dataset_owner_packet, dict) else [],
        },
        "route_chain": "Human -> QGCS route decision -> document-first PDCA packet -> local script validators/subagent inventories/DeepSeek logic review -> current-cycle E2E evidence -> GPT-5.5/Codex final acceptance packet",
        "model_lane": "GPT-5.5/Codex planner and final acceptance; local scripts for deterministic validation; DeepSeek for researcher workflow logic review; subagents for bounded read-only inventory.",
        "headroom_savings": {
            "status": "not_measured",
            "claim": "No Headroom savings claimed; router/Headroom/IPC/gateway were not changed.",
        },
    }

    write_json(OUT_JSON, packet)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(build_markdown(packet), encoding="utf-8")
    print(json.dumps({"status": status, "packet": rel(OUT_JSON), "blockers": blockers}, ensure_ascii=False, indent=2))
    return 0 if status == "completed_final_receipt" else 1


if __name__ == "__main__":
    raise SystemExit(main())
