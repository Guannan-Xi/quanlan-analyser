from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
import importlib.util
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class BytesUpload:
    def __init__(self, filename: str, payload: bytes, content_type: str = "application/octet-stream"):
        self.filename = filename
        self.content_type = content_type
        self._payload = payload
        self._offset = 0
        self.read_sizes: list[int] = []

    async def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        if self._offset >= len(self._payload):
            return b""
        if size is None or size < 0:
            size = len(self._payload) - self._offset
        end = min(len(self._payload), self._offset + size)
        chunk = self._payload[self._offset:end]
        self._offset = end
        return chunk


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add_check(checks: list[dict[str, Any]], name: str, status: str, detail: str, **extra: Any) -> None:
    checks.append({"name": name, "status": status, "detail": detail, **extra})


ALIYUN_REQUIRED_ENV = [
    "QLANALYSER_ALIYUN_OSS_ENDPOINT",
    "QLANALYSER_ALIYUN_OSS_BUCKET",
    "QLANALYSER_ALIYUN_OSS_ACCESS_KEY_ID",
    "QLANALYSER_ALIYUN_OSS_ACCESS_KEY_SECRET",
]


def aliyun_prerequisites() -> dict[str, Any]:
    missing_env = [name for name in ALIYUN_REQUIRED_ENV if not os.getenv(name)]
    allow_write = os.getenv("QLANALYSER_ALIYUN_OSS_ALLOW_WRITE") == "1"
    oss2_available = importlib.util.find_spec("oss2") is not None
    lifecycle_path = os.getenv("QLANALYSER_ALIYUN_OSS_LIFECYCLE_POLICY_EVIDENCE", "").strip()
    lifecycle_exists = bool(lifecycle_path and Path(lifecycle_path).exists())
    return {
        "missing_env": missing_env,
        "allow_write": allow_write,
        "oss2_available": oss2_available,
        "lifecycle_evidence_path": lifecycle_path or None,
        "lifecycle_evidence_exists": lifecycle_exists,
        "ready_for_cloud_smoke": not missing_env and allow_write and oss2_available,
    }


def reload_storage(object_root: Path, storage_target: str):
    os.environ["QLANALYSER_OBJECT_ROOT"] = str(object_root)
    os.environ["QLANALYSER_UPLOAD_CHUNK_BYTES"] = str(8 * 1024)
    if storage_target == "local":
        os.environ["QLANALYSER_STORAGE_BACKEND"] = "local"
    elif storage_target == "aliyun":
        os.environ["QLANALYSER_STORAGE_BACKEND"] = "oss"

    import backend.services.object_storage_service as object_storage_service

    return importlib.reload(object_storage_service)


def run_boundary_smoke(object_storage_service, target: str, strict: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    payload = b"QLanalyser Alibaba Cloud storage contract evidence\n" * 32
    object_key = f"acceptance/aliyun-storage-contract/{target}-{utc_stamp()}/payload.bin"
    expected_hash = sha256_bytes(payload)

    upload = BytesUpload("payload.bin", payload)
    metadata = asyncio.run(object_storage_service.put_upload_file_stream(
        upload,
        object_key,
        metadata={"purpose": "aliyun-storage-contract", "target": target},
    ))
    add_check(
        checks,
        "put_stream",
        "pass",
        "put_upload_file_stream wrote the payload through the storage boundary.",
        size_bytes=metadata.get("size_bytes"),
        sha256=metadata.get("sha256"),
        max_read_size=max([size for size in upload.read_sizes if size and size > 0], default=0),
    )

    exists = object_storage_service.exists(object_key)
    add_check(checks, "exists", "pass" if exists else "fail", "exists(object_key) reflects the stored object.")

    stat = object_storage_service.stat(object_key)
    stat_ok = stat.get("size_bytes") == len(payload) and stat.get("sha256") == expected_hash
    add_check(
        checks,
        "stat_hash",
        "pass" if stat_ok else "fail",
        "stat(object_key) returns size and SHA-256 matching the written payload.",
        stat=stat,
        expected_sha256=expected_hash,
    )

    readable = object_storage_service.get_readable(object_key)
    read_payload = Path(readable).read_bytes()
    add_check(
        checks,
        "get_readable",
        "pass" if read_payload == payload else "fail",
        "get_readable(object_key) exposes bytes equal to the uploaded payload.",
        path=str(readable),
    )

    signed_url = object_storage_service.signed_download_url(object_key, expires_in=900)
    backend = stat.get("storage_backend")
    if backend in {"oss", "aliyun", "aliyun-oss"}:
        download_ok = isinstance(signed_url, str) and signed_url.startswith(("http://", "https://")) and object_key in signed_url
    else:
        download_ok = isinstance(signed_url, str) and object_key in signed_url and "expires_in=900" in signed_url
    add_check(
        checks,
        "signed_download_contract",
        "pass" if download_ok else "fail",
        "signed_download_url returns a deterministic download contract for the boundary.",
        signed_url=signed_url,
    )

    copied = object_storage_service.copy_to_tier(object_key, "warm")
    copied_stat = object_storage_service.stat(copied["object_key"])
    copied_ok = copied_stat.get("sha256") == expected_hash
    add_check(
        checks,
        "copy_to_tier",
        "pass" if copied_ok else "fail",
        "copy_to_tier can produce a warm-tier object with the same payload hash.",
        copy_result=copied,
        copied_stat=copied_stat,
    )

    deletion = object_storage_service.delete_or_mark_deleted(object_key)
    marker = deletion.get("deleted_marker")
    marker_object_key = deletion.get("deleted_marker_object_key")
    marker_ok = False
    if marker:
        marker_ok = bool(marker) and Path(marker).exists() and not object_storage_service.exists(object_key)
    elif marker_object_key:
        marker_ok = bool(marker_object_key) and object_storage_service.exists(marker_object_key) and not object_storage_service.exists(object_key)
    add_check(
        checks,
        "delete_or_mark_deleted",
        "pass" if marker_ok else "fail",
        "delete_or_mark_deleted removes the readable object and leaves a local marker.",
        delete_result=deletion,
    )

    prereqs = aliyun_prerequisites() if target == "aliyun" else {}
    if target == "aliyun":
        add_check(
            checks,
            "aliyun_oss_adapter",
            "pass" if backend in {"oss", "aliyun", "aliyun-oss"} else ("fail" if strict else "todo"),
            "Aliyun target must invoke the optional OSS adapter under explicit staging credentials before cloud readiness can be claimed.",
            required_env_placeholders=ALIYUN_REQUIRED_ENV,
            missing_env=prereqs.get("missing_env"),
            allow_write=prereqs.get("allow_write"),
            oss2_available=prereqs.get("oss2_available"),
            storage_backend_reported=backend,
        )
        lifecycle_ok = bool(prereqs.get("lifecycle_evidence_exists"))
        add_check(
            checks,
            "lifecycle_policy",
            "pass" if lifecycle_ok else ("fail" if strict else "todo"),
            "Provide exported staging OSS lifecycle policy evidence for warm/cold retention before cloud production readiness is claimed.",
            lifecycle_evidence_path=prereqs.get("lifecycle_evidence_path"),
        )
    else:
        add_check(
            checks,
            "lifecycle_policy",
            "todo",
            "Local storage can exercise tier-copy semantics, but real Alibaba Cloud OSS lifecycle policy evidence is a deployment gate.",
        )

    details = {
        "object_key": object_key,
        "expected_sha256": expected_hash,
        "storage_backend_reported": stat.get("storage_backend"),
        "object_root": str(object_storage_service.OBJECT_ROOT),
        "strict": strict,
    }
    return checks, details


def summarize(checks: list[dict[str, Any]]) -> str:
    if any(check["status"] == "fail" for check in checks):
        return "failed"
    if any(check["status"] == "todo" for check in checks):
        return "passed_with_todos"
    return "passed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate QLanalyser object-storage release contract evidence.")
    parser.add_argument("--target", choices=["local", "aliyun"], default="local")
    parser.add_argument("--evidence-dir", type=Path, default=ROOT / "work" / "acceptance")
    parser.add_argument("--strict", action="store_true", help="Fail on missing Aliyun OSS prerequisites for cloud target.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    evidence_dir = args.evidence_dir.resolve()
    evidence_path = evidence_dir / f"aliyun_storage_contract_{args.target}_{utc_stamp()}.json"
    prereqs = aliyun_prerequisites() if args.target == "aliyun" else {}
    storage_target = "aliyun" if args.target == "aliyun" and prereqs.get("ready_for_cloud_smoke") else "local"

    with tempfile.TemporaryDirectory(prefix="qlanalyser-storage-contract-") as tmp:
        object_storage_service = reload_storage(Path(tmp) / "objects", storage_target)
        checks, details = run_boundary_smoke(object_storage_service, args.target, strict=args.strict)

    status = summarize(checks)
    evidence = {
        "status": status,
        "target": args.target,
        "storage_target": storage_target,
        "strict": bool(args.strict),
        "aliyun_prerequisites": prereqs,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "script": str(Path(__file__).resolve()),
        "checks": checks,
        "details": details,
    }
    write_json(evidence_path, evidence)

    print(json.dumps({
        "status": status,
        "target": args.target,
        "storage_target": storage_target,
        "strict": bool(args.strict),
        "evidence_path": str(evidence_path),
        "passed": len([check for check in checks if check["status"] == "pass"]),
        "todos": len([check for check in checks if check["status"] == "todo"]),
        "failed": len([check for check in checks if check["status"] == "fail"]),
    }, ensure_ascii=False, indent=2))
    return 1 if status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
