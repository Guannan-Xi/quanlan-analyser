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
OUT_PATH = ROOT / "work" / "release_evidence" / "virtual_reviewer_round_006" / "pac_real_report_consumption.json"


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


def find_pac_prefix(names: set[str], evidence: dict[str, Any]) -> str | None:
    inspect = evidence.get("reportZipInspect") or {}
    for item in inspect.get("included_analyses") or []:
        if item.get("module_name") == "pac" and item.get("package_prefix"):
            prefix = str(item["package_prefix"]).rstrip("/")
            if f"{prefix}/reproducibility/pac_summary.json" in names:
                return prefix
    for name in sorted(names):
        if name.startswith("analyses/pac_") and name.endswith("/reproducibility/pac_summary.json"):
            return name.rsplit("/reproducibility/pac_summary.json", 1)[0]
    return None


def has_forbidden_positive_claim(text: str) -> bool:
    patterns = [
        r"\bproves?\b",
        r"\bsignificant (?:pac|coupling|effect|difference)\b",
        r"\bcauses? (?:improved|reduced|abnormal|clinical|diagnostic)\b",
        r"\b(?:proves?|shows?|indicates?) [^.]{0,80}\bbrain[- ]region communication\b",
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
    pac_prefix = None
    if not failures and report_zip is not None:
        with zipfile.ZipFile(report_zip) as zf:
            names = {name.replace("\\", "/") for name in zf.namelist()}
            pac_prefix = find_pac_prefix(names, evidence)
            checks["pac_analysis_namespace_present"] = status(bool(pac_prefix), pac_prefix)
            if pac_prefix:
                required = {
                    "pac_summary": f"{pac_prefix}/reproducibility/pac_summary.json",
                    "parameters": f"{pac_prefix}/reproducibility/parameters.json",
                    "frequency_grid": f"{pac_prefix}/reproducibility/frequency_grid.json",
                    "effective_call": f"{pac_prefix}/reproducibility/effective_call.json",
                    "scope_contract": f"{pac_prefix}/reproducibility/scope_contract.json",
                    "workflow": f"{pac_prefix}/reproducibility/workflow.json",
                    "filter_edge_policy": f"{pac_prefix}/reproducibility/filter_edge_policy.json",
                    "comod_csv": f"{pac_prefix}/tables/pac_comodulogram_long.csv",
                    "bins_csv": f"{pac_prefix}/tables/pac_binned_amplitude.csv",
                    "dynamic_csv": f"{pac_prefix}/tables/pac_dynamic_curve.csv",
                    "summary_csv": f"{pac_prefix}/tables/pac_channel_summary.csv",
                }
                optional = {
                    "comod_svg": f"{pac_prefix}/figures/pac_comodulogram.svg",
                    "phase_bins_svg": f"{pac_prefix}/figures/pac_phase_bins.svg",
                    "dynamic_svg": f"{pac_prefix}/figures/pac_dynamic_curve.svg",
                    "artifact_bundle": f"{pac_prefix}/pac_beta_artifact_bundle.zip",
                }
                for label, name in required.items():
                    checks[f"{label}_present"] = status(name in names, name)
                for label, name in optional.items():
                    checks[f"{label}_present"] = status(name in names, name)

                if all(name in names for name in required.values()):
                    pac_summary = load_json_from_zip(zf, required["pac_summary"])
                    params = load_json_from_zip(zf, required["parameters"])
                    frequency_grid = load_json_from_zip(zf, required["frequency_grid"])
                    effective_call = load_json_from_zip(zf, required["effective_call"])
                    scope_contract = load_json_from_zip(zf, required["scope_contract"])
                    workflow = load_json_from_zip(zf, required["workflow"])
                    filter_policy = load_json_from_zip(zf, required["filter_edge_policy"])
                    comod_rows = read_csv_rows(zf, required["comod_csv"])
                    bins_rows = read_csv_rows(zf, required["bins_csv"])
                    dynamic_rows = read_csv_rows(zf, required["dynamic_csv"])
                    summary_rows = read_csv_rows(zf, required["summary_csv"])
                    combined_text = " ".join(
                        [
                            json.dumps(pac_summary, ensure_ascii=False),
                            json.dumps(scope_contract, ensure_ascii=False),
                            json.dumps(workflow, ensure_ascii=False),
                            load_text_from_zip(zf, f"{pac_prefix}/reproducibility/method_description.txt")
                            if f"{pac_prefix}/reproducibility/method_description.txt" in names
                            else "",
                        ]
                    )

                    comod_columns = set(comod_rows[0].keys()) if comod_rows else set()
                    bins_columns = set(bins_rows[0].keys()) if bins_rows else set()
                    dynamic_columns = set(dynamic_rows[0].keys()) if dynamic_rows else set()
                    summary_columns = set(summary_rows[0].keys()) if summary_rows else set()
                    effective_kwargs = effective_call.get("kwargs") or {}
                    workflow_steps = [str(item.get("name", "")).lower() for item in workflow.get("steps") or []]
                    phase_grid = frequency_grid.get("phase_bands_hz") or []
                    amp_grid = frequency_grid.get("amplitude_bands_hz") or []
                    max_amp_edge = max((float(item[1]) for item in amp_grid if isinstance(item, list) and len(item) >= 2), default=0.0)
                    nyquist = float(frequency_grid.get("nyquist_hz") or 0.0)

                    checks.update(
                        {
                            "pac_frequency_grid_present": status(bool(phase_grid and amp_grid), {"phase_bands_hz": phase_grid, "amplitude_bands_hz": amp_grid}),
                            "pac_frequency_grid_below_nyquist": status(bool(nyquist and max_amp_edge < nyquist), {"max_amp_edge": max_amp_edge, "nyquist_hz": nyquist}),
                            "pac_surrogate_method_present": status(bool(params.get("surrogate_method") and frequency_grid.get("surrogate_method") and effective_kwargs.get("surrogate_method")), {"parameters": params.get("surrogate_method"), "frequency_grid": frequency_grid.get("surrogate_method"), "effective_call": effective_kwargs.get("surrogate_method")}),
                            "pac_normalization_present": status(bool(params.get("normalization") and frequency_grid.get("normalization") and effective_kwargs.get("normalization")), {"parameters": params.get("normalization"), "frequency_grid": frequency_grid.get("normalization"), "effective_call": effective_kwargs.get("normalization")}),
                            "random_state_or_reproducibility_present": status(params.get("random_state") is not None and frequency_grid.get("random_state") is not None and effective_kwargs.get("random_state") is not None, {"parameters": params.get("random_state"), "frequency_grid": frequency_grid.get("random_state"), "effective_call": effective_kwargs.get("random_state")}),
                            "surrogate_columns_present": status({"surrogate_method", "n_surrogates", "surrogate_mean_mi", "surrogate_std_mi", "normalized_mi_z", "random_state"}.issubset(comod_columns), sorted(comod_columns)),
                            "phase_bin_table_present": status({"phase_bin_start_rad", "phase_bin_end_rad", "normalized_amplitude", "sample_count"}.issubset(bins_columns) and bool(bins_rows), sorted(bins_columns)),
                            "dynamic_curve_table_present": status({"window_start_sec", "window_end_sec", "mi_value"}.issubset(dynamic_columns) and bool(dynamic_rows), sorted(dynamic_columns)),
                            "channel_summary_present": status({"peak_phase_band", "peak_amp_band", "peak_mi", "warnings"}.issubset(summary_columns) and bool(summary_rows), sorted(summary_columns)),
                            "workflow_records_filter_hilbert_and_mi": status("filter_hilbert" in workflow_steps and "compute_mi" in workflow_steps, workflow_steps),
                            "filter_edge_policy_present": status(bool(filter_policy.get("filter_engine") and filter_policy.get("hilbert_engine")), filter_policy),
                            "source_or_sensor_space_label_present": status("sensor/channel space" in combined_text.lower() or "sensor-space" in combined_text.lower(), "sensor/channel space boundary scan"),
                            "inverse_method_absent_and_no_source_claim": status("inverse_method" not in params and "source localization" in combined_text.lower() and not has_forbidden_positive_claim(combined_text), "source/topomap forbidden claim scan"),
                            "forbidden_claim_scan_present": status(not has_forbidden_positive_claim(combined_text), "forbidden claim scan over summary/scope/workflow/method text"),
                            "beta_boundary_present": status(
                                "single-record" in combined_text.lower()
                                and "diagnosis" in combined_text.lower()
                                and "causality" in combined_text.lower()
                                and "source localization" in combined_text.lower(),
                                pac_summary.get("boundary") or scope_contract.get("boundary"),
                            ),
                        }
                    )

    blockers = [key for key, item in checks.items() if isinstance(item, dict) and item.get("status") == "block"]
    failures.extend(blockers)
    result = {
        "schema_version": "qlanalyser-round006-pac-real-report-consumption-v0.1",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not failures else "failed",
        "requirement_id": "VR-EO-0019",
        "scope": "real UI-only report ZIP consumption for PAC frequency grids, surrogate/normalization reproducibility, and source/topomap boundary evidence",
        "important_boundary": "This is PAC beta report artifact consumption evidence only; not stable promotion, statistical approval, or clinical/diagnostic approval.",
        "ui_evidence_path": str(EDF_UI_EVIDENCE),
        "report_zip_path": str(report_zip) if report_zip else None,
        "pac_prefix": pac_prefix,
        "checks": checks,
        "blockers": failures,
        "what_07_can_consume_next": [
            "Use this as the real-report counterpart to round_006 VR-EO-0019 for PAC boundary evidence.",
            "Keep PAC beta interpretation gated on frequency grids, surrogate method, normalization, random state, and source/topomap boundary wording.",
            "Do not use this checker as PAC stable promotion, group-statistics, clinical, or scientific pass decision.",
        ],
        "07A_SHORT_PACKET_METRICS": {
            "mini/script packet count": 1,
            "script packet used": "round_006 PAC real report consumption checker",
            "GPT-5.5 low-value work avoided": "ZIP entry inventory and field presence checks are scripted",
            "concurrency frontier": "single deterministic checker over latest UI-only report ZIP",
            "long-term platform asset produced": "real PAC report artifact validator adapter for VR-EO-0019",
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
