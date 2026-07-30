from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


PROJECT_SCHEMA_VERSION = "simnibs.service-project.v1"
REFERENCE_ROLES = {"method_basis", "figure_requirements", "benchmark", "background"}
DELIVERABLES = {"html_report", "pdf_report", "publication_figures", "roi_tables", "nifti_fields", "mesh", "reproducibility"}


class ProjectConfigError(ValueError):
    pass


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectConfigError(f"{path} must be a non-empty string")
    return value.strip()


def _list(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ProjectConfigError(f"{path} must be a non-empty array")
    return value


def validate_project_config(config: Mapping[str, Any]) -> None:
    if config.get("schema_version") != PROJECT_SCHEMA_VERSION:
        raise ProjectConfigError(f"schema_version must be {PROJECT_SCHEMA_VERSION!r}")
    project = config.get("project")
    if not isinstance(project, Mapping):
        raise ProjectConfigError("project must be an object")
    for key in ("project_id", "title", "scientific_question", "customer_label"):
        _text(project.get(key), f"project.{key}")

    subject = config.get("subject")
    if not isinstance(subject, Mapping):
        raise ProjectConfigError("subject must be an object")
    for key in ("subject_id", "image_source", "model_type"):
        _text(subject.get(key), f"subject.{key}")

    for index, target in enumerate(_list(config.get("targets"), "targets")):
        if not isinstance(target, Mapping):
            raise ProjectConfigError(f"targets[{index}] must be an object")
        for key in ("target_id", "name", "role", "definition", "coordinate_space"):
            _text(target.get(key), f"targets[{index}].{key}")

    protocol = config.get("protocol")
    if not isinstance(protocol, Mapping):
        raise ProjectConfigError("protocol must be an object")
    if protocol.get("stimulation_modality") not in {"tes", "temporal_interference", "tms"}:
        raise ProjectConfigError("protocol.stimulation_modality is not supported")
    if protocol.get("analysis_mode") not in {"forward_single", "forward_compare", "inverse_optimization", "group_analysis"}:
        raise ProjectConfigError("protocol.analysis_mode is not supported")
    _list(protocol.get("conditions"), "protocol.conditions")

    deliverables = set(_list(config.get("requested_deliverables"), "requested_deliverables"))
    unsupported = deliverables - DELIVERABLES
    if unsupported:
        raise ProjectConfigError(f"requested_deliverables contains unsupported values: {sorted(unsupported)}")

    references = config.get("references", [])
    if not isinstance(references, Sequence) or isinstance(references, (str, bytes)):
        raise ProjectConfigError("references must be an array")
    for index, reference in enumerate(references):
        if not isinstance(reference, Mapping):
            raise ProjectConfigError(f"references[{index}] must be an object")
        _text(reference.get("citation"), f"references[{index}].citation")
        if reference.get("role") not in REFERENCE_ROLES:
            raise ProjectConfigError(f"references[{index}].role is not supported")
        if reference.get("defines_project_identity", False):
            raise ProjectConfigError("references may guide methods or outputs but cannot define project identity")
