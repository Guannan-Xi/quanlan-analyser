import hashlib
import csv
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException

from backend.models.report import ReportCreate, ReportRead
from backend.services import audit_service, quota_service, state_store, task_service
from eeg_core.report.html_report import readable_artifact_label, write_html_report
from eeg_core.report.pdf_report import write_pdf_report

ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "data" / "reports"
DERIVATIVES_ROOT = ROOT / "data" / "derivatives"
PATH_TOKEN_RE = re.compile(r"(?i)([a-z]:[\\/][^\s\"'<>]+)")

_reports: dict[str, ReportRead] = state_store.load_registry("reports", ReportRead)


def _refresh_reports() -> None:
    _reports.clear()
    _reports.update(state_store.load_registry("reports", ReportRead))


def _save_reports() -> None:
    for report in _reports.values():
        state_store.upsert_item("reports", report)


def create_report(payload: ReportCreate) -> ReportRead:
    task = task_service.get_task(payload.task_id)
    if task.project_id != payload.project_id:
        raise HTTPException(status_code=422, detail="Report project_id must match the task project_id")

    report_payload = payload.model_dump()
    report_payload.update({"organization_id": task.organization_id, "owner_user_id": task.owner_user_id})
    report = ReportRead(**report_payload, html_path=REPORT_ROOT / payload.project_id / "pending" / "report.html")
    report_dir = REPORT_ROOT / payload.project_id / report.id
    report_dir.mkdir(parents=True, exist_ok=True)

    artifacts = [artifact.model_dump(mode="json") for artifact in task_service.list_task_artifacts(task.id)]
    sibling_analyses = _sibling_completed_analyses(task.model_dump(mode="json"))
    related_artifacts = _related_qc_and_audit_artifacts(task.model_dump(mode="json"))
    task_output_dir = DERIVATIVES_ROOT / task.project_id / task.id
    context = {
        "task": task.model_dump(mode="json"),
        "artifacts": artifacts,
        "related_artifacts": related_artifacts,
        "sibling_analyses": sibling_analyses,
        "task_output_dir": str(task_output_dir),
    }
    html_path = write_html_report(report_dir, payload.title, context)
    package_path = _write_report_package(report_dir, report.id, html_path, task.model_dump(mode="json"), task_output_dir, artifacts, related_artifacts, sibling_analyses)

    report.html_path = html_path
    report.package_path = package_path
    report.html_object_key = f"reports/{payload.project_id}/{report.id}/report.html"
    report.package_object_key = f"reports/{payload.project_id}/{report.id}/{package_path.name}"
    package_meta = _file_metadata(package_path)
    report.size_bytes = package_meta["size_bytes"]
    report.sha256 = package_meta["sha256"]
    report.quota_usage_json = {
        "resource_type": "report_package_storage_bytes",
        "quantity": report.size_bytes,
        "unit": "bytes",
        "billable": False,
    }
    audit = audit_service.record_event(
        action="report.created",
        object_type="report",
        object_id=report.id,
        organization_id=report.organization_id,
        project_id=report.project_id,
        actor_user_id=report.owner_user_id,
        metadata_json={
            "task_id": report.task_id,
            "package_object_key": report.package_object_key,
            "size_bytes": report.size_bytes,
            "sha256": report.sha256,
        },
    )
    report.audit_trace_id = audit.audit_trace_id
    quota_service.record_usage(
        resource_type="report_package_storage_bytes",
        action="report.created",
        quantity=float(report.size_bytes or 0),
        unit="bytes",
        source_type="report",
        source_id=report.id,
        organization_id=report.organization_id,
        project_id=report.project_id,
        owner_user_id=report.owner_user_id,
        metadata_json=report.quota_usage_json,
    )
    _reports[report.id] = report
    state_store.upsert_item("reports", report)
    return report


def get_report(report_id: str) -> ReportRead:
    _refresh_reports()
    try:
        return _reports[report_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Report not found") from exc


def get_report_file(report_id: str, kind: str) -> Path:
    report = get_report(report_id)
    if kind == "html":
        path = report.html_path
    elif kind == "package":
        path = report.package_path
    else:
        raise HTTPException(status_code=404, detail="Unknown report file kind")
    if path is None or not Path(path).exists():
        raise HTTPException(status_code=410, detail="Report file is not available on disk")
    return Path(path)


def _write_report_package(report_dir: Path, report_id: str, html_path: Path, task: dict, task_output_dir: Path, artifacts: list[dict], related_artifacts: list[dict] | None = None, sibling_analyses: list[dict] | None = None) -> Path:
    package_path = report_dir / f"{report_id}.zip"
    sanitized_dir = report_dir / "_package_sanitized"
    written: set[str] = set()

    def add_file(archive: ZipFile, source: Path, archive_name: str) -> None:
        normalized = archive_name.replace("\\", "/")
        if normalized in written:
            return
        archive.write(source, normalized)
        written.add(normalized)

    def add_customer_file(archive: ZipFile, source: Path, archive_name: str) -> None:
        normalized = archive_name.replace("\\", "/")
        if normalized in written:
            return
        packaged_source = _customer_safe_package_file(source, normalized, sanitized_dir)
        archive.write(packaged_source, normalized)
        written.add(normalized)

    with ZipFile(package_path, "w", compression=ZIP_DEFLATED) as archive:
        add_file(archive, html_path, "reports/report.html")
        report_manifest = report_dir / "report_manifest.json"
        report_manifest.write_text(
            json.dumps(
                {
                    "contract_version": "qlanalyser-report-package-v0.1",
                    "report_id": report_id,
                    "task_id": task.get("id"),
                    "project_id": task.get("project_id"),
                    "input_file_id": task.get("input_file_id"),
                    "module_name": task.get("module_name"),
                    "workflow_id": task.get("workflow_id"),
                    "data_preparation_plan_id": task.get("data_preparation_plan_id"),
                    "data_preparation_revision": task.get("data_preparation_revision"),
                    "artifact_count": len(artifacts),
                    "artifact_labels": _readable_artifact_labels(artifacts),
                    "included_analysis_modules": [item.get("module_name") for item in (sibling_analyses or [])],
                    "included_analysis_task_ids": [item.get("task", {}).get("id") for item in (sibling_analyses or [])],
                    "required_download_endpoints": [
                        f"/api/reports/{report_id}/html",
                        f"/api/reports/{report_id}/package",
                        "/api/artifacts/{artifact_id}/download",
                    ],
                    "artifact_path_policy": "package-relative",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        add_file(archive, report_manifest, "reports/report_manifest.json")
        report_json = _write_report_json_alias(report_dir, report_id, task, task_output_dir, artifacts, related_artifacts or [], sibling_analyses or [])
        add_file(archive, report_json, "reports/report.json")
        report_pdf = write_pdf_report(report_dir, "QLanalyser EEG report", _read_json_if_exists(report_json))
        add_file(archive, report_pdf, "reports/report.pdf")
        ica_audit = _write_ica_not_run_artifact(report_dir, task)
        add_file(archive, ica_audit, "preprocessing/ica/ica_audit_not_run.json")
        metrics_csv = _write_metrics_csv_alias(report_dir, task_output_dir)
        if metrics_csv is not None:
            add_file(archive, metrics_csv, "tables/metrics.csv")
        manifest = report_dir / "manifest.txt"
        manifest.write_text(
            "QLanalyser EEG V01 report package\n"
            f"report_id={report_id}\n"
            "artifact_path_policy=package-relative\n"
            "Included directories preserve task-relative paths where possible.\n",
            encoding="utf-8",
        )
        add_file(archive, manifest, "manifest.txt")

        if task_output_dir.exists():
            for child in task_output_dir.rglob("*"):
                if child.is_file():
                    add_customer_file(archive, child, child.relative_to(task_output_dir).as_posix())

        for artifact in artifacts:
            path = Path(artifact.get("path", ""))
            if path.exists() and path.is_file():
                try:
                    relative = path.relative_to(task_output_dir).as_posix()
                except ValueError:
                    relative = f"artifacts/{path.name}"
                add_customer_file(archive, path, relative)
        for artifact in related_artifacts or []:
            path = Path(artifact.get("path", ""))
            if path.exists() and path.is_file():
                prefix = artifact.get("package_prefix") or "related"
                add_customer_file(archive, path, f"{prefix}/{path.name}")
        for analysis in sibling_analyses or []:
            output_dir = Path(str(analysis.get("task_output_dir") or ""))
            prefix = analysis.get("package_prefix") or f"analyses/{analysis.get('module_name')}_{analysis.get('task', {}).get('id')}"
            if output_dir.exists():
                for child in output_dir.rglob("*"):
                    if child.is_file():
                        add_customer_file(archive, child, f"{prefix}/{child.relative_to(output_dir).as_posix()}")
    return package_path


def _write_ica_not_run_artifact(report_dir: Path, task: dict) -> Path:
    path = report_dir / "ica_audit_not_run.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "qlanalyser-ica-audit-boundary-v0.1",
                "status": "not_run",
                "reason": "ICA artifact cleaning is not part of this V01 report package unless an explicit ICA task is executed.",
                "module_boundary": "This artifact is a boundary record, not an ICA cleaning result.",
                "component_policy": {
                    "removed_components": [],
                    "kept_components": [],
                    "component_reason_score_label": "not_applicable_no_ica_components_were_estimated",
                    "score_label_policy": "No ICA score or label is reported because ICA was not run.",
                },
                "before_after_provenance": {
                    "before_cleaning_artifact": None,
                    "after_cleaning_artifact": None,
                    "provenance_status": "not_applicable_no_ica_transform_applied",
                },
                "task_context": {
                    "task_id": task.get("id"),
                    "project_id": task.get("project_id"),
                    "input_file_id": task.get("input_file_id"),
                    "data_preparation_plan_id": task.get("data_preparation_plan_id"),
                    "data_preparation_revision": task.get("data_preparation_revision"),
                },
                "non_diagnostic_boundary": "No ICA component-level interpretation, diagnosis, clinical marker, anatomical localization, or causal mechanism is reported.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _write_report_json_alias(report_dir: Path, report_id: str, task: dict, task_output_dir: Path, artifacts: list[dict], related_artifacts: list[dict] | None = None, sibling_analyses: list[dict] | None = None) -> Path:
    result_payload = _read_json_if_exists(task_output_dir / "result.json")
    manifest_payload = _read_json_if_exists(task_output_dir / "manifest.json")
    workflow_payload = _read_json_if_exists(task_output_dir / "reproducibility" / "workflow.json")
    software_versions = _read_json_if_exists(task_output_dir / "reproducibility" / "software_versions.json")
    scope_contract = _read_json_if_exists(task_output_dir / "reproducibility" / "scope_contract.json")
    table_dictionary = _read_json_if_exists(task_output_dir / "reproducibility" / "table_dictionary.json")
    report_json = {
        "schema_version": "qlanalyser-report-json-v0.1",
        "report_id": report_id,
        "analysis_id": task.get("id"),
        "task": {
            "id": task.get("id"),
            "project_id": task.get("project_id"),
            "input_file_id": task.get("input_file_id"),
            "module_name": task.get("module_name"),
            "workflow_id": task.get("workflow_id"),
            "data_preparation_plan_id": task.get("data_preparation_plan_id"),
            "data_preparation_revision": task.get("data_preparation_revision"),
        },
        "parameters": result_payload.get("parameters") or task.get("parameters_json") or {},
        "processing_steps": workflow_payload.get("steps", []),
        "software_version": software_versions,
        "timestamp": result_payload.get("generated_at") or result_payload.get("finished_at"),
        "warnings": result_payload.get("warnings", []),
        "methods_summary": (
            "BIDS-compatible report package summary: task artifacts are packaged with related QC evidence "
            "for the same project/input file when available. QC evidence includes metadata, waveform/filter "
            "preview artifacts, bad-channel audit JSON, channels.tsv, and UI evidence. Research-use only; "
            "not for clinical diagnosis."
        ),
        "bad_channel_summary": _bad_channel_summary_from_related(related_artifacts or []),
        "annotation_summary": _annotation_summary_from_related(related_artifacts or []),
        "qc_artifacts": [
            {
                "label": item.get("label"),
                "path": item.get("package_prefix") + "/" + Path(str(item.get("path", ""))).name if item.get("package_prefix") else None,
                "artifact_type": item.get("artifact_type"),
            }
            for item in (related_artifacts or [])
            if str(item.get("package_prefix", "")).startswith("qc")
        ],
        "non_diagnostic_boundary": "Research-use descriptive EEG analysis output; not for clinical diagnosis or treatment decisions.",
        "scientific_boundary": scope_contract or {},
        "source_data_refs": {
            "result": "result.json",
            "manifest": "manifest.json",
            "workflow": "reproducibility/workflow.json",
            "software_versions": "reproducibility/software_versions.json",
            "table_dictionary": "reproducibility/table_dictionary.json",
        },
        "artifact_count": len(artifacts),
        "artifact_labels": _readable_artifact_labels(artifacts),
        "included_analyses": [
            {
                "task_id": item.get("task", {}).get("id"),
                "module_name": item.get("module_name"),
                "workflow_id": item.get("workflow_id"),
                "artifact_count": len(item.get("artifacts") or []),
                "package_prefix": item.get("package_prefix"),
            }
            for item in (sibling_analyses or [])
        ],
        "manifest_summary": {
            "schema_version": manifest_payload.get("schema_version"),
            "artifact_schema_version": manifest_payload.get("artifact_schema_version"),
            "file_count": len(manifest_payload.get("files", [])) if isinstance(manifest_payload.get("files"), list) else None,
        },
        "table_dictionary": table_dictionary,
    }
    path = report_dir / "report.json"
    path.write_text(json.dumps(report_json, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_metrics_csv_alias(report_dir: Path, task_output_dir: Path) -> Path | None:
    candidates = [
        task_output_dir / "tables" / "band_power.csv",
        task_output_dir / "tables" / "channel_band_power.csv",
        task_output_dir / "tables" / "erp_metrics.csv",
        task_output_dir / "tables" / "tfr_summary_table.csv",
        task_output_dir / "tables" / "pac_channel_summary.csv",
        task_output_dir / "tables" / "pac_dynamic_curve.csv",
    ]
    source = next((candidate for candidate in candidates if candidate.exists()), None)
    if source is None:
        return None
    target = report_dir / "metrics.csv"
    with source.open("r", newline="", encoding="utf-8") as source_handle:
        reader = csv.DictReader(source_handle)
        fieldnames = list(reader.fieldnames or [])
        output_fields = ["analysis_id", "source_table", *fieldnames]
        with target.open("w", newline="", encoding="utf-8") as target_handle:
            writer = csv.DictWriter(target_handle, fieldnames=output_fields)
            writer.writeheader()
            for row in reader:
                writer.writerow({"analysis_id": task_output_dir.name, "source_table": source.name, **row})
    return target


def _readable_artifact_labels(artifacts: list[dict]) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for artifact in artifacts:
        label = readable_artifact_label(artifact)
        if label in seen:
            continue
        labels.append(label)
        seen.add(label)
    return labels


def _sibling_completed_analyses(task: dict) -> list[dict]:
    project_id = task.get("project_id")
    input_file_id = task.get("input_file_id")
    supported = {"psd", "erp", "epilepsy", "tfr", "pac", "reference_csd", "connectivity"}
    analyses: list[dict] = []
    for candidate in task_service.list_tasks():
        if candidate.project_id != project_id or candidate.input_file_id != input_file_id or candidate.status != "completed":
            continue
        if candidate.module_name not in supported:
            continue
        task_payload = candidate.model_dump(mode="json")
        artifacts = [artifact.model_dump(mode="json") for artifact in task_service.list_task_artifacts(candidate.id)]
        module_name = str(candidate.module_name)
        analyses.append(
            {
                "task": task_payload,
                "task_id": candidate.id,
                "module_name": module_name,
                "workflow_id": candidate.workflow_id,
                "artifacts": artifacts,
                "task_output_dir": str(DERIVATIVES_ROOT / candidate.project_id / candidate.id),
                "package_prefix": f"analyses/{module_name}_{candidate.id}",
            }
        )
    analyses.sort(key=lambda item: (str(item.get("module_name")), str(item.get("task_id"))))
    return analyses


def _related_qc_and_audit_artifacts(task: dict) -> list[dict]:
    related: list[dict] = []
    project_id = task.get("project_id")
    input_file_id = task.get("input_file_id")
    for candidate in task_service.list_tasks():
        if candidate.project_id != project_id or candidate.input_file_id != input_file_id or candidate.status != "completed":
            continue
        if candidate.module_name != "qc":
            continue
        for artifact in task_service.list_task_artifacts(candidate.id):
            item = artifact.model_dump(mode="json")
            item["package_prefix"] = f"qc/{candidate.workflow_id or candidate.id}"
            related.append(item)

    plan_id = task.get("data_preparation_plan_id")
    revision = task.get("data_preparation_revision")
    if plan_id and revision:
        audit_root = DERIVATIVES_ROOT / str(project_id) / "data_preparation" / str(plan_id) / f"revision_{revision}" / "quality"
        if audit_root.exists():
            for path in audit_root.rglob("*"):
                if path.is_file():
                    related.append(
                        {
                            "label": path.stem,
                            "artifact_type": path.suffix.lstrip(".") or "file",
                            "path": str(path),
                            "package_prefix": "quality/bad_channel_audit",
                        }
                    )
    return related


def _bad_channel_summary_from_related(related_artifacts: list[dict]) -> dict:
    audit_items = [item for item in related_artifacts if "bad_channel_audit" in str(item.get("package_prefix", ""))]
    return {
        "artifact_count": len(audit_items),
        "has_audit_json": any(str(item.get("path", "")).lower().endswith("bad_channel_audit.json") for item in audit_items),
        "has_channels_tsv": any(str(item.get("path", "")).lower().endswith("channels.tsv") for item in audit_items),
        "boundary": "Bad-channel review records user decisions and provenance only; it is not a clinical diagnosis.",
    }


def _annotation_summary_from_related(related_artifacts: list[dict]) -> dict:
    qc_items = [item for item in related_artifacts if str(item.get("package_prefix", "")).startswith("qc/")]
    return {
        "qc_artifact_count": len(qc_items),
        "has_qc_json": any(str(item.get("path", "")).lower().endswith(".json") for item in qc_items),
        "has_qc_figure": any(str(item.get("path", "")).lower().endswith((".svg", ".png")) for item in qc_items),
        "boundary": "Annotation and QC summaries are descriptive review aids; they do not establish clinical or causal conclusions.",
    }


def _read_json_if_exists(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _customer_safe_package_file(source: Path, archive_name: str, sanitized_dir: Path) -> Path:
    suffix = source.suffix.lower()
    if suffix not in {".json", ".txt", ".log", ".csv", ".tsv", ".md", ".html", ".xml", ".yaml", ".yml"}:
        return source

    text = source.read_text(encoding="utf-8", errors="replace")
    if suffix == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            safe_text = _redact_customer_text(text)
        else:
            payload = _redact_customer_payload(payload)
            safe_text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        safe_text = _redact_customer_text(text)

    target = sanitized_dir / archive_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(safe_text, encoding="utf-8")
    return target


def _redact_customer_payload(value):
    if isinstance(value, dict):
        return {key: _redact_customer_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_customer_payload(item) for item in value]
    if isinstance(value, str):
        return _redact_customer_text(value)
    return value


def _redact_customer_text(text: str) -> str:
    normalized_roots = [
        str(ROOT).replace("\\", "/"),
        str(ROOT.parent).replace("\\", "/"),
        str(DERIVATIVES_ROOT).replace("\\", "/"),
        "C:/Users/",
    ]

    def redact_token(match: re.Match[str]) -> str:
        raw = match.group(1)
        normalized = raw.replace("\\", "/")
        for root in normalized_roots:
            if normalized.startswith(root):
                return f"package-relative:{Path(normalized).name}"
        if normalized.startswith("D:/") or normalized.startswith("C:/Users/"):
            return f"package-relative:{Path(normalized).name}"
        return raw

    return PATH_TOKEN_RE.sub(redact_token, text)


def _file_metadata(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"size_bytes": path.stat().st_size, "sha256": digest.hexdigest()}
