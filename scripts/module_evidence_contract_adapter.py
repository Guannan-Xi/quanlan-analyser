from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_OUTPUTS = {"parameters", "method_description", "result", "manifest", "log"}
DEFAULT_EXCLUDE_PARTS = {"20260620-v01-sanitized-review"}


def read_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if "\ufffd" in text:
        raise ValueError(f"replacement character found in {path}")
    return json.loads(text)


def should_skip(path: Path) -> bool:
    return any(part in DEFAULT_EXCLUDE_PARTS for part in path.parts)


def discover_evidence_files(release_root: Path) -> list[Path]:
    candidates = sorted(release_root.rglob("acceptance_*module*.json"))
    return [path for path in candidates if not should_skip(path)]


def normalize_module(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    checked_outputs = set(payload.get("checked_outputs") or [])
    missing_outputs = sorted(REQUIRED_OUTPUTS - checked_outputs)
    module_id = payload.get("module") or payload.get("module_id") or path.stem
    workflow = payload.get("workflow") or module_id
    boundary = payload.get("boundary") or payload.get("acceptance_boundary")
    return {
        "module_id": module_id,
        "workflow": workflow,
        "lifecycle_state": payload.get("lifecycle_state") or "acceptance_evidence_only",
        "task_id": payload.get("task_id"),
        "task_status": payload.get("task_status") or payload.get("status"),
        "artifact_count": payload.get("artifact_count"),
        "checked_outputs": sorted(checked_outputs),
        "missing_outputs": missing_outputs,
        "method_description_present": "method_description" in checked_outputs,
        "parameters_present": "parameters" in checked_outputs,
        "manifest_present": "manifest" in checked_outputs,
        "result_present": "result" in checked_outputs,
        "log_present": "log" in checked_outputs,
        "scientific_boundary_present": bool(boundary),
        "scientific_boundary": boundary,
        "report_mapping_present": bool(payload.get("report_mapping_present")),
        "pass_fail_status": payload.get("status", "unknown"),
        "source_evidence_path": str(path),
        "runner_output": payload.get("runner_output"),
        "source_failures": payload.get("failures") or [],
    }


def build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Module Evidence Contract Adapter",
        "",
        f"status: {result['status']}",
        f"adapter_id: {result['adapter_id']}",
        "consumer: 07 QLanalyser Product / 12 Method Center",
        "",
        "## Release Boundary",
        "",
        f"- release_status: {result['release_boundary']['release_status']}",
        f"- local_sandbox_review_ready: {result['release_boundary']['local_sandbox_review_ready']}",
        f"- public_ecs_sandbox_review_ready: {result['release_boundary']['public_ecs_sandbox_review_ready']}",
        f"- public_cloud_ready: {result['release_boundary']['public_cloud_ready']}",
        f"- blocked_release_claims: {', '.join(result['blocked_release_claims'])}",
        "",
        "## Normalized Modules",
        "",
    ]
    for module in result["normalized_modules"]:
        missing = ", ".join(module["missing_outputs"]) or "none"
        boundary = module.get("scientific_boundary") or "missing"
        lines.extend(
            [
                f"### {module['module_id']}",
                "",
                f"- workflow: {module['workflow']}",
                f"- pass_fail_status: {module['pass_fail_status']}",
                f"- task_status: {module['task_status']}",
                f"- artifact_count: {module['artifact_count']}",
                f"- missing_outputs: {missing}",
                f"- scientific_boundary_present: {module['scientific_boundary_present']}",
                f"- boundary: {boundary}",
                f"- source: {module['source_evidence_path']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Acceptance Boundary",
            "",
            result["acceptance_boundary"],
            "",
            "07 may consume this as module-level evidence only. 12 may extend this adapter for stricter lifecycle/report mapping gates. This is not clinical, diagnostic, statistical, public-cloud, or production-release approval.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        default=str(Path(__file__).resolve().parents[1]),
        help="QLanalyser repo root",
    )
    parser.add_argument(
        "--out",
        default="work/release_evidence/module_evidence_contract_adapter/module_evidence_contract_adapter.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--markdown-out",
        default="work/release_evidence/module_evidence_contract_adapter/module_evidence_contract_adapter.md",
        help="Output Markdown path",
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    out = (repo / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)
    markdown_out = (repo / args.markdown_out).resolve() if not Path(args.markdown_out).is_absolute() else Path(args.markdown_out)
    release_root = repo / "work" / "release_evidence"
    release_summary_path = release_root / "20260620-v01-acceptance" / "release_gate_summary.json"

    missing_files = []
    blocked_release_claims: list[str] = []
    normalized_modules: list[dict[str, Any]] = []

    release_summary: dict[str, Any] | None = None
    if release_summary_path.exists():
        release_summary = read_json(release_summary_path)
        if release_summary.get("status") != "passed":
            blocked_release_claims.append(f"release_summary_status:{release_summary.get('status')}")
        if release_summary.get("public_cloud_ready") is not True:
            blocked_release_claims.append("public_cloud_ready:false")
    else:
        missing_files.append(str(release_summary_path))

    evidence_files = discover_evidence_files(release_root)
    if not evidence_files:
        missing_files.append(str(release_root / "**" / "acceptance_*module*.json"))

    parse_errors: list[str] = []
    support_evidence_files: list[dict[str, Any]] = []
    for evidence_path in evidence_files:
        try:
            payload = read_json(evidence_path)
            if not isinstance(payload, dict):
                parse_errors.append(f"{evidence_path}:not_object")
                continue
            if payload.get("checked_outputs"):
                normalized_modules.append(normalize_module(evidence_path, payload))
            else:
                support_evidence_files.append(
                    {
                        "path": str(evidence_path),
                        "status": payload.get("status"),
                        "evidence_type": payload.get("evidence_type") or payload.get("adapter_id") or evidence_path.stem,
                        "reason_not_module_runner": "missing checked_outputs",
                    }
                )
        except Exception as exc:  # noqa: BLE001 - evidence adapter must report all parse failures.
            parse_errors.append(f"{evidence_path}:{exc}")

    missing_fields: list[str] = []
    for module in normalized_modules:
        for field in ("module_id", "workflow", "pass_fail_status", "source_evidence_path"):
            if not module.get(field):
                missing_fields.append(f"{module.get('module_id', 'unknown')}:{field}")
        if module.get("missing_outputs"):
            missing_fields.append(f"{module.get('module_id')}:missing_outputs:{','.join(module['missing_outputs'])}")

    module_level_blockers = [
        f"{module['module_id']}:status:{module['pass_fail_status']}"
        for module in normalized_modules
        if module.get("pass_fail_status") != "passed"
    ]

    status = "passed" if not missing_files and normalized_modules and not missing_fields and not parse_errors else "failed"
    result = {
        "status": status,
        "adapter_id": "qlanalyser_module_evidence_contract_adapter.v0.2",
        "repo": str(repo),
        "source_paths": {
            "release_summary": str(release_summary_path),
            "module_acceptance_files": [str(path) for path in evidence_files],
        },
        "release_boundary": {
            "release_status": release_summary.get("status") if release_summary else None,
            "local_sandbox_review_ready": release_summary.get("local_sandbox_review_ready") if release_summary else None,
            "public_ecs_sandbox_review_ready": release_summary.get("public_ecs_sandbox_review_ready") if release_summary else None,
            "public_cloud_ready": release_summary.get("public_cloud_ready") if release_summary else None,
            "safe_claim": release_summary.get("safe_claim") if release_summary else None,
        },
        "blocked_release_claims": blocked_release_claims,
        "module_level_blockers": module_level_blockers,
        "normalized_modules": sorted(normalized_modules, key=lambda item: str(item.get("module_id"))),
        "module_count": len(normalized_modules),
        "support_evidence_files": support_evidence_files,
        "support_evidence_count": len(support_evidence_files),
        "missing_files": missing_files,
        "missing_fields": missing_fields,
        "parse_errors": parse_errors,
        "consumer": ["07 QLanalyser Product", "12 Method Center"],
        "acceptance_boundary": "module acceptance evidence only; does not imply public production readiness",
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_out.write_text(build_markdown(result), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
