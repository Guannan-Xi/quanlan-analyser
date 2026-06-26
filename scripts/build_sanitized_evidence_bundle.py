from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "evidence_manifest.json"
DEFAULT_OUTPUT = ROOT / "work" / "release_evidence" / "20260620-v01-sanitized-review"
DEFAULT_SCREENSHOT_DIR = ROOT / "work" / "release_evidence" / "20260620-page-visual-qa" / "screenshots"

DEFAULT_EXTERNAL_SCREENSHOT_PREFIXES = (
    "preset-analysis-library",
    "lab-workbench",
    "customer-dashboard",
    "customer-billing",
    "customer-inbox-empty",
    "customer-register-wechat",
    "admin-overview",
    "customer-report-download",
)

SENSITIVE_SCREENSHOT_PREFIXES = (
    "customer-login",
    "customer-register-email",
    "customer-register-phone",
    "customer-invoice",
    "qc-data-preparation-lab",
    "admin-operations",
    "admin-finance",
)


REDACTIONS = [
    (re.compile(r"Bearer\s+[A-Za-z0-9_.\-]+"), "Bearer <redacted>"),
    (re.compile(r"qls_[A-Za-z0-9_\-]+"), "qls_<redacted>"),
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "<email-redacted>"),
    (re.compile(r"\b(acct|invoice|recharge|task|proj|eeg|report|artifact|inbox|billtx|audit|usage)_[A-Za-z0-9]*\d[A-Za-z0-9]*\b"), r"\1_<redacted>"),
    (re.compile(r"\b(ACCESS_KEY_ID|ACCESS_KEY_SECRET|SECRET|TOKEN|PASSWORD)\b(\s*[:=]\s*[\"']?)(?!<redacted>|missing\b|todo\b|false\b|true\b|null\b)([^\"'\s,}]+)", re.IGNORECASE), r"\1\2<redacted>"),
]


def redact_text(value: str) -> str:
    result = value
    for pattern, replacement in REDACTIONS:
        result = pattern.sub(replacement, result)
    return result


def redact_json(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_json(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_json(item) for key, item in value.items()}
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def copy_redacted_text(source: Path, target: Path) -> None:
    text = source.read_text(encoding="utf-8", errors="replace")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(redact_text(text), encoding="utf-8")


def relative_under_root(path: Path) -> Path:
    try:
        return path.resolve().relative_to(ROOT)
    except ValueError:
        return Path(path.name)


def redaction_regions(filename: str, width: int, height: int) -> list[dict[str, Any]]:
    name = filename.lower()
    regions: list[dict[str, Any]] = []

    def add(x1: float, y1: float, x2: float, y2: float, reason: str) -> None:
        left = max(0, min(width, int(x1)))
        top = max(0, min(height, int(y1)))
        right = max(left, min(width, int(x2)))
        bottom = max(top, min(height, int(y2)))
        if right > left and bottom > top:
            regions.append({"box": [left, top, right, bottom], "reason": reason})

    if name.startswith("admin-"):
        if width >= 900:
            add(width * 0.16, height * 0.10, width, height, "admin tables, metrics, account emails, task and invoice records")
        else:
            add(0, height * 0.18, width, height, "mobile admin tables, account emails, task and invoice records")
    elif name.startswith("customer-login") or name.startswith("customer-register"):
        if width >= 900:
            add(width * 0.55, height * 0.08, width * 0.98, min(height, height * 0.92), "login/register form values and demo credentials")
        else:
            add(width * 0.04, height * 0.12, width * 0.96, min(height, height * 0.72), "login/register form values and demo credentials")
    elif name.startswith("customer-invoice"):
        if width >= 900:
            add(width * 0.50, height * 0.20, width * 0.98, min(height, height * 0.82), "invoice form fields and recipient details")
        else:
            add(width * 0.04, height * 0.28, width * 0.96, min(height, height * 0.92), "invoice form fields and recipient details")
    elif name.startswith("customer-inbox"):
        if width >= 900:
            add(width * 0.48, height * 0.22, width * 0.98, min(height, height * 0.82), "inbox rows and attachment metadata")
        else:
            add(width * 0.04, height * 0.30, width * 0.96, min(height, height * 0.92), "inbox rows and attachment metadata")
    elif name.startswith("qc-data-preparation-lab"):
        if width >= 900:
            add(width * 0.04, height * 0.32, width * 0.98, height, "QC file ids, plan state, preview evidence, and plan JSON")
        else:
            add(width * 0.04, height * 0.28, width * 0.96, height, "QC file ids, plan state, preview evidence, and plan JSON")

    return regions


def sanitize_screenshot(source: Path, target: Path) -> dict[str, Any]:
    with Image.open(source) as image:
        sanitized = image.convert("RGBA")
    draw = ImageDraw.Draw(sanitized)
    regions = redaction_regions(source.name, sanitized.width, sanitized.height)
    for region in regions:
        left, top, right, bottom = region["box"]
        draw.rectangle([left, top, right, bottom], fill=(238, 242, 247, 255), outline=(15, 23, 42, 255), width=2)
        draw.text((left + 10, top + 10), "REDACTED FOR EXTERNAL REVIEW", fill=(15, 23, 42, 255))
    draw.rectangle([8, 8, min(sanitized.width - 8, 360), 34], fill=(15, 23, 42, 230))
    draw.text((16, 14), "Sanitized review copy", fill=(255, 255, 255, 255))
    target.parent.mkdir(parents=True, exist_ok=True)
    sanitized.convert("RGB").save(target, "PNG")
    return {
        "source": str(source),
        "target": str(target),
        "width": sanitized.width,
        "height": sanitized.height,
        "redaction_regions": regions,
    }


def matches_prefix(filename: str, prefixes: tuple[str, ...]) -> bool:
    name = filename.lower()
    return any(name.startswith(prefix) for prefix in prefixes)


def sanitize_screenshots(source_dir: Path, output_dir: Path, include_sensitive: bool = False) -> dict[str, Any]:
    copied: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    if not source_dir.exists():
        return {"status": "skipped", "reason": "source_dir_missing", "source_dir": str(source_dir), "copied": copied, "skipped": skipped}
    target_dir = output_dir / "screenshots-sanitized"
    for source in sorted(source_dir.glob("*.png")):
        if matches_prefix(source.name, SENSITIVE_SCREENSHOT_PREFIXES) and not include_sensitive:
            skipped.append({"source": str(source), "reason": "sensitive_screenshot_excluded_by_default"})
            continue
        if not include_sensitive and not matches_prefix(source.name, DEFAULT_EXTERNAL_SCREENSHOT_PREFIXES):
            skipped.append({"source": str(source), "reason": "not_in_default_external_screenshot_allowlist"})
            continue
        try:
            copied.append(sanitize_screenshot(source, target_dir / source.name))
        except Exception as exc:
            skipped.append({"source": str(source), "reason": f"{type(exc).__name__}: {exc}"})
    return {
        "status": "passed" if not skipped else "passed_with_skips",
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "copied_count": len(copied),
        "skipped_count": len(skipped),
        "copied": copied,
        "skipped": skipped,
        "policy": "Default external screenshot set uses an allowlist of generic/sandbox/aggregate pages. Identifier-bearing screenshots are excluded unless --include-sensitive-screenshots is used.",
    }


def build_bundle(source_manifest: Path, output_dir: Path, include_screenshots: bool = False, include_sensitive_screenshots: bool = False) -> dict[str, Any]:
    manifest = read_json(source_manifest)
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshot_output_dir = output_dir / "screenshots-sanitized"
    if screenshot_output_dir.exists():
        shutil.rmtree(screenshot_output_dir)

    copied: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []

    sanitized_manifest = redact_json(manifest)
    write_json(output_dir / "evidence_manifest.sanitized.json", sanitized_manifest)
    copied.append({"source": str(source_manifest), "target": str(output_dir / "evidence_manifest.sanitized.json")})

    for entry in manifest.get("evidence", []):
        source_text = entry.get("path", "")
        if not source_text:
            continue
        source = Path(source_text)
        if not source.is_absolute():
            source = ROOT / source
        if not source.exists() or not source.is_file():
            skipped.append({"source": source_text, "reason": "missing_or_not_file"})
            continue
        suffix = source.suffix.lower()
        if suffix not in {".json", ".md", ".txt", ".csv"}:
            skipped.append({"source": str(source), "reason": f"unsupported_suffix:{suffix}"})
            continue
        relative = relative_under_root(source)
        target = output_dir / "files" / relative
        if suffix == ".json":
            write_json(target, redact_json(read_json(source)))
        else:
            copy_redacted_text(source, target)
        copied.append({"source": str(source), "target": str(target)})

    screenshot_summary = (
        sanitize_screenshots(DEFAULT_SCREENSHOT_DIR, output_dir, include_sensitive=include_sensitive_screenshots)
        if include_screenshots
        else {
            "status": "skipped",
            "reason": "screenshots require --include-screenshots",
            "source_dir": str(DEFAULT_SCREENSHOT_DIR),
            "copied_count": 0,
            "skipped_count": 0,
            "copied": [],
            "skipped": [],
            "policy": "Screenshots are excluded by default. Use --include-screenshots for the generic external allowlist; use --include-sensitive-screenshots only for internal masked review.",
        }
    )

    readme = output_dir / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# QLanalyser V01 Sanitized Evidence Bundle",
                "",
                f"Generated: {datetime.now(timezone.utc).isoformat()}",
                "",
                "This bundle redacts bearer tokens, account ids, task/report/invoice ids, email addresses, and common secret-like fields from JSON/MD/TXT/CSV evidence.",
                "",
                "Screenshots are excluded by default. If generated with `--include-screenshots`, only generic/sandbox/aggregate screenshots are copied into `screenshots-sanitized/`; identifier-bearing screenshots remain excluded unless explicitly requested for internal masked review.",
                "",
                "This bundle is for external-readable review support only. The authoritative release evidence remains the internal owner/team evidence manifest.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    summary = {
        "status": "passed",
        "source_manifest": str(source_manifest),
        "output_dir": str(output_dir),
        "copied_count": len(copied),
        "skipped_count": len(skipped),
        "copied": copied,
        "skipped": skipped,
        "screenshots_copied": screenshot_summary.get("copied_count", 0) > 0,
        "screenshot_policy": screenshot_summary.get("policy"),
        "screenshot_summary": screenshot_summary,
    }
    write_json(output_dir / "sanitized_bundle_manifest.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a sanitized JSON/text evidence bundle for external-readable QLanalyser review.")
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--include-screenshots", action="store_true", help="Include only the default external-safe screenshot allowlist.")
    parser.add_argument("--include-sensitive-screenshots", action="store_true", help="Also include masked copies of identifier-bearing screenshots; for internal masked review only.")
    args = parser.parse_args()

    summary = build_bundle(args.source_manifest, args.output_dir, args.include_screenshots, args.include_sensitive_screenshots)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
