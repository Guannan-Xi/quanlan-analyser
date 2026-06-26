from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "work" / "release_evidence" / "07-full-product-e2e-pdca"
SLICE_ROOT = EVIDENCE_ROOT / "12_current_modules_teaching_mode"
OUT_DIR = SLICE_ROOT / "09_acceptance_packet"
OUT_JSON = OUT_DIR / "current_modules_teaching_mode_acceptance_packet_20260626.json"
OUT_MD = OUT_DIR / "current_modules_teaching_mode_acceptance_packet_20260626.md"


PATHS = {
    "requirements_doc": ROOT / "docs" / "product" / "qlanalyser_current_modules_teaching_mode_requirements_20260626.md",
    "design_doc": ROOT / "docs" / "product" / "qlanalyser_current_modules_teaching_mode_design_20260626.md",
    "ui_design_doc": ROOT / "docs" / "product" / "qlanalyser_current_modules_teaching_mode_ui_design_20260626.md",
    "test_plan_doc": ROOT / "docs" / "product" / "qlanalyser_current_modules_teaching_mode_test_plan_20260626.md",
    "execution_packet": SLICE_ROOT / "current_modules_teaching_mode_execution_packet_20260626.md",
    "deepseek_prompt": SLICE_ROOT / "deepseek" / "researcher_logic_review_prompt.md",
    "deepseek_review": SLICE_ROOT / "deepseek" / "researcher_logic_review.md",
    "deepseek_adoption": SLICE_ROOT / "deepseek" / "researcher_logic_review_adoption.md",
    "static_acceptance": SLICE_ROOT / "03_static_checks" / "current_modules_teaching_mode_static.json",
    "csd_dual_path": SLICE_ROOT / "06_methods" / "csd_dual_path" / "csd_dual_path_acceptance.json",
    "teaching_overlay": SLICE_ROOT / "07_ui_browser" / "teaching_mode_overlay_e2e.json",
    "backend_smoke": EVIDENCE_ROOT / "04_backend_api" / "backend_api_smoke.json",
    "method_matrix": EVIDENCE_ROOT / "05_methods" / "method_source_comparison_matrix.json",
    "ui_scroll_review": EVIDENCE_ROOT / "08_ui_visual_scroll" / "scroll_review.json",
    "ui_color_audit": EVIDENCE_ROOT / "08_ui_visual_scroll" / "design_token_color_audit.json",
    "ui_screenshot_manifest": EVIDENCE_ROOT / "08_ui_visual_scroll" / "screenshot_manifest.json",
    "synthetic_full_analysis": ROOT / "work" / "release_evidence" / "20260625-synthetic-edf-full-analysis" / "synthetic_edf_full_analysis_scientific_figures.json",
    "scientific_colormap_audit": ROOT / "work" / "release_evidence" / "20260625-synthetic-edf-full-analysis" / "scientific_colormap_audit_validator_ready.json",
    "full_product_acceptance_packet": EVIDENCE_ROOT / "10_acceptance_packet" / "full_product_e2e_acceptance_packet_20260626.json",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def doc_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": rel(path), "exists": False, "bytes": 0}
    text = path.read_text(encoding="utf-8")
    return {
        "path": rel(path),
        "exists": True,
        "bytes": path.stat().st_size,
        "contains_teaching_mode": "教学模式" in text,
        "contains_csd": "CSD" in text,
        "contains_pdca": "PDCA" in text,
    }


def status_of_json(path: Path, *, pass_key: str = "status") -> str:
    payload = read_json(path)
    if payload is None:
        return "missing"
    if isinstance(payload, dict):
        if payload.get("passed") is True:
            return "passed"
        value = payload.get(pass_key)
        if isinstance(value, str):
            return value
    return "present"


def count_failures(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["missing_or_invalid_payload"]
    failures: list[str] = []
    checks = payload.get("checks")
    if isinstance(checks, list):
        for item in checks:
            if isinstance(item, dict) and item.get("pass") is False:
                failures.append(str(item.get("name", "unnamed_check")))
    blockers = payload.get("blockers")
    if isinstance(blockers, list):
        failures.extend(str(item) for item in blockers)
    return failures


def build_packet() -> dict[str, Any]:
    static_payload = read_json(PATHS["static_acceptance"])
    teaching_payload = read_json(PATHS["teaching_overlay"])
    backend_payload = read_json(PATHS["backend_smoke"])
    method_payload = read_json(PATHS["method_matrix"])
    scroll_payload = read_json(PATHS["ui_scroll_review"])
    color_payload = read_json(PATHS["ui_color_audit"])
    synthetic_payload = read_json(PATHS["synthetic_full_analysis"])
    full_product_payload = read_json(PATHS["full_product_acceptance_packet"])

    checks = [
        {
            "id": "docs_requirements_design_ui_test",
            "status": "passed" if all(PATHS[key].exists() for key in ("requirements_doc", "design_doc", "ui_design_doc", "test_plan_doc")) else "failed",
            "evidence": [rel(PATHS[key]) for key in ("requirements_doc", "design_doc", "ui_design_doc", "test_plan_doc")],
        },
        {
            "id": "deepseek_researcher_logic_review",
            "status": "passed" if PATHS["deepseek_review"].exists() and PATHS["deepseek_adoption"].exists() else "failed",
            "evidence": [rel(PATHS["deepseek_prompt"]), rel(PATHS["deepseek_review"]), rel(PATHS["deepseek_adoption"])],
        },
        {
            "id": "current_available_analysis_methods_static",
            "status": "passed" if isinstance(static_payload, dict) and static_payload.get("passed") is True else "failed",
            "evidence": rel(PATHS["static_acceptance"]),
            "method_ids": static_payload.get("actual_method_ids") if isinstance(static_payload, dict) else None,
            "failures": count_failures(static_payload),
        },
        {
            "id": "teaching_mode_overlay_browser_e2e",
            "status": "passed" if isinstance(teaching_payload, dict) and teaching_payload.get("passed") is True else "failed",
            "evidence": rel(PATHS["teaching_overlay"]),
            "screenshots": teaching_payload.get("screenshots") if isinstance(teaching_payload, dict) else None,
            "failures": count_failures(teaching_payload),
        },
        {
            "id": "csd_dual_path_and_boundary",
            "status": status_of_json(PATHS["csd_dual_path"]),
            "evidence": rel(PATHS["csd_dual_path"]),
        },
        {
            "id": "backend_api_smoke",
            "status": status_of_json(PATHS["backend_smoke"]),
            "evidence": rel(PATHS["backend_smoke"]),
            "blockers": backend_payload.get("blockers") if isinstance(backend_payload, dict) else None,
        },
        {
            "id": "method_source_comparison",
            "status": status_of_json(PATHS["method_matrix"]),
            "evidence": rel(PATHS["method_matrix"]),
            "method_count": method_payload.get("method_count") if isinstance(method_payload, dict) else None,
            "backend_method_family_count": method_payload.get("backend_method_family_count") if isinstance(method_payload, dict) else None,
        },
        {
            "id": "ui_visual_scroll_and_color_governance",
            "status": "passed" if status_of_json(PATHS["ui_scroll_review"]) == "passed" and status_of_json(PATHS["ui_color_audit"]) == "passed" else "failed",
            "evidence": [rel(PATHS["ui_scroll_review"]), rel(PATHS["ui_color_audit"]), rel(PATHS["ui_screenshot_manifest"])],
            "surfaces": len(scroll_payload.get("surfaces", [])) if isinstance(scroll_payload, dict) else None,
            "p0_count": len(scroll_payload.get("p0Issues", [])) if isinstance(scroll_payload, dict) else None,
            "green_navigation_findings": len(color_payload.get("greenNavigationFindings", [])) if isinstance(color_payload, dict) else None,
        },
        {
            "id": "synthetic_edf_all_methods_scientific_figures",
            "status": status_of_json(PATHS["synthetic_full_analysis"]),
            "evidence": [rel(PATHS["synthetic_full_analysis"]), rel(PATHS["scientific_colormap_audit"])],
            "summary": synthetic_payload.get("summary") if isinstance(synthetic_payload, dict) else None,
        },
        {
            "id": "full_product_e2e_acceptance_packet",
            "status": full_product_payload.get("status") if isinstance(full_product_payload, dict) else "missing",
            "evidence": rel(PATHS["full_product_acceptance_packet"]),
        },
    ]
    blockers = [item for item in checks if item["status"] not in {"passed", "completed_final_receipt"}]
    return {
        "schema": "qlanalyser-current-modules-teaching-mode-acceptance-v1",
        "generated_at": now_iso(),
        "route_decision": "gpt55_planner_or_acceptance + script_validator + DeepSeek researcher-logic review + bounded subagent audit",
        "reused_pool_or_new_pool": "reused_current_07_pool",
        "execution_packets": [rel(PATHS["execution_packet"])],
        "documents": [doc_status(PATHS[key]) for key in ("requirements_doc", "design_doc", "ui_design_doc", "test_plan_doc")],
        "executor_evidence": checks,
        "targeted_or_full_e2e": {
            "targeted_slice": "current available analysis methods, CSD boundary, teaching mode overlay",
            "full_product_e2e": rel(PATHS["full_product_acceptance_packet"]),
            "synthetic_data": synthetic_payload.get("synthetic_edf") if isinstance(synthetic_payload, dict) else None,
        },
        "page_visual_review": {
            "scroll_review": rel(PATHS["ui_scroll_review"]),
            "color_audit": rel(PATHS["ui_color_audit"]),
            "screenshot_manifest": rel(PATHS["ui_screenshot_manifest"]),
        },
        "gpt55_acceptance": {
            "status": "accepted" if not blockers else "blocked",
            "blockers": blockers,
            "rationale": "All required docs and current-slice/full-product validation artifacts are present and passing." if not blockers else "One or more required checks are not passing.",
        },
        "final_receipt": "completed_final_receipt" if not blockers else "blocked_final_receipt",
        "next_real_artifact": "owner can review current_modules_teaching_mode_acceptance_packet_20260626.md and then decide whether to push/deploy",
        "route_chain": [
            "Human requirement",
            "QGCS route decision",
            "document-first PDCA packet",
            "DeepSeek researcher logic review",
            "script/browser/API/method validators",
            "GPT-5.5/Codex acceptance",
        ],
        "model_lane": "GPT-5.5/Codex final acceptance; DeepSeek bounded logic review; script validators for deterministic evidence.",
        "headroom_savings": "not_measured_in_this_local_acceptance_slice",
    }


def build_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# QLanalyser Current Modules + Teaching Mode Acceptance Packet",
        "",
        f"- final_receipt: `{packet['final_receipt']}`",
        f"- generated_at: `{packet['generated_at']}`",
        f"- route_decision: `{packet['route_decision']}`",
        f"- reused_pool_or_new_pool: `{packet['reused_pool_or_new_pool']}`",
        "",
        "## Documents",
    ]
    for doc in packet["documents"]:
        status = "PASS" if doc["exists"] else "FAIL"
        lines.append(f"- {status} `{doc['path']}` bytes={doc['bytes']}")

    lines.extend(["", "## Evidence Checks"])
    for item in packet["executor_evidence"]:
        status = item["status"]
        lines.append(f"- `{status}` {item['id']}")

    lines.extend(["", "## GPT-5.5/Codex Acceptance"])
    lines.append(f"- status: `{packet['gpt55_acceptance']['status']}`")
    blockers = packet["gpt55_acceptance"]["blockers"]
    if blockers:
        lines.append("- blockers:")
        for blocker in blockers:
            lines.append(f"  - `{blocker['id']}` status=`{blocker['status']}`")
    else:
        lines.append("- blockers: none")

    lines.extend(
        [
            "",
            "## Next Real Artifact",
            packet["next_real_artifact"],
            "",
            "## Route Receipt",
            f"- route_chain: {' -> '.join(packet['route_chain'])}",
            f"- model_lane: {packet['model_lane']}",
            f"- headroom_savings: {packet['headroom_savings']}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    packet = build_packet()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(build_markdown(packet), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": packet["final_receipt"],
                "packet": rel(OUT_JSON),
                "markdown": rel(OUT_MD),
                "blockers": packet["gpt55_acceptance"]["blockers"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if packet["final_receipt"] == "completed_final_receipt" else 1


if __name__ == "__main__":
    raise SystemExit(main())
