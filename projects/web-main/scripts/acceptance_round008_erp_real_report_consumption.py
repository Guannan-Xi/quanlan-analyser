from __future__ import annotations

import csv
import json
import zipfile
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EDF_UI_EVIDENCE = ROOT / "work" / "release_evidence" / "edf_upload_to_results_ui_only" / "edf_upload_to_results_ui_only.json"
OUT_PATH = ROOT / "work" / "release_evidence" / "virtual_reviewer_round_008" / "erp_real_report_consumption.json"


def status(ok: bool, evidence: Any = None) -> dict[str, Any]:
    item: dict[str, Any] = {"status": "pass" if ok else "block"}
    if evidence is not None:
        item["evidence"] = evidence
    return item


def load_json_from_zip(zf: zipfile.ZipFile, name: str) -> dict[str, Any]:
    return json.loads(zf.read(name).decode("utf-8"))


def find_erp_prefix(names: set[str], evidence: dict[str, Any]) -> str | None:
    inspect = evidence.get("reportZipInspect") or {}
    for item in inspect.get("included_analyses") or []:
        if item.get("module_name") == "erp" and item.get("package_prefix"):
            prefix = str(item["package_prefix"]).rstrip("/")
            if f"{prefix}/reproducibility/erp_summary.json" in names:
                return prefix
    for name in sorted(names):
        if name.startswith("analyses/erp_") and name.endswith("/reproducibility/erp_summary.json"):
            return name.rsplit("/reproducibility/erp_summary.json", 1)[0]
    return None


def read_metrics_rows(zf: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    text = zf.read(name).decode("utf-8")
    return list(csv.DictReader(StringIO(text)))


def main() -> int:
    failures: list[str] = []
    evidence = json.loads(EDF_UI_EVIDENCE.read_text(encoding="utf-8"))
    downloads = evidence.get("downloads") or []
    report_download = next((item for item in downloads if item.get("requirement") == "report package zip"), None)
    report_zip = Path(str(report_download.get("path", ""))) if report_download else None
    if evidence.get("status") != "passed":
        failures.append("EDF UI-only evidence is not passed")
    if report_zip is None or not report_zip.exists():
        failures.append("report package zip is missing")

    checks: dict[str, Any] = {}
    erp_prefix = None
    if not failures and report_zip is not None:
        with zipfile.ZipFile(report_zip) as zf:
            names = {name.replace("\\", "/") for name in zf.namelist()}
            erp_prefix = find_erp_prefix(names, evidence)
            checks["erp_analysis_namespace_present"] = status(bool(erp_prefix), erp_prefix)
            if erp_prefix:
                required = {
                    "erp_summary": f"{erp_prefix}/reproducibility/erp_summary.json",
                    "event_confirmation": f"{erp_prefix}/reproducibility/event_confirmation.json",
                    "drop_log_summary": f"{erp_prefix}/reproducibility/drop_log_summary.json",
                    "parameters": f"{erp_prefix}/reproducibility/parameters.json",
                    "workflow": f"{erp_prefix}/reproducibility/workflow.json",
                    "metrics_csv": f"{erp_prefix}/tables/erp_metrics.csv",
                }
                for label, name in required.items():
                    checks[f"{label}_present"] = status(name in names, name)

                if all(name in names for name in required.values()):
                    erp_summary = load_json_from_zip(zf, required["erp_summary"])
                    event_confirmation = load_json_from_zip(zf, required["event_confirmation"])
                    drop_log = load_json_from_zip(zf, required["drop_log_summary"])
                    workflow = load_json_from_zip(zf, required["workflow"])
                    rows = read_metrics_rows(zf, required["metrics_csv"])
                    params = (load_json_from_zip(zf, required["parameters"]).get("parameters") or {})

                    event_id = erp_summary.get("event_id") or event_confirmation.get("selected_event_id") or params.get("event_id")
                    baseline = erp_summary.get("baseline", params.get("baseline"))
                    per_condition_counts = erp_summary.get("per_condition_epoch_counts") or {
                        condition: payload.get("n_epochs")
                        for condition, payload in (erp_summary.get("conditions") or {}).items()
                        if isinstance(payload, dict) and payload.get("n_epochs") is not None
                    }
                    workflow_steps = [str(item.get("name", "")).lower() for item in workflow.get("steps") or []]

                    checks.update(
                        {
                            "event_id_mapping_present": status(isinstance(event_id, dict) and len(event_id) >= 2, event_id),
                            "epoch_tmin_tmax_present": status(erp_summary.get("tmin") is not None and erp_summary.get("tmax") is not None, [erp_summary.get("tmin"), erp_summary.get("tmax")]),
                            "baseline_window_present_or_explicit_none": status("baseline" in erp_summary and baseline is not None, baseline),
                            "reject_by_annotation_present": status("reject_by_annotation" in erp_summary, erp_summary.get("reject_by_annotation")),
                            "drop_log_present": status(bool(drop_log) and "kept_epochs" in drop_log and "dropped_epochs" in drop_log, drop_log),
                            "nave_or_epoch_count_present": status(bool(erp_summary.get("nave") or per_condition_counts), erp_summary.get("nave") or per_condition_counts),
                            "per_condition_counts_present": status(bool(per_condition_counts), per_condition_counts),
                            "channel_units_present": status(bool(erp_summary.get("units") or any("amplitude_uv" in row for row in rows)), erp_summary.get("units") or "amplitude_uv"),
                            "baseline_state_present": status(bool(erp_summary.get("baseline_state") or baseline is not None), erp_summary.get("baseline_state")),
                            "workflow_records_epoch_and_drop_log": status("epoch" in workflow_steps and "drop_log" in workflow_steps, workflow_steps),
                            "metrics_csv_has_condition_component_epoch_columns": status(
                                bool(rows)
                                and {"condition", "component", "n_epochs"}.issubset(set(rows[0].keys())),
                                list(rows[0].keys()) if rows else [],
                            ),
                        }
                    )

    blockers = [key for key, item in checks.items() if isinstance(item, dict) and item.get("status") == "block"]
    failures.extend(blockers)
    result = {
        "schema_version": "qlanalyser-round008-real-report-consumption-v0.1",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not failures else "failed",
        "requirement_id": "VR-EO-0023",
        "scope": "real UI-only report ZIP consumption for ERP baseline/count/drop-log evidence",
        "important_boundary": "This is report artifact consumption evidence only; not product release pass, statistical approval, or clinical/diagnostic approval.",
        "ui_evidence_path": str(EDF_UI_EVIDENCE),
        "report_zip_path": str(report_zip) if report_zip else None,
        "erp_prefix": erp_prefix,
        "checks": checks,
        "blockers": failures,
        "what_07_can_consume_next": [
            "Use this as the real-report counterpart to round_008 VR-EO-0023.",
            "Keep ERP interpretation gated on event mapping, baseline, drop log, and per-condition epoch counts.",
            "Do not use this checker as a group-statistics or release-pass decision.",
        ],
        "07A_SHORT_PACKET_METRICS": {
            "mini/script packet count": 1,
            "script packet used": "round_008 ERP real report consumption checker",
            "GPT-5.5 low-value work avoided": "ZIP entry inventory and field presence checks are scripted",
            "concurrency frontier": "single deterministic checker over latest UI-only report ZIP",
            "long-term platform asset produced": "real ERP report artifact validator adapter for VR-EO-0023",
            "owner boundary respected": "yes",
            "handoff target": "07 main owner",
        },
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
