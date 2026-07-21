from __future__ import annotations

import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "work" / "release_evidence" / "20260621-module-review-objects"
PACK = OUT_DIR / "module_virtual_review_pack.v0.1.1-draft.json"
CHECKLISTS = OUT_DIR / "module_artifact_validator_checklists.json"
SCHEMA = Path(r"D:\QuanLanKnowledgeBase\library\qlanalyser\virtual-reviewer\schemas\virtual_reviewer_pack.schema.v0.1.1.json")
ACCEPTANCE_OUT = OUT_DIR / "acceptance_module_virtual_review_objects.json"


def main() -> int:
    pack = json.loads(PACK.read_text(encoding="utf-8"))
    checklists = json.loads(CHECKLISTS.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(pack, schema)

    expected_count = 12
    failures: list[str] = []
    for key in ["interaction_test_cases", "fixture_requirements", "expected_output_requirements"]:
        if len(pack.get(key, [])) != expected_count:
            failures.append(f"{key}_count:{len(pack.get(key, []))}")
    if checklists.get("module_count") != expected_count:
        failures.append(f"checklist_count:{checklists.get('module_count')}")

    interaction_modules = _module_ids_from_interactions(pack["interaction_test_cases"])
    checklist_modules = {item["module_id"] for item in checklists.get("checklists", [])}
    if interaction_modules != checklist_modules:
        failures.append("interaction_and_checklist_module_ids_mismatch")

    text = json.dumps(pack, ensure_ascii=False).lower()
    required_boundaries = [
        "not for clinical diagnosis",
        "beta and draft lifecycle modules must remain disabled",
        "source localization",
        "causality",
    ]
    for phrase in required_boundaries:
        if phrase not in text:
            failures.append(f"boundary_phrase_missing:{phrase}")

    for case in pack["interaction_test_cases"]:
        if not {"click", "upload", "wait", "screenshot", "download", "artifact_inspect"}.issubset(
            {step["action"] for step in case["steps"]}
        ):
            failures.append(f"runner_step_coverage_missing:{case['task_id']}")

    payload = {
        "status": "passed" if not failures else "failed",
        "pack": str(PACK),
        "checklists": str(CHECKLISTS),
        "schema": str(SCHEMA),
        "interaction_count": len(pack["interaction_test_cases"]),
        "fixture_count": len(pack["fixture_requirements"]),
        "expected_output_count": len(pack["expected_output_requirements"]),
        "checklist_count": checklists.get("module_count"),
        "module_ids": sorted(interaction_modules),
        "failures": failures,
    }
    ACCEPTANCE_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


def _module_ids_from_interactions(cases: list[dict]) -> set[str]:
    modules: set[str] = set()
    for case in cases:
        validators = case.get("artifact_validators") or []
        for validator in validators:
            if validator.startswith("artifact_validator_checklists:"):
                modules.add(validator.split(":", 1)[1])
    return modules


if __name__ == "__main__":
    raise SystemExit(main())
