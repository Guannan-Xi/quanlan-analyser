from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eeg_core.analysis.pac_v2 import run_pac_v2
from scripts.generate_teaching_oddball_case import build_raw


WORK = ROOT / "work" / "release_evidence" / "pac_v2_contract"
DATA = WORK / "data"
OUTPUT = WORK / "runner_output"
EVIDENCE_PATH = WORK / "acceptance_pac_v2_contract.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_file(path: Path, failures: list[str], label: str) -> None:
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        failures.append(f"missing_or_empty:{label}:{path}")


def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    DATA.mkdir(parents=True, exist_ok=True)
    raw = build_raw()
    fif_path = DATA / "pac_v2_sample_raw.fif"
    raw.save(fif_path, overwrite=True, verbose="ERROR")

    failures: list[str] = []
    paths = run_pac_v2(
        fif_path,
        OUTPUT,
        {
            "channels": ["Cz", "Pz"],
            "phase_freqs": [4, 6, 8],
            "amp_freqs": [30, 50, 70],
            "n_surrogates": 20,
            "time_window": {"start_sec": 0, "end_sec": 20},
        },
    )
    required = {
        "pac_v2_long",
        "pac_v2_channel_summary",
        "parameters",
        "method_description",
        "software_versions",
        "workflow",
        "parameter_schema_snapshot",
        "threshold_validation",
        "effective_call",
        "source_metadata",
        "table_dictionary",
        "scope_contract",
        "result",
        "manifest",
        "log",
    }
    for label in required:
        if label not in paths:
            failures.append(f"missing_label:{label}")
            continue
        _assert_file(Path(paths[label]), failures, label)

    result = _read_json(Path(paths["result"]))
    manifest = _read_json(Path(paths["manifest"]))
    table_dictionary = _read_json(Path(paths["table_dictionary"]))
    scope_contract = _read_json(Path(paths["scope_contract"]))

    result_text = json.dumps(result, ensure_ascii=False).lower()
    manifest_text = json.dumps(manifest, ensure_ascii=False).lower()
    if result.get("module_name") != "pac_v2":
        failures.append(f"result_module_mismatch:{result.get('module_name')}")
    if result.get("job_type") != "pac_v2_lab":
        failures.append(f"result_job_type_mismatch:{result.get('job_type')}")
    if "stable" in result_text or "stable" in manifest_text:
        failures.append("pac_v2_contract_must_not_contain_stable")
    if result.get("summary", {}).get("lifecycle_state") != "beta_lab_only":
        failures.append(f"pac_v2_lifecycle_not_beta_lab_only:{result.get('summary', {}).get('lifecycle_state')}")
    if manifest.get("schema_version") is None or "files" not in manifest:
        failures.append("manifest_not_standard_contract")
    if not {"schema_version", "module", "tables"}.issubset(table_dictionary):
        failures.append("table_dictionary_schema_missing_standard_shell")
    if table_dictionary.get("module") != "pac_v2":
        failures.append(f"table_dictionary_module_mismatch:{table_dictionary.get('module')}")
    if not isinstance(table_dictionary.get("tables"), dict) or "tables/pac_v2_long.csv" not in table_dictionary.get("tables", {}):
        failures.append("table_dictionary_missing_pac_v2_table")
    for field in ("analysis_scope", "disallowed_claims", "customer_boundary_note"):
        if not scope_contract.get(field):
            failures.append(f"scope_contract_missing:{field}")
    if scope_contract.get("stable_status") != "beta_lab_only":
        failures.append(f"scope_contract_status_mismatch:{scope_contract.get('stable_status')}")

    payload = {
        "status": "passed" if not failures else "failed",
        "runner_output": str(OUTPUT),
        "failures": failures,
        "checked_outputs": sorted(required),
        "result_lifecycle": result.get("summary", {}).get("lifecycle_state"),
        "scope_status": scope_contract.get("stable_status"),
    }
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
