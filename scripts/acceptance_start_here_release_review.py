from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START_HERE = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "START_HERE_RELEASE_REVIEW.md"

REQUIRED_PHRASES = [
    "Local/sandbox product loop: review-ready with evidence.",
    "Public cloud / production release: blocked on external inputs.",
    "python scripts\\run_release_review_gate.py",
    "work\\release_evidence\\20260620-v01-acceptance\\release_gate_summary.md",
    "work\\release_evidence\\20260620-v01-acceptance\\acceptance_release_review_gate_steps.json",
    "work\\release_evidence\\20260620-v01-acceptance\\acceptance_release_manifest_consistency.json",
    "work\\release_evidence\\20260620-v01-acceptance\\production_goal_requirement_matrix.md",
    "work\\release_evidence\\20260620-v01-acceptance\\production_goal_completion_audit.md",
    "work\\release_evidence\\mainline_eeg_review\\mainline_eeg_review_bridge_acceptance.json",
    "work\\release_evidence\\checkpoints\\2026-06-22-0502-07a-mainline-eeg-bridge-checkpoint.md",
    "work\\release_evidence\\checkpoints\\2026-06-22-0505-07a-mainline-eeg-handoff.md",
    "work\\release_evidence\\checkpoints\\2026-06-22-0506-07a-mainline-eeg-brief.md",
    "work\\release_evidence\\checkpoints\\2026-06-22-0507-07a-mainline-eeg-index.md",
    "work\\release_evidence\\20260620-aliyun-staging\\owner_input_checklist.md",
    "work\\release_evidence\\20260620-aliyun-staging\\owner_decision_packet.md",
    "work\\release_evidence\\module_lab_preview_selectors\\acceptance_module_lab_preview_selectors.json",
    "Sandbox payment is not production payment.",
    "Sandbox email/SMS/WeChat auth is not production provider evidence.",
    "Local queue-ready lifecycle is not distributed worker deployment evidence.",
    "Historical DeepSeek copy gate does not cover the latest V1 public-status copy",
    "module-lab preview selectors are preview-only boundary evidence, not stable runnable product paths.",
    "Mainline EEG bridge/handoff/brief/index packets are review-integration evidence, not release pass.",
]


def main() -> int:
    text = START_HERE.read_text(encoding="utf-8")
    missing = [phrase for phrase in REQUIRED_PHRASES if phrase not in text]
    result = {
        "status": "passed" if not missing else "failed",
        "path": str(START_HERE),
        "required_phrases": len(REQUIRED_PHRASES),
        "missing": missing,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
