from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "work" / "release_evidence" / "p0_ui_only_runner"
EVIDENCE_PATH = EVIDENCE_DIR / "p0-ui-only-runner-evidence.json"
ACCEPTANCE_PATH = EVIDENCE_DIR / "acceptance_p0_ui_only_runner_contract.json"
MODULES = ["preprocessing_readiness", "event_epoch", "psd_bandpower", "erp_p300"]
REQUIRED_COVERAGE = {"click", "upload", "wait", "screenshot", "download", "artifact_inspect"}


def check(condition: bool, code: str, detail: str, failures: list[dict], warnings: list[dict] | None = None) -> None:
    if not condition:
        (warnings if warnings is not None and code.startswith("WARN_") else failures).append(
            {"code": code, "detail": detail}
        )


def load_evidence() -> dict:
    if not EVIDENCE_PATH.exists():
        raise FileNotFoundError(f"Evidence file missing: {EVIDENCE_PATH}")
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def validate_zip(download: dict, failures: list[dict]) -> None:
    package_path = Path(download.get("path", ""))
    check(package_path.exists(), "DOWNLOAD_FILE_MISSING", f"Downloaded package not found: {package_path}", failures)
    if not package_path.exists():
        return
    check(download.get("via") == "visible UI data-report-download button", "DOWNLOAD_NOT_UI_EXPOSED", "Download was not recorded as coming from the visible report download UI.", failures)
    check(download.get("is_zip") is True, "DOWNLOAD_NOT_ZIP", "Downloaded artifact did not have a ZIP header.", failures)
    try:
        with zipfile.ZipFile(package_path) as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile:
        failures.append({"code": "BAD_ZIP", "detail": f"Cannot open ZIP: {package_path}"})
        return
    for entry in ["reports/report.pdf", "reports/report.json", "tables/metrics.csv"]:
        check(entry in names, "ZIP_REQUIRED_ENTRY_MISSING", f"Missing required ZIP entry: {entry}", failures)


def run_boundary_validators(evidence_path: Path, downloads: list[dict], failures: list[dict], warnings: list[dict]) -> dict:
    validator_results: dict[str, dict] = {}
    node_validator = ROOT / "scripts" / "validate_vr_eo_0001.mjs"
    if node_validator.exists():
        proc = subprocess.run(
            ["node", str(node_validator), str(evidence_path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        validator_results["vr_eo_0001"] = {
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:],
        }
        if proc.returncode != 0:
            failures.append({"code": "VR_EO_0001_VALIDATOR_FAILED", "detail": proc.stderr or proc.stdout})
    else:
        warnings.append({"code": "WARN_VR_EO_0001_VALIDATOR_MISSING", "detail": str(node_validator)})

    pdf_validator = ROOT / "scripts" / "validate_vr_itc_0009_pdf_boundary.py"
    if pdf_validator.exists() and downloads:
        package_path = downloads[0].get("path")
        pdf_output = EVIDENCE_DIR / "vr-itc-0009-pdf-ocr-boundary-validator.json"
        proc = subprocess.run(
            [sys.executable, str(pdf_validator), str(package_path), "--output", str(pdf_output)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        parsed_output = {}
        if pdf_output.exists():
            try:
                parsed_output = json.loads(pdf_output.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                failures.append({"code": "PDF_BOUNDARY_VALIDATOR_OUTPUT_BAD_JSON", "detail": str(exc)})
        validator_results["vr_itc_0009_pdf_boundary"] = {
            "returncode": proc.returncode,
            "output_path": str(pdf_output),
            "primary_parse": parsed_output.get("primary_parse"),
            "auxiliary_text_layer_audit": parsed_output.get("auxiliary_text_layer_audit"),
            "artifact_validator_verdict": parsed_output.get("artifact_validator_verdict"),
            "verdict": parsed_output.get("verdict"),
            "page_count": (parsed_output.get("checks") or {}).get("page_count"),
            "errors": parsed_output.get("errors", []),
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:],
        }
        if proc.returncode == 0:
            check(
                pdf_output.exists(),
                "PDF_BOUNDARY_VALIDATOR_OUTPUT_MISSING",
                f"PDF boundary validator did not write output JSON: {pdf_output}",
                failures,
            )
            check(
                parsed_output.get("primary_parse") == "PaddleOCR_all_pages",
                "PDF_BOUNDARY_VALIDATOR_NOT_OCR_FIRST",
                "VR-ITC-0009 validator did not report primary_parse=PaddleOCR_all_pages.",
                failures,
            )
            check(
                parsed_output.get("auxiliary_text_layer_audit") in {"yes", "unavailable"},
                "PDF_BOUNDARY_AUXILIARY_TEXT_AUDIT_MISSING",
                "VR-ITC-0009 validator did not report auxiliary text-layer audit status.",
                failures,
            )
        if proc.returncode != 0:
            failures.append({"code": "PDF_BOUNDARY_VALIDATOR_FAILED", "detail": proc.stderr or proc.stdout})
    else:
        warnings.append({"code": "WARN_PDF_BOUNDARY_VALIDATOR_MISSING_OR_NO_DOWNLOAD", "detail": str(pdf_validator)})
    return validator_results


def read_vr_eo_product_gate() -> dict:
    validator_path = EVIDENCE_DIR / "vr-eo-0001-artifact-validator.json"
    if not validator_path.exists():
        return {
            "status": "missing",
            "validator_path": str(validator_path),
            "blockers": [{"code": "VR_EO_0001_RESULT_MISSING", "detail": str(validator_path)}],
        }
    payload = json.loads(validator_path.read_text(encoding="utf-8"))
    decision = payload.get("decision")
    blockers = []
    if decision == "block":
        blockers.append(
            {
                "code": "VR_EO_0001_DECISION_BLOCK",
                "detail": "VR-EO-0001 artifact validator decision=block. Runner contract pass must not be read as P0 product/module pass.",
            }
        )
    for name, check_payload in (payload.get("checks") or {}).items():
        status = check_payload.get("status") if isinstance(check_payload, dict) else None
        if status not in {"pass", "passed"}:
            blockers.append({"code": "VR_EO_CHECK_NOT_PASS", "detail": f"{name}: {status}"})
    return {
        "status": "blocked" if blockers else "passed",
        "validator_path": str(validator_path),
        "decision": decision,
        "blockers": blockers,
    }


def main() -> int:
    failures: list[dict] = []
    warnings: list[dict] = []
    evidence = load_evidence()

    check(evidence.get("protocol") == "QLANALYSER_P0_UI_ONLY_RUNNER", "PROTOCOL_MISMATCH", "Evidence protocol is not QLANALYSER_P0_UI_ONLY_RUNNER.", failures)
    check(evidence.get("implementation_packet_marker") == "P0_UI_ONLY_RUNNER_PACKET_READY", "PACKET_MARKER_MISSING", "Implementation packet marker missing.", failures)
    check(evidence.get("verdict") in {"pass", "revise"}, "RUNNER_ERROR", f"Runner verdict is {evidence.get('verdict')!r}.", failures)
    check(evidence.get("no_direct_api_mutation") is True, "UI_ONLY_POLICY_MISSING", "no_direct_api_mutation must be true.", failures)
    check(not evidence.get("direct_api_mutations"), "DIRECT_API_MUTATION_RECORDED", "Runner recorded direct API mutations.", failures)

    coverage = set(evidence.get("runner_plan_coverage") or [])
    missing_coverage = sorted(REQUIRED_COVERAGE - coverage)
    check(not missing_coverage, "RUNNER_PLAN_COVERAGE_MISSING", f"Missing coverage: {missing_coverage}", failures)

    screenshots = evidence.get("screenshots") or []
    check(len(screenshots) >= 6, "SCREENSHOT_EVIDENCE_INSUFFICIENT", f"Expected at least 6 screenshots, found {len(screenshots)}.", failures)
    for item in screenshots:
        path = Path(item.get("path", ""))
        check(path.exists(), "SCREENSHOT_FILE_MISSING", f"Screenshot missing: {path}", failures)

    p0_modules = evidence.get("p0_modules") or {}
    for module_id in MODULES:
        module = p0_modules.get(module_id) or {}
        check(bool(module), "MODULE_EVIDENCE_MISSING", f"Missing module evidence for {module_id}.", failures)
        check(
            module.get("status")
            in {"ui_task_created", "implicit_fixture_events_only", "confirmed_plan_created", "standalone_epoch_manifest_exported", "persistent_epoch_set_created"},
            "MODULE_STATUS_INVALID",
            f"{module_id} status is {module.get('status')!r}.",
            failures,
        )

    plan = evidence.get("data_preparation_plan") or {}
    check(plan.get("status") == "confirmed", "DATA_PREPARATION_PLAN_NOT_CONFIRMED", "No confirmed data-preparation plan was recorded from the UI click path.", failures)
    check(bool(plan.get("id")) and isinstance(plan.get("revision"), int), "DATA_PREPARATION_PLAN_LINEAGE_MISSING", "Confirmed plan id/revision missing.", failures)
    check(bool(plan.get("preprocessing_json")), "PREPROCESSING_PARAMETERS_MISSING", "Confirmed plan lacks preprocessing_json.", failures)

    gaps = evidence.get("product_gaps") or []
    gap_modules = {gap.get("module_id") for gap in gaps}
    check(plan.get("status") == "confirmed" or "preprocessing_readiness" in gap_modules, "PREPROCESSING_GAP_NOT_EXPLICIT", "Missing confirmed plan or explicit preprocessing gap.", failures)
    persisted_epoch_set = evidence.get("persisted_epoch_set") or {}
    check(
        bool(persisted_epoch_set.get("id")) or "event_epoch" in gap_modules,
        "EVENT_EPOCH_GAP_NOT_EXPLICIT",
        "Missing persisted epoch_set evidence or explicit event_epoch product gap.",
        failures,
    )
    for gap in gaps:
        check(bool(gap.get("required_action")), "PRODUCT_GAP_ACTION_MISSING", f"Gap lacks required_action: {gap}", failures)

    downloads = evidence.get("downloads") or []
    report_downloads = [item for item in downloads if item.get("requirement") == "report bundle"]
    check(bool(report_downloads), "DOWNLOAD_EVIDENCE_MISSING", "No report bundle download evidence recorded.", failures)
    if report_downloads:
        validate_zip(report_downloads[0], failures)

    inspect = evidence.get("artifact_inspect") or {}
    checks = inspect.get("checks") or {}
    boundary_scan = inspect.get("boundary_scan") or {}
    for key in ["report_pdf_present", "report_json_present", "metrics_csv_present", "pdf_header", "pdf_text_extractable"]:
        check(checks.get(key) is True, "ARTIFACT_CHECK_FAILED", f"Artifact check failed: {key}", failures)
    check(
        boundary_scan.get("non_diagnostic_boundary") is True or boundary_scan.get("pdf_non_diagnostic_boundary") is True,
        "NON_DIAGNOSTIC_BOUNDARY_MISSING",
        "Report bundle did not expose a non-diagnostic boundary.",
        failures,
    )
    check(
        boundary_scan.get("pdf_sensor_space_boundary") is True,
        "SENSOR_SPACE_BOUNDARY_MISSING",
        "PDF boundary scan did not find sensor/channel-space wording.",
        failures,
    )

    validator_results = run_boundary_validators(EVIDENCE_PATH, report_downloads, failures, warnings)
    product_gate = read_vr_eo_product_gate()
    product_blockers = list(product_gate.get("blockers") or [])
    for gap in gaps:
        product_blockers.append(
            {
                "code": "P0_PRODUCT_UI_GAP",
                "detail": f"{gap.get('module_id')}: {gap.get('gap')}",
                "required_action": gap.get("required_action"),
            }
        )

    output = {
        "schema_version": "qlanalyser-p0-ui-only-runner-acceptance-v0.1",
        "generated_at": datetime.now(UTC).isoformat(),
        "evidence_path": str(EVIDENCE_PATH),
        "status": "passed" if not failures else "failed",
        "runner_verdict": evidence.get("verdict"),
        "product_gate_status": "blocked" if product_blockers else "not_blocked_by_this_contract",
        "product_blockers": product_blockers,
        "vr_eo_0001_product_gate": product_gate,
        "important_boundary": "This acceptance validates the UI-only runner contract and evidence shape; it is not product release pass, module promotion, or P0 product pass. VR-EO-0001 decision=block and recorded UI gaps remain product blockers.",
        "product_gaps": gaps,
        "failures": failures,
        "warnings": warnings,
        "validator_results": validator_results,
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    ACCEPTANCE_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
