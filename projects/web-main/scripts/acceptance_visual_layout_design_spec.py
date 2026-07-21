from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "quality" / "visual_layout_design_spec.md"
OUTPUT = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "acceptance_visual_layout_design_spec.json"


REQUIRED_PHRASES = [
    "DESIGN_SPEC",
    "before rendering",
    "Rendering code must consume",
    "Fail preflight on overflow",
    "collision",
    "Chinese mojibake",
    "three consecutive question marks",
    "Draw-first-inspect-later is not allowed",
    "canvas",
    "safe_margins",
    "panel_grid",
    "title",
    "axis",
    "legend",
    "typography",
    "label_limits",
    "density",
    "reserved_zones",
    "forbidden_overlap_zones",
    "motion_bounds",
    "max_chars_per_line",
    "max_lines",
    "max_ink_ratio",
    "artifact_path",
    "overflow_count",
    "collision_count",
    "mojibake_count",
]

NUMERIC_PATTERNS = {
    "canvas_width": r'"width_px":\s*\d+',
    "canvas_height": r'"height_px":\s*\d+',
    "safe_margin_top": r'"top_px":\s*\d+',
    "grid_columns": r'"columns":\s*\d+',
    "min_font": r'"body_min_font_px":\s*\d+',
    "max_labels": r'"max_labels":\s*\d+',
    "max_chars": r'"max_chars_per_line":\s*\d+',
    "max_lines": r'"max_lines":\s*\d+',
    "density": r'"max_ink_ratio":\s*0\.\d+',
    "motion_translation": r'"max_translation_px_per_frame":\s*\d+',
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    text = SPEC.read_text(encoding="utf-8") if SPEC.exists() else ""
    missing_phrases = [phrase for phrase in REQUIRED_PHRASES if phrase not in text]
    missing_numeric_patterns = [
        name for name, pattern in NUMERIC_PATTERNS.items() if not re.search(pattern, text)
    ]
    bad_encoding_markers = [marker for marker in ("\ufffd", "???") if marker in text]
    literal_question_guard = "three consecutive question marks" in text and "Chinese mojibake" in text
    result = {
        "status": "passed"
        if SPEC.exists()
        and not missing_phrases
        and not missing_numeric_patterns
        and not bad_encoding_markers
        and literal_question_guard
        else "failed",
        "generated_at": utc_now(),
        "spec": str(SPEC),
        "checks": {
            "spec_exists": SPEC.exists(),
            "required_phrases": not missing_phrases,
            "numeric_layout_budget": not missing_numeric_patterns,
            "bad_encoding_markers_absent": not bad_encoding_markers,
            "literal_question_guard": literal_question_guard,
        },
        "missing_phrases": missing_phrases,
        "missing_numeric_patterns": missing_numeric_patterns,
        "bad_encoding_markers": bad_encoding_markers,
        "policy": "Visual artifacts require numeric DESIGN_SPEC before rendering and must fail preflight on overflow, collision, mojibake, or literal question-mark markers.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
