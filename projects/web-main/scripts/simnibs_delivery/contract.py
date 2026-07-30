from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .modules import ModuleContractError, validate_active_module


SCHEMA_VERSION = "simnibs.delivery.v2"
ANALYSIS_MODES = {"forward_single", "forward_compare", "inverse_optimization", "group_analysis"}
MODALITIES = {"tes", "temporal_interference", "tms"}
REPORT_STATUSES = {"draft", "ready", "blocked"}
QC_STATUSES = {"pass", "warning", "fail", "not_assessed"}
FIGURE_CATEGORIES = {"anatomy", "protocol", "field", "quantitative", "localization", "robustness"}


class ContractError(ValueError):
    """Raised when a delivery payload violates the v2 contract."""


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{path} must be an object")
    return value


def _sequence(value: Any, path: str, *, allow_empty: bool = False) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ContractError(f"{path} must be an array")
    if not value and not allow_empty:
        raise ContractError(f"{path} must not be empty")
    return value


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{path} must be a non-empty string")
    return value.strip()


def validate_delivery(payload: Mapping[str, Any], root: Path | None = None) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {SCHEMA_VERSION!r}")
    if payload.get("analysis_mode") not in ANALYSIS_MODES:
        raise ContractError("analysis_mode is not supported")
    if payload.get("stimulation_modality") not in MODALITIES:
        raise ContractError("stimulation_modality is not supported")

    project = _mapping(payload.get("project"), "project")
    for key in ("project_id", "title", "scientific_question", "service_status"):
        _text(project.get(key), f"project.{key}")
    if project["service_status"] not in REPORT_STATUSES:
        raise ContractError("project.service_status is not supported")

    subject = _mapping(payload.get("subject"), "subject")
    for key in ("subject_id", "model_type", "image_source"):
        _text(subject.get(key), f"subject.{key}")

    targets = _sequence(payload.get("targets"), "targets")
    for index, target_value in enumerate(targets):
        target = _mapping(target_value, f"targets[{index}]")
        for key in ("target_id", "name", "role", "definition", "coordinate_space"):
            _text(target.get(key), f"targets[{index}].{key}")

    conditions = _sequence(_mapping(payload.get("protocol"), "protocol").get("conditions"), "protocol.conditions")
    condition_ids: set[str] = set()
    for index, condition_value in enumerate(conditions):
        condition = _mapping(condition_value, f"protocol.conditions[{index}]")
        condition_id = _text(condition.get("condition_id"), f"protocol.conditions[{index}].condition_id")
        if condition_id in condition_ids:
            raise ContractError(f"duplicate condition_id: {condition_id}")
        condition_ids.add(condition_id)
        _text(condition.get("label"), f"protocol.conditions[{index}].label")
        _sequence(condition.get("channels"), f"protocol.conditions[{index}].channels")

    results = _mapping(payload.get("results"), "results")
    _sequence(results.get("headline_findings"), "results.headline_findings")
    metric_definitions = _mapping(results.get("metric_definitions"), "results.metric_definitions")
    metric_ids = set(metric_definitions)
    for metric_id, definition_value in metric_definitions.items():
        definition = _mapping(definition_value, f"results.metric_definitions.{metric_id}")
        for key in ("label", "unit", "definition"):
            _text(definition.get(key), f"results.metric_definitions.{metric_id}.{key}")

    for index, row_value in enumerate(_sequence(results.get("roi_metrics"), "results.roi_metrics")):
        row = _mapping(row_value, f"results.roi_metrics[{index}]")
        if row.get("condition_id") not in condition_ids:
            raise ContractError(f"results.roi_metrics[{index}].condition_id is unknown")
        _text(row.get("target_id"), f"results.roi_metrics[{index}].target_id")
        values = _mapping(row.get("values"), f"results.roi_metrics[{index}].values")
        unknown_metrics = set(values) - metric_ids
        if unknown_metrics:
            raise ContractError(f"results.roi_metrics[{index}] uses unknown metrics: {sorted(unknown_metrics)}")

    qc = _mapping(payload.get("quality_control"), "quality_control")
    checks = _sequence(qc.get("checks"), "quality_control.checks")
    for index, check_value in enumerate(checks):
        check = _mapping(check_value, f"quality_control.checks[{index}]")
        _text(check.get("name"), f"quality_control.checks[{index}].name")
        if check.get("status") not in QC_STATUSES:
            raise ContractError(f"quality_control.checks[{index}].status is not supported")
    _sequence(qc.get("limitations"), "quality_control.limitations")

    figure_ids: set[str] = set()
    for index, figure_value in enumerate(_sequence(payload.get("figures"), "figures")):
        figure = _mapping(figure_value, f"figures[{index}]")
        figure_id = _text(figure.get("figure_id"), f"figures[{index}].figure_id")
        if figure_id in figure_ids:
            raise ContractError(f"duplicate figure_id: {figure_id}")
        figure_ids.add(figure_id)
        if figure.get("category") not in FIGURE_CATEGORIES:
            raise ContractError(f"figures[{index}].category is not supported")
        for key in ("title", "conclusion", "image", "source_data"):
            _text(figure.get(key), f"figures[{index}].{key}")
        if root is not None:
            for key in ("image", "vector", "pdf", "source_data"):
                if figure.get(key) and not (root / figure[key]).is_file():
                    raise ContractError(f"figures[{index}].{key} does not exist: {figure[key]}")

    for index, artifact_value in enumerate(_sequence(payload.get("artifacts"), "artifacts")):
        artifact = _mapping(artifact_value, f"artifacts[{index}]")
        for key in ("path", "label", "purpose"):
            _text(artifact.get(key), f"artifacts[{index}].{key}")
        if root is not None and not artifact.get("generated_by_builder", False) and not (root / artifact["path"]).is_file():
            raise ContractError(f"artifacts[{index}].path does not exist: {artifact['path']}")
    modules = _mapping(payload.get("modules"), "modules")
    try:
        validate_active_module(payload["stimulation_modality"], modules)
    except ModuleContractError as error:
        raise ContractError(str(error)) from error

    if project["service_status"] == "ready":
        hard_gates = [check for check in checks if check.get("hard_gate", False)]
        if not hard_gates:
            raise ContractError("ready deliveries must declare at least one hard quality gate")
        failed_hard_gates = [check["name"] for check in hard_gates if check.get("status") != "pass"]
        if failed_hard_gates:
            raise ContractError(f"ready delivery has incomplete hard quality gates: {failed_hard_gates}")
        required_categories = {"anatomy", "protocol", "field", "quantitative"}
        delivered_categories = {figure["category"] for figure in payload["figures"]}
        missing_categories = required_categories - delivered_categories
        if missing_categories:
            raise ContractError(f"ready delivery is missing required figure categories: {sorted(missing_categories)}")
