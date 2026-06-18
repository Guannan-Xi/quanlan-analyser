from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGETS = ["frontend", "outputs/eeglab-mne-release", "backend", "eeg_core", "worker", "docs", "README.md"]
BAD_PATTERNS = [
    (re.compile(r"\?\?\?"), "three or more question marks, usually lost CJK text"),
    (re.compile(r"\ufffd"), "Unicode replacement character"),
]
TEXT_SUFFIXES = {".js", ".mjs", ".html", ".css", ".py", ".md", ".json", ".txt", ".ps1"}
SKIP_PARTS = {"node_modules", "__pycache__", ".git", "test-results"}


def iter_files(target: Path):
    if target.is_file():
        yield target
        return
    if not target.exists():
        return
    for path in target.rglob("*"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def main() -> int:
    targets = [ROOT / item for item in (sys.argv[1:] or DEFAULT_TARGETS)]
    failures = []
    for target in targets:
        for path in iter_files(target):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                try:
                    text = path.read_text(encoding="utf-8-sig")
                except UnicodeDecodeError:
                    continue
            rel = path.relative_to(ROOT)
            for line_no, line in enumerate(text.splitlines(), 1):
                for pattern, reason in BAD_PATTERNS:
                    if pattern.search(line):
                        failures.append(f"{rel}:{line_no}: {reason}: {line[:180]}")
    if failures:
        print("Mojibake/readiness text check failed:")
        print("\n".join(failures))
        return 1
    print("Mojibake/readiness text check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
