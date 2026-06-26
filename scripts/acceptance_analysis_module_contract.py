from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "modules" / "analysis_module_contract.md"
ROADMAP = ROOT / "docs" / "product" / "LONG_TERM_GOAL_AND_ONE_YEAR_ROADMAP.md"
OUTPUT = (
    ROOT
    / "work"
    / "release_evidence"
    / "20260620-v01-acceptance"
    / "acceptance_analysis_module_contract.json"
)


REQUIRED_CONTRACT_PHRASES = [
    "Research EEG analysis tool + CRO infrastructure, not medical software.",
    "Clinical diagnosis.",
    "module_id: stable_ascii_identifier",
    "parameters_schema:",
    "execution_contract:",
    "output_schema:",
    "artifact_manifest:",
    "report_mapping:",
    "acceptance_gates:",
    "deepseek_official_direct_required: true",
    "UI action -> POST /api/tasks -> task_service -> module runner -> artifacts -> report ZIP",
    "psd_bandpower",
    "erp_p300",
    "connectivity",
    "source_localization",
    "ai_interpretation",
]

REQUIRED_ROADMAP_PHRASES = [
    "Top-tier research EEG analysis tool + CRO infrastructure, not medical software.",
    "Pluggable analysis-method module system.",
    "Do not drift into medical diagnosis",
    "Do not hard-code one-off analysis flows when a module contract is needed.",
]


def missing_phrases(text: str, phrases: list[str]) -> list[str]:
    return [phrase for phrase in phrases if phrase not in text]


def main() -> int:
    contract_text = CONTRACT.read_text(encoding="utf-8") if CONTRACT.exists() else ""
    roadmap_text = ROADMAP.read_text(encoding="utf-8") if ROADMAP.exists() else ""
    missing_contract = missing_phrases(contract_text, REQUIRED_CONTRACT_PHRASES)
    missing_roadmap = missing_phrases(roadmap_text, REQUIRED_ROADMAP_PHRASES)

    checks = {
        "contract_exists": CONTRACT.exists(),
        "roadmap_exists": ROADMAP.exists(),
        "contract_required_phrases": not missing_contract,
        "roadmap_required_phrases": not missing_roadmap,
    }
    payload = {
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "contract": str(CONTRACT),
        "roadmap": str(ROADMAP),
        "missing_contract_phrases": missing_contract,
        "missing_roadmap_phrases": missing_roadmap,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
