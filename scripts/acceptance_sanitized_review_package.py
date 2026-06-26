from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "work" / "release_evidence" / "20260620-v01-sanitized-review-package.json"
OUTPUT = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_sanitized_review_package.json"

REQUIRED_MEMBERS = [
    "20260620-v01-sanitized-review/README.md",
    "20260620-v01-sanitized-review/evidence_manifest.sanitized.json",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-v01-acceptance/START_HERE_RELEASE_REVIEW.md",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-v01-acceptance/release_gate_summary.md",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-v01-acceptance/production_goal_requirement_matrix.json",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-v01-acceptance/production_goal_requirement_matrix.md",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-v01-acceptance/release_review_gate_run.core.json",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-v01-acceptance/acceptance_release_review_gate_steps.json",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-v01-acceptance/acceptance_utf8_text_preflight.json",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-v01-acceptance/acceptance_visual_layout_design_spec.json",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-v01-acceptance/acceptance_analysis_module_contract.json",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-v01-acceptance/acceptance_cro_traceability_contract.json",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-v01-acceptance/acceptance_release_manifest_consistency.json",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-v01-acceptance/release_no_misclaim.json",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-v01-acceptance/acceptance_owner_decision_packet.json",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-v01-public/PUBLIC_DEPLOYMENT_EVIDENCE.md",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-v01-public/acceptance_ops_ui_public_after_deploy.json",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-aliyun-staging/owner_input_checklist.md",
    "20260620-v01-sanitized-review/files/work/release_evidence/20260620-aliyun-staging/owner_decision_packet.md",
]

TEXT_SUFFIXES = {".csv", ".html", ".json", ".log", ".md", ".txt", ".xml", ".yaml", ".yml"}

SENSITIVE_PATTERNS = [
    ("bearer_token", re.compile(r"Bearer\s+(?!<redacted>)[A-Za-z0-9_.\-]+")),
    ("qls_token", re.compile(r"qls_(?!<redacted>)[A-Za-z0-9_\-]+")),
    ("email", re.compile(r"(?<!<email-redacted>\s)[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    (
        "internal_id",
        re.compile(
            r"\b(acct|invoice|recharge|task|proj|eeg|report|artifact|inbox|billtx|audit|usage)_"
            r"(?!<redacted>\b)[A-Za-z0-9]*\d[A-Za-z0-9]*\b"
        ),
    ),
    (
        "secret_field",
        re.compile(
            r"\b(ACCESS_KEY_ID|ACCESS_KEY_SECRET|SECRET|TOKEN|PASSWORD)\b\s*[:=]\s*"
            r"[\"']?(?!<redacted>|missing\b|todo\b|false\b|true\b|null\b)([^\"'\s,}]+)",
            re.IGNORECASE,
        ),
    ),
]


def scan_zip_text_members(zip_path: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            suffix = Path(member.filename).suffix.lower()
            if member.is_dir() or suffix not in TEXT_SUFFIXES:
                continue
            raw = archive.read(member)
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                findings.append(
                    {
                        "member": member.filename,
                        "pattern": "text_decode",
                        "detail": "text-like file is not utf-8 decodable",
                    }
                )
                continue
            for pattern_name, pattern in SENSITIVE_PATTERNS:
                match = pattern.search(text)
                if match:
                    findings.append(
                        {
                            "member": member.filename,
                            "pattern": pattern_name,
                            "offset": match.start(),
                        }
                    )
    return findings


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    zip_path = Path(manifest["zip_path"])
    with zipfile.ZipFile(zip_path) as archive:
        members = set(archive.namelist())
    missing = [item for item in REQUIRED_MEMBERS if item not in members]
    sensitive_findings = scan_zip_text_members(zip_path)
    result = {
        "status": "passed"
        if manifest.get("status") == "passed" and zip_path.exists() and not missing and not sensitive_findings
        else "failed",
        "zip_path": str(zip_path),
        "zip_bytes": manifest.get("zip_bytes"),
        "file_count": manifest.get("file_count"),
        "missing": missing,
        "sensitive_findings": sensitive_findings,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
