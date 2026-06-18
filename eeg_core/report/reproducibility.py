import hashlib
import json
import mimetypes
import platform
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any


CONTRACT_SCHEMA_VERSION = "qlanalyser-output-v0.1"
PRODUCT_NAME = "QLanalyser Online"
PRODUCT_VERSION = "QLanalyser Online v0.1 Pilot"
MANIFEST_FILENAME = "manifest.json"
RESULT_FILENAME = "result.json"
LOG_FILENAME = "log.txt"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def collect_software_versions() -> dict:
    packages = {}
    for package in ("mne", "numpy", "scipy", "pandas", "fastapi", "pydantic"):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = None
    return {
        "generated_at": _utc_now(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": packages,
    }


def write_json(path: str | Path, payload: dict) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def write_reproducibility_files(
    output_dir: str | Path,
    *,
    module_name: str,
    input_path: str | Path,
    parameters: dict,
    workflow_steps: list[dict] | None = None,
) -> dict[str, Path]:
    reproducibility = Path(output_dir) / "reproducibility"
    reproducibility.mkdir(parents=True, exist_ok=True)
    workflow = {
        "module": module_name,
        "input": str(input_path),
        "parameters": parameters,
        "steps": workflow_steps
        or [
            {
                "name": "read_raw",
                "description": "Read EEG data with the MNE reader selected by file suffix.",
            },
            {
                "name": module_name,
                "description": f"Run the V01 {module_name} analysis module.",
            },
            {
                "name": "write_outputs",
                "description": "Write tables, summaries, method text, and reproducibility files.",
            },
        ],
    }
    return {
        "software_versions": write_json(reproducibility / "software_versions.json", collect_software_versions()),
        "workflow": write_json(reproducibility / "workflow.json", workflow),
    }


def write_output_contract(
    output_dir: str | Path,
    *,
    job_type: str,
    module_name: str,
    input_path: str | Path,
    parameters: dict,
    summary: dict,
    outputs: dict[str, str | Path],
    status: str = "completed",
    started_at: str | None = None,
    finished_at: str | None = None,
    log_lines: list[str] | None = None,
) -> dict[str, Path]:
    """Write the v0.1 task-level contract files in a stable order."""
    output_path = Path(output_dir)
    finished = finished_at or _utc_now()
    result_path = write_result_contract(
        output_path / RESULT_FILENAME,
        build_result_contract(
            output_path,
            job_type=job_type,
            module_name=module_name,
            input_path=input_path,
            parameters=parameters,
            summary=summary,
            outputs=outputs,
            status=status,
            started_at=started_at or finished,
            finished_at=finished,
        ),
    )
    log_path = write_run_log(
        output_path,
        _build_default_log_lines(
            job_type=job_type,
            module_name=module_name,
            input_path=input_path,
            parameters=parameters,
            status=status,
            outputs=outputs,
            extra_lines=log_lines or [],
        ),
    )
    manifest_path = write_manifest(output_path)
    return {"result": result_path, "log": log_path, "manifest": manifest_path}


def build_result_contract(
    output_dir: str | Path,
    *,
    job_type: str,
    module_name: str,
    input_path: str | Path,
    parameters: dict,
    summary: dict,
    outputs: dict[str, str | Path],
    status: str,
    started_at: str,
    finished_at: str,
) -> dict:
    output_path = Path(output_dir)
    output_entries = []
    for label, artifact_path in outputs.items():
        path = Path(artifact_path)
        if path.exists() and path.is_file():
            output_entries.append(_file_entry(output_path, path, label=label))

    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "product_name": PRODUCT_NAME,
        "product_version": PRODUCT_VERSION,
        "job_id": output_path.name,
        "job_type": job_type,
        "module_name": module_name,
        "status": status,
        "input": {
            "path": str(input_path),
            "filename": Path(input_path).name,
        },
        "parameters": parameters,
        "summary": summary,
        "metrics": _extract_metrics(summary),
        "warnings": _extract_warnings(summary),
        "errors": _extract_errors(summary),
        "outputs": output_entries,
        "references": _contract_references(output_path),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": None,
        "generated_at": finished_at,
    }


def write_result_contract(path: str | Path, payload: dict) -> Path:
    return write_json(path, payload)


def write_run_log(output_dir: str | Path, lines: list[str]) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    generated_at = _utc_now()
    content_lines = [f"[{generated_at}] {line}" for line in lines]
    log_path = output_path / LOG_FILENAME
    log_path.write_text("\n".join(content_lines).rstrip() + "\n", encoding="utf-8")
    return log_path


def build_manifest(output_dir: str | Path) -> dict:
    output_path = Path(output_dir)
    files = []
    for path in sorted(output_path.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        if _relative_path(output_path, path) == MANIFEST_FILENAME:
            continue
        files.append(_file_entry(output_path, path))
    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "product_name": PRODUCT_NAME,
        "product_version": PRODUCT_VERSION,
        "job_id": output_path.name,
        "created_at": _utc_now(),
        "manifest_excludes": [MANIFEST_FILENAME],
        "files": files,
    }


def write_manifest(output_dir: str | Path) -> Path:
    output_path = Path(output_dir)
    return write_json(output_path / MANIFEST_FILENAME, build_manifest(output_path))


def _build_default_log_lines(
    *,
    job_type: str,
    module_name: str,
    input_path: str | Path,
    parameters: dict,
    status: str,
    outputs: dict[str, str | Path],
    extra_lines: list[str],
) -> list[str]:
    lines = [
        f"job_type={job_type}",
        f"module={module_name}",
        f"input={input_path}",
        "parameters=" + json.dumps(parameters, ensure_ascii=False, sort_keys=True),
        f"status={status}",
    ]
    lines.extend(extra_lines)
    for label, path in outputs.items():
        lines.append(f"output[{label}]={_normalize_for_log(path)}")
    lines.append(f"output[{RESULT_FILENAME}]={RESULT_FILENAME}")
    lines.append(f"output[{LOG_FILENAME}]={LOG_FILENAME}")
    lines.append(f"output[{MANIFEST_FILENAME}]={MANIFEST_FILENAME}")
    return lines


def _contract_references(output_dir: Path) -> dict[str, str]:
    references: dict[str, str] = {}
    candidates = {
        "parameters": output_dir / "reproducibility" / "parameters.json",
        "method_description": output_dir / "reproducibility" / "method_description.txt",
        "software_versions": output_dir / "reproducibility" / "software_versions.json",
        "workflow": output_dir / "reproducibility" / "workflow.json",
        "log": output_dir / LOG_FILENAME,
        "manifest": output_dir / MANIFEST_FILENAME,
    }
    for label, path in candidates.items():
        references[label] = _relative_path(output_dir, path)
    return references


def _extract_metrics(summary: dict) -> dict:
    metrics: dict[str, Any] = {}
    skipped = {"band_power", "checks", "metadata", "parameters", "channel_ptp_uv", "conditions", "components"}
    for key, value in summary.items():
        if key in skipped:
            continue
        if _is_json_scalar(value) or _is_json_scalar_list(value):
            metrics[key] = value
    metadata = summary.get("metadata")
    if isinstance(metadata, dict):
        for key in ("sampling_rate", "duration_sec", "eeg_channel_count", "annotation_count"):
            if key in metadata and _is_json_scalar(metadata[key]):
                metrics[f"metadata_{key}"] = metadata[key]
    return metrics


def _extract_warnings(summary: dict) -> list[dict]:
    warnings: list[dict] = []
    checks = summary.get("checks")
    if isinstance(checks, list):
        for check in checks:
            if isinstance(check, dict) and check.get("ok") is False:
                warnings.append({
                    "name": str(check.get("name", "check")),
                    "detail": str(check.get("detail", "")),
                })
    if summary.get("status") == "warning" and not warnings:
        warnings.append({"name": "status", "detail": "summary status is warning"})
    return warnings


def _extract_errors(summary: dict) -> list[dict]:
    if summary.get("status") != "failed":
        return []
    metadata = summary.get("metadata")
    metadata_error = metadata.get("error") if isinstance(metadata, dict) else None
    error = summary.get("error") or metadata_error
    return [{"name": "summary", "detail": str(error or "summary status is failed")}]


def _file_entry(root: Path, path: Path, *, label: str | None = None) -> dict:
    stat = path.stat()
    relative = _relative_path(root, path)
    return {
        "path": relative,
        "type": _infer_file_type(path, relative),
        "label": label or _infer_label(path, relative),
        "mime_type": _guess_mime_type(path),
        "size_bytes": stat.st_size,
        "sha256": _sha256(path),
    }


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _infer_file_type(path: Path, relative: str) -> str:
    if relative == RESULT_FILENAME:
        return "result"
    if relative == LOG_FILENAME:
        return "log"
    if relative.startswith("tables/"):
        return "table"
    if relative.startswith("figures/"):
        return "figure"
    if relative.startswith("reproducibility/"):
        return "reproducibility"
    if path.suffix.lower() == ".html":
        return "report"
    return "artifact"


def _infer_label(path: Path, relative: str) -> str:
    if relative in {RESULT_FILENAME, LOG_FILENAME, MANIFEST_FILENAME}:
        return path.stem
    return path.stem


def _guess_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "text/csv"
    if suffix == ".json":
        return "application/json"
    if suffix == ".txt":
        return "text/plain"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _is_json_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _is_json_scalar_list(value: Any) -> bool:
    return isinstance(value, list) and all(_is_json_scalar(item) for item in value)


def _normalize_for_log(path: str | Path) -> str:
    return str(path).replace("\\", "/")
