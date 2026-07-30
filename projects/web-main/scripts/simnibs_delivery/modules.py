from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Callable


class ModuleContractError(ValueError):
    pass


def _text(module: Mapping[str, Any], key: str, modality: str) -> str:
    value = module.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ModuleContractError(f"modules.{modality}.{key} must be a non-empty string")
    return value


def _number(module: Mapping[str, Any], key: str, modality: str) -> float:
    value = module.get(key)
    if not isinstance(value, (int, float)):
        raise ModuleContractError(f"modules.{modality}.{key} must be numeric")
    return float(value)


def validate_temporal_interference(module: Mapping[str, Any]) -> None:
    _text(module, "primary_metric", "temporal_interference")
    _text(module, "secondary_metric", "temporal_interference")
    _text(module, "direction_source", "temporal_interference")
    frequencies = module.get("carrier_frequencies_hz")
    if not isinstance(frequencies, Sequence) or isinstance(frequencies, (str, bytes)) or len(frequencies) != 2:
        raise ModuleContractError("modules.temporal_interference.carrier_frequencies_hz must contain two frequencies")
    if not all(isinstance(value, (int, float)) and value > 0 for value in frequencies):
        raise ModuleContractError("modules.temporal_interference.carrier_frequencies_hz must be positive")
    beat = _number(module, "beat_frequency_hz", "temporal_interference")
    expected = abs(float(frequencies[0]) - float(frequencies[1]))
    if abs(beat - expected) > 1e-9:
        raise ModuleContractError("modules.temporal_interference.beat_frequency_hz must match the carrier-frequency difference")


def validate_tes(module: Mapping[str, Any]) -> None:
    primary_field = _text(module, "primary_field", "tes")
    if primary_field not in {"magnitude", "normal", "tangential"}:
        raise ModuleContractError("modules.tes.primary_field is not supported")
    _text(module, "current_unit", "tes")
    _text(module, "field_unit", "tes")


def validate_tms(module: Mapping[str, Any]) -> None:
    _text(module, "coil_model", "tms")
    _text(module, "field_metric", "tms")
    _text(module, "field_unit", "tms")
    pose = module.get("coil_pose")
    if not isinstance(pose, Mapping):
        raise ModuleContractError("modules.tms.coil_pose must be an object")
    center = pose.get("center_mm")
    direction = pose.get("direction")
    if not isinstance(center, Sequence) or len(center) != 3 or not all(isinstance(value, (int, float)) for value in center):
        raise ModuleContractError("modules.tms.coil_pose.center_mm must contain three numbers")
    if not isinstance(direction, Sequence) or len(direction) != 3 or not all(isinstance(value, (int, float)) for value in direction):
        raise ModuleContractError("modules.tms.coil_pose.direction must contain three numbers")


VALIDATORS: dict[str, Callable[[Mapping[str, Any]], None]] = {
    "temporal_interference": validate_temporal_interference,
    "tes": validate_tes,
    "tms": validate_tms,
}


def validate_active_module(modality: str, modules: Mapping[str, Any]) -> None:
    if modality not in modules:
        raise ModuleContractError("modules must include the active stimulation modality")
    module = modules[modality]
    if not isinstance(module, Mapping):
        raise ModuleContractError(f"modules.{modality} must be an object")
    VALIDATORS[modality](module)
