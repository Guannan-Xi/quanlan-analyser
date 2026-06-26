from __future__ import annotations

import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
E2E_EVIDENCE = ROOT / "work" / "release_evidence" / "edf_upload_to_results_ui_only" / "edf_upload_to_results_ui_only.json"
PDF_QA = ROOT / "work" / "release_evidence" / "pdf_ocr_artifact_qa" / "pdf_ocr_artifact_qa.json"
OUT = ROOT / "work" / "release_evidence" / "report_artifact_label_readability" / "acceptance_report_artifact_label_readability.json"

RAW_ARTIFACT_LABEL_RE = re.compile(
    r"\b("
    r"pac_dynamic_curve|pac_comodulogram|pac_binned_amplitude|pac_channel_summary|"
    r"parameter_schema_snapshot|software_versions|method_description|scope_contract|"
    r"effective_call|table_dictionary|threshold_validation|filter_edge_policy|"
    r"band_power|channel_band_power|psd_mean_spectrum|tfr_power_long|erp_metrics"
    r")\b",
    re.IGNORECASE,
)

REQUIRED_READABLE_LABELS = ["参数记录", "方法说明", "软件版本记录", "文件清单"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_report_zip(e2e: dict[str, Any]) -> Path:
    downloads = e2e.get("downloads") or []
    for item in reversed(downloads):
        if item.get("requirement") == "report package zip" and item.get("path"):
            return Path(item["path"])
    raise RuntimeError("latest report ZIP not found in UI-only E2E evidence")


def raw_hits(value: Any) -> list[str]:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return sorted(set(match.group(0) for match in RAW_ARTIFACT_LABEL_RE.finditer(text)))


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    e2e = load_json(E2E_EVIDENCE)
    pdf_qa = load_json(PDF_QA) if PDF_QA.exists() else {}
    report_zip = latest_report_zip(e2e)
    issues: list[dict[str, Any]] = []

    with zipfile.ZipFile(report_zip) as zf:
        report_json = json.loads(zf.read("reports/report.json").decode("utf-8"))
        report_html = zf.read("reports/report.html").decode("utf-8", "replace")

    report_labels = report_json.get("artifact_labels") or []
    pdf_labels = (
        (((pdf_qa.get("page_checks") or {}).get("results") or {}).get("evidence") or {}).get("artifact_labels")
        or []
    )

    for surface, payload in {
        "report_json_artifact_labels": report_labels,
        "pdf_ocr_artifact_labels": pdf_labels,
    }.items():
        hits = raw_hits(payload)
        if hits:
            issues.append({"surface": surface, "issue": "raw_engineering_artifact_label", "matches": hits})

    html_delivery_section = report_html[report_html.find("交付文件") :] if "交付文件" in report_html else report_html
    hits = raw_hits(html_delivery_section)
    if hits:
        issues.append({"surface": "report_html_delivery_section", "issue": "raw_engineering_artifact_label", "matches": hits})

    missing_readable = [label for label in REQUIRED_READABLE_LABELS if label not in report_labels and label not in report_html]
    if missing_readable:
        issues.append({"surface": "report", "issue": "missing_readable_labels", "missing": missing_readable})

    if e2e.get("status") != "passed":
        issues.append({"surface": "ui_e2e", "issue": "latest_ui_e2e_not_passed", "status": e2e.get("status")})
    if pdf_qa.get("status") != "passed":
        issues.append({"surface": "pdf_qa", "issue": "pdf_qa_not_passed", "status": pdf_qa.get("status")})

    report = {
        "requirement_id": "QLANALYSER_REPORT_ARTIFACT_LABEL_READABILITY",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not issues else "failed",
        "ui_e2e_evidence": str(E2E_EVIDENCE),
        "pdf_qa_evidence": str(PDF_QA),
        "report_zip_path": str(report_zip),
        "report_json_artifact_labels": report_labels,
        "pdf_ocr_artifact_labels": pdf_labels,
        "required_readable_labels": REQUIRED_READABLE_LABELS,
        "issues": issues,
        "important_boundary": "This gate checks user-facing report/PDF label readability. Raw machine labels may remain in package paths or manifest/audit layers, but not as artifact labels in report.json, report HTML delivery table, or PDF OCR evidence.",
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
