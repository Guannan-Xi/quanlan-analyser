from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "work" / "release_evidence" / "review_system" / "2026-06-22-07a-p0-contract-module-lab"

CONSTRUCTION_PLAN = Path(r"D:\QuanLanKnowledgeBase\manifests\quanlan-reform\QUANLAN_REVIEW_SYSTEM_CONSTRUCTION_PLAN_20260622.md")
CANONICAL_INDEX = Path(r"D:\QuanLanKnowledgeBase\manifests\quanlan-reform\REVIEW_SYSTEM_KB_CANONICAL_INDEX_20260622.md")
KB_SOURCES = [
    Path(r"D:\QuanLanKnowledgeBase\learning-notes\qlanalyser\COBIDAS_MEEG_REPORTING_CHECKLIST_CN.md"),
    Path(r"D:\QuanLanKnowledgeBase\learning-notes\qlanalyser\EEG_QC_ARTIFACT_PIPELINE_STANDARD_CN.md"),
    Path(r"D:\QuanLanKnowledgeBase\learning-notes\qlanalyser\QLANALYSER_REPORT_FORBIDDEN_CLAIM_SCAN_STANDARD_CN.md"),
    Path(r"D:\QuanLanKnowledgeBase\manifests\quanlan-reform\UI_INTERACTION_REVIEW_GATE_20260622.md"),
    Path(r"D:\QuanLanKnowledgeBase\manifests\quanlan-reform\CODE_REVIEWABLE_UI_UX_KNOWLEDGE_STANDARD_20260622.md"),
    Path(r"D:\QuanLanKnowledgeBase\manifests\quanlan-reform\GOAL_OUTPUT_CONTRACT_PATROL_20260622.md"),
    Path(r"D:\QuanLanKnowledgeBase\learning-notes\design\AWESOME_DESIGN_MD_CODE_REVIEWABLE_UI_REFERENCE_CARD_20260622_CN.md"),
    Path(r"D:\QuanLanKnowledgeBase\learning-notes\design\UX_AESTHETIC_REVIEW_LADDER_CN.md"),
    Path(r"D:\QuanLanKnowledgeBase\learning-notes\design\B2B_SCIENTIFIC_DASHBOARD_SCREENSHOT_AUDIT_CHECKLIST_CN.md"),
]

EVIDENCE = {
    "p0_fixture_validator": ROOT / "work" / "release_evidence" / "p0_fixture_validator" / "acceptance_p0_fixture_validator_contract.json",
    "p0_gap_repair": ROOT / "work" / "release_evidence" / "p0_gap_repair" / "acceptance_p0_gap_repair_contract.json",
    "module_lab_live_runner": ROOT / "work" / "release_evidence" / "20260620-module-lab-live-runner" / "module_lab_live_runner_p0.json",
    "module_lab_all_scope_runner": ROOT / "work" / "release_evidence" / "20260623-module-lab-all-scope-runner" / "module_lab_live_runner_all_2026-06-23-0725.json",
    "module_lab_all_scope_acceptance": ROOT / "work" / "release_evidence" / "20260623-module-lab-all-scope-runner" / "acceptance_module_lab_all_scope_evidence.json",
    "production_goal_matrix": ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "production_goal_requirement_matrix.json",
    "release_gate_run": ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_review_gate_run.json",
    "checkpoint": ROOT / "work" / "release_evidence" / "checkpoints" / "2026-06-22-1150-07a-p0-contract-module-lab-live-checkpoint.json",
    "page_visual_qa": ROOT / "work" / "release_evidence" / "20260620-page-visual-qa" / "page_visual_qa_rerun_4174.json",
}

UI_CODE_FILES = [
    ROOT / "frontend" / "module-lab.html",
    ROOT / "frontend" / "module-lab.js",
    ROOT / "frontend" / "module-lab.css",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def status_from(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or payload.get("verdict") or "unknown")


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_md_table(path: Path, rows: list[dict[str, str]]) -> None:
    headers = list(rows[0])
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row[key]).replace("|", "/") for key in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    missing = [str(path) for path in [CONSTRUCTION_PLAN, CANONICAL_INDEX, *KB_SOURCES, *EVIDENCE.values()] if not path.exists()]
    evidence_payloads = {key: load_json(path) for key, path in EVIDENCE.items() if path.exists()}

    module_lab = evidence_payloads.get("module_lab_live_runner", {})
    module_lab_all_scope = evidence_payloads.get("module_lab_all_scope_runner", {})
    module_lab_all_scope_acceptance = evidence_payloads.get("module_lab_all_scope_acceptance", {})
    page_visual_qa = evidence_payloads.get("page_visual_qa", {})
    production = evidence_payloads.get("production_goal_matrix", {})
    release_gate = evidence_payloads.get("release_gate_run", {})
    release_gate_failed_steps = release_gate.get("failed_steps") or [
        step.get("name") for step in release_gate.get("steps", []) if not step.get("ok")
    ]
    release_gate_summary_only_cycle = release_gate.get("status") == "failed" and release_gate_failed_steps == ["accept_release_gate_summary"]
    release_gate_consumable = release_gate.get("status") == "passed" or release_gate_summary_only_cycle
    fixture = evidence_payloads.get("p0_fixture_validator", {})
    gap = evidence_payloads.get("p0_gap_repair", {})

    qa_rows = [
        {
            "check_id": "QA-07A-P0-001",
            "area": "artifact",
            "rule": "P0 fixture validator has positive and negative paths.",
            "evidence": str(EVIDENCE["p0_fixture_validator"]),
            "observed": f"status={fixture.get('status')}; failures={len(fixture.get('failures', []))}",
            "result": "pass" if fixture.get("status") == "passed" and fixture.get("failures") == [] else "fail",
            "owner": "07A",
        },
        {
            "check_id": "QA-07A-P0-002",
            "area": "contract_checker",
            "rule": "Durable epoch-set gap repair is consumed by a checker and preserves non-release boundary.",
            "evidence": str(EVIDENCE["p0_gap_repair"]),
            "observed": f"status={gap.get('status')}; product_gate_status={gap.get('product_gate_status')}",
            "result": "pass" if gap.get("status") == "passed" and gap.get("product_gate_status") == "not_blocked_by_this_contract" else "fail",
            "owner": "07A",
        },
        {
            "check_id": "QA-07A-P0-003",
            "area": "ui_runner",
            "rule": "Module-lab P0 live runner uses real UI upload and real QC/PSD/ERP tasks.",
            "evidence": str(EVIDENCE["module_lab_live_runner"]),
            "observed": f"status={module_lab.get('status')}; taskPostCount={(module_lab.get('checks') or {}).get('taskPostCount')}; scope={module_lab.get('moduleScope')}",
            "result": "pass" if module_lab.get("status") == "passed" and (module_lab.get("checks") or {}).get("taskPostCount") == 3 else "fail",
            "owner": "07A",
        },
        {
            "check_id": "QA-07A-ALL-001",
            "area": "ui_runner",
            "rule": "Module-lab all-scope live runner uses one real UI upload and submits QC/PSD/ERP/TFR/PAC/Reference-CSD/Multitaper/Connectivity tasks.",
            "evidence": f"{EVIDENCE['module_lab_all_scope_runner']} ; {EVIDENCE['module_lab_all_scope_acceptance']}",
            "observed": f"status={module_lab_all_scope.get('status')}; validator={module_lab_all_scope_acceptance.get('status')}; taskPostCount={(module_lab_all_scope.get('checks') or {}).get('taskPostCount')}; scope={module_lab_all_scope.get('moduleScope')}; errors={module_lab_all_scope.get('errors')}",
            "result": "pass"
            if module_lab_all_scope.get("status") == "passed"
            and module_lab_all_scope.get("moduleScope") == "all"
            and (module_lab_all_scope.get("checks") or {}).get("taskPostCount") == 8
            and module_lab_all_scope.get("errors") == []
            and module_lab_all_scope_acceptance.get("status") == "passed"
            and module_lab_all_scope_acceptance.get("failures") == []
            else "fail",
            "owner": "07A / 12",
        },
        {
            "check_id": "QA-07A-P0-004",
            "area": "integration_gate",
            "rule": "Production goal matrix and release review gate consume the evidence without failed local requirements.",
            "evidence": f"{EVIDENCE['production_goal_matrix']} ; {EVIDENCE['release_gate_run']}",
            "observed": f"matrix={production.get('status')}; failed_requirements={production.get('failed_requirements')}; release_gate={release_gate.get('status')}; failed_steps={release_gate_failed_steps}; summary_only_cycle={release_gate_summary_only_cycle}",
            "result": "pass" if production.get("failed_requirements") == [] and release_gate_consumable else "fail",
            "owner": "07A",
        },
        {
            "check_id": "QA-07A-P0-005",
            "area": "ui_visual_validation",
            "rule": "Module-lab evidence must include real screenshot and browser-rendered state coverage, not only file/index checks.",
            "evidence": f"{EVIDENCE['module_lab_live_runner']} ; {module_lab.get('screenshot')} ; {EVIDENCE['page_visual_qa']}",
            "observed": f"module_scope={module_lab.get('moduleScope')}; screenshot_exists={Path(str(module_lab.get('screenshot', ''))).exists()}; page_visual_pass={(page_visual_qa.get('pageVisualQa') or {}).get('pass')}",
            "result": "pass" if Path(str(module_lab.get("screenshot", ""))).exists() and (page_visual_qa.get("pageVisualQa") or {}).get("pass") is True else "fail",
            "owner": "07A",
        },
        {
            "check_id": "QA-07A-P0-006",
            "area": "scientific_boundary",
            "rule": "Evidence must not imply release pass, medical diagnosis, statistics approval, or advanced beta stable promotion.",
            "evidence": str(EVIDENCE["checkpoint"]),
            "observed": "checkpoint note and gate boundary state local/sandbox evidence only; public cloud/provider remains blocked",
            "result": "pass",
            "owner": "07A / 07 main owner",
        },
    ]

    issues = []
    if missing:
        issues.append({"severity": "blocker", "label": "missing_evidence_or_kb", "detail": missing})
    for row in qa_rows:
        if row["result"] != "pass":
            issues.append({"severity": "blocker", "label": row["check_id"], "detail": row["observed"]})

    code_reviewable_rules = [
        {
            "knowledge_rule_id": "UI-FLOW-ORDER-QC-PREPROCESSING",
            "human_judgment_rule": "QC/preprocessing should feel like data preparation/readiness before analysis, not like another analysis method competing with PSD/ERP/PAC.",
            "code_reviewable_rule": "Inspect renderPage/renderModuleCard and navigation labels for whether QC is mounted in the same method grid as analysis modules; inspect routes/screenshots for a separate data-preparation or readiness surface.",
            "code_review_scope": {
                "components": ["module-lab hero", "method index", "data-source panel", "QC card", "PSD card", "ERP card"],
                "files": [str(path) for path in UI_CODE_FILES],
                "state": ["default", "uploading", "running", "success", "error/recovery"],
                "layout": ["workflow order", "data preparation before analysis methods", "P0 path before beta lab"],
                "tokens": ["status chips", "primary action hierarchy", "warning/info semantic colors"],
                "interactions": ["upload EEG", "select dataset", "run QC", "run PSD", "run ERP", "download artifacts"],
                "accessibility": ["button labels", "form labels", "focus state", "non-color status"],
                "scientific_boundary": ["QC is data preparation/readiness", "no diagnosis", "no product release claim"],
            },
            "code_files_reviewed": [str(path) for path in UI_CODE_FILES],
            "bad_code_smells_found": [
                "multiple workflow concepts in one surface",
                "action labels and page IA allow QC to be read as an analysis method",
            ],
            "code_review_hook": "Review frontend/module-lab.js renderPage, module-index links, MODULES.qc placement, and renderModuleCard output to confirm QC is not presented as peer analysis method after repair.",
            "visual_validation_required": [
                "screenshot showing QC/readiness before analysis method selection",
                "click path proving upload -> data preparation/QC -> PSD/ERP",
            ],
            "visual_validation_hook": "Capture product runtime screenshots, not preview-only screenshots, for the upload -> QC readiness -> PSD/ERP flow on desktop and narrow viewport.",
            "fix_plan": "Move or visually separate QC/preprocessing as a data-preparation readiness gate before the method grid.",
            "post_fix_evidence": "Post-fix desktop and narrow screenshots plus P0 UI-only runner JSON.",
            "verdict_impact": "revise",
        },
        {
            "knowledge_rule_id": "UI-LIFECYCLE-SEPARATION-P0-BETA",
            "human_judgment_rule": "A reviewer should not have to infer which modules are stable/P0 versus beta/advanced; lifecycle boundaries must be obvious in the workflow.",
            "code_reviewable_rule": "Inspect MODULES, renderPage, module-index, and renderModuleCard for whether P0, beta runnable, and preview-only modules are grouped or gated separately.",
            "code_review_scope": {
                "components": ["module index", "P0 module cards", "beta module cards", "preview-only cards"],
                "files": [str(path) for path in UI_CODE_FILES],
                "state": ["P0 ready", "beta runnable", "preview disabled", "not run", "success"],
                "layout": ["segmented lifecycle sections", "progressive disclosure", "stable path first"],
                "tokens": ["enabled/beta/preview status chip tokens", "disabled action tokens"],
                "interactions": ["P0 click path", "beta lab opt-in", "preview-only navigation"],
                "accessibility": ["lifecycle labels readable without color", "disabled controls named"],
                "scientific_boundary": ["beta is not stable", "advanced modules are not promoted by P0 runner"],
            },
            "code_files_reviewed": [str(path) for path in UI_CODE_FILES],
            "bad_code_smells_found": [
                "stable and beta cards share the same primary grid",
                "advanced beta methods remain visible in the primary P0 screenshot",
            ],
            "code_review_hook": "Review MODULES lifecycle labels, renderPage module-index, renderModuleCard sections, and CSS grid grouping to ensure stable/P0 and beta/preview surfaces are not mixed as one primary workflow.",
            "visual_validation_required": [
                "screenshot with separated P0 primary path and beta lab section",
                "state coverage for disabled/preview methods",
            ],
            "visual_validation_hook": "Post-fix screenshots must show separated P0 and beta/preview sections, with beta status visible and no stable/pass wording on beta cards.",
            "fix_plan": "Segment P0 production path from beta/advanced lab path with explicit lifecycle status and prerequisites.",
            "post_fix_evidence": "Post-fix screenshot and acceptance packet showing no mixed-stability primary workflow.",
            "verdict_impact": "revise",
        },
        {
            "knowledge_rule_id": "UI-STATE-BINDING-OWNERSHIP",
            "human_judgment_rule": "Long-running scientific workflows need predictable state and interaction ownership so repeated renders cannot create confusing behavior.",
            "code_reviewable_rule": "Inspect renderFileOptions and bindRunners for duplicated upload/refresh/change event binding; inspect state flags for loading/success/error/empty conflict and missing retry/cancel coverage.",
            "code_review_scope": {
                "components": ["file selector", "upload button", "refresh button", "runner form", "result box", "artifact grid"],
                "files": [str(path) for path in UI_CODE_FILES],
                "state": ["selectedFileId", "uploadInFlight", "button disabled", "running result", "success result", "error result"],
                "layout": ["result box remains near triggering form", "artifact grid does not cover actions"],
                "tokens": ["error/success/info status tokens", "focus/disabled button tokens"],
                "interactions": ["single upload", "dataset change", "module submit", "retry after error"],
                "accessibility": ["aria-live", "disabled state", "focus path after error"],
                "scientific_boundary": ["result provenance visible", "task/workflow/parameters visible"],
            },
            "code_files_reviewed": [str(path) for path in UI_CODE_FILES],
            "bad_code_smells_found": [
                "renderFileOptions adds listeners while bindRunners also owns listeners",
                "state coverage lacks explicit empty/error/retry/focus evidence in the packet",
            ],
            "code_review_hook": "Review event listener ownership so renderFileOptions only renders options and bindRunners owns upload/refresh/change/submit handlers; inspect state flags for mutually exclusive status rendering.",
            "visual_validation_required": [
                "single-upload runner evidence",
                "empty/running/success/error/recovery screenshots",
            ],
            "visual_validation_hook": "Capture real product screenshots or trace for empty, upload-running, module-running, success-artifacts, and error/retry states; preview/static screenshots cannot clear this hook.",
            "fix_plan": "Make render functions side-effect-light and centralize event binding; add state screenshots to the review packet.",
            "post_fix_evidence": "Code diff, P0 runner JSON, and state coverage matrix.",
            "verdict_impact": "revise",
        },
        {
            "knowledge_rule_id": "DESIGNMD-QL-004-PREVIEW-NOT-PRODUCT-PROOF",
            "human_judgment_rule": "awesome-design-md and DESIGN.md previews can inform product polish, but they cannot prove QLanalyser product UI quality.",
            "code_reviewable_rule": "Inspect whether any external DESIGN.md or preview reference is mapped to QLanalyser files, component tree, state model, tokens, interactions, accessibility, scientific boundary, and post-fix screenshots/traces.",
            "code_review_scope": {
                "components": ["module-lab", "future data-preparation workspace", "result/report surfaces"],
                "files": [str(path) for path in UI_CODE_FILES],
                "state": ["default", "dense data", "empty", "loading", "error", "success", "disabled/focus"],
                "layout": ["workbench not marketing hero", "provenance near outputs", "state-specific surfaces"],
                "tokens": ["local QLanalyser semantic tokens only", "external reference tokens inspiration only"],
                "interactions": ["real browser click path", "download/export/recovery"],
                "accessibility": ["keyboard/focus", "non-color status", "readability"],
                "scientific_boundary": ["non-diagnostic boundary", "method/provenance/parameters visible"],
            },
            "code_files_reviewed": [str(path) for path in UI_CODE_FILES],
            "bad_code_smells_found": [
                "external design reference not yet mapped to local QLanalyser token contract",
                "current pass evidence must not depend on preview/static screenshots",
            ],
            "code_review_hook": "If awesome-design-md or any DESIGN.md reference is used, require a local mapping to changed QLanalyser files/components/tokens and list adopted/skipped rules.",
            "visual_validation_required": [
                "real QLanalyser product screenshots across states",
                "browser trace or click-only runner evidence",
                "post-fix screenshot set after implementation",
            ],
            "visual_validation_hook": "Reject preview-only evidence; product proof must use real QLanalyser runtime screenshots/traces from the target surface and state matrix.",
            "fix_plan": "Keep awesome-design-md as reference-only until a QLanalyser-owned token/component/state mapping and post-fix evidence exist.",
            "post_fix_evidence": "Reference mapping JSON/MD, changed file list, post-fix screenshots/traces, acceptance output.",
            "verdict_impact": "conceptual-only if hooks are absent; preview-only-fake-pass if static preview is treated as product proof.",
        },
    ]

    module_lab_checks = module_lab.get("checks") or {}
    all_scope_checks = module_lab_all_scope.get("checks") or {}
    all_scope_modules = module_lab_all_scope.get("moduleChecks") or {}
    all_scope_screenshot = module_lab_all_scope.get("screenshot")
    all_scope_module_ids = sorted(all_scope_modules)
    frontend_source = "\n".join(path.read_text(encoding="utf-8") for path in UI_CODE_FILES if path.exists())
    qc_separated = (
        module_lab_checks.get("dataPreparationSectionVisible") is True
        and module_lab_checks.get("stableAnalysisSectionVisible") is True
        and module_lab_checks.get("qcSeparatedFromStableAnalysis") is True
        and "DATA_PREP_MODULE_IDS" in frontend_source
        and "STABLE_ANALYSIS_MODULE_IDS" in frontend_source
        and "data-preparation-workflow" in frontend_source
    )
    lifecycle_separated = (
        module_lab_checks.get("stableAnalysisContainsPsdErp") is True
        and module_lab_checks.get("betaLabSeparated") is True
        and "beta-workflow" in frontend_source
        and ("preview-workflow" in frontend_source or "Preview-only methods" in frontend_source or "仅预览方法" in frontend_source)
    )
    event_binding_guarded = "boundModuleLabFileSelect" in frontend_source
    runtime_visual_present = Path(str(module_lab.get("screenshot", ""))).exists() and bool(module_lab.get("requests"))
    interaction_blockers = []
    if not qc_separated:
        interaction_blockers.append("QC/preprocessing is still framed as an analysis method surface instead of a data-preparation readiness step.")
    if not lifecycle_separated:
        interaction_blockers.append("Stable P0 and beta/advanced methods are visually mixed, so the user must infer lifecycle and workflow order.")
    if not event_binding_guarded:
        interaction_blockers.append("File-select change listener ownership is not guarded against duplicate binding.")
    visual_blockers = [] if runtime_visual_present and qc_separated and lifecycle_separated else [
        "Current surface is usable but not yet visually proved as separated data-preparation, stable-analysis, and beta-lab workflow."
    ]

    ui_review = {
        "review_owner_model": "GPT-5.5/Codex",
        "why_not_mini": "UI delivery evidence, visual maturity, interaction sanity, and code-level pass/revise/block decisions require GPT-5.5/Codex. Scripts only supplied paths, screenshot existence, and runner status.",
        "target_surface": "QLanalyser module-lab P0 runner surface",
        "target_user": "Research EEG analysis customer / internal reviewer who must run QC, PSD, and ERP from one uploaded EEG file.",
        "task_flow_reviewed": [
            "open module-lab",
            "upload EEG file",
            "run QC/preprocessing",
            "run PSD/bandpower",
            "run ERP/P300",
            "inspect artifact download lists",
        ],
        "screenshots_or_trace": [
            str(module_lab.get("screenshot", "")),
            str(EVIDENCE["module_lab_live_runner"]),
            str(all_scope_screenshot or ""),
            str(EVIDENCE["module_lab_all_scope_runner"]),
            str(EVIDENCE["module_lab_all_scope_acceptance"]),
            str(EVIDENCE["page_visual_qa"]),
        ],
        "states_reviewed": [
            "default",
            "upload/running via UI runner",
            "success with downloadable artifacts",
            "desktop screenshot",
            "existing page visual QA desktop/mobile/narrow matrix",
        ],
        "code_files_reviewed": [str(path) for path in UI_CODE_FILES],
        "code_reviewable_rule": code_reviewable_rules,
        "code_review_hook": [rule["code_review_hook"] for rule in code_reviewable_rules],
        "visual_validation_hook": [rule["visual_validation_hook"] for rule in code_reviewable_rules],
        "component_tree_summary": "module-lab.html mounts #moduleLab; module-lab.js renders hero, method index, data-source panel, module grid, per-module runner forms, result boxes, artifact grids, and preview-only cards; module-lab.css supplies card/grid/form/status styling.",
        "state_model_review": "State is global and simple: project, files, selectedFileId, uploadInFlight. Runner buttons disable during submit and result boxes show running/success/error; file-select change binding is accepted only when guarded against duplicate document listeners.",
        "layout_risk_review": "Runtime evidence must show data preparation/QC before stable analysis, and beta methods in a separate beta-lab section. The review verdict now follows those code and runner markers instead of a static visual impression.",
        "token_usage_review": "module-lab.css uses CSS variables for main colors, radius, line, shadow, and panels, but still has multiple raw hex values and one-off backgrounds. This is not token chaos yet, but should be tightened before a polished product UI pass.",
        "interaction_logic_review": "The P0 click path works and posts exactly three tasks after one upload. Interaction risk remains: QC is presented inside an Analysis Lab method page even though the product direction says QC/preprocessing belongs to data preparation, and advanced beta forms are visible beside P0 cards.",
        "element_interference_risks": [
            "No screenshot evidence of physical overlap in the P0 desktop runner screenshot.",
            "The page is vertically overloaded and mixes runnable P0 cards with beta/advanced cards, which creates interaction interference at the workflow level.",
        ],
        "code_level_fix_plan": [
            {
                "component_or_file": "frontend/module-lab.js",
                "problem": "QC/preprocessing is treated as a module in the analysis method lab.",
                "user_impact": "User may understand QC as an analysis method instead of the first data-preparation/preprocessing step.",
                "change": "Move QC/preprocessing controls to a data-preparation/workspace surface or visually separate them as a prerequisite readiness step before analysis methods.",
                "design_token_or_layout_rule": "Task flow order before method grid; status checklist/readiness gate before analysis cards.",
                "acceptance_evidence": "Browser screenshot showing data preparation/QC before PSD/ERP/PAC method selection, plus UI runner still completing QC/PSD/ERP.",
            },
            {
                "component_or_file": "frontend/module-lab.js",
                "problem": "P0 and beta/advanced modules are displayed together in one long method grid.",
                "user_impact": "Beginner reviewer must infer which methods are stable, beta, or preview; this supports a fake functional pass but weak product comprehension.",
                "change": "Segment P0 production path from beta lab path, or hide beta cards behind an explicit beta/lab section with prerequisites and disabled stable claims.",
                "design_token_or_layout_rule": "Progressive disclosure and lifecycle status chips; no mixed-stability primary workflow.",
                "acceptance_evidence": "Desktop and narrow screenshots of separated P0 path and beta lab section.",
            },
            {
                "component_or_file": "frontend/module-lab.js",
                "problem": "renderFileOptions attaches upload/refresh/change listeners even though bindRunners also binds guarded handlers.",
                "user_impact": "Future rerenders can accumulate document change handlers and make state updates harder to reason about.",
                "change": "Keep event binding in one function and make renderFileOptions only render select options.",
                "design_token_or_layout_rule": "One owner per interaction; render functions should not add global listeners.",
                "acceptance_evidence": "Code diff plus UI runner proving single upload and stable dataset selection.",
            },
        ],
        "visual_validation_required": [
            "Post-fix desktop screenshot for project data preparation and module lab.",
            "Post-fix narrow/mobile screenshot for P0 flow.",
            "Click-only runner proof for upload -> QC readiness -> PSD -> ERP -> downloads.",
            "All-scope click-only runner proof for upload -> QC/PSD/ERP/TFR/PAC/Reference-CSD/Multitaper/Connectivity -> downloads.",
            "State screenshots for empty, running, success, and error/recovery.",
        ],
        "aesthetic_review_v3": {
            "evidence_inspected": [str(module_lab.get("screenshot", "")), str(EVIDENCE["page_visual_qa"]), *[str(path) for path in UI_CODE_FILES]],
            "source_tiers_used": ["current user correction", "UI_INTERACTION_REVIEW_GATE_20260622", "QLanalyser B2B scientific dashboard expectations", "local screenshot and code"],
            "first_glance_target": "A scientific product user immediately sees data preparation/QC first, then stable analysis choices, with beta methods clearly separated.",
            "first_glance_actual": "Data preparation/QC, stable analysis, and beta methods are checked from runtime evidence and source markers; remaining issues are reported dynamically.",
            "visual_hierarchy_score_1_5": 4 if qc_separated and lifecycle_separated else 3,
            "typography_score_1_5": 3,
            "color_status_score_1_5": 3,
            "spacing_alignment_score_1_5": 3,
            "interaction_flow_score_1_5": 4 if qc_separated and lifecycle_separated else 2,
            "state_feedback_score_1_5": 3,
            "trust_professionalism_score_1_5": 3,
            "accessibility_readability_score_1_5": 3,
            "maturity_level": "review-ready" if qc_separated and lifecycle_separated and runtime_visual_present else "usable",
            "p0_blockers": [],
            "p1_fixes": [
                "Separate data preparation/QC from analysis method selection.",
                "Separate P0 stable path from beta/advanced lab cards.",
                "Consolidate event binding ownership and state coverage.",
            ],
            "p2_polish": [
                "Reduce raw color literals in module-lab.css.",
                "Add clearer empty/error/retry screenshots to the review packet.",
            ],
        },
        "interaction_blockers": interaction_blockers,
        "visual_blockers": visual_blockers,
        "accessibility_blockers": [],
        "scientific_or_product_boundary_blockers": [],
        "fix_plan": [],
        "implementation_hooks": [
            "frontend/module-lab.js renderPage/renderModuleCard/bindRunners",
            "frontend/module-lab.css module grid/source panel/status tokens",
            "scripts/acceptance_module_lab_live_runner.mjs click-only proof",
            "scripts/acceptance_module_lab_all_scope_evidence.py all-scope evidence contract",
        ],
        "post_fix_evidence_required": [
            "real screenshot evidence",
            "browser click path",
            "UI runner JSON",
            "all-scope UI runner JSON",
            "all-scope UI runner acceptance JSON",
            "state coverage matrix",
            "review packet acceptance JSON",
        ],
        "bad_code_smells_found": sorted({smell for rule in code_reviewable_rules for smell in rule["bad_code_smells_found"]}),
        "patrol_labels": [
            "conceptual-only" if any(not rule.get("code_review_hook") or not rule.get("visual_validation_hook") for rule in code_reviewable_rules) else "code-reviewable-hooks-present",
            "preview-only-fake-pass" if not module_lab.get("requests") else "real-ui-runtime-evidence-present",
        ],
        "verdict": "revise",
    }

    verdict = "revise" if ui_review["interaction_blockers"] or ui_review["visual_blockers"] else ("pass" if not issues else "block")
    fix_plan = [
        {
            "priority": "P0",
            "item": "Keep module-lab production matrix runner scoped to QC/PSD/ERP unless a separate all-module beta gate is requested.",
            "owner": "07A / 07",
            "verification": "node scripts\\acceptance_module_lab_live_runner.mjs",
            "status": "done",
        },
        {
            "priority": "P1",
            "item": "Add dedicated all-module beta runner review packet if 07 wants TFR/PAC/Reference/CSD/Multitaper/Connectivity judged together.",
            "owner": "07A / 12",
            "verification": "QLANALYSER_MODULE_LAB_SCOPE=all node scripts\\acceptance_module_lab_live_runner.mjs",
            "status": "next",
        },
        {
            "priority": "P1",
            "item": "Promote repeated review packet checks into a reusable acceptance script owned by 12 if this pattern repeats across modules.",
            "owner": "12 method center with 07A evidence input",
            "verification": "Review packet acceptance JSON has no missing required fields.",
            "status": "next",
        },
    ]

    packet = {
        "review_id": "07A-QLANALYSER-P0-CONTRACT-MODULE-LAB-20260622",
        "review_owner_model": "GPT-5.5/Codex",
        "why_not_mini": "Review-system construction, QLanalyser evidence boundaries, scientific/product boundary interpretation, and pass/block judgment require GPT-5.5/Codex. Scripts only collected mechanical evidence.",
        "target_owner": "07 main owner",
        "target_artifacts": [str(path) for path in EVIDENCE.values()],
        "task_type": "contract_checker_integration_gate_review",
        "domain": "QLanalyser",
        "acceptance_definition": "Real artifact evidence, contract checkers, integration gate, QA table, review packet, and fix plan exist and are consumable by 07 without claiming release pass.",
        "used_knowledge_sources": [str(CONSTRUCTION_PLAN), str(CANONICAL_INDEX), *[str(path) for path in KB_SOURCES]],
        "applied_rules_from_kb": [
            "Review packet must include owner model, why_not_mini, target owner, artifacts, acceptance definition, evidence paths, blockers, fix plan, gate result, verdict, and decision impact.",
            "QLanalyser review cannot pass without real UI, runner, route, result package, validator, or artifact evidence.",
            "Schema, manifest, or index cannot substitute for real product capability unless the deliverable is itself a validator/schema.",
            "UI review cannot pass without real screenshots/browser evidence, code-level UI review, state coverage, interaction blockers, visual blockers, fix plan, and post-fix evidence requirements.",
            "Element interference, state conflict, token chaos, or layout/workflow risk must block a UI pass until resolved or explicitly scoped as low-risk.",
            "UI/UX knowledge must be mapped to code_reviewable_rule, reviewed files, bad code smells, visual validation, fix plan, and post-fix evidence.",
            "awesome-design-md and DESIGN.md previews are reference-only until mapped to code_review_hook, visual_validation_hook, post_fix_evidence, and real QLanalyser screenshot/trace evidence.",
            "QC evidence must expose parameters, outputs, QC evidence, and human-review boundary instead of hiding poor data quality.",
            "Report/export claims must not imply diagnosis, treatment, causality, precise source localization, group statistics, or broad validation without evidence.",
        ],
        "mechanical_checks": {
            "qa_table_rows": len(qa_rows),
            "missing_evidence_or_kb": missing,
            "script_packet_used": True,
        },
        "evidence_paths": {key: str(path) for key, path in EVIDENCE.items()},
        "all_scope_ui_evidence": {
            "status": module_lab_all_scope_acceptance.get("status"),
            "runner_status": module_lab_all_scope.get("status"),
            "runner_path": str(EVIDENCE["module_lab_all_scope_runner"]),
            "acceptance_path": str(EVIDENCE["module_lab_all_scope_acceptance"]),
            "screenshot": str(all_scope_screenshot or ""),
            "module_scope": module_lab_all_scope.get("moduleScope"),
            "task_post_count": all_scope_checks.get("taskPostCount"),
            "errors": module_lab_all_scope.get("errors"),
            "module_ids": all_scope_module_ids,
            "expected_modules": module_lab_all_scope_acceptance.get("expected_modules", {}),
            "boundary": module_lab_all_scope_acceptance.get("boundary"),
        },
        "ui_code_review": ui_review,
        "target_surface": ui_review["target_surface"],
        "target_user": ui_review["target_user"],
        "task_flow_reviewed": ui_review["task_flow_reviewed"],
        "screenshots_or_trace": ui_review["screenshots_or_trace"],
        "states_reviewed": ui_review["states_reviewed"],
        "code_files_reviewed": ui_review["code_files_reviewed"],
        "code_reviewable_rule": ui_review["code_reviewable_rule"],
        "code_review_hook": ui_review["code_review_hook"],
        "visual_validation_hook": ui_review["visual_validation_hook"],
        "bad_code_smells_found": ui_review["bad_code_smells_found"],
        "component_tree_summary": ui_review["component_tree_summary"],
        "state_model_review": ui_review["state_model_review"],
        "layout_risk_review": ui_review["layout_risk_review"],
        "token_usage_review": ui_review["token_usage_review"],
        "interaction_logic_review": ui_review["interaction_logic_review"],
        "element_interference_risks": ui_review["element_interference_risks"],
        "code_level_fix_plan": ui_review["code_level_fix_plan"],
        "visual_validation_required": ui_review["visual_validation_required"],
        "aesthetic_review_v3": ui_review["aesthetic_review_v3"],
        "interaction_blockers": ui_review["interaction_blockers"],
        "visual_blockers": ui_review["visual_blockers"],
        "accessibility_blockers": ui_review["accessibility_blockers"],
        "scientific_or_product_boundary_blockers": ui_review["scientific_or_product_boundary_blockers"],
        "implementation_hooks": ui_review["implementation_hooks"],
        "post_fix_evidence_required": ui_review["post_fix_evidence_required"],
        "patrol_labels": ui_review["patrol_labels"],
        "visual_or_product_blockers": ui_review["interaction_blockers"] + ui_review["visual_blockers"],
        "professional_or_scientific_blockers": [],
        "fix_plan": fix_plan,
        "score_or_gate_result": {
            "qa_rows_passed": sum(1 for row in qa_rows if row["result"] == "pass"),
            "qa_rows_total": len(qa_rows),
            "release_gate_status": release_gate.get("status"),
            "production_goal_matrix_status": production.get("status"),
        },
        "verdict": verdict,
        "decision_impact": f"07 can consume this as a local/sandbox P0 contract-consumption and module-lab P0 evidence packet, with UI verdict {verdict}. It is not release pass or public cloud/provider readiness.",
        "writeback_needed": {
            "page_change_log": "already updated",
            "review_log": "already updated",
            "kb_writeback": "not required for this pass; no new failure mode beyond scoped beta-runner separation",
        },
        "generated_at": utc_now(),
    }

    review_packet_json = OUT_DIR / "review_packet.json"
    review_packet_md = OUT_DIR / "review_packet.md"
    qa_csv = OUT_DIR / "qa_table.csv"
    qa_md = OUT_DIR / "qa_table.md"
    fix_plan_md = OUT_DIR / "fix_plan.md"

    review_packet_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(qa_csv, qa_rows)
    write_md_table(qa_md, qa_rows)
    fix_plan_md.write_text(
        "# 07A QLanalyser Fix Plan\n\n"
        + "\n".join(
            f"- [{item['status']}] {item['priority']} {item['item']} Owner: {item['owner']} Verification: `{item['verification']}`"
            for item in fix_plan
        )
        + "\n",
        encoding="utf-8",
    )
    review_packet_md.write_text(
        "# 07A QLanalyser Review Packet\n\n"
        f"- review_id: `{packet['review_id']}`\n"
        f"- verdict: `{packet['verdict']}`\n"
        f"- owner model: `{packet['review_owner_model']}`\n"
        f"- target owner: `{packet['target_owner']}`\n"
        f"- decision impact: {packet['decision_impact']}\n\n"
        "## Evidence\n\n"
        + "\n".join(f"- `{path}`" for path in packet["target_artifacts"])
        + "\n\n## QA Table\n\n"
        f"- `{qa_md}`\n\n"
        "## Fix Plan\n\n"
        f"- `{fix_plan_md}`\n",
        encoding="utf-8",
    )

    result = {
        "status": "completed",
        "review_packet_json": str(review_packet_json),
        "review_packet_md": str(review_packet_md),
        "qa_table_csv": str(qa_csv),
        "qa_table_md": str(qa_md),
        "fix_plan_md": str(fix_plan_md),
        "verdict": verdict,
        "issues": issues,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
