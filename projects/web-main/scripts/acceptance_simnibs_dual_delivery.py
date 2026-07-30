#!/usr/bin/env python3
"""Evidence-based release gate for paired SimNIBS forward/inverse deliveries."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ModuleNotFoundError:  # The bundled lightweight runtime does not include it.
    jsonschema = None


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "frontend" / "assets" / "simnibs-report.schema.json"
MANIFEST_EXCLUDED_RELATIVE_PATHS = {
    "manifest.json", "manifest.sha256", "delivery_root_sha256.txt", "dual_acceptance.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


class Audit:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def check(self, condition: bool, code: str, detail: str, *, severity: str = "P1") -> None:
        self.checks.append({
            "code": code,
            "status": "pass" if condition else "fail",
            "severity": severity,
            "detail": detail,
        })

    @property
    def failures(self) -> list[dict[str, Any]]:
        return [item for item in self.checks if item["status"] == "fail"]


def validate_schema(data: dict[str, Any], audit: Audit, label: str) -> None:
    if jsonschema is None:
        audit.check(
            False,
            f"{label}.schema",
            "jsonschema is required for Draft 2020-12 validation; acceptance fails closed",
            severity="P0",
        )
        return
    schema = load_json(SCHEMA_PATH)
    try:
        jsonschema.Draft202012Validator(schema).validate(data)
    except jsonschema.ValidationError as error:
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        audit.check(False, f"{label}.schema", f"Schema violation at {location}: {error.message}", severity="P0")
    else:
        audit.check(True, f"{label}.schema", "report_data.json conforms to simnibs.report.v1")


def validate_manifest(directory: Path, data: dict[str, Any], audit: Audit, label: str) -> None:
    manifest_path = directory / "manifest.json"
    audit.check(manifest_path.is_file(), f"{label}.manifest.exists", "manifest.json is present", severity="P0")
    if not manifest_path.is_file():
        return
    manifest = load_json(manifest_path)
    entries = manifest.get("files", [])
    audit.check(bool(entries), f"{label}.manifest.nonempty", "manifest contains file records", severity="P0")
    seen: set[str] = set()
    valid = True
    for entry in entries:
        rel = entry.get("path", "")
        if not rel or rel in seen:
            valid = False
            continue
        seen.add(rel)
        path = (directory / rel).resolve()
        try:
            path.relative_to(directory)
        except ValueError:
            valid = False
            continue
        if not path.is_file():
            valid = False
            continue
        if entry.get("bytes") != path.stat().st_size or str(entry.get("sha256", "")).upper() != sha256(path):
            valid = False
    audit.check(valid, f"{label}.manifest.integrity", "all manifest paths, sizes, and SHA-256 values match disk", severity="P0")
    disk_files = set()
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(directory).as_posix()
        if relative_path not in MANIFEST_EXCLUDED_RELATIVE_PATHS:
            disk_files.add(relative_path)
    audit.check(
        seen == disk_files,
        f"{label}.manifest.completeness",
        f"manifest and disk file sets match exactly (listed={len(seen)}, disk={len(disk_files)})",
        severity="P0",
    )
    manifest_digest = sha256(manifest_path)
    root_digest_path = directory / "delivery_root_sha256.txt"
    legacy_digest_path = directory / "manifest.sha256"
    root_digest_valid = False
    if root_digest_path.is_file():
        root_digest_valid = (
            root_digest_path.read_text(encoding="ascii").strip()
            == f"manifest.json  SHA256  {manifest_digest}"
        )
    elif legacy_digest_path.is_file():
        root_digest_valid = (
            legacy_digest_path.read_text(encoding="ascii").strip()
            == f"{manifest_digest}  manifest.json"
        )
    audit.check(
        root_digest_valid,
        f"{label}.manifest.detached_root",
        "the detached root digest matches the current manifest SHA-256",
        severity="P0",
    )
    audit.check(
        {"report.html", "report_data.json"}.issubset(seen),
        f"{label}.manifest.core_files",
        "manifest covers report.html and report_data.json",
        severity="P0",
    )

    artifact_valid = True
    for artifact in data.get("artifacts", []):
        rel = artifact.get("path", "")
        path = (directory / rel).resolve()
        try:
            path.relative_to(directory)
        except ValueError:
            artifact_valid = False
            continue
        if not rel or not path.is_file() or str(artifact.get("sha256", "")).upper() != sha256(path):
            artifact_valid = False
    audit.check(artifact_valid, f"{label}.artifacts.integrity", "all declared artifacts exist and match their SHA-256", severity="P0")


def validate_common(directory: Path, data: dict[str, Any], audit: Audit, label: str) -> None:
    audit.check(data.get("report", {}).get("status") == "ready", f"{label}.ready", "report status is ready", severity="P0")
    audit.check(bool(data.get("target")), f"{label}.target", "target ROI is explicitly defined", severity="P0")

    hard_gates = [gate for gate in data.get("quality_gates", []) if gate.get("hard_gate") is True]
    audit.check(len(hard_gates) >= 4, f"{label}.hard_gates.count", "at least four hard quality gates are present", severity="P0")
    audit.check(
        bool(hard_gates) and all(gate.get("status") == "pass" for gate in hard_gates),
        f"{label}.hard_gates.pass",
        "every hard quality gate passes",
        severity="P0",
    )

    roi_roles = {row.get("role") for row in data.get("results", {}).get("roi_metrics", [])}
    audit.check("目标区" in roi_roles, f"{label}.roi.target", "target ROI statistics are present", severity="P0")
    audit.check("非目标区" in roi_roles, f"{label}.roi.offtarget", "off-target statistics are present", severity="P1")

    figures = data.get("figures", [])
    figure_ids = [figure.get("id") for figure in figures]
    audit.check(len(figure_ids) == len(set(figure_ids)), f"{label}.figures.unique", "figure IDs are unique", severity="P0")
    figures_valid = True
    for figure in figures:
        src = figure.get("src")
        if not isinstance(src, str) or not src:
            figures_valid = False
            continue
        figure_path = (directory / src).resolve()
        try:
            figure_path.relative_to(directory)
        except ValueError:
            figures_valid = False
            continue
        if not (
            figure.get("run_id")
            and figure_path.is_file()
            and str(figure.get("alt", "")).strip()
        ):
            figures_valid = False
    audit.check(figures_valid, f"{label}.figures.traceable", "every figure has an existing source, alt text, and run_id", severity="P0")

    artifact_types = {str(item.get("type", "")).upper() for item in data.get("artifacts", [])}
    audit.check(bool(artifact_types & {"MSH", "NIFTI", "HDF5"}), f"{label}.field_data", "a machine-readable field artifact is delivered", severity="P0")
    audit.check("CSV" in artifact_types and "EXCEL" in artifact_types, f"{label}.secondary_analysis", "CSV and Excel outputs support secondary analysis", severity="P1")

    grouped_currents: dict[str, float] = {}
    electrodes = data.get("protocol", {}).get("electrodes", [])
    for electrode in electrodes:
        circuit = str(electrode.get("circuit") or "default")
        grouped_currents[circuit] = grouped_currents.get(circuit, 0.0) + float(electrode.get("current_ma", 0.0))
    conserved = bool(grouped_currents) and all(math.isclose(value, 0.0, abs_tol=1e-9) for value in grouped_currents.values())
    audit.check(conserved, f"{label}.current_conservation", f"per-circuit current sums are zero: {grouped_currents}", severity="P0")


def validate_forward(directory: Path, data: dict[str, Any], audit: Audit) -> None:
    label = "forward"
    audit.check(data.get("analysis_mode") in {"forward_single", "forward_compare"}, f"{label}.mode", "forward package declares a forward mode", severity="P0")
    required = {"model_registration", "stimulation_montage", "field_primary", "roi_distribution", "target_offtarget"}
    if data.get("stimulation_modality") == "temporal_interference":
        required |= {"field_e1", "field_e2", "field_surface", "field_3d"}
    figure_ids = {figure.get("id") for figure in data.get("figures", [])}
    audit.check(required.issubset(figure_ids), f"{label}.figure_set", f"required forward figures are present: {sorted(required)}", severity="P0")
    title = str(data.get("report", {}).get("title", ""))
    audit.check("逆向" not in title and "优化" not in title, f"{label}.title_mode", "forward title is not presented as inverse optimization", severity="P0")


def validate_inverse(directory: Path, data: dict[str, Any], audit: Audit) -> None:
    label = "inverse"
    audit.check(data.get("analysis_mode") == "inverse_optimization", f"{label}.mode", "inverse package declares inverse_optimization", severity="P0")
    optimization = data.get("optimization", {})
    audit.check(optimization.get("four_electrode_recompute_status") == "completed", f"{label}.four_electrode_recompute", "selected finite-library candidate completed a four-active-electrode FEM recomputation", severity="P0")
    audit.check(bool(optimization.get("four_electrode_recompute_run_id")), f"{label}.four_electrode_recompute_run_id", "four-electrode recomputation has a traceable run_id", severity="P0")
    provenance = optimization.get("search_strategy_provenance", {})
    audit.check(
        provenance.get("native_attempt_status") == "failed_before_optimization"
        and provenance.get("native_result_produced") is False,
        f"{label}.native_optimizer_outcome",
        "the failed native TesFlex attempt is machine-readable and does not claim an optimization result",
        severity="P0",
    )
    audit.check(
        provenance.get("fallback_strategy") == "manually declared finite candidate library"
        and provenance.get("global_optimum_claim_allowed") is False
        and len(provenance.get("candidate_bipolar_pairs", [])) >= 3,
        f"{label}.finite_library_provenance",
        "the manual finite-library fallback and its non-global scope are explicit",
        severity="P0",
    )
    report_text = (directory / "report.html").read_text(encoding="utf-8")
    audit.check(
        "TesFlexOptimization" in report_text
        and "人工预先声明" in report_text
        and "并非由 10-10 全部位置或 64 通道全部组合穷举得到" in report_text,
        f"{label}.customer_optimizer_boundary",
        "the customer report discloses the native optimizer failure and manual candidate-library scope",
        severity="P0",
    )
    solutions = optimization.get("solutions", [])
    audit.check(bool(solutions), f"{label}.solutions", "optimization solution records are present", severity="P0")
    solution_types = {str(item.get("solution_type") or item.get("type") or "").lower() for item in solutions}
    optimization_mode = str(optimization.get("optimization_mode") or optimization.get("mode") or "").lower()
    discrete_exhaustive = optimization_mode in {"discrete_exhaustive", "finite_exhaustive_enumeration"}
    if discrete_exhaustive:
        search_space = optimization.get("search_space", {})
        audit.check(bool(search_space), f"{label}.search_space", "finite discrete search space is explicit", severity="P0")
        audit.check(
            optimization.get("all_admissible_candidates_evaluated") is True,
            f"{label}.exhaustive_completion",
            "all admissible candidates in the declared finite library were evaluated",
            severity="P0",
        )
        audit.check(
            bool(optimization.get("candidate_ranking") or optimization.get("candidate_ranking_artifact")),
            f"{label}.candidate_ranking",
            "candidate ranking is delivered",
            severity="P0",
        )
        audit.check(
            not any("theor" in value or "continuous" in value or "理论" in value for value in solution_types),
            f"{label}.no_fabricated_theoretical_solution",
            "discrete exhaustive report does not present an unavailable continuous/theoretical solution",
            severity="P0",
        )
        audit.check(
            any("candidate" in value or "finite" in value or "discrete" in value for value in solution_types),
            f"{label}.discrete_candidate",
            "a finite-library/discrete candidate is reported",
            severity="P0",
        )
    else:
        audit.check(
            any("theor" in value or "continuous" in value or "理论" in value for value in solution_types),
            f"{label}.theoretical_solution",
            "a theoretical/continuous solution is reported",
            severity="P1",
        )
    device_validated = data.get("protocol", {}).get("device_executability_validated") is True
    executable_labels = any("execut" in value or "device" in value or "可执行" in value for value in solution_types)
    audit.check(
        device_validated or not executable_labels,
        f"{label}.device_executability_label",
        "solution labels do not claim device executability unless it was validated",
        severity="P0",
    )
    figure_ids = {figure.get("id") for figure in data.get("figures", [])}
    publication_context = {
        "model_target_registration",
        "stimulation_montage",
        "carrier_and_timax_field",
        "field_surface",
        "four_electrode_quantitative",
        "four_electrode_recompute",
    }
    required = publication_context | ({"candidate_ranking"} if discrete_exhaustive else {"optimization_convergence", "theory_executable"})
    audit.check(required.issubset(figure_ids), f"{label}.figure_set", f"required inverse figures are present: {sorted(required)}", severity="P0")
    artifact_paths = {str(item.get("path", "")) for item in data.get("artifacts", [])}
    required_machine_artifacts = {
        "independent_fem/independent_timax_recompute.npz",
        "independent_fem/four_electrode_timax_T1grid.nii.gz",
        "independent_fem/ernie_TDCS_1_scalar.msh",
        "independent_fem/ernie_TDCS_2_scalar.msh",
        "tables/candidate_ranking.csv",
        "tables/inverse_ti_results.xlsx",
    }
    audit.check(
        required_machine_artifacts.issubset(artifact_paths),
        f"{label}.publication_machine_artifacts",
        "final E1/E2/TImax fields, candidate ranking, and secondary-analysis workbook are declared",
        severity="P0",
    )
    artifact_run_ids = {
        str(item.get("path", "")): str(item.get("run_id", ""))
        for item in data.get("artifacts", [])
    }
    recompute_run_id = str(optimization.get("four_electrode_recompute_run_id") or "")
    search_run_ids = {
        str(item.get("run_id", ""))
        for item in data.get("results", {}).get("search_stage_roi_metrics", [])
        if item.get("run_id")
    }
    recompute_artifacts = {
        path: artifact_run_ids.get(path)
        for path in artifact_paths
        if path.startswith("independent_fem/")
        or path.startswith("tables/four_electrode_")
        or path.startswith((
            "figures/fig00_",
            "figures/fig06_",
            "figures/fig07_",
            "figures/fig08_",
            "figures/figure_data/fig00_",
        ))
    }
    audit.check(
        bool(recompute_run_id)
        and bool(recompute_artifacts)
        and all(value == recompute_run_id for value in recompute_artifacts.values()),
        f"{label}.recompute_artifact_run_ids",
        "four-electrode recomputation artifacts and final-result figures use the recomputation run_id",
        severity="P0",
    )
    search_artifacts = {
        path: artifact_run_ids.get(path)
        for path in artifact_paths
        if path.startswith("raw/fields/")
        or path.startswith((
            "figures/fig01_",
            "figures/fig02_",
            "figures/fig03_",
            "figures/fig04_",
            "figures/fig05_",
        ))
    }
    audit.check(
        len(search_run_ids) == 1
        and bool(search_artifacts)
        and all(value in search_run_ids for value in search_artifacts.values()),
        f"{label}.search_artifact_run_ids",
        "candidate-search fields and figures use the finite-search run_id",
        severity="P0",
    )
    cross_stage = data.get("results", {}).get("cross_stage_comparison", {})
    cross_stage_metrics = {
        str(item.get("metric", "")): item
        for item in cross_stage.get("metrics", [])
        if isinstance(item, dict)
    }
    required_cross_stage_metrics = {
        "target_roi_mean_v_per_m",
        "off_target_mean_v_per_m",
        "target_to_off_target_mean_ratio",
    }
    cross_stage_complete = required_cross_stage_metrics == set(cross_stage_metrics)
    if cross_stage_complete:
        cross_stage_complete = all(
            isinstance(item.get("search_stage"), (int, float))
            and isinstance(item.get("four_electrode_recompute"), (int, float))
            and isinstance(item.get("relative_change_pct"), (int, float))
            for item in cross_stage_metrics.values()
        )
    interpretation = str(cross_stage.get("interpretation", "")).lower()
    cross_stage_boundary_complete = (
        cross_stage.get("comparison_type") == "cross_stage_descriptive"
        and cross_stage.get("causal_attribution_status") == "not_identifiable"
        and cross_stage.get("calibration_error_comparability") == "not_comparable_search_stage_summary_missing"
        and cross_stage.get("configuration_effect_inference_allowed") is False
        and cross_stage.get("robustness_inference_allowed") is False
        and len(cross_stage.get("confounding_factors", [])) >= 3
        and "cannot be separated" in interpretation
        and "cannot be attributed" in interpretation
        and "configuration sensitivity" not in interpretation
    )
    audit.check(
        cross_stage_complete and cross_stage_boundary_complete,
        f"{label}.cross_stage_comparison",
        "cross-stage changes are machine-readable and explicitly disallow configuration or robustness attribution when calibration evidence is not comparable",
        severity="P0",
    )
    numerical_validity = data.get("results", {}).get("numerical_field_validity", {})
    numerical_validity_complete = (
        data.get("results", {}).get("value_of_record_status")
        == "demo_only_electrical_independence_not_established"
        and numerical_validity.get("electrical_independence_established") is False
        and numerical_validity.get("local_shunting_may_affect_e1_e2_timax") is True
        and numerical_validity.get("values_citable_for_formal_research") is False
        and set(numerical_validity.get("affected_outputs", []))
        == {"E1", "E2", "TImax", "regional_statistics", "threshold_coverage"}
        and "positive F5-FC3 clearance" in numerical_validity.get("replacement_requirement", "")
        and "both carrier solves" in numerical_validity.get("replacement_requirement", "")
    )
    audit.check(
        numerical_validity_complete,
        f"{label}.electrical_independence_value_boundary",
        "point contact explicitly invalidates formal citation of E1, E2, TImax and derived statistics until positive clearance and both carrier re-solves are complete",
        severity="P0",
    )
    report_text = (directory / "report.html").read_text(encoding="utf-8")
    audit.check(
        all(term in report_text for term in ("搜索阶段目标/靶外均值比", "靶外均值增加", "均值比下降", "不能与运行间校准偏差分离", "不能归因于电极构型"))
        and "构型敏感性" not in report_text,
        f"{label}.cross_stage_customer_disclosure",
        "the customer report discloses all cross-stage changes and prevents configuration attribution",
        severity="P1",
    )
    audit.check(
        all(term in report_text for term in (
            "两个载波回路的电气独立性未建立",
            "局部分流可能影响 E1、E2、TImax",
            "0.2614 V/m、2.350 和覆盖率",
            "不得作为正式研究结果引用",
            "重新网格",
            "重新求解",
        )),
        f"{label}.electrical_independence_customer_disclosure",
        "the customer report explicitly blocks formal citation of affected field values and derived statistics until remeshing and both carrier re-solves",
        severity="P0",
    )
    audit.check(bool(optimization.get("objective") or optimization.get("objective_function")), f"{label}.objective", "optimization objective is explicit", severity="P0")
    audit.check(bool(optimization.get("constraints")), f"{label}.constraints", "device and safety constraints are explicit", severity="P0")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forward-dir", required=True, type=Path)
    parser.add_argument("--inverse-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    forward_dir = args.forward_dir.resolve()
    inverse_dir = args.inverse_dir.resolve()
    audit = Audit()
    audit.check(forward_dir != inverse_dir, "pair.separate_directories", "forward and inverse packages use separate directories", severity="P0")

    packages: dict[str, tuple[Path, dict[str, Any]]] = {}
    for label, directory in (("forward", forward_dir), ("inverse", inverse_dir)):
        report_path = directory / "report_data.json"
        audit.check(report_path.is_file(), f"{label}.report_data.exists", "report_data.json is present", severity="P0")
        if report_path.is_file():
            packages[label] = (directory, load_json(report_path))

    if len(packages) == 2:
        forward = packages["forward"][1]
        inverse = packages["inverse"][1]
        audit.check(
            forward.get("report", {}).get("report_id") != inverse.get("report", {}).get("report_id"),
            "pair.distinct_report_ids",
            "forward and inverse reports have distinct report IDs",
            severity="P0",
        )
        audit.check(
            sha256(forward_dir / "report_data.json") != sha256(inverse_dir / "report_data.json"),
            "pair.distinct_payloads",
            "forward and inverse report payloads are not duplicated",
            severity="P0",
        )
        for label, (directory, data) in packages.items():
            validate_schema(data, audit, label)
            validate_common(directory, data, audit, label)
            validate_manifest(directory, data, audit, label)
        validate_forward(*packages["forward"], audit)
        validate_inverse(*packages["inverse"], audit)

    result = {
        "status": "passed" if not audit.failures else "failed",
        "forward_dir": str(forward_dir),
        "inverse_dir": str(inverse_dir),
        "checks": audit.checks,
        "failure_count": len(audit.failures),
        "failures": audit.failures,
    }
    output = args.output or (inverse_dir.parent / "simnibs_dual_delivery_acceptance.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "failure_count": result["failure_count"], "output": str(output)}, ensure_ascii=False))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
