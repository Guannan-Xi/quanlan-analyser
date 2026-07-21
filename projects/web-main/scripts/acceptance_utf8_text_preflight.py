from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELFTEST_DIR = ROOT / "work" / "acceptance" / "utf8_text_preflight_selftest"
OUTPUT = (
    ROOT
    / "work"
    / "release_evidence"
    / "20260620-v01-acceptance"
    / "acceptance_utf8_text_preflight.json"
)


def run_check(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/check_no_mojibake.py", str(path.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def main() -> int:
    if SELFTEST_DIR.exists():
        shutil.rmtree(SELFTEST_DIR)
    SELFTEST_DIR.mkdir(parents=True, exist_ok=True)

    bad_encoding = SELFTEST_DIR / "bad_cp936.md"
    bad_question_marks = SELFTEST_DIR / "bad_questions.md"
    good_utf8 = SELFTEST_DIR / "good_utf8.md"

    bad_encoding.write_bytes(b"\xff\xfe\x00\x00not-valid-utf8")
    bad_question_marks.write_text("customer visible copy ????\n", encoding="utf-8")
    good_utf8.write_text("Research EEG and CRO traceability preflight.\n", encoding="utf-8")

    bad_encoding_run = run_check(bad_encoding)
    bad_question_run = run_check(bad_question_marks)
    good_run = run_check(good_utf8)

    checks = {
        "rejects_non_utf8_text": bad_encoding_run.returncode != 0
        and "not valid UTF-8" in (bad_encoding_run.stdout + bad_encoding_run.stderr),
        "rejects_literal_question_marks": bad_question_run.returncode != 0
        and "three or more question marks" in (bad_question_run.stdout + bad_question_run.stderr),
        "accepts_good_utf8": good_run.returncode == 0,
    }
    payload = {
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "selftest_dir": str(SELFTEST_DIR),
        "bad_encoding_returncode": bad_encoding_run.returncode,
        "bad_question_returncode": bad_question_run.returncode,
        "good_returncode": good_run.returncode,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    shutil.rmtree(SELFTEST_DIR, ignore_errors=True)
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
