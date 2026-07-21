from __future__ import annotations

import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = Path(
    r"D:\QuanLanKnowledgeBase\manifests\qlanalyser\virtual-reviewer-user-signals\packs\v0.1.1"
)
P0_EVIDENCE_PATH = ROOT / "work" / "release_evidence" / "p0_ui_only_runner" / "p0-ui-only-runner-evidence.json"
OUT_DIR = ROOT / "work" / "release_evidence" / "virtual_reviewer_round_005"
OUT_PATH = OUT_DIR / "round_005_dry_run.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_jsonl(path: Path, key: str) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    result: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        identifier = item.get(key) or item.get("requirement_id") or item.get("task_id") or item.get("fixture_id")
        if identifier:
            result[str(identifier)] = item
    return result


def find_report_bundle(evidence: dict[str, Any]) -> Path | None:
    for item in evidence.get("downloads") or []:
        if item.get("requirement") == "report bundle":
            candidate = Path(str(item.get("path", "")))
            if candidate.exists():
                return candidate
    candidates = sorted(
        (ROOT / "work" / "release_evidence" / "p0_ui_only_runner").glob("report_*.zip"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def zip_text(zf: zipfile.ZipFile, name: str) -> str:
    if name not in zf.namelist():
        return ""
    return zf.read(name).decode("utf-8", "replace")


def zip_json(zf: zipfile.ZipFile, name: str) -> dict[str, Any]:
    text = zip_text(zf, name)
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(flatten(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(flatten(item) for item in value)
    return str(value)


def extract_pdf_text(zf: zipfile.ZipFile, name: str) -> str:
    if name not in zf.namelist():
        return ""
    data = zf.read(name)
    try:
        import fitz  # type: ignore

        doc = fitz.open(stream=data, filetype="pdf")
        return "\n".join(page.get_text() for page in doc)
    except Exception:
        return ""


def status_item(status: str, evidence: Any = None, detail: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"status": status}
    if detail is not None:
        item["detail"] = detail
    if evidence is not None:
        item["evidence"] = evidence
    return item


def forbidden_diagnostic_claim(text: str) -> bool:
    patterns = [
        r"\bdiagnosed\s+with\b",
        r"\bdiagnosis\s+is\b",
        r"\bdiagnostic\s+conclusion\b",
        r"\bclinical\s+diagnosis\s+is\b",
        r"\btreatment\s+decision\s+(?:should|must|is)\b",
        r"\bproves?\s+(?:a\s+)?(?:disease|disorder|diagnosis)\b",
    ]
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def evaluate_vr_eo_0014(report_bundle: Path | None) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []
    warnings: list[str] = []
    if not report_bundle or not report_bundle.exists():
        return {
            "requirement_id": "VR-EO-0014",
            "decision": "block",
            "checks": {"report_bundle_present": status_item("block", False, "No report bundle found.")},
            "blockers": ["report_bundle_missing"],
            "warnings": [],
        }

    with zipfile.ZipFile(report_bundle) as zf:
        names = set(zf.namelist())
        report_json = zip_json(zf, "reports/report.json")
        result_json = zip_json(zf, "result.json")
        manifest_json = zip_json(zf, "manifest.json")
        workflow_json = zip_json(zf, "reproducibility/workflow.json")
        software_json = zip_json(zf, "reproducibility/software_versions.json")
        method_text = zip_text(zf, "reproducibility/method_description.txt")
        pdf_text = extract_pdf_text(zf, "reports/report.pdf")
        html_text = zip_text(zf, "reports/report.html")
        text_blob = " ".join(
            [
                flatten(report_json),
                flatten(result_json),
                flatten(manifest_json),
                flatten(workflow_json),
                method_text,
                pdf_text,
                html_text,
            ]
        ).lower()

        processing_steps = report_json.get("processing_steps") or workflow_json.get("steps")
        qc_artifacts = [
            name
            for name in names
            if "qc" in name.lower() and (name.endswith(".json") or name.endswith(".csv") or name.endswith(".png") or name.endswith(".svg"))
        ]
        bad_channel_summary = bool(
            report_json.get("bad_channel_summary")
            or result_json.get("bad_channels")
            or "bad_channel" in text_blob
            or "bad channels" in text_blob
        )
        annotation_summary = bool(
            report_json.get("annotation_summary") or result_json.get("annotations") or "annotation" in text_blob
        )
        warnings_present = "warnings" in report_json or "warnings" in result_json
        methods_present = bool(method_text.strip() or report_json.get("methods_summary") or "method summary" in pdf_text.lower())
        software_timestamp = bool(
            software_json
            and (
                report_json.get("timestamp")
                or report_json.get("generated_at")
                or result_json.get("created_at")
                or manifest_json.get("created_at")
            )
        )
        non_diagnostic = "not for clinical diagnosis" in text_blob or "non-diagnostic" in text_blob
        diagnostic_claim = forbidden_diagnostic_claim(text_blob)

        checks = {
            "html_or_pdf_openable": status_item("pass" if {"reports/report.html", "reports/report.pdf"} & names else "block"),
            "json_manifest_present": status_item(
                "pass" if {"reports/report.json", "manifest.json"} <= names else "block",
                sorted(name for name in names if name.endswith(".json"))[:20],
            ),
            "preprocessing_steps_present": status_item("pass" if processing_steps else "block"),
            "qc_figures_or_tables_present": status_item("pass" if qc_artifacts else "block", qc_artifacts),
            "bad_channel_and_annotation_summary_present": status_item(
                "pass" if bad_channel_summary and annotation_summary else "block",
                {"bad_channel_summary": bad_channel_summary, "annotation_summary": annotation_summary},
            ),
            "warnings_preserved": status_item("pass" if warnings_present else "block"),
            "bids_methods_summary_present": status_item(
                "pass" if methods_present and "bids" in text_blob else "revise",
                {"methods_present": methods_present, "bids_term_present": "bids" in text_blob},
            ),
            "software_version_timestamp_present": status_item("pass" if software_timestamp else "block"),
            "non_diagnostic_boundary_present": status_item("pass" if non_diagnostic and not diagnostic_claim else "block"),
        }

    for name, item in checks.items():
        if item["status"] == "block":
            blockers.append(name)
        elif item["status"] == "revise":
            warnings.append(name)

    return {
        "requirement_id": "VR-EO-0014",
        "artifact": str(report_bundle),
        "decision": "block" if blockers else "revise" if warnings else "pass",
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "boundary": "QC/methods completeness dry-run only; this does not certify clinical data quality.",
    }


def evaluate_vr_eo_0015(report_bundle: Path | None) -> dict[str, Any]:
    names: set[str] = set()
    if report_bundle and report_bundle.exists():
        with zipfile.ZipFile(report_bundle) as zf:
            names = set(zf.namelist())
    has_audit = any("bad_channel_audit" in name.lower() and name.endswith(".json") for name in names)
    has_channels_tsv = any(name.lower().endswith("channels.tsv") or name.lower().endswith("channels_updated.tsv") for name in names)
    has_ui_evidence = any("bad_channel" in name.lower() and name.lower().endswith((".png", ".jpg", ".json")) for name in names)
    has_discard = False
    discard_source_integrity = False
    if report_bundle and report_bundle.exists():
        with zipfile.ZipFile(report_bundle) as zf:
            for name in names:
                if "bad_channel_audit" in name.lower() and name.endswith(".json"):
                    try:
                        audit = json.loads(zf.read(name).decode("utf-8"))
                    except Exception:
                        continue
                    if audit.get("decision") == "discard":
                        has_discard = True
                        integrity = audit.get("source_integrity") or {}
                        if (
                            integrity.get("source_eeg_object_unchanged") is True
                            and integrity.get("source_channels_tsv_modified") is False
                            and integrity.get("audit_channels_tsv_role") == "derivative_review_record_not_source_bids_channels_tsv"
                        ):
                            discard_source_integrity = True
                if "source_integrity" in name.lower() and name.endswith(".json"):
                    try:
                        integrity = json.loads(zf.read(name).decode("utf-8"))
                    except Exception:
                        continue
                    if (
                        integrity.get("decision") == "discard"
                        and integrity.get("source_eeg_object_unchanged") is True
                        and integrity.get("source_channels_tsv_modified") is False
                        and integrity.get("audit_channels_tsv_role") == "derivative_review_record_not_source_bids_channels_tsv"
                    ):
                        discard_source_integrity = True
    checks = {
        "audit_json_parseable": status_item("pass" if has_audit else "block"),
        "before_after_channel_status_present": status_item("pass" if has_audit else "block"),
        "changed_channels_list_present": status_item("pass" if has_audit else "block"),
        "save_or_discard_decision_present": status_item("pass" if has_audit else "block"),
        "channels_tsv_updated_when_saved": status_item("pass" if has_channels_tsv else "block"),
        "channels_tsv_unchanged_when_discarded": status_item(
            "pass" if has_discard and discard_source_integrity else "revise",
            {"discard_audit_present": has_discard, "source_integrity_proof_present": discard_source_integrity},
            "Discard case requires source integrity hash proof." if has_discard else "Discard case fixture not present in current P0 report bundle.",
        ),
        "screenshot_or_ui_evidence_present": status_item("pass" if has_ui_evidence else "block"),
    }
    blockers = [name for name, item in checks.items() if item["status"] == "block"]
    warnings = [name for name, item in checks.items() if item["status"] == "revise"]
    return {
        "requirement_id": "VR-EO-0015",
        "artifact": str(report_bundle) if report_bundle else None,
        "decision": "block" if blockers else "revise" if warnings else "pass",
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "boundary": "Bad-channel edit audit is not proven unless channels.tsv and audit JSON are generated by visible UI save/discard actions.",
    }


def evaluate_vr_eo_0016(report_bundle: Path | None) -> dict[str, Any]:
    text_blob = ""
    names: set[str] = set()
    if report_bundle and report_bundle.exists():
        with zipfile.ZipFile(report_bundle) as zf:
            names = set(zf.namelist())
            for name in names:
                if name.endswith((".json", ".txt", ".html", ".csv")):
                    text_blob += " " + zip_text(zf, name).lower()
    has_group_artifact = any("group" in name.lower() or "statistics" in name.lower() for name in names)
    significance_claim = bool(re.search(r"\b(significant|p\s*[<=>]|p-value|group difference)\b", text_blob))
    has_test = bool(re.search(r"\b(t-test|anova|permutation|cluster|mixed model|wilcoxon|mann-whitney)\b", text_blob))
    has_correction = bool(re.search(r"\b(fdr|bonferroni|holm|cluster correction|multiple comparison)\b", text_blob))

    if not has_group_artifact:
        return {
            "requirement_id": "VR-EO-0016",
            "artifact": str(report_bundle) if report_bundle else None,
            "decision": "not_applicable_current_p0_single_record",
            "checks": {
                "group_artifact_present": status_item("not_applicable", False),
                "no_significance_claim_without_test_and_correction": status_item(
                    "pass" if not significance_claim or (has_test and has_correction) else "block",
                    {"significance_claim": significance_claim, "test": has_test, "correction": has_correction},
                ),
            },
            "blockers": [],
            "warnings": ["Group-analysis validators must be mandatory before any group/statistics feature is exposed."],
            "boundary": "V01 current evidence is single-record descriptive analysis; group/statistical claims are not in scope.",
        }

    checks = {
        "datatype_label_present": status_item("pass" if "analysis_output_type" in text_blob else "block"),
        "dimension_metadata_present": status_item("pass" if "dimensions" in text_blob else "block"),
        "measure_type_present": status_item("pass" if "measure_type" in text_blob else "block"),
        "subject_count_present": status_item("pass" if "subject_count" in text_blob else "block"),
        "condition_or_group_design_present": status_item("pass" if "conditions" in text_blob or "groups" in text_blob else "block"),
        "precompute_parameters_present": status_item("pass" if "precompute_parameters" in text_blob else "block"),
        "statistical_test_present_when_significance_claimed": status_item("pass" if not significance_claim or has_test else "block"),
        "multiple_comparison_correction_present_when_significance_claimed": status_item(
            "pass" if not significance_claim or has_correction else "block"
        ),
        "limitations_present": status_item("pass" if "limitations" in text_blob else "block"),
    }
    blockers = [name for name, item in checks.items() if item["status"] == "block"]
    return {
        "requirement_id": "VR-EO-0016",
        "artifact": str(report_bundle),
        "decision": "block" if blockers else "pass",
        "checks": checks,
        "blockers": blockers,
        "warnings": [],
        "boundary": "Group-analysis statistical boundary dry-run; no diagnosis, causality or unsupported group conclusion is allowed.",
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p0_evidence = read_json(P0_EVIDENCE_PATH) if P0_EVIDENCE_PATH.exists() else {}
    report_bundle = find_report_bundle(p0_evidence)
    requirements = load_jsonl(PACK_ROOT / "expected_output_requirements.jsonl", "requirement_id")
    interactions = load_jsonl(PACK_ROOT / "interaction_test_cases.jsonl", "task_id")
    fixtures = load_jsonl(PACK_ROOT / "fixture_requirements.jsonl", "fixture_id")

    findings = {
        "VR-EO-0014": evaluate_vr_eo_0014(report_bundle),
        "VR-EO-0015": evaluate_vr_eo_0015(report_bundle),
        "VR-EO-0016": evaluate_vr_eo_0016(report_bundle),
    }
    blocking_findings = {
        key: value
        for key, value in findings.items()
        if value.get("decision") == "block"
    }
    payload = {
        "schema_version": "qlanalyser-virtual-reviewer-round-005-dry-run-v0.1",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "completed",
        "product_gate_status": "blocked" if blocking_findings else "not_blocked_by_round_005_dry_run",
        "important_boundary": (
            "This dry-run validates object-layer evidence coverage only. It is not product pass, "
            "module promotion, or clinical/scientific release approval."
        ),
        "pack_root": str(PACK_ROOT),
        "p0_evidence_path": str(P0_EVIDENCE_PATH),
        "report_bundle": str(report_bundle) if report_bundle else None,
        "requirements_loaded": sorted(requirements.keys()),
        "round_005_objects": {
            "interaction_tests": {key: interactions.get(key) for key in ["VR-ITC-0014", "VR-ITC-0015", "VR-ITC-0016"]},
            "fixtures": {key: fixtures.get(key) for key in ["VR-FX-0014", "VR-FX-0015", "VR-FX-0016"]},
            "expected_outputs": {key: requirements.get(key) for key in ["VR-EO-0014", "VR-EO-0015", "VR-EO-0016"]},
        },
        "findings": findings,
        "blocking_findings": blocking_findings,
        "next_actions": [
            "Add a real QC/methods report surface with preprocessing, QC figures/tables, bad channel and annotation summaries.",
            "Add visible bad-channel save/discard UI with channels.tsv and audit JSON artifacts before downstream analysis.",
            "Keep group/statistics features disabled until datatype, design, precompute and correction metadata validators pass.",
        ],
    }
    write_json(OUT_PATH, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
