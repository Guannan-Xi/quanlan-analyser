from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from acceptance_pdf_ocr_artifact_qa import (
    build_checks,
    compare_key_terms,
    native_text_audit,
    render_pdf_pages,
    run_paddle_ocr,
)


REQUIRED_PHRASES = {
    "non_diagnostic_boundary": re.compile(r"\bnot\s+for\s+clinical\s+diagnosis\b", re.IGNORECASE),
    "method_summary": re.compile(r"\b(method summary|effective parameters)\b", re.IGNORECASE),
    "sensor_space_boundary": re.compile(r"\bsensor/channel-space\b|\bsensor-space\b", re.IGNORECASE),
}

FORBIDDEN_PATTERNS = {
    "diagnostic_claim": re.compile(r"\b(diagnosed|diagnosis\s+is|clinical diagnosis shows)\b", re.IGNORECASE),
    "treatment_claim": re.compile(r"\b(treatment recommendation|should be treated|therapy decision)\b", re.IGNORECASE),
    "causal_claim": re.compile(r"\b(caused by|proves that|demonstrates causality)\b", re.IGNORECASE),
    "source_overclaim": re.compile(r"\b(brain region activation|source localization result|localized to the cortex)\b", re.IGNORECASE),
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate VR-ITC-0009 PDF boundary scan with OCR-first artifact QA."
    )
    parser.add_argument("artifact", help="Path to a report PDF or a report ZIP containing reports/report.pdf")
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args()

    artifact_path = Path(args.artifact)
    output = validate_artifact(artifact_path)
    output_text = json.dumps(output, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(f"{output_text}\n", encoding="utf-8")
    print(output_text)
    if output["verdict"] != "pass":
        sys.exit(1)


def validate_artifact(path: Path) -> dict[str, Any]:
    started_at = datetime.now(UTC).isoformat()
    checks: dict[str, Any] = {}
    errors: list[str] = []
    warnings: list[str] = []

    try:
        pdf_bytes, report_json, source_member, report_json_member = _load_artifact(path)
        checks["pdf_header"] = pdf_bytes.startswith(b"%PDF")
        checks["pdf_size_bytes"] = len(pdf_bytes)
        checks["source_member"] = source_member
        checks["report_json_member"] = report_json_member
        if not report_json:
            warnings.append("REPORT_JSON_NOT_AVAILABLE_FOR_CROSS_CHECK")

        rendered_pages, page_count = render_pdf_pages(pdf_bytes)
        ocr_payload = run_paddle_ocr(rendered_pages)
        ocr_text = str(ocr_payload.get("combined_text") or "")
        native_audit = native_text_audit(pdf_bytes)
        native_text = str(native_audit.get("text") or "")
        combined_text = "\n".join([ocr_text, native_text, json.dumps(report_json, ensure_ascii=False)])
        artifact_checks = build_checks(ocr_payload, native_audit, report_json)
        comparison = compare_key_terms(ocr_text, native_text)

        checks.update(
            {
                "primary_parse": "PaddleOCR_all_pages",
                "auxiliary_text_layer_audit": "yes" if native_audit.get("available") else "unavailable",
                "text_extractable": bool(ocr_text.strip()),
                "ocr_text_extractable": bool(ocr_text.strip()),
                "native_text_extractable": bool(native_text.strip()),
                "page_count": page_count,
                "rendered_pages": [str(item) for item in rendered_pages],
                "extractor": "PaddleOCR_all_pages",
                "auxiliary_extractor": native_audit.get("engine"),
                "text_sha256": _sha256_text(ocr_text),
                "text_length": len(ocr_text),
                "ocr_text_extraction": {
                    "page_text_counts": [page.get("text_count") for page in ocr_payload.get("pages", [])],
                    "mean_confidence_by_page": [page.get("mean_confidence") for page in ocr_payload.get("pages", [])],
                    "sample_by_page": [
                        {"page": page.get("page"), "sample_text": page.get("sample_text")}
                        for page in ocr_payload.get("pages", [])
                    ],
                },
                "page_checks": {
                    "cover": artifact_checks["cover_page_check"],
                    "overview": artifact_checks["overview_page_check"],
                    "data_quality": artifact_checks["data_quality_page_check"],
                    "methods": artifact_checks["methods_page_check"],
                    "results": artifact_checks["results_page_check"],
                    "appendix": artifact_checks["appendix_page_check"],
                },
                "layout_blocks": artifact_checks["layout_blocks"],
                "tables_figures": artifact_checks["tables_figures"],
                "units_axes_channel_labels": artifact_checks["units_axes_channel_labels"],
                "parameters": artifact_checks["parameters"],
                "software_schema_version": artifact_checks["software_schema_version"],
                "timestamp": artifact_checks["timestamp"],
                "processing_steps": artifact_checks["processing_steps"],
                "warnings": artifact_checks["warnings"],
                "provenance_source_data_refs": artifact_checks["provenance_source_data_refs"],
                "non_diagnostic_boundary": artifact_checks["non_diagnostic_boundary"],
                "forbidden_claim_scan": artifact_checks["forbidden_claim_scan"],
                "native_text_audit_differences": comparison,
                "native_text_audit": {
                    "available": native_audit.get("available"),
                    "engine": native_audit.get("engine"),
                    "page_count": native_audit.get("page_count"),
                    "error": native_audit.get("error"),
                },
                "known_ocr_tradeoffs": [
                    "PaddleOCR is primary for page-level PDF artifact QA and visible report text.",
                    "Native text-layer parsing is auxiliary for exact selectable text, versions, timestamps, and schema strings.",
                    "OCR can misread punctuation or rare terms, so critical fields are cross-checked against report JSON/native text when available.",
                ],
            }
        )

        required = {name: bool(pattern.search(combined_text)) for name, pattern in REQUIRED_PHRASES.items()}
        forbidden = _scan_forbidden(combined_text)
        checks["required_phrases"] = required
        checks["forbidden_patterns"] = forbidden

        if not checks["pdf_header"]:
            errors.append("PDF_HEADER_MISSING")
        if not checks["text_extractable"]:
            errors.append("PDF_OCR_TEXT_NOT_EXTRACTABLE")
        for name, passed in required.items():
            if not passed:
                errors.append(f"REQUIRED_BOUNDARY_MISSING:{name}")
        if forbidden:
            errors.append("FORBIDDEN_BOUNDARY_LANGUAGE_FOUND")
        blocked_artifact_checks = [
            name for name, item in artifact_checks.items() if isinstance(item, dict) and item.get("status") == "block"
        ]
        if blocked_artifact_checks:
            errors.extend(f"OCR_ARTIFACT_CHECK_BLOCK:{name}" for name in blocked_artifact_checks)
    except Exception as exc:
        errors.append(f"VALIDATION_ERROR:{type(exc).__name__}")
        checks["exception"] = str(exc)

    return {
        "protocol": "QLANALYSER_PDF_OCR_ARTIFACT_QA_READY",
        "requirement_id": "VR-ITC-0009",
        "validator": "validate_vr_itc_0009_pdf_boundary.py",
        "artifact": str(path),
        "generated_at": started_at,
        "primary_parse": "PaddleOCR_all_pages",
        "auxiliary_text_layer_audit": checks.get("auxiliary_text_layer_audit", "unavailable"),
        "artifact_validator_verdict": "pass" if not errors else "revise",
        "verdict": "pass" if not errors else "revise",
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "boundary": (
            "OCR-first PDF artifact QA and boundary scan only. Native text-layer parsing is auxiliary. "
            "This validator does not replace expert EEG, statistics, medical, privacy, accessibility, release, "
            "or full report review."
        ),
    }


def _load_artifact(path: Path) -> tuple[bytes, dict[str, Any], str, str | None]:
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            preferred_pdf = "reports/report.pdf"
            if preferred_pdf in names:
                pdf_member = preferred_pdf
            else:
                pdf_members = [name for name in names if name.lower().endswith(".pdf")]
                if not pdf_members:
                    raise FileNotFoundError("No PDF member found in report ZIP")
                pdf_member = pdf_members[0]
            report_json_member = "reports/report.json" if "reports/report.json" in names else None
            report_json = (
                json.loads(archive.read(report_json_member).decode("utf-8")) if report_json_member else {}
            )
            return archive.read(pdf_member), report_json, pdf_member, report_json_member
    return path.read_bytes(), {}, path.name, None


def _scan_forbidden(text: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for name, pattern in FORBIDDEN_PATTERNS.items():
        for match in pattern.finditer(text):
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 80)
            findings.append(
                {
                    "pattern": name,
                    "match": match.group(0),
                    "context": " ".join(text[start:end].split()),
                }
            )
    return findings


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


if __name__ == "__main__":
    main()
