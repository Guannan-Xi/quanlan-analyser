from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SLICE_ROOT = ROOT / "work/release_evidence/07-full-product-e2e-pdca/13_data_prep_analysis_entry_consistency"
OUT_DIR = SLICE_ROOT / "acceptance_packet"


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def exists_nonempty(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def check_json_status(name: str, path: Path, expected: str = "passed") -> dict:
    if not exists_nonempty(path):
        return {"name": name, "status": "missing", "path": rel(path), "pass": False}
    payload = read_json(path)
    status = payload.get("status")
    return {"name": name, "status": status, "path": rel(path), "pass": status == expected, "summary": summarize_payload(payload)}


def summarize_payload(payload: dict) -> dict:
    summary: dict[str, object] = {}
    for key in (
        "checks",
        "errors",
        "blockers",
        "method_count",
        "backend_method_family_count",
        "states",
        "p0Issues",
        "greenNavigationFindings",
    ):
        if key not in payload:
            continue
        value = payload[key]
        if isinstance(value, list):
            summary[key] = len(value)
        else:
            summary[key] = value
    if isinstance(payload.get("summary"), dict):
        summary.update(payload["summary"])
    return summary


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    docs = [
        ROOT / "docs/product/qlanalyser_data_prep_analysis_entry_consistency_requirements_20260626.md",
        ROOT / "docs/product/qlanalyser_data_prep_analysis_entry_consistency_design_20260626.md",
        ROOT / "docs/product/qlanalyser_data_prep_analysis_entry_consistency_ui_design_20260626.md",
        ROOT / "docs/product/qlanalyser_data_prep_analysis_entry_consistency_test_plan_20260626.md",
        SLICE_ROOT / "data_prep_analysis_entry_consistency_execution_packet_20260626.md",
    ]
    evidence_paths = {
        "static_contract": SLICE_ROOT / "04_static_checks/data_prep_analysis_entry_consistency_static.json",
        "browser_e2e": SLICE_ROOT / "05_browser_e2e/data_prep_analysis_entry_consistency_e2e.json",
        "backend_api_smoke": ROOT / "work/release_evidence/07-full-product-e2e-pdca/04_backend_api/backend_api_smoke.json",
        "method_source_comparison": ROOT / "work/release_evidence/07-full-product-e2e-pdca/05_methods/method_source_comparison_matrix.json",
        "synthetic_edf_scientific_figures": ROOT / "work/release_evidence/20260625-synthetic-edf-full-analysis/synthetic_edf_full_analysis_scientific_figures.json",
        "ui_scroll_review": ROOT / "work/release_evidence/07-full-product-e2e-pdca/08_ui_visual_scroll/scroll_review.json",
        "design_token_color_audit": ROOT / "work/release_evidence/07-full-product-e2e-pdca/08_ui_visual_scroll/design_token_color_audit.json",
        "deepseek_recheck_adoption": SLICE_ROOT / "deepseek/researcher_logic_review_recheck_adoption_20260626.json",
    }
    deepseek_route = SLICE_ROOT / "deepseek/deepseek_route_check_20260626.json"
    screenshots = [
        SLICE_ROOT / "05_browser_e2e/teaching_overlay_desktop.png",
        SLICE_ROOT / "05_browser_e2e/teaching_overlay_mobile.png",
        SLICE_ROOT / "05_browser_e2e/selected_data_waveform.png",
        SLICE_ROOT / "05_browser_e2e/analysis_method_cards.png",
    ]
    expected_status = {"deepseek_recheck_adoption": "adopted_with_codex_boundaries"}
    checks = [check_json_status(name, path, expected_status.get(name, "passed")) for name, path in evidence_paths.items()]
    checks.append({
        "name": "deepseek_route_direct",
        "path": rel(deepseek_route),
        "pass": exists_nonempty(deepseek_route) and read_json(deepseek_route).get("model") == "deepseek-chat" and read_json(deepseek_route).get("uses_headroom") is False,
        "summary": read_json(deepseek_route) if exists_nonempty(deepseek_route) else {},
    })
    checks.extend({
        "name": f"doc_exists:{path.name}",
        "path": rel(path),
        "pass": exists_nonempty(path),
    } for path in docs)
    checks.extend({
        "name": f"screenshot_exists:{path.name}",
        "path": rel(path),
        "pass": exists_nonempty(path),
        "bytes": path.stat().st_size if path.exists() else 0,
    } for path in screenshots)

    blockers = [item for item in checks if not item.get("pass")]
    e2e = read_json(evidence_paths["browser_e2e"])
    static = read_json(evidence_paths["static_contract"])
    backend = read_json(evidence_paths["backend_api_smoke"])
    methods = read_json(evidence_paths["method_source_comparison"])
    synthetic = read_json(evidence_paths["synthetic_edf_scientific_figures"])
    scroll = read_json(evidence_paths["ui_scroll_review"])
    color = read_json(evidence_paths["design_token_color_audit"])
    packet = {
        "schema_version": "qlanalyser-data-prep-analysis-entry-consistency-acceptance-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed_final_receipt" if not blockers else "blocked_final_receipt",
        "route_decision": "GPT-5.5/Codex acceptance with script_validator, DeepSeek polish/researcher-logic review, and read-only subagent audits.",
        "reused_pool_or_new_pool": "reused_current_07_pool",
        "execution_packet_or_skip_reason": rel(SLICE_ROOT / "data_prep_analysis_entry_consistency_execution_packet_20260626.md"),
        "execution_packets": [
            rel(SLICE_ROOT / "data_prep_analysis_entry_consistency_execution_packet_20260626.md"),
            rel(SLICE_ROOT / "deepseek/researcher_logic_review_prompt.md"),
        ],
        "executor_evidence": {
            "static_contract": {"path": rel(evidence_paths["static_contract"]), "status": static.get("status"), "checks": len(static.get("checks", []))},
            "browser_e2e": {"path": rel(evidence_paths["browser_e2e"]), "status": e2e.get("status"), "checks": len(e2e.get("checks", [])), "screenshots": [rel(Path(item)) if Path(item).is_absolute() and str(item).startswith(str(ROOT)) else item for item in e2e.get("screenshots", [])]},
            "backend_api_smoke": {"path": rel(evidence_paths["backend_api_smoke"]), "status": backend.get("status"), "checks": backend.get("checks"), "blockers": backend.get("blockers", [])},
            "method_source_comparison": {"path": rel(evidence_paths["method_source_comparison"]), "status": methods.get("status"), "method_count": methods.get("method_count"), "backend_method_family_count": methods.get("backend_method_family_count")},
            "synthetic_edf_scientific_figures": {"path": rel(evidence_paths["synthetic_edf_scientific_figures"]), "status": synthetic.get("status"), "modules_total": synthetic.get("summary", {}).get("modules_total"), "figures_audited": synthetic.get("summary", {}).get("figures_audited")},
            "ui_scroll_review": {"path": rel(evidence_paths["ui_scroll_review"]), "status": scroll.get("status"), "surfaces": len(scroll.get("surfaces", [])), "p0Issues": len(scroll.get("p0Issues", []))},
            "design_token_color_audit": {"path": rel(evidence_paths["design_token_color_audit"]), "status": color.get("status"), "greenNavigationFindings": len(color.get("greenNavigationFindings", []))},
            "deepseek": {"route_check": rel(deepseek_route), "adoption": rel(evidence_paths["deepseek_recheck_adoption"])},
        },
        "targeted_or_full_e2e": "targeted browser E2E for slice 13 plus full backend smoke, method source comparison, synthetic EDF scientific figures, and full product UI scroll review.",
        "page_visual_review": {
            "status": scroll.get("status"),
            "screenshot_manifest": "work/release_evidence/07-full-product-e2e-pdca/08_ui_visual_scroll/screenshot_manifest.json",
            "surfaces": len(scroll.get("surfaces", [])),
            "p0_issues": len(scroll.get("p0Issues", [])),
            "color_audit_status": color.get("status"),
            "green_navigation_findings": len(color.get("greenNavigationFindings", [])),
        },
        "gpt55_acceptance": "accepted: requirements/design/test docs are persisted, DeepSeek review was bounded and adopted with non-medical boundaries, implementation is verified by static/browser/backend/method/scientific/UI-scroll evidence.",
        "final_receipt": "completed_final_receipt" if not blockers else "blocked_final_receipt",
        "next_real_artifact": rel(OUT_DIR / "data_prep_analysis_entry_consistency_acceptance_packet_20260626.json"),
        "route_chain": [
            "Human intent",
            "QGCS Route Decision",
            "Execution Packet",
            "DeepSeek polish/researcher-logic review",
            "script-validator static/browser/backend/method/scientific/UI evidence",
            "read-only subagent audit",
            "GPT-5.5/Codex acceptance",
            "Final Receipt",
        ],
        "model_lane": "GPT-5.5/Codex final acceptance; DeepSeek for bounded Chinese/researcher-logic review; local scripts for deterministic validation.",
        "headroom_savings": "not measured for this local validation slice; DeepSeek route explicitly uses_headroom=false.",
        "pdca": {
            "plan": [rel(path) for path in docs],
            "do": ["frontend/index.html", "frontend/app.js", "frontend/styles.css", "scripts/acceptance_data_prep_analysis_entry_consistency_static.mjs", "scripts/acceptance_data_prep_analysis_entry_consistency_e2e.mjs"],
            "check": [item["path"] for item in checks if item.get("path")],
            "act": "slice accepted; keep residual risks in next backlog rather than blocking current completed receipt.",
        },
        "blockers": blockers,
        "residual_risks": [
            "Synthetic EDF evidence verifies plumbing and figure contracts, not real-cohort scientific validity.",
            "DeepSeek review is advisory; Codex acceptance and local evidence remain the release gate.",
            "Long filename hover/tooltip evidence is covered by static/style checks but not yet by a dedicated hover screenshot.",
        ],
    }
    json_path = OUT_DIR / "data_prep_analysis_entry_consistency_acceptance_packet_20260626.json"
    md_path = OUT_DIR / "data_prep_analysis_entry_consistency_acceptance_packet_20260626.md"
    json_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Data Prep / Analysis Entry Consistency Acceptance Packet",
        "",
        f"Status: `{packet['status']}`",
        "",
        "## Evidence",
    ]
    for key, value in packet["executor_evidence"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Final Receipt",
        packet["final_receipt"],
        "",
        "## Residual Risks",
    ])
    lines.extend(f"- {item}" for item in packet["residual_risks"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": packet["status"], "json": rel(json_path), "markdown": rel(md_path), "blockers": len(blockers)}, ensure_ascii=False, indent=2))
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
