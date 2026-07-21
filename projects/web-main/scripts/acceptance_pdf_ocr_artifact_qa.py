from __future__ import annotations

import json
import os
import re
import tempfile
import zipfile
import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EDF_UI_EVIDENCE = ROOT / "work" / "release_evidence" / "edf_upload_to_results_ui_only" / "edf_upload_to_results_ui_only.json"
OUT_DIR = ROOT / "work" / "release_evidence" / "pdf_ocr_artifact_qa"
OUT_PATH = OUT_DIR / "pdf_ocr_artifact_qa.json"
PAGE_DIR = OUT_DIR / "pages"


FORBIDDEN_PATTERNS = [
    r"\bdiagnos(?:is|tic)\b(?![^.]{0,80}\bnot\b)",
    r"\btreatment recommendation\b",
    r"\bclinical (?:marker|proof|evidence|finding)\b",
    r"\bsignificant (?:difference|effect|finding|result)\b",
    r"\bcaus(?:e|al|ality)\b(?![^.]{0,80}\bnot\b)",
    r"\bsource local(?:i|iza)tion\b",
    r"\bbrain region activation\b",
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def status(ok: bool, evidence: Any = None, *, revise: bool = False) -> dict[str, Any]:
    item: dict[str, Any] = {"status": "revise" if revise and not ok else ("pass" if ok else "block")}
    if evidence is not None:
        item["evidence"] = evidence
    return item


def load_report_zip(explicit_report_zip: str | None = None) -> Path:
    if explicit_report_zip:
        report_zip = Path(explicit_report_zip)
        if not report_zip.exists():
            raise FileNotFoundError(f"report package zip does not exist: {report_zip}")
        return report_zip

    evidence = json.loads(EDF_UI_EVIDENCE.read_text(encoding="utf-8"))
    downloads = evidence.get("downloads") or []
    report_download = next((item for item in downloads if item.get("requirement") == "report package zip"), None)
    if not report_download:
        raise FileNotFoundError("EDF UI-only evidence does not contain a report package zip download")
    report_zip = Path(str(report_download.get("path", "")))
    if not report_zip.exists():
        raise FileNotFoundError(f"report package zip does not exist: {report_zip}")
    return report_zip


def read_zip_member(zf: zipfile.ZipFile, name: str) -> bytes:
    if name not in zf.namelist():
        raise FileNotFoundError(f"missing ZIP member: {name}")
    return zf.read(name)


def render_pdf_pages(pdf_bytes: bytes) -> tuple[list[Path], int]:
    import fitz

    PAGE_DIR.mkdir(parents=True, exist_ok=True)
    for old_page in PAGE_DIR.glob("page_*.png"):
        old_page.unlink()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    rendered: list[Path] = []
    for index, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
        page_path = PAGE_DIR / f"page_{index:03d}.png"
        pix.save(str(page_path))
        rendered.append(page_path)
    return rendered, doc.page_count


def native_text_audit(pdf_bytes: bytes) -> dict[str, Any]:
    audit: dict[str, Any] = {
        "available": False,
        "engine": None,
        "page_count": 0,
        "text": "",
        "error": None,
    }
    try:
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        audit.update(
            {
                "available": True,
                "engine": "PyMuPDF",
                "page_count": doc.page_count,
                "text": text,
            }
        )
        return audit
    except Exception as exc:  # pragma: no cover - fallback depends on optional library state.
        audit["error"] = f"PyMuPDF failed: {exc}"

    try:
        import pdfplumber

        with tempfile.TemporaryFile() as handle:
            handle.write(pdf_bytes)
            handle.seek(0)
            with pdfplumber.open(handle) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                audit.update(
                    {
                        "available": True,
                        "engine": "pdfplumber",
                        "page_count": len(pdf.pages),
                        "text": text,
                        "error": None,
                    }
                )
                return audit
    except Exception as exc:  # pragma: no cover - fallback depends on optional library state.
        audit["error"] = f"{audit.get('error')}; pdfplumber failed: {exc}"
    return audit


def run_paddle_ocr(page_paths: list[Path]) -> dict[str, Any]:
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    from paddleocr import PaddleOCR

    ocr = PaddleOCR(
        lang="en",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    pages: list[dict[str, Any]] = []
    for page_index, page_path in enumerate(page_paths, start=1):
        results = ocr.predict(str(page_path))
        page_texts: list[str] = []
        scores: list[float] = []
        boxes = 0
        for result in results:
            rec_texts = list(result.get("rec_texts", []) if hasattr(result, "get") else [])
            rec_scores = list(result.get("rec_scores", []) if hasattr(result, "get") else [])
            rec_boxes = list(result.get("rec_boxes", []) if hasattr(result, "get") else [])
            page_texts.extend(str(item) for item in rec_texts)
            scores.extend(float(item) for item in rec_scores)
            boxes += len(rec_boxes)
        pages.append(
            {
                "page": page_index,
                "image_path": str(page_path),
                "text_count": len(page_texts),
                "layout_block_count": boxes,
                "mean_confidence": round(sum(scores) / len(scores), 4) if scores else None,
                "text": "\n".join(page_texts),
                "sample_text": page_texts[:20],
            }
        )
    return {
        "primary_parse": "PaddleOCR_all_pages",
        "pages": pages,
        "combined_text": "\n".join(page["text"] for page in pages),
    }


def has_forbidden_claim(text: str) -> tuple[bool, list[str]]:
    hits: list[str] = []
    for pattern in FORBIDDEN_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            context = text[max(0, match.start() - 140) : match.end() + 140].lower()
            if any(
                marker in context
                for marker in (
                    "not for clinical",
                    "not clinical",
                    "non-diagnostic",
                    "not a clinical",
                    "no p-value",
                    "no p value",
                    "no statistical",
                    "no significance",
                    "no diagnosis",
                    "or source-localization",
                    "not source localization",
                    "boundary",
                )
            ):
                continue
            hits.append(match.group(0))
    return bool(hits), hits


def text_has_any(text: str, tokens: list[str]) -> bool:
    lowered = text.lower()
    return any(token.lower() in lowered for token in tokens)


def compare_key_terms(ocr_text: str, native_text: str) -> dict[str, Any]:
    terms = [
        "QLanalyser EEG report",
        "not for clinical diagnosis",
        "sensor/channel-space",
        "Report ID",
        "Analysis ID",
        "Generated at",
        "Effective parameters",
        "Processing steps",
        "Warnings and limitations",
    ]
    return {
        "terms_checked": terms,
        "ocr_missing_terms": [term for term in terms if term.lower() not in ocr_text.lower()],
        "native_missing_terms": [term for term in terms if term.lower() not in native_text.lower()],
    }


def build_checks(ocr_payload: dict[str, Any], native_audit: dict[str, Any], report_json: dict[str, Any]) -> dict[str, Any]:
    ocr_text = ocr_payload.get("combined_text", "")
    native_text = str(native_audit.get("text") or "")
    combined_text = "\n".join([ocr_text, native_text, json.dumps(report_json, ensure_ascii=False)])
    forbidden, forbidden_hits = has_forbidden_claim(combined_text)
    page_count = len(ocr_payload.get("pages", []))
    text_counts = [page.get("text_count", 0) for page in ocr_payload.get("pages", [])]
    layout_counts = [page.get("layout_block_count", 0) for page in ocr_payload.get("pages", [])]
    warnings = report_json.get("warnings") or []
    parameters = report_json.get("parameters") or {}
    software_version = report_json.get("software_version") or {}
    processing_steps = report_json.get("processing_steps") or []
    source_refs = report_json.get("source_data_refs") or {}
    artifact_labels = report_json.get("artifact_labels") or []
    qc_artifacts = report_json.get("qc_artifacts") or []

    return {
        "primary_parse_all_pages": status(page_count > 0 and all(count > 0 for count in text_counts), text_counts),
        "auxiliary_text_layer_audit": status(native_audit.get("available") is True, native_audit.get("engine")),
        "cover_page_check": status(text_has_any(ocr_text, ["QLanalyser EEG report", "QLanalyser EEG V01 report package"]), "title detected by OCR"),
        "overview_page_check": status(text_has_any(combined_text, ["Report identity", "Report ID", "Analysis ID", "Project ID"]), "identity fields"),
        "data_quality_page_check": status(
            bool(qc_artifacts)
            and text_has_any(combined_text, ["QC evidence", "metadata", "waveform", "bad-channel", "bad channel"]),
            {"qc_artifact_count": len(qc_artifacts)},
        ),
        "methods_page_check": status(
            text_has_any(combined_text, ["Method summary", "Effective parameters", "Processing steps"])
            and bool(parameters)
            and bool(processing_steps),
            {"parameter_count": len(parameters), "processing_step_count": len(processing_steps)},
        ),
        "results_page_check": status(
            bool(artifact_labels) and text_has_any(combined_text, ["result", "manifest", "table", "artifact"]),
            {"artifact_labels": artifact_labels[:20]},
        ),
        "appendix_page_check": status(
            text_has_any(combined_text, ["Software and table metadata", "software_versions", "table_dictionary", "appendix"]),
            "software/table metadata references detected",
        ),
        "layout_blocks": status(sum(layout_counts) > 0, {"per_page": layout_counts}),
        "tables_figures": status(
            bool(artifact_labels or report_json.get("table_dictionary") or qc_artifacts),
            {
                "artifact_label_count": len(artifact_labels),
                "qc_artifact_count": len(qc_artifacts),
                "has_table_dictionary": bool(report_json.get("table_dictionary")),
            },
        ),
        "units_axes_channel_labels": status(
            text_has_any(combined_text, ["hz", "sec", "channels", "fp1", "fp2", "phase_freqs", "amp_freqs"]),
            {
                "channels": parameters.get("channels"),
                "phase_freqs": parameters.get("phase_freqs"),
                "amp_freqs": parameters.get("amp_freqs"),
                "time_window": parameters.get("time_window"),
            },
        ),
        "parameters": status(bool(parameters) and text_has_any(combined_text, ["parameters_hash", "workflow_id"]), parameters),
        "software_schema_version": status(
            bool(report_json.get("schema_version")) and bool(software_version.get("python")),
            {"schema_version": report_json.get("schema_version"), "software_version": software_version},
        ),
        "timestamp": status(bool(report_json.get("timestamp")) and text_has_any(combined_text, ["Generated at"]), report_json.get("timestamp")),
        "processing_steps": status(bool(processing_steps) and text_has_any(combined_text, ["Processing steps"]), processing_steps),
        "warnings": status(
            ("warnings" in report_json)
            and text_has_any(
                combined_text,
                [
                    "Warnings and limitations",
                    "No module warning was recorded",
                    "No p-value",
                    "limitations",
                ],
            ),
            {"warnings": warnings, "field_present": "warnings" in report_json},
        ),
        "provenance_source_data_refs": status(bool(source_refs) and text_has_any(combined_text, ["Provenance references"]), source_refs),
        "non_diagnostic_boundary": status(
            text_has_any(
                combined_text,
                [
                    "not for clinical diagnosis",
                    "non-diagnostic",
                    "not a clinical interpretation",
                    "research-use",
                ],
            ),
            "boundary scan over OCR/native/report JSON",
        ),
        "forbidden_claim_scan": status(not forbidden, forbidden_hits),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OCR-first QA for a QLanalyser report PDF inside a report ZIP.")
    parser.add_argument(
        "--report-zip",
        default="",
        help="Optional explicit report ZIP path. Defaults to the latest EDF UI-only evidence report package.",
    )
    args = parser.parse_args()

    blockers: list[str] = []
    warnings: list[str] = []
    report_zip: Path | None = None
    pdf_member = "reports/report.pdf"
    report_json_member = "reports/report.json"
    result: dict[str, Any]

    try:
        report_zip = load_report_zip(args.report_zip or None)
        with zipfile.ZipFile(report_zip) as zf:
            pdf_bytes = read_zip_member(zf, pdf_member)
            report_json = json.loads(read_zip_member(zf, report_json_member).decode("utf-8"))
        page_paths, page_count = render_pdf_pages(pdf_bytes)
        native_audit = native_text_audit(pdf_bytes)
        ocr_payload = run_paddle_ocr(page_paths)
        checks = build_checks(ocr_payload, native_audit, report_json)
        blockers = [name for name, item in checks.items() if item.get("status") == "block"]
        revise_items = [name for name, item in checks.items() if item.get("status") == "revise"]
        comparison = compare_key_terms(ocr_payload.get("combined_text", ""), str(native_audit.get("text") or ""))
        if comparison["ocr_missing_terms"]:
            warnings.append("OCR missing some native key terms; inspect native_text_audit_differences")

        verdict = "block" if blockers else ("revise" if revise_items else "pass")
        result = {
            "schema_version": "qlanalyser-pdf-ocr-artifact-qa-v0.1",
            "generated_at": utc_now(),
            "status": "passed" if verdict == "pass" else verdict,
            "requirement_id": "QLANALYSER_PDF_OCR_ARTIFACT_QA_READY",
            "primary_parse": "PaddleOCR_all_pages",
            "auxiliary_text_layer_audit": "yes" if native_audit.get("available") else "unavailable",
            "report_zip_path": str(report_zip),
            "pdf_member": pdf_member,
            "report_json_member": report_json_member,
            "page_count": page_count,
            "rendered_pages": [str(path) for path in page_paths],
            "page_checks": {
                "cover": checks["cover_page_check"],
                "overview": checks["overview_page_check"],
                "data_quality": checks["data_quality_page_check"],
                "methods": checks["methods_page_check"],
                "results": checks["results_page_check"],
                "appendix": checks["appendix_page_check"],
            },
            "ocr_text_extraction": {
                "engine": "PaddleOCR",
                "page_text_counts": [page.get("text_count") for page in ocr_payload.get("pages", [])],
                "mean_confidence_by_page": [page.get("mean_confidence") for page in ocr_payload.get("pages", [])],
                "sample_by_page": [
                    {"page": page.get("page"), "sample_text": page.get("sample_text")} for page in ocr_payload.get("pages", [])
                ],
            },
            "layout_blocks": checks["layout_blocks"],
            "tables_figures": checks["tables_figures"],
            "units_axes_channel_labels": checks["units_axes_channel_labels"],
            "parameters": checks["parameters"],
            "software_schema_version": checks["software_schema_version"],
            "timestamp": checks["timestamp"],
            "processing_steps": checks["processing_steps"],
            "warnings": checks["warnings"],
            "provenance_source_data_refs": checks["provenance_source_data_refs"],
            "non_diagnostic_boundary": checks["non_diagnostic_boundary"],
            "forbidden_claim_scan": checks["forbidden_claim_scan"],
            "native_text_audit_differences": comparison,
            "native_text_audit": {
                "available": native_audit.get("available"),
                "engine": native_audit.get("engine"),
                "page_count": native_audit.get("page_count"),
                "error": native_audit.get("error"),
            },
            "known_ocr_tradeoffs": [
                "OCR is primary for page-level QA, scanned pages, visual reports, and layout-visible text.",
                "Native text-layer audit remains auxiliary for exact selectable text, coordinates, links, schema names, versions, and timestamps.",
                "OCR may confuse punctuation or rare words; key parameters are cross-checked against report JSON/native text.",
            ],
            "checks": checks,
            "blockers": blockers,
            "revise_items": revise_items,
            "validator_warnings": warnings,
            "artifact_validator_verdict": verdict,
            "important_boundary": "This is PDF artifact QA only. It is not release pass, clinical/diagnostic validation, statistical approval, or scientific interpretation approval.",
            "what_07_can_consume_next": [
                "Use this checker as the OCR-first PDF report artifact QA gate for report ZIPs.",
                "Keep native text audit as auxiliary comparison for exact parameters, units, versions, and timestamps.",
                "Do not use this gate as a release, diagnosis, statistics, or scientific-interpretation verdict.",
            ],
            "07A_SHORT_PACKET_METRICS": {
                "mini/script packet count": 1,
                "script packet used": "OCR-first PDF artifact QA checker",
                "GPT-5.5 low-value work avoided": "PDF ZIP lookup, page render inventory, OCR text counts, field presence checks, and forbidden-claim scan are scripted",
                "concurrency frontier": "single deterministic PDF artifact checker; no parallel OCR fan-out to avoid CPU pressure",
                "long-term platform asset produced": "reusable OCR-first PDF artifact QA gate for QLanalyser report ZIPs",
                "owner boundary respected": "yes",
                "handoff target": "07 main owner",
            },
        }
    except Exception as exc:
        blockers = [f"pdf_ocr_artifact_qa_exception: {type(exc).__name__}: {exc}"]
        result = {
            "schema_version": "qlanalyser-pdf-ocr-artifact-qa-v0.1",
            "generated_at": utc_now(),
            "status": "blocked",
            "requirement_id": "QLANALYSER_PDF_OCR_ARTIFACT_QA_READY",
            "primary_parse": "PaddleOCR_all_pages",
            "auxiliary_text_layer_audit": "unavailable",
            "report_zip_path": str(report_zip) if report_zip else None,
            "blockers": blockers,
            "artifact_validator_verdict": "block",
            "important_boundary": "This is PDF artifact QA only. It is not release pass, clinical/diagnostic validation, statistical approval, or scientific interpretation approval.",
        }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
