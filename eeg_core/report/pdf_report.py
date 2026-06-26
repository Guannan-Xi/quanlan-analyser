from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def write_pdf_report(report_dir: Path, title: str, report_json: dict[str, Any]) -> Path:
    """Write a text-extractable customer PDF summary for the report package."""

    report_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = report_dir / "report.pdf"

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="SmallMono",
            parent=styles["BodyText"],
            fontName="Courier",
            fontSize=8,
            leading=10,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Boundary",
            parent=styles["BodyText"],
            borderColor="#94a3b8",
            borderWidth=0.5,
            borderPadding=6,
            backColor="#f8fafc",
            leading=12,
            spaceAfter=8,
        )
    )

    story: list[Any] = []
    story.append(Paragraph(_clean_text(title or "QLanalyser EEG report"), styles["Title"]))
    story.append(Paragraph("QLanalyser EEG V01 report package", styles["BodyText"]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Interpretation boundary", styles["Heading2"]))
    story.append(
        Paragraph(
            "This report is a research-use descriptive EEG analysis output. It is not for clinical "
            "diagnosis, treatment decisions, causality claims, or individual brain-region localization.",
            styles["Boundary"],
        )
    )
    story.append(
        Paragraph(
            "PSD and band-power outputs describe sensor/channel-space measurements under the recorded "
            "preprocessing and analysis parameters. Topographic figures, when present, are scalp sensor "
            "interpolation views and are not source localization or brain activation evidence.",
            styles["BodyText"],
        )
    )

    task = report_json.get("task") or {}
    story.append(Paragraph("Report identity", styles["Heading2"]))
    story.extend(
        _key_value_lines(
            {
                "Report ID": report_json.get("report_id"),
                "Analysis ID": report_json.get("analysis_id"),
                "Project ID": task.get("project_id"),
                "Input file ID": task.get("input_file_id"),
                "Module": task.get("module_name"),
                "Workflow": task.get("workflow_id"),
                "Generated at": report_json.get("timestamp") or datetime.now(UTC).isoformat(),
            },
            styles,
        )
    )

    story.append(Paragraph("Method summary", styles["Heading2"]))
    params = report_json.get("parameters") or {}
    story.append(Paragraph("Effective parameters:", styles["BodyText"]))
    story.append(Paragraph(_json_preview(params), styles["SmallMono"]))

    steps = report_json.get("processing_steps") or []
    story.append(Paragraph("Processing steps:", styles["BodyText"]))
    if steps:
        for index, step in enumerate(steps[:12], start=1):
            story.append(Paragraph(f"{index}. {_clean_text(_step_summary(step))}", styles["BodyText"]))
        if len(steps) > 12:
            story.append(Paragraph(f"... {len(steps) - 12} additional steps are available in workflow.json.", styles["BodyText"]))
    else:
        story.append(Paragraph("No processing steps were recorded in the workflow artifact.", styles["BodyText"]))

    story.append(Paragraph("Warnings and limitations", styles["Heading2"]))
    warnings = report_json.get("warnings") or []
    if warnings:
        for warning in warnings[:12]:
            story.append(Paragraph(f"- {_clean_text(warning)}", styles["BodyText"]))
    else:
        story.append(Paragraph("No module warning was recorded. This does not remove the interpretation boundary above.", styles["BodyText"]))

    story.append(Paragraph("Provenance references", styles["Heading2"]))
    refs = report_json.get("source_data_refs") or {}
    story.extend(_key_value_lines(refs, styles))
    story.append(Paragraph("Software and table metadata are included in the ZIP package JSON artifacts.", styles["BodyText"]))

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=_clean_text(title or "QLanalyser EEG report"),
        author="QLanalyser",
    )
    doc.build(story)
    return pdf_path


def _key_value_lines(values: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    lines: list[Any] = []
    for key, value in values.items():
        lines.append(Paragraph(f"<b>{_clean_text(key)}:</b> {_clean_text(value)}", styles["BodyText"]))
    return lines


def _step_summary(step: Any) -> str:
    if isinstance(step, dict):
        label = step.get("name") or step.get("step") or step.get("action") or step.get("id") or "step"
        details = {k: v for k, v in step.items() if k not in {"name", "step", "action", "id"}}
        if details:
            return f"{label}: {json.dumps(details, ensure_ascii=True, default=str)[:240]}"
        return str(label)
    return str(step)


def _json_preview(value: Any, *, max_chars: int = 1600) -> str:
    text = json.dumps(value, ensure_ascii=True, indent=2, default=str)
    if len(text) > max_chars:
        text = f"{text[:max_chars]}\n... see report.json for the complete parameter payload."
    return _clean_text(text).replace("\n", "<br/>")


def _clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\x00", "")
    )
