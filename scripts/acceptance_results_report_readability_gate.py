from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
E2E_EVIDENCE = ROOT / "work" / "release_evidence" / "edf_upload_to_results_ui_only" / "edf_upload_to_results_ui_only.json"
OUT_DIR = ROOT / "work" / "release_evidence" / "ui_interaction_review" / "results_report_readability_gate"
OUT_JSON = OUT_DIR / "results_report_readability_gate.json"


FORBIDDEN_PATTERNS = {
    "internal_report_id_visible": re.compile(r"\breport_[0-9a-f]{8,}\b", re.IGNORECASE),
    "internal_task_id_visible": re.compile(r"\btask_[0-9a-f]{8,}\b", re.IGNORECASE),
    "concatenated_artifact_labels": re.compile(r"(planData|contractband|powerspectrum|summarymethod|versionsworkflow|callsource|metadatatable|contractresult|logmanifest)", re.IGNORECASE),
    "raw_engineering_artifact_names": re.compile(r"\b(band_power|channel_band_power|spectrum_long|psd_mean_spectrum|erp_metrics|drop_log_summary|tfr_power_long|pac_dynamic_curve|scope_contract|effective_call|parameter_schema_snapshot|threshold_validation|manifest)\b", re.IGNORECASE),
    "legacy_placeholder": re.compile(r"(Online data management|Persistence Gate|Acceptance project|acceptance-label|task_id)", re.IGNORECASE),
    "mojibake": re.compile(r"[\ufffd]|閫|鐧|鍙|锟|宸茬|寰呯|鏁版|椤圭"),
}

REQUIRED_RESULT_TERMS = ["PSD / Bandpower", "ERP / P300", "TFR / ERSP / ITC", "PAC / CFC", "生成报告 ZIP"]
REQUIRED_DELIVERY_TERMS = ["报告已生成", "下载报告 ZIP", "查看 HTML"]


def visible_texts(payload: dict[str, Any]) -> dict[str, str]:
    result_state = payload.get("resultState") or {}
    delivery_state = payload.get("deliveryState") or {}
    return {
        "result_page": "\n".join([
            str(result_state.get("title") or ""),
            str(result_state.get("resultText") or ""),
            str(result_state.get("deliveryText") or ""),
        ]),
        "report_delivery_page": "\n".join([
            str(delivery_state.get("title") or ""),
            str(delivery_state.get("resultText") or ""),
            str(delivery_state.get("deliveryText") or ""),
            str((payload.get("reportDownloadDom") or {}).get("text") or ""),
        ]),
    }


def find_issues(surface: str, text: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for name, pattern in FORBIDDEN_PATTERNS.items():
        matches = sorted(set(match.group(0) for match in pattern.finditer(text)))
        if matches:
            issues.append({
                "surface": surface,
                "issue": name,
                "matches": matches[:20],
            })
    if len(text.strip()) < 30:
        issues.append({"surface": surface, "issue": "surface_text_too_short", "length": len(text.strip())})
    return issues


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads(E2E_EVIDENCE.read_text(encoding="utf-8"))
    texts = visible_texts(payload)
    issues: list[dict[str, Any]] = []
    for surface, text in texts.items():
        issues.extend(find_issues(surface, text))

    result_text = texts["result_page"]
    delivery_text = texts["report_delivery_page"]
    missing_result_terms = [term for term in REQUIRED_RESULT_TERMS if term not in result_text]
    missing_delivery_terms = [term for term in REQUIRED_DELIVERY_TERMS if term not in delivery_text]
    if missing_result_terms:
        issues.append({"surface": "result_page", "issue": "missing_required_result_terms", "missing": missing_result_terms})
    if missing_delivery_terms:
        issues.append({"surface": "report_delivery_page", "issue": "missing_required_delivery_terms", "missing": missing_delivery_terms})

    screenshots = payload.get("screenshots") or []
    missing_screenshots = [path for path in screenshots if not Path(str(path)).exists()]
    if missing_screenshots:
        issues.append({"surface": "evidence", "issue": "missing_screenshots", "missing": missing_screenshots})

    report = {
        "requirement_id": "QLANALYSER_RESULTS_REPORT_READABILITY_GATE",
        "review_owner_model": "GPT-5.5/Codex",
        "why_not_mini": "User-facing results/report readability and scientific boundary verdict require GPT-5.5/Codex; script only checks deterministic evidence.",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not issues else "failed",
        "source_evidence": str(E2E_EVIDENCE),
        "surfaces_checked": list(texts.keys()),
        "required_result_terms": REQUIRED_RESULT_TERMS,
        "required_delivery_terms": REQUIRED_DELIVERY_TERMS,
        "screenshots": screenshots,
        "missing_screenshots": missing_screenshots,
        "issues": issues,
        "forbidden_patterns": list(FORBIDDEN_PATTERNS.keys()),
        "acceptance_contract": {
            "forbidden": [
                "raw report/task IDs as primary user-facing labels",
                "concatenated engineering artifact labels",
                "raw artifact filenames/types without readable grouping",
                "mojibake or stale internal labels",
            ],
            "required": [
                "results page summarizes each analysis module in readable language",
                "report delivery page shows clear generated/download state",
                "technical details may exist only behind clear labels and readable spacing",
            ],
        },
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
