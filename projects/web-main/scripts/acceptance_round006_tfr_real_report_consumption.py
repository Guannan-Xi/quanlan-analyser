from __future__ import annotations

import csv
import json
import re
import zipfile
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EDF_UI_EVIDENCE = ROOT / "work" / "release_evidence" / "edf_upload_to_results_ui_only" / "edf_upload_to_results_ui_only.json"
OUT_PATH = ROOT / "work" / "release_evidence" / "virtual_reviewer_round_006" / "tfr_real_report_consumption.json"


def status(ok: bool, evidence: Any = None) -> dict[str, Any]:
    item: dict[str, Any] = {"status": "pass" if ok else "block"}
    if evidence is not None:
        item["evidence"] = evidence
    return item


def load_json_from_zip(zf: zipfile.ZipFile, name: str) -> dict[str, Any]:
    return json.loads(zf.read(name).decode("utf-8"))


def load_text_from_zip(zf: zipfile.ZipFile, name: str) -> str:
    return zf.read(name).decode("utf-8", errors="replace")


def read_csv_rows(zf: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    return list(csv.DictReader(StringIO(load_text_from_zip(zf, name))))


def find_tfr_prefix(names: set[str], evidence: dict[str, Any]) -> str | None:
    inspect = evidence.get("reportZipInspect") or {}
    for item in inspect.get("included_analyses") or []:
        if item.get("module_name") == "tfr" and item.get("package_prefix"):
            prefix = str(item["package_prefix"]).rstrip("/")
            if f"{prefix}/reproducibility/tfr_summary.json" in names:
                return prefix
    for name in sorted(names):
        if name.startswith("analyses/tfr_") and name.endswith("/reproducibility/tfr_summary.json"):
            return name.rsplit("/reproducibility/tfr_summary.json", 1)[0]
    return None


def has_unsupported_claim(text: str) -> bool:
    patterns = [
        r"\bproves?\b",
        r"\bsignificant neural effect\b",
        r"\bcauses? (?:improved|reduced|abnormal|clinical|diagnostic)\b",
        r"\blocali[sz]es? (?:abnormal|the|a|an)? ?(?:source|brain|cortex|hippocampus|region)\b",
        r"\bdiagnostic (?:marker|proof|result|finding|evidence)\b",
    ]
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


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
    tfr_prefix = None
    if not failures and report_zip is not None:
        with zipfile.ZipFile(report_zip) as zf:
            names = {name.replace("\\", "/") for name in zf.namelist()}
            tfr_prefix = find_tfr_prefix(names, evidence)
            checks["tfr_analysis_namespace_present"] = status(bool(tfr_prefix), tfr_prefix)
            if tfr_prefix:
                required = {
                    "tfr_summary": f"{tfr_prefix}/reproducibility/tfr_summary.json",
                    "parameters": f"{tfr_prefix}/reproducibility/parameters.json",
                    "frequency_grid": f"{tfr_prefix}/reproducibility/frequency_grid.json",
                    "effective_call": f"{tfr_prefix}/reproducibility/effective_call.json",
                    "scope_contract": f"{tfr_prefix}/reproducibility/scope_contract.json",
                    "workflow": f"{tfr_prefix}/reproducibility/workflow.json",
                    "power_csv": f"{tfr_prefix}/tables/tfr_power_long.csv",
                    "summary_csv": f"{tfr_prefix}/tables/tfr_summary.csv",
                }
                optional = {
                    "itc_csv": f"{tfr_prefix}/tables/tfr_itc_long.csv",
                    "power_svg": f"{tfr_prefix}/figures/tfr_power.svg",
                    "itc_svg": f"{tfr_prefix}/figures/tfr_itc.svg",
                }
                for label, name in required.items():
                    checks[f"{label}_present"] = status(name in names, name)
                for label, name in optional.items():
                    checks[f"{label}_present"] = status(name in names, name)

                if all(name in names for name in required.values()):
                    tfr_summary = load_json_from_zip(zf, required["tfr_summary"])
                    params = load_json_from_zip(zf, required["parameters"])
                    frequency_grid = load_json_from_zip(zf, required["frequency_grid"])
                    effective_call = load_json_from_zip(zf, required["effective_call"])
                    scope_contract = load_json_from_zip(zf, required["scope_contract"])
                    workflow = load_json_from_zip(zf, required["workflow"])
                    power_rows = read_csv_rows(zf, required["power_csv"])
                    summary_rows = read_csv_rows(zf, required["summary_csv"])
                    itc_rows = read_csv_rows(zf, optional["itc_csv"]) if optional["itc_csv"] in names else []
                    combined_text = " ".join(
                        [
                            json.dumps(tfr_summary, ensure_ascii=False),
                            json.dumps(scope_contract, ensure_ascii=False),
                            json.dumps(workflow, ensure_ascii=False),
                            load_text_from_zip(zf, f"{tfr_prefix}/reproducibility/method_description.txt")
                            if f"{tfr_prefix}/reproducibility/method_description.txt" in names
                            else "",
                        ]
                    )

                    power_columns = set(power_rows[0].keys()) if power_rows else set()
                    summary_columns = set(summary_rows[0].keys()) if summary_rows else set()
                    itc_columns = set(itc_rows[0].keys()) if itc_rows else set()
                    effective_kwargs = effective_call.get("kwargs") or {}
                    workflow_steps = [str(item.get("name", "")).lower() for item in workflow.get("steps") or []]

                    checks.update(
                        {
                            "measure_type_present": status(
                                "power_db" in power_columns and (not params.get("return_itc") or "itc" in itc_columns),
                                {"power_columns": sorted(power_columns), "itc_columns": sorted(itc_columns)},
                            ),
                            "method_present": status(bool(tfr_summary.get("method") and effective_call.get("call")), {"method": tfr_summary.get("method"), "call": effective_call.get("call")}),
                            "frequency_grid_present": status(bool(frequency_grid.get("freqs_hz") or params.get("freqs")), frequency_grid.get("freqs_hz") or params.get("freqs")),
                            "time_axis_present": status("time_sec" in power_columns and bool(power_rows), "time_sec"),
                            "baseline_or_correction_present": status(bool(params.get("baseline")) and "baseline" in power_columns, {"parameters_baseline": params.get("baseline"), "power_csv_baseline_column": "baseline" in power_columns}),
                            "units_or_colorbar_present": status(
                                ("unit" in power_columns and any(row.get("unit") for row in power_rows[:20])) and optional["power_svg"] in names,
                                {"power_unit_column": "unit" in power_columns, "power_svg": optional["power_svg"] in names},
                            ),
                            "method_parameters_present": status(
                                all(key in effective_kwargs for key in ("freqs", "n_cycles", "return_itc", "decim"))
                                and all(key in params for key in ("freqs", "n_cycles", "return_itc", "decim")),
                                {"effective_kwargs": effective_kwargs, "parameters": {key: params.get(key) for key in ("freqs", "n_cycles", "return_itc", "decim")}},
                            ),
                            "warnings_and_limitations_present": status(bool(tfr_summary.get("warnings")) and bool(scope_contract.get("boundary")), {"warnings": tfr_summary.get("warnings"), "boundary": scope_contract.get("boundary")}),
                            "workflow_records_epoch_and_compute_tfr": status("epoch" in workflow_steps and "compute_tfr" in workflow_steps, workflow_steps),
                            "summary_csv_has_expected_columns": status({"channel", "peak_frequency_hz", "peak_time_sec", "peak_power_db", "itc_available", "warnings"}.issubset(summary_columns), sorted(summary_columns)),
                            "no_effect_claim_without_statistics": status(not has_unsupported_claim(combined_text), "forbidden claim scan over summary/scope/workflow/method text"),
                            "beta_boundary_present": status(
                                "single-record" in combined_text.lower()
                                and "diagnosis" in combined_text.lower()
                                and "group" in combined_text.lower()
                                and "source" in combined_text.lower(),
                                tfr_summary.get("boundary") or scope_contract.get("boundary"),
                            ),
                        }
                    )

    blockers = [key for key, item in checks.items() if isinstance(item, dict) and item.get("status") == "block"]
    failures.extend(blockers)
    result = {
        "schema_version": "qlanalyser-round006-tfr-real-report-consumption-v0.1",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not failures else "failed",
        "requirement_id": "VR-EO-0017",
        "scope": "real UI-only report ZIP consumption for TFR power/ITC method, axes, units, baseline, and boundary evidence",
        "important_boundary": "This is TFR report artifact consumption evidence only; not advanced method release, statistical approval, or clinical/diagnostic approval.",
        "ui_evidence_path": str(EDF_UI_EVIDENCE),
        "report_zip_path": str(report_zip) if report_zip else None,
        "tfr_prefix": tfr_prefix,
        "checks": checks,
        "blockers": failures,
        "what_07_can_consume_next": [
            "Use this as the real-report counterpart to round_006 VR-EO-0017.",
            "Keep TFR interpretation gated on measure type, frequency/time axes, baseline, units, method parameters, and beta boundary wording.",
            "Do not use this checker as an advanced-method release, group-statistics, or clinical/scientific pass decision.",
        ],
        "07A_SHORT_PACKET_METRICS": {
            "mini/script packet count": 1,
            "script packet used": "round_006 TFR real report consumption checker",
            "GPT-5.5 low-value work avoided": "ZIP entry inventory and field presence checks are scripted",
            "concurrency frontier": "single deterministic checker over latest UI-only report ZIP",
            "long-term platform asset produced": "real TFR report artifact validator adapter for VR-EO-0017",
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
