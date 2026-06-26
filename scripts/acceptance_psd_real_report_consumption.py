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
OUT_PATH = ROOT / "work" / "release_evidence" / "virtual_reviewer_p0" / "psd_real_report_consumption.json"


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


def find_psd_prefix(names: set[str], evidence: dict[str, Any]) -> str | None:
    inspect = evidence.get("reportZipInspect") or {}
    for item in inspect.get("included_analyses") or []:
        if item.get("module_name") == "psd" and item.get("package_prefix"):
            prefix = str(item["package_prefix"]).rstrip("/")
            if f"{prefix}/reproducibility/psd_summary.json" in names:
                return prefix
    for name in sorted(names):
        if name.startswith("analyses/psd_") and name.endswith("/reproducibility/psd_summary.json"):
            return name.rsplit("/reproducibility/psd_summary.json", 1)[0]
    return None


def has_unsupported_claim(text: str) -> bool:
    patterns = [
        r"\bdiagnos(?:is|tic)\b",
        r"\btreatment recommendation\b",
        r"\bclinical (?:marker|proof|evidence|finding)\b",
        r"\bsignificant (?:difference|effect|finding|result)\b",
        r"\bcauses? (?:abnormal|improved|reduced|clinical|diagnostic)\b",
        r"\bbrain region activation\b",
        r"\bsource local(?:i|iza)tion\b",
    ]
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
    psd_prefix = None
    if not failures and report_zip is not None:
        with zipfile.ZipFile(report_zip) as zf:
            names = {name.replace("\\", "/") for name in zf.namelist()}
            psd_prefix = find_psd_prefix(names, evidence)
            checks["psd_analysis_namespace_present"] = status(bool(psd_prefix), psd_prefix)
            if psd_prefix:
                required = {
                    "psd_summary": f"{psd_prefix}/reproducibility/psd_summary.json",
                    "parameters": f"{psd_prefix}/reproducibility/parameters.json",
                    "effective_call": f"{psd_prefix}/reproducibility/effective_call.json",
                    "scope_contract": f"{psd_prefix}/reproducibility/scope_contract.json",
                    "workflow": f"{psd_prefix}/reproducibility/workflow.json",
                    "method_description": f"{psd_prefix}/reproducibility/method_description.txt",
                    "band_power_csv": f"{psd_prefix}/tables/band_power.csv",
                    "channel_band_power_csv": f"{psd_prefix}/tables/channel_band_power.csv",
                    "spectrum_long_csv": f"{psd_prefix}/tables/spectrum_long.csv",
                    "band_power_svg": f"{psd_prefix}/figures/psd_band_power.svg",
                    "mean_spectrum_svg": f"{psd_prefix}/figures/psd_mean_spectrum.svg",
                }
                for label, name in required.items():
                    checks[f"{label}_present"] = status(name in names, name)

                if all(name in names for name in required.values()):
                    psd_summary = load_json_from_zip(zf, required["psd_summary"])
                    params = load_json_from_zip(zf, required["parameters"])
                    effective_call = load_json_from_zip(zf, required["effective_call"])
                    scope_contract = load_json_from_zip(zf, required["scope_contract"])
                    workflow = load_json_from_zip(zf, required["workflow"])
                    method_description = load_text_from_zip(zf, required["method_description"])
                    band_rows = read_csv_rows(zf, required["band_power_csv"])
                    channel_rows = read_csv_rows(zf, required["channel_band_power_csv"])
                    spectrum_rows = read_csv_rows(zf, required["spectrum_long_csv"])

                    band_columns = set(band_rows[0].keys()) if band_rows else set()
                    channel_columns = set(channel_rows[0].keys()) if channel_rows else set()
                    spectrum_columns = set(spectrum_rows[0].keys()) if spectrum_rows else set()
                    workflow_steps = [str(item.get("name", "")).lower() for item in workflow.get("steps") or []]
                    kwargs = effective_call.get("kwargs") or {}
                    sfreq = as_float(psd_summary.get("sfreq") or (effective_call.get("input_shape") or {}).get("sfreq"))
                    fmax = as_float(params.get("fmax") or kwargs.get("fmax") or (psd_summary.get("freq_range_hz") or [None, None])[1])
                    nyquist = sfreq / 2.0 if sfreq is not None else None
                    band_names = {row.get("band") for row in band_rows}
                    combined_text = " ".join(
                        [
                            json.dumps(psd_summary, ensure_ascii=False),
                            json.dumps(scope_contract, ensure_ascii=False),
                            json.dumps(workflow, ensure_ascii=False),
                            method_description,
                        ]
                    )

                    checks.update(
                        {
                            "welch_method_present": status(
                                effective_call.get("call") == "Raw.compute_psd"
                                and str(effective_call.get("method", "")).lower() == "welch",
                                {"call": effective_call.get("call"), "method": effective_call.get("method")},
                            ),
                            "frequency_range_present": status(
                                psd_summary.get("freq_range_hz") is not None and params.get("fmin") is not None and params.get("fmax") is not None,
                                {"summary": psd_summary.get("freq_range_hz"), "parameters": [params.get("fmin"), params.get("fmax")]},
                            ),
                            "frequency_range_below_nyquist": status(
                                nyquist is not None and fmax is not None and fmax <= nyquist,
                                {"fmax_hz": fmax, "nyquist_hz": nyquist},
                            ),
                            "band_power_columns_present": status(
                                {"band", "fmin", "fmax", "mean_psd", "median_psd"}.issubset(band_columns),
                                sorted(band_columns),
                            ),
                            "canonical_bands_present": status(
                                {"delta", "theta", "alpha", "beta", "gamma_low"}.issubset(band_names),
                                sorted(item for item in band_names if item),
                            ),
                            "channel_band_power_columns_present": status(
                                {"channel", "delta", "theta", "alpha", "beta", "gamma_low"}.issubset(channel_columns),
                                sorted(channel_columns),
                            ),
                            "spectrum_long_columns_present": status(
                                {"channel", "frequency_hz", "psd"}.issubset(spectrum_columns),
                                sorted(spectrum_columns),
                            ),
                            "data_preparation_lineage_present": status(
                                bool(params.get("data_preparation_plan_id")) and params.get("data_preparation_revision") is not None,
                                {
                                    "plan_id": params.get("data_preparation_plan_id"),
                                    "revision": params.get("data_preparation_revision"),
                                    "contract": params.get("data_preparation_contract_version"),
                                },
                            ),
                            "workflow_records_psd_steps": status(
                                "read_raw" in workflow_steps
                                and "welch_psd" in workflow_steps
                                and ("bandpower" in workflow_steps or "band_summary" in workflow_steps),
                                workflow_steps,
                            ),
                            "scope_contract_stable_sensor_space": status(
                                scope_contract.get("module") == "psd"
                                and scope_contract.get("analysis_scope") == "single_record_descriptive_sensor_space_psd"
                                and scope_contract.get("stable_status") == "stable_v01",
                                {
                                    "module": scope_contract.get("module"),
                                    "analysis_scope": scope_contract.get("analysis_scope"),
                                    "stable_status": scope_contract.get("stable_status"),
                                },
                            ),
                            "warnings_or_cautions_present": status(
                                bool(scope_contract.get("high_frequency_caution")) and "artifact" in str(scope_contract.get("high_frequency_caution", "")).lower(),
                                scope_contract.get("high_frequency_caution"),
                            ),
                            "no_forbidden_claims": status(
                                not has_unsupported_claim(combined_text),
                                "forbidden claim scan over summary/scope/workflow/method text",
                            ),
                        }
                    )

    blockers = [key for key, item in checks.items() if isinstance(item, dict) and item.get("status") == "block"]
    failures.extend(blockers)
    result = {
        "schema_version": "qlanalyser-psd-real-report-consumption-v0.1",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not failures else "failed",
        "requirement_id": "VR-EO-0003",
        "scope": "real UI-only report ZIP consumption for PSD/bandpower method, frequency range, tables, lineage, and boundary evidence",
        "important_boundary": "This is PSD/bandpower report artifact consumption evidence only; not release pass, statistical approval, source localization, or clinical/diagnostic approval.",
        "ui_evidence_path": str(EDF_UI_EVIDENCE),
        "report_zip_path": str(report_zip) if report_zip else None,
        "psd_prefix": psd_prefix,
        "checks": checks,
        "blockers": failures,
        "what_07_can_consume_next": [
            "Use this as the real-report counterpart to the PSD/bandpower P0 artifact contract.",
            "Keep PSD interpretation gated on Welch method metadata, frequency range, band/channel tables, data-preparation lineage, and sensor-space boundary wording.",
            "Do not use this checker as a release-pass, source-localization, group-statistics, clinical, or scientific-interpretation decision.",
        ],
        "07A_SHORT_PACKET_METRICS": {
            "mini/script packet count": 1,
            "script packet used": "PSD real report consumption checker",
            "GPT-5.5 low-value work avoided": "ZIP entry inventory and field presence checks are scripted",
            "concurrency frontier": "single deterministic checker over latest UI-only report ZIP",
            "long-term platform asset produced": "real PSD report artifact validator adapter for P0 report consumption",
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
