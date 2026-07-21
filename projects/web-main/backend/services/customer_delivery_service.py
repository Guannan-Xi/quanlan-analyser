from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.models.artifact import ArtifactRead


ROOT = Path(__file__).resolve().parents[2]
DERIVATIVES_ROOT = (ROOT / "data" / "derivatives").resolve()
CUSTOMER_SAFE_ROOT = ROOT / "data" / "customer_safe_downloads"
TEXT_SUFFIXES = {".json", ".txt", ".log", ".csv", ".tsv", ".md", ".html", ".xml", ".yaml", ".yml"}
WINDOWS_PATH_RE = re.compile(r"(?i)([a-z]:[\\/][^\s\"'<>),;]+)")
INTERNAL_METADATA_KEYS = {
    "absolute_path",
    "artifact_root",
    "audit_json_path",
    "channels_tsv_path",
    "edf_path",
    "events_tsv_path",
    "file_path",
    "html_path",
    "local_path",
    "package_path",
    "path",
    "repo_path",
    "root_dir",
    "source_integrity_path",
    "stored_path",
    "ui_evidence_path",
}


def assert_path_within_derivatives(raw_path: Path) -> Path:
    resolved = raw_path.resolve()
    try:
        resolved.relative_to(DERIVATIVES_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Artifact path is outside the allowed directory") from exc
    return resolved


def assert_customer_artifact_file(artifact: ArtifactRead | dict, task: Any, task_service_module) -> Path:
    if not task_service_module.is_artifact_download_allowed(artifact, task):
        raise HTTPException(status_code=403, detail="Artifact is not available for customer download")
    raw_path = Path(str(artifact.path if hasattr(artifact, "path") else artifact.get("path", "")))
    path = assert_path_within_derivatives(raw_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=410, detail="Artifact file is not available on disk")
    return path


def safe_archive_name(label: str | None, path: Path) -> str:
    raw = (label or path.name).replace("/", "_").replace("\\", "_").strip() or path.name
    if not raw.endswith(path.suffix):
        raw += path.suffix
    return raw


def customer_safe_file(path: Path, *, archive_name: str | None = None) -> Path:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return path
    safe_text = _customer_safe_text(path.read_text(encoding="utf-8", errors="replace"), path.suffix.lower())
    digest_key = hashlib.sha256(f"{path.resolve()}:{path.stat().st_mtime_ns}:{archive_name or path.name}".encode("utf-8")).hexdigest()[:16]
    target = CUSTOMER_SAFE_ROOT / digest_key / (archive_name or path.name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(safe_text, encoding="utf-8")
    return target


def customer_safe_bytes(path: Path) -> bytes:
    safe_path = customer_safe_file(path)
    return safe_path.read_bytes()


def _customer_safe_text(text: str, suffix: str) -> str:
    if suffix == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return _redact_text(text)
        return json.dumps(_redact_payload(payload), ensure_ascii=False, indent=2)
    return _redact_text(text)


def _redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _redact_payload(item)
            for key, item in value.items()
            if str(key).lower() not in INTERNAL_METADATA_KEYS
        }
    if isinstance(value, list):
        return [_redact_payload(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _redact_text(text: str) -> str:
    normalized_roots = [
        str(ROOT).replace("\\", "/"),
        str(ROOT.parent).replace("\\", "/"),
        str(DERIVATIVES_ROOT).replace("\\", "/"),
        "C:/Users/",
        "D:/Quanlan/",
    ]

    def redact_token(match: re.Match[str]) -> str:
        raw = match.group(1)
        normalized = raw.replace("\\", "/")
        for root in normalized_roots:
            if normalized.startswith(root):
                return "package-relative:[redacted-path]"
        if normalized.startswith("D:/") or normalized.startswith("C:/"):
            return "package-relative:[redacted-path]"
        return raw

    redacted = WINDOWS_PATH_RE.sub(redact_token, text)
    redacted = re.sub(r"(?i)quanlan-analyser[^\s\"'<>),;]*", "[redacted-repo]", redacted)
    redacted = re.sub(r"(?i)\b127\.0\.0\.1\b", "[local-service]", redacted)
    redacted = re.sub(r"(?i)\blocalhost\b", "[local-service]", redacted)
    redacted = redacted.replace("Traceback (most recent call last)", "[internal-error-redacted]")
    return redacted
