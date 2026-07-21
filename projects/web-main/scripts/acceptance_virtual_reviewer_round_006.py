from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = Path(
    r"D:\QuanLanKnowledgeBase\manifests\qlanalyser\virtual-reviewer-user-signals\packs\v0.1.1"
)
OUT_DIR = ROOT / "work" / "release_evidence" / "virtual_reviewer_round_006"
OUT_PATH = OUT_DIR / "round_006_dry_run.json"
FIXTURE_DIR = OUT_DIR / "synthetic_fixtures"


def read_jsonl(path: Path, key: str) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    items: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        identifier = payload.get(key) or payload.get("task_id") or payload.get("fixture_id") or payload.get("requirement_id")
        if identifier:
            items[str(identifier)] = payload
    return items


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def status_item(status: str, evidence: Any = None, detail: str | None = None) -> dict[str, Any]:
    item = {"status": status}
    if evidence is not None:
        item["evidence"] = evidence
    if detail:
        item["detail"] = detail
    return item


def has_any_claim(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def build_synthetic_fixtures() -> dict[str, Path]:
    fixtures = {
        "tfr_positive": {
            "schema_version": "qlanalyser-tfr-result-v0.1",
            "module_id": "tfr_ersp_itc",
            "measure_type": "power_and_itc",
            "method": "morlet_tfr",
            "frequencies": [4, 8, 13, 30],
            "times": [-0.2, 0.0, 0.3, 0.8],
            "baseline": [-0.2, 0.0],
            "correction": "logratio",
            "units": "dB change from baseline",
            "colorbar_label": "Power (dB); ITC unitless",
            "n_cycles": 7,
            "time_bandwidth": None,
            "decim": 2,
            "return_itc": True,
            "software_version": {"mne": "synthetic-fixture"},
            "warnings": ["Synthetic fixture for validator only; descriptive output."],
            "limitations": ["Single-record synthetic fixture; no statistical inference."],
            "caption_text": "Time-frequency power and ITC are descriptive outputs with baseline and units disclosed.",
        },
        "tfr_negative_missing_baseline": {
            "schema_version": "qlanalyser-tfr-result-v0.1",
            "module_id": "tfr_ersp_itc",
            "measure_type": "power",
            "method": "morlet_tfr",
            "frequencies": [4, 8, 13],
            "times": [0.0, 0.3, 0.8],
            "units": "",
            "caption_text": "This heatmap proves a significant neural effect.",
        },
        "connectivity_positive": {
            "schema_version": "qlanalyser-connectivity-result-v0.1",
            "module_id": "connectivity_sensor_method_design",
            "connectivity_method": "spectral_connectivity",
            "mode": "multitaper",
            "nodes": ["Fz", "Cz", "Pz"],
            "indices": [[0, 1], [1, 2]],
            "n_connections_or_n_nodes": 3,
            "n_freqs": 3,
            "frequency_bands": [{"name": "alpha", "fmin": 8, "fmax": 13}],
            "shape": [3, 3, 1],
            "space": "sensor",
            "threshold_policy": "display only; no inferential threshold",
            "limitations": ["Sensor-space association metric; descriptive matrix display only."],
            "caption_text": "Sensor-space coherence matrix with method, nodes, dimensions, and threshold policy disclosed.",
        },
        "connectivity_negative_causal": {
            "schema_version": "qlanalyser-connectivity-result-v0.1",
            "module_id": "connectivity_sensor_method_design",
            "connectivity_method": "",
            "nodes": [],
            "frequency_bands": [],
            "space": "sensor",
            "caption_text": "The frontal brain region sends information to parietal cortex and causes improved attention.",
        },
        "pac_source_positive": {
            "schema_version": "qlanalyser-pac-source-boundary-v0.1",
            "module_id": "pac_cfc",
            "phase_frequency_range": [4, 8],
            "amplitude_frequency_range": [30, 80],
            "frequency_grid": {"phase": [4, 6, 8], "amplitude": [30, 50, 80]},
            "surrogate_method": "time_shift",
            "normalization": "zscore_against_surrogates",
            "random_state": 20260621,
            "sensor_or_source_space": "sensor_topomap",
            "inverse_method": None,
            "forward_model_or_mri_context": None,
            "caption_text": "PAC comodulogram and sensor-space topomap; descriptive sensor-space display only.",
            "forbidden_claim_hits": [],
        },
        "pac_source_negative": {
            "schema_version": "qlanalyser-pac-source-boundary-v0.1",
            "module_id": "pac_cfc",
            "phase_frequency_range": [4, 8],
            "amplitude_frequency_range": [],
            "sensor_or_source_space": "sensor_topomap",
            "caption_text": "This topomap localizes abnormal coupling to hippocampus and proves brain-region communication.",
            "forbidden_claim_hits": ["precise brain-region localization"],
        },
    }
    paths = {}
    for name, payload in fixtures.items():
        paths[name] = write_json(FIXTURE_DIR / f"{name}.json", payload)
    return paths


def evaluate_tfr(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    text = json.dumps(data, ensure_ascii=False).lower()
    checks = {
        "measure_type_present": status_item("pass" if data.get("measure_type") in {"power", "itc", "power_and_itc"} else "block", data.get("measure_type")),
        "method_present": status_item("pass" if data.get("method") else "block", data.get("method")),
        "frequency_grid_present": status_item("pass" if data.get("frequencies") else "block"),
        "time_axis_present": status_item("pass" if data.get("times") else "block"),
        "baseline_or_correction_present": status_item("pass" if data.get("baseline") and data.get("correction") else "block"),
        "units_or_colorbar_present": status_item("pass" if data.get("units") and data.get("colorbar_label") else "block"),
        "method_parameters_present": status_item(
            "pass" if all(key in data for key in ["n_cycles", "time_bandwidth", "decim", "return_itc"]) else "block",
            {key: key in data for key in ["n_cycles", "time_bandwidth", "decim", "return_itc"]},
        ),
        "warnings_and_limitations_present": status_item("pass" if data.get("warnings") and data.get("limitations") else "block"),
        "no_effect_claim_without_statistics": status_item(
            "pass" if not has_any_claim(text, [r"\bproves?\b", r"\bsignificant\b", r"\beffect\b"]) else "block",
            data.get("caption_text"),
        ),
    }
    blockers = [name for name, item in checks.items() if item["status"] == "block"]
    return {"artifact": str(path), "decision": "block" if blockers else "pass", "checks": checks, "blockers": blockers}


def evaluate_connectivity(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    text = json.dumps(data, ensure_ascii=False).lower()
    overclaim = has_any_claim(text, [r"\bcauses?\b", r"\bsends? information\b", r"\banatomical connectivity\b", r"\bbrain region.*communicat"])
    checks = {
        "connectivity_method_present": status_item("pass" if data.get("connectivity_method") else "block"),
        "mode_or_estimator_present": status_item("pass" if data.get("mode") or data.get("estimator") else "block"),
        "node_labels_present": status_item("pass" if data.get("nodes") and data.get("indices") else "block"),
        "frequency_bands_present": status_item("pass" if data.get("frequency_bands") else "block"),
        "shape_or_dimension_metadata_present": status_item("pass" if data.get("shape") or data.get("n_connections_or_n_nodes") else "block"),
        "sensor_or_source_space_label_present": status_item("pass" if data.get("space") in {"sensor", "source"} else "block", data.get("space")),
        "threshold_policy_present_when_network_plot": status_item("pass" if data.get("threshold_policy") else "block"),
        "limitations_present": status_item("pass" if data.get("limitations") else "block"),
        "no_causal_or_anatomical_overclaim": status_item("pass" if not overclaim else "block", data.get("caption_text")),
    }
    blockers = [name for name, item in checks.items() if item["status"] == "block"]
    return {"artifact": str(path), "decision": "block" if blockers else "pass", "checks": checks, "blockers": blockers}


def evaluate_pac_source(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    text = json.dumps(data, ensure_ascii=False).lower()
    source_claim = has_any_claim(text, [r"\blocali[sz]es?\b", r"\bhippocampus\b", r"\bprecise brain", r"\bbrain-region communication\b"])
    has_source_model = bool(data.get("inverse_method") and data.get("forward_model_or_mri_context"))
    checks = {
        "pac_frequency_grid_present": status_item("pass" if data.get("phase_frequency_range") and data.get("amplitude_frequency_range") and data.get("frequency_grid") else "block"),
        "pac_surrogate_method_present": status_item("pass" if data.get("surrogate_method") else "block"),
        "pac_normalization_present": status_item("pass" if data.get("normalization") else "block"),
        "random_state_or_reproducibility_present": status_item("pass" if data.get("random_state") is not None else "block"),
        "source_or_sensor_space_label_present": status_item("pass" if data.get("sensor_or_source_space") else "block"),
        "inverse_method_fields_present_when_source_claimed": status_item("pass" if not source_claim or has_source_model else "block"),
        "forbidden_claim_scan_present": status_item("pass" if "forbidden_claim_hits" in data else "block"),
        "no_precise_localization_from_sensor_topomap": status_item("pass" if not source_claim else "block", data.get("caption_text")),
    }
    blockers = [name for name, item in checks.items() if item["status"] == "block"]
    return {"artifact": str(path), "decision": "block" if blockers else "pass", "checks": checks, "blockers": blockers}


def summarize_pair(requirement_id: str, positive: dict[str, Any], negative: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "decision": "pass" if positive["decision"] == "pass" and negative["decision"] == "block" else "block",
        "positive_case": positive,
        "negative_case": negative,
        "boundary": "Synthetic positive/negative dry-run only; not product pass or scientific validation.",
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = build_synthetic_fixtures()
    requirements = read_jsonl(PACK_ROOT / "expected_output_requirements.jsonl", "requirement_id")
    interactions = read_jsonl(PACK_ROOT / "interaction_test_cases.jsonl", "task_id")
    fixtures = read_jsonl(PACK_ROOT / "fixture_requirements.jsonl", "fixture_id")

    findings = {
        "VR-EO-0017": summarize_pair("VR-EO-0017", evaluate_tfr(paths["tfr_positive"]), evaluate_tfr(paths["tfr_negative_missing_baseline"])),
        "VR-EO-0018": summarize_pair("VR-EO-0018", evaluate_connectivity(paths["connectivity_positive"]), evaluate_connectivity(paths["connectivity_negative_causal"])),
        "VR-EO-0019": summarize_pair("VR-EO-0019", evaluate_pac_source(paths["pac_source_positive"]), evaluate_pac_source(paths["pac_source_negative"])),
    }
    blocking_findings = {key: item for key, item in findings.items() if item.get("decision") == "block"}
    payload = {
        "schema_version": "qlanalyser-virtual-reviewer-round-006-dry-run-v0.1",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "completed",
        "product_gate_status": "blocked" if blocking_findings else "not_blocked_by_round_006_dry_run",
        "important_boundary": (
            "This validates synthetic object-layer positive/negative cases only. It is not product pass, "
            "advanced method release, or scientific/clinical approval."
        ),
        "pack_root": str(PACK_ROOT),
        "fixture_dir": str(FIXTURE_DIR),
        "round_006_objects": {
            "interaction_tests": {key: interactions.get(key) for key in ["VR-ITC-0017", "VR-ITC-0018", "VR-ITC-0019"]},
            "fixtures": {key: fixtures.get(key) for key in ["VR-FX-0017", "VR-FX-0018", "VR-FX-0019"]},
            "expected_outputs": {key: requirements.get(key) for key in ["VR-EO-0017", "VR-EO-0018", "VR-EO-0019"]},
        },
        "findings": findings,
        "blocking_findings": blocking_findings,
        "next_actions": [
            "Wire these validators to real TFR/connectivity/PAC artifact exports before exposing advanced methods.",
            "Keep advanced method UI disabled or beta/lab-only until real UI trace and artifact validators pass.",
            "Continue blocking causal, anatomical connectivity, precise localization, diagnosis, and unsupported effect claims.",
        ],
    }
    write_json(OUT_PATH, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
