from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MANIFEST_SCHEMA = "qlanalyser-backup-manifest-v0.1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_tree_contents(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        return
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def manifest_for(root: Path, area: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not root.exists():
        return entries
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        entries.append({
            "area": area,
            "path": relative,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return entries


def manifest_index(entries: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(entry["area"], entry["path"]): entry for entry in entries}


def export_backup(source_state_root: Path, source_object_root: Path, export_root: Path) -> dict[str, Any]:
    state_root = export_root / "state"
    object_root = export_root / "objects"
    copy_tree_contents(source_state_root, state_root)
    copy_tree_contents(source_object_root, object_root)
    entries = manifest_for(state_root, "state") + manifest_for(object_root, "objects")
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }
    export_root.mkdir(parents=True, exist_ok=True)
    (export_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def restore_backup(export_root: Path, restore_state_root: Path, restore_object_root: Path, verify_hashes: bool = True) -> dict[str, Any]:
    manifest_path = export_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError(f"Unsupported backup manifest schema: {manifest.get('schema')}")

    copy_tree_contents(export_root / "state", restore_state_root)
    copy_tree_contents(export_root / "objects", restore_object_root)

    restored_entries = manifest_for(restore_state_root, "state") + manifest_for(restore_object_root, "objects")
    if verify_hashes:
        expected = manifest_index(manifest.get("entries", []))
        actual = manifest_index(restored_entries)
        if expected != actual:
            raise ValueError("Restored backup hash manifest does not match exported manifest")

    return {
        "schema": MANIFEST_SCHEMA,
        "restored_entries": restored_entries,
        "entry_count": len(restored_entries),
    }
