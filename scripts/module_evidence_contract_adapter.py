from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_OUTPUTS = {"parameters", "method_description", "result", "manifest", "log"}


def read_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if "\ufffd" in text:
        raise ValueError(f"replacement character found in {path}")
    return json.loads(text)


def normalize_connectivity(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    checked_outputs = set(payload.get("checked_outputs") or [])
    missing_outputs = sorted(REQUIRED_OUTPUTS - checked_outputs)
    return {
        "module_id": payload.get("module") or "unknown",
        "workflow": payload.get("workflow") or payload.get("module") or "unknown",
        "lifecycle_state": "acceptance_evidence_only",
        "task_status": payload.get("task_status"),
        "artifact_count": payload.get("artifact_count"),
        "checked_outputs": sorted(checked_outputs),
        "missing_outputs": missing_outputs,
        "method_description_present": "method_description" in checked_outputs,
        "parameters_present": "parameters" in checked_outputs,
        "manifest_present": "manifest" in checked_outputs,
        "result_present": "result" in checked_outputs,
        "log_present": "log" in checked_outputs,
        "scientific_boundary_present": False,
        "report_mapping_present": False,
        "pass_fail_status": payload.get("status", "unknown"),
        "source_evidence_path": str(path),
        "source_failures": payload.get("failures") or [],
    }


def normalize_generic(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    checked_outputs = set(payload.get("checked_outputs") or [])
    missing_outputs = sorted(REQUIRED_OUTPUTS - checked_outputs)
    module_id = payload.get("module") or payload.get("module_id") or path.stem
    return {
        "module_id": module_id,
        "workflow": payload.get("workflow") or module_id,
        "lifecycle_state": payload.get("lifecycle_state") or "acceptance_evidence_only",
        "task_status": payload.get("task_status") or payload.get("status"),
        "artifact_count": payload.get("artifact_count"),
        "checked_outputs": sorted(checked_outputs),
        "missing_outputs": missing_outputs,
        "method_description_present": "method_description" in checked_outputs,
        "parameters_present": "parameters" in checked_outputs,
        "manifest_present": "manifest" in checked_outputs,
        "result_present": "result" in checked_outputs,
        "log_present": "log" in checked_outputs,
        "scientific_boundary_present": bool(payload.get("scientific_boundary_present")),
        "report_mapping_present": bool(payload.get("report_mapping_present")),
        "pass_fail_status": payload.get("status", "unknown"),
        "source_evidence_path": str(path),
        "source_failures": payload.get("failures") or [],
    }


def normalize_module(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("module") == "connectivity":
        return normalize_connectivity(path, payload)
    return normalize_generic(path, payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        default="D:/Quanlan/Codes/Python/quanlan-analyser-official",
        help="QLanalyser repo root",
    )
    parser.add_argument(
        "--out",
        default="work/release_evidence/module_evidence_contract_adapter/module_evidence_contract_adapter.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    repo = Path(args.repo)
    out = Path(args.out)
    release_root = repo / "work" / "release_evidence"
    release_summary_path = release_root / "20260620-v01-acceptance" / "release_gate_summary.json"
    connectivity_path = release_root / "20260622-connectivity-module" / "acceptance_connectivity_module.json"

    missing_files = [str(path) for path in (release_summary_path, connectivity_path) if not path.exists()]
    blocked_release_claims: list[str] = []
    normalized_modules: list[dict[str, Any]] = []

    release_summary: dict[str, Any] | None = None
    if release_summary_path.exists():
        release_summary = read_json(release_summary_path)
        if release_summary.get("status") != "passed":
            blocked_release_claims.append(f"release_summary_status:{release_summary.get('status')}")
        if release_summary.get("public_cloud_ready") is not True:
            blocked_release_claims.append("public_cloud_ready:false")

    if connectivity_path.exists():
        normalized_modules.append(normalize_module(connectivity_path, read_json(connectivity_path)))

    missing_fields: list[str] = []
    for module in normalized_modules:
        for field in ("module_id", "workflow", "pass_fail_status", "source_evidence_path"):
            if not module.get(field):
                missing_fields.append(f"{module.get('module_id', 'unknown')}:{field}")
        if module.get("missing_outputs"):
            missing_fields.append(f"{module.get('module_id')}:missing_outputs:{','.join(module['missing_outputs'])}")

    status = "passed" if not missing_files and normalized_modules and not missing_fields else "failed"
    result = {
        "status": status,
        "adapter_id": "qlanalyser_module_evidence_contract_adapter.v0.1",
        "repo": str(repo),
        "source_paths": {
            "release_summary": str(release_summary_path),
            "connectivity_acceptance": str(connectivity_path),
        },
        "release_boundary": {
            "release_status": release_summary.get("status") if release_summary else None,
            "local_sandbox_review_ready": release_summary.get("local_sandbox_review_ready") if release_summary else None,
            "public_ecs_sandbox_review_ready": release_summary.get("public_ecs_sandbox_review_ready") if release_summary else None,
            "public_cloud_ready": release_summary.get("public_cloud_ready") if release_summary else None,
            "safe_claim": release_summary.get("safe_claim") if release_summary else None,
        },
        "blocked_release_claims": blocked_release_claims,
        "normalized_modules": normalized_modules,
        "missing_files": missing_files,
        "missing_fields": missing_fields,
        "consumer": ["07 QLanalyser Product", "12 Method Center"],
        "acceptance_boundary": "module acceptance evidence only; does not imply public production readiness",
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
