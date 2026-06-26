from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_review_gate_run.json"
CORE_OUTPUT = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_review_gate_run.core.json"
PREFLIGHT = ROOT / "work" / "release_evidence" / "20260620-aliyun-staging" / "aliyun_staging_preflight.json"
CHECKPOINT_DIR = ROOT / "work" / "release_evidence" / "checkpoints"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_step(
    name: str,
    command: list[str],
    allow_blocked_preflight: bool = False,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    started = utc_now()
    timed_out = False
    timeout_note = ""
    try:
        proc = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout_seconds,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        returncode = proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        timeout_note = f"step timed out after {timeout_seconds} seconds"
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        returncode = 124
    ok = returncode == 0
    note = ""
    if allow_blocked_preflight and returncode != 0 and PREFLIGHT.exists() and not timed_out:
        payload = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
        failed = [check for check in payload.get("checks", []) if check.get("status") == "fail"]
        if payload.get("status") == "blocked_missing_prerequisites" and not failed:
            ok = True
            note = "strict preflight is expected to block until external inputs are provided"
    if timeout_note:
        note = "; ".join(part for part in [note, timeout_note] if part)
    return {
        "name": name,
        "command": command,
        "started_at": started,
        "finished_at": utc_now(),
        "returncode": returncode,
        "ok": ok,
        "note": note,
        "timeout_seconds": timeout_seconds,
        "timed_out": timed_out,
        "stdout_tail": stdout[-4000:],
        "stderr_tail": stderr[-4000:],
    }


def run_step_spec(step: tuple[Any, ...]) -> dict[str, Any]:
    name, command, allow, *rest = step
    timeout_seconds = rest[0] if rest else None
    return run_step(name, command, allow, timeout_seconds)


def latest_checkpoint_json() -> Path:
    candidates = sorted(CHECKPOINT_DIR.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        return CHECKPOINT_DIR / "__missing_checkpoint__.json"
    return candidates[0]


def main() -> int:
    py = sys.executable
    checkpoint_json = latest_checkpoint_json()
    core_steps = [
        ("compile_release_gate_scripts", [py, "-m", "py_compile",
            "scripts/aliyun_staging_preflight.py",
            "scripts/build_aliyun_owner_input_checklist.py",
            "scripts/build_release_gate_summary.py",
            "scripts/acceptance_start_here_release_review.py",
        "scripts/acceptance_owner_input_checklist.py",
        "scripts/acceptance_owner_decision_packet.py",
        "scripts/acceptance_release_gate_summary.py",
        "scripts/acceptance_production_goal_matrix.py",
        "scripts/acceptance_release_no_misclaim.py",
        "scripts/acceptance_utf8_text_preflight.py",
        "scripts/acceptance_visual_layout_design_spec.py",
        "scripts/acceptance_analysis_module_contract.py",
        "scripts/acceptance_analysis_workflow_framework.py",
            "scripts/acceptance_cro_traceability_contract.py",
            "scripts/build_sanitized_review_package.py",
            "scripts/acceptance_sanitized_review_package.py",
            "scripts/refresh_release_readiness_manifest.py",
            "scripts/acceptance_round006_pac_real_report_consumption.py",
            "scripts/acceptance_psd_real_report_consumption.py",
            "scripts/acceptance_qc_real_report_consumption.py",
            "scripts/acceptance_pdf_ocr_artifact_qa.py",
            "scripts/acceptance_round006_tfr_real_report_consumption.py",
            "scripts/acceptance_mainline_eeg_contract_mapping_consumption.py",
            "scripts/acceptance_round007_preprocessing_real_report_consumption.py",
            "scripts/acceptance_round008_erp_real_report_consumption.py",
            "scripts/acceptance_v01_no_group_statistics_boundary.py",
            "scripts/acceptance_p0_fixture_validator_contract.py",
            "scripts/acceptance_p0_gap_repair_contract.py",
            "scripts/build_07a_review_system_packet.py",
            "scripts/acceptance_07a_review_system_packet.py",
            "scripts/acceptance_stage_gated_review_policy.py",
            "scripts/acceptance_review_system_all_environments.py",
            "scripts/acceptance_report_artifact_label_readability.py",
            "scripts/validate_checkpoint_packet_access.py",
            "scripts/acceptance_checkpoint_packet_access.py",
        ], False),
        ("check_workflow_pages_ui_gate_script", ["node", "--check", "scripts/acceptance_workflow_pages_ui_gate.mjs"], False),
        ("mojibake_check", [py, "scripts/check_no_mojibake.py"], False),
        ("accept_utf8_text_preflight", [py, "scripts/acceptance_utf8_text_preflight.py"], False),
        ("accept_visual_layout_design_spec", [py, "scripts/acceptance_visual_layout_design_spec.py"], False),
        ("strict_preflight_expected_block", [py, "scripts/aliyun_staging_preflight.py", "--strict"], True),
        ("owner_input_checklist", [py, "scripts/build_aliyun_owner_input_checklist.py"], False),
        ("accept_start_here_release_review", [py, "scripts/acceptance_start_here_release_review.py"], False),
        ("accept_owner_input_checklist", [py, "scripts/acceptance_owner_input_checklist.py"], False),
        ("accept_owner_decision_packet", [py, "scripts/acceptance_owner_decision_packet.py"], False),
        ("accept_analysis_module_contract", [py, "scripts/acceptance_analysis_module_contract.py"], False),
        ("accept_analysis_workflow_framework", [py, "scripts/acceptance_analysis_workflow_framework.py"], False),
        ("accept_cro_traceability_contract", [py, "scripts/acceptance_cro_traceability_contract.py"], False),
        ("accept_edf_upload_to_results_ui_only", ["node", "scripts/acceptance_edf_upload_to_results_ui_only.mjs"], False, 420),
        ("accept_round006_pac_real_report_consumption", [py, "scripts/acceptance_round006_pac_real_report_consumption.py"], False),
        ("accept_psd_real_report_consumption", [py, "scripts/acceptance_psd_real_report_consumption.py"], False),
        ("accept_qc_real_report_consumption", [py, "scripts/acceptance_qc_real_report_consumption.py"], False),
        ("accept_pdf_ocr_artifact_qa", [py, "scripts/acceptance_pdf_ocr_artifact_qa.py"], False),
        ("accept_round006_tfr_real_report_consumption", [py, "scripts/acceptance_round006_tfr_real_report_consumption.py"], False),
        ("accept_mainline_eeg_contract_mapping_consumption", [py, "scripts/acceptance_mainline_eeg_contract_mapping_consumption.py"], False),
        ("accept_round007_preprocessing_real_report_consumption", [py, "scripts/acceptance_round007_preprocessing_real_report_consumption.py"], False),
        ("accept_round008_erp_real_report_consumption", [py, "scripts/acceptance_round008_erp_real_report_consumption.py"], False),
        ("accept_v01_no_group_statistics_boundary", [py, "scripts/acceptance_v01_no_group_statistics_boundary.py"], False),
        ("accept_p0_fixture_validator_contract", [py, "scripts/acceptance_p0_fixture_validator_contract.py"], False),
        ("accept_p0_gap_repair_contract", [py, "scripts/acceptance_p0_gap_repair_contract.py"], False),
        ("accept_stage_gated_review_policy", [py, "scripts/acceptance_stage_gated_review_policy.py"], False),
        ("accept_workflow_pages_ui_gate", ["node", "scripts/acceptance_workflow_pages_ui_gate.mjs"], False, 240),
        ("accept_review_system_all_environments", [py, "scripts/acceptance_review_system_all_environments.py"], False),
        ("accept_report_artifact_label_readability", [py, "scripts/acceptance_report_artifact_label_readability.py"], False),
        ("validate_latest_checkpoint_access", [py, "scripts/validate_checkpoint_packet_access.py", str(checkpoint_json)], False),
        ("accept_latest_checkpoint_access", [py, "scripts/acceptance_checkpoint_packet_access.py", str(checkpoint_json)], False),
    ]
    post_output_steps = [
        ("accept_production_goal_matrix", [py, "scripts/acceptance_production_goal_matrix.py"], False),
        ("accept_release_no_misclaim", [py, "scripts/acceptance_release_no_misclaim.py"], False),
        ("build_07a_review_system_packet", [py, "scripts/build_07a_review_system_packet.py"], False),
        ("accept_07a_review_system_packet", [py, "scripts/acceptance_07a_review_system_packet.py"], False),
        ("sanitized_evidence_bundle", [py, "scripts/build_sanitized_evidence_bundle.py"], False),
        ("sanitized_review_package", [py, "scripts/build_sanitized_review_package.py"], False),
        ("accept_sanitized_review_package", [py, "scripts/acceptance_sanitized_review_package.py"], False),
        ("accept_release_review_gate_steps", [py, "scripts/acceptance_release_review_gate_steps.py"], False),
        ("refresh_release_readiness_manifest", [py, "scripts/refresh_release_readiness_manifest.py"], False),
        ("accept_release_manifest_consistency", [py, "scripts/acceptance_release_manifest_consistency.py"], False),
        ("release_gate_summary", [py, "scripts/build_release_gate_summary.py"], False),
        ("accept_release_gate_summary", [py, "scripts/acceptance_release_gate_summary.py"], False),
    ]

    results = [run_step_spec(step) for step in core_steps]
    status = "passed" if all(step["ok"] for step in results) else "failed"
    payload = {
        "status": status,
        "generated_at": utc_now(),
        "safe_claim": "Local/sandbox release review gate passed; public cloud release remains blocked by strict preflight external inputs.",
        "steps": results,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    CORE_OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if status == "passed":
        post_results = []
        for step in post_output_steps:
            payload.update({
                "status": "passed" if all(step["ok"] for step in results + post_results) else "failed",
                "generated_at": utc_now(),
                "steps": results + post_results,
            })
            OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            post_results.append(run_step_spec(step))
        results.extend(post_results)
        status = "passed" if all(step["ok"] for step in results) else "failed"
        payload.update({
            "status": status,
            "generated_at": utc_now(),
            "steps": results,
        })

    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": status,
        "output": str(OUTPUT),
        "steps": len(results),
        "failed_steps": [step["name"] for step in results if not step["ok"]],
    }, ensure_ascii=False, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
