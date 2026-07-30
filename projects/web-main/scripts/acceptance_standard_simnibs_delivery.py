from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from simnibs_delivery import ContractError, validate_delivery  # noqa: E402


def expect_failure(payload: dict, expected: str) -> None:
    try:
        validate_delivery(payload)
    except ContractError as error:
        if expected not in str(error):
            raise AssertionError(f"Expected {expected!r} in {str(error)!r}") from error
    else:
        raise AssertionError(f"Expected contract failure containing {expected!r}")


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

    tms_payload = copy.deepcopy(payload)
    tms_payload["stimulation_modality"] = "tms"
    tms_payload["modules"] = {"tms": {"coil_model": "example-coil", "field_metric": "magnitude", "field_unit": "V/m", "coil_pose": {"center_mm": [0, 0, 0], "direction": [0, 1, 0]}}}
    validate_delivery(tms_payload)

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

    print(json.dumps({"status": "passed", "schema": payload["schema_version"], "figures": len(payload["figures"]), "roi_rows": len(payload["results"]["roi_metrics"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
