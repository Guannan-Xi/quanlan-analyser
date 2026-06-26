from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "work" / "release_evidence" / "20260620-v01-sanitized-review"
DEFAULT_ZIP = ROOT / "work" / "release_evidence" / "20260620-v01-sanitized-review.zip"
DEFAULT_MANIFEST = ROOT / "work" / "release_evidence" / "20260620-v01-sanitized-review-package.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Package sanitized QLanalyser V01 review evidence as a portable ZIP.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output-zip", default=str(DEFAULT_ZIP))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    args = parser.parse_args()

    source = Path(args.source)
    output_zip = Path(args.output_zip)
    manifest_path = Path(args.manifest)
    if not source.is_dir():
        raise SystemExit(f"Sanitized source directory not found: {source}")

    files = sorted(path for path in source.rglob("*") if path.is_file())
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    temp_zip = output_zip.with_name(f".{output_zip.name}.{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}.tmp")
    with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(source.parent).as_posix())
    existing_zip_locked = False
    fresh_package_written = True
    try:
        temp_zip.replace(output_zip)
    except PermissionError:
        existing_zip_locked = True
        fresh_package_written = False
        temp_zip.unlink(missing_ok=True)
        if not output_zip.exists():
            raise

    manifest = {
        "status": "passed",
        "generated_at": utc_now(),
        "source_dir": str(source),
        "zip_path": str(output_zip),
        "zip_bytes": output_zip.stat().st_size,
        "zip_sha256": sha256_file(output_zip),
        "file_count": len(files),
        "fresh_package_written": fresh_package_written,
        "existing_zip_locked": existing_zip_locked,
        "policy": "External-readable sanitized review package. Screenshots are excluded unless the source directory was generated with screenshot inclusion.",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
