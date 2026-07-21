from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import HTTPException

from backend.models.analysis_task import AnalysisTaskCreate
from backend.models.eeg_file import EEGFileRead
from backend.models.project import ProjectRead
from backend.models.report import ReportCreate
from backend.services import metadata_service, report_service, storage_service, task_service
from scripts import build_real_dataset_owner_review_packet as input_gate


EVIDENCE_ROOT = ROOT / "work" / "release_evidence" / "07-full-product-e2e-pdca" / "11_real_dataset_owner_review"
REGRESSION_DIR = EVIDENCE_ROOT / "02_regression"
REPORTS_DIR = EVIDENCE_ROOT / "03_reports"
OWNER_DIR = EVIDENCE_ROOT / "05_owner_packet"
DEFAULT_MANIFEST_PATH = EVIDENCE_ROOT / "input_manifest.json"
REGRESSION_PATH = REGRESSION_DIR / "real_dataset_regression_run.json"
REPORT_INVENTORY_PATH = REPORTS_DIR / "real_dataset_report_inventory.json"
FINAL_PACKET_PATH = OWNER_DIR / "real_dataset_owner_review_final_packet.json"
PROJECT_ID = "proj_real_dataset_owner_review_20260626"

METHOD_ALIASES = {
    "multitaper": "multitaper_psd",
    "multitaper_psd_tfr": "multitaper_psd",
    "preprocess": "qc",
}

EVENT_DEPENDENT_METHODS = {"erp", "tfr", "multitaper_tfr"}

UNSAFE_CLAIM_PATTERNS = [
    re.compile(r"\bclinical decision\b", re.I),
    re.compile(r"\btreatment recommendation\b", re.I),
    re.compile(r"\bdiagnostic conclusion\b", re.I),
    re.compile(r"\bproves? causality\b", re.I),
    re.compile(r"\bexact source localization\b", re.I),
    re.compile(r"\bbrain[- ]region activation\b", re.I),
    re.compile(r"\bstatistical significance\b", re.I),
    re.compile(r"\bp[- ]?value\b", re.I),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: str | Path) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except (ValueError, OSError):
        return str(p).replace("\\", "/")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path, limit_mb: int = 512) -> str | None:
    if path.stat().st_size > limit_mb * 1024 * 1024:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_id(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_").lower()
    return cleaned or fallback


def run_input_gate(manifest_path: Path, candidate_limit: int) -> dict[str, Any]:
    command = [
        sys.executable,
        "-X",
        "utf8",
        str(ROOT / "scripts" / "build_real_dataset_owner_review_packet.py"),
        "--input-manifest",
        str(manifest_path),
        "--candidate-limit",
        str(candidate_limit),
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, encoding="utf-8", capture_output=True)
    preflight = read_json(input_gate.PREFLIGHT_PATH, {})
    preflight["builder_command"] = " ".join(command)
    preflight["builder_exit_code"] = result.returncode
    preflight["builder_stdout_tail"] = result.stdout[-2000:]
    preflight["builder_stderr_tail"] = result.stderr[-2000:]
    return preflight


def blocked_outputs(preflight: dict[str, Any], *, manifest_path: Path) -> dict[str, Any]:
    blockers = list(preflight.get("blockers") or ["real dataset input gate did not pass"])
    regression = {
        "status": "blocked_final_receipt",
        "generated_at": utc_now(),
        "manifest_path": rel(manifest_path),
        "input_gate": rel(input_gate.PREFLIGHT_PATH),
        "blockers": blockers,
        "datasets": [],
        "method_matrix": [],
        "reports": [],
        "boundary": "No real-dataset task was executed because the owner authorization gate did not pass.",
    }
    report_inventory = {
        "status": "blocked",
        "generated_at": utc_now(),
        "reason": "No report package can be created before an owner-authorized dataset regression passes at least one task.",
        "blockers": blockers,
        "reports": [],
        "claim_scan": {"status": "not_run"},
    }
    final_packet = final_packet_from(regression, report_inventory, preflight)
    write_json(REGRESSION_PATH, regression)
    write_json(REPORT_INVENTORY_PATH, report_inventory)
    write_json(FINAL_PACKET_PATH, final_packet)
    return final_packet


def normalize_allowed_methods(methods: Any) -> list[str]:
    if not isinstance(methods, list):
        return []
    normalized = []
    for method in methods:
        key = METHOD_ALIASES.get(str(method).strip(), str(method).strip())
        if key and key not in normalized:
            normalized.append(key)
    return normalized


def has_events(dataset: dict[str, Any]) -> bool:
    return dataset.get("event_markers_available") is True


def method_spec(method: str, event_markers_available: bool) -> dict[str, Any] | None:
    if method == "qc":
        return {"module_name": "qc", "workflow_id": "metadata_qc", "parameters_json": {}}
    if method == "psd":
        return {"module_name": "psd", "workflow_id": "resting_psd", "parameters_json": {"fmin": 1.0, "fmax": 40.0}}
    if method == "erp":
        if not event_markers_available:
            return None
        return {
            "module_name": "erp",
            "workflow_id": "erp_p300",
            "parameters_json": {"tmin": -0.2, "tmax": 0.8, "baseline": [None, 0.0]},
        }
    if method == "tfr":
        if not event_markers_available:
            return None
        return {
            "module_name": "tfr",
            "workflow_id": "tfr_ersp_itc",
            "parameters_json": {"tmin": -0.2, "tmax": 0.8, "baseline": [-0.2, 0.0], "freqs": [8.0, 13.0, 30.0], "n_cycles": 3.0, "decim": 2},
        }
    if method == "multitaper_psd":
        return {
            "module_name": "multitaper_psd_tfr",
            "workflow_id": "multitaper_psd_tfr",
            "parameters_json": {"analysis_family": "psd", "fmin": 1.0, "fmax": 40.0, "freqs": [8.0, 13.0, 30.0]},
        }
    if method == "multitaper_tfr":
        if not event_markers_available:
            return None
        return {
            "module_name": "multitaper_psd_tfr",
            "workflow_id": "multitaper_psd_tfr",
            "parameters_json": {
                "analysis_family": "tfr",
                "fmin": 1.0,
                "fmax": 40.0,
                "freqs": [8.0, 13.0, 30.0],
                "tmin": -0.2,
                "tmax": 0.8,
                "baseline": [-0.2, 0.0],
                "decim": 1,
            },
        }
    if method == "reference_csd":
        return {"module_name": "reference_csd", "workflow_id": "reference_csd", "parameters_json": {"reference_mode": "average"}}
    if method == "pac":
        return {
            "module_name": "pac",
            "workflow_id": "pac_cfc",
            "parameters_json": {
                "phase_freqs": [4.0, 8.0],
                "phase_band_width": 2.0,
                "amp_freqs": [40.0],
                "amp_band_width": 12.0,
                "n_surrogates": 3,
                "dynamic_window_sec": 4.0,
                "dynamic_step_sec": 4.0,
                "random_state": 20260626,
            },
        }
    if method == "connectivity":
        return {
            "module_name": "connectivity",
            "workflow_id": "connectivity",
            "parameters_json": {"method": "correlation", "fmin": 8.0, "fmax": 12.0, "segment_length_sec": 4.0},
        }
    return None


def upsert_regression_project() -> ProjectRead:
    project = ProjectRead(
        id=PROJECT_ID,
        name="QLanalyser owner-authorized real dataset regression",
        description="Owner-authorized anonymized dataset regression project for local acceptance evidence.",
        research_type="owner_review_regression",
        owner_user_id="local-user",
        owner_id="local-user",
        created_by="real_dataset_regression_runner",
        updated_by="real_dataset_regression_runner",
        quota_account_id="demo-customer",
    )
    return storage_service.upsert_project(project)


def register_dataset(project: ProjectRead, dataset: dict[str, Any], manifest_dataset: dict[str, Any]) -> dict[str, Any]:
    file_path = Path(str(dataset["path"]))
    digest = sha256_file(file_path)
    dataset_key = safe_id(str(dataset.get("dataset_id") or file_path.stem), "dataset")
    eeg_file = EEGFileRead(
        id=f"eeg_real_{dataset_key}_{(digest or 'largefile')[:12]}",
        organization_id=project.organization_id,
        project_id=project.id,
        original_filename=file_path.name,
        stored_path=file_path,
        detected_format=file_path.suffix.lower().lstrip("."),
        object_key=f"owner_authorized/{dataset_key}/{file_path.name}",
        size_bytes=file_path.stat().st_size,
        sha256=digest,
        metadata_json={
            "owner_review": {
                "dataset_id": dataset.get("dataset_id"),
                "path_alias": file_path.name,
                "authorization_note_present": bool(manifest_dataset.get("authorization_note")),
                "allowed_methods": dataset.get("allowed_methods"),
                "known_limitations": dataset.get("known_limitations", []),
                "raw_path_redacted_in_reports": True,
            }
        },
        status="owner_authorized",
        upload_status="owner_authorized_manifest",
        owner_user_id=project.owner_user_id,
        created_by="real_dataset_regression_runner",
        quota_account_id=project.quota_account_id,
    )
    metadata_status = "not_run"
    try:
        metadata_service.extract_metadata(eeg_file)
        eeg_file.status = "metadata_ready"
        eeg_file.metadata_extracted_at = datetime.now(timezone.utc)
        metadata_status = "passed"
    except Exception as exc:  # real-data regression should report, not hide, metadata failures
        eeg_file.metadata_json["metadata_status"] = "metadata_extraction_failed"
        eeg_file.metadata_json["metadata_error"] = str(exc)
        metadata_status = "failed"
    registered = storage_service.register_eeg_file(eeg_file)
    return {
        "dataset_id": dataset.get("dataset_id"),
        "path_alias": file_path.name,
        "eeg_file_id": registered.id,
        "format": registered.detected_format,
        "size_bytes": registered.size_bytes,
        "sha256_if_small": registered.sha256,
        "metadata_status": metadata_status,
        "metadata": {
            "sampling_rate": registered.sampling_rate,
            "channel_count": registered.channel_count,
            "duration_sec": registered.duration_sec,
            "detected_format": registered.detected_format,
        },
        "status": registered.status,
    }


def run_method(project: ProjectRead, eeg_file_id: str, dataset_id: str, method: str, spec: dict[str, Any]) -> dict[str, Any]:
    started = time.time()
    parameters = dict(spec["parameters_json"])
    parameters.setdefault("input_file_id", eeg_file_id)
    parameters.setdefault("owner_review_dataset_id", dataset_id)
    payload = AnalysisTaskCreate(
        organization_id=project.organization_id,
        project_id=project.id,
        input_file_id=eeg_file_id,
        module_name=spec["module_name"],
        workflow_id=spec["workflow_id"],
        parameters_json=parameters,
        owner_user_id=project.owner_user_id,
        created_by="real_dataset_regression_runner",
        idempotency_key=f"real-dataset-owner-review:{dataset_id}:{method}",
    )
    try:
        task = task_service.create_task(payload)
        artifacts = task_service.list_task_artifacts(task.id)
        return {
            "dataset_id": dataset_id,
            "method": method,
            "module_name": task.module_name,
            "workflow_id": task.workflow_id,
            "status": task.status,
            "task_id": task.id,
            "artifact_count": len(artifacts),
            "artifacts": [
                {"artifact_id": item.id, "label": item.label, "artifact_type": item.artifact_type, "path": rel(item.path)}
                for item in artifacts
            ],
            "elapsed_sec": round(time.time() - started, 3),
        }
    except HTTPException as exc:
        return {
            "dataset_id": dataset_id,
            "method": method,
            "module_name": spec["module_name"],
            "workflow_id": spec["workflow_id"],
            "status": "failed",
            "http_status": exc.status_code,
            "error": exc.detail,
            "elapsed_sec": round(time.time() - started, 3),
        }
    except Exception as exc:
        return {
            "dataset_id": dataset_id,
            "method": method,
            "module_name": spec["module_name"],
            "workflow_id": spec["workflow_id"],
            "status": "failed",
            "error": str(exc),
            "elapsed_sec": round(time.time() - started, 3),
        }


def create_report_for_task(project: ProjectRead, dataset_id: str, row: dict[str, Any]) -> dict[str, Any]:
    task_id = row.get("task_id")
    if not task_id:
        return {"dataset_id": dataset_id, "method": row.get("method"), "status": "skipped", "reason": "no completed task_id"}
    try:
        report = report_service.create_report(
            ReportCreate(
                organization_id=project.organization_id,
                project_id=project.id,
                task_id=str(task_id),
                title=f"QLanalyser owner review report - {dataset_id} - {row.get('method')}",
                owner_user_id=project.owner_user_id,
                created_by="real_dataset_regression_runner",
            )
        )
        package_scan = inspect_report_package(report.package_path)
        return {
            "dataset_id": dataset_id,
            "method": row.get("method"),
            "status": "passed" if package_scan["required_entries_present"] else "failed",
            "report_id": report.id,
            "html_path": rel(report.html_path),
            "package_path": rel(report.package_path) if report.package_path else None,
            "package_object_key": report.package_object_key,
            "size_bytes": report.size_bytes,
            "sha256": report.sha256,
            "package_scan": package_scan,
            "claim_scan": scan_report_claims(report.package_path),
        }
    except HTTPException as exc:
        return {"dataset_id": dataset_id, "method": row.get("method"), "status": "failed", "http_status": exc.status_code, "error": exc.detail}
    except Exception as exc:
        return {"dataset_id": dataset_id, "method": row.get("method"), "status": "failed", "error": str(exc)}


def inspect_report_package(path: Path | None) -> dict[str, Any]:
    required = ["reports/report.html", "reports/report_manifest.json", "reports/report.json", "reports/report.pdf"]
    if path is None or not Path(path).exists():
        return {"status": "missing", "path": None, "required_entries_present": False, "entries": []}
    with zipfile.ZipFile(path) as archive:
        entries = archive.namelist()
    return {
        "status": "passed",
        "path": rel(path),
        "entry_count": len(entries),
        "required_entries": required,
        "missing_required_entries": [entry for entry in required if entry not in entries],
        "required_entries_present": all(entry in entries for entry in required),
        "entries_sample": entries[:80],
    }


def scan_report_claims(path: Path | None) -> dict[str, Any]:
    if path is None or not Path(path).exists():
        return {"status": "missing", "path": None, "findings": []}
    findings: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.lower().endswith((".html", ".json", ".txt", ".md", ".csv", ".tsv")):
                continue
            try:
                text = archive.read(name).decode("utf-8", errors="replace")
            except Exception:
                continue
            for pattern in UNSAFE_CLAIM_PATTERNS:
                if pattern.search(text):
                    findings.append({"entry": name, "pattern": pattern.pattern})
    return {
        "status": "passed" if not findings else "failed",
        "path": rel(path),
        "findings": findings,
        "boundary": "Scan catches unsupported positive claims; limitation and non-clinical boundary statements are allowed.",
    }


def run_regression(manifest_path: Path, preflight: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = read_json(manifest_path, {})
    datasets = preflight.get("manifest_validation", {}).get("datasets") or []
    manifest_datasets = {str(item.get("dataset_id")): item for item in manifest.get("datasets", []) if isinstance(item, dict)}
    project = upsert_regression_project()

    dataset_records: list[dict[str, Any]] = []
    method_matrix: list[dict[str, Any]] = []
    report_rows: list[dict[str, Any]] = []
    for dataset in datasets:
        dataset_id = str(dataset.get("dataset_id") or "dataset")
        manifest_dataset = manifest_datasets.get(dataset_id, {})
        registered = register_dataset(project, dataset, manifest_dataset)
        dataset_records.append(registered)
        event_markers_available = has_events(dataset)
        for method in normalize_allowed_methods(dataset.get("allowed_methods")):
            spec = method_spec(method, event_markers_available)
            if spec is None:
                reason = "event markers are required" if method in EVENT_DEPENDENT_METHODS else "unsupported method"
                method_matrix.append({"dataset_id": dataset_id, "method": method, "status": "skipped", "reason": reason})
                continue
            result = run_method(project, registered["eeg_file_id"], dataset_id, method, spec)
            method_matrix.append(result)

        completed = [row for row in method_matrix if row.get("dataset_id") == dataset_id and row.get("status") == "completed"]
        report_seed = next((row for row in completed if row.get("method") in {"psd", "qc", "multitaper_psd"}), completed[0] if completed else None)
        if report_seed is None:
            report_rows.append({"dataset_id": dataset_id, "status": "skipped", "reason": "no completed task for report generation"})
        else:
            report_rows.append(create_report_for_task(project, dataset_id, report_seed))

    passed_methods = [row for row in method_matrix if row.get("status") == "completed"]
    failed_methods = [row for row in method_matrix if row.get("status") == "failed"]
    passed_reports = [row for row in report_rows if row.get("status") == "passed"]
    claim_failures = [
        item
        for row in report_rows
        for item in (row.get("claim_scan") or {}).get("findings", [])
    ]
    status = "completed_final_receipt" if passed_methods and passed_reports and not claim_failures else "blocked_final_receipt"
    blockers = []
    if not passed_methods:
        blockers.append("no authorized real-dataset method completed")
    if not passed_reports:
        blockers.append("no authorized real-dataset report package passed required-entry checks")
    if claim_failures:
        blockers.append("report forbidden claim scan failed")
    if failed_methods:
        blockers.append(f"{len(failed_methods)} method(s) failed; inspect method_matrix")

    regression = {
        "status": status,
        "generated_at": utc_now(),
        "manifest_path": rel(manifest_path),
        "input_gate": rel(input_gate.PREFLIGHT_PATH),
        "project_id": project.id,
        "datasets": dataset_records,
        "method_matrix": method_matrix,
        "summary": {
            "dataset_count": len(dataset_records),
            "method_passed": len(passed_methods),
            "method_skipped": len([row for row in method_matrix if row.get("status") == "skipped"]),
            "method_failed": len(failed_methods),
            "report_passed": len(passed_reports),
        },
        "blockers": blockers,
        "boundary": "Single-record real-dataset regression validates workflow execution and report packaging only; it is not clinical, causal, source-localization, statistical, or cohort-validity evidence.",
    }
    report_inventory = {
        "status": "passed" if passed_reports and not claim_failures else "blocked",
        "generated_at": utc_now(),
        "reports": report_rows,
        "required_report_entries": ["reports/report.html", "reports/report_manifest.json", "reports/report.json", "reports/report.pdf"],
        "claim_scan_summary": {
            "status": "passed" if not claim_failures else "failed",
            "finding_count": len(claim_failures),
            "findings": claim_failures,
        },
    }
    return regression, report_inventory


def final_packet_from(regression: dict[str, Any], report_inventory: dict[str, Any], preflight: dict[str, Any]) -> dict[str, Any]:
    status = regression.get("status", "blocked_final_receipt")
    return {
        "status": status,
        "generated_at": utc_now(),
        "route_decision": {
            "lane": "gpt55_planner_or_acceptance + script_validator",
            "decision": "Run owner-manifest input gate first; execute backend regression only when authorization passes.",
        },
        "execution_packets": [
            {"id": "real_dataset_input_gate", "status": preflight.get("status"), "artifact": rel(input_gate.PREFLIGHT_PATH)},
            {"id": "authorized_real_dataset_regression", "status": regression.get("status"), "artifact": rel(REGRESSION_PATH)},
            {"id": "real_dataset_report_inventory", "status": report_inventory.get("status"), "artifact": rel(REPORT_INVENTORY_PATH)},
        ],
        "executor_evidence": {
            "input_gate": rel(input_gate.PREFLIGHT_PATH),
            "candidate_inventory": rel(input_gate.CANDIDATE_INVENTORY_PATH),
            "regression_run": rel(REGRESSION_PATH),
            "report_inventory": rel(REPORT_INVENTORY_PATH),
        },
        "targeted_or_full_e2e": {
            "scope": "authorized_manifest_datasets_only",
            "status": regression.get("status"),
            "dataset_count": len(regression.get("datasets") or []),
            "method_count": len(regression.get("method_matrix") or []),
        },
        "page_visual_review": {
            "status": "not_applicable_to_this_script_slice",
            "reason": "This slice adds backend/report regression infrastructure; UI visual gates remain in full-product acceptance packet.",
        },
        "gpt55_acceptance": {
            "status": "accepted" if status == "completed_final_receipt" else "accepted_blocked_state",
            "blockers": regression.get("blockers") or preflight.get("blockers") or [],
            "boundary": regression.get("boundary"),
        },
        "final_receipt": status,
        "next_real_artifact": "owner-provided input_manifest.json with anonymized authorized datasets" if status != "completed_final_receipt" else "owner real-dataset release review decision",
        "route_chain": "full-product synthetic acceptance -> real-dataset input gate -> authorized regression runner -> report package/claim scan -> owner packet",
        "model_lane": "GPT-5.5/Codex owns design and acceptance; local script-validator executes deterministic checks.",
        "headroom_savings": "No Headroom savings claimed; router/Headroom/IPC/gateway were not changed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run QLanalyser real-dataset regression from an owner-authorized manifest.")
    parser.add_argument("--input-manifest", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--candidate-limit", type=int, default=200)
    parser.add_argument("--fail-on-blocked", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.input_manifest)
    REGRESSION_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    OWNER_DIR.mkdir(parents=True, exist_ok=True)

    preflight = run_input_gate(manifest_path, args.candidate_limit)
    if preflight.get("status") != "passed":
        final_packet = blocked_outputs(preflight, manifest_path=manifest_path)
        print(json.dumps({"status": final_packet["status"], "packet": rel(FINAL_PACKET_PATH), "blockers": final_packet["gpt55_acceptance"]["blockers"]}, ensure_ascii=False, indent=2))
        return 1 if args.fail_on_blocked else 0

    regression, report_inventory = run_regression(manifest_path, preflight)
    write_json(REGRESSION_PATH, regression)
    write_json(REPORT_INVENTORY_PATH, report_inventory)
    final_packet = final_packet_from(regression, report_inventory, preflight)
    write_json(FINAL_PACKET_PATH, final_packet)
    print(json.dumps({"status": final_packet["status"], "packet": rel(FINAL_PACKET_PATH), "blockers": final_packet["gpt55_acceptance"]["blockers"]}, ensure_ascii=False, indent=2))
    return 0 if final_packet["status"] == "completed_final_receipt" or not args.fail_on_blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
