from __future__ import annotations

import argparse
import csv
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any


REQUIRED_TABLES = {
    "tables/pac_comodulogram_long.csv": ["file_id", "prep_plan_id", "epoch_set_id", "channel", "channel_group", "phase_fmin", "phase_fmax", "amp_fmin", "amp_fmax", "metric", "mi_value", "n_samples", "unit"],
    "tables/pac_binned_amplitude.csv": ["channel", "phase_bin_index", "phase_bin_start_rad", "phase_bin_end_rad", "mean_amplitude", "normalized_amplitude", "sample_count"],
    "tables/pac_dynamic_curve.csv": ["channel", "window_start_sec", "window_end_sec", "phase_band_label", "amp_band_label", "metric", "mi_value"],
    "tables/pac_channel_summary.csv": ["channel", "channel_group", "peak_phase_band", "peak_amp_band", "peak_mi", "data_coverage_sec", "warnings"],
}
REQUIRED_FIGURES = ["figures/pac_comodulogram.svg", "figures/pac_phase_bins.svg", "figures/pac_dynamic_curve.svg"]
REQUIRED_REPRO = [
    "reproducibility/parameters.json",
    "reproducibility/effective_call.json",
    "reproducibility/frequency_grid.json",
    "reproducibility/filter_edge_policy.json",
    "reproducibility/scope_contract.json",
    "reproducibility/table_dictionary.json",
]
REQUIRED_RESULT_FIELDS = ["schema_version", "module_id", "workflow_id", "input_file_id", "data_preparation_plan_id", "parameters_hash", "artifacts", "warnings"]
FORBIDDEN_TERMS = [
    "diagnosis",
    "treatment decision",
    "p-value",
    "p value",
    "significant",
    "significance",
    "group comparison",
    "group difference",
    "causal",
    "causality",
    "brain-region communication",
    "brain region communication",
    "source localization",
]
NEGATED_OR_BOUNDARY_MARKERS = [
    "no ",
    "not ",
    "without ",
    "forbidden",
    "not for clinical",
    "single-record descriptive",
    "does not",
    "must not",
    "do not",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def extract_if_zip(path: Path) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    if path.is_dir():
        return path, None
    temp = tempfile.TemporaryDirectory()
    with zipfile.ZipFile(path) as zf:
        zf.extractall(temp.name)
    return Path(temp.name), temp


def scan_forbidden(root: Path) -> list[dict[str, str]]:
    hits = []
    for path in root.rglob("*"):
        if path.suffix.lower() not in {".json", ".csv", ".txt", ".md", ".svg", ".html"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for term in FORBIDDEN_TERMS:
            start = 0
            while True:
                idx = text.find(term, start)
                if idx < 0:
                    break
                context = text[max(0, idx - 220) : min(len(text), idx + len(term) + 160)]
                guarded = any(marker in context for marker in NEGATED_OR_BOUNDARY_MARKERS)
                if not guarded:
                    hits.append({"file": str(path.relative_to(root)), "term": term, "context": context.strip()})
                start = idx + len(term)
    return hits


def validate(root: Path) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    checks: dict[str, Any] = {}

    result_path = root / "result.json"
    if not result_path.exists():
        failures.append({"code": "RESULT_JSON_MISSING", "detail": "result.json is required"})
        result = {}
    else:
        result = read_json(result_path)
    checks["module_id"] = result.get("module_id")
    checks["workflow_id"] = result.get("workflow_id")
    if result.get("module_id") != "pac_cfc":
        failures.append({"code": "MODULE_ID_INVALID", "detail": str(result.get("module_id"))})
    if result.get("workflow_id") != "pac_cfc_beta":
        failures.append({"code": "WORKFLOW_ID_INVALID", "detail": str(result.get("workflow_id"))})
    for field in REQUIRED_RESULT_FIELDS:
        if field not in result:
            failures.append({"code": "RESULT_FIELD_MISSING", "detail": field})

    for rel, columns in REQUIRED_TABLES.items():
        path = root / rel
        if not path.exists():
            failures.append({"code": "TABLE_MISSING", "detail": rel})
            continue
        headers, rows = csv_rows(path)
        missing = [column for column in columns if column not in headers]
        if missing:
            failures.append({"code": "TABLE_COLUMN_MISSING", "detail": f"{rel}: {missing}"})
        if not rows:
            failures.append({"code": "TABLE_EMPTY", "detail": rel})
        if rel == "tables/pac_comodulogram_long.csv":
            mi_values = [float(row["mi_value"]) for row in rows if row.get("mi_value")]
            if not mi_values or max(mi_values) <= 0:
                failures.append({"code": "MI_VALUES_EMPTY", "detail": rel})
            units = {row.get("unit") for row in rows}
            if not units or "" in units:
                failures.append({"code": "UNIT_MISSING", "detail": rel})

    for rel in REQUIRED_FIGURES + REQUIRED_REPRO:
        if not (root / rel).exists():
            failures.append({"code": "REQUIRED_FILE_MISSING", "detail": rel})

    params_path = root / "reproducibility" / "parameters.json"
    if params_path.exists():
        params = read_json(params_path)
        phase = params.get("phase_freqs") or []
        amp = params.get("amp_freqs") or []
        nyquist = None
        grid_path = root / "reproducibility" / "frequency_grid.json"
        if grid_path.exists():
            nyquist = read_json(grid_path).get("nyquist_hz")
        if phase and amp and max(phase) >= min(amp):
            failures.append({"code": "INVALID_FREQUENCY_ORDER", "detail": "phase frequencies must be lower than amplitude frequencies"})
        if nyquist is not None and amp and max(amp) >= float(nyquist):
            failures.append({"code": "AMP_FREQ_EXCEEDS_NYQUIST", "detail": f"amp max {max(amp)} >= nyquist {nyquist}"})
        for key in ["n_phase_bins", "filter_edge_padding_sec", "edge_trim_sec", "dynamic_window_sec", "dynamic_step_sec"]:
            if key not in params:
                failures.append({"code": "PARAMETER_MISSING", "detail": key})
        if int(params.get("n_phase_bins", 0)) < 6:
            failures.append({"code": "PHASE_BIN_COUNT_TOO_LOW", "detail": str(params.get("n_phase_bins"))})

    table_dictionary_path = root / "reproducibility" / "table_dictionary.json"
    if table_dictionary_path.exists():
        dictionary = read_json(table_dictionary_path)
        for rel, columns in REQUIRED_TABLES.items():
            defined = dictionary.get(rel) or {}
            missing = [column for column in columns if column not in defined]
            if missing:
                failures.append({"code": "TABLE_DICTIONARY_COLUMN_MISSING", "detail": f"{rel}: {missing}"})

    forbidden_hits = scan_forbidden(root)
    if forbidden_hits:
        failures.append({"code": "FORBIDDEN_CLAIM_HIT", "detail": json.dumps(forbidden_hits, ensure_ascii=False)})

    return {
        "schema_version": "qlanalyser-pac-beta-artifact-validator-v0.1",
        "verdict": "pass" if not failures else "fail",
        "root": str(root),
        "checks": checks,
        "failures": failures,
        "warnings": warnings,
        "boundary": "PAC beta artifact validation only; no clinical, causal, group, or significance conclusion is made.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", help="PAC beta artifact directory or ZIP")
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    root, temp = extract_if_zip(Path(args.artifact))
    try:
        result = validate(root)
    finally:
        if temp is not None:
            temp.cleanup()
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
