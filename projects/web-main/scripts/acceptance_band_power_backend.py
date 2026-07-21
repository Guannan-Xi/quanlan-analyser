import csv
import json
import shutil
import sys
from pathlib import Path

import mne
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eeg_core.analysis.band_power import run_band_power
from backend.services.product_catalog import ANALYSIS_TEMPLATES
from backend.services.task_service import WORKFLOW_TEMPLATES

WORK = ROOT / "work" / "release_evidence" / "band_power_backend"


def assert_ok(condition: bool, code: str, detail=None) -> None:
    if not condition:
        raise AssertionError(f"{code}: {detail}")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def make_low_sfreq_fixture(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sfreq = 80.0
    seconds = 12
    times = np.arange(int(sfreq * seconds)) / sfreq
    data = np.vstack(
        [
            8e-6 * np.sin(2 * np.pi * 10 * times),
            5e-6 * np.sin(2 * np.pi * 18 * times),
            3e-6 * np.sin(2 * np.pi * 32 * times),
        ]
    )
    info = mne.create_info(["Fz", "Cz", "Pz"], sfreq=sfreq, ch_types=["eeg", "eeg", "eeg"])
    raw = mne.io.RawArray(data, info, verbose="ERROR")
    raw.save(path, overwrite=True, verbose="ERROR")


def main() -> None:
    if WORK.exists():
        shutil.rmtree(WORK)
    fixture = WORK / "fixtures" / "band_power_80hz_raw.fif"
    output_dir = WORK / "outputs" / "band_power_80hz_default"
    make_low_sfreq_fixture(fixture)

    artifacts = run_band_power(fixture, output_dir, {})
    required_labels = {
        "band_power",
        "channel_band_power",
        "band_power_summary",
        "parameters",
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
    assert_ok(required_labels.issubset(artifacts), "BAND_POWER_ARTIFACT_LABELS_MISSING", sorted(artifacts))
    for label in required_labels:
        assert_ok(Path(artifacts[label]).exists(), "BAND_POWER_ARTIFACT_MISSING", {"label": label, "path": str(artifacts[label])})

    summary = read_json(Path(artifacts["band_power_summary"]))
    params = read_json(Path(artifacts["parameters"]))
    result = read_json(Path(artifacts["result"]))
    manifest = read_json(Path(artifacts["manifest"]))
    scope = read_json(Path(artifacts["scope_contract"]))
    threshold = read_json(Path(artifacts["threshold_validation"]))
    rows = read_csv_rows(Path(artifacts["band_power"]))

    assert_ok(result.get("module_name") == "band_power", "RESULT_MODULE_NOT_BAND_POWER", result)
    assert_ok(manifest.get("module_name") == "band_power", "MANIFEST_MODULE_NOT_BAND_POWER", manifest)
    assert_ok(scope.get("module") == "band_power", "SCOPE_MODULE_NOT_BAND_POWER", scope)
    assert_ok(scope.get("analysis_scope"), "SCOPE_ANALYSIS_SCOPE_MISSING", scope)
    assert_ok(isinstance(scope.get("disallowed_claims"), list) and scope["disallowed_claims"], "SCOPE_DISALLOWED_CLAIMS_MISSING", scope)
    assert_ok(threshold.get("status") == "passed", "THRESHOLD_VALIDATION_NOT_PASSED", threshold)

    included_bands = {row["band"] for row in rows}
    assert_ok("gamma_low" in included_bands, "GAMMA_LOW_SHOULD_BE_CLIPPED_NOT_DROPPED", rows)
    gamma = next(row for row in rows if row["band"] == "gamma_low")
    assert_ok(float(gamma["fmax"]) < 40.0, "GAMMA_LOW_FMAX_NOT_BELOW_NYQUIST", gamma)
    assert_ok(float(gamma["fmax"]) < 80.0 / 2.0, "GAMMA_LOW_FMAX_NOT_BELOW_80HZ_NYQUIST", gamma)

    notes = params.get("parameter_notes") or summary.get("parameter_notes") or {}
    excluded = params.get("excluded_bands") or summary.get("excluded_bands") or []
    adjusted = params.get("adjusted_bands") or summary.get("adjusted_bands") or []
    assert_ok(notes or excluded or adjusted, "BAND_POWER_BAND_ADJUSTMENT_NOT_RECORDED", {"params": params, "summary": summary})
    assert_ok(any(item.get("band") == "gamma_low" for item in adjusted), "GAMMA_LOW_ADJUSTMENT_NOT_RECORDED", adjusted)

    workflow_by_id = {item["id"]: item for item in WORKFLOW_TEMPLATES}
    catalog_by_id = {item["id"]: item for item in ANALYSIS_TEMPLATES}
    band_workflow = workflow_by_id.get("band_power")
    psd_workflow = workflow_by_id.get("resting_psd")
    band_catalog = catalog_by_id.get("band_power")
    psd_catalog = catalog_by_id.get("resting_psd")
    assert_ok(band_workflow and band_workflow.get("module") == "band_power", "BAND_POWER_WORKFLOW_NOT_INDEPENDENT", band_workflow)
    assert_ok(band_catalog and band_catalog.get("module") == "band_power", "BAND_POWER_CATALOG_NOT_INDEPENDENT", band_catalog)
    assert_ok("tables/band_power.csv" in set(band_workflow.get("outputs") or []), "BAND_POWER_WORKFLOW_OUTPUT_MISSING", band_workflow)
    assert_ok("tables/band_power.csv" in set(band_catalog.get("outputs") or []), "BAND_POWER_CATALOG_OUTPUT_MISSING", band_catalog)
    assert_ok("tables/band_power.csv" not in set(psd_workflow.get("outputs") or []), "PSD_WORKFLOW_STILL_DECLARES_BAND_POWER", psd_workflow)
    assert_ok("tables/band_power.csv" not in set(psd_catalog.get("outputs") or []), "PSD_CATALOG_STILL_DECLARES_BAND_POWER", psd_catalog)

    receipt = {
        "status": "passed",
        "fixture": str(fixture),
        "output_dir": str(output_dir),
        "gamma_low": gamma,
        "adjusted_bands": adjusted,
        "excluded_bands": excluded,
        "workflow_outputs": band_workflow.get("outputs"),
        "catalog_outputs": band_catalog.get("outputs"),
    }
    receipt_path = WORK / "acceptance_band_power_backend.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
