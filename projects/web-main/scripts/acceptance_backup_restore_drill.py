from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


FIXED_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add_check(checks: list[dict[str, Any]], name: str, status: str, detail: str, **extra: Any) -> None:
    checks.append({"name": name, "status": status, "detail": detail, **extra})


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


def manifest_for(root: Path, label: str) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    entries: list[dict[str, Any]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        entries.append({
            "area": label,
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return entries


def manifest_index(entries: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(entry["area"], entry["path"]): entry for entry in entries}


def reload_state_store(state_root: Path):
    os.environ["QLANALYSER_STATE_ROOT"] = str(state_root)
    import backend.services.state_store as state_store

    return importlib.reload(state_store)


def seed_source_state(state_root: Path, object_root: Path) -> dict[str, Any]:
    state_store = reload_state_store(state_root)

    from backend.models.artifact import ArtifactRead
    from backend.models.eeg_file import EEGFileRead
    from backend.models.project import ProjectRead
    from backend.models.report import ReportRead

    upload_path = object_root / "uploads" / "backup-drill.edf"
    artifact_path = object_root / "artifacts" / "task_backup_drill" / "result.json"
    report_path = object_root / "reports" / "proj_backup_drill" / "report.html"
    package_path = object_root / "reports" / "proj_backup_drill" / "report.zip"

    upload_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(b"backup drill eeg bytes\n")
    artifact_path.write_text('{"status":"ok","module":"qc"}\n', encoding="utf-8")
    report_path.write_text("<html><body>backup drill report</body></html>\n", encoding="utf-8")
    package_path.write_bytes(b"backup drill package bytes\n")

    project = ProjectRead(
        id="proj_backup_drill",
        name="Backup restore drill project",
        organization_id="org_backup_drill",
        owner_user_id="user_backup_drill",
        quota_account_id="quota_backup_drill",
        created_at=FIXED_TIME,
        updated_at=FIXED_TIME,
    )
    eeg_file = EEGFileRead(
        id="eeg_backup_drill",
        organization_id=project.organization_id,
        project_id=project.id,
        original_filename="backup-drill.edf",
        stored_path=Path("uploads/backup-drill.edf"),
        detected_format="edf",
        object_key="uploads/backup-drill.edf",
        size_bytes=upload_path.stat().st_size,
        sha256=sha256_file(upload_path),
        content_type="application/octet-stream",
        owner_user_id=project.owner_user_id,
        quota_account_id=project.quota_account_id,
        created_at=FIXED_TIME,
        updated_at=FIXED_TIME,
    )
    artifact = ArtifactRead(
        id="artifact_backup_drill_result",
        task_id="task_backup_drill",
        organization_id=project.organization_id,
        project_id=project.id,
        input_file_id=eeg_file.id,
        artifact_type="result",
        label="result",
        path=Path("artifacts/task_backup_drill/result.json"),
        object_key="artifacts/task_backup_drill/result.json",
        size_bytes=artifact_path.stat().st_size,
        sha256=sha256_file(artifact_path),
        created_at=FIXED_TIME,
        mime_type="application/json",
    )
    report = ReportRead(
        id="report_backup_drill",
        organization_id=project.organization_id,
        project_id=project.id,
        task_id=artifact.task_id,
        title="Backup restore drill report",
        owner_user_id=project.owner_user_id,
        html_path=Path("reports/proj_backup_drill/report.html"),
        package_path=Path("reports/proj_backup_drill/report.zip"),
        html_object_key="reports/proj_backup_drill/report.html",
        package_object_key="reports/proj_backup_drill/report.zip",
        size_bytes=package_path.stat().st_size,
        sha256=sha256_file(package_path),
        created_at=FIXED_TIME,
        updated_at=FIXED_TIME,
    )

    state_store.upsert_item("projects", project)
    state_store.upsert_item("eeg_files", eeg_file)
    state_store.upsert_item("artifacts", artifact)
    state_store.upsert_item("reports", report)

    return {
        "project_id": project.id,
        "eeg_file_id": eeg_file.id,
        "artifact_id": artifact.id,
        "report_id": report.id,
    }


def export_backup(source_state: Path, source_objects: Path, export_root: Path) -> list[dict[str, Any]]:
    copy_tree_contents(source_state, export_root / "state")
    copy_tree_contents(source_objects, export_root / "objects")
    entries = manifest_for(export_root / "state", "state") + manifest_for(export_root / "objects", "objects")
    write_json(export_root / "manifest.json", {
        "schema": "qlanalyser-backup-manifest-v0.1",
        "generated_at": FIXED_TIME.isoformat(),
        "entries": entries,
    })
    return entries


def restore_backup(export_root: Path, restore_state: Path, restore_objects: Path) -> None:
    copy_tree_contents(export_root / "state", restore_state)
    copy_tree_contents(export_root / "objects", restore_objects)


def verify_restored_state(restore_state: Path) -> dict[str, int]:
    state_store = reload_state_store(restore_state)

    from backend.models.artifact import ArtifactRead
    from backend.models.eeg_file import EEGFileRead
    from backend.models.project import ProjectRead
    from backend.models.report import ReportRead

    projects = state_store.load_registry("projects", ProjectRead)
    eeg_files = state_store.load_registry("eeg_files", EEGFileRead)
    artifacts = state_store.load_registry("artifacts", ArtifactRead)
    reports = state_store.load_registry("reports", ReportRead)
    return {
        "projects": len(projects),
        "eeg_files": len(eeg_files),
        "artifacts": len(artifacts),
        "reports": len(reports),
    }


def run_local_drill(work_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    source_state = work_root / "source" / "state"
    source_objects = work_root / "source" / "objects"
    export_root = work_root / "backup-export"
    restore_state = work_root / "restore" / "state"
    restore_objects = work_root / "restore" / "objects"

    seed = seed_source_state(source_state, source_objects)
    source_entries = manifest_for(source_state, "state") + manifest_for(source_objects, "objects")
    add_check(
        checks,
        "seed_state_and_artifacts",
        "pass" if len(source_entries) >= 7 else "fail",
        "Seeded isolated state registries plus upload, artifact, report, and package files.",
        seed=seed,
        source_file_count=len(source_entries),
    )

    export_entries = export_backup(source_state, source_objects, export_root)
    manifest_path = export_root / "manifest.json"
    add_check(
        checks,
        "export_manifest",
        "pass" if manifest_path.exists() and export_entries else "fail",
        "Export wrote state/object copies and a manifest with size/hash entries.",
        manifest_path=str(manifest_path),
        manifest_schema="qlanalyser-backup-manifest-v0.1",
        manifest_entries=len(export_entries),
    )

    restore_backup(export_root, restore_state, restore_objects)
    restored_entries = manifest_for(restore_state, "state") + manifest_for(restore_objects, "objects")
    source_index = manifest_index(export_entries)
    restored_index = manifest_index(restored_entries)
    hashes_match = source_index == restored_index
    add_check(
        checks,
        "restore_hashes",
        "pass" if hashes_match else "fail",
        "Restored state/object files match exported manifest paths, sizes, and SHA-256 values.",
        restored_entries=len(restored_entries),
    )

    counts = verify_restored_state(restore_state)
    counts_ok = counts == {"projects": 1, "eeg_files": 1, "artifacts": 1, "reports": 1}
    add_check(
        checks,
        "restore_state_validation",
        "pass" if counts_ok else "fail",
        "Restored JSON registries validate through existing pydantic models.",
        registry_counts=counts,
    )

    return checks, {
        "work_root": str(work_root),
        "export_manifest_path": str(manifest_path),
        "export_manifest_entries": export_entries,
        "restored_manifest_entries": restored_entries,
        "seed": seed,
    }


def summarize(checks: list[dict[str, Any]]) -> str:
    if any(check["status"] == "fail" for check in checks):
        return "failed"
    if any(check["status"] == "todo" for check in checks):
        return "passed_with_todos"
    return "passed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a safe backup/restore evidence drill.")
    parser.add_argument("--target", choices=["local", "aliyun"], default="local")
    parser.add_argument("--evidence-dir", type=Path, default=ROOT / "work" / "acceptance")
    parser.add_argument("--strict", action="store_true", help="Fail on hard missing cloud prerequisites for Aliyun target.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    evidence_dir = args.evidence_dir.resolve()
    evidence_path = evidence_dir / f"backup_restore_drill_{args.target}_{utc_stamp()}.json"

    with tempfile.TemporaryDirectory(prefix="qlanalyser-backup-restore-") as tmp:
        checks, details = run_local_drill(Path(tmp))

    backup_service_spec = importlib.util.find_spec("backend.services.backup_service")
    if backup_service_spec is None:
        add_check(
            checks,
            "backup_restore_api",
            "fail" if args.strict and args.target == "aliyun" else "todo",
            "No backend.services.backup_service module exists yet; drill uses deterministic state/object manifest export-import.",
        )
    else:
        backup_service = importlib.import_module("backend.services.backup_service")
        required_api = ["export_backup", "restore_backup", "manifest_for", "MANIFEST_SCHEMA"]
        missing_api = [name for name in required_api if not hasattr(backup_service, name)]
        add_check(
            checks,
            "backup_restore_api",
            "fail" if missing_api else "pass",
            "backend.services.backup_service exposes the manifest export/restore API used by the local drill.",
            missing_api=missing_api,
            required_api=required_api,
            manifest_schema=getattr(backup_service, "MANIFEST_SCHEMA", None),
        )

    if args.target == "aliyun":
        required_placeholders = [
            "QLANALYSER_ALIYUN_OSS_BUCKET",
            "QLANALYSER_ALIYUN_BACKUP_BUCKET",
            "QLANALYSER_ALIYUN_BACKUP_PREFIX",
        ]
        missing = [name for name in required_placeholders if not os.getenv(name)]
        add_check(
            checks,
            "aliyun_backup_target_placeholders",
            "fail" if args.strict and missing else "todo",
            "Aliyun backup target is recorded as placeholders only; no external write was attempted.",
            missing_env=missing,
            required_env_placeholders=required_placeholders,
        )
        add_check(
            checks,
            "aliyun_restore_rehearsal",
            "todo",
            "Run against an isolated staging OSS bucket once the backup service and deployment credentials are available.",
        )

    status = summarize(checks)
    evidence = {
        "status": status,
        "target": args.target,
        "strict": bool(args.strict),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "script": str(Path(__file__).resolve()),
        "checks": checks,
        "details": details,
    }
    write_json(evidence_path, evidence)

    print(json.dumps({
        "status": status,
        "target": args.target,
        "strict": bool(args.strict),
        "evidence_path": str(evidence_path),
        "passed": len([check for check in checks if check["status"] == "pass"]),
        "todos": len([check for check in checks if check["status"] == "todo"]),
        "failed": len([check for check in checks if check["status"] == "fail"]),
    }, ensure_ascii=False, indent=2))
    return 1 if status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
