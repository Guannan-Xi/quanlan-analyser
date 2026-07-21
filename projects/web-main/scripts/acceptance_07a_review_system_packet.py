from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "work" / "release_evidence" / "review_system" / "2026-06-22-07a-p0-contract-module-lab"
PACKET = OUT_DIR / "review_packet.json"
QA_CSV = OUT_DIR / "qa_table.csv"
QA_MD = OUT_DIR / "qa_table.md"
FIX_PLAN = OUT_DIR / "fix_plan.md"
OUTPUT = OUT_DIR / "acceptance_07a_review_system_packet.json"

REQUIRED_PACKET_KEYS = [
    "review_id",
    "review_owner_model",
    "why_not_mini",
    "target_owner",
    "target_artifacts",
    "task_type",
    "domain",
    "acceptance_definition",
    "used_knowledge_sources",
    "applied_rules_from_kb",
    "mechanical_checks",
    "evidence_paths",
    "all_scope_ui_evidence",
    "target_surface",
    "target_user",
    "task_flow_reviewed",
    "screenshots_or_trace",
    "states_reviewed",
    "code_files_reviewed",
    "code_reviewable_rule",
    "code_review_hook",
    "visual_validation_hook",
    "component_tree_summary",
    "state_model_review",
    "layout_risk_review",
    "token_usage_review",
    "interaction_logic_review",
    "element_interference_risks",
    "code_level_fix_plan",
    "visual_validation_required",
    "aesthetic_review_v3",
    "interaction_blockers",
    "visual_blockers",
    "accessibility_blockers",
    "implementation_hooks",
    "post_fix_evidence_required",
    "patrol_labels",
    "visual_or_product_blockers",
    "professional_or_scientific_blockers",
    "fix_plan",
    "score_or_gate_result",
    "verdict",
    "decision_impact",
    "writeback_needed",
]


def main() -> int:
    failures: list[str] = []
    for path in [PACKET, QA_CSV, QA_MD, FIX_PLAN]:
        if not path.exists():
            failures.append(f"missing artifact: {path}")

    packet = {}
    if PACKET.exists():
        packet = json.loads(PACKET.read_text(encoding="utf-8"))
        for key in REQUIRED_PACKET_KEYS:
            if key not in packet:
                failures.append(f"missing packet key: {key}")
        if packet.get("review_owner_model") != "GPT-5.5/Codex":
            failures.append("review_owner_model must be GPT-5.5/Codex")
        if packet.get("domain") != "QLanalyser":
            failures.append("domain must be QLanalyser")
        if packet.get("verdict") not in {"pass", "conditional_pass", "revise", "block"}:
            failures.append("verdict must be pass, conditional_pass, revise, or block")
        if len(packet.get("used_knowledge_sources", [])) < 5:
            failures.append("used_knowledge_sources must include canonical review plan/index plus QLanalyser pack files")
        if len(packet.get("applied_rules_from_kb", [])) < 3:
            failures.append("applied_rules_from_kb must list concrete applied rules")
        has_ui_blockers = bool(packet.get("interaction_blockers") or packet.get("visual_blockers"))
        if packet.get("verdict") == "pass" and has_ui_blockers:
            failures.append("packet cannot pass while interaction_blockers or visual_blockers are present")
        if packet.get("verdict") in {"revise", "block"} and not has_ui_blockers:
            failures.append("revise/block verdict must expose interaction or visual blockers")
        if packet.get("professional_or_scientific_blockers") != []:
            failures.append("professional_or_scientific_blockers must be empty for pass")
        all_scope = packet.get("all_scope_ui_evidence", {})
        if not isinstance(all_scope, dict):
            failures.append("all_scope_ui_evidence must be an object")
            all_scope = {}
        if all_scope.get("status") != "passed":
            failures.append("all_scope_ui_evidence.status must be passed")
        if all_scope.get("runner_status") != "passed":
            failures.append("all_scope_ui_evidence.runner_status must be passed")
        if all_scope.get("module_scope") != "all":
            failures.append("all_scope_ui_evidence.module_scope must be all")
        if all_scope.get("task_post_count") != 8:
            failures.append("all_scope_ui_evidence.task_post_count must be 8")
        if all_scope.get("errors") != []:
            failures.append("all_scope_ui_evidence.errors must be empty")
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
        if set(all_scope.get("module_ids", [])) != expected_all_scope_modules:
            failures.append("all_scope_ui_evidence.module_ids must cover all 8 module-lab runners")
        for key in ["runner_path", "acceptance_path", "screenshot"]:
            if not all_scope.get(key):
                failures.append(f"all_scope_ui_evidence.{key} is required")
            elif not Path(str(all_scope.get(key))).exists():
                failures.append(f"all_scope_ui_evidence.{key} file missing: {all_scope.get(key)}")
        if not packet.get("fix_plan"):
            failures.append("fix_plan must be non-empty")
        if len(packet.get("code_files_reviewed", [])) < 3:
            failures.append("code_files_reviewed must include module-lab html/js/css")
        if not packet.get("component_tree_summary"):
            failures.append("component_tree_summary is required")
        for key in ["state_model_review", "layout_risk_review", "token_usage_review", "interaction_logic_review"]:
            if not packet.get(key):
                failures.append(f"{key} is required")
        if not packet.get("element_interference_risks"):
            failures.append("element_interference_risks is required")
        if not packet.get("code_level_fix_plan"):
            failures.append("code_level_fix_plan is required")
        if not packet.get("visual_validation_required"):
            failures.append("visual_validation_required is required")
        aesthetic = packet.get("aesthetic_review_v3", {})
        if not aesthetic or not aesthetic.get("maturity_level"):
            failures.append("aesthetic_review_v3 with maturity_level is required")
        rules = packet.get("code_reviewable_rule", [])
        if len(rules) < 1:
            failures.append("code_reviewable_rule must contain at least one mapped rule")
        if not packet.get("code_review_hook"):
            failures.append("code_review_hook is required")
        if not packet.get("visual_validation_hook"):
            failures.append("visual_validation_hook is required")
        if "conceptual-only" in packet.get("patrol_labels", []):
            failures.append("packet is conceptual-only because code/visual hooks are missing")
        if packet.get("verdict") == "pass" and "preview-only-fake-pass" in packet.get("patrol_labels", []):
            failures.append("packet cannot pass with preview-only-fake-pass")
        hook_count = len(packet.get("code_review_hook", []))
        visual_hook_count = len(packet.get("visual_validation_hook", []))
        if hook_count < len(rules):
            failures.append("code_review_hook count must cover each code_reviewable_rule")
        if visual_hook_count < len(rules):
            failures.append("visual_validation_hook count must cover each code_reviewable_rule")
        for index, rule in enumerate(rules, start=1):
            for key in [
                "knowledge_rule_id",
                "human_judgment_rule",
                "code_reviewable_rule",
                "code_review_scope",
                "code_files_reviewed",
                "bad_code_smells_found",
                "code_review_hook",
                "visual_validation_required",
                "visual_validation_hook",
                "fix_plan",
                "post_fix_evidence",
                "verdict_impact",
            ]:
                if not rule.get(key):
                    failures.append(f"code_reviewable_rule[{index}] missing {key}")
            scope = rule.get("code_review_scope", {})
            for scope_key in [
                "components",
                "files",
                "state",
                "layout",
                "tokens",
                "interactions",
                "accessibility",
                "scientific_boundary",
            ]:
                if not scope.get(scope_key):
                    failures.append(f"code_reviewable_rule[{index}].code_review_scope missing {scope_key}")
        for evidence_path in packet.get("evidence_paths", {}).values():
            if not Path(str(evidence_path)).exists():
                failures.append(f"evidence path missing: {evidence_path}")
        for screenshot_path in packet.get("screenshots_or_trace", []):
            text = str(screenshot_path)
            if text.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) and not Path(text).exists():
                failures.append(f"screenshot path missing: {text}")
        impact = str(packet.get("decision_impact", "")).lower()
        if "not release pass" not in impact:
            failures.append("decision_impact must explicitly say not release pass")

    result = {
        "status": "passed" if not failures else "failed",
        "review_packet": str(PACKET),
        "qa_table_csv": str(QA_CSV),
        "qa_table_md": str(QA_MD),
        "fix_plan": str(FIX_PLAN),
        "failures": failures,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
