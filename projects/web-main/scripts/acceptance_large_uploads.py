import argparse
import asyncio
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ChunkedUpload:
    def __init__(self, filename: str, total_bytes: int, byte: bytes = b"e"):
        self.filename = filename
        self.content_type = "application/octet-stream"
        self.total_bytes = total_bytes
        self.sent = 0
        self.read_sizes: list[int] = []
        self.byte = byte

    async def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        if self.sent >= self.total_bytes:
            return b""
        if size is None or size < 0:
            size = self.total_bytes - self.sent
        length = min(size, self.total_bytes - self.sent)
        self.sent += length
        return self.byte * length


def _reload_for_isolated_state(root: Path, chunk_bytes: int) -> tuple:
    os.environ["QLANALYSER_STATE_ROOT"] = str(root / "state")
    os.environ["QLANALYSER_OBJECT_ROOT"] = str(root / "objects")
    os.environ["QLANALYSER_UPLOAD_CHUNK_BYTES"] = str(chunk_bytes)

    import backend.services.state_store as state_store
    import backend.services.object_storage_service as object_storage_service
    import backend.services.storage_service as storage_service
    import backend.services.audit_service as audit_service
    import backend.services.quota_service as quota_service

    for module in (state_store, object_storage_service, storage_service, audit_service, quota_service):
        importlib.reload(module)
    return state_store, object_storage_service, storage_service, audit_service, quota_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate streaming upload contract for large EEG uploads.")
    parser.add_argument("--users", type=int, default=3)
    parser.add_argument("--min-mb", type=int, default=200)
    parser.add_argument("--max-mb", type=int, default=1024)
    parser.add_argument(
        "--actual-mb-cap",
        type=int,
        default=8,
        help="Actual bytes written per upload in smoke mode. Set >= max-mb for real capacity evidence.",
    )
    parser.add_argument("--chunk-kb", type=int, default=64)
    parser.add_argument(
        "--evidence-path",
        type=Path,
        default=Path(os.getenv("QLANALYSER_LARGE_UPLOAD_EVIDENCE_PATH")) if os.getenv("QLANALYSER_LARGE_UPLOAD_EVIDENCE_PATH") else None,
    )
    args = parser.parse_args()

    actual_mb = min(args.max_mb, max(1, args.actual_mb_cap))
    actual_bytes = actual_mb * 1024 * 1024
    chunk_bytes = args.chunk_kb * 1024
    mode = "real_capacity" if args.actual_mb_cap >= args.max_mb else "streaming_contract_smoke"
    note = (
        "Real capacity evidence: actual bytes per upload reached the configured max-mb target."
        if mode == "real_capacity"
        else "Run with --actual-mb-cap >= --max-mb for real 200MB-1GB capacity evidence."
    )

    with tempfile.TemporaryDirectory(prefix="qlanalyser-large-upload-") as tmp:
        root = Path(tmp)
        state_store, object_storage_service, storage_service, audit_service, quota_service = _reload_for_isolated_state(root, chunk_bytes)
        import backend.models.project as project_model

        project = storage_service.create_project(project_model.ProjectCreate(name="Large upload acceptance"))
        files = []
        max_read = 0
        for idx in range(args.users):
            upload = ChunkedUpload(f"large_{idx}.edf", actual_bytes, byte=bytes([65 + (idx % 26)]))
            eeg_file = asyncio.run(storage_service.create_eeg_file(project.id, None, upload))
            max_read = max(max_read, *(size for size in upload.read_sizes if size and size > 0))
            assert eeg_file.size_bytes == actual_bytes
            assert eeg_file.sha256
            assert eeg_file.object_key
            assert object_storage_service.exists(eeg_file.object_key)
            assert max(size for size in upload.read_sizes if size and size > 0) <= chunk_bytes
            files.append(eeg_file.id)

        audit_events = state_store.load_registry("audit_events", audit_service.AuditEventRead)
        usage_records = state_store.load_registry("usage_records", quota_service.UsageRecordRead)
        assert len([event for event in audit_events.values() if event.action == "eeg_file.uploaded"]) == args.users
        assert len([record for record in usage_records.values() if record.resource_type == "storage_bytes_hot"]) == args.users

        payload = {
            "status": "passed",
            "mode": mode,
            "users": args.users,
            "target_min_mb": args.min_mb,
            "target_max_mb": args.max_mb,
            "actual_mb_per_upload": actual_mb,
            "chunk_kb": args.chunk_kb,
            "max_read_bytes": max_read,
            "files": files,
            "note": note,
        }
        if args.evidence_path:
            args.evidence_path.parent.mkdir(parents=True, exist_ok=True)
            args.evidence_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            payload["evidence_path"] = str(args.evidence_path)
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
