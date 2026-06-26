from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import HTTPException, UploadFile

ROOT = Path(__file__).resolve().parents[2]
OBJECT_ROOT = Path(os.getenv("QLANALYSER_OBJECT_ROOT", ROOT / "data"))
DEFAULT_UPLOAD_CHUNK_BYTES = int(os.getenv("QLANALYSER_UPLOAD_CHUNK_BYTES", str(8 * 1024 * 1024)))
STORAGE_BACKEND = os.getenv("QLANALYSER_STORAGE_BACKEND", "local").strip().lower()
OSS_BACKEND_NAMES = {"oss", "aliyun", "aliyun-oss"}
OSS_CACHE_ROOT = Path(os.getenv("QLANALYSER_OBJECT_CACHE_ROOT", OBJECT_ROOT / ".oss-cache"))
OSS_UPLOAD_TMP_ROOT = Path(os.getenv("QLANALYSER_OBJECT_UPLOAD_TMP_ROOT", OBJECT_ROOT / ".oss-uploading"))


def _safe_object_key(object_key: str) -> str:
    normalized = object_key.replace("\\", "/").strip("/")
    parts = [part for part in normalized.split("/") if part]
    if not parts or any(part in {".", ".."} for part in parts):
        raise HTTPException(status_code=422, detail="Invalid object key")
    return "/".join(parts)


def _uses_oss() -> bool:
    return STORAGE_BACKEND in OSS_BACKEND_NAMES


def local_path_for_object_key(object_key: str) -> Path:
    safe_key = _safe_object_key(object_key)
    return OBJECT_ROOT / safe_key


def _oss_module():
    try:
        import oss2  # type: ignore
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Alibaba Cloud OSS backend requires optional dependency oss2.",
        ) from exc
    return oss2


def _oss_env() -> dict[str, str]:
    required = {
        "endpoint": os.getenv("QLANALYSER_ALIYUN_OSS_ENDPOINT", "").strip(),
        "bucket": os.getenv("QLANALYSER_ALIYUN_OSS_BUCKET", "").strip(),
        "access_key_id": os.getenv("QLANALYSER_ALIYUN_OSS_ACCESS_KEY_ID", "").strip(),
        "access_key_secret": os.getenv("QLANALYSER_ALIYUN_OSS_ACCESS_KEY_SECRET", "").strip(),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Alibaba Cloud OSS backend is missing required settings: {', '.join(missing)}",
        )
    return required


def _oss_bucket():
    oss2 = _oss_module()
    env = _oss_env()
    auth = oss2.Auth(env["access_key_id"], env["access_key_secret"])
    return oss2.Bucket(auth, env["endpoint"], env["bucket"])


def _oss_bucket_name() -> str:
    return _oss_env()["bucket"]


def _oss_object_key(object_key: str) -> str:
    safe_key = _safe_object_key(object_key)
    prefix = os.getenv("QLANALYSER_ALIYUN_OSS_PREFIX", "").replace("\\", "/").strip("/")
    return f"{prefix}/{safe_key}" if prefix else safe_key


def _oss_cache_path(object_key: str) -> Path:
    return OSS_CACHE_ROOT / _safe_object_key(object_key)


def _header_get(headers: Any, name: str) -> str | None:
    if not headers:
        return None
    if hasattr(headers, "get"):
        value = headers.get(name) or headers.get(name.lower()) or headers.get(name.upper())
        if value is not None:
            return str(value)
    lowered = name.lower()
    for key, value in dict(headers).items():
        if str(key).lower() == lowered:
            return str(value)
    return None


def _metadata_headers(metadata: dict | None, sha256: str) -> dict[str, str]:
    headers = {"x-oss-meta-sha256": sha256}
    if metadata:
        for key, value in metadata.items():
            normalized = str(key).lower().replace("_", "-")
            if normalized.startswith("x-oss-meta-"):
                header_name = normalized
            else:
                header_name = f"x-oss-meta-{normalized}"
            headers[header_name] = str(value)
    return headers


async def put_upload_file_stream(upload: UploadFile, object_key: str, metadata: dict | None = None) -> dict:
    """Persist an UploadFile in chunks and return object metadata."""
    safe_key = _safe_object_key(object_key)
    if _uses_oss():
        return await _put_upload_file_stream_oss(upload, safe_key, metadata)
    return await _put_upload_file_stream_local(upload, safe_key, metadata)


async def _put_upload_file_stream_local(upload: UploadFile, object_key: str, metadata: dict | None = None) -> dict:
    target = local_path_for_object_key(object_key)
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size_bytes = 0
    tmp_path: Path | None = None

    try:
        with NamedTemporaryFile(delete=False, dir=target.parent, prefix=f".{target.name}.", suffix=".uploading") as tmp:
            tmp_path = Path(tmp.name)
            while True:
                chunk = await upload.read(DEFAULT_UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                size_bytes += len(chunk)
                digest.update(chunk)
                tmp.write(chunk)
        if size_bytes <= 0:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()
            raise HTTPException(status_code=422, detail="Uploaded EEG file is empty")
        os.replace(tmp_path, target)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive IO boundary
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Upload stream failed: {exc}") from exc

    stat_result = target.stat()
    return {
        "object_key": object_key,
        "path": str(target),
        "size_bytes": size_bytes,
        "sha256": digest.hexdigest(),
        "storage_backend": STORAGE_BACKEND,
        "metadata": metadata or {},
        "modified_at": stat_result.st_mtime,
    }


async def _put_upload_file_stream_oss(upload: UploadFile, object_key: str, metadata: dict | None = None) -> dict:
    target_key = _oss_object_key(object_key)
    OSS_UPLOAD_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size_bytes = 0
    tmp_path: Path | None = None

    try:
        with NamedTemporaryFile(delete=False, dir=OSS_UPLOAD_TMP_ROOT, prefix="oss-", suffix=".uploading") as tmp:
            tmp_path = Path(tmp.name)
            while True:
                chunk = await upload.read(DEFAULT_UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                size_bytes += len(chunk)
                digest.update(chunk)
                tmp.write(chunk)
        if size_bytes <= 0:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()
            raise HTTPException(status_code=422, detail="Uploaded EEG file is empty")

        sha256 = digest.hexdigest()
        headers = _metadata_headers(metadata, sha256)
        content_type = getattr(upload, "content_type", None)
        if content_type:
            headers["Content-Type"] = str(content_type)
        _oss_bucket().put_object_from_file(target_key, str(tmp_path), headers=headers)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - requires cloud credentials
        raise HTTPException(status_code=502, detail=f"OSS upload failed: {exc}") from exc
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    return {
        "object_key": object_key,
        "oss_key": target_key,
        "size_bytes": size_bytes,
        "sha256": digest.hexdigest(),
        "storage_backend": STORAGE_BACKEND,
        "metadata": metadata or {},
        "modified_at": datetime.now(timezone.utc).isoformat(),
    }


def exists(object_key: str) -> bool:
    if _uses_oss():
        try:
            return bool(_oss_bucket().object_exists(_oss_object_key(object_key)))
        except Exception:
            return False
    path = local_path_for_object_key(object_key)
    return path.exists() and not path.name.endswith(".deleted")


def get_readable(object_key: str) -> Path:
    if _uses_oss():
        safe_key = _safe_object_key(object_key)
        target = _oss_cache_path(safe_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            _oss_bucket().get_object_to_file(_oss_object_key(safe_key), str(target))
        except Exception as exc:  # pragma: no cover - requires cloud credentials
            raise HTTPException(status_code=410, detail=f"Object is not available from OSS: {exc}") from exc
        return target

    path = local_path_for_object_key(object_key)
    if not path.exists() or path.name.endswith(".deleted"):
        raise HTTPException(status_code=410, detail="Object is not available")
    return path


def stat(object_key: str) -> dict:
    safe_key = _safe_object_key(object_key)
    if _uses_oss():
        oss_key = _oss_object_key(safe_key)
        try:
            head = _oss_bucket().head_object(oss_key)
        except Exception as exc:  # pragma: no cover - requires cloud credentials
            raise HTTPException(status_code=410, detail=f"Object is not available from OSS: {exc}") from exc
        headers = getattr(head, "headers", {}) or {}
        size_bytes = int(_header_get(headers, "Content-Length") or 0)
        sha256 = _header_get(headers, "x-oss-meta-sha256")
        return {
            "object_key": safe_key,
            "oss_key": oss_key,
            "path": None,
            "size_bytes": size_bytes,
            "sha256": sha256,
            "storage_backend": STORAGE_BACKEND,
            "modified_at": _header_get(headers, "Last-Modified"),
        }

    path = get_readable(safe_key)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    info = path.stat()
    return {
        "object_key": safe_key,
        "path": str(path),
        "size_bytes": info.st_size,
        "sha256": digest.hexdigest(),
        "storage_backend": STORAGE_BACKEND,
        "modified_at": info.st_mtime,
    }


def signed_download_url(object_key: str, expires_in: int = 3600) -> str:
    safe_key = _safe_object_key(object_key)
    if _uses_oss():
        try:
            return str(_oss_bucket().sign_url("GET", _oss_object_key(safe_key), expires_in))
        except Exception as exc:  # pragma: no cover - requires cloud credentials
            raise HTTPException(status_code=502, detail=f"OSS signed URL failed: {exc}") from exc
    get_readable(safe_key)
    return f"/api/files/download?object_key={safe_key}&expires_in={expires_in}"


def copy_to_tier(object_key: str, tier: str) -> dict:
    safe_key = _safe_object_key(object_key)
    tier_key = _safe_object_key(tier)
    target_key = f"{tier_key}/{safe_key}"
    if _uses_oss():
        try:
            _oss_bucket().copy_object(_oss_bucket_name(), _oss_object_key(safe_key), _oss_object_key(target_key))
        except Exception as exc:  # pragma: no cover - requires cloud credentials
            raise HTTPException(status_code=502, detail=f"OSS tier copy failed: {exc}") from exc
        return {
            "object_key": target_key,
            "oss_key": _oss_object_key(target_key),
            "storage_tier": tier_key,
            "storage_backend": STORAGE_BACKEND,
        }

    source = get_readable(safe_key)
    target = local_path_for_object_key(target_key)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return {"object_key": target_key, "storage_tier": tier_key, "path": str(target)}


def delete_or_mark_deleted(object_key: str) -> dict:
    safe_key = _safe_object_key(object_key)
    if _uses_oss():
        marker_key = f"deleted/{safe_key}.deleted"
        marker_payload = json.dumps(
            {
                "object_key": safe_key,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
                "storage_backend": STORAGE_BACKEND,
            },
            ensure_ascii=True,
        ).encode("utf-8")
        try:
            bucket = _oss_bucket()
            bucket.delete_object(_oss_object_key(safe_key))
            bucket.put_object(_oss_object_key(marker_key), marker_payload)
        except Exception as exc:  # pragma: no cover - requires cloud credentials
            raise HTTPException(status_code=502, detail=f"OSS delete marker failed: {exc}") from exc
        return {
            "object_key": safe_key,
            "deleted_marker_object_key": marker_key,
            "deleted_marker_oss_key": _oss_object_key(marker_key),
            "storage_backend": STORAGE_BACKEND,
        }

    path = get_readable(safe_key)
    tombstone = path.with_suffix(path.suffix + ".deleted")
    os.replace(path, tombstone)
    return {"object_key": safe_key, "deleted_marker": str(tombstone)}
