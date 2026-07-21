from __future__ import annotations

import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EDF_UI_EVIDENCE = ROOT / "work" / "release_evidence" / "edf_upload_to_results_ui_only" / "edf_upload_to_results_ui_only.json"
OUT_PATH = ROOT / "work" / "release_evidence" / "virtual_reviewer_p0" / "qc_real_report_consumption.json"


def status(ok: bool, evidence: Any = None) -> dict[str, Any]:
    item: dict[str, Any] = {"status": "pass" if ok else "block"}
    if evidence is not None:
        item["evidence"] = evidence
    return item


def load_json_from_zip(zf: zipfile.ZipFile, name: str) -> dict[str, Any]:
    return json.loads(zf.read(name).decode("utf-8"))


def load_text_from_zip(zf: zipfile.ZipFile, name: str) -> str:
    return zf.read(name).decode("utf-8", errors="replace")


def has_forbidden_claim(text: str) -> bool:
    patterns = [
        r"\bdiagnos(?:is|tic)\b(?![^.]{0,80}\bnot\b)",
        r"\btreatment recommendation\b",
        r"\bclinical (?:marker|proof|evidence|finding)\b",
        r"\bsignificant (?:difference|effect|finding|result)\b",
        r"\bsource local(?:i|iza)tion\b",
        r"\bbrain region activation\b",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            context = text[max(0, match.start() - 120) : match.end() + 120].lower()
            if any(
                marker in context
                for marker in (
                    "not for clinical",
                    "not for",
                    "not a clinical",
                    "not clinical",
                    "non-diagnostic",
                    "no p-value",
                    "no p value",
                    "no statistical",
                    "no significance",
                    "no diagnosis",
                    "forbidden",
                    "boundary",
                    "or source localization",
                )
            ):
                continue
            return True
    return False


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []
    evidence = json.loads(EDF_UI_EVIDENCE.read_text(encoding="utf-8"))
    downloads = evidence.get("downloads") or []
    report_download = next((item for item in downloads if item.get("requirement") == "report package zip"), None)
    report_zip = Path(str(report_download.get("path", ""))) if report_download else None
    if evidence.get("status") != "passed":
        failures.append("EDF UI-only evidence is not passed")
    if report_zip is None or not report_zip.exists():
        failures.append("report package zip is missing")

    checks: dict[str, Any] = {}
    qc_prefix = "qc/qc_waveform_preview"
    metadata_prefix = "qc/metadata_qc"
    if not failures and report_zip is not None:
        with zipfile.ZipFile(report_zip) as zf:
            names = {name.replace("\\", "/") for name in zf.namelist()}
            required = {
                "report_json": "reports/report.json",
                "result": f"{qc_prefix}/result.json",
                "parameters": f"{qc_prefix}/parameters.json",
                "workflow": f"{qc_prefix}/workflow.json",
                "method_description": f"{qc_prefix}/method_description.txt",
                "software_versions": f"{qc_prefix}/software_versions.json",
                "manifest": f"{qc_prefix}/manifest.json",
                "waveform_preview": f"{qc_prefix}/waveform_preview.json",
                "filter_preview": f"{qc_prefix}/filter_preview.json",
                "snapshot_json": f"{qc_prefix}/snapshot_001.json",
                "raw_svg": f"{qc_prefix}/waveform_raw_preview.svg",
                "filter_svg": f"{qc_prefix}/waveform_filter_preview.svg",
                "snapshot_svg": f"{qc_prefix}/snapshot_001.svg",
            }
            for label, name in required.items():
                checks[f"{label}_present"] = status(name in names, name)

            metadata_required = {
                "metadata_qc_summary": f"{metadata_prefix}/qc_summary.json",
                "metadata_parameters": f"{metadata_prefix}/parameters.json",
                "metadata_workflow": f"{metadata_prefix}/workflow.json",
                "metadata_method_description": f"{metadata_prefix}/method_description.txt",
                "metadata_software_versions": f"{metadata_prefix}/software_versions.json",
                "metadata_result": f"{metadata_prefix}/result.json",
                "metadata_manifest": f"{metadata_prefix}/manifest.json",
            }
            for label, name in metadata_required.items():
                checks[f"{label}_present"] = status(name in names, name)

            audit_entries = [name for name in names if name.startswith("quality/bad_channel_audit/")]
            checks.update(
                {
                    "bad_channel_audit_json_present": status(
                        any(name.endswith("_bad_channel_audit.json") for name in audit_entries),
                        audit_entries,
                    ),
                    "bad_channel_ui_evidence_present": status(
                        any(name.endswith("_bad_channel_ui_evidence.json") for name in audit_entries),
                        audit_entries,
                    ),
                    "bad_channel_channels_tsv_present": status(
                        any(name.endswith("_channels.tsv") for name in audit_entries),
                        audit_entries,
                    ),
                    "bad_channel_source_integrity_present": status(
                        any(name.endswith("_source_integrity.json") for name in audit_entries),
                        audit_entries,
                    ),
                }
            )

            if all(name in names for name in required.values()):
                report_json = load_json_from_zip(zf, required["report_json"])
                result = load_json_from_zip(zf, required["result"])
                parameters = load_json_from_zip(zf, required["parameters"])
                workflow = load_json_from_zip(zf, required["workflow"])
                software_versions = load_json_from_zip(zf, required["software_versions"])
                waveform = load_json_from_zip(zf, required["waveform_preview"])
                filter_preview = load_json_from_zip(zf, required["filter_preview"])
                snapshot = load_json_from_zip(zf, required["snapshot_json"])
                method_description = load_text_from_zip(zf, required["method_description"])

                workflow_steps = [str(item.get("name", "")).lower() for item in workflow.get("steps") or []]
                result_summary = result.get("summary") or {}
                defaults = parameters.get("defaults") or {}
                report_qc_artifacts = report_json.get("qc_artifacts") or []
                combined_text = " ".join(
                    [
                        json.dumps(report_json, ensure_ascii=False),
                        json.dumps(result, ensure_ascii=False),
                        json.dumps(parameters, ensure_ascii=False),
                        json.dumps(workflow, ensure_ascii=False),
                        method_description,
                    ]
                )

                checks.update(
                    {
                        "workflow_records_qc_preview_steps": status(
                            "read_raw" in workflow_steps
                            and "select_preview_window" in workflow_steps
                            and "optional_filter_preview" in workflow_steps
                            and "write_preview_artifacts" in workflow_steps,
                            workflow_steps,
                        ),
                        "preview_window_and_channels_present": status(
                            waveform.get("start_sec") is not None
                            and waveform.get("duration_sec") is not None
                            and bool(waveform.get("channels"))
                            and waveform.get("unit") == "uV",
                            {
                                "start_sec": waveform.get("start_sec"),
                                "duration_sec": waveform.get("duration_sec"),
                                "channels": waveform.get("channels"),
                                "unit": waveform.get("unit"),
                            },
                        ),
                        "filter_preview_declared_preview_only": status(
                            filter_preview.get("filter_preview_only") is True
                            and filter_preview.get("parameters", {}).get("apply_to") == "preview_window_only"
                            and parameters.get("preview_only_filtering") is True,
                            {
                                "filter_preview_only": filter_preview.get("filter_preview_only"),
                                "apply_to": filter_preview.get("parameters", {}).get("apply_to"),
                                "parameters_preview_only": parameters.get("preview_only_filtering"),
                            },
                        ),
                        "filter_parameters_present": status(
                            bool((defaults.get("filter_preview") or {}).get("bandpass"))
                            and bool((defaults.get("filter_preview") or {}).get("notch")),
                            defaults.get("filter_preview"),
                        ),
                        "warnings_preserved": status(
                            any("preview only" in str(item).lower() for item in result_summary.get("warnings", []))
                            or "preview-only" in combined_text.lower(),
                            result_summary.get("warnings"),
                        ),
                        "software_versions_present": status(
                            bool(software_versions.get("python")) and bool(software_versions.get("packages", {}).get("mne")),
                            software_versions,
                        ),
                        "report_json_qc_artifacts_present": status(
                            len(report_qc_artifacts) >= 6
                            and any(str(item.get("path", "")).endswith("waveform_preview.json") for item in report_qc_artifacts),
                            report_qc_artifacts,
                        ),
                        "non_diagnostic_boundary_present": status(
                            "non-diagnostic" in combined_text.lower()
                            or "not for clinical diagnosis" in combined_text.lower()
                            or "not a clinical interpretation" in combined_text.lower(),
                            "boundary scan over report/qc artifacts",
                        ),
                        "no_forbidden_claims": status(
                            not has_forbidden_claim(combined_text),
                            "forbidden claim scan over report/qc artifacts",
                        ),
                        "snapshot_metadata_present": status(
                            snapshot.get("snapshot_id") == "snapshot_001"
                            and bool(snapshot.get("time_window"))
                            and bool(snapshot.get("channels")),
                            snapshot,
                        ),
                    }
                )

            if all(name in names for name in metadata_required.values()):
                metadata_summary = load_json_from_zip(zf, metadata_required["metadata_qc_summary"])
                metadata_workflow = load_json_from_zip(zf, metadata_required["metadata_workflow"])
                metadata_result = load_json_from_zip(zf, metadata_required["metadata_result"])
                metadata_text = " ".join(
                    [
                        json.dumps(metadata_summary, ensure_ascii=False),
                        json.dumps(metadata_workflow, ensure_ascii=False),
                        json.dumps(metadata_result, ensure_ascii=False),
                    ]
                ).lower()
                checks.update(
                    {
                        "metadata_qc_summary_has_status": status(
                            bool(metadata_summary.get("status") or metadata_result.get("status")),
                            {"summary_status": metadata_summary.get("status"), "result_status": metadata_result.get("status")},
                        ),
                        "metadata_qc_workflow_has_steps": status(
                            bool(metadata_workflow.get("steps") or metadata_result.get("processing_steps")),
                            metadata_workflow.get("steps") or metadata_result.get("processing_steps"),
                        ),
                        "metadata_qc_boundary_present": status(
                            "non-diagnostic" in metadata_text
                            or "not for clinical diagnosis" in metadata_text
                            or "research" in metadata_text,
                            "metadata QC boundary scan",
                        ),
                    }
                )

    blockers = [key for key, item in checks.items() if isinstance(item, dict) and item.get("status") == "block"]
    failures.extend(blockers)
    result = {
        "schema_version": "qlanalyser-qc-real-report-consumption-v0.1",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not failures else "failed",
        "requirement_id": "VR-EO-0014-qc-methods-report-consumption",
        "scope": "real UI-only report ZIP consumption for metadata QC, QC waveform/filter preview artifacts, bad-channel audit records, methods, parameters, warnings, software versions, and non-diagnostic boundary",
        "important_boundary": "This is script-layer QC/methods report artifact consumption evidence only; it does not certify clinical data quality, release readiness, scientific interpretation, or diagnostic use.",
        "ui_evidence_path": str(EDF_UI_EVIDENCE),
        "report_zip_path": str(report_zip) if report_zip else None,
        "qc_prefix": qc_prefix,
        "metadata_prefix": metadata_prefix,
        "checks": checks,
        "blockers": failures,
        "warnings": warnings,
        "what_07_can_consume_next": [
            "Use this as the real-report counterpart for QC/methods artifact consumption across metadata QC, QC preview, and bad-channel audit records.",
            "Keep UI/report review and expert findings separate from this script-layer artifact consumption check.",
            "Do not use this checker as a clinical data-quality, release-pass, or scientific-interpretation decision.",
        ],
        "07A_SHORT_PACKET_METRICS": {
            "mini/script packet count": 1,
            "script packet used": "QC real report consumption checker",
            "GPT-5.5 low-value work avoided": "ZIP entry inventory and field presence checks are scripted",
            "concurrency frontier": "single deterministic checker over latest UI-only report ZIP",
            "long-term platform asset produced": "real QC preview report artifact validator adapter for report consumption",
            "owner boundary respected": "yes",
            "handoff target": "07 main owner",
        },
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
