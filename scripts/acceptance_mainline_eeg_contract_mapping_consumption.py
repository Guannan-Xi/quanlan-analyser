from __future__ import annotations

import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_DIR = ROOT / "work" / "release_evidence" / "checkpoints"
SUMMARY_PATH = ROOT / "work" / "release_evidence" / "20260620-v01-acceptance" / "release_gate_summary.json"
MAPPING_PATH = CHECKPOINT_DIR / "2026-06-22-07a-mainline-eeg-contract-mapping.json"
BRIDGE_ACCEPTANCE_PATH = ROOT / "work" / "release_evidence" / "mainline_eeg_review" / "mainline_eeg_review_bridge_acceptance.json"
EDF_UI_EVIDENCE_PATH = ROOT / "work" / "release_evidence" / "edf_upload_to_results_ui_only" / "edf_upload_to_results_ui_only.json"
OUTPUT_PATH = ROOT / "work" / "release_evidence" / "mainline_eeg_review" / "mainline_eeg_contract_mapping_consumption.json"

REPORT_ZIP_REQUIRED = {
    "reports/report.pdf",
    "reports/report.json",
    "reports/report_manifest.json",
    "tables/metrics.csv",
    "manifest.json",
    "result.json",
    "reproducibility/parameters.json",
    "reproducibility/software_versions.json",
    "reproducibility/workflow.json",
    "reproducibility/method_description.txt",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure(condition: bool, failures: list[str], message: str) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []

    for path, label in [
        (MAPPING_PATH, "mapping"),
        (SUMMARY_PATH, "release summary"),
        (BRIDGE_ACCEPTANCE_PATH, "bridge acceptance"),
    ]:
        ensure(path.exists(), failures, f"missing {label}: {path}")

    mapping: dict = {}
    summary: dict = {}
    bridge: dict = {}
    edf_evidence: dict = {}
    report_zip_path: Path | None = None
    report_zip_missing: list[str] = []
    if not failures:
        mapping = load_json(MAPPING_PATH)
        summary = load_json(SUMMARY_PATH)
        bridge = load_json(BRIDGE_ACCEPTANCE_PATH)
        edf_evidence = load_json(EDF_UI_EVIDENCE_PATH)

        ensure(mapping.get("checkpoint_type") == "07A_MAINLINE_EEG_CONTRACT_MAPPING", failures, "unexpected checkpoint_type")
        ensure(mapping.get("status") == "ready_for_07_review", failures, "mapping status is not ready_for_07_review")
        ensure(mapping.get("final_marker") == "QLANALYSER_MAINLINE_REVIEW_READY", failures, "mapping final_marker missing")

        snapshot = mapping.get("snapshot") or {}
        ensure(snapshot.get("edf_ui_only_checkpoint") == "passed", failures, "edf ui checkpoint is not passed in mapping snapshot")
        ensure(snapshot.get("mainline_eeg_expert_review") == "CONDITIONAL PASS", failures, "mainline expert review is not CONDITIONAL PASS in mapping snapshot")
        ensure(snapshot.get("bridge_gate") == "passed", failures, "bridge gate is not passed in mapping snapshot")

        evidence = mapping.get("evidence") or {}
        for key in [
            "edf_ui_only_checkpoint_md",
            "mainline_eeg_expert_review_md",
            "bridge_checkpoint_md",
            "handoff_checkpoint_md",
            "brief_checkpoint_md",
        ]:
            ensure(bool(str(evidence.get(key, "")).strip()), failures, f"mapping missing evidence key: {key}")

        recent = summary.get("recent_review_checkpoints") or {}
        contract_summary = recent.get("mainline_eeg_contract_mapping_checkpoint") or {}
        ensure(contract_summary.get("status") == "ready_for_07_review", failures, "release summary does not expose contract mapping as ready_for_07_review")
        ensure(
            str(contract_summary.get("path", "")).endswith("2026-06-22-07a-mainline-eeg-contract-mapping.json"),
            failures,
            "release summary points at wrong contract mapping path",
        )
        ensure(
            str(contract_summary.get("markdown_path", "")).endswith("2026-06-22-07a-mainline-eeg-contract-mapping.md"),
            failures,
            "release summary points at wrong contract mapping markdown path",
        )

        source_paths = summary.get("source_paths") or {}
        ensure(
            str(source_paths.get("mainline_eeg_contract_mapping_checkpoint", "")).endswith("2026-06-22-07a-mainline-eeg-contract-mapping.json"),
            failures,
            "release summary source_paths missing contract mapping checkpoint",
        )

        bridge_summary = bridge.get("summary") or {}
        ensure(bridge.get("status") == "passed", failures, "bridge acceptance is not passed")
        ensure(bridge_summary.get("recommendation") == "CONDITIONAL PASS for entering mainline integration review", failures, "bridge acceptance recommendation mismatch")
        bridge_metrics = bridge.get("07A_SHORT_PACKET_METRICS") or {}
        ensure(
            "mainline EEG prototype review packets" in str(bridge_metrics.get("long_term_platform_asset_produced", "")),
            failures,
            "bridge acceptance asset value mismatch",
        )

        ensure(edf_evidence.get("status") == "passed", failures, "EDF UI-only evidence is not passed")
        downloads = edf_evidence.get("downloads") or []
        report_download = next((item for item in downloads if item.get("requirement") == "report package zip"), None)
        ensure(bool(report_download), failures, "EDF UI-only evidence has no report package zip download")
        if report_download:
            report_zip_path = Path(str(report_download.get("path", "")))
            ensure(report_zip_path.exists(), failures, f"report ZIP missing: {report_zip_path}")
            ensure(report_download.get("header") == "504b0304", failures, "report ZIP header is not a ZIP header")
            if report_zip_path.exists():
                with zipfile.ZipFile(report_zip_path) as zf:
                    names = {name.replace("\\", "/") for name in zf.namelist()}
                    report_zip_missing = sorted(item for item in REPORT_ZIP_REQUIRED if item not in names)
                    ensure(not report_zip_missing, failures, f"report ZIP missing required entries: {report_zip_missing}")
                    ensure(any(name.startswith("qc/") for name in names), failures, "report ZIP missing QC artifact namespace")
                    ensure(any(name.startswith("reproducibility/") for name in names), failures, "report ZIP missing reproducibility namespace")

    result = {
        "status": "passed" if not failures else "failed",
        "mapping_path": str(MAPPING_PATH),
        "executable_checker_or_adapter": str(Path(__file__).resolve()),
        "run_result": {
            "mapping_status": mapping.get("status") if mapping else None,
            "release_summary_contract_mapping_status": (summary.get("recent_review_checkpoints") or {}).get("mainline_eeg_contract_mapping_checkpoint", {}).get("status") if summary else None,
            "bridge_status": bridge.get("status") if bridge else None,
            "bridge_recommendation": (bridge.get("summary") or {}).get("recommendation") if bridge else None,
            "edf_ui_only_status": edf_evidence.get("status") if edf_evidence else None,
            "report_zip_path": str(report_zip_path) if report_zip_path else None,
            "report_zip_missing_required_entries": report_zip_missing,
        },
        "what_07_can_consume_next": [
            "Use the mapping as a review-intake normalization layer for the mainline EEG evidence chain.",
            "Treat it as a contract-consumption check only; do not read it as release pass.",
            "Consume the bridge/handoff/brief chain plus the EDF UI-only PASS as the current staged integration evidence set.",
        ],
        "blocker": failures,
        "why_not_mini": "Mainline EEG contract consumption touches the main repo evidence contract and staged integration judgment, which belongs in GPT-5.5/Codex.",
        "07A_SHORT_PACKET_METRICS": {
            "mini_script_packet_count": 1,
            "script_packet_used": "mainline EEG contract mapping consumption checker",
            "GPT_5_5_low_value_work_avoided": "path assertions, JSON linkage checks, evidence-consistency counting",
            "concurrency_frontier": "single narrow checker over mapping, release summary, and bridge acceptance",
            "long_term_platform_asset_produced": "mainline EEG contract-consumption check for 07 handoff",
            "owner_boundary_respected": "yes",
            "handoff_target": "07 main owner",
        },
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
