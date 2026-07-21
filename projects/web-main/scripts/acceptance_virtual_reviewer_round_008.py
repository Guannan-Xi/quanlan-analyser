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
OUT_DIR = ROOT / "work" / "release_evidence" / "virtual_reviewer_round_008"
OUT_PATH = OUT_DIR / "round_008_dry_run.json"
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
    item: dict[str, Any] = {"status": status}
    if evidence is not None:
        item["evidence"] = evidence
    if detail:
        item["detail"] = detail
    return item


def has_forbidden_claim(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def build_synthetic_fixtures() -> dict[str, Path]:
    fixtures = {
        "erp_positive": {
            "schema_version": "qlanalyser-erp-evoked-v0.1",
            "module_id": "erp_p300",
            "event_id": {"standard": 1, "target": 2},
            "tmin": -0.2,
            "tmax": 0.8,
            "baseline": [-0.2, 0.0],
            "reject_by_annotation": True,
            "drop_log": [{"epoch": 3, "reason": "BAD_annotation"}],
            "nave": {"standard": 52, "target": 48},
            "per_condition_epoch_counts": {"standard": 52, "target": 48},
            "channels": ["Fz", "Cz", "Pz"],
            "units": "uV",
            "warnings": ["Synthetic validator fixture; descriptive ERP only."],
            "caption_text": "ERP averages disclose event IDs, baseline, drop log, nave, channels, and units.",
        },
        "erp_negative_missing_counts": {
            "schema_version": "qlanalyser-erp-evoked-v0.1",
            "module_id": "erp_p300",
            "event_id": {"target": 2},
            "tmin": -0.2,
            "tmax": 0.8,
            "baseline": None,
            "reject_by_annotation": True,
            "channels": ["Pz"],
            "units": "",
            "caption_text": "The target ERP is stronger and proves a reliable group difference.",
        },
        "grand_average_positive": {
            "schema_version": "qlanalyser-grand-average-v0.1",
            "analysis_output_type": "grand_average_evoked",
            "subject_count": 12,
            "subject_refs": [f"sub-{idx:02d}" for idx in range(1, 13)],
            "channel_policy": "equalize_channels_then_average",
            "common_channels": ["Fz", "Cz", "Pz"],
            "interpolate_bads": False,
            "dropped_channels": ["Oz"],
            "nave": 12,
            "per_subject_contribution": {f"sub-{idx:02d}": 1 for idx in range(1, 13)},
            "warnings": ["Grand average is descriptive; inferential statistics require a separate design and test."],
            "caption_text": "Grand average discloses subject count, channel equalization, dropped channels, and per-subject contribution.",
        },
        "grand_average_negative_missing_policy": {
            "schema_version": "qlanalyser-grand-average-v0.1",
            "analysis_output_type": "grand_average_evoked",
            "subject_refs": ["sub-01", "sub-02"],
            "common_channels": [],
            "caption_text": "Grand average shows the true group effect.",
        },
        "cluster_positive": {
            "schema_version": "qlanalyser-cluster-statistics-v0.1",
            "analysis_output_type": "cluster_permutation",
            "test_type": "spatiotemporal_cluster_1samp",
            "n_permutations": 1024,
            "threshold": {"type": "cluster_forming", "value": 2.5},
            "adjacency": "sensor_time_adjacency",
            "correction_method": "cluster-level permutation",
            "statistical_unit": "subject",
            "subject_count": 18,
            "cluster_p_values": [0.041],
            "limitations": ["Cluster-level inference; do not interpret as exact time/channel/source boundary."],
            "caption_text": "One cluster-level permutation result is reported with method, threshold, adjacency, correction, statistical unit, and p value.",
            "forbidden_claim_hits": [],
        },
        "cluster_negative_exact_extent": {
            "schema_version": "qlanalyser-cluster-statistics-v0.1",
            "analysis_output_type": "cluster_permutation",
            "test_type": "",
            "n_permutations": None,
            "threshold": None,
            "statistical_unit": "epochs",
            "subject_count": None,
            "caption_text": "The significant cluster proves the exact Pz effect from 310 to 420 ms and localizes the abnormal source.",
        },
    }
    return {name: write_json(FIXTURE_DIR / f"{name}.json", payload) for name, payload in fixtures.items()}


def evaluate_erp(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    text = json.dumps(data, ensure_ascii=False)
    checks = {
        "event_id_mapping_present": status_item("pass" if data.get("event_id") and len(data.get("event_id", {})) >= 2 else "block", data.get("event_id")),
        "epoch_tmin_tmax_present": status_item("pass" if data.get("tmin") is not None and data.get("tmax") is not None else "block"),
        "baseline_window_present_or_explicit_none": status_item("pass" if data.get("baseline") or data.get("baseline") == "none_explicit" else "block", data.get("baseline")),
        "reject_by_annotation_present": status_item("pass" if "reject_by_annotation" in data else "block", data.get("reject_by_annotation")),
        "drop_log_present": status_item("pass" if data.get("drop_log") else "block"),
        "nave_or_epoch_count_present": status_item("pass" if data.get("nave") or data.get("per_condition_epoch_counts") else "block"),
        "per_condition_counts_present": status_item("pass" if data.get("per_condition_epoch_counts") else "block"),
        "channel_units_present": status_item("pass" if data.get("channels") and data.get("units") else "block"),
        "baseline_state_present": status_item("pass" if "baseline" in data else "block"),
        "no_erp_overclaim": status_item(
            "pass"
            if not has_forbidden_claim(text, [r"\bproves?\b", r"\breliable group difference\b", r"\bdiagnos"])
            else "block",
            data.get("caption_text"),
        ),
    }
    blockers = [name for name, item in checks.items() if item["status"] == "block"]
    return {"artifact": str(path), "decision": "block" if blockers else "pass", "checks": checks, "blockers": blockers}


def evaluate_grand_average(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    text = json.dumps(data, ensure_ascii=False)
    checks = {
        "subject_count_present": status_item("pass" if isinstance(data.get("subject_count"), int) and data["subject_count"] > 1 else "block", data.get("subject_count")),
        "subject_ids_or_anonymized_indices_present": status_item("pass" if data.get("subject_refs") else "block"),
        "channel_set_alignment_present": status_item("pass" if data.get("channel_policy") and data.get("common_channels") else "block"),
        "interpolate_bads_policy_present": status_item("pass" if "interpolate_bads" in data else "block", data.get("interpolate_bads")),
        "dropped_channels_present_when_any": status_item("pass" if "dropped_channels" in data else "block", data.get("dropped_channels")),
        "nave_or_contribution_count_present": status_item("pass" if data.get("nave") or data.get("per_subject_contribution") else "block"),
        "per_subject_contribution_present": status_item("pass" if data.get("per_subject_contribution") else "block"),
        "grand_average_not_inferential": status_item(
            "pass" if not has_forbidden_claim(text, [r"\btrue group effect\b", r"\bsignificant\b", r"\bproves?\b"]) else "block",
            data.get("caption_text"),
        ),
    }
    blockers = [name for name, item in checks.items() if item["status"] == "block"]
    return {"artifact": str(path), "decision": "block" if blockers else "pass", "checks": checks, "blockers": blockers}


def evaluate_cluster(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    text = str(data.get("caption_text", ""))
    exact_extent_overclaim = has_forbidden_claim(
        text,
        [
            r"\bexact\b.*\b(ms|time|channel|source)\b",
            r"\blocali[sz]es?\b",
            r"\bproves?\b.*\b(Pz|source|effect)\b",
            r"\babnormal source\b",
        ],
    )
    checks = {
        "test_type_present": status_item("pass" if data.get("test_type") else "block"),
        "permutation_count_present": status_item("pass" if isinstance(data.get("n_permutations"), int) and data["n_permutations"] > 0 else "block"),
        "threshold_present": status_item("pass" if data.get("threshold") else "block"),
        "adjacency_present_when_spatiotemporal": status_item("pass" if data.get("adjacency") else "block"),
        "correction_method_present": status_item("pass" if data.get("correction_method") else "block"),
        "statistical_unit_present": status_item("pass" if data.get("statistical_unit") == "subject" else "block", data.get("statistical_unit")),
        "subject_count_present_when_group": status_item("pass" if isinstance(data.get("subject_count"), int) and data["subject_count"] > 1 else "block", data.get("subject_count")),
        "cluster_level_interpretation_present": status_item("pass" if data.get("limitations") else "block"),
        "caption_forbidden_claim_scan_present": status_item("pass" if "forbidden_claim_hits" in data else "block"),
        "no_exact_extent_overclaim": status_item("pass" if not exact_extent_overclaim else "block", data.get("caption_text")),
    }
    blockers = [name for name, item in checks.items() if item["status"] == "block"]
    return {"artifact": str(path), "decision": "block" if blockers else "pass", "checks": checks, "blockers": blockers}


def summarize_pair(requirement_id: str, positive: dict[str, Any], negative: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "decision": "pass" if positive["decision"] == "pass" and negative["decision"] == "block" else "block",
        "positive_case": positive,
        "negative_case": negative,
        "boundary": "Synthetic positive/negative dry-run only; not product pass, statistical approval, or scientific validation.",
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = build_synthetic_fixtures()
    requirements = read_jsonl(PACK_ROOT / "expected_output_requirements.jsonl", "requirement_id")
    interactions = read_jsonl(PACK_ROOT / "interaction_test_cases.jsonl", "task_id")
    fixtures = read_jsonl(PACK_ROOT / "fixture_requirements.jsonl", "fixture_id")
    coverage = json.loads((PACK_ROOT / "coverage_matrix_round_008.json").read_text(encoding="utf-8"))

    findings = {
        "VR-EO-0023": summarize_pair("VR-EO-0023", evaluate_erp(paths["erp_positive"]), evaluate_erp(paths["erp_negative_missing_counts"])),
        "VR-EO-0024": summarize_pair(
            "VR-EO-0024",
            evaluate_grand_average(paths["grand_average_positive"]),
            evaluate_grand_average(paths["grand_average_negative_missing_policy"]),
        ),
        "VR-EO-0025": summarize_pair(
            "VR-EO-0025",
            evaluate_cluster(paths["cluster_positive"]),
            evaluate_cluster(paths["cluster_negative_exact_extent"]),
        ),
    }
    blocking_findings = {key: item for key, item in findings.items() if item.get("decision") == "block"}
    payload = {
        "schema_version": "qlanalyser-virtual-reviewer-round-008-dry-run-v0.1",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "completed",
        "product_gate_status": "blocked" if blocking_findings else "not_blocked_by_round_008_dry_run",
        "important_boundary": (
            "This validates synthetic object-layer positive/negative cases only. It is not product pass, "
            "statistical approval, clinical approval, or group-analysis release approval."
        ),
        "pack_root": str(PACK_ROOT),
        "coverage_matrix": str(PACK_ROOT / "coverage_matrix_round_008.json"),
        "coverage_matrix_loaded": isinstance(coverage, list) and len(coverage) == 3,
        "fixture_dir": str(FIXTURE_DIR),
        "round_008_objects": {
            "interaction_tests": {key: interactions.get(key) for key in ["VR-ITC-0023", "VR-ITC-0024", "VR-ITC-0025"]},
            "fixtures": {key: fixtures.get(key) for key in ["VR-FX-0023", "VR-FX-0024", "VR-FX-0025"]},
            "expected_outputs": {key: requirements.get(key) for key in ["VR-EO-0023", "VR-EO-0024", "VR-EO-0025"]},
        },
        "findings": findings,
        "blocking_findings": blocking_findings,
        "next_actions": [
            "Wire ERP baseline/count validator to real ERP report exports before interpreting condition differences.",
            "Keep grand-average/group average reports blocked unless subject count and channel policy fields are exported.",
            "Keep cluster/statistics features disabled unless test settings, statistical unit, correction and caption boundary validators pass.",
        ],
    }
    write_json(OUT_PATH, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
