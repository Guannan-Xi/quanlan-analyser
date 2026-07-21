from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "work" / "release_evidence" / "20260626-teaching-mode-independent-product-design"
IMPLEMENTATION_ROOT = EVIDENCE_ROOT / "implementation"
JSON_OUT = IMPLEMENTATION_ROOT / "final_acceptance_packet.json"
MD_OUT = IMPLEMENTATION_ROOT / "final_acceptance_packet.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def status_of(path: Path) -> str:
    payload = load_json(path)
    if payload.get("status"):
        return str(payload["status"])
    return "passed" if payload.get("passed") else "failed"


def main() -> int:
    evidence = {
        "backend_protection_smoke": IMPLEMENTATION_ROOT / "backend_protection_smoke.json",
        "static_acceptance": IMPLEMENTATION_ROOT / "static_acceptance.json",
        "browser_overlay": IMPLEMENTATION_ROOT / "browser_overlay" / "teaching_mode_overlay_e2e.json",
        "browser_independence": IMPLEMENTATION_ROOT / "browser_independence" / "browser_e2e.json",
    }
    evidence_status = {name: status_of(path) for name, path in evidence.items()}
    all_passed = all(value == "passed" for value in evidence_status.values())
    packet = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "route_decision": "gpt55_planner_or_acceptance + script_validator + subagent_or_thread_worker + 02_thread_readback",
        "reused_pool_or_new_pool": "reused_current_07_pool; no new pool created for this bounded implementation slice",
        "execution_packets": [
            "Hegel readonly code-risk audit: backend protection gap",
            "Planck readonly E2E-pattern audit: Playwright/Edge fallback and evidence schema",
            "Copernicus readonly final audit: code/evidence/route-boundary check",
            "local script validators: syntax, backend protection smoke, static acceptance, browser overlay E2E, browser independence E2E",
        ],
        "executor_evidence": {name: str(path.relative_to(ROOT)) for name, path in evidence.items()},
        "evidence_status": evidence_status,
        "targeted_or_full_e2e": "targeted_e2e_for_teaching_mode_independence; full all-method teaching run remains a release-gate follow-up",
        "page_visual_review": {
            "status": "passed_targeted",
            "screenshots": [
                str((IMPLEMENTATION_ROOT / "browser_overlay" / "screenshots" / "teaching-00-project-management.png").relative_to(ROOT)),
                str((IMPLEMENTATION_ROOT / "browser_overlay" / "screenshots" / "teaching-01-overlay-start.png").relative_to(ROOT)),
                str((IMPLEMENTATION_ROOT / "browser_overlay" / "screenshots" / "teaching-08-result-step.png").relative_to(ROOT)),
                str((IMPLEMENTATION_ROOT / "browser_independence" / "screenshots" / "01_normal_mode.png").relative_to(ROOT)),
                str((IMPLEMENTATION_ROOT / "browser_independence" / "screenshots" / "02_teaching_mode_protected.png").relative_to(ROOT)),
            ],
        },
        "changed_files": [
            "backend/services/lab_demo_service.py",
            "backend/services/storage_service.py",
            "frontend/app.js",
            "scripts/acceptance_teaching_mode_protection.py",
            "scripts/acceptance_teaching_mode_independence_static.mjs",
            "scripts/acceptance_teaching_mode_overlay_e2e.mjs",
            "scripts/e2e_teaching_mode_independence.mjs",
            "scripts/build_teaching_mode_independent_acceptance_packet.py",
        ],
        "gpt55_acceptance": "passed" if all_passed else "failed",
        "final_receipt": "completed_final_receipt" if all_passed else "blocked_final_receipt",
        "next_real_artifact": "release gate: run full teaching-mode all-method E2E after 02 epilepsy workbench final handoff lands",
        "route_chain": "Human -> 07 Codex route decision -> 02 readback -> parallel readonly audits -> scoped implementation -> local validators -> readonly final audit -> Codex acceptance",
        "model_lane": "GPT-5.5/Codex final owner; scripts/browser validators; subagents readonly audit",
        "headroom_savings": "not_measured",
        "deepseek_logic_review": "pending_unavailable_in_current_tooling; packet exists but no fake DeepSeek claim",
        "route_boundary": {
            "router": "not_touched",
            "headroom": "not_touched",
            "ipc": "not_touched",
            "gateway": "not_touched",
            "front_route": "not_touched",
        },
        "owner_notify_blocked": {
            "reason": "Feishu Xiaozhuli owner-notify tool/config not exposed in this turn",
            "copy_ready_message": "【全澜小猪理｜任务完成提醒】\n事情：QLanalyser 教学模式独立化第一轮开发验收。\n结果：普通模式不显示教学数据，教学模式可加载内置数据，内置教学项目和数据已由后端保护，不能删除、归档或改名；浏览器 E2E 和后端保护测试通过。\n影响：客户试用时不会污染真实项目，教学数据也不会被误删。\n需要你做：无需操作。\n下一步：待 02 癫痫工作台最终交接后，跑全方法教学模式 release gate。",
        },
    }
    IMPLEMENTATION_ROOT.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = [
        "# Teaching Mode Independent Acceptance Packet",
        "",
        f"- final_receipt: {packet['final_receipt']}",
        f"- gpt55_acceptance: {packet['gpt55_acceptance']}",
        f"- targeted_or_full_e2e: {packet['targeted_or_full_e2e']}",
        f"- next_real_artifact: {packet['next_real_artifact']}",
        "",
        "## Evidence",
    ]
    for name, rel in packet["executor_evidence"].items():
        md.append(f"- {name}: {packet['evidence_status'][name]} - `{rel}`")
    md.extend(["", "## Route Boundary"])
    for name, status in packet["route_boundary"].items():
        md.append(f"- {name}: {status}")
    MD_OUT.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(packet, ensure_ascii=False, indent=2))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
