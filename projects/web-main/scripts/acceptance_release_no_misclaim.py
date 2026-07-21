from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "aliyun_staging_preflight.json"
OUTPUT = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_no_misclaim.json"

SCANNED_FILES = [
    ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "START_HERE_RELEASE_REVIEW.md",
    ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_gate_summary.md",
    ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_gate_summary.json",
    ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "production_goal_completion_audit.md",
    ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "production_goal_requirement_matrix.md",
    ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "production_goal_requirement_matrix.json",
    ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "owner_input_checklist.md",
    ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "owner_decision_packet.md",
]

FORBIDDEN_WHEN_PREFLIGHT_BLOCKED = [
    re.compile(r"\bpublic cloud ready\b\s*[:=]\s*true\b", re.IGNORECASE),
    re.compile(r"\bpublic_cloud_ready\b[\"']?\s*[:=]\s*true\b", re.IGNORECASE),
    re.compile(r"\bcloud_ready\b[\"']?\s*[:=]\s*true\b", re.IGNORECASE),
    re.compile(r"\bready_for_release_review\b", re.IGNORECASE),
    re.compile(r"\bready_for_strict_staging\b", re.IGNORECASE),
    re.compile(r"\bproduction ready\b", re.IGNORECASE),
    re.compile(r"\bready for production\b", re.IGNORECASE),
    re.compile(r"公网[^。\n\r]*(已完成|已就绪|可上线)", re.IGNORECASE),
    re.compile(r"生产[^。\n\r]*(已完成|已就绪|可上线)", re.IGNORECASE),
]

REQUIRED_SAFE_PHRASES = [
    "Local/sandbox",
    "blocked",
    "external",
]


def preflight_is_blocked() -> bool:
    payload = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    failed = [check for check in payload.get("checks", []) if check.get("status") == "fail"]
    return payload.get("status") == "blocked_missing_prerequisites" and not failed


def scan_file(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    findings: list[dict[str, Any]] = []
    for pattern in FORBIDDEN_WHEN_PREFLIGHT_BLOCKED:
        match = pattern.search(text)
        if match:
            findings.append(
                {
                    "path": str(path),
                    "pattern": pattern.pattern,
                    "offset": match.start(),
                    "match": match.group(0),
                }
            )
    return findings


def main() -> int:
    missing_files = [str(path) for path in SCANNED_FILES if not path.exists()]
    blocked = preflight_is_blocked()
    findings: list[dict[str, Any]] = []
    if blocked:
        for path in SCANNED_FILES:
            if path.exists():
                findings.extend(scan_file(path))

    start_here = SCANNED_FILES[0].read_text(encoding="utf-8") if SCANNED_FILES[0].exists() else ""
    missing_safe_phrases = [phrase for phrase in REQUIRED_SAFE_PHRASES if phrase not in start_here]
    status = "passed" if blocked and not missing_files and not findings and not missing_safe_phrases else "failed"
    result = {
        "status": status,
        "preflight_blocked": blocked,
        "scanned_files": [str(path) for path in SCANNED_FILES],
        "missing_files": missing_files,
        "forbidden_claims": findings,
        "missing_safe_phrases_in_start_here": missing_safe_phrases,
        "policy": "When strict preflight is blocked, release artifacts must not claim public cloud or production readiness.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
