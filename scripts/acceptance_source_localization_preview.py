from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_LAB = ROOT / "frontend" / "module-lab.js"
PREVIEW_PAGE = ROOT / "frontend" / "research-module" / "source_localization.html"
OUT_DIR = ROOT / "work" / "release_evidence" / "20260622-source-localization-preview"
OUT_FILE = OUT_DIR / "source_localization_preview_acceptance.json"


def must(condition: bool, message: str, detail=None) -> None:
    if not condition:
        raise AssertionError(f"{message}: {detail}")


def read_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    must("\ufffd" not in text, "mojibake detected", path)
    must("????" not in text, "placeholder garble detected", path)
    return text


def main() -> None:
    report = {
        "status": "running",
        "checks": [],
        "files": [],
    }

    module_lab = read_text(MODULE_LAB)
    preview_page = read_text(PREVIEW_PAGE)

    checks = [
        (
            "module-lab preview card exists",
            "source_localization" in module_lab and "Source localization preview" in module_lab,
        ),
        (
            "module-lab links preview page",
            "./research-module/source_localization.html" in module_lab,
        ),
        (
            "preview page title exists",
            "Source localization / Inverse" in preview_page,
        ),
        (
            "preview page carries forward-model boundary",
            "forward model" in preview_page and "head model" in preview_page and "source space" in preview_page,
        ),
        (
            "preview page rejects scalp-space misuse",
            "scalp topomap" in preview_page and "不适合" in preview_page,
        ),
        (
            "preview page keeps clinical boundary",
            "临床" in preview_page and "不提供临床建议" in preview_page,
        ),
    ]

    for name, ok in checks:
        report["checks"].append({"name": name, "ok": bool(ok)})
        must(ok, name)

    report["files"].append({"path": str(MODULE_LAB.relative_to(ROOT))})
    report["files"].append({"path": str(PREVIEW_PAGE.relative_to(ROOT))})
    report["status"] = "passed"

    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_file = OUT_FILE
    except PermissionError:
        fallback_dir = Path(tempfile.gettempdir()) / "qlanalyser-source-localization-preview"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        out_file = fallback_dir / "source_localization_preview_acceptance.json"
    out_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(out_file)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
