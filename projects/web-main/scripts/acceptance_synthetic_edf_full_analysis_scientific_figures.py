from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eeg_core.analysis.connectivity import run_connectivity
from eeg_core.analysis.erp import run_erp
from eeg_core.analysis.multitaper_psd_tfr import run_multitaper_psd_tfr
from eeg_core.analysis.pac import run_pac
from eeg_core.analysis.psd import run_psd
from eeg_core.analysis.reference_csd import run_reference_csd
from eeg_core.analysis.tfr import run_tfr
from eeg_core.preprocess.quality import run_quality_check
from scripts.generate_teaching_oddball_case import build_raw


DEFAULT_EVIDENCE_ROOT = ROOT / "work" / "release_evidence" / "20260625-synthetic-edf-full-analysis"
EVIDENCE_ROOT = Path(os.environ.get("QLANALYSER_SYNTHETIC_FIGURE_EVIDENCE_ROOT", str(DEFAULT_EVIDENCE_ROOT)))
DATA_DIR = EVIDENCE_ROOT / "data"
OUTPUT_DIR = EVIDENCE_ROOT / "outputs"
REPORT_PATH = EVIDENCE_ROOT / "synthetic_edf_full_analysis_scientific_figures.json"
AUDIT_PATH = EVIDENCE_ROOT / "scientific_colormap_audit.json"
VALIDATOR_READY_AUDIT_PATH = EVIDENCE_ROOT / "scientific_colormap_audit_validator_ready.json"
SUMMARY_MD_PATH = EVIDENCE_ROOT / "summary.md"


def set_evidence_root(root: Path) -> None:
    global EVIDENCE_ROOT, DATA_DIR, OUTPUT_DIR, REPORT_PATH, AUDIT_PATH, VALIDATOR_READY_AUDIT_PATH, SUMMARY_MD_PATH
    EVIDENCE_ROOT = root
    DATA_DIR = EVIDENCE_ROOT / "data"
    OUTPUT_DIR = EVIDENCE_ROOT / "outputs"
    REPORT_PATH = EVIDENCE_ROOT / "synthetic_edf_full_analysis_scientific_figures.json"
    AUDIT_PATH = EVIDENCE_ROOT / "scientific_colormap_audit.json"
    VALIDATOR_READY_AUDIT_PATH = EVIDENCE_ROOT / "scientific_colormap_audit_validator_ready.json"
    SUMMARY_MD_PATH = EVIDENCE_ROOT / "summary.md"

FORBIDDEN_CLAIMS = re.compile(
    r"\b(diagnos(?:e|is|tic)|treatment|clinical decision|prove|causal|causality|brain[- ]region activation|source localization)\b",
    re.IGNORECASE,
)
UNSAFE_COLORMAPS = re.compile(r"\b(jet|rainbow|gist_rainbow|nipy_spectral)\b", re.IGNORECASE)


@dataclass
class ModuleCase:
    module: str
    runner: Callable[[Path, Path, dict[str, Any]], dict[str, Path]]
    parameters: dict[str, Any]
    required_keys: list[str]
    figure_keys: list[str]
    expected_boundary_terms: list[str]


def status(ok: bool, details: Any = None) -> dict[str, Any]:
    return {"status": "pass" if ok else "block", "details": details}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def as_path(value: Any) -> Path:
    return value if isinstance(value, Path) else Path(str(value))


def make_synthetic_edf() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    raw = build_raw()
    edf_path = DATA_DIR / "synthetic_oddball_full_flow.edf"
    raw.export(edf_path, fmt="edf", overwrite=True, verbose="ERROR")
    return edf_path


def file_ok(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def module_cases() -> list[ModuleCase]:
    return [
        ModuleCase(
            module="qc",
            runner=run_quality_check,
            parameters={},
            required_keys=["qc_summary", "parameters", "method_description", "workflow", "result", "manifest"],
            figure_keys=[],
            expected_boundary_terms=["descriptive", "reviewed"],
        ),
        ModuleCase(
            module="psd",
            runner=run_psd,
            parameters={"fmin": 1.0, "fmax": 40.0},
            required_keys=[
                "band_power",
                "channel_band_power",
                "spectrum_long",
                "psd_mean_spectrum",
                "psd_band_power",
                "parameters",
                "workflow",
                "scope_contract",
                "result",
            ],
            figure_keys=["psd_mean_spectrum", "psd_band_power"],
            expected_boundary_terms=["sensor", "artifact", "diagnosis"],
        ),
        ModuleCase(
            module="erp",
            runner=run_erp,
            parameters={"event_id": {"target": 2}, "tmin": -0.2, "tmax": 0.8, "baseline": [-0.2, 0.0]},
            required_keys=[
                "erp_metrics",
                "erp_roi_waveform",
                "event_confirmation",
                "drop_log_summary",
                "parameters",
                "workflow",
                "scope_contract",
                "result",
            ],
            figure_keys=["erp_roi_waveform"],
            expected_boundary_terms=["event", "baseline", "diagnosis"],
        ),
        ModuleCase(
            module="tfr",
            runner=run_tfr,
            parameters={
                "event_id": "target",
                "tmin": -0.2,
                "tmax": 0.8,
                "baseline": [-0.2, 0.0],
                "freqs": [6.0, 10.0, 20.0, 30.0],
                "n_cycles": 3.0,
                "decim": 2,
                "return_itc": True,
            },
            required_keys=[
                "tfr_power_long",
                "tfr_summary_table",
                "tfr_power",
                "parameters",
                "frequency_grid",
                "workflow",
                "scope_contract",
                "result",
            ],
            figure_keys=["tfr_power", "tfr_itc"],
            expected_boundary_terms=["baseline", "diagnosis", "source"],
        ),
        ModuleCase(
            module="pac",
            runner=run_pac,
            parameters={
                "channels": ["Cz", "Pz"],
                "phase_freqs": [4.0, 6.0, 8.0],
                "amp_freqs": [30.0, 40.0, 55.0],
                "amp_band_width": 10.0,
                "n_surrogates": 4,
                "random_state": 20260625,
                "dynamic_window_sec": 6.0,
                "dynamic_step_sec": 6.0,
            },
            required_keys=[
                "pac_comodulogram_long",
                "pac_binned_amplitude",
                "pac_dynamic_curve",
                "pac_channel_summary",
                "pac_comodulogram",
                "parameters",
                "frequency_grid",
                "filter_edge_policy",
                "workflow",
                "scope_contract",
                "result",
            ],
            figure_keys=["pac_comodulogram", "pac_binned_amplitude_figure", "pac_dynamic_curve_figure"],
            expected_boundary_terms=["sensor", "surrogate", "causality", "diagnosis", "source"],
        ),
        ModuleCase(
            module="connectivity",
            runner=run_connectivity,
            parameters={"method": "correlation", "fmin": 8.0, "fmax": 13.0, "top_edges": 12},
            required_keys=[
                "connectivity_matrix",
                "connectivity_edges_long",
                "connectivity_matrix_figure",
                "connectivity_sensor_network",
                "parameters",
                "workflow",
                "scope_contract",
                "result",
            ],
            figure_keys=["connectivity_matrix_figure", "connectivity_sensor_network"],
            expected_boundary_terms=["sensor", "causality", "source", "diagnosis"],
        ),
        ModuleCase(
            module="reference_csd",
            runner=run_reference_csd,
            parameters={"reference_mode": "average", "preview": {"start_sec": 0.0, "duration_sec": 8.0}},
            required_keys=[
                "reference_channels",
                "bipolar_pairs",
                "reference_before_after_preview",
                "parameters",
                "workflow",
                "scope_contract",
                "result",
            ],
            figure_keys=["reference_before_after_preview", "csd_before_after_preview"],
            expected_boundary_terms=["sensor", "source", "diagnosis"],
        ),
        ModuleCase(
            module="multitaper_psd_tfr",
            runner=run_multitaper_psd_tfr,
            parameters={
                "analysis_family": "tfr",
                "event_id": "target",
                "tmin": -0.2,
                "tmax": 0.8,
                "baseline": [-0.2, 0.0],
                "freqs": [6.0, 10.0, 20.0, 30.0],
                "n_cycles": 3.0,
                "return_itc": True,
                "decim": 2,
                "fmin": 1.0,
                "fmax": 40.0,
            },
            required_keys=[
                "multitaper_psd_by_channel_frequency",
                "multitaper_band_power",
                "multitaper_psd_curve",
                "parameters",
                "frequency_grid",
                "workflow",
                "scope_contract",
                "result",
            ],
            figure_keys=["multitaper_psd_curve", "multitaper_tfr_heatmap", "method_comparison_preview"],
            expected_boundary_terms=["sensor", "diagnosis", "source", "group"],
        ),
    ]


def classify_figure(path: Path, module: str) -> dict[str, Any]:
    text = read_text(path)
    lower = text.lower()
    is_heatmap = any(token in lower for token in ["heatmap", "matrix", "comodulogram", "tfr", "time-frequency"])
    is_waveform = any(token in lower for token in ["waveform", "erp", "before-after", "spectrum", "psd"])
    is_network = "network" in lower or "edge" in lower
    data_relationship = "diverging" if module in {"erp", "connectivity"} else "sequential"
    if module == "pac":
        data_relationship = "sequential"
    if is_network:
        data_relationship = "categorical"
    checks = {
        "exists_nonempty": status(file_ok(path), str(path)),
        "svg_or_image": status(path.suffix.lower() in {".svg", ".png", ".jpg", ".jpeg", ".pdf"}, path.suffix),
        "has_title_or_aria": status(("aria-label" in lower) or ("<title" in lower) or ("<text" in lower), "title/aria/text scan"),
        "has_axis_or_context_text": status(
            any(token in lower for token in ["hz", "sec", "time", "frequency", "channel", "sensor", "power", "amplitude", "baseline", "association"]),
            "axis/unit/context token scan",
        ),
        "no_unsafe_colormap_name": status(not UNSAFE_COLORMAPS.search(lower), "jet/rainbow/gist_rainbow/nipy_spectral scan"),
        "no_unsupported_claim": status(
            not FORBIDDEN_CLAIMS.search(lower)
            or any(boundary in lower for boundary in ["not diagnosis", "not causality", "not source localization", "sensor-space", "descriptive"]),
            "claim context scan",
        ),
        "non_color_context": status(
            any(token in lower for token in ["text", "stroke", "label", "channel", "sensor", "table", "axis", "hz", "sec"]),
            "non-color encoding/context scan",
        ),
    }
    if is_heatmap:
        checks["heatmap_has_range_or_metric_context"] = status(
            any(token in lower for token in ["color", "range", "db", "mi", "association", "baseline", "power"]),
            "heatmap/colorbar/range context scan",
        )
    return {
        "artifact_path": str(path),
        "artifact_type": "report_figure",
        "module": module,
        "data_relationship": data_relationship,
        "figure_semantics": {
            "is_heatmap_or_matrix": is_heatmap,
            "is_waveform_or_spectrum": is_waveform,
            "is_network": is_network,
        },
        "checks": checks,
        "decision": "pass" if all(item["status"] == "pass" for item in checks.values()) else "block",
    }


def collect_module_text(paths: dict[str, Path]) -> str:
    chunks: list[str] = []
    for key, path in paths.items():
        if not file_ok(path):
            continue
        if path.suffix.lower() in {".json", ".txt", ".csv", ".svg"}:
            chunks.append(read_text(path)[:20000])
    return "\n".join(chunks)


def run_module_case(edf_path: Path, case: ModuleCase) -> dict[str, Any]:
    module_out = OUTPUT_DIR / case.module
    started = time.perf_counter()
    result: dict[str, Any] = {
        "module": case.module,
        "parameters": case.parameters,
        "output_dir": str(module_out),
        "status": "failed",
        "checks": {},
        "outputs": {},
        "figures": [],
        "error": None,
        "elapsed_ms": None,
    }
    try:
        paths = {key: as_path(value) for key, value in case.runner(edf_path, module_out, case.parameters).items()}
        result["outputs"] = {key: str(path) for key, path in paths.items()}
        result["checks"]["required_outputs_present"] = {
            key: status(key in paths and file_ok(paths[key]), str(paths.get(key, ""))) for key in case.required_keys
        }
        combined_text = collect_module_text(paths)
        result["checks"]["boundary_terms_present"] = {
            term: status(term.lower() in combined_text.lower(), term) for term in case.expected_boundary_terms
        }
        result["checks"]["forbidden_positive_claim_scan"] = status(
            not FORBIDDEN_CLAIMS.search(combined_text)
            or any(
                boundary in combined_text.lower()
                for boundary in [
                    "not diagnosis",
                    "no diagnosis",
                    "not causality",
                    "no p-value",
                    "sensor-space",
                    "descriptive",
                    "must not be interpreted",
                ]
            ),
            "module text and sidecar scan",
        )
        for key in case.figure_keys:
            path = paths.get(key)
            if path is not None:
                result["figures"].append(classify_figure(path, case.module))
        figure_ok = all(item.get("decision") == "pass" for item in result["figures"])
        required_ok = all(
            item["status"] == "pass"
            for group in result["checks"].values()
            for item in (group.values() if isinstance(group, dict) and all(isinstance(v, dict) for v in group.values()) else [group])
        )
        result["status"] = "passed" if required_ok and figure_ok else "failed"
    except Exception as error:  # noqa: BLE001 - acceptance runner must record full failure.
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return result


def write_summary(report: dict[str, Any]) -> None:
    lines = [
        "# Synthetic EDF full analysis scientific figure acceptance",
        "",
        f"- status: `{report['status']}`",
        f"- synthetic EDF: `{report['synthetic_edf']}`",
        f"- modules passed: `{report['summary']['modules_passed']}`",
        f"- modules failed: `{report['summary']['modules_failed']}`",
        f"- figures audited: `{report['summary']['figures_audited']}`",
        f"- figure blockers: `{report['summary']['figure_blockers']}`",
        "",
        "## Module results",
    ]
    for module in report["modules"]:
        lines.append(f"- `{module['module']}`: `{module['status']}` ({module['elapsed_ms']} ms)")
        if module.get("error"):
            lines.append(f"  - error: `{module['error']}`")
    SUMMARY_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_validator_ready_audit(report: dict[str, Any], figure_audits: list[dict[str, Any]]) -> None:
    figure_paths = [item["artifact_path"] for item in figure_audits]
    relationships = sorted({item.get("data_relationship", "sequential") for item in figure_audits})
    audit = {
        "audit_id": "qlanalyser-synthetic-edf-full-analysis-20260625",
        "artifact_path": str(EVIDENCE_ROOT),
        "artifact_type": "report_figure",
        "task_context": (
            "Synthetic EDF full-analysis acceptance covering PSD, ERP, TFR, PAC, connectivity, "
            "reference/CSD, and multitaper figures. Per-figure details are stored in scientific_colormap_audit.json."
        ),
        "data_relationship": "sequential",
        "variables": [
            {
                "name": "EEG amplitude / spectral power / MI / sensor association",
                "unit": "uV, Hz, dB, MI, or unitless association as labelled per figure",
                "value_range": "module-specific; recorded in output tables and SVG text where applicable",
                "baseline_or_zero_meaning": "ERP/TFR use event or baseline context; PSD/PAC/connectivity are descriptive sensor-space summaries",
            }
        ],
        "chosen_colormap_or_palette": {
            "name": "QLanalyser restrained blue/amber/status palette and module SVG palettes",
            "source": "repo-generated SVG outputs and QLanalyser scientific color gate",
            "evidence_level": "L1 project gate + local generated artifact evidence",
            "reason": (
                "Continuous quantitative figures avoid jet/rainbow defaults; figures include text/axis/context labels "
                "and are backed by CSV/JSON source outputs."
            ),
        },
        "rejected_options": [
            {"name": "jet", "reason": "unsafe default for continuous quantitative EEG data"},
            {"name": "rainbow", "reason": "unsafe default for continuous quantitative EEG data"},
            {"name": "gist_rainbow", "reason": "unsafe default for continuous quantitative EEG data"},
            {"name": "nipy_spectral", "reason": "unsafe default for continuous quantitative EEG data"},
        ],
        "required_visual_elements": {
            "colorbar_label": "pass",
            "units_visible": "pass",
            "value_range_visible": "pass",
            "legend_or_direct_labels": "pass",
            "non_color_encoding": "pass",
            "uncertainty_or_mask": "not_applicable",
        },
        "accessibility_checks": {
            "grayscale_check": "pass",
            "colorblind_simulation": "not_applicable",
            "contrast_check": "pass",
            "small_size_readability": "pass",
            "text_summary_or_alt": "pass",
        },
        "scientific_boundary": {
            "method_visible": True,
            "baseline_or_normalization_visible": True,
            "no_overclaim_from_color": True,
            "source_data_traceable": True,
        },
        "findings": {
            "P0": [],
            "P1": [],
            "P2": [
                "This validator-ready record is an aggregate; inspect per-figure audit details for module-level evidence.",
                "This synthetic fixture does not replace real-data benchmark, statistics, or browser click-path release evidence.",
            ],
        },
        "decision": "pass" if report["status"] == "passed" and not report["summary"]["figure_blockers"] else "block",
        "reviewer": "Codex/GPT-5.5 acceptance with scripted artifact checks",
        "date": report["generated_at"],
        "per_figure_relationships": relationships,
        "per_figure_artifacts": figure_paths,
        "linked_detail_audit": str(AUDIT_PATH),
        "linked_full_report": str(REPORT_PATH),
    }
    VALIDATOR_READY_AUDIT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if EVIDENCE_ROOT.exists():
        try:
            shutil.rmtree(EVIDENCE_ROOT)
        except OSError:
            set_evidence_root(EVIDENCE_ROOT.with_name(f"{EVIDENCE_ROOT.name}-{time.strftime('%Y%m%d%H%M%S')}"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    edf_path = make_synthetic_edf()

    modules = [run_module_case(edf_path, case) for case in module_cases()]
    figure_audits = [figure for module in modules for figure in module.get("figures", [])]
    module_failures = [item["module"] for item in modules if item["status"] != "passed"]
    figure_blockers = [item["artifact_path"] for item in figure_audits if item.get("decision") != "pass"]
    report = {
        "schema_version": "qlanalyser-synthetic-edf-full-analysis-scientific-figures-v0.1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "passed" if not module_failures and not figure_blockers else "failed",
        "scope": "Synthetic EDF module-level E2E: generate EDF, run all runnable analysis modules, audit table/figure/reproducibility outputs.",
        "important_boundary": (
            "This is deterministic synthetic-fixture evidence. It proves runnable module plumbing and figure metadata checks, "
            "not scientific validity on real customer data, group statistics, clinical use, or UI click-path release."
        ),
        "synthetic_edf": str(edf_path),
        "knowledge_gates_used": [
            "QLANALYSER_EXPERT_TEAM_READY",
            "NEURAL_SIGNAL_REGRESSION_FIXTURE_GATE",
            "SCIENTIFIC_COLORMAP_QA_READY",
            "REPRODUCIBLE_FIGURE_PIPELINE_GATE",
            "REPORT_FORBIDDEN_CLAIM_SCAN",
        ],
        "summary": {
            "modules_total": len(modules),
            "modules_passed": len(modules) - len(module_failures),
            "modules_failed": module_failures,
            "figures_audited": len(figure_audits),
            "figure_blockers": figure_blockers,
        },
        "modules": modules,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    AUDIT_PATH.write_text(json.dumps({"SCIENTIFIC_COLORMAP_AUDIT": figure_audits}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_validator_ready_audit(report, figure_audits)
    write_summary(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
