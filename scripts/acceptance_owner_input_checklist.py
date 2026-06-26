from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "aliyun_staging_preflight.json"
CHECKLIST = ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "owner_input_checklist.md"
MANIFEST = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "evidence_manifest.json"


REQUIRED_SECTIONS = [
    "deepseek_copy_gate",
    "oss_required_env",
    "oss_storage_backend",
    "oss_allow_write",
    "oss_lifecycle_evidence",
    "oss2_dependency",
    "backup_required_env",
    "deploy_origin_env",
    "provider_boundary_env",
]


def main() -> int:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    checklist = CHECKLIST.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    todo_checks = [check for check in preflight.get("checks", []) if check.get("status") == "todo"]
    todo_names = {str(check.get("name")) for check in todo_checks}
    expected_sections = [name for name in REQUIRED_SECTIONS if name in todo_names]
    unexpected_sections = [name for name in REQUIRED_SECTIONS if name not in todo_names and f"### {name}" in checklist]
    missing_sections = [name for name in expected_sections if f"### {name}" not in checklist]
    missing_commands = [command for command in preflight.get("next_commands", []) if command not in checklist]

    manifest_paths = {item.get("path") for item in manifest.get("evidence", [])}
    manifest_release = manifest.get("release_readiness_evidence", {})
    manifest_paths.update(str(value) for value in manifest_release.values() if isinstance(value, str))
    manifest_missing = [
        str(PREFLIGHT),
        str(CHECKLIST),
    ]
    manifest_missing = [
        path for path in manifest_missing
        if path not in manifest_paths and str(Path(path).relative_to(ROOT)) not in manifest_paths
    ]

    status = "passed" if (
        preflight.get("status") == "blocked_missing_prerequisites"
        and todo_names.issubset(set(REQUIRED_SECTIONS))
        and not missing_sections
        and not unexpected_sections
        and not missing_commands
        and not manifest_missing
    ) else "failed"

    result = {
        "status": status,
        "preflight_status": preflight.get("status"),
        "todo_count": len(todo_checks),
        "required_sections": REQUIRED_SECTIONS,
        "expected_sections": expected_sections,
        "missing_sections": missing_sections,
        "unexpected_sections": unexpected_sections,
        "missing_commands": missing_commands,
        "manifest_missing": manifest_missing,
        "checklist": str(CHECKLIST),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
