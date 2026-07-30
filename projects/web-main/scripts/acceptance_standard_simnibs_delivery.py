from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from simnibs_delivery import (  # noqa: E402
    ContractError,
    ProjectConfigError,
    render_report,
    validate_delivery,
    validate_project_config,
)


def expect_failure(payload: dict, expected: str) -> None:
    try:
        validate_delivery(payload)
    except ContractError as error:
        if expected not in str(error):
            raise AssertionError(f"Expected {expected!r} in {str(error)!r}") from error
    else:
        raise AssertionError(f"Expected contract failure containing {expected!r}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> None:
    output = ROOT / "outputs" / "simnibs_ti_violante2023_reproduction_20260729"
    payload = json.loads((output / "standard_report_data.json").read_text(encoding="utf-8"))
    validate_delivery(payload, root=output)

    duplicate_condition = copy.deepcopy(payload)
    duplicate_condition["protocol"]["conditions"].append(copy.deepcopy(duplicate_condition["protocol"]["conditions"][0]))
    expect_failure(duplicate_condition, "duplicate condition_id")

    unknown_metric = copy.deepcopy(payload)
    unknown_metric["results"]["roi_metrics"][0]["values"]["unsupported"] = 1
    expect_failure(unknown_metric, "unknown metrics")

    missing_module = copy.deepcopy(payload)
    missing_module["modules"] = {}
    expect_failure(missing_module, "active stimulation modality")

    invalid_ti_frequency = copy.deepcopy(payload)
    invalid_ti_frequency["modules"]["temporal_interference"]["beat_frequency_hz"] = 10
    expect_failure(invalid_ti_frequency, "carrier-frequency difference")

    tes_payload = copy.deepcopy(payload)
    tes_payload["stimulation_modality"] = "tes"
    tes_payload["modules"] = {"tes": {"primary_field": "normal", "current_unit": "mA", "field_unit": "V/m"}}
    validate_delivery(tes_payload)
    if "五、方法、质量控制与交付" not in render_report(tes_payload):
        raise AssertionError("tES payload did not render with the common report structure")

    tms_payload = copy.deepcopy(payload)
    tms_payload["stimulation_modality"] = "tms"
    tms_payload["modules"] = {"tms": {"coil_model": "example-coil", "field_metric": "magnitude", "field_unit": "V/m", "coil_pose": {"center_mm": [0, 0, 0], "direction": [0, 1, 0]}}}
    validate_delivery(tms_payload)
    if "五、方法、质量控制与交付" not in render_report(tms_payload):
        raise AssertionError("TMS payload did not render with the common report structure")

    ready_without_gate = copy.deepcopy(payload)
    ready_without_gate["project"]["service_status"] = "ready"
    expect_failure(ready_without_gate, "hard quality gate")

    ready_payload = copy.deepcopy(payload)
    ready_payload["project"]["service_status"] = "ready"
    ready_payload["quality_control"]["checks"][0]["hard_gate"] = True
    validate_delivery(ready_payload)

    ready_without_field = copy.deepcopy(ready_payload)
    ready_without_field["figures"] = [item for item in ready_without_field["figures"] if item["category"] != "field"]
    expect_failure(ready_without_field, "required figure categories")

    missing_figure = copy.deepcopy(payload)
    missing_figure["figures"][0]["image"] = "figures/png/not_found.png"
    try:
        validate_delivery(missing_figure, root=output)
    except ContractError as error:
        if "does not exist" not in str(error):
            raise
    else:
        raise AssertionError("Missing figure was accepted")

    report = (output / "report.html").read_text(encoding="utf-8")
    required = ["一、主要结论", "二、模型与刺激方案", "三、模拟结果", "四、结果解读", "五、方法、质量控制与交付"]
    if not all(item in report for item in required):
        raise AssertionError("The five-part report structure is incomplete")
    if "Violante 2023 复现" in report or "论文复现" in report:
        raise AssertionError("The service report is still framed as a paper reproduction")

    project_config = json.loads((ROOT / "docs" / "templates" / "SIMNIBS_SERVICE_PROJECT_EXAMPLE.json").read_text(encoding="utf-8"))
    validate_project_config(project_config)
    invalid_reference = copy.deepcopy(project_config)
    invalid_reference["references"][0]["defines_project_identity"] = True
    try:
        validate_project_config(invalid_reference)
    except ProjectConfigError as error:
        if "cannot define project identity" not in str(error):
            raise
    else:
        raise AssertionError("A reference was allowed to define project identity")

    manifest = json.loads((output / "standard_manifest.json").read_text(encoding="utf-8"))
    if not any(item["path"] == "publication_index.json" for item in manifest["generated_files"]):
        raise AssertionError("The publication figure index is missing from the standard manifest")
    for item in manifest["generated_files"]:
        path = output / item["path"]
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise AssertionError(f"Generated-file manifest mismatch: {item['path']}")
    for item in manifest["declared_artifacts"]:
        if item.get("sha256"):
            path = output / item["path"]
            if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
                raise AssertionError(f"Artifact manifest mismatch: {item['path']}")

    print(json.dumps({"status": "passed", "schema": payload["schema_version"], "figures": len(payload["figures"]), "roi_rows": len(payload["results"]["roi_metrics"]), "manifest_files": len(manifest["generated_files"]) + len(manifest["declared_artifacts"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
