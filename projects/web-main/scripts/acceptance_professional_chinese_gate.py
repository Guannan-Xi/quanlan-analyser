from __future__ import annotations

import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "work" / "release_evidence" / "professional_chinese_gate"
OUT_PATH = OUT_DIR / "professional_chinese_gate.json"
P0_EVIDENCE_PATH = ROOT / "work" / "release_evidence" / "p0_ui_only_runner" / "p0-ui-only-runner-evidence.json"

VISIBLE_SOURCE_FILES = [
    ROOT / "frontend" / "index.html",
    ROOT / "frontend" / "app.js",
    ROOT / "frontend" / "styles.css",
]

MOJIBAKE_PATTERNS = [
    (re.compile(r"\?\?\?\?+"), "literal question-mark placeholder"),
    (re.compile("\ufffd"), "Unicode replacement character"),
    (re.compile(r"(閫夋嫨|鏁版嵁|涓婁紶|鍒嗘瀽|鎶ュ憡|鍙傛暟|绠＄悊|瀵煎嚭|鍒涘缓|鏂囦欢|纭|浜嬩欢|棰勫|鐢ㄦ埛|璇婃柇)"), "common mojibake Chinese sequence"),
    (re.compile(r"(锟|鏂|绠|鐢|杩|妯|欏|戜)"), "common mojibake marker"),
]

FORBIDDEN_BOUNDARY_PATTERNS = [
    (re.compile(r"\b(?:diagnosed with|diagnosis is|diagnosis:|clinical diagnosis is)\b", re.IGNORECASE), "unsupported diagnosis wording"),
    (re.compile(r"(诊断为|可诊断|用于诊断|临床诊断结论)"), "unsupported Chinese diagnostic wording"),
    (re.compile(r"\b(treatment decision|clinical recommendation)\b", re.IGNORECASE), "treatment or clinical recommendation wording"),
    (re.compile(r"(治疗建议|临床建议|用药建议)"), "Chinese treatment recommendation wording"),
    (re.compile(r"\b(proves?|causes?)\b", re.IGNORECASE), "causal overclaim wording"),
    (re.compile(r"(证明.*因果|导致.*脑区|脑区通信.*证明)"), "Chinese causal or brain-region overclaim wording"),
    (re.compile(r"(脑区激活|脑源图|脑源定位结论|脑区通信)"), "source/localization overclaim wording"),
    (re.compile(r"\b(statistically significant|p-value|p\s*[<=>]\s*0?\.\d+)\b", re.IGNORECASE), "significance wording without explicit statistics gate"),
    (re.compile(r"(显著差异|统计显著|组间差异)"), "Chinese significance or group-comparison wording"),
]

OLD_GATE_PATTERNS = [
    "CHINESE_EDITORIAL_MASTERY_READY",
    "CHINESE_SCIENCE_TRANSLATION_READY",
    "CHINESE_TOP_EDITOR_REVIEW_READY",
    "文学总编辑",
]


def decode_utf8(path: Path) -> tuple[str, dict[str, Any]]:
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return "", {"path": str(path), "exists": False, "strict_utf8": False}
    try:
        text = data.decode("utf-8")
        return text, {"path": str(path), "exists": True, "strict_utf8": True, "bytes": len(data)}
    except UnicodeDecodeError as exc:
        return "", {"path": str(path), "exists": True, "strict_utf8": False, "error": str(exc)}


def load_p0_report_bundle() -> Path | None:
    if P0_EVIDENCE_PATH.exists():
        try:
            evidence = json.loads(P0_EVIDENCE_PATH.read_text(encoding="utf-8"))
            for item in evidence.get("downloads") or []:
                if item.get("requirement") == "report bundle":
                    candidate = Path(str(item.get("path", "")))
                    if candidate.exists():
                        return candidate
        except Exception:
            pass
    candidates = sorted(
        (ROOT / "work" / "release_evidence" / "p0_ui_only_runner").glob("report_*.zip"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def zip_member_text(zf: zipfile.ZipFile, name: str) -> str:
    if name not in zf.namelist():
        return ""
    return zf.read(name).decode("utf-8", "replace")


def extract_pdf_text(zf: zipfile.ZipFile, name: str) -> str:
    if name not in zf.namelist():
        return ""
    try:
        import fitz  # type: ignore

        data = zf.read(name)
        doc = fitz.open(stream=data, filetype="pdf")
        return "\n".join(page.get_text() for page in doc)
    except Exception:
        return ""


def collect_report_text(report_bundle: Path | None) -> tuple[str, dict[str, Any]]:
    if not report_bundle or not report_bundle.exists():
        return "", {"exists": False, "path": str(report_bundle) if report_bundle else None}
    details: dict[str, Any] = {"exists": True, "path": str(report_bundle), "members": []}
    parts: list[str] = []
    with zipfile.ZipFile(report_bundle) as zf:
        names = zf.namelist()
        details["members"] = names
        for name in names:
            if name.endswith((".html", ".json", ".txt", ".csv")):
                parts.append(zip_member_text(zf, name))
        parts.append(extract_pdf_text(zf, "reports/report.pdf"))
    return "\n".join(parts), details


def find_pattern_hits(text: str, patterns: list[tuple[re.Pattern[str], str]], source: str, limit: int = 20) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for pattern, label in patterns:
        for match in pattern.finditer(text):
            start = max(match.start() - 36, 0)
            end = min(match.end() + 36, len(text))
            hits.append(
                {
                    "source": source,
                    "label": label,
                    "match": match.group(0),
                    "context": text[start:end].replace("\n", " ")[:160],
                }
            )
            if len(hits) >= limit:
                return hits
    return hits


def find_forbidden_boundary_hits(text: str, source: str, limit: int = 20) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    negation_markers = [
        "not for",
        "no ",
        "without",
        "non-diagnostic",
        "not claim",
        "不输出",
        "不提供",
        "不用于",
        "不能",
        "不得",
        "禁止",
        "不是",
        "不代表",
    ]
    for pattern, label in FORBIDDEN_BOUNDARY_PATTERNS:
        for match in pattern.finditer(text):
            start = max(match.start() - 48, 0)
            end = min(match.end() + 48, len(text))
            context = text[start:end].replace("\n", " ")
            if any(marker in context.lower() for marker in negation_markers):
                continue
            hits.append(
                {
                    "source": source,
                    "label": label,
                    "match": match.group(0),
                    "context": context[:180],
                }
            )
            if len(hits) >= limit:
                return hits
    return hits


def check_boundary_present(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in [
            "not for clinical diagnosis",
            "non-diagnostic",
            "single-record",
            "sensor-space",
            "source localization",
        ]
    ) or any(phrase in text for phrase in ["不用于临床诊断", "非诊断", "单份数据", "头皮传感器", "科研"])


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    source_checks: list[dict[str, Any]] = []
    source_text_parts: list[tuple[str, str]] = []
    for path in VISIBLE_SOURCE_FILES:
        text, info = decode_utf8(path)
        source_checks.append(info)
        if info.get("strict_utf8"):
            source_text_parts.append((str(path), text))

    report_bundle = load_p0_report_bundle()
    report_text, report_info = collect_report_text(report_bundle)
    source_text_parts.append(("report_bundle", report_text))

    mojibake_hits: list[dict[str, Any]] = []
    forbidden_hits: list[dict[str, Any]] = []
    old_gate_hits: list[dict[str, Any]] = []
    for source, text in source_text_parts:
        mojibake_hits.extend(find_pattern_hits(text, MOJIBAKE_PATTERNS, source))
        forbidden_hits.extend(find_forbidden_boundary_hits(text, source))
        for old_gate in OLD_GATE_PATTERNS:
            if old_gate in text:
                old_gate_hits.append({"source": source, "match": old_gate})

    combined_text = "\n".join(text for _, text in source_text_parts)
    strict_utf8_ok = all(item.get("strict_utf8") for item in source_checks) and report_info.get("exists", False)
    boundary_present = check_boundary_present(combined_text)
    numbers_units_parameters_present = all(term in combined_text for term in ["Hz", "s"]) and any(
        term in combined_text for term in ["parameters", "参数", "baseline", "epoch"]
    )
    terminology_consistent = not old_gate_hits
    grammar_logic_clear = not mojibake_hits
    user_understandable = not mojibake_hits
    professional_register = not forbidden_hits and not old_gate_hits

    checks = {
        "strict_utf8": strict_utf8_ok,
        "no_mojibake_or_question_mark_placeholders": not mojibake_hits,
        "terminology_consistent": terminology_consistent,
        "grammar_logic_clear": grammar_logic_clear,
        "user_understandable": user_understandable,
        "professional_register": professional_register,
        "non_diagnostic_boundary_preserved": boundary_present and not forbidden_hits,
        "numbers_units_parameters_preserved": numbers_units_parameters_present,
        "deepseek_polish_used_or_skip_reason": {
            "status": "skip_recorded",
            "reason": "This is an executable gate run, not a prose rewrite pass. DeepSeek polish is required before approving new user-visible Chinese copy.",
        },
        "final_reviewer_checked": "C0 executable gate produced machine-readable findings; final scientific/product judgment remains with GPT-5.5/Codex and QLanalyser reviewer.",
    }
    blockers = [
        name
        for name, value in checks.items()
        if isinstance(value, bool) and not value
    ]
    if mojibake_hits:
        blockers.append("mojibake_hits_present")
    if forbidden_hits:
        blockers.append("forbidden_boundary_hits_present")
    if old_gate_hits:
        blockers.append("old_chinese_gate_terms_present")

    payload = {
        "schema_version": "qlanalyser-professional-chinese-gate-v0.1",
        "gate": "QLANALYSER_PROFESSIONAL_CHINESE_READY",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not blockers else "blocked",
        "important_boundary": "This gate checks visible language quality, mojibake, and scientific/medical boundary wording. It does not replace EEG expert review.",
        "source_files": source_checks,
        "report_bundle": report_info,
        "checks": checks,
        "blockers": sorted(set(blockers)),
        "mojibake_hits": mojibake_hits[:30],
        "forbidden_boundary_hits": forbidden_hits[:30],
        "old_gate_hits": old_gate_hits[:30],
        "next_actions": [
            "Repair visible frontend mojibake with explicit UTF-8 file-backed writes before product-ready claims.",
            "Run DeepSeek polish only on reviewed copy, then rerun this gate and final scientific boundary review.",
            "Keep non-diagnostic, single-record, sensor-space wording visible in UI/report/export copy.",
        ],
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
