from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "workspace-inventory" / "baseline-safety-scan.json"
TEXT_SIZE_LIMIT = 5 * 1024 * 1024

SIGNATURES = {
    "private-key-block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "openai-style-key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "bearer-token": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{20,}={0,2}\b", re.IGNORECASE),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
}

ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd)\b"
    r"\s*[:=]\s*([\"'])([^\"'\r\n]{8,})\2"
)
PLACEHOLDER_RE = re.compile(
    r"(?i)(example|sample|placeholder|dummy|fake|test|changeme|your[_ -]|<[^>]+>|\$\{|os\.environ|getenv|settings\.)"
)


def trackable_paths() -> list[Path]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    paths: list[Path] = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        raw = line[3:]
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        path = ROOT / raw
        if path.is_file():
            paths.append(path)
    return sorted(set(paths))


def is_probably_text(path: Path) -> bool:
    if path.stat().st_size > TEXT_SIZE_LIMIT:
        return False
    try:
        sample = path.read_bytes()[:8192]
    except OSError:
        return False
    return b"\x00" not in sample


def scan_file(path: Path) -> list[dict[str, object]]:
    if not is_probably_text(path):
        return []
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return []
    findings: list[dict[str, object]] = []
    for signature_name, pattern in SIGNATURES.items():
        for match in pattern.finditer(text):
            findings.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "line": text.count("\n", 0, match.start()) + 1,
                    "rule": signature_name,
                    "severity": "block",
                }
            )
    for match in ASSIGNMENT_RE.finditer(text):
        value = match.group(3)
        if PLACEHOLDER_RE.search(value):
            continue
        findings.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "line": text.count("\n", 0, match.start()) + 1,
                "rule": f"literal-{match.group(1).lower()}",
                "severity": "review",
            }
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan baseline candidates without recording secret values.")
    parser.add_argument("--fail-on-block", action="store_true")
    args = parser.parse_args()

    paths = trackable_paths()
    findings = [finding for path in paths for finding in scan_file(path)]
    counts = Counter(str(finding["severity"]) for finding in findings)
    payload = {
        "schema_version": "baseline-safety-scan-v1",
        "trackable_file_count": len(paths),
        "scanned_text_file_count": sum(is_probably_text(path) for path in paths),
        "finding_counts": dict(sorted(counts.items())),
        "findings": findings,
        "privacy": "Matched values are intentionally not recorded.",
        "limitations": [
            "Pattern scanning cannot prove the absence of all secrets or personal data.",
            "Binary and files larger than 5 MiB are not content-scanned; Git ignore and large-file review cover them.",
            "Review findings require manual classification before commit.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"trackable_files": len(paths), "findings": len(findings), "counts": counts}))
    if args.fail_on_block and counts.get("block", 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
