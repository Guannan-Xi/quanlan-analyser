from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = (
    ROOT
    / "work"
    / "release_evidence"
    / "20260623-module-lab-all-scope-runner"
    / "module_lab_live_runner_all_2026-06-23-0725.json"
)
OUTPUT = (
    ROOT
    / "work"
    / "release_evidence"
    / "20260623-module-lab-all-scope-runner"
    / "acceptance_module_lab_all_scope_evidence.json"
)

EXPECTED_MODULES = {
    "qc": "metadata_qc",
    "psd": "resting_psd",
    "erp": "erp_p300",
    "tfr": "tfr_ersp_itc",
    "pac": "pac_cfc",
    "reference_csd": "reference_csd",
    "multitaper_psd_tfr": "multitaper_psd_tfr",
    "connectivity": "connectivity",
}


def main() -> int:
    evidence_path = Path(os.environ.get("QLANALYSER_MODULE_LAB_ALL_SCOPE_EVIDENCE", DEFAULT_EVIDENCE))
    failures: list[str] = []
    payload: dict[str, object] = {}

    if not evidence_path.exists():
        failures.append(f"missing evidence file: {evidence_path}")
    else:
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))

    checks = payload.get("checks", {}) if isinstance(payload, dict) else {}
    module_checks = payload.get("moduleChecks", {}) if isinstance(payload, dict) else {}
    screenshot = payload.get("screenshot") if isinstance(payload, dict) else None

    if payload.get("status") != "passed":
        failures.append("runner status is not passed")
    if payload.get("moduleScope") != "all":
        failures.append("moduleScope is not all")
    if checks.get("taskPostCount") != len(EXPECTED_MODULES):
        failures.append(f"taskPostCount is not {len(EXPECTED_MODULES)}")
    if checks.get("singleUpload") is not True:
        failures.append("runner did not prove single upload")
    if checks.get("customerFileSelected") is not True or checks.get("uploadedFileSelected") is not True:
        failures.append("runner did not prove uploaded customer file selection")
    if checks.get("dataPreparationSectionVisible") is not True:
        failures.append("data preparation section not visible")
    if checks.get("stableAnalysisSectionVisible") is not True:
        failures.append("stable analysis section not visible")
    if checks.get("betaSectionVisible") is not True:
        failures.append("beta section not visible")
    if checks.get("qcSeparatedFromStableAnalysis") is not True:
        failures.append("QC is not separated from stable analysis")
    if checks.get("stableAnalysisContainsPsdErp") is not True:
        failures.append("stable analysis does not contain PSD/ERP")
    if checks.get("betaLabSeparated") is not True:
        failures.append("beta lab is not separated")
    if payload.get("errors") != []:
        failures.append("runner errors array is not empty")

    for module_id, workflow in EXPECTED_MODULES.items():
        module = module_checks.get(module_id)
        if not isinstance(module, dict):
            failures.append(f"missing module check: {module_id}")
            continue
        if module.get("workflow") != workflow:
            failures.append(f"{module_id} workflow mismatch")
        if module.get("workflowMatches") is not True:
            failures.append(f"{module_id} workflowMatches is not true")
        if module.get("taskUsesSelectedFile") is not True:
            failures.append(f"{module_id} task did not use selected uploaded file")
        if module.get("completed") is not True:
            failures.append(f"{module_id} task did not complete")
        if module.get("parametersVisible") is not True:
            failures.append(f"{module_id} parameters are not visible in result")
        if not module.get("createdTaskId"):
            failures.append(f"{module_id} missing createdTaskId")
        if module.get("passed") is not True:
            failures.append(f"{module_id} module check did not pass")

    if not screenshot:
        failures.append("missing screenshot path")
    elif not Path(str(screenshot)).exists():
        failures.append(f"screenshot file missing: {screenshot}")

    result = {
        "status": "passed" if not failures else "failed",
        "evidence": str(evidence_path),
        "screenshot": screenshot,
        "expected_modules": EXPECTED_MODULES,
        "task_post_count": checks.get("taskPostCount"),
        "errors": payload.get("errors") if isinstance(payload, dict) else None,
        "failures": failures,
        "boundary": "All-scope module-lab UI evidence proves local click-runner coverage only; it is not production/public-cloud release approval.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
